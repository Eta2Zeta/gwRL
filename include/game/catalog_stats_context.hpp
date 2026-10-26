#pragma once
// Immutable primary-catalog tables and exact original-statistics oracle.
#include "game/catalog.hpp"
#include "game/device_state.hpp"
#include <cstdint>
#include <vector>

namespace game::campaign {
struct CatalogStatsContext {
    std::shared_ptr<const Definition> definition;
    std::string wireContextFingerprint,catalogFingerprint;
    std::vector<Id> strings,unitTypes,technologies,factions;
    std::vector<std::string> messages{""};
    std::int64_t lookupMessage {0};
    bool closedTheatre {false};
    // Tokens index strings, which is mapped to the state's immutable prefix once.
    std::vector<std::int64_t> unitTokens,technologyTokens,factionTokens,homeTokens;
    // [U,4] state offset/count, conditional instruction offset/count.
    // [S,19] damage, then presence/value for all nine CatalogStats members.
    std::vector<std::int64_t> units,states;
    // [N,3] Home Country known, token offset/count.
    std::vector<std::int64_t> home;
    // [K,4] modifier offset/count, lazy modifiers.asArray exception/message.
    std::vector<std::int64_t> technology;
    // [I,12] pre-exception/message, flags offset/count, flags-list exception/message,
    // add/assignment, lazy value exception/message, stat index, stat exception/message.
    std::vector<std::int64_t> conditionals,modifiers;
    // [M,U] exact union match of unit_types and classes, parsed once natively.
    std::vector<std::int64_t> matches;
    // [F,4] string token, derived flag kind, lazy flag-item exception/message.
    std::vector<std::int64_t> flags;
    explicit CatalogStatsContext(const Engine&);
};

struct CatalogStatsQuery {
    std::int64_t lane {0};
    Id type;
    int damage {0};
    Id owner;
    std::optional<Id> zone;
};
struct CatalogStatsOracle {
    // [Q,9,2] presence/value, including all three always-present dice members.
    std::vector<std::int64_t> stats,errors;
    std::vector<std::string> messages;
};
void appendCatalogStats(std::vector<std::int64_t>&,const CatalogStats&);
} // namespace game::campaign
