// Direct read-only state capture for the income tensor component.
#include "game/income_batch.hpp"
#include <algorithm>
#include <array>
#include <limits>
#include <stdexcept>

namespace game::campaign {
namespace {
std::size_t product(std::size_t a, std::size_t b, std::size_t c) {
    if (b && a > std::numeric_limits<std::size_t>::max()/b) throw std::length_error("Income batch allocation overflow");
    a *= b;
    if (c && a > std::numeric_limits<std::size_t>::max()/c) throw std::length_error("Income batch allocation overflow");
    return a*c;
}
std::int64_t index(const std::vector<Id>& ids, const Id& id) {
    auto it=std::lower_bound(ids.begin(),ids.end(),id);
    return it!=ids.end()&&*it==id ? std::distance(ids.begin(),it) : -1;
}
int flag(const std::map<Id,int>& flags,const Id& name) {
    const auto it=flags.find(name);return it==flags.end()?0:it->second;
}
void sameDefinition(const IncomeContext& c,const State& s) {
    if(!s.definition || s.definition->fingerprint!=c.definitionFingerprint)
        throw std::invalid_argument("Income batch requires the same frozen definition");
    // Registered geography/faction identities are the validated engine domain.
    // No unknown identity is silently converted into KMT or another nation.
    for(const auto& [id,_]:s.territories)if(index(c.territories,id)<0)
        throw std::out_of_range("Income export: unregistered territory: "+id);
    for(const auto& [id,_]:s.nations)if(index(c.nations,id)<0)
        throw std::out_of_range("Income export: unregistered nation: "+id);
}
std::shared_ptr<const IncomeContext> checkedContext(std::shared_ptr<const IncomeContext> c) {
    if(!c)throw std::invalid_argument("Income context is absent");
    return c;
}
}

IncomeContext::IncomeContext(const Definition& d):definitionFingerprint(d.fingerprint),
    intMinimum(std::numeric_limits<int>::min()),intMaximum(std::numeric_limits<int>::max()) {
    if(d.fingerprint.empty())throw std::invalid_argument("Income context requires a frozen definition");
    static const std::array<Id,6> bonus{"land_china_beiping","land_china_hopeh","land_china_shantung",
        "land_china_nanking","land_china_hunan","land_kwangtung"};
    // Include all geography nodes. Presence remains dynamic; absent sea/land
    // territories must not accidentally become an existing capital/holding.
    for(const auto& [id,node]:d.geography.require("nodes").asObject()) {
        territories.push_back(id);
        int base=0;bool valid=false;
        // Preserve lazy native errors: an invalid IPP field is an error only
        // when the original evaluator would actually read that owned territory.
        try {base=node.require("ipp_value").asInt();valid=true;}catch(const std::exception&){}
        territoryStatic.insert(territoryStatic.end(),{base,valid,
            std::find(bonus.begin(),bonus.end(),id)!=bonus.end()});
    }
    for(const auto& [id,_]:d.factions) {
        nations.push_back(id);
        nationStatic.insert(nationStatic.end(),{id=="japan"||id=="kmt"||id=="ccp",id=="japan"});
    }
}

IncomeBatch::IncomeBatch(std::shared_ptr<const IncomeContext> c,std::size_t b):context(checkedContext(std::move(c))),rows(b),
    territoryState(product(b,context->territories.size(),4),0),nationState(product(b,context->nations.size(),6),0) {}

void IncomeBatch::capture(std::size_t row,const State& s) {
    if(row>=rows)throw std::out_of_range("Income row index");
    sameDefinition(*context,s);
    const auto T=context->territories.size(),N=context->nations.size();
    std::fill_n(territoryState.data()+row*T*4,T*4,0);
    std::fill_n(nationState.data()+row*N*6,N*6,0);
    for(std::size_t t=0;t<T;++t) {
        auto* out=territoryState.data()+(row*T+t)*4;out[1]=-1;
        const auto found=s.territories.find(context->territories[t]);
        if(found==s.territories.end())continue;
        const auto& value=found->second;
        out[0]=1;out[1]=value.possessor?index(context->nations,*value.possessor):-1;
        out[2]=flag(value.flags,"city_ipp_lost");out[3]=flag(value.flags,"city_damage");
    }
    for(std::size_t n=0;n<N;++n) {
        auto* out=nationState.data()+(row*N+n)*6;out[5]=-1;
        const auto& id=context->nations[n];const auto found=s.nations.find(id);
        if(found==s.nations.end())continue;
        const auto& value=found->second;
        out[0]=1;out[1]=value.treasury.has_value();out[2]=value.powerStatus=="major";
        out[3]=s.politics.surrendered.contains(id);
        const auto cap=s.politics.capitals.find(id);
        if(cap!=s.politics.capitals.end()){out[4]=1;out[5]=index(context->territories,cap->second);}
    }
}

IncomeOracleBatch::IncomeOracleBatch(std::shared_ptr<const IncomeContext> c,std::size_t b):context(checkedContext(std::move(c))),rows(b),
    income(product(b,context->nations.size(),6),0),effective(product(b,context->territories.size(),2),0) {}

void IncomeOracleBatch::capture(std::size_t row,const State& s) {
    if(row>=rows)throw std::out_of_range("Income oracle row index");
    sameDefinition(*context,s);
    std::fill_n(income.data()+row*context->nations.size()*6,context->nations.size()*6,0);
    std::fill_n(effective.data()+row*context->territories.size()*2,context->territories.size()*2,0);
    for(std::size_t n=0;n<context->nations.size();++n) {
        auto* out=income.data()+(row*context->nations.size()+n)*6;
        try {
            const auto value=evaluateIncome(s,context->nations[n]);
            const auto territory=value.components.find("territorial"),bonus=value.components.find("china_control_bonus");
            out[1]=(territory!=value.components.end()?1:0)|(bonus!=value.components.end()?2:0);
            out[2]=value.collectable;out[3]=territory==value.components.end()?0:territory->second;
            out[4]=bonus==value.components.end()?0:bonus->second;out[5]=value.total;
        }catch(const std::out_of_range&){out[0]=1;}catch(const std::exception&){out[0]=2;}
    }
    for(std::size_t t=0;t<context->territories.size();++t) {
        auto* out=effective.data()+(row*context->territories.size()+t)*2;
        try {out[1]=effectiveTerritorialIpp(s,context->territories[t]);}
        catch(const std::out_of_range&){out[0]=1;}catch(const std::exception&){out[0]=2;}
    }
}
} // namespace game::campaign
