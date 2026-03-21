#include "game/action_encoder.hpp"

#include <algorithm>
#include <stdexcept>

namespace game {

namespace {

bool isInfantry(const Unit& unit) {
    return unit.kind() == UnitKind::Infantry;
}

const std::vector<UnitKind>& unitKindOrder() {
    static const std::vector<UnitKind> order{
        UnitKind::Infantry,
        UnitKind::Artillery,
        UnitKind::Marine,
        UnitKind::Fighter,
        UnitKind::Transport,
    };
    return order;
}

void appendOneHotIndex(std::vector<double>& features, std::size_t size, std::optional<std::size_t> activeIndex) {
    for (std::size_t index = 0; index < size; ++index) {
        features.push_back(activeIndex.has_value() && *activeIndex == index ? 1.0 : 0.0);
    }
}

double availableUnitCountForAction(
    const GameState& gameState,
    std::string_view trackedNationId,
    const Action& action) {
    if (action.kind == ActionKind::PurchaseUnit) {
        if (!action.unitKind.has_value()) {
            return 0.0;
        }
        const auto remainingCapacity = std::max(
            0,
            gameState.totalFactoryOutputForNation(trackedNationId) - gameState.pendingPurchaseCountFor(trackedNationId));
        const auto cost = purchaseCost(*action.unitKind);
        if (cost <= 0) {
            return 0.0;
        }
        const auto affordableCount = gameState.nation(trackedNationId).treasury() / cost;
        return static_cast<double>(std::min(remainingCapacity, affordableCount));
    }

    if (action.kind == ActionKind::MoveCombatUnit) {
        if (!action.sourceZoneId.has_value()) {
            return 0.0;
        }

        double availableCount = 0.0;
        for (const auto* unit : gameState.unitsInZone(*action.sourceZoneId)) {
            if (unit->ownerId() == trackedNationId
                && isInfantry(*unit)
                && unit->movementLeft() > 0
                && !unit->hasPendingCombatTarget()) {
                availableCount += 1.0;
            }
        }
        return availableCount;
    }

    if (action.kind == ActionKind::ResolveCombat) {
        if (!action.targetZoneId.has_value()) {
            return 0.0;
        }

        double availableCount = 0.0;
        for (const auto& unitPtr : gameState.units()) {
            const auto& unit = *unitPtr;
            if (unit.ownerId() == trackedNationId
                && isInfantry(unit)
                && unit.hasPendingCombatTarget()
                && *unit.pendingCombatTargetZoneId() == *action.targetZoneId) {
                availableCount += 1.0;
            }
        }
        return availableCount;
    }

    if (action.kind == ActionKind::PlaceUnit) {
        if (!action.targetZoneId.has_value() || !action.unitKind.has_value()) {
            return 0.0;
        }
        const auto remainingCapacity = gameState.remainingPlacementCapacityForZone(
            trackedNationId,
            *action.targetZoneId);
        const auto pendingCount = gameState.pendingPurchaseCountFor(trackedNationId, *action.unitKind);
        return static_cast<double>(std::min(remainingCapacity, pendingCount));
    }

    return 0.0;
}

double requestedUnitCountForAction(
    const GameState& gameState,
    std::string_view trackedNationId,
    const Action& action) {
    if (action.kind == ActionKind::PurchaseUnit
        || action.kind == ActionKind::MoveCombatUnit
        || action.kind == ActionKind::PlaceUnit) {
        return action.unitCount.has_value() ? static_cast<double>(*action.unitCount) : 0.0;
    }

    if (action.kind == ActionKind::ResolveCombat) {
        return availableUnitCountForAction(gameState, trackedNationId, action);
    }

    return 0.0;
}

std::optional<std::size_t> zoneIndexFor(
    const std::vector<std::string>& zoneOrder,
    const std::optional<std::string>& zoneId,
    const char* label) {
    if (!zoneId.has_value()) {
        return std::nullopt;
    }

    const auto it = std::find(zoneOrder.begin(), zoneOrder.end(), *zoneId);
    if (it == zoneOrder.end()) {
        throw std::runtime_error(std::string("Unknown ") + label + " zone in ActionEncoder: " + *zoneId);
    }
    return static_cast<std::size_t>(std::distance(zoneOrder.begin(), it));
}

}  // namespace

ActionEncoder ActionEncoder::forNation(const GameState& gameState, std::string trackedNationId) {
    ActionEncoder encoder;
    encoder.trackedNationId_ = std::move(trackedNationId);

    for (const auto& [zoneId, zone] : gameState.zones()) {
        encoder.zoneOrder_.push_back(zoneId);
    }
    std::sort(encoder.zoneOrder_.begin(), encoder.zoneOrder_.end());
    return encoder;
}

std::vector<double> ActionEncoder::encode(const GameState& gameState, const Action& action) const {
    std::vector<double> features;
    features.reserve(featureCount());

    features.push_back(action.kind == ActionKind::DeclareWarOnChina ? 1.0 : 0.0);
    features.push_back(action.kind == ActionKind::PurchaseUnit ? 1.0 : 0.0);
    features.push_back(action.kind == ActionKind::MoveCombatUnit ? 1.0 : 0.0);
    features.push_back(action.kind == ActionKind::ResolveCombat ? 1.0 : 0.0);
    features.push_back(action.kind == ActionKind::PlaceUnit ? 1.0 : 0.0);
    features.push_back(action.kind == ActionKind::EndPhase ? 1.0 : 0.0);

    const auto sourceIndex = zoneIndexFor(zoneOrder_, action.sourceZoneId, "source");
    appendOneHotIndex(features, zoneOrder_.size(), sourceIndex);

    const auto targetIndex = zoneIndexFor(zoneOrder_, action.targetZoneId, "target");
    appendOneHotIndex(features, zoneOrder_.size(), targetIndex);

    const auto activeUnitKind = [&]() -> std::optional<std::size_t> {
        if (!action.unitKind.has_value()) {
            return std::nullopt;
        }
        const auto& order = unitKindOrder();
        const auto it = std::find(order.begin(), order.end(), *action.unitKind);
        if (it == order.end()) {
            throw std::runtime_error("Unknown unit kind in ActionEncoder");
        }
        return static_cast<std::size_t>(std::distance(order.begin(), it));
    }();
    appendOneHotIndex(features, unitKindOrder().size(), activeUnitKind);

    const auto unitCount = requestedUnitCountForAction(gameState, trackedNationId_, action);
    const auto availableCount = availableUnitCountForAction(gameState, trackedNationId_, action);
    const auto unitFraction = availableCount > 0.0 ? unitCount / availableCount : 0.0;

    features.push_back(unitCount);
    features.push_back(availableCount);
    features.push_back(unitFraction);

    return features;
}

std::size_t ActionEncoder::featureCount() const {
    return 6 + zoneOrder_.size() + zoneOrder_.size() + unitKindOrder().size() + 3;
}

std::vector<std::string> ActionEncoder::featureLabels() const {
    std::vector<std::string> labels;
    labels.reserve(featureCount());

    labels.push_back("action_kind.declare_war_on_china");
    labels.push_back("action_kind.purchase_unit");
    labels.push_back("action_kind.move_combat_unit");
    labels.push_back("action_kind.resolve_combat");
    labels.push_back("action_kind.place_unit");
    labels.push_back("action_kind.end_phase");

    for (const auto& zoneId : zoneOrder_) {
        labels.push_back("source_zone." + zoneId);
    }
    for (const auto& zoneId : zoneOrder_) {
        labels.push_back("target_zone." + zoneId);
    }
    for (const auto unitKind : unitKindOrder()) {
        labels.push_back("unit_kind." + std::string(toString(unitKind)));
    }
    labels.push_back("requested_unit_count");
    labels.push_back("available_unit_count");
    labels.push_back("requested_unit_fraction");

    return labels;
}

}  // namespace game
