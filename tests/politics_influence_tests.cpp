#include "game/politics.hpp"
#include "game/catalog.hpp"

#include <algorithm>
#include <functional>
#include <iostream>
#include <stdexcept>

namespace {
using namespace game::campaign;
using V = game::json::Value;
using O = V::Object;
using A = V::Array;
const auto root = std::filesystem::path(GWRL_SOURCE_DIR);
const Id shensi = "land_china_shensi";
const Id sui = "land_china_suiyuan";
const Id beiping = "land_china_beiping";
const Id hopeh = "land_china_hopeh";
const Id clique = "warlord_beiping_hopeh";
const Id central = "land_mongolia_central_mongolia";
const Id kerulen = "land_mongolia_kerulen";

void check(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}
void rejects(const std::function<void()>& operation, const std::string& message) {
    try { operation(); } catch (const std::exception&) { return; }
    throw std::runtime_error(message);
}
void unit(State& state, const Id& id, const Id& owner, const Id& zone,
          const Id& type = "infantry") {
    UnitState value;
    value.id = id;
    value.type = type;
    value.owner = owner;
    value.zone = value.turnOrigin = zone;
    value.movementAllowance = value.movementRemaining = 1;
    state.units[id] = value;
}

// The source values/identities/catalog are real. Deliberately small synthetic
// adjacency graphs isolate influence counts from future movement/pathfinding.
void borders(State& state, const std::vector<std::tuple<Id, Id, bool>>& edges) {
    auto definition = *state.definition;
    O geography = definition.geography.asObject();
    O nodes = geography.at("nodes").asObject();
    std::map<Id, A> neighbors;
    for (const auto& [a, b, passable] : edges) {
        neighbors[a].push_back(V(O{{"neighbor_id", V(b)}, {"passable", V(passable)}}));
        neighbors[b].push_back(V(O{{"neighbor_id", V(a)}, {"passable", V(passable)}}));
    }
    for (auto& [id, value] : nodes) {
        O node = value.asObject();
        node["neighbors"] = V(neighbors[id]);
        value = V(std::move(node));
    }
    geography["nodes"] = V(std::move(nodes));
    definition.geography = V(std::move(geography));
    state.definition = freezeDefinition(std::move(definition));
}

State fixture(const Id& actor = "ccp") {
    static const auto loaded = loadScenario(root / "game_content/scenarios/japan_china_1936");
    auto state = loaded.clone();
    auto definition = *state.definition;
    if (!definition.factions.contains("dadao"))
        definition.factions["dadao"] = FactionDefinition{"dadao", "Dadao Government", {}, false, true};
    O rules = definition.rules.asObject();
    O politics = rules.contains("politics") ? rules.at("politics").asObject() : O{};
    politics["offshore_land_zone_ids"] = V(A{V(std::string("land_hainan")), V(std::string("land_formosa"))});
    rules["politics"] = V(std::move(politics));
    definition.rules = V(std::move(rules));
    state.definition = freezeDefinition(std::move(definition));
    const auto index = std::find(state.definition->turnOrder.begin(), state.definition->turnOrder.end(), actor);
    state.clock.nationIndex = static_cast<int>(index - state.definition->turnOrder.begin());
    state.clock.playerTurnSerial = static_cast<std::uint64_t>(state.clock.nationIndex);
    state.clock.phase = Phase::PlaceUnits;
    for (std::size_t i = 0; i < state.definition->turnOrder.size(); ++i)
        state.completedTurns[state.definition->turnOrder[i]] = i < static_cast<std::size_t>(state.clock.nationIndex) ? 1 : 0;
    state.units.clear();
    unit(state, "ccp_garrison", "ccp", shensi);
    unit(state, "kmt_garrison", "kmt", "land_china_nanking");
    unit(state, "japan_garrison", "japan", "land_jap_tokyo");
    unit(state, "mongolian_garrison", "mongolia", central, "cavalry");
    unit(state, "warlord_a", clique, beiping);
    unit(state, "warlord_b", clique, hopeh, "militia");
    state.captureTurnStart();
    borders(state, {{shensi, beiping, true}, {shensi, hopeh, true}});
    state.validate();
    return state;
}

std::vector<Action> actions(const State& state, const Id& kind) {
    std::vector<Action> result;
    const auto available = state.decisions.empty() ? influenceActions(state) : state.decisions.back().options;
    for (const auto& action : available) if (action.kind == kind) result.push_back(action);
    return result;
}

Action influence(const State& state, const Id& target, int spend = 0) {
    for (const auto& action : actions(state, "influence_roll"))
        if (action.parameters.require("target").asString() == target
                && action.parameters.require("spend").asInt() == spend) return action;
    throw std::runtime_error("Missing expected influence action");
}

bool hasInfluence(const State& state, const Id& target, int spend = 0) {
    for (const auto& action : actions(state, "influence_roll"))
        if (action.parameters.require("target").asString() == target
                && action.parameters.require("spend").asInt() == spend) return true;
    return false;
}

Action recruitment(const State& state, const Id& beneficiary) {
    for (const auto& action : actions(state, "recruitment_roll"))
        if (action.parameters.require("beneficiary").asString() == beneficiary) return action;
    throw std::runtime_error("Missing expected recruitment roll");
}

void resolve(State& state, int raw) {
    check(state.chance.has_value(), "No pending political chance");
    const auto request = *state.chance;
    state.chance.reset();  // Engine resolves callbacks using a copied request.
    check(applyInfluenceChance(state, request, ChanceOutcome{{{raw}}}), "Chance was not handled");
    state.validate();
}

std::size_t ownedUnits(const State& state, const Id& owner, const Id& type) {
    return static_cast<std::size_t>(std::count_if(state.units.begin(), state.units.end(), [&](const auto& item) {
        return item.second.owner == owner && item.second.type == type;
    }));
}

void wholeWarlordAndUniqueAdjacency() {
    auto state = fixture();
    state.territories.at(sui).possessor = "ccp";
    state.captureTurnStart();
    borders(state, {{shensi, beiping, true}, {shensi, hopeh, true}, {sui, hopeh, true}});
    check(hasInfluence(state, clique, 2), "Whole-warlord adjacent-zone union was not counted");
    check(!hasInfluence(state, clique, 3), "Shared adjacency counted a zone twice");
    applyInfluenceAction(state, influence(state, clique));
    check(pendingPolitical(state, state.chance->continuation).require("threshold").asInt() == 2,
          "Threshold did not include the adjacent unoccupied possession");
    resolve(state, 2);
    check(state.territories.at(beiping).possessor == "ccp" && state.territories.at(hopeh).possessor == "ccp",
          "Influence aligned only one part of the warlord");
    check(state.units.at("warlord_a").owner == "ccp" && state.units.at("warlord_b").owner == "ccp",
          "Influence did not transfer all remaining warlord military units");
    check(!hasInfluence(state, "warlord_suiyuan"), "A second influence attempt was offered this turn");
}

void beginningUnitAndPassability() {
    auto state = fixture();
    borders(state, {{shensi, beiping, false}, {shensi, hopeh, false}});
    check(!hasInfluence(state, clique), "Impassable border allowed influence");
    borders(state, {{shensi, beiping, true}});
    state.turnStart.units.erase("ccp_garrison");
    check(!hasInfluence(state, clique), "Unit newly present this turn established an Influencing Zone");
    state.captureTurnStart();
    check(hasInfluence(state, clique), "Beginning-turn garrison was ignored");
    state.units.at("ccp_garrison").route = {hopeh, shensi};
    check(!hasInfluence(state, clique), "Departed-and-returned unit was treated as a continuous garrison");
    state.units.erase("ccp_garrison");
    check(!hasInfluence(state, clique), "Destroyed garrison still established influence");

    auto allied = fixture();
    allied.politics.chineseTruce = true;
    auto& garrison = allied.units.at("ccp_garrison");
    garrison.owner = "kmt";
    garrison.route = {"land_china_nanking", shensi};
    garrison.turnFlags["placed_this_turn"] = 1;  // Stale from KMT's earlier turn.
    allied.captureTurnStart();
    check(hasInfluence(allied, clique), "Another nation's stale turn flags invalidated a start-present unit");
}

void spendingCapAndPaidBeforeChance() {
    auto state = fixture();
    const int cash = *state.nations.at("ccp").treasury;
    auto invalid = influence(state, clique);
    O parameters = invalid.parameters.asObject();
    parameters["spend"] = V(2.0);
    invalid.parameters = V(parameters);
    const auto before = state.serialize();
    rejects([&] { applyInfluenceAction(state, invalid); }, "Spending beyond the base threshold accepted");
    check(state.serialize() == before, "Rejected influence changed state");
    state.nations.at("ccp").treasury = 0;
    check(!hasInfluence(state, clique, 1), "Insufficient treasury was ignored");
    state.nations.at("ccp").treasury = cash;
    applyInfluenceAction(state, influence(state, clique, 1));
    check(*state.nations.at("ccp").treasury == cash - 1 && state.chance,
          "Influence payment was not recorded before the die roll");
    resolve(state, 2);  // 2 - 1 <= base1.
    check(state.territories.at(hopeh).possessor == "ccp", "Paid modifier did not change success threshold");
}

void failedInfluenceAndNaturalTwelve() {
    auto failed = fixture();
    applyInfluenceAction(failed, influence(failed, clique));
    resolve(failed, 11);
    check(failed.territories.at(beiping).possessor == clique && !hasInfluence(failed, clique),
          "Failed attempt transferred land or did not consume the attempt");

    auto state = fixture("japan");
    std::vector<std::tuple<Id, Id, bool>> edges;
    int adjacent = 0;
    for (auto& [zone, territory] : state.territories) {
        if (zone == beiping || zone == hopeh || zone == shensi || zone == "land_china_nanking"
                || zone == central || adjacent == 12) continue;
        territory.possessor = "japan";
        edges.emplace_back(zone, beiping, true);
        ++adjacent;
    }
    check(adjacent == 12, "Fixture has too few zones for natural12 boundary");
    const auto first = std::get<0>(edges.front());
    unit(state, "japan_influencing_garrison", "japan", first);
    state.captureTurnStart();
    borders(state, edges);
    applyInfluenceAction(state, influence(state, clique, 12));
    resolve(state, 12);  // Even 12 - 12 <= 12 must backfire.
    check(state.territories.at(beiping).possessor == "kmt" && state.territories.at(hopeh).possessor == "kmt",
          "Natural12 was treated as a modified successful roll");
    check(state.units.at("warlord_a").owner == "kmt" && !state.nations.contains("dadao"),
          "Backfire created Dadao or failed whole-warlord transfer");
}

void dadaoRemainsControlledMinorAndJoins() {
    auto state = fixture("japan");
    const auto zone = "land_manchuria_rehe";
    unit(state, "japan_influencing_garrison", "japan", zone);
    state.captureTurnStart();
    borders(state, {{zone, beiping, true}, {zone, hopeh, true}});
    const auto japanLand = possessedLand(state, "japan").size();
    applyInfluenceAction(state, influence(state, clique));
    resolve(state, 1);
    check(state.territories.at(beiping).possessor == "dadao" && state.territories.at(hopeh).possessor == "dadao",
          "Japanese influence did not create the separate Dadao nation");
    const auto& dadao = state.nations.at("dadao");
    check(dadao.controllerNation == "japan" && dadao.player == "axis" && !dadao.treasury,
          "Dadao control created a Japanese possession or a minor treasury");
    check(possessedLand(state, "japan").size() == japanLand && state.units.at("warlord_a").owner == "dadao",
          "Dadao assets were incorporated into Japan");

    // A second turn uses Dadao's controlled possession as an Influencing Zone.
    state.nations.at("japan").turnFlags.clear();
    state.captureTurnStart();
    borders(state, {{beiping, "land_china_tsinghai", true}, {hopeh, "land_china_tsinghai", true}});
    const auto next = "warlord_tsinghai";
    applyInfluenceAction(state, influence(state, next, 2));
    check(pendingPolitical(state, state.chance->continuation).require("threshold").asInt() == 2,
          "Japanese threshold ignored controlled Dadao possessions");
    resolve(state, 4);
    check(state.territories.at("land_china_tsinghai").possessor == "dadao"
          && state.nations.at("dadao").controllerNation == "japan",
          "Subsequent influence did not join the existing Dadao nation");
}

void backfireRevivesOnlyActualWarlordAssets() {
    auto state = fixture();
    state.nations.at("kmt").powerStatus = "major";
    state.politics.capitals["kmt"] = "land_china_nanking";
    state.politics.evolutionAwarded.insert("kmt");
    surrenderNation(state, "kmt", "ccp");
    check(state.politics.surrendered.contains("kmt") && !state.units.contains("kmt_garrison")
          && state.nations.at("kmt").treasury == 0, "Surrender fixture did not remove KMT's old assets");
    const auto facilities = state.facilities.size();
    const auto construction = state.construction.size();
    const auto capitals = state.politics.capitals;
    applyInfluenceAction(state, influence(state, clique, 1));
    resolve(state, 12);
    check(!state.politics.surrendered.contains("kmt") && state.nations.at("kmt").gameFlags.at("surrendered") == 0,
          "Adopted always-backfire could not align with surrendered KMT");
    check(state.territories.at(beiping).possessor == "kmt" && state.territories.at(hopeh).possessor == "kmt"
          && state.units.at("warlord_a").owner == "kmt" && state.units.at("warlord_b").owner == "kmt",
          "Backfire failed to transfer the actual remaining warlord assets");
    check(!state.units.contains("kmt_garrison") && state.nations.at("kmt").treasury == 0
          && state.territories.at("land_china_nanking").possessor != "kmt"
          && state.nations.at("kmt").powerStatus == "major",
          "Backfire resurrected old KMT forces, cash, capital possession or changed its power status");
    check(state.facilities.size() == facilities && state.construction.size() == construction
          && state.politics.capitals == capitals && state.politics.evolutionAwarded.contains("kmt"),
          "Backfire restored a lost capital or repeated once-only awards");
}

void influenceAfterDadaoIncorporation() {
    auto state = fixture("japan");
    ensureDadao(state);
    incorporateNation(state, clique, "dadao");
    incorporateNation(state, "dadao", "japan");
    const auto target = "warlord_tsinghai";
    const auto zone = "land_china_tsinghai";
    unit(state, "next_warlord", target, zone);
    state.captureTurnStart();
    borders(state, {{beiping, zone, true}, {hopeh, zone, true}});
    applyInfluenceAction(state, influence(state, target));
    resolve(state, 1);
    check(state.territories.at(zone).possessor == "japan" && state.units.at("next_warlord").owner == "japan",
          "Japanese success tried to transfer assets into an inactive incorporated Dadao");
    check(possessedLand(state, "dadao").empty() && state.nations.at("dadao").gameFlags.at("incorporated") == 1
          && !state.nations.at("dadao").treasury,
          "Subsequent influence recreated a separate incorporated Dadao or its treasury");
}

void ccpPossessionOnlyAndMajorLoss() {
    auto state = fixture();
    ensureDadao(state);
    state.nations.at("dadao").controllerNation = "ccp";
    state.nations.at("dadao").player = "comintern";
    state.territories.at(sui).possessor = "dadao";
    unit(state, "controlled_garrison", "dadao", sui);
    state.captureTurnStart();
    borders(state, {{shensi, beiping, true}, {sui, hopeh, true}});
    check(hasInfluence(state, clique, 1) && !hasInfluence(state, clique, 2),
          "CCP threshold incorrectly included controlled rather than possessed land");
    state.nations.at("ccp").powerStatus = "major";
    check(actions(state, "influence_roll").empty(), "Evolved CCP retained influence");
    for (const auto& action : actions(state, "recruitment_roll"))
        check(action.parameters.require("beneficiary").asString() != "ccp", "Evolved CCP retained special recruitment");
}

void ccpRecruitmentAndSplitMilitia() {
    auto state = fixture();
    state.territories.at(sui).possessor = "ccp";
    state.captureTurnStart();
    const auto cash = state.nations.at("ccp").treasury;
    applyInfluenceAction(state, recruitment(state, "ccp"));
    check(pendingPolitical(state, state.chance->continuation).require("threshold").asInt() == 2,
          "CCP recruitment did not use its land count");
    resolve(state, 2);
    check(actions(state, "recruitment_advance_ship").empty() && actions(state, "recruitment_repair_facility").empty(),
          "CCP recruitment gained controlled-minor alternatives");
    Action selected;
    bool found = false;
    for (const auto& action : actions(state, "recruitment_place_militia")) {
        const auto& zones = action.parameters.require("zones").asArray();
        if (zones[0].asString() != zones[1].asString()) { selected = action; found = true; break; }
    }
    check(found, "Two militia could not be split across eligible land zones");
    applyInfluenceAction(state, selected);
    check(ownedUnits(state, "ccp", "militia") == 2 && state.nations.at("ccp").treasury == cash,
          "Recruitment did not place two free national militia");
    for (const auto& [id, value] : state.units) if (value.owner == "ccp" && value.type == "militia")
        check(value.movementRemaining == 0 && value.turnFlags.at("placed_this_turn") != 0,
              "Recruited unit gained movement this turn");
    check(actions(state, "recruitment_roll").empty(), "CCP recruited twice in one turn");
}

void recruitmentUsesBeginningPossessionAndHome() {
    auto state = fixture();
    state.territories.at(sui).possessor = "ccp";  // Acquired after snapshot.
    state.territories.at("land_jap_honshu").possessor = "ccp";
    state.turnStart.possessions["land_jap_honshu"] = "ccp";
    applyInfluenceAction(state, recruitment(state, "ccp"));
    resolve(state, 1);
    const auto options = actions(state, "recruitment_place_infantry");
    check(options.size() == 1 && options.front().parameters.require("zone").asString() == shensi,
          "CCP recruitment ignored start-possession or Chinese Home Country");
    state.territories.at(shensi).flags["last_possession_change_turn"] = static_cast<int>(state.clock.playerTurnSerial);
    const auto before = state.serialize();
    rejects([&] { applyInfluenceAction(state, options.front()); }, "Lost-and-retaken recruitment site remained eligible");
    check(state.serialize() == before, "Stale recruitment choice consumed pending work");
}

void mongoliaRecruitmentIsIndependent() {
    auto state = fixture("mongolia");
    const auto infantry = ownedUnits(state, "mongolia", "infantry");
    applyInfluenceAction(state, recruitment(state, "mongolia"));
    check(pendingPolitical(state, state.chance->continuation).require("threshold").asInt() == 4,
          "Mongolia recruitment used unit count or an invented Soviet ledger");
    resolve(state, 4);
    const auto choice = actions(state, "recruitment_place_infantry").front();
    check(choice.player == "comintern" && choice.nation == "mongolia", "Mongolia decision routed incorrectly");
    applyInfluenceAction(state, choice);
    check(ownedUnits(state, "mongolia", "infantry") == infantry + 1
          && !state.nations.contains("ussr") && !state.nations.at("mongolia").treasury,
          "Mongolia recruitment incorporated units or created income");

    auto failed = fixture("mongolia");
    const auto before = failed.units.size();
    applyInfluenceAction(failed, recruitment(failed, "mongolia"));
    resolve(failed, 5);
    check(failed.decisions.empty() && failed.units.size() == before
          && actions(failed, "recruitment_roll").empty(),
          "Failed recruitment placed troops or retained another attempt");
}

void recruitmentMilitiaExemptFromPurchaseQuota() {
    auto state = fixture();  // Shensi's printed IPP is1; it is the only CCP zone.
    applyInfluenceAction(state, recruitment(state, "ccp"));
    resolve(state, 1);
    const auto choices = actions(state, "recruitment_place_militia");
    check(choices.size() == 1, "Single-zone militia fixture changed");
    applyInfluenceAction(state, choices.front());
    check(ownedUnits(state, "ccp", "militia") == 2,
          "Purchased-militia placement cap was incorrectly applied to recruitment");
}

void offshoreThresholdDoesNotForbidPlacement() {
    auto state = fixture("japan");
    ensureDadao(state);
    state.territories.at(beiping).possessor = "dadao";
    state.territories.at("land_hainan").possessor = "dadao";
    state.captureTurnStart();
    applyInfluenceAction(state, recruitment(state, "dadao"));
    check(pendingPolitical(state, state.chance->continuation).require("threshold").asInt() == 1,
          "Offshore Hainan inflated controlled-minor recruitment threshold");
    resolve(state, 1);
    bool offshorePlacement = false;
    for (const auto& action : actions(state, "recruitment_place_infantry"))
        if (action.parameters.require("zone").asString() == "land_hainan") offshorePlacement = true;
    check(offshorePlacement, "Offshore counting exclusion was incorrectly applied to troop placement");
}

void freeShipAdvanceAndFacilityRepair() {
    auto ship = fixture("mongolia");
    ship.construction["minor_ship"] = BuildProject{"minor_ship", "mongolia", "heavy_cruiser", std::nullopt,
        2, 5, {5}, {}};
    const auto cash = ship.nations.at("ccp").treasury;
    const auto units = ship.units.size();
    applyInfluenceAction(ship, recruitment(ship, "mongolia"));
    resolve(ship, 1);
    applyInfluenceAction(ship, actions(ship, "recruitment_advance_ship").front());
    const auto& project = ship.construction.at("minor_ship");
    check(project.queuePosition == 1 && project.remainingPayments.empty() && project.paidIpp == 5
          && project.flags.at("completed") == 1 && ship.units.size() == units,
          "Free ship advancement spent money, inflated paid value or invented placement");
    check(ship.nations.at("ccp").treasury == cash && !ship.nations.at("mongolia").treasury,
          "Controlled-minor queue work changed a national treasury");

    auto repair = fixture("mongolia");
    repair.facilities["minor_repair"] = FacilityState{"minor_repair", "major_factory", central, 9, {}};
    repair.repairs["pending_job"] = RepairJob{"pending_job", "mongolia", "minor_repair", 9, 9, true};
    applyInfluenceAction(repair, recruitment(repair, "mongolia"));
    resolve(repair, 1);
    const auto choices = actions(repair, "recruitment_repair_facility");
    const auto selected = std::find_if(choices.begin(), choices.end(), [](const auto& action) {
        return action.parameters.require("facility").asString() == "minor_repair";
    });
    check(selected != choices.end(), "Full repair alternative missing");
    applyInfluenceAction(repair, *selected);
    check(repair.facilities.at("minor_repair").damage == 0 && !repair.repairs.contains("pending_job"),
          "Recruitment did not fully repair facility or left duplicate pending work");
}

void dadaoRecruitmentAfterJapanSurrenders() {
    auto state = fixture("japan");
    ensureDadao(state);
    state.territories.at(beiping).possessor = "dadao";
    state.captureTurnStart();
    state.construction.clear();  // This fixture isolates surviving Dadao, not surrender ship dice.
    surrenderNation(state, "japan", "kmt");
    check(!state.nations.at("dadao").controllerNation && state.nations.at("dadao").player == "axis"
          && state.nations.at("dadao").gameFlags.at("direct_axis_control_after_japan_surrender") == 1,
          "Japan's fall erased Dadao or changed its approved direct Axis control");
    check(actions(state, "influence_roll").empty(), "Surrendered Japan retained influence");
    applyInfluenceAction(state, recruitment(state, "dadao"));
    resolve(state, 1);
    applyInfluenceAction(state, actions(state, "recruitment_place_infantry").front());
    check(ownedUnits(state, "dadao", "infantry") == 1 && !state.nations.at("dadao").treasury
          && state.territories.at(beiping).possessor == "dadao" && state.currentNation() == "japan",
          "Surviving Dadao lost separate recruitment in the existing Japanese slot");
}

class FixtureRules final : public Rules {
  public:
    Id id() const override { return "m4_influence_recruitment_fixture"; }
    std::vector<Action> actions(const State& state) const override { return influenceActions(state); }
    bool phaseComplete(const State&) const override { return false; }
    void apply(State& state, const Action& action) const override {
        check(applyInfluenceAction(state, action), "Unknown fixture action");
    }
    void applyChance(State& state, const ChanceRequest& request, const ChanceOutcome& outcome) const override {
        check(applyInfluenceChance(state, request, outcome), "Unknown fixture chance");
    }
    void finishTurn(State&) const override { throw std::runtime_error("Fixture has no economy"); }
};

void routingForgeryAndCheckpointReplay() {
    auto state = fixture();
    auto rules = std::make_shared<FixtureRules>();
    Engine engine(state, rules, 319);
    auto forged = influence(state, clique, 1);
    forged.player = "axis";
    const auto before = engine.serialize();
    rejects([&] { engine.step(forged); }, "Wrong player could buy an influence attempt");
    check(engine.serialize() == before, "Rejected influence changed execution state");
    engine.setDiceTapeForTesting({2});
    engine.step(influence(engine.state(), clique, 1));
    const auto checkpoint = engine.serialize();
    auto restored = Engine::restore(state.definition, rules, checkpoint);
    check(restored.state().politics.pending.size() == 1 && restored.state().chance,
          "Influence continuation did not survive checkpoint");
    engine.resolveChance();
    restored.resolveChance();
    check(restored.serialize() == engine.serialize(), "Restored political chance diverged");
    const auto event = engine.state().history.back();
    const auto replay = Engine::replay(state.definition, rules, checkpoint, {event});
    check(replay.serialize() == engine.serialize(), "Political chance replay diverged");

    auto recruitmentState = fixture("mongolia");
    Engine recruitEngine(recruitmentState, rules, 42);
    recruitEngine.setDiceTapeForTesting({1});
    recruitEngine.step(recruitment(recruitEngine.state(), "mongolia"));
    recruitEngine.resolveChance();
    auto wrong = recruitEngine.legalActions().front();
    O parameters = wrong.parameters.asObject();
    parameters["beneficiary"] = V(std::string("japan"));
    wrong.parameters = V(parameters);
    const auto pending = recruitEngine.serialize();
    rejects([&] { recruitEngine.step(wrong); }, "Forged recruitment beneficiary accepted");
    check(recruitEngine.serialize() == pending, "Rejected choice consumed pending recruitment");
    const auto restoredChoice = Engine::restore(recruitmentState.definition, rules, pending);
    check(restoredChoice.planningKey() == recruitEngine.planningKey(), "Pending recruitment choice lost on restore");
}
} // namespace

int main() {
    const std::vector<std::pair<std::string, std::function<void()>>> tests {
        {"whole_warlord_unique_adjacency", wholeWarlordAndUniqueAdjacency},
        {"beginning_unit_passability", beginningUnitAndPassability},
        {"spending_paid_before_chance", spendingCapAndPaidBeforeChance},
        {"failure_natural_twelve", failedInfluenceAndNaturalTwelve},
        {"dadao_control_and_join", dadaoRemainsControlledMinorAndJoins},
        {"backfire_after_kmt_surrender", backfireRevivesOnlyActualWarlordAssets},
        {"influence_after_dadao_incorporation", influenceAfterDadaoIncorporation},
        {"ccp_possession_and_evolution", ccpPossessionOnlyAndMajorLoss},
        {"ccp_recruitment_split_militia", ccpRecruitmentAndSplitMilitia},
        {"recruitment_start_and_home", recruitmentUsesBeginningPossessionAndHome},
        {"mongolia_separate_recruitment", mongoliaRecruitmentIsIndependent},
        {"recruitment_militia_quota_exemption", recruitmentMilitiaExemptFromPurchaseQuota},
        {"offshore_count_not_placement", offshoreThresholdDoesNotForbidPlacement},
        {"ship_advance_full_repair", freeShipAdvanceAndFacilityRepair},
        {"dadao_recruitment_after_japan_surrender", dadaoRecruitmentAfterJapanSurrenders},
        {"routing_checkpoint_replay", routingForgeryAndCheckpointReplay},
    };
    for (const auto& [name, test] : tests) {
        try { test(); std::cout << "PASS " << name << '\n'; }
        catch (const std::exception& error) { std::cerr << "FAIL " << name << ": " << error.what() << '\n'; return 1; }
    }
    std::cout << tests.size() << " influence/recruitment tests passed\n";
}
