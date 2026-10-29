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
