#pragma once
#include "game/income_batch.hpp"
#include <cstdint>
#include <vector>

namespace game::campaign {
struct IncomeLedgerBatch {
    IncomeBatch incomeInputs;
    // The two expected keys lead a lossless union of all existing component
    // keys, including unknown/old keys that must survive a rejected lane.
    std::vector<Id> componentIds{"territorial", "china_control_bonus"};
    // [B,N,2]: optional treasury value (presence in incomeInputs), incomeKnown.
    std::vector<std::int64_t> ledger;
    // [B,N,K,2]: component present, component value. No component count cap.
    std::vector<std::int64_t> components;
    // [B,2]: exact current nation index, incomeCollected. Other clock fields
    // are deliberately outside this accounting operation and never rewritten.
    std::vector<std::int64_t> clock;
    explicit IncomeLedgerBatch(std::shared_ptr<const IncomeContext>, std::size_t rows);
    void capture(std::size_t row, const State&);
  private:
    void addComponent(const Id&);
};

struct IncomeLedgerOracleBatch {
    IncomeLedgerBatch after;
    // [B]: 0 success, 1 std::out_of_range, 2 other std::exception.
    // Each lane executes applyIncomeLedger on a cloned State. A rejected
    // transaction retains its complete original ledger, exactly as Engine.
    std::vector<std::int64_t> errors;
    explicit IncomeLedgerOracleBatch(std::shared_ptr<const IncomeContext>, std::size_t rows);
    void capture(std::size_t row, const State&);
};
}
