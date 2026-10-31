#pragma once

#include "game/campaign.hpp"

namespace game::campaign {

inline constexpr char trainingActionSchema[] = "campaign-orders-v2";

// A versioned action interface for self-play. The ordinary campaignRules()
// retain the editable tabletop interface; completed game orders remain shared.
// v2 clears finished battles itself instead of offering their clearing clicks.
std::shared_ptr<const Rules> trainingCampaignRules();

// Restored interface metadata is complete observable source state. Reject
// unknown versions or malformed records before committing a restored engine.
void validateTrainingActionState(const State&);

}  // namespace game::campaign
