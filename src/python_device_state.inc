// Included inside python_bindings.cpp's private namespace after NativeCampaignEnv.
// Only explicit snapshot boundaries expose these privileged state/RNG buffers.
struct DeviceStateNativeAccess {
    using Context = game::campaign::DeviceStateContext;
    using Batch = game::campaign::DeviceStateBatch;
    static std::shared_ptr<Context> context(const NativeCampaignEnv& env) {
        return env.call([](const auto& value){return std::make_shared<Context>(value.engine());});
    }
    static Batch capture(std::shared_ptr<Context> context, const std::vector<NativeCampaignEnv*>& envs) {
        const auto owners = pinNativeEnvironments(envs);
        py::gil_scoped_release release;
        Batch result(context);
        for (const auto* env : envs) {
            if (!env) throw std::invalid_argument("Null device state lane");
            std::lock_guard lock(env->mutex_);
            result.append(env->env_.engine());
        }
        return result;
    }
    static std::vector<std::unique_ptr<NativeCampaignEnv>> restore(const Batch& batch) {
        py::gil_scoped_release release;
        std::vector<std::unique_ptr<NativeCampaignEnv>> result;
        for (std::size_t lane=0;lane<batch.rows();++lane)
            result.push_back(std::make_unique<NativeCampaignEnv>(CampaignEnv(batch.restore(lane))));
        return result;
    }
};
template<class Owner,class T>
py::array deviceStateArray(const Owner& owner,const T* data,std::vector<py::ssize_t> shape) {
    std::vector<py::ssize_t> strides(shape.size());py::ssize_t stride=sizeof(T);
    for(std::size_t i=shape.size();i--;){strides[i]=stride;
        if(shape[i]<0||(shape[i]&&stride>std::numeric_limits<py::ssize_t>::max()/shape[i]))
            throw std::overflow_error("Device state array dimension overflow");
        stride*=shape[i];
    }
    auto result=py::array(py::dtype::of<T>(),shape,strides,data,py::cast(&owner,py::return_value_policy::reference));
    result.attr("setflags")(py::arg("write")=false);return result;
}
template<class T> std::vector<T> deviceStateCopy(const py::array& array,std::size_t dimensions) {
    if(!array.dtype().is(py::dtype::of<T>())||static_cast<std::size_t>(array.ndim())!=dimensions||
       !(array.flags()&py::array::c_style))throw py::value_error("Device state buffer must preserve native contiguous shape/dtype");
    const auto* begin=static_cast<const T*>(array.data());
    if(!array.size())return {};
    return std::vector<T>(begin,begin+array.size());
}
void bindDeviceState(py::module_& module) {
    using C=DeviceStateNativeAccess::Context;using B=DeviceStateNativeAccess::Batch;
    static_assert(sizeof(game::campaign::DeviceRecord)==5*sizeof(std::int64_t));
    py::class_<C,std::shared_ptr<C>>(module,"CampaignDeviceStateContext")
        .def_property_readonly("schema",[](const C&){return game::campaign::deviceStateSchema;})
        .def_property_readonly("definition_fingerprint",[](const C& c){return c.definitionFingerprint;})
        .def_property_readonly("rules_id",[](const C& c){return c.rulesId;})
        .def_property_readonly("string_count",[](const C& c){return c.strings.size();})
        .def("record_array",[](const C& c){return deviceStateArray(c,reinterpret_cast<const std::int64_t*>(c.records.data()),{static_cast<py::ssize_t>(c.records.size()),5});})
        .def("string_bytes",[](const C& c){return deviceStateArray(c,c.stringBytes.data(),{static_cast<py::ssize_t>(c.stringBytes.size())});})
        .def("string_offsets",[](const C& c){return deviceStateArray(c,c.stringOffsets.data(),{static_cast<py::ssize_t>(c.stringOffsets.size())});});
    py::class_<B>(module,"CampaignDeviceStateBatch")
        .def_property_readonly("context",[](const B& b){return std::const_pointer_cast<C>(b.context);})
        .def_property_readonly("lane_count",&B::rows)
        .def_property_readonly("max_lane_records",[](const B& b){return b.maxLaneRecords;})
        .def_property_readonly("section_names",[](const B&){return B::sectionNames();})
        .def("record_array",[](const B& b){return deviceStateArray(b,reinterpret_cast<const std::int64_t*>(b.records.data()),{static_cast<py::ssize_t>(b.records.size()),5});})
        .def("lane_offsets",[](const B& b){return deviceStateArray(b,b.laneOffsets.data(),{static_cast<py::ssize_t>(b.laneOffsets.size())});})
        .def("section_array",[](const B& b){return deviceStateArray(b,b.sections.data(),{static_cast<py::ssize_t>(b.rows()),static_cast<py::ssize_t>(B::sectionNames().size())});})
        .def("string_bytes",[](const B& b){return deviceStateArray(b,b.stringBytes.data(),{static_cast<py::ssize_t>(b.stringBytes.size())});})
        .def("string_offsets",[](const B& b){return deviceStateArray(b,b.stringOffsets.data(),{static_cast<py::ssize_t>(b.stringOffsets.size())});})
        .def("validate",[](const B& b){py::gil_scoped_release release;b.validate();});
    module.def("device_state_context",&DeviceStateNativeAccess::context);
    module.def("capture_device_states",&DeviceStateNativeAccess::capture);
    module.def("restore_device_states",&DeviceStateNativeAccess::restore);
    module.def("device_state_batch_from_packed",[](std::shared_ptr<C> context,const py::array& records,
            const py::array& offsets,const py::array& bytes,const py::array& stringOffsets) {
        auto data=deviceStateCopy<std::int64_t>(records,2);
        if(records.shape(1)!=5)throw py::value_error("Device state record width mismatch");
        std::vector<game::campaign::DeviceRecord> nodes(data.size()/5);
        for(std::size_t i=0;i<nodes.size();++i)std::copy_n(data.data()+i*5,5,nodes[i].data());
        auto lanes=deviceStateCopy<std::int64_t>(offsets,1);auto strings=deviceStateCopy<std::uint8_t>(bytes,1);
        auto indexes=deviceStateCopy<std::int64_t>(stringOffsets,1);
        py::gil_scoped_release release;
        return B::fromPacked(context,std::move(nodes),std::move(lanes),std::move(strings),std::move(indexes));
    });
    module.attr("CAMPAIGN_DEVICE_STATE_SCHEMA")=game::campaign::deviceStateSchema;
}
