#include "game/movement.hpp"
#include "game/catalog.hpp"
#include "game/land_combat.hpp"
#include "game/naval.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <deque>
#include <functional>
#include <stdexcept>

namespace game::campaign {
namespace {
using V = json::Value;
using O = V::Object;
using A = V::Array;
void require(bool c, const std::string &m) {
  if (!c)
    throw std::runtime_error(m);
}
bool flag(const std::map<Id, int> &f, const Id &k) {
  auto i = f.find(k);
  return i != f.end() && i->second != 0;
}
bool truth(const V &v, const Id &k) {
  const auto *p = v.find(k);
  return p && p->isBool() && p->asBool();
}
const V *profile(const State &s) {
  return s.definition->rules.find("movement_profile");
}
const V &node(const State &s, const Id &id) {
  return s.definition->geography.require("nodes").require(id);
}
const V *edge(const State &s, const Id &a, const Id &b) {
  for (const auto &e : node(s, a).require("neighbors").asArray())
    if (e.require("neighbor_id").asString() == b)
      return &e;
  return nullptr;
}
std::set<Id> terrains(const V *v) {
  std::set<Id> out;
  if (!v || v->isNull())
    return out;
  if (v->isString()) {
    if (v->asString() != "normal")
      out.insert(v->asString());
  } else if (v->isArray())
    for (const auto &x : v->asArray())
      if (x.asString() != "normal")
        out.insert(x.asString());
  return out;
}
bool hostile(const State &s, const Id &nation, const Id &other) {
  return areAtWar(s, nation, other);
}
bool restrictedTerrain(const std::set<Id> &t) {
  for (const auto &x :
       {"mountain", "desert", "jungle", "marsh", "tundra", "ice", "tundra_ice"})
    if (t.contains(x))
      return true;
  return false;
}
bool inHome(const State &s, const Id &nation, const Id &zone) {
  auto i = s.definition->factions.find(nation);
  return i != s.definition->factions.end() &&
         i->second.homeCountry.contains(zone);
}
bool hasTech(const State &s, const Id &nation, const Id &tech) {
  auto i = s.nations.at(nation).technologyStages.find(tech);
  return i != s.nations.at(nation).technologyStages.end() && i->second == 4;
}
bool damagedThisTurn(const State &s, const Id &id) {
  auto i = s.flags.find("logistics_damaged_turn:" + id);
  return i != s.flags.end() &&
         i->second == static_cast<int>(s.clock.playerTurnSerial + 1);
}
std::vector<const RailState *> rails(const State &s, const Id &a, const Id &b) {
  std::vector<const RailState *> out;
  for (const auto &[id, r] : s.rails)
    if ((r.endpointA == a && r.endpointB == b) ||
        (r.endpointB == a && r.endpointA == b))
      out.push_back(&r);
  return out;
}
bool hasRail(const State &s, const Id &a, const Id &b) {
  const auto *e = edge(s, a, b);
  return !rails(s, a, b).empty() || (e && truth(*e, "railway_connection"));
}
bool hasRiver(const State &s, const Id &a, const Id &b) {
  const auto *e = edge(s, a, b);
  return e && truth(*e, "has_river");
}
bool narrow(const V *e) { return e && truth(*e, "narrow_crossing"); }
bool continuousInfrastructure(const State &s, const Id &id) {
  auto i = s.flags.find("logistics_start_damaged:" + id);
  return (i == s.flags.end() || i->second == 0) && !damagedThisTurn(s, id);
}
bool strategicPermission(const State &s, const Id &nation, const Id &zone) {
  const auto owner = s.territories.at(zone).possessor;
  if (!owner)
    return false;
  return strategicRailPermission(s, nation, *owner);
}
bool gaugeChange(const State &s, const Id &a, const Id &b) {
  const auto *e = edge(s, a, b);
  const auto *raw = e ? e->find("gauge_change") : nullptr;
  if ((!e || !truth(*e, "railway_connection")) && !rails(s, a, b).empty()) {
    const std::set<Id> broad{"brazil",   "spain",      "finland",
                             "mongolia", "tannu_tuva", "ussr"};
    return broad.contains(originalNation(s, a)) !=
           broad.contains(originalNation(s, b));
  }
  if (raw && raw->isBool())
    return raw->asBool();
  if (const auto *p = profile(s))
    for (const auto &r : p->require("rail_gauges").asArray()) {
      const auto &ends = r.require("endpoints").asArray();
      if ((ends[0].asString() == a && ends[1].asString() == b) ||
          (ends[0].asString() == b && ends[1].asString() == a))
        return r.require("gauge_change").asBool();
    }
  throw std::runtime_error("Unreviewed railroad gauge at " + a + " -> " + b);
}
bool opposingFortification(const State &s, const Id &nation, const Id &from,
                           const Id &to) {
  if (!s.territories.at(to).possessor ||
      !hostile(s, nation, *s.territories.at(to).possessor))
    return false;
  for (const auto &[id, f] : s.facilities)
    if (f.zone == to &&
        (f.type == "fortification" || f.type == "improved_fortification")) {
      if (truth(node(s, to), "is_city") || flag(f.flags, "border:" + from))
        return true;
      const auto *metadata = s.definition->geography.find("facilities");
      const auto *spec = metadata ? metadata->find(id) : nullptr;
      if (spec)
        if (const auto *protectedBorders = spec->find("land_accesses"))
          for (const auto &x : protectedBorders->asArray())
            if (x.asString() == from)
              return true;
    }
  return false;
}
std::string railCounter(const State &s, const Id &region) {
  return "rail_used:" + politicalPlayer(s, s.currentNation()) + ":" + region;
}
int navalRange(const FacilityState &f) {
  return f.type.rfind("major_", 0) == 0 ? 4 : 2;
}
bool navalFacilityType(const Id &t) {
  return t.find("port") != Id::npos || t.find("dockyard") != Id::npos ||
         t.find("shipyard") != Id::npos;
}
bool narrowBlocked(const State &s, const Id &nation, const V &e, bool combat,
                   const Id &target) {
  if (combat)
    for (const auto &[id, f] : s.facilities)
      if (f.zone == target && f.type == "coastal_artillery")
        return true;
  const auto *seas = e.find("narrow_crossing_sea_zones");
  if (!seas)
    return true;
  for (const auto &sea : seas->asArray())
    for (const auto &[id, u] : s.units)
      if (u.zone == sea.asString() && hostile(s, nation, u.owner)) {
        if (unitClass(s, u, "surface_warship") ||
            (unitClass(s, u, "submarine") && !flag(u.turnFlags, "submerged")) ||
            u.commitments.contains("maritime_air_patrol") ||
            flag(u.turnFlags, "on_map"))
          return true;
      }
  return false;
}
Id crossingCounter(const V &e, const Id &a, const Id &b) {
  const auto *id = e.find("narrow_crossing_id");
  return "crossing_used:" +
         (id ? id->asString() : std::min(a, b) + "__" + std::max(a, b));
}
Action movementAction(const State &s, const RouteRequest &r) {
  A path;
  for (const auto &z : r.path)
    path.emplace_back(z);
  O parameters{{"unit", V(r.unit)},
               {"path", V(path)},
               {"mode", V(toString(r.mode))},
               {"combat", V(r.combat)}};
  if (r.towed)
    parameters["towed"] = V(*r.towed);
  V params(std::move(parameters));
  const auto &u = s.units.at(r.unit);
  return {"move_" + contentDigest(canonicalJson(params)),
          "movement_route",
          politicalPlayer(s, u.owner),
          u.owner,
          std::nullopt,
          std::move(params)};
}
RouteRequest requestFrom(const Action &a) {
  RouteRequest r;
  r.unit = a.parameters.require("unit").asString();
  for (const auto &x : a.parameters.require("path").asArray())
    r.path.push_back(x.asString());
  r.mode = parseMovementMode(a.parameters.require("mode").asString());
  r.combat = a.parameters.require("combat").asBool();
  if (const auto *towed = a.parameters.find("towed"))
    r.towed = towed->asString();
  return r;
}
} // namespace

std::string toString(MovementMode m) {
  switch (m) {
  case MovementMode::Ordinary:
    return "ordinary";
  case MovementMode::Blitz:
    return "blitz";
  case MovementMode::StrategicRail:
    return "strategic_rail";
  case MovementMode::StrategicRiver:
    return "strategic_river";
  case MovementMode::NarrowCrossing:
    return "narrow_crossing";
  }
  throw std::runtime_error("Unknown movement mode");
}
MovementMode parseMovementMode(const std::string &s) {
  for (auto m : {MovementMode::Ordinary, MovementMode::Blitz,
                 MovementMode::StrategicRail, MovementMode::StrategicRiver,
                 MovementMode::NarrowCrossing})
    if (toString(m) == s)
      return m;
  throw std::runtime_error("Unknown movement mode: " + s);
}
bool unitClass(const State &s, const UnitState &u, const Id &c) {
  return s.definition->catalog->unit(u.type).classes.contains(c);
}
bool areAtWar(const State &s, const Id &actor, const Id &target) {
  return actor != target && s.nations.at(actor).atWarWith.contains(target);
}
bool logisticsFriendly(const State &s, const Id &actor, const Id &owner) {
  return actor == owner || politicallyFriendly(s, actor, owner) ||
         controlledBy(s, owner, actor);
}
bool strategicRailPermission(const State &s, const Id &actor, const Id &owner) {
  if (actor == owner) return true;
  if (!politicallyFriendly(s, actor, owner)) return false;
  // Optional equality, including two absent players, is intentional.
  if (s.nations.at(actor).player == s.nations.at(owner).player) return true;
  return flag(s.nations.at(owner).turnFlags, "rail_permission:" + actor);
}
bool movementController(const State &s, const Id &nation) {
  return nation == s.currentNation() ||
         controlledBy(s, nation, s.currentNation()) ||
         (nation == "dadao" && s.currentNation() == "japan" &&
          flag(s.nations.at(nation).gameFlags,
               "direct_axis_control_after_japan_surrender"));
}
bool landAccess(const State &s, const Id &nation, const Id &zone, bool combat) {
  if (!s.territories.contains(zone))
    return false;
  const auto owner = s.territories.at(zone).possessor;
  if (!owner)
    return combat;
  if (*owner == nation || politicallyFriendly(s, nation, *owner))
    return true;
  if (!combat)
    return false;
  if (controlledBy(s, nation, s.currentNation()))
    return hostile(s, nation, *owner);
  return hostile(s, nation, *owner) ||
         mayDeclareWar(s, nation, *owner, DeclarationMode::LandAttack).allowed;
}
bool aircraftFlightAccess(const State &s, const Id &nation, const Id &zone,
                          bool combat) {
  if (!s.territories.contains(zone)) {
    if (node(s, zone).require("type").asString() != "sea")
      return false;
    if (!combat)
      for (const auto &[id, u] : s.units)
        if (u.zone == zone && hostile(s, nation, u.owner) &&
            unitClass(s, u, "fighter"))
          return false;
    return true;
  }
  const auto owner = s.territories.at(zone).possessor;
  if (!owner)
    return true;
  if (*owner == nation || politicallyFriendly(s, nation, *owner) ||
      controlledBy(s, *owner, nation))
    return true;
  if (!hostile(s, nation, *owner))
    return false;
  if (!combat)
    for (const auto &[id, u] : s.units)
      if (u.zone == zone && hostile(s, nation, u.owner) &&
          unitClass(s, u, "fighter"))
        return false;
  return true;
}
bool heldSinceTurnStart(const State &s, const Id &nation, const Id &zone,
                        bool allowFriendly) {
  const auto t = s.territories.find(zone);
  const auto start = s.turnStart.possessions.find(zone);
  if (t == s.territories.end() || start == s.turnStart.possessions.end() ||
      !t->second.possessor || t->second.possessor != start->second)
    return false;
  const auto changed = t->second.flags.find("last_possession_change_turn");
  if (changed != t->second.flags.end() &&
      changed->second == static_cast<int>(s.clock.playerTurnSerial))
    return false;
  return *t->second.possessor == nation ||
         (allowFriendly && logisticsFriendly(s, nation, *t->second.possessor));
}
bool heldSinceNationTurnStart(const State &s, const Id &nation, const Id &zone,
                              bool allowFriendly) {
  const auto t = s.territories.find(zone);
  if (t == s.territories.end() || !t->second.possessor ||
      !s.nations.contains(nation))
    return false;
  if (*t->second.possessor != nation &&
      (!allowFriendly || !logisticsFriendly(s, nation, *t->second.possessor)))
    return false;
  const auto changed = t->second.flags.find("last_possession_change_turn");
  if (changed == t->second.flags.end())
    return true;
  const auto ownStart =
      s.nations.at(nation).gameFlags.find("logistics_last_turn_start");
  return ownStart != s.nations.at(nation).gameFlags.end() &&
         changed->second + 1 < ownStart->second;
}
BorderApproach borderApproach(const State &s, const Id &from, const Id &to) {
  BorderApproach out;
  out.from = from;
  out.to = to;
  out.nodeTerrain = terrains(node(s, to).find("terrain"));
  const auto *e = edge(s, from, to);
  require(e, "Nonadjacent approach edge");
  out.borderTerrain = terrains(e->find("border_terrain"));
  const auto *r = e->find("river_crossing");
  out.riverKnown = r && r->isBool();
  out.river = out.riverKnown && r->asBool();
  if (!out.riverKnown)
    if (const auto *p = profile(s))
      for (const auto &review : p->require("river_crossings").asArray())
        if (review.require("from").asString() == from &&
            review.require("to").asString() == to) {
          out.river = review.require("river_crossing").asBool();
          out.riverKnown = true;
          break;
        }
  return out;
}
bool railUndamaged(const State &s, const Id &from, const Id &to, bool since) {
  if (!hasRail(s, from, to))
    return false;
  for (const auto *r : rails(s, from, to)) {
    for (const auto &[endpoint, d] : r->damageByEndpoint)
      if (d > 0)
        return false;
    if (since) {
      if (!continuousInfrastructure(s, r->id))
        return false;
      const auto i = s.flags.find("logistics_rail_created_turn:" + r->id);
      if (i != s.flags.end() &&
          i->second == static_cast<int>(s.clock.playerTurnSerial + 1))
        return false;
    }
  }
  return true;
}
bool riverRouteAvailable(const State &s, const Id &nation, const Id &from,
                         const Id &to) {
  if (!hasRiver(s, from, to))
    return false;
  const auto *e = edge(s, from, to);
  if (const auto *banks = e->find("river_banks"))
    for (const auto &z : banks->asArray()) {
      const auto i = s.territories.find(z.asString());
      if (i == s.territories.end())
        return false;
      if (i->second.possessor && hostile(s, nation, *i->second.possessor))
        return false;
    }
  // A river forming this edge cannot be used along an enemy-held bank.
  for (const auto &z : {from, to})
    if (s.territories.at(z).possessor &&
        hostile(s, nation, *s.territories.at(z).possessor))
      return false;
  return true;
}
bool railGaugeChange(const State &s, const Id &from, const Id &to) {
  return gaugeChange(s, from, to);
}
Id railRegion(const State &s, const Id &zone) {
  const auto *rg = s.definition->geography.find("rail_geography");
  const auto *memberships = rg ? rg->find("memberships") : nullptr;
  const auto *entry = memberships ? memberships->find(zone) : nullptr;
  if (entry && entry->isString())
    return entry->asString();
  if (const auto *p = profile(s))
    if (const auto *region = p->require("rail_regions").find(zone))
      return region->asString();
  throw std::runtime_error("Unreviewed rail region for " + zone);
}
int regionalRailCapacity(const Id &r) {
  static const std::map<Id, int> capacities{
      {"north_america", 4}, {"south_america", 1}, {"europe", 4},
      {"soviet_union", 2},  {"africa", 1},        {"middle_east", 1},
      {"asia", 1}};
  return capacities.at(r);
}
bool blitzPairValid(const State &s, const UnitState &u, const Id &from,
                    const Id &to) {
  if (u.type == "light_armor" || u.type == "medium_armor" || u.type == "t_34" ||
      u.type == "heavy_armor" || u.type == "tiger_i" ||
      u.type == "panzergrenadier")
    return true;
  for (const auto &link : u.commitments)
    if (link.rfind("blitz_with:", 0) == 0) {
      const auto armor = s.units.find(link.substr(11));
      return armor != s.units.end() && armor->second.zone == to &&
             armor->second.commitments.contains("blitz_from:" + from) &&
             armor->second.commitments.contains("blitz_to:" + to);
    }
  return false;
}

static RouteResult validateSingleRoute(const State &s, const RouteRequest &r) {
  RouteResult out;
  auto fail = [&](const std::string &why) {
    out.reason = why;
    return out;
  };
  const auto it = s.units.find(r.unit);
  if (it == s.units.end())
    return fail("Unknown unit");
  const auto &u = it->second;
  if (!movementController(s, u.owner))
    return fail("Not this nation's movement turn");
  for (const auto &[id, battle] : s.battles)
    if (!flag(battle.flags, "finished") && !flag(battle.flags, "capture_done") &&
        std::find(battle.attackers.begin(), battle.attackers.end(), u.id) != battle.attackers.end())
      return fail("Unit is committed to an unresolved battle");
  if (u.carriedBy)
    return fail("Cargo must be moved by its transport");
  if (flag(u.turnFlags, "naval_unloaded") ||
      flag(u.turnFlags, "air_transport_unloaded") ||
      u.commitments.contains("transport_unloaded") ||
      (u.gameFlags.contains("port_unloaded_round") &&
       u.gameFlags.at("port_unloaded_round") == s.clock.roundIndex + 1))
    return fail("Transported units cannot move further after unloading");
  if (flag(u.turnFlags, "repairing") || u.commitments.contains("repair"))
    return fail("Unit is committed to repair");
  if (u.commitments.contains("attrition"))
    return fail("Artillery used an attrition attack this turn");
  if (flag(u.turnFlags, "placed_this_turn"))
    return fail("Newly placed units cannot move this turn");
  if (r.path.size() < 2 || r.path.front() != u.zone)
    return fail("Route must start at the unit's current zone");
  const bool strategic = r.mode == MovementMode::StrategicRail ||
                         r.mode == MovementMode::StrategicRiver;
  if (strategic) {
    if (s.clock.phase != Phase::NonCombatMovement || r.combat)
      return fail("Strategic rail is noncombat movement");
    if (!u.route.empty() || u.commitments.contains("combat_move") ||
        flag(u.turnFlags, "strategic_moved"))
      return fail("Unit already moved this turn");
  } else {
    if (!unitClass(s, u, "land"))
      return fail("Ordinary land movement requires a land unit");
    if (r.combat && s.clock.phase != Phase::CombatMovement &&
        !(r.mode == MovementMode::Blitz && s.clock.phase == Phase::Combat))
      return fail("Combat movement phase required");
    if (!r.combat && s.clock.phase != Phase::NonCombatMovement)
      return fail("Noncombat movement phase required");
    if (!r.combat && u.commitments.contains("combat_move") &&
        !flag(u.turnFlags, "must_withdraw_from_chinese_gift"))
      return fail("Unit combat moved this turn");
  }
  if (!strategic && (!u.movementRemaining || *u.movementRemaining <= 0))
    return fail("No movement remaining");
  if (unitClass(s, u, "naval") ||
      (strategic && !unitClass(s, u, "land") && !unitClass(s, u, "aircraft") &&
       !unitClass(s, u, "rocket")))
    return fail("Unit cannot use strategic rail");
  if (u.type == "militia" && (!inHome(s, u.owner, r.path.front()) ||
                              !inHome(s, u.owner, r.path.back())))
    return fail("Militia must start and end in its Home Country");
  if (r.mode == MovementMode::Blitz &&
      (!flag(u.turnFlags, "blitz_eligible") ||
       flag(u.turnFlags, "crossed_enemy_fortification") ||
       u.commitments.contains("amphibious_assault")))
    return fail("Unit is not eligible to blitz");
  if (r.mode == MovementMode::Blitz &&
      !blitzPairValid(s, u, r.path.front(), r.path.back()))
    return fail(
        "Blitz companion must follow its paired armor to the same target");
  std::set<Id> seen{r.path.front()};
  for (std::size_t i = 1; i < r.path.size(); ++i) {
    const auto &a = r.path[i - 1];
    const auto &b = r.path[i];
    if (!s.territories.contains(a) || !s.territories.contains(b))
      return fail("Land route left the selected map");
    if (!seen.insert(b).second)
      return fail("Land routes cannot contain loops");
    const auto *e = edge(s, a, b);
    if (!e && !hasRail(s, a, b))
      return fail("Nonadjacent land route");
    if ((e && !passableLandBorder(s, a, b)) ||
        terrains(node(s, b).find("terrain")).contains("impassable"))
      return fail("Impassable land boundary");
    if (narrow(e) && r.mode != MovementMode::NarrowCrossing)
      return fail("Narrow crossing requires its own movement mode");
    if (strategic) {
      if (!heldSinceTurnStart(s, u.owner, b) ||
          !strategicPermission(s, u.owner, b))
        return fail("Strategic destination must be continuously possessed with "
                    "permission");
      if (!railUndamaged(s, a, b) && !riverRouteAvailable(s, u.owner, a, b))
        return fail("No undamaged railroad or usable river");
      if (r.mode == MovementMode::StrategicRiver &&
          !riverRouteAvailable(s, u.owner, a, b))
        return fail("This route is not a river route");
      if (railUndamaged(s, a, b) && !riverRouteAvailable(s, u.owner, a, b) &&
          railGaugeChange(s, a, b) && !hasTech(s, u.owner, "improved_logistics"))
        return fail("Gauge change requires Improved Logistics");
      out.regions.insert(railRegion(s, a));
      out.regions.insert(railRegion(s, b));
    } else {
      if (!landAccess(s, u.owner, b, r.combat))
        return fail("Land access is prohibited");
      const auto owner = s.territories.at(b).possessor;
      const bool friendly = owner && (*owner == u.owner ||
                                      politicallyFriendly(s, u.owner, *owner));
      if (!friendly && i + 1 < r.path.size())
        return fail("Enemy land ends ordinary movement; resolve combat before "
                    "blitzing");
      if (!friendly && u.type == "militia")
        return fail("Militia cannot attack");
      if (!r.combat && !heldSinceTurnStart(s, u.owner, b))
        return fail("Cannot enter land captured this turn");
      const auto approach = borderApproach(s, a, b);
      auto all = approach.nodeTerrain;
      all.insert(approach.borderTerrain.begin(), approach.borderTerrain.end());
      if (r.mode == MovementMode::Blitz) {
        const auto originTerrain = terrains(node(s, a).find("terrain"));
        if (restrictedTerrain(all) || restrictedTerrain(originTerrain) ||
            truth(node(s, a), "is_city") ||
            opposingFortification(s, u.owner, a, b))
          return fail("Terrain, city or fortification prohibits blitzing");
        if (friendly)
          return fail("Cannot blitz into friendly land");
      }
      bool stops = restrictedTerrain(all);
      if (u.type == "cavalry" && all.size() == 1 && all.contains("mountain"))
        stops = false;
      if (stops) {
        out.exhaustsMovement = true;
        if (i + 1 < r.path.size())
          return fail("Terrain ends movement immediately");
      }
      if (r.mode == MovementMode::NarrowCrossing) {
        if (!narrow(e) || r.path.size() != 2 || !u.route.empty())
          return fail("Crossing must begin and end the unit's movement");
        if (r.combat ? u.type != "marine" : !unitClass(s, u, "infantry_class"))
          return fail(
              "Only Marines attack; infantry-class units may noncombat cross");
        if (narrowBlocked(s, u.owner, *e, r.combat, b))
          return fail("Enemy units prevent the narrow crossing");
        const int cap = e->require("unit_capacity").asInt();
        auto used = s.flags.find(crossingCounter(*e, a, b));
        if (used != s.flags.end() && used->second >= cap)
          return fail("Narrow crossing capacity exhausted");
        out.exhaustsMovement = true;
      }
      ++out.cost;
      if (out.cost > *u.movementRemaining)
        return fail("Insufficient movement points");
      out.approach = approach;
    }
  }
  if (strategic) {
    for (const auto &region : out.regions) {
      auto used = s.nations.at(s.currentNation())
                      .turnFlags.find(railCounter(s, region));
      const int capacity =
          regionalRailCapacity(region) +
          (hasTech(s, s.currentNation(), "improved_logistics") ? 1 : 0);
      if (used != s.nations.at(s.currentNation()).turnFlags.end() &&
          used->second >= capacity)
        return fail("Regional rail capacity exhausted");
    }
    out.exhaustsMovement = true;
    out.cost = 0;
  }
  out.allowed = true;
  return out;
}
RouteResult validateRoute(const State &s, const RouteRequest &r) {
  auto fail = [](const std::string &why) {
    RouteResult result;
    result.reason = why;
    return result;
  };
  if (!s.units.contains(r.unit))
    return fail("Unknown moving unit");
  const auto &motor = s.units.at(r.unit);
  if (!r.towed) {
    for (const auto &commitment : motor.commitments)
      if (commitment.rfind("towed_by:", 0) == 0)
        return fail("Towed artillery must continue with its motorized partner");
    return validateSingleRoute(s, r);
  }
  if (r.mode != MovementMode::Ordinary || motor.type != "motorized_infantry" ||
      !s.units.contains(*r.towed) || *r.towed == r.unit)
    return fail("Only ordinary Motorized Infantry movement can tow one unit");
  const auto &artillery = s.units.at(*r.towed);
  if (artillery.type != "artillery" && artillery.type != "advanced_artillery" &&
      artillery.type != "anti_aircraft_artillery")
    return fail("This unit cannot be towed");
  if (artillery.owner != motor.owner || artillery.zone != motor.zone ||
      artillery.carriedBy)
    return fail("Tow pair must be the same nation's units in the same zone");
  const bool continuing = motor.commitments.contains("towing:" + *r.towed) &&
                          artillery.commitments.contains("towed_by:" + r.unit);
  if (!continuing && (!motor.route.empty() || !artillery.route.empty() ||
                      motor.turnOrigin != artillery.turnOrigin))
    return fail("Tow pair must start together before either moves");
  for (const auto &commitment : motor.commitments)
    if (commitment.rfind("towing:", 0) == 0 &&
        commitment != "towing:" + *r.towed)
      return fail(
          "Motorized Infantry is already paired with another towed unit");
  for (const auto &commitment : artillery.commitments)
    if (commitment.rfind("towed_by:", 0) == 0 &&
        commitment != "towed_by:" + r.unit)
      return fail("Artillery is already paired with another towing unit");
  if (!artillery.movementRemaining || *artillery.movementRemaining <= 0)
    return fail("Towed unit has no movement remaining");
  RouteRequest solo = r;
  solo.towed.reset();
  auto motorResult = validateSingleRoute(s, solo);
  if (!motorResult.allowed)
    return motorResult;
  State probe = s.clone();
  auto &copy = probe.units.at(*r.towed);
  copy.movementAllowance = 2;
  copy.movementRemaining = std::min(2, motor.movementRemaining.value_or(0));
  solo.unit = *r.towed;
  const auto artilleryResult = validateSingleRoute(probe, solo);
  if (!artilleryResult.allowed)
    return artilleryResult;
  motorResult.exhaustsMovement =
      motorResult.exhaustsMovement || artilleryResult.exhaustsMovement;
  return motorResult;
}
RouteResult validateFactoryRailRoute(const State &s, const Id &facility,
                                     const std::vector<Id> &path) {
  RouteResult out;
  const auto i = s.facilities.find(facility);
  if (i == s.facilities.end()) {
    out.reason = "Unknown factory";
    return out;
  }
  const auto &f = i->second;
  const auto nation = s.currentNation();
  if (f.type != "minor_factory" && f.type != "medium_factory" &&
      f.type != "major_factory") {
    out.reason = "Only factories may relocate";
    return out;
  }
  if (!hasTech(s, nation, "improved_logistics")) {
    out.reason = "Factory relocation requires Improved Logistics";
    return out;
  }
  if (path.size() < 2 || path.front() != f.zone ||
      std::any_of(path.begin(), path.end(),
                  [&](const auto &z) { return !inHome(s, nation, z); }) ||
      s.territories.at(f.zone).possessor != nation) {
    out.reason =
        "Factory relocation must remain inside its possessed Home Country";
    return out;
  }
  if (flag(f.flags, "placed_this_turn") || flag(f.flags, "moved_this_turn") ||
      flag(f.flags, "researched_this_turn") ||
      flag(f.flags, "under_construction")) {
    out.reason = "Factory was placed, moved or used for technology this turn";
    return out;
  }
  for (const auto &[id, repair] : s.repairs)
    if (repair.target == facility) {
      out.reason = "Factory is committed to repair";
      return out;
    }
  for (const auto &[id, project] : s.construction)
    if (flag(project.flags, "target:" + facility)) {
      out.reason = "Factory is committed to an upgrade";
      return out;
    }
  auto probe = s.clone();
  Id proxy = "__factory_relocation_probe";
  while (probe.units.contains(proxy))
    proxy += "_";
  UnitState u;
  u.id = proxy;
  u.type = "infantry";
  u.owner = nation;
  u.zone = u.turnOrigin = f.zone;
  u.movementAllowance = u.movementRemaining = 0;
  probe.units.emplace(proxy, std::move(u));
  out = validateRoute(probe, {proxy, path, MovementMode::StrategicRail, false});
  if (!out.allowed)
    return out;
  const int cost = f.type == "major_factory" ? 2 : 1;
  for (const auto &region : out.regions) {
    const auto used =
        s.nations.at(nation).turnFlags.find(railCounter(s, region));
    const int spent =
        used == s.nations.at(nation).turnFlags.end() ? 0 : used->second;
    if (spent + cost > regionalRailCapacity(region) + 1) {
      out.allowed = false;
      out.reason = "Factory exceeds remaining regional rail capacity";
      return out;
    }
  }
  out.cost = cost;
  return out;
}

std::vector<Id> navalFacilitySeaZones(const State &s, const Id &id) {
  const auto &f = s.facilities.at(id);
  std::set<Id> out;
  const auto *metadata = s.definition->geography.find("facilities");
  const auto *spec = metadata ? metadata->find(id) : nullptr;
  if (spec)
    if (const auto *accesses = spec->find("sea_accesses"))
      for (const auto &x : accesses->asArray())
        if (s.definition->geography.require("nodes").find(x.asString()))
          out.insert(x.asString());
  for (const auto &[k, v] : f.flags)
    if (v && k.rfind("border:", 0) == 0) {
      const auto zone = k.substr(7);
      const auto *n = s.definition->geography.require("nodes").find(zone);
      if (n && n->require("type").asString() == "sea")
        out.insert(zone);
    }
  if (out.empty())
    for (const auto &e : node(s, f.zone).require("neighbors").asArray())
      if (const auto *ids = e.find("naval_facility_ids"))
        for (const auto &x : ids->asArray())
          if (x.asString() == id)
            out.insert(e.require("neighbor_id").asString());
  return {out.begin(), out.end()};
}
bool seaBlockaded(const State &s, const Id &nation, const Id &sea) {
  std::map<Id, int> count;
  for (const auto &[id, u] : s.units)
    if (u.zone == sea && unitClass(s, u, "surface_warship") &&
        s.nations.at(u.owner).alliance)
      ++count[*s.nations.at(u.owner).alliance];
  for (const auto &[alliance, n] : count)
    if (n >= 3) {
      bool enemy = false, opposed = false;
      for (const auto &[id, u] : s.units)
        if (u.zone == sea && unitClass(s, u, "surface_warship") &&
            s.nations.at(u.owner).alliance == alliance)
          enemy |= hostile(s, nation, u.owner);
      if (!enemy)
        continue;
      for (const auto &[id, u] : s.units)
        if (u.zone == sea && unitClass(s, u, "surface_warship") &&
            s.nations.at(u.owner).alliance != alliance) {
          for (const auto &[oid, other] : s.units)
            if (other.zone == sea && unitClass(s, other, "surface_warship") &&
                s.nations.at(other.owner).alliance == alliance &&
                hostile(s, other.owner, u.owner))
              opposed = true;
        }
      if (!opposed)
        return true;
    }
  return false;
}
bool facilityBlockaded(const State &s, const Id &nation, const Id &facility) {
  const auto seas = navalFacilitySeaZones(s, facility);
  return !seas.empty() &&
         std::all_of(seas.begin(), seas.end(),
                     [&](const auto &z) { return seaBlockaded(s, nation, z); });
}
bool navalFacilityUsable(const State &s, const Id &nation, const Id &id,
                         bool held) {
  const auto i = s.facilities.find(id);
  if (i == s.facilities.end() || !navalFacilityType(i->second.type) ||
      i->second.damage > 0)
    return false;
  const auto &f = i->second;
  const auto owner = s.territories.at(f.zone).possessor;
  if (!owner || !logisticsFriendly(s, nation, *owner))
    return false;
  if (held &&
      (!heldSinceTurnStart(s, nation, f.zone) ||
       flag(f.flags, "placed_this_turn") || !continuousInfrastructure(s, id)))
    return false;
  return !navalFacilitySeaZones(s, id).empty() &&
         !facilityBlockaded(s, nation, id);
}

namespace {
SupplyRoute traceSupply(const State &s, const Id &nation, const Id &destination,
                        const std::optional<Id> &recipient, bool navalUnit) {
  SupplyRoute none;
  if (!s.definition->factions.contains(nation) ||
      !s.definition->geography.require("nodes").find(destination))
    return none;
  auto permittedLand = [&](const Id &zone) {
    if (heldSinceTurnStart(s, nation, zone))
      return true;
    return recipient && zone == destination &&
           heldSinceTurnStart(s, *recipient, zone, false);
  };
  auto landPaths = [&](const std::vector<Id> &starts) {
    std::map<Id, std::vector<Id>> paths;
    std::deque<Id> todo;
    for (const auto &z : starts)
      if (permittedLand(z)) {
        paths[z] = {z};
        todo.push_back(z);
      }
    while (!todo.empty()) {
      const auto z = todo.front();
      todo.pop_front();
      if (navalUnit)
        continue;
      // A delivered lend-lease stops upon reaching recipient Home Country.
      if (recipient && s.territories.at(z).possessor == *recipient &&
          (inHome(s, *recipient, z) ||
           (*recipient == "dadao" && nation == "japan" &&
            chineseHomeCountry(s, z))))
        continue;
      std::set<Id> adjacent;
      for (const auto &e : node(s, z).require("neighbors").asArray())
        if (s.territories.contains(e.require("neighbor_id").asString()))
          adjacent.insert(e.require("neighbor_id").asString());
      for (const auto &[id, r] : s.rails)
        if (r.endpointA == z)
          adjacent.insert(r.endpointB);
        else if (r.endpointB == z)
          adjacent.insert(r.endpointA);
      for (const auto &next : adjacent)
        if (!paths.contains(next) && permittedLand(next) &&
            (railUndamaged(s, z, next, true) ||
             riverRouteAvailable(s, nation, z, next))) {
          paths[next] = paths.at(z);
          paths[next].push_back(next);
          todo.push_back(next);
        }
    }
    return paths;
  };
  auto usable = [&](const Id &id) {
    if (navalFacilityUsable(s, nation, id))
      return true;
    if (!recipient)
      return false;
    const auto &f = s.facilities.at(id);
    return f.zone == destination &&
           s.territories.at(f.zone).possessor == *recipient &&
           navalFacilityType(f.type) && !f.damage &&
           heldSinceTurnStart(s, *recipient, f.zone, false) &&
           !flag(f.flags, "placed_this_turn") &&
           continuousInfrastructure(s, id) &&
           !navalFacilitySeaZones(s, id).empty() &&
           !facilityBlockaded(s, *recipient, id);
  };
  std::vector<Id> homes;
  for (const auto &home : s.definition->factions.at(nation).homeCountry)
    if (s.territories.contains(home) &&
        heldSinceTurnStart(s, nation, home, false))
      homes.push_back(home);
  const auto initial = landPaths(homes);
  if (initial.contains(destination))
    return {true, initial.at(destination), {}};
  struct PortVisit {
    Id facility;
    std::vector<Id> zones;
    std::vector<Id> facilities;
  };
  std::deque<PortVisit> ports;
  std::set<Id> visitedPorts;
  for (const auto &[id, f] : s.facilities)
    if (initial.contains(f.zone) && usable(id)) {
      ports.push_back({id, initial.at(f.zone), {id}});
      visitedPorts.insert(id);
    }
  while (!ports.empty()) {
    auto port = std::move(ports.front());
    ports.pop_front();
    const auto &origin = s.facilities.at(port.facility);
    struct SeaVisit {
      Id sea;
      int distance;
      std::vector<Id> path;
    };
    std::deque<SeaVisit> seas;
    std::set<Id> visitedSeas;
    auto starts = navalFacilitySeaZones(s, port.facility);
    if (!port.zones.empty() && !s.territories.contains(port.zones.back()))
      starts = {port.zones.back()};
    for (const auto &sea : starts)
      if (!seaBlockaded(s, nation, sea)) {
        auto path = port.zones;
        if (path.empty() || path.back() != sea)
          path.push_back(sea);
        seas.push_back({sea, 0, std::move(path)});
        visitedSeas.insert(sea);
      }
    while (!seas.empty()) {
      auto sea = std::move(seas.front());
      seas.pop_front();
      if (sea.sea == destination)
        return {true, sea.path, port.facilities};
      for (const auto &[id, f] : s.facilities)
        if (id != port.facility && usable(id)) {
          const auto accesses = navalFacilitySeaZones(s, id);
          if (std::find(accesses.begin(), accesses.end(), sea.sea) ==
              accesses.end())
            continue;
          const auto afterLandfall = landPaths({f.zone});
          if (afterLandfall.contains(destination)) {
            auto path = sea.path;
            const auto &land = afterLandfall.at(destination);
            path.insert(path.end(), land.begin(), land.end());
            auto facilities = port.facilities;
            facilities.push_back(id);
            return {true, path, facilities};
          }
          // Refresh while the path remains at sea; landfall is considered
          // only by the terminal land search above. A shortest path never
          // needs to revisit the same refreshing facility.
          if (navalFacilityUsable(s, nation, id) &&
              visitedPorts.insert(id).second) {
            auto facilities = port.facilities;
            facilities.push_back(id);
            ports.push_back({id, sea.path, std::move(facilities)});
          }
        }
      if (sea.distance >=
          navalRange(origin) +
              (hasTech(s, nation, "improved_logistics") ? 1 : 0))
        continue;
      for (const auto &e : node(s, sea.sea).require("neighbors").asArray()) {
        const auto next = e.require("neighbor_id").asString();
        if (s.territories.contains(next) ||
            !s.definition->geography.require("nodes").find(next) ||
            seaBlockaded(s, nation, next) || !visitedSeas.insert(next).second)
          continue;
        auto path = sea.path;
        path.push_back(next);
        seas.push_back({next, sea.distance + 1, std::move(path)});
      }
    }
  }
  return none;
}
} // namespace
SupplyRoute supplyRoute(const State &s, const Id &nation,
                        const Id &destination) {
  return traceSupply(s, nation, destination, std::nullopt, false);
}
SupplyRoute lendLeaseSupplyRoute(const State &s, const Id &sender,
                                 const Id &recipient, const Id &destination,
                                 bool navalUnit) {
  if (!s.nations.contains(recipient) || !s.territories.contains(destination) ||
      s.territories.at(destination).possessor != recipient)
    return {};
  const bool dadao = recipient == "dadao" && sender == "japan" &&
                     chineseHomeCountry(s, destination);
  if (!dadao && !inHome(s, recipient, destination))
    return {};
  return traceSupply(s, sender, destination, recipient, navalUnit);
}
bool inSupply(const State &s, const Id &nation, const Id &zone) {
  return supplyRoute(s, nation, zone).connected;
}
bool burmaRoadOpen(const State &s, bool ledo) {
  const auto date = s.calendarDate();
  if (date.first * 100 + date.second < 193807 || !s.nations.contains("japan") ||
      !s.nations.contains("kmt") || !hostile(s, "kmt", "japan"))
    return false;
  auto allied = [&](const Id &z) {
    const auto i = s.territories.find(z);
    return i != s.territories.end() && i->second.possessor &&
           s.nations.at(*i->second.possessor).alliance == "allies";
  };
  const auto y = s.territories.find("land_china_yunnan");
  return y != s.territories.end() && y->second.possessor == "kmt" &&
         allied("land_burma") && (!ledo || allied("land_bengal"));
}
bool ccpSovietRailConnected(const State &s, const Id &zone) {
  if (!s.nations.contains("ussr") || !s.territories.contains(zone) ||
      s.territories.at(zone).possessor != "ccp")
    return false;
  std::deque<Id> todo{zone};
  std::set<Id> seen;
  while (!todo.empty()) {
    const auto z = todo.front();
    todo.pop_front();
    if (!seen.insert(z).second)
      continue;
    if (s.territories.at(z).possessor == "ussr")
      return true;
    for (const auto &[id, r] : s.rails) {
      Id next;
      if (r.endpointA == z)
        next = r.endpointB;
      else if (r.endpointB == z)
        next = r.endpointA;
      else
        continue;
      if (!s.territories.at(next).possessor ||
          (*s.territories.at(next).possessor != "ccp" &&
           *s.territories.at(next).possessor != "ussr"))
        continue;
      if (railUndamaged(s, z, next))
        todo.push_back(next);
    }
  }
  return false;
}
std::set<Id> withdrawalEligibleRecipients(const State &s, const Id &attacker,
                                          const Id &zone) {
  std::set<Id> recipients;
  if (!s.territories.contains(zone) || !movementController(s, attacker))
    return recipients;
  State probe = s.clone();
  probe.clock.phase = Phase::NonCombatMovement;
  std::vector<Id> needTransport;
  for (const auto &[id, u] : s.units)
    if (u.owner == attacker &&
        (u.zone == zone || flag(u.turnFlags, "must_withdraw_from_chinese_gift")) && !u.carriedBy &&
        unitClass(s, u, "land")) {
      auto &p = probe.units.at(id);
      p.turnFlags["must_withdraw_from_chinese_gift"] = 1;
      bool canLeave = false;
      std::function<void(std::vector<Id>)> search = [&](std::vector<Id> path) {
        if (canLeave)
          return;
        if (path.size() > 1) {
          RouteRequest r{id, path, MovementMode::Ordinary, false};
          if (!validateRoute(probe, r).allowed)
            return;
          canLeave = true;
          return;
        }
        for (const auto &e :
             node(s, path.back()).require("neighbors").asArray())
          if (s.territories.contains(e.require("neighbor_id").asString())) {
            auto next = path;
            next.push_back(e.require("neighbor_id").asString());
            search(std::move(next));
          }
      };
      search({u.zone});
      if (!canLeave)
        needTransport.push_back(id);
    }
  // Use the same loading permission as the eventual executable action. A
  // nearby ship's nominal capacity is insufficient if it already unloaded,
  // the conquering cargo cannot move again, or a national cargo rule forbids it.
  std::map<Id, std::vector<Id>> candidates;
  std::set<Id> ships;
  for (const auto &cargo : needTransport) {
    for (const auto &[ship, u] : probe.units)
      if (unitClass(probe, u, "naval") && navalLoadAllowed(probe, ship, cargo)) {
        candidates[cargo].push_back(ship);
        ships.insert(ship);
      }
    if (candidates[cargo].empty()) return recipients;
  }
  std::stable_sort(needTransport.begin(), needTransport.end(), [&](const Id &a, const Id &b) {
    return candidates.at(a).size() < candidates.at(b).size();
  });
  std::set<std::string> failed;
  std::function<bool(std::size_t)> assign = [&](std::size_t index) {
    if (index == needTransport.size()) return true;
    O loads;
    for (const auto &ship : ships) {
      std::vector<Id> types;
      for (const auto &cargo : probe.units.at(ship).cargo) types.push_back(probe.units.at(cargo).type);
      std::sort(types.begin(), types.end());
      A entries;
      for (const auto &type : types) entries.emplace_back(type);
      loads.emplace(ship, V(std::move(entries)));
    }
    const auto key = std::to_string(index) + canonicalJson(V(std::move(loads)));
    if (failed.contains(key)) return false;
    const auto &cargo = needTransport[index];
    for (const auto &ship : candidates.at(cargo)) {
      if (!navalLoadAllowed(probe, ship, cargo)) continue;
      const auto origin = probe.units.at(cargo).zone;
      attachCargo(probe, ship, cargo);
      if (assign(index + 1)) return true;
      detachCargo(probe, ship, cargo, origin);
    }
    failed.insert(key);
    return false;
  };
  if (!assign(0)) return recipients;
  for (const auto &china : {"ccp", "kmt"})
    if (s.nations.contains(china) && !s.politics.surrendered.contains(china))
      recipients.insert(china);
  return recipients;
}
void attachCargo(State &s, const Id &transport, const Id &cargo) {
  auto &t = s.units.at(transport);
  auto &c = s.units.at(cargo);
  require(transport != cargo && !t.carriedBy && !c.carriedBy && c.cargo.empty(),
          "Cargo attachment would nest transports or duplicate cargo");
  require(std::find(t.cargo.begin(), t.cargo.end(), cargo) == t.cargo.end(),
          "Cargo is already attached");
  c.carriedBy = transport;
  c.zone = t.zone;
  t.cargo.push_back(cargo);
}
void detachCargo(State &s, const Id &transport, const Id &cargo,
                 const Id &destination) {
  auto &t = s.units.at(transport);
  auto &c = s.units.at(cargo);
  require(c.carriedBy == transport, "Cargo is not on this transport");
  c.carriedBy.reset();
  c.zone = destination;
  t.cargo.erase(std::remove(t.cargo.begin(), t.cargo.end(), cargo),
                t.cargo.end());
}

MovementRules::MovementRules(std::shared_ptr<const Rules> gameplay)
    : gameplay_(std::move(gameplay)) {}
Id MovementRules::id() const {
  return "gw36_v43_m5_movement" + (gameplay_ ? "+" + gameplay_->id() : "");
}
std::vector<Action> MovementRules::actions(const State &s) const {
  auto out = gameplay_ ? gameplay_->actions(s) : std::vector<Action>{};
  if (!s.decisions.empty() || s.chance)
    return out;
  const bool combat = s.clock.phase == Phase::CombatMovement;
  const bool blitz = s.clock.phase == Phase::Combat;
  if (!combat && !blitz && s.clock.phase != Phase::NonCombatMovement)
    return out;
  for (const auto &[id, u] : s.units)
    if (movementController(s, u.owner) && !u.carriedBy &&
        s.territories.contains(u.zone)) {
      if (unitClass(s, u, "land")) {
        std::function<void(std::vector<Id>)> visit = [&](std::vector<Id> path) {
          if (path.size() > 1) {
            RouteRequest r{id, path,
                           blitz ? MovementMode::Blitz : MovementMode::Ordinary,
                           combat || blitz};
            if (validateRoute(s, r).allowed) {
              out.push_back(movementAction(s, r));
              if (u.type == "motorized_infantry" && !blitz)
                for (const auto &[partner, towed] : s.units)
                  if (partner != id && towed.zone == u.zone &&
                      towed.owner == u.owner) {
                    auto tow = r;
                    tow.towed = partner;
                    if (validateRoute(s, tow).allowed)
                      out.push_back(movementAction(s, tow));
                  }
            } else
              return;
          }
          if (path.size() >
              static_cast<std::size_t>(u.movementRemaining.value_or(0)))
            return;
          for (const auto &e :
               node(s, path.back()).require("neighbors").asArray()) {
            const auto next = e.require("neighbor_id").asString();
            if (!s.territories.contains(next) ||
                std::find(path.begin(), path.end(), next) != path.end())
              continue;
            auto nextPath = path;
            nextPath.push_back(next);
            visit(std::move(nextPath));
          }
        };
        visit({u.zone});
        if (!blitz)
          for (const auto &e : node(s, u.zone).require("neighbors").asArray())
            if (narrow(&e)) {
              RouteRequest r{id,
                             {u.zone, e.require("neighbor_id").asString()},
                             MovementMode::NarrowCrossing,
                             combat};
              if (validateRoute(s, r).allowed)
                out.push_back(movementAction(s, r));
            }
      }
      if (!combat && !blitz) {
        std::deque<std::vector<Id>> todo{{u.zone}};
        std::set<Id> seen{u.zone};
        while (!todo.empty()) {
          auto path = std::move(todo.front());
          todo.pop_front();
          const auto last = path.back();
          std::set<Id> adjacent;
          for (const auto &e : node(s, last).require("neighbors").asArray())
            if (s.territories.contains(e.require("neighbor_id").asString()))
              adjacent.insert(e.require("neighbor_id").asString());
          for (const auto &[rid, r] : s.rails)
            if (r.endpointA == last)
              adjacent.insert(r.endpointB);
            else if (r.endpointB == last)
              adjacent.insert(r.endpointA);
          for (const auto &next : adjacent)
            if (!seen.contains(next)) {
              auto p = path;
              p.push_back(next);
              RouteRequest r{id, p, MovementMode::StrategicRail, false};
              if (validateRoute(s, r).allowed) {
                seen.insert(next);
                out.push_back(movementAction(s, r));
                todo.push_back(std::move(p));
              }
            }
        }
      }
    }
  if (!combat && !blitz && hasTech(s, s.currentNation(), "improved_logistics"))
    for (const auto &[id, f] : s.facilities)
      if (f.type == "minor_factory" || f.type == "medium_factory" ||
          f.type == "major_factory") {
        std::deque<std::vector<Id>> todo{{f.zone}};
        std::set<Id> seen{f.zone};
        while (!todo.empty()) {
          auto path = std::move(todo.front());
          todo.pop_front();
          for (const auto &e :
               node(s, path.back()).require("neighbors").asArray()) {
            const auto next = e.require("neighbor_id").asString();
            if (!s.territories.contains(next) || seen.contains(next))
              continue;
            auto p = path;
            p.push_back(next);
            const auto result = validateFactoryRailRoute(s, id, p);
            if (!result.allowed)
              continue;
            seen.insert(next);
            todo.push_back(p);
            A encoded;
            for (const auto &z : p)
              encoded.emplace_back(z);
            V params(O{{"facility", V(id)}, {"path", V(std::move(encoded))}});
            out.push_back(
                {"factory_rail_" + contentDigest(canonicalJson(params)),
                 "movement_factory_rail", politicalPlayer(s, s.currentNation()),
                 s.currentNation(), std::nullopt, std::move(params)});
          }
        }
      }
  if (s.clock.phase == Phase::NonCombatMovement) {
    const bool withdrawalPending = std::any_of(s.units.begin(), s.units.end(), [&](const auto &item) {
      return movementController(s, item.second.owner) &&
             flag(item.second.turnFlags, "must_withdraw_from_chinese_gift");
    });
    if (withdrawalPending)
      out.erase(std::remove_if(out.begin(), out.end(), [&](const Action &a) {
        // Finish mandatory withdrawals before optional moves can consume their
        // proven transport capacity. Required aircraft returns remain available.
        if (a.kind == "air_land" || a.kind == "air_end_patrol") return false;
        if (a.kind != "movement_route" && a.kind != "naval_load") return true;
        const auto *unit = a.parameters.find("unit");
        return !unit || !s.units.contains(unit->asString()) ||
               !flag(s.units.at(unit->asString()).turnFlags, "must_withdraw_from_chinese_gift");
      }), out.end());
  }
  return out;
}
std::vector<Action> MovementRules::interrupts(const State &s) const {
  auto out = gameplay_ ? gameplay_->interrupts(s) : std::vector<Action>{};
  if (s.clock.phase != Phase::NonCombatMovement || !s.decisions.empty() ||
      s.chance)
    return out;
  const auto active = s.currentNation();
  for (const auto &[owner, n] : s.nations)
    if (owner != active && politicallyFriendly(s, owner, active) &&
        !flag(n.turnFlags, "rail_permission:" + active)) {
      V p(O{{"requester", V(active)}});
      out.push_back({"rail_permission_" + owner + "_" + active,
                     "movement_grant_rail", politicalPlayer(s, owner), owner,
                     std::nullopt, p});
    }
  return out;
}
bool MovementRules::phaseComplete(const State &s) const {
  if (s.clock.phase == Phase::NonCombatMovement)
    for (const auto &[id, u] : s.units)
      if (movementController(s, u.owner) &&
          flag(u.turnFlags, "must_withdraw_from_chinese_gift"))
        return false;
  return !gameplay_ || gameplay_->phaseComplete(s);
}
void MovementRules::apply(State &s, const Action &a) const {
  if (a.kind == "movement_grant_rail") {
    s.nations.at(a.nation)
        .turnFlags["rail_permission:" +
                   a.parameters.require("requester").asString()] = 1;
    return;
  }
  if (a.kind == "movement_factory_rail") {
    const auto id = a.parameters.require("facility").asString();
    std::vector<Id> path;
    for (const auto &z : a.parameters.require("path").asArray())
      path.push_back(z.asString());
    const auto result = validateFactoryRailRoute(s, id, path);
    require(result.allowed, result.reason);
    for (const auto &region : result.regions)
      s.nations.at(s.currentNation()).turnFlags[railCounter(s, region)] +=
          result.cost;
    auto &f = s.facilities.at(id);
    f.zone = path.back();
    f.flags["moved_this_turn"] = 1;
    return;
  }
  if (a.kind != "movement_route") {
    require(bool(gameplay_), "Unknown movement action");
    gameplay_->apply(s, a);
    return;
  }
  const auto r = requestFrom(a);
  const auto result = validateRoute(s, r);
  require(result.allowed, result.reason);
  auto &u = s.units.at(r.unit);
  require(u.owner == a.nation, "Movement action owner mismatch");
  const auto owner = u.owner;
  const auto from = u.zone;
  if (r.towed) {
    auto &artillery = s.units.at(*r.towed);
    const int remaining = std::min(2, u.movementRemaining.value_or(0));
    artillery.movementAllowance = 2;
    artillery.movementRemaining =
        result.exhaustsMovement ? 0 : remaining - result.cost;
    for (std::size_t i = 1; i < r.path.size(); ++i)
      artillery.route.push_back(r.path[i]);
    artillery.zone = r.path.back();
    artillery.commitments.insert("towed_by:" + r.unit);
    u.commitments.insert("towing:" + *r.towed);
    if (r.combat)
      artillery.commitments.insert("combat_move");
  }
  const auto target = r.path.back();
  if (r.mode == MovementMode::StrategicRail ||
      r.mode == MovementMode::StrategicRiver) {
    for (const auto &region : result.regions)
      ++s.nations.at(s.currentNation()).turnFlags[railCounter(s, region)];
    u.turnFlags["strategic_moved"] = 1;
  }
  if (r.mode == MovementMode::NarrowCrossing) {
    ++s.flags[crossingCounter(*edge(s, from, target), from, target)];
    if (r.combat)
      u.commitments.insert("amphibious_assault");
  }
  if (r.mode == MovementMode::Blitz) {
    u.turnFlags.erase("blitz_eligible");
    u.commitments.insert("blitz_from:" + from);
    u.commitments.insert("blitz_to:" + target);
  }
  const auto possessor = s.territories.at(target).possessor;
  const bool attack =
      r.combat && (!possessor || (*possessor != owner &&
                                  !politicallyFriendly(s, owner, *possessor)));
  for (std::size_t i = 1; i < r.path.size(); ++i)
    u.route.push_back(r.path[i]);
  u.zone = target;
  for (const auto &id : u.cargo)
    s.units.at(id).zone = target;
  u.movementRemaining =
      result.exhaustsMovement ? 0 : *u.movementRemaining - result.cost;
  if (r.combat)
    u.commitments.insert("combat_move");
  if (flag(u.turnFlags, "must_withdraw_from_chinese_gift"))
    u.turnFlags.erase("must_withdraw_from_chinese_gift");
  if (attack) {
    recordLandAttack(s, owner, target);
    std::vector<Id> attackers{r.unit};
    std::map<Id, Id> origins{{r.unit, r.path[r.path.size() - 2]}};
    if (r.towed) {
      attackers.push_back(*r.towed);
      origins[*r.towed] = r.path[r.path.size() - 2];
    }
    registerLandBattle(s, target, owner, attackers, origins);
  }
}
void MovementRules::applyChance(State &s, const ChanceRequest &r,
                                const ChanceOutcome &o) const {
  require(bool(gameplay_), "Unknown movement chance request");
  gameplay_->applyChance(s, r, o);
}
void MovementRules::finishTurn(State &s) const {
  require(bool(gameplay_), "Movement module requires income accounting");
  gameplay_->finishTurn(s);
}
void MovementRules::beginTurn(State &s) const {
  for (auto &[id, n] : s.nations)
    if (movementController(s, id))
      n.gameFlags["logistics_last_turn_start"] =
          static_cast<int>(s.clock.playerTurnSerial + 1);
  for (auto it = s.flags.begin(); it != s.flags.end();)
    if (it->first.rfind("crossing_used:", 0) == 0 ||
        it->first.rfind("logistics_start_damaged:", 0) == 0)
      it = s.flags.erase(it);
    else
      ++it;
  for (const auto &[id, f] : s.facilities)
    s.flags["logistics_start_damaged:" + id] = f.damage;
  for (const auto &[id, r] : s.rails) {
    int damage = 0;
    for (const auto &[zone, d] : r.damageByEndpoint)
      damage += d;
    s.flags["logistics_start_damaged:" + id] = damage;
  }
  for (auto &[id, n] : s.nations)
    for (auto it = n.turnFlags.begin(); it != n.turnFlags.end();)
      if (it->first.rfind("rail_permission:", 0) == 0)
        it = n.turnFlags.erase(it);
      else
        ++it;
  if (gameplay_)
    gameplay_->beginTurn(s);
}
void MovementRules::finishPhase(State &s) const {
  if (gameplay_)
    gameplay_->finishPhase(s);
}
} // namespace game::campaign
