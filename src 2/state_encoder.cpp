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

const std::vector<UnitKind>& trackedStateUnitKinds() {
    static const std::vector<UnitKind> kinds{
        UnitKind::Infantry,
        UnitKind::Artillery,
        UnitKind::Marine,
        UnitKind::Fighter,
        UnitKind::Transport,
    };
    return kinds;
}

struct ZoneCounts {
    std::unordered_map<std::string, std::unordered_map<UnitKind, int>> unitsByNationAndKind;
    std::unordered_map<std::string, std::unordered_map<UnitKind, int>> movableUnitsByNationAndKind;
    std::unordered_map<std::string, std::unordered_map<UnitKind, int>> pendingUnitsByNationAndKind;
    std::unordered_map<UnitKind, int> otherUnitsByKind;
    std::unordered_map<UnitKind, int> otherMovableUnitsByKind;
    std::unordered_map<UnitKind, int> otherPendingUnitsByKind;
};

std::unordered_map<std::string, ZoneCounts> buildZoneCounts(const GameState& gameState) {
    std::unordered_map<std::string, ZoneCounts> zoneCounts;
    for (const auto& unitPtr : gameState.units()) {
        const auto& unit = *unitPtr;

        auto& counts = zoneCounts[unit.zoneId()];
        if (gameState.hasNation(unit.ownerId())) {
            ++counts.unitsByNationAndKind[unit.ownerId()][unit.kind()];
            if (unit.movementLeft() > 0) {
                ++counts.movableUnitsByNationAndKind[unit.ownerId()][unit.kind()];
            }
        } else {
            ++counts.otherUnitsByKind[unit.kind()];
            if (unit.movementLeft() > 0) {
                ++counts.otherMovableUnitsByKind[unit.kind()];
            }
        }

        if (!unit.hasPendingCombatTarget()) {
            continue;
        }

        auto& pendingCounts = zoneCounts[*unit.pendingCombatTargetZoneId()];
        if (gameState.hasNation(unit.ownerId())) {
            ++pendingCounts.pendingUnitsByNationAndKind[unit.ownerId()][unit.kind()];
        } else {
            ++pendingCounts.otherPendingUnitsByKind[unit.kind()];
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
            for (const auto unitKind : trackedStateUnitKinds()) {
                const auto nationUnitsIt = counts.unitsByNationAndKind.find(nationId);
                const auto unitCount = nationUnitsIt != counts.unitsByNationAndKind.end()
                                           && nationUnitsIt->second.find(unitKind) != nationUnitsIt->second.end()
                    ? nationUnitsIt->second.at(unitKind)
                    : 0;
                features.push_back(static_cast<double>(unitCount));

                const auto nationMovableIt = counts.movableUnitsByNationAndKind.find(nationId);
                const auto movableCount = nationMovableIt != counts.movableUnitsByNationAndKind.end()
                                              && nationMovableIt->second.find(unitKind)
                                                  != nationMovableIt->second.end()
                    ? nationMovableIt->second.at(unitKind)
                    : 0;
                features.push_back(static_cast<double>(movableCount));

                const auto nationPendingIt = counts.pendingUnitsByNationAndKind.find(nationId);
                const auto pendingCount = nationPendingIt != counts.pendingUnitsByNationAndKind.end()
                                              && nationPendingIt->second.find(unitKind)
                                                  != nationPendingIt->second.end()
                    ? nationPendingIt->second.at(unitKind)
                    : 0;
                features.push_back(static_cast<double>(pendingCount));
            }
        }

        for (const auto unitKind : trackedStateUnitKinds()) {
            const auto otherCountIt = counts.otherUnitsByKind.find(unitKind);
            const auto otherMovableIt = counts.otherMovableUnitsByKind.find(unitKind);
            const auto otherPendingIt = counts.otherPendingUnitsByKind.find(unitKind);
            features.push_back(otherCountIt != counts.otherUnitsByKind.end()
                                   ? static_cast<double>(otherCountIt->second)
                                   : 0.0);
            features.push_back(otherMovableIt != counts.otherMovableUnitsByKind.end()
                                   ? static_cast<double>(otherMovableIt->second)
                                   : 0.0);
            features.push_back(otherPendingIt != counts.otherPendingUnitsByKind.end()
                                   ? static_cast<double>(otherPendingIt->second)
                                   : 0.0);
        }
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
    features.push_back(static_cast<double>(gameState.unitValueFor(trackedNationId_)));
    features.push_back(static_cast<double>(gameState.enemyUnitValueDestroyedByNation(trackedNationId_)));

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
    output << "|reward_components="
           << gameState.unitValueFor(trackedNationId_)
           << ":"
           << gameState.enemyUnitValueDestroyedByNation(trackedNationId_);

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
            for (const auto unitKind : trackedStateUnitKinds()) {
                const auto nationUnitsIt = counts.unitsByNationAndKind.find(nationId);
                const auto nationMovableIt = counts.movableUnitsByNationAndKind.find(nationId);
                const auto nationPendingIt = counts.pendingUnitsByNationAndKind.find(nationId);
                const auto unitCount = nationUnitsIt != counts.unitsByNationAndKind.end()
                                           && nationUnitsIt->second.find(unitKind) != nationUnitsIt->second.end()
                    ? nationUnitsIt->second.at(unitKind)
                    : 0;
                const auto movableCount = nationMovableIt != counts.movableUnitsByNationAndKind.end()
                                              && nationMovableIt->second.find(unitKind)
                                                  != nationMovableIt->second.end()
                    ? nationMovableIt->second.at(unitKind)
                    : 0;
                const auto pendingCount = nationPendingIt != counts.pendingUnitsByNationAndKind.end()
                                              && nationPendingIt->second.find(unitKind)
                                                  != nationPendingIt->second.end()
                    ? nationPendingIt->second.at(unitKind)
                    : 0;
                output << ":" << nationId
                       << "." << toString(unitKind)
                       << "=" << unitCount
                       << "/" << movableCount
                       << "/" << pendingCount;
            }
        }

        for (const auto unitKind : trackedStateUnitKinds()) {
            const auto otherCountIt = counts.otherUnitsByKind.find(unitKind);
            const auto otherMovableIt = counts.otherMovableUnitsByKind.find(unitKind);
            const auto otherPendingIt = counts.otherPendingUnitsByKind.find(unitKind);
            output << ":other." << toString(unitKind)
                   << "=" << (otherCountIt != counts.otherUnitsByKind.end() ? otherCountIt->second : 0)
                   << "/" << (otherMovableIt != counts.otherMovableUnitsByKind.end() ? otherMovableIt->second : 0)
                   << "/" << (otherPendingIt != counts.otherPendingUnitsByKind.end() ? otherPendingIt->second : 0);
        }
    }

    return output.str();
}

std::size_t StateEncoder::featureCount() const {
    const auto perZoneFeatureCount =
        controllerOrder_.size() + 4 + nationOrder_.size() * trackedStateUnitKinds().size() * 3
        + trackedStateUnitKinds().size() * 3;
    const auto globalFeatureCount = nationOrder_.size() + 6 + nationOrder_.size() + nationOrder_.size()
                                    + nationOrder_.size() + trackedPurchaseUnitKinds().size() + 2 + 3;
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
            for (const auto unitKind : trackedStateUnitKinds()) {
                const auto unitKindName = std::string(toString(unitKind));
                labels.push_back(zoneId + "." + unitKindName + "_count." + nationId);
                labels.push_back(zoneId + ".movable_" + unitKindName + "_count." + nationId);
                labels.push_back(zoneId + ".pending_" + unitKindName + "_count." + nationId);
            }
        }

        for (const auto unitKind : trackedStateUnitKinds()) {
            const auto unitKindName = std::string(toString(unitKind));
            labels.push_back(zoneId + "." + unitKindName + "_count.other");
            labels.push_back(zoneId + ".movable_" + unitKindName + "_count.other");
            labels.push_back(zoneId + ".pending_" + unitKindName + "_count.other");
        }
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
    labels.push_back("global.tracked_nation_unit_value");
    labels.push_back("global.tracked_nation_destroyed_enemy_unit_value");

    labels.push_back("global.at_war.Japan_vs_CCP");
    labels.push_back("global.at_war.Japan_vs_KMT");
    labels.push_back("global.at_war.CCP_vs_KMT");

    return labels;
}

}  // namespace game
