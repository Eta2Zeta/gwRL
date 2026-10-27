#pragma once
#include "game/device_state.hpp"
#include "game/politics.hpp"
#include <array>

namespace game::campaign {
// Read-only access to the original anonymous recruitment services. Independent
// queries preserve their own lazy exceptions, even for ineligible factions.
struct RecruitmentQueryOracle {
    bool available {false},quietPlacement {false};
    int threshold {0};
    std::vector<Id> zones;
    std::vector<Action> choices,rolls;
    std::array<std::int64_t,5> errors{};
    std::array<std::string,5> messages;
};
RecruitmentQueryOracle recruitmentQueryOracle(const State&,const Id& minor);

struct RecruitmentContext {
    std::shared_ptr<const Definition> definition;
    std::string wireContextFingerprint;
    std::vector<Id> territories,navalTypes,offshoreIds;
    std::vector<std::int64_t> chineseHome,offshoreSteps;
    // [step,3]: offshoreIds index/-1, lazy exception class/message index.
    std::int64_t offshoreError {0},offshoreMessage {0};
    bool chineseHomePresent {false},catalogPresent {false};
    std::vector<std::string> messages{""};
    explicit RecruitmentContext(const Engine&);
};
}
