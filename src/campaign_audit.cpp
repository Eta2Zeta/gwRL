#include "game/campaign_audit.hpp"
#include "game/campaign_objective.hpp"
#include "game/air.hpp"
#include "game/catalog.hpp"
#include "game/economy.hpp"
#include "game/land_combat.hpp"
#include "game/movement.hpp"
#include "game/naval.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <fstream>
#include <numeric>
#include <stdexcept>

namespace game::campaign {
namespace {
using V = json::Value;
using O = V::Object;
using A = V::Array;
V n(int x) { return V(static_cast<double>(x)); }
int value(const std::map<Id,int> &flags, const Id &key) {
    const auto i=flags.find(key); return i==flags.end()?0:i->second;
}
bool has(const State &s,const UnitState &u,const Id &c) {
    return s.definition->catalog->unit(u.type).classes.contains(c);
}
V unitJson(const UnitState &u) {
    A cargo;for(const auto&id:u.cargo)cargo.emplace_back(id);
    return V(O{{"id",V(u.id)},{"type",V(u.type)},{"owner",V(u.owner)},{"zone",V(u.zone)},
        {"damage",n(u.damage)},{"movement",u.movementRemaining?n(*u.movementRemaining):V(nullptr)},
        {"carried_by",u.carriedBy?V(*u.carriedBy):V(nullptr)},{"cargo",V(cargo)}});
}
V clockJson(const State&s) {
    const auto[y,m]=s.calendarDate();
    return V(O{{"year",n(y)},{"month",n(m)},{"round",n(s.clock.roundIndex)},
        {"serial",V(std::to_string(s.clock.playerTurnSerial))},{"nation",V(s.currentNation())},
        {"phase",V(toString(s.clock.phase))},{"terminal",V(s.terminal)}});
}
V eventsJson(const EventLog&events,std::size_t from) {
    A out;
    for(std::size_t i=from;i<events.size();++i)
        out.emplace_back(O{{"kind",V(events[i].kind)}, {"payload",events[i].payload},
                          {"after_state_key",V(events[i].afterStateKey)}});
    return V(out);
}
std::uint64_t mix(std::uint64_t x) {
    x^=x>>30;x*=UINT64_C(0xbf58476d1ce4e5b9);x^=x>>27;x*=UINT64_C(0x94d049bb133111eb);return x^(x>>31);
}
Id text(const V&v,const Id&k,const Id&fallback={}) {const auto*p=v.find(k);return p&&p->isString()?p->asString():fallback;}
bool prefix(const Id&v,const Id&p) {return v.rfind(p,0)==0;}

double actionScore(const State&s,const Action&a,int phaseCount,std::uint64_t seed) {
    // Stable tiny jitter breaks ties without touching execution RNG.
    const auto digest=contentDigest(a.id);
    const double jitter=(mix(seed+std::stoull(digest.substr(0,12),nullptr,16))%1000)/10000.0;
    const auto &k=a.kind;
    const auto unit=text(a.parameters,"unit");
    // Preserve one exposed starting cruiser and the Chinese production city so
    // later evolved Chinese aircraft can exercise real naval combat.
    if(unit=="setup_japan_sea_p14_heavy_cruiser_1"&&(k=="naval_start_move"||k=="naval_enter_port"))return -1000+jitter;
    if(s.currentNation()=="japan"&&s.clock.roundIndex<4) {
        auto zone=text(a.parameters,"zone");
        if(const auto*p=a.parameters.find("path");p&&!p->asArray().empty())zone=p->asArray().back().asString();
        if(zone=="land_china_nanking"&&(k=="movement_route"||k=="air_ground_attack"||k=="air_support"||k=="naval_declare_assault"))return -1000+jitter;
    }
    if(k=="end_phase")return (phaseCount>=8?10000:-100)+jitter;
    if(a.decision) {
        if(k=="politics_keep_capture")return 750+jitter;
        if(k.find("cancel")!=Id::npos)return 100+jitter;
        if(k.find("remove")!=Id::npos)return -100+jitter;
        if(k=="naval_force_add")return -20+jitter;
        if(k=="naval_route"||k=="naval_screen_confirm"||k=="naval_strategic_continue")return 800+jitter;
        if(k.find("continue")!=Id::npos||k.find("accept")!=Id::npos||k.find("confirm")!=Id::npos)return 700+jitter;
        if(k.find("decline")!=Id::npos||k.find("retreat")!=Id::npos||k.find("neutral")!=Id::npos)return -10+jitter;
        if(k.find("finish")!=Id::npos)return 400+jitter;
        if(k.find("take_casualty")!=Id::npos) {
            const auto id=text(a.parameters,"unit");
            if(s.units.contains(id))return 1000-s.definition->catalog->unit(s.units.at(id).type).assetValue.value_or(0)+jitter;
        }
        if(k=="politics_choose_capital") {
            const auto zone=text(a.parameters,"zone");
            return (zone=="land_china_nanking"?1000:zone=="land_china_beiping"?900:300)+jitter;
        }
        return 300+jitter;
    }
    if(k=="economy_research")return phaseCount<2?900+jitter:100+jitter;
    if(k=="economy_finish_research")return 800+jitter;
    if(k=="economy_advance")return 750+jitter;
    if(k=="economy_purchase") {
        const auto type=s.definition->catalog->row(a.parameters.require("row").asString()).type;
        if(s.currentNation()=="japan"&&phaseCount>=5)return -20+jitter;
        if(type=="fighter")return 700+jitter;
        if(type=="infantry")return 600+jitter;
        if(type=="artillery")return 550+jitter;
        if(type=="militia")return 300+jitter;
        return -30+jitter;
    }
    if(prefix(k,"economy_place")||prefix(k,"economy_deliver")||prefix(k,"economy_complete"))return 900+jitter;
    if(k.find("recruit")!=Id::npos||prefix(k,"influence_"))return 600+jitter;
    if(prefix(k,"land_begin")||prefix(k,"land_progress")||prefix(k,"naval_begin_battle")||k=="naval_progress_battle"||k=="air_progress")return 950+jitter;
    if(k=="air_land"||k=="air_end_patrol"||k=="air_land_noncombat")return 950+jitter;
    if(k=="naval_air_attack")return 850+jitter;
    if(k=="naval_port_attack"||k=="air_ground_attack"||k=="air_support"||k=="air_bomb")return 650+jitter;
    if(k=="movement_route") {
        const auto*path=a.parameters.find("path");
        if(path&&!path->asArray().empty()) {
            const auto zone=path->asArray().back().asString();
            if(s.territories.contains(zone)&&s.territories.at(zone).possessor&&
               s.territories.at(zone).possessor!=a.nation) {
                // Keep Japan's first turn available for Dadao influence.
                if(a.nation=="japan"&&s.clock.roundIndex==0)return -30+jitter;
                return 600+jitter;
            }
        }
        return phaseCount<3?150+jitter:-50+jitter;
    }
    if(k=="naval_start_move")return phaseCount<2?200+jitter:-50+jitter;
    if(prefix(k,"naval_load")||prefix(k,"air_load"))return 250+jitter;
    if(prefix(k,"naval_declare_assault"))return 600+jitter;
    if(k=="land_select_surprise_zone") {
        const auto zone=text(a.parameters,"zone");
        return (zone=="land_china_beiping"?1100:zone=="land_china_hopeh"?1050:850)+jitter;
    }
    return (phaseCount<3?20:-200)+jitter;
}
} // namespace

std::shared_ptr<const Rules> campaignRules() {
    return std::make_shared<PoliticsRules>(std::make_shared<MovementRules>(std::make_shared<NavalRules>(
        std::make_shared<LandCombatRules>(std::make_shared<AirRules>(std::make_shared<EconomyRules>())))));
}
std::vector<std::string> campaignInvariantFailures(const State&s) {
    std::vector<std::string> out;
    try{s.validate();}catch(const std::exception&e){out.push_back(std::string("structural: ")+e.what());return out;}
    for(const auto &[id,nation]:s.nations)for(const auto&enemy:nation.atWarWith)
        if(!s.nations.at(enemy).atWarWith.contains(id))out.push_back("asymmetric war: "+id+" / "+enemy);
    std::map<Id,Id> pendingAttacks;
    for(const auto&[battleId,b]:s.battles)
        if(!value(b.flags,"finished")&&!value(b.flags,"naval_battle")&&!value(b.flags,"air_mission")&&
           !value(b.flags,"amphibious_preparation")&&!value(b.flags,"naval_movement_plan"))
            for(const auto&unit:b.attackers) {
                if(pendingAttacks.contains(unit))out.push_back("unit in two unresolved land attacks: "+unit);
                else pendingAttacks[unit]=battleId;
            }
    for(const auto &[id,u]:s.units) {
        if(!u.cargo.empty()) {
            if(has(s,u,"carrier")) {
                int occupied=0;
                for(const auto&child:u.cargo) {
                    const auto&c=s.units.at(child);occupied+=c.type=="medium_bomber"?2:1;
                    if(!isAircraft(s,c))out.push_back("non-aircraft carrier cargo: "+child);
                    if(!(has(s,c,"fighter")||c.type=="tactical_bomber"||(c.type=="medium_bomber"&&u.type=="heavy_fleet_carrier")))
                        out.push_back("ineligible carrier aircraft: "+child);
                }
                const int cap=s.definition->catalog->stats(u.type,u.damage,catalogContext(s,u.owner,u.zone)).carrierCapacity.value_or(0);
                if(occupied>cap)out.push_back("carrier over capacity: "+id);
            } else if(has(s,u,"naval")) {
                if(!navalCargoFits(s,id,u.cargo))out.push_back("illegal naval cargo: "+id);
            } else if(isAircraft(s,u)) {
                const bool airTransport=u.type=="air_transport"||u.type=="heavy_air_transport";
                const bool strategic=has(s,u,"strategic_bomber");
                if(!airTransport&&!strategic)out.push_back("non-transport aircraft carries cargo: "+id);
                const bool airborne=std::all_of(u.cargo.begin(),u.cargo.end(),[&](const auto&child){const auto&type=s.units.at(child).type;return type=="airborne_infantry"||type=="elite_airborne_infantry";});
                const int cap=u.type=="heavy_air_transport"&&airborne?2:1;
                if(static_cast<int>(u.cargo.size())>cap)out.push_back("air transport cargo exceeds mission capacity: "+id);
                if(strategic&&!airborne)out.push_back("strategic bomber carries non-airborne cargo: "+id);
                for(const auto&child:u.cargo) {
                    const auto&cargo=s.units.at(child);
                    const bool allowed=has(s,cargo,"infantry_class")||(u.type=="heavy_air_transport"&&(has(s,cargo,"artillery_class")||cargo.type=="anti_aircraft_artillery"));
                    if(!has(s,cargo,"land")||(!strategic&&!allowed))out.push_back("ineligible air cargo: "+child);
                }
            } else out.push_back("non-transport carries cargo: "+id);
        }
        if(!u.carriedBy&&has(s,u,"land")&&!s.territories.contains(u.zone))
            out.push_back("untransported land unit at sea: "+id);
        if(has(s,u,"naval")&&s.territories.contains(u.zone)) {
            bool berthed=false;
            for(const auto&[flag,on]:u.gameFlags)if(on&&prefix(flag,"in_port:")) {
                const auto facility=flag.substr(std::string("in_port:").size());
                if(s.facilities.contains(facility)&&s.facilities.at(facility).zone==u.zone)berthed=true;
            }
            if(!berthed)out.push_back("unberthed ship in a land zone: "+id);
        }
    }
    for(const auto&[id,nation]:s.nations)for(const auto&[key,amount]:nation.turnFlags)
        if(prefix(key,"economy_used:")) {
            const auto fid=key.substr(std::string("economy_used:").size());
            if(!s.facilities.contains(fid)||amount<0)out.push_back("invalid facility capacity use: "+key);
            else {
                const auto &f=s.facilities.at(fid);
                const auto ctx=catalogContext(s,id,f.zone);
                int highest=std::max(value(nation.turnFlags,"economy_production_cap:"+fid),value(nation.turnFlags,"economy_repair_cap:"+fid));
                for(const auto&[startKey,flag]:nation.turnFlags)if(flag&&prefix(startKey,"economy_start_type:"+fid+":")) {
                    const auto type=startKey.substr(("economy_start_type:"+fid+":").size());
                    const int damage=value(nation.turnFlags,"economy_start_damage:"+fid);
                    highest=std::max({highest,s.definition->catalog->productionCapacity(type,damage,ctx),s.definition->catalog->repairCapacity(type,damage,ctx)});
                }
                if(amount>highest)out.push_back("facility capacity exceeded: "+fid);
            }
        }
    if(s.terminal)for(const auto&[id,u]:s.units)
        if(value(u.turnFlags,"air_in_flight")&&!value(u.gameFlags,"on_map"))out.push_back("terminal aircraft still in flight: "+id);
    if(s.clock.phase==Phase::PlaceUnits&&s.battles.empty()&&s.decisions.empty()&&!s.chance)
        for(const auto&[id,u]:s.units)if(isAircraft(s,u)&&movementController(s,u.owner)&&
            value(u.turnFlags,"air_in_flight")&&!value(u.gameFlags,"on_map"))
            out.push_back("aircraft passed noncombat without landing: "+id);
    return out;
}
void requireCampaignInvariants(const State&s) {
    const auto failures=campaignInvariantFailures(s);
    if(!failures.empty())throw std::runtime_error("Campaign invariant: "+failures.front());
}
V campaignSnapshot(const State&s) {
    O units,land,cash,income,status,turns;A battles,decisions;
    for(const auto&[id,u]:s.units)units[id]=unitJson(u);
    for(const auto&[id,t]:s.territories)land[id]=t.possessor?V(*t.possessor):V(nullptr);
    for(const auto&[id,t]:s.nations){cash[id]=t.treasury?n(*t.treasury):V(nullptr);income[id]=n(evaluateIncome(s,id).total);status[id]=V(t.powerStatus);}
    for(const auto&[id,c]:s.completedTurns)turns[id]=n(c);
    for(const auto&[id,b]:s.battles)battles.emplace_back(O{{"id",V(id)},{"zone",V(b.zone)},{"attacker",V(b.attacker)},{"defender",V(b.defender)},{"stage",V(b.stage)}});
    for(const auto&d:s.decisions)decisions.emplace_back(O{{"kind",V(d.kind)},{"nation",V(d.nation)}});
    return V(O{{"clock",clockJson(s)},{"units",V(units)},{"territories",V(land)},{"treasuries",V(cash)},
        {"incomes",V(income)},{"power_status",V(status)},{"completed_turns",V(turns)},
        {"battles",V(battles)},{"decisions",V(decisions)},{"truce",V(s.politics.chineseTruce)},{"wealth",wealthJson(s)}});
}
CampaignAuditLog::CampaignAuditLog(const Engine&e):initialCheckpoint_(e.serialize()),initialSnapshot_(campaignSnapshot(e.state())) {
    requireCampaignInvariants(e.state());for(const auto&[id,u]:e.state().units)seenUnitIds_.insert(id);
}
void CampaignAuditLog::record(const State&before,const Engine&e,const std::string&kind,const V&input) {
    const auto&after=e.state();requireCampaignInvariants(after);
    A added,removed,changed;O possessions,cash;std::set<Id> live;
    const auto command=text(input,"kind");
    for(const auto&[id,u]:after.units) {
        live.insert(id);
        if(!before.units.contains(id)) {
            if(seenUnitIds_.contains(id))throw std::runtime_error("Removed unit ID reused: "+id);
            bool authorized=false;
            if(kind=="action"&&(command=="economy_place"||command=="economy_lease_place")) {
                const auto project=text(input.require("parameters"),"project");
                authorized=before.construction.contains(project)&&!after.construction.contains(project);
                if(authorized) {
                    const auto&type=before.construction.at(project).type;
                    authorized=type==u.type;
                    if(!authorized)for(const auto&conversion:after.definition->catalog->automaticConversions(type,catalogContext(after,u.owner,u.zone)))
                        authorized=authorized||conversion.to==u.type;
                    // The explicit elite-airborne aid rule reverts doctrine-
                    // dependent elite infantry for an unqualified recipient.
                    authorized=authorized||(type=="elite_airborne_infantry"&&u.type=="airborne_infantry"&&command=="economy_lease_place");
                }
            }
            if(kind=="action"&&command=="recruitment_place_infantry")authorized=u.type=="infantry";
            if(kind=="action"&&command=="recruitment_place_militia")authorized=u.type=="militia";
            if(prefix(id,"ship_crew_"))for(const auto&[flag,on]:u.gameFlags)if(on&&prefix(flag,"ship_crew:")) {
                const auto ship=flag.substr(std::string("ship_crew:").size());
                authorized=before.units.contains(ship)&&u.type=="militia"&&before.units.at(ship).owner==u.owner&&before.units.at(ship).zone==u.zone;
            }
            if(!authorized)throw std::runtime_error("Unit creation lacks a completed placement, recruitment choice, or ship-crew source: "+id);
            seenUnitIds_.insert(id);added.push_back(unitJson(u));
        } else if(canonicalJson(unitJson(before.units.at(id)))!=canonicalJson(unitJson(u)))changed.push_back(unitJson(u));
    }
    for(const auto&[id,u]:before.units)if(!after.units.contains(id))removed.push_back(unitJson(u));
    if(command=="economy_purchase"||command=="economy_advance") {
        const auto nation=text(input,"nation");int paid=0;
        for(const auto&[id,p]:after.construction)if(p.owner==nation)
            paid+=p.paidIpp-(before.construction.contains(id)?before.construction.at(id).paidIpp:0);
        if(!before.nations.at(nation).treasury||!after.nations.at(nation).treasury||
            *before.nations.at(nation).treasury-*after.nations.at(nation).treasury!=paid)
            throw std::runtime_error("Treasury/construction payment conservation failed for "+command);
    }
    if(!removed.empty()&&(command=="economy_purchase"||command=="economy_advance"||command=="economy_research"||command=="economy_finish_research"||command=="influence_roll"||command=="recruitment_roll"))
        throw std::runtime_error("Financial/roll-declaration action removed deployed units: "+command);
    for(const auto&[id,t]:after.territories)if(before.territories.at(id).possessor!=t.possessor)possessions[id]=t.possessor?V(*t.possessor):V(nullptr);
    for(const auto&[id,nation]:after.nations)if(!before.nations.contains(id)||before.nations.at(id).treasury!=nation.treasury)cash[id]=nation.treasury?n(*nation.treasury):V(nullptr);
    auto snapshot=campaignSnapshot(after).asObject();snapshot.erase("units");
    transitions_.emplace_back(O{{"index",n(static_cast<int>(transitions_.size()))},{"kind",V(kind)},{"input",input},
        {"before",clockJson(before)},{"after",clockJson(after)},{"unit_creation",V(added)},
        {"unit_destruction",V(removed)},{"unit_updates",V(changed)},{"possession_changes",V(possessions)},
        {"treasury_changes",V(cash)},{"events",eventsJson(after.history,before.history.size())},
        {"snapshot",V(std::move(snapshot))},{"state_key",V(after.planningKey())},
        {"invariants",V(std::string("passed"))}});
}
V CampaignAuditLog::report(const Engine&e) const {
    O kinds;int chances=0,actions=0;
    for(const auto&t:transitions_) {
        const auto type=t.require("kind").asString();
        if(type=="chance")++chances;else {++actions;const auto k=t.require("input").require("kind").asString();const auto i=kinds.find(k);kinds[k]=n(i==kinds.end()?1:i->second.asInt()+1);}
    }
    return V(O{{"schema_version",n(2)},{"scope",V(std::string("Legal combined-module integration trace; deliberately non-optimal policies, no training. Unit snapshots reconstruct from the initial snapshot plus each transition's exact creation/destruction/update deltas."))},
        {"scenario_id",V(e.state().definition->scenarioId)},{"definition_fingerprint",V(e.state().definition->fingerprint)},
        {"initial_checkpoint",V(initialCheckpoint_)},{"initial_snapshot",initialSnapshot_},{"terminal",V(e.state().terminal)},
        {"final_checkpoint",V(e.serialize())},{"final_snapshot",campaignSnapshot(e.state())},
        {"transitions",V(A(transitions_.begin(),transitions_.end()))},{"action_counts",V(kinds)},
        {"action_transitions",n(actions)},{"chance_transitions",n(chances)},
        {"invariant_checks",n(static_cast<int>(transitions_.size())+1)},
        {"exact_replay_identity",V(e.exactReplayIdentity())}});
}
void runCampaignTrace(Engine&e,CampaignAuditLog&log,const CampaignTraceOptions&options) {
    Id phase;int optional=0;
    std::map<Id,int> choices;
    for(int step=0;!e.state().terminal&&step<options.maximumTransitions;++step) {
        const auto before=e.state().clone();
        const auto marker=std::to_string(before.clock.playerTurnSerial)+":"+toString(before.clock.phase);
        if(marker!=phase){phase=marker;optional=0;choices.clear();}
        if(options.progress)options.progress(before,log.transitions().size());
        if(before.chance) {
            const auto request=before.chance->id;e.resolveChance();log.record(before,e,"chance",V(O{{"request_id",V(request)}}));continue;
        }
        if(options.delayedJapaneseWar&&before.decisions.empty()&&before.currentNation()=="japan"&&before.clock.phase==Phase::CombatMovement&&before.nations.at("kmt").powerStatus=="major") {
            const auto interrupts=e.legalInterrupts();
            const auto declaration=std::find_if(interrupts.begin(),interrupts.end(),[](const auto&a){return a.kind=="politics_declare_war"&&a.nation=="japan"&&a.parameters.require("target").asString()=="kmt";});
            if(declaration!=interrupts.end()) {const auto a=*declaration;e.interrupt(a);log.record(before,e,"interrupt",actionJson(a));continue;}
        }
        std::vector<Action> legal;
        try{legal=e.legalActions();}catch(const std::exception&error){throw std::runtime_error("Trace action enumeration at "+marker+": "+error.what());}
        if(legal.empty())throw std::runtime_error("Trace dead end at "+marker+" "+before.currentNation());
        auto best=legal.begin();double bestScore=-1e99;
        for(auto i=legal.begin();i!=legal.end();++i) {
            double score=actionScore(before,*i,optional,options.policySeed);
            if(options.delayedJapaneseWar&&before.currentNation()=="japan"&&before.nations.at("kmt").powerStatus!="major"&&before.clock.phase==Phase::CombatMovement) {
                const auto&k=i->kind;
                if(k=="movement_route"||k=="air_ground_attack"||k=="air_support"||k=="air_bomb"||k=="naval_declare_assault"||k=="naval_port_attack"||k=="naval_air_attack")score-=5000;
            }
            if(options.delayedJapaneseWar&&(i->nation=="kmt"||i->nation=="ccp")&&!before.nations.at("japan").atWarWith.contains(i->nation)) {
                auto target=text(i->parameters,"zone");
                if(const auto*path=i->parameters.find("path");path&&!path->asArray().empty())target=path->asArray().back().asString();
                if((before.territories.contains(target)&&before.territories.at(target).possessor=="japan")||i->kind=="naval_air_attack"||i->kind=="naval_port_attack")score-=5000;
            }
            const auto key=i->kind+":"+canonicalJson(i->parameters);
            score-=choices[key]*10000;
            if(i->kind=="end_phase"&&optional>=options.optionalActionsPerPhase)score+=20000;
            if(score>bestScore){bestScore=score;best=i;}
        }
        const auto a=*best;
        if(++choices[a.kind+":"+canonicalJson(a.parameters)]>20)
            throw std::runtime_error("Trace policy repeated an unchanged choice: "+a.kind+" at "+marker);
        try{e.step(a);}catch(const std::exception&error){throw std::runtime_error("Trace action "+canonicalJson(actionJson(a))+": "+error.what());}
        log.record(before,e,"action",actionJson(a));
        if(!a.decision&&a.kind!="end_phase")++optional;
    }
    if(!e.state().terminal)throw std::runtime_error("Trace exceeded transition budget");
}
void writeCampaignTrace(const std::filesystem::path&directory,const V&report) {
    std::filesystem::create_directories(directory);
    std::ofstream output(directory/"trace.json");output<<canonicalJson(report)<<'\n';
    if(!output)throw std::runtime_error("Cannot write campaign trace");
    std::ofstream html(directory/"index.html");
    html<<R"HTML(<!doctype html><meta charset="utf-8"><title>Campaign integration trace</title><style>body{font:15px system-ui;margin:2rem;background:#f7f7f3;color:#17222a}button,input{font:inherit}pre{white-space:pre-wrap;background:white;padding:1rem;border:1px solid #ddd}table{border-collapse:collapse;background:white}td,th{padding:.35rem .6rem;border:1px solid #ddd}#board{max-height:30rem;overflow:auto}.muted{color:#65717a}</style><h1>July 1936–July 1941 integration trace</h1><p class="muted">Legal shared-engine actions and actual seeded dice. These deliberately non-optimal policies are verification fixtures.</p><button id="prev">Previous</button> <input id="position" type="range" min="0" value="0"> <button id="next">Next</button> <span id="count"></span><h2 id="clock"></h2><pre id="action"></pre><div id="board"></div><h3>Transition effects and checks</h3><pre id="effects"></pre><script>const report=)HTML";
    auto json=canonicalJson(report);for(std::size_t p=0;(p=json.find("</",p))!=Id::npos;p+=3)json.replace(p,2,"<\\/");html<<json;
    html<<R"HTML(;const steps=report.transitions,slider=document.querySelector('#position');slider.max=steps.length;function show(){let i=+slider.value,t=i?steps[i-1]:null,s=t?t.snapshot:report.initial_snapshot;document.querySelector('#count').textContent=i+' / '+steps.length;document.querySelector('#clock').textContent=JSON.stringify(s.clock);document.querySelector('#action').textContent=t?JSON.stringify(t.input,null,2):'Approved initial setup';let table=document.createElement('table'),head=table.insertRow();for(let x of ['Unit','Owner','Type','Location','Damage','Carrier']){let c=document.createElement('th');c.textContent=x;head.append(c)}let units=structuredClone(report.initial_snapshot.units);for(let j=0;j<i;j++){for(let u of steps[j].unit_destruction)delete units[u.id];for(let u of [...steps[j].unit_creation,...steps[j].unit_updates])units[u.id]=u}for(let u of Object.values(units)){let r=table.insertRow();for(let x of [u.id,u.owner,u.type,u.zone,u.damage,u.carried_by||'']){let c=r.insertCell();c.textContent=x}}document.querySelector('#board').replaceChildren(table);document.querySelector('#effects').textContent=t?JSON.stringify({created:t.unit_creation,destroyed:t.unit_destruction,possessions:t.possession_changes,treasuries:t.treasury_changes,invariants:t.invariants,events:t.events},null,2):JSON.stringify(s.treasuries,null,2)}slider.oninput=show;document.querySelector('#prev').onclick=()=>{slider.value=Math.max(0,+slider.value-1);show()};document.querySelector('#next').onclick=()=>{slider.value=Math.min(steps.length,+slider.value+1);show()};show();</script>)HTML";
    if(!html)throw std::runtime_error("Cannot write campaign trace HTML");
}
} // namespace game::campaign
