#include "game/politics.hpp"
#include "game/catalog.hpp"

#include <algorithm>
#include <stdexcept>

// v4.3 source contract: RB glossary p6; recruitment p82; CCP pp103-104;
// Dadao p105; CCP NRS p3; Japan NRS p4; adopted spending ruling RCL-002.
// These services do not grant movement, income or purchase permissions.
namespace game::campaign {
namespace {
using V = json::Value;
using O = V::Object;
using A = V::Array;

// Builds the message only on failure; most messages are literals.
template <class Message> void require(bool condition, const Message &message) {
    if (!condition) throw std::runtime_error(message);
}

V number(int value) { return V(static_cast<double>(value)); }

bool flagged(const std::map<Id, int>& flags, const Id& key) {
    const auto found = flags.find(key);
    return found != flags.end() && found->second != 0;
}

bool quietPlacement(const State& state) {
    return !state.terminal && state.clock.phase == Phase::PlaceUnits
        && !state.clock.incomeCollected && !state.chance
        && state.decisions.empty() && state.battles.empty() && state.battleOrder.empty();
}

bool controlsZone(const State& state, NationId actor, ZoneId zone) {
    const auto& owner = state.territories.at(zone).possessor;
    return owner && (*owner == actor || (actor == knownNations(state).japan && controlledBy(state, *owner, actor)));
}

// RB p6 requires a unit since the beginning of this Player Turn, not a unit
// newly moved/placed into the zone. The snapshot keeps stable identity even if
// its owner changes. A departed-and-returned unit cannot establish this fact.
bool influencingGarrison(const State& state, ZoneId zone) {
    for (const auto& [id, beginning] : state.turnStart.units) {
        if (beginning.second != zone) continue;
        const auto current = state.units.find(id);
        if (current == state.units.end() || current->second.zone != zone) continue;
        const auto& unit = current->second;
        const bool resetForActiveTurn = unit.owner == state.currentNation()
            || controlledBy(state, unit.owner, state.currentNation())
            || (unit.owner == knownNations(state).dadao && state.currentNation() == knownNations(state).japan
                && flagged(state.nations.at(nationNumber(state, "dadao")).gameFlags, "direct_axis_control_after_japan_surrender"));
        // Other nations' units may retain routes and placement flags from their
        // earlier Player Turn. Those stale flags cannot invalidate this snapshot.
        if (!resetForActiveTurn || unit.route.empty()) return true;
    }
    return false;
}

struct InfluenceTarget {
    NationId warlord;
    int threshold {0};
    bool eligible {false};
};

InfluenceTarget influenceTarget(const State& state, NationId actor, NationId target) {
    InfluenceTarget result {target};
    const auto found = state.nations.find(target);
    if (found == state.nations.end() || !isWarlord(nationName(state, target))) return result;
    const auto& nation = found->second;
    if (nation.controllerNation || nation.player || nation.alliance
            || flagged(nation.gameFlags, "incorporated")) return result;
    const auto remaining = possessedLand(state, target);
    if (remaining.empty()) return result;
    std::set<ZoneId> adjacent;
    for (const auto& [zone, territory] : state.territories) {
        if (!controlsZone(state, actor, zone)) continue;
        for (const auto& other : remaining) {
            if (!passableLandBorder(state, zone, other)) continue;
            adjacent.insert(zone);
            if (influencingGarrison(state, zone)) result.eligible = true;
            break;
        }
    }
    // Count a qualifying owned/controlled zone once even when it borders two
    // parts of the same warlord; a unit is the eligibility gate, not a bonus.
    result.threshold = static_cast<int>(adjacent.size());
    return result;
}

bool canInfluence(const State& state, NationId actor) {
    const auto& nation = state.nations.at(actor);
    return (actor == knownNations(state).japan || (actor == knownNations(state).ccp && nation.powerStatus == "minor"))
        && !state.politics.surrendered.contains(actor)
        && !flagged(nation.turnFlags, "influence_attempted")
        && nation.treasury.has_value();
}

bool offshore(const State& state, ZoneId zone) {
    const auto* politics = state.definition->rules.find("politics");
    const auto* zones = politics ? politics->find("offshore_land_zone_ids") : nullptr;
    require(zones != nullptr, "Recruitment requires reviewed offshore classification");
    const auto& name = zoneName(state, zone);
    for (const auto& id : zones->asArray()) if (id.asString() == name) return true;
    return false;
}

bool controlledRecruitment(const State& state, NationId minor) {
    const auto& nation = state.nations.at(minor);
    if (nation.powerStatus != "minor" || minor == knownNations(state).ccp || minor == knownNations(state).kmt
            || flagged(nation.gameFlags, "incorporated")
            || state.politics.surrendered.contains(minor)) return false;
    if (minor == knownNations(state).dadao && state.currentNation() == knownNations(state).japan && nation.player == "axis"
            && state.politics.surrendered.contains(knownNations(state).japan)
            && flagged(nation.gameFlags, "direct_axis_control_after_japan_surrender")) return true;
    if (minor == knownNations(state).mongolia && state.currentNation() == knownNations(state).mongolia)
        return nation.player.has_value();  // Approved direct Comintern control.
    return minor != state.currentNation() && controlledBy(state, minor, state.currentNation());
}

bool recruitmentAvailable(const State& state, NationId minor) {
    const auto& nation = state.nations.at(minor);
    if (flagged(nation.turnFlags, "recruitment_attempted")) return false;
    if (minor == knownNations(state).ccp) return state.currentNation() == minor && nation.powerStatus == "minor";
    return controlledRecruitment(state, minor);
}

int recruitmentThreshold(const State& state, NationId minor) {
    int count = 0;
    for (const auto& zone : possessedLand(state, minor))
        if (minor == knownNations(state).ccp || !offshore(state, zone)) ++count;
    return count;
}

std::vector<ZoneId> recruitmentZones(const State& state, NationId minor) {
    std::vector<ZoneId> zones;
    for (const auto& zone : possessedLand(state, minor)) {
        const auto beginning = state.turnStart.possessions.find(zone);
        if (beginning == state.turnStart.possessions.end() || beginning->second != minor) continue;
        const auto& flags = state.territories.at(zone).flags;
        const auto changed = flags.find("last_possession_change_turn");
        if (changed != flags.end() && changed->second >= 0
                && static_cast<std::uint64_t>(changed->second) == state.clock.playerTurnSerial) continue;
        if (minor == knownNations(state).ccp && !chineseHomeCountry(state, zone)) continue;
        zones.push_back(zone);
    }
    return zones;
}

bool unfinishedShip(const State& state, const BuildProject& project, NationId minor) {
    if (project.owner != minor || project.remainingPayments.empty() || project.queuePosition <= 1
            || !state.definition->catalog) return false;
    const auto& units = state.definition->catalog->units();
    return units.contains(project.type) && units.at(project.type).classes.contains("naval");
}

std::vector<Action> recruitmentChoices(const State& state, NationId minor) {
    std::vector<Action> choices;
    const auto zones = recruitmentZones(state, minor);
    for (const auto& zone : zones) choices.push_back(politicalAction(state, minor,
        "recruitment_place_infantry", V(O{{"beneficiary", V(nationName(state, minor))}, {"zone", V(zoneName(state, zone))}})));
    // The two militia may be split. These are recruitment pieces, so purchased
    // militia's per-zone placement quota does not consume or limit them (RB79).
    for (std::size_t first = 0; first < zones.size(); ++first)
        for (std::size_t second = first; second < zones.size(); ++second)
            choices.push_back(politicalAction(state, minor, "recruitment_place_militia",
                V(O{{"beneficiary", V(nationName(state, minor))}, {"zones", V(A{V(zoneName(state, zones[first])), V(zoneName(state, zones[second]))})}})));
    if (minor == knownNations(state).ccp) return choices;
    for (const auto& [id, project] : state.construction)
        if (unfinishedShip(state, project, minor)) choices.push_back(politicalAction(state, minor,
            "recruitment_advance_ship", V(O{{"beneficiary", V(nationName(state, minor))}, {"project", V(id)}})));
    for (const auto& [id, facility] : state.facilities)
        if (facility.damage > 0 && state.territories.at(facility.zone).possessor == minor)
            choices.push_back(politicalAction(state, minor, "recruitment_repair_facility",
                V(O{{"beneficiary", V(nationName(state, minor))}, {"facility", V(id)}})));
    return choices;
}

bool sameAction(const Action& first, const Action& second) {
    return canonicalJson(actionJson(first)) == canonicalJson(actionJson(second));
}

bool listed(const std::vector<Action>& actions, const Action& action) {
    return std::any_of(actions.begin(), actions.end(), [&](const auto& candidate) {
        return sameAction(candidate, action);
    });
}

void applyRecruitmentChoice(State& state, const Action& action) {
    require(!state.decisions.empty(), "No pending recruitment choice");
    const auto decision = state.decisions.back();
    require(decision.kind == "recruitment_choice" && listed(decision.options, action),
            "Action does not match a pending recruitment option");
    const auto continuation = pendingPolitical(state, decision.continuation);
    const auto minorName = continuation.require("beneficiary").asString();
    const auto minor = nationNumber(state, minorName);
    require(action.parameters.require("beneficiary").asString() == minorName,
            "Recruitment beneficiary changed");
    const auto eligible = recruitmentChoices(state, minor);
    require(std::any_of(eligible.begin(), eligible.end(), [&](const auto& option) {
        return option.kind == action.kind && option.nation == action.nation && option.player == action.player
            && canonicalJson(option.parameters) == canonicalJson(action.parameters);
    }), "Recruitment choice is no longer eligible");
    state.decisions.pop_back();
    erasePoliticalContinuation(state, decision.continuation);
    if (action.kind == "recruitment_place_infantry") {
        addPoliticalUnit(state, minor, "infantry", zoneNumber(state, action.parameters.require("zone").asString()));
    } else if (action.kind == "recruitment_place_militia") {
        const auto& zones = action.parameters.require("zones").asArray();
        require(zones.size() == 2, "Recruitment requires exactly two militia");
        for (const auto& zone : zones) addPoliticalUnit(state, minor, "militia", zoneNumber(state, zone.asString()));
    } else if (action.kind == "recruitment_advance_ship") {
        auto& project = state.construction.at(action.parameters.require("project").asString());
        require(unfinishedShip(state, project, minor), "Recruitment ship no longer eligible");
        project.remainingPayments.erase(project.remainingPayments.begin());
        --project.queuePosition;
        // Free recruitment work is not an IPP payment. A finished ship waits
        // for the economy module's placement rather than spawning at an invented location.
        if (project.remainingPayments.empty()) project.flags["completed"] = 1;
    } else if (action.kind == "recruitment_repair_facility") {
        const auto id = action.parameters.require("facility").asString();
        auto& facility = state.facilities.at(id);
        require(facility.damage > 0 && state.territories.at(facility.zone).possessor == minor,
                "Recruitment facility no longer eligible");
        facility.damage = 0;
        for (auto job = state.repairs.begin(); job != state.repairs.end();)
            if (job->second.target == id) job = state.repairs.erase(job); else ++job;
    } else throw std::runtime_error("Unknown recruitment choice");
    refreshPoliticalState(state);
}
} // namespace

std::vector<Action> influenceActions(const State& state) {
    std::vector<Action> actions;
    if (!quietPlacement(state)) return actions;
    const auto actor = state.currentNation();
    if (canInfluence(state, actor)) for (const auto& [target, nation] : state.nations) {
        const auto candidate = influenceTarget(state, actor, target);
        if (!candidate.eligible || candidate.threshold == 0) continue;
        const int cap = std::min(candidate.threshold, *state.nations.at(actor).treasury);
        for (int spend = 0; spend <= cap; ++spend)
            actions.push_back(politicalAction(state, actor, "influence_roll",
                V(O{{"target", V(nationName(state, target))}, {"spend", number(spend)}})));
    }
    for (const auto& [minor, nation] : state.nations)
        if (recruitmentAvailable(state, minor) && recruitmentThreshold(state, minor) > 0
                && !recruitmentChoices(state, minor).empty())
            actions.push_back(politicalAction(state, actor, "recruitment_roll",
                V(O{{"beneficiary", V(nationName(state, minor))}})));
    return actions;
}

bool applyInfluenceAction(State& state, const Action& action) {
    if (action.kind.rfind("influence_", 0) != 0 && action.kind.rfind("recruitment_", 0) != 0) return false;
    if (action.kind != "influence_roll" && action.kind != "recruitment_roll") {
        applyRecruitmentChoice(state, action);
        return true;
    }
    require(listed(influenceActions(state), action), "Illegal influence or recruitment action");
    if (action.kind == "influence_roll") {
        const auto targetName = action.parameters.require("target").asString();
        const int spend = action.parameters.require("spend").asInt();
        const auto actorNation = nationNumber(state, action.nation);
        const auto candidate = influenceTarget(state, actorNation, nationNumber(state, targetName));
        auto& actor = state.nations.at(actorNation);
        *actor.treasury -= spend;
        actor.turnFlags["influence_attempted"] = 1;
        requestPoliticalRoll(state, actorNation, "influence_roll", 12,
            V(O{{"actor", V(action.nation)}, {"target", V(targetName)},
                {"threshold", number(candidate.threshold)}, {"spend", number(spend)}}));
    } else {
        const auto minorName = action.parameters.require("beneficiary").asString();
        const auto minor = nationNumber(state, minorName);
        state.nations.at(minor).turnFlags["recruitment_attempted"] = 1;
        requestPoliticalRoll(state, minor, "recruitment_roll", 12,
            V(O{{"beneficiary", V(minorName)}, {"threshold", number(recruitmentThreshold(state, minor))}}));
    }
    return true;
}

bool applyInfluenceChance(State& state, const ChanceRequest& request, const ChanceOutcome& outcome) {
    if (request.purpose != "influence_roll" && request.purpose != "recruitment_roll") return false;
    const auto results = effectiveResults(request, outcome);
    require(request.dice.size() == 1 && request.dice.front().sides == 12
            && request.dice.front().modifier == 0 && request.dice.front().maxRerolls == 0
            && results.size() == 1, "Political roll requires one unmodified D12");
    const int raw = results.front();
    const auto parameters = pendingPolitical(state, request.continuation);
    const int threshold = parameters.require("threshold").asInt();
    require(threshold > 0, "Political roll has no eligible possessions");
    erasePoliticalContinuation(state, request.continuation);
    if (request.purpose == "influence_roll") {
        const auto actor = parameters.require("actor").asString();
        const auto target = nationNumber(state, parameters.require("target").asString());
        const int spend = parameters.require("spend").asInt();
        require(actor == request.nation && spend >= 0 && spend <= threshold,
                "Influence continuation differs from paid attempt");
        if (raw == 12) {
            // RCL-002/NRS explicitly say this result always aligns with KMT.
            // RB4.9's surrendered-KMT exception is for attacks; RB5.7 bars
            // liberation, not this specific influence result. Restore only the
            // recipient's ability to receive the actual surviving warlord.
            state.politics.surrendered.erase(nationNumber(state, "kmt"));
            state.nations.at(nationNumber(state, "kmt")).gameFlags["surrendered"] = 0;
            incorporateNation(state, target, nationNumber(state, "kmt"));
        }
        else if (raw - spend <= threshold) {
            if (actor == "japan") {
                ensureDadao(state);
                const auto& dadao = state.nations.at(nationNumber(state, "dadao"));
                if (flagged(dadao.gameFlags, "incorporated")) {
                    require(dadao.controllerNation.has_value(), "Incorporated Dadao has no recipient nation");
                    incorporateNation(state, target, *dadao.controllerNation);
                } else incorporateNation(state, target, nationNumber(state, "dadao"));
            } else incorporateNation(state, target, nationNumber(state, actor));
        }
        refreshPoliticalState(state);
    } else {
        const auto minorName = parameters.require("beneficiary").asString();
        require(minorName == request.nation, "Recruitment beneficiary differs from roll");
        if (raw <= threshold) {
            const auto minor = nationNumber(state, minorName);
            auto choices = recruitmentChoices(state, minor);
            if (!choices.empty()) queuePoliticalDecision(state, minor, "recruitment_choice",
                std::move(choices), V(O{{"beneficiary", V(minorName)}}));
        }
    }
    return true;
}

} // namespace game::campaign
