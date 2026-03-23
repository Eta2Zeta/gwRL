#include "game/debug_tools.hpp"

#include "game/action_encoder.hpp"
#include "game/game_state.hpp"
#include "game/mdp.hpp"
#include "game/setup_loader.hpp"
#include "game/simple_json.hpp"
#include "game/state_encoder.hpp"
#include "game/unit.hpp"

#include <algorithm>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <tuple>
#include <unordered_map>
#include <vector>

namespace game::debug {

namespace {

ActionKind parseActionKind(std::string_view value) {
    if (value == "declare_war_on_china") {
        return ActionKind::DeclareWarOnChina;
    }
    if (value == "purchase_unit") {
        return ActionKind::PurchaseUnit;
    }
    if (value == "move_combat_unit") {
        return ActionKind::MoveCombatUnit;
    }
    if (value == "resolve_combat") {
        return ActionKind::ResolveCombat;
    }
    if (value == "place_unit") {
        return ActionKind::PlaceUnit;
    }
    if (value == "end_phase") {
        return ActionKind::EndPhase;
    }
    throw std::runtime_error("Unsupported action kind in manual battle spec: " + std::string(value));
}

bool actionsMatch(const Action& lhs, const Action& rhs) {
    return lhs.kind == rhs.kind
        && lhs.sourceZoneId == rhs.sourceZoneId
        && lhs.targetZoneId == rhs.targetZoneId
        && lhs.unitCount == rhs.unitCount
        && lhs.unitKind == rhs.unitKind;
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

std::string readOptionalStringField(
    const json::Value& object,
    const std::string& key,
    std::string defaultValue = {}) {
    if (const auto* field = object.find(key)) {
        return field->asString();
    }
    return defaultValue;
}

int readOptionalIntField(const json::Value& object, const std::string& key, int defaultValue) {
    if (const auto* field = object.find(key)) {
        return field->asInt();
    }
    return defaultValue;
}

bool readOptionalBoolField(const json::Value& object, const std::string& key, bool defaultValue) {
    if (const auto* field = object.find(key)) {
        return field->asBool();
    }
    return defaultValue;
}

struct ManualBattleSpec {
    std::string description;
    std::filesystem::path scenarioPath;
    std::string actingNation {"Japan"};
    Phase phase {Phase::CombatMove};
    bool clearUnits {true};
    std::vector<std::pair<std::string, std::string>> wars;
    std::unordered_map<std::string, std::string> controllers;
    std::vector<Action> scriptedActions;
    std::vector<std::tuple<UnitKind, std::string, std::string, int>> units;
};

ManualBattleSpec parseManualBattleSpec(const std::filesystem::path& specPath) {
    const auto root = json::parseFile(specPath);
    ManualBattleSpec spec;
    spec.description = readOptionalStringField(root, "description", specPath.stem().string());
    spec.scenarioPath = std::filesystem::path(
        readOptionalStringField(root, "scenario_path", "data/china_simplified_setup.json"));
    spec.actingNation = readOptionalStringField(root, "acting_nation", "Japan");
    spec.phase = parsePhase(readOptionalStringField(root, "phase", "combat_move"));
    spec.clearUnits = readOptionalBoolField(root, "clear_units", true);

    if (const auto* wars = root.find("wars")) {
        for (const auto& warValue : wars->asArray()) {
            spec.wars.emplace_back(
                warValue.require("aggressor").asString(),
                warValue.require("defender").asString());
        }
    }

    if (const auto* controllers = root.find("controllers")) {
        for (const auto& [zoneId, controllerValue] : controllers->asObject()) {
            spec.controllers.emplace(zoneId, controllerValue.asString());
        }
    }

    for (const auto& unitValue : root.require("units").asArray()) {
        spec.units.emplace_back(
            parseUnitKind(unitValue.require("type").asString()),
            readOptionalStringField(unitValue, "owner"),
            unitValue.require("zone").asString(),
            readOptionalIntField(unitValue, "count", 1));
    }

    for (const auto& actionValue : root.require("actions").asArray()) {
        Action action;
        action.kind = parseActionKind(actionValue.require("kind").asString());
        if (const auto* from = actionValue.find("from")) {
            action.sourceZoneId = from->asString();
        }
        if (const auto* to = actionValue.find("to")) {
            action.targetZoneId = to->asString();
        }
        if (const auto* count = actionValue.find("count")) {
            action.unitCount = count->asInt();
        }
        if (const auto* unit = actionValue.find("unit")) {
            action.unitKind = parseUnitKind(unit->asString());
        }
        spec.scriptedActions.push_back(std::move(action));
    }

    return spec;
}

void clearAllUnits(GameState& gameState) {
    std::vector<const Unit*> allUnits;
    allUnits.reserve(gameState.units().size());
    for (const auto& unitPtr : gameState.units()) {
        allUnits.push_back(unitPtr.get());
    }
    gameState.removeUnits(allUnits);
}

std::vector<std::string> summarizeZoneForces(const GameState& gameState) {
    std::vector<std::string> lines;
    std::vector<std::string> zoneIds;
    zoneIds.reserve(gameState.zones().size());
    for (const auto& [zoneId, zone] : gameState.zones()) {
        zoneIds.push_back(zoneId);
    }
    std::sort(zoneIds.begin(), zoneIds.end());

    for (const auto& zoneId : zoneIds) {
        const auto& zone = gameState.zone(zoneId);
        std::vector<std::string> unitParts;
        for (const auto* unit : gameState.unitsInZone(zoneId)) {
            std::string part = unit->ownerId();
            part += " ";
            part += std::string(toString(unit->kind()));
            if (unit->hasPendingCombatTarget()) {
                part += "->" + *unit->pendingCombatTargetZoneId();
            }
            unitParts.push_back(std::move(part));
        }
        if (unitParts.empty()) {
            continue;
        }
        std::ostringstream stream;
        stream << zoneId << " (" << zone.controller << "): ";
        for (std::size_t index = 0; index < unitParts.size(); ++index) {
            if (index > 0) {
                stream << ", ";
            }
            stream << unitParts[index];
        }
        lines.push_back(stream.str());
    }
    return lines;
}

GameState buildJapanFirstDecisionAfterDeclarationState(const std::filesystem::path& scenarioPath) {
    auto gameState = SetupLoader::loadFromFile(scenarioPath);
    SimplifiedChinaMdp mdp;

    for (int step = 0; step < 6; ++step) {
        mdp.step(gameState, Action{.kind = ActionKind::EndPhase});
    }
    mdp.step(gameState, Action{.kind = ActionKind::DeclareWarOnChina});
    mdp.step(gameState, Action{.kind = ActionKind::EndPhase});

    if (gameState.currentNation() != "Japan") {
        throw std::runtime_error("Failed to build Japan first post-declaration state");
    }
    return gameState;
}

}  // namespace

std::string describeAction(const Action& action) {
    std::string description(toString(action.kind));
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
    if (action.unitKind.has_value()) {
        description += hasDetails ? ", unit=" : "(unit=";
        description += std::string(toString(*action.unitKind));
        hasDetails = true;
    }
    if (hasDetails) {
        description += ")";
    }
    return description;
}

void printSimulationResult(const SimulationResult& simulation) {
    std::cout << "Simulation trace\n";
    for (const auto& entry : simulation.trace) {
        std::cout << "  " << entry.stepIndex
                  << ": " << entry.actingNation
                  << " / " << toString(entry.phaseBefore)
                  << " -> " << describeAction(entry.action);
        if (entry.terminalAfterAction) {
            std::cout << " -> terminal";
        } else {
            std::cout << " -> " << *entry.nextNation << " / " << toString(*entry.nextPhase);
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
    const SimulationResult& simulation,
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
               << " / " << toString(entry.phaseBefore)
               << " -> " << describeAction(entry.action);
        if (entry.terminalAfterAction) {
            output << " -> terminal";
        } else {
            output << " -> " << *entry.nextNation << " / " << toString(*entry.nextPhase);
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

void runManualBattleSpec(
    const std::filesystem::path& specPath,
    const std::filesystem::path& outputPath) {
    const auto spec = parseManualBattleSpec(specPath);
    auto gameState = SetupLoader::loadFromFile(spec.scenarioPath);
    SimplifiedChinaMdp mdp;

    if (spec.clearUnits) {
        clearAllUnits(gameState);
    }
    for (const auto& [zoneId, controller] : spec.controllers) {
        gameState.setZoneController(zoneId, controller);
    }
    for (const auto& [aggressor, defender] : spec.wars) {
        if (!gameState.areAtWar(aggressor, defender)) {
            gameState.declareWar(aggressor, defender);
        }
    }
    for (const auto& [unitKind, ownerId, zoneId, count] : spec.units) {
        if (count <= 0) {
            throw std::runtime_error("Manual battle unit count must be positive");
        }
        for (int index = 0; index < count; ++index) {
            gameState.addUnit(makeUnit(unitKind, ownerId, zoneId));
        }
    }
    gameState.forceCurrentTurnState(spec.actingNation, spec.phase);

    std::vector<std::string> lines;
    lines.push_back("Manual battle");
    lines.push_back("description=" + spec.description);
    lines.push_back("spec_file=" + specPath.string());
    lines.push_back("scenario=" + spec.scenarioPath.string());
    lines.push_back(
        "start=" + std::string(gameState.currentNation()) + " / " + std::string(toString(gameState.currentPhase())));
    lines.push_back("");
    lines.push_back("Initial forces");
    for (const auto& line : summarizeZoneForces(gameState)) {
        lines.push_back("  " + line);
    }

    for (std::size_t actionIndex = 0; actionIndex < spec.scriptedActions.size(); ++actionIndex) {
        const auto& requestedAction = spec.scriptedActions[actionIndex];
        const auto legalActions = mdp.legalActions(gameState);
        const auto legalIt = std::find_if(
            legalActions.begin(),
            legalActions.end(),
            [&](const Action& legalAction) {
                return actionsMatch(legalAction, requestedAction);
            });
        if (legalIt == legalActions.end()) {
            std::ostringstream error;
            error << "Requested manual action is not legal: " << describeAction(requestedAction) << ". Legal actions: ";
            for (std::size_t index = 0; index < legalActions.size(); ++index) {
                if (index > 0) {
                    error << ", ";
                }
                error << describeAction(legalActions[index]);
            }
            throw std::runtime_error(error.str());
        }

        const auto result = mdp.step(gameState, *legalIt);
        lines.push_back("");
        lines.push_back(
            std::to_string(actionIndex + 1)
            + ": "
            + result.actingNation
            + " / "
            + std::string(toString(result.phaseBefore))
            + " -> "
            + describeAction(result.action));
        for (const auto& detail : result.detailLines) {
            lines.push_back("    " + detail);
        }
        if (result.terminal) {
            lines.push_back("    next=terminal");
        } else {
            lines.push_back(
                "    next=" + *result.nextNation + " / " + std::string(toString(*result.nextPhase)));
        }
        lines.push_back("    forces:");
        for (const auto& line : summarizeZoneForces(gameState)) {
            lines.push_back("      " + line);
        }
    }

    lines.push_back("");
    lines.push_back("Final reward");
    lines.push_back(
        "  Japan="
        + std::to_string(
            gameState.nation("Japan").income()
            + 0.1 * gameState.unitValueFor("Japan")
            + 0.1 * gameState.enemyUnitValueDestroyedByNation("Japan")));
    lines.push_back(
        "  components: income=" + std::to_string(gameState.nation("Japan").income())
        + " surviving_unit_value=" + std::to_string(gameState.unitValueFor("Japan"))
        + " destroyed_enemy_unit_value=" + std::to_string(gameState.enemyUnitValueDestroyedByNation("Japan")));

    std::ofstream output(outputPath);
    if (!output) {
        throw std::runtime_error("Unable to write manual battle log: " + outputPath.string());
    }
    for (const auto& line : lines) {
        std::cout << line << "\n";
        output << line << "\n";
    }
}

void writeTrainingExample(
    const std::filesystem::path& scenarioPath,
    const std::filesystem::path& outputPath) {
    const auto gameState = buildJapanFirstDecisionAfterDeclarationState(scenarioPath);
    const SimplifiedChinaMdp mdp;
    const auto legalActions = mdp.legalActions(gameState);
    const auto stateEncoder = StateEncoder::forNation(gameState, "Japan");
    const auto actionEncoder = ActionEncoder::forNation(gameState, "Japan");
    const auto stateFeatures = stateEncoder.encode(gameState);
    const auto stateFeatureLabels = stateEncoder.featureLabels();
    const auto actionFeatureLabels = actionEncoder.featureLabels();

    std::ofstream output(outputPath);
    if (!output) {
        throw std::runtime_error("Unable to write training example: " + outputPath.string());
    }

    output << "{\n";
    output << "  \"description\": ";
    writeJsonString(output, "Japan first decision after declaration");
    output << ",\n";
    output << "  \"scenario_path\": ";
    writeJsonString(output, scenarioPath.string());
    output << ",\n";
    output << "  \"current_nation\": ";
    writeJsonString(output, std::string(gameState.currentNation()));
    output << ",\n";
    output << "  \"current_phase\": ";
    writeJsonString(output, std::string(toString(gameState.currentPhase())));
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

}  // namespace game::debug
