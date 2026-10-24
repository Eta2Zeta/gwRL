#pragma once

#include "game/simple_json.hpp"

#include <cstdint>
#include <filesystem>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <string>
#include <vector>

// The shared campaign foundation. The prototype API remains available while
// its gameplay handlers are replaced by modules using this state.
namespace game::campaign {

using Id = std::string;
class Catalog;

enum class Phase { Production, CombatMovement, Combat, NonCombatMovement, PlaceUnits };
std::string toString(Phase phase);
Phase parsePhase(const std::string& text);

struct FactionDefinition {
    Id id;
    std::string displayName;
    std::set<Id> homeCountry;
    bool homeCountryKnown {false};
    bool dormant {false};
};

struct Definition {
    Id scenarioId;
    std::string fingerprint;  // Computed by freezeDefinition, never a policy feature.
    json::Value geography;
    json::Value rules;
    std::shared_ptr<const Catalog> catalog;
    std::map<Id, FactionDefinition> factions;
    std::vector<Id> turnOrder;
    std::set<Id> players;
    int startYear {1936};
    int startMonth {7};
    int calendarRounds {11};
};

std::shared_ptr<const Definition> freezeDefinition(Definition definition);

struct NationState {
    std::optional<Id> controllerNation;
    std::optional<Id> player;
    std::optional<Id> alliance;
    std::string powerStatus {"minor"};
    std::optional<int> treasury;  // No account is different from an account with zero cash.
    std::map<Id, int> incomeComponents;
    bool incomeKnown {false};  // An unevaluated rate is not a zero-income ruling.
    std::map<Id, int> technologyStages;
    std::set<Id> atWarWith;
    std::set<Id> allies;
    std::map<Id, int> turnFlags;
    std::map<Id, int> gameFlags;
};

struct TerritoryState {
    std::optional<Id> possessor;
    std::map<Id, int> flags;
};

struct UnitState {
    Id id;
    Id type;
    Id owner;
    Id zone;
    // Null is reserved for catalog-free foundation fixtures, never zero movement.
    std::optional<int> movementRemaining;
    std::optional<int> movementAllowance;
    Id turnOrigin;
    std::vector<Id> route;
    std::optional<Id> carriedBy;
    std::vector<Id> cargo;
    int damage {0};
    std::set<Id> commitments;
    std::map<Id, int> turnFlags;
    std::map<Id, int> gameFlags;
};

struct FacilityState {
    Id id;
    Id type;
    Id zone;
    int damage {0};
    std::map<Id, int> flags;
};

struct RailState {
    Id id;
    Id endpointA;
    Id endpointB;
    // Bombing can target one side; do not erase that distinction in state.
    std::map<Id, int> damageByEndpoint;
};

struct BuildProject {
    Id id;
    Id owner;
    Id type;
    std::optional<Id> site;
    int queuePosition {1};
    int paidIpp {0};
    std::vector<int> remainingPayments;
    std::map<Id, int> flags;
};

struct RepairJob {
    Id id;
    Id owner;
    Id target;
    int remainingDamage {0};
    int remainingCost {0};
    bool restrictsAction {true};
    std::optional<Id> endpoint;  // Railroad damage belongs to a selected land side.
};

struct Action {
    Id id;
    std::string kind;
    Id player;
    Id nation;
    std::optional<Id> decision;
    json::Value parameters {json::Value::Object {}};
};

struct Decision {
    Id id;
    std::string kind;
    Id nation;
    bool reaction {false};
    std::string continuation;
    std::vector<Action> options;
};

struct BattleState {
    Id id;
    Id zone;
    Id attacker;
    Id defender;
    std::string stage;
    std::vector<Id> attackers;
    std::vector<Id> defenders;
    std::map<Id, int> pendingHits;
    std::map<Id, int> flags;
    // Explicit battle continuations, participant roles and roll/casualty queues.
    // This is serialized decision state, never module-local memory.
    json::Value data {json::Value::Object {}};
};

struct DieSpec {
    int sides {12};
    int modifier {0};
    std::set<int> rerollFaces;
    int maxRerolls {0};
};

struct ChanceRequest {
    Id id;
    std::string purpose;
    Id nation;
    std::string continuation;
    std::vector<DieSpec> dice;
};

struct ChanceOutcome {
    std::vector<std::vector<int>> faces;  // Each die's first face and any required rerolls.
};

struct TurnSnapshot {
    std::map<Id, std::optional<Id>> possessions;
    std::map<Id, std::pair<Id, Id>> units;  // Stable unit ID -> (owner, zone).
};

struct Clock {
    int roundIndex {0};
    int nationIndex {0};
    Phase phase {Phase::Production};
    int completedRounds {0};
    std::uint64_t playerTurnSerial {0};
    bool incomeCollected {false};
};

struct PoliticalState {
    bool chineseTruce {false};
    bool trucePermanentlyEnded {false};
    bool foreignChinaWarPending {false};
    bool truceOfferPending {false};
    std::optional<Id> chinaInvader;
    std::map<Id, std::set<Id>> attackedWarlords;
    std::vector<Id> alignmentQueue;
    std::map<Id, Id> capitals;
    std::set<Id> surrendered;
    std::set<Id> evolutionAwarded;
    std::map<Id, json::Value> pending;
};

struct Event {
    std::string kind;
    json::Value payload;
    std::string afterStateKey;
};

struct State {
    std::shared_ptr<const Definition> definition;
    std::map<Id, NationState> nations;
    std::map<Id, TerritoryState> territories;
    std::map<Id, UnitState> units;
    std::map<Id, FacilityState> facilities;
    std::map<Id, RailState> rails;
    std::map<Id, BuildProject> construction;
    std::map<Id, RepairJob> repairs;
    Clock clock;
    PoliticalState politics;
    TurnSnapshot turnStart;
    std::map<Id, int> completedTurns;
    std::vector<Decision> decisions;  // Last entry owns the current choice.
    std::map<Id, BattleState> battles;
    std::vector<Id> battleOrder;
    std::optional<ChanceRequest> chance;
    std::map<Id, int> flags;
    std::vector<Event> history;
    bool terminal {false};

    State clone() const;  // Value-copy mutable data; share immutable definition.
    void validate() const;
    Id currentNation() const;
    std::optional<Id> decisionPlayer() const;
    std::pair<int, int> calendarDate() const;
    void captureTurnStart();
    json::Value toJson(bool includeHistory = true) const;
    static State fromJson(std::shared_ptr<const Definition>, const json::Value&);
    std::string serialize() const;
    std::string planningKey() const;  // Complete decision state, excludes history and all RNG.
    json::Value observation() const;  // No execution RNG or future test tape exists in State.
};

// JSON is canonical and finite. Large execution counters use decimal strings.
std::string canonicalJson(const json::Value& value);
std::string contentDigest(const std::string& value);
json::Value actionJson(const Action& action);
Action actionFromJson(const json::Value& value);
json::Value outcomeJson(const ChanceOutcome& outcome);
ChanceOutcome outcomeFromJson(const json::Value& value);

struct RandomStreams {
    std::uint64_t actual {1};
    std::uint64_t search {2};
    std::uint64_t training {3};
    std::string active {"actual"};
    std::vector<int> testTape;
    std::size_t tapePosition {0};

    static RandomStreams seeded(std::uint64_t seed);
    int roll(int sides);
    json::Value toJson() const;
    static RandomStreams fromJson(const json::Value& value);
};

std::vector<int> effectiveResults(const ChanceRequest&, const ChanceOutcome&);
double outcomeProbability(const ChanceRequest&, const ChanceOutcome&);

// M3+ modules provide game rules. There is deliberately no permissive default
// implementation that would present phase-only stepping as a playable campaign.
// Modules are immutable/stateless: all decision-relevant effects belong in
// State fields and flags. State.history is an audit log, not hidden rule state.
class Rules {
  public:
    virtual ~Rules() = default;
    virtual Id id() const = 0;
    virtual std::vector<Action> actions(const State&) const = 0;
    virtual std::vector<Action> interrupts(const State&) const { return {}; }
    virtual bool phaseComplete(const State&) const = 0;
    virtual void apply(State&, const Action&) const = 0;
    virtual void applyChance(State&, const ChanceRequest&, const ChanceOutcome&) const = 0;
    // Must explicitly finish collection/accounting and set clock.incomeCollected.
    virtual void finishTurn(State&) const = 0;
    virtual void beginTurn(State&) const {}
    virtual void finishPhase(State&) const {}
};

class Engine {
  public:
    // Wrap an already prepared state; no start-of-turn hook is re-applied.
    Engine(State initial, std::shared_ptr<const Rules> rules, std::uint64_t seed = 1);
    // A fresh campaign invokes the first nation's beginTurn exactly once.
    static Engine start(State initial, std::shared_ptr<const Rules> rules, std::uint64_t seed = 1);
    const State& state() const { return state_; }
    std::vector<Action> legalActions() const;
    std::vector<Action> legalInterrupts() const;
    void step(const Action& action);
    void interrupt(const Action& action);
    void resolveChance();  // Execution service, never a policy action.
    Engine clone() const;
    Engine cloneForSearch(std::uint64_t seed) const;
    void setDiceTapeForTesting(std::vector<int> tape);
    std::string serialize() const;
    static Engine restore(std::shared_ptr<const Definition>, std::shared_ptr<const Rules>, const std::string&);
    static Engine replay(std::shared_ptr<const Definition>, std::shared_ptr<const Rules>,
                         const std::string& checkpoint, const std::vector<Event>& events);
    std::string exactReplayIdentity() const;
    std::string planningKey() const;

  private:
    struct ActionMenu;
    struct DecisionCache;
    State state_;
    std::shared_ptr<const Rules> rules_;
    RandomStreams random_;
    // One complete decision state per engine. Clones share lazily constructed,
    // immutable menus; a mutation detaches before changing the cloned state.
    std::shared_ptr<DecisionCache> decisionCache_;
    std::shared_ptr<const ActionMenu> actionMenu() const;
    std::shared_ptr<const ActionMenu> interruptMenu() const;
    void invalidateDecisionCache();
    void endPhase();
};

State loadScenario(const std::filesystem::path& scenarioDirectory);

}  // namespace game::campaign
