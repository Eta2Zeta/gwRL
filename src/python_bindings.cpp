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

namespace py = pybind11;

namespace {

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

    py::class_<game::campaign::CampaignEnv>(module, "CampaignEnv")
        .def(py::init([](const std::string& scenario, std::uint64_t seed, bool trainingActions) {
            return game::campaign::CampaignEnv(std::filesystem::path(scenario), seed, trainingActions);
        }), py::arg("scenario_path"), py::arg("seed") = 1, py::arg("training_actions") = false)
        .def_static("curriculum", [](const std::string& scenario, int rounds, std::uint64_t seed, bool trainingActions) {
            return game::campaign::CampaignEnv::curriculum(std::filesystem::path(scenario), rounds, seed, trainingActions);
        }, py::arg("scenario_path"), py::arg("calendar_rounds"), py::arg("seed") = 1, py::arg("training_actions") = false)
        .def("is_terminal", &game::campaign::CampaignEnv::isTerminal)
        .def("current_decision_player", &game::campaign::CampaignEnv::currentDecisionPlayer)
        .def("current_nation", &game::campaign::CampaignEnv::currentNation)
        .def("decision_kind", &game::campaign::CampaignEnv::decisionKind)
        .def("legal_actions", &game::campaign::CampaignEnv::legalActions)
        .def("legal_interrupts", &game::campaign::CampaignEnv::legalInterrupts)
        .def("apply_action", &game::campaign::CampaignEnv::applyAction)
        .def("apply_interrupt", &game::campaign::CampaignEnv::applyInterrupt)
        .def("resolve_chance", &game::campaign::CampaignEnv::resolveChance)
        .def("returns", &game::campaign::CampaignEnv::returns)
        .def("wealth", [](const game::campaign::CampaignEnv& env) {
            return py::module_::import("json").attr("loads")(game::campaign::canonicalJson(env.wealth()));
        })
        .def("observation", [](const game::campaign::CampaignEnv& env) {
            return py::module_::import("json").attr("loads")(game::campaign::canonicalJson(env.observation()));
        })
        .def("context", [](const game::campaign::CampaignEnv& env) {
            return py::module_::import("json").attr("loads")(game::campaign::canonicalJson(env.context()));
        })
        .def("clone", &game::campaign::CampaignEnv::clone)
        .def("clone_for_search", &game::campaign::CampaignEnv::cloneForSearch)
        .def("planning_key", &game::campaign::CampaignEnv::planningKey)
        .def("serialize", &game::campaign::CampaignEnv::serialize)
        .def("history_size", &game::campaign::CampaignEnv::historySize)
        .def("history_since", [](const game::campaign::CampaignEnv& env, std::size_t index) {
            return py::module_::import("json").attr("loads")(game::campaign::canonicalJson(env.historySince(index)));
        }, py::arg("index"))
        .def("restore", &game::campaign::CampaignEnv::restore);
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
