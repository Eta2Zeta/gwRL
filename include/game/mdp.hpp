#pragma once

#include "game/action.hpp"
#include "game/game_state.hpp"

#include <algorithm>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

namespace game {

struct StepResult {
    std::string actingNation;
    Phase phaseBefore {Phase::PurchaseUnits};
    Action action;
    std::vector<std::string> detailLines;
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

        applyAction(gameState, action, result);
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
        std::vector<std::string> roundLogs;
    };

    static bool isLandCombatUnit(const Unit& unit) {
        return unit.kind() == UnitKind::Infantry || unit.kind() == UnitKind::Marine;
    }

    static bool isCombatMovableInfantry(const Unit& unit) {
        return unit.kind() == UnitKind::Infantry;
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
            const auto attackerCountBeforeRound = attackingUnits.size();
            const auto defenderCountBeforeRound = defendingUnits.size();
            const auto attackRemainderBeforeRound = accumulatedAttack;
            const auto defenseRemainderBeforeRound = accumulatedDefense;

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

            outcome.roundLogs.push_back(
                "round "
                + std::to_string(outcome.roundLogs.size() / 2 + 1)
                + ": attacker "
                + std::to_string(attackerCountBeforeRound)
                + " Inf (" + std::to_string(attackRemainderBeforeRound) + "+"
                + std::to_string(roundAttack) + "=" + std::to_string(accumulatedAttack)
                + "), defender "
                + std::to_string(defenderCountBeforeRound)
                + " Inf (" + std::to_string(defenseRemainderBeforeRound) + "+"
                + std::to_string(roundDefense) + "=" + std::to_string(accumulatedDefense)
                + ")");

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

            outcome.roundLogs.push_back(
                "  after casualties: attacker "
                + std::to_string(attackingUnits.size())
                + " Inf attack_remainder=" + std::to_string(accumulatedAttack)
                + ", defender "
                + std::to_string(defendingUnits.size())
                + " Inf defense_remainder=" + std::to_string(accumulatedDefense)
                + ", losses attacker=" + std::to_string(attackerLosses)
                + ", defender=" + std::to_string(defenderLosses));
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
        std::vector<std::string> sourceZoneOrder;
        std::unordered_map<std::string, int> availableInfantryByZone;

        for (const auto& unitPtr : gameState.units()) {
            const auto& unit = *unitPtr;
            if (unit.ownerId() != actingNationId || !isCombatMovableInfantry(unit) || unit.movementLeft() <= 0) {
                continue;
            }

            const auto& originZone = gameState.zone(unit.zoneId());
            if (originZone.kind != ZoneKind::Land) {
                continue;
            }

            auto [it, inserted] = availableInfantryByZone.emplace(originZone.id, 0);
            if (inserted) {
                sourceZoneOrder.push_back(originZone.id);
            }
            ++it->second;
        }

        for (const auto& originZoneId : sourceZoneOrder) {
            const auto& originZone = gameState.zone(originZoneId);
            const auto availableInfantry = availableInfantryByZone.at(originZoneId);
            for (const auto& neighbor : originZone.neighbors) {
                if (!gameState.hasZone(neighbor.id)) {
                    continue;
                }
                const auto& destinationZone = gameState.zone(neighbor.id);
                if (!isEnemyControlledLandZone(gameState, actingNationId, destinationZone)) {
                    continue;
                }
                for (int infantryCount = 1; infantryCount <= availableInfantry; ++infantryCount) {
                    actions.push_back(Action{
                        .kind = ActionKind::MoveCombatUnit,
                        .sourceZoneId = originZone.id,
                        .targetZoneId = destinationZone.id,
                        .unitCount = infantryCount,
                    });
                }
            }
        }
        actions.push_back(Action{ActionKind::EndPhase});
        return actions;
    }

    void applyAction(GameState& gameState, const Action& action, StepResult& result) const {
        switch (action.kind) {
            case ActionKind::DeclareWarOnChina:
                applyDeclareWarOnChina(gameState, result);
                return;
            case ActionKind::MoveCombatUnit:
                applyCombatMove(gameState, action, result);
                return;
            case ActionKind::EndPhase:
                gameState.advancePhase();
                return;
        }
        throw std::runtime_error("Unsupported action kind");
    }

    void applyDeclareWarOnChina(GameState& gameState, StepResult& result) const {
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
        gameState.activateAllWarlordsForKmt();
        result.detailLines.push_back("declaration result: all warlord lands and units transfer to KMT");
    }

    void applyCombatMove(GameState& gameState, const Action& action, StepResult& result) const {
        if (gameState.currentPhase() != Phase::Combat) {
            throw std::runtime_error("MoveCombatUnit can only be used in combat");
        }
        if (!action.sourceZoneId.has_value() || !action.targetZoneId.has_value() || !action.unitCount.has_value()) {
            throw std::runtime_error("MoveCombatUnit requires a source zone, target zone, and unit count");
        }

        const auto actingNationId = gameState.currentNation();
        const auto& sourceZoneId = *action.sourceZoneId;
        const auto& targetZoneId = *action.targetZoneId;
        const auto infantryCount = *action.unitCount;
        if (infantryCount <= 0) {
            throw std::runtime_error("MoveCombatUnit requires a positive unit count");
        }

        const auto& originZone = gameState.zone(sourceZoneId);
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

        std::vector<Unit*> attackingUnits;
        for (auto* unit : gameState.unitsInZone(sourceZoneId)) {
            if (unit->ownerId() != actingNationId || !isCombatMovableInfantry(*unit) || unit->movementLeft() <= 0) {
                continue;
            }
            attackingUnits.push_back(unit);
        }
        if (static_cast<int>(attackingUnits.size()) < infantryCount) {
            throw std::runtime_error("Combat move requested more infantry than are available in the source zone");
        }
        attackingUnits.resize(static_cast<std::size_t>(infantryCount));
        for (auto* unit : attackingUnits) {
            unit->spendMovement(1);
        }

        std::vector<const Unit*> defendingUnits;
        for (auto* unit : gameState.unitsInZone(targetZoneId)) {
            if (unit->ownerId() != actingNationId && isLandCombatUnit(*unit)) {
                defendingUnits.push_back(unit);
            }
        }

        if (defendingUnits.empty()) {
            result.detailLines.push_back("combat: no defenders, territory occupied immediately");
            for (auto* unit : attackingUnits) {
                gameState.moveUnit(unit, targetZoneId, 0);
            }
            gameState.setZoneController(targetZoneId, std::string(actingNationId));
            return;
        }

        const auto outcome = resolveLandCombat(
            gameState.zone(targetZoneId),
            std::vector<const Unit*>(attackingUnits.begin(), attackingUnits.end()),
            defendingUnits);
        result.detailLines.insert(
            result.detailLines.end(),
            outcome.roundLogs.begin(),
            outcome.roundLogs.end());

        gameState.removeUnits(outcome.destroyedDefenders);
        gameState.removeUnits(outcome.destroyedAttackers);

        if (outcome.attackersWon) {
            result.detailLines.push_back("combat result: attackers won and occupy the territory");
            for (auto* unit : attackingUnits) {
                if (std::find(outcome.destroyedAttackers.begin(), outcome.destroyedAttackers.end(), unit)
                    == outcome.destroyedAttackers.end()) {
                    gameState.moveUnit(unit, targetZoneId, 0);
                }
            }
            gameState.setZoneController(targetZoneId, std::string(actingNationId));
        } else {
            result.detailLines.push_back("combat result: defenders held, surviving attackers stay in origin");
        }
    }
};

}  // namespace game
