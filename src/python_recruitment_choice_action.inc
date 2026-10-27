// Diagnostic complete Engine action; rule formulas and hooks are not copied.
struct RecruitmentChoiceActionNativeAccess {
    using Context=game::campaign::DeviceStateContext;
    using Batch=game::campaign::DeviceStateBatch;
    struct Row {std::unique_ptr<Batch> packed;int error;std::string message,stateKey,engineKey;};
    static py::list oracle(std::shared_ptr<Context> context,const std::vector<NativeCampaignEnv*>& envs,
            const std::vector<std::int64_t>& selections,const std::vector<bool>& selected){
        if(!context||selections.size()!=envs.size()||selected.size()!=envs.size())
            throw std::invalid_argument("Recruitment-choice Engine oracle source/lane batch differs");
        const auto pinned=pinNativeEnvironments(envs);py::list output;
        for(std::size_t lane=0;lane<envs.size();++lane){
            auto row=envs[lane]->call([&](const game::campaign::CampaignEnv& value){
                const auto& original=value.engine();auto next=original.clone();int error=0;std::string message;
                if(selected[lane])try{
                    const auto& decisions=next.state().decisions;
                    if(decisions.empty()||selections[lane]<0||static_cast<std::uint64_t>(selections[lane])>=decisions.back().options.size())
                        throw std::runtime_error("No selected stored recruitment option");
                    const auto action=decisions.back().options.at(static_cast<std::size_t>(selections[lane]));
                    next.step(action);
                }catch(const std::out_of_range& e){error=1;message=e.what();}
                 catch(const std::exception& e){error=2;message=e.what();}
                const auto& result=error?original:next;auto packed=std::make_unique<Batch>(context);packed->append(result);
                return Row{std::move(packed),error,std::move(message),result.state().planningKey(),result.planningKey()};
            });
            py::dict item;item["packed_state"]=py::cast(std::move(row.packed));item["error"]=row.error;item["message"]=row.message;
            item["state_key"]=row.stateKey;item["engine_key"]=row.engineKey;output.append(item);
        }
        return output;
    }
};
void bindRecruitmentChoiceAction(py::module_& module){
    module.def("campaign_apply_recruitment_choice_action_oracle",&RecruitmentChoiceActionNativeAccess::oracle,
        py::arg("context"),py::arg("environments"),py::arg("selections"),py::arg("selected"));
}
