#include "game/economy.hpp"
#include "game/air.hpp"
#include "game/catalog.hpp"
#include "game/movement.hpp"
#include "game/naval.hpp"
#include "game/politics.hpp"
#include "game/position_facts.hpp"

#include <algorithm>
#include <limits>
#include <numeric>
#include <stdexcept>

namespace game::campaign {
bool upgradeKeepsCargo(const State &s, const UnitState &unit, UnitTypeId type) {
    if (!unit.carriedBy)
        return true;
    const auto &carrier = s.units.at(*unit.carriedBy);
    if (isAircraft(s, carrier))
        return airCargoTypeFits(s, carrier, type);
    std::vector<UnitTypeId> types;
    for (const auto &id : carrier.cargo)
        types.push_back(id == unit.id ? type : s.units.at(id).type);
    return navalCargoTypesFit(s, carrier, types);
}
namespace {
using V = json::Value;
using O = V::Object;
// Builds the message only on failure; most messages are literals.
template <class Message> void require(bool yes, const Message &why) {
    if (!yes)
        throw std::runtime_error(why);
}
V number(int x) {
    return V(static_cast<double>(x));
}
int value(const Marks &flags, const MarkKey &key) { return flags.value(key); }
bool flag(const Marks &flags, const MarkKey &key) { return flags.value(key) != 0; }
const V &node(const State &s, ZoneId zone) {
    return mapNode(s, zone);
}
bool home(const State &s, NationId nation, ZoneId zone) {
    return nationFaction(s, nation).homeZones.contains(zone);
}
bool city(const State &s, ZoneId zone) {
    const auto *v = node(s, zone).find("is_city");
    return v && v->asBool();
}
// Whether a build type is a naval unit, or a capital ship.
bool naval(const State &s, BuildType type) {
    return type.isUnit() && s.definition->catalog->unit(type.unit()).classes.contains(knownUnitClasses(s).naval);
}
bool capitalShip(const State &s, BuildType type) {
    return type.isUnit() && s.definition->catalog->unit(type.unit()).classes.contains(knownUnitClasses(s).capital_ship);
}
// A nation's research stage of a technology: 0 before its first roll.
int researchStage(const NationState &n, TechnologyId technology) {
    const auto i = n.technologyStages.find(technology);
    return i == n.technologyStages.end() ? 0 : i->second;
}
int serial(const State &s) {
    require(s.clock.playerTurnSerial < std::numeric_limits<int>::max(), "Economy turn serial overflow");
    return static_cast<int>(s.clock.playerTurnSerial) + 1;
}
Id unique(State &s, const Id &prefix) {
    return "economy_" + prefix + "_" + std::to_string(++s.flags[mark::economy_sequence]);
}
Action action(const State &s, const Id &kind, O args = {}) {
    Action a;
    a.kind = kind;
    a.nation = s.currentNationName();
    a.player = politicalPlayer(s, s.currentNation());
    a.parameters = V(std::move(args));
    a.id = kind + ":" + contentDigest(canonicalJson(a.parameters));
    return a;
}
void debit(State &s, NationId nation, int amount) {
    auto &cash = s.nations.at(nation).treasury;
    require(amount >= 0 && cash && *cash >= amount, "Insufficient IPP");
    *cash -= amount;
}
bool ownsHeld(const State &s, NationId nation, ZoneId zone) {
    return s.territories.contains(zone) && s.territories.at(zone).possessor == nation &&
           heldSinceTurnStart(s, nation, zone, false);
}
std::vector<ZoneId> neighbors(const State &s, ZoneId zone, bool landOnly = false, bool seaOnly = false) {
    std::vector<ZoneId> out;
    for (const auto id : mapNeighbors(s, zone)) {
        const bool land = s.territories.contains(id);
        if ((landOnly && !land) || (seaOnly && land))
            continue;
        out.push_back(id);
    }
    return out;
}
const V *edge(const State &s, ZoneId from, ZoneId to) {
    return mapEdge(s, from, to);
}
bool harshRail(const State &s, ZoneId from, ZoneId to) {
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
// The argument after `prefix` of the first nonzero mark of this base, in name order.
std::optional<Id> marker(const Marks &flags, MarkId base, std::string_view prefix = {}) {
    return flags.argumentAfter(base, prefix);
}
const BuildChartRow *projectRow(const State &s, const BuildProject &p) {
    if (const auto id = marker(p.flags, mark::row))
        return &s.definition->catalog->row(*id);
    const auto &status = s.nations.at(p.owner).powerStatus;
    for (const auto &[id, r] : s.definition->catalog->rows())
        if (r.nation == nationName(s, p.owner) && r.powerStatus == status && r.type == p.type && r.kind == "purchase")
            return &r;
    return nullptr;
}
bool ready(const BuildProject &p) {
    return p.remainingPayments.empty() || flag(p.flags, mark::completed);
}
int slotsUsed(const State &s, NationId nation, const Id &facility) {
    return value(s.nations.at(nation).turnFlags, MarkKey(mark::economy_used, facility));
}
int capacity(const State &s, NationId nation, const Id &facility, bool repair) {
    const auto &f = s.facilities.at(facility);
    const auto owner = s.territories.at(f.zone).possessor;
    if (!owner || (!repair && *owner != nation))
        return 0;
    if (repair && *owner != nation && !politicallyFriendly(s, nation, *owner))
        return 0;
    if (!heldSinceTurnStart(s, nation, f.zone, repair) || flag(f.flags, mark::placed_this_turn) ||
        flag(f.flags, mark::moved_this_turn))
        return 0;
    if (!inSupply(s, nation, f.zone))
        return 0;
    if (knownFacilityTypes(s).naval(f.type) && !navalFacilityUsable(s, nation, facility, true))
        return 0;
    const auto &catalog = *s.definition->catalog;
    const auto technologies = completedTechnologies(s, nation);
    const int current = repair ? catalog.repairCapacity(f.type, f.damage, technologies)
                               : catalog.productionCapacity(f.type, f.damage, technologies);
    const auto &flags = s.nations.at(nation).turnFlags;
    const MarkKey key(repair ? mark::economy_repair_cap : mark::economy_production_cap, facility);
    const auto i = flags.find(key);
    int snapshot = i == flags.end() ? 0 : i->second;
    if (const auto original = marker(flags, mark::economy_start_type, facility + ":")) {
        const int damage = value(flags, MarkKey(mark::economy_start_damage, facility));
        const auto type = facilityTypeNumber(s, *original);
        snapshot = repair ? catalog.repairCapacity(type, damage, technologies)
                          : catalog.productionCapacity(type, damage, technologies);
    }
    return std::max(0, std::min(snapshot, current) - slotsUsed(s, nation, facility));
}
int totalCapacity(const State &s, NationId nation, bool ships, bool capitals = false) {
    int sum = 0;
    for (const auto &[id, f] : s.facilities)
        if (ships ? (capitals ? f.type == knownFacilityTypes(s).major_shipyard : knownFacilityTypes(s).shipyard(f.type))
                  : knownFacilityTypes(s).factory(f.type))
            sum += capacity(s, nation, id, false);
    return sum;
}
int queuedCapacity(const State &s, NationId nation, bool ships, bool capitals = false) {
    int n = 0;
    for (const auto &[id, p] : s.construction)
        if (p.owner == nation && ready(p) && !p.type.isFacility() && !marker(p.flags, mark::target) &&
            !flag(p.flags, mark::unit_upgrade) && !flag(p.flags, mark::facility_upgrade) && p.type != knownUnitTypes(s).militia &&
            !flag(p.flags, mark::lease_received)) {
            const bool ship = naval(s, p.type);
            if (ship != ships || (capitals && !capitalShip(s, p.type)))
                continue;
            const auto &u = s.definition->catalog->unit(p.type.unit());
            if (!ship && decentralizedProduction(s, nation) &&
                (u.classes.contains(knownUnitClasses(s).infantry_class) || p.type == knownUnitTypes(s).cavalry))
                continue;
            ++n;
        }
    return n;
}
bool canFactoryBuy(const State &s, NationId nation, BuildType type, bool completion) {
    if (type.isFacility() || type == knownUnitTypes(s).militia)
        return true;
    const auto &u = s.definition->catalog->unit(type.unit());
    if (!naval(s, type) && decentralizedProduction(s, nation) &&
        (u.classes.contains(knownUnitClasses(s).infantry_class) || type == knownUnitTypes(s).cavalry))
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
int militiaAllowance(const State &s, NationId nation, ZoneId zone) {
    if (!ownsHeld(s, nation, zone))
        return 0;
    const int limit = std::max(1, effectiveTerritorialIpp(s, zone));
    int left = std::min(limit, originalNation(s, zone) == nation ? limit : 1) -
               value(s.nations.at(nation).turnFlags, MarkKey(mark::economy_militia_placed, zoneName(s, zone)));
    if (s.nations.at(nation).powerStatus == "major" && !home(s, nation, zone)) {
        int present = 0;
        for (const auto &[id, u] : s.units)
            if (u.owner == nation && u.zone == zone && u.type == knownUnitTypes(s).militia)
                ++present;
        left = std::min(left, limit - present);
    }
    return std::max(0, left);
}
bool siteLegal(const State &s, const BuildChartRow &r, ZoneId zone, std::optional<ZoneId> border = {},
               const std::optional<Id> &exclude = {}, bool foreignRequest = false) {
    // A build chart row names its nation; a nation the scenario lacks owns no site.
    const auto rowNation = findNation(s, r.nation);
    if (!rowNation || !ownsHeld(s, *rowNation, zone))
        return false;
    // Construction sites, flags and permissions name zones.
    const auto &site = zoneName(s, zone);
    const auto borderName = border ? std::optional<Id>(zoneName(s, *border)) : std::nullopt;
    if (r.placement.contains("home_country") && !home(s, *rowNation, zone))
        return false;
    if (r.placement.contains("coastal_border") &&
        (!border || s.territories.contains(*border) || !edge(s, zone, *border)))
        return false;
    if (r.placement.contains("land_or_sea_border") && (!border || !edge(s, zone, *border)))
        return false;
    const auto &known = knownFacilityTypes(s);
    // The facilities of a type in the zone, built or under construction.
    auto count = [&](FacilityTypeId type) {
        int n = 0;
        for (const auto &[id, f] : s.facilities)
            if (f.zone == zone && (!exclude || id != *exclude) && f.type == type)
                ++n;
        for (const auto &[id, p] : s.construction)
            if ((!exclude || id != *exclude) && p.site == site && p.type == type &&
                !marker(p.flags, mark::target))
                ++n;
        return n;
    };
    if (r.placement.contains("airbase_per_zone_limit") && count(known.airbase))
        return false;
    if (r.placement.contains("facility_city_naval_limit") && city(s, zone)) {
        const bool major = known.major(r.type.facility());
        for (const auto &[id, f] : s.facilities)
            if (f.zone == zone && (!exclude || id != *exclude) && known.naval(f.type) &&
                known.major(f.type) == major)
                return false;
        for (const auto &[id, p] : s.construction)
            if ((!exclude || id != *exclude) && p.site == site && known.naval(p.type.facility()) &&
                known.major(p.type.facility()) == major && !marker(p.flags, mark::target))
                return false;
    }
    if (r.type == knownFacilityTypes(s).fortification && border) {
        for (const auto &[id, f] : s.facilities)
            if (f.type == knownFacilityTypes(s).fortification && f.zone == zone && flag(f.flags, MarkKey(mark::border, *borderName)))
                return false;
        for (const auto &[id, p] : s.construction)
            if ((!exclude || id != *exclude) && p.type == knownFacilityTypes(s).fortification && p.site == site &&
                flag(p.flags, MarkKey(mark::border, *borderName)))
                return false;
    }
    if (r.type == knownFacilityTypes(s).railroad) {
        if (!border || !s.territories.contains(*border) || !passableLandBorder(s, zone, *border))
            return false;
        const auto owner = s.territories.at(*border).possessor;
        if (!owner)
            return false;
        if (*owner != *rowNation) {
            if (s.nations.at(*rowNation).atWarWith.contains(*owner) || !s.nations.at(*owner).player)
                return false;
            const auto permission = nationName(s, *owner) + ":" + site + ":" + *borderName;
            if (!foreignRequest &&
                value(s.nations.at(*rowNation).turnFlags, MarkKey(mark::rail_build_permission, permission)) != serial(s))
                return false;
        }
        for (const auto &[id, rail] : s.rails)
            if ((rail.endpointA == zone && rail.endpointB == *border) ||
                (rail.endpointA == *border && rail.endpointB == zone))
                return false;
        for (const auto &[id, p] : s.construction)
            if ((!exclude || id != *exclude) && p.type == knownFacilityTypes(s).railroad &&
                ((p.site == site && flag(p.flags, MarkKey(mark::border, *borderName))) ||
                 (p.site == *borderName && flag(p.flags, MarkKey(mark::border, site)))))
                return false;
        if (harshRail(s, zone, *border) != r.placement.contains("railroad_route_cost_4"))
            return false;
    }
    return true;
}
bool upgradeFacilityLegal(const State &s, const BuildChartRow &row, const FacilityState &f) {
    std::optional<ZoneId> border;
    if (const auto marked = marker(f.flags, mark::border))
        border = zoneNumber(s, *marked);
    else {
        const auto seas = navalFacilitySeaZones(s, f.id);
        if (!seas.empty())
            border = seas.front();
    }
    return isNation(s, s.territories.at(f.zone).possessor, row.nation) && row.upgradesFrom == BuildType(f.type) &&
           !flag(f.flags, mark::moved_this_turn) && siteLegal(s, row, f.zone, border, f.id);
}
// RB 12.3 needs a Supply Path to the land zone the unit is in, so a unit aboard
// a ship at sea, in no land zone, cannot be upgraded until it is ashore or in
// port (RCL-021).
bool upgradeUnitLegal(const State &s, NationId nation, const BuildChartRow &row, const UnitState &u,
                      BuildType type) {
    return u.owner == nation && row.upgradesFrom == BuildType(u.type) && !flag(u.turnFlags, mark::placed_this_turn) &&
           s.territories.contains(u.zone) && inSupply(s, nation, u.zone) &&
           upgradeKeepsCargo(s, u, type.unit()) &&
           (u.type != knownUnitTypes(s).militia || value(s.nations.at(nation).turnFlags, mark::economy_militia_upgrades) < 2);
}
void copyMetadata(BuildProject &p, const BuildChartRow &row, const PriceOption &price) {
    p.flags[MarkKey(mark::row, row.id)] = 1;
    p.flags[MarkKey(mark::price, price.method)] = 1;
    p.flags[mark::stages_total] = static_cast<int>(price.payments.size());
    p.flags[mark::stages_paid] = 1;
    for (std::size_t i = 0; i < price.payments.size(); ++i) {
        const auto index = std::to_string(i);
        p.flags[MarkKey(mark::payment, index)] = price.payments[i];
    }
}
std::vector<Action> placements(const State &s, const BuildProject &p) {
    std::vector<Action> out;
    const auto n = p.owner;
    if (n != s.currentNation() || !ready(p))
        return out;
    if (marker(p.flags, mark::lend_to) || flag(p.flags, mark::lease_received))
        return out;
    const auto *row = projectRow(s, p);
    if (flag(p.flags, mark::unit_upgrade) && row) {
        for (const auto &[id, u] : s.units)
            if (upgradeUnitLegal(s, n, *row, u, p.type))
                out.push_back(action(s, "economy_place", {{"project", V(p.id)}, {"target", V(id)}}));
        return out;
    }
    if (flag(p.flags, mark::facility_upgrade) && row) {
        for (const auto &[id, f] : s.facilities)
            if (upgradeFacilityLegal(s, *row, f) && inSupply(s, n, f.zone))
                out.push_back(action(s, "economy_place", {{"project", V(p.id)}, {"target", V(id)}}));
        return out;
    }
    const auto target = marker(p.flags, mark::target);
    if (target) {
        const auto unit = s.units.find(*target);
        const auto fac = s.facilities.find(*target);
        if (unit != s.units.end() && row && upgradeUnitLegal(s, n, *row, unit->second, p.type))
            out.push_back(action(s, "economy_place", {{"project", V(p.id)}, {"target", V(*target)}}));
        if (fac != s.facilities.end() && s.territories.at(fac->second.zone).possessor == n &&
            inSupply(s, n, fac->second.zone) && row && row->upgradesFrom == BuildType(fac->second.type))
            out.push_back(action(s, "economy_place", {{"project", V(p.id)}, {"target", V(*target)}}));
        return out;
    }
    if (p.type.isFacility()) {
        const auto site = p.site ? findZone(s, *p.site) : std::nullopt;
        if (site && s.territories.contains(*site) && ownsHeld(s, n, *site) &&
            !value(p.flags, mark::damage)) {
            const auto marked = marker(p.flags, mark::border);
            const auto border = marked ? std::optional<ZoneId>(zoneNumber(s, *marked)) : std::nullopt;
            std::optional<NationId> foreign;
            if (border && s.territories.contains(*border))
                foreign = s.territories.at(*border).possessor;
            const bool approved = foreign && flag(p.flags, MarkKey(mark::foreign_consent, nationName(s, *foreign)));
            if (!row || siteLegal(s, *row, *site, border, p.id, approved))
                out.push_back(action(s, "economy_place", {{"project", V(p.id)}, {"zone", V(*p.site)}}));
            else if (row->type == knownFacilityTypes(s).railroad && foreign && *foreign != n &&
                     !value(s.nations.at(n).turnFlags, MarkKey(mark::rail_declined, p.id)) &&
                     siteLegal(s, *row, *site, border, p.id, true))
                out.push_back(action(s, "economy_request_rail",
                                     {{"project", V(p.id)}, {"zone", V(*p.site)}, {"border", V(*marked)}}));
        }
        return out;
    }
    for (const auto &[zone, t] : s.territories) {
        if (!ownsHeld(s, n, zone))
            continue;
        if (p.type == knownUnitTypes(s).militia) {
            if (militiaAllowance(s, n, zone) > 0)
                out.push_back(action(s, "economy_place", {{"project", V(p.id)}, {"zone", V(zoneName(s, zone))}}));
            continue;
        }
        const auto &unit = s.definition->catalog->unit(p.type.unit());
        if (decentralizedProduction(s, n) && chineseHomeCountry(s, zone) &&
            (unit.classes.contains(knownUnitClasses(s).infantry_class) || p.type == knownUnitTypes(s).cavalry)) {
            out.push_back(action(s, "economy_place", {{"project", V(p.id)}, {"zone", V(zoneName(s, zone))}}));
            continue;
        }
        for (const auto &[id, f] : s.facilities)
            if (f.zone == zone && capacity(s, n, id, false) > 0) {
                if (naval(s, p.type)) {
                    if (!knownFacilityTypes(s).shipyard(f.type) ||
                        (capitalShip(s, p.type) && f.type != knownFacilityTypes(s).major_shipyard))
                        continue;
                    for (const auto &sea : navalFacilitySeaZones(s, id))
                        out.push_back(action(s, "economy_place",
                                             {{"project", V(p.id)}, {"zone", V(zoneName(s, sea))}, {"facility", V(id)}}));
                    if (f.type == knownFacilityTypes(s).major_shipyard && !unit.classes.contains(knownUnitClasses(s).submarine))
                        out.push_back(action(s, "economy_place",
                                             {{"project", V(p.id)},
                                              {"zone", V(zoneName(s, zone))},
                                              {"facility", V(id)},
                                              {"in_port", V(true)}}));
                } else if (knownFacilityTypes(s).factory(f.type))
                    out.push_back(action(s, "economy_place",
                                         {{"project", V(p.id)}, {"zone", V(zoneName(s, zone))}, {"facility", V(id)}}));
            }
    }
    return out;
}
} // namespace

int effectiveTerritorialIpp(const State &s, ZoneId zone) {
    const auto &flags = s.territories.at(zone).flags;
    return std::max(0, node(s, zone).require("ipp_value").asInt() -
                           std::max(value(flags, mark::city_ipp_lost), value(flags, mark::city_damage) / 20));
}
bool keepsAccount(const Id& nation) {
    return nation == "japan" || nation == "kmt" || nation == "ccp";
}
bool incomePartPossible(const Id& nation, const Id &part) {
    if (part == "territorial")
        return keepsAccount(nation);
    return part == "china_control_bonus" && nation == "japan";
}
bool researchPossible(const Id& nation) {
    return canBeMajorPower(nation);
}
IncomeBreakdown evaluateIncome(const State &s, NationId nation) {
    IncomeBreakdown out;
    const auto &n = s.nations.at(nation);
    const bool account = nation == knownNations(s).japan || nation == knownNations(s).kmt || nation == knownNations(s).ccp || n.powerStatus == "major";
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
    if (nation == knownNations(s).japan) {
        int bonus = 0;
        for (const auto *name : {"land_china_beiping", "land_china_hopeh", "land_china_shantung",
                                 "land_china_nanking", "land_china_hunan", "land_kwangtung"}) {
            const auto zone = findZone(s, name);
            if (zone && s.territories.contains(*zone) && s.territories.at(*zone).possessor == nation)
                ++bonus;
        }
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
void reconcileCapturedFacilities(State &s, ZoneId zone, std::optional<NationId> oldOwner,
                                 NationId newOwner) {
    for (auto &[id, f] : s.facilities)
        if (f.zone == zone && knownFacilityTypes(s).factory(f.type)) {
            if (!marker(f.flags, mark::original_owner))
                f.flags[MarkKey(mark::original_owner, nationName(s, oldOwner.value_or(originalNation(s, zone))))] = 1;
            if (!marker(f.flags, mark::original_type))
                f.flags[MarkKey(mark::original_type, facilityTypeName(s, f.type))] = 1;
            const auto originalType = facilityTypeNumber(s, *marker(f.flags, mark::original_type));
            if (marker(f.flags, mark::original_owner) == nationName(s, newOwner)) {
                f.type = originalType;
                f.flags.erase(mark::captured_max_damage);
            } else if (originalType == knownFacilityTypes(s).medium_factory ||
                       originalType == knownFacilityTypes(s).major_factory) {
                f.type = knownFacilityTypes(s).minor_factory;
                f.flags[mark::captured_max_damage] =
                    s.definition->catalog->facility(originalType).maxDamage.value();
            }
        }
}
int facilityCapacity(const State &s, NationId nation, const Id &facility, bool repair) {
    return capacity(s, nation, facility, repair);
}
void beginEconomyTurn(State &s) {
    auto &n = s.nations.at(s.currentNation());
    for (auto &[id, f] : s.facilities)
        if (s.territories.at(f.zone).possessor == s.currentNation()) {
            f.flags.erase(mark::placed_this_turn);
            f.flags.erase(mark::upgraded_this_turn);
            f.flags.erase(mark::moved_this_turn);
            f.flags.erase(mark::researched_this_turn);
        }
    const auto technologies = completedTechnologies(s, s.currentNation());
    for (const auto &[id, f] : s.facilities) {
        const auto owner = s.territories.at(f.zone).possessor;
        if (!owner || (*owner != s.currentNation() && !politicallyFriendly(s, s.currentNation(), *owner)))
            continue;
        const auto startType = id + ":" + facilityTypeName(s, f.type);
        n.turnFlags[MarkKey(mark::economy_start_type, startType)] = 1;
        n.turnFlags[MarkKey(mark::economy_start_damage, id)] = f.damage;
        n.turnFlags[MarkKey(mark::economy_production_cap, id)] =
            s.definition->catalog->productionCapacity(f.type, f.damage, technologies);
        n.turnFlags[MarkKey(mark::economy_repair_cap, id)] =
            s.definition->catalog->repairCapacity(f.type, f.damage, technologies);
    }
    int research = 0;
    for (const auto &[id, f] : s.facilities)
        if (f.type == knownFacilityTypes(s).major_factory && f.damage == 0 &&
            s.territories.at(f.zone).possessor == s.currentNation() && !flag(f.flags, mark::placed_this_turn))
            ++research;
    n.turnFlags[mark::economy_research_capacity] = n.powerStatus == "major" ? research : 0;
    n.turnFlags[mark::economy_research_finished] = research == 0 || n.powerStatus != "major";
}
void damageConstruction(State &s, const Id &id, int damage) {
    require(damage >= 0, "Negative construction damage");
    auto &p = s.construction.at(id);
    require(p.type.isFacility() && p.type != knownFacilityTypes(s).fortification && p.type != knownFacilityTypes(s).coastal_artillery,
            "Not a bombable construction project");
    int combined = value(p.flags, mark::damage) + damage;
    int paid = value(p.flags, mark::stages_paid);
    if (!paid)
        paid = std::max(1, value(p.flags, mark::stages_total) - static_cast<int>(p.remainingPayments.size()));
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
        const auto stage = std::to_string(paid);
        const auto payment = value(p.flags, MarkKey(mark::payment, stage));
        p.remainingPayments.insert(p.remainingPayments.begin(), payment);
        combined -= 3;
    }
    p.flags[mark::stages_paid] = paid;
    p.flags[mark::damage] = combined;
    if (!p.remainingPayments.empty())
        p.flags.erase(mark::completed);
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
    if (!flag(n.turnFlags, mark::economy_research_finished)) {
        if (value(n.turnFlags, mark::economy_research_used) < value(n.turnFlags, mark::economy_research_capacity))
            for (const auto tech : catalog.technologies().numbers()) {
                const auto &t = catalog.technology(tech);
                const auto &id = t.id;
                const int reached = researchStage(n, tech);
                if (reached >= 4 ||
                    (reached == 2 && s.calendarDate().first * 100 + s.calendarDate().second < t.stageThreeFrom))
                    continue;
                if (value(n.gameFlags, MarkKey(mark::economy_researched_round, id)) == s.clock.roundIndex + 1)
                    continue;
                for (const auto &[facility, f] : s.facilities)
                    if (f.type == knownFacilityTypes(s).major_factory && f.damage == 0 &&
                        s.territories.at(f.zone).possessor == nation && !flag(f.flags, mark::placed_this_turn) &&
                        !flag(f.flags, mark::moved_this_turn) && !flag(f.flags, mark::researched_this_turn))
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
                // The unit type the row upgrades, numbered once for the scan below.
                const auto from = r.upgradesFrom ? r.upgradesFrom->unit() : UnitTypeId {};
                if (!r.type.isFacility() &&
                    std::any_of(s.units.begin(), s.units.end(), [&](const auto &item) {
                        const auto &u = item.second;
                        return u.owner == nation && from == u.type &&
                               !flag(u.turnFlags, mark::placed_this_turn);
                    }))
                    out.push_back(action(s, "economy_purchase", base));
                if (r.type.isFacility() &&
                    std::any_of(s.facilities.begin(), s.facilities.end(),
                                [&](const auto &item) { return upgradeFacilityLegal(s, r, item.second); }))
                    out.push_back(action(s, "economy_purchase", base));
                continue;
            }
            if (!canFactoryBuy(s, nation, r.type, price.payments.size() == 1))
                continue;
            if (r.type.isFacility()) {
                for (const auto &[zone, t] : s.territories) {
                    if (r.placement.contains("coastal_border") ||
                        r.placement.contains("land_or_sea_border") || r.type == knownFacilityTypes(s).railroad)
                        for (const auto &border : neighbors(s, zone)) {
                            const bool legal = siteLegal(s, r, zone, border);
                            const bool request =
                                r.type == knownFacilityTypes(s).railroad && !legal && siteLegal(s, r, zone, border, {}, true);
                            if (!legal && !request)
                                continue;
                            auto args = base;
                            args["zone"] = V(zoneName(s, zone));
                            args["border"] = V(zoneName(s, border));
                            out.push_back(
                                action(s, request ? "economy_request_rail" : "economy_purchase", args));
                            if (legal && (knownFacilityTypes(s).naval(r.type.facility()) || r.type == knownFacilityTypes(s).seaplane_base ||
                                          r.type == knownFacilityTypes(s).submarine_base))
                                for (const auto &second : neighbors(s, zone, false, true))
                                    if (border < second) {
                                        auto dual = args;
                                        dual["border2"] = V(zoneName(s, second));
                                        out.push_back(action(s, "economy_purchase", std::move(dual)));
                                    }
                        }
                    else if (siteLegal(s, r, zone)) {
                        auto args = base;
                        args["zone"] = V(zoneName(s, zone));
                        out.push_back(action(s, "economy_purchase", std::move(args)));
                    }
                }
            } else {
                int available = 0, queued = 0;
                if (r.type == knownUnitTypes(s).militia) {
                    for (const auto &[zone, t] : s.territories)
                        available += militiaAllowance(s, nation, zone);
                    for (const auto &[id, p] : s.construction)
                        if (p.owner == nation && p.type == knownUnitTypes(s).militia && ready(p))
                            ++queued;
                }
                if (r.type != knownUnitTypes(s).militia || queued < available)
                    out.push_back(action(s, "economy_purchase", base));
            }
        }
    for (const auto &[id, p] : s.construction)
        if (p.owner == nation && !ready(p) && !value(p.flags, mark::damage) &&
            value(p.flags, mark::economy_last_paid_turn) != serial(s) &&
            p.remainingPayments.front() <= *n.treasury &&
            canFactoryBuy(s, nation, p.type, p.remainingPayments.size() == 1))
            out.push_back(action(s, "economy_advance", {{"project", V(id)}}));
    for (const auto &[id, f] : s.facilities)
        if (s.territories.at(f.zone).possessor == nation && f.damage > 0 &&
            !flag(f.flags, mark::moved_this_turn) && !s.repairs.contains("repair_" + id))
            for (int damage = 1; damage <= std::min(f.damage, *n.treasury); ++damage)
                out.push_back(action(s, "economy_repair", {{"target", V(id)}, {"damage", number(damage)}}));
    for (const auto &[zone, t] : s.territories)
        if (t.possessor == nation && city(s, zone) && !flag(t.flags, mark::city_destroyed) &&
            value(t.flags, mark::city_damage) > 0 && !s.repairs.contains("repair_" + zoneName(s, zone)))
            for (int damage = 1; damage <= std::min(value(t.flags, mark::city_damage), *n.treasury); ++damage)
                out.push_back(action(s, "economy_repair", {{"target", V(zoneName(s, zone))}, {"damage", number(damage)}}));
    for (const auto &[id, p] : s.construction)
        if (p.owner == nation && value(p.flags, mark::damage) > 0 && !s.repairs.contains("repair_" + id))
            for (int damage = 1; damage <= std::min(value(p.flags, mark::damage), *n.treasury); ++damage)
                out.push_back(action(s, "economy_repair", {{"target", V(id)}, {"damage", number(damage)}}));
    for (const auto &[id, rail] : s.rails)
        for (const auto &[endpoint, damage] : rail.damageByEndpoint)
            if (damage > 0 && s.territories.at(endpoint).possessor == nation &&
                !s.repairs.contains("repair_" + id + "_" + zoneName(s, endpoint)))
                for (int count = 1; count <= std::min(damage, *n.treasury); ++count)
                    out.push_back(
                        action(s, "economy_repair",
                               {{"target", V(id)}, {"endpoint", V(zoneName(s, endpoint))}, {"damage", number(count)}}));
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
    // Engine::step has already found a move it plays in the position's whole
    // menu, of which the economy's options are a part. Any other action, such
    // as the purchase a railroad consent completes, is checked against them.
    if (!MenuCheckedAction::marks(a)) {
        const auto options = [&] {
            // The check only reads the position: each facility's supply is traced once.
            const PositionScope scope(s);
            return economyActions(s);
        }();
        const auto proposed = canonicalJson(actionJson(a));
        require(std::any_of(options.begin(), options.end(),
                            [&](const auto &option) { return canonicalJson(actionJson(option)) == proposed; }),
                "Illegal economy action");
    }
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
            const auto permission = a.nation + ":" + zone + ":" + border;
            s.nations.at(nationNumber(s, sender)).turnFlags[MarkKey(mark::rail_build_permission, permission)] = serial(s);
            if (const auto *project = payload.require("parameters").find("project"))
                s.construction.at(project->asString()).flags[MarkKey(mark::foreign_consent, a.nation)] = 1;
            else {
                const auto original = action(s, "economy_purchase", payload.require("parameters").asObject());
                applyEconomyAction(s, original);
            }
        } else if (const auto *project = payload.require("parameters").find("project"))
            s.nations.at(nationNumber(s, payload.require("sender").asString()))
                .turnFlags[MarkKey(mark::rail_declined, project->asString())] = 1;
        return true;
    }
    if (a.kind == "economy_request_rail") {
        const auto border = zoneNumber(s, a.parameters.require("border").asString());
        const auto recipient = *s.territories.at(border).possessor;
        std::vector<Action> choices{politicalAction(s, recipient, "economy_approve_rail"),
                                    politicalAction(s, recipient, "economy_decline_rail")};
        queuePoliticalDecision(s, recipient, "economy_rail_permission", std::move(choices),
                               V(O{{"sender", V(a.nation)}, {"parameters", a.parameters}}));
        return true;
    }
    const auto actor = nationNumber(s, a.nation);
    auto &n = s.nations.at(actor);
    const auto &catalog = *s.definition->catalog;
    if (a.kind == "economy_finish_research") {
        n.turnFlags[mark::economy_research_finished] = 1;
        return true;
    }
    if (a.kind == "economy_research") {
        const auto tech = a.parameters.require("technology").asString();
        s.facilities.at(a.parameters.require("facility").asString()).flags[mark::researched_this_turn] = 1;
        ++n.turnFlags[mark::economy_research_used];
        n.gameFlags[MarkKey(mark::economy_researched_round, tech)] = s.clock.roundIndex + 1;
        ChanceRequest request;
        request.id = unique(s, "research");
        request.purpose = "economy_research:" + tech;
        request.nation = a.nation;
        request.continuation = tech;
        request.dice = {DieSpec{12, 0, {}, 0}};
        s.chance = std::move(request);
        return true;
    }
    if (a.kind == "economy_purchase") {
        const auto &r = catalog.row(a.parameters.require("row").asString());
        const auto prices = catalog.priceOptions(r.id, catalogContext(s, actor));
        const auto method = a.parameters.require("price").asString();
        const auto price =
            std::find_if(prices.begin(), prices.end(), [&](const auto &x) { return x.method == method; });
        require(price != prices.end(), "Unknown price option");
        debit(s, actor, price->payments.front());
        BuildProject p;
        p.id = unique(s, buildTypeName(s, r.type));
        p.owner = actor;
        p.type = r.type;
        p.paidIpp = price->payments.front();
        p.remainingPayments.assign(price->payments.begin() + 1, price->payments.end());
        p.queuePosition = std::max(1, static_cast<int>(p.remainingPayments.size()) + 1);
        copyMetadata(p, r, *price);
        p.flags[mark::economy_last_paid_turn] = serial(s);
        p.flags[mark::economy_purchased] = 1;
        if (const auto *zone = a.parameters.find("zone"))
            p.site = zone->asString();
        if (const auto *border = a.parameters.find("border"))
            p.flags[MarkKey(mark::border, border->asString())] = 1;
        if (const auto *border = a.parameters.find("border2"))
            p.flags[MarkKey(mark::border, border->asString())] = 1;
        if (r.type == knownFacilityTypes(s).railroad)
            if (const auto border = marker(p.flags, mark::border)) {
                const auto owner = s.territories.at(zoneNumber(s, *border)).possessor;
                if (owner && *owner != actor)
                    p.flags[MarkKey(mark::foreign_consent, nationName(s, *owner))] = 1;
            }
        if (r.kind == "upgrade")
            p.flags[r.type.isFacility() ? mark::facility_upgrade : mark::unit_upgrade] = 1;
        if (const auto *target = a.parameters.find("target")) {
            p.flags[MarkKey(mark::target, target->asString())] = 1;
            if (s.facilities.contains(target->asString()))
                p.site = target->asString();
        }
        if (ready(p))
            p.flags[mark::completed] = 1;
        s.construction.emplace(p.id, std::move(p));
        const auto group = r.capGroup.value_or(r.id);
        ++n.turnFlags[MarkKey(mark::purchased, group)];
        return true;
    }
    if (a.kind == "economy_advance") {
        auto &p = s.construction.at(a.parameters.require("project").asString());
        const int payment = p.remainingPayments.front();
        debit(s, actor, payment);
        p.paidIpp += payment;
        p.remainingPayments.erase(p.remainingPayments.begin());
        p.queuePosition = std::max(1, static_cast<int>(p.remainingPayments.size()) + 1);
        ++p.flags[mark::stages_paid];
        p.flags[mark::economy_last_paid_turn] = serial(s);
        if (ready(p))
            p.flags[mark::completed] = 1;
        return true;
    }
    if (a.kind == "economy_repair") {
        const auto target = a.parameters.require("target").asString();
        const int damage = a.parameters.require("damage").asInt();
        const bool ship = s.units.contains(target);
        if (!ship)
            debit(s, actor, damage);
        RepairJob job;
        job.id = "repair_" + target;
        job.owner = actor;
        job.target = target;
        job.remainingDamage = damage;
        job.remainingCost = 0;
        job.restrictsAction = ship;
        if (const auto *endpoint = a.parameters.find("endpoint")) {
            job.id += "_" + endpoint->asString();
            job.endpoint = zoneNumber(s, endpoint->asString());
        }
        s.repairs.emplace(job.id, job);
        if (ship) {
            auto &u = s.units.at(target);
            u.turnFlags[mark::repairing] = 1;
            u.commitments.insert(mark::repair);
            const auto facility = a.parameters.require("facility").asString();
            u.turnFlags[MarkKey(mark::repair_at, facility)] = 1;
            n.turnFlags[MarkKey(mark::economy_used, facility)] += damage;
        }
        return true;
    }
    if (a.kind == "economy_place") {
        const auto id = a.parameters.require("project").asString();
        const auto p = s.construction.at(id);
        if (const auto target = (flag(p.flags, mark::unit_upgrade) || flag(p.flags, mark::facility_upgrade))
                                    ? std::optional<Id>(a.parameters.require("target").asString())
                                    : marker(p.flags, mark::target)) {
            if (s.units.contains(*target)) {
                auto &u = s.units.at(*target);
                if (u.type == knownUnitTypes(s).militia)
                    ++n.turnFlags[mark::economy_militia_upgrades];
                u.type = p.type.unit();
                const auto stats = catalog.stats(u.type, u.damage, catalogContext(s, u.owner, u.zone));
                u.movementAllowance = stats.movement;
                u.movementRemaining = 0;
            } else {
                auto &f = s.facilities.at(*target);
                f.type = p.type.facility();
                f.flags[mark::upgraded_this_turn] = 1;
                if (!flag(f.flags, mark::captured_max_damage)) {
                    for (auto it = f.flags.begin(); it != f.flags.end();)
                        if (it->first.base() == mark::original_type)
                            it = f.flags.erase(it);
                        else
                            ++it;
                    f.flags[MarkKey(mark::original_type, facilityTypeName(s, f.type))] = 1;
                }
            }
        } else if (p.type.isFacility()) {
            const auto zone = zoneNumber(s, *p.site);
            if (p.type == knownFacilityTypes(s).railroad) {
                // One railroad per border (RCL-019); siteLegal refuses a second.
                const auto border = zoneNumber(s, *marker(p.flags, mark::border));
                RailState rail;
                rail.id = railroadId(s, zone, border);
                rail.endpointA = std::min(zone, border);
                rail.endpointB = std::max(zone, border);
                require(!s.rails.contains(rail.id), "Border already has a railroad");
                rail.damageByEndpoint[rail.endpointA] = rail.damageByEndpoint[rail.endpointB] = 0;
                s.flags[MarkKey(mark::logistics_rail_created_turn, rail.id)] = serial(s);
                s.rails.emplace(rail.id, std::move(rail));
            } else {
                FacilityState f;
                f.id = unique(s, "facility");
                f.type = p.type.facility();
                f.zone = zone;
                f.flags[mark::placed_this_turn] = 1;
                f.flags[MarkKey(mark::original_owner, nationName(s, p.owner))] = 1;
                f.flags[MarkKey(mark::original_type, facilityTypeName(s, f.type))] = 1;
                for (const auto &[key, v] : p.flags)
                    if (key.base() == mark::border)
                        f.flags[key] = v;
                s.facilities.emplace(f.id, std::move(f));
            }
        } else {
            UnitState u;
            u.id = unique(s, "unit");
            u.type = p.type.unit();
            u.owner = p.owner;
            u.zone = zoneNumber(s, a.parameters.require("zone").asString());
            u.turnOrigin = u.zone;
            u.movementAllowance = catalog.stats(u.type, 0, catalogContext(s, u.owner, u.zone)).movement;
            u.movementRemaining = 0;
            u.turnFlags[mark::placed_this_turn] = 1;
            if (const auto *f = a.parameters.find("facility")) {
                ++n.turnFlags[MarkKey(mark::economy_used, f->asString())];
                if (const auto *port = a.parameters.find("in_port"))
                    if (port->asBool())
                        u.gameFlags[MarkKey(mark::in_port, f->asString())] = 1;
            }
            if (u.type == knownUnitTypes(s).militia)
                ++n.turnFlags[MarkKey(mark::economy_militia_placed, zoneName(s, u.zone))];
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
    const auto tech = technologyNumber(s, request.purpose.substr(17));
    const auto researcher = nationNumber(s, request.nation);
    auto &n = s.nations.at(researcher);
    auto &stage = n.technologyStages[tech];
    const int face = effectiveResults(request, outcome).at(0);
    if (face <= s.definition->catalog->technology(tech).thresholds.at(static_cast<std::size_t>(stage))) {
        ++stage;
        if (stage == 4)
            for (auto &[id, u] : s.units)
                if (u.owner == researcher) {
                    const auto conversions = s.definition->catalog->automaticConversions(
                        u.type, catalogContext(s, u.owner, u.zone));
                    if (!conversions.empty())
                        u.type = conversions.front().to.unit();
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
    if (flag(s.nations.at(s.currentNation()).turnFlags, mark::economy_repairs_finished))
        return;
    for (auto it = s.repairs.begin(); it != s.repairs.end();) {
        const auto job = it->second;
        if (!movementController(s, job.owner)) {
            ++it;
            continue;
        }
        const auto wait = s.nations.at(job.owner).gameFlags.find(MarkKey(mark::lease_repair_wait, job.target));
        if (wait != s.nations.at(job.owner).gameFlags.end()) {
            const auto &controllerNation = s.nations.at(job.owner).controllerNation;
            const auto controller = s.completedTurns.contains(job.owner) ? job.owner
                                    : controllerNation ? *controllerNation
                                                       : nationNumber(s, "japan");
            if (s.completedTurns.at(controller) < wait->second) {
                ++it;
                continue;
            }
        }
        if (s.facilities.contains(job.target)) {
            auto &f = s.facilities.at(job.target);
            if (s.territories.at(f.zone).possessor == job.owner) {
                f.damage = std::max(0, f.damage - job.remainingDamage);
                s.flags[MarkKey(mark::logistics_damaged_turn, f.id)] = serial(s);
            }
        } else if (const auto zone = findZone(s, job.target); zone && s.territories.contains(*zone)) {
            auto &t = s.territories.at(*zone);
            if (t.possessor == job.owner && !flag(t.flags, mark::city_destroyed)) {
                t.flags[mark::city_ipp_lost] =
                    std::max(value(t.flags, mark::city_ipp_lost), value(t.flags, mark::city_damage) / 20);
                t.flags[mark::city_damage] = std::max(0, value(t.flags, mark::city_damage) - job.remainingDamage);
            }
        } else if (s.construction.contains(job.target)) {
            auto &p = s.construction.at(job.target);
            if (p.owner == job.owner)
                p.flags[mark::damage] = std::max(0, value(p.flags, mark::damage) - job.remainingDamage);
        } else if (s.units.contains(job.target)) {
            auto &u = s.units.at(job.target);
            const auto facility = marker(u.turnFlags, mark::repair_at);
            if (u.owner == job.owner && facility && s.facilities.contains(*facility) &&
                navalFacilityUsable(s, job.owner, *facility, true))
                u.damage = std::max(0, u.damage - job.remainingDamage);
        } else if (s.rails.contains(job.target) && job.endpoint) {
            auto &rail = s.rails.at(job.target);
            const auto endpoint = *job.endpoint;
            if (s.territories.at(endpoint).possessor == job.owner) {
                rail.damageByEndpoint[endpoint] =
                    std::max(0, rail.damageByEndpoint[endpoint] - job.remainingDamage);
                s.flags[MarkKey(mark::logistics_damaged_turn, rail.id)] = serial(s);
            }
        }
        it = s.repairs.erase(it);
    }
    s.nations.at(s.currentNation()).turnFlags[mark::economy_repairs_finished] = 1;
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
        !flag(s.nations.at(s.currentNation()).turnFlags, mark::economy_research_finished))
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
}
void EconomyRules::applyChance(State &s, const ChanceRequest &r, const ChanceOutcome &o) const {
    if (!applyEconomyChance(s, r, o)) {
        require(bool(gameplay_), "Unhandled gameplay chance");
        gameplay_->applyChance(s, r, o);
    }
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
void EconomyRules::settle(State &s) const {
    if (gameplay_)
        gameplay_->settle(s);
    // Land changes hands in moves no economy step sees, so the stored rates are
    // brought up to date here, where every transition ends.
    refreshIncome(s);
}
} // namespace game::campaign
