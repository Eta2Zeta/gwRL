#pragma once

#include "game/campaign.hpp"

#include <array>
#include <cstdint>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace game::campaign {

// The neural network's view of one campaign decision, built directly from the
// engine state. It is the fixed-size, board-shaped description used by
// AlphaZero-style programs: every zone of the fixed map answers the same list
// of questions with integers ("how many undamaged Japanese infantry are here?"),
// the position as a whole answers a second list, and every legal option a
// third. Units are counted, never named. Most answers are zero, so only nonzero
// answers are stored: (zone, column, value) for zones, (column, value) for the
// position and for each option. The column lists are fixed for a scenario.
struct ZoneEncodingSpec {
    std::string version;  // Changes whenever any column list changes.
    std::vector<Id> zones;
    std::vector<Id> nations;
    std::vector<Id> unitTypes;
    std::vector<Id> facilityTypes;
    std::vector<Id> technologies;
    std::vector<Id> projectTypes;
    std::vector<Id> rows;
    int zoneColumns{0};
    int globalColumns{0};
    int actionColumns{0};
    // Fixed map facts, the same in every position: zones x staticFeatures.
    int staticFeatures{0};
    std::vector<float> zoneStatic;
    // Directed borders of the map and their fixed facts: edges x edgeFeatures.
    std::vector<std::int32_t> edgeSource;
    std::vector<std::int32_t> edgeTarget;
    int edgeFeatures{0};
    std::vector<float> edgeStatic;
    // Readable names, for tests and debugging only.
    std::vector<std::string> zoneColumnNames;
    std::vector<std::string> globalColumnNames;
    std::vector<std::string> actionColumnNames;
    std::vector<std::string> staticFeatureNames;
    std::vector<std::string> edgeFeatureNames;
};

// The scheduling layer around the engine's own decision: which alliance is
// choosing, whether an interrupt (such as a declaration of war) is on offer, and
// who has already passed on it.
struct ZoneSchedule {
    std::optional<Id> owner;
    std::string decisionKind;
    std::optional<Id> offered;
    std::vector<Id> passed;
    std::vector<Id> order;
};

struct ZoneOption {
    std::string kind;  // "play", "interrupt" or "pass_interrupt".
    Id player;
    const Action* action{nullptr};  // Absent only for a pass.
};

struct ZoneInput {
    std::vector<std::int32_t> zoneIndex, zoneColumn, zoneValue;
    std::vector<std::int32_t> globalColumn, globalValue;
    // Option i owns entries [actionOffsets[i], actionOffsets[i + 1]).
    std::vector<std::int32_t> actionOffsets{0}, actionColumn, actionValue;
    // The zone an option acts from and the zone it acts on, or -1.
    std::vector<std::int32_t> actionSource, actionTarget;
    // Zones an option's path passes through; option i owns [pathOffsets[i], pathOffsets[i + 1]).
    std::vector<std::int32_t> pathOffsets{0}, pathZone;
    // Policy groups, four per option: its kind, then what acts, how it travels
    // and what it acts on. Group ids are numbered per level from zero in order of
    // first appearance; options share a level's id exactly when they agree on
    // that level and every level before it.
    std::vector<std::int32_t> factorGroups;
    std::size_t actionCount() const { return actionSource.size(); }
    std::size_t bytes() const;
};

std::shared_ptr<const ZoneEncodingSpec> zoneEncodingSpec(const State&);
ZoneInput encodeZoneInput(const State&, const ZoneSchedule&, const std::vector<ZoneOption>&);
// Names that matched no column list and were counted in an "other" column,
// since the last reset. Tests and the completeness check read this.
std::map<std::string, long> zoneEncodingUnknowns(bool reset);

}  // namespace game::campaign
