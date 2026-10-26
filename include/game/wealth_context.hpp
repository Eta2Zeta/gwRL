#pragma once
#include "game/income_batch.hpp"
#include <memory>
#include <vector>

namespace game::campaign {
struct WealthContext {
    std::shared_ptr<const Definition> definition;
    std::shared_ptr<const IncomeContext> income;
    std::vector<Id> unitTypes, facilityTypes;
    // [U,4]: completed asset price, valid price, per-hit repair cost, valid cost.
    std::vector<std::int64_t> units;
    // [F,2]: completed asset value, per-hit repair cost (absent -> zero).
    std::vector<std::int64_t> facilities;
    // [T,T,2]: price, valid directed-pair lookup. Both directions are inspected
    // by the original railAssetPrice helper, never intrinsic node terrain.
    std::vector<std::int64_t> rails;
    explicit WealthContext(std::shared_ptr<const Definition>);
};

struct WealthOracleBatch {
    std::shared_ptr<const WealthContext> context;
    std::size_t rows;
    // These are actual original native double values, not a second formula.
    std::vector<double> components, wealth, gaps, terminal;
    // [B,2]: wealth API exception, terminalReturns exception. Nonterminal
    // returns remain zero even when the independent wealth API would throw.
    std::vector<std::int64_t> errors;
    explicit WealthOracleBatch(std::shared_ptr<const WealthContext>,std::size_t);
    void capture(std::size_t,const State&);
};
}
