#include "game/air.hpp"
#include "game/catalog.hpp"
#include "game/economy.hpp"
#include "game/land_combat.hpp"
#include "game/movement.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <functional>
#include <iostream>
#include <stdexcept>

namespace {
using namespace game::campaign;
using V = game::json::Value;
using O = V::Object;
const Id beiping = "land_china_beiping", hopeh = "land_china_hopeh", tokyo = "land_jap_tokyo";
void check(bool condition, const std::string &message) {
    if (!condition)
        throw std::runtime_error(message);
}
void rejects(const std::function<void()> &operation, const std::string &message) {
    try {
        operation();
    } catch (const std::exception &) {
        return;
    }
    throw std::runtime_error(message);
}
State fixture(Phase phase = Phase::CombatMovement) {
    static const auto base =
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
    s.units.emplace(id, std::move(u));
}
std::shared_ptr<const Rules> rules() {
    return std::make_shared<PoliticsRules>(std::make_shared<MovementRules>(
        std::make_shared<LandCombatRules>(std::make_shared<AirRules>(std::make_shared<EconomyRules>()))));
}
Action select(
    Engine &e, const Id &kind,
    const std::function<bool(const Action &)> &predicate = [](const Action &) { return true; }) {
    for (const auto &a : e.legalActions())
        if (a.kind == kind && predicate(a))
            return a;
    throw std::runtime_error("Missing action " + kind);
}
void makeCity(State &s, const Id &zone) {
    auto d = *s.definition;
    auto geography = d.geography.asObject();
    auto nodes = geography.at("nodes").asObject();
    auto n = nodes.at(zone).asObject();
    n["is_city"] = V(true);
    nodes[zone] = V(n);
    geography["nodes"] = V(nodes);
    d.geography = V(geography);
    s.definition = freezeDefinition(std::move(d));
}
void actualAirborneEntryFacesCityAAAndReplays() {
    auto s = fixture();
    makeCity(s, hopeh);
    add(s, "transport", "air_transport", "japan", beiping);
    add(s, "paratrooper", "airborne_infantry", "japan", beiping);
    add(s, "defender", "militia", "kmt", hopeh);
    Engine e(s, rules(), 42);
    e.setDiceTapeForTesting({1});
    const auto checkpoint = e.serialize();
    e.step(select(e, "air_load",
                  [](const Action &a) { return a.parameters.require("cargo").asString() == "paratrooper"; }));
    e.step(select(e, "air_assault", [](const Action &a) {
        return a.parameters.require("path").asArray().back().asString() == hopeh;
    }));
    e.step(select(e, "end_phase"));
    e.step(select(e, "land_begin_battle"));
    check(e.state().chance && e.state().chance->purpose == "land_combat_roll" &&
              e.state().chance->dice.size() == 1,
          "Actual airborne entry skipped inherent city AA");
    const auto &battle = e.state().battles.begin()->second;
    check(battle.data.require("rolling_phase").asString() == "city_airborne_aaa",
          "City AA did not fire before first strike");
    e.resolveChance();
    e.step(select(e, "land_take_casualty",
                  [](const Action &a) { return a.parameters.require("unit").asString() == "transport"; }));
    check(!e.state().units.contains("transport") && !e.state().units.contains("paratrooper"),
          "City AA transport casualty landed cargo or let it attack");
    check(e.state().territories.at(hopeh).possessor == "kmt", "Failed assault captured the city");
    auto replayed = Engine::replay(s.definition, rules(), checkpoint, e.state().history);
    check(replayed.exactReplayIdentity() == e.exactReplayIdentity(), "Actual airborne entry replay diverged");
}
void actualAirborneEntryResolvesFightersAndAaaBeforeLanding() {
    auto s = fixture();
    add(s, "transport", "air_transport", "japan", beiping);
    add(s, "paratrooper", "airborne_infantry", "japan", beiping);
    add(s, "escort", "fighter", "japan", beiping);
    add(s, "defending_aaa", "anti_aircraft_artillery", "kmt", hopeh);
    add(s, "defending_fighter", "fighter", "kmt", hopeh);
    add(s, "defender", "militia", "kmt", hopeh);
    Engine e(s, rules(), 42);
    e.setDiceTapeForTesting({1, 1, 12, 1});
    const auto checkpoint = e.serialize();
    e.step(select(e, "air_load", [](const Action &a) {
        return a.parameters.require("cargo").asString() == "paratrooper";
    }));
    e.step(select(e, "air_assault", [](const Action &a) {
        return a.parameters.require("path").asArray().back().asString() == hopeh;
    }));
    e.step(select(e, "air_support", [](const Action &a) {
        return a.parameters.require("unit").asString() == "escort" &&
               a.parameters.require("path").asArray().back().asString() == hopeh;
    }));
    e.step(select(e, "end_phase"));
    e.step(select(e, "land_begin_battle"));
    e.step(select(e, "air_defend"));
    e.step(select(e, "land_progress_battle"));
    const auto battle = e.state().battleOrder.front();
    check(e.state().chance && e.state().chance->dice.size() == 4 &&
              e.state().battles.at(battle).data.require("rolling_phase").asString() == "air_fire" &&
              e.state().units.at("paratrooper").carriedBy == "transport",
          "Actual airborne entry split defender AAA from Fighters or landed before step 4");
    e.resolveChance();
    for (const auto &unit : {"defending_fighter", "transport", "escort"})
        e.step(select(e, "land_take_casualty", [&](const Action &a) {
            return a.parameters.require("unit").asString() == unit;
        }));
    check(!e.state().units.contains("transport") && !e.state().units.contains("paratrooper") &&
              !e.state().units.contains("escort") && !e.state().units.contains("defending_fighter") &&
              !e.state().chance && e.state().decisions.empty() &&
              e.state().battles.at(battle).flags.at("finished") &&
              e.state().territories.at(hopeh).possessor == "kmt",
          "Step-4 losses landed, lost simultaneous return fire, or prolonged an eliminated assault");
    auto replay = Engine::replay(s.definition, rules(), checkpoint, e.state().history);
    check(replay.exactReplayIdentity() == e.exactReplayIdentity(), "Actual airborne step-4 entry replay diverged");
}
void regularInfantryCannotBecomeAirborneByStayingLoaded() {
    auto s = fixture();
    add(s, "transport", "air_transport", "japan", beiping);
    add(s, "regular", "infantry", "japan", beiping);
    attachCargo(s, "transport", "regular");
    Engine e(s, rules());
    const auto options = e.legalActions();
    check(
        std::none_of(options.begin(), options.end(), [](const Action &a) { return a.kind == "air_assault"; }),
        "Regular Infantry retained aboard a transport became airborne infantry");
}
void controlledMinorsRetainSeparateAttackingForces() {
    auto s = fixture();
    ensureDadao(s);
    add(s, "japanese", "infantry", "japan", hopeh);
    add(s, "dadao", "infantry", "dadao", hopeh);
    rejects(
        [&] {
            registerLandBattle(s, hopeh, "japan", {"japanese", "dadao"},
                               {{"japanese", beiping}, {"dadao", beiping}});
        },
        "Controlling Japan and Dadao combined an attack");
    registerLandBattle(s, hopeh, "dadao", {"dadao"}, {{"dadao", beiping}});
    check(s.battles.size() == 1 && s.battles.begin()->second.attacker == "dadao",
          "Separate Dadao attack lost its identity");
}
void aircraftLaunchesFromCarrierAndReplaysCargoLinks() {
    auto s = fixture(Phase::NonCombatMovement);
    add(s, "carrier", "fleet_carrier", "japan", "sea_p16");
    add(s, "fighter", "fighter", "japan", "sea_p16");
    attachCargo(s, "carrier", "fighter");
    Engine e(s, rules(), 7);
    const auto checkpoint = e.serialize();
    e.step(select(e, "air_fly", [](const Action &a) {
        return a.parameters.require("unit").asString() == "fighter" &&
               a.parameters.require("path").asArray().back().asString() == tokyo;
    }));
    check(!e.state().units.at("fighter").carriedBy && e.state().units.at("carrier").cargo.empty(),
          "Launched fighter remained attached to its carrier");
    check(e.state().units.at("fighter").zone == tokyo && e.state().units.at("fighter").movementRemaining == 3,
          "Carrier launch lost origin or charged incorrect movement");
    e.step(select(e, "air_land_noncombat", [](const Action &a) {
        return a.parameters.require("unit").asString() == "fighter" &&
               a.parameters.require("destination").asString() == tokyo;
    }));
    auto replayed = Engine::replay(s.definition, rules(), checkpoint, e.state().history);
    check(replayed.exactReplayIdentity() == e.exactReplayIdentity(),
          "Carrier launch replay changed cargo links");
}
void finishScreening(Engine& e, const Id& battle) {
    for(int step=0;step<80;++step) {
        if(e.state().chance){e.resolveChance();continue;}
        if(e.state().decisions.empty()&&e.state().battles.at(battle).flags.contains("finished"))return;
        const auto actions=e.legalActions();
        const auto a=std::find_if(actions.begin(),actions.end(),[](const Action& x){return
            x.kind=="air_defend"||x.kind=="land_take_casualty"||x.kind=="land_progress_battle"||x.kind=="air_land";});
        check(a!=actions.end(),"Air screening continuation lost its battle action");e.step(*a);
    }
    throw std::runtime_error("Air screening battle did not finish");
}
void successfulAirScreeningContinuesToAnotherAttackAndReplays() {
    auto s=fixture();add(s,"screen","fighter","japan",beiping);add(s,"continuing","medium_bomber","japan",beiping);
    add(s,"defender","fighter","kmt",hopeh);s.captureTurnStart();
    Engine e(s,rules(),19);e.setDiceTapeForTesting({1,12,2,12});const auto checkpoint=e.serialize();
    e.step(select(e,"air_ground_attack",[](const Action& a){return a.parameters.require("unit").asString()=="screen"&&
        a.parameters.require("path").asArray().back().asString()==hopeh;}));
    const auto screenBattle=e.state().battleOrder.front();
    e.step(select(e,"air_screen_continue",[](const Action& a){return a.parameters.require("unit").asString()=="continuing";}));
    check(e.state().battles.at(screenBattle).attackers==std::vector<Id>{"screen"}&&
          e.state().units.at("continuing").turnFlags.at("air_screening_wait")==1,
          "Continuing aircraft fired in the screening battle");
    e.step(select(e,"end_phase"));e.step(select(e,"land_begin_battle"));finishScreening(e,screenBattle);
    check(!e.state().units.contains("defender")&&e.state().units.at("continuing").turnFlags.at("air_screening_ready")==1,
          "Successful fighter screening did not release the continuing aircraft");
    const auto restored=Engine::restore(s.definition,rules(),e.serialize());
    check(restored.planningKey()==e.planningKey(),"Successful air screening continuation was not serialized");
    e.step(select(e,"land_progress_battle"));
    e.step(select(e,"air_bomb",[](const Action& a){return a.parameters.require("unit").asString()=="continuing"&&
        a.parameters.require("kind").asString()=="city"&&a.parameters.require("target").asString()=="land_china_nanking";}));
    check(e.state().clock.phase==Phase::Combat,"Continuing aircraft introduced a new movement phase");
    e.step(select(e,"air_begin_bombing"));e.resolveChance();e.resolveChance();e.step(select(e,"air_land"));
    check(e.state().territories.at("land_china_nanking").flags.at("city_damage")==2&&e.state().battles.empty(),
          "Continuing bomber did not complete its subsequent city bombing");
    auto replay=Engine::replay(s.definition,rules(),checkpoint,e.state().history);
    check(replay.exactReplayIdentity()==e.exactReplayIdentity(),"Screening→continuing attack replay diverged");
}
void failedAirScreeningForcesTheContinuingAircraftToLand() {
    auto s=fixture();add(s,"screen","fighter","japan",beiping);add(s,"continuing","medium_bomber","japan",beiping);
    add(s,"defender","fighter","kmt",hopeh);s.captureTurnStart();
    Engine e(s,rules());e.setDiceTapeForTesting({12,1});
    e.step(select(e,"air_ground_attack",[](const Action& a){return a.parameters.require("unit").asString()=="screen"&&
        a.parameters.require("path").asArray().back().asString()==hopeh;}));const auto battle=e.state().battleOrder.front();
    e.step(select(e,"air_screen_continue",[](const Action& a){return a.parameters.require("unit").asString()=="continuing";}));
    e.step(select(e,"end_phase"));e.step(select(e,"land_begin_battle"));finishScreening(e,battle);
    check(!e.state().units.contains("screen")&&e.state().units.contains("defender")&&
          !e.state().units.at("continuing").turnFlags.contains("air_screening_ready")&&
          !e.state().units.at("continuing").turnFlags.contains("air_in_flight")&&
          e.state().units.at("continuing").zone!=hopeh,"Failed screening let continuing aircraft attack through enemy fighters");
}
void continuingAircraftCannotPerformAnAirborneAssault() {
    auto s=fixture();add(s,"screen","fighter","japan",beiping);add(s,"transport","air_transport","japan",beiping);
    add(s,"para","airborne_infantry","japan",beiping);attachCargo(s,"transport","para");
    add(s,"defender","fighter","kmt",hopeh);s.captureTurnStart();
    Engine e(s,rules());e.setDiceTapeForTesting({1,12});
    e.step(select(e,"air_ground_attack",[](const Action& a){return a.parameters.require("unit").asString()=="screen"&&
        a.parameters.require("path").asArray().back().asString()==hopeh;}));const auto battle=e.state().battleOrder.front();
    e.step(select(e,"air_screen_continue",[](const Action& a){return a.parameters.require("unit").asString()=="transport";}));
    e.step(select(e,"end_phase"));e.step(select(e,"land_begin_battle"));finishScreening(e,battle);
    const auto actions=e.legalActions();
    check(std::none_of(actions.begin(),actions.end(),[](const Action& a){return a.kind=="air_assault";}),
          "A screened continuing force conducted an airborne assault");
}
void survivingAirborneTransportLandsBeforeInfantryAttack() {
    auto s=fixture();add(s,"transport","air_transport","japan",beiping);
    add(s,"para","airborne_infantry","japan",beiping);add(s,"defender","militia","kmt",hopeh);
    add(s,"aaa","anti_aircraft_artillery","kmt",hopeh);s.captureTurnStart();
    Engine e(s,rules());e.setDiceTapeForTesting({12,12,12});const auto checkpoint=e.serialize();e.step(select(e,"air_load"));
    e.step(select(e,"air_assault",[](const Action& a){return a.parameters.require("path").asArray().back().asString()==hopeh;}));
    e.step(select(e,"end_phase"));e.step(select(e,"land_begin_battle"));
    check(e.state().chance&&e.state().chance->dice.size()==1&&
          e.state().units.at("para").carriedBy=="transport"&&
          e.state().battles.begin()->second.data.require("rolling_phase").asString()=="air_fire",
          "Surviving assault did not face defender AAA in shared step4 before landing");
    e.resolveChance();
    check(!e.state().chance&&e.state().decisions.back().kind=="air_landing"&&
          !e.state().units.at("para").carriedBy,"Transport did not unload and land before airborne infantry fire");
    e.step(select(e,"air_land",[](const Action& a){return a.parameters.require("destination").asString()==beiping;}));
    check(e.state().units.at("transport").zone==beiping&&e.state().units.at("para").zone==hopeh,
          "Airborne transport did not leave its surviving infantry at the battle");
    if(!e.state().chance)e.step(select(e,"land_progress_battle"));
    check(e.state().chance&&e.state().chance->purpose=="land_combat_roll","Airborne infantry fire did not follow transport landing");
    e.resolveChance();e.resolveChance();
    for(const auto& a:e.legalActions())check(a.kind!="land_retreat_begin","Airborne-only attacking infantry received a retreat option");
    auto replay=Engine::replay(s.definition,rules(),checkpoint,e.state().history);
    check(replay.exactReplayIdentity()==e.exactReplayIdentity(),"Surviving airborne AAA/landing sequence replay diverged");
}
void ordinaryAircraftRetreatUsesRemainingFlightAndReplays() {
    auto s=fixture();add(s,"fighter","fighter","japan",beiping);add(s,"defender","infantry","kmt",hopeh);s.captureTurnStart();
    Engine e(s,rules(),13);e.setDiceTapeForTesting({12,12});const auto checkpoint=e.serialize();
    e.step(select(e,"air_ground_attack",[](const Action& a){return a.parameters.require("path").asArray().back().asString()==hopeh;}));
    e.step(select(e,"end_phase"));e.step(select(e,"land_begin_battle"));e.resolveChance();e.resolveChance();
    e.step(select(e,"land_retreat_begin"));
    check(e.state().decisions.back().kind=="air_landing","Aircraft retreat did not choose a flight landing");
    e.step(select(e,"air_land",[](const Action& a){return a.parameters.require("destination").asString()==beiping;}));
    check(e.state().units.at("fighter").zone==beiping&&e.state().units.at("fighter").movementRemaining==2&&
          !e.state().units.at("fighter").turnFlags.contains("air_in_flight"),"Aircraft retreat ignored its actual remaining movement");
    auto replay=Engine::replay(s.definition,rules(),checkpoint,e.state().history);
    check(replay.exactReplayIdentity()==e.exactReplayIdentity(),"Aircraft retreat/landing replay diverged");
}

} // namespace
int main() {
    try {
        actualAirborneEntryFacesCityAAAndReplays();
        actualAirborneEntryResolvesFightersAndAaaBeforeLanding();
        regularInfantryCannotBecomeAirborneByStayingLoaded();
        controlledMinorsRetainSeparateAttackingForces();
        aircraftLaunchesFromCarrierAndReplaysCargoLinks();
        successfulAirScreeningContinuesToAnotherAttackAndReplays();
        failedAirScreeningForcesTheContinuingAircraftToLand();
        continuingAircraftCannotPerformAnAirborneAssault();
        survivingAirborneTransportLandsBeforeInfantryAttack();
        ordinaryAircraftRetreatUsesRemainingFlightAndReplays();
        std::cout << "10 air/land integration fixture groups passed\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
