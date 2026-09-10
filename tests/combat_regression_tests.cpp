#include "game/battle_resolver.hpp"
#include "game/mdp.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <functional>
#include <initializer_list>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace {

using game::BattleResolver;
using game::UnitKind;
using Composition = std::initializer_list<std::pair<UnitKind, int>>;

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void near(double actual, double expected, const std::string& message) {
    require(std::isfinite(actual) && std::abs(actual - expected) < 1e-8,
            message + ": expected " + std::to_string(expected) + ", got " + std::to_string(actual));
}

struct Army {
    std::vector<std::unique_ptr<game::Unit>> storage;
    std::vector<const game::Unit*> units;

    explicit Army(Composition composition) {
        for (const auto& [kind, count] : composition) {
            for (int index = 0; index < count; ++index) {
                storage.push_back(game::makeUnit(kind, "owner", "battle"));
                units.push_back(storage.back().get());
            }
        }
    }
};

BattleResolver::CombatOutcome battle(Composition attacker, Composition defender, game::Zone zone = {}) {
    const Army attackingArmy(attacker);
    const Army defendingArmy(defender);
    return BattleResolver::resolveLandCombat(zone, attackingArmy.units, defendingArmy.units);
}

const std::string& logStartingWith(const BattleResolver::CombatOutcome& outcome, std::string_view prefix) {
    const auto found = std::find_if(outcome.roundLogs.begin(), outcome.roundLogs.end(),
                                    [&](const auto& line) { return line.starts_with(prefix); });
    require(found != outcome.roundLogs.end(), "Missing combat log: " + std::string(prefix));
    return *found;
}

void contains(const std::string& line, std::string_view text) {
    require(line.find(text) != std::string::npos,
            "Expected '" + std::string(text) + "' in '" + line + "'");
}

void tdCasualtiesReturnFire() {
    const auto outcome = battle({{UnitKind::TankDestroyer, 4}}, {{UnitKind::Infantry, 4}});
    // All four infantry fire: 16/12 losses, even though the TDs kill one of them.
    const auto& firstRound = logStartingWith(outcome, "  after casualties:");
    contains(firstRound, "attacker 2.67 TD");
    contains(firstRound, "defender 3 Inf");
}

void tdTargetsVehiclesBeforeInfantry() {
    for (const auto vehicle : {UnitKind::LightTank, UnitKind::MechanizedInfantry, UnitKind::TankDestroyer}) {
        const auto outcome = battle({{UnitKind::TankDestroyer, 4}},
                                    {{UnitKind::Infantry, 4}, {vehicle, 1}});
        // The vehicle is the only eligible selected target; all defenders still fire.
        const auto& firstRound = logStartingWith(outcome, "  after casualties:");
        contains(firstRound, vehicle == UnitKind::LightTank ? "attacker 2.58 TD" : "attacker 2.33 TD");
        contains(firstRound, "defender 4 Inf,");
    }
}

void tdWithoutVehiclesUsesOrdinaryCasualtyPriority() {
    const auto outcome = battle({{UnitKind::TankDestroyer, 4}},
                                {{UnitKind::Infantry, 4}, {UnitKind::Artillery, 1}});
    // Artillery first strike leaves 3.75 TDs. Their 0.9375 hits remove weak artillery,
    // not stronger defending infantry, because there is no eligible selected target.
    contains(logStartingWith(outcome, "  after casualties:"), "defender 4 Inf + 0.06 Art,");
}

void tdExcessSelectedHitsBecomeOrdinaryHits() {
    const auto outcome = battle({{UnitKind::TankDestroyer, 12}},
                                {{UnitKind::Infantry, 4}, {UnitKind::LightTank, 1}});
    // Three hits remove the one vehicle and then two infantry instead of discarding overflow.
    const auto& firstRound = logStartingWith(outcome, "  after casualties:");
    contains(firstRound, "attacker 10.58 TD");
    contains(firstRound, "defender 2 Inf,");
}

void tdSelectsStrongestEligibleVehicle() {
    const auto outcome = battle({{UnitKind::TankDestroyer, 4}},
                                {{UnitKind::Infantry, 2}, {UnitKind::LightTank, 1}, {UnitKind::MediumTank, 1}});
    const auto& firstRound = logStartingWith(outcome, "  after casualties:");
    contains(firstRound, "attacker 2.83 TD");
    contains(firstRound, "defender 2 Inf + 1 LT,");
}

void defendingTdRetainsOrdinaryFire() {
    const auto outcome = battle(
        {{UnitKind::Infantry, 4}, {UnitKind::LightTank, 1}, {UnitKind::MediumTank, 1}},
        {{UnitKind::TankDestroyer, 4}});
    // Four defending TDs have 12 targeted strength plus 4 ordinary strength:
    // the selected hit kills the medium tank, and the ordinary 1/3 hit removes infantry.
    const auto& firstRound = logStartingWith(outcome, "  after casualties:");
    contains(firstRound, "attacker 3.67 Inf + 1 LT,");
    contains(firstRound, "defender 2.58 TD");
}

void unpairedArtilleryFirstStrikeIsWeaker() {
    const auto outcome = battle({{UnitKind::Artillery, 2}}, {{UnitKind::Infantry, 8}});
    // Both unpaired guns attack at 2: they inflict 4/12, then die to infantry return fire.
    near(outcome.survivingDefenderForce[UnitKind::Infantry], 23.0 / 3.0,
         "Unpaired artillery first-strike damage");
    require(outcome.defendersWon, "Infantry should defeat two unsupported artillery");

    const auto defense = battle({{UnitKind::Infantry, 8}},
                                {{UnitKind::Artillery, 2}, {UnitKind::Infantry, 1}});
    // Only one gun is paired: first strike totals 3 + 2, and the infantry defends at 4.
    contains(logStartingWith(defense, "first strike:"), "defender 2 Art (5/12=0.42)");
    contains(logStartingWith(defense, "  after casualties:"), "attacker 7.25 Inf");
}

void artilleryOnlySupportsInfantryAttack() {
    for (const auto infantry : {UnitKind::Infantry, UnitKind::Marine}) {
        const auto outcome = battle({{UnitKind::Artillery, 1}, {infantry, 1}},
                                    {{UnitKind::Infantry, 12}});
        // Three first-strike strength + three supported infantry strength = 1/2 casualty.
        near(outcome.survivingDefenderForce[UnitKind::Infantry], 11.5,
             "Artillery supports infantry-class attack");
    }
    const auto defense = battle({{UnitKind::Infantry, 12}},
                                {{UnitKind::Artillery, 1}, {UnitKind::Infantry, 1}});
    // After 1/4 first-strike loss, the attacker loses 4/12 to defending infantry, not 5/12.
    contains(logStartingWith(defense, "  after casualties:"), "attacker 11.42 Inf");
}

void mechanizedPairsButReceivesNoAttackBonus() {
    const auto solo = battle({{UnitKind::MechanizedInfantry, 1}}, {{UnitKind::Infantry, 12}});
    near(solo.survivingDefenderForce[UnitKind::Infantry], 11.75, "Mechanized attack is three");
    const auto paired = battle({{UnitKind::Artillery, 2}, {UnitKind::MechanizedInfantry, 1}},
                               {{UnitKind::Infantry, 12}});
    // One paired gun (3), one unpaired gun (2), and the mechanized unit (3), for 8/12.
    near(paired.survivingDefenderForce[UnitKind::Infantry], 34.0 / 3.0,
         "Mechanized prevents one artillery penalty without gaining infantry support");
}

void artilleryPairingRecalculatesAfterCasualties() {
    const auto outcome = battle({{UnitKind::Artillery, 2}, {UnitKind::Infantry, 1}},
                                {{UnitKind::Artillery, 2}, {UnitKind::Infantry, 2}});
    // The opening strike leaves 1/2 attacking infantry, and ordinary fire removes it
    // plus 1/6 artillery. The surviving 11/6 guns are all unpaired in round two.
    contains(logStartingWith(outcome, "round 2:"), "attacker 1.83 Art (3.67/12=0.31)");
}

void artilleryOnlyBattleContinuesAfterFirstStrike() {
    const auto outcome = battle({{UnitKind::Artillery, 1}}, {{UnitKind::Artillery, 1}});
    logStartingWith(outcome, "round 2:");
    require(outcome.draw && outcome.survivingAttackerCount == 0 && outcome.survivingDefenderCount == 0,
            "Equal artillery forces should keep fighting to mutual destruction");
}

void ordinaryCombatTerrainAndRoundingRemainStable() {
    const auto normal = battle({{UnitKind::Infantry, 12}}, {{UnitKind::Infantry, 1}});
    near(normal.survivingAttackerForce[UnitKind::Infantry], 35.0 / 3.0, "Infantry return fire");
    require(normal.attackersWon && normal.survivingAttackerCount == 12,
            "Fractional survivor rounding should retain twelve infantry");

    game::Zone mountainCity;
    mountainCity.terrain = "mountain";
    mountainCity.isCity = true;
    const auto modified = battle({{UnitKind::Infantry, 12}}, {{UnitKind::Infantry, 1}}, mountainCity);
    near(modified.survivingAttackerForce[UnitKind::Infantry], 139.0 / 12.0,
         "Mountain attack penalty and city defense bonus");
    require(modified.attackersWon, "Twelve mountain attackers still inflict one casualty");
}

void emptyForcesHaveConsistentOutcomes() {
    const auto empty = battle({}, {});
    require(empty.draw && empty.roundLogs.empty(), "Empty battle should be a draw with no rounds");
    const auto unopposed = battle({{UnitKind::Infantry, 2}}, {});
    require(unopposed.attackersWon && unopposed.survivingAttackerCount == 2,
            "Unopposed attackers survive unchanged");
    const auto undefendedAttack = battle({}, {{UnitKind::Artillery, 1}});
    require(undefendedAttack.defendersWon && undefendedAttack.survivingDefenderCount == 1,
            "Defenders survive absent attackers");
}

void checkMapBattle(Composition attackers, Composition defenders, bool expectAttackerWin) {
    game::GameState state;
    state.addNation(game::Nation("attacker", "Attacker", 0, 0));
    state.addNation(game::Nation("defender", "Defender", 0, 0));
    state.addZone(game::Zone{.id = "origin", .controller = "attacker"});
    state.addZone(game::Zone{.id = "battle", .controller = "defender"});
    state.setTurnOrder({"attacker", "defender"});
    state.setPhaseOrder({game::Phase::CombatResolve});
    state.declareWar("attacker", "defender");

    std::vector<const game::Unit*> attackerUnits;
    std::vector<const game::Unit*> defenderUnits;
    for (const auto& [kind, count] : attackers) {
        for (int index = 0; index < count; ++index) {
            auto unit = game::makeUnit(kind, "attacker", "origin");
            unit->setPendingCombatTargetZoneId("battle");
            attackerUnits.push_back(unit.get());
            state.addUnit(std::move(unit));
        }
    }
    for (const auto& [kind, count] : defenders) {
        for (int index = 0; index < count; ++index) {
            auto unit = game::makeUnit(kind, "defender", "battle");
            defenderUnits.push_back(unit.get());
            state.addUnit(std::move(unit));
        }
    }

    const auto& zone = state.zone("battle");
    const auto expected = BattleResolver::resolveLandCombat(zone, attackerUnits, defenderUnits);
    require(expected.attackersWon == expectAttackerWin, "Unexpected fixture winner");
    const auto lostAttackers = BattleResolver::destroyedUnitsFromRoundedSurvivors(
        attackerUnits, zone, true, expected.survivingAttackerForce, expected.survivingAttackerCount);
    const auto lostDefenders = BattleResolver::destroyedUnitsFromRoundedSurvivors(
        defenderUnits, zone, false, expected.survivingDefenderForce, expected.survivingDefenderCount);
    std::array<int, game::unitKindCount()> expectedAttackerKinds{};
    std::array<int, game::unitKindCount()> expectedDefenderKinds{};
    int expectedDestroyedCredit = 0;
    for (const auto* unit : attackerUnits) {
        if (std::find(lostAttackers.begin(), lostAttackers.end(), unit) == lostAttackers.end()) {
            ++expectedAttackerKinds[game::unitKindIndex(unit->kind())];
        }
    }
    for (const auto* unit : defenderUnits) {
        if (std::find(lostDefenders.begin(), lostDefenders.end(), unit) == lostDefenders.end()) {
            ++expectedDefenderKinds[game::unitKindIndex(unit->kind())];
        } else {
            expectedDestroyedCredit += game::rewardValue(unit->kind());
        }
    }

    const auto result = game::SimplifiedChinaMdp{}.step(
        state, game::Action{.kind = game::ActionKind::ResolveCombat, .targetZoneId = "battle"});
    require(state.unitCountFor("attacker") == expected.survivingAttackerCount,
            "Map attacker survivor count differs from shared resolver");
    require(state.unitCountFor("defender") == expected.survivingDefenderCount,
            "Map defender survivor count differs from shared resolver");
    require(state.zone("battle").controller == (expected.attackersWon ? "attacker" : "defender"),
            "Map territory control differs from shared resolver");
    require(state.enemyUnitValueDestroyedByNation("attacker") == expectedDestroyedCredit,
            "Map destroyed-unit reward must use rounded casualties");

    std::array<int, game::unitKindCount()> actualAttackerKinds{};
    std::array<int, game::unitKindCount()> actualDefenderKinds{};
    for (const auto& unit : state.units()) {
        require(!unit->hasPendingCombatTarget(), "Resolved attacker still has pending combat");
        if (unit->ownerId() == "attacker") {
            ++actualAttackerKinds[game::unitKindIndex(unit->kind())];
            require(unit->zoneId() == (expected.attackersWon ? "battle" : "origin"),
                    "Surviving attacker occupies wrong territory");
        } else {
            ++actualDefenderKinds[game::unitKindIndex(unit->kind())];
        }
    }
    require(actualAttackerKinds == expectedAttackerKinds && actualDefenderKinds == expectedDefenderKinds,
            "Map survivor unit types differ from shared resolver rounding");
    require(result.detailLines.size() == expected.roundLogs.size() + 2 &&
                std::equal(expected.roundLogs.begin(), expected.roundLogs.end(), result.detailLines.begin() + 1),
            "Map must report the shared resolver's battle rounds");
}

void mapUsesSharedResolverForWinsLossesAndDraws() {
    checkMapBattle({{UnitKind::TankDestroyer, 4}}, {{UnitKind::Infantry, 4}}, false);
    checkMapBattle({{UnitKind::TankDestroyer, 12}},
                   {{UnitKind::MediumTank, 1}, {UnitKind::LightTank, 1}, {UnitKind::Infantry, 2}}, true);
    checkMapBattle({{UnitKind::Artillery, 1}}, {{UnitKind::Artillery, 1}}, false);
    checkMapBattle({{UnitKind::Infantry, 12}}, {{UnitKind::Infantry, 1}}, true);
}

}  // namespace

int main() {
    const std::vector<std::pair<std::string, std::function<void()>>> tests{
        {"TD casualties return fire", tdCasualtiesReturnFire},
        {"TD vehicle restriction", tdTargetsVehiclesBeforeInfantry},
        {"TD no-vehicle ordinary priority", tdWithoutVehiclesUsesOrdinaryCasualtyPriority},
        {"TD excess hits fall back", tdExcessSelectedHitsBecomeOrdinaryHits},
        {"TD vehicle selection priority", tdSelectsStrongestEligibleVehicle},
        {"Defending TD ordinary fire", defendingTdRetainsOrdinaryFire},
        {"Unpaired artillery first strike", unpairedArtilleryFirstStrikeIsWeaker},
        {"Artillery infantry attack support", artilleryOnlySupportsInfantryAttack},
        {"Mechanized artillery pairing", mechanizedPairsButReceivesNoAttackBonus},
        {"Artillery pairing after casualties", artilleryPairingRecalculatesAfterCasualties},
        {"Artillery-only battle termination", artilleryOnlyBattleContinuesAfterFirstStrike},
        {"Ordinary combat, terrain, rounding", ordinaryCombatTerrainAndRoundingRemainStable},
        {"Empty forces", emptyForcesHaveConsistentOutcomes},
        {"Map shared-resolver integration", mapUsesSharedResolverForWinsLossesAndDraws},
    };
    int failed = 0;
    for (const auto& [name, run] : tests) {
        try {
            run();
            std::cout << "PASS " << name << '\n';
        } catch (const std::exception& error) {
            ++failed;
            std::cerr << "FAIL " << name << ": " << error.what() << '\n';
        }
    }
    std::cout << tests.size() - failed << "/" << tests.size() << " combat regressions passed\n";
    return failed == 0 ? 0 : 1;
}
