#pragma once

#include "game/action_catalog.hpp"
#include "game/agent.hpp"
#include "game/mdp.hpp"
#include "game/state_encoder.hpp"

#include <filesystem>
#include <random>
#include <string>
#include <unordered_map>
#include <vector>

namespace game {

struct JapanTrainingConfig {
    int episodes {250};
    double epsilonStart {0.35};
    double epsilonEnd {0.05};
    unsigned int seed {1936};
};

struct JapanEpisodeStats {
    int episodeIndex {0};
    double epsilon {0.0};
    double reward {0.0};
    int japanIncome {0};
    int japanUnitCount {0};
    int japanDecisionCount {0};
};

struct JapanTrainingResult {
    std::vector<JapanEpisodeStats> episodes;
};

class JapanPolicyTable {
  public:
    struct StateSummary {
        std::string stateKey;
        int totalVisits {0};
        int bestActionId {0};
        double bestActionValue {0.0};
    };

    explicit JapanPolicyTable(std::size_t actionCatalogSize);

    int selectActionId(
        const std::string& stateKey,
        const std::vector<int>& legalActionIds,
        double epsilon,
        std::mt19937& rng) const;

    void updateEpisode(
        const std::vector<std::pair<std::string, int>>& trajectory,
        double reward);

    double qValue(const std::string& stateKey, int actionId) const;
    int visitCount(const std::string& stateKey, int actionId) const;
    std::vector<StateSummary> summarizeStates(std::size_t maxStates) const;

  private:
    std::size_t actionCatalogSize_ {0};
    std::unordered_map<std::string, std::vector<double>> qValues_;
    std::unordered_map<std::string, std::vector<int>> visitCounts_;
};

class JapanPolicyAgent final : public Agent {
  public:
    JapanPolicyAgent(
        std::string nationId,
        const StateEncoder& stateEncoder,
        const ActionCatalog& actionCatalog,
        const JapanPolicyTable& policyTable,
        double epsilon = 0.0,
        unsigned int seed = 1936);

    Action chooseAction(const GameState& gameState, const std::vector<Action>& legalActions) override;

  private:
    const StateEncoder& stateEncoder_;
    const ActionCatalog& actionCatalog_;
    const JapanPolicyTable& policyTable_;
    double epsilon_ {0.0};
    mutable std::mt19937 rng_;
};

class JapanMonteCarloTrainer {
  public:
    JapanMonteCarloTrainer(std::filesystem::path scenarioPath, JapanTrainingConfig config = {});

    JapanTrainingResult train();

    const JapanPolicyTable& policyTable() const { return policyTable_; }
    const ActionCatalog& actionCatalog() const { return actionCatalog_; }
    const StateEncoder& stateEncoder() const { return stateEncoder_; }
    const std::filesystem::path& scenarioPath() const { return scenarioPath_; }

  private:
    double epsilonForEpisode(int episodeIndex) const;
    double evaluateJapanReward(const GameState& finalState) const;

    std::filesystem::path scenarioPath_;
    JapanTrainingConfig config_;
    SimplifiedChinaMdp mdp_;
    ActionCatalog actionCatalog_;
    StateEncoder stateEncoder_;
    JapanPolicyTable policyTable_;
    std::mt19937 rng_;
};

}  // namespace game
