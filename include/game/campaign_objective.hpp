#pragma once

#include "game/campaign.hpp"

#include <array>

namespace game::campaign {

inline const std::array<Id, 3> allianceOrder{"axis", "allies", "comintern"};

// The owner's weights since 22 November 2026: every land zone an alliance
// holds counts 1 and its income per turn counts on top; units, infrastructure,
// treasury and paid construction count a twentieth of their IPP, one weight for
// all four so that buying, building or repairing leaves wealth unchanged.
inline constexpr double landZoneWeight = 1;
inline constexpr double assetWeight = 0.05;

struct WealthComponents {
    double landZones{0};
    double incomeRate{0};
    double units{0};
    double infrastructure{0};
    double treasury{0};
    double paidConstruction{0};
    double total() const;
};

// The approved objective, in original IPP-like units. This is an evaluation
// of the current position, not an intermediate reward or a collection event.
std::array<WealthComponents, 3> allianceWealth(const State&);
std::array<double, 3> wealthGaps(const State&);
std::array<double, 3> terminalReturns(const State&);
json::Value wealthJson(const State&);

}  // namespace game::campaign
