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
void require(bool c, const std::string &why) {
    if (!c)
        throw std::runtime_error(why);
}
int value(const std::map<Id, int> &flags, const Id &key) {
    const auto i = flags.find(key);
    return i == flags.end() ? 0 : i->second;
}
std::optional<Id> marker(const std::map<Id, int> &flags, const Id &prefix) {
    for (const auto &[key, n] : flags)
        if (n && key.rfind(prefix, 0) == 0)
            return key.substr(prefix.size());
    return {};
}
Action action(const State &s, const Id &kind, O args = {}) {
    Action a;
    a.nation = s.currentNation();
    a.player = politicalPlayer(s, a.nation);
    a.kind = kind;
    a.parameters = V(std::move(args));
    a.id = kind + ":" + contentDigest(canonicalJson(a.parameters));
    return a;
}
Id unique(State &s, const Id &prefix) {
    return "economy_" + prefix + "_" + std::to_string(++s.flags["economy_sequence"]);
}
bool recipientHome(const State &s, const Id &recipient, const Id &zone) {
    return s.territories.at(zone).possessor == recipient &&
           (s.definition->factions.at(recipient).homeCountry.contains(zone) ||
            (recipient == "dadao" && chineseHomeCountry(s, zone)));
}
bool baseType(const Id &type) {
    return type == "airbase" || type == "seaplane_base" || type == "submarine_base";
}
bool techUnit(const State &s, const BuildProject &p) {
    if (p.type == "elite_airborne_infantry")
        return false; // RB47 expressly permits its lend-lease conversion.
    for (const auto &[id, row] : s.definition->catalog->rows())
        if (row.nation == p.owner && row.type == p.type && row.kind == "purchase" &&
            !row.requiredTechnologies.empty())
            return true;
    return false;
}
bool ready(const BuildProject &p) {
    return p.remainingPayments.empty();
}
bool available(const State &s, const BuildProject &p) {
    const auto gate = marker(p.flags, "lease_wait_controller:");
    if (!gate)
        return true;
    return s.completedTurns.at(*gate) >= value(p.flags, "lease_available_after_turns");
}
Id controllerTurn(const State &s, const Id &nation) {
    if (s.completedTurns.contains(nation))
        return nation;
    if (s.nations.at(nation).controllerNation)
        return *s.nations.at(nation).controllerNation;
    return "japan";
}
std::vector<std::pair<Id, Id>> senderFactories(const State &s, const BuildProject &p) {
    std::vector<std::pair<Id, Id>> out;
    if (s.definition->catalog->facilities().contains(p.type) || value(p.flags, "lease_militia_upgrade") ||
        value(p.flags, "lease_repair"))
        return {{"", ""}};
    const bool naval = s.definition->catalog->unit(p.type).classes.contains("naval");
    const bool capital = s.definition->catalog->unit(p.type).classes.contains("capital_ship");
    if (p.type == "militia")
        return {{"", ""}};
    if (decentralizedProduction(s, p.owner) &&
        (s.definition->catalog->unit(p.type).classes.contains("infantry_class") || p.type == "cavalry"))
        return {{"", ""}};
    for (const auto &[id, f] : s.facilities)
        if (facilityCapacity(s, p.owner, id, false) > 0 &&
            (naval ? (f.type.find("shipyard") != Id::npos && (!capital || f.type == "major_shipyard"))
                   : (f.type == "minor_factory" || f.type == "medium_factory" || f.type == "major_factory")))
            out.emplace_back(id, f.zone);
    return out;
}
bool transportable(const State &s, const BuildProject &p, const SupplyRoute &route) {
    if (!route.connected)
        return false;
    if (!s.definition->catalog->units().contains(p.type) ||
        !s.definition->catalog->unit(p.type).classes.contains("naval"))
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
            if (value(p.flags, "lease_militia_upgrade")) {
                const auto sender = marker(p.flags, "lease_sender:");
                const bool supplied = inSupply(s, p.owner, zone) ||
                                      (sender && lendLeaseSupplyRoute(s, *sender, p.owner, zone).connected);
                for (const auto &[id, u] : s.units)
                    if (supplied && value(s.nations.at(p.owner).turnFlags, "economy_militia_upgrades") < 2 &&
                        u.owner == p.owner && u.zone == zone && u.type == "militia" &&
                        !value(u.turnFlags, "placed_this_turn"))
                        out.push_back(
                            action(s, "economy_lease_place", {{"project", V(p.id)}, {"target", V(id)}}));
            } else if (baseType(p.type)) {
                if (p.type == "airbase") {
                    bool exists = false;
                    for (const auto &[id, f] : s.facilities)
                        if (f.zone == zone && f.type == "airbase")
                            exists = true;
                    if (!exists)
                        out.push_back(
                            action(s, "economy_lease_place", {{"project", V(p.id)}, {"zone", V(zone)}}));
                } else
                    for (const auto &edge : s.definition->geography.require("nodes")
                                                .require(zone)
                                                .require("neighbors")
                                                .asArray()) {
                        const auto sea = edge.require("neighbor_id").asString();
                        if (!s.territories.contains(sea)) {
                            O args{{"project", V(p.id)}, {"zone", V(zone)}, {"border", V(sea)}};
                            out.push_back(action(s, "economy_lease_place", args));
                            for (const auto &next : s.definition->geography.require("nodes")
                                                        .require(zone)
                                                        .require("neighbors")
                                                        .asArray()) {
                                const auto second = next.require("neighbor_id").asString();
                                if (sea < second && !s.territories.contains(second)) {
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

bool lendLeasePermitted(const State &s, const Id &sender, const Id &recipient) {
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
    if (sender == "japan" && recipient == "dadao" && controlledBy(s, recipient, sender))
        return true;
    if (sender != "japan" && sender != "kmt" && sender != "ccp")
        return false;
    return atWarWithMajor(s, recipient);
}
std::vector<Action> lendLeaseActions(const State &s) {
    std::vector<Action> out;
    if (s.terminal || s.chance || !s.decisions.empty())
        return out;
    const auto sender = s.currentNation();
    const auto &n = s.nations.at(sender);
    if (s.clock.phase == Phase::Production && value(n.turnFlags, "economy_research_finished")) {
        for (const auto &[recipient, r] : s.nations)
            if (lendLeasePermitted(s, sender, recipient) &&
                !value(n.turnFlags, "lease_declared:" + recipient)) {
                for (const auto &[id, p] : s.construction)
                    if (p.owner == sender && ready(p) && !value(p.flags, "national_objective_award") &&
                        !marker(p.flags, "lend_to:") && !marker(p.flags, "target:") &&
                        !value(p.flags, "unit_upgrade") && !value(p.flags, "facility_upgrade") &&
                        !value(p.flags, "lease_received") &&
                        (!s.definition->catalog->facilities().contains(p.type) || baseType(p.type)) &&
                        !techUnit(s, p))
                        out.push_back(action(s, "economy_lease_declare",
                                             {{"project", V(id)}, {"recipient", V(recipient)}}));
                if (n.treasury && *n.treasury >= 2)
                    out.push_back(action(s, "economy_lease_upgrade", {{"recipient", V(recipient)}}));
                for (const auto &[id, f] : s.facilities)
                    if (s.territories.at(f.zone).possessor == recipient && f.damage > 0 && n.treasury &&
                        *n.treasury >= f.damage)
                        out.push_back(action(s, "economy_lease_repair",
                                             {{"recipient", V(recipient)}, {"target", V(id)}}));
            }
    }
    if (s.clock.phase != Phase::PlaceUnits)
        return out;
    for (const auto &[id, p] : s.construction) {
        if (value(p.flags, "lease_received")) {
            auto choices = recipientPlacements(s, p);
            out.insert(out.end(), choices.begin(), choices.end());
            continue;
        }
        const auto recipient = marker(p.flags, "lend_to:");
        if (p.owner != sender || !recipient || !ready(p) || !lendLeasePermitted(s, sender, *recipient) ||
            value(n.turnFlags, "lease_delivered:" + *recipient))
            continue;
        for (const auto &[zone, t] : s.territories)
            if (recipientHome(s, *recipient, zone)) {
                const bool ship = s.definition->catalog->units().contains(p.type) &&
                                  s.definition->catalog->unit(p.type).classes.contains("naval");
                const auto route = lendLeaseSupplyRoute(s, sender, *recipient, zone, ship);
                if (!transportable(s, p, route))
                    continue;
                for (const auto &[factory, location] : senderFactories(s, p)) {
                    O params{{"project", V(id)}, {"zone", V(zone)}};
                    if (!factory.empty())
                        params["factory"] = V(factory);
                    if (s.definition->catalog->units().contains(p.type) &&
                        s.definition->catalog->unit(p.type).classes.contains("naval")) {
                        // Delivery in port is allowed; submarines need a submarine base.
                        const bool sub = s.definition->catalog->unit(p.type).classes.contains("submarine");
                        if (!route.facilities.empty())
                            for (const auto &sea : navalFacilitySeaZones(s, route.facilities.back())) {
                                auto afloat = params;
                                afloat["sea"] = V(sea);
                                out.push_back(action(s, "economy_lease_deliver", std::move(afloat)));
                            }
                        for (const auto &[fid, f] : s.facilities)
                            if (f.zone == zone && f.damage == 0 &&
                                (sub ? f.type == "submarine_base"
                                     : f.type.rfind("major_", 0) == 0 &&
                                           f.type.find("factory") == Id::npos)) {
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
        p.flags["lend_to:" + recipient] = 1;
        s.nations.at(a.nation).turnFlags["lease_declared:" + recipient] = 1;
        return true;
    }
    if (a.kind == "economy_lease_upgrade" || a.kind == "economy_lease_repair") {
        const auto recipient = a.parameters.require("recipient").asString();
        BuildProject p;
        p.id = unique(s, "lease");
        p.owner = a.nation;
        p.type = a.kind == "economy_lease_upgrade"
                     ? "infantry"
                     : s.facilities.at(a.parameters.require("target").asString()).type;
        const int cost = a.kind == "economy_lease_upgrade"
                             ? 2
                             : s.facilities.at(a.parameters.require("target").asString()).damage;
        *s.nations.at(a.nation).treasury -= cost;
        p.paidIpp = cost;
        p.flags["completed"] = 1;
        p.flags["lend_to:" + recipient] = 1;
        p.flags[a.kind == "economy_lease_upgrade" ? "lease_militia_upgrade" : "lease_repair"] = 1;
        if (const auto *target = a.parameters.find("target"))
            p.flags["lease_repair_target:" + target->asString()] = 1;
        s.construction.emplace(p.id, std::move(p));
        s.nations.at(a.nation).turnFlags["lease_declared:" + recipient] = 1;
        return true;
    }
    if (a.kind == "economy_lease_place") {
        const auto id = a.parameters.require("project").asString();
        const auto p = s.construction.at(id);
        if (value(p.flags, "lease_militia_upgrade")) {
            auto &u = s.units.at(a.parameters.require("target").asString());
            ++s.nations.at(u.owner).turnFlags["economy_militia_upgrades"];
            u.type = "infantry";
            u.movementAllowance =
                s.definition->catalog->stats(u.type, 0, catalogContext(s, u.owner, u.zone)).movement;
            u.movementRemaining = 0;
        } else {
            FacilityState f;
            f.id = unique(s, "lease_base");
            f.zone = a.parameters.require("zone").asString();
            f.type = p.type;
            f.flags["placed_this_turn"] = 1;
            f.flags["original_owner:" + p.owner] = 1;
            f.flags["original_type:" + p.type] = 1;
            if (const auto *border = a.parameters.find("border"))
                f.flags["border:" + border->asString()] = 1;
            if (const auto *border = a.parameters.find("border2"))
                f.flags["border:" + border->asString()] = 1;
            s.facilities.emplace(f.id, std::move(f));
        }
        s.construction.erase(id);
        return true;
    }
    if (a.kind == "economy_lease_deliver") {
        const auto id = a.parameters.require("project").asString();
        auto &p = s.construction.at(id);
        const auto recipient = *marker(p.flags, "lend_to:");
        const auto zone = a.parameters.require("zone").asString();
        s.nations.at(a.nation).turnFlags["lease_delivered:" + recipient] = 1;
        if (const auto *factory = a.parameters.find("factory"))
            ++s.nations.at(a.nation).turnFlags["economy_used:" + factory->asString()];
        if (value(p.flags, "lease_repair")) {
            const auto target = marker(p.flags, "lease_repair_target:");
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
            s.nations.at(recipient).gameFlags["lease_repair_wait:" + *target] =
                s.completedTurns.at(controllerTurn(s, recipient)) +
                (controllerTurn(s, recipient) == a.nation ? 1 : 0);
            s.construction.erase(id);
        } else if (value(p.flags, "lease_militia_upgrade") || baseType(p.type)) {
            p.flags.erase("lend_to:" + recipient);
            p.owner = recipient;
            p.site.reset();
            p.flags["lease_received"] = 1;
            p.flags["lease_sender:" + a.nation] = 1;
            const auto controller = controllerTurn(s, recipient);
            p.flags["lease_wait_controller:" + controller] = 1;
            p.flags["lease_available_after_turns"] =
                s.completedTurns.at(controller) + (controller == a.nation ? 1 : 0);
        } else {
            UnitState u;
            u.id = unique(s, "lease_unit");
            u.type = p.type;
            u.owner = recipient;
            if (u.type == "elite_airborne_infantry" &&
                value(s.nations.at(recipient).technologyStages, "airborne_doctrine") != 4)
                u.type = "airborne_infantry";
            const auto conversions =
                s.definition->catalog->automaticConversions(u.type, catalogContext(s, recipient, zone));
            if (!conversions.empty())
                u.type = conversions.front().to;
            u.zone = u.turnOrigin = a.parameters.find("sea") ? a.parameters.require("sea").asString() : zone;
            u.movementAllowance =
                s.definition->catalog->stats(u.type, 0, catalogContext(s, recipient, zone)).movement;
            u.movementRemaining = 0;
            u.turnFlags["placed_this_turn"] = 1;
            if (const auto *port = a.parameters.find("port"))
                u.gameFlags["in_port:" + port->asString()] = 1;
            s.units.emplace(u.id, std::move(u));
            s.construction.erase(id);
        }
        return true;
    }
    return false;
}
} // namespace game::campaign
