#include "game/simulator.hpp"

#include <stdexcept>

namespace game {

SimulationResult Simulator::run(
    GameState initialState,
    const SimplifiedChinaMdp& mdp,
    const std::unordered_map<std::string, std::unique_ptr<Agent>>& agents) {
    SimulationResult result{
        .finalState = std::move(initialState),
    };

    int stepIndex = 0;
    while (!result.finalState.isTerminal()) {
        const auto actingNation = std::string(result.finalState.currentNation());
        auto agentIt = agents.find(actingNation);
        if (agentIt == agents.end() || !agentIt->second) {
            throw std::runtime_error("Missing agent for nation: " + actingNation);
        }

        const auto legalActions = mdp.legalActions(result.finalState);
        if (legalActions.empty()) {
            throw std::runtime_error("MDP returned no legal actions for nation: " + actingNation);
        }

        const auto chosenAction = agentIt->second->chooseAction(result.finalState, legalActions);
        const auto step = mdp.step(result.finalState, chosenAction);

        result.trace.push_back(TraceEntry{
            .stepIndex = stepIndex++,
            .actingNation = step.actingNation,
            .phaseBefore = step.phaseBefore,
            .action = step.action,
            .terminalAfterAction = step.terminal,
            .nextNation = step.nextNation,
            .nextPhase = step.nextPhase,
        });
    }

    result.outcome.totalActions = static_cast<int>(result.trace.size());
    result.outcome.terminal = result.finalState.isTerminal();
    for (const auto& nationId : result.finalState.turnOrder()) {
        result.outcome.completedTurns.emplace(nationId, result.finalState.completedTurnsFor(nationId));
        result.outcome.unitCounts.emplace(nationId, result.finalState.unitCountFor(nationId));
    }

    return result;
}

}  // namespace game
