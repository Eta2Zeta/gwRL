#pragma once

#include "game/campaign.hpp"

namespace game::campaign {

// Rule events called by later movement/combat/economy modules. These functions
// never stand in for resolving a battle or proving a movement/supply path.
enum class PossessionCause { Capture, Liberation, Alignment, Influence, Transfer };
enum class DeclarationMode { MajorPowerDeclaration, LandAttack };

struct PoliticalPermission {
    bool allowed {false};
    std::string reason;
};

bool isWarlord(const Id& nation);
Id originalNation(const State&, const Id& zone);
std::vector<Id> possessedLand(const State&, const Id& nation);
std::vector<Id> originalLand(const State&, const Id& nation);
bool passableLandBorder(const State&, const Id& from, const Id& to);
bool controlledBy(const State&, const Id& minor, const Id& controller);
bool atWarWithMajor(const State&, const Id& nation);
bool politicallyFriendly(const State&, const Id& first, const Id& second);
bool chineseHomeCountry(const State&, const Id& zone);
bool decentralizedProduction(const State&, const Id& nation);
Id politicalPlayer(const State&, const Id& nation);
void addPoliticalUnit(State&, const Id& nation, const Id& type, const Id& zone, int count = 1);
// Refresh only this owner's existing units, preserving used movement exactly.
void refreshPoliticalUnitMovement(State&, const Id& owner);
void removePoliticalUnits(State&, const std::set<Id>& units);
void incorporateNation(State&, const Id& minor, const Id& recipient);
void ensureDadao(State&);
void refreshPoliticalState(State&);
void changePossession(State&, const Id& zone, const Id& recipient, PossessionCause,
                      const std::optional<Id>& conqueror = std::nullopt);
// The withdrawal set is supplied by M5's route validator, never by a policy.
void captureLand(State&, const Id& attacker, const Id& zone,
                 const std::set<Id>& withdrawalEligibleRecipients = {});
PoliticalPermission mayDeclareWar(const State&, const Id& actor, const Id& target,
                                  DeclarationMode = DeclarationMode::MajorPowerDeclaration);
void declareWar(State&, const Id& actor, const Id& target, DeclarationMode);
void recordLandAttack(State&, const Id& attacker, const Id& zone);
void surrenderNation(State&, const Id& nation, const Id& attacker);

// Shared decision/chance helpers keep continuations explicit in State, so
// checkpoints, planning keys and replay include all pending political work.
Action politicalAction(const State&, const Id& decisionNation, const Id& kind,
                       json::Value parameters = json::Value::Object {},
                       const std::optional<Id>& decisionId = std::nullopt);
void queuePoliticalDecision(State&, const Id& nation, const Id& kind,
                            std::vector<Action> options, json::Value continuation = json::Value::Object {});
void requestPoliticalRoll(State&, const Id& nation, const Id& kind, int sides,
                          json::Value parameters = json::Value::Object {}, int dice = 1);
const json::Value& pendingPolitical(const State&, const Id& continuation);
void erasePoliticalContinuation(State&, const Id& continuation);

// Warlords, invasion alignment, and Chinese Truce (politics_warlords.cpp).
std::vector<Action> warlordActions(const State&);
bool applyWarlordAction(State&, const Action&);
bool applyWarlordChance(State&, const ChanceRequest&, const ChanceOutcome&);
void beginCombatPoliticalResolution(State&);
bool continueCombatPoliticalResolution(State&);
void terminateChineseTruce(State&, const Id& breaker, bool evolution = false);

// Influence and the distinct CCP / controlled-minor recruitment rules.
std::vector<Action> influenceActions(const State&);
bool applyInfluenceAction(State&, const Action&);
bool applyInfluenceChance(State&, const ChanceRequest&, const ChanceOutcome&);

// Compose M4 politics with later gameplay modules. Without an accounting module,
// an unevaluated national income cannot silently become zero or be collected.
class PoliticsRules final : public Rules {
  public:
    explicit PoliticsRules(std::shared_ptr<const Rules> gameplay = nullptr);
    Id id() const override;
    std::vector<Action> actions(const State&) const override;
    std::vector<Action> interrupts(const State&) const override;
    bool phaseComplete(const State&) const override;
    void apply(State&, const Action&) const override;
    void applyChance(State&, const ChanceRequest&, const ChanceOutcome&) const override;
    void finishTurn(State&) const override;
    void beginTurn(State&) const override;
    void finishPhase(State&) const override;

  private:
    void applyImpl(State&, const Action&) const;
    void applyChanceImpl(State&, const ChanceRequest&, const ChanceOutcome&) const;
    std::shared_ptr<const Rules> gameplay_;
    bool refreshIncomeAfterEffects_{false};
};

} // namespace game::campaign
