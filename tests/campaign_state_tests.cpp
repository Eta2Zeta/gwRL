#include "game/campaign.hpp"
#include "game/campaign_actions.hpp"

#include <cmath>
#include <functional>
#include <deque>
#include <iostream>
#include <limits>
#include <random>
#include <stdexcept>

namespace {
using namespace game::campaign;
using V=game::json::Value;
using O=V::Object;
void check(bool value,const std::string& message){if(!value)throw std::runtime_error(message);}
void rejects(const std::function<void()>& operation,const std::string& message){bool failed=false;try{operation();}catch(const std::exception&){failed=true;}check(failed,message);}
Definition definition() {
    Definition d;d.scenarioId="state_fixture";d.players={"axis","allies","comintern"};d.turnOrder={"ccp","mongolia","japan","kmt"};
    for(const auto& id:{"ccp","mongolia","japan","kmt","warlord"})d.factions.emplace(id,FactionDefinition{.id=id,.displayName=id});
    d.geography=V(O{{"nodes",V(O{{"a",V(O{{"id",V(std::string("a"))},{"type",V(std::string("land"))},{"original_owner",V(std::string("Japan"))}})},{"b",V(O{{"id",V(std::string("b"))},{"type",V(std::string("land"))},{"original_owner",V(std::string("Mongolia"))}})},{"sea",V(O{{"id",V(std::string("sea"))},{"type",V(std::string("sea"))}})}})},{"source_warning",V(std::string("Unresolved river network"))}});
    d.rules=V(O{{"catalog_status",V(std::string("not_implemented"))}});d.factions.at("japan").homeCountry={"a"};d.factions.at("japan").homeCountryKnown=true;return d;
}
State fixture() {
    State s;s.definition=freezeDefinition(definition());
    for(const auto& [id,f]:s.definition->factions)s.nations.emplace(id,NationState{});
    s.nations.at("ccp").player="comintern";s.nations.at("ccp").alliance="comintern";s.nations.at("ccp").treasury=2;
    s.nations.at("mongolia").player="comintern";s.nations.at("mongolia").alliance="comintern";s.nations.at("mongolia").powerStatus="controlled_minor_not_incorporated";
    s.nations.at("japan").player="axis";s.nations.at("japan").alliance="axis";s.nations.at("japan").treasury=15;s.nations.at("japan").powerStatus="major";
    s.nations.at("kmt").player="allies";s.nations.at("kmt").alliance="allies";s.nations.at("kmt").treasury=6;
    s.nations.at("warlord").powerStatus="unaligned_warlord";
    s.nations.at("kmt").atWarWith={"ccp"};s.nations.at("ccp").atWarWith={"kmt"};
    s.nations.at("japan").incomeComponents={{"land",9},{"penalty",-1}};s.nations.at("japan").incomeKnown=true;s.nations.at("japan").technologyStages={{"radar",2}};s.nations.at("japan").turnFlags={{"research",1}};s.nations.at("japan").gameFlags={{"event",1}};
    s.territories={{"a",TerritoryState{"japan",{{"occupied",1}}}},{"b",TerritoryState{"mongolia",{}}}};
    UnitState carrier;carrier.id="carrier";carrier.type="transport";carrier.owner="japan";carrier.zone="sea";carrier.turnOrigin="sea";carrier.movementRemaining=1;carrier.movementAllowance=2;carrier.cargo={"cargo"};carrier.route={"sea"};carrier.damage=1;carrier.commitments={"reserved"};carrier.turnFlags={{"moved",1}};carrier.gameFlags={{"veteran",1}};
    UnitState cargo;cargo.id="cargo";cargo.type="infantry";cargo.owner="kmt";cargo.zone="sea";cargo.turnOrigin="b";cargo.carriedBy="carrier";cargo.route={"b","sea"};
    UnitState defender;defender.id="defender";defender.type="militia";defender.owner="mongolia";defender.zone="b";defender.turnOrigin="b";
    s.units={{carrier.id,carrier},{cargo.id,cargo},{defender.id,defender}};
    s.facilities.emplace("port",FacilityState{"port","major_port","a",1,{{"blocked",1}}});
    s.rails.emplace("rail",RailState{"rail","a","b",{{"a",1},{"b",0}}});
    s.construction.emplace("ship",BuildProject{"ship","japan","fleet_carrier",std::optional<Id>("port"),3,5,{5,5},{{"national_queue",1}}});
    s.repairs.emplace("repair",RepairJob{"repair","japan","carrier",1,3,true});
    s.repairs.emplace("rail_repair",RepairJob{"rail_repair","japan","rail",1,1,true,std::optional<Id>("a")});
    s.completedTurns={{"ccp",0},{"mongolia",0},{"japan",0},{"kmt",0}};s.captureTurnStart();s.turnStart.units.emplace("historical_destroyed",std::pair{Id("kmt"),Id("a")});
    s.clock.playerTurnSerial=std::numeric_limits<std::uint64_t>::max();s.flags={{"rule_gate",1}};
    Decision d;d.id="reaction";d.kind="scramble";d.nation="mongolia";d.reaction=true;d.continuation="resume_battle";d.options.push_back(Action{"decline","decline","comintern","mongolia",std::optional<Id>("reaction"),V(O{{"choice",V(std::string("no\n\"scramble\""))}})});s.decisions.push_back(d);
    s.battles.emplace("battle",BattleState{"battle","b","japan","mongolia","defender_reaction",{"carrier"},{"defender"},{{"defender",1}},{{"round",2}}});s.battleOrder={"battle"};s.battles.at("battle").data=V(O{{"origin",V(std::string("a"))},{"stage_queue",V(V::Array{V(std::string("first_strike")),V(std::string("ordinary"))})}});
    s.chance=ChanceRequest{"roll","bombing","japan","resume_bombing",{{6,1,{1},1},{12,-1,{},0}}};
    s.history.push_back(Event{"fixture",V(O{{"text",V(std::string("歴史"))}}),"previous"});s.validate();return s;
}
void digestsAndCanonicalJson() {
    check(contentDigest("")=="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855","SHA-256 empty vector");
    check(contentDigest("abc")=="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad","SHA-256 abc vector");
    check(contentDigest(std::string(1000000,'a'))=="cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0","SHA-256 multiblock vector");
    // Lengths on both sides of the 56- and 64-byte padding boundaries.
    const std::map<std::size_t,std::string> boundaries{
        {3,"2fe3269fa210706de21ff97cc964590ec5bddd6677885fc55cfa6bfd94924822"},{55,"7cda990214cc40c5e59b2a5f09f1c34da7ea4a7d44479d36b150ea7c04aa009a"},
        {56,"642b572edefc37c5664b4b95a7a83bdc5617dc06b241bfac5c8094b10fec734e"},{63,"125d5830922e3666b5891332b54f12d328861b7ec30fec51a03fa27bbe549642"},
        {64,"15c32cfa73534b3c34a1244e4331e3757b34daf267f6a7322d471c849e3a5c65"},{65,"ddd761939cd192b02ac5b652b6f4763b0351e0c40a325432c318b0aab6c4afc5"},
        {119,"a1913d07c18ff09efb38be9e5317b92e7a4cf103f6fb7448257c30c7cab59462"},{120,"f9fe9011baded2c49c901e5d4d74f66a00f057070e9e9d641b566eeea45f3be3"},
        {1000,"4256460c8769ec1a1d2a8e3edeeda0d3cc4fbc30b3c0f6a2b53da3ef9f60ea5e"}};
    for(const auto& [size,expected]:boundaries) {
        std::string text;for(std::size_t i=0;i<size;++i)text.push_back(static_cast<char>('a'+(i*7)%26));
        check(contentDigest(text)==expected,"SHA-256 padding boundary vector");
    }
    const std::map<std::string,std::string> published{
        {"","e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
        {"abc","ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"},
        {"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq","248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"},
        {"abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu","cf5b16a778af8380036ce59e7b0492370b249b11e8f07a51afac45037afee9d1"}};
    for(const auto& [text,expected]:published)check(contentDigest(text)==expected&&portableContentDigest(text)==expected,"SHA-256 published vector");
    // Every length across several blocks, then longer texts, at shifted starts.
    std::mt19937_64 random(2048);
    const auto samePaths=[&](std::size_t size) {
        std::string text(size+8,'\0');for(auto& c:text)c=static_cast<char>(random());
        check(contentDigest(text)==portableContentDigest(text),"Hardware and portable SHA-256 differ");
        const auto shifted=text.substr(random()%8);
        check(contentDigest(shifted)==portableContentDigest(shifted),"Hardware and portable SHA-256 differ on a shifted buffer");
    };
    for(std::size_t size=0;size<=320;++size)samePaths(size);
    for(int sample=0;sample<200;++sample)samePaths(random()%100000);
    const auto raw=V(O{{"z",V(-0.0)},{"a",V(std::string("\x01\n\"\\"))}});const auto serialized=canonicalJson(raw);check(canonicalJson(game::json::parse(serialized))==serialized,"Canonical escaped JSON round trip");
    rejects([]{canonicalJson(V(std::numeric_limits<double>::infinity()));},"Nonfinite JSON accepted");
    for(auto p:{Phase::Production,Phase::CombatMovement,Phase::Combat,Phase::NonCombatMovement,Phase::PlaceUnits})check(parsePhase(toString(p))==p,"Phase round trip");
    rejects([]{parsePhase("legacy_purchase_units");},"Unknown phase accepted");
}
void completeRoundTrip() {
    const auto s=fixture();const auto encoded=s.serialize();auto restored=State::fromJson(s.definition,game::json::parse(encoded));check(restored.serialize()==encoded,"Complete mutable state was not round-tripped");check(restored.definition.get()==s.definition.get(),"Restore replaced immutable definition");check(restored.clock.playerTurnSerial==std::numeric_limits<std::uint64_t>::max(),"64-bit turn counter lost precision");check(restored.nations.at("mongolia").treasury==std::nullopt,"No-account state became zero cash");check(restored.nations.at("japan").incomeKnown&&!restored.nations.at("kmt").incomeKnown,"Known vs unresolved income was lost");check(!restored.units.at("cargo").movementAllowance,"Unresolved movement became zero");check(restored.units.at("cargo").owner=="kmt"&&restored.units.at("carrier").owner=="japan","Cargo ownership merged with carrier");check(restored.turnStart.units.contains("historical_destroyed"),"Historical destroyed unit was discarded");
    auto wrong=definition();wrong.rules=V(O{{"different",V(true)}});rejects([&]{State::fromJson(freezeDefinition(wrong),game::json::parse(encoded));},"Wrong immutable definition accepted");
    auto json=game::json::parse(encoded).asObject();auto c=json.at("clock").asObject();c["player_turn_serial"]=V(std::string("18446744073709551616"));json["clock"]=V(c);rejects([&]{State::fromJson(s.definition,V(json));},"Overflow counter accepted");
    c["player_turn_serial"]=V(1.0);json["clock"]=V(c);rejects([&]{State::fromJson(s.definition,V(json));},"Numeric lossy counter accepted");
    ChanceOutcome outcome{{{1,5},{12}}};check(canonicalJson(outcomeJson(outcomeFromJson(outcomeJson(outcome))))==canonicalJson(outcomeJson(outcome)),"Outcome round trip");
}
void cloneIsolationAndKeys() {
    const auto original=fixture();const auto before=original.serialize();const auto key=original.planningKey();auto copy=original.clone();check(copy.definition.get()==original.definition.get(),"Clone copied definition");
    const std::vector<std::function<void(State&)>> changes={
        [](State&s){s.nations.at("japan").treasury=14;},[](State&s){s.nations.at("mongolia").player="allies";},[](State&s){s.nations.at("japan").incomeComponents["land"]=8;},[](State&s){s.nations.at("japan").incomeKnown=false;},[](State&s){s.nations.at("japan").technologyStages["radar"]=3;},[](State&s){s.nations.at("japan").gameFlags["event"]=0;},
        [](State&s){s.territories.at("a").possessor="kmt";},[](State&s){s.units.at("carrier").movementRemaining=0;},[](State&s){s.units.at("carrier").route.push_back("a");},[](State&s){s.units.at("carrier").commitments.insert("another");},[](State&s){s.units.at("cargo").owner="japan";},[](State&s){s.units.at("carrier").damage=0;},
        [](State&s){s.facilities.at("port").flags["blocked"]=0;},[](State&s){s.rails.at("rail").damageByEndpoint["b"]=1;},[](State&s){s.construction.at("ship").remainingPayments[0]=4;},[](State&s){s.repairs.at("repair").restrictsAction=false;},[](State&s){s.repairs.at("rail_repair").endpoint="b";},
        [](State&s){s.clock.incomeCollected=true;},[](State&s){s.completedTurns.at("ccp")=1;},[](State&s){s.turnStart.possessions.at("a")="kmt";},[](State&s){s.turnStart.units.at("cargo").first="japan";},
        [](State&s){s.decisions.back().continuation="different";},[](State&s){s.decisions.back().options[0].parameters=V(O{{"choice",V(true)}});},[](State&s){s.battles.at("battle").pendingHits["defender"]=2;},[](State&s){s.battles.at("battle").data=V(O{{"origin",V(std::string("b"))}});},[](State&s){s.chance->dice[0].modifier=2;},[](State&s){s.flags["rule_gate"]=2;}
    };
    for(const auto& change:changes){copy=original.clone();change(copy);check(copy.planningKey()!=key,"Planning key omitted a mutable decision/outcome field");check(original.serialize()==before,"Clone mutation changed original");}
    copy=original.clone();copy.history.push_back(Event{"another",V(nullptr),"other"});check(copy.planningKey()==key,"History polluted planning identity");check(copy.serialize()!=before,"Exact state serialization omitted history");
    check(!original.observation().find("history")&&!original.observation().find("definition_fingerprint"),"Policy observation leaked execution/provenance fields");
    auto unknown=definition();unknown.factions.at("japan").homeCountryKnown=false;check(freezeDefinition(unknown)->fingerprint!=original.definition->fingerprint,"Known vs unknown homeland omitted from definition identity");
}
void invalidReferencesAndCargo() {
    const auto original=fixture();const std::vector<std::function<void(State&)>> bad={
        [](State&s){s.nations.erase("warlord");},[](State&s){s.nations.at("mongolia").controllerNation="comintern";},[](State&s){s.nations.at("japan").player="missing";},[](State&s){s.nations.at("japan").treasury=-1;},[](State&s){s.territories.erase("a");},[](State&s){s.territories.at("a").possessor="missing";},
        [](State&s){s.units.at("cargo").owner="missing";},[](State&s){s.units.at("cargo").zone="b";},[](State&s){s.units.at("carrier").cargo.clear();},[](State&s){s.units.at("carrier").cargo.push_back("cargo");},[](State&s){s.units.at("carrier").carriedBy="cargo";s.units.at("cargo").cargo={"carrier"};},[](State&s){s.units.at("carrier").movementRemaining=3;},
        [](State&s){s.facilities.at("port").zone="sea";},[](State&s){s.rails.at("rail").damageByEndpoint["sea"]=1;},[](State&s){s.construction.at("ship").site="missing";},[](State&s){s.repairs.at("repair").target="missing";},[](State&s){s.repairs.at("rail_repair").endpoint="sea";},
        [](State&s){s.clock.nationIndex=4;},[](State&s){s.clock.roundIndex=11;},
        [](State&s){s.clock.completedRounds=1;},
        [](State&s){s.completedTurns.erase("ccp");},
        [](State&s){s.completedTurns["warlord"]=0;},
        [](State&s){s.completedTurns["ccp"]=1;},
        [](State&s){s.clock.nationIndex=1;},
        [](State&s){s.clock.incomeCollected=true;},[](State&s){s.turnStart.units.at("cargo").first="missing";},[](State&s){s.decisions.back().options[0].player="axis";},[](State&s){s.decisions.back().options[0].decision="different";},[](State&s){s.battles.at("battle").defenders={"missing"};},[](State&s){s.battleOrder={"missing"};},[](State&s){s.battles.at("battle").data=V(1.0);},[](State&s){s.chance->dice[0].rerollFaces={7};},[](State&s){s.terminal=true;}
    };for(const auto& mutation:bad){auto state=original.clone();mutation(state);rejects([&]{state.validate();},"Malformed state accepted");}
}
void consistentClockProgression() {
    auto s = fixture();
    s.chance.reset();
    s.decisions.clear();
    s.battles.clear();
    s.battleOrder.clear();
    // Ending CCP's turn advances its count before Mongolia becomes active.
    s.completedTurns.at("ccp") = 1;
    s.clock.nationIndex = 1;
    s.validate();
    // Collection can wait for a later reaction without finishing the current turn.
    s.clock.phase = Phase::PlaceUnits;
    s.clock.incomeCollected = true;
    s.validate();
    // A completed half-year opens the next round with all nations at one turn.
    for (const auto& id : s.definition->turnOrder) s.completedTurns.at(id) = 1;
    s.clock.roundIndex = 1;
    s.clock.completedRounds = 1;
    s.clock.nationIndex = 0;
    s.clock.phase = Phase::Production;
    s.clock.incomeCollected = false;
    s.validate();
}
void nationalityRoutingCalendarAndSnapshot() {
    auto s=fixture();check(!s.decisionPlayer(),"Chance request exposed player action");s.chance.reset();check(s.currentNation()=="ccp"&&s.decisionPlayer()==std::optional<Id>("comintern"),"Reaction routing wrong");s.decisions.back().nation="kmt";s.decisions.back().options.clear();check(s.decisionPlayer()==std::optional<Id>("allies"),"Defender not routed independently of player turn");s.decisions.clear();s.clock.nationIndex=1;check(s.currentNation()=="mongolia"&&s.decisionPlayer()==std::optional<Id>("comintern"),"Mongolia nationality merged with player");check(!s.nations.contains("ussr")&&!s.nations.contains("comintern"),"Player/source controller became a nation");
    check(s.calendarDate()==std::pair{1936,7},"Initial calendar date");s.clock.roundIndex=1;check(s.calendarDate()==std::pair{1937,1},"Half-year rollover");s.clock.roundIndex=10;check(s.calendarDate()==std::pair{1941,7},"Final round date");
    s.captureTurnStart();s.territories.at("a").possessor="kmt";s.units.erase("defender");check(s.turnStart.possessions.at("a")=="japan"&&s.turnStart.units.contains("defender"),"Beginning-turn snapshot changed with mutable state");
    s.battles.clear();s.battleOrder.clear();s.clock.completedRounds=11;s.clock.incomeCollected=true;s.clock.nationIndex=3;s.clock.phase=Phase::PlaceUnits;for(const auto& id:s.definition->turnOrder)s.completedTurns[id]=11;s.terminal=true;s.validate();auto incomplete=s.clone();incomplete.completedTurns["ccp"]=10;rejects([&]{incomplete.validate();},"Premature national-turn completion accepted");check(!s.decisionPlayer(),"Terminal state still exposes actor");
}
std::set<Id> referenceGeometry(const Definition& definition,const Id& start,int range) {
    std::set<Id> zones{start};
    std::deque<std::pair<Id,int>> pending{{start,0}};
    while(!pending.empty()) {
        const auto [zone,distance]=pending.front();pending.pop_front();
        if(distance>=range)continue;
        for(const auto& edge:definition.geography.require("nodes").require(zone).require("neighbors").asArray()) {
            const auto& next=edge.require("neighbor_id").asString();
            if(zones.insert(next).second)pending.emplace_back(next,distance+1);
        }
    }
    return zones;
}
void immutableIndexedGeometry() {
    auto source=definition();
    O nodes;
    const std::map<Id,std::vector<Id>> links{{"a",{"c","b","c"}},{"b",{"d"}},{"c",{"a","d"}},{"d",{"sea"}},{"isolated",{}},{"sea",{}}};
    for(const auto& [id,neighbors]:links) {
        V::Array edges;for(const auto& next:neighbors)edges.emplace_back(O{{"neighbor_id",V(next)}});
        nodes.emplace(id,V(O{{"id",V(id)},{"type",V(std::string(id=="sea"?"sea":"land"))},{"neighbors",V(std::move(edges))}}));
    }
    source.geography=V(O{{"nodes",V(nodes)}});
    const auto frozen=freezeDefinition(source);
    check(frozen->indexedGeography!=nullptr,"Complete geography was not indexed");
    const auto& index=*frozen->indexedGeography;
    check(index.nodeIds==std::vector<Id>({"a","b","c","d","isolated","sea"}),"Dense IDs lost lexical ordering");
    std::vector<Id> adjacent;for(auto next:index.adjacency.at(index.nodeIndices.at("a")))adjacent.push_back(index.nodeIds.at(next));
    check(adjacent==links.at("a"),"Dense adjacency changed source order or duplicate edges");
    for(const auto& [start,neighbors]:links)for(int range=-2;range<=8;++range)
        check(index.withinHops(start,range)==referenceGeometry(*frozen,start,range),"Indexed directed reachability differs from reference BFS");
    check(!index.withinHops("sea",8).contains("a"),"Directed geometry became undirected");
    auto unchanged=*frozen;unchanged.indexedGeography.reset();
    check(freezeDefinition(unchanged)->fingerprint==frozen->fingerprint,"Derived geometry changed definition identity");
    auto edited=*frozen;
    auto a=nodes.at("a").asObject();a["neighbors"]=V(V::Array{});nodes["a"]=V(a);edited.geography=V(O{{"nodes",V(nodes)}});
    const auto refrozen=freezeDefinition(edited);
    check(refrozen->indexedGeography.get()!=frozen->indexedGeography.get(),"Re-freeze reused a potentially stale geometry view");
    check(refrozen->indexedGeography->withinHops("a",8)==std::set<Id>{"a"} && index.withinHops("a",8).contains("sea"),"Edited geometry corrupted or reused prior distances");
    check(!freezeDefinition(definition())->indexedGeography,"Incomplete foundation map received invented adjacency");
    const auto actual=loadScenario(std::filesystem::path(GWRL_SOURCE_DIR)/"game_content/scenarios/japan_china_1936");
    check(actual.definition->indexedGeography!=nullptr,"Campaign geography has no dense view");
    for(const auto& start:actual.definition->indexedGeography->nodeIds)for(int range=-1;range<=10;++range)
        check(actual.definition->indexedGeography->withinHops(start,range)==referenceGeometry(*actual.definition,start,range),"Campaign geometry differs from reference BFS");
    // Map reads through the index match reading the JSON, duplicates and all.
    const auto sameReads=[](const State& state) {
        for(const auto& [id,node]:state.definition->geography.require("nodes").asObject()) {
            check(findMapNode(state,id) && canonicalJson(mapNode(state,id))==canonicalJson(node),"Indexed node differs from its JSON");
            std::vector<Id> expected;
            for(const auto& edge:node.require("neighbors").asArray())expected.push_back(edge.require("neighbor_id").asString());
            check(mapNeighbors(state,id).ids()==expected,"Indexed neighbors changed source order or duplicates");
            for(const auto& next:expected) {
                const V* first=nullptr;
                for(const auto& edge:node.require("neighbors").asArray())
                    if(!first && edge.require("neighbor_id").asString()==next)first=&edge;
                check(mapEdge(state,id,next) && canonicalJson(*mapEdge(state,id,next))==canonicalJson(*first),"Indexed edge is not the first edge to its neighbor");
            }
            check(!mapEdge(state,id,"missing"),"Indexed edge invented a neighbor");
        }
        check(!findMapNode(state,"missing"),"Unknown node found");
        rejects([&]{mapNode(state,"missing");},"Unknown node read");
        rejects([&]{mapNeighbors(state,"missing");},"Unknown node neighbors listed");
        rejects([&]{mapEdge(state,"missing","a");},"Unknown node edge read");
    };
    State indexed;indexed.definition=frozen;
    sameReads(indexed);sameReads(actual);
    const auto bare=fixture();
    check(!bare.definition->indexedGeography && canonicalJson(mapNode(bare,"a"))==canonicalJson(bare.definition->geography.require("nodes").require("a")),
          "Unindexed node read differs from its JSON");
    rejects([&]{mapNeighbors(bare,"a");},"Unindexed node without edges listed neighbors");
}
V nestedNumber(double number) {
    return V(O{{"outer",V(V::Array{V(nullptr),V(true),V("opaque\n中国"),V(O{{"number",V(number)}})})}});
}
void everyFreeFormPayloadRetainsFiniteValidation() {
    const std::vector<std::function<void(State&,const V&)>> payloads{
        [](State& s,const V& v){s.politics.pending["opaque_finite_fixture"]=v;},
        [](State& s,const V& v){s.decisions.back().options.front().parameters=v;},
        [](State& s,const V& v){s.battles.begin()->second.data=v;},
        [](State& s,const V& v){
            // Recorded events are immutable; rebuild the log with an edited first event.
            std::vector<Event> events=s.history;events.front().payload=v;
            s.history.clear();for(auto& event:events)s.history.push_back(std::move(event));},
    };
    for(const auto& replace:payloads) {
        for(const double number:{std::numeric_limits<double>::quiet_NaN(),
                std::numeric_limits<double>::infinity(),-std::numeric_limits<double>::infinity()}) {
            auto state=fixture();replace(state,nestedNumber(number));
            rejects([&]{state.validate();},"Nested nonfinite free-form state number accepted");
        }
        for(const double number:{-0.0,0.0,1.25,std::numeric_limits<double>::max(),
                std::numeric_limits<double>::lowest(),std::numeric_limits<double>::denorm_min()}) {
            auto state=fixture();replace(state,nestedNumber(number));
            const auto before=canonicalJson(state.toJson());state.validate();
            check(canonicalJson(state.toJson())==before,"Finite validation changed a payload or its canonical spelling");
        }
    }
    // Action-interface numbers have their own integer/schema checks as well.
    // Exercise a valid nested raider-configuration field, not an unknown field
    // that would be rejected regardless of whether its number was finite.
    auto state=loadScenario(std::filesystem::path(GWRL_SOURCE_DIR)/"game_content/scenarios/japan_china_1936");
    state.units.clear();
    UnitState unit;unit.id="finite_raider";unit.type="battlecruiser";unit.owner=state.currentNation();
    unit.zone=unit.turnOrigin="sea_p15";unit.movementAllowance=unit.movementRemaining=0;unit.gameFlags["raider"]=0;
    state.units.emplace(unit.id,unit);
    auto configuration=[&](double number) {
        return V(O{{"schema",V(trainingActionSchema)},{"visited_configurations",V(V::Array{V(O{
            {"raiders",V(O{{unit.id,V(O{{"raider",V(number)}})}})},
            {"aircraft",V(O{})},{"carriers",V(O{})}})})},{"declined_rail_requests",V(V::Array{})}});
    };
    state.actionInterface=configuration(-0.0);state.validate();
    check(std::signbit(state.actionInterface.require("visited_configurations").asArray().front()
        .require("raiders").require(unit.id).require("raider").asNumber()),"Validation normalized a stored negative zero");
    for(const double number:{std::numeric_limits<double>::quiet_NaN(),
            std::numeric_limits<double>::infinity(),-std::numeric_limits<double>::infinity()}) {
        state.actionInterface=configuration(number);
        rejects([&]{state.validate();},"Nested nonfinite action-interface number accepted");
    }
}
// Strings are appended in whole runs; they must escape exactly as written one
// character at a time, wherever an escaped byte falls.
void canonicalStringsEscapeEveryByte() {
    const auto escaped=[](const std::string& text) {
        static constexpr char hex[]="0123456789abcdef";std::string out="\"";
        for(unsigned char c:text) {
            if(c=='"'||c=='\\'){out+='\\';out+=static_cast<char>(c);}
            else if(c<32){out+="\\u00";out+=hex[c>>4];out+=hex[c&15];}
            else out+=static_cast<char>(c);
        }
        return out+'"';
    };
    const auto same=[&](const std::string& text) {
        check(canonicalJson(V(text))==escaped(text),"Canonical string differs from its escaped characters");
        check(canonicalJson(V(O{{text,V(1.0)}}))=="{"+escaped(text)+":1}","Canonical key differs from its escaped characters");
    };
    same("");
    for(int byte=0;byte<256;++byte) {
        const std::string c(1,static_cast<char>(byte));
        for(const auto& text:{c,c+c+c,"ab"+c,c+"cd","ab"+c+"cd","ab"+c+"cd"+c})same(text);
    }
    std::mt19937_64 random(2049);
    for(int sample=0;sample<2000;++sample) {
        std::string text(random()%64,'\0');
        for(auto& c:text)c=random()%8?static_cast<char>('a'+random()%26):static_cast<char>(random());
        same(text);
    }
}
// Saves and planning keys write the state's canonical text directly; it must
// equal the text of the JSON tree, including decisions, battles and history.
void directTextMatchesJsonTree() {
    const auto same=[](const State& state) {
        check(state.serialize()==canonicalJson(state.toJson()),"Direct saved text differs from the JSON tree");
        check(state.planningKey()==contentDigest(canonicalJson(state.toJson(false))),"Direct planning text differs from the JSON tree");
    };
    same(fixture());
    auto engine=Engine::start(loadScenario(std::filesystem::path(GWRL_SOURCE_DIR)/"game_content/scenarios/japan_china_1936"),
                              trainingCampaignRules(),7);
    std::mt19937 choose(7);
    for(int step=0;step<400 && !engine.state().terminal;++step) {
        same(engine.state());
        if(engine.state().chance) {engine.resolveChance();continue;}
        const auto actions=engine.legalActions();
        if(actions.empty())break;
        engine.step(actions[choose()%actions.size()]);
    }
}
}
int main(){try{digestsAndCanonicalJson();completeRoundTrip();cloneIsolationAndKeys();invalidReferencesAndCargo();consistentClockProgression();nationalityRoutingCalendarAndSnapshot();immutableIndexedGeometry();everyFreeFormPayloadRetainsFiniteValidation();canonicalStringsEscapeEveryByte();directTextMatchesJsonTree();std::cout<<"campaign state tests passed\n";return 0;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
