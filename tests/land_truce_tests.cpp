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
const Id hopeh="land_china_hopeh", beiping="land_china_beiping", shantung="land_china_shantung";
const Id nanking="land_china_nanking", hainan="land_hainan", kwangtung="land_kwangtung";
void check(bool condition, const std::string& message) { if(!condition) throw std::runtime_error(message); }
bool marked(const std::map<Id,int>& flags,const Id& key){auto i=flags.find(key);return i!=flags.end()&&i->second;}
State fixture(const Id& actor="ccp",Phase phase=Phase::Combat) {
    static const auto base=loadScenario(std::filesystem::path(GWRL_SOURCE_DIR)/"game_content/scenarios/japan_china_1936");
    auto s=base.clone();s.units.clear();s.facilities.clear();s.construction.clear();s.repairs.clear();
    const auto i=std::find(s.definition->turnOrder.begin(),s.definition->turnOrder.end(),actor);
    s.clock.nationIndex=static_cast<int>(i-s.definition->turnOrder.begin());s.clock.playerTurnSerial=s.clock.nationIndex;s.clock.phase=phase;
    for(std::size_t n=0;n<s.definition->turnOrder.size();++n)s.completedTurns[s.definition->turnOrder[n]]=n<static_cast<std::size_t>(s.clock.nationIndex)?1:0;
    s.politics.chineseTruce=true;s.nations.at("ccp").atWarWith.insert("kmt");s.nations.at("kmt").atWarWith.insert("ccp");
    s.captureTurnStart();return s;
}
void add(State& s,const Id& id,const Id& owner,const Id& zone,const Id& type="infantry") {
    UnitState u;u.id=id;u.type=type;u.owner=owner;u.zone=u.turnOrigin=zone;
    u.movementAllowance=u.movementRemaining=s.definition->catalog->stats(type,0,catalogContext(s,owner,zone)).movement;
    s.units.emplace(id,std::move(u));
}
std::shared_ptr<const Rules> rules(){return std::make_shared<PoliticsRules>(std::make_shared<MovementRules>(std::make_shared<LandCombatRules>(std::make_shared<AirRules>(std::make_shared<EconomyRules>()))));}
Action select(Engine& e,const Id& kind,const std::function<bool(const Action&)>& matches=[](const Action&){return true;}){
    for(const auto& a:e.legalActions())if(a.kind==kind&&matches(a))return a;throw std::runtime_error("Missing action "+kind);
}
void choose(Engine& e,const Id& kind,const std::function<bool(const Action&)>& matches=[](const Action&){return true;}){e.step(select(e,kind,matches));}
void capitalize(Engine& e){choose(e,"politics_choose_capital",[](const Action& a){return a.parameters.require("zone").asString()==nanking&&!a.parameters.require("factory").asBool();});}
void clearNested(Engine& e){
    for(int step=0;step<100&&marked(e.state().flags,"immediate_land_battles");++step){
        if(e.state().chance){e.resolveChance();continue;}
        auto actions=e.legalActions();check(!actions.empty(),"Nested shared-zone event has no continuation");
        auto capital=std::find_if(actions.begin(),actions.end(),[](const Action& a){return a.kind=="politics_choose_capital";});
        if(capital!=actions.end()){capitalize(e);continue;}
        e.step(actions.front());
    }
    check(!marked(e.state().flags,"immediate_land_battles"),"Nested shared-zone event did not finish");
}
void restrictAdjacent(State& s,const Id& zone,const std::set<Id>& kmtZones){
    for(const auto& border:s.definition->geography.require("nodes").require(zone).require("neighbors").asArray()){
        const auto adjacent=border.require("neighbor_id").asString();if(s.territories.contains(adjacent))s.territories.at(adjacent).possessor=kmtZones.contains(adjacent)?"kmt":"ccp";
    }
}
void voluntarySharedRolesFollowTheActiveBreaker(){
    for(const auto& owner:{Id("ccp"),Id("kmt")})for(const auto& breaker:{Id("ccp"),Id("kmt")}){
        auto s=fixture(breaker);s.territories.at(hopeh).possessor=owner;
        add(s,"c","ccp",hopeh,"militia");add(s,"k","kmt",hopeh,"artillery");
        Engine e(s,rules());choose(e,"truce_break");check(e.state().battles.size()==1,"Shared combat was not queued");const auto& b=e.state().battles.begin()->second;
        check(b.attacker==breaker&&b.defender==(breaker=="ccp"?"kmt":"ccp"),"Voluntary shared combat did not use the active truce breaker as attacker");
        check(b.attackers==std::vector<Id>{breaker=="ccp"?"c":"k"}&&b.defenders==std::vector<Id>{breaker=="ccp"?"k":"c"},"Shared combat assigned units to the wrong side");
        check(b.data.require("origins").asObject().empty()&&!b.data.find("retreat_mode"),"Shared battle invented an entry origin or retreat exception");
        check(marked(e.state().flags,"immediate_land_battles"),"Mandatory shared combat did not block the surrounding phase");
    }
}
void automaticSharedRolesFollowTheActiveChineseFaction(){
    for(const auto& actor:{Id("ccp"),Id("kmt")})for(const auto& evolved:{Id("ccp"),Id("kmt")})for(const auto phase:{Phase::Production,Phase::PlaceUnits}){
        auto s=fixture(actor,phase);s.territories.at(hopeh).possessor=actor;
        add(s,"c","ccp",hopeh,"militia");add(s,"k","kmt",hopeh,"artillery");
        s.nations.at(evolved).powerStatus="major";terminateChineseTruce(s,evolved,true);
        check(!s.chance&&s.battles.size()==1,"Own-turn automatic termination did not queue combat directly");
        const auto& b=s.battles.begin()->second;
        check(b.attacker==actor&&b.defender==(actor=="ccp"?"kmt":"ccp"),"Automatic shared combat ignored the active Chinese faction");
        check(s.clock.phase==phase&&s.currentNation()==actor,"Own-turn automatic termination advanced the calendar");
    }
}
void thirdPartyAutomaticSharedRolesFollowTheLandPossessor(){
    for(const auto& actor:{Id("japan"),Id("mongolia")})
        for(const auto& possessor:{Id("ccp"),Id("kmt")})
            for(const auto& evolved:{Id("ccp"),Id("kmt")}){
                auto s=fixture(actor);s.territories.at(hopeh).possessor=possessor;
                add(s,"c","ccp",hopeh,"militia");add(s,"k","kmt",hopeh,"artillery");
                const auto before=s.clock;
                s.nations.at(evolved).powerStatus="major";terminateChineseTruce(s,evolved,true);
                check(!s.chance&&s.battles.size()==1,"Third-party automatic termination did not queue shared combat directly");
                const auto& battle=s.battles.begin()->second;
                const Id attacker=possessor=="ccp"?"kmt":"ccp";
                check(battle.defender==possessor&&battle.attacker==attacker,
                      "Third-party automatic combat did not let the land possessor defend");
                check(battle.attackers==std::vector<Id>{attacker=="ccp"?"c":"k"}&&
                      battle.defenders==std::vector<Id>{possessor=="ccp"?"c":"k"},
                      "Third-party automatic combat routed units to the wrong side");
                check(marked(battle.flags,"truce_low_morale_eliminates")==
                      (attacker=="kmt"&&evolved!="kmt")&&battle.data.require("origins").asObject().empty(),
                      "Automatic termination lost attacking minor KMT elimination or invented an attack origin");
                check(marked(s.flags,"immediate_land_battles")&&s.currentNation()==actor&&
                      s.clock.phase==before.phase&&s.clock.playerTurnSerial==before.playerTurnSerial,
                      "Third-party automatic combat advanced its surrounding turn or phase");
            }
}
void automaticTruceLowMoraleEliminatesWithoutAnEscape(){
    for(const auto& actor:{Id("japan"),Id("mongolia")})
        for(const auto& type:{Id("infantry"),Id("cavalry")})
            for(const auto& friendly: {std::set<Id>{},std::set<Id>{beiping,shantung}}){
                auto s=fixture(actor,Phase::PlaceUnits);restrictAdjacent(s,hopeh,friendly);
                s.territories.at(hopeh).possessor="ccp";s.nations.at("ccp").powerStatus="major";
                add(s,"c","ccp",hopeh,"militia");add(s,"k","kmt",hopeh,type);
                // An earlier turn's route is not a fresh origin, and adjacent
                // safe land does not override the shared-zone elimination.
                s.units.at("k").turnOrigin=beiping;s.units.at("k").route={hopeh};s.units.at("k").commitments.insert("combat_move");
                terminateChineseTruce(s,"ccp",true);
                const auto& battle=s.battles.begin()->second;
                check(marked(battle.flags,"truce_low_morale_eliminates")&&
                      battle.data.require("origins").asObject().empty(),
                      "Automatic shared-zone elimination lost its flag or invented a fresh origin");
                Engine e(s,rules(),9);e.setDiceTapeForTesting({10});const auto checkpoint=e.serialize();
                choose(e,"land_begin_battle");check(e.state().chance&&e.state().chance->dice.size()==1,
                      "Automatic termination requested an extra Low Morale die");e.resolveChance();
                check(!e.state().units.contains("k")&&e.state().units.contains("c")&&
                      !e.state().chance&&e.state().decisions.empty(),
                      "Automatic Low Morale did not eliminate the affected attacking unit directly");
                check(game::json::parse(e.serialize()).require("random").require("tape_position").asString()=="1",
                      "Automatic shared-zone elimination consumed an extra die");
                auto replayed=Engine::replay(s.definition,rules(),checkpoint,e.state().history);
                check(replayed.exactReplayIdentity()==e.exactReplayIdentity(),"Automatic Low Morale elimination replay diverged");
            }
}
void voluntaryKmtBreakUsesTheAttackingDiceInEveryRound(){
    auto s=fixture("kmt");restrictAdjacent(s,hopeh,{beiping});s.territories.at(hopeh).possessor="kmt";
    add(s,"c","ccp",hopeh,"militia");add(s,"lost","kmt",hopeh);add(s,"survivor","kmt",hopeh,"cavalry");
    Engine e(s,rules(),17);e.setDiceTapeForTesting({10,9,12,11});const auto checkpoint=e.serialize();choose(e,"truce_break");
    check(!e.state().chance&&e.state().units.size()==3,"Truce break rolled or eliminated before combat");
    choose(e,"land_begin_battle");check(e.state().chance->purpose=="land_combat_roll"&&e.state().chance->dice.size()==2,"KMT did not use one attacking die per eligible unit");
    e.resolveChance();check(!e.state().units.contains("lost")&&e.state().units.contains("survivor")&&e.state().units.at("survivor").zone==hopeh,"First-round attack 10+ did not eliminate exactly the affected unit");
    check(e.state().decisions.empty()&&e.state().chance->dice.size()==1,"KMT elimination offered an escape choice or extra morale die");
    e.resolveChance();check(e.state().chance&&e.state().chance->dice.size()==1&&e.state().battles.begin()->second.data.require("round").asInt()==2,"No-origin combat did not continue to round two");
    e.resolveChance();check(!e.state().units.contains("survivor")&&e.state().units.contains("c"),"Second-round KMT Low Morale did not eliminate on its attacking die");
    check(!e.state().chance&&e.state().decisions.empty(),"All eliminated attackers still fired or selected casualties");
    choose(e,"land_progress_battle");check(!marked(e.state().flags,"immediate_land_battles"),"Finished mandatory combat failed to release its phase");
    check(game::json::parse(e.serialize()).require("random").require("tape_position").asString()=="4","Extra preliminary morale dice were consumed");
    auto replayed=Engine::replay(s.definition,rules(),checkpoint,e.state().history);check(replayed.exactReplayIdentity()==e.exactReplayIdentity(),"Corrected KMT truce combat replay diverged");
}
void automaticTruceEliminationOverridesAnAvailableAttackOrigin(){
    auto s=fixture("kmt");s.territories.at(hopeh).possessor="ccp";s.territories.at(beiping).possessor="kmt";
    s.nations.at("ccp").powerStatus="major";add(s,"c","ccp",hopeh,"militia");add(s,"k","kmt",hopeh);
    auto& unit=s.units.at("k");unit.turnOrigin=beiping;unit.route={hopeh};unit.commitments.insert("combat_move");
    terminateChineseTruce(s,"ccp",true);
    check(landRetreatOrigins(s,s.battles.begin()->second)==std::set<Id>{beiping},
          "Automatic Low Morale fixture lost its genuinely available attack-origin retreat");
    Engine e(s,rules());e.setDiceTapeForTesting({10});choose(e,"land_begin_battle");e.resolveChance();
    check(!e.state().units.contains("k")&&e.state().decisions.empty(),
          "An available attack origin overrode the shared-zone Low Morale elimination");
}
void automaticTruceLowMoralePreservesAnAttackRollBelowTen(){
    auto s=fixture("japan");s.territories.at(hopeh).possessor="ccp";s.nations.at("ccp").powerStatus="major";
    add(s,"c","ccp",hopeh,"militia");add(s,"k","kmt",hopeh);terminateChineseTruce(s,"ccp",true);
    Engine e(s,rules());e.setDiceTapeForTesting({9,12});choose(e,"land_begin_battle");e.resolveChance();
    check(e.state().units.contains("k")&&e.state().units.at("k").zone==hopeh,
          "Automatic shared-zone Low Morale eliminated an attacking roll below10");
    e.resolveChance();check(e.state().chance&&e.state().chance->dice.size()==1&&
          e.state().battles.begin()->second.data.require("round").asInt()==2,
          "Surviving KMT attacker did not continue ordinary combat after rolling9");
}
void defendingKmtDoesNotTestLowMorale(){
    for(bool automatic:{false,true}){
        auto s=fixture(automatic?"japan":"ccp");s.territories.at(hopeh).possessor=automatic?"kmt":"ccp";
        add(s,"c","ccp",hopeh);add(s,"k","kmt",hopeh);
        if(automatic){s.nations.at("ccp").powerStatus="major";terminateChineseTruce(s,"ccp",true);}
        Engine e(s,rules());e.setDiceTapeForTesting({12,10});if(!automatic)choose(e,"truce_break");
        check(!e.state().chance,"Truce termination requested a preliminary KMT morale test");
        choose(e,"land_begin_battle");e.resolveChance();e.resolveChance();
        check(e.state().units.contains("k")&&e.state().units.at("k").zone==hopeh,"Defending KMT suffered attacking Low Morale");
    }
}
void majorAndMilitiaAreExemptFromBreakElimination(){
    for(bool automatic:{false,true})for(bool major:{false,true}){
        auto s=fixture(automatic?"japan":"kmt");s.territories.at(hopeh).possessor=automatic?"ccp":"kmt";add(s,"c","ccp",hopeh,"militia");
        add(s,"k","kmt",hopeh,major?"infantry":"militia");if(major)s.nations.at("kmt").powerStatus="major";
        if(automatic){s.nations.at("ccp").powerStatus="major";terminateChineseTruce(s,"ccp",true);}
        Engine e(s,rules());e.setDiceTapeForTesting({10,12});if(!automatic)choose(e,"truce_break");choose(e,"land_begin_battle");e.resolveChance();
        check(e.state().units.contains("k")&&e.state().units.at("k").zone==hopeh,"Major KMT or militia was subjected to break elimination");
        if(major)check(e.state().chance&&e.state().chance->dice.size()==1,"Major KMT attack did not proceed normally");
    }
}
void ordinarySharedRetreatHasNoEntryOrigin(){
    for(bool includeAircraft:{false,true}){
        auto s=fixture();restrictAdjacent(s,hopeh,{shantung});s.territories.at(hopeh).possessor="kmt";add(s,"c","ccp",hopeh);add(s,"k","kmt",hopeh,"militia");
        if(includeAircraft)add(s,"plane","ccp",hopeh,"fighter");terminateChineseTruce(s,"ccp");
        Engine e(s,rules());e.setDiceTapeForTesting({12,12,12,12,12});choose(e,"land_begin_battle");
        for(int i=0;i<5&&e.state().battles.begin()->second.data.require("round").asInt()==1;++i){
            if(e.state().chance)e.resolveChance();else{const auto actions=e.legalActions();for(const auto& a:actions)check(a.kind!="land_retreat_begin","Shared stack was allowed an invented retreat");e.step(actions.front());}
        }
        check(e.state().battles.begin()->second.data.require("round").asInt()==2,"No-origin shared stack failed to keep fighting");
        check(e.state().units.at("c").zone==hopeh,"No-origin attacker retreated or disappeared");
    }
}
void genuineCurrentTurnEntryProvidesAnOrdinaryRetreat(){
    for(bool multiStep:{false,true}){
        auto s=fixture();s.territories.at(hopeh).possessor="kmt";s.territories.at(beiping).possessor="ccp";s.territories.at(shantung).possessor="ccp";
        add(s,"c","ccp",hopeh);add(s,"entered","ccp",hopeh);add(s,"k","kmt",hopeh,"militia");
        auto& unit=s.units.at("entered");unit.turnOrigin=shantung;unit.route=multiStep?std::vector<Id>{beiping,hopeh}:std::vector<Id>{hopeh};unit.commitments.insert("combat_move");
        terminateChineseTruce(s,"ccp");const auto origin=multiStep?beiping:shantung;const auto& b=s.battles.begin()->second;
        check(b.data.require("origins").asObject().size()==1&&b.data.require("origins").require("entered").asString()==origin,"Current-turn entry lost its real adjacent approach");
        check(landRetreatOrigins(s,b)==std::set<Id>{origin},"Shared battle allowed a destination other than its real entry origin");
        Engine e(s,rules());e.setDiceTapeForTesting({12,12,12});choose(e,"land_begin_battle");e.resolveChance();e.resolveChance();
        choose(e,"land_retreat_begin");choose(e,"land_retreat_unit");choose(e,"land_retreat_unit");
        check(e.state().units.at("c").zone==origin&&e.state().units.at("entered").zone==origin,"Ordinary shared retreat did not use genuine contingent entry");
    }
}
void noOriginTerrainLimitEliminatesAttackers(){
    for(bool tundra:{false,true}){
        auto s=fixture();const auto zone=tundra?hopeh:beiping;
        if(tundra){
            auto definition=*s.definition;auto geography=definition.geography.asObject();auto nodes=geography.at("nodes").asObject();auto territory=nodes.at(zone).asObject();
            territory["terrain"]=V(V::Array{V(std::string("tundra"))});territory["is_city"]=V(false);nodes[zone]=V(std::move(territory));geography["nodes"]=V(std::move(nodes));definition.geography=V(std::move(geography));s.definition=freezeDefinition(std::move(definition));
        }
        s.territories.at(zone).possessor="kmt";add(s,"c","ccp",zone);add(s,"k","kmt",zone,"militia");terminateChineseTruce(s,"ccp");
        Engine e(s,rules());e.setDiceTapeForTesting({12,12,12,12,12,12});choose(e,"land_begin_battle");
        for(int i=0;i<(tundra?2:6);++i)e.resolveChance();
        check(!e.state().units.contains("c")&&e.state().units.contains("k")&&e.state().battles.begin()->second.data.require("result").asString()=="forced_retreat","City/tundra no-retreat elimination was lost");
    }
}
void prepareTwelveIppKmt(State& s){
    for(const auto& zone:{beiping,hopeh,Id("land_china_yunnan"),Id("land_formosa")})s.territories.at(zone).possessor="kmt";
    refreshPoliticalState(s);check(s.nations.at("kmt").gameFlags.at("possessed_land_ipp")==12,"Nested-evolution fixture does not begin at 12 IPP");
}
void evolutionDuringAnotherSlotPreservesPhase(Phase phase){
    auto s=fixture("japan",phase);prepareTwelveIppKmt(s);add(s,"c","ccp",beiping);add(s,"k","kmt",beiping,"militia");add(s,"c2","ccp",hopeh);add(s,"k2","kmt",hopeh,"militia");
    changePossession(s,hainan,"kmt",PossessionCause::Alignment);check(s.nations.at("kmt").powerStatus=="major"&&!s.politics.chineseTruce&&s.battles.size()==2,"Out-of-turn 13-IPP evolution delayed shared-zone combat");
    for(const auto& [id,b]:s.battles)check(b.defender=="kmt"&&b.attacker=="ccp","Third-party evolution lost the possessor-defends fallback");
    Engine e(s,rules(),123);e.setDiceTapeForTesting({1,12,1,12});const auto checkpoint=e.serialize();capitalize(e);const auto before=e.state().clock;const auto options=e.legalActions();
    check(options.size()==1&&options.front().kind=="land_begin_battle"&&options.front().nation=="japan"&&options.front().player=="axis","Nested battle allowed unrelated purchases, influence, phase end, or discretionary third-party ordering");
    check(options.front().parameters.require("battle").asString()==e.state().battleOrder.front(),"Mandatory event order is unstable");check(e.legalInterrupts().empty(),"Discretionary interrupt broke nested atomic resolution");clearNested(e);
    check(e.state().clock.phase==before.phase&&e.state().clock.playerTurnSerial==before.playerTurnSerial&&e.state().clock.nationIndex==before.nationIndex,"Nested combat advanced the national phase or turn");auto replayed=Engine::replay(s.definition,rules(),checkpoint,e.state().history);check(replayed.exactReplayIdentity()==e.exactReplayIdentity(),"Out-of-turn evolution combat did not replay");
}
void japaneseCaptureGiftCanEndAnExistingTruce(){
    auto s=fixture("japan",Phase::CombatMovement);
    // An existing Truce follows foreign-invasion alignment, so there must be
    // no independent warlord available for a later Japanese influence roll.
    for(const auto& [id,nation]:s.nations)if(isWarlord(id))incorporateNation(s,id,"ccp");
    s.territories.at(beiping).possessor="japan";
    for(const auto& zone:{Id("land_china_yunnan"),Id("land_formosa"),kwangtung,hainan})
        s.territories.at(zone).possessor="kmt";
    for(auto& [zone,territory]:s.territories)
        territory.flags.erase("last_possession_change_turn");
    for(const auto& faction:{Id("ccp"),Id("kmt")}){
        s.nations.at("japan").atWarWith.insert(faction);
        s.nations.at(faction).atWarWith.insert("japan");
    }
    refreshPoliticalState(s);
    check(s.nations.at("kmt").gameFlags.at("possessed_land_ipp")==12&&
          s.nations.at("kmt").powerStatus=="minor"&&s.politics.chineseTruce,
          "Chinese-land gift fixture does not begin with a legal 12-IPP KMT Truce");
    for(const auto& [id,nation]:s.nations)if(isWarlord(id))
        check(marked(nation.gameFlags,"incorporated"),"Existing Truce retained an independent warlord");
    add(s,"conqueror","japan",beiping,"medium_armor");
    add(s,"d","ccp",hopeh);
    add(s,"c","ccp",nanking,"militia");add(s,"k","kmt",nanking,"artillery");
    s.captureTurnStart();
    Engine e(s,rules(),55);e.setDiceTapeForTesting({1,12,1,12});const auto checkpoint=e.serialize();
    choose(e,"movement_route",[](const Action& a){const auto& path=a.parameters.require("path").asArray();return a.parameters.require("unit").asString()=="conqueror"&&
        path.size()==2&&path.front().asString()==beiping&&path.back().asString()==hopeh;});
    check(e.state().units.at("conqueror").movementRemaining==1,"Conquering armor has no subsequent withdrawal movement");
    choose(e,"end_phase");choose(e,"land_begin_battle");
    for(int step=0;step<30&&(e.state().decisions.empty()||
            e.state().decisions.back().kind!="politics_chinese_liberation");++step){
        if(e.state().chance)e.resolveChance();else{
            const auto actions=e.legalActions();
            auto battleAction=std::find_if(actions.begin(),actions.end(),[](const Action& a){return
                a.kind=="land_take_casualty"||a.kind=="land_progress_battle";});
            check(battleAction!=actions.end(),"Japanese capture did not reach its Chinese-land choice");e.step(*battleAction);
        }
    }
    check(e.state().territories.at(hopeh).possessor=="japan"&&e.state().politics.chineseTruce,
          "Japanese conquest did not preserve the Truce before the gift: possessor="+
          e.state().territories.at(hopeh).possessor.value_or("none")+" decision="+
          (e.state().decisions.empty()?Id("none"):e.state().decisions.back().kind));
    choose(e,"politics_give_capture",[](const Action& a){return a.parameters.require("zone").asString()==hopeh&&
        a.parameters.require("recipient").asString()=="kmt"&&a.parameters.require("requires_withdrawal").asBool();});
    check(e.state().nations.at("kmt").powerStatus=="major"&&
          e.state().nations.at("kmt").gameFlags.at("possessed_land_ipp")==13&&
          e.state().territories.at(hopeh).possessor=="kmt"&&!e.state().politics.chineseTruce,
          "Japanese Chinese-land gift did not terminate the Truce at 13 IPP");
    check(marked(e.state().units.at("conqueror").turnFlags,"must_withdraw_from_chinese_gift"),
          "Unaligned gift lost the Japanese conquering unit's withdrawal obligation");
    check(std::any_of(e.state().battles.begin(),e.state().battles.end(),[](const auto& entry){
        return entry.second.zone==nanking&&marked(entry.second.flags,"chinese_truce_termination");}),
        "Gift-triggered evolution omitted the remaining mixed Chinese stack");
    const auto before=e.state().clock;capitalize(e);clearNested(e);
    check(e.state().clock.phase==Phase::Combat&&e.state().currentNation()=="japan"&&
          e.state().clock.playerTurnSerial==before.playerTurnSerial,
          "Gift-triggered shared combat advanced Japan's current turn or phase");
    for(int step=0;step<10&&e.state().clock.phase==Phase::Combat;++step){
        const auto actions=e.legalActions();auto progress=std::find_if(actions.begin(),actions.end(),[](const Action& a){return a.kind=="land_progress_battle";});
        if(progress!=actions.end())e.step(*progress);else choose(e,"end_phase");
    }
    check(e.state().clock.phase==Phase::NonCombatMovement,"Japanese Combat did not resume after the nested reaction");
    choose(e,"movement_route",[](const Action& a){const auto& path=a.parameters.require("path").asArray();return a.parameters.require("unit").asString()=="conqueror"&&
        path.size()==2&&path.front().asString()==hopeh&&path.back().asString()==beiping;});
    check(e.state().units.at("conqueror").zone==beiping&&
          !marked(e.state().units.at("conqueror").turnFlags,"must_withdraw_from_chinese_gift"),
          "Japanese conqueror could not complete the proven friendly withdrawal");
    auto replayed=Engine::replay(s.definition,rules(),checkpoint,e.state().history);
    check(replayed.exactReplayIdentity()==e.exactReplayIdentity(),"Capture→gift→evolution→shared combat replay diverged");
}
} // namespace
int main(){try{
    voluntarySharedRolesFollowTheActiveBreaker();automaticSharedRolesFollowTheActiveChineseFaction();thirdPartyAutomaticSharedRolesFollowTheLandPossessor();automaticTruceLowMoraleEliminatesWithoutAnEscape();voluntaryKmtBreakUsesTheAttackingDiceInEveryRound();automaticTruceEliminationOverridesAnAvailableAttackOrigin();automaticTruceLowMoralePreservesAnAttackRollBelowTen();defendingKmtDoesNotTestLowMorale();majorAndMilitiaAreExemptFromBreakElimination();ordinarySharedRetreatHasNoEntryOrigin();genuineCurrentTurnEntryProvidesAnOrdinaryRetreat();noOriginTerrainLimitEliminatesAttackers();evolutionDuringAnotherSlotPreservesPhase(Phase::Production);evolutionDuringAnotherSlotPreservesPhase(Phase::CombatMovement);japaneseCaptureGiftCanEndAnExistingTruce();
    std::cout<<"15 shared-zone Chinese Truce fixture groups passed\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
