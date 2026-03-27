#pragma once

#include "game/action.hpp"
#include "game/battle_resolver.hpp"
#include "game/mdp.hpp"

#include <algorithm>
#include <array>
#include <filesystem>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace game {

class CompositionBattleEnv {
  public:
    CompositionBattleEnv(
        int attackerBudget = 10,
        int defenderBudget = 10,
        std::string terrain = "normal",
        bool isCity = false)
        : initialAttackerBudget_(attackerBudget),
          initialDefenderBudget_(defenderBudget),
          battleZone_(Zone{
              .id = "battlefield",
              .displayName = "Battlefield",
              .kind = ZoneKind::Land,
              .terrain = std::move(terrain),
              .controller = std::string(kDefenderId),
              .isCity = isCity,
              .incomeValue = 0,
          }) {
        if (attackerBudget < 0 || defenderBudget < 0) {
            throw std::runtime_error("CompositionBattleEnv budgets must be non-negative");
        }
        reset();
    }

    CompositionBattleEnv clone() const { return *this; }

    void reset() {
        attackerBudgetRemaining_ = initialAttackerBudget_;
        defenderBudgetRemaining_ = initialDefenderBudget_;
        attackerDone_ = false;
        defenderDone_ = false;
        attackerTurn_ = true;
        terminal_ = false;
        finalReward_ = 0.0;
        winnerId_.clear();
        unitCounts_ = {};
    }

    bool isTerminal() const { return terminal_; }
    std::string currentNation() const { return attackerTurn_ ? std::string(kAttackerId) : std::string(kDefenderId); }
    std::string currentPhase() const { return terminal_ ? "terminal" : "purchase_units"; }

    std::vector<Action> legalActions() const {
        if (terminal_) {
            return {};
        }
        std::vector<Action> actions;
        const auto budgetRemaining = attackerTurn_ ? attackerBudgetRemaining_ : defenderBudgetRemaining_;
        for (const auto unitKind : BattleResolver::compositionPurchasableUnitKinds()) {
            const auto cost = purchaseCost(unitKind);
            if (cost <= 0 || budgetRemaining < cost) {
                continue;
            }
            const auto maxCount = budgetRemaining / cost;
            for (int unitCount = 1; unitCount <= maxCount; ++unitCount) {
                actions.push_back(Action{
                    .kind = ActionKind::PurchaseUnit,
                    .unitCount = unitCount,
                    .unitKind = unitKind,
                });
            }
        }
        actions.push_back(Action{ActionKind::EndPhase});
        return actions;
    }

    std::vector<double> encodeState() const {
        std::vector<double> features;
        features.reserve(stateFeatureLabels().size());
        features.push_back(attackerTurn_ ? 1.0 : 0.0);
        features.push_back(attackerTurn_ ? 0.0 : 1.0);
        features.push_back(static_cast<double>(attackerBudgetRemaining_));
        features.push_back(static_cast<double>(defenderBudgetRemaining_));
        features.push_back(attackerDone_ ? 1.0 : 0.0);
        features.push_back(defenderDone_ ? 1.0 : 0.0);
        features.push_back(battleZone_.terrain == "mountain" ? 1.0 : 0.0);
        features.push_back(battleZone_.isCity ? 1.0 : 0.0);
        for (const auto sideIndex : {0U, 1U}) {
            for (const auto unitKind : BattleResolver::compositionPurchasableUnitKinds()) {
                features.push_back(static_cast<double>(unitCounts_.at(sideIndex).at(unitKindIndex(unitKind))));
            }
        }
        return features;
    }

    std::vector<std::vector<double>> encodeLegalActions() const {
        std::vector<std::vector<double>> encodedActions;
        for (const auto& action : legalActions()) {
            encodedActions.push_back(encodeAction(action));
        }
        return encodedActions;
    }

    std::vector<std::string> stateFeatureLabels() const {
        std::vector<std::string> labels{
            "current_side.attacker",
            "current_side.defender",
            "budget_remaining.attacker",
            "budget_remaining.defender",
            "purchase_done.attacker",
            "purchase_done.defender",
            "battlefield.is_mountain",
            "battlefield.is_city",
        };
        for (const auto sideId : {std::string(kAttackerId), std::string(kDefenderId)}) {
            for (const auto unitKind : BattleResolver::compositionPurchasableUnitKinds()) {
                labels.push_back(sideId + ".count." + std::string(toString(unitKind)));
            }
        }
        return labels;
    }

    std::vector<std::string> actionFeatureLabels() const {
        std::vector<std::string> labels{
            "action_kind.purchase_unit",
            "action_kind.end_phase",
        };
        for (const auto unitKind : BattleResolver::compositionPurchasableUnitKinds()) {
            labels.push_back("unit_kind." + std::string(toString(unitKind)));
        }
        labels.push_back("requested_unit_count");
        labels.push_back("available_unit_count");
        labels.push_back("requested_unit_fraction");
        return labels;
    }

    StepResult step(const Action& action) {
        if (terminal_) {
            throw std::runtime_error("Cannot step a terminal CompositionBattleEnv");
        }

        StepResult result{
            .actingNation = currentNation(),
            .phaseBefore = Phase::PurchaseUnits,
            .action = action,
        };

        if (action.kind == ActionKind::PurchaseUnit) {
            applyPurchase(action, result);
        } else if (action.kind == ActionKind::EndPhase) {
            applyEndPhase(result);
        } else {
            throw std::runtime_error("CompositionBattleEnv only supports PurchaseUnit and EndPhase");
        }

        result.terminal = terminal_;
        if (!terminal_) {
            result.nextNation = currentNation();
            result.nextPhase = Phase::PurchaseUnits;
        }
        return result;
    }

    double finalReward() const { return finalReward_; }
    double terminalRewardFor(std::string_view nationId) const {
        if (!terminal_) {
            return 0.0;
        }
        if (nationId == kAttackerId) {
            return finalReward_;
        }
        if (nationId == kDefenderId) {
            return -finalReward_;
        }
        throw std::runtime_error("Unknown nation id in terminalRewardFor");
    }

    std::string winnerId() const { return winnerId_; }
    int budgetRemaining(std::string_view nationId) const {
        if (nationId == kAttackerId) {
            return attackerBudgetRemaining_;
        }
        if (nationId == kDefenderId) {
            return defenderBudgetRemaining_;
        }
        throw std::runtime_error("Unknown nation id in budgetRemaining");
    }

    int purchasedUnitCount(std::string_view nationId, UnitKind unitKind) const {
        const auto sideIndex = sideIndexFor(nationId);
        return unitCounts_.at(sideIndex).at(unitKindIndex(unitKind));
    }

  private:
    static constexpr std::string_view kAttackerId = "Attacker";
    static constexpr std::string_view kDefenderId = "Defender";

    std::vector<double> encodeAction(const Action& action) const {
        std::vector<double> features;
        features.reserve(actionFeatureLabels().size());
        features.push_back(action.kind == ActionKind::PurchaseUnit ? 1.0 : 0.0);
        features.push_back(action.kind == ActionKind::EndPhase ? 1.0 : 0.0);
        for (const auto unitKind : BattleResolver::compositionPurchasableUnitKinds()) {
            features.push_back(action.unitKind.has_value() && *action.unitKind == unitKind ? 1.0 : 0.0);
        }
        const auto availableCount = availableUnitCountForAction(action);
        const auto requestedCount = action.unitCount.has_value() ? static_cast<double>(*action.unitCount) : 0.0;
        features.push_back(requestedCount);
        features.push_back(availableCount);
        features.push_back(availableCount > 0.0 ? requestedCount / availableCount : 0.0);
        return features;
    }

    double availableUnitCountForAction(const Action& action) const {
        if (action.kind != ActionKind::PurchaseUnit || !action.unitKind.has_value()) {
            return 0.0;
        }
        const auto budgetRemaining = attackerTurn_ ? attackerBudgetRemaining_ : defenderBudgetRemaining_;
        const auto cost = purchaseCost(*action.unitKind);
        if (cost <= 0 || budgetRemaining < cost) {
            return 0.0;
        }
        return static_cast<double>(budgetRemaining / cost);
    }

    void applyPurchase(const Action& action, StepResult& result) {
        if (!action.unitKind.has_value() || !action.unitCount.has_value()) {
            throw std::runtime_error("PurchaseUnit requires unit kind and unit count");
        }
        const auto unitKind = *action.unitKind;
        const auto unitCount = *action.unitCount;
        if (unitCount <= 0) {
            throw std::runtime_error("PurchaseUnit count must be positive");
        }
        const auto unitCost = purchaseCost(unitKind);
        const auto totalCost = unitCost * unitCount;
        auto& budgetRemaining = attackerTurn_ ? attackerBudgetRemaining_ : defenderBudgetRemaining_;
        if (unitCost <= 0 || totalCost > budgetRemaining) {
            throw std::runtime_error("PurchaseUnit exceeds remaining budget");
        }
        budgetRemaining -= totalCost;
        ++unitCounts_.at(currentSideIndex()).at(unitKindIndex(unitKind));
        if (unitCount > 1) {
            unitCounts_.at(currentSideIndex()).at(unitKindIndex(unitKind)) += unitCount - 1;
        }
        result.detailLines.push_back(
            std::string(currentNation())
            + " purchase: "
            + std::to_string(unitCount)
            + " "
            + std::string(toString(unitKind))
            + " for "
            + std::to_string(totalCost)
            + " budget");
    }

    void applyEndPhase(StepResult& result) {
        if (attackerTurn_) {
            attackerDone_ = true;
            attackerTurn_ = false;
            result.detailLines.push_back("attacker composition locked");
            return;
        }

        defenderDone_ = true;
        result.detailLines.push_back("defender composition locked");
        resolveBattle(result);
    }

    void resolveBattle(StepResult& result) {
        auto attackerUnits = buildUnitsForSide(kAttackerId, 0U);
        auto defenderUnits = buildUnitsForSide(kDefenderId, 1U);
        std::vector<const Unit*> attackerRefs;
        std::vector<const Unit*> defenderRefs;
        attackerRefs.reserve(attackerUnits.size());
        defenderRefs.reserve(defenderUnits.size());
        for (const auto& unit : attackerUnits) {
            attackerRefs.push_back(unit.get());
        }
        for (const auto& unit : defenderUnits) {
            defenderRefs.push_back(unit.get());
        }

        result.detailLines.push_back(
            "resolving composition battle: attackers=" + std::to_string(attackerRefs.size())
            + ", defenders=" + std::to_string(defenderRefs.size()));
        const auto outcome = BattleResolver::resolveLandCombat(battleZone_, attackerRefs, defenderRefs);
        result.detailLines.insert(result.detailLines.end(), outcome.roundLogs.begin(), outcome.roundLogs.end());

        terminal_ = true;
        if (outcome.attackersWon) {
            finalReward_ = 1.0;
            winnerId_ = std::string(kAttackerId);
            result.detailLines.push_back("battle result: attackers won");
        } else if (outcome.defendersWon) {
            finalReward_ = -1.0;
            winnerId_ = std::string(kDefenderId);
            result.detailLines.push_back("battle result: defenders won");
        } else {
            finalReward_ = 0.0;
            winnerId_ = "Draw";
            result.detailLines.push_back("battle result: draw");
        }
    }

    std::vector<std::unique_ptr<Unit>> buildUnitsForSide(std::string_view ownerId, std::size_t sideIndex) const {
        std::vector<std::unique_ptr<Unit>> units;
        for (const auto unitKind : BattleResolver::compositionPurchasableUnitKinds()) {
            const auto count = unitCounts_.at(sideIndex).at(unitKindIndex(unitKind));
            for (int index = 0; index < count; ++index) {
                units.push_back(makeUnit(unitKind, std::string(ownerId), battleZone_.id));
            }
        }
        return units;
    }

    std::size_t currentSideIndex() const {
        return attackerTurn_ ? 0U : 1U;
    }

    static std::size_t sideIndexFor(std::string_view nationId) {
        if (nationId == kAttackerId) {
            return 0U;
        }
        if (nationId == kDefenderId) {
            return 1U;
        }
        throw std::runtime_error("Unknown nation id in sideIndexFor");
    }

    int initialAttackerBudget_ {0};
    int initialDefenderBudget_ {0};
    int attackerBudgetRemaining_ {0};
    int defenderBudgetRemaining_ {0};
    bool attackerDone_ {false};
    bool defenderDone_ {false};
    bool attackerTurn_ {true};
    bool terminal_ {false};
    double finalReward_ {0.0};
    std::string winnerId_;
    Zone battleZone_;
    std::array<std::array<int, unitKindCount()>, 2> unitCounts_ {};
};

}  // namespace game
