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

}  // namespace

ActionEncoder ActionEncoder::forNation(const GameState& gameState, std::string trackedNationId) {
    ActionEncoder encoder;
    encoder.trackedNationId_ = std::move(trackedNationId);

    for (const auto& [zoneId, zone] : gameState.zones()) {
        encoder.zoneOrder_.push_back(zoneId);
    }
    std::sort(encoder.zoneOrder_.begin(), encoder.zoneOrder_.end());

    int infantryCount = 0;
    for (const auto& unitPtr : gameState.units()) {
        const auto& unit = *unitPtr;
        if (unit.ownerId() == encoder.trackedNationId_ && isInfantry(unit)) {
            ++infantryCount;
        }
    }
    encoder.maxCombatUnitCount_ = std::max(1, infantryCount);
    return encoder;
}

std::vector<double> ActionEncoder::encode(const Action& action) const {
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

    const auto cappedCount = action.unitCount.has_value()
        ? std::min(*action.unitCount, maxCombatUnitCount_)
        : 0;
    for (int count = 0; count <= maxCombatUnitCount_; ++count) {
        features.push_back(cappedCount == count ? 1.0 : 0.0);
    }

    return features;
}

std::size_t ActionEncoder::featureCount() const {
    return 3 + zoneOrder_.size() + zoneOrder_.size() + static_cast<std::size_t>(maxCombatUnitCount_ + 1);
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
    for (int count = 0; count <= maxCombatUnitCount_; ++count) {
        labels.push_back("combat_unit_count." + std::to_string(count));
    }

    return labels;
}

}  // namespace game
