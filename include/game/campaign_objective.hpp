#pragma once

#include "game/campaign.hpp"

#include <array>

namespace game::campaign {

inline const std::array<Id, 3> allianceOrder{"axis", "allies", "comintern"};

struct WealthComponents {
    double incomeRate{0};
    double units{0};
    double infrastructure{0};
    double treasury{0};
    double paidConstruction{0};
    double total() const;
};

// Shared static authority for native and resident-device wealth contexts.
void validateWealthDefinition(const Definition&);
int railAssetPrice(const State&, const RailState&);

// The approved M0 objective, in original IPP-like units. This is an evaluation
// of the current position, not an intermediate reward or a collection event.
std::array<WealthComponents, 3> allianceWealth(const State&);
std::array<double, 3> wealthGaps(const State&);
std::array<double, 3> terminalReturns(const State&);
json::Value wealthJson(const State&);

}  // namespace game::campaign
