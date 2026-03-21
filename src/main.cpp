#include "game/action.hpp"
#include "game/action_encoder.hpp"
#include "game/agent.hpp"
#include "game/game_state.hpp"
#include "game/mdp.hpp"
#include "game/setup_loader.hpp"
#include "game/simulator.hpp"
#include "game/state_encoder.hpp"
#include "game/unit.hpp"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <unordered_map>

namespace {

std::vector<std::string> splitString(const std::string& value, char delimiter) {
    std::vector<std::string> parts;
    std::stringstream stream(value);
    std::string part;
    while (std::getline(stream, part, delimiter)) {
        parts.push_back(part);
    }
    return parts;
}

std::string describeAction(const game::Action& action) {
    std::string description(game::toString(action.kind));
    bool hasDetails = false;
    if (action.sourceZoneId.has_value()) {
        description += "(from=" + *action.sourceZoneId;
        hasDetails = true;
    }
    if (action.targetZoneId.has_value()) {
        description += hasDetails ? ", to=" : "(to=";
        description += *action.targetZoneId;
        hasDetails = true;
    }
    if (action.unitCount.has_value()) {
        description += hasDetails ? ", count=" : "(count=";
        description += std::to_string(*action.unitCount);
        hasDetails = true;
    }
    if (hasDetails) {
        description += ")";
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
        for (const auto& detail : entry.detailLines) {
            std::cout << "      " << detail << "\n";
        }
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
        for (const auto& detail : entry.detailLines) {
            output << "    " << detail << "\n";
        }
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

void writeJsonString(std::ostream& output, const std::string& value) {
    output << '"';
    for (const auto character : value) {
        switch (character) {
            case '\\':
                output << "\\\\";
                break;
            case '"':
                output << "\\\"";
                break;
            case '\n':
                output << "\\n";
                break;
            default:
                output << character;
                break;
        }
    }
    output << '"';
}

void writeJsonStringArray(std::ostream& output, const std::vector<std::string>& values) {
    output << "[";
    for (std::size_t index = 0; index < values.size(); ++index) {
        if (index > 0) {
            output << ", ";
        }
        writeJsonString(output, values[index]);
    }
    output << "]";
}

void writeJsonNumberArray(std::ostream& output, const std::vector<double>& values) {
    output << "[";
    for (std::size_t index = 0; index < values.size(); ++index) {
        if (index > 0) {
            output << ", ";
        }
        output << values[index];
    }
    output << "]";
}

game::GameState buildJapanFirstCombatState(const std::filesystem::path& scenarioPath) {
    auto gameState = game::SetupLoader::loadFromFile(scenarioPath);
    game::SimplifiedChinaMdp mdp;

    for (int step = 0; step < 5; ++step) {
        mdp.step(gameState, game::Action{.kind = game::ActionKind::EndPhase});
    }
    mdp.step(gameState, game::Action{.kind = game::ActionKind::DeclareWarOnChina});
    mdp.step(gameState, game::Action{.kind = game::ActionKind::EndPhase});
    mdp.step(gameState, game::Action{.kind = game::ActionKind::EndPhase});

    if (gameState.currentNation() != "Japan" || gameState.currentPhase() != game::Phase::Combat) {
        throw std::runtime_error("Failed to build Japan first combat state");
    }
    return gameState;
}

void writeTrainingExample(
    const std::filesystem::path& scenarioPath,
    const std::filesystem::path& outputPath) {
    const auto gameState = buildJapanFirstCombatState(scenarioPath);
    const game::SimplifiedChinaMdp mdp;
    const auto legalActions = mdp.legalActions(gameState);
    const auto stateEncoder = game::StateEncoder::forNation(gameState, "Japan");
    const auto actionEncoder = game::ActionEncoder::forNation(gameState, "Japan");
    const auto stateFeatures = stateEncoder.encode(gameState);
    const auto stateFeatureLabels = stateEncoder.featureLabels();
    const auto actionFeatureLabels = actionEncoder.featureLabels();

    std::ofstream output(outputPath);
    if (!output) {
        throw std::runtime_error("Unable to write training example: " + outputPath.string());
    }

    output << "{\n";
    output << "  \"description\": ";
    writeJsonString(output, "Japan first combat decision state");
    output << ",\n";
    output << "  \"scenario_path\": ";
    writeJsonString(output, scenarioPath.string());
    output << ",\n";
    output << "  \"current_nation\": ";
    writeJsonString(output, std::string(gameState.currentNation()));
    output << ",\n";
    output << "  \"current_phase\": ";
    writeJsonString(output, std::string(game::toString(gameState.currentPhase())));
    output << ",\n";
    output << "  \"state_feature_count\": " << stateEncoder.featureCount() << ",\n";
    output << "  \"action_feature_count\": " << actionEncoder.featureCount() << ",\n";
    output << "  \"zone_order\": ";
    writeJsonStringArray(output, stateEncoder.zoneOrder());
    output << ",\n";
    output << "  \"controller_order\": ";
    writeJsonStringArray(output, stateEncoder.controllerOrder());
    output << ",\n";
    output << "  \"nation_order\": ";
    writeJsonStringArray(output, stateEncoder.nationOrder());
    output << ",\n";
    output << "  \"action_zone_order\": ";
    writeJsonStringArray(output, actionEncoder.zoneOrder());
    output << ",\n";
    output << "  \"state_feature_labels\": ";
    writeJsonStringArray(output, stateFeatureLabels);
    output << ",\n";
    output << "  \"state_features\": ";
    writeJsonNumberArray(output, stateFeatures);
    output << ",\n";
    output << "  \"action_feature_labels\": ";
    writeJsonStringArray(output, actionFeatureLabels);
    output << ",\n";
    output << "  \"legal_actions\": [\n";
    for (std::size_t index = 0; index < legalActions.size(); ++index) {
        const auto& action = legalActions[index];
        output << "    {\n";
        output << "      \"description\": ";
        writeJsonString(output, describeAction(action));
        output << ",\n";
        output << "      \"action_features\": ";
        writeJsonNumberArray(output, actionEncoder.encode(gameState, action));
        output << "\n";
        output << "    }";
        if (index + 1 < legalActions.size()) {
            output << ",";
        }
        output << "\n";
    }
    output << "  ]\n";
    output << "}\n";
}

}  // namespace

int main(int argc, char** argv) {
    const auto defaultScenarioPath = std::filesystem::path("data/china_simplified_setup.json");
    const auto snapshotDirectory = std::filesystem::path("output/snapshots");
    const auto actionLogPath = std::filesystem::path("output/session_actions.txt");
    const auto trainingExamplePath = std::filesystem::path("output/japan_training_example.json");

    try {
        std::filesystem::create_directories(actionLogPath.parent_path());

        std::filesystem::path scenarioPath = defaultScenarioPath;
        bool dumpTrainingExample = false;

        if (argc > 1 && std::string_view(argv[1]) == "--dump-training-example") {
            dumpTrainingExample = true;
            if (argc > 2) {
                scenarioPath = std::filesystem::path(argv[2]);
            }
        } else if (argc > 1) {
            scenarioPath = std::filesystem::path(argv[1]);
        }

        if (dumpTrainingExample) {
            writeTrainingExample(scenarioPath, trainingExamplePath);
            std::cout << "Training example written to " << trainingExamplePath.string() << "\n";
            return 0;
        }

        auto gameState = game::SetupLoader::loadFromFile(scenarioPath);
        game::SimplifiedChinaMdp mdp;
        std::unordered_map<std::string, std::unique_ptr<game::Agent>> agents;
        agents.emplace("CCP", std::make_unique<game::LazyPolicyAgent>("CCP"));
        agents.emplace("KMT", std::make_unique<game::LazyPolicyAgent>("KMT"));
        agents.emplace("Japan", std::make_unique<game::FirstActionAgent>("Japan"));

        const auto simulation = game::Simulator::run(std::move(gameState), mdp, agents, snapshotDirectory);
        printSimulationResult(simulation);
        writeActionLog(simulation, actionLogPath);
        std::cout << "\nSnapshots written to " << snapshotDirectory.string() << "\n";
        std::cout << "Action log written to " << actionLogPath.string() << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Failed to load scenario: " << error.what() << "\n";
        return 1;
    }
}
