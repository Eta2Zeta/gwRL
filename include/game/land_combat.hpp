#pragma once

#include "game/campaign.hpp"
#include "game/catalog.hpp"

namespace game::campaign {

// Movement supplies the final approach zone independently for every contingent.
// Registration does not resolve combat or roll dice, including empty attacks.
Id registerLandBattle(State &, const Id &zone, const Id &attacker, const std::vector<Id> &units,
                      const std::map<Id, Id> &origins);
Id registerAttritionBattle(State &, const Id &zone, const Id &attacker, const std::vector<Id> &units);
void beginLandBattle(State &, const Id &battle);

struct LandCombatStats {
    std::optional<int> threshold;
    int dice{0};
    int targetSelection{0};
    std::set<Id> targetClasses;
    bool firstStrike{false};
};
LandCombatStats landCombatStats(const State &, const BattleState &, const Id &unit, bool attacking,
                                int round);
bool citySurrounded(const State &, const Id &zone, const Id &defender);
std::set<Id> landRetreatOrigins(const State &, const BattleState &);
std::vector<Id> blitzEligible(const State &, const BattleState &);

class LandCombatRules final : public Rules {
  public:
    explicit LandCombatRules(std::shared_ptr<const Rules> gameplay = nullptr);
    Id id() const override;
    std::vector<Action> actions(const State &) const override;
    std::vector<Action> interrupts(const State &) const override;
    bool phaseComplete(const State &) const override;
    void apply(State &, const Action &) const override;
    void applyChance(State &, const ChanceRequest &, const ChanceOutcome &) const override;
    void finishTurn(State &) const override;
    void beginTurn(State &) const override;
    void finishPhase(State &) const override;

  private:
    std::shared_ptr<const Rules> gameplay_;
};

} // namespace game::campaign
