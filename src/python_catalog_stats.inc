// Included after the privileged state binding; immutable metadata, read-only oracle.
struct CatalogStatsNativeAccess {
    using Context=game::campaign::CatalogStatsContext;
    using Oracle=game::campaign::CatalogStatsOracle;
    static std::shared_ptr<Context> context(const NativeCampaignEnv& env) {
        return env.call([](const auto& value){return std::make_shared<Context>(value.engine());});
    }
    static Oracle oracle(std::shared_ptr<Context> context,const std::vector<NativeCampaignEnv*>& envs,
                         const std::vector<std::tuple<std::int64_t,std::string,int,std::string,std::optional<std::string>>>& queries,
                         const std::map<std::string,int>& testStages={}) {
        if(!context)throw std::invalid_argument("Missing catalog-stat oracle context");
        const auto owners=pinNativeEnvironments(envs);py::gil_scoped_release release;Oracle out;
        for(const auto& [lane,type,damage,owner,zone]:queries) {
            std::int64_t error=0;std::string message;std::vector<std::int64_t> values;
            try {
                if(lane<0||static_cast<std::size_t>(lane)>=envs.size())throw std::out_of_range("Catalog query lane");
                std::lock_guard lock(envs[lane]->mutex_);const auto& state=envs[lane]->env_.engine().state();
                if(!state.definition||state.definition->fingerprint!=context->definition->fingerprint||
                   !state.definition->catalog||state.definition->catalog->fingerprint()!=context->catalogFingerprint)
                    throw std::invalid_argument("Catalog stats oracle source differs");
                // Optional overrides are used only by the explicitly named
                // diagnostic test oracle, to exercise lazy unknown-tech paths
                // that normal validated State ingress correctly rejects.
                std::optional<game::campaign::State> changed;
                if(!testStages.empty()) {
                    changed=state.clone();
                    for(const auto& [id,stage]:testStages)changed->nations.at(owner).technologyStages[id]=stage;
                }
                const auto& source=changed?*changed:state;
                const auto result=source.definition->catalog->stats(type,damage,game::campaign::catalogContext(source,owner,zone));
                game::campaign::appendCatalogStats(values,result);
            }catch(const std::out_of_range& e){error=1;message=e.what();}
             catch(const std::exception& e){error=2;message=e.what();}
            if(error)values.assign(18,0);
            out.stats.insert(out.stats.end(),values.begin(),values.end());out.errors.push_back(error);out.messages.push_back(message);
        }
        return out;
    }
    static std::unique_ptr<NativeCampaignEnv> fixture(const NativeCampaignEnv& env,const std::string& document) {
        return env.call([&](const auto& value) {
            const auto context=game::campaign::DeviceStateContext(value.engine());
            auto definition=std::make_shared<game::campaign::Definition>(*value.engine().state().definition);
            definition->catalog=game::campaign::Catalog::fromJson(game::json::parse(document));
            definition->fingerprint=game::campaign::contentDigest(
                "catalog-stat-test-fixture:"+definition->fingerprint+":"+definition->catalog->fingerprint());
            auto saved=game::json::parse(value.engine().serialize()).asObject();
            auto state=saved.at("state").asObject();state["definition_fingerprint"]=game::json::Value(definition->fingerprint);
            saved["state"]=game::json::Value(std::move(state));
            auto engine=game::campaign::Engine::restore(definition,context.rules,
                game::campaign::canonicalJson(game::json::Value(std::move(saved))));
            return std::make_unique<NativeCampaignEnv>(CampaignEnv(std::move(engine)));
        });
    }
};
void bindCatalogStats(py::module_& module) {
    using C=CatalogStatsNativeAccess::Context;using O=CatalogStatsNativeAccess::Oracle;
    py::class_<C,std::shared_ptr<C>>(module,"CampaignCatalogStatsContext")
        .def_property_readonly("definition_fingerprint",[](const C& c){return c.definition->fingerprint;})
        .def_property_readonly("wire_context_fingerprint",[](const C& c){return c.wireContextFingerprint;})
        .def_property_readonly("catalog_fingerprint",[](const C& c){return c.catalogFingerprint;})
        .def_property_readonly("strings",[](const C& c){return c.strings;})
        .def_property_readonly("unit_types",[](const C& c){return c.unitTypes;})
        .def_property_readonly("technologies",[](const C& c){return c.technologies;})
        .def_property_readonly("factions",[](const C& c){return c.factions;})
        .def_property_readonly("messages",[](const C& c){return c.messages;})
        .def_property_readonly("lookup_message",[](const C& c){return c.lookupMessage;})
        .def_property_readonly("closed_theatre",[](const C& c){return c.closedTheatre;})
        .def_property_readonly("_test_source_json",[](const C& c){return game::campaign::canonicalJson(c.definition->catalog->sourceData());})
        .def("unit_token_array",[](const C& c){return incomeArray(c,c.unitTokens,{static_cast<py::ssize_t>(c.unitTokens.size())});})
        .def("technology_token_array",[](const C& c){return incomeArray(c,c.technologyTokens,{static_cast<py::ssize_t>(c.technologyTokens.size())});})
        .def("faction_token_array",[](const C& c){return incomeArray(c,c.factionTokens,{static_cast<py::ssize_t>(c.factionTokens.size())});})
        .def("home_token_array",[](const C& c){return incomeArray(c,c.homeTokens,{static_cast<py::ssize_t>(c.homeTokens.size())});})
        .def("unit_array",[](const C& c){return incomeArray(c,c.units,{static_cast<py::ssize_t>(c.unitTypes.size()),4});})
        .def("state_array",[](const C& c){return incomeArray(c,c.states,{static_cast<py::ssize_t>(c.states.size()/19),19});})
        .def("home_array",[](const C& c){return incomeArray(c,c.home,{static_cast<py::ssize_t>(c.factions.size()),3});})
        .def("technology_array",[](const C& c){return incomeArray(c,c.technology,{static_cast<py::ssize_t>(c.technologies.size()),4});})
        .def("conditional_array",[](const C& c){return incomeArray(c,c.conditionals,{static_cast<py::ssize_t>(c.conditionals.size()/12),12});})
        .def("modifier_array",[](const C& c){return incomeArray(c,c.modifiers,{static_cast<py::ssize_t>(c.modifiers.size()/12),12});})
        .def("match_array",[](const C& c){return incomeArray(c,c.matches,{static_cast<py::ssize_t>(c.modifiers.size()/12),static_cast<py::ssize_t>(c.unitTypes.size())});})
        .def("flag_array",[](const C& c){return incomeArray(c,c.flags,{static_cast<py::ssize_t>(c.flags.size()/4),4});});
    py::class_<O>(module,"CampaignCatalogStatsOracle")
        .def("stat_array",[](const O& o){return incomeArray(o,o.stats,{static_cast<py::ssize_t>(o.errors.size()),9,2});})
        .def("error_array",[](const O& o){return incomeArray(o,o.errors,{static_cast<py::ssize_t>(o.errors.size())});})
        .def_property_readonly("messages",[](const O& o){return o.messages;});
    module.def("campaign_catalog_stats_context",&CatalogStatsNativeAccess::context);
    module.def("campaign_catalog_stats_oracle",[](std::shared_ptr<C> context,const std::vector<NativeCampaignEnv*>& envs,
            const std::vector<std::tuple<std::int64_t,std::string,int,std::string,std::optional<std::string>>>& queries) {
        return CatalogStatsNativeAccess::oracle(std::move(context),envs,queries);
    });
    module.def("_campaign_catalog_stats_test_oracle",&CatalogStatsNativeAccess::oracle);
    module.def("_campaign_catalog_stats_test_fixture",&CatalogStatsNativeAccess::fixture);
}
