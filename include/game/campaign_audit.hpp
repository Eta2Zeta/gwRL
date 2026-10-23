#pragma once

#include "game/campaign.hpp"
#include <functional>

namespace game::campaign {

// The authoritative module chain, shared by integration traces and public APIs.
std::shared_ptr<const Rules> campaignRules();

// Diagnostics supplement State::validate with domain checks. Pending combat and
// reactions are not mistaken for completed-phase landing/occupancy states.
std::vector<std::string> campaignInvariantFailures(const State &);
void requireCampaignInvariants(const State &);
json::Value campaignSnapshot(const State &);

class CampaignAuditLog {
  public:
    explicit CampaignAuditLog(const Engine &);
    void record(const State &before, const Engine &after, const std::string &inputKind,
                const json::Value &input);
    json::Value report(const Engine &) const;
    const std::vector<json::Value> &transitions() const { return transitions_; }

  private:
    std::string initialCheckpoint_;
    json::Value initialSnapshot_;
    std::set<Id> seenUnitIds_;
    std::vector<json::Value> transitions_;
};

struct CampaignTraceOptions {
    int maximumTransitions{6000};
    int optionalActionsPerPhase{8};
    std::uint64_t policySeed{1936};
    std::function<void(const State &, std::size_t)> progress;
    bool delayedJapaneseWar{false};
};

// A deterministic, deliberately non-optimal integration policy. Every choice
// comes from Engine::legalActions; it never writes gameplay state or dice.
void runCampaignTrace(Engine &, CampaignAuditLog &, const CampaignTraceOptions & = {});
void writeCampaignTrace(const std::filesystem::path &, const json::Value &report);

} // namespace game::campaign
