#include "game/campaign.hpp"
#include "game/catalog.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <limits>
#include <mutex>
#include <stdexcept>

namespace game::campaign {
namespace {
using V = json::Value;
using O = V::Object;
using A = V::Array;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

std::uint64_t nextRandom(std::uint64_t& state) {
    std::uint64_t value = (state += UINT64_C(0x9e3779b97f4a7c15));
    value = (value ^ (value >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
    value = (value ^ (value >> 27)) * UINT64_C(0x94d049bb133111eb);
    return value ^ (value >> 31);
}

std::uint64_t counter(const V& value) {
    const auto& text = value.asString();
    require(!text.empty() && (text.size() == 1 || text.front() != '0'), "Invalid execution counter");
    std::uint64_t result = 0;
    const auto [end, error] = std::from_chars(text.data(), text.data() + text.size(), result);
    require(error == std::errc{} && end == text.data() + text.size(), "Invalid execution counter");
    return result;
}

void validateStream(const std::string& stream) {
    require(stream == "actual" || stream == "search" || stream == "training", "Unknown random stream");
}

void validateDie(const DieSpec& die) {
    require(die.sides >= 2 && die.maxRerolls >= 0, "Invalid die sides or reroll count");
    for (int face : die.rerollFaces) require(face > 0 && face <= die.sides, "Invalid conditional reroll face");
}

bool workClear(const State& state) {
    return state.decisions.empty() && !state.chance && state.battles.empty() && state.battleOrder.empty();
}

bool sameClock(const Clock& a, const Clock& b, bool ignoreIncome = false) {
    return a.roundIndex == b.roundIndex && a.nationIndex == b.nationIndex
        && a.phase == b.phase && a.completedRounds == b.completedRounds
        && a.playerTurnSerial == b.playerTurnSerial
        && (ignoreIncome || a.incomeCollected == b.incomeCollected);
}

void checkHookClock(const State& state, const Clock& before, bool terminal, bool ignoreIncome = false) {
    require(sameClock(state.clock, before, ignoreIncome) && state.terminal == terminal,
            "Rules hooks must not advance the campaign clock or terminal state");
}

bool phaseWorkClear(const State& state) {
    const auto immediate = state.flags.find("immediate_land_battles");
    if (immediate != state.flags.end() && immediate->second) return false;
    const auto naval = state.flags.find("immediate_naval_battles");
    if (naval != state.flags.end() && naval->second) return false;
    if (workClear(state)) return true;
    if (state.clock.phase != Phase::CombatMovement || !state.decisions.empty() || state.chance) return false;
    for (const auto& [id,battle] : state.battles)
        if (battle.stage != "awaiting_combat_rules" && battle.stage != "air_declared"
                && battle.stage != "naval_declared" && battle.stage != "amphibious_declared") return false;
    return true;
}

Action endPhaseAction(const State& state, const Id& player) {
    Action action;
    action.id = "end_phase";
    action.kind = "end_phase";
    action.player = player;
    action.nation = state.currentNation();
    return action;
}

bool reserved(const Action& action) {
    return action.id == "end_phase" || action.kind == "end_phase";
}

void increment(int& value, const std::string& name) {
    require(value < std::numeric_limits<int>::max(), name + " overflow");
    ++value;
}

void prepareTurnStart(State& state) {
    const auto active = state.currentNation();
    state.nations.at(active).turnFlags.clear();
    for (auto& [id, unit] : state.units) {
        if (unit.owner != active) continue;
        unit.turnFlags.clear();
        unit.commitments.clear();
        unit.turnOrigin = unit.zone;
        unit.route.clear();
        if(state.definition->catalog) {
            unit.movementAllowance=state.definition->catalog->stats(
                unit.type,unit.damage,catalogContext(state,unit.owner,unit.zone)).movement;
        }
        unit.movementRemaining = unit.movementAllowance;
    }
    state.captureTurnStart();
}

}  // namespace

struct Engine::ActionMenu {
    std::vector<Action> actions;
    std::map<Id, std::string> canonicalById;
};

struct Engine::DecisionCache {
    std::mutex mutex;
    std::shared_ptr<const ActionMenu> actions;
    std::shared_ptr<const ActionMenu> interrupts;
};

void Engine::invalidateDecisionCache() {
    decisionCache_ = std::make_shared<DecisionCache>();
}

RandomStreams RandomStreams::seeded(std::uint64_t seed) {
    RandomStreams result;
    result.actual = nextRandom(seed);
    result.search = nextRandom(seed);
    result.training = nextRandom(seed);
    return result;
}

int RandomStreams::roll(int sides) {
    require(sides > 0, "Die must have positive sides");
    validateStream(active);
    if (!testTape.empty()) {
        require(tapePosition < testTape.size(), "Test dice tape exhausted");
        const int face = testTape[tapePosition];
        require(face > 0 && face <= sides, "Test dice tape face outside die range");
        ++tapePosition;
        return face;
    }
    require(tapePosition == 0, "Empty test dice tape has nonzero position");
    auto& state = active == "actual" ? actual : active == "search" ? search : training;
    const auto bound = static_cast<std::uint64_t>(sides);
    const auto threshold = -bound % bound;
    std::uint64_t value;
    do { value = nextRandom(state); } while (value < threshold);
    return static_cast<int>(value % bound) + 1;
}

V RandomStreams::toJson() const {
    validateStream(active);
    require(tapePosition <= testTape.size(), "Invalid test dice tape position");
    A tape;
    for (int face : testTape) {
        require(face > 0, "Invalid test dice tape face");
        tape.emplace_back(static_cast<double>(face));
    }
    return V(O{{"actual", V(std::to_string(actual))}, {"search", V(std::to_string(search))},
               {"training", V(std::to_string(training))}, {"active", V(active)},
               {"test_tape", V(std::move(tape))}, {"tape_position", V(std::to_string(tapePosition))}});
}

RandomStreams RandomStreams::fromJson(const V& value) {
    require(value.asObject().size() == 6, "Invalid random stream fields");
    RandomStreams result;
    result.actual = counter(value.require("actual"));
    result.search = counter(value.require("search"));
    result.training = counter(value.require("training"));
    result.active = value.require("active").asString();
    validateStream(result.active);
    for (const auto& face : value.require("test_tape").asArray()) {
        const int number = face.asInt();
        require(number > 0, "Invalid test dice tape face");
        result.testTape.push_back(number);
    }
    const auto position = counter(value.require("tape_position"));
    require(position <= result.testTape.size(), "Invalid test dice tape position");
    result.tapePosition = static_cast<std::size_t>(position);
    return result;
}

std::vector<int> effectiveResults(const ChanceRequest& request, const ChanceOutcome& outcome) {
    require(outcome.faces.size() == request.dice.size(), "Chance outcome has wrong dice count");
    std::vector<int> result;
    for (std::size_t index = 0; index < request.dice.size(); ++index) {
        const auto& die = request.dice[index];
        const auto& faces = outcome.faces[index];
        validateDie(die);
        require(!faces.empty() && faces.size() - 1 <= static_cast<std::size_t>(die.maxRerolls),
                "Chance outcome has invalid reroll count");
        for (std::size_t roll = 0; roll < faces.size(); ++roll) {
            require(faces[roll] > 0 && faces[roll] <= die.sides, "Chance face outside die range");
            const bool mustReroll = die.rerollFaces.contains(faces[roll])
                && roll < static_cast<std::size_t>(die.maxRerolls);
            require(mustReroll == (roll + 1 < faces.size()), "Chance outcome violates conditional reroll");
        }
        const auto effective = static_cast<long long>(faces.back()) + die.modifier;
        require(effective >= std::numeric_limits<int>::min() && effective <= std::numeric_limits<int>::max(),
                "Modified die result overflow");
        result.push_back(static_cast<int>(effective));
    }
    return result;
}

double outcomeProbability(const ChanceRequest& request, const ChanceOutcome& outcome) {
    (void)effectiveResults(request, outcome);
    double probability = 1;
    for (std::size_t index = 0; index < request.dice.size(); ++index)
        for (std::size_t roll = 0; roll < outcome.faces[index].size(); ++roll)
            probability /= request.dice[index].sides;
    return probability;
}

Engine::Engine(State initial, std::shared_ptr<const Rules> rules, std::uint64_t seed)
    : state_(std::move(initial)), rules_(std::move(rules)), random_(RandomStreams::seeded(seed)),
      decisionCache_(std::make_shared<DecisionCache>()) {
    require(rules_ && !rules_->id().empty(), "Campaign execution requires an explicit rules module");
    state_.validate();
}

Engine Engine::start(State initial, std::shared_ptr<const Rules> rules, std::uint64_t seed) {
    Engine result(std::move(initial), std::move(rules), seed);
    const auto& clock = result.state_.clock;
    require(!result.state_.terminal && clock.roundIndex == 0 && clock.nationIndex == 0
            && clock.phase == Phase::Production && clock.completedRounds == 0
            && clock.playerTurnSerial == 0 && !clock.incomeCollected
            && result.state_.history.empty() && workClear(result.state_)
            && !result.state_.flags.contains("__campaign_started"), "Campaign start requires a fresh state");
    for (const auto& [nation, count] : result.state_.completedTurns)
        require(count == 0, "Campaign start has completed national turns");
    // The __ prefix is reserved for runtime bookkeeping. Keep this marker in
    // state so a fresh-position restore cannot accidentally begin twice.
    result.state_.flags["__campaign_started"] = 1;
    prepareTurnStart(result.state_);
    const auto before = result.state_.clock;
    result.rules_->beginTurn(result.state_);
    checkHookClock(result.state_, before, false);
    result.state_.validate();
    return result;
}

std::shared_ptr<const Engine::ActionMenu> Engine::actionMenu() const {
    std::lock_guard lock(decisionCache_->mutex);
    if (decisionCache_->actions) return decisionCache_->actions;
    auto menu = std::make_shared<ActionMenu>();
    const auto finish = [&]() -> std::shared_ptr<const ActionMenu> {
        decisionCache_->actions = menu;
        return menu;
    };
    if (state_.terminal || state_.chance) return finish();
    const auto player = state_.decisionPlayer();
    if (!player) return finish();
    const bool decisionPending = !state_.decisions.empty();
    auto& actions = menu->actions;
    actions = decisionPending ? state_.decisions.back().options : rules_->actions(state_);
    const auto immediate = state_.flags.find("immediate_land_battles");
    if (!decisionPending && immediate != state_.flags.end() && immediate->second)
        actions.erase(std::remove_if(actions.begin(), actions.end(), [](const Action& action) {
            return action.kind != "land_begin_battle" && action.kind != "land_progress_battle";
        }), actions.end());
    std::set<Id> ids;
    for (const auto& action : actions) {
        require(!action.id.empty() && !action.kind.empty() && !reserved(action), "Rules action uses an empty or reserved identity");
        require(action.parameters.isObject(), "Action parameters must be an object");
        require(ids.insert(action.id).second, "Rules actions have duplicate IDs");
        require(action.player == *player, "Rules action routes to wrong player");
        if (decisionPending) {
            const auto& decision = state_.decisions.back();
            require(action.nation == decision.nation && action.decision == decision.id,
                    "Rules action does not match pending decision");
        } else {
            require(state_.nations.contains(action.nation),"Rules action names an unknown nation");
            const auto &nation=state_.nations.at(action.nation);
            const bool directAxis=action.nation=="dadao" && state_.currentNation()=="japan" &&
                nation.gameFlags.contains("direct_axis_control_after_japan_surrender") &&
                nation.gameFlags.at("direct_axis_control_after_japan_surrender")!=0;
            require((action.nation == state_.currentNation() ||
                     controlledBy(state_,action.nation,state_.currentNation()) || directAxis) && !action.decision,
                    "Rules action does not match active nation");
        }
        menu->canonicalById.emplace(action.id, canonicalJson(actionJson(action)));
    }
    if (!decisionPending && phaseWorkClear(state_) && rules_->phaseComplete(state_)) {
        actions.push_back(endPhaseAction(state_, *player));
        const auto& action = actions.back();
        menu->canonicalById.emplace(action.id, canonicalJson(actionJson(action)));
    }
    return finish();
}

std::vector<Action> Engine::legalActions() const {
    return actionMenu()->actions;
}

void Engine::step(const Action& action) {
    const auto proposed = canonicalJson(actionJson(action));
    const auto menu = actionMenu();
    const auto found = menu->canonicalById.find(action.id);
    require(found != menu->canonicalById.end() && found->second == proposed, "Illegal campaign action");
    Engine next = clone();
    next.invalidateDecisionCache();
    if (reserved(action)) next.endPhase();
    else {
        const auto before = next.state_.clock;
        const bool terminal = next.state_.terminal;
        next.rules_->apply(next.state_, action);
        checkHookClock(next.state_, before, terminal);
    }
    next.state_.validate();
    next.state_.history.push_back(Event{"action", actionJson(action), next.state_.planningKey()});
    *this = std::move(next);
}

std::shared_ptr<const Engine::ActionMenu> Engine::interruptMenu() const {
    std::lock_guard lock(decisionCache_->mutex);
    if (decisionCache_->interrupts) return decisionCache_->interrupts;
    auto menu = std::make_shared<ActionMenu>();
    const auto finish = [&]() -> std::shared_ptr<const ActionMenu> {
        decisionCache_->interrupts = menu;
        return menu;
    };
    if(state_.terminal||state_.chance)return finish();
    const auto immediate = state_.flags.find("immediate_land_battles");
    if (immediate != state_.flags.end() && immediate->second) return finish();
    const auto naval = state_.flags.find("immediate_naval_battles");
    if (naval != state_.flags.end() && naval->second) return finish();
    auto& actions=menu->actions;
    actions=rules_->interrupts(state_);
    std::set<Id> ids;
    for(const auto& action:actions) {
        require(!reserved(action)&&!action.id.empty()&&ids.insert(action.id).second,
                "Invalid political interrupt identity");
        require(state_.nations.contains(action.nation)&&state_.nations.at(action.nation).player==action.player,
                "Interrupt entitlement mismatch");
        require(!action.decision&&action.parameters.isObject(),"Invalid interrupt payload");
        menu->canonicalById.emplace(action.id, canonicalJson(actionJson(action)));
    }
    return finish();
}

std::vector<Action> Engine::legalInterrupts() const {
    return interruptMenu()->actions;
}

void Engine::interrupt(const Action& action) {
    const auto proposed=canonicalJson(actionJson(action));
    const auto menu=interruptMenu();
    const auto found=menu->canonicalById.find(action.id);
    require(found!=menu->canonicalById.end()&&found->second==proposed, "Illegal campaign interrupt");
    auto next=clone();
    next.invalidateDecisionCache();
    const auto before=next.state_.clock;
    const bool beforeTerminal=next.state_.terminal;
    next.rules_->apply(next.state_,action);
    checkHookClock(next.state_,before,beforeTerminal);
    next.state_.validate();
    next.state_.history.push_back(Event{"interrupt",actionJson(action),next.state_.planningKey()});
    *this=std::move(next);
}

void Engine::resolveChance() {
    require(!state_.terminal && state_.chance.has_value(), "No pending campaign chance request");
    Engine next = clone();
    next.invalidateDecisionCache();
    const ChanceRequest request = *next.state_.chance;
    ChanceOutcome outcome;
    for (const auto& die : request.dice) {
        validateDie(die);
        std::vector<int> faces;
        for (int count = 0;; ++count) {
            const int face = next.random_.roll(die.sides);
            faces.push_back(face);
            if (!die.rerollFaces.contains(face) || count == die.maxRerolls) break;
        }
        outcome.faces.push_back(std::move(faces));
    }
    (void)effectiveResults(request, outcome);
    const auto before = next.state_.clock;
    const bool terminal = next.state_.terminal;
    next.state_.chance.reset();
    next.rules_->applyChance(next.state_, request, outcome);
    checkHookClock(next.state_, before, terminal);
    next.state_.validate();
    next.state_.history.push_back(Event{"chance", V(O{{"request_id", V(request.id)}, {"outcome", outcomeJson(outcome)}}), next.state_.planningKey()});
    *this = std::move(next);
}

void Engine::endPhase() {
    require(phaseWorkClear(state_) && rules_->phaseComplete(state_), "Campaign phase is not complete");
    const auto beforePhase=state_.clock;
    const bool beforeTerminal=state_.terminal;
    rules_->finishPhase(state_);
    checkHookClock(state_,beforePhase,beforeTerminal);
    if(!phaseWorkClear(state_))return;
    switch (state_.clock.phase) {
        case Phase::Production: state_.clock.phase = Phase::CombatMovement; return;
        case Phase::CombatMovement: state_.clock.phase = Phase::Combat; return;
        case Phase::Combat: state_.clock.phase = Phase::NonCombatMovement; return;
        case Phase::NonCombatMovement: state_.clock.phase = Phase::PlaceUnits; return;
        case Phase::PlaceUnits: break;
    }
    if (!state_.clock.incomeCollected) {
        const auto before = state_.clock;
        const bool terminal = state_.terminal;
        rules_->finishTurn(state_);
        checkHookClock(state_, before, terminal, true);
        require(state_.clock.incomeCollected, "Rules finishTurn did not complete income/accounting");
    }
    if (!workClear(state_)) return;
    increment(state_.completedTurns[state_.currentNation()], "Completed national turns");
    require(state_.clock.playerTurnSerial < std::numeric_limits<std::uint64_t>::max(), "Player turn serial overflow");
    ++state_.clock.playerTurnSerial;
    const auto& order = state_.definition->turnOrder;
    if (state_.clock.nationIndex + 1 == static_cast<int>(order.size())) {
        increment(state_.clock.completedRounds, "Completed calendar rounds");
        if (state_.clock.completedRounds == state_.definition->calendarRounds) {
            state_.terminal = true;
            return;
        }
        ++state_.clock.roundIndex;
        state_.clock.nationIndex = 0;
    } else ++state_.clock.nationIndex;
    state_.clock.phase = Phase::Production;
    state_.clock.incomeCollected = false;
    prepareTurnStart(state_);
    const auto before = state_.clock;
    const bool terminal = state_.terminal;
    rules_->beginTurn(state_);
    checkHookClock(state_, before, terminal);
}

Engine Engine::clone() const { return *this; }

Engine Engine::cloneForSearch(std::uint64_t seed) const {
    Engine result = clone();
    result.random_.search = RandomStreams::seeded(seed).search;
    result.random_.active = "search";
    result.random_.testTape.clear();
    result.random_.tapePosition = 0;
    return result;
}

void Engine::setDiceTapeForTesting(std::vector<int> tape) {
    for (int face : tape) require(face > 0, "Invalid test dice tape face");
    random_.testTape = std::move(tape);
    random_.tapePosition = 0;
}

std::string Engine::serialize() const {
    return canonicalJson(V(O{{"schema_version", V(1.0)}, {"rules_id", V(rules_->id())},
                             {"state", state_.toJson()}, {"random", random_.toJson()}}));
}

Engine Engine::restore(std::shared_ptr<const Definition> definition, std::shared_ptr<const Rules> rules,
                       const std::string& serialized) {
    const auto value = json::parse(serialized);
    require(value.asObject().size() == 4 && value.require("schema_version").asNumber() == 1, "Invalid engine checkpoint schema");
    require(rules && value.require("rules_id").asString() == rules->id(), "Checkpoint rules module mismatch");
    Engine result(State::fromJson(std::move(definition), value.require("state")), std::move(rules));
    result.random_ = RandomStreams::fromJson(value.require("random"));
    return result;
}

Engine Engine::replay(std::shared_ptr<const Definition> definition, std::shared_ptr<const Rules> rules,
                      const std::string& checkpoint, const std::vector<Event>& events) {
    Engine result = restore(std::move(definition), std::move(rules), checkpoint);
    for (std::size_t first = 0; first < events.size();) {
        // Rules may emit deterministic audit effects before the input event
        // that caused them. Apply that input once, then verify its whole batch;
        // effects are evidence, never independent commands or policy choices.
        std::size_t input = first;
        while (input < events.size() && events[input].kind == "unit_destruction") ++input;
        require(input < events.size(), "Replay audit effects have no causing input event");
        const auto& event = events[input];
        const auto historyOffset = result.state_.history.size();
        if (event.kind == "action") result.step(actionFromJson(event.payload));
        else if (event.kind == "interrupt") result.interrupt(actionFromJson(event.payload));
        else if (event.kind == "chance") result.resolveChance();
        else throw std::runtime_error("Unknown replay event kind");
        const auto count = input - first + 1;
        require(result.state_.history.size() == historyOffset + count, "Campaign replay audit batch divergence");
        for (std::size_t offset = 0; offset < count; ++offset) {
            const auto& expected = events[first + offset];
            const auto& actual = result.state_.history[historyOffset + offset];
            require(actual.kind == expected.kind && canonicalJson(actual.payload) == canonicalJson(expected.payload)
                    && actual.afterStateKey == expected.afterStateKey, "Campaign replay divergence");
        }
        first = input + 1;
    }
    return result;
}

std::string Engine::exactReplayIdentity() const { return contentDigest(serialize()); }

std::string Engine::planningKey() const {
    return contentDigest(canonicalJson(V(O{{"rules_id", V(rules_->id())}, {"state_key", V(state_.planningKey())}})));
}

}  // namespace game::campaign
