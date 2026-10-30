#include "game/numeric_graph.hpp"

#include <pybind11/numpy.h>

#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstring>
#include <deque>
#include <limits>
#include <mutex>
#include <numeric>
#include <stdexcept>
#include <string>
#include <type_traits>
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
constexpr std::size_t NumericCacheEntries = 32768;
constexpr std::size_t StringCacheBytes = 16 * 1024 * 1024;
constexpr std::size_t CacheSets = 8;
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

struct FieldEncoding {
    std::vector<std::int64_t> tokens;
    bool collection = false;
};

struct ValueEncoding {
    std::vector<std::int64_t> tokens;
    std::int64_t length = 0;
    double number = 0;
};

// FIFO bounds both entry count and retained source-string bytes. An unusually
// large scalar is still encoded completely, but is not retained.
template <class Value>
struct StringCache {
    struct Entry {
        Value value;
        std::size_t bytes;
    };
    std::unordered_map<std::string, Entry> values;
    std::deque<std::string> order;
    std::size_t bytes = 0;
    Value unretained;

    const Value& insert(const std::string& key, Value value, std::size_t valueBytes, std::size_t capacity) {
        const auto entryBytes = key.size() * 2 + valueBytes;
        if (entryBytes > StringCacheBytes) return unretained = std::move(value);
        while (!order.empty() && (values.size() >= capacity || bytes + entryBytes > StringCacheBytes)) {
            const auto found = values.find(order.front());
            bytes -= found->second.bytes;
            values.erase(found);
            order.pop_front();
        }
        order.push_back(key);
        bytes += entryBytes;
        return values.emplace(key, Entry{std::move(value), entryBytes}).first->second.value;
    }
};

// One compile's scalar encodings. A compile owns its set from start to finish
// and no other thread can reach it, so lookups take no lock. Threads compiling
// at the same time use different sets, which fill independently.
struct ScalarCaches {
    explicit ScalarCaches(std::uint64_t currentGeneration) : generation(currentGeneration) {}
    std::uint64_t generation;
    StringCache<FieldEncoding> fields;
    StringCache<ValueEncoding> values;
    std::unordered_map<NumericKey, std::array<double, 8>, NumericKeyHash> numeric;
    std::deque<NumericKey> numericOrder;
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
        std::vector<std::int64_t> nodes;  // Sorted and unique.
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

    void clear() {
        tokenIds.clear();
        tokenOffsets.clear();
        types.clear();
        numeric.clear();
        sources.clear();
        targets.clear();
        relations.clear();
        references.clear();
        identities.clear();
        identityLookup.clear();
        leaves = 0;
    }

    void compact() {
        tokenIds.shrink_to_fit();
        tokenOffsets.shrink_to_fit();
        types.shrink_to_fit();
        numeric.shrink_to_fit();
        sources.shrink_to_fit();
        targets.shrink_to_fit();
        relations.shrink_to_fit();
        references.shrink_to_fit();
        identities.shrink_to_fit();
        for (auto& identity : identities) identity.nodes.shrink_to_fit();
    }

    void addTokens(const std::vector<std::int64_t>& tokens) {
        for (const auto token : tokens) tokenIds.push_back(token);
    }

    void addEdge(std::int64_t source, std::int64_t target, std::int64_t relation) {
        sources.push_back(source);
        targets.push_back(target);
        relations.push_back(relation);
    }

    void bind(const std::string& identity, std::int64_t index) {
        const auto [found, inserted] = identityLookup.try_emplace(identity, identities.size());
        if (inserted) identities.push_back({identity, {}});
        auto& nodes = identities[found->second].nodes;
        const auto position = std::lower_bound(nodes.begin(), nodes.end(), index);
        if (position == nodes.end() || *position != index) nodes.insert(position, index);
    }
};

// Finished observation graphs, kept to reuse their arrays. Freeing a large vector
// hands its pages to the kernel and the next graph faults them in again, and growing
// one copies it. A graph lands here only when its last owner lets go, so whoever
// takes it from here owns it alone.
struct SpareGraphs {
    std::mutex mutex;
    std::vector<std::unique_ptr<NumericGraphData>> graphs;

    static std::shared_ptr<NumericGraphData> take(const std::shared_ptr<SpareGraphs>& spares) {
        std::unique_ptr<NumericGraphData> graph;
        {
            std::lock_guard lock(spares->mutex);
            if (!spares->graphs.empty()) {
                graph = std::move(spares->graphs.back());
                spares->graphs.pop_back();
            }
        }
        if (!graph) graph = std::make_unique<NumericGraphData>();
        return {graph.release(), [spares](NumericGraphData* finished) {
            std::unique_ptr<NumericGraphData> owned(finished);
            owned->clear();
            std::lock_guard lock(spares->mutex);
            if (spares->graphs.size() < CacheSets) spares->graphs.push_back(std::move(owned));
        }};
    }
};

struct NumericGraphCompiler::Impl {
    Impl(std::int64_t bucketCount, py::function lexical, py::function descriptor, py::function numeric)
        : buckets(bucketCount), lexicalIds(std::move(lexical)),
          stringDescriptor(std::move(descriptor)), numericFeatures(std::move(numeric)) {}

    std::unique_ptr<ScalarCaches> checkOut() {
        std::lock_guard lock(poolMutex);
        if (pool.empty()) return std::make_unique<ScalarCaches>(generation);
        auto caches = std::move(pool.back());
        pool.pop_back();
        return caches;
    }

    void checkIn(std::unique_ptr<ScalarCaches> caches) {
        std::lock_guard lock(poolMutex);
        if (caches->generation == generation && pool.size() < CacheSets) pool.push_back(std::move(caches));
    }

    std::vector<std::int64_t> lexical(const std::string& text, const char* role) {
        const auto found = lexicalIds(py::str(text), role, buckets);
        const auto sequence = py::reinterpret_steal<py::object>(PySequence_Tuple(found.ptr()));
        if (!sequence) throw py::error_already_set();
        const auto count = PyTuple_GET_SIZE(sequence.ptr());
        std::vector<std::int64_t> encoded;
        encoded.reserve(static_cast<std::size_t>(count));
        for (py::ssize_t index = 0; index < count; ++index) {
            encoded.push_back(py::cast<std::int64_t>(py::handle(PyTuple_GET_ITEM(sequence.ptr(), index))));
        }
        return encoded;
    }

    const FieldEncoding& field(ScalarCaches& caches, const std::string& text) {
        const auto found = caches.fields.values.find(text);
        if (found != caches.fields.values.end()) return found->second.value;
        FieldEncoding encoded;
        {
            py::gil_scoped_acquire gil;
            encoded.tokens = lexical(text, "field");
        }
        encoded.collection = entityCollection(text);
        const auto encodedBytes = encoded.tokens.size() * sizeof(std::int64_t);
        return caches.fields.insert(text, std::move(encoded), encodedBytes, LexicalCacheEntries);
    }

    const ValueEncoding& value(ScalarCaches& caches, const std::string& text) {
        const auto found = caches.values.values.find(text);
        if (found != caches.values.values.end()) return found->second.value;
        ValueEncoding encoded;
        {
            py::gil_scoped_acquire gil;
            const auto description = stringDescriptor(py::str(text));
            if (!PyTuple_Check(description.ptr()) || PyTuple_GET_SIZE(description.ptr()) != 2) {
                throw py::type_error("String descriptor must return (UTF-8 length, numeric value)");
            }
            encoded.length = py::cast<std::int64_t>(description[py::int_(0)]);
            encoded.number = py::cast<double>(description[py::int_(1)]);
            encoded.tokens = lexical(text, "value");
        }
        const auto encodedBytes = encoded.tokens.size() * sizeof(std::int64_t) + sizeof(ValueEncoding);
        return caches.values.insert(text, std::move(encoded), encodedBytes, LexicalCacheEntries);
    }

    const std::array<double, 8>& numbers(ScalarCaches& caches, double number, std::int64_t length,
                                         std::int64_t size, std::int64_t position) {
        // Float equality alone loses the distinction between -0.0 and +0.0.
        const NumericKey key{std::bit_cast<std::uint64_t>(number), length, size, position};
        const auto found = caches.numeric.find(key);
        if (found != caches.numeric.end()) return found->second;
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
        if (caches.numeric.size() >= NumericCacheEntries) {
            caches.numeric.erase(caches.numericOrder.front());
            caches.numericOrder.pop_front();
        }
        caches.numericOrder.push_back(key);
        return caches.numeric.emplace(key, encoded).first->second;
    }

    struct Builder {
        explicit Builder(Impl& scalarCompiler)
            : compiler(scalarCompiler), caches(compiler.checkOut()) {}

        ~Builder() { compiler.checkIn(std::move(caches)); }

        std::shared_ptr<const NumericGraphData> run(const json::Value& value,
                                                   const json::Value::Object* rootOverrides = nullptr,
                                                   const NumericGraphCompiler::Menu* menu = nullptr) {
            const bool observation = rootOverrides && rootOverrides->contains("legal_actions");
            scheduledMenu = observation ? menu : nullptr;
            graph = observation ? SpareGraphs::take(compiler.spares) : std::make_shared<NumericGraphData>();
            graph->buckets = compiler.buckets;
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
            // Published graphs are immutable. Actions and contexts are cached for
            // the run, so they keep no append-growth capacity. Most observations
            // die within a simulation; a caller retaining one takes compacted().
            if (!observation) graph->compact();
            return std::move(graph);
        }

        std::int64_t visit(const json::Value& value, const std::string& key,
                           std::int64_t position, Path path, std::size_t depth,
                           const json::Value::Object* rootOverrides = nullptr,
                           const NumericGraphCompiler::Menu* elements = nullptr) {
            if (depth >= MaximumDepth) throw std::runtime_error("Campaign neural JSON nesting exceeds 1024 levels");
            if (rootOverrides && !value.isObject()) throw std::invalid_argument("Campaign neural root overrides require an object");
            const auto index = indexValue(graph->types.size());
            double number = 0;
            std::int64_t length = 0;
            std::int64_t size = 0;
            Kind kind;
            const auto& field = compiler.field(*caches, key);
            const bool collection = field.collection;
            graph->addTokens(field.tokens);
            if (value.isNull()) {
                kind = Null;
            } else if (value.isBool()) {
                kind = Bool;
                number = value.asBool() ? 1 : 0;
            } else if (value.isNumber()) {
                kind = Number;
                number = value.asNumber();
                // Public native JSON canonicalizes numeric -0.0 to 0. Retain
                // that established feature spelling without text round trips.
                if (number == 0) number = 0.0;
                if (!std::isfinite(number)) throw std::invalid_argument("Neural features require finite JSON numbers");
            } else if (value.isString()) {
                kind = String;
                const auto& text = value.asString();
                const auto& encoded = compiler.value(*caches, text);
                length = encoded.length;
                number = encoded.number;
                graph->addTokens(encoded.tokens);
                graph->references.push_back({index, text});
            } else if (value.isArray()) {
                kind = Array;
                size = indexValue(elements ? elements->size() : value.asArray().size());
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
            const auto& encoded = compiler.numbers(*caches, number, length, size, position);
            graph->numeric.insert(graph->numeric.end(), encoded.begin(), encoded.end());
            if (kind == Object) {
                const auto overriddenIdentity = rootOverrides ? rootOverrides->find("id") : json::Value::Object::const_iterator{};
                const auto* identity = rootOverrides && overriddenIdentity != rootOverrides->end()
                    ? &overriddenIdentity->second : value.find("id");
                if (identity && identity->isString()) {
                    graph->bind(identity->asString(), index);
                }
                // Native JSON objects use std::map. For valid UTF-8 this is the
                // same code-point order as sorted() in the feature oracle.
                const auto visitField = [&](const std::string& field, const json::Value& child) {
                    Path childPath = OtherPath;
                    if (path == RootPath && field == "geography") childPath = GeographyPath;
                    if (path == GeographyPath && field == "nodes") childPath = GeographyNodesPath;
                    const auto target = visit(child, field, 0, childPath, depth + 1, nullptr,
                                              rootOverrides && field == "legal_actions" ? scheduledMenu : nullptr);
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
                const auto visitElement = [&](const json::Value& child) {
                    const auto target = visit(child, "[]", offset++, OtherPath, depth + 1);
                    graph->addEdge(index, target, ParentToChild);
                    graph->addEdge(target, index, ChildToParent);
                };
                if (elements) {
                    for (const auto& child : *elements) visitElement(*child);
                } else {
                    for (const auto& child : value.asArray()) visitElement(child);
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
        std::unique_ptr<ScalarCaches> caches;
        std::shared_ptr<NumericGraphData> graph;
        std::unordered_map<std::string, std::int64_t> geographyNodes;
        const NumericGraphCompiler::Menu* scheduledMenu = nullptr;
    };

    std::int64_t buckets;
    py::function lexicalIds;
    py::function stringDescriptor;
    py::function numericFeatures;
    mutable std::mutex poolMutex;
    std::vector<std::unique_ptr<ScalarCaches>> pool;
    std::uint64_t generation = 0;
    std::shared_ptr<SpareGraphs> spares = std::make_shared<SpareGraphs>();
};

NumericGraph::NumericGraph(std::shared_ptr<const NumericGraphData> data) : data_(std::move(data)) {}

std::shared_ptr<NumericGraph> NumericGraph::compacted() const {
    return std::shared_ptr<NumericGraph>(new NumericGraph(std::make_shared<NumericGraphData>(*data_)));
}

std::size_t NumericGraph::nodeCount() const { return data_->types.size(); }
std::size_t NumericGraph::leafCount() const { return data_->leaves; }
std::int64_t NumericGraph::bucketCount() const { return data_->buckets; }

std::size_t NumericGraph::retainedBytes() const {
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
        bytes += identity.nodes.capacity() * sizeof(std::int64_t);
    }
    bytes += data_->identityLookup.bucket_count() * sizeof(void*);
    for (const auto& [name, ignored] : data_->identityLookup) {
        bytes += sizeof(std::pair<const std::string, std::size_t>) + 2 * sizeof(void*) + name.capacity() + 1;
    }
    return bytes;
}

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
        std::vector<std::int64_t> indices;
        for (const auto value : py::reinterpret_borrow<py::iterable>(item.second)) {
            if (!PyLong_CheckExact(value.ptr())) throw std::invalid_argument("Packed campaign graph identity indices must be integers");
            const auto index = py::cast<std::int64_t>(value);
            if (index <= previous || index >= nodes || data->types[index] != Object) {
                throw std::invalid_argument("Packed campaign graph identity indices must be sorted unique object indices");
            }
            indices.push_back(index);
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
    data->compact();
    return std::shared_ptr<NumericGraph>(new NumericGraph(std::move(data)));
}

namespace {

template <class Visit>
void forEachReference(const NumericGraphData& graph, const NumericGraphData& bank, Visit&& visit) {
    for (const auto& reference : graph.references) {
        const auto found = bank.identityLookup.find(reference.identity);
        if (found == bank.identityLookup.end()) continue;
        for (const auto index : bank.identities[found->second].nodes) visit(reference.source, index);
    }
}

// An evaluation's arrays laid out in a caller's buffer, as read_arrays reads them.
class EvaluationWriter {
public:
    explicit EvaluationWriter(const py::buffer& buffer) : view_(buffer.request(true)) {
        // The arrays are written straight through the pointer, so the buffer must
        // be one run of bytes starting where an int32 or float32 can be stored.
        if (view_.ndim != 1 || view_.strides[0] != view_.itemsize ||
            reinterpret_cast<std::uintptr_t>(view_.ptr) % alignof(std::int32_t) != 0) {
            throw py::buffer_error("Evaluation arrays need a contiguous, aligned buffer");
        }
    }

    template <class Value>
    Value* array(const std::string& name, std::size_t rows, std::size_t columns = 0) {
        const auto start = (end_ + 15) & ~std::size_t{15};
        end_ = start + rows * std::max<std::size_t>(columns, 1) * sizeof(Value);
        if (end_ > static_cast<std::size_t>(view_.size * view_.itemsize)) {
            throw std::invalid_argument("A prepared position exceeds its shared-memory buffer");
        }
        py::tuple shape = columns ? py::tuple(py::make_tuple(rows, columns)) : py::tuple(py::make_tuple(rows));
        header_.append(py::make_tuple(name, std::is_same_v<Value, float> ? "<f4" : "<i4", shape, start));
        return reinterpret_cast<Value*>(static_cast<char*>(view_.ptr) + start);
    }

    py::list header() const { return header_; }

private:
    py::buffer_info view_;
    std::size_t end_ = 0;
    py::list header_;
};

// Copies values narrowed to the model's array type; returns the end.
template <class Source, class Target>
Target* narrowed(const std::vector<Source>& values, Target* out) {
    for (std::size_t index = 0; index < values.size(); ++index) out[index] = static_cast<Target>(values[index]);
    return out + values.size();
}

// The same for node or token indices, moved past a block's earlier graphs.
std::int32_t* shifted(const std::int64_t* values, std::size_t count, std::int32_t* out, std::int32_t shift) {
    for (std::size_t index = 0; index < count; ++index) out[index] = static_cast<std::int32_t>(values[index]) + shift;
    return out + count;
}

void writeBlock(EvaluationWriter& out, const std::string& prefix, const std::vector<const NumericGraphData*>& graphs) {
    std::size_t tokenCount = 0, nodeCount = 0, edgeCount = 0;
    for (const auto* graph : graphs) {
        tokenCount += graph->tokenIds.size();
        nodeCount += graph->types.size();
        edgeCount += graph->sources.size();
    }
    auto* ids = out.array<std::int32_t>(prefix + "ids", tokenCount);
    auto* offsets = out.array<std::int32_t>(prefix + "offsets", nodeCount + 1);
    auto* types = out.array<std::int32_t>(prefix + "types", nodeCount);
    auto* numbers = out.array<float>(prefix + "numbers", nodeCount, 8);
    auto* sources = out.array<std::int32_t>(prefix + "sources", edgeCount);
    auto* targets = out.array<std::int32_t>(prefix + "targets", edgeCount);
    auto* relations = out.array<std::int32_t>(prefix + "relations", edgeCount);
    std::int32_t nodeStart = 0, tokenStart = 0;
    for (const auto* graph : graphs) {
        ids = narrowed(graph->tokenIds, ids);
        offsets = shifted(graph->tokenOffsets.data(), graph->types.size(), offsets, tokenStart);
        types = narrowed(graph->types, types);
        numbers = narrowed(graph->numeric, numbers);
        sources = shifted(graph->sources.data(), graph->sources.size(), sources, nodeStart);
        targets = shifted(graph->targets.data(), graph->targets.size(), targets, nodeStart);
        relations = narrowed(graph->relations, relations);
        nodeStart += static_cast<std::int32_t>(graph->types.size());
        tokenStart += static_cast<std::int32_t>(graph->tokenIds.size());
    }
    *offsets = tokenStart;
}

void writeReferences(EvaluationWriter& out, const std::string& prefix,
                     const std::vector<const NumericGraphData*>& graphs, const NumericGraphData& bank) {
    std::vector<std::int32_t> destinations, indices;
    std::int32_t nodeStart = 0;
    for (const auto* graph : graphs) {
        forEachReference(*graph, bank, [&](std::int64_t source, std::int64_t index) {
            destinations.push_back(static_cast<std::int32_t>(source) + nodeStart);
            indices.push_back(static_cast<std::int32_t>(index));
        });
        nodeStart += static_cast<std::int32_t>(graph->types.size());
    }
    narrowed(destinations, out.array<std::int32_t>(prefix + "dest", destinations.size()));
    narrowed(indices, out.array<std::int32_t>(prefix + "index", indices.size()));
}

// The four levels of CampaignPolicyValueNet._factor_layout. Once the actions are
// sorted, those sharing a prefix are adjacent, in the sorted order of the
// prefixes, so each level's groups and their parents come from one walk. UTF-8
// byte order is code-point order, which is how Python sorts the same strings.
void writeFactorLevels(EvaluationWriter& out, const std::vector<std::array<std::string_view, 4>>& factors) {
    std::vector<std::int32_t> order(factors.size());
    std::iota(order.begin(), order.end(), 0);
    std::sort(order.begin(), order.end(), [&](std::int32_t left, std::int32_t right) {
        return factors[left] < factors[right];
    });
    std::vector<std::int32_t> owners(factors.size()), counts, parents, above(factors.size(), 0);
    std::vector<std::int32_t> parentCounts;
    std::int32_t groupsAbove = 1;
    for (std::size_t level = 1; level <= factors.front().size(); ++level) {
        counts.clear();
        parents.clear();
        for (std::size_t rank = 0; rank < order.size(); ++rank) {
            const auto action = order[rank];
            if (rank == 0 || !std::equal(factors[action].begin(), factors[action].begin() + level,
                                         factors[order[rank - 1]].begin())) {
                counts.push_back(0);
                parents.push_back(above[action]);
            }
            owners[action] = static_cast<std::int32_t>(counts.size()) - 1;
            ++counts.back();
        }
        const auto name = "f" + std::to_string(level) + "_";
        narrowed(owners, out.array<std::int32_t>(name + "owners", owners.size()));
        narrowed(counts, out.array<std::int32_t>(name + "counts", counts.size()));
        narrowed(parents, out.array<std::int32_t>(name + "parents", parents.size()));
        parentCounts.push_back(groupsAbove);
        groupsAbove = static_cast<std::int32_t>(counts.size());
        above = owners;
    }
    narrowed(parentCounts, out.array<std::int32_t>("f_parent_counts", parentCounts.size()));
}

}  // namespace

py::tuple NumericGraph::externalReferences(const NumericGraph& context) const {
    struct Pairs {
        std::vector<std::int64_t> destinations;
        std::vector<std::int64_t> indices;
    };
    auto pairs = std::make_shared<Pairs>();
    {
        py::gil_scoped_release release;
        forEachReference(*data_, *context.data_, [&](std::int64_t source, std::int64_t index) {
            pairs->destinations.push_back(source);
            pairs->indices.push_back(index);
        });
    }
    std::shared_ptr<const Pairs> immutable = std::move(pairs);
    return py::make_tuple(arrayView(immutable, immutable->destinations), arrayView(immutable, immutable->indices));
}

py::list NumericGraph::writeEvaluation(const py::buffer& buffer, const NumericGraph& context,
                                       const std::vector<std::reference_wrapper<const NumericGraph>>& actions,
                                       const std::vector<std::array<std::string_view, 4>>& factors) const {
    if (actions.size() != factors.size()) throw std::invalid_argument("Numerical legal menu and factors disagree");
    std::vector<const NumericGraphData*> menu;
    menu.reserve(actions.size());
    for (const auto& action : actions) menu.push_back(action.get().data_.get());
    EvaluationWriter out(buffer);
    writeBlock(out, "obs_", {data_.get()});
    writeReferences(out, "obs_ref_", {data_.get()}, *context.data_);
    writeBlock(out, "act_", menu);
    writeReferences(out, "act_obs_", menu, *data_);
    writeReferences(out, "act_ctx_", menu, *context.data_);
    auto* nodes = out.array<std::int32_t>("act_nodes", menu.size());
    for (const auto* graph : menu) *nodes++ = static_cast<std::int32_t>(graph->types.size());
    if (!menu.empty()) writeFactorLevels(out, factors);
    return out.header();
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
                                                          const json::Value::Object& rootOverrides,
                                                          const Menu& menu) {
    if (PyGILState_Check()) {
        py::gil_scoped_release release;
        return std::shared_ptr<NumericGraph>(new NumericGraph(Impl::Builder(*impl_).run(value, &rootOverrides, &menu)));
    }
    return std::shared_ptr<NumericGraph>(new NumericGraph(Impl::Builder(*impl_).run(value, &rootOverrides, &menu)));
}

std::int64_t NumericGraphCompiler::bucketCount() const { return impl_->buckets; }

void NumericGraphCompiler::clearCaches() {
    std::lock_guard lock(impl_->poolMutex);
    impl_->pool.clear();
    ++impl_->generation;
}

py::dict NumericGraphCompiler::cacheStats() const {
    std::size_t fields = 0, values = 0, numeric = 0, bytes = 0, sets = 0;
    {
        std::lock_guard lock(impl_->poolMutex);
        sets = impl_->pool.size();
        for (const auto& caches : impl_->pool) {
            fields += caches->fields.values.size();
            values += caches->values.values.size();
            numeric += caches->numeric.size();
            bytes += caches->fields.bytes + caches->values.bytes;
        }
    }
    std::size_t spareGraphs = 0;
    {
        std::lock_guard lock(impl_->spares->mutex);
        spareGraphs = impl_->spares->graphs.size();
    }
    py::dict result;
    result["cache_sets"] = sets;
    result["spare_graphs"] = spareGraphs;
    result["field_tokens"] = fields;
    result["value_tokens"] = values;
    result["numeric_features"] = numeric;
    result["retained_string_bytes"] = bytes;
    result["set_capacity"] = CacheSets;
    result["lexical_capacity"] = LexicalCacheEntries * CacheSets;
    result["numeric_capacity"] = NumericCacheEntries * CacheSets;
    result["string_byte_capacity"] = StringCacheBytes * 2 * CacheSets;
    return result;
}

}  // namespace game::neural
