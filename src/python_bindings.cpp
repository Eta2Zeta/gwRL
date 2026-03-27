#include "game/action.hpp"
#include "game/composition_battle_env.hpp"
#include "game/japan_training_env.hpp"
#include "game/mdp.hpp"

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

    py::class_<game::StepResult>(module, "StepResult")
        .def_readonly("acting_nation", &game::StepResult::actingNation)
        .def_readonly("action", &game::StepResult::action)
        .def_readonly("detail_lines", &game::StepResult::detailLines)
        .def_readonly("terminal", &game::StepResult::terminal);

    py::class_<game::JapanTrainingEnv>(module, "JapanTrainingEnv")
        .def(py::init([](const std::string& scenarioPath, const std::string& trackedNationId) {
            return game::JapanTrainingEnv(std::filesystem::path(scenarioPath), trackedNationId);
        }), py::arg("scenario_path"), py::arg("tracked_nation_id") = "Japan")
        .def("reset", &game::JapanTrainingEnv::reset)
        .def("clone", [](const game::JapanTrainingEnv& env) {
            return std::make_unique<game::JapanTrainingEnv>(env.clone());
        })
        .def("is_terminal", &game::JapanTrainingEnv::isTerminal)
        .def("current_nation", &game::JapanTrainingEnv::currentNation)
        .def("current_phase", &game::JapanTrainingEnv::currentPhase)
        .def("legal_actions", &game::JapanTrainingEnv::legalActions)
        .def("encode_state", &game::JapanTrainingEnv::encodeState)
        .def("encode_legal_actions", &game::JapanTrainingEnv::encodeLegalActions)
        .def("state_feature_labels", &game::JapanTrainingEnv::stateFeatureLabels)
        .def("action_feature_labels", &game::JapanTrainingEnv::actionFeatureLabels)
        .def("step", &game::JapanTrainingEnv::step)
        .def("final_reward", &game::JapanTrainingEnv::finalReward)
        .def("completed_turns_for", &game::JapanTrainingEnv::completedTurnsFor)
        .def("nation_income", &game::JapanTrainingEnv::nationIncome)
        .def("nation_treasury", &game::JapanTrainingEnv::nationTreasury)
        .def("unit_count_for", &game::JapanTrainingEnv::unitCountFor)
        .def("unit_value_for", &game::JapanTrainingEnv::unitValueFor)
        .def("enemy_unit_value_destroyed_by_nation", &game::JapanTrainingEnv::enemyUnitValueDestroyedByNation);

    py::class_<game::CompositionBattleEnv>(module, "CompositionBattleEnv")
        .def(
            py::init<int, int, std::string, bool>(),
            py::arg("attacker_budget") = 10,
            py::arg("defender_budget") = 10,
            py::arg("terrain") = "normal",
            py::arg("is_city") = false)
        .def("reset", &game::CompositionBattleEnv::reset)
        .def("clone", [](const game::CompositionBattleEnv& env) {
            return std::make_unique<game::CompositionBattleEnv>(env.clone());
        })
        .def("is_terminal", &game::CompositionBattleEnv::isTerminal)
        .def("current_nation", &game::CompositionBattleEnv::currentNation)
        .def("current_phase", &game::CompositionBattleEnv::currentPhase)
        .def("legal_actions", &game::CompositionBattleEnv::legalActions)
        .def("encode_state", &game::CompositionBattleEnv::encodeState)
        .def("encode_legal_actions", &game::CompositionBattleEnv::encodeLegalActions)
        .def("state_feature_labels", &game::CompositionBattleEnv::stateFeatureLabels)
        .def("action_feature_labels", &game::CompositionBattleEnv::actionFeatureLabels)
        .def("step", &game::CompositionBattleEnv::step)
        .def("final_reward", &game::CompositionBattleEnv::finalReward)
        .def("terminal_reward_for", &game::CompositionBattleEnv::terminalRewardFor)
        .def("winner_id", &game::CompositionBattleEnv::winnerId)
        .def("budget_remaining", &game::CompositionBattleEnv::budgetRemaining)
        .def("purchased_unit_count", &game::CompositionBattleEnv::purchasedUnitCount);
}
