#include "game/income_batch.hpp"

#include <algorithm>
#include <functional>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {
using namespace game::campaign;
using V = game::json::Value;
const Id tokyo = "land_jap_tokyo";
void check(bool yes, const std::string& message) {
    if (!yes) throw std::runtime_error(message);
}
void rejects(const std::function<void()>& operation, const std::string& message) {
    try { operation(); } catch (const std::exception&) { return; }
    throw std::runtime_error(message);
}
std::size_t at(const std::vector<Id>& ids, const Id& id) {
    return std::find(ids.begin(), ids.end(), id) - ids.begin();
}
State original() {
    static const auto baseline = loadScenario(std::filesystem::path(GWRL_SOURCE_DIR) / "game_content/scenarios/japan_china_1936");
    return baseline;
}
void directCapture() {
    auto s = original();
    const auto before = s.serialize();
    auto context = std::make_shared<IncomeContext>(*s.definition);
    IncomeBatch batch(context, 2);
    IncomeOracleBatch oracle(context, 2);
    batch.capture(0, s); oracle.capture(0, s);
    check(context->territories.size() == 37 && context->nations.size() == 13, "Full definition registry not retained");
    check(batch.context.get() == context.get(), "Static context copied instead of shared");
    const auto t = at(context->territories, tokyo), j = at(context->nations, "japan");
    check(batch.territoryState[t * 4] == 1 && batch.territoryState[t * 4 + 1] == j, "Exact possession missing");
    check(batch.nationState[j * 6 + 1] == 1, "Treasury presence omitted");
    check(oracle.income[j * 6] == 0 && oracle.income[j * 6 + 1] == 3 && oracle.income[j * 6 + 5] == 15,
          "Opening oracle differs from existing income evaluator");
    check(s.serialize() == before, "Income capture changed source state/history");
    s.nations.at("japan").treasury = 0;
    s.territories.at(tokyo).flags = {{"city_damage", -39}, {"city_ipp_lost", -3}};
    batch.capture(1, s); oracle.capture(1, s);
    check(batch.nationState[(context->nations.size() + j) * 6 + 1] == 1, "Zero treasury became absent");
    check(batch.territoryState[(context->territories.size() + t) * 4 + 3] == -39, "Signed flag changed");
    check(oracle.effective[(context->territories.size() + t) * 2 + 1] == effectiveTerritorialIpp(s, tokyo), "Signed native oracle changed");
    s.territories.erase(tokyo); s.nations.erase("japan");
    batch.capture(1, s); oracle.capture(1, s);
    check(batch.territoryState[(context->territories.size() + t) * 4] == 0 &&
          batch.territoryState[(context->territories.size() + t) * 4 + 3] == 0, "Reused row retained old flags");
    check(batch.nationState[(context->nations.size() + j) * 6] == 0, "Reused row retained an absent nation");
    check(oracle.income[(context->nations.size() + j) * 6] == 1, "Missing native nation exception hidden");
    check(oracle.effective[(context->territories.size() + t) * 2] == 1, "Missing native territory exception hidden");
    rejects([&]{batch.capture(2, s);}, "Out-of-range row accepted");
    rejects([&]{IncomeBatch bad(nullptr, 1);}, "Absent context accepted");
    rejects([&]{IncomeBatch bad(context, std::numeric_limits<std::size_t>::max());}, "Overflow allocation accepted");
    s.territories.emplace("unregistered", TerritoryState{});
    rejects([&]{batch.capture(0, s);}, "Unregistered territory silently truncated");
    s.territories.erase("unregistered");
    s.nations.emplace("unregistered", NationState{});
    rejects([&]{batch.capture(0, s);}, "Unregistered nation silently truncated");
    auto changed = *s.definition; changed.calendarRounds = 3; s.definition = freezeDefinition(changed);
    rejects([&]{batch.capture(0, s);}, "Different definition silently adopted");
}
void lazyErrorsAndOrdering() {
    auto s = original();
    auto definition = *s.definition;
    auto geography = definition.geography.asObject();
    auto nodes = geography.at("nodes").asObject();
    auto node = nodes.at(tokyo).asObject();
    node["ipp_value"] = V("invalid");
    nodes[tokyo] = V(node); geography["nodes"] = V(nodes); definition.geography = V(geography);
    s.definition = freezeDefinition(definition);
    auto context = std::make_shared<IncomeContext>(*s.definition);
    const auto j = at(context->nations, "japan"), t = at(context->territories, tokyo);
    check(context->territoryStatic[t * 3 + 1] == 0, "Invalid IPP was silently replaced by valid zero");
    IncomeBatch batch(context, 1); IncomeOracleBatch oracle(context, 1);
    batch.capture(0, s); oracle.capture(0, s);
    check(oracle.income[j * 6] == 2 && oracle.effective[t * 2] == 2, "Owned invalid IPP native error missing");
    s.nations.at("japan").treasury.reset();
    s.politics.capitals["japan"] = "unregistered";
    oracle.capture(0, s);
    check(oracle.income[j * 6] == 0 && oracle.income[j * 6 + 1] == 0, "Early return did not mask irrelevant source errors");
    s.nations.at("japan").treasury = 0;
    oracle.capture(0, s);
    check(oracle.income[j * 6] == 1, "Capital lookup must precede invalid territorial IPP");
    s.politics.capitals.erase("japan");
    oracle.capture(0, s);
    check(oracle.income[j * 6] == 2, "Missing capital MAP incorrectly bypassed owned territorial reads");
    s.territories.at(tokyo).possessor = "kmt";
    oracle.capture(0, s);
    check(oracle.income[j * 6] == 0 && oracle.income[j * 6 + 1] == 3 && oracle.income[j * 6 + 2] == 0 &&
          oracle.income[j * 6 + 5] == 0, "Missing capital map should retain full components, collectable false");
}
} // namespace
int main() {
    try { directCapture(); lazyErrorsAndOrdering(); std::cout << "income batch tests passed\n"; }
    catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
