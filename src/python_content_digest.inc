// Native SHA-256 oracle for GPU action-identity byte conformance and timing.
void bindContentDigestProbe(py::module_& module) {
    module.def("campaign_content_digest_probe", [](const std::vector<py::bytes>& input, int repetitions) {
        if (repetitions < 1 || repetitions > 1000000) throw py::value_error("Invalid digest repetitions");
        std::vector<std::string> bytes, output(input.size());
        bytes.reserve(input.size());
        for (const auto& value : input) bytes.push_back(py::cast<std::string>(value));
        double seconds=0;
        {
            py::gil_scoped_release release;
            const auto started=std::chrono::steady_clock::now();
            for (int repeat=0;repeat<repetitions;++repeat)
                for (std::size_t row=0;row<bytes.size();++row)
                    output[row]=game::campaign::contentDigest(bytes[row]);
            seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
        }
        py::dict result;result["digests"]=output;result["rules_seconds"]=seconds;return result;
    },py::arg("messages"),py::arg("repetitions")=1);
}
