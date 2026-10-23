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
const auto root = std::filesystem::path(GWRL_SOURCE_DIR);
const Id nanking = "land_china_nanking";
const Id shensi = "land_china_shensi";
const Id hunan = "land_china_hunan";
const Id tokyo = "land_jap_tokyo";
const Id beiping = "land_china_beiping";
const Id hopeh = "land_china_hopeh";
const Id guangxi = "warlord_kwangtung_hainan";

void check(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}
void rejects(const std::function<void()>& operation, const std::string& message) {
    try { operation(); } catch (const std::exception&) { return; }
    throw std::runtime_error(message);
}
bool flagged(const std::map<Id, int>& flags, const Id& name) {
    const auto found = flags.find(name);
    return found != flags.end() && found->second != 0;
}
const State& baseline() {
    // Verify source hashes once, then isolate mutable state for every case.
    static const auto state = loadScenario(root / "game_content/scenarios/japan_china_1936");
    return state;
}
void turn(State& state, const Id& actor, Phase phase, int round = 0) {
    const auto& order = state.definition->turnOrder;
    const auto position = std::find(order.begin(), order.end(), actor);
    check(position != order.end(), "Fixture actor has no national turn");
    state.clock.roundIndex = state.clock.completedRounds = round;
    state.clock.nationIndex = static_cast<int>(position - order.begin());
    state.clock.playerTurnSerial = static_cast<std::uint64_t>(round * order.size() + state.clock.nationIndex);
    state.clock.phase = phase;
    state.clock.incomeCollected = false;
    for (std::size_t i = 0; i < order.size(); ++i)
        state.completedTurns[order[i]] = round + (i < static_cast<std::size_t>(state.clock.nationIndex) ? 1 : 0);
}
State fixture(const Id& actor = "japan", Phase phase = Phase::Combat) {
    auto state = baseline().clone();
    turn(state, actor, phase);
    state.captureTurnStart();
    return state;
}
void addUnit(State& state, const Id& id, const Id& owner, const Id& zone, const Id& type = "infantry") {
    UnitState unit;
    unit.id = id;
    unit.type = type;
    unit.owner = owner;
    unit.zone = unit.turnOrigin = zone;
    unit.movementAllowance = unit.movementRemaining = state.definition->catalog->stats(type, 0, catalogContext(state, owner, zone)).movement;
    state.units.emplace(id, std::move(unit));
}
Action action(const std::vector<Action>& options, const Id& kind,
              const std::function<bool(const Action&)>& matches = [](const Action&) { return true; }) {
    for (const auto& candidate : options)
        if (candidate.kind == kind && matches(candidate)) return candidate;
    throw std::runtime_error("Missing expected action: " + kind);
}
void chooseCapital(State& state, const Id& zone, bool factory = true) {
    check(!state.decisions.empty(), "Evolution failed to queue a capital decision");
    const auto choice = action(state.decisions.back().options, "politics_choose_capital", [&](const auto& option) {
        return option.parameters.require("zone").asString() == zone
            && option.parameters.require("factory").asBool() == factory;
    });
    PoliticsRules{}.apply(state, choice);
    state.validate();
}
std::size_t factoryCount(const State& state, const Id& zone, const Id& type) {
    return static_cast<std::size_t>(std::count_if(state.facilities.begin(), state.facilities.end(), [&](const auto& pair) {
        return pair.second.zone == zone && pair.second.type == type;
    }));
}
void prepareTwelveIppKmt(State& state) {
    // Printed 6 + Beiping 2 + Hopeh 1 + Kwangtung 2 + Yunnan 1 = 12.
    for (const auto& zone : {beiping, hopeh, Id("land_kwangtung"), Id("land_china_yunnan")})
        state.territories.at(zone).possessor = "kmt";
    refreshPoliticalState(state);
    check(state.nations.at("kmt").gameFlags.at("possessed_land_ipp") == 12,
          "Hand-checked evolution fixture no longer totals 12 IPP");
    check(state.nations.at("kmt").powerStatus == "minor" && state.decisions.empty(),
          "A 12-IPP faction evolved");
}

// RB 6-7: immutable original roundels and explicit Home Country table differ
// from current possession, alliance and the controlling player's identity.
void initialIdentityAndHomeCountry() {
    const auto& state = baseline();
    check(state.nations.size() == 12 && state.definition->factions.size() == 13,
          "Dormant Dadao became an active setup nation");
    check(!state.nations.contains("dadao") && state.definition->factions.at("dadao").dormant,
          "Dadao identity must remain dormant until created");
    for (const auto& [id, faction] : state.definition->factions)
        check(faction.homeCountryKnown, "Unresolved M4 Home Country: " + id);
    check(state.definition->factions.at("mongolia").homeCountry == std::set<Id>({
        "land_mongolia_central_mongolia", "land_mongolia_kerulen",
        "land_mongolia_kobdo", "land_mongolia_ulyassutai"}), "Mongolian original homeland changed");
    check(state.definition->factions.at(guangxi).homeCountry == std::set<Id>({"land_kwangtung"}),
          "Offshore Hainan was incorrectly assigned to Guangxi's mainland homeland");
    check(chineseHomeCountry(state, "land_hainan") && chineseHomeCountry(state, "land_formosa")
            && chineseHomeCountry(state, "land_mongolia_kerulen") && !chineseHomeCountry(state, "land_korea"),
          "Chinese Home Country was confused with original national homelands");
    check(state.definition->factions.at("dadao").homeCountry.empty(), "Dadao inherited a printed homeland");
    const auto& mongolia = state.nations.at("mongolia");
    check(mongolia.player == "comintern" && mongolia.alliance == "comintern" && !mongolia.controllerNation
            && !mongolia.treasury && mongolia.incomeKnown && mongolia.incomeComponents.empty(),
          "Mongolia's separate direct control/no-account policy changed");
    check(!state.nations.contains("ussr") && state.definition->turnOrder == std::vector<Id>({"ccp", "mongolia", "japan", "kmt"}),
          "An absent Soviet identity or extra calendar turn appeared");
    check(state.units.size() == 99 && state.construction.size() == 2,
          "M4 loader changed the frozen initial force inventory");
    for (const auto& [id, project] : state.construction)
        check(project.paidIpp == 5 && project.owner == "japan", "Initial ship's already-paid cost changed");
}

// RB 101 / RCL-006: possessed land, not cash or collection, triggers evolution.
void immediateEvolutionOutsideOwnTurn() {
    auto state = fixture("japan", Phase::Combat);
    prepareTwelveIppKmt(state);
    const auto cash = state.nations.at("kmt").treasury;
    const auto beforeFactories = factoryCount(state, nanking, "major_factory");
    changePossession(state, "land_hainan", "kmt", PossessionCause::Alignment);
    check(state.nations.at("kmt").powerStatus == "major" && state.nations.at("kmt").gameFlags.at("possessed_land_ipp") == 13,
          "The thirteenth possessed IPP did not evolve KMT immediately");
    check(state.nations.at("kmt").treasury == cash && !state.clock.incomeCollected,
          "Evolution was coupled to cash or income collection");
    check(!decentralizedProduction(state, "kmt"), "Outside-turn evolution retained Decentralized Production");
    check(state.decisions.back().nation == "kmt" && state.decisions.back().reaction
            && state.decisionPlayer() == "allies", "Out-of-turn capital choice was routed to the active Japan player");
    chooseCapital(state, nanking);
    check(state.politics.capitals.at("kmt") == nanking && factoryCount(state, nanking, "major_factory") == beforeFactories + 1,
          "A city capital did not receive exactly one Major Factory");
    refreshPoliticalState(state);
    check(state.decisions.empty() && factoryCount(state, nanking, "major_factory") == beforeFactories + 1,
          "Evolution and its objective awarded duplicate factories");
    check(originalNation(state, "land_hainan") == guangxi && originalNation(state, beiping) == "warlord_beiping_hopeh",
          "Evolution/possession changed original nationality");
}

void ownTurnEvolutionExceptionAndOptionalFactory() {
    auto state = fixture("kmt", Phase::Combat);
    prepareTwelveIppKmt(state);
    state.politics.chineseTruce = true;
    changePossession(state, "land_hainan", "kmt", PossessionCause::Alignment);
    check(decentralizedProduction(state, "kmt"), "Own-turn evolution lost the explicit production grace period");
    check(!state.politics.chineseTruce && state.politics.trucePermanentlyEnded,
          "Evolution did not permanently terminate the Chinese Truce");
    const auto before = factoryCount(state, hunan, "medium_factory");
    chooseCapital(state, hunan);
    check(factoryCount(state, hunan, "medium_factory") == before + 1
            && factoryCount(state, hunan, "major_factory") == 0,
          "A non-city capital received the wrong factory grade");
    turn(state, "kmt", Phase::Production, 1);
    check(!decentralizedProduction(state, "kmt"), "Production grace leaked into the next national turn");
    state.validate();

    auto optional = fixture("kmt", Phase::Production);
    prepareTwelveIppKmt(optional);
    changePossession(optional, "land_hainan", "kmt", PossessionCause::Alignment);
    const auto count = optional.facilities.size();
    chooseCapital(optional, hunan, false);
    refreshPoliticalState(optional);
    check(optional.facilities.size() == count && optional.decisions.empty()
            && optional.politics.evolutionAwarded.contains("kmt"), "Declining the optional factory re-opened the award");
}

void ccpEvolutionLosesMinorActionsImmediately() {
    auto state = fixture("ccp", Phase::PlaceUnits);
    // Shensi 2 + five printed 2-IPP zones + Hainan 1 = 13.
    for (const auto& zone : {beiping, Id("land_kwangtung"), nanking, hunan, Id("land_china_shantung"), Id("land_hainan")})
        state.territories.at(zone).possessor = "ccp";
    refreshPoliticalState(state);
    check(state.nations.at("ccp").powerStatus == "major" && decentralizedProduction(state, "ccp"),
          "CCP did not evolve while preserving its own-turn production exception");
    chooseCapital(state, shensi, false);
    for (const auto& option : influenceActions(state))
        check(option.kind != "influence_roll" && !(option.kind == "recruitment_roll"
            && option.parameters.require("beneficiary").asString() == "ccp"),
            "Evolved CCP retained minor influence/recruitment during its production grace period");
}

// CCP NRS 2 distinguishes the point condition from the surrender-time award.
void oneChinaPointIsNotSurrenderBonus() {
    auto state = fixture();
    for (auto& [zone, territory] : state.territories)
        if (territory.possessor == "kmt") territory.possessor = "japan";
    state.territories.at("land_hainan").possessor = "kmt";
    refreshPoliticalState(state);
    check(flagged(state.nations.at("ccp").gameFlags, "objective_one_china")
            && !state.politics.surrendered.contains("kmt"), "Hainan-only KMT was mistaken for a surrendered faction");
    check(!flagged(state.nations.at("ccp").gameFlags, "one_china_bonus_awarded"),
          "The victory-point condition incorrectly awarded units");
    const auto unitCount = state.units.size();
    changePossession(state, "land_hainan", "japan", PossessionCause::Capture);
    check(state.politics.surrendered.contains("kmt") && possessedLand(state, "kmt").empty(),
          "KMT did not surrender immediately upon loss of its last land");
    check(std::none_of(state.units.begin(), state.units.end(), [](const auto& pair) { return pair.second.owner == "kmt"; }),
          "Surrender retained KMT military units");
    check(state.units.size() < unitCount, "A surrender bonus was placed at an invented destination");
    std::map<Id, int> awards;
    for (const auto& [id, project] : state.construction) if (flagged(project.flags, "national_objective_award")) {
        ++awards[project.type];
        check(project.owner == "ccp" && project.paidIpp == 0 && project.remainingPayments.empty()
                && !project.site && flagged(project.flags, "completed"), "One China entitlement is not a free completed placement project");
    }
    check(awards == std::map<Id, int>({{"cavalry", 3}, {"infantry", 2}}), "Wrong One China unit entitlement");
    const auto projects = state.construction.size();
    refreshPoliticalState(state);
    surrenderNation(state, "kmt", "japan");
    check(state.construction.size() == projects, "One China bonus repeated");
    state.validate();

    auto ineligible = fixture();
    ineligible.territories.at(shensi).possessor = "japan";
    for (auto& [zone, territory] : ineligible.territories)
        if (territory.possessor == "kmt") territory.possessor = "japan";
    refreshPoliticalState(ineligible);
    check(!flagged(ineligible.nations.at("ccp").gameFlags, "one_china_bonus_awarded"),
          "CCP with no land at surrender received the bonus");
    changePossession(ineligible, shensi, "ccp", PossessionCause::Transfer);
    check(!flagged(ineligible.nations.at("ccp").gameFlags, "one_china_bonus_awarded"),
          "Later CCP land recovery retroactively qualified for the bonus");
}

void ccpNoUnitsIsNotSurrenderOrGameEnd() {
    auto state = fixture("kmt", Phase::CombatMovement);
    std::set<Id> communistUnits;
    for (const auto& [id, unit] : state.units) if (unit.owner == "ccp") communistUnits.insert(id);
    removePoliticalUnits(state, communistUnits);
    refreshPoliticalState(state);
    check(flagged(state.nations.at("ccp").gameFlags, "civil_war_eliminated")
            && !state.politics.surrendered.contains("ccp") && !state.terminal,
          "No surviving CCP units became universal surrender or campaign termination");
    check(state.territories.at(shensi).possessor == "ccp", "Elimination incorrectly erased CCP land");
    check(mayDeclareWar(state, "kmt", "warlord_beiping_hopeh", DeclarationMode::LandAttack).allowed,
          "KMT's post-elimination warlord permission did not unlock");
    changePossession(state, shensi, "japan", PossessionCause::Capture);
    check(!state.politics.surrendered.contains("ccp") && !state.terminal, "Landless CCP surrendered");
    rejects([&] { surrenderNation(state, "ccp", "japan"); }, "Explicit CCP surrender was accepted");
    state.validate();
}

void captureCapitalAndFacilities() {
    auto state = fixture("kmt");
    state.nations.at("kmt").atWarWith.insert("japan");
    state.nations.at("japan").atWarWith.insert("kmt");
    const auto conquerorCash = state.nations.at("kmt").treasury;
    state.facilities["test_fort"] = FacilityState{"test_fort", "fortification", tokyo};
    state.facilities["test_coast"] = FacilityState{"test_coast", "coastal_artillery", tokyo};
    state.facilities["test_factory"] = FacilityState{"test_factory", "medium_factory", tokyo};
    state.construction["test_factory_queue"] = BuildProject{"test_factory_queue", "japan", "minor_factory", tokyo, 2, 4, {4}};
    rejects([&] { captureLand(state, "kmt", tokyo); }, "Air/naval presence alone established land possession");
    addUnit(state, "surviving_conqueror", "kmt", tokyo);
    captureLand(state, "kmt", tokyo);
    check(state.territories.at(tokyo).possessor == "kmt" && originalNation(state, tokyo) == "japan",
          "Capture failed to distinguish possession from original nationality");
    check(state.nations.at("japan").treasury == 0 && state.nations.at("kmt").treasury == conquerorCash,
          "Captured capital treasury was looted instead of sent to the bank");
    check(!state.politics.surrendered.contains("japan"), "Japan surrendered before its own turn ended");
    check(!state.facilities.contains("test_fort") && !state.facilities.contains("test_coast")
            && state.facilities.contains("test_factory") && !state.construction.contains("test_factory_queue"),
          "Capture destroyed the wrong facilities or retained facility construction");
    state.validate();
}

void mandatoryLiberationAndProvenWithdrawal() {
    auto state = fixture("kmt");
    // Synthetic alliance relation exercises the common liberation service;
    // this does not change the fixed initial alliance assignments.
    state.nations.at("kmt").powerStatus = "major";
    state.nations.at("kmt").alliance = "axis";
    state.territories.at("land_formosa").possessor = "ccp";
    addUnit(state, "liberating_unit", "kmt", "land_formosa");
    captureLand(state, "kmt", "land_formosa", {"kmt"});
    check(state.territories.at("land_formosa").possessor == "japan" && state.decisions.empty(),
          "Optional Chinese gift overrode mandatory allied-major liberation");

    auto noProof = fixture();
    addUnit(noProof, "conqueror", "japan", beiping);
    captureLand(noProof, "japan", beiping);
    check(noProof.decisions.empty(), "Unaligned Chinese gift guessed a withdrawal route");
    auto proven = fixture();
    addUnit(proven, "conqueror", "japan", beiping);
    addUnit(proven, "returning_aircraft", "japan", beiping, "fighter");
    captureLand(proven, "japan", beiping, {"ccp"});
    const auto give = action(proven.decisions.back().options, "politics_give_capture", [](const auto& option) {
        return option.parameters.require("recipient").asString() == "ccp";
    });
    PoliticsRules{}.apply(proven, give);
    check(proven.territories.at(beiping).possessor == "ccp"
            && flagged(proven.units.at("conqueror").turnFlags, "must_withdraw_from_chinese_gift"),
          "Proven unaligned gift lost the required subsequent withdrawal obligation");
    check(!flagged(proven.units.at("returning_aircraft").turnFlags, "must_withdraw_from_chinese_gift"),
          "Aircraft received an additional land-conqueror withdrawal obligation instead of ordinary landing");
    check(originalNation(proven, beiping) == "warlord_beiping_hopeh", "Gift erased original nationality");
    proven.validate();
}

void japanSurrenderQueueBoundaryAndReplay() {
    auto state = fixture("japan", Phase::PlaceUnits);
    state.nations.at("japan").incomeKnown = true;
    state.nations.at("japan").incomeComponents.clear();
    state.nations.at("japan").atWarWith.insert("kmt");
    state.nations.at("kmt").atWarWith.insert("japan");
    changePossession(state, tokyo, "kmt", PossessionCause::Capture);
    const auto rules = std::make_shared<PoliticsRules>();
    Engine engine(state, rules, 22);
    engine.setDiceTapeForTesting({7, 8});
    const auto checkpoint = engine.serialize();
    const auto beforeSerial = engine.state().clock.playerTurnSerial;
    engine.step(action(engine.legalActions(), "end_phase"));
    check(engine.state().politics.surrendered.contains("japan") && engine.state().chance
            && engine.state().chance->purpose == "politics_surrender_queues", "Japan's own turn end did not request surrender dice");
    check(engine.state().clock.incomeCollected && engine.state().clock.playerTurnSerial == beforeSerial
            && engine.legalActions().empty() && engine.legalInterrupts().empty(), "Turn advanced before surrender chance resolved");
    const auto ships = pendingPolitical(engine.state(), engine.state().chance->continuation).require("ships").asArray();
    check(ships.size() == 2 && engine.state().chance->dice.size() == 2
            && engine.state().chance->dice.front().sides == 12, "Surrender must roll one D12 for each starting queued ship");
    const auto retainedBefore = engine.state().construction.at(ships[1].asString());
    const auto restoredPending = Engine::restore(state.definition, rules, engine.serialize());
    check(restoredPending.planningKey() == engine.planningKey(), "Surrender checkpoint lost its pending ship list");
    engine.resolveChance();
    check(!engine.state().construction.contains(ships[0].asString()), "D12 result 7 did not scuttle the ship");
    const auto& retained = engine.state().construction.at(ships[1].asString());
    check(retained.owner == "kmt" && retained.paidIpp == 5 && retained.remainingPayments == retainedBefore.remainingPayments
            && retained.queuePosition == retainedBefore.queuePosition, "D12 result 8 did not preserve captured ship progress");
    engine.step(action(engine.legalActions(), "end_phase"));
    check(engine.state().currentNation() == "kmt" && engine.state().clock.playerTurnSerial == beforeSerial + 1,
          "Surrender chance repeated collection or skipped an extra national turn");
    const auto replay = Engine::replay(state.definition, rules, checkpoint, engine.state().history);
    check(replay.exactReplayIdentity() == engine.exactReplayIdentity(), "Surrender chance replay diverged");
}

void directAxisDadaoSurvivesJapan() {
    auto state = fixture("japan", Phase::PlaceUnits);
    ensureDadao(state);
    incorporateNation(state, "warlord_beiping_hopeh", "dadao");
    state.nations.at("dadao").atWarWith.insert("kmt");
    state.nations.at("kmt").atWarWith.insert("dadao");
    state.construction.clear(); // This case isolates the approved controller fallback.
    state.captureTurnStart();
    std::set<Id> dadaoUnits;
    for (const auto& [id, unit] : state.units) if (unit.owner == "dadao") dadaoUnits.insert(id);
    surrenderNation(state, "japan", "kmt");
    const auto& dadao = state.nations.at("dadao");
    check(dadao.player == "axis" && dadao.alliance == "axis" && !dadao.controllerNation
            && dadao.powerStatus == "minor" && !dadao.treasury && dadao.incomeKnown && dadao.incomeComponents.empty()
            && flagged(dadao.gameFlags, "direct_axis_control_after_japan_surrender"),
          "Approved direct Axis Dadao control was not preserved");
    check(possessedLand(state, "dadao") == std::vector<Id>({beiping, hopeh}) && dadao.atWarWith.contains("kmt"),
          "Japan's surrender removed separate Dadao land or wars");
    for (const auto& id : dadaoUnits) check(state.units.contains(id) && state.units.at(id).owner == "dadao", "Japan's surrender removed Dadao units");
    check(!mayDeclareWar(state, "dadao", "japan").allowed, "Controlled-minor identity gained ordinary major declarations");
    turn(state, "japan", Phase::PlaceUnits, 1);
    state.captureTurnStart();
    PoliticsRules rules;
    rules.beginTurn(state);
    const auto recruitment = action(rules.actions(state), "recruitment_roll", [](const auto& option) {
        return option.parameters.require("beneficiary").asString() == "dadao";
    });
    check(recruitment.player == "axis" && state.currentNation() == "japan", "Separate Dadao recruitment left the retained Japanese slot");
    rules.finishTurn(state);
    check(!state.nations.at("dadao").treasury && state.clock.incomeCollected, "Direct Axis control created an ordinary Dadao income account");
    state.validate();
}

void outOfTurnPriorityCheckpointAndClone() {
    auto state = fixture("ccp", Phase::Production);
    const auto rules = std::make_shared<PoliticsRules>();
    Engine engine(state, rules, 7);
    const auto checkpoint = engine.serialize();
    auto declaration = action(engine.legalInterrupts(), "politics_declare_war", [](const auto& option) {
        return option.nation == "kmt" && option.parameters.require("target").asString() == "japan";
    });
    auto forged = declaration;
    forged.player = "axis";
    rejects([&] { engine.interrupt(forged); }, "Another player forged a national declaration");
    check(engine.serialize() == checkpoint, "Rejected interrupt partially mutated the campaign");
    engine.interrupt(declaration);
    check(!engine.state().nations.at("kmt").atWarWith.contains("japan")
            && engine.state().decisions.back().kind == "politics_declaration_priority"
            && engine.state().decisionPlayer() == "comintern", "Out-of-turn declaration bypassed the active player's priority");
    check(engine.legalInterrupts().empty(), "Another interrupt displaced the pending priority response");
    auto clone = engine.clone();
    check(clone.state().definition == engine.state().definition, "Clone copied immutable political source data");
    const auto priority = action(clone.legalActions(), "politics_priority_declare", [](const auto& option) {
        return option.parameters.require("declaring_nation").asString() == "ccp"
            && option.parameters.require("target").asString() == "japan";
    });
    clone.step(priority);
    check(clone.state().nations.at("ccp").atWarWith.contains("japan")
            && !engine.state().nations.at("ccp").atWarWith.contains("japan")
            && clone.planningKey() != engine.planningKey(), "Priority clone leaked mutable war/continuation state");
    check(!clone.state().nations.at("kmt").atWarWith.contains("japan"), "One priority declaration prematurely committed the waiting request");
    clone.step(action(clone.legalActions(), "politics_priority_decline"));
    check(clone.state().nations.at("kmt").atWarWith.contains("japan"), "Waiting request did not commit after priority ended");
    const auto restored = Engine::restore(state.definition, rules, engine.serialize());
    check(restored.planningKey() == engine.planningKey() && restored.state().politics.pending.size() == engine.state().politics.pending.size(),
          "Priority checkpoint lost future decision state");
    engine.step(action(engine.legalActions(), "politics_priority_decline"));
    check(engine.state().nations.at("kmt").atWarWith.contains("japan")
            && !engine.state().nations.at("ccp").atWarWith.contains("japan"), "Declining priority changed the wrong nation's war");
    check(engine.state().clock.playerTurnSerial == state.clock.playerTurnSerial && engine.state().clock.phase == state.clock.phase,
          "A political interrupt advanced the national calendar");
    const auto replay = Engine::replay(state.definition, rules, checkpoint, engine.state().history);
    check(replay.exactReplayIdentity() == engine.exactReplayIdentity(), "Interrupt/action replay diverged");
}

void declarationGatesAndUnknownAccounting() {
    auto state = fixture("japan", Phase::Production);
    check(!mayDeclareWar(state, "japan", "warlord_sinkiang").allowed,
          "A standalone declaration targeted a minor warlord");
    check(!mayDeclareWar(state, "japan", "warlord_sinkiang", DeclarationMode::LandAttack).allowed,
          "Land-attack declaration escaped Combat Movement");
    turn(state, "japan", Phase::CombatMovement);
    check(mayDeclareWar(state, "japan", "warlord_sinkiang", DeclarationMode::LandAttack).allowed,
          "Japan's valid land-attack declaration was unavailable");
    check(!mayDeclareWar(state, "ccp", "mongolia", DeclarationMode::LandAttack).allowed,
          "CCP could declare war against its own alliance");
    check(!mayDeclareWar(state, "mongolia", "japan").allowed, "Direct player control granted Mongolia new-war authority");
    state.nations.at("ccp").powerStatus = "major";
    state.nations.at("ccp").atWarWith.insert("japan");
    state.nations.at("mongolia").atWarWith.insert("japan");
    check(!politicallyFriendly(state, "ccp", "mongolia"),
          "A common enemy invented a non-incorporating Mongolia/CCP alignment");
    refreshPoliticalState(state);
    check(!state.nations.at("ccp").allies.contains("mongolia")
            && !state.nations.at("mongolia").allies.contains("ccp"),
          "The derived allies cache granted unsupported Mongolia/CCP alignment");
    state.flags["strategic_naval_movement_in_progress"] = 1;
    check(PoliticsRules{}.interrupts(state).empty(), "Major-war interrupt occurred during strategic naval movement");
    state.flags.erase("strategic_naval_movement_in_progress");
    turn(state, "japan", Phase::PlaceUnits);
    const auto rules = std::make_shared<PoliticsRules>();
    Engine engine(state, rules);
    const auto before = engine.serialize();
    rejects([&] { engine.step(action(engine.legalActions(), "end_phase")); }, "M4 silently fabricated missing M6 income accounting");
    check(engine.serialize() == before, "Failed unevaluated income collection partially committed a turn");

    auto minor = fixture("mongolia", Phase::PlaceUnits);
    const auto japanCash = minor.nations.at("japan").treasury;
    PoliticsRules{}.finishTurn(minor);
    check(minor.clock.incomeCollected && !minor.nations.at("mongolia").treasury
            && minor.nations.at("japan").treasury == japanCash, "Mongolia collected or redirected ordinary income");
}
} // namespace

int main() {
    const std::vector<std::pair<std::string, std::function<void()>>> tests {
        {"initial identity and source Home Country", initialIdentityAndHomeCountry},
        {"immediate evolution outside own turn", immediateEvolutionOutsideOwnTurn},
        {"own-turn evolution and optional factory", ownTurnEvolutionExceptionAndOptionalFactory},
        {"CCP evolution removes minor actions", ccpEvolutionLosesMinorActionsImmediately},
        {"One China point versus surrender entitlement", oneChinaPointIsNotSurrenderBonus},
        {"CCP elimination is not surrender", ccpNoUnitsIsNotSurrenderOrGameEnd},
        {"capital capture and facility aftermath", captureCapitalAndFacilities},
        {"mandatory liberation and proven withdrawal", mandatoryLiberationAndProvenWithdrawal},
        {"Japan surrender queue boundary and replay", japanSurrenderQueueBoundaryAndReplay},
        {"direct Axis Dadao after Japan surrender", directAxisDadaoSurvivesJapan},
        {"out-of-turn declaration priority and replay", outOfTurnPriorityCheckpointAndClone},
        {"declaration gates and unknown accounting", declarationGatesAndUnknownAccounting},
    };
    int failures = 0;
    for (const auto& [name, test] : tests) {
        try { test(); std::cout << "PASS " << name << '\n'; }
        catch (const std::exception& error) { ++failures; std::cerr << "FAIL " << name << ": " << error.what() << '\n'; }
    }
    return failures ? 1 : 0;
}
