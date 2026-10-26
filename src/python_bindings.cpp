#include "game/action.hpp"
#include "game/composition_battle_env.hpp"
#include "game/japan_training_env.hpp"
#include "game/mdp.hpp"
#include "game/campaign_env.hpp"
#include "game/income_batch.hpp"
#include "game/device_state.hpp"
#include "game/income_ledger_batch.hpp"
#include "game/wealth_context.hpp"
#include "game/relations_context.hpp"
#include "game/movement_context.hpp"
#include "game/catalog_stats_context.hpp"
#include "game/campaign_actions.hpp"
#include "game/neural_graph.hpp"
#include "game/numeric_graph.hpp"

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <limits>
#include <pybind11/stl.h>

#include <stdexcept>
#include <string>
#include <memory>
#include <mutex>
#include <utility>
#include <chrono>
#include <bit>

namespace py = pybind11;

namespace {

// Keep Python's synchronization policy at its boundary, not in the rules core.
// Each bound environment owns its operation mutex; cloned boards get new ones.
// Always release the GIL BEFORE waiting for this mutex. The reverse order could
// deadlock with a native operation that is returning to Python. Owned native
// results are prepared under the mutex, which is released before GIL reacquire.
struct IncomeNativeAccess;
struct DeviceStateNativeAccess;
struct IncomeLedgerNativeAccess;
struct WealthNativeAccess;
struct StateJsonNativeAccess;
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
    friend struct IncomeNativeAccess;
    friend struct DeviceStateNativeAccess;
    friend struct IncomeLedgerNativeAccess;
    friend struct WealthNativeAccess;
    friend struct RelationsNativeAccess;
    friend struct StateJsonNativeAccess;
    friend struct CatalogStatsNativeAccess;
    game::campaign::CampaignEnv env_;
    mutable std::mutex mutex_;
};

// Vector<Env*> casters do not retain each Python wrapper if another thread
// clears the caller's mutable list while native code releases the GIL.
std::vector<py::object> pinNativeEnvironments(const std::vector<NativeCampaignEnv*>& envs) {
    std::vector<py::object> owners;
    owners.reserve(envs.size());
    for (auto* env : envs) {
        if (!env) throw std::invalid_argument("Null campaign lane");
        owners.emplace_back(py::cast(env, py::return_value_policy::reference));
    }
    return owners;
}

struct IncomeNativeAccess {
    using Context=game::campaign::IncomeContext;
    using Batch=game::campaign::IncomeBatch;
    using Oracle=game::campaign::IncomeOracleBatch;
    static std::shared_ptr<Context> context(const NativeCampaignEnv& env) {
        return env.call([](const auto& value){return std::make_shared<Context>(*value.engine().state().definition);});
    }
    static Batch capture(std::shared_ptr<Context> context,const std::vector<NativeCampaignEnv*>& envs) {
        const auto owners = pinNativeEnvironments(envs);
        py::gil_scoped_release release;
        Batch out(context,envs.size());
        for(std::size_t row=0;row<envs.size();++row) {
            if(!envs[row])throw std::invalid_argument("Null income lane");
            std::lock_guard lock(envs[row]->mutex_);
            out.capture(row,envs[row]->env_.engine().state());
        }
        return out;
    }
    static Oracle oracle(std::shared_ptr<Context> context,const std::vector<NativeCampaignEnv*>& envs) {
        const auto owners = pinNativeEnvironments(envs);
        py::gil_scoped_release release;
        Oracle out(context,envs.size());
        for(std::size_t row=0;row<envs.size();++row) {
            if(!envs[row])throw std::invalid_argument("Null income lane");
            std::lock_guard lock(envs[row]->mutex_);
            out.capture(row,envs[row]->env_.engine().state());
        }
        return out;
    }
    static py::dict benchmark(const std::vector<NativeCampaignEnv*>& envs,std::size_t repeats) {
        if(!repeats)throw std::invalid_argument("Positive income repetitions required");
        const auto owners = pinNativeEnvironments(envs);
        std::uint64_t calls=0,checksum=0;double seconds=0;
        {
            py::gil_scoped_release release;
            const auto before=std::chrono::steady_clock::now();
            for(std::size_t repeat=0;repeat<repeats;++repeat)for(const auto* env:envs) {
                if(!env)throw std::invalid_argument("Null income lane");
                std::lock_guard lock(env->mutex_);
                const auto& state=env->env_.engine().state();
                for(const auto& [id,_]:state.nations) {
                    const auto value=game::campaign::evaluateIncome(state,id);
                    checksum=checksum*131+static_cast<std::uint64_t>(value.total)+value.collectable;
                    ++calls;
                }
            }
            seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-before).count();
        }
        py::dict result;result["calls"]=calls;result["checksum"]=checksum;result["seconds"]=seconds;
        return result;
    }
};

// Read-only NumPy views own their native object. All shape/size arithmetic is
// representability-checked; there is no gameplay/entity/batch truncation cap.
template<class Owner>
py::array incomeArray(const Owner& object,const std::vector<std::int64_t>& data,
                      std::vector<py::ssize_t> shape) {
    std::vector<py::ssize_t> strides(shape.size());
    py::ssize_t stride=sizeof(std::int64_t);
    for(std::size_t i=shape.size();i--;) {
        strides[i]=stride;
        if(shape[i]<0 || (shape[i] && stride>std::numeric_limits<py::ssize_t>::max()/shape[i]))
            throw std::overflow_error("Income buffer dimension overflow");
        stride*=shape[i];
    }
    auto result=py::array(py::dtype::of<std::int64_t>(),shape,strides,data.data(),
                          py::cast(&object,py::return_value_policy::reference));
    result.attr("setflags")(py::arg("write")=false);
    return result;
}

// Call bindIncome(module) after the existing CampaignEnv class registration.
void bindIncome(py::module_& module) {
    using C=IncomeNativeAccess::Context;using B=IncomeNativeAccess::Batch;using O=IncomeNativeAccess::Oracle;
    py::class_<C,std::shared_ptr<C>>(module,"CampaignIncomeContext")
        .def_property_readonly("definition_fingerprint",[](const C& c){return c.definitionFingerprint;})
        .def_property_readonly("territory_ids",[](const C& c){return c.territories;})
        .def_property_readonly("nation_ids",[](const C& c){return c.nations;})
        .def_property_readonly("int_minimum",[](const C& c){return c.intMinimum;})
        .def_property_readonly("int_maximum",[](const C& c){return c.intMaximum;})
        .def("territory_array",[](const C& c){return incomeArray(c,c.territoryStatic,{static_cast<py::ssize_t>(c.territories.size()),3});})
        .def("nation_array",[](const C& c){return incomeArray(c,c.nationStatic,{static_cast<py::ssize_t>(c.nations.size()),2});});
    py::class_<B>(module,"CampaignIncomeBatch")
        .def_property_readonly("context",[](const B& b){return std::const_pointer_cast<C>(b.context);})
        .def("territory_array",[](const B& b){return incomeArray(b,b.territoryState,{static_cast<py::ssize_t>(b.rows),static_cast<py::ssize_t>(b.context->territories.size()),4});})
        .def("nation_array",[](const B& b){return incomeArray(b,b.nationState,{static_cast<py::ssize_t>(b.rows),static_cast<py::ssize_t>(b.context->nations.size()),6});});
    py::class_<O>(module,"CampaignIncomeOracleBatch")
        .def("income_array",[](const O& o){return incomeArray(o,o.income,{static_cast<py::ssize_t>(o.rows),static_cast<py::ssize_t>(o.context->nations.size()),6});})
        .def("effective_array",[](const O& o){return incomeArray(o,o.effective,{static_cast<py::ssize_t>(o.rows),static_cast<py::ssize_t>(o.context->territories.size()),2});});
    module.def("campaign_income_context",&IncomeNativeAccess::context);
    module.def("capture_campaign_income",&IncomeNativeAccess::capture);
    module.def("campaign_income_oracle",&IncomeNativeAccess::oracle);
    module.def("benchmark_campaign_income_oracle",&IncomeNativeAccess::benchmark);
}

using CampaignEnv = game::campaign::CampaignEnv;

#include "python_device_state.inc"
#include "python_income_ledger.inc"
#include "python_random_metal.inc"
#include "python_wealth.inc"
#include "python_relations.inc"
#include "python_movement_context.inc"
#include "python_content_digest.inc"
#include "python_canonical_json.inc"
#include "python_state_json.inc"
#include "python_action_ids.inc"
#include "python_catalog_stats.inc"
#include "python_event_append.inc"

// Immutable owning views outlive an environment mutation without copying its
// state tree. Only small scheduler fields overlay the complete native document.
struct NumericSnapshot {
    using V = game::json::Value;
    std::shared_ptr<const V> source;
    V::Object overrides;
    std::shared_ptr<const std::string> actionSourceKey;
    bool passAction {false};

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
            const std::vector<NumericSnapshot>& actions, const std::string& schema,
            const std::vector<std::string>& order, const std::vector<std::string>& passed) const {
        auto result = scheduledContext(schema, order);
        result.overrides["current_decision_player"] = owner ? V(*owner) : V(nullptr);
        result.overrides["decision_kind"] = V(kind);
        V::Array menu, passSequence;
        for (const auto& action : actions) menu.emplace_back(action.materialize());
        for (const auto& player : passed) passSequence.emplace_back(player);
        result.overrides["legal_actions"] = V(std::move(menu));
        auto scheduler = result.overrides.at("interrupt_scheduler").asObject();
        scheduler["passed"] = V(std::move(passSequence));
        result.overrides["interrupt_scheduler"] = V(std::move(scheduler));
        return result;
    }

    static NumericSnapshot scheduledAction(const game::campaign::Action* action,
            const std::string& id, const std::string& kind, const std::string& player) {
        return {std::make_shared<const V>(V::Object{{"id", V(id)}, {"kind", V(kind)},
            {"player", V(player)}, {"action", action ? game::campaign::actionJson(*action) : V(nullptr)}}), {},
            action ? action->neuralSourceKey : nullptr, action == nullptr};
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

}  // namespace

PYBIND11_MODULE(gwrl_cpp, module) {
    module.doc() = "C++ training environment bindings for gwRL";

    module.def("campaign_effective_results_probe", [](const std::vector<std::string>& requestJson,
            const std::vector<std::string>& outcomeJson, const py::object& repetitions) {
        if (!PyLong_CheckExact(repetitions.ptr())) throw py::type_error("Probe repetitions must be an integer");
        const auto count = py::cast<std::int64_t>(repetitions);
        if (count < 1 || count > 1000000) throw py::value_error("Probe repetitions must be in [1, 1000000]");
        if (requestJson.size() != outcomeJson.size()) throw py::value_error("Probe lane counts differ");
        std::vector<std::vector<int>> results(requestJson.size());
        double preparationSeconds = 0, rulesSeconds = 0;
        {
            py::gil_scoped_release release;
            const auto preparation = std::chrono::steady_clock::now();
            std::vector<game::campaign::ChanceRequest> requests;
            std::vector<game::campaign::ChanceOutcome> outcomes;
            requests.reserve(requestJson.size()); outcomes.reserve(outcomeJson.size());
            for (std::size_t lane = 0; lane < requestJson.size(); ++lane) {
                requests.push_back(game::campaign::chanceRequestFromJson(game::json::parse(requestJson[lane])));
                outcomes.push_back(game::campaign::outcomeFromJson(game::json::parse(outcomeJson[lane])));
            }
            preparationSeconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - preparation).count();
            const auto started = std::chrono::steady_clock::now();
            for (std::int64_t repetition = 0; repetition < count; ++repetition)
                for (std::size_t lane = 0; lane < requests.size(); ++lane)
                    results[lane] = game::campaign::effectiveResults(requests[lane], outcomes[lane]);
            rulesSeconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
        }
        py::dict report;
        report["results"] = results;
        report["preparation_seconds"] = preparationSeconds;
        report["rules_seconds"] = rulesSeconds;
        report["repetitions"] = count;
        report["lanes"] = requestJson.size();
        return report;
    }, py::arg("request_jsons"), py::arg("outcome_jsons"), py::arg("repetitions") = py::int_(1),
       "Benchmark/conformance probe only: parse once, time the authoritative native dice primitive without Python lane calls.");

    module.def("compile_campaign_graph", &game::neural::compileCampaignGraph,
               py::arg("value"), py::arg("buckets"), py::arg("lexical_ids"),
               py::arg("string_descriptor"), py::arg("numeric_features"),
               "Compile complete public JSON features without engine state or learned tensors.");

    py::class_<NumericSnapshot>(module, "CampaignNumericSnapshot")
        .def_property_readonly("cache_key", &NumericSnapshot::cacheKey)
        .def("scheduled_context", &NumericSnapshot::scheduledContext, py::call_guard<py::gil_scoped_release>())
        .def("scheduled_observation", &NumericSnapshot::scheduledObservation, py::call_guard<py::gil_scoped_release>())
        .def("factor_json", &NumericSnapshot::factorJson, py::call_guard<py::gil_scoped_release>())
        .def("to_python", [](const NumericSnapshot& snapshot) {
            return py::module_::import("json").attr("loads")(game::campaign::canonicalJson(snapshot.materialize()));
        });
    module.def("campaign_pass_snapshot", [](const std::string& id, const std::string& kind, const std::string& player) {
        return NumericSnapshot::scheduledAction(nullptr, id, kind, player);
    }, py::call_guard<py::gil_scoped_release>());

    py::class_<game::neural::NumericGraph, std::shared_ptr<game::neural::NumericGraph>>(module, "CampaignNumericGraph")
        .def("arrays", &game::neural::NumericGraph::arrays)
        .def("__eq__", &game::neural::NumericGraph::equals, py::is_operator(), py::call_guard<py::gil_scoped_release>())
        .def("debug_graph", &game::neural::NumericGraph::debugGraph)
        .def("external_references", &game::neural::NumericGraph::externalReferences)
        .def_property_readonly("node_count", &game::neural::NumericGraph::nodeCount)
        .def_property_readonly("leaf_count", &game::neural::NumericGraph::leafCount)
        .def_property_readonly("token_buckets", &game::neural::NumericGraph::bucketCount)
        .def_property_readonly("nbytes", &game::neural::NumericGraph::retainedBytes)
        .def("packed_state", &game::neural::NumericGraph::packedState)
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
            return compiler.compile(*snapshot.source, snapshot.overrides);
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
            return NumericSnapshot::scheduledAction(&action, id, kind, player);
        }, py::call_guard<py::gil_scoped_release>())
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
            return NumericSnapshot{self.call([](const CampaignEnv& env) { return env.observationSnapshot(); }), {}};
        })
        .def("numeric_context", [](const NativeCampaignEnv& self) {
            return NumericSnapshot{self.call([](const CampaignEnv& env) { return env.contextSnapshot(); }), {}};
        })
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
    bindIncome(module);
    bindDeviceState(module);
    bindIncomeLedger(module);
    bindRandomProbe(module);
    bindWealth(module);
    bindRelations(module);
    bindMovementContext(module);
    bindContentDigestProbe(module);
    bindCanonicalJson(module);
    bindStateJson(module);
    bindActionIds(module);
    bindCatalogStats(module);
    bindEventAppendProbe(module);

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
