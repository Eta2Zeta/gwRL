// Diagnostic only: exact original helpers and a lossless typed State/RNG gold.
struct SurrenderNativeAccess {
    using Context=game::campaign::DeviceStateContext;
    static py::list oracle(std::shared_ptr<Context> context,const std::vector<NativeCampaignEnv*>& envs,
                           const std::vector<std::string>& nations,const std::vector<std::string>& attackers,
                           const std::vector<bool>& selected,bool bonusOnly) {
        if(!context||selected.size()!=envs.size()||(!bonusOnly&&(nations.size()!=envs.size()||attackers.size()!=envs.size())))
            throw std::invalid_argument("Surrender oracle context/lane batch differs");
        const auto pinned=pinNativeEnvironments(envs);
        std::vector<std::string> states,planning,messages;std::vector<int> errors;
        std::vector<game::campaign::DeviceStateBatch> packed;
        {
            py::gil_scoped_release release;
            for(std::size_t lane=0;lane<envs.size();++lane) {
                std::lock_guard lock(envs[lane]->mutex_);const auto& original=envs[lane]->env_.engine().state();
                if(!original.definition||original.definition->fingerprint!=context->definition->fingerprint)
                    throw std::invalid_argument("Surrender oracle source differs");
                auto next=original.clone();int error=0;std::string message;
                if(selected[lane])try {
                    if(bonusOnly)game::campaign::queuePoliticalObjectiveBonus(next);
                    else game::campaign::surrenderNation(next,nations[lane],attackers[lane]);
                }catch(const std::out_of_range& e){error=1;message=e.what();}
                catch(const std::exception& e){error=2;message=e.what();}
                const auto& result=error?original:next;
                states.push_back(game::campaign::canonicalJson(result.toJson()));
                planning.push_back(game::campaign::canonicalJson(result.toJson(false)));
                packed.emplace_back(context);packed.back().appendDiagnosticState(result,envs[lane]->env_.engine());
                errors.push_back(error);messages.push_back(message);
            }
        }
        py::list output;
        for(std::size_t lane=0;lane<envs.size();++lane){py::dict item;
            item["state_json"]=states[lane];item["planning_json"]=planning[lane];item["error"]=errors[lane];item["message"]=messages[lane];
            item["packed_state"]=py::cast(std::move(packed[lane]));output.append(item);}
        return output;
    }
};
void bindSurrender(py::module_& module) {
    using A=SurrenderNativeAccess;
    module.def("campaign_surrender_nation_oracle",[](std::shared_ptr<A::Context> context,const std::vector<NativeCampaignEnv*>& envs,
        const std::vector<std::string>& nations,const std::vector<std::string>& attackers,const std::vector<bool>& selected) {
        return A::oracle(std::move(context),envs,nations,attackers,selected,false);
    });
    module.def("campaign_queue_political_objective_bonus_oracle",[](std::shared_ptr<A::Context> context,
        const std::vector<NativeCampaignEnv*>& envs,const std::vector<bool>& selected) {
        return A::oracle(std::move(context),envs,{}, {},selected,true);
    });
}
