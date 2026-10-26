#pragma once
// Immutable movement metadata and the original native validateRoute oracle.
#include "game/movement.hpp"
#include <cstdint>
#include <memory>
#include <vector>

namespace game::campaign {
struct MovementContext {
    std::shared_ptr<const Definition> definition;
    std::vector<Id> zones, nations, unitTypes, terrains, regions, facilityIds;
    // [Z,7]: land, city, region index/error/message, terrain error/message.
    std::vector<std::int64_t> nodes;
    // [Z,Z,20]: edge/passable/rail/river/narrow; crossing capacity/error/message;
    // approach river/known/error/message; base/built gauge value/error/message.
    // Final two fields preserve lazy passableLandBorder exceptions.
    std::vector<std::int64_t> edges;
    // Complete named terrain sets, bank/sea lists and Home Country membership.
    std::vector<std::int64_t> nodeTerrain, borderTerrain, riverBanks, crossingSeas, home;
    // [U,8]: classes land/naval/aircraft/rocket/infantry/surface/submarine/fighter.
    std::vector<std::int64_t> classes;
    // [Z,Z,3]: unknown bank or missing sea-list, exception/message.
    // [F,Z]: static fort borders; [F,2] lazy metadata exception/message.
    std::vector<std::int64_t> bankUnknown, crossingSeasMissing, fortBorders;
    std::vector<std::int64_t> fortErrors;
    // [R,3]: regional capacity, exception class/message index.
    std::vector<std::int64_t> capacities;
    // Full static counter keys, one directed-pair crossing key and player/region
    // rail key. A separate byte table avoids mutating the resident state pool.
    std::vector<std::uint8_t> counterBytes;
    std::vector<std::int64_t> counterOffsets, crossingCounter, crossingCounterErrors, railCounters;
    std::vector<Id> players;
    std::vector<std::string> exceptionMessages;
    explicit MovementContext(std::shared_ptr<const Definition>);
};
struct MovementQuery {
    std::int64_t lane {0};
    RouteRequest request;
};
struct MovementOracleResult {
    RouteResult result;
    int exception {0};
    std::string message;
};
} // namespace game::campaign
