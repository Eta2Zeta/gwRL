#include "game/naval.hpp"
#include "game/air.hpp"
#include "game/catalog.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <functional>
#include <stdexcept>

namespace game::campaign {
namespace {
using V = json::Value;
using O = V::Object;
using A = V::Array;
void require(bool ok, const std::string& message) { if (!ok) throw std::runtime_error(message); }
V num(int n) { return V(static_cast<double>(n)); }
bool marked(const std::map<Id, int>& flags, const Id& key) {
    auto it = flags.find(key); return it != flags.end() && it->second != 0;
}
bool has(const State& s, const UnitState& u, const Id& c) {
    return s.definition->catalog->unit(u.type).classes.contains(c);
}
bool hostile(const State& s, const Id& a, const Id& b) {
    return a != b && s.nations.at(a).atWarWith.contains(b);
}
bool sub(const State& s, const UnitState& u) { return has(s, u, "submarine"); }
bool plane(const State& s, const UnitState& u) { return has(s, u, "aircraft"); }
bool fighter(const State& s, const UnitState& u) { return has(s, u, "fighter"); }
bool transport(const State& s, const UnitState& u) { return has(s, u, "naval_transport"); }
bool tech(const State& s, const Id& owner, const Id& t) {
    const auto it = s.nations.at(owner).technologyStages.find(t);
    return it != s.nations.at(owner).technologyStages.end() && it->second == 4;
}
O object(const BattleState& b, const Id& key) { auto p = b.data.find(key); return p ? p->asObject() : O{}; }
A array(const BattleState& b, const Id& key) { auto p = b.data.find(key); return p ? p->asArray() : A{}; }
Id string(const BattleState& b, const Id& key, const Id& fallback = "") {
    auto p = b.data.find(key); return p ? p->asString() : fallback;
}
int integer(const BattleState& b, const Id& key, int fallback = 0) {
    auto p = b.data.find(key); return p ? p->asInt() : fallback;
}
bool boolean(const BattleState& b, const Id& key) {
    auto p = b.data.find(key); return p && p->asBool();
}
void put(BattleState& b, const Id& key, V value) {
    auto data = b.data.asObject(); data[key] = std::move(value); b.data = V(std::move(data));
}
A ids(const std::vector<Id>& list) { A out; for (const auto& id : list) out.emplace_back(id); return out; }
std::vector<Id> readIds(const V& v) {
    std::vector<Id> out; for (const auto& item : v.asArray()) out.push_back(item.asString()); return out;
}
bool listed(const A& list, const Id& id) {
    return std::any_of(list.begin(), list.end(), [&](const V& v) { return v.asString() == id; });
}
Action action(const State& s, const Id& nation, const Id& kind, O parameters = {}) {
    Action a; a.kind = kind; a.nation = nation; a.player = politicalPlayer(s, nation);
    a.parameters = V(std::move(parameters)); a.id = kind + ":" + contentDigest(canonicalJson(a.parameters)); return a;
}
void decision(State& s, BattleState& b, const Id& nation, const Id& kind, std::vector<Action> options) {
    require(!options.empty(), "Empty naval decision");
    Decision d; d.id = b.id + "_decision_" + std::to_string(++s.flags["naval_decision_sequence"]);
    d.nation = nation; d.kind = kind; d.reaction = nation != s.currentNation(); d.continuation = b.id;
    for (auto& a : options) a.decision = d.id;
    d.options = std::move(options); s.decisions.push_back(std::move(d));
}
void release(State& s, const Action& a) {
    require(a.decision && !s.decisions.empty() && s.decisions.back().id == *a.decision,
            "Missing naval decision");
    s.decisions.pop_back();
}
bool pendingDead(const BattleState& b, const Id& id) { return listed(array(b, "naval_pending_dead"), id); }
bool operational(const State& s, const BattleState& b, const Id& id, bool includeDead = false) {
    if (!s.units.contains(id) || (!includeDead && pendingDead(b, id))) return false;
    const auto& u = s.units.at(id);
    const bool portDefender = string(b, "context") == "port_attack" && b.data.find("facility") &&
        s.facilities.contains(string(b, "facility")) &&
        u.zone == s.facilities.at(string(b, "facility")).zone &&
        std::find(b.defenders.begin(), b.defenders.end(), id) != b.defenders.end();
    return (u.zone == b.zone || portDefender) && !object(b, "grounded").contains(id) &&
           !object(b, "naval_excluded").contains(id) &&
           !marked(u.turnFlags, "submerged") && !marked(u.turnFlags, "naval_retreated");
}
std::vector<Id> living(const State& s, const BattleState& b, bool attacker, bool includeDead = false) {
    std::vector<Id> out;
    for (const auto& id : attacker ? b.attackers : b.defenders)
        if (operational(s, b, id, includeDead)) out.push_back(id);
    return out;
}
bool oneRound(const BattleState& b) {
    const auto context = string(b, "context", "standard");
    return context == "movement_submarines" || context == "movement_map" ||
           context == "port_attack" || boolean(b, "one_round");
}
bool immediateBattle(const BattleState& b) {
    const auto context = string(b, "context");
    return marked(b.flags, "immediate") || context == "movement_submarines" || context == "movement_map";
}
bool onMap(const State& s, const Id& id) {
    if (!s.units.contains(id)) return false;
    const auto& u = s.units.at(id);
    return marked(u.gameFlags, "on_map") ||
           std::any_of(u.commitments.begin(), u.commitments.end(), [](const Id& commitment) {
               return commitment.rfind("air_defending_carrier:", 0) == 0;
           }) ||
           (u.carriedBy && s.units.contains(*u.carriedBy) && has(s, s.units.at(*u.carriedBy), "carrier"));
}
std::optional<Id> originalCarrier(const UnitState& u) {
    if (u.carriedBy) return u.carriedBy;
    const Id prefix = "air_defending_carrier:";
    for (const auto& commitment : u.commitments)
        if (commitment.rfind(prefix, 0) == 0) return commitment.substr(prefix.size());
    return std::nullopt;
}
void advance(State&, BattleState&);
void chooseHit(State&, BattleState&);
void queueCarrierLandings(State&, BattleState&);
void removeUnit(State& s, BattleState& b, const Id& id) {
    if (!s.units.contains(id)) return;
    const bool carrier = has(s, s.units.at(id), "carrier");
    if (carrier) {
        // RB10.7: defending aircraft get an immediate one-movement landing.
        // Detach before generic linked-cargo removal; ordinary transport cargo
        // remains linked and is destroyed with its ship.
        A rescue = array(b, "naval_carrier_landing_queue");
        std::vector<Id> aircraft;
        for (const auto& [uid, u] : s.units)
            if (plane(s, u) && originalCarrier(u) == id &&
                std::find(b.defenders.begin(), b.defenders.end(), uid) != b.defenders.end()) aircraft.push_back(uid);
        for (const auto& uid : aircraft) {
            auto& u = s.units.at(uid);
            if (u.carriedBy) {
                auto& cargo = s.units.at(*u.carriedBy).cargo;
                cargo.erase(std::remove(cargo.begin(), cargo.end(), uid), cargo.end());
                u.carriedBy.reset();
            }
            u.commitments.erase("air_defending_carrier:" + id);
            u.movementRemaining = 1;
            if (!listed(rescue, uid)) rescue.emplace_back(uid);
            auto excluded = object(b, "naval_excluded"); excluded[uid] = V(true); put(b, "naval_excluded", V(excluded));
        }
        put(b, "naval_carrier_landing_queue", V(rescue));
    }
    removePoliticalUnits(s, {id});
}
void flushDead(State& s, BattleState& b) {
    const auto dead = array(b, "naval_pending_dead"); put(b, "naval_pending_dead", V(A{}));
    for (const auto& id : dead) removeUnit(s, b, id.asString());
}
void takeHit(State& s, BattleState& b, const Id& id, bool immediate) {
    auto& u = s.units.at(id);
    const auto maxHits = s.definition->catalog->unit(u.type).maxHits;
    if (u.damage + 1 < maxHits) {
        ++u.damage;
        // Damaged status costs one movement, regardless of the damage count.
        if (u.damage == 1 && u.movementRemaining) u.movementRemaining = std::max(0, *u.movementRemaining - 1);
        return;
    }
    if (immediate) removeUnit(s, b, id);
    else { auto dead = array(b, "naval_pending_dead"); dead.emplace_back(id); put(b, "naval_pending_dead", V(dead)); }
}
void roll(State& s, BattleState& b, const Id& purpose, int count) {
    require(!s.chance && count > 0, "Invalid naval roll");
    ChanceRequest c; c.id = b.id + "_roll_" + std::to_string(++s.flags["naval_roll_sequence"]);
    c.purpose = purpose; c.nation = b.attacker; c.continuation = b.id;
    for (int i = 0; i < count; ++i) c.dice.push_back(DieSpec{});
    s.chance = std::move(c);
}
std::vector<Id> targetsFor(const State& s, const BattleState& b, const Id& firing, bool victimAttacker) {
    auto candidates = living(s, b, victimAttacker);
    if (!s.units.contains(firing)) return {};
    const auto& shooter = s.units.at(firing);
    const bool port = string(b, "context") == "port_attack";
    const bool subsInitiated = boolean(b, "submarines_initiated");
    const auto protectedSubs = object(b, "naval_protected_submarines");
    const auto pairs = object(b, "naval_destroyer_pairs");
    candidates.erase(std::remove_if(candidates.begin(), candidates.end(), [&](const Id& id) {
        const auto& target = s.units.at(id);
        if (sub(s, shooter) && plane(s, target)) return true;
        if (shooter.type == "seaplane" && !sub(s, target) && !transport(s, target)) return true;
        if (!sub(s, target) || victimAttacker || port || subsInitiated || !protectedSubs.contains(id)) return false;
        if (plane(s, shooter) && onMap(s, firing)) return false;
        if (shooter.type == "destroyer" && pairs.contains(firing) && target.type != "advanced_submarine") return false;
        return true;
    }), candidates.end());
    return candidates;
}
void shoot(State& s, BattleState& b, const Id& stage) {
    A shots;
    const bool first = stage == "naval_first_strike", air = stage == "naval_air_superiority";
    const int round = integer(b, "round", 1);
    for (bool attacking : {true, false}) {
        if (!first && !air && attacking != (stage == "naval_attacker_fire")) continue;
        const auto participants = living(s, b, attacking, !attacking && stage == "naval_defender_fire");
        const auto opponents = living(s, b, !attacking);
        const bool enemyDestroyer = std::any_of(opponents.begin(), opponents.end(), [&](const Id& id) {
            return s.units.at(id).type == "destroyer";
        });
        for (const auto& id : participants) {
            const auto& u = s.units.at(id);
            bool firstStrike = (sub(s, u) && !enemyDestroyer) ||
                (attacking && plane(s, u) && marked(b.flags, "japanese_surprise_attack"));
            if (first && (!firstStrike || round != 1)) continue;
            if (air && (!fighter(s, u) || firstStrike || round != 1)) continue;
            if (!first && !air && round == 1 && (firstStrike || fighter(s, u))) continue;
            auto stats = s.definition->catalog->stats(u.type, u.damage, catalogContext(s, u.owner, u.zone));
            auto threshold = attacking ? stats.attack : stats.defense;
            int dice = attacking ? stats.attackDice : stats.defenseDice;
            bool aswTransport = false;
            if (!attacking && u.type == "naval_transport" && tech(s, u.owner, "anti_submarine_warfare") &&
                std::any_of(opponents.begin(), opponents.end(), [&](const Id& enemy) { return sub(s, s.units.at(enemy)); })) {
                threshold = 1; dice = 1; aswTransport = true;
            }
            if (!threshold || dice == 0) continue;
            if (!attacking && string(b, "context") == "port_attack" && has(s, u, "naval")) continue;
            if (!attacking && round == 1 && marked(b.flags, "japanese_surprise_attack")) threshold = std::max(1, *threshold - 1);
            auto eligible = targetsFor(s, b, id, !attacking);
            if (aswTransport) eligible.erase(std::remove_if(eligible.begin(), eligible.end(), [&](const Id& enemy) { return !sub(s, s.units.at(enemy)); }), eligible.end());
            if (eligible.empty()) continue;
            int target = 0; std::set<Id> targetClasses;
            for (const auto& mode : s.definition->catalog->modes(u.type, catalogContext(s, u.owner, u.zone), u.damage))
                if (mode.id == "target_selection") {
                    target = mode.threshold.value_or(0);
                    for (const auto& c : mode.parameters.require("target_classes").asArray()) targetClasses.insert(c.asString());
                }
            if (sub(s, u)) { target = 1; targetClasses = {"surface_ship"}; }
            if (!attacking && u.type == "battlecruiser" && marked(u.gameFlags, "raider")) {
                target = *threshold; targetClasses = {"naval"};
            }
            A classes; for (const auto& c : targetClasses) classes.emplace_back(c);
            for (int n = 0; n < dice; ++n)
                shots.emplace_back(O{{"unit", V(id)}, {"nation", V(u.owner)}, {"victim_attacker", V(!attacking)},
                                     {"threshold", num(*threshold)}, {"target", num(target)},
                                     {"target_classes", V(classes)}, {"eligible", V(ids(eligible))},
                                     {"air_priority", V(air)},
                                     {"asw_sub_bonus", num(attacking && u.type == "seaplane" && onMap(s, id) && tech(s, u.owner, "anti_submarine_warfare") ? 2 : 0)}});
        }
    }
    const Id after = first ? "naval_air_superiority" : air ? "naval_attacker_fire" :
                     stage == "naval_attacker_fire" ? "naval_defender_fire" : "naval_round_end";
    put(b, "naval_round_shots", num(integer(b, "naval_round_shots") + static_cast<int>(shots.size())));
    put(b, "naval_after_roll", V(after)); put(b, "naval_shots", V(shots));
    if (stage == "naval_attacker_fire") put(b, "naval_attacker_shots", num(static_cast<int>(shots.size())));
    put(b, "naval_immediate_hits", V(first));
    if (shots.empty()) { b.stage = after; advance(s, b); }
    else roll(s, b, "naval_combat_roll", static_cast<int>(shots.size()));
}
std::vector<Id> eligibleHit(const State& s, const BattleState& b, const V& hit) {
    auto units = living(s, b, hit.require("victim_attacker").asBool());
    const auto eligible = readIds(hit.require("eligible"));
    units.erase(std::remove_if(units.begin(), units.end(), [&](const Id& id) {
        return std::find(eligible.begin(), eligible.end(), id) == eligible.end();
    }), units.end());
    if (hit.require("air_priority").asBool()) {
        const bool any = std::any_of(units.begin(), units.end(), [&](const Id& id) { return plane(s, s.units.at(id)); });
        if (any) units.erase(std::remove_if(units.begin(), units.end(), [&](const Id& id) { return !plane(s, s.units.at(id)); }), units.end());
    }
    std::vector<Id> targeted;
    if (hit.require("targeted").asBool())
        for (const auto& id : units)
            for (const auto& c : hit.require("target_classes").asArray())
                if (has(s, s.units.at(id), c.asString())) { targeted.push_back(id); break; }
    if (!targeted.empty()) return targeted;
    const bool combatants = std::any_of(units.begin(), units.end(), [&](const Id& id) { return !transport(s, s.units.at(id)); });
    if (combatants) units.erase(std::remove_if(units.begin(), units.end(), [&](const Id& id) { return transport(s, s.units.at(id)); }), units.end());
    return units;
}
bool isTargeted(const State& s, const V& hit, const std::vector<Id>& eligible) {
    if (!hit.require("targeted").asBool()) return false;
    for (const auto& id : eligible)
        for (const auto& c : hit.require("target_classes").asArray())
            if (has(s, s.units.at(id), c.asString())) return true;
    return false;
}
void chooseHit(State& s, BattleState& b) {
    const auto hits = array(b, "naval_hits");
    int index = integer(b, "naval_hit_index");
    while (index < static_cast<int>(hits.size())) {
        const auto& hit = hits[static_cast<std::size_t>(index)];
        auto candidates = eligibleHit(s, b, hit);
        if (candidates.empty()) { put(b, "naval_hit_index", num(++index)); continue; }
        const bool targeted = isTargeted(s, hit, candidates);
        Id chooser = targeted ? hit.require("nation").asString() :
                     hit.require("victim_attacker").asBool() ? b.attacker : b.defender;
        const auto proposal = string(b, "naval_casualty_proposal");
        if (!targeted && !hit.require("victim_attacker").asBool() && !proposal.empty()) {
            const auto consents = object(b, "naval_casualty_consents");
            std::set<Id> players;
            for (const auto& id : candidates) players.insert(politicalPlayer(s, s.units.at(id).owner));
            for (const auto& id : candidates) {
                const auto owner = s.units.at(id).owner;
                const auto player = politicalPlayer(s, owner);
                if (player != politicalPlayer(s, b.defender) && !consents.contains(player)) {
                    decision(s, b, owner, "naval_casualty_consent", {
                        action(s, owner, "naval_casualty_accept", {{"battle", V(b.id)}}),
                        action(s, owner, "naval_casualty_dispute", {{"battle", V(b.id)}})}); return;
                }
            }
            if (std::find(candidates.begin(), candidates.end(), proposal) != candidates.end())
                takeHit(s, b, proposal, boolean(b, "naval_immediate_hits"));
            put(b, "naval_casualty_proposal", V(std::string{})); put(b, "naval_casualty_consents", V(O{}));
            put(b, "naval_hit_index", num(++index)); continue;
        }
        std::vector<Action> options;
        for (const auto& id : candidates)
            options.push_back(action(s, chooser, "naval_take_casualty", {{"battle", V(b.id)}, {"unit", V(id)}, {"targeted", V(targeted)}}));
        decision(s, b, chooser, "naval_casualty", std::move(options)); return;
    }
    put(b, "naval_hits", V(A{})); put(b, "naval_hit_index", num(0));
    const auto next = string(b, "naval_after_roll");
    if (next != "naval_defender_fire") flushDead(s, b);
    b.stage = next; advance(s, b);
}
void queueCarrierLandings(State& s, BattleState& b) {
    auto queue = array(b, "naval_carrier_landing_queue");
    while (!queue.empty()) {
        const auto id = queue.front().asString();
        if (!s.units.contains(id)) { queue.erase(queue.begin()); put(b, "naval_carrier_landing_queue", V(queue)); continue; }
        auto spots = airLandingSpots(s, id);
        if (spots.empty()) {
            removePoliticalUnits(s, {id}); queue.erase(queue.begin()); put(b, "naval_carrier_landing_queue", V(queue)); continue;
        }
        std::vector<Action> options;
        for (const auto& destination : spots)
            options.push_back(action(s, s.units.at(id).owner, "naval_carrier_land",
                                    {{"battle", V(b.id)}, {"unit", V(id)}, {"destination", V(destination)}}));
        decision(s, b, s.units.at(id).owner, "naval_carrier_landing", std::move(options)); return;
    }
}
void finishBattle(State& s, BattleState& b, const Id& result) {
    put(b, "result", V(result));
    if (result == "attacker_wins") {
        const auto grounded = object(b, "grounded");
        for (const auto& [id, _] : grounded) if (s.units.contains(id)) removePoliticalUnits(s, {id});
    }
    // Aircraft that launched from a surviving defending carrier return to that
    // carrier without receiving their full normal movement as an extra flight.
    for (const auto& id : b.defenders)
        if (s.units.contains(id) && plane(s, s.units.at(id))) {
            auto carrier = originalCarrier(s.units.at(id));
            if (carrier && s.units.contains(*carrier) && !s.units.at(id).carriedBy) {
                if (airLandingAvailable(s, id, *carrier)) attachCargo(s, *carrier, id);
                else { s.units.at(id).movementRemaining = 1; auto q = array(b, "naval_carrier_landing_queue"); q.emplace_back(id); put(b, "naval_carrier_landing_queue", V(q)); }
                s.units.at(id).commitments.erase("air_defending_carrier:" + *carrier);
            }
        }
    b.stage = "naval_aftermath";
    if (!array(b, "naval_carrier_landing_queue").empty()) { queueCarrierLandings(s, b); return; }
    if (!b.data.find("air_landing_done")) finishAirCombat(s, b.id);
    if (s.decisions.empty() && !s.chance && boolean(b, "air_landing_done")) {
        b.flags["finished"] = 1; b.stage = "naval_complete";
        s.flags.erase("immediate_naval_battles");
        if (b.data.find("naval_movement")) { const auto id = b.id; continueNavalMovement(s, id); }
    }
}
bool endIfOver(State& s, BattleState& b) {
    const auto attackers = living(s, b, true), defenders = living(s, b, false);
    if (!attackers.empty() && string(b, "context") == "port_attack" && !marked(b.flags, "port_aa_done")) return false;
    if (attackers.empty() || defenders.empty()) {
        finishBattle(s, b, attackers.empty() ? (defenders.empty() ? "mutual_destruction" : "defender_wins") : "attacker_wins"); return true;
    }
    return false;
}
std::set<Id> retreatOrigins(const State& s, const BattleState& b) {
    std::set<Id> out;
    for (const auto& origin : array(b, "naval_entry_origins")) {
        const auto& from = origin.asString();
        const auto& nodes = s.definition->geography.require("nodes");
        if (!nodes.find(from) || nodes.require(from).require("type").asString() != "sea") continue;
        bool adjacent = false;
        for (const auto& edge : nodes.require(b.zone).require("neighbors").asArray())
            adjacent |= edge.require("neighbor_id").asString() == from;
        if (!adjacent) continue;
        // RB10.3 requires the real adjacent entry sea, not Friendly ownership.
        out.insert(from);
    }
    return out;
}
void assignRetreat(State& s, BattleState& b) {
    const auto origins = retreatOrigins(s, b);
    for (const auto& id : living(s, b, true))
        if (has(s, s.units.at(id), "naval")) {
            std::vector<Action> options;
            for (const auto& destination : origins)
                options.push_back(action(s, b.attacker, "naval_retreat_unit", {{"battle", V(b.id)}, {"unit", V(id)}, {"zone", V(destination)}}));
            require(!options.empty(), "Naval retreat lacks an entry sea zone");
            decision(s, b, b.attacker, "naval_retreat_destination", std::move(options)); return;
        }
    finishBattle(s, b, "retreated");
}
void preparePairs(State& s, BattleState& b) {
    auto pairs = object(b, "naval_destroyer_pairs");
    std::set<Id> used; for (const auto& [ship, aircraft] : pairs) used.insert(aircraft.asString());
    for (bool attacker : {true, false}) {
        const auto enemy = living(s, b, !attacker);
        if (std::none_of(enemy.begin(), enemy.end(), [&](const Id& id) { return sub(s, s.units.at(id)) && s.units.at(id).type != "advanced_submarine"; })) continue;
        auto own = living(s, b, attacker);
        if (!attacker && string(b, "context") == "movement_map")
            for (const auto& [id, u] : s.units)
                if (u.zone == b.zone && u.type == "destroyer" && hostile(s, b.attacker, u.owner) &&
                    std::find(own.begin(), own.end(), id) == own.end() &&
                    std::any_of(own.begin(), own.end(), [&](const Id& aircraft) {
                        return plane(s, s.units.at(aircraft)) && onMap(s, aircraft) &&
                               politicallyFriendly(s, u.owner, s.units.at(aircraft).owner);
                    })) own.push_back(id);
        for (const auto& id : own)
            if (s.units.at(id).type == "destroyer" && !pairs.contains(id) && !object(b, "naval_pairing_done").contains(id)) {
                std::vector<Action> options{action(s, s.units.at(id).owner, "naval_decline_pair", {{"battle", V(b.id)}, {"unit", V(id)}})};
                for (const auto& aircraft : own)
                    if (plane(s, s.units.at(aircraft)) && onMap(s, aircraft) && !used.contains(aircraft))
                        options.push_back(action(s, s.units.at(id).owner, "naval_pair_destroyer", {{"battle", V(b.id)}, {"unit", V(id)}, {"aircraft", V(aircraft)}}));
                if (options.size() > 1) { decision(s, b, s.units.at(id).owner, "naval_destroyer_pairing", std::move(options)); return; }
            }
    }
    b.stage = "naval_submarine_choices"; advance(s, b);
}
void prepareSubmarines(State& s, BattleState& b) {
    const auto attackers = living(s, b, true);
    const bool mapPresent = std::any_of(attackers.begin(), attackers.end(), [&](const Id& id) { return plane(s, s.units.at(id)) && onMap(s, id); });
    if (string(b, "context") != "port_attack" && !boolean(b, "submarines_initiated"))
        for (const auto& id : b.defenders)
            if (operational(s, b, id) && sub(s, s.units.at(id)) && !object(b, "naval_submarine_choices").contains(id)) {
                std::vector<Action> options;
                if (!mapPresent) options.push_back(action(s, s.units.at(id).owner, "naval_sub_decline", {{"battle", V(b.id)}, {"unit", V(id)}}));
                options.push_back(action(s, s.units.at(id).owner, "naval_sub_protected", {{"battle", V(b.id)}, {"unit", V(id)}}));
                options.push_back(action(s, s.units.at(id).owner, "naval_sub_unprotected", {{"battle", V(b.id)}, {"unit", V(id)}}));
                decision(s, b, s.units.at(id).owner, "naval_submarine_participation", std::move(options)); return;
            }
    if (string(b, "context") != "movement_submarines" && string(b, "context") != "movement_map")
        for (const bool attacker : {true, false}) for (const auto& id : living(s, b, attacker))
            s.units.at(id).commitments.insert("naval_combat");
    b.stage = "naval_first_strike"; advance(s, b);
}
void prepareRaiders(State& s, BattleState& b) {
    if (string(b, "context") != "port_attack" && string(b, "context") != "movement_submarines" && string(b, "context") != "movement_map")
        for (const auto& id : b.defenders)
            if (operational(s, b, id) && s.units.at(id).type == "battlecruiser" &&
                marked(s.units.at(id).gameFlags, "raider") && !object(b, "naval_raider_choices").contains(id)) {
                decision(s, b, b.attacker, "naval_engage_raider", {
                    action(s, b.attacker, "naval_ignore_raider", {{"battle", V(b.id)}, {"unit", V(id)}}),
                    action(s, b.attacker, "naval_discover_raider", {{"battle", V(b.id)}, {"unit", V(id)}})}); return;
            }
    b.stage = "naval_scrambling"; advance(s, b);
}
void prepareShipScrambles(State& s, BattleState& b) {
    if (string(b, "context") != "port_attack" && !boolean(b, "no_scramble") &&
        !marked(b.flags, "japanese_surprise_attack") && !b.defenders.empty())
        for (const auto& [id, u] : s.units) {
            if (!has(s, u, "naval") || !hostile(s, b.attacker, u.owner) ||
                !politicallyFriendly(s, b.defender, u.owner) || marked(u.gameFlags, "skeleton_crew") || u.gameFlags.contains("skeleton_crew_until_own_turn") ||
                marked(u.turnFlags, "repairing") || object(b, "naval_scramble_choices").contains(id)) continue;
            Id facility;
            for (const auto& [key, value] : u.gameFlags)
                if (value && key.rfind("in_port:", 0) == 0) facility = key.substr(8);
            if (facility.empty() || !s.facilities.contains(facility)) continue;
            const auto& f = s.facilities.at(facility);
            if (f.damage || (sub(s, u) ? f.type != "submarine_base" :
                f.type != "major_port" && f.type != "major_dockyard" && f.type != "major_shipyard")) continue;
            const auto seas = navalFacilitySeaZones(s, facility);
            if (std::find(seas.begin(), seas.end(), b.zone) == seas.end()) continue;
            const auto owner = s.territories.at(f.zone).possessor;
            if (!owner || (*owner != u.owner && !politicallyFriendly(s, u.owner, *owner)) ||
                marked(f.flags, "placed_this_turn") || (*owner == u.owner && !heldSinceNationTurnStart(s, u.owner, f.zone, false))) continue;
            int spent = marked(f.flags, "naval_scramble_turn") && f.flags.at("naval_scramble_turn") == static_cast<int>(s.clock.playerTurnSerial + 1) ?
                (f.flags.contains("naval_scramble_used") ? f.flags.at("naval_scramble_used") : 0) : 0;
            if (!tech(s, *owner, "radar") && spent >= 3) continue;
            std::vector<Action> options{
                action(s, u.owner, "naval_decline_scramble", {{"battle", V(b.id)}, {"unit", V(id)}}),
                action(s, u.owner, "naval_scramble", {{"battle", V(b.id)}, {"unit", V(id)}, {"facility", V(facility)}})};
            decision(s, b, u.owner, "naval_scramble", std::move(options)); return;
        }
    b.stage = "naval_air_defence";
    if (boolean(b, "no_scramble")) {
        // Movement encounters cannot gain unrelated defenders. Existing aircraft
        // in the explicitly selected force still participate.
        put(b, "air_defence_ready", V(true)); b.stage = "naval_pairing"; advance(s, b);
    } else { beginAirDefence(s, b.id); advance(s, b); }
}
void advance(State& s, BattleState& b) {
    if (s.chance || !s.decisions.empty() || marked(b.flags, "finished")) return;
    if (!array(b, "naval_carrier_landing_queue").empty()) { queueCarrierLandings(s, b); return; }
    if (b.stage == "naval_raider_discovery") { prepareRaiders(s, b); return; }
    if (b.stage == "naval_scrambling") { prepareShipScrambles(s, b); return; }
    if (b.stage == "naval_air_defence") {
        if (!boolean(b, "air_defence_ready")) return;
        b.stage = "naval_pairing";
    }
    if (b.stage == "naval_pairing") { preparePairs(s, b); return; }
    if (b.stage == "naval_submarine_choices") { prepareSubmarines(s, b); return; }
    if (b.stage == "naval_first_strike" || b.stage == "naval_air_superiority" ||
        b.stage == "naval_attacker_fire" || b.stage == "naval_defender_fire") {
        if (b.stage != "naval_defender_fire" && endIfOver(s, b)) return;
        shoot(s, b, b.stage); return;
    }
    if (b.stage == "naval_choose_hits") { chooseHit(s, b); return; }
    if (b.stage == "naval_round_end") {
        flushDead(s, b);
        for (const auto& id : b.defenders)
            if (operational(s, b, id) && sub(s, s.units.at(id)) && string(b, "context") != "port_attack") {
                s.units.at(id).turnFlags["submerged"] = 1;
                auto excluded = object(b, "naval_excluded"); excluded[id] = V(true); put(b, "naval_excluded", V(excluded));
            }
        if (!array(b, "naval_carrier_landing_queue").empty()) { queueCarrierLandings(s, b); return; }
        if (string(b, "context") == "port_attack" && !marked(b.flags, "port_aa_done")) {
            b.flags["port_aa_done"] = 1;
            int aircraft = 0; for (const auto& id : living(s, b, true)) aircraft += plane(s, s.units.at(id));
            if (aircraft && b.data.find("facility") && s.facilities.contains(string(b, "facility")) &&
                !marked(b.flags, "japanese_surprise_attack")) {
                const auto& facility = s.facilities.at(string(b, "facility"));
                const auto max = s.definition->catalog->facility(facility.type).maxDamage;
                if (!max || facility.damage < *max) { roll(s, b, "naval_port_aa", aircraft); return; }
            }
        }
        if (endIfOver(s, b)) return;
        if (oneRound(b)) { finishBattle(s, b, "one_round"); return; }
        if (integer(b, "naval_round_shots") == 0) { finishBattle(s, b, "stalemate"); return; }
        auto origins = retreatOrigins(s, b);
        bool ship = false, air = false;
        for (const auto& id : living(s, b, true)) { ship |= has(s, s.units.at(id), "naval"); air |= plane(s, s.units.at(id)); }
        if ((!ship || !origins.empty()) && (ship || air)) {
            std::vector<Action> choices{
                action(s, b.attacker, "naval_continue_fighting", {{"battle", V(b.id)}}),
                action(s, b.attacker, "naval_retreat_begin", {{"battle", V(b.id)}})};
            b.stage = "naval_retreat"; decision(s, b, b.attacker, "naval_retreat_or_continue", std::move(choices)); return;
        }
        put(b, "round", num(integer(b, "round", 1) + 1)); put(b, "naval_round_shots", num(0)); b.stage = "naval_attacker_fire"; advance(s, b); return;
    }
    if (b.stage == "naval_retreat_assign") { assignRetreat(s, b); return; }
    if (b.stage == "naval_aftermath") { finishBattle(s, b, string(b, "result")); return; }
}
} // namespace

Id registerNavalBattle(State& s, const Id& zone, const Id& attacker,
                       const std::vector<Id>& attackers, const std::map<Id, Id>& origins, const V& options) {
    require(s.definition->geography.require("nodes").find(zone) && s.nations.contains(attacker) && !attackers.empty(),
            "Invalid naval battle registration");
    require(options.isObject(), "Naval battle options must be an object");
    const bool attackingRaider = std::any_of(attackers.begin(), attackers.end(), [&](const Id& id) {
        return s.units.contains(id) && s.units.at(id).type == "battlecruiser" && marked(s.units.at(id).gameFlags, "raider");
    });
    require(!attackingRaider || attackers.size() == 1, "A designated raider cannot combine with other attackers");
    const Id context = options.find("context") ? options.require("context").asString() : "standard";
    for (auto& [bid, existing] : s.battles)
        if (marked(existing.flags, "naval_battle") && existing.stage == "naval_declared" &&
            existing.zone == zone && existing.attacker == attacker && string(existing, "context") == context &&
            (context != "port_attack" || string(existing, "facility") == (options.find("facility") ? options.require("facility").asString() : ""))) {
            require(!attackingRaider && std::none_of(existing.attackers.begin(), existing.attackers.end(), [&](const Id& id) {
                return s.units.contains(id) && s.units.at(id).type == "battlecruiser" && marked(s.units.at(id).gameFlags, "raider");
            }), "A designated raider cannot combine with other attackers");
            auto oldOrigins = object(existing, "origins"); auto entries = array(existing, "naval_entry_origins");
            for (const auto& id : attackers) {
                require(s.units.contains(id) && s.units.at(id).owner == attacker && s.units.at(id).zone == zone,
                        "Invalid merged naval attacker");
                if (std::find(existing.attackers.begin(), existing.attackers.end(), id) == existing.attackers.end()) existing.attackers.push_back(id);
                if (origins.contains(id)) { oldOrigins[id] = V(origins.at(id)); if (has(s, s.units.at(id), "naval")) entries.emplace_back(origins.at(id)); }
            }
            if (const auto* defenders = options.find("defenders"))
                for (const auto& id : readIds(*defenders)) if (std::find(existing.defenders.begin(), existing.defenders.end(), id) == existing.defenders.end()) existing.defenders.push_back(id);
            put(existing, "origins", V(oldOrigins)); put(existing, "naval_entry_origins", V(entries)); return bid;
        }
    BattleState b; b.id = "naval_battle_" + std::to_string(++s.flags["naval_battle_sequence"]);
    b.zone = zone; b.attacker = attacker; b.stage = "naval_declared"; b.attackers = attackers; b.data = options;
    b.flags["naval_battle"] = 1;
    if (!b.data.find("context")) put(b, "context", V(std::string("standard")));
    O originData; A entries;
    for (const auto& id : attackers) {
        require(s.units.contains(id) && s.units.at(id).owner == attacker && s.units.at(id).zone == zone,
                "Naval attackers must be one nation's units in the battle zone");
        require(has(s, s.units.at(id), "naval") || plane(s, s.units.at(id)), "Invalid naval attacker type");
        if (origins.contains(id)) {
            originData[id] = V(origins.at(id));
            if (has(s, s.units.at(id), "naval")) entries.emplace_back(origins.at(id));
        }
    }
    if (const auto* defenders = options.find("defenders")) b.defenders = readIds(*defenders);
    else for (const auto& [id, u] : s.units)
        if (u.zone == zone && hostile(s, attacker, u.owner) && (has(s, u, "naval") || plane(s, u))) b.defenders.push_back(id);
    for (const auto& id : b.defenders) {
        const bool inPort = string(b, "context") == "port_attack" && b.data.find("facility") &&
            s.facilities.contains(string(b, "facility")) && s.units.contains(id) &&
            s.units.at(id).zone == s.facilities.at(string(b, "facility")).zone;
        require(s.units.contains(id) && (s.units.at(id).zone == zone || inPort) && hostile(s, attacker, s.units.at(id).owner),
                "Invalid naval defender");
        if (b.defender.empty()) b.defender = s.units.at(id).owner;
    }
    if (b.defender.empty()) b.defender = attacker;
    put(b, "origins", V(originData)); put(b, "naval_entry_origins", V(entries)); put(b, "round", num(1));
    const auto id = b.id; s.battleOrder.push_back(id); s.battles.emplace(id, std::move(b));
    if (s.clock.phase != Phase::Combat && immediateBattle(s.battles.at(id)))
        s.flags["immediate_naval_battles"] = 1;
    return id;
}
void beginNavalBattle(State& s, const Id& id) {
    auto& b = s.battles.at(id);
    require(marked(b.flags, "naval_battle") && b.stage == "naval_declared" && !s.chance && s.decisions.empty(),
            "Naval battle cannot begin now");
    const Id targetZone = string(b, "context") == "port_attack" && b.data.find("facility") &&
        s.facilities.contains(string(b, "facility")) ? s.facilities.at(string(b, "facility")).zone : b.zone;
    if (b.attacker == "japan" && marked(s.nations.at("japan").turnFlags, "surprise_attack_zone:" + targetZone) &&
        !marked(s.nations.at("japan").turnFlags, "surprise_attack_used")) {
        b.flags["japanese_surprise_attack"] = 1;
        s.nations.at("japan").turnFlags["surprise_attack_used"] = 1;
        if (string(b, "context") != "port_attack") s.nations.at("japan").turnFlags["surprise_attack_naval_sea:" + b.zone] = 1;
    }
    for (const auto& unit : b.attackers)
        if (s.units.contains(unit)) s.units.at(unit).turnFlags["naval_combat_turn"] = static_cast<int>(s.clock.playerTurnSerial + 1);
    for (const auto& unit : b.defenders)
        if (s.units.contains(unit)) s.units.at(unit).turnFlags["naval_combat_turn"] = static_cast<int>(s.clock.playerTurnSerial + 1);
    if (b.defenders.size() == 1 && s.units.at(b.defenders.front()).type == "battlecruiser" &&
        marked(s.units.at(b.defenders.front()).gameFlags, "raider")) put(b, "one_round", V(true));
    b.stage = "naval_raider_discovery"; advance(s, b);
}
std::vector<Action> navalCombatActions(const State& s) {
    if (s.chance || !s.decisions.empty()) return {};
    std::vector<Action> out;
    for (const auto& id : s.battleOrder) {
        const auto it = s.battles.find(id); if (it == s.battles.end()) continue;
        const auto& b = it->second; if (!marked(b.flags, "naval_battle")) continue;
        if (marked(b.flags, "finished")) return {action(s, s.currentNation(), "naval_finish_battle", {{"battle", V(id)}})};
        if (b.stage != "naval_declared") return {action(s, s.currentNation(), "naval_progress_battle", {{"battle", V(id)}})};
    }
    for (const auto& id : s.battleOrder) {
        const auto it = s.battles.find(id); if (it == s.battles.end()) continue;
        if (marked(it->second.flags, "naval_battle") && it->second.stage == "naval_declared" &&
            (s.clock.phase == Phase::Combat || immediateBattle(it->second)))
            out.push_back(action(s, s.currentNation(), "naval_begin_battle", {{"battle", V(id)}}));
    }
    return out;
}
bool applyNavalCombatAction(State& s, const Action& a) {
    if (a.kind.rfind("naval_", 0) != 0 || !a.parameters.find("battle")) return false;
    const auto id = a.parameters.require("battle").asString();
    if (!s.battles.contains(id) || !marked(s.battles.at(id).flags, "naval_battle")) return false;
    auto& b = s.battles.at(id);
    if (a.kind == "naval_finish_battle") {
        require(marked(b.flags, "finished"), "Naval battle has not finished");
        s.battleOrder.erase(std::remove(s.battleOrder.begin(), s.battleOrder.end(), id), s.battleOrder.end());
        s.battles.erase(id); return true;
    }
    if (a.kind == "naval_begin_battle") { beginNavalBattle(s, id); return true; }
    if (a.kind == "naval_progress_battle") { advance(s, b); return true; }
    if (a.kind == "naval_take_casualty") {
        release(s, a); const auto selected = a.parameters.require("unit").asString();
        const auto hits = array(b, "naval_hits"); const auto& hit = hits.at(static_cast<std::size_t>(integer(b, "naval_hit_index")));
        if (!a.parameters.require("targeted").asBool() && !hit.require("victim_attacker").asBool() &&
            !marked(b.flags, "naval_casualty_dispute_decided")) {
            const auto candidates = eligibleHit(s, b, hit);
            const bool joint = std::any_of(candidates.begin(), candidates.end(), [&](const Id& unit) {
                return politicalPlayer(s, s.units.at(unit).owner) != politicalPlayer(s, b.defender);
            });
            if (joint) { put(b, "naval_casualty_proposal", V(selected)); put(b, "naval_casualty_consents", V(O{})); chooseHit(s, b); return true; }
        }
        b.flags.erase("naval_casualty_dispute_decided");
        takeHit(s, b, selected, boolean(b, "naval_immediate_hits"));
        put(b, "naval_hit_index", num(integer(b, "naval_hit_index") + 1)); chooseHit(s, b); return true;
    }
    if (a.kind == "naval_ignore_raider" || a.kind == "naval_raider_slip" || a.kind == "naval_raider_stay") {
        release(s, a); const auto unit = a.parameters.require("unit").asString();
        auto choices = object(b, "naval_raider_choices"); choices[unit] = V(true); put(b, "naval_raider_choices", V(choices));
        if (a.kind != "naval_raider_stay") { auto excluded = object(b, "naval_excluded"); excluded[unit] = V(true); put(b, "naval_excluded", V(excluded)); }
        b.stage = "naval_raider_discovery"; advance(s, b); return true;
    }
    if (a.kind == "naval_discover_raider") {
        release(s, a); put(b, "naval_discovering_raider", a.parameters.require("unit")); roll(s, b, "naval_raider_discovery", 2); return true;
    }
    if (a.kind == "naval_casualty_accept") {
        release(s, a); auto consents = object(b, "naval_casualty_consents"); consents[politicalPlayer(s, a.nation)] = V(true);
        put(b, "naval_casualty_consents", V(consents)); chooseHit(s, b); return true;
    }
    if (a.kind == "naval_casualty_dispute") {
        release(s, a); put(b, "naval_casualty_proposal", V(std::string{}));
        std::map<Id, Id> nations; const auto hit = array(b, "naval_hits").at(static_cast<std::size_t>(integer(b, "naval_hit_index")));
        for (const auto& id : eligibleHit(s, b, hit)) nations[politicalPlayer(s, s.units.at(id).owner)] = s.units.at(id).owner;
        A list; for (const auto& [player, nation] : nations) list.emplace_back(nation);
        put(b, "naval_disputing_nations", V(list)); roll(s, b, "naval_casualty_dispute", static_cast<int>(list.size())); return true;
    }
    if (a.kind == "naval_sub_decline" || a.kind == "naval_sub_protected" || a.kind == "naval_sub_unprotected") {
        release(s, a); const auto unit = a.parameters.require("unit").asString();
        auto done = object(b, "naval_submarine_choices"); done[unit] = V(true); put(b, "naval_submarine_choices", V(done));
        if (a.kind == "naval_sub_decline") { auto excluded = object(b, "naval_excluded"); excluded[unit] = V(true); put(b, "naval_excluded", V(excluded)); }
        if (a.kind == "naval_sub_protected") { auto protectedSubs = object(b, "naval_protected_submarines"); protectedSubs[unit] = V(true); put(b, "naval_protected_submarines", V(protectedSubs)); }
        advance(s, b); return true;
    }
    if (a.kind == "naval_pair_destroyer" || a.kind == "naval_decline_pair") {
        release(s, a); const auto unit = a.parameters.require("unit").asString();
        auto done = object(b, "naval_pairing_done"); done[unit] = V(true); put(b, "naval_pairing_done", V(done));
        if (a.kind == "naval_pair_destroyer") {
            if (std::find(b.attackers.begin(), b.attackers.end(), unit) == b.attackers.end() &&
                std::find(b.defenders.begin(), b.defenders.end(), unit) == b.defenders.end()) {
                b.defenders.push_back(unit); s.units.at(unit).turnFlags["naval_combat_turn"] = static_cast<int>(s.clock.playerTurnSerial + 1);
            }
            auto pairs = object(b, "naval_destroyer_pairs"); pairs[unit] = a.parameters.require("aircraft"); put(b, "naval_destroyer_pairs", V(pairs)); }
        advance(s, b); return true;
    }
    if (a.kind == "naval_decline_scramble" || a.kind == "naval_scramble") {
        release(s, a); const auto unit = a.parameters.require("unit").asString();
        auto done = object(b, "naval_scramble_choices"); done[unit] = V(true); put(b, "naval_scramble_choices", V(done));
        if (a.kind == "naval_scramble") {
            const auto facility = a.parameters.require("facility").asString(); auto& f = s.facilities.at(facility);
            if (!f.flags.contains("naval_scramble_turn") || f.flags.at("naval_scramble_turn") != static_cast<int>(s.clock.playerTurnSerial + 1)) f.flags["naval_scramble_used"] = 0;
            f.flags["naval_scramble_turn"] = static_cast<int>(s.clock.playerTurnSerial + 1); ++f.flags["naval_scramble_used"];
            auto& u = s.units.at(unit); u.gameFlags.erase("in_port:" + facility); u.zone = b.zone;
            u.commitments.insert("naval_scramble_origin:" + facility); u.turnFlags["naval_combat_turn"] = static_cast<int>(s.clock.playerTurnSerial + 1);
            b.defenders.push_back(unit);
        }
        advance(s, b); return true;
    }
    if (a.kind == "naval_carrier_land") {
        release(s, a); const auto unit = a.parameters.require("unit").asString(), destination = a.parameters.require("destination").asString();
        require(airLandingAvailable(s, unit, destination), "Carrier rescue landing no longer available");
        auto& u = s.units.at(unit); const auto zone = s.units.contains(destination) ? s.units.at(destination).zone : destination;
        if (zone != u.zone) u.movementRemaining = std::max(0, u.movementRemaining.value_or(0) - 1);
        u.zone = zone; u.turnFlags.erase("air_in_flight");
        if (s.units.contains(destination)) attachCargo(s, destination, unit);
        auto queue = array(b, "naval_carrier_landing_queue"); queue.erase(queue.begin()); put(b, "naval_carrier_landing_queue", V(queue));
        advance(s, b); return true;
    }
    if (a.kind == "naval_continue_fighting") { release(s, a); put(b, "round", num(integer(b, "round", 1) + 1)); put(b, "naval_round_shots", num(0)); b.stage = "naval_attacker_fire"; advance(s, b); return true; }
    if (a.kind == "naval_retreat_begin") { release(s, a); b.stage = "naval_retreat_assign"; assignRetreat(s, b); return true; }
    if (a.kind == "naval_retreat_unit") {
        release(s, a); auto& u = s.units.at(a.parameters.require("unit").asString()); const auto destination = a.parameters.require("zone").asString();
        require(retreatOrigins(s, b).contains(destination), "Naval retreat destination is not an entry sea zone");
        u.zone = destination; u.movementRemaining = 0; u.turnFlags["naval_retreated"] = 1; u.commitments.insert("retreated");
        for (const auto& cargo : u.cargo) s.units.at(cargo).zone = destination;
        assignRetreat(s, b); return true;
    }
    return false;
}
bool applyNavalCombatChance(State& s, const ChanceRequest& request, const ChanceOutcome& outcome) {
    if (request.purpose == "naval_raider_discovery") {
        auto& b = s.battles.at(request.continuation); const auto results = effectiveResults(request, outcome);
        require(results.size() == 2, "Raider discovery requires two dice"); const auto unit = string(b, "naval_discovering_raider");
        const auto owner = s.units.at(unit).owner; int opponent = 0;
        for (const auto& id : living(s, b, true)) {
            const auto& u = s.units.at(id); if (has(s, u, "surface_warship")) ++opponent;
            if (plane(s, u) && s.definition->catalog->stats(u.type, u.damage, catalogContext(s, u.owner, u.zone)).attack) opponent += 4;
        }
        const int raider = results[0] + 6 + (tech(s, owner, "radar") ? 1 : 0);
        const int attack = results[1] + opponent + (tech(s, b.attacker, "radar") ? 1 : 0);
        if (raider == attack) { roll(s, b, "naval_raider_discovery", 2); return true; }
        if (raider > attack) {
            decision(s, b, owner, "naval_raider_slip_choice", {
                action(s, owner, "naval_raider_slip", {{"battle", V(b.id)}, {"unit", V(unit)}}),
                action(s, owner, "naval_raider_stay", {{"battle", V(b.id)}, {"unit", V(unit)}})}); return true;
        }
        auto choices = object(b, "naval_raider_choices"); choices[unit] = V(true); put(b, "naval_raider_choices", V(choices));
        b.stage = "naval_raider_discovery"; advance(s, b); return true;
    }
    if (request.purpose == "naval_casualty_dispute") {
        auto& b = s.battles.at(request.continuation); const auto results = effectiveResults(request, outcome);
        const auto nations = array(b, "naval_disputing_nations"); require(results.size() == nations.size(), "Naval dispute dice mismatch");
        const int top = *std::max_element(results.begin(), results.end()); A tied;
        for (std::size_t i = 0; i < results.size(); ++i) if (results[i] == top) tied.push_back(nations[i]);
        if (tied.size() > 1) { put(b, "naval_disputing_nations", V(tied)); roll(s, b, "naval_casualty_dispute", static_cast<int>(tied.size())); return true; }
        const auto chooser = tied.front().asString();
        const auto hit = array(b, "naval_hits").at(static_cast<std::size_t>(integer(b, "naval_hit_index")));
        std::vector<Action> options; for (const auto& unit : eligibleHit(s, b, hit))
            options.push_back(action(s, chooser, "naval_take_casualty", {{"battle", V(b.id)}, {"unit", V(unit)}, {"targeted", V(false)}}));
        b.flags["naval_casualty_dispute_decided"] = 1; decision(s, b, chooser, "naval_casualty", std::move(options)); return true;
    }
    if (request.purpose == "naval_port_aa") {
        auto& b = s.battles.at(request.continuation); const auto results = effectiveResults(request, outcome);
        A hits; auto eligible = living(s, b, true);
        eligible.erase(std::remove_if(eligible.begin(), eligible.end(), [&](const Id& id) { return !plane(s, s.units.at(id)); }), eligible.end());
        for (const auto result : results) if (result <= 3)
            hits.emplace_back(O{{"victim_attacker", V(true)}, {"nation", V(b.defender)}, {"targeted", V(false)},
                                {"target_classes", V(A{})}, {"eligible", V(ids(eligible))}, {"air_priority", V(false)}});
        put(b, "naval_hits", V(hits)); put(b, "naval_hit_index", num(0)); put(b, "naval_after_roll", V(std::string("naval_round_end")));
        put(b, "naval_immediate_hits", V(true)); b.stage = "naval_choose_hits"; chooseHit(s, b); return true;
    }
    if (request.purpose != "naval_combat_roll") return false;
    auto& b = s.battles.at(request.continuation); const auto shots = array(b, "naval_shots");
    const auto results = effectiveResults(request, outcome); require(results.size() == shots.size(), "Naval dice mismatch");
    A hits;
    for (std::size_t i = 0; i < shots.size(); ++i) {
        auto hit = shots[i].asObject(); const int threshold = shots[i].require("threshold").asInt();
        const int extra = shots[i].find("asw_sub_bonus") ? shots[i].require("asw_sub_bonus").asInt() : 0;
        if (results[i] > threshold + extra) continue;
        if (results[i] > threshold) {
            auto eligible = readIds(shots[i].require("eligible"));
            eligible.erase(std::remove_if(eligible.begin(), eligible.end(), [&](const Id& id) { return !s.units.contains(id) || !sub(s, s.units.at(id)); }), eligible.end());
            if (eligible.empty()) continue;
            hit["eligible"] = V(ids(eligible));
        }
        hit["targeted"] = V(results[i] <= shots[i].require("target").asInt()); hits.emplace_back(hit);
    }
    put(b, "naval_hits", V(hits)); put(b, "naval_hit_index", num(0)); b.stage = "naval_choose_hits"; chooseHit(s, b); return true;
}
bool navalCombatPhaseComplete(const State& s) {
    return std::none_of(s.battles.begin(), s.battles.end(), [&](const auto& entry) {
        const auto& b = entry.second;
        if (s.clock.phase == Phase::CombatMovement && b.stage == "naval_declared" &&
            !immediateBattle(b)) return false;
        return marked(b.flags, "naval_battle") && !marked(b.flags, "finished");
    });
}
} // namespace game::campaign
