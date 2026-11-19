#include "game/politics.hpp"
#include "game/catalog.hpp"
#include "game/movement.hpp"

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
bool flagged(const Marks& flags, const MarkKey& name) { return flags.value(name) != 0; }
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
        state.completedTurns[nationNumber(state, order[i])] = round + (i < static_cast<std::size_t>(state.clock.nationIndex) ? 1 : 0);
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
    unit.type = unitTypeNumber(state, type);
    unit.owner = nationNumber(state, owner);
    unit.zone = unit.turnOrigin = zoneNumber(state, zone);
    unit.movementAllowance = unit.movementRemaining = state.definition->catalog->stats(unitTypeNumber(state, type), 0, catalogContext(state, nationNumber(state, owner), zoneNumber(state, zone))).movement;
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
        return pair.second.zone == zoneNumber(state, zone) && pair.second.type == facilityTypeNumber(state, type);
    }));
}
void prepareTwelveIppKmt(State& state) {
    // Printed 6 + Beiping 2 + Hopeh 1 + Kwangtung 2 + Yunnan 1 = 12.
    for (const auto& zone : {beiping, hopeh, Id("land_kwangtung"), Id("land_china_yunnan")})
        state.territories.at(zoneNumber(state, zone)).possessor = nationNumber(state, "kmt");
    refreshPoliticalState(state);
    check(state.nations.at(nationNumber(state, "kmt")).gameFlags.at(mark::possessed_land_ipp) == 12,
          "Hand-checked evolution fixture no longer totals 12 IPP");
    check(state.nations.at(nationNumber(state, "kmt")).powerStatus == "minor" && state.decisions.empty(),
          "A 12-IPP faction evolved");
}

// RB 6-7: immutable original roundels and explicit Home Country table differ
// from current possession, alliance and the controlling player's identity.
void initialIdentityAndHomeCountry() {
    const auto& state = baseline();
    check(state.nations.size() == 12 && state.definition->factions.size() == 13,
          "Dormant Dadao became an active setup nation");
    check(!hasNation(state, "dadao") && state.definition->factions.at("dadao").dormant,
          "Dadao identity must remain dormant until created");
    for (const auto& [id, faction] : state.definition->factions)
        check(faction.homeCountryKnown, "Unresolved Home Country: " + id);
    check(state.definition->factions.at("mongolia").homeCountry == std::set<Id>({
        "land_mongolia_central_mongolia", "land_mongolia_kerulen",
        "land_mongolia_kobdo", "land_mongolia_ulyassutai"}), "Mongolian original homeland changed");
    check(state.definition->factions.at(guangxi).homeCountry == std::set<Id>({"land_kwangtung"}),
          "Offshore Hainan was incorrectly assigned to Guangxi's mainland homeland");
    check(chineseHomeCountry(state, zoneNumber(state, "land_hainan")) && chineseHomeCountry(state, zoneNumber(state, "land_formosa"))
            && chineseHomeCountry(state, zoneNumber(state, "land_mongolia_kerulen")) && !chineseHomeCountry(state, zoneNumber(state, "land_korea")),
          "Chinese Home Country was confused with original national homelands");
    check(state.definition->factions.at("dadao").homeCountry.empty(), "Dadao inherited a printed homeland");
    const auto& mongolia = state.nations.at(nationNumber(state, "mongolia"));
    check(mongolia.player == "comintern" && mongolia.alliance == "comintern" && !mongolia.controllerNation
            && !mongolia.treasury && mongolia.incomeKnown && mongolia.incomeComponents.empty(),
          "Mongolia's separate direct control/no-account policy changed");
    check(!hasNation(state, "ussr") && state.definition->turnOrder == std::vector<Id>({"ccp", "mongolia", "japan", "kmt"}),
          "An absent Soviet identity or extra calendar turn appeared");
    check(state.units.size() == 99 && state.construction.size() == 2,
          "The loader changed the frozen initial force inventory");
    for (const auto& [id, project] : state.construction)
        check(project.paidIpp == 5 && project.owner == nationNumber(state, "japan"), "Initial ship's already-paid cost changed");
}

// RB 101 / RCL-006: possessed land, not cash or collection, triggers evolution.
void immediateEvolutionOutsideOwnTurn() {
    auto state = fixture("japan", Phase::Combat);
    prepareTwelveIppKmt(state);
    const auto cash = state.nations.at(nationNumber(state, "kmt")).treasury;
    const auto beforeFactories = factoryCount(state, nanking, "major_factory");
    changePossession(state, zoneNumber(state, "land_hainan"), nationNumber(state, "kmt"), PossessionCause::Alignment);
    check(state.nations.at(nationNumber(state, "kmt")).powerStatus == "major" && state.nations.at(nationNumber(state, "kmt")).gameFlags.at(mark::possessed_land_ipp) == 13,
          "The thirteenth possessed IPP did not evolve KMT immediately");
    check(state.nations.at(nationNumber(state, "kmt")).treasury == cash && !state.clock.incomeCollected,
          "Evolution was coupled to cash or income collection");
    check(!decentralizedProduction(state, nationNumber(state, "kmt")), "Outside-turn evolution retained Decentralized Production");
    check(state.decisions.back().nation == "kmt" && state.decisions.back().reaction
            && state.decisionPlayer() == "allies", "Out-of-turn capital choice was routed to the active Japan player");
    chooseCapital(state, nanking);
    check(state.politics.capitals.at(nationNumber(state, "kmt")) == zoneNumber(state, nanking) && factoryCount(state, nanking, "major_factory") == beforeFactories + 1,
          "A city capital did not receive exactly one Major Factory");
    refreshPoliticalState(state);
    check(state.decisions.empty() && factoryCount(state, nanking, "major_factory") == beforeFactories + 1,
          "Evolution and its objective awarded duplicate factories");
    check(originalNation(state, zoneNumber(state, "land_hainan")) == nationNumber(state, guangxi) && originalNation(state, zoneNumber(state, beiping)) == nationNumber(state, "warlord_beiping_hopeh"),
          "Evolution/possession changed original nationality");
}

void ownTurnEvolutionExceptionAndOptionalFactory() {
    auto state = fixture("kmt", Phase::Combat);
    prepareTwelveIppKmt(state);
    state.politics.chineseTruce = true;
    changePossession(state, zoneNumber(state, "land_hainan"), nationNumber(state, "kmt"), PossessionCause::Alignment);
    check(decentralizedProduction(state, nationNumber(state, "kmt")), "Own-turn evolution lost the explicit production grace period");
    check(!state.politics.chineseTruce && state.politics.trucePermanentlyEnded,
          "Evolution did not permanently terminate the Chinese Truce");
    const auto before = factoryCount(state, hunan, "medium_factory");
    chooseCapital(state, hunan);
    check(factoryCount(state, hunan, "medium_factory") == before + 1
            && factoryCount(state, hunan, "major_factory") == 0,
          "A non-city capital received the wrong factory grade");
    turn(state, "kmt", Phase::Production, 1);
    check(!decentralizedProduction(state, nationNumber(state, "kmt")), "Production grace leaked into the next national turn");
    state.validate();

    auto optional = fixture("kmt", Phase::Production);
    prepareTwelveIppKmt(optional);
    changePossession(optional, zoneNumber(optional, "land_hainan"), nationNumber(optional, "kmt"), PossessionCause::Alignment);
    const auto count = optional.facilities.size();
    chooseCapital(optional, hunan, false);
    refreshPoliticalState(optional);
    check(optional.facilities.size() == count && optional.decisions.empty()
            && optional.politics.evolutionAwarded.contains(nationNumber(optional, "kmt")), "Declining the optional factory re-opened the award");
}

void ccpEvolutionLosesMinorActionsImmediately() {
    auto state = fixture("ccp", Phase::PlaceUnits);
    // Shensi 2 + five printed 2-IPP zones + Hainan 1 = 13.
    for (const auto& zone : {beiping, Id("land_kwangtung"), nanking, hunan, Id("land_china_shantung"), Id("land_hainan")})
        state.territories.at(zoneNumber(state, zone)).possessor = nationNumber(state, "ccp");
    refreshPoliticalState(state);
    check(state.nations.at(nationNumber(state, "ccp")).powerStatus == "major" && decentralizedProduction(state, nationNumber(state, "ccp")),
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
        if (isNation(state, territory.possessor, "kmt")) territory.possessor = nationNumber(state, "japan");
    state.territories.at(zoneNumber(state, "land_hainan")).possessor = nationNumber(state, "kmt");
    refreshPoliticalState(state);
    check(flagged(state.nations.at(nationNumber(state, "ccp")).gameFlags, mark::objective_one_china)
            && !state.politics.surrendered.contains(nationNumber(state, "kmt")), "Hainan-only KMT was mistaken for a surrendered faction");
    check(!flagged(state.nations.at(nationNumber(state, "ccp")).gameFlags, mark::one_china_bonus_awarded),
          "The victory-point condition incorrectly awarded units");
    const auto unitCount = state.units.size();
    changePossession(state, zoneNumber(state, "land_hainan"), nationNumber(state, "japan"), PossessionCause::Capture);
    check(state.politics.surrendered.contains(nationNumber(state, "kmt")) && possessedLand(state, nationNumber(state, "kmt")).empty(),
          "KMT did not surrender immediately upon loss of its last land");
    check(std::none_of(state.units.begin(), state.units.end(), [&](const auto& pair) { return pair.second.owner == nationNumber(state, "kmt"); }),
          "Surrender retained KMT military units");
    check(state.units.size() < unitCount, "A surrender bonus was placed at an invented destination");
    std::map<Id, int> awards;
    for (const auto& [id, project] : state.construction) if (flagged(project.flags, mark::national_objective_award)) {
        ++awards[buildTypeName(state, project.type)];
        check(project.owner == nationNumber(state, "ccp") && project.paidIpp == 0 && project.remainingPayments.empty()
                && !project.site && flagged(project.flags, mark::completed), "One China entitlement is not a free completed placement project");
    }
    check(awards == std::map<Id, int>({{"cavalry", 3}, {"infantry", 2}}), "Wrong One China unit entitlement");
    const auto projects = state.construction.size();
    refreshPoliticalState(state);
    surrenderNation(state, nationNumber(state, "kmt"), nationNumber(state, "japan"));
    check(state.construction.size() == projects, "One China bonus repeated");
    state.validate();

    auto ineligible = fixture();
    ineligible.territories.at(zoneNumber(ineligible, shensi)).possessor = nationNumber(ineligible, "japan");
    for (auto& [zone, territory] : ineligible.territories)
        if (isNation(ineligible, territory.possessor, "kmt")) territory.possessor = nationNumber(ineligible, "japan");
    refreshPoliticalState(ineligible);
    check(!flagged(ineligible.nations.at(nationNumber(ineligible, "ccp")).gameFlags, mark::one_china_bonus_awarded),
          "CCP with no land at surrender received the bonus");
    changePossession(ineligible, zoneNumber(ineligible, shensi), nationNumber(ineligible, "ccp"), PossessionCause::Transfer);
    check(!flagged(ineligible.nations.at(nationNumber(ineligible, "ccp")).gameFlags, mark::one_china_bonus_awarded),
          "Later CCP land recovery retroactively qualified for the bonus");
}

void ccpNoUnitsIsNotSurrenderOrGameEnd() {
    auto state = fixture("kmt", Phase::CombatMovement);
    std::set<Id> communistUnits;
    for (const auto& [id, unit] : state.units) if (unit.owner == nationNumber(state, "ccp")) communistUnits.insert(id);
    removePoliticalUnits(state, communistUnits);
    refreshPoliticalState(state);
    check(flagged(state.nations.at(nationNumber(state, "ccp")).gameFlags, mark::civil_war_eliminated)
            && !state.politics.surrendered.contains(nationNumber(state, "ccp")) && !state.terminal,
          "No surviving CCP units became universal surrender or campaign termination");
    check(isNation(state, state.territories.at(zoneNumber(state, shensi)).possessor, "ccp"), "Elimination incorrectly erased CCP land");
    check(mayDeclareWar(state, nationNumber(state, "kmt"), nationNumber(state, "warlord_beiping_hopeh"), DeclarationMode::LandAttack).allowed,
          "KMT's post-elimination warlord permission did not unlock");
    changePossession(state, zoneNumber(state, shensi), nationNumber(state, "japan"), PossessionCause::Capture);
    check(!state.politics.surrendered.contains(nationNumber(state, "ccp")) && !state.terminal, "Landless CCP surrendered");
    rejects([&] { surrenderNation(state, nationNumber(state, "ccp"), nationNumber(state, "japan")); }, "Explicit CCP surrender was accepted");
    state.validate();
}

void captureCapitalAndFacilities() {
    auto state = fixture("kmt");
    state.nations.at(nationNumber(state, "kmt")).atWarWith.insert(nationNumber(state, "japan"));
    state.nations.at(nationNumber(state, "japan")).atWarWith.insert(nationNumber(state, "kmt"));
    const auto conquerorCash = state.nations.at(nationNumber(state, "kmt")).treasury;
    state.facilities.insert_or_assign("test_fort", FacilityState{"test_fort", facilityTypeNumber(state, "fortification"), zoneNumber(state, tokyo)});
    state.facilities.insert_or_assign("test_coast", FacilityState{"test_coast", facilityTypeNumber(state, "coastal_artillery"), zoneNumber(state, tokyo)});
    state.facilities.insert_or_assign("test_factory", FacilityState{"test_factory", facilityTypeNumber(state, "medium_factory"), zoneNumber(state, tokyo)});
    state.construction["test_factory_queue"] = BuildProject{"test_factory_queue", nationNumber(state, "japan"), buildTypeNumber(state, "minor_factory"), tokyo, 2, 4, {4}};
    rejects([&] { captureLand(state, nationNumber(state, "kmt"), zoneNumber(state, tokyo)); }, "Air/naval presence alone established land possession");
    addUnit(state, "surviving_conqueror", "kmt", tokyo);
    captureLand(state, nationNumber(state, "kmt"), zoneNumber(state, tokyo));
    check(isNation(state, state.territories.at(zoneNumber(state, tokyo)).possessor, "kmt") && originalNation(state, zoneNumber(state, tokyo)) == nationNumber(state, "japan"),
          "Capture failed to distinguish possession from original nationality");
    check(state.nations.at(nationNumber(state, "japan")).treasury == 0 && state.nations.at(nationNumber(state, "kmt")).treasury == conquerorCash,
          "Captured capital treasury was looted instead of sent to the bank");
    check(!state.politics.surrendered.contains(nationNumber(state, "japan")), "Japan surrendered before its own turn ended");
    check(!state.facilities.contains("test_fort") && !state.facilities.contains("test_coast")
            && state.facilities.contains("test_factory") && !state.construction.contains("test_factory_queue"),
          "Capture destroyed the wrong facilities or retained facility construction");
    state.validate();
}

void mandatoryLiberationAndProvenWithdrawal() {
    auto state = fixture("kmt");
    // Synthetic alliance relation exercises the common liberation service;
    // this does not change the fixed initial alliance assignments.
    state.nations.at(nationNumber(state, "kmt")).powerStatus = "major";
    state.nations.at(nationNumber(state, "kmt")).alliance = "axis";
    state.territories.at(zoneNumber(state, "land_formosa")).possessor = nationNumber(state, "ccp");
    addUnit(state, "liberating_unit", "kmt", "land_formosa");
    captureLand(state, nationNumber(state, "kmt"), zoneNumber(state, "land_formosa"), {nationNumber(state, "kmt")});
    check(isNation(state, state.territories.at(zoneNumber(state, "land_formosa")).possessor, "japan") && state.decisions.empty(),
          "Optional Chinese gift overrode mandatory allied-major liberation");

    auto noProof = fixture();
    addUnit(noProof, "conqueror", "japan", beiping);
    captureLand(noProof, nationNumber(noProof, "japan"), zoneNumber(noProof, beiping));
    check(noProof.decisions.empty(), "Unaligned Chinese gift guessed a withdrawal route");
    auto proven = fixture();
    addUnit(proven, "conqueror", "japan", beiping);
    addUnit(proven, "returning_aircraft", "japan", beiping, "fighter");
    captureLand(proven, nationNumber(proven, "japan"), zoneNumber(proven, beiping), {nationNumber(proven, "ccp")});
    const auto give = action(proven.decisions.back().options, "politics_give_capture", [](const auto& option) {
        return option.parameters.require("recipient").asString() == "ccp";
    });
    PoliticsRules{}.apply(proven, give);
    check(isNation(proven, proven.territories.at(zoneNumber(proven, beiping)).possessor, "ccp")
            && flagged(proven.units.at("conqueror").turnFlags, mark::must_withdraw_from_chinese_gift),
          "Proven unaligned gift lost the required subsequent withdrawal obligation");
    check(!flagged(proven.units.at("returning_aircraft").turnFlags, mark::must_withdraw_from_chinese_gift),
          "Aircraft received an additional land-conqueror withdrawal obligation instead of ordinary landing");
    check(originalNation(proven, zoneNumber(proven, beiping)) == nationNumber(proven, "warlord_beiping_hopeh"), "Gift erased original nationality");
    proven.validate();
}

void japanSurrenderQueueBoundaryAndReplay() {
    auto state = fixture("japan", Phase::PlaceUnits);
    state.nations.at(nationNumber(state, "japan")).incomeKnown = true;
    state.nations.at(nationNumber(state, "japan")).incomeComponents.clear();
    state.nations.at(nationNumber(state, "japan")).atWarWith.insert(nationNumber(state, "kmt"));
    state.nations.at(nationNumber(state, "kmt")).atWarWith.insert(nationNumber(state, "japan"));
    changePossession(state, zoneNumber(state, tokyo), nationNumber(state, "kmt"), PossessionCause::Capture);
    const auto rules = std::make_shared<PoliticsRules>();
    Engine engine(state, rules, 22);
    engine.setDiceTapeForTesting({7, 8});
    const auto checkpoint = engine.serialize();
    const auto beforeSerial = engine.state().clock.playerTurnSerial;
    engine.step(action(engine.legalActions(), "end_phase"));
    check(engine.state().politics.surrendered.contains(nationNumber(engine.state(), "japan")) && engine.state().chance
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
    check(retained.owner == nationNumber(engine.state(), "kmt") && retained.paidIpp == 5 && retained.remainingPayments == retainedBefore.remainingPayments
            && retained.queuePosition == retainedBefore.queuePosition, "D12 result 8 did not preserve captured ship progress");
    engine.step(action(engine.legalActions(), "end_phase"));
    check(engine.state().currentNationName() == "kmt" && engine.state().clock.playerTurnSerial == beforeSerial + 1,
          "Surrender chance repeated collection or skipped an extra national turn");
    const auto replay = Engine::replay(state.definition, rules, checkpoint, engine.state().history);
    check(replay.exactReplayIdentity() == engine.exactReplayIdentity(), "Surrender chance replay diverged");
}

void directAxisDadaoSurvivesJapan() {
    auto state = fixture("japan", Phase::PlaceUnits);
    ensureDadao(state);
    incorporateNation(state, nationNumber(state, "warlord_beiping_hopeh"), nationNumber(state, "dadao"));
    state.nations.at(nationNumber(state, "dadao")).atWarWith.insert(nationNumber(state, "kmt"));
    state.nations.at(nationNumber(state, "kmt")).atWarWith.insert(nationNumber(state, "dadao"));
    state.construction.clear(); // This case isolates the approved controller fallback.
    state.captureTurnStart();
    std::set<Id> dadaoUnits;
    for (const auto& [id, unit] : state.units) if (unit.owner == nationNumber(state, "dadao")) dadaoUnits.insert(id);
    surrenderNation(state, nationNumber(state, "japan"), nationNumber(state, "kmt"));
    const auto& dadao = state.nations.at(nationNumber(state, "dadao"));
    check(dadao.player == "axis" && dadao.alliance == "axis" && !dadao.controllerNation
            && dadao.powerStatus == "minor" && !dadao.treasury && dadao.incomeKnown && dadao.incomeComponents.empty()
            && flagged(dadao.gameFlags, mark::direct_axis_control_after_japan_surrender),
          "Approved direct Axis Dadao control was not preserved");
    check(possessedLand(state, nationNumber(state, "dadao")) == zoneNumbers(state, {beiping, hopeh}) && dadao.atWarWith.contains(nationNumber(state, "kmt")),
          "Japan's surrender removed separate Dadao land or wars");
    for (const auto& id : dadaoUnits) check(state.units.contains(id) && state.units.at(id).owner == nationNumber(state, "dadao"), "Japan's surrender removed Dadao units");
    check(!mayDeclareWar(state, nationNumber(state, "dadao"), nationNumber(state, "japan")).allowed, "Controlled-minor identity gained ordinary major declarations");
    turn(state, "japan", Phase::PlaceUnits, 1);
    state.captureTurnStart();
    PoliticsRules rules;
    rules.beginTurn(state);
    const auto recruitment = action(rules.actions(state), "recruitment_roll", [](const auto& option) {
        return option.parameters.require("beneficiary").asString() == "dadao";
    });
    check(recruitment.player == "axis" && state.currentNationName() == "japan", "Separate Dadao recruitment left the retained Japanese slot");
    rules.finishTurn(state);
    check(!state.nations.at(nationNumber(state, "dadao")).treasury && state.clock.incomeCollected, "Direct Axis control created an ordinary Dadao income account");
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
    check(!engine.state().nations.at(nationNumber(engine.state(), "kmt")).atWarWith.contains(nationNumber(engine.state(), "japan"))
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
    check(clone.state().nations.at(nationNumber(clone.state(), "ccp")).atWarWith.contains(nationNumber(clone.state(), "japan"))
            && !engine.state().nations.at(nationNumber(engine.state(), "ccp")).atWarWith.contains(nationNumber(engine.state(), "japan"))
            && clone.planningKey() != engine.planningKey(), "Priority clone leaked mutable war/continuation state");
    check(!clone.state().nations.at(nationNumber(clone.state(), "kmt")).atWarWith.contains(nationNumber(clone.state(), "japan")), "One priority declaration prematurely committed the waiting request");
    clone.step(action(clone.legalActions(), "politics_priority_decline"));
    check(clone.state().nations.at(nationNumber(clone.state(), "kmt")).atWarWith.contains(nationNumber(clone.state(), "japan")), "Waiting request did not commit after priority ended");
    const auto restored = Engine::restore(state.definition, rules, engine.serialize());
    check(restored.planningKey() == engine.planningKey() && restored.state().politics.pending.size() == engine.state().politics.pending.size(),
          "Priority checkpoint lost future decision state");
    engine.step(action(engine.legalActions(), "politics_priority_decline"));
    check(engine.state().nations.at(nationNumber(engine.state(), "kmt")).atWarWith.contains(nationNumber(engine.state(), "japan"))
            && !engine.state().nations.at(nationNumber(engine.state(), "ccp")).atWarWith.contains(nationNumber(engine.state(), "japan")), "Declining priority changed the wrong nation's war");
    check(engine.state().clock.playerTurnSerial == state.clock.playerTurnSerial && engine.state().clock.phase == state.clock.phase,
          "A political interrupt advanced the national calendar");
    const auto replay = Engine::replay(state.definition, rules, checkpoint, engine.state().history);
    check(replay.exactReplayIdentity() == engine.exactReplayIdentity(), "Interrupt/action replay diverged");
}

void declarationGatesAndUnknownAccounting() {
    auto state = fixture("japan", Phase::Production);
    check(!mayDeclareWar(state, nationNumber(state, "japan"), nationNumber(state, "warlord_sinkiang")).allowed,
          "A standalone declaration targeted a minor warlord");
    check(!mayDeclareWar(state, nationNumber(state, "japan"), nationNumber(state, "warlord_sinkiang"), DeclarationMode::LandAttack).allowed,
          "Land-attack declaration escaped Combat Movement");
    turn(state, "japan", Phase::CombatMovement);
    check(mayDeclareWar(state, nationNumber(state, "japan"), nationNumber(state, "warlord_sinkiang"), DeclarationMode::LandAttack).allowed,
          "Japan's valid land-attack declaration was unavailable");
    check(!mayDeclareWar(state, nationNumber(state, "ccp"), nationNumber(state, "mongolia"), DeclarationMode::LandAttack).allowed,
          "CCP could declare war against its own alliance");
    check(!mayDeclareWar(state, nationNumber(state, "mongolia"), nationNumber(state, "japan")).allowed, "Direct player control granted Mongolia new-war authority");
    state.nations.at(nationNumber(state, "ccp")).powerStatus = "major";
    state.nations.at(nationNumber(state, "ccp")).atWarWith.insert(nationNumber(state, "japan"));
    state.nations.at(nationNumber(state, "mongolia")).atWarWith.insert(nationNumber(state, "japan"));
    check(!politicallyFriendly(state, nationNumber(state, "ccp"), nationNumber(state, "mongolia")),
          "A common enemy invented a non-incorporating Mongolia/CCP alignment");
    refreshPoliticalState(state);
    check(!state.nations.at(nationNumber(state, "ccp")).allies.contains(nationNumber(state, "mongolia"))
            && !state.nations.at(nationNumber(state, "mongolia")).allies.contains(nationNumber(state, "ccp")),
          "The derived allies cache granted unsupported Mongolia/CCP alignment");
    state.flags[mark::strategic_naval_movement_in_progress] = 1;
    check(PoliticsRules{}.interrupts(state).empty(), "Major-war interrupt occurred during strategic naval movement");
    state.flags.erase(mark::strategic_naval_movement_in_progress);
    turn(state, "japan", Phase::PlaceUnits);
    const auto rules = std::make_shared<PoliticsRules>();
    Engine engine(state, rules);
    const auto before = engine.serialize();
    rejects([&] { engine.step(action(engine.legalActions(), "end_phase")); }, "Politics silently fabricated missing income accounting");
    check(engine.serialize() == before, "Failed unevaluated income collection partially committed a turn");

    auto minor = fixture("mongolia", Phase::PlaceUnits);
    const auto japanCash = minor.nations.at(nationNumber(minor, "japan")).treasury;
    PoliticsRules{}.finishTurn(minor);
    check(minor.clock.incomeCollected && !minor.nations.at(nationNumber(minor, "mongolia")).treasury
            && minor.nations.at(nationNumber(minor, "japan")).treasury == japanCash, "Mongolia collected or redirected ordinary income");
}

// RB 10.10.1's choice to give conquered Chinese land to a Chinese faction is for
// outside Major Powers; an evolved CCP or KMT simply keeps what it conquers.
void chineseFactionsKeepTheirConquests() {
    for (const Id conqueror : {Id("ccp"), Id("kmt")}) {
        auto state = fixture(conqueror);
        state.nations.at(nationNumber(state, conqueror)).powerStatus = "major";
        addUnit(state, "conqueror", conqueror, beiping);
        captureLand(state, nationNumber(state, conqueror), zoneNumber(state, beiping), {nationNumber(state, "ccp"), nationNumber(state, "kmt")});
        check(state.territories.at(zoneNumber(state, beiping)).possessor == nationNumber(state, conqueror)
                && std::none_of(state.decisions.begin(), state.decisions.end(), [](const auto& decision) {
                       return decision.kind == "politics_chinese_liberation"; }),
              "A Chinese faction was offered to give away its own conquest");
    }
}

// A pending capital choice offers only land its nation still possesses.
void capitalChoicesFollowPossession() {
    auto state = fixture("japan", Phase::Combat);
    prepareTwelveIppKmt(state);
    changePossession(state, zoneNumber(state, "land_hainan"), nationNumber(state, "kmt"), PossessionCause::Alignment);
    const auto offered = [&](const Id& zone) {
        const auto& options = state.decisions.back().options;
        return std::any_of(options.begin(), options.end(), [&](const auto& option) {
            return option.parameters.require("zone").asString() == zone; });
    };
    check(state.decisions.back().kind == "politics_evolution" && offered(beiping) && offered(nanking),
          "Evolution did not offer the evolving faction's land");
    changePossession(state, zoneNumber(state, beiping), nationNumber(state, "japan"), PossessionCause::Capture, nationNumber(state, "japan"));
    check(state.decisions.back().kind == "politics_evolution" && !offered(beiping) && offered(nanking),
          "A capital choice still offered land its nation lost");

    // With no land left to offer, the choice is withdrawn rather than left empty.
    auto lone = fixture("japan", Phase::Combat);
    lone.territories.at(zoneNumber(lone, beiping)).possessor = nationNumber(lone, "kmt");
    Action only;
    only.id = "capital_only";
    only.kind = "politics_choose_capital";
    only.parameters = V(O{{"zone", V(beiping)}, {"factory", V(false)}});
    queuePoliticalDecision(lone, nationNumber(lone, "kmt"), "politics_evolution", {only});
    lone.flags[MarkKey(mark::evolution_pending, "kmt")] = 1;
    changePossession(lone, zoneNumber(lone, beiping), nationNumber(lone, "japan"), PossessionCause::Capture, nationNumber(lone, "japan"));
    check(lone.decisions.empty() && !lone.flags.contains(MarkKey(mark::evolution_pending, "kmt")),
          "A capital choice without land stayed pending");
}
// RCL-022 (Q-001 and Q-002): an attack on land that was originally a warlord's,
// the CCP's or the KMT's declares war on all of China, whoever holds the land
// (RB 4.9). Mongolia may start no war (4.5) and none with the CCP of its own
// alliance (5.1), so it may not make that attack; it may still attack land that
// was never Chinese. Japan may start each of those wars, so it may invade.
void onlyNationsFreeToFightAllOfChinaInvadeIt() {
    auto s = fixture("mongolia", Phase::CombatMovement);
    const auto mongolia = nationNumber(s, "mongolia"), kmt = nationNumber(s, "kmt"), japan = nationNumber(s, "japan");
    for (const auto enemy : {kmt, japan}) {
        s.nations.at(mongolia).atWarWith.insert(enemy);
        s.nations.at(enemy).atWarWith.insert(mongolia);
    }
    const Id home = "land_mongolia_central_mongolia", tsinghai = "land_china_tsinghai",
             suiyuan = "land_china_suiyuan", kobdo = "land_mongolia_kobdo";
    s.territories.at(zoneNumber(s, tsinghai)).possessor = kmt;   // the case of Q-001
    s.territories.at(zoneNumber(s, suiyuan)).possessor = japan;  // the case of Q-002
    s.territories.at(zoneNumber(s, kobdo)).possessor = kmt;      // Mongolia's own land, taken
    addUnit(s, "rider", "mongolia", home, "cavalry");
    const auto attack = [&](const State& state, const Id& zone) {
        return validateRoute(state, {"rider", zoneNumbers(state, {home, zone}), MovementMode::Ordinary, true}).allowed;
    };
    check(!attack(s, tsinghai), "Mongolia attacked land the KMT holds that was a warlord's");
    check(!attack(s, suiyuan), "Mongolia attacked land Japan holds that was a warlord's");
    check(attack(s, kobdo), "Mongolia could not retake its own land");
    const auto refusal = mayInvadeChina(s, mongolia, zoneNumber(s, tsinghai));
    check(!refusal.allowed && refusal.reason.find("ccp: Same alliance") != std::string::npos,
          "Mongolia's invasion was not refused for the war with the CCP: " + refusal.reason);
    rejects([&] { auto copy = s.clone(); recordLandAttack(copy, mongolia, zoneNumber(copy, tsinghai)); },
            "recordLandAttack let Mongolia invade China");
    auto empty = s.clone();
    empty.territories.at(zoneNumber(empty, tsinghai)).possessor.reset();
    check(!attack(empty, tsinghai), "Mongolia attacked land nobody holds that was a warlord's");
    check(!s.nations.at(mongolia).atWarWith.contains(nationNumber(s, "ccp")), "Mongolia came to be at war with the CCP");

    auto invader = fixture("japan", Phase::CombatMovement);
    addUnit(invader, "regiment", "japan", "land_manchuria_rehe");
    check(validateRoute(invader, {"regiment", zoneNumbers(invader, {"land_manchuria_rehe", suiyuan}), MovementMode::Ordinary, true}).allowed,
          "Japan could not invade China");
    recordLandAttack(invader, japan, zoneNumber(invader, suiyuan));
    for (const Id china : {"kmt", "ccp", "warlord_yunnan"})
        check(invader.nations.at(japan).atWarWith.contains(nationNumber(invader, china)),
              "Japan's invasion left it at peace with " + china);
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
        {"Chinese factions keep their conquests", chineseFactionsKeepTheirConquests},
        {"capital choices follow possession", capitalChoicesFollowPossession},
        {"Japan surrender queue boundary and replay", japanSurrenderQueueBoundaryAndReplay},
        {"direct Axis Dadao after Japan surrender", directAxisDadaoSurvivesJapan},
        {"out-of-turn declaration priority and replay", outOfTurnPriorityCheckpointAndClone},
        {"declaration gates and unknown accounting", declarationGatesAndUnknownAccounting},
        {"only nations free to fight all of China invade it", onlyNationsFreeToFightAllOfChinaInvadeIt},
    };
    int failures = 0;
    for (const auto& [name, test] : tests) {
        try { test(); std::cout << "PASS " << name << '\n'; }
        catch (const std::exception& error) { ++failures; std::cerr << "FAIL " << name << ": " << error.what() << '\n'; }
    }
    return failures ? 1 : 0;
}
