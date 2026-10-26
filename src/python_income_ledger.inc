// Included inside python_bindings.cpp's anonymous namespace, after incomeArray.
struct IncomeLedgerNativeAccess {
    using Context=game::campaign::IncomeContext;
    using Batch=game::campaign::IncomeLedgerBatch;
    using Oracle=game::campaign::IncomeLedgerOracleBatch;
    template<class Result>
    static Result captureAs(std::shared_ptr<Context> context,const std::vector<NativeCampaignEnv*>& envs) {
        const auto owners = pinNativeEnvironments(envs);
        py::gil_scoped_release release;
        Result out(context,envs.size());
        for(std::size_t row=0;row<envs.size();++row) {
            if(!envs[row])throw std::invalid_argument("Null income ledger lane");
            std::lock_guard lock(envs[row]->mutex_);
            out.capture(row,envs[row]->env_.engine().state());
        }
        return out;
    }
};

void bindIncomeLedger(py::module_& module) {
    using C=IncomeLedgerNativeAccess::Context;using B=IncomeLedgerNativeAccess::Batch;using O=IncomeLedgerNativeAccess::Oracle;
    py::class_<B>(module,"CampaignIncomeLedgerBatch")
        .def_property_readonly("income_inputs",[](const B& b)->const game::campaign::IncomeBatch& {return b.incomeInputs;},py::return_value_policy::reference_internal)
        .def_property_readonly("context",[](const B& b){return std::const_pointer_cast<C>(b.incomeInputs.context);})
        .def_property_readonly("component_ids",[](const B& b){return b.componentIds;})
        .def("ledger_array",[](const B& b){return incomeArray(b,b.ledger,{static_cast<py::ssize_t>(b.incomeInputs.rows),static_cast<py::ssize_t>(b.incomeInputs.context->nations.size()),2});})
        .def("component_array",[](const B& b){return incomeArray(b,b.components,{static_cast<py::ssize_t>(b.incomeInputs.rows),static_cast<py::ssize_t>(b.incomeInputs.context->nations.size()),static_cast<py::ssize_t>(b.componentIds.size()),2});})
        .def("clock_array",[](const B& b){return incomeArray(b,b.clock,{static_cast<py::ssize_t>(b.incomeInputs.rows),2});});
    py::class_<O>(module,"CampaignIncomeLedgerOracleBatch")
        .def_property_readonly("after",[](const O& o)->const B& {return o.after;},py::return_value_policy::reference_internal)
        .def("error_array",[](const O& o){return incomeArray(o,o.errors,{static_cast<py::ssize_t>(o.errors.size())});});
    module.def("capture_campaign_income_ledger",&IncomeLedgerNativeAccess::captureAs<B>);
    module.def("campaign_income_ledger_oracle",&IncomeLedgerNativeAccess::captureAs<O>);
}
