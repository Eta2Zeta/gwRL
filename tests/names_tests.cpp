// Names held as numbers (include/game/names.hpp): the tables, the number type
// and the containers keyed by numbers, then the scenario's zone and nation tables
// and the catalog's unit type and unit class tables, then the mark table and
// the sets of marks keyed by it.
#include "game/campaign.hpp"
#include "game/catalog.hpp"
#include "game/marks.hpp"
#include "game/names.hpp"

#include <algorithm>
#include <filesystem>
#include <functional>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <type_traits>
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

// Numbers of different kinds never mix, and no string or integer becomes one.
static_assert(!std::is_constructible_v<NationId, ZoneId> && !std::is_constructible_v<ZoneId, NationId>);
static_assert(!std::is_constructible_v<NationId, const char*> && !std::is_constructible_v<NationId, std::string>);
static_assert(!std::is_constructible_v<NationId, int> && !std::is_constructible_v<ZoneId, std::size_t>);
static_assert(!std::is_constructible_v<UnitTypeId, NationId> && !std::is_constructible_v<UnitTypeId, std::string>);
static_assert(!std::is_constructible_v<UnitClassId, UnitTypeId> && !std::is_constructible_v<UnitClassId, const char*>);
// A mark key refers to its argument's text, so it cannot be made from a temporary string.
static_assert(!std::is_constructible_v<MarkKey, MarkId, std::string&&> && std::is_constructible_v<MarkKey, MarkId, const std::string&>);
static_assert(!std::is_convertible_v<const char*, MarkKey> && !std::is_convertible_v<std::string, MarkKey>);
// Two names in braces are not a pair of iterators into a set of numbers.
static_assert(!std::is_constructible_v<NumberSet<NationId>, const char*, const char*>);

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
    const NumberMap<ZoneId, int> listed {{c, 3}, {a, 1}, {a, 9}};
    check(listed.size() == 2 && listed.begin()->first == a && listed.at(a) == 1 && listed.at(c) == 3,
          "A map made from a list does not keep the first value of a key, in name order");
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

void theScenarioNumbersItsNations() {
    const auto state = loadScenario(std::filesystem::path(GWRL_SOURCE_DIR) / "game_content/scenarios/japan_china_1936");
    std::vector<std::string> names;
    for (const auto& [id, faction] : state.definition->factions) names.push_back(id);
    check(state.definition->names->nations.names() == names,
          "The nation table is not the definition's factions in name order");
    check(std::find(names.begin(), names.end(), "dadao") != names.end() && !hasNation(state, "dadao"),
          "Dormant Dadao is not numbered before it enters play");
    for (const auto& name : names)
        check(nationName(state, nationNumber(state, name)) == name, "A nation's name and number do not round-trip");
    for (const auto& [nation, n] : state.nations)
        check(state.definition->factions.contains(nationName(state, nation)), "A nation in play has no faction");
    // A nation's faction by number is its faction by name, home zones included.
    for (const auto nation : state.definition->names->nations.numbers()) {
        const auto& byName = state.definition->factions.at(nationName(state, nation));
        const auto& byNumber = nationFaction(state, nation);
        check(byNumber.id == byName.id && byNumber.homeZones == byName.homeZones &&
                  byNumber.homeCountryKnown == byName.homeCountryKnown && byNumber.dormant == byName.dormant,
              "A nation's faction by number differs from its faction by name");
    }
    check(!nationFaction(state, nationNumber(state, "japan")).homeZones.empty(),
          "The copies were made before the home zones were numbered");
    rejects([&] { nationFaction(state, NationId {}); }, "A number naming no nation had a faction");
    // The nations the rules name: those the campaign lacks have no number.
    const auto& known = knownNations(state);
    check(known.japan == nationNumber(state, "japan") && known.kmt == nationNumber(state, "kmt") &&
              known.ccp == nationNumber(state, "ccp") && known.dadao == nationNumber(state, "dadao") &&
              known.mongolia == nationNumber(state, "mongolia") && !known.ussr,
          "The known nations are not the scenario's numbers");
    check(!findNation(state, "comintern") && !hasNation(state, "ussr"), "A player or an absent nation was numbered");
    throwsWith<std::runtime_error>([&] { nationNumber(state, "comintern"); }, "Unknown nation: comintern",
                                   "An unknown nation is not reported by kind and name");
    // An empty possessor is no nation, not even one the scenario lacks.
    const std::optional<NationId> nobody;
    check(!isNation(state, nobody, "ussr") && !isNation(state, nobody, "kmt") &&
              isNation(state, known.kmt, "kmt") && !isNation(state, *known.kmt, "ccp"),
          "isNation confused an empty possessor with an absent nation");
    check(state.definition->turnNations.size() == state.definition->turnOrder.size(), "The turn order lost nations");
    for (std::size_t at = 0; at < state.definition->turnOrder.size(); ++at)
        check(nationName(state, state.definition->turnNations[at]) == state.definition->turnOrder[at],
              "The numbered turn order differs from the named one");
    check(nationName(state, state.currentNation()) == state.currentNationName(),
          "The current nation's number and name disagree");
}
void theCatalogNumbersItsUnitTypesAndClasses() {
    const auto state = loadScenario(std::filesystem::path(GWRL_SOURCE_DIR) / "game_content/scenarios/japan_china_1936");
    const auto& catalog = *state.definition->catalog;
    // The unit types in name order, each definition at its own number.
    const auto& types = catalog.unitTypes();
    check(types.size() == catalog.units().size() && types.size() == 53, "The catalog does not number its 53 unit types");
    for (const auto type : types.numbers()) {
        const auto& unit = catalog.unit(type);
        check(unit.number == type && unit.id == types.name(type) && &catalog.unit(unit.id) == &unit &&
                  unitTypeNumber(state, unit.id) == type && unitTypeName(state, type) == unit.id,
              "A unit type's number, name and definition do not agree");
    }
    rejects([&] { catalog.unit(UnitTypeId {}); }, "A number naming no unit type had a definition");
    throwsWith<std::runtime_error>([&] { unitTypeNumber(state, "invented_type"); }, "Unknown unit type: invented_type",
                                   "An unknown unit type is not reported by kind and name");
    // The classes: every class some unit has, and each unit's classes by number.
    const auto& classes = catalog.unitClasses();
    check(classes.size() == 17 && classes.contains("naval") && classes.contains("vehicle_class"),
          "The catalog does not number its 17 unit classes");
    const auto& infantry = catalog.unit("infantry");
    check(infantry.classes.contains(classes.number("land")) && infantry.classes.contains(classes.number("infantry_class")) &&
              !infantry.classes.contains(classes.number("naval")) && catalog.unitHasClass(infantry.number, "land") &&
              !catalog.unitHasClass(infantry.number, "invented_class"),
          "A unit's classes are not its catalog classes");
    // The names the rules use, each the number of the string it is spelled as.
    const auto& known = catalog.knownUnitTypes();
#define GWRL_CHECK(name) check(known.name == types.number(#name), "Known unit type " #name " has another number");
    GWRL_KNOWN_UNIT_TYPES(GWRL_CHECK)
#undef GWRL_CHECK
    const auto& knownClasses = catalog.knownUnitClasses();
#define GWRL_CHECK(name) check(knownClasses.name == classes.number(#name), "Known unit class " #name " has another number");
    GWRL_UNIT_CLASSES(GWRL_CHECK)
#undef GWRL_CHECK
    check(&knownUnitTypes(state) == &known && &knownUnitClasses(state) == &knownClasses,
          "The position reads other known names than its catalog's");
}
void marksAreNumberedInNameOrder() {
    const auto names = markNames();
    check(names.size() > 200 && std::is_sorted(names.begin(), names.end()), "The mark table is not sorted by name");
    for (std::size_t at = 0; at < names.size(); ++at) {
        const auto mark = markNumber(names[at]);
        check(mark.index() == at && markName(mark) == names[at] && findMark(names[at]) == mark, "A mark's number is not its place");
    }
    check(markName(mark::campaign_started) == "__campaign_started" && mark::campaign_started.index() == 0 &&
              markName(mark::placed_this_turn) == "placed_this_turn",
          "A mark constant names another mark");
    check(markTakesArgument(mark::naval_last_origin) && markArgument(mark::naval_last_origin) == "zone" &&
              !markTakesArgument(mark::placed_this_turn) && markSeparator(mark::evolution_pending) == '_' &&
              markSeparator(mark::in_port) == ':',
          "A mark's argument or separator is wrong");
    // Names round-trip, and a name the table lacks or whose argument does not fit is refused.
    for (const std::string name : {"placed_this_turn", "naval_last_origin:sea_p15", "evolution_pending_ccp",
                                   "economy_start_type:facility_a:airbase", "payment:0"})
        check(parseMark(name).name() == name, "A mark name does not round-trip: " + name);
    throwsWith<std::runtime_error>([] { parseMark("invented_mark"); }, "Unknown mark: invented_mark",
                                   "An unknown mark is not reported by name");
    rejects([] { parseMark("placed_this_turn:x"); }, "A mark without an argument took one");
    rejects([] { parseMark("naval_last_origin"); }, "A mark with an argument lost it");
    check(!findMarkKey("kmt_burma_road") && findMarkKey("in_port:x")->argument() == "x", "findMarkKey is wrong");
    // Keys order as the names do, so a set of marks lists them in name order.
    // The keys refer into `sample`, which therefore stays as it is.
    const std::vector<std::string> sample {"skeleton_crew", "skeleton_crew_until_own_turn", "naval_last_origin:sea_p15",
                                           "naval_last_origin:land_a", "naval_movement_spent", "evolution_pending_kmt",
                                           "evolution_pending_ccp", "in_port:z", "in_port:a"};
    std::vector<MarkKey> keys;
    for (const auto& name : sample) keys.push_back(parseMark(name));
    std::sort(keys.begin(), keys.end());
    auto sorted = sample;
    std::sort(sorted.begin(), sorted.end());
    for (std::size_t at = 0; at < keys.size(); ++at) check(keys[at].name() == sorted[at], "Keys do not order as names");
}

void setsOfMarksListThemInNameOrder() {
    Marks marks;
    const std::string zone = "sea_p15";
    marks[MarkKey(mark::naval_last_origin, zone)] = 2;
    marks[mark::placed_this_turn] = 1;
    marks[MarkKey(mark::economy_start_type, "facility_a:airbase")] = 1;
    marks[MarkKey(mark::economy_start_type, "facility_b:major_factory")] = 0;
    std::vector<std::string> names;
    for (const auto& [key, value] : marks) names.push_back(key.name());
    check(names == std::vector<std::string>({"economy_start_type:facility_a:airbase", "economy_start_type:facility_b:major_factory",
                                             "naval_last_origin:sea_p15", "placed_this_turn"}),
          "A set of marks does not list them in name order");
    check(marks.value(MarkKey(mark::naval_last_origin, "sea_p15")) == 2 && marks.value(mark::naval_unloaded) == 0 &&
              marks.contains(mark::placed_this_turn) && !marks.contains(mark::naval_unloaded) &&
              marks.argumentAfter(mark::economy_start_type, "facility_a:") == "airbase" &&
              !marks.argumentAfter(mark::economy_start_type, "facility_b:"),
          "Looking marks up gives the wrong answer");
    rejects([&] { marks[mark::naval_last_origin] = 1; }, "A mark with an argument was set without one");
    rejects([&] { marks[MarkKey(mark::placed_this_turn, "x")] = 1; }, "A mark without an argument was set with one");
    throwsWith<std::out_of_range>([&] { marks.at(mark::naval_unloaded); }, "Marks::at: no mark naval_unloaded",
                                  "Reading an absent mark did not throw");
    // A key read from the set itself can add a mark to it.
    const auto from = *marks.begin();
    marks[MarkKey(mark::in_port, from.first.argument())] = 3;
    check(marks.value(MarkKey(mark::in_port, "facility_a:airbase")) == 3, "A key from the set itself was mangled");
    // Copies are equal and independent; erasing many marks keeps the rest whole.
    auto copy = marks;
    check(copy == marks, "A copy differs");
    copy[mark::placed_this_turn] = 5;
    check(!(copy == marks) && marks.value(mark::placed_this_turn) == 1, "A copy shares values");
    Marks many;
    std::vector<std::string> texts;
    for (int i = 0; i < 50; ++i) texts.push_back("facility_number_" + std::to_string(i));
    for (const auto& text : texts) many[MarkKey(mark::economy_used, text)] = 1;
    for (int i = 0; i < 45; ++i) many.erase(MarkKey(mark::economy_used, texts[static_cast<std::size_t>(i)]));
    check(many.size() == 5 && many.contains(MarkKey(mark::economy_used, "facility_number_49")) &&
              many.begin()->first.argument() == "facility_number_45",
          "Erasing marks broke the others");
    for (auto it = many.begin(); it != many.end();) it = it->first.argument().ends_with("7") ? many.erase(it) : std::next(it);
    check(many.size() == 4 && !many.contains(MarkKey(mark::economy_used, "facility_number_47")), "Erasing while iterating failed");
    // Clearing forgets the erased text too: erasing after it rewrites a whole buffer.
    many.clear();
    for (const auto& text : texts) many[MarkKey(mark::economy_used, text)] = 1;
    for (int i = 0; i < 49; ++i) many.erase(MarkKey(mark::economy_used, texts[static_cast<std::size_t>(i)]));
    check(many.size() == 1 && many.begin()->first.argument() == "facility_number_49", "Erasing after clearing broke the set");
    // Commitments: a set of marks without values.
    MarkSet set {mark::combat_move, MarkKey(mark::air_battle, "land_battle_9")};
    check(set.insert(mark::retreated) && !set.insert(mark::retreated) && set.contains(MarkKey(mark::air_battle, "land_battle_9")) &&
              set.size() == 3 && set.argumentAfter(mark::air_battle) == "land_battle_9" && set.erase(mark::combat_move) == 1,
          "A set of commitments misbehaved");
}
}  // namespace

int main() {
    const std::vector<std::pair<std::string, std::function<void()>>> tests {
        {"tables number names in sorted order", tablesNumberNamesInSortedOrder},
        {"numbers have no name until a table gives them", numbersHaveNoNameUntilATableGivesThem},
        {"number maps keep name order without nodes", numberMapsKeepNameOrderWithoutNodes},
        {"number sets hold bits in name order", numberSetsHoldBitsInNameOrder},
        {"the scenario numbers its map zones", theScenarioNumbersItsMapZones},
        {"the scenario numbers its nations", theScenarioNumbersItsNations},
        {"the catalog numbers its unit types and classes", theCatalogNumbersItsUnitTypesAndClasses},
        {"marks are numbered in name order", marksAreNumberedInNameOrder},
        {"sets of marks list them in name order", setsOfMarksListThemInNameOrder},
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
