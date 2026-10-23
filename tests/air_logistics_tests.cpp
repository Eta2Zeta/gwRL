#include "game/air.hpp"
#include "game/campaign_audit.hpp"
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
const Id honshu = "land_jap_honshu", beiping = "land_china_beiping", shantung = "land_china_shantung";
void check(bool ok, const std::string &why) {
    if (!ok)
        throw std::runtime_error(why);
}
State fixture(Phase phase = Phase::CombatMovement) {
    static const auto initial =
        loadScenario(std::filesystem::path(GWRL_SOURCE_DIR) / "game_content/scenarios/japan_china_1936");
    auto s = initial.clone();
    s.units.clear();
    s.facilities.clear();
    s.construction.clear();
    s.repairs.clear();
    s.clock.nationIndex = 2;
    s.clock.playerTurnSerial = 2;
    s.clock.phase = phase;
    s.completedTurns["ccp"] = s.completedTurns["mongolia"] = 1;
    s.territories.at(beiping).possessor = "japan";
    s.territories.at(shantung).possessor = "japan";
    s.captureTurnStart();
    return s;
}
void add(State &s, const Id &id, const Id &type, const Id &zone, const Id &owner = "japan") {
    UnitState u;
    u.id = id;
    u.type = type;
    u.owner = owner;
    u.zone = u.turnOrigin = zone;
    u.movementAllowance = u.movementRemaining =
        s.definition->catalog->stats(type, 0, catalogContext(s, owner, zone)).movement;
    s.units[id] = std::move(u);
}
bool offered(const State &s, const Id &kind) {
    const auto actions = AirRules{}.actions(s);
    return std::any_of(actions.begin(), actions.end(), [&](const auto &a) { return a.kind == kind; });
}
void endPatrolOnlyNoncombat() {
    auto s = fixture();
    add(s, "patrol", "fighter", "sea_p16");
    auto &u = s.units.at("patrol");
    u.gameFlags["on_map"] = 1;
    u.gameFlags["map_range"] = 1;
    u.commitments.insert("maritime_air_patrol");
    check(!offered(s, "air_end_patrol"), "MAP aircraft ended patrol during Combat Movement");
    s.clock.phase = Phase::NonCombatMovement;
    check(offered(s, "air_end_patrol"), "MAP aircraft could not return during Noncombat Movement");
}
void controlPermitsOverflightOnly() {
    auto s = fixture();
    ensureDadao(s);
    s.territories.at(shantung).possessor = "dadao";
    s.captureTurnStart();
    add(s, "aircraft", "fighter", beiping);
    check(controlledBy(s, "dadao", "japan"), "Fixture lost Dadao control");
    check(aircraftFlightAccess(s, "japan", shantung, false), "Controlling nation cannot overfly its minor");
    check(!airLandingAvailable(s, "aircraft", shantung),
          "Control alone granted landing permission in minor's land");
}
void baseMovementNeedsSupplyAndAge() {
    auto isolated = fixture();
    add(isolated, "aircraft", "fighter", beiping);
    isolated.facilities["base"] = {"base", "airbase", beiping, 0, {}};
    const int ordinary = *isolated.units.at("aircraft").movementRemaining;
    check(!inSupply(isolated, "japan", beiping), "Isolated-base fixture accidentally has supply");
    AirRules{}.beginTurn(isolated);
    check(isolated.units.at("aircraft").movementRemaining == ordinary,
          "Unsupplied airbase granted movement bonus");
    auto supplied = fixture();
    add(supplied, "aircraft", "fighter", honshu);
    supplied.facilities["base"] = {"base", "airbase", honshu, 0, {}};
    AirRules{}.beginTurn(supplied);
    check(supplied.units.at("aircraft").movementRemaining == ordinary + 1,
          "Held supplied airbase failed movement bonus");
    auto newBase = fixture();
    add(newBase, "aircraft", "fighter", honshu);
    newBase.facilities["base"] = {"base", "airbase", honshu, 0, {{"placed_this_turn", 1}}};
    AirRules{}.beginTurn(newBase);
    check(newBase.units.at("aircraft").movementRemaining == ordinary,
          "Newly placed airbase granted immediate movement bonus");
    auto damaged = fixture();
    add(damaged, "aircraft", "fighter", honshu);
    damaged.facilities["base"] = {"base", "airbase", honshu, 1, {}};
    AirRules{}.beginTurn(damaged);
    check(damaged.units.at("aircraft").movementRemaining == ordinary,
          "Damaged airbase granted movement bonus");
}
void carrierAircraftCanLaunch() {
    auto s = fixture();
    add(s, "carrier", "fleet_carrier", "sea_p16");
    add(s, "aircraft", "fighter", "sea_p16");
    attachCargo(s, "carrier", "aircraft");
    const auto actions = AirRules{}.actions(s);
    const auto flight = std::find_if(actions.begin(), actions.end(), [](const auto &a) {
        return a.kind == "air_fly" && a.parameters.require("unit").asString() == "aircraft";
    });
    check(flight != actions.end(), "Carrier-based aircraft has no launch action");
    AirRules{}.apply(s, *flight);
    check(!s.units.at("aircraft").carriedBy && s.units.at("carrier").cargo.empty(),
          "Launched aircraft remained carrier cargo");
}
void jointLandingCannotCountTheSameCarrierSlotsTwice() {
    auto s=fixture();add(s,"carrier","fleet_carrier","sea_p41");
    for(const auto& id:{Id("a"),Id("b")}) {
        add(s,id,"fighter","sea_p41");s.units.at(id).movementRemaining=0;s.units.at(id).turnFlags["air_in_flight"]=1;
    }
    check(airLandingPlanAvailable(s),"Two returning fighters cannot share a two-slot carrier");
    add(s,"c","fighter","sea_p41");s.units.at("c").movementRemaining=0;s.units.at("c").turnFlags["air_in_flight"]=1;
    for(const auto& id:{Id("a"),Id("b"),Id("c")})check(airLandingAvailable(s,id,"carrier"),"Individual landing query unexpectedly reserved an unassigned aircraft");
    check(!airLandingPlanAvailable(s)&&!AirRules{}.phaseComplete(s),"Three attackers reused two carrier slots at the Combat Movement boundary");
}
void jointLandingUsesWeightedCarrierAssignments() {
    auto s=fixture();add(s,"heavy","heavy_fleet_carrier","sea_p41");add(s,"fleet","fleet_carrier","sea_p41");
    for(const auto& id:{Id("a"),Id("b"),Id("c"),Id("bomber")}) {
        add(s,id,id=="bomber"?"medium_bomber":"fighter","sea_p41");
        s.units.at(id).movementRemaining=0;s.units.at(id).turnFlags["air_in_flight"]=1;
    }
    check(airLandingPlanAvailable(s),"Joint assignment stranded a bomber despite a fitting heavy-carrier allocation");
    s.units.erase("a");s.units.erase("b");s.units.erase("c");
    add(s,"second","medium_bomber","sea_p41");s.units.at("second").movementRemaining=0;s.units.at("second").turnFlags["air_in_flight"]=1;
    check(!airLandingPlanAvailable(s),"Medium bombers used a fleet carrier or shared only three heavy-carrier slots");
    add(s,"second_heavy","heavy_fleet_carrier","sea_p41");
    check(airLandingPlanAvailable(s),"Separate heavy carriers did not provide independent bomber capacity");
}
void scrambledAircraftReserveTheirOriginalCarrierSeats() {
    auto s=fixture(Phase::Combat);s.nations.at("japan").atWarWith.insert("kmt");s.nations.at("kmt").atWarWith.insert("japan");
    s.territories.at("land_china_hopeh").possessor="kmt";
    add(s,"carrier","heavy_fleet_carrier","sea_p14","kmt");
    for(const auto& id:{Id("a_scrambler"),Id("b_deck"),Id("c_deck")}){
        add(s,id,"fighter","sea_p14","kmt");attachCargo(s,"carrier",id);
    }
    add(s,"attacker","infantry","land_china_hopeh");add(s,"defender","militia","land_china_hopeh","kmt");
    s.nations.at("kmt").technologyStages["radar"]=4;s.captureTurnStart();
    const auto battle=registerLandBattle(s,"land_china_hopeh","japan",{"attacker"},{{"attacker",beiping}});
    beginAirDefence(s,battle);
    auto choice=std::find_if(s.decisions.back().options.begin(),s.decisions.back().options.end(),[](const auto& a){return a.kind=="air_scramble";});
    check(choice!=s.decisions.back().options.end(),"Radar heavy carrier did not offer its fighter scramble");
    const auto scramble=*choice;AirRules{}.apply(s,scramble);
    while(!s.decisions.empty()) {
        auto decline=std::find_if(s.decisions.back().options.begin(),s.decisions.back().options.end(),[](const auto& a){return a.kind=="air_decline_scramble";});
        check(decline!=s.decisions.back().options.end(),"Unexpected carrier-scramble continuation");
        const auto declined=*decline;AirRules{}.apply(s,declined);
    }
    add(s,"incoming","fighter","sea_p14","kmt");s.units.at("incoming").movementRemaining=0;
    s.units.at("incoming").turnFlags["air_in_flight"]=1;
    check(!airLandingAvailable(s,"incoming","carrier")&&!airLandingPlanAvailable(s),"Another plane stole a surviving scrambler's reserved carrier seat");
    removePoliticalUnits(s,{"incoming"});AirRules{}.finishPhase(s);
    check(s.units.at("a_scrambler").carriedBy=="carrier"&&s.units.at("carrier").cargo.size()==3,
          "Reserved carrier return was double-counted or failed to reattach the scrambler");
}
void landingChoicesPreserveOtherAircraftsOnlyCarrierSlot() {
    auto s=fixture(Phase::NonCombatMovement);add(s,"carrier","fleet_carrier","sea_p16");
    add(s,"deck","fighter","sea_p16");attachCargo(s,"carrier","deck");
    add(s,"flexible","fighter","sea_p16");s.units.at("flexible").movementRemaining=1;s.units.at("flexible").turnFlags["air_in_flight"]=1;
    add(s,"constrained","fighter","sea_p16");s.units.at("constrained").movementRemaining=0;s.units.at("constrained").turnFlags["air_in_flight"]=1;
    check(airLandingPlanAvailable(s),"Flexible land return and constrained carrier return were not jointly feasible");
    auto options=AirRules{}.actions(s);
    check(std::none_of(options.begin(),options.end(),[](const auto& a){return a.kind=="air_land_noncombat"&&
        a.parameters.require("unit").asString()=="flexible"&&a.parameters.require("destination").asString()=="carrier";}),
        "Flexible aircraft could consume the other aircraft's sole available slot");
    auto landAt=[&](const Id& unit,const Id& destination){auto actions=AirRules{}.actions(s);
        auto a=std::find_if(actions.begin(),actions.end(),[&](const auto& x){return x.kind=="air_land_noncombat"&&
            x.parameters.require("unit").asString()==unit&&x.parameters.require("destination").asString()==destination;});
        check(a!=actions.end(),"Missing noncombat carrier/land landing choice");AirRules{}.apply(s,*a);};
    landAt("flexible","land_jap_tokyo");landAt("constrained","carrier");
    check(s.units.at("flexible").zone=="land_jap_tokyo"&&s.units.at("constrained").carriedBy=="carrier",
          "Joint landing choices did not complete their feasible plan");
}
void attackDeclarationsRequireACombinedReturnPlan() {
    auto s=fixture();s.territories.at(beiping).possessor="kmt";s.territories.at(shantung).possessor="kmt";
    s.territories.at("land_china_hopeh").possessor="kmt";
    s.nations.at("japan").atWarWith.insert("kmt");s.nations.at("kmt").atWarWith.insert("japan");
    add(s,"carrier","fleet_carrier","sea_p14");
    for(const auto& id:{Id("a"),Id("b"),Id("c")})add(s,id,"fighter","land_jap_tokyo");
    s.facilities["base"]={"base","airbase","land_jap_tokyo",0,{}};s.captureTurnStart();AirRules{}.beginTurn(s);
    auto attack=[&](const Id& unit,const Id& kind){auto actions=AirRules{}.actions(s);
        auto a=std::find_if(actions.begin(),actions.end(),[&](const auto& x){return x.kind==kind&&
            x.parameters.require("unit").asString()==unit&&x.parameters.require("path").asArray().back().asString()=="land_china_hopeh";});
        check(a!=actions.end(),"Missing source-valid long-range carrier-return attack");AirRules{}.apply(s,*a);};
    attack("a","air_ground_attack");attack("b","air_support");
    const auto options=AirRules{}.actions(s);
    check(std::none_of(options.begin(),options.end(),[](const auto& a){return a.kind=="air_support"&&
        a.parameters.require("unit").asString()=="c"&&a.parameters.require("path").asArray().back().asString()=="land_china_hopeh";}),
        "Third attacking fighter double-counted the two returning carrier slots");
    check(airLandingPlanAvailable(s)&&AirRules{}.phaseComplete(s),"A valid two-aircraft return plan prevented Combat Movement completion");
}
void groundedLandingCannotRepeatWithoutChangingState() {
    auto s = fixture(Phase::NonCombatMovement);
    add(s, "grounded", "fighter", honshu);
    const auto options = AirRules{}.actions(s);
    const auto redundant = std::find_if(options.begin(), options.end(), [](const auto &a) {
        return a.kind == "air_land_noncombat" &&
               a.parameters.require("unit").asString() == "grounded" &&
               a.parameters.require("destination").asString() == honshu;
    });
    if (redundant != options.end()) {
        auto proof = s.clone();
        const auto before = proof.planningKey();
        AirRules{}.apply(proof, *redundant);
        check(proof.planningKey() == before, "Grounded landing unexpectedly changed its rule state");
        std::cout << "PROOF grounded landing preserved exact planning identity\n";
    }
    check(redundant == options.end(), "Grounded aircraft can repeat a same-zone landing with no effect");
    Action forged;
    forged.kind = "air_land_noncombat";
    forged.nation = "japan";
    forged.parameters = game::json::Value(game::json::Value::Object{
        {"unit", game::json::Value(std::string("grounded"))}, {"destination", game::json::Value(honshu)}});
    const auto before = s.planningKey();
    bool rejected = false;
    try { AirRules{}.apply(s, forged); } catch (const std::runtime_error &) { rejected = true; }
    check(rejected && s.planningKey() == before, "Forged no-effect landing changed state or escaped the guard");
    const auto moved = std::find_if(options.begin(), options.end(), [](const auto &a) {
        return a.kind == "air_land_noncombat" &&
               a.parameters.require("unit").asString() == "grounded" &&
               a.parameters.require("destination").asString() == "land_jap_tokyo";
    });
    check(moved != options.end(), "No-op filtering removed a real noncombat flight and landing");
    AirRules{}.apply(s, *moved);
    check(s.units.at("grounded").zone == "land_jap_tokyo" && !s.units.at("grounded").route.empty() &&
          !s.units.at("grounded").turnFlags.contains("air_in_flight"), "Real noncombat relocation failed");
}
void sameZoneLandingsRetainActualReturnEffects() {
    for (const bool screening : {false, true}) {
        auto s = fixture(Phase::NonCombatMovement);
        add(s, "returning", "fighter", honshu);
        auto &u = s.units.at("returning");
        u.movementRemaining = 0;
        u.turnFlags[screening ? "air_screening_ready" : "air_in_flight"] = 1;
        const auto options = AirRules{}.actions(s);
        const auto landing = std::find_if(options.begin(), options.end(), [](const auto &a) {
            return a.kind == "air_land_noncombat" &&
                   a.parameters.require("unit").asString() == "returning" &&
                   a.parameters.require("destination").asString() == honshu;
        });
        check(landing != options.end(), "Actual same-zone return or screening consumption was removed");
        const auto before = s.planningKey();
        AirRules{}.apply(s, *landing);
        check(s.planningKey() != before && !u.turnFlags.contains("air_in_flight") &&
              !u.turnFlags.contains("air_screening_ready"), "Same-zone return did not consume its state effect");
        if (screening)
            check(u.turnFlags.at("air_battle_turn") == static_cast<int>(s.clock.playerTurnSerial + 1),
                  "Landing failed to consume the screened aircraft's combat commitment");
    }
    auto s = fixture(Phase::NonCombatMovement);
    add(s, "first", "fleet_carrier", "sea_p16");
    add(s, "second", "fleet_carrier", "sea_p16");
    add(s, "deck", "fighter", "sea_p16");
    attachCargo(s, "first", "deck");
    const auto options = AirRules{}.actions(s);
    check(std::none_of(options.begin(), options.end(), [](const auto &a) {
        return a.kind == "air_land_noncombat" && a.parameters.require("unit").asString() == "deck" &&
               a.parameters.require("destination").asString() == "first";
    }), "Aircraft already aboard a carrier can repeatedly reattach to that carrier");
    const auto transfer = std::find_if(options.begin(), options.end(), [](const auto &a) {
        return a.kind == "air_land_noncombat" && a.parameters.require("unit").asString() == "deck" &&
               a.parameters.require("destination").asString() == "second";
    });
    check(transfer != options.end(), "No-op filtering removed a genuine same-sea carrier transfer");
    AirRules{}.apply(s, *transfer);
    check(s.units.at("deck").carriedBy == "second" && s.units.at("first").cargo.empty(),
          "Same-sea carrier transfer failed");
    add(s, "incoming", "fighter", "sea_p16");
    s.units.at("incoming").movementRemaining = 0;
    s.units.at("incoming").turnFlags["air_in_flight"] = 1;
    const auto incomingOptions = AirRules{}.actions(s);
    const auto actualReturn = std::find_if(incomingOptions.begin(), incomingOptions.end(), [](const auto &a) {
        return a.kind == "air_land_noncombat" && a.parameters.require("unit").asString() == "incoming" &&
               a.parameters.require("destination").asString() == "first";
    });
    check(actualReturn != incomingOptions.end(), "Redundant reattachment filtering removed an actual carrier return");
    AirRules{}.apply(s, *actualReturn);
    check(s.units.at("incoming").carriedBy == "first" &&
          !s.units.at("incoming").turnFlags.contains("air_in_flight"), "Actual carrier return failed");
}
void startingCarrierAircraftDoNotOfferRedundantReattachment() {
    auto engine = Engine::start(
        loadScenario(std::filesystem::path(GWRL_SOURCE_DIR) / "game_content/scenarios/japan_china_1936"),
        campaignRules(), 713);
    for (int step = 0; step < 40 && !(engine.state().currentNation() == "japan" &&
                                    engine.state().clock.phase == Phase::NonCombatMovement); ++step) {
        const auto options = engine.legalActions();
        auto next = std::find_if(options.begin(), options.end(), [](const auto &a) { return a.kind == "end_phase"; });
        if (next == options.end())
            next = std::find_if(options.begin(), options.end(), [](const auto &a) { return a.kind == "economy_finish_research"; });
        check(next != options.end(), "Approved setup did not offer the legal phase/research completion path");
        engine.step(*next);
    }
    const auto &state = engine.state();
    check(state.currentNation() == "japan" && state.clock.phase == Phase::NonCombatMovement,
          "Approved setup did not reach Japan Noncombat Movement");
    const auto &plane = state.units.at("japan_fighter_p15_fleet_carrier_1");
    check(plane.carriedBy == "japan_fleet_carrier_p15_setup_1", "Source setup aircraft lost its carrier");
    const auto options = engine.legalActions();
    check(std::none_of(options.begin(), options.end(), [&](const auto &a) {
        return a.kind == "air_land_noncombat" && a.parameters.require("unit").asString() == plane.id &&
               a.parameters.require("destination").asString() == plane.carriedBy;
    }), "Approved starting aircraft can repeatedly land on its existing carrier");
}
} // namespace
int main() {
    try {
        for(const auto& [name,test]:std::vector<std::pair<Id,std::function<void()>>>{
            {"patrol return timing",endPatrolOnlyNoncombat},{"minor overflight",controlPermitsOverflightOnly},
            {"supplied airbase",baseMovementNeedsSupplyAndAge},{"carrier launch",carrierAircraftCanLaunch},
            {"shared carrier slots",jointLandingCannotCountTheSameCarrierSlotsTwice},
            {"weighted joint assignment",jointLandingUsesWeightedCarrierAssignments},
            {"scramble reservations",scrambledAircraftReserveTheirOriginalCarrierSeats},
            {"landing choices",landingChoicesPreserveOtherAircraftsOnlyCarrierSlot},
            {"attack return planning",attackDeclarationsRequireACombinedReturnPlan},
            {"grounded landing no-op",groundedLandingCannotRepeatWithoutChangingState},
            {"actual same-zone returns",sameZoneLandingsRetainActualReturnEffects},
            {"starting carrier reattachment",startingCarrierAircraftDoNotOfferRedundantReattachment}}){
            test();std::cout<<"PASS "<<name<<'\n';
        }
        std::cout << "12 air logistics fixture groups passed\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
