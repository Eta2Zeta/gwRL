#include "game/campaign_actions.hpp"
#include "game/campaign_env.hpp"
#include "game/politics.hpp"
#include "game/zone_encoding.hpp"

#include <algorithm>
#include <iostream>
#include <map>
#include <random>
#include <set>
#include <stdexcept>

namespace {
using namespace game::campaign;
using V = game::json::Value;
using O = V::Object;
const auto scenario = std::filesystem::path(GWRL_SOURCE_DIR) / "game_content/scenarios/japan_china_1936";

void require(bool value, const std::string& message) {
    if (!value) throw std::runtime_error(message);
}

ZoneSchedule scheduleOf(const CampaignEnv& env) {
    return {env.currentDecisionPlayer(), env.decisionKind(), std::nullopt, {}, {"axis", "allies", "comintern"}};
}

std::vector<ZoneOption> optionsOf(const std::vector<Action>& actions) {
    std::vector<ZoneOption> out;
    for (const auto& action : actions) out.push_back({"play", action.player, &action});
    return out;
}

bool sameInput(const ZoneInput& a, const ZoneInput& b) {
    return a.zoneIndex == b.zoneIndex && a.zoneColumn == b.zoneColumn && a.zoneValue == b.zoneValue &&
           a.globalColumn == b.globalColumn && a.globalValue == b.globalValue && a.actionOffsets == b.actionOffsets &&
           a.actionColumn == b.actionColumn && a.actionValue == b.actionValue && a.actionSource == b.actionSource &&
           a.actionTarget == b.actionTarget && a.pathOffsets == b.pathOffsets && a.pathZone == b.pathZone &&
           a.factorGroups == b.factorGroups;
}

// Every stored answer is nonzero, in range and listed once, in sorted order.
void requireWellFormed(const ZoneEncodingSpec& spec, const ZoneInput& z, std::size_t options) {
    const auto zones = static_cast<int>(spec.zones.size());
    require(z.actionCount() == options && z.factorGroups.size() == 4 * options, "Every option is encoded once");
    // Policy groups: numbered from zero in order of first appearance, each
    // group inside one group of the level above.
    std::vector<int> above(options, 0);
    for (std::size_t level = 0; level < 4; ++level) {
        std::map<int, int> parent;
        int next = 0;
        for (std::size_t a = 0; a < options; ++a) {
            const int group = z.factorGroups[4 * a + level];
            if (!parent.contains(group)) {
                require(group == next++, "Policy groups are numbered in order of first appearance");
                parent[group] = above[a];
            }
            require(parent[group] == above[a], "Policy groups are nested");
        }
        for (std::size_t a = 0; a < options; ++a) above[a] = z.factorGroups[4 * a + level];
    }
    for (std::size_t i = 0; i < z.zoneIndex.size(); ++i) {
        require(z.zoneIndex[i] >= 0 && z.zoneIndex[i] < zones, "Zone index out of range");
        require(z.zoneColumn[i] >= 0 && z.zoneColumn[i] < spec.zoneColumns, "Zone column out of range");
        require(z.zoneValue[i] != 0, "Zero answers are not stored");
        if (i) require(std::pair(z.zoneIndex[i - 1], z.zoneColumn[i - 1]) < std::pair(z.zoneIndex[i], z.zoneColumn[i]),
                       "Zone answers are sorted and merged");
    }
    for (std::size_t i = 0; i < z.globalColumn.size(); ++i) {
        require(z.globalColumn[i] >= 0 && z.globalColumn[i] < spec.globalColumns && z.globalValue[i] != 0,
                "Position answer out of range or zero");
        if (i) require(z.globalColumn[i - 1] < z.globalColumn[i], "Position answers are sorted and merged");
    }
    require(z.actionOffsets.size() == options + 1 && z.pathOffsets.size() == options + 1, "Option offsets cover every option");
    for (std::size_t a = 0; a < options; ++a) {
        require(z.actionSource[a] >= -1 && z.actionSource[a] < zones && z.actionTarget[a] >= -1 && z.actionTarget[a] < zones,
                "Option zones out of range");
        for (auto k = z.actionOffsets[a]; k < z.actionOffsets[a + 1]; ++k) {
            const auto i = static_cast<std::size_t>(k);
            require(z.actionColumn[i] >= 0 && z.actionColumn[i] < spec.actionColumns && z.actionValue[i] != 0,
                    "Option answer out of range or zero");
            if (k > z.actionOffsets[a]) require(z.actionColumn[i - 1] < z.actionColumn[i], "Option answers are sorted and merged");
        }
        for (auto k = z.pathOffsets[a]; k < z.pathOffsets[a + 1]; ++k)
            require(z.pathZone[static_cast<std::size_t>(k)] >= 0 && z.pathZone[static_cast<std::size_t>(k)] < zones,
                    "Path zone out of range");
    }
}

std::map<std::string, int> zoneAnswers(const ZoneEncodingSpec& spec, const ZoneInput& z, const Id& zone) {
    const auto index = static_cast<int>(std::find(spec.zones.begin(), spec.zones.end(), zone) - spec.zones.begin());
    std::map<std::string, int> out;
    for (std::size_t i = 0; i < z.zoneIndex.size(); ++i)
        if (z.zoneIndex[i] == index) out[spec.zoneColumnNames[static_cast<std::size_t>(z.zoneColumn[i])]] = z.zoneValue[i];
    return out;
}

std::map<std::string, int> positionAnswers(const ZoneEncodingSpec& spec, const ZoneInput& z) {
    std::map<std::string, int> out;
    for (std::size_t i = 0; i < z.globalColumn.size(); ++i)
        out[spec.globalColumnNames[static_cast<std::size_t>(z.globalColumn[i])]] = z.globalValue[i];
    return out;
}

std::multiset<std::string> optionAnswers(const ZoneEncodingSpec& spec, const ZoneInput& z, std::size_t option) {
    std::multiset<std::string> out;
    for (auto k = z.actionOffsets[option]; k < z.actionOffsets[option + 1]; ++k)
        out.insert(spec.actionColumnNames[static_cast<std::size_t>(z.actionColumn[static_cast<std::size_t>(k)])] + "=" +
                   std::to_string(z.actionValue[static_cast<std::size_t>(k)]));
    return out;
}

void specDescribesTheFixedMap() {
    CampaignEnv env(scenario, 1, true);
    const auto spec = zoneEncodingSpec(env.engine().state());
    require(spec->zones.size() == 37 && spec->version.rfind("campaign-zone-v1-", 0) == 0, "Spec names the 37 zones");
    require(spec->zoneColumnNames.size() == static_cast<std::size_t>(spec->zoneColumns) &&
            spec->globalColumnNames.size() == static_cast<std::size_t>(spec->globalColumns) &&
            spec->actionColumnNames.size() == static_cast<std::size_t>(spec->actionColumns), "Every column has a name");
    require(spec->zoneStatic.size() == spec->zones.size() * static_cast<std::size_t>(spec->staticFeatures), "Map facts per zone");
    require(spec->edgeSource.size() == 160 && spec->edgeTarget.size() == 160 &&
            spec->edgeStatic.size() == 160 * static_cast<std::size_t>(spec->edgeFeatures), "Map facts per border");
    require(zoneEncodingSpec(env.clone().engine().state())->version == spec->version, "One layout per scenario");
}

void openingReadsAsTheBoard() {
    CampaignEnv env(scenario, 1, true);
    const auto& s = env.engine().state();
    const auto spec = zoneEncodingSpec(s);
    const auto z = encodeZoneInput(s, scheduleOf(env), {});
    const auto hokkaido = zoneAnswers(*spec, z, "land_jap_hokkaido");
    require(hokkaido.at("possessor:japan") == 1 && hokkaido.at("turn_start_possessor:japan") == 1,
            "Hokkaido is held by Japan");
    require(hokkaido.at("units:japan:infantry") == 1 && hokkaido.at("unit_stat:axis:infantry:count") == 1 &&
            hokkaido.at("unit_stat:axis:infantry:move_1") == 1, "Hokkaido holds one Japanese infantry with one move");
    require(z.bytes() < 40000, "An opening position is a few kilobytes");
}

void randomPlayStaysWellFormedAndDeterministic() {
    CampaignEnv env(scenario, 7, true);
    const auto spec = zoneEncodingSpec(env.engine().state());
    std::mt19937 rng(5);
    int encoded = 0;
    for (int step = 0; step < 400 && !env.isTerminal(); ++step) {
        if (env.decisionKind() == "chance") {
            env.resolveChance();
            continue;
        }
        const auto actions = env.legalActions();
        require(!actions.empty(), "A decision before the end has a legal action");
        const auto options = optionsOf(actions);
        const auto first = encodeZoneInput(env.engine().state(), scheduleOf(env), options);
        requireWellFormed(*spec, first, actions.size());
        require(sameInput(first, encodeZoneInput(env.engine().state(), scheduleOf(env), options)),
                "The same decision always encodes the same way");
        ++encoded;
        env.applyAction(actions[std::uniform_int_distribution<std::size_t>(0, actions.size() - 1)(rng)]);
    }
    require(encoded > 300, "Random play reached enough decisions");
}

Action moveOf(const Id& unit, const Id& from, const Id& to) {
    Action a;
    a.id = "test_move_" + unit;
    a.kind = "movement_route";
    a.player = "axis";
    a.nation = "japan";
    a.parameters = V(O{{"unit", V(unit)}, {"path", V(V::Array{V(from), V(to)})}, {"mode", V(std::string("ordinary"))},
                       {"combat", V(true)}});
    return a;
}

// Interchangeable units are counted, not named. Only their place in ID order
// tells two such options apart, because rules that build groups in ID order
// treat the first and the second differently.
void identicalUnitsDifferOnlyByRank() {
    CampaignEnv env(scenario, 1, true);
    auto s = env.engine().state().clone();
    const Id first = "setup_japan_land_manchuria_rehe_infantry_1", second = "setup_japan_land_manchuria_rehe_infantry_2";
    require(s.units.contains(first) && s.units.contains(second), "Rehe holds two Japanese infantry");
    const auto spec = zoneEncodingSpec(s);
    const std::vector<Action> moves{moveOf(first, "land_manchuria_rehe", "land_china_beiping"),
                                    moveOf(second, "land_manchuria_rehe", "land_china_beiping")};
    const auto z = encodeZoneInput(s, scheduleOf(env), optionsOf(moves));
    auto a = optionAnswers(*spec, z, 0), b = optionAnswers(*spec, z, 1);
    require(a.erase("unit_rank:0_source:0=1") == 1 && b.erase("unit_rank:0_source:1=1") == 1, "Ranks follow ID order");
    // The first may still be joined by the second, not the other way round.
    const auto peers = [](const std::multiset<std::string>& answers) {
        return std::count_if(answers.begin(), answers.end(), [](const std::string& x) {
            return x.rfind("unit_later_peers:0_source:infantry=", 0) == 0;
        });
    };
    require(peers(a) == 1 && peers(b) == 0, "Later units of the same owner are counted");
    std::erase_if(a, [](const std::string& x) { return x.rfind("unit_later_peers:", 0) == 0; });
    std::erase_if(b, [](const std::string& x) { return x.rfind("unit_later_peers:", 0) == 0; });
    require(a == b && z.actionSource[0] == z.actionSource[1] && z.actionTarget[0] == z.actionTarget[1],
            "Identical units' options differ only by their place in ID order");
    // A unit that has moved is no longer interchangeable with one that has not.
    s.units.at(first).movementRemaining = 0;
    const auto moved = encodeZoneInput(s, scheduleOf(env), optionsOf(moves));
    a = optionAnswers(*spec, moved, 0);
    b = optionAnswers(*spec, moved, 1);
    require(a.contains("unit_rank:0_source:0=1") && b.contains("unit_rank:0_source:0=1") &&
            a.contains("unit_stat:0_source:move_0=1") && b.contains("unit_stat:0_source:move_1=1"),
            "Different units each rank first among their own kind");
    const auto rehe = zoneAnswers(*spec, moved, "land_manchuria_rehe");
    require(rehe.at("unit_stat:axis:infantry:move_0") == 1 && rehe.at("unit_stat:axis:infantry:move_1") == 1,
            "The zone counts each movement state");
}

Action railRepairOf(const Id& rail, const Id& side) {
    Action a;
    a.id = "test_repair_" + rail + "_" + side;
    a.kind = "economy_repair";
    a.player = "axis";
    a.nation = "japan";
    a.parameters = V(O{{"target", V(rail)}, {"endpoint", V(side)}, {"damage", V(1.0)}});
    return a;
}

int zoneNumber(const ZoneEncodingSpec& spec, const Id& zone) {
    return static_cast<int>(std::find(spec.zones.begin(), spec.zones.end(), zone) - spec.zones.begin());
}

// A railroad repair names the railroad by its border: both zones as what the
// repair acts on, the damage on each side, the side being repaired and the
// amount. Two railroads that meet at one zone therefore stay apart.
void railroadRepairNamesItsBorder() {
    CampaignEnv env(scenario, 1, true);
    auto s = env.engine().state().clone();
    const Id northern = "land_manchuria_northern", western = "land_manchuria_western";
    const auto id = railroadId(northern, western);
    require(s.rails.contains(id), "Manchuria Northern and Western share a railroad");
    const auto other = std::find_if(s.rails.begin(), s.rails.end(), [&](const auto& item) {
        return item.first != id && (item.second.endpointA == zoneNumber(s, western) || item.second.endpointB == zoneNumber(s, western));
    });
    require(other != s.rails.end(), "Manchuria Western has a second railroad");
    s.rails.at(id).damageByEndpoint[zoneNumber(s, northern)] = 1;
    s.rails.at(id).damageByEndpoint[zoneNumber(s, western)] = 1;
    s.rails.at(other->first).damageByEndpoint[zoneNumber(s, western)] = 1;
    const auto spec = zoneEncodingSpec(s);
    const std::vector<Action> repairs{railRepairOf(id, western), railRepairOf(other->first, western)};
    zoneEncodingUnknowns(true);
    const auto z = encodeZoneInput(s, scheduleOf(env), optionsOf(repairs));
    require(zoneEncodingUnknowns(true).empty(), "Every railroad repair detail has a column");
    const auto answers = optionAnswers(*spec, z, 0);
    for (const std::string expected :
         {"kind:economy_repair=1", "parameter:target=1", "parameter:endpoint=1", "parameter:damage=1",
          "zone:2_target:land_manchuria_western=1", "rail_endpoint:2_target:land_manchuria_northern=1",
          "rail_endpoint:2_target:land_manchuria_western=1", "rail_damage:2_target:land_manchuria_northern=1",
          "rail_damage:2_target:land_manchuria_western=1", "number:damage=1"})
        require(answers.contains(expected), "Railroad repair answers " + expected);
    require(std::none_of(answers.begin(), answers.end(),
                         [](const std::string& x) {
                             return x.rfind("value:", 0) == 0 || x.find(":3_other:") != std::string::npos ||
                                    x.rfind("number:other", 0) == 0 || x.rfind("parameter:other", 0) == 0;
                         }),
            "Nothing in a railroad repair is filed as unknown");
    require(z.actionTarget[0] == zoneNumber(*spec, western) && z.actionTarget[1] == zoneNumber(*spec, western),
            "A railroad repair acts on the side being repaired");
    require(z.factorGroups[4 * 0 + 3] != z.factorGroups[4 * 1 + 3],
            "Repairs of two railroads at one zone differ in what they act on");

    // A repair under way shows on the repaired side's row, toward the zone across.
    RepairJob job;
    job.id = "repair_" + id + "_" + western;
    job.owner = nationNumber(s, "japan");
    job.target = id;
    job.remainingDamage = 1;
    job.restrictsAction = false;
    job.endpoint = zoneNumber(s, western);
    s.repairs.emplace(job.id, job);
    const auto row = zoneAnswers(*spec, encodeZoneInput(s, scheduleOf(env), {}), western);
    require(row.at("repair:japan:rail:count") == 1 && row.at("rail_repair_toward:land_manchuria_northern") == 1 &&
                row.at("rail_damage_toward:land_manchuria_northern") == 1,
            "The board shows which railroad is being repaired");
}

void marksAreAskedWhereTheRulesPutThem() {
    CampaignEnv env(scenario, 1, true);
    auto s = env.engine().state().clone();
    const auto spec = zoneEncodingSpec(s);
    const std::set<std::string> zone(spec->zoneColumnNames.begin(), spec->zoneColumnNames.end());
    const std::set<std::string> global(spec->globalColumnNames.begin(), spec->globalColumnNames.end());
    const std::set<std::string> action(spec->actionColumnNames.begin(), spec->actionColumnNames.end());
    // The mark table says which kinds of thing each mark is on.
    require(markOn(mark::scrambled, MarkPlace::unit) && !markOn(mark::scrambled, MarkPlace::nation) &&
                markOn(mark::bombing_reduction, MarkPlace::nation) && markOn(mark::border, MarkPlace::facility) &&
                markOn(mark::border, MarkPlace::project) && !markOn(mark::escort, MarkPlace::unit),
            "The mark table names the kinds of thing a mark is on");
    require(global.contains("nation_flag:japan:bombing_reduction") && global.contains("nation_flag:japan:city_bombing_reduction") &&
                zone.contains("nation_flag_here:japan:city_bombing_reduction_turn") &&
                !global.contains("nation_flag:japan:scrambled") && !global.contains("nation_flag:japan:economy_researched_round") &&
                !zone.contains("nation_flag_here:japan:surprise_attack_target") && global.contains("state_flag:crossing_used") &&
                !global.contains("state_flag:moved_this_turn") && !global.contains("state_flag:land_battle_sequence") &&
                !global.contains("state_flag:__campaign_started") && zone.contains("battle_flag:attack_rolled") &&
                !zone.contains("battle_flag:city_damage") && zone.contains("territory_flag:city_damage") &&
                !zone.contains("territory_flag:last_possession_change_turn") && zone.contains("unit_flag:axis:naval:repairing") &&
                !zone.contains("unit_flag:axis:land:combat_move") && !zone.contains("unit_flag:axis:land:escort") &&
                action.contains("unit_cargo_flag:0_source:combat_move") && !action.contains("unit_cargo_flag:0_source:completed"),
            "A mark is asked about only on the kinds of thing the rules put it on");
    // The bombing reductions a nation has used are read, also at the place they were used.
    const auto japan = nationNumber(s, "japan");
    s.nations.at(japan).turnFlags[MarkKey(mark::city_bombing_reduction, "land_jap_tokyo")] = 5;
    // A mark where the rules never put it counts in its family's shared column and is reported.
    s.units.at("setup_japan_land_jap_hokkaido_infantry_1").turnFlags[MarkKey(mark::bombing_reduction, "x")] = 1;
    zoneEncodingUnknowns(true);
    const auto z = encodeZoneInput(s, scheduleOf(env), {});
    const auto unknown = zoneEncodingUnknowns(true);
    require(positionAnswers(*spec, z).at("nation_flag:japan:city_bombing_reduction") == 5 &&
                zoneAnswers(*spec, z, "land_jap_tokyo").at("nation_flag_here:japan:city_bombing_reduction") == 5,
            "A bombing reduction is read on the nation and at the city");
    require(unknown.size() == 1 && unknown.contains("impossible_unit_flag:axis:land:bombing_reduction"),
            "A mark on a kind of thing the rules never put it on is reported");
    require(zoneAnswers(*spec, z, "land_jap_hokkaido").at("unit_flag:~impossible") == 1,
            "A mark on a kind of thing the rules never put it on still counts");
}

// Only Japan, the KMT and the CCP keep an income account, and only Japan has
// the bonus for Chinese land, so only those four questions exist. Any other
// nation and part share one column and are reported, and so is a nation whose
// income was never worked out, which the position has no question for.
void incomeQuestionsFollowTheRules() {
    CampaignEnv env(scenario, 1, true);
    auto s = env.engine().state().clone();
    const auto spec = zoneEncodingSpec(s);
    std::set<std::string> questions;
    for (const auto& name : spec->globalColumnNames)
        if (name.rfind("income", 0) == 0) questions.insert(name);
    require(questions == std::set<std::string>{"income:ccp:territorial", "income:japan:china_control_bonus",
                                               "income:japan:territorial", "income:kmt:territorial",
                                               "income:~impossible", "income_collected"},
            "Income questions exist only for the parts a nation can have");
    zoneEncodingUnknowns(true);
    auto answers = positionAnswers(*spec, encodeZoneInput(s, scheduleOf(env), {}));
    require(answers.at("income:japan:territorial") == 15 && answers.at("income:kmt:territorial") == 6 &&
                answers.at("income:ccp:territorial") == 2 && !answers.contains("income:~impossible") &&
                zoneEncodingUnknowns(true).empty(),
            "The opening's incomes are read and nothing is reported");
    s.nations.at(nationNumber(s, "mongolia")).incomeComponents["territorial"] = 2;
    s.nations.at(nationNumber(s, "kmt")).incomeComponents["zone_test_income"] = 1;
    s.nations.at(nationNumber(s, "japan")).incomeKnown = false;
    answers = positionAnswers(*spec, encodeZoneInput(s, scheduleOf(env), {}));
    const auto unknown = zoneEncodingUnknowns(true);
    require(answers.at("income:~impossible") == 3, "A ruled-out income still counts, in one shared column");
    require(unknown.contains("impossible_income:mongolia:territorial") && unknown.contains("impossible_income:kmt:other") &&
                unknown.contains("income_component:zone_test_income") && unknown.contains("income_not_evaluated:japan"),
            "A ruled-out or unevaluated income is reported");
}

std::set<std::string> questionsOf(const ZoneEncodingSpec& spec, const std::string& family) {
    std::set<std::string> out;
    for (const auto& name : spec.globalColumnNames)
        if (name == family || name.rfind(family + ":", 0) == 0) out.insert(name);
    return out;
}

// The position asks about a nation only what the rules can make of it (the
// rules in politics.hpp and economy.hpp). An answer they allow, however rare,
// has its own question; one they rule out is counted in its family's shared
// column and reported.
void nationQuestionsFollowTheRules() {
    CampaignEnv env(scenario, 1, true);
    const auto spec = zoneEncodingSpec(env.engine().state());
    const auto impossible = [](const std::string& family) { return family + ":~impossible"; };
    require(questionsOf(*spec, "treasury") ==
                std::set<std::string>{"treasury:ccp", "treasury:japan", "treasury:kmt", "treasury:~impossible"} &&
                questionsOf(*spec, "has_treasury").empty(),
            "Only the three nations that keep an account have a treasury question");
    require(questionsOf(*spec, "turn_nation") ==
                std::set<std::string>{"turn_nation:ccp", "turn_nation:japan", "turn_nation:kmt", "turn_nation:mongolia",
                                      "turn_nation:~impossible"} &&
                questionsOf(*spec, "completed_turns").size() == 5,
            "Only the nations of the turn order take turns");
    // A nation in every game with one possible value of a fact always has it,
    // so the position does not ask: Japan's, the KMT's, the CCP's and Mongolia's
    // alliance and controller, and Japan's, Mongolia's and the warlords' status.
    std::set<std::string> statuses{"power_status:ccp:major", "power_status:ccp:minor", "power_status:dadao:minor",
                                   "power_status:kmt:major", "power_status:kmt:minor", "power_status:~impossible"};
    std::set<std::string> sides{"alliance:dadao:axis", "alliance:~impossible"};
    std::set<std::string> controllers{"controller:dadao:japan", "controller:dadao:~none", "controller:~impossible"};
    std::set<std::string> attacks{"attacked_warlord:~impossible"}, queue{"alignment_queue:~impossible"};
    int warlords = 0;
    for (const auto& nation : spec->nations) {
        if (!isWarlord(nation)) continue;
        ++warlords;
        for (const std::string side : {"allies", "axis", "comintern", "~none"}) sides.insert("alliance:" + nation + ":" + side);
        for (const std::string by : {"ccp", "dadao", "japan", "kmt", "~none"}) controllers.insert("controller:" + nation + ":" + by);
        for (const std::string by : {"ccp", "dadao", "japan", "mongolia"})
            attacks.insert("attacked_warlord:" + nation + ":" + by);
        queue.insert("alignment_queue:" + nation);
    }
    require(warlords == 8 && questionsOf(*spec, "power_status") == statuses && questionsOf(*spec, "alliance") == sides &&
                questionsOf(*spec, "player").empty() && questionsOf(*spec, "controller") == controllers &&
                questionsOf(*spec, "nation_present") == std::set<std::string>{"nation_present:dadao"},
            "A nation's status, alliance and controller questions are the ones whose answer can change");
    require(questionsOf(*spec, "attacked_warlord") == attacks && questionsOf(*spec, "alignment_queue") == queue,
            "Only warlords are attacked as warlords or wait to be aligned");
    require(questionsOf(*spec, "allied") == std::set<std::string>{"allied:ccp:kmt", "allied:kmt:ccp", "allied:~impossible"} &&
                questionsOf(*spec, "surrendered") ==
                    std::set<std::string>{"surrendered:japan", "surrendered:kmt", "surrendered:~impossible"} &&
                questionsOf(*spec, "evolution_awarded") ==
                    std::set<std::string>{"evolution_awarded:ccp", "evolution_awarded:kmt", "evolution_awarded:~impossible"} &&
                questionsOf(*spec, "china_invader") ==
                    std::set<std::string>{"china_invader:japan", "china_invader:mongolia", "china_invader:~impossible"} &&
                questionsOf(*spec, "state_flag_nation") ==
                    std::set<std::string>{"state_flag_nation:evolution_pending:ccp", "state_flag_nation:evolution_pending:kmt",
                                          "state_flag_nation:~impossible"},
            "Allies, surrender, evolution and invasion are asked of the nations they can happen to");
    const auto technologies = spec->technologies.size();
    require(questionsOf(*spec, "technology_stage").size() == 3 * technologies + 1 &&
                questionsOf(*spec, "researched_round").size() == 3 * technologies + 1 &&
                spec->globalColumnNames.end() != std::find(spec->globalColumnNames.begin(), spec->globalColumnNames.end(),
                                                           "technology_stage:ccp:radar") &&
                !questionsOf(*spec, "technology_stage").contains("technology_stage:mongolia:radar") &&
                !questionsOf(*spec, "technology_stage").contains("technology_stage:japan:other"),
            "Only nations that can become major powers have technology questions");
    const auto wars = questionsOf(*spec, "at_war");
    // Of the 13 x 13 ordered pairs, none of a nation with itself or of two
    // warlords; none of Japan with Dadao, the KMT with the CCP or the CCP with
    // Mongolia, either way round; none of a warlord with the KMT; and one
    // shared ~impossible question.
    require(wars.size() == 13 * 13 - 13 - 8 * 7 - 2 * 3 - 2 * 8 + 1 && wars.contains("at_war:kmt:mongolia") &&
                wars.contains("at_war:mongolia:japan") && wars.contains("at_war:ccp:warlord_tibet") &&
                wars.contains("at_war:dadao:warlord_tibet") && !wars.contains("at_war:kmt:ccp") &&
                !wars.contains("at_war:ccp:kmt") && !wars.contains("at_war:japan:japan") &&
                !wars.contains("at_war:japan:dadao") && !wars.contains("at_war:warlord_tibet:warlord_yunnan") &&
                !wars.contains("at_war:ccp:mongolia") && wars.contains("at_war:mongolia:dadao") &&
                wars.contains("at_war:mongolia:warlord_tibet") && !wars.contains("at_war:kmt:warlord_tibet") &&
                !wars.contains("at_war:warlord_tibet:kmt"),
            "No nation fights itself, a warlord fights only Japan, the CCP, Dadao and Mongolia, Mongolia never the "
            "CCP, Japan never Dadao, and the KMT and the CCP always fight");

    // The opening answers only kept questions.
    auto s = env.engine().state().clone();
    zoneEncodingUnknowns(true);
    auto answers = positionAnswers(*spec, encodeZoneInput(s, scheduleOf(env), {}));
    require(zoneEncodingUnknowns(true).empty(), "The opening answers no ruled-out question");
    for (const std::string expected :
         {"treasury:japan", "power_status:kmt:minor", "controller:warlord_tibet:~none", "alliance:warlord_tibet:~none",
          "turn_nation:ccp"})
        require(answers.contains(expected), "The opening answers " + expected);
    require(answers.at("treasury:japan") == 15 && !answers.contains("completed_turns:ccp"), "The opening's values are read");

    // Rare answers the rules allow have their own questions.
    ensureDadao(s);
    auto& tibet = s.nations.at(nationNumber(s, "warlord_tibet"));
    tibet.controllerNation = nationNumber(s, "japan");
    tibet.player = tibet.alliance = "axis";
    s.nations.at(nationNumber(s, "ccp")).powerStatus = "major";
    s.nations.at(nationNumber(s, "ccp")).technologyStages[technologyNumber(s, "radar")] = 1;
    s.nations.at(nationNumber(s, "ccp")).gameFlags[MarkKey(mark::economy_researched_round, "radar")] = 1;
    s.nations.at(nationNumber(s, "kmt")).atWarWith.insert(nationNumber(s, "mongolia"));
    s.nations.at(nationNumber(s, "ccp")).allies.insert(nationNumber(s, "kmt"));
    s.nations.at(nationNumber(s, "dadao")).atWarWith.insert(nationNumber(s, "warlord_yunnan"));
    s.politics.surrendered.insert(nationNumber(s, "kmt"));
    s.politics.evolutionAwarded.insert(nationNumber(s, "ccp"));
    s.politics.chinaInvader = nationNumber(s, "japan");
    s.politics.attackedWarlords[nationNumber(s, "warlord_yunnan")].insert(nationNumber(s, "dadao"));
    s.politics.alignmentQueue.push_back(nationNumber(s, "warlord_yunnan"));
    s.flags[MarkKey(mark::evolution_pending, "ccp")] = 1;
    answers = positionAnswers(*spec, encodeZoneInput(s, scheduleOf(env), {}));
    require(zoneEncodingUnknowns(true).empty(), "Rare answers the rules allow are not reported");
    for (const std::string expected :
         {"nation_present:dadao", "power_status:dadao:minor", "alliance:dadao:axis", "controller:dadao:japan",
          "controller:warlord_tibet:japan", "alliance:warlord_tibet:axis", "power_status:ccp:major", "technology_stage:ccp:radar", "researched_round:ccp:radar",
          "at_war:kmt:mongolia", "allied:ccp:kmt", "at_war:dadao:warlord_yunnan", "surrendered:kmt", "evolution_awarded:ccp",
          "china_invader:japan", "attacked_warlord:warlord_yunnan:dadao", "alignment_queue:warlord_yunnan",
          "state_flag_nation:evolution_pending:ccp"})
        require(answers.contains(expected), "A rare answer has its question: " + expected);

    // An answer the rules rule out is counted in its family's shared column and reported.
    auto broken = env.engine().state().clone();
    ensureDadao(broken);
    auto& mongolia = broken.nations.at(nationNumber(broken, "mongolia"));
    mongolia.treasury = 3;
    mongolia.alliance = mongolia.player = "axis";
    mongolia.controllerNation = nationNumber(s, "japan");
    mongolia.powerStatus = "major";
    auto& kmt = broken.nations.at(nationNumber(broken, "kmt"));
    kmt.player = "axis";
    kmt.powerStatus = "warlord";
    kmt.atWarWith.erase(nationNumber(broken, "ccp"));
    broken.nations.at(nationNumber(broken, "dadao")).alliance = broken.nations.at(nationNumber(broken, "dadao")).player = "allies";
    broken.nations.at(nationNumber(broken, "warlord_tibet")).controllerNation = nationNumber(broken, "mongolia");
    broken.flags.erase(MarkKey(mark::campaign_started));
    mongolia.technologyStages[technologyNumber(s, "radar")] = 2;
    mongolia.gameFlags[MarkKey(mark::economy_researched_round, "radar")] = 1;
    mongolia.allies.insert(nationNumber(s, "ccp"));
    broken.nations.at(nationNumber(broken, "japan")).treasury.reset();
    broken.nations.at(nationNumber(broken, "warlord_tibet")).atWarWith.insert(nationNumber(broken, "warlord_yunnan"));
    kmt.atWarWith.insert(nationNumber(broken, "warlord_yunnan"));
    mongolia.atWarWith.insert(nationNumber(broken, "ccp"));
    broken.completedTurns[nationNumber(broken, "dadao")] = 1;
    broken.politics.surrendered.insert(nationNumber(broken, "ccp"));
    broken.politics.evolutionAwarded.insert(nationNumber(broken, "japan"));
    broken.politics.chinaInvader = nationNumber(broken, "kmt");
    broken.politics.attackedWarlords[nationNumber(broken, "warlord_tibet")].insert(nationNumber(broken, "kmt"));
    broken.politics.alignmentQueue.push_back(nationNumber(broken, "japan"));
    broken.flags[MarkKey(mark::evolution_pending, "japan")] = 1;
    answers = positionAnswers(*spec, encodeZoneInput(broken, scheduleOf(env), {}));
    const auto unknown = zoneEncodingUnknowns(true);
    for (const std::string family :
         {"treasury", "alliance", "controller", "power_status", "technology_stage", "researched_round", "allied",
          "at_war", "completed_turns", "surrendered", "evolution_awarded", "china_invader", "attacked_warlord",
          "alignment_queue", "state_flag_nation"})
        require(answers.contains(impossible(family)), "A ruled-out answer still counts: " + family);
    require(answers.at("treasury:~impossible") == 3, "A ruled-out treasury keeps its amount");
    for (const std::string report :
         {"impossible_treasury:mongolia", "treasury_missing:japan", "impossible_alliance:dadao:allies",
          "alliance_changed:mongolia", "player_not_alliance:kmt", "impossible_controller:warlord_tibet:mongolia",
          "controller_changed:mongolia", "impossible_power_status:kmt:warlord", "power_status_changed:mongolia",
          "war_ended:kmt:ccp", "campaign_not_started:state",
          "impossible_technology_stage:mongolia:radar", "impossible_researched_round:mongolia:radar",
          "impossible_allied:mongolia:ccp", "impossible_at_war:warlord_tibet:warlord_yunnan",
          "impossible_at_war:kmt:warlord_yunnan", "impossible_at_war:mongolia:ccp",
          "impossible_completed_turns:dadao", "impossible_surrendered:ccp", "impossible_evolution_awarded:japan",
          "impossible_china_invader:kmt", "impossible_attacked_warlord:warlord_tibet:kmt",
          "impossible_alignment_queue:japan", "impossible_state_flag_nation:evolution_pending:japan"})
        require(unknown.contains(report), "A ruled-out answer is reported: " + report);
    require(!answers.contains("treasury:japan"), "A missing treasury is reported, not read as empty");
}

// A battle's notes keep their words: its steps, situation, result, the classes
// a hit may take and the nations and players named. A unit lost earlier this
// turn is skipped; a new word is counted in an "other" column and reported.
void battleNotesKeepTheirWords() {
    CampaignEnv env(scenario, 1, true);
    auto s = env.engine().state().clone();
    const Id zone = "land_china_beiping", victim = "setup_warlord_beiping_hopeh_land_china_beiping_infantry_1";
    require(s.units.contains(victim), "Beiping holds a warlord infantry");
    const Id lost = "setup_zone_test_lost_unit";
    s.turnStart.units.emplace(lost, std::pair{nationNumber(s, "kmt"), zoneNumber(s, zone)});
    BattleState battle;
    battle.id = "land_battle_test";
    battle.zone = zoneNumber(s, zone);
    battle.attacker = nationNumber(s, "japan");
    battle.defender = nationNumber(s, "warlord_beiping_hopeh");
    battle.stage = "choose_hits";
    battle.data = V(O{
        {"rolling_phase", V(std::string("defender_fire"))},
        {"after_hits", V(std::string("round_end"))},
        {"result", V(std::string("attacker_wins"))},
        {"context", V(std::string("port_attack"))},
        {"hits", V(V::Array{V(O{{"eligible", V(V::Array{V(victim)})},
                                {"firing_nation", V(std::string("kmt"))},
                                {"target_classes", V(V::Array{V(std::string("vehicle_class"))})},
                                {"victim_attacker", V(false)}})})},
        {"casualty_consents", V(O{{"axis", V(true)}})},
        {"truce_breaker", V(std::string("kmt"))},
        {"map_attack", V(true)},
        {"defenders", V(V::Array{V(lost)})}});
    s.battles.emplace(battle.id, battle);
    s.nations.at(nationNumber(s, "japan")).turnFlags[MarkKey(mark::surprise_attack_linked_land, zone)] = 1;
    const auto spec = zoneEncodingSpec(s);
    zoneEncodingUnknowns(true);
    auto row = zoneAnswers(*spec, encodeZoneInput(s, scheduleOf(env), {}), zone);
    require(zoneEncodingUnknowns(true).empty(), "Every battle note and word has a column");
    for (const std::string expected :
         {"battle_data_word:rolling_phase:defender_fire", "battle_data_word:after_hits:round_end",
          "battle_data_word:result:attacker_wins", "battle_data_word:context:port_attack", "battle_data_word:hits:kmt",
          "battle_data_word:hits:vehicle_class", "battle_data_word:casualty_consents:axis",
          "battle_data_word:truce_breaker:kmt", "battle_data_unit:hits:infantry",
          "nation_flag_here:japan:surprise_attack_linked_land"})
        require(row.contains(expected) && row.at(expected) == 1, "Battle note answers " + expected);
    require(row.at("battle_data:map_attack") == 2, "A note that is true counts once for being there and once for true");

    // An unlisted word, and a word in a note that holds no words, still count and are reported.
    auto& data = s.battles.at(battle.id).data;
    auto notes = data.asObject();
    notes["context"] = V(std::string("zone_test_word"));
    notes["cursor"] = V(std::string("standard"));
    data = V(std::move(notes));
    row = zoneAnswers(*spec, encodeZoneInput(s, scheduleOf(env), {}), zone);
    const auto unknown = zoneEncodingUnknowns(true);
    require(unknown.contains("battle_word:zone_test_word") && unknown.contains("battle_word_note:cursor"),
            "New words and word-holding notes are reported");
    require(row.at("battle_data_word:context:other") == 1 && row.at("battle_data_word:other:standard") == 1,
            "New words still count in other columns");
}

// Repairs of cities and construction projects show at their zones, and rare
// values of a move's details have their own questions.
void repairsAndRareValuesHaveColumns() {
    CampaignEnv env(scenario, 1, true);
    auto s = env.engine().state().clone();
    s.repairs.emplace("repair_land_china_beiping",
                      RepairJob{"repair_land_china_beiping", nationNumber(s, "ccp"), "land_china_beiping", 3, 0, false, std::nullopt});
    s.construction.emplace("economy_airbase_1", BuildProject{"economy_airbase_1", nationNumber(s, "japan"), buildTypeNumber(s, "airbase"),
                                                             std::optional<Id>("land_formosa"), 1, 2, {2}, {{mark::damage, 1}}});
    s.repairs.emplace("repair_economy_airbase_1",
                      RepairJob{"repair_economy_airbase_1", nationNumber(s, "japan"), "economy_airbase_1", 1, 0, false, std::nullopt});
    const auto spec = zoneEncodingSpec(s);
    Action intercept;
    intercept.id = "test_intercept";
    intercept.kind = "air_intercept";
    intercept.player = "axis";
    intercept.nation = "japan";
    intercept.parameters = V(O{{"source", V(std::string("local"))}});
    Action purchase = intercept;
    purchase.id = "test_purchase";
    purchase.kind = "economy_purchase";
    purchase.parameters = V(O{{"row", V(std::string("japan_major_airbase"))},
                              {"price", V(std::string("improved_construction_discount"))}});
    Action combined = purchase;
    combined.id = "test_purchase_combined";
    combined.parameters = V(O{{"row", V(std::string("japan_major_airbase"))},
                              {"price", V(std::string("improved_construction_combine"))}});
    const std::vector<Action> moves{intercept, purchase, combined};
    zoneEncodingUnknowns(true);
    const auto z = encodeZoneInput(s, scheduleOf(env), optionsOf(moves));
    require(zoneEncodingUnknowns(true).empty(), "Repairs and rare values have columns");
    const auto beiping = zoneAnswers(*spec, z, "land_china_beiping");
    require(beiping.at("repair:ccp:city:count") == 1 && beiping.at("repair:ccp:city:remaining_damage") == 3,
            "A city repair under way shows at the city");
    require(zoneAnswers(*spec, z, "land_formosa").at("repair:japan:construction:count") == 1,
            "A construction repair under way shows at its site");
    require(optionAnswers(*spec, z, 0).contains("value:source:local=1"), "An interception from the zone itself");
    require(optionAnswers(*spec, z, 1).contains("value:price:improved_construction_discount=1") &&
                optionAnswers(*spec, z, 2).contains("value:price:improved_construction_combine=1") &&
                optionAnswers(*spec, z, 1) != optionAnswers(*spec, z, 2),
            "The two Improved Construction prices are told apart");
}

void schedulingStateIsPartOfThePosition() {
    CampaignEnv env(scenario, 1, true);
    const auto& s = env.engine().state();
    auto plain = scheduleOf(env);
    auto offered = plain;
    offered.decisionKind = "declaration_offer";
    offered.offered = "axis";
    offered.passed = {"allies"};
    require(!sameInput(encodeZoneInput(s, plain, {}), encodeZoneInput(s, offered, {})),
            "An interrupt offer changes the encoded position");
}
}  // namespace

int main() {
    try {
        for (const auto& [name, test] : std::vector<std::pair<std::string, void (*)()>>{
                 {"spec describes the fixed map", specDescribesTheFixedMap},
                 {"opening reads as the board", openingReadsAsTheBoard},
                 {"random play stays well formed and deterministic", randomPlayStaysWellFormedAndDeterministic},
                 {"identical units differ only by rank", identicalUnitsDifferOnlyByRank},
                 {"a railroad repair names its border", railroadRepairNamesItsBorder},
                 {"marks are asked where the rules put them", marksAreAskedWhereTheRulesPutThem},
                 {"income questions follow the rules", incomeQuestionsFollowTheRules},
                 {"nation questions follow the rules", nationQuestionsFollowTheRules},
                 {"battle notes keep their words", battleNotesKeepTheirWords},
                 {"repairs and rare values have columns", repairsAndRareValuesHaveColumns},
                 {"scheduling state is part of the position", schedulingStateIsPartOfThePosition}}) {
            test();
            std::cout << "PASS " << name << '\n';
        }
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
    return 0;
}
