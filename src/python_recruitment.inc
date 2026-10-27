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
    static py::list start(std::shared_ptr<Context> context,const std::vector<NativeCampaignEnv*>& envs,
                          const std::vector<std::string>& actions) {
        if(!context||actions.size()!=envs.size())throw std::invalid_argument("Recruitment start oracle context/action batch differs");
        const auto owners=pinNativeEnvironments(envs);
        std::vector<std::string> states,messages;std::vector<int> errors;std::vector<bool> handled;
        {
            py::gil_scoped_release release;
            for(std::size_t lane=0;lane<envs.size();++lane) {
                std::lock_guard lock(envs[lane]->mutex_);const auto& original=envs[lane]->env_.engine().state();
                if(!original.definition||original.definition->fingerprint!=context->definition->fingerprint)
                    throw std::invalid_argument("Recruitment start oracle definition differs");
                auto next=original.clone();int error=0;std::string message;bool applies=false;
                try {
                    const auto action=game::campaign::actionFromJson(game::json::parse(actions[lane]));
                    applies=action.kind=="recruitment_roll";
                    if(applies)(void)game::campaign::applyInfluenceAction(next,action);
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
    static py::dict chanceBenchmark(std::shared_ptr<game::campaign::DeviceStateContext> context,
            const std::vector<NativeCampaignEnv*>& envs,const std::vector<std::string>& expectedKeys,
            std::size_t trials,std::shared_ptr<NativeDiagnosticPool> pool,bool profile) {
        using namespace game::campaign;
        if(!context||envs.empty()||envs.size()!=expectedKeys.size()||!trials||trials>1000000)
            throw std::invalid_argument("Recruitment chance benchmark requires matching nonempty lanes/keys and positive bounded trials");
        for(const auto& key:expectedKeys)
            if(key.size()!=64||!std::all_of(key.begin(),key.end(),[](unsigned char c){return(c>='0'&&c<='9')||(c>='a'&&c<='f');}))
                throw std::invalid_argument("Recruitment benchmark requires exact Engine SHA256 keys");
        const auto owners=pinNativeEnvironments(envs);
        std::vector<double> elapsed,cloneSeconds,verificationSeconds,guardSeconds,resolveSeconds,keySeconds;
        std::vector<std::string> outputKeys(envs.size());
        auto original=std::make_unique<DeviceStateBatch>(context);
        auto output=std::make_unique<DeviceStateBatch>(context);
        bool unchanged=true,repeatExact=true;
        {
            py::gil_scoped_release release;
            std::vector<Engine> sources;sources.reserve(envs.size());
            for(auto* env:envs){std::lock_guard lock(env->mutex_);
                const auto& engine=env->env_.engine();
                if(engine.rulesId()!=context->rulesId||engine.state().definition->fingerprint!=context->definitionFingerprint)
                    throw std::invalid_argument("Recruitment benchmark source/context differs");
                if(!engine.state().chance||engine.state().chance->purpose!="recruitment_roll")
                    throw std::invalid_argument("Benchmark accepts pending recruitment chance only");
                sources.push_back(engine.clone());original->append(engine);
            }
            // Real committed sources already cache State::planningKey. Prime it
            // explicitly here; never manufacture a cold CPU baseline for MPS.
            for(const auto& source:sources)(void)source.planningKey();
            const auto equal=[](const DeviceStateBatch& a,const DeviceStateBatch& b){
                return a.records==b.records&&a.laneOffsets==b.laneOffsets&&a.strings==b.strings&&
                       a.stringBytes==b.stringBytes&&a.stringOffsets==b.stringOffsets&&a.sections==b.sections;
            };
            for(std::size_t trial=0;trial<trials;++trial){
                const auto copyStarted=std::chrono::steady_clock::now();
                std::vector<Engine> work;work.reserve(sources.size());
                for(const auto& source:sources)work.push_back(source.clone());
                cloneSeconds.push_back(std::chrono::duration<double>(std::chrono::steady_clock::now()-copyStarted).count());
                std::vector<double> guard(envs.size()),resolve(envs.size()),key(envs.size());
                const auto execute=[&](std::size_t worker,std::size_t workers){
                    for(std::size_t lane=worker;lane<work.size();lane+=workers){
                        if(profile){
                            const auto a=std::chrono::steady_clock::now();
                            if(work[lane].planningKey()!=expectedKeys[lane])throw std::runtime_error("Stale recruitment benchmark Engine key");
                            const auto b=std::chrono::steady_clock::now();work[lane].resolveChance();
                            const auto c=std::chrono::steady_clock::now();outputKeys[lane]=work[lane].planningKey();
                            const auto d=std::chrono::steady_clock::now();
                            guard[lane]=std::chrono::duration<double>(b-a).count();resolve[lane]=std::chrono::duration<double>(c-b).count();
                            key[lane]=std::chrono::duration<double>(d-c).count();
                        }else{
                            if(work[lane].planningKey()!=expectedKeys[lane])throw std::runtime_error("Stale recruitment benchmark Engine key");
                            work[lane].resolveChance();outputKeys[lane]=work[lane].planningKey();
                        }
                    }
                };
                const auto started=std::chrono::steady_clock::now();
                if(pool)pool->run(execute);else execute(0,1);
                elapsed.push_back(std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count());
                if(profile){double a=0,b=0,c=0;for(std::size_t lane=0;lane<work.size();++lane){a+=guard[lane];b+=resolve[lane];c+=key[lane];}
                    guardSeconds.push_back(a);resolveSeconds.push_back(b);keySeconds.push_back(c);}
                // Lossless full State/history/RNG capture and Python boxing are
                // outside the timed region. Keep one output, never all trials.
                const auto checked=std::chrono::steady_clock::now();DeviceStateBatch current(context);
                for(const auto& engine:work)current.append(engine);
                if(trial&&!equal(*output,current))repeatExact=false;
                *output=std::move(current);
                verificationSeconds.push_back(std::chrono::duration<double>(std::chrono::steady_clock::now()-checked).count());
            }
            DeviceStateBatch after(context);
            for(auto* env:envs){std::lock_guard lock(env->mutex_);after.append(env->env_.engine());}
            unchanged=equal(*original,after);
        }
        py::dict result;result["schema"]="campaign-native-recruitment-chance-timing-v1";
        result["batch_size"]=envs.size();result["trials"]=trials;result["workers"]=pool?pool->workers():1;
        result["execution"]=pool?"persistent_native_pool":"serial_native";
        result["pool_startup_seconds"]=pool?pool->startupSeconds():0.;result["profiled"]=profile;
        result["seconds"]=elapsed;result["input_clone_seconds"]=cloneSeconds;result["verification_seconds"]=verificationSeconds;
        result["guard_worker_seconds"]=guardSeconds;result["resolve_worker_seconds"]=resolveSeconds;result["output_key_worker_seconds"]=keySeconds;
        result["source_unchanged"]=unchanged;result["repeated_outputs_exact"]=repeatExact;result["output_engine_keys"]=outputKeys;
        result["original"]=py::cast(std::move(original));result["output"]=py::cast(std::move(output));
        result["timed_scope"]="Warm cached Engine key guard, original Engine.resolveChance (including its internal clone/validation/history/RNG), output Engine key; native pool dispatch included";
        result["excluded_scope"]="Owner/wrapper locks, GIL, input trial clones, full-output capture/verification, Python boxing and pool startup";
        return result;
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
    module.def("campaign_recruitment_start_oracle",&RecruitmentNativeAccess::start);
    module.def("campaign_recruitment_chance_benchmark",&RecruitmentNativeAccess::chanceBenchmark,
        py::arg("context"),py::arg("envs"),py::arg("expected_engine_keys"),py::arg("trials"),
        py::arg("pool")=nullptr,py::arg("profile")=false);
}
