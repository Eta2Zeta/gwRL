#pragma once

#include "game/action.hpp"
#include "game/game_state.hpp"

#include <algorithm>
#include <optional>
#include <string>
#include <vector>

namespace game {

struct StepResult {
    std::string actingNation;
    Phase phaseBefore {Phase::PurchaseUnits};
    Action action;
    bool terminal {false};
    std::optional<std::string> nextNation;
    std::optional<Phase> nextPhase;
};

class SimplifiedChinaMdp {
  public:
    std::vector<Action> legalActions(const GameState& gameState) const {
        if (gameState.isTerminal()) {
            return {};
        }
        switch (gameState.currentPhase()) {
            case Phase::DeclarationOfWar:
                return legalDeclarationOfWarActions(gameState);
            case Phase::Combat:
                return legalCombatActions(gameState);
            case Phase::PurchaseUnits:
            case Phase::NonCombat:
            case Phase::PlaceUnits:
                return {Action{ActionKind::EndPhase}};
        }
        throw std::runtime_error("Unsupported phase in legalActions");
    }

    StepResult step(GameState& gameState, const Action& action) const {
        if (gameState.isTerminal()) {
            throw std::runtime_error("Cannot step a terminal state");
        }

        StepResult result{
            .actingNation = std::string(gameState.currentNation()),
            .phaseBefore = gameState.currentPhase(),
            .action = action,
        };

        applyAction(gameState, action);
        result.terminal = gameState.isTerminal();
        if (!result.terminal) {
            result.nextNation = std::string(gameState.currentNation());
            result.nextPhase = gameState.currentPhase();
        }

        return result;
    }

  private:
    struct CombatOutcome {
        bool attackersWon {false};
        std::vector<const Unit*> destroyedAttackers;
        std::vector<const Unit*> destroyedDefenders;
    };

    static bool isLandCombatUnit(const Unit& unit) {
        return unit.kind() == UnitKind::Infantry || unit.kind() == UnitKind::Marine;
    }

    static int baseAttackValue(const Unit& unit) {
        switch (unit.kind()) {
            case UnitKind::Infantry:
            case UnitKind::Marine:
                return 2;
            case UnitKind::Fighter:
            case UnitKind::Transport:
                return 0;
        }
        throw std::runtime_error("Unknown unit kind for attack value");
    }

    static int baseDefenseValue(const Unit& unit) {
        switch (unit.kind()) {
            case UnitKind::Infantry:
            case UnitKind::Marine:
                return 4;
            case UnitKind::Fighter:
            case UnitKind::Transport:
                return 0;
        }
        throw std::runtime_error("Unknown unit kind for defense value");
    }

    static int adjustedAttackValue(const Unit& unit, const Zone& battleZone) {
        auto value = baseAttackValue(unit);
        if (battleZone.terrain == "mountain") {
            value -= 1;
        }
        return std::max(0, value);
    }

    static int adjustedDefenseValue(const Unit& unit, const Zone& battleZone) {
        auto value = baseDefenseValue(unit);
        if (battleZone.isCity) {
            value += 1;
        }
        return std::max(0, value);
    }

    static void removeLowestValueCasualties(
        std::vector<const Unit*>& units,
        const Zone& battleZone,
        bool attackers,
        int casualtyCount,
        std::vector<const Unit*>& destroyedUnits) {
        if (casualtyCount <= 0 || units.empty()) {
            return;
        }
        std::stable_sort(
            units.begin(),
            units.end(),
            [&](const Unit* lhs, const Unit* rhs) {
                const auto lhsValue = attackers ? adjustedAttackValue(*lhs, battleZone)
                                                : adjustedDefenseValue(*lhs, battleZone);
                const auto rhsValue = attackers ? adjustedAttackValue(*rhs, battleZone)
                                                : adjustedDefenseValue(*rhs, battleZone);
                return lhsValue < rhsValue;
            });
        const auto actualLosses = std::min<std::size_t>(units.size(), static_cast<std::size_t>(casualtyCount));
        destroyedUnits.insert(destroyedUnits.end(), units.begin(), units.begin() + actualLosses);
        units.erase(units.begin(), units.begin() + actualLosses);
    }

    CombatOutcome resolveLandCombat(
        const Zone& battleZone,
        std::vector<const Unit*> attackingUnits,
        std::vector<const Unit*> defendingUnits) const {
        CombatOutcome outcome;
        int accumulatedAttack = 0;
        int accumulatedDefense = 0;

        while (!attackingUnits.empty() && !defendingUnits.empty()) {
            int roundAttack = 0;
            for (const auto* unit : attackingUnits) {
                roundAttack += adjustedAttackValue(*unit, battleZone);
            }

            int roundDefense = 0;
            for (const auto* unit : defendingUnits) {
                roundDefense += adjustedDefenseValue(*unit, battleZone);
            }

            if (roundAttack == 0 && roundDefense == 0) {
                break;
            }

            accumulatedAttack += roundAttack;
            accumulatedDefense += roundDefense;

            const auto defenderLosses = accumulatedAttack / 12;
            accumulatedAttack %= 12;
            const auto attackerLosses = accumulatedDefense / 12;
            accumulatedDefense %= 12;

            removeLowestValueCasualties(
                defendingUnits,
                battleZone,
                false,
                defenderLosses,
                outcome.destroyedDefenders);
            removeLowestValueCasualties(
                attackingUnits,
                battleZone,
                true,
                attackerLosses,
                outcome.destroyedAttackers);
        }

        outcome.attackersWon = defendingUnits.empty() && !attackingUnits.empty();
        return outcome;
    }

    static bool isEnemyControlledLandZone(
        const GameState& gameState,
        std::string_view actingNationId,
        const Zone& zone) {
        if (zone.kind != ZoneKind::Land) {
            return false;
        }
        if (zone.controller == actingNationId) {
            return false;
        }
        if (gameState.isWarlordFaction(zone.controller)) {
            return actingNationId != "KMT" && gameState.areAtWar(actingNationId, "KMT");
        }
        if (!gameState.hasNation(zone.controller)) {
            return false;
        }
        return gameState.areAtWar(actingNationId, zone.controller);
    }

    std::vector<Action> legalDeclarationOfWarActions(const GameState& gameState) const {
        std::vector<Action> actions;
        const auto actingNationId = gameState.currentNation();
        if (actingNationId == "Japan"
            && (!gameState.areAtWar("Japan", "CCP") || !gameState.areAtWar("Japan", "KMT"))) {
            actions.push_back(Action{ActionKind::DeclareWarOnChina});
        }
        actions.push_back(Action{ActionKind::EndPhase});
        return actions;
    }

    std::vector<Action> legalCombatActions(const GameState& gameState) const {
        std::vector<Action> actions;
        const auto actingNationId = gameState.currentNation();
        const auto& units = gameState.units();
        for (std::size_t unitIndex = 0; unitIndex < units.size(); ++unitIndex) {
            const auto& unit = *units[unitIndex];
            if (unit.ownerId() != actingNationId || !isLandCombatUnit(unit) || unit.movementLeft() <= 0) {
                continue;
            }

            const auto& originZone = gameState.zone(unit.zoneId());
            if (originZone.kind != ZoneKind::Land) {
                continue;
            }

            for (const auto& neighbor : originZone.neighbors) {
                if (!gameState.hasZone(neighbor.id)) {
                    continue;
                }
                const auto& destinationZone = gameState.zone(neighbor.id);
                if (!isEnemyControlledLandZone(gameState, actingNationId, destinationZone)) {
                    continue;
                }
                actions.push_back(Action{
                    .kind = ActionKind::MoveCombatUnit,
                    .unitIndex = unitIndex,
                    .targetZoneId = destinationZone.id,
                });
            }
        }
        actions.push_back(Action{ActionKind::EndPhase});
        return actions;
    }

    void applyAction(GameState& gameState, const Action& action) const {
        switch (action.kind) {
            case ActionKind::DeclareWarOnChina:
                applyDeclareWarOnChina(gameState);
                return;
            case ActionKind::MoveCombatUnit:
                applyCombatMove(gameState, action);
                return;
            case ActionKind::EndPhase:
                gameState.advancePhase();
                return;
        }
        throw std::runtime_error("Unsupported action kind");
    }

    void applyDeclareWarOnChina(GameState& gameState) const {
        if (gameState.currentPhase() != Phase::DeclarationOfWar) {
            throw std::runtime_error("DeclareWarOnChina can only be used in declaration_of_war");
        }
        if (gameState.currentNation() != "Japan") {
            throw std::runtime_error("Only Japan can declare war on China in this simplified model");
        }
        if (!gameState.areAtWar("Japan", "CCP")) {
            gameState.declareWar("Japan", "CCP");
        }
        if (!gameState.areAtWar("Japan", "KMT")) {
            gameState.declareWar("Japan", "KMT");
        }
    }

    void applyCombatMove(GameState& gameState, const Action& action) const {
        if (gameState.currentPhase() != Phase::Combat) {
            throw std::runtime_error("MoveCombatUnit can only be used in combat");
        }
        if (!action.unitIndex.has_value() || !action.targetZoneId.has_value()) {
            throw std::runtime_error("MoveCombatUnit requires a unit index and target zone");
        }

        const auto unitIndex = *action.unitIndex;
        const auto actingNationId = gameState.currentNation();
        auto* attackingUnit = &gameState.unitAt(unitIndex);
        if (attackingUnit->ownerId() != actingNationId) {
            throw std::runtime_error("Cannot move a unit owned by another nation");
        }
        if (!isLandCombatUnit(*attackingUnit)) {
            throw std::runtime_error("Only land units can use MoveCombatUnit");
        }
        if (attackingUnit->movementLeft() <= 0) {
            throw std::runtime_error("Unit has no movement remaining");
        }

        const auto& originZone = gameState.zone(attackingUnit->zoneId());
        const auto targetZoneId = *action.targetZoneId;
        const auto hasNeighbor = std::find_if(
                                     originZone.neighbors.begin(),
                                     originZone.neighbors.end(),
                                     [&](const ZoneNeighbor& neighbor) {
                                         return neighbor.id == targetZoneId;
                                     })
                                 != originZone.neighbors.end();
        if (!hasNeighbor) {
            throw std::runtime_error("Combat move target is not adjacent to the origin zone");
        }

        const auto& destinationZone = gameState.zone(targetZoneId);
        if (!isEnemyControlledLandZone(gameState, actingNationId, destinationZone)) {
            throw std::runtime_error("Combat move target is not an enemy-controlled land zone");
        }

        const auto originalController = destinationZone.controller;
        if (gameState.isWarlordFaction(originalController)) {
            gameState.activateWarlordForKmt(originalController);
        }

        attackingUnit->spendMovement(1);

        std::vector<const Unit*> defendingUnits;
        for (auto* unit : gameState.unitsInZone(targetZoneId)) {
            if (unit != attackingUnit && unit->ownerId() != actingNationId) {
                defendingUnits.push_back(unit);
            }
        }

        if (defendingUnits.empty()) {
            gameState.moveUnit(attackingUnit, targetZoneId, 0);
            gameState.setZoneController(targetZoneId, std::string(actingNationId));
            return;
        }

        const auto outcome = resolveLandCombat(
            gameState.zone(targetZoneId),
            std::vector<const Unit*>{attackingUnit},
            defendingUnits);

        gameState.removeUnits(outcome.destroyedDefenders);
        gameState.removeUnits(outcome.destroyedAttackers);

        if (outcome.attackersWon) {
            gameState.moveUnit(attackingUnit, targetZoneId, 0);
            gameState.setZoneController(targetZoneId, std::string(actingNationId));
        }
    }
};

}  // namespace game
