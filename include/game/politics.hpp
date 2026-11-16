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

// What the rules can ever make of a nation of this campaign: which answers a
// nation can have at all. The reason for each is beside its definition in
// politics.cpp. The network's input asks only about these (zone_encoding.cpp)
// and reports a position that breaks one. A rare answer counts as possible;
// these rule out only what no game can reach.
//
// Japan is a major power from the start, and only the KMT and the CCP are
// promoted to one.
bool canEvolve(const Id& nation);
bool canBeMajorPower(const Id& nation);
bool powerStatusPossible(const Id& nation, const Id& status);
// A nation's alliance and its player bear the same name and change together,
// and only a warlord's ever change, when it is incorporated. Before that a
// warlord has neither.
bool alliancePossible(const Id& nation, const std::optional<Id>& alliance);
// The nation that controls a nation: itself for Japan, the KMT and the CCP,
// Japan or nobody for Dadao, nobody for Mongolia, and for a warlord nobody or
// the nation that incorporated it (the KMT, the CCP, Dadao or Japan).
bool controllerPossible(const Id& nation, const std::optional<Id>& controller);
// Only the KMT, which loses its last land, and Japan, which loses Tokyo, surrender.
bool canSurrender(const Id& nation);
// The invader recorded when Chinese land is attacked is not Chinese.
bool canInvadeChina(const Id& nation);
// Whether the two can ever be at war. One side of every war is Japan, the KMT,
// the CCP, Dadao or Mongolia, and Japan and Dadao share an alliance for good.
bool warPossible(const Id& first, const Id& second);
// Whether the two can ever be allies: only the KMT and the CCP, under their truce.
bool alliesPossible(const Id& first, const Id& second);
// Whether `attacker` can be recorded as having attacked this warlord. A warlord
// attacks nobody, and one the KMT attacks joins the CCP at once instead.
bool warlordAttackPossible(const Id& warlord, const Id& attacker);

NationId originalNation(const State&, ZoneId zone);
std::vector<ZoneId> possessedLand(const State&, NationId nation);
std::vector<ZoneId> originalLand(const State&, NationId nation);
bool passableLandBorder(const State&, ZoneId from, ZoneId to);
bool controlledBy(const State&, NationId minor, NationId controller);
bool atWarWithMajor(const State&, NationId nation);
bool politicallyFriendly(const State&, NationId first, NationId second);
bool chineseHomeCountry(const State&, ZoneId zone);
// Until they evolve, CCP and KMT may only move or attack within Chinese Home
// Country and the sea zones adjacent to it (RB 14.3.1): whether this nation may
// enter this zone on that account. Every other nation may.
bool chineseMovementAllowed(const State&, NationId nation, ZoneId zone);
bool decentralizedProduction(const State&, NationId nation);
Id politicalPlayer(const State&, NationId nation);
void addPoliticalUnit(State&, NationId nation, const Id& type, ZoneId zone, int count = 1);
void removePoliticalUnits(State&, const std::set<Id>& units);
void incorporateNation(State&, NationId minor, NationId recipient);
void ensureDadao(State&);
void refreshPoliticalState(State&);
// Recomputes each nation's allies list, which follows wars, alliances and the
// Chinese Truce; refreshPoliticalState ends with it.
void refreshAlliances(State&);
void changePossession(State&, ZoneId zone, NationId recipient, PossessionCause,
                      std::optional<NationId> conqueror = std::nullopt);
// The withdrawal set is supplied by the movement module's route validator, never by a policy.
void captureLand(State&, NationId attacker, ZoneId zone,
                 const NumberSet<NationId>& withdrawalEligibleRecipients = {});
PoliticalPermission mayDeclareWar(const State&, NationId actor, NationId target,
                                  DeclarationMode = DeclarationMode::MajorPowerDeclaration);
void declareWar(State&, NationId actor, NationId target, DeclarationMode);
void recordLandAttack(State&, NationId attacker, ZoneId zone);
void surrenderNation(State&, NationId nation, NationId attacker);

// Shared decision/chance helpers keep continuations explicit in State, so
// checkpoints, planning keys and replay include all pending political work.
Action politicalAction(const State&, NationId decisionNation, const Id& kind,
                       json::Value parameters = json::Value::Object {},
                       const std::optional<Id>& decisionId = std::nullopt);
void queuePoliticalDecision(State&, NationId nation, const Id& kind,
                            std::vector<Action> options, json::Value continuation = json::Value::Object {});
void requestPoliticalRoll(State&, NationId nation, const Id& kind, int sides,
                          json::Value parameters = json::Value::Object {}, int dice = 1);
const json::Value& pendingPolitical(const State&, const Id& continuation);
void erasePoliticalContinuation(State&, const Id& continuation);

// Warlords, invasion alignment, and Chinese Truce (politics_warlords.cpp).
std::vector<Action> warlordActions(const State&);
bool applyWarlordAction(State&, const Action&);
bool applyWarlordChance(State&, const ChanceRequest&, const ChanceOutcome&);
void beginCombatPoliticalResolution(State&);
bool continueCombatPoliticalResolution(State&);
void terminateChineseTruce(State&, NationId breaker, bool evolution = false);

// Influence and the distinct CCP / controlled-minor recruitment rules.
std::vector<Action> influenceActions(const State&);
bool applyInfluenceAction(State&, const Action&);
bool applyInfluenceChance(State&, const ChanceRequest&, const ChanceOutcome&);

// Compose politics with the other gameplay modules. Without an accounting module,
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
    void settle(State&) const override;

  private:
    std::shared_ptr<const Rules> gameplay_;
};

} // namespace game::campaign
