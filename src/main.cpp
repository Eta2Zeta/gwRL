#include "game/action.hpp"
#include "game/action_encoder.hpp"
#include "game/agent.hpp"
#include "game/game_state.hpp"
#include "game/mdp.hpp"
#include "game/setup_loader.hpp"
#include "game/simulator.hpp"
#include "game/training.hpp"
#include "game/unit.hpp"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <numeric>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <unordered_map>

namespace {

struct ParsedTurnProgress {
    std::string nationId;
    int completedTurns {0};
};

struct ParsedEconomy {
    std::string nationId;
    int income {0};
    int treasury {0};
};

struct ParsedZoneUnitCount {
    std::string ownerId;
    int total {0};
    int movable {0};
};

struct ParsedZoneState {
    std::string zoneId;
    std::string controller;
    bool isCity {false};
    int incomeValue {0};
    std::vector<ParsedZoneUnitCount> unitCounts;
};

struct ParsedPolicyState {
    std::string currentNation;
    std::string phase;
    std::vector<ParsedTurnProgress> turns;
    std::vector<ParsedEconomy> economies;
    std::string wars;
    std::vector<ParsedZoneState> zones;
};

std::vector<std::string> splitString(const std::string& value, char delimiter) {
    std::vector<std::string> parts;
    std::stringstream stream(value);
    std::string part;
    while (std::getline(stream, part, delimiter)) {
        parts.push_back(part);
    }
    return parts;
}

ParsedPolicyState parsePolicyStateString(const std::string& stateKey) {
    ParsedPolicyState parsed;
    for (const auto& token : splitString(stateKey, '|')) {
        if (token.rfind("current=", 0) == 0) {
            parsed.currentNation = token.substr(std::string("current=").size());
            continue;
        }
        if (token.rfind("phase=", 0) == 0) {
            parsed.phase = token.substr(std::string("phase=").size());
            continue;
        }
        if (token.rfind("turns=", 0) == 0) {
            for (const auto& entry : splitString(token.substr(std::string("turns=").size()), ',')) {
                if (entry.empty()) {
                    continue;
                }
                const auto parts = splitString(entry, ':');
                if (parts.size() != 2) {
                    continue;
                }
                parsed.turns.push_back(ParsedTurnProgress{
                    .nationId = parts[0],
                    .completedTurns = std::stoi(parts[1]),
                });
            }
            continue;
        }
        if (token.rfind("income=", 0) == 0) {
            for (const auto& entry : splitString(token.substr(std::string("income=").size()), ',')) {
                if (entry.empty()) {
                    continue;
                }
                const auto parts = splitString(entry, ':');
                if (parts.size() != 3) {
                    continue;
                }
                parsed.economies.push_back(ParsedEconomy{
                    .nationId = parts[0],
                    .income = std::stoi(parts[1]),
                    .treasury = std::stoi(parts[2]),
                });
            }
            continue;
        }
        if (token.rfind("wars=", 0) == 0) {
            parsed.wars = token.substr(std::string("wars=").size());
            continue;
        }
        if (token.rfind("zone=", 0) == 0) {
            const auto fields = splitString(token, ':');
            if (fields.size() < 4) {
                continue;
            }

            ParsedZoneState zone;
            zone.zoneId = fields[0].substr(std::string("zone=").size());
            zone.controller = fields[1].substr(std::string("ctrl=").size());
            zone.isCity = fields[2].substr(std::string("city=").size()) == "1";
            zone.incomeValue = std::stoi(fields[3].substr(std::string("income=").size()));

            for (std::size_t index = 4; index < fields.size(); ++index) {
                const auto& field = fields[index];
                const auto equalsPosition = field.find('=');
                if (equalsPosition == std::string::npos) {
                    continue;
                }
                const auto ownerId = field.substr(0, equalsPosition);
                const auto values = splitString(field.substr(equalsPosition + 1), '/');
                if (values.size() != 2) {
                    continue;
                }
                zone.unitCounts.push_back(ParsedZoneUnitCount{
                    .ownerId = ownerId,
                    .total = std::stoi(values[0]),
                    .movable = std::stoi(values[1]),
                });
            }

            parsed.zones.push_back(std::move(zone));
        }
    }

    return parsed;
}

std::string describeWars(const std::string& wars) {
    std::vector<std::string> descriptions;
    if (wars.size() >= 1 && wars[0] == '1') {
        descriptions.push_back("Japan vs CCP");
    }
    if (wars.size() >= 2 && wars[1] == '1') {
        descriptions.push_back("Japan vs KMT");
    }
    if (wars.size() >= 3 && wars[2] == '1') {
        descriptions.push_back("CCP vs KMT");
    }
    if (descriptions.empty()) {
        return "none";
    }

    std::string value;
    for (std::size_t index = 0; index < descriptions.size(); ++index) {
        if (index > 0) {
            value += ", ";
        }
        value += descriptions[index];
    }
    return value;
}

std::string zoneLabel(
    const ParsedZoneState& zone,
    const std::unordered_map<std::string, std::string>& zoneDisplayNames) {
    const auto it = zoneDisplayNames.find(zone.zoneId);
    return it != zoneDisplayNames.end() ? it->second : zone.zoneId;
}

void writeFormattedPolicyState(
    std::ostream& output,
    const ParsedPolicyState& state,
    const std::unordered_map<std::string, std::string>& zoneDisplayNames) {
    output << "Acting nation: " << state.currentNation << "\n";
    output << "Phase: " << state.phase << "\n";

    output << "Turns completed so far:\n";
    for (const auto& turn : state.turns) {
        output << "  - " << turn.nationId << ": " << turn.completedTurns << "\n";
    }

    output << "Wars: " << describeWars(state.wars) << "\n";

    output << "Economy:\n";
    for (const auto& economy : state.economies) {
        output << "  - " << economy.nationId
               << ": income " << economy.income
               << ", treasury " << economy.treasury
               << "\n";
    }

    output << "Map state:\n";
    for (const auto& zone : state.zones) {
        output << "  - " << zoneLabel(zone, zoneDisplayNames)
               << " [" << zone.zoneId << "]"
               << ": controller " << zone.controller
               << ", income " << zone.incomeValue;
        if (zone.isCity) {
            output << ", city";
        }
        output << "\n";

        bool printedAnyUnits = false;
        for (const auto& unitCount : zone.unitCounts) {
            if (unitCount.total <= 0) {
                continue;
            }
            printedAnyUnits = true;
            output << "    * " << unitCount.ownerId
                   << " infantry: " << unitCount.total
                   << " total, " << unitCount.movable
                   << " movable\n";
        }
        if (!printedAnyUnits) {
            output << "    * no infantry present\n";
        }
    }
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

void writeTrainingSummary(
    const game::JapanTrainingResult& trainingResult,
    const game::JapanMonteCarloTrainer& trainer,
    const std::filesystem::path& outputPath) {
    std::ofstream output(outputPath);
    if (!output) {
        throw std::runtime_error("Unable to write training summary: " + outputPath.string());
    }

    const auto scenario = game::SetupLoader::loadFromFile(trainer.scenarioPath());
    std::unordered_map<std::string, std::string> zoneDisplayNames;
    for (const auto& [zoneId, zone] : scenario.zones()) {
        zoneDisplayNames.emplace(zoneId, zone.displayName);
    }

    output << "Japan training summary\n";
    output << "episodes=" << trainingResult.episodes.size() << "\n";
    output << "action_catalog_size=" << trainer.actionCatalog().size() << "\n";
    output << "state_feature_count=" << trainer.stateEncoder().featureCount() << "\n\n";
    output << "Note:\n";
    output << "  These are intermediate Japan decision states seen during training.\n";
    output << "  They are not terminal end-of-session boards.\n";
    output << "  \"Acting nation\" means whose turn it is at that decision point.\n\n";

    if (!trainingResult.episodes.empty()) {
        const auto recentWindow = std::min<std::size_t>(10, trainingResult.episodes.size());
        const auto recentRewardSum = std::accumulate(
            trainingResult.episodes.end() - static_cast<std::ptrdiff_t>(recentWindow),
            trainingResult.episodes.end(),
            0.0,
            [](double sum, const game::JapanEpisodeStats& episode) {
                return sum + episode.reward;
            });
        output << "recent_average_reward=" << (recentRewardSum / static_cast<double>(recentWindow)) << "\n";
        output << "last_episode_reward=" << trainingResult.episodes.back().reward << "\n";
        output << "last_episode_income=" << trainingResult.episodes.back().japanIncome << "\n";
        output << "last_episode_unit_count=" << trainingResult.episodes.back().japanUnitCount << "\n\n";
    }

    output << "Most visited Japan decision states\n\n";
    int stateIndex = 1;
    for (const auto& summary : trainer.policyTable().summarizeStates(8)) {
        const auto parsedState = parsePolicyStateString(summary.stateKey);
        output << "State " << stateIndex++ << "\n";
        output << "Seen during training: " << summary.totalVisits << " times\n";
        output << "Learned best action: "
               << describeAction(trainer.actionCatalog().actionAt(summary.bestActionId))
               << "\n";
        output << "Estimated Japan value: " << summary.bestActionValue << "\n";
        writeFormattedPolicyState(output, parsedState, zoneDisplayNames);
        output << "\n";
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

void writeOptionBExample(
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
        throw std::runtime_error("Unable to write Option-B example: " + outputPath.string());
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
    output << "  \"max_combat_unit_count\": " << actionEncoder.maxCombatUnitCount() << ",\n";
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
        writeJsonNumberArray(output, actionEncoder.encode(action));
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
    const auto trainingSummaryPath = std::filesystem::path("output/japan_training_summary.txt");
    const auto optionBExamplePath = std::filesystem::path("output/japan_option_b_example.json");

    try {
        std::filesystem::create_directories(actionLogPath.parent_path());

        std::filesystem::path scenarioPath = defaultScenarioPath;
        bool trainJapan = false;
        int trainingEpisodes = 250;
        bool dumpOptionBExample = false;

        if (argc > 1 && std::string_view(argv[1]) == "--dump-option-b-example") {
            dumpOptionBExample = true;
            if (argc > 2) {
                scenarioPath = std::filesystem::path(argv[2]);
            }
        } else if (argc > 1 && std::string_view(argv[1]) == "--train-japan") {
            trainJapan = true;
            if (argc > 2) {
                trainingEpisodes = std::stoi(argv[2]);
            }
            if (argc > 3) {
                scenarioPath = std::filesystem::path(argv[3]);
            }
        } else if (argc > 1) {
            scenarioPath = std::filesystem::path(argv[1]);
        }

        if (dumpOptionBExample) {
            writeOptionBExample(scenarioPath, optionBExamplePath);
            std::cout << "Option-B example written to " << optionBExamplePath.string() << "\n";
            return 0;
        }

        auto gameState = game::SetupLoader::loadFromFile(scenarioPath);
        game::SimplifiedChinaMdp mdp;
        std::unordered_map<std::string, std::unique_ptr<game::Agent>> agents;
        agents.emplace("CCP", std::make_unique<game::LazyPolicyAgent>("CCP"));
        agents.emplace("KMT", std::make_unique<game::LazyPolicyAgent>("KMT"));

        std::unique_ptr<game::JapanMonteCarloTrainer> trainer;
        if (trainJapan) {
            trainer = std::make_unique<game::JapanMonteCarloTrainer>(
                scenarioPath,
                game::JapanTrainingConfig{
                    .episodes = trainingEpisodes,
                });
            const auto trainingResult = trainer->train();
            writeTrainingSummary(trainingResult, *trainer, trainingSummaryPath);
            std::cout << "Japan training complete\n";
            std::cout << "  episodes=" << trainingResult.episodes.size() << "\n";
            std::cout << "  action_catalog_size=" << trainer->actionCatalog().size() << "\n";
            std::cout << "  state_feature_count=" << trainer->stateEncoder().featureCount() << "\n";
            if (!trainingResult.episodes.empty()) {
                const auto& lastEpisode = trainingResult.episodes.back();
                std::cout << "  last_reward=" << lastEpisode.reward << "\n";
            }
            agents.emplace(
                "Japan",
                std::make_unique<game::JapanPolicyAgent>(
                    "Japan",
                    trainer->stateEncoder(),
                    trainer->actionCatalog(),
                    trainer->policyTable(),
                    0.0,
                    1936));
        } else {
            agents.emplace("Japan", std::make_unique<game::FirstActionAgent>("Japan"));
        }

        const auto simulation = game::Simulator::run(std::move(gameState), mdp, agents, snapshotDirectory);
        printSimulationResult(simulation);
        writeActionLog(simulation, actionLogPath);
        std::cout << "\nSnapshots written to " << snapshotDirectory.string() << "\n";
        std::cout << "Action log written to " << actionLogPath.string() << "\n";
        if (trainJapan) {
            std::cout << "Training summary written to " << trainingSummaryPath.string() << "\n";
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Failed to load scenario: " << error.what() << "\n";
        return 1;
    }
}
