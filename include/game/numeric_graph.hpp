#pragma once

#include "game/simple_json.hpp"

#include <pybind11/pybind11.h>

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <memory>
#include <string_view>
#include <vector>

namespace game::neural {

struct NumericGraphData;

// An immutable graph of native JSON. The Python view contains contiguous
// numeric buffers rather than one Python object for every graph scalar.
class NumericGraph {
public:
    std::size_t nodeCount() const;
    std::size_t leafCount() const;
    std::size_t retainedBytes() const;
    bool equals(const NumericGraph& other) const;
    std::int64_t bucketCount() const;
    pybind11::dict arrays() const;
    pybind11::dict debugGraph() const;
    pybind11::dict packedState() const;
    static std::shared_ptr<NumericGraph> fromPacked(const pybind11::dict& state);
    // An equal graph with no spare capacity, for retaining an observation.
    std::shared_ptr<NumericGraph> compacted() const;

    // Preserve the model's reference-first, sorted-identity-index ordering.
    // The returned arrays are (destination indices, context node indices).
    pybind11::tuple externalReferences(const NumericGraph& context) const;

    // Writes one evaluation's whole network input into a caller's buffer, as
    // int32 and float32 arrays: this observation and its references into the
    // context, then the menu's graphs joined as one block, as the model's
    // encoder joins them, with their references and policy factor levels.
    // Returns each array's (name, dtype, shape, offset). The work is short
    // enough to keep the GIL rather than hand it over and wait to get it back.
    pybind11::list writeEvaluation(const pybind11::buffer& buffer, const NumericGraph& context,
                                   const std::vector<std::reference_wrapper<const NumericGraph>>& actions,
                                   const std::vector<std::array<std::string_view, 4>>& factors) const;

private:
    explicit NumericGraph(std::shared_ptr<const NumericGraphData> data);
    std::shared_ptr<const NumericGraphData> data_;
    friend class NumericGraphCompiler;
};

// A compiler belongs to one feature configuration. Its bounded caches contain
// only immutable scalar encodings, never engine state or learned tensors.
// Traversal runs without the GIL; a cold scalar encoding acquires it only while
// calling the supplied Python feature oracle. Native JSON must remain immutable
// throughout compile(), as it does for cached campaign decision snapshots.
class NumericGraphCompiler {
public:
    NumericGraphCompiler(std::int64_t buckets,
                         pybind11::function lexicalIds,
                         pybind11::function stringDescriptor,
                         pybind11::function numericFeatures);
    ~NumericGraphCompiler();
    NumericGraphCompiler(const NumericGraphCompiler&) = delete;
    NumericGraphCompiler& operator=(const NumericGraphCompiler&) = delete;

    // The menu's elements replace a root legal_actions override, without being copied into it.
    using Menu = std::vector<std::shared_ptr<const json::Value>>;

    std::shared_ptr<NumericGraph> compile(const json::Value& value);
    std::shared_ptr<NumericGraph> compile(const json::Value& value, const json::Value::Object& rootOverrides,
                                          const Menu& menu);
    std::int64_t bucketCount() const;
    void clearCaches();
    pybind11::dict cacheStats() const;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace game::neural
