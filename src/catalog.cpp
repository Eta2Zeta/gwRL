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
    if(!c.flagSources.empty())if(const auto key=findMarkKey(id))
        for(const auto* source:c.flagSources) if(const auto i=source->find(*key); i!=source->end()) return i->second!=0;
    return false;
}
bool flags(const CatalogContext& c,const V* list) { if(list) for(const auto& x:list->asArray()) if(!flag(c,x.asString())) return false; return true; }
// The names of a list as a set of technology numbers. Throws "Unknown
// technology: <name>" for a name the catalog lacks.
NumberSet<TechnologyId> technologySet(const NameTable<TechnologyKind>& technologies,const V& v) {
    NumberSet<TechnologyId> out;for(const auto& x:v.asArray())require(out.insert(technologies.number(x.asString())).second,"Duplicate catalog list entry");return out;
}
std::vector<CatalogUpgrade> upgrades(const Catalog& catalog,const V& list) {
    std::vector<CatalogUpgrade> out;
    for(const auto& v:list.asArray()) {
        CatalogUpgrade u; u.to=catalog.buildType(v.require("to").asString());u.costIpp=v.require("cost_ipp").asInt();u.automatic=v.require("automatic").asBool();u.requiredTechnologies=technologySet(catalog.technologies(),v.require("requires_technology"));u.parameters=v.require("parameters");u.sourceRefs=v.require("source_refs");require(u.costIpp>=0,"Negative upgrade price");out.push_back(std::move(u));
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
    // First the tables: every unit type, unit class, facility type and
    // technology, each numbered in name order (names.hpp), so that the
    // definitions below can hold the names they cite as numbers.
    std::set<Id> unitNames,classNames,facilityNames,technologyNames;
    for(const auto& [file,doc]:documents.asObject()) {
        require(doc.require("schema_version").asInt()==1,"Unsupported catalog schema");
        if(const auto* list=doc.find("units"))for(const auto& v:list->asArray()) {
            require(unitNames.insert(v.require("id").asString()).second,"Duplicate unit type");
            for(const auto& c:v.require("classes").asArray())classNames.insert(c.asString());
        }
        if(const auto* list=doc.find("facilities"))for(const auto& v:list->asArray())require(facilityNames.insert(v.require("id").asString()).second,"Duplicate facility");
        if(const auto* list=doc.find("technologies"))for(const auto& v:list->asArray())require(technologyNames.insert(v.require("id").asString()).second,"Duplicate technology");
    }
    for(const auto& id:unitNames)require(!facilityNames.contains(id),"Ambiguous catalog type");
    out->unitTypes_=NameTable<UnitTypeKind>(std::vector<std::string>(unitNames.begin(),unitNames.end()));
    out->unitClasses_=NameTable<UnitClassKind>(std::vector<std::string>(classNames.begin(),classNames.end()));
    out->facilityTypes_=NameTable<FacilityTypeKind>(std::vector<std::string>(facilityNames.begin(),facilityNames.end()));
    out->technologies_=NameTable<TechnologyKind>(std::vector<std::string>(technologyNames.begin(),technologyNames.end()));
    // The names the rules use must be in the catalog: number() throws for one that is not.
#define GWRL_FILL(name) out->knownUnitTypes_.name=out->unitTypes_.number(#name);
    GWRL_KNOWN_UNIT_TYPES(GWRL_FILL)
#undef GWRL_FILL
#define GWRL_FILL(name) out->knownUnitClasses_.name=out->unitClasses_.number(#name);
    GWRL_UNIT_CLASSES(GWRL_FILL)
#undef GWRL_FILL
#define GWRL_FILL(name) out->knownFacilityTypes_.name=out->facilityTypes_.number(#name);
    GWRL_KNOWN_FACILITY_TYPES(GWRL_FILL)
#undef GWRL_FILL
#define GWRL_FILL(name) out->knownTechnologies_.name=out->technologies_.number(#name);
    GWRL_KNOWN_TECHNOLOGIES(GWRL_FILL)
#undef GWRL_FILL
    // Then the definitions, kept in number order.
    out->units_.resize(out->unitTypes_.size());out->facilities_.resize(out->facilityTypes_.size());out->technologyDefinitions_.resize(out->technologies_.size());
    const auto technologyList=[&](const V& v){return technologySet(out->technologies_,v);};
    for(const auto& [file,doc]:documents.asObject()) {
        std::set<Id> sources;for(const auto& source:doc.require("sources").asArray())require(sources.insert(source.require("id").asString()).second,"Duplicate catalog source");references(doc,sources);
        if(const auto* list=doc.find("units")) for(const auto& v:list->asArray()) {
            UnitDefinition u;u.id=v.require("id").asString();u.number=out->unitTypes_.number(u.id);u.name=v.require("name").asString();const auto unitClassNames=ids(v.require("classes"));u.purchaseCosts=integers(v.require("purchase_costs"));u.assetValue=optionalInt(v.require("asset_value"));u.maxHits=v.require("max_hits").asInt();u.targetClasses=ids(v.require("target_classes"));u.abilities=ids(v.require("abilities"));u.upgrades=upgrades(*out,v.require("upgrades"));u.rules=v.require("rules");u.repair=v.require("repair");u.sourceRefs=v.require("source_refs"); if(const auto* p=v.find("unresolved_fields"))u.unresolved=*p;
            require(!u.name.empty()&&!unitClassNames.empty()&&u.maxHits>0,"Invalid unit definition");prices(u.purchaseCosts);
            for(const auto& name:unitClassNames)u.classes.insert(out->unitClasses_.number(name));
            for(const auto& s:v.require("states").asArray()) {
                CatalogStats x;x.attack=optionalInt(s.require("attack"));x.defense=optionalInt(s.require("defense"));x.attackDice=s.require("attack_dice").asInt();x.defenseDice=s.require("defense_dice").asInt();x.movement=optionalInt(s.require("movement"));x.bombardment=optionalInt(s.require("bombardment"));x.bombardmentDice=s.require("bombardment_dice").asInt();x.cargoCapacity=optionalInt(s.require("cargo_capacity"));x.carrierCapacity=optionalInt(s.require("carrier_capacity"));
                const int damage=s.require("damage").asInt(); require(damage>=0&&damage<u.maxHits,"Invalid surviving damage state");for(auto n:{x.attack,x.defense,x.bombardment})require(!n||(*n>=0&&*n<=12),"Invalid D12 combat threshold");for(auto n:{x.movement,x.cargoCapacity,x.carrierCapacity})require(!n||*n>=0,"Negative unit capacity/movement");require(x.attackDice>=0&&x.defenseDice>=0&&x.bombardmentDice>=0,"Negative combat dice");require(u.states.emplace(damage,x).second,"Duplicate damage state");
            }
            require(u.states.size()==static_cast<std::size_t>(u.maxHits),"Missing surviving unit state: "+u.id);
            std::set<Id> modes;
            for(const auto& m:v.require("modes").asArray()) {
                CatalogMode x;x.id=m.require("id").asString();x.threshold=optionalInt(m.require("threshold"));x.dieSides=m.require("die_sides").asInt();x.dice=m.require("dice").asInt();x.requiredTechnologies=technologyList(m.require("requires_technology"));x.parameters=m.require("parameters");x.sourceRefs=m.require("source_refs");require(modes.insert(x.id).second&&x.dice>=0&&(x.dice==0||x.dieSides>=2),"Invalid/duplicate unit mode");u.modes.push_back(std::move(x));
            }
            const auto at=u.number.index();out->units_[at]=std::move(u);
        }
        if(const auto* list=doc.find("facilities"))for(const auto& v:list->asArray()) {
            FacilityDefinition f;f.id=v.require("id").asString();f.number=out->facilityTypes_.number(f.id);f.name=v.require("name").asString();f.purchaseCosts=integers(v.require("purchase_costs"));f.assetValue=v.require("asset_value").asInt();f.maxDamage=optionalInt(v.require("max_damage"));f.repairCost=optionalInt(v.require("repair_cost_per_damage"));f.productionCapacity=v.require("production_capacity").asInt();f.repairCapacity=v.require("repair_capacity").asInt();f.aaThreshold=optionalInt(v.require("aaa").require("threshold"));f.aaDice=v.require("aaa").require("dice").asInt();f.abilities=ids(v.require("abilities"));f.upgrades=upgrades(*out,v.require("upgrades"));f.rules=v.require("rules");f.sourceRefs=v.require("source_refs");prices(f.purchaseCosts);require(!f.name.empty()&&f.assetValue>=0&&f.productionCapacity>=0&&f.repairCapacity>=0,"Invalid facility");
            const auto at=f.number.index();out->facilities_[at]=std::move(f);
        }
        if(const auto* list=doc.find("technologies"))for(const auto& v:list->asArray()) {
            TechnologyDefinition t;t.id=v.require("id").asString();t.number=out->technologies_.number(t.id);t.name=v.require("name").asString();t.thresholds=integers(v.require("thresholds"));t.stageThreeFrom=date(v.require("stage_iii_from").asString());for(const auto& type:v.require("unlocks").asArray())t.unlocks.push_back(out->buildType(type.asString()));t.abilities=ids(v.require("abilities"));t.modifiers=v.require("modifiers");t.conversions=v.require("conversions");t.rules=v.require("rules");t.sourceRefs=v.require("source_refs");require(t.thresholds.size()==4,"Technology must have four stages");for(int n:t.thresholds)require(n>=1&&n<=12,"Invalid research threshold");
            for(const auto& c:t.conversions.asArray()){out->buildType(c.require("from").asString());out->buildType(c.require("to").asString());}
            const auto at=t.number.index();out->technologyDefinitions_[at]=std::move(t);
        }
        if(const auto* list=doc.find("rows"))for(const auto& v:list->asArray()) {
            BuildChartRow r;r.id=v.require("id").asString();r.nation=v.require("nation").asString();r.powerStatus=v.require("power_status").asString();r.type=out->buildType(v.require("type").asString());r.kind=v.require("kind").asString();r.purchaseCosts=integers(v.require("purchase_costs"));r.availableFrom=optionalDate(v.require("available_from"));r.availableThrough=optionalDate(v.require("available_through"));r.requiredTechnologies=technologyList(v.require("requires_technology"));r.forbiddenTechnologies=technologyList(v.require("forbids_technology"));r.cap=optionalInt(v.require("cap_per_turn"));r.capGroup=optionalId(v.require("cap_group"));r.requiredFlags=ids(v.require("requires_flags"));r.placement=ids(v.require("placement"));if(const auto from=optionalId(v.require("upgrades_from")))r.upgradesFrom=out->buildType(*from);if(const auto* d=v.find("derived_from"))r.derivedFrom=optionalId(*d);r.sourceRefs=v.require("source_refs");r.notes=v.require("notes").asString();prices(r.purchaseCosts);require(!r.id.empty()&&!r.purchaseCosts.empty()&&(r.kind=="purchase"||r.kind=="upgrade")&&(!r.cap||*r.cap>0),"Invalid build-chart row");require(out->rows_.emplace(r.id,std::move(r)).second,"Duplicate build-chart row");
        }
    }
    for(const auto& [id,r]:out->rows_)if(r.derivedFrom)require(out->rows_.contains(*r.derivedFrom),"Unknown derived build row");
    // Improved Factories' capacities, read once from its rule.
    for(auto& f:out->facilities_){f.improvedProductionCapacity=f.productionCapacity;f.improvedRepairCapacity=f.repairCapacity;}
    for(const auto& rule:out->technology(out->knownTechnologies_.improved_factories).rules.asArray()) {
        if(rule.require("id").asString()!="improved_factories_capacity")continue;
        const auto& parameters=rule.require("parameters");
        for(const auto& [type,value]:parameters.require("production_capacity_by_type").asObject())out->facilities_[out->facilityTypes_.number(type).index()].improvedProductionCapacity=value.asInt();
        if(const auto* table=parameters.find("repair_capacity_by_type"))
            for(const auto& [type,value]:table->asObject())out->facilities_[out->facilityTypes_.number(type).index()].improvedRepairCapacity=value.asInt();
    }
    out->fingerprint_=contentDigest(canonicalJson(documents));return out;
}

const UnitDefinition& Catalog::unit(UnitTypeId type) const {
    if(!type.valid()||type.index()>=units_.size())throw std::runtime_error("A unit type number names no unit type");
    return units_[type.index()];
}
const UnitDefinition& Catalog::unit(const Id& type) const { return units_[unitTypes_.number(type).index()]; }
const FacilityDefinition& Catalog::facility(FacilityTypeId type) const {
    if(!type.valid()||type.index()>=facilities_.size())throw std::runtime_error("A facility type number names no facility type");
    return facilities_[type.index()];
}
const FacilityDefinition& Catalog::facility(const Id& type) const { return facilities_[facilityTypes_.number(type).index()]; }
const TechnologyDefinition& Catalog::technology(TechnologyId technology) const {
    if(!technology.valid()||technology.index()>=technologyDefinitions_.size())throw std::runtime_error("A technology number names no technology");
    return technologyDefinitions_[technology.index()];
}
const TechnologyDefinition& Catalog::technology(const Id& technology) const { return technologyDefinitions_[technologies_.number(technology).index()]; }
std::optional<BuildType> Catalog::findBuildType(std::string_view name) const {
    if(const auto unit=unitTypes_.find(name))return BuildType(*unit);
    if(const auto facility=facilityTypes_.find(name))return BuildType(*facility);
    return std::nullopt;
}
BuildType Catalog::buildType(std::string_view name) const {
    if(const auto type=findBuildType(name))return *type;
    throw std::runtime_error("Unknown build type: "+std::string(name));
}
const std::string& Catalog::buildTypeName(BuildType type) const {
    if(type.isUnit())return unitTypes_.name(type.unit());
    if(type.isFacility())return facilityTypes_.name(type.facility());
    throw std::runtime_error("A build type names nothing");
}
const BuildChartRow& Catalog::row(const Id& id) const { return rows_.at(id); }
CatalogStats Catalog::stats(UnitTypeId type,int damage,const CatalogContext& c) const {
    const auto& u=unit(type);auto s=u.states.at(damage);
    for(const auto& rule:u.rules.asArray())if(rule.require("id").asString()=="militia_conditional_movement") {const auto& p=rule.require("parameters");if(flags(c,p.find("requires_flags")))s.movement=p.require("conditional_movement").asInt();}
    for(const auto tech:c.technologies)for(const auto& m:technology(tech).modifiers.asArray()) {
        const auto types=ids(m.require("unit_types")),classes=ids(m.require("classes"));bool match=types.contains(u.id);for(const auto& id:classes)match=match||u.classes.contains(unitClasses_.find(id));if(!match||!flags(c,m.find("requires_flags")))continue;
        const int add=m.require("add").asInt();const auto& stat=m.require("stat").asString();
        const auto apply=[&](std::optional<int>& n){if(n)*n+=add;};
        if(stat=="attack")apply(s.attack);else if(stat=="defense")apply(s.defense);else if(stat=="movement")apply(s.movement);else if(stat=="bombardment")apply(s.bombardment);else if(stat=="cargo_capacity")apply(s.cargoCapacity);else if(stat=="carrier_capacity")apply(s.carrierCapacity);else if(stat=="attack_dice")s.attackDice+=add;else if(stat=="defense_dice")s.defenseDice+=add;else throw std::runtime_error("Unknown stat modifier: "+stat);
    }return s;
}
std::vector<CatalogMode> Catalog::modes(UnitTypeId type,const CatalogContext& c,int damage) const {
    const auto current=stats(type,damage,c);
    std::vector<CatalogMode> out;
    for(const auto& mode:unit(type).modes) {
        if(!c.technologies.includes(mode.requiredTechnologies)||!flags(c,mode.parameters.find("requires_flags")))continue;
        auto resolved=mode;
        if(const auto* stat=mode.parameters.find("threshold_from_state_stat")) {
            require(stat->asString()=="bombardment","Unknown mode state statistic");
            resolved.threshold=current.bombardment;
            resolved.dice=current.bombardmentDice;
        }
        if(mode.id=="interception"&&c.technologies.contains(knownTechnologies_.radar)) {
            if(const auto* bonus=mode.parameters.find("radar_bonus")) {
                require(resolved.threshold.has_value(),"Interception lacks a threshold");
                *resolved.threshold+=bonus->asInt();
            }
        }
        if(mode.id=="maritime_air_patrol"&&c.technologies.contains(knownTechnologies_.long_range_aircraft)) {
            for(const auto& rule:technology(knownTechnologies_.long_range_aircraft).rules.asArray()) {
                if(rule.require("id").asString()!="long_range_aircraft_map")continue;
                const auto& p=rule.require("parameters");
                int bonus=0;
                if(type==knownUnitTypes_.medium_bomber)bonus=p.require("medium_bomber_map_range_bonus").asInt();
                if(type==knownUnitTypes_.seaplane&&flags(c,p.find("seaplane_requires_flags")))bonus=p.require("seaplane_map_range_bonus").asInt();
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
    for(const auto tech:r.requiredTechnologies)if(!c.technologies.contains(tech))fail("requires_technology:"+technologies_.name(tech));for(const auto tech:r.forbiddenTechnologies)if(c.technologies.contains(tech))fail("forbids_technology:"+technologies_.name(tech));for(const auto& id:r.requiredFlags)if(!flag(c,id))fail("requires_flag:"+id);
    if(r.cap) {const auto key=r.capGroup.value_or(r.id);const auto i=c.purchases.find(key);const int used=i==c.purchases.end()?0:i->second;require(used>=0,"Negative purchase usage");if(count>*r.cap||used>*r.cap-count)fail("per_turn_cap:"+key);}
    e.allowed=e.reasons.empty();return e;
}
Eligibility Catalog::placementEligibility(const Id& id,const CatalogContext& c) const {Eligibility e;for(const auto& p:row(id).placement)if(!flag(c,p))e.reasons.push_back("placement:"+p);e.allowed=e.reasons.empty();return e;}
std::vector<BuildChartRow> Catalog::purchaseOptions(const CatalogContext& c) const {std::vector<BuildChartRow> out;for(const auto& [id,r]:rows_)if(purchaseEligibility(id,c).allowed)out.push_back(r);return out;}
std::vector<PriceOption> Catalog::priceOptions(const Id& id,const CatalogContext& c) const {
    const auto& r=row(id);if(!purchaseEligibility(id,c).allowed)return {};std::vector<PriceOption> out;
    const bool naval=r.type.isUnit()&&unit(r.type.unit()).classes.contains(knownUnitClasses_.naval);if(!c.technologies.contains(knownTechnologies_.improved_construction)||(!naval&&!r.type.isFacility())){out.push_back({"printed",r.purchaseCosts});return out;}
    // The discount replaces the printed price: that would buy the same thing on
    // the same schedule for more (user decision, 5 November 2026).
    auto reduced=r.purchaseCosts;for(int& n:reduced)n=std::max(0,n-1);out.push_back({"improved_construction_discount",reduced});
    if(r.purchaseCosts.size()>=2) {auto combined=r.purchaseCosts;combined[0]+=combined[1];combined.erase(combined.begin()+1);out.push_back({"improved_construction_combine",combined});}return out;
}
std::vector<CatalogUpgrade> Catalog::automaticConversions(UnitTypeId type,const CatalogContext& c) const {
    const auto& u=unit(type);std::vector<CatalogUpgrade> out;
    for(const auto& up:u.upgrades)if(up.automatic&&c.technologies.includes(up.requiredTechnologies)&&flags(c,up.parameters.find("requires_flags")))out.push_back(up);
    for(const auto tech:c.technologies)for(const auto& v:technology(tech).conversions.asArray())if(v.require("from").asString()==u.id&&v.require("automatic").asBool()) {CatalogUpgrade up;up.to=buildType(v.require("to").asString());up.costIpp=v.require("cost_ipp").asInt();up.automatic=true;up.requiredTechnologies={tech};up.parameters=V::Object{};up.sourceRefs=technology(tech).sourceRefs; if(std::none_of(out.begin(),out.end(),[&](const auto& x){return x.to==up.to;}))out.push_back(std::move(up));}return out;
}
int Catalog::productionCapacity(FacilityTypeId type,int damage,const NumberSet<TechnologyId>& technologies) const {
    require(damage>=0,"Negative facility damage");
    const auto& f=facility(type);
    const int capacity=technologies.contains(knownTechnologies_.improved_factories)?f.improvedProductionCapacity:f.productionCapacity;
    return type==knownFacilityTypes_.major_factory?std::max(0,capacity-damage):(damage?0:capacity);
}
int Catalog::repairCapacity(FacilityTypeId type,int damage,const NumberSet<TechnologyId>& technologies) const {
    require(damage>=0,"Negative facility damage");
    const auto& f=facility(type);
    if(damage)return 0;
    return technologies.contains(knownTechnologies_.improved_factories)?f.improvedRepairCapacity:f.repairCapacity;
}
std::vector<std::string> Catalog::unresolvedFields() const {std::vector<std::string> out;for(const auto& u:units_)if(!u.unresolved.isNull()&&((u.unresolved.isArray()&&!u.unresolved.asArray().empty())||(!u.unresolved.isArray())))out.push_back(u.id+":"+canonicalJson(u.unresolved));for(const auto& [file,doc]:sourceData_.asObject())if(const auto* b=doc.find("blockers"))for(const auto& x:b->asArray())out.push_back(file+":"+canonicalJson(x));return out;}
void Catalog::requireComplete() const {const auto missing=unresolvedFields();require(missing.empty(),"Catalog has unresolved source fields" );require(!units_.empty()&&!facilities_.empty()&&!technologies_.empty()&&!rows_.empty(),"Incomplete catalog documents");}

namespace {
// Later flag maps override earlier ones and the derived flags override all.
CatalogContext buildContext(const State& state,NationId owner,std::optional<ZoneId> zone,bool copyFlags) {
    require(state.definition!=nullptr,"Catalog context requires definition");const auto& n=state.nations.at(owner);CatalogContext c;c.nation=nationName(state,owner);c.powerStatus=n.powerStatus;const auto [y,m]=state.calendarDate();c.year=y;c.month=m;c.technologies=completedTechnologies(state,owner);
    if(copyFlags) for(const auto* list:{&state.flags,&n.gameFlags,&n.turnFlags})for(const auto& [key,v]:*list)c.flags[key.name()]=v!=0;
    else c.flagSources={&n.turnFlags,&n.gameFlags,&state.flags};
    c.flags["owner_is_major_power"]=n.powerStatus=="major";
    if(zone) {const auto& faction=nationFaction(state,owner);const bool home=faction.homeCountryKnown&&faction.homeZones.contains(*zone);c.flags["movement_starts_in_owner_home_country"]=home;c.flags["movement_ends_in_owner_home_country"]=home;}
    if(!state.nations.contains(knownNations(state).ussr))c.disabledFlags.insert("ccp_soviet_rail_production");
    // These source predicates cannot be satisfied by a generic supply flag in
    // the closed theatre. Geography/rail path evaluation belongs to the politics and movement modules.
    if(state.definition->scenarioId=="japan_china_1936_1941")c.disabledFlags.insert("kmt_burma_road");
    for(const auto& [key,value]:n.turnFlags)if(key.base()==mark::purchased)c.purchases[std::string(key.argument())]=value;
    return c;
}
}
CatalogContext catalogContext(const State& state,NationId owner,std::optional<ZoneId> zone) {
    return buildContext(state,owner,zone,true);
}
CatalogStats catalogStats(const State& state,UnitTypeId type,int damage,NationId owner,std::optional<ZoneId> zone) {
    return state.definition->catalog->stats(type,damage,buildContext(state,owner,zone,false));
}
void initializeCatalogState(State& state) {
    require(state.definition&&state.definition->catalog,"Campaign has no catalog");
    for(auto& [id,u]:state.units) {const auto s=state.definition->catalog->stats(u.type,u.damage,catalogContext(state,u.owner,u.zone));u.movementAllowance=s.movement;u.movementRemaining=s.movement;}
}
int completedAssetValue(const Definition& d,BuildType type) {
    require(bool(d.catalog),"Asset valuation requires catalog");if(type.isFacility())return d.catalog->facility(type.facility()).assetValue;const auto value=d.catalog->unit(type.unit()).assetValue;if(value)return *value;
    const auto& name=d.catalog->buildTypeName(type);
    if(const auto* contract=d.rules.find("scenario_contract"))if(const auto* list=contract->find("setup_only_unit_values"))for(const auto& row:list->asArray())if(row.require("type").asString()==name)return row.require("valuation_ipp_per_piece").asInt();
    throw std::runtime_error("No asset valuation for unpriced type: "+name);
}
} // namespace game::campaign
