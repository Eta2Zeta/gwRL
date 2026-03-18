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

    void setTurnOrder(std::vector<std::string> turnOrder);
    void setPhaseOrder(std::vector<Phase> phases);

    std::string_view currentNation() const;
    Phase currentPhase() const;
    void advancePhase();

    const std::unordered_map<std::string, Nation>& nations() const { return nations_; }
    const std::unordered_map<std::string, Zone>& zones() const { return zones_; }
    const std::vector<std::unique_ptr<Unit>>& units() const { return units_; }
    const std::vector<std::string>& turnOrder() const { return turnOrder_; }
    const std::vector<Phase>& phaseOrder() const { return phaseOrder_; }

  private:
    std::unordered_map<std::string, Nation> nations_;
    std::unordered_map<std::string, Zone> zones_;
    std::vector<std::unique_ptr<Unit>> units_;
    std::vector<std::string> turnOrder_;
    std::vector<Phase> phaseOrder_;
    std::size_t currentNationIndex_ {0};
    std::size_t currentPhaseIndex_ {0};
};

}  // namespace game
