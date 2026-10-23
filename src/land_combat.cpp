#include "game/land_combat.hpp"
#include "game/air.hpp"
#include "game/movement.hpp"
#include "game/naval.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <functional>
#include <limits>
#include <stdexcept>

namespace game::campaign {
namespace {
using V = json::Value;
using O = V::Object;
using A = V::Array;
void require(bool ok, const std::string &message) {
    if (!ok)
        throw std::runtime_error(message);
}
V num(int n) {
    return V(static_cast<double>(n));
}
bool marked(const std::map<Id, int> &f, const Id &k) {
    auto i = f.find(k);
    return i != f.end() && i->second != 0;
}
void put(BattleState &b, const Id &key, V value) {
    auto o = b.data.asObject();
    o[key] = std::move(value);
    b.data = V(std::move(o));
}
int integer(const BattleState &b, const Id &k, int d = 0) {
    const auto *v = b.data.find(k);
    return v ? v->asInt() : d;
}
std::string string(const BattleState &b, const Id &k, std::string d = {}) {
    const auto *v = b.data.find(k);
    return v ? v->asString() : d;
}
A array(const BattleState &b, const Id &k) {
    const auto *v = b.data.find(k);
    return v ? v->asArray() : A{};
}
O object(const BattleState &b, const Id &k) {
    const auto *v = b.data.find(k);
    return v ? v->asObject() : O{};
}
V ids(const std::vector<Id> &x) {
    A a;
    for (const auto &id : x)
        a.emplace_back(id);
    return V(std::move(a));
}
std::vector<Id> readIds(const V &x) {
    std::vector<Id> v;
    for (const auto &a : x.asArray())
        v.push_back(a.asString());
    return v;
}
const V &node(const State &s, const Id &id) {
    return s.definition->geography.require("nodes").require(id);
}
const V *edge(const State &s, const Id &from, const Id &to) {
    if (from.empty()) return nullptr; // Shared-zone battles have no entry edge.
    for (const auto &e : node(s, from).require("neighbors").asArray())
        if (e.require("neighbor_id").asString() == to)
            return &e;
    return nullptr;
}
std::set<Id> terrain(const V *value) {
    std::set<Id> out;
    if (!value || value->isNull())
        return out;
    if (value->isString())
        out.insert(value->asString());
    if (value->isArray())
        for (const auto &x : value->asArray())
            if (x.isString())
                out.insert(x.asString());
    return out;
}
bool has(const State &s, const UnitState &u, const Id &c) {
    return s.definition->catalog->unit(u.type).classes.contains(c);
}
bool aircraft(const State &s, const UnitState &u) {
    return has(s, u, "aircraft");
}
bool fighter(const UnitState &u) {
    return u.type == "fighter" || u.type == "jet_fighter";
}
bool transport(const UnitState &u) {
    return u.type == "air_transport" || u.type == "heavy_air_transport";
}
bool airborne(const UnitState &u) {
    return u.commitments.contains("airborne_assault") || marked(u.turnFlags, "airborne_assault");
}
bool amphibious(const UnitState &u) {
    return u.commitments.contains("amphibious_assault") || marked(u.turnFlags, "amphibious_assault");
}
bool ground(const State &s, const UnitState &u) {
    return has(s, u, "land");
}
bool doubleAmphibiousCasualty(const State &s, const BattleState &b, const Id &id) {
    if (integer(b,"round",1)!=1 || !s.units.contains(id)) return false;
    const auto &u=s.units.at(id);
    return ground(s,u) && amphibious(u) && u.type!="marine" &&
        !(has(s,u,"infantry_class") &&
          catalogContext(s,u.owner,u.zone).technologies.contains("amphibious_doctrine"));
}
bool operational(const State &s, const BattleState &b, const Id &id) {
    if (!s.units.contains(id))
        return false;
    const auto &u = s.units.at(id);
    if (u.zone != b.zone && !(marked(b.flags, "attrition") &&
                              std::find(b.attackers.begin(), b.attackers.end(), id) != b.attackers.end()))
        return false;
    auto used = u.turnFlags.find("air_battle_turn");
    if (aircraft(s, u) && used != u.turnFlags.end() &&
        used->second == static_cast<int>(s.clock.playerTurnSerial + 1) &&
        !u.commitments.contains("air_battle:" + b.id))
        return false;
    const auto grounded = object(b, "grounded");
    return !grounded.contains(id) && !marked(u.turnFlags, "land_retreating");
}
std::vector<Id> living(const State &s, const BattleState &b, bool attacker) {
    std::vector<Id> out;
    for (const auto &id : attacker ? b.attackers : b.defenders)
        if (operational(s, b, id))
            out.push_back(id);
    return out;
}
bool opposing(const State &s, const Id &a, const Id &b) {
    return a != b && s.nations.at(a).atWarWith.contains(b);
}
Id approach(const BattleState &b, const Id &id) {
    const auto o = object(b, "origins");
    return o.contains(id) ? o.at(id).asString() : Id{};
}
bool city(const State &s, const Id &zone) {
    const auto *c = node(s, zone).find("is_city");
    return c && c->isBool() && c->asBool();
}
bool fortBorder(const State &s, const FacilityState &f, const Id &from) {
    if (f.type != "fortification" || f.damage || marked(f.flags, "under_construction"))
        return false;
    if (marked(f.flags, "border_" + from) || marked(f.flags, "towards_" + from) ||
        marked(f.flags, "border:" + from))
        return true;
    const auto *fs = s.definition->geography.find("facilities");
    if (fs && fs->isObject())
        if (const auto *source = fs->find(f.id)) {
            for (const auto &key : {"border_id", "neighbor_id", "towards", "sea_id"})
                if (const auto *v = source->find(key))
                    if (v->isString() && v->asString() == from)
                        return true;
            if (const auto *a = source->find("borders"))
                if (a->isArray())
                    for (const auto &v : a->asArray())
                        if (v.isString() && v.asString() == from)
                            return true;
        }
    return false;
}
std::vector<Id> protectedAttackers(const State &s, const BattleState &b, const FacilityState &f) {
    std::vector<Id> out;
    for (const auto &id : living(s, b, true))
        if (fortBorder(s, f, approach(b, id)))
            out.push_back(id);
    return out;
}
bool fortActive(const State &s, const BattleState &b) {
    if (marked(b.flags, "ignore_fortification"))
        return false;
    for (const auto &[id, f] : s.facilities)
        if (f.zone == b.zone && !protectedAttackers(s, b, f).empty())
            return true;
    return false;
}
Action action(const State &s, const Id &nation, const Id &kind, O p = {}) {
    Action a;
    a.kind = kind;
    a.nation = nation;
    a.player = politicalPlayer(s, nation);
    a.parameters = V(std::move(p));
    a.id = kind + "_" + contentDigest(canonicalJson(a.parameters)).substr(0, 20);
    return a;
}
void decision(State &s, BattleState &b, const Id &nation, const Id &kind, std::vector<Action> options) {
    require(!options.empty(), "Empty land battle decision");
    Decision d;
    d.id = b.id + "_" + kind + "_" + std::to_string(++s.flags["land_decision_sequence"]);
    d.kind = kind;
    d.nation = nation;
    d.reaction = nation != s.currentNation();
    d.continuation = b.id;
    for (auto &a : options) {
        a.decision = d.id;
        a.nation = nation;
        a.player = politicalPlayer(s, nation);
    }
    d.options = std::move(options);
    s.decisions.push_back(std::move(d));
}
void release(State &s, const Action &a) {
    require(a.decision && !s.decisions.empty() && s.decisions.back().id == *a.decision,
            "Missing land combat decision");
    s.decisions.pop_back();
}
void refreshImmediateBattles(State& s) {
    const bool pending = std::any_of(s.battles.begin(), s.battles.end(), [](const auto& entry) {
        return marked(entry.second.flags, "chinese_truce_termination");
    });
    if (pending) s.flags["immediate_land_battles"] = 1;
    else s.flags.erase("immediate_land_battles");
}
bool pendingAmphibiousPreparation(const State& s, const BattleState& land) {
    return std::any_of(s.battles.begin(), s.battles.end(), [&](const auto& entry) {
        const auto& prep = entry.second;
        return marked(prep.flags, "amphibious_preparation") &&
               prep.zone == land.zone && prep.attacker == land.attacker;
    });
}
void setStage(BattleState &b, const Id &stage) {
    b.stage = stage;
}
void eraseUnit(State &s, const Id &id) {
    if (s.units.contains(id))
        for (const auto &[key, value] : s.units.at(id).gameFlags)
            if (value && key.rfind("ship_crew:", 0) == 0) {
                const auto ship = key.substr(10);
                if (s.units.contains(ship)) {
                    const auto owner = s.units.at(ship).owner;
                    s.units.at(ship).gameFlags["skeleton_crew_until_own_turn"] =
                        navalCompletedTurns(s,owner) + (movementController(s,owner) ? 2 : 1);
                }
            }
    removePoliticalUnits(s, {id});
}
void eliminateUnsupportedRockets(State &s, BattleState &b) {
    std::vector<Id> doomed;
    for(const auto& [id,rocket]:s.units) {
        if(rocket.zone!=b.zone||rocket.carriedBy||!has(s,rocket,"rocket"))continue;
        bool enemyLand=false,supported=false;
        for(const auto& [other,u]:s.units) {
            if(other==id||u.zone!=b.zone||u.carriedBy)continue;
            if(ground(s,u)&&opposing(s,rocket.owner,u.owner)&&!politicallyFriendly(s,rocket.owner,u.owner))enemyLand=true;
            const bool participating=std::find(b.attackers.begin(),b.attackers.end(),other)!=b.attackers.end()||
                                     std::find(b.defenders.begin(),b.defenders.end(),other)!=b.defenders.end();
            if(participating&&!has(s,u,"rocket")&&operational(s,b,other)&&politicallyFriendly(s,rocket.owner,u.owner))supported=true;
        }
        if(enemyLand&&!supported)doomed.push_back(id);
    }
    // RB13.1.7: this is destruction by an occupying enemy land unit, never an
    // assignable combat casualty. Multiple unsupported rockets are all lost.
    for(const auto& id:doomed)if(s.units.contains(id))eraseUnit(s,id);
}
void clearPendingDead(State &s, BattleState &b) {
    auto dead = array(b, "pending_dead");
    for (const auto &id : array(b, "airborne_return_fire")) dead.push_back(id);
    put(b, "pending_dead", V(A{}));
    put(b, "airborne_return_fire", V(A{}));
    for (const auto &x : dead)
        if (s.units.contains(x.asString()))
            eraseUnit(s, x.asString());
}
void markDead(BattleState &b, const Id &id) {
    auto a = array(b, "pending_dead");
    if (std::none_of(a.begin(), a.end(), [&](const V &v) { return v.asString() == id; }))
        a.emplace_back(id);
    put(b, "pending_dead", V(std::move(a)));
}
bool pendingDead(const BattleState &b, const Id &id) {
    for (const auto &key : {"pending_dead", "airborne_return_fire"}) {
        const auto a = array(b, key);
        if (std::any_of(a.begin(), a.end(), [&](const V &v) { return v.asString() == id; })) return true;
    }
    return false;
}
void retreatUnit(State &s, const Id &id, const Id &to) {
    auto &u = s.units.at(id);
    u.zone = to;
    u.movementRemaining = 0;
    u.turnFlags["land_retreating"] = 1;
    u.commitments.insert("retreated");
}
void pruneUnits(State &s, BattleState &b) {
    for (auto *v : {&b.attackers, &b.defenders})
        v->erase(std::remove_if(v->begin(), v->end(), [&](const Id &id) { return !operational(s, b, id); }),
                 v->end());
}
std::vector<Id> eligibleHits(const State &s, const BattleState &b, const V &hit) {
    bool side = hit.require("victim_attacker").asBool();
    auto v = living(s, b, side);
    const auto *limit = hit.find("eligible");
    if (limit) {
        const auto restricted = readIds(*limit);
        v.erase(std::remove_if(v.begin(), v.end(),
                               [&](const Id &id) {
                                   return std::find(restricted.begin(), restricted.end(), id) ==
                                          restricted.end();
                               }),
                v.end());
    }
    v.erase(std::remove_if(v.begin(), v.end(), [&](const Id &id) {
        return pendingDead(b,id)||has(s,s.units.at(id),"rocket");
    }),v.end());
    if (const auto *extra=hit.find("amphibious_extra"); extra && extra->asBool())
        v.erase(std::remove_if(v.begin(),v.end(),[&](const Id &id){
            return !doubleAmphibiousCasualty(s,b,id);
        }),v.end());
    if (side && marked(b.flags,"amphibious_assault")) {
        const bool assaulting=std::any_of(v.begin(),v.end(),[&](const Id &id){
            return ground(s,s.units.at(id)) && amphibious(s.units.at(id));
        });
        if (assaulting) v.erase(std::remove_if(v.begin(),v.end(),[&](const Id &id){
            return ground(s,s.units.at(id)) && !amphibious(s.units.at(id));
        }),v.end());
    }
    const auto phase = string(b, "rolling_phase");
    if ((phase == "first_strike" || phase == "air_fire" || phase == "city_airborne_aaa") &&
        marked(b.flags, "airborne_assault"))
        v.erase(std::remove_if(v.begin(), v.end(),
                               [&](const Id &id) {
                                   const auto &u = s.units.at(id);
                                   return u.carriedBy && airborne(u);
                               }),
                v.end());
    const auto *only = hit.find("air_only");
    if (only && only->asBool())
        v.erase(
            std::remove_if(v.begin(), v.end(), [&](const Id &id) { return !aircraft(s, s.units.at(id)); }),
            v.end());
    const auto *preference = hit.find("air_priority");
    if (preference && preference->asBool()) {
        bool any = std::any_of(v.begin(), v.end(), [&](const Id &id) { return aircraft(s, s.units.at(id)); });
        if (any)
            v.erase(std::remove_if(v.begin(), v.end(),
                                   [&](const Id &id) { return !aircraft(s, s.units.at(id)); }),
                    v.end());
    }
    const auto *landOnly = hit.find("land_only");
    if (landOnly && landOnly->asBool())
        v.erase(std::remove_if(v.begin(), v.end(), [&](const Id &id) { return !ground(s, s.units.at(id)); }),
                v.end());
    bool carryingException = side && integer(b, "round", 1) == 1;
    bool notTransport = std::any_of(v.begin(), v.end(), [&](const Id &id) {
        const auto &u = s.units.at(id);
        return !transport(u) || (carryingException && airborne(u));
    });
    if (notTransport)
        v.erase(std::remove_if(v.begin(), v.end(),
                               [&](const Id &id) {
                                   const auto &u = s.units.at(id);
                                   return transport(u) && !(carryingException && airborne(u));
                               }),
                v.end());
    return v;
}
void advance(State &, BattleState &);
void chooseHit(State &s, BattleState &b) {
    auto hits = array(b, "hits");
    int index = integer(b, "hit_index");
    while (index < static_cast<int>(hits.size())) {
        auto hit = hits.at(static_cast<std::size_t>(index));
        auto candidates = eligibleHits(s, b, hit);
        if (candidates.empty()) {
            put(b, "hit_index", num(++index));
            continue;
        }
        const auto target = hit.find("target_classes");
        std::vector<Id> targets;
        if (target)
            for (const auto &id : candidates)
                for (const auto &c : target->asArray())
                    if (has(s, s.units.at(id), c.asString())) {
                        targets.push_back(id);
                        break;
                    }
        bool targeted = hit.require("targeted").asBool() && !targets.empty();
        if (targeted)
            candidates = std::move(targets);
        const bool victimAttacker = hit.require("victim_attacker").asBool();
        Id chooser =
            targeted ? hit.require("firing_nation").asString() : (victimAttacker ? b.attacker : b.defender);
        // Joint defense is explicit: propose a casualty, then every other
        // defending player may accept it or request the rulebook dice dispute.
        auto proposal = string(b, "casualty_proposal");
        if (!targeted && !victimAttacker && !proposal.empty()) {
            const auto checked = object(b, "casualty_consents");
            std::set<Id> players;
            for (const auto &id : candidates)
                players.insert(politicalPlayer(s, s.units.at(id).owner));
            for (const auto &id : candidates) {
                const auto &owner = s.units.at(id).owner;
                auto player = politicalPlayer(s, owner);
                if (player != politicalPlayer(s, b.defender) && !checked.contains(player)) {
                    std::vector<Action> options;
                    options.push_back(action(s, owner, "land_casualty_accept", {{"battle", V(b.id)}}));
                    options.push_back(action(s, owner, "land_casualty_dispute", {{"battle", V(b.id)}}));
                    decision(s, b, owner, "land_casualty_consent", std::move(options));
                    return;
                }
            }
            if (s.units.contains(proposal)) {
                markDead(b, proposal);
                put(b, "casualty_proposal", V(std::string{}));
                put(b, "casualty_consents", V(O{}));
                put(b, "hit_index", num(++index));
                continue;
            }
        }
        std::vector<Action> options;
        for (const auto &id : candidates)
            options.push_back(action(s, chooser, "land_take_casualty",
                                     {{"battle", V(b.id)}, {"unit", V(id)}, {"targeted", V(targeted)}}));
        decision(s, b, chooser, "land_casualty", std::move(options));
        return;
    }
    put(b, "hits", V(A{}));
    put(b, "hit_index", num(0));
    const auto after = string(b, "after_hits");
    if (after == "airborne_drop") {
        // Corrected airborne step 4 grants a not-yet-fired casualty its normal
        // roll. Fighters/AAA have already fired; linked transport losses were
        // removed together with their cargo when selected.
        const auto dead = array(b, "pending_dead");
        put(b, "pending_dead", V(A{}));
        A returning;
        for (const auto &entry : dead) {
            const auto &id = entry.asString();
            if (!s.units.contains(id)) continue;
            const auto &u = s.units.at(id);
            const bool attacking = std::find(b.attackers.begin(), b.attackers.end(), id) != b.attackers.end();
            const auto stats = landCombatStats(s, b, id, attacking, integer(b, "round", 1));
            bool ordinaryRoll = stats.threshold && stats.dice > 0;
            if (attacking && has(s, u, "strategic_bomber") && !airborne(u))
                for (const auto &mode : s.definition->catalog->modes(u.type, catalogContext(s, u.owner, u.zone), u.damage))
                    if (mode.id == "carpet_bombing" && mode.dice > 0) ordinaryRoll = true;
            if (!fighter(u) && !transport(u) && u.type != "seaplane" &&
                !has(s, u, "anti_aircraft_artillery_class") && !stats.firstStrike &&
                ordinaryRoll)
                returning.push_back(entry);
            else
                eraseUnit(s, id);
        }
        put(b, "airborne_return_fire", V(std::move(returning)));
    } else if (after == "defender_fire") {
        A returning;
        for (const auto &entry : array(b, "airborne_return_fire")) {
            const auto &id = entry.asString();
            if (std::find(b.attackers.begin(), b.attackers.end(), id) != b.attackers.end()) {
                if (s.units.contains(id)) eraseUnit(s, id);
            } else
                returning.push_back(entry);
        }
        put(b, "airborne_return_fire", V(std::move(returning)));
    } else
        clearPendingDead(s, b);
    if (after == "air_fire") {
        put(b, "attack_pairs", V(O{}));
        put(b, "defense_pairs", V(O{}));
        put(b, "after_pairing", V(std::string("air_fire")));
        setStage(b, "pair_attack");
    } else
        setStage(b, after);
    advance(s, b);
}
void addShot(A &shots, const Id &unit, const Id &nation, bool victimAttacker, int threshold, int target = 0,
             const std::set<Id> &classes = {}, O extra = {}) {
    O shot{{"unit", V(unit)},
           {"nation", V(nation)},
           {"victim_attacker", V(victimAttacker)},
           {"threshold", num(threshold)},
           {"target", num(target)}};
    A c;
    for (const auto &x : classes)
        c.emplace_back(x);
    shot["target_classes"] = V(std::move(c));
    for (auto &[k, v] : extra)
        shot[k] = std::move(v);
    shots.emplace_back(std::move(shot));
}
void requestShots(State &s, BattleState &b, A shots, const Id &after) {
    if (shots.empty()) {
        setStage(b, after);
        advance(s, b);
        return;
    }
    put(b, "shots", V(shots));
    put(b, "after_roll", V(after));
    put(b, "rolling_phase", V(b.stage));
    ChanceRequest c;
    c.id = b.id + "_roll_" + std::to_string(++s.flags["land_roll_sequence"]);
    c.continuation = b.id;
    c.nation = b.attacker;
    c.purpose = "land_combat_roll";
    for (std::size_t i = 0; i < shots.size(); ++i)
        c.dice.push_back(DieSpec{12, 0, {}, 0});
    s.chance = std::move(c);
}
void requestPairing(State &s, BattleState &b, bool attacker, const Id &after) {
    const auto current = living(s, b, attacker);
    auto pairs = object(b, attacker ? "attack_pairs" : "defense_pairs");
    std::set<Id> used;
    for (const auto &[art, companion] : pairs)
        used.insert(companion.asString());
    for (const auto &artillery : current)
        if (has(s, s.units.at(artillery), "artillery_class") && !pairs.contains(artillery)) {
            std::vector<Action> options;
            for (const auto &companion : current)
                if (!used.contains(companion) && (has(s, s.units.at(companion), "infantry_class") ||
                                                  has(s, s.units.at(companion), "vehicle_class")))
                    options.push_back(action(s, attacker ? b.attacker : b.defender, "land_pair_artillery",
                                             {{"battle", V(b.id)},
                                              {"artillery", V(artillery)},
                                              {"companion", V(companion)},
                                              {"attacking", V(attacker)}}));
            if (!options.empty()) {
                put(b, "pair_after", V(after));
                decision(s, b, attacker ? b.attacker : b.defender, "land_artillery_pairing",
                         std::move(options));
                return;
            }
        }
    setStage(b, after);
    advance(s, b);
}
void shoot(State &s, BattleState &b, const Id &which) {
    A shots;
    int round = integer(b, "round", 1);
    const bool first = which == "first_strike";
    const bool airStep = which == "air_fire";
    const bool attackerOnly = which == "attacker_fire" || which == "attrition_fire";
    if (which == "city_airborne_aaa") {
        if (city(s, b.zone) &&
            !catalogContext(s, b.attacker, b.zone).technologies.contains("airborne_doctrine"))
            for (const auto &id : living(s, b, true)) {
                const auto &u = s.units.at(id);
                if (aircraft(s, u) && airborne(u) && !u.cargo.empty())
                    addShot(shots, "city_aaa", b.defender, true, 3, 0, {},
                            {{"eligible", ids({id})}, {"air_only", V(true)}});
            }
        requestShots(s, b, std::move(shots), "first_strike");
        return;
    }
    for (bool attacking : {true, false}) {
        if (attackerOnly && !attacking)
            continue;
        if (which == "defender_fire" && attacking)
            continue;
        const auto opponents = living(s, b, !attacking);
        int enemyAircraft = static_cast<int>(std::count_if(
            opponents.begin(), opponents.end(), [&](const Id &id) { return aircraft(s, s.units.at(id)); }));
        for (const auto &id : living(s, b, attacking)) {
            const auto &u = s.units.at(id);
            const auto &definition = s.definition->catalog->unit(u.type);
            auto stats = landCombatStats(s, b, id, attacking, round);
            if (which == "attrition_fire") {
                addShot(shots, id, u.owner, false, fortActive(s, b) ? 1 : 2, 0, {}, {{"land_only", V(true)}});
                continue;
            }
            if (first) {
                if (!stats.firstStrike)
                    continue;
            } else if (airStep) {
                if (round != 1)
                    continue;
                if (has(s, u, "anti_aircraft_artillery_class")) {
                    // Corrected airborne step 4 resolves both sides' AAA and
                    // Fighters together before surviving transports land.
                    for (int n = 0; n < std::min(3, enemyAircraft); ++n)
                        addShot(shots, id, u.owner, !attacking, 3, 0, {}, {{"air_only", V(true)}});
                    continue;
                }
                if (!fighter(u) || stats.firstStrike)
                    continue;
            } else {
                if (round == 1 && (stats.firstStrike || fighter(u)))
                    continue;
                if (has(s, u, "anti_aircraft_artillery_class")) {

                    continue;
                }
            }
            if (u.type == "seaplane" || transport(u))
                continue;
            const bool carpet = attacking && definition.classes.contains("strategic_bomber");
            if (carpet) {
                if (round != 1 || airborne(u))
                    continue;
                if (!airStep)
                    for (const auto &m :
                         s.definition->catalog->modes(u.type, catalogContext(s, u.owner, u.zone), u.damage))
                        if (m.id == "carpet_bombing")
                            for (int n = 0; n < m.dice; ++n)
                                addShot(shots, id, u.owner, false,
                                        std::max(1, m.threshold.value_or(2) -
                                                        (city(s, b.zone) && fortActive(s, b) ? 1 : 0)),
                                        0, {}, {{"land_only", V(true)}});
                continue;
            }
            if (!stats.threshold) {
                // Minor KMT must still roll every attacking Infantry/Cavalry
                // even if the destination was empty or an attack value is N/A.
                if (attacking && u.owner == "kmt" && s.nations.at("kmt").powerStatus != "major" &&
                    (u.type == "infantry" || u.type == "cavalry"))
                    addShot(shots, id, u.owner, false, 0, 0, {}, {{"low_morale", V(true)}});
                continue;
            }
            O extra;
            if (!attacking && !fighter(u)) {
                std::vector<Id> eligible;
                for (const auto &target : opponents)
                    if (!(has(s, s.units.at(target), "strategic_bomber") && !airborne(s.units.at(target))))
                        eligible.push_back(target);
                extra["eligible"] = ids(eligible);
            }
            if (attacking && u.owner == "kmt" && s.nations.at("kmt").powerStatus != "major" &&
                (u.type == "infantry" || u.type == "cavalry"))
                extra["low_morale"] = V(true);
            if (fighter(u) && round == 1)
                extra["air_priority"] = V(true);
            if (!attacking && round == 1 && has(s, u, "infantry_class") && fortActive(s, b)) {
                auto withoutFort = b;
                withoutFort.flags["ignore_fortification"] = 1;
                const auto baseline = landCombatStats(s, withoutFort, id, false, round).threshold.value_or(0);
                extra["fort_baseline"] = num(baseline);
                std::vector<Id> eligible;
                for (const auto &[fid, f] : s.facilities)
                    if (f.zone == b.zone) {
                        auto p = protectedAttackers(s, b, f);
                        eligible.insert(eligible.end(), p.begin(), p.end());
                    }
                extra["fort_eligible"] = ids(eligible);
            }
            for (int n = 0; n < stats.dice; ++n)
                addShot(shots, id, u.owner, !attacking, *stats.threshold, stats.targetSelection,
                        stats.targetClasses, extra);
        }
    }
    if (first && round == 1)
        for (const auto &[id, f] : s.facilities)
            if (f.zone == b.zone && f.type == "fortification") {
                auto eligible = protectedAttackers(s, b, f);
                if (eligible.empty())
                    continue;
                bool doctrine = false;
                if (marked(b.flags, "airborne_assault"))
                    doctrine =
                        catalogContext(s, b.attacker, b.zone).technologies.contains("airborne_doctrine");
                if (doctrine)
                    continue;
                for (int n = 0; n < 2; ++n)
                    addShot(shots, id, b.defender, true, 5, 0, {}, {{"eligible", ids(eligible)}});
                for (const auto &unit : eligible)
                    if (s.units.contains(unit))
                        s.units.at(unit).turnFlags["crossed_enemy_fortification"] = 1;
            }
    Id after = first     ? "air_fire"
               : airStep ? (marked(b.flags, "airborne_assault") ? "airborne_drop" : "attacker_fire")
               : which == "attacker_fire" ? "defender_fire"
                                          : "round_end";
    requestShots(s, b, std::move(shots), after);
}
void finishPostBattle(State &s, BattleState &b) {
    if (s.chance || !s.decisions.empty())
        return;
    if (string(b, "result") == "attacker_wins" && !marked(b.flags, "blitz_pairing_done")) {
        const auto armor = blitzEligible(s, b);
        auto pairs = object(b, "blitz_pairs");
        std::set<Id> used;
        for (const auto &[tank, companions] : pairs)
            for (const auto &id : companions.asArray())
                used.insert(id.asString());
        for (const auto &id : armor)
            if (s.units.contains(id))
                s.units.at(id).turnFlags["blitz_eligible"] = 1;
        std::vector<Action> options;
        for (const auto &tank : armor) {
            int usedCapacity = 0;
            if (pairs.contains(tank))
                for (const auto &id : pairs.at(tank).asArray())
                    usedCapacity += s.units.at(id.asString()).type == "advanced_mechanized_infantry" ? 1 : 2;
            for (const auto &id : living(s, b, true)) {
                const auto &u = s.units.at(id);
                bool advanced = u.type == "advanced_mechanized_infantry";
                bool companion = advanced || u.type == "mechanized_infantry" ||
                                 u.type == "self_propelled_artillery" ||
                                 u.type == "advanced_self_propelled_artillery" || fighter(u) ||
                                 u.type == "tactical_bomber";
                if (!companion || used.contains(id) || !u.movementRemaining || *u.movementRemaining < 1 ||
                    marked(u.turnFlags, "crossed_enemy_fortification") || airborne(u) || amphibious(u) ||
                    usedCapacity + (advanced ? 1 : 2) > 2)
                    continue;
                options.push_back(action(s, b.attacker, "land_pair_blitz",
                                         {{"battle", V(b.id)}, {"armor", V(tank)}, {"unit", V(id)}}));
            }
        }
        if (!options.empty()) {
            options.push_back(action(s, b.attacker, "land_finish_blitz_pairing", {{"battle", V(b.id)}}));
            decision(s, b, b.attacker, "land_blitz_pairing", std::move(options));
            return;
        }
        b.flags["blitz_pairing_done"] = 1;
    }
    b.flags["finished"] = 1;
    b.stage = "finished";
    finishAirCombat(s, b.id);
}
void finishBattle(State &s, BattleState &b, const Id &result) {
    if (result=="attacker_wins" && integer(b,"round",1)==1 && marked(b.flags,"amphibious_assault"))
        releaseAmphibiousReserves(s,b.id);
    put(b, "result", V(result));
    b.stage = "post_capture";
    const auto alive = living(s, b, true);
    if (result == "attacker_wins" && !marked(b.flags, "capture_done")) {
        auto grounded = object(b, "grounded");
        for (const auto &[id, x] : grounded)
            if (s.units.contains(id))
                eraseUnit(s, id);
        bool occupying =
            std::any_of(alive.begin(), alive.end(), [&](const Id &id) { return ground(s, s.units.at(id)); });
        b.flags["capture_done"] = 1;
        if (occupying && !marked(b.flags, "attrition")) {
            resolveCapturedPorts(s, b.zone, b.attacker);
            captureLand(s, b.attacker, b.zone, withdrawalEligibleRecipients(s, b.attacker, b.zone));
        }
    }
    std::set<Id> crews;
    for (const auto &[id, unit] : s.units)
        for (const auto &[key, value] : unit.gameFlags)
            if (value && key.rfind("ship_crew:", 0) == 0 && unit.zone == b.zone) crews.insert(id);
    removePoliticalUnits(s, crews);
    finishPostBattle(s, b);
}

bool endIfOver(State &s, BattleState &b) {
    eliminateUnsupportedRockets(s,b);
    auto attackers = living(s, b, true), defenders = living(s, b, false);
    const bool onlyRockets=!defenders.empty()&&std::all_of(defenders.begin(),defenders.end(),[&](const Id& id){return has(s,s.units.at(id),"rocket");});
    if(onlyRockets&&std::none_of(attackers.begin(),attackers.end(),[&](const Id& id){return ground(s,s.units.at(id));})) {
        finishBattle(s,b,"defender_wins");return true;
    }
    // Unsupported seaplanes and transports cannot defend a land zone alone.
    bool defendingCombatant = std::any_of(defenders.begin(), defenders.end(), [&](const Id &id) {
        const auto &u = s.units.at(id);
        return u.type != "seaplane" && !transport(u);
    });
    if (!defendingCombatant)
        for (const auto &id : defenders)
            if (s.units.contains(id))
                eraseUnit(s, id);
    defenders = living(s, b, false);
    if (attackers.empty()) {
        finishBattle(s, b, defenders.empty() ? "mutual_destruction" : "defender_wins");
        return true;
    }
    if (defenders.empty()) {
        // Low-morale tests are an attack roll, even against empty territory.
        if (integer(b, "round", 1) == 1 && !marked(b.flags, "attack_rolled"))
            return false;
        finishBattle(s, b, "attacker_wins");
        return true;
    }
    return false;
}
void retreatDecision(State &s, BattleState &b, bool forced) {
    const auto origins = landRetreatOrigins(s, b);
    const auto current = living(s, b, true);
    std::vector<Id> retreatable;
    for (const auto &id : current) {
        const auto &u = s.units.at(id);
        if (ground(s, u) && !airborne(u) && !amphibious(u))
            retreatable.push_back(id);
    }
    const bool hasAir = std::any_of(current.begin(), current.end(),
                                    [&](const Id &id) { return aircraft(s, s.units.at(id)); });
    const bool strandedLand = !retreatable.empty() && origins.empty();
    if ((!forced && strandedLand) || ((retreatable.empty() || origins.empty()) && !hasAir)) {
        if (forced) {
            for (const auto &id : current)
                if (ground(s, s.units.at(id)))
                    eraseUnit(s, id);
            finishBattle(s, b, "forced_retreat");
        } else {
            put(b, "round", num(integer(b, "round", 1) + 1));
            put(b, "after_pairing", V(std::string("attacker_fire")));
            put(b, "attack_pairs", V(O{}));
            put(b, "defense_pairs", V(O{}));
            setStage(b, "pair_attack");
            advance(s, b);
        }
        return;
    }
    std::vector<Action> options;
    if (!forced)
        options.push_back(action(s, b.attacker, "land_continue_fighting", {{"battle", V(b.id)}}));
    options.push_back(action(s, b.attacker, "land_retreat_begin", {{"battle", V(b.id)}}));
    put(b, "forced_retreat", V(forced));
    decision(s, b, b.attacker, "land_retreat_or_continue", std::move(options));
}
void assignRetreat(State &s, BattleState &b) {
    for (const auto &id : living(s, b, true)) {
        const auto &u = s.units.at(id);
        if (!ground(s, u) || airborne(u) || amphibious(u))
            continue;
        auto origins = landRetreatOrigins(s, b);
        std::vector<Action> options;
        for (const auto &to : origins)
            options.push_back(action(s, b.attacker, "land_retreat_unit",
                                     {{"battle", V(b.id)}, {"unit", V(id)}, {"zone", V(to)}}));
        if (options.empty()) {
            const auto* forced = b.data.find("forced_retreat");
            require(forced && forced->asBool(), "Optional retreat cannot eliminate stranded land units");
            eraseUnit(s, id);
        } else {
            decision(s, b, b.attacker, "land_retreat_destination", std::move(options));
            return;
        }
    }
    auto exited = object(b, "exited_aircraft");
    auto current = living(s, b, true);
    for (const auto &id : current)
        if (aircraft(s, s.units.at(id))) {
            exited[id] = V(true);
            b.attackers.erase(std::remove(b.attackers.begin(), b.attackers.end(), id), b.attackers.end());
        }
    put(b, "exited_aircraft", V(exited));
    put(b, "air_landing_done", V(false));
    setStage(b, "retreat_air");
    finishAirCombat(s, b.id);
    advance(s, b);
}
void finishRetreat(State &s, BattleState &b) {
    const auto *ready = b.data.find("air_landing_done");
    if (!ready || !ready->asBool())
        return;
    bool forced = false;
    if (const auto *p = b.data.find("forced_retreat"))
        forced = p->asBool();
    if (forced) {
        for (const auto &id : living(s, b, true))
            if (ground(s, s.units.at(id)))
                eraseUnit(s, id);
        finishBattle(s, b, "forced_retreat");
        return;
    }
    const auto remaining = living(s, b, true);
    if (remaining.empty() || std::none_of(remaining.begin(), remaining.end(),
                                          [&](const Id &id) { return ground(s, s.units.at(id)); })) {
        finishBattle(s, b, "retreated");
        return;
    }
    put(b, "round", num(integer(b, "round", 1) + 1));
    put(b, "after_pairing", V(std::string("attacker_fire")));
    put(b, "attack_pairs", V(O{}));
    put(b, "defense_pairs", V(O{}));
    setStage(b, "pair_attack");
    advance(s, b);
}

void advance(State &s, BattleState &b) {
    if (s.chance || !s.decisions.empty() || marked(b.flags, "finished"))
        return;
    eliminateUnsupportedRockets(s,b);
    pruneUnits(s, b);
    if (b.stage == "awaiting_air_defence") {
        const auto *ready = b.data.find("air_defence_ready");
        if (!ready || !ready->asBool())
            return;
        setStage(b, "pair_attack");
        put(b, "after_pairing",
            V(marked(b.flags, "airborne_assault") ? std::string("city_airborne_aaa")
                                                  : std::string("first_strike")));
    }
    if (b.stage == "airborne_drop") {
        prepareLandAirborneDrop(s, b.id);
        const auto *ready = b.data.find("airborne_drop_ready");
        if (!ready || !ready->asBool())
            return;
        setStage(b, "attacker_fire");
    }
    if (b.stage == "pair_attack") {
        requestPairing(s, b, true, "pair_defense");
        return;
    }
    if (b.stage == "pair_defense") {
        requestPairing(
            s, b, false,
            string(b, "after_pairing", integer(b, "round", 1) == 1 ? "first_strike" : "attacker_fire"));
        return;
    }
    if (b.stage == "first_strike" || b.stage == "air_fire" || b.stage == "attacker_fire" ||
        b.stage == "defender_fire" || b.stage == "attrition_fire" || b.stage == "city_airborne_aaa") {
        if (b.stage == "defender_fire" && living(s, b, true).empty()) {
            clearPendingDead(s, b);
            finishBattle(s, b, living(s, b, false).empty() ? "mutual_destruction" : "defender_wins");
            return;
        }
        if (b.stage != "attacker_fire" && b.stage != "defender_fire" && endIfOver(s, b))
            return;
        if (b.stage == "attacker_fire")
            b.flags["attack_rolled"] = 1;
        shoot(s, b, b.stage);
        return;
    }
    if (b.stage == "choose_hits") {
        chooseHit(s, b);
        return;
    }
    if (b.stage == "post_capture") {
        finishPostBattle(s, b);
        return;
    }
    if (b.stage == "retreat_air") {
        finishRetreat(s, b);
        return;
    }
    if (b.stage == "retreat_assign") {
        assignRetreat(s, b);
        return;
    }
    if (b.stage == "round_end") {
        clearPendingDead(s, b);
        pruneUnits(s, b);
        if (integer(b, "round", 1) == 1 && marked(b.flags, "amphibious_assault"))
            releaseAmphibiousReserves(s, b.id);
        if (marked(b.flags, "attrition")) {
            finishBattle(s, b, "attrition_complete");
            return;
        }
        // RB10.2 requires the surviving carpet bombers to return immediately,
        // before choosing whether the remaining forces fight another round.
        if (integer(b, "round", 1) == 1 && !marked(b.flags,"carpet_return_started")) {
            b.flags["carpet_return_started"] = 1;
            auto exited = object(b, "exited_aircraft");
            std::vector<Id> bombers;
            for (const auto &id : living(s, b, true))
                if (has(s, s.units.at(id), "strategic_bomber") && !airborne(s.units.at(id))) {
                    exited[id] = V(true);
                    bombers.push_back(id);
                }
            put(b, "exited_aircraft", V(exited));
            for (const auto &[id, x] : exited)
                b.attackers.erase(std::remove(b.attackers.begin(), b.attackers.end(), id), b.attackers.end());
            if (!bombers.empty()) {
                returnCarpetBombers(s,b.id,bombers);
                if (s.chance || !s.decisions.empty()) return;
            }
        }
        if (endIfOver(s, b))
            return;
        auto t = terrain(node(s, b.zone).find("terrain"));
        if (integer(b, "round", 1) == 1)
            for (const auto &id : living(s, b, true))
                if (edge(s, approach(b, id), b.zone)) {
                    auto border = borderApproach(s, approach(b, id), b.zone).borderTerrain;
                    t.insert(border.begin(), border.end());
                }
        bool forced = (city(s, b.zone) && integer(b, "round", 1) >= 3 &&
                       !marked(b.flags, "japanese_surprise_attack")) ||
                      t.contains("tundra") || t.contains("ice") || t.contains("tundra/ice");
        setStage(b, "retreat");
        retreatDecision(s, b, forced);
        return;
    }
}
} // namespace

bool citySurrounded(const State &s, const Id &zone, const Id &defender) {
    if (!city(s, zone))
        return false;
    bool landNeighbor = false;
    for (const auto &e : node(s, zone).require("neighbors").asArray()) {
        auto id = e.require("neighbor_id").asString();
        if (!s.territories.contains(id))
            continue;
        landNeighbor = true;
        const auto owner = s.territories.at(id).possessor;
        if (!owner || !opposing(s, defender, *owner))
            return false;
    }
    if (!landNeighbor)
        return false;
    for (const auto &[id, f] : s.facilities)
        if (f.zone == zone && f.damage == 0 && !marked(f.flags, "under_construction")) {
            if (f.type == "airbase" || f.type == "airfield")
                return false;
            if (f.type.find("port") != Id::npos || f.type.find("dockyard") != Id::npos ||
                f.type.find("shipyard") != Id::npos) {
                if (!facilityBlockaded(s, defender, id))
                    return false;
            }
        }
    return true;
}

LandCombatStats landCombatStats(const State &s, const BattleState &b, const Id &id, bool attacking,
                                int round) {
    const auto &u = s.units.at(id);
    const auto &catalog = *s.definition->catalog;
    const auto &d = catalog.unit(u.type);
    auto base = catalog.stats(u.type, u.damage, catalogContext(s, u.owner, u.zone));
    LandCombatStats result;
    result.threshold = attacking ? base.attack : base.defense;
    result.dice = attacking ? base.attackDice : base.defenseDice;
    if (has(s, u, "anti_aircraft_artillery_class")) {
        result.threshold = std::nullopt;
        result.dice = 0;
        return result;
    }
    result.firstStrike =
        round == 1 &&
        (d.classes.contains("artillery_class") ||
         (attacking && u.owner == "japan" && aircraft(s, u) && marked(b.flags, "japanese_surprise_attack")));
    for (const auto &mode : catalog.modes(u.type, catalogContext(s, u.owner, u.zone), u.damage))
        if (mode.id == "target_selection") {
            const auto *enabled = mode.parameters.find(attacking ? "attack" : "defense");
            if (enabled && !enabled->asBool())
                continue;
            result.targetSelection = mode.threshold.value_or(0);
            if (const auto *c = mode.parameters.find("target_classes"))
                for (const auto &x : c->asArray())
                    result.targetClasses.insert(x.asString());
        }
    if (!result.threshold)
        return result;
    int positive = 0, negative = 0, extra = 0;
    auto bonus = [&](int n) {
        if (n > 0)
            positive = std::max(positive, n);
        else
            negative = std::min(negative, n);
    };
    auto t = terrain(node(s, b.zone).find("terrain"));
    if (round == 1 && attacking && edge(s, approach(b, id), b.zone)) {
        auto border = borderApproach(s, approach(b, id), b.zone).borderTerrain;
        t.insert(border.begin(), border.end());
    }
    if (round == 1 && !attacking)
        for (const auto &attacker : living(s, b, true))
            if (edge(s, approach(b, attacker), b.zone)) {
                auto border = borderApproach(s, approach(b, attacker), b.zone).borderTerrain;
                t.insert(border.begin(), border.end());
            }
    bool mountain =
        d.abilities.contains("mountain_infantry_terrain") || u.type == "foreign_legion" || u.type == "gurkha";
    if (!aircraft(s, u)) {
        if (t.contains("mountain") || t.contains("mountains")) {
            if (attacking && !mountain)
                bonus(-1);
            if (!attacking && mountain)
                bonus(1);
        }
        if (t.contains("desert")) {
            if (attacking && u.type != "foreign_legion")
                bonus(-1);
            if (attacking && u.type == "foreign_legion")
                bonus(1);
        }
        if ((t.contains("jungle") || t.contains("marsh")) && has(s, u, "vehicle_class"))
            bonus(-2);
        if (t.contains("jungle") && attacking && u.type == "gurkha")
            bonus(1);
        if (attacking && round == 1 && !has(s, u, "artillery_class") && u.type != "marine" && !airborne(u)) {
            if (edge(s, approach(b, id), b.zone) && borderApproach(s, approach(b, id), b.zone).river)
                bonus(-1);
        }
    }
    bool surrounded = citySurrounded(s, b.zone, b.defender);
    if (city(s, b.zone)) {
        if (!attacking && surrounded && !marked(u.turnFlags, "scrambled"))
            bonus(-1);
        if (!surrounded) {
            if (attacking && has(s, u, "vehicle_class"))
                bonus(-2);
            if (!attacking && has(s, u, "infantry_class")) {
                bonus(1);
                result.targetSelection = std::max(result.targetSelection, 1);
                result.targetClasses.insert("vehicle_class");
            }
        }
    }
    if (!attacking && round == 1 && has(s, u, "infantry_class") && fortActive(s, b))
        bonus(2);
    if (!attacking && u.owner == "japan" && has(s, u, "infantry_class") &&
        s.definition->factions.at("japan").homeCountry.contains(b.zone))
        extra += 1;
    if (!attacking && round == 1 && marked(b.flags, "japanese_surprise_attack"))
        extra -= 1;
    auto pairs = object(b, attacking ? "attack_pairs" : "defense_pairs");
    if (has(s, u, "artillery_class") && (!pairs.contains(id) || !s.units.contains(pairs.at(id).asString())))
        bonus(-1);
    if (attacking && has(s, u, "infantry_class"))
        for (const auto &[art, companion] : pairs)
            if (companion.asString() == id && s.units.contains(art))
                bonus(1);
    if (attacking && round == 1 && airborne(u) &&
        (u.type == "airborne_infantry" || u.type == "elite_airborne_infantry"))
        bonus(1);
    if (attacking && round == 1 && u.type == "marine" && marked(u.turnFlags, "from_attack_naval_transport"))
        bonus(1);
    result.threshold = std::max(1, *result.threshold + positive + negative + extra);
    return result;
}

Id registerLandBattle(State &s, const Id &zone, const Id &attacker, const std::vector<Id> &units,
                      const std::map<Id, Id> &origins) {
    require(s.territories.contains(zone) && s.nations.contains(attacker) && !units.empty(),
            "Invalid land battle registration");
    for (const auto &id : units) {
        require(s.units.contains(id) && s.units.at(id).owner == attacker,
                "Controlled minors and separate nations cannot combine attacking forces");
        require(s.units.at(id).zone == zone && origins.contains(id),
                "Attacker is not at battle zone or lacks its approach origin");
    }
    for (auto &[id, b] : s.battles)
        if (b.zone == zone && b.attacker == attacker && !marked(b.flags, "attrition") &&
            !marked(b.flags, "naval_battle") && !marked(b.flags, "amphibious_preparation") &&
            !marked(b.flags, "finished")) {
            auto o = object(b, "origins");
            auto landEntries = array(b, "land_entry_origins");
            for (const auto &unit : units) {
                require(s.units.at(unit).zone == zone, "Attacker is not at battle zone");
                if (std::find(b.attackers.begin(), b.attackers.end(), unit) == b.attackers.end())
                    b.attackers.push_back(unit);
                o[unit] = V(origins.at(unit));
                if (ground(s, s.units.at(unit)) && !airborne(s.units.at(unit)) &&
                    !amphibious(s.units.at(unit))) landEntries.emplace_back(origins.at(unit));
            }
            put(b, "origins", V(o));
            put(b, "land_entry_origins", V(std::move(landEntries)));
            eliminateUnsupportedRockets(s,b);
            return id;
        }
    BattleState b;
    b.id = "land_battle_" + std::to_string(++s.flags["land_battle_sequence"]);
    b.zone = zone;
    b.attacker = attacker;
    b.stage = "awaiting_combat_rules";
    b.attackers = units;
    auto owner = s.territories.at(zone).possessor;
    b.defender = owner.value_or(attacker);
    if (!owner)
        b.flags["uncontested"] = 1;
    O o;
    A landEntries;
    for (const auto &id : units) {
        const auto &u = s.units.at(id);
        require(u.zone == zone, "Attacker is not at battle zone");
        require(u.owner == attacker, "Separate nations cannot combine attacking forces");
        o[id] = V(origins.at(id));
        if (ground(s, u) && !airborne(u) && !amphibious(u)) landEntries.emplace_back(origins.at(id));
        if (airborne(u))
            b.flags["airborne_assault"] = 1;
        if (amphibious(u))
            b.flags["amphibious_assault"] = 1;
    }
    for (const auto &[id, u] : s.units)
        if (u.zone == zone && !u.carriedBy && (ground(s, u) || aircraft(s, u)) &&
            std::find(units.begin(), units.end(), id) == units.end() &&
            opposing(s, attacker, u.owner))
            b.defenders.push_back(id);
    if (b.defender == attacker && !b.defenders.empty())
        b.defender = s.units.at(b.defenders.front()).owner;
    put(b, "origins", V(o));
    put(b, "land_entry_origins", V(std::move(landEntries)));
    put(b, "round", num(1));
    put(b, "attack_pairs", V(O{}));
    put(b, "defense_pairs", V(O{}));
    put(b, "grounded", V(O{}));
    auto id = b.id;
    s.battles.emplace(id, std::move(b));
    s.battleOrder.push_back(id);
    eliminateUnsupportedRockets(s,s.battles.at(id));
    return id;
}
Id registerAttritionBattle(State &s, const Id &zone, const Id &attacker, const std::vector<Id> &units) {
    require(!units.empty(), "Attrition attack has no artillery");
    std::map<Id, Id> origins;
    for (const auto &id : units) {
        auto &u = s.units.at(id);
        require(u.owner == attacker &&
                    (u.type == "advanced_artillery" || u.type == "advanced_self_propelled_artillery" ||
                     u.type == "katyusha_rocket_artillery"),
                "Unit cannot make an attrition attack");
        require(u.route.empty() && s.turnStart.units.contains(id) &&
                    s.turnStart.units.at(id).second == u.zone && passableLandBorder(s, u.zone, zone),
                "Attrition artillery must have remained adjacent since turn start");
        require(!u.commitments.contains("combat_move") && !u.commitments.contains("combat") &&
                    !u.commitments.contains("attrition"),
                "Artillery already committed");
        origins[id] = u.zone;
        u.commitments.insert("attrition");
        u.movementRemaining = 0;
    }
    BattleState b;
    b.id = "attrition_battle_" + std::to_string(++s.flags["land_battle_sequence"]);
    b.zone = zone;
    b.attacker = attacker;
    b.defender = s.territories.at(zone).possessor.value_or(attacker);
    b.attackers = units;
    b.stage = "awaiting_combat_rules";
    b.flags["attrition"] = 1;
    for (const auto &[id, u] : s.units)
        if (u.zone == zone && opposing(s, attacker, u.owner) && ground(s, u))
            b.defenders.push_back(id);
    O o;
    for (const auto &[id, from] : origins)
        o[id] = V(from);
    put(b, "origins", V(o));
    put(b, "round", num(1));
    auto id = b.id;
    s.battles.emplace(id, std::move(b));
    s.battleOrder.push_back(id);
    return id;
}
void beginLandBattle(State &s, const Id &id) {
    const auto& pending = s.battles.at(id);
    require(!pendingAmphibiousPreparation(s, pending),
            "Resolve the same nation's amphibious preparation before its combined land battle");
    require((s.clock.phase == Phase::Combat || marked(pending.flags, "chinese_truce_termination")) &&
                !s.chance && s.decisions.empty(),
            "Cannot begin land battle now");
    auto &b = s.battles.at(id);
    require(b.stage == "awaiting_combat_rules", "Battle has already begun");
    for (const auto &[other, x] : s.battles)
        if (other != id && !marked(x.flags, "finished") && x.stage != "awaiting_combat_rules" &&
            x.stage != "air_declared" && x.stage != "naval_declared" && x.stage != "amphibious_declared")
            throw std::runtime_error("Another battle is in progress");
    if (marked(b.flags, "attrition")) {
        setStage(b, "attrition_fire");
        advance(s, b);
        return;
    }
    preparePortLandDefence(s, id);
    if (b.attacker == "japan" && marked(s.nations.at("japan").turnFlags, "surprise_attack_zone:" + b.zone) &&
        !marked(s.nations.at("japan").turnFlags, "surprise_attack_used")) {
        b.flags["japanese_surprise_attack"] = 1;
        s.nations.at("japan").turnFlags["surprise_attack_used"] = 1;
    }
    setStage(b, "awaiting_air_defence");
    beginAirDefence(s, id);
    advance(s, b);
}
std::set<Id> landRetreatOrigins(const State &s, const BattleState &b) {
    std::set<Id> out;
    for (const auto& from : array(b, "land_entry_origins")) {
        const auto zone = from.asString();
        if (!s.territories.contains(zone) || !passableLandBorder(s, b.zone, zone)) continue;
        const auto owner = s.territories.at(zone).possessor;
        if (owner && politicallyFriendly(s, b.attacker, *owner)) out.insert(zone);
    }
    return out;
}
std::vector<Id> blitzEligible(const State &s, const BattleState &b) {
    std::vector<Id> out;
    if (s.clock.phase != Phase::Combat || b.attacker != s.currentNation()) return out;
    if (integer(b, "round", 1) > 2 || city(s, b.zone) || marked(b.flags, "amphibious_assault") ||
        marked(b.flags, "attrition"))
        return out;
    auto t = terrain(node(s, b.zone).find("terrain"));
    for (const auto &x :
         {"mountain", "mountains", "desert", "jungle", "marsh", "tundra", "ice", "tundra/ice"})
        if (t.contains(x))
            return out;
    for (const auto &id : living(s, b, true)) {
        const auto &u = s.units.at(id);
        if (!u.movementRemaining || *u.movementRemaining < 1 ||
            marked(u.turnFlags, "crossed_enemy_fortification") || airborne(u) || amphibious(u))
            continue;
        if (u.type == "light_armor" || u.type == "medium_armor" || u.type == "heavy_armor" ||
            u.type == "t34" || u.type == "tiger_i" || u.type == "panzergrenadier")
            out.push_back(id);
    }
    return out;
}

LandCombatRules::LandCombatRules(std::shared_ptr<const Rules> next) : gameplay_(std::move(next)) {}
Id LandCombatRules::id() const {
    return "gw36_v43_m7_land_combat" + (gameplay_ ? "+" + gameplay_->id() : "");
}
std::vector<Action> LandCombatRules::actions(const State &s) const {
    auto out = gameplay_ ? gameplay_->actions(s) : std::vector<Action>{};
    if (s.chance || !s.decisions.empty())
        return out;
    if (s.currentNation() == "japan" && s.clock.phase == Phase::CombatMovement &&
        marked(s.nations.at("japan").turnFlags, "surprise_attack_available")) {
        bool selected = false;
        for (const auto &[key, value] : s.nations.at("japan").turnFlags)
            if (value && key.rfind("surprise_attack_zone:", 0) == 0)
                selected = true;
        if (!selected)
            for (const auto &[zone, t] : s.territories)
                if (t.possessor &&
                    marked(s.nations.at("japan").turnFlags, "surprise_attack_target:" + *t.possessor))
                    out.push_back(action(s, "japan", "land_select_surprise_zone", {{"zone", V(zone)}}));
    }
    if (s.clock.phase == Phase::CombatMovement) {
        for (const auto &[id, u] : s.units)
            if (movementController(s, u.owner) &&
                (u.type == "advanced_artillery" || u.type == "advanced_self_propelled_artillery") &&
                u.route.empty() && !u.commitments.contains("attrition") &&
                !u.commitments.contains("combat") && s.turnStart.units.contains(id))
                for (const auto &e : node(s, u.zone).require("neighbors").asArray()) {
                    auto zone = e.require("neighbor_id").asString();
                    if (s.territories.contains(zone) && s.territories.at(zone).possessor &&
                        opposing(s, u.owner, *s.territories.at(zone).possessor) &&
                        passableLandBorder(s, u.zone, zone))
                        out.push_back(action(s, s.currentNation(), "land_declare_attrition",
                                             {{"unit", V(id)}, {"zone", V(zone)}}));
                }
    }
    const bool immediate = marked(s.flags, "immediate_land_battles");
    if (s.clock.phase != Phase::Combat && !immediate)
        return out;
    for (const auto &[id, b] : s.battles)
        if (!marked(b.flags, "air_mission") && !marked(b.flags, "naval_battle") &&
            !marked(b.flags, "amphibious_preparation") && marked(b.flags, "finished"))
            out.push_back(action(s, s.currentNation(), "land_progress_battle", {{"battle", V(id)}}));
    bool active = false;
    for (const auto &[id, b] : s.battles)
        if (!marked(b.flags, "finished") && b.stage != "awaiting_combat_rules" &&
            b.stage != "air_declared" && b.stage != "naval_declared" &&
            b.stage != "amphibious_declared") {
            active = true;
            const auto *ready = b.data.find("air_defence_ready");
            if (!marked(b.flags, "air_mission") && !marked(b.flags, "naval_battle") &&
                !marked(b.flags, "amphibious_preparation") &&
                (b.stage != "awaiting_air_defence" || (ready && ready->asBool())))
                out.push_back(action(s, s.currentNation(), "land_progress_battle", {{"battle", V(id)}}));
        }
    if (!active)
        for (const auto &id : s.battleOrder)
            if (s.battles.contains(id) && s.battles.at(id).stage == "awaiting_combat_rules" &&
                !pendingAmphibiousPreparation(s, s.battles.at(id)) &&
                (!immediate || marked(s.battles.at(id).flags, "chinese_truce_termination"))) {
                out.push_back(action(s, s.currentNation(), "land_begin_battle", {{"battle", V(id)}}));
                // Mandatory shared-zone reactions use their stable queued
                // order; the active third-party player gets no ordering choice.
                if (immediate) break;
            }

    return out;
}
std::vector<Action> LandCombatRules::interrupts(const State &s) const {
    return gameplay_ ? gameplay_->interrupts(s) : std::vector<Action>{};
}
bool LandCombatRules::phaseComplete(const State &s) const {
    if (s.clock.phase == Phase::Combat)
        for (const auto &[id, b] : s.battles)
            if (!marked(b.flags, "finished"))
                return false;
    return !gameplay_ || gameplay_->phaseComplete(s);
}
void LandCombatRules::apply(State &s, const Action &a) const {
    if (a.kind.rfind("land_", 0) != 0) {
        if (gameplay_) {
            gameplay_->apply(s, a);
            return;
        }
        throw std::runtime_error("Unknown land combat action");
    }
    if (a.kind == "land_select_surprise_zone") {
        s.nations.at("japan").turnFlags["surprise_attack_zone:" + a.parameters.require("zone").asString()] =
            1;
        return;
    }
    if (a.kind == "land_declare_attrition") {
        auto id = a.parameters.require("unit").asString();
        registerAttritionBattle(s, a.parameters.require("zone").asString(), s.units.at(id).owner, {id});
        return;
    }
    const auto id = a.parameters.require("battle").asString();
    auto &b = s.battles.at(id);
    if (a.kind == "land_begin_battle") {
        beginLandBattle(s, id);
        return;
    }
    if (a.kind == "land_progress_battle") {
        if (marked(b.flags, "finished")) {
            require(!s.chance && s.decisions.empty(), "Air reactions must finish before battle cleanup");
            s.battles.erase(id);
            s.battleOrder.erase(std::remove(s.battleOrder.begin(), s.battleOrder.end(), id),
                                s.battleOrder.end());
            refreshImmediateBattles(s);
        } else
            advance(s, b);
        return;
    }
    if (a.kind == "land_pair_blitz") {
        release(s, a);
        const auto tank = a.parameters.require("armor").asString(),
                   unit = a.parameters.require("unit").asString();
        auto pairs = object(b, "blitz_pairs");
        A list = pairs.contains(tank) ? pairs.at(tank).asArray() : A{};
        list.emplace_back(unit);
        pairs[tank] = V(list);
        put(b, "blitz_pairs", V(pairs));
        s.units.at(unit).turnFlags["blitz_eligible"] = 1;
        s.units.at(unit).commitments.insert("blitz_with:" + tank);
        finishPostBattle(s, b);
        return;
    }
    if (a.kind == "land_finish_blitz_pairing") {
        release(s, a);
        b.flags["blitz_pairing_done"] = 1;
        finishPostBattle(s, b);
        return;
    }
    if (a.kind == "land_pair_artillery") {
        release(s, a);
        auto pairs = object(b, a.parameters.require("attacking").asBool() ? "attack_pairs" : "defense_pairs");
        pairs[a.parameters.require("artillery").asString()] = a.parameters.require("companion");
        put(b, a.parameters.require("attacking").asBool() ? "attack_pairs" : "defense_pairs", V(pairs));
        requestPairing(s, b, a.parameters.require("attacking").asBool(), string(b, "pair_after"));
        return;
    }
    if (a.kind == "land_take_casualty") {
        release(s, a);
        const auto unit = a.parameters.require("unit").asString();
        bool targeted = a.parameters.require("targeted").asBool();
        auto hits=array(b,"hits");
        const auto hitIndex=integer(b,"hit_index");
        const auto &currentHit=hits.at(static_cast<std::size_t>(hitIndex));
        const bool extraHit=currentHit.find("amphibious_extra") &&
                            currentHit.require("amphibious_extra").asBool();
        const bool doubleLoss=currentHit.require("victim_attacker").asBool() && !extraHit &&
                              doubleAmphibiousCasualty(s,b,unit);
        if (!targeted && std::find(b.defenders.begin(), b.defenders.end(), unit) != b.defenders.end()) {
            bool other = false;
            for (const auto &d : living(s, b, false))
                if (politicalPlayer(s, s.units.at(d).owner) != politicalPlayer(s, b.defender))
                    other = true;
            if (other && !marked(b.flags, "casualty_dispute_decided")) {
                put(b, "casualty_proposal", V(unit));
                put(b, "casualty_consents", V(O{}));
                chooseHit(s, b);
                return;
            }
        }
        const auto phase = string(b, "rolling_phase");
        const bool linkedAirborne = marked(b.flags, "airborne_assault") && s.units.contains(unit) &&
                                    !s.units.at(unit).cargo.empty() &&
                                    (phase == "first_strike" || phase == "air_fire" ||
                                     phase == "city_airborne_aaa");
        if (linkedAirborne)
            eraseUnit(s, unit);
        else
            markDead(b, unit);
        if (doubleLoss) {
            auto extra=currentHit.asObject();
            extra["targeted"]=V(false); extra["target_classes"]=V(A{});
            extra["amphibious_extra"]=V(true);
            hits.insert(hits.begin()+hitIndex+1,V(std::move(extra)));
            put(b,"hits",V(std::move(hits)));
        }
        b.flags.erase("casualty_dispute_decided");
        put(b, "hit_index", num(integer(b, "hit_index") + 1));
        chooseHit(s, b);
        return;
    }
    if (a.kind == "land_casualty_accept") {
        release(s, a);
        auto checked = object(b, "casualty_consents");
        checked[a.player] = V(true);
        put(b, "casualty_consents", V(checked));
        chooseHit(s, b);
        return;
    }
    if (a.kind == "land_casualty_dispute") {
        release(s, a);
        put(b, "casualty_proposal", V(std::string{}));
        put(b, "casualty_consents", V(O{}));
        std::map<Id, Id> players;
        for (const auto &d : living(s, b, false)) {
            const auto &n = s.units.at(d).owner;
            players[politicalPlayer(s, n)] = n;
        }
        A nations;
        ChanceRequest c;
        c.id = b.id + "_casualty_dispute";
        c.purpose = "land_casualty_dispute";
        c.continuation = b.id;
        c.nation = b.defender;
        for (const auto &[player, nation] : players) {
            nations.emplace_back(nation);
            c.dice.push_back(DieSpec{12, 0, {}, 0});
        }
        put(b, "disputing_nations", V(nations));
        s.chance = std::move(c);
        return;
    }
    if (a.kind == "land_continue_fighting") {
        release(s, a);
        put(b, "round", num(integer(b, "round", 1) + 1));
        put(b, "after_pairing", V(std::string("attacker_fire")));
        put(b, "attack_pairs", V(O{}));
        put(b, "defense_pairs", V(O{}));
        setStage(b, "pair_attack");
        advance(s, b);
        return;
    }
    if (a.kind == "land_retreat_begin") {
        release(s, a);
        setStage(b, "retreat_assign");
        assignRetreat(s, b);
        return;
    }
    if (a.kind == "land_retreat_unit") {
        release(s, a);
        retreatUnit(s, a.parameters.require("unit").asString(), a.parameters.require("zone").asString());
        assignRetreat(s, b);
        return;
    }
    throw std::runtime_error("Unsupported land battle action: " + a.kind);
}
void LandCombatRules::applyChance(State &s, const ChanceRequest &request,
                                  const ChanceOutcome &outcome) const {
    if (request.purpose.rfind("land_", 0) != 0) {
        if (gameplay_) {
            gameplay_->applyChance(s, request, outcome);
            return;
        }
        throw std::runtime_error("Unknown land combat chance");
    }
    auto &b = s.battles.at(request.continuation);
    auto results = effectiveResults(request, outcome);
    if (request.purpose == "land_casualty_dispute") {
        const auto nations = array(b, "disputing_nations");
        int top = *std::max_element(results.begin(), results.end());
        std::vector<std::size_t> tied;
        for (std::size_t i = 0; i < results.size(); ++i)
            if (results[i] == top)
                tied.push_back(i);
        if (tied.size() > 1) {
            ChanceRequest c = request;
            c.dice.resize(tied.size());
            A n;
            for (auto i : tied)
                n.push_back(nations[i]);
            put(b, "disputing_nations", V(n));
            s.chance = c;
            return;
        }
        auto hits = array(b, "hits");
        auto hit = hits.at(static_cast<std::size_t>(integer(b, "hit_index")));
        auto candidates = eligibleHits(s, b, hit);
        std::vector<Action> options;
        auto winner = nations.at(tied.front()).asString();
        for (const auto &unit : candidates)
            options.push_back(action(s, winner, "land_take_casualty",
                                     {{"battle", V(b.id)}, {"unit", V(unit)}, {"targeted", V(false)}}));
        b.flags["casualty_dispute_decided"] = 1;
        decision(s, b, winner, "land_casualty", std::move(options));
        return;
    }
    const auto shots = array(b, "shots");
    require(results.size() == shots.size(), "Land dice mismatch");
    A hits;
    for (std::size_t i = 0; i < shots.size(); ++i) {
        const auto &shot = shots[i];
        const auto unit = shot.require("unit").asString();
        const auto *low = shot.find("low_morale");
        if (low && low->asBool() && results[i] >= 10 && s.units.contains(unit)) {
            if (marked(b.flags, "truce_low_morale_eliminates")) {
                // RB 6.6 uses the attacking die for voluntary shared-zone
                // elimination. The user's campaign ruling extends that result
                // to automatic truce termination, without an extra die.
                eraseUnit(s, unit);
            } else {
                const auto from = approach(b, unit);
                require(s.territories.contains(from) && passableLandBorder(s, b.zone, from) &&
                            s.territories.at(from).possessor &&
                            politicallyFriendly(s, s.units.at(unit).owner,
                                                *s.territories.at(from).possessor),
                        "Unsupported rule state: KMT Low Morale has no legal attack-origin retreat");
                retreatUnit(s, unit, from);
            }
            continue;
        }
        if (results[i] > shot.require("threshold").asInt())
            continue;
        O hit{{"victim_attacker", shot.require("victim_attacker")},
              {"firing_nation", shot.require("nation")},
              {"targeted", V(results[i] <= shot.require("target").asInt())},
              {"target_classes", shot.require("target_classes")}};
        for (const auto &key : {"air_only", "air_priority", "land_only", "eligible"})
            if (const auto *v = shot.find(key))
                hit[key] = *v;
        if (const auto *baseline = shot.find("fort_baseline"))
            if (results[i] > baseline->asInt())
                hit["eligible"] = shot.require("fort_eligible");
        hits.emplace_back(std::move(hit));
    }
    put(b, "hits", V(hits));
    put(b, "hit_index", num(0));
    put(b, "after_hits", V(string(b, "after_roll")));
    setStage(b, "choose_hits");
    chooseHit(s, b);
}
void LandCombatRules::finishTurn(State &s) const {
    if (gameplay_)
        gameplay_->finishTurn(s);
    else
        throw std::runtime_error("Land combat requires an income accounting module");
}
void LandCombatRules::beginTurn(State &s) const {
    if (gameplay_)
        gameplay_->beginTurn(s);
}
void LandCombatRules::finishPhase(State &s) const {
    if (s.clock.phase == Phase::Combat) {
        for (auto i = s.battles.begin(); i != s.battles.end();)
            if (marked(i->second.flags, "finished"))
                i = s.battles.erase(i);
            else
                ++i;
        s.battleOrder.erase(std::remove_if(s.battleOrder.begin(), s.battleOrder.end(),
                                           [&](const Id &id) { return !s.battles.contains(id); }),
                            s.battleOrder.end());
    }
    if (gameplay_)
        gameplay_->finishPhase(s);
    refreshImmediateBattles(s);
}
} // namespace game::campaign
