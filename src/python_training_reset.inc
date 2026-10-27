// Exact diagnostic reset; actual dispatch belongs to TrainingRules.
void bindTrainingResetProbe(py::module_& module) {
    module.def("campaign_training_reset_probe",[](const std::vector<NativeCampaignEnv*>& envs) {
        const auto owners=pinNativeEnvironments(envs);std::vector<std::string> result;
        for(auto* env:envs)result.push_back(env->call([](const auto& value) {
            auto state=value.engine().state().clone();game::campaign::resetTrainingActionState(state);
            return state.serialize();
        }));
        return result;
    });
}
