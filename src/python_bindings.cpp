#include "game/action.hpp"
#include "game/air.hpp"
#include "game/composition_battle_env.hpp"
#include "game/japan_training_env.hpp"
#include "game/mdp.hpp"
#include "game/campaign_env.hpp"
#include "game/campaign_actions.hpp"
#include "game/neural_graph.hpp"
#include "game/numeric_graph.hpp"
#include "game/zone_encoding.hpp"

#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <algorithm>
#include <array>
#include <cstring>
#include <functional>
#include <stdexcept>
#include <string>
#include <memory>
#include <mutex>
#include <utility>

namespace py = pybind11;

namespace {

// Keep Python's synchronization policy at its boundary, not in the rules core.
// Each bound environment owns its operation mutex; cloned boards get new ones.
// Always release the GIL BEFORE waiting for this mutex. The reverse order could
// deadlock with a native operation that is returning to Python. Owned native
// results are prepared under the mutex, which is released before GIL reacquire.
class NativeCampaignEnv {
  public:
    explicit NativeCampaignEnv(game::campaign::CampaignEnv env) : env_(std::move(env)) {}

    template <class Function> auto call(Function&& function) {
        py::gil_scoped_release release;
        std::lock_guard lock(mutex_);
        return std::forward<Function>(function)(env_);
    }

    template <class Function> auto call(Function&& function) const {
        py::gil_scoped_release release;
        std::lock_guard lock(mutex_);
        return std::forward<Function>(function)(std::as_const(env_));
    }

  private:
    game::campaign::CampaignEnv env_;
    mutable std::mutex mutex_;
};

using CampaignEnv = game::campaign::CampaignEnv;

// Immutable owning views outlive an environment mutation without copying its
// state tree. Only small scheduler fields overlay the complete native document.
struct NumericSnapshot {
    using V = game::json::Value;
    std::shared_ptr<const V> source;
    V::Object overrides;
    std::shared_ptr<const std::string> actionSourceKey;
    bool passAction {false};
    // An observation's legal_actions elements, shared with the actions' own
    // snapshots; the array in `overrides` stays empty.
    game::neural::NumericGraphCompiler::Menu menu;

    py::object cacheKey() const {
        if (!overrides.empty() || (!actionSourceKey && !passAction)) return py::none();
        const auto& fields = source->asObject();
        return py::make_tuple(fields.at("id").asString(), fields.at("kind").asString(),
            fields.at("player").asString(), actionSourceKey ? py::object(py::str(*actionSourceKey)) : py::object(py::none()));
    }

    V materialize() const {
        if (overrides.empty()) return *source;
        auto result = source->asObject();
        for (const auto& [key, value] : overrides) result.insert_or_assign(key, value);
        if (!menu.empty()) {
            V::Array elements;
            for (const auto& element : menu) elements.push_back(*element);
            result.insert_or_assign("legal_actions", V(std::move(elements)));
        }
        return V(std::move(result));
    }

    NumericSnapshot scheduledContext(const std::string& schema, const std::vector<std::string>& order) const {
        auto result = *this;
        V::Array sequence;
        for (const auto& owner : order) sequence.emplace_back(owner);
        result.overrides["interrupt_scheduler"] = V(V::Object{{"schema", V(schema)}, {"order", V(std::move(sequence))}});
        return result;
    }

    NumericSnapshot scheduledObservation(const std::optional<std::string>& owner, const std::string& kind,
            const std::vector<std::reference_wrapper<const NumericSnapshot>>& actions, const std::string& schema,
            const std::vector<std::string>& order, const std::vector<std::string>& passed) const {
        auto result = scheduledContext(schema, order);
        result.overrides["current_decision_player"] = owner ? V(*owner) : V(nullptr);
        result.overrides["decision_kind"] = V(kind);
        result.overrides["legal_actions"] = V(V::Array{});
        result.menu.clear();
        result.menu.reserve(actions.size());
        for (const NumericSnapshot& action : actions) {
            result.menu.push_back(action.overrides.empty() ? action.source : std::make_shared<const V>(action.materialize()));
        }
        V::Array passSequence;
        for (const auto& player : passed) passSequence.emplace_back(player);
        auto scheduler = result.overrides.at("interrupt_scheduler").asObject();
        scheduler["passed"] = V(std::move(passSequence));
        result.overrides["interrupt_scheduler"] = V(std::move(scheduler));
        return result;
    }

    static NumericSnapshot scheduledAction(const game::campaign::Action* action,
            const std::string& id, const std::string& kind, const std::string& player) {
        V::Object wrapped;
        wrapped.emplace("id", id);
        wrapped.emplace("kind", kind);
        wrapped.emplace("player", player);
        wrapped.emplace("action", action ? game::campaign::actionJson(*action) : V(nullptr));
        return {std::make_shared<const V>(std::move(wrapped)), {}, action ? action->neuralSourceKey : nullptr,
            action == nullptr};
    }

    std::vector<std::string> factorJson() const {
        const auto& wrapped = source->asObject();
        const auto* action = source->find("action");
        const auto& raw = action && action->isObject() ? *action : *source;
        const auto* kind = raw.find("kind");
        const auto* parameters = raw.find("parameters");
        const std::vector<std::vector<std::string>> groups{
            {"source", "from", "origin", "source_zone", "unit", "units", "group", "force", "transport", "carrier", "facility", "battle"},
            {"path", "route", "sea_route", "land_route"},
            {"target", "destination", "to", "zone", "recipient", "endpoint"}};
        std::vector<std::string> result{game::campaign::canonicalJson(kind ? *kind : wrapped.at("kind"))};
        for (const auto& fields : groups) {
            V::Object group;
            if (parameters && parameters->isObject()) for (const auto& field : fields)
                if (const auto* value = parameters->find(field)) group.emplace(field, *value);
            result.push_back(game::campaign::canonicalJson(V(std::move(group))));
        }
        return result;
    }
};

std::string describeAction(const game::Action& action) {
    std::string description(game::toString(action.kind));
    bool hasDetails = false;
    if (action.sourceZoneId.has_value()) {
        description += "(from=" + *action.sourceZoneId;
        hasDetails = true;
    }
    if (action.targetZoneId.has_value()) {
        description += hasDetails ? ", to=" : "(to=";
        description += *action.targetZoneId;
        hasDetails = true;
    }
    if (action.unitCount.has_value()) {
        description += hasDetails ? ", count=" : "(count=";
        description += std::to_string(*action.unitCount);
        hasDetails = true;
    }
    if (action.unitKind.has_value()) {
        description += hasDetails ? ", unit=" : "(unit=";
        description += std::string(game::toString(*action.unitKind));
        hasDetails = true;
    }
    if (hasDetails) {
        description += ")";
    }
    return description;
}

using ZoneInput = game::campaign::ZoneInput;

// One encoded decision, immutable and shared between Python objects.
struct ZoneInputHandle {
    std::shared_ptr<const ZoneInput> input;
    std::string version;
};

constexpr std::array<const char*, 12> zoneArrayNames{
    "zone_index", "zone_column", "zone_value", "global_column", "global_value", "action_offsets",
    "action_column", "action_value", "action_source", "action_target", "path_offsets", "path_zone"};

std::array<const std::vector<std::int32_t>*, 12> zoneFields(const ZoneInput& z) {
    return {&z.zoneIndex, &z.zoneColumn, &z.zoneValue, &z.globalColumn, &z.globalValue, &z.actionOffsets,
            &z.actionColumn, &z.actionValue, &z.actionSource, &z.actionTarget, &z.pathOffsets, &z.pathZone};
}

std::array<std::vector<std::int32_t>*, 12> zoneFields(ZoneInput& z) {
    return {&z.zoneIndex, &z.zoneColumn, &z.zoneValue, &z.globalColumn, &z.globalValue, &z.actionOffsets,
            &z.actionColumn, &z.actionValue, &z.actionSource, &z.actionTarget, &z.pathOffsets, &z.pathZone};
}

py::array_t<std::int32_t> int32Array(const std::vector<std::int32_t>& values) {
    py::array_t<std::int32_t> out(static_cast<py::ssize_t>(values.size()));
    if (!values.empty()) std::memcpy(out.mutable_data(), values.data(), values.size() * sizeof(std::int32_t));
    return out;
}

std::vector<std::int32_t> int32Vector(const py::handle& value) {
    const auto array = py::array_t<std::int32_t, py::array::c_style | py::array::forcecast>::ensure(value);
    if (!array || array.ndim() != 1) throw std::invalid_argument("Zone input fields must be one-dimensional integer arrays");
    return {array.data(), array.data() + array.size()};
}

void validateZoneInput(const ZoneInput& z) {
    const auto offsets = [](const std::vector<std::int32_t>& o, std::size_t entries, std::size_t count) {
        if (o.size() != count + 1 || o.front() != 0 || static_cast<std::size_t>(o.back()) != entries ||
            !std::is_sorted(o.begin(), o.end()))
            throw std::invalid_argument("Zone input offsets are inconsistent");
    };
    if (z.zoneIndex.size() != z.zoneColumn.size() || z.zoneIndex.size() != z.zoneValue.size() ||
        z.globalColumn.size() != z.globalValue.size() || z.actionColumn.size() != z.actionValue.size() ||
        z.actionSource.size() != z.actionTarget.size() || z.factors.size() != z.actionSource.size())
        throw std::invalid_argument("Zone input fields differ in length");
    offsets(z.actionOffsets, z.actionColumn.size(), z.actionSource.size());
    offsets(z.pathOffsets, z.pathZone.size(), z.actionSource.size());
}

ZoneInput zoneFromParts(const py::dict& arrays, const py::list& factors) {
    ZoneInput z;
    const auto fields = zoneFields(z);
    for (std::size_t i = 0; i < fields.size(); ++i) {
        if (!arrays.contains(zoneArrayNames[i])) throw std::invalid_argument(std::string("Zone input lacks ") + zoneArrayNames[i]);
        *fields[i] = int32Vector(arrays[zoneArrayNames[i]]);
    }
    for (const auto& item : factors) {
        const auto parts = item.cast<std::vector<std::string>>();
        if (parts.size() != 4) throw std::invalid_argument("Each zone option needs four policy groups");
        z.factors.push_back({parts[0], parts[1], parts[2], parts[3]});
    }
    validateZoneInput(z);
    return z;
}

// The same position with only the listed options, in the listed order.
ZoneInput selectZoneOptions(const ZoneInput& z, const std::vector<int>& indices) {
    ZoneInput out;
    out.zoneIndex = z.zoneIndex;
    out.zoneColumn = z.zoneColumn;
    out.zoneValue = z.zoneValue;
    out.globalColumn = z.globalColumn;
    out.globalValue = z.globalValue;
    for (const int index : indices) {
        if (index < 0 || static_cast<std::size_t>(index) >= z.actionCount())
            throw std::invalid_argument("Zone option index out of range");
        const auto i = static_cast<std::size_t>(index);
        for (auto k = z.actionOffsets[i]; k < z.actionOffsets[i + 1]; ++k) {
            out.actionColumn.push_back(z.actionColumn[static_cast<std::size_t>(k)]);
            out.actionValue.push_back(z.actionValue[static_cast<std::size_t>(k)]);
        }
        out.actionOffsets.push_back(static_cast<std::int32_t>(out.actionColumn.size()));
        out.actionSource.push_back(z.actionSource[i]);
        out.actionTarget.push_back(z.actionTarget[i]);
        for (auto k = z.pathOffsets[i]; k < z.pathOffsets[i + 1]; ++k) out.pathZone.push_back(z.pathZone[static_cast<std::size_t>(k)]);
        out.pathOffsets.push_back(static_cast<std::int32_t>(out.pathZone.size()));
        out.factors.push_back(z.factors[i]);
    }
    return out;
}

bool sameZoneInput(const ZoneInput& a, const ZoneInput& b) {
    const auto left = zoneFields(a), right = zoneFields(b);
    for (std::size_t i = 0; i < left.size(); ++i)
        if (*left[i] != *right[i]) return false;
    return a.factors == b.factors;
}

}  // namespace

PYBIND11_MODULE(gwrl_cpp, module) {
    module.doc() = "C++ training environment bindings for gwRL";

    py::class_<ZoneInputHandle>(module, "CampaignZoneInput",
        "One campaign decision in the fixed zone encoding: nonzero answers to fixed per-zone, "
        "per-position and per-option questions. Immutable; copies share the native arrays.")
        .def("arrays", [](const ZoneInputHandle& self) {
            py::dict out;
            const auto fields = zoneFields(*self.input);
            for (std::size_t i = 0; i < fields.size(); ++i) out[zoneArrayNames[i]] = int32Array(*fields[i]);
            return out;
        })
        .def("factors", [](const ZoneInputHandle& self) {
            py::list out;
            for (const auto& f : self.input->factors) out.append(py::make_tuple(f[0], f[1], f[2], f[3]));
            return out;
        })
        .def("select", [](const ZoneInputHandle& self, const std::vector<int>& indices) {
            return ZoneInputHandle{std::make_shared<const ZoneInput>(selectZoneOptions(*self.input, indices)), self.version};
        }, py::arg("indices"))
        .def("without_actions", [](const ZoneInputHandle& self) {
            return ZoneInputHandle{std::make_shared<const ZoneInput>(selectZoneOptions(*self.input, {})), self.version};
        })
        .def_property_readonly("version", [](const ZoneInputHandle& self) { return self.version; })
        .def_property_readonly("action_count", [](const ZoneInputHandle& self) { return self.input->actionCount(); })
        .def_property_readonly("nbytes", [](const ZoneInputHandle& self) { return self.input->bytes(); })
        .def("__eq__", [](const ZoneInputHandle& self, const ZoneInputHandle& other) {
            return self.version == other.version && sameZoneInput(*self.input, *other.input);
        }, py::is_operator())
        .def("__deepcopy__", [](const ZoneInputHandle& self, py::dict) { return self; })
        .def(py::pickle(
            [](const ZoneInputHandle& self) {
                py::dict arrays;
                const auto fields = zoneFields(*self.input);
                for (std::size_t i = 0; i < fields.size(); ++i) arrays[zoneArrayNames[i]] = int32Array(*fields[i]);
                py::list factors;
                for (const auto& f : self.input->factors) factors.append(py::make_tuple(f[0], f[1], f[2], f[3]));
                return py::make_tuple(self.version, arrays, factors);
            },
            [](const py::tuple& state) {
                if (state.size() != 3) throw std::invalid_argument("Invalid zone input pickle");
                return ZoneInputHandle{std::make_shared<const ZoneInput>(
                    zoneFromParts(state[1].cast<py::dict>(), state[2].cast<py::list>())), state[0].cast<std::string>()};
            }));
    module.def("campaign_zone_input", [](const std::string& version, const py::dict& arrays, const py::list& factors) {
        return ZoneInputHandle{std::make_shared<const ZoneInput>(zoneFromParts(arrays, factors)), version};
    }, py::arg("version"), py::arg("arrays"), py::arg("factors"),
       "Rebuild a zone input from its arrays, checking only that its fields fit together.");
    module.def("zone_encoding_unknowns", [](bool reset) { return game::campaign::zoneEncodingUnknowns(reset); },
               py::arg("reset") = false,
               "Names counted in an \"other\" column of the zone encoding since the last reset.");

    module.def("compile_campaign_graph", &game::neural::compileCampaignGraph,
               py::arg("value"), py::arg("buckets"), py::arg("lexical_ids"),
               py::arg("string_descriptor"), py::arg("numeric_features"),
               "Compile complete public JSON features without engine state or learned tensors.");

    py::class_<NumericSnapshot>(module, "CampaignNumericSnapshot")
        .def_property_readonly("cache_key", &NumericSnapshot::cacheKey)
        .def("scheduled_context", &NumericSnapshot::scheduledContext, py::call_guard<py::gil_scoped_release>())
        .def("scheduled_observation", &NumericSnapshot::scheduledObservation)
        .def("factor_json", &NumericSnapshot::factorJson, py::call_guard<py::gil_scoped_release>())
        .def("to_python", [](const NumericSnapshot& snapshot) {
            return py::module_::import("json").attr("loads")(game::campaign::canonicalJson(snapshot.materialize()));
        });
    module.def("campaign_pass_snapshot", [](const std::string& id, const std::string& kind, const std::string& player) {
        return NumericSnapshot::scheduledAction(nullptr, id, kind, player);
    });

    py::class_<game::neural::NumericGraph, std::shared_ptr<game::neural::NumericGraph>>(module, "CampaignNumericGraph")
        .def("arrays", &game::neural::NumericGraph::arrays)
        .def("__eq__", &game::neural::NumericGraph::equals, py::is_operator(), py::call_guard<py::gil_scoped_release>())
        .def("debug_graph", &game::neural::NumericGraph::debugGraph)
        .def("external_references", &game::neural::NumericGraph::externalReferences)
        .def("write_evaluation", &game::neural::NumericGraph::writeEvaluation)
        .def_property_readonly("node_count", &game::neural::NumericGraph::nodeCount)
        .def_property_readonly("leaf_count", &game::neural::NumericGraph::leafCount)
        .def_property_readonly("token_buckets", &game::neural::NumericGraph::bucketCount)
        .def_property_readonly("nbytes", &game::neural::NumericGraph::retainedBytes)
        .def("packed_state", &game::neural::NumericGraph::packedState)
        .def("compacted", &game::neural::NumericGraph::compacted)
        .def_static("from_packed", &game::neural::NumericGraph::fromPacked)
        .def("__deepcopy__", [](const std::shared_ptr<game::neural::NumericGraph>& graph, py::dict) { return graph; })
        .def(py::pickle(
            [](const game::neural::NumericGraph& graph) -> py::object {
                return py::module_::import("studies.campaign.numeric_storage").attr("pack_graph")(graph.packedState());
            },
            [](const py::object& state) {
                const auto packed = py::module_::import("studies.campaign.numeric_storage").attr("unpack_graph")(state);
                return game::neural::NumericGraph::fromPacked(packed.cast<py::dict>());
            }));
    py::class_<game::neural::NumericGraphCompiler>(module, "CampaignNumericGraphCompiler")
        .def(py::init<std::int64_t, py::function, py::function, py::function>())
        .def("compile", [](game::neural::NumericGraphCompiler& compiler, const NumericSnapshot& snapshot) {
            return compiler.compile(*snapshot.source, snapshot.overrides, snapshot.menu);
        })
        .def("clear_caches", &game::neural::NumericGraphCompiler::clearCaches)
        .def("cache_stats", &game::neural::NumericGraphCompiler::cacheStats);

    py::enum_<game::UnitKind>(module, "UnitKind")
        .value("Infantry", game::UnitKind::Infantry)
        .value("Artillery", game::UnitKind::Artillery)
        .value("Marine", game::UnitKind::Marine)
        .value("LightTank", game::UnitKind::LightTank)
        .value("MechanizedInfantry", game::UnitKind::MechanizedInfantry)
        .value("MediumTank", game::UnitKind::MediumTank)
        .value("TankDestroyer", game::UnitKind::TankDestroyer)
        .value("Fighter", game::UnitKind::Fighter)
        .value("Transport", game::UnitKind::Transport);

    py::enum_<game::ActionKind>(module, "ActionKind")
        .value("DeclareWarOnChina", game::ActionKind::DeclareWarOnChina)
        .value("PurchaseUnit", game::ActionKind::PurchaseUnit)
        .value("MoveCombatUnit", game::ActionKind::MoveCombatUnit)
        .value("ResolveCombat", game::ActionKind::ResolveCombat)
        .value("PlaceUnit", game::ActionKind::PlaceUnit)
        .value("EndPhase", game::ActionKind::EndPhase);

    py::class_<game::Action>(module, "Action")
        .def(py::init<>())
        .def_readwrite("kind", &game::Action::kind)
        .def_readwrite("source_zone_id", &game::Action::sourceZoneId)
        .def_readwrite("target_zone_id", &game::Action::targetZoneId)
        .def_readwrite("unit_count", &game::Action::unitCount)
        .def_readwrite("unit_kind", &game::Action::unitKind)
        .def("describe", &describeAction)
        .def("__repr__", [](const game::Action& action) {
            return "<Action " + describeAction(action) + ">";
        });

    py::class_<game::campaign::Action>(module, "CampaignAction")
        .def_readonly("id", &game::campaign::Action::id)
        .def_readonly("kind", &game::campaign::Action::kind)
        .def_readonly("nation", &game::campaign::Action::nation)
        .def_readonly("player", &game::campaign::Action::player)
        .def_readonly("decision", &game::campaign::Action::decision)
        .def("scheduled_snapshot", [](const game::campaign::Action& action,
                const std::string& id, const std::string& kind, const std::string& player) {
            // Far too short to hand Python's lock to another thread and wait to get it back.
            return NumericSnapshot::scheduledAction(&action, id, kind, player);
        })
        .def_property_readonly("parameters", [](const game::campaign::Action &a) {
            return py::module_::import("json").attr("loads")(game::campaign::canonicalJson(a.parameters));
        })
        .def("describe", [](const game::campaign::Action &a) {
            return game::campaign::canonicalJson(game::campaign::actionJson(a));
        });

    py::class_<NativeCampaignEnv>(module, "CampaignEnv",
        "Native operations release Python's lock. Each environment protects its own state; "
        "independent environments and clones can execute concurrently.")
        .def(py::init([](const std::string& scenario, std::uint64_t seed, bool trainingActions) {
            py::gil_scoped_release release;
            return std::make_unique<NativeCampaignEnv>(
                CampaignEnv(std::filesystem::path(scenario), seed, trainingActions));
        }), py::arg("scenario_path"), py::arg("seed") = 1, py::arg("training_actions") = false)
        .def_static("curriculum", [](const std::string& scenario, int rounds, std::uint64_t seed, bool trainingActions) {
            py::gil_scoped_release release;
            return std::make_unique<NativeCampaignEnv>(
                CampaignEnv::curriculum(std::filesystem::path(scenario), rounds, seed, trainingActions));
        }, py::arg("scenario_path"), py::arg("calendar_rounds"), py::arg("seed") = 1, py::arg("training_actions") = false)
        .def("is_terminal", [](const NativeCampaignEnv& self) {
            return self.call([](const CampaignEnv& env) { return env.isTerminal(); });
        })
        .def("current_decision_player", [](const NativeCampaignEnv& self) {
            return self.call([](const CampaignEnv& env) { return env.currentDecisionPlayer(); });
        })
        .def("current_nation", [](const NativeCampaignEnv& self) {
            return self.call([](const CampaignEnv& env) { return env.currentNation(); });
        })
        .def("decision_kind", [](const NativeCampaignEnv& self) {
            return self.call([](const CampaignEnv& env) { return env.decisionKind(); });
        })
        .def("legal_actions", [](const NativeCampaignEnv& self) {
            return self.call([](const CampaignEnv& env) { return env.legalActions(); });
        })
        .def("legal_interrupts", [](const NativeCampaignEnv& self) {
            return self.call([](const CampaignEnv& env) { return env.legalInterrupts(); });
        })
        .def("apply_action", [](NativeCampaignEnv& self, game::campaign::Action action) {
            self.call([&](CampaignEnv& env) { env.applyAction(action); });
        })
        .def("apply_interrupt", [](NativeCampaignEnv& self, game::campaign::Action action) {
            self.call([&](CampaignEnv& env) { env.applyInterrupt(action); });
        })
        .def("resolve_chance", [](NativeCampaignEnv& self) {
            self.call([](CampaignEnv& env) { env.resolveChance(); });
        })
        .def("chance_request", [](const NativeCampaignEnv& self) {
            auto text = self.call([](const CampaignEnv& env) {
                return game::campaign::canonicalJson(env.chanceRequest());
            });
            return py::module_::import("json").attr("loads")(text);
        })
        .def("apply_chance_outcome", [](NativeCampaignEnv& self, const std::string& expectedKey,
                const py::object& faces) {
            if (!py::isinstance<py::list>(faces) && !py::isinstance<py::tuple>(faces))
                throw py::type_error("Chance faces must be nested integer lists or tuples");
            game::campaign::ChanceOutcome outcome;
            for (py::handle die : faces.cast<py::sequence>()) {
                if (!py::isinstance<py::list>(die) && !py::isinstance<py::tuple>(die))
                    throw py::type_error("Each die requires its complete integer face sequence");
                std::vector<int> values;
                for (py::handle face : py::reinterpret_borrow<py::sequence>(die)) {
                    if (!PyLong_CheckExact(face.ptr()))
                        throw py::type_error("Chance faces must be integers, not booleans or converted numbers");
                    values.push_back(py::cast<int>(face));
                }
                outcome.faces.push_back(std::move(values));
            }
            self.call([&](CampaignEnv& env) {
                env.applyChanceOutcome(expectedKey, outcome);
            });
        }, py::arg("expected_key"), py::arg("faces"))
        .def("returns", [](const NativeCampaignEnv& self) {
            return self.call([](const CampaignEnv& env) { return env.returns(); });
        })
        .def("wealth", [](const NativeCampaignEnv& self) {
            auto text = self.call([](const CampaignEnv& env) { return game::campaign::canonicalJson(env.wealth()); });
            return py::module_::import("json").attr("loads")(text);
        })
        .def("observation", [](const NativeCampaignEnv& self) {
            auto text = self.call([](const CampaignEnv& env) { return game::campaign::canonicalJson(env.observation()); });
            return py::module_::import("json").attr("loads")(text);
        })
        .def("numeric_observation", [](const NativeCampaignEnv& self) {
            return NumericSnapshot{self.call([](const CampaignEnv& env) { return env.observationWithoutMenu(); }), {}};
        })
        .def("numeric_context", [](const NativeCampaignEnv& self) {
            return NumericSnapshot{self.call([](const CampaignEnv& env) { return env.contextSnapshot(); }), {}};
        })
        .def("zone_encoding_spec", [](const NativeCampaignEnv& self) {
            const auto spec = self.call([](const CampaignEnv& env) {
                return game::campaign::zoneEncodingSpec(env.engine().state());
            });
            const auto floats = [](const std::vector<float>& values, int columns) {
                const auto rows = columns ? static_cast<py::ssize_t>(values.size() / static_cast<std::size_t>(columns)) : 0;
                py::array_t<float> out({rows, static_cast<py::ssize_t>(columns)});
                if (!values.empty()) std::memcpy(out.mutable_data(), values.data(), values.size() * sizeof(float));
                return out;
            };
            py::dict out;
            out["version"] = spec->version;
            out["zones"] = spec->zones;
            out["nations"] = spec->nations;
            out["unit_types"] = spec->unitTypes;
            out["facility_types"] = spec->facilityTypes;
            out["technologies"] = spec->technologies;
            out["project_types"] = spec->projectTypes;
            out["rows"] = spec->rows;
            out["zone_columns"] = spec->zoneColumns;
            out["global_columns"] = spec->globalColumns;
            out["action_columns"] = spec->actionColumns;
            out["zone_static"] = floats(spec->zoneStatic, spec->staticFeatures);
            out["edge_source"] = int32Array(spec->edgeSource);
            out["edge_target"] = int32Array(spec->edgeTarget);
            out["edge_static"] = floats(spec->edgeStatic, spec->edgeFeatures);
            out["zone_column_names"] = spec->zoneColumnNames;
            out["global_column_names"] = spec->globalColumnNames;
            out["action_column_names"] = spec->actionColumnNames;
            out["static_feature_names"] = spec->staticFeatureNames;
            out["edge_feature_names"] = spec->edgeFeatureNames;
            return out;
        })
        .def("zone_input", [](const NativeCampaignEnv& self, const std::optional<std::string>& owner,
                              const std::string& decisionKind, const std::optional<std::string>& offered,
                              const std::vector<std::string>& passed, const std::vector<std::string>& order,
                              const py::list& options) {
            // Options stay owned by the caller's list, which outlives the native call.
            std::vector<game::campaign::ZoneOption> converted;
            converted.reserve(options.size());
            for (const auto& item : options) {
                const auto tuple = item.cast<py::tuple>();
                if (tuple.size() != 3) throw std::invalid_argument("Each zone option is (kind, player, action or None)");
                game::campaign::ZoneOption option;
                option.kind = tuple[0].cast<std::string>();
                option.player = tuple[1].is_none() ? std::string() : tuple[1].cast<std::string>();
                if (!tuple[2].is_none()) option.action = &tuple[2].cast<const game::campaign::Action&>();
                converted.push_back(std::move(option));
            }
            const game::campaign::ZoneSchedule schedule{owner, decisionKind, offered, passed, order};
            return self.call([&](const CampaignEnv& env) {
                const auto& state = env.engine().state();
                auto input = std::make_shared<const ZoneInput>(game::campaign::encodeZoneInput(state, schedule, converted));
                return ZoneInputHandle{std::move(input), game::campaign::zoneEncodingSpec(state)->version};
            });
        }, py::arg("owner"), py::arg("decision_kind"), py::arg("offered"), py::arg("passed"), py::arg("order"),
           py::arg("options"))
        .def("context", [](const NativeCampaignEnv& self) {
            auto text = self.call([](const CampaignEnv& env) { return game::campaign::canonicalJson(env.context()); });
            return py::module_::import("json").attr("loads")(text);
        })
        .def("clone", [](const NativeCampaignEnv& self) {
            return self.call([](const CampaignEnv& env) {
                return std::make_unique<NativeCampaignEnv>(env.clone());
            });
        })
        .def("clone_for_search", [](const NativeCampaignEnv& self, std::uint64_t seed) {
            return self.call([&](const CampaignEnv& env) {
                return std::make_unique<NativeCampaignEnv>(env.cloneForSearch(seed));
            });
        })
        .def("planning_key", [](const NativeCampaignEnv& self) {
            return self.call([](const CampaignEnv& env) { return env.planningKey(); });
        })
        // Whether every airborne aircraft still has a reachable joint landing
        // plan, and how many no plan lands; random-play testing checks that
        // no move raises that number.
        .def("landing_plan_reachable", [](const NativeCampaignEnv& self) {
            return self.call([](const CampaignEnv& env) {
                return game::campaign::airLandingPlanReachable(env.engine().state());
            });
        })
        .def("landing_shortfall", [](const NativeCampaignEnv& self) {
            return self.call([](const CampaignEnv& env) {
                return game::campaign::airLandingShortfall(env.engine().state());
            });
        })
        .def("serialize", [](const NativeCampaignEnv& self) {
            return self.call([](const CampaignEnv& env) { return env.serialize(); });
        })
        .def("history_size", [](const NativeCampaignEnv& self) {
            return self.call([](const CampaignEnv& env) { return env.historySize(); });
        })
        .def("history_since", [](const NativeCampaignEnv& self, std::size_t index) {
            auto text = self.call([&](const CampaignEnv& env) { return game::campaign::canonicalJson(env.historySince(index)); });
            return py::module_::import("json").attr("loads")(text);
        }, py::arg("index"))
        .def("restore", [](NativeCampaignEnv& self, const std::string& serialized) {
            self.call([&](CampaignEnv& env) { env.restore(serialized); });
        });
    module.attr("CAMPAIGN_SCHEMA") = "campaign_entities_v1";
    module.attr("CAMPAIGN_ACTION_SCHEMA") = game::campaign::trainingActionSchema;

    py::class_<game::BenchmarkStepResult>(module, "StepResult")
        .def_readonly("acting_nation", &game::BenchmarkStepResult::actingNation)
        .def_readonly("action", &game::BenchmarkStepResult::action)
        .def_readonly("detail_lines", &game::BenchmarkStepResult::detailLines)
        .def_readonly("terminal", &game::BenchmarkStepResult::terminal);

    py::class_<game::CampaignBenchmarkEnv>(module, "CampaignBenchmarkEnv")
        .def("reset", &game::CampaignBenchmarkEnv::reset)
        .def("reset_with_seed", &game::CampaignBenchmarkEnv::resetWithSeed)
        .def("is_terminal", &game::CampaignBenchmarkEnv::isTerminal)
        .def("current_nation", &game::CampaignBenchmarkEnv::currentNation)
        .def("current_phase", &game::CampaignBenchmarkEnv::currentPhase)
        .def("legal_actions", &game::CampaignBenchmarkEnv::legalActions)
        .def("legal_interrupts", &game::CampaignBenchmarkEnv::legalInterrupts)
        .def("encode_state", &game::CampaignBenchmarkEnv::encodeState)
        .def("encode_legal_actions", &game::CampaignBenchmarkEnv::encodeLegalActions)
        .def("state_feature_labels", &game::CampaignBenchmarkEnv::stateFeatureLabels)
        .def("action_feature_labels", &game::CampaignBenchmarkEnv::actionFeatureLabels)
        .def("step", &game::CampaignBenchmarkEnv::step)
        .def("completed_turns_for", &game::CampaignBenchmarkEnv::completedTurnsFor)
        .def("nation_income", &game::CampaignBenchmarkEnv::nationIncome)
        .def("nation_treasury", &game::CampaignBenchmarkEnv::nationTreasury)
        .def("unit_count_for", &game::CampaignBenchmarkEnv::unitCountFor)
        .def("unit_value_for", &game::CampaignBenchmarkEnv::unitValueFor)
        .def("enemy_unit_value_destroyed_by_nation", &game::CampaignBenchmarkEnv::enemyUnitValueDestroyedByNation)
        .def("serialize", &game::CampaignBenchmarkEnv::serialize)
        .def("restore", &game::CampaignBenchmarkEnv::restore)
        .def("set_dice_tape_for_testing", &game::CampaignBenchmarkEnv::setDiceTapeForTesting);

    py::class_<game::JapanTrainingEnv, game::CampaignBenchmarkEnv>(module, "JapanTrainingEnv")
        .def(py::init([](const std::string &scenarioPath, const std::string &trackedNationId, std::uint64_t seed) {
            return game::JapanTrainingEnv(std::filesystem::path(scenarioPath), trackedNationId, seed);
        }), py::arg("scenario_path"), py::arg("tracked_nation_id") = "Japan", py::arg("seed") = 1)
        .def("clone", [](const game::JapanTrainingEnv &env) { return std::make_unique<game::JapanTrainingEnv>(env.clone()); })
        .def("clone_for_search", &game::JapanTrainingEnv::cloneForSearch)
        .def("final_reward", &game::JapanTrainingEnv::finalReward);

    py::class_<game::CompositionBattleEnv, game::CampaignBenchmarkEnv>(module, "CompositionBattleEnv")
        .def(py::init<int, int, std::string, bool, std::uint64_t>(),
            py::arg("attacker_budget") = 10, py::arg("defender_budget") = 10,
            py::arg("terrain") = "normal", py::arg("is_city") = false, py::arg("seed") = 1)
        .def("clone", [](const game::CompositionBattleEnv &env) { return std::make_unique<game::CompositionBattleEnv>(env.clone()); })
        .def("clone_for_search", &game::CompositionBattleEnv::cloneForSearch)
        .def("final_reward", &game::CompositionBattleEnv::finalReward)
        .def("terminal_reward_for", &game::CompositionBattleEnv::terminalRewardFor)
        .def("winner_id", &game::CompositionBattleEnv::winnerId)
        .def("budget_remaining", &game::CompositionBattleEnv::budgetRemaining)
        .def("purchased_unit_count", &game::CompositionBattleEnv::purchasedUnitCount);
    module.attr("BENCHMARK_SCHEMA") = "campaign_v1";
}
