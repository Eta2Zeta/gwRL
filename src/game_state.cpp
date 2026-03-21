#include "game/game_state.hpp"

#include <array>
#include <algorithm>
#include <stdexcept>
#include <unordered_set>

namespace game {

namespace {

constexpr std::array<std::string_view, 7> kWarlordFactions{
    "ZhiliClique",
    "SzechwanClique",
    "SinkiangClique",
    "YunnanClique",
    "GuangxiClique",
    "MaClique",
    "Mengjiang",
};

int facilityOutput(std::string_view facilityId) {
    if (facilityId == "minor_factory") {
        return 1;
    }
    if (facilityId == "medium_factory") {
        return 3;
    }
    if (facilityId == "major_factory") {
        return 5;
    }
    return 0;
}

}  // namespace

void GameState::addNation(Nation nation) {
    const auto nationId = nation.id();
    auto [it, inserted] = nations_.emplace(nationId, std::move(nation));
    if (!inserted) {
        throw std::runtime_error("Duplicate nation id: " + nationId);
    }
}

void GameState::addZone(Zone zone) {
    const auto zoneId = zone.id;
    auto [it, inserted] = zones_.emplace(zoneId, std::move(zone));
    if (!inserted) {
        throw std::runtime_error("Duplicate zone id: " + zoneId);
    }
}

void GameState::addUnit(std::unique_ptr<Unit> unit) {
    if (!unit) {
        throw std::runtime_error("Cannot add null unit");
    }
    if (!hasZone(unit->zoneId())) {
        throw std::runtime_error("Unknown unit zone: " + unit->zoneId());
    }
    units_.push_back(std::move(unit));
}

bool GameState::hasNation(std::string_view nationId) const {
    return nations_.find(std::string(nationId)) != nations_.end();
}

bool GameState::hasZone(std::string_view zoneId) const {
    return zones_.find(std::string(zoneId)) != zones_.end();
}

Nation& GameState::nation(std::string_view nationId) {
    auto it = nations_.find(std::string(nationId));
    if (it == nations_.end()) {
        throw std::runtime_error("Unknown nation id: " + std::string(nationId));
    }
    return it->second;
}

const Nation& GameState::nation(std::string_view nationId) const {
    auto it = nations_.find(std::string(nationId));
    if (it == nations_.end()) {
        throw std::runtime_error("Unknown nation id: " + std::string(nationId));
    }
    return it->second;
}

const Zone& GameState::zone(std::string_view zoneId) const {
    auto it = zones_.find(std::string(zoneId));
    if (it == zones_.end()) {
        throw std::runtime_error("Unknown zone id: " + std::string(zoneId));
    }
    return it->second;
}

Unit& GameState::unitAt(std::size_t unitIndex) {
    if (unitIndex >= units_.size()) {
        throw std::runtime_error("Unit index out of range");
    }
    return *units_.at(unitIndex);
}

const Unit& GameState::unitAt(std::size_t unitIndex) const {
    if (unitIndex >= units_.size()) {
        throw std::runtime_error("Unit index out of range");
    }
    return *units_.at(unitIndex);
}

void GameState::setTurnOrder(std::vector<std::string> turnOrder) {
    if (turnOrder.empty()) {
        throw std::runtime_error("Turn order cannot be empty");
    }
    completedTurns_.clear();
    for (const auto& nationId : turnOrder) {
        if (!hasNation(nationId)) {
            throw std::runtime_error("Turn order references unknown nation: " + nationId);
        }
        completedTurns_.emplace(nationId, 0);
    }
    turnOrder_ = std::move(turnOrder);
    currentNationIndex_ = 0;
    terminal_ = false;
}

void GameState::setPhaseOrder(std::vector<Phase> phases) {
    if (phases.empty()) {
        throw std::runtime_error("Phase order cannot be empty");
    }
    phaseOrder_ = std::move(phases);
    currentPhaseIndex_ = 0;
}

void GameState::setTurnLimitPerNation(int turnLimitPerNation) {
    if (turnLimitPerNation <= 0) {
        throw std::runtime_error("Turn limit per nation must be positive");
    }
    turnLimitPerNation_ = turnLimitPerNation;
}

void GameState::declareWar(std::string_view aggressorNationId, std::string_view defenderNationId) {
    if (aggressorNationId == defenderNationId) {
        throw std::runtime_error("A nation cannot declare war on itself");
    }
    auto& aggressor = nation(aggressorNationId);
    auto& defender = nation(defenderNationId);
    aggressor.declareWarOn(defender.id());
    defender.declareWarOn(aggressor.id());
}

bool GameState::areAtWar(std::string_view nationA, std::string_view nationB) const {
    if (nationA == nationB) {
        return false;
    }
    return nation(nationA).isAtWarWith(nationB) || nation(nationB).isAtWarWith(nationA);
}

bool GameState::isWarlordFaction(std::string_view factionId) const {
    for (const auto candidate : kWarlordFactions) {
        if (candidate == factionId) {
            return true;
        }
    }
    return false;
}

int GameState::activateAllWarlordsForKmt() {
    int addedIncome = 0;
    for (const auto warlordFaction : kWarlordFactions) {
        for (auto& [zoneId, zone] : zones_) {
            if (zone.controller == warlordFaction) {
                addedIncome += zone.incomeValue;
                setZoneController(zoneId, "KMT");
            }
        }

        for (auto& unit : units_) {
            if (unit->ownerId() == warlordFaction) {
                unit->setOwnerId("KMT");
            }
        }
    }
    return addedIncome;
}

void GameState::moveUnit(std::size_t unitIndex, std::string zoneId, int movementCost) {
    if (!hasZone(zoneId)) {
        throw std::runtime_error("Unknown destination zone: " + zoneId);
    }
    auto& unit = unitAt(unitIndex);
    unit.spendMovement(movementCost);
    unit.setZoneId(std::move(zoneId));
}

void GameState::moveUnit(Unit* unit, std::string zoneId, int movementCost) {
    if (unit == nullptr) {
        throw std::runtime_error("Cannot move a null unit");
    }
    if (!hasZone(zoneId)) {
        throw std::runtime_error("Unknown destination zone: " + zoneId);
    }
    unit->spendMovement(movementCost);
    unit->setZoneId(std::move(zoneId));
}

void GameState::setZoneController(std::string_view zoneId, std::string controller) {
    auto it = zones_.find(std::string(zoneId));
    if (it == zones_.end()) {
        throw std::runtime_error("Unknown zone id: " + std::string(zoneId));
    }

    auto& zone = it->second;
    if (zone.controller == controller) {
        return;
    }
    if (hasNation(zone.controller)) {
        auto& oldNation = nation(zone.controller);
        oldNation.setIncome(oldNation.income() - zone.incomeValue);
    }
    if (hasNation(controller)) {
        auto& newNation = nation(controller);
        newNation.setIncome(newNation.income() + zone.incomeValue);
    }
    zone.controller = std::move(controller);
}

std::vector<Unit*> GameState::unitsInZone(std::string_view zoneId) {
    std::vector<Unit*> result;
    for (auto& unit : units_) {
        if (unit->zoneId() == zoneId) {
            result.push_back(unit.get());
        }
    }
    return result;
}

std::vector<const Unit*> GameState::unitsInZone(std::string_view zoneId) const {
    std::vector<const Unit*> result;
    for (const auto& unit : units_) {
        if (unit->zoneId() == zoneId) {
            result.push_back(unit.get());
        }
    }
    return result;
}

void GameState::removeUnits(const std::vector<const Unit*>& destroyedUnits) {
    std::unordered_set<const Unit*> destroyedSet(destroyedUnits.begin(), destroyedUnits.end());
    units_.erase(
        std::remove_if(
            units_.begin(),
            units_.end(),
            [&](const std::unique_ptr<Unit>& unit) {
                return destroyedSet.find(unit.get()) != destroyedSet.end();
            }),
        units_.end());
}

void GameState::resetMovementForNation(std::string_view nationId) {
    for (auto& unit : units_) {
        if (unit->ownerId() == nationId) {
            unit->resetMovement();
        }
    }
}

int GameState::factoryOutputForZone(std::string_view zoneId) const {
    const auto& targetZone = zone(zoneId);
    int output = 0;
    for (const auto& facilityId : targetZone.facilities) {
        output += facilityOutput(facilityId);
    }
    return output;
}

int GameState::totalFactoryOutputForNation(std::string_view nationId) const {
    int totalOutput = 0;
    for (const auto& [zoneId, zoneValue] : zones_) {
        if (zoneValue.controller == nationId) {
            totalOutput += factoryOutputForZone(zoneId);
        }
    }
    return totalOutput;
}

int GameState::placedUnitsThisPhaseInZone(std::string_view zoneId) const {
    const auto it = placedUnitsThisPhaseByZone_.find(std::string(zoneId));
    return it != placedUnitsThisPhaseByZone_.end() ? it->second : 0;
}

int GameState::remainingPlacementCapacityForZone(std::string_view nationId, std::string_view zoneId) const {
    const auto& targetZone = zone(zoneId);
    if (targetZone.controller != nationId) {
        return 0;
    }
    return std::max(0, factoryOutputForZone(zoneId) - placedUnitsThisPhaseInZone(zoneId));
}

int GameState::pendingPurchaseCountFor(std::string_view nationId) const {
    const auto it = pendingPurchasesByNation_.find(std::string(nationId));
    if (it == pendingPurchasesByNation_.end()) {
        return 0;
    }
    int total = 0;
    for (const auto& [unitKind, count] : it->second) {
        total += count;
    }
    return total;
}

int GameState::pendingPurchaseCountFor(std::string_view nationId, UnitKind unitKind) const {
    const auto it = pendingPurchasesByNation_.find(std::string(nationId));
    if (it == pendingPurchasesByNation_.end()) {
        return 0;
    }
    const auto kindIt = it->second.find(unitKind);
    return kindIt != it->second.end() ? kindIt->second : 0;
}

void GameState::addPendingPurchases(std::string_view nationId, UnitKind unitKind, int count) {
    if (count <= 0) {
        throw std::runtime_error("Pending purchase count must be positive");
    }
    pendingPurchasesByNation_[std::string(nationId)][unitKind] += count;
}

void GameState::removePendingPurchases(std::string_view nationId, UnitKind unitKind, int count) {
    if (count <= 0) {
        throw std::runtime_error("Pending purchase removal count must be positive");
    }
    auto nationIt = pendingPurchasesByNation_.find(std::string(nationId));
    if (nationIt == pendingPurchasesByNation_.end()) {
        throw std::runtime_error("No pending purchases recorded for nation");
    }
    auto kindIt = nationIt->second.find(unitKind);
    if (kindIt == nationIt->second.end() || kindIt->second < count) {
        throw std::runtime_error("Tried to remove more pending purchases than are available");
    }
    kindIt->second -= count;
    if (kindIt->second == 0) {
        nationIt->second.erase(kindIt);
    }
    if (nationIt->second.empty()) {
        pendingPurchasesByNation_.erase(nationIt);
    }
}

void GameState::placePurchasedUnits(std::string_view nationId, std::string_view zoneId, UnitKind unitKind, int count) {
    if (count <= 0) {
        throw std::runtime_error("Placed unit count must be positive");
    }
    if (remainingPlacementCapacityForZone(nationId, zoneId) < count) {
        throw std::runtime_error("Not enough placement capacity in target zone");
    }
    if (pendingPurchaseCountFor(nationId, unitKind) < count) {
        throw std::runtime_error("Not enough pending purchased units of requested type");
    }

    removePendingPurchases(nationId, unitKind, count);
    placedUnitsThisPhaseByZone_[std::string(zoneId)] += count;
    for (int index = 0; index < count; ++index) {
        addUnit(makeUnit(unitKind, std::string(nationId), std::string(zoneId)));
    }
}

void GameState::recordEnemyUnitValueDestroyedByNation(
    std::string_view nationId,
    const std::vector<const Unit*>& destroyedUnits) {
    int addedValue = 0;
    for (const auto* unit : destroyedUnits) {
        if (unit == nullptr || unit->ownerId() == nationId) {
            continue;
        }
        addedValue += rewardValue(unit->kind());
    }
    enemyUnitValueDestroyedByNation_[std::string(nationId)] += addedValue;
}

void GameState::forceCurrentTurnState(std::string_view nationId, Phase phase) {
    const auto nationIt = std::find(turnOrder_.begin(), turnOrder_.end(), nationId);
    if (nationIt == turnOrder_.end()) {
        throw std::runtime_error("Unknown nation id in forceCurrentTurnState: " + std::string(nationId));
    }
    const auto phaseIt = std::find(phaseOrder_.begin(), phaseOrder_.end(), phase);
    if (phaseIt == phaseOrder_.end()) {
        throw std::runtime_error("Unknown phase in forceCurrentTurnState");
    }

    currentNationIndex_ = static_cast<std::size_t>(std::distance(turnOrder_.begin(), nationIt));
    currentPhaseIndex_ = static_cast<std::size_t>(std::distance(phaseOrder_.begin(), phaseIt));
    terminal_ = false;
    placedUnitsThisPhaseByZone_.clear();
}

std::string_view GameState::currentNation() const {
    if (turnOrder_.empty()) {
        throw std::runtime_error("Turn order has not been initialized");
    }
    return turnOrder_.at(currentNationIndex_);
}

Phase GameState::currentPhase() const {
    if (phaseOrder_.empty()) {
        throw std::runtime_error("Phase order has not been initialized");
    }
    return phaseOrder_.at(currentPhaseIndex_);
}

int GameState::completedTurnsFor(std::string_view nationId) const {
    auto it = completedTurns_.find(std::string(nationId));
    if (it == completedTurns_.end()) {
        throw std::runtime_error("Unknown nation id in completedTurnsFor: " + std::string(nationId));
    }
    return it->second;
}

int GameState::unitCountFor(std::string_view nationId) const {
    int count = 0;
    for (const auto& unit : units_) {
        if (unit->ownerId() == nationId) {
            ++count;
        }
    }
    return count;
}

int GameState::unitValueFor(std::string_view nationId) const {
    int totalValue = 0;
    for (const auto& unit : units_) {
        if (unit->ownerId() == nationId) {
            totalValue += rewardValue(unit->kind());
        }
    }
    return totalValue;
}

int GameState::enemyUnitValueDestroyedByNation(std::string_view nationId) const {
    const auto it = enemyUnitValueDestroyedByNation_.find(std::string(nationId));
    return it != enemyUnitValueDestroyedByNation_.end() ? it->second : 0;
}

void GameState::advancePhase() {
    if (turnOrder_.empty() || phaseOrder_.empty()) {
        throw std::runtime_error("Turn structure has not been initialized");
    }
    if (terminal_) {
        throw std::runtime_error("Cannot advance a terminal game state");
    }

    const auto previousPhase = currentPhase();
    ++currentPhaseIndex_;
    if (currentPhaseIndex_ < phaseOrder_.size()) {
        if (currentPhase() == Phase::PlaceUnits || previousPhase == Phase::PlaceUnits) {
            placedUnitsThisPhaseByZone_.clear();
        }
        return;
    }

    const auto finishedNation = turnOrder_.at(currentNationIndex_);
    ++completedTurns_.at(finishedNation);
    currentPhaseIndex_ = 0;

    bool everyoneFinished = true;
    for (const auto& nationId : turnOrder_) {
        if (completedTurns_.at(nationId) < turnLimitPerNation_) {
            everyoneFinished = false;
            break;
        }
    }
    if (everyoneFinished) {
        terminal_ = true;
        return;
    }

    currentNationIndex_ = (currentNationIndex_ + 1) % turnOrder_.size();
    resetMovementForNation(turnOrder_.at(currentNationIndex_));
    placedUnitsThisPhaseByZone_.clear();
}

}  // namespace game
