// Native State JSON/State key/outer Engine key, used only as an oracle.
struct StateJsonNativeAccess {
    struct Row {std::string json,stateKey,engineKey,rulesJson;};
    static std::vector<Row> oracle(const std::vector<NativeCampaignEnv*>& envs) {
        const auto owners=pinNativeEnvironments(envs);py::gil_scoped_release release;
        std::vector<Row> rows;rows.reserve(envs.size());
        for(auto* env:envs){if(!env)throw std::invalid_argument("Null State JSON oracle lane");
            std::lock_guard lock(env->mutex_);const auto& engine=env->env_.engine();const auto& state=engine.state();
            rows.push_back({game::campaign::canonicalJson(state.toJson(false)),state.planningKey(),engine.planningKey(),
                game::campaign::canonicalJson(game::json::Value(engine.rulesId()))});}
        return rows;
    }
};
void bindStateJson(py::module_& module) {
    module.def("campaign_state_json_oracle",[](const std::vector<NativeCampaignEnv*>& envs){
        const auto native=StateJsonNativeAccess::oracle(envs);py::list rows;
        for(const auto& row:native){py::dict out;out["json"]=py::bytes(row.json);out["state_key"]=row.stateKey;
            out["engine_key"]=row.engineKey;out["rules_json"]=py::bytes(row.rulesJson);rows.append(std::move(out));}return rows;
    });
}
