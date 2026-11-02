#include "game/air.hpp"
#include "game/catalog.hpp"
#include "game/economy.hpp"
#include "game/land_combat.hpp"
#include "game/movement.hpp"
#include "game/naval.hpp"
#include "game/politics.hpp"
#include <algorithm>
#include <functional>
#include <iostream>
#include <stdexcept>
using namespace game::campaign;
using V = game::json::Value;
using O = V::Object;
namespace {
const Id honshu = "land_jap_honshu", tokyo = "land_jap_tokyo", hopeh = "land_china_hopeh",
         beiping = "land_china_beiping", shantung = "land_china_shantung", nanking = "land_china_nanking";
void check(bool yes, const std::string &why) {
    if (!yes)
        throw std::runtime_error(why);
}
State fixture(Phase phase = Phase::CombatMovement) {
    static auto base =
        loadScenario(std::filesystem::path(GWRL_SOURCE_DIR) / "game_content/scenarios/japan_china_1936");
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
    s.territories.at(beiping).possessor = "japan";
    s.territories.at(hopeh).possessor = "kmt";
    s.territories.at(shantung).possessor = "japan";
    s.captureTurnStart();
    return s;
}
void add(State &s, const Id &id, const Id &type, const Id &owner, const Id &zone) {
    UnitState u;
    u.id = id;
    u.type = type;
    u.owner = owner;
    u.zone = u.turnOrigin = zone;
    u.movementAllowance = u.movementRemaining =
        s.definition->catalog->stats(type, 0, catalogContext(s, owner, zone)).movement;
    s.units[id] = u;
}
std::shared_ptr<const Rules> rules() {
    return std::make_shared<PoliticsRules>(std::make_shared<MovementRules>(
        std::make_shared<LandCombatRules>(std::make_shared<AirRules>(std::make_shared<EconomyRules>()))));
}
Action select(
    Engine &e, const Id &kind, std::function<bool(const Action &)> f = [](const Action &) { return true; }) {
    for (const auto &a : e.legalActions())
        if (a.kind == kind && f(a))
            return a;
    throw std::runtime_error("Missing action " + kind);
}
void choose(
    Engine &e, const Id &kind, std::function<bool(const Action &)> f = [](const Action &) { return true; }) {
    e.step(select(e, kind, f));
}
bool offered(Engine &e, const Id &kind) {
    auto a = e.legalActions();
    return std::any_of(a.begin(), a.end(), [&](const auto &x) { return x.kind == kind; });
}
void indexedGeometryPreservesAircraftMenus() {
    for(const auto phase:{Phase::CombatMovement,Phase::NonCombatMovement}) {
        auto state=fixture(phase);
        add(state,"test_fighter","fighter","japan",beiping);
        add(state,"test_bomber","tactical_bomber","japan",tokyo);
        add(state,"test_carrier","fleet_carrier","japan","sea_p15");
        add(state,"test_enemy","fighter","kmt",hopeh);
        state.captureTurnStart();
        const auto before=state.serialize();
        const auto fast=AirRules{}.actions(state);
        auto referenceDefinition=std::make_shared<Definition>(*state.definition);
        referenceDefinition->indexedGeography.reset();
        state.definition=referenceDefinition;
        const auto reference=AirRules{}.actions(state);
        check(fast.size()==reference.size(),"Indexed flight bound changed menu size");
        for(std::size_t i=0;i<fast.size();++i)
            check(canonicalJson(actionJson(fast[i]))==canonicalJson(actionJson(reference[i])),
                  "Indexed flight bound changed aircraft choices or order");
        check(state.serialize()==before,"Derived flight bound changed state or fingerprint");
    }
}
void resolveToLanding(Engine &e) {
    for (int n = 0; n < 100 && !e.state().battles.empty(); ++n) {
        if (e.state().chance) {
            e.resolveChance();
            continue;
        }
        auto opts = e.legalActions();
        check(!opts.empty(), "Air mission stuck");
        auto i = std::find_if(opts.begin(), opts.end(), [](const auto &a) {
            return a.kind == "air_decline_intercept" || a.kind == "air_decline_scramble" ||
                   a.kind == "air_ground" || a.kind == "air_land";
        });
        e.step(i == opts.end() ? opts.front() : *i);
    }
}
void flightPermissionAndRange() {
    auto s = fixture();
    add(s, "f", "fighter", "japan", beiping);
    check(validateFlight(s, "f", {beiping, hopeh}, true, true).allowed, "Enemy target flight blocked");
    add(s, "enemy", "fighter", "kmt", hopeh);
    check(!validateFlight(s, "f", {beiping, hopeh, shantung}, true, true).allowed,
          "Enemy fighter transit permitted");
    check(!validateFlight(s, "f", {beiping, "land_china_shensi"}, false).allowed,
          "Nonadjacent or neutral overflight permitted");
    s.units.at("f").movementRemaining = 0;
    check(!validateFlight(s, "f", {beiping, hopeh}, true, true).allowed, "Zero range flew");
}
void landingTimingAndCarrierCapacity() {
    auto s = fixture();
    add(s, "f", "fighter", "japan", beiping);
    check(airLandingAvailable(s, "f", beiping), "Held friendly land unavailable");
    s.territories.at(hopeh).possessor = "japan";
    s.territories.at(hopeh).flags["last_possession_change_turn"] = 2;
    check(!airLandingAvailable(s, "f", hopeh), "Newly captured landing allowed");
    add(s, "cv", "fleet_carrier", "japan", beiping);
    check(airLandingAvailable(s, "f", "cv"), "Carrier landing unavailable");
    add(s, "g", "fighter", "japan", beiping);
    add(s, "h", "fighter", "japan", beiping);
    attachCargo(s, "cv", "g");
    attachCargo(s, "cv", "h");
    check(!airLandingAvailable(s, "f", "cv"), "Full carrier accepted extra aircraft");
}
// Split flights exist only in Noncombat Movement; Combat Movement flights attack.
void ordinaryFlightsKeepALandingContinuation() {
    const Id formosa = "land_formosa", hainan = "land_hainan";
    auto s = fixture(Phase::NonCombatMovement);
    s.nations.at("japan").atWarWith.insert("warlord_kwangtung_hainan");
    s.nations.at("warlord_kwangtung_hainan").atWarWith.insert("japan");
    add(s, "b", "tactical_bomber", "japan", tokyo);
    s.units.at("b").movementAllowance = s.units.at("b").movementRemaining = 5;
    const std::vector<Id> stranded{tokyo, honshu, "sea_p15", "sea_p32", "sea_p41", hainan};
    check(validateFlight(s, "b", stranded, false).allowed,
          "Stranded-flight fixture did not pass ordinary path/range checks");
    Engine e(s, rules());
    for (const auto& action : e.legalActions())
        check(action.kind != "air_fly" || action.parameters.require("path").asArray().back().asString() != hainan,
              "A zero-fuel flight was offered onto unlandable Hainan");
    Action invalid;
    invalid.kind = "air_fly";
    V::Array path;
    for (const auto& zone : stranded) path.emplace_back(zone);
    invalid.parameters = V(O{{"unit", V("b")}, {"path", V(path)}});
    const auto before = canonicalJson(s.toJson());
    bool rejected = false;
    try { AirRules{}.apply(s, invalid); } catch (const std::runtime_error&) { rejected = true; }
    check(rejected && canonicalJson(s.toJson()) == before,
          "Authoritative flight application accepted or mutated a stranded flight");
    const auto initial = e.serialize();
    choose(e, "air_fly", [](const Action& action) {
        return action.parameters.require("path").asArray().back().asString() == "sea_p15";
    });
    check(e.state().units.at("b").turnFlags.at("air_in_flight") && !offered(e, "end_phase"),
          "A valid split flight was rejected or prematurely grounded");
    auto clone = e.clone();
    const auto landing = select(e, "air_land_noncombat", [&](const Action& action) {
        return action.parameters.require("destination").asString() == formosa;
    });
    e.step(landing); clone.step(landing);
    check(offered(e, "end_phase") && e.state().units.at("b").zone == formosa &&
              clone.exactReplayIdentity() == e.exactReplayIdentity(),
          "A split flight lost its later landing or clone identity");
    auto replay = Engine::replay(s.definition, rules(), initial, e.state().history);
    check(replay.exactReplayIdentity() == e.exactReplayIdentity(), "Split flight replay diverged");

    auto culdesac = fixture(Phase::NonCombatMovement);
    culdesac.nations.at("japan").atWarWith.insert("warlord_kwangtung_hainan");
    culdesac.nations.at("warlord_kwangtung_hainan").atWarWith.insert("japan");
    add(culdesac, "b", "strategic_bomber", "japan", tokyo);
    culdesac.units.at("b").movementAllowance = culdesac.units.at("b").movementRemaining = 6;
    Engine oneFuel(culdesac, rules());
    for (const auto& action : oneFuel.legalActions())
        check(action.kind != "air_fly" || action.parameters.require("path").asArray().back().asString() != hainan,
              "A one-fuel cul-de-sac flight had no reachable landing continuation");
    auto atSea = fixture(Phase::NonCombatMovement);
    add(atSea, "t", "air_transport", "japan", tokyo);
    atSea.units.at("t").movementAllowance = atSea.units.at("t").movementRemaining = 3;
    Engine noCarrier(atSea, rules());
    for (const auto& action : noCarrier.legalActions())
        check(action.kind != "air_fly" || action.parameters.require("path").asArray().back().asString() != "sea_p32",
              "A zero-fuel transport was offered a sea destination with no landing carrier or MAP option");
}
void flightMayPrecedeItsLandingCarrier() {
    const Id formosa = "land_formosa", landingSea = "sea_p41";
    auto s = fixture(Phase::NonCombatMovement);
    add(s, "f", "fighter", "japan", formosa);
    s.units.at("f").movementAllowance = s.units.at("f").movementRemaining = 1;
    add(s, "cv", "fleet_carrier", "japan", "sea_p15");
    s.captureTurnStart();
    auto gameplay = std::make_shared<NavalRules>(rules());
    auto fly = [&](Engine& engine) {
        choose(engine, "air_fly", [&](const Action& action) {
            return action.parameters.require("unit").asString() == "f" &&
                   action.parameters.require("path").asArray().back().asString() == landingSea;
        });
    };
    auto sail = [&](Engine& engine) {
        choose(engine, "naval_start_move", [](const Action& action) {
            return action.parameters.require("unit").asString() == "cv";
        });
        choose(engine, "naval_route", [&](const Action& action) {
            return action.parameters.require("request").require("path").asArray().back().asString() == landingSea;
        });
    };
    auto landOnCarrier = [&](Engine& engine) {
        choose(engine, "air_land_noncombat", [](const Action& action) {
            return action.parameters.require("destination").asString() == "cv";
        });
    };
    Engine airFirst(s, gameplay);
    const auto initial = airFirst.serialize();
    fly(airFirst);
    check(airFirst.state().units.at("f").movementRemaining == 0 &&
              !airLandingPlanAvailable(airFirst.state()) && !offered(airFirst, "end_phase"),
          "Future-carrier fixture did not require an actual later ship move");
    sail(airFirst); landOnCarrier(airFirst);
    check(offered(airFirst, "end_phase") && airFirst.state().units.at("f").carriedBy == "cv",
          "An aircraft-first/carrier-later sequence lost its legal landing");
    Engine carrierFirst(s, gameplay);
    sail(carrierFirst); fly(carrierFirst); landOnCarrier(carrierFirst);
    check(carrierFirst.state().units.at("f").zone == airFirst.state().units.at("f").zone &&
              carrierFirst.state().units.at("f").carriedBy == airFirst.state().units.at("f").carriedBy,
          "Changing flight/carrier ordering changed the final landing choice");
    auto replay = Engine::replay(s.definition, gameplay, initial, airFirst.state().history);
    check(replay.exactReplayIdentity() == airFirst.exactReplayIdentity(),
          "Future-carrier landing replay diverged");
}
void bombingDamageThenAAAndReplay() {
    auto s = fixture();
    add(s, "b", "medium_bomber", "japan", beiping);
    s.facilities["factory"] = {"factory", "major_factory", hopeh, 0, {}};
    Engine e(s, rules(), 4);
    e.setDiceTapeForTesting({6, 1});
    auto checkpoint = e.serialize();
    choose(e, "air_bomb",
           [](const auto &a) { return a.parameters.require("target").asString() == "factory"; });
    choose(e, "end_phase");
    choose(e, "air_begin_bombing");
    check(e.state().chance->purpose == "air_bomb_damage", "Damage not first");
    e.resolveChance();
    check(e.state().facilities.at("factory").damage == 6, "Strategic damage missing");
    check(e.state().chance->purpose == "air_facility_aa", "Facility AA omitted");
    e.resolveChance();
    choose(e, "air_choose_casualty");
    check(!e.state().units.contains("b") && e.state().battles.empty(), "Destroyed bomber not removed");
    auto replay = Engine::replay(s.definition, rules(), checkpoint, e.state().history);
    check(replay.exactReplayIdentity() == e.exactReplayIdentity(), "Bombing replay diverged");
}
void interceptorAndEscortSimultaneous() {
    auto s = fixture();
    add(s, "b", "medium_bomber", "japan", beiping);
    add(s, "escort", "fighter", "japan", beiping);
    add(s, "i", "fighter", "kmt", hopeh);
    s.facilities["factory"] = {"factory", "major_factory", hopeh, 0, {}};
    Engine e(s, rules());
    choose(e, "air_bomb",
           [](const auto &a) { return a.parameters.require("target").asString() == "factory"; });
    choose(e, "air_escort");
    choose(e, "end_phase");
    choose(e, "air_begin_bombing");
    choose(e, "air_intercept");
    check(e.state().chance->purpose == "air_interception_roll" && e.state().chance->dice.size() == 3,
          "Bombers, escorts, interceptors must all fire");
    auto restored = Engine::restore(s.definition, rules(), e.serialize());
    check(restored.planningKey() == e.planningKey(), "Interception continuation lost");
}
void railroadSideAndAllTracks() {
    auto s = fixture();
    s.rails.clear();
    s.rails["r"] = {"r", hopeh, beiping, {}};
    s.rails["second"] = {"second", beiping, hopeh, {}};
    applyRailBombDamage(s, hopeh, beiping, 6);
    check(s.rails.at("r").damageByEndpoint.at(hopeh) == 1 &&
              s.rails.at("second").damageByEndpoint.at(hopeh) == 1,
          "Rail cap/all tracks wrong");
    check(!s.rails.at("r").damageByEndpoint.contains(beiping), "Bombing damaged opposite side");
    applyRailBombDamage(s, beiping, hopeh, 1);
    check(s.rails.at("r").damageByEndpoint.at(beiping) == 1, "Opposite side independent damage lost");
}
void cityPermanentIPPAndDestruction() {
    auto s = fixture();
    s.territories.at(nanking).possessor = "kmt";
    applyCityBombDamage(s, nanking, 20);
    check(effectiveTerritorialIpp(s, nanking) == 1, "City IPP not reduced");
    s.territories.at(nanking).flags["city_damage"] = 0;
    check(effectiveTerritorialIpp(s, nanking) == 1, "Repair restored permanently destroyed IPP");
    applyCityBombDamage(s, nanking, 100);
    check(s.territories.at(nanking).flags.at("city_destroyed") == 1 &&
              s.territories.at(nanking).flags.at("city_damage") == 45,
          "Ordinary city cap wrong");
}
void improvedConstructionPerPlayerTurn() {
    auto s = fixture();
    s.nations.at("kmt").technologyStages["improved_construction"] = 4;
    s.facilities["factory"] = {"factory", "major_factory", hopeh, 0, {}};
    applyFacilityBombDamage(s, "factory", 4);
    applyFacilityBombDamage(s, "factory", 4);
    check(s.facilities.at("factory").damage == 3, "Factory mitigation stacked across missions");
    ++s.clock.playerTurnSerial;
    applyFacilityBombDamage(s, "factory", 4);
    check(s.facilities.at("factory").damage == 3, "Mitigation failed to reset on next player turn");
}
void airliftHeavyCapacityAndContinuation() {
    auto s = fixture(Phase::NonCombatMovement);
    add(s, "t", "heavy_air_transport", "japan", beiping);
    add(s, "a", "artillery", "japan", beiping);
    add(s, "i", "infantry", "japan", beiping);
    Engine e(s, rules());
    choose(e, "air_load", [](const auto &a) { return a.parameters.require("cargo").asString() == "a"; });
    check(!offered(e, "air_load"), "Heavy air transport took multiple noncombat units");
    choose(e, "air_fly", [](const auto &a) {
        return a.parameters.require("path").asArray().back().asString() == shantung;
    });
    choose(e, "air_unload");
    check(e.state().units.at("a").zone == shantung && e.state().units.at("a").movementRemaining == 0,
          "Airlift cargo moved after unloading");
    check(e.state().units.at("t").movementRemaining.value() > 0 && offered(e, "air_fly"),
          "Transport cannot continue after unloading");
}
void failedLanding() {
    // Combat Movement too: a flight that waited for a Carrier that never came
    // cannot be rescued by a patrol, because a patrol cannot follow a flight.
    for (const auto phase : {Phase::NonCombatMovement, Phase::CombatMovement}) {
        auto s = fixture(phase);
        add(s, "f", "fighter", "japan", phase == Phase::NonCombatMovement ? hopeh : "sea_p14");
        s.units.at("f").movementRemaining = 0;
        s.units.at("f").turnFlags["air_in_flight"] = 1;
        Engine e(s, rules());
        check(!offered(e, "end_phase") && !offered(e, "air_start_patrol"), "Stranded plane let phase complete");
        choose(e, "air_failed_landing");
        check(!e.state().units.contains("f"), "Stranded aircraft survived");
    }
}
void strandedAttackersStillEndCombatMovement() {
    // Moves never leave more aircraft without a landing, so only dice or another
    // nation's turn strand an attacker; this fixture does it by editing the
    // bomber's fuel. Its owner gives it up while other moves stay open, and the
    // phase then ends; the battle it was to fight ends for the defender.
    auto s = fixture();
    add(s, "bomber", "tactical_bomber", "japan", beiping);
    add(s, "defender", "infantry", "kmt", hopeh);
    s.captureTurnStart();
    Engine attack(s, rules());
    choose(attack, "air_ground_attack", [](const Action &a) {
        return a.parameters.require("path").asArray().back().asString() == hopeh;
    });
    auto stranded = attack.state().clone();
    stranded.units.at("bomber").movementRemaining = 0;
    auto busy = stranded.clone();
    add(busy, "spare", "infantry", "japan", shantung);
    Engine waiting(busy, rules());
    check(!offered(waiting, "end_phase") && offered(waiting, "air_failed_landing") && waiting.legalActions().size() > 2,
          "A stranded attacker could not be given up, or Combat Movement ended with it still flying");
    Engine e(stranded, rules());
    const auto menu = e.legalActions();
    check(menu.size() == 1 && menu.front().kind == "air_failed_landing", "The stranded attacker could not be given up");
    e.step(menu.front());
    check(!e.state().units.contains("bomber") && offered(e, "end_phase") && !e.state().flags.contains("stranded_aircraft_lost"),
          "Giving up the stranded attacker did not let Combat Movement end");
    choose(e, "end_phase");
    check(e.state().clock.phase == Phase::Combat, "Combat Movement did not end after the attacker was given up");
    for (int step = 0; step < 8 && !offered(e, "end_phase"); ++step)
        if (e.state().chance) e.resolveChance();
        else e.step(e.legalActions().front());
    check(offered(e, "end_phase") && e.state().units.contains("defender"),
          "Battle that lost its only attacker did not end for the defender");
}
void noAircraftCapture() {
    auto s = fixture();
    add(s, "f", "fighter", "japan", hopeh);
    check(s.territories.at(hopeh).possessor == "kmt", "Fixture owner");
    Engine e(s, rules());
    check(!offered(e, "movement_route"), "Aircraft got ordinary land capture route");
}
} // namespace
std::vector<Id> unitOrders(Engine &e, const Id &unit) {
    std::vector<Id> kinds;
    for (const auto &a : e.legalActions())
        if (const auto *p = a.parameters.find("unit"); p && p->asString() == unit)
            kinds.push_back(a.kind);
    return kinds;
}
bool hasOrder(Engine &e, const Id &unit, const Id &kind) {
    const auto kinds = unitOrders(e, unit);
    return std::find(kinds.begin(), kinds.end(), kind) != kinds.end();
}
void toNoncombat(Engine &e) {
    for (int guard = 0; guard < 8 && e.state().clock.phase != Phase::NonCombatMovement; ++guard)
        choose(e, "end_phase");
    check(e.state().clock.phase == Phase::NonCombatMovement, "Fixture did not reach Noncombat Movement");
}
bool refused(const State &source, const Action &action) {
    auto state = source.clone();
    const auto before = canonicalJson(state.toJson());
    try { AirRules{}.apply(state, action); } catch (const std::runtime_error &) {
        return canonicalJson(state.toJson()) == before;
    }
    return false;
}
Action flight(const Id &unit, const std::vector<Id> &path) {
    Action a;
    a.kind = "air_fly";
    V::Array zones;
    for (const auto &zone : path) zones.emplace_back(zone);
    a.parameters = V(O{{"unit", V(unit)}, {"path", V(zones)}});
    return a;
}
// RB 9.1 and 11.1: a Combat Movement flight attacks or patrols, and a plane
// that moved then makes no Noncombat move.
void combatMovementFlightIsTheTurnsMove() {
    auto s = fixture();
    for (const auto &id : {"idle", "patrol"}) {
        add(s, id, "fighter", "japan", tokyo);
        s.units.at(id).movementAllowance = s.units.at(id).movementRemaining = 5;
    }
    add(s, "deck", "fighter", "japan", "sea_p16");
    s.units.at("deck").movementAllowance = s.units.at("deck").movementRemaining = 5;
    add(s, "cv", "fleet_carrier", "japan", "sea_p16");
    add(s, "cv2", "fleet_carrier", "japan", "sea_p16");
    attachCargo(s, "cv", "deck");
    s.captureTurnStart();
    Engine e(s, std::make_shared<NavalRules>(rules()));
    check(!hasOrder(e, "idle", "air_fly") && hasOrder(e, "idle", "air_ground_attack"),
          "Combat Movement offered a fighter a flight that starts no combat, or no attack");
    check(refused(e.state(), flight("idle", {tokyo, honshu})), "A Combat Movement flight that starts no combat was applied");
    choose(e, "air_start_patrol", [](const Action &a) { return a.parameters.require("unit").asString() == "patrol"; });
    // A carrier that sails leaves its aircraft in the air over its starting zone;
    // the fighter lands on the other carrier there, still in Combat Movement.
    choose(e, "naval_start_move", [](const Action &a) { return a.parameters.require("unit").asString() == "cv"; });
    choose(e, "naval_route", [](const Action &a) {
        return a.parameters.require("request").require("path").asArray().back().asString() == "sea_p15";
    });
    check(e.state().units.at("deck").turnFlags.contains("air_in_flight") && !hasOrder(e, "deck", "air_fly"),
          "A sailing carrier carried its fighter along, or the fighter got a flight that starts no combat");
    choose(e, "air_land_noncombat", [](const Action &a) {
        return a.parameters.require("unit").asString() == "deck" &&
               a.parameters.require("destination").asString() == "cv2";
    });
    toNoncombat(e);
    check(hasOrder(e, "idle", "air_fly") && hasOrder(e, "idle", "air_land_noncombat"),
          "An aircraft that did not move in Combat Movement lost its Noncombat move");
    check(hasOrder(e, "patrol", "air_end_patrol"), "A patrol could not end in Noncombat Movement");
    check(unitOrders(e, "deck").empty(), "An aircraft that moved in Combat Movement moved again");
    check(refused(e.state(), flight("deck", {"sea_p16", "sea_p15"})), "A second flight was applied after Combat Movement");
    // When its carrier sails in Noncombat Movement, the aircraft may only land.
    choose(e, "naval_start_move", [](const Action &a) { return a.parameters.require("unit").asString() == "cv2"; });
    choose(e, "naval_route", [](const Action &a) {
        return a.parameters.require("request").require("path").asArray().back().asString() == "sea_p15";
    });
    const auto orders = unitOrders(e, "deck");
    check(e.state().units.at("deck").turnFlags.contains("air_in_flight") && !orders.empty() &&
              std::all_of(orders.begin(), orders.end(), [](const Id &kind) {
                  return kind == "air_land_noncombat" || kind == "air_failed_landing";
              }),
          "An aircraft its carrier left in the air could do more than land");
    choose(e, "air_land_noncombat", [](const Action &a) {
        return a.parameters.require("unit").asString() == "deck" &&
               a.parameters.require("destination").asString() == "cv2";
    });
    check(e.state().units.at("deck").carriedBy == "cv2" && unitOrders(e, "deck").empty(),
          "The launched aircraft did not land back on its carrier");
}
// RB 9.3.2: an air transport may stop on its way to collect airborne infantry.
void combatMovementStopsOnlyToCollectAirborneInfantry() {
    auto s = fixture();
    add(s, "lift", "air_transport", "japan", tokyo);
    add(s, "para", "airborne_infantry", "japan", honshu);
    s.captureTurnStart();
    Engine e(s, rules());
    std::vector<Id> stops;
    for (const auto &a : e.legalActions())
        if (a.kind == "air_fly" && a.parameters.require("unit").asString() == "lift")
            stops.push_back(a.parameters.require("path").asArray().back().asString());
    check(stops == std::vector<Id>{honshu}, "An air transport's Combat Movement stop went elsewhere than its paratroopers");
    choose(e, "air_fly", [](const Action &a) { return a.parameters.require("unit").asString() == "lift"; });
    choose(e, "air_load", [](const Action &a) {
        return a.parameters.require("unit").asString() == "lift" && a.parameters.require("cargo").asString() == "para";
    });
    check(e.state().units.at("para").carriedBy == "lift", "The air transport did not collect its airborne infantry");
}
// An allied transport keeps the marks of its owner's own turn; boarding it
// during another player's Noncombat Movement does not move it.
void alliedTransportBoardsAfterItsOwnersTurn() {
    auto s = fixture(Phase::NonCombatMovement);
    s.clock.nationIndex = 3;  // KMT, after CCP, Mongolia and Japan
    s.clock.playerTurnSerial = 3;
    s.completedTurns["japan"] = 1;
    s.politics.chineseTruce = true;
    add(s, "lift", "air_transport", "ccp", hopeh);
    s.units.at("lift").commitments.insert("combat_move");  // From CCP's own Combat Movement.
    add(s, "infantry", "infantry", "kmt", hopeh);
    s.captureTurnStart();
    Engine e(s, rules());
    choose(e, "air_allied_load", [](const Action &a) {
        return a.parameters.require("unit").asString() == "lift" &&
               a.parameters.require("cargo").asString() == "infantry";
    });
    check(e.state().units.at("infantry").carriedBy == "lift", "An ally could not board a transport that flew on its own turn");
}
void aRaidOnAVanishedProjectDoesNothing() {
    // Capturing the zone or an earlier raid may remove the targeted project
    // before the damage roll (seed 8215 of the 2 November random games).
    auto s = fixture();
    add(s, "b", "medium_bomber", "japan", beiping);
    s.construction["project"] = BuildProject{"project", "kmt", "medium_factory", hopeh, 1, 3, {3}};
    Engine e(s, rules(), 4);
    choose(e, "air_bomb",
           [](const auto &a) { return a.parameters.require("target").asString() == "project"; });
    choose(e, "end_phase");
    choose(e, "air_begin_bombing");
    check(e.state().chance && e.state().chance->purpose == "air_bomb_damage", "Construction raid rolled no damage");
    auto vanished = e.state().clone();
    vanished.construction.erase("project");
    Engine after(vanished, rules(), 4);
    after.setDiceTapeForTesting({6});
    after.resolveChance();
    check(!after.state().chance || after.state().chance->purpose != "air_bomb_damage",
          "A raid on a removed project did not move on");
    check(after.state().units.contains("b"), "The raid lost its bomber");
}
int main() {
    try {
        flightPermissionAndRange();
        landingTimingAndCarrierCapacity();
        ordinaryFlightsKeepALandingContinuation();
        flightMayPrecedeItsLandingCarrier();
        bombingDamageThenAAAndReplay();
        interceptorAndEscortSimultaneous();
        railroadSideAndAllTracks();
        cityPermanentIPPAndDestruction();
        improvedConstructionPerPlayerTurn();
        airliftHeavyCapacityAndContinuation();
        failedLanding();
        strandedAttackersStillEndCombatMovement();
        noAircraftCapture();
        indexedGeometryPreservesAircraftMenus();
        combatMovementFlightIsTheTurnsMove();
        combatMovementStopsOnlyToCollectAirborneInfantry();
        alliedTransportBoardsAfterItsOwnersTurn();
        aRaidOnAVanishedProjectDoesNothing();
        std::cout << "18 air fixture groups passed\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
