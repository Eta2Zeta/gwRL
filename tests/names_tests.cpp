// Names held as numbers (include/game/names.hpp): the tables, the number type
// and the containers keyed by numbers, then the zone table of the scenario.
#include "game/campaign.hpp"
#include "game/names.hpp"

#include <filesystem>
#include <functional>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using namespace game::campaign;

void check(bool ok, const std::string& why) {
    if (!ok) throw std::runtime_error(why);
}
void rejects(const std::function<void()>& operation, const std::string& why) {
    try {
        operation();
    } catch (const std::exception&) {
        return;
    }
    throw std::runtime_error(why);
}
template <class Error>
void throwsWith(const std::function<void()>& operation, const std::string& message, const std::string& why) {
    try {
        operation();
    } catch (const Error& error) {
        check(std::string(error.what()) == message, why + ": got '" + error.what() + "'");
        return;
    }
    throw std::runtime_error(why);
}

void tablesNumberNamesInSortedOrder() {
    const NameTable<ZoneKind> zones({"sea_p15", "land_b", "land_a", "sea_p1"});
    check(zones.names() == std::vector<std::string>({"land_a", "land_b", "sea_p1", "sea_p15"}),
          "A table does not list its names sorted bytewise");
    for (std::size_t at = 0; at < zones.size(); ++at) {
        const auto zone = zones.number(zones.names()[at]);
        check(zone.index() == at && zones.name(zone) == zones.names()[at], "A name's number is not its place");
    }
    check(zones.number("land_a") < zones.number("land_b") && zones.number("sea_p1") < zones.number("sea_p15"),
          "Numbers do not compare as their names do");
    check(zones.find("land_c") == std::nullopt && !zones.contains("land_c") && zones.contains("sea_p1"),
          "Finding a name gives the wrong answer");
    throwsWith<std::runtime_error>([&] { zones.number("land_c"); }, "Unknown zone: land_c",
                                   "An unknown name is not reported by kind and name");
    rejects([&] { zones.name(ZoneId {}); }, "A number naming nothing was given a name");
    rejects([&] { zones.name(ZoneId::fromIndex(4)); }, "A number beyond the table was given a name");
    std::vector<ZoneId> listed;
    for (const auto zone : zones.numbers()) listed.push_back(zone);
    check(listed.size() == 4 && listed.front() == zones.number("land_a") && listed.back() == zones.number("sea_p15"),
          "A table's numbers are not every number, ascending");
    rejects([] { NameTable<ZoneKind>({"a", "b", "a"}); }, "A repeated name was accepted");
    rejects([] { NameTable<ZoneKind>({"a", ""}); }, "An empty name was accepted");
    rejects([] { NameTable<ZoneKind>(std::vector<std::string>(ZoneKind::capacity + 1, "x")); },
            "More names than the kind holds were accepted");
}

void numbersHaveNoNameUntilATableGivesThem() {
    const ZoneId none;
    check(!none.valid() && ZoneId::fromIndex(0).valid() && none != ZoneId::fromIndex(0),
          "A default number names a zone");
    rejects([] { ZoneId::fromIndex(ZoneKind::capacity); }, "A number beyond the kind's capacity was made");
    check(std::hash<ZoneId> {}(ZoneId::fromIndex(7)) == std::hash<ZoneId> {}(ZoneId::fromIndex(7)),
          "Equal numbers hash differently");
}

void numberMapsKeepNameOrderWithoutNodes() {
    const NameTable<ZoneKind> zones({"c", "a", "b", "d"});
    const auto a = zones.number("a"), b = zones.number("b"), c = zones.number("c"), d = zones.number("d");
    NumberMap<ZoneId, int> map;
    check(map.empty() && map.size() == 0 && map.begin() == map.end(), "A new map is not empty");
    map[c] = 3;
    map.emplace(a, 1);
    check(!map.emplace(a, 9).second && map.at(a) == 1, "Emplacing over an entry replaced it");
    map.try_emplace(d, 4);
    std::vector<std::pair<ZoneId, int>> seen;
    for (const auto& [zone, value] : map) seen.emplace_back(zone, value);
    check(seen == std::vector<std::pair<ZoneId, int>>({{a, 1}, {c, 3}, {d, 4}}), "A map does not list its entries in name order");
    check(map.size() == 3 && map.contains(c) && !map.contains(b) && map.count(b) == 0 && map.find(b) == map.end(),
          "A map's membership is wrong");
    throwsWith<std::out_of_range>([&] { map.at(b); }, "NumberMap::at: no entry", "Reading an absent entry did not throw");
    rejects([&] { map[ZoneId {}]; }, "A map took a key with no name");
    for (auto& [zone, value] : map) value *= 10;
    check(map.at(d) == 40, "Entries could not be changed through iteration");
    auto copy = map;
    copy.erase(c);
    check(map.contains(c) && !copy.contains(c) && copy.size() == 2, "A copy shares entries with its source");
    copy = map;
    check(copy == map && copy.at(c) == 30, "Copying over a map lost entries");
    for (auto it = copy.begin(); it != copy.end();)
        it = it->first == a ? copy.erase(it) : std::next(it);
    check(!copy.contains(a) && copy.size() == 2 && !(copy == map), "Erasing while iterating failed");
    copy.insert_or_assign(b, 2);
    check(copy.at(b) == 2 && copy.insert({b, 7}).second == false && copy.at(b) == 2, "Inserting misbehaved");
    copy.clear();
    check(copy.empty() && copy.begin() == copy.end(), "Clearing left entries");
}

void numberSetsHoldBitsInNameOrder() {
    const NameTable<ZoneKind> zones({"c", "a", "b"});
    const auto a = zones.number("a"), b = zones.number("b"), c = zones.number("c");
    NumberSet<ZoneId> set {c, a};
    check(set.size() == 2 && set.contains(a) && !set.contains(b) && set.count(c) == 1 && !set.empty(),
          "A set's membership is wrong");
    check(set.insert(b).second && !set.insert(b).second, "Inserting twice was reported as new");
    std::vector<ZoneId> listed(set.begin(), set.end());
    check(listed == std::vector<ZoneId>({a, b, c}), "A set does not list its members in name order");
    check(set.erase(b) == 1 && set.erase(b) == 0 && !set.contains(b), "Erasing misbehaved");
    NumberSet<ZoneId> other {b, c};
    auto both = set;
    both &= other;
    check(both == NumberSet<ZoneId>({c}), "Intersection kept the wrong members");
    const auto far = ZoneId::fromIndex(ZoneKind::capacity - 1);
    set.insert(far);
    check(*std::prev(std::vector<ZoneId>(set.begin(), set.end()).end()) == far, "The last bit is not listed");
    rejects([&] { set.insert(ZoneId {}); }, "A set took a number with no name");
    check(!set.contains(ZoneId {}), "A set contains a number with no name");
    set.clear();
    check(set.empty() && set.begin() == set.end(), "Clearing left members");
}

void theScenarioNumbersItsMapZones() {
    const auto state = loadScenario(std::filesystem::path(GWRL_SOURCE_DIR) / "game_content/scenarios/japan_china_1936");
    const auto& nodes = state.definition->geography.require("nodes").asObject();
    std::vector<std::string> names;
    for (const auto& [id, node] : nodes) names.push_back(id);
    check(state.definition->names->zones.names() == names, "The zone table is not the map's zones in name order");
    for (const auto& name : names)
        check(zoneName(state, zoneNumber(state, name)) == name, "A zone's name and number do not round-trip");
    check(zoneNumbers(state, {"land_china_beiping", "sea_p15"}).size() == 2 &&
              zoneNames(state, zoneNumbers(state, {"land_china_beiping", "sea_p15"})) ==
                  std::vector<Id>({"land_china_beiping", "sea_p15"}),
          "Zone lists do not convert both ways");
    for (const auto& [zone, territory] : state.territories)
        check(mapNode(state, zone).require("type").asString() == "land", "A territory is not a land zone");
    // The saved position names zones; restoring it numbers them again.
    const auto restored = State::fromJson(state.definition, state.toJson());
    check(restored.serialize() == state.serialize() && restored.planningKey() == state.planningKey(),
          "Saving and restoring changed the position");
}
}  // namespace

int main() {
    const std::vector<std::pair<std::string, std::function<void()>>> tests {
        {"tables number names in sorted order", tablesNumberNamesInSortedOrder},
        {"numbers have no name until a table gives them", numbersHaveNoNameUntilATableGivesThem},
        {"number maps keep name order without nodes", numberMapsKeepNameOrderWithoutNodes},
        {"number sets hold bits in name order", numberSetsHoldBitsInNameOrder},
        {"the scenario numbers its map zones", theScenarioNumbersItsMapZones},
    };
    int failures = 0;
    for (const auto& [name, test] : tests) {
        try {
            test();
            std::cout << "PASS " << name << '\n';
        } catch (const std::exception& error) {
            ++failures;
            std::cout << "FAIL " << name << ": " << error.what() << '\n';
        }
    }
    return failures == 0 ? 0 : 1;
}
