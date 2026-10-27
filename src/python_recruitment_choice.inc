// Diagnostic original public dispatch only; no copied recruitment formulas.
struct RecruitmentChoiceNativeAccess {
    using Context=game::campaign::DeviceStateContext;
    static py::list oracle(std::shared_ptr<Context> context,const std::vector<NativeCampaignEnv*>& envs,
            const std::vector<std::int64_t>& selections,const std::vector<bool>& selected){
        if(!context||selections.size()!=envs.size()||selected.size()!=envs.size())
            throw std::invalid_argument("Recruitment-choice oracle source/lane batch differs");
        const auto pinned=pinNativeEnvironments(envs);std::vector<game::campaign::DeviceStateBatch> packed;
        std::vector<int> errors;std::vector<bool> handled;std::vector<std::string> messages;
        {
            py::gil_scoped_release release;
            for(std::size_t lane=0;lane<envs.size();++lane){
                std::lock_guard lock(envs[lane]->mutex_);const auto& engine=envs[lane]->env_.engine();const auto& original=engine.state();
                if(!original.definition||original.definition->fingerprint!=context->definitionFingerprint)
                    throw std::invalid_argument("Recruitment-choice oracle definition differs");
                auto next=original.clone();int error=0;std::string message;bool applies=false;
                if(selected[lane])try{
                    if(next.decisions.empty()||selections[lane]<0||static_cast<std::uint64_t>(selections[lane])>=next.decisions.back().options.size())
                        throw std::runtime_error("No selected stored recruitment option");
                    const auto action=next.decisions.back().options.at(static_cast<std::size_t>(selections[lane]));
                    applies=game::campaign::applyInfluenceAction(next,action);
                }catch(const std::out_of_range& e){error=1;message=e.what();}
                 catch(const std::exception& e){error=2;message=e.what();}
                packed.emplace_back(context);packed.back().appendDiagnosticState(error?original:next,engine);
                errors.push_back(error);messages.push_back(message);handled.push_back(applies);
            }
        }
        py::list output;for(std::size_t lane=0;lane<envs.size();++lane){py::dict item;
            item["packed_state"]=py::cast(std::move(packed[lane]));item["error"]=errors[lane];item["message"]=messages[lane];
            if(errors[lane])item["handled"]=py::none();else item["handled"]=static_cast<bool>(handled[lane]);
            output.append(item);}return output;
    }
};
void bindRecruitmentChoice(py::module_& module){
    module.def("campaign_apply_recruitment_choice_oracle",&RecruitmentChoiceNativeAccess::oracle,
        py::arg("context"),py::arg("environments"),py::arg("selections"),py::arg("selected"));
}
