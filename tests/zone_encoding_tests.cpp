#include "game/campaign_actions.hpp"
#include "game/campaign_env.hpp"
#include "game/zone_encoding.hpp"

#include <algorithm>
#include <iostream>
#include <map>
#include <random>
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
        return item.first != id && (item.second.endpointA == western || item.second.endpointB == western);
    });
    require(other != s.rails.end(), "Manchuria Western has a second railroad");
    s.rails.at(id).damageByEndpoint[northern] = 1;
    s.rails.at(id).damageByEndpoint[western] = 1;
    s.rails.at(other->first).damageByEndpoint[western] = 1;
    const auto spec = zoneEncodingSpec(s);
    const std::vector<Action> repairs{railRepairOf(id, western), railRepairOf(other->first, western)};
    zoneEncodingUnknowns(true);
    const auto z = encodeZoneInput(s, scheduleOf(env), optionsOf(repairs));
    require(zoneEncodingUnknowns(true).empty(), "Every railroad repair detail has a column");
    const auto answers = optionAnswers(*spec, z, 0);
    for (const std::string expected :
         {"kind:economy_repair=1", "parameter:target=1", "parameter:endpoint=1", "parameter:damage=1",
          "zone:2_target:land_manchuria_western=1", "rail_zone:2_target:land_manchuria_northern=1",
          "rail_zone:2_target:land_manchuria_western=1", "rail_damage:2_target:land_manchuria_northern=1",
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
    job.owner = "japan";
    job.target = id;
    job.remainingDamage = 1;
    job.restrictsAction = false;
    job.endpoint = western;
    s.repairs.emplace(job.id, job);
    const auto row = zoneAnswers(*spec, encodeZoneInput(s, scheduleOf(env), {}), western);
    require(row.at("repair:japan:rail:count") == 1 && row.at("rail_repair_toward:land_manchuria_northern") == 1 &&
                row.at("rail_damage_toward:land_manchuria_northern") == 1,
            "The board shows which railroad is being repaired");
}

void unknownNamesAreCountedNotDropped() {
    CampaignEnv env(scenario, 1, true);
    auto s = env.engine().state().clone();
    s.units.at("setup_japan_land_jap_hokkaido_infantry_1").turnFlags["zone_test_unknown_flag"] = 1;
    zoneEncodingUnknowns(true);
    const auto spec = zoneEncodingSpec(s);
    const auto z = encodeZoneInput(s, scheduleOf(env), {});
    const auto unknown = zoneEncodingUnknowns(true);
    require(unknown.contains("actor_flag:zone_test_unknown_flag"), "Unknown flags are reported");
    require(zoneAnswers(*spec, z, "land_jap_hokkaido").at("unit_flag:axis:land:other") == 1,
            "Unknown flags still count in an other column");
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
                 {"unknown names are counted, not dropped", unknownNamesAreCountedNotDropped},
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
