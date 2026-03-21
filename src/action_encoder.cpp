#include "game/action_encoder.hpp"

#include <algorithm>
#include <stdexcept>

namespace game {

namespace {

bool isInfantry(const Unit& unit) {
    return unit.kind() == UnitKind::Infantry;
}

void appendOneHotIndex(std::vector<double>& features, std::size_t size, std::optional<std::size_t> activeIndex) {
    for (std::size_t index = 0; index < size; ++index) {
        features.push_back(activeIndex.has_value() && *activeIndex == index ? 1.0 : 0.0);
    }
}

double availableCombatInfantryCount(
    const GameState& gameState,
    std::string_view trackedNationId,
    const std::optional<std::string>& sourceZoneId) {
    if (!sourceZoneId.has_value()) {
        return 0.0;
    }

    double availableCount = 0.0;
    for (const auto* unit : gameState.unitsInZone(*sourceZoneId)) {
        if (unit->ownerId() == trackedNationId && isInfantry(*unit) && unit->movementLeft() > 0) {
            availableCount += 1.0;
        }
    }
    return availableCount;
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
    features.push_back(action.kind == ActionKind::MoveCombatUnit ? 1.0 : 0.0);
    features.push_back(action.kind == ActionKind::EndPhase ? 1.0 : 0.0);

    auto sourceIndex = std::optional<std::size_t>{};
    if (action.sourceZoneId.has_value()) {
        const auto it = std::find(zoneOrder_.begin(), zoneOrder_.end(), *action.sourceZoneId);
        if (it == zoneOrder_.end()) {
            throw std::runtime_error("Unknown source zone in ActionEncoder: " + *action.sourceZoneId);
        }
        sourceIndex = static_cast<std::size_t>(std::distance(zoneOrder_.begin(), it));
    }
    appendOneHotIndex(features, zoneOrder_.size(), sourceIndex);

    auto targetIndex = std::optional<std::size_t>{};
    if (action.targetZoneId.has_value()) {
        const auto it = std::find(zoneOrder_.begin(), zoneOrder_.end(), *action.targetZoneId);
        if (it == zoneOrder_.end()) {
            throw std::runtime_error("Unknown target zone in ActionEncoder: " + *action.targetZoneId);
        }
        targetIndex = static_cast<std::size_t>(std::distance(zoneOrder_.begin(), it));
    }
    appendOneHotIndex(features, zoneOrder_.size(), targetIndex);

    const auto unitCount = action.unitCount.has_value() ? static_cast<double>(*action.unitCount) : 0.0;
    const auto availableCount = availableCombatInfantryCount(gameState, trackedNationId_, action.sourceZoneId);
    const auto unitFraction = availableCount > 0.0 ? unitCount / availableCount : 0.0;

    features.push_back(unitCount);
    features.push_back(availableCount);
    features.push_back(unitFraction);

    return features;
}

std::size_t ActionEncoder::featureCount() const {
    return 3 + zoneOrder_.size() + zoneOrder_.size() + 3;
}

std::vector<std::string> ActionEncoder::featureLabels() const {
    std::vector<std::string> labels;
    labels.reserve(featureCount());

    labels.push_back("action_kind.declare_war_on_china");
    labels.push_back("action_kind.move_combat_unit");
    labels.push_back("action_kind.end_phase");

    for (const auto& zoneId : zoneOrder_) {
        labels.push_back("source_zone." + zoneId);
    }
    for (const auto& zoneId : zoneOrder_) {
        labels.push_back("target_zone." + zoneId);
    }
    labels.push_back("combat_unit_count");
    labels.push_back("combat_available_count");
    labels.push_back("combat_unit_fraction");

    return labels;
}

}  // namespace game
