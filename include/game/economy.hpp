#pragma once

#include "game/campaign.hpp"

namespace game::campaign {

struct IncomeBreakdown {
    std::map<Id, int> components;
    int total{0};
    bool collectable{false};
};

int effectiveTerritorialIpp(const State &, const Id &zone);
// Whether upgrading this unit to `type` leaves its transport, if it is aboard
// one, with cargo it may carry. An upgrade that would not waits on the build
// queue (user ruling RCL-021; RB 12.3).
bool upgradeKeepsCargo(const State &, const UnitState &unit, const Id &type);
// Whether the rules can ever give this nation this part of an income: land
// for the three nations that keep an account, and Japan's bonus for the
// Chinese land it holds. evaluateIncome names no other part, and the network's
// input asks about these pairs only (zone_encoding.cpp).
bool incomePartPossible(const Id &nation, const Id &part);
// The nation's income as the position stands: its parts, whether the nation
// may collect it, and the total it would collect.
IncomeBreakdown evaluateIncome(const State &, const Id &nation);
// Stores the parts of every nation's income in the state. EconomyRules::settle
// does this at the end of every transition, so a recorded position never
// carries an income from before land changed hands.
void refreshIncome(State &);
void reconcileCapturedFacilities(State &, const Id &zone, const std::optional<Id> &oldOwner,
                                 const Id &newOwner);
bool lendLeasePermitted(const State &, const Id &sender, const Id &recipient);
std::vector<Action> lendLeaseActions(const State &);
bool applyLendLeaseAction(State &, const Action &);
// Beginning-of-turn capacities are caps; damage and lost supply can lower them.
int facilityCapacity(const State &, const Id &nation, const Id &facility, bool repair = false);
void beginEconomyTurn(State &);
void finishEconomyPlacement(State &);
// Used by strategic bombing. Setbacks undo progress, never refund payments.
void damageConstruction(State &, const Id &project, int damage);
std::vector<Action> economyActions(const State &);
bool applyEconomyAction(State &, const Action &);
bool applyEconomyChance(State &, const ChanceRequest &, const ChanceOutcome &);

class EconomyRules final : public Rules {
  public:
    explicit EconomyRules(std::shared_ptr<const Rules> gameplay = nullptr);
    Id id() const override;
    std::vector<Action> actions(const State &) const override;
    std::vector<Action> interrupts(const State &) const override;
    bool phaseComplete(const State &) const override;
    void apply(State &, const Action &) const override;
    void applyChance(State &, const ChanceRequest &, const ChanceOutcome &) const override;
    void finishTurn(State &) const override;
    void beginTurn(State &) const override;
    void finishPhase(State &) const override;
    void settle(State &) const override;

  private:
    std::shared_ptr<const Rules> gameplay_;
};

} // namespace game::campaign
