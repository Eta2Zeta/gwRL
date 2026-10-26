#include "game/income_ledger_batch.hpp"
#include "game/income_ledger.hpp"
#include <algorithm>
#include <limits>
#include <stdexcept>

namespace game::campaign {
namespace {
std::size_t product(std::size_t a, std::size_t b, std::size_t c) {
    if (b && a > std::numeric_limits<std::size_t>::max()/b)
        throw std::length_error("Income ledger allocation overflow");
    a *= b;
    if (c && a > std::numeric_limits<std::size_t>::max()/c)
        throw std::length_error("Income ledger allocation overflow");
    return a*c;
}
std::int64_t nationIndex(const IncomeContext& context, const Id& id) {
    const auto found=std::lower_bound(context.nations.begin(),context.nations.end(),id);
    return found!=context.nations.end()&&*found==id ? std::distance(context.nations.begin(),found) : -1;
}
}

IncomeLedgerBatch::IncomeLedgerBatch(std::shared_ptr<const IncomeContext> context,std::size_t rows):
    incomeInputs(std::move(context),rows),ledger(product(rows,incomeInputs.context->nations.size(),2),0),
    components(product(rows,incomeInputs.context->nations.size(),4),0),clock(product(rows,2,1),0) {}

void IncomeLedgerBatch::addComponent(const Id& id) {
    if(std::find(componentIds.begin(),componentIds.end(),id)!=componentIds.end())return;
    const auto old=componentIds.size(), count=product(incomeInputs.rows,incomeInputs.context->nations.size(),1);
    if(old==std::numeric_limits<std::size_t>::max())throw std::length_error("Income component count overflow");
    std::vector<std::int64_t> expanded(product(count,old+1,2),0);
    for(std::size_t item=0;item<count;++item)
        std::copy_n(components.data()+item*old*2,old*2,expanded.data()+item*(old+1)*2);
    componentIds.push_back(id);
    components=std::move(expanded);
}

void IncomeLedgerBatch::capture(std::size_t row,const State& state) {
    incomeInputs.capture(row,state); // Domain/definition check before capture.
    const auto N=incomeInputs.context->nations.size();
    for(const auto& [id,nation]:state.nations)
        for(const auto& [component,value]:nation.incomeComponents)addComponent(component);
    const auto K=componentIds.size();
    std::fill_n(ledger.data()+row*N*2,N*2,0);
    std::fill_n(components.data()+row*N*K*2,N*K*2,0);
    for(const auto& [id,nation]:state.nations) {
        const auto n=static_cast<std::size_t>(nationIndex(*incomeInputs.context,id));
        ledger[(row*N+n)*2]=nation.treasury.value_or(0);
        ledger[(row*N+n)*2+1]=nation.incomeKnown;
        for(const auto& [component,value]:nation.incomeComponents) {
            const auto k=std::distance(componentIds.begin(),std::find(componentIds.begin(),componentIds.end(),component));
            components[((row*N+n)*K+k)*2]=1;
            components[((row*N+n)*K+k)*2+1]=value;
        }
    }
    clock[row*2]=nationIndex(*incomeInputs.context,state.currentNation());
    clock[row*2+1]=state.clock.incomeCollected;
}

IncomeLedgerOracleBatch::IncomeLedgerOracleBatch(std::shared_ptr<const IncomeContext> context,std::size_t rows):
    after(std::move(context),rows),errors(rows,0) {}

void IncomeLedgerOracleBatch::capture(std::size_t row,const State& state) {
    after.capture(row,state); // Retain all original keys even if success erases them.
    auto next=state.clone();
    try {applyIncomeLedger(next);errors.at(row)=0;after.capture(row,next);}
    catch(const std::out_of_range&) {errors.at(row)=1;}
    catch(const std::exception&) {errors.at(row)=2;}
}
}
