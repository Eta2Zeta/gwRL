// Exact public rule helper, with raw typed State/RNG diagnostic gold.
struct ChineseTruceNativeAccess {
    using Context=game::campaign::DeviceStateContext;
    static std::unique_ptr<NativeCampaignEnv> borderFixture(const NativeCampaignEnv& env,const std::string& from,
            const std::string& to,const std::string& borderDocument) {
        const auto border=game::json::parse(borderDocument);
        return env.call([&](const game::campaign::CampaignEnv& value){
            const auto& source=value.engine();auto state=source.state().clone();auto definition=*state.definition;
            auto geography=definition.geography.asObject();auto nodes=geography.at("nodes").asObject();
            auto node=nodes.at(from).asObject();auto neighbors=node.at("neighbors").asArray();bool found=false;
            for(auto& item:neighbors)if(item.require("neighbor_id").asString()==to){
                auto edge=item.asObject();edge["border_terrain"]=border;item=game::json::Value(std::move(edge));found=true;break;
            }
            if(!found)throw std::invalid_argument("Diagnostic truce border must name an existing directed edge");
            node["neighbors"]=game::json::Value(std::move(neighbors));nodes[from]=game::json::Value(std::move(node));
            geography["nodes"]=game::json::Value(std::move(nodes));definition.geography=game::json::Value(std::move(geography));
            state.definition=game::campaign::freezeDefinition(std::move(definition));
            auto fixture=game::campaign::restoreDiagnosticState(std::move(state),source);
            return std::make_unique<NativeCampaignEnv>(game::campaign::CampaignEnv(std::move(fixture)));
        });
    }
    static py::list oracle(std::shared_ptr<Context> context,const std::vector<NativeCampaignEnv*>& envs,
                          const std::vector<std::string>& breakers,const std::vector<bool>& evolution,
                          const std::vector<bool>& selected) {
        if(!context||breakers.size()!=envs.size()||evolution.size()!=envs.size()||selected.size()!=envs.size())
            throw std::invalid_argument("Chinese Truce oracle context/lane batch differs");
        const auto pinned=pinNativeEnvironments(envs);
        std::vector<std::string> states,messages;std::vector<int> errors;
        std::vector<game::campaign::DeviceStateBatch> packed;
        {
            py::gil_scoped_release release;
            for(std::size_t lane=0;lane<envs.size();++lane) {
                std::lock_guard lock(envs[lane]->mutex_);const auto& original=envs[lane]->env_.engine().state();
                if(!original.definition||original.definition->fingerprint!=context->definition->fingerprint)
                    throw std::invalid_argument("Chinese Truce oracle source differs");
                auto next=original.clone();int error=0;std::string message;
                if(selected[lane])try {game::campaign::terminateChineseTruce(next,breakers[lane],evolution[lane]);}
                catch(const std::out_of_range& e){error=1;message=e.what();}
                catch(const std::exception& e){error=2;message=e.what();}
                const auto& result=error?original:next;
                states.push_back(game::campaign::canonicalJson(result.toJson()));
                packed.emplace_back(context);packed.back().appendDiagnosticState(result,envs[lane]->env_.engine());
                errors.push_back(error);messages.push_back(message);
            }
        }
        py::list output;
        for(std::size_t lane=0;lane<envs.size();++lane){py::dict item;
            item["state_json"]=states[lane];item["packed_state"]=py::cast(std::move(packed[lane]));
            item["error"]=errors[lane];item["message"]=messages[lane];output.append(item);}
        return output;
    }
};
void bindChineseTruce(py::module_& module) {
    module.def("_campaign_chinese_truce_border_test_fixture",&ChineseTruceNativeAccess::borderFixture,
        py::arg("environment"),py::arg("from_zone"),py::arg("to_zone"),py::arg("border_terrain_json"));
    module.def("campaign_terminate_chinese_truce_oracle",&ChineseTruceNativeAccess::oracle,
        py::arg("context"),py::arg("environments"),py::arg("breakers"),py::arg("evolution"),py::arg("selected"));
}
