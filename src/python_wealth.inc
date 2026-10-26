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
}
