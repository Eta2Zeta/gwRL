#include "game/game_state.hpp"

#include <array>
#include <algorithm>
#include <stdexcept>
#include <unordered_set>

namespace game {

namespace {

constexpr std::array<std::string_view, 6> kWarlordFactions{
    "ZhiliClique",
    "SzechwanClique",
    "SinkiangClique",
    "YunnanClique",
    "GuangxiClique",
    "MaClique",
};

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

int GameState::activateWarlordForKmt(std::string_view warlordFactionId) {
    if (!isWarlordFaction(warlordFactionId)) {
        return 0;
    }

    int addedIncome = 0;
    for (auto& [zoneId, zone] : zones_) {
        if (zone.controller == warlordFactionId) {
            addedIncome += zone.incomeValue;
            setZoneController(zoneId, "KMT");
        }
    }

    for (auto& unit : units_) {
        if (unit->ownerId() == warlordFactionId) {
            unit->setOwnerId("KMT");
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

void GameState::advancePhase() {
    if (turnOrder_.empty() || phaseOrder_.empty()) {
        throw std::runtime_error("Turn structure has not been initialized");
    }
    if (terminal_) {
        throw std::runtime_error("Cannot advance a terminal game state");
    }

    ++currentPhaseIndex_;
    if (currentPhaseIndex_ < phaseOrder_.size()) {
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
}

}  // namespace game
