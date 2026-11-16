#include "game/catalog.hpp"
#include "game/economy.hpp"
#include "game/movement.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <stdexcept>

namespace game::campaign {
namespace {
using V = json::Value;
using O = V::Object;
// Builds the message only on failure; most messages are literals.
template <class Message> void require(bool c, const Message &why) {
    if (!c)
        throw std::runtime_error(why);
}
int value(const Marks &flags, const MarkKey &key) { return flags.value(key); }
// The argument after `prefix` of the first nonzero mark of this base, in name order.
std::optional<Id> marker(const Marks &flags, MarkId base, std::string_view prefix = {}) {
    return flags.argumentAfter(base, prefix);
}
Action action(const State &s, const Id &kind, O args = {}) {
    Action a;
    a.nation = s.currentNationName();
    a.player = politicalPlayer(s, s.currentNation());
    a.kind = kind;
    a.parameters = V(std::move(args));
    a.id = kind + ":" + contentDigest(canonicalJson(a.parameters));
    return a;
}
Id unique(State &s, const Id &prefix) {
    return "economy_" + prefix + "_" + std::to_string(++s.flags[mark::economy_sequence]);
}
bool recipientHome(const State &s, NationId recipient, ZoneId zone) {
    return s.territories.at(zone).possessor == recipient &&
           (nationFaction(s, recipient).homeZones.contains(zone) ||
            (recipient == knownNations(s).dadao && chineseHomeCountry(s, zone)));
}
bool baseType(const State &s, BuildType type) {
    return knownFacilityTypes(s).base(type.facility());
}
bool techUnit(const State &s, const BuildProject &p) {
    if (p.type == knownUnitTypes(s).elite_airborne_infantry)
        return false; // RB47 expressly permits its lend-lease conversion.
    for (const auto &[id, row] : s.definition->catalog->rows())
        if (row.nation == nationName(s, p.owner) && row.type == p.type && row.kind == "purchase" &&
            !row.requiredTechnologies.empty())
            return true;
    return false;
}
bool ready(const BuildProject &p) {
    return p.remainingPayments.empty();
}
bool available(const State &s, const BuildProject &p) {
    const auto gate = marker(p.flags, mark::lease_wait_controller);
    if (!gate)
        return true;
    return s.completedTurns.at(nationNumber(s, *gate)) >= value(p.flags, mark::lease_available_after_turns);
}
NationId controllerTurn(const State &s, NationId nation) {
    if (s.completedTurns.contains(nation))
        return nation;
    if (s.nations.at(nation).controllerNation)
        return *s.nations.at(nation).controllerNation;
    return nationNumber(s, "japan");
}
std::vector<std::pair<Id, ZoneId>> senderFactories(const State &s, const BuildProject &p) {
    std::vector<std::pair<Id, ZoneId>> out;
    if (p.type.isFacility() || value(p.flags, mark::lease_militia_upgrade) ||
        value(p.flags, mark::lease_repair))
        return {{"", ZoneId {}}};
    const auto &unit = s.definition->catalog->unit(p.type.unit());
    const bool naval = unit.classes.contains(knownUnitClasses(s).naval);
    const bool capital = unit.classes.contains(knownUnitClasses(s).capital_ship);
    if (p.type == knownUnitTypes(s).militia)
        return {{"", ZoneId {}}};
    if (decentralizedProduction(s, p.owner) &&
        (unit.classes.contains(knownUnitClasses(s).infantry_class) || p.type == knownUnitTypes(s).cavalry))
        return {{"", ZoneId {}}};
    for (const auto &[id, f] : s.facilities)
        if (facilityCapacity(s, p.owner, id, false) > 0 &&
            (naval ? (knownFacilityTypes(s).shipyard(f.type) && (!capital || f.type == knownFacilityTypes(s).major_shipyard))
                   : knownFacilityTypes(s).factory(f.type)))
            out.emplace_back(id, f.zone);
    return out;
}
bool transportable(const State &s, const BuildProject &p, const SupplyRoute &route) {
    if (!route.connected)
        return false;
    if (!p.type.isUnit() ||
        !s.definition->catalog->unit(p.type.unit()).classes.contains(knownUnitClasses(s).naval))
        return true;
    // A naval delivery can only have its source and destination land tiles.
    for (std::size_t i = 1; i + 1 < route.zones.size(); ++i)
        if (s.territories.contains(route.zones[i]))
            return false;
    return std::any_of(route.zones.begin(), route.zones.end(),
                       [&](const auto &zone) { return !s.territories.contains(zone); });
}
std::vector<Action> recipientPlacements(const State &s, const BuildProject &p) {
    std::vector<Action> out;
    if (!movementController(s, p.owner) || !available(s, p))
        return out;
    for (const auto &[zone, t] : s.territories)
        if (recipientHome(s, p.owner, zone) && heldSinceTurnStart(s, p.owner, zone, false)) {
            if (value(p.flags, mark::lease_militia_upgrade)) {
                const auto sender = marker(p.flags, mark::lease_sender);
                const bool supplied = inSupply(s, p.owner, zone) ||
                                      (sender && lendLeaseSupplyRoute(s, nationNumber(s, *sender), p.owner, zone).connected);
                for (const auto &[id, u] : s.units)
                    if (supplied && value(s.nations.at(p.owner).turnFlags, mark::economy_militia_upgrades) < 2 &&
                        u.owner == p.owner && u.zone == zone && u.type == knownUnitTypes(s).militia &&
                        !value(u.turnFlags, mark::placed_this_turn) && upgradeKeepsCargo(s, u, knownUnitTypes(s).infantry))
                        out.push_back(
                            action(s, "economy_lease_place", {{"project", V(p.id)}, {"target", V(id)}}));
            } else if (baseType(s, p.type)) {
                if (p.type == knownFacilityTypes(s).airbase) {
                    bool exists = false;
                    for (const auto &[id, f] : s.facilities)
                        if (f.zone == zone && f.type == knownFacilityTypes(s).airbase)
                            exists = true;
                    if (!exists)
                        out.push_back(
                            action(s, "economy_lease_place", {{"project", V(p.id)}, {"zone", V(zoneName(s, zone))}}));
                } else
                    for (const auto &edge : s.definition->geography.require("nodes")
                                                .require(zoneName(s, zone))
                                                .require("neighbors")
                                                .asArray()) {
                        const auto sea = edge.require("neighbor_id").asString();
                        if (!s.territories.contains(zoneNumber(s, sea))) {
                            O args{{"project", V(p.id)}, {"zone", V(zoneName(s, zone))}, {"border", V(sea)}};
                            out.push_back(action(s, "economy_lease_place", args));
                            for (const auto &next : s.definition->geography.require("nodes")
                                                        .require(zoneName(s, zone))
                                                        .require("neighbors")
                                                        .asArray()) {
                                const auto second = next.require("neighbor_id").asString();
                                if (sea < second && !s.territories.contains(zoneNumber(s, second))) {
                                    auto dual = args;
                                    dual["border2"] = V(second);
                                    out.push_back(action(s, "economy_lease_place", std::move(dual)));
                                }
                            }
                        }
                    }
            }
        }
    return out;
}
} // namespace

bool lendLeasePermitted(const State &s, NationId sender, NationId recipient) {
    if (sender == recipient || !s.nations.contains(sender) || !s.nations.contains(recipient) ||
        s.politics.surrendered.contains(sender) || s.politics.surrendered.contains(recipient))
        return false;
    const auto &n = s.nations.at(sender);
    if (n.powerStatus != "major" || !n.treasury)
        return false;
    if (n.alliance)
        for (const auto &enemy : s.nations.at(recipient).atWarWith)
            if (s.nations.at(enemy).alliance == n.alliance)
                return false;
    if (sender == knownNations(s).japan && recipient == knownNations(s).dadao && controlledBy(s, recipient, sender))
        return true;
    if (sender != knownNations(s).japan && sender != knownNations(s).kmt && sender != knownNations(s).ccp)
        return false;
    return atWarWithMajor(s, recipient);
}
std::vector<Action> lendLeaseActions(const State &s) {
    std::vector<Action> out;
    if (s.terminal || s.chance || !s.decisions.empty())
        return out;
    const auto sender = s.currentNation();
    const auto &n = s.nations.at(sender);
    if (s.clock.phase == Phase::Production && value(n.turnFlags, mark::economy_research_finished)) {
        for (const auto &[recipient, r] : s.nations)
            if (lendLeasePermitted(s, sender, recipient) &&
                !value(n.turnFlags, MarkKey(mark::lease_declared, nationName(s, recipient)))) {
                for (const auto &[id, p] : s.construction)
                    if (p.owner == sender && ready(p) && !value(p.flags, mark::national_objective_award) &&
                        !marker(p.flags, mark::lend_to) && !marker(p.flags, mark::target) &&
                        !value(p.flags, mark::unit_upgrade) && !value(p.flags, mark::facility_upgrade) &&
                        !value(p.flags, mark::lease_received) &&
                        (!p.type.isFacility() || baseType(s, p.type)) &&
                        !techUnit(s, p))
                        out.push_back(action(s, "economy_lease_declare",
                                             {{"project", V(id)}, {"recipient", V(nationName(s, recipient))}}));
                if (n.treasury && *n.treasury >= 2)
                    out.push_back(action(s, "economy_lease_upgrade", {{"recipient", V(nationName(s, recipient))}}));
                for (const auto &[id, f] : s.facilities)
                    if (s.territories.at(f.zone).possessor == recipient && f.damage > 0 && n.treasury &&
                        *n.treasury >= f.damage)
                        out.push_back(action(s, "economy_lease_repair",
                                             {{"recipient", V(nationName(s, recipient))}, {"target", V(id)}}));
            }
    }
    if (s.clock.phase != Phase::PlaceUnits)
        return out;
    for (const auto &[id, p] : s.construction) {
        if (value(p.flags, mark::lease_received)) {
            auto choices = recipientPlacements(s, p);
            out.insert(out.end(), choices.begin(), choices.end());
            continue;
        }
        const auto recipientName = marker(p.flags, mark::lend_to);
        const auto recipient = recipientName ? findNation(s, *recipientName) : std::nullopt;
        if (p.owner != sender || !recipient || !ready(p) || !lendLeasePermitted(s, sender, *recipient) ||
            value(n.turnFlags, MarkKey(mark::lease_delivered, *recipientName)))
            continue;
        for (const auto &[zone, t] : s.territories)
            if (recipientHome(s, *recipient, zone)) {
                const bool ship = p.type.isUnit() &&
                                  s.definition->catalog->unit(p.type.unit()).classes.contains(knownUnitClasses(s).naval);
                const auto route = lendLeaseSupplyRoute(s, sender, *recipient, zone, ship);
                if (!transportable(s, p, route))
                    continue;
                for (const auto &[factory, location] : senderFactories(s, p)) {
                    O params{{"project", V(id)}, {"zone", V(zoneName(s, zone))}};
                    if (!factory.empty())
                        params["factory"] = V(factory);
                    if (ship) {
                        // Delivery in port is allowed; submarines need a submarine base.
                        const bool sub = s.definition->catalog->unit(p.type.unit()).classes.contains(knownUnitClasses(s).submarine);
                        if (!route.facilities.empty())
                            for (const auto &sea : navalFacilitySeaZones(s, route.facilities.back())) {
                                auto afloat = params;
                                afloat["sea"] = V(zoneName(s, sea));
                                out.push_back(action(s, "economy_lease_deliver", std::move(afloat)));
                            }
                        for (const auto &[fid, f] : s.facilities)
                            if (f.zone == zone && f.damage == 0 &&
                                (sub ? f.type == knownFacilityTypes(s).submarine_base
                                     : knownFacilityTypes(s).major(f.type) &&
                                           !knownFacilityTypes(s).factory(f.type))) {
                                auto port = params;
                                port["port"] = V(fid);
                                out.push_back(action(s, "economy_lease_deliver", std::move(port)));
                            }
                    } else
                        out.push_back(action(s, "economy_lease_deliver", std::move(params)));
                }
            }
    }
    return out;
}
bool applyLendLeaseAction(State &s, const Action &a) {
    if (a.kind.rfind("economy_lease_", 0) != 0)
        return false;
    const auto offered = lendLeaseActions(s);
    require(std::any_of(
                offered.begin(), offered.end(),
                [&](const auto &x) { return canonicalJson(actionJson(x)) == canonicalJson(actionJson(a)); }),
            "Illegal lend-lease action");
    if (a.kind == "economy_lease_declare") {
        auto &p = s.construction.at(a.parameters.require("project").asString());
        const auto recipient = a.parameters.require("recipient").asString();
        p.flags[MarkKey(mark::lend_to, recipient)] = 1;
        s.nations.at(nationNumber(s, a.nation)).turnFlags[MarkKey(mark::lease_declared, recipient)] = 1;
        return true;
    }
    if (a.kind == "economy_lease_upgrade" || a.kind == "economy_lease_repair") {
        const auto recipient = a.parameters.require("recipient").asString();
        BuildProject p;
        p.id = unique(s, "lease");
        p.owner = nationNumber(s, a.nation);
        p.type = a.kind == "economy_lease_upgrade"
                     ? BuildType(knownUnitTypes(s).infantry)
                     : BuildType(s.facilities.at(a.parameters.require("target").asString()).type);
        const int cost = a.kind == "economy_lease_upgrade"
                             ? 2
                             : s.facilities.at(a.parameters.require("target").asString()).damage;
        *s.nations.at(nationNumber(s, a.nation)).treasury -= cost;
        p.paidIpp = cost;
        p.flags[mark::completed] = 1;
        p.flags[MarkKey(mark::lend_to, recipient)] = 1;
        p.flags[a.kind == "economy_lease_upgrade" ? mark::lease_militia_upgrade : mark::lease_repair] = 1;
        if (const auto *target = a.parameters.find("target"))
            p.flags[MarkKey(mark::lease_repair_target, target->asString())] = 1;
        s.construction.emplace(p.id, std::move(p));
        s.nations.at(nationNumber(s, a.nation)).turnFlags[MarkKey(mark::lease_declared, recipient)] = 1;
        return true;
    }
    if (a.kind == "economy_lease_place") {
        const auto id = a.parameters.require("project").asString();
        const auto p = s.construction.at(id);
        if (value(p.flags, mark::lease_militia_upgrade)) {
            auto &u = s.units.at(a.parameters.require("target").asString());
            ++s.nations.at(u.owner).turnFlags[mark::economy_militia_upgrades];
            u.type = knownUnitTypes(s).infantry;
            u.movementAllowance =
                s.definition->catalog->stats(u.type, 0, catalogContext(s, u.owner, u.zone)).movement;
            u.movementRemaining = 0;
        } else {
            FacilityState f;
            f.id = unique(s, "lease_base");
            f.zone = zoneNumber(s, a.parameters.require("zone").asString());
            f.type = p.type.facility();
            f.flags[mark::placed_this_turn] = 1;
            f.flags[MarkKey(mark::original_owner, nationName(s, p.owner))] = 1;
            f.flags[MarkKey(mark::original_type, facilityTypeName(s, f.type))] = 1;
            if (const auto *border = a.parameters.find("border"))
                f.flags[MarkKey(mark::border, border->asString())] = 1;
            if (const auto *border = a.parameters.find("border2"))
                f.flags[MarkKey(mark::border, border->asString())] = 1;
            s.facilities.emplace(f.id, std::move(f));
        }
        s.construction.erase(id);
        return true;
    }
    if (a.kind == "economy_lease_deliver") {
        const auto id = a.parameters.require("project").asString();
        auto &p = s.construction.at(id);
        const auto recipientName = *marker(p.flags, mark::lend_to);
        const auto recipient = nationNumber(s, recipientName);
        const auto sender = nationNumber(s, a.nation);
        const auto zone = zoneNumber(s, a.parameters.require("zone").asString());
        s.nations.at(sender).turnFlags[MarkKey(mark::lease_delivered, recipientName)] = 1;
        if (const auto *factory = a.parameters.find("factory"))
            ++s.nations.at(sender).turnFlags[MarkKey(mark::economy_used, factory->asString())];
        if (value(p.flags, mark::lease_repair)) {
            const auto target = marker(p.flags, mark::lease_repair_target);
            require(target && s.facilities.contains(*target) &&
                        s.territories.at(s.facilities.at(*target).zone).possessor == recipient,
                    "Lend-lease repair target lost");
            RepairJob job;
            job.id = "lease_repair_" + id;
            job.owner = recipient;
            job.target = *target;
            job.remainingDamage = p.paidIpp;
            job.restrictsAction = false;
            s.repairs.emplace(job.id, std::move(job));
            s.nations.at(recipient).gameFlags[MarkKey(mark::lease_repair_wait, *target)] =
                s.completedTurns.at(controllerTurn(s, recipient)) +
                (controllerTurn(s, recipient) == sender ? 1 : 0);
            s.construction.erase(id);
        } else if (value(p.flags, mark::lease_militia_upgrade) || baseType(s, p.type)) {
            p.flags.erase(MarkKey(mark::lend_to, recipientName));
            p.owner = recipient;
            p.site.reset();
            p.flags[mark::lease_received] = 1;
            p.flags[MarkKey(mark::lease_sender, a.nation)] = 1;
            const auto controller = controllerTurn(s, recipient);
            p.flags[MarkKey(mark::lease_wait_controller, nationName(s, controller))] = 1;
            p.flags[mark::lease_available_after_turns] =
                s.completedTurns.at(controller) + (controller == sender ? 1 : 0);
        } else {
            UnitState u;
            u.id = unique(s, "lease_unit");
            u.type = p.type.unit();
            u.owner = recipient;
            if (u.type == knownUnitTypes(s).elite_airborne_infantry &&
                !hasTechnology(s, recipient, knownTechnologies(s).airborne_doctrine))
                u.type = knownUnitTypes(s).airborne_infantry;
            const auto conversions =
                s.definition->catalog->automaticConversions(u.type, catalogContext(s, recipient, zone));
            if (!conversions.empty())
                u.type = conversions.front().to.unit();
            u.zone = u.turnOrigin = a.parameters.find("sea") ? zoneNumber(s, a.parameters.require("sea").asString()) : zone;
            u.movementAllowance =
                s.definition->catalog->stats(u.type, 0, catalogContext(s, recipient, zone)).movement;
            u.movementRemaining = 0;
            u.turnFlags[mark::placed_this_turn] = 1;
            if (const auto *port = a.parameters.find("port"))
                u.gameFlags[MarkKey(mark::in_port, port->asString())] = 1;
            s.units.emplace(u.id, std::move(u));
            s.construction.erase(id);
        }
        return true;
    }
    return false;
}
} // namespace game::campaign
