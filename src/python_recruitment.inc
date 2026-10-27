// Read-only metadata/oracle boundary. Rule formulae remain in politics_influence.
struct RecruitmentNativeAccess {
    using Context=game::campaign::RecruitmentContext;
    static std::shared_ptr<Context> context(const NativeCampaignEnv& env) {
        return env.call([](const auto& value){return std::make_shared<Context>(value.engine());});
    }
    static py::list oracle(std::shared_ptr<Context> context,const std::vector<NativeCampaignEnv*>& envs,
                           const std::vector<std::pair<std::int64_t,std::string>>& queries) {
        if(!context)throw std::invalid_argument("Missing recruitment oracle context");
        const auto owners=pinNativeEnvironments(envs);
        std::vector<game::campaign::RecruitmentQueryOracle> values;
        {
            py::gil_scoped_release release;
            for(const auto& [lane,minor]:queries) {
                if(lane<0||static_cast<std::size_t>(lane)>=envs.size())throw std::out_of_range("Recruitment query lane");
                std::lock_guard lock(envs[lane]->mutex_);const auto& state=envs[lane]->env_.engine().state();
                if(!state.definition||state.definition->fingerprint!=context->definition->fingerprint)
                    throw std::invalid_argument("Recruitment oracle definition differs");
                values.push_back(game::campaign::recruitmentQueryOracle(state,minor));
            }
        }
        py::list output;
        for(const auto& value:values) {
            py::dict item;item["available"]=value.available;item["threshold"]=value.threshold;
            item["quiet_placement"]=value.quietPlacement;item["zones"]=value.zones;
            item["errors"]=value.errors;item["messages"]=value.messages;
            std::vector<std::string> choices,rolls;
            for(const auto& action:value.choices)choices.push_back(game::campaign::canonicalJson(game::campaign::actionJson(action)));
            for(const auto& action:value.rolls)rolls.push_back(game::campaign::canonicalJson(game::campaign::actionJson(action)));
            item["choices"]=choices;item["rolls"]=rolls;output.append(item);
        }
        return output;
    }
    static py::list effects(std::shared_ptr<Context> context,const std::vector<NativeCampaignEnv*>& envs,
                            const std::vector<std::vector<std::vector<int>>>& faces) {
        if(!context||faces.size()!=envs.size())throw std::invalid_argument("Recruitment effect oracle context/outcome batch differs");
        const auto owners=pinNativeEnvironments(envs);
        std::vector<std::string> states,messages;std::vector<int> errors;std::vector<bool> handled;
        {
            py::gil_scoped_release release;
            for(std::size_t lane=0;lane<envs.size();++lane) {
                std::lock_guard lock(envs[lane]->mutex_);const auto& original=envs[lane]->env_.engine().state();
                if(!original.definition||original.definition->fingerprint!=context->definition->fingerprint)
                    throw std::invalid_argument("Recruitment effect oracle definition differs");
                auto next=original.clone();int error=0;std::string message;
                const bool applies=next.chance&&next.chance->purpose=="recruitment_roll";
                if(applies)try {
                    const auto request=*next.chance;
                    // Exact Engine pre-hook, then the unchanged original rule.
                    next.chance.reset();
                    (void)game::campaign::applyInfluenceChance(next,request,game::campaign::ChanceOutcome{faces[lane]});
                }catch(const std::out_of_range& e){error=1;message=e.what();}
                 catch(const std::exception& e){error=2;message=e.what();}
                states.push_back((error?original:next).serialize());errors.push_back(error);
                messages.push_back(message);handled.push_back(applies);
            }
        }
        py::list output;
        for(std::size_t lane=0;lane<envs.size();++lane){py::dict item;
            item["state_json"]=states[lane];item["error"]=errors[lane];item["message"]=messages[lane];
            item["handled"]=static_cast<bool>(handled[lane]);output.append(item);}
        return output;
    }
};
void bindRecruitment(py::module_& module) {
    using C=RecruitmentNativeAccess::Context;
    py::class_<C,std::shared_ptr<C>>(module,"CampaignRecruitmentContext")
        .def_property_readonly("definition_fingerprint",[](const C& c){return c.definition->fingerprint;})
        .def_property_readonly("wire_context_fingerprint",[](const C& c){return c.wireContextFingerprint;})
        .def_property_readonly("territories",[](const C& c){return c.territories;})
        .def_property_readonly("naval_types",[](const C& c){return c.navalTypes;})
        .def_property_readonly("offshore_ids",[](const C& c){return c.offshoreIds;})
        .def_property_readonly("offshore_error",[](const C& c){return c.offshoreError;})
        .def_property_readonly("offshore_message",[](const C& c){return c.offshoreMessage;})
        .def_property_readonly("messages",[](const C& c){return c.messages;})
        .def_property_readonly("chinese_home_present",[](const C& c){return c.chineseHomePresent;})
        .def_property_readonly("catalog_present",[](const C& c){return c.catalogPresent;})
        .def("chinese_home_array",[](const C& c){return incomeArray(c,c.chineseHome,{static_cast<py::ssize_t>(c.chineseHome.size())});})
        .def("offshore_step_array",[](const C& c){return incomeArray(c,c.offshoreSteps,{static_cast<py::ssize_t>(c.offshoreSteps.size()/3),3});});
    module.def("campaign_recruitment_context",&RecruitmentNativeAccess::context);
    module.def("campaign_recruitment_oracle",&RecruitmentNativeAccess::oracle);
    module.def("campaign_recruitment_effects_oracle",&RecruitmentNativeAccess::effects);
}
