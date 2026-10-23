#include "game/japan_training_env.hpp"
#include "game/mdp.hpp"
#include "game/composition_battle_env.hpp"
#include "game/state_encoder.hpp"
#include "game/catalog.hpp"

#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <system_error>
#include <utility>
#include <vector>

namespace {

using game::Action;
using game::ActionKind;
using game::Phase;
using game::UnitKind;

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

template <typename Callable>
void requireRejected(Callable&& call, const std::string& message) {
    bool rejected = false;
    try {
        call();
    } catch (const std::runtime_error&) {
        rejected = true;
    }
    require(rejected, message);
}

class TemporaryScenario {
  public:
    TemporaryScenario() {
        const auto nonce = std::chrono::steady_clock::now().time_since_epoch().count();
        for (int attempt = 0; attempt < 100; ++attempt) {
            const auto candidate = std::filesystem::temp_directory_path()
                / ("gwrl-prototype-boundary-" + std::to_string(nonce) + "-" + std::to_string(attempt));
            if (std::filesystem::create_directory(candidate)) {
                directory_ = candidate;
                break;
            }
        }
        require(!directory_.empty(), "Could not create a unique temporary scenario directory");
        std::ofstream output(path());
        output << R"json({
          "nations": [
            {"id":"Japan","display_name":"Japan","income":2,"max_factory_output":5,"treasury":20},
            {"id":"KMT","display_name":"KMT","income":1,"max_factory_output":0},
            {"id":"CCP","display_name":"CCP","income":0,"max_factory_output":0}
          ],
          "turn_order":["Japan","KMT","CCP"],
          "turn_limit_per_nation":2,
          "phases":["declaration_of_war","purchase_units","combat_move","combat_resolve","non_combat","place_units"],
          "zones":[
            {"id":"origin","display_name":"Origin","kind":"land","controller":"Japan",
             "income_value":2,"facilities":["major_factory"],"neighbors":[{"id":"target","railway":false}]},
            {"id":"target","display_name":"Target","kind":"land","controller":"KMT",
             "income_value":1,"neighbors":[{"id":"origin","railway":false}]}
          ],
          "setup":{
            "Japan":{"units":[
              {"type":"Infantry","zone":"origin"},{"type":"Infantry","zone":"origin"},
              {"type":"Infantry","zone":"origin"},{"type":"Infantry","zone":"origin"}]},
            "KMT":{"units":[{"type":"Infantry","zone":"target"}]},
            "CCP":{"units":[]}
          }
        })json";
        output.close();
        if (!output) {
            std::error_code ignored;
            std::filesystem::remove_all(directory_, ignored);
            throw std::runtime_error("Could not write temporary scenario");
        }
    }

    ~TemporaryScenario() {
        std::error_code ignored;
        std::filesystem::remove_all(directory_, ignored);
    }

    TemporaryScenario(const TemporaryScenario&) = delete;
    TemporaryScenario& operator=(const TemporaryScenario&) = delete;

    std::filesystem::path path() const { return directory_ / "scenario.json"; }

  private:
    std::filesystem::path directory_;
};

game::GameState decisionState(Phase phase) {
    game::GameState state;
    state.addNation(game::Nation("Japan", "Japan", 2, 5, 20));
    state.addNation(game::Nation("KMT", "KMT", 1, 0, 0));
    state.addNation(game::Nation("CCP", "CCP", 0, 0, 0));
    state.addZone(game::Zone{
        .id = "origin", .controller = "Japan", .incomeValue = 2,
        .facilities = {"major_factory"}, .neighbors = {{"target", false}},
    });
    state.addZone(game::Zone{
        .id = "target", .controller = "KMT", .incomeValue = 1,
        .neighbors = {{"origin", false}},
    });
    for (int index = 0; index < 4; ++index) {
        state.addUnit(game::makeUnit(UnitKind::Infantry, "Japan", "origin"));
    }
    state.addUnit(game::makeUnit(UnitKind::Infantry, "KMT", "target"));
    state.setTurnOrder({"Japan", "KMT", "CCP"});
    state.setPhaseOrder({Phase::DeclarationOfWar, Phase::PurchaseUnits, Phase::CombatMove,
                         Phase::CombatResolve, Phase::NonCombat, Phase::PlaceUnits});
    state.declareWar("Japan", "KMT");
    state.forceCurrentTurnState("Japan", phase);
    return state;
}

Action purchase(UnitKind kind, int count) {
    return Action{.kind = ActionKind::PurchaseUnit, .unitCount = count, .unitKind = kind};
}

Action moveInfantry(int count) {
    return Action{.kind = ActionKind::MoveCombatUnit, .sourceZoneId = "origin",
                  .targetZoneId = "target", .unitCount = count, .unitKind = UnitKind::Infantry};
}

void cloneSurvivesDeletedSourceAndIsolatesMutableState() {
    TemporaryScenario source;
    game::JapanTrainingEnv original(source.path());
    require(original.currentPhase() == "production", "Canonical campaign must begin in Production");
    const auto opening = original.legalActions();
    require(!opening.empty(), "No canonical production decisions");
    original.step(opening.front());
    const auto originalFeatures = original.encodeState();
    const auto originalActions = original.encodeLegalActions();
    require(std::filesystem::remove(source.path()), "Could not remove source before cloning");
    auto branch = original.clone();
    require(branch.encodeState() == originalFeatures, "Clone lost progressed state");
    require(branch.encodeLegalActions() == originalActions, "Clone changed legal action encoding");
    require(branch.stateFeatureLabels() == original.stateFeatureLabels(), "Clone changed encoder schema");
    require(branch.finalReward() == original.finalReward(), "Clone changed reward");
    require(!branch.legalActions().empty(), "Cloned production is stuck");
    branch.step(branch.legalActions().front());
    require(branch.encodeState() != originalFeatures, "Branch action did not change state");
    require(original.encodeState() == originalFeatures, "Branch mutated original");
    const auto checkpoint = branch.serialize();
    original.restore(checkpoint);
    require(original.serialize() == checkpoint, "Canonical checkpoint restore changed execution");
    require(branch.clone().encodeState() == branch.encodeState(), "Re-cloning depends on deleted source");
}

void tinyUsesCanonicalFivePhasesAndHorizon() {
    game::JapanTrainingEnv env(std::filesystem::path(GWRL_SOURCE_DIR) / "game_content/scenarios/china_simplified_setup.json");
    require(env.unitCountFor("Japan") == 4 && env.nationTreasury("Japan") == 13,
            "Tiny campaign starting task changed");
    require(env.engine().state().definition->rules.find("benchmark"), "Missing explicit benchmark profile");
    require(env.stateFeatureLabels().size() == env.encodeState().size(), "State encoder dimension mismatch");
    int steps = 0;
    while (!env.isTerminal() && steps++ < 200) {
        const auto actions = env.legalActions();
        require(!actions.empty(), "Canonical tiny campaign has a dead end");
        auto selected = std::find_if(actions.begin(), actions.end(), [](const auto &a) { return a.kind == "end_phase"; });
        if (selected == actions.end()) selected = actions.begin();
        env.step(*selected);
    }
    require(env.isTerminal(), "Tiny benchmark did not finish two full rounds");
    for (const auto &id : {"Japan", "CCP", "KMT"}) require(env.completedTurnsFor(id) == 2, "National horizon mismatch");
    require(env.engine().state().clock.completedRounds == 2, "Calendar accounting mismatch");
}

void compositionUsesDiceAndEntitledCombatDecisions() {
    game::CompositionBattleEnv env(3, 3);
    env.setDiceTapeForTesting(std::vector<int>(50, 1));
    auto choose = [&](const std::string &kind) {
        const auto actions = env.legalActions();
        auto i = std::find_if(actions.begin(), actions.end(), [&](const auto &a) { return a.kind == kind; });
        require(i != actions.end(), "Missing canonical composition action: " + kind);
        env.step(*i);
    };
    choose("benchmark_compose_units");
    require(env.purchasedUnitCount("Attacker", UnitKind::Infantry) == 1, "Catalog allocation missing");
    choose("benchmark_finish_composition");
    require(env.currentNation() == "Defender", "Defender did not own its allocation choice");
    choose("benchmark_compose_units"); choose("benchmark_finish_composition");
    require(!env.isTerminal(), "Composition used fractional combat during setup");
    bool defenderCasualty = false, attackerCasualty = false;
    for (int steps = 0; !env.isTerminal() && steps < 100; ++steps) {
        auto actions = env.legalActions(); require(!actions.empty(), "Canonical composition combat stuck");
        auto i = std::find_if(actions.begin(), actions.end(), [](const auto &a) {
            return a.kind.find("decline") != std::string::npos || a.kind.find("no_banzai") != std::string::npos;
        });
        if (i == actions.end()) i = actions.begin();
        if (i->kind == "land_take_casualty") {
            defenderCasualty |= i->nation == "kmt"; attackerCasualty |= i->nation == "japan";
            require(env.currentNation() == (i->nation == "kmt" ? "Defender" : "Attacker"), "Casualty owner hidden by adapter");
        }
        env.step(*i);
    }
    require(env.isTerminal(), "Composition battle did not terminate");
    require(defenderCasualty && attackerCasualty, "Actual simultaneous fire/casualties were not exposed");
    require(env.unitCountFor("Attacker") == 0 && env.unitCountFor("Defender") == 0, "D12 losses were replaced by expected survivors");
    require(env.finalReward() == 0.0, "Mutual destruction reward mismatch");
    auto clone = env.clone(); require(clone.serialize() == env.serialize(), "Combat clone lost actual dice state");
    const auto checkpoint = env.serialize(); env.reset(); env.restore(checkpoint);
    require(env.isTerminal() && env.finalReward() == 0.0, "Composition terminal checkpoint lost result");
}

void zeroBudgetCompositionAndSearchIsolation() {
    game::CompositionBattleEnv env(0, 0);
    env.step(env.legalActions().front()); env.step(env.legalActions().front());
    require(env.isTerminal() && env.winnerId().empty(), "Empty force allocation should draw");
    auto branch = env.cloneForSearch(99);
    require(branch.encodeState() == env.encodeState(), "Search seed leaked into policy observation");
    require(branch.serialize() != env.serialize(), "Search clone did not use independent simulation randomness");
}

void purchaseKindsMustComeFromLegalActions() {
    auto state = decisionState(Phase::PurchaseUnits);
    const game::SimplifiedChinaMdp mdp;
    const auto encoder = game::StateEncoder::forNation(state, "Japan");
    const auto before = encoder.encode(state);
    requireRejected([&] { mdp.step(state, purchase(UnitKind::LightTank, 1)); },
                    "Unlisted LightTank purchase bypassed the prototype's legal roster");
    require(encoder.encode(state) == before, "Rejected purchase changed encoded state");
    require(state.nation("Japan").treasury() == 20 && state.pendingPurchaseCountFor("Japan") == 0,
            "Rejected purchase spent treasury or added pending units");

    mdp.step(state, purchase(UnitKind::Infantry, 2));
    require(state.nation("Japan").treasury() == 14 && state.pendingPurchaseCountFor("Japan") == 2,
            "Listed Infantry purchase no longer works");
    mdp.step(state, Action{.kind = ActionKind::EndPhase});
    require(state.currentPhase() == Phase::CombatMove, "Ending purchases must remain legal with units awaiting placement");
}

void endPhaseCannotSkipPlaceablePurchases() {
    auto state = decisionState(Phase::PurchaseUnits);
    const game::SimplifiedChinaMdp mdp;
    mdp.step(state, purchase(UnitKind::Infantry, 2));
    for (int phase = 0; phase < 4; ++phase) {
        mdp.step(state, Action{.kind = ActionKind::EndPhase});
    }
    require(state.currentPhase() == Phase::PlaceUnits, "Fixture did not reach placement");
    requireRejected([&] { mdp.step(state, Action{.kind = ActionKind::EndPhase}); },
                    "Direct EndPhase skipped purchases that can be placed");
    require(state.currentPhase() == Phase::PlaceUnits && state.pendingPurchaseCountFor("Japan") == 2
                && state.completedTurnsFor("Japan") == 0 && state.unitCountFor("Japan") == 4,
            "Rejected EndPhase changed the turn or purchase state");
    mdp.step(state, Action{.kind = ActionKind::PlaceUnit, .targetZoneId = "origin",
                           .unitCount = 2, .unitKind = UnitKind::Infantry});
    mdp.step(state, Action{.kind = ActionKind::EndPhase});
    require(state.currentNation() == "KMT" && state.completedTurnsFor("Japan") == 1
                && state.pendingPurchaseCountFor("Japan") == 0 && state.unitCountFor("Japan") == 6,
            "Valid placement and end-turn behavior changed");
}

void endPhaseRemainsLegalWhenPlacementIsImpossible() {
    auto state = decisionState(Phase::PurchaseUnits);
    const game::SimplifiedChinaMdp mdp;
    mdp.step(state, purchase(UnitKind::Infantry, 1));
    state.forceCurrentTurnState("Japan", Phase::PlaceUnits);
    state.setZoneController("origin", "KMT");
    mdp.step(state, Action{.kind = ActionKind::EndPhase});
    require(state.currentNation() == "KMT" && state.pendingPurchaseCountFor("Japan") == 1,
            "Prototype must preserve its existing unplaceable-purchase carryover behavior");
}

void endPhaseCannotSkipPendingCombat() {
    auto state = decisionState(Phase::CombatMove);
    const game::SimplifiedChinaMdp mdp;
    mdp.step(state, moveInfantry(4));
    mdp.step(state, Action{.kind = ActionKind::EndPhase});
    require(state.currentPhase() == Phase::CombatResolve, "Fixture did not reach combat resolution");
    requireRejected([&] { mdp.step(state, Action{.kind = ActionKind::EndPhase}); },
                    "Direct EndPhase skipped unresolved combat");
    require(state.currentPhase() == Phase::CombatResolve && state.unitCountFor("Japan") == 4
                && state.unitCountFor("KMT") == 1 && state.unitAt(0).hasPendingCombatTarget(),
            "Rejected combat EndPhase changed the battle");
    mdp.step(state, Action{.kind = ActionKind::ResolveCombat, .targetZoneId = "target"});
    for (const auto& unit : state.units()) {
        require(!unit->hasPendingCombatTarget(), "Legal ResolveCombat left a stale combat commitment");
    }
    mdp.step(state, Action{.kind = ActionKind::EndPhase});
    require(state.currentPhase() == Phase::NonCombat, "EndPhase must work after combat resolution");
}

void extraneousActionPayloadIsRejected() {
    auto state = decisionState(Phase::PurchaseUnits);
    const game::SimplifiedChinaMdp mdp;
    requireRejected([&] {
        mdp.step(state, Action{.kind = ActionKind::EndPhase, .targetZoneId = "target"});
    }, "A forged payload must not match an enumerated EndPhase action");
    require(state.currentPhase() == Phase::PurchaseUnits && state.nation("Japan").treasury() == 20,
            "Rejected action payload changed state");
    mdp.step(state, Action{.kind = ActionKind::EndPhase});
    require(state.currentPhase() == Phase::CombatMove, "Plain EndPhase was rejected");
}

}  // namespace

int main() {
    const std::vector<std::pair<std::string, std::function<void()>>> tests{
        {"Clone after source deletion and state isolation", cloneSurvivesDeletedSourceAndIsolatesMutableState},
        {"Canonical tiny campaign horizon", tinyUsesCanonicalFivePhasesAndHorizon},
        {"Canonical composition combat and decisions", compositionUsesDiceAndEntitledCombatDecisions},
        {"Empty composition and search isolation", zeroBudgetCompositionAndSearchIsolation},
        {"Purchase legal roster", purchaseKindsMustComeFromLegalActions},
        {"Cannot skip placeable purchases", endPhaseCannotSkipPlaceablePurchases},
        {"Unplaceable purchase carryover", endPhaseRemainsLegalWhenPlacementIsImpossible},
        {"Cannot skip pending combat", endPhaseCannotSkipPendingCombat},
        {"Exact enumerated action payload", extraneousActionPayloadIsRejected},
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
    std::cout << tests.size() - failed << "/" << tests.size() << " prototype boundary regressions passed\n";
    return failed == 0 ? 0 : 1;
}
