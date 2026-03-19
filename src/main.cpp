#include "game/action.hpp"
#include "game/agent.hpp"
#include "game/game_state.hpp"
#include "game/mdp.hpp"
#include "game/setup_loader.hpp"
#include "game/simulator.hpp"
#include "game/unit.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <unordered_map>

namespace {

std::string describeAction(const game::Action& action) {
    std::string description(game::toString(action.kind));
    if (action.unitIndex.has_value()) {
        description += "(unit=" + std::to_string(*action.unitIndex);
        if (action.targetZoneId.has_value()) {
            description += ", to=" + *action.targetZoneId;
        }
        description += ")";
    } else if (action.targetZoneId.has_value()) {
        description += "(to=" + *action.targetZoneId + ")";
    }
    return description;
}

void printSimulationResult(const game::SimulationResult& simulation) {
    std::cout << "Simulation trace\n";
    for (const auto& entry : simulation.trace) {
        std::cout << "  " << entry.stepIndex
                  << ": " << entry.actingNation
                  << " / " << game::toString(entry.phaseBefore)
                  << " -> " << describeAction(entry.action);
        if (entry.terminalAfterAction) {
            std::cout << " -> terminal";
        } else {
            std::cout << " -> " << *entry.nextNation << " / " << game::toString(*entry.nextPhase);
        }
        std::cout << "\n";
    }

    std::cout << "\nOutcome\n";
    std::cout << "  terminal=" << (simulation.outcome.terminal ? "true" : "false")
              << " total_actions=" << simulation.outcome.totalActions << "\n";
    for (const auto& nationId : simulation.finalState.turnOrder()) {
        const auto& nation = simulation.finalState.nation(nationId);
        std::cout << "  " << nationId
                  << " turns=" << simulation.outcome.completedTurns.at(nationId)
                  << " income=" << nation.income()
                  << " treasury=" << nation.treasury()
                  << " units=" << simulation.outcome.unitCounts.at(nationId) << "\n";
    }
}

void writeActionLog(
    const game::SimulationResult& simulation,
    const std::filesystem::path& logPath) {
    std::ofstream output(logPath);
    if (!output) {
        throw std::runtime_error("Unable to write action log: " + logPath.string());
    }

    output << "Simulation action log\n";
    output << "scenario_turn_limit_per_nation=" << simulation.finalState.turnLimitPerNation() << "\n";
    output << "total_actions=" << simulation.outcome.totalActions << "\n\n";

    for (const auto& entry : simulation.trace) {
        output << entry.stepIndex
               << ": " << entry.actingNation
               << " / " << game::toString(entry.phaseBefore)
               << " -> " << describeAction(entry.action);
        if (entry.terminalAfterAction) {
            output << " -> terminal";
        } else {
            output << " -> " << *entry.nextNation << " / " << game::toString(*entry.nextPhase);
        }
        output << "\n";
    }

    output << "\nOutcome\n";
    output << "terminal=" << (simulation.outcome.terminal ? "true" : "false") << "\n";
    for (const auto& nationId : simulation.finalState.turnOrder()) {
        const auto& nation = simulation.finalState.nation(nationId);
        output << nationId
               << " turns=" << simulation.outcome.completedTurns.at(nationId)
               << " income=" << nation.income()
               << " treasury=" << nation.treasury()
               << " units=" << simulation.outcome.unitCounts.at(nationId)
               << "\n";
    }
}

}  // namespace

int main(int argc, char** argv) {
    const auto scenarioPath = argc > 1 ? std::filesystem::path(argv[1])
                                       : std::filesystem::path("data/china_simplified_setup.json");
    const auto snapshotDirectory = std::filesystem::path("output/snapshots");
    const auto actionLogPath = std::filesystem::path("output/session_actions.txt");

    try {
        auto gameState = game::SetupLoader::loadFromFile(scenarioPath);
        game::SimplifiedChinaMdp mdp;

        std::unordered_map<std::string, std::unique_ptr<game::Agent>> agents;
        agents.emplace("CCP", std::make_unique<game::LazyPolicyAgent>("CCP"));
        agents.emplace("Japan", std::make_unique<game::FirstActionAgent>("Japan"));
        agents.emplace("KMT", std::make_unique<game::LazyPolicyAgent>("KMT"));

        const auto simulation = game::Simulator::run(std::move(gameState), mdp, agents, snapshotDirectory);
        printSimulationResult(simulation);
        std::filesystem::create_directories(actionLogPath.parent_path());
        writeActionLog(simulation, actionLogPath);
        std::cout << "\nSnapshots written to " << snapshotDirectory.string() << "\n";
        std::cout << "Action log written to " << actionLogPath.string() << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Failed to load scenario: " << error.what() << "\n";
        return 1;
    }
}
