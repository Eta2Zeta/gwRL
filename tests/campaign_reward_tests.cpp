#include "game/campaign_env.hpp"
#include "game/campaign_audit.hpp"
#include "game/catalog.hpp"
#include "game/economy.hpp"
#include "game/movement.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <cmath>
#include <functional>
#include <iostream>
#include <stdexcept>

namespace {
using namespace game::campaign;
const auto scenario = std::filesystem::path(GWRL_SOURCE_DIR) / "game_content/scenarios/japan_china_1936";
const Id tokyo = "land_jap_tokyo", shensi = "land_china_shensi", beiping = "land_china_beiping",
         hopeh = "land_china_hopeh", clique = "warlord_beiping_hopeh";

void check(bool yes, const std::string& why) { if (!yes) throw std::runtime_error(why); }
void near(double actual, double expected, const std::string& why) {
    check(std::abs(actual - expected) < 1e-9, why + " (actual " + std::to_string(actual) +
                                             ", expected " + std::to_string(expected) + ")");
}
void rejects(const std::function<void()>& operation, const std::string& why) {
    try { operation(); } catch (const std::exception&) { return; }
    throw std::runtime_error(why);
}
void turn(State& s, const Id& nation, Phase phase) {
    const auto& order = s.definition->turnOrder;
    s.clock.nationIndex = static_cast<int>(std::find(order.begin(), order.end(), nation) - order.begin());
    s.clock.playerTurnSerial = static_cast<std::uint64_t>(s.clock.nationIndex);
    s.clock.phase = phase;
    s.clock.incomeCollected = false;
    for (std::size_t i = 0; i < order.size(); ++i)
        s.completedTurns[order[i]] = i < static_cast<std::size_t>(s.clock.nationIndex) ? 1 : 0;
    s.captureTurnStart();
    MovementRules{}.beginTurn(s);
    beginEconomyTurn(s);
}
State fixture(const Id& nation = "japan", Phase phase = Phase::Production, bool empty = false) {
    static const auto initial = loadScenario(scenario);
    auto s = initial.clone();
    if (empty) {
        s.units.clear(); s.facilities.clear(); s.rails.clear(); s.construction.clear(); s.repairs.clear();
    }
    turn(s, nation, phase);
    return s;
}
void add(State& s, const Id& id, const Id& type, const Id& owner, const Id& zone) {
    UnitState u;
    u.id = id; u.type = type; u.owner = owner; u.zone = u.turnOrigin = zone;
    u.movementAllowance = u.movementRemaining =
        s.definition->catalog->stats(type, 0, catalogContext(s, owner, zone)).movement;
    s.units.emplace(id, std::move(u));
}
Action pick(const Engine& e, const Id& kind,
            const std::function<bool(const Action&)>& predicate = [](const auto&) { return true; }) {
    for (const auto& action : e.legalActions())
        if (action.kind == kind && predicate(action)) return action;
    throw std::runtime_error("Missing legal action " + kind);
}
bool offers(const Engine& e, const Id& kind,
            const std::function<bool(const Action&)>& predicate = [](const auto&) { return true; }) {
    try { (void)pick(e, kind, predicate); return true; } catch (...) { return false; }
}
void choose(Engine& e, const Id& kind,
            const std::function<bool(const Action&)>& predicate = [](const auto&) { return true; }) {
    e.step(pick(e, kind, predicate));
    check(terminalReturns(e.state()) == std::array<double, 3>{0, 0, 0},
          "An intermediate rules action paid a wealth reward");
}
void research(Engine& e) {
    if (offers(e, "economy_finish_research")) choose(e, "economy_finish_research");
}
void placementPhase(Engine& e) {
    for (int i = 0; i < 5 && e.state().clock.phase != Phase::PlaceUnits; ++i) choose(e, "end_phase");
    check(e.state().clock.phase == Phase::PlaceUnits, "Could not reach placement normally");
}
void replayMatches(const Engine& e, const std::string& checkpoint) {
    const auto replay = Engine::replay(e.state().definition, campaignRules(), checkpoint, e.state().history);
    check(replay.exactReplayIdentity() == e.exactReplayIdentity(), "Wealth action replay changed the rules state");
    const auto expected = allianceWealth(e.state()), actual = allianceWealth(replay.state());
    for (std::size_t i = 0; i < 3; ++i) near(actual[i].total(), expected[i].total(), "Replay changed wealth");
}

void purchasesReplaceCashWithPaidWorkAndCompletedAssets() {
    auto s = fixture();
    Engine e(s, campaignRules(), 71);
    const auto checkpoint = e.serialize();
    research(e);
    const auto before = allianceWealth(e.state())[0];
    choose(e, "economy_purchase", [](const auto& a) {
        return a.parameters.require("row").asString() == "japan_major_infantry" &&
               a.parameters.require("price").asString() == "printed";
    });
    const auto paid = allianceWealth(e.state())[0];
    near(before.treasury - paid.treasury, 3, "Infantry did not debit its printed price");
    near(paid.paidConstruction - before.paidConstruction, 3, "Paid unit queue omitted the spent IPP");
    near(paid.total(), before.total(), "Moving cash into a unit queue created or destroyed wealth");
    placementPhase(e);
    choose(e, "economy_place", [](const auto& a) {
        return a.parameters.require("project").asString().find("infantry") != Id::npos;
    });
    const auto placed = allianceWealth(e.state())[0];
    near(placed.units - before.units, 3, "Completed infantry has wrong asset value");
    near(placed.paidConstruction, before.paidConstruction, "Placed unit remained in paid construction");
    near(placed.total(), before.total(), "Unit completion counted paid work and finished unit twice");
    replayMatches(e, checkpoint);

    auto bare = fixture("japan", Phase::Production, true);
    Engine facility(bare, campaignRules(), 73);
    const auto original = allianceWealth(facility.state())[0];
    choose(facility, "economy_purchase", [](const auto& a) {
        return a.parameters.require("row").asString() == "japan_major_minor_port" &&
               a.parameters.require("zone").asString() == tokyo;
    });
    near(allianceWealth(facility.state())[0].total(), original.total(), "Facility purchase changed wealth");
    placementPhase(facility);
    choose(facility, "economy_place");
    const auto completed = allianceWealth(facility.state())[0];
    near(completed.infrastructure - original.infrastructure, 3, "Placed port omitted its completed value");
    near(completed.paidConstruction, original.paidConstruction, "Placed port retained paid work");
    near(completed.total(), original.total(), "Facility completion created wealth from the queue");
}

void stagedShipsScoreOnlyPaidInstallments() {
    auto s = fixture();
    Engine e(s, campaignRules(), 79);
    const auto checkpoint = e.serialize();
    research(e);
    const auto before = allianceWealth(e.state())[0];
    near(before.paidConstruction, 10, "Opening installments changed");
    for (const Id project : {"japan_queue_heavy_cruiser", "japan_queue_fleet_carrier"}) {
        const auto previous = allianceWealth(e.state())[0];
        const auto advance = pick(e, "economy_advance", [&](const auto& a) {
            return a.parameters.require("project").asString() == project;
        });
        e.step(advance);
        const auto next = allianceWealth(e.state())[0];
        near(next.treasury, previous.treasury - 5, "Installment charged the wrong amount");
        near(next.paidConstruction, previous.paidConstruction + 5, "Unpaid ship value appeared in wealth");
        near(next.total(), previous.total(), "Ship installment created a scoring profit");
        const auto exact = e.serialize();
        rejects([&] { e.step(advance); }, "Same installment could be paid twice in one turn");
        check(e.serialize() == exact, "Rejected repeated installment changed state");
    }
    placementPhase(e);
    const auto ready = allianceWealth(e.state())[0];
    choose(e, "economy_place", [](const auto& a) {
        return a.parameters.require("project").asString() == "japan_queue_heavy_cruiser";
    });
    const auto cruiser = allianceWealth(e.state())[0];
    near(cruiser.units, ready.units + 10, "Finished heavy cruiser value differs from its actual payments");
    near(cruiser.paidConstruction, ready.paidConstruction - 10, "Heavy cruiser installment value survived placement");
    near(cruiser.total(), ready.total(), "Ship completion manufactured wealth");
    const auto serial = e.state().clock.playerTurnSerial;
    for (int i = 0; i < 30; ++i) {
        if (e.state().currentNation() == "japan" && e.state().clock.phase == Phase::Production &&
            e.state().clock.playerTurnSerial > serial) break;
        research(e);
        choose(e, "end_phase");
    }
    check(e.state().currentNation() == "japan" && e.state().clock.phase == Phase::Production,
          "Did not advance through real intervening national turns");
    research(e);
    const auto lastPayment = allianceWealth(e.state())[0];
    choose(e, "economy_advance", [](const auto& a) {
        return a.parameters.require("project").asString() == "japan_queue_fleet_carrier";
    });
    near(allianceWealth(e.state())[0].total(), lastPayment.total(), "Final carrier payment created wealth");
    placementPhase(e);
    const auto readyCarrier = allianceWealth(e.state())[0];
    choose(e, "economy_place", [](const auto& a) {
        return a.parameters.require("project").asString() == "japan_queue_fleet_carrier";
    });
    const auto carrier = allianceWealth(e.state())[0];
    near(carrier.units, readyCarrier.units + 15, "Carrier completion ignored approved completed price");
    near(carrier.paidConstruction, 0, "Completed opening ships remained in the queue score");
    near(carrier.total(), readyCarrier.total(), "Carrier placement counted cash/queue/asset more than once");
    replayMatches(e, checkpoint);
}

void bombingAndPaidRepairCannotCreateValue() {
    auto s = fixture("japan", Phase::CombatMovement, true);
    s.territories.at(beiping).possessor = "japan";
    s.territories.at(hopeh).possessor = "kmt";
    s.nations.at("japan").atWarWith.insert("kmt");
    s.nations.at("kmt").atWarWith.insert("japan");
    s.nations.at("kmt").powerStatus = "major";
    s.politics.capitals["kmt"] = "land_china_nanking";
    s.politics.evolutionAwarded.insert("kmt");
    s.facilities["target_factory"] = {"target_factory", "major_factory", hopeh, 0, {}};
    add(s, "bomber", "medium_bomber", "japan", beiping);
    s.captureTurnStart();
    Engine e(s, campaignRules(), 83);
    e.setDiceTapeForTesting({4, 12});
    const auto checkpoint = e.serialize();
    const auto healthy = allianceWealth(e.state())[1];
    choose(e, "air_bomb", [](const auto& a) { return a.parameters.require("target").asString() == "target_factory"; });
    choose(e, "end_phase");
    choose(e, "air_begin_bombing");
    check(e.state().chance && e.state().chance->purpose == "air_bomb_damage", "Expected strategic damage dice");
    e.resolveChance();
    check(e.state().facilities.at("target_factory").damage == 4, "Bombing did not damage the real facility");
    const auto damaged = allianceWealth(e.state())[1];
    near(damaged.infrastructure, healthy.infrastructure - 4, "Damage did not deduct its paid repair cost");
    near(damaged.total(), healthy.total() - 0.4, "Facility damage created an incorrect wealth change");
    check(e.state().chance && e.state().chance->purpose == "air_facility_aa", "Facility AAA was skipped");
    e.resolveChance();
    choose(e, "air_land");
    replayMatches(e, checkpoint);

    auto repairState = e.state().clone();
    repairState.history.clear();
    turn(repairState, "kmt", Phase::Production);
    Engine repaired(repairState, campaignRules(), 89);
    const auto repairCheckpoint = repaired.serialize();
    const auto beforePayment = allianceWealth(repaired.state())[1];
    const auto payment = pick(repaired, "economy_repair", [](const auto& a) {
        return a.parameters.require("target").asString() == "target_factory" &&
               a.parameters.require("damage").asInt() == 4;
    });
    repaired.step(payment);
    const auto prepaid = allianceWealth(repaired.state())[1];
    near(prepaid.treasury, beforePayment.treasury - 4, "Repair did not spend the promised amount");
    near(prepaid.infrastructure, beforePayment.infrastructure + 4, "Paid repair value was lost before completion");
    near(prepaid.total(), beforePayment.total(), "Repair payment created a wealth profit");
    const auto exact = repaired.serialize();
    rejects([&] { repaired.step(payment); }, "Same damaged facility accepted duplicate full repairs");
    check(repaired.serialize() == exact, "Rejected duplicate repair changed state");
    placementPhase(repaired);
    const auto beforeFinish = allianceWealth(repaired.state())[1];
    const auto income = evaluateIncome(repaired.state(), "kmt").total;
    choose(repaired, "end_phase");
    check(repaired.state().facilities.at("target_factory").damage == 0 && repaired.state().repairs.empty(),
          "Placement did not consume the paid repair");
    near(allianceWealth(repaired.state())[1].infrastructure, beforeFinish.infrastructure,
         "Repair completion credited the same work a second time");
    near(allianceWealth(repaired.state())[1].total(), beforeFinish.total() + 0.1 * income,
         "Only legitimate end-turn income may increase wealth during repair completion");
    replayMatches(repaired, repairCheckpoint);
}

void conquestTransfersAssetsAndDoesNotRewardDeclarations() {
    auto s = fixture("japan", Phase::CombatMovement, true);
    s.territories.at(beiping).possessor = "japan";
    s.territories.at(hopeh).possessor = "kmt";
    s.nations.at("japan").atWarWith.insert("kmt");
    s.nations.at("kmt").atWarWith.insert("japan");
    s.facilities["captured_factory"] = {"captured_factory", "minor_factory", hopeh, 0, {}};
    add(s, "attacker", "infantry", "japan", beiping);
    s.captureTurnStart();
    Engine e(s, campaignRules(), 97);
    const auto checkpoint = e.serialize();
    const auto before = allianceWealth(e.state());
    const auto facilityValue = before[1].infrastructure;
    check(facilityValue > 0, "Capture fixture lacks a valued enemy facility");
    choose(e, "movement_route", [](const auto& a) {
        const auto& path = a.parameters.require("path").asArray();
        return a.parameters.require("unit").asString() == "attacker" && path.size() == 2 &&
               path.back().asString() == hopeh;
    });
    near(allianceWealth(e.state())[0].total(), before[0].total(), "Attack declaration paid an immediate wealth bonus");
    near(allianceWealth(e.state())[1].infrastructure, facilityValue, "Moving before combat stole the defender's factory");
    choose(e, "end_phase");
    choose(e, "land_begin_battle");
    for (int i = 0; i < 20 && e.state().territories.at(hopeh).possessor != "japan"; ++i) {
        if (e.state().chance) e.resolveChance();
        else if (offers(e, "politics_keep_capture")) choose(e, "politics_keep_capture");
        else if (offers(e, "land_progress_battle")) choose(e, "land_progress_battle");
        else {
            std::string kinds;
            for (const auto& action : e.legalActions()) kinds += action.kind + " ";
            throw std::runtime_error("Uncontested capture did not finish; offered " + kinds);
        }
    }
    check(e.state().territories.at(hopeh).possessor == "japan", "Undefended enemy land was not captured");
    const auto captured = allianceWealth(e.state());
    near(captured[0].infrastructure, before[0].infrastructure + facilityValue, "Captured factory was not credited to its possessor");
    near(captured[1].infrastructure, 0, "Former owner retained captured infrastructure value");
    near(captured[0].units, before[0].units, "Ground capture duplicated its attacking unit");
    near(captured[0].treasury, before[0].treasury, "Noncapital capture minted treasury");
    replayMatches(e, checkpoint);
}

void recruitmentAndAlignmentAreOnceOnlyRealAssets() {
    auto s = fixture("ccp", Phase::PlaceUnits, true);
    add(s, "garrison", "infantry", "ccp", shensi);
    add(s, "clique_infantry", "infantry", clique, beiping);
    add(s, "clique_militia", "militia", clique, hopeh);
    s.captureTurnStart();
    Engine e(s, campaignRules(), 101);
    e.setDiceTapeForTesting({1, 1});
    const auto checkpoint = e.serialize();
    const auto before = allianceWealth(e.state())[2];
    const auto recruitment = pick(e, "recruitment_roll", [](const auto& a) {
        return a.parameters.require("beneficiary").asString() == "ccp";
    });
    e.step(recruitment);
    e.resolveChance();
    choose(e, "recruitment_place_infantry");
    const auto recruited = allianceWealth(e.state())[2];
    near(recruited.units, before.units + 3, "Recruited infantry was not valued as one real asset");
    near(recruited.treasury, before.treasury, "Free recruitment minted or spent cash");
    near(recruited.incomeRate, before.incomeRate, "Recruitment changed land income");
    const auto exact = e.serialize();
    rejects([&] { e.step(recruitment); }, "Recruitment could be repeated for a free-asset loop");
    check(e.serialize() == exact, "Rejected repeated recruitment changed state");
    const auto influence = pick(e, "influence_roll", [](const auto& a) {
        return a.parameters.require("target").asString() == clique && a.parameters.require("spend").asInt() == 0;
    });
    e.step(influence);
    e.resolveChance();
    const auto aligned = allianceWealth(e.state())[2];
    check(e.state().units.at("clique_infantry").owner == "ccp" &&
          e.state().units.at("clique_militia").owner == "ccp", "Whole-warlord military assets did not transfer");
    near(aligned.units, recruited.units + 5, "Neutral warlord assets were omitted or already credited before alignment");
    near(aligned.incomeRate, recruited.incomeRate + 3, "Whole-warlord possession did not update tracked income once");
    near(aligned.treasury, recruited.treasury, "Zero-spend influence minted a treasury");
    const auto once = e.serialize();
    rejects([&] { e.step(influence); }, "Alignment could be repeated to farm assets");
    check(e.serialize() == once, "Rejected repeated influence changed state");
    replayMatches(e, checkpoint);
}

void phasePassingOnlyCollectsRealIncomeAndPaysOnceAtTerminal() {
    auto env = CampaignEnv::curriculum(scenario, 1, 103);
    int boundaries = 0;
    for (int i = 0; i < 30 && !env.isTerminal(); ++i) {
        const auto& state = env.engine().state();
        check(env.returns() == std::array<double, 3>{0, 0, 0}, "A nonterminal phase paid wealth");
        const auto nation = state.currentNation();
        const auto cash = state.nations.at(nation).treasury.value_or(0);
        const auto phase = state.clock.phase;
        const auto income = evaluateIncome(state, nation).total;
        const auto wealth = allianceWealth(state);
        const auto actions = env.legalActions();
        auto action = std::find_if(actions.begin(), actions.end(), [](const auto& a) { return a.kind == "end_phase"; });
        if (action == actions.end())
            action = std::find_if(actions.begin(), actions.end(), [](const auto& a) { return a.kind == "economy_finish_research"; });
        check(action != actions.end(), "Peaceful pass unexpectedly required another decision");
        const bool finishTurn = action->kind == "end_phase" && phase == Phase::PlaceUnits;
        env.applyAction(*action);
        const auto next = allianceWealth(env.engine().state());
        for (std::size_t player = 0; player < 3; ++player) {
            near(next[player].units, wealth[player].units, "Passing generated units");
            near(next[player].infrastructure, wealth[player].infrastructure, "Passing generated infrastructure");
            near(next[player].paidConstruction, wealth[player].paidConstruction, "Passing advanced unpaid construction");
        }
        near(env.engine().state().nations.at(nation).treasury.value_or(0) - cash,
             finishTurn ? income : 0, "Passing collected income at an extra phase boundary");
        if (finishTurn) ++boundaries;
    }
    check(env.isTerminal() && boundaries == 4, "One-round curriculum did not finish exactly four real turns");
    const auto exact = env.serialize();
    const auto terminal = env.returns();
    check(terminal == wealthGaps(env.engine().state()), "Terminal did not use the approved three wealth gaps");
    for (int i = 0; i < 5; ++i) check(env.returns() == terminal, "Reading terminal returns accumulated wealth rewards");
    check(env.serialize() == exact && env.legalActions().empty(), "Terminal read advanced the rules state");
    auto restored = env.clone();
    restored.restore(exact);
    check(restored.returns() == terminal && restored.serialize() == exact, "Terminal resume paid a second reward or income");
}
}  // namespace

int main() {
    const std::vector<std::pair<std::string, std::function<void()>>> tests{
        {"cash/paid work/completed unit and facility", purchasesReplaceCashWithPaidWorkAndCompletedAssets},
        {"staged ship installment and completion conservation", stagedShipsScoreOnlyPaidInstallments},
        {"real bombing and paid facility repair", bombingAndPaidRepairCannotCreateValue},
        {"capture transfers actual assets", conquestTransfersAssetsAndDoesNotRewardDeclarations},
        {"recruitment and whole-warlord alignment are once-only", recruitmentAndAlignmentAreOnceOnlyRealAssets},
        {"phase passing and true terminal rewards", phasePassingOnlyCollectsRealIncomeAndPaysOnceAtTerminal},
    };
    for (const auto& [name, run] : tests) {
        try { run(); std::cout << "PASS " << name << '\n'; }
        catch (const std::exception& error) { std::cerr << "FAIL " << name << ": " << error.what() << '\n'; return 1; }
    }
}
