#pragma once

#include "game/campaign.hpp"

#include <filesystem>
#include <optional>
#include <string_view>

namespace game {

// Benchmark setup is explicit scenario data. Gameplay always runs through the
// same campaign modules as the regional campaign; no fractional combat exists
// in these adapters. Historical prototype model dimensions are not compatible.
struct BenchmarkStepResult {
    std::string actingNation;
    campaign::Action action;
    std::vector<std::string> detailLines;
    bool terminal{false};
};

campaign::Id benchmarkNation(std::string_view);
std::string benchmarkDisplayNation(const campaign::Id &);
std::filesystem::path benchmarkContentRoot();
campaign::State tinyCampaignBenchmark(const std::filesystem::path &);
campaign::State compositionCampaignBenchmark(int attackerBudget, int defenderBudget,
                                             const std::string &terrain, bool city);
std::shared_ptr<const campaign::Rules> benchmarkCampaignRules(bool composition = false);

class CampaignBenchmarkEnv {
  public:
    CampaignBenchmarkEnv(campaign::State, bool composition, std::uint64_t seed = 1);
    void reset();
    void resetWithSeed(std::uint64_t);
    bool isTerminal() const;
    std::string currentNation() const;
    std::string currentPhase() const;
    std::vector<campaign::Action> legalActions() const;
    std::vector<campaign::Action> legalInterrupts() const;
    BenchmarkStepResult step(const campaign::Action &);
    std::vector<double> encodeState() const;
    std::vector<std::vector<double>> encodeLegalActions() const;
    std::vector<std::string> stateFeatureLabels() const;
    std::vector<std::string> actionFeatureLabels() const;
    int completedTurnsFor(std::string_view) const;
    int nationIncome(std::string_view) const;
    int nationTreasury(std::string_view) const;
    int unitCountFor(std::string_view) const;
    int unitValueFor(std::string_view) const;
    int enemyUnitValueDestroyedByNation(std::string_view) const;
    const campaign::Engine &engine() const { return *engine_; }
    void setDiceTapeForTesting(std::vector<int>);
    std::string serialize() const;
    void restore(const std::string &);
    void useSearchSeed(std::uint64_t);

  protected:
    campaign::State initial_;
    bool composition_{false};
    std::uint64_t seed_{1};
    std::shared_ptr<const campaign::Rules> rules_;
    std::optional<campaign::Engine> engine_;
    void resolvePendingChance();
};

} // namespace game
