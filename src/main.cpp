#include "game/action.hpp"
#include "game/agent.hpp"
#include "game/game_state.hpp"
#include "game/mdp.hpp"
#include "game/setup_loader.hpp"
#include "game/simulator.hpp"
#include "game/unit.hpp"

#include <filesystem>
#include <iostream>
#include <memory>
#include <unordered_map>

namespace {

void printSimulationResult(const game::SimulationResult& simulation) {
    std::cout << "Simulation trace\n";
    for (const auto& entry : simulation.trace) {
        std::cout << "  " << entry.stepIndex
                  << ": " << entry.actingNation
                  << " / " << game::toString(entry.phaseBefore)
                  << " -> " << game::toString(entry.action.kind);
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

}  // namespace

int main(int argc, char** argv) {
    const auto scenarioPath = argc > 1 ? std::filesystem::path(argv[1])
                                       : std::filesystem::path("data/china_simplified_setup.json");

    try {
        auto gameState = game::SetupLoader::loadFromFile(scenarioPath);
        game::SimplifiedChinaMdp mdp;

        std::unordered_map<std::string, std::unique_ptr<game::Agent>> agents;
        agents.emplace("CCP", std::make_unique<game::PassAgent>("CCP"));
        agents.emplace("Japan", std::make_unique<game::PassAgent>("Japan"));
        agents.emplace("KMT", std::make_unique<game::PassAgent>("KMT"));

        const auto simulation = game::Simulator::run(std::move(gameState), mdp, agents);
        printSimulationResult(simulation);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Failed to load scenario: " << error.what() << "\n";
        return 1;
    }
}
