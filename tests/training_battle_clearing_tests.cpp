#include "game/campaign_actions.hpp"
#include "game/campaign_env.hpp"
#include "game/catalog.hpp"
#include "game/naval.hpp"

#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <random>
#include <stdexcept>

namespace {
using namespace game::campaign;
using V = game::json::Value;
using O = V::Object;

void check(bool condition, const std::string &message) {
  if (!condition)
    throw std::runtime_error(message);
}

// The training profile without its settle step, which is how it worked before
// finished battles were cleared automatically.
class WithoutSettle final : public Rules {
public:
  explicit WithoutSettle(std::shared_ptr<const Rules> rules) : rules_(std::move(rules)) {}
  Id id() const override { return rules_->id(); }
  std::vector<Action> actions(const State &s) const override { return rules_->actions(s); }
  std::vector<Action> interrupts(const State &s) const override { return rules_->interrupts(s); }
  bool phaseComplete(const State &s) const override { return rules_->phaseComplete(s); }
  void apply(State &s, const Action &a) const override { rules_->apply(s, a); }
  void applyChance(State &s, const ChanceRequest &r, const ChanceOutcome &o) const override {
    rules_->applyChance(s, r, o);
  }
  void finishTurn(State &s) const override { rules_->finishTurn(s); }
  void beginTurn(State &s) const override { rules_->beginTurn(s); }
  void finishPhase(State &s) const override { rules_->finishPhase(s); }

private:
  std::shared_ptr<const Rules> rules_;
};

bool marked(const std::map<Id, int> &flags, const Id &key) {
  const auto found = flags.find(key);
  return found != flags.end() && found->second != 0;
}

bool clearsFinishedBattle(const State &state, const Action &action) {
  if (action.kind == "naval_finish_battle")
    return true;
  if (action.kind != "land_progress_battle")
    return false;
  const auto found = state.battles.find(action.parameters.require("battle").asString());
  return found != state.battles.end() && marked(found->second.flags, "finished");
}

std::vector<std::string> menuText(const std::vector<Action> &actions) {
  std::vector<std::string> out;
  for (const auto &action : actions)
    out.push_back(canonicalJson(actionJson(action)));
  return out;
}

std::string positionText(const Engine &engine) {
  return canonicalJson(engine.state().toJson(false));
}

std::string randomText(const Engine &engine) {
  return canonicalJson(game::json::parse(engine.serialize()).require("random"));
}

// Clicks every clearing the reference offers, as the training profile now does
// itself, and checks that no declaration opportunity disappears by never
// stopping at the uncleared position.
int clearLikeTraining(Engine &reference) {
  int clicks = 0;
  for (int guard = 0; guard < 256; ++guard) {
    if (reference.state().terminal || reference.state().chance)
      return clicks;
    const auto actions = reference.legalActions();
    const auto clearing = std::find_if(actions.begin(), actions.end(), [&](const Action &action) {
      return clearsFinishedBattle(reference.state(), action);
    });
    if (clearing == actions.end())
      return clicks;
    const auto before = menuText(reference.legalInterrupts());
    reference.step(*clearing);
    const auto after = menuText(reference.legalInterrupts());
    for (const auto &declaration : before)
      check(std::find(after.begin(), after.end(), declaration) != after.end(),
            "Clearing a finished battle removed a declaration opportunity");
    ++clicks;
  }
  throw std::runtime_error("Reference kept offering battle clearings");
}

struct Lockstep {
  int decisions = 0;
  int chances = 0;
  int clearings = 0;
};

// Plays one curriculum game on both profiles with the same position, seed and
// choices. At every decision the training engine must match the reference after
// its clearings: position, menu, declarations and execution randomness.
Lockstep playLockstep(std::uint64_t seed, int rounds) {
  const auto scenario =
      std::filesystem::path(GWRL_SOURCE_DIR) / "game_content/scenarios/japan_china_1936";
  const auto start = CampaignEnv::curriculum(scenario, rounds, seed, true).engine().state();
  Engine training(start, trainingCampaignRules(), seed);
  Engine reference(start, std::make_shared<WithoutSettle>(trainingCampaignRules()), seed);
  std::mt19937_64 choices(seed * 7919 + 17);
  Lockstep result;
  for (int step = 0; step < 20000 && !training.state().terminal; ++step) {
    result.clearings += clearLikeTraining(reference);
    check(positionText(training) == positionText(reference),
          "Training position differs from the cleared reference at step " + std::to_string(step));
    check(randomText(training) == randomText(reference), "Execution randomness diverged");
    if (training.state().chance) {
      training.resolveChance();
      reference.resolveChance();
      ++result.chances;
      continue;
    }
    const auto actions = training.legalActions();
    check(menuText(actions) == menuText(reference.legalActions()), "Training menu differs from the reference");
    check(menuText(training.legalInterrupts()) == menuText(reference.legalInterrupts()),
          "Training declarations differ from the reference");
    check(!actions.empty(), "Nonterminal training position has no legal action");
    for (const auto &action : actions)
      check(!clearsFinishedBattle(training.state(), action), "Training profile offered a battle clearing");
    if (training.state().decisions.empty() && !training.state().chance)
      for (const auto &[id, battle] : training.state().battles)
        check(!marked(battle.flags, "finished") || marked(battle.flags, "air_mission") ||
                  marked(battle.flags, "amphibious_preparation"),
              "Training profile kept a finished battle with nothing pending");
    // End a phase more often than uniform play would, so games reach later rounds.
    std::size_t index = std::uniform_int_distribution<std::size_t>(0, actions.size() - 1)(choices);
    const auto end = std::find_if(actions.begin(), actions.end(),
                                  [](const Action &action) { return action.kind == "end_phase"; });
    if (end != actions.end() && std::uniform_real_distribution<double>(0, 1)(choices) < 0.05)
      index = static_cast<std::size_t>(end - actions.begin());
    training.step(actions[index]);
    reference.step(actions[index]);
    ++result.decisions;
  }
  check(training.state().terminal, "Lockstep game did not finish");
  result.clearings += clearLikeTraining(reference);
  check(positionText(training) == positionText(reference), "Final positions differ");
  check(randomText(training) == randomText(reference), "Final randomness differs");
  check(terminalReturns(training.state()) == terminalReturns(reference.state()), "Returns differ");
  return result;
}

std::vector<Id> battleIds(const Engine &engine) {
  std::vector<Id> out;
  for (const auto &[id, battle] : engine.state().battles)
    out.push_back(id);
  return out;
}

struct Delayed {
  int decisions = 0;
  int chances = 0;
  int declarations = 0;
  int delayed = 0;
  int delayedDeclarations = 0;
  int comparisons = 0;
};

// The reference player may also leave finished battles uncleared and do anything
// else first, declarations included; while a clearing is offered it prefers
// other choices. Every such choice must stay legal for the training profile, and
// clearing a copy of the reference must reproduce the training position whenever
// the copy can clear the same battles.
Delayed playDelayed(std::uint64_t seed, int rounds) {
  const auto scenario =
      std::filesystem::path(GWRL_SOURCE_DIR) / "game_content/scenarios/japan_china_1936";
  const auto start = CampaignEnv::curriculum(scenario, rounds, seed, true).engine().state();
  Engine training(start, trainingCampaignRules(), seed);
  Engine reference(start, std::make_shared<WithoutSettle>(trainingCampaignRules()), seed);
  std::mt19937_64 choices(seed * 104729 + 3);
  const auto chance = [&](double probability) {
    return std::uniform_real_distribution<double>(0, 1)(choices) < probability;
  };
  Delayed result;
  for (int step = 0; step < 40000 && !reference.state().terminal; ++step) {
    auto cleared = reference.clone();
    clearLikeTraining(cleared);
    if (battleIds(cleared) == battleIds(training)) {
      check(positionText(training) == positionText(cleared),
            "Training position differs from the reference cleared later, at step " + std::to_string(step));
      if (!training.state().chance) {
        check(menuText(training.legalActions()) == menuText(cleared.legalActions()),
              "Training menu differs from the reference cleared later");
        check(menuText(training.legalInterrupts()) == menuText(cleared.legalInterrupts()),
              "Training declarations differ from the reference cleared later");
      }
      ++result.comparisons;
    }
    if (reference.state().chance) {
      check(training.state().chance.has_value(), "Training engine missed the reference's chance event");
      check(randomText(training) == randomText(reference), "Execution randomness diverged");
      training.resolveChance();
      reference.resolveChance();
      ++result.chances;
      continue;
    }
    const auto actions = reference.legalActions();
    check(!actions.empty(), "Nonterminal reference position has no legal action");
    std::vector<std::size_t> others;
    for (std::size_t i = 0; i < actions.size(); ++i)
      if (!clearsFinishedBattle(reference.state(), actions[i]))
        others.push_back(i);
    const bool clearingOffered = others.size() < actions.size();
    const auto declarations = reference.legalInterrupts();
    if (!declarations.empty() && chance(clearingOffered ? 0.25 : 0.02)) {
      const auto &declaration =
          declarations[std::uniform_int_distribution<std::size_t>(0, declarations.size() - 1)(choices)];
      training.interrupt(declaration);
      reference.interrupt(declaration);
      ++result.declarations;
      result.delayedDeclarations += clearingOffered;
      continue;
    }
    std::size_t index = std::uniform_int_distribution<std::size_t>(0, actions.size() - 1)(choices);
    if (clearingOffered && !others.empty() && chance(0.8))
      index = others[std::uniform_int_distribution<std::size_t>(0, others.size() - 1)(choices)];
    const auto end = std::find_if(actions.begin(), actions.end(),
                                  [](const Action &action) { return action.kind == "end_phase"; });
    if (end != actions.end() && chance(0.05))
      index = static_cast<std::size_t>(end - actions.begin());
    if (clearsFinishedBattle(reference.state(), actions[index])) {
      reference.step(actions[index]);
      continue;
    }
    result.delayed += clearingOffered;
    training.step(actions[index]);
    reference.step(actions[index]);
    ++result.decisions;
  }
  check(reference.state().terminal && training.state().terminal, "Delayed lockstep game did not finish");
  check(positionText(training) == positionText(reference), "Final positions differ");
  check(randomText(training) == randomText(reference), "Final randomness differs");
  check(terminalReturns(training.state()) == terminalReturns(reference.state()), "Returns differ");
  return result;
}

int setting(const char *name, int fallback) {
  const char *text = std::getenv(name);
  return text ? std::max(1, std::atoi(text)) : fallback;
}

void randomGamesMatchTheProfileThatClicked() {
  // TRAINING_CLEARING_SEEDS and _ROUNDS widen the run for manual verification.
  const int seeds = setting("TRAINING_CLEARING_SEEDS", 1);
  const int rounds = setting("TRAINING_CLEARING_ROUNDS", 1);
  Lockstep total;
  for (int seed = 0; seed < seeds; ++seed) {
    const auto game = playLockstep(5000 + static_cast<std::uint64_t>(seed), rounds);
    total.decisions += game.decisions;
    total.chances += game.chances;
    total.clearings += game.clearings;
  }
  check(total.clearings > 0, "Lockstep games never finished a battle");
  std::cout << "PASS " << seeds << " lockstep games of " << rounds << " rounds: " << total.decisions
            << " decisions, " << total.chances << " chance events, " << total.clearings
            << " clearings the training profile took itself\n";
}

void delayedClearingsLoseNoChoice() {
  const int seeds = setting("TRAINING_CLEARING_SEEDS", 1);
  const int rounds = setting("TRAINING_CLEARING_ROUNDS", 1);
  Delayed total;
  for (int seed = 0; seed < seeds; ++seed) {
    const auto game = playDelayed(6000 + static_cast<std::uint64_t>(seed), rounds);
    total.decisions += game.decisions;
    total.chances += game.chances;
    total.declarations += game.declarations;
    total.delayed += game.delayed;
    total.delayedDeclarations += game.delayedDeclarations;
    total.comparisons += game.comparisons;
  }
  check(total.delayed > 0, "The reference never left a finished battle uncleared");
  std::cout << "PASS " << seeds << " delayed-clearing games of " << rounds << " rounds: " << total.decisions
            << " shared decisions, " << total.delayed << " of them with a clearing left for later, "
            << total.declarations << " declarations (" << total.delayedDeclarations
            << " with a clearing left), " << total.chances << " chance events, " << total.comparisons
            << " position comparisons\n";
}

State navalFixture() {
  static const auto initial =
      loadScenario(std::filesystem::path(GWRL_SOURCE_DIR) / "game_content/scenarios/japan_china_1936");
  auto state = initial.clone();
  state.units.clear();
  state.construction.clear();
  state.repairs.clear();
  state.clock.nationIndex = 2;
  state.clock.playerTurnSerial = 2;
  state.clock.phase = Phase::Combat;
  for (const auto &nation : state.definition->turnOrder)
    state.completedTurns[nation] = nation == "ccp" || nation == "mongolia" ? 1 : 0;
  state.nations.at("japan").atWarWith.insert("kmt");
  state.nations.at("kmt").atWarWith.insert("japan");
  for (const auto &[id, owner] : {std::pair<Id, Id>{"attacker", "japan"}, {"defender", "kmt"}}) {
    UnitState unit;
    unit.id = id;
    unit.type = "destroyer";
    unit.owner = owner;
    unit.zone = unit.turnOrigin = "sea_p15";
    unit.movementAllowance = unit.movementRemaining =
        state.definition->catalog->stats("destroyer", 0, catalogContext(state, owner, "sea_p15")).movement;
    state.units.emplace(id, std::move(unit));
  }
  state.captureTurnStart();
  registerNavalBattle(state, "sea_p15", "japan", {"attacker"}, {{"attacker", "sea_p14"}},
                      V(O{{"no_scramble", V(true)}}));
  return state;
}

void choose(Engine &engine, const Id &kind, const Id &unit = "") {
  for (const auto &action : engine.legalActions())
    if (action.kind == kind &&
        (unit.empty() || action.parameters.require("unit").asString() == unit)) {
      engine.step(action);
      return;
    }
  throw std::runtime_error("Missing action: " + kind);
}

void finishedNavalBattlesClearThemselves() {
  const auto state = navalFixture();
  Engine training(state, trainingCampaignRules(), 5);
  Engine reference(state, std::make_shared<WithoutSettle>(trainingCampaignRules()), 5);
  for (auto *engine : {&training, &reference}) {
    engine->setDiceTapeForTesting({1, 1});
    choose(*engine, "naval_begin_battle");
    engine->resolveChance();
    choose(*engine, "naval_take_casualty", "defender");
    engine->resolveChance();
    choose(*engine, "naval_take_casualty", "attacker");
  }
  const auto clicks = menuText(reference.legalActions());
  check(clicks.size() == 1 && reference.legalActions().front().kind == "naval_finish_battle",
        "Reference no longer waits for the naval finish click");
  check(training.state().battles.empty(), "Training kept a finished naval battle");
  reference.step(reference.legalActions().front());
  check(positionText(training) == positionText(reference), "Naval clearing changed the position");
  check(randomText(training) == randomText(reference), "Naval clearing consumed randomness");
  check(menuText(training.legalActions()) == menuText(reference.legalActions()),
        "Naval clearing changed the next menu");
  std::cout << "PASS finished naval battles clear themselves\n";
}

void clearedTrainingGamesReplayExactly() {
  const auto scenario =
      std::filesystem::path(GWRL_SOURCE_DIR) / "game_content/scenarios/japan_china_1936";
  const auto start = CampaignEnv::curriculum(scenario, 1, 5003, true).engine().state();
  const auto rules = trainingCampaignRules();
  Engine engine(start, rules, 5003);
  const auto checkpoint = engine.serialize();
  std::mt19937_64 choices(11);
  for (int step = 0; step < 20000 && !engine.state().terminal; ++step) {
    if (engine.state().chance) {
      engine.resolveChance();
      continue;
    }
    const auto actions = engine.legalActions();
    engine.step(actions[std::uniform_int_distribution<std::size_t>(0, actions.size() - 1)(choices)]);
  }
  check(engine.state().terminal, "Replay game did not finish");
  const auto replayed = Engine::replay(start.definition, rules, checkpoint, engine.state().history);
  check(replayed.exactReplayIdentity() == engine.exactReplayIdentity(),
        "A game with automatic clearings does not replay exactly");
  std::cout << "PASS training games with automatic clearings replay exactly\n";
}
} // namespace

int main() {
  try {
    finishedNavalBattlesClearThemselves();
    clearedTrainingGamesReplayExactly();
    randomGamesMatchTheProfileThatClicked();
    delayedClearingsLoseNoChoice();
    std::cout << "Training battle clearing checks passed\n";
    return 0;
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
