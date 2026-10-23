#include "game/catalog.hpp"
#include "game/land_combat.hpp"
#include "game/movement.hpp"
#include "game/naval.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <functional>
#include <iostream>
#include <stdexcept>

namespace {
using namespace game::campaign;
using V = game::json::Value;
using O = V::Object;
using A = V::Array;
V str(const char *s) { return V(std::string(s)); }
void check(bool ok, const std::string &why) {
  if (!ok)
    throw std::runtime_error(why);
}
void rejects(const std::function<void()> &fn, const std::string &why) {
  try {
    fn();
  } catch (const std::exception &) {
    return;
  }
  throw std::runtime_error(why);
}
const State &baseline() {
  static const auto s = loadScenario(std::filesystem::path(GWRL_SOURCE_DIR) /
                                     "game_content/scenarios/japan_china_1936");
  return s;
}
struct Puzzle {
  O nodes;
  O owners;
  O regions;
  Puzzle() {
    for (const auto *id : {"a", "b", "c", "d", "e", "enemy"})
      land(id, id == std::string("enemy") ? "kmt" : "japan");
  }
  void land(const Id &id, const Id &owner) {
    nodes[id] = V(O{{"id", V(id)},
                    {"name", V(id)},
                    {"type", str("land")},
                    {"terrain", str("normal")},
                    {"is_city", V(false)},
                    {"ipp_value", V(1.0)},
                    {"original_owner", V(owner)},
                    {"neighbors", V(A{})}});
    owners[id] = V(owner);
    regions[id] = str("asia");
  }
  void sea(const Id &id) {
    nodes[id] = V(O{{"id", V(id)},
                    {"type", str("sea")},
                    {"terrain", str("sea")},
                    {"neighbors", V(A{})}});
  }
  void nodeField(const Id &id, const Id &key, V value) {
    auto n = nodes.at(id).asObject();
    n[key] = std::move(value);
    nodes[id] = V(std::move(n));
  }
  void oneEdge(const Id &a, const Id &b, O extra = {}) {
    auto n = nodes.at(a).asObject();
    auto neighbors = n.at("neighbors").asArray();
    O e{{"neighbor_id", V(b)},        {"border_terrain", str("normal")},
        {"passable", V(true)},        {"has_river", V(false)},
        {"river_crossing", V(false)}, {"railway_connection", V(false)},
        {"gauge_change", V(false)},   {"narrow_crossing", V(false)}};
    for (auto &[k, v] : extra)
      e[k] = std::move(v);
    neighbors.emplace_back(std::move(e));
    n["neighbors"] = V(std::move(neighbors));
    nodes[a] = V(std::move(n));
  }
  void link(const Id &a, const Id &b, O extra = {}) {
    oneEdge(a, b, extra);
    oneEdge(b, a, std::move(extra));
  }
  State state(Phase phase = Phase::NonCombatMovement) {
    auto s = baseline().clone();
    Definition def = *s.definition;
    def.scenarioId = "m5_route_puzzle";
    def.geography = V(O{{"nodes", V(nodes)},
                        {"facilities", V(O{})},
                        {"rail_geography", V(O{{"memberships", V(regions)}})}});
    auto rules = def.rules.asObject();
    rules.erase("faction_index");
    rules.erase("movement_profile");
    def.rules = V(std::move(rules));
    for (auto &[id, f] : def.factions)
      f.homeCountry.clear();
    def.factions.at("japan").homeCountry = {"a"};
    def.factions.at("kmt").homeCountry = {"enemy"};
    s.definition = freezeDefinition(std::move(def));
    s.units.clear();
    s.facilities.clear();
    s.rails.clear();
    s.construction.clear();
    s.repairs.clear();
    s.decisions.clear();
    s.battles.clear();
    s.battleOrder.clear();
    s.chance.reset();
    s.flags.clear();
    s.history.clear();
    s.politics = PoliticalState{};
    s.politics.capitals["japan"] = "a";
    s.territories.clear();
    for (const auto &[id, owner] : owners)
      s.territories[id].possessor = owner.asString();
    s.clock.nationIndex = 2;
    s.clock.playerTurnSerial = 2;
    s.clock.phase = phase;
    s.clock.roundIndex = s.clock.completedRounds = 0;
    s.clock.incomeCollected = false;
    for (std::size_t i = 0; i < s.definition->turnOrder.size(); ++i)
      s.completedTurns[s.definition->turnOrder[i]] = i < 2 ? 1 : 0;
    s.nations.at("japan").atWarWith = {"kmt"};
    s.nations.at("kmt").atWarWith = {"japan"};
    s.captureTurnStart();
    return s;
  }
};
void unit(State &s, const Id &id, const Id &zone, const Id &type = "infantry",
          const Id &owner = "japan", int movement = -1) {
  UnitState u;
  u.id = id;
  u.owner = owner;
  u.type = type;
  u.zone = u.turnOrigin = zone;
  u.movementAllowance = u.movementRemaining =
      movement >= 0 ? std::optional<int>(movement)
                    : s.definition->catalog
                          ->stats(type, 0, catalogContext(s, owner, zone))
                          .movement;
  s.units[id] = std::move(u);
}
void port(State &s, const Id &id, const Id &zone, const std::vector<Id> &seas,
          const Id &type = "minor_port") {
  FacilityState f;
  f.id = id;
  f.type = type;
  f.zone = zone;
  for (const auto &sea : seas)
    f.flags["border:" + sea] = 1;
  s.facilities[id] = std::move(f);
}
Action offered(const MovementRules &rules, const State &s, const Id &id,
               const std::vector<Id> &path, MovementMode mode) {
  for (const auto &a : rules.actions(s))
    if (a.kind == "movement_route" &&
        a.parameters.require("unit").asString() == id &&
        a.parameters.require("mode").asString() == toString(mode)) {
      std::vector<Id> candidate;
      for (const auto &x : a.parameters.require("path").asArray())
        candidate.push_back(x.asString());
      if (candidate == path)
        return a;
    }
  throw std::runtime_error("Expected route was not offered");
}

void directionalTerrain() {
  Puzzle p;
  p.link("a", "b");
  p.oneEdge("b", "c",
            {{"border_terrain", str("mountain")}, {"river_crossing", V(true)}});
  p.oneEdge("c", "b");
  p.link("c", "d");
  auto s = p.state();
  unit(s, "tank", "b", "light_armor");
  const auto entered =
      validateRoute(s, {"tank", {"b", "c"}, MovementMode::Ordinary, false});
  check(entered.allowed && entered.exhaustsMovement && entered.approach.river,
        "Directional mountain/river entry lost");
  check(!validateRoute(s,
                       {"tank", {"b", "c", "d"}, MovementMode::Ordinary, false})
             .allowed,
        "Tank traversed terrain that ends movement");
  unit(s, "reverse", "c", "light_armor");
  check(validateRoute(
            s, {"reverse", {"c", "b", "a"}, MovementMode::Ordinary, false})
            .allowed,
        "Origin terrain leaked into reverse entry");
  unit(s, "horse", "b", "cavalry");
  check(validateRoute(s,
                      {"horse", {"b", "c", "d"}, MovementMode::Ordinary, false})
            .allowed,
        "Cavalry mountain movement exemption missing");
  auto def = *s.definition;
  auto nodes = def.geography.require("nodes").asObject();
  auto c = nodes.at("c").asObject();
  c["terrain"] = V(A{str("mountain"), str("desert")});
  nodes["c"] = V(std::move(c));
  auto g = def.geography.asObject();
  g["nodes"] = V(std::move(nodes));
  def.geography = V(std::move(g));
  s.definition = freezeDefinition(std::move(def));
  check(!validateRoute(
             s, {"horse", {"b", "c", "d"}, MovementMode::Ordinary, false})
             .allowed,
        "Cavalry mountain exemption incorrectly erased desert");
}
void hostileStopsAndOrigins() {
  Puzzle p;
  p.link("a", "b");
  p.link("b", "enemy", {{"river_crossing", V(true)}});
  p.link("c", "enemy");
  p.link("enemy", "d");
  auto s = p.state(Phase::CombatMovement);
  unit(s, "west", "a", "light_armor", "japan", 3);
  unit(s, "north", "c", "infantry");
  check(
      !validateRoute(
           s, {"west", {"a", "b", "enemy", "d"}, MovementMode::Ordinary, true})
           .allowed,
      "Unresolved enemy zone did not stop movement");
  MovementRules rules;
  rules.apply(s, offered(rules, s, "west", {"a", "b", "enemy"},
                         MovementMode::Ordinary));
  rules.apply(
      s, offered(rules, s, "north", {"c", "enemy"}, MovementMode::Ordinary));
  check(s.battles.size() == 1 &&
            s.battles.begin()->second.attackers.size() == 2,
        "Contingents did not join one pending battle");
  const auto &origins = s.battles.begin()->second.data.require("origins");
  check(origins.require("west").asString() == "b" &&
            origins.require("north").asString() == "c",
        "Approach origins collapsed to one source");
  check(s.units.at("west").turnOrigin == "a" &&
            s.units.at("west").movementRemaining == 1,
        "Turn origin or exact movement lost");
  check(!validateRoute(s, {"west", {"enemy", "d"}, MovementMode::Ordinary, true}).allowed,
        "Segmenting public actions bypassed the unresolved hostile-zone stop");
  const auto following = rules.actions(s);
  check(std::none_of(following.begin(), following.end(), [](const Action &a) {
    return a.kind == "movement_route" && a.parameters.require("unit").asString() == "west";
  }), "A committed attacker was offered a second movement before its battle resolved");
  const auto restored = State::fromJson(s.definition, s.toJson());
  check(restored.planningKey() == s.planningKey(),
        "Pending movement/battle failed checkpoint roundtrip");
}
void railGaugeDamageCapacity() {
  Puzzle p;
  p.link("a", "b", {{"railway_connection", V(true)}});
  p.link("b", "c",
         {{"railway_connection", V(true)}, {"gauge_change", V(true)}});
  p.regions["c"] = str("soviet_union");
  auto s = p.state();
  unit(s, "one", "a");
  unit(s, "two", "a");
  s.rails["ab"] = {"ab", "a", "b", {}};
  s.rails["bc"] = {"bc", "b", "c", {}};
  check(!validateRoute(
             s, {"one", {"a", "b", "c"}, MovementMode::StrategicRail, false})
             .allowed,
        "Gauge change accepted without technology");
  s.nations.at("japan").technologyStages["improved_logistics"] = 4;
  const auto route = validateRoute(
      s, {"one", {"a", "b", "c"}, MovementMode::StrategicRail, false});
  check(route.allowed && route.regions.size() == 2,
        "Improved Logistics or cross-region accounting missing");
  MovementRules rules;
  rules.apply(s, offered(rules, s, "one", {"a", "b", "c"},
                         MovementMode::StrategicRail));
  check(
      validateRoute(s, {"two", {"a", "b"}, MovementMode::StrategicRail, false})
          .allowed,
      "Improved Logistics did not add one regional move");
  rules.apply(
      s, offered(rules, s, "two", {"a", "b"}, MovementMode::StrategicRail));
  unit(s, "three", "a");
  check(!validateRoute(
             s, {"three", {"a", "b"}, MovementMode::StrategicRail, false})
             .allowed,
        "Asia capacity did not apply after crossing regions");
  auto bombed = p.state();
  unit(bombed, "u", "a");
  bombed.rails["ab"] = {"ab", "a", "b", {{"b", 1}}};
  check(!inSupply(bombed, "japan", "b"), "Bombed rail remained a Supply Path");
  check(!validateRoute(bombed,
                       {"u", {"a", "b"}, MovementMode::StrategicRail, false})
             .allowed,
        "Bombed rail remained usable for strategic movement");
  bombed.rails.at("ab").damageByEndpoint.clear();
  bombed.flags["logistics_damaged_turn:ab"] = 3;
  check(!inSupply(bombed, "japan", "b"),
        "Repair this turn restored continuously undamaged supply");
  check(
      validateRoute(bombed,
                    {"u", {"a", "b"}, MovementMode::StrategicRail, false})
          .allowed,
      "Current undamaged rail incorrectly barred ordinary strategic rail use");
}
void immobileRailAndContinuousPossession() {
  Puzzle p;
  p.link("a", "b", {{"railway_connection", V(true)}});
  auto s = p.state();
  unit(s, "militia", "a", "militia");
  s.units.at("militia").movementRemaining = 0;
  check(validateRoute(
            s, {"militia", {"a", "b"}, MovementMode::StrategicRail, false})
                .allowed == false,
        "Militia Home Country endpoint restriction missing");
  auto def = *s.definition;
  def.factions.at("japan").homeCountry.insert("b");
  s.definition = freezeDefinition(std::move(def));
  check(validateRoute(
            s, {"militia", {"a", "b"}, MovementMode::StrategicRail, false})
            .allowed,
        "Zero ordinary movement prevented strategic rail");
  s.units.at("militia").commitments.insert("attrition");
  check(!validateRoute(
             s, {"militia", {"a", "b"}, MovementMode::StrategicRail, false})
             .allowed,
        "Attrition unit moved by strategic rail");
  s.units.at("militia").commitments.clear();
  s.territories.at("b").flags["last_possession_change_turn"] = 2;
  check(!heldSinceTurnStart(s, "japan", "b") &&
            !validateRoute(
                 s, {"militia", {"a", "b"}, MovementMode::StrategicRail, false})
                 .allowed,
        "Recaptured territory passed possession timing");
  check(!heldSinceNationTurnStart(s, "japan", "b"),
        "Captured base became eligible before first own turn");
  s.nations.at("japan").gameFlags["logistics_last_turn_start"] = 3;
  check(!heldSinceNationTurnStart(s, "japan", "b"),
        "Same-turn capture satisfied own-turn age");
  s.nations.at("japan").gameFlags["logistics_last_turn_start"] = 7;
  check(heldSinceNationTurnStart(s, "japan", "b"),
        "Base held across next own turn stayed unavailable");
}
void riverBanksAndImpassableRoads() {
  Puzzle p;
  p.link("a", "b",
         {{"has_river", V(true)}, {"river_banks", V(A{str("enemy")})}});
  p.link("b", "c",
         {{"passable", V(false)}, {"border_terrain", str("impassable")}});
  auto s = p.state();
  unit(s, "u", "a");
  check(!riverRouteAvailable(s, "japan", "a", "b") &&
            !inSupply(s, "japan", "b"),
        "Enemy river bank did not cut supply");
  check(
      !validateRoute(s, {"u", {"a", "b"}, MovementMode::StrategicRiver, false})
           .allowed,
      "Enemy bank allowed strategic river move");
  s.nations.at("japan").atWarWith.clear();
  s.nations.at("kmt").atWarWith.clear();
  check(riverRouteAvailable(s, "japan", "a", "b") && inSupply(s, "japan", "b"),
        "Neutral bank incorrectly prevented river use");
  unit(s, "v", "b");
  check(!validateRoute(s, {"v", {"b", "c"}, MovementMode::Ordinary, false})
             .allowed,
        "Impassable/supply-only road became ordinary land adjacency");
}
void seaRangeRefreshAndSharedPorts() {
  Puzzle p;
  for (int i = 0; i < 6; ++i)
    p.sea("s" + std::to_string(i));
  for (int i = 0; i < 4; ++i)
    p.link("s" + std::to_string(i), "s" + std::to_string(i + 1));
  auto s = p.state();
  port(s, "source", "a", {"s0"});
  port(s, "destination", "b", {"s3"});
  check(!inSupply(s, "japan", "b"), "Minor port exceeded range two");
  s.nations.at("japan").technologyStages["improved_logistics"] = 4;
  check(inSupply(s, "japan", "b"),
        "Improved Logistics did not extend supply by one");
  s.nations.at("japan").technologyStages.clear();
  port(s, "refresh", "c", {"s2"});
  check(inSupply(s, "japan", "b"),
        "Naval facility failed to refresh sea supply range");
  s.facilities.at("refresh").damage = 1;
  check(!inSupply(s, "japan", "b"), "Damaged port refreshed supply");
  s.facilities.at("refresh").damage = 0;
  s.facilities.at("refresh").flags["placed_this_turn"] = 1;
  check(!inSupply(s, "japan", "b"), "New port immediately supplied route");
  s.facilities.at("refresh").flags.clear();
  s.facilities.at("refresh").flags["border:s2"] = 1;
  s.facilities.at("refresh").flags["border:s5"] = 1;
  s.facilities.at("destination").flags.clear();
  s.facilities.at("destination").flags["border:s5"] = 1;
  check(!inSupply(s, "japan", "b"),
        "Shared port teleported supply between unconnected sea accesses");
}
void noSecondSeaLeg() {
  Puzzle p;
  p.sea("s0");
  p.sea("s1");
  p.link("b", "c", {{"railway_connection", V(true)}});
  auto s = p.state();
  port(s, "source", "a", {"s0"});
  port(s, "landfall", "b", {"s0"});
  port(s, "second_departure", "c", {"s1"});
  port(s, "destination", "d", {"s1"});
  check(inSupply(s, "japan", "c"), "Land route after landfall missing");
  check(!inSupply(s, "japan", "d"), "Supply returned to sea after landfall");
}
void blockadeSurfaceOnly() {
  Puzzle p;
  p.sea("s0");
  p.sea("s1");
  auto s = p.state();
  port(s, "shared", "enemy", {"s0", "s1"});
  for (int i = 0; i < 3; ++i)
    unit(s, "blockader" + std::to_string(i), "s0", "destroyer");
  unit(s, "sub", "s0", "submarine", "kmt");
  check(seaBlockaded(s, "kmt", "s0"),
        "Enemy submarine incorrectly prevented surface blockade");
  check(!facilityBlockaded(s, "kmt", "shared"),
        "One access incorrectly blockaded shared facility");
  unit(s, "surface", "s0", "destroyer", "kmt");
  check(!seaBlockaded(s, "kmt", "s0"),
        "Enemy surface warship did not prevent blockade");
  s.units.erase("surface");
  for (int i = 3; i < 6; ++i)
    unit(s, "blockader" + std::to_string(i), "s1", "destroyer");
  check(facilityBlockaded(s, "kmt", "shared"),
        "Both blockaded sea accesses failed to block facility");
  s.nations.at("japan").atWarWith.clear();
  s.nations.at("kmt").atWarWith.clear();
  check(!facilityBlockaded(s, "kmt", "shared"),
        "Peacetime fleet blockaded neutral facilities");
}
void narrowCrossings() {
  Puzzle p;
  p.sea("s0");
  p.link("a", "b",
         {{"narrow_crossing", V(true)},
          {"unit_capacity", V(1.0)},
          {"narrow_crossing_id", str("crossing")},
          {"narrow_crossing_sea_zones", V(A{str("s0")})}});
  auto s = p.state();
  unit(s, "one", "a");
  unit(s, "two", "a");
  MovementRules rules;
  check(!validateRoute(s, {"one", {"a", "b"}, MovementMode::Ordinary, false})
             .allowed,
        "Narrow crossing treated as ordinary land edge");
  rules.apply(
      s, offered(rules, s, "one", {"a", "b"}, MovementMode::NarrowCrossing));
  check(s.units.at("one").movementRemaining == 0 &&
            !validateRoute(
                 s, {"two", {"a", "b"}, MovementMode::NarrowCrossing, false})
                 .allowed,
        "Crossing capacity or full-move cost missing");
  auto blocked = p.state();
  unit(blocked, "u", "a");
  unit(blocked, "enemy_ship", "s0", "destroyer", "kmt");
  check(!validateRoute(blocked,
                       {"u", {"a", "b"}, MovementMode::NarrowCrossing, false})
             .allowed,
        "Enemy ship did not close narrow crossing");
}
void sourceOverlayAndClosedBoundary() {
  auto s = baseline().clone();
  s.captureTurnStart();
  for (const auto &[a, n] : s.definition->geography.require("nodes").asObject())
    if (s.territories.contains(a)) {
      check(railRegion(s, a) == "asia",
            "Included territory assigned outside Asia");
      for (const auto &e : n.require("neighbors").asArray())
        if (s.territories.contains(e.require("neighbor_id").asString()))
          check(borderApproach(s, a, e.require("neighbor_id").asString())
                    .riverKnown,
                "Unreviewed retained river approach");
    }
  check(!burmaRoadOpen(s) && !burmaRoadOpen(s, true) &&
            !ccpSovietRailConnected(s, "land_china_shensi"),
        "Closed map fabricated Burma/Ledo/USSR connection");
  check(inSupply(s, "japan", "land_jap_tokyo") &&
            inSupply(s, "japan", "land_korea"),
        "Retained Japanese home/coastal supply failed");
}
void cargoAndWithdrawal() {
  Puzzle p;
  p.sea("s0");
  p.link("a", "s0");
  p.link("a", "b");
  auto s = p.state(Phase::Combat);
  unit(s, "inf1", "a");
  unit(s, "inf2", "a");
  unit(s, "inf3", "a");
  for (auto &[id, u] : s.units)
    u.movementRemaining = 0;
  check(withdrawalEligibleRecipients(s, "japan", "a").empty(),
        "Immobile conquering units received unproved withdrawal permission");
  unit(s, "ship", "s0", "naval_transport");
  check(withdrawalEligibleRecipients(s, "japan", "a").empty(),
        "Transport capacity not shared among withdrawing units");
  s.units.erase("inf3");
  check(withdrawalEligibleRecipients(s, "japan", "a").size() == 2,
        "Adjacent two-slot transport failed withdrawal proof");
  attachCargo(s, "ship", "inf1");
  check(s.units.at("inf1").zone == "s0" &&
            s.units.at("inf1").carriedBy == "ship",
        "Cargo not linked to carrier location");
  rejects([&] { attachCargo(s, "ship", "inf1"); }, "Duplicate cargo accepted");
  auto restored = State::fromJson(s.definition, s.toJson());
  check(restored.planningKey() == s.planningKey(),
        "Cargo checkpoint changed state");
  detachCargo(s, "ship", "inf1", "b");
  check(!s.units.at("inf1").carriedBy && s.units.at("inf1").zone == "b",
        "Cargo unloading failed");
}
void giftWithdrawalRequiresExecutableSharedLoading() {
  Puzzle p;
  p.sea("s0");
  p.link("a", "s0");
  auto s = p.state(Phase::Combat);
  unit(s, "inf", "a");
  unit(s, "ship", "s0", "naval_transport");
  auto &inf = s.units.at("inf");
  inf.route = {"enemy", "a"};
  inf.commitments.insert("combat_move");
  inf.commitments.insert("combat");
  inf.movementRemaining = 0;
  check(withdrawalEligibleRecipients(s, "japan", "a").size() == 2,
        "Gift's printed noncombat exception did not allow boarding a fresh transport");
  auto unloaded = s;
  unloaded.units.at("ship").turnFlags["naval_unloaded"] = 1;
  check(withdrawalEligibleRecipients(unloaded, "japan", "a").empty(),
        "Transport already unloaded this turn falsely proved Chinese gift withdrawal");
  auto amphibious = s;
  amphibious.units.at("inf").turnFlags["naval_unloaded"] = 1;
  amphibious.units.at("inf").commitments.insert("transport_unloaded");
  check(withdrawalEligibleRecipients(amphibious, "japan", "a").empty(),
        "Amphibiously unloaded cargo falsely proved another movement after debarking");
  s.clock.phase = Phase::NonCombatMovement;
  s.territories.at("a").possessor = "ccp";
  s.units.at("inf").turnFlags["must_withdraw_from_chinese_gift"] = 1;
  check(navalLoadAllowed(s, "ship", "inf"), "Proved loading became impossible after the unaligned gift");
  const auto actions = navalMovementActions(s);
  const auto load = std::find_if(actions.begin(), actions.end(), [](const Action &a) {
    return a.kind == "naval_load" && a.parameters.require("unit").asString() == "inf";
  });
  check(load != actions.end(), "Executable withdrawal loading action was not exposed");
  check(applyNavalMovementAction(s, *load) && s.units.at("inf").carriedBy == "ship" &&
            !s.units.at("inf").turnFlags.contains("must_withdraw_from_chinese_gift"),
        "Actual loading failed to complete the mandatory gift withdrawal");
}
void pendingGiftsShareTheSameTransportCapacity() {
  Puzzle p;
  p.sea("s0");
  p.sea("s1");
  p.link("a", "s0"); p.link("b", "s0"); p.link("s0", "s1");
  auto s = p.state(Phase::Combat);
  unit(s, "old1", "a"); unit(s, "old2", "a"); unit(s, "new", "b");
  unit(s, "ship", "s0", "naval_transport");
  for (const auto &id : {"old1", "old2", "new"}) s.units.at(id).movementRemaining = 0;
  s.units.at("old1").turnFlags["must_withdraw_from_chinese_gift"] = 1;
  s.units.at("old2").turnFlags["must_withdraw_from_chinese_gift"] = 1;
  check(withdrawalEligibleRecipients(s, "japan", "b").empty(),
        "Two Chinese gifts double-booked the same physical transport slots");
  s.units.erase("new");
  s.clock.phase = Phase::NonCombatMovement;
  s.territories.at("a").possessor = "ccp";
  MovementRules rules(std::make_shared<NavalRules>());
  const auto actions = rules.actions(s);
  check(std::any_of(actions.begin(), actions.end(), [](const Action &a) { return a.kind == "naval_load"; }),
        "Mandatory gift loading was hidden");
  check(std::none_of(actions.begin(), actions.end(), [](const Action &a) { return a.kind == "naval_start_move"; }),
        "Optional ship movement could abandon the only mandatory withdrawal transport");
}
void pairedBlitz() {
  Puzzle p;
  p.link("a", "enemy");
  auto s = p.state(Phase::Combat);
  unit(s, "armor", "a", "light_armor");
  unit(s, "support", "a", "self_propelled_artillery");
  s.units.at("armor").turnFlags["blitz_eligible"] = 1;
  s.units.at("support").turnFlags["blitz_eligible"] = 1;
  s.units.at("support").commitments.insert("blitz_with:armor");
  check(
      !validateRoute(s, {"support", {"a", "enemy"}, MovementMode::Blitz, true})
           .allowed,
      "Companion blitzed independently before armor");
  MovementRules rules;
  rules.apply(s,
              offered(rules, s, "armor", {"a", "enemy"}, MovementMode::Blitz));
  check(validateRoute(s, {"support", {"a", "enemy"}, MovementMode::Blitz, true})
            .allowed,
        "Paired support could not follow armor approach");
}
void factoryRelocation() {
  Puzzle p;
  p.link("a", "b", {{"railway_connection", V(true)}});
  auto s = p.state();
  auto def = *s.definition;
  def.factions.at("japan").homeCountry.insert("b");
  s.definition = freezeDefinition(std::move(def));
  FacilityState f;
  f.id = "factory";
  f.type = "major_factory";
  f.zone = "a";
  f.damage = 2;
  s.facilities[f.id] = f;
  check(!validateFactoryRailRoute(s, "factory", {"a", "b"}).allowed,
        "Factory moved without Improved Logistics");
  s.nations.at("japan").technologyStages["improved_logistics"] = 4;
  check(validateFactoryRailRoute(s, "factory", {"a", "b"}).allowed,
        "Eligible damaged factory could not relocate");
  s.facilities.at("factory").flags["researched_this_turn"] = 1;
  check(!validateFactoryRailRoute(s, "factory", {"a", "b"}).allowed,
        "Research factory moved in same turn");
  s.facilities.at("factory").flags.clear();
  MovementRules rules;
  const auto options = rules.actions(s);
  const auto a =
      std::find_if(options.begin(), options.end(), [](const auto &x) {
        return x.kind == "movement_factory_rail";
      });
  check(a != options.end(), "Factory rail action missing");
  rules.apply(s, *a);
  check(s.facilities.at("factory").zone == "b" &&
            s.facilities.at("factory").damage == 2 &&
            s.facilities.at("factory").flags.at("moved_this_turn") == 1,
        "Factory relocation lost damage or restriction");
  unit(s, "u", "a");
  check(!validateRoute(s, {"u", {"a", "b"}, MovementMode::StrategicRail, false})
             .allowed,
        "Major factory failed to consume two rail moves");
}
Action offeredTow(const MovementRules &rules, const State &s, const Id &motor,
                  const Id &artillery, const std::vector<Id> &path) {
  for (const auto &a : rules.actions(s))
    if (a.kind == "movement_route" &&
        a.parameters.require("unit").asString() == motor &&
        a.parameters.find("towed") &&
        a.parameters.require("towed").asString() == artillery) {
      std::vector<Id> p;
      for (const auto &z : a.parameters.require("path").asArray())
        p.push_back(z.asString());
      if (p == path)
        return a;
    }
  throw std::runtime_error("Expected paired towing route was not offered");
}
void pairedTowingMovesWithoutChangingCatalogStats() {
  Puzzle p;
  p.link("a", "b");
  p.link("b", "c");
  auto s = p.state();
  unit(s, "motor", "a", "motorized_infantry");
  unit(s, "gun", "a", "artillery");
  MovementRules rules;
  const auto action = offeredTow(rules, s, "motor", "gun", {"a", "b", "c"});
  rules.apply(s, action);
  check(s.units.at("motor").zone == "c" && s.units.at("gun").zone == "c" &&
            s.units.at("motor").movementRemaining == 0 &&
            s.units.at("gun").movementRemaining == 0,
        "Two-zone towing failed to move/exhaust both partners");
  check(!s.units.at("gun").carriedBy && s.units.at("motor").cargo.empty(),
        "Towing incorrectly used transport cargo");
  check(s.definition->catalog->stats("artillery", 0, catalogContext(s, "japan"))
                .movement == 1,
        "Towing rewrote ordinary artillery catalog movement");
}
void segmentedTowBudgetAndOneToOnePairing() {
  Puzzle p;
  p.link("a", "b");
  p.link("b", "c");
  auto s = p.state();
  unit(s, "motor", "a", "motorized_infantry");
  unit(s, "second", "b", "motorized_infantry");
  unit(s, "gun", "a", "anti_aircraft_artillery");
  MovementRules rules;
  rules.apply(s, offeredTow(rules, s, "motor", "gun", {"a", "b"}));
  check(!validateRoute(s, {"gun", {"b", "c"}, MovementMode::Ordinary, false})
             .allowed,
        "Towed gun used boosted remaining movement without its partner");
  check(
      !validateRoute(
           s, {"second", {"b", "c"}, MovementMode::Ordinary, false, Id("gun")})
           .allowed,
      "Gun changed towing partner during same turn");
  rules.apply(s, offeredTow(rules, s, "motor", "gun", {"b", "c"}));
  check(s.units.at("gun").movementRemaining == 0 &&
            s.units.at("motor").movementRemaining == 0,
        "Segmented tow gained additional movement");
}
void towingRespectsTerrainAndCommitments() {
  Puzzle p;
  p.link("a", "b", {{"border_terrain", str("mountain")}});
  p.link("b", "c");
  auto s = p.state();
  unit(s, "motor", "a", "motorized_infantry");
  unit(s, "gun", "a", "advanced_artillery");
  check(
      !validateRoute(
           s,
           {"motor", {"a", "b", "c"}, MovementMode::Ordinary, false, Id("gun")})
           .allowed,
      "Towing crossed terrain that ends movement");
  MovementRules rules;
  rules.apply(s, offeredTow(rules, s, "motor", "gun", {"a", "b"}));
  check(s.units.at("gun").movementRemaining == 0 &&
            s.units.at("motor").movementRemaining == 0,
        "Terrain did not exhaust both tow partners");
  for (const auto &commitment :
       {Id("attrition"), Id("repair"), Id("transport_unloaded")}) {
    auto t = p.state();
    unit(t, "motor", "a", "motorized_infantry");
    unit(t, "gun", "a", "artillery");
    t.units.at("gun").commitments.insert(commitment);
    check(
        !validateRoute(
             t, {"motor", {"a", "b"}, MovementMode::Ordinary, false, Id("gun")})
             .allowed,
        "Towing bypassed committed artillery restriction");
  }
}
void combatTowingRegistersBothApproachesAndReplays() {
  Puzzle p;
  p.link("a", "b");
  p.link("b", "enemy", {{"river_crossing", V(true)}});
  auto s = p.state(Phase::CombatMovement);
  unit(s, "motor", "a", "motorized_infantry");
  unit(s, "gun", "a", "advanced_artillery");
  auto rules = std::make_shared<MovementRules>();
  Engine e(s, rules, 9);
  const auto checkpoint = e.serialize();
  e.step(offeredTow(*rules, e.state(), "motor", "gun", {"a", "b", "enemy"}));
  check(e.state().battles.size() == 1,
        "Combat tow did not register one combined attack");
  const auto &b = e.state().battles.begin()->second;
  check(b.attackers == std::vector<Id>({"motor", "gun"}) &&
            b.data.require("origins").require("motor").asString() == "b" &&
            b.data.require("origins").require("gun").asString() == "b",
        "Towed contingent lost actual approach origins");
  check(e.state().units.at("gun").commitments.contains("combat_move"),
        "Towed gun was not committed to combat movement");
  auto replay =
      Engine::replay(s.definition, rules, checkpoint, e.state().history);
  check(replay.exactReplayIdentity() == e.exactReplayIdentity(),
        "Paired combat towing failed exact replay");
}
void lendLeaseDestinationException() {
  Puzzle p;
  p.sea("s0");
  p.link("a", "b", {{"railway_connection", V(true)}});
  auto s = p.state();
  s.nations.at("japan").atWarWith.clear();
  s.nations.at("kmt").atWarWith.clear();
  port(s, "source", "b", {"s0"});
  port(s, "recipient", "enemy", {"s0"});
  check(!inSupply(s, "japan", "enemy"),
        "Ordinary supply gained neutral recipient facility permission");
  check(lendLeaseSupplyRoute(s, "japan", "kmt", "enemy").connected,
        "Lend-lease final-recipient facility exception missing");
  check(!lendLeaseSupplyRoute(s, "japan", "kmt", "enemy", true).connected,
        "Naval lend-lease traveled over inland rail");
  port(s, "home_port", "a", {"s0"});
  check(lendLeaseSupplyRoute(s, "japan", "kmt", "enemy", true).connected,
        "Naval lend-lease could not leave Home Country port");
}
} // namespace
int main() {
  try {
    for (const auto &[name, fn] :
         std::vector<std::pair<std::string, std::function<void()>>>{
             {"directional terrain", directionalTerrain},
             {"hostile stops and origins", hostileStopsAndOrigins},
             {"rail gauge damage capacity", railGaugeDamageCapacity},
             {"immobile rail possession timing",
              immobileRailAndContinuousPossession},
             {"river banks and roads", riverBanksAndImpassableRoads},
             {"range refresh shared ports", seaRangeRefreshAndSharedPorts},
             {"no second sea leg", noSecondSeaLeg},
             {"surface blockade", blockadeSurfaceOnly},
             {"narrow crossings", narrowCrossings},
             {"source overlay closed boundary", sourceOverlayAndClosedBoundary},
             {"cargo withdrawal", cargoAndWithdrawal},
             {"gift executable loading", giftWithdrawalRequiresExecutableSharedLoading},
             {"gift shared reservations", pendingGiftsShareTheSameTransportCapacity},
             {"paired blitz", pairedBlitz},
             {"factory relocation", factoryRelocation},
             {"paired towing", pairedTowingMovesWithoutChangingCatalogStats},
             {"segmented towing", segmentedTowBudgetAndOneToOnePairing},
             {"tow terrain/commitments", towingRespectsTerrainAndCommitments},
             {"combat tow/replay",
              combatTowingRegistersBothApproachesAndReplays},
             {"lend-lease destination exception",
              lendLeaseDestinationException}}) {
      fn();
      std::cout << "PASS " << name << '\n';
    }
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
