#include "game/air.hpp"
#include "game/campaign_env.hpp"
#include "game/campaign_actions.hpp"
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
#include <unordered_map>
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

    // Both boards' operations held at once, without lock-order deadlock.
    template <class Function> auto callWith(const NativeCampaignEnv& other, Function&& function) const {
        py::gil_scoped_release release;
        if (this == &other) {
            std::lock_guard lock(mutex_);
            return std::forward<Function>(function)(std::as_const(env_), std::as_const(env_));
        }
        std::scoped_lock lock(mutex_, other.mutex_);
        return std::forward<Function>(function)(std::as_const(env_), std::as_const(other.env_));
    }

  private:
    game::campaign::CampaignEnv env_;
    mutable std::mutex mutex_;
};

using CampaignEnv = game::campaign::CampaignEnv;

using ZoneInput = game::campaign::ZoneInput;

// One encoded decision, immutable and shared between Python objects.
struct ZoneInputHandle {
    std::shared_ptr<const ZoneInput> input;
    std::string version;
};

constexpr std::array<const char*, 13> zoneArrayNames{
    "zone_index", "zone_column", "zone_value", "global_column", "global_value", "action_offsets",
    "action_column", "action_value", "action_source", "action_target", "path_offsets", "path_zone",
    "factor_groups"};

std::array<const std::vector<std::int32_t>*, 13> zoneFields(const ZoneInput& z) {
    return {&z.zoneIndex, &z.zoneColumn, &z.zoneValue, &z.globalColumn, &z.globalValue, &z.actionOffsets,
            &z.actionColumn, &z.actionValue, &z.actionSource, &z.actionTarget, &z.pathOffsets, &z.pathZone,
            &z.factorGroups};
}

std::array<std::vector<std::int32_t>*, 13> zoneFields(ZoneInput& z) {
    return {&z.zoneIndex, &z.zoneColumn, &z.zoneValue, &z.globalColumn, &z.globalValue, &z.actionOffsets,
            &z.actionColumn, &z.actionValue, &z.actionSource, &z.actionTarget, &z.pathOffsets, &z.pathZone,
            &z.factorGroups};
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

// What the network relies on: fields that fit together, zones in order, and
// policy groups numbered densely, each group inside one group of the level above.
void validateZoneInput(const ZoneInput& z) {
    const auto offsets = [](const std::vector<std::int32_t>& o, std::size_t entries, std::size_t count) {
        if (o.size() != count + 1 || o.front() != 0 || static_cast<std::size_t>(o.back()) != entries ||
            !std::is_sorted(o.begin(), o.end()))
            throw std::invalid_argument("Zone input offsets are inconsistent");
    };
    const auto options = z.actionSource.size();
    if (z.zoneIndex.size() != z.zoneColumn.size() || z.zoneIndex.size() != z.zoneValue.size() ||
        z.globalColumn.size() != z.globalValue.size() || z.actionColumn.size() != z.actionValue.size() ||
        z.actionSource.size() != z.actionTarget.size() || z.factorGroups.size() != 4 * options)
        throw std::invalid_argument("Zone input fields differ in length");
    if (!std::is_sorted(z.zoneIndex.begin(), z.zoneIndex.end()))
        throw std::invalid_argument("Zone input entries are not in zone order");
    offsets(z.actionOffsets, z.actionColumn.size(), options);
    offsets(z.pathOffsets, z.pathZone.size(), options);
    std::vector<std::int32_t> above(options, 0), parent;
    for (std::size_t level = 0; level < 4; ++level) {
        std::int32_t groups = 0;
        for (std::size_t i = 0; i < options; ++i) groups = std::max(groups, z.factorGroups[4 * i + level] + 1);
        parent.assign(static_cast<std::size_t>(groups), -1);
        for (std::size_t i = 0; i < options; ++i) {
            const auto group = z.factorGroups[4 * i + level];
            if (group < 0) throw std::invalid_argument("Zone policy groups must be nonnegative");
            auto& seen = parent[static_cast<std::size_t>(group)];
            if (seen != -1 && seen != above[i]) throw std::invalid_argument("Zone policy groups are not nested");
            seen = above[i];
        }
        if (std::find(parent.begin(), parent.end(), -1) != parent.end())
            throw std::invalid_argument("Zone policy groups are not numbered densely");
        for (std::size_t i = 0; i < options; ++i) above[i] = z.factorGroups[4 * i + level];
    }
}

ZoneInput zoneFromArrays(const py::dict& arrays) {
    ZoneInput z;
    const auto fields = zoneFields(z);
    for (std::size_t i = 0; i < fields.size(); ++i) {
        if (!arrays.contains(zoneArrayNames[i])) throw std::invalid_argument(std::string("Zone input lacks ") + zoneArrayNames[i]);
        *fields[i] = int32Vector(arrays[zoneArrayNames[i]]);
    }
    if (arrays.size() != fields.size()) throw std::invalid_argument("Zone input has unknown fields");
    validateZoneInput(z);
    return z;
}

py::dict zoneArrays(const ZoneInput& z) {
    py::dict out;
    const auto fields = zoneFields(z);
    for (std::size_t i = 0; i < fields.size(); ++i) out[zoneArrayNames[i]] = int32Array(*fields[i]);
    return out;
}

// The same position with only the listed options, in the listed order. Policy
// groups are renumbered from zero in order of first appearance.
ZoneInput selectZoneOptions(const ZoneInput& z, const std::vector<int>& indices) {
    ZoneInput out;
    out.zoneIndex = z.zoneIndex;
    out.zoneColumn = z.zoneColumn;
    out.zoneValue = z.zoneValue;
    out.globalColumn = z.globalColumn;
    out.globalValue = z.globalValue;
    std::array<std::unordered_map<std::int32_t, std::int32_t>, 4> renumbered;
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
        for (std::size_t level = 0; level < 4; ++level) {
            auto& map = renumbered[level];
            const auto next = static_cast<std::int32_t>(map.size());
            out.factorGroups.push_back(map.try_emplace(z.factorGroups[4 * i + level], next).first->second);
        }
    }
    return out;
}

bool sameZoneInput(const ZoneInput& a, const ZoneInput& b) {
    const auto left = zoneFields(a), right = zoneFields(b);
    for (std::size_t i = 0; i < left.size(); ++i)
        if (*left[i] != *right[i]) return false;
    return true;
}

}  // namespace

PYBIND11_MODULE(gwrl_cpp, module) {
    module.doc() = "C++ training environment bindings for gwRL";

    py::class_<ZoneInputHandle>(module, "CampaignZoneInput",
        "One campaign decision in the fixed zone encoding: nonzero answers to fixed per-zone, "
        "per-position and per-option questions, and each option's four policy groups. "
        "Immutable; copies share the native arrays.")
        .def("arrays", [](const ZoneInputHandle& self) { return zoneArrays(*self.input); },
             "Fresh int32 copies of every field; factor_groups holds four ids per option.")
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
        // Immutable: a copy is the object itself, as for a tuple.
        .def("__copy__", [](py::object self) { return self; })
        .def("__deepcopy__", [](py::object self, py::dict) { return self; })
        .def(py::pickle(
            [](const ZoneInputHandle& self) { return py::make_tuple(self.version, zoneArrays(*self.input)); },
            [](const py::tuple& state) {
                if (state.size() != 2) throw std::invalid_argument("Invalid zone input pickle");
                return ZoneInputHandle{std::make_shared<const ZoneInput>(zoneFromArrays(state[1].cast<py::dict>())),
                                       state[0].cast<std::string>()};
            }));
    module.def("campaign_zone_input", [](const std::string& version, const py::dict& arrays) {
        return ZoneInputHandle{std::make_shared<const ZoneInput>(zoneFromArrays(arrays)), version};
    }, py::arg("version"), py::arg("arrays"),
       "Rebuild a zone input from its arrays, checking that its fields fit together.");
    module.def("zone_encoding_unknowns", [](bool reset) { return game::campaign::zoneEncodingUnknowns(reset); },
               py::arg("reset") = false,
               "Names counted in an \"other\" column of the zone encoding since the last reset.");

    py::class_<game::campaign::Action>(module, "CampaignAction")
        .def_readonly("id", &game::campaign::Action::id)
        .def_readonly("kind", &game::campaign::Action::kind)
        .def_readonly("nation", &game::campaign::Action::nation)
        .def_readonly("player", &game::campaign::Action::player)
        .def_readonly("decision", &game::campaign::Action::decision)
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
        .def("clone_for_search_continuing", [](const NativeCampaignEnv& self, const NativeCampaignEnv& source) {
            return self.callWith(source, [](const CampaignEnv& env, const CampaignEnv& stream) {
                return std::make_unique<NativeCampaignEnv>(env.cloneForSearchContinuing(stream));
            });
        }, py::arg("source"),
           "A search copy of this position whose dice continue source's search stream.")
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
}
