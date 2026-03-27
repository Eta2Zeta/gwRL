#pragma once

#include "game/action.hpp"
#include "game/simulator.hpp"

#include <filesystem>
#include <string>

namespace game::debug {

std::string describeAction(const Action& action);

void printSimulationResult(const SimulationResult& simulation);
void writeActionLog(const SimulationResult& simulation, const std::filesystem::path& logPath);
void runManualBattleSpec(
    const std::filesystem::path& specPath,
    const std::filesystem::path& outputPath);
void writeTrainingExample(
    const std::filesystem::path& scenarioPath,
    const std::filesystem::path& outputPath);

}  // namespace game::debug
