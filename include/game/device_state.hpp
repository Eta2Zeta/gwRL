#pragma once
// Lossless direct-native state transport. These privileged snapshots include
// execution randomness; they are never neural observations or policy inputs.
#include "game/campaign.hpp"
#include <array>
#include <cstdint>
#include <memory>
#include <vector>

namespace game::campaign {
inline constexpr const char* deviceStateSchema = "campaign-device-state-v2";
inline constexpr std::size_t deviceStateColumns = 5;
using DeviceRecord = std::array<std::int64_t, deviceStateColumns>;

enum class DeviceTag : std::int64_t {
    Null, Boolean, SignedInteger, UnsignedInteger, NumberBits, String,
    Sequence, Map, Set, Optional, Record, Pair, JsonArray, JsonObject
};

struct DeviceStateContext {
    std::shared_ptr<const Definition> definition;
    std::shared_ptr<const Rules> rules;
    std::string definitionFingerprint, rulesId, wireContextFingerprint;
    std::map<std::string,std::int64_t> stringIds;
    std::vector<DeviceRecord> records;
    std::vector<std::string> strings;
    std::vector<std::uint8_t> stringBytes;
    std::vector<std::int64_t> stringOffsets;
    explicit DeviceStateContext(const Engine&);
    std::vector<std::int64_t> prefixLookupIds(const std::vector<std::string>&) const;
};

struct DeviceStateBatch {
    std::shared_ptr<const DeviceStateContext> context;
    // Nodes are contiguous; subtree_end is LOCAL to its lane. Optional null,
    // absent map entries, container order and every number bit remain distinct.
    std::vector<DeviceRecord> records;
    std::vector<std::int64_t> laneOffsets;
    // String IDs first address the context's immutable prefix, then this suffix.
    std::vector<std::string> strings;
    std::vector<std::uint8_t> stringBytes;
    std::vector<std::int64_t> stringOffsets;
    std::vector<std::int64_t> sections;
    std::size_t maxLaneRecords {0};
    explicit DeviceStateBatch(std::shared_ptr<const DeviceStateContext>);
    void append(const Engine&);
    std::size_t rows() const { return laneOffsets.size() - 1; }
    Engine restore(std::size_t lane) const;
    void validate() const;
    // Import contiguous buffers from an explicit host snapshot boundary.
    static DeviceStateBatch fromPacked(std::shared_ptr<const DeviceStateContext>,
        std::vector<DeviceRecord>, std::vector<std::int64_t> offsets,
        std::vector<std::uint8_t> bytes, std::vector<std::int64_t> stringOffsets,
        const std::string& expectedWireContextFingerprint);
    static const std::vector<std::string>& sectionNames();
};
} // namespace game::campaign
