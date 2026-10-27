// Explicit oracle boundary. Production removal works entirely on resident data.
struct PoliticalUnitRemovalNativeAccess {
    using Context=game::campaign::DeviceStateContext;
    using LinkOverrides=std::map<std::string,std::pair<std::optional<std::string>,std::vector<std::string>>>;
    static py::list remove(std::shared_ptr<Context> context,const std::vector<NativeCampaignEnv*>& envs,
                           const std::vector<std::vector<std::string>>& ids,const std::vector<bool>& selected,
                           const std::vector<LinkOverrides>& testLinks={}) {
        if(!context||ids.size()!=envs.size()||selected.size()!=envs.size()||(!testLinks.empty()&&testLinks.size()!=envs.size()))
            throw std::invalid_argument("Political unit removal oracle context/lane batch differs");
        const auto pinned=pinNativeEnvironments(envs);
        std::vector<std::string> states,planning,messages;std::vector<int> errors;
        std::vector<game::campaign::DeviceStateBatch> packed;
        {
            py::gil_scoped_release release;
            for(std::size_t lane=0;lane<envs.size();++lane) {
                std::lock_guard lock(envs[lane]->mutex_);const auto& original=envs[lane]->env_.engine().state();
                if(!original.definition||original.definition->fingerprint!=context->definition->fingerprint)
                    throw std::invalid_argument("Political unit removal oracle source differs");
                auto source=original.clone();
                // Diagnostic entry only: the helper itself has well-defined
                // closure semantics for cyclic links that Engine ingress bans.
                if(!testLinks.empty())for(const auto& [id,links]:testLinks[lane]) {
                    auto& unit=source.units.at(id);unit.carriedBy=links.first;unit.cargo=links.second;
                }
                auto next=source.clone();int error=0;std::string message;
                if(selected[lane])try {
                    game::campaign::removePoliticalUnits(next,std::set<std::string>(ids[lane].begin(),ids[lane].end()));
                }catch(const std::out_of_range& e){error=1;message=e.what();}
                catch(const std::exception& e){error=2;message=e.what();}
                const auto& result=error?source:next;
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
void bindPoliticalUnitRemoval(py::module_& module) {
    using A=PoliticalUnitRemovalNativeAccess;
    module.def("campaign_remove_political_units_oracle",[](std::shared_ptr<A::Context> context,
        const std::vector<NativeCampaignEnv*>& envs,const std::vector<std::vector<std::string>>& ids,const std::vector<bool>& selected) {
        return A::remove(std::move(context),envs,ids,selected);
    });
    module.def("_campaign_remove_political_units_test_oracle",&A::remove);
}
