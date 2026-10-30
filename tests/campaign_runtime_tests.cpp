#include "game/campaign.hpp"
#include "game/position_facts.hpp"

#include <algorithm>
#include <cmath>
#include <functional>
#include <future>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {
using namespace game::campaign;
using V = game::json::Value;
using O = V::Object;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}
template<class Function> void rejects(Function function, const std::string& message) {
    bool rejected = false;
    try { function(); } catch (const std::exception&) { rejected = true; }
    require(rejected, message);
}
void near(double actual, double expected) {
    require(std::abs(actual - expected) < 1e-12, "Incorrect hand-computed chance probability");
}

State initialState() {
    Definition definition;
    definition.scenarioId = "synthetic_m2_fixture";
    definition.geography = V(O{{"nodes", V(O{
        {"land_a", V(O{{"id", V(std::string("land_a"))}, {"type", V(std::string("land"))}})},
        {"land_b", V(O{{"id", V(std::string("land_b"))}, {"type", V(std::string("land"))}})}
    })}});
    definition.rules = V(O{{"synthetic_fixture_only", V(true)}});
    definition.turnOrder = {"ccp", "mongolia", "japan", "kmt"};
    definition.players = {"axis", "allies", "comintern"};
    for (const auto& id : definition.turnOrder) definition.factions[id] = FactionDefinition{id, id, {}};
    State state;
    state.definition = freezeDefinition(std::move(definition));
    for (const auto& id : state.definition->turnOrder) {
        NationState nation;
        nation.player = id == "japan" ? "axis" : id == "kmt" ? "allies" : "comintern";
        nation.alliance = nation.player;
        if (id != "mongolia") nation.treasury = 2;
        state.nations[id] = nation;
        state.completedTurns[id] = 0;
    }
    state.territories["land_a"] = TerritoryState{"ccp", {}};
    state.territories["land_b"] = TerritoryState{"japan", {}};
    state.captureTurnStart();
    state.validate();
    return state;
}

// Explicit synthetic rules exercise the foundation only. None of these
// fixture actions implements production, combat, movement or income rules.
class FixtureRules : public Rules {
  public:
    std::string identity {"synthetic_m2_rules_v1"};
    bool throwOnChance {false};
    bool missingIncome {false};
    bool finalPendingWork {false};
    bool moveOnBegin {false};
    bool moveOnInitialBegin {false};
    bool offerReservedAction {false};

    Id id() const override { return identity; }
    std::vector<Action> actions(const State& state) const override {
        std::vector<Action> actions;
        for (const auto& kind : {"mark", "request_chance", "request_reaction", "throw_after_mutation", "change_clock", "clear_battle"}) {
            Action action;
            action.id = kind;
            action.kind = kind;
            action.nation = state.currentNation();
            action.player = *state.nations.at(action.nation).player;
            action.parameters = V(O{{"value", V(7.0)}});
            actions.push_back(action);
        }
        if (offerReservedAction) { actions.front().id = "end_phase"; actions.front().kind = "end_phase"; }
        return actions;
    }
    bool phaseComplete(const State& state) const override {
        return !state.flags.contains("phase_blocked");
    }
    static Decision reaction(const Id& nation, const Id& player) {
        Decision decision;
        decision.id = "fixture_reaction";
        decision.kind = "synthetic_reaction";
        decision.nation = nation;
        decision.reaction = true;
        decision.continuation = "fixture_resume";
        Action option;
        option.id = "react";
        option.kind = "react";
        option.nation = nation;
        option.player = player;
        option.decision = decision.id;
        option.parameters = V(O{{"answer", V(3.0)}});
        decision.options.push_back(option);
        return decision;
    }
    static ChanceRequest chance(const Id& nation) {
        ChanceRequest request;
        request.id = "fixture_dice";
        request.purpose = "synthetic_probability_check";
        request.nation = nation;
        request.continuation = "fixture_resume";
        request.dice = {DieSpec{6, 2, {1}, 1}, DieSpec{12, -1, {}, 0}};
        return request;
    }
    void apply(State& state, const Action& action) const override {
        if (action.kind == "mark") ++state.flags["marks"];
        else if (action.kind == "request_chance") state.chance = chance(action.nation);
        else if (action.kind == "request_reaction") state.decisions.push_back(reaction("kmt", "allies"));
        else if (action.kind == "react") { state.decisions.pop_back(); ++state.flags["reactions"]; }
        else if (action.kind == "clear_battle") { state.battles.clear(); state.battleOrder.clear(); }
        else if (action.kind == "throw_after_mutation") { state.flags["bad_mutation"] = 1; throw std::runtime_error("Synthetic handler failure"); }
        else if (action.kind == "change_clock") state.clock.phase = Phase::Combat;
        else throw std::runtime_error("Unknown synthetic action");
    }
    void applyChance(State& state, const ChanceRequest& request, const ChanceOutcome& outcome) const override {
        const auto results = effectiveResults(request, outcome);
        state.flags["result"] = results.at(0) + results.at(1);
        if (throwOnChance) throw std::runtime_error("Synthetic chance failure");
    }
    void finishTurn(State& state) const override {
        ++state.flags["finished:" + state.currentNation()];
        if (!missingIncome) state.clock.incomeCollected = true;
        if (finalPendingWork && state.currentNation() == "kmt" && state.clock.roundIndex == 10
                && !state.flags.contains("final_work_created")) {
            state.flags["final_work_created"] = 1;
            state.chance = chance("kmt");
            state.decisions.push_back(reaction("japan", "axis"));
            BattleState battle;
            battle.id = "final_battle";
            battle.zone = "land_b";
            battle.attacker = "kmt";
            battle.defender = "japan";
            battle.stage = "fixture_pending";
            state.battles[battle.id] = battle;
            state.battleOrder.push_back(battle.id);
        }
    }
    void beginTurn(State& state) const override {
        ++state.flags["began:" + state.currentNation()];
        if (moveOnInitialBegin && state.currentNation() == "ccp") {
            state.territories.at("land_a").possessor = "kmt";
            state.units.at("ccp_unit").zone = "land_b";
        }
        if (moveOnBegin && state.currentNation() == "mongolia") {
            state.territories.at("land_a").possessor = "mongolia";
            state.units.at("mongolian_unit").zone = "land_b";
        }
    }
};

class CountingRules : public FixtureRules {
  public:
    mutable int actionCalls {0};
    mutable int interruptCalls {0};
    std::vector<Action> actions(const State& state) const override {
        ++actionCalls;
        auto actions = FixtureRules::actions(state);
        const auto mark = state.flags.find("marks");
        for (auto& action : actions)
            if (action.kind == "mark")
                action.parameters = V(O{{"value", V(mark == state.flags.end() ? 0.0 : double(mark->second))}});
        return actions;
    }
    std::vector<Action> interrupts(const State& state) const override {
        ++interruptCalls;
        if (state.flags.contains("interrupt_mark")) return {};
        Action action;
        action.id = action.kind = "interrupt_mark";
        action.nation = "kmt";
        action.player = "allies";
        action.parameters = V(O{{"value", V(1.0)}});
        return {action};
    }
    void apply(State& state, const Action& action) const override {
        if (action.kind == "interrupt_mark") ++state.flags["interrupt_mark"];
        else FixtureRules::apply(state, action);
    }
};

Action findAction(const Engine& engine, const std::string& kind) {
    const auto actions = engine.legalActions();
    const auto found = std::find_if(actions.begin(), actions.end(), [&](const Action& action) { return action.kind == kind; });
    require(found != actions.end(), "Missing legal action: " + kind);
    return *found;
}
bool hasAction(const Engine& engine, const std::string& kind) {
    const auto actions = engine.legalActions();
    return std::any_of(actions.begin(), actions.end(), [&](const Action& action) { return action.kind == kind; });
}
void endPhase(Engine& engine) { engine.step(findAction(engine, "end_phase")); }

void diceProbabilities() {
    ChanceRequest request;
    request.dice = {DieSpec{6, 0, {}, 0}, DieSpec{12, -2, {}, 0}};
    ChanceOutcome outcome{{{6}, {12}}};
    require(effectiveResults(request, outcome) == std::vector<int>({6, 10}), "D6/D12 modifiers wrong");
    near(outcomeProbability(request, outcome), 1.0 / 72);
    request.dice = {DieSpec{6, 3, {1}, 1}};
    near(outcomeProbability(request, ChanceOutcome{{{1, 6}}}), 1.0 / 36);
    near(outcomeProbability(request, ChanceOutcome{{{4}}}), 1.0 / 6);
    require(effectiveResults(request, ChanceOutcome{{{1, 6}}}) == std::vector<int>({9}), "Reroll modifier wrong");
    double total = 0;
    for (int face = 2; face <= 6; ++face) total += outcomeProbability(request, ChanceOutcome{{{face}}});
    for (int face = 1; face <= 6; ++face) total += outcomeProbability(request, ChanceOutcome{{{1, face}}});
    near(total, 1);
    request.dice = {DieSpec{12, 0, {}, 0}};
    total = 0;
    for (int face = 1; face <= 12; ++face) total += outcomeProbability(request, ChanceOutcome{{{face}}});
    near(total, 1);
}

void invalidDicePaths() {
    ChanceRequest request;
    request.dice = {DieSpec{6, 0, {1}, 1}};
    for (const auto& faces : std::vector<std::vector<int>>{{}, {1}, {2, 3}, {1, 1, 2}, {0}, {7}})
        rejects([&] { effectiveResults(request, ChanceOutcome{{faces}}); }, "Invalid reroll path accepted");
    rejects([&] { outcomeProbability(request, ChanceOutcome{}); }, "Wrong dice count accepted");
    request.dice[0].rerollFaces = {7};
    rejects([&] { effectiveResults(request, ChanceOutcome{{{2}}}); }, "Invalid reroll face accepted");
    request.dice = {DieSpec{6, std::numeric_limits<int>::max(), {}, 0}};
    rejects([&] { effectiveResults(request, ChanceOutcome{{{6}}}); }, "Modified result overflow accepted");
}

void randomStreamsAndExactCounters() {
    auto random = RandomStreams::seeded(123);
    auto baseline = random;
    random.active = "search";
    for (int i = 0; i < 40; ++i) random.roll(12);
    require(random.actual == baseline.actual && random.training == baseline.training, "Search consumed another RNG stream");
    random.active = "training";
    for (int i = 0; i < 30; ++i) random.roll(6);
    require(random.actual == baseline.actual, "Training consumed actual RNG");
    random.active = "actual";
    for (int i = 0; i < 40; ++i) require(random.roll(12) == baseline.roll(12), "Actual RNG sequence changed");
    random.actual = std::numeric_limits<std::uint64_t>::max();
    const auto encoded = random.toJson();
    require(encoded.require("actual").asString() == "18446744073709551615", "RNG state lost uint64 precision");
    auto restored = RandomStreams::fromJson(game::json::parse(canonicalJson(encoded)));
    require(canonicalJson(restored.toJson()) == canonicalJson(encoded), "RNG round trip changed state");
    for (int i = 0; i < 20; ++i) require(random.roll(6) == restored.roll(6), "Restored RNG future differs");
    auto bad = encoded.asObject();
    bad["actual"] = V(std::string("18446744073709551616"));
    rejects([&] { RandomStreams::fromJson(V(bad)); }, "Counter overflow accepted");
    bad["actual"] = V(1.0);
    rejects([&] { RandomStreams::fromJson(V(bad)); }, "Floating RNG counter accepted");
    bad["actual"] = V(std::string("01"));
    rejects([&] { RandomStreams::fromJson(V(bad)); }, "Noncanonical counter accepted");
}

void tapesAreTestOnlyAndExact() {
    auto rules = std::make_shared<FixtureRules>();
    Engine engine(initialState(), rules, 1);
    const auto observation = canonicalJson(engine.state().observation());
    const auto key = engine.planningKey();
    const auto exact = engine.exactReplayIdentity();
    engine.setDiceTapeForTesting({1, 6, 12, 5, 3});
    require(engine.planningKey() == key && canonicalJson(engine.state().observation()) == observation, "Future test dice leaked into policy inputs");
    require(engine.exactReplayIdentity() != exact, "Exact execution identity omitted test tape");
    engine.step(findAction(engine, "request_chance"));
    engine.resolveChance();
    require(engine.state().flags.at("result") == 19, "Controlled reroll/modifier result wrong");
    auto restored = Engine::restore(engine.state().definition, rules, engine.serialize());
    for (auto* branch : {&engine, &restored}) {
        branch->step(findAction(*branch, "request_chance"));
        branch->resolveChance();
    }
    require(engine.exactReplayIdentity() == restored.exactReplayIdentity(), "Tape cursor restore changed future");
    engine.step(findAction(engine, "request_chance"));
    const auto before = engine.serialize();
    rejects([&] { engine.resolveChance(); }, "Exhausted tape silently fell back to random");
    require(engine.serialize() == before, "Exhausted tape changed execution state");
}

void directActionsCannotBypassLegality() {
    auto rules = std::make_shared<FixtureRules>();
    auto state = initialState();
    state.flags["phase_blocked"] = 1;
    Engine engine(state, rules);
    require(!hasAction(engine, "end_phase"), "Incomplete phase offered end action");
    auto legal = findAction(engine, "mark");
    std::vector<Action> invalid;
    auto action = legal; action.player = "axis"; invalid.push_back(action);
    action = legal; action.nation = "japan"; invalid.push_back(action);
    action = legal; action.decision = "invented"; invalid.push_back(action);
    action = legal; action.parameters = V(O{{"value", V(8.0)}}); invalid.push_back(action);
    action = legal; action.kind = "unlisted"; invalid.push_back(action);
    action = legal; action.id = "other"; invalid.push_back(action);
    action = legal; action.id = "end_phase"; action.kind = "end_phase"; action.parameters = V(O{}); invalid.push_back(action);
    const auto before = engine.serialize();
    for (const auto& forged : invalid) {
        rejects([&] { engine.step(forged); }, "Forged direct action accepted");
        require(engine.serialize() == before, "Rejected action changed engine");
    }
    engine.step(legal);
    require(engine.state().flags.at("marks") == 1, "Listed action failed");
    rules->offerReservedAction = true;
    rejects([&] { engine.legalActions(); }, "Rules could forge reserved phase action");
    rejects([&] { Engine(initialState(), nullptr); }, "Missing rules module was permissive");
}

void handlerFailuresRollbackStateAndRandom() {
    auto rules = std::make_shared<FixtureRules>();
    Engine engine(initialState(), rules, 99);
    const auto before = engine.serialize();
    rejects([&] { engine.step(findAction(engine, "throw_after_mutation")); }, "Throwing handler did not reject");
    require(engine.serialize() == before, "Throwing handler mutation committed");
    rejects([&] { engine.step(findAction(engine, "change_clock")); }, "Handler bypassed phase clock");
    require(engine.serialize() == before, "Clock bypass mutation committed");
    engine.step(findAction(engine, "request_chance"));
    const auto pending = engine.serialize();
    rules->throwOnChance = true;
    rejects([&] { engine.resolveChance(); }, "Throwing chance handler accepted");
    require(engine.serialize() == pending, "Failed chance consumed actual RNG/state");
    rejects([&] { engine.applyChanceOutcome(engine.planningKey(), ChanceOutcome{{{2}, {7}}}); },
            "Throwing explicit chance handler accepted");
    require(engine.serialize() == pending, "Failed explicit chance changed RNG/state");
    rules->throwOnChance = false;
    auto restored = Engine::restore(engine.state().definition, rules, pending);
    engine.resolveChance(); restored.resolveChance();
    require(engine.serialize() == restored.serialize(), "Chance rollback changed deterministic future");
}

void explicitChanceOutcomesMatchRulesWithoutConsumingRandom() {
    auto rules = std::make_shared<FixtureRules>();
    Engine explicitEngine(initialState(), rules, 765);
    rejects([&] { explicitEngine.applyChanceOutcome(explicitEngine.planningKey(), ChanceOutcome{}); },
            "Explicit outcome accepted without a pending chance request");
    explicitEngine.step(findAction(explicitEngine, "request_chance"));
    const auto pending = explicitEngine.serialize();
    const auto key = explicitEngine.planningKey();
    const auto randomBefore = game::json::parse(pending).require("random");
    const ChanceOutcome valid{{{1, 5}, {7}}};
    rejects([&] { explicitEngine.applyChanceOutcome("old decision", valid); }, "Stale explicit outcome accepted");
    const std::vector<ChanceOutcome> invalid{
        ChanceOutcome{}, ChanceOutcome{{{1}, {7}}}, ChanceOutcome{{{2, 5}, {7}}},
        ChanceOutcome{{{7}, {7}}}, ChanceOutcome{{{1, 5, 6}, {7}}}, ChanceOutcome{{{2}, {0}}},
    };
    for (const auto& outcome : invalid) {
        rejects([&] { explicitEngine.applyChanceOutcome(key, outcome); }, "Malformed explicit dice accepted");
        require(explicitEngine.serialize() == pending, "Rejected explicit dice changed state/history/RNG");
    }
    auto sampled = explicitEngine.clone();
    sampled.setDiceTapeForTesting({1, 5, 7});
    sampled.resolveChance();
    explicitEngine.applyChanceOutcome(key, valid);
    require(canonicalJson(explicitEngine.state().toJson()) == canonicalJson(sampled.state().toJson()),
            "Explicit and sampled outcomes apply different rules/history");
    require(canonicalJson(game::json::parse(explicitEngine.serialize()).require("random")) == canonicalJson(randomBefore),
            "Explicit chance consumed execution RNG");
    require(explicitEngine.state().flags.at("result") == 13, "Explicit rerolls/modifiers were not applied");
    const auto after = explicitEngine.serialize();
    rejects([&] { explicitEngine.applyChanceOutcome(key, valid); }, "An outcome could be applied twice");
    require(explicitEngine.serialize() == after, "Repeated outcome changed completed state");
}

void defenderDecisionPausesClock() {
    auto rules = std::make_shared<FixtureRules>();
    Engine engine(initialState(), rules);
    engine.step(findAction(engine, "request_reaction"));
    require(engine.state().currentNation() == "ccp" && engine.state().decisionPlayer() == "allies", "Defender decision was routed to attacker");
    require(engine.legalActions().size() == 1 && !hasAction(engine, "end_phase"), "Pending decision did not suspend ordinary actions");
    auto action = findAction(engine, "react");
    auto forged = action; forged.player = "comintern";
    rejects([&] { engine.step(forged); }, "Attacker answered defender choice");
    engine.step(action);
    require(engine.state().decisions.empty() && engine.state().clock.phase == Phase::Production
            && engine.state().currentNation() == "ccp", "Reaction advanced national clock");
}

void fivePhasesAndElevenFullRounds() {
    auto rules = std::make_shared<FixtureRules>();
    Engine engine = Engine::start(initialState(), rules);
    const std::vector<Phase> phases = {Phase::Production, Phase::CombatMovement, Phase::Combat, Phase::NonCombatMovement, Phase::PlaceUnits};
    for (int round = 0; round < 11; ++round) {
        for (const auto& nation : engine.state().definition->turnOrder) {
            for (const auto phase : phases) {
                require(!engine.state().terminal && engine.state().currentNation() == nation && engine.state().clock.phase == phase, "Five-phase national ordering changed");
                endPhase(engine);
            }
        }
    }
    require(engine.state().terminal && engine.state().clock.completedRounds == 11 && engine.state().clock.playerTurnSerial == 44, "Calendar ended before eleven complete national rounds");
    require(engine.state().calendarDate() == std::pair<int, int>{1941, 7}, "Terminal date is not July 1941");
    require(engine.legalActions().empty(), "Terminal campaign still offered actions");
    for (const auto& nation : engine.state().definition->turnOrder) {
        require(engine.state().completedTurns.at(nation) == 11 && engine.state().flags.at("finished:" + nation) == 11, "Income/accounting hook was skipped or repeated");
        require(engine.state().flags.at("began:" + nation) == 11, "Initial or later beginTurn hook was skipped/repeated");
        if (engine.state().nations.at(nation).treasury) require(*engine.state().nations.at(nation).treasury == 2, "Foundation invented income");
    }
}

void freshCampaignStartAndRestoreBoundary() {
    auto rules = std::make_shared<FixtureRules>();
    rules->moveOnInitialBegin = true;
    auto state = initialState();
    UnitState unit;
    unit.id = "ccp_unit"; unit.owner = "ccp"; unit.type = "fixture_unit";
    unit.zone = "land_a"; unit.turnOrigin = "land_b"; unit.route = {"land_b", "land_a"};
    unit.movementAllowance = 3; unit.movementRemaining = 0;
    unit.turnFlags["used"] = 1; unit.commitments.insert("spent");
    state.units[unit.id] = unit;
    state.nations.at("ccp").turnFlags["used"] = 1;
    auto engine = Engine::start(state, rules, 42);
    require(engine.state().flags.at("began:ccp") == 1, "Fresh initial nation did not begin once");
    require(engine.state().turnStart.possessions.at("land_a") == "ccp"
            && engine.state().turnStart.units.at(unit.id).second == "land_a", "Initial snapshot followed hook effects");
    require(engine.state().territories.at("land_a").possessor == "kmt"
            && engine.state().units.at(unit.id).zone == "land_b", "Initial beginTurn effects were skipped");
    require(engine.state().units.at(unit.id).movementRemaining == 3
            && engine.state().units.at(unit.id).turnFlags.empty()
            && engine.state().units.at(unit.id).commitments.empty(), "Initial active turn state was not reset");
    require(!state.flags.contains("began:ccp") && state.units.at(unit.id).zone == "land_a", "Start mutated its input state");
    auto restored = Engine::restore(engine.state().definition, rules, engine.serialize());
    auto replayed = Engine::replay(engine.state().definition, rules, engine.serialize(), {});
    auto clone = engine.clone();
    auto search = engine.cloneForSearch(12);
    Engine wrapped(engine.state().clone(), rules);
    for (const auto* branch : {&restored, &replayed, &clone, &search, &wrapped}) {
        require(branch->state().flags.at("began:ccp") == 1, "Restore/clone/wrap re-ran beginTurn");
        require(branch->state().flags.at("__campaign_started") == 1, "Restore/clone/wrap dropped runtime start marker");
    }
    require(restored.serialize() == engine.serialize() && replayed.serialize() == engine.serialize(), "Initial checkpoint round trip changed execution");
    rejects([&] { Engine::start(engine.state().clone(), rules); }, "Already started state was started twice");
}

void startRejectsNonFreshState() {
    auto rules = std::make_shared<FixtureRules>();
    auto state = initialState();
    state.clock.phase = Phase::CombatMovement;
    rejects([&] { Engine::start(state, rules); }, "Mid-phase state accepted as fresh campaign");
    state = initialState();
    state.decisions.push_back(FixtureRules::reaction("kmt", "allies"));
    rejects([&] { Engine::start(state, rules); }, "Pending reaction accepted at fresh start");
    state = initialState();
    state.chance = FixtureRules::chance("ccp");
    rejects([&] { Engine::start(state, rules); }, "Pending chance accepted at fresh start");
    state = initialState();
    state.history.push_back(Event{"fixture", V(O{}), "previous"});
    rejects([&] { Engine::start(state, rules); }, "Historical state accepted as fresh campaign");
}

void accountingFailureAndTurnStartSnapshot() {
    auto rules = std::make_shared<FixtureRules>();
    auto state = initialState();
    state.clock.phase = Phase::PlaceUnits;
    UnitState unit;
    unit.id = "mongolian_unit"; unit.owner = "mongolia"; unit.type = "fixture_unit";
    unit.zone = "land_a"; unit.turnOrigin = "land_a"; unit.route = {"land_a"};
    unit.movementAllowance = 2; unit.movementRemaining = 0;
    unit.turnFlags["used"] = 1; unit.gameFlags["keep"] = 1; unit.commitments.insert("spent");
    state.units[unit.id] = unit;
    state.nations.at("mongolia").turnFlags["used"] = 1;
    Engine engine(state, rules);
    rules->missingIncome = true;
    const auto before = engine.serialize();
    rejects([&] { endPhase(engine); }, "Missing income completion accepted");
    require(engine.serialize() == before, "Failed finishTurn changed clock/accounting");
    rules->missingIncome = false;
    rules->moveOnBegin = true;
    endPhase(engine);
    require(engine.state().currentNation() == "mongolia", "Next national slot wrong");
    require(engine.state().turnStart.possessions.at("land_a") == "ccp"
            && engine.state().turnStart.units.at(unit.id).second == "land_a", "Snapshot was taken after beginTurn effects");
    const auto& reset = engine.state().units.at(unit.id);
    require(reset.zone == "land_b" && reset.movementRemaining == 2 && reset.turnFlags.empty()
            && reset.commitments.empty() && reset.route.empty() && reset.gameFlags.at("keep") == 1, "Per-turn unit reset lost persistent state");
}

void finalPendingWorkPreventsDeadline() {
    auto rules = std::make_shared<FixtureRules>();
    rules->finalPendingWork = true;
    Engine engine(initialState(), rules);
    for (int step = 0; step < 219; ++step) endPhase(engine);
    engine.setDiceTapeForTesting({2, 12});
    endPhase(engine);
    require(!engine.state().terminal && engine.state().clock.incomeCollected && engine.state().clock.playerTurnSerial == 43, "Deadline ignored post-collection work");
    require(engine.legalActions().empty(), "Pending chance offered policy action");
    engine.resolveChance();
    require(engine.state().decisionPlayer() == "axis" && !hasAction(engine, "end_phase"), "Final defender reaction was skipped");
    engine.step(findAction(engine, "react"));
    require(!hasAction(engine, "end_phase"), "Unresolved battle did not hold final turn");
    engine.step(findAction(engine, "clear_battle"));
    endPhase(engine);
    require(engine.state().terminal && engine.state().flags.at("finished:kmt") == 11
            && engine.state().clock.playerTurnSerial == 44, "Final turn was collected twice or never completed");
}

void replayAndRestoreAreExact() {
    auto rules = std::make_shared<FixtureRules>();
    Engine engine(initialState(), rules, 456);
    engine.step(findAction(engine, "mark"));
    engine.setDiceTapeForTesting({1, 6, 12});
    const auto checkpoint = engine.serialize();
    const auto historyOffset = engine.state().history.size();
    engine.step(findAction(engine, "request_chance")); engine.resolveChance(); endPhase(engine);
    const std::vector<Event> events(engine.state().history.begin() + historyOffset, engine.state().history.end());
    auto replayed = Engine::replay(engine.state().definition, rules, checkpoint, events);
    require(replayed.exactReplayIdentity() == engine.exactReplayIdentity(), "Action/chance replay was not exact");
    auto restored = Engine::restore(engine.state().definition, rules, engine.serialize());
    require(restored.serialize() == engine.serialize(), "Engine restore lost execution/history state");
    auto wrongRules = std::make_shared<FixtureRules>(); wrongRules->identity = "other_rules";
    rejects([&] { Engine::restore(engine.state().definition, wrongRules, checkpoint); }, "Rules-ID mismatch accepted");
    auto tampered = events; tampered.back().afterStateKey = "divergence";
    rejects([&] { Engine::replay(engine.state().definition, rules, checkpoint, tampered); }, "Replay state divergence accepted");
    tampered = events;
    auto payload = tampered[1].payload.asObject();
    payload["outcome"] = outcomeJson(ChanceOutcome{{{2}, {12}}}); tampered[1].payload = V(payload);
    rejects([&] { Engine::replay(engine.state().definition, rules, checkpoint, tampered); }, "Replay chance divergence accepted");
}

void cloneAndSearchRandomnessAreIsolated() {
    auto rules = std::make_shared<FixtureRules>();
    Engine engine(initialState(), rules, 555);
    engine.setDiceTapeForTesting({6, 12});
    const auto original = engine.serialize();
    auto clone = engine.clone();
    require(clone.state().definition == engine.state().definition, "Clone copied immutable definition");
    clone.step(findAction(clone, "mark"));
    require(engine.serialize() == original && clone.planningKey() != engine.planningKey(), "Mutable clone state leaked");
    auto search = engine.cloneForSearch(999);
    require(search.planningKey() == engine.planningKey() && search.exactReplayIdentity() != engine.exactReplayIdentity(), "Planning key includes future random state");
    const auto searchBefore = game::json::parse(search.serialize()).require("random");
    require(searchBefore.require("test_tape").asArray().empty(), "Search inherited future controlled dice");
    search.step(findAction(search, "request_chance")); search.resolveChance();
    const auto searchAfter = game::json::parse(search.serialize()).require("random");
    require(searchBefore.require("actual").asString() == searchAfter.require("actual").asString()
            && searchBefore.require("training").asString() == searchAfter.require("training").asString()
            && searchBefore.require("search").asString() != searchAfter.require("search").asString(), "Search clone consumed wrong RNG stream");
    require(engine.serialize() == original, "Search execution changed actual game");
    auto state = engine.state().clone();
    const auto key = state.planningKey();
    state.history.push_back(Event{"fixture_history", V(O{}), "fixture"});
    require(state.planningKey() == key && state.serialize() != engine.state().serialize(), "Planning key did not distinguish history from decision state");
}

void decisionMenusAreReusedAndTransactional() {
    auto rules = std::make_shared<CountingRules>();
    Engine engine(initialState(), rules, 555);
    const auto checkpoint = engine.serialize();
    const auto mark = findAction(engine, "mark");
    auto exposed = engine.legalActions();
    auto branch = engine.cloneForSearch(654);
    branch.legalActions();
    engine.setDiceTapeForTesting({6, 12});
    engine.legalActions();
    require(rules->actionCalls == 1, "Unchanged states, clones or RNG reseeding regenerated actions");
    exposed.front().parameters = V(O{{"poison", V(true)}});
    require(canonicalJson(actionJson(findAction(engine, "mark"))) == canonicalJson(actionJson(mark)),
            "A caller changed the authoritative cached action payload");
    auto forged = mark;
    forged.parameters = V(O{{"value", V(1.0)}});
    const auto before = engine.serialize();
    rejects([&] { engine.step(forged); }, "Cached ID bypassed full payload validation");
    rejects([&] { engine.step(findAction(engine, "throw_after_mutation")); }, "Throwing handler accepted");
    require(engine.serialize() == before && rules->actionCalls == 1,
            "Rejected input discarded or poisoned an unchanged decision cache");
    branch.step(mark);
    require(rules->actionCalls == 1, "Applying a previously generated action rebuilt its menu");
    const auto changed = findAction(branch, "mark");
    require(rules->actionCalls == 2 && changed.parameters.require("value").asInt() == 1,
            "Successful action retained a stale menu");
    engine.legalActions();
    require(rules->actionCalls == 2 && !engine.state().flags.contains("marks"),
            "Clone mutation invalidated or changed its parent cache");
    rejects([&] { branch.step(mark); }, "An old action payload remained legal after state changed");
    require(rules->actionCalls == 2, "Stale payload validation regenerated an available menu");

    const auto interrupts = engine.legalInterrupts();
    engine.legalInterrupts();
    require(rules->interruptCalls == 1 && interrupts.size() == 1, "Interrupts were generated repeatedly");
    auto forgedInterrupt = interrupts.front();
    forgedInterrupt.parameters = V(O{{"value", V(2.0)}});
    rejects([&] { engine.interrupt(forgedInterrupt); }, "Cached interrupt ID bypassed payload validation");
    engine.interrupt(interrupts.front());
    require(rules->interruptCalls == 1, "Interrupt validation rebuilt its menu");
    require(engine.legalInterrupts().empty() && rules->interruptCalls == 2,
            "Successful interrupt retained a stale menu");

    auto restored = Engine::restore(engine.state().definition, rules, checkpoint);
    restored.legalActions();
    require(rules->actionCalls == 3, "Restore inherited another state's action cache");
    restored.step(findAction(restored, "request_chance"));
    require(restored.legalActions().empty(), "Chance retained an ordinary action menu");
    restored.setDiceTapeForTesting({6, 12});
    restored.resolveChance();
    restored.legalActions();
    require(rules->actionCalls == 4, "Resolved chance did not invalidate its empty menu");
    endPhase(restored);
    restored.legalActions();
    require(rules->actionCalls == 5 && restored.state().clock.phase == Phase::CombatMovement,
            "Phase transition retained the preceding phase menu");

    auto sharedRules = std::make_shared<CountingRules>();
    Engine cold(initialState(), sharedRules);
    auto left = cold.clone();
    auto right = cold.cloneForSearch(42);
    auto leftActions = std::async(std::launch::async, [&] { return left.legalActions(); });
    auto rightActions = std::async(std::launch::async, [&] { return right.legalActions(); });
    require(leftActions.get().size() == rightActions.get().size() && sharedRules->actionCalls == 1,
            "Concurrent clones regenerated their shared unchanged menu");
}

void runtimeStateKeysFollowEveryMutationAndIgnoreLoadedEventKeys() {
    const auto expected=[](const Engine& engine) {
        return contentDigest(canonicalJson(V(O{{"rules_id",V(engine.rulesId())},
            {"state_key",V(engine.state().planningKey())}})));
    };
    const auto checkKey=[&](const Engine& engine,bool finalEvent) {
        require(engine.planningKey()==expected(engine),"Cached runtime key differs from complete decision state");
        require(engine.planningKey()==expected(engine),"Repeated runtime key changed");
        if(finalEvent)require(engine.state().history.back().afterStateKey==engine.state().planningKey(),
            "Final runtime event key does not describe the committed state");
    };
    auto rules=std::make_shared<CountingRules>();
    auto engine=Engine::start(initialState(),rules,41);
    checkKey(engine,false);  // Start hooks finish before the first cached key.
    const auto original=engine.planningKey();
    auto branch=engine.cloneForSearch(73);
    require(branch.planningKey()==original,"Search RNG reseeding changed cached state identity");
    engine.step(findAction(engine,"mark"));checkKey(engine,true);
    require(engine.planningKey()!=original && branch.planningKey()==original,"Key cache leaked across a clone mutation");
    engine.interrupt(engine.legalInterrupts().front());checkKey(engine,true);
    engine.step(findAction(engine,"request_chance"));checkKey(engine,true);
    const auto chanceKey=engine.planningKey();
    engine.setDiceTapeForTesting({2,12});
    require(engine.planningKey()==chanceKey,"Future test tape changed decision identity");
    engine.resolveChance();checkKey(engine,true);
    endPhase(engine);checkKey(engine,true);
    const auto beforeFailure=engine.planningKey();
    rejects([&]{engine.step(findAction(engine,"throw_after_mutation"));},"Throwing mutation was committed");
    require(engine.planningKey()==beforeFailure,"Failed action changed the prior key cache");

    auto encoded=game::json::parse(engine.serialize()).asObject();
    auto state=encoded.at("state").asObject();auto history=state.at("history").asArray();
    auto event=history.back().asObject();event["after_state_key"]=V("untrusted historical key");
    history.back()=V(std::move(event));state["history"]=V(std::move(history));encoded["state"]=V(std::move(state));
    const auto restored=Engine::restore(engine.state().definition,rules,canonicalJson(V(std::move(encoded))));
    checkKey(restored,false);
    require(restored.planningKey()==engine.planningKey(),"Restore trusted a loaded historical key");
    auto externallyPrepared=engine.state().clone();externallyPrepared.flags["prepared_outside_runtime"]=1;
    Engine wrapped(std::move(externallyPrepared),rules);
    checkKey(wrapped,false);
    require(wrapped.planningKey()!=engine.planningKey(),"Wrapping a state reused a stale historical key");

    Engine cold(initialState(),rules);auto left=cold.clone();auto right=cold.cloneForSearch(91);
    auto first=std::async(std::launch::async,[&]{return left.planningKey();});
    auto second=std::async(std::launch::async,[&]{return right.planningKey();});
    require(first.get()==second.get() && cold.planningKey()==expected(cold),"Concurrent cold clone keys diverged");
}

void menuSourceKeysShareExactFeaturesAndNeverAuthorizeActions() {
    const auto verify=[](const std::vector<Action>& actions) {
        for(const auto& action:actions) {
            require(action.neuralSourceKey && *action.neuralSourceKey==canonicalJson(actionJson(action)),
                "Derived action source key omits or changes a public feature");
            const auto external=actionFromJson(actionJson(action));
            require(!external.neuralSourceKey && canonicalJson(actionJson(external))==*action.neuralSourceKey,
                "Derived source metadata leaked into external action features");
        }
    };
    auto rules=std::make_shared<CountingRules>();
    Engine engine(initialState(),rules,92);
    const auto actions=engine.legalActions();verify(actions);
    auto branch=engine.clone();const auto repeated=branch.legalActions();
    for(std::size_t i=0;i<actions.size();++i)
        require(actions[i].neuralSourceKey==repeated[i].neuralSourceKey,"Unchanged clone copied derived source bytes");
    const auto mark=findAction(engine,"mark");
    auto forged=mark;forged.parameters=V(O{{"value",V(999.0)}});
    rejects([&]{engine.step(forged);},"A retained source key authorized a forged action payload");
    auto alteredMetadata=mark;alteredMetadata.neuralSourceKey=std::make_shared<const std::string>("external derived metadata");
    engine.step(alteredMetadata);branch.step(mark);
    require(engine.serialize()==branch.serialize(),"Derived source metadata changed rule execution or history");
    const auto changed=findAction(engine,"mark");
    require(changed.id==mark.id && *changed.neuralSourceKey!=*mark.neuralSourceKey,
        "Same action ID with changed parameters reused stale source bytes");
    const auto interrupts=engine.legalInterrupts();verify(interrupts);
    engine.interrupt(interrupts.front());
    engine.step(findAction(engine,"request_reaction"));
    const auto pending=engine.legalActions();verify(pending);
    require(pending.front().decision && pending.front().player=="allies",
        "Source-key fixture lost its defender decision metadata");
}

void reachedMenusAreSharedAcrossClonesAndBounded() {
    auto rules = std::make_shared<CountingRules>();
    Engine engine(initialState(), rules, 777);
    const auto mark = findAction(engine, "mark");
    auto left = engine.cloneForSearch(1);
    auto right = engine.cloneForSearch(2);
    left.step(mark);
    const auto reached = left.legalActions();
    right.step(mark);
    const auto again = right.legalActions();
    require(rules->actionCalls == 2, "A clone regenerated a menu another clone built for the same decision state");
    require(reached.size() == again.size(), "Clones reaching one state received different menus");
    for (std::size_t i = 0; i < reached.size(); ++i)
        require(reached[i].neuralSourceKey == again[i].neuralSourceKey, "A shared menu copied or changed its source bytes");
    auto forged = findAction(right, "mark");
    forged.parameters = V(O{{"value", V(999.0)}});
    rejects([&] { right.step(forged); }, "A shared menu authorized a forged payload");
    right.step(findAction(right, "mark"));
    require(rules->actionCalls == 2 && right.state().flags.at("marks") == 2,
            "Validating against a shared menu rebuilt it or misapplied the action");
    Engine independent(initialState(), rules, 777);
    independent.legalActions();
    require(rules->actionCalls == 3, "Separately constructed engines shared a menu table");
    auto walker = engine.cloneForSearch(3);
    for (int step = 0; step < 200; ++step) walker.step(findAction(walker, "mark"));
    const auto beforeRevisit = rules->actionCalls;
    auto revisit = engine.cloneForSearch(4);
    revisit.step(mark);
    revisit.legalActions();
    require(rules->actionCalls == beforeRevisit + 1, "The shared menu table retained unbounded old menus");
}

// Transitions reread only the history they add, so rules may only append to it.
class HistoryRules : public FixtureRules {
  public:
    std::vector<Action> actions(const State& state) const override {
        auto actions = FixtureRules::actions(state);
        auto option = actions.front();
        for (const auto& kind : {"append_event", "append_nonfinite", "rebuild_history", "clear_history", "corrupt_state"}) {
            option.id = option.kind = kind;
            actions.push_back(option);
        }
        return actions;
    }
    std::vector<Action> interrupts(const State&) const override {
        Action action;
        action.id = action.kind = "interrupt_after_mutation";
        action.nation = "kmt";
        action.player = "allies";
        action.parameters = V(O{});
        return {action};
    }
    void apply(State& state, const Action& action) const override {
        if (action.kind == "append_event") state.history.push_back(Event{"audit", V(O{{"value", V(1.0)}}), "key"});
        else if (action.kind == "interrupt_after_mutation") {
            state.flags["bad_mutation"] = 1;
            throw std::runtime_error("Synthetic interrupt failure");
        }
        // As the economy rules do, read the action after removing the decision that held it.
        else if (action.kind == "react") { state.decisions.pop_back(); ++state.flags["reacted:" + action.kind]; }
        else if (action.kind == "append_nonfinite")
            state.history.push_back(Event{"audit", V(O{{"value", V(std::numeric_limits<double>::infinity())}}), "key"});
        else if (action.kind == "rebuild_history") {
            const std::vector<Event> events = state.history;
            state.history.clear();
            for (const auto& event : events) state.history.push_back(event);
        }
        else if (action.kind == "clear_history") state.history.clear();
        else if (action.kind == "corrupt_state") state.nations.at("ccp").treasury = -1;
        else FixtureRules::apply(state, action);
    }
};

void transitionsCheckAddedHistoryAndEverythingElse() {
    auto rules = std::make_shared<HistoryRules>();
    Engine engine(initialState(), rules, 31);
    engine.step(findAction(engine, "mark"));
    engine.step(findAction(engine, "append_event"));
    require(engine.state().history.size() == 3 && engine.state().history[1].kind == "audit"
            && engine.state().history[2].kind == "action", "Rules' events lost their place before the action's");
    const auto before = engine.serialize();
    for (const auto& kind : {"append_nonfinite", "rebuild_history", "clear_history", "corrupt_state"}) {
        rejects([&] { engine.step(findAction(engine, kind)); }, std::string("Transition accepted ") + kind);
        require(engine.serialize() == before, "A rejected transition changed the engine");
        auto search = engine.cloneForSearch(5);
        rejects([&] { search.step(findAction(search, kind)); }, std::string("Search transition accepted ") + kind);
    }
    engine.step(findAction(engine, "append_event"));
    require(engine.state().history.size() == 5, "A rejected transition stopped later ones");
}

void refusesEveryCall(Engine& failed) {
    Action action;
    action.id = action.kind = "mark";
    const std::vector<std::function<void()>> calls{
        [&] { failed.state(); }, [&] { failed.rulesId(); }, [&] { failed.legalActions(); },
        [&] { failed.legalInterrupts(); }, [&] { failed.step(action); }, [&] { failed.interrupt(action); },
        [&] { failed.resolveChance(); }, [&] { failed.applyChanceOutcome("key", ChanceOutcome{{{2}, {7}}}); },
        [&] { failed.clone(); }, [&] { failed.cloneForSearch(1); }, [&] { failed.setDiceTapeForTesting({1}); },
        [&] { failed.serialize(); }, [&] { failed.exactReplayIdentity(); }, [&] { failed.planningKey(); },
        [&] { auto copy = failed; copy.state(); }};
    for (const auto& call : calls) {
        std::string message;
        try { call(); } catch (const std::exception& error) { message = error.what(); }
        require(message == "Search copy failed during a transition", "A failed search copy answered a call: " + message);
    }
}

void searchCopiesRefuseEveryCallAfterFailingMidTransition() {
    auto rules = std::make_shared<HistoryRules>();
    Engine engine(initialState(), rules, 81);
    engine.step(findAction(engine, "mark"));
    const auto checkpoint = engine.serialize();
    const auto key = engine.planningKey();
    for (const auto& kind : {"throw_after_mutation", "change_clock", "append_nonfinite", "clear_history", "corrupt_state"}) {
        auto search = engine.cloneForSearch(3);
        rejects([&] { search.step(findAction(search, kind)); }, std::string("Search copy accepted ") + kind);
        refusesEveryCall(search);
    }
    auto interrupted = engine.cloneForSearch(4);
    rejects([&] { interrupted.interrupt(interrupted.legalInterrupts().front()); }, "Search copy accepted a failing interrupt");
    refusesEveryCall(interrupted);

    auto pending = engine.clone();
    pending.step(findAction(pending, "request_chance"));
    rules->throwOnChance = true;
    auto rolled = pending.cloneForSearch(5);
    rejects([&] { rolled.resolveChance(); }, "Search copy accepted a failing chance handler");
    refusesEveryCall(rolled);
    auto explicitOutcome = pending.cloneForSearch(6);
    rejects([&] { explicitOutcome.applyChanceOutcome(explicitOutcome.planningKey(), ChanceOutcome{{{2}, {7}}}); },
            "Search copy accepted a failing explicit chance handler");
    refusesEveryCall(explicitOutcome);
    rules->throwOnChance = false;

    require(engine.serialize() == checkpoint && engine.planningKey() == key, "A failed search copy changed its source");
    auto fresh = engine.cloneForSearch(7);
    fresh.step(findAction(fresh, "mark"));
    require(fresh.state().flags.at("marks") == 2, "A failed search copy spoiled later copies");
}

void searchCopiesStayUsableAfterRejections() {
    auto rules = std::make_shared<HistoryRules>();
    Engine engine(initialState(), rules, 82);
    auto search = engine.cloneForSearch(3);
    const auto before = search.serialize();
    auto forged = findAction(search, "mark");
    forged.parameters = V(O{{"value", V(999.0)}});
    rejects([&] { search.step(forged); }, "Search copy accepted a forged action");
    rejects([&] { search.interrupt(forged); }, "Search copy accepted a forged interrupt");
    rejects([&] { search.resolveChance(); }, "Search copy resolved absent chance");
    rejects([&] { search.applyChanceOutcome(search.planningKey(), ChanceOutcome{{{2}, {7}}}); }, "Search copy applied absent chance");
    require(search.serialize() == before, "A rejected call changed a search copy");
    search.step(findAction(search, "request_chance"));
    const auto pending = search.serialize();
    rejects([&] { search.applyChanceOutcome("stale key", ChanceOutcome{{{2}, {7}}}); }, "Search copy applied a stale outcome");
    rejects([&] { search.applyChanceOutcome(search.planningKey(), ChanceOutcome{{{2}, {99}}}); }, "Search copy applied an impossible outcome");
    require(search.serialize() == pending, "A rejected outcome changed a search copy");
    search.resolveChance();
    require(search.state().flags.contains("result"), "A rejection stopped a search copy");
}

void searchCopiesMatchEnginesThatRollBack() {
    auto rules = std::make_shared<HistoryRules>();
    Engine engine(initialState(), rules, 83);
    auto inPlace = engine.cloneForSearch(3);
    auto copying = inPlace.clone();
    const auto both = [&](const std::function<void(Engine&)>& change) {
        change(inPlace);
        change(copying);
        require(inPlace.serialize() == copying.serialize() && inPlace.planningKey() == copying.planningKey(),
                "Changing a search copy in place differs from swapping in a copy");
    };
    const auto mark = [](Engine& next) { next.step(findAction(next, "mark")); };
    const auto chance = [](Engine& next) { next.step(findAction(next, "request_chance")); };
    both(mark);
    both([](Engine& next) { next.step(findAction(next, "request_reaction")); });
    // The action passed here lives inside the decision that the rules remove.
    both([](Engine& next) { next.step(next.state().decisions.back().options.front()); });
    require(inPlace.state().flags.at("reacted:react") == 1, "Rules lost the action they were applying");
    both(chance);
    both([](Engine& next) { next.resolveChance(); });
    both(chance);
    both([](Engine& next) { next.applyChanceOutcome(next.planningKey(), ChanceOutcome{{{2}, {7}}}); });
    for (int phase = 0; phase < 12; ++phase) both(endPhase);

    const auto snapshot = copying.serialize();
    rejects([&] { copying.step(findAction(copying, "throw_after_mutation")); }, "Throwing handler accepted");
    require(copying.serialize() == snapshot, "A plain copy of a search copy lost its rollback");
    both(mark);
}

void eventLogCopiesShareEventsAndStayIndependent() {
    EventLog log;
    log.push_back(Event{"first", V(O{{"n", V(1.0)}}), "k1"});
    log.push_back(Event{"second", V(O{}), "k2"});
    auto copy = log;
    copy.push_back(Event{"third", V(O{}), "k3"});
    require(log.size() == 2 && copy.size() == 3 && &log[0] == &copy[0], "Copies must share recorded events");
    require(log.back().kind == "second" && copy.back().kind == "third", "Appending to a copy changed the original");
    const std::vector<Event> tail(copy.begin() + 1, copy.end());
    require(tail.size() == 2 && tail.front().kind == "second" && tail.back().afterStateKey == "k3",
            "Random-access iteration differs from the recorded order");
    const std::vector<Event> all = copy;
    require(all.size() == 3 && all.front().payload.require("n").asInt() == 1, "Conversion to events differs");
    copy.clear();
    require(copy.empty() && log.size() == 2, "Clearing a copy cleared the original");
}

void positionFactsAreScopedToOneUnchangedState() {
    auto state = initialState();
    auto other = state;
    require(!positionFacts(state), "Facts exist without a scope");
    int computed = 0;
    const auto answer = [&] { ++computed; return true; };
    {
        const PositionScope scope(state);
        auto* facts = positionFacts(state);
        require(facts && !positionFacts(other), "Facts must belong to the exact State object");
        facts->remember(PositionFacts::Fact::SeaBlockaded, "a", "b", answer);
        facts->remember(PositionFacts::Fact::SeaBlockaded, "a", "b", answer);
        facts->remember(PositionFacts::Fact::SeaBlockaded, "a", "c", answer);
        facts->remember(PositionFacts::Fact::InSupply, "a", "b", answer);
        require(computed == 3, "A remembered answer was recomputed or different keys were conflated");
        {
            const PositionScope reuse(state);
            require(positionFacts(state) == facts, "A nested scope for the same State must reuse its facts");
            const PositionScope probe(other);
            require(positionFacts(other) && positionFacts(other) != facts && positionFacts(state) == facts,
                    "Nested scopes must keep each State's own facts");
        }
        require(positionFacts(state) == facts && !positionFacts(other), "Closing nested scopes lost or leaked facts");
    }
    require(!positionFacts(state), "Facts outlived their scope");
}

}  // namespace

int main() {
    const std::vector<std::pair<std::string, std::function<void()>>> tests = {
        {"dice probabilities", diceProbabilities}, {"invalid dice paths", invalidDicePaths},
        {"RNG stream isolation and uint64 round trip", randomStreamsAndExactCounters},
        {"test tape isolation and exact cursor", tapesAreTestOnlyAndExact},
        {"direct action validation", directActionsCannotBypassLegality},
        {"handler rollback", handlerFailuresRollbackStateAndRandom},
        {"explicit chance parity and RNG isolation", explicitChanceOutcomesMatchRulesWithoutConsumingRandom},
        {"defender reaction routing", defenderDecisionPausesClock},
        {"five phases and eleven complete rounds", fivePhasesAndElevenFullRounds},
        {"fresh campaign start and restore boundary", freshCampaignStartAndRestoreBoundary},
        {"fresh campaign start guards", startRejectsNonFreshState},
        {"accounting and turn-start snapshot", accountingFailureAndTurnStartSnapshot},
        {"final pending work", finalPendingWorkPreventsDeadline},
        {"exact replay and restore", replayAndRestoreAreExact},
        {"clone and search isolation", cloneAndSearchRandomnessAreIsolated},
        {"decision menu reuse and invalidation", decisionMenusAreReusedAndTransactional},
        {"state key reuse and invalidation", runtimeStateKeysFollowEveryMutationAndIgnoreLoadedEventKeys},
        {"action source reuse and authoritative validation", menuSourceKeysShareExactFeaturesAndNeverAuthorizeActions},
        {"reached menus shared across clones and bounded", reachedMenusAreSharedAcrossClonesAndBounded},
        {"transitions check added history and everything else", transitionsCheckAddedHistoryAndEverythingElse},
        {"failed search copies refuse every call", searchCopiesRefuseEveryCallAfterFailingMidTransition},
        {"rejections leave search copies usable", searchCopiesStayUsableAfterRejections},
        {"search copies match engines that roll back", searchCopiesMatchEnginesThatRollBack},
        {"event log copies share events", eventLogCopiesShareEventsAndStayIndependent},
        {"position facts scoped to one state", positionFactsAreScopedToOneUnchangedState},
    };
    for (const auto& [name, test] : tests) {
        try { test(); std::cout << "PASS " << name << '\n'; }
        catch (const std::exception& error) { std::cerr << "FAIL " << name << ": " << error.what() << '\n'; return 1; }
    }
    std::cout << tests.size() << " synthetic campaign runtime checks passed\n";
}
