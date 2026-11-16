#pragma once

#include "game/campaign.hpp"

namespace game::campaign {

enum class MovementMode {
  Ordinary,
  Blitz,
  StrategicRail,
  StrategicRiver,
  NarrowCrossing
};
std::string toString(MovementMode);
MovementMode parseMovementMode(const std::string &);

// Terrain is directional. Node terrain lasts throughout combat; border terrain
// and the river-crossing flag belong to this individual contingent's approach.
struct BorderApproach {
  ZoneId from;
  ZoneId to;
  std::set<Id> nodeTerrain;
  std::set<Id> borderTerrain;
  bool river{false};
  bool riverKnown{true};
};
struct RouteRequest {
  Id unit;
  std::vector<ZoneId> path; // Includes the current zone and destination.
  MovementMode mode{MovementMode::Ordinary};
  bool combat{false};
  std::optional<Id> towed; // Paired Motorized Infantry towing, never cargo.
};
struct RouteResult {
  bool allowed{false};
  std::string reason;
  int cost{0};
  bool exhaustsMovement{false};
  std::set<Id> regions;
  BorderApproach approach;
};
struct SupplyRoute {
  bool connected{false};
  std::vector<ZoneId> zones;
  std::vector<Id> facilities;
};

bool unitClass(const State &, const UnitState &, UnitClassId classification);
bool movementController(const State &, NationId nation);
bool landAccess(const State &, NationId nation, ZoneId zone,
                bool combat = false);
bool aircraftFlightAccess(const State &, NationId nation, ZoneId zone,
                          bool combat);
bool heldSinceTurnStart(const State &, NationId nation, ZoneId zone,
                        bool allowFriendly = true);
// Land a unit may enter this turn outside combat: held since the turn began,
// or handed over this turn by a minor's alignment (RB 4.6). RB 11.1 bars only
// land captured this Player Turn. Strategic rail, supply and production still
// require land held since the turn began.
bool enterableThisTurn(const State &, NationId nation, ZoneId zone,
                       bool allowFriendly = true);
// Defensive scrambling refers to the defender's last own turn, rather than the
// active attacker's turn snapshot used by supply and current-turn movement.
bool heldSinceNationTurnStart(const State &, NationId nation, ZoneId zone,
                              bool allowFriendly = true);
BorderApproach borderApproach(const State &, ZoneId from, ZoneId to);
bool railUndamaged(const State &, ZoneId from, ZoneId to,
                   bool sinceTurnStart = false);
bool riverRouteAvailable(const State &, NationId nation, ZoneId from,
                         ZoneId to);
Id railRegion(const State &, ZoneId zone);
int regionalRailCapacity(const Id &region);
RouteResult validateRoute(const State &, const RouteRequest &);
RouteResult validateFactoryRailRoute(const State &, const Id &facility,
                                     const std::vector<ZoneId> &path);
bool blitzPairValid(const State &, const UnitState &, ZoneId from,
                    ZoneId to);

std::vector<ZoneId> navalFacilitySeaZones(const State &, const Id &facility);
bool seaBlockaded(const State &, NationId nation, ZoneId sea);
bool facilityBlockaded(const State &, NationId nation, const Id &facility);
bool navalFacilityUsable(const State &, NationId nation, const Id &facility,
                         bool requireHeld = true);
SupplyRoute supplyRoute(const State &, NationId nation, ZoneId zone);
SupplyRoute lendLeaseSupplyRoute(const State &, NationId sender,
                                 NationId recipient, ZoneId zone,
                                 bool navalUnit = false);
bool inSupply(const State &, NationId nation, ZoneId zone);
bool burmaRoadOpen(const State &, bool ledo = false);
bool ccpSovietRailConnected(const State &, ZoneId zone);
NumberSet<NationId> withdrawalEligibleRecipients(const State &, NationId attacker,
                                          ZoneId zone);

// Shared cargo bookkeeping; transport-specific loading/range rules stay in the
// air/naval modules. Removing a carrier and its linked cargo is handled by the
// shared political-unit removal function.
void attachCargo(State &, const Id &transport, const Id &cargo);
void detachCargo(State &, const Id &transport, const Id &cargo,
                 ZoneId destination);

class MovementRules final : public Rules {
public:
  explicit MovementRules(std::shared_ptr<const Rules> gameplay = nullptr);
  Id id() const override;
  std::vector<Action> actions(const State &) const override;
  std::vector<Action> interrupts(const State &) const override;
  bool phaseComplete(const State &) const override;
  void apply(State &, const Action &) const override;
  void applyChance(State &, const ChanceRequest &,
                   const ChanceOutcome &) const override;
  void finishTurn(State &) const override;
  void beginTurn(State &) const override;
  void finishPhase(State &) const override;
  void settle(State &) const override;

private:
  std::shared_ptr<const Rules> gameplay_;
};
} // namespace game::campaign
