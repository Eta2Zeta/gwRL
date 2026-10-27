#include "game/campaign_objective.hpp"
#include "game/catalog.hpp"
#include "game/economy.hpp"
#include "game/movement.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>

namespace game::campaign {
namespace {
using V = json::Value;
using O = V::Object;

std::optional<std::size_t> recipient(const State& s, const std::optional<Id>& nation) {
    if (!nation) return std::nullopt;
    // A temporary policy assigned to independent warlord defense is deliberately
    // absent from NationState.player and must not acquire its neutral assets.
    const auto& player = s.nations.at(*nation).player;
    if (!player) return std::nullopt;
    const auto it = std::find(allianceOrder.begin(), allianceOrder.end(), *player);
    if (it == allianceOrder.end()) throw std::runtime_error("Unknown wealth recipient");
    return static_cast<std::size_t>(it - allianceOrder.begin());
}

int prepaidRepair(const State& s, const Id& target, const Id& owner,
                  const std::optional<Id>& endpoint = std::nullopt) {
    int damage = 0;
    for (const auto& [id, job] : s.repairs)
        if (job.target == target && job.owner == owner && job.endpoint == endpoint && job.remainingCost == 0)
            damage += job.remainingDamage;
    return damage;
}

}  // namespace

int railAssetPrice(const State& s, const RailState& rail) {
    const std::set<Id> harsh{"desert", "jungle", "marsh", "mountain", "tundra", "tundra_ice"};
    const auto approach = borderApproach(s, rail.endpointA, rail.endpointB);
    const auto reverse = borderApproach(s, rail.endpointB, rail.endpointA);
    // Both directed records describe one physical route. Either direction can
    // name its non-normal crossing; intrinsic node terrain is not substituted.
    for (const auto* terrain : {&approach.borderTerrain, &reverse.borderTerrain})
        for (const auto& t : *terrain) if (harsh.contains(t)) return 4;
    return 2;
}

void validateWealthDefinition(const Definition& definition) {
    if (!definition.catalog || !definition.rules.find("scenario_contract"))
        throw std::runtime_error("Wealth objective requires the approved scenario contract and catalog");
    const auto& objective = definition.rules.require("scenario_contract").require("wealth");
    if (objective.require("comparison").asString() != "own_wealth_minus_combined_other_two_sides")
        throw std::runtime_error("Unsupported campaign objective");
    const auto& weights = objective.require("weights");
    if (weights.require("income_rate").asNumber() != 1 ||
        weights.require("unit_value").asNumber() != 0.1 ||
        weights.require("infrastructure_value").asNumber() != 0.1 ||
        weights.require("treasury").asNumber() != 0.1 ||
        weights.require("paid_construction_value").asNumber() != 0.1)
        throw std::runtime_error("Unsupported campaign wealth weights");
}
double WealthComponents::total() const {
    // Codify the fused operation already emitted by the Apple CPU build. This
    // also makes the rounding contract explicit for other compilers/backends.
    return std::fma(0.1, units + infrastructure + treasury + paidConstruction, incomeRate);
}

std::array<WealthComponents, 3> allianceWealth(const State& s) {
    validateWealthDefinition(*s.definition);
    std::array<WealthComponents, 3> values{};
    for (const auto& [nation, n] : s.nations) if (const auto i = recipient(s, nation)) {
        values[*i].incomeRate += evaluateIncome(s, nation).total;
        values[*i].treasury += n.treasury.value_or(0);
    }
    for (const auto& [id, unit] : s.units) if (const auto i = recipient(s, unit.owner)) {
        const bool crew = std::any_of(unit.gameFlags.begin(), unit.gameFlags.end(), [](const auto& flag) {
            return flag.second && flag.first.rfind("ship_crew:", 0) == 0;
        });
        if (crew) continue;
        const auto& type = s.definition->catalog->unit(unit.type);
        const auto* repair = type.repair.isObject() ? type.repair.find("cost_per_hit") : nullptr;
        const int cost = repair && repair->isNumber() ? repair->asInt() : 0;
        const int remainingDamage = std::max(0, unit.damage - prepaidRepair(s, id, unit.owner));
        values[*i].units += completedAssetValue(*s.definition, unit.type) - cost * remainingDamage;
    }
    for (const auto& [id, facility] : s.facilities)
        if (const auto i = recipient(s, s.territories.at(facility.zone).possessor)) {
            const auto& type = s.definition->catalog->facility(facility.type);
            const auto& owner = *s.territories.at(facility.zone).possessor;
            const int remainingDamage = std::max(0, facility.damage - prepaidRepair(s, id, owner));
            values[*i].infrastructure += type.assetValue - remainingDamage * type.repairCost.value_or(0);
        }
    std::set<std::pair<Id, Id>> borders;
    for (const auto& [id, rail] : s.rails) {
        const auto border = std::minmax(rail.endpointA, rail.endpointB);
        if (!borders.emplace(border.first, border.second).second)
            throw std::runtime_error("Duplicate physical railway in wealth valuation");
        int remainingCost = 0;
        for (const auto& [endpoint, damage] : rail.damageByEndpoint) {
            const auto& owner = s.territories.at(endpoint).possessor;
            const int paid = owner ? prepaidRepair(s, id, *owner, endpoint) : 0;
            remainingCost += std::max(0, damage - paid);
        }
        const double half = 0.5 * (railAssetPrice(s, rail) - remainingCost);
        for (const auto& endpoint : {rail.endpointA, rail.endpointB})
            if (const auto i = recipient(s, s.territories.at(endpoint).possessor))
                values[*i].infrastructure += half;
    }
    // A queue entry remains paid work until it is replaced by its placed asset.
    // Economy removes that project when creating/upgrading the completed piece.
    for (const auto& [id, project] : s.construction)
        if (const auto i = recipient(s, project.owner)) values[*i].paidConstruction += project.paidIpp;
    return values;
}

std::array<double, 3> wealthGaps(const State& s) {
    const auto wealth = allianceWealth(s);
    const double sum = wealth[0].total() + wealth[1].total() + wealth[2].total();
    return {2 * wealth[0].total() - sum, 2 * wealth[1].total() - sum, 2 * wealth[2].total() - sum};
}

std::array<double, 3> terminalReturns(const State& s) {
    return s.terminal ? wealthGaps(s) : std::array<double, 3>{0, 0, 0};
}

V wealthJson(const State& s) {
    const auto values = allianceWealth(s);
    O out;
    for (std::size_t i = 0; i < allianceOrder.size(); ++i) {
        const auto& x = values[i];
        out.emplace(allianceOrder[i], V(O{{"income_rate", V(x.incomeRate)}, {"units", V(x.units)},
            {"infrastructure", V(x.infrastructure)}, {"treasury", V(x.treasury)},
            {"paid_construction", V(x.paidConstruction)}, {"wealth", V(x.total())}}));
    }
    return V(std::move(out));
}
}  // namespace game::campaign
