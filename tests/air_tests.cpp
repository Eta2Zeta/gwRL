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
void ordinaryFlightsKeepALandingContinuation() {
    const Id formosa = "land_formosa", hainan = "land_hainan";
    auto s = fixture();
    s.nations.at("japan").atWarWith.insert("warlord_kwangtung_hainan");
    s.nations.at("warlord_kwangtung_hainan").atWarWith.insert("japan");
    add(s, "b", "tactical_bomber", "japan", tokyo);
    s.units.at("b").movementAllowance = s.units.at("b").movementRemaining = 5;
    const std::vector<Id> stranded{tokyo, honshu, "sea_p15", "sea_p32", "sea_p41", hainan};
    check(validateFlight(s, "b", stranded, true).allowed,
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

    auto culdesac = fixture();
    culdesac.nations.at("japan").atWarWith.insert("warlord_kwangtung_hainan");
    culdesac.nations.at("warlord_kwangtung_hainan").atWarWith.insert("japan");
    add(culdesac, "b", "strategic_bomber", "japan", tokyo);
    culdesac.units.at("b").movementAllowance = culdesac.units.at("b").movementRemaining = 6;
    Engine oneFuel(culdesac, rules());
    for (const auto& action : oneFuel.legalActions())
        check(action.kind != "air_fly" || action.parameters.require("path").asArray().back().asString() != hainan,
              "A one-fuel cul-de-sac flight had no reachable landing continuation");
    auto atSea = fixture();
    add(atSea, "t", "air_transport", "japan", tokyo);
    atSea.units.at("t").movementAllowance = atSea.units.at("t").movementRemaining = 3;
    Engine noCarrier(atSea, rules());
    for (const auto& action : noCarrier.legalActions())
        check(action.kind != "air_fly" || action.parameters.require("path").asArray().back().asString() != "sea_p32",
              "A zero-fuel transport was offered a sea destination with no landing carrier or MAP option");
}
void flightMayPrecedeItsLandingCarrier() {
    const Id formosa = "land_formosa", landingSea = "sea_p41";
    auto s = fixture();
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
    auto s = fixture(Phase::NonCombatMovement);
    add(s, "f", "fighter", "japan", hopeh);
    s.units.at("f").movementRemaining = 0;
    s.units.at("f").turnFlags["air_in_flight"] = 1;
    Engine e(s, rules());
    check(!offered(e, "end_phase"), "Stranded plane let phase complete");
    choose(e, "air_failed_landing");
    check(!e.state().units.contains("f"), "Stranded aircraft survived");
}
void noAircraftCapture() {
    auto s = fixture();
    add(s, "f", "fighter", "japan", hopeh);
    check(s.territories.at(hopeh).possessor == "kmt", "Fixture owner");
    Engine e(s, rules());
    check(!offered(e, "movement_route"), "Aircraft got ordinary land capture route");
}
} // namespace
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
        noAircraftCapture();
        indexedGeometryPreservesAircraftMenus();
        std::cout << "13 air fixture groups passed\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
