// Conformance/timing oracle only. Production GPU sampling consumes numerical
// buffers; no JSON conversion or native call occurs in its resident dispatch.
void bindRandomProbe(py::module_& module) {
    module.def("campaign_sample_chance_probe", [](const std::vector<std::string>& requestsJson,
            const std::vector<std::string>& randomJson, int repetitions) {
        if (requestsJson.size() != randomJson.size()) throw py::value_error("Probe lane counts differ");
        if (repetitions < 1 || repetitions > 1000000) throw py::value_error("Invalid probe repetitions");
        using namespace game::campaign;
        std::vector<ChanceRequest> requests;
        std::vector<RandomStreams> initial;
        std::vector<ChanceOutcome> outcomes(requestsJson.size());
        std::vector<std::vector<int>> results(requestsJson.size());
        std::vector<RandomStreams> final;
        std::vector<std::string> errors(requestsJson.size());
        double seconds = 0;
        {
            py::gil_scoped_release release;
            for (std::size_t lane=0; lane<requestsJson.size(); ++lane) {
                requests.push_back(chanceRequestFromJson(game::json::parse(requestsJson[lane])));
                initial.push_back(RandomStreams::fromJson(game::json::parse(randomJson[lane])));
            }
            final = initial;
            const auto started = std::chrono::steady_clock::now();
            for (int repeat=0; repeat<repetitions; ++repeat) for (std::size_t lane=0; lane<requests.size(); ++lane) {
                auto random = initial[lane];
                ChanceOutcome outcome;
                try {
                    for (const auto& die : requests[lane].dice) {
                        if (die.sides < 2 || die.maxRerolls < 0) throw std::runtime_error("Invalid die specification");
                        for (int face : die.rerollFaces)
                            if (face <= 0 || face > die.sides) throw std::runtime_error("Invalid reroll face");
                        std::vector<int> path;
                        for (int count=0;;++count) {
                            const int face=random.roll(die.sides);
                            path.push_back(face);
                            if (!die.rerollFaces.contains(face) || count==die.maxRerolls) break;
                        }
                        outcome.faces.push_back(std::move(path));
                    }
                    results[lane]=effectiveResults(requests[lane],outcome);
                    outcomes[lane]=std::move(outcome);final[lane]=std::move(random);errors[lane].clear();
                } catch (const std::exception& error) {
                    errors[lane]=error.what();outcomes[lane]={};results[lane].clear();final[lane]=initial[lane];
                }
            }
            seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
        }
        py::list rows;
        for (std::size_t lane=0;lane<requests.size();++lane) {
            py::dict row;row["faces"]=outcomes[lane].faces;row["effective"]=results[lane];
            row["error"]=errors[lane];row["random"]=game::campaign::canonicalJson(final[lane].toJson());
            rows.append(row);
        }
        py::dict report;report["rows"]=rows;report["rules_seconds"]=seconds;report["repetitions"]=repetitions;
        return report;
    }, py::arg("requests"), py::arg("random"), py::arg("repetitions")=1);
}
