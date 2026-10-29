#include "game/air.hpp"
#include "game/campaign_actions.hpp"
#include "game/campaign_audit.hpp"
#include "game/campaign_env.hpp"
#include "game/catalog.hpp"
#include "game/movement.hpp"
#include "game/naval.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <functional>
#include <iostream>
#include <set>
#include <stdexcept>

namespace {
using namespace game::campaign;
using V = game::json::Value;
const Id p14 = "sea_p14", p15 = "sea_p15", p16 = "sea_p16";
const Id tokyo = "land_jap_tokyo";
const Id tokyoPort = "facility_tokyo_major_shipyard";

void check(bool condition, const std::string &message) {
  if (!condition)
    throw std::runtime_error(message);
}

State fixture(Phase phase = Phase::NonCombatMovement) {
  static const auto initial =
      loadScenario(std::filesystem::path(GWRL_SOURCE_DIR) /
                   "game_content/scenarios/japan_china_1936");
  auto state = initial.clone();
  state.units.clear();
  state.construction.clear();
  state.repairs.clear();
  state.clock.nationIndex = 2;
  state.clock.playerTurnSerial = 2;
  state.clock.phase = phase;
  for (const auto &nation : state.definition->turnOrder)
    state.completedTurns[nation] = nation == "ccp" || nation == "mongolia" ? 1 : 0;
  state.captureTurnStart();
  return state;
}

void add(State &state, const Id &id, const Id &type, const Id &zone,
         const Id &owner = "japan") {
  UnitState unit;
  unit.id = id;
  unit.type = type;
  unit.owner = owner;
  unit.zone = unit.turnOrigin = zone;
  unit.movementAllowance = unit.movementRemaining =
      state.definition->catalog->stats(type, 0, catalogContext(state, owner, zone))
          .movement;
  state.units.emplace(id, std::move(unit));
}

Action select(const Engine &engine, const Id &kind,
              const std::function<bool(const Action &)> &match =
                  [](const Action &) { return true; }) {
  for (const auto &candidate : engine.legalActions())
    if (candidate.kind == kind && match(candidate))
      return candidate;
  throw std::runtime_error("Missing action: " + kind);
}

void choose(Engine &engine, const Id &kind,
            const std::function<bool(const Action &)> &match =
                [](const Action &) { return true; }) {
  engine.step(select(engine, kind, match));
}

void chooseUnit(Engine &engine, const Id &kind, const Id &unit) {
  choose(engine, kind, [&](const Action &candidate) {
    return candidate.parameters.require("unit").asString() == unit;
  });
}

bool hasKind(const Engine &engine, const Id &kind) {
  const auto actions = engine.legalActions();
  return std::any_of(actions.begin(), actions.end(), [&](const Action &candidate) {
    return candidate.kind == kind;
  });
}

std::vector<Id> selected(const Engine &engine, const Id &field = "selected") {
  const auto &decision = engine.state().decisions.back();
  const auto &plan = engine.state().battles.at(decision.continuation);
  std::vector<Id> result;
  if (const auto *value = plan.data.find(field))
    for (const auto &id : value->asArray())
      result.push_back(id.asString());
  return result;
}

Id fleetText(const std::vector<Id> &fleet) {
  V::Array ids;
  for (const auto &id : fleet)
    ids.emplace_back(id);
  return canonicalJson(V(std::move(ids)));
}

Id commitKey(const Action &candidate, const std::vector<Id> &fleet) {
  return candidate.kind == "naval_route"
             ? canonicalJson(candidate.parameters.require("request"))
             : candidate.kind + fleetText(fleet);
}

void allFleetOrdersRemainAvailableAndEveryDraftTerminates() {
  for (bool enemyAtOrigin : {false, true}) {
    auto state = fixture(enemyAtOrigin ? Phase::CombatMovement
                                       : Phase::NonCombatMovement);
    add(state, "a", enemyAtOrigin ? "destroyer" : "naval_transport", p16);
    add(state, "b", enemyAtOrigin ? "battleship" : "attack_naval_transport", p16);
    add(state, "c", "submarine", p16);
    if (enemyAtOrigin) {
      state.nations.at("japan").atWarWith.insert("kmt");
      state.nations.at("kmt").atWarWith.insert("japan");
      add(state, "enemy", "destroyer", p16, "kmt");
    }
    state.captureTurnStart();
    std::set<Id> reference, forward;
    // Enumerate the seven fleets only in this tiny completeness oracle, never
    // in the production action menu. Each reference fleet uses the human API.
    for (unsigned mask = 1; mask < 8; ++mask) {
      std::vector<Id> fleet;
      for (unsigned bit = 0; bit < 3; ++bit)
        if (mask & (1U << bit))
          fleet.push_back(Id(1, static_cast<char>('a' + bit)));
      Engine human(state, campaignRules());
      chooseUnit(human, "naval_start_move", fleet.front());
      for (std::size_t i = 1; i < fleet.size(); ++i)
        chooseUnit(human, "naval_force_add", fleet[i]);
      for (const auto &candidate : human.legalActions())
        if (candidate.kind == "naval_route" ||
            candidate.kind == "naval_engage_force")
          reference.insert(commitKey(candidate, fleet));
    }

    std::size_t drafts = 0;
    std::function<void(const Engine &, unsigned)> walk =
        [&](const Engine &engine, unsigned depth) {
          ++drafts;
          const auto fleet = selected(engine);
          check(!fleet.empty() && std::is_sorted(fleet.begin(), fleet.end()),
                "Forward draft is empty or reordered");
          check(depth <= 3 && depth == fleet.size(),
                "Forward draft does not strictly progress");
          check(engine.legalInterrupts().empty(),
                "An opponent acquired a decision during pure fleet construction");
          bool hasCompletion = false;
          for (const auto &candidate : engine.legalActions()) {
            check(candidate.kind != "naval_cancel_move" &&
                      candidate.kind != "naval_force_remove",
                  "Forward draft retained a reversible edit");
            if (candidate.kind == "naval_route" ||
                candidate.kind == "naval_engage_force") {
              forward.insert(commitKey(candidate, fleet));
              hasCompletion = true;
            } else if (candidate.kind == "naval_force_add") {
              check(candidate.parameters.require("unit").asString() > fleet.back(),
                    "Forward draft permits duplicate fleet permutations");
              auto next = engine.clone();
              next.step(candidate);
              walk(next, depth + 1);
              hasCompletion = true;
            } else {
              throw std::runtime_error("Unexpected choice in a fleet draft");
            }
          }
          check(hasCompletion, "A forward draft cannot reach a committed order");
        };
    Engine engine(state, trainingCampaignRules());
    for (const auto &candidate : engine.legalActions())
      if (candidate.kind == "naval_start_move") {
        auto draft = engine.clone();
        draft.step(candidate);
        walk(draft, 1);
      }
    check(forward == reference, "Forward construction lost an executable fleet/route");
    if (!enemyAtOrigin)
      check(std::any_of(reference.begin(), reference.end(), [](const Id &request) {
              return request.find("\"strategic\":true") != Id::npos;
            }), "Fleet oracle did not exercise strategic movement");
    check(drafts == 7, "A three-ship fleet has duplicate or missing construction paths");
  }
}

void exhaustedAndZeroRouteStartsAreAbsentButPortExitRemains() {
  auto state = fixture();
  add(state, "exhausted", "destroyer", p16);
  state.units.at("exhausted").turnFlags["naval_movement_spent"] = 99;
  state.units.at("exhausted").movementRemaining = 0;
  Engine human(state, campaignRules());
  Engine training(state, trainingCampaignRules());
  check(hasKind(human, "naval_start_move"), "Human picker unexpectedly disappeared");
  check(!hasKind(training, "naval_start_move"), "Exhausted ship opens a dead-end draft");
  check(hasKind(training, "end_phase"), "Not moving must remain an ordinary phase choice");
  chooseUnit(human, "naval_start_move", "exhausted");
  check(hasKind(human, "naval_cancel_move") &&
            hasKind(human, "naval_force_remove"),
        "Training construction removed the human picker's reversible edits");

  state.units.clear();
  add(state, "in_port", "destroyer", tokyo);
  state.units.at("in_port").gameFlags["in_port:" + tokyoPort] = 1;
  state.units.at("in_port").turnFlags["naval_movement_spent"] = 99;
  state.units.at("in_port").movementRemaining = 0;
  Engine port(state, trainingCampaignRules());
  chooseUnit(port, "naval_start_move", "in_port");
  choose(port, "naval_route", [&](const Action &candidate) {
    return candidate.parameters.require("request").require("path").asArray().size() == 1;
  });
  check(port.state().units.at("in_port").zone == p16,
        "A zero-cost legal port sortie was removed with exhausted movement");
}

void landingFailureAtAnIntermediateDestinationDoesNotHideLongerRoutes() {
  auto state = fixture();
  add(state, "carrier", "light_carrier", p16);
  add(state, "plane", "fighter", p14);
  state.units.at("plane").turnFlags["air_in_flight"] = 1;
  state.units.at("plane").movementRemaining = 0;
  // RB 9.3 needs the seat only when movement ends, so a first leg that keeps
  // the waiting aircraft within the carrier's remaining reach is legal.
  check(validateNavalRoute(state, {{"carrier"}, {p16, p15}}).allowed &&
            validateNavalRoute(state, {{"carrier"}, {p16, p15, p14}}).allowed,
        "A carrier leg that can still reach a waiting aircraft was refused");
  // With movement for one leg only, the aircraft beyond reach is lost already,
  // and stopping short strands one waiting beside the carrier.
  auto oneLeg = state.clone();
  for (int spent = 1; spent < 12 &&
                      validateNavalRoute(oneLeg, {{"carrier"}, {p16, p15, p14}}).allowed;
       ++spent)
    oneLeg.units.at("carrier").turnFlags["naval_movement_spent"] = spent;
  add(oneLeg, "beside", "fighter", p16);
  oneLeg.units.at("beside").turnFlags["air_in_flight"] = 1;
  oneLeg.units.at("beside").movementRemaining = 0;
  const auto shortLeg = validateNavalRoute(oneLeg, {{"carrier"}, {p16, p15}});
  check(!shortLeg.allowed &&
            shortLeg.reason == "Carrier movement leaves aircraft without a joint landing plan" &&
            validateNavalRoute(oneLeg, {{"carrier"}, {p16, p15, p14}}).reason == "Insufficient naval movement",
        "Landing-prefix fixture does not distinguish the two destinations");
  for (const auto &rules : {campaignRules(), trainingCampaignRules()}) {
    Engine engine(state, rules);
    chooseUnit(engine, "naval_start_move", "carrier");
    choose(engine, "naval_route", [&](const Action &candidate) {
      return canonicalJson(candidate.parameters.require("request").require("path")) ==
             canonicalJson(V(V::Array{V(p16), V(p15), V(p14)}));
    });
    check(engine.state().units.at("carrier").zone == p14,
          "A landing-only prefix rejection hid a legal longer route");
  }
}

void carriersMayJoinWaitingAircraftOneAtATime() {
  // Three aircraft without fuel need three seats only when movement ends
  // (RB 9.3), so each carrier may sail alone while the others can follow.
  auto state = fixture();
  for (const auto &id : {"a", "b", "c"})
    add(state, id, "light_carrier", p16);
  for (const auto &id : {"plane_one", "plane_two", "plane_three"}) {
    add(state, id, "fighter", p14);
    state.units.at(id).turnFlags["air_in_flight"] = 1;
    state.units.at(id).movementRemaining = 0;
  }
  check(validateNavalRoute(state, {{"a"}, {p16, p15, p14}}).allowed &&
            validateNavalRoute(state, {{"a", "b", "c"}, {p16, p15, p14}}).allowed,
        "A carrier could not sail toward aircraft the other carriers can still seat");
  // Two carriers can seat only two of the three, so one aircraft is lost
  // whatever they do; each may still sail to save the others.
  auto twoSeats = state.clone();
  twoSeats.units.erase("c");
  check(airLandingShortfall(twoSeats) == 1 && validateNavalRoute(twoSeats, {{"a"}, {p16, p15, p14}}).allowed,
        "A carrier could not sail to save two of three aircraft that two seats can hold");
  Engine engine(state, trainingCampaignRules());
  for (const auto &id : {"a", "b", "c"}) {
    chooseUnit(engine, "naval_start_move", id);
    choose(engine, "naval_route", [&](const Action &candidate) {
      return canonicalJson(candidate.parameters.require("request").require("path")) ==
             canonicalJson(V(V::Array{V(p16), V(p15), V(p14)}));
    });
  }
  check(engine.state().units.at("a").zone == p14 &&
            engine.state().units.at("b").zone == p14 &&
            engine.state().units.at("c").zone == p14,
        "Carriers joining one at a time failed to execute");
}

void screeningRetainsAllNonemptySubsetsAndItsRealContinuationChoice() {
  auto state = fixture(Phase::CombatMovement);
  state.nations.at("japan").atWarWith.insert("kmt");
  state.nations.at("kmt").atWarWith.insert("japan");
  for (const auto &id : {"a", "b", "c"}) {
    add(state, id, "destroyer", tokyo);
    state.units.at(id).gameFlags["in_port:" + tokyoPort] = 1;
  }
  add(state, "enemy", "destroyer", p16, "kmt");
  Engine engine(state, trainingCampaignRules());
  chooseUnit(engine, "naval_start_move", "a");
  chooseUnit(engine, "naval_force_add", "b");
  chooseUnit(engine, "naval_force_add", "c");
  choose(engine, "naval_route", [&](const Action &candidate) {
    return canonicalJson(candidate.parameters.require("request").require("path")) ==
           canonicalJson(V(V::Array{V(p16), V(p15)}));
  });
  check(engine.state().decisions.back().kind == "naval_screening_force" &&
            engine.state().units.at("a").zone == tokyo,
        "Blocked fleet left port before its screening battle: " +
            engine.state().decisions.back().kind + " / " +
            engine.state().units.at("a").zone);
  std::set<Id> subsets;
  std::function<void(const Engine &, unsigned)> walk =
      [&](const Engine &draft, unsigned depth) {
        check(depth <= 3, "Screen subset construction can loop");
        const auto fleet = selected(draft, "screening");
        check(fleet.size() == depth && std::is_sorted(fleet.begin(), fleet.end()),
              "Screen construction is not strictly ascending");
        for (const auto &candidate : draft.legalActions()) {
          check(candidate.kind != "naval_screen_remove",
                "Screen retained an undo loop");
          if (candidate.kind == "naval_screen_confirm") {
            check(!fleet.empty(), "Empty screening force was admitted");
            subsets.insert(fleetText(fleet));
          } else if (candidate.kind == "naval_screen_add") {
            auto next = draft.clone();
            next.step(candidate);
            walk(next, depth + 1);
          }
        }
      };
  walk(engine, 0);
  check(subsets.size() == 7, "Screen construction lost a legal force subset");
  chooseUnit(engine, "naval_screen_add", "a");
  choose(engine, "naval_screen_confirm");
  check(engine.state().units.at("a").zone == p16 &&
            engine.state().units.at("b").zone == tokyo,
        "Selecting a screen incorrectly moved the waiting ships");
  auto after = engine.state().clone();
  const auto battle = after.battles.begin()->first;
  removePoliticalUnits(after, {"enemy"});
  after.battles.at(battle).stage = "naval_complete";
  after.battles.at(battle).flags["finished"] = 1;
  continueNavalMovement(after, battle);
  forwardNavalOrderDecision(after);
  check(after.decisions.back().kind == "naval_screening_continuation",
        "Actual screening continuation disappeared");
  const auto &options = after.decisions.back().options;
  for (const auto &kind : {"naval_screen_stop_route", "naval_screen_continue_route"})
    check(std::any_of(options.begin(), options.end(), [&](const Action &candidate) {
            return candidate.kind == kind;
          }), "Real post-battle stop/continue choice was removed");
}

void declarationsAndSubmarineReactionsRemainActualDecisions() {
  for (bool submarine : {false, true}) {
    auto state = fixture(submarine ? Phase::NonCombatMovement : Phase::CombatMovement);
    add(state, "ship", "destroyer", p16);
    add(state, "other", submarine ? "submarine" : "destroyer", p15, "kmt");
    if (submarine) {
      state.nations.at("japan").atWarWith.insert("kmt");
      state.nations.at("kmt").atWarWith.insert("japan");
    } else {
      state.nations.at("kmt").powerStatus = "major";
    }
    Engine human(state, campaignRules(), 71);
    Engine training(state, trainingCampaignRules(), 71);
    for (auto *engine : {&human, &training}) {
      chooseUnit(*engine, "naval_start_move", "ship");
      choose(*engine, "naval_route", [&](const Action &candidate) {
        return canonicalJson(candidate.parameters.require("request").require("path")) ==
               canonicalJson(V(V::Array{V(p16), V(p15)}));
      });
    }
    auto humanState = human.state().toJson(false).asObject();
    auto trainingState = training.state().toJson(false).asObject();
    humanState.erase("action_interface");
    trainingState.erase("action_interface");
    check(canonicalJson(V(std::move(humanState))) ==
              canonicalJson(V(std::move(trainingState))),
          "Forward construction changed actual sea-entry/reaction state");
    check(canonicalJson(game::json::parse(human.serialize()).require("random")) ==
              canonicalJson(game::json::parse(training.serialize()).require("random")),
          "Order construction consumed execution RNG");
    check(training.state().decisions.back().kind ==
              (submarine ? "naval_movement_reaction" : "naval_entry_intent"),
          "A genuine movement interruption was collapsed into the draft");
    check(training.state().decisions.back().nation ==
              (submarine ? "kmt" : "japan"),
          "Movement interruption went to the calendar owner");
  }
}

void laterBlockingSeasStartAFreshScreenSelection() {
  auto state = fixture(Phase::CombatMovement);
  state.nations.at("japan").atWarWith.insert("kmt");
  state.nations.at("kmt").atWarWith.insert("japan");
  for (const auto &id : {"a", "b", "c"})
    add(state, id, "destroyer", p16);
  add(state, "first_enemy", "destroyer", p15, "kmt");
  add(state, "second_enemy", "destroyer", "sea_p32", "kmt");
  for (const auto &rules : {campaignRules(), trainingCampaignRules()}) {
    Engine engine(state, rules);
    chooseUnit(engine, "naval_start_move", "a");
    chooseUnit(engine, "naval_force_add", "b");
    chooseUnit(engine, "naval_force_add", "c");
    choose(engine, "naval_route", [&](const Action &candidate) {
      return canonicalJson(candidate.parameters.require("request").require("path")) ==
             canonicalJson(V(V::Array{V(p16), V(p15), V("sea_p32"), V("sea_p41")}));
    });
    chooseUnit(engine, "naval_screen_add", "a");
    choose(engine, "naval_screen_confirm");
    auto after = engine.state().clone();
    const auto battle = after.battles.begin()->first;
    removePoliticalUnits(after, {"first_enemy"});
    after.battles.at(battle).stage = "naval_complete";
    after.battles.at(battle).flags["finished"] = 1;
    continueNavalMovement(after, battle);
    const auto &options = after.decisions.back().options;
    const auto continuation = std::find_if(options.begin(), options.end(),
        [](const Action &candidate) {
          return candidate.kind == "naval_screen_continue_route";
        });
    check(continuation != options.end(), "First screening lost its continuation");
    const auto action = *continuation;
    check(applyNavalMovementAction(after, action), "Screen continuation did not apply");
    forwardNavalOrderDecision(after);
    check(after.decisions.back().kind == "naval_screening_force",
          "Second blocking sea did not require its own screening choice");
    const auto &next = after.battles.at(after.decisions.back().continuation);
    check(next.zone == "sea_p32" && next.data.require("screening").asArray().empty(),
          "Second screen inherited ships committed at the previous sea");
    for (const auto &candidate : after.decisions.back().options) {
      check(candidate.kind != "naval_screen_confirm",
            "Old screening ships enabled confirmation of an unselected screen");
      check(candidate.kind == "naval_screen_add" &&
                candidate.parameters.require("unit").asString() != "a",
            "A ship left in the first screening battle reappeared in the second");
    }
  }
}
} // namespace

int main() {
  try {
    allFleetOrdersRemainAvailableAndEveryDraftTerminates();
    exhaustedAndZeroRouteStartsAreAbsentButPortExitRemains();
    landingFailureAtAnIntermediateDestinationDoesNotHideLongerRoutes();
    carriersMayJoinWaitingAircraftOneAtATime();
    screeningRetainsAllNonemptySubsetsAndItsRealContinuationChoice();
    declarationsAndSubmarineReactionsRemainActualDecisions();
    laterBlockingSeasStartAFreshScreenSelection();
    std::cout << "Campaign action interface checks passed\n";
    return 0;
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
