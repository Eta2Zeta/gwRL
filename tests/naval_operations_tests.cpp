#include "game/air.hpp"
#include "game/catalog.hpp"
#include "game/economy.hpp"
#include "game/land_combat.hpp"
#include "game/naval.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <functional>
#include <iostream>
#include <stdexcept>

namespace {
using namespace game::campaign;
using V = game::json::Value;
const Id p14 = "sea_p14", p16 = "sea_p16", tokyo = "land_jap_tokyo",
         honshu = "land_jap_honshu", shantung = "land_china_shantung",
         beiping = "land_china_beiping";
void check(bool value, const std::string &message) {
  if (!value)
    throw std::runtime_error(message);
}
State fixture(Phase phase = Phase::CombatMovement) {
  static const auto base =
      loadScenario(std::filesystem::path(GWRL_SOURCE_DIR) /
                   "game_content/scenarios/japan_china_1936");
  auto s = base.clone();
  s.units.clear();
  s.facilities.clear();
  s.construction.clear();
  s.repairs.clear();
  s.clock.nationIndex = 2;
  s.clock.playerTurnSerial = 2;
  s.clock.phase = phase;
  s.completedTurns["ccp"] = s.completedTurns["mongolia"] = 1;
  s.nations.at("japan").atWarWith.insert("kmt");
  s.nations.at("kmt").atWarWith.insert("japan");
  s.territories.at(shantung).possessor = "kmt";
  s.territories.at(beiping).possessor = "japan";
  s.captureTurnStart();
  return s;
}
void add(State &s, const Id &id, const Id &type, const Id &owner,
         const Id &zone) {
  UnitState u;
  u.id = id;
  u.type = type;
  u.owner = owner;
  u.zone = u.turnOrigin = zone;
  u.movementAllowance = u.movementRemaining =
      s.definition->catalog->stats(type, 0, catalogContext(s, owner, zone))
          .movement;
  s.units.emplace(id, std::move(u));
}
std::shared_ptr<const Rules> rules() {
  return std::make_shared<NavalRules>(std::make_shared<PoliticsRules>(
      std::make_shared<MovementRules>(std::make_shared<LandCombatRules>(
          std::make_shared<AirRules>(std::make_shared<EconomyRules>())))));
}
Action select(
    Engine &e, const Id &kind,
    std::function<bool(const Action &)> predicate = [](const Action &) {
      return true;
    }) {
  for (const auto &a : e.legalActions())
    if (a.kind == kind && predicate(a))
      return a;
  throw std::runtime_error("Missing operation action: " + kind);
}
void choose(
    Engine &e, const Id &kind,
    std::function<bool(const Action &)> predicate = [](const Action &) {
      return true;
    }) {
  e.step(select(e, kind, std::move(predicate)));
}
bool offered(Engine &e, const Id &kind) {
  const auto actions = e.legalActions();
  return std::any_of(actions.begin(), actions.end(),
                     [&](const Action &a) { return a.kind == kind; });
}
void finishBattles(Engine &e) {
  for (int step = 0; step < 200 && !e.state().battles.empty(); ++step) {
    if (e.state().chance) {
      e.resolveChance();
      continue;
    }
    const auto actions = e.legalActions();
    check(!actions.empty(), "Naval operation stalled");
    const std::vector<Id> priorities = {"politics_keep_capture",
                                        "air_decline_scramble",
                                        "air_ground",
                                        "naval_finish_shore_selection",
                                        "land_begin_battle",
                                        "land_progress_battle",
                                        "naval_finish_battle"};
    auto chosen = actions.begin();
    for (const auto &kind : priorities) {
      const auto found =
          std::find_if(actions.begin(), actions.end(),
                       [&](const Action &a) { return a.kind == kind; });
      if (found != actions.end()) {
        chosen = found;
        break;
      }
    }
    e.step(*chosen);
  }
  check(e.state().battles.empty(), "Battle did not finish within bound");
}
void uncontestedAssaultAndReplay() {
  auto s = fixture();
  add(s, "transport", "naval_transport", "japan", p14);
  add(s, "infantry", "infantry", "japan", p14);
  attachCargo(s, "transport", "infantry");
  Engine e(s, rules(), 2);
  e.setDiceTapeForTesting(std::vector<int>(80, 1));
  const auto checkpoint = e.serialize();
  choose(e, "naval_declare_assault", [](const Action &a) {
    return a.parameters.require("zone").asString() == shantung;
  });
  check(!offered(e, "naval_declare_assault"),
        "Same cargo can declare assault twice");
  check(e.state().units.at("infantry").carriedBy == "transport",
        "Cargo unloaded before assault resolution");
  choose(e, "end_phase");
  choose(e, "naval_begin_assault");
  finishBattles(e);
  check(e.state().territories.at(shantung).possessor == "japan" &&
            e.state().units.at("infantry").zone == shantung &&
            !e.state().units.at("infantry").carriedBy,
        "Uncontested assault did not land and capture");
  check(e.state().units.at("transport").movementRemaining == 0,
        "Unloading transport retained movement");
  check(Engine::replay(s.definition, rules(), checkpoint, e.state().history)
                .exactReplayIdentity() == e.exactReplayIdentity(),
        "Amphibious assault replay differs");
}
void seaMustBeClearedBeforeAssault() {
  auto s = fixture();
  add(s, "t", "naval_transport", "japan", p14);
  add(s, "i", "infantry", "japan", p14);
  add(s, "enemy", "destroyer", "kmt", p14);
  attachCargo(s, "t", "i");
  Engine e(s, rules());
  check(!offered(e, "naval_declare_assault"),
        "Blocked sea offered an impossible assault declaration");
  choose(e, "end_phase");
  check(!offered(e, "naval_begin_assault") && offered(e, "end_phase"),
        "Blocked assault left unresolved preparation trapping the Combat phase");
  auto cleared = s.clone();
  removePoliticalUnits(cleared, {"enemy"});
  Engine eligible(cleared, rules());
  check(offered(eligible, "naval_declare_assault"),
        "Cleared launching sea did not allow an amphibious assault");
}
void waitingArmorRemainsAboardUntilFoothold() {
  auto s = fixture();
  add(s, "t", "naval_transport", "japan", p14);
  add(s, "i", "infantry", "japan", p14);
  add(s, "armor", "light_armor", "japan", p14);
  add(s, "defender", "infantry", "kmt", shantung);
  attachCargo(s, "t", "i");
  attachCargo(s, "t", "armor");
  Engine e(s, rules());
  for (const auto &cargo : {Id("i"), Id("armor")})
    choose(e, "naval_declare_assault", [&](const Action &a) {
      return a.parameters.require("zone").asString() == shantung &&
             a.parameters.require("cargo").asString() == cargo;
    });
  choose(e, "end_phase");
  choose(e, "naval_begin_assault");
  choose(e, "naval_finish_shore_selection");
  check(e.state().units.at("armor").carriedBy == "t" &&
            e.state().units.at("i").zone == shantung,
        "Second-wave armor entered first combat round");
  auto probe = e.state().clone();
  const auto battle = probe.battles.begin()->first;
  removePoliticalUnits(probe, {"i"});
  releaseAmphibiousReserves(probe, battle);
  check(probe.units.at("armor").carriedBy == "t",
        "Lost first wave destroyed or unloaded waiting cargo");
  auto foothold = e.state().clone();
  releaseAmphibiousReserves(foothold, battle);
  check(!foothold.units.at("armor").carriedBy &&
            foothold.units.at("armor").zone == shantung,
        "Surviving first wave did not release armor");
}
void shoreBombardmentAndCoastalFirstStrike() {
  auto s = fixture();
  add(s, "t", "naval_transport", "japan", p14);
  add(s, "i", "infantry", "japan", p14);
  add(s, "bb", "battleship", "japan", p14);
  add(s, "defender", "infantry", "kmt", shantung);
  attachCargo(s, "t", "i");
  s.facilities["coast"] = {
      "coast", "coastal_artillery", shantung, 0, {{"border:" + p14, 1}}};
  Engine e(s, rules());
  e.setDiceTapeForTesting({1, 12, 12});
  choose(e, "naval_declare_assault", [](const Action &a) {
    return a.parameters.require("zone").asString() == shantung;
  });
  choose(e, "end_phase");
  choose(e, "naval_begin_assault");
  choose(e, "naval_select_bombardment");
  choose(e, "naval_finish_shore_selection");
  check(e.state().chance && e.state().chance->dice.size() == 3,
        "Shore/coastal shot count incorrect");
  e.resolveChance();
  choose(e, "naval_shore_casualty");
  check(!e.state().units.contains("defender") &&
            e.state().units.at("i").zone == shantung,
        "Shore first-strike casualty survived into land combat");
  check(e.state().units.at("bb").commitments.contains("shore_bombardment"),
        "Bombardment usage missing");
}
void berthLocksMovementAndKeepsCargo() {
  auto s = fixture(Phase::NonCombatMovement);
  add(s, "t", "naval_transport", "japan", p16);
  add(s, "i", "infantry", "japan", p16);
  attachCargo(s, "t", "i");
  s.facilities["port"] = {
      "port", "major_port", tokyo, 0, {{"border:" + p16, 1}}};
  Engine e(s, rules());
  choose(e, "naval_enter_port", [](const Action &a) {
    return !a.parameters.require("unload").asBool();
  });
  check(e.state().units.at("t").zone == tokyo &&
            e.state().units.at("i").zone == tokyo &&
            e.state().units.at("i").carriedBy == "t",
        "Berthing broke cargo location");
  check(!offered(e, "naval_start_move"),
        "Movement offered after end-of-movement berthing");
}
void capturedShipRollPreservesDamage() {
  auto s = fixture(Phase::PlaceUnits);
  add(s, "bb", "battleship", "kmt", beiping);
  s.units.at("bb").damage = 1;
  s.units.at("bb").gameFlags["in_port:port"] = 1;
  s.units.at("bb").gameFlags["skeleton_crew"] = 1;
  s.units.at("bb").gameFlags["skeleton_crew_until_own_turn"] = 1;
  s.facilities["port"] = {"port", "major_port", beiping, 0, {}};
  resolveCapturedPorts(s, beiping, "japan");
  Engine e(s, rules());
  e.setDiceTapeForTesting({10});
  choose(e, "naval_roll_capture");
  e.resolveChance();
  check(e.state().units.at("bb").owner == "japan" &&
            e.state().units.at("bb").damage == 1,
        "Capture failed to preserve damaged ship state");
  check(e.state().units.at("bb").gameFlags.at("skeleton_crew_until_own_turn") ==
            navalCompletedTurns(e.state(), "japan") + 2,
        "Captured skeleton crew did not retain the next full own-turn lock");
  auto loss = s.clone();
  Engine scuttle(loss, rules());
  scuttle.setDiceTapeForTesting({9});
  choose(scuttle, "naval_roll_capture");
  scuttle.resolveChance();
  check(!scuttle.state().units.contains("bb"), "Scuttle boundary wrong");
}
void portUnloadAlternativeNeedsOwnedCargo() {
  for (const bool ownCargo : {false, true}) {
    auto s = fixture(Phase::NonCombatMovement);
    ensureDadao(s);
    add(s, "transport", "naval_transport", "japan", p16);
    add(s, "foreign", "infantry", "dadao", p16);
    attachCargo(s, "transport", "foreign");
    if (ownCargo) {
      add(s, "own", "infantry", "japan", p16);
      attachCargo(s, "transport", "own");
    }
    s.facilities["home_port"] = {
        "home_port", "major_port", tokyo, 0, {{"border:" + p16, 1}}};
    Engine engine(s, rules(), 57);
    int choices = 0;
    bool unload = false;
    for (const auto &a : engine.legalActions())
      if (a.kind == "naval_enter_port" &&
          a.parameters.require("unit").asString() == "transport" &&
          a.parameters.require("facility").asString() == "home_port") {
        ++choices;
        unload |= a.parameters.require("unload").asBool();
      }
    check(choices == (ownCargo ? 2 : 1) && unload == ownCargo,
          "Port entry offers a duplicate foreign-only unload or loses owned unloading");
    if (ownCargo) {
      choose(engine, "naval_enter_port", [](const Action &a) {
        return a.parameters.require("facility").asString() == "home_port" &&
               a.parameters.require("unload").asBool();
      });
      check(!engine.state().units.at("own").carriedBy &&
                engine.state().units.at("foreign").carriedBy == "transport",
            "Port unload changed allied cargo or failed to unload owned cargo");
    }
  }
}
void temporaryCrewAndSkeletonRestriction() {
  auto s = fixture(Phase::Combat);
  add(s, "cruiser", "heavy_cruiser", "kmt", shantung);
  s.units.at("cruiser").gameFlags["in_port:port"] = 1;
  s.facilities["port"] = {"port", "major_port", shantung, 0, {}};
  add(s, "attacker", "infantry", "japan", shantung);
  const auto b = registerLandBattle(s, shantung, "japan", {"attacker"},
                                    {{"attacker", beiping}});
  preparePortLandDefence(s, b);
  int crews = 0;
  for (const auto &[id, u] : s.units)
    if (u.gameFlags.contains("ship_crew:cruiser"))
      ++crews;
  check(crews == 1 && s.battles.at(b).defenders.size() == 1,
        "Port ship fought as naval unit or supplied wrong crew");
  preparePortLandDefence(s, b);
  check(s.battles.at(b).defenders.size() == 1, "Ship crew created twice");
}
void amphibiousDoubleCasualtiesAndExemptions() {
  for (const auto &mode : {Id("ordinary"), Id("marine"), Id("doctrine")}) {
    auto s = fixture(Phase::Combat);
    add(s, "first", mode == "marine" ? "marine" : "infantry", "japan",
        shantung);
    add(s, "second", "infantry", "japan", shantung);
    add(s, "defender", "infantry", "kmt", shantung);
    for (const auto &id : {Id("first"), Id("second")})
      s.units.at(id).commitments.insert("amphibious_assault");
    if (mode == "doctrine")
      s.nations.at("japan").technologyStages["amphibious_doctrine"] = 4;
    registerLandBattle(s, shantung, "japan", {"first", "second"},
                       {{"first", p14}, {"second", p14}});
    Engine e(s, rules());
    e.setDiceTapeForTesting({12, 12, 1});
    choose(e, "land_begin_battle");
    check(e.state().chance && e.state().chance->dice.size() == 2,
          "First assault attack volley incorrect");
    e.resolveChance();
    e.resolveChance();
    choose(e, "land_take_casualty", [](const Action &a) {
      return a.parameters.require("unit").asString() == "first";
    });
    if (mode == "ordinary") {
      check(!e.state().decisions.empty() &&
                e.state().decisions.back().kind == "land_casualty",
            "One defending hit did not require second amphibious casualty");
      choose(e, "land_take_casualty");
      check(!e.state().units.contains("first") &&
                !e.state().units.contains("second"),
            "Double casualty did not remove both first-wave infantry");
    } else {
      check(!e.state().units.contains("first") &&
                e.state().units.contains("second"),
            "Marine or doctrine infantry did not retain single-casualty "
            "exemption");
    }
  }
}
void damagedPortEvacuationSuspendsAndResumesBombing() {
  auto s = fixture();
  add(s, "bomber", "medium_bomber", "japan", beiping);
  add(s, "cruiser", "heavy_cruiser", "kmt", shantung);
  s.units.at("cruiser").gameFlags["in_port:port"] = 1;
  s.facilities["port"] = {
      "port", "major_port", shantung, 0, {{"border:" + p14, 1}}};
  Engine e(s, rules());
  e.setDiceTapeForTesting({1, 12});
  const auto checkpoint = e.serialize();
  choose(e, "air_bomb", [](const Action &a) {
    return a.parameters.require("target").asString() == "port";
  });
  choose(e, "end_phase");
  choose(e, "air_begin_bombing");
  e.resolveChance();
  check(!e.state().chance &&
            e.state().decisions.back().kind == "naval_port_evacuation" &&
            e.state().decisionPlayer() == "allies",
        "Evacuation was delayed past AA or assigned to bomber policy");
  choose(e, "naval_evacuate_port");
  check(e.state().units.at("cruiser").zone == p14,
        "Evacuating ship stayed in damaged port");
  choose(e, "air_resume_bombing");
  finishBattles(e);
  check(Engine::replay(s.definition, rules(), checkpoint, e.state().history)
                .exactReplayIdentity() == e.exactReplayIdentity(),
        "Port evacuation interrupted bombing replay");
}
void thirdPartyEvacuationUsesFleetRolesAndPreservesBombing() {
  auto s = fixture();
  add(s, "bomber", "medium_bomber", "japan", beiping);
  for (const auto &id : {Id("cruiser_a"), Id("cruiser_b"), Id("waiting")}) {
    add(s, id, "heavy_cruiser", "kmt", shantung);
    s.units.at(id).gameFlags["in_port:port"] = 1;
  }
  add(s, "transport", "naval_transport", "kmt", shantung);
  s.units.at("transport").gameFlags["in_port:port"] = 1;
  add(s, "cargo", "infantry", "kmt", shantung);
  attachCargo(s, "transport", "cargo");
  for (const auto &id : {Id("destroyer_a"), Id("destroyer_b")})
    add(s, id, "destroyer", "ccp", p14);
  add(s, "enemy_transport", "naval_transport", "ccp", p14);
  add(s, "enemy_cargo", "infantry", "ccp", p14);
  attachCargo(s, "enemy_transport", "enemy_cargo");
  s.facilities["port"] = {
      "port", "major_port", shantung, 0, {{"border:" + p14, 1}}};
  s.nations.at("ccp").atWarWith.insert("kmt");
  s.nations.at("kmt").atWarWith.insert("ccp");
  Engine e(s, rules());
  // Bombing damage, two shots from the outside destroyers, the evacuating
  // cruisers' return fire, round two, the last unopposed transport, then AA.
  e.setDiceTapeForTesting({1, 1, 12, 1, 12, 12, 1, 1, 12});
  const auto checkpoint = e.serialize();
  choose(e, "air_bomb", [](const Action &a) {
    return a.parameters.require("target").asString() == "port";
  });
  choose(e, "end_phase");
  choose(e, "air_begin_bombing");
  e.resolveChance();
  const auto clock = canonicalJson(e.state().toJson(false).require("clock"));
  const auto completed = e.state().completedTurns;
  for (const auto &id : {Id("cruiser_a"), Id("cruiser_b")}) {
    choose(e, "naval_evacuate_port", [&](const Action &a) {
      return a.parameters.require("unit").asString() == id;
    });
    check(!e.state().chance && e.state().decisionPlayer() == "allies" &&
              e.state().units.at(id).zone == shantung,
          "Fleet fought before the defender finished selecting its evacuation");
  }
  choose(e, "naval_evacuate_port", [](const Action &a) {
    return a.parameters.require("unit").asString() == "transport";
  });
  check(e.state().chance && e.state().chance->nation == "ccp" &&
            e.state().chance->dice.size() == 2,
        "Outside fleet did not make the first attacking volley together");
  const auto battle = e.state().chance->continuation;
  const auto &b = e.state().battles.at(battle);
  check(b.attacker == "ccp" && b.defender == "kmt" && b.attackers.size() == 3 &&
            b.defenders.size() == 3 &&
            b.data.require("naval_entry_origins").asArray().empty(),
        "Third-party evacuation roles, full enemy fleet, or port origin wrong");
  check(e.state().units.at("cargo").zone == p14 &&
            e.state().units.at("cargo").carriedBy == "transport" &&
            e.state().units.at("waiting").zone == shantung,
        "Three-ship limit or linked evacuation cargo wrong");
  check(!offered(e, "air_resume_bombing") && e.legalInterrupts().empty(),
        "Unrelated calendar activity escaped the immediate naval battle");
  e.resolveChance();
  check(e.state().decisionPlayer() == "allies",
        "Evacuating defender casualty belonged to the active Japan policy");
  choose(e, "naval_take_casualty", [](const Action &a) {
    return a.parameters.require("unit").asString() == "cruiser_a";
  });
  check(e.state().chance && e.state().chance->dice.size() == 2,
        "Selected defending casualty lost its return shot");
  e.resolveChance();
  check(e.state().decisionPlayer() == "comintern",
        "Third-party attacker casualty belonged to the active Japan policy");
  choose(e, "naval_take_casualty", [](const Action &a) {
    return a.parameters.require("unit").asString() == "destroyer_a";
  });
  check(e.state().chance &&
            e.state().battles.at(battle).data.require("round").asInt() == 2 &&
            !offered(e, "naval_retreat_begin"),
        "Port evacuation invented an adjacent retreat sea or a one-round cap");
  e.resolveChance();
  e.resolveChance();
  choose(e, "naval_take_casualty", [](const Action &a) {
    return a.parameters.require("unit").asString() == "destroyer_b";
  });
  e.resolveChance();
  choose(e, "naval_take_casualty");
  check(
      !e.state().units.contains("enemy_transport") &&
          !e.state().units.contains("enemy_cargo") &&
          e.state().units.contains("cargo"),
      "Enemy transport did not join the required combat or lost cargo wrongly");
  const auto cleanup = e.legalActions();
  check(cleanup.size() == 1 && cleanup.front().kind == "naval_finish_battle",
        "Bombing resumed before mandatory naval cleanup");
  choose(e, "naval_finish_battle");
  check(!offered(e, "naval_evacuate_port") && offered(e, "air_resume_bombing"),
        "Three completed escape choices restarted evacuation or lost bombing");
  choose(e, "air_resume_bombing");
  finishBattles(e);
  check(e.state().currentNation() == "japan" &&
            canonicalJson(e.state().toJson(false).require("clock")) == clock &&
            e.state().completedTurns == completed,
        "Third-party combat advanced the active calendar or national turn");
  check(Engine::replay(s.definition, rules(), checkpoint, e.state().history)
                .exactReplayIdentity() == e.exactReplayIdentity(),
        "Third-party evacuation/bombing exact replay differs");
}
void activeEnemyAttacksEvacuationAndSelectionMayStop() {
  auto s = fixture(Phase::Combat);
  for (const auto &id : {Id("cruiser"), Id("waiting")}) {
    add(s, id, "heavy_cruiser", "kmt", shantung);
    s.units.at(id).gameFlags["in_port:port"] = 1;
  }
  add(s, "active_enemy", "destroyer", "japan", p14);
  add(s, "neutral", "destroyer", "mongolia", p14);
  s.nations.at("mongolia").atWarWith.erase("kmt");
  s.nations.at("kmt").atWarWith.erase("mongolia");
  s.facilities["port"] = {
      "port", "major_port", shantung, 1, {{"border:" + p14, 1}}};
  queueDamagedPortEvacuation(s, "port");
  Engine e(s, rules());
  e.setDiceTapeForTesting({12, 1});
  const auto checkpoint = e.serialize();
  choose(e, "naval_evacuate_port", [](const Action &a) {
    return a.parameters.require("unit").asString() == "cruiser";
  });
  choose(e, "naval_finish_evacuation");
  check(e.state().chance && e.state().chance->nation == "japan",
        "Active enemy did not become the attacking fleet");
  const auto &battle = e.state().battles.at(e.state().chance->continuation);
  check(battle.attacker == "japan" && battle.defender == "kmt" &&
            battle.attackers == std::vector<Id>{"active_enemy"} &&
            battle.defenders == std::vector<Id>{"cruiser"},
        "Calendar nation or neutral ships corrupted evacuation participants");
  finishBattles(e);
  check(
      e.state().units.at("waiting").zone == shantung &&
          e.state().decisions.empty() && !offered(e, "naval_evacuate_port"),
      "Declined remaining evacuation reopened after observing battle results");
  check(Engine::replay(s.definition, rules(), checkpoint, e.state().history)
                .exactReplayIdentity() == e.exactReplayIdentity(),
        "Partial fleet selection replay differs");
}
void evacuationUsesAttackAndDefenseValues() {
  auto s = fixture(Phase::Combat);
  add(s, "carrier", "fleet_carrier", "kmt", shantung);
  s.units.at("carrier").gameFlags["in_port:port"] = 1;
  add(s, "outside", "coastal_defense_ship", "japan", p14);
  s.facilities["port"] = {
      "port", "major_port", shantung, 1, {{"border:" + p14, 1}}};
  queueDamagedPortEvacuation(s, "port");
  Engine e(s, rules());
  // A coastal defense ship attacks at 4 rather than defending at 6. The
  // evacuating carrier has no attack but defends at 2.
  e.setDiceTapeForTesting({5, 2});
  const auto checkpoint = e.serialize();
  choose(e, "naval_evacuate_port");
  const auto battle = e.state().chance->continuation;
  const auto &attacking = e.state().battles.at(battle).data.require("naval_shots");
  check(attacking.asArray().size() == 1 &&
            attacking.asArray().front().require("unit").asString() == "outside" &&
            attacking.asArray().front().require("threshold").asInt() == 4,
        "Outside fleet used its defense value or the carrier attacked");
  e.resolveChance();
  const auto &defending = e.state().battles.at(battle).data.require("naval_shots");
  check(e.state().chance && defending.asArray().size() == 1 &&
            defending.asArray().front().require("unit").asString() == "carrier" &&
            defending.asArray().front().require("threshold").asInt() == 2,
        "Evacuating carrier failed to use its defense value");
  e.resolveChance();
  check(e.state().decisionPlayer() == "axis",
        "Outside attacking fleet casualty was assigned to the evacuee");
  choose(e, "naval_take_casualty");
  finishBattles(e);
  check(e.state().units.contains("carrier") &&
            e.state().units.at("carrier").damage == 0 &&
            !e.state().units.contains("outside"),
        "Asymmetric attack/defense rolls produced the wrong evacuation result");
  check(Engine::replay(s.definition, rules(), checkpoint, e.state().history)
                .exactReplayIdentity() == e.exactReplayIdentity(),
        "Asymmetric evacuation combat replay differs");
}
void evacuatingSubmarineMakesDefendingChoicesAndSubmerges() {
  auto s = fixture(Phase::Combat);
  add(s, "sub", "submarine", "kmt", shantung);
  s.units.at("sub").gameFlags["in_port:base"] = 1;
  add(s, "outside", "destroyer", "japan", p14);
  s.facilities["base"] = {
      "base", "submarine_base", shantung, 1, {{"border:" + p14, 1}}};
  queueDamagedPortEvacuation(s, "base");
  Engine e(s, rules());
  e.setDiceTapeForTesting({12});
  const auto checkpoint = e.serialize();
  choose(e, "naval_evacuate_port");
  check(!e.state().chance &&
            e.state().decisions.back().kind == "naval_submarine_participation" &&
            e.state().decisionPlayer() == "allies" &&
            offered(e, "naval_sub_decline"),
        "Evacuating submarine lost its defending participation choice");
  choose(e, "naval_sub_protected");
  e.resolveChance();
  finishBattles(e);
  check(e.state().units.contains("sub") &&
            e.state().units.at("sub").turnFlags.at("submerged") == 1 &&
            e.state().units.at("sub").zone == p14,
        "Evacuating defending submarine failed to submerge after one round");
  check(Engine::replay(s.definition, rules(), checkpoint, e.state().history)
                .exactReplayIdentity() == e.exactReplayIdentity(),
        "Evacuating submarine replay differs");
}
void evacuationScramblesOnlySupportTheDefendingFleet() {
  auto s = fixture(Phase::Combat);
  add(s, "cruiser", "heavy_cruiser", "kmt", shantung);
  s.units.at("cruiser").gameFlags["in_port:port"] = 1;
  add(s, "defending_fighter", "fighter", "kmt", shantung);
  add(s, "outside", "destroyer", "japan", p14);
  add(s, "attacking_fighter", "fighter", "japan", beiping);
  s.facilities["port"] = {
      "port", "major_port", shantung, 1, {{"border:" + p14, 1}}};
  s.facilities["defending_airbase"] = {
      "defending_airbase", "airbase", shantung, 0, {}};
  s.facilities["attacking_airbase"] = {
      "attacking_airbase", "airbase", beiping, 0, {}};
  queueDamagedPortEvacuation(s, "port");
  Engine e(s, rules());
  e.setDiceTapeForTesting({1});
  const auto checkpoint = e.serialize();
  choose(e, "naval_evacuate_port");
  check(!e.state().chance && e.state().decisionPlayer() == "allies",
        "Evacuation scramble was assigned to the outside attacking fleet");
  for (const auto &a : e.legalActions())
    check(a.parameters.require("unit").asString() == "defending_fighter",
          "The outside attacking fleet received a defensive air scramble");
  choose(e, "air_scramble");
  choose(e, "naval_progress_battle");
  const auto &battle = e.state().battles.at(e.state().chance->continuation);
  check(battle.defenders == std::vector<Id>({"cruiser", "defending_fighter"}) &&
            e.state().units.at("attacking_fighter").zone == beiping,
        "Airbase scramble joined the wrong side of evacuation combat");
  finishBattles(e);
  check(Engine::replay(s.definition, rules(), checkpoint, e.state().history)
                .exactReplayIdentity() == e.exactReplayIdentity(),
        "Evacuation defensive air scramble replay differs");
}
void multinationalOutsideFleetUsesActualCasualtyPolicies() {
  auto s = fixture(Phase::Combat);
  add(s, "cruiser", "heavy_cruiser", "kmt", shantung);
  s.units.at("cruiser").gameFlags["in_port:port"] = 1;
  add(s, "axis_ship", "destroyer", "japan", p14);
  add(s, "comintern_ship", "destroyer", "ccp", p14);
  s.nations.at("ccp").atWarWith.insert("kmt");
  s.nations.at("kmt").atWarWith.insert("ccp");
  s.facilities["port"] = {
      "port", "major_port", shantung, 1, {{"border:" + p14, 1}}};
  queueDamagedPortEvacuation(s, "port");
  Engine e(s, rules());
  e.setDiceTapeForTesting({12, 12, 4, 1, 1});
  const auto checkpoint = e.serialize();
  choose(e, "naval_evacuate_port");
  const auto &battle = e.state().battles.at(e.state().chance->continuation);
  check(battle.attackers == std::vector<Id>({"axis_ship", "comintern_ship"}) &&
            battle.defenders == std::vector<Id>{"cruiser"},
        "Role reversal omitted an enemy already required to fight outside");
  e.resolveChance();
  e.resolveChance();
  choose(e, "naval_take_casualty", [](const Action &a) {
    return a.parameters.require("unit").asString() == "axis_ship";
  });
  check(e.state().decisionPlayer() == "comintern" &&
            offered(e, "naval_casualty_accept"),
        "Second attacking policy did not consent to the joint fleet casualty");
  choose(e, "naval_casualty_accept");
  e.resolveChance();
  choose(e, "naval_take_casualty");
  e.resolveChance();
  check(e.state().decisionPlayer() == "comintern",
        "Last surviving attacking policy's casualty went to an eliminated fleet");
  choose(e, "naval_take_casualty");
  finishBattles(e);
  check(Engine::replay(s.definition, rules(), checkpoint, e.state().history)
                .exactReplayIdentity() == e.exactReplayIdentity(),
        "Multinational evacuation combat replay differs");
}
void currentTurnOutsideFleetMayRetreatToItsRealEntrySea() {
  auto s = fixture();
  const Id origin = "sea_p15";
  add(s, "bomber", "medium_bomber", "japan", beiping);
  add(s, "outside", "destroyer", "japan", origin);
  add(s, "cruiser", "heavy_cruiser", "kmt", shantung);
  s.units.at("cruiser").gameFlags["in_port:port"] = 1;
  s.facilities["port"] = {
      "port", "major_port", shantung, 0, {{"border:" + p14, 1}}};
  Engine e(s, rules());
  e.setDiceTapeForTesting({1, 12, 12, 12});
  const auto checkpoint = e.serialize();
  choose(e, "air_bomb", [](const Action &a) {
    return a.parameters.require("target").asString() == "port";
  });
  choose(e, "naval_start_move", [](const Action &a) {
    return a.parameters.require("unit").asString() == "outside";
  });
  choose(e, "naval_route", [&](const Action &a) {
    return canonicalJson(a.parameters.require("request").require("path")) ==
           canonicalJson(V(V::Array{V(origin), V(p14)}));
  });
  choose(e, "end_phase");
  choose(e, "air_begin_bombing");
  e.resolveChance();
  const auto clock = canonicalJson(e.state().toJson(false).require("clock"));
  choose(e, "naval_evacuate_port");
  e.resolveChance();
  e.resolveChance();
  check(offered(e, "naval_retreat_begin") &&
            e.state().decisionPlayer() == "axis",
        "Outside fleet lost the retreat earned by its actual combat movement");
  choose(e, "naval_retreat_begin");
  for (const auto &a : e.legalActions())
    check(a.parameters.require("zone").asString() == origin,
          "Forced evacuation combat invented an unused retreat sea");
  choose(e, "naval_retreat_unit");
  choose(e, "naval_finish_battle");
  check(e.state().units.at("outside").zone == origin &&
            e.state().units.at("outside").movementRemaining == 0 &&
            e.state().units.at("cruiser").zone == p14 &&
            canonicalJson(e.state().toJson(false).require("clock")) == clock &&
            offered(e, "air_resume_bombing"),
        "Outside fleet retreat lost its origin, advanced the turn, or lost bombing");
  choose(e, "air_resume_bombing");
  finishBattles(e);
  check(Engine::replay(s.definition, rules(), checkpoint, e.state().history)
                .exactReplayIdentity() == e.exactReplayIdentity(),
        "Current-turn outside fleet retreat replay differs");
}
void mandatoryEvacuationDoesNotMergeOrdinaryNavalDeclarations() {
  for (const bool evacuationFirst : {false, true}) {
    auto s = fixture(Phase::Combat);
    add(s, "outside", "destroyer", "japan", p14);
    add(s, "evacuated", "heavy_cruiser", "kmt", p14);
    add(s, "ordinary_defender", "destroyer", "kmt", p14);
    const V ordinary(V::Object{
        {"context", V(Id("standard"))},
        {"defenders", V(V::Array{V(Id("ordinary_defender"))})}});
    const V evacuation(V::Object{
        {"context", V(Id("standard"))},
        {"port_evacuation", V(Id("port"))},
        {"defenders", V(V::Array{V(Id("evacuated"))})}});
    const auto first = registerNavalBattle(
        s, p14, "japan", {"outside"}, {},
        evacuationFirst ? evacuation : ordinary);
    const auto second = registerNavalBattle(
        s, p14, "japan", {"outside"}, {},
        evacuationFirst ? ordinary : evacuation);
    check(first != second && s.battles.size() == 2 &&
              s.battles.at(first).defenders.size() == 1 &&
              s.battles.at(second).defenders.size() == 1 &&
              s.battles.at(first).defenders != s.battles.at(second).defenders,
          "Mandatory evacuation merged with an ordinary pending declaration");
  }
}
void separateEvacuationSeasResolveBeforeCalendarResumes() {
  auto s = fixture(Phase::NonCombatMovement);
  const Id p15 = "sea_p15";
  s.territories.at(tokyo).possessor = "kmt";
  for (const auto &id : {Id("first"), Id("second")}) {
    add(s, id, "heavy_cruiser", "kmt", tokyo);
    s.units.at(id).gameFlags["in_port:port"] = 1;
  }
  add(s, "enemy_first", "destroyer", "ccp", p15);
  add(s, "enemy_second", "destroyer", "ccp", p16);
  s.nations.at("ccp").atWarWith.insert("kmt");
  s.nations.at("kmt").atWarWith.insert("ccp");
  s.facilities["port"] = {"port",
                          "major_port",
                          tokyo,
                          1,
                          {{"border:" + p15, 1}, {"border:" + p16, 1}}};
  queueDamagedPortEvacuation(s, "port");
  Engine e(s, rules());
  e.setDiceTapeForTesting({12, 1, 12, 1});
  const auto checkpoint = e.serialize();
  const auto clock = canonicalJson(e.state().toJson(false).require("clock"));
  choose(e, "naval_evacuate_port", [&](const Action &a) {
    return a.parameters.require("unit").asString() == "first" &&
           a.parameters.require("sea").asString() == p15;
  });
  choose(e, "naval_evacuate_port", [](const Action &a) {
    return a.parameters.require("unit").asString() == "second" &&
           a.parameters.require("sea").asString() == p16;
  });
  check(e.state().battles.size() == 2 && e.state().chance,
        "Separate sea evacuations were not retained as immediate combats");
  e.resolveChance();
  e.resolveChance();
  choose(e, "naval_take_casualty");
  choose(e, "naval_finish_battle");
  check(e.state().battles.size() == 1 && e.state().chance &&
            e.state().chance->nation == "ccp" && e.legalInterrupts().empty(),
        "First cleanup failed to start the next required evacuation combat");
  finishBattles(e);
  check(canonicalJson(e.state().toJson(false).require("clock")) == clock &&
            e.state().units.at("first").zone == p15 &&
            e.state().units.at("second").zone == p16,
        "Multiple evacuation combats changed destination or calendar");
  check(Engine::replay(s.definition, rules(), checkpoint, e.state().history)
                .exactReplayIdentity() == e.exactReplayIdentity(),
        "Multiple evacuation seas replay differs");
}
void sharedShoreCasualtiesNeedBothPolicies() {
  auto s = fixture();
  s.politics.chineseTruce = true;
  s.nations.at("japan").atWarWith.insert("ccp");
  s.nations.at("ccp").atWarWith.insert("japan");
  add(s, "t", "naval_transport", "japan", p14);
  add(s, "i", "infantry", "japan", p14);
  add(s, "bb", "battleship", "japan", p14);
  add(s, "kmt", "infantry", "kmt", shantung);
  add(s, "ccp", "infantry", "ccp", shantung);
  attachCargo(s, "t", "i");
  Engine e(s, rules());
  e.setDiceTapeForTesting({1, 1, 12});
  choose(e, "naval_declare_assault", [](const Action &a) {
    return a.parameters.require("zone").asString() == shantung;
  });
  choose(e, "end_phase");
  choose(e, "naval_begin_assault");
  choose(e, "naval_select_bombardment");
  choose(e, "naval_finish_shore_selection");
  e.resolveChance();
  choose(e, "naval_shore_casualty", [](const Action &a) {
    return a.parameters.require("unit").asString() == "kmt";
  });
  check(e.state().decisionPlayer() == "comintern" &&
            e.state().units.contains("kmt"),
        "Shore casualty bypassed other defending policy");
  choose(e, "naval_shore_dispute");
  e.resolveChance();
  check(e.state().decisionPlayer() == "comintern",
        "High-die defending policy did not receive casualty choice");
  choose(e, "naval_shore_casualty", [](const Action &a) {
    return a.parameters.require("unit").asString() == "kmt";
  });
  check(!e.state().units.contains("kmt") && e.state().units.contains("ccp"),
        "Disputed shore casualty not applied");
}
void carrierAircraftAndProtectedSubmarinesAreNotAssaultTargets() {
  auto s = fixture();
  add(s, "carrier", "fleet_carrier", "japan", p14);
  add(s, "fighter", "fighter", "japan", p14);
  attachCargo(s, "carrier", "fighter");
  add(s, "sub", "submarine", "kmt", p14);
  Engine e(s, rules());
  check(!offered(e, "naval_declare_assault"),
        "Carrier aircraft offered as landing troops");
  auto free = s.clone();
  detachCargo(free, "carrier", "fighter", beiping);
  Engine attack(free, rules());
  check(!offered(attack, "naval_air_attack"),
        "Ordinary aircraft attacked protected submarine without MAP");
}
void portUnloadCannotBecomeRailOrAirMove() {
  auto s = fixture(Phase::NonCombatMovement);
  add(s, "t", "naval_transport", "japan", p16);
  add(s, "i", "infantry", "japan", p16);
  attachCargo(s, "t", "i");
  s.facilities["port"] = {
      "port", "major_port", tokyo, 0, {{"border:" + p16, 1}}};
  Engine e(s, rules());
  choose(e, "naval_enter_port", [](const Action &a) {
    return a.parameters.require("unload").asBool();
  });
  check(
      !validateRoute(e.state(),
                     {"i", {tokyo, honshu}, MovementMode::StrategicRail, false})
           .allowed,
      "Port-unloaded infantry reused strategic movement");
}
void recordCombinedExitTrace(const Id &variant, const State &initial,
                             const Engine &engine,
                             const std::vector<int> &dice,
                             const Id &fixtureFunction =
                                 "japanToChinaVoyageAndLanding") {
  const auto *directory = std::getenv("GWRL_NAVAL_EXIT_TRACE_DIR");
  if (!directory)
    return;
  // Optional verification evidence only. Test dice/checkpoints never become
  // policy observations or rule state.
  V::Array tape;
  for (const int face : dice)
    tape.emplace_back(static_cast<double>(face));
  const V trace(V::Object{
      {"schema", V(Id("naval_combined_exit_trace_v1"))},
      {"fixture", V(fixtureFunction)},
      {"variant", V(variant)},
      {"execution_seed", V(1.0)},
      {"controlled_test_dice", V(std::move(tape))},
      {"initial_state", initial.toJson(false)},
      {"final_state", engine.state().toJson(false)},
      {"events", engine.state().toJson().require("history")},
      {"exact_replay_identity_verified", V(true)}});
  std::filesystem::create_directories(directory);
  const auto path = std::filesystem::path(directory) /
                    ("combined_" + variant + "_2026_10_23.json");
  std::ofstream output(path);
  check(bool(output), "Could not open combined naval trace evidence");
  output << canonicalJson(trace) << '\n';
  check(bool(output), "Could not write combined naval trace evidence");
}
void japanToChinaVoyageAndLanding(const Id &variant) {
  const Id p15 = "sea_p15";
  auto s = fixture();
  add(s, "transport", "naval_transport", "japan", p16);
  add(s, "screen", "heavy_cruiser", "japan", p16);
  add(s, "bombard", "battleship", "japan", p16);
  add(s, "idle", "destroyer", "japan", p16);
  add(s, "marine", "marine", "japan", honshu);
  add(s, "reinforcement", "infantry", "japan", beiping);
  add(s, "defender", "infantry", "kmt", shantung);
  if (variant != "clear")
    add(s, "blocker", "destroyer", "kmt", p15);
  if (variant == "retreat")
    add(s, "origin_enemy", "destroyer", "kmt", p16);
  s.facilities["home_shipyard"] = {
      "home_shipyard", "major_shipyard", tokyo, 0, {{"border:" + p16, 1}}};
  s.facilities["coast"] = {
      "coast", "coastal_artillery", shantung, 0, {{"border:" + p14, 1}}};
  s.captureTurnStart();
  Engine e(s, rules());
  auto tape = variant == "clear"     ? std::vector<int>{1, 12, 12}
              : variant == "retreat" ? std::vector<int>{12, 12}
                                     : std::vector<int>{1, 12, 1, 12, 12};
  // The real campaign's capture aftermath may also resolve queued warlord
  // rolls.
  tape.insert(tape.end(), 32, 1);
  e.setDiceTapeForTesting(tape);
  const auto checkpoint = e.serialize();
  choose(e, "naval_load", [](const Action &a) {
    return a.parameters.require("transport").asString() == "transport" &&
           a.parameters.require("unit").asString() == "marine";
  });
  choose(e, "naval_start_move", [](const Action &a) {
    return a.parameters.require("unit").asString() == "transport";
  });
  for (const auto &id : {Id("screen"), Id("bombard")})
    choose(e, "naval_force_add", [&](const Action &a) {
      return a.parameters.require("unit").asString() == id;
    });
  choose(e, "naval_route", [&](const Action &a) {
    return canonicalJson(a.parameters.require("request").require("path")) ==
           canonicalJson(V(V::Array{V(p16), V(p15), V(p14)}));
  });
  if (variant != "clear") {
    choose(e, "naval_screen_add", [](const Action &a) {
      return a.parameters.require("unit").asString() == "screen";
    });
    choose(e, "naval_screen_confirm");
    check(e.state().units.at("marine").carriedBy == "transport" &&
              e.state().units.at("transport").zone == p15,
          "Contested Japan-to-China voyage lost its waiting cargo");
    choose(e, "end_phase");
    choose(e, "naval_begin_battle");
    e.resolveChance();
    if (variant != "retreat")
      choose(e, "naval_take_casualty");
    e.resolveChance();
    if (variant == "retreat") {
      choose(e, "naval_retreat_begin");
      choose(e, "naval_retreat_unit");
      check(e.state().battles.empty() &&
                e.state().units.at("screen").zone == p16 &&
                e.state().units.at("transport").zone == p16 &&
                e.state().units.at("bombard").zone == p16 &&
                e.state().units.at("marine").zone == p16 &&
                e.state().units.at("marine").carriedBy == "transport" &&
                e.state().units.at("transport").movementRemaining == 0 &&
                e.state().units.at("origin_enemy").zone == p16 &&
                e.state().units.at("origin_enemy").damage == 0 &&
                e.state().territories.at(shantung).possessor == "kmt" &&
                !offered(e, "naval_declare_assault"),
            "Lost screening failed to return continuing ships/cargo or allowed "
            "landing");
      check(Engine::replay(s.definition, rules(), checkpoint, e.state().history)
                    .exactReplayIdentity() == e.exactReplayIdentity(),
            "Contested voyage retreat replay differs");
      recordCombinedExitTrace(variant, s, e, tape);
      return;
    }
    choose(e, "naval_screen_continue_route");
    check(e.state().clock.phase == Phase::Combat &&
              e.state().units.at("transport").zone == p14 &&
              e.state().units.at("screen").zone == p15,
          "Winning screening did not release only the continuing force");
    for (const auto &a : e.legalActions())
      check(!(a.kind == "naval_start_move" &&
              a.parameters.require("unit").asString() == "idle"),
            "Screening success granted unrelated ships a new movement phase");
  }
  choose(e, "naval_load", [](const Action &a) {
    return a.parameters.require("transport").asString() == "transport" &&
           a.parameters.require("unit").asString() == "reinforcement";
  });
  for (const auto &id : {Id("marine"), Id("reinforcement")})
    choose(e, "naval_declare_assault", [&](const Action &a) {
      return a.parameters.require("cargo").asString() == id &&
             a.parameters.require("zone").asString() == shantung;
    });
  if (variant == "clear")
    choose(e, "end_phase");
  choose(e, "naval_begin_assault");
  choose(e, "naval_select_bombardment", [](const Action &a) {
    return a.parameters.require("unit").asString() == "bombard";
  });
  choose(e, "naval_finish_shore_selection");
  check(e.state().chance && e.state().chance->dice.size() == 3,
        "Combined voyage lost eligible shore bombardment or coastal shots");
  e.resolveChance();
  choose(e, "naval_shore_casualty");
  finishBattles(e);
  check(e.state().territories.at(shantung).possessor == "japan" &&
            e.state().units.at("marine").zone == shantung &&
            e.state().units.at("reinforcement").zone == shantung &&
            !e.state().units.at("marine").carriedBy &&
            !e.state().units.at("reinforcement").carriedBy &&
            e.state().units.at("transport").movementRemaining == 0 &&
            e.state().facilities.find("coast") == e.state().facilities.end(),
        "Japan-to-China reinforcement/assault did not capture and unload "
        "exactly");
  check(e.state().currentNation() == "japan" &&
            e.state().clock.phase == Phase::Combat &&
            e.state().clock.playerTurnSerial == 2,
        "Combined screening and amphibious trace changed the calendar");
  check(Engine::replay(s.definition, rules(), checkpoint, e.state().history)
                .exactReplayIdentity() == e.exactReplayIdentity(),
        "Japan-to-China combined voyage/landing replay differs");
  recordCombinedExitTrace(variant, s, e, tape);
}
void berthWaitsForMandatoryLandingAndWithdrawal() {
  auto s = fixture(Phase::NonCombatMovement);
  add(s, "ship", "destroyer", "japan", p16);
  add(s, "aircraft", "medium_bomber", "japan", p16);
  s.units.at("aircraft").turnFlags["air_in_flight"] = 1;
  s.facilities["home_port"] = {
      "home_port", "major_port", tokyo, 0, {{"border:" + p16, 1}}};
  for (bool restoredBerthing : {false, true}) {
    auto state = s.clone();
    if (restoredBerthing)
      state.flags["naval_berthing"] = 1;
    Engine e(state, rules());
    check(!offered(e, "naval_enter_port") && offered(e, "air_land_noncombat"),
          "Berthing stranded a mandatory airborne return");
    choose(e, "air_land_noncombat", [](const Action &a) {
      return a.parameters.require("destination").asString() == tokyo;
    });
    check(offered(e, "naval_enter_port"),
          "Finished landing failed to release end-of-movement berthing");
  }
  auto gift = fixture(Phase::NonCombatMovement);
  gift.territories.at(honshu).possessor = "ccp";
  add(gift, "transport", "naval_transport", "japan", p16);
  add(gift, "gift", "infantry", "japan", honshu);
  gift.units.at("gift").turnFlags["must_withdraw_from_chinese_gift"] = 1;
  gift.units.at("gift").commitments.insert("combat_move");
  gift.facilities["home_port"] = s.facilities.at("home_port");
  gift.flags["naval_berthing"] = 1;
  Engine e(gift, rules());
  check(!offered(e, "naval_enter_port") && offered(e, "naval_load"),
        "Restored berthing lock stranded mandatory Chinese gift withdrawal");
  choose(e, "naval_load");
  check(offered(e, "naval_enter_port"),
        "Gift boarding failed to release final berthing");
}
void adjacentLandAndAmphibiousAttacksResolveTogether() {
  auto s = fixture();
  const Id origin = "land_china_hopeh";
  s.territories.at(origin).possessor = "japan";
  add(s, "transport", "naval_transport", "japan", p14);
  add(s, "amphibious", "infantry", "japan", p14);
  add(s, "overland", "infantry", "japan", origin);
  add(s, "bombard", "battleship", "japan", p14);
  add(s, "defender", "infantry", "kmt", shantung);
  attachCargo(s, "transport", "amphibious");
  s.facilities["coast"] = {
      "coast", "coastal_artillery", shantung, 0, {{"border:" + p14, 1}}};
  s.captureTurnStart();
  Engine e(s, rules());
  std::vector<int> tape(6, 12); // Shore shots, both attackers, defender miss.
  tape.push_back(1);
  tape.push_back(12);
  tape.insert(tape.end(), 32, 1);
  e.setDiceTapeForTesting(tape);
  const auto checkpoint = e.serialize();
  choose(e, "movement_route", [&](const Action &a) {
    return a.parameters.require("unit").asString() == "overland" &&
           canonicalJson(a.parameters.require("path")) ==
               canonicalJson(V(V::Array{V(origin), V(shantung)}));
  });
  const auto land = e.state().battles.begin()->first;
  choose(e, "naval_declare_assault", [](const Action &a) {
    return a.parameters.require("zone").asString() == shantung;
  });
  choose(e, "end_phase");
  check(!offered(e, "land_begin_battle") && offered(e, "naval_begin_assault"),
        "Overland combat started before the same nation's declared landing");
  // The guard concerns this attacker and target, not every pending landing.
  for (bool otherNation : {false, true}) {
    auto independent = e.state().clone();
    for (auto &[id, b] : independent.battles)
      if (b.flags.contains("amphibious_preparation")) {
        if (otherNation)
          b.attacker = "ccp";
        else
          b.zone = beiping;
      }
    const auto actions = LandCombatRules().actions(independent);
    check(std::any_of(actions.begin(), actions.end(), [&](const Action &a) {
            return a.kind == "land_begin_battle" &&
                   a.parameters.require("battle").asString() == land;
          }), "Independent target or nation's preparation blocked land combat");
  }
  choose(e, "naval_begin_assault");
  choose(e, "naval_select_bombardment");
  choose(e, "naval_finish_shore_selection");
  check(e.state().chance && e.state().chance->purpose == "naval_shore_roll" &&
            e.state().units.at("amphibious").carriedBy == "transport" &&
            !e.state().units.at("overland").commitments.contains("combat"),
        "Land units fired or landed before shore/Coastal Artillery first strike");
  e.resolveChance();
  check(e.state().battles.size() == 1 && e.state().battles.contains(land),
        "Declared landing created a second land battle instead of merging");
  const auto &combined = e.state().battles.at(land);
  check(combined.attackers.size() == 2 &&
            combined.data.require("origins").require("overland").asString() == origin &&
            combined.data.require("origins").require("amphibious").asString() == p14 &&
            landRetreatOrigins(e.state(), combined) == std::set<Id>{origin},
        "Combined attack lost either approach or invented an amphibious retreat");
  choose(e, "land_begin_battle");
  e.resolveChance();
  e.resolveChance();
  choose(e, "land_retreat_begin");
  for (const auto &a : e.legalActions())
    check(a.kind == "land_retreat_unit" &&
              a.parameters.require("unit").asString() == "overland" &&
              a.parameters.require("zone").asString() == origin,
          "Combined retreat allowed the amphibious force to withdraw");
  choose(e, "land_retreat_unit");
  check(e.state().units.at("overland").zone == origin &&
            e.state().units.at("amphibious").zone == shantung,
        "Overland retreat moved the amphibious attackers with it");
  finishBattles(e);
  check(e.state().territories.at(shantung).possessor == "japan" &&
            e.state().units.at("overland").zone == origin &&
            e.state().units.at("amphibious").zone == shantung,
        "Remaining amphibious force failed to resolve its combined attack");
  check(Engine::replay(s.definition, rules(), checkpoint, e.state().history)
                .exactReplayIdentity() == e.exactReplayIdentity(),
        "Combined overland/amphibious preparation and retreat replay differs");
  recordCombinedExitTrace("overland_amphibious", s, e, tape,
                          "adjacentLandAndAmphibiousAttacksResolveTogether");
}
void actualNavalAirDeclarationsKeepContextAndCombatPhase() {
  for (const auto &kind : {Id("naval_air_attack"), Id("naval_port_attack"),
                           Id("naval_patrol_attack")}) {
    auto s = fixture(kind == "naval_patrol_attack" ? Phase::Combat
                                                   : Phase::CombatMovement);
    add(s, "plane",
        kind == "naval_patrol_attack" ? "seaplane" : "medium_bomber", "japan",
        kind == "naval_patrol_attack" ? p14 : beiping);
    if (kind == "naval_patrol_attack") {
      s.units.at("plane").gameFlags["on_map"] = 1;
      s.units.at("plane").gameFlags["map_range"] = 2;
    }
    add(s, "defender", "destroyer", "kmt",
        kind == "naval_port_attack" ? shantung : p14);
    if (kind == "naval_port_attack") {
      s.units.at("defender").gameFlags["in_port:port"] = 1;
      s.facilities["port"] = {
          "port", "major_port", shantung, 0, {{"border:" + p14, 1}}};
    }
    Engine e(s, rules());
    const auto checkpoint = e.serialize();
    choose(e, kind);
    check(e.state().battles.size() == 1 &&
              e.state()
                      .battles.begin()
                      ->second.data.require("context")
                      .asString() ==
                  (kind == "naval_port_attack" ? "port_attack" : "standard"),
          "Actual naval air mission serialized a boolean context");
    if (kind != "naval_patrol_attack") {
      check(e.state().units.at("plane").commitments.contains("air_combat") &&
                !offered(e, "air_fly") && !offered(e, "air_land_noncombat"),
            "Declared naval aircraft received another move or landed before "
            "its battle");
      check(!offered(e, "naval_begin_battle") && offered(e, "end_phase"),
            "Declared naval air combat ran during Combat Movement or blocked "
            "Combat");
      choose(e, "end_phase");
    }
    choose(e, "naval_begin_battle");
    if (kind == "naval_port_attack")
      check(!offered(e, "naval_scramble") &&
                e.state().units.at("defender").zone == shantung,
            "A port attack allowed its ships to scramble out of the port");
    check(e.state().clock.phase == Phase::Combat && e.state().chance,
          "Actual " + kind + " declaration failed to reach combat dice (stage " +
              e.state().battles.begin()->second.stage + ")");
    check(Engine::replay(s.definition, rules(), checkpoint, e.state().history)
                  .exactReplayIdentity() == e.exactReplayIdentity(),
          "Actual naval air mission declaration replay differs");
  }
}
// RB 9.3.1: a patrol is an aircraft's whole combat move, into a sea zone
// within MAP range of the land zone or Carrier it takes off from.
void patrolsStartOnlyFromWhereAircraftTakeOff() {
  const auto patrols = [](Engine &e, const Id &zone) {
    const auto actions = e.legalActions();
    return std::any_of(actions.begin(), actions.end(), [&](const Action &a) {
      return a.kind == "air_start_patrol" &&
             a.parameters.require("path").asArray().back().asString() == zone;
    });
  };
  auto s = fixture();
  add(s, "fighter", "fighter", "japan", beiping);
  Engine landBased(s, rules());
  check(patrols(landBased, p14),
        "A Fighter could not patrol the sea zone next to its land zone");
  check(!patrols(landBased, "sea_p15") && !patrols(landBased, "sea_p32"),
        "A Fighter patrolled beyond its MAP range of one");
  choose(landBased, "air_fly", [](const Action &a) {
    const auto &path = a.parameters.require("path").asArray();
    return path.size() == 2 && path.back().asString() == p14;
  });
  check(!offered(landBased, "air_start_patrol"),
        "An aircraft started a patrol at the end of an ordinary flight");

  auto c = fixture();
  add(c, "carrier", "fleet_carrier", "japan", p16);
  add(c, "deck", "fighter", "japan", p16);
  attachCargo(c, "carrier", "deck");
  Engine carrierBased(c, rules());
  check(patrols(carrierBased, p16) && patrols(carrierBased, "sea_p15"),
        "A carrier Fighter could not patrol its Carrier's or the next sea zone");
  check(!patrols(carrierBased, p14) && !patrols(carrierBased, "sea_p32") &&
            !patrols(carrierBased, "sea_p33"),
        "A carrier Fighter patrolled two sea zones from its Carrier");
}
// RB 9.3.1: on patrol an aircraft attacks only Enemy naval units in its own sea
// zone, in its Combat Phase, and must end the patrol before any other use.
void patrollingAircraftAttackOnlyInTheirOwnSeaZone() {
  const auto patrol = [](State &s, const Id &zone) {
    add(s, "plane", "fighter", "japan", zone);
    auto &plane = s.units.at("plane");
    plane.gameFlags["on_map"] = 1;
    plane.gameFlags["map_range"] = 1;
    plane.turnFlags["on_map"] = 1;
    plane.commitments.insert("maritime_air_patrol");
  };
  for (const bool patrolling : {false, true}) {
    auto s = fixture();
    if (patrolling)
      patrol(s, "sea_p15");
    else
      add(s, "plane", "fighter", "japan", beiping);
    add(s, "ship", "destroyer", "kmt", p14);
    add(s, "docked", "destroyer", "kmt", shantung);
    s.units.at("docked").gameFlags["in_port:port"] = 1;
    s.facilities["port"] = {"port", "major_port", shantung, 0, {{"border:" + p14, 1}}};
    Engine e(s, rules());
    check(offered(e, "naval_air_attack") != patrolling &&
              offered(e, "naval_port_attack") != patrolling,
          patrolling ? "A patrolling aircraft attacked outside its own sea zone"
                     : "An aircraft at its base lost its naval air and port attacks");
  }
  auto s = fixture(Phase::Combat);
  patrol(s, "sea_p15");
  add(s, "ship", "destroyer", "kmt", "sea_p15");
  Engine e(s, rules());
  check(offered(e, "naval_patrol_attack"),
        "A patrol could not attack Enemy ships in its own sea zone");
}
} // namespace
int main() {
  try {
    for (const auto &[name, test] :
         std::vector<std::pair<std::string, std::function<void()>>>{
             {"uncontested assault and replay", uncontestedAssaultAndReplay},
             {"sea clearance", seaMustBeClearedBeforeAssault},
             {"waiting second wave", waitingArmorRemainsAboardUntilFoothold},
             {"shore and coastal fire", shoreBombardmentAndCoastalFirstStrike},
             {"berthing", berthLocksMovementAndKeepsCargo},
             {"port unload alternatives", portUnloadAlternativeNeedsOwnedCargo},
             {"capture and scuttle", capturedShipRollPreservesDamage},
             {"temporary ship crew", temporaryCrewAndSkeletonRestriction},
             {"amphibious double casualties",
              amphibiousDoubleCasualtiesAndExemptions},
             {"damaged port evacuation",
              damagedPortEvacuationSuspendsAndResumesBombing},
             {"third-party evacuation fleet",
              thirdPartyEvacuationUsesFleetRolesAndPreservesBombing},
             {"active enemy attacks evacuation",
              activeEnemyAttacksEvacuationAndSelectionMayStop},
             {"evacuation attack and defense values",
              evacuationUsesAttackAndDefenseValues},
             {"evacuating submarine defense",
              evacuatingSubmarineMakesDefendingChoicesAndSubmerges},
             {"evacuation defensive air scramble",
              evacuationScramblesOnlySupportTheDefendingFleet},
             {"multinational evacuation casualties",
              multinationalOutsideFleetUsesActualCasualtyPolicies},
             {"current-turn outside fleet retreat",
              currentTurnOutsideFleetMayRetreatToItsRealEntrySea},
             {"isolated evacuation declaration",
              mandatoryEvacuationDoesNotMergeOrdinaryNavalDeclarations},
             {"separate evacuation seas",
              separateEvacuationSeasResolveBeforeCalendarResumes},
             {"shared shore casualty consent",
              sharedShoreCasualtiesNeedBothPolicies},
             {"aircraft and submarine declarations",
              carrierAircraftAndProtectedSubmarinesAreNotAssaultTargets},
             {"port unload movement lock", portUnloadCannotBecomeRailOrAirMove},
             {"Japan-to-China reinforcement and landing",
              [] { japanToChinaVoyageAndLanding("clear"); }},
             {"contested reinforcement and landing",
              [] { japanToChinaVoyageAndLanding("contested"); }},
             {"contested reinforcement retreat",
              [] { japanToChinaVoyageAndLanding("retreat"); }},
             {"berthing after mandatory returns",
              berthWaitsForMandatoryLandingAndWithdrawal},
             {"combined overland/amphibious preparation and retreat",
              adjacentLandAndAmphibiousAttacksResolveTogether},
             {"actual naval air declaration",
              actualNavalAirDeclarationsKeepContextAndCombatPhase},
             {"patrol take-off range", patrolsStartOnlyFromWhereAircraftTakeOff},
             {"patrol attacks stay in their sea zone",
              patrollingAircraftAttackOnlyInTheirOwnSeaZone}}) {
      test();
      std::cout << "PASS " << name << '\n';
    }
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
