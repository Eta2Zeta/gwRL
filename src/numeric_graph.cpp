#include "game/numeric_graph.hpp"

#include <pybind11/numpy.h>

#include <array>
#include <bit>
#include <cmath>
#include <cstring>
#include <deque>
#include <limits>
#include <mutex>
#include <set>
#include <shared_mutex>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace py = pybind11;

namespace game::neural {
namespace {

enum Relation { ParentToChild, ChildToParent, IdentityReference, ReferenceBack, Adjacent };
enum Kind { Null, Bool, Number, String, Array, Object };
enum Path { OtherPath, RootPath, GeographyPath, GeographyNodesPath };

constexpr std::size_t LexicalCacheEntries = 131072;
constexpr std::size_t DescriptorCacheEntries = 131072;
constexpr std::size_t NumericCacheEntries = 32768;
constexpr std::size_t StringCacheBytes = 16 * 1024 * 1024;
constexpr std::size_t MaximumDepth = 1024;

std::int64_t indexValue(std::size_t value) {
    if (value > static_cast<std::size_t>(std::numeric_limits<std::int64_t>::max())) {
        throw std::overflow_error("Campaign neural graph exceeds int64 indexing");
    }
    return static_cast<std::int64_t>(value);
}

struct NumericKey {
    std::uint64_t numberBits;
    std::int64_t length;
    std::int64_t size;
    std::int64_t position;
    bool operator==(const NumericKey&) const = default;
};

struct NumericKeyHash {
    std::size_t operator()(const NumericKey& key) const {
        std::size_t hash = std::hash<std::uint64_t>{}(key.numberBits);
        for (const auto value : {key.length, key.size, key.position}) {
            hash ^= std::hash<std::int64_t>{}(value) + 0x9e3779b97f4a7c15ULL + (hash << 6) + (hash >> 2);
        }
        return hash;
    }
};

struct StringDescription {
    std::int64_t length;
    double number;
};

// FIFO bounds both entry count and retained source-string bytes. Hits do not
// mutate the cache, so simultaneous native traversals take shared locks only.
// An unusually large scalar is still encoded completely, but is not retained.
template <class Value>
struct StringCache {
    struct Entry {
        Value value;
        std::size_t bytes;
    };
    std::unordered_map<std::string, Entry> values;
    std::deque<std::string> order;
    std::size_t bytes = 0;

    void insert(const std::string& key, Value value, std::size_t valueBytes, std::size_t capacity) {
        const auto entryBytes = key.size() * 2 + valueBytes;
        if (entryBytes > StringCacheBytes || values.contains(key)) return;
        while (!order.empty() && (values.size() >= capacity || bytes + entryBytes > StringCacheBytes)) {
            const auto found = values.find(order.front());
            bytes -= found->second.bytes;
            values.erase(found);
            order.pop_front();
        }
        values.emplace(key, Entry{std::move(value), entryBytes});
        order.push_back(key);
        bytes += entryBytes;
    }

    void clear() {
        values.clear();
        order.clear();
        bytes = 0;
    }
};

bool entityCollection(const std::string& key) {
    for (const auto* name : {"nodes", "factions", "nations", "units", "territories", "facilities",
                             "construction", "repairs", "rails", "battles"}) {
        if (key == name) return true;
    }
    return false;
}

template <class Owner, class Value>
py::array_t<Value> arrayView(std::shared_ptr<const Owner> owner, const std::vector<Value>& values) {
    // Each view owns a shared reference independently of the Python graph or
    // compiler. It remains valid after either object is released.
    auto* retained = new std::shared_ptr<const Owner>(std::move(owner));
    py::capsule capsule(retained, [](void* value) {
        delete static_cast<std::shared_ptr<const Owner>*>(value);
    });
    py::array_t<Value> result({static_cast<py::ssize_t>(values.size())},
                             {static_cast<py::ssize_t>(sizeof(Value))}, values.data(), capsule);
    result.attr("setflags")(py::arg("write") = false);
    return result;
}

template <class Values>
py::tuple integerTuple(const Values& values) {
    py::tuple result(values.size());
    std::size_t index = 0;
    for (const auto value : values) result[index++] = py::int_(value);
    return result;
}

template <class Value>
std::vector<Value> packedArray(const py::dict& state, const char* key, int dimensions) {
    if (!state.contains(key) || !py::isinstance<py::array>(state[key])) {
        throw std::invalid_argument(std::string("Packed campaign graph requires NumPy array: ") + key);
    }
    const auto array = py::reinterpret_borrow<py::array>(state[key]);
    if (array.ndim() != dimensions || !array.dtype().equal(py::dtype::of<Value>())) {
        throw std::invalid_argument(std::string("Packed campaign graph array has incorrect shape or dtype: ") + key);
    }
    const auto contiguous = py::array_t<Value, py::array::c_style>::ensure(array);
    if (!contiguous) throw std::invalid_argument(std::string("Invalid packed campaign graph array: ") + key);
    std::vector<Value> result(static_cast<std::size_t>(contiguous.size()));
    if (!result.empty()) std::memcpy(result.data(), contiguous.data(), result.size() * sizeof(Value));
    return result;
}

}  // namespace

struct NumericGraphData {
    struct Reference {
        std::int64_t source;
        std::string identity;
    };
    struct Identity {
        std::string name;
        std::set<std::int64_t> nodes;
    };
    std::vector<std::int64_t> tokenIds;
    std::vector<std::int64_t> tokenOffsets;
    std::vector<std::int64_t> types;
    std::vector<double> numeric;
    std::vector<std::int64_t> sources;
    std::vector<std::int64_t> targets;
    std::vector<std::int64_t> relations;
    std::vector<Reference> references;
    std::vector<Identity> identities;
    std::unordered_map<std::string, std::size_t> identityLookup;
    std::size_t leaves = 0;
    std::int64_t buckets = 0;

    void addEdge(std::int64_t source, std::int64_t target, std::int64_t relation) {
        sources.push_back(source);
        targets.push_back(target);
        relations.push_back(relation);
    }

    void bind(const std::string& identity, std::int64_t index) {
        const auto [found, inserted] = identityLookup.emplace(identity, identities.size());
        if (inserted) identities.push_back({identity, {}});
        identities[found->second].nodes.insert(index);
    }
};

struct NumericGraphCompiler::Impl {
    Impl(std::int64_t bucketCount, py::function lexical, py::function descriptor, py::function numeric)
        : buckets(bucketCount), lexicalIds(std::move(lexical)),
          stringDescriptor(std::move(descriptor)), numericFeatures(std::move(numeric)) {}

    void addTokens(const std::string& text, bool value, std::vector<std::int64_t>& output) {
        auto& cache = value ? valueTokens : fieldTokens;
        {
            std::shared_lock lock(cacheMutex);
            const auto found = cache.values.find(text);
            if (found != cache.values.end()) {
                const auto& tokens = found->second.value;
                output.insert(output.end(), tokens.begin(), tokens.end());
                return;
            }
        }
        std::vector<std::int64_t> encoded;
        {
            py::gil_scoped_acquire gil;
            const auto found = lexicalIds(py::str(text), value ? "value" : "field", buckets);
            const auto sequence = py::reinterpret_steal<py::object>(PySequence_Tuple(found.ptr()));
            if (!sequence) throw py::error_already_set();
            const auto count = PyTuple_GET_SIZE(sequence.ptr());
            encoded.reserve(static_cast<std::size_t>(count));
            for (py::ssize_t index = 0; index < count; ++index) {
                encoded.push_back(py::cast<std::int64_t>(py::handle(PyTuple_GET_ITEM(sequence.ptr(), index))));
            }
        }
        output.insert(output.end(), encoded.begin(), encoded.end());
        const auto encodedBytes = encoded.size() * sizeof(std::int64_t);
        std::unique_lock lock(cacheMutex);
        cache.insert(text, std::move(encoded), encodedBytes, LexicalCacheEntries);
    }

    StringDescription describe(const std::string& text) {
        {
            std::shared_lock lock(cacheMutex);
            const auto found = stringDescriptions.values.find(text);
            if (found != stringDescriptions.values.end()) return found->second.value;
        }
        StringDescription encoded;
        {
            py::gil_scoped_acquire gil;
            const auto value = stringDescriptor(py::str(text));
            if (!PyTuple_Check(value.ptr()) || PyTuple_GET_SIZE(value.ptr()) != 2) {
                throw py::type_error("String descriptor must return (UTF-8 length, numeric value)");
            }
            encoded = {py::cast<std::int64_t>(value[py::int_(0)]), py::cast<double>(value[py::int_(1)])};
        }
        std::unique_lock lock(cacheMutex);
        stringDescriptions.insert(text, encoded, sizeof(encoded), DescriptorCacheEntries);
        return encoded;
    }

    std::array<double, 8> numbers(double number, std::int64_t length,
                                  std::int64_t size, std::int64_t position) {
        // Float equality alone loses the distinction between -0.0 and +0.0.
        const NumericKey key{std::bit_cast<std::uint64_t>(number), length, size, position};
        {
            std::shared_lock lock(cacheMutex);
            const auto found = numericCache.find(key);
            if (found != numericCache.end()) return found->second;
        }
        std::array<double, 8> encoded;
        {
            py::gil_scoped_acquire gil;
            const auto value = numericFeatures(number, length, size, position);
            if (!PyTuple_Check(value.ptr()) || PyTuple_GET_SIZE(value.ptr()) != 8) {
                throw py::type_error("Numeric features must return an eight-value tuple");
            }
            for (std::size_t index = 0; index < encoded.size(); ++index) {
                encoded[index] = py::cast<double>(py::handle(PyTuple_GET_ITEM(value.ptr(), index)));
            }
        }
        std::unique_lock lock(cacheMutex);
        if (!numericCache.contains(key)) {
            if (numericCache.size() >= NumericCacheEntries) {
                numericCache.erase(numericOrder.front());
                numericOrder.pop_front();
            }
            numericCache.emplace(key, encoded);
            numericOrder.push_back(key);
        }
        return encoded;
    }

    struct Builder {
        explicit Builder(Impl& scalarCompiler) : compiler(scalarCompiler), graph(std::make_shared<NumericGraphData>()) {
            graph->buckets = compiler.buckets;
        }

        std::shared_ptr<const NumericGraphData> run(const json::Value& value,
                                                   const json::Value::Object* rootOverrides = nullptr) {
            graph->tokenOffsets.push_back(0);
            visit(value, "$", 0, RootPath, 0, rootOverrides);
            for (const auto& reference : graph->references) {
                const auto found = graph->identityLookup.find(reference.identity);
                if (found == graph->identityLookup.end()) continue;
                for (const auto target : graph->identities[found->second].nodes) {
                    if (reference.source != target) {
                        graph->addEdge(target, reference.source, IdentityReference);
                        graph->addEdge(reference.source, target, ReferenceBack);
                    }
                }
            }
            addAdjacency(value, rootOverrides);
            return std::move(graph);
        }

        std::int64_t visit(const json::Value& value, const std::string& key,
                           std::int64_t position, Path path, std::size_t depth,
                           const json::Value::Object* rootOverrides = nullptr) {
            if (depth >= MaximumDepth) throw std::runtime_error("Campaign neural JSON nesting exceeds 1024 levels");
            if (rootOverrides && !value.isObject()) throw std::invalid_argument("Campaign neural root overrides require an object");
            const auto index = indexValue(graph->types.size());
            double number = 0;
            std::int64_t length = 0;
            std::int64_t size = 0;
            Kind kind;
            compiler.addTokens(key, false, graph->tokenIds);
            if (value.isNull()) {
                kind = Null;
            } else if (value.isBool()) {
                kind = Bool;
                number = value.asBool() ? 1 : 0;
            } else if (value.isNumber()) {
                kind = Number;
                number = value.asNumber();
                if (!std::isfinite(number)) throw std::invalid_argument("Neural features require finite JSON numbers");
            } else if (value.isString()) {
                kind = String;
                const auto& text = value.asString();
                const auto description = compiler.describe(text);
                length = description.length;
                number = description.number;
                compiler.addTokens(text, true, graph->tokenIds);
                graph->references.push_back({index, text});
            } else if (value.isArray()) {
                kind = Array;
                size = indexValue(value.asArray().size());
            } else {
                kind = Object;
                size = indexValue(value.asObject().size());
                if (rootOverrides) {
                    for (const auto& [field, ignored] : *rootOverrides) {
                        if (!value.asObject().contains(field)) ++size;
                    }
                }
            }
            graph->tokenOffsets.push_back(indexValue(graph->tokenIds.size()));
            graph->types.push_back(kind);
            const auto encoded = compiler.numbers(number, length, size, position);
            graph->numeric.insert(graph->numeric.end(), encoded.begin(), encoded.end());
            if (kind == Object) {
                const auto overriddenIdentity = rootOverrides ? rootOverrides->find("id") : json::Value::Object::const_iterator{};
                const auto* identity = rootOverrides && overriddenIdentity != rootOverrides->end()
                    ? &overriddenIdentity->second : value.find("id");
                if (identity && identity->isString()) {
                    graph->bind(identity->asString(), index);
                }
                const bool collection = entityCollection(key);
                // Native JSON objects use std::map. For valid UTF-8 this is the
                // same code-point order as sorted() in the feature oracle.
                const auto visitField = [&](const std::string& field, const json::Value& child) {
                    Path childPath = OtherPath;
                    if (path == RootPath && field == "geography") childPath = GeographyPath;
                    if (path == GeographyPath && field == "nodes") childPath = GeographyNodesPath;
                    const auto target = visit(child, field, 0, childPath, depth + 1);
                    graph->addEdge(index, target, ParentToChild);
                    graph->addEdge(target, index, ChildToParent);
                    if (collection && child.isObject()) graph->bind(field, target);
                    if (path == GeographyNodesPath) geographyNodes.emplace(field, target);
                };
                if (rootOverrides) {
                    // Merge root key pointers only. Large nested state and
                    // immutable context documents stay in their native owner.
                    std::map<std::string, const json::Value*> fields;
                    for (const auto& [field, child] : value.asObject()) fields.emplace(field, &child);
                    for (const auto& [field, child] : *rootOverrides) fields[field] = &child;
                    for (const auto& [field, child] : fields) visitField(field, *child);
                } else {
                    for (const auto& [field, child] : value.asObject()) visitField(field, child);
                }
            } else if (kind == Array) {
                std::int64_t offset = 0;
                for (const auto& child : value.asArray()) {
                    const auto target = visit(child, "[]", offset++, OtherPath, depth + 1);
                    graph->addEdge(index, target, ParentToChild);
                    graph->addEdge(target, index, ChildToParent);
                }
            } else {
                ++graph->leaves;
            }
            return index;
        }

        void addAdjacency(const json::Value& value, const json::Value::Object* rootOverrides) {
            if (!value.isObject()) return;
            const auto overriddenGeography = rootOverrides ? rootOverrides->find("geography") : json::Value::Object::const_iterator{};
            const auto* geography = rootOverrides && overriddenGeography != rootOverrides->end()
                ? &overriddenGeography->second : value.find("geography");
            if (!geography || !geography->isObject()) return;
            const auto* nodes = geography->find("nodes");
            if (!nodes) return;
            if (!nodes->isObject()) throw std::invalid_argument("Campaign geography.nodes must be an object");
            // Production JSON was already canonicalized before the old
            // compiler, including the insertion order used for adjacency.
            for (const auto& [identity, node] : nodes->asObject()) {
                if (!node.isObject()) continue;
                const auto source = geographyNodes.find(identity);
                const auto* neighbors = node.find("neighbors");
                if (!neighbors) continue;
                if (!neighbors->isArray()) throw std::invalid_argument("Campaign geography neighbors must be an array");
                for (const auto& neighbor : neighbors->asArray()) {
                    if (!neighbor.isObject()) throw std::invalid_argument("Campaign geography neighbor must be an object");
                    const auto* targetIdentity = neighbor.find("neighbor_id");
                    if (!targetIdentity || !targetIdentity->isString()) continue;
                    const auto target = geographyNodes.find(targetIdentity->asString());
                    if (source != geographyNodes.end() && target != geographyNodes.end()) {
                        graph->addEdge(source->second, target->second, Adjacent);
                    }
                }
            }
        }

        Impl& compiler;
        std::shared_ptr<NumericGraphData> graph;
        std::unordered_map<std::string, std::int64_t> geographyNodes;
    };

    std::int64_t buckets;
    py::function lexicalIds;
    py::function stringDescriptor;
    py::function numericFeatures;
    mutable std::shared_mutex cacheMutex;
    StringCache<std::vector<std::int64_t>> fieldTokens;
    StringCache<std::vector<std::int64_t>> valueTokens;
    StringCache<StringDescription> stringDescriptions;
    std::unordered_map<NumericKey, std::array<double, 8>, NumericKeyHash> numericCache;
    std::deque<NumericKey> numericOrder;
};

NumericGraph::NumericGraph(std::shared_ptr<const NumericGraphData> data) : data_(std::move(data)) {
    // Include vector capacities and the native reference index, not only the
    // exported ndarray lengths. Container-node overhead is a conservative
    // portable estimate; allocator bookkeeping is outside this accounting.
    std::size_t bytes = sizeof(NumericGraph) + sizeof(NumericGraphData);
    for (const auto* values : {&data_->tokenIds, &data_->tokenOffsets, &data_->types,
                               &data_->sources, &data_->targets, &data_->relations}) {
        bytes += values->capacity() * sizeof(std::int64_t);
    }
    bytes += data_->numeric.capacity() * sizeof(double);
    bytes += data_->references.capacity() * sizeof(NumericGraphData::Reference);
    for (const auto& reference : data_->references) bytes += reference.identity.capacity() + 1;
    bytes += data_->identities.capacity() * sizeof(NumericGraphData::Identity);
    for (const auto& identity : data_->identities) {
        bytes += identity.name.capacity() + 1;
        bytes += identity.nodes.size() * (sizeof(std::int64_t) + 4 * sizeof(void*));
    }
    bytes += data_->identityLookup.bucket_count() * sizeof(void*);
    for (const auto& [name, ignored] : data_->identityLookup) {
        bytes += sizeof(std::pair<const std::string, std::size_t>) + 2 * sizeof(void*) + name.capacity() + 1;
    }
    retainedBytes_ = bytes;
}

std::size_t NumericGraph::nodeCount() const { return data_->types.size(); }
std::size_t NumericGraph::leafCount() const { return data_->leaves; }
std::int64_t NumericGraph::bucketCount() const { return data_->buckets; }
std::size_t NumericGraph::retainedBytes() const { return retainedBytes_; }

bool NumericGraph::equals(const NumericGraph& other) const {
    if (data_ == other.data_) return true;
    const auto& a = *data_;
    const auto& b = *other.data_;
    if (a.buckets != b.buckets || a.leaves != b.leaves || a.tokenIds != b.tokenIds ||
        a.tokenOffsets != b.tokenOffsets || a.types != b.types || a.sources != b.sources ||
        a.targets != b.targets || a.relations != b.relations || a.numeric.size() != b.numeric.size() ||
        a.identities.size() != b.identities.size() || a.references.size() != b.references.size()) return false;
    if (!a.numeric.empty() && std::memcmp(a.numeric.data(), b.numeric.data(), a.numeric.size() * sizeof(double))) return false;
    for (const auto& identity : a.identities) {
        const auto found = b.identityLookup.find(identity.name);
        if (found == b.identityLookup.end() || identity.nodes != b.identities[found->second].nodes) return false;
    }
    for (std::size_t i = 0; i < a.references.size(); ++i)
        if (a.references[i].source != b.references[i].source || a.references[i].identity != b.references[i].identity) return false;
    return true;
}

py::dict NumericGraph::arrays() const {
    py::dict result;
    result["token_ids"] = arrayView(data_, data_->tokenIds);
    result["token_offsets"] = arrayView(data_, data_->tokenOffsets);
    result["types"] = arrayView(data_, data_->types);
    auto numeric = arrayView(data_, data_->numeric);
    result["numeric"] = numeric.attr("reshape")(nodeCount(), 8);
    result["sources"] = arrayView(data_, data_->sources);
    result["targets"] = arrayView(data_, data_->targets);
    result["relations"] = arrayView(data_, data_->relations);
    return result;
}

py::dict NumericGraph::debugGraph() const {
    py::dict result;
    result["token_ids"] = integerTuple(data_->tokenIds);
    result["token_offsets"] = integerTuple(data_->tokenOffsets);
    result["types"] = integerTuple(data_->types);
    py::tuple numbers(nodeCount());
    for (std::size_t index = 0; index < nodeCount(); ++index) {
        py::tuple row(8);
        for (std::size_t column = 0; column < 8; ++column) row[column] = py::float_(data_->numeric[index * 8 + column]);
        numbers[index] = std::move(row);
    }
    result["numeric"] = std::move(numbers);
    py::tuple edges(data_->sources.size());
    for (std::size_t index = 0; index < data_->sources.size(); ++index) {
        edges[index] = py::make_tuple(data_->sources[index], data_->targets[index], data_->relations[index]);
    }
    result["edges"] = std::move(edges);
    py::dict identities;
    for (const auto& identity : data_->identities) identities[py::str(identity.name)] = integerTuple(identity.nodes);
    result["identities"] = std::move(identities);
    py::tuple references(data_->references.size());
    for (std::size_t index = 0; index < data_->references.size(); ++index) {
        const auto& reference = data_->references[index];
        references[index] = py::make_tuple(reference.source, py::str(reference.identity));
    }
    result["references"] = std::move(references);
    result["leaf_count"] = py::int_(leafCount());
    return result;
}

py::dict NumericGraph::packedState() const {
    auto result = arrays();
    result["schema"] = "campaign-numeric-graph-v1";
    result["buckets"] = data_->buckets;
    py::dict identities;
    for (const auto& identity : data_->identities) identities[py::str(identity.name)] = integerTuple(identity.nodes);
    result["identities"] = std::move(identities);
    py::tuple references(data_->references.size());
    for (std::size_t index = 0; index < data_->references.size(); ++index) {
        const auto& reference = data_->references[index];
        references[index] = py::make_tuple(reference.source, py::str(reference.identity));
    }
    result["references"] = std::move(references);
    result["leaf_count"] = py::int_(leafCount());
    return result;
}

std::shared_ptr<NumericGraph> NumericGraph::fromPacked(const py::dict& state) {
    constexpr std::array<const char*, 12> fields{
        "token_ids", "token_offsets", "types", "numeric", "sources", "targets", "relations",
        "schema", "buckets", "identities", "references", "leaf_count"};
    if (state.size() != fields.size()) throw std::invalid_argument("Packed campaign graph has missing or unknown fields");
    for (const auto* field : fields) {
        if (!state.contains(field)) throw std::invalid_argument("Packed campaign graph has missing or unknown fields");
    }
    if (!py::isinstance<py::str>(state["schema"]) || py::cast<std::string>(state["schema"]) != "campaign-numeric-graph-v1") {
        throw std::invalid_argument("Unsupported packed campaign graph schema");
    }
    if (!PyLong_CheckExact(state["buckets"].ptr()) || !PyLong_CheckExact(state["leaf_count"].ptr())) {
        throw std::invalid_argument("Packed campaign graph vocabulary and leaf count must be integers");
    }
    auto data = std::make_shared<NumericGraphData>();
    data->buckets = py::cast<std::int64_t>(state["buckets"]);
    if (data->buckets < 2) throw std::invalid_argument("Packed campaign graph has invalid lexical vocabulary");
    data->tokenIds = packedArray<std::int64_t>(state, "token_ids", 1);
    data->tokenOffsets = packedArray<std::int64_t>(state, "token_offsets", 1);
    data->types = packedArray<std::int64_t>(state, "types", 1);
    data->numeric = packedArray<double>(state, "numeric", 2);
    data->sources = packedArray<std::int64_t>(state, "sources", 1);
    data->targets = packedArray<std::int64_t>(state, "targets", 1);
    data->relations = packedArray<std::int64_t>(state, "relations", 1);
    const auto nodes = indexValue(data->types.size());
    const auto numericArray = py::reinterpret_borrow<py::array>(state["numeric"]);
    if (!nodes || numericArray.shape(0) != nodes || numericArray.shape(1) != 8) {
        throw std::invalid_argument("Packed campaign graph numeric array must be node_count by eight");
    }
    for (const auto number : data->numeric) {
        if (!std::isfinite(number)) throw std::invalid_argument("Packed campaign graph numeric features must be finite");
    }
    if (data->tokenOffsets.size() != data->types.size() + 1 || data->tokenOffsets.front() != 0 ||
        data->tokenOffsets.back() != indexValue(data->tokenIds.size())) {
        throw std::invalid_argument("Packed campaign graph has invalid token offsets");
    }
    for (std::size_t index = 1; index < data->tokenOffsets.size(); ++index) {
        if (data->tokenOffsets[index] < data->tokenOffsets[index - 1]) {
            throw std::invalid_argument("Packed campaign graph token offsets are not monotone");
        }
    }
    for (const auto token : data->tokenIds) {
        if (token < 0 || token >= data->buckets) throw std::invalid_argument("Packed campaign graph token exceeds lexical vocabulary");
    }
    std::size_t leaves = 0;
    std::vector<std::int64_t> strings;
    for (std::size_t index = 0; index < data->types.size(); ++index) {
        const auto kind = data->types[index];
        if (kind < Null || kind > Object) throw std::invalid_argument("Packed campaign graph has an invalid node type");
        if (kind < Array) ++leaves;
        if (kind == String) strings.push_back(indexValue(index));
    }
    const auto packedLeaves = py::cast<std::int64_t>(state["leaf_count"]);
    if (packedLeaves < 0 || static_cast<std::size_t>(packedLeaves) != leaves) {
        throw std::invalid_argument("Packed campaign graph has invalid leaf count");
    }
    data->leaves = leaves;
    if (data->sources.size() != data->targets.size() || data->sources.size() != data->relations.size()) {
        throw std::invalid_argument("Packed campaign graph edge arrays have different lengths");
    }
    for (std::size_t index = 0; index < data->sources.size(); ++index) {
        if (data->sources[index] < 0 || data->sources[index] >= nodes ||
            data->targets[index] < 0 || data->targets[index] >= nodes ||
            data->relations[index] < ParentToChild || data->relations[index] > Adjacent) {
            throw std::invalid_argument("Packed campaign graph has an invalid edge");
        }
    }
    if (!py::isinstance<py::dict>(state["identities"])) throw std::invalid_argument("Packed campaign graph identities must be a dictionary");
    const auto identities = py::reinterpret_borrow<py::dict>(state["identities"]);
    for (const auto item : identities) {
        if (!py::isinstance<py::str>(item.first)) throw std::invalid_argument("Packed campaign graph identity must be a string");
        if (!py::isinstance<py::tuple>(item.second)) throw std::invalid_argument("Packed campaign graph identity indices must be a tuple");
        const auto name = py::cast<std::string>(item.first);
        std::int64_t previous = -1;
        std::set<std::int64_t> indices;
        for (const auto value : py::reinterpret_borrow<py::iterable>(item.second)) {
            if (!PyLong_CheckExact(value.ptr())) throw std::invalid_argument("Packed campaign graph identity indices must be integers");
            const auto index = py::cast<std::int64_t>(value);
            if (index <= previous || index >= nodes || data->types[index] != Object) {
                throw std::invalid_argument("Packed campaign graph identity indices must be sorted unique object indices");
            }
            indices.insert(index);
            previous = index;
        }
        if (indices.empty()) throw std::invalid_argument("Packed campaign graph identity has no target");
        data->identityLookup.emplace(name, data->identities.size());
        data->identities.push_back({name, std::move(indices)});
    }
    if (!py::isinstance<py::tuple>(state["references"])) throw std::invalid_argument("Packed campaign graph references must be a tuple");
    const auto references = py::reinterpret_borrow<py::tuple>(state["references"]);
    if (references.size() != strings.size()) throw std::invalid_argument("Packed campaign graph references omit string nodes");
    for (std::size_t index = 0; index < references.size(); ++index) {
        if (!py::isinstance<py::tuple>(references[index])) throw std::invalid_argument("Packed campaign graph reference must be a tuple");
        const auto reference = py::reinterpret_borrow<py::tuple>(references[index]);
        if (reference.size() != 2 || !py::isinstance<py::str>(reference[1])) {
            throw std::invalid_argument("Packed campaign graph reference must contain a node index and string");
        }
        if (!PyLong_CheckExact(reference[0].ptr())) throw std::invalid_argument("Packed campaign graph reference index must be an integer");
        const auto source = py::cast<std::int64_t>(reference[0]);
        if (source != strings[index]) throw std::invalid_argument("Packed campaign graph references are not in string traversal order");
        data->references.push_back({source, py::cast<std::string>(reference[1])});
    }
    return std::shared_ptr<NumericGraph>(new NumericGraph(std::move(data)));
}

py::tuple NumericGraph::externalReferences(const NumericGraph& context) const {
    struct Pairs {
        std::vector<std::int64_t> destinations;
        std::vector<std::int64_t> indices;
    };
    auto pairs = std::make_shared<Pairs>();
    {
        py::gil_scoped_release release;
        for (const auto& reference : data_->references) {
            const auto found = context.data_->identityLookup.find(reference.identity);
            if (found == context.data_->identityLookup.end()) continue;
            const auto& indices = context.data_->identities[found->second].nodes;
            for (const auto index : indices) {
                pairs->destinations.push_back(reference.source);
                pairs->indices.push_back(index);
            }
        }
    }
    std::shared_ptr<const Pairs> immutable = std::move(pairs);
    return py::make_tuple(arrayView(immutable, immutable->destinations), arrayView(immutable, immutable->indices));
}

NumericGraphCompiler::NumericGraphCompiler(std::int64_t buckets, py::function lexicalIds,
                                         py::function stringDescriptor, py::function numericFeatures)
    : impl_(std::make_unique<Impl>(buckets, std::move(lexicalIds), std::move(stringDescriptor), std::move(numericFeatures))) {
    if (buckets < 2) throw std::invalid_argument("The lexical vocabulary needs at least two buckets");
}

NumericGraphCompiler::~NumericGraphCompiler() = default;

std::shared_ptr<NumericGraph> NumericGraphCompiler::compile(const json::Value& value) {
    // Callers may already have released the GIL while protecting the immutable
    // native decision snapshot. Acquire it only for cache-miss callbacks.
    if (PyGILState_Check()) {
        py::gil_scoped_release release;
        return std::shared_ptr<NumericGraph>(new NumericGraph(Impl::Builder(*impl_).run(value)));
    }
    return std::shared_ptr<NumericGraph>(new NumericGraph(Impl::Builder(*impl_).run(value)));
}

std::shared_ptr<NumericGraph> NumericGraphCompiler::compile(const json::Value& value,
                                                          const json::Value::Object& rootOverrides) {
    if (PyGILState_Check()) {
        py::gil_scoped_release release;
        return std::shared_ptr<NumericGraph>(new NumericGraph(Impl::Builder(*impl_).run(value, &rootOverrides)));
    }
    return std::shared_ptr<NumericGraph>(new NumericGraph(Impl::Builder(*impl_).run(value, &rootOverrides)));
}

std::int64_t NumericGraphCompiler::bucketCount() const { return impl_->buckets; }

void NumericGraphCompiler::clearCaches() {
    std::unique_lock lock(impl_->cacheMutex);
    impl_->fieldTokens.clear();
    impl_->valueTokens.clear();
    impl_->stringDescriptions.clear();
    impl_->numericCache.clear();
    impl_->numericOrder.clear();
}

py::dict NumericGraphCompiler::cacheStats() const {
    py::dict result;
    std::shared_lock lock(impl_->cacheMutex);
    result["field_tokens"] = impl_->fieldTokens.values.size();
    result["value_tokens"] = impl_->valueTokens.values.size();
    result["string_descriptors"] = impl_->stringDescriptions.values.size();
    result["numeric_features"] = impl_->numericCache.size();
    result["retained_string_bytes"] = impl_->fieldTokens.bytes + impl_->valueTokens.bytes + impl_->stringDescriptions.bytes;
    result["lexical_capacity"] = LexicalCacheEntries;
    result["descriptor_capacity"] = DescriptorCacheEntries;
    result["numeric_capacity"] = NumericCacheEntries;
    result["string_byte_capacity"] = StringCacheBytes * 3;
    return result;
}

}  // namespace game::neural
