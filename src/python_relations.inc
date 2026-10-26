// Included inside the native binding namespace after incomeArray.
struct RelationsNativeAccess {
    using Context=game::campaign::RelationsContext;
    using Oracle=game::campaign::RelationsOracleBatch;
    static std::shared_ptr<Context> context(const NativeCampaignEnv& env) {
        return env.call([](const auto& value){return std::make_shared<Context>(value.engine().state().definition);});
    }
    static Oracle oracle(std::shared_ptr<Context> context,const std::vector<NativeCampaignEnv*>& envs) {
        const auto owners=pinNativeEnvironments(envs);py::gil_scoped_release release;Oracle out(context,envs.size());
        for(std::size_t row=0;row<envs.size();++row){if(!envs[row])throw std::invalid_argument("Null relations lane");
            std::lock_guard lock(envs[row]->mutex_);out.capture(row,envs[row]->env_.engine().state());}return out;
    }
};
void bindRelations(py::module_& module) {
    using C=RelationsNativeAccess::Context;using O=RelationsNativeAccess::Oracle;
    py::class_<C,std::shared_ptr<C>>(module,"CampaignRelationsContext")
        .def_property_readonly("definition_fingerprint",[](const C& c){return c.definition->fingerprint;})
        .def_property_readonly("nations",[](const C& c){return c.nations;})
        .def_property_readonly("players",[](const C& c){return c.players;})
        .def_property_readonly("territories",[](const C& c){return c.territories;})
        .def_property_readonly("chinese_home_valid",[](const C& c){return c.chineseHomeValid;})
        .def("chinese_home_array",[](const C& c){return incomeArray(c,c.chineseHome,{static_cast<py::ssize_t>(c.territories.size())});})
        .def("warlord_array",[](const C& c){return incomeArray(c,c.warlords,{static_cast<py::ssize_t>(c.nations.size())});});
    py::class_<O>(module,"CampaignRelationsOracleBatch")
        .def("pair_array",[](const O& o){const auto N=static_cast<py::ssize_t>(o.context->nations.size());return incomeArray(o,o.pairs,{static_cast<py::ssize_t>(o.rows),N,N,7});})
        .def("pair_error_array",[](const O& o){const auto N=static_cast<py::ssize_t>(o.context->nations.size());return incomeArray(o,o.pairErrors,{static_cast<py::ssize_t>(o.rows),N,N,7});})
        .def("nation_array",[](const O& o){return incomeArray(o,o.nations,{static_cast<py::ssize_t>(o.rows),static_cast<py::ssize_t>(o.context->nations.size()),3});})
        .def("nation_error_array",[](const O& o){return incomeArray(o,o.nationErrors,{static_cast<py::ssize_t>(o.rows),static_cast<py::ssize_t>(o.context->nations.size()),3});})
        .def("present_array",[](const O& o){return incomeArray(o,o.present,{static_cast<py::ssize_t>(o.rows),static_cast<py::ssize_t>(o.context->nations.size())});})
        .def("land_attack_array",[](const O& o){const auto N=static_cast<py::ssize_t>(o.context->nations.size());return incomeArray(o,o.landAttack,{static_cast<py::ssize_t>(o.rows),N,N});})
        .def("land_attack_error_array",[](const O& o){const auto N=static_cast<py::ssize_t>(o.context->nations.size());return incomeArray(o,o.landAttackErrors,{static_cast<py::ssize_t>(o.rows),N,N});});
    module.def("campaign_relations_context",&RelationsNativeAccess::context);
    module.def("campaign_relations_oracle",&RelationsNativeAccess::oracle);
}
