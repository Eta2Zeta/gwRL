#pragma once

#include "game/simple_json.hpp"

#include <pybind11/pybind11.h>

#include <cstddef>
#include <cstdint>
#include <memory>

namespace game::neural {

struct NumericGraphData;

// An immutable graph of native JSON. The Python view contains contiguous
// numeric buffers rather than one Python object for every graph scalar.
class NumericGraph {
public:
    std::size_t nodeCount() const;
    std::size_t leafCount() const;
    std::size_t retainedBytes() const;
    std::int64_t bucketCount() const;
    pybind11::dict arrays() const;
    pybind11::dict debugGraph() const;
    pybind11::dict packedState() const;
    static std::shared_ptr<NumericGraph> fromPacked(const pybind11::dict& state);

    // Preserve the model's reference-first, sorted-identity-index ordering.
    // The returned arrays are (destination indices, context node indices).
    pybind11::tuple externalReferences(const NumericGraph& context) const;

private:
    explicit NumericGraph(std::shared_ptr<const NumericGraphData> data);
    std::shared_ptr<const NumericGraphData> data_;
    std::size_t retainedBytes_ = 0;
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

    std::shared_ptr<NumericGraph> compile(const json::Value& value);
    std::shared_ptr<NumericGraph> compile(const json::Value& value, const json::Value::Object& rootOverrides);
    std::int64_t bucketCount() const;
    void clearCaches();
    pybind11::dict cacheStats() const;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace game::neural
