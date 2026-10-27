// Included after the common native array helper and NativeCampaignEnv wrapper.
struct WealthNativeAccess {
    using Context=game::campaign::WealthContext;
    using Oracle=game::campaign::WealthOracleBatch;
    static std::shared_ptr<Context> context(const NativeCampaignEnv& env) {
        return env.call([](const auto& value){return std::make_shared<Context>(value.engine().state().definition);});
    }
    static Oracle oracle(std::shared_ptr<Context> context,const std::vector<NativeCampaignEnv*>& envs) {
        const auto owners=pinNativeEnvironments(envs);
        py::gil_scoped_release release;Oracle out(context,envs.size());
        for(std::size_t row=0;row<envs.size();++row){if(!envs[row])throw std::invalid_argument("Null wealth lane");
            std::lock_guard lock(envs[row]->mutex_);out.capture(row,envs[row]->env_.engine().state());}
        return out;
    }
};
template<class Owner>
py::array wealthDoubleArray(const Owner& object,const std::vector<double>& data,std::vector<py::ssize_t> shape) {
    std::vector<py::ssize_t> strides(shape.size());py::ssize_t stride=sizeof(double);
    for(std::size_t i=shape.size();i--;){strides[i]=stride;
        if(shape[i]<0||(shape[i]&&stride>std::numeric_limits<py::ssize_t>::max()/shape[i]))throw std::overflow_error("Wealth dimension overflow");
        stride*=shape[i];}
    auto result=py::array(py::dtype::of<double>(),shape,strides,data.data(),py::cast(&object,py::return_value_policy::reference));
    result.attr("setflags")(py::arg("write")=false);return result;
}
void bindWealth(py::module_& module) {
    using C=WealthNativeAccess::Context;using O=WealthNativeAccess::Oracle;
    py::class_<C,std::shared_ptr<C>>(module,"CampaignWealthContext")
        .def_property_readonly("definition_fingerprint",[](const C& c){return c.definition->fingerprint;})
        .def_property_readonly("income_context",[](const C& c){return std::const_pointer_cast<game::campaign::IncomeContext>(c.income);})
        .def_property_readonly("unit_types",[](const C& c){return c.unitTypes;})
        .def_property_readonly("facility_types",[](const C& c){return c.facilityTypes;})
        .def("unit_array",[](const C& c){return incomeArray(c,c.units,{static_cast<py::ssize_t>(c.unitTypes.size()),4});})
        .def("facility_array",[](const C& c){return incomeArray(c,c.facilities,{static_cast<py::ssize_t>(c.facilityTypes.size()),2});})
        .def("rail_array",[](const C& c){const auto T=static_cast<py::ssize_t>(c.income->territories.size());return incomeArray(c,c.rails,{T,T,2});});
    py::class_<O>(module,"CampaignWealthOracleBatch")
        .def("component_array",[](const O& o){return wealthDoubleArray(o,o.components,{static_cast<py::ssize_t>(o.rows),3,5});})
        .def("wealth_array",[](const O& o){return wealthDoubleArray(o,o.wealth,{static_cast<py::ssize_t>(o.rows),3});})
        .def("gap_array",[](const O& o){return wealthDoubleArray(o,o.gaps,{static_cast<py::ssize_t>(o.rows),3});})
        .def("terminal_array",[](const O& o){return wealthDoubleArray(o,o.terminal,{static_cast<py::ssize_t>(o.rows),3});})
        .def("error_array",[](const O& o){return incomeArray(o,o.errors,{static_cast<py::ssize_t>(o.rows),2});});
    module.def("campaign_wealth_context",&WealthNativeAccess::context);
    module.def("campaign_wealth_oracle",&WealthNativeAccess::oracle);
    module.def("campaign_wealth_component_sum_probe",[](const std::vector<std::vector<std::int64_t>>& rows){
        std::vector<double> output;output.reserve(rows.size());
        for(const auto& row:rows){double value=0;for(auto twice:row)value+=static_cast<double>(twice)*0.5;output.push_back(value);}
        return output;
    });
    module.def("campaign_wealth_scores_probe",[](const std::vector<std::vector<std::int64_t>>& rows,const std::vector<bool>& terminal){
        if(rows.size()!=terminal.size())throw std::invalid_argument("Wealth score probe terminal count differs");
        std::vector<std::vector<std::uint64_t>> wealth,gaps,returns;
        std::vector<std::vector<std::uint32_t>> targets;
        for(std::size_t lane=0;lane<rows.size();++lane){
            if(rows[lane].size()!=15)throw std::invalid_argument("Wealth score probe requires three five-component rows");
            std::array<double,3> values;
            for(std::size_t player=0;player<3;++player){const auto* x=rows[lane].data()+player*5;
                values[player]=game::campaign::WealthComponents{static_cast<double>(x[0])*.5,static_cast<double>(x[1])*.5,
                    static_cast<double>(x[2])*.5,static_cast<double>(x[3])*.5,static_cast<double>(x[4])*.5}.total();}
            const double sum=(values[0]+values[1])+values[2];
            std::vector<std::uint64_t> w,g,r;std::vector<std::uint32_t> t;
            for(const double value:values){const double gap=2*value-sum,result=terminal[lane]?gap:0.0;
                w.push_back(std::bit_cast<std::uint64_t>(value));g.push_back(std::bit_cast<std::uint64_t>(gap));
                r.push_back(std::bit_cast<std::uint64_t>(result));t.push_back(std::bit_cast<std::uint32_t>(static_cast<float>(result)));}
            wealth.push_back(std::move(w));gaps.push_back(std::move(g));returns.push_back(std::move(r));targets.push_back(std::move(t));
        }
        py::dict result;result["wealth_bits"]=wealth;result["gap_bits"]=gaps;result["terminal_bits"]=returns;
        result["terminal_float32_bits"]=targets;return result;
    });
}
