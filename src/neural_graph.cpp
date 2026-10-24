#include "game/neural_graph.hpp"

#include <bit>
#include <cmath>
#include <cstdint>
#include <set>
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

struct Edge {
    std::size_t source;
    std::size_t target;
    int relation;
};

struct Reference {
    std::size_t source;
    py::object identity;
};

struct Identity {
    py::object name;
    std::set<std::size_t> nodes;
};

struct NumericKey {
    std::uint64_t numberBits;
    Py_ssize_t length;
    Py_ssize_t size;
    Py_ssize_t position;
    bool operator==(const NumericKey&) const = default;
};

struct NumericKeyHash {
    std::size_t operator()(const NumericKey& key) const {
        std::size_t hash = std::hash<std::uint64_t>{}(key.numberBits);
        for (const auto value : {key.length, key.size, key.position}) {
            hash ^= std::hash<Py_ssize_t>{}(value) + 0x9e3779b97f4a7c15ULL + (hash << 6) + (hash >> 2);
        }
        return hash;
    }
};

struct RecursiveCall {
    RecursiveCall() {
        if (Py_EnterRecursiveCall(" while compiling campaign neural features")) {
            throw py::error_already_set();
        }
    }
    ~RecursiveCall() { Py_LeaveRecursiveCall(); }
};

bool equalsAscii(PyObject* text, const char* expected) {
    const auto result = PyUnicode_CompareWithASCIIString(text, expected);
    if (result == -1 && PyErr_Occurred()) throw py::error_already_set();
    return result == 0;
}

std::string utf8(PyObject* text) {
    Py_ssize_t length = 0;
    const auto* data = PyUnicode_AsUTF8AndSize(text, &length);
    if (!data) throw py::error_already_set();
    return std::string(data, static_cast<std::size_t>(length));
}

PyObject* dictGet(PyObject* dictionary, const char* key) {
    auto* result = PyDict_GetItemString(dictionary, key);
    if (!result && PyErr_Occurred()) throw py::error_already_set();
    return result;
}

bool entityCollection(PyObject* key) {
    for (const auto* name : {"nodes", "factions", "nations", "units", "territories", "facilities",
                             "construction", "repairs", "rails", "battles"}) {
        if (equalsAscii(key, name)) return true;
    }
    return false;
}

template <class Values>
py::tuple integerTuple(const Values& values) {
    py::tuple result(values.size());
    std::size_t index = 0;
    for (const auto value : values) result[index++] = py::int_(value);
    return result;
}

class Compiler {
public:
    Compiler(py::object buckets, const py::function& lexicalIds,
             const py::function& stringDescriptor, const py::function& numericFeatures)
        : buckets_(std::move(buckets)), lexicalIds_(lexicalIds), stringDescriptor_(stringDescriptor),
          numericFeatures_(numericFeatures) {}

    py::dict run(py::handle value) {
        const auto invalidBuckets = PyObject_RichCompareBool(buckets_.ptr(), py::int_(2).ptr(), Py_LT);
        if (invalidBuckets == -1) throw py::error_already_set();
        if (invalidBuckets) throw py::value_error("The lexical vocabulary needs at least two buckets");
        offsets_.push_back(0);
        visit(value.ptr(), rootKey_.ptr(), 0, RootPath);
        // Reference edges follow the established per-string traversal order,
        // with each identity's target set visited in sorted node-index order.
        for (const auto& reference : references_) {
            const auto found = identityLookup_.find(utf8(reference.identity.ptr()));
            if (found == identityLookup_.end()) continue;
            for (const auto target : identities_[found->second].nodes) {
                if (reference.source != target) {
                    edges_.push_back({target, reference.source, IdentityReference});
                    edges_.push_back({reference.source, target, ReferenceBack});
                }
            }
        }
        addAdjacency(value.ptr());

        // Reuse each node's Python integer across all of its edges and identity
        // references, as the reference traversal does. This avoids allocating
        // thousands of duplicate index objects for a large source graph.
        py::tuple nodeIndices(types_.size());
        for (std::size_t index = 0; index < types_.size(); ++index) {
            auto* value = PyLong_FromSize_t(index);
            if (!value) throw py::error_already_set();
            PyTuple_SET_ITEM(nodeIndices.ptr(), index, value);
        }
        py::tuple tokenIds(tokens_.size());
        for (std::size_t index = 0; index < tokens_.size(); ++index) {
            PyTuple_SET_ITEM(tokenIds.ptr(), index, Py_NewRef(tokens_[index]));
        }
        py::tuple numbers(numbers_.size());
        for (std::size_t index = 0; index < numbers_.size(); ++index) {
            PyTuple_SET_ITEM(numbers.ptr(), index, Py_NewRef(numbers_[index]));
        }
        py::tuple edges(edges_.size());
        for (std::size_t index = 0; index < edges_.size(); ++index) {
            const auto& edge = edges_[index];
            py::tuple item(3);
            PyTuple_SET_ITEM(item.ptr(), 0, Py_NewRef(PyTuple_GET_ITEM(nodeIndices.ptr(), edge.source)));
            PyTuple_SET_ITEM(item.ptr(), 1, Py_NewRef(PyTuple_GET_ITEM(nodeIndices.ptr(), edge.target)));
            PyTuple_SET_ITEM(item.ptr(), 2, PyLong_FromLong(edge.relation));
            PyTuple_SET_ITEM(edges.ptr(), index, item.release().ptr());
        }
        py::dict identities;
        for (const auto& identity : identities_) {
            py::tuple indices(identity.nodes.size());
            std::size_t offset = 0;
            for (const auto index : identity.nodes) {
                PyTuple_SET_ITEM(indices.ptr(), offset++, Py_NewRef(PyTuple_GET_ITEM(nodeIndices.ptr(), index)));
            }
            identities[identity.name] = std::move(indices);
        }
        py::tuple references(references_.size());
        for (std::size_t index = 0; index < references_.size(); ++index) {
            const auto& reference = references_[index];
            py::tuple item(2);
            PyTuple_SET_ITEM(item.ptr(), 0, Py_NewRef(PyTuple_GET_ITEM(nodeIndices.ptr(), reference.source)));
            PyTuple_SET_ITEM(item.ptr(), 1, Py_NewRef(reference.identity.ptr()));
            PyTuple_SET_ITEM(references.ptr(), index, item.release().ptr());
        }
        py::dict result;
        result["token_ids"] = std::move(tokenIds);
        result["token_offsets"] = integerTuple(offsets_);
        result["types"] = integerTuple(types_);
        result["numeric"] = std::move(numbers);
        result["edges"] = std::move(edges);
        result["identities"] = std::move(identities);
        result["references"] = std::move(references);
        result["leaf_count"] = py::int_(leaves_);
        return result;
    }

private:
    void addTokens(PyObject* text, bool value) {
        auto& cache = value ? valueTokens_ : fieldTokens_;
        auto* words = PyDict_GetItemWithError(cache.ptr(), text);
        if (!words) {
            if (PyErr_Occurred()) throw py::error_already_set();
            auto found = lexicalIds_(py::handle(text), value ? valueRole_ : fieldRole_, buckets_);
            // Retain an immutable tuple even if a custom callback returns a
            // mutable sequence that it later edits during another callback.
            auto sequence = py::reinterpret_steal<py::object>(PySequence_Tuple(found.ptr()));
            if (!sequence) throw py::error_already_set();
            if (PyDict_SetItem(cache.ptr(), text, sequence.ptr())) throw py::error_already_set();
            words = PyDict_GetItemWithError(cache.ptr(), text);
        }
        const auto count = PyTuple_GET_SIZE(words);
        auto** values = PySequence_Fast_ITEMS(words);
        tokens_.insert(tokens_.end(), values, values + count);
    }

    std::pair<Py_ssize_t, double> stringDescription(PyObject* value) {
        auto* description = PyDict_GetItemWithError(stringDescriptions_.ptr(), value);
        if (!description) {
            if (PyErr_Occurred()) throw py::error_already_set();
            auto found = stringDescriptor_(py::handle(value));
            if (PyDict_SetItem(stringDescriptions_.ptr(), value, found.ptr())) throw py::error_already_set();
            description = PyDict_GetItemWithError(stringDescriptions_.ptr(), value);
        }
        const auto tuple = py::reinterpret_borrow<py::tuple>(description);
        if (!PyTuple_Check(description) || tuple.size() != 2) {
            throw py::type_error("String descriptor must return (UTF-8 length, numeric value)");
        }
        return {py::cast<Py_ssize_t>(tuple[0]), py::cast<double>(tuple[1])};
    }

    PyObject* numbers(double number, Py_ssize_t length, Py_ssize_t size, Py_ssize_t position) {
        // IEEE bits distinguish +0.0 and -0.0, whose signed-log features differ.
        const NumericKey key{std::bit_cast<std::uint64_t>(number), length, size, position};
        auto found = numberCache_.find(key);
        if (found != numberCache_.end()) return found->second.ptr();
        auto value = numericFeatures_(number, length, size, position);
        if (!PyTuple_Check(value.ptr()) || PyTuple_GET_SIZE(value.ptr()) != 8) {
            throw py::type_error("Numeric features must return an eight-value tuple");
        }
        return numberCache_.emplace(key, std::move(value)).first->second.ptr();
    }

    void bind(PyObject* identity, std::size_t index) {
        const auto key = utf8(identity);
        auto [found, inserted] = identityLookup_.emplace(key, identities_.size());
        if (inserted) identities_.push_back({py::reinterpret_borrow<py::object>(identity), {}});
        identities_[found->second].nodes.insert(index);
    }

    std::size_t visit(PyObject* value, PyObject* key, Py_ssize_t position, Path path) {
        RecursiveCall recursion;
        // A callback may release the GIL. Own the current source and key even
        // if another thread removes them from their parent in the meantime.
        const auto ownedValue = py::reinterpret_borrow<py::object>(value);
        const auto ownedKey = py::reinterpret_borrow<py::object>(key);
        const auto index = types_.size();
        double number = 0;
        Py_ssize_t length = 0;
        Py_ssize_t size = 0;
        Kind kind;
        addTokens(key, false);
        if (value == Py_None) {
            kind = Null;
        } else if (PyBool_Check(value)) {
            kind = Bool;
            number = value == Py_True ? 1 : 0;
        } else if (PyLong_Check(value) || PyFloat_Check(value)) {
            kind = Number;
            if (PyFloat_Check(value) && !PyFloat_CheckExact(value)) {
                // float(item) honors a float subclass's __float__ method.
                // Ordinary JSON floats retain the direct C API fast path.
                const auto converted = py::reinterpret_steal<py::object>(PyNumber_Float(value));
                if (!converted) throw py::error_already_set();
                number = PyFloat_AS_DOUBLE(converted.ptr());
            } else {
                number = PyFloat_AsDouble(value);
            }
            if (PyErr_Occurred()) throw py::error_already_set();
            if (!std::isfinite(number)) throw py::value_error("Neural features require finite JSON numbers");
        } else if (PyUnicode_Check(value)) {
            kind = String;
            const auto description = stringDescription(value);
            length = description.first;
            number = description.second;
            addTokens(value, true);
            references_.push_back({index, py::reinterpret_borrow<py::object>(value)});
        } else if (PyList_Check(value)) {
            kind = Array;
            size = PyList_GET_SIZE(value);
        } else if (PyDict_Check(value)) {
            kind = Object;
            size = PyDict_Size(value);
            Py_ssize_t cursor = 0;
            PyObject *field = nullptr, *child = nullptr;
            while (PyDict_Next(value, &cursor, &field, &child)) {
                if (!PyUnicode_Check(field)) throw py::value_error("JSON object keys must be strings");
            }
        } else {
            throw py::type_error("Unsupported neural JSON value: " + py::str(py::type::of(py::handle(value)).attr("__name__")).cast<std::string>());
        }
        offsets_.push_back(tokens_.size());
        types_.push_back(kind);
        numbers_.push_back(numbers(number, length, size, position));
        if (kind == Object) {
            if (auto* identity = dictGet(value, "id"); identity && PyUnicode_Check(identity)) bind(identity, index);
            // Match sorted(item.items()): retain both keys and children before
            // recursive callbacks, rather than re-reading a mutable mapping.
            auto fields = py::reinterpret_steal<py::list>(PyDict_Items(value));
            if (!fields || PyList_Sort(fields.ptr())) throw py::error_already_set();
            const bool collection = entityCollection(key);
            for (Py_ssize_t offset = 0; offset < PyList_GET_SIZE(fields.ptr()); ++offset) {
                auto* entry = PyList_GET_ITEM(fields.ptr(), offset);
                auto* field = PyTuple_GET_ITEM(entry, 0);
                auto* child = PyTuple_GET_ITEM(entry, 1);
                const auto ownedChild = py::reinterpret_borrow<py::object>(child);
                Path childPath = OtherPath;
                if (path == RootPath && equalsAscii(field, "geography")) childPath = GeographyPath;
                if (path == GeographyPath && equalsAscii(field, "nodes")) childPath = GeographyNodesPath;
                const auto target = visit(child, field, 0, childPath);
                edges_.push_back({index, target, ParentToChild});
                edges_.push_back({target, index, ChildToParent});
                if (collection && PyDict_Check(child)) bind(field, target);
                if (path == GeographyNodesPath) geographyNodes_.emplace(utf8(field), target);
            }
        } else if (kind == Array) {
            for (Py_ssize_t offset = 0; offset < size; ++offset) {
                if (PyList_GET_SIZE(value) != size) {
                    throw py::value_error("JSON source changed while compiling neural features");
                }
                const auto target = visit(PyList_GET_ITEM(value, offset), arrayKey_.ptr(), offset, OtherPath);
                edges_.push_back({index, target, ParentToChild});
                edges_.push_back({target, index, ChildToParent});
            }
        } else {
            ++leaves_;
        }
        return index;
    }

    void addAdjacency(PyObject* value) {
        if (!PyDict_Check(value)) return;
        auto* geography = dictGet(value, "geography");
        if (!geography || !PyDict_Check(geography)) return;
        const auto ownedGeography = py::reinterpret_borrow<py::object>(geography);
        auto* nodes = dictGet(geography, "nodes");
        if (!nodes) return;
        const auto ownedNodes = py::reinterpret_borrow<py::object>(nodes);
        // The established Python compiler expects geography.nodes to support
        // items(); preserve that failure for malformed public JSON.
        if (!PyDict_Check(nodes)) {
            py::reinterpret_borrow<py::object>(nodes).attr("items")();
            return;
        }
        // Snapshot the pairs so a custom callback/get method cannot invalidate
        // a borrowed node or an active PyDict_Next cursor.
        const auto entries = py::reinterpret_steal<py::list>(PyDict_Items(nodes));
        if (!entries) throw py::error_already_set();
        for (Py_ssize_t offset = 0; offset < PyList_GET_SIZE(entries.ptr()); ++offset) {
            auto* entry = PyList_GET_ITEM(entries.ptr(), offset);
            auto* identity = PyTuple_GET_ITEM(entry, 0);
            auto* node = PyTuple_GET_ITEM(entry, 1);
            if (!PyDict_Check(node)) continue;
            const auto source = geographyNodes_.find(utf8(identity));
            auto* neighbors = dictGet(node, "neighbors");
            if (!neighbors) continue;
            const auto ownedNeighbors = py::reinterpret_borrow<py::object>(neighbors);
            auto iterator = py::reinterpret_steal<py::object>(PyObject_GetIter(neighbors));
            if (!iterator) throw py::error_already_set();
            while (auto* next = PyIter_Next(iterator.ptr())) {
                auto neighbor = py::reinterpret_steal<py::object>(next);
                auto targetIdentity = neighbor.attr("get")("neighbor_id");
                if (PyObject_Hash(targetIdentity.ptr()) == -1 && PyErr_Occurred()) throw py::error_already_set();
                if (!PyUnicode_Check(targetIdentity.ptr())) continue;
                const auto target = geographyNodes_.find(utf8(targetIdentity.ptr()));
                if (source != geographyNodes_.end() && target != geographyNodes_.end()) {
                    edges_.push_back({source->second, target->second, Adjacent});
                }
            }
            if (PyErr_Occurred()) throw py::error_already_set();
        }
    }

    py::object buckets_;
    const py::function& lexicalIds_;
    const py::function& stringDescriptor_;
    const py::function& numericFeatures_;
    py::str rootKey_{"$"};
    py::str arrayKey_{"[]"};
    py::str fieldRole_{"field"};
    py::str valueRole_{"value"};
    // All callback results stay alive until the output tuples own their refs.
    // These caches contain source data only and die after this one compilation.
    py::dict fieldTokens_;
    py::dict valueTokens_;
    py::dict stringDescriptions_;
    std::unordered_map<NumericKey, py::object, NumericKeyHash> numberCache_;
    std::vector<PyObject*> tokens_;
    std::vector<std::size_t> offsets_;
    std::vector<int> types_;
    std::vector<PyObject*> numbers_;
    std::vector<Edge> edges_;
    std::vector<Reference> references_;
    std::vector<Identity> identities_;
    std::unordered_map<std::string, std::size_t> identityLookup_;
    std::unordered_map<std::string, std::size_t> geographyNodes_;
    std::size_t leaves_ = 0;
};

}  // namespace

py::dict compileCampaignGraph(py::handle value, py::object buckets, const py::function& lexicalIds,
                             const py::function& stringDescriptor, const py::function& numericFeatures) {
    return Compiler(std::move(buckets), lexicalIds, stringDescriptor, numericFeatures).run(value);
}

}  // namespace game::neural
