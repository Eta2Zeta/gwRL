#include "game/air.hpp"
#include "game/campaign_audit.hpp"
#include "game/catalog.hpp"
#include "game/economy.hpp"
#include "game/land_combat.hpp"
#include "game/movement.hpp"
#include "game/naval.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <functional>
#include <iostream>
#include <set>
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
// The aircraft their owner may give up, and giving one up.
std::set<Id> givenUp(const State &s) {
    std::set<Id> out;
    for (const auto &a : AirRules{}.actions(s))
        if (a.kind == "air_failed_landing")
            out.insert(a.parameters.require("unit").asString());
    return out;
}
void giveUp(State &s, const Id &unit) {
    for (const auto &a : AirRules{}.actions(s))
        if (a.kind == "air_failed_landing" && a.parameters.require("unit").asString() == unit) {
            AirRules{}.apply(s, a);
            return;
        }
    throw std::runtime_error("Aircraft could not be given up: " + unit);
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
    // As attackers, one of the three must be lost: their owner chooses which, and
    // Combat Movement ends once the other two can land.
    for(const auto& id:{Id("a"),Id("b"),Id("c")})s.units.at(id).commitments.insert("air_combat");
    check(!airLandingPlanAvailable(s)&&airLandingShortfall(s)==1&&givenUp(s)==std::set<Id>{"a","b","c"}&&
              !AirRules{}.phaseComplete(s)&&strandedAircraft(s).size()==1,
          "Three attackers reused two carrier slots at the Combat Movement boundary");
    giveUp(s,"b");
    check(airLandingPlanAvailable(s)&&givenUp(s).empty()&&AirRules{}.phaseComplete(s),
          "Giving up one of three attackers did not let the other two land");
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
    // The plan with no list covers only the moving nation's aircraft; name KMT's.
    check(!airLandingAvailable(s,"incoming","carrier")&&!airLandingPlanAvailable(s,{"incoming"}),"Another plane stole a surviving scrambler's reserved carrier seat");
    removePoliticalUnits(s,{"incoming"});AirRules{}.finishPhase(s);
    check(s.units.at("a_scrambler").carriedBy=="carrier"&&s.units.at("carrier").cargo.size()==3,
          "Reserved carrier return was double-counted or failed to reattach the scrambler");
}
void landingChoicesPreserveOtherAircraftsOnlyCarrierSlot() {
    auto s=fixture(Phase::NonCombatMovement);add(s,"carrier","fleet_carrier","sea_p16");
    add(s,"deck","fighter","sea_p16");attachCargo(s,"carrier","deck");s.units.at("deck").movementRemaining=0;
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
void carriedAircraftAbleToFlyAshoreFreeTheirSeats() {
    auto s=fixture(Phase::NonCombatMovement);add(s,"carrier","light_carrier","sea_p16");
    add(s,"deck","fighter","sea_p16");attachCargo(s,"carrier","deck");
    add(s,"inbound","fighter","sea_p16");s.units.at("inbound").movementRemaining=0;s.units.at("inbound").turnFlags["air_in_flight"]=1;
    check(!airLandingPlanAvailable(s)&&airLandingPlanReachable(s),
          "A carried fighter able to fly ashore did not free its seat for an aircraft without fuel");
    s.units.at("deck").movementRemaining=0;
    check(!airLandingPlanReachable(s),"A carried fighter that cannot fly counted as leaving its seat");
}
// Seed 5090 of the random-play run: one bomber attacks Hopeh with one move
// left, a fighter without fuel waits over the fleet carrier, and the light
// carrier's only seat is the attacker's. A second bomber may take that seat
// only while the two carriers can still swap zones.
State fiveThousandNinety(bool lightCarrierCanSail) {
    auto s=fixture();
    for(const auto& zone:{beiping,shantung,Id("land_china_hopeh")})s.territories.at(zone).possessor="kmt";
    s.nations.at("japan").atWarWith.insert("kmt");s.nations.at("kmt").atWarWith.insert("japan");s.captureTurnStart();
    add(s,"light","light_carrier","sea_p14");add(s,"fleet","fleet_carrier","sea_p15");
    if(!lightCarrierCanSail)s.units.at("light").turnFlags["naval_movement_spent"]=99;
    auto airborne=[&](const Id& id,const Id& type,const Id& zone,int fuel){
        add(s,id,type,zone);s.units.at(id).movementRemaining=fuel;s.units.at(id).turnFlags["air_in_flight"]=1;};
    airborne("pinned","fighter","sea_p15",0);
    airborne("attacker","tactical_bomber","land_china_hopeh",1);s.units.at("attacker").commitments.insert("air_combat");
    airborne("returning","tactical_bomber","land_manchuria_rehe",1);
    return s;
}
void secondBomberCannotTakeTheAttackersOnlySeat() {
    const std::vector<Id> back{"land_manchuria_rehe","sea_p14"};
    for(const bool swap:{false,true}) {
        auto s=fiveThousandNinety(swap);
        check(airLandingPlanAvailable(s)&&airLandingPlanReachable(s),"The seed 5090 position lacked its landing plan");
        const auto actions=AirRules{}.actions(s);
        const auto offeredFor=[&](const Id& kind,const Id& place){return std::any_of(actions.begin(),actions.end(),[&](const auto& a){
            return a.kind==kind&&a.parameters.require("unit").asString()=="returning"&&(kind=="air_fly"
                ?a.parameters.require("path").asArray().back().asString()==place:a.parameters.require("destination").asString()==place);});};
        check(offeredFor("air_land_noncombat","land_manchuria_rehe"),"The second bomber lost its landing ashore");
        check(offeredFor("air_fly","sea_p14")==swap&&airFlightKeepsLandings(s,"returning",back)==swap,
              swap?"The carriers could not swap zones to seat both bombers and the fighter"
                  :"A second bomber took the only seat an attacking bomber can reach");
    }
    // Once the bomber is back over P14, either carrier may begin the swap.
    auto s=fiveThousandNinety(true);
    const auto actions=AirRules{}.actions(s);
    const auto fly=std::find_if(actions.begin(),actions.end(),[](const auto& a){return a.kind=="air_fly"&&
        a.parameters.require("unit").asString()=="returning"&&a.parameters.require("path").asArray().back().asString()=="sea_p14";});
    check(fly!=actions.end(),"The swap fixture offered no flight back over P14");
    AirRules{}.apply(s,*fly);
    check(validateNavalRoute(s,{{"light"},{"sea_p14","sea_p15"},true}).allowed&&
              validateNavalRoute(s,{{"fleet"},{"sea_p15","sea_p14"},true}).allowed,
          "Either carrier could not begin the swap that seats all three aircraft");
}
void attacksMayPrecedeTheCarrierTheyReturnTo() {
    auto s=fixture();for(const auto& zone:{beiping,shantung,Id("land_china_hopeh")})s.territories.at(zone).possessor="kmt";
    s.nations.at("japan").atWarWith.insert("kmt");s.nations.at("kmt").atWarWith.insert("japan");
    add(s,"cv","fleet_carrier","sea_p15");add(s,"f","fighter","land_jap_tokyo");
    s.facilities["base"]={"base","airbase","land_jap_tokyo",0,{}};s.captureTurnStart();AirRules{}.beginTurn(s);
    auto actions=AirRules{}.actions(s);
    auto attack=std::find_if(actions.begin(),actions.end(),[](const auto& a){return a.kind=="air_ground_attack"&&
        a.parameters.require("unit").asString()=="f"&&a.parameters.require("path").asArray().back().asString()=="land_china_hopeh";});
    check(attack!=actions.end(),"An attack was refused although its carrier can still sail into reach");
    AirRules{}.apply(s,*attack);
    check(!airLandingPlanAvailable(s)&&airLandingPlanReachable(s)&&!AirRules{}.phaseComplete(s),
          "The attack's later carrier landing was not left to a ship move");
    check(validateNavalRoute(s,{{"cv"},{"sea_p15","sea_p14"},true}).allowed&&
              !validateNavalRoute(s,{{"cv"},{"sea_p15","sea_p16"},true}).allowed,
          "The carrier the attacker relies on could sail away from it");
}
void otherNationsPatrolsDoNotHoldTheMoversPlan() {
    // A KMT patrol with no landing is lost by RB 9.3.1 at a phase end; it does
    // not constrain Japan's moves or keep Japan's Combat Movement open.
    auto s=fixture();add(s,"patrol","fighter","sea_p16","kmt");
    auto &u=s.units.at("patrol");u.gameFlags["on_map"]=1;u.gameFlags["map_range"]=0;u.commitments.insert("maritime_air_patrol");
    check(!airLandingPlanAvailable(s,{"patrol"})&&airLandingPlanAvailable(s)&&airLandingPlanReachable(s)&&AirRules{}.phaseComplete(s),
          "Another nation's stranded patrol held Japan's landing plan or Combat Movement");
}
void noncombatMovementEndsOnlyWithTheMoversPatrolsLandable() {
    auto s=fixture(Phase::NonCombatMovement);add(s,"cv","light_carrier","sea_p16");
    add(s,"deck","fighter","sea_p16");attachCargo(s,"cv","deck");s.units.at("deck").movementRemaining=0;
    add(s,"patrol","fighter","sea_p16");auto &u=s.units.at("patrol");
    u.gameFlags["on_map"]=1;u.gameFlags["map_range"]=0;u.commitments.insert("maritime_air_patrol");
    check(!AirRules{}.phaseComplete(s),"Noncombat Movement ended with Japan's own patrol unable to land");
    add(s,"spare","light_carrier","sea_p16");
    check(AirRules{}.phaseComplete(s),"A landable patrol kept Noncombat Movement open");
}
void aSailingCarriersAircraftMayUseAnyCarrier() {
    // The bomber needs the heavy carrier to sail; its fighter, left behind
    // without fuel, takes the light carrier that the bomber cannot use.
    auto s=fixture();add(s,"heavy","heavy_fleet_carrier","sea_p16");
    add(s,"deck","fighter","sea_p16");attachCargo(s,"heavy","deck");s.units.at("deck").movementRemaining=0;
    add(s,"light","light_carrier","sea_p16");
    add(s,"bomber","medium_bomber","sea_p15");s.units.at("bomber").movementRemaining=0;s.units.at("bomber").turnFlags["air_in_flight"]=1;
    check(!airLandingPlanAvailable(s)&&airLandingPlanReachable(s),
          "A sailing carrier's own aircraft could not use a carrier no airborne aircraft needed");
}
void aControlledMinorsAircraftKeepTheirLandings() {
    // Japan moves Dadao's units, so a Dadao fighter's flights must keep its
    // landing. It may land only on Dadao land, not Japan's.
    auto s=fixture();ensureDadao(s);s.territories.at("land_china_hopeh").possessor="dadao";s.captureTurnStart();
    add(s,"leased","fighter","land_china_hopeh","dadao");s.units.at("leased").movementRemaining=2;
    const auto actions=AirRules{}.actions(s);
    std::vector<int> fuels;
    for(const auto& a:actions)if(a.kind=="air_fly"&&a.parameters.require("unit").asString()=="leased")
        fuels.push_back(s.units.at("leased").movementRemaining.value_or(0)-static_cast<int>(a.parameters.require("path").asArray().size())+1);
    check(!fuels.empty()&&std::all_of(fuels.begin(),fuels.end(),[](int fuel){return fuel>=1;}),
          "A controlled minor's fighter was offered a flight from which it can never land");
}
void aircraftThatCannotLandDoNotBlockOtherMoves() {
    // Two patrols left by another nation's turn share one free seat, so one is
    // lost whatever Japan does. Moves that leave no more aircraft without a
    // landing stay legal, a carrier still may not abandon the patrol it can
    // seat, and Combat Movement may end at once.
    auto s=fixture();
    for(const Id zone:{"land_china_hopeh","land_china_shensi","land_china_suiyuan","land_china_szechwan","land_china_tsinghai"})
        s.territories.at(zone).possessor="kmt";
    s.nations.at("japan").atWarWith.insert("kmt");s.nations.at("kmt").atWarWith.insert("japan");s.captureTurnStart();
    add(s,"cv","light_carrier","sea_p16");
    for(const Id id:{"p1","p2"}){
        add(s,id,"fighter","sea_p16");auto &u=s.units.at(id);
        u.gameFlags["on_map"]=1;u.gameFlags["map_range"]=0;u.commitments.insert("maritime_air_patrol");
    }
    // A carrier with one zone of movement left, too far to bring a second seat.
    add(s,"other","light_carrier","sea_p32");
    for(int spent=1;spent<12&&validateNavalRoute(s,{{"other"},{"sea_p32","sea_p15","sea_p16"},true}).reason!=
                          "Insufficient naval movement";++spent)
        s.units.at("other").turnFlags["naval_movement_spent"]=spent;
    add(s,"bomber","tactical_bomber",beiping);add(s,"defender","infantry","land_china_hopeh","kmt");
    check(airLandingShortfall(s)==1&&!airLandingPlanReachable(s),"Two patrols for one seat did not leave exactly one without a landing");
    const auto attacks=[](const State& state,const Id& unit,const Id& target){
        const auto actions=AirRules{}.actions(state);
        return std::any_of(actions.begin(),actions.end(),[&](const auto& a){
            return (a.kind=="air_ground_attack"||a.kind=="air_bomb"||a.kind=="air_support")&&
                   a.parameters.require("unit").asString()==unit&&a.parameters.require("path").asArray().back().asString()==target;});
    };
    check(attacks(s,"bomber","land_china_hopeh"),"A patrol that cannot land blocked an unrelated attack");
    check(validateNavalRoute(s,{{"other"},{"sea_p32","sea_p33"},true}).allowed,"A patrol that cannot land blocked an unrelated carrier");
    check(!validateNavalRoute(s,{{"cv"},{"sea_p16","sea_p15","sea_p33"},true}).allowed,"A carrier abandoned the patrol it can still seat");
    check(givenUp(s)==std::set<Id>{"p1","p2"}&&!AirRules{}.phaseComplete(s),
          "The owner could not choose which of two patrols for one seat is lost");
    // A fighter in flight may attack only if it can still land afterwards, even
    // where it is already lost without the attack.
    add(s,"target","infantry","land_china_suiyuan","kmt");
    add(s,"stray","fighter","land_china_shensi");s.units.at("stray").turnFlags["air_in_flight"]=1;
    s.units.at("stray").movementRemaining=3;
    check(airLandingShortfall(s)==1&&attacks(s,"stray","land_china_suiyuan"),"A fighter able to return was refused its attack");
    s.units.at("stray").movementRemaining=1;
    check(airLandingShortfall(s)==2&&!attacks(s,"stray","land_china_suiyuan"),"A fighter that cannot land spent its last flight attacking");
    // Combat Movement stays open while a carrier can still save an aircraft,
    // even with another already lost.
    auto waiting=s.clone();waiting.units.erase("stray");
    add(waiting,"late","fighter","sea_p33");waiting.units.at("late").movementRemaining=0;
    waiting.units.at("late").turnFlags["air_in_flight"]=1;waiting.units.at("late").commitments.insert("air_combat");
    check(airLandingShortfall(waiting)==1&&!AirRules{}.phaseComplete(waiting)&&!givenUp(waiting).contains("late"),
          "Combat Movement ended, or offered to give up an attacker, while a carrier could still sail to it");
    waiting.units.at("other").zone="sea_p33";
    check(!AirRules{}.phaseComplete(waiting),"Combat Movement ended before the owner gave up the patrol that cannot land");
    giveUp(waiting,"p1");
    check(AirRules{}.phaseComplete(waiting),"Combat Movement stayed open with every remaining aircraft able to land");
}
void aMediumBomberLeftOutMayBeGivenUpAndAloneIsLost() {
    // A medium bomber takes two of a heavy carrier's seats. With two seats left
    // and two fighters also needing them, the plan that lands the most loses the
    // bomber: it may be given up although a free seat remains, and ending Combat
    // Movement loses it alone rather than both fighters.
    auto s=fixture();add(s,"heavy","heavy_fleet_carrier","sea_p41");
    add(s,"x","fighter","sea_p41");attachCargo(s,"heavy","x");s.units.at("x").movementRemaining=0;
    for(const auto& [id,type]:{std::pair<Id,Id>{"a","medium_bomber"},{"b","fighter"},{"c","fighter"}}){
        add(s,id,type,"sea_p41");s.units.at(id).movementRemaining=0;s.units.at(id).turnFlags["air_in_flight"]=1;
    }
    for(const auto& id:{Id("b"),Id("c")})s.units.at(id).commitments.insert("air_combat");
    const auto actions=AirRules{}.actions(s);
    check(airLandingShortfall(s)==1&&!airLandingSpots(s,"a").empty()&&
              std::any_of(actions.begin(),actions.end(),[](const auto& a){
                  return a.kind=="air_failed_landing"&&a.parameters.require("unit").asString()=="a";}),
          "A medium bomber that no plan can land could not be given up");
    s.units.at("a").commitments.insert("air_combat");
    check(givenUp(s)==std::set<Id>{"a"}&&!AirRules{}.phaseComplete(s)&&strandedAircraft(s)==std::vector<Id>{"a"},
          "The owner could give up a fighter where only losing the bomber loses no more");
    giveUp(s,"a");
    check(AirRules{}.phaseComplete(s),"Combat Movement stayed open after the bomber was given up");
}
void continuingAndScreenedAircraftMayBeGivenUp() {
    // A continuing (screening) aircraft counts among the losses and may be chosen,
    // and in Combat a screened aircraft left with no landing may be given up, so
    // the phase can end.
    auto s=fixture();add(s,"cv","light_carrier","sea_p16");
    add(s,"p1","fighter","sea_p16");s.units.at("p1").gameFlags["on_map"]=1;s.units.at("p1").gameFlags["map_range"]=0;
    s.units.at("p1").commitments.insert("maritime_air_patrol");
    add(s,"cont","fighter","sea_p16");s.units.at("cont").movementRemaining=0;
    s.units.at("cont").turnFlags["air_in_flight"]=1;s.units.at("cont").turnFlags["air_screening_wait"]=1;
    s.units.at("cont").commitments.insert("air_combat");
    check(airLandingShortfall(s)==1&&givenUp(s)==std::set<Id>{"p1","cont"},
          "A continuing aircraft could not be chosen among the losses");
    auto combat=fixture(Phase::Combat);
    add(combat,"ready","fighter","sea_p16");combat.units.at("ready").movementRemaining=0;
    combat.units.at("ready").turnFlags["air_in_flight"]=1;combat.units.at("ready").turnFlags["air_screening_ready"]=1;
    combat.units.at("ready").commitments.insert("air_combat");
    check(givenUp(combat)==std::set<Id>{"ready"},"A screened aircraft with no landing could not be given up in Combat");
    giveUp(combat,"ready");
    check(!combat.units.contains("ready"),"Giving up the screened aircraft left it in play");
}
void givingUpAMissionsLastBomberEndsTheMission() {
    // A bombing mission whose only bomber is given up has nothing to escort: it
    // ends, and its escort flies on uncommitted.
    auto s=fixture();add(s,"heavy","heavy_fleet_carrier","sea_p41");
    add(s,"x","fighter","sea_p41");attachCargo(s,"heavy","x");s.units.at("x").movementRemaining=0;
    for(const auto& [id,type]:{std::pair<Id,Id>{"a","medium_bomber"},{"b","fighter"},{"c","fighter"}}){
        add(s,id,type,"sea_p41");s.units.at(id).movementRemaining=0;s.units.at(id).turnFlags["air_in_flight"]=1;
        s.units.at(id).commitments.insert("air_combat");
    }
    add(s,"esc","fighter",beiping);s.units.at("esc").turnFlags["air_in_flight"]=1;s.units.at("esc").commitments.insert("air_combat");
    BattleState mission;mission.id="mission";mission.zone="land_china_hopeh";mission.attacker="japan";mission.defender="kmt";
    mission.stage="air_declared";mission.flags["air_mission"]=1;mission.attackers={"a","esc"};
    s.battles.emplace(mission.id,mission);s.battleOrder.push_back(mission.id);
    giveUp(s,"a");
    check(!s.battles.contains("mission")&&!s.units.at("esc").commitments.contains("air_combat"),
          "A bombing mission kept its escort after losing its only bomber");
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
            {"freed carrier seats",carriedAircraftAbleToFlyAshoreFreeTheirSeats},
            {"seed 5090 carrier seat",secondBomberCannotTakeTheAttackersOnlySeat},
            {"attack before carrier",attacksMayPrecedeTheCarrierTheyReturnTo},
            {"other nations' patrols",otherNationsPatrolsDoNotHoldTheMoversPlan},
            {"noncombat patrol landings",noncombatMovementEndsOnlyWithTheMoversPatrolsLandable},
            {"released aircraft seats",aSailingCarriersAircraftMayUseAnyCarrier},
            {"controlled minor's aircraft",aControlledMinorsAircraftKeepTheirLandings},
            {"aircraft that cannot land",aircraftThatCannotLandDoNotBlockOtherMoves},
            {"medium bomber left out",aMediumBomberLeftOutMayBeGivenUpAndAloneIsLost},
            {"continuing and screened aircraft",continuingAndScreenedAircraftMayBeGivenUp},
            {"mission without its bomber",givingUpAMissionsLastBomberEndsTheMission},
            {"attack return planning",attackDeclarationsRequireACombinedReturnPlan},
            {"grounded landing no-op",groundedLandingCannotRepeatWithoutChangingState},
            {"actual same-zone returns",sameZoneLandingsRetainActualReturnEffects},
            {"starting carrier reattachment",startingCarrierAircraftDoNotOfferRedundantReattachment}}){
            test();std::cout<<"PASS "<<name<<'\n';
        }
        std::cout << "23 air logistics fixture groups passed\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
