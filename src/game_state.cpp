#include "game/game_state.hpp"

#include <stdexcept>

namespace game {

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
    if (!hasNation(unit->ownerId())) {
        throw std::runtime_error("Unknown unit owner: " + unit->ownerId());
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

void GameState::setTurnOrder(std::vector<std::string> turnOrder) {
    if (turnOrder.empty()) {
        throw std::runtime_error("Turn order cannot be empty");
    }
    for (const auto& nationId : turnOrder) {
        if (!hasNation(nationId)) {
            throw std::runtime_error("Turn order references unknown nation: " + nationId);
        }
    }
    turnOrder_ = std::move(turnOrder);
    currentNationIndex_ = 0;
}

void GameState::setPhaseOrder(std::vector<Phase> phases) {
    if (phases.empty()) {
        throw std::runtime_error("Phase order cannot be empty");
    }
    phaseOrder_ = std::move(phases);
    currentPhaseIndex_ = 0;
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

void GameState::advancePhase() {
    if (turnOrder_.empty() || phaseOrder_.empty()) {
        throw std::runtime_error("Turn structure has not been initialized");
    }

    ++currentPhaseIndex_;
    if (currentPhaseIndex_ < phaseOrder_.size()) {
        return;
    }

    currentPhaseIndex_ = 0;
    currentNationIndex_ = (currentNationIndex_ + 1) % turnOrder_.size();
}

}  // namespace game
