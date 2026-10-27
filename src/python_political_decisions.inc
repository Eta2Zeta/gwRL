// Explicit original-helper probes; production decision building stays resident.
struct PoliticalDecisionsNativeAccess {
    using Context=game::campaign::DeviceStateContext;
    using Batch=game::campaign::DeviceStateBatch;
    struct Row {std::unique_ptr<Batch> packed;int error;std::string message;};
    static std::unique_ptr<NativeCampaignEnv> actorFixture(const NativeCampaignEnv& env) {
        return env.call([](const game::campaign::CampaignEnv& value){
            const auto& original=value.engine();auto definition=*original.state().definition;
            game::campaign::FactionDefinition faction;faction.id="queue_actor_1";faction.displayName="Queue actor diagnostic";
            faction.homeCountryKnown=true;faction.dormant=true;definition.factions.emplace(faction.id,faction);
            auto state=original.state().clone();state.definition=game::campaign::freezeDefinition(std::move(definition));
            state.nations.emplace(faction.id,game::campaign::NationState{});
            state.politics.pending["warlord_defense_player:"+faction.id]=game::json::Value(std::string("axis"));
            // Diagnostic authoring creates a fresh validated definition while
            // retaining the original private random streams without JSON.
            auto fixture=game::campaign::restoreDiagnosticState(std::move(state),original);
            return std::make_unique<NativeCampaignEnv>(game::campaign::CampaignEnv(std::move(fixture)));
        });
    }
    static py::list oracle(std::shared_ptr<Context> context,const std::vector<NativeCampaignEnv*>& envs,
            const std::vector<std::string>& nations,const std::vector<std::string>& kinds,
            const std::vector<std::string>& options,const std::vector<std::string>& continuations,
            const std::vector<bool>& selected,bool evolution) {
        if(!context||nations.size()!=envs.size()||selected.size()!=envs.size()||
           (!evolution&&(kinds.size()!=envs.size()||options.size()!=envs.size()||continuations.size()!=envs.size())))
            throw std::invalid_argument("Political decision oracle context/lane batch differs");
        const auto pinned=pinNativeEnvironments(envs);py::list output;
        for(std::size_t lane=0;lane<envs.size();++lane){auto row=envs[lane]->call([&](const game::campaign::CampaignEnv& value){
            const auto& engine=value.engine();const auto& original=engine.state();auto next=original.clone();int error=0;std::string message;
            if(selected[lane])try {
                if(evolution)game::campaign::queuePoliticalEvolutionChoice(next,nations[lane]);
                else{std::vector<game::campaign::Action> choices;const auto document=game::json::parse(options[lane]);
                    for(const auto& action:document.asArray())choices.push_back(game::campaign::actionFromJson(action));
                    game::campaign::queuePoliticalDecision(next,nations[lane],kinds[lane],std::move(choices),game::json::parse(continuations[lane]));}
            }catch(const std::out_of_range& e){error=1;message=e.what();}
             catch(const std::exception& e){error=2;message=e.what();}
            auto packed=std::make_unique<Batch>(context);packed->appendDiagnosticState(error?original:next,engine);
            return Row{std::move(packed),error,std::move(message)};
        });py::dict item;item["packed_state"]=py::cast(std::move(row.packed));item["error"]=row.error;item["message"]=row.message;output.append(item);}
        return output;
    }
};
void bindPoliticalDecisions(py::module_& module) {
    using A=PoliticalDecisionsNativeAccess;
    module.def("_campaign_political_decision_actor_test_fixture",&A::actorFixture);
    module.def("campaign_queue_political_decision_oracle",[](std::shared_ptr<A::Context> context,
            const std::vector<NativeCampaignEnv*>& envs,const std::vector<std::string>& nations,const std::vector<std::string>& kinds,
            const std::vector<std::string>& options,const std::vector<std::string>& continuations,const std::vector<bool>& selected){
        return A::oracle(std::move(context),envs,nations,kinds,options,continuations,selected,false);});
    module.def("campaign_queue_political_evolution_oracle",[](std::shared_ptr<A::Context> context,
            const std::vector<NativeCampaignEnv*>& envs,const std::vector<std::string>& nations,const std::vector<bool>& selected){
        return A::oracle(std::move(context),envs,nations,{},{},{},selected,true);});
}
