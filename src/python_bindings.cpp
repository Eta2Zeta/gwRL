#include "game/action.hpp"
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
    if (hasDetails) {
        description += ")";
    }
    return description;
}

}  // namespace

PYBIND11_MODULE(gwrl_cpp, module) {
    module.doc() = "C++ training environment bindings for gwRL";

    py::enum_<game::ActionKind>(module, "ActionKind")
        .value("DeclareWarOnChina", game::ActionKind::DeclareWarOnChina)
        .value("MoveCombatUnit", game::ActionKind::MoveCombatUnit)
        .value("EndPhase", game::ActionKind::EndPhase);

    py::class_<game::Action>(module, "Action")
        .def(py::init<>())
        .def_readwrite("kind", &game::Action::kind)
        .def_readwrite("source_zone_id", &game::Action::sourceZoneId)
        .def_readwrite("target_zone_id", &game::Action::targetZoneId)
        .def_readwrite("unit_count", &game::Action::unitCount)
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
        .def("unit_count_for", &game::JapanTrainingEnv::unitCountFor);
}
