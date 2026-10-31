#include "game/campaign_actions.hpp"

#include "game/air.hpp"
#include "game/campaign_audit.hpp"
#include "game/catalog.hpp"
#include "game/land_combat.hpp"
#include "game/naval.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <functional>
#include <stdexcept>

namespace game::campaign {
namespace {
using V = json::Value;
using O = V::Object;
using A = V::Array;

// Builds the message only on failure; most messages are literals.
template <class Message> void require(bool yes, const Message &message) {
    if (!yes) throw std::runtime_error(message);
}

V integer(int value) { return V(static_cast<double>(value)); }
V optionalNumber(const std::optional<int>& value) { return value ? integer(*value) : V(nullptr); }
V flags(const std::map<Id, int>& source) {
    O result;
    for (const auto& [key, value] : source) result.emplace(key, integer(value));
    return V(std::move(result));
}
V ids(const std::vector<Id>& source) {
    A result;
    for (const auto& id : source) result.emplace_back(id);
    return V(std::move(result));
}

O metadata(const State& state) {
    if (state.actionInterface.asObject().empty())
        return { {"schema", V(trainingActionSchema)}, {"visited_configurations", V(A{})},
                 {"declined_rail_requests", V(A{})} };
    return state.actionInterface.asObject();
}

void reset(State& state) {
    state.actionInterface = V(O{{"schema", V(trainingActionSchema)},
                               {"visited_configurations", V(A{})},
                               {"declined_rail_requests", V(A{})}});
}

const A& records(const State& state, const Id& key) {
    static const A empty;
    const auto* value = state.actionInterface.find(key);
    return value ? value->asArray() : empty;
}

bool contains(const A& records, const V& value) {
    const auto text = canonicalJson(value);
    return std::any_of(records.begin(), records.end(), [&](const V& record) {
        return canonicalJson(record) == text;
    });
}

void remember(State& state, const Id& key, const V& value) {
    auto data = metadata(state);
    auto list = data.at(key).asArray();
    if (!contains(list, value)) list.push_back(value);
    data[key] = V(std::move(list));
    state.actionInterface = V(std::move(data));
}

// Only these fields can change during a reversible role/deck-assignment run.
// Their readable values are retained, rather than an opaque planning identity.
V configuration(const State& state) {
    O raiders, aircraft, carriers;
    std::set<Id> deckZones;
    for (const auto& [id, unit] : state.units) {
        if (unitClass(state, unit, "carrier")) deckZones.insert(unit.zone);
        if (unit.type == "battlecruiser" && movementController(state, unit.owner)) {
            O roles;
            for (const auto* key : {"raider", "naval_raider"})
                if (const auto found = unit.gameFlags.find(key); found != unit.gameFlags.end())
                    roles.emplace(key, integer(found->second));
            raiders.emplace(id, V(std::move(roles)));
        }
    }
    std::set<Id> relevantZones;
    for (const auto& [id, unit] : state.units)
        if (isAircraft(state, unit) && movementController(state, unit.owner) && deckZones.contains(unit.zone)) {
            relevantZones.insert(unit.zone);
            aircraft.emplace(id, V(O{{"zone", V(unit.zone)},
                {"carried_by", unit.carriedBy ? V(*unit.carriedBy) : V(nullptr)},
                {"route", ids(unit.route)}, {"movement_allowance", optionalNumber(unit.movementAllowance)},
                {"movement_remaining", optionalNumber(unit.movementRemaining)},
                {"turn_flags", flags(unit.turnFlags)}}));
        }
    for (const auto& [id, unit] : state.units)
        if (unitClass(state, unit, "carrier") && relevantZones.contains(unit.zone))
            carriers.emplace(id, V(O{{"cargo", ids(unit.cargo)}}));
    return V(O{{"raiders", V(std::move(raiders))}, {"aircraft", V(std::move(aircraft))},
               {"carriers", V(std::move(carriers))}});
}

bool reversibleConfigurationAction(const State& state, const Action& action) {
    if (action.kind == "naval_designate_raider" || action.kind == "naval_remove_raider") return true;
    if (action.kind != "air_land_noncombat") return false;
    const auto& unit = state.units.at(action.parameters.require("unit").asString());
    const auto destination = action.parameters.require("destination").asString();
    const auto carrier = state.units.find(destination);
    const auto zone = carrier != state.units.end() ? carrier->second.zone : destination;
    if (unit.zone != zone) return false;
    // A carrier at a port also permits a zero-distance deck -> land -> deck
    // assignment. Real inland returns without a nearby carrier remain ordinary
    // progress, so their mandatory landing effects are never filtered away.
    return std::any_of(state.units.begin(), state.units.end(), [&](const auto& entry) {
        return entry.second.zone == zone && unitClass(state, entry.second, "carrier");
    });
}

bool visited(const State& state, const V& current, const V& candidate) {
    return canonicalJson(current) == canonicalJson(candidate) ||
           contains(records(state, "visited_configurations"), candidate);
}

V railSignature(const State& state, const Action& action) {
    const auto& border = action.parameters.require("border").asString();
    const auto recipient = state.territories.at(border).possessor;
    require(recipient.has_value(), "Railroad consent has no recipient");
    return V(O{{"sender", V(action.nation)}, {"recipient", V(*recipient)},
               {"parameters", action.parameters}});
}

V declinedRailSignature(const State& state, const Action& action) {
    require(!state.decisions.empty() && state.decisions.back().kind == "economy_rail_permission",
            "Railroad decline has no pending consent");
    const auto& pending = pendingPolitical(state, state.decisions.back().continuation);
    return V(O{{"sender", pending.require("sender")}, {"recipient", V(action.nation)},
               {"parameters", pending.require("parameters")}});
}

bool flagged(const std::map<Id, int>& flags, const char* key) {
    const auto found = flags.find(key);
    return found != flags.end() && found->second != 0;
}

// The click that deletes a finished battle, if the combat menu offers one now.
// NavalRules lists a finished naval battle's click alone and hides the land
// combat menu while a naval battle is active or the land battles are immediate.
std::optional<Action> battleClearing(const State& state) {
    if (state.terminal || state.chance || !state.decisions.empty()) return std::nullopt;
    if (!flagged(state.flags, "immediate_land_battles")) {
        for (auto& action : navalCombatActions(state))
            if (action.kind == "naval_finish_battle") return std::move(action);
        const bool navalActive = flagged(state.flags, "immediate_naval_battles") ||
            std::any_of(state.battles.begin(), state.battles.end(), [](const auto& entry) {
                const auto& battle = entry.second;
                return flagged(battle.flags, "naval_battle") && !flagged(battle.flags, "finished") &&
                       battle.stage != "naval_declared";
            });
        if (navalActive) return std::nullopt;
    }
    auto land = landBattleClearing(state);
    if (land.empty()) return std::nullopt;
    return std::move(land.front());
}

bool preservesConstructionContext(const Action& action) {
    return action.kind == "economy_request_rail" || action.kind == "economy_decline_rail" ||
           action.kind == "naval_start_move" || action.kind == "naval_force_add" ||
           action.kind == "naval_force_remove" || action.kind == "naval_cancel_move" ||
           action.kind == "naval_screen_add" || action.kind == "naval_screen_remove";
}

class TrainingRules final : public Rules {
  public:
    explicit TrainingRules(std::shared_ptr<const Rules> core) : core_(std::move(core)) {}
    Id id() const override { return std::string(trainingActionSchema) + "+" + core_->id(); }
    std::vector<Action> actions(const State& state) const override {
        auto result = forwardNavalOrderActions(state, core_->actions(state));
        std::optional<V> current;
        result.erase(std::remove_if(result.begin(), result.end(), [&](const Action& action) {
            if (action.kind == "economy_request_rail")
                return contains(records(state, "declined_rail_requests"), railSignature(state, action));
            if (!reversibleConfigurationAction(state, action)) return false;
            if (!current) current = configuration(state);
            auto candidate = state.clone();
            core_->apply(candidate, action);
            return visited(state, *current, configuration(candidate));
        }), result.end());
        return result;
    }
    std::vector<Action> interrupts(const State& state) const override { return core_->interrupts(state); }
    bool phaseComplete(const State& state) const override { return core_->phaseComplete(state); }
    void apply(State& state, const Action& action) const override {
        if (reversibleConfigurationAction(state, action)) {
            const auto current = configuration(state);
            auto next = state.clone();
            core_->apply(next, action);
            forwardNavalOrderDecision(next);
            const auto candidate = configuration(next);
            require(!visited(state, current, candidate), "Campaign order repeats an unchanged configuration");
            remember(next, "visited_configurations", current);
            remember(next, "visited_configurations", candidate);
            state = std::move(next);
            return;
        }
        std::optional<V> decline;
        if (action.kind == "economy_decline_rail") decline = declinedRailSignature(state, action);
        if (action.kind == "economy_request_rail")
            require(!contains(records(state, "declined_rail_requests"), railSignature(state, action)),
                    "Identical railroad consent was already declined in this decision context");
        core_->apply(state, action);
        if (!preservesConstructionContext(action)) reset(state);
        if (decline) remember(state, "declined_rail_requests", *decline);
        forwardNavalOrderDecision(state);
    }
    void applyChance(State& state, const ChanceRequest& request, const ChanceOutcome& outcome) const override {
        core_->applyChance(state, request, outcome);
        reset(state);
        forwardNavalOrderDecision(state);
    }
    void finishTurn(State& state) const override {
        core_->finishTurn(state);
        reset(state);
        forwardNavalOrderDecision(state);
    }
    void beginTurn(State& state) const override {
        core_->beginTurn(state);
        reset(state);
        forwardNavalOrderDecision(state);
    }
    void finishPhase(State& state) const override {
        core_->finishPhase(state);
        reset(state);
        forwardNavalOrderDecision(state);
    }
    void settle(State& state) const override {
        core_->settle(state);
        // A finished battle stays listed only until its follow-ups are done. Its
        // click then only deletes the record, in any order, so the profile takes
        // each one itself as soon as it is offered, exactly as if chosen.
        while (const auto clearing = battleClearing(state)) apply(state, *clearing);
    }
  private:
    std::shared_ptr<const Rules> core_;
};

void exactKeys(const V& value, const std::set<Id>& expected, const Id& label) {
    require(value.isObject(), "Action-interface " + label + " must be an object");
    std::set<Id> keys;
    for (const auto& [key, entry] : value.asObject()) keys.insert(key);
    require(keys == expected, "Action-interface " + label + " has unknown or missing fields");
}

void integerRecord(const V& value, const Id& label) {
    require(value.isObject(), "Action-interface " + label + " must be an object");
    for (const auto& [key, number] : value.asObject()) {
        require(!key.empty() && number.isNumber(), "Invalid action-interface integer record");
        (void)number.asInt();
    }
}

void stringArray(const V& value, const Id& label, const std::function<bool(const Id&)>& allowed) {
    require(value.isArray(), "Action-interface " + label + " must be an array");
    for (const auto& entry : value.asArray())
        require(entry.isString() && allowed(entry.asString()), "Invalid action-interface " + label + " identity");
}

std::set<Id> keys(const V& object) {
    std::set<Id> result;
    for (const auto& [key, value] : object.asObject()) result.insert(key);
    return result;
}

}  // namespace

std::shared_ptr<const Rules> trainingCampaignRules() {
    return std::make_shared<TrainingRules>(campaignRules());
}

void validateTrainingActionState(const State& state) {
    require(state.actionInterface.isObject(), "Action-interface state must be an object");
    if (state.actionInterface.asObject().empty()) return;
    exactKeys(state.actionInterface, {"schema", "visited_configurations", "declined_rail_requests"}, "state");
    require(state.actionInterface.require("schema").isString() &&
            state.actionInterface.require("schema").asString() == trainingActionSchema,
            "Unsupported campaign action-interface schema");
    require(state.actionInterface.require("visited_configurations").isArray() &&
            state.actionInterface.require("declined_rail_requests").isArray(),
            "Campaign action-interface continuation lists must be arrays");
    const auto* visitedRecords = state.actionInterface.find("visited_configurations");
    const auto current = visitedRecords && !visitedRecords->asArray().empty() ? configuration(state) : V(nullptr);
    std::set<std::string> seen;
    for (const auto& record : records(state, "visited_configurations")) {
        exactKeys(record, {"raiders", "aircraft", "carriers"}, "configuration");
        for (const auto* category : {"raiders", "aircraft", "carriers"}) {
            require(record.require(category).isObject(), "Configuration registry must be an object");
            require(keys(record.require(category)) == keys(current.require(category)),
                    "Configuration registry belongs to a different decision context");
        }
        for (const auto& [id, roles] : record.require("raiders").asObject()) {
            integerRecord(roles, "raider flags");
            for (const auto& [key, value] : roles.asObject())
                require(key == "raider" || key == "naval_raider", "Unknown raider configuration field");
        }
        for (const auto& [id, plane] : record.require("aircraft").asObject()) {
            exactKeys(plane, {"zone", "carried_by", "route", "movement_allowance", "movement_remaining", "turn_flags"}, "aircraft");
            require(plane.require("zone").isString() &&
                    state.definition->geography.require("nodes").find(plane.require("zone").asString()),
                    "Invalid aircraft configuration zone");
            const auto& parent = plane.require("carried_by");
            require(parent.isNull() || (parent.isString() && state.units.contains(parent.asString()) &&
                    unitClass(state, state.units.at(parent.asString()), "carrier")), "Invalid aircraft carrier configuration");
            for (const auto* field : {"movement_allowance", "movement_remaining"}) {
                const auto& amount = plane.require(field);
                require(amount.isNull() || amount.isNumber(), "Invalid aircraft movement configuration");
                if (amount.isNumber()) (void)amount.asInt();
            }
            stringArray(plane.require("route"), "aircraft route", [&](const Id& zone) {
                return state.definition->geography.require("nodes").find(zone) != nullptr;
            });
            integerRecord(plane.require("turn_flags"), "aircraft turn flags");
        }
        for (const auto& [id, carrier] : record.require("carriers").asObject()) {
            exactKeys(carrier, {"cargo"}, "carrier");
            stringArray(carrier.require("cargo"), "carrier cargo", [&](const Id& unit) { return state.units.contains(unit); });
            std::set<Id> cargo;
            for (const auto& entry : carrier.require("cargo").asArray())
                require(cargo.insert(entry.asString()).second, "Duplicate carrier cargo configuration");
        }
        require(seen.insert(canonicalJson(record)).second, "Duplicate visited configuration");
    }
    if (!records(state, "visited_configurations").empty())
        require(canonicalJson(records(state, "visited_configurations").back()) == canonicalJson(current),
                "Visited configuration does not match the current decision context");
    seen.clear();
    for (const auto& request : records(state, "declined_rail_requests")) {
        exactKeys(request, {"sender", "recipient", "parameters"}, "railroad request");
        for (const auto* field : {"sender", "recipient"})
            require(request.require(field).isString() && state.nations.contains(request.require(field).asString()),
                    "Invalid railroad request nation");
        const auto& parameters = request.require("parameters");
        require(parameters.isObject(), "Railroad request parameters must be an object");
        if (parameters.find("project")) exactKeys(parameters, {"project", "zone", "border"}, "railroad parameters");
        else exactKeys(parameters, {"row", "price", "zone", "border"}, "railroad parameters");
        for (const auto& [field, value] : parameters.asObject())
            require(value.isString() && !value.asString().empty(), "Invalid railroad request parameter");
        for (const auto* field : {"zone", "border"})
            require(state.territories.contains(parameters.require(field).asString()), "Invalid railroad request endpoint");
        require(request.require("sender").asString() == state.currentNation() &&
                state.territories.at(parameters.require("border").asString()).possessor ==
                    std::optional<Id>(request.require("recipient").asString()) &&
                request.require("sender").asString() != request.require("recipient").asString(),
                "Railroad request belongs to a different decision context");
        if (const auto* project = parameters.find("project"))
            require(state.construction.contains(project->asString()), "Unknown railroad request project");
        else
            require(state.definition->catalog->rows().contains(parameters.require("row").asString()) &&
                    state.definition->catalog->row(parameters.require("row").asString()).type == "railroad",
                    "Unknown railroad request purchase row");
        require(seen.insert(canonicalJson(request)).second, "Duplicate declined railroad request");
    }
}

}  // namespace game::campaign
