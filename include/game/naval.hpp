#pragma once

#include "game/campaign.hpp"
#include "game/movement.hpp"

namespace game::campaign {

struct NavalRouteRequest {
    std::vector<Id> units;
    std::vector<Id> path;
    bool combat{false};
    bool strategic{false};
    std::optional<Id> originFacility;
    std::optional<Id> destinationFacility;
};

RouteResult validateNavalRoute(const State &, const NavalRouteRequest &);
// Militia start and end every move in their Home Country (RB): whether this
// unit may start or end one in this zone on that account. Other units may.
bool militiaAllowedIn(const State &, const UnitState &unit, const Id &zone);
// Whether these ships can still put every militia aboard ashore in its Home
// Country, from these land zones, in this Noncombat Movement.
bool militiaCanLandFrom(const State &, const std::vector<Id> &ships, const std::vector<Id> &zones);
// Whether this patrol plane let all these ships pass this turn, when they
// entered its sea zone or by staying out of a battle with them (user rulings
// RCL-017 and RCL-020). It then stays out of combat with them for the rest of
// the turn, and it does not stop their amphibious assaults.
bool patrolLetPass(const State &, const UnitState &plane, const std::vector<Id> &ships);
// Sea zones where a ship can still end this phase's movement, its own zone
// included, by a route that meets no unfriendly unit before its last zone, so
// that no encounter, screen or peace entry can stop it short.
std::set<Id> navalEndZones(const State &, const Id &ship);
int strategicNavalCapacity(const State &, const Id &nation);
int navalCompletedTurns(const State &, const Id &nation);
bool navalCargoFits(const State &, const Id &transport, const std::vector<Id> &cargo);
bool navalLoadAllowed(const State &, const Id &transport, const Id &cargo);
std::vector<Action> navalMovementActions(const State &);
// Training order construction is forward-only. The ordinary rules retain the
// editable human picker; these helpers preserve each executable fleet/route
// while removing drafts that have no legal completion.
std::vector<Action> forwardNavalOrderActions(const State &, std::vector<Action>);
void forwardNavalOrderDecision(State &);
bool applyNavalMovementAction(State &, const Action &);
bool applyNavalMovementChance(State &, const ChanceRequest &, const ChanceOutcome &);
bool navalMovementPhaseComplete(const State &);
void beginNavalMovementTurn(State &);
void finishNavalMovementPhase(State &);
// Called with a naval_complete battle still present. Reads its result and the
// serialized route continuation; removes it before resuming any remaining route.
void continueNavalMovement(State &, const Id &completedBattle);

// A designated raider attacks alone (RB 9.4.4). True when these attackers mix one
// with other units, or would merge with a declared battle where either side has one.
bool raiderWouldCombine(const State &, const Id &zone, const Id &attacker,
                        const std::vector<Id> &attackers, const Id &context);

// Options are serialized in BattleState.data. Contexts distinguish ordinary
// combat from movement reactions, screening, raiders and port attacks.
Id registerNavalBattle(State &, const Id &zone, const Id &attacker,
                       const std::vector<Id> &attackers, const std::map<Id, Id> &origins,
                       const json::Value &options = json::Value(json::Value::Object{}));
void beginNavalBattle(State &, const Id &);
std::vector<Action> navalCombatActions(const State &);
bool applyNavalCombatAction(State &, const Action &);
bool applyNavalCombatChance(State &, const ChanceRequest &, const ChanceOutcome &);
bool navalCombatPhaseComplete(const State &);

std::vector<Action> navalOperationActions(const State &);
bool applyNavalOperationAction(State &, const Action &);
bool applyNavalOperationChance(State &, const ChanceRequest &, const ChanceOutcome &);
bool navalOperationPhaseComplete(const State &);
void finishNavalOperationPhase(State &);
// RCL-018: a declared amphibious assault that cannot go ahead in the Combat
// Phase, because Enemy surface ships or aircraft hold its sea zone or no cargo
// is still aboard a transport there. Neither the phase's end nor a land battle
// in the same zone waits for it; beginning a land battle or ending the phase
// calls it off with its cargo left aboard.
bool assaultCalledOff(const State &, const BattleState &);
void callOffUnclearedAssaults(State &);
void preparePortLandDefence(State &, const Id &battle);
void resolveCapturedPorts(State &, const Id &landZone, const Id &captor);
void queueDamagedPortEvacuation(State &, const Id &facility);
void resumeDamagedPortEvacuation(State &, const Id &facility, int moved);
void releaseAmphibiousReserves(State &, const Id &battle);

class NavalRules final : public Rules {
  public:
    explicit NavalRules(std::shared_ptr<const Rules> gameplay = nullptr);
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
