#pragma once
// Immutable raw possession-IPP/home data, independent of income eligibility.
#include "game/campaign.hpp"
#include <cstdint>
#include <memory>
#include <vector>

namespace game::campaign {
struct PoliticalFactsContext {
    std::shared_ptr<const Definition> definition;
    std::string wireContextFingerprint;
    std::vector<Id> territories,nations;
    // [T,3]: original ipp_value.asInt, exception class, message index.
    // Failures remain lazy until that territory is actually possessed/read.
    std::vector<std::int64_t> ipp;
    std::vector<std::int64_t> chineseHome;
    int homeError {0};
    std::int64_t homeMessage {-1};
    std::vector<std::string> messages;
    explicit PoliticalFactsContext(const Engine&);
};
} // namespace game::campaign
