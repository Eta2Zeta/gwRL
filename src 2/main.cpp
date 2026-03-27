#include "game/debug_tools.hpp"
#include "game/agent.hpp"
#include "game/mdp.hpp"
#include "game/setup_loader.hpp"
#include "game/simulator.hpp"

#include <filesystem>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <unordered_map>

int main(int argc, char** argv) {
    const auto defaultScenarioPath = std::filesystem::path("data/china_simplified_setup.json");
    const auto snapshotDirectory = std::filesystem::path("output/snapshots");
    const auto actionLogPath = std::filesystem::path("output/session_actions.txt");
    const auto trainingExamplePath = std::filesystem::path("output/japan_training_example.json");
    const auto defaultManualBattleSpecPath = std::filesystem::path("data/manual_battles/suiyuan_rehe_vs_beiping.json");
    const auto manualBattleOutputPath = std::filesystem::path("output/manual_battle_trace.txt");

    try {
        std::filesystem::create_directories(actionLogPath.parent_path());

        std::filesystem::path scenarioPath = defaultScenarioPath;
        std::filesystem::path manualBattleSpecPath = defaultManualBattleSpecPath;
        bool dumpTrainingExample = false;
        bool runManualBattle = false;

        if (argc > 1 && std::string_view(argv[1]) == "--dump-training-example") {
            dumpTrainingExample = true;
            if (argc > 2) {
                scenarioPath = std::filesystem::path(argv[2]);
            }
        } else if (argc > 1 && std::string_view(argv[1]) == "--run-manual-battle") {
            runManualBattle = true;
            if (argc > 2) {
                manualBattleSpecPath = std::filesystem::path(argv[2]);
            }
        } else if (argc > 1) {
            scenarioPath = std::filesystem::path(argv[1]);
        }

        if (dumpTrainingExample) {
            game::debug::writeTrainingExample(scenarioPath, trainingExamplePath);
            std::cout << "Training example written to " << trainingExamplePath.string() << "\n";
            return 0;
        }

        if (runManualBattle) {
            game::debug::runManualBattleSpec(manualBattleSpecPath, manualBattleOutputPath);
            std::cout << "\nManual battle log written to " << manualBattleOutputPath.string() << "\n";
            return 0;
        }

        auto gameState = game::SetupLoader::loadFromFile(scenarioPath);
        game::SimplifiedChinaMdp mdp;
        std::unordered_map<std::string, std::unique_ptr<game::Agent>> agents;
        agents.emplace("CCP", std::make_unique<game::LazyPolicyAgent>("CCP"));
        agents.emplace("KMT", std::make_unique<game::LazyPolicyAgent>("KMT"));
        agents.emplace("Japan", std::make_unique<game::FirstActionAgent>("Japan"));

        const auto simulation = game::Simulator::run(std::move(gameState), mdp, agents, snapshotDirectory);
        game::debug::printSimulationResult(simulation);
        game::debug::writeActionLog(simulation, actionLogPath);
        std::cout << "\nSnapshots written to " << snapshotDirectory.string() << "\n";
        std::cout << "Action log written to " << actionLogPath.string() << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Failed to run: " << error.what() << "\n";
        return 1;
    }
}
