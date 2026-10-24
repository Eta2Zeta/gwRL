#include "game/campaign.hpp"
#include "game/campaign_actions.hpp"
#include "game/catalog.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <array>
#include <charconv>
#include <cmath>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string_view>

namespace game::campaign {
namespace {
using V = json::Value;
using O = V::Object;
using A = V::Array;
void require(bool ok, const std::string& message) { if (!ok) throw std::runtime_error(message); }
V number(int v) { return V(static_cast<double>(v)); }
V optionalId(const std::optional<Id>& v) { return v ? V(*v) : V(nullptr); }
V optionalInt(const std::optional<int>& v) { return v ? number(*v) : V(nullptr); }
std::optional<Id> readOptionalId(const V& v) { return v.isNull() ? std::nullopt : std::optional<Id>(v.asString()); }
std::optional<int> readOptionalInt(const V& v) { return v.isNull() ? std::nullopt : std::optional<int>(v.asInt()); }
template<class C> V strings(const C& values) { A a; for (const auto& v : values) a.emplace_back(v); return V(std::move(a)); }
std::vector<Id> readStrings(const V& v) { std::vector<Id> a; for (const auto& x : v.asArray()) a.push_back(x.asString()); return a; }
std::set<Id> readSet(const V& v) { auto a = readStrings(v); std::set<Id> s(a.begin(), a.end()); require(s.size() == a.size(), "Duplicate set value"); return s; }
V ints(const std::vector<int>& values) { A a; for (int v : values) a.push_back(number(v)); return V(std::move(a)); }
std::vector<int> readInts(const V& v) { std::vector<int> a; for (const auto& x : v.asArray()) a.push_back(x.asInt()); return a; }
V intMap(const std::map<Id, int>& values) { O o; for (const auto& [k,v] : values) o.emplace(k,number(v)); return V(std::move(o)); }
std::map<Id,int> readIntMap(const V& v) { std::map<Id,int> o; for (const auto& [k,x] : v.asObject()) o.emplace(k,x.asInt()); return o; }
V idMap(const std::map<Id, Id>& values) { O o; for (const auto& [k,v] : values) o.emplace(k,V(v)); return V(std::move(o)); }
V optionalIdMap(const std::map<Id, std::optional<Id>>& values) { O o; for(const auto& [k,v]:values)o.emplace(k,optionalId(v));return V(std::move(o)); }
std::map<Id,std::optional<Id>> readOptionalIdMap(const V& v) {std::map<Id,std::optional<Id>> o;for(const auto& [k,x]:v.asObject())o.emplace(k,readOptionalId(x));return o;}
std::map<Id,Id> readIdMap(const V& v) { std::map<Id,Id> o; for (const auto& [k,x] : v.asObject()) o.emplace(k,x.asString()); return o; }
std::uint64_t readCounter(const V& v) {
    const auto& text=v.asString(); std::uint64_t n=0;
    require(!text.empty() && (text.size()==1 || text.front()!='0'), "Invalid decimal counter");
    const auto [end, ec]=std::from_chars(text.data(),text.data()+text.size(),n);
    require(ec==std::errc{} && end==text.data()+text.size(), "Invalid decimal counter"); return n;
}
void writeString(std::string& out,const std::string& text) {
    static constexpr char hex[]="0123456789abcdef"; out+='"';
    for (unsigned char c:text) {
        if (c=='"' || c=='\\') { out+='\\'; out+=static_cast<char>(c); }
        else if (c<32) { out+="\\u00"; out+=hex[c>>4]; out+=hex[c&15]; }
        else out+=static_cast<char>(c);
    }
    out+='"';
}
void writeJson(std::string& out,const V& v) {
    if (v.isNull()) out+="null";
    else if (v.isBool()) out+=v.asBool()?"true":"false";
    else if (v.isNumber()) {
        const double d=v.asNumber(); require(std::isfinite(d),"JSON numbers must be finite");
        if (d==0) { out+='0'; return; }
        char buffer[64]; const auto [end,ec]=std::to_chars(buffer,buffer+sizeof(buffer),d,std::chars_format::general,std::numeric_limits<double>::max_digits10);
        require(ec==std::errc{},"Cannot format JSON number"); out.append(buffer,end);
    } else if (v.isString()) writeString(out,v.asString());
    else if (v.isArray()) { out+='['; bool first=true; for (const auto& x:v.asArray()) { if (!first) out+=','; first=false; writeJson(out,x); } out+=']'; }
    else { out+='{'; bool first=true; for (const auto& [k,x]:v.asObject()) { if (!first) out+=','; first=false; writeString(out,k); out+=':'; writeJson(out,x); } out+='}'; }
}
V definitionJson(const Definition& d) {
    O factions; for (const auto& [k,f]:d.factions) factions.emplace(k,V(O{{"id",V(f.id)},{"display_name",V(f.displayName)},{"home_country",strings(f.homeCountry)},{"home_country_known",V(f.homeCountryKnown)},{"dormant",V(f.dormant)}}));
    return V(O{{"scenario_id",V(d.scenarioId)},{"geography",d.geography},{"rules",d.rules},{"factions",V(std::move(factions))},{"turn_order",strings(d.turnOrder)},{"players",strings(d.players)},{"start_year",number(d.startYear)},{"start_month",number(d.startMonth)},{"calendar_rounds",number(d.calendarRounds)}});
}
V politicsJson(const PoliticalState& p) {
    O attacks, pending;
    for(const auto& [id,actors]:p.attackedWarlords)attacks.emplace(id,strings(actors));
    for(const auto& [id,value]:p.pending)pending.emplace(id,value);
    return V(O{{"chinese_truce",V(p.chineseTruce)}, {"truce_permanently_ended",V(p.trucePermanentlyEnded)},
        {"foreign_china_war_pending",V(p.foreignChinaWarPending)}, {"truce_offer_pending",V(p.truceOfferPending)},
        {"china_invader",optionalId(p.chinaInvader)}, {"attacked_warlords",V(std::move(attacks))},
        {"alignment_queue",strings(p.alignmentQueue)}, {"capitals",idMap(p.capitals)},
        {"surrendered",strings(p.surrendered)}, {"evolution_awarded",strings(p.evolutionAwarded)},
        {"pending",V(std::move(pending))}});
}
PoliticalState readPolitics(const V& v) {
    PoliticalState p;
    p.chineseTruce=v.require("chinese_truce").asBool();p.trucePermanentlyEnded=v.require("truce_permanently_ended").asBool();
    p.foreignChinaWarPending=v.require("foreign_china_war_pending").asBool();p.truceOfferPending=v.require("truce_offer_pending").asBool();
    p.chinaInvader=readOptionalId(v.require("china_invader"));
    for(const auto& [id,actors]:v.require("attacked_warlords").asObject())p.attackedWarlords.emplace(id,readSet(actors));
    p.alignmentQueue=readStrings(v.require("alignment_queue"));p.capitals=readIdMap(v.require("capitals"));
    p.surrendered=readSet(v.require("surrendered"));p.evolutionAwarded=readSet(v.require("evolution_awarded"));
    p.pending=v.require("pending").asObject();return p;
}
V decisionJson(const Decision& d) { A options; for (const auto& a:d.options) options.push_back(actionJson(a)); return V(O{{"id",V(d.id)},{"kind",V(d.kind)},{"nation",V(d.nation)},{"reaction",V(d.reaction)},{"continuation",V(d.continuation)},{"options",V(std::move(options))}}); }
Decision readDecision(const V& v) { Decision d; d.id=v.require("id").asString(); d.kind=v.require("kind").asString(); d.nation=v.require("nation").asString(); d.reaction=v.require("reaction").asBool(); d.continuation=v.require("continuation").asString(); for(const auto& a:v.require("options").asArray())d.options.push_back(actionFromJson(a)); return d; }
V chanceJson(const ChanceRequest& c) { A dice; for(const auto& d:c.dice) { std::vector<int> faces(d.rerollFaces.begin(),d.rerollFaces.end()); dice.emplace_back(O{{"sides",number(d.sides)},{"modifier",number(d.modifier)},{"reroll_faces",ints(faces)},{"max_rerolls",number(d.maxRerolls)}}); } return V(O{{"id",V(c.id)},{"purpose",V(c.purpose)},{"nation",V(c.nation)},{"continuation",V(c.continuation)},{"dice",V(std::move(dice))}}); }
ChanceRequest readChance(const V& v) { ChanceRequest c; c.id=v.require("id").asString(); c.purpose=v.require("purpose").asString(); c.nation=v.require("nation").asString(); c.continuation=v.require("continuation").asString(); for(const auto& x:v.require("dice").asArray()) { DieSpec d; d.sides=x.require("sides").asInt(); d.modifier=x.require("modifier").asInt(); d.maxRerolls=x.require("max_rerolls").asInt(); auto faces=readInts(x.require("reroll_faces")); d.rerollFaces={faces.begin(),faces.end()}; require(d.rerollFaces.size()==faces.size(),"Duplicate reroll face"); c.dice.push_back(std::move(d)); } return c; }
}

std::string toString(Phase phase) { switch(phase) { case Phase::Production:return "production"; case Phase::CombatMovement:return "combat_movement"; case Phase::Combat:return "combat"; case Phase::NonCombatMovement:return "non_combat_movement"; case Phase::PlaceUnits:return "place_units"; } throw std::runtime_error("Invalid campaign phase"); }
Phase parsePhase(const std::string& text) { for(auto phase:{Phase::Production,Phase::CombatMovement,Phase::Combat,Phase::NonCombatMovement,Phase::PlaceUnits}) if(toString(phase)==text)return phase; throw std::runtime_error("Unknown campaign phase: "+text); }
std::string canonicalJson(const V& value) { std::string result; writeJson(result,value); return result; }

// SHA-256 over exact canonical bytes; no platform hash or external dependency.
std::string contentDigest(const std::string& value) {
    static constexpr std::array<std::uint32_t,64> k={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
    std::array<std::uint32_t,8> h={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    std::vector<unsigned char> data(value.begin(),value.end()); const auto bits=static_cast<std::uint64_t>(data.size())*8; data.push_back(0x80); while(data.size()%64!=56)data.push_back(0); for(int i=7;i>=0;--i)data.push_back(static_cast<unsigned char>(bits>>(8*i)));
    const auto rotr=[](std::uint32_t x,int n){return (x>>n)|(x<<(32-n));};
    for(std::size_t offset=0;offset<data.size();offset+=64) {
        std::array<std::uint32_t,64>w{}; for(int i=0;i<16;++i)for(int j=0;j<4;++j)w[i]=(w[i]<<8)|data[offset+4*i+j];
        for(int i=16;i<64;++i) { auto s0=rotr(w[i-15],7)^rotr(w[i-15],18)^(w[i-15]>>3); auto s1=rotr(w[i-2],17)^rotr(w[i-2],19)^(w[i-2]>>10); w[i]=w[i-16]+s0+w[i-7]+s1; }
        auto [a,b,c,d,e,f,g,z]=h; for(int i=0;i<64;++i) { auto s1=rotr(e,6)^rotr(e,11)^rotr(e,25); auto t1=z+s1+((e&f)^((~e)&g))+k[i]+w[i]; auto s0=rotr(a,2)^rotr(a,13)^rotr(a,22); auto t2=s0+((a&b)^(a&c)^(b&c)); z=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2; }
        h[0]+=a;h[1]+=b;h[2]+=c;h[3]+=d;h[4]+=e;h[5]+=f;h[6]+=g;h[7]+=z;
    }
    std::ostringstream out; out<<std::hex<<std::setfill('0'); for(auto x:h)out<<std::setw(8)<<x; return out.str();
}

std::shared_ptr<const Definition> freezeDefinition(Definition d) {
    require(!d.scenarioId.empty(),"Missing scenario identity"); require(d.geography.isObject() && d.rules.isObject(),"Definition geography/rules must be objects");
    const auto& nodes=d.geography.require("nodes").asObject(); require(!nodes.empty(),"Definition has no map nodes");
    for(const auto& [id,node]:nodes) { require(node.require("id").asString()==id,"Map key/ID mismatch"); const auto& type=node.require("type").asString(); require(type=="land"||type=="sea","Unknown map node type"); }
    require(!d.factions.empty()&&!d.players.empty()&&!d.turnOrder.empty(),"Definition requires factions, players and turn order");
    for(const auto& [id,f]:d.factions) { require(!id.empty()&&f.id==id&&!f.displayName.empty(),"Invalid faction identity"); for(const auto& zone:f.homeCountry) require(nodes.contains(zone)&&nodes.at(zone).require("type").asString()=="land","Home-country reference is not retained land"); }
    std::set<Id> turns; for(const auto& id:d.turnOrder) require(d.factions.contains(id)&&turns.insert(id).second,"Invalid/duplicate national turn order"); for(const auto& id:d.players)require(!id.empty(),"Empty player identity");
    require(d.startYear>0&&(d.startMonth==1||d.startMonth==7)&&d.calendarRounds>0,"Invalid half-year calendar");
    auto encoded=definitionJson(d).asObject();
    if(d.catalog) { d.catalog->requireComplete(); encoded.emplace("catalog_fingerprint",V(d.catalog->fingerprint())); }
    d.fingerprint=contentDigest(canonicalJson(V(std::move(encoded)))); return std::make_shared<const Definition>(std::move(d));
}

V actionJson(const Action& a) { return V(O{{"id",V(a.id)},{"kind",V(a.kind)},{"player",V(a.player)},{"nation",V(a.nation)},{"decision",optionalId(a.decision)},{"parameters",a.parameters}}); }
Action actionFromJson(const V& v) { Action a; a.id=v.require("id").asString();a.kind=v.require("kind").asString();a.player=v.require("player").asString();a.nation=v.require("nation").asString();a.decision=readOptionalId(v.require("decision"));a.parameters=v.require("parameters"); return a; }
V outcomeJson(const ChanceOutcome& o) { A a; for(const auto& faces:o.faces)a.push_back(ints(faces)); return V(O{{"faces",V(std::move(a))}}); }
ChanceOutcome outcomeFromJson(const V& v) { ChanceOutcome o; for(const auto& faces:v.require("faces").asArray())o.faces.push_back(readInts(faces)); return o; }
State State::clone() const { return *this; }
Id State::currentNation() const { require(definition!=nullptr,"State has no definition"); require(clock.nationIndex>=0&&static_cast<std::size_t>(clock.nationIndex)<definition->turnOrder.size(),"Invalid national turn cursor");return definition->turnOrder[clock.nationIndex]; }
std::optional<Id> State::decisionPlayer() const { if(terminal||chance)return std::nullopt; const auto nation=decisions.empty()?currentNation():decisions.back().nation; require(nations.contains(nation),"Decision nation is unknown");return politicalPlayer(*this,nation); }
std::pair<int,int> State::calendarDate() const { require(definition!=nullptr,"State has no definition");const auto months=definition->startMonth-1+6*clock.roundIndex;return {definition->startYear+months/12,months%12+1}; }
void State::captureTurnStart() { turnStart={};for(const auto& [id,t]:territories)turnStart.possessions.emplace(id,t.possessor);for(const auto& [id,u]:units)turnStart.units.emplace(id,std::pair{u.owner,u.zone}); }

V State::toJson(bool includeHistory) const {
    require(definition!=nullptr,"State has no definition"); O n,t,u,f,r,b,j,bs; A ds,events; O snapshotUnits;
    for(const auto& [id,x]:nations)n.emplace(id,V(O{{"controller_nation",optionalId(x.controllerNation)},{"player",optionalId(x.player)},{"alliance",optionalId(x.alliance)},{"power_status",V(x.powerStatus)},{"treasury",optionalInt(x.treasury)},{"income_components",intMap(x.incomeComponents)},{"income_known",V(x.incomeKnown)},{"technology_stages",intMap(x.technologyStages)},{"at_war_with",strings(x.atWarWith)},{"allies",strings(x.allies)},{"turn_flags",intMap(x.turnFlags)},{"game_flags",intMap(x.gameFlags)}}));
    for(const auto& [id,x]:territories)t.emplace(id,V(O{{"possessor",optionalId(x.possessor)},{"flags",intMap(x.flags)}}));
    for(const auto& [id,x]:units)u.emplace(id,V(O{{"id",V(x.id)},{"type",V(x.type)},{"owner",V(x.owner)},{"zone",V(x.zone)},{"movement_remaining",optionalInt(x.movementRemaining)},{"movement_allowance",optionalInt(x.movementAllowance)},{"turn_origin",V(x.turnOrigin)},{"route",strings(x.route)},{"carried_by",optionalId(x.carriedBy)},{"cargo",strings(x.cargo)},{"damage",number(x.damage)},{"commitments",strings(x.commitments)},{"turn_flags",intMap(x.turnFlags)},{"game_flags",intMap(x.gameFlags)}}));
    for(const auto& [id,x]:facilities)f.emplace(id,V(O{{"id",V(x.id)},{"type",V(x.type)},{"zone",V(x.zone)},{"damage",number(x.damage)},{"flags",intMap(x.flags)}}));
    for(const auto& [id,x]:rails)r.emplace(id,V(O{{"id",V(x.id)},{"endpoint_a",V(x.endpointA)},{"endpoint_b",V(x.endpointB)},{"damage_by_endpoint",intMap(x.damageByEndpoint)}}));
    for(const auto& [id,x]:construction)b.emplace(id,V(O{{"id",V(x.id)},{"owner",V(x.owner)},{"type",V(x.type)},{"site",optionalId(x.site)},{"queue_position",number(x.queuePosition)},{"paid_ipp",number(x.paidIpp)},{"remaining_payments",ints(x.remainingPayments)},{"flags",intMap(x.flags)}}));
    for(const auto& [id,x]:repairs)j.emplace(id,V(O{{"id",V(x.id)},{"owner",V(x.owner)},{"target",V(x.target)},{"remaining_damage",number(x.remainingDamage)},{"remaining_cost",number(x.remainingCost)},{"restricts_action",V(x.restrictsAction)},{"endpoint",optionalId(x.endpoint)}}));
    for(const auto& [id,x]:battles)bs.emplace(id,V(O{{"id",V(x.id)},{"zone",V(x.zone)},{"attacker",V(x.attacker)},{"defender",V(x.defender)},{"stage",V(x.stage)},{"attackers",strings(x.attackers)},{"defenders",strings(x.defenders)},{"pending_hits",intMap(x.pendingHits)},{"flags",intMap(x.flags)},{"data",x.data}}));
    for(const auto& d:decisions)ds.push_back(decisionJson(d));
    for(const auto& [id,pair]:turnStart.units)snapshotUnits.emplace(id,V(A{V(pair.first),V(pair.second)}));
    O result{{"schema_version",number(1)},{"definition_fingerprint",V(definition->fingerprint)},{"nations",V(std::move(n))},{"territories",V(std::move(t))},{"units",V(std::move(u))},{"facilities",V(std::move(f))},{"rails",V(std::move(r))},{"construction",V(std::move(b))},{"repairs",V(std::move(j))},{"clock",V(O{{"round_index",number(clock.roundIndex)},{"nation_index",number(clock.nationIndex)},{"phase",V(toString(clock.phase))},{"completed_rounds",number(clock.completedRounds)},{"player_turn_serial",V(std::to_string(clock.playerTurnSerial))},{"income_collected",V(clock.incomeCollected)}})},{"turn_start",V(O{{"possessions",optionalIdMap(turnStart.possessions)},{"units",V(std::move(snapshotUnits))}})},{"politics",politicsJson(politics)},{"completed_turns",intMap(completedTurns)},{"decisions",V(std::move(ds))},{"battles",V(std::move(bs))},{"battle_order",strings(battleOrder)},{"chance",chance?chanceJson(*chance):V(nullptr)},{"flags",intMap(flags)},{"terminal",V(terminal)}};
    if(!actionInterface.asObject().empty()) result.emplace("action_interface",actionInterface);
    if(includeHistory) { for(const auto& e:history)events.emplace_back(O{{"kind",V(e.kind)},{"payload",e.payload},{"after_state_key",V(e.afterStateKey)}});result.emplace("history",V(std::move(events))); }
    return V(std::move(result));
}

State State::fromJson(std::shared_ptr<const Definition> definition,const V& v) {
    require(definition!=nullptr,"Restore requires a definition");require(v.require("schema_version").asInt()==1,"Unsupported state schema");require(v.require("definition_fingerprint").asString()==definition->fingerprint,"State definition fingerprint mismatch");State s;s.definition=std::move(definition);
    for(const auto& [id,x]:v.require("nations").asObject()) { NationState n;n.controllerNation=readOptionalId(x.require("controller_nation"));n.player=readOptionalId(x.require("player"));n.alliance=readOptionalId(x.require("alliance"));n.powerStatus=x.require("power_status").asString();n.treasury=readOptionalInt(x.require("treasury"));n.incomeComponents=readIntMap(x.require("income_components"));n.incomeKnown=x.require("income_known").asBool();n.technologyStages=readIntMap(x.require("technology_stages"));n.atWarWith=readSet(x.require("at_war_with"));n.allies=readSet(x.require("allies"));n.turnFlags=readIntMap(x.require("turn_flags"));n.gameFlags=readIntMap(x.require("game_flags"));s.nations.emplace(id,std::move(n)); }
    for(const auto& [id,x]:v.require("territories").asObject())s.territories.emplace(id,TerritoryState{readOptionalId(x.require("possessor")),readIntMap(x.require("flags"))});
    for(const auto& [id,x]:v.require("units").asObject()) { UnitState u;u.id=x.require("id").asString();u.type=x.require("type").asString();u.owner=x.require("owner").asString();u.zone=x.require("zone").asString();u.movementRemaining=readOptionalInt(x.require("movement_remaining"));u.movementAllowance=readOptionalInt(x.require("movement_allowance"));u.turnOrigin=x.require("turn_origin").asString();u.route=readStrings(x.require("route"));u.carriedBy=readOptionalId(x.require("carried_by"));u.cargo=readStrings(x.require("cargo"));u.damage=x.require("damage").asInt();u.commitments=readSet(x.require("commitments"));u.turnFlags=readIntMap(x.require("turn_flags"));u.gameFlags=readIntMap(x.require("game_flags"));s.units.emplace(id,std::move(u)); }
    for(const auto& [id,x]:v.require("facilities").asObject())s.facilities.emplace(id,FacilityState{x.require("id").asString(),x.require("type").asString(),x.require("zone").asString(),x.require("damage").asInt(),readIntMap(x.require("flags"))});
    for(const auto& [id,x]:v.require("rails").asObject())s.rails.emplace(id,RailState{x.require("id").asString(),x.require("endpoint_a").asString(),x.require("endpoint_b").asString(),readIntMap(x.require("damage_by_endpoint"))});
    for(const auto& [id,x]:v.require("construction").asObject())s.construction.emplace(id,BuildProject{x.require("id").asString(),x.require("owner").asString(),x.require("type").asString(),readOptionalId(x.require("site")),x.require("queue_position").asInt(),x.require("paid_ipp").asInt(),readInts(x.require("remaining_payments")),readIntMap(x.require("flags"))});
    for(const auto& [id,x]:v.require("repairs").asObject())s.repairs.emplace(id,RepairJob{x.require("id").asString(),x.require("owner").asString(),x.require("target").asString(),x.require("remaining_damage").asInt(),x.require("remaining_cost").asInt(),x.require("restricts_action").asBool(),x.find("endpoint")?readOptionalId(x.require("endpoint")):std::nullopt});
    const auto& c=v.require("clock");s.clock={c.require("round_index").asInt(),c.require("nation_index").asInt(),parsePhase(c.require("phase").asString()),c.require("completed_rounds").asInt(),readCounter(c.require("player_turn_serial")),c.require("income_collected").asBool()};
    const auto& snapshot=v.require("turn_start");s.turnStart.possessions=readOptionalIdMap(snapshot.require("possessions"));for(const auto& [id,x]:snapshot.require("units").asObject()) { const auto& a=x.asArray();require(a.size()==2,"Snapshot unit needs owner and zone");s.turnStart.units.emplace(id,std::pair{a[0].asString(),a[1].asString()}); }
    if(const auto* p=v.find("politics"))s.politics=readPolitics(*p);
    if(const auto* p=v.find("action_interface"))s.actionInterface=*p;
    s.completedTurns=readIntMap(v.require("completed_turns"));for(const auto& x:v.require("decisions").asArray())s.decisions.push_back(readDecision(x));
    for(const auto& [id,x]:v.require("battles").asObject())s.battles.emplace(id,BattleState{x.require("id").asString(),x.require("zone").asString(),x.require("attacker").asString(),x.require("defender").asString(),x.require("stage").asString(),readStrings(x.require("attackers")),readStrings(x.require("defenders")),readIntMap(x.require("pending_hits")),readIntMap(x.require("flags")),x.find("data")?x.require("data"):V(O{})});
    s.battleOrder=readStrings(v.require("battle_order"));if(!v.require("chance").isNull())s.chance=readChance(v.require("chance"));s.flags=readIntMap(v.require("flags"));s.terminal=v.require("terminal").asBool();
    if(const auto* events=v.find("history"))for(const auto& x:events->asArray())s.history.push_back(Event{x.require("kind").asString(),x.require("payload"),x.require("after_state_key").asString()});
    s.validate();return s;
}
std::string State::serialize() const { validate();return canonicalJson(toJson()); }
std::string State::planningKey() const { return contentDigest(canonicalJson(toJson(false))); }
V State::observation() const { auto object=toJson(false).asObject();object.erase("definition_fingerprint");return V(std::move(object)); }

void State::validate() const {
    require(definition!=nullptr&&!definition->fingerprint.empty(),"State requires a frozen definition");
    require(actionInterface.isObject(),"Action-interface state must be an object");
    validateTrainingActionState(*this);
    const auto& nodes=definition->geography.require("nodes").asObject();
    const auto zone=[&](const Id& id){require(nodes.contains(id),"Unknown zone: "+id);};
    const auto land=[&](const Id& id){zone(id);require(nodes.at(id).require("type").asString()=="land","Expected land zone: "+id);};
    const auto nation=[&](const Id& id){require(nations.contains(id),"Unknown nation: "+id);};
    const auto unique=[](const std::vector<Id>& ids,const std::string& message){require(std::set<Id>(ids.begin(),ids.end()).size()==ids.size(),message);};
    for(const auto& [id,f]:definition->factions)require(f.dormant||nations.contains(id),"State faction inventory differs from definition");
    for(const auto& [id,n]:nations) { require(definition->factions.contains(id),"Undefined national identity: "+id);if(n.controllerNation)nation(*n.controllerNation);if(n.player)require(definition->players.contains(*n.player),"Unknown controlling player");if(n.alliance)require(!n.alliance->empty(),"Empty alliance identity");require(!n.powerStatus.empty(),"Missing power status");if(n.treasury)require(*n.treasury>=0,"Negative treasury");for(const auto& [tech,stage]:n.technologyStages){require(!tech.empty()&&stage>=0,"Invalid technology stage");if(definition->catalog)require(stage<=4&&definition->catalog->technologies().contains(tech),"Unknown catalog technology/stage");}for(const auto& other:n.atWarWith){nation(other);require(other!=id,"Nation cannot be at war with itself");}for(const auto& other:n.allies){nation(other);require(other!=id,"Nation cannot ally with itself");} }
    for(const auto& [id,node]:nodes)if(node.require("type").asString()=="land")require(territories.contains(id),"Missing retained territory: "+id);
    for(const auto& [id,t]:territories){land(id);if(t.possessor)nation(*t.possessor);}
    for(const auto& [id,u]:units) {
        require(!id.empty()&&id==u.id&&!u.type.empty(),"Invalid unit identity/type");nation(u.owner);zone(u.zone);zone(u.turnOrigin);for(const auto& routeZone:u.route)zone(routeZone);require(u.damage>=0,"Negative unit damage");
        if(definition->catalog) {
            const auto& type=definition->catalog->unit(u.type);
            require(type.states.contains(u.damage),"Unknown surviving unit damage state");
            require(u.movementAllowance.has_value()&&u.movementRemaining.has_value(),"Catalog unit has unresolved movement");
        }
        if(u.movementRemaining)require(*u.movementRemaining>=0,"Negative remaining movement");if(u.movementAllowance)require(*u.movementAllowance>=0,"Negative movement allowance");if(u.movementRemaining&&u.movementAllowance)require(*u.movementRemaining<=*u.movementAllowance,"Remaining movement exceeds allowance");
        unique(u.cargo,"Duplicate cargo reference");for(const auto& child:u.cargo){require(child!=id&&units.contains(child),"Unknown/self cargo reference");const auto& item=units.at(child);require(item.carriedBy&&*item.carriedBy==id,"Cargo links are not reciprocal");require(item.zone==u.zone,"Cargo and carrier locations differ");}
        if(u.carriedBy){require(units.contains(*u.carriedBy),"Unknown carrier");const auto& carrier=units.at(*u.carriedBy);require(std::count(carrier.cargo.begin(),carrier.cargo.end(),id)==1,"Carrier omits cargo");require(carrier.zone==u.zone,"Cargo and carrier locations differ");}
        std::set<Id> chain{id};auto parent=u.carriedBy;while(parent){require(chain.insert(*parent).second,"Cargo cycle");require(units.contains(*parent),"Unknown carrier");parent=units.at(*parent).carriedBy;}
    }
    for(const auto& [id,f]:facilities){require(!id.empty()&&id==f.id&&!f.type.empty(),"Invalid facility identity/type");land(f.zone);require(f.damage>=0,"Negative facility damage");require(!units.contains(id),"Unit/facility identity collision");if(definition->catalog){const auto& type=definition->catalog->facility(f.type);const auto captured=f.flags.find("captured_max_damage");const int maximum=captured==f.flags.end()?type.maxDamage.value_or(f.damage):captured->second;require(maximum>=0&&f.damage<=maximum,"Facility damage exceeds maximum");}}
    for(const auto& [id,r]:rails){require(!id.empty()&&id==r.id&&r.endpointA!=r.endpointB,"Invalid railway identity/endpoints");land(r.endpointA);land(r.endpointB);require(!units.contains(id)&&!facilities.contains(id),"Ambiguous repair target identity");for(const auto& [endpoint,damage]:r.damageByEndpoint)require((endpoint==r.endpointA||endpoint==r.endpointB)&&damage>=0,"Invalid railway damage endpoint");}
    for(const auto& [id,b]:construction){require(!id.empty()&&id==b.id&&!b.type.empty(),"Invalid construction identity/type");nation(b.owner);if(b.site)require(nodes.contains(*b.site)||facilities.contains(*b.site),"Unknown construction site");require(b.queuePosition>=1&&b.paidIpp>=0,"Invalid build stage/payment");for(auto payment:b.remainingPayments)require(payment>=0,"Negative remaining build payment");if(definition->catalog)require(definition->catalog->units().contains(b.type)||definition->catalog->facilities().contains(b.type),"Unknown construction type");}
    for(const auto& [id,r]:repairs){require(!id.empty()&&id==r.id,"Invalid repair identity");nation(r.owner);require(units.contains(r.target)||facilities.contains(r.target)||rails.contains(r.target)||territories.contains(r.target)||construction.contains(r.target),"Unknown repair target");require(r.remainingDamage>=0&&r.remainingCost>=0,"Negative repair work/cost");if(r.endpoint){require(rails.contains(r.target),"Only railroad repair has an endpoint");const auto& rail=rails.at(r.target);require(*r.endpoint==rail.endpointA||*r.endpoint==rail.endpointB,"Repair endpoint not on border");}}
    require(clock.roundIndex>=0&&clock.roundIndex<definition->calendarRounds,"Invalid calendar round");require(clock.completedRounds>=0&&clock.completedRounds<=definition->calendarRounds,"Invalid completed-round count");(void)currentNation();(void)toString(clock.phase);
    require(clock.completedRounds == clock.roundIndex + (terminal ? 1 : 0),
            "Completed rounds disagree with calendar cursor");
    require(!clock.incomeCollected || clock.phase == Phase::PlaceUnits,
            "Income collection is only valid during placement/end-of-turn accounting");
    require(completedTurns.size() == definition->turnOrder.size(),
            "Completed-turn inventory differs from national turn order");
    for (std::size_t index = 0; index < definition->turnOrder.size(); ++index) {
        const auto& id = definition->turnOrder[index];
        const int expected = terminal ? definition->calendarRounds
            : clock.roundIndex + (index < static_cast<std::size_t>(clock.nationIndex) ? 1 : 0);
        require(completedTurns.contains(id) && completedTurns.at(id) == expected,
                "Completed national turns disagree with calendar cursor: " + id);
    }
    for(const auto& [id,owner]:turnStart.possessions){land(id);if(owner)nation(*owner);}for(const auto& [id,pair]:turnStart.units){require(!id.empty(),"Empty snapshot unit identity");nation(pair.first);zone(pair.second);}
    require(!(politics.chineseTruce&&politics.trucePermanentlyEnded),"Terminated Chinese Truce is active");
    if(politics.chinaInvader)nation(*politics.chinaInvader);
    for(const auto& [id,actors]:politics.attackedWarlords){nation(id);for(const auto& actor:actors)nation(actor);}
    unique(politics.alignmentQueue,"Duplicate political alignment queue entry");for(const auto& id:politics.alignmentQueue)nation(id);
    for(const auto& [id,capital]:politics.capitals){nation(id);land(capital);}
    for(const auto& id:politics.surrendered)nation(id);for(const auto& id:politics.evolutionAwarded)nation(id);
    for(const auto& [id,payload]:politics.pending){require(!id.empty(),"Empty political continuation");(void)canonicalJson(payload);}
    require(!politics.surrendered.contains("ccp"),"CCP cannot surrender");
    const auto politicalKind=[](const Id& kind) {
        return kind.rfind("politics_",0)==0||kind.rfind("warlord_",0)==0||kind.rfind("truce_",0)==0
            ||kind.rfind("influence_",0)==0||kind.rfind("recruitment_",0)==0;
    };
    for(const auto& d:decisions)if(politicalKind(d.kind))require(politics.pending.contains(d.continuation),"Missing political decision continuation");
    if(chance&&politicalKind(chance->purpose))require(politics.pending.contains(chance->continuation),"Missing political chance continuation");
    std::set<Id> decisionIds;for(const auto& d:decisions){require(!d.id.empty()&&decisionIds.insert(d.id).second&&!d.kind.empty(),"Invalid/duplicate pending decision");nation(d.nation);const auto controller=politicalPlayer(*this,d.nation);require(definition->players.contains(controller),"Decision nation has no controlling player");std::set<Id> optionIds;for(const auto& a:d.options){require(!a.id.empty()&&optionIds.insert(a.id).second&&!a.kind.empty(),"Invalid/duplicate decision option");require(a.nation==d.nation&&a.player==controller&&a.decision&&*a.decision==d.id,"Decision option entitlement mismatch");require(a.parameters.isObject(),"Action parameters must be an object");}}
    for(const auto& [id,b]:battles){require(!id.empty()&&id==b.id&&!b.stage.empty(),"Invalid battle identity/stage");require(b.data.isObject(),"Battle continuation data must be an object");zone(b.zone);nation(b.attacker);nation(b.defender);const bool movementPlan=b.flags.contains("naval_movement_plan")&&b.flags.at("naval_movement_plan")==1&&b.defenders.empty()&&(b.stage=="naval_force_selection"||b.stage=="naval_screen_selection"||b.stage=="naval_moving");require(b.attacker!=b.defender||movementPlan||(b.defenders.empty()&&territories.contains(b.zone)&&(!territories.at(b.zone).possessor||(b.flags.contains("uncontested")&&b.flags.at("uncontested")==1))),"Battle opponents must differ except uncontested land or an explicit movement plan");unique(b.attackers,"Duplicate attacking unit");unique(b.defenders,"Duplicate defending unit");std::set<Id> participants;for(const auto* side:{&b.attackers,&b.defenders})for(const auto& unit:*side)require(units.contains(unit)&&participants.insert(unit).second,"Unknown/duplicate battle participant");for(const auto& [target,hits]:b.pendingHits)require(!target.empty()&&hits>=0,"Invalid pending hits");}
    unique(battleOrder,"Duplicate battle order entry");for(const auto& id:battleOrder)require(battles.contains(id),"Unknown battle order reference");
    if(chance){require(!chance->id.empty()&&!chance->purpose.empty()&&!chance->dice.empty(),"Incomplete chance request");nation(chance->nation);for(const auto& die:chance->dice){require(die.sides>=2&&die.maxRerolls>=0,"Invalid die specification");for(int face:die.rerollFaces)require(face>=1&&face<=die.sides,"Invalid reroll face");}}
    if(terminal) {
        require(decisions.empty()&&!chance&&battles.empty()&&battleOrder.empty()&&clock.incomeCollected&&clock.completedRounds==definition->calendarRounds,"Terminal state has unfinished work/accounting");
        require(clock.roundIndex==definition->calendarRounds-1&&clock.nationIndex==static_cast<int>(definition->turnOrder.size())-1&&clock.phase==Phase::PlaceUnits,"Terminal state is not at the final national turn");
        for(const auto& id:definition->turnOrder) require(completedTurns.contains(id)&&completedTurns.at(id)==definition->calendarRounds,"Terminal state has incomplete national turns");
    }
    // Validate free-form payload numbers even when no serialization was requested.
    (void)canonicalJson(toJson());
}
} // namespace game::campaign
