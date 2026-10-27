// Explicit raw oracle boundary, never used by resident production effects.
struct PoliticalUnitCreationNativeAccess {
    using Context=game::campaign::DeviceStateContext;
    using Batch=game::campaign::DeviceStateBatch;
    struct Row {std::unique_ptr<Batch> packed;int error;std::string message;std::int64_t failed;};
    static py::list add(std::shared_ptr<Context> context,const std::vector<NativeCampaignEnv*>& envs,
                        const std::vector<std::string>& nations,const std::vector<std::string>& types,
                        const std::vector<std::string>& zones,const std::vector<int>& counts,
                        const std::vector<bool>& selected) {
        if(!context||nations.size()!=envs.size()||types.size()!=envs.size()||zones.size()!=envs.size()||
           counts.size()!=envs.size()||selected.size()!=envs.size())
            throw std::invalid_argument("Political unit creation oracle context/lane batch differs");
        const auto pinned=pinNativeEnvironments(envs);py::list output;
        for(std::size_t lane=0;lane<envs.size();++lane){
            auto row=envs[lane]->call([&](const game::campaign::CampaignEnv& value){
                const auto& engine=value.engine();const auto& original=engine.state();
                auto next=original.clone();int error=0;std::string message;std::int64_t failed=0;
                const auto counter=[](const auto& state){const auto it=state.flags.find("politics_sequence");
                    return it==state.flags.end()?std::int64_t{0}:std::int64_t{it->second};};
                if(selected[lane])try {game::campaign::addPoliticalUnit(next,nations[lane],types[lane],zones[lane],counts[lane]);}
                catch(const std::out_of_range& e){error=1;message=e.what();}
                catch(const std::exception& e){error=2;message=e.what();}
                if(error){failed=counter(next)-counter(original);
                    if(message=="Political event sequence overflow")++failed;}
                auto packed=std::make_unique<Batch>(context);
                // Typed Writer preserves negative zero, opaque payloads and
                // original RNG even when this pure helper returns an unresolved
                // optional movement allowance rejected by Engine validation.
                packed->appendDiagnosticState(error?original:next,engine);
                return Row{std::move(packed),error,std::move(message),failed};
            });
            py::dict item;item["packed_state"]=py::cast(std::move(row.packed));item["error"]=row.error;
            item["message"]=row.message;item["first_failure_ordinal"]=row.failed;output.append(item);
        }
        return output;
    }
};
void bindPoliticalUnitCreation(py::module_& module) {
    module.def("campaign_add_political_unit_oracle",&PoliticalUnitCreationNativeAccess::add,
        py::arg("context"),py::arg("envs"),py::arg("nations"),py::arg("types"),py::arg("zones"),py::arg("counts"),py::arg("selected"));
}
