#pragma once
#include "game/campaign.hpp"
namespace game::campaign {
struct FlightResult {
    bool allowed{false};
    std::string reason;
    int cost{0};
};
bool isAircraft(const State &, const UnitState &);
FlightResult validateFlight(const State &, const Id &unit, const std::vector<Id> &path, bool combat,
                            bool attackDestination = false);
std::vector<Id> airLandingSpots(const State &, const Id &unit);
bool airLandingAvailable(const State &, const Id &unit, const Id &destination);
// Empty aircraft list checks every airborne attacker and aircraft on MAP.
// Carrier seats occupied by grounded cargo or reserved for scramble returns
// cannot also support another aircraft's proposed return.
bool airLandingPlanAvailable(const State &, const std::vector<Id> &aircraft = {});
// The joint plan that every move must keep (RB 9.3): carriers the mover can
// still sail may end in any sea zone they can reach, a carrier that sails
// launches its own aircraft first, and carried aircraft that can still fly
// ashore free their seats.
bool airLandingPlanReachable(const State &);
// How many of the moving side's airborne aircraft no such plan lands. Moves
// never raise it, so it is zero unless dice or another nation's turn left
// aircraft without a landing; those must not block moves that strand no one.
int airLandingShortfall(const State &);
// Whether a plan lands all of them but at most `shortfall`.
bool airLandingPlanReachableWithin(const State &, int shortfall);
// Whether `after`, a probe of a move from `before`, leaves no more aircraft
// without a landing; it solves `before` only when `after` lacks a complete plan.
bool airLandingsKept(const State &before, const State &after);
// Whether `unit` flying `path` keeps itself a landing and leaves no more
// aircraft without one, without changing or copying the state.
bool airFlightKeepsLandings(const State &, const Id &unit, const std::vector<Id> &path);
// Whether the moving side has aircraft in flight or on patrol, whose landings
// its moves must keep; without them no move can strand one.
bool movingSideAirborne(const State &);
// The fewest airborne aircraft whose loss lets the rest land as the carriers
// stand; where there is a choice, earlier aircraft in unit order keep theirs.
std::vector<Id> strandedAircraft(const State &);
// Removes them, counting them in the state flag "stranded_aircraft_lost",
// when Combat Movement ends with nothing else legal. Normally their owner gives
// up the aircraft that must be lost first, choosing which.
void eliminateStrandedAircraft(State &);
void enforcePatrolLandingAvailability(State &);
void beginAirDefence(State &, const Id &battle);
void prepareLandAirborneDrop(State &, const Id &battle);
void finishAirCombat(State &, const Id &battle);
// RB10.2: carpet bombers return immediately after round one while the rest of
// the land battle pauses. The pending return choices live in BattleState.data.
void returnCarpetBombers(State &, const Id &battle, const std::vector<Id> &bombers);
void applyFacilityBombDamage(State &, const Id &facility, int damage);
void applyCityBombDamage(State &, const Id &zone, int damage);
void applyRailBombDamage(State &, const Id &zone, const Id &borderNeighbor, int damage);
class AirRules final : public Rules {
  public:
    explicit AirRules(std::shared_ptr<const Rules> gameplay = nullptr);
    Id id() const override;
    std::vector<Action> actions(const State &) const override;
    std::vector<Action> interrupts(const State &) const override;
    bool phaseComplete(const State &) const override;
    void apply(State &, const Action &) const override;
    void applyChance(State &, const ChanceRequest &, const ChanceOutcome &) const override;
    void finishTurn(State &) const override;
    void beginTurn(State &) const override;
    void finishPhase(State &) const override;

  private:
    std::shared_ptr<const Rules> gameplay_;
};
} // namespace game::campaign
