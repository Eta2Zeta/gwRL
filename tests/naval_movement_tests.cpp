#include "game/air.hpp"
#include "game/catalog.hpp"
#include "game/economy.hpp"
#include "game/naval.hpp"
#include "game/politics.hpp"
#include <algorithm>
#include <functional>
#include <iostream>
#include <stdexcept>
namespace {
using namespace game::campaign;
using V = game::json::Value;
const Id p14 = "sea_p14", p15 = "sea_p15", p16 = "sea_p16", p32 = "sea_p32",
         p33 = "sea_p33", p41 = "sea_p41", honshu = "land_jap_honshu",
         beiping = "land_china_beiping", shantung = "land_china_shantung",
         tokyo = "land_jap_tokyo";
void check(bool ok, const std::string &why) {
  if (!ok)
    throw std::runtime_error(why);
}
State fixture(Phase phase = Phase::NonCombatMovement) {
  static const auto initial =
      loadScenario(std::filesystem::path(GWRL_SOURCE_DIR) /
                   "game_content/scenarios/japan_china_1936");
  auto s = initial.clone();
  s.units.clear();
  s.construction.clear();
  s.repairs.clear();
  s.clock.nationIndex = 2;
  s.clock.playerTurnSerial = 2;
  s.clock.phase = phase;
  for (const auto &n : s.definition->turnOrder)
    s.completedTurns[n] = (n == "ccp" || n == "mongolia") ? 1 : 0;
  for (auto &[id, t] : s.territories)
    t.possessor = "japan";
  s.captureTurnStart();
  return s;
}
void add(State &s, const Id &id, const Id &type, const Id &zone,
         const Id &n = "japan", int damage = 0) {
  UnitState u;
  u.id = id;
  u.type = type;
  u.owner = n;
  u.zone = u.turnOrigin = zone;
  u.damage = damage;
  u.movementAllowance = u.movementRemaining =
      s.definition->catalog->stats(type, damage, catalogContext(s, n, zone))
          .movement;
  s.units.emplace(id, std::move(u));
}
std::shared_ptr<const Rules> rules() {
  return std::make_shared<NavalRules>(
      std::make_shared<AirRules>(std::make_shared<EconomyRules>()));
}
Action select(
    Engine &e, const Id &kind,
    const std::function<bool(const Action &)> &match = [](const Action &) {
      return true;
    }) {
  for (const auto &a : e.legalActions())
    if (a.kind == kind && match(a))
      return a;
  throw std::runtime_error("Missing action " + kind);
}
void choose(
    Engine &e, const Id &kind,
    const std::function<bool(const Action &)> &match = [](const Action &) {
      return true;
    }) {
  e.step(select(e, kind, match));
}
void move(Engine &e, const Id &unit, const std::vector<Id> &path,
          bool strategic = false, const Id &dest = {}) {
  choose(e, "naval_start_move", [&](const Action &a) {
    return a.parameters.require("unit").asString() == unit;
  });
  choose(e, "naval_route", [&](const Action &a) {
    const auto &r = a.parameters.require("request");
    std::vector<Id> p;
    for (const auto &z : r.require("path").asArray())
      p.push_back(z.asString());
    return p == path && r.require("strategic").asBool() == strategic &&
           (dest.empty() ||
            r.require("destination_facility").asString() == dest);
  });
}
void regularMovementAndReplay() {
  auto s = fixture();
  add(s, "ship", "destroyer", p16);
  s.captureTurnStart();
  Engine e(s, rules(), 4);
  const auto start = e.serialize();
  move(e, "ship", {p16, p15, p14});
  check(e.state().units.at("ship").zone == p14 &&
            e.state().units.at("ship").movementRemaining == 2,
        "Ship movement lost facility bonus or route cost");
  check(e.state().battles.empty(),
        "Completed route retained a planning battle");
  auto replay = Engine::replay(s.definition, rules(), start, e.state().history);
  check(replay.exactReplayIdentity() == e.exactReplayIdentity(),
        "Fleet planning/movement replay differs");
}
void supplyDamageAndSubmarineRanges() {
  auto s = fixture();
  s.facilities.clear();
  add(s, "dd", "destroyer", p16);
  add(s, "bb", "battleship", p16, "japan", 1);
  add(s, "sub", "submarine", p16);
  check(!validateNavalRoute(s, {{"dd"}, {p16, p15, p32, p41}}).allowed,
        "Unsupplied surface ship retained full range");
  check(!validateNavalRoute(s, {{"bb"}, {p16, p15}}).allowed,
        "Damage and absent supply did not stack");
  check(validateNavalRoute(s, {{"sub"}, {p16, p15, p32, p41}}).allowed,
        "Submarine incorrectly suffered surface supply penalty");
}
void transportComposition() {
  auto s = fixture();
  add(s, "t", "naval_transport", p15);
  add(s, "dd", "destroyer", p15);
  add(s, "i1", "infantry", honshu);
  add(s, "i2", "infantry", honshu);
  add(s, "a1", "artillery", honshu);
  add(s, "a2", "artillery", honshu);
  add(s, "r", "strategic_rocket", honshu);
  add(s, "m", "marine", honshu);
  check(navalCargoFits(s, "t", {"i1", "i2"}) &&
            navalCargoFits(s, "t", {"i1", "a1"}) &&
            navalCargoFits(s, "t", {"i1", "r"}),
        "Legal transport composition rejected");
  check(!navalCargoFits(s, "t", {"a1", "a2"}) &&
            !navalCargoFits(s, "t", {"i1", "i2", "a1"}),
        "Excess cargo admitted");
  check(navalCargoFits(s, "dd", {"m"}) && !navalCargoFits(s, "dd", {"i1"}),
        "Japanese destroyer accepted non-Marine cargo");
}
void loadVoyageAndFriendlyUnload() {
  auto s = fixture();
  add(s, "t", "naval_transport", p15);
  add(s, "i", "infantry", honshu);
  s.captureTurnStart();
  Engine e(s, rules());
  choose(e, "naval_load");
  check(e.state().units.at("i").carriedBy == "t", "Cargo links missing");
  move(e, "t", {p15, p14});
  choose(e, "naval_unload", [](const Action &a) {
    return a.parameters.require("zone").asString() == beiping;
  });
  check(!e.state().units.at("i").carriedBy &&
            e.state().units.at("i").zone == beiping &&
            e.state().units.at("t").movementRemaining == 0,
        "Unload did not exhaust cargo and carrier");
  for (const auto &a : e.legalActions())
    check(a.kind != "naval_start_move", "Unloaded transport kept moving");
}
void movedCargoAndSplitUnloadingRejected() {
  auto s = fixture();
  add(s, "t", "naval_transport", p15);
  add(s, "i", "infantry", honshu);
  s.units.at("i").route = {honshu};
  for (const auto &a : navalMovementActions(s))
    check(a.kind != "naval_load", "Moved land cargo loaded");
  s.units.at("i").route.clear();
  attachCargo(s, "t", "i");
  s.units.at("t").turnFlags["naval_combat_unloaded"] = 1;
  for (const auto &a : navalMovementActions(s))
    check(a.kind != "naval_unload",
          "Transport split combat and noncombat unloading");
}
void destroyerTransportRangeAndStop() {
  auto s = fixture();
  add(s, "dd", "destroyer", p16);
  add(s, "m", "marine", p16);
  attachCargo(s, "dd", "m");
  check(!validateNavalRoute(s, {{"dd"}, {p16, p15, p32, p41, p32}}).allowed,
        "Loaded destroyer did not lose movement");
  Engine e(s, rules());
  move(e, "dd", {p16, p15, p14});
  choose(e, "naval_unload", [](const Action &a) {
    return a.parameters.require("zone").asString() == beiping;
  });
  check(e.state().units.at("dd").movementRemaining == 0,
        "Destroyer moved after unloading");
}
void strategicCapacityEndpointsAndUnloading() {
  auto s = fixture();
  add(s, "t", "naval_transport", p16);
  add(s, "i", "infantry", p16);
  add(s, "a", "artillery", p16);
  attachCargo(s, "t", "i");
  attachCargo(s, "t", "a");
  NavalRouteRequest r{{"t"},
                      {p16, p15, p14},
                      false,
                      true,
                      "facility_tokyo_major_shipyard",
                      "facility_beiping_minor_port"};
  check(validateNavalRoute(s, r).allowed, "Supplied strategic voyage rejected");
  s.nations.at("japan").turnFlags["strategic_naval_used"] = 1;
  check(!validateNavalRoute(s, r).allowed, "Strategic capacity omitted cargo");
  s.nations.at("japan").turnFlags.clear();
  Engine e(s, rules());
  move(e, "t", r.path, true, *r.destinationFacility);
  check(e.state().nations.at("japan").turnFlags.at("strategic_naval_used") == 3,
        "Strategic accounting does not count transport plus cargo");
  for (const auto &a : e.legalActions())
    if (a.kind == "naval_unload")
      check(a.parameters.require("zone").asString() == beiping,
            "Strategic cargo unloaded away from final facility");
}
void strategicPickupAlongRoute() {
  auto s = fixture();
  add(s, "t", "naval_transport", p16);
  add(s, "i", "infantry", honshu);
  Engine e(s, rules());
  move(e, "t", {p16, p15, p14}, true, "facility_beiping_minor_port");
  check(e.state().decisions.back().kind == "naval_strategic_pickup",
        "Strategic route skipped legal intermediate pickup");
  choose(e, "naval_strategic_pickup");
  check(e.state().units.at("t").zone == p14 &&
            e.state().units.at("i").carriedBy == "t" &&
            e.state().nations.at("japan").turnFlags.at(
                "strategic_naval_used") == 2,
        "Intermediate pickup lost cargo or capacity");
}
void strategicAndNoncombatBlockers() {
  auto s = fixture();
  s.nations.at("japan").atWarWith.insert("kmt");
  s.nations.at("kmt").atWarWith.insert("japan");
  add(s, "t", "naval_transport", p16);
  add(s, "enemy", "naval_transport", p16, "kmt");
  NavalRouteRequest r{{"t"},
                      {p16, p15, p14},
                      false,
                      true,
                      "facility_tokyo_major_shipyard",
                      "facility_beiping_minor_port"};
  check(!validateNavalRoute(s, r).allowed,
        "Strategic voyage departed an enemy transport");
  s.units.erase("enemy");
  add(s, "enemy", "destroyer", p15, "kmt");
  check(!validateNavalRoute(s, r).allowed &&
            !validateNavalRoute(s, {{"t"}, {p16, p15, p14}}).allowed,
        "Enemy warship failed to block route");
  s.units.at("enemy").gameFlags["raider"] = 1;
  s.units.at("enemy").type = "battlecruiser";
  check(validateNavalRoute(s, {{"t"}, {p16, p15, p14}}).allowed,
        "Ordinary movement could not ignore raiding battlecruiser");
  check(!validateNavalRoute(s, r).allowed,
        "Strategic move ignored enemy raider");
}
void carrierMovementGivesNoAircraftRide() {
  auto s = fixture();
  add(s, "cv", "fleet_carrier", p16);
  add(s, "f", "fighter", p16);
  attachCargo(s, "cv", "f");
  Engine e(s, rules());
  move(e, "cv", {p16, p15});
  check(e.state().units.at("f").zone == p16 &&
            !e.state().units.at("f").carriedBy &&
            e.state().units.at("f").movementRemaining == 4,
        "Aircraft rode carrier before receiving own flight");
}
void portExitCostsZero() {
  auto s = fixture();
  add(s, "dd", "destroyer", tokyo);
  s.units.at("dd").gameFlags["in_port:facility_tokyo_major_shipyard"] = 1;
  Engine e(s, rules());
  move(e, "dd", {p16});
  check(e.state().units.at("dd").zone == p16 &&
            e.state().units.at("dd").movementRemaining == 4,
        "Port exit consumed ship movement");
}
void noncombatPortExitCannotPassEnemyWarships() {
  // Ships in port begin in an adjacent sea zone but still enter it. Sailing out
  // past Enemy Surface Warships needs a screening force, which is combat
  // movement (RB 9.4.2, 11.4, 11.5).
  auto s = fixture();
  s.nations.at("japan").atWarWith.insert("kmt");
  s.nations.at("kmt").atWarWith.insert("japan");
  add(s, "dd", "destroyer", tokyo);
  s.units.at("dd").gameFlags["in_port:facility_tokyo_major_shipyard"] = 1;
  add(s, "enemy", "destroyer", p16, "kmt");
  check(!validateNavalRoute(s, {{"dd"}, {p16}}).allowed &&
            !validateNavalRoute(s, {{"dd"}, {p16, p15}}).allowed,
        "Noncombat port exit passed an Enemy Surface Warship");
  auto combat = s.clone();
  combat.clock.phase = Phase::CombatMovement;
  check(validateNavalRoute(combat, {{"dd"}, {p16}, true}).allowed,
        "Combat Movement lost its port sortie against an Enemy warship");
}
// A carrier's route must keep aircraft landings wherever it can end: a passing
// Enemy transport does not stop it, while blocking warships make a lone carrier
// screen and stay.
void carrierRoutesKeepLandingsWhereverTheyCanEnd() {
  auto s = fixture(Phase::CombatMovement);
  s.nations.at("japan").atWarWith.insert("kmt");
  s.nations.at("kmt").atWarWith.insert("japan");
  add(s, "cv", "light_carrier", p16);
  add(s, "convoy", "naval_transport", p15, "kmt");
  add(s, "f", "fighter", p15);
  s.units.at("f").movementRemaining = 0;
  s.units.at("f").turnFlags["air_in_flight"] = 1;
  // Leave the carrier exactly the two points this route spends.
  for (int spent = 1; spent < 12 &&
                      validateNavalRoute(s, {{"cv"}, {p16, p15, p14}, true}).reason !=
                          "Insufficient naval movement";
       ++spent)
    s.units.at("cv").turnFlags["naval_movement_spent"] = spent;
  --s.units.at("cv").turnFlags["naval_movement_spent"];
  check(validateNavalRoute(s, {{"cv"}, {p16, p15}, true}).allowed &&
            !validateNavalRoute(s, {{"cv"}, {p16, p15, p14}, true}).allowed,
        "A carrier sailed past a transport, away from the aircraft waiting for it");
  auto blocked = s.clone();
  blocked.units.erase("convoy");
  add(blocked, "screen", "destroyer", p15, "kmt");
  blocked.units.at("f").zone = p14;
  check(!validateNavalRoute(blocked, {{"cv"}, {p16, p15, p14}, true}).allowed,
        "A lone carrier counted on passing blocking warships to reach its aircraft");
}
// Patrol aircraft only react, so a carrier sails on past them; and a lone
// carrier leaving port past Enemy warships must screen, so it cannot stay in
// port while its own aircraft wait outside.
void carrierRoutesAreNotHeldWhereTheForceSailsOn() {
  auto s = fixture(Phase::CombatMovement);
  s.nations.at("japan").atWarWith.insert("kmt");
  s.nations.at("kmt").atWarWith.insert("japan");
  add(s, "cv", "light_carrier", p16);
  add(s, "patrol", "fighter", p15, "kmt");
  s.units.at("patrol").gameFlags["on_map"] = 1;
  s.units.at("patrol").gameFlags["map_range"] = 1;
  s.units.at("patrol").commitments.insert("maritime_air_patrol");
  add(s, "f", "fighter", p14);
  s.units.at("f").movementRemaining = 0;
  s.units.at("f").turnFlags["air_in_flight"] = 1;
  check(validateNavalRoute(s, {{"cv"}, {p16, p15, p14}, true}).allowed,
        "A carrier was held behind an Enemy patrol that only reacts");
  auto sortie = fixture(Phase::CombatMovement);
  sortie.nations.at("japan").atWarWith.insert("kmt");
  sortie.nations.at("kmt").atWarWith.insert("japan");
  add(sortie, "cv", "light_carrier", tokyo);
  sortie.units.at("cv").gameFlags["in_port:facility_tokyo_major_shipyard"] = 1;
  add(sortie, "deck", "fighter", tokyo);
  attachCargo(sortie, "cv", "deck");
  sortie.units.at("deck").movementRemaining = 0;
  add(sortie, "enemy", "destroyer", p16, "kmt");
  check(validateNavalRoute(sortie, {{"cv"}, {p16}, true}).allowed,
        "A lone carrier's sortie was refused as if it could stay in port");
}
// Engaging holds the carrier where it is, so it may not strand an aircraft
// that needs the carrier to sail.
void engagingCannotHoldACarrierItsAircraftNeed() {
  auto s = fixture(Phase::CombatMovement);
  s.nations.at("japan").atWarWith.insert("kmt");
  s.nations.at("kmt").atWarWith.insert("japan");
  add(s, "cv", "light_carrier", p16);
  add(s, "sub", "submarine", p16, "kmt");
  auto alone = s.clone();
  add(s, "f", "fighter", p15);
  s.units.at("f").movementRemaining = 0;
  s.units.at("f").turnFlags["air_in_flight"] = 1;
  const auto engageOffered = [](const State &state) {
    Engine e(state, rules());
    choose(e, "naval_start_move",
           [](const Action &a) { return a.parameters.require("unit").asString() == "cv"; });
    const auto actions = e.legalActions();
    return std::any_of(actions.begin(), actions.end(),
                       [](const Action &a) { return a.kind == "naval_engage_force"; });
  };
  check(engageOffered(alone) && !engageOffered(s),
        "Engaging froze a carrier that a waiting aircraft needs to sail");
}
void blockadedPortKeepsContinuingShipsInBerth() {
  auto s = fixture(Phase::CombatMovement);
  s.nations.at("japan").atWarWith.insert("kmt");
  s.nations.at("kmt").atWarWith.insert("japan");
  add(s, "screen", "destroyer", tokyo);
  add(s, "waiting", "naval_transport", tokyo);
  for (const auto &id : {Id("screen"), Id("waiting")})
    s.units.at(id).gameFlags["in_port:facility_tokyo_major_shipyard"] = 1;
  for (int i = 0; i < 3; ++i)
    add(s, "enemy" + std::to_string(i), "destroyer", p16, "kmt");
  Engine e(s, rules());
  choose(e, "naval_start_move", [](const Action &a) {
    return a.parameters.require("unit").asString() == "screen";
  });
  choose(e, "naval_force_add", [](const Action &a) {
    return a.parameters.require("unit").asString() == "waiting";
  });
  choose(e, "naval_route", [](const Action &a) {
    return canonicalJson(a.parameters.require("request").require("path")) ==
           canonicalJson(V(V::Array{V(p16), V(p15)}));
  });
  check(e.state().units.at("waiting").zone == tokyo &&
            e.state().units.at("screen").zone == tokyo,
        "Fleet left blocked berth before assigning screening force");
  choose(e, "naval_screen_add", [](const Action &a) {
    return a.parameters.require("unit").asString() == "screen";
  });
  choose(e, "naval_screen_confirm");
  check(e.state().units.at("screen").zone == p16 &&
            e.state().units.at("waiting").zone == tokyo,
        "Continuing ships exited port with screening force");
  auto failed = e.state().clone();
  const auto id = failed.battles.begin()->first;
  failed.battles.at(id).stage = "naval_complete";
  failed.battles.at(id).flags["finished"] = 1;
  continueNavalMovement(failed, id);
  check(failed.units.at("waiting").zone == tokyo &&
            failed.units.at("waiting").gameFlags.contains(
                "in_port:facility_tokyo_major_shipyard"),
        "Failed port screening moved or destroyed waiting ships");
  auto success = e.state().clone();
  removePoliticalUnits(success, {"enemy0", "enemy1", "enemy2"});
  success.battles.at(id).stage = "naval_complete";
  success.battles.at(id).flags["finished"] = 1;
  continueNavalMovement(success, id);
  check(success.decisions.back().kind == "naval_screening_continuation" &&
            success.units.at("waiting").zone == p16,
        "Victorious continuing force lost its choice to stop at cleared sea");
  auto stopped = success.clone();
  const auto stop = *std::find_if(
      stopped.decisions.back().options.begin(),
      stopped.decisions.back().options.end(),
      [](const Action &a) { return a.kind == "naval_screen_stop_route"; });
  applyNavalMovementAction(stopped, stop);
  check(stopped.battles.empty() && stopped.units.at("waiting").zone == p16 &&
            stopped.units.at("waiting").turnFlags.at(
                "naval_screening_continuing") == 1,
        "Stopping after screening moved the fleet or lost continuation "
        "eligibility");
  const auto resume = *std::find_if(
      success.decisions.back().options.begin(),
      success.decisions.back().options.end(),
      [](const Action &a) { return a.kind == "naval_screen_continue_route"; });
  applyNavalMovementAction(success, resume);
  check(success.units.at("waiting").zone == p15 &&
            !success.units.at("waiting").gameFlags.contains(
                "in_port:facility_tokyo_major_shipyard"),
        "Successful screening failed to release waiting sortie");
}
void immediateSubmarineReactionResumesTheVoyage() {
  auto s = fixture();
  s.nations.at("japan").atWarWith.insert("kmt");
  s.nations.at("kmt").atWarWith.insert("japan");
  add(s, "dd", "destroyer", p16);
  add(s, "enemy", "submarine", p15, "kmt");
  Engine e(s, rules(), 7);
  e.setDiceTapeForTesting({12, 12, 12, 12});
  const auto checkpoint = e.serialize();
  move(e, "dd", {p16, p15, p14});
  check(e.state().decisions.back().nation == "kmt" &&
            e.state().decisions.back().reaction,
        "Submarine owner did not receive movement reaction");
  choose(e, "naval_reaction_engage");
  for (int i = 0; i < 20 && !e.state().battles.empty(); ++i) {
    if (e.state().chance)
      e.resolveChance();
    else {
      const auto actions = e.legalActions();
      check(!actions.empty(), "Immediate submarine event has no continuation");
      e.step(actions.front());
    }
  }
  check(
      e.state().battles.empty() && e.state().units.at("dd").zone == p14 &&
          e.state().clock.phase == Phase::NonCombatMovement,
      "One-round submarine reaction did not resume original voyage and phase");
  auto replay =
      Engine::replay(s.definition, rules(), checkpoint, e.state().history);
  check(replay.exactReplayIdentity() == e.exactReplayIdentity(),
        "Contested voyage replay differs");
}
void defendingCarrierAircraftMayEngageMovingSubmarine() {
  auto s = fixture();
  s.nations.at("japan").atWarWith.insert("kmt");
  s.nations.at("kmt").atWarWith.insert("japan");
  add(s, "sub", "submarine", p16);
  add(s, "carrier", "fleet_carrier", p15, "kmt");
  add(s, "fighter", "fighter", p15, "kmt");
  attachCargo(s, "carrier", "fighter");
  Engine e(s, rules());
  move(e, "sub", {p16, p15, p14});
  check(!e.state().decisions.empty() &&
            e.state().decisions.back().nation == "kmt" &&
            e.state().decisions.back().kind == "naval_movement_reaction",
        "Carrier aircraft could not act as defensive MAP against moving "
        "submarine");
  choose(e, "naval_reaction_decline");
  check(e.state().units.at("sub").zone == p14 &&
            e.state().units.at("fighter").carriedBy == "carrier",
        "Declined carrier patrol reaction changed aircraft or blocked "
        "submarine voyage");
}
void controlledDadaoUsesControllerCalendarForCargo() {
  auto s = fixture();
  ensureDadao(s);
  s.territories.at(honshu).possessor = "dadao";
  add(s, "t", "naval_transport", p15, "dadao");
  add(s, "i", "infantry", honshu, "dadao");
  s.captureTurnStart();
  Engine e(s, rules());
  choose(e, "naval_load");
  check(e.state().units.at("i").carriedBy == "t" &&
            e.state().units.at("i").gameFlags.contains(
                "naval_loaded_completed_turns"),
        "Controlled Dadao cargo required an absent scheduled nation turn");
}
void peacefulSeaEntryWindowsAreSequentialAndReplayable() {
  auto s = fixture(Phase::CombatMovement);
  s.nations.at("kmt").powerStatus = "major";
  s.nations.at("ccp").powerStatus = "major";
  add(s, "dd", "destroyer", p16);
  add(s, "k", "destroyer", p15, "kmt");
  add(s, "c", "destroyer", p14, "ccp");
  auto nc = s.clone();
  nc.clock.phase = Phase::NonCombatMovement;
  check(!validateNavalRoute(nc, {{"dd"}, {p16, p15, p14}}).allowed,
        "Peaceful potential-DoW entry bypassed Combat Movement");
  Engine e(s, rules(), 91);
  const auto checkpoint = e.serialize();
  move(e, "dd", {p16, p15, p14});
  check(e.state().units.at("dd").zone == p16 &&
            e.state().decisions.back().kind == "naval_entry_intent",
        "Mover entered sea before declaring intent");
  choose(e, "naval_entry_peaceful");
  check(
      e.state().units.at("dd").zone == p16 &&
          e.state().decisions.back().nation == "kmt",
      "Defender declaration opportunity occurred after entry or went to mover");
  choose(e, "naval_entry_neutral");
  check(e.state().units.at("dd").zone == p15 &&
            e.state().decisions.back().kind == "naval_entry_intent",
        "Multi-leg route skipped second entry window");
  choose(e, "naval_entry_peaceful");
  check(e.state().decisions.back().nation == "ccp",
        "Second peaceful nation did not receive its own response");
  choose(e, "naval_entry_neutral");
  check(e.state().units.at("dd").zone == p14 && e.state().battles.empty(),
        "Neutral responses failed to resume route");
  auto replay =
      Engine::replay(s.definition, rules(), checkpoint, e.state().history);
  check(replay.exactReplayIdentity() == e.exactReplayIdentity(),
        "Peaceful entry windows lost exact replay");
}
void defenderDeclarationQueuesCombatAndAllowsReinforcements() {
  auto s = fixture(Phase::CombatMovement);
  s.nations.at("kmt").powerStatus = "major";
  s.territories.at(beiping).possessor = "kmt";
  s.politics.capitals["kmt"] = beiping;
  s.captureTurnStart();
  add(s, "dd", "destroyer", p16);
  add(s, "reinforcement", "destroyer", p16);
  add(s, "k", "destroyer", p15, "kmt");
  Engine e(s, rules());
  move(e, "dd", {p16, p15});
  choose(e, "naval_entry_peaceful");
  choose(e, "naval_entry_defender_declare");
  check(e.state().nations.at("kmt").atWarWith.contains("japan") &&
            e.state().clock.phase == Phase::CombatMovement &&
            e.state().battles.size() == 1 &&
            e.state().battles.begin()->second.stage == "naval_declared",
        "Defending declaration resolved ordinary combat during movement");
  move(e, "reinforcement", {p16, p15});
  check(e.state().battles.size() == 1 &&
            e.state().battles.begin()->second.attackers.size() == 2,
        "New war prevented combat movement reinforcement");
}
void optionalStationaryEngagementCommitsTheForce() {
  auto s = fixture(Phase::CombatMovement);
  s.nations.at("japan").atWarWith.insert("kmt");
  s.nations.at("kmt").atWarWith.insert("japan");
  add(s, "sub", "submarine", p15);
  add(s, "enemy", "destroyer", p15, "kmt");
  Engine e(s, rules());
  choose(e, "naval_start_move", [](const Action &a) {
    return a.parameters.require("unit").asString() == "sub";
  });
  choose(e, "naval_engage_force");
  check(
      e.state().battles.size() == 1 &&
          e.state().battles.begin()->second.attackers == std::vector<Id>{"sub"},
      "Submarine could not elect an attack instead of ignoring surface ships");
  for (const auto &a : navalMovementActions(e.state()))
    check(a.kind != "naval_start_move",
          "Committed attacking ship moved out before its battle");
}
void attackingRaiderSlipIsExplicitAndReplayable() {
  for (bool success : {false, true}) {
    auto s = fixture(Phase::CombatMovement);
    s.nations.at("japan").atWarWith.insert("kmt");
    s.nations.at("kmt").atWarWith.insert("japan");
    add(s, "bc", "battlecruiser", p16);
    add(s, "enemy", "destroyer", p15, "kmt");
    Engine e(s, rules(), 23);
    e.setDiceTapeForTesting(success ? std::vector<int>{12, 1}
                                    : std::vector<int>{1, 12});
    const auto checkpoint = e.serialize();
    choose(e, "naval_designate_raider");
    move(e, "bc", {p16, p15, p14});
    check(e.state().chance &&
              e.state().chance->purpose == "naval_movement_slip",
          "Raider movement did not expose opposed discovery dice");
    e.resolveChance();
    if (success)
      check(e.state().units.at("bc").zone == p14 && e.state().battles.empty(),
            "Successful attacking raider slip did not continue");
    else
      check(e.state().units.at("bc").zone == p15 &&
                e.state().battles.size() == 1 &&
                e.state()
                        .battles.begin()
                        ->second.data.require("context")
                        .asString() == "raider",
            "Failed attacking raider slip did not register combat");
    auto replay =
        Engine::replay(s.definition, rules(), checkpoint, e.state().history);
    check(replay.exactReplayIdentity() == e.exactReplayIdentity(),
          "Raider opposed roll replay differed");
  }
}
void convoyMissionsRemainExcluded() {
  auto s = fixture(Phase::CombatMovement);
  add(s, "bc", "battlecruiser", p16);
  for (const auto &a : navalMovementActions(s))
    check(a.kind.find("convoy") == Id::npos &&
              a.kind.find("interdict") == Id::npos &&
              a.kind.find("escort") == Id::npos,
          "Excluded convoy/interdiction mission offered");
}
void giftWithdrawalBoardsOnlyAUsableTransport() {
  auto s = fixture();
  s.territories.at(shantung).possessor = "ccp";
  add(s, "t", "naval_transport", p14);
  add(s, "gift", "infantry", shantung);
  auto &u = s.units.at("gift");
  u.route = {beiping, shantung};
  u.commitments.insert("combat_move");
  u.commitments.insert("combat");
  u.turnFlags["must_withdraw_from_chinese_gift"] = 1;
  u.movementRemaining = 0;
  check(navalLoadAllowed(s, "t", "gift"),
        "Explicit Chinese gift withdrawal could not board a fresh transport");
  auto exhausted = s.clone();
  exhausted.units.at("t").turnFlags["naval_combat_unloaded"] = 1;
  check(!navalLoadAllowed(exhausted, "t", "gift"),
        "Gift withdrawal reused a combat-unloaded transport");
  auto landed = s.clone();
  landed.units.at("gift").commitments.insert("amphibious_assault");
  check(!navalLoadAllowed(landed, "t", "gift"),
        "Gift withdrawal moved already amphibiously unloaded cargo again");
  Engine e(s, rules());
  const auto checkpoint = e.serialize();
  choose(e, "naval_load", [](const Action &a) {
    return a.parameters.require("unit").asString() == "gift";
  });
  check(e.state().units.at("gift").carriedBy == "t" &&
            !e.state().units.at("gift").turnFlags.contains(
                "must_withdraw_from_chinese_gift"),
        "Actual boarding did not discharge the gift withdrawal obligation");
  check(Engine::replay(s.definition, rules(), checkpoint, e.state().history)
                .exactReplayIdentity() == e.exactReplayIdentity(),
        "Chinese gift transport withdrawal replay differs");
}
} // namespace
int main() {
  try {
    for (const auto &[name, test] :
         std::vector<std::pair<std::string, std::function<void()>>>{
             {"regular voyage and replay", regularMovementAndReplay},
             {"supply damage submarine", supplyDamageAndSubmarineRanges},
             {"cargo composition", transportComposition},
             {"cargo voyage unload", loadVoyageAndFriendlyUnload},
             {"cargo movement restrictions",
              movedCargoAndSplitUnloadingRejected},
             {"destroyer transport", destroyerTransportRangeAndStop},
             {"strategic capacity/endpoints",
              strategicCapacityEndpointsAndUnloading},
             {"strategic pickup", strategicPickupAlongRoute},
             {"naval blockers", strategicAndNoncombatBlockers},
             {"carrier independent flight", carrierMovementGivesNoAircraftRide},
             {"zero-cost port exit", portExitCostsZero},
             {"noncombat port exit blockers",
              noncombatPortExitCannotPassEnemyWarships},
             {"staged blocked port sortie",
              blockadedPortKeepsContinuingShipsInBerth},
             {"carrier route landing stops",
              carrierRoutesKeepLandingsWhereverTheyCanEnd},
             {"engagement keeps landings",
              engagingCannotHoldACarrierItsAircraftNeed},
             {"carrier routes past reactions",
              carrierRoutesAreNotHeldWhereTheForceSailsOn},
             {"immediate submarine reaction",
              immediateSubmarineReactionResumesTheVoyage},
             {"carrier patrol reaction",
              defendingCarrierAircraftMayEngageMovingSubmarine},
             {"Dadao cargo calendar",
              controlledDadaoUsesControllerCalendarForCargo},
             {"peace entry sequence/replay",
              peacefulSeaEntryWindowsAreSequentialAndReplayable},
             {"defender DoW and reinforcements",
              defenderDeclarationQueuesCombatAndAllowsReinforcements},
             {"optional engagement commitment",
              optionalStationaryEngagementCommitsTheForce},
             {"attacking raider opposed rolls",
              attackingRaiderSlipIsExplicitAndReplayable},
             {"Chinese gift transport withdrawal",
              giftWithdrawalBoardsOnlyAUsableTransport},
             {"convoy exclusions", convoyMissionsRemainExcluded}}) {
      test();
      std::cout << "PASS " << name << '\n';
    }
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
