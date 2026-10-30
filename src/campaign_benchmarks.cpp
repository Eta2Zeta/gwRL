#include "game/campaign_benchmarks.hpp"
#include "game/campaign_audit.hpp"
#include "game/composition_battle_env.hpp"
#include "game/air.hpp"
#include "game/catalog.hpp"
#include "game/economy.hpp"
#include "game/land_combat.hpp"
#include "game/movement.hpp"
#include "game/naval.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <stdexcept>

namespace game {
namespace {
using namespace campaign;
using V = json::Value;
using O = V::Object;
using A = V::Array;
V n(int value) { return V(static_cast<double>(value)); }
int flag(const std::map<Id, int> &flags, const Id &key) {
    auto i = flags.find(key); return i == flags.end() ? 0 : i->second;
}
int asset(const State &s, const Id &type) {
    return s.definition->catalog->unit(type).assetValue.value_or(0);
}
Id unitType(std::string_view text) {
    static const std::map<std::string_view, Id> aliases{
        {"Infantry", "infantry"}, {"Artillery", "artillery"}, {"Marine", "marine"},
        {"LightTank", "light_armor"}, {"MechanizedInfantry", "mechanized_infantry"},
        {"MediumTank", "medium_armor"}, {"TankDestroyer", "tank_destroyer"},
        {"Fighter", "fighter"}, {"Transport", "transport"}};
    const auto i = aliases.find(text); return i == aliases.end() ? Id(text) : i->second;
}
void unit(State &s, const Id &owner, const Id &zone, const Id &type) {
    UnitState u;
    u.id = "benchmark_unit_" + std::to_string(++s.flags["benchmark_unit_sequence"]);
    u.type = type; u.owner = owner; u.zone = u.turnOrigin = zone;
    u.movementAllowance = u.movementRemaining =
        s.definition->catalog->stats(type, 0, catalogContext(s, owner, zone)).movement;
    s.units.emplace(u.id, std::move(u));
}
V landNode(const Id &owner, const std::string &terrain, bool city, int ipp, A neighbors) {
    return V(O{{"type", V(std::string("land"))}, {"original_owner", V(owner)},
        {"terrain", V(terrain)}, {"is_city", V(city)}, {"ipp_value", n(ipp)},
        {"neighbors", V(std::move(neighbors))}, {"rail_region", V(std::string("asia"))},
        {"rail_gauge", V(std::string("standard"))}, {"island", V(false)}});
}
V edge(const Id &to, bool rail = false) {
    return V(O{{"neighbor_id", V(to)}, {"passable", V(true)},
        {"border_terrain", V(nullptr)}, {"river_crossing", V(false)},
        {"railway_connection", V(rail)}, {"gauge_change", V(false)},
        {"narrow_crossing", V(false)}, {"naval_facilities", V(A{})},
        {"naval_facility_ids", V(A{})}});
}
State emptyBase() {
    auto s = loadScenario(benchmarkContentRoot() / "game_content/scenarios/japan_china_1936");
    s.units.clear(); s.facilities.clear(); s.rails.clear(); s.territories.clear();
    s.construction.clear(); s.repairs.clear(); s.battles.clear(); s.battleOrder.clear();
    s.decisions.clear(); s.chance.reset(); s.history.clear(); s.flags.clear();
    s.politics = {}; s.clock = {}; s.turnStart = {}; s.completedTurns.clear();
    for (auto &[id, nation] : s.nations) {
        nation.turnFlags.clear(); nation.gameFlags.clear(); nation.technologyStages.clear();
        nation.atWarWith.clear(); nation.allies.clear(); nation.incomeComponents.clear();
        nation.incomeKnown = true; nation.treasury = std::nullopt;
    }
    return s;
}
void defineGeography(State &s, Definition d, O nodes, O owners, O config) {
    for (auto &[id, value] : nodes) {
        auto record = value.asObject(); record["id"] = V(id); value = V(std::move(record));
    }
    d.geography = V(O{{"nodes", V(std::move(nodes))}, {"facilities", V(O{})}});
    auto rules = d.rules.asObject();
    auto index = rules.at("faction_index").asObject();
    index["land_original_owners"] = V(std::move(owners));
    rules["faction_index"] = V(std::move(index));
    rules["benchmark"] = V(std::move(config));
    d.rules = V(std::move(rules));
    for (auto &[id, faction] : d.factions) {
        for (auto i = faction.homeCountry.begin(); i != faction.homeCountry.end();)
            if (!s.territories.contains(*i)) i = faction.homeCountry.erase(i); else ++i;
    }
    s.definition = freezeDefinition(std::move(d));
    for (const auto &nation : s.definition->turnOrder) s.completedTurns[nation] = 0;
    refreshPoliticalState(s); refreshIncome(s); s.captureTurnStart(); s.validate();
}
O original(const Id &owner) {
    return O{{"original_faction_id", V(owner)}, {"source_original_owner", V(owner)}};
}
void losses(State &s, const std::map<Id, UnitState> &before,
            const std::map<Id, BattleState> &battles) {
    for (const auto &[id, u] : before) {
        if (s.units.contains(id)) continue;
        const int value = asset(s, u.type);
        s.nations.at(u.owner).gameFlags["benchmark_lost_value"] += value;
        for (const auto &[bid, b] : battles) {
            const bool attacker = std::find(b.attackers.begin(), b.attackers.end(), id) != b.attackers.end();
            const bool defender = std::find(b.defenders.begin(), b.defenders.end(), id) != b.defenders.end();
            if (attacker || defender) {
                const auto &credited = attacker ? b.defender : b.attacker;
                if (credited != u.owner)
                    s.nations.at(credited).gameFlags["benchmark_destroyed_enemy_value"] += value;
                break;
            }
        }
    }
}
void compositionChoices(State &s, const Id &nation) {
    Decision d;
    d.id = "benchmark_compose_" + nation; d.kind = "benchmark_compose"; d.nation = nation;
    d.continuation = "benchmark_setup";
    const int cash = s.nations.at(nation).treasury.value_or(0);
    for (const auto &type : s.definition->rules.require("benchmark").require("roster").asArray()) {
        const auto &u = s.definition->catalog->unit(type.asString());
        const int cost = std::accumulate(u.purchaseCosts.begin(), u.purchaseCosts.end(), 0);
        if (cost <= 0) continue;
        for (int count = 1; count <= cash / cost; ++count) {
            auto a = politicalAction(s, nation, "benchmark_compose_units",
                V(O{{"type", type}, {"count", n(count)}}), d.id);
            d.options.push_back(std::move(a));
        }
    }
    d.options.push_back(politicalAction(s, nation, "benchmark_finish_composition", V(O{}), d.id));
    s.decisions.push_back(std::move(d));
}
class BenchmarkRules final : public Rules {
  public:
    explicit BenchmarkRules(bool composition) : composition_(composition), core_(campaignRules()) {}
    Id id() const override { return "campaign_benchmark_v1+" + core_->id(); }
    std::vector<Action> actions(const State &s) const override {
        auto out = core_->actions(s);
        if (!composition_) {
            const auto &allowed = s.definition->rules.require("benchmark").require("purchase_roster").asArray();
            out.erase(std::remove_if(out.begin(), out.end(), [&](const Action &a) {
                if (a.kind != "economy_purchase") return false;
                const auto &row = s.definition->catalog->row(a.parameters.require("row").asString());
                return std::none_of(allowed.begin(), allowed.end(), [&](const V &v) { return v.asString() == row.type; });
            }), out.end());
        }
        return out;
    }
    std::vector<Action> interrupts(const State &s) const override { return core_->interrupts(s); }
    bool phaseComplete(const State &s) const override { return !composition_ && core_->phaseComplete(s); }
    void apply(State &s, const Action &a) const override {
        if (a.kind.rfind("benchmark_", 0) == 0) {
            if (s.decisions.empty() || s.decisions.back().kind != "benchmark_compose")
                throw std::runtime_error("Benchmark composition is not pending");
            s.decisions.pop_back();
            if (a.kind == "benchmark_compose_units") {
                const auto type = a.parameters.require("type").asString();
                const int count = a.parameters.require("count").asInt();
                const auto &costs = s.definition->catalog->unit(type).purchaseCosts;
                const int cost = std::accumulate(costs.begin(), costs.end(), 0) * count;
                *s.nations.at(a.nation).treasury -= cost;
                s.nations.at(a.nation).gameFlags["benchmark_purchased:" + type] += count;
                for (int i = 0; i < count; ++i) unit(s, a.nation, "benchmark_battle", type);
                compositionChoices(s, a.nation);
                return;
            }
            if (a.kind != "benchmark_finish_composition") throw std::runtime_error("Unknown benchmark action");
            s.nations.at(a.nation).gameFlags["benchmark_unspent_budget"] =
                s.nations.at(a.nation).treasury.value_or(0);
            if (a.nation == "japan") { compositionChoices(s, "kmt"); return; }
            s.flags["benchmark_composition_ready"] = 1;
            std::vector<Id> attackers; std::map<Id, Id> origins;
            for (const auto &[id, u] : s.units) if (u.owner == "japan") {
                attackers.push_back(id); origins[id] = "benchmark_origin";
            }
            if (attackers.empty()) { s.flags["benchmark_battle_finished"] = 1; return; }
            registerLandBattle(s, "benchmark_battle", "japan", attackers, origins);
            return;
        }
        const auto before = s.units; const auto battles = s.battles;
        core_->apply(s, a); losses(s, before, battles);
    }
    void applyChance(State &s, const ChanceRequest &q, const ChanceOutcome &o) const override {
        const auto before = s.units; const auto battles = s.battles;
        core_->applyChance(s, q, o); losses(s, before, battles);
    }
    void beginTurn(State &s) const override { core_->beginTurn(s); }
    void finishTurn(State &s) const override { core_->finishTurn(s); }
    void finishPhase(State &s) const override { core_->finishPhase(s); }
  private:
    bool composition_; std::shared_ptr<const Rules> core_;
};
std::uint64_t hash(const std::string &text) {
    std::uint64_t value = UINT64_C(14695981039346656037);
    for (const unsigned char c : text) { value ^= c; value *= UINT64_C(1099511628211); }
    return value;
}
// Feature hashing traverses every public decision-state field. It gives both
// benchmarks a stable-size neural input without encoding RNG or audit history.
void features(const V &v, const std::string &path, std::vector<double> &out) {
    if (v.isObject()) {
        for (const auto &[key, child] : v.asObject()) features(child, path + "/" + key, out);
    } else if (v.isArray()) {
        for (std::size_t i = 0; i < v.asArray().size(); ++i)
            features(v.asArray()[i], path + "/" + std::to_string(i), out);
    } else {
        const auto token = v.isNumber() ? path + "=number" : path + "=" + canonicalJson(v);
        const auto h = hash(token);
        const double amount = v.isNumber() ? std::copysign(std::log1p(std::abs(v.asNumber())), v.asNumber()) : 1.0;
        out[h % out.size()] += (h & (UINT64_C(1) << 63) ? -amount : amount);
    }
}
std::vector<double> encode(const V &value, std::size_t size) {
    std::vector<double> out(size, 0.0); features(value, "", out); return out;
}
std::vector<std::string> labels(const std::string &kind, std::size_t size) {
    std::vector<std::string> out;
    for (std::size_t i = 0; i < size; ++i) out.push_back("campaign_v1_" + kind + "_hash_" + std::to_string(i));
    return out;
}
} // namespace

campaign::Id benchmarkNation(std::string_view text) {
    static const std::map<std::string_view, campaign::Id> aliases{{"Japan", "japan"},
        {"CCP", "ccp"}, {"KMT", "kmt"}, {"Attacker", "japan"}, {"Defender", "kmt"},
        {"ZhiliClique", "warlord_beiping_hopeh"}, {"Mengjiang", "warlord_suiyuan"}};
    const auto i = aliases.find(text); return i == aliases.end() ? campaign::Id(text) : i->second;
}
std::string benchmarkDisplayNation(const campaign::Id &id) {
    if (id == "japan") return "Japan"; if (id == "ccp") return "CCP"; if (id == "kmt") return "KMT";
    return id;
}
std::filesystem::path benchmarkContentRoot() {
#ifdef GWRL_SOURCE_DIR
    return std::filesystem::path(GWRL_SOURCE_DIR);
#else
    auto path = std::filesystem::current_path();
    while (!path.empty()) {
        if (std::filesystem::exists(path / "game_content/catalog/gw36_v43")) return path;
        if (path == path.parent_path()) break; path = path.parent_path();
    }
    throw std::runtime_error("Cannot locate benchmark campaign content");
#endif
}
campaign::State tinyCampaignBenchmark(const std::filesystem::path &path) {
    const auto source = json::parseFile(path);
    auto s = emptyBase(); auto d = *s.definition;
    d.scenarioId = "tiny_shared_campaign_v1"; d.turnOrder.clear();
    for (const auto &id : source.require("turn_order").asArray()) d.turnOrder.push_back(benchmarkNation(id.asString()));
    d.calendarRounds = source.require("turn_limit_per_nation").asInt();
    O nodes, owners;
    for (auto &[id, f] : d.factions) f.homeCountry.clear();
    for (const auto &zone : source.require("zones").asArray()) {
        const auto id = zone.require("id").asString();
        const auto owner = benchmarkNation(zone.require("controller").asString());
        if (!s.nations.contains(owner)) throw std::runtime_error("Unknown tiny benchmark owner: " + owner);
        A neighbors;
        for (const auto &e : zone.require("neighbors").asArray()) {
            const auto to = e.require("id").asString();
            const bool rail = e.find("railway") && e.require("railway").asBool();
            neighbors.push_back(edge(to, rail));
            if (rail && id < to) {
                const auto rid = "benchmark_rail_" + id + "_" + to;
                s.rails.emplace(rid, RailState{rid, id, to, {}});
            }
        }
        const auto terrain = zone.find("terrain") ? zone.require("terrain").asString() : "normal";
        const bool city = zone.find("is_city") && zone.require("is_city").asBool();
        const int ipp = zone.find("income_value") ? zone.require("income_value").asInt() : 0;
        nodes[id] = landNode(owner, terrain, city, ipp, std::move(neighbors));
        owners[id] = V(original(owner)); s.territories[id].possessor = owner;
        // The teaching fixture explicitly treats starting national possessions
        // as its Home Country; this is not the historical China scenario map.
        if (d.factions.contains(owner)) { d.factions.at(owner).homeCountryKnown = true; d.factions.at(owner).homeCountry.insert(id); }
    }
    O capacity;
    for (const auto &row : source.require("nations").asArray()) {
        const auto nation = benchmarkNation(row.require("id").asString());
        auto &account = s.nations.at(nation);
        account.treasury = row.find("treasury") ? row.require("treasury").asInt() : row.require("income").asInt();
        account.player = nation == "japan" ? "axis" : nation == "ccp" ? "comintern" : "allies";
        account.controllerNation = nation;
        int output = row.require("max_factory_output").asInt(); capacity[nation] = n(output);
        auto owned = d.factions.at(nation).homeCountry;
        if (output && owned.empty()) throw std::runtime_error("Benchmark production requires a home zone");
        while (output > 0) {
            const auto type = output >= 5 ? "major_factory" : output >= 3 ? "medium_factory" : "minor_factory";
            const int amount = s.definition->catalog->facility(type).productionCapacity;
            const auto fid = "benchmark_factory_" + nation + "_" + std::to_string(output);
            s.facilities.emplace(fid, FacilityState{fid, type, *owned.begin(), 0, {}}); output -= amount;
        }
    }
    s.politics.capitals["japan"] = *d.factions.at("japan").homeCountry.begin();
    O config{{"kind", V(std::string("tiny"))}, {"source_sha256", V(contentDigest(canonicalJson(source)))},
        {"home_country", V(std::string("starting possessions are benchmark homelands"))},
        {"initial_factory_capacity", V(capacity)}, {"purchase_roster", V(A{V(std::string("infantry")), V(std::string("artillery")), V(std::string("fighter"))})},
        {"objective", V(std::string("tracked territorial IPP + 0.1 surviving asset IPP + 0.1 destroyed enemy asset IPP"))}};
    defineGeography(s, std::move(d), std::move(nodes), std::move(owners), std::move(config));
    for (const auto &[nation, setup] : source.require("setup").asObject())
        for (const auto &u : setup.require("units").asArray())
            unit(s, benchmarkNation(u.find("owner") ? u.require("owner").asString() : nation),
                 u.require("zone").asString(), unitType(u.require("type").asString()));
    s.captureTurnStart(); s.validate(); return s;
}
campaign::State compositionCampaignBenchmark(int attackerBudget, int defenderBudget,
                                             const std::string &terrain, bool city) {
    if (attackerBudget < 0 || defenderBudget < 0 || attackerBudget > 1000 || defenderBudget > 1000)
        throw std::runtime_error("Composition budgets must be between 0 and 1000 IPP");
    const std::set<std::string> terrains{"normal", "mountain", "desert", "jungle", "forest", "marsh", "tundra", "tundra_ice"};
    if (!terrains.contains(terrain)) throw std::runtime_error("Unknown composition terrain");
    auto s = emptyBase(); auto d = *s.definition;
    d.scenarioId = "composition_shared_campaign_v1"; d.turnOrder = {"japan", "kmt"}; d.calendarRounds = 1;
    for (auto &[id, f] : d.factions) f.homeCountry.clear();
    d.factions.at("japan").homeCountry = {"benchmark_origin"};
    d.factions.at("kmt").homeCountry = {"benchmark_battle"};
    s.territories["benchmark_origin"].possessor = "japan";
    s.territories["benchmark_battle"].possessor = "kmt";
    O nodes{{"benchmark_origin", landNode("japan", "normal", false, 1, A{edge("benchmark_battle")})},
            {"benchmark_battle", landNode("kmt", terrain, city, 1, A{edge("benchmark_origin")})}};
    O owners{{"benchmark_origin", V(original("japan"))}, {"benchmark_battle", V(original("kmt"))}};
    s.nations.at("japan").treasury = attackerBudget; s.nations.at("kmt").treasury = defenderBudget;
    s.nations.at("japan").gameFlags["benchmark_initial_budget"] = attackerBudget;
    s.nations.at("kmt").gameFlags["benchmark_initial_budget"] = defenderBudget;
    s.nations.at("japan").atWarWith.insert("kmt"); s.nations.at("kmt").atWarWith.insert("japan");
    s.nations.at("japan").player = "axis"; s.nations.at("kmt").player = "allies";
    s.nations.at("japan").powerStatus = s.nations.at("kmt").powerStatus = "major";
    O config{{"kind", V(std::string("composition"))}, {"setup", V(std::string("catalog-cost force allocation; deployed before combat; both factions Major"))},
        {"roster", V(A{V(std::string("infantry")), V(std::string("artillery")), V(std::string("light_armor")),
            V(std::string("mechanized_infantry")), V(std::string("medium_armor")), V(std::string("tank_destroyer"))})},
        {"objective", V(std::string("win/loss plus 0.1 enemy asset losses minus own asset losses"))}};
    defineGeography(s, std::move(d), std::move(nodes), std::move(owners), std::move(config));
    s.clock.phase = Phase::Combat; compositionChoices(s, "japan"); s.validate(); return s;
}
std::shared_ptr<const campaign::Rules> benchmarkCampaignRules(bool composition) {
    return std::make_shared<BenchmarkRules>(composition);
}
CampaignBenchmarkEnv::CampaignBenchmarkEnv(State initial, bool composition, std::uint64_t seed)
    : initial_(std::move(initial)), composition_(composition), seed_(seed), rules_(benchmarkCampaignRules(composition)) { reset(); }
void CampaignBenchmarkEnv::reset() {
    engine_ = composition_ ? Engine(initial_.clone(), rules_, seed_) : Engine::start(initial_.clone(), rules_, seed_);
    resolvePendingChance();
}
void CampaignBenchmarkEnv::resetWithSeed(std::uint64_t seed) { seed_ = seed; reset(); }
void CampaignBenchmarkEnv::resolvePendingChance() {
    for (int k = 0; engine_->state().chance; ++k) {
        if (k >= 10000) throw std::runtime_error("Benchmark chance continuation did not finish");
        engine_->resolveChance();
    }
}
bool CampaignBenchmarkEnv::isTerminal() const {
    const auto &s = engine_->state();
    if (!composition_) return s.terminal;
    if (!flag(s.flags, "benchmark_composition_ready") || s.chance || !s.decisions.empty()) return false;
    if (flag(s.flags, "benchmark_battle_finished")) return true;
    return s.battles.empty() || std::all_of(s.battles.begin(), s.battles.end(), [](const auto &entry) {
        return flag(entry.second.flags, "finished") != 0;
    });
}
std::string CampaignBenchmarkEnv::currentNation() const {
    const auto &s = engine_->state();
    const auto nation = s.decisions.empty() ? s.currentNation() : s.decisions.back().nation;
    if (composition_) return nation == "japan" ? "Attacker" : nation == "kmt" ? "Defender" : nation;
    return benchmarkDisplayNation(nation);
}
std::string CampaignBenchmarkEnv::currentPhase() const {
    if (isTerminal()) return "terminal";
    if (composition_ && !flag(engine_->state().flags, "benchmark_composition_ready")) return "force_composition";
    return campaign::toString(engine_->state().clock.phase);
}
std::vector<campaign::Action> CampaignBenchmarkEnv::legalActions() const {
    if (isTerminal()) return {};
    auto out = engine_->legalActions();
    const auto player = engine_->state().decisionPlayer();
    // Other players' off-turn priorities remain available through the explicit
    // legalInterrupts API; the current player also sees its own interrupts in
    // the same encoded action list used by the training entrypoints.
    if (engine_->state().decisions.empty())
        for (const auto &a : engine_->legalInterrupts())
            if (player && a.player == *player) out.push_back(a);
    return out;
}
std::vector<campaign::Action> CampaignBenchmarkEnv::legalInterrupts() const { return isTerminal() ? std::vector<campaign::Action>{} : engine_->legalInterrupts(); }
BenchmarkStepResult CampaignBenchmarkEnv::step(const campaign::Action &a) {
    if (isTerminal()) throw std::runtime_error("Benchmark is terminal");
    BenchmarkStepResult result; result.actingNation = benchmarkDisplayNation(a.nation); result.action = a;
    const auto interrupts = engine_->legalInterrupts();
    const auto identity = canonicalJson(actionJson(a));
    const bool interrupt = std::any_of(interrupts.begin(), interrupts.end(), [&](const auto &candidate) { return canonicalJson(actionJson(candidate)) == identity; });
    if (interrupt) engine_->interrupt(a); else engine_->step(a);
    resolvePendingChance(); result.terminal = isTerminal(); result.detailLines.push_back(identity); return result;
}
std::vector<double> CampaignBenchmarkEnv::encodeState() const { return encode(engine_->state().observation(), 512); }
std::vector<std::vector<double>> CampaignBenchmarkEnv::encodeLegalActions() const {
    std::vector<std::vector<double>> out; for (const auto &a : legalActions()) out.push_back(encode(actionJson(a), 256)); return out;
}
std::vector<std::string> CampaignBenchmarkEnv::stateFeatureLabels() const { return labels("state", 512); }
std::vector<std::string> CampaignBenchmarkEnv::actionFeatureLabels() const { return labels("action", 256); }
int CampaignBenchmarkEnv::completedTurnsFor(std::string_view nation) const { const auto &m = engine_->state().completedTurns; const auto i = m.find(benchmarkNation(nation)); return i == m.end() ? 0 : i->second; }
int CampaignBenchmarkEnv::nationIncome(std::string_view nation) const { return evaluateIncome(engine_->state(), benchmarkNation(nation)).total; }
int CampaignBenchmarkEnv::nationTreasury(std::string_view nation) const { return engine_->state().nations.at(benchmarkNation(nation)).treasury.value_or(0); }
int CampaignBenchmarkEnv::unitCountFor(std::string_view nation) const { const auto id = benchmarkNation(nation); int count = 0; for (const auto &[uid, u] : engine_->state().units) if (u.owner == id) ++count; return count; }
int CampaignBenchmarkEnv::unitValueFor(std::string_view nation) const { const auto id = benchmarkNation(nation); int value = 0; for (const auto &[uid, u] : engine_->state().units) if (u.owner == id) value += asset(engine_->state(), u.type); return value; }
int CampaignBenchmarkEnv::enemyUnitValueDestroyedByNation(std::string_view nation) const { return flag(engine_->state().nations.at(benchmarkNation(nation)).gameFlags, "benchmark_destroyed_enemy_value"); }
void CampaignBenchmarkEnv::setDiceTapeForTesting(std::vector<int> tape) { engine_->setDiceTapeForTesting(std::move(tape)); }
std::string CampaignBenchmarkEnv::serialize() const { return engine_->serialize(); }
void CampaignBenchmarkEnv::restore(const std::string &snapshot) { engine_ = Engine::restore(initial_.definition, rules_, snapshot); }
void CampaignBenchmarkEnv::useSearchSeed(std::uint64_t seed) { engine_ = engine_->cloneForSearch(seed); }
void CampaignBenchmarkEnv::useOrdinaryEngine() { engine_ = engine_->clone(); }
std::string CompositionBattleEnv::winnerId() const {
    if (!isTerminal()) return "";
    if (unitCountFor("Attacker") && !unitCountFor("Defender")) return "Attacker";
    if (unitCountFor("Defender") && !unitCountFor("Attacker")) return "Defender";
    // Retreat leaves surviving attackers at their origin; possession decides.
    if (unitCountFor("Attacker") && unitCountFor("Defender")) return "Defender";
    return "";
}
double CompositionBattleEnv::finalReward() const {
    if (!isTerminal()) return 0.0;
    const auto winner = winnerId(); const auto &s = engine_->state();
    return (winner == "Attacker" ? 1.0 : winner == "Defender" ? -1.0 : 0.0) +
        0.1 * (flag(s.nations.at("kmt").gameFlags, "benchmark_lost_value") - flag(s.nations.at("japan").gameFlags, "benchmark_lost_value"));
}
double CompositionBattleEnv::terminalRewardFor(std::string_view nation) const {
    const auto id = benchmarkNation(nation);
    if (id != "japan" && id != "kmt") throw std::runtime_error("Unknown composition side");
    return id == "japan" ? finalReward() : -finalReward();
}
int CompositionBattleEnv::purchasedUnitCount(std::string_view nation, UnitKind kind) const {
    return flag(engine_->state().nations.at(benchmarkNation(nation)).gameFlags, "benchmark_purchased:" + unitType(game::toString(kind)));
}
int CompositionBattleEnv::budgetRemaining(std::string_view nation) const {
    const auto id = benchmarkNation(nation);
    const auto &flags = engine_->state().nations.at(id).gameFlags;
    const auto i = flags.find("benchmark_unspent_budget");
    return i == flags.end() ? nationTreasury(nation) : i->second;
}
} // namespace game
