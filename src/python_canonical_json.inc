// One-time native ingress metadata for exact binary64 JSON spellings. New
// resident integer values are formatted from their exact bits on the GPU.
struct CanonicalNumberContext {
    std::string wireContextFingerprint;
    std::vector<std::int64_t> words,offsets {0};
    std::vector<std::uint8_t> bytes;
    explicit CanonicalNumberContext(const game::campaign::DeviceStateBatch& batch) {
        batch.validate();wireContextFingerprint=batch.context->wireContextFingerprint;
        std::map<std::uint64_t,std::string> unique;
        auto add=[&](const auto& nodes) {for(const auto& row:nodes) {
            if(row[0]!=static_cast<std::int64_t>(game::campaign::DeviceTag::NumberBits))continue;
            const auto bits=static_cast<std::uint64_t>(row[2])|(static_cast<std::uint64_t>(row[3])<<32);
            unique.try_emplace(bits,game::campaign::canonicalJson(game::json::Value(std::bit_cast<double>(bits))));
        }};
        add(batch.context->records);add(batch.records);
        for(const auto& [bits,text]:unique) {
            words.push_back(static_cast<std::int64_t>(bits&UINT64_C(0xffffffff)));
            words.push_back(static_cast<std::int64_t>(bits>>32));
            bytes.insert(bytes.end(),text.begin(),text.end());
            if(bytes.size()>static_cast<std::size_t>(std::numeric_limits<std::int64_t>::max()))
                throw std::length_error("Canonical number arena overflow");
            offsets.push_back(static_cast<std::int64_t>(bytes.size()));
        }
    }
};
void bindCanonicalJson(py::module_& module) {
    using C=CanonicalNumberContext;
    py::class_<C,std::shared_ptr<C>>(module,"CampaignCanonicalNumberContext")
        .def_property_readonly("wire_context_fingerprint",[](const C& c){return c.wireContextFingerprint;})
        .def("word_array",[](const C& c){return incomeArray(c,c.words,{static_cast<py::ssize_t>(c.words.size()/2),2});})
        .def("offset_array",[](const C& c){return incomeArray(c,c.offsets,{static_cast<py::ssize_t>(c.offsets.size())});})
        .def("byte_array",[](const C& c){return deviceStateArray(c,c.bytes.data(),{static_cast<py::ssize_t>(c.bytes.size())});});
    module.def("campaign_canonical_number_context",[](const game::campaign::DeviceStateBatch& batch) {
        py::gil_scoped_release release;return std::make_shared<C>(batch);
    });
    module.def("campaign_canonical_json_probe",[](const std::vector<std::string>& texts) {
        py::gil_scoped_release release;std::vector<std::string> output;output.reserve(texts.size());
        for(const auto& text:texts)output.push_back(game::campaign::canonicalJson(game::json::parse(text)));
        return output;
    });
}
