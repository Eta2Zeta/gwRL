#include "game/action.hpp"
#include "game/composition_battle_env.hpp"
#include "game/japan_training_env.hpp"
#include "game/mdp.hpp"
#include "game/campaign_env.hpp"
#include "game/campaign_actions.hpp"
#include "game/neural_graph.hpp"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

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

    module.def("compile_campaign_graph", &game::neural::compileCampaignGraph,
               py::arg("value"), py::arg("buckets"), py::arg("lexical_ids"),
               py::arg("string_descriptor"), py::arg("numeric_features"),
               "Compile complete public JSON features without engine state or learned tensors.");

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
