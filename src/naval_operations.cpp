#include "game/air.hpp"
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
// Builds the message only on failure; most messages are literals.
template <class Message> void require(bool value, const Message &message) {
  if (!value)
    throw std::runtime_error(message);
}
int flag(const std::map<Id, int> &values, const Id &key) {
  const auto it = values.find(key);
  return it == values.end() ? 0 : it->second;
}
bool hostile(const State &s, const Id &a, const Id &b) {
  return a != b && s.nations.at(a).atWarWith.contains(b);
}
bool friendly(const State &s, const Id &a, const Id &b) {
  return a == b || politicallyFriendly(s, a, b);
}
bool sea(const State &s, const Id &zone) {
  return !s.territories.contains(zone);
}
const V &node(const State &s, const Id &id) {
  return mapNode(s, id);
}
bool adjacent(const State &s, const Id &a, const Id &b) {
  return mapEdge(s, a, b) != nullptr;
}
V ids(const std::vector<Id> &values) {
  A a;
  for (const auto &v : values)
    a.emplace_back(v);
  return V(std::move(a));
}
std::vector<Id> readIds(const V &value) {
  std::vector<Id> out;
  for (const auto &v : value.asArray())
    out.push_back(v.asString());
  return out;
}
void put(BattleState &b, const Id &key, V value) {
  auto o = b.data.asObject();
  o[key] = std::move(value);
  b.data = V(std::move(o));
}
Action action(const State &s, const Id &nation, const Id &kind, O params) {
  const auto p = V(std::move(params));
  return {kind + "_" + contentDigest(canonicalJson(p)),
          kind,
          politicalPlayer(s, nation),
          nation,
          std::nullopt,
          p};
}
void decision(State &s, const Id &nation, const Id &kind,
              const Id &continuation, std::vector<Action> options) {
  require(!options.empty(), "Empty naval operation decision");
  const auto id =
      kind + "_" +
      std::to_string(++s.flags["naval_operation_decision_sequence"]);
  for (auto &a : options)
    a.decision = id;
  s.decisions.push_back({id, kind, nation, nation != s.currentNation(),
                         continuation, std::move(options)});
}
void release(State &s, const Action &a) {
  require(!s.decisions.empty() && a.decision == s.decisions.back().id,
          "Naval operation does not match pending choice");
  s.decisions.pop_back();
}
Id berth(const UnitState &u) {
  for (const auto &[k, v] : u.gameFlags)
    if (v && k.rfind("in_port:", 0) == 0)
      return k.substr(8);
  return {};
}
bool ship(const State &s, const UnitState &u) {
  return unitClass(s, u, "naval");
}
bool occupiedForAssault(const State &s, const Id &owner, const Id &zone) {
  for (const auto &[id, u] : s.units)
    if (u.zone == zone && !u.carriedBy && hostile(s, owner, u.owner) &&
        (unitClass(s, u, "surface_ship") || isAircraft(s, u)) &&
        !flag(u.turnFlags, "map_declined_combat"))
      return true;
  return false;
}
bool unavailable(const UnitState &u) {
  return flag(u.gameFlags, "skeleton_crew_until_own_turn") ||
         u.commitments.contains("repair") ||
         u.commitments.contains("newly_placed") ||
         flag(u.turnFlags, "placed_this_turn") ||
         flag(u.turnFlags, "repairing");
}
// Each target's first valid shortest combat flight, in breadth-first order
// from the aircraft's zone. Enemy Fighters may occupy only a path's final zone,
// its target, so paths into them are kept but never extended. One search finds
// what a separate search per target would.
std::map<Id, std::vector<Id>> combatPaths(const State &s, const Id &unit) {
  const auto &u = s.units.at(unit);
  std::map<Id, std::vector<Id>> paths;
  std::deque<std::vector<Id>> q{{u.zone}};
  std::set<Id> visited;
  while (!q.empty()) {
    auto path = std::move(q.front());
    q.pop_front();
    const auto current = path.back();
    if (!visited.insert(current).second)
      continue;
    if (validateFlight(s, unit, path, true, true).allowed)
      paths.emplace(current, path);
    if (static_cast<int>(path.size()) > u.movementRemaining.value_or(0))
      continue;
    for (const auto &next : mapNeighbors(s, current)) {
      auto candidate = path;
      candidate.push_back(next);
      if (validateFlight(s, unit, candidate, true, true).allowed)
        q.push_back(std::move(candidate));
    }
  }
  return paths;
}
void moveAircraft(State &s, const Id &id, const std::vector<Id> &path) {
  auto &u = s.units.at(id);
  const auto result = validateFlight(s, id, path, true, true);
  require(result.allowed, result.reason);
  if (u.carriedBy) {
    auto &cargo = s.units.at(*u.carriedBy).cargo;
    cargo.erase(std::remove(cargo.begin(), cargo.end(), id), cargo.end());
    u.carriedBy.reset();
  }
  for (std::size_t i = 1; i < path.size(); ++i)
    u.route.push_back(path[i]);
  u.zone = path.back();
  u.movementRemaining = u.movementRemaining.value_or(0) - result.cost;
  u.turnFlags["air_in_flight"] = 1;
  u.commitments.insert("combat_move");
}
bool landingAfter(const State &s, const Id &id, const std::vector<Id> &path) {
  auto after = s.clone();
  moveAircraft(after, id, path);
  return airLandingPlanAvailable(after);
}
std::vector<Id> portDefenders(const State &s, const Id &facility,
                              const Id &owner) {
  std::vector<Id> out;
  const auto &f = s.facilities.at(facility);
  for (const auto &[id, u] : s.units)
    if (hostile(s, owner, u.owner) &&
        (berth(u) == facility ||
         (u.zone == f.zone && !u.carriedBy &&
          (u.type == "fighter" || u.type == "jet_fighter"))))
      out.push_back(id);
  return out;
}
void eraseBattle(State &s, const Id &id) {
  const auto removed = id;
  s.battles.erase(removed);
  s.battleOrder.erase(
      std::remove(s.battleOrder.begin(), s.battleOrder.end(), removed),
      s.battleOrder.end());
}
bool activeBattle(const State &s) {
  for (const auto &[id, b] : s.battles)
    if (b.stage != "awaiting_combat_rules" && b.stage != "air_declared" &&
        b.stage != "naval_declared" && b.stage != "amphibious_declared")
      return true;
  return false;
}
std::vector<Id> shoreCandidates(const State &s, const BattleState &b) {
  const auto water = b.data.require("sea").asString();
  std::vector<Id> out;
  const auto selected = readIds(b.data.require("bombarding"));
  const auto count = b.data.require("cargo").asArray().size();
  if (selected.size() >= count)
    return out;
  for (const auto &[id, u] : s.units) {
    const auto stats = s.definition->catalog->stats(
        u.type, u.damage, catalogContext(s, u.owner, u.zone));
    if (u.owner == b.attacker && u.zone == water && stats.bombardment &&
        !unavailable(u) && !u.commitments.contains("naval_combat") &&
        !u.commitments.contains("shore_bombardment") &&
        std::find(selected.begin(), selected.end(), id) == selected.end())
      out.push_back(id);
  }
  return out;
}
void shoreChoice(State &s, BattleState &b) {
  auto options = std::vector<Action>{action(
      s, b.attacker, "naval_finish_shore_selection", {{"battle", V(b.id)}})};
  for (const auto &id : shoreCandidates(s, b))
    options.push_back(action(s, b.attacker, "naval_select_bombardment",
                             {{"battle", V(b.id)}, {"unit", V(id)}}));
  decision(s, b.attacker, "naval_shore_selection", b.id, std::move(options));
}
void beginAssaultLand(State &s, const Id &id) {
  const auto prep = s.battles.at(id);
  const auto cargo = readIds(prep.data.require("cargo"));
  const auto water = prep.data.require("sea").asString();
  std::vector<Id> attackers;
  std::vector<Id> waiting;
  std::map<Id, Id> origins;
  bool defended = false;
  for (const auto &[unit, u] : s.units)
    if (u.zone == prep.zone && !u.carriedBy &&
        hostile(s, prep.attacker, u.owner) &&
        (unitClass(s, u, "land") || isAircraft(s, u)))
      defended = true;
  for (const auto &c : cargo) {
    if (!s.units.contains(c) || !s.units.at(c).carriedBy)
      continue;
    auto &u = s.units.at(c);
    const auto transport = *u.carriedBy;
    if (!s.units.contains(transport))
      continue;
    const auto attackTransport =
        s.units.at(transport).type == "attack_naval_transport";
    if (defended && !attackTransport && !unitClass(s, u, "infantry_class")) {
      waiting.push_back(c);
      continue;
    }
    detachCargo(s, transport, c, prep.zone);
    u.commitments.insert("amphibious_assault");
    u.commitments.insert("combat_move");
    u.movementRemaining = 0;
    u.turnFlags["from_attack_naval_transport"] = attackTransport;
    u.gameFlags["amphibious_transport:" + transport] = 1;
    attackers.push_back(c);
    origins[c] = water;
  }
  eraseBattle(s, id);
  if (!attackers.empty()) {
    const auto battle =
        registerLandBattle(s, prep.zone, prep.attacker, attackers, origins);
    s.battles.at(battle).flags["amphibious_assault"] = 1;
    s.battles.at(battle).flags["shore_resolved"] = 1;
    if (prep.attacker == "japan") {
      auto &flags = s.nations.at("japan").turnFlags;
      const bool selected = flag(flags, "surprise_attack_zone:" + water);
      const bool seaUsed = flag(flags, "surprise_attack_naval_sea:" + water);
      const bool alreadyLinked =
          std::any_of(flags.begin(), flags.end(), [](const auto &entry) {
            return entry.second &&
                   entry.first.rfind("surprise_attack_linked_land:", 0) == 0;
          });
      if (!alreadyLinked &&
          (seaUsed || (selected && !flag(flags, "surprise_attack_used")))) {
        flags["surprise_attack_used"] = 1;
        flags["surprise_attack_linked_land:" + prep.zone] = 1;
        s.battles.at(battle).flags["japanese_surprise_attack"] = 1;
      }
    }
    put(s.battles.at(battle), "amphibious_waiting", ids(waiting));
    put(s.battles.at(battle), "amphibious_sea", V(water));
  } else if (!waiting.empty()) {
    for (auto &[battle, b] : s.battles)
      if (b.zone == prep.zone && b.attacker == prep.attacker &&
          b.stage == "awaiting_combat_rules") {
        put(b, "amphibious_waiting", ids(waiting));
        put(b, "amphibious_sea", V(water));
        b.flags["amphibious_assault"] = 1;
        break;
      }
  }
}
void chooseShoreCasualty(State &s, BattleState &b) {
  auto hits = b.data.require("shore_hits").asArray();
  int index = b.data.require("shore_hit_index").asInt();
  while (index < static_cast<int>(hits.size())) {
    const auto &h = hits[index];
    std::vector<Id> eligible;
    for (const auto &v : h.require("eligible").asArray())
      if (s.units.contains(v.asString()))
        eligible.push_back(v.asString());
    if (eligible.empty()) {
      put(b, "shore_hit_index", V(static_cast<double>(++index)));
      continue;
    }
    const auto owner = h.require("owner").asString();
    if (const auto *proposal = b.data.find("shore_proposal");
        proposal && !proposal->asString().empty()) {
      auto consents = b.data.require("shore_consents").asObject();
      for (const auto &unit : eligible) {
        const auto nation = s.units.at(unit).owner;
        const auto player = politicalPlayer(s, nation);
        if (player != politicalPlayer(s, owner) && !consents.contains(player)) {
          decision(
              s, nation, "naval_shore_consent", b.id,
              {action(s, nation, "naval_shore_accept", {{"battle", V(b.id)}}),
               action(s, nation, "naval_shore_dispute",
                      {{"battle", V(b.id)}})});
          return;
        }
      }
      const auto unit = proposal->asString();
      put(b, "shore_proposal", V(Id{}));
      if (s.units.contains(unit)) {
        auto &u = s.units.at(unit);
        if (ship(s, u) &&
            u.damage + 1 < s.definition->catalog->unit(u.type).maxHits)
          ++u.damage;
        else
          removePoliticalUnits(s, {unit});
      }
      put(b, "shore_hit_index", V(static_cast<double>(++index)));
      continue;
    }
    std::vector<Action> options;
    for (const auto &unit : eligible)
      options.push_back(action(s, owner, "naval_shore_casualty",
                               {{"battle", V(b.id)}, {"unit", V(unit)}}));
    decision(s, owner, "naval_shore_casualty", b.id, std::move(options));
    return;
  }
  beginAssaultLand(s, b.id);
}
void rollShore(State &s, BattleState &b) {
  A shots;
  std::vector<Id> defenders;
  for (const auto &[id, u] : s.units)
    if (u.zone == b.zone && !u.carriedBy && hostile(s, b.attacker, u.owner) &&
        (unitClass(s, u, "land") || isAircraft(s, u)))
      defenders.push_back(id);
  bool fort = false;
  const auto water = b.data.require("sea").asString();
  for (const auto &[id, f] : s.facilities)
    if (f.zone == b.zone && f.type == "fortification" && !f.damage &&
        (flag(f.flags, "border:" + water) || flag(f.flags, "border_" + water) ||
         flag(f.flags, "towards_" + water)))
      fort = true;
  std::set<Id> attackingShips;
  for (const auto &v : b.data.require("bombarding").asArray()) {
    const auto id = v.asString();
    if (!s.units.contains(id))
      continue;
    auto &u = s.units.at(id);
    const auto stats = s.definition->catalog->stats(
        u.type, u.damage, catalogContext(s, u.owner, u.zone));
    if (!stats.bombardment)
      continue;
    u.commitments.insert("shore_bombardment");
    u.turnFlags["assault_zone:" + b.zone] = 1;
    attackingShips.insert(id);
    for (int n = 0; n < std::max(1, stats.bombardmentDice); ++n)
      shots.emplace_back(
          O{{"threshold", V(static_cast<double>(std::max(
                              1, *stats.bombardment - (fort ? 1 : 0))))},
            {"owner", V(b.defender)},
            {"eligible", ids(defenders)}});
  }
  for (const auto &c : b.data.require("cargo").asArray())
    if (s.units.contains(c.asString()) && s.units.at(c.asString()).carriedBy)
      attackingShips.insert(*s.units.at(c.asString()).carriedBy);
  std::vector<Id> targets(attackingShips.begin(), attackingShips.end());
  for (auto &[id, f] : s.facilities)
    if (f.zone == b.zone && f.type == "coastal_artillery" && !f.damage) {
      bool border =
          flag(f.flags, "border:" + water) || flag(f.flags, "towards_" + water);
      if (const auto *metadata = s.definition->geography.find("facilities"))
        if (const auto *entry = metadata->find(id))
          if (const auto *access = entry->find("sea_accesses"))
            for (const auto &v : access->asArray())
              if (v.asString() == water)
                border = true;
      if (!border)
        continue;
      const auto turn = static_cast<int>(s.clock.playerTurnSerial + 1);
      if (flag(f.flags, "coastal_fire_turn") != turn) {
        f.flags["coastal_fire_turn"] = turn;
        f.flags["coastal_shots_used"] = 0;
      }
      const int shotsAvailable =
          std::max(0, 3 - flag(f.flags, "coastal_shots_used"));
      const int count =
          std::min(shotsAvailable, static_cast<int>(targets.size()));
      f.flags["coastal_shots_used"] += count;
      for (int n = 0; n < count; ++n)
        shots.emplace_back(O{{"threshold", V(3.0)},
                             {"owner", V(b.attacker)},
                             {"eligible", ids(targets)}});
    }
  put(b, "shore_shots", V(shots));
  b.stage = "amphibious_shore_roll";
  if (shots.empty()) {
    beginAssaultLand(s, b.id);
    return;
  }
  ChanceRequest request;
  request.id = b.id + "_shore";
  request.purpose = "naval_shore_roll";
  request.nation = b.attacker;
  request.continuation = b.id;
  request.dice.assign(shots.size(), DieSpec{});
  s.chance = std::move(request);
}
bool canBerth(const State &s, const UnitState &u, const Id &facility) {
  if (!ship(s, u) || u.carriedBy || !berth(u).empty() || unavailable(u))
    return false;
  for (const auto &[id, other] : s.units)
    if (movementController(s, other.owner) &&
        (flag(other.turnFlags, "air_in_flight") ||
         flag(other.turnFlags, "must_withdraw_from_chinese_gift")))
      return false;
  const auto &f = s.facilities.at(facility);
  if (f.damage || !s.territories.at(f.zone).possessor ||
      !friendly(s, u.owner, *s.territories.at(f.zone).possessor))
    return false;
  if (facilityBlockaded(s, u.owner, facility))
    return false;
  const auto seas = navalFacilitySeaZones(s, facility);
  if (std::find(seas.begin(), seas.end(), u.zone) == seas.end())
    return false;
  if (unitClass(s, u, "submarine")) {
    if (f.type != "submarine_base")
      return false;
  } else if (f.type != "major_port" && f.type != "major_dockyard" &&
             f.type != "major_shipyard")
    return false;
  if (unitClass(s, u, "carrier") && !u.cargo.empty())
    return false;
  std::set<Id> assaults;
  for (const auto &[k, v] : u.turnFlags)
    if (v && k.rfind("assault_zone:", 0) == 0)
      assaults.insert(k.substr(13));
  if (!assaults.empty() &&
      (assaults.size() != 1 || !assaults.contains(f.zone) ||
       *s.territories.at(f.zone).possessor != u.owner))
    return false;
  for (const auto &[key, value] : u.turnFlags)
    if (value && key.rfind("naval_strategic_destination:", 0) == 0 &&
        key.substr(Id("naval_strategic_destination:").size()) != facility)
      return false;
  for (const auto &c : u.commitments)
    if (c.rfind("strategic_destination:", 0) == 0 && c.substr(22) != facility)
      return false;
  return true;
}
void beginEvacuationCombat(State &s, const Id &facility) {
  for (const auto &id : s.battleOrder) {
    const auto &b = s.battles.at(id);
    const auto *port = b.data.find("port_evacuation");
    if (port && port->asString() == facility && b.stage == "naval_declared") {
      s.flags["immediate_naval_battles"] = 1;
      beginNavalBattle(s, id);
      return;
    }
  }
}
void commitEvacuation(State &s, const Id &facility, int moved,
                      const A &selected) {
  std::map<std::pair<Id, Id>, std::vector<Id>> fleets;
  for (const auto &entry : selected) {
    const auto id = entry.require("unit").asString();
    const auto water = entry.require("sea").asString();
    auto &u = s.units.at(id);
    require(berth(u) == facility && !unavailable(u),
            "Selected evacuation ship is no longer available");
    u.gameFlags.erase("in_port:" + facility);
    u.zone = water;
    for (const auto &cargo : u.cargo)
      s.units.at(cargo).zone = water;
    fleets[{water, u.owner}].push_back(id);
  }
  for (const auto &[destination, defenders] : fleets) {
    const auto &[water, owner] = destination;
    const bool fight =
        std::any_of(s.units.begin(), s.units.end(), [&](const auto &entry) {
          const auto &u = entry.second;
          return u.zone == water && !u.carriedBy &&
                 hostile(s, owner, u.owner) &&
                 unitClass(s, u, "surface_warship");
        });
    if (!fight)
      continue;
    std::vector<Id> attackers;
    std::map<Id, Id> origins;
    for (const auto &[id, u] : s.units)
      if (u.zone == water && hostile(s, owner, u.owner) &&
          (ship(s, u) || isAircraft(s, u))) {
        attackers.push_back(id);
        if (ship(s, u) && movementController(s, u.owner) &&
            u.commitments.contains("combat_move") && !u.route.empty() &&
            u.route.back() == water) {
          const auto origin =
              u.route.size() > 1 ? u.route[u.route.size() - 2] : u.turnOrigin;
          if (sea(s, origin) && adjacent(s, origin, water) &&
              flag(u.turnFlags, "naval_last_origin:" + origin) ==
                  static_cast<int>(s.clock.playerTurnSerial + 1))
            origins[id] = origin;
        }
      }
    // RCL-014: ships slipping out defend against the enemy force at sea,
    // including when neither fleet owns the current calendar turn. Only a
    // real entry sea from this turn's Combat Movement permits naval retreat;
    // the damaged port does not create one for either fleet.
    const auto battle = registerNavalBattle(
        s, water, s.units.at(attackers.front()).owner, attackers, origins,
        V(O{{"context", V(Id("standard"))},
            {"defenders", V(ids(defenders))},
            {"port_evacuation", V(facility)},
            {"evacuated", V(static_cast<double>(moved + selected.size()))},
            {"evacuation_selection_complete", V(true)}}));
    s.battles.at(battle).flags["immediate"] = 1;
    s.flags["immediate_naval_battles"] = 1;
  }
  beginEvacuationCombat(s, facility);
}
void evacuationChoice(State &s, const Id &facility, int moved,
                      const A &selected = {}, const A &declined = {}) {
  if (!s.facilities.contains(facility))
    return;
  if (moved + selected.size() >= 3) {
    commitEvacuation(s, facility, moved, selected);
    return;
  }
  std::set<Id> chosen, finished;
  for (const auto &entry : selected)
    chosen.insert(entry.require("unit").asString());
  for (const auto &owner : declined)
    finished.insert(owner.asString());
  std::vector<Action> options;
  Id owner;
  for (const auto &[id, u] : s.units)
    if (berth(u) == facility && !unavailable(u) && !chosen.contains(id) &&
        !finished.contains(u.owner)) {
      if (owner.empty())
        owner = u.owner;
      if (u.owner != owner)
        continue;
      for (const auto &water : navalFacilitySeaZones(s, facility))
        options.push_back(action(s, owner, "naval_evacuate_port",
                                 {{"facility", V(facility)},
                                  {"unit", V(id)},
                                  {"sea", V(water)},
                                  {"moved", V(static_cast<double>(moved))},
                                  {"selected", V(selected)},
                                  {"declined", V(declined)}}));
    }
  if (options.empty()) {
    commitEvacuation(s, facility, moved, selected);
    return;
  }
  options.push_back(action(s, owner,
                           selected.empty() ? "naval_decline_evacuation"
                                            : "naval_finish_evacuation",
                           {{"facility", V(facility)},
                            {"moved", V(static_cast<double>(moved))},
                            {"selected", V(selected)},
                            {"declined", V(declined)}}));
  decision(s, owner, "naval_port_evacuation", facility, std::move(options));
}
} // namespace

std::vector<Action> navalOperationActions(const State &s) {
  std::vector<Action> out;
  if (s.chance || !s.decisions.empty())
    return out;
  const bool active = activeBattle(s);
  if ((s.clock.phase == Phase::CombatMovement ||
       s.clock.phase == Phase::Combat) &&
      !active) {
    if (s.clock.phase == Phase::CombatMovement &&
        s.currentNation() == "japan" &&
        flag(s.nations.at("japan").turnFlags, "surprise_attack_available")) {
      const auto &flags = s.nations.at("japan").turnFlags;
      const bool selected =
          std::any_of(flags.begin(), flags.end(), [](const auto &entry) {
            return entry.second &&
                   entry.first.rfind("surprise_attack_zone:", 0) == 0;
          });
      if (!selected)
        for (const auto &[zone, n] :
             s.definition->geography.require("nodes").asObject()) {
          if (!sea(s, zone))
            continue;
          bool target = false;
          for (const auto &[unit, u] : s.units)
            if (u.zone == zone &&
                flag(flags, "surprise_attack_target:" + u.owner))
              target = true;
          for (const auto &e : n.require("neighbors").asArray()) {
            const auto land = e.require("neighbor_id").asString();
            if (s.territories.contains(land) &&
                s.territories.at(land).possessor &&
                flag(flags, "surprise_attack_target:" +
                                *s.territories.at(land).possessor))
              target = true;
          }
          if (target)
            out.push_back(action(s, "japan", "naval_select_surprise_zone",
                                 {{"zone", V(zone)}}));
        }
    }
    for (const auto &[id, u] : s.units) {
      if (!movementController(s, u.owner) || unavailable(u))
        continue;
      if (s.clock.phase == Phase::Combat &&
          (!flag(u.turnFlags, "naval_screening_continuing") ||
           u.commitments.contains("naval_combat")))
        continue;
      // Aircraft on Maritime Air Patrol attack only Enemy ships in their own
      // sea zone, in the Combat Phase (RB 9.3.1): see naval_patrol_attack.
      if (isAircraft(s, u) && !flag(u.gameFlags, "on_map") &&
          !u.commitments.contains("combat") &&
          !u.commitments.contains("air_battle") &&
          !flag(u.turnFlags, "air_in_flight")) {
        std::optional<std::map<Id, std::vector<Id>>> paths;
        for (const auto &[zone, n] :
             s.definition->geography.require("nodes").asObject()) {
          if (!sea(s, zone))
            continue;
          bool enemy = false;
          for (const auto &[other, v] : s.units)
            if (v.zone == zone && hostile(s, u.owner, v.owner) &&
                !v.carriedBy &&
                ((ship(s, v) && !unitClass(s, v, "submarine")) ||
                 isAircraft(s, v)))
              enemy = true;
          if (!paths)
            paths = combatPaths(s, id);
          const auto found = paths->find(zone);
          if (found == paths->end() || !landingAfter(s, id, found->second))
            continue;
          const auto &path = found->second;
          if (enemy && catalogStats(s, u.type, u.damage, u.owner).attack)
            out.push_back(action(
                s, s.currentNation(), "naval_air_attack",
                {{"unit", V(id)}, {"path", ids(path)}, {"sea", V(zone)}}));
          if (u.type != "fighter" && u.type != "jet_fighter" &&
              u.type != "seaplane" && u.type != "tactical_bomber" &&
              u.type != "medium_bomber")
            continue;
          for (const auto &[fid, f] : s.facilities) {
            const auto accesses = navalFacilitySeaZones(s, fid);
            if (std::find(accesses.begin(), accesses.end(), zone) ==
                accesses.end())
              continue;
            const auto defenders = portDefenders(s, fid, u.owner);
            if (std::none_of(
                    defenders.begin(), defenders.end(),
                    [&](const Id &d) { return ship(s, s.units.at(d)); }))
              continue;
            out.push_back(action(s, s.currentNation(), "naval_port_attack",
                                 {{"unit", V(id)},
                                  {"path", ids(path)},
                                  {"sea", V(zone)},
                                  {"facility", V(fid)}}));
          }
        }
      }
      if ((!unitClass(s, u, "naval_transport") &&
           !(u.owner == "japan" && u.type == "destroyer")) ||
          !sea(s, u.zone) || occupiedForAssault(s, u.owner, u.zone))
        continue;
      for (const auto &c : u.cargo) {
        if (!s.units.contains(c) || s.units.at(c).owner != u.owner ||
            !unitClass(s, s.units.at(c), "land") ||
            s.units.at(c).commitments.contains("assault_declared") ||
            u.commitments.contains("unloaded_noncombat"))
          continue;
        for (const auto &e : node(s, u.zone).require("neighbors").asArray()) {
          const auto land = e.require("neighbor_id").asString();
          if (!s.territories.contains(land) ||
              !s.territories.at(land).possessor ||
              !hostile(s, u.owner, *s.territories.at(land).possessor))
            continue;
          out.push_back(action(
              s, s.currentNation(), "naval_declare_assault",
              {{"transport", V(id)}, {"cargo", V(c)}, {"zone", V(land)}}));
        }
      }
    }
  }
  if (s.clock.phase == Phase::Combat && !active) {
    for (const auto &[id, b] : s.battles)
      if (b.stage == "amphibious_declared" &&
          !occupiedForAssault(s, b.attacker, b.data.require("sea").asString()))
        out.push_back(action(s, s.currentNation(), "naval_begin_assault",
                             {{"battle", V(id)}}));
    for (const auto &[id, u] : s.units)
      if (movementController(s, u.owner) && flag(u.gameFlags, "on_map") &&
          !u.commitments.contains("naval_combat")) {
        bool enemy = false;
        for (const auto &[other, v] : s.units)
          if (v.zone == u.zone && ship(s, v) && hostile(s, u.owner, v.owner))
            enemy = true;
        if (enemy)
          out.push_back(action(s, s.currentNation(), "naval_patrol_attack",
                               {{"unit", V(id)}}));
      }
  }
  if (s.clock.phase == Phase::NonCombatMovement && !active)
    for (const auto &[id, u] : s.units)
      if (movementController(s, u.owner))
        for (const auto &[fid, f] : s.facilities)
          if (canBerth(s, u, fid)) {
            out.push_back(action(
                s, s.currentNation(), "naval_enter_port",
                {{"unit", V(id)}, {"facility", V(fid)}, {"unload", V(false)}}));
            if (std::any_of(u.cargo.begin(), u.cargo.end(), [&](const Id& cargo) {
                  return s.units.at(cargo).owner == u.owner;
                }))
              out.push_back(action(s, s.currentNation(), "naval_enter_port",
                                   {{"unit", V(id)},
                                    {"facility", V(fid)},
                                    {"unload", V(true)}}));
          }
  if (s.clock.phase == Phase::PlaceUnits)
    for (const auto &[id, u] : s.units)
      if (flag(u.gameFlags, "captured_port_pending:" + s.currentNation()))
        out.push_back(action(s, s.currentNation(), "naval_roll_capture",
                             {{"unit", V(id)}}));
  return out;
}

bool applyNavalOperationAction(State &s, const Action &a) {
  if (a.kind == "naval_select_surprise_zone") {
    s.nations.at("japan").turnFlags["surprise_attack_zone:" +
                                    a.parameters.require("zone").asString()] =
        1;
    return true;
  }
  if (a.kind == "naval_air_attack" || a.kind == "naval_port_attack") {
    const auto id = a.parameters.require("unit").asString();
    const auto owner = s.units.at(id).owner;
    const auto origin = s.units.at(id).zone;
    const auto water = a.parameters.require("sea").asString();
    moveAircraft(s, id, readIds(a.parameters.require("path")));
    require(airLandingPlanAvailable(s),
            "Naval air attack has no joint landing plan");
    // This is a declared Combat attack, as with shared land/strategic air
    // missions. Keep its aircraft committed until the naval battle resolves.
    s.units.at(id).commitments.insert("air_combat");
    O options{{"context", V(Id(a.kind == "naval_port_attack" ? "port_attack"
                                                             : "standard"))}};
    if (a.kind == "naval_port_attack") {
      const auto facility = a.parameters.require("facility").asString();
      options["facility"] = V(facility);
      options["sea"] = V(water);
      options["defenders"] = ids(portDefenders(s, facility, owner));
    }
    registerNavalBattle(s, water, owner, {id}, {{id, origin}}, V(options));
    return true;
  }
  if (a.kind == "naval_patrol_attack") {
    const auto id = a.parameters.require("unit").asString();
    const auto &u = s.units.at(id);
    registerNavalBattle(
        s, u.zone, u.owner, {id}, {{id, u.zone}},
        V(O{{"context", V(Id("standard"))}, {"map_attack", V(true)}}));
    return true;
  }
  if (a.kind == "naval_declare_assault") {
    const auto t = a.parameters.require("transport").asString(),
               c = a.parameters.require("cargo").asString();
    const auto zone = a.parameters.require("zone").asString();
    auto &transport = s.units.at(t);
    require(!occupiedForAssault(s, transport.owner, transport.zone),
            "Clear the launching sea before declaring the amphibious assault");
    require(s.units.at(c).carriedBy == t,
            "Assault cargo is not aboard transport");
    transport.movementRemaining = 0;
    transport.commitments.insert("unloaded_combat");
    transport.turnFlags["naval_combat_unloaded"] = 1;
    transport.turnFlags["naval_unloaded"] = 1;
    transport.turnFlags["assault_zone:" + zone] = 1;
    s.units.at(c).commitments.insert("assault_declared");
    BattleState *existing = nullptr;
    for (auto &[id, b] : s.battles)
      if (b.stage == "amphibious_declared" && b.zone == zone &&
          b.attacker == transport.owner &&
          b.data.require("sea").asString() == transport.zone)
        existing = &b;
    if (!existing) {
      BattleState b;
      b.id = "amphibious_" + std::to_string(++s.flags["amphibious_sequence"]);
      b.zone = zone;
      b.attacker = transport.owner;
      b.defender = *s.territories.at(zone).possessor;
      b.stage = "amphibious_declared";
      b.flags["amphibious_preparation"] = 1;
      b.data = V(O{{"sea", V(transport.zone)},
                   {"cargo", V(A{})},
                   {"bombarding", V(A{})}});
      const auto id = b.id;
      s.battles.emplace(id, std::move(b));
      s.battleOrder.push_back(id);
      existing = &s.battles.at(id);
    }
    auto cargo = existing->data.require("cargo").asArray();
    require(std::none_of(cargo.begin(), cargo.end(),
                         [&](const V &v) { return v.asString() == c; }),
            "Cargo already declared");
    cargo.emplace_back(c);
    put(*existing, "cargo", V(cargo));
    recordLandAttack(s, transport.owner, zone);
    return true;
  }
  if (a.kind == "naval_begin_assault") {
    auto &b = s.battles.at(a.parameters.require("battle").asString());
    require(
        !occupiedForAssault(s, b.attacker, b.data.require("sea").asString()),
        "Sea must be cleared before assault");
    b.stage = "amphibious_shore_selection";
    shoreChoice(s, b);
    return true;
  }
  if (a.kind == "naval_select_bombardment" ||
      a.kind == "naval_finish_shore_selection") {
    release(s, a);
    auto &b = s.battles.at(a.parameters.require("battle").asString());
    if (a.kind == "naval_finish_shore_selection")
      rollShore(s, b);
    else {
      auto selected = b.data.require("bombarding").asArray();
      selected.push_back(a.parameters.require("unit"));
      put(b, "bombarding", V(selected));
      shoreChoice(s, b);
    }
    return true;
  }
  if (a.kind == "naval_shore_casualty") {
    release(s, a);
    const auto id = a.parameters.require("battle").asString();
    const auto unit = a.parameters.require("unit").asString();
    auto &b = s.battles.at(id);
    const auto &hit = b.data.require("shore_hits")
                          .asArray()
                          .at(b.data.require("shore_hit_index").asInt());
    std::set<Id> players;
    for (const auto &candidate : hit.require("eligible").asArray())
      if (s.units.contains(candidate.asString()))
        players.insert(
            politicalPlayer(s, s.units.at(candidate.asString()).owner));
    if (players.size() > 1 && !flag(b.flags, "shore_dispute_decided")) {
      put(b, "shore_proposal", V(unit));
      put(b, "shore_consents", V(O{}));
      chooseShoreCasualty(s, b);
      return true;
    }
    auto &u = s.units.at(unit);
    if (ship(s, u) &&
        u.damage + 1 < s.definition->catalog->unit(u.type).maxHits)
      ++u.damage;
    else
      removePoliticalUnits(s, {unit});
    b.flags.erase("shore_dispute_decided");
    put(b, "shore_hit_index",
        V(static_cast<double>(b.data.require("shore_hit_index").asInt() + 1)));
    chooseShoreCasualty(s, b);
    return true;
  }
  if (a.kind == "naval_shore_accept" || a.kind == "naval_shore_dispute") {
    release(s, a);
    auto &b = s.battles.at(a.parameters.require("battle").asString());
    if (a.kind == "naval_shore_accept") {
      auto consents = b.data.require("shore_consents").asObject();
      consents[a.player] = V(true);
      put(b, "shore_consents", V(consents));
      chooseShoreCasualty(s, b);
    } else {
      put(b, "shore_proposal", V(Id{}));
      const auto &hit = b.data.require("shore_hits")
                            .asArray()
                            .at(b.data.require("shore_hit_index").asInt());
      std::map<Id, Id> representatives;
      for (const auto &v : hit.require("eligible").asArray())
        if (s.units.contains(v.asString())) {
          const auto owner = s.units.at(v.asString()).owner;
          representatives[politicalPlayer(s, owner)] = owner;
        }
      A nations;
      for (const auto &[player, nation] : representatives)
        nations.emplace_back(nation);
      put(b, "shore_disputing_nations", V(nations));
      ChanceRequest request{
          b.id + "_shore_dispute", "naval_shore_dispute", b.attacker, b.id, {}};
      request.dice.assign(nations.size(), DieSpec{});
      s.chance = std::move(request);
    }
    return true;
  }
  if (a.kind == "naval_enter_port") {
    const auto id = a.parameters.require("unit").asString(),
               f = a.parameters.require("facility").asString();
    auto &u = s.units.at(id);
    require(canBerth(s, u, f), "Ship cannot enter this port");
    s.flags["naval_berthing"] = 1;
    u.zone = s.facilities.at(f).zone;
    u.gameFlags["in_port:" + f] = 1;
    u.gameFlags.erase("raider");
    u.commitments.erase("raider");
    for (const auto &c : u.cargo)
      s.units.at(c).zone = u.zone;
    if (a.parameters.require("unload").asBool()) {
      auto cargo = u.cargo;
      for (const auto &c : cargo) {
        auto &v = s.units.at(c);
        if (v.owner != u.owner)
          continue;
        detachCargo(s, id, c, u.zone);
        v.movementRemaining = 0;
        v.gameFlags["port_unloaded_round"] = s.clock.roundIndex + 1;
        v.commitments.insert("transport_unloaded");
      }
    }
    return true;
  }
  if (a.kind == "naval_roll_capture") {
    const auto id = a.parameters.require("unit").asString();
    s.chance = ChanceRequest{"capture_" + id,
                             "naval_port_capture",
                             s.currentNation(),
                             id,
                             {DieSpec{}}};
    return true;
  }
  if (a.kind == "naval_evacuate_port" || a.kind == "naval_decline_evacuation" ||
      a.kind == "naval_finish_evacuation") {
    release(s, a);
    const auto &p = a.parameters;
    const auto facility = p.require("facility").asString();
    auto selected = p.find("selected") ? p.require("selected").asArray() : A{};
    auto declined = p.find("declined") ? p.require("declined").asArray() : A{};
    const int moved = p.find("moved") ? p.require("moved").asInt() : 0;
    if (a.kind == "naval_evacuate_port")
      selected.emplace_back(
          O{{"unit", p.require("unit")}, {"sea", p.require("sea")}});
    else
      declined.emplace_back(a.nation);
    evacuationChoice(s, facility, moved, selected, declined);
    return true;
  }
  return false;
}

bool applyNavalOperationChance(State &s, const ChanceRequest &r,
                               const ChanceOutcome &o) {
  if (r.purpose == "naval_shore_dispute") {
    auto &b = s.battles.at(r.continuation);
    const auto results = effectiveResults(r, o);
    const auto nations = b.data.require("shore_disputing_nations").asArray();
    const int top = *std::max_element(results.begin(), results.end());
    A tied;
    for (std::size_t i = 0; i < results.size(); ++i)
      if (results[i] == top)
        tied.push_back(nations[i]);
    if (tied.size() > 1) {
      put(b, "shore_disputing_nations", V(tied));
      auto again = r;
      again.dice.resize(tied.size());
      s.chance = again;
      return true;
    }
    const auto owner = tied.front().asString();
    const auto &hit = b.data.require("shore_hits")
                          .asArray()
                          .at(b.data.require("shore_hit_index").asInt());
    std::vector<Action> options;
    for (const auto &v : hit.require("eligible").asArray())
      if (s.units.contains(v.asString()))
        options.push_back(action(s, owner, "naval_shore_casualty",
                                 {{"battle", V(b.id)}, {"unit", v}}));
    b.flags["shore_dispute_decided"] = 1;
    if (options.empty())
      chooseShoreCasualty(s, b);
    else
      decision(s, owner, "naval_shore_casualty", b.id, std::move(options));
    return true;
  }
  if (r.purpose == "naval_shore_roll") {
    auto &b = s.battles.at(r.continuation);
    const auto result = effectiveResults(r, o);
    const auto shots = b.data.require("shore_shots").asArray();
    A hits;
    for (std::size_t i = 0; i < shots.size(); ++i)
      if (result[i] <= shots[i].require("threshold").asInt())
        hits.push_back(shots[i]);
    put(b, "shore_hits", V(hits));
    put(b, "shore_hit_index", V(0.0));
    b.stage = "amphibious_shore_casualties";
    chooseShoreCasualty(s, b);
    return true;
  }
  if (r.purpose == "naval_port_capture") {
    if (!s.units.contains(r.continuation))
      return true;
    if (effectiveResults(r, o).front() <= 9)
      removePoliticalUnits(s, {r.continuation});
    else {
      auto &u = s.units.at(r.continuation);
      u.owner = r.nation;
      u.gameFlags.erase("captured_port_pending:" + r.nation);
      if (flag(u.gameFlags, "skeleton_crew_until_own_turn") ||
          flag(u.gameFlags, "skeleton_crew"))
        u.gameFlags["skeleton_crew_until_own_turn"] =
            navalCompletedTurns(s, r.nation) + 2;
      for (const auto &id : u.cargo)
        s.units.at(id).owner = r.nation;
    }
    return true;
  }
  return false;
}
bool navalOperationPhaseComplete(const State &s) {
  for (const auto &[id, b] : s.battles)
    if (flag(b.flags, "amphibious_preparation")) {
      if (s.clock.phase == Phase::CombatMovement &&
          b.stage == "amphibious_declared")
        continue;
      return false;
    }
  if (s.clock.phase == Phase::PlaceUnits)
    for (const auto &[id, u] : s.units)
      if (flag(u.gameFlags, "captured_port_pending:" + s.currentNation()))
        return false;
  return true;
}
void finishNavalOperationPhase(State &s) {
  s.flags.erase("naval_berthing");
  if (s.clock.phase == Phase::Combat) {
    std::vector<Id> lost;
    for (auto &[id, u] : s.units) {
      if (!unitClass(s, u, "naval"))
        continue;
      Id origin;
      for (const auto &c : u.commitments)
        if (c.rfind("naval_scramble_origin:", 0) == 0)
          origin = c.substr(22);
      if (origin.empty())
        continue;
      if (!s.facilities.contains(origin) ||
          !s.territories.at(s.facilities.at(origin).zone).possessor ||
          !friendly(
              s, u.owner,
              *s.territories.at(s.facilities.at(origin).zone).possessor)) {
        lost.push_back(id);
        continue;
      }
      u.zone = s.facilities.at(origin).zone;
      u.gameFlags["in_port:" + origin] = 1;
      for (const auto &cargo : u.cargo)
        s.units.at(cargo).zone = u.zone;
      u.commitments.erase("naval_scramble_origin:" + origin);
      u.commitments.erase("naval_scrambled");
    }
    removePoliticalUnits(s, std::set<Id>(lost.begin(), lost.end()));
  }
}
void preparePortLandDefence(State &s, const Id &id) {
  auto &b = s.battles.at(id);
  if (flag(b.flags, "port_crew_prepared"))
    return;
  b.flags["port_crew_prepared"] = 1;
  std::vector<UnitState> crews;
  for (const auto &[shipId, u] : s.units)
    if (u.zone == b.zone && !berth(u).empty() &&
        hostile(s, b.attacker, u.owner) &&
        !flag(u.gameFlags, "skeleton_crew_until_own_turn") &&
        (u.type == "heavy_cruiser" || u.type == "battlecruiser" ||
         unitClass(s, u, "carrier") || u.type == "battleship" ||
         u.type == "heavy_battleship")) {
      UnitState crew;
      crew.id = "ship_crew_" + b.id + "_" + shipId;
      crew.type = "militia";
      crew.owner = u.owner;
      crew.zone = crew.turnOrigin = b.zone;
      crew.movementAllowance = crew.movementRemaining = 0;
      crew.gameFlags["ship_crew:" + shipId] = 1;
      crews.push_back(std::move(crew));
    }
  for (auto &u : crews) {
    b.defenders.push_back(u.id);
    s.units.emplace(u.id, std::move(u));
  }
}
void resolveCapturedPorts(State &s, const Id &landZone, const Id &captor) {
  for (auto &[id, u] : s.units)
    if (u.zone == landZone && !berth(u).empty() && hostile(s, captor, u.owner))
      u.gameFlags["captured_port_pending:" + captor] = 1;
}
void queueDamagedPortEvacuation(State &s, const Id &facility) {
  evacuationChoice(s, facility, 0);
}
void resumeDamagedPortEvacuation(State &s, const Id &facility, int moved) {
  if (moved >= 3) {
    beginEvacuationCombat(s, facility);
    return;
  }
  evacuationChoice(s, facility, moved);
}
void releaseAmphibiousReserves(State &s, const Id &battle) {
  auto &b = s.battles.at(battle);
  const auto *waiting = b.data.find("amphibious_waiting");
  if (!waiting || waiting->asArray().empty())
    return;
  const bool foothold =
      std::any_of(b.attackers.begin(), b.attackers.end(), [&](const Id &id) {
        return s.units.contains(id) && s.units.at(id).zone == b.zone &&
               unitClass(s, s.units.at(id), "land");
      });
  if (!foothold)
    return;
  const auto water = b.data.require("amphibious_sea").asString();
  auto origins = b.data.require("origins").asObject();
  const auto cargo = readIds(*waiting);
  for (const auto &id : cargo)
    if (s.units.contains(id) && s.units.at(id).carriedBy) {
      const auto transport = *s.units.at(id).carriedBy;
      if (!s.units.contains(transport))
        continue;
      detachCargo(s, transport, id, b.zone);
      auto &u = s.units.at(id);
      u.commitments.insert("amphibious_assault");
      u.commitments.insert("combat_move");
      u.movementRemaining = 0;
      u.gameFlags["amphibious_transport:" + transport] = 1;
      b.attackers.push_back(id);
      origins[id] = V(water);
    }
  put(b, "origins", V(origins));
  put(b, "amphibious_waiting", V(A{}));
}

} // namespace game::campaign
