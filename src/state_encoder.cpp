#include "game/state_encoder.hpp"

#include <algorithm>
#include <array>
#include <sstream>
#include <stdexcept>
#include <unordered_map>

namespace game {

namespace {

constexpr std::array<std::string_view, 6> kKnownControllers{
    "CCP",
    "Japan",
    "KMT",
    "ZhiliClique",
    "Mengjiang",
    "Neutral",
};

const std::vector<UnitKind>& trackedPurchaseUnitKinds() {
    static const std::vector<UnitKind> kinds{
        UnitKind::Infantry,
        UnitKind::Artillery,
        UnitKind::Fighter,
    };
    return kinds;
}

struct ZoneCounts {
    std::unordered_map<std::string, int> infantryByNation;
    std::unordered_map<std::string, int> movableInfantryByNation;
    std::unordered_map<std::string, int> pendingInfantryByNation;
    int otherInfantry {0};
    int otherMovableInfantry {0};
    int otherPendingInfantry {0};
};

std::unordered_map<std::string, ZoneCounts> buildZoneCounts(const GameState& gameState) {
    std::unordered_map<std::string, ZoneCounts> zoneCounts;
    for (const auto& unitPtr : gameState.units()) {
        const auto& unit = *unitPtr;
        if (unit.kind() != UnitKind::Infantry) {
            continue;
        }

        auto& counts = zoneCounts[unit.zoneId()];
        if (gameState.hasNation(unit.ownerId())) {
            ++counts.infantryByNation[unit.ownerId()];
            if (unit.movementLeft() > 0) {
                ++counts.movableInfantryByNation[unit.ownerId()];
            }
        } else {
            ++counts.otherInfantry;
            if (unit.movementLeft() > 0) {
                ++counts.otherMovableInfantry;
            }
        }

        if (!unit.hasPendingCombatTarget()) {
            continue;
        }

        auto& pendingCounts = zoneCounts[*unit.pendingCombatTargetZoneId()];
        if (gameState.hasNation(unit.ownerId())) {
            ++pendingCounts.pendingInfantryByNation[unit.ownerId()];
        } else {
            ++pendingCounts.otherPendingInfantry;
        }
    }
    return zoneCounts;
}

void appendOneHot(
    std::vector<double>& features,
    const std::vector<std::string>& orderedValues,
    std::string_view activeValue) {
    for (const auto& value : orderedValues) {
        features.push_back(value == activeValue ? 1.0 : 0.0);
    }
}

std::string safeController(std::string_view controller, const std::vector<std::string>& orderedControllers) {
    if (std::find(orderedControllers.begin(), orderedControllers.end(), controller) != orderedControllers.end()) {
        return std::string(controller);
    }
    return "Neutral";
}

}  // namespace

StateEncoder StateEncoder::forNation(const GameState& gameState, std::string trackedNationId) {
    StateEncoder encoder;
    encoder.trackedNationId_ = std::move(trackedNationId);

    encoder.nationOrder_ = gameState.turnOrder();
    encoder.zoneOrder_.reserve(gameState.zones().size());
    for (const auto& [zoneId, zone] : gameState.zones()) {
        encoder.zoneOrder_.push_back(zoneId);
    }
    std::sort(encoder.zoneOrder_.begin(), encoder.zoneOrder_.end());

    for (const auto controller : kKnownControllers) {
        encoder.controllerOrder_.push_back(std::string(controller));
    }
    for (const auto& [zoneId, zone] : gameState.zones()) {
        if (std::find(encoder.controllerOrder_.begin(), encoder.controllerOrder_.end(), zone.controller)
            == encoder.controllerOrder_.end()) {
            encoder.controllerOrder_.push_back(zone.controller);
        }
    }

    return encoder;
}

std::vector<double> StateEncoder::encode(const GameState& gameState) const {
    if (gameState.turnOrder() != nationOrder_) {
        throw std::runtime_error("StateEncoder received a game state with a different nation order");
    }

    std::vector<double> features;
    const auto zoneCounts = buildZoneCounts(gameState);

    for (const auto& zoneId : zoneOrder_) {
        const auto& zone = gameState.zone(zoneId);
        appendOneHot(features, controllerOrder_, safeController(zone.controller, controllerOrder_));
        features.push_back(zone.isCity ? 1.0 : 0.0);
        features.push_back(static_cast<double>(zone.incomeValue));
        features.push_back(static_cast<double>(gameState.factoryOutputForZone(zoneId)));
        features.push_back(static_cast<double>(gameState.remainingPlacementCapacityForZone(trackedNationId_, zoneId)));

        const auto countsIt = zoneCounts.find(zoneId);
        const ZoneCounts emptyCounts;
        const auto& counts = countsIt != zoneCounts.end() ? countsIt->second : emptyCounts;

        for (const auto& nationId : nationOrder_) {
            const auto infantryIt = counts.infantryByNation.find(nationId);
            features.push_back(
                infantryIt != counts.infantryByNation.end() ? static_cast<double>(infantryIt->second) : 0.0);

            const auto movableIt = counts.movableInfantryByNation.find(nationId);
            features.push_back(
                movableIt != counts.movableInfantryByNation.end() ? static_cast<double>(movableIt->second) : 0.0);

            const auto pendingIt = counts.pendingInfantryByNation.find(nationId);
            features.push_back(
                pendingIt != counts.pendingInfantryByNation.end() ? static_cast<double>(pendingIt->second) : 0.0);
        }

        features.push_back(static_cast<double>(counts.otherInfantry));
        features.push_back(static_cast<double>(counts.otherMovableInfantry));
        features.push_back(static_cast<double>(counts.otherPendingInfantry));
    }

    appendOneHot(features, nationOrder_, gameState.currentNation());
    for (const auto phase : {
             Phase::DeclarationOfWar,
             Phase::PurchaseUnits,
             Phase::CombatMove,
             Phase::CombatResolve,
             Phase::NonCombat,
             Phase::PlaceUnits}) {
        features.push_back(gameState.currentPhase() == phase ? 1.0 : 0.0);
    }

    for (const auto& nationId : nationOrder_) {
        features.push_back(static_cast<double>(gameState.completedTurnsFor(nationId)));
    }
    for (const auto& nationId : nationOrder_) {
        features.push_back(static_cast<double>(gameState.nation(nationId).income()));
    }
    for (const auto& nationId : nationOrder_) {
        features.push_back(static_cast<double>(gameState.nation(nationId).treasury()));
    }
    for (const auto unitKind : trackedPurchaseUnitKinds()) {
        features.push_back(static_cast<double>(gameState.pendingPurchaseCountFor(trackedNationId_, unitKind)));
    }

    features.push_back(gameState.areAtWar("Japan", "CCP") ? 1.0 : 0.0);
    features.push_back(gameState.areAtWar("Japan", "KMT") ? 1.0 : 0.0);
    features.push_back(gameState.areAtWar("CCP", "KMT") ? 1.0 : 0.0);

    return features;
}

std::string StateEncoder::encodeKey(const GameState& gameState) const {
    const auto zoneCounts = buildZoneCounts(gameState);
    std::ostringstream output;

    output << "current=" << gameState.currentNation()
           << "|phase=" << toString(gameState.currentPhase());

    output << "|turns=";
    for (const auto& nationId : nationOrder_) {
        output << nationId << ":" << gameState.completedTurnsFor(nationId) << ",";
    }

    output << "|income=";
    for (const auto& nationId : nationOrder_) {
        const auto& nation = gameState.nation(nationId);
        output << nationId << ":" << nation.income() << ":" << nation.treasury() << ",";
    }

    output << "|pending=";
    for (const auto unitKind : trackedPurchaseUnitKinds()) {
        output << toString(unitKind)
               << ":" << gameState.pendingPurchaseCountFor(trackedNationId_, unitKind)
               << ",";
    }

    output << "|wars="
           << (gameState.areAtWar("Japan", "CCP") ? 1 : 0)
           << (gameState.areAtWar("Japan", "KMT") ? 1 : 0)
           << (gameState.areAtWar("CCP", "KMT") ? 1 : 0);

    for (const auto& zoneId : zoneOrder_) {
        const auto& zone = gameState.zone(zoneId);
        const auto countsIt = zoneCounts.find(zoneId);
        const ZoneCounts emptyCounts;
        const auto& counts = countsIt != zoneCounts.end() ? countsIt->second : emptyCounts;

        output << "|zone=" << zoneId
               << ":ctrl=" << safeController(zone.controller, controllerOrder_)
               << ":city=" << (zone.isCity ? 1 : 0)
               << ":income=" << zone.incomeValue
               << ":factory=" << gameState.factoryOutputForZone(zoneId)
               << ":placement=" << gameState.remainingPlacementCapacityForZone(trackedNationId_, zoneId);

        for (const auto& nationId : nationOrder_) {
            const auto infantryIt = counts.infantryByNation.find(nationId);
            const auto movableIt = counts.movableInfantryByNation.find(nationId);
            const auto pendingIt = counts.pendingInfantryByNation.find(nationId);
            output << ":" << nationId
                   << "=" << (infantryIt != counts.infantryByNation.end() ? infantryIt->second : 0)
                   << "/" << (movableIt != counts.movableInfantryByNation.end() ? movableIt->second : 0)
                   << "/" << (pendingIt != counts.pendingInfantryByNation.end() ? pendingIt->second : 0);
        }

        output << ":other=" << counts.otherInfantry
               << "/" << counts.otherMovableInfantry
               << "/" << counts.otherPendingInfantry;
    }

    return output.str();
}

std::size_t StateEncoder::featureCount() const {
    const auto perZoneFeatureCount = controllerOrder_.size() + 4 + nationOrder_.size() * 3 + 3;
    const auto globalFeatureCount = nationOrder_.size() + 6 + nationOrder_.size() + nationOrder_.size()
                                    + nationOrder_.size() + trackedPurchaseUnitKinds().size() + 3;
    return zoneOrder_.size() * perZoneFeatureCount + globalFeatureCount;
}

std::vector<std::string> StateEncoder::featureLabels() const {
    std::vector<std::string> labels;
    labels.reserve(featureCount());

    for (const auto& zoneId : zoneOrder_) {
        for (const auto& controllerId : controllerOrder_) {
            labels.push_back(zoneId + ".owner." + controllerId);
        }
        labels.push_back(zoneId + ".is_city");
        labels.push_back(zoneId + ".income_value");
        labels.push_back(zoneId + ".factory_output");
        labels.push_back(zoneId + ".remaining_placement_capacity");

        for (const auto& nationId : nationOrder_) {
            labels.push_back(zoneId + ".infantry_count." + nationId);
            labels.push_back(zoneId + ".movable_infantry_count." + nationId);
            labels.push_back(zoneId + ".pending_infantry_count." + nationId);
        }

        labels.push_back(zoneId + ".infantry_count.other");
        labels.push_back(zoneId + ".movable_infantry_count.other");
        labels.push_back(zoneId + ".pending_infantry_count.other");
    }

    for (const auto& nationId : nationOrder_) {
        labels.push_back("global.current_nation." + nationId);
    }
    labels.push_back("global.current_phase.declaration_of_war");
    labels.push_back("global.current_phase.purchase_units");
    labels.push_back("global.current_phase.combat_move");
    labels.push_back("global.current_phase.combat_resolve");
    labels.push_back("global.current_phase.non_combat");
    labels.push_back("global.current_phase.place_units");

    for (const auto& nationId : nationOrder_) {
        labels.push_back("global.completed_turns." + nationId);
    }
    for (const auto& nationId : nationOrder_) {
        labels.push_back("global.income." + nationId);
    }
    for (const auto& nationId : nationOrder_) {
        labels.push_back("global.treasury." + nationId);
    }
    for (const auto unitKind : trackedPurchaseUnitKinds()) {
        labels.push_back("global.pending_purchase." + std::string(toString(unitKind)));
    }

    labels.push_back("global.at_war.Japan_vs_CCP");
    labels.push_back("global.at_war.Japan_vs_KMT");
    labels.push_back("global.at_war.CCP_vs_KMT");

    return labels;
}

}  // namespace game
