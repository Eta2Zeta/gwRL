#pragma once

#include "game/nation.hpp"
#include "game/types.hpp"
#include "game/unit.hpp"

#include <memory>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace game {

class GameState {
  public:
    void addNation(Nation nation);
    void addZone(Zone zone);
    void addUnit(std::unique_ptr<Unit> unit);

    bool hasNation(std::string_view nationId) const;
    bool hasZone(std::string_view zoneId) const;

    Nation& nation(std::string_view nationId);
    const Nation& nation(std::string_view nationId) const;
    const Zone& zone(std::string_view zoneId) const;
    Unit& unitAt(std::size_t unitIndex);
    const Unit& unitAt(std::size_t unitIndex) const;

    void setTurnOrder(std::vector<std::string> turnOrder);
    void setPhaseOrder(std::vector<Phase> phases);
    void setTurnLimitPerNation(int turnLimitPerNation);
    void declareWar(std::string_view aggressorNationId, std::string_view defenderNationId);
    bool areAtWar(std::string_view nationA, std::string_view nationB) const;
    bool isWarlordFaction(std::string_view factionId) const;
    int activateAllWarlordsForKmt();
    void moveUnit(std::size_t unitIndex, std::string zoneId, int movementCost);
    void moveUnit(Unit* unit, std::string zoneId, int movementCost);
    void setZoneController(std::string_view zoneId, std::string controller);
    std::vector<Unit*> unitsInZone(std::string_view zoneId);
    std::vector<const Unit*> unitsInZone(std::string_view zoneId) const;
    void removeUnits(const std::vector<const Unit*>& destroyedUnits);
    void resetMovementForNation(std::string_view nationId);

    std::string_view currentNation() const;
    Phase currentPhase() const;
    void advancePhase();
    bool isTerminal() const { return terminal_; }
    int turnLimitPerNation() const { return turnLimitPerNation_; }
    int completedTurnsFor(std::string_view nationId) const;
    int unitCountFor(std::string_view nationId) const;

    const std::unordered_map<std::string, Nation>& nations() const { return nations_; }
    const std::unordered_map<std::string, Zone>& zones() const { return zones_; }
    const std::vector<std::unique_ptr<Unit>>& units() const { return units_; }
    const std::vector<std::string>& turnOrder() const { return turnOrder_; }
    const std::vector<Phase>& phaseOrder() const { return phaseOrder_; }
    const std::unordered_map<std::string, int>& completedTurns() const { return completedTurns_; }

  private:
    std::unordered_map<std::string, Nation> nations_;
    std::unordered_map<std::string, Zone> zones_;
    std::vector<std::unique_ptr<Unit>> units_;
    std::vector<std::string> turnOrder_;
    std::vector<Phase> phaseOrder_;
    std::unordered_map<std::string, int> completedTurns_;
    std::size_t currentNationIndex_ {0};
    std::size_t currentPhaseIndex_ {0};
    int turnLimitPerNation_ {2};
    bool terminal_ {false};
};

}  // namespace game
