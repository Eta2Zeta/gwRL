#pragma once

#include "game/marks.hpp"
#include "game/names.hpp"
#include "game/simple_json.hpp"
#include "game/slot_map.hpp"

#include <compare>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <iterator>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <string>
#include <unordered_map>
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
    // homeCountry as zone numbers. freezeDefinition fills it; never serialized.
    NumberSet<ZoneId> homeZones;
};

// The nations the rules name in their code, by number: empty for a nation a
// definition lacks. A rule compares a nation with one of these as it would
// with the name (`owner == known.japan`), at the cost of an integer compare.
// Never compare one with another optional, such as a territory's possessor:
// an empty possessor would equal a nation the definition lacks.
// isNation(state, possessor, "kmt") asks that question instead.
struct KnownNations {
    std::optional<NationId> japan, kmt, ccp, dadao, ussr, mongolia;
};

// The definition's tables of names held as numbers (include/game/names.hpp),
// built by freezeDefinition from the definition's own data. Never serialized:
// the names, not the numbers, are what a definition's fingerprint covers.
struct Names {
    NameTable<ZoneKind> zones;  // The keys of geography["nodes"].
    NameTable<NationKind> nations;  // The keys of factions, dormant ones too.
    KnownNations known;
};

// Derived solely from frozen map geometry, indexed by zone number. Neighbors
// keep the authoring data's source order. This shared view is neither
// serialized nor part of the definition fingerprint, and it is absent for a
// map whose edges are incomplete (some foundation fixtures).
struct IndexedGeography {
    std::vector<char> land;  // Per zone: whether its type is land.
    std::vector<ZoneId> landZones;  // The land zones, in number order.
    std::vector<std::vector<int>> hopDistances;  // [from][to]; -1 means unreachable.
    // Per zone, for rules that read the map inside move generation: a copy of
    // its JSON, its neighbors in source order (one entry per edge) and the
    // first edge to each neighbor. Edges point into nodes, so never copy this.
    std::vector<json::Value> nodes;
    std::vector<std::vector<ZoneId>> neighbors;
    std::vector<std::vector<std::pair<ZoneId, const json::Value*>>> edges;

    IndexedGeography() = default;
    IndexedGeography(const IndexedGeography&) = delete;
    IndexedGeography& operator=(const IndexedGeography&) = delete;
    NumberSet<ZoneId> withinHops(ZoneId origin, int range) const;
};

struct Definition {
    Id scenarioId;
    std::string fingerprint;  // Computed by freezeDefinition, never a policy feature.
    json::Value geography;
    // Rebuilt by freezeDefinition. The map index is absent for incomplete
    // foundation fixtures; the name tables always exist once frozen.
    std::shared_ptr<const IndexedGeography> indexedGeography;
    std::shared_ptr<const Names> names;
    json::Value rules;
    std::shared_ptr<const Catalog> catalog;
    std::map<Id, FactionDefinition> factions;
    // factions by nation number, copied by freezeDefinition: nationFaction reads
    // a nation's faction without looking its name up.
    std::vector<FactionDefinition> nationFactions;
    std::vector<Id> turnOrder;
    std::vector<NationId> turnNations;  // turnOrder as numbers; freezeDefinition fills it.
    std::set<Id> players;
    int startYear {1936};
    int startMonth {7};
    int calendarRounds {11};
};

std::shared_ptr<const Definition> freezeDefinition(Definition definition);

struct State;
// The definition's name tables, and a zone's number and name.
const Names& names(const State&);
ZoneId zoneNumber(const State&, std::string_view name);  // Throws "Unknown zone: <name>".
std::optional<ZoneId> findZone(const State&, std::string_view name);  // Empty for a name that is no zone.
bool isZone(const State&, ZoneId);  // Whether the number names one of the definition's zones.
const std::string& zoneName(const State&, ZoneId);
std::vector<ZoneId> zoneNumbers(const State&, const std::vector<Id>& names);
std::vector<Id> zoneNames(const State&, const std::vector<ZoneId>& zones);
// A nation's number and name, as for zones.
NationId nationNumber(const State&, std::string_view name);  // Throws "Unknown nation: <name>".
std::optional<NationId> findNation(const State&, std::string_view name);  // Empty for a name that is no nation.
const std::string& nationName(const State&, NationId);
const FactionDefinition& nationFaction(const State&, NationId);  // Throws for a number naming no nation.
const KnownNations& knownNations(const State&);
// Whether a nation, or a possessor that may be empty, is the nation of this
// name. False for an empty possessor and for a name the definition lacks.
bool isNation(const State&, NationId, std::string_view name);
bool isNation(const State&, const std::optional<NationId>&, std::string_view name);
// Whether the position holds a nation of this name.
bool hasNation(const State&, std::string_view name);
// A unit type's number and name, from the catalog's table (catalog.hpp), and
// the unit types and classes the rules name. Each throws for a definition
// without a catalog.
struct KnownUnitTypes;
struct KnownUnitClasses;
UnitTypeId unitTypeNumber(const State&, std::string_view name);  // Throws "Unknown unit type: <name>".
const std::string& unitTypeName(const State&, UnitTypeId);
const KnownUnitTypes& knownUnitTypes(const State&);
const KnownUnitClasses& knownUnitClasses(const State&);
// The same for facility types and technologies, also from the catalog.
struct KnownFacilityTypes;
struct KnownTechnologies;
FacilityTypeId facilityTypeNumber(const State&, std::string_view name);  // Throws "Unknown facility type: <name>".
const std::string& facilityTypeName(const State&, FacilityTypeId);
const KnownFacilityTypes& knownFacilityTypes(const State&);
TechnologyId technologyNumber(const State&, std::string_view name);  // Throws "Unknown technology: <name>".
const std::string& technologyName(const State&, TechnologyId);
const KnownTechnologies& knownTechnologies(const State&);

// What a construction project or a build-chart row builds: a unit type or a
// facility type, held as a number of its own kind. The catalog never gives a
// unit type and a facility type the same name, so a name says which of the two
// it is (buildTypeNumber). A default BuildType names nothing.
class BuildType {
  public:
    constexpr BuildType() = default;
    constexpr BuildType(UnitTypeId unit) : unit_(unit) {}
    constexpr BuildType(FacilityTypeId facility) : facility_(facility) {}
    constexpr bool valid() const { return unit_.valid() || facility_.valid(); }
    constexpr bool isUnit() const { return unit_.valid(); }
    constexpr bool isFacility() const { return facility_.valid(); }
    // The unit type; a default number, which names no unit type, for a facility type.
    constexpr UnitTypeId unit() const { return unit_; }
    // The facility type; a default number for a unit type.
    constexpr FacilityTypeId facility() const { return facility_; }
    friend constexpr bool operator==(BuildType, BuildType) = default;

  private:
    UnitTypeId unit_;
    FacilityTypeId facility_;
};
BuildType buildTypeNumber(const State&, std::string_view name);  // Throws "Unknown build type: <name>".
const std::string& buildTypeName(const State&, BuildType);

// Whether a nation has completed a technology (stage 4 of 4), and the set of
// technologies it has completed.
bool hasTechnology(const State&, NationId, TechnologyId);
NumberSet<TechnologyId> completedTechnologies(const State&, NationId);
// A railroad's name from the two land zones it connects, in either order.
Id railroadId(const State&, ZoneId a, ZoneId b);
// Map reads for rule hot paths. Each matches reading the definition's map JSON
// directly, including its errors, and uses the frozen index when it has one.
const json::Value& mapNode(const State&, ZoneId zone);
// First edge from one zone to a neighbor, or null.
const json::Value* mapEdge(const State&, ZoneId from, ZoneId to);
// Source-order neighbors, one per edge, borrowed from the index or read from the JSON.
class Neighbors {
  public:
    static Neighbors borrow(const std::vector<ZoneId>& zones) { Neighbors result; result.borrowed_ = &zones; return result; }
    static Neighbors own(std::vector<ZoneId> zones) { Neighbors result; result.owned_ = std::move(zones); return result; }
    const std::vector<ZoneId>& zones() const { return borrowed_ ? *borrowed_ : owned_; }
    std::vector<ZoneId>::const_iterator begin() const { return zones().begin(); }
    std::vector<ZoneId>::const_iterator end() const { return zones().end(); }
    std::size_t size() const { return zones().size(); }

  private:
    Neighbors() = default;
    const std::vector<ZoneId>* borrowed_ {nullptr};
    std::vector<ZoneId> owned_;
};
Neighbors mapNeighbors(const State&, ZoneId zone);

struct NationState {
    std::optional<NationId> controllerNation;
    std::optional<Id> player;
    std::optional<Id> alliance;
    std::string powerStatus {"minor"};
    std::optional<int> treasury;  // No account is different from an account with zero cash.
    std::map<Id, int> incomeComponents;  // The parts of its income as the position stands.
    bool incomeKnown {false};  // An unevaluated rate is not a zero-income ruling.
    // Research stage of each technology it has rolled for, 0 to 4; 4 is
    // complete. A technology never rolled for has no entry.
    NumberMap<TechnologyId, int> technologyStages;
    NumberSet<NationId> atWarWith;
    NumberSet<NationId> allies;
    Marks turnFlags;  // Marks (marks.hpp) cleared when the nation's turn begins.
    Marks gameFlags;  // Marks kept from turn to turn.
};

struct TerritoryState {
    std::optional<NationId> possessor;
    Marks flags;
};

// Units and facilities enter and leave a game, so the position keeps them in
// SlotMaps (slot_map.hpp): each has a slot there, fixed while it exists.
struct UnitKind {};
struct FacilityKind {};
using UnitSlot = Slot<UnitKind>;
using FacilitySlot = Slot<FacilityKind>;

struct UnitState {
    Id id;
    UnitTypeId type;  // A number in the catalog's unit type table (unitTypeName names it).
    NationId owner;
    ZoneId zone;
    // Set for every unit of a valid position: a unit's type comes from the catalog,
    // which gives its movement, and State::validate refuses a unit without it.
    std::optional<int> movementRemaining;
    std::optional<int> movementAllowance;
    ZoneId turnOrigin;
    std::vector<ZoneId> route;
    std::optional<Id> carriedBy;
    std::vector<Id> cargo;
    int damage {0};
    MarkSet commitments;  // What the unit is committed to this turn, as marks without values.
    Marks turnFlags;  // Marks cleared when its owner's turn begins.
    Marks gameFlags;  // Marks kept from turn to turn.
    UnitSlot slot;  // Its slot in the position's units, which the SlotMap writes; never set it.
};

struct FacilityState {
    Id id;
    FacilityTypeId type;  // A number in the catalog's facility type table (facilityTypeName names it).
    ZoneId zone;
    int damage {0};
    Marks flags;
    FacilitySlot slot;  // Its slot in the position's facilities, which the SlotMap writes; never set it.
};

struct RailState {
    Id id;  // railroadId(names of endpointA and endpointB)
    ZoneId endpointA;  // The two land zones it connects, endpointA < endpointB.
    ZoneId endpointB;
    // Bombing can target one side; do not erase that distinction in state.
    std::map<ZoneId, int> damageByEndpoint;
};

// A border has at most one railroad (RCL-019), so a railroad is named by the
// two land zones it connects, in sorted order: rail_<first>__<second>.
inline Id railroadId(const Id& a, const Id& b) {
    return a < b ? "rail_" + a + "__" + b : "rail_" + b + "__" + a;
}

struct BuildProject {
    Id id;
    NationId owner;
    BuildType type;  // The unit or facility it builds (buildTypeName names it).
    std::optional<Id> site;
    int queuePosition {1};
    int paidIpp {0};
    std::vector<int> remainingPayments;
    Marks flags;
};

struct RepairJob {
    Id id;
    NationId owner;
    Id target;
    int remainingDamage {0};
    int remainingCost {0};
    bool restrictsAction {true};
    std::optional<ZoneId> endpoint;  // Railroad damage belongs to a selected land side.
};

struct Action {
    Id id;
    std::string kind;
    Id player;
    Id nation;
    std::optional<Id> decision;
    json::Value parameters {json::Value::Object {}};
    // Derived immutable bytes from the authoritative menu. Never serialized,
    // supplied by a policy, or trusted as proof of legality.
    std::shared_ptr<const std::string> neuralSourceKey;
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
    ZoneId zone;
    NationId attacker;
    NationId defender;
    std::string stage;
    std::vector<Id> attackers;
    std::vector<Id> defenders;
    std::map<Id, int> pendingHits;
    Marks flags;
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
    NumberMap<ZoneId, std::optional<NationId>> possessions;
    std::map<Id, std::pair<NationId, ZoneId>> units;  // Stable unit ID -> (owner, zone).
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
    std::optional<NationId> chinaInvader;
    NumberMap<NationId, NumberSet<NationId>> attackedWarlords;
    std::vector<NationId> alignmentQueue;
    NumberMap<NationId, ZoneId> capitals;
    NumberSet<NationId> surrendered;
    NumberSet<NationId> evolutionAwarded;
    std::map<Id, json::Value> pending;
};

struct Event {
    std::string kind;
    json::Value payload;
    std::string afterStateKey;
};

// An append-only audit log whose copies share the recorded events, so copying
// a State for an engine step, search clone or rule probe does not copy history.
class EventLog {
    using Entries = std::vector<std::shared_ptr<const Event>>;

  public:
    class const_iterator {
      public:
        using iterator_category = std::random_access_iterator_tag;
        using value_type = Event;
        using difference_type = std::ptrdiff_t;
        using pointer = const Event*;
        using reference = const Event&;
        const_iterator() = default;
        explicit const_iterator(Entries::const_iterator at) : at_(at) {}
        reference operator*() const { return **at_; }
        pointer operator->() const { return at_->get(); }
        reference operator[](difference_type n) const { return *at_[n]; }
        const_iterator& operator++() { ++at_; return *this; }
        const_iterator operator++(int) { auto old = *this; ++at_; return old; }
        const_iterator& operator--() { --at_; return *this; }
        const_iterator operator--(int) { auto old = *this; --at_; return old; }
        const_iterator& operator+=(difference_type n) { at_ += n; return *this; }
        const_iterator& operator-=(difference_type n) { at_ -= n; return *this; }
        friend const_iterator operator+(const_iterator i, difference_type n) { return i += n; }
        friend const_iterator operator+(difference_type n, const_iterator i) { return i += n; }
        friend const_iterator operator-(const_iterator i, difference_type n) { return i -= n; }
        friend difference_type operator-(const const_iterator& a, const const_iterator& b) { return a.at_ - b.at_; }
        friend bool operator==(const const_iterator& a, const const_iterator& b) { return a.at_ == b.at_; }
        friend auto operator<=>(const const_iterator& a, const const_iterator& b) { return a.at_ <=> b.at_; }

      private:
        Entries::const_iterator at_;
    };
    using iterator = const_iterator;
    using value_type = Event;

    void push_back(Event event) { entries_.push_back(std::make_shared<const Event>(std::move(event))); }
    void clear() { entries_.clear(); }
    std::size_t size() const { return entries_.size(); }
    bool empty() const { return entries_.empty(); }
    const Event& operator[](std::size_t index) const { return *entries_[index]; }
    const Event& back() const { return *entries_.back(); }
    std::shared_ptr<const Event> lastEntry() const { return entries_.empty() ? nullptr : entries_.back(); }
    const_iterator begin() const { return const_iterator(entries_.begin()); }
    const_iterator end() const { return const_iterator(entries_.end()); }
    operator std::vector<Event>() const { return {begin(), end()}; }

  private:
    Entries entries_;
};

struct State {
    std::shared_ptr<const Definition> definition;
    NumberMap<NationId, NationState> nations;
    NumberMap<ZoneId, TerritoryState> territories;
    SlotMap<UnitKind, UnitState> units;  // By name, in name order; each unit also has a slot.
    SlotMap<FacilityKind, FacilityState> facilities;
    std::map<Id, RailState> rails;
    std::map<Id, BuildProject> construction;
    std::map<Id, RepairJob> repairs;
    Clock clock;
    PoliticalState politics;
    TurnSnapshot turnStart;
    NumberMap<NationId, int> completedTurns;
    std::vector<Decision> decisions;  // Last entry owns the current choice.
    std::map<Id, BattleState> battles;
    std::vector<Id> battleOrder;
    std::optional<ChanceRequest> chance;
    Marks flags;
    EventLog history;
    // Versioned AI action-construction state. Empty for the human/game API.
    // Public source data, included in observations, keys, clones and saves.
    json::Value actionInterface {json::Value::Object{}};
    bool terminal {false};

    State clone() const;  // Value-copy mutable data; share immutable definition.
    // A transition starts at the events it added: recorded events never change.
    void validate(std::size_t historyFrom = 0) const;
    NationId currentNation() const;
    const Id& currentNationName() const;
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
// The same digest without hardware instructions, which tests compare it with.
std::string portableContentDigest(const std::string& value);
json::Value actionJson(const Action& action);
Action actionFromJson(const json::Value& value);
json::Value outcomeJson(const ChanceOutcome& outcome);
ChanceOutcome outcomeFromJson(const json::Value& value);
json::Value chanceRequestJson(const ChanceRequest& request);

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

// Rules modules provide the game's rules. There is deliberately no permissive default
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
    // Runs when a campaign starts and at the end of every action, interrupt and
    // chance transition, before the position is recorded. A module brings the
    // values it keeps about the position up to date here, and passes the call
    // on to the module it wraps. A rules profile may also take steps that offer
    // no choice; they become part of the transition that made them possible.
    virtual void settle(State&) const {}
};

// While open, marks the action Engine::step is applying as one it found in the
// complete menu of the position it applies it to. A rule that checks an action
// by listing its own menu again may skip that check for the marked Action
// object; an action a rule builds for itself is not marked and is checked.
class MenuCheckedAction {
  public:
    explicit MenuCheckedAction(const Action&);
    ~MenuCheckedAction();
    MenuCheckedAction(const MenuCheckedAction&) = delete;
    MenuCheckedAction& operator=(const MenuCheckedAction&) = delete;
    static bool marks(const Action&);

  private:
    const Action* outer_;
};

class Engine {
  public:
    Id rulesId() const { requireIntact(); return rules_->id(); }
    // Wrap an already prepared state; no start-of-turn hook is re-applied.
    Engine(State initial, std::shared_ptr<const Rules> rules, std::uint64_t seed = 1);
    // A fresh campaign invokes the first nation's beginTurn exactly once.
    static Engine start(State initial, std::shared_ptr<const Rules> rules, std::uint64_t seed = 1);
    const State& state() const { requireIntact(); return state_; }
    std::vector<Action> legalActions() const;
    // The cached menu itself, which stays valid after this engine changes.
    std::shared_ptr<const std::vector<Action>> legalActionMenu() const;
    std::vector<Action> legalInterrupts() const;
    void step(const Action& action);
    void interrupt(const Action& action);
    void resolveChance();  // Execution service, never a policy action.
    // Explicit conformance/replay input. Validates the complete current decision
    // and every face/reroll, applies ordinary rules/history, and consumes no RNG.
    void applyChanceOutcome(const std::string& expectedKey, const ChanceOutcome&);
    Engine clone() const;  // An ordinary engine, also when copied from a search copy.
    // A copy for one simulation, on the search random stream. It is thrown away
    // afterwards, so it changes its state in place, without the rollback an
    // ordinary engine has. Should a transition fail after its legality check,
    // the copy refuses every later call; a rejected action leaves it usable.
    Engine cloneForSearch(std::uint64_t seed) const;
    // The same, with dice that continue `source`'s search stream where it has
    // got to: a search can save copies of positions and still roll each
    // simulation's dice from one stream.
    Engine cloneForSearchContinuing(const Engine& source) const;
    void setDiceTapeForTesting(std::vector<int> tape);
    std::string serialize() const;
    static Engine restore(std::shared_ptr<const Definition>, std::shared_ptr<const Rules>, const std::string&);
    static Engine replay(std::shared_ptr<const Definition>, std::shared_ptr<const Rules>,
                         const std::string& checkpoint, const std::vector<Event>& events);
    std::string exactReplayIdentity() const;
    std::string planningKey() const;
    void requireIntact() const {
        if (unfinished_) throw std::runtime_error("Search copy failed during a transition");
    }

  private:
    struct ActionMenu;
    struct DecisionCache;
    struct MenuTable;
    State state_;
    std::shared_ptr<const Rules> rules_;
    RandomStreams random_;
    // One complete decision state per engine. Clones share lazily constructed,
    // immutable menus; a mutation detaches before changing the cloned state.
    std::shared_ptr<DecisionCache> decisionCache_;
    // Bounded menus by complete planning key, shared by every clone of one
    // engine, so a search clone reaching another clone's state reuses its menu.
    std::shared_ptr<MenuTable> menuTable_;
    bool disposable_ {false};
    bool unfinished_ {false};  // Stays set if a transition in place throws.
    std::shared_ptr<const ActionMenu> actionMenu() const;
    std::shared_ptr<const ActionMenu> interruptMenu() const;
    void invalidateDecisionCache();
    template <class Change> void transition(Change&& change);
    void commitChance(const ChanceRequest&, const ChanceOutcome&);
    void settle();
    void endPhase();
};

State loadScenario(const std::filesystem::path& scenarioDirectory);

}  // namespace game::campaign
