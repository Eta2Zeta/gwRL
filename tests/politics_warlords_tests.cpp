#include "game/politics.hpp"
#include "game/catalog.hpp"
#include "game/air.hpp"
#include "game/economy.hpp"
#include "game/land_combat.hpp"
#include "game/movement.hpp"

#include <algorithm>
#include <filesystem>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <tuple>

namespace {
using namespace game::campaign;
using V = game::json::Value;
using O = V::Object;
using A = V::Array;
const Id firstWarlord = "warlord_beiping_hopeh";
const Id secondWarlord = "warlord_tsinghai";

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}
void rejects(const std::function<void()>& action, const std::string& message) {
    try { action(); } catch (const std::exception&) { return; }
    throw std::runtime_error(message);
}
State fixture(const std::vector<std::pair<Id, Id>>& links = {}, bool withDadao = false,
              bool secondActive = false, bool impassable = false) {
    static const auto catalog = Catalog::load(std::filesystem::path(GWRL_SOURCE_DIR) / "game_content/catalog/gw36_v43");
    Definition definition;
    definition.scenarioId = "synthetic_warlord_fixture";
    definition.catalog = catalog;
    definition.players = {"axis", "allies", "comintern"};
    definition.turnOrder = {"ccp", "mongolia", "japan", "kmt"};
    const std::map<Id, Id> original {
        {"w1a", firstWarlord}, {"w1b", firstWarlord}, {"w2", secondWarlord},
        {"ccp_home", "ccp"}, {"kmt_home", "kmt"}, {"japan_home", "japan"},
        {"dadao_home", "japan"}, {"mongolia_home", "mongolia"}, {"separated", "kmt"}
    };
    O nodes;
    for (const auto& [zone, owner] : original) {
        A neighbors;
        for (const auto& [a, b] : links) if (a == zone || b == zone) neighbors.emplace_back(O{
            {"neighbor_id", V(a == zone ? b : a)}, {"impassable", V(impassable)}});
        nodes.emplace(zone, V(O{{"id", V(zone)}, {"type", V(std::string("land"))},
            {"original_owner", V(owner)}, {"ipp_value", V(1.0)},
            {"is_city", V(false)}, {"neighbors", V(std::move(neighbors))}}));
    }
    definition.geography = V(O{{"nodes", V(std::move(nodes))}});
    definition.rules = V(O{});
    for (const auto& id : {Id("ccp"), Id("kmt"), Id("japan"), Id("mongolia"), Id("dadao"), firstWarlord, secondWarlord}) {
        FactionDefinition faction;
        faction.id = id;
        faction.displayName = id;
        faction.homeCountryKnown = true;
        for (const auto& [zone, owner] : original) if (owner == id || id == "ccp" || id == "kmt") faction.homeCountry.insert(zone);
        if (id == "dadao") faction.dormant = true;
        definition.factions.emplace(id, std::move(faction));
    }
    State state;
    state.definition = freezeDefinition(std::move(definition));
    for (const auto& [id, faction] : state.definition->factions) {
        if (id == "dadao") continue;
        NationState nation;
        if (!isWarlord(id)) {
            nation.player = id == "japan" ? "axis" : id == "kmt" ? "allies" : "comintern";
            nation.alliance = nation.player;
            if (id != "mongolia") nation.treasury = 3;
        }
        if (id == "japan") nation.powerStatus = "major";
        state.nations.emplace(nationNumber(state, id), std::move(nation));
    }
    state.nations.at(nationNumber(state, "ccp")).atWarWith.insert(nationNumber(state, "kmt"));
    state.nations.at(nationNumber(state, "kmt")).atWarWith.insert(nationNumber(state, "ccp"));
    for (const auto& [zone, owner] : original) state.territories[zoneNumber(state, zone)] = TerritoryState{nationNumber(state, owner), {}};
    state.territories.at(zoneNumber(state, "w2")).possessor = nationNumber(state, secondActive ? secondWarlord : Id("japan"));
    if (withDadao) {
        ensureDadao(state);
        state.territories.at(zoneNumber(state, "dadao_home")).possessor = nationNumber(state, "dadao");
    }
    for (const auto& [id, type, owner, zone] : std::vector<std::tuple<Id, Id, Id, Id>>{
            {"ccp_guard", "infantry", "ccp", "ccp_home"},
            {"kmt_guard", "infantry", "kmt", "kmt_home"},
            {"w1_guard_a", "infantry", firstWarlord, "w1a"},
            {"w1_guard_b", "militia", firstWarlord, "w1b"}}) {
        UnitState unit;
        unit.id = id; unit.type = type; unit.owner = nationNumber(state, owner); unit.zone = zoneNumber(state, zone);
        unit.turnOrigin = zoneNumber(state, zone); unit.movementAllowance = type == "militia" ? 0 : 1; unit.movementRemaining = unit.movementAllowance;
        state.units.emplace(id, std::move(unit));
    }
    state.clock.nationIndex = 2;
    state.clock.phase = Phase::Combat;
    state.clock.playerTurnSerial = 7;
    state.completedTurns = {{nationNumber(state, "ccp"), 1}, {nationNumber(state, "mongolia"), 1}, {nationNumber(state, "japan"), 0}, {nationNumber(state, "kmt"), 0}};
    state.captureTurnStart();
    return state;
}
void startForeignResolution(State& state, bool freshDeclaration = true) {
    state.politics.foreignChinaWarPending = true;
    state.politics.chinaInvader = nationNumber(state, "japan");
    if (freshDeclaration) state.politics.pending["truce_foreign_declaration"] = V(true);
    beginCombatPoliticalResolution(state);
}
void resolve(State& state, const std::vector<int>& dice) {
    require(state.chance.has_value(), "Expected pending chance request");
    const ChanceRequest request = *state.chance;
    ChanceOutcome outcome;
    for (int die : dice) outcome.faces.push_back({die});
    state.chance.reset();
    require(applyWarlordChance(state, request, outcome), "Warlord service did not handle its own chance");
}
Action option(const State& state, const Id& kind) {
    require(!state.decisions.empty(), "Expected a pending decision");
    for (const auto& action : state.decisions.back().options) if (action.kind == kind) return action;
    throw std::runtime_error("Missing decision option: " + kind);
}
void addUnit(State& state, const Id& id, const Id& type, const Id& owner, const Id& zone) {
    UnitState unit;
    unit.id = id; unit.type = type; unit.owner = nationNumber(state, owner); unit.zone = zoneNumber(state, zone);
    unit.turnOrigin = zoneNumber(state, zone); unit.movementAllowance = 1; unit.movementRemaining = 1;
    state.units.emplace(id, std::move(unit));
}

void wholeWarlordTable() {
    for (const auto& [roll, recipient] : std::vector<std::pair<int, Id>>{
            {1, "ccp"}, {5, "ccp"}, {6, "kmt"}, {10, "kmt"}, {11, "dadao"}, {12, "dadao"}}) {
        auto state = fixture({{"w1a", "ccp_home"}, {"w1b", "dadao_home"}}, true);
        const auto originalIdentity = originalNation(state, zoneNumber(state, "w1a"));
        startForeignResolution(state);
        require(state.chance && state.chance->dice.size() == 1, "Two-zone warlord received more than one die");
        require(state.politics.alignmentQueue == std::vector<NationId>{nationNumber(state, firstWarlord)}, "Queue contains territories rather than factions");
        resolve(state, {roll});
        for (const auto& zone : {"w1a", "w1b"}) require(state.territories.at(zoneNumber(state, zone)).possessor == nationNumber(state, recipient), "Whole-warlord territory result split");
        for (const auto& id : {"w1_guard_a", "w1_guard_b"}) require(state.units.at(id).owner == nationNumber(state, recipient), "Whole-warlord units did not follow result");
        require(state.nations.contains(nationNumber(state, firstWarlord)) && originalNation(state, zoneNumber(state, "w1a")) == originalIdentity,
                "Alignment erased original national identity");
        require(state.nations.at(nationNumber(state, firstWarlord)).gameFlags.at("incorporated") == 1, "Incorporated identity remained active");
    }
    for (const auto& neighbor : {Id("ccp"), Id("dadao")}) for (int roll : {6, 7}) {
        auto state = fixture({{"w1a", neighbor + "_home"}}, true);
        startForeignResolution(state);
        resolve(state, {roll});
        require(state.territories.at(zoneNumber(state, "w1b")).possessor == nationNumber(state, roll == 6 ? neighbor : Id("kmt")), "Single-neighbor boundary wrong");
    }
    auto isolated = fixture({{"w1a", "ccp_home"}}, false, false, true);
    startForeignResolution(isolated);
    require(!isolated.chance && isNation(isolated, isolated.territories.at(zoneNumber(isolated, "w1a")).possessor, "kmt"), "Impassable adjacency produced an alignment roll");
}

void frozenNeighborsAndCheckpoint() {
    auto state = fixture({{"w1a", "ccp_home"}, {"w1b", "w2"}}, false, true);
    startForeignResolution(state);
    const auto serialized = state.serialize();
    auto restored = State::fromJson(state.definition, game::json::parse(serialized));
    auto clone = state.clone();
    require(clone.planningKey() == restored.planningKey(), "Pending alignment was omitted from snapshot");
    resolve(state, {1});
    require(isNation(state, state.territories.at(zoneNumber(state, "w1b")).possessor, "ccp"), "First table result wrong");
    require(isNation(state, state.territories.at(zoneNumber(state, "w2")).possessor, "kmt") && !state.chance,
            "Earlier alignment changed a later warlord's frozen neighbor category");
    require(restored.territories.at(zoneNumber(restored, "w1a")).possessor == nationNumber(restored, firstWarlord), "Clone/checkpoint state mutated with original");
    resolve(restored, {1});
    require(restored.serialize() == state.serialize(), "Checkpoint changed alignment continuation result");
}

void attacksAndDefeatedKmt() {
    for (const auto& attacker : {Id("ccp"), Id("dadao")}) {
        auto state = fixture({}, true, true);
        state.politics.attackedWarlords[nationNumber(state, firstWarlord)].insert(nationNumber(state, attacker));
        beginCombatPoliticalResolution(state);
        require(!state.chance && isNation(state, state.territories.at(zoneNumber(state, "w1a")).possessor, "kmt"), "Chinese attack used foreign-invasion dice");
        require(state.territories.at(zoneNumber(state, "w2")).possessor == nationNumber(state, secondWarlord), "Chinese attack aligned unrelated warlords");
        require(state.units.at("w1_guard_b").owner == nationNumber(state, "kmt"), "Attacked warlord did not transfer its surviving units");
    }
    for (const auto& attacker : {Id("ccp"), Id("dadao")}) {
        auto defeated = fixture({}, true);
        surrenderNation(defeated, nationNumber(defeated, "kmt"), nationNumber(defeated, "ccp"));
        defeated.politics.attackedWarlords[nationNumber(defeated, firstWarlord)].insert(nationNumber(defeated, attacker));
        beginCombatPoliticalResolution(defeated);
        require(defeated.territories.at(zoneNumber(defeated, "w1a")).possessor == nationNumber(defeated, firstWarlord)
                && defeated.politics.surrendered.contains(nationNumber(defeated, "kmt")), "Chinese attack revived surrendered KMT");
    }
    // Automatic KMT and both single-neighbor KMT boundary outcomes retain the
    // table result even after KMT surrendered. Only surviving warlord assets
    // transfer; the surrendered nation's old holdings and awards stay gone.
    for (int roll : {0, 7, 12}) {
        auto defeated = fixture(roll ? std::vector<std::pair<Id, Id>>{{"w1a", "ccp_home"}}
                                     : std::vector<std::pair<Id, Id>>{});
        surrenderNation(defeated, nationNumber(defeated, "kmt"), nationNumber(defeated, "ccp"));
        const auto oldCapitals = defeated.politics.capitals;
        const auto oldAwards = defeated.politics.evolutionAwarded;
        const auto oldFacilities = defeated.facilities.size();
        startForeignResolution(defeated);
        if (roll) resolve(defeated, {roll});
        require(isNation(defeated, defeated.territories.at(zoneNumber(defeated, "w1a")).possessor, "kmt")
                && isNation(defeated, defeated.territories.at(zoneNumber(defeated, "w1b")).possessor, "kmt")
                && defeated.units.at("w1_guard_a").owner == nationNumber(defeated, "kmt")
                && defeated.units.at("w1_guard_b").owner == nationNumber(defeated, "kmt"), "Foreign table did not award the surviving warlord to KMT");
        require(!defeated.politics.surrendered.contains(nationNumber(defeated, "kmt"))
                && !defeated.nations.at(nationNumber(defeated, "kmt")).gameFlags.contains("surrendered"), "Foreign table left KMT inactive");
        require(!defeated.territories.at(zoneNumber(defeated, "kmt_home")).possessor
                && !defeated.territories.at(zoneNumber(defeated, "separated")).possessor
                && !defeated.units.contains("kmt_guard") && defeated.nations.at(nationNumber(defeated, "kmt")).treasury == 0,
                "KMT's pre-surrender assets or cash were restored");
        require(defeated.politics.capitals == oldCapitals && defeated.politics.evolutionAwarded == oldAwards
                && defeated.facilities.size() == oldFacilities, "Foreign table restored a capital or evolution award");
    }

    auto revival = fixture();
    revival.units.erase("ccp_guard");
    refreshPoliticalState(revival);
    revival.clock.nationIndex = 3;
    revival.clock.phase = Phase::CombatMovement;
    recordLandAttack(revival, nationNumber(revival, "kmt"), zoneNumber(revival, "w1a"));
    require(isNation(revival, revival.territories.at(zoneNumber(revival, "w1b")).possessor, "ccp") && revival.units.at("w1_guard_a").owner == nationNumber(revival, "ccp"),
            "KMT attack did not immediately revive CCP through the whole warlord");
    require(!revival.politics.surrendered.contains(nationNumber(revival, "ccp")) && revival.nations.at(nationNumber(revival, "ccp")).gameFlags.at("civil_war_eliminated") == 0,
            "CCP elimination was treated as permanent surrender");
}

void dadaoAlignment() {
    auto chineseAttack = fixture({}, true);
    chineseAttack.politics.pending["dadao_attacked_by"] = V(std::string("ccp"));
    beginCombatPoliticalResolution(chineseAttack);
    require(isNation(chineseAttack, chineseAttack.territories.at(zoneNumber(chineseAttack, "dadao_home")).possessor, "dadao"), "CCP attack incorrectly incorporated Dadao into Japan");
    auto foreignAttack = fixture({}, true);
    addUnit(foreignAttack, "dadao_guard", "infantry", "dadao", "dadao_home");
    foreignAttack.politics.pending["dadao_attacked_by"] = V(std::string("mongolia"));
    beginCombatPoliticalResolution(foreignAttack);
    require(isNation(foreignAttack, foreignAttack.territories.at(zoneNumber(foreignAttack, "dadao_home")).possessor, "japan")
            && foreignAttack.units.at("dadao_guard").owner == nationNumber(foreignAttack, "japan"), "Foreign attack failed Dadao alignment trigger");
    auto twoWars = fixture({}, true);
    twoWars.nations.at(nationNumber(twoWars, "japan")).atWarWith = {nationNumber(twoWars, "ccp"), nationNumber(twoWars, "kmt")};
    twoWars.nations.at(nationNumber(twoWars, "kmt")).powerStatus = "major";
    beginCombatPoliticalResolution(twoWars);
    require(isNation(twoWars, twoWars.territories.at(zoneNumber(twoWars, "dadao_home")).possessor, "japan"), "Japan at war with China and a Major did not align Dadao");
}

void truceConsentAndTiming() {
    auto state = fixture();
    startForeignResolution(state);
    require(!state.politics.chineseTruce && state.decisions.back().nation == "ccp", "Truce activated without consent");
    auto forged = option(state, "truce_offer");
    forged.nation = "kmt";
    rejects([&]{ applyWarlordAction(state, forged); }, "Wrong player offered the truce");
    applyWarlordAction(state, option(state, "truce_offer"));
    require(state.decisions.back().nation == "kmt" && !state.politics.chineseTruce, "Second faction was not asked for consent");
    applyWarlordAction(state, option(state, "truce_accept"));
    require(state.politics.chineseTruce && state.decisions.empty() && !state.politics.truceOfferPending, "Accepted truce not activated/consumed");
    require(politicallyFriendly(state, nationNumber(state, "ccp"), nationNumber(state, "kmt")), "Truce did not expose joint-defense/passage permission");
    require(state.nations.at(nationNumber(state, "ccp")).allies.contains(nationNumber(state, "kmt")) && state.nations.at(nationNumber(state, "kmt")).allies.contains(nationNumber(state, "ccp")),
            "Accepted truce did not list the factions as allies at once");
    require(warlordActions(state).empty(), "Foreign active turn offered Chinese truce break");
    state.clock.nationIndex = 0;
    state.clock.phase = Phase::CombatMovement;
    require(warlordActions(state).empty(), "Combat Movement offered formal truce break");
    rejects([&]{ terminateChineseTruce(state, nationNumber(state, "ccp")); }, "Truce broke before Combat");
    state.clock.phase = Phase::Combat;
    require(warlordActions(state).size() == 1, "Own Combat did not permit truce break without prior commitment");
    applyWarlordAction(state, warlordActions(state).front());
    require(!state.politics.chineseTruce && state.politics.trucePermanentlyEnded, "Terminated treaty can be re-signed");
    require(!state.nations.at(nationNumber(state, "ccp")).allies.contains(nationNumber(state, "kmt")) && !state.nations.at(nationNumber(state, "kmt")).allies.contains(nationNumber(state, "ccp")),
            "Broken truce still listed the factions as allies");
    state.clock.nationIndex = 2;
    startForeignResolution(state);
    require(state.decisions.empty(), "Terminated treaty was offered again");

    auto repeatAttack = fixture();
    startForeignResolution(repeatAttack, false);
    require(repeatAttack.decisions.empty(), "Attack during an existing foreign war offered a new truce");
    auto notMajor = fixture();
    notMajor.nations.at(nationNumber(notMajor, "japan")).powerStatus = "minor";
    startForeignResolution(notMajor);
    require(notMajor.decisions.empty(), "Foreign minor attack offered Chinese Truce");
    auto evolved = fixture();
    evolved.nations.at(nationNumber(evolved, "ccp")).powerStatus = "major";
    startForeignResolution(evolved);
    require(evolved.decisions.empty(), "Evolved China was offered a truce");
}

void lowMoraleAndSharedBattles() {
    auto state = fixture();
    state.politics.chineseTruce = true;
    state.clock.nationIndex = 3;
    state.completedTurns.at(nationNumber(state, "japan")) = 1;
    state.units.at("kmt_guard").zone = zoneNumber(state, "ccp_home");
    addUnit(state, "kmt_cavalry", "cavalry", "kmt", "ccp_home");
    addUnit(state, "kmt_militia", "militia", "kmt", "ccp_home");
    addUnit(state, "kmt_separated", "infantry", "kmt", "separated");
    // A preceding normal movement separated this unit; no binding break-intent
    // state is required or added by RCL-007.
    const auto origin = state.units.at("kmt_separated").zone;
    applyWarlordAction(state, warlordActions(state).front());
    require(!state.chance, "Truce termination invented a preliminary Low Morale roll");
    require(state.units.contains("kmt_cavalry") && state.units.contains("kmt_guard") &&
            state.units.contains("kmt_militia"), "Truce termination removed units before their attack rolls");
    require(state.units.at("kmt_separated").zone == origin, "Truce termination moved a separated unit retroactively");
    require(state.battleOrder.size() == 1, "Shared land stack did not produce one battle");
    const auto& battle = state.battles.at(state.battleOrder.front());
    require(battle.stage == "awaiting_combat_rules" && battle.attacker == nationNumber(state, "kmt") && battle.defender == nationNumber(state, "ccp")
            && battle.attackers.size() == 3 && battle.defenders == std::vector<Id>{"ccp_guard"}
            && battle.flags.at("truce_low_morale_eliminates") == 1,
            "Shared-stack battle has wrong sides or lacks the attack-roll elimination rule");
    state.validate();

    auto evolution = fixture();
    evolution.politics.chineseTruce = true;
    evolution.units.at("kmt_guard").zone = zoneNumber(evolution, "ccp_home");
    evolution.nations.at(nationNumber(evolution, "kmt")).powerStatus = "major";
    terminateChineseTruce(evolution, nationNumber(evolution, "kmt"), true);
    require(!evolution.chance && evolution.units.contains("kmt_guard") && evolution.battleOrder.size() == 1
            && evolution.politics.trucePermanentlyEnded, "Evolution wrongly applied voluntary KMT Low Morale or omitted battle");
    require(!evolution.battles.begin()->second.flags.contains("truce_low_morale_eliminates"),
            "Major KMT received the minor-only Low Morale elimination flag");
    auto minorAttacking = fixture();
    minorAttacking.politics.chineseTruce = true;
    minorAttacking.units.at("kmt_guard").zone = zoneNumber(minorAttacking, "ccp_home");
    minorAttacking.nations.at(nationNumber(minorAttacking, "ccp")).powerStatus = "major";
    terminateChineseTruce(minorAttacking, nationNumber(minorAttacking, "ccp"), true);
    require(!minorAttacking.chance && minorAttacking.units.contains("kmt_guard") &&
            minorAttacking.battles.begin()->second.attacker == nationNumber(minorAttacking, "kmt") &&
            minorAttacking.battles.begin()->second.flags.at("truce_low_morale_eliminates") == 1,
            "Automatic Truce ending omitted minor attacking KMT's same-die elimination rule");
}

void invasionAlignsEveryWarlordBeforeTruce() {
    auto state = fixture({{"w1a", "ccp_home"}, {"w1a", "japan_home"},
                          {"w2", "ccp_home"}, {"w2", "japan_home"}}, false, true);
    addUnit(state, "japan_guard", "infantry", "japan", "japan_home");
    state.captureTurnStart();
    auto beforeInvasion = state.clone();
    beforeInvasion.clock.phase = Phase::PlaceUnits;
    require(!influenceActions(beforeInvasion).empty(), "Pre-invasion fixture has no qualifying Japanese influence target");
    state.clock.phase = Phase::CombatMovement;
    recordLandAttack(state, nationNumber(beforeInvasion, "japan"), zoneNumber(state, "w1a"));
    state.clock.phase = Phase::Combat;
    beginCombatPoliticalResolution(state);
    require(state.chance && state.decisions.empty() && !state.politics.chineseTruce,
            "Chinese Truce was offered before the first warlord alignment");
    resolve(state, {7});
    require(state.chance && state.decisions.empty() && !state.politics.chineseTruce,
            "Chinese Truce was offered while another warlord alignment remained");
    resolve(state, {7});
    for (const auto& id : {firstWarlord, secondWarlord})
        require(state.nations.at(nationNumber(state, id)).gameFlags.at("incorporated") == 1,
                "Foreign invasion left an independent warlord before the Truce offer");
    require(!state.chance && state.decisions.back().kind == "truce_offer_decision",
            "Completed invasion alignment did not offer the eligible Truce");
    applyWarlordAction(state, option(state, "truce_offer"));
    applyWarlordAction(state, option(state, "truce_accept"));
    state.clock.phase = Phase::PlaceUnits;
    require(state.politics.chineseTruce && influenceActions(state).empty(),
            "Japan retained a warlord influence target after accepting the Chinese Truce");
}
std::shared_ptr<const Rules> integratedRules() {
    return std::make_shared<PoliticsRules>(std::make_shared<MovementRules>(
        std::make_shared<LandCombatRules>(std::make_shared<AirRules>(std::make_shared<EconomyRules>()))));
}
Action engineOption(Engine& engine,const Id& kind,const Id& unit={}) {
    for(const auto& action:engine.legalActions())
        if(action.kind==kind&&(unit.empty()||(action.parameters.find("unit")&&action.parameters.require("unit").asString()==unit)))return action;
    throw std::runtime_error("Missing integrated political action: "+kind);
}
void temporaryWarlordDefenseDoesNotGrantControl() {
    for(const auto& attacker:{Id("japan"),Id("ccp"),Id("dadao")}) {
        auto state=fixture({{"w1a","japan_home"},{"w1a","ccp_home"}},true);
        if(attacker=="ccp") {state.clock.nationIndex=0;state.clock.playerTurnSerial=0;for(auto& [id,turns]:state.completedTurns)turns=0;}
        state.clock.phase=Phase::CombatMovement;recordLandAttack(state,nationNumber(state, attacker),zoneNumber(state, "w1a"));
        const auto& neutral=state.nations.at(nationNumber(state, firstWarlord));
        require(politicalPlayer(state,nationNumber(state, firstWarlord))=="allies"&&!neutral.player&&!neutral.controllerNation&&!neutral.alliance,
                "Temporary defense changed independent warlord control, alliance, or asset attribution");
        require(state.territories.at(zoneNumber(state, "w1a")).possessor==nationNumber(state, firstWarlord)&&state.units.at("w1_guard_a").owner==nationNumber(state, firstWarlord),
                "Warlord was incorporated before combat");
        addUnit(state,"invader","infantry",attacker,"w1a");state.units.at("invader").turnOrigin=zoneNumber(state, attacker=="ccp"?"ccp_home":"japan_home");
        state.units.at("invader").commitments.insert("combat_move");state.clock.phase=Phase::Combat;
        registerLandBattle(state,zoneNumber(state, "w1a"),nationNumber(state, attacker),{"invader"},{{"invader",state.units.at("invader").turnOrigin}});
        Engine engine(state,integratedRules());engine.setDiceTapeForTesting({1,12});const auto checkpoint=engine.serialize();
        engine.step(engineOption(engine,"land_begin_battle"));engine.resolveChance();
        require(engine.state().decisionPlayer()=="allies"&&engine.state().decisions.back().nation==firstWarlord,
                "Real warlord casualty choice did not reach temporary defending policy");
        auto restored=Engine::restore(state.definition,integratedRules(),engine.serialize());
        require(restored.state().decisionPlayer()=="allies"&&restored.planningKey()==engine.planningKey(),
                "Temporary warlord defense was not preserved by a pending-decision checkpoint");
        engine.step(engineOption(engine,"land_take_casualty","w1_guard_a"));
        auto replayed=Engine::replay(state.definition,integratedRules(),checkpoint,engine.state().history);
        require(replayed.exactReplayIdentity()==engine.exactReplayIdentity(),"Temporary neutral defense replay diverged");
    }
    auto defeated=fixture({},true);defeated.politics.surrendered.insert(nationNumber(defeated, "kmt"));defeated.clock.phase=Phase::CombatMovement;
    recordLandAttack(defeated,nationNumber(defeated, "dadao"),zoneNumber(defeated, "w1a"));require(politicalPlayer(defeated,nationNumber(defeated, firstWarlord))=="allies","KMT's surrender erased the defensive alliance policy");
    defeated.clock.phase=Phase::Combat;beginCombatPoliticalResolution(defeated);
    require(!defeated.politics.pending.contains("warlord_defense_player:"+firstWarlord)&&
            !defeated.nations.at(nationNumber(defeated, firstWarlord)).player&&!defeated.nations.at(nationNumber(defeated, firstWarlord)).controllerNation,
            "A neutral surviving warlord retained temporary control after combat");
}
void incorporationDoesNotCreateWarWithDadaosController() {
    auto state=fixture({{"w1a","dadao_home"}},true);
    state.clock.phase=Phase::CombatMovement;recordLandAttack(state,nationNumber(state, "japan"),zoneNumber(state, "w1a"));
    state.nations.at(nationNumber(state, firstWarlord)).atWarWith.insert(nationNumber(state, "ccp"));state.nations.at(nationNumber(state, "ccp")).atWarWith.insert(nationNumber(state, firstWarlord));
    state.clock.phase=Phase::Combat;beginCombatPoliticalResolution(state);resolve(state,{1});
    require(isNation(state, state.territories.at(zoneNumber(state, "w1a")).possessor, "dadao")&&controlledBy(state,nationNumber(state, "dadao"),nationNumber(state, "japan")),"Fixture did not align invaded warlord to Dadao");
    require(!state.nations.at(nationNumber(state, "dadao")).atWarWith.contains(nationNumber(state, "japan"))&&!state.nations.at(nationNumber(state, "japan")).atWarWith.contains(nationNumber(state, "dadao")),
            "Incorporation made Dadao fight its Japanese controller");
    require(state.nations.at(nationNumber(state, "dadao")).atWarWith.contains(nationNumber(state, "ccp"))&&state.nations.at(nationNumber(state, "ccp")).atWarWith.contains(nationNumber(state, "dadao")),
            "Fix dropped the warlord's genuinely hostile foreign relations");
    require(state.nations.at(nationNumber(state, firstWarlord)).atWarWith.empty()&&!state.nations.at(nationNumber(state, "japan")).atWarWith.contains(nationNumber(state, firstWarlord))&&
            !state.nations.at(nationNumber(state, "ccp")).atWarWith.contains(nationNumber(state, firstWarlord)),"Incorporated minor retained an independent reciprocal war");
}
void neutralNonparticipantsRelocateToNearestFriendlyLand() {
    auto state=fixture({{"kmt_home","ccp_home"},{"kmt_home","separated"},{"kmt_home","japan_home"}},true);
    state.politics.chineseTruce=true;state.nations.at(nationNumber(state, "dadao")).atWarWith.insert(nationNumber(state, "kmt"));state.nations.at(nationNumber(state, "kmt")).atWarWith.insert(nationNumber(state, "dadao"));
    state.units.erase("kmt_guard");state.units.at("ccp_guard").zone = zoneNumber(state, "kmt_home");
    addUnit(state,"neutral_plane","fighter","ccp","kmt_home");addUnit(state,"captor","infantry","dadao","kmt_home");
    captureLand(state,nationNumber(state, "dadao"),zoneNumber(state, "kmt_home"));
    require(isNation(state, state.territories.at(zoneNumber(state, "kmt_home")).possessor, "dadao")&&state.decisionPlayer()=="comintern",
            "Conquest did not give neutral CCP its relocation choice");
    Engine engine(state,integratedRules());const auto checkpoint=engine.serialize();
    auto restored=Engine::restore(state.definition,integratedRules(),checkpoint);
    require(restored.planningKey()==engine.planningKey(),"Pending neutral relocation was omitted from checkpoint");
    for(const auto& action:engine.legalActions()) {
        const auto zone=action.parameters.require("zone").asString();
        require(action.kind=="politics_relocate_neutral"&&(zone=="ccp_home"||zone=="separated"),"Relocation offered nonfriendly or farther destination");
    }
    for(const auto& unit:{Id("ccp_guard"),Id("neutral_plane")}) {
        auto choice=engineOption(engine,"politics_relocate_neutral",unit);
        const auto destination=choice.parameters.require("zone").asString();engine.step(choice);
        require(engine.state().units.at(unit).zone==zoneNumber(engine.state(), destination)&&engine.state().units.at(unit).owner==nationNumber(engine.state(), "ccp"),
                "Neutral relocation lost unit identity or ignored chosen nearest location");
    }
    require(engine.state().decisions.empty()&&std::none_of(engine.state().politics.pending.begin(),engine.state().politics.pending.end(),[](const auto& item){
        return item.first.rfind("neutral_land_relocation",0)==0||item.first.rfind("politics_neutral_relocation",0)==0;
    }),"Resolved relocations left pending work");
    auto replayed=Engine::replay(state.definition,integratedRules(),checkpoint,engine.state().history);
    require(replayed.exactReplayIdentity()==engine.exactReplayIdentity(),"Neutral relocation choice replay diverged");
    auto distant=fixture({{"kmt_home","w1a"},{"w1a","ccp_home"}},true);
    distant.politics.chineseTruce=true;distant.territories.at(zoneNumber(distant, "separated")).possessor=nationNumber(distant, "japan");
    distant.nations.at(nationNumber(distant, "dadao")).atWarWith.insert(nationNumber(distant, "kmt"));distant.nations.at(nationNumber(distant, "kmt")).atWarWith.insert(nationNumber(distant, "dadao"));distant.units.erase("kmt_guard");
    distant.units.at("ccp_guard").zone = zoneNumber(distant, "kmt_home");addUnit(distant,"captor","infantry","dadao","kmt_home");const auto movement=distant.units.at("ccp_guard").movementRemaining;
    captureLand(distant,nationNumber(distant, "dadao"),zoneNumber(distant, "kmt_home"));
    require(distant.units.at("ccp_guard").zone == zoneNumber(distant, "ccp_home")&&distant.units.at("ccp_guard").movementRemaining==movement,
            "Forced relocation incorrectly required an ordinary move through intervening territory");
}
void neutralRelocationWithoutFriendlyLandUsesAdoptedElimination() {
    auto state=fixture({},true);state.politics.chineseTruce=true;
    state.territories.at(zoneNumber(state, "ccp_home")).possessor=nationNumber(state, "japan");state.territories.at(zoneNumber(state, "separated")).possessor=nationNumber(state, "japan");
    state.units.at("ccp_guard").zone = zoneNumber(state, "kmt_home");state.nations.at(nationNumber(state, "dadao")).atWarWith.insert(nationNumber(state, "kmt"));state.nations.at(nationNumber(state, "kmt")).atWarWith.insert(nationNumber(state, "dadao"));
    addUnit(state,"neutral_plane","fighter","ccp","kmt_home");
    addUnit(state,"neutral_transport","air_transport","ccp","kmt_home");
    addUnit(state,"neutral_cargo","infantry","ccp","kmt_home");
    state.units.at("neutral_transport").cargo={"neutral_cargo"};state.units.at("neutral_cargo").carriedBy="neutral_transport";
    RepairJob repair;repair.id="neutral_repair";repair.owner=nationNumber(state, "ccp");repair.target="neutral_plane";
    state.repairs.emplace(repair.id,repair);
    addUnit(state,"captor","infantry","dadao","kmt_home");state.units.at("captor").turnOrigin = zoneNumber(state, "dadao_home");
    registerLandBattle(state,zoneNumber(state, "kmt_home"),nationNumber(state, "dadao"),{"captor"},{{"captor",zoneNumber(state, "dadao_home")}});
    Engine engine(state,integratedRules());engine.setDiceTapeForTesting({1,12});const auto checkpoint=engine.serialize();
    engine.step(engineOption(engine,"land_begin_battle"));engine.resolveChance();engine.step(engineOption(engine,"land_take_casualty","kmt_guard"));
    const auto beforeResolution=engine.serialize();const auto historyOffset=engine.state().history.size();
    auto restoredPending=Engine::restore(state.definition,integratedRules(),beforeResolution);engine.resolveChance();restoredPending.resolveChance();
    require(restoredPending.exactReplayIdentity()==engine.exactReplayIdentity(),"No-destination destruction lost pending chance/RNG checkpoint identity");
    require(isNation(engine.state(), engine.state().territories.at(zoneNumber(engine.state(), "kmt_home")).possessor, "dadao")&&engine.state().units.contains("captor"),"Adopted relocation consequence rolled back the conquest");
    for(const auto& id:{"ccp_guard","neutral_plane","neutral_transport","neutral_cargo"})
        require(!engine.state().units.contains(id),"No-destination neutral unit or linked cargo survived");
    require(!engine.state().repairs.contains("neutral_repair")&&engine.state().decisions.empty()&&!engine.state().chance,
            "Eliminated neutrals retained repair work or introduced an extra choice/die");
    require(engine.state().units.contains("w1_guard_a")&&engine.state().units.contains("w1_guard_b"),"RCL-015 removed an unrelated neutral unit");
    require(!engine.state().politics.surrendered.contains(nationNumber(engine.state(), "ccp"))&&engine.state().nations.at(nationNumber(engine.state(), "ccp")).gameFlags.at("civil_war_eliminated")==1,
            "No-destination elimination surrendered CCP or failed to refresh its surviving-unit status");
    require(std::none_of(engine.state().politics.pending.begin(),engine.state().politics.pending.end(),[](const auto& item){
        return item.first.rfind("neutral_land_relocation",0)==0||item.first.rfind("politics_neutral_relocation",0)==0;
    }),"Automatic elimination left pending relocation work");
    std::set<Id> destroyed;std::size_t auditEvents=0;
    for(std::size_t i=historyOffset;i<engine.state().history.size();++i) {
        const auto& event=engine.state().history[i];if(event.kind!="unit_destruction")continue;++auditEvents;
        require(event.payload.require("rule").asString()=="RCL-015"&&event.payload.require("authority").asString()=="user_adopted_campaign_interpretation"&&
                event.payload.require("reason").asString()=="no_friendly_land_destination"&&event.payload.require("origin").asString()=="kmt_home",
                "Neutral destruction audit omitted its adopted rule, cause or location");
        for(const auto& unit:event.payload.require("units").asArray()) {
            require(unit.require("owner").asString()=="ccp"&&unit.require("zone").asString()=="kmt_home","Destruction audit lost unit ownership/location");
            destroyed.insert(unit.require("id").asString());
        }
    }
    require(auditEvents==3&&destroyed==std::set<Id>({"ccp_guard","neutral_plane","neutral_transport","neutral_cargo"}),"Destruction log did not account for every neutral and carried unit exactly");
    auto replayed=Engine::replay(state.definition,integratedRules(),checkpoint,engine.state().history);
    require(replayed.exactReplayIdentity()==engine.exactReplayIdentity(),"Input plus destruction-audit replay diverged");
    const std::vector<Event> tail(engine.state().history.begin()+historyOffset,engine.state().history.end());
    auto tailReplay=Engine::replay(state.definition,integratedRules(),beforeResolution,tail);
    require(tailReplay.exactReplayIdentity()==engine.exactReplayIdentity(),"A pending chance checkpoint could not replay a batch of destruction effects");
    auto tampered=tail;tampered.front().payload=V(O{});
    rejects([&]{Engine::replay(state.definition,integratedRules(),beforeResolution,tampered);},"Replay accepted a tampered destruction audit");
    tampered=tail;tampered.erase(tampered.begin());
    rejects([&]{Engine::replay(state.definition,integratedRules(),beforeResolution,tampered);},"Replay accepted a missing destruction audit");
    tampered=tail;tampered.pop_back();
    rejects([&]{Engine::replay(state.definition,integratedRules(),beforeResolution,tampered);},"Replay accepted destruction effects without their causing input");
}
void neutralRelocationDoesNotTreatDisconnectedFriendlyLandAsAbsent() {
    auto state=fixture({},true);state.politics.chineseTruce=true;
    state.territories.at(zoneNumber(state, "separated")).possessor=nationNumber(state, "japan");state.units.at("ccp_guard").zone = zoneNumber(state, "kmt_home");
    state.nations.at(nationNumber(state, "dadao")).atWarWith.insert(nationNumber(state, "kmt"));state.nations.at(nationNumber(state, "kmt")).atWarWith.insert(nationNumber(state, "dadao"));
    addUnit(state,"captor","infantry","dadao","kmt_home");state.units.at("captor").turnOrigin = zoneNumber(state, "dadao_home");
    registerLandBattle(state,zoneNumber(state, "kmt_home"),nationNumber(state, "dadao"),{"captor"},{{"captor",zoneNumber(state, "dadao_home")}});
    Engine engine(state,integratedRules());engine.setDiceTapeForTesting({1,12});
    engine.step(engineOption(engine,"land_begin_battle"));engine.resolveChance();engine.step(engineOption(engine,"land_take_casualty","kmt_guard"));
    const auto before=engine.serialize();rejects([&]{engine.resolveChance();},"Disconnected map was treated as an absence of Friendly possessions");
    require(engine.serialize()==before,"Invalid relocation geography partially changed capture, units, history, or RNG");
}
} // namespace

int main() {
    try {
        const std::vector<std::pair<std::string, std::function<void()>>> checks {
            {"whole-warlord table and atomic identity transfer", wholeWarlordTable},
            {"frozen neighbor categories and pending checkpoint", frozenNeighborsAndCheckpoint},
            {"Chinese attacks, defeated KMT and CCP revival", attacksAndDefeatedKmt},
            {"Dadao alignment triggers", dadaoAlignment},
            {"truce consent, timing and permanent termination", truceConsentAndTiming},
            {"invasion alignment precedes Truce and consumes influence targets", invasionAlignsEveryWarlordBeforeTruce},
            {"Low Morale and shared-stack battle requests", lowMoraleAndSharedBattles},
            {"temporary neutral warlord defense and replay", temporaryWarlordDefenseDoesNotGrantControl},
            {"incorporation preserves only genuinely hostile wars", incorporationDoesNotCreateWarWithDadaosController},
            {"nearest-Friendly neutral relocation and replay", neutralNonparticipantsRelocateToNearestFriendlyLand},
            {"adopted no-destination neutral elimination, cargo and audited replay", neutralRelocationWithoutFriendlyLandUsesAdoptedElimination},
            {"disconnected Friendly land is not absent land", neutralRelocationDoesNotTreatDisconnectedFriendlyLandAsAbsent}
        };
        for (const auto& [name, check] : checks) { check(); std::cout << "PASS " << name << '\n'; }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
}
