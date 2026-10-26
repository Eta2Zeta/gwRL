#include "game/movement_context.hpp"
#include "game/catalog.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <functional>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>

namespace game::campaign {
namespace {
using V=json::Value;
bool truth(const V& value,const Id& key){const auto* p=value.find(key);return p&&p->isBool()&&p->asBool();}
std::set<Id> terrain(const V* value){
    std::set<Id> result;if(!value||value->isNull())return result;
    if(value->isString()){if(value->asString()!="normal")result.insert(value->asString());}
    else if(value->isArray())for(const auto& child:value->asArray())if(child.asString()!="normal")result.insert(child.asString());
    return result;
}
std::int64_t index(const std::vector<Id>& ids,const Id& value){
    const auto found=std::lower_bound(ids.begin(),ids.end(),value);
    return found!=ids.end()&&*found==value?std::distance(ids.begin(),found):-1;
}
std::size_t product(std::size_t a,std::size_t b,std::size_t c=1){
    if((b&&a>std::numeric_limits<std::size_t>::max()/b)||(c&&a*b>std::numeric_limits<std::size_t>::max()/c))
        throw std::length_error("Movement metadata allocation overflow; no entries truncated");
    return a*b*c;
}
struct Errors {
    MovementContext& context;
    std::int64_t message(const std::string& value){
        auto found=std::find(context.exceptionMessages.begin(),context.exceptionMessages.end(),value);
        if(found==context.exceptionMessages.end()){context.exceptionMessages.push_back(value);return context.exceptionMessages.size()-1;}
        return std::distance(context.exceptionMessages.begin(),found);
    }
    template<class F> void evaluate(std::int64_t& code,std::int64_t& text,F&& fn){
        try{fn();}catch(const std::out_of_range& e){code=1;text=message(e.what());}
        catch(const std::exception& e){code=2;text=message(e.what());}
    }
};
}

MovementContext::MovementContext(std::shared_ptr<const Definition> d):definition(std::move(d)) {
    if(!definition||definition->fingerprint.empty()||!definition->catalog)
        throw std::invalid_argument("Movement context requires a frozen catalog-backed definition");
    const auto& geography=definition->geography.require("nodes").asObject();
    for(const auto& [id,_]:geography)zones.push_back(id);
    for(const auto& [id,_]:definition->factions)nations.push_back(id);
    for(const auto& [id,_]:definition->catalog->units())unitTypes.push_back(id);
    players.assign(definition->players.begin(),definition->players.end());
    if(const auto* raw=definition->geography.find("facilities"))for(const auto& [id,_]:raw->asObject())facilityIds.push_back(id);
    const auto Z=zones.size(),N=nations.size(),U=unitTypes.size(),F=facilityIds.size();
    nodes.assign(product(Z,7),0);edges.assign(product(Z,Z,20),0);
    riverBanks.assign(product(Z,Z,Z),0);crossingSeas.assign(product(Z,Z,Z),0);
    bankUnknown.assign(product(Z,Z,3),0);crossingSeasMissing.assign(product(Z,Z,3),0);
    home.assign(product(N,Z),0);classes.assign(product(U,8),0);fortBorders.assign(product(F,Z),0);fortErrors.assign(product(F,2),0);
    std::set<Id> labels,regionNames;std::vector<std::set<Id>> nt(Z),bt(Z*Z);
    Errors errors{*this};State probe;probe.definition=definition;
    for(std::size_t z=0;z<Z;++z)if(geography.at(zones[z]).require("type").asString()=="land")probe.territories.emplace(zones[z],TerritoryState{});
    for(std::size_t z=0;z<Z;++z){
        const auto& spec=geography.at(zones[z]);auto* row=nodes.data()+z*7;row[0]=probe.territories.contains(zones[z]);row[1]=truth(spec,"is_city");
        errors.evaluate(row[5],row[6],[&]{nt[z]=terrain(spec.find("terrain"));labels.insert(nt[z].begin(),nt[z].end());});
        errors.evaluate(row[3],row[4],[&]{regionNames.insert(railRegion(probe,zones[z]));});
    }
    for(std::size_t a=0;a<Z;++a)for(std::size_t b=0;b<Z;++b){
        const auto pair=a*Z+b;auto* out=edges.data()+pair*20;const V* edge=nullptr;
        for(const auto& candidate:geography.at(zones[a]).require("neighbors").asArray())
            if(candidate.require("neighbor_id").asString()==zones[b]){edge=&candidate;break;}
        out[0]=edge!=nullptr;
        errors.evaluate(out[18],out[19],[&]{out[1]=passableLandBorder(probe,zones[a],zones[b]);});
        if(edge){
            out[2]=truth(*edge,"railway_connection");out[3]=truth(*edge,"has_river");out[4]=truth(*edge,"narrow_crossing");
            errors.evaluate(out[6],out[7],[&]{out[5]=edge->require("unit_capacity").asInt();});
            errors.evaluate(out[10],out[11],[&]{const auto approach=borderApproach(probe,zones[a],zones[b]);
                bt[pair]=approach.borderTerrain;labels.insert(bt[pair].begin(),bt[pair].end());out[8]=approach.river;out[9]=approach.riverKnown;});
            auto* bank=bankUnknown.data()+pair*3;
            errors.evaluate(bank[1],bank[2],[&]{if(const auto* list=edge->find("river_banks"))for(const auto& value:list->asArray()){
                const auto z=index(zones,value.asString());if(z<0)bank[0]=1;else riverBanks[pair*Z+z]=1;}});
            auto* seas=crossingSeasMissing.data()+pair*3;seas[0]=edge->find("narrow_crossing_sea_zones")==nullptr;
            errors.evaluate(seas[1],seas[2],[&]{if(const auto* list=edge->find("narrow_crossing_sea_zones"))for(const auto& value:list->asArray()){
                const auto z=index(zones,value.asString());if(z>=0)crossingSeas[pair*Z+z]=1;}});
        }else {out[10]=2;out[11]=errors.message("Nonadjacent approach edge");}
        errors.evaluate(out[13],out[14],[&]{out[12]=railGaugeChange(probe,zones[a],zones[b]);});
        probe.rails.emplace("__device_route_gauge_probe",RailState{"__device_route_gauge_probe",zones[a],zones[b],{}});
        errors.evaluate(out[16],out[17],[&]{out[15]=railGaugeChange(probe,zones[a],zones[b]);});
        probe.rails.clear();
    }
    terrains.assign(labels.begin(),labels.end());regions.assign(regionNames.begin(),regionNames.end());
    const auto K=terrains.size(),R=regions.size();nodeTerrain.assign(product(Z,K),0);borderTerrain.assign(product(Z,Z,K),0);
    for(std::size_t z=0;z<Z;++z){for(const auto& label:nt[z])nodeTerrain[z*K+index(terrains,label)]=1;
        if(!nodes[z*7+3])nodes[z*7+2]=index(regions,railRegion(probe,zones[z]));else nodes[z*7+2]=-1;}
    for(std::size_t pair=0;pair<Z*Z;++pair)for(const auto& label:bt[pair])borderTerrain[pair*K+index(terrains,label)]=1;
    capacities.assign(product(R,3),0);
    for(std::size_t r=0;r<R;++r)errors.evaluate(capacities[r*3+1],capacities[r*3+2],[&]{capacities[r*3]=regionalRailCapacity(regions[r]);});
    for(std::size_t n=0;n<N;++n)for(std::size_t z=0;z<Z;++z)home[n*Z+z]=definition->factions.at(nations[n]).homeCountry.contains(zones[z]);
    const std::vector<Id> names{"land","naval","aircraft","rocket","infantry_class","surface_warship","submarine","fighter"};
    for(std::size_t u=0;u<U;++u)for(std::size_t c=0;c<names.size();++c)classes[u*8+c]=definition->catalog->unit(unitTypes[u]).classes.contains(names[c]);
    if(const auto* metadata=definition->geography.find("facilities"))for(std::size_t f=0;f<F;++f){
        const auto& spec=metadata->require(facilityIds[f]);errors.evaluate(fortErrors[f*2],fortErrors[f*2+1],[&]{
            if(const auto* borders=spec.find("land_accesses"))for(const auto& value:borders->asArray()){
                const auto z=index(zones,value.asString());if(z>=0)fortBorders[f*Z+z]=1;}});
    }
    counterOffsets={0};std::map<Id,std::int64_t> counterIds;
    const auto addCounter=[&](const Id& key){auto found=counterIds.find(key);if(found!=counterIds.end())return found->second;
        const auto id=static_cast<std::int64_t>(counterOffsets.size()-1);counterIds.emplace(key,id);
        counterBytes.insert(counterBytes.end(),key.begin(),key.end());counterOffsets.push_back(counterBytes.size());return id;};
    crossingCounter.assign(Z*Z,-1);crossingCounterErrors.assign(product(Z,Z,2),0);
    for(std::size_t a=0;a<Z;++a)for(std::size_t b=0;b<Z;++b)for(const auto& e:geography.at(zones[a]).require("neighbors").asArray())
        if(e.require("neighbor_id").asString()==zones[b]){const auto* id=e.find("narrow_crossing_id");
            const auto pair=a*Z+b;errors.evaluate(crossingCounterErrors[pair*2],crossingCounterErrors[pair*2+1],[&]{
                crossingCounter[pair]=addCounter("crossing_used:"+(id?id->asString():std::min(zones[a],zones[b])+"__"+std::max(zones[a],zones[b])));});break;}
    railCounters.assign(product(players.size(),R),-1);
    for(std::size_t p=0;p<players.size();++p)for(std::size_t r=0;r<R;++r)railCounters[p*R+r]=addCounter("rail_used:"+players[p]+":"+regions[r]);
}
} // namespace game::campaign
