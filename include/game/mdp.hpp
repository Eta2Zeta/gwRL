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
            case Phase::PurchaseUnits:
                return legalPurchaseActions(gameState);
            case Phase::CombatMove:
                return legalCombatMoveActions(gameState);
            case Phase::CombatResolve:
                return legalCombatResolveActions(gameState);
            case Phase::NonCombat:
                return {Action{ActionKind::EndPhase}};
            case Phase::PlaceUnits:
                return legalPlaceActions(gameState);
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
    static std::vector<UnitKind> purchasableUnitKinds() {
        return {UnitKind::Infantry, UnitKind::Artillery, UnitKind::Fighter};
    }

    struct CombatOutcome {
        bool attackersWon {false};
        std::vector<const Unit*> destroyedAttackers;
        std::vector<const Unit*> destroyedDefenders;
        std::vector<std::string> roundLogs;
    };

    static bool isLandCombatUnit(const Unit& unit) {
        return unit.kind() == UnitKind::Infantry
            || unit.kind() == UnitKind::Artillery
            || unit.kind() == UnitKind::Marine;
    }

    static bool isCombatMovableInfantry(const Unit& unit) {
        return unit.kind() == UnitKind::Infantry;
    }

    static int baseAttackValue(const Unit& unit) {
        switch (unit.kind()) {
            case UnitKind::Infantry:
                return 2;
            case UnitKind::Artillery:
                return 3;
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
                return 4;
            case UnitKind::Artillery:
                return 3;
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

    static std::vector<std::string> sortedZoneIds(const GameState& gameState) {
        std::vector<std::string> zoneIds;
        zoneIds.reserve(gameState.zones().size());
        for (const auto& [zoneId, zone] : gameState.zones()) {
            zoneIds.push_back(zoneId);
        }
        std::sort(zoneIds.begin(), zoneIds.end());
        return zoneIds;
    }

    static std::vector<const Unit*> availableCombatMoveInfantry(
        const GameState& gameState,
        std::string_view nationId,
        std::string_view zoneId) {
        std::vector<const Unit*> units;
        for (auto* unit : gameState.unitsInZone(zoneId)) {
            if (unit->ownerId() != nationId
                || !isCombatMovableInfantry(*unit)
                || unit->movementLeft() <= 0
                || unit->hasPendingCombatTarget()) {
                continue;
            }
            units.push_back(unit);
        }
        return units;
    }

    static std::vector<const Unit*> pendingAttackersForZone(
        const GameState& gameState,
        std::string_view nationId,
        std::string_view targetZoneId) {
        std::vector<const Unit*> units;
        for (const auto& unitPtr : gameState.units()) {
            const auto* unit = unitPtr.get();
            if (unit->ownerId() != nationId || !unit->hasPendingCombatTarget()) {
                continue;
            }
            if (unit->pendingCombatTargetZoneId().has_value()
                && *unit->pendingCombatTargetZoneId() == targetZoneId) {
                units.push_back(unit);
            }
        }
        return units;
    }

    static bool hasPendingAttackersForZone(
        const GameState& gameState,
        std::string_view nationId,
        std::string_view targetZoneId) {
        return !pendingAttackersForZone(gameState, nationId, targetZoneId).empty();
    }

    static std::vector<const Unit*> defendingLandUnitsForZone(
        const GameState& gameState,
        std::string_view actingNationId,
        std::string_view targetZoneId) {
        std::vector<const Unit*> defenders;
        for (const auto* unit : gameState.unitsInZone(targetZoneId)) {
            if (unit->ownerId() != actingNationId && isLandCombatUnit(*unit)) {
                defenders.push_back(unit);
            }
        }
        return defenders;
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

    std::vector<Action> legalPurchaseActions(const GameState& gameState) const {
        std::vector<Action> actions;
        const auto actingNationId = gameState.currentNation();
        const auto& actingNation = gameState.nation(actingNationId);
        const auto remainingCapacity = std::max(
            0,
            gameState.totalFactoryOutputForNation(actingNationId) - gameState.pendingPurchaseCountFor(actingNationId));

        if (remainingCapacity > 0) {
            for (const auto unitKind : purchasableUnitKinds()) {
                const auto cost = purchaseCost(unitKind);
                if (cost <= 0 || actingNation.treasury() < cost) {
                    continue;
                }
                const auto maxCount = std::min(remainingCapacity, actingNation.treasury() / cost);
                for (int unitCount = 1; unitCount <= maxCount; ++unitCount) {
                    actions.push_back(Action{
                        .kind = ActionKind::PurchaseUnit,
                        .unitCount = unitCount,
                        .unitKind = unitKind,
                    });
                }
            }
        }

        actions.push_back(Action{ActionKind::EndPhase});
        return actions;
    }

    std::vector<Action> legalCombatMoveActions(const GameState& gameState) const {
        std::vector<Action> actions;
        const auto actingNationId = gameState.currentNation();
        std::vector<std::string> sourceZoneOrder;
        std::unordered_map<std::string, int> availableInfantryByZone;

        for (const auto& unitPtr : gameState.units()) {
            const auto& unit = *unitPtr;
            if (unit.ownerId() != actingNationId
                || !isCombatMovableInfantry(unit)
                || unit.movementLeft() <= 0
                || unit.hasPendingCombatTarget()) {
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
                if (hasPendingAttackersForZone(gameState, actingNationId, destinationZone.id)) {
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

    std::vector<Action> legalCombatResolveActions(const GameState& gameState) const {
        std::vector<Action> actions;
        const auto actingNationId = gameState.currentNation();

        for (const auto& zoneId : sortedZoneIds(gameState)) {
            const auto& zone = gameState.zone(zoneId);
            if (zone.kind != ZoneKind::Land || zone.controller == actingNationId) {
                continue;
            }

            const auto attackers = pendingAttackersForZone(gameState, actingNationId, zoneId);
            if (attackers.empty()) {
                continue;
            }

            const auto defenders = defendingLandUnitsForZone(gameState, actingNationId, zoneId);
            if (defenders.empty()) {
                continue;
            }

            actions.push_back(Action{
                .kind = ActionKind::ResolveCombat,
                .targetZoneId = zoneId,
            });
        }

        if (actions.empty()) {
            actions.push_back(Action{ActionKind::EndPhase});
        }
        return actions;
    }

    std::vector<Action> legalPlaceActions(const GameState& gameState) const {
        std::vector<Action> actions;
        const auto actingNationId = gameState.currentNation();
        const auto pendingCount = gameState.pendingPurchaseCountFor(actingNationId);

        for (const auto& zoneId : sortedZoneIds(gameState)) {
            const auto remainingCapacity = gameState.remainingPlacementCapacityForZone(actingNationId, zoneId);
            if (remainingCapacity <= 0) {
                continue;
            }
            for (const auto unitKind : purchasableUnitKinds()) {
                const auto pendingUnitsOfKind = gameState.pendingPurchaseCountFor(actingNationId, unitKind);
                const auto maxCount = std::min(remainingCapacity, pendingUnitsOfKind);
                for (int unitCount = 1; unitCount <= maxCount; ++unitCount) {
                    actions.push_back(Action{
                        .kind = ActionKind::PlaceUnit,
                        .targetZoneId = zoneId,
                        .unitCount = unitCount,
                        .unitKind = unitKind,
                    });
                }
            }
        }

        if (pendingCount == 0 || actions.empty()) {
            actions.push_back(Action{ActionKind::EndPhase});
        }
        return actions;
    }

    void applyAction(GameState& gameState, const Action& action, StepResult& result) const {
        switch (action.kind) {
            case ActionKind::DeclareWarOnChina:
                applyDeclareWarOnChina(gameState, result);
                return;
            case ActionKind::PurchaseUnit:
                applyPurchaseUnit(gameState, action, result);
                return;
            case ActionKind::MoveCombatUnit:
                applyCombatMove(gameState, action, result);
                return;
            case ActionKind::ResolveCombat:
                applyResolveCombat(gameState, action, result);
                return;
            case ActionKind::PlaceUnit:
                applyPlaceUnit(gameState, action, result);
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

    void applyPurchaseUnit(GameState& gameState, const Action& action, StepResult& result) const {
        if (gameState.currentPhase() != Phase::PurchaseUnits) {
            throw std::runtime_error("PurchaseUnit can only be used in purchase_units");
        }
        if (!action.unitKind.has_value() || !action.unitCount.has_value()) {
            throw std::runtime_error("PurchaseUnit requires a unit kind and count");
        }

        const auto actingNationId = gameState.currentNation();
        const auto unitKind = *action.unitKind;
        const auto unitCount = *action.unitCount;
        if (unitCount <= 0) {
            throw std::runtime_error("PurchaseUnit requires a positive unit count");
        }

        const auto remainingCapacity = std::max(
            0,
            gameState.totalFactoryOutputForNation(actingNationId) - gameState.pendingPurchaseCountFor(actingNationId));
        if (unitCount > remainingCapacity) {
            throw std::runtime_error("PurchaseUnit exceeds remaining factory output capacity");
        }

        const auto unitCost = purchaseCost(unitKind);
        const auto totalCost = unitCost * unitCount;
        auto& nation = gameState.nation(actingNationId);
        if (unitCost <= 0 || totalCost > nation.treasury()) {
            throw std::runtime_error("PurchaseUnit exceeds available treasury");
        }

        nation.spendTreasury(totalCost);
        gameState.addPendingPurchases(actingNationId, unitKind, unitCount);
        result.detailLines.push_back(
            "purchase: "
            + std::to_string(unitCount)
            + " " + std::string(toString(unitKind))
            + " for " + std::to_string(totalCost)
            + " treasury");
    }

    void applyCombatMove(GameState& gameState, const Action& action, StepResult& result) const {
        if (gameState.currentPhase() != Phase::CombatMove) {
            throw std::runtime_error("MoveCombatUnit can only be used in combat_move");
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
        if (hasPendingAttackersForZone(gameState, actingNationId, targetZoneId)) {
            throw std::runtime_error("Combat move target already has pending infantry assigned to it");
        }

        std::vector<Unit*> attackingUnits;
        for (auto* unit : gameState.unitsInZone(sourceZoneId)) {
            if (unit->ownerId() != actingNationId
                || !isCombatMovableInfantry(*unit)
                || unit->movementLeft() <= 0
                || unit->hasPendingCombatTarget()) {
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

        result.detailLines.push_back(
            "combat move: "
            + std::to_string(attackingUnits.size())
            + " infantry committed from "
            + sourceZoneId
            + " to pending battle at "
            + targetZoneId);
        for (auto* unit : attackingUnits) {
            unit->setPendingCombatTargetZoneId(targetZoneId);
        }
    }

    void applyResolveCombat(GameState& gameState, const Action& action, StepResult& result) const {
        if (gameState.currentPhase() != Phase::CombatResolve) {
            throw std::runtime_error("ResolveCombat can only be used in combat_resolve");
        }
        if (!action.targetZoneId.has_value()) {
            throw std::runtime_error("ResolveCombat requires a target zone");
        }

        const auto actingNationId = gameState.currentNation();
        const auto& targetZoneId = *action.targetZoneId;

        std::vector<Unit*> attackingUnits;
        for (auto& unitPtr : gameState.units()) {
            auto* unit = unitPtr.get();
            if (unit->ownerId() != actingNationId || !unit->hasPendingCombatTarget()) {
                continue;
            }
            if (*unit->pendingCombatTargetZoneId() == targetZoneId) {
                attackingUnits.push_back(unit);
            }
        }
        if (attackingUnits.empty()) {
            throw std::runtime_error("ResolveCombat requires pending attackers in the target zone");
        }

        std::vector<const Unit*> defendingUnits;
        for (auto* unit : gameState.unitsInZone(targetZoneId)) {
            if (unit->ownerId() != actingNationId && isLandCombatUnit(*unit)) {
                defendingUnits.push_back(unit);
            }
        }
        if (defendingUnits.empty()) {
            throw std::runtime_error("ResolveCombat requires defenders in the target zone");
        }

        result.detailLines.push_back(
            "resolving pending battle at "
            + targetZoneId
            + ": attackers=" + std::to_string(attackingUnits.size())
            + ", defenders=" + std::to_string(defendingUnits.size()));

        const auto outcome = resolveLandCombat(
            gameState.zone(targetZoneId),
            std::vector<const Unit*>(attackingUnits.begin(), attackingUnits.end()),
            defendingUnits);
        result.detailLines.insert(
            result.detailLines.end(),
            outcome.roundLogs.begin(),
            outcome.roundLogs.end());

        std::vector<Unit*> survivingAttackers;
        survivingAttackers.reserve(attackingUnits.size());
        for (auto* unit : attackingUnits) {
            if (std::find(outcome.destroyedAttackers.begin(), outcome.destroyedAttackers.end(), unit)
                == outcome.destroyedAttackers.end()) {
                survivingAttackers.push_back(unit);
            }
        }

        if (outcome.attackersWon) {
            result.detailLines.push_back("combat result: attackers won and occupy the territory");
            for (auto* unit : survivingAttackers) {
                unit->clearPendingCombatTargetZoneId();
                gameState.moveUnit(unit, targetZoneId, 0);
            }
            gameState.removeUnits(outcome.destroyedDefenders);
            gameState.removeUnits(outcome.destroyedAttackers);
            gameState.setZoneController(targetZoneId, std::string(actingNationId));
        } else {
            result.detailLines.push_back("combat result: defenders held, surviving attackers stay in origin");
            for (auto* unit : survivingAttackers) {
                unit->clearPendingCombatTargetZoneId();
            }
            gameState.removeUnits(outcome.destroyedDefenders);
            gameState.removeUnits(outcome.destroyedAttackers);
        }
    }

    void applyPlaceUnit(GameState& gameState, const Action& action, StepResult& result) const {
        if (gameState.currentPhase() != Phase::PlaceUnits) {
            throw std::runtime_error("PlaceUnit can only be used in place_units");
        }
        if (!action.targetZoneId.has_value() || !action.unitKind.has_value() || !action.unitCount.has_value()) {
            throw std::runtime_error("PlaceUnit requires a target zone, unit kind, and count");
        }

        const auto actingNationId = gameState.currentNation();
        const auto& targetZoneId = *action.targetZoneId;
        const auto unitKind = *action.unitKind;
        const auto unitCount = *action.unitCount;
        if (unitCount <= 0) {
            throw std::runtime_error("PlaceUnit requires a positive unit count");
        }

        gameState.placePurchasedUnits(actingNationId, targetZoneId, unitKind, unitCount);
        result.detailLines.push_back(
            "place units: "
            + std::to_string(unitCount)
            + " " + std::string(toString(unitKind))
            + " placed at " + targetZoneId);
    }
};

}  // namespace game
