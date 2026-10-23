#include "game/air.hpp"
#include "game/economy.hpp"
#include "game/land_combat.hpp"
#include "game/movement.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <cmath>
#include <functional>
#include <iostream>
#include <stdexcept>

namespace {
using namespace game::campaign;
using V = game::json::Value;
using O = V::Object;
using A = V::Array;
const auto root = std::filesystem::path(GWRL_SOURCE_DIR);
const Id hopeh = "land_china_hopeh", beiping = "land_china_beiping", shantung = "land_china_shantung",
         nanking = "land_china_nanking", shensi = "land_china_shensi";
void check(bool x, const std::string &m) {
    if (!x)
        throw std::runtime_error(m);
}
void rejects(const std::function<void()> &f, const std::string &m) {
    try {
        f();
    } catch (const std::exception &) {
        return;
    }
    throw std::runtime_error(m);
}
bool flag(const std::map<Id, int> &x, const Id &k) {
    auto i = x.find(k);
    return i != x.end() && i->second;
}
State fixture(const Id &actor = "japan") {
    static auto base = loadScenario(root / "game_content/scenarios/japan_china_1936");
    auto s = base.clone();
    s.units.clear();
    s.facilities.clear();
    s.construction.clear();
    s.repairs.clear();
    s.decisions.clear();
    s.chance.reset();
    auto i = std::find(s.definition->turnOrder.begin(), s.definition->turnOrder.end(), actor);
    s.clock.nationIndex = static_cast<int>(i - s.definition->turnOrder.begin());
    s.clock.playerTurnSerial = s.clock.nationIndex;
    s.clock.phase = Phase::Combat;
    for (std::size_t k = 0; k < s.definition->turnOrder.size(); ++k)
        s.completedTurns[s.definition->turnOrder[k]] =
            k < static_cast<std::size_t>(s.clock.nationIndex) ? 1 : 0;
    s.nations.at("japan").atWarWith.insert("kmt");
    s.nations.at("kmt").atWarWith.insert("japan");
    s.territories.at(hopeh).possessor = "kmt";
    s.territories.at(beiping).possessor = "japan";
    s.territories.at(shantung).possessor = "japan";
    s.captureTurnStart();
    return s;
}
void add(State &s, const Id &id, const Id &nation, const Id &zone, const Id &type = "infantry") {
    UnitState u;
    u.id = id;
    u.owner = nation;
    u.zone = u.turnOrigin = zone;
    u.type = type;
    u.movementAllowance = u.movementRemaining =
        s.definition->catalog->stats(type, 0, catalogContext(s, nation, zone)).movement;
    s.units.emplace(id, u);
}
Action select(
    const std::vector<Action> &v, const Id &kind,
    const std::function<bool(const Action &)> &match = [](const Action &) { return true; }) {
    for (const auto &a : v)
        if (a.kind == kind && match(a))
            return a;
    throw std::runtime_error("Missing action " + kind);
}
Id battle(State &s, std::vector<Id> a = {"a"}, std::map<Id, Id> origins = {{"a", beiping}}, Id zone = hopeh,
          Id nation = "japan") {
    return registerLandBattle(s, zone, nation, a, origins);
}
void begin(Engine &e) {
    e.step(select(e.legalActions(), "land_begin_battle"));
}
void choose(Engine &e, const Id &kind, const Id &unit = {}) {
    e.step(select(e.legalActions(), kind, [&](const Action &a) {
        const auto *u = a.parameters.find("unit");
        return unit.empty() || (u && u->asString() == unit);
    }));
}
void drain(Engine &e, int maximum = 200) {
    for (int k = 0; k < maximum; ++k) {
        if (e.state().chance) {
            e.resolveChance();
            continue;
        }
        bool finished = true;
        for (const auto &[id, b] : e.state().battles)
            if (!flag(b.flags, "finished"))
                finished = false;
        if (finished)
            return;
        const auto a = e.legalActions();
        check(!a.empty(), "Battle stuck without action");
        e.step(a.front());
    }
    throw std::runtime_error("Battle did not terminate");
}
std::shared_ptr<const Rules> rules() {
    return std::make_shared<PoliticsRules>(std::make_shared<LandCombatRules>(std::make_shared<AirRules>()));
}
void editNode(State &s, const Id &zone, const std::function<void(O &)> &f) {
    auto d = *s.definition;
    auto geo = d.geography.asObject();
    auto nodes = geo.at("nodes").asObject();
    auto n = nodes.at(zone).asObject();
    f(n);
    nodes[zone] = V(n);
    geo["nodes"] = V(nodes);
    d.geography = V(geo);
    s.definition = freezeDefinition(std::move(d));
}
void clearTerrain(State &s, const Id &zone) {
    editNode(s, zone, [](O &n) {
        n["terrain"] = V(std::string("normal"));
        n["is_city"] = V(false);
        auto edges = n.at("neighbors").asArray();
        for (auto &e : edges) {
            auto v = e.asObject();
            v["border_terrain"] = V(nullptr);
            v["river_crossing"] = V(false);
            e = V(v);
        }
        n["neighbors"] = V(edges);
    });
}
void simultaneousFireAndReplay() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    add(s, "a", "japan", hopeh);
    add(s, "d", "kmt", hopeh);
    auto b = battle(s);
    Engine e(s, rules(), 7);
    e.setDiceTapeForTesting({1, 1});
    const auto initial = e.serialize();
    begin(e);
    check(e.state().chance.has_value(), "Attacker ordinary roll absent");
    e.resolveChance();
    check(e.state().decisions.back().nation == "kmt", "Normal casualty choice not defender owned");
    choose(e, "land_take_casualty", "d");
    check(e.state().chance.has_value() && e.state().units.contains("d"),
          "Defender casualty lost return fire");
    e.resolveChance();
    choose(e, "land_take_casualty", "a");
    check(!e.state().units.contains("a") && !e.state().units.contains("d"),
          "Simultaneous casualties did not both fire");
    check(e.state().battles.at(b).data.require("result").asString() == "mutual_destruction",
          "Wrong mutual destruction result");
    auto replayed = Engine::replay(s.definition, rules(), initial, e.state().history);
    check(replayed.exactReplayIdentity() == e.exactReplayIdentity(), "Land battle replay diverged");
    auto restored = Engine::restore(s.definition, rules(), e.serialize());
    check(restored.planningKey() == e.planningKey(), "Battle context lost in checkpoint");
}
void exactSmallBattleProbabilities() {
    int win = 0, lose = 0, both = 0, neither = 0;
    double total = 0;
    for (int a = 1; a <= 12; ++a)
        for (int d = 1; d <= 12; ++d) {
            auto s = fixture();
            clearTerrain(s, hopeh);
            add(s, "a", "japan", hopeh);
            add(s, "d", "kmt", hopeh);
            battle(s);
            Engine e(s, rules(), 1);
            e.setDiceTapeForTesting({a, d});
            begin(e);
            auto c = *e.state().chance;
            total += outcomeProbability(c, ChanceOutcome{{{a}}}) / 12.0;
            e.resolveChance();
            if (!e.state().decisions.empty())
                choose(e, "land_take_casualty", "d");
            if (e.state().chance)
                e.resolveChance();
            if (!e.state().decisions.empty() && e.state().decisions.back().kind == "land_casualty")
                choose(e, "land_take_casualty", "a");
            bool aliveA = e.state().units.contains("a"), aliveD = e.state().units.contains("d");
            if (aliveA && !aliveD)
                ++win;
            else if (!aliveA && aliveD)
                ++lose;
            else if (!aliveA && !aliveD)
                ++both;
            else
                ++neither;
        }
    check(win == 16 && lose == 40 && both == 8 && neither == 80,
          "Hand-computed 2/12 versus 4/12 distribution changed");
    check(std::abs(total - 1) < 1e-12, "D12 branch probabilities do not sum to one");
}
void firstStrikePreventsOrdinaryReturn() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    add(s, "a", "japan", hopeh, "artillery");
    add(s, "d", "kmt", hopeh);
    battle(s);
    Engine e(s, rules());
    e.setDiceTapeForTesting({1});
    begin(e);
    check(e.state().chance->dice.size() == 1, "Artillery first strike did not fire separately");
    e.resolveChance();
    choose(e, "land_take_casualty", "d");
    check(e.state().units.contains("a") && !e.state().units.contains("d") && !e.state().chance,
          "First-strike victim returned fire");
}
void opposingFirstStrikesAreSimultaneous() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    add(s, "a", "japan", hopeh, "artillery");
    add(s, "d", "kmt", hopeh, "artillery");
    battle(s);
    Engine e(s, rules());
    e.setDiceTapeForTesting({1, 1});
    begin(e);
    check(e.state().chance->dice.size() == 2, "Opposing first strike not simultaneous");
    e.resolveChance();
    while (!e.state().decisions.empty())
        choose(e, "land_take_casualty");
    check(e.state().units.empty(), "Both first-strike casualties must fire");
}
void casualtySelectionIsPlayerChoice() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    add(s, "a", "japan", hopeh);
    add(s, "d1", "kmt", hopeh);
    add(s, "d2", "kmt", hopeh, "cavalry");
    battle(s);
    Engine e(s, rules());
    e.setDiceTapeForTesting({1, 12, 12});
    begin(e);
    e.resolveChance();
    check(e.legalActions().size() == 2, "Casualty policy hid legal choices");
    choose(e, "land_take_casualty", "d2");
    check(e.state().chance->dice.size() == 2, "Chosen casualty did not return fire");
    e.resolveChance();
    check(e.state().units.contains("d1") && !e.state().units.contains("d2"),
          "Explicit casualty selection ignored");
}
void targetSelectionAndFallback() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    add(s, "a", "japan", hopeh, "tank_destroyer");
    add(s, "d", "kmt", hopeh, "light_armor");
    battle(s);
    Engine e(s, rules());
    e.setDiceTapeForTesting({1, 12});
    begin(e);
    e.resolveChance();
    check(e.state().decisions.back().nation == "japan", "Target Selection not firing player choice");
    choose(e, "land_take_casualty", "d");
    auto t = fixture();
    clearTerrain(t, hopeh);
    add(t, "a", "japan", hopeh, "tank_destroyer");
    add(t, "d", "kmt", hopeh);
    battle(t);
    Engine f(t, rules());
    f.setDiceTapeForTesting({1});
    begin(f);
    f.resolveChance();
    check(f.state().decisions.back().nation == "kmt",
          "No eligible target did not fall back to normal casualty");
}
void kmtLowMoraleEmptyAndOrigins() {
    auto s = fixture("kmt");
    clearTerrain(s, hopeh);
    s.territories.at(hopeh).possessor = "japan";
    s.territories.at(beiping).possessor = "kmt";
    s.territories.at(shantung).possessor = "kmt";
    add(s, "a", "kmt", hopeh);
    add(s, "b", "kmt", hopeh, "cavalry");
    auto id = battle(s, {"a", "b"}, {{"a", beiping}, {"b", shantung}}, hopeh, "kmt");
    Engine e(s, rules());
    e.setDiceTapeForTesting({10, 12});
    begin(e);
    check(e.state().chance && e.state().chance->dice.size() == 2, "Empty attack skipped Low Morale");
    e.resolveChance();
    check(e.state().units.at("a").zone == beiping && e.state().units.at("b").zone == shantung,
          "Low Morale lost contingent origins");
    check(e.state().territories.at(hopeh).possessor == "japan", "Retreated force captured empty territory");
    check(e.state().battles.at(id).flags.at("finished"), "Empty low morale attack stuck");
}
void lowMoraleUnitsCannotBeCasualties() {
    auto s = fixture("kmt");
    clearTerrain(s, hopeh);
    s.territories.at(hopeh).possessor = "japan";
    s.territories.at(beiping).possessor = "kmt";
    add(s, "a", "kmt", hopeh);
    add(s, "b", "kmt", hopeh);
    add(s, "d", "japan", hopeh);
    battle(s, {"a", "b"}, {{"a", beiping}, {"b", beiping}}, hopeh, "kmt");
    Engine e(s, rules());
    e.setDiceTapeForTesting({10, 7, 1});
    begin(e);
    e.resolveChance();
    check(e.state().units.at("a").zone == beiping, "Low Morale did not retreat");
    e.resolveChance();
    for (const auto &a : e.legalActions())
        if (a.parameters.find("unit"))
            check(a.parameters.require("unit").asString() != "a",
                  "Retreating Low Morale unit offered as casualty");
}
void ordinaryLowMoraleWithoutAnOriginIsUnsupported() {
    auto s = fixture("kmt");
    clearTerrain(s, hopeh);
    s.territories.at(hopeh).possessor = "japan";
    add(s, "a", "kmt", hopeh);
    battle(s, {"a"}, {{"a", ""}}, hopeh, "kmt");
    Engine e(s, rules());
    e.setDiceTapeForTesting({10});
    begin(e);
    const auto before = e.serialize();
    bool rejected = false;
    try { e.resolveChance(); } catch (const std::runtime_error& error) {
        rejected = std::string(error.what()).find("Unsupported rule state: KMT Low Morale") != std::string::npos;
    }
    check(rejected, "Ordinary Low Morale inherited the shared-Truce elimination exception");
    check(e.serialize() == before, "Unsupported ordinary Low Morale changed units, events or RNG");
}
void artilleryPairingAndSurvivorRecalculation() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    add(s, "a", "japan", hopeh, "artillery");
    add(s, "b", "japan", hopeh, "artillery");
    add(s, "i", "japan", hopeh);
    add(s, "d", "kmt", hopeh);
    auto id = battle(s, {"a", "b", "i"}, {{"a", beiping}, {"b", beiping}, {"i", beiping}});
    Engine e(s, rules());
    begin(e);
    check(e.state().decisions.back().kind == "land_artillery_pairing", "Pair selection not exposed");
    choose(e, "land_pair_artillery");
    const auto &b = e.state().battles.at(id);
    int supported = 0, unpaired = 0;
    for (const auto &art : {"a", "b"}) {
        auto x = landCombatStats(e.state(), b, art, true, 1);
        if (x.threshold == 3)
            ++supported;
        if (x.threshold == 2)
            ++unpaired;
    }
    check(supported == 1 && unpaired == 1, "Artillery companion count wrong");
    check(landCombatStats(e.state(), b, "i", true, 1).threshold == 3, "Infantry support bonus absent");
}
void onlyLandEntriesCreateRetreatDestinations() {
    auto s = fixture();
    add(s, "land", "japan", hopeh);
    add(s, "air", "japan", hopeh, "fighter");
    add(s, "defender", "kmt", hopeh);
    const auto id = battle(s, {"land", "air"}, {{"land", beiping}, {"air", shantung}});
    check(landRetreatOrigins(s, s.battles.at(id)) == std::set<Id>{beiping},
          "Aircraft entry created a ground retreat destination");
    removePoliticalUnits(s, {"land"});
    check(landRetreatOrigins(s, s.battles.at(id)) == std::set<Id>{beiping},
          "The land entrant's death erased its genuine retreat origin");
}
void cityRoundLimitAndRetreatChoice() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    editNode(s, hopeh, [](O &n) { n["is_city"] = V(true); });
    add(s, "a", "japan", hopeh);
    add(s, "d", "kmt", hopeh);
    battle(s);
    Engine e(s, rules());
    e.setDiceTapeForTesting({12, 12, 12, 12, 12, 12});
    begin(e);
    for (int round = 0; round < 3; ++round) {
        e.resolveChance();
        e.resolveChance();
        if (round < 2)
            choose(e, "land_continue_fighting");
    }
    auto finalChoices = e.legalActions();
    check(std::none_of(finalChoices.begin(), finalChoices.end(),
                       [](const Action &a) { return a.kind == "land_continue_fighting"; }),
          "City allowed fourth combat round");
    choose(e, "land_retreat_begin");
    auto choices = e.legalActions();
    check(!choices.empty() && choices.front().parameters.require("zone").asString() == beiping,
          "Retreat not restricted to legal origins");
    choose(e, "land_retreat_unit", "a");
    check(e.state().units.at("a").zone == beiping && e.state().units.at("a").movementRemaining == 0,
          "Retreat did not exhaust movement");
}
void terrainAndJapaneseModifiers() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    editNode(s, hopeh, [](O &n) {
        n["terrain"] = V(A{V(std::string("mountain")), V(std::string("marsh"))});
        n["is_city"] = V(true);
    });
    add(s, "a", "japan", hopeh, "medium_armor");
    add(s, "d", "kmt", hopeh, "mountain_infantry");
    auto id = battle(s);
    check(landCombatStats(s, s.battles.at(id), "a", true, 1).threshold == 4,
          "Terrain penalties stacked beyond greatest negative");
    check(landCombatStats(s, s.battles.at(id), "d", false, 1).threshold == 5,
          "Positive mountain/city bonuses stacked");
    auto t = fixture("kmt");
    const Id tokyo = "land_jap_tokyo";
    t.territories.at(tokyo).possessor = "japan";
    add(t, "a", "kmt", tokyo);
    add(t, "d", "japan", tokyo);
    auto bid = battle(t, {"a"}, {{"a", "land_jap_honshu"}}, tokyo, "kmt");
    check(landCombatStats(t, t.battles.at(bid), "d", false, 1).threshold == 6,
          "Dug In Defense failed to stack with city bonus");
}
void fortificationConstrainsApproach() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    add(s, "a", "japan", hopeh);
    add(s, "b", "japan", hopeh);
    add(s, "d", "kmt", hopeh);
    FacilityState f;
    f.id = "fort";
    f.type = "fortification";
    f.zone = hopeh;
    f.flags["border:" + beiping] = 1;
    s.facilities.emplace(f.id, f);
    battle(s, {"a", "b"}, {{"a", beiping}, {"b", shantung}});
    Engine e(s, rules());
    e.setDiceTapeForTesting({1, 12});
    begin(e);
    check(e.state().chance->dice.size() == 2, "Fortification first strike missing");
    e.resolveChance();
    check(e.legalActions().size() == 1 &&
              e.legalActions().front().parameters.require("unit").asString() == "a",
          "Fort hit escaped protected approach");
}
void attritionIsSeparateAndNoReturnFire() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    add(s, "a", "japan", beiping, "advanced_artillery");
    add(s, "d", "kmt", hopeh);
    s.captureTurnStart();
    auto id = registerAttritionBattle(s, hopeh, "japan", {"a"});
    Engine e(s, rules());
    e.setDiceTapeForTesting({1});
    begin(e);
    e.resolveChance();
    choose(e, "land_take_casualty", "d");
    check(!e.state().chance && e.state().units.at("a").zone == beiping,
          "Attrition moved artillery or allowed return fire");
    check(e.state().territories.at(hopeh).possessor == "kmt" && e.state().battles.at(id).flags.at("finished"),
          "Attrition captured territory or continued rounds");
    auto t = fixture();
    add(t, "a", "japan", beiping, "advanced_artillery");
    t.captureTurnStart();
    t.units.at("a").route = {beiping};
    rejects([&] { registerAttritionBattle(t, hopeh, "japan", {"a"}); },
            "Moved artillery made attrition attack");
}
void choiceChangesPlanningKeyAndForgedCasualtyRollsBack() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    add(s, "a", "japan", hopeh);
    add(s, "d1", "kmt", hopeh);
    add(s, "d2", "kmt", hopeh);
    battle(s);
    Engine e(s, rules());
    e.setDiceTapeForTesting({1, 12, 12});
    begin(e);
    e.resolveChance();
    auto before = e.exactReplayIdentity();
    auto forged = e.legalActions().front();
    auto p = forged.parameters.asObject();
    p["unit"] = V(std::string("a"));
    forged.parameters = V(p);
    rejects([&] { e.step(forged); }, "Forged casualty accepted");
    check(e.exactReplayIdentity() == before, "Rejected casualty changed state or RNG");
    auto clone = e.clone();
    choose(e, "land_take_casualty", "d1");
    choose(clone, "land_take_casualty", "d2");
    check(clone.planningKey() != e.planningKey(), "Distinct pending casualties missing from planning state");
}
void strategicRocketsAreNotCombatCasualties() {
    for (bool attackingRocket : {false, true}) {
        auto s = fixture();
        clearTerrain(s, hopeh);
        add(s, "a", "japan", hopeh);
        add(s, "d", "kmt", hopeh);
        add(s, "rocket", attackingRocket ? "japan" : "kmt", hopeh, "strategic_rocket");
        auto id = attackingRocket
                      ? battle(s, {"a", "rocket"}, {{"a", beiping}, {"rocket", beiping}})
                      : battle(s);
        Engine e(s, rules());
        e.setDiceTapeForTesting(attackingRocket ? std::vector<int>{12, 1} : std::vector<int>{1, 12});
        const auto initial = e.serialize();
        begin(e);
        check(e.state().chance && e.state().chance->dice.size() == 1,
              "Strategic Rocket received an attack die");
        e.resolveChance();
        if (attackingRocket) {
            check(e.state().chance && e.state().chance->dice.size() == 1,
                  "Unexpected defender dice against attacking Rocket");
            e.resolveChance();
        }
        auto actions = e.legalActions();
        check(actions.size() == 1 && actions.front().kind == "land_take_casualty" &&
                  actions.front().parameters.require("unit").asString() == (attackingRocket ? "a" : "d"),
              "Strategic Rocket offered as ordinary casualty");
        auto forged = actions.front();
        auto parameters = forged.parameters.asObject();
        parameters["unit"] = V(std::string("rocket"));
        forged.parameters = V(parameters);
        const auto before = e.exactReplayIdentity();
        rejects([&] { e.step(forged); }, "Forged Strategic Rocket casualty accepted");
        check(e.exactReplayIdentity() == before, "Rejected Rocket casualty mutated state");
        choose(e, "land_take_casualty", attackingRocket ? "a" : "d");
        if (!attackingRocket) {
            check(e.state().chance && e.state().chance->dice.size() == 1,
                  "Strategic Rocket received a defense die");
            check(e.state().units.contains("rocket"), "Rocket lost its escort before simultaneous return fire");
            e.resolveChance();
        }
        check(!e.state().units.contains("rocket"), "Unsupported Rocket survived enemy land occupation");
        drain(e);
        check(flag(e.state().battles.at(id).flags, "finished"), "Rocket prevented combat completion");
        check(e.state().territories.at(hopeh).possessor == (attackingRocket ? "kmt" : "japan"),
              "Rocket changed conquest after the last escort fell");
        auto replay = Engine::replay(s.definition, rules(), initial, e.state().history);
        check(replay.exactReplayIdentity() == e.exactReplayIdentity(),
              "Rocket destruction after escort loss did not replay");
    }
}
void unsupportedRocketsFallOnEnemyLandEntry() {
    for (bool attackingRocket : {false, true}) {
        auto s = fixture();
        clearTerrain(s, hopeh);
        if (attackingRocket) {
            add(s, "a", "japan", hopeh, "strategic_rocket");
            add(s, "d", "kmt", hopeh);
        } else {
            add(s, "a", "japan", hopeh);
            add(s, "r1", "kmt", hopeh, "strategic_rocket");
            add(s, "r2", "kmt", hopeh, "strategic_rocket");
        }
        auto id = battle(s);
        check(attackingRocket ? !s.units.contains("a")
                              : !s.units.contains("r1") && !s.units.contains("r2"),
              "Rockets remained alone alongside an enemy land unit");
        Engine e(s, rules());
        e.setDiceTapeForTesting({12});
        begin(e);
        drain(e);
        check(flag(e.state().battles.at(id).flags, "finished"), "Unsupported Rocket battle stuck");
        check(e.state().territories.at(hopeh).possessor == (attackingRocket ? "kmt" : "japan"),
              "Unsupported Rockets blocked conquest or conquered enemy defenders");
    }
}
void airOnlyAttacksPreserveStrategicRockets() {
    for (bool withEscort : {false, true}) {
        auto s = fixture();
        clearTerrain(s, hopeh);
        add(s, "a", "japan", hopeh, "fighter");
        s.units.at("a").turnFlags["air_in_flight"] = 1;
        add(s, "rocket", "kmt", hopeh, "strategic_rocket");
        if (withEscort) add(s, "d", "kmt", hopeh);
        auto id = battle(s);
        Engine e(s, rules());
        e.setDiceTapeForTesting({1});
        const auto initial = e.serialize();
        begin(e);
        if (withEscort) {
            check(e.state().chance && e.state().chance->dice.size() == 1,
                  "Air-only attack did not engage the Rocket escort");
            e.resolveChance();
            choose(e, "land_take_casualty", "d");
        }
        check(!e.state().chance && e.state().units.contains("rocket"),
              "Aircraft destroyed a Strategic Rocket or prolonged an ineffective raid");
        check(!e.state().decisions.empty() && e.state().decisions.back().kind == "air_landing",
              "Air-only Rocket attack omitted normal aircraft return");
        choose(e, "air_land");
        check(e.state().units.at("a").zone != hopeh && e.state().units.contains("rocket") &&
                  e.state().territories.at(hopeh).possessor == "kmt" &&
                  flag(e.state().battles.at(id).flags, "finished"),
              "Air-only Rocket attack captured land or failed to finish");
        auto replay = Engine::replay(s.definition, rules(), initial, e.state().history);
        check(replay.exactReplayIdentity() == e.exactReplayIdentity(), "Rocket air raid return did not replay");
    }
}
void strategicRocketSurvivesMutualEscortLossAndAttrition() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    add(s, "a", "japan", hopeh);
    add(s, "d", "kmt", hopeh);
    add(s, "rocket", "kmt", hopeh, "strategic_rocket");
    auto id = battle(s);
    Engine e(s, rules());
    e.setDiceTapeForTesting({1, 1});
    begin(e);
    e.resolveChance();
    choose(e, "land_take_casualty", "d");
    e.resolveChance();
    choose(e, "land_take_casualty", "a");
    check(e.state().units.contains("rocket") && e.state().units.size() == 1 &&
              e.state().territories.at(hopeh).possessor == "kmt" &&
              flag(e.state().battles.at(id).flags, "finished"),
          "Rocket was destroyed despite no enemy land surviving simultaneous fire");

    auto t = fixture();
    clearTerrain(t, hopeh);
    add(t, "a", "japan", beiping, "advanced_artillery");
    add(t, "rocket", "kmt", hopeh, "strategic_rocket");
    t.captureTurnStart();
    auto attrition = registerAttritionBattle(t, hopeh, "japan", {"a"});
    Engine remote(t, rules());
    remote.setDiceTapeForTesting({1});
    begin(remote);
    remote.resolveChance();
    check(remote.state().units.contains("rocket") && !remote.state().chance &&
              remote.state().decisions.empty() && flag(remote.state().battles.at(attrition).flags, "finished") &&
              remote.state().territories.at(hopeh).possessor == "kmt",
          "Remote attrition selected a Rocket casualty or treated adjacent artillery as occupying land");
}
void fightersPrioritizeAircraft() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    add(s, "a", "japan", hopeh, "fighter");
    add(s, "i", "japan", hopeh);
    add(s, "d", "kmt", hopeh, "tactical_bomber");
    add(s, "di", "kmt", hopeh);
    auto id = battle(s, {"a", "i"}, {{"a", beiping}, {"i", beiping}});
    s.units.at("a").turnFlags["air_in_flight"] = 1;
    Engine e(s, rules());
    e.setDiceTapeForTesting({1, 12, 12});
    begin(e);
    choose(e, "air_defend");
    choose(e, "land_progress_battle");
    e.resolveChance();
    check(e.legalActions().size() == 1 &&
              e.legalActions().front().parameters.require("unit").asString() == "d",
          "Fighter hit did not prioritize enemy aircraft");
    choose(e, "land_take_casualty", "d");
    check(!e.state().units.contains("d"), "Air superiority casualty remained for ordinary fire");
}
void aaaFiresOnlyOnceAndCountsAircraft() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    for (const auto &id : {"a", "b"}) {
        add(s, id, "japan", hopeh, "fighter");
        s.units.at(id).turnFlags["air_in_flight"] = 1;
    }
    add(s, "d", "kmt", hopeh);
    add(s, "aa1", "kmt", hopeh, "anti_aircraft_artillery");
    add(s, "aa2", "kmt", hopeh, "anti_aircraft_artillery");
    battle(s, {"a", "b"}, {{"a", beiping}, {"b", beiping}});
    Engine e(s, rules());
    e.setDiceTapeForTesting(std::vector<int>(20, 12));
    begin(e);
    check(e.state().chance->dice.size() == 6,
          "Two AAA against two aircraft must fire four shots plus two fighter shots");
    e.resolveChance();
    check(e.state().chance->dice.size() == 1, "AAA fired again in ordinary defender step");
    e.resolveChance();
    choose(e, "land_continue_fighting");
    check(e.state().chance->dice.size() == 2, "Second round repeated AAA or skipped ordinary fighter fire");
}
void airborneCityAaDestroysLinkedCargoBeforeLanding() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    editNode(s, hopeh, [](O &n) { n["is_city"] = V(true); });
    add(s, "plane", "japan", hopeh, "air_transport");
    add(s, "a", "japan", hopeh, "airborne_infantry");
    add(s, "d", "kmt", hopeh);
    attachCargo(s, "plane", "a");
    s.units.at("plane").commitments.insert("airborne_assault");
    s.units.at("a").commitments.insert("airborne_assault");
    s.units.at("plane").turnFlags["air_in_flight"] = 1;
    auto id = battle(s, {"plane", "a"}, {{"plane", beiping}, {"a", beiping}});
    Engine e(s, rules());
    e.setDiceTapeForTesting({1});
    begin(e);
    check(e.state().chance && e.state().chance->dice.size() == 1,
          "City airborne AAA missing before ordinary combat");
    e.resolveChance();
    choose(e, "land_take_casualty", "plane");
    check(!e.state().units.contains("plane") && !e.state().units.contains("a"),
          "Destroyed airborne transport landed or let cargo attack");
    check(e.state().battles.at(id).flags.at("finished"),
          "City AAA elimination did not finish failed assault");
}
void airborneOrdinaryAaTimingAndSurvivingDrop() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    add(s, "plane", "japan", hopeh, "air_transport");
    add(s, "a", "japan", hopeh, "airborne_infantry");
    add(s, "d", "kmt", hopeh);
    add(s, "aa", "kmt", hopeh, "anti_aircraft_artillery");
    attachCargo(s, "plane", "a");
    s.units.at("plane").commitments.insert("airborne_assault");
    s.units.at("a").commitments.insert("airborne_assault");
    s.units.at("plane").turnFlags["air_in_flight"] = 1;
    auto id = battle(s, {"plane", "a"}, {{"plane", beiping}, {"a", beiping}});
    Engine e(s, rules());
    e.setDiceTapeForTesting({12, 1, 12});
    begin(e);
    check(e.state().battles.at(id).data.require("rolling_phase").asString() == "air_fire",
          "Defender ordinary AAA did not fire in the shared step 4");
    e.resolveChance();
    choose(e, "air_land");
    choose(e, "land_progress_battle");
    check(!e.state().units.at("a").carriedBy && e.state().units.at("plane").zone != hopeh,
          "Surviving airborne drop failed to land transport before infantry attack");
    check(e.state().chance &&
              e.state().battles.at(id).data.require("rolling_phase").asString() == "attacker_fire",
          "Dropped infantry did not attack after transport landed");
    e.resolveChance();
    check(e.state().decisions.back().nation == "kmt", "Airborne attack bonus did not generate normal hit");
}
void airborneFightersAndBothAaaRollTogether() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    add(s, "plane", "japan", hopeh, "air_transport");
    add(s, "para", "japan", hopeh, "airborne_infantry");
    add(s, "escort", "japan", hopeh, "fighter");
    add(s, "attacking_aaa", "japan", hopeh, "anti_aircraft_artillery");
    add(s, "defending_aaa", "kmt", hopeh, "anti_aircraft_artillery");
    add(s, "defending_fighter", "kmt", hopeh, "fighter");
    add(s, "defending_infantry", "kmt", hopeh);
    attachCargo(s, "plane", "para");
    for (const auto &id : {"plane", "para"}) s.units.at(id).commitments.insert("airborne_assault");
    for (const auto &id : {"plane", "escort"}) s.units.at(id).turnFlags["air_in_flight"] = 1;
    auto id = battle(s, {"attacking_aaa", "plane", "para", "escort"},
                     {{"attacking_aaa", beiping}, {"plane", beiping}, {"para", beiping}, {"escort", beiping}});
    Engine e(s, rules());
    e.setDiceTapeForTesting({1, 12, 1, 12, 1, 12, 12});
    const auto checkpoint = e.serialize();
    begin(e);
    choose(e, "air_defend");
    choose(e, "land_progress_battle");
    check(e.state().chance && e.state().chance->dice.size() == 5 &&
              e.state().battles.at(id).data.require("rolling_phase").asString() == "air_fire",
          "Airborne step 4 did not include both Fighters and both AAA sides together");
    check(e.state().units.at("para").carriedBy == "plane" && e.state().units.at("plane").zone == hopeh,
          "Airborne cargo landed before the shared Air Superiority/AAA roll");
    e.resolveChance();
    choose(e, "land_take_casualty", "defending_fighter");
    check(e.state().units.contains("defending_fighter"), "Step-4 casualty lost its simultaneous shot");
    for (const auto &a : e.legalActions())
        check(a.parameters.require("unit").asString() != "para",
              "Airborne infantry was independently selectable before its transport landed");
    choose(e, "land_take_casualty", "plane");
    check(!e.state().units.contains("plane") && !e.state().units.contains("para"),
          "Step-4 transport casualty detached or landed its cargo");
    choose(e, "land_take_casualty", "escort");
    check(!e.state().units.contains("escort") && !e.state().units.contains("defending_fighter") &&
              e.state().chance && e.state().chance->dice.size() == 1 &&
              e.state().battles.at(id).data.require("rolling_phase").asString() == "defender_fire",
          "Selected Fighter failed to return fire or AAA repeated its first-round shot");
    e.resolveChance();
    choose(e, "land_continue_fighting");
    check(e.state().chance && e.state().chance->dice.size() == 1,
          "Airborne AAA fired again in a later combat round");
    e.resolveChance();
    auto replay = Engine::replay(s.definition, rules(), checkpoint, e.state().history);
    check(replay.exactReplayIdentity() == e.exactReplayIdentity(), "Shared airborne Air Superiority/AAA replay diverged");
}
void firstStrikeFighterKeepsPriorityAndFiresOnce() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    add(s, "a", "japan", hopeh, "fighter");
    add(s, "i", "japan", hopeh);
    add(s, "defending_fighter", "kmt", hopeh, "fighter");
    add(s, "defending_aaa", "kmt", hopeh, "anti_aircraft_artillery");
    add(s, "defending_infantry", "kmt", hopeh);
    s.units.at("a").turnFlags["air_in_flight"] = 1;
    s.nations.at("japan").turnFlags["surprise_attack_zone:" + hopeh] = 1;
    auto id = battle(s, {"a", "i"}, {{"a", beiping}, {"i", beiping}});
    Engine e(s, rules());
    e.setDiceTapeForTesting({1, 12, 12, 12, 12, 12});
    const auto checkpoint = e.serialize();
    begin(e);
    choose(e, "air_defend");
    choose(e, "land_progress_battle");
    check(e.state().chance && e.state().chance->dice.size() == 1 &&
              e.state().battles.at(id).data.require("rolling_phase").asString() == "first_strike",
          "Surprise Fighter did not fire separately in step 3");
    e.resolveChance();
    check(e.legalActions().size() == 1 &&
              e.legalActions().front().parameters.require("unit").asString() == "defending_fighter",
          "First-strike Fighter lost its first-round aircraft priority");
    choose(e, "land_take_casualty", "defending_fighter");
    check(!e.state().units.contains("defending_fighter") && e.state().chance &&
              e.state().chance->dice.size() == 1 &&
              e.state().battles.at(id).data.require("rolling_phase").asString() == "air_fire" &&
              e.state().battles.at(id).data.require("shots").asArray().front().require("unit").asString() == "defending_aaa",
          "First-strike casualty returned fire or surviving Fighter fired again in step 4");
    e.resolveChance();
    check(e.state().chance && e.state().chance->dice.size() == 1,
          "First-strike Fighter fired again with ordinary attackers");
    e.resolveChance();
    e.resolveChance();
    choose(e, "land_continue_fighting");
    check(e.state().chance && e.state().chance->dice.size() == 2 &&
              e.state().battles.at(id).data.require("rolling_phase").asString() == "attacker_fire",
          "Surviving first-strike Fighter did not fire normally in the second round");
    auto replay = Engine::replay(s.definition, rules(), checkpoint, e.state().history);
    check(replay.exactReplayIdentity() == e.exactReplayIdentity(), "First-strike Fighter stage replay diverged");
}
void airborneAircraftCasualtiesRetainOnlyTheirUnfiredRoll() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    add(s, "plane", "japan", hopeh, "air_transport");
    add(s, "para", "japan", hopeh, "airborne_infantry");
    add(s, "af", "japan", hopeh, "fighter");
    add(s, "am", "japan", hopeh, "medium_bomber");
    add(s, "df", "kmt", hopeh, "fighter");
    add(s, "di", "kmt", hopeh);
    add(s, "dm", "kmt", hopeh, "medium_bomber");
    attachCargo(s, "plane", "para");
    for (const auto &id : {"plane", "para"}) s.units.at(id).commitments.insert("airborne_assault");
    for (const auto &id : {"plane", "af", "am"}) s.units.at(id).turnFlags["air_in_flight"] = 1;
    auto id = battle(s, {"plane", "para", "af", "am"},
                     {{"plane", beiping}, {"para", beiping}, {"af", beiping}, {"am", beiping}});
    Engine e(s, rules());
    e.setDiceTapeForTesting({1, 1, 12, 1, 12, 12});
    const auto checkpoint = e.serialize();
    begin(e);
    choose(e, "air_defend", "df");
    choose(e, "air_defend", "dm");
    choose(e, "land_progress_battle");
    e.resolveChance();
    choose(e, "land_take_casualty", "dm");
    choose(e, "land_take_casualty", "am");
    check(e.state().units.contains("am") && e.state().units.contains("dm") &&
              e.state().decisions.back().kind == "air_landing" &&
              e.legalActions().front().parameters.require("unit").asString() == "plane",
          "Not-yet-fired aircraft died before their roll or became landing candidates");
    auto restored = Engine::restore(s.definition, rules(), e.serialize());
    check(restored.planningKey() == e.planningKey(), "Airborne return-fire casualties were not checkpointed");
    choose(e, "air_land", "plane");
    choose(e, "land_progress_battle");
    auto shots = e.state().battles.at(id).data.require("shots").asArray();
    check(e.state().chance && shots.size() == 2 &&
              std::any_of(shots.begin(), shots.end(), [](const V &x) { return x.require("unit").asString() == "am"; }),
          "Attacking aircraft casualty lost its ordinary return roll");
    e.resolveChance();
    for (const auto &a : e.legalActions())
        check(a.parameters.require("unit").asString() != "dm", "Step-4 casualty could be selected twice");
    choose(e, "land_take_casualty", "di");
    shots = e.state().battles.at(id).data.require("shots").asArray();
    check(!e.state().units.contains("am") && e.state().units.contains("dm") &&
              e.state().chance && shots.size() == 2 &&
              std::any_of(shots.begin(), shots.end(), [](const V &x) { return x.require("unit").asString() == "dm"; }),
          "Attacking casualty survived its roll or defending aircraft lost its return roll");
    e.resolveChance();
    check(!e.state().units.contains("am") && !e.state().units.contains("dm") &&
              e.state().territories.at(hopeh).possessor == "kmt" &&
              e.state().battles.at(id).data.require("airborne_return_fire").asArray().empty(),
          "Selected aircraft survived into another round or changed possession");
    auto replay = Engine::replay(s.definition, rules(), checkpoint, e.state().history);
    check(replay.exactReplayIdentity() == e.exactReplayIdentity(), "Airborne aircraft return-fire replay diverged");
}
void airborneInfantryFallbackCasualtiesGetTheirUnfiredRoll() {
    for (bool attackingCasualty : {false, true}) {
        auto s = fixture();
        clearTerrain(s, hopeh);
        add(s, "plane", "japan", hopeh, "air_transport");
        add(s, "para", "japan", hopeh, "airborne_infantry");
        attachCargo(s, "plane", "para");
        for (const auto &id : {"plane", "para"}) s.units.at(id).commitments.insert("airborne_assault");
        s.units.at("plane").turnFlags["air_in_flight"] = 1;
        std::vector<Id> attackers{"plane", "para"};
        std::map<Id, Id> origins{{"plane", beiping}, {"para", beiping}};
        if (attackingCasualty) {
            add(s, "i", "japan", hopeh);
            attackers.push_back("i"); origins["i"] = beiping;
            add(s, "da", "kmt", hopeh, "anti_aircraft_artillery");
            add(s, "df", "kmt", hopeh, "fighter");
        } else {
            add(s, "af", "japan", hopeh, "fighter");
            s.units.at("af").turnFlags["air_in_flight"] = 1;
            attackers.push_back("af"); origins["af"] = beiping;
            add(s, "i", "kmt", hopeh);
        }
        auto id = battle(s, attackers, origins);
        Engine e(s, rules());
        e.setDiceTapeForTesting(attackingCasualty ? std::vector<int>{1, 1, 1} : std::vector<int>{1, 12, 1});
        const auto checkpoint = e.serialize();
        begin(e);
        if (attackingCasualty) {
            choose(e, "air_defend", "df");
            choose(e, "land_progress_battle");
        }
        e.resolveChance();
        if (attackingCasualty) choose(e, "land_take_casualty", "plane");
        choose(e, "land_take_casualty", "i");
        check(e.state().units.contains("i"), "Airborne step-4 infantry fallback casualty lost its return roll");
        if (!attackingCasualty) {
            choose(e, "air_land", "plane");
            choose(e, "land_progress_battle");
            e.resolveChance();
        }
        const auto shots = e.state().battles.at(id).data.require("shots").asArray();
        check(e.state().chance && shots.size() == 1 && shots.front().require("unit").asString() == "i",
              "Selected infantry did not get exactly one normal roll");
        e.resolveChance();
        choose(e, "land_take_casualty", attackingCasualty ? "da" : "para");
        check(!e.state().units.contains("i") && e.state().territories.at(hopeh).possessor == "kmt",
              "Selected infantry survived its return roll or captured land");
        if (!attackingCasualty) choose(e, "air_land", "af");
        auto replay = Engine::replay(s.definition, rules(), checkpoint, e.state().history);
        check(replay.exactReplayIdentity() == e.exactReplayIdentity(), "Infantry fallback return-fire replay diverged");
    }
}
void blitzPairingIsAnExplicitChoice() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    add(s, "a", "japan", hopeh, "light_armor");
    add(s, "m1", "japan", hopeh, "advanced_mechanized_infantry");
    add(s, "m2", "japan", hopeh, "advanced_mechanized_infantry");
    add(s, "m3", "japan", hopeh, "mechanized_infantry");
    auto id = battle(s, {"a", "m1", "m2", "m3"},
                     {{"a", beiping}, {"m1", beiping}, {"m2", beiping}, {"m3", beiping}});
    Engine e(s, rules());
    e.setDiceTapeForTesting({12, 12, 12, 12});
    begin(e);
    e.resolveChance();
    if (!e.state().decisions.empty() && e.state().decisions.back().kind == "politics_chinese_liberation") {
        choose(e, "politics_keep_capture");
        choose(e, "land_progress_battle");
    }
    check(!e.state().decisions.empty() && e.state().decisions.back().kind == "land_blitz_pairing",
          "Blitz pairing choice missing");
    choose(e, "land_pair_blitz", "m1");
    auto options = e.legalActions();
    check(std::none_of(options.begin(), options.end(),
                       [](const Action &a) {
                           auto p = a.parameters.find("unit");
                           return p && p->asString() == "m3";
                       }),
          "Blitz ordinary companion allowed after half advanced capacity was used");
    choose(e, "land_pair_blitz", "m2");
    check(flag(e.state().units.at("a").turnFlags, "blitz_eligible") &&
              flag(e.state().units.at("m1").turnFlags, "blitz_eligible") &&
              flag(e.state().units.at("m2").turnFlags, "blitz_eligible"),
          "Blitz capacity or survivor grant wrong");
    check(e.state().units.at("m2").commitments.contains("blitz_with:a"),
          "Blitz companion lost armor identity");
    check(e.state().battles.at(id).flags.at("finished"), "Blitz completion left battle unfinished");
}

void jointDefendersConsentAndDiceDispute() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    s.politics.chineseTruce = true;
    s.nations.at("japan").atWarWith.insert("ccp");
    s.nations.at("ccp").atWarWith.insert("japan");
    add(s, "a", "japan", hopeh);
    add(s, "d", "kmt", hopeh);
    add(s, "c", "ccp", hopeh);
    battle(s);
    Engine e(s, rules());
    e.setDiceTapeForTesting({1, 5, 5, 9, 4, 12, 12});
    begin(e);
    e.resolveChance();
    choose(e, "land_take_casualty", "c");
    check(e.state().decisions.back().nation == "ccp" &&
              e.state().decisions.back().kind == "land_casualty_consent",
          "Joint defender was not asked to agree");
    choose(e, "land_casualty_dispute");
    check(e.state().chance && e.state().chance->purpose == "land_casualty_dispute",
          "Dispute did not roll entitled players");
    e.resolveChance();
    check(e.state().chance && e.state().chance->dice.size() == 2,
          "Tied joint-defense dispute did not reroll");
    e.resolveChance();
    check(e.state().decisions.back().nation == "kmt",
          "Highest joint-defense die did not choose casualty selector");
    choose(e, "land_take_casualty", "d");
    check(e.state().chance && e.state().chance->dice.size() == 2,
          "Joint chosen defender lost simultaneous return fire");
}
void directAxisDadaoUsesJapanCalendarSlot() {
    auto s = fixture();
    clearTerrain(s, hopeh);
    ensureDadao(s);
    s.politics.surrendered.insert("japan");
    auto &n = s.nations.at("dadao");
    n.controllerNation.reset();
    n.player = "axis";
    n.alliance = "axis";
    n.gameFlags["direct_axis_control_after_japan_surrender"] = 1;
    n.atWarWith.insert("kmt");
    s.nations.at("kmt").atWarWith.insert("dadao");
    s.territories.at(beiping).possessor = "dadao";
    add(s, "a", "dadao", hopeh);
    auto id = battle(s, {"a"}, {{"a", beiping}}, hopeh, "dadao");
    Engine e(s, rules());
    e.setDiceTapeForTesting({12});
    auto beginAction = select(e.legalActions(), "land_begin_battle");
    check(beginAction.nation == "japan" && beginAction.player == "axis",
          "Controlled Dadao ordinary action stole a nation calendar slot");
    e.step(beginAction);
    e.resolveChance();
    check(e.state().territories.at(hopeh).possessor == "dadao" && e.state().units.at("a").owner == "dadao",
          "Dadao capture changed national identity");
    check(e.state().politics.surrendered.contains("japan") && e.state().battles.at(id).flags.at("finished"),
          "Direct Axis fallback did not finish Dadao combat");
    choose(e, "land_progress_battle");
    check(e.state().battles.empty(), "Finished minor battle could not be cleaned up in Japan slot");
}

void replayableGroundCampaignAndCounterattack() {
    auto s = fixture("ccp");
    clearTerrain(s, hopeh);
    s.clock.phase = Phase::CombatMovement;
    s.territories.at(beiping).possessor = "ccp";
    s.territories.at(shantung).possessor = "kmt";
    s.nations.at("ccp").atWarWith.insert("kmt");
    s.nations.at("kmt").atWarWith.insert("ccp");
    add(s, "a", "ccp", beiping);
    add(s, "d", "kmt", hopeh, "militia");
    add(s, "counter", "kmt", shantung, "cavalry");
    s.captureTurnStart();
    auto gameplay = std::make_shared<PoliticsRules>(std::make_shared<MovementRules>(
        std::make_shared<AirRules>(std::make_shared<LandCombatRules>(std::make_shared<EconomyRules>()))));
    gameplay->beginTurn(s);
    Engine e(s, gameplay, 123);
    e.setDiceTapeForTesting({1, 12, 1, 12});
    auto checkpoint = e.serialize();
    e.step(select(e.legalActions(), "movement_route", [](const Action &a) {
        return a.parameters.require("unit").asString() == "a" &&
               a.parameters.require("path").asArray().back().asString() == hopeh;
    }));
    choose(e, "end_phase");
    begin(e);
    drain(e);
    choose(e, "land_progress_battle");
    check(e.state().territories.at(hopeh).possessor == "ccp", "Opening ground attack did not capture");
    for (int k = 0;
         k < 30 && !(e.state().currentNation() == "kmt" && e.state().clock.phase == Phase::CombatMovement);
         ++k) {
        auto actions = e.legalActions();
        auto skip = std::find_if(actions.begin(), actions.end(),
                                 [](const Action &a) { return a.kind == "end_phase"; });
        if (skip != actions.end())
            e.step(*skip);
        else
            e.step(select(actions, "economy_finish_research"));
    }
    check(e.state().currentNation() == "kmt" && e.state().clock.phase == Phase::CombatMovement,
          "Ground campaign did not advance calendar slots");
    e.step(select(e.legalActions(), "movement_route", [](const Action &a) {
        return a.parameters.require("unit").asString() == "counter" &&
               a.parameters.require("path").asArray().back().asString() == hopeh;
    }));
    choose(e, "end_phase");
    begin(e);
    drain(e);
    choose(e, "land_progress_battle");
    check(e.state().territories.at(hopeh).possessor == "kmt", "Counterattack did not restore KMT possession");
    check(e.state().nations.at("ccp").treasury.value() > 2, "Intermediate income was not collected");
    auto replay = Engine::replay(s.definition, gameplay, checkpoint, e.state().history);
    check(replay.exactReplayIdentity() == e.exactReplayIdentity(),
          "Multi-turn movement/combat/accounting replay diverged");
}

} // namespace
int main() {
    try {
        for (const auto &[name, test] : std::vector<std::pair<std::string, std::function<void()>>>{
                 {"simultaneous fire and replay", simultaneousFireAndReplay},
                 {"exact probabilities", exactSmallBattleProbabilities},
                 {"first strike", firstStrikePreventsOrdinaryReturn},
                 {"opposing first strikes", opposingFirstStrikesAreSimultaneous},
                 {"casualty choice", casualtySelectionIsPlayerChoice},
                 {"target selection fallback", targetSelectionAndFallback},
                 {"KMT empty origins", kmtLowMoraleEmptyAndOrigins},
                 {"KMT protected retreaters", lowMoraleUnitsCannotBeCasualties},
                 {"ordinary KMT missing origin", ordinaryLowMoraleWithoutAnOriginIsUnsupported},
                 {"artillery pairs", artilleryPairingAndSurvivorRecalculation},
                 {"land retreat entry source", onlyLandEntriesCreateRetreatDestinations},
                 {"city round limit", cityRoundLimitAndRetreatChoice},
                 {"terrain and Dug In", terrainAndJapaneseModifiers},
                 {"fort approach", fortificationConstrainsApproach},
                 {"attrition", attritionIsSeparateAndNoReturnFire},
                 {"choice state and rollback", choiceChangesPlanningKeyAndForgedCasualtyRollsBack},
                 {"Strategic Rocket casualty and replay", strategicRocketsAreNotCombatCasualties},
                 {"unsupported Strategic Rockets", unsupportedRocketsFallOnEnemyLandEntry},
                 {"Strategic Rockets and air raids", airOnlyAttacksPreserveStrategicRockets},
                 {"Strategic Rockets simultaneous loss and attrition", strategicRocketSurvivesMutualEscortLossAndAttrition},
                 {"fighter priority", fightersPrioritizeAircraft},
                 {"AAA once", aaaFiresOnlyOnceAndCountsAircraft},
                 {"airborne city cargo loss", airborneCityAaDestroysLinkedCargoBeforeLanding},
                 {"airborne AAA/drop", airborneOrdinaryAaTimingAndSurvivingDrop},
                 {"shared airborne Fighter/AAA stage", airborneFightersAndBothAaaRollTogether},
                 {"first-strike Fighter priority and once", firstStrikeFighterKeepsPriorityAndFiresOnce},
                 {"airborne aircraft casualty return fire", airborneAircraftCasualtiesRetainOnlyTheirUnfiredRoll},
                 {"airborne infantry fallback return fire", airborneInfantryFallbackCasualtiesGetTheirUnfiredRoll},
                 {"blitz pairing", blitzPairingIsAnExplicitChoice},
                 {"joint defender dispute", jointDefendersConsentAndDiceDispute},
                 {"Dadao calendar slot", directAxisDadaoUsesJapanCalendarSlot},
                 {"ground campaign replay", replayableGroundCampaignAndCounterattack}}) {
            test();
            std::cout << "PASS " << name << '\n';
        }
        return 0;
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
