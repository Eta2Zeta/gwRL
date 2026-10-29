#include "game/air.hpp"
#include "game/catalog.hpp"
#include "game/economy.hpp"
#include "game/land_combat.hpp"
#include "game/naval.hpp"
#include "game/movement.hpp"
#include "game/politics.hpp"
#include "game/position_facts.hpp"
#include <algorithm>
#include <deque>
#include <functional>
#include <numeric>
#include <stdexcept>
namespace game::campaign {
namespace {
using V = json::Value;
using O = V::Object;
using A = V::Array;
// Builds the message only on failure; most messages are literals.
template <class Message> void require(bool ok, const Message &why) {
    if (!ok)
        throw std::runtime_error(why);
}
V num(int x) {
    return V(static_cast<double>(x));
}
bool marked(const std::map<Id, int> &f, const Id &k) {
    auto i = f.find(k);
    return i != f.end() && i->second != 0;
}
int flag(const std::map<Id, int> &f, const Id &k) {
    auto i = f.find(k);
    return i == f.end() ? 0 : i->second;
}
const V &node(const State &s, const Id &z) {
    return mapNode(s, z);
}
bool land(const State &s, const Id &z) {
    return node(s, z).require("type").asString() == "land";
}
bool city(const State &s, const Id &z) {
    auto p = node(s, z).find("is_city");
    return p && p->asBool();
}
bool tech(const State &s, const Id &nation, const Id &id) {
    return flag(s.nations.at(nation).technologyStages, id) == 4;
}
bool has(const State &s, const UnitState &u, const Id &cls) {
    return s.definition->catalog->unit(u.type).classes.contains(cls);
}
bool fighter(const State &s, const UnitState &u) {
    return has(s, u, "fighter") || u.type == "fighter" || u.type == "jet_fighter";
}
bool transport(const UnitState &u) {
    return u.type == "air_transport" || u.type == "heavy_air_transport";
}
bool bomber(const State &s, const UnitState &u) {
    return u.type == "medium_bomber" || has(s, u, "strategic_bomber");
}
bool friendly(const State &s, const Id &n, const Id &owner) {
    return n == owner || politicallyFriendly(s, n, owner);
}
bool hostile(const State &s, const Id &n, const Id &owner) {
    return n != owner && s.nations.at(n).atWarWith.contains(owner);
}
int carrierSlots(const UnitState &u) { return u.type == "medium_bomber" ? 2 : 1; }
Id scrambleSource(const UnitState &u) {
    for (const auto &c : u.commitments)
        if (c.rfind("air_scramble_source:", 0) == 0)
            return c.substr(std::string("air_scramble_source:").size());
    return {};
}
bool carrierEligible(const State &s, const UnitState &u, const UnitState &c) {
    return friendly(s, u.owner, c.owner) && has(s, c, "carrier") &&
        (fighter(s, u) || u.type == "tactical_bomber" ||
         (u.type == "medium_bomber" && c.type == "heavy_fleet_carrier"));
}
int occupiedCarrierSlots(const State &s, const Id &carrier, const std::set<Id> &except = {}) {
    int occupied = 0;
    for (const auto &[id, u] : s.units)
        if (!except.contains(id) && (u.carriedBy == carrier || (!u.carriedBy &&
            ((marked(u.turnFlags, "scrambled") && scrambleSource(u) == carrier) ||
             u.commitments.contains("air_defending_carrier:" + carrier)))))
            occupied += carrierSlots(u);
    return occupied;
}
int patrolRange(const State &s, const UnitState &u) {
    auto ctx = catalogContext(s, u.owner, u.zone);
    for (const auto &[id, f] : s.facilities)
        if (f.zone == u.turnOrigin && f.type == "seaplane_base" && f.damage == 0 &&
            !marked(f.flags, "placed_this_turn") && s.territories.at(f.zone).possessor &&
            friendly(s, u.owner, *s.territories.at(f.zone).possessor) &&
            (*s.territories.at(f.zone).possessor != u.owner ||
             heldSinceNationTurnStart(s, u.owner, f.zone, false)) &&
            inSupply(s, u.owner, f.zone))
            ctx.flags["starts_at_seaplane_base"] = true;
    for (const auto &m : s.definition->catalog->modes(u.type, ctx, u.damage))
        if (m.id == "maritime_air_patrol")
            return m.parameters.require("range").asInt();
    return 0;
}
bool used(const State &s, const UnitState &u) {
    return flag(u.turnFlags, "air_battle_turn") == static_cast<int>(s.clock.playerTurnSerial + 1);
}
void stamp(State &s, UnitState &u) {
    u.turnFlags["air_battle_turn"] = static_cast<int>(s.clock.playerTurnSerial + 1);
}
bool landingChangesState(const State &s, const UnitState &u, const Id &destination) {
    if (marked(u.turnFlags, "air_in_flight") || marked(u.turnFlags, "air_screening_ready"))
        return true;
    if (u.carriedBy == destination)
        return false;
    return destination != u.zone || !land(s, u.zone) || u.carriedBy.has_value();
}
O object(const BattleState &b, const Id &key) {
    auto p = b.data.find(key);
    return p ? p->asObject() : O{};
}
A array(const BattleState &b, const Id &key) {
    auto p = b.data.find(key);
    return p ? p->asArray() : A{};
}
Id str(const BattleState &b, const Id &key, const Id &fallback = "") {
    auto p = b.data.find(key);
    return p ? p->asString() : fallback;
}
void put(BattleState &b, const Id &key, V v) {
    auto o = b.data.asObject();
    o[key] = std::move(v);
    b.data = V(std::move(o));
}
A ids(const std::vector<Id> &v) {
    A a;
    for (const auto &x : v)
        a.emplace_back(x);
    return a;
}
std::vector<Id> readIds(const V &v) {
    std::vector<Id> r;
    for (const auto &x : v.asArray())
        r.push_back(x.asString());
    return r;
}
NeighborIds neighbors(const State &s, const Id &z) {
    return mapNeighbors(s, z);
}
bool adjacent(const State &s, const Id &a, const Id &b) {
    return mapEdge(s, a, b) != nullptr;
}
bool enemyFighter(const State &s, const Id &nation, const Id &z) {
    if (auto *facts = positionFacts(s))
        return facts->zones(PositionFacts::Fact::HostileFighterZones, nation, [&] {
            std::set<Id> zones;
            for (const auto &[id, u] : s.units)
                if (hostile(s, nation, u.owner) && fighter(s, u))
                    zones.insert(u.zone);
            return zones;
        }).contains(z);
    for (const auto &[id, u] : s.units)
        if (u.zone == z && hostile(s, nation, u.owner) && fighter(s, u))
            return true;
    return false;
}
std::map<Id, std::vector<Id>> flightPaths(const State &s, const Id &id, bool combat, int limit = -1,
                                      bool rocketRange = false) {
    const auto &u = s.units.at(id);
    int range = limit < 0 ? u.movementRemaining.value_or(0) : limit;
    std::map<Id, std::vector<Id>> paths{{u.zone, {u.zone}}};
    std::deque<Id> q{u.zone};
    while (!q.empty()) {
        auto z = q.front();
        q.pop_front();
        const auto p = paths.at(z);
        if (static_cast<int>(p.size()) - 1 >= range)
            continue;
        if (!rocketRange && z != u.zone && enemyFighter(s, u.owner, z))
            continue;
        for (const auto &to : neighbors(s, z)) {
            bool access = aircraftFlightAccess(s, u.owner, to, combat);
            if (rocketRange && land(s, to)) {
                const auto owner = s.territories.at(to).possessor;
                access = owner && (friendly(s, u.owner, *owner) || hostile(s, u.owner, *owner));
            }
            if (paths.contains(to) || !access)
                continue;
            auto path = p;
            path.push_back(to);
            paths[to] = path;
            q.push_back(to);
        }
    }
    return paths;
}
Action action(const State &s, const Id &nation, const Id &kind, O p = {}) {
    Action a;
    a.kind = kind;
    a.nation = nation;
    a.player = politicalPlayer(s, nation);
    a.parameters = V(std::move(p));
    a.id = kind + ":" + contentDigest(canonicalJson(a.parameters));
    return a;
}
void decision(State &s, BattleState &b, const Id &nation, const Id &kind, std::vector<Action> choices) {
    require(!choices.empty(), "Empty air decision");
    Decision d;
    d.id = "air_decision_" + std::to_string(++s.flags["air_decision_sequence"]);
    d.kind = kind;
    d.nation = nation;
    d.reaction = nation != s.currentNation();
    d.continuation = b.id;
    for (auto &a : choices) {
        a.decision = d.id;
        a.id = d.id + ":" + a.id;
    }
    d.options = std::move(choices);
    s.decisions.push_back(std::move(d));
}
void release(State &s, const Action &a) {
    require(!s.decisions.empty() && s.decisions.back().id == a.decision, "Wrong air decision");
    s.decisions.pop_back();
}
void roll(State &s, BattleState &b, const Id &purpose, const Id &nation, const std::vector<DieSpec> &dice) {
    require(!s.chance && !dice.empty(), "Invalid air roll");
    s.chance = ChanceRequest{"air_roll_" + std::to_string(++s.flags["air_roll_sequence"]), purpose, nation,
                             b.id, dice};
}
void moveFlight(State &s, const Id &id, const std::vector<Id> &path) {
    auto &u = s.units.at(id);
    if (u.carriedBy) {
        const auto parent = *u.carriedBy;
        require(has(s, s.units.at(parent), "carrier"), "Aircraft is transport cargo");
        detachCargo(s, parent, id, u.zone);
        u.turnFlags["launched_from_carrier"] = 1;
    }
    for (std::size_t n = 1; n < path.size(); ++n)
        u.route.push_back(path[n]);
    u.zone = path.back();
    *u.movementRemaining -= static_cast<int>(path.size()) - 1;
    u.turnFlags["air_in_flight"] = 1;
    for (const auto &cargo : u.cargo)
        s.units.at(cargo).zone = u.zone;
}
void eraseAirUnit(State &s, const Id &id) {
    if (!s.units.contains(id))
        return;
    std::set<Id> dead{id};
    const auto cargo = s.units.at(id).cargo;
    dead.insert(cargo.begin(), cargo.end());
    removePoliticalUnits(s, dead);
    for (auto &[bid, b] : s.battles) {
        for (auto *side : {&b.attackers, &b.defenders})
            side->erase(
                std::remove_if(side->begin(), side->end(), [&](const Id &x) { return dead.contains(x); }),
                side->end());
    }
}
void eraseBattle(State &s, const Id &id) {
    s.battleOrder.erase(std::remove(s.battleOrder.begin(), s.battleOrder.end(), id), s.battleOrder.end());
    s.battles.erase(id);
}
void queueLandings(State &s, BattleState &b);
void continueDefence(State &s, BattleState &b);
void continueBombing(State &s, BattleState &b);
void queueAirCasualty(State &s, BattleState &b);
bool preservesLandingPlan(const State &s, const Id &id, const Id &destination) {
    if (!airLandingPlanAvailable(s)) return true;
    State after = s.clone();
    auto &u = after.units.at(id);
    u.turnFlags.erase("air_in_flight");u.gameFlags.erase("on_map");
    if (u.carriedBy) detachCargo(after, *u.carriedBy, id, u.zone);
    if (after.units.contains(destination)) attachCargo(after, destination, id);
    return airLandingPlanAvailable(after);
}
std::vector<Id> liveAircraft(const State &s, const std::vector<Id> &units) {
    std::vector<Id> out;
    for (const auto &id : units)
        if (s.units.contains(id) && isAircraft(s, s.units.at(id)))
            out.push_back(id);
    return out;
}
std::vector<Id> scrambleSources(const State &s, const Id &unit, const Id &target, bool intercept) {
    const auto &u = s.units.at(unit);
    std::vector<Id> r;
    const bool seaplane = u.type == "seaplane" && !intercept && !land(s, target);
    if ((!fighter(s, u) && !seaplane) || used(s, u) || !adjacent(s, u.zone, target))
        return r;
    for (const auto &[id, f] : s.facilities)
        if (f.zone == u.zone && f.type == (seaplane ? "seaplane_base" : "airbase") && f.damage == 0 &&
            !marked(f.flags, "placed_this_turn") && s.territories.at(f.zone).possessor &&
            friendly(s, u.owner, *s.territories.at(f.zone).possessor) &&
            (*s.territories.at(f.zone).possessor != u.owner ||
             heldSinceNationTurnStart(s, u.owner, f.zone, false))) {
            const auto owner = *s.territories.at(f.zone).possessor;
            int spent = flag(f.flags, "air_scramble_turn") == static_cast<int>(s.clock.playerTurnSerial + 1)
                            ? flag(f.flags, "air_scramble_used")
                            : 0;
            if (tech(s, owner, "radar") || spent < 3)
                r.push_back(id);
        }
    for (const auto &[id, carrier] : s.units)
        if (!seaplane && carrier.zone == u.zone && carrier.type == "heavy_fleet_carrier" &&
            tech(s, carrier.owner, "radar") && friendly(s, u.owner, carrier.owner) &&
            std::find(carrier.cargo.begin(), carrier.cargo.end(), unit) != carrier.cargo.end())
            r.push_back(id);
    return r;
}
void useScramble(State &s, BattleState &b, const Id &id, const Id &source) {
    auto &u = s.units.at(id);
    auto origins = object(b, "scramble_origins");
    origins[id] = V(u.zone);
    put(b, "scramble_origins", V(origins));
    auto sources = object(b, "scramble_sources");
    sources[id] = V(source);
    put(b, "scramble_sources", V(sources));
    if (s.facilities.contains(source)) {
        auto &f = s.facilities.at(source);
        if (flag(f.flags, "air_scramble_turn") != static_cast<int>(s.clock.playerTurnSerial + 1)) {
            f.flags["air_scramble_turn"] = static_cast<int>(s.clock.playerTurnSerial + 1);
            f.flags["air_scramble_used"] = 0;
        }
        ++f.flags["air_scramble_used"];
    }
    if (u.carriedBy) {
        auto &c = s.units.at(*u.carriedBy).cargo;
        c.erase(std::remove(c.begin(), c.end(), id), c.end());
        u.carriedBy.reset();
    }
    u.commitments.insert("air_scramble_origin:" + u.zone);
    u.commitments.insert("air_scramble_source:" + source);
    u.zone = b.zone;
    u.turnFlags["scrambled"] = 1;
    stamp(s, u);
    u.commitments.insert("air_battle:" + b.id);
    if (std::find(b.defenders.begin(), b.defenders.end(), id) == b.defenders.end())
        b.defenders.push_back(id);
}
void continueDefence(State &s, BattleState &b) {
    auto done = object(b, "air_defence_choices");
    const bool surprise = marked(b.flags, "japanese_surprise_attack");
    if (!surprise)
        for (const auto &[id, u] : s.units)
            if (hostile(s, b.attacker, u.owner) && friendly(s, u.owner, b.defender) &&
                (fighter(s, u) || (u.type == "seaplane" && !land(s, b.zone))) &&
                !done.contains("scramble:" + id)) {
                auto sources = scrambleSources(s, id, b.zone, false);
                if (sources.empty())
                    continue;
                std::vector<Action> options{
                    action(s, u.owner, "air_decline_scramble", {{"battle", V(b.id)}, {"unit", V(id)}})};
                for (const auto &source : sources)
                    options.push_back(action(s, u.owner, "air_scramble",
                                             {{"battle", V(b.id)}, {"unit", V(id)}, {"source", V(source)}}));
                decision(s, b, u.owner, "air_scramble", std::move(options));
                return;
            }
    for (const auto &id : b.defenders)
        if (s.units.contains(id) && isAircraft(s, s.units.at(id)) && !done.contains("ground:" + id)) {
            const auto &u = s.units.at(id);
            if (marked(u.turnFlags, "scrambled"))
                continue;
            if (used(s, u) && !u.commitments.contains("air_battle:" + b.id)) {
                if (u.zone == b.zone) {
                    auto grounded = object(b, "grounded");
                    grounded[id] = V(true);
                    put(b, "grounded", V(grounded));
                }
                continue;
            }
            std::vector<Action> options{
                action(s, u.owner, "air_ground", {{"battle", V(b.id)}, {"unit", V(id)}})};
            if (u.type != "seaplane" || !land(s, b.zone))
                options.push_back(action(s, u.owner, "air_defend", {{"battle", V(b.id)}, {"unit", V(id)}}));
            decision(s, b, u.owner, "air_ground_or_defend", std::move(options));
            return;
        }
    put(b, "air_defence_ready", V(true));
}
void queueLandings(State &s, BattleState &b) {
    auto pending = array(b, "air_landing_queue");
    while (!pending.empty()) {
        const Id id = pending.front().asString();
        pending.erase(pending.begin());
        put(b, "air_landing_queue", V(pending));
        if (!s.units.contains(id) || !marked(s.units.at(id).turnFlags, "air_in_flight"))
            continue;
        const auto owner = s.units.at(id).owner;
        auto spots = airLandingSpots(s, id);
        std::erase_if(spots, [&](const Id &destination) { return !preservesLandingPlan(s, id, destination); });
        if (spots.empty()) {
            eraseAirUnit(s, id);
            continue;
        }
        std::vector<Action> opts;
        for (const auto &z : spots)
            opts.push_back(
                action(s, owner, "air_land", {{"battle", V(b.id)}, {"unit", V(id)}, {"destination", V(z)}}));
        decision(s, b, owner, "air_landing", std::move(opts));
        return;
    }
    if (str(b, "air_after_landing") == "carpet_round_end")
        put(b, "carpet_return_done", V(true));
    else if (str(b, "air_after_landing") == "drop")
        put(b, "airborne_drop_ready", V(true));
    else
        put(b, "air_landing_done", V(true));
    if (marked(b.flags, "air_mission") && str(b, "air_stage") == "landing") {
        const auto id = b.id;
        eraseBattle(s, id);
    }
}
void queueAirCasualty(State &s, BattleState &b) {
    auto hits = array(b, "air_hit_queue");
    while (!hits.empty()) {
        const auto hit = hits.front();
        const auto target = hit.require("target").asString();
        const bool defender = target == "defender";
        auto candidates = liveAircraft(s, defender ? b.defenders : b.attackers);
        if (candidates.empty()) {
            hits.erase(hits.begin());
            put(b, "air_hit_queue", V(hits));
            continue;
        }
        std::vector<Action> options;
        Id chooser = defender ? b.defender : b.attacker;
        for (const auto &id : candidates) {
            if (politicalPlayer(s, s.units.at(id).owner) != politicalPlayer(s, chooser))
                continue;
            options.push_back(
                action(s, chooser, "air_choose_casualty", {{"battle", V(b.id)}, {"unit", V(id)}}));
        }
        if (options.empty()) {
            chooser = s.units.at(candidates.front()).owner;
            for (const auto &id : candidates)
                if (s.units.at(id).owner == chooser)
                    options.push_back(
                        action(s, chooser, "air_choose_casualty", {{"battle", V(b.id)}, {"unit", V(id)}}));
        }
        decision(s, b, chooser, "air_casualty", std::move(options));
        return;
    }
    auto dead = array(b, "air_pending_dead");
    for (const auto &x : dead)
        eraseAirUnit(s, x.asString());
    put(b, "air_pending_dead", V(A{}));
    continueBombing(s, b);
}
int interceptionValue(const State &s, const UnitState &u) {
    for (const auto &mode :
         s.definition->catalog->modes(u.type, catalogContext(s, u.owner, u.zone), u.damage))
        if (mode.id == "interception")
            return mode.threshold.value_or(0);
    return 0;
}
int damageDice(const State &s, const UnitState &u) {
    for (const auto &mode :
         s.definition->catalog->modes(u.type, catalogContext(s, u.owner, u.zone), u.damage))
        if (mode.id == "strategic_bombing")
            return mode.dice;
    return 0;
}
int aaThreshold(const State &s, const BattleState &b) {
    return tech(s, b.attacker, "heavy_strategic_bombers") ? 2 : 3;
}
void continueBombing(State &s, BattleState &b) {
    auto stage = str(b, "air_stage");
    if (stage == "interception_choices") {
        auto done = object(b, "air_interception_choices");
        for (const auto &[id, u] : s.units)
            if (hostile(s, b.attacker, u.owner) && friendly(s, u.owner, b.defender) && fighter(s, u) &&
                !used(s, u) && !done.contains(id)) {
                bool local = u.zone == b.zone;
                auto sources = marked(b.flags, "japanese_surprise_attack") ? std::vector<Id>{} :
                    scrambleSources(s, id, b.zone, true);
                if (!local && sources.empty())
                    continue;
                std::vector<Action> opts{
                    action(s, u.owner, "air_decline_intercept", {{"battle", V(b.id)}, {"unit", V(id)}})};
                if (local)
                    opts.push_back(
                        action(s, u.owner, "air_intercept",
                               {{"battle", V(b.id)}, {"unit", V(id)}, {"source", V(std::string("local"))}}));
                for (const auto &f : sources)
                    opts.push_back(action(s, u.owner, "air_intercept",
                                          {{"battle", V(b.id)}, {"unit", V(id)}, {"source", V(f)}}));
                decision(s, b, u.owner, "air_interception", std::move(opts));
                return;
            }
        put(b, "air_stage", V(std::string("interception_roll")));
        continueBombing(s, b);
        return;
    }
    if (stage == "interception_roll" || stage == "interception_return") {
        std::vector<DieSpec> dice;
        A shots;
        const bool surprise = marked(b.flags, "japanese_surprise_attack");
        if (!b.defenders.empty()) {
            for (bool defending : {false, true})
                if (!surprise || (stage == "interception_return" ? defending : !defending))
                for (const auto &id : defending ? b.defenders : b.attackers)
                    if (s.units.contains(id)) {
                        int value = interceptionValue(s, s.units.at(id));
                        if (defending && surprise && value > 0) value = std::max(1, value - 1);
                        if (value > 0) {
                            dice.push_back(DieSpec{});
                            shots.emplace_back(
                                O{{"target", V(std::string(defending ? "attacker" : "defender"))},
                                  {"threshold", num(value)}});
                        }
                    }
        }
        put(b, "air_stage", V(std::string(surprise && stage == "interception_roll" ? "interception_return" : "damage")));
        put(b, "air_shots", V(shots));
        if (!dice.empty()) {
            roll(s, b, "air_interception_roll", b.attacker, dice);
            return;
        }
        continueBombing(s, b);
        return;
    }
    if (stage == "rocket_aa") {
        put(b, "air_stage", V(std::string("damage")));
        if (tech(s, b.defender, "radar") && str(b, "target_kind") != "rail" &&
            str(b, "target_kind") != "construction") {
            roll(s, b, "air_rocket_aa", b.defender, {DieSpec{}});
            return;
        }
        continueBombing(s, b);
        return;
    }
    if (stage == "damage") {
        if (marked(b.flags, "artillery_city_bombing")) {
            put(b, "air_stage", V(std::string("artillery_done")));
            roll(s, b, "air_bomb_damage", b.attacker, {DieSpec{6, 0, {}, 0}});
            return;
        }
        if (marked(b.flags, "rocket_mission")) {
            put(b, "air_stage", V(std::string("rocket_consumed")));
            if (!b.attackers.empty()) {
                roll(s, b, "air_bomb_damage", b.attacker, {DieSpec{6, 0, {}, 0}});
                return;
            }
            continueBombing(s, b);
            return;
        }
        std::vector<DieSpec> dice;
        for (const auto &id : b.attackers)
            if (s.units.contains(id) && bomber(s, s.units.at(id)))
                for (int n = 0; n < damageDice(s, s.units.at(id)); ++n)
                    dice.push_back(DieSpec{6, 0, {}, 0});
        put(b, "air_stage", V(std::string("facility_aa")));
        if (!dice.empty()) {
            roll(s, b, "air_bomb_damage", b.attacker, dice);
            return;
        }
        continueBombing(s, b);
        return;
    }
    if (stage == "rocket_consumed") {
        auto units = b.attackers;
        for (const auto &id : units)
            eraseAirUnit(s, id);
        auto id = b.id;
        eraseBattle(s, id);
        return;
    }
    if (stage == "artillery_done") {
        const auto id = b.id;
        eraseBattle(s, id);
        return;
    }
    if (stage == "facility_aa") {
        put(b, "air_stage", V(std::string("landing")));
        bool fire = str(b, "target_kind") != "rail" && str(b, "target_kind") != "construction";
        if (str(b, "target_kind") == "facility") {
            auto i = s.facilities.find(str(b, "target"));
            if (i == s.facilities.end())
                fire = false;
            else {
                const auto max = s.definition->catalog->facility(i->second.type).maxDamage;
                const auto captured = flag(i->second.flags, "captured_max_damage");
                fire = fire && (captured ? i->second.damage < captured : (!max || i->second.damage < *max));
            }
        }
        std::vector<DieSpec> dice;
        for (const auto &id : b.attackers)
            if (s.units.contains(id) && bomber(s, s.units.at(id)) && fire)
                dice.push_back(DieSpec{});
        if (!dice.empty()) {
            roll(s, b, "air_facility_aa", b.defender, dice);
            return;
        }
        continueBombing(s, b);
        return;
    }
    if (stage == "landing") {
        finishAirCombat(s, b.id);
    }
}
std::vector<Id> targets(const State &s, const Id &zone, const Id &kind) {
    std::vector<Id> r;
    if (kind == "city") {
        if (city(s, zone) && !marked(s.territories.at(zone).flags, "city_destroyed"))
            r.push_back(zone);
    } else if (kind == "facility") {
        for (const auto &[id, f] : s.facilities)
            if (f.zone == zone && f.type != "fortification" && f.type != "coastal_artillery")
                r.push_back(id);
    } else if (kind == "construction") {
        for (const auto &[id, p] : s.construction)
            if (p.site && *p.site == zone && s.definition->catalog->facilities().contains(p.type) &&
                p.type != "fortification")
                r.push_back(id);
    } else if (kind == "rail") {
        for (const auto &[id, r1] : s.rails)
            if (r1.endpointA == zone || r1.endpointB == zone) {
                r.push_back(zone);
                break;
            }
    }
    return r;
}
} // namespace

bool isAircraft(const State &s, const UnitState &u) {
    return has(s, u, "aircraft");
}
FlightResult validateFlight(const State &s, const Id &id, const std::vector<Id> &path, bool combat,
                            bool attackDestination) {
    if (!s.units.contains(id))
        return {false, "Unknown aircraft", 0};
    const auto &u = s.units.at(id);
    if (!isAircraft(s, u) || (u.carriedBy && !has(s, s.units.at(*u.carriedBy), "carrier")) || path.empty() ||
        path.front() != u.zone)
        return {false, "Invalid flight origin or aircraft", 0};
    int cost = static_cast<int>(path.size()) - 1;
    if (!combat && transport(u) && u.cargo.size() > 1)
        return {false, "Noncombat air transport capacity is one land unit", cost};
    if (cost > u.movementRemaining.value_or(0))
        return {false, "Insufficient aircraft movement", cost};
    for (std::size_t i = 1; i < path.size(); ++i) {
        if (!adjacent(s, path[i - 1], path[i]))
            return {false, "Nonadjacent flight", cost};
        if (!aircraftFlightAccess(s, u.owner, path[i], combat))
            return {false, "Overflight permission denied", cost};
        if (enemyFighter(s, u.owner, path[i]) && !(attackDestination && i + 1 == path.size()))
            return {false, "Enemy fighters block overflight", cost};
    }
    return {true, "", cost};
}
bool airLandingAvailable(const State &s, const Id &id, const Id &destination) {
    if (!s.units.contains(id))
        return false;
    const auto &u = s.units.at(id);
    if (s.units.contains(destination)) {
        const auto &c = s.units.at(destination);
        if (!carrierEligible(s, u, c))
            return false;
        const auto cap = catalogStats(s, c.type, c.damage, c.owner, c.zone)
                             .carrierCapacity.value_or(0);
        return occupiedCarrierSlots(s, destination, {id}) + carrierSlots(u) <= cap;
    }
    if (!s.territories.contains(destination) || !land(s, destination))
        return false;
    const auto &t = s.territories.at(destination);
    if (!t.possessor || !friendly(s, u.owner, *t.possessor))
        return false;
    return heldSinceTurnStart(s, u.owner, destination, true);
}
namespace {
bool landingPlan(const State &s, const std::vector<Id> &aircraft) {
    std::set<Id> requested(aircraft.begin(), aircraft.end());
    if (aircraft.empty())
        for (const auto &[id, u] : s.units)
            if (isAircraft(s, u) && !marked(u.turnFlags, "scrambled") &&
                (marked(u.turnFlags, "air_in_flight") || marked(u.gameFlags, "on_map")))
                requested.insert(id);
    // Free deck slots matter only to aircraft without a land spot in reach.
    std::map<Id, int> capacity;
    bool capacityKnown = false;
    const auto decks = [&]() -> std::map<Id, int> & {
        if (!capacityKnown)
            for (const auto &[id, u] : s.units)
                if (has(s, u, "carrier"))
                    capacity[id] = catalogStats(s, u.type, u.damage, u.owner, u.zone).carrierCapacity.value_or(0) -
                        occupiedCarrierSlots(s, id, requested);
        capacityKnown = true;
        return capacity;
    };
    struct Return { int slots; std::vector<Id> carriers; };
    std::vector<Return> returns;
    for (const auto &id : requested) {
        if (!s.units.contains(id) || !isAircraft(s, s.units.at(id))) return false;
        const auto &u = s.units.at(id);
        auto paths = flightPaths(s, id, false, marked(u.gameFlags, "on_map") ? flag(u.gameFlags, "map_range") : -1);
        if (std::any_of(paths.begin(), paths.end(), [&](const auto &entry) {
                return s.territories.contains(entry.first) && airLandingAvailable(s, id, entry.first);
            }))
            continue;
        Return options{carrierSlots(u), {}};
        for (const auto &[carrier, remaining] : decks())
            if (remaining >= options.slots && paths.contains(s.units.at(carrier).zone) &&
                carrierEligible(s, u, s.units.at(carrier))) options.carriers.push_back(carrier);
        if (options.carriers.empty()) return false;
        returns.push_back(std::move(options));
    }
    std::sort(returns.begin(), returns.end(), [](const Return &a, const Return &b) {
        return a.carriers.size() != b.carriers.size() ? a.carriers.size() < b.carriers.size() : a.slots > b.slots;
    });
    std::function<bool(std::size_t)> assign = [&](std::size_t index) {
        if (index == returns.size()) return true;
        const auto &r = returns[index];
        for (const auto &carrier : r.carriers) if (capacity[carrier] >= r.slots) {
            capacity[carrier] -= r.slots;
            if (assign(index + 1)) return true;
            capacity[carrier] += r.slots;
        }
        return false;
    };
    return assign(0);
}
} // namespace
bool airLandingPlanAvailable(const State &s, const std::vector<Id> &aircraft) {
    const PositionScope scope(s);
    if (aircraft.empty())
        if (auto *facts = positionFacts(s))
            return facts->remember(PositionFacts::Fact::AirLandingPlan, {}, {},
                                   [&] { return landingPlan(s, aircraft); });
    return landingPlan(s, aircraft);
}
namespace {
using CarrierLandingBounds = std::map<Id, std::set<Id>>;
std::set<Id> potentialFlightZones(const State& state, const Id& start, int range) {
    // This bound depends only on physical geometry. Permissions and enemy
    // Fighters remain in the actual flight/landing checks below.
    if(state.definition->indexedGeography)
        return state.definition->indexedGeography->withinHops(start,range);
    std::set<Id> zones{start};
    std::deque<std::pair<Id, int>> queue{{start, 0}};
    while (!queue.empty()) {
        const auto [zone, distance] = queue.front(); queue.pop_front();
        if (distance >= range) continue;
        // A necessary-condition bound only. Real flight validation and the
        // final landing planner still enforce permissions and enemy Fighters.
        for (const auto& next : neighbors(state, zone))
            if (zones.insert(next).second) queue.emplace_back(next, distance + 1);
    }
    return zones;
}
CarrierLandingBounds futureCarrierBounds(const State& state) {
    CarrierLandingBounds bounds;
    for (const auto& [id, carrier] : state.units) {
        if (!has(state, carrier, "carrier")) continue;
        auto& destinations = bounds[id];
        destinations.insert(carrier.zone);
        // Optimistic geometry only: allow both the port and Japanese surprise
        // bonuses, and ignore obstacles, ownership and commitments. This is an
        // upper bound used to prove impossibility, never a promised ship route.
        const int base = catalogStats(state, carrier.type, carrier.damage, carrier.owner, carrier.zone)
                             .movement.value_or(0);
        const int range = std::max(carrier.movementRemaining.value_or(0),
                                  base + 2 - flag(carrier.turnFlags, "naval_movement_spent"));
        std::deque<std::pair<Id, int>> queue;
        if (land(state, carrier.zone)) {
            for (const auto& zone : neighbors(state, carrier.zone)) if (!land(state, zone)) {
                if (destinations.insert(zone).second) queue.emplace_back(zone, 0);
            }
        } else queue.emplace_back(carrier.zone, 0);
        while (!queue.empty()) {
            const auto [zone, distance] = queue.front(); queue.pop_front();
            if (distance >= range) continue;
            for (const auto& next : neighbors(state, zone))
                if (!land(state, next) && destinations.insert(next).second)
                    queue.emplace_back(next, distance + 1);
        }
    }
    return bounds;
}
bool flightCanContinue(const State& state, const Id& id, const std::vector<Id>& path,
                       std::optional<CarrierLandingBounds>* cachedBounds = nullptr) {
    // Flight changes one aircraft's origin/range and releases its former deck
    // slot. Reuse immutable board data rather than copying the whole position
    // for every candidate destination in an aircraft's movement menu.
    auto preview = state.units.at(id);
    preview.zone = path.back();
    preview.movementRemaining = preview.movementRemaining.value_or(0) - static_cast<int>(path.size()) + 1;
    preview.carriedBy.reset();
    preview.turnFlags["air_in_flight"] = 1;
    std::optional<CarrierLandingBounds> local;
    auto& bounds = cachedBounds ? *cachedBounds : local;
    const auto reachable = potentialFlightZones(state, preview.zone, preview.movementRemaining.value_or(0));
    auto possibleLanding = [&](const std::set<Id>& zones) {
        for (const auto& zone : zones)
            if (airLandingAvailable(state, id, zone)) return true;
        // A partial flight may precede a carrier's movement or another aircraft
        // vacating its deck. Ignore deck occupancy in this optimistic bound;
        // ending Combat Movement still requires the actual joint assignment.
        if (!bounds) bounds = futureCarrierBounds(state);
        for (const auto& [carrierId, destinations] : *bounds)
            if (carrierEligible(state, preview, state.units.at(carrierId)))
                for (const auto& zone : destinations) if (zones.contains(zone)) return true;
        return false;
    };
    // No patrol can follow this flight; a patrol is a whole combat move of its own.
    return possibleLanding(reachable);
}
} // namespace
std::vector<Id> airLandingSpots(const State &s, const Id &id) {
    const PositionScope scope(s);
    std::vector<Id> out;
    if (!s.units.contains(id))
        return out;
    auto paths = flightPaths(
        s, id, false,
        marked(s.units.at(id).gameFlags, "on_map") ? flag(s.units.at(id).gameFlags, "map_range") : -1);
    for (const auto &[zone, path] : paths)
        if (airLandingAvailable(s, id, zone))
            out.push_back(zone);
    for (const auto &[carrier, c] : s.units)
        if (paths.contains(c.zone) && airLandingAvailable(s, id, carrier))
            out.push_back(carrier);
    return out;
}
std::vector<Id> strandedAircraft(const State &s) {
    std::vector<Id> kept, stranded;
    for (const auto &[id, u] : s.units)
        if (isAircraft(s, u) && !marked(u.turnFlags, "scrambled") &&
            (marked(u.turnFlags, "air_in_flight") || marked(u.gameFlags, "on_map"))) {
            kept.push_back(id);
            if (!airLandingPlanAvailable(s, kept)) {
                kept.pop_back();
                stranded.push_back(id);
            }
        }
    return stranded;
}
void eliminateStrandedAircraft(State &s) {
    for (const auto &id : strandedAircraft(s))
        eraseAirUnit(s, id);
}
void enforcePatrolLandingAvailability(State &s) {
    std::vector<Id> stranded;
    for (const auto &[id, u] : s.units)
        if (isAircraft(s, u) && marked(u.gameFlags, "on_map") && airLandingSpots(s, id).empty())
            stranded.push_back(id);
    for (const auto &id : stranded)
        eraseAirUnit(s, id);
}

void beginAirDefence(State &s, const Id &id) {
    auto &b = s.battles.at(id);
    for (const auto &unit : b.attackers)
        if (s.units.contains(unit) && isAircraft(s, s.units.at(unit))) {
            stamp(s, s.units.at(unit));
            s.units.at(unit).commitments.insert("air_battle:" + b.id);
        }
    if (marked(b.flags, "attrition")) {
        put(b, "air_defence_ready", V(true));
        return;
    }
    continueDefence(s, b);
}
void prepareLandAirborneDrop(State &s, const Id &id) {
    auto &b = s.battles.at(id);
    A queue;
    auto participants = b.attackers;
    for (const auto &x : participants)
        if (s.units.contains(x) && isAircraft(s, s.units.at(x)) && !s.units.at(x).cargo.empty()) {
            auto cargo = s.units.at(x).cargo;
            for (const auto &c : cargo)
                if (s.units.contains(c))
                    detachCargo(s, x, c, b.zone);
            b.attackers.erase(std::remove(b.attackers.begin(), b.attackers.end(), x), b.attackers.end());
            queue.emplace_back(x);
        }
    put(b, "air_landing_queue", V(queue));
    put(b, "air_after_landing", V(std::string("drop")));
    queueLandings(s, b);
}
void finishAirCombat(State &s, const Id &id) {
    auto &b = s.battles.at(id);
    A queue;
    for (const auto &entry : array(b, "air_screening_continuing")) {
        const auto unit = entry.asString();
        if (!s.units.contains(unit)) continue;
        auto &u = s.units.at(unit);
        u.turnFlags.erase("air_screening_wait");
        if (enemyFighter(s, u.owner, b.zone)) {
            stamp(s, u);
            queue.emplace_back(unit);
        } else {
            u.turnFlags["air_screening_ready"] = 1;
        }
    }
    put(b, "air_screening_continuing", V(A{}));
    for (const auto &unit : b.attackers)
        if (s.units.contains(unit) && isAircraft(s, s.units.at(unit)) &&
            !marked(s.units.at(unit).turnFlags, "blitz_eligible"))
            queue.emplace_back(unit);
    for (const auto &[unit, x] : object(b, "exited_aircraft"))
        if (s.units.contains(unit))
            queue.emplace_back(unit);
    put(b, "air_landing_queue", V(queue));
    put(b, "air_after_landing", V(std::string("finish")));
    queueLandings(s, b);
}
void returnCarpetBombers(State &s, const Id &id, const std::vector<Id> &bombers) {
    require(!s.chance && s.decisions.empty(), "Carpet return cannot replace pending decisions");
    auto &battle = s.battles.at(id);
    A queue;
    for (const auto &unit : bombers)
        if (s.units.contains(unit)) {
            require(has(s,s.units.at(unit),"strategic_bomber"), "Carpet return requires a strategic bomber");
            queue.emplace_back(unit);
        }
    put(battle, "air_landing_queue", V(std::move(queue)));
    put(battle, "air_after_landing", V(std::string("carpet_round_end")));
    queueLandings(s, battle);
}
void applyFacilityBombDamage(State &s, const Id &id, int damage) {
    require(damage >= 0, "Negative bombing damage");
    auto &f = s.facilities.at(id);
    const int previousDamage=f.damage;
    const auto &type = s.definition->catalog->facility(f.type);
    require(f.type != "fortification" && f.type != "coastal_artillery", "Unbombable facility");
    auto owner = s.territories.at(f.zone).possessor;
    if (owner && tech(s, *owner, "improved_construction")) {
        int allowance = f.type == "minor_factory"    ? 1
                        : f.type == "medium_factory" ? 3
                        : f.type == "major_factory"  ? 5
                                                     : 0;
        const auto key = "bombing_reduction:" + id;
        auto &ledger = s.nations.at(*owner).turnFlags;
        const auto turnKey = "bombing_reduction_turn:" + id;
        int used =
            flag(ledger, turnKey) == static_cast<int>(s.clock.playerTurnSerial + 1) ? flag(ledger, key) : 0;
        ledger[turnKey] = static_cast<int>(s.clock.playerTurnSerial + 1);
        int reduction = std::min(damage, std::max(0, allowance - used));
        damage -= reduction;
        s.nations.at(*owner).turnFlags[key] = used + reduction;
    }
    int max = flag(f.flags, "captured_max_damage");
    if (!max)
        max = type.maxDamage.value_or(f.damage + damage);
    f.damage = std::min(max, f.damage + damage);
    if (damage)
        s.flags["logistics_damaged_turn:" + id] = static_cast<int>(s.clock.playerTurnSerial + 1);
    if (previousDamage==0 && f.damage>0) queueDamagedPortEvacuation(s,id);
}
void applyCityBombDamage(State &s, const Id &zone, int damage) {
    require(city(s, zone) && damage >= 0, "Invalid city bombing");
    auto &t = s.territories.at(zone);
    if (marked(t.flags, "city_destroyed"))
        return;
    if (t.possessor && tech(s, *t.possessor, "improved_construction")) {
        auto &ledger = s.nations.at(*t.possessor).turnFlags;
        const auto key = "city_bombing_reduction:" + zone, turnKey = "city_bombing_reduction_turn:" + zone;
        int used =
            flag(ledger, turnKey) == static_cast<int>(s.clock.playerTurnSerial + 1) ? flag(ledger, key) : 0;
        int reduction = std::min(damage, std::max(0, 5 - used));
        damage -= reduction;
        ledger[key] = used + reduction;
        ledger[turnKey] = static_cast<int>(s.clock.playerTurnSerial + 1);
    }
    int max = 45;
    for (const auto &[nation, capital] : s.politics.capitals)
        if (capital == zone && s.nations.at(nation).powerStatus == "major")
            max = 60;
    t.flags["city_damage"] = std::min(max, flag(t.flags, "city_damage") + damage);
    t.flags["city_ipp_lost"] = std::max(flag(t.flags, "city_ipp_lost"), t.flags["city_damage"] / 20);
    if (t.flags["city_damage"] == max)
        t.flags["city_destroyed"] = 1;
    refreshIncome(s);
    refreshPoliticalState(s);
}
void applyRailBombDamage(State &s, const Id &zone, const Id &other, int damage) {
    require(damage >= 0, "Negative railroad damage");
    bool found = false;
    int cap = 1;
    for (const auto &edge : node(s, zone).require("neighbors").asArray())
        if (edge.require("neighbor_id").asString() == other) {
            if (const auto *t = edge.find("border_terrain")) {
                auto harsh = [&](const V &v) {
                    return v.isString() && v.asString() != "normal" && v.asString() != "river";
                };
                if (harsh(*t) ||
                    (t->isArray() && std::any_of(t->asArray().begin(), t->asArray().end(), harsh)))
                    cap = 2;
            }
        }
    for (auto &[id, r] : s.rails)
        if ((r.endpointA == zone && r.endpointB == other) || (r.endpointB == zone && r.endpointA == other)) {
            r.damageByEndpoint[zone] = std::min(cap, r.damageByEndpoint[zone] + damage);
            s.flags["logistics_damaged_turn:" + id] = static_cast<int>(s.clock.playerTurnSerial + 1);
            found = true;
        }
    require(found, "No railroad on selected border");
}

AirRules::AirRules(std::shared_ptr<const Rules> gameplay) : gameplay_(std::move(gameplay)) {}
Id AirRules::id() const {
    return "gw36_v43_m8_air" + (gameplay_ ? "+" + gameplay_->id() : "");
}
std::vector<Action> AirRules::interrupts(const State &s) const {
    return gameplay_ ? gameplay_->interrupts(s) : std::vector<Action>{};
}
std::vector<Action> AirRules::actions(const State &s) const {
    auto out = gameplay_ ? gameplay_->actions(s) : std::vector<Action>{};
    std::optional<CarrierLandingBounds> carrierBounds;
    if (s.chance || !s.decisions.empty())
        return out;
    if (s.clock.phase == Phase::Combat) {
        for (const auto &[id,b]:s.battles)
            if (marked(b.flags,"air_waiting_port_evacuation")) {
                out.push_back(action(s,s.currentNation(),"air_resume_bombing",{{"battle",V(id)}}));
                return out;
            }
        bool busy = false;
        for (const auto &[id, b] : s.battles)
            if (b.stage != "awaiting_combat_rules" && b.stage != "air_declared" && b.stage != "naval_declared" &&
                b.stage != "amphibious_declared" &&
                !marked(b.flags, "finished"))
                busy = true;
        if (busy)
            return out;
        for (const auto &[id, b] : s.battles)
            if (marked(b.flags, "air_mission") && b.stage == "air_declared")
                out.push_back(action(s, s.currentNation(), "air_begin_bombing", {{"battle", V(id)}}));
        for (const auto &[id, u] : s.units)
            if (isAircraft(s, u) && movementController(s, u.owner) && marked(u.turnFlags, "blitz_eligible") &&
                (fighter(s, u) || u.type == "tactical_bomber") && u.movementRemaining.value_or(0) > 0) {
                for (const auto &zone : neighbors(s, u.zone))
                    if (s.territories.contains(zone) && blitzPairValid(s, u, u.zone, zone)) {
                        std::vector<Id> path{u.zone, zone};
                        if (!validateFlight(s, id, path, true, true).allowed)
                            continue;
                        State after = s.clone();
                        moveFlight(after, id, path);
                        if (airLandingPlanAvailable(after))
                            out.push_back(action(s, s.currentNation(), "air_blitz",
                                                 {{"unit", V(id)}, {"path", V(ids(path))}}));
                    }
            }
        if (std::none_of(s.units.begin(), s.units.end(), [&](const auto &entry) {
            return movementController(s, entry.second.owner) && marked(entry.second.turnFlags, "air_screening_ready");
        })) return out;
    }
    if (s.clock.phase != Phase::CombatMovement && s.clock.phase != Phase::NonCombatMovement &&
        s.clock.phase != Phase::Combat)
        return out;
    const bool combat = s.clock.phase != Phase::NonCombatMovement;
    if (s.clock.phase == Phase::CombatMovement)
        for (const auto &[id, u] : s.units)
            if ((u.type == "advanced_artillery" || u.type == "advanced_self_propelled_artillery") &&
                movementController(s, u.owner) && !u.carriedBy && u.route.empty() &&
                !marked(u.turnFlags, "placed_this_turn") && !u.commitments.contains("attrition") &&
                !u.commitments.contains("combat_move") && !u.commitments.contains("combat") &&
                s.turnStart.units.contains(id) && s.turnStart.units.at(id).second == u.zone)
                for (const auto &zone : neighbors(s, u.zone))
                    if (s.territories.contains(zone) && passableLandBorder(s, u.zone, zone) &&
                        s.territories.at(zone).possessor && hostile(s, u.owner, *s.territories.at(zone).possessor) &&
                        !targets(s, zone, "city").empty())
                        out.push_back(action(s, s.currentNation(), "air_artillery_city_bomb",
                                             {{"unit", V(id)}, {"zone", V(zone)}}));
    if (!combat)
        for (const auto &[tid, t] : s.units)
            if (transport(t) && t.owner != s.currentNation() &&
                politicallyFriendly(s, s.currentNation(), t.owner))
                for (const auto &[cid, c] : s.units)
                    if (c.owner == s.currentNation() && has(s, c, "land")) {
                        if (c.carriedBy == tid && heldSinceTurnStart(s, c.owner, t.zone, true) &&
                            flag(c.gameFlags, "air_allied_loaded_turn") !=
                                static_cast<int>(s.clock.playerTurnSerial + 1) &&
                            land(s, t.zone) && s.territories.at(t.zone).possessor &&
                            friendly(s, c.owner, *s.territories.at(t.zone).possessor))
                            out.push_back(action(s, s.currentNation(), "air_allied_unload",
                                                 {{"unit", V(tid)}, {"cargo", V(cid)}}));
                        if (!c.carriedBy && c.zone == t.zone && c.route.empty() &&
                            !marked(c.turnFlags, "placed_this_turn") && !marked(c.turnFlags, "air_transport_unloaded") &&
                            !marked(c.turnFlags,"naval_unloaded") && !c.commitments.contains("transport_unloaded") &&
                            !c.commitments.contains("attrition") && !c.commitments.contains("combat") &&
                            !c.commitments.contains("combat_move") && t.cargo.empty() &&
                            (has(s, c, "infantry_class") ||
                             (t.type == "heavy_air_transport" &&
                              (has(s, c, "artillery_class") || c.type == "anti_aircraft_artillery"))))
                            out.push_back(action(s, s.currentNation(), "air_allied_load",
                                                 {{"unit", V(tid)}, {"cargo", V(cid)}}));
                    }
    if (s.clock.phase == Phase::CombatMovement)
        for (const auto &[id, u] : s.units)
            if (u.type == "strategic_rocket" && movementController(s, u.owner) && !u.carriedBy && u.route.empty() &&
                u.commitments.empty() && !marked(u.turnFlags, "placed_this_turn"))
                for (const auto &[zone, path] : flightPaths(s, id, true, 3, true)) {
                    auto owner =
                        s.territories.contains(zone) ? s.territories.at(zone).possessor : std::nullopt;
                    if (!owner || !hostile(s, u.owner, *owner))
                        continue;
                    for (const auto &kind : {"city", "facility", "construction", "rail"})
                        for (const auto &target : targets(s, zone, kind))
                            out.push_back(action(s, s.currentNation(), "air_rocket_attack",
                                                 {{"unit", V(id)},
                                                  {"zone", V(zone)},
                                                  {"kind", V(std::string(kind))},
                                                  {"target", V(target)}}));
                }

    for (const auto &[id, u] : s.units)
        if (isAircraft(s, u) && movementController(s, u.owner) &&
            (!u.carriedBy || has(s, s.units.at(*u.carriedBy), "carrier"))) {
            if (s.clock.phase == Phase::Combat && !marked(u.turnFlags, "air_screening_ready")) continue;
            if (marked(u.turnFlags, "air_screening_wait")) continue;
            if (marked(u.gameFlags, "on_map")) {
                int range = flag(u.gameFlags, "map_range");
                auto paths = flightPaths(s, id, false, range);
                for (const auto &destination : airLandingSpots(s, id)) {
                    auto zone = s.units.contains(destination) ? s.units.at(destination).zone : destination;
                    if (!combat && paths.contains(zone) && preservesLandingPlan(s, id, destination))
                        out.push_back(action(s, s.currentNation(), "air_end_patrol",
                                             {{"unit", V(id)},
                                              {"path", V(ids(paths.at(zone)))},
                                              {"destination", V(destination)}}));
                }
                if (airLandingSpots(s, id).empty())
                    out.push_back(action(s, s.currentNation(), "air_failed_landing", {{"unit", V(id)}}));
                continue;
            }
            if (combat && (used(s, u) || u.commitments.contains("air_combat")) &&
                !marked(u.turnFlags, "air_screening_ready"))
                continue;
            if (!combat && used(s, u) && !marked(u.turnFlags, "air_in_flight"))
                continue;
            // An aircraft still flying without a landing spot is lost. In Combat Movement
            // this ends a flight that relied on a Carrier that never came; a patrol can
            // no longer rescue it, because a patrol cannot follow a flight.
            if (s.clock.phase != Phase::Combat && marked(u.turnFlags, "air_in_flight") &&
                airLandingSpots(s, id).empty())
                out.push_back(action(s, s.currentNation(), "air_failed_landing", {{"unit", V(id)}}));
            if (!combat && transport(u) && u.cargo.size() > 1) {
                if (land(s, u.zone) && heldSinceTurnStart(s, u.owner, u.zone, true))
                    for (const auto &cargo : u.cargo)
                        if (s.units.at(cargo).owner == u.owner)
                            out.push_back(action(s, s.currentNation(), "air_unload",
                                                 {{"unit", V(id)}, {"cargo", V(cargo)}}));
                continue;
            }
            // A patrol is the aircraft's whole combat move, into a sea zone within MAP
            // range of the land zone or Carrier it takes off from (RB 9.3.1).
            const bool takesOff = s.clock.phase == Phase::CombatMovement && u.route.empty() &&
                                  !marked(u.turnFlags, "air_in_flight");
            std::optional<int> patrolLimit;  // Fixed for this aircraft; read only when needed.
            const auto patrolReach = [&] {
                if (!patrolLimit) patrolLimit = patrolRange(s, u);
                return *patrolLimit;
            };
            auto paths = flightPaths(s, id, combat);
            for (const auto &[zone, path] : paths) {
                if (path.size() > 1 && validateFlight(s, id, path, combat, false).allowed &&
                    flightCanContinue(s, id, path, &carrierBounds) &&
                    (!combat || !enemyFighter(s, u.owner, zone)))
                    out.push_back(
                        action(s, s.currentNation(), "air_fly", {{"unit", V(id)}, {"path", V(ids(path))}}));
                if (!combat || marked(u.turnFlags, "air_in_flight")) {
                    if (landingChangesState(s, u, zone) && airLandingAvailable(s, id, zone) &&
                        preservesLandingPlan(s, id, zone))
                        out.push_back(action(s, s.currentNation(), "air_land_noncombat",
                                             {{"unit", V(id)}, {"destination", V(zone)}}));
                    if (!combat)
                        continue;
                }
                if (takesOff && !land(s, zone) && static_cast<int>(path.size()) - 1 <= patrolReach() &&
                    patrolReach() > 0) {
                    State patrol = s.clone();
                    moveFlight(patrol, id, path);
                    patrol.units.at(id).movementRemaining = patrolReach();
                    if (!airLandingSpots(patrol, id).empty())
                        out.push_back(action(
                            s, s.currentNation(), "air_start_patrol",
                            {{"unit", V(id)}, {"path", V(ids(path))}, {"range", num(patrolReach())}}));
                }
                if (combat && enemyFighter(s, u.owner, zone) &&
                    validateFlight(s, id, path, true, true).allowed)
                    for (const auto &[bid, b] : s.battles)
                        if (b.zone == zone && b.attacker == u.owner && !marked(b.flags, "air_mission") &&
                            !marked(b.flags, "finished") &&
                            (b.stage == "awaiting_combat_rules" || b.stage == "naval_declared")) {
                            State after = s.clone();moveFlight(after, id, path);
                            if (airLandingPlanAvailable(after))
                                out.push_back(action(s, s.currentNation(), "air_screen_continue",
                                    {{"unit", V(id)}, {"path", V(ids(path))}, {"battle", V(bid)}}));
                        }
                const auto owner =
                    s.territories.contains(zone) ? s.territories.at(zone).possessor : std::nullopt;
                if (!owner || !hostile(s, u.owner, *owner))
                    continue;
                State after = s.clone();
                moveFlight(after, id, path);
                if (!airLandingPlanAvailable(after))
                    continue;
                if (bomber(s, u)) {
                    for (const auto &kind : {"facility", "construction", "city", "rail"})
                        for (const auto &target : targets(s, zone, kind))
                            out.push_back(action(s, s.currentNation(), "air_bomb",
                                                 {{"unit", V(id)},
                                                  {"path", V(ids(path))},
                                                  {"kind", V(std::string(kind))},
                                                  {"target", V(target)}}));
                }
                if (fighter(s, u))
                    for (const auto &[bid, b] : s.battles)
                        if (b.zone == zone && b.attacker == u.owner && marked(b.flags, "air_mission") &&
                            !marked(b.flags, "rocket_mission") && !marked(b.flags, "artillery_city_bombing") &&
                            b.stage == "air_declared")
                            out.push_back(
                                action(s, s.currentNation(), "air_escort",
                                       {{"unit", V(id)}, {"path", V(ids(path))}, {"battle", V(bid)}}));
                if (u.type != "seaplane" && !transport(u) &&
                    (!has(s, u, "strategic_bomber") || tech(s, u.owner, "heavy_strategic_bombers"))) {
                    bool existing = false;
                    for (const auto &[bid, b] : s.battles)
                        if (b.zone == zone && b.attacker == u.owner && !marked(b.flags, "air_mission") &&
                            !marked(b.flags, "finished"))
                            existing = true;
                    if (!existing)
                        out.push_back(action(s, s.currentNation(), "air_ground_attack",
                                             {{"unit", V(id)}, {"path", V(ids(path))}}));
                }
                if (u.type != "seaplane" && !transport(u)) {
                    for (const auto &[bid, b] : s.battles)
                        if (b.zone == zone && b.attacker == s.currentNation() &&
                            !marked(b.flags, "air_mission") && !marked(b.flags, "finished") &&
                            b.stage == "awaiting_combat_rules" &&
                            (!has(s, u, "strategic_bomber") || tech(s, u.owner, "heavy_strategic_bombers")))
                            out.push_back(
                                action(s, s.currentNation(), "air_support",
                                       {{"unit", V(id)}, {"path", V(ids(path))}, {"battle", V(bid)}}));
                }
                if (!u.commitments.contains("air_screening_continued") && !u.cargo.empty() &&
                    (transport(u) || has(s, u, "strategic_bomber")) &&
                    std::all_of(u.cargo.begin(), u.cargo.end(), [&](const Id &c) {
                        const auto &cargo = s.units.at(c);
                        return cargo.owner == u.owner &&
                               (cargo.type == "airborne_infantry" || cargo.type == "elite_airborne_infantry");
                    }))
                    out.push_back(action(s, s.currentNation(), "air_assault",
                                         {{"unit", V(id)}, {"path", V(ids(path))}}));
            }
            if ((transport(u) || has(s, u, "strategic_bomber")) && land(s, u.zone))
                for (const auto &[cargo, c] : s.units)
                    if (c.zone == u.zone && !c.carriedBy && has(s, c, "land") && u.owner == c.owner &&
                        c.route.empty() && !marked(c.turnFlags, "placed_this_turn") &&
                        !marked(c.turnFlags, "air_transport_unloaded") && !marked(c.turnFlags,"naval_unloaded") &&
                        !c.commitments.contains("transport_unloaded") && !c.commitments.contains("attrition") &&
                        !c.commitments.contains("combat") && !c.commitments.contains("combat_move")) {
                        int cap = u.type == "heavy_air_transport" && combat ? 2 : 1;
                        if (static_cast<int>(u.cargo.size()) >= cap)
                            continue;
                        bool allowed =
                            combat
                                ? (c.type == "airborne_infantry" || c.type == "elite_airborne_infantry")
                                : (transport(u) &&
                                   (has(s, c, "infantry_class") ||
                                    (u.type == "heavy_air_transport" &&
                                     (has(s, c, "artillery_class") || c.type == "anti_aircraft_artillery"))));
                        if (allowed)
                            out.push_back(action(s, s.currentNation(), "air_load",
                                                 {{"unit", V(id)}, {"cargo", V(cargo)}}));
                    }
            if (!combat || marked(u.turnFlags, "air_in_flight"))
                for (const auto &destination : airLandingSpots(s, id))
                    if (s.units.contains(destination) && landingChangesState(s, u, destination) &&
                        preservesLandingPlan(s, id, destination))
                        out.push_back(action(s, s.currentNation(), "air_land_noncombat",
                                             {{"unit", V(id)}, {"destination", V(destination)}}));
            if (!combat && !u.cargo.empty() && land(s, u.zone) &&
                heldSinceTurnStart(s, u.owner, u.zone, true) && s.territories.at(u.zone).possessor &&
                friendly(s, u.owner, *s.territories.at(u.zone).possessor))
                for (const auto &cargo : u.cargo)
                    if(s.units.at(cargo).owner==u.owner)
                        out.push_back(action(s, s.currentNation(), "air_unload", {{"unit", V(id)}, {"cargo", V(cargo)}}));
        }
    return out;
}
bool AirRules::phaseComplete(const State &s) const {
    if (s.clock.phase == Phase::CombatMovement && !airLandingPlanAvailable(s)) return false;
    if (s.clock.phase == Phase::Combat)
        for (const auto &[id, u] : s.units)
            if (movementController(s, u.owner) && (marked(u.turnFlags, "air_screening_wait") ||
                marked(u.turnFlags, "air_screening_ready"))) return false;
    if (s.clock.phase == Phase::CombatMovement || s.clock.phase == Phase::NonCombatMovement)
        for (const auto &[id, u] : s.units)
            if (isAircraft(s, u) && movementController(s, u.owner) && marked(u.turnFlags, "air_in_flight") &&
                (s.clock.phase == Phase::NonCombatMovement || !u.commitments.contains("air_combat")))
                return false;
    return !gameplay_ || gameplay_->phaseComplete(s);
}
void AirRules::apply(State &s, const Action &a) const {
    if (a.kind.rfind("air_", 0) != 0) {
        require(bool(gameplay_), "Unknown air action");
        gameplay_->apply(s, a);
        return;
    }
    const auto &p = a.parameters;
    if (a.kind=="air_resume_bombing") {
        auto &b=s.battles.at(p.require("battle").asString());
        b.flags.erase("air_waiting_port_evacuation");
        continueBombing(s,b);return;
    }
    if (a.kind == "air_screen_continue") {
        const auto id = p.require("unit").asString();
        const auto path = readIds(p.require("path"));
        require(validateFlight(s, id, path, true, true).allowed, "Invalid continuing-force flight");
        moveFlight(s, id, path);
        auto &u = s.units.at(id);u.turnFlags.erase("air_screening_ready");
        u.turnFlags["air_screening_wait"] = 1;
        u.commitments.insert("air_screening_continued");u.commitments.insert("air_combat");
        auto &b = s.battles.at(p.require("battle").asString());
        auto waiting = array(b, "air_screening_continuing");waiting.emplace_back(id);
        put(b, "air_screening_continuing", V(std::move(waiting)));
        require(airLandingPlanAvailable(s), "Continuing aircraft have no joint return plan");
        return;
    }
    if (a.kind == "air_artillery_city_bomb") {
        const auto id = p.require("unit").asString(), zone = p.require("zone").asString();
        auto &u = s.units.at(id);
        u.commitments.insert("attrition");u.movementRemaining = 0;
        BattleState b;
        b.id = "air_mission_" + std::to_string(++s.flags["air_mission_sequence"]);
        b.zone = zone;b.attacker = u.owner;b.defender = *s.territories.at(zone).possessor;
        b.attackers = {id};b.stage = "air_declared";
        b.flags["air_mission"] = 1;b.flags["artillery_city_bombing"] = 1;
        put(b, "target_kind", V(std::string("city")));put(b, "target", V(zone));
        s.battleOrder.push_back(b.id);s.battles.emplace(b.id, std::move(b));
        return;
    }
    if (a.kind == "air_failed_landing") {
        auto id = p.require("unit").asString();
        require(airLandingSpots(s, id).empty(), "Aircraft can still land");
        eraseAirUnit(s, id);
        return;
    }
    if (a.kind == "air_start_patrol") {
        auto id = p.require("unit").asString();
        moveFlight(s, id, readIds(p.require("path")));
        auto &u = s.units.at(id);
        u.gameFlags["on_map"] = 1;
        u.gameFlags["map_range"] = p.require("range").asInt();
        u.commitments.insert("maritime_air_patrol");
        u.turnFlags.erase("air_in_flight");
        u.turnFlags["on_map"] = 1;
        return;
    }
    if (a.kind == "air_end_patrol") {
        auto id = p.require("unit").asString();
        auto &u = s.units.at(id);
        auto range = flag(u.gameFlags, "map_range");
        auto path = readIds(p.require("path"));
        require(static_cast<int>(path.size()) - 1 <= range, "Patrol return exceeds range");
        u.movementRemaining = std::max(u.movementRemaining.value_or(0), range);
        u.movementAllowance = std::max(u.movementAllowance.value_or(0), range);
        moveFlight(s, id, path);
        u.gameFlags.erase("on_map");
        u.gameFlags.erase("map_range");
        u.turnFlags.erase("on_map");
        u.turnFlags.erase("air_in_flight");
        u.commitments.erase("maritime_air_patrol");
        u.movementRemaining = 0;
        auto dest = p.require("destination").asString();
        if (s.units.contains(dest))
            attachCargo(s, dest, id);
        return;
    }
    if (a.kind == "air_fly") {
        auto id = p.require("unit").asString();
        auto path = readIds(p.require("path"));
        require(validateFlight(s, id, path, s.clock.phase != Phase::NonCombatMovement, false).allowed,
                "Invalid flight");
        require(flightCanContinue(s, id, path), "Flight leaves aircraft without any possible landing continuation");
        moveFlight(s, id, path);
        return;
    }
    if (a.kind == "air_load" || a.kind == "air_allied_load") {
        attachCargo(s, p.require("unit").asString(), p.require("cargo").asString());
        if (a.kind == "air_allied_load")
            s.units.at(p.require("cargo").asString()).gameFlags["air_allied_loaded_turn"] =
                static_cast<int>(s.clock.playerTurnSerial + 1);
        return;
    }
    if (a.kind == "air_unload" || a.kind == "air_allied_unload") {
        auto id = p.require("unit").asString(), cargo = p.require("cargo").asString();
        detachCargo(s, id, cargo, s.units.at(id).zone);
        s.units.at(cargo).movementRemaining = 0;
        s.units.at(cargo).turnFlags["air_transport_unloaded"] = 1;
        return;
    }
    if (a.kind == "air_land_noncombat") {
        auto id = p.require("unit").asString(), z = p.require("destination").asString();
        require(landingChangesState(s, s.units.at(id), z), "Aircraft is already grounded at this landing destination");
        auto paths = flightPaths(s, id, false);
        auto dest = s.units.contains(z) ? s.units.at(z).zone : z;
        require(paths.contains(dest) && airLandingAvailable(s, id, z), "Invalid landing");
        moveFlight(s, id, paths.at(dest));
        s.units.at(id).turnFlags.erase("air_in_flight");
        if (marked(s.units.at(id).turnFlags, "air_screening_ready")) {
            s.units.at(id).turnFlags.erase("air_screening_ready");stamp(s, s.units.at(id));
        }
        if (s.units.contains(z))
            attachCargo(s, z, id);
        return;
    }
    if (a.kind == "air_bomb" || a.kind == "air_support" || a.kind == "air_assault" ||
        a.kind == "air_escort" || a.kind == "air_ground_attack" || a.kind == "air_blitz") {
        auto id = p.require("unit").asString();
        auto path = readIds(p.require("path"));
        require(validateFlight(s, id, path, true, true).allowed, "Invalid attack flight");
        if (a.kind == "air_blitz")
            require(marked(s.units.at(id).turnFlags, "blitz_eligible") &&
                        blitzPairValid(s, s.units.at(id), path.front(), path.back()),
                    "Aircraft has no paired blitz path");
        moveFlight(s, id, path);
        auto &u = s.units.at(id);
        u.turnFlags.erase("air_screening_ready");
        if (a.kind == "air_blitz")
            u.turnFlags.erase("blitz_eligible");
        require(airLandingPlanAvailable(s), "No joint legal return landing plan");
        u.commitments.insert("air_combat");
        if (a.kind == "air_support" || a.kind == "air_escort") {
            auto &b = s.battles.at(p.require("battle").asString());
            b.attackers.push_back(id);
            return;
        }
        if (a.kind == "air_ground_attack" || a.kind == "air_blitz") {
            auto origin = path.size() > 1 ? path[path.size() - 2] : u.turnOrigin;
            recordLandAttack(s,u.owner,u.zone);
            registerLandBattle(s, u.zone, u.owner, {id}, {{id, origin}});
            return;
        }
        if (a.kind == "air_assault") {
            require(!u.commitments.contains("air_screening_continued"), "A continuing force cannot conduct an airborne assault");
            auto cargo = u.cargo;
            require(!cargo.empty() &&
                        cargo.size() <= static_cast<std::size_t>(u.type == "heavy_air_transport" ? 2 : 1),
                    "Invalid airborne capacity");
            for (const auto &c : cargo)
                require(s.units.at(c).owner == u.owner && (s.units.at(c).type == "airborne_infantry" ||
                                                           s.units.at(c).type == "elite_airborne_infantry"),
                        "Only own airborne infantry can assault");
            u.commitments.insert("airborne_assault");
            for (const auto &c : cargo) {
                s.units.at(c).commitments.insert("airborne_assault");
                s.units.at(c).turnFlags["airborne_assault"] = 1;
            }
            auto units = cargo;
            units.push_back(id);
            std::map<Id, Id> origins;
            for (const auto &x : units)
                origins[x] = path.size() > 1 ? path[path.size() - 2] : u.turnOrigin;
            recordLandAttack(s, u.owner, u.zone);
            auto bid = registerLandBattle(s, u.zone, u.owner, units, origins);
            s.battles.at(bid).flags["airborne_assault"] = 1;
            return;
        }
        for (auto &[bid, existing] : s.battles)
            if (marked(existing.flags, "air_mission") && !marked(existing.flags, "rocket_mission") &&
                !marked(existing.flags, "artillery_city_bombing") &&
                existing.stage == "air_declared" && existing.attacker == u.owner && existing.zone == u.zone &&
                str(existing, "target_kind") == p.require("kind").asString() &&
                str(existing, "target") == p.require("target").asString()) {
                existing.attackers.push_back(id);
                return;
            }
        BattleState b;
        b.id = "air_mission_" + std::to_string(++s.flags["air_mission_sequence"]);
        b.zone = u.zone;
        b.attacker = u.owner;
        b.defender = *s.territories.at(u.zone).possessor;
        b.attackers = {id};
        b.stage = "air_declared";
        b.flags["air_mission"] = 1;
        put(b, "target_kind", p.require("kind"));
        put(b, "target", p.require("target"));
        s.battleOrder.push_back(b.id);
        s.battles.emplace(b.id, std::move(b));
        return;
    }
    if (a.kind == "air_rocket_attack") {
        auto id = p.require("unit").asString();
        auto &u = s.units.at(id);
        u.turnFlags["rocket_launched"] = 1;
        u.commitments.insert("combat_move");
        u.movementRemaining = 0;
        BattleState b;
        b.id = "air_mission_" + std::to_string(++s.flags["air_mission_sequence"]);
        b.zone = p.require("zone").asString();
        b.attacker = u.owner;
        b.defender = *s.territories.at(b.zone).possessor;
        b.attackers = {id};
        b.stage = "air_declared";
        b.flags["air_mission"] = 1;
        b.flags["rocket_mission"] = 1;
        put(b, "target_kind", p.require("kind"));
        put(b, "target", p.require("target"));
        s.battleOrder.push_back(b.id);
        s.battles.emplace(b.id, std::move(b));
        return;
    }
    const auto bid = p.require("battle").asString();
    auto &b = s.battles.at(bid);
    if (a.kind == "air_begin_bombing") {
        b.stage = "air_resolving";
        if (b.attacker == "japan" &&
            marked(s.nations.at("japan").turnFlags, "surprise_attack_zone:" + b.zone) &&
            !marked(s.nations.at("japan").turnFlags, "surprise_attack_used")) {
            b.flags["japanese_surprise_attack"] = 1;
            s.nations.at("japan").turnFlags["surprise_attack_used"] = 1;
        }
        put(b, "air_stage",
            V(std::string(marked(b.flags, "artillery_city_bombing") ? "damage" :
                          marked(b.flags, "rocket_mission") ? "rocket_aa" : "interception_choices")));
        for (const auto &id : b.attackers)
            stamp(s, s.units.at(id));
        continueBombing(s, b);
        return;
    }
    if (a.kind == "air_scramble" || a.kind == "air_decline_scramble" || a.kind == "air_ground" ||
        a.kind == "air_defend") {
        release(s, a);
        auto id = p.require("unit").asString();
        auto done = object(b, "air_defence_choices");
        if (a.kind == "air_scramble" || a.kind == "air_decline_scramble")
            done["scramble:" + id] = V(true);
        else
            done["ground:" + id] = V(true);
        put(b, "air_defence_choices", V(done));
        if (a.kind == "air_scramble")
            useScramble(s, b, id, p.require("source").asString());
        if (a.kind == "air_ground") {
            auto grounded = object(b, "grounded");
            grounded[id] = V(true);
            put(b, "grounded", V(grounded));
        }
        if (a.kind == "air_defend") {
            auto &u = s.units.at(id);
            if (u.carriedBy && has(s, s.units.at(*u.carriedBy), "carrier") && !land(s, b.zone)) {
                const auto carrier = *u.carriedBy;
                detachCargo(s, carrier, id, u.zone);
                u.commitments.insert("air_defending_carrier:" + carrier);
            }
            stamp(s, s.units.at(id));
            s.units.at(id).commitments.insert("air_battle:" + b.id);
        }
        continueDefence(s, b);
        return;
    }
    if (a.kind == "air_intercept" || a.kind == "air_decline_intercept") {
        release(s, a);
        auto id = p.require("unit").asString();
        auto done = object(b, "air_interception_choices");
        done[id] = V(true);
        put(b, "air_interception_choices", V(done));
        if (a.kind == "air_intercept") {
            auto source = p.require("source").asString();
            if (source == "local") {
                b.defenders.push_back(id);
                stamp(s, s.units.at(id));
                s.units.at(id).commitments.insert("air_battle:" + b.id);
            } else
                useScramble(s, b, id, source);
        }
        continueBombing(s, b);
        return;
    }
    if (a.kind == "air_choose_casualty") {
        release(s, a);
        auto id = p.require("unit").asString();
        auto pending = array(b, "air_pending_dead");
        pending.emplace_back(id);
        put(b, "air_pending_dead", V(pending));
        auto hits = array(b, "air_hit_queue");
        hits.erase(hits.begin());
        put(b, "air_hit_queue", V(hits));
        auto &side = std::find(b.attackers.begin(), b.attackers.end(), id) != b.attackers.end() ? b.attackers
                                                                                                : b.defenders;
        side.erase(std::remove(side.begin(), side.end(), id), side.end());
        queueAirCasualty(s, b);
        return;
    }
    if (a.kind == "air_choose_rail_border") {
        release(s, a);
        applyRailBombDamage(s, b.zone, p.require("neighbor").asString(), b.flags.at("bomb_damage"));
        continueBombing(s, b);
        return;
    }
    if (a.kind == "air_choose_technology_loss") {
        release(s, a);
        auto owner = *s.territories.at(b.zone).possessor;
        --s.nations.at(owner).technologyStages.at(p.require("technology").asString());
        continueBombing(s, b);
        return;
    }
    if (a.kind == "air_land") {
        release(s, a);
        auto id = p.require("unit").asString(), z = p.require("destination").asString();
        require(airLandingAvailable(s, id, z), "Landing spot lost");
        auto dest = s.units.contains(z) ? s.units.at(z).zone : z;
        auto paths = flightPaths(s, id, false);
        require(paths.contains(dest), "Landing beyond range");
        moveFlight(s, id, paths.at(dest));
        s.units.at(id).turnFlags.erase("air_in_flight");
        s.units.at(id).turnFlags["air_landed_after_combat"] = 1;
        if (s.units.contains(z))
            attachCargo(s, z, id);
        queueLandings(s, b);
        return;
    }
    throw std::runtime_error("Unknown air action: " + a.kind);
}
void AirRules::applyChance(State &s, const ChanceRequest &r, const ChanceOutcome &o) const {
    if (r.purpose.rfind("air_", 0) != 0) {
        require(bool(gameplay_), "Unknown air chance");
        gameplay_->applyChance(s, r, o);
        return;
    }
    auto &b = s.battles.at(r.continuation);
    auto values = effectiveResults(r, o);
    if (r.purpose == "air_bomb_damage") {
        int damage = std::accumulate(values.begin(), values.end(), 0);
        b.flags["bomb_damage"] = damage;
        auto kind = str(b, "target_kind");
        if (kind == "facility")
            applyFacilityBombDamage(s, str(b, "target"), damage);
        else if (kind == "construction")
            damageConstruction(s, str(b, "target"), damage);
        else if (kind == "city") {
            bool before = marked(s.territories.at(b.zone).flags, "city_destroyed");
            applyCityBombDamage(s, b.zone, damage);
            if (!before && marked(s.territories.at(b.zone).flags, "city_destroyed")) {
                auto owner = *s.territories.at(b.zone).possessor;
                std::vector<Action> opts;
                for (const auto &[id, stage] : s.nations.at(owner).technologyStages)
                    if (stage >= 1 && stage <= 3)
                        opts.push_back(action(s, b.attacker, "air_choose_technology_loss",
                                              {{"battle", V(b.id)}, {"technology", V(id)}}));
                if (!opts.empty()) {
                    decision(s, b, b.attacker, "air_destroyed_city_technology", std::move(opts));
                    return;
                }
            }
        } else if (kind == "rail") {
            std::set<Id> other;
            for (const auto &[id, x] : s.rails)
                if (x.endpointA == b.zone)
                    other.insert(x.endpointB);
                else if (x.endpointB == b.zone)
                    other.insert(x.endpointA);
            std::vector<Action> opts;
            for (const auto &z : other)
                opts.push_back(action(s, b.attacker, "air_choose_rail_border",
                                      {{"battle", V(b.id)}, {"neighbor", V(z)}}));
            decision(s, b, b.attacker, "air_rail_border", std::move(opts));
            return;
        }
        if (!s.decisions.empty()) { b.flags["air_waiting_port_evacuation"]=1; return; }
        continueBombing(s, b);
        return;
    }
    if (r.purpose == "air_rocket_aa") {
        if (values.front() <= aaThreshold(s, b)) {
            auto units = b.attackers;
            for (const auto &id : units)
                eraseAirUnit(s, id);
        }
        continueBombing(s, b);
        return;
    }
    A hits;
    if (r.purpose == "air_interception_roll") {
        auto shots = array(b, "air_shots");
        for (std::size_t i = 0; i < values.size(); ++i)
            if (values[i] <= shots[i].require("threshold").asInt())
                hits.emplace_back(O{{"target", shots[i].require("target")}});
    } else if (r.purpose == "air_facility_aa") {
        for (int x : values)
            if (x <= aaThreshold(s, b))
                hits.emplace_back(O{{"target", V(std::string("attacker"))}});
    } else
        throw std::runtime_error("Unknown air roll");
    put(b, "air_hit_queue", V(hits));
    queueAirCasualty(s, b);
}
void AirRules::beginTurn(State &s) const {
    if (gameplay_)
        gameplay_->beginTurn(s);
    for (auto &[id, u] : s.units)
        if (isAircraft(s, u) && movementController(s, u.owner)) {
            if (marked(u.gameFlags, "on_map")) {
                u.turnFlags["on_map"] = 1;
                u.commitments.insert("maritime_air_patrol");
                continue;
            }
            for (const auto &[fid, f] : s.facilities)
                if (f.zone == u.zone && f.damage == 0 && !marked(f.flags, "placed_this_turn") &&
                    ((f.type == "airbase" && u.type != "seaplane") ||
                     (f.type == "seaplane_base" && u.type == "seaplane")) &&
                    s.territories.at(f.zone).possessor &&
                    friendly(s, u.owner, *s.territories.at(f.zone).possessor) &&
                    (*s.territories.at(f.zone).possessor != u.owner ||
                     heldSinceNationTurnStart(s, u.owner, f.zone, false)) &&
                    inSupply(s, u.owner, f.zone)) {
                    ++*u.movementAllowance;
                    ++*u.movementRemaining;
                    break;
                }
        }
}
void AirRules::finishPhase(State &s) const {
    enforcePatrolLandingAvailability(s);
    if (s.clock.phase == Phase::Combat) {
        std::vector<Id> returners;
        for (const auto &[id, u] : s.units)
            if (marked(u.turnFlags, "scrambled"))
                returners.push_back(id);
        for (const auto &id : returners) {
            if (!s.units.contains(id))
                continue;
            auto &u = s.units.at(id);
            Id origin, source;
            for (const auto &c : u.commitments) {
                if (c.rfind("air_scramble_origin:", 0) == 0)
                    origin = c.substr(std::string("air_scramble_origin:").size());
                if (c.rfind("air_scramble_source:", 0) == 0)
                    source = c.substr(std::string("air_scramble_source:").size());
            }
            bool available = false;
            if (s.territories.contains(origin)) {
                // The return location is the land zone. Damage to its airbase
                // does not destroy that location or prevent ordinary landing.
                const auto owner = s.territories.at(origin).possessor;
                available = owner && friendly(s, u.owner, *owner);
            } else
                available = s.units.contains(source) && s.units.at(source).zone == origin &&
                            airLandingAvailable(s, id, source);
            if (!available || origin.empty())
                eraseAirUnit(s, id);
            else {
                u.zone = origin;
                u.turnFlags.erase("scrambled");
                u.commitments.erase("air_scramble_origin:" + origin);
                u.commitments.erase("air_scramble_source:" + source);
                if (s.units.contains(source))
                    attachCargo(s, source, id);
            }
        }
    }
    if (gameplay_)
        gameplay_->finishPhase(s);
}
void AirRules::finishTurn(State &s) const {
    require(bool(gameplay_), "Air module requires income accounting");
    gameplay_->finishTurn(s);
}
} // namespace game::campaign
