#include "game/wealth_context.hpp"
#include "game/campaign_objective.hpp"
#include "game/catalog.hpp"
#include <limits>
#include <stdexcept>

namespace game::campaign {
namespace {
std::size_t size(std::size_t a,std::size_t b,std::size_t c=1) {
    if(b&&a>std::numeric_limits<std::size_t>::max()/b)throw std::length_error("Wealth context allocation overflow");
    a*=b;
    if(c&&a>std::numeric_limits<std::size_t>::max()/c)throw std::length_error("Wealth context allocation overflow");
    return a*c;
}
}
WealthContext::WealthContext(std::shared_ptr<const Definition> value):definition(std::move(value)) {
    if(!definition)throw std::invalid_argument("Wealth context requires a definition");
    validateWealthDefinition(*definition);
    income=std::make_shared<IncomeContext>(*definition);
    for(const auto& [id,type]:definition->catalog->units()) {
        unitTypes.push_back(id);
        int asset=0,cost=0;bool assetValid=true,costValid=true;
        try{asset=completedAssetValue(*definition,id);}catch(const std::exception&){assetValid=false;}
        try{const auto* repair=type.repair.isObject()?type.repair.find("cost_per_hit"):nullptr;
            cost=repair&&repair->isNumber()?repair->asInt():0;
        }catch(const std::exception&){costValid=false;}
        units.insert(units.end(),{asset,assetValid,cost,costValid});
    }
    for(const auto& [id,type]:definition->catalog->facilities()) {
        facilityTypes.push_back(id);facilities.insert(facilities.end(),{type.assetValue,type.repairCost.value_or(0)});
    }
    const auto T=income->territories.size();rails.assign(size(T,T,2),0);
    State staticState;staticState.definition=definition;
    for(std::size_t a=0;a<T;++a)for(std::size_t b=0;b<T;++b)if(a!=b) {
        RailState rail;rail.endpointA=income->territories[a];rail.endpointB=income->territories[b];
        try{rails[(a*T+b)*2]=railAssetPrice(staticState,rail);rails[(a*T+b)*2+1]=1;}
        catch(const std::exception&){} // Preserve the original lazy lookup error.
    }
}
WealthOracleBatch::WealthOracleBatch(std::shared_ptr<const WealthContext> value,std::size_t count):
    context(std::move(value)),rows(count),components(size(count,3,5),0),wealth(size(count,3),0),
    gaps(size(count,3),0),terminal(size(count,3),0),errors(size(count,2),0) {
    if(!context)throw std::invalid_argument("Missing wealth context");
}
void WealthOracleBatch::capture(std::size_t row,const State& state) {
    if(row>=rows)throw std::out_of_range("Wealth oracle lane");
    if(!state.definition||state.definition->fingerprint!=context->definition->fingerprint)
        throw std::invalid_argument("Wealth context definition mismatch");
    try {
        const auto value=allianceWealth(state);
        const auto actualGaps=wealthGaps(state);
        for(std::size_t player=0;player<3;++player) {
            const auto& x=value[player];const auto base=(row*3+player)*5;
            components[base]=x.incomeRate;components[base+1]=x.units;components[base+2]=x.infrastructure;
            components[base+3]=x.treasury;components[base+4]=x.paidConstruction;
            wealth[row*3+player]=x.total();gaps[row*3+player]=actualGaps[player];
        }
    }catch(const std::out_of_range&){errors[row*2]=1;}catch(const std::exception&){errors[row*2]=2;}
    try{const auto result=terminalReturns(state);for(std::size_t player=0;player<3;++player)terminal[row*3+player]=result[player];}
    catch(const std::out_of_range&){errors[row*2+1]=1;}catch(const std::exception&){errors[row*2+1]=2;}
}
}
