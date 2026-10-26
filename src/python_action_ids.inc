// Independent native canonical/hash formula oracle, plus real menus stay the
// authority in tests. This helper neither generates nor validates legal actions.
void bindActionIds(py::module_& module) {
    module.def("campaign_action_id_formula_probe",[](const std::vector<std::int64_t>& families,
        const std::vector<std::array<std::string,4>>& fields,const std::vector<std::string>& parameters) {
        if(fields.size()!=families.size()||parameters.size()!=families.size())throw std::invalid_argument("Action ID oracle lengths differ");
        py::list output;
        for(std::size_t row=0;row<families.size();++row){const auto f=families[row];const auto& v=fields[row];
            std::string digest,id;
            if(f>=1&&f<=7)digest=game::campaign::contentDigest(game::campaign::canonicalJson(game::json::parse(parameters[row])));
            switch(f){
            case 0:id="end_phase";break;
            case 1:id=v[0]+"_"+v[1]+"_"+digest.substr(0,16);break;
            case 2:id="move_"+digest;break;
            case 3:id="factory_rail_"+digest;break;
            case 4:id=v[0]+"_"+digest.substr(0,20);break;
            case 5:id=v[0]+":"+digest;break;
            case 6:id=v[0]+"_"+digest;break;
            case 7:id=v[3]+":"+v[0]+":"+digest;break;
            case 8:id="rail_permission_"+v[1]+"_"+v[2];break;
            case 9:id="campaign-interrupt-scheduler-v1:play:"+v[0];break;
            case 10:id="campaign-interrupt-scheduler-v1:interrupt:"+v[0];break;
            case 11:id="campaign-interrupt-scheduler-v1:pass:"+v[1];break;
            default:throw std::invalid_argument("Unknown action ID construction family");}
            output.append(py::bytes(id));}
        return output;
    });
}
