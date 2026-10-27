#pragma once

#include "game/campaign.hpp"

namespace game::campaign {

inline constexpr char trainingActionSchema[] = "campaign-orders-v1";

// A versioned action interface for self-play. The ordinary campaignRules()
// retain the editable tabletop interface; completed game orders remain shared.
std::shared_ptr<const Rules> trainingCampaignRules();

// Restored interface metadata is complete observable source state. Reject
// unknown versions or malformed records before committing a restored engine.
void validateTrainingActionState(const State&);
// Exact existing reset operation, shared with the resident hook oracle.
void resetTrainingActionState(State&);

}  // namespace game::campaign
