// Read-only definition preparation and independent original validateRoute API.
struct MovementNativeAccess {
    using Context=game::campaign::MovementContext;
    using Query=game::campaign::MovementQuery;
    using Result=game::campaign::MovementOracleResult;
    static std::shared_ptr<Context> context(const NativeCampaignEnv& env){
        return env.call([](const auto& value){return std::make_shared<Context>(value.engine().state().definition);});
    }
    static py::list oracle(std::shared_ptr<Context> context,const std::vector<NativeCampaignEnv*>& envs,
                           const std::vector<Query>& queries){
        if(!context)throw py::value_error("Movement oracle requires its frozen context");
        const auto owners=pinNativeEnvironments(envs);std::vector<Result> results;results.reserve(queries.size());
        for(const auto& query:queries){
            if(query.lane<0||static_cast<std::uint64_t>(query.lane)>=envs.size()||!envs[query.lane])
                throw py::value_error("Movement oracle lane outside batch");
            results.push_back(envs[query.lane]->call([&](const auto& value){Result result;
                const auto& state=value.engine().state();
                if(state.definition->fingerprint!=context->definition->fingerprint)
                    throw std::invalid_argument("Movement oracle definition mismatch");
                try{result.result=game::campaign::validateRoute(state,query.request);}
                catch(const std::out_of_range& e){result.exception=1;result.message=e.what();}
                catch(const std::exception& e){result.exception=2;result.message=e.what();}
                return result;}));
        }
        py::list output;
        for(const auto& row:results){const auto& r=row.result;py::dict approach;
            approach["from"]=r.approach.from;approach["to"]=r.approach.to;
            approach["node_terrain"]=r.approach.nodeTerrain;approach["border_terrain"]=r.approach.borderTerrain;
            approach["river"]=r.approach.river;approach["river_known"]=r.approach.riverKnown;
            py::dict value;value["allowed"]=r.allowed;value["reason"]=r.reason;value["cost"]=r.cost;
            value["exhausts_movement"]=r.exhaustsMovement;value["regions"]=r.regions;value["approach"]=approach;
            value["exception"]=row.exception;value["message"]=row.message;output.append(value);
        }return output;
    }
};
void bindMovementContext(py::module_& module){
    using C=MovementNativeAccess::Context;using Q=MovementNativeAccess::Query;
    py::class_<C,std::shared_ptr<C>>(module,"CampaignMovementContext")
        .def_property_readonly("definition_fingerprint",[](const C& c){return c.definition->fingerprint;})
        .def_property_readonly("zones",[](const C& c){return c.zones;})
        .def_property_readonly("nations",[](const C& c){return c.nations;})
        .def_property_readonly("players",[](const C& c){return c.players;})
        .def_property_readonly("unit_types",[](const C& c){return c.unitTypes;})
        .def_property_readonly("terrains",[](const C& c){return c.terrains;})
        .def_property_readonly("regions",[](const C& c){return c.regions;})
        .def_property_readonly("facility_ids",[](const C& c){return c.facilityIds;})
        .def_property_readonly("exception_messages",[](const C& c){return c.exceptionMessages;})
        .def_property_readonly("relations_context",[](const C& c){return std::make_shared<game::campaign::RelationsContext>(c.definition);})
        .def("node_array",[](const C& c){return incomeArray(c,c.nodes,{static_cast<py::ssize_t>(c.zones.size()),7});})
        .def("edge_array",[](const C& c){const auto Z=static_cast<py::ssize_t>(c.zones.size());return incomeArray(c,c.edges,{Z,Z,20});})
        .def("node_terrain_array",[](const C& c){return incomeArray(c,c.nodeTerrain,{static_cast<py::ssize_t>(c.zones.size()),static_cast<py::ssize_t>(c.terrains.size())});})
        .def("border_terrain_array",[](const C& c){const auto Z=static_cast<py::ssize_t>(c.zones.size());return incomeArray(c,c.borderTerrain,{Z,Z,static_cast<py::ssize_t>(c.terrains.size())});})
        .def("river_bank_array",[](const C& c){const auto Z=static_cast<py::ssize_t>(c.zones.size());return incomeArray(c,c.riverBanks,{Z,Z,Z});})
        .def("crossing_sea_array",[](const C& c){const auto Z=static_cast<py::ssize_t>(c.zones.size());return incomeArray(c,c.crossingSeas,{Z,Z,Z});})
        .def("bank_unknown_array",[](const C& c){const auto Z=static_cast<py::ssize_t>(c.zones.size());return incomeArray(c,c.bankUnknown,{Z,Z,3});})
        .def("crossing_missing_array",[](const C& c){const auto Z=static_cast<py::ssize_t>(c.zones.size());return incomeArray(c,c.crossingSeasMissing,{Z,Z,3});})
        .def("home_array",[](const C& c){return incomeArray(c,c.home,{static_cast<py::ssize_t>(c.nations.size()),static_cast<py::ssize_t>(c.zones.size())});})
        .def("class_array",[](const C& c){return incomeArray(c,c.classes,{static_cast<py::ssize_t>(c.unitTypes.size()),8});})
        .def("fort_array",[](const C& c){return incomeArray(c,c.fortBorders,{static_cast<py::ssize_t>(c.facilityIds.size()),static_cast<py::ssize_t>(c.zones.size())});})
        .def("fort_error_array",[](const C& c){return incomeArray(c,c.fortErrors,{static_cast<py::ssize_t>(c.facilityIds.size()),2});})
        .def("capacity_array",[](const C& c){return incomeArray(c,c.capacities,{static_cast<py::ssize_t>(c.regions.size()),3});})
        .def("crossing_counter_array",[](const C& c){const auto Z=static_cast<py::ssize_t>(c.zones.size());return incomeArray(c,c.crossingCounter,{Z,Z});})
        .def("crossing_counter_error_array",[](const C& c){const auto Z=static_cast<py::ssize_t>(c.zones.size());return incomeArray(c,c.crossingCounterErrors,{Z,Z,2});})
        .def("rail_counter_array",[](const C& c){return incomeArray(c,c.railCounters,{static_cast<py::ssize_t>(c.players.size()),static_cast<py::ssize_t>(c.regions.size())});})
        .def("counter_bytes",[](const C& c){return deviceStateArray(c,c.counterBytes.data(),{static_cast<py::ssize_t>(c.counterBytes.size())});})
        .def("counter_offsets",[](const C& c){return incomeArray(c,c.counterOffsets,{static_cast<py::ssize_t>(c.counterOffsets.size())});});
    py::class_<Q>(module,"CampaignMovementQuery")
        .def(py::init([](std::int64_t lane,const std::string& unit,const std::vector<std::string>& path,
                        const std::string& mode,bool combat,const std::optional<std::string>& towed){
            Q result;result.lane=lane;result.request={unit,path,game::campaign::parseMovementMode(mode),combat,towed};return result;}),
             py::arg("lane"),py::arg("unit"),py::arg("path"),py::arg("mode")="ordinary",py::arg("combat")=false,py::arg("towed")=py::none());
    module.def("campaign_movement_context",&MovementNativeAccess::context);
    module.def("campaign_route_oracle",&MovementNativeAccess::oracle);
}
