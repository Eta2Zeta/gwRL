#pragma once

#include "game/types.hpp"
#include "game/unit.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace game {

class BattleResolver {
  public:
    struct ForceState {
        std::array<double, unitKindCount()> counts {};

        double& operator[](UnitKind kind) { return counts.at(unitKindIndex(kind)); }
        double operator[](UnitKind kind) const { return counts.at(unitKindIndex(kind)); }
    };

    struct CombatOutcome {
        bool attackersWon {false};
        bool defendersWon {false};
        bool draw {false};
        int survivingAttackerCount {0};
        int survivingDefenderCount {0};
        ForceState survivingAttackerForce {};
        ForceState survivingDefenderForce {};
        std::vector<std::string> roundLogs;
    };

    static const std::vector<UnitKind>& compositionPurchasableUnitKinds() {
        static const std::vector<UnitKind> kinds{
            UnitKind::Infantry,
            UnitKind::Artillery,
            UnitKind::LightTank,
            UnitKind::MechanizedInfantry,
            UnitKind::MediumTank,
            UnitKind::TankDestroyer,
        };
        return kinds;
    }

    static const std::vector<UnitKind>& landCombatUnitKinds() {
        static const std::vector<UnitKind> kinds{
            UnitKind::Infantry,
            UnitKind::Artillery,
            UnitKind::Marine,
            UnitKind::LightTank,
            UnitKind::MechanizedInfantry,
            UnitKind::MediumTank,
            UnitKind::TankDestroyer,
        };
        return kinds;
    }

    static bool isLandCombatUnit(UnitKind kind) {
        return std::find(landCombatUnitKinds().begin(), landCombatUnitKinds().end(), kind)
            != landCombatUnitKinds().end();
    }

    static bool isLandCombatUnit(const Unit& unit) {
        return isLandCombatUnit(unit.kind());
    }

    static bool isCombatMovableLandUnit(UnitKind kind) {
        return isLandCombatUnit(kind);
    }

    static bool isCombatMovableLandUnit(const Unit& unit) {
        return isCombatMovableLandUnit(unit.kind());
    }

    static int baseAttackValue(UnitKind kind) {
        switch (kind) {
            case UnitKind::Infantry:
                return 2;
            case UnitKind::Artillery:
                return 3;
            case UnitKind::Marine:
                return 2;
            case UnitKind::LightTank:
                return 3;
            case UnitKind::MechanizedInfantry:
                return 3;
            case UnitKind::MediumTank:
                return 6;
            case UnitKind::TankDestroyer:
                return 3;
            case UnitKind::Fighter:
            case UnitKind::Transport:
                return 0;
        }
        throw std::runtime_error("Unknown unit kind for attack value");
    }

    static int baseDefenseValue(UnitKind kind) {
        switch (kind) {
            case UnitKind::Infantry:
                return 4;
            case UnitKind::Artillery:
                return 3;
            case UnitKind::Marine:
                return 4;
            case UnitKind::LightTank:
                return 1;
            case UnitKind::MechanizedInfantry:
                return 4;
            case UnitKind::MediumTank:
                return 5;
            case UnitKind::TankDestroyer:
                return 4;
            case UnitKind::Fighter:
            case UnitKind::Transport:
                return 0;
        }
        throw std::runtime_error("Unknown unit kind for defense value");
    }

    static int targetSelectionValue(UnitKind kind) {
        switch (kind) {
            case UnitKind::TankDestroyer:
                return 3;
            default:
                return 0;
        }
    }

    static int adjustedAttackValue(UnitKind kind, const Zone& battleZone) {
        auto value = baseAttackValue(kind);
        if (battleZone.terrain == "mountain") {
            value -= 1;
        }
        return std::max(0, value);
    }

    static int adjustedDefenseValue(UnitKind kind, const Zone& battleZone) {
        auto value = baseDefenseValue(kind);
        if (battleZone.isCity) {
            value += 1;
        }
        return std::max(0, value);
    }

    static ForceState buildForceState(const std::vector<const Unit*>& units) {
        ForceState force;
        for (const auto* unit : units) {
            if (!unit || !isLandCombatUnit(*unit)) {
                continue;
            }
            force[unit->kind()] += 1.0;
        }
        return force;
    }

    static double totalUnits(const ForceState& force) {
        double total = 0.0;
        for (const auto kind : landCombatUnitKinds()) {
            total += force[kind];
        }
        return total;
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
        for (const auto kind : landCombatUnitKinds()) {
            const auto count = force[kind];
            if (count <= 1e-9) {
                continue;
            }
            parts.push_back(formatCount(count) + " " + std::string(kindAbbreviation(kind)));
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

    static std::vector<const Unit*> destroyedUnitsFromRoundedSurvivors(
        const std::vector<const Unit*>& units,
        const Zone& battleZone,
        bool attackers,
        const ForceState& survivingForce,
        int roundedTotalSurvivors) {
        const auto survivorsByKind =
            roundedSurvivorDistribution(survivingForce, battleZone, attackers, roundedTotalSurvivors);

        std::array<int, unitKindCount()> keptByKind {};
        std::vector<const Unit*> destroyedUnits;
        destroyedUnits.reserve(units.size());

        for (const auto* unit : units) {
            if (unit == nullptr) {
                continue;
            }
            const auto kindIndex = unitKindIndex(unit->kind());
            const auto allowedSurvivors = survivorsByKind.at(kindIndex);
            if (keptByKind.at(kindIndex) < allowedSurvivors) {
                ++keptByKind.at(kindIndex);
                continue;
            }
            destroyedUnits.push_back(unit);
        }

        return destroyedUnits;
    }

    static CombatOutcome resolveLandCombat(
        const Zone& battleZone,
        const std::vector<const Unit*>& attackingUnits,
        const std::vector<const Unit*>& defendingUnits) {
        CombatOutcome outcome;
        const auto initialAttackerCount = static_cast<int>(attackingUnits.size());
        const auto initialDefenderCount = static_cast<int>(defendingUnits.size());

        auto attackingForce = buildForceState(attackingUnits);
        auto defendingForce = buildForceState(defendingUnits);
        int roundNumber = 1;

        while (totalUnits(attackingForce) > 1e-9 && totalUnits(defendingForce) > 1e-9) {
            if (roundNumber == 1 && (attackingForce[UnitKind::Artillery] > 0.0 || defendingForce[UnitKind::Artillery] > 0.0)) {
                const auto artilleryAttackValue =
                    artilleryCombatValue(attackingForce, battleZone, true);
                const auto artilleryDefenseValue =
                    artilleryCombatValue(defendingForce, battleZone, false);
                const auto artilleryDefenderLosses = artilleryAttackValue / 12.0;
                const auto artilleryAttackerLosses = artilleryDefenseValue / 12.0;

                outcome.roundLogs.push_back(
                    "first strike: attacker "
                    + formatCount(attackingForce[UnitKind::Artillery])
                    + " Art ("
                    + formatCount(artilleryAttackValue)
                    + "/12="
                    + formatCount(artilleryDefenderLosses)
                    + "), defender "
                    + formatCount(defendingForce[UnitKind::Artillery])
                    + " Art ("
                    + formatCount(artilleryDefenseValue)
                    + "/12="
                    + formatCount(artilleryAttackerLosses)
                    + ")");

                auto attackerAfterStrike = attackingForce;
                auto defenderAfterStrike = defendingForce;
                applyStandardCasualties(attackerAfterStrike, battleZone, true, artilleryAttackerLosses);
                applyStandardCasualties(defenderAfterStrike, battleZone, false, artilleryDefenderLosses);
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

            if (totalUnits(attackingForce) <= 1e-9 || totalUnits(defendingForce) <= 1e-9) {
                break;
            }

            // Target selection chooses casualties; unlike artillery first strike,
            // it does not suppress return fire. Compute all fire before any losses.
            const auto targetedAttack = targetedCombatValue(attackingForce, battleZone, true);
            const auto targetedDefense = targetedCombatValue(defendingForce, battleZone, false);
            const auto includeArtillery = roundNumber > 1;
            const auto regularAttack = regularCombatValue(attackingForce, battleZone, true, includeArtillery);
            const auto regularDefense = regularCombatValue(defendingForce, battleZone, false, includeArtillery);
            const auto roundAttack = targetedAttack + regularAttack;
            const auto roundDefense = targetedDefense + regularDefense;

            if (roundAttack <= 1e-9 && roundDefense <= 1e-9) {
                // Artillery already fired this round, but can fire normally next
                // round. Two surviving artillery forces are not a stalemate.
                if (!includeArtillery) {
                    ++roundNumber;
                    continue;
                }
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

            if (targetedAttack > 1e-9 || targetedDefense > 1e-9) {
                outcome.roundLogs.push_back(
                    "  target selection (included in round fire): attacker="
                    + formatCount(targetedAttack)
                    + "/12=" + formatCount(targetedAttack / 12.0)
                    + ", defender=" + formatCount(targetedDefense)
                    + "/12=" + formatCount(targetedDefense / 12.0));
            }

            const auto defenderLosses = roundAttack / 12.0;
            const auto attackerLosses = roundDefense / 12.0;

            auto attackerAfterRound = attackingForce;
            auto defenderAfterRound = defendingForce;
            applyTargetedCasualties(attackerAfterRound, battleZone, true, targetedDefense / 12.0);
            applyTargetedCasualties(defenderAfterRound, battleZone, false, targetedAttack / 12.0);
            applyStandardCasualties(attackerAfterRound, battleZone, true, regularDefense / 12.0);
            applyStandardCasualties(defenderAfterRound, battleZone, false, regularAttack / 12.0);
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
        outcome.defendersWon = outcome.survivingDefenderCount > 0 && outcome.survivingAttackerCount == 0;
        outcome.draw = !outcome.attackersWon && !outcome.defendersWon;
        return outcome;
    }

  private:
    static std::string_view kindAbbreviation(UnitKind kind) {
        switch (kind) {
            case UnitKind::Infantry:
                return "Inf";
            case UnitKind::Artillery:
                return "Art";
            case UnitKind::Marine:
                return "Mar";
            case UnitKind::LightTank:
                return "LT";
            case UnitKind::MechanizedInfantry:
                return "Mech";
            case UnitKind::MediumTank:
                return "MT";
            case UnitKind::TankDestroyer:
                return "TD";
            case UnitKind::Fighter:
                return "Fig";
            case UnitKind::Transport:
                return "Trn";
        }
        throw std::runtime_error("Unknown unit kind for abbreviation");
    }

    static bool isInfantryClass(UnitKind kind) {
        return kind == UnitKind::Infantry || kind == UnitKind::Marine;
    }

    static bool isVehicleClass(UnitKind kind) {
        return kind == UnitKind::LightTank || kind == UnitKind::MechanizedInfantry
            || kind == UnitKind::MediumTank || kind == UnitKind::TankDestroyer;
    }

    static double artilleryCombatValue(const ForceState& force, const Zone& battleZone, bool attackers) {
        double partners = 0.0;
        for (const auto kind : landCombatUnitKinds()) {
            if (isInfantryClass(kind) || isVehicleClass(kind)) {
                partners += force[kind];
            }
        }
        // Both classes prevent the unpaired-artillery penalty. Recompute from
        // the surviving force for first strike and each later round.
        const auto paired = std::min(force[UnitKind::Artillery], partners);
        const auto unpaired = force[UnitKind::Artillery] - paired;
        const auto value = attackers ? adjustedAttackValue(UnitKind::Artillery, battleZone)
                                    : adjustedDefenseValue(UnitKind::Artillery, battleZone);
        return paired * value + unpaired * std::max(0, value - 1);
    }

    static double artillerySupportBonus(const ForceState& force) {
        double total = 0.0;
        for (const auto kind : landCombatUnitKinds()) {
            if (isInfantryClass(kind)) {
                total += force[kind];
            }
        }
        // Pair infantry first for the attack bonus; remaining artillery may
        // pair with vehicles, which receive no support bonus themselves.
        return std::min(total, force[UnitKind::Artillery]);
    }

    static std::vector<UnitKind> standardCasualtyPriorityOrder(const Zone& battleZone, bool attackers) {
        auto order = landCombatUnitKinds();
        std::stable_sort(
            order.begin(),
            order.end(),
            [&](UnitKind lhs, UnitKind rhs) {
                const auto lhsValue = attackers ? adjustedAttackValue(lhs, battleZone)
                                                : adjustedDefenseValue(lhs, battleZone);
                const auto rhsValue = attackers ? adjustedAttackValue(rhs, battleZone)
                                                : adjustedDefenseValue(rhs, battleZone);
                if (lhsValue != rhsValue) {
                    return lhsValue < rhsValue;
                }
                return rewardValue(lhs) < rewardValue(rhs);
            });
        return order;
    }

    static std::vector<UnitKind> targetedCasualtyPriorityOrder(const Zone& battleZone, bool attackers) {
        auto order = landCombatUnitKinds();
        order.erase(
            std::remove_if(order.begin(), order.end(), [](UnitKind kind) { return !isVehicleClass(kind); }),
            order.end());
        std::stable_sort(
            order.begin(),
            order.end(),
            [&](UnitKind lhs, UnitKind rhs) {
                const auto lhsValue = attackers ? adjustedAttackValue(lhs, battleZone)
                                                : adjustedDefenseValue(lhs, battleZone);
                const auto rhsValue = attackers ? adjustedAttackValue(rhs, battleZone)
                                                : adjustedDefenseValue(rhs, battleZone);
                if (lhsValue != rhsValue) {
                    return lhsValue > rhsValue;
                }
                return rewardValue(lhs) > rewardValue(rhs);
            });
        return order;
    }

    static double applyCasualtiesByOrder(
        ForceState& force,
        const std::vector<UnitKind>& casualtyOrder,
        double casualties) {
        if (casualties <= 0.0) {
            return 0.0;
        }
        auto remaining = casualties;
        for (const auto kind : casualtyOrder) {
            // Apply even tiny hits so symmetric fractional battles keep making
            // progress until the force-level termination threshold is reached.
            if (remaining <= 0.0) {
                break;
            }
            const auto removed = std::min(force[kind], remaining);
            force[kind] -= removed;
            remaining -= removed;
        }
        return remaining;
    }

    static void applyStandardCasualties(
        ForceState& force,
        const Zone& battleZone,
        bool attackers,
        double casualties) {
        if (casualties <= 0.0 || totalUnits(force) <= 0.0) {
            return;
        }
        applyCasualtiesByOrder(force, standardCasualtyPriorityOrder(battleZone, attackers), casualties);
    }

    static void applyTargetedCasualties(
        ForceState& force,
        const Zone& battleZone,
        bool attackers,
        double casualties) {
        if (casualties <= 0.0 || totalUnits(force) <= 0.0) {
            return;
        }
        const auto remaining =
            applyCasualtiesByOrder(force, targetedCasualtyPriorityOrder(battleZone, attackers), casualties);
        // Once eligible vehicles are exhausted, excess hits are ordinary
        // casualties chosen by the receiving side's existing heuristic.
        applyStandardCasualties(force, battleZone, attackers, remaining);
    }

    static double targetedCombatValueForKind(UnitKind kind, const Zone& battleZone, bool attackers) {
        const auto adjustedValue = attackers ? adjustedAttackValue(kind, battleZone)
                                             : adjustedDefenseValue(kind, battleZone);
        return static_cast<double>(std::min(adjustedValue, targetSelectionValue(kind)));
    }

    static double targetedCombatValue(const ForceState& force, const Zone& battleZone, bool attackers) {
        double total = 0.0;
        for (const auto kind : landCombatUnitKinds()) {
            total += force[kind] * targetedCombatValueForKind(kind, battleZone, attackers);
        }
        return total;
    }

    static double regularCombatValue(
        const ForceState& force,
        const Zone& battleZone,
        bool attackers,
        bool includeArtillery) {
        double total = 0.0;
        for (const auto kind : landCombatUnitKinds()) {
            if (kind == UnitKind::Artillery) {
                continue;
            }
            const auto value = attackers ? adjustedAttackValue(kind, battleZone)
                                        : adjustedDefenseValue(kind, battleZone);
            total += force[kind] * (value - targetedCombatValueForKind(kind, battleZone, attackers));
        }
        if (includeArtillery) {
            total += artilleryCombatValue(force, battleZone, attackers);
        }
        if (attackers) {
            total += artillerySupportBonus(force);
        }
        return total;
    }

    static int roundedSurvivorCount(double survivingUnits, int initialUnits) {
        if (survivingUnits <= 1e-9) {
            return 0;
        }
        return std::min(initialUnits, std::max(1, static_cast<int>(std::round(survivingUnits))));
    }

    static std::array<int, unitKindCount()> roundedSurvivorDistribution(
        const ForceState& force,
        const Zone& battleZone,
        bool attackers,
        int roundedTotalSurvivors) {
        std::array<int, unitKindCount()> survivorsByKind {};
        if (roundedTotalSurvivors <= 0) {
            return survivorsByKind;
        }

        struct FractionalKindState {
            UnitKind kind;
            int baseCount;
            double remainder;
            int priorityValue;
            int reward;
        };

        std::vector<FractionalKindState> kindStates;
        int assignedSurvivors = 0;
        for (const auto kind : landCombatUnitKinds()) {
            const auto survivingCount = force[kind];
            if (survivingCount <= 1e-9) {
                continue;
            }

            const auto baseCount = static_cast<int>(std::floor(survivingCount + 1e-9));
            if (baseCount > 0) {
                survivorsByKind.at(unitKindIndex(kind)) = baseCount;
                assignedSurvivors += baseCount;
            }

            const auto priorityValue = attackers ? adjustedAttackValue(kind, battleZone)
                                                 : adjustedDefenseValue(kind, battleZone);
            kindStates.push_back(FractionalKindState{
                .kind = kind,
                .baseCount = baseCount,
                .remainder = survivingCount - static_cast<double>(baseCount),
                .priorityValue = priorityValue,
                .reward = rewardValue(kind),
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
                if (lhs.priorityValue != rhs.priorityValue) {
                    return lhs.priorityValue > rhs.priorityValue;
                }
                return lhs.reward > rhs.reward;
            });

        for (const auto& kindState : kindStates) {
            if (remainingSurvivors <= 0) {
                break;
            }
            const auto rawAvailable = force[kindState.kind];
            const auto maxAvailable = static_cast<int>(std::ceil(rawAvailable - 1e-9));
            if (maxAvailable <= survivorsByKind.at(unitKindIndex(kindState.kind))) {
                continue;
            }
            ++survivorsByKind.at(unitKindIndex(kindState.kind));
            --remainingSurvivors;
        }

        return survivorsByKind;
    }
};

}  // namespace game
