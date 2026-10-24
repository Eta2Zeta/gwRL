#include "game/campaign_actions.hpp"
#include "game/campaign_audit.hpp"
#include "game/air.hpp"
#include "game/catalog.hpp"
#include "game/economy.hpp"
#include "game/naval.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <functional>
#include <iostream>
#include <stdexcept>

namespace {
using namespace game::campaign;
using V = game::json::Value;
using O = V::Object;
using A = V::Array;
const Id sea = "sea_p16", honshu = "land_jap_honshu", tokyo = "land_jap_tokyo";

void check(bool yes, const std::string& message) { if (!yes) throw std::runtime_error(message); }
void rejects(const std::function<void()>& callback, const std::string& message) {
    try { callback(); } catch (const std::exception&) { return; }
    throw std::runtime_error(message);
}

State fixture(Phase phase) {
    static const auto source = loadScenario(std::filesystem::path(GWRL_SOURCE_DIR) /
                                           "game_content/scenarios/japan_china_1936");
    auto state = source.clone();
    state.units.clear();
    state.construction.clear();
    state.repairs.clear();
    state.clock.nationIndex = 2;
    state.clock.playerTurnSerial = 2;
    state.clock.phase = phase;
    state.completedTurns["ccp"] = state.completedTurns["mongolia"] = 1;
    state.captureTurnStart();
    return state;
}

void add(State& state, const Id& id, const Id& type, const Id& zone, const Id& owner = "japan") {
    UnitState unit;
    unit.id = id;
    unit.type = type;
    unit.owner = owner;
    unit.zone = unit.turnOrigin = zone;
    unit.movementAllowance = unit.movementRemaining =
        state.definition->catalog->stats(type, 0, catalogContext(state, owner, zone)).movement;
    state.units.emplace(id, std::move(unit));
}

using Predicate = std::function<bool(const Action&)>;
const Predicate any = [](const Action&) { return true; };
bool offers(const Engine& engine, const Id& kind, const Predicate& predicate = any) {
    const auto actions = engine.legalActions();
    return std::any_of(actions.begin(), actions.end(), [&](const Action& action) {
        return action.kind == kind && predicate(action);
    });
}
Action select(const Engine& engine, const Id& kind, const Predicate& predicate = any) {
    for (const auto& action : engine.legalActions())
        if (action.kind == kind && predicate(action)) return action;
    throw std::runtime_error("Missing training action " + kind);
}
void choose(Engine& engine, const Id& kind, const Predicate& predicate = any) {
    engine.step(select(engine, kind, predicate));
}
Predicate landing(const Id& plane, const Id& destination) {
    return [=](const Action& action) {
        return action.parameters.require("unit").asString() == plane &&
               action.parameters.require("destination").asString() == destination;
    };
}

void raiderChoicesRemainReachableAndBounceStops() {
    auto source = fixture(Phase::CombatMovement);
    add(source, "raider", "battlecruiser", sea);
    add(source, "walker", "infantry", honshu);
    source.captureTurnStart();
    Engine engine(source, trainingCampaignRules(), 17);
    check(offers(engine, "end_phase"), "Normal stationary role cannot finish the phase");
    choose(engine, "naval_designate_raider");
    check(engine.state().units.at("raider").gameFlags.at("raider") == 1,
          "Raider role outcome is unreachable");
    check(!offers(engine, "naval_remove_raider"), "Raider role can immediately toggle back");
    const auto raw = campaignRules()->actions(engine.state());
    check(std::any_of(raw.begin(), raw.end(), [](const Action& action) {
        return action.kind == "naval_remove_raider";
    }), "Training wrapper changed the human rule interface");
    auto completed = engine.clone();
    choose(completed, "end_phase");
    check(completed.state().clock.phase == Phase::Combat &&
          completed.state().actionInterface.require("visited_configurations").asArray().empty(),
          "Phase boundary retained an earlier role-configuration frame");
    choose(engine, "movement_route", [](const Action& action) {
        return action.parameters.require("unit").asString() == "walker" &&
               action.parameters.require("path").asArray().back().asString() == tokyo;
    });
    check(engine.state().actionInterface.require("visited_configurations").asArray().empty(),
          "Physical movement retained stale configuration restrictions");
    choose(engine, "naval_remove_raider");
    check(!engine.state().units.at("raider").gameFlags.contains("raider"),
          "Role change after real progress was incorrectly removed");

    source.units.at("raider").gameFlags["naval_raider"] = 1;
    Engine alias(source, trainingCampaignRules(), 17);
    choose(alias, "naval_remove_raider");
    choose(alias, "naval_designate_raider");
    check(!offers(alias, "naval_remove_raider"), "Raider alias configuration can loop");
}

void zeroMovementCarrierAssignmentsRemainReachable() {
    auto source = fixture(Phase::NonCombatMovement);
    for (const auto& id : {Id("first"), Id("second"), Id("third")}) add(source, id, "fleet_carrier", sea);
    add(source, "plane", "fighter", sea);
    attachCargo(source, "first", "plane");
    source.units.at("plane").movementRemaining = 0;
    source.captureTurnStart();
    for (const auto& destination : {Id("second"), Id("third")}) {
        Engine branch(source, trainingCampaignRules(), 21);
        choose(branch, "air_land_noncombat", landing("plane", destination));
        check(branch.state().units.at("plane").carriedBy == destination &&
              branch.state().units.at("plane").movementRemaining == 0,
              "A genuine zero-movement carrier assignment was removed");
    }
    Engine engine(source, trainingCampaignRules(), 21);
    choose(engine, "air_land_noncombat", landing("plane", "second"));
    choose(engine, "air_land_noncombat", landing("plane", "first"));
    check(!offers(engine, "air_land_noncombat", landing("plane", "second")),
          "Zero-cost A-B-A-B assignment can repeat");
    check(offers(engine, "air_land_noncombat", landing("plane", "third")),
          "Cycle filtering removed a new final carrier assignment");
    auto forged = select(Engine(source, campaignRules()), "air_land_noncombat", landing("plane", "second"));
    const auto before = engine.serialize();
    rejects([&] { engine.step(forged); }, "Stale repeated carrier assignment was accepted");
    check(engine.serialize() == before, "Rejected assignment changed state/RNG");

    auto swap = source.clone();
    add(swap, "other", "fighter", sea);
    attachCargo(swap, "second", "other");
    swap.units.at("other").movementRemaining = 0;
    Engine pair(swap, trainingCampaignRules(), 22);
    choose(pair, "air_land_noncombat", landing("plane", "second"));
    choose(pair, "air_land_noncombat", landing("other", "first"));
    check(pair.state().units.at("plane").carriedBy == "second" &&
          pair.state().units.at("other").carriedBy == "first",
          "Capacity rearrangement lost a reachable final carrier allocation");
}

void inPortDeckLandAssignmentsCannotCycle() {
    auto source = fixture(Phase::NonCombatMovement);
    source.facilities["test_port"] = {"test_port", "major_port", honshu, 0, {{"border:" + sea, 1}}};
    add(source, "carrier", "fleet_carrier", honshu);
    source.units.at("carrier").gameFlags["in_port:test_port"] = 1;
    add(source, "plane", "fighter", honshu);
    attachCargo(source, "carrier", "plane");
    source.units.at("plane").movementRemaining = 0;
    Engine engine(source, trainingCampaignRules(), 23);
    choose(engine, "air_land_noncombat", landing("plane", honshu));
    choose(engine, "air_land_noncombat", landing("plane", "carrier"));
    check(!offers(engine, "air_land_noncombat", landing("plane", honshu)),
          "Port deck-land-deck landing assignment can cycle");
}

State railFixture(const Id& recipient) {
    auto source = fixture(Phase::Production);
    ensureDadao(source);
    source.nations.at("japan").treasury = 100;
    source.nations.at("japan").atWarWith.erase(recipient);
    source.nations.at(recipient).atWarWith.erase("japan");
    source.territories.at("land_manchuria_rehe").possessor = "japan";
    source.territories.at("land_china_hopeh").possessor = "japan";
    source.territories.at("land_china_suiyuan").possessor = recipient;
    source.captureTurnStart();
    beginEconomyTurn(source);
    source.nations.at("japan").turnFlags["economy_research_finished"] = 1;
    return source;
}

void declinedRailRequestsAreBoundedAndResetAfterProgress() {
    for (const auto& recipient : {Id("dadao"), Id("kmt")}) {
        auto source = railFixture(recipient);
        Engine engine(source, trainingCampaignRules(), 31);
        const auto request = select(engine, "economy_request_rail", [](const Action& action) {
            return action.parameters.require("zone").asString() == "land_manchuria_rehe" &&
                   action.parameters.require("border").asString() == "land_china_suiyuan";
        });
        const auto cash = engine.state().nations.at("japan").treasury;
        engine.step(request);
        choose(engine, "economy_decline_rail");
        check(engine.state().nations.at("japan").treasury == cash && engine.state().construction.empty(),
              "Declined railroad consumed money or created a project");
        const auto same = [&](const Action& action) { return canonicalJson(action.parameters) == canonicalJson(request.parameters); };
        check(!offers(engine, "economy_request_rail", same), "Identical declined request can repeat");
        check(offers(engine, "economy_request_rail", [](const Action& action) {
            return action.parameters.require("zone").asString() == "land_china_hopeh" &&
                   action.parameters.require("border").asString() == "land_china_suiyuan";
        }), "Declining one request removed a different legal railroad proposal");
        auto completed = engine.clone();
        choose(completed, "end_phase");
        check(completed.state().actionInterface.require("declined_rail_requests").asArray().empty(),
              "Phase boundary retained an earlier railroad-consent context");
        const auto before = engine.serialize();
        rejects([&] { engine.step(request); }, "Stale declined railroad request was accepted");
        check(engine.serialize() == before, "Rejected request changed state/RNG");
        choose(engine, "economy_purchase", [](const Action& action) {
            return action.parameters.require("row").asString() == "japan_major_infantry";
        });
        check(offers(engine, "economy_request_rail", same), "Real economic progress did not permit reconsideration");
        engine.step(select(engine, "economy_request_rail", same));
        choose(engine, "economy_approve_rail");
        check(engine.state().construction.size() == 2, "Approved retry failed to purchase its railroad");
    }
}

void progressMetadataReplaysAndRejectsMalformedRestore() {
    auto source = fixture(Phase::CombatMovement);
    add(source, "raider", "battlecruiser", sea);
    Engine engine(source, trainingCampaignRules(), 41);
    const auto initial = engine.serialize();
    choose(engine, "naval_designate_raider");
    const auto checkpoint = engine.serialize();
    auto restored = Engine::restore(source.definition, trainingCampaignRules(), checkpoint);
    auto replayed = Engine::replay(source.definition, trainingCampaignRules(), initial, engine.state().history);
    check(restored.exactReplayIdentity() == engine.exactReplayIdentity() &&
          replayed.exactReplayIdentity() == engine.exactReplayIdentity(),
          "Configuration continuation lost exact checkpoint/replay behavior");
    check(canonicalJson(engine.state().observation().require("action_interface")) ==
          canonicalJson(engine.state().actionInterface), "Continuation is hidden from model observations");
    const auto valid = engine.state().actionInterface;
    for (const auto& corrupt : std::vector<V>{V(O{{"schema", V("unknown")}}),
            V(O{{"schema", V(trainingActionSchema)}, {"visited_configurations", V("opaque hash")},
                {"declined_rail_requests", V(A{})}})}) {
        auto broken = engine.state().clone();
        broken.actionInterface = corrupt;
        rejects([&] { broken.validate(); }, "Malformed interface state passed validation");
    }
    auto broken = engine.state().clone();
    auto data = valid.asObject();
    auto list = data.at("visited_configurations").asArray();
    auto record = list.back().asObject();
    record["opaque_planning_hash"] = V("forbidden");
    list.back() = V(record);
    data["visited_configurations"] = V(list);
    broken.actionInterface = V(data);
    rejects([&] { State::fromJson(source.definition, broken.toJson()); },
            "Unknown descriptor field survived restore");
}

}  // namespace

int main() {
    try {
        for (const auto& [name, test] : std::vector<std::pair<Id, std::function<void()>>>{
                {"raider roles and physical progress", raiderChoicesRemainReachableAndBounceStops},
                {"zero-movement carrier assignments", zeroMovementCarrierAssignmentsRemainReachable},
                {"in-port deck-land assignment", inPortDeckLandAssignmentsCannotCycle},
                {"rail refusal and reconsideration", declinedRailRequestsAreBoundedAndResetAfterProgress},
                {"source metadata replay and validation", progressMetadataReplaysAndRejectsMalformedRestore}}) {
            test();
            std::cout << "PASS " << name << '\n';
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
