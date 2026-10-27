// Explicit diagnostic boundary: invoke the original movement-refresh helper on
// a clone. The production resident handler uses typed buffers and Catalog stats.
struct PoliticalUnitsNativeAccess {
    using Context=game::campaign::DeviceStateContext;
    using MovementOverride=std::map<std::string,std::pair<std::optional<int>,std::optional<int>>>;
    static py::list movement(std::shared_ptr<Context> context,const std::vector<NativeCampaignEnv*>& envs,
                             const std::vector<std::string>& owners,const std::vector<bool>& selected,
                             const std::vector<MovementOverride>& testMovement={}) {
        if(!context||owners.size()!=envs.size()||selected.size()!=envs.size()||
           (!testMovement.empty()&&testMovement.size()!=envs.size()))
            throw std::invalid_argument("Political unit movement oracle context/lane batch differs");
        const auto pinned=pinNativeEnvironments(envs);
        std::vector<std::string> states,planning,messages;std::vector<int> errors;
        {
            py::gil_scoped_release release;
            for(std::size_t lane=0;lane<envs.size();++lane) {
                std::lock_guard lock(envs[lane]->mutex_);const auto& original=envs[lane]->env_.engine().state();
                if(!original.definition||original.definition->fingerprint!=context->definition->fingerprint)
                    throw std::invalid_argument("Political unit movement oracle source differs");
                auto source=original.clone();
                // Deliberately named test entry only: exercise the private
                // helper's optional inputs, which validated catalog State
                // ingress otherwise correctly requires to be resolved.
                if(!testMovement.empty())for(const auto& [id,values]:testMovement[lane]) {
                    auto& unit=source.units.at(id);unit.movementAllowance=values.first;unit.movementRemaining=values.second;
                }
                auto next=source.clone();int error=0;std::string message;
                if(selected[lane])try {game::campaign::refreshPoliticalUnitMovement(next,owners[lane]);}
                catch(const std::out_of_range& e){error=1;message=e.what();}
                catch(const std::exception& e){error=2;message=e.what();}
                const auto& result=error?source:next;
                // The original helper can intentionally clear an allowance.
                // Inspect that value before the separate Engine validation.
                states.push_back(game::campaign::canonicalJson(result.toJson()));
                planning.push_back(game::campaign::canonicalJson(result.toJson(false)));
                errors.push_back(error);messages.push_back(message);
            }
        }
        py::list output;
        for(std::size_t lane=0;lane<envs.size();++lane){py::dict item;
            item["state_json"]=states[lane];item["planning_json"]=planning[lane];item["error"]=errors[lane];item["message"]=messages[lane];output.append(item);}
        return output;
    }
};
void bindPoliticalUnits(py::module_& module) {
    using A=PoliticalUnitsNativeAccess;
    module.def("campaign_refresh_political_unit_movement_oracle",[](std::shared_ptr<A::Context> context,
        const std::vector<NativeCampaignEnv*>& envs,const std::vector<std::string>& owners,const std::vector<bool>& selected) {
        return A::movement(std::move(context),envs,owners,selected);
    });
    module.def("_campaign_political_unit_movement_test_oracle",&A::movement);
}
