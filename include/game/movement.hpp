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
  Id from;
  Id to;
  std::set<Id> nodeTerrain;
  std::set<Id> borderTerrain;
  bool river{false};
  bool riverKnown{true};
};
struct RouteRequest {
  Id unit;
  std::vector<Id> path; // Includes the current zone and destination.
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
  std::vector<Id> zones;
  std::vector<Id> facilities;
};

bool unitClass(const State &, const UnitState &, const Id &classification);
// Shared directed political permissions. Control and alignment are distinct.
bool areAtWar(const State &, const Id &actor, const Id &target);
bool logisticsFriendly(const State &, const Id &actor, const Id &owner);
bool strategicRailPermission(const State &, const Id &actor, const Id &owner);
bool movementController(const State &, const Id &nation);
bool landAccess(const State &, const Id &nation, const Id &zone,
                bool combat = false);
bool aircraftFlightAccess(const State &, const Id &nation, const Id &zone,
                          bool combat);
bool heldSinceTurnStart(const State &, const Id &nation, const Id &zone,
                        bool allowFriendly = true);
// Defensive scrambling refers to the defender's last own turn, rather than the
// active attacker's turn snapshot used by supply and current-turn movement.
bool heldSinceNationTurnStart(const State &, const Id &nation, const Id &zone,
                              bool allowFriendly = true);
BorderApproach borderApproach(const State &, const Id &from, const Id &to);
bool railUndamaged(const State &, const Id &from, const Id &to,
                   bool sinceTurnStart = false);
// Exact native gauge predicate, also used to prepare immutable device metadata.
bool railGaugeChange(const State &, const Id &from, const Id &to);
bool riverRouteAvailable(const State &, const Id &nation, const Id &from,
                         const Id &to);
Id railRegion(const State &, const Id &zone);
int regionalRailCapacity(const Id &region);
RouteResult validateRoute(const State &, const RouteRequest &);
RouteResult validateFactoryRailRoute(const State &, const Id &facility,
                                     const std::vector<Id> &path);
bool blitzPairValid(const State &, const UnitState &, const Id &from,
                    const Id &to);

std::vector<Id> navalFacilitySeaZones(const State &, const Id &facility);
bool seaBlockaded(const State &, const Id &nation, const Id &sea);
bool facilityBlockaded(const State &, const Id &nation, const Id &facility);
bool navalFacilityUsable(const State &, const Id &nation, const Id &facility,
                         bool requireHeld = true);
SupplyRoute supplyRoute(const State &, const Id &nation, const Id &zone);
SupplyRoute lendLeaseSupplyRoute(const State &, const Id &sender,
                                 const Id &recipient, const Id &zone,
                                 bool navalUnit = false);
bool inSupply(const State &, const Id &nation, const Id &zone);
bool burmaRoadOpen(const State &, bool ledo = false);
bool ccpSovietRailConnected(const State &, const Id &zone);
std::set<Id> withdrawalEligibleRecipients(const State &, const Id &attacker,
                                          const Id &zone);

// Shared cargo bookkeeping; transport-specific loading/range rules stay in the
// air/naval modules. Removing a carrier and its linked cargo is handled by the
// shared political-unit removal function.
void attachCargo(State &, const Id &transport, const Id &cargo);
void detachCargo(State &, const Id &transport, const Id &cargo,
                 const Id &destination);

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

private:
  std::shared_ptr<const Rules> gameplay_;
};
} // namespace game::campaign
