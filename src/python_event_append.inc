// Diagnostic oracle: append exactly one ordinary native audit Event per lane.
// Input JSON parsing belongs only to this test/export boundary.
void bindEventAppendProbe(py::module_& module) {
    module.def("campaign_event_append_probe",[](const std::vector<NativeCampaignEnv*>& envs,
        const std::vector<std::string>& kinds,const std::vector<std::string>& payloads) {
        if(envs.size()!=kinds.size()||envs.size()!=payloads.size())throw py::value_error("Event oracle lengths differ");
        const auto owners=pinNativeEnvironments(envs);std::vector<game::json::Value> values;
        for(const auto& text:payloads)values.push_back(game::json::parse(text));
        std::vector<std::string> states;
        for(std::size_t lane=0;lane<envs.size();++lane) {
            if(kinds[lane]!="action"&&kinds[lane]!="interrupt"&&kinds[lane]!="chance")
                throw py::value_error("Unknown engine event kind");
            states.push_back(envs[lane]->call([&](const auto& env) {
                auto state=env.engine().state().clone();const auto key=state.planningKey();
                state.history.push_back(game::campaign::Event{kinds[lane],values[lane],key});
                return state.serialize();
            }));
        }
        return states;
    });
}
