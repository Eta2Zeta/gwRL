// Exact tiny original refresh blocks, with typed State/RNG diagnostic gold.
struct PoliticalFactsNativeAccess {
    using Context=game::campaign::PoliticalFactsContext;
    using Wire=game::campaign::DeviceStateContext;
    static std::shared_ptr<Context> context(const NativeCampaignEnv& env){
        return env.call([](const game::campaign::CampaignEnv& value){return std::make_shared<Context>(value.engine());});
    }
    static py::list oracle(std::shared_ptr<Wire> context,const std::vector<NativeCampaignEnv*>& envs,
            const std::vector<std::string>& owners,const std::vector<bool>& selected,int mode){
        if(!context||selected.size()!=envs.size()||((mode==1||mode==2)&&owners.size()!=envs.size())||mode<0||mode>5)
            throw std::invalid_argument("Political facts oracle source/lane/mode differs");
        const auto pinned=pinNativeEnvironments(envs);std::vector<std::string> messages;std::vector<int> errors;
        std::vector<bool> promoted;std::vector<game::campaign::DeviceStateBatch> packed;
        {
            py::gil_scoped_release release;
            for(std::size_t lane=0;lane<envs.size();++lane){
                std::lock_guard lock(envs[lane]->mutex_);const auto& engine=envs[lane]->env_.engine();const auto& original=engine.state();
                if(!original.definition||original.definition->fingerprint!=context->definitionFingerprint)
                    throw std::invalid_argument("Political facts oracle definition differs");
                auto next=original.clone();int error=0;std::string message;bool mark=false;
                if(selected[lane])try{
                    switch(mode){
                        case 0:game::campaign::refreshPoliticalPossessionFlags(next);break;
                        case 1:game::campaign::refreshPoliticalCivilWarFlag(next,owners[lane]);break;
                        case 2:mark=game::campaign::markPoliticalEvolutionIfDue(next,owners[lane]);break;
                        case 3:game::campaign::refreshPoliticalOneChinaObjective(next);break;
                        case 4:game::campaign::refreshPoliticalAllies(next);break;
                        case 5:game::campaign::refreshPoliticalState(next);break;
                    }
                }catch(const std::out_of_range& e){error=1;message=e.what();}
                 catch(const std::exception& e){error=2;message=e.what();}
                packed.emplace_back(context);packed.back().appendDiagnosticState(error?original:next,engine);
                errors.push_back(error);messages.push_back(message);promoted.push_back(!error&&mark);
            }
        }
        py::list output;for(std::size_t lane=0;lane<envs.size();++lane){py::dict item;
            item["packed_state"]=py::cast(std::move(packed[lane]));item["error"]=errors[lane];item["message"]=messages[lane];
            item["promoted"]=static_cast<bool>(promoted[lane]);output.append(item);}return output;
    }
    static std::unique_ptr<NativeCampaignEnv> ippFixture(const NativeCampaignEnv& env,const std::string& zone,
            const std::string& ippDocument,bool erase){
        const auto ipp=game::json::parse(ippDocument);
        return env.call([&](const game::campaign::CampaignEnv& value){
            const auto& engine=value.engine();auto state=engine.state().clone();auto definition=*state.definition;
            auto geography=definition.geography.asObject();auto nodes=geography.at("nodes").asObject();auto node=nodes.at(zone).asObject();
            if(erase)node.erase("ipp_value");else node["ipp_value"]=ipp;
            nodes[zone]=game::json::Value(std::move(node));geography["nodes"]=game::json::Value(std::move(nodes));
            definition.geography=game::json::Value(std::move(geography));state.definition=game::campaign::freezeDefinition(std::move(definition));
            auto fixture=game::campaign::restoreDiagnosticState(std::move(state),engine);
            return std::make_unique<NativeCampaignEnv>(game::campaign::CampaignEnv(std::move(fixture)));
        });
    }
    static std::unique_ptr<NativeCampaignEnv> absentFixture(const NativeCampaignEnv& env,const std::string& nation){
        return env.call([&](const game::campaign::CampaignEnv& value){
            const auto& engine=value.engine();auto state=engine.state().clone();auto definition=*state.definition;
            definition.factions.at(nation).dormant=true;
            std::set<game::campaign::Id> removed;
            for(const auto& [id,unit]:state.units)if(unit.owner==nation)removed.insert(id);
            game::campaign::removePoliticalUnits(state,removed);
            for(auto& [id,territory]:state.territories)if(territory.possessor==nation)territory.possessor.reset();
            for(auto it=state.construction.begin();it!=state.construction.end();)
                if(it->second.owner==nation)it=state.construction.erase(it);else ++it;
            for(auto it=state.repairs.begin();it!=state.repairs.end();){const auto& job=it->second;
                const bool target=state.units.contains(job.target)||state.facilities.contains(job.target)||state.rails.contains(job.target)
                    ||state.territories.contains(job.target)||state.construction.contains(job.target);
                if(job.owner==nation||!target)it=state.repairs.erase(it);else ++it;
            }
            state.nations.erase(nation);
            for(auto& [id,other]:state.nations){
                if(other.controllerNation==nation)other.controllerNation.reset();
                other.atWarWith.erase(nation);other.allies.erase(nation);
            }
            for(auto& [zone,owner]:state.turnStart.possessions)if(owner==nation)owner.reset();
            for(auto it=state.turnStart.units.begin();it!=state.turnStart.units.end();)
                if(it->second.first==nation)it=state.turnStart.units.erase(it);else ++it;
            auto& politics=state.politics;
            politics.capitals.erase(nation);politics.surrendered.erase(nation);politics.evolutionAwarded.erase(nation);
            politics.attackedWarlords.erase(nation);for(auto& [id,actors]:politics.attackedWarlords)actors.erase(nation);
            std::erase(politics.alignmentQueue,nation);if(politics.chinaInvader==nation)politics.chinaInvader.reset();
            for(auto it=state.battles.begin();it!=state.battles.end();)
                if(it->second.attacker==nation||it->second.defender==nation)it=state.battles.erase(it);else ++it;
            std::erase_if(state.battleOrder,[&](const auto& id){return !state.battles.contains(id);});
            if(state.chance&&state.chance->nation==nation)state.chance.reset();
            std::erase_if(state.decisions,[&](const auto& decision){
                if(decision.nation==nation)return true;
                try{const auto player=game::campaign::politicalPlayer(state,decision.nation);
                    return std::any_of(decision.options.begin(),decision.options.end(),[&](const auto& action){return action.player!=player;});
                }catch(const std::exception&){return true;}
            });
            state.definition=game::campaign::freezeDefinition(std::move(definition));
            auto fixture=game::campaign::restoreDiagnosticState(std::move(state),engine);
            return std::make_unique<NativeCampaignEnv>(game::campaign::CampaignEnv(std::move(fixture)));
        });
    }
};
void bindPoliticalFacts(py::module_& module){
    using A=PoliticalFactsNativeAccess;using C=A::Context;
    py::class_<C,std::shared_ptr<C>>(module,"CampaignPoliticalFactsContext")
        .def_property_readonly("definition_fingerprint",[](const C& c){return c.definition->fingerprint;})
        .def_property_readonly("wire_context_fingerprint",[](const C& c){return c.wireContextFingerprint;})
        .def_property_readonly("territories",[](const C& c){return c.territories;})
        .def_property_readonly("nations",[](const C& c){return c.nations;})
        .def_property_readonly("messages",[](const C& c){return c.messages;})
        .def_property_readonly("home_error",[](const C& c){return c.homeError;})
        .def_property_readonly("home_message",[](const C& c){return c.homeMessage;})
        .def("ipp_array",[](const C& c){return incomeArray(c,c.ipp,{static_cast<py::ssize_t>(c.territories.size()),3});})
        .def("home_array",[](const C& c){return incomeArray(c,c.chineseHome,{static_cast<py::ssize_t>(c.territories.size())});});
    module.def("campaign_political_facts_context",&A::context);
    module.def("campaign_political_facts_oracle",&A::oracle,py::arg("context"),py::arg("environments"),py::arg("owners"),py::arg("selected"),py::arg("mode"));
    module.def("_campaign_political_facts_ipp_test_fixture",&A::ippFixture,
        py::arg("environment"),py::arg("zone"),py::arg("ipp_json"),py::arg("erase")=false);
    module.def("_campaign_political_facts_absent_test_fixture",&A::absentFixture,py::arg("environment"),py::arg("nation"));
}
