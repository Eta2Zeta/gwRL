#include "game/campaign_audit.hpp"
#include "game/catalog.hpp"
#include "game/air.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <iostream>
#include <stdexcept>

namespace {
using namespace game::campaign;
void check(bool condition,const std::string&why){if(!condition)throw std::runtime_error(why);}
State initial(){static const auto s=loadScenario(std::filesystem::path(GWRL_SOURCE_DIR)/"game_content/scenarios/japan_china_1936");return s.clone();}
void authoritativeInitialStateAndDomainDiagnostics() {
    auto s=initial();requireCampaignInvariants(s);
    check(s.units.size()==99,"Initial campaign piece count changed");
    auto broken=s.clone();broken.nations.at("japan").atWarWith.insert("kmt");
    const auto warFailures=campaignInvariantFailures(broken);
    check(std::find(warFailures.begin(),warFailures.end(),"asymmetric war: japan / kmt")!=warFailures.end(),"Asymmetric war escaped domain audit");
    broken=s.clone();
    const auto i=std::find_if(broken.units.begin(),broken.units.end(),[&](const auto&p){return broken.definition->catalog->unit(p.second.type).classes.contains("land");});
    check(i!=broken.units.end(),"No land unit in setup");
    i->second.zone="sea_p14";
    const auto cargoFailures=campaignInvariantFailures(broken);
    check(std::find(cargoFailures.begin(),cargoFailures.end(),"untransported land unit at sea: "+i->first)!=cargoFailures.end(),"Untransported land unit at sea escaped audit");
    broken=s.clone();auto&carrier=broken.units.at("japan_light_carrier_p15_setup_1");
    auto extra=broken.units.at(carrier.cargo.front());extra.id="extra_carrier_fighter";extra.carriedBy=carrier.id;
    broken.units[extra.id]=extra;carrier.cargo.push_back(extra.id);
    const auto carrierFailures=campaignInvariantFailures(broken);
    check(std::find(carrierFailures.begin(),carrierFailures.end(),"carrier over capacity: "+carrier.id)!=carrierFailures.end(),"Carrier overbooking escaped audit");
    broken=s.clone();auto&fighter=broken.units.at("setup_japan_land_jap_tokyo_fighter_1");
    auto&cargo=broken.units.at("setup_japan_land_jap_tokyo_infantry_1");fighter.cargo.push_back(cargo.id);cargo.carriedBy=fighter.id;
    const auto aircraftFailures=campaignInvariantFailures(broken);
    check(std::find(aircraftFailures.begin(),aircraftFailures.end(),"non-transport aircraft carries cargo: "+fighter.id)!=aircraftFailures.end(),"Fighter carrying land cargo escaped audit");
    broken=s.clone();const Id factory="setup_japan_tokyo_major_factory";
    broken.nations.at("japan").turnFlags["economy_production_cap:"+factory]=5;
    broken.nations.at("japan").turnFlags["economy_used:"+factory]=6;
    const auto capacityFailures=campaignInvariantFailures(broken);
    check(std::find(capacityFailures.begin(),capacityFailures.end(),"facility capacity exceeded: "+factory)!=capacityFailures.end(),"Excess facility use escaped audit");
}
void transitionAuditAndExactReplay() {
    auto s=initial();auto rules=campaignRules();auto e=Engine::start(s,rules,1936);CampaignAuditLog log(e);
    const auto checkpoint=e.serialize();
    for(int count=0;count<5;++count) {
        const auto before=e.state().clone();const auto actions=e.legalActions();
        const auto end=std::find_if(actions.begin(),actions.end(),[](const auto&a){return a.kind=="end_phase";});
        check(end!=actions.end(),"First CCP turn cannot pass a legal phase");
        const auto action=*end;e.step(action);log.record(before,e,"action",actionJson(action));
    }
    const auto report=log.report(e);check(report.require("transitions").asArray().size()==5,"Audit lost an input transition");
    const auto replay=Engine::replay(s.definition,rules,checkpoint,e.state().history);
    check(replay.exactReplayIdentity()==e.exactReplayIdentity(),"Recorded first national turn does not replay");
    check(e.state().completedTurns.at("ccp")==1,"Five legal phases failed to finish first national turn");
}
void carpetBombingParticipatesOnceAndCannotBeHitByInfantry() {
    // Conditional capability fixture, not a fabricated continuation of the
    // July1936 setup: explicit units/technology isolate RB10.6.5 at the engine.
    auto s=initial();s.units.clear();s.facilities.clear();s.construction.clear();s.repairs.clear();
    s.clock.nationIndex=2;s.clock.playerTurnSerial=2;s.clock.phase=Phase::CombatMovement;
    s.completedTurns["ccp"]=s.completedTurns["mongolia"]=1;
    s.nations.at("japan").atWarWith.insert("kmt");s.nations.at("kmt").atWarWith.insert("japan");
    const Id origin="land_china_beiping",target="land_china_hopeh";
    s.territories.at(origin).possessor="japan";s.territories.at(target).possessor="kmt";
    auto add=[&](const Id&id,const Id&type,const Id&owner,const Id&zone){
        UnitState u;u.id=id;u.type=type;u.owner=owner;u.zone=u.turnOrigin=zone;
        u.movementAllowance=u.movementRemaining=s.definition->catalog->stats(type,0,catalogContext(s,owner,zone)).movement;s.units[id]=u;
    };
    add("carpet_bomber","heavy_strategic_bomber","japan",origin);
    add("ordinary_aircraft","tactical_bomber","japan",origin);
    add("attacker_a","infantry","japan",origin);add("attacker_b","infantry","japan",origin);
    add("defender_a","infantry","kmt",target);add("defender_b","infantry","kmt",target);s.captureTurnStart();
    auto rules=campaignRules();
    const auto beforeTechnology=AirRules{}.actions(s);
    check(std::none_of(beforeTechnology.begin(),beforeTechnology.end(),[](const auto&a){return a.kind=="air_ground_attack"&&a.parameters.require("unit").asString()=="carpet_bomber";}),"Carpet bombing became available without Heavy Strategic Bombers technology");
    s.nations.at("japan").technologyStages["heavy_strategic_bombers"]=4;
    Engine e(s,rules,68);e.setDiceTapeForTesting({12,12,12,12,12,12,12,12,1,12,12,12,12,12});
    const auto checkpoint=e.serialize();CampaignAuditLog log(e);
    auto choose=[&](const Id&kind,const Id&unit=Id{}){
        const auto options=e.legalActions();
        const auto action=std::find_if(options.begin(),options.end(),[&](const auto&a){
            if(a.kind!=kind)return false;
            if(!unit.empty()&&(!a.parameters.find("unit")||a.parameters.require("unit").asString()!=unit))return false;
            if(kind=="air_land"&&a.parameters.require("destination").asString()!=origin)return false;
            const auto*path=a.parameters.find("path");return !path||(path->asArray().size()==2&&path->asArray().back().asString()==target);
        });
        check(action!=options.end(),"Conditional carpet fixture lacks legal action "+kind);
        const auto a=*action;const auto before=e.state().clone();e.step(a);log.record(before,e,"action",actionJson(a));
    };
    auto chance=[&]{const auto before=e.state().clone();e.resolveChance();log.record(before,e,"chance",game::json::Value(game::json::Value::Object{}));};
    choose("air_ground_attack","carpet_bomber");choose("air_support","ordinary_aircraft");choose("movement_route","attacker_a");choose("movement_route","attacker_b");choose("end_phase");choose("land_begin_battle");
    check(e.state().chance&&e.state().chance->dice.size()==8,"Carpet bombing failed to combine five bomber dice with two infantry and one tactical-bomber die");
    const auto battle=e.state().chance->continuation;
    int carpetDice=0;for(const auto&shot:e.state().battles.at(battle).data.require("shots").asArray())
        if(shot.require("unit").asString()=="carpet_bomber") {++carpetDice;check(shot.require("threshold").asInt()==2&&shot.require("land_only").asBool(),"Carpet bombing changed its at2 land-only attack");}
    check(carpetDice==5,"Heavy carpet bombing did not roll exactly five dice");chance();
    check(e.state().chance&&e.state().chance->dice.size()==2,"Ordinary infantry defenders lost simultaneous fire");
    for(const auto&shot:e.state().battles.at(battle).data.require("shots").asArray())
        for(const auto&id:shot.require("eligible").asArray())check(id.asString()!="carpet_bomber","Ordinary infantry were allowed to hit a carpet bomber");
    chance();
    for(const auto&a:e.legalActions())if(a.kind=="land_take_casualty")check(a.parameters.require("unit").asString()!="carpet_bomber","Carpet bomber offered as ordinary infantry casualty");
    choose("land_take_casualty","attacker_a");
    check(!e.state().decisions.empty()&&e.state().decisions.back().kind=="air_landing","Carpet bomber did not return immediately after round1 before the next-round choice");
    const auto returning=e.serialize();
    const auto clone=e.clone();const auto restored=Engine::restore(s.definition,rules,returning);
    check(clone.exactReplayIdentity()==e.exactReplayIdentity()&&restored.exactReplayIdentity()==e.exactReplayIdentity(),"Pending first-round carpet return lost clone/checkpoint/RNG identity");
    choose("air_land","carpet_bomber");
    check(e.state().units.at("carpet_bomber").zone==origin&&e.state().units.at("ordinary_aircraft").zone==target,"Carpet return moved other aircraft or waited for battle end");
    choose("land_progress_battle");choose("land_continue_fighting");
    check(e.state().chance&&e.state().chance->dice.size()==2,"Round2 did not retain ordinary infantry/aircraft while excluding carpet bombing");
    check(std::find(e.state().battles.at(battle).attackers.begin(),e.state().battles.at(battle).attackers.end(),"carpet_bomber")==e.state().battles.at(battle).attackers.end(),"Carpet bomber remained a round2 combat participant");
    chance();chance();choose("land_retreat_begin");choose("land_retreat_unit","attacker_b");
    choose("air_land","ordinary_aircraft");
    for(int count=0;count<3&&!e.state().battles.empty();++count)choose("land_progress_battle");
    check(e.state().battles.empty()&&e.state().units.at("carpet_bomber").zone==origin&&e.state().territories.at(target).possessor=="kmt","Conditional carpet combat did not return the bomber and preserve uncaptured land");
    const auto replay=Engine::replay(s.definition,rules,checkpoint,e.state().history);
    check(replay.exactReplayIdentity()==e.exactReplayIdentity(),"Carpet bombing combined-engine trace replay diverged");
}
void creationRequiresAnExplicitRuleSource() {
    auto s=initial();auto rules=campaignRules();auto e=Engine::start(s,rules,1);CampaignAuditLog audit(e);
    const auto before=e.state().clone();auto changed=before.clone();
    auto invented=changed.units.begin()->second;invented.id="unfunded_duplicate";invented.cargo.clear();invented.carriedBy.reset();
    changed.units[invented.id]=invented;Engine illegal(changed,rules,1);
    bool rejected=false;
    try{audit.record(before,illegal,"action",game::json::Value(game::json::Value::Object{{"kind",game::json::Value(std::string("end_phase"))}}));}
    catch(const std::exception&error){rejected=std::string(error.what()).find("Unit creation lacks")!=std::string::npos;}
    check(rejected,"Audit allowed a new unit without placement, recruitment, or temporary ship-crew source");
    check(audit.transitions().empty(),"Rejected creation was recorded as a successful transition");
}
void randomLegalChoicesPreserveDomainAndReplay() {
    auto base=initial();auto rules=campaignRules();
    for(const auto seed:{1u,17u,89u}) {
        auto e=Engine::start(base.clone(),rules,seed);const auto checkpoint=e.serialize();CampaignAuditLog audit(e);
        std::uint64_t policy=seed;Id phase;int count=0;
        for(int step=0;step<80&&!e.state().terminal;++step) {
            const auto before=e.state().clone();
            if(before.chance){const auto request=before.chance->id;e.resolveChance();audit.record(before,e,"chance",game::json::Value(game::json::Value::Object{{"request_id",game::json::Value(request)}}));continue;}
            policy=policy*UINT64_C(6364136223846793005)+UINT64_C(1442695040888963407);
            const auto current=std::to_string(before.clock.playerTurnSerial)+toString(before.clock.phase);
            if(current!=phase){phase=current;count=0;}
            const auto interrupts=e.legalInterrupts();
            if(!interrupts.empty()&&policy%7==0){const auto a=interrupts[(policy>>8)%interrupts.size()];e.interrupt(a);audit.record(before,e,"interrupt",actionJson(a));continue;}
            const auto actions=e.legalActions();check(!actions.empty(),"Random legal stress reached a campaign dead end");
            auto action=actions[(policy>>8)%actions.size()];
            if(before.decisions.empty()&&count>=4){const auto end=std::find_if(actions.begin(),actions.end(),[](const auto&a){return a.kind=="end_phase";});if(end!=actions.end())action=*end;}
            e.step(action);audit.record(before,e,"action",actionJson(action));if(before.decisions.empty())++count;
        }
        check(audit.transitions().size()==80,"Random legal stress did not execute its bounded transition budget");
        const auto replay=Engine::replay(base.definition,rules,checkpoint,e.state().history);
        check(replay.exactReplayIdentity()==e.exactReplayIdentity(),"Random legal action/chance/interrupt trace replay diverged");
    }
}
}
int main(){try{authoritativeInitialStateAndDomainDiagnostics();transitionAuditAndExactReplay();carpetBombingParticipatesOnceAndCannotBeHitByInfantry();creationRequiresAnExplicitRuleSource();randomLegalChoicesPreserveDomainAndReplay();std::cout<<"Campaign integration: 5 fixture groups passed\n";return 0;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
