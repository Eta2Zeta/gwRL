#include "game/air.hpp"
#include "game/catalog.hpp"
#include "game/naval.hpp"
#include "game/politics.hpp"
#include "game/position_facts.hpp"

#include <algorithm>
#include <deque>
#include <functional>
#include <stdexcept>

namespace game::campaign {
namespace {
using V = json::Value;
using O = V::Object;
using A = V::Array;
// Builds the message only on failure; most messages are literals.
template <class Message> void require(bool ok, const Message &why) {
  if (!ok)
    throw std::runtime_error(why);
}
V number(int n) { return V(static_cast<double>(n)); }
bool marked(const std::map<Id, int> &flags, const Id &key) {
  auto i = flags.find(key);
  return i != flags.end() && i->second;
}
int value(const std::map<Id, int> &flags, const Id &key) {
  auto i = flags.find(key);
  return i == flags.end() ? 0 : i->second;
}
bool has(const State &s, const UnitState &u, const Id &cls) {
  return unitClass(s, u, cls);
}
bool hostile(const State &s, const Id &n, const Id &other) {
  return n != other && s.nations.at(n).atWarWith.contains(other);
}
bool sea(const State &s, const Id &zone) {
  const auto *n = findMapNode(s, zone);
  return n && n->require("type").asString() == "sea";
}
bool adjacent(const State &s, const Id &a, const Id &b) {
  const auto *e = mapEdge(s, a, b);
  return e && (!e->find("passable") || e->require("passable").asBool());
}
bool tech(const State &s, const Id &n, const Id &id) {
  return value(s.nations.at(n).technologyStages, id) == 4;
}
A ids(const std::vector<Id> &units) {
  A a;
  for (const auto &id : units)
    a.emplace_back(id);
  return a;
}
std::vector<Id> readIds(const V &v) {
  std::vector<Id> out;
  for (const auto &x : v.asArray())
    out.push_back(x.asString());
  return out;
}
O object(const BattleState &b) { return b.data.asObject(); }
void put(BattleState &b, const Id &key, V v) {
  auto o = object(b);
  o[key] = std::move(v);
  b.data = V(std::move(o));
}
Id text(const BattleState &b, const Id &key, const Id &fallback = {}) {
  const auto *v = b.data.find(key);
  return v ? v->asString() : fallback;
}
Id port(const UnitState &u) {
  for (const auto &[key, v] : u.gameFlags)
    if (v && key.rfind("in_port:", 0) == 0)
      return key.substr(8);
  return {};
}
bool patrol(const UnitState &u) {
  return marked(u.gameFlags, "on_map") || marked(u.turnFlags, "on_map") ||
         u.commitments.contains("maritime_air_patrol");
}
bool carrierPatrol(const State &s, const UnitState &u) {
  return isAircraft(s, u) && u.carriedBy && s.units.contains(*u.carriedBy) &&
         has(s, s.units.at(*u.carriedBy), "carrier");
}
bool submerged(const State &s, const UnitState &u) {
  return has(s, u, "submarine") &&
         (marked(u.turnFlags, "submerged") || marked(u.gameFlags, "submerged"));
}
bool raider(const UnitState &u) {
  return marked(u.gameFlags, "raider") || marked(u.gameFlags, "naval_raider");
}
bool escort(const UnitState &u) {
  return marked(u.gameFlags, "escort") || marked(u.gameFlags, "naval_escort");
}
std::vector<Id> live(const State &s, const std::vector<Id> &units) {
  std::vector<Id> out;
  for (const auto &id : units)
    if (s.units.contains(id))
      out.push_back(id);
  return out;
}
Action action(const State &s, const Id &n, const Id &kind, O parameters = {}) {
  Action a;
  a.kind = kind;
  a.nation = n;
  a.player = politicalPlayer(s, n);
  a.parameters = V(std::move(parameters));
  a.id = kind + "_" + contentDigest(canonicalJson(a.parameters)).substr(0, 20);
  return a;
}
void decision(State &s, BattleState &b, const Id &n, const Id &kind,
              std::vector<Action> options) {
  require(!options.empty(), "Empty naval movement decision");
  Decision d;
  d.id =
      b.id + "_decision_" + std::to_string(++s.flags["naval_move_decisions"]);
  d.nation = n;
  d.kind = kind;
  d.continuation = b.id;
  d.reaction = n != s.currentNation();
  for (auto &a : options)
    a.decision = d.id;
  d.options = std::move(options);
  s.decisions.push_back(std::move(d));
}
void release(State &s, const Action &a) {
  require(a.decision && !s.decisions.empty() &&
              s.decisions.back().id == a.decision,
          "Missing naval movement decision");
  s.decisions.pop_back();
}
void refreshImmediate(State &s) {
  bool pending = false;
  for (const auto &[id, b] : s.battles)
    if (marked(b.flags, "naval_movement_immediate") &&
        !marked(b.flags, "finished"))
      pending = true;
  if (pending)
    s.flags["immediate_naval_battles"] = 1;
  else
    s.flags.erase("immediate_naval_battles");
}
void erasePlan(State &s, const Id &id) {
  const auto removed = id;
  s.battles.erase(removed);
  std::erase(s.battleOrder, removed);
  refreshImmediate(s);
}
NavalRouteRequest readRequest(const V &v) {
  NavalRouteRequest r;
  r.units = readIds(v.require("units"));
  r.path = readIds(v.require("path"));
  r.combat = v.require("combat").asBool();
  r.strategic = v.require("strategic").asBool();
  if (auto f = v.find("origin_facility"); f && !f->isNull())
    r.originFacility = f->asString();
  if (auto f = v.find("destination_facility"); f && !f->isNull())
    r.destinationFacility = f->asString();
  return r;
}
V requestJson(const NavalRouteRequest &r) {
  return V(O{
      {"units", V(ids(r.units))},
      {"path", V(ids(r.path))},
      {"combat", V(r.combat)},
      {"strategic", V(r.strategic)},
      {"origin_facility", r.originFacility ? V(*r.originFacility) : V(nullptr)},
      {"destination_facility",
       r.destinationFacility ? V(*r.destinationFacility) : V(nullptr)}});
}
std::vector<Id> seasAt(const State &s, const Id &id) {
  if (!port(s.units.at(id)).empty())
    return navalFacilitySeaZones(s, port(s.units.at(id)));
  return {s.units.at(id).zone};
}
bool atSeaStart(const State &s, const UnitState &u, const Id &z) {
  if (port(u).empty())
    return u.zone == z;
  const auto access = navalFacilitySeaZones(s, port(u));
  return std::find(access.begin(), access.end(), z) != access.end();
}
bool available(const State &s, const UnitState &u, bool combat) {
  if (s.clock.phase == Phase::Combat &&
      (!marked(u.turnFlags, "naval_screening_continuing") ||
       u.commitments.contains("naval_combat")))
    return false;
  for (const auto &[id, b] : s.battles)
    if (marked(b.flags, "naval_battle") && !marked(b.flags, "finished") &&
        (std::find(b.attackers.begin(), b.attackers.end(), u.id) !=
             b.attackers.end() ||
         std::find(b.defenders.begin(), b.defenders.end(), u.id) !=
             b.defenders.end()))
      return false;
  if (!has(s, u, "naval") || !movementController(s, u.owner) || u.carriedBy ||
      marked(u.turnFlags, "placed_this_turn") ||
      marked(u.turnFlags, "repairing") || u.commitments.contains("repair") ||
      (marked(u.gameFlags, "skeleton_crew") ||
       u.gameFlags.contains("skeleton_crew_until_own_turn")) ||
      marked(u.turnFlags, "naval_unloaded") ||
      marked(u.turnFlags, "naval_strategic_moved"))
    return false;
  if (!combat && u.commitments.contains("combat_move"))
    return false;
  const auto p = port(u);
  return p.empty() ||
         (s.facilities.contains(p) && s.facilities.at(p).damage == 0);
}
int allowanceNow(const State &s, const UnitState &u, bool combat,
                 const Id &target, const Id &routeStart) {
  int total =
      catalogStats(s, u.type, u.damage, u.owner, u.zone).movement.value_or(0);
  Id start = u.turnOrigin;
  if (!sea(s, start)) {
    for (const auto &[key, v] : u.turnFlags)
      if (v && key.rfind("naval_start_sea:", 0) == 0)
        start = key.substr(16);
    if (!sea(s, start)) {
      const auto access = seasAt(s, u.id);
      start = !routeStart.empty() ? routeStart
              : access.empty()    ? Id{}
                                  : access.front();
    }
  }
  bool facilityBonus = false;
  for (const auto &[id, f] : s.facilities) {
    const bool type = has(s, u, "submarine") ? f.type == "submarine_base"
                                             : f.type == "major_port" ||
                                                   f.type == "major_dockyard" ||
                                                   f.type == "major_shipyard";
    if (!type || f.damage || marked(f.flags, "placed_this_turn"))
      continue;
    const auto owner = s.territories.at(f.zone).possessor;
    if (!owner || !politicallyFriendly(s, u.owner, *owner))
      continue;
    const auto access = navalFacilitySeaZones(s, id);
    if (std::find(access.begin(), access.end(), start) != access.end() &&
        inSupply(s, u.owner, f.zone))
      facilityBonus = true;
  }
  if (facilityBonus)
    ++total;
  if (has(s, u, "surface_ship") &&
      s.nations.at(u.owner).powerStatus == "major" && !raider(u) &&
      !start.empty() && !inSupply(s, u.owner, start))
    --total;
  if (u.owner == "japan" && u.type == "destroyer" && !u.cargo.empty())
    --total;
  if (combat && u.owner == "japan" &&
      marked(s.nations.at("japan").turnFlags, "surprise_attack_zone:" + target))
    ++total;
  return std::max(0, total);
}
int allowance(const State &s, const UnitState &u, bool combat, const Id &target,
              const Id &routeStart = {}) {
  // Route validation asks again for every route with the same unit, origin
  // and destination. Reuse the answer only for this position's own unit.
  const auto found = s.units.find(u.id);
  auto *facts = found != s.units.end() && &found->second == &u
                    ? positionFacts(s)
                    : nullptr;
  if (!facts)
    return allowanceNow(s, u, combat, target, routeStart);
  return facts->number(
      PositionFacts::Fact::NavalAllowance,
      u.id + '\n' + target + '\n' + routeStart + (combat ? "\nc" : "\nn"),
      [&] { return allowanceNow(s, u, combat, target, routeStart); });
}
int spent(const State &s, const UnitState &u) {
  return value(u.turnFlags, "naval_movement_spent");
}
std::vector<Id> blockers(const State &s, const Id &n, const Id &z,
                         bool includeOptional = false) {
  std::vector<Id> out;
  for (const auto &[id, u] : s.units)
    if (u.zone == z && !u.carriedBy && hostile(s, n, u.owner) &&
        port(u).empty())
      if ((has(s, u, "surface_warship") &&
           (!raider(u) && !escort(u) || includeOptional)) ||
          (isAircraft(s, u) && patrol(u)))
        out.push_back(id);
  return out;
}
bool anyEnemy(const State &s, const Id &n, const Id &z) {
  for (const auto &[id, u] : s.units)
    if (u.zone == z && !u.carriedBy && hostile(s, n, u.owner) &&
        port(u).empty())
      return true;
  return false;
}
bool passage(const State &s, const UnitState &u, const Id &from, const Id &to,
             bool strategic) {
  const auto *e = mapEdge(s, from, to);
  if (!e)
    return false;
  if (auto p = e->find("closed"); p && p->isBool() && p->asBool()) {
    auto kind = e->find("canal_or_strait");
    return !strategic && has(s, u, "submarine") && kind && kind->isString() &&
           kind->asString() == "strait";
  }
  return !e->find("passable") || e->require("passable").asBool();
}
void detachAircraft(State &s, const std::vector<Id> &fleet, const Id &seaZone) {
  for (const auto &ship : fleet) {
    const auto cargo = s.units.at(ship).cargo;
    for (const auto &id : cargo)
      if (isAircraft(s, s.units.at(id)) &&
          s.units.at(id).owner == s.units.at(ship).owner) {
        detachCargo(s, ship, id, seaZone);
        s.units.at(id).turnFlags["air_in_flight"] = 1;
      }
  }
}
void moveTo(State &s, const std::vector<Id> &fleet, const Id &zone, int cost,
            bool combat) {
  for (const auto &id : fleet)
    if (s.units.contains(id)) {
      auto &u = s.units.at(id);
      if (!port(u).empty())
        u.turnFlags["naval_start_sea:" + zone] = 1;
      if (sea(s, u.zone) && u.zone != zone)
        u.turnFlags["naval_last_origin:" + u.zone] =
            static_cast<int>(s.clock.playerTurnSerial + 1);
      for (auto i = u.gameFlags.begin(); i != u.gameFlags.end();)
        if (i->first.rfind("in_port:", 0) == 0)
          i = u.gameFlags.erase(i);
        else
          ++i;
      u.zone = zone;
      u.route.push_back(zone);
      u.turnFlags["naval_movement_spent"] += cost;
      const int cap = allowance(s, u, combat, zone);
      u.movementAllowance = std::max(cap, spent(s, u));
      u.movementRemaining = std::max(0, cap - spent(s, u));
      if (combat)
        u.commitments.insert("combat_move");
      for (const auto &child : u.cargo)
        s.units.at(child).zone = zone;
    }
}
void routeChoices(State &, BattleState &);
bool canLoad(const State &, const Id &, const Id &);
void continueRoute(State &, const Id &);
void encounter(State &, const Id &);
bool peaceEntryWindow(State &s, BattleState &b, const Id &zone) {
  const auto r = readRequest(b.data.require("request"));
  if (!r.combat || r.strategic)
    return false;
  const auto processed = b.data.find("entry_processed")
                             ? readIds(b.data.require("entry_processed"))
                             : std::vector<Id>{};
  std::set<Id> nations;
  for (const auto &[id, u] : s.units)
    if (u.zone == zone && u.owner != b.attacker &&
        !hostile(s, b.attacker, u.owner) &&
        s.nations.at(u.owner).alliance != s.nations.at(b.attacker).alliance &&
        s.nations.at(u.owner).player &&
        std::find(processed.begin(), processed.end(), u.owner) ==
            processed.end() &&
        (mayDeclareWar(s, b.attacker, u.owner).allowed ||
         mayDeclareWar(s, u.owner, b.attacker).allowed))
      nations.insert(u.owner);
  if (nations.empty())
    return false;
  const auto target = *nations.begin();
  put(b, "entry_nation", V(target));
  put(b, "entry_zone", V(zone));
  std::vector<Action> options;
  if (mayDeclareWar(s, b.attacker, target).allowed)
    options.push_back(
        action(s, b.attacker, "naval_entry_declare", {{"plan", V(b.id)}}));
  options.push_back(
      action(s, b.attacker, "naval_entry_peaceful", {{"plan", V(b.id)}}));
  decision(s, b, b.attacker, "naval_entry_intent", std::move(options));
  return true;
}
void markEntryProcessed(BattleState &b) {
  auto processed = b.data.find("entry_processed")
                       ? readIds(b.data.require("entry_processed"))
                       : std::vector<Id>{};
  processed.push_back(text(b, "entry_nation"));
  put(b, "entry_processed", V(ids(processed)));
}
void resumeEntry(State &s, const Id &plan) {
  auto &b = s.battles.at(plan);
  if (b.data.find("waiting_ports"))
    encounter(s, plan);
  else
    continueRoute(s, plan);
}

void beginBattleFromPlan(State &s, const Id &planId,
                         const std::vector<Id> &attackers,
                         const std::vector<Id> &defenders, const Id &context,
                         const std::vector<Id> &continuing = {}) {
  const auto plan = s.battles.at(planId);
  const auto r = readRequest(plan.data.require("request"));
  for (const auto &ship : attackers)
    if (!port(s.units.at(ship)).empty())
      moveTo(s, {ship}, plan.zone, 0, r.combat);
  std::map<Id, Id> origins;
  for (const auto &id : attackers) {
    auto &u = s.units.at(id);
    u.turnFlags.erase("naval_screening_continuing");
    origins[id] =
        u.route.size() > 1 ? u.route[u.route.size() - 2] : u.turnOrigin;
    if (!sea(s, origins[id]))
      origins[id] = plan.zone;
  }
  O options{{"context", V(context)},
            {"defenders", V(ids(defenders))},
            {"no_scramble",
             V(context == "movement_submarines" || context == "movement_map")},
            {"submarines_initiated", V(context == "movement_submarines")}};
  const auto battle = registerNavalBattle(s, plan.zone, plan.attacker,
                                          attackers, origins, V(options));
  auto &b = s.battles.at(battle);
  if (context == "screening" || context == "movement_submarines" ||
      context == "movement_map") {
    auto data = plan.data.asObject();
    data["kind"] = V(context);
    if (context == "screening")
      data["continuing"] = V(ids(continuing));
    put(b, "naval_movement", V(std::move(data)));
    if (context != "screening")
      b.flags["naval_movement_immediate"] = 1;
  }
  erasePlan(s, planId);
  if (context == "movement_submarines" || context == "movement_map") {
    s.flags["immediate_naval_battles"] = 1;
    beginNavalBattle(s, battle);
  }
}
void reaction(State &s, BattleState &b, const std::vector<Id> &candidates,
              const Id &context) {
  if (candidates.empty()) {
    encounter(s, b.id);
    return;
  }
  const auto n = s.units.at(candidates.front()).owner;
  std::vector<Id> own;
  for (const auto &id : candidates)
    if (s.units.at(id).owner == n)
      own.push_back(id);
  put(b, "reaction_units", V(ids(own)));
  put(b, "reaction_context", V(context));
  std::vector<Action> options{
      action(s, n, "naval_reaction_engage", {{"plan", V(b.id)}})};
  if (text(b, "entry_compelled") != n || text(b, "entry_zone") != b.zone)
    options.push_back(
        action(s, n, "naval_reaction_decline", {{"plan", V(b.id)}}));
  decision(s, b, n, "naval_movement_reaction", std::move(options));
}
void screenChoice(State &s, BattleState &b) {
  const auto r = readRequest(b.data.require("request"));
  auto selected = b.data.find("screening")
                      ? readIds(b.data.require("screening"))
                      : std::vector<Id>{};
  std::vector<Action> options;
  for (const auto &id : r.units)
    if (s.units.contains(id))
      options.push_back(action(
          s, b.attacker,
          std::find(selected.begin(), selected.end(), id) == selected.end()
              ? "naval_screen_add"
              : "naval_screen_remove",
          {{"plan", V(b.id)}, {"unit", V(id)}}));
  if (!selected.empty())
    options.push_back(
        action(s, b.attacker, "naval_screen_confirm", {{"plan", V(b.id)}}));
  decision(s, b, b.attacker, "naval_screening_force", std::move(options));
}
void encounter(State &s, const Id &id) {
  auto &b = s.battles.at(id);
  auto r = readRequest(b.data.require("request"));
  r.units = live(s, r.units);
  if (r.units.empty()) {
    erasePlan(s, id);
    return;
  }
  const auto n = b.attacker;
  if (b.data.find("waiting_ports")) {
    if (peaceEntryWindow(s, b, b.zone))
      return;
    auto opposing = blockers(s, n, b.zone);
    std::erase_if(opposing, [&](const Id &unit) {
      return !has(s, s.units.at(unit), "surface_warship");
    });
    if (!opposing.empty()) {
      b.stage = "naval_screen_selection";
      put(b, "screening", V(A{}));
      screenChoice(s, b);
      return;
    }
    for (const auto &ship : r.units)
      if (!port(s.units.at(ship)).empty())
        moveTo(s, {ship}, b.zone, 0, r.combat);
    auto data = b.data.asObject();
    data.erase("waiting_ports");
    b.data = V(std::move(data));
  }
  bool surface = false;
  for (const auto &unit : r.units)
    surface |= has(s, s.units.at(unit), "surface_ship");
  const auto declined = b.data.find("declined")
                            ? readIds(b.data.require("declined"))
                            : std::vector<Id>{};
  std::vector<Id> maps, subs;
  for (const auto &[other, u] : s.units)
    if (u.zone == b.zone && (!u.carriedBy || carrierPatrol(s, u)) &&
        hostile(s, n, u.owner) &&
        std::find(declined.begin(), declined.end(), other) == declined.end()) {
      if (patrol(u) || carrierPatrol(s, u))
        maps.push_back(other);
      else if (surface && has(s, u, "submarine") && !submerged(s, u))
        subs.push_back(other);
    }
  if (!maps.empty()) {
    reaction(s, b, maps, "movement_map");
    return;
  }
  if (!subs.empty()) {
    reaction(s, b, subs, "movement_submarines");
    return;
  }
  auto opposing = blockers(s, n, b.zone);
  std::erase_if(opposing, [&](const Id &unit) {
    return patrol(s.units.at(unit)) &&
           std::find(declined.begin(), declined.end(), unit) != declined.end();
  });
  if (!surface)
    opposing.clear();
  if (!opposing.empty()) {
    const bool loneRaider =
        r.units.size() == 1 &&
        s.units.at(r.units.front()).type == "battlecruiser" &&
        raider(s.units.at(r.units.front()));
    if (loneRaider && !marked(b.flags, "slip_attempted")) {
      ChanceRequest c;
      c.id = id + "_slip";
      c.purpose = "naval_movement_slip";
      c.nation = n;
      c.continuation = id;
      c.dice = {DieSpec{12, 0, {}, 0}, DieSpec{12, 0, {}, 0}};
      s.chance = c;
      return;
    }
    const auto cursor = b.data.require("cursor").asInt();
    if (cursor + 1 < static_cast<int>(r.path.size())) {
      b.stage = "naval_screen_selection";
      put(b, "screening", V(A{}));
      screenChoice(s, b);
      return;
    }
    beginBattleFromPlan(s, id, r.units, opposing, "standard");
    return;
  }
  continueRoute(s, id);
}
bool strategicPickup(State &s, BattleState &b) {
  const auto r = readRequest(b.data.require("request"));
  std::vector<Action> options;
  if (value(s.nations.at(b.attacker).turnFlags, "strategic_naval_used") <
      strategicNavalCapacity(s, b.attacker))
    for (const auto &ship : r.units)
      for (const auto &[cargo, c] : s.units)
        if (c.owner == b.attacker && canLoad(s, ship, cargo)) {
          bool facility = false;
          for (const auto &[id, f] : s.facilities)
            if (f.zone == c.zone && navalFacilityUsable(s, b.attacker, id) &&
                inSupply(s, b.attacker, f.zone)) {
              const auto access = navalFacilitySeaZones(s, id);
              if (std::find(access.begin(), access.end(), b.zone) !=
                  access.end())
                facility = true;
            }
          if (facility)
            options.push_back(action(s, b.attacker, "naval_strategic_pickup",
                                     {{"plan", V(b.id)},
                                      {"transport", V(ship)},
                                      {"unit", V(cargo)}}));
        }
  if (options.empty())
    return false;
  options.push_back(
      action(s, b.attacker, "naval_strategic_continue", {{"plan", V(b.id)}}));
  decision(s, b, b.attacker, "naval_strategic_pickup", std::move(options));
  return true;
}
void continueRoute(State &s, const Id &id) {
  auto &b = s.battles.at(id);
  auto r = readRequest(b.data.require("request"));
  r.units = live(s, r.units);
  if (r.units.empty()) {
    erasePlan(s, id);
    return;
  }
  const int cursor = b.data.require("cursor").asInt();
  if (cursor + 1 >= static_cast<int>(r.path.size())) {
    if (r.strategic && r.destinationFacility)
      for (const auto &ship : r.units) {
        auto &u = s.units.at(ship);
        u.turnFlags["naval_strategic_moved"] = 1;
        u.turnFlags["naval_strategic_destination:" + *r.destinationFacility] =
            1;
        u.movementRemaining = 0;
      }
    erasePlan(s, id);
    return;
  }
  const auto next = r.path[static_cast<std::size_t>(cursor + 1)];
  if (peaceEntryWindow(s, b, next))
    return;
  moveTo(s, r.units, next, r.strategic ? 0 : 1, r.combat);
  b.zone = next;
  put(b, "cursor", number(cursor + 1));
  put(b, "declined", V(A{}));
  put(b, "entry_processed", V(A{}));
  b.flags.erase("slip_attempted");
  if (r.strategic) {
    if (!strategicPickup(s, b))
      continueRoute(s, id);
  } else
    encounter(s, id);
}
void execute(State &s, const NavalRouteRequest &r) {
  const auto valid = validateNavalRoute(s, r);
  require(valid.allowed, valid.reason);
  const auto n = s.units.at(r.units.front()).owner;
  detachAircraft(s, r.units, r.path.front());
  if (r.strategic) {
    int count = 0;
    for (const auto &id : r.units)
      count += 1 + static_cast<int>(s.units.at(id).cargo.size());
    s.nations.at(n).turnFlags["strategic_naval_used"] += count;
  }
  O waitingPorts;
  for (const auto &id : r.units)
    if (!port(s.units.at(id)).empty())
      waitingPorts[id] = V(port(s.units.at(id)));
  const bool blockedSortie = !r.strategic && !waitingPorts.empty();
  if (!blockedSortie)
    for (const auto &id : r.units)
      if (!port(s.units.at(id)).empty())
        moveTo(s, {id}, r.path.front(), 0, r.combat);
  BattleState b;
  b.id = "naval_move_" + std::to_string(++s.flags["naval_move_sequence"]);
  b.zone = r.path.front();
  b.attacker = b.defender = n;
  b.stage = "naval_moving";
  b.attackers = r.units;
  b.flags["naval_movement_plan"] = 1;
  b.flags["naval_movement_immediate"] = 1;
  b.data = V(O{{"request", requestJson(r)},
               {"cursor", number(0)},
               {"declined", V(A{})}});
  if (blockedSortie)
    put(b, "waiting_ports", V(std::move(waitingPorts)));
  const auto id = b.id;
  s.battles.emplace(id, std::move(b));
  s.battleOrder.push_back(id);
  s.flags["immediate_naval_battles"] = 1;
  if (blockedSortie || r.path.size() == 1)
    encounter(s, id);
  else
    continueRoute(s, id);
}
bool canLoad(const State &s, const Id &ship, const Id &cargo) {
  if (!s.units.contains(ship) || !s.units.contains(cargo))
    return false;
  const auto &t = s.units.at(ship);
  const auto &c = s.units.at(cargo);
  const bool giftWithdrawal =
      s.clock.phase == Phase::NonCombatMovement &&
      marked(c.turnFlags, "must_withdraw_from_chinese_gift");
  if (!movementController(s, c.owner) || c.carriedBy || !c.cargo.empty() ||
      (!giftWithdrawal &&
       (!c.route.empty() || c.commitments.contains("combat_move") ||
        c.commitments.contains("combat"))) ||
      c.commitments.contains("attrition") ||
      c.commitments.contains("transport_unloaded") ||
      c.commitments.contains("amphibious_assault") ||
      marked(c.turnFlags, "air_transport_unloaded") ||
      marked(c.turnFlags, "placed_this_turn") ||
      marked(c.turnFlags, "naval_unloaded") ||
      marked(t.turnFlags, "naval_unloaded") ||
      marked(t.turnFlags, "naval_combat_unloaded") ||
      marked(t.turnFlags, "repairing") || t.commitments.contains("repair") ||
      (marked(t.gameFlags, "skeleton_crew") ||
       t.gameFlags.contains("skeleton_crew_until_own_turn")))
    return false;
  if (c.owner != t.owner &&
      (!politicallyFriendly(s, c.owner, t.owner) ||
       s.nations.at(c.owner).alliance != s.nations.at(t.owner).alliance))
    return false;
  if (!s.territories.contains(c.zone) || !s.territories.at(c.zone).possessor ||
      (!giftWithdrawal &&
       !politicallyFriendly(s, c.owner, *s.territories.at(c.zone).possessor)))
    return false;
  if (s.clock.phase != Phase::CombatMovement &&
      s.clock.phase != Phase::NonCombatMovement &&
      !(s.clock.phase == Phase::Combat &&
        marked(t.turnFlags, "naval_screening_continuing") &&
        !t.commitments.contains("naval_combat")))
    return false;
  if (s.clock.phase != Phase::NonCombatMovement && c.owner != t.owner)
    return false;
  if (port(t).empty()) {
    if (!adjacent(s, c.zone, t.zone))
      return false;
  } else if (s.facilities.at(port(t)).zone != c.zone)
    return false;
  auto load = t.cargo;
  load.push_back(cargo);
  return navalCargoFits(s, ship, load);
}
bool canUnload(const State &s, const Id &ship, const Id &cargo,
               const Id &destination) {
  if (!s.units.contains(ship) || !s.units.contains(cargo) ||
      !s.territories.contains(destination) ||
      s.clock.phase != Phase::NonCombatMovement)
    return false;
  const auto &t = s.units.at(ship);
  const auto &c = s.units.at(cargo);
  if (c.carriedBy != ship || !movementController(s, c.owner) ||
      marked(t.turnFlags, "naval_combat_unloaded"))
    return false;
  const auto owner = s.territories.at(destination).possessor;
  if (!owner || !politicallyFriendly(s, c.owner, *owner) ||
      !heldSinceTurnStart(s, c.owner, destination))
    return false;
  if (c.owner != t.owner &&
      value(c.gameFlags, "naval_loaded_completed_turns") >=
          navalCompletedTurns(s, c.owner))
    return false;
  if (!port(t).empty()) {
    if (s.facilities.at(port(t)).zone != destination)
      return false;
  } else if (!adjacent(s, t.zone, destination))
    return false;
  for (const auto &[key, v] : t.turnFlags)
    if (v && key.rfind("naval_strategic_destination:", 0) == 0 &&
        s.facilities.at(key.substr(Id("naval_strategic_destination:").size()))
                .zone != destination)
      return false;
  return true;
}
// The visitor returns true to stop after finding a completion witness. It does
// not execute the route, draw dice, or enter any opponent decision window.
bool visitNavalRoutes(const State &s, const std::vector<Id> &selected,
                      const std::function<bool(const NavalRouteRequest &)> &emit,
                      bool *landingBlocked = nullptr) {
  if (selected.empty())
    return false;
  const auto &nation = s.units.at(selected.front()).owner;
  const bool strategicEligible =
      s.clock.phase == Phase::NonCombatMovement &&
      std::all_of(selected.begin(), selected.end(), [&](const Id &id) {
        const auto &unit = s.units.at(id);
        return has(s, unit, "naval_transport") && unit.route.empty() &&
               !unit.commitments.contains("combat_move");
      });
  for (const auto &start : seasAt(s, selected.front())) {
      std::function<bool(std::vector<Id>)> visit = [&](std::vector<Id> path) {
        NavalRouteRequest r{
            selected, path,         s.clock.phase != Phase::NonCombatMovement,
            false,    std::nullopt, std::nullopt};
        if (path.size() > 1 || !port(s.units.at(selected.front())).empty()) {
          const auto valid = validateNavalRoute(s, r);
          if (valid.allowed) {
            if (emit(r))
              return true;
          } else if (valid.reason ==
                     "Carrier movement leaves aircraft without a joint landing plan") {
            // A later destination may restore aircraft landing capacity. This
            // final-position constraint cannot prune the route's extensions.
            if (landingBlocked)
              *landingBlocked = true;
          } else {
            return false;
          }
        }
        if (path.size() > 8)
          return false;
        for (const auto &next : mapNeighbors(s, path.back())) {
          if (!sea(s, next) ||
              std::find(path.begin(), path.end(), next) != path.end())
            continue;
          auto p = path;
          p.push_back(next);
          if (visit(std::move(p)))
            return true;
        }
        return false;
      };
      if (visit({start}))
        return true;
      if (strategicEligible)
        for (const auto &[origin, f] : s.facilities)
          if (f.type.rfind("major_", 0) == 0) {
            const auto access = navalFacilitySeaZones(s, origin);
            if (std::find(access.begin(), access.end(), start) == access.end())
              continue;
            std::function<bool(std::vector<Id>)> strategic =
                [&](std::vector<Id> path) {
                  for (const auto &[dest, end] : s.facilities) {
                    NavalRouteRequest r{selected, path,   false,
                                        true,     origin, dest};
                    const auto valid = validateNavalRoute(s, r);
                    if (valid.allowed && emit(r))
                      return true;
                    if (!valid.allowed && landingBlocked && valid.reason ==
                        "Carrier movement leaves aircraft without a joint landing plan")
                      *landingBlocked = true;
                  }
                  if (path.size() >
                      static_cast<std::size_t>(
                          4 +
                          (tech(s, nation, "improved_logistics") ? 1 : 0)))
                    return false;
                  for (const auto &next : mapNeighbors(s, path.back())) {
                    if (!sea(s, next) ||
                        std::find(path.begin(), path.end(), next) != path.end())
                      continue;
                    auto p = path;
                    p.push_back(next);
                    if (strategic(std::move(p)))
                      return true;
                  }
                  return false;
                };
            if (strategic({start}))
              return true;
          }
  }
  return false;
}

// Engaging holds the selected ships in battle where they are and launches
// their own aircraft there, so it must keep the aircraft's landing plan.
bool engagementKeepsLanding(const State &s, const std::vector<Id> &selected, const Id &zone) {
  const bool carriesAircraft =
      std::any_of(selected.begin(), selected.end(), [&](const Id &id) {
        const auto &u = s.units.at(id);
        return has(s, u, "carrier") ||
               std::any_of(u.cargo.begin(), u.cargo.end(), [&](const Id &c) {
                 return isAircraft(s, s.units.at(c));
               });
      });
  if (!carriesAircraft || !airLandingPlanReachable(s))
    return true;
  State probe = s.clone();
  detachAircraft(probe, selected, zone);
  for (const auto &id : selected) {
    auto &u = probe.units.at(id);
    u.commitments.insert("combat_move");
    u.turnFlags["naval_movement_spent"] = 1000;
  }
  return airLandingPlanReachable(probe);
}
class NavalOrderCompletion {
public:
  explicit NavalOrderCompletion(const State &state) : state_(state) {}

  void rememberComplete(const std::vector<Id> &selected) {
    complete_[selected] = true;
  }

  bool possible(const std::vector<Id> &selected) {
    if (selected.empty())
      return false;
    if (const auto known = complete_.find(selected); known != complete_.end())
      return known->second;
    const auto &first = state_.units.at(selected.front());
    if (state_.clock.phase != Phase::NonCombatMovement &&
        sea(state_, first.zone) && anyEnemy(state_, first.owner, first.zone) &&
        engagementKeepsLanding(state_, selected, first.zone))
      return complete_[selected] = true;
    bool landingBlocked = false;
    if (visitNavalRoutes(state_, selected,
                         [](const NavalRouteRequest &) { return true; },
                         &landingBlocked))
      return complete_[selected] = true;
    // An added ship cannot repair a range, origin, passage, ownership,
    // transport-capacity or raider-combination failure. Only moving additional
    // aircraft capacity (or aircraft cargo in an externally supplied state)
    // can repair the global joint-landing constraint. Search those helpers
    // lazily, retaining all combinations rather than capping a fleet menu.
    if (landingBlocked) {
      for (const auto &[id, unit] : state_.units) {
        if (id <= selected.back() || unit.zone != first.zone ||
            unit.owner != first.owner ||
            !available(state_, unit,
                       state_.clock.phase != Phase::NonCombatMovement))
          continue;
        const bool aircraftCargo =
            std::any_of(unit.cargo.begin(), unit.cargo.end(), [&](const Id &cargo) {
              return isAircraft(state_, state_.units.at(cargo));
            });
        if (!has(state_, unit, "carrier") && !aircraftCargo)
          continue;
        auto withHelper = selected;
        withHelper.push_back(id);
        if (possible(withHelper))
          return complete_[selected] = true;
      }
    }
    return complete_[selected] = false;
  }

private:
  const State &state_;
  std::map<std::vector<Id>, bool> complete_;
};

void routeChoices(State &s, BattleState &b) {
  const auto selected = readIds(b.data.require("selected"));
  std::vector<Action> options;
  for (const auto &[id, u] : s.units)
    if (u.zone == b.zone && u.owner == b.attacker &&
        available(s, u, s.clock.phase != Phase::NonCombatMovement))
      options.push_back(action(
          s, b.attacker,
          std::find(selected.begin(), selected.end(), id) == selected.end()
              ? "naval_force_add"
              : "naval_force_remove",
          {{"plan", V(b.id)}, {"unit", V(id)}}));
  options.push_back(
      action(s, b.attacker, "naval_cancel_move", {{"plan", V(b.id)}}));
  if (!selected.empty() && s.clock.phase != Phase::NonCombatMovement &&
      sea(s, b.zone) && anyEnemy(s, b.attacker, b.zone) &&
      engagementKeepsLanding(s, selected, b.zone))
    options.push_back(
        action(s, b.attacker, "naval_engage_force", {{"plan", V(b.id)}}));
  visitNavalRoutes(s, selected, [&](const NavalRouteRequest &request) {
    options.push_back(action(s, b.attacker, "naval_route",
                             {{"plan", V(b.id)},
                              {"request", requestJson(request)}}));
    return false;
  });
  decision(s, b, b.attacker, "naval_force_selection", std::move(options));
}
} // namespace

std::vector<Action> forwardNavalOrderActions(const State &s,
                                            std::vector<Action> actions) {
  NavalOrderCompletion completion(s);
  std::erase_if(actions, [&](const Action &candidate) {
    return candidate.kind == "naval_start_move" &&
           !completion.possible({candidate.parameters.require("unit").asString()});
  });
  return actions;
}

void forwardNavalOrderDecision(State &s) {
  if (s.decisions.empty())
    return;
  auto &pending = s.decisions.back();
  if (pending.kind == "naval_screening_force") {
    const auto &plan = s.battles.at(pending.continuation);
    const auto selected = plan.data.find("screening")
                              ? readIds(plan.data.require("screening"))
                              : std::vector<Id>{};
    std::erase_if(pending.options, [&](const Action &candidate) {
      return candidate.kind == "naval_screen_remove" ||
             (candidate.kind == "naval_screen_add" && !selected.empty() &&
              candidate.parameters.require("unit").asString() <= selected.back());
    });
    require(!pending.options.empty(), "Forward naval screen has no completion");
    return;
  }
  if (pending.kind != "naval_force_selection")
    return;
  const auto &plan = s.battles.at(pending.continuation);
  const auto selected = readIds(plan.data.require("selected"));
  require(!selected.empty() && std::is_sorted(selected.begin(), selected.end()),
          "Forward naval order requires an ascending nonempty fleet");
  NavalOrderCompletion completion(s);
  if (std::any_of(pending.options.begin(), pending.options.end(),
                  [](const Action &candidate) {
                    return candidate.kind == "naval_route" ||
                           candidate.kind == "naval_engage_force";
                  }))
    completion.rememberComplete(selected);
  std::erase_if(pending.options, [&](const Action &candidate) {
    if (candidate.kind == "naval_cancel_move" ||
        candidate.kind == "naval_force_remove")
      return true;
    if (candidate.kind != "naval_force_add")
      return false;
    const auto &unit = candidate.parameters.require("unit").asString();
    if (unit <= selected.back())
      return true;
    auto next = selected;
    next.push_back(unit);
    return !completion.possible(next);
  });
  require(!pending.options.empty(), "Forward naval order has no completion");
}

int strategicNavalCapacity(const State &s, const Id &n) {
  int base = n == "japan"                                            ? 3
             : n == "ussr" || n == "germany"                         ? 2
             : n == "usa"                                            ? 4
             : n == "italy" || n == "france" || n == "great_britain" ? 3
                                                                     : 0;
  if (tech(s, n, "improved_logistics"))
    base += 2;
  if (marked(s.nations.at(n).gameFlags, "access_to_resources_completed"))
    ++base;
  return base;
}
bool navalCargoFits(const State &s, const Id &ship,
                    const std::vector<Id> &cargo) {
  if (!s.units.contains(ship))
    return false;
  const auto &t = s.units.at(ship);
  if (std::set<Id>(cargo.begin(), cargo.end()).size() != cargo.size())
    return false;
  if (t.type == "destroyer" && t.owner == "japan") {
    return cargo.size() <= 1 &&
           std::all_of(cargo.begin(), cargo.end(), [&](const Id &id) {
             return s.units.contains(id) && s.units.at(id).type == "marine";
           });
  }
  if (!has(s, t, "naval_transport"))
    return false;
  if (cargo.size() > 2)
    return false;
  int other = 0;
  for (const auto &id : cargo) {
    if (!s.units.contains(id))
      return false;
    const auto &c = s.units.at(id);
    if (!has(s, c, "land") && !has(s, c, "rocket"))
      return false;
    if (!has(s, c, "infantry_class"))
      ++other;
  }
  return other <= 1;
}
RouteResult validateNavalRoute(const State &s, const NavalRouteRequest &r) {
  auto fail = [](const std::string &why) {
    RouteResult x;
    x.reason = why;
    return x;
  };
  if (r.units.empty() || r.path.empty() ||
      std::set<Id>(r.units.begin(), r.units.end()).size() != r.units.size())
    return fail("Empty or duplicate naval force");
  if (!s.units.contains(r.units.front()))
    return fail("Unknown naval unit");
  const auto n = s.units.at(r.units.front()).owner;
  if ((r.combat && s.clock.phase != Phase::CombatMovement &&
       s.clock.phase != Phase::Combat) ||
      (!r.combat && s.clock.phase != Phase::NonCombatMovement))
    return fail("Wrong naval movement phase");
  if (r.strategic && r.combat)
    return fail("Strategic naval movement is noncombat");
  for (const auto &z : r.path)
    if (!sea(s, z))
      return fail("Naval path must remain in retained sea zones");
  for (std::size_t i = 1; i < r.path.size(); ++i)
    if (!adjacent(s, r.path[i - 1], r.path[i]))
      return fail("Nonadjacent naval path");
  int totalCost = static_cast<int>(r.path.size()) - 1;
  int strategicCost = 0;
  for (const auto &id : r.units) {
    if (!s.units.contains(id))
      return fail("Unknown naval unit");
    const auto &u = s.units.at(id);
    if (u.owner != n || !available(s, u, r.combat) ||
        !atSeaStart(s, u, r.path.front()))
      return fail("Naval force is unavailable or has different origins/owners");
    if ((has(s, u, "naval_transport") ||
         (u.owner == "japan" && u.type == "destroyer")) &&
        !navalCargoFits(s, id, u.cargo))
      return fail("Naval cargo exceeds transport capacity");
    if (r.path.size() == 1 && port(u).empty())
      return fail("Naval route has no movement");
    for (std::size_t i = 1; i < r.path.size(); ++i)
      if (!passage(s, u, r.path[i - 1], r.path[i], r.strategic))
        return fail("Closed naval passage");
    if (r.strategic) {
      if (!has(s, u, "naval_transport") || !u.route.empty() ||
          u.commitments.contains("combat_move"))
        return fail("Only unmoved naval transports use strategic movement");
      for (const auto &child : u.cargo)
        if (s.units.at(child).owner != n)
          return fail("Strategic naval movement cannot carry aligned cargo");
      strategicCost += 1 + static_cast<int>(u.cargo.size());
    } else if (totalCost > std::max(0, allowance(s, u, r.combat, r.path.back(),
                                                 r.path.front()) -
                                           spent(s, u)))
      return fail("Insufficient naval movement");
  }
  if (r.strategic) {
    if (!r.originFacility || !r.destinationFacility ||
        !s.facilities.contains(*r.originFacility) ||
        !s.facilities.contains(*r.destinationFacility))
      return fail("Strategic movement requires origin and destination naval "
                  "facilities");
    const auto &f = s.facilities.at(*r.originFacility);
    if (f.type.rfind("major_", 0) != 0 ||
        !navalFacilityUsable(s, n, *r.originFacility) ||
        !navalFacilityUsable(s, n, *r.destinationFacility) ||
        !inSupply(s, n, f.zone) ||
        !inSupply(s, n, s.facilities.at(*r.destinationFacility).zone))
      return fail("Strategic facilities require supply and undamaged friendly "
                  "possession");
    const auto origin = navalFacilitySeaZones(s, *r.originFacility),
               destination = navalFacilitySeaZones(s, *r.destinationFacility);
    if (std::find(origin.begin(), origin.end(), r.path.front()) ==
            origin.end() ||
        std::find(destination.begin(), destination.end(), r.path.back()) ==
            destination.end())
      return fail("Strategic endpoints do not match facility accesses");
    if (totalCost > 4 + (tech(s, n, "improved_logistics") ? 1 : 0) ||
        value(s.nations.at(n).turnFlags, "strategic_naval_used") +
                strategicCost >
            strategicNavalCapacity(s, n))
      return fail("Strategic naval range or capacity exceeded");
    if (anyEnemy(s, n, r.path.front()))
      return fail("Strategic movement cannot depart enemy-occupied sea");
    for (const auto &z : r.path) {
      if (!inSupply(s, n, z))
        return fail("Strategic route is outside a Supply Path");
      for (const auto &[id, u] : s.units)
        if (u.zone == z && hostile(s, n, u.owner) &&
            ((has(s, u, "surface_warship")) ||
             (has(s, u, "submarine") && !submerged(s, u)) || patrol(u)))
          return fail("Enemy unit blocks strategic route");
    }
  } else if (r.combat && r.units.size() > 1 &&
             std::any_of(
                 r.units.begin(), r.units.end(),
                 [&](const Id &id) { return raider(s.units.at(id)); }) &&
             std::any_of(r.path.begin(), r.path.end(), [&](const Id &z) {
               return !blockers(s, n, z).empty();
             }))
    return fail(
        "A raiding battlecruiser cannot combine attacks with other units");
  else if (!r.combat) {
    // Ships in port begin in an adjacent sea zone but still enter it: exiting
    // past Enemy Surface Warships needs a screening force, which is combat
    // movement (RB 9.4.2, 11.4, 11.5).
    const std::size_t entered =
        std::any_of(r.units.begin(), r.units.end(),
                    [&](const Id &id) { return !port(s.units.at(id)).empty(); })
            ? 0
            : 1;
    for (std::size_t i = entered; i < r.path.size(); ++i)
      for (const auto &[id, u] : s.units)
        if (u.zone == r.path[i] && !hostile(s, n, u.owner) && u.owner != n &&
            s.nations.at(u.owner).alliance != s.nations.at(n).alliance &&
            (mayDeclareWar(s, n, u.owner).allowed ||
             mayDeclareWar(s, u.owner, n).allowed))
          return fail(
              "Potential declaration of war requires Combat Movement entry");
    bool surface = false;
    for (const auto &id : r.units)
      surface |= has(s, s.units.at(id), "surface_ship");
    if (surface)
      for (std::size_t i = entered; i < r.path.size(); ++i)
        if (!blockers(s, n, r.path[i]).empty())
          return fail("Enemy surface warship or MAP blocks noncombat movement");
  }
  // The joint landing plan reads only aircraft and carriers. A force with no
  // carrier, aircraft or aircraft cargo leaves all of them, and every carrier's
  // remaining reach, where they are.
  const bool movesAircraft =
      std::any_of(r.units.begin(), r.units.end(), [&](const Id &id) {
        const auto &u = s.units.at(id);
        return has(s, u, "carrier") || isAircraft(s, u) ||
               std::any_of(u.cargo.begin(), u.cargo.end(), [&](const Id &c) {
                 return isAircraft(s, s.units.at(c));
               });
      });
  if (movesAircraft) {
    // Aircraft must keep a reachable landing plan wherever the move can end:
    // in its last zone; short of it where blockers force a screen (a lone
    // carrier must screen and stays) or where neutral units raise a peace
    // entry (a declaration can make them blockers); and, leaving port past
    // either, in port with its own aircraft already launched. Reactions and
    // passing transports, submarines or raiders do not stop the force.
    const bool fromPort =
        std::any_of(r.units.begin(), r.units.end(),
                    [&](const Id &id) { return !port(s.units.at(id)).empty(); });
    const bool surface =
        std::any_of(r.units.begin(), r.units.end(),
                    [&](const Id &id) { return has(s, s.units.at(id), "surface_ship"); });
    const auto canStop = [&](const Id &zone) {
      if (surface && !blockers(s, n, zone).empty())
        return true;
      for (const auto &[id, other] : s.units)
        if (other.zone == zone && other.owner != n && !hostile(s, n, other.owner) &&
            s.nations.at(other.owner).alliance != s.nations.at(n).alliance &&
            s.nations.at(other.owner).player &&
            (mayDeclareWar(s, n, other.owner).allowed || mayDeclareWar(s, other.owner, n).allowed))
          return true;
      return false;
    };
    // (zone index, or -1 for still in port; whether the force stops there for good)
    std::vector<std::pair<int, bool>> stops;
    if (r.combat && !r.strategic) {
      if (fromPort && canStop(r.path.front()))
        stops.emplace_back(-1, true);
      for (std::size_t i = fromPort ? 0 : 1; i + 1 < r.path.size(); ++i)
        if (canStop(r.path[i]))
          stops.emplace_back(static_cast<int>(i), true);
    }
    stops.emplace_back(static_cast<int>(r.path.size()) - 1, false);
    for (const auto &[stop, held] : stops) {
      // The force as the move leaves it there, with the movement it spends,
      // so the plan sees how far these carriers can still sail.
      State probe = s.clone();
      detachAircraft(probe, r.units, r.path.front());
      if (stop >= 0)
        for (const auto &id : r.units) {
          auto &u = probe.units.at(id);
          if (!port(u).empty())
            u.turnFlags["naval_start_sea:" + r.path.front()] = 1;
          for (auto i = u.gameFlags.begin(); i != u.gameFlags.end();)
            i = i->first.rfind("in_port:", 0) == 0 ? u.gameFlags.erase(i) : std::next(i);
          u.zone = r.path[static_cast<std::size_t>(stop)];
          if (r.strategic)
            u.turnFlags["naval_strategic_moved"] = 1;
          else
            u.turnFlags["naval_movement_spent"] += stop;
          if (r.combat)
            u.commitments.insert("combat_move");
          for (const auto &child : u.cargo)
            probe.units.at(child).zone = u.zone;
        }
      if (held)
        for (const auto &id : r.units)
          probe.units.at(id).turnFlags["naval_movement_spent"] = 1000;  // Held there.
      if (!airLandingPlanReachable(probe))
        return fail(
            "Carrier movement leaves aircraft without a joint landing plan");
    }
  }
  RouteResult result;
  result.allowed = true;
  result.cost = totalCost;
  return result;
}
std::set<Id> navalEndZones(const State &s, const Id &ship) {
  auto compute = [&] {
    std::set<Id> out;
    if (!s.units.contains(ship))
      return out;
    const auto &u = s.units.at(ship);
    out.insert(u.zone);
    const bool combat = s.clock.phase != Phase::NonCombatMovement;
    // A ship that sailed into Enemy units this phase stays for their battle.
    if ((s.clock.phase != Phase::CombatMovement &&
         s.clock.phase != Phase::NonCombatMovement) ||
        !available(s, u, combat) ||
        (u.commitments.contains("combat_move") && anyEnemy(s, u.owner, u.zone)))
      return out;
    // A route ends early wherever an encounter can stop it. Enemy units may
    // wait only in a Combat Movement route's last zone, where its battle is
    // fought; neutral units, which raise a peace entry, nowhere.
    const auto unfriendly = [&](const Id &zone, bool enemiesAllowed) {
      for (const auto &[id, other] : s.units)
        if (other.zone == zone && !other.carriedBy && other.owner != u.owner &&
            !politicallyFriendly(s, u.owner, other.owner) &&
            (!enemiesAllowed || !hostile(s, u.owner, other.owner)))
          return true;
      return false;
    };
    const bool inPort = !port(u).empty();
    for (const auto &start : seasAt(s, ship)) {
      // Leaving port enters the first sea zone, where blockers force a screen.
      if (inPort && unfriendly(start, false))
        continue;
      // A Japanese surprise attack adds one point for its own target zone.
      const int reach =
          std::max(0, allowance(s, u, combat, Id{}, start) + 1 - spent(s, u));
      std::map<Id, int> distance{{start, 0}};
      std::deque<Id> queue{start};
      while (!queue.empty()) {
        const auto zone = queue.front();
        queue.pop_front();
        const int steps = distance.at(zone);
        const bool entered = steps > 0 || inPort;
        if (entered &&
            steps <= allowance(s, u, combat, zone, start) - spent(s, u) &&
            !unfriendly(zone, combat))
          out.insert(zone);
        if (steps >= reach || (entered && unfriendly(zone, false)))
          continue;
        for (const auto &next : mapNeighbors(s, zone))
          if (sea(s, next) && !distance.contains(next) &&
              passage(s, u, zone, next, false)) {
            distance.emplace(next, steps + 1);
            queue.push_back(next);
          }
      }
    }
    return out;
  };
  if (auto *facts = positionFacts(s))
    return facts->zones(PositionFacts::Fact::NavalEndZones, ship, compute);
  return compute();
}
bool navalLoadAllowed(const State &s, const Id &transport, const Id &cargo) {
  return canLoad(s, transport, cargo);
}
std::vector<Action> navalMovementActions(const State &s) {
  std::vector<Action> out;
  if (s.terminal || s.chance || !s.decisions.empty() ||
      (s.clock.phase != Phase::CombatMovement &&
       s.clock.phase != Phase::NonCombatMovement &&
       s.clock.phase != Phase::Combat))
    return out;
  const bool combat = s.clock.phase != Phase::NonCombatMovement;
  for (const auto &[id, u] : s.units) {
    if (available(s, u, combat))
      out.push_back(action(s, u.owner, "naval_start_move", {{"unit", V(id)}}));
    if (u.type == "battlecruiser" && available(s, u, combat) &&
        s.clock.phase == Phase::CombatMovement &&
        !(marked(u.gameFlags, "skeleton_crew") ||
          u.gameFlags.contains("skeleton_crew_until_own_turn"))) {
      if (!raider(u) && !escort(u))
        out.push_back(
            action(s, u.owner, "naval_designate_raider", {{"unit", V(id)}}));
      if (raider(u) && u.route.empty())
        out.push_back(
            action(s, u.owner, "naval_remove_raider", {{"unit", V(id)}}));
    }
    // canLoad ends with navalCargoFits, which only transports and Japanese
    // destroyers pass, so other ships need no per-unit loading test.
    const bool carriesCargo =
        (u.type == "destroyer" && u.owner == "japan") ||
        has(s, u, "naval_transport");
    for (const auto &[cargo, c] : s.units) {
      if (carriesCargo && canLoad(s, id, cargo))
        out.push_back(action(s, c.owner, "naval_load",
                             {{"transport", V(id)}, {"unit", V(cargo)}}));
      if (c.carriedBy == id)
        for (const auto &[zone, t] : s.territories)
          if (canUnload(s, id, cargo, zone))
            out.push_back(action(
                s, c.owner, "naval_unload",
                {{"transport", V(id)}, {"unit", V(cargo)}, {"zone", V(zone)}}));
    }
  }
  return out;
}
bool applyNavalMovementAction(State &s, const Action &a) {
  const auto &p = a.parameters;
  if (a.kind == "naval_screen_continue_route" ||
      a.kind == "naval_screen_stop_route") {
    const auto plan = p.require("plan").asString();
    release(s, a);
    if (a.kind == "naval_screen_stop_route")
      erasePlan(s, plan);
    else
      encounter(s, plan);
    return true;
  }
  if (a.kind == "naval_start_move") {
    const auto unit = p.require("unit").asString();
    const auto &u = s.units.at(unit);
    BattleState b;
    b.id = "naval_plan_" + std::to_string(++s.flags["naval_move_sequence"]);
    b.attacker = b.defender = u.owner;
    b.zone = u.zone;
    b.stage = "naval_force_selection";
    b.flags["naval_movement_plan"] = 1;
    b.data = V(O{{"selected", V(A{V(unit)})}});
    const auto id = b.id;
    s.battles.emplace(id, std::move(b));
    s.battleOrder.push_back(id);
    routeChoices(s, s.battles.at(id));
    return true;
  }
  if (a.kind == "naval_designate_raider" || a.kind == "naval_remove_raider") {
    auto &u = s.units.at(p.require("unit").asString());
    if (a.kind == "naval_designate_raider")
      u.gameFlags["raider"] = 1;
    else {
      u.gameFlags.erase("raider");
      u.gameFlags.erase("naval_raider");
    }
    return true;
  }
  if (a.kind == "naval_load") {
    const auto ship = p.require("transport").asString(),
               cargo = p.require("unit").asString();
    require(canLoad(s, ship, cargo), "Illegal naval loading");
    attachCargo(s, ship, cargo);
    auto &c = s.units.at(cargo);
    c.turnFlags.erase("must_withdraw_from_chinese_gift");
    c.movementRemaining = 0;
    c.gameFlags["naval_loaded_completed_turns"] =
        navalCompletedTurns(s, c.owner);
    return true;
  }
  if (a.kind == "naval_unload") {
    const auto ship = p.require("transport").asString(),
               cargo = p.require("unit").asString(),
               zone = p.require("zone").asString();
    require(canUnload(s, ship, cargo, zone), "Illegal naval unloading");
    detachCargo(s, ship, cargo, zone);
    s.units.at(cargo).turnFlags["naval_unloaded"] = 1;
    s.units.at(cargo).route.push_back(zone);
    s.units.at(cargo).movementRemaining = 0;
    s.units.at(ship).turnFlags["naval_unloaded"] = 1;
    s.units.at(ship).movementRemaining = 0;
    return true;
  }
  if (a.kind == "naval_entry_declare" || a.kind == "naval_entry_peaceful" ||
      a.kind == "naval_entry_defender_declare" ||
      a.kind == "naval_entry_neutral") {
    const auto plan = p.require("plan").asString();
    release(s, a);
    auto &b = s.battles.at(plan);
    const auto target = text(b, "entry_nation");
    if (a.kind == "naval_entry_peaceful" &&
        mayDeclareWar(s, target, b.attacker).allowed) {
      decision(s, b, target, "naval_entry_response",
               {action(s, target, "naval_entry_defender_declare",
                       {{"plan", V(plan)}}),
                action(s, target, "naval_entry_neutral", {{"plan", V(plan)}})});
      return true;
    }
    if (a.kind == "naval_entry_declare")
      declareWar(s, b.attacker, target, DeclarationMode::MajorPowerDeclaration);
    if (a.kind == "naval_entry_defender_declare") {
      declareWar(s, target, b.attacker, DeclarationMode::MajorPowerDeclaration);
      put(b, "entry_compelled", V(target));
    }
    markEntryProcessed(b);
    resumeEntry(s, plan);
    return true;
  }
  if (a.kind == "naval_engage_force") {
    const auto plan = p.require("plan").asString();
    release(s, a);
    const auto b = s.battles.at(plan);
    const auto selected = readIds(b.data.require("selected"));
    require(engagementKeepsLanding(s, selected, b.zone),
            "Engaging leaves aircraft without a joint landing plan");
    detachAircraft(s, selected, b.zone);
    std::map<Id, Id> origins;
    std::vector<Id> enemies;
    for (const auto &ship : selected) {
      const auto &u = s.units.at(ship);
      if (!u.route.empty())
        origins[ship] =
            u.route.size() > 1 ? u.route[u.route.size() - 2] : u.turnOrigin;
    }
    for (const auto &[id, u] : s.units)
      if (u.zone == b.zone && !u.carriedBy && hostile(s, b.attacker, u.owner) &&
          (has(s, u, "naval") || isAircraft(s, u)))
        enemies.push_back(id);
    erasePlan(s, plan);
    registerNavalBattle(s, b.zone, b.attacker, selected, origins,
                        V(O{{"context", V(std::string("standard"))},
                            {"defenders", V(ids(enemies))}}));
    // Ordinary CM declarations wait for Combat and allow further
    // reinforcements.
    refreshImmediate(s);
    return true;
  }
  if (a.kind == "naval_force_add" || a.kind == "naval_force_remove" ||
      a.kind == "naval_cancel_move" || a.kind == "naval_route") {
    const auto plan = p.require("plan").asString();
    release(s, a);
    if (a.kind == "naval_cancel_move") {
      erasePlan(s, plan);
      return true;
    }
    if (a.kind == "naval_route") {
      const auto r = readRequest(p.require("request"));
      erasePlan(s, plan);
      execute(s, r);
      return true;
    }
    auto &b = s.battles.at(plan);
    auto selected = readIds(b.data.require("selected"));
    const auto unit = p.require("unit").asString();
    if (a.kind == "naval_force_add")
      selected.push_back(unit);
    else
      std::erase(selected, unit);
    put(b, "selected", V(ids(selected)));
    routeChoices(s, b);
    return true;
  }
  if (a.kind == "naval_screen_add" || a.kind == "naval_screen_remove" ||
      a.kind == "naval_screen_confirm") {
    const auto plan = p.require("plan").asString();
    release(s, a);
    auto &b = s.battles.at(plan);
    auto selected = b.data.find("screening")
                        ? readIds(b.data.require("screening"))
                        : std::vector<Id>{};
    if (a.kind == "naval_screen_confirm") {
      const auto r = readRequest(b.data.require("request"));
      auto continuing = r.units;
      for (const auto &unit : selected)
        std::erase(continuing, unit);
      beginBattleFromPlan(s, plan, selected, blockers(s, b.attacker, b.zone),
                          "screening", continuing);
    } else {
      const auto unit = p.require("unit").asString();
      if (a.kind == "naval_screen_add")
        selected.push_back(unit);
      else
        std::erase(selected, unit);
      put(b, "screening", V(ids(selected)));
      screenChoice(s, b);
    }
    return true;
  }
  if (a.kind == "naval_strategic_pickup" ||
      a.kind == "naval_strategic_continue") {
    const auto plan = p.require("plan").asString();
    release(s, a);
    auto &b = s.battles.at(plan);
    if (a.kind == "naval_strategic_continue") {
      continueRoute(s, plan);
      return true;
    }
    const auto ship = p.require("transport").asString(),
               cargo = p.require("unit").asString();
    require(canLoad(s, ship, cargo), "Invalid strategic pickup");
    attachCargo(s, ship, cargo);
    s.units.at(cargo).movementRemaining = 0;
    s.units.at(cargo).gameFlags["naval_loaded_completed_turns"] =
        navalCompletedTurns(s, b.attacker);
    ++s.nations.at(b.attacker).turnFlags["strategic_naval_used"];
    if (!strategicPickup(s, b))
      continueRoute(s, plan);
    return true;
  }
  if (a.kind == "naval_reaction_engage" || a.kind == "naval_reaction_decline") {
    const auto plan = p.require("plan").asString();
    release(s, a);
    auto &b = s.battles.at(plan);
    const auto defenders = readIds(b.data.require("reaction_units"));
    if (a.kind == "naval_reaction_engage") {
      const auto r = readRequest(b.data.require("request"));
      beginBattleFromPlan(s, plan, r.units, defenders,
                          text(b, "reaction_context"));
    } else {
      auto declined = b.data.find("declined")
                          ? readIds(b.data.require("declined"))
                          : std::vector<Id>{};
      declined.insert(declined.end(), defenders.begin(), defenders.end());
      put(b, "declined", V(ids(declined)));
      encounter(s, plan);
    }
    return true;
  }
  return false;
}
bool applyNavalMovementChance(State &s, const ChanceRequest &request,
                              const ChanceOutcome &outcome) {
  if (request.purpose != "naval_movement_slip")
    return false;
  const auto rolls = effectiveResults(request, outcome);
  auto &b = s.battles.at(request.continuation);
  const auto r = readRequest(b.data.require("request"));
  const auto enemies = blockers(s, b.attacker, b.zone);
  int opponent = 0;
  bool radar = false;
  for (const auto &id : enemies) {
    const auto &u = s.units.at(id);
    opponent += isAircraft(s, u) ? 4 : has(s, u, "surface_warship") ? 1 : 0;
    radar |= tech(s, u.owner, "radar");
  }
  const int own = rolls[0] + 6 + (tech(s, b.attacker, "radar") ? 1 : 0),
            enemy = rolls[1] + opponent + (radar ? 1 : 0);
  if (own == enemy) {
    s.chance = request;
    return true;
  }
  b.flags["slip_attempted"] = 1;
  if (own > enemy)
    continueRoute(s, b.id);
  else
    beginBattleFromPlan(s, b.id, r.units, enemies, "raider");
  return true;
}
bool navalMovementPhaseComplete(const State &s) {
  for (const auto &[id, b] : s.battles)
    if (b.stage == "naval_force_selection" ||
        b.stage == "naval_screen_selection" || b.stage == "naval_moving" ||
        (b.data.find("naval_movement") && b.stage != "naval_declared"))
      return false;
  return true;
}
void beginNavalMovementTurn(State &s) {
  s.nations.at(s.currentNation()).turnFlags.erase("strategic_naval_used");
}
void finishNavalMovementPhase(State &s) { refreshImmediate(s); }
void continueNavalMovement(State &s, const Id &id) {
  const auto b = s.battles.at(id);
  const auto *continuation = b.data.find("naval_movement");
  if (!continuation)
    return;
  auto data = continuation->asObject();
  auto r = readRequest(data.at("request"));
  const auto kind = data.at("kind").asString();
  auto continuing = kind == "screening" && data.contains("continuing")
                        ? readIds(data.at("continuing"))
                        : r.units;
  continuing = live(s, continuing);
  const auto remaining = blockers(s, b.attacker, b.zone);
  erasePlan(s, id);
  if (continuing.empty())
    return;
  if (kind == "screening" && !remaining.empty()) {
    if (data.contains("waiting_ports"))
      return;
    for (const auto &unit : continuing) {
      auto &u = s.units.at(unit);
      Id from = u.route.size() > 1 ? u.route[u.route.size() - 2] : u.turnOrigin;
      require(sea(s, from) && adjacent(s, from, b.zone),
              "Failed screening requires its actual adjacent entry sea");
      u.zone = from;
      u.movementRemaining = 0;
      u.turnFlags["naval_retreated"] = 1;
      for (const auto &cargo : u.cargo)
        s.units.at(cargo).zone = from;
    }
    return;
  }
  r.units = continuing;
  if (data.contains("waiting_ports")) {
    for (const auto &ship : continuing)
      if (!port(s.units.at(ship)).empty())
        moveTo(s, {ship}, b.zone, 0, r.combat);
    data.erase("waiting_ports");
  }
  if (kind == "screening")
    for (const auto &unit : continuing)
      s.units.at(unit).turnFlags["naval_screening_continuing"] = 1;
  data["request"] = requestJson(r);
  if (!data.contains("declined"))
    data["declined"] = V(A{});
  auto declined = readIds(data.at("declined"));
  declined.insert(declined.end(), b.defenders.begin(), b.defenders.end());
  data["declined"] = V(ids(declined));
  BattleState plan;
  plan.id = "naval_move_" + std::to_string(++s.flags["naval_move_sequence"]);
  plan.zone = b.zone;
  plan.attacker = plan.defender = b.attacker;
  plan.attackers = continuing;
  plan.stage = "naval_moving";
  plan.flags["naval_movement_plan"] = 1;
  plan.flags["naval_movement_immediate"] = 1;
  plan.data = V(std::move(data));
  const auto next = plan.id;
  s.battles.emplace(next, std::move(plan));
  s.battleOrder.push_back(next);
  s.flags["immediate_naval_battles"] = 1;
  if (kind == "screening")
    decision(s, s.battles.at(next), b.attacker, "naval_screening_continuation",
             {action(s, b.attacker, "naval_screen_continue_route",
                     {{"plan", V(next)}}),
              action(s, b.attacker, "naval_screen_stop_route",
                     {{"plan", V(next)}})});
  else
    encounter(s, next);
}
} // namespace game::campaign
