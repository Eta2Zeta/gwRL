#include "game/politics.hpp"
#include "game/economy.hpp"
#include "game/air.hpp"
#include "game/catalog.hpp"

#include <algorithm>
#include <deque>
#include <limits>
#include <numeric>
#include <stdexcept>

namespace game::campaign {
namespace {
using V=json::Value;
using O=V::Object;
using A=V::Array;
void require(bool condition,const std::string& message) {if(!condition)throw std::runtime_error(message);}
bool marked(const std::map<Id,int>& flags,const Id& key) {
    const auto it=flags.find(key);return it!=flags.end()&&it->second!=0;
}
bool chinese(const Id& nation) {return nation=="ccp"||nation=="kmt"||nation=="dadao"||isWarlord(nation);}
bool hasUnits(const State& s,const Id& nation) {
    return std::any_of(s.units.begin(),s.units.end(),[&](const auto& item){return item.second.owner==nation;});
}
Id uniqueContinuation(State& s,const Id& kind) {
    auto& n=s.flags["politics_sequence"];
    require(n<std::numeric_limits<int>::max(),"Political event sequence overflow");
    return kind+"_"+std::to_string(++n);
}
void refreshUnitMovement(State& s,UnitState& unit) {
    const auto allowance=s.definition->catalog->stats(unit.type,unit.damage,catalogContext(s,unit.owner,unit.zone)).movement;
    const int used=unit.movementAllowance&&unit.movementRemaining?std::max(0,*unit.movementAllowance-*unit.movementRemaining):0;
    unit.movementAllowance=allowance;
    if(allowance)unit.movementRemaining=marked(unit.turnFlags,"placed_this_turn")?0:std::max(0,*allowance-used);
}
void warPair(State& s,const Id& first,const Id& second) {
    if(first==second)return;
    s.nations.at(first).atWarWith.insert(second);s.nations.at(second).atWarWith.insert(first);
}
void releaseDecision(State& s,const Action& action) {
    require(action.decision&& !s.decisions.empty()&&s.decisions.back().id==*action.decision,"Missing political choice");
    erasePoliticalContinuation(s,s.decisions.back().continuation);s.decisions.pop_back();
}
void chooseEvolution(State& s,const Id& nation) {
    if(s.politics.evolutionAwarded.contains(nation))return;
    const auto key="evolution_pending_"+nation;
    if(marked(s.flags,key))return;
    std::vector<Action> options;
    for(const auto& zone:possessedLand(s,nation)) {
        for(bool factory:{false,true})options.push_back(politicalAction(s,nation,"politics_choose_capital",
            V(O{{"zone",V(zone)},{"factory",V(factory)}})));
    }
    require(!options.empty(),"Evolving nation has no capital choice");
    s.flags[key]=1;
    queuePoliticalDecision(s,nation,"politics_evolution",std::move(options));
}
void queueObjectiveBonus(State& s) {
    if(!s.nations.contains("ccp"))return;
    auto& ccp=s.nations.at("ccp");
    if(!marked(ccp.gameFlags,"one_china_bonus_eligible_at_surrender")||marked(ccp.gameFlags,"one_china_bonus_awarded"))return;
    for(const auto& [type,count]:std::vector<std::pair<Id,int>>{{"cavalry",3},{"infantry",2}}) {
        for(int i=0;i<count;++i) {
            BuildProject award;award.id=uniqueContinuation(s,"one_china_award");award.owner="ccp";award.type=type;
            award.flags["completed"]=1;award.flags["national_objective_award"]=1;
            s.construction.emplace(award.id,std::move(award));
        }
    }
    ccp.gameFlags["one_china_bonus_awarded"]=1;
}

std::vector<Id> nearestFriendlyLand(const State& s,const Id& owner,const Id& origin) {
    const auto& nodes=s.definition->geography.require("nodes");
    std::deque<Id> queue{origin};std::map<Id,int> distances{{origin,0}};
    std::vector<Id> destinations;int nearest=std::numeric_limits<int>::max();
    while(!queue.empty()) {
        const auto zone=queue.front();queue.pop_front();const int distance=distances.at(zone);
        if(distance>nearest)break;
        if(zone!=origin&&s.territories.contains(zone)) {
            const auto possessor=s.territories.at(zone).possessor;
            if(possessor&&politicallyFriendly(s,owner,*possessor)) {destinations.push_back(zone);nearest=distance;continue;}
        }
        if(distance>=nearest)continue;
        for(const auto& edge:nodes.require(zone).require("neighbors").asArray()) {
            const auto next=edge.require("neighbor_id").asString();
            if(nodes.find(next)&&!distances.contains(next)) {distances[next]=distance+1;queue.push_back(next);}
        }
    }
    std::sort(destinations.begin(),destinations.end());return destinations;
}
void relocateNeutralUnit(State& s,const Id& unit,const Id& destination) {
    auto& u=s.units.at(unit);u.zone=destination;
    // RB0.3 is a forced relocation, not a normal move or an aircraft flight.
    // Ownership, damage, cargo and the owner's unused movement remain intact.
    for(const auto& cargo:u.cargo)s.units.at(cargo).zone=destination;
}
void destroyUnrelocatableNeutralUnit(State& s,const Id& unit,const Id& origin) {
    // RCL-015 is the adopted campaign consequence, not a printed destruction
    // rule. Use the shared removal path so cargo, repairs and battle references
    // cannot survive the destroyed unit.
    std::set<Id> removed{unit};bool changed=true;
    while(changed) {
        changed=false;
        for(const auto& [id,u]:s.units)
            if(u.carriedBy&&removed.contains(*u.carriedBy))changed=removed.insert(id).second||changed;
    }
    A destroyed;
    for(const auto& id:removed) {
        const auto& u=s.units.at(id);
        destroyed.emplace_back(O{{"id",V(id)},{"type",V(u.type)},{"owner",V(u.owner)},
            {"zone",V(u.zone)},{"carried_by",u.carriedBy?V(*u.carriedBy):V(nullptr)}});
    }
    removePoliticalUnits(s,removed);
    refreshPoliticalState(s);
    s.history.push_back(Event{"unit_destruction",V(O{{"rule",V(std::string("RCL-015"))},
        {"authority",V(std::string("user_adopted_campaign_interpretation"))},
        {"reason",V(std::string("no_friendly_land_destination"))},
        {"origin",V(origin)},{"unit",V(unit)},{"units",V(std::move(destroyed))}}),s.planningKey()});
}
void continueNeutralRelocation(State& s,const Id& key) {
    auto context=s.politics.pending.at(key).asObject();auto units=context.at("units").asArray();
    const auto origin=context.at("origin").asString();
    while(!units.empty()) {
        const auto id=units.front().asString();
        if(!s.units.contains(id)||s.units.at(id).zone!=origin) {units.erase(units.begin());continue;}
        const auto owner=s.units.at(id).owner;
        const auto destinations=nearestFriendlyLand(s,owner,origin);
        if(destinations.empty()) {
            const bool friendlyLandExists=std::any_of(s.territories.begin(),s.territories.end(),[&](const auto& item) {
                return item.second.possessor&&politicallyFriendly(s,owner,*item.second.possessor);
            });
            require(!friendlyLandExists,"Cannot determine nearest neutral relocation destination from disconnected geography");
            destroyUnrelocatableNeutralUnit(s,id,origin);units.erase(units.begin());continue;
        }
        if(destinations.size()==1) {relocateNeutralUnit(s,id,destinations.front());units.erase(units.begin());continue;}
        context["units"]=V(units);s.politics.pending[key]=V(context);
        std::vector<Action> options;
        for(const auto& zone:destinations)options.push_back(politicalAction(s,owner,"politics_relocate_neutral",
            V(O{{"relocation",V(key)},{"unit",V(id)},{"zone",V(zone)}})));
        queuePoliticalDecision(s,owner,"politics_neutral_relocation",std::move(options));return;
    }
    s.politics.pending.erase(key);
}
void queueNeutralRelocation(State& s,const Id& origin,const std::vector<Id>& units) {
    if(units.empty())return;A pending;for(const auto& id:units)pending.emplace_back(id);
    const auto key=uniqueContinuation(s,"neutral_land_relocation");
    s.politics.pending[key]=V(O{{"origin",V(origin)},{"units",V(pending)}});continueNeutralRelocation(s,key);
}

bool ownCapital(const State& s,const Id& nation) {
    const auto it=s.politics.capitals.find(nation);
    return it!=s.politics.capitals.end()&&s.territories.at(it->second).possessor==nation;
}
void commitDeclaration(State& s,const Id& actor,const Id& target) {
    if(actor=="japan"&&s.nations.at(target).alliance=="allies"&&s.nations.at(target).powerStatus=="major"&&!marked(s.nations.at(actor).gameFlags,"first_allies_major_war_declared")) {
        s.nations.at(actor).gameFlags["first_allies_major_war_declared"]=1;
        s.nations.at(actor).turnFlags["surprise_attack_available"]=1;
        s.nations.at(actor).turnFlags["surprise_attack_target:"+target]=1;
    }
    warPair(s,actor,target);
    // Sharing an alliance alone grants neither passage nor combined defense.
    // Its separate alignment condition is a common Major-Power enemy.
    for(auto& [id,n]:s.nations) {
        if(id==actor||!n.alliance||n.alliance!=s.nations.at(actor).alliance)continue;
        if(n.atWarWith.contains(target)&&s.nations.at(target).powerStatus=="major") {
            n.allies.insert(actor);s.nations.at(actor).allies.insert(id);
        }
    }
    refreshPoliticalState(s);
}
void queueDeclarationPriority(State& s,const Id& actor,const Id& target) {
    const auto active=s.currentNation();
    std::vector<Action> options;
    for(const auto& [nation,n]:s.nations) {
        if(nation!=active&&(!n.alliance||n.alliance!=s.nations.at(active).alliance))continue;
        for(const auto& [enemy,e]:s.nations)if(mayDeclareWar(s,nation,enemy).allowed) {
            options.push_back(politicalAction(s,active,"politics_priority_declare",
                V(O{{"declaring_nation",V(nation)},{"target",V(enemy)}})));
        }
    }
    options.push_back(politicalAction(s,active,"politics_priority_decline"));
    queuePoliticalDecision(s,active,"politics_declaration_priority",std::move(options),
        V(O{{"actor",V(actor)},{"target",V(target)}}));
}
}

bool isWarlord(const Id& nation) {return nation.rfind("warlord_",0)==0;}
void refreshPoliticalUnitMovement(State& s,const Id& owner) {
    for(auto& [id,unit]:s.units)if(unit.owner==owner)refreshUnitMovement(s,unit);
}
void queuePoliticalObjectiveBonus(State& s) { queueObjectiveBonus(s); }
Id originalNation(const State& s,const Id& zone) {
    const auto* index=s.definition->rules.find("faction_index");
    if(index)return index->require("land_original_owners").require(zone).require("original_faction_id").asString();
    const auto& original=s.definition->geography.require("nodes").require(zone).require("original_owner").asString();
    if(s.definition->factions.contains(original))return original;
    for(const auto& [id,f]:s.definition->factions)if(f.displayName==original)return id;
    throw std::runtime_error("Unresolved original nationality: "+zone);
}
std::vector<Id> possessedLand(const State& s,const Id& nation) {
    std::vector<Id> out;for(const auto& [id,t]:s.territories)if(t.possessor==nation)out.push_back(id);return out;
}
std::vector<Id> originalLand(const State& s,const Id& nation) {
    std::vector<Id> out;for(const auto& [id,t]:s.territories)if(originalNation(s,id)==nation)out.push_back(id);return out;
}
bool passableLandBorder(const State& s,const Id& from,const Id& to) {
    const auto& nodes=s.definition->geography.require("nodes");
    if(!s.territories.contains(from)||!s.territories.contains(to))return false;
    for(const auto& edge:nodes.require(from).require("neighbors").asArray()) {
        if(edge.require("neighbor_id").asString()!=to)continue;
        if(const auto* passable=edge.find("passable"))if(passable->isBool()&&!passable->asBool())return false;
        const auto* terrain=edge.find("border_terrain");
        if(terrain&&terrain->isString()&&terrain->asString()=="impassable")return false;
        if(terrain&&terrain->isArray())for(const auto& x:terrain->asArray())if(x.asString()=="impassable")return false;
        if(const auto* impassable=edge.find("impassable"))if(impassable->isBool()&&impassable->asBool())return false;
        return true;
    }return false;
}
bool controlledBy(const State& s,const Id& minor,const Id& controller) {
    const auto it=s.nations.find(minor);
    return it!=s.nations.end()&&minor!=controller&&it->second.controllerNation==controller
        &&!marked(it->second.gameFlags,"incorporated")&&!s.politics.surrendered.contains(minor);
}
bool atWarWithMajor(const State& s,const Id& nation) {
    for(const auto& other:s.nations.at(nation).atWarWith)if(s.nations.at(other).powerStatus=="major")return true;
    return false;
}
bool politicallyFriendly(const State& s,const Id& a,const Id& b) {
    if(a==b)return true;
    if(s.politics.chineseTruce&&((a=="ccp"&&b=="kmt")||(a=="kmt"&&b=="ccp")))return true;
    const auto& first=s.nations.at(a);const auto& second=s.nations.at(b);
    if(first.atWarWith.contains(b))return false;
    if(controlledBy(s,a,b)||controlledBy(s,b,a))return false; // control grants named permissions, not alignment
    if(first.alliance!=second.alliance||!first.alliance)return false;
    // Ordinary minor alignment incorporates that nation; it does not create a
    // second, independent friendly army. Mongolia's named recipient is absent
    // in this profile, so shared Comintern control grants no substitute link.
    if(first.powerStatus!="major"||second.powerStatus!="major")return false;
    for(const auto& enemy:first.atWarWith)if(second.atWarWith.contains(enemy)&&s.nations.at(enemy).powerStatus=="major")return true;
    return false;
}
bool chineseHomeCountry(const State& s,const Id& zone) {
    const auto& f=s.definition->factions.at("ccp");return f.homeCountryKnown&&f.homeCountry.contains(zone);
}
bool decentralizedProduction(const State& s,const Id& nation) {
    if(nation!="ccp"&&nation!="kmt")return false;
    const auto& n=s.nations.at(nation);if(n.powerStatus!="major")return true;
    const auto it=n.gameFlags.find("evolved_turn_serial");
    return s.currentNation()==nation&&marked(n.gameFlags,"evolved_during_own_turn")
        &&it!=n.gameFlags.end()&&it->second==static_cast<int>(s.clock.playerTurnSerial);
}
Id politicalPlayer(const State& s,const Id& nation) {
    const auto& n=s.nations.at(nation);if(n.player)return *n.player;
    if(n.controllerNation)return politicalPlayer(s,*n.controllerNation);
    if(const auto it=s.politics.pending.find("warlord_defense_player:"+nation);it!=s.politics.pending.end()) {
        const auto player=it->second.asString();require(s.definition->players.contains(player),"Invalid temporary warlord defense player");return player;
    }
    throw std::runtime_error("Political nation has no controlling player: "+nation);
}
void addPoliticalUnit(State& s,const Id& nation,const Id& type,const Id& zone,int count) {
    require(count>0&&s.territories.at(zone).possessor==nation,"Invalid political unit placement");
    for(int i=0;i<count;++i) {
        UnitState u;u.id=uniqueContinuation(s,"political_"+type);u.type=type;u.owner=nation;u.zone=zone;u.turnOrigin=zone;
        u.movementAllowance=s.definition->catalog->stats(type,0,catalogContext(s,nation,zone)).movement;
        u.movementRemaining=0;u.turnFlags["placed_this_turn"]=1;s.units.emplace(u.id,std::move(u));
    }
}
void removePoliticalUnits(State& s,const std::set<Id>& ids) {
    auto removed=ids;bool changed=true;
    while(changed) {changed=false;for(const auto& [id,u]:s.units)if(u.carriedBy&&removed.contains(*u.carriedBy))changed=removed.insert(id).second||changed;}
    for(const auto& id:removed)s.units.erase(id);
    for(auto& [id,u]:s.units)u.cargo.erase(std::remove_if(u.cargo.begin(),u.cargo.end(),[&](const auto& item){return removed.contains(item);}),u.cargo.end());
    for(auto it=s.repairs.begin();it!=s.repairs.end();)if(removed.contains(it->second.target))it=s.repairs.erase(it);else ++it;
    for(auto& [id,b]:s.battles)for(auto* group:{&b.attackers,&b.defenders})group->erase(std::remove_if(group->begin(),group->end(),[&](const auto& x){return removed.contains(x);}),group->end());
}
void ensureDadao(State& s) {
    if(s.nations.contains("dadao"))return;
    require(s.definition->factions.contains("dadao"),"Definition lacks dormant Dadao identity");
    NationState n;n.controllerNation="japan";n.player=politicalPlayer(s,"japan");n.alliance="axis";n.incomeKnown=true;
    s.nations.emplace("dadao",std::move(n));
}
void incorporateNation(State& s,const Id& minor,const Id& recipient) {
    require(minor!=recipient&&s.nations.contains(minor)&&s.nations.contains(recipient),"Invalid faction incorporation");
    require(minor!="ccp"&&minor!="kmt"&&s.nations.at(minor).powerStatus!="major",
            "Chinese national factions and Major Powers retain their identities");
    require(!s.politics.surrendered.contains(recipient),"Cannot align with a surrendered nation");
    for(auto& [zone,t]:s.territories)if(t.possessor==minor) {
        t.possessor=recipient;t.flags["last_possession_change_turn"]=static_cast<int>(s.clock.playerTurnSerial);
    }
    for(auto& [id,u]:s.units)if(u.owner==minor) {
        u.owner=recipient;
        refreshUnitMovement(s,u);
    }
    for(auto& [id,b]:s.construction)if(b.owner==minor)b.owner=recipient;
    auto& old=s.nations.at(minor);const auto oldWars=old.atWarWith;
    old.gameFlags["incorporated"]=1;old.controllerNation=recipient;old.player=s.nations.at(recipient).player;
    old.alliance=s.nations.at(recipient).alliance;
    // Incorporation retires the minor's independent relations. The recipient
    // inherits hostile relations, not a war against itself, its controller, or
    // members of its own alliance (notably a warlord joining Axis Dadao after
    // Japan's invasion). Preserve wars with genuinely opposing nations.
    for(auto& [id,nation]:s.nations)nation.atWarWith.erase(minor);
    old.atWarWith.clear();
    for(const auto& other:oldWars) {
        if(other==recipient||other==minor)continue;
        const auto& target=s.nations.at(other);const auto& receiving=s.nations.at(recipient);
        if((receiving.alliance&&receiving.alliance==target.alliance)||
            controlledBy(s,recipient,other)||controlledBy(s,other,recipient))continue;
        warPair(s,recipient,other);
    }
    s.politics.pending.erase("warlord_defense_player:"+minor);
}
Action politicalAction(const State& s,const Id& nation,const Id& kind,V parameters,const std::optional<Id>& decision) {
    Action a;a.kind=kind;a.nation=nation;a.player=politicalPlayer(s,nation);a.parameters=std::move(parameters);a.decision=decision;
    a.id=kind+"_"+nation+"_"+contentDigest(canonicalJson(a.parameters)).substr(0,16);return a;
}
void queuePoliticalDecision(State& s,const Id& nation,const Id& kind,std::vector<Action> options,V continuation) {
    require(!options.empty(),"Political decision needs an option");
    Decision d;d.id=uniqueContinuation(s,kind);d.kind=kind;d.nation=nation;d.reaction=nation!=s.currentNation();d.continuation=d.id;
    s.politics.pending[d.continuation]=std::move(continuation);
    for(auto& option:options){option.nation=nation;option.player=politicalPlayer(s,nation);option.decision=d.id;}
    d.options=std::move(options);s.decisions.push_back(std::move(d));
}
void requestPoliticalRoll(State& s,const Id& nation,const Id& kind,int sides,V parameters,int dice) {
    require(!s.chance&&dice>0,"Political chance is already pending or empty");
    ChanceRequest c;c.id=uniqueContinuation(s,kind);c.purpose=kind;c.nation=nation;c.continuation=c.id;
    for(int i=0;i<dice;++i)c.dice.push_back(DieSpec{sides,0,{},0});
    s.politics.pending[c.continuation]=std::move(parameters);s.chance=std::move(c);
}
const V& pendingPolitical(const State& s,const Id& continuation) {return s.politics.pending.at(continuation);}
void erasePoliticalContinuation(State& s,const Id& continuation) {s.politics.pending.erase(continuation);}

void refreshPoliticalState(State& s) {
    for(auto& [id,n]:s.nations) {
        int total=0;for(const auto& zone:possessedLand(s,id))total+=effectiveTerritorialIpp(s,zone);
        n.gameFlags["possessed_land_ipp"]=total;
    }
    for(const auto& nation:{"ccp","kmt"}) {
        if(!s.nations.contains(nation))continue;
        auto& n=s.nations.at(nation);
        n.gameFlags["civil_war_eliminated"]=hasUnits(s,nation)?0:1;
        if(n.powerStatus=="major"||s.politics.surrendered.contains(nation))continue;
        int total=0;for(const auto& zone:possessedLand(s,nation))total+=effectiveTerritorialIpp(s,zone);
        if(total<13)continue;
        n.powerStatus="major";
        require(s.clock.playerTurnSerial<=static_cast<std::uint64_t>(std::numeric_limits<int>::max()),"Evolution turn counter overflow");
        n.gameFlags["evolved_turn_serial"]=static_cast<int>(s.clock.playerTurnSerial);
        n.gameFlags["evolved_during_own_turn"]=s.currentNation()==nation;
        n.gameFlags["objective_evolution"]=1;
        refreshPoliticalUnitMovement(s,nation);
        if(s.politics.chineseTruce)terminateChineseTruce(s,nation,true);
        chooseEvolution(s,nation);
    }
    if(s.nations.contains("kmt")&&!s.politics.surrendered.contains("kmt")&&possessedLand(s,"kmt").empty()) {
        const auto* invader=s.politics.pending.contains("last_conqueror_kmt")?&s.politics.pending.at("last_conqueror_kmt"):nullptr;
        surrenderNation(s,"kmt",invader?invader->asString():s.currentNation());
    }
    if(s.nations.contains("ccp")&&s.nations.contains("kmt")) {
        bool objective=true;
        for(const auto& zone:possessedLand(s,"kmt"))if(chineseHomeCountry(s,zone)&&zone!="land_hainan"&&zone!="land_formosa")objective=false;
        s.nations.at("ccp").gameFlags["objective_one_china"]=objective;
    }
    queueObjectiveBonus(s);
    for(auto& [id,n]:s.nations)n.allies.clear();
    for(auto& [id,n]:s.nations) {
        for(const auto& [other,m]:s.nations)if(id!=other&&politicallyFriendly(s,id,other))n.allies.insert(other);
    }
}

void changePossession(State& s,const Id& zone,const Id& recipient,PossessionCause cause,const std::optional<Id>& conqueror) {
    require(s.nations.contains(recipient)&&!s.politics.surrendered.contains(recipient),"Invalid possession recipient");
    auto& territory=s.territories.at(zone);const auto old=territory.possessor;
    if(old==recipient)return;
    if(old&&s.politics.capitals.contains(*old)&&s.politics.capitals.at(*old)==zone&&s.nations.at(*old).treasury)s.nations.at(*old).treasury=0;
    territory.possessor=recipient;territory.flags["last_possession_change_turn"]=static_cast<int>(s.clock.playerTurnSerial);
    if(cause==PossessionCause::Capture||cause==PossessionCause::Liberation) {
        reconcileCapturedFacilities(s,zone,old.value_or(recipient),recipient);
        std::set<Id> removed;
        for(auto it=s.facilities.begin();it!=s.facilities.end();) {
            if(it->second.zone==zone&&(it->second.type=="fortification"||it->second.type=="coastal_artillery"||marked(it->second.flags,"under_construction"))) {removed.insert(it->first);it=s.facilities.erase(it);}else ++it;
        }
        for(auto it=s.construction.begin();it!=s.construction.end();) {
            const auto& b=it->second;const bool facility=s.definition->catalog->facilities().contains(b.type);
            if(facility&&b.site&&(b.site==zone||removed.contains(*b.site)))it=s.construction.erase(it);else ++it;
        }
        for(auto it=s.repairs.begin();it!=s.repairs.end();)if(removed.contains(it->second.target))it=s.repairs.erase(it);else ++it;
    }
    if(old)s.politics.pending["last_conqueror_"+*old]=V(conqueror.value_or(recipient));
    // Current territorial value is tracked at the transfer event, independently
    // of later legal-income evaluation and income collection.
    for(auto& [id,n]:s.nations) {int total=0;for(const auto& z:possessedLand(s,id))total+=effectiveTerritorialIpp(s,z);n.gameFlags["possessed_land_ipp"]=total;}
    refreshPoliticalState(s);
    if(s.definition->catalog)enforcePatrolLandingAvailability(s);
}
void captureLand(State& s,const Id& attacker,const Id& zone,const std::set<Id>& withdrawalEligibleRecipients) {
    require(s.nations.contains(attacker),"Unknown land conqueror");
    require(std::any_of(s.units.begin(),s.units.end(),[&](const auto& item){const auto& u=item.second;return u.owner==attacker&&u.zone==zone&&s.definition->catalog->unit(u.type).classes.contains("land");}),"Land capture requires a surviving attacking land unit");
    std::vector<Id> neutralNonparticipants;const auto previous=s.territories.at(zone).possessor;
    if(previous)for(const auto& [id,u]:s.units)
        if(u.zone==zone&&!u.carriedBy&&u.owner!=attacker&&u.owner!=*previous&&
            !s.nations.at(attacker).atWarWith.contains(u.owner)&&politicallyFriendly(s,u.owner,*previous)&&
            !s.definition->catalog->unit(u.type).classes.contains("naval"))neutralNonparticipants.push_back(id);
    const Id original=originalNation(s,zone);Id recipient=attacker;
    if(original!=attacker&&s.nations.at(original).powerStatus=="major"&&s.nations.at(original).alliance==s.nations.at(attacker).alliance&&!s.politics.surrendered.contains(original))recipient=original;
    changePossession(s,zone,recipient,recipient==attacker?PossessionCause::Capture:PossessionCause::Liberation,attacker);
    if(recipient==attacker&&s.nations.at(attacker).powerStatus=="major"&&chineseHomeCountry(s,zone)&&original!=attacker) {
        std::vector<Action> options{politicalAction(s,attacker,"politics_keep_capture",V(O{{"zone",V(zone)}}))};
        for(const auto& china:{"ccp","kmt"})if(!s.politics.surrendered.contains(china)
                &&(politicallyFriendly(s,attacker,china)||withdrawalEligibleRecipients.contains(china)))
            options.push_back(politicalAction(s,attacker,"politics_give_capture",V(O{
                {"zone",V(zone)},{"recipient",V(std::string(china))},
                {"requires_withdrawal",V(!politicallyFriendly(s,attacker,china))}})));
        // An unaligned transfer needs an actual friendly retreat/transport path.
        // M5 supplies that proof; a policy flag never substitutes for validation.
        if(options.size()>1)queuePoliticalDecision(s,attacker,"politics_chinese_liberation",std::move(options));
    }
    queueNeutralRelocation(s,zone,neutralNonparticipants);
}

PoliticalPermission mayDeclareWar(const State& s,const Id& actor,const Id& target,DeclarationMode mode) {
    if(!s.nations.contains(actor)||!s.nations.contains(target)||actor==target)return {false,"Unknown/self declaration"};
    const auto& a=s.nations.at(actor);const auto& b=s.nations.at(target);
    if(s.politics.surrendered.contains(actor)||marked(a.gameFlags,"incorporated"))return {false,"Inactive declaring nation"};
    if(s.politics.surrendered.contains(target)||marked(b.gameFlags,"incorporated"))return {false,"Inactive target nation"};
    if(a.atWarWith.contains(target))return {false,"Already at war"};
    if(a.alliance&&a.alliance==b.alliance)return {false,"Same alliance"};
    if(s.politics.chineseTruce&&((actor=="ccp"&&target=="kmt")||(actor=="kmt"&&target=="ccp")))return {false,"Use Chinese Truce termination"};
    if(b.powerStatus!="major"&&mode!=DeclarationMode::LandAttack)return {false,"Minor declarations require land combat movement"};
    if(mode==DeclarationMode::LandAttack&&(s.clock.phase!=Phase::CombatMovement||(actor!=s.currentNation()&&!controlledBy(s,actor,s.currentNation()))))return {false,"Land attack outside actor's combat movement"};
    if(actor=="kmt"&&(isWarlord(target)||target=="mongolia")) {
        if(hasUnits(s,"ccp"))return {false,"CCP has not been eliminated"};
        return {mode==DeclarationMode::LandAttack,"KMT warlord/Mongolia attack requires combat movement"};
    }
    if(actor=="ccp"&&isWarlord(target))return {mode==DeclarationMode::LandAttack,"Warlord attack requires combat movement"};
    if(actor=="ccp"||actor=="kmt") {
        if(a.powerStatus=="major")return {true,{}};
        bool present=false;
        for(const auto& zone:possessedLand(s,target))present=present||chineseHomeCountry(s,zone);
        for(const auto& [id,u]:s.units)if(u.owner==target&&s.territories.contains(u.zone))present=present||chineseHomeCountry(s,u.zone);
        return {present,present?"":"Target has no presence in Chinese Home Country"};
    }
    if(actor=="japan")return {true,{}};
    if(actor=="dadao"&&chinese(target))return {mode==DeclarationMode::LandAttack,"Dadao Chinese attack exception"};
    return {false,"Controlled minors cannot initiate a new war"};
}
void declareWar(State& s,const Id& actor,const Id& target,DeclarationMode mode) {
    const auto permission=mayDeclareWar(s,actor,target,mode);require(permission.allowed,"Illegal declaration: "+permission.reason);
    commitDeclaration(s,actor,target);
}
void recordLandAttack(State& s,const Id& attacker,const Id& zone) {
    require(s.territories.contains(zone),"Land attack target is not land");
    const auto defender=s.territories.at(zone).possessor;
    require(defender!=attacker,"Cannot attack one's own possession");
    if(defender&&s.politics.chineseTruce&&((attacker=="ccp"&&*defender=="kmt")||(attacker=="kmt"&&*defender=="ccp")))
        throw std::runtime_error("Chinese Truce prevents attacking the other faction");
    bool newChinaDeclaration=false;
    if(!chinese(attacker))for(const auto& china:{"ccp","kmt"}) {
        if(!s.politics.surrendered.contains(china)&&!s.nations.at(attacker).atWarWith.contains(china))newChinaDeclaration=true;
    }
    if(defender&&*defender!=attacker&&!s.nations.at(attacker).atWarWith.contains(*defender))declareWar(s,attacker,*defender,DeclarationMode::LandAttack);
    const auto original=originalNation(s,zone);
    if(defender&&isWarlord(*defender)) {
        if(attacker=="kmt") {incorporateNation(s,*defender,"ccp");refreshPoliticalState(s);}
        else {
            s.politics.attackedWarlords[*defender].insert(attacker);
            // RB4.9: warlords count as KMT to foreign powers, and those attacked
            // by CCP/Dadao join KMT only after Combat. RB4.5 assigns defense
            // choices before formal control. This records the defending policy
            // only; it grants no control, alignment, possession or asset credit.
            s.politics.pending["warlord_defense_player:"+*defender]=V(politicalPlayer(s,"kmt"));
        }
    }
    if(defender=="dadao"&&!chinese(attacker))s.politics.pending["dadao_attacked_by"]=V(attacker);
    if(!chinese(attacker)&&(original=="ccp"||original=="kmt"||isWarlord(original))&&defender!="dadao") {
        s.politics.foreignChinaWarPending=true;s.politics.chinaInvader=attacker;
        if(newChinaDeclaration)s.politics.pending["truce_foreign_declaration"]=V(true);
        for(auto& [id,n]:s.nations)if((id=="ccp"||id=="kmt"||isWarlord(id))&&!s.politics.surrendered.contains(id)&&!marked(n.gameFlags,"incorporated"))warPair(s,attacker,id);
    }
}
void surrenderNation(State& s,const Id& nation,const Id& attacker) {
    if(s.politics.surrendered.contains(nation))return;
    require(nation!="ccp","CCP never surrenders");
    s.politics.surrendered.insert(nation);
    if(nation=="kmt"&&s.nations.contains("ccp"))s.nations.at("ccp").gameFlags["one_china_bonus_eligible_at_surrender"]=!possessedLand(s,"ccp").empty();
    std::set<Id> removed;for(const auto& [id,u]:s.units)if(u.owner==nation)removed.insert(id);removePoliticalUnits(s,removed);
    for(auto& [id,t]:s.territories)if(t.possessor==nation)t.possessor.reset();
    auto& n=s.nations.at(nation);n.gameFlags["surrendered"]=1;if(n.treasury)n.treasury=0;
    for(auto it=s.repairs.begin();it!=s.repairs.end();)if(it->second.owner==nation)it=s.repairs.erase(it);else ++it;
    for(auto& [id,minor]:s.nations)if(id!=nation&&minor.controllerNation==nation&&!marked(minor.gameFlags,"incorporated")) {
        std::optional<Id> controller;
        for(const auto& [candidate,other]:s.nations)if(candidate!=nation&&other.alliance==n.alliance&&other.powerStatus=="major"&&!s.politics.surrendered.contains(candidate)) {controller=candidate;break;}
        minor.controllerNation=controller;if(controller)minor.player=s.nations.at(*controller).player;
        else if(nation=="japan"&&id=="dadao") {
            minor.player="axis";minor.alliance="axis";minor.gameFlags["direct_axis_control_after_japan_surrender"]=1;
        } else {minor.player.reset();minor.gameFlags["controller_unresolved"]=1;}
    }
    A ships;for(auto it=s.construction.begin();it!=s.construction.end();) {
        if(it->second.owner!=nation){++it;continue;}
        if(s.definition->catalog->units().contains(it->second.type)&&s.definition->catalog->unit(it->second.type).classes.contains("naval")){ships.emplace_back(it->first);++it;}else it=s.construction.erase(it);
    }
    if(!ships.empty()) {
        require(!s.chance,"Cannot queue surrender dice over another chance event");
        requestPoliticalRoll(s,attacker,"politics_surrender_queues",12,V(O{{"nation",V(nation)},{"attacker",V(attacker)},{"ships",V(ships)}}),static_cast<int>(ships.size()));
    }
    queueObjectiveBonus(s);
}

PoliticsRules::PoliticsRules(std::shared_ptr<const Rules> gameplay):gameplay_(std::move(gameplay)) {
    // Resolve the immutable composition once. An old milestone label here used
    // to miss the actual economy module, leaving rates stale after outer rules.
    refreshIncomeAfterEffects_ = gameplay_ && ("+" + gameplay_->id() + "+").find("+" + Id(economyRulesId) + "+") != Id::npos;
}
Id PoliticsRules::id() const {return "gw36_v43_m4_politics_income_refresh_v1"+(gameplay_?"+"+gameplay_->id():"");}
std::vector<Action> PoliticsRules::actions(const State& s) const {
    auto out=influenceActions(s);auto warlords=warlordActions(s);out.insert(out.end(),warlords.begin(),warlords.end());
    if(gameplay_) {auto more=gameplay_->actions(s);out.insert(out.end(),more.begin(),more.end());}

    return out;
}
std::vector<Action> PoliticsRules::interrupts(const State& s) const {
    if(s.flags.contains("strategic_naval_movement_in_progress")&&s.flags.at("strategic_naval_movement_in_progress"))return {};
    if(!s.decisions.empty())return {};
    std::vector<Action> out;
    for(const auto& [actor,a]:s.nations) {
        if(!a.player)continue;
        for(const auto& [target,b]:s.nations)if(mayDeclareWar(s,actor,target).allowed)out.push_back(politicalAction(s,actor,"politics_declare_war",V(O{{"target",V(target)}})));
    }
    return out;
}
bool PoliticsRules::phaseComplete(const State& s) const {
    return !gameplay_||gameplay_->phaseComplete(s);
}
void PoliticsRules::apply(State& s,const Action& a) const {
    applyImpl(s,a);if(refreshIncomeAfterEffects_)refreshIncome(s);
}
void PoliticsRules::applyImpl(State& s,const Action& a) const {
    if(a.kind=="politics_declare_war") {
        const auto target=a.parameters.require("target").asString();
        if(a.nation!=s.currentNation()&&s.nations.at(a.nation).alliance!=s.nations.at(s.currentNation()).alliance) {
            queueDeclarationPriority(s,a.nation,target);
        }else declareWar(s,a.nation,target,DeclarationMode::MajorPowerDeclaration);
        return;
    }
    if(a.kind=="politics_priority_decline"||a.kind=="politics_priority_declare") {
        const auto context=pendingPolitical(s,s.decisions.back().continuation);
        releaseDecision(s,a);
        if(a.kind=="politics_priority_declare")declareWar(s,a.parameters.require("declaring_nation").asString(),a.parameters.require("target").asString(),DeclarationMode::MajorPowerDeclaration);
        const auto actor=context.require("actor").asString(),target=context.require("target").asString();
        if(!s.nations.at(actor).atWarWith.contains(target)) {
            if(a.kind=="politics_priority_declare")queueDeclarationPriority(s,actor,target);
            else declareWar(s,actor,target,DeclarationMode::MajorPowerDeclaration);
        }
        return;
    }
    if(a.kind=="politics_choose_capital") {
        const auto zone=a.parameters.require("zone").asString();require(s.territories.at(zone).possessor==a.nation,"Capital choice lost possession");
        releaseDecision(s,a);s.politics.capitals[a.nation]=zone;s.politics.evolutionAwarded.insert(a.nation);s.flags.erase("evolution_pending_"+a.nation);
        if(a.parameters.require("factory").asBool()) {
            const auto& node=s.definition->geography.require("nodes").require(zone);const auto* city=node.find("is_city");
            FacilityState facility;facility.id=uniqueContinuation(s,"evolution_factory");facility.zone=zone;facility.type=city&&city->asBool()?"major_factory":"medium_factory";
            facility.flags["placed_this_turn"]=1;s.facilities.emplace(facility.id,std::move(facility));
        }
        continueCombatPoliticalResolution(s);return;
    }
    if(a.kind=="politics_relocate_neutral") {
        const auto key=a.parameters.require("relocation").asString();
        const auto unit=a.parameters.require("unit").asString(),zone=a.parameters.require("zone").asString();
        require(s.politics.pending.contains(key)&&s.units.contains(unit),"Neutral relocation is no longer pending");
        const auto context=s.politics.pending.at(key);
        const auto destinations=nearestFriendlyLand(s,s.units.at(unit).owner,context.require("origin").asString());
        require(std::find(destinations.begin(),destinations.end(),zone)!=destinations.end(),"Neutral relocation destination is no longer nearest Friendly land");
        releaseDecision(s,a);relocateNeutralUnit(s,unit,zone);
        auto next=s.politics.pending.at(key).asObject();auto units=next.at("units").asArray();
        require(!units.empty()&&units.front().asString()==unit,"Unexpected neutral relocation continuation");
        units.erase(units.begin());next["units"]=V(units);s.politics.pending[key]=V(next);continueNeutralRelocation(s,key);return;
    }
    if(a.kind=="politics_keep_capture"||a.kind=="politics_give_capture") {
        releaseDecision(s,a);
        if(a.kind=="politics_give_capture") {
            const auto zone=a.parameters.require("zone").asString();
            if(a.parameters.require("requires_withdrawal").asBool())
                for(auto& [id,u]:s.units)if(u.owner==a.nation&&u.zone==zone&&
                    s.definition->catalog->unit(u.type).classes.contains("land"))
                    u.turnFlags["must_withdraw_from_chinese_gift"]=1;
            changePossession(s,zone,a.parameters.require("recipient").asString(),PossessionCause::Transfer,a.nation);
        }
        return;
    }
    if(applyWarlordAction(s,a)||applyInfluenceAction(s,a))return;
    if(gameplay_){gameplay_->apply(s,a);refreshPoliticalState(s);return;}
    throw std::runtime_error("Unknown political action: "+a.kind);
}
void PoliticsRules::applyChance(State& s,const ChanceRequest& request,const ChanceOutcome& outcome) const {
    applyChanceImpl(s,request,outcome);if(refreshIncomeAfterEffects_)refreshIncome(s);
}
void PoliticsRules::applyChanceImpl(State& s,const ChanceRequest& request,const ChanceOutcome& outcome) const {
    if(request.purpose=="politics_surrender_queues") {
        const auto context=pendingPolitical(s,request.continuation);erasePoliticalContinuation(s,request.continuation);
        const auto faces=effectiveResults(request,outcome);const auto& ships=context.require("ships").asArray();
        for(std::size_t i=0;i<ships.size();++i) {const auto id=ships[i].asString();if(faces[i]<=7)s.construction.erase(id);else s.construction.at(id).owner=context.require("attacker").asString();}
        continueCombatPoliticalResolution(s);return;
    }
    if(applyWarlordChance(s,request,outcome)||applyInfluenceChance(s,request,outcome))return;
    if(gameplay_){gameplay_->applyChance(s,request,outcome);refreshPoliticalState(s);return;}
    throw std::runtime_error("Unknown political chance continuation");
}
void PoliticsRules::beginTurn(State& s) const {
    const auto active=s.currentNation();
    for(auto& [id,n]:s.nations)if(controlledBy(s,id,active)||(id=="dadao"&&active=="japan"&&marked(n.gameFlags,"direct_axis_control_after_japan_surrender"))) {
        n.turnFlags.clear();
        for(auto& [unitId,u]:s.units)if(u.owner==id){u.turnFlags.clear();u.commitments.clear();u.route.clear();u.turnOrigin=u.zone;u.movementAllowance=s.definition->catalog->stats(u.type,u.damage,catalogContext(s,id,u.zone)).movement;u.movementRemaining=u.movementAllowance;}
    }
    if(gameplay_)gameplay_->beginTurn(s);
    refreshPoliticalState(s);
}
void PoliticsRules::finishPhase(State& s) const {
    if(gameplay_)gameplay_->finishPhase(s);
    if(s.clock.phase==Phase::Combat&&!marked(s.nations.at(s.currentNation()).turnFlags,"politics_combat_finished")) {
        s.nations.at(s.currentNation()).turnFlags["politics_combat_finished"]=1;
        beginCombatPoliticalResolution(s);
    }
}
void PoliticsRules::finishTurn(State& s) const {
    if(s.politics.surrendered.contains(s.currentNation()))s.clock.incomeCollected=true;
    else if(gameplay_)gameplay_->finishTurn(s);
    else {
        auto& n=s.nations.at(s.currentNation());
        const bool incomeAccount=s.currentNation()=="japan"||s.currentNation()=="ccp"||s.currentNation()=="kmt"||n.powerStatus=="major";
        require(!incomeAccount||n.incomeKnown,"M6 national income evaluation is not installed");
        int income=0;for(const auto& [id,value]:n.incomeComponents)income+=value;
        if(incomeAccount&&n.treasury&&(n.powerStatus!="major"||ownCapital(s,s.currentNation()))) {
            require(income>=0&&*n.treasury<=std::numeric_limits<int>::max()-income,"Invalid income collection");*n.treasury+=income;
        }
        s.clock.incomeCollected=true;
    }
    if(s.currentNation()=="japan"&&!s.politics.surrendered.contains("japan")) {
        const auto it=s.politics.capitals.find("japan");
        if(it!=s.politics.capitals.end()) {const auto owner=s.territories.at(it->second).possessor;if(owner&&s.nations.at("japan").atWarWith.contains(*owner))surrenderNation(s,"japan",*owner);}
    }
}
} // namespace game::campaign
