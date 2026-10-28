#include "game/catalog.hpp"

#include <algorithm>
#include <fstream>
#include <iterator>
#include <numeric>
#include <stdexcept>

namespace game::campaign {
namespace {
using V = json::Value;
// Builds the message only on failure; most messages are literals.
template <class Message> void require(bool ok, const Message &message) { if (!ok) throw std::runtime_error(message); }
std::optional<int> optionalInt(const V& v) { return v.isNull() ? std::nullopt : std::optional<int>(v.asInt()); }
std::optional<Id> optionalId(const V& v) { return v.isNull() ? std::nullopt : std::optional<Id>(v.asString()); }
std::vector<int> integers(const V& v) { std::vector<int> out; for (const auto& x:v.asArray()) out.push_back(x.asInt()); return out; }
std::set<Id> ids(const V& v) { std::set<Id> out; for(const auto& x:v.asArray()) require(out.insert(x.asString()).second,"Duplicate catalog list entry"); return out; }
std::string readBytes(const std::filesystem::path& p) { std::ifstream f(p,std::ios::binary); require(bool(f),"Cannot open catalog source: "+p.string()); return {std::istreambuf_iterator<char>(f),{}}; }
int date(const std::string& s) {
    require(s.size()==7 && s[4]=='-',"Invalid catalog date: "+s);
    for(std::size_t i=0;i<s.size();++i) require(i==4 || (s[i]>='0'&&s[i]<='9'),"Invalid catalog date");
    const int y=std::stoi(s.substr(0,4)),m=std::stoi(s.substr(5)); require(y>0 && m>=1 && m<=12,"Invalid catalog date"); return y*100+m;
}
std::optional<int> optionalDate(const V& v) { return v.isNull()?std::nullopt:std::optional<int>(date(v.asString())); }
bool flag(const CatalogContext& c,const Id& id) {
    if(c.disabledFlags.contains(id)) return false;
    if(const auto i=c.flags.find(id); i!=c.flags.end()) return i->second;
    for(const auto* source:c.flagSources) if(const auto i=source->find(id); i!=source->end()) return i->second!=0;
    return false;
}
bool flags(const CatalogContext& c,const V* list) { if(list) for(const auto& x:list->asArray()) if(!flag(c,x.asString())) return false; return true; }
bool hasTechnologies(const CatalogContext& c,const std::set<Id>& list) { return std::includes(c.technologies.begin(),c.technologies.end(),list.begin(),list.end()); }
std::vector<CatalogUpgrade> upgrades(const V& list) {
    std::vector<CatalogUpgrade> out;
    for(const auto& v:list.asArray()) {
        CatalogUpgrade u; u.to=v.require("to").asString();u.costIpp=v.require("cost_ipp").asInt();u.automatic=v.require("automatic").asBool();u.requiredTechnologies=ids(v.require("requires_technology"));u.parameters=v.require("parameters");u.sourceRefs=v.require("source_refs");require(u.costIpp>=0,"Negative upgrade price");out.push_back(std::move(u));
    } return out;
}
void prices(const std::vector<int>& costs) { for(int n:costs) require(n>=0,"Negative catalog price"); }
void references(const V& value,const std::set<Id>& sources) {
    if(value.isArray()) { for(const auto& x:value.asArray()) references(x,sources); }
    else if(value.isObject()) {
        if(const auto* source=value.find("source_id")) { require(sources.contains(source->asString()),"Unknown catalog source reference");if(const auto* page=value.find("pdf_page"))require(page->asInt()>0,"Invalid source page"); }
        for(const auto& [k,x]:value.asObject()) references(x,sources);
    }
}
}

std::shared_ptr<const Catalog> Catalog::load(const std::filesystem::path& directory) {
    V::Object documents;
    const auto root=std::filesystem::absolute(directory).lexically_normal().parent_path().parent_path().parent_path();
    for(const auto* file:{"land_air","naval","facilities","technologies","build_charts"}) {
        auto document=json::parseFile(directory/(std::string(file)+".json"));
        for(const auto& source:document.require("sources").asArray()) {
            if(const auto* path=source.find("path")) require(contentDigest(readBytes(root/path->asString()))==source.require("sha256").asString(),"Catalog source hash mismatch: "+path->asString());
            else require(source.require("kind").asString()=="user_ruling" && !source.require("text").asString().empty(),"Catalog source lacks verifiable provenance");
        }
        documents.emplace(file,std::move(document));
    }
    auto catalog=fromJson(V(std::move(documents))); catalog->requireComplete(); return catalog;
}

std::shared_ptr<const Catalog> Catalog::fromJson(const V& documents) {
    auto out=std::shared_ptr<Catalog>(new Catalog);out->sourceData_=documents;
    for(const auto& [file,doc]:documents.asObject()) {
        require(doc.require("schema_version").asInt()==1,"Unsupported catalog schema");
        std::set<Id> sources;for(const auto& source:doc.require("sources").asArray())require(sources.insert(source.require("id").asString()).second,"Duplicate catalog source");references(doc,sources);
        if(const auto* list=doc.find("units")) for(const auto& v:list->asArray()) {
            UnitDefinition u;u.id=v.require("id").asString();u.name=v.require("name").asString();u.classes=ids(v.require("classes"));u.purchaseCosts=integers(v.require("purchase_costs"));u.assetValue=optionalInt(v.require("asset_value"));u.maxHits=v.require("max_hits").asInt();u.targetClasses=ids(v.require("target_classes"));u.abilities=ids(v.require("abilities"));u.upgrades=upgrades(v.require("upgrades"));u.rules=v.require("rules");u.repair=v.require("repair");u.sourceRefs=v.require("source_refs"); if(const auto* p=v.find("unresolved_fields"))u.unresolved=*p;
            require(!u.id.empty()&&!u.name.empty()&&!u.classes.empty()&&u.maxHits>0,"Invalid unit definition");prices(u.purchaseCosts);
            for(const auto& s:v.require("states").asArray()) {
                CatalogStats x;x.attack=optionalInt(s.require("attack"));x.defense=optionalInt(s.require("defense"));x.attackDice=s.require("attack_dice").asInt();x.defenseDice=s.require("defense_dice").asInt();x.movement=optionalInt(s.require("movement"));x.bombardment=optionalInt(s.require("bombardment"));x.bombardmentDice=s.require("bombardment_dice").asInt();x.cargoCapacity=optionalInt(s.require("cargo_capacity"));x.carrierCapacity=optionalInt(s.require("carrier_capacity"));
                const int damage=s.require("damage").asInt(); require(damage>=0&&damage<u.maxHits,"Invalid surviving damage state");for(auto n:{x.attack,x.defense,x.bombardment})require(!n||(*n>=0&&*n<=12),"Invalid D12 combat threshold");for(auto n:{x.movement,x.cargoCapacity,x.carrierCapacity})require(!n||*n>=0,"Negative unit capacity/movement");require(x.attackDice>=0&&x.defenseDice>=0&&x.bombardmentDice>=0,"Negative combat dice");require(u.states.emplace(damage,x).second,"Duplicate damage state");
            }
            require(u.states.size()==static_cast<std::size_t>(u.maxHits),"Missing surviving unit state: "+u.id);
            std::set<Id> modes;
            for(const auto& m:v.require("modes").asArray()) {
                CatalogMode x;x.id=m.require("id").asString();x.threshold=optionalInt(m.require("threshold"));x.dieSides=m.require("die_sides").asInt();x.dice=m.require("dice").asInt();x.requiredTechnologies=ids(m.require("requires_technology"));x.parameters=m.require("parameters");x.sourceRefs=m.require("source_refs");require(modes.insert(x.id).second&&x.dice>=0&&(x.dice==0||x.dieSides>=2),"Invalid/duplicate unit mode");u.modes.push_back(std::move(x));
            }
            require(out->units_.emplace(u.id,std::move(u)).second,"Duplicate unit type");
        }
        if(const auto* list=doc.find("facilities"))for(const auto& v:list->asArray()) {
            FacilityDefinition f;f.id=v.require("id").asString();f.name=v.require("name").asString();f.purchaseCosts=integers(v.require("purchase_costs"));f.assetValue=v.require("asset_value").asInt();f.maxDamage=optionalInt(v.require("max_damage"));f.repairCost=optionalInt(v.require("repair_cost_per_damage"));f.productionCapacity=v.require("production_capacity").asInt();f.repairCapacity=v.require("repair_capacity").asInt();f.aaThreshold=optionalInt(v.require("aaa").require("threshold"));f.aaDice=v.require("aaa").require("dice").asInt();f.abilities=ids(v.require("abilities"));f.upgrades=upgrades(v.require("upgrades"));f.rules=v.require("rules");f.sourceRefs=v.require("source_refs");prices(f.purchaseCosts);require(!f.id.empty()&&!f.name.empty()&&f.assetValue>=0&&f.productionCapacity>=0&&f.repairCapacity>=0,"Invalid facility");require(out->facilities_.emplace(f.id,std::move(f)).second,"Duplicate facility");
        }
        if(const auto* list=doc.find("technologies"))for(const auto& v:list->asArray()) {
            TechnologyDefinition t;t.id=v.require("id").asString();t.name=v.require("name").asString();t.thresholds=integers(v.require("thresholds"));t.stageThreeFrom=date(v.require("stage_iii_from").asString());t.unlocks=ids(v.require("unlocks"));t.abilities=ids(v.require("abilities"));t.modifiers=v.require("modifiers");t.conversions=v.require("conversions");t.rules=v.require("rules");t.sourceRefs=v.require("source_refs");require(t.thresholds.size()==4,"Technology must have four stages");for(int n:t.thresholds)require(n>=1&&n<=12,"Invalid research threshold");require(out->technologies_.emplace(t.id,std::move(t)).second,"Duplicate technology");
        }
        if(const auto* list=doc.find("rows"))for(const auto& v:list->asArray()) {
            BuildChartRow r;r.id=v.require("id").asString();r.nation=v.require("nation").asString();r.powerStatus=v.require("power_status").asString();r.type=v.require("type").asString();r.kind=v.require("kind").asString();r.purchaseCosts=integers(v.require("purchase_costs"));r.availableFrom=optionalDate(v.require("available_from"));r.availableThrough=optionalDate(v.require("available_through"));r.requiredTechnologies=ids(v.require("requires_technology"));r.forbiddenTechnologies=ids(v.require("forbids_technology"));r.cap=optionalInt(v.require("cap_per_turn"));r.capGroup=optionalId(v.require("cap_group"));r.requiredFlags=ids(v.require("requires_flags"));r.placement=ids(v.require("placement"));r.upgradesFrom=optionalId(v.require("upgrades_from"));if(const auto* d=v.find("derived_from"))r.derivedFrom=optionalId(*d);r.sourceRefs=v.require("source_refs");r.notes=v.require("notes").asString();prices(r.purchaseCosts);require(!r.id.empty()&&!r.purchaseCosts.empty()&&(r.kind=="purchase"||r.kind=="upgrade")&&(!r.cap||*r.cap>0),"Invalid build-chart row");require(out->rows_.emplace(r.id,std::move(r)).second,"Duplicate build-chart row");
        }
    }
    const auto knownType=[&](const Id& id){return out->units_.contains(id)||out->facilities_.contains(id);};
    const auto knownTech=[&](const auto& list){for(const auto& id:list)require(out->technologies_.contains(id),"Unknown required technology: "+id);};
    for(const auto& [id,u]:out->units_) {require(!out->facilities_.contains(id),"Ambiguous catalog type");for(const auto& m:u.modes)knownTech(m.requiredTechnologies);for(const auto& up:u.upgrades){require(knownType(up.to),"Unknown upgrade target");knownTech(up.requiredTechnologies);}}
    for(const auto& [id,f]:out->facilities_) for(const auto& up:f.upgrades){require(knownType(up.to),"Unknown facility upgrade target");knownTech(up.requiredTechnologies);}
    for(const auto& [id,t]:out->technologies_) {for(const auto& type:t.unlocks)require(knownType(type),"Unknown technology unlock");for(const auto& c:t.conversions.asArray())require(knownType(c.require("from").asString())&&knownType(c.require("to").asString()),"Unknown conversion type");}
    for(const auto& [id,r]:out->rows_) {require(knownType(r.type),"Unknown build type: "+r.type);if(r.upgradesFrom)require(knownType(*r.upgradesFrom),"Unknown upgrade source");if(r.derivedFrom)require(out->rows_.contains(*r.derivedFrom),"Unknown derived build row");knownTech(r.requiredTechnologies);knownTech(r.forbiddenTechnologies);}
    out->fingerprint_=contentDigest(canonicalJson(documents));return out;
}

const UnitDefinition& Catalog::unit(const Id& id) const { return units_.at(id); }
const FacilityDefinition& Catalog::facility(const Id& id) const { return facilities_.at(id); }
const TechnologyDefinition& Catalog::technology(const Id& id) const { return technologies_.at(id); }
const BuildChartRow& Catalog::row(const Id& id) const { return rows_.at(id); }
CatalogStats Catalog::stats(const Id& type,int damage,const CatalogContext& c) const {
    const auto& u=unit(type);auto s=u.states.at(damage);
    for(const auto& rule:u.rules.asArray())if(rule.require("id").asString()=="militia_conditional_movement") {const auto& p=rule.require("parameters");if(flags(c,p.find("requires_flags")))s.movement=p.require("conditional_movement").asInt();}
    for(const auto& tech:c.technologies)for(const auto& m:technology(tech).modifiers.asArray()) {
        const auto types=ids(m.require("unit_types")),classes=ids(m.require("classes"));bool match=types.contains(type);for(const auto& id:classes)match=match||u.classes.contains(id);if(!match||!flags(c,m.find("requires_flags")))continue;
        const int add=m.require("add").asInt();const auto& stat=m.require("stat").asString();
        const auto apply=[&](std::optional<int>& n){if(n)*n+=add;};
        if(stat=="attack")apply(s.attack);else if(stat=="defense")apply(s.defense);else if(stat=="movement")apply(s.movement);else if(stat=="bombardment")apply(s.bombardment);else if(stat=="cargo_capacity")apply(s.cargoCapacity);else if(stat=="carrier_capacity")apply(s.carrierCapacity);else if(stat=="attack_dice")s.attackDice+=add;else if(stat=="defense_dice")s.defenseDice+=add;else throw std::runtime_error("Unknown stat modifier: "+stat);
    }return s;
}
std::vector<CatalogMode> Catalog::modes(const Id& type,const CatalogContext& c,int damage) const {
    const auto current=stats(type,damage,c);
    std::vector<CatalogMode> out;
    for(const auto& mode:unit(type).modes) {
        if(!hasTechnologies(c,mode.requiredTechnologies)||!flags(c,mode.parameters.find("requires_flags")))continue;
        auto resolved=mode;
        if(const auto* stat=mode.parameters.find("threshold_from_state_stat")) {
            require(stat->asString()=="bombardment","Unknown mode state statistic");
            resolved.threshold=current.bombardment;
            resolved.dice=current.bombardmentDice;
        }
        if(mode.id=="interception"&&c.technologies.contains("radar")) {
            if(const auto* bonus=mode.parameters.find("radar_bonus")) {
                require(resolved.threshold.has_value(),"Interception lacks a threshold");
                *resolved.threshold+=bonus->asInt();
            }
        }
        if(mode.id=="maritime_air_patrol"&&c.technologies.contains("long_range_aircraft")) {
            for(const auto& rule:technology("long_range_aircraft").rules.asArray()) {
                if(rule.require("id").asString()!="long_range_aircraft_map")continue;
                const auto& p=rule.require("parameters");
                int bonus=0;
                if(type=="medium_bomber")bonus=p.require("medium_bomber_map_range_bonus").asInt();
                if(type=="seaplane"&&flags(c,p.find("seaplane_requires_flags")))bonus=p.require("seaplane_map_range_bonus").asInt();
                auto parameters=resolved.parameters.asObject();
                parameters["range"]=V(static_cast<double>(parameters.at("range").asInt()+bonus));
                resolved.parameters=V(std::move(parameters));
            }
        }
        out.push_back(std::move(resolved));
    }
    return out;
}
Eligibility Catalog::purchaseEligibility(const Id& id,const CatalogContext& c,int count) const {
    const auto& r=row(id);Eligibility e;const auto fail=[&](const std::string& why){e.reasons.push_back(why);};
    require(c.year>0&&c.month>=1&&c.month<=12,"Invalid catalog context date");require(count>0,"Purchase count must be positive");
    if(r.nation!=c.nation)fail("nation");if(r.powerStatus!=c.powerStatus)fail("power_status");const int now=c.year*100+c.month;if(r.availableFrom&&now<*r.availableFrom)fail("available_from");if(r.availableThrough&&now>*r.availableThrough)fail("available_through");
    for(const auto& tech:r.requiredTechnologies)if(!c.technologies.contains(tech))fail("requires_technology:"+tech);for(const auto& tech:r.forbiddenTechnologies)if(c.technologies.contains(tech))fail("forbids_technology:"+tech);for(const auto& id:r.requiredFlags)if(!flag(c,id))fail("requires_flag:"+id);
    if(r.cap) {const auto key=r.capGroup.value_or(r.id);const auto i=c.purchases.find(key);const int used=i==c.purchases.end()?0:i->second;require(used>=0,"Negative purchase usage");if(count>*r.cap||used>*r.cap-count)fail("per_turn_cap:"+key);}
    e.allowed=e.reasons.empty();return e;
}
Eligibility Catalog::placementEligibility(const Id& id,const CatalogContext& c) const {Eligibility e;for(const auto& p:row(id).placement)if(!flag(c,p))e.reasons.push_back("placement:"+p);e.allowed=e.reasons.empty();return e;}
std::vector<BuildChartRow> Catalog::purchaseOptions(const CatalogContext& c) const {std::vector<BuildChartRow> out;for(const auto& [id,r]:rows_)if(purchaseEligibility(id,c).allowed)out.push_back(r);return out;}
std::vector<PriceOption> Catalog::priceOptions(const Id& id,const CatalogContext& c) const {
    const auto& r=row(id);if(!purchaseEligibility(id,c).allowed)return {};std::vector<PriceOption> out{{"printed",r.purchaseCosts}};
    const bool naval=units_.contains(r.type)&&unit(r.type).classes.contains("naval");if(!c.technologies.contains("improved_construction")||(!naval&&!facilities_.contains(r.type)))return out;
    auto reduced=r.purchaseCosts;for(int& n:reduced)n=std::max(0,n-1);out.push_back({"improved_construction_discount",reduced});
    if(r.purchaseCosts.size()>=2) {auto combined=r.purchaseCosts;combined[0]+=combined[1];combined.erase(combined.begin()+1);out.push_back({"improved_construction_combine",combined});}return out;
}
std::vector<CatalogUpgrade> Catalog::automaticConversions(const Id& type,const CatalogContext& c) const {
    (void)unit(type);std::vector<CatalogUpgrade> out;
    for(const auto& up:unit(type).upgrades)if(up.automatic&&hasTechnologies(c,up.requiredTechnologies)&&flags(c,up.parameters.find("requires_flags")))out.push_back(up);
    for(const auto& tech:c.technologies)for(const auto& v:technology(tech).conversions.asArray())if(v.require("from").asString()==type&&v.require("automatic").asBool()) {CatalogUpgrade up;up.to=v.require("to").asString();up.costIpp=v.require("cost_ipp").asInt();up.automatic=true;up.requiredTechnologies={tech};up.parameters=V::Object{};up.sourceRefs=technology(tech).sourceRefs; if(std::none_of(out.begin(),out.end(),[&](const auto& x){return x.to==up.to;}))out.push_back(std::move(up));}return out;
}
int Catalog::productionCapacity(const Id& type,int damage,const CatalogContext& c) const {
    require(damage>=0,"Negative facility damage");
    int capacity=facility(type).productionCapacity;
    if(c.technologies.contains("improved_factories")) {
        for(const auto& rule:technology("improved_factories").rules.asArray()) {
            if(rule.require("id").asString()!="improved_factories_capacity")continue;
            if(const auto* value=rule.require("parameters").require("production_capacity_by_type").find(type))capacity=value->asInt();
        }
    }
    return type=="major_factory"?std::max(0,capacity-damage):(damage?0:capacity);
}
int Catalog::repairCapacity(const Id& type,int damage,const CatalogContext& c) const {
    require(damage>=0,"Negative facility damage");
    int capacity=facility(type).repairCapacity;
    if(damage)return 0;
    if(c.technologies.contains("improved_factories")) {
        for(const auto& rule:technology("improved_factories").rules.asArray()) {
            if(rule.require("id").asString()!="improved_factories_capacity")continue;
            if(const auto* table=rule.require("parameters").find("repair_capacity_by_type")) {
                if(const auto* value=table->find(type))capacity=value->asInt();
            }
        }
    }
    return capacity;
}
std::vector<std::string> Catalog::unresolvedFields() const {std::vector<std::string> out;for(const auto& [id,u]:units_)if(!u.unresolved.isNull()&&((u.unresolved.isArray()&&!u.unresolved.asArray().empty())||(!u.unresolved.isArray())))out.push_back(id+":"+canonicalJson(u.unresolved));for(const auto& [file,doc]:sourceData_.asObject())if(const auto* b=doc.find("blockers"))for(const auto& x:b->asArray())out.push_back(file+":"+canonicalJson(x));return out;}
void Catalog::requireComplete() const {const auto missing=unresolvedFields();require(missing.empty(),"Catalog has unresolved source fields" );require(!units_.empty()&&!facilities_.empty()&&!technologies_.empty()&&!rows_.empty(),"Incomplete catalog documents");}

namespace {
// Later flag maps override earlier ones and the derived flags override all.
CatalogContext buildContext(const State& state,const Id& owner,const std::optional<Id>& zone,bool copyFlags) {
    require(state.definition!=nullptr,"Catalog context requires definition");const auto& n=state.nations.at(owner);CatalogContext c;c.nation=owner;c.powerStatus=n.powerStatus;const auto [y,m]=state.calendarDate();c.year=y;c.month=m;for(const auto& [id,stage]:n.technologyStages)if(stage==4)c.technologies.insert(id);
    if(copyFlags) for(const auto* list:{&state.flags,&n.gameFlags,&n.turnFlags})for(const auto& [id,v]:*list)c.flags[id]=v!=0;
    else c.flagSources={&n.turnFlags,&n.gameFlags,&state.flags};
    c.flags["owner_is_major_power"]=n.powerStatus=="major";
    if(zone) {const auto& faction=state.definition->factions.at(owner);const bool home=faction.homeCountryKnown&&faction.homeCountry.contains(*zone);c.flags["movement_starts_in_owner_home_country"]=home;c.flags["movement_ends_in_owner_home_country"]=home;}
    if(!state.nations.contains("ussr"))c.disabledFlags.insert("ccp_soviet_rail_production");
    // These source predicates cannot be satisfied by a generic supply flag in
    // the closed theatre. Geography/rail path evaluation belongs to M4/M5.
    if(state.definition->scenarioId=="japan_china_1936_1941")c.disabledFlags.insert("kmt_burma_road");
    for(const auto& [key,value]:n.turnFlags)if(key.rfind("purchased:",0)==0)c.purchases[key.substr(10)]=value;
    return c;
}
}
CatalogContext catalogContext(const State& state,const Id& owner,const std::optional<Id>& zone) {
    return buildContext(state,owner,zone,true);
}
CatalogStats catalogStats(const State& state,const Id& type,int damage,const Id& owner,const std::optional<Id>& zone) {
    return state.definition->catalog->stats(type,damage,buildContext(state,owner,zone,false));
}
void initializeCatalogState(State& state) {
    require(state.definition&&state.definition->catalog,"Campaign has no catalog");
    for(auto& [id,f]:state.facilities)if(f.type=="airfield")f.type="airbase";
    for(auto& [id,u]:state.units) {const auto s=state.definition->catalog->stats(u.type,u.damage,catalogContext(state,u.owner,u.zone));u.movementAllowance=s.movement;u.movementRemaining=s.movement;}
}
int completedAssetValue(const Definition& d,const Id& type) {
    require(bool(d.catalog),"Asset valuation requires catalog");if(d.catalog->facilities().contains(type))return d.catalog->facility(type).assetValue;const auto value=d.catalog->unit(type).assetValue;if(value)return *value;
    if(const auto* contract=d.rules.find("scenario_contract"))if(const auto* list=contract->find("setup_only_unit_values"))for(const auto& row:list->asArray())if(row.require("type").asString()==type)return row.require("valuation_ipp_per_piece").asInt();
    throw std::runtime_error("No asset valuation for unpriced type: "+type);
}
} // namespace game::campaign
