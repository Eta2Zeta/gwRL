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
// ashore free their seats. Combat Movement ends only once the plan above holds.
bool airLandingPlanReachable(const State &);
// The same after `unit` flies `path`, without changing or copying the state.
bool airLandingPlanReachableAfterFlight(const State &, const Id &unit, const std::vector<Id> &path);
// Airborne aircraft, in unit order, that no joint landing assignment can
// include once the earlier ones keep theirs.
std::vector<Id> strandedAircraft(const State &);
// Removes them and counts them in the state flag "stranded_aircraft_lost", an
// alarm: moves keep a reachable plan, so legal play should never strand one.
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
