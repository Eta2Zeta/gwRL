#include "game/economy.hpp"
#include "game/catalog.hpp"
#include "game/movement.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <limits>
#include <numeric>
#include <stdexcept>

namespace game::campaign {
namespace {
using V = json::Value;
using O = V::Object;
void require(bool yes, const std::string &why) {
    if (!yes)
        throw std::runtime_error(why);
}
V number(int x) {
    return V(static_cast<double>(x));
}
int value(const std::map<Id, int> &flags, const Id &key) {
    const auto i = flags.find(key);
    return i == flags.end() ? 0 : i->second;
}
bool flag(const std::map<Id, int> &flags, const Id &key) {
    return value(flags, key) != 0;
}
const V &node(const State &s, const Id &zone) {
    return s.definition->geography.require("nodes").require(zone);
}
bool home(const State &s, const Id &nation, const Id &zone) {
    return s.definition->factions.at(nation).homeCountry.contains(zone);
}
bool city(const State &s, const Id &zone) {
    const auto *v = node(s, zone).find("is_city");
    return v && v->asBool();
}
bool facilityType(const State &s, const Id &type) {
    return s.definition->catalog->facilities().contains(type);
}
bool naval(const State &s, const Id &type) {
    return !facilityType(s, type) && s.definition->catalog->unit(type).classes.contains("naval");
}
bool capitalShip(const State &s, const Id &type) {
    return !facilityType(s, type) && s.definition->catalog->unit(type).classes.contains("capital_ship");
}
bool factory(const Id &type) {
    return type == "minor_factory" || type == "medium_factory" || type == "major_factory";
}
bool navalFacility(const Id &type) {
    return type.find("port") != Id::npos || type.find("dockyard") != Id::npos ||
           type.find("shipyard") != Id::npos;
}
int serial(const State &s) {
    require(s.clock.playerTurnSerial < std::numeric_limits<int>::max(), "Economy turn serial overflow");
    return static_cast<int>(s.clock.playerTurnSerial) + 1;
}
Id unique(State &s, const Id &prefix) {
    return "economy_" + prefix + "_" + std::to_string(++s.flags["economy_sequence"]);
}
Action action(const State &s, const Id &kind, O args = {}) {
    Action a;
    a.kind = kind;
    a.nation = s.currentNation();
    a.player = politicalPlayer(s, a.nation);
    a.parameters = V(std::move(args));
    a.id = kind + ":" + contentDigest(canonicalJson(a.parameters));
    return a;
}
void debit(State &s, const Id &nation, int amount) {
    auto &cash = s.nations.at(nation).treasury;
    require(amount >= 0 && cash && *cash >= amount, "Insufficient IPP");
    *cash -= amount;
}
bool ownsHeld(const State &s, const Id &nation, const Id &zone) {
    return s.territories.contains(zone) && s.territories.at(zone).possessor == nation &&
           heldSinceTurnStart(s, nation, zone, false);
}
std::vector<Id> neighbors(const State &s, const Id &zone, bool landOnly = false, bool seaOnly = false) {
    std::vector<Id> out;
    for (const auto &edge : node(s, zone).require("neighbors").asArray()) {
        const auto id = edge.require("neighbor_id").asString();
        const bool land = s.territories.contains(id);
        if ((landOnly && !land) || (seaOnly && land))
            continue;
        out.push_back(id);
    }
    return out;
}
const V *edge(const State &s, const Id &from, const Id &to) {
    for (const auto &e : node(s, from).require("neighbors").asArray())
        if (e.require("neighbor_id").asString() == to)
            return &e;
    return nullptr;
}
bool harshRail(const State &s, const Id &from, const Id &to) {
    const auto *e = edge(s, from, to);
    if (!e)
        return false;
    const auto *t = e->find("border_terrain");
    if (!t || t->isNull())
        return false;
    const std::set<Id> harsh{"desert", "jungle", "marsh", "mountain", "tundra", "tundra_ice"};
    if (t->isString())
        return harsh.contains(t->asString());
    if (t->isArray())
        for (const auto &a : t->asArray())
            if (harsh.contains(a.asString()))
                return true;
    return false;
}
std::optional<Id> marker(const std::map<Id, int> &flags, const Id &prefix) {
    for (const auto &[key, n] : flags)
        if (n && key.rfind(prefix, 0) == 0)
            return key.substr(prefix.size());
    return std::nullopt;
}
const BuildChartRow *projectRow(const State &s, const BuildProject &p) {
    if (const auto id = marker(p.flags, "row:"))
        return &s.definition->catalog->row(*id);
    const auto &status = s.nations.at(p.owner).powerStatus;
    for (const auto &[id, r] : s.definition->catalog->rows())
        if (r.nation == p.owner && r.powerStatus == status && r.type == p.type && r.kind == "purchase")
            return &r;
    return nullptr;
}
bool ready(const BuildProject &p) {
    return p.remainingPayments.empty() || flag(p.flags, "completed");
}
int slotsUsed(const State &s, const Id &nation, const Id &facility) {
    return value(s.nations.at(nation).turnFlags, "economy_used:" + facility);
}
int capacity(const State &s, const Id &nation, const Id &facility, bool repair) {
    const auto &f = s.facilities.at(facility);
    const auto owner = s.territories.at(f.zone).possessor;
    if (!owner || (!repair && *owner != nation))
        return 0;
    if (repair && *owner != nation && !politicallyFriendly(s, nation, *owner))
        return 0;
    if (!heldSinceTurnStart(s, nation, f.zone, repair) || flag(f.flags, "placed_this_turn") ||
        flag(f.flags, "moved_this_turn"))
        return 0;
    if (!inSupply(s, nation, f.zone))
        return 0;
    if (navalFacility(f.type) && !navalFacilityUsable(s, nation, facility, true))
        return 0;
    const auto &catalog = *s.definition->catalog;
    const auto ctx = catalogContext(s, nation, f.zone);
    const int current = repair ? catalog.repairCapacity(f.type, f.damage, ctx)
                               : catalog.productionCapacity(f.type, f.damage, ctx);
    const auto &flags = s.nations.at(nation).turnFlags;
    const auto key = (repair ? "economy_repair_cap:" : "economy_production_cap:") + facility;
    const auto i = flags.find(key);
    int snapshot = i == flags.end() ? 0 : i->second;
    if (const auto original = marker(flags, "economy_start_type:" + facility + ":")) {
        const int damage = value(flags, "economy_start_damage:" + facility);
        snapshot = repair ? catalog.repairCapacity(*original, damage, ctx)
                          : catalog.productionCapacity(*original, damage, ctx);
    }
    return std::max(0, std::min(snapshot, current) - slotsUsed(s, nation, facility));
}
int totalCapacity(const State &s, const Id &nation, bool ships, bool capitals = false) {
    int sum = 0;
    for (const auto &[id, f] : s.facilities)
        if (ships ? (capitals ? f.type == "major_shipyard" : f.type.find("shipyard") != Id::npos)
                  : factory(f.type))
            sum += capacity(s, nation, id, false);
    return sum;
}
int queuedCapacity(const State &s, const Id &nation, bool ships, bool capitals = false) {
    int n = 0;
    for (const auto &[id, p] : s.construction)
        if (p.owner == nation && ready(p) && !facilityType(s, p.type) && !marker(p.flags, "target:") &&
            !flag(p.flags, "unit_upgrade") && !flag(p.flags, "facility_upgrade") && p.type != "militia" &&
            !flag(p.flags, "lease_received")) {
            const bool ship = naval(s, p.type);
            if (ship != ships || (capitals && !capitalShip(s, p.type)))
                continue;
            const auto &u = s.definition->catalog->unit(p.type);
            if (!ship && decentralizedProduction(s, nation) &&
                (u.classes.contains("infantry_class") || p.type == "cavalry"))
                continue;
            ++n;
        }
    return n;
}
bool canFactoryBuy(const State &s, const Id &nation, const Id &type, bool completion) {
    if (facilityType(s, type) || type == "militia")
        return true;
    const auto &u = s.definition->catalog->unit(type);
    if (!naval(s, type) && decentralizedProduction(s, nation) &&
        (u.classes.contains("infantry_class") || type == "cavalry"))
        return true;
    if (naval(s, type)) {
        if (!completion)
            return totalCapacity(s, nation, true, capitalShip(s, type)) > 0;
        return queuedCapacity(s, nation, true) < totalCapacity(s, nation, true) &&
               (!capitalShip(s, type) ||
                queuedCapacity(s, nation, true, true) < totalCapacity(s, nation, true, true));
    }
    return queuedCapacity(s, nation, false) < totalCapacity(s, nation, false);
}
int militiaAllowance(const State &s, const Id &nation, const Id &zone) {
    if (!ownsHeld(s, nation, zone))
        return 0;
    const int limit = std::max(1, effectiveTerritorialIpp(s, zone));
    int left = std::min(limit, originalNation(s, zone) == nation ? limit : 1) -
               value(s.nations.at(nation).turnFlags, "economy_militia_placed:" + zone);
    if (s.nations.at(nation).powerStatus == "major" && !home(s, nation, zone)) {
        int present = 0;
        for (const auto &[id, u] : s.units)
            if (u.owner == nation && u.zone == zone && u.type == "militia")
                ++present;
        left = std::min(left, limit - present);
    }
    return std::max(0, left);
}
bool siteLegal(const State &s, const BuildChartRow &r, const Id &zone, const std::optional<Id> &border = {},
               const std::optional<Id> &exclude = {}, bool foreignRequest = false) {
    if (!ownsHeld(s, r.nation, zone))
        return false;
    if (r.placement.contains("home_country") && !home(s, r.nation, zone))
        return false;
    if (r.placement.contains("coastal_border") &&
        (!border || s.territories.contains(*border) || !edge(s, zone, *border)))
        return false;
    if (r.placement.contains("land_or_sea_border") && (!border || !edge(s, zone, *border)))
        return false;
    auto count = [&](const Id &type, bool major) {
        int n = 0;
        for (const auto &[id, f] : s.facilities)
            if (f.zone == zone && (!exclude || id != *exclude) &&
                ((type.empty() && navalFacility(f.type) && (f.type.rfind("major_", 0) == 0) == major) ||
                 f.type == type))
                ++n;
        for (const auto &[id, p] : s.construction)
            if ((!exclude || id != *exclude) && p.site == zone && p.type == type &&
                !marker(p.flags, "target:"))
                ++n;
        return n;
    };
    if (r.placement.contains("airbase_per_zone_limit") && count("airbase", false))
        return false;
    if (r.placement.contains("facility_city_naval_limit") && city(s, zone)) {
        const bool major = r.type.rfind("major_", 0) == 0;
        for (const auto &[id, f] : s.facilities)
            if (f.zone == zone && (!exclude || id != *exclude) && navalFacility(f.type) &&
                (f.type.rfind("major_", 0) == 0) == major)
                return false;
        for (const auto &[id, p] : s.construction)
            if ((!exclude || id != *exclude) && p.site == zone && navalFacility(p.type) &&
                (p.type.rfind("major_", 0) == 0) == major && !marker(p.flags, "target:"))
                return false;
    }
    if (r.type == "fortification" && border) {
        for (const auto &[id, f] : s.facilities)
            if (f.type == "fortification" && f.zone == zone && flag(f.flags, "border:" + *border))
                return false;
        for (const auto &[id, p] : s.construction)
            if ((!exclude || id != *exclude) && p.type == "fortification" && p.site == zone &&
                flag(p.flags, "border:" + *border))
                return false;
    }
    if (r.type == "railroad") {
        if (!border || !s.territories.contains(*border) || !passableLandBorder(s, zone, *border))
            return false;
        const auto owner = s.territories.at(*border).possessor;
        if (!owner)
            return false;
        if (*owner != r.nation) {
            if (s.nations.at(r.nation).atWarWith.contains(*owner) || !s.nations.at(*owner).player)
                return false;
            const auto permission = "rail_build_permission:" + *owner + ":" + zone + ":" + *border;
            if (!foreignRequest && value(s.nations.at(r.nation).turnFlags, permission) != serial(s))
                return false;
        }
        for (const auto &[id, rail] : s.rails)
            if ((rail.endpointA == zone && rail.endpointB == *border) ||
                (rail.endpointA == *border && rail.endpointB == zone))
                return false;
        for (const auto &[id, p] : s.construction)
            if ((!exclude || id != *exclude) && p.type == "railroad" &&
                ((p.site == zone && flag(p.flags, "border:" + *border)) ||
                 (p.site == *border && flag(p.flags, "border:" + zone))))
                return false;
        if (harshRail(s, zone, *border) != r.placement.contains("railroad_route_cost_4"))
            return false;
    }
    return true;
}
bool upgradeFacilityLegal(const State &s, const BuildChartRow &row, const FacilityState &f) {
    auto border = marker(f.flags, "border:");
    if (!border) {
        const auto seas = navalFacilitySeaZones(s, f.id);
        if (!seas.empty())
            border = seas.front();
    }
    return s.territories.at(f.zone).possessor == row.nation && row.upgradesFrom == f.type &&
           !flag(f.flags, "moved_this_turn") && siteLegal(s, row, f.zone, border, f.id);
}
void copyMetadata(BuildProject &p, const BuildChartRow &row, const PriceOption &price) {
    p.flags["row:" + row.id] = 1;
    p.flags["price:" + price.method] = 1;
    p.flags["stages_total"] = static_cast<int>(price.payments.size());
    p.flags["stages_paid"] = 1;
    for (std::size_t i = 0; i < price.payments.size(); ++i)
        p.flags["payment:" + std::to_string(i)] = price.payments[i];
}
std::vector<Action> placements(const State &s, const BuildProject &p) {
    std::vector<Action> out;
    const auto n = p.owner;
    if (n != s.currentNation() || !ready(p))
        return out;
    if (marker(p.flags, "lend_to:") || flag(p.flags, "lease_received"))
        return out;
    const auto *row = projectRow(s, p);
    if (flag(p.flags, "unit_upgrade") && row) {
        for (const auto &[id, u] : s.units)
            if (u.owner == n && row->upgradesFrom == u.type && !flag(u.turnFlags, "placed_this_turn") &&
                inSupply(s, n, u.zone) &&
                (u.type != "militia" || value(s.nations.at(n).turnFlags, "economy_militia_upgrades") < 2))
                out.push_back(action(s, "economy_place", {{"project", V(p.id)}, {"target", V(id)}}));
        return out;
    }
    if (flag(p.flags, "facility_upgrade") && row) {
        for (const auto &[id, f] : s.facilities)
            if (upgradeFacilityLegal(s, *row, f) && inSupply(s, n, f.zone))
                out.push_back(action(s, "economy_place", {{"project", V(p.id)}, {"target", V(id)}}));
        return out;
    }
    const auto target = marker(p.flags, "target:");
    if (target) {
        const auto unit = s.units.find(*target);
        const auto fac = s.facilities.find(*target);
        if (unit != s.units.end() && unit->second.owner == n &&
            !flag(unit->second.turnFlags, "placed_this_turn") && inSupply(s, n, unit->second.zone) && row &&
            row->upgradesFrom == unit->second.type &&
            (unit->second.type != "militia" ||
             value(s.nations.at(n).turnFlags, "economy_militia_upgrades") < 2))
            out.push_back(action(s, "economy_place", {{"project", V(p.id)}, {"target", V(*target)}}));
        if (fac != s.facilities.end() && s.territories.at(fac->second.zone).possessor == n &&
            inSupply(s, n, fac->second.zone) && row && row->upgradesFrom == fac->second.type)
            out.push_back(action(s, "economy_place", {{"project", V(p.id)}, {"target", V(*target)}}));
        return out;
    }
    if (facilityType(s, p.type)) {
        if (p.site && s.territories.contains(*p.site) && ownsHeld(s, n, *p.site) &&
            !value(p.flags, "damage")) {
            const auto border = marker(p.flags, "border:");
            std::optional<Id> foreign;
            if (border && s.territories.contains(*border))
                foreign = s.territories.at(*border).possessor;
            const bool approved = foreign && flag(p.flags, "foreign_consent:" + *foreign);
            if (!row || siteLegal(s, *row, *p.site, border, p.id, approved))
                out.push_back(action(s, "economy_place", {{"project", V(p.id)}, {"zone", V(*p.site)}}));
            else if (row->type == "railroad" && foreign && *foreign != n &&
                     !value(s.nations.at(n).turnFlags, "rail_declined:" + p.id) &&
                     siteLegal(s, *row, *p.site, border, p.id, true))
                out.push_back(action(s, "economy_request_rail",
                                     {{"project", V(p.id)}, {"zone", V(*p.site)}, {"border", V(*border)}}));
        }
        return out;
    }
    for (const auto &[zone, t] : s.territories) {
        if (!ownsHeld(s, n, zone))
            continue;
        if (p.type == "militia") {
            if (militiaAllowance(s, n, zone) > 0)
                out.push_back(action(s, "economy_place", {{"project", V(p.id)}, {"zone", V(zone)}}));
            continue;
        }
        const auto &unit = s.definition->catalog->unit(p.type);
        if (decentralizedProduction(s, n) && chineseHomeCountry(s, zone) &&
            (unit.classes.contains("infantry_class") || p.type == "cavalry")) {
            out.push_back(action(s, "economy_place", {{"project", V(p.id)}, {"zone", V(zone)}}));
            continue;
        }
        for (const auto &[id, f] : s.facilities)
            if (f.zone == zone && capacity(s, n, id, false) > 0) {
                if (naval(s, p.type)) {
                    if (f.type.find("shipyard") == Id::npos ||
                        (capitalShip(s, p.type) && f.type != "major_shipyard"))
                        continue;
                    for (const auto &sea : navalFacilitySeaZones(s, id))
                        out.push_back(action(s, "economy_place",
                                             {{"project", V(p.id)}, {"zone", V(sea)}, {"facility", V(id)}}));
                    if (f.type == "major_shipyard" && !unit.classes.contains("submarine"))
                        out.push_back(action(s, "economy_place",
                                             {{"project", V(p.id)},
                                              {"zone", V(zone)},
                                              {"facility", V(id)},
                                              {"in_port", V(true)}}));
                } else if (factory(f.type))
                    out.push_back(action(s, "economy_place",
                                         {{"project", V(p.id)}, {"zone", V(zone)}, {"facility", V(id)}}));
            }
    }
    return out;
}
} // namespace

int effectiveTerritorialIpp(const State &s, const Id &zone) {
    const auto &flags = s.territories.at(zone).flags;
    return std::max(0, node(s, zone).require("ipp_value").asInt() -
                           std::max(value(flags, "city_ipp_lost"), value(flags, "city_damage") / 20));
}
IncomeBreakdown evaluateIncome(const State &s, const Id &nation) {
    IncomeBreakdown out;
    const auto &n = s.nations.at(nation);
    const bool account = nation == "japan" || nation == "kmt" || nation == "ccp" || n.powerStatus == "major";
    if (!account || !n.treasury || s.politics.surrendered.contains(nation))
        return out;
    const auto cap = s.politics.capitals.find(nation);
    out.collectable = n.powerStatus != "major" ||
                      (cap != s.politics.capitals.end() && s.territories.at(cap->second).possessor == nation);
    int territorial = 0;
    for (const auto &[zone, t] : s.territories)
        if (t.possessor == nation)
            territorial += effectiveTerritorialIpp(s, zone);
    out.components["territorial"] = territorial;
    if (nation == "japan") {
        int bonus = 0;
        for (const auto &zone : {"land_china_beiping", "land_china_hopeh", "land_china_shantung",
                                 "land_china_nanking", "land_china_hunan", "land_kwangtung"})
            if (s.territories.contains(zone) && s.territories.at(zone).possessor == nation)
                ++bonus;
        out.components["china_control_bonus"] = bonus;
    }
    // Oil trade, Burma Road and Soviet-Home-Country bonuses have absent actors
    // or cut routes in this closed profile. No historical outside ledger exists.
    for (const auto &[id, n] : out.components)
        out.total += n;
    if (!out.collectable)
        out.total = 0;
    return out;
}
void refreshIncome(State &s) {
    for (auto &[id, n] : s.nations) {
        const auto rate = evaluateIncome(s, id);
        n.incomeComponents = rate.components;
        n.incomeKnown = true;
    }
}
void reconcileCapturedFacilities(State &s, const Id &zone, const std::optional<Id> &oldOwner,
                                 const Id &newOwner) {
    for (auto &[id, f] : s.facilities)
        if (f.zone == zone && factory(f.type)) {
            if (!marker(f.flags, "original_owner:"))
                f.flags["original_owner:" + oldOwner.value_or(originalNation(s, zone))] = 1;
            if (!marker(f.flags, "original_type:"))
                f.flags["original_type:" + f.type] = 1;
            const auto originalType = *marker(f.flags, "original_type:");
            if (marker(f.flags, "original_owner:") == newOwner) {
                f.type = originalType;
                f.flags.erase("captured_max_damage");
            } else if (originalType == "medium_factory" || originalType == "major_factory") {
                f.type = "minor_factory";
                f.flags["captured_max_damage"] =
                    s.definition->catalog->facility(originalType).maxDamage.value();
            }
        }
}
int facilityCapacity(const State &s, const Id &nation, const Id &facility, bool repair) {
    return capacity(s, nation, facility, repair);
}
void beginEconomyTurn(State &s) {
    auto &n = s.nations.at(s.currentNation());
    for (auto &[id, f] : s.facilities)
        if (s.territories.at(f.zone).possessor == s.currentNation()) {
            f.flags.erase("placed_this_turn");
            f.flags.erase("upgraded_this_turn");
            f.flags.erase("moved_this_turn");
            f.flags.erase("researched_this_turn");
        }
    for (const auto &[id, f] : s.facilities) {
        const auto owner = s.territories.at(f.zone).possessor;
        if (!owner || (*owner != s.currentNation() && !politicallyFriendly(s, s.currentNation(), *owner)))
            continue;
        const auto context = catalogContext(s, s.currentNation(), f.zone);
        n.turnFlags["economy_start_type:" + id + ":" + f.type] = 1;
        n.turnFlags["economy_start_damage:" + id] = f.damage;
        n.turnFlags["economy_production_cap:" + id] =
            s.definition->catalog->productionCapacity(f.type, f.damage, context);
        n.turnFlags["economy_repair_cap:" + id] =
            s.definition->catalog->repairCapacity(f.type, f.damage, context);
    }
    int research = 0;
    for (const auto &[id, f] : s.facilities)
        if (f.type == "major_factory" && f.damage == 0 &&
            s.territories.at(f.zone).possessor == s.currentNation() && !flag(f.flags, "placed_this_turn"))
            ++research;
    n.turnFlags["economy_research_capacity"] = n.powerStatus == "major" ? research : 0;
    n.turnFlags["economy_research_finished"] = research == 0 || n.powerStatus != "major";
    refreshIncome(s);
}
void damageConstruction(State &s, const Id &id, int damage) {
    require(damage >= 0, "Negative construction damage");
    auto &p = s.construction.at(id);
    require(facilityType(s, p.type) && p.type != "fortification" && p.type != "coastal_artillery",
            "Not a bombable construction project");
    int combined = value(p.flags, "damage") + damage;
    int paid = value(p.flags, "stages_paid");
    if (!paid)
        paid = std::max(1, value(p.flags, "stages_total") - static_cast<int>(p.remainingPayments.size()));
    while (combined >= 3) {
        if (paid <= 1) {
            s.construction.erase(id);
            for (auto it = s.repairs.begin(); it != s.repairs.end();)
                if (it->second.target == id)
                    it = s.repairs.erase(it);
                else
                    ++it;
            return;
        }
        --paid;
        const auto payment = value(p.flags, "payment:" + std::to_string(paid));
        p.remainingPayments.insert(p.remainingPayments.begin(), payment);
        combined -= 3;
    }
    p.flags["stages_paid"] = paid;
    p.flags["damage"] = combined;
    if (!p.remainingPayments.empty())
        p.flags.erase("completed");
    p.queuePosition = std::max(1, static_cast<int>(p.remainingPayments.size()) + 1);
}

std::vector<Action> economyActions(const State &s) {
    std::vector<Action> out;
    if (s.chance || s.terminal)
        return out;
    if (!s.decisions.empty()) {
        if (s.decisions.back().kind == "economy_rail_permission")
            return s.decisions.back().options;
        return out;
    }
    const auto nation = s.currentNation();
    const auto &n = s.nations.at(nation);
    const auto &catalog = *s.definition->catalog;
    if (s.clock.phase == Phase::PlaceUnits) {
        for (const auto &[id, p] : s.construction) {
            auto options = placements(s, p);
            out.insert(out.end(), options.begin(), options.end());
        }
        return out;
    }
    if (s.clock.phase != Phase::Production || !n.treasury || s.politics.surrendered.contains(nation))
        return out;
    if (!flag(n.turnFlags, "economy_research_finished")) {
        if (value(n.turnFlags, "economy_research_used") < value(n.turnFlags, "economy_research_capacity"))
            for (const auto &[id, t] : catalog.technologies()) {
                const int stage = value(n.technologyStages, id);
                if (stage >= 4 ||
                    (stage == 2 && s.calendarDate().first * 100 + s.calendarDate().second < t.stageThreeFrom))
                    continue;
                if (value(n.gameFlags, "economy_researched_round:" + id) == s.clock.roundIndex + 1)
                    continue;
                for (const auto &[facility, f] : s.facilities)
                    if (f.type == "major_factory" && f.damage == 0 &&
                        s.territories.at(f.zone).possessor == nation && !flag(f.flags, "placed_this_turn") &&
                        !flag(f.flags, "moved_this_turn") && !flag(f.flags, "researched_this_turn"))
                        out.push_back(action(s, "economy_research",
                                             {{"technology", V(id)}, {"facility", V(facility)}}));
            }
        out.push_back(action(s, "economy_finish_research"));
        return out;
    }
    auto ctx = catalogContext(s, nation);
    for (const auto &r : catalog.purchaseOptions(ctx))
        for (const auto &price : catalog.priceOptions(r.id, ctx)) {
            if (price.payments.empty() || price.payments.front() > *n.treasury)
                continue;
            const auto base = O{{"row", V(r.id)}, {"price", V(price.method)}};
            if (r.kind == "upgrade") {
                if (!facilityType(s, r.type) &&
                    std::any_of(s.units.begin(), s.units.end(), [&](const auto &item) {
                        const auto &u = item.second;
                        return u.owner == nation && r.upgradesFrom == u.type &&
                               !flag(u.turnFlags, "placed_this_turn");
                    }))
                    out.push_back(action(s, "economy_purchase", base));
                if (facilityType(s, r.type) &&
                    std::any_of(s.facilities.begin(), s.facilities.end(),
                                [&](const auto &item) { return upgradeFacilityLegal(s, r, item.second); }))
                    out.push_back(action(s, "economy_purchase", base));
                continue;
            }
            if (!canFactoryBuy(s, nation, r.type, price.payments.size() == 1))
                continue;
            if (facilityType(s, r.type)) {
                for (const auto &[zone, t] : s.territories) {
                    if (r.placement.contains("coastal_border") ||
                        r.placement.contains("land_or_sea_border") || r.type == "railroad")
                        for (const auto &border : neighbors(s, zone)) {
                            const bool legal = siteLegal(s, r, zone, border);
                            const bool request =
                                r.type == "railroad" && !legal && siteLegal(s, r, zone, border, {}, true);
                            if (!legal && !request)
                                continue;
                            auto args = base;
                            args["zone"] = V(zone);
                            args["border"] = V(border);
                            out.push_back(
                                action(s, request ? "economy_request_rail" : "economy_purchase", args));
                            if (legal && (navalFacility(r.type) || r.type == "seaplane_base" ||
                                          r.type == "submarine_base"))
                                for (const auto &second : neighbors(s, zone, false, true))
                                    if (border < second) {
                                        auto dual = args;
                                        dual["border2"] = V(second);
                                        out.push_back(action(s, "economy_purchase", std::move(dual)));
                                    }
                        }
                    else if (siteLegal(s, r, zone)) {
                        auto args = base;
                        args["zone"] = V(zone);
                        out.push_back(action(s, "economy_purchase", std::move(args)));
                    }
                }
            } else {
                int available = 0, queued = 0;
                if (r.type == "militia") {
                    for (const auto &[zone, t] : s.territories)
                        available += militiaAllowance(s, nation, zone);
                    for (const auto &[id, p] : s.construction)
                        if (p.owner == nation && p.type == "militia" && ready(p))
                            ++queued;
                }
                if (r.type != "militia" || queued < available)
                    out.push_back(action(s, "economy_purchase", base));
            }
        }
    for (const auto &[id, p] : s.construction)
        if (p.owner == nation && !ready(p) && !value(p.flags, "damage") &&
            value(p.flags, "economy_last_paid_turn") != serial(s) &&
            p.remainingPayments.front() <= *n.treasury &&
            canFactoryBuy(s, nation, p.type, p.remainingPayments.size() == 1))
            out.push_back(action(s, "economy_advance", {{"project", V(id)}}));
    for (const auto &[id, f] : s.facilities)
        if (s.territories.at(f.zone).possessor == nation && f.damage > 0 &&
            !flag(f.flags, "moved_this_turn") && !s.repairs.contains("repair_" + id))
            for (int damage = 1; damage <= std::min(f.damage, *n.treasury); ++damage)
                out.push_back(action(s, "economy_repair", {{"target", V(id)}, {"damage", number(damage)}}));
    for (const auto &[zone, t] : s.territories)
        if (t.possessor == nation && city(s, zone) && !flag(t.flags, "city_destroyed") &&
            value(t.flags, "city_damage") > 0 && !s.repairs.contains("repair_" + zone))
            for (int damage = 1; damage <= std::min(value(t.flags, "city_damage"), *n.treasury); ++damage)
                out.push_back(action(s, "economy_repair", {{"target", V(zone)}, {"damage", number(damage)}}));
    for (const auto &[id, p] : s.construction)
        if (p.owner == nation && value(p.flags, "damage") > 0 && !s.repairs.contains("repair_" + id))
            for (int damage = 1; damage <= std::min(value(p.flags, "damage"), *n.treasury); ++damage)
                out.push_back(action(s, "economy_repair", {{"target", V(id)}, {"damage", number(damage)}}));
    for (const auto &[id, rail] : s.rails)
        for (const auto &[endpoint, damage] : rail.damageByEndpoint)
            if (damage > 0 && s.territories.at(endpoint).possessor == nation &&
                !s.repairs.contains("repair_" + id + "_" + endpoint))
                for (int count = 1; count <= std::min(damage, *n.treasury); ++count)
                    out.push_back(
                        action(s, "economy_repair",
                               {{"target", V(id)}, {"endpoint", V(endpoint)}, {"damage", number(count)}}));
    for (const auto &[id, u] : s.units)
        if (u.owner == nation && u.damage > 0 && capitalShip(s, u.type) &&
            !s.repairs.contains("repair_" + id))
            for (const auto &[fid, f] : s.facilities) {
                const auto seas = navalFacilitySeaZones(s, fid);
                if (u.zone != f.zone && std::find(seas.begin(), seas.end(), u.zone) == seas.end())
                    continue;
                const auto start = s.turnStart.units.find(id);
                if (start == s.turnStart.units.end() || start->second.second != u.zone ||
                    start->second.first != nation)
                    continue;
                for (int damage = 1; damage <= std::min(u.damage, capacity(s, nation, fid, true)); ++damage)
                    out.push_back(
                        action(s, "economy_repair",
                               {{"target", V(id)}, {"facility", V(fid)}, {"damage", number(damage)}}));
            }
    return out;
}

bool applyEconomyAction(State &s, const Action &a) {
    if (a.kind.rfind("economy_", 0) != 0)
        return false;
    if (applyLendLeaseAction(s, a))
        return true;
    const auto options = economyActions(s);
    require(std::any_of(options.begin(), options.end(),
                        [&](const auto &option) {
                            return canonicalJson(actionJson(option)) == canonicalJson(actionJson(a));
                        }),
            "Illegal economy action");
    if (a.kind == "economy_approve_rail" || a.kind == "economy_decline_rail") {
        require(!s.decisions.empty() && a.decision && s.decisions.back().id == *a.decision,
                "Missing railroad consent");
        const auto payload = pendingPolitical(s, s.decisions.back().continuation);
        erasePoliticalContinuation(s, s.decisions.back().continuation);
        s.decisions.pop_back();
        if (a.kind == "economy_approve_rail") {
            const auto sender = payload.require("sender").asString();
            const auto zone = payload.require("parameters").require("zone").asString();
            const auto border = payload.require("parameters").require("border").asString();
            s.nations.at(sender).turnFlags["rail_build_permission:" + a.nation + ":" + zone + ":" + border] =
                serial(s);
            if (const auto *project = payload.require("parameters").find("project"))
                s.construction.at(project->asString()).flags["foreign_consent:" + a.nation] = 1;
            else {
                const auto original = action(s, "economy_purchase", payload.require("parameters").asObject());
                applyEconomyAction(s, original);
            }
        } else if (const auto *project = payload.require("parameters").find("project"))
            s.nations.at(payload.require("sender").asString())
                .turnFlags["rail_declined:" + project->asString()] = 1;
        return true;
    }
    if (a.kind == "economy_request_rail") {
        const auto border = a.parameters.require("border").asString();
        const auto recipient = *s.territories.at(border).possessor;
        std::vector<Action> choices{politicalAction(s, recipient, "economy_approve_rail"),
                                    politicalAction(s, recipient, "economy_decline_rail")};
        queuePoliticalDecision(s, recipient, "economy_rail_permission", std::move(choices),
                               V(O{{"sender", V(a.nation)}, {"parameters", a.parameters}}));
        return true;
    }
    auto &n = s.nations.at(a.nation);
    const auto &catalog = *s.definition->catalog;
    if (a.kind == "economy_finish_research") {
        n.turnFlags["economy_research_finished"] = 1;
        return true;
    }
    if (a.kind == "economy_research") {
        const auto tech = a.parameters.require("technology").asString();
        const int stage = value(n.technologyStages, tech);
        s.facilities.at(a.parameters.require("facility").asString()).flags["researched_this_turn"] = 1;
        ++n.turnFlags["economy_research_used"];
        n.gameFlags["economy_researched_round:" + tech] = s.clock.roundIndex + 1;
        ChanceRequest request;
        request.id = unique(s, "research");
        request.purpose = "economy_research:" + tech;
        request.nation = a.nation;
        request.continuation = tech;
        request.dice = {DieSpec{12, 0, {}, 0}};
        s.chance = std::move(request);
        (void)stage;
        return true;
    }
    if (a.kind == "economy_purchase") {
        const auto &r = catalog.row(a.parameters.require("row").asString());
        const auto prices = catalog.priceOptions(r.id, catalogContext(s, a.nation));
        const auto method = a.parameters.require("price").asString();
        const auto price =
            std::find_if(prices.begin(), prices.end(), [&](const auto &x) { return x.method == method; });
        require(price != prices.end(), "Unknown price option");
        debit(s, a.nation, price->payments.front());
        BuildProject p;
        p.id = unique(s, r.type);
        p.owner = a.nation;
        p.type = r.type;
        p.paidIpp = price->payments.front();
        p.remainingPayments.assign(price->payments.begin() + 1, price->payments.end());
        p.queuePosition = std::max(1, static_cast<int>(p.remainingPayments.size()) + 1);
        copyMetadata(p, r, *price);
        p.flags["economy_last_paid_turn"] = serial(s);
        p.flags["economy_purchased"] = 1;
        if (const auto *zone = a.parameters.find("zone"))
            p.site = zone->asString();
        if (const auto *border = a.parameters.find("border"))
            p.flags["border:" + border->asString()] = 1;
        if (const auto *border = a.parameters.find("border2"))
            p.flags["border:" + border->asString()] = 1;
        if (r.type == "railroad")
            if (const auto border = marker(p.flags, "border:")) {
                const auto owner = s.territories.at(*border).possessor;
                if (owner && *owner != a.nation)
                    p.flags["foreign_consent:" + *owner] = 1;
            }
        if (r.kind == "upgrade")
            p.flags[facilityType(s, r.type) ? "facility_upgrade" : "unit_upgrade"] = 1;
        if (const auto *target = a.parameters.find("target")) {
            p.flags["target:" + target->asString()] = 1;
            if (s.facilities.contains(target->asString()))
                p.site = target->asString();
        }
        if (ready(p))
            p.flags["completed"] = 1;
        s.construction.emplace(p.id, std::move(p));
        ++n.turnFlags["purchased:" + r.capGroup.value_or(r.id)];
        return true;
    }
    if (a.kind == "economy_advance") {
        auto &p = s.construction.at(a.parameters.require("project").asString());
        const int payment = p.remainingPayments.front();
        debit(s, a.nation, payment);
        p.paidIpp += payment;
        p.remainingPayments.erase(p.remainingPayments.begin());
        p.queuePosition = std::max(1, static_cast<int>(p.remainingPayments.size()) + 1);
        ++p.flags["stages_paid"];
        p.flags["economy_last_paid_turn"] = serial(s);
        if (ready(p))
            p.flags["completed"] = 1;
        return true;
    }
    if (a.kind == "economy_repair") {
        const auto target = a.parameters.require("target").asString();
        const int damage = a.parameters.require("damage").asInt();
        const bool ship = s.units.contains(target);
        if (!ship)
            debit(s, a.nation, damage);
        RepairJob job;
        job.id = "repair_" + target;
        job.owner = a.nation;
        job.target = target;
        job.remainingDamage = damage;
        job.remainingCost = 0;
        job.restrictsAction = ship;
        if (const auto *endpoint = a.parameters.find("endpoint")) {
            job.id += "_" + endpoint->asString();
            job.endpoint = endpoint->asString();
        }
        s.repairs.emplace(job.id, job);
        if (ship) {
            auto &u = s.units.at(target);
            u.turnFlags["repairing"] = 1;
            u.commitments.insert("repair");
            const auto facility = a.parameters.require("facility").asString();
            u.turnFlags["repair_at:" + facility] = 1;
            n.turnFlags["economy_used:" + facility] += damage;
        }
        return true;
    }
    if (a.kind == "economy_place") {
        const auto id = a.parameters.require("project").asString();
        const auto p = s.construction.at(id);
        if (const auto target = (flag(p.flags, "unit_upgrade") || flag(p.flags, "facility_upgrade"))
                                    ? std::optional<Id>(a.parameters.require("target").asString())
                                    : marker(p.flags, "target:")) {
            if (s.units.contains(*target)) {
                auto &u = s.units.at(*target);
                if (u.type == "militia")
                    ++n.turnFlags["economy_militia_upgrades"];
                u.type = p.type;
                const auto stats = catalog.stats(u.type, u.damage, catalogContext(s, u.owner, u.zone));
                u.movementAllowance = stats.movement;
                u.movementRemaining = 0;
            } else {
                auto &f = s.facilities.at(*target);
                f.type = p.type;
                f.flags["upgraded_this_turn"] = 1;
                if (!flag(f.flags, "captured_max_damage")) {
                    for (auto it = f.flags.begin(); it != f.flags.end();)
                        if (it->first.rfind("original_type:", 0) == 0)
                            it = f.flags.erase(it);
                        else
                            ++it;
                    f.flags["original_type:" + p.type] = 1;
                }
            }
        } else if (facilityType(s, p.type)) {
            const auto zone = *p.site;
            if (p.type == "railroad") {
                RailState rail;
                rail.id = unique(s, "rail");
                rail.endpointA = zone;
                rail.endpointB = *marker(p.flags, "border:");
                rail.damageByEndpoint[rail.endpointA] = rail.damageByEndpoint[rail.endpointB] = 0;
                s.flags["logistics_rail_created_turn:" + rail.id] = serial(s);
                s.rails.emplace(rail.id, std::move(rail));
            } else {
                FacilityState f;
                f.id = unique(s, "facility");
                f.type = p.type;
                f.zone = zone;
                f.flags["placed_this_turn"] = 1;
                f.flags["original_owner:" + p.owner] = 1;
                f.flags["original_type:" + p.type] = 1;
                for (const auto &[key, v] : p.flags)
                    if (key.rfind("border:", 0) == 0)
                        f.flags[key] = v;
                s.facilities.emplace(f.id, std::move(f));
            }
        } else {
            UnitState u;
            u.id = unique(s, "unit");
            u.type = p.type;
            u.owner = p.owner;
            u.zone = a.parameters.require("zone").asString();
            u.turnOrigin = u.zone;
            u.movementAllowance = catalog.stats(u.type, 0, catalogContext(s, u.owner, u.zone)).movement;
            u.movementRemaining = 0;
            u.turnFlags["placed_this_turn"] = 1;
            if (const auto *f = a.parameters.find("facility")) {
                ++n.turnFlags["economy_used:" + f->asString()];
                if (const auto *port = a.parameters.find("in_port"))
                    if (port->asBool())
                        u.gameFlags["in_port:" + f->asString()] = 1;
            }
            if (u.type == "militia")
                ++n.turnFlags["economy_militia_placed:" + u.zone];
            s.units.emplace(u.id, std::move(u));
        }
        s.construction.erase(id);
        return true;
    }
    throw std::runtime_error("Unhandled economy action");
}
bool applyEconomyChance(State &s, const ChanceRequest &request, const ChanceOutcome &outcome) {
    if (request.purpose.rfind("economy_research:", 0) != 0)
        return false;
    const auto tech = request.purpose.substr(17);
    auto &n = s.nations.at(request.nation);
    auto &stage = n.technologyStages[tech];
    const int face = effectiveResults(request, outcome).at(0);
    if (face <= s.definition->catalog->technology(tech).thresholds.at(static_cast<std::size_t>(stage))) {
        ++stage;
        if (stage == 4)
            for (auto &[id, u] : s.units)
                if (u.owner == request.nation) {
                    const auto conversions = s.definition->catalog->automaticConversions(
                        u.type, catalogContext(s, u.owner, u.zone));
                    if (!conversions.empty())
                        u.type = conversions.front().to;
                    const auto stats =
                        s.definition->catalog->stats(u.type, u.damage, catalogContext(s, u.owner, u.zone));
                    const int used = u.movementAllowance && u.movementRemaining
                                         ? *u.movementAllowance - *u.movementRemaining
                                         : 0;
                    u.movementAllowance = stats.movement;
                    if (stats.movement)
                        u.movementRemaining = std::max(0, *stats.movement - used);
                }
    }
    return true;
}
void finishEconomyPlacement(State &s) {
    if (flag(s.nations.at(s.currentNation()).turnFlags, "economy_repairs_finished"))
        return;
    for (auto it = s.repairs.begin(); it != s.repairs.end();) {
        const auto job = it->second;
        if (!movementController(s, job.owner)) {
            ++it;
            continue;
        }
        const auto wait = s.nations.at(job.owner).gameFlags.find("lease_repair_wait:" + job.target);
        if (wait != s.nations.at(job.owner).gameFlags.end()) {
            const auto controller = s.completedTurns.contains(job.owner)
                                        ? job.owner
                                        : s.nations.at(job.owner).controllerNation.value_or("japan");
            if (s.completedTurns.at(controller) < wait->second) {
                ++it;
                continue;
            }
        }
        if (s.facilities.contains(job.target)) {
            auto &f = s.facilities.at(job.target);
            if (s.territories.at(f.zone).possessor == job.owner) {
                f.damage = std::max(0, f.damage - job.remainingDamage);
                s.flags["logistics_damaged_turn:" + f.id] = serial(s);
            }
        } else if (s.territories.contains(job.target)) {
            auto &t = s.territories.at(job.target);
            if (t.possessor == job.owner && !flag(t.flags, "city_destroyed")) {
                t.flags["city_ipp_lost"] =
                    std::max(value(t.flags, "city_ipp_lost"), value(t.flags, "city_damage") / 20);
                t.flags["city_damage"] = std::max(0, value(t.flags, "city_damage") - job.remainingDamage);
            }
        } else if (s.construction.contains(job.target)) {
            auto &p = s.construction.at(job.target);
            if (p.owner == job.owner)
                p.flags["damage"] = std::max(0, value(p.flags, "damage") - job.remainingDamage);
        } else if (s.units.contains(job.target)) {
            auto &u = s.units.at(job.target);
            const auto facility = marker(u.turnFlags, "repair_at:");
            if (u.owner == job.owner && facility && s.facilities.contains(*facility) &&
                navalFacilityUsable(s, job.owner, *facility, true))
                u.damage = std::max(0, u.damage - job.remainingDamage);
        } else if (s.rails.contains(job.target) && job.endpoint) {
            auto &rail = s.rails.at(job.target);
            const auto endpoint = *job.endpoint;
            if (s.territories.at(endpoint).possessor == job.owner) {
                rail.damageByEndpoint[endpoint] =
                    std::max(0, rail.damageByEndpoint[endpoint] - job.remainingDamage);
                s.flags["logistics_damaged_turn:" + rail.id] = serial(s);
            }
        }
        it = s.repairs.erase(it);
    }
    s.nations.at(s.currentNation()).turnFlags["economy_repairs_finished"] = 1;
    refreshIncome(s);
}

EconomyRules::EconomyRules(std::shared_ptr<const Rules> gameplay) : gameplay_(std::move(gameplay)) {}
Id EconomyRules::id() const {
    return "gw36_economy_v43" + (gameplay_ ? "+" + gameplay_->id() : "");
}
std::vector<Action> EconomyRules::actions(const State &s) const {
    auto out = economyActions(s);
    auto leases = lendLeaseActions(s);
    out.insert(out.end(), leases.begin(), leases.end());
    if (gameplay_) {
        auto other = gameplay_->actions(s);
        out.insert(out.end(), other.begin(), other.end());
    }
    return out;
}
std::vector<Action> EconomyRules::interrupts(const State &s) const {
    return gameplay_ ? gameplay_->interrupts(s) : std::vector<Action>{};
}
bool EconomyRules::phaseComplete(const State &s) const {
    if (s.clock.phase == Phase::Production &&
        !flag(s.nations.at(s.currentNation()).turnFlags, "economy_research_finished"))
        return false;
    if (s.clock.phase == Phase::PlaceUnits) {
        for (const auto &[id, p] : s.construction)
            if (!placements(s, p).empty())
                return false;
        if (!lendLeaseActions(s).empty())
            return false;
    }
    return !gameplay_ || gameplay_->phaseComplete(s);
}
void EconomyRules::apply(State &s, const Action &a) const {
    if (!applyEconomyAction(s, a)) {
        require(bool(gameplay_), "Unhandled gameplay action");
        gameplay_->apply(s, a);
    }
    refreshIncome(s);
}
void EconomyRules::applyChance(State &s, const ChanceRequest &r, const ChanceOutcome &o) const {
    if (!applyEconomyChance(s, r, o)) {
        require(bool(gameplay_), "Unhandled gameplay chance");
        gameplay_->applyChance(s, r, o);
    }
    refreshIncome(s);
}
void EconomyRules::beginTurn(State &s) const {
    if (gameplay_)
        gameplay_->beginTurn(s);
    beginEconomyTurn(s);
}
void EconomyRules::finishPhase(State &s) const {
    if (gameplay_)
        gameplay_->finishPhase(s);
    if (s.clock.phase == Phase::PlaceUnits)
        finishEconomyPlacement(s);
}
void EconomyRules::finishTurn(State &s) const {
    finishEconomyPlacement(s);
    refreshIncome(s);
    auto &n = s.nations.at(s.currentNation());
    const auto rate = evaluateIncome(s, s.currentNation());
    if (!s.clock.incomeCollected && rate.collectable && n.treasury) {
        require(*n.treasury <= std::numeric_limits<int>::max() - rate.total, "IPP overflow");
        *n.treasury += rate.total;
    }
    s.clock.incomeCollected = true;
    if (gameplay_)
        gameplay_->finishTurn(s);
}
} // namespace game::campaign
