#include "game/naval.hpp"
#include "game/air.hpp"
#include "game/catalog.hpp"
#include "game/economy.hpp"
#include "game/politics.hpp"
#include <algorithm>
#include <functional>
#include <iostream>
#include <stdexcept>

namespace {
using namespace game::campaign;
using V = game::json::Value; using O = V::Object; using A = V::Array;
const Id sea="sea_p15", from="sea_p14", other="sea_p16", tokyo="land_jap_tokyo";
void check(bool ok,const std::string& why){if(!ok)throw std::runtime_error(why);}
State fixture(){
    static auto base=loadScenario(std::filesystem::path(GWRL_SOURCE_DIR)/"game_content/scenarios/japan_china_1936");
    auto s=base.clone();s.units.clear();s.facilities.clear();s.construction.clear();s.repairs.clear();
    s.clock.nationIndex=2;s.clock.playerTurnSerial=2;s.clock.phase=Phase::Combat;
    s.completedTurns["ccp"]=s.completedTurns["mongolia"]=1;
    s.nations.at("japan").atWarWith.insert("kmt");s.nations.at("kmt").atWarWith.insert("japan");
    s.captureTurnStart();return s;
}
void add(State& s,const Id& id,const Id& type,const Id& owner,const Id& zone=sea){
    UnitState u;u.id=id;u.type=type;u.owner=owner;u.zone=u.turnOrigin=zone;
    u.movementAllowance=u.movementRemaining=s.definition->catalog->stats(type,0,catalogContext(s,owner,zone)).movement;
    s.units[id]=u;
}
std::shared_ptr<const Rules> rules(){return std::make_shared<NavalRules>(std::make_shared<AirRules>(std::make_shared<EconomyRules>()));}
Action pick(Engine& e,const Id& kind,const std::function<bool(const Action&)>& match=[](const Action&){return true;}){
    for(const auto& a:e.legalActions())if(a.kind==kind&&match(a))return a;
    throw std::runtime_error("Missing naval test action "+kind);
}
void choose(Engine& e,const Id& kind,const Id& unit=""){
    e.step(pick(e,kind,[&](const Action& a){return unit.empty()||(a.parameters.find("unit")&&a.parameters.require("unit").asString()==unit);}));
}
Id battle(State& s,const std::vector<Id>& attackers,const O& extra={}){
    O options=extra;options["no_scramble"]=V(true);std::map<Id,Id> origins;for(const auto& id:attackers)origins[id]=from;
    return registerNavalBattle(s,sea,"japan",attackers,origins,V(options));
}
void finish(Engine& e){
    for(int i=0;i<100&&!e.state().battles.empty();++i){
        if(e.state().chance){e.resolveChance();continue;}
        auto actions=e.legalActions();check(!actions.empty(),"Naval battle lacks continuation");
        auto choice=std::find_if(actions.begin(),actions.end(),[](const Action& a){return a.kind=="naval_finish_battle"||a.kind=="naval_progress_battle";});
        if(choice!=actions.end())e.step(*choice);else e.step(actions.front());
    }
    check(e.state().battles.empty(),"Naval battle did not finish within test budget");
}
void reciprocalHitsAndReplay(){
    auto s=fixture();add(s,"a","destroyer","japan");add(s,"d","destroyer","kmt");auto id=battle(s,{"a"});
    Engine e(s,rules(),5);e.setDiceTapeForTesting({1,1});const auto checkpoint=e.serialize();choose(e,"naval_begin_battle");e.resolveChance();choose(e,"naval_take_casualty","d");
    check(e.state().chance&&e.state().units.contains("d"),"Ordinary naval casualty failed to return fire");
    e.resolveChance();choose(e,"naval_take_casualty","a");check(e.state().units.empty(),"Simultaneous naval casualties survived");
    check(e.state().battles.at(id).data.require("result").asString()=="mutual_destruction","Mutual destruction result wrong");finish(e);
    auto replayed=Engine::replay(s.definition,rules(),checkpoint,e.state().history);check(replayed.exactReplayIdentity()==e.exactReplayIdentity(),"Naval casualty replay diverged");
}
void capitalHitsAndDamageValues(){
    auto s=fixture();add(s,"a1","destroyer","japan");add(s,"a2","destroyer","japan");add(s,"d","battleship","kmt");battle(s,{"a1","a2"});
    Engine e(s,rules());e.setDiceTapeForTesting({1,1,12});choose(e,"naval_begin_battle");e.resolveChance();choose(e,"naval_take_casualty","d");
    check(e.state().units.at("d").damage==1&&e.state().units.at("d").movementRemaining==1,"First battleship hit did not reduce damage/movement once");
    choose(e,"naval_take_casualty","d");check(e.state().chance&&e.state().units.contains("d"),"Sunk capital ship did not receive ordinary return fire");e.resolveChance();finish(e);
    check(!e.state().units.contains("d"),"Second battleship hit failed to sink");
    auto c=s.definition->catalog->stats("heavy_battleship",2,catalogContext(s,"japan",sea));
    check(c.attack==6&&c.defense==6&&c.movement==2,"User-confirmed capital damage matrix changed");
    auto carrier=s.definition->catalog->stats("fleet_carrier",1,catalogContext(s,"japan",sea));check(carrier.defense==1,"Damaged carrier defense incorrect");
}
void submarineFirstStrikeAndDestroyer(){
    auto s=fixture();add(s,"a","submarine","japan");add(s,"d","heavy_cruiser","kmt");battle(s,{"a"});Engine e(s,rules());e.setDiceTapeForTesting({2});choose(e,"naval_begin_battle");e.resolveChance();choose(e,"naval_take_casualty","d");
    check(!e.state().units.contains("d")&&!e.state().chance,"Submarine first-strike victim returned fire");finish(e);
    auto t=fixture();add(t,"a","submarine","japan");add(t,"d","destroyer","kmt");battle(t,{"a"});Engine f(t,rules());f.setDiceTapeForTesting({2,12});choose(f,"naval_begin_battle");f.resolveChance();choose(f,"naval_take_casualty","d");
    check(f.state().units.contains("d")&&f.state().chance,"Destroyer failed to negate enemy submarine first strike");
}
void protectedSubmarinesAndSubmerge(){
    auto s=fixture();add(s,"a","destroyer","japan");add(s,"d","submarine","kmt");battle(s,{"a"});Engine e(s,rules());e.setDiceTapeForTesting({12});choose(e,"naval_begin_battle");choose(e,"naval_sub_protected");
    check(e.state().chance&&e.state().chance->dice.size()==1,"Protected submarine incorrectly became an ordinary destroyer target");e.resolveChance();
    check(e.state().units.at("d").turnFlags.at("submerged")==1,"Surviving defending submarine did not submerge");finish(e);
    auto t=fixture();add(t,"a","destroyer","japan");add(t,"d","submarine","kmt");battle(t,{"a"});Engine f(t,rules());choose(f,"naval_begin_battle");choose(f,"naval_sub_decline");
    check(!f.state().units.at("d").turnFlags.contains("submerged"),"Declining submarine was incorrectly submerged");finish(f);
}
void mapPairingAndAdvancedSubmarineImmunity(){
    for(bool advanced:{false,true}){
        auto s=fixture();add(s,"a","destroyer","japan");add(s,"p","seaplane","japan");s.units.at("p").gameFlags["on_map"]=1;s.units.at("p").gameFlags["map_range"]=2;
        add(s,"d",advanced?"advanced_submarine":"submarine","kmt");battle(s,{"a","p"});Engine e(s,rules());e.setDiceTapeForTesting({12,12,12});choose(e,"naval_begin_battle");
        if(!advanced)choose(e,"naval_pair_destroyer");choose(e,"naval_sub_protected");
        check(e.state().chance&&e.state().chance->dice.size()==(advanced?1:2),"MAP pairing targeted advanced submarine or omitted ordinary pairing");
    }
}
void transportsLastAndLinkedCargo(){
    auto s=fixture();add(s,"a","heavy_cruiser","japan");add(s,"d","heavy_cruiser","kmt");add(s,"t","naval_transport","kmt");add(s,"cargo","infantry","kmt");attachCargo(s,"t","cargo");battle(s,{"a"});
    Engine e(s,rules());e.setDiceTapeForTesting({4,12});choose(e,"naval_begin_battle");e.resolveChance();for(const auto& a:e.legalActions())check(a.parameters.require("unit").asString()!="t","Transport offered before other valid casualty");
    auto t=fixture();add(t,"a","submarine","japan");add(t,"d","heavy_cruiser","kmt");add(t,"t","naval_transport","kmt");add(t,"cargo","infantry","kmt");attachCargo(t,"t","cargo");battle(t,{"a"});
    Engine f(t,rules());f.setDiceTapeForTesting({1});choose(f,"naval_begin_battle");f.resolveChance();check(f.state().decisions.back().nation=="japan","Submarine Target Selection did not belong to shooter");choose(f,"naval_take_casualty","t");check(!f.state().units.contains("t")&&!f.state().units.contains("cargo"),"Targeted transport loss spared cargo");
}
void aswTransportDefendsOnlySubmarines(){
    auto s=fixture();add(s,"a","submarine","japan");add(s,"d","naval_transport","kmt");s.nations.at("kmt").technologyStages["anti_submarine_warfare"]=4;battle(s,{"a"});
    Engine e(s,rules());e.setDiceTapeForTesting({12,1});choose(e,"naval_begin_battle");e.resolveChance();
    check(e.state().chance.has_value(),"ASW transport failed to defend against attacking submarine");e.resolveChance();choose(e,"naval_take_casualty","a");check(!e.state().units.contains("a"),"ASW transport defense hit did not apply");
}
void retreatUsesActualShipEntry(){
    auto s=fixture();add(s,"a","destroyer","japan");add(s,"d","destroyer","kmt");auto id=battle(s,{"a"});Engine e(s,rules());e.setDiceTapeForTesting({12,12});choose(e,"naval_begin_battle");e.resolveChance();e.resolveChance();choose(e,"naval_retreat_begin");
    for(const auto& a:e.legalActions())check(a.parameters.require("zone").asString()==from,"Naval retreat offered unused entry sea");choose(e,"naval_retreat_unit","a");
    check(e.state().units.at("a").zone==from&&e.state().units.at("a").movementRemaining==0,"Naval retreat did not exhaust movement");finish(e);
}
void carrierLossRescuesDefendingAircraft(){
    auto s=fixture();add(s,"a","submarine","japan");add(s,"c","light_carrier","kmt");add(s,"p","fighter","kmt");add(s,"other","fleet_carrier","kmt");attachCargo(s,"c","p");
    auto id=battle(s,{"a"},{{"defenders",V(A{V(std::string("c")),V(std::string("p"))})}});
    Engine e(s,rules());e.setDiceTapeForTesting({1});choose(e,"naval_begin_battle");e.resolveChance();choose(e,"naval_take_casualty","c");
    check(e.state().units.contains("p")&&e.state().decisions.back().kind=="naval_carrier_landing","Carrier loss recursively destroyed defending aircraft or skipped immediate landing");
    e.step(pick(e,"naval_carrier_land",[](const Action& a){return a.parameters.require("destination").asString()=="other";}));
    check(e.state().units.at("p").carriedBy=="other","Sunk-carrier aircraft failed to land on available carrier");finish(e);
}
void defendingAircraftReturnToTheirIntactCarrier(){
    auto s=fixture();add(s,"a","destroyer","japan");add(s,"c","fleet_carrier","kmt");add(s,"p","fighter","kmt");attachCargo(s,"c","p");
    registerNavalBattle(s,sea,"japan",{"a"},{{"a",from}});Engine e(s,rules());e.setDiceTapeForTesting({12,12,12});choose(e,"naval_begin_battle");choose(e,"air_defend","p");
    check(!e.state().units.at("p").carriedBy&&e.state().units.at("p").commitments.contains("air_defending_carrier:c"),"Defending carrier aircraft did not preserve its source");
    choose(e,"naval_progress_battle");e.resolveChance();e.resolveChance();e.resolveChance();choose(e,"naval_retreat_begin");choose(e,"naval_retreat_unit","a");
    check(e.state().units.at("p").carriedBy=="c"&&e.state().units.at("p").movementRemaining==4&&
          !e.state().units.at("p").commitments.contains("air_defending_carrier:c"),"Defending aircraft did not return to intact carrier without a bonus flight");finish(e);
}
void declaredAircraftMergeAndAttackOriginsStayNaval(){
    auto s=fixture();add(s,"a","destroyer","japan");add(s,"p","fighter","japan");add(s,"d","destroyer","kmt");auto first=battle(s,{"a"});
    auto second=registerNavalBattle(s,sea,"japan",{"p"},{{"p",other}},V(O{{"context",V(std::string("standard"))}}));
    check(first==second&&s.battles.size()==1&&s.battles.at(first).attackers.size()==2,"Same nation's naval aircraft did not join its declared sea battle");
    check(s.battles.at(first).data.require("naval_entry_origins").asArray().size()==1,"Aircraft approach created a naval retreat origin");
}
void portAttackStillGetsFacilityAaAfterShipLoss(){
    auto s=fixture();s.territories.at(tokyo).possessor="kmt";s.captureTurnStart();
    FacilityState f;f.id="port";f.type="major_port";f.zone=tokyo;s.facilities[f.id]=f;
    add(s,"a","fighter","japan");add(s,"d","destroyer","kmt",tokyo);s.units.at("d").gameFlags["in_port:port"]=1;
    auto id=registerNavalBattle(s,sea,"japan",{"a"},{{"a",from}},V(O{{"context",V(std::string("port_attack"))},{"facility",V(std::string("port"))},{"defenders",V(A{V(std::string("d"))})},{"no_scramble",V(true)}}));
    Engine e(s,rules());e.setDiceTapeForTesting({1,1});choose(e,"naval_begin_battle");e.resolveChance();choose(e,"naval_take_casualty","d");
    check(e.state().chance&&e.state().chance->purpose=="naval_port_aa","Port facility lost its AA merely because its last ship was sunk");e.resolveChance();choose(e,"naval_take_casualty","a");
    check(!e.state().units.contains("a")&&!e.state().units.contains("d"),"Port attack AA or ship casualty wrong");finish(e);
}
void oneRoundMovementEncounterExcludesParkedFleet(){
    auto s=fixture();s.clock.phase=Phase::CombatMovement;add(s,"a","destroyer","japan");add(s,"d","submarine","kmt");add(s,"parked","battleship","kmt");
    battle(s,{"a"},{{"context",V(std::string("movement_submarines"))},{"submarines_initiated",V(true)},{"defenders",V(A{V(std::string("d"))})}});
    Engine e(s,rules());e.setDiceTapeForTesting({12,12});choose(e,"naval_begin_battle");e.resolveChance();e.resolveChance();
    check(e.state().units.at("parked").damage==0&&!e.state().units.at("parked").turnFlags.contains("naval_combat_turn"),"Moving submarine reaction borrowed unrelated parked fleet");
    check(e.state().units.at("a").movementRemaining==3&&e.state().clock.phase==Phase::CombatMovement,"Single-round encounter spent extra movement or advanced phase");finish(e);
}
void raiderDiscoveryTiesAndSlipStayInSea(){
    auto s=fixture();add(s,"a","destroyer","japan");add(s,"d","battlecruiser","kmt");s.units.at("d").gameFlags["raider"]=1;auto id=battle(s,{"a"});
    Engine e(s,rules());e.setDiceTapeForTesting({1,6,12,1});const auto checkpoint=e.serialize();choose(e,"naval_begin_battle");choose(e,"naval_discover_raider");e.resolveChance();
    check(e.state().chance&&e.state().chance->purpose=="naval_raider_discovery","Equal modified raider dice did not reroll");e.resolveChance();
    check(e.state().decisions.back().nation=="kmt","Winning raider slip choice went to attacker");choose(e,"naval_raider_slip");check(e.state().units.at("d").zone==sea,"Slipping defending raider teleported to another sea");finish(e);
    auto replayed=Engine::replay(s.definition,rules(),checkpoint,e.state().history);check(replayed.exactReplayIdentity()==e.exactReplayIdentity(),"Raider tie/slip replay diverged");
    auto t=fixture();add(t,"a","destroyer","japan");add(t,"d","battlecruiser","kmt");t.units.at("d").gameFlags["raider"]=1;auto bid=battle(t,{"a"});Engine f(t,rules());f.setDiceTapeForTesting({1,12,12,12});choose(f,"naval_begin_battle");choose(f,"naval_discover_raider");f.resolveChance();f.resolveChance();f.resolveChance();
    check(f.state().battles.at(bid).flags.at("finished")&&f.state().battles.at(bid).data.require("round").asInt()==1,"Lone defending raider exceeded one round");finish(f);
}
void jointDefenseDisputeUsesEntitledPlayers(){
    auto s=fixture();s.nations.at("ccp").atWarWith.insert("japan");s.nations.at("japan").atWarWith.insert("ccp");
    add(s,"a","destroyer","japan");add(s,"d_ccp","destroyer","ccp");add(s,"d_kmt","destroyer","kmt");battle(s,{"a"});Engine e(s,rules());e.setDiceTapeForTesting({4,12,1,12,12});choose(e,"naval_begin_battle");e.resolveChance();choose(e,"naval_take_casualty","d_ccp");
    check(e.state().decisions.back().nation=="kmt"&&e.state().decisions.back().reaction,"Other defending alliance did not receive casualty agreement choice");choose(e,"naval_casualty_dispute");e.resolveChance();
    check(e.state().decisions.back().nation=="kmt","Highest dispute die did not receive casualty choice");choose(e,"naval_take_casualty","d_ccp");
    check(e.state().chance&&e.state().chance->dice.size()==2,"Disputed ordinary casualty lost its normal return fire");
}
void shipScrambleAndSkeletonCrewExclusion(){
    auto s=fixture();s.territories.at(tokyo).possessor="kmt";FacilityState port;port.id="scramble_port";port.type="major_port";port.zone=tokyo;port.flags["border:"+sea]=1;s.facilities[port.id]=port;
    add(s,"a","destroyer","japan");add(s,"d","destroyer","kmt");add(s,"scramble","destroyer","kmt",tokyo);add(s,"locked","heavy_cruiser","kmt",tokyo);
    s.units.at("scramble").gameFlags["in_port:scramble_port"]=1;s.units.at("locked").gameFlags["in_port:scramble_port"]=1;s.units.at("locked").gameFlags["skeleton_crew_until_own_turn"]=1;s.captureTurnStart();
    registerNavalBattle(s,sea,"japan",{"a"},{{"a",from}});Engine e(s,rules());choose(e,"naval_begin_battle");
    for(const auto& a:e.legalActions())check(a.parameters.require("unit").asString()=="scramble","Skeleton crew was allowed to scramble");choose(e,"naval_scramble","scramble");
    check(e.state().units.at("scramble").zone==sea&&e.state().units.at("scramble").commitments.contains("naval_scramble_origin:scramble_port"),"Ship scramble lost physical source");
}
void scrambledCarrierTakesItsAircraft(){
    auto s=fixture();s.territories.at(tokyo).possessor="kmt";FacilityState port;port.id="scramble_port";port.type="major_port";port.zone=tokyo;port.flags["border:"+sea]=1;s.facilities[port.id]=port;
    add(s,"a","destroyer","japan");add(s,"d","destroyer","kmt");add(s,"carrier","fleet_carrier","kmt",tokyo);add(s,"plane","fighter","kmt",tokyo);
    s.units.at("carrier").gameFlags["in_port:scramble_port"]=1;attachCargo(s,"carrier","plane");s.captureTurnStart();
    registerNavalBattle(s,sea,"japan",{"a"},{{"a",from}});Engine e(s,rules());choose(e,"naval_begin_battle");choose(e,"naval_scramble","carrier");
    check(e.state().units.at("carrier").zone==sea&&e.state().units.at("plane").zone==sea,"Scrambled Carrier left its aircraft in port");
}
void seaplaneAswBonusTargetsSubmarines(){
    auto s=fixture();add(s,"a","seaplane","japan");add(s,"d","submarine","kmt");s.nations.at("japan").technologyStages["anti_submarine_warfare"]=4;
    s.units.at("a").gameFlags["on_map"]=1;s.units.at("a").gameFlags["map_range"]=2;const auto base=s.definition->catalog->stats("seaplane",0,catalogContext(s,"japan",sea)).attack.value();battle(s,{"a"});
    Engine e(s,rules());e.setDiceTapeForTesting({base+1});choose(e,"naval_begin_battle");choose(e,"naval_sub_protected");e.resolveChance();choose(e,"naval_take_casualty","d");check(!e.state().units.contains("d"),"Seaplane MAP ASW bonus did not hit submarine");finish(e);
}
} // namespace
int main(){try{
    const std::vector<std::pair<std::string, std::function<void()>>> checks {
        {"reciprocal", reciprocalHitsAndReplay}, {"capital", capitalHitsAndDamageValues}, {"first strike", submarineFirstStrikeAndDestroyer},
        {"protected submarines", protectedSubmarinesAndSubmerge}, {"MAP pairing", mapPairingAndAdvancedSubmarineImmunity},
        {"transports", transportsLastAndLinkedCargo}, {"ASW", aswTransportDefendsOnlySubmarines}, {"retreat", retreatUsesActualShipEntry},
        {"carrier", carrierLossRescuesDefendingAircraft}, {"air merge", declaredAircraftMergeAndAttackOriginsStayNaval}, {"carrier return", defendingAircraftReturnToTheirIntactCarrier},
        {"port AA", portAttackStillGetsFacilityAaAfterShipLoss}, {"movement reaction", oneRoundMovementEncounterExcludesParkedFleet},
        {"raider",raiderDiscoveryTiesAndSlipStayInSea}, {"joint defense",jointDefenseDisputeUsesEntitledPlayers},
        {"ship scramble",shipScrambleAndSkeletonCrewExclusion}, {"carrier scramble cargo",scrambledCarrierTakesItsAircraft},
        {"seaplane ASW",seaplaneAswBonusTargetsSubmarines}
    };
    for (const auto& [name, test] : checks) { std::cerr << "checking " << name << '\n'; test(); }
    std::cout<<"18 naval combat fixture groups passed\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
