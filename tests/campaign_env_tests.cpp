#include "game/campaign_env.hpp"
#include "game/campaign_audit.hpp"
#include "game/catalog.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <cmath>
#include <functional>
#include <future>
#include <iostream>
#include <stdexcept>

namespace {
using namespace game::campaign;
using V = game::json::Value;
using O = V::Object;
const auto scenario = std::filesystem::path(GWRL_SOURCE_DIR) / "game_content/scenarios/japan_china_1936";
void require(bool value, const std::string& message) { if (!value) throw std::runtime_error(message); }
void near(double actual, double expected, const std::string& message) { require(std::abs(actual - expected) < 1e-9, message); }

State emptyAssets() {
    auto s = loadScenario(scenario);
    s.units.clear(); s.facilities.clear(); s.rails.clear(); s.construction.clear(); s.repairs.clear();
    s.captureTurnStart();
    return s;
}

void publicDecisionsAndNoAutomaticOpponents() {
    CampaignEnv env(scenario, 123);
    require(env.currentDecisionPlayer() == "comintern" && env.currentNation() == "ccp", "Opening owner mismatch");
    require(env.returns() == std::array<double, 3>{0, 0, 0}, "Intermediate wealth was paid as reward");
    const auto start = env.serialize();
    auto copy = env.clone();
    auto action = copy.legalActions().back();
    require(action.kind == "end_phase", "Expected explicit phase boundary");
    copy.applyAction(action);
    require(env.serialize() == start && copy.serialize() != start, "Clone mutated actual game");
    copy.restore(start);
    require(copy.serialize() == start, "Checkpoint restore changed state");
    // Passing is a visible caller choice, never an automatic Chinese turn.
    for (int i = 0; i < 5; ++i) {
        const auto actions = env.legalActions();
        const auto end = std::find_if(actions.begin(), actions.end(), [](const Action& a) { return a.kind == "end_phase"; });
        require(end != actions.end(), "Opening peaceful pass must be legal");
        env.applyAction(*end);
    }
    require(env.currentNation() == "mongolia" && env.currentDecisionPlayer() == "comintern", "Mongolia turn was hidden or merged into CCP");
}

void entityObservationsAndRandomIsolation() {
    auto s = loadScenario(scenario);
    Engine engine = Engine::start(s, campaignRules(), 77);
    engine.setDiceTapeForTesting({1, 12, 6});
    CampaignEnv env(std::move(engine));
    const auto observed = canonicalJson(env.observation());
    const auto searched = env.cloneForSearch(456);
    require(canonicalJson(searched.observation()) == observed && searched.planningKey() == env.planningKey(), "Search RNG became a feature");
    require(searched.serialize() != env.serialize(), "Search execution identity reused actual dice");
    const auto features = env.observation();
    require(features.require("state").require("units").asObject().size() == 99, "Observation dropped setup entities");
    require(!features.require("state").find("history") && !features.require("state").find("definition_fingerprint"), "Execution metadata leaked into model state");
    require(env.context().require("geography").require("nodes").asObject().size() == 37, "Observation lost map graph");
    require(env.context().require("factions").require("mongolia").require("home_country_known").asBool(), "Home-country identity missing");
    require(env.context().require("catalog").asObject().size() == 5, "Unit registry was replaced by a flat toy encoding");
}

void reactionAndChanceEntitlements() {
    auto s = loadScenario(scenario);
    const auto action = politicalAction(s, "kmt", "test_reaction");
    queuePoliticalDecision(s, "kmt", "test_reaction", {action});
    CampaignEnv env(Engine(s, campaignRules(), 7));
    require(env.currentNation() == "ccp" && env.currentDecisionPlayer() == "allies", "Defender decision routed to calendar owner");
    require(env.decisionKind() == "test_reaction" && env.legalActions().size() == 1, "Pending reaction concealed");
    s.decisions.clear(); s.politics.pending.clear();
    s.chance = ChanceRequest{"test_die", "test_chance", "ccp", "test_chance", {DieSpec{12, 0, {}, 0}}};
    CampaignEnv chance(Engine(s, campaignRules(), 7));
    require(chance.decisionKind() == "chance" && !chance.currentDecisionPlayer() && chance.legalActions().empty(), "Dice were exposed as a player action");
    require(chance.observation().require("state").require("chance").require("dice").asArray().size() == 1, "Visible chance distribution missing");
}

void cachedPlanningKeysTrackEveryMutation() {
    const auto checkKey = [](const CampaignEnv& env, const std::string& message) {
        const auto actual = env.engine().planningKey();
        require(env.planningKey() == actual && env.planningKey() == actual, message);
        const auto& observed = env.observation();
        require(canonicalJson(observed.require("state")) == canonicalJson(env.engine().state().observation()),
                message + ": observation retained a different state");
        V::Array actions, interrupts;
        for (const auto& action : env.engine().legalActions()) actions.push_back(actionJson(action));
        for (const auto& action : env.engine().legalInterrupts()) interrupts.push_back(actionJson(action));
        require(canonicalJson(observed.require("legal_actions")) == canonicalJson(V(actions))
                && canonicalJson(observed.require("legal_interrupts")) == canonicalJson(V(interrupts)),
                message + ": observation retained a different legal menu");
        require(observed.require("decision_kind").asString() == env.decisionKind(),
                message + ": observation retained a different pending decision");
        auto withoutMenu = env.observationWithoutMenu()->asObject();
        require(!withoutMenu.contains("legal_actions"), message + ": numeric observation built the menu it replaces");
        withoutMenu.emplace("legal_actions", observed.require("legal_actions"));
        require(canonicalJson(V(std::move(withoutMenu))) == canonicalJson(observed),
                message + ": numeric observation differs from the public one");
    };
    const auto rejects = [](const std::function<void()>& operation) {
        try { operation(); } catch (const std::exception&) { return; }
        throw std::runtime_error("Expected rejected operation");
    };
    const auto choose = [](const std::vector<Action>& actions, const Id& kind) {
        const auto found = std::find_if(actions.begin(), actions.end(), [&](const Action& action) { return action.kind == kind; });
        require(found != actions.end(), "Missing planning-key test action: " + kind);
        return *found;
    };

    CampaignEnv env(scenario, 123);
    const auto checkpoint = env.serialize();
    const auto original = env.planningKey();
    checkKey(env, "Initial cached key differs from the engine");
    auto exact = env.clone();
    auto searched = env.cloneForSearch(987);
    require(exact.planningKey() == original && searched.planningKey() == original,
            "Clone or search reseeding changed decision identity");
    require(searched.serialize() != checkpoint, "Search clone did not isolate execution RNG");
    exact.applyAction(choose(exact.legalActions(), "end_phase"));
    checkKey(exact, "Action retained a stale planning key");
    require(exact.planningKey() != original && env.planningKey() == original && searched.planningKey() == original,
            "Clone key invalidation leaked into another environment");

    auto forged = choose(env.legalActions(), "end_phase");
    forged.id = "illegal_planning_key_test";
    rejects([&] { env.applyAction(forged); });
    rejects([&] { env.resolveChance(); });
    require(env.serialize() == checkpoint && env.planningKey() == original,
            "Rejected action/chance changed the cached planning state");

    const auto declarations = env.legalInterrupts();
    const auto declaration = std::find_if(declarations.begin(), declarations.end(), [](const Action& action) {
        return action.kind == "politics_declare_war" && action.nation == "kmt"
            && action.parameters.require("target").asString() == "japan";
    });
    require(declaration != declarations.end(), "No declaration available for planning-key invalidation");
    auto forgedInterrupt = *declaration;
    forgedInterrupt.player = "axis";
    rejects([&] { env.applyInterrupt(forgedInterrupt); });
    require(env.planningKey() == original && env.serialize() == checkpoint,
            "Rejected interrupt changed cached decision identity");
    env.applyInterrupt(*declaration);
    checkKey(env, "Interrupt retained a stale planning key");
    require(env.planningKey() != original, "Declaration did not change the planning state");
    const auto pending = env.serialize();
    const auto pendingKey = env.planningKey();
    rejects([&] { env.restore("invalid JSON checkpoint"); });
    require(env.serialize() == pending && env.planningKey() == pendingKey,
            "Rejected restore changed the cached planning state");
    env.restore(checkpoint);
    checkKey(env, "Restore retained a stale planning key");
    require(env.planningKey() == original, "Successful restore did not recover original decision identity");

    for (int phase = 0; phase < 4; ++phase) env.applyAction(choose(env.legalActions(), "end_phase"));
    env.applyAction(choose(env.legalActions(), "recruitment_roll"));
    require(env.decisionKind() == "chance", "Recruitment did not create a real chance request");
    const auto chanceKey = env.planningKey();
    checkKey(env, "Chance request retained a stale action key");
    env.resolveChance();
    checkKey(env, "Chance resolution retained a stale planning key");
    require(env.planningKey() != chanceKey, "Resolved chance retained its pending decision identity");
}

void observationsAreSharedOnlyForTheSameDecisionState() {
    CampaignEnv env(scenario, 123);
    const auto checkpoint = env.serialize();
    const auto* snapshot = &env.observation();
    const auto observed = canonicalJson(*snapshot);
    auto exact = env.clone();
    auto searched = env.cloneForSearch(987);
    require(&env.observation() == snapshot && &exact.observation() == snapshot
            && &searched.observation() == snapshot, "Unchanged clones rebuilt their observation");
    auto detached = env.observation();
    detached = V(O{{"poison", V(true)}});
    require(canonicalJson(env.observation()) == observed, "Caller altered the shared observation snapshot");
    auto forged = env.legalActions().back();
    forged.parameters = V(O{{"poison", V(true)}});
    try { env.applyAction(forged); throw std::logic_error("Expected forged action rejection"); }
    catch (const std::runtime_error&) {}
    require(&env.observation() == snapshot && env.serialize() == checkpoint,
            "Rejected action discarded an unchanged observation");
    env.applyAction(env.legalActions().back());
    require(&env.observation() != snapshot && canonicalJson(env.observation()) != observed,
            "Successful action retained its old observation snapshot");
    require(&exact.observation() == snapshot && &searched.observation() == snapshot
            && canonicalJson(*snapshot) == observed, "Mutation changed another clone's observation");
    env.restore(checkpoint);
    require(&env.observation() != snapshot && canonicalJson(env.observation()) == observed,
            "Restore retained the changed state observation");

    CampaignEnv cold(scenario, 777);
    auto left = cold.clone();
    auto right = cold.cloneForSearch(888);
    auto leftObservation = std::async(std::launch::async, [&] { return &left.observation(); });
    auto rightObservation = std::async(std::launch::async, [&] { return &right.observation(); });
    require(leftObservation.get() == rightObservation.get(),
            "Concurrent clones rebuilt their unchanged observation snapshot");
}

void setupValuesAndNoDoubleCounting() {
    auto s = loadScenario(scenario);
    const auto initial = allianceWealth(s);
    near(initial[0].paidConstruction, 10, "Opening queue paid amounts changed");
    near(initial[0].treasury, 15, "Opening treasury was debited historical payments");
    const auto first = std::find_if(s.units.begin(), s.units.end(), [](const auto& item) { return item.second.type == "torpedo_boat_destroyer"; });
    require(first != s.units.end(), "Missing setup-only ship");
    s.units.erase(first);
    near(initial[0].units - allianceWealth(s)[0].units, 5, "Unbuildable setup type lost approved price");
    auto bare = emptyAssets();
    UnitState battleship;
    battleship.id = "battleship"; battleship.type = "battleship"; battleship.owner = "japan";
    battleship.zone = battleship.turnOrigin = "sea_p15";
    battleship.movementAllowance = battleship.movementRemaining = 2;
    bare.units.emplace(battleship.id, battleship);
    auto& ship = bare.units.begin()->second;
    const auto undamaged = allianceWealth(bare)[0].units;
    ship.damage = 1;
    near(allianceWealth(bare)[0].units, undamaged, "Invented a capital ship damage discount despite free repair");
    UnitState crew;
    crew.id = "crew"; crew.owner = "japan"; crew.type = "militia"; crew.zone = crew.turnOrigin = "land_jap_honshu";
    crew.gameFlags["ship_crew:" + ship.id] = 1;
    bare.units.emplace(crew.id, crew);
    near(allianceWealth(bare)[0].units, undamaged, "Temporary crew was counted as another purchased asset");
}

void repairsRailAndNeutralAttribution() {
    auto s = emptyAssets();
    const auto healthyCity = allianceWealth(s)[0];
    s.territories.at("land_jap_tokyo").flags["city_damage"] = 20;
    const auto bombedCity = allianceWealth(s)[0];
    near(healthyCity.incomeRate - bombedCity.incomeRate, 1, "City bombing did not change the current legal income rate");
    near(healthyCity.infrastructure, bombedCity.infrastructure, "City label created a separately priced asset or repair deduction");
    s.territories.at("land_jap_tokyo").flags.clear();
    FacilityState factory;
    factory.id = "factory"; factory.type = "major_factory"; factory.zone = "land_jap_honshu"; factory.damage = 20;
    s.facilities.emplace(factory.id, factory);
    near(allianceWealth(s)[0].infrastructure, -2, "Negative surviving facility value was clamped");
    const auto before = allianceWealth(s)[0].total();
    *s.nations.at("japan").treasury -= 3;
    s.repairs.emplace("paid", RepairJob{"paid", "japan", "factory", 3, 0, false, std::nullopt});
    near(allianceWealth(s)[0].total(), before, "Prepaid repair lost both cash and repair value");
    auto captured = emptyAssets();
    captured.facilities.emplace("yard", FacilityState{"yard", "major_shipyard", "land_jap_honshu", 3});
    captured.repairs.emplace("old_repair", RepairJob{"old_repair", "japan", "yard", 3, 0, false, std::nullopt});
    near(allianceWealth(captured)[0].infrastructure, 10, "Current owner's prepaid repair was not credited");
    captured.territories.at("land_jap_honshu").possessor = "kmt";
    near(allianceWealth(captured)[1].infrastructure, 7, "Old owner's cancelled repair inflated the captured asset");
    auto railState = loadScenario(scenario);
    railState.units.clear(); railState.facilities.clear(); railState.construction.clear();
    require(!railState.rails.empty(), "No retained rail asset");
    const auto rail = railState.rails.begin()->second;
    railState.rails = {{rail.id, rail}};
    railState.territories.at(rail.endpointA).possessor = "japan";
    railState.territories.at(rail.endpointB).possessor = "kmt";
    const auto split = allianceWealth(railState);
    near(split[0].infrastructure, split[1].infrastructure, "Rail endpoint halves differ");
    railState.territories.at(rail.endpointB).possessor = "japan";
    near(allianceWealth(railState)[0].infrastructure, split[0].infrastructure * 2, "Same-side rail endpoints double-count border");
    const auto neutral = std::find_if(railState.nations.begin(), railState.nations.end(), [](const auto& x) { return x.first.rfind("warlord_", 0) == 0; })->first;
    railState.territories.at(rail.endpointB).possessor = neutral;
    near(allianceWealth(railState)[0].infrastructure, split[0].infrastructure, "Neutral endpoint granted free wealth");
    railState.rails.at(rail.id).damageByEndpoint[rail.endpointA] = 1;
    railState.repairs.emplace("rail_paid", RepairJob{"rail_paid", "japan", rail.id, 1, 0, false, rail.endpointA});
    const auto prepaidRail = allianceWealth(railState)[0].infrastructure;
    railState.territories.at(rail.endpointA).possessor = "kmt";
    near(allianceWealth(railState)[1].infrastructure, prepaidRail - 0.5,
         "Previous endpoint owner's cancelled rail repair inflated the new owner's half");
}

void terminalThreeVector() {
    auto s = loadScenario(scenario);
    const auto wealth = allianceWealth(s);
    const auto gaps = wealthGaps(s);
    for (std::size_t i = 0; i < 3; ++i)
        near(gaps[i], wealth[i].total() - wealth[(i + 1) % 3].total() - wealth[(i + 2) % 3].total(), "Wealth gap used a scalar or zero-sum substitute");
    near(gaps[0] + gaps[1] + gaps[2], -(wealth[0].total() + wealth[1].total() + wealth[2].total()), "General-sum identity changed");
    s.terminal = true;
    require(terminalReturns(s) == gaps, "Terminal returns do not use approved wealth");
}
}  // namespace

int main() {
    const std::vector<std::pair<std::string, std::function<void()>>> tests{
        {"explicit decisions and opponents", publicDecisionsAndNoAutomaticOpponents},
        {"registry observations and RNG separation", entityObservationsAndRandomIsolation},
        {"reaction and chance owner", reactionAndChanceEntitlements},
        {"planning key cache invalidation", cachedPlanningKeysTrackEveryMutation},
        {"observation snapshot reuse", observationsAreSharedOnlyForTheSameDecisionState},
        {"setup and temporary asset values", setupValuesAndNoDoubleCounting},
        {"repair/rail/neutral accounting", repairsRailAndNeutralAttribution},
        {"ordered general-sum returns", terminalThreeVector},
    };
    for (const auto& [name, run] : tests) {
        try { run(); std::cout << "PASS " << name << '\n'; }
        catch (const std::exception& e) { std::cerr << "FAIL " << name << ": " << e.what() << '\n'; return 1; }
    }
}
