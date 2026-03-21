#pragma once

#include "game/action.hpp"
#include "game/game_state.hpp"

#include <algorithm>
#include <cmath>
#include <optional>
#include <sstream>
#include <stdexcept>
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

    static std::vector<UnitKind> combatMovableUnitKinds() {
        return {UnitKind::Infantry, UnitKind::Artillery, UnitKind::Marine};
    }

    struct ForceState {
        double infantry {0.0};
        double artillery {0.0};
        double marine {0.0};
    };

    struct CombatOutcome {
        bool attackersWon {false};
        int survivingAttackerCount {0};
        int survivingDefenderCount {0};
        ForceState survivingAttackerForce {};
        ForceState survivingDefenderForce {};
        std::vector<std::string> roundLogs;
    };

    static bool isLandCombatUnit(const Unit& unit) {
        return unit.kind() == UnitKind::Infantry
            || unit.kind() == UnitKind::Artillery
            || unit.kind() == UnitKind::Marine;
    }

    static bool isCombatMovableLandUnit(const Unit& unit) {
        return unit.kind() == UnitKind::Infantry
            || unit.kind() == UnitKind::Artillery
            || unit.kind() == UnitKind::Marine;
    }

    static int baseAttackValue(UnitKind kind) {
        switch (kind) {
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

    static int baseAttackValue(const Unit& unit) {
        return baseAttackValue(unit.kind());
    }

    static int baseDefenseValue(UnitKind kind) {
        switch (kind) {
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

    static int baseDefenseValue(const Unit& unit) {
        return baseDefenseValue(unit.kind());
    }

    static int adjustedAttackValue(UnitKind kind, const Zone& battleZone) {
        auto value = baseAttackValue(kind);
        if (battleZone.terrain == "mountain") {
            value -= 1;
        }
        return std::max(0, value);
    }

    static int adjustedAttackValue(const Unit& unit, const Zone& battleZone) {
        return adjustedAttackValue(unit.kind(), battleZone);
    }

    static int adjustedDefenseValue(UnitKind kind, const Zone& battleZone) {
        auto value = baseDefenseValue(kind);
        if (battleZone.isCity) {
            value += 1;
        }
        return std::max(0, value);
    }

    static int adjustedDefenseValue(const Unit& unit, const Zone& battleZone) {
        return adjustedDefenseValue(unit.kind(), battleZone);
    }

    static ForceState buildForceState(const std::vector<const Unit*>& units) {
        ForceState force;
        for (const auto* unit : units) {
            switch (unit->kind()) {
                case UnitKind::Infantry:
                    force.infantry += 1.0;
                    break;
                case UnitKind::Artillery:
                    force.artillery += 1.0;
                    break;
                case UnitKind::Marine:
                    force.marine += 1.0;
                    break;
                case UnitKind::Fighter:
                case UnitKind::Transport:
                    break;
            }
        }
        return force;
    }

    static double totalUnits(const ForceState& force) {
        return force.infantry + force.artillery + force.marine;
    }

    static std::string formatCount(double value) {
        if (std::abs(value - std::round(value)) < 1e-9) {
            return std::to_string(static_cast<int>(std::round(value)));
        }
        std::ostringstream stream;
        stream.setf(std::ios::fixed);
        stream.precision(2);
        stream << value;
        return stream.str();
    }

    static std::string describeForce(const ForceState& force) {
        std::vector<std::string> parts;
        if (force.infantry > 0.0) {
            parts.push_back(formatCount(force.infantry) + " Inf");
        }
        if (force.artillery > 0.0) {
            parts.push_back(formatCount(force.artillery) + " Art");
        }
        if (force.marine > 0.0) {
            parts.push_back(formatCount(force.marine) + " Mar");
        }
        if (parts.empty()) {
            return "0";
        }
        std::ostringstream stream;
        for (std::size_t index = 0; index < parts.size(); ++index) {
            if (index > 0) {
                stream << " + ";
            }
            stream << parts[index];
        }
        return stream.str();
    }

    static double forceCountForKind(const ForceState& force, UnitKind kind) {
        switch (kind) {
            case UnitKind::Infantry:
                return force.infantry;
            case UnitKind::Artillery:
                return force.artillery;
            case UnitKind::Marine:
                return force.marine;
            case UnitKind::Fighter:
            case UnitKind::Transport:
                return 0.0;
        }
        throw std::runtime_error("Unknown unit kind in forceCountForKind");
    }

    static std::vector<UnitKind> casualtyPriorityOrder(const Zone& battleZone, bool attackers) {
        std::vector<UnitKind> order{UnitKind::Infantry, UnitKind::Artillery, UnitKind::Marine};
        std::stable_sort(
            order.begin(),
            order.end(),
            [&](UnitKind lhs, UnitKind rhs) {
                const auto lhsValue = attackers ? adjustedAttackValue(lhs, battleZone)
                                                : adjustedDefenseValue(lhs, battleZone);
                const auto rhsValue = attackers ? adjustedAttackValue(rhs, battleZone)
                                                : adjustedDefenseValue(rhs, battleZone);
                return lhsValue < rhsValue;
            });
        return order;
    }

    static void applyFractionalCasualties(
        ForceState& force,
        const Zone& battleZone,
        bool attackers,
        double casualties) {
        if (casualties <= 0.0 || totalUnits(force) <= 0.0) {
            return;
        }

        auto removeFromKind = [&](UnitKind kind, double amount) {
            switch (kind) {
                case UnitKind::Infantry: {
                    const auto removed = std::min(force.infantry, amount);
                    force.infantry -= removed;
                    return removed;
                }
                case UnitKind::Artillery: {
                    const auto removed = std::min(force.artillery, amount);
                    force.artillery -= removed;
                    return removed;
                }
                case UnitKind::Marine: {
                    const auto removed = std::min(force.marine, amount);
                    force.marine -= removed;
                    return removed;
                }
                case UnitKind::Fighter:
                case UnitKind::Transport:
                    return 0.0;
            }
            return 0.0;
        };

        auto remaining = casualties;
        for (const auto kind : casualtyPriorityOrder(battleZone, attackers)) {
            if (remaining <= 1e-9) {
                break;
            }
            remaining -= removeFromKind(kind, remaining);
        }
    }

    static double artillerySupportBonus(const ForceState& force) {
        return std::min(force.infantry + force.marine, force.artillery);
    }

    static double regularAttackValue(const ForceState& force, const Zone& battleZone, bool includeArtillery) {
        double total = 0.0;
        total += force.infantry * adjustedAttackValue(UnitKind::Infantry, battleZone);
        total += force.marine * adjustedAttackValue(UnitKind::Marine, battleZone);
        if (includeArtillery) {
            total += force.artillery * adjustedAttackValue(UnitKind::Artillery, battleZone);
        }
        total += artillerySupportBonus(force);
        return total;
    }

    static double regularDefenseValue(const ForceState& force, const Zone& battleZone, bool includeArtillery) {
        double total = 0.0;
        total += force.infantry * adjustedDefenseValue(UnitKind::Infantry, battleZone);
        total += force.marine * adjustedDefenseValue(UnitKind::Marine, battleZone);
        if (includeArtillery) {
            total += force.artillery * adjustedDefenseValue(UnitKind::Artillery, battleZone);
        }
        total += artillerySupportBonus(force);
        return total;
    }

    static int roundedSurvivorCount(double survivingUnits, int initialUnits) {
        if (survivingUnits <= 1e-9) {
            return 0;
        }
        return std::min(initialUnits, std::max(1, static_cast<int>(std::round(survivingUnits))));
    }

    static std::unordered_map<UnitKind, int> roundedSurvivorDistribution(
        const ForceState& force,
        const Zone& battleZone,
        bool attackers,
        int roundedTotalSurvivors) {
        std::unordered_map<UnitKind, int> survivorsByKind;
        if (roundedTotalSurvivors <= 0) {
            return survivorsByKind;
        }

        struct FractionalKindState {
            UnitKind kind;
            int baseCount;
            double remainder;
            int priorityValue;
        };

        std::vector<FractionalKindState> kindStates;
        int assignedSurvivors = 0;
        for (const auto kind : {UnitKind::Infantry, UnitKind::Artillery, UnitKind::Marine}) {
            const auto survivingCount = forceCountForKind(force, kind);
            if (survivingCount <= 1e-9) {
                continue;
            }

            const auto baseCount = static_cast<int>(std::floor(survivingCount + 1e-9));
            if (baseCount > 0) {
                survivorsByKind[kind] = baseCount;
                assignedSurvivors += baseCount;
            }

            const auto priorityValue = attackers ? adjustedAttackValue(kind, battleZone)
                                                 : adjustedDefenseValue(kind, battleZone);
            kindStates.push_back(FractionalKindState{
                .kind = kind,
                .baseCount = baseCount,
                .remainder = survivingCount - static_cast<double>(baseCount),
                .priorityValue = priorityValue,
            });
        }

        auto remainingSurvivors = std::max(0, roundedTotalSurvivors - assignedSurvivors);
        std::stable_sort(
            kindStates.begin(),
            kindStates.end(),
            [](const FractionalKindState& lhs, const FractionalKindState& rhs) {
                if (std::abs(lhs.remainder - rhs.remainder) > 1e-9) {
                    return lhs.remainder > rhs.remainder;
                }
                return lhs.priorityValue > rhs.priorityValue;
            });

        for (auto& kindState : kindStates) {
            if (remainingSurvivors <= 0) {
                break;
            }
            const auto rawAvailable = forceCountForKind(force, kindState.kind);
            const auto maxAvailable = static_cast<int>(std::ceil(rawAvailable - 1e-9));
            if (maxAvailable <= survivorsByKind[kindState.kind]) {
                continue;
            }
            ++survivorsByKind[kindState.kind];
            --remainingSurvivors;
        }

        return survivorsByKind;
    }

    static std::vector<const Unit*> destroyedUnitsFromRoundedSurvivors(
        const std::vector<const Unit*>& units,
        const Zone& battleZone,
        bool attackers,
        const ForceState& survivingForce,
        int roundedTotalSurvivors) {
        const auto survivorsByKind =
            roundedSurvivorDistribution(survivingForce, battleZone, attackers, roundedTotalSurvivors);

        std::unordered_map<UnitKind, int> keptByKind;
        std::vector<const Unit*> destroyedUnits;
        destroyedUnits.reserve(units.size());

        for (const auto* unit : units) {
            const auto allowedSurvivors = [&]() {
                const auto it = survivorsByKind.find(unit->kind());
                return it != survivorsByKind.end() ? it->second : 0;
            }();
            if (keptByKind[unit->kind()] < allowedSurvivors) {
                ++keptByKind[unit->kind()];
                continue;
            }
            destroyedUnits.push_back(unit);
        }

        return destroyedUnits;
    }

    CombatOutcome resolveLandCombat(
        const Zone& battleZone,
        std::vector<const Unit*> attackingUnits,
        std::vector<const Unit*> defendingUnits) const {
        CombatOutcome outcome;
        const auto initialAttackerCount = static_cast<int>(attackingUnits.size());
        const auto initialDefenderCount = static_cast<int>(defendingUnits.size());

        auto attackingForce = buildForceState(attackingUnits);
        auto defendingForce = buildForceState(defendingUnits);
        int roundNumber = 1;

        while (totalUnits(attackingForce) > 1e-9 && totalUnits(defendingForce) > 1e-9) {
            if (roundNumber == 1 && (attackingForce.artillery > 0.0 || defendingForce.artillery > 0.0)) {
                const auto artilleryAttackValue =
                    attackingForce.artillery * adjustedAttackValue(UnitKind::Artillery, battleZone);
                const auto artilleryDefenseValue =
                    defendingForce.artillery * adjustedDefenseValue(UnitKind::Artillery, battleZone);
                const auto artilleryDefenderLosses = artilleryAttackValue / 12.0;
                const auto artilleryAttackerLosses = artilleryDefenseValue / 12.0;

                outcome.roundLogs.push_back(
                    "first strike: attacker "
                    + formatCount(attackingForce.artillery)
                    + " Art ("
                    + formatCount(artilleryAttackValue)
                    + "/12="
                    + formatCount(artilleryDefenderLosses)
                    + "), defender "
                    + formatCount(defendingForce.artillery)
                    + " Art ("
                    + formatCount(artilleryDefenseValue)
                    + "/12="
                    + formatCount(artilleryAttackerLosses)
                    + ")");

                auto attackerAfterStrike = attackingForce;
                auto defenderAfterStrike = defendingForce;
                applyFractionalCasualties(attackerAfterStrike, battleZone, true, artilleryAttackerLosses);
                applyFractionalCasualties(defenderAfterStrike, battleZone, false, artilleryDefenderLosses);
                attackingForce = attackerAfterStrike;
                defendingForce = defenderAfterStrike;

                outcome.roundLogs.push_back(
                    "  after first strike: attacker "
                    + describeForce(attackingForce)
                    + ", defender "
                    + describeForce(defendingForce)
                    + ", losses attacker=" + formatCount(artilleryAttackerLosses)
                    + ", defender=" + formatCount(artilleryDefenderLosses));
            }

            const auto includeArtillery = roundNumber > 1;
            const auto roundAttack = regularAttackValue(attackingForce, battleZone, includeArtillery);
            const auto roundDefense = regularDefenseValue(defendingForce, battleZone, includeArtillery);

            if (roundAttack <= 1e-9 && roundDefense <= 1e-9) {
                break;
            }

            outcome.roundLogs.push_back(
                "round "
                + std::to_string(roundNumber)
                + ": attacker "
                + describeForce(attackingForce)
                + " ("
                + formatCount(roundAttack)
                + "/12="
                + formatCount(roundAttack / 12.0)
                + "), defender "
                + describeForce(defendingForce)
                + " ("
                + formatCount(roundDefense)
                + "/12="
                + formatCount(roundDefense / 12.0)
                + ")");

            const auto defenderLosses = roundAttack / 12.0;
            const auto attackerLosses = roundDefense / 12.0;

            auto attackerAfterRound = attackingForce;
            auto defenderAfterRound = defendingForce;
            applyFractionalCasualties(attackerAfterRound, battleZone, true, attackerLosses);
            applyFractionalCasualties(defenderAfterRound, battleZone, false, defenderLosses);
            attackingForce = attackerAfterRound;
            defendingForce = defenderAfterRound;

            outcome.roundLogs.push_back(
                "  after casualties: attacker "
                + describeForce(attackingForce)
                + ", defender "
                + describeForce(defendingForce)
                + ", losses attacker=" + formatCount(attackerLosses)
                + ", defender=" + formatCount(defenderLosses));

            ++roundNumber;
        }

        outcome.survivingAttackerForce = attackingForce;
        outcome.survivingDefenderForce = defendingForce;
        outcome.survivingAttackerCount = roundedSurvivorCount(totalUnits(attackingForce), initialAttackerCount);
        outcome.survivingDefenderCount = roundedSurvivorCount(totalUnits(defendingForce), initialDefenderCount);
        outcome.attackersWon = outcome.survivingAttackerCount > 0 && outcome.survivingDefenderCount == 0;
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

    static bool hasPendingAttackersForZoneAndKind(
        const GameState& gameState,
        std::string_view nationId,
        std::string_view targetZoneId,
        UnitKind unitKind) {
        for (const auto* unit : pendingAttackersForZone(gameState, nationId, targetZoneId)) {
            if (unit->kind() == unitKind) {
                return true;
            }
        }
        return false;
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
        std::unordered_map<std::string, std::unordered_map<UnitKind, int>> availableUnitsByZoneAndKind;

        for (const auto& unitPtr : gameState.units()) {
            const auto& unit = *unitPtr;
            if (unit.ownerId() != actingNationId
                || !isCombatMovableLandUnit(unit)
                || unit.movementLeft() <= 0
                || unit.hasPendingCombatTarget()) {
                continue;
            }

            const auto& originZone = gameState.zone(unit.zoneId());
            if (originZone.kind != ZoneKind::Land) {
                continue;
            }

            if (availableUnitsByZoneAndKind.find(originZone.id) == availableUnitsByZoneAndKind.end()) {
                sourceZoneOrder.push_back(originZone.id);
            }
            ++availableUnitsByZoneAndKind[originZone.id][unit.kind()];
        }

        std::sort(sourceZoneOrder.begin(), sourceZoneOrder.end());
        sourceZoneOrder.erase(std::unique(sourceZoneOrder.begin(), sourceZoneOrder.end()), sourceZoneOrder.end());

        for (const auto& originZoneId : sourceZoneOrder) {
            const auto& originZone = gameState.zone(originZoneId);
            const auto& availableByKind = availableUnitsByZoneAndKind.at(originZoneId);
            for (const auto unitKind : combatMovableUnitKinds()) {
                const auto availableIt = availableByKind.find(unitKind);
                if (availableIt == availableByKind.end()) {
                    continue;
                }
                const auto availableCount = availableIt->second;
                for (const auto& neighbor : originZone.neighbors) {
                    if (!gameState.hasZone(neighbor.id)) {
                        continue;
                    }
                    const auto& destinationZone = gameState.zone(neighbor.id);
                    if (!isEnemyControlledLandZone(gameState, actingNationId, destinationZone)) {
                        continue;
                    }
                    if (hasPendingAttackersForZoneAndKind(gameState, actingNationId, destinationZone.id, unitKind)) {
                        continue;
                    }
                    for (int unitCount = 1; unitCount <= availableCount; ++unitCount) {
                        actions.push_back(Action{
                            .kind = ActionKind::MoveCombatUnit,
                            .sourceZoneId = originZone.id,
                            .targetZoneId = destinationZone.id,
                            .unitCount = unitCount,
                            .unitKind = unitKind,
                        });
                    }
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
        if (!action.unitKind.has_value()) {
            throw std::runtime_error("MoveCombatUnit requires a unit kind");
        }
        const auto unitKind = *action.unitKind;
        const auto unitCount = *action.unitCount;
        if (unitCount <= 0) {
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
        if (hasPendingAttackersForZoneAndKind(gameState, actingNationId, targetZoneId, unitKind)) {
            throw std::runtime_error("Combat move target already has pending attackers of this unit type assigned to it");
        }

        std::vector<Unit*> attackingUnits;
        for (auto* unit : gameState.unitsInZone(sourceZoneId)) {
            if (unit->ownerId() != actingNationId
                || unit->kind() != unitKind
                || !isCombatMovableLandUnit(*unit)
                || unit->movementLeft() <= 0
                || unit->hasPendingCombatTarget()) {
                continue;
            }
            attackingUnits.push_back(unit);
        }
        if (static_cast<int>(attackingUnits.size()) < unitCount) {
            throw std::runtime_error("Combat move requested more units than are available in the source zone");
        }
        attackingUnits.resize(static_cast<std::size_t>(unitCount));
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
            + " " + std::string(toString(unitKind))
            + " committed from "
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

        const auto destroyedAttackers = destroyedUnitsFromRoundedSurvivors(
            std::vector<const Unit*>(attackingUnits.begin(), attackingUnits.end()),
            gameState.zone(targetZoneId),
            true,
            outcome.survivingAttackerForce,
            outcome.survivingAttackerCount);
        const auto destroyedDefenders = destroyedUnitsFromRoundedSurvivors(
            defendingUnits,
            gameState.zone(targetZoneId),
            false,
            outcome.survivingDefenderForce,
            outcome.survivingDefenderCount);

        std::vector<Unit*> survivingAttackers;
        survivingAttackers.reserve(attackingUnits.size());
        for (auto* unit : attackingUnits) {
            if (std::find(destroyedAttackers.begin(), destroyedAttackers.end(), unit) == destroyedAttackers.end()) {
                survivingAttackers.push_back(unit);
            }
        }

        if (outcome.attackersWon) {
            result.detailLines.push_back("combat result: attackers won and occupy the territory");
            for (auto* unit : survivingAttackers) {
                unit->clearPendingCombatTargetZoneId();
                gameState.moveUnit(unit, targetZoneId, 0);
            }
            gameState.recordEnemyUnitValueDestroyedByNation(actingNationId, destroyedDefenders);
            gameState.removeUnits(destroyedDefenders);
            gameState.removeUnits(destroyedAttackers);
            gameState.setZoneController(targetZoneId, std::string(actingNationId));
        } else {
            if (outcome.survivingDefenderCount == 0) {
                result.detailLines.push_back(
                    "combat result: both forces were destroyed, territory remains under defender control");
            } else {
                result.detailLines.push_back("combat result: defenders held, surviving attackers stay in origin");
            }
            for (auto* unit : survivingAttackers) {
                unit->clearPendingCombatTargetZoneId();
            }
            gameState.recordEnemyUnitValueDestroyedByNation(actingNationId, destroyedDefenders);
            gameState.removeUnits(destroyedDefenders);
            gameState.removeUnits(destroyedAttackers);
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
