#include "game/catalog_stats_context.hpp"
#include <algorithm>
#include <array>
#include <limits>
#include <map>
#include <stdexcept>

namespace game::campaign {
namespace {
using V=json::Value;
using Instruction=std::array<std::int64_t,12>;
std::int64_t size(std::size_t count) {
    if(count>static_cast<std::size_t>(std::numeric_limits<std::int64_t>::max()))
        throw std::length_error("Catalog-stat table is not representable; no truncation");
    return static_cast<std::int64_t>(count);
}
struct Builder {
    CatalogStatsContext& out;
    std::map<std::string,std::int64_t> tokens;
    std::int64_t token(const std::string& text) {
        const auto [where,inserted]=tokens.emplace(text,size(out.strings.size()));
        if(inserted)out.strings.push_back(text);
        return where->second;
    }
    std::int64_t message(const std::string& text) {
        const auto found=std::find(out.messages.begin(),out.messages.end(),text);
        if(found!=out.messages.end())return size(found-out.messages.begin());
        out.messages.push_back(text);return size(out.messages.size()-1);
    }
    template<class F> bool attempt(std::int64_t& error,std::int64_t& why,F function) {
        try{function();return true;}
        catch(const std::out_of_range& e){error=1;why=message(e.what());}
        catch(const std::exception& e){error=2;why=message(e.what());}
        return false;
    }
    static std::set<Id> ids(const V& list) {
        std::set<Id> result;
        for(const auto& item:list.asArray())if(!result.insert(item.asString()).second)
            throw std::runtime_error("Duplicate catalog list entry");
        return result;
    }
    void requiredFlags(const V& object,Instruction& row) {
        row[2]=size(out.flags.size()/4);
        attempt(row[4],row[5],[&] {
            const auto* list=object.find("requires_flags");if(!list)return;
            for(const auto& item:list->asArray()) {
                std::array<std::int64_t,4> flag{-1,0,0,0};
                attempt(flag[2],flag[3],[&] {
                    const auto& text=item.asString();flag[0]=token(text);
                    if(text=="owner_is_major_power")flag[1]=1;
                    else if(text=="movement_starts_in_owner_home_country"||text=="movement_ends_in_owner_home_country")flag[1]=2;
                    else if(text=="ccp_soviet_rail_production")flag[1]=3;
                    else if(text=="kmt_burma_road")flag[1]=4;
                });
                out.flags.insert(out.flags.end(),flag.begin(),flag.end());++row[3];
            }
        });
    }
    void conditional(const V& rule) {
        Instruction row{};bool relevant=false;const V* parameters=nullptr;
        if(attempt(row[0],row[1],[&] {
            relevant=rule.require("id").asString()=="militia_conditional_movement";
            if(relevant)parameters=&rule.require("parameters");
        })&&!relevant)return;
        row[9]=4;
        if(!row[0]) {
            requiredFlags(*parameters,row);
            attempt(row[7],row[8],[&]{row[6]=parameters->require("conditional_movement").asInt();});
        }
        out.conditionals.insert(out.conditionals.end(),row.begin(),row.end());
    }
    void modifier(const V& value,const Catalog& catalog) {
        Instruction row{};std::set<Id> types,classes;
        attempt(row[0],row[1],[&] {
            types=ids(value.require("unit_types"));classes=ids(value.require("classes"));
        });
        for(const auto& [id,unit]:catalog.units()) {
            bool match=types.contains(id);
            for(const auto& name:classes)match|=unit.classes.contains(name);
            out.matches.push_back(match);
        }
        if(!row[0]) {
            requiredFlags(value,row);
            attempt(row[7],row[8],[&]{row[6]=value.require("add").asInt();});
            attempt(row[10],row[11],[&] {
                const auto& stat=value.require("stat").asString();
                const std::map<std::string,int> indices{{"attack",0},{"defense",1},{"attack_dice",2},{"defense_dice",3},
                    {"movement",4},{"bombardment",5},{"cargo_capacity",7},{"carrier_capacity",8}};
                const auto found=indices.find(stat);
                if(found==indices.end())throw std::runtime_error("Unknown stat modifier: "+stat);
                row[9]=found->second;
            });
        }
        out.modifiers.insert(out.modifiers.end(),row.begin(),row.end());
    }
};
}
void appendCatalogStats(std::vector<std::int64_t>& values,const CatalogStats& stats) {
    // Compile-time exhaustive member binding: additions cannot silently vanish.
    const auto& [a,b,c,d,e,f,g,h,i]=stats;
    for(const auto& value:std::array<std::optional<int>,9>{a,b,c,d,e,f,g,h,i}) {
        values.push_back(value.has_value());values.push_back(value.value_or(0));
    }
}
CatalogStatsContext::CatalogStatsContext(const Engine& engine):definition(engine.state().definition) {
    if(!definition||!definition->catalog)throw std::invalid_argument("Catalog stats require a catalog definition");
    wireContextFingerprint=DeviceStateContext(engine).wireContextFingerprint;
    const auto& catalog=*definition->catalog;catalogFingerprint=catalog.fingerprint();
    closedTheatre=definition->scenarioId=="japan_china_1936_1941";
    Builder builder{*this,{}};
    try{(void)std::map<Id,int>{}.at("");}catch(const std::out_of_range& e){lookupMessage=builder.message(e.what());}
    for(const auto& [id,unit]:catalog.units()) {
        unitTypes.push_back(id);unitTokens.push_back(builder.token(id));
        const auto stateOffset=size(states.size()/19),conditionOffset=size(conditionals.size()/12);
        for(const auto& [damage,stats]:unit.states){states.push_back(damage);appendCatalogStats(states,stats);}
        std::int64_t error=0,why=0;
        if(!builder.attempt(error,why,[&]{for(const auto& rule:unit.rules.asArray())builder.conditional(rule);})) {
            Instruction row{};row[0]=error;row[1]=why;conditionals.insert(conditionals.end(),row.begin(),row.end());
        }
        units.insert(units.end(),{stateOffset,size(unit.states.size()),conditionOffset,size(conditionals.size()/12)-conditionOffset});
    }
    for(const auto& [id,tech]:catalog.technologies()) {
        technologies.push_back(id);technologyTokens.push_back(builder.token(id));
        const auto start=size(modifiers.size()/12);std::int64_t error=0,why=0;
        builder.attempt(error,why,[&]{for(const auto& modifier:tech.modifiers.asArray())builder.modifier(modifier,catalog);});
        technology.insert(technology.end(),{start,size(modifiers.size()/12)-start,error,why});
    }
    for(const auto& [id,faction]:definition->factions) {
        factions.push_back(id);factionTokens.push_back(builder.token(id));const auto start=size(homeTokens.size());
        for(const auto& zone:faction.homeCountry)homeTokens.push_back(builder.token(zone));
        home.insert(home.end(),{faction.homeCountryKnown,start,size(homeTokens.size())-start});
    }
}
} // namespace game::campaign
