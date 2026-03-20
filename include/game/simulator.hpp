#pragma once

#include "game/agent.hpp"
#include "game/mdp.hpp"

#include <filesystem>
#include <memory>
#include <unordered_map>
#include <vector>

namespace game {

struct TraceEntry {
    int stepIndex {0};
    std::string actingNation;
    Phase phaseBefore {Phase::PurchaseUnits};
    Action action;
    std::vector<std::string> detailLines;
    bool terminalAfterAction {false};
    std::optional<std::string> nextNation;
    std::optional<Phase> nextPhase;
};

struct OutcomeSummary {
    int totalActions {0};
    bool terminal {false};
    std::unordered_map<std::string, int> completedTurns;
    std::unordered_map<std::string, int> unitCounts;
};

struct SimulationResult {
    GameState finalState;
    std::vector<TraceEntry> trace;
    OutcomeSummary outcome;
};

class Simulator {
  public:
    static SimulationResult run(
        GameState initialState,
        const SimplifiedChinaMdp& mdp,
        const std::unordered_map<std::string, std::unique_ptr<Agent>>& agents,
        const std::filesystem::path& snapshotDirectory = {});
};

}  // namespace game
