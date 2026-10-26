// Native oracle/capture fixtures. Undefined signed-overflow cases are excluded.
#include "game/income_batch.hpp"
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>

namespace {
using namespace game::campaign;
using V = game::json::Value;
void binary(const std::filesystem::path& path, const std::vector<std::int64_t>& values) {
    if (std::filesystem::exists(path)) throw std::runtime_error("Preserve existing income evidence");
    std::ofstream out(path, std::ios::binary);
    out.write(reinterpret_cast<const char*>(values.data()), values.size() * sizeof(std::int64_t));
    if (!out) throw std::runtime_error("Income fixture write failed");
}
V writeFamily(const std::filesystem::path& directory, const State& original,
              const std::vector<State>& states, const std::vector<Id>& labels,
              std::uint64_t repeats, V::Array children = {}) {
    auto context = std::make_shared<IncomeContext>(*original.definition);
    IncomeBatch batch(context, states.size());
    IncomeOracleBatch oracle(context, states.size());
    for (std::size_t row = 0; row < states.size(); ++row) {
        batch.capture(row, states[row]); oracle.capture(row, states[row]);
    }
    std::filesystem::create_directories(directory);
    binary(directory / "territory_static.i64", context->territoryStatic);
    binary(directory / "nation_static.i64", context->nationStatic);
    binary(directory / "territory_state.i64", batch.territoryState);
    binary(directory / "nation_state.i64", batch.nationState);
    binary(directory / "income_oracle.i64", oracle.income);
    binary(directory / "effective_oracle.i64", oracle.effective);
    V::Array nations, territories, cases;
    for (const auto& id : context->nations) nations.emplace_back(id);
    for (const auto& id : context->territories) territories.emplace_back(id);
    for (const auto& id : labels) cases.emplace_back(id);
    const auto before = std::chrono::steady_clock::now();
    std::uint64_t checksum = 0, calls = 0;
    // Repeats are zero for invalid-definition fixtures. Timed ordinary income
    // uses only the valid opening, excluding exception fixtures and I/O/setup.
    for (std::uint64_t r = 0; r < repeats; ++r) for (const auto& [id, _] : original.nations) {
        auto value = evaluateIncome(original, id);
        checksum = checksum * 131 + value.total + value.collectable;
        ++calls;
    }
    const auto seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - before).count();
    const V metadata(V::Object{{"schema", V("income-native-probe-v1")},
        {"definition_fingerprint", V(context->definitionFingerprint)}, {"nations", V(nations)},
        {"territories", V(territories)}, {"cases", V(cases)}, {"subprobes", V(children)},
        {"int_min", V(double(context->intMinimum))}, {"int_max", V(double(context->intMaximum))},
        {"oracle_calls", V(std::to_string(calls))}, {"oracle_checksum", V(std::to_string(checksum))},
        {"oracle_seconds", V(seconds)}});
    std::ofstream(directory / "metadata.json") << canonicalJson(metadata) << '\n';
    return metadata;
}
State invalidIppDefinition(const State& original) {
    auto state = original;
    auto definition = *original.definition;
    auto geography = definition.geography.asObject();
    auto nodes = geography.at("nodes").asObject();
    auto tokyo = nodes.at("land_jap_tokyo").asObject();
    tokyo["ipp_value"] = V("invalid");
    nodes["land_jap_tokyo"] = V(tokyo); geography["nodes"] = V(nodes); definition.geography = V(geography);
    state.definition = freezeDefinition(definition);
    return state;
}
}
int main(int argc, char** argv) {
    try {
        if (argc != 3) throw std::invalid_argument("usage: campaign_income_probe NEW_OUTPUT_DIRECTORY REPETITIONS");
        const auto directory = std::filesystem::path(argv[1]);
        if (std::filesystem::exists(directory)) throw std::invalid_argument("Output must be new");
        const auto repeats = std::stoull(argv[2]);
        if (!repeats) throw std::invalid_argument("Positive repetitions required");
        const auto original = loadScenario(std::filesystem::path(GWRL_SOURCE_DIR) / "game_content/scenarios/japan_china_1936");
        std::vector<State> states{original};
        std::vector<Id> labels{"opening"};
        const auto add = [&](const Id& label, const auto& edit) {
            auto s = original; edit(s); states.push_back(std::move(s)); labels.push_back(label);
        };
        add("zero_treasury", [](auto& s){s.nations.at("japan").treasury = 0;});
        add("no_treasury", [](auto& s){s.nations.at("japan").treasury.reset();});
        add("surrendered", [](auto& s){s.politics.surrendered.insert("japan");});
        add("lost_capital", [](auto& s){s.territories.at(s.politics.capitals.at("japan")).possessor = "ccp";});
        add("no_capital_map", [](auto& s){s.politics.capitals.erase("japan");});
        add("missing_capital_territory", [](auto& s){s.territories.erase(s.politics.capitals.at("japan"));});
        add("minor_ignores_missing_capital", [](auto& s){s.nations.at("kmt").powerStatus = "regional";s.politics.capitals["kmt"] = "unregistered";});
        add("early_out_masks_missing_capital", [](auto& s){s.nations.at("japan").treasury.reset();s.politics.capitals["japan"] = "unregistered";});
        add("nation_absent", [](auto& s){s.nations.erase("japan");});
        add("dynamic_nonforced_major_account", [](auto& s){
            s.nations.at("mongolia").powerStatus = "major";s.nations.at("mongolia").treasury = 0;
            s.politics.capitals["mongolia"] = "land_mongolia_central_mongolia";
        });
        for (const int damage : {19, 20, 39, 40, -19, -20, -39, -40})
            add("signed_damage_" + std::to_string(damage), [&](auto& s){
                s.territories.at("land_jap_tokyo").flags["city_damage"] = damage;
                s.territories.at("land_jap_tokyo").flags["city_ipp_lost"] = -3;
            });
        add("bonus_survives_zero_effective_ipp", [](auto& s){
            for (const auto& id : {"land_china_beiping", "land_china_hopeh", "land_china_shantung", "land_china_nanking", "land_china_hunan", "land_kwangtung"})
                if (s.territories.contains(id)) {
                    s.territories.at(id).possessor = "japan";s.territories.at(id).flags["city_damage"] = 1000;
                }
        });
        add("dadao_possession_does_not_merge_japan", [](auto& s){
            s.territories.at("land_china_beiping").possessor = "dadao";
            s.territories.at("land_kwangtung").possessor = "dadao";
        });
        const auto metadata = writeFamily(directory, original, states, labels, repeats, {V("invalid_ipp")});
        const auto invalid = invalidIppDefinition(original);
        states = {invalid}; labels = {"owned_invalid_ipp"};
        auto state = invalid;
        state.nations.at("japan").treasury.reset();state.politics.capitals["japan"] = "unregistered";
        states.push_back(state);labels.push_back("early_out_masks_invalid_ipp_and_capital");
        state.nations.at("japan").treasury = 0;
        states.push_back(state);labels.push_back("capital_error_precedes_invalid_ipp");
        state.politics.capitals.erase("japan");
        states.push_back(state);labels.push_back("no_capital_map_still_reads_owned_invalid_ipp");
        state.territories.at("land_jap_tokyo").possessor = "kmt";
        states.push_back(state);labels.push_back("unowned_invalid_ipp_is_lazy");
        writeFamily(directory / "invalid_ipp", invalid, states, labels, 0);
        std::cout << canonicalJson(metadata) << '\n';
        return 0;
    } catch (const std::exception& e) {std::cerr << e.what() << '\n';return 1;}
}
