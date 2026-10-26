#pragma once
// Direct indexed input and independent native oracle for income evaluation.
#include "game/economy.hpp"
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace game::campaign {
struct IncomeContext {
    std::string definitionFingerprint;
    std::vector<Id> territories, nations;
    // Row-major [T,3]: baseIPP, baseIPP_valid, exact_Japan_bonus_zone.
    // Row-major [N,2]: forced_account_identity, exact_Japan_identity.
    std::vector<std::int64_t> territoryStatic, nationStatic;
    std::int64_t intMinimum, intMaximum;
    explicit IncomeContext(const Definition&);
};

struct IncomeBatch {
    std::shared_ptr<const IncomeContext> context;
    std::size_t rows;
    // [B,T,4]: territory_present, exact_possessor_index(-1:none/foreign),
    //          city_ipp_lost(default0), signed_city_damage(default0).
    std::vector<std::int64_t> territoryState;
    // [B,N,6]: nation_present, treasury_HAS_VALUE, dynamic_major,
    //          surrendered, capital_map_present, capital_zone_index(-1:unknown).
    std::vector<std::int64_t> nationState;
    explicit IncomeBatch(std::shared_ptr<const IncomeContext>, std::size_t);
    void capture(std::size_t row, const State&);
};

struct IncomeOracleBatch {
    std::shared_ptr<const IncomeContext> context;
    std::size_t rows;
    // [B,N,6]: exception_class, component_mask, collectable,
    //          territorial_component, China_bonus_component, total.
    // exception_class:0success,1std::out_of_range,2otherstd::exception.
    // Every result comes from the existing evaluateIncome, not a second formula.
    std::vector<std::int64_t> income;
    // [B,T,2]: exception_class, existing effectiveTerritorialIpp result.
    std::vector<std::int64_t> effective;
    explicit IncomeOracleBatch(std::shared_ptr<const IncomeContext>, std::size_t);
    void capture(std::size_t row, const State&);
};
} // namespace game::campaign
