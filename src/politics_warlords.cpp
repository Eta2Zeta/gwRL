#include "game/politics.hpp"
#include "game/catalog.hpp"

#include <algorithm>
#include <stdexcept>

namespace game::campaign {
namespace {
using V = json::Value;
using O = V::Object;
using A = V::Array;

const Id resolutionKey = "warlord_combat_resolution";
Id alignmentKey(const Id& nation) { return "warlord_alignment:" + nation; }
bool flag(const std::map<Id, int>& flags, const Id& key) {
    const auto it = flags.find(key);
    return it != flags.end() && it->second != 0;
}
bool chineseFaction(const Id& nation) {
    return nation == "ccp" || nation == "kmt" || nation == "dadao" || isWarlord(nation);
}
bool activeWarlord(const State& state, const Id& nation) {
    const auto it = state.nations.find(nation);
    if (it == state.nations.end() || !isWarlord(nation)
            || flag(it->second.gameFlags, "incorporated")
            || state.politics.surrendered.contains(nation)) return false;
    return !possessedLand(state, nation).empty()
        || std::any_of(state.units.begin(), state.units.end(), [&](const auto& pair) {
            return pair.second.owner == nation;
        });
}
bool maySignTruce(const State& state) {
    return !state.politics.chineseTruce && !state.politics.trucePermanentlyEnded
        && state.nations.contains("ccp") && state.nations.contains("kmt")
        && state.nations.at("ccp").powerStatus != "major"
        && state.nations.at("kmt").powerStatus != "major"
        && !state.politics.surrendered.contains("kmt");
}
void requireDecision(const State& state, const Action& action, const Id& kind) {
    if (state.decisions.empty() || state.decisions.back().kind != kind
            || action.decision != state.decisions.back().id
            || action.nation != state.decisions.back().nation
            || std::none_of(state.decisions.back().options.begin(), state.decisions.back().options.end(),
                [&](const Action& option) { return canonicalJson(actionJson(option)) == canonicalJson(actionJson(action)); }))
        throw std::runtime_error("Action does not match the pending Chinese Truce decision");
}
void popDecision(State& state) {
    const Id continuation = state.decisions.back().continuation;
    state.decisions.pop_back();
    erasePoliticalContinuation(state, continuation);
}
std::map<Id, std::pair<std::vector<Id>, std::vector<Id>>> mixedChineseStacks(const State& state) {
    std::map<Id, std::pair<std::vector<Id>, std::vector<Id>>> stacks;
    for (const auto& [id, unit] : state.units) {
        // The rule applies in land zones, including aircraft sharing that land.
        if (!state.territories.contains(unit.zone) || unit.carriedBy) continue;
        if (unit.owner == "ccp") stacks[unit.zone].first.push_back(id);
        if (unit.owner == "kmt") stacks[unit.zone].second.push_back(id);
    }
    std::erase_if(stacks, [](const auto& entry) {
        return entry.second.first.empty() || entry.second.second.empty();
    });
    return stacks;
}
void queueSharedBattles(State& state, const Id& breaker) {
    for (const auto& [zone, sides] : mixedChineseStacks(state)) {
        BattleState battle;
        battle.id = "truce_shared_" + std::to_string(state.clock.playerTurnSerial) + "_" + zone;
        battle.zone = zone;
        const auto possessor = state.territories.at(zone).possessor;
        if (!possessor || (*possessor != "ccp" && *possessor != "kmt"))
            throw std::runtime_error("Shared Chinese armies require a Chinese land possessor");
        // RB 0.2 makes the active Chinese faction the attacker, including an
        // automatic termination during its own turn. The developer ruling
        // reported in RCL-012 makes the possessor defend on a third party's turn.
        const auto active = state.currentNation();
        battle.attacker = active == "ccp" || active == "kmt"
            ? active : (*possessor == "ccp" ? "kmt" : "ccp");
        battle.defender = battle.attacker == "ccp" ? "kmt" : "ccp";
        battle.stage = "awaiting_combat_rules";
        battle.attackers = battle.attacker == "ccp" ? sides.first : sides.second;
        battle.defenders = battle.defender == "ccp" ? sides.first : sides.second;
        battle.flags["chinese_truce_termination"] = 1;
        if (battle.attacker == "kmt" && state.nations.at("kmt").powerStatus == "minor")
            battle.flags["truce_low_morale_eliminates"] = 1;
        O origins;
        A landEntries;
        for (const auto& id : battle.attackers) {
            const auto& unit = state.units.at(id);
            // Routes are reset on the owning faction's turn, so off-turn routes
            // cannot establish an entry into this battle during the active turn.
            if (unit.owner != active || !unit.commitments.contains("combat_move") ||
                unit.route.empty() || unit.route.back() != zone) continue;
            const auto from = unit.route.size() > 1
                ? unit.route[unit.route.size() - 2] : unit.turnOrigin;
            if (passableLandBorder(state, from, zone)) {
                origins[id] = V(from);
                if (state.definition->catalog->unit(unit.type).classes.contains("land") &&
                    !unit.commitments.contains("airborne_assault") &&
                    !unit.commitments.contains("amphibious_assault")) landEntries.emplace_back(from);
            }
        }
        battle.data = V(O{{"round", V(1.0)}, {"origins", V(std::move(origins))},
                          {"land_entry_origins", V(std::move(landEntries))},
                          {"truce_breaker", V(breaker)}});
        state.flags["immediate_land_battles"] = 1;
        if (state.battles.contains(battle.id))
            throw std::runtime_error("Chinese Truce battle already queued");
        state.battleOrder.push_back(battle.id);
        state.battles.emplace(battle.id, std::move(battle));
    }
}
void snapshotAlignment(State& state, const Id& warlord, const std::optional<Id>& directRecipient) {
    bool ccp = false;
    bool dadao = false;
    if (!directRecipient) {
        for (const auto& zone : possessedLand(state, warlord)) {
            for (const auto& [neighbor, territory] : state.territories) {
                if ((territory.possessor == "ccp" || territory.possessor == "dadao")
                        && passableLandBorder(state, zone, neighbor)) {
                    ccp = ccp || territory.possessor == "ccp";
                    dadao = dadao || territory.possessor == "dadao";
                }
            }
        }
    }
    state.politics.alignmentQueue.push_back(warlord);
    state.politics.pending[alignmentKey(warlord)] = V(O{
        {"warlord", V(warlord)}, {"ccp_neighbor", V(ccp)}, {"dadao_neighbor", V(dadao)},
        {"recipient", directRecipient ? V(*directRecipient) : V(nullptr)}});
}
void considerDadaoAlignment(State& state) {
    if (!state.nations.contains("dadao") || !controlledBy(state, "dadao", "japan")) {
        state.politics.pending.erase("dadao_attacked_by");
        return;
    }
    bool align = false;
    const auto attack = state.politics.pending.find("dadao_attacked_by");
    if (attack != state.politics.pending.end()) {
        align = !chineseFaction(attack->second.asString());
        state.politics.pending.erase(attack);
    }
    if (state.currentNation() == "japan" && atWarWithMajor(state, "japan")) {
        const auto& enemies = state.nations.at("japan").atWarWith;
        align = align || std::any_of(enemies.begin(), enemies.end(), [](const Id& enemy) {
            return enemy == "ccp" || enemy == "kmt" || isWarlord(enemy);
        });
    }
    if (align) incorporateNation(state, "dadao", "japan");
}
void alignSurvivingNation(State& state, const Id& warlord, const Id& recipient, bool foreign) {
    if (state.politics.surrendered.contains(recipient)) {
        // RB 4.9's defeated-KMT exception applies only to CCP/Dadao attacks.
        // The foreign-invasion table still awards KMT the surviving warlord;
        // this does not restore KMT's former units, possessions or treasury.
        if (!foreign || recipient != "kmt" || !activeWarlord(state, warlord)) return;
        state.politics.surrendered.erase("kmt");
        state.nations.at("kmt").gameFlags.erase("surrendered");
    }
    incorporateNation(state, warlord, recipient);
}
} // namespace

std::vector<Action> warlordActions(const State& state) {
    if (state.terminal || state.chance || !state.decisions.empty()
            || state.clock.phase != Phase::Combat || !state.politics.chineseTruce
            || (state.currentNation() != "ccp" && state.currentNation() != "kmt")) return {};
    return {politicalAction(state, state.currentNation(), "truce_break")};
}

bool applyWarlordAction(State& state, const Action& action) {
    if (action.kind == "truce_break") {
        const auto actions = warlordActions(state);
        if (actions.empty() || canonicalJson(actionJson(actions.front())) != canonicalJson(actionJson(action)))
            throw std::runtime_error("Chinese Truce may only be broken during the faction's own Combat Phase");
        terminateChineseTruce(state, action.nation);
        return true;
    }
    if (action.kind == "truce_offer" || action.kind == "truce_decline_offer") {
        requireDecision(state, action, "truce_offer_decision");
        popDecision(state);
        if (action.kind == "truce_offer" && maySignTruce(state)) {
            queuePoliticalDecision(state, "kmt", "truce_response_decision", {
                politicalAction(state, "kmt", "truce_accept"),
                politicalAction(state, "kmt", "truce_reject")});
        } else {
            state.politics.truceOfferPending = false;
            continueCombatPoliticalResolution(state);
        }
        return true;
    }
    if (action.kind == "truce_accept" || action.kind == "truce_reject") {
        requireDecision(state, action, "truce_response_decision");
        if (action.kind == "truce_accept" && !maySignTruce(state))
            throw std::runtime_error("Chinese Truce is no longer eligible");
        popDecision(state);
        state.politics.truceOfferPending = false;
        if (action.kind == "truce_accept") {
            state.politics.chineseTruce = true;
            refreshAlliances(state);
        }
        continueCombatPoliticalResolution(state);
        return true;
    }
    return false;
}

void beginCombatPoliticalResolution(State& state) {
    if (state.clock.phase != Phase::Combat)
        throw std::runtime_error("Warlord alignment resolves at the end of Combat");
    if (state.politics.pending.contains(resolutionKey)) {
        continueCombatPoliticalResolution(state);
        return;
    }
    // Snapshot all categories before applying any result (RB 4.9; RCL-003).
    const bool foreign = state.politics.foreignChinaWarPending;
    bool truceEligible = false;
    const auto declaration = state.politics.pending.find("truce_foreign_declaration");
    const bool freshDeclaration = declaration != state.politics.pending.end() && declaration->second.asBool();
    state.politics.pending.erase("truce_foreign_declaration");
    if (foreign && freshDeclaration && state.politics.chinaInvader) {
        const auto invader = state.nations.find(*state.politics.chinaInvader);
        truceEligible = invader != state.nations.end() && invader->second.powerStatus == "major";
    }
    state.politics.pending[resolutionKey] = V(O{{"truce_eligible", V(truceEligible)}});
    for (const auto& [nation, info] : state.nations) {
        if (!activeWarlord(state, nation)) continue;
        if (foreign) snapshotAlignment(state, nation, std::nullopt);
        else {
            const auto attacked = state.politics.attackedWarlords.find(nation);
            if (attacked != state.politics.attackedWarlords.end()
                    && (attacked->second.contains("ccp") || attacked->second.contains("dadao"))
                    && !state.politics.surrendered.contains("kmt"))
                snapshotAlignment(state, nation, Id("kmt"));
        }
    }
    state.politics.foreignChinaWarPending = false;
    state.politics.chinaInvader.reset();
    state.politics.attackedWarlords.clear();
    continueCombatPoliticalResolution(state);
}

bool continueCombatPoliticalResolution(State& state) {
    if (state.chance || !state.decisions.empty() || !state.politics.pending.contains(resolutionKey)) return false;
    while (!state.politics.alignmentQueue.empty()) {
        const Id nation = state.politics.alignmentQueue.front();
        const V snapshot = state.politics.pending.at(alignmentKey(nation));
        const bool ccp = snapshot.require("ccp_neighbor").asBool();
        const bool dadao = snapshot.require("dadao_neighbor").asBool();
        const V& direct = snapshot.require("recipient");
        if (direct.isNull() && (ccp || dadao)) {
            // The responsible active player supplies an explicit chance result;
            // uncontrolled warlords themselves have no player account.
            requestPoliticalRoll(state, state.currentNation(), "warlord_alignment", 12, snapshot);
            return true;
        }
        state.politics.alignmentQueue.erase(state.politics.alignmentQueue.begin());
        state.politics.pending.erase(alignmentKey(nation));
        alignSurvivingNation(state, nation, direct.isNull() ? Id("kmt") : direct.asString(), direct.isNull());
        refreshPoliticalState(state);
        if (state.chance || !state.decisions.empty()) return true;
    }
    const bool truceEligible = state.politics.pending.at(resolutionKey).require("truce_eligible").asBool();
    // Consume the marker before refresh: an evolution may create other decisions.
    state.politics.pending.erase(resolutionKey);
    for(auto it=state.politics.pending.begin();it!=state.politics.pending.end();)
        if(it->first.rfind("warlord_defense_player:",0)==0)it=state.politics.pending.erase(it);else ++it;
    considerDadaoAlignment(state);
    refreshPoliticalState(state);
    if (truceEligible && maySignTruce(state)) {
        state.politics.truceOfferPending = true;
        queuePoliticalDecision(state, "ccp", "truce_offer_decision", {
            politicalAction(state, "ccp", "truce_offer"),
            politicalAction(state, "ccp", "truce_decline_offer")});
    }
    return true;
}

bool applyWarlordChance(State& state, const ChanceRequest& request, const ChanceOutcome& outcome) {
    if (request.purpose != "warlord_alignment") return false;
    const auto results = effectiveResults(request, outcome);
    const V parameters = pendingPolitical(state, request.continuation);
    const Id nation = parameters.require("warlord").asString();
    if (results.size() != 1 || state.politics.alignmentQueue.empty()
            || state.politics.alignmentQueue.front() != nation)
        throw std::runtime_error("Unexpected whole-warlord alignment continuation");
    const bool ccp = parameters.require("ccp_neighbor").asBool();
    const bool dadao = parameters.require("dadao_neighbor").asBool();
    const int roll = results.front();
    Id recipient = "kmt";
    if (ccp && dadao) recipient = roll <= 5 ? "ccp" : roll <= 10 ? "kmt" : "dadao";
    else if (roll <= 6 && (ccp || dadao)) recipient = ccp ? "ccp" : "dadao";
    state.politics.alignmentQueue.erase(state.politics.alignmentQueue.begin());
    state.politics.pending.erase(alignmentKey(nation));
    erasePoliticalContinuation(state, request.continuation);
    alignSurvivingNation(state, nation, recipient, true);
    refreshPoliticalState(state);
    continueCombatPoliticalResolution(state);
    return true;
}

void terminateChineseTruce(State& state, const Id& breaker, bool evolution) {
    if (!state.politics.chineseTruce) return;
    if (breaker != "ccp" && breaker != "kmt") throw std::runtime_error("Only a Chinese faction can terminate its truce");
    if (!evolution && (state.clock.phase != Phase::Combat || state.currentNation() != breaker))
        throw std::runtime_error("Voluntary Chinese Truce termination requires the faction's Combat Phase");
    state.politics.chineseTruce = false;
    // RB 6.2 bars re-signing after either voluntary or automatic termination.
    state.politics.trucePermanentlyEnded = true;
    state.politics.truceOfferPending = false;
    queueSharedBattles(state, breaker);
    // The two factions stop being allies now, not at the next political refresh.
    refreshAlliances(state);
}

} // namespace game::campaign
