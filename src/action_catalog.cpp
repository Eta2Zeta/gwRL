#include "game/action_catalog.hpp"

#include <algorithm>
#include <stdexcept>

namespace game {

namespace {

bool isInfantry(const Unit& unit) {
    return unit.kind() == UnitKind::Infantry;
}

}  // namespace

ActionCatalog ActionCatalog::forNation(const GameState& gameState, std::string nationId) {
    ActionCatalog catalog;
    catalog.entries_.push_back(Action{.kind = ActionKind::DeclareWarOnChina});

    int maxInfantryPerMove = 0;
    for (const auto& unitPtr : gameState.units()) {
        const auto& unit = *unitPtr;
        if (unit.ownerId() == nationId && isInfantry(unit)) {
            ++maxInfantryPerMove;
        }
    }
    maxInfantryPerMove = std::max(1, maxInfantryPerMove);

    std::vector<std::string> zoneIds;
    zoneIds.reserve(gameState.zones().size());
    for (const auto& [zoneId, zone] : gameState.zones()) {
        if (zone.kind == ZoneKind::Land) {
            zoneIds.push_back(zoneId);
        }
    }
    std::sort(zoneIds.begin(), zoneIds.end());

    for (const auto& sourceZoneId : zoneIds) {
        const auto& sourceZone = gameState.zone(sourceZoneId);
        std::vector<std::string> neighborIds;
        for (const auto& neighbor : sourceZone.neighbors) {
            if (!gameState.hasZone(neighbor.id)) {
                continue;
            }
            if (gameState.zone(neighbor.id).kind != ZoneKind::Land) {
                continue;
            }
            neighborIds.push_back(neighbor.id);
        }
        std::sort(neighborIds.begin(), neighborIds.end());
        neighborIds.erase(std::unique(neighborIds.begin(), neighborIds.end()), neighborIds.end());

        for (const auto& targetZoneId : neighborIds) {
            for (int unitCount = 1; unitCount <= maxInfantryPerMove; ++unitCount) {
                catalog.entries_.push_back(Action{
                    .kind = ActionKind::MoveCombatUnit,
                    .sourceZoneId = sourceZoneId,
                    .targetZoneId = targetZoneId,
                    .unitCount = unitCount,
                });
            }
        }
    }

    catalog.entries_.push_back(Action{.kind = ActionKind::EndPhase});

    for (std::size_t index = 0; index < catalog.entries_.size(); ++index) {
        catalog.indexBySignature_.emplace(signature(catalog.entries_[index]), static_cast<int>(index));
    }
    return catalog;
}

const Action& ActionCatalog::actionAt(int actionId) const {
    if (actionId < 0 || static_cast<std::size_t>(actionId) >= entries_.size()) {
        throw std::runtime_error("Action id out of range");
    }
    return entries_[static_cast<std::size_t>(actionId)];
}

int ActionCatalog::indexOf(const Action& action) const {
    const auto it = indexBySignature_.find(signature(action));
    if (it == indexBySignature_.end()) {
        throw std::runtime_error("Action not present in catalog: " + signature(action));
    }
    return it->second;
}

std::vector<int> ActionCatalog::legalActionIds(const std::vector<Action>& legalActions) const {
    std::vector<int> actionIds;
    actionIds.reserve(legalActions.size());
    for (const auto& action : legalActions) {
        actionIds.push_back(indexOf(action));
    }
    return actionIds;
}

std::string ActionCatalog::signature(const Action& action) {
    std::string value(std::string(toString(action.kind)));
    value += "|from=" + (action.sourceZoneId.has_value() ? *action.sourceZoneId : std::string("-"));
    value += "|to=" + (action.targetZoneId.has_value() ? *action.targetZoneId : std::string("-"));
    value += "|count=" + (action.unitCount.has_value() ? std::to_string(*action.unitCount) : std::string("-"));
    return value;
}

}  // namespace game
