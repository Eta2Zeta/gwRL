#include "game/training.hpp"

#include "game/setup_loader.hpp"

#include <algorithm>
#include <stdexcept>

namespace game {

JapanPolicyTable::JapanPolicyTable(std::size_t actionCatalogSize)
    : actionCatalogSize_(actionCatalogSize) {}

int JapanPolicyTable::selectActionId(
    const std::string& stateKey,
    const std::vector<int>& legalActionIds,
    double epsilon,
    std::mt19937& rng) const {
    if (legalActionIds.empty()) {
        throw std::runtime_error("JapanPolicyTable cannot choose from an empty legal action list");
    }

    std::uniform_real_distribution<double> probabilityDraw(0.0, 1.0);
    if (epsilon > 0.0 && probabilityDraw(rng) < epsilon) {
        std::uniform_int_distribution<std::size_t> randomAction(0, legalActionIds.size() - 1);
        return legalActionIds[randomAction(rng)];
    }

    auto bestActionId = legalActionIds.front();
    auto bestValue = qValue(stateKey, bestActionId);
    for (const auto actionId : legalActionIds) {
        const auto candidateValue = qValue(stateKey, actionId);
        if (candidateValue > bestValue
            || (candidateValue == bestValue && actionId < bestActionId)) {
            bestActionId = actionId;
            bestValue = candidateValue;
        }
    }
    return bestActionId;
}

void JapanPolicyTable::updateEpisode(
    const std::vector<std::pair<std::string, int>>& trajectory,
    double reward) {
    for (const auto& [stateKey, actionId] : trajectory) {
        auto& qValues = qValues_[stateKey];
        if (qValues.empty()) {
            qValues.assign(actionCatalogSize_, 0.0);
        }

        auto& visitCounts = visitCounts_[stateKey];
        if (visitCounts.empty()) {
            visitCounts.assign(actionCatalogSize_, 0);
        }

        ++visitCounts.at(static_cast<std::size_t>(actionId));
        auto& value = qValues.at(static_cast<std::size_t>(actionId));
        value += (reward - value) / static_cast<double>(visitCounts.at(static_cast<std::size_t>(actionId)));
    }
}

double JapanPolicyTable::qValue(const std::string& stateKey, int actionId) const {
    const auto stateIt = qValues_.find(stateKey);
    if (stateIt == qValues_.end()) {
        return 0.0;
    }
    return stateIt->second.at(static_cast<std::size_t>(actionId));
}

int JapanPolicyTable::visitCount(const std::string& stateKey, int actionId) const {
    const auto stateIt = visitCounts_.find(stateKey);
    if (stateIt == visitCounts_.end()) {
        return 0;
    }
    return stateIt->second.at(static_cast<std::size_t>(actionId));
}

std::vector<JapanPolicyTable::StateSummary> JapanPolicyTable::summarizeStates(std::size_t maxStates) const {
    std::vector<StateSummary> summaries;
    summaries.reserve(visitCounts_.size());

    for (const auto& [stateKey, counts] : visitCounts_) {
        auto totalVisits = 0;
        auto bestActionId = 0;
        auto bestActionValue = qValue(stateKey, 0);
        auto hasBestAction = false;
        for (std::size_t actionId = 0; actionId < counts.size(); ++actionId) {
            totalVisits += counts[actionId];
            if (counts[actionId] <= 0) {
                continue;
            }
            const auto candidateValue = qValue(stateKey, static_cast<int>(actionId));
            if (!hasBestAction || candidateValue > bestActionValue) {
                hasBestAction = true;
                bestActionId = static_cast<int>(actionId);
                bestActionValue = candidateValue;
            }
        }
        if (!hasBestAction) {
            continue;
        }
        summaries.push_back(StateSummary{
            .stateKey = stateKey,
            .totalVisits = totalVisits,
            .bestActionId = bestActionId,
            .bestActionValue = bestActionValue,
        });
    }

    std::sort(
        summaries.begin(),
        summaries.end(),
        [](const StateSummary& lhs, const StateSummary& rhs) {
            return lhs.totalVisits > rhs.totalVisits;
        });

    if (summaries.size() > maxStates) {
        summaries.resize(maxStates);
    }
    return summaries;
}

JapanPolicyAgent::JapanPolicyAgent(
    std::string nationId,
    const StateEncoder& stateEncoder,
    const ActionCatalog& actionCatalog,
    const JapanPolicyTable& policyTable,
    double epsilon,
    unsigned int seed)
    : Agent(std::move(nationId)),
      stateEncoder_(stateEncoder),
      actionCatalog_(actionCatalog),
      policyTable_(policyTable),
      epsilon_(epsilon),
      rng_(seed) {}

Action JapanPolicyAgent::chooseAction(const GameState& gameState, const std::vector<Action>& legalActions) {
    if (legalActions.empty()) {
        throw std::runtime_error("JapanPolicyAgent was asked to choose from an empty action list");
    }
    const auto stateKey = stateEncoder_.encodeKey(gameState);
    const auto legalActionIds = actionCatalog_.legalActionIds(legalActions);
    const auto actionId = policyTable_.selectActionId(stateKey, legalActionIds, epsilon_, rng_);
    return actionCatalog_.actionAt(actionId);
}

JapanMonteCarloTrainer::JapanMonteCarloTrainer(
    std::filesystem::path scenarioPath,
    JapanTrainingConfig config)
    : scenarioPath_(std::move(scenarioPath)),
      config_(config),
      actionCatalog_(ActionCatalog::forNation(SetupLoader::loadFromFile(scenarioPath_), "Japan")),
      stateEncoder_(StateEncoder::forNation(SetupLoader::loadFromFile(scenarioPath_), "Japan")),
      policyTable_(actionCatalog_.size()),
      rng_(config_.seed) {}

JapanTrainingResult JapanMonteCarloTrainer::train() {
    JapanTrainingResult result;
    result.episodes.reserve(static_cast<std::size_t>(config_.episodes));

    LazyPolicyAgent ccpAgent("CCP");
    LazyPolicyAgent kmtAgent("KMT");

    for (int episodeIndex = 0; episodeIndex < config_.episodes; ++episodeIndex) {
        auto gameState = SetupLoader::loadFromFile(scenarioPath_);
        std::vector<std::pair<std::string, int>> japanTrajectory;

        while (!gameState.isTerminal()) {
            const auto legalActions = mdp_.legalActions(gameState);
            if (legalActions.empty()) {
                throw std::runtime_error("Trainer received an empty legal action list");
            }

            Action chosenAction;
            if (gameState.currentNation() == "Japan") {
                const auto stateKey = stateEncoder_.encodeKey(gameState);
                const auto legalActionIds = actionCatalog_.legalActionIds(legalActions);
                const auto actionId = policyTable_.selectActionId(
                    stateKey,
                    legalActionIds,
                    epsilonForEpisode(episodeIndex),
                    rng_);
                chosenAction = actionCatalog_.actionAt(actionId);
                japanTrajectory.emplace_back(stateKey, actionId);
            } else if (gameState.currentNation() == "CCP") {
                chosenAction = ccpAgent.chooseAction(gameState, legalActions);
            } else {
                chosenAction = kmtAgent.chooseAction(gameState, legalActions);
            }

            mdp_.step(gameState, chosenAction);
        }

        const auto reward = evaluateJapanReward(gameState);
        policyTable_.updateEpisode(japanTrajectory, reward);
        result.episodes.push_back(JapanEpisodeStats{
            .episodeIndex = episodeIndex,
            .epsilon = epsilonForEpisode(episodeIndex),
            .reward = reward,
            .japanIncome = gameState.nation("Japan").income(),
            .japanUnitCount = gameState.unitCountFor("Japan"),
            .japanDecisionCount = static_cast<int>(japanTrajectory.size()),
        });
    }

    return result;
}

double JapanMonteCarloTrainer::epsilonForEpisode(int episodeIndex) const {
    if (config_.episodes <= 1) {
        return config_.epsilonEnd;
    }
    const auto progress = static_cast<double>(episodeIndex) / static_cast<double>(config_.episodes - 1);
    return config_.epsilonStart + (config_.epsilonEnd - config_.epsilonStart) * progress;
}

double JapanMonteCarloTrainer::evaluateJapanReward(const GameState& finalState) const {
    return static_cast<double>(finalState.nation("Japan").income())
           + 0.1 * static_cast<double>(finalState.unitCountFor("Japan"));
}

}  // namespace game
