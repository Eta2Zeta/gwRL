#pragma once

#include "game/names.hpp"

#include <algorithm>
#include <compare>
#include <cstddef>
#include <cstdint>
#include <initializer_list>
#include <iterator>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

// Marks held as numbers.
//
// A mark is a small fact a rule notes, with a whole number, on a unit, a
// nation, a territory, a facility, a construction project, a battle or the
// position itself: placed_this_turn = 1, naval_movement_spent = 2,
// economy_production_cap:facility_honshu_airfield = 3. A unit's commitments
// are marks without numbers, such as combat_move. A mark's name has a base,
// which says what the mark records, and for some bases an argument, which says
// what it is about: a zone, a nation, a facility and so on.
//
// The engine numbers the bases. GWRL_MARKS below lists every base a position
// may hold, sorted bytewise, with the argument it takes ("" for none); a base's
// number is its place in the list (MarkId, like the kinds in names.hpp), and
// mark::placed_this_turn names that number in code. The argument stays text,
// held in one buffer per set of marks (Marks), so copying a set allocates
// twice however many marks it holds.
//
// Saved positions, planning keys and observations still write each mark by its
// name: the base, then for a mark with an argument ':' (or '_' for the bases in
// GWRL_MARKS_JOINED_BY_UNDERSCORE) and the argument. Numbers follow the names'
// order, and the static_asserts below keep it so, so a set of marks lists them
// in the order of their names, as the string-keyed maps it replaced did.
// tools/print_name_tables.py prints the table; docs/engine/names.md explains it.

namespace game::campaign {

struct MarkKind {
    using Rep = std::uint16_t;
    static constexpr std::size_t capacity = 1024;
    static constexpr std::string_view noun = "mark";
};
using MarkId = Number<MarkKind>;

// Each row: the identifier code uses (mark::<identifier>), the mark's name,
// what its argument names ("" for a mark without one) and the kinds of thing
// the rules put it on: unit, nation, territory, facility, project (a
// construction project), battle and game (the position as a whole), or
// nowhere. The identifier is the name except for __campaign_started, a name
// C++ reserves. Add a row, in name order, when a rule starts to note a new
// mark, and add a kind when a rule starts to put a mark on another kind of
// thing: tools/mark_writes.py lists every place the code gives a mark a value
// and what it lands on, and a test checks the table against it. The network's
// input asks about a mark only on the kinds listed here. A mark the rules only
// read, never set, is on nowhere. fixture:<name> is for test rules and tools,
// such as a test's own bookkeeping; no rule of the game notes one.
#define GWRL_MARKS(X) \
    X(campaign_started, "__campaign_started", "", game) \
    X(access_to_resources_completed, "access_to_resources_completed", "", nowhere) \
    X(air_allied_loaded_turn, "air_allied_loaded_turn", "", unit) \
    X(air_battle, "air_battle", "battle", unit) \
    X(air_battle_turn, "air_battle_turn", "", unit) \
    X(air_combat, "air_combat", "", unit) \
    X(air_decision_sequence, "air_decision_sequence", "", game) \
    X(air_defending_carrier, "air_defending_carrier", "unit", unit) \
    X(air_in_flight, "air_in_flight", "", unit) \
    X(air_landed_after_combat, "air_landed_after_combat", "", unit) \
    X(air_mission, "air_mission", "", battle) \
    X(air_mission_sequence, "air_mission_sequence", "", game) \
    X(air_roll_sequence, "air_roll_sequence", "", game) \
    X(air_scramble_origin, "air_scramble_origin", "zone", unit) \
    X(air_scramble_source, "air_scramble_source", "scramble source", unit) \
    X(air_scramble_turn, "air_scramble_turn", "", facility) \
    X(air_scramble_used, "air_scramble_used", "", facility) \
    X(air_screening_continued, "air_screening_continued", "", unit) \
    X(air_screening_ready, "air_screening_ready", "", unit) \
    X(air_screening_wait, "air_screening_wait", "", unit) \
    X(air_transport_unloaded, "air_transport_unloaded", "", unit) \
    X(air_waiting_port_evacuation, "air_waiting_port_evacuation", "", battle) \
    X(airborne_assault, "airborne_assault", "", unit | battle) \
    X(aligned_turn, "aligned_turn", "", territory) \
    X(amphibious_assault, "amphibious_assault", "", unit | battle) \
    X(amphibious_preparation, "amphibious_preparation", "", battle) \
    X(amphibious_sequence, "amphibious_sequence", "", game) \
    X(amphibious_transport, "amphibious_transport", "unit", unit) \
    X(artillery_city_bombing, "artillery_city_bombing", "", battle) \
    X(assault_declared, "assault_declared", "", unit) \
    X(assault_zone, "assault_zone", "zone", unit) \
    X(attack_rolled, "attack_rolled", "", battle) \
    X(attrition, "attrition", "", unit | battle) \
    X(blitz_eligible, "blitz_eligible", "", unit) \
    X(blitz_from, "blitz_from", "zone", unit) \
    X(blitz_pairing_done, "blitz_pairing_done", "", battle) \
    X(blitz_to, "blitz_to", "zone", unit) \
    X(blitz_with, "blitz_with", "unit", unit) \
    X(bomb_damage, "bomb_damage", "", battle) \
    X(bombing_reduction, "bombing_reduction", "facility", nation) \
    X(bombing_reduction_turn, "bombing_reduction_turn", "facility", nation) \
    X(border, "border", "zone", facility | project) \
    X(capture_done, "capture_done", "", battle) \
    X(captured_max_damage, "captured_max_damage", "", facility) \
    X(captured_port_pending, "captured_port_pending", "nation", unit) \
    X(carpet_return_started, "carpet_return_started", "", battle) \
    X(casualty_dispute_decided, "casualty_dispute_decided", "", battle) \
    X(chinese_truce_termination, "chinese_truce_termination", "", battle) \
    X(city_bombing_reduction, "city_bombing_reduction", "zone", nation) \
    X(city_bombing_reduction_turn, "city_bombing_reduction_turn", "zone", nation) \
    X(city_damage, "city_damage", "", territory) \
    X(city_destroyed, "city_destroyed", "", territory) \
    X(city_ipp_lost, "city_ipp_lost", "", territory) \
    X(civil_war_eliminated, "civil_war_eliminated", "", nation) \
    X(coastal_fire_turn, "coastal_fire_turn", "", facility) \
    X(coastal_shots_used, "coastal_shots_used", "", facility) \
    X(combat, "combat", "", nowhere) \
    X(combat_move, "combat_move", "", unit) \
    X(completed, "completed", "", project) \
    X(controller_unresolved, "controller_unresolved", "", nation) \
    X(crossed_enemy_fortification, "crossed_enemy_fortification", "", unit) \
    X(crossing_used, "crossing_used", "crossing", game) \
    X(damage, "damage", "", project) \
    X(direct_axis_control_after_japan_surrender, "direct_axis_control_after_japan_surrender", "", nation) \
    X(economy_last_paid_turn, "economy_last_paid_turn", "", project) \
    X(economy_militia_placed, "economy_militia_placed", "zone", nation) \
    X(economy_militia_upgrades, "economy_militia_upgrades", "", nation) \
    X(economy_production_cap, "economy_production_cap", "facility", nation) \
    X(economy_purchased, "economy_purchased", "", project) \
    X(economy_repair_cap, "economy_repair_cap", "facility", nation) \
    X(economy_repairs_finished, "economy_repairs_finished", "", nation) \
    X(economy_research_capacity, "economy_research_capacity", "", nation) \
    X(economy_research_finished, "economy_research_finished", "", nation) \
    X(economy_research_used, "economy_research_used", "", nation) \
    X(economy_researched_round, "economy_researched_round", "technology", nation) \
    X(economy_sequence, "economy_sequence", "", game) \
    X(economy_start_damage, "economy_start_damage", "facility", nation) \
    X(economy_start_type, "economy_start_type", "facility:type", nation) \
    X(economy_used, "economy_used", "facility", nation) \
    X(escort, "escort", "", nowhere) \
    X(evolution_pending, "evolution_pending", "nation", game) \
    X(evolved_during_own_turn, "evolved_during_own_turn", "", nation) \
    X(evolved_turn_serial, "evolved_turn_serial", "", nation) \
    X(facility_upgrade, "facility_upgrade", "", project) \
    X(finished, "finished", "", battle) \
    X(first_allies_major_war_declared, "first_allies_major_war_declared", "", nation) \
    X(fixture, "fixture", "name", nowhere) \
    X(foreign_consent, "foreign_consent", "nation", project) \
    X(from_attack_naval_transport, "from_attack_naval_transport", "", unit) \
    X(ignore_fortification, "ignore_fortification", "", battle) \
    X(immediate, "immediate", "", battle) \
    X(immediate_land_battles, "immediate_land_battles", "", game) \
    X(immediate_naval_battles, "immediate_naval_battles", "", game) \
    X(in_port, "in_port", "facility", unit) \
    X(incorporated, "incorporated", "", nation) \
    X(influence_attempted, "influence_attempted", "", nation) \
    X(japanese_surprise_attack, "japanese_surprise_attack", "", battle) \
    X(land_battle_sequence, "land_battle_sequence", "", game) \
    X(land_decision_sequence, "land_decision_sequence", "", game) \
    X(land_retreating, "land_retreating", "", unit) \
    X(land_roll_sequence, "land_roll_sequence", "", game) \
    X(last_possession_change_turn, "last_possession_change_turn", "", territory) \
    X(launched_from_carrier, "launched_from_carrier", "", unit) \
    X(lease_available_after_turns, "lease_available_after_turns", "", project) \
    X(lease_declared, "lease_declared", "nation", nation) \
    X(lease_delivered, "lease_delivered", "nation", nation) \
    X(lease_militia_upgrade, "lease_militia_upgrade", "", project) \
    X(lease_received, "lease_received", "", project) \
    X(lease_repair, "lease_repair", "", project) \
    X(lease_repair_target, "lease_repair_target", "repair target", project) \
    X(lease_repair_wait, "lease_repair_wait", "repair target", nation) \
    X(lease_sender, "lease_sender", "nation", project) \
    X(lease_wait_controller, "lease_wait_controller", "nation", project) \
    X(lend_to, "lend_to", "nation", project) \
    X(logistics_damaged_turn, "logistics_damaged_turn", "facility or railroad", game) \
    X(logistics_last_turn_start, "logistics_last_turn_start", "", nation) \
    X(logistics_rail_created_turn, "logistics_rail_created_turn", "railroad", game) \
    X(logistics_start_damaged, "logistics_start_damaged", "facility", game) \
    X(map_declined_combat, "map_declined_combat", "", unit) \
    X(map_range, "map_range", "", unit) \
    X(maritime_air_patrol, "maritime_air_patrol", "", unit) \
    X(moved_this_turn, "moved_this_turn", "", facility) \
    X(must_withdraw_from_chinese_gift, "must_withdraw_from_chinese_gift", "", unit) \
    X(national_objective_award, "national_objective_award", "", project) \
    X(naval_battle, "naval_battle", "", battle) \
    X(naval_battle_sequence, "naval_battle_sequence", "", game) \
    X(naval_berthing, "naval_berthing", "", game) \
    X(naval_casualty_dispute_decided, "naval_casualty_dispute_decided", "", battle) \
    X(naval_combat, "naval_combat", "", unit) \
    X(naval_combat_turn, "naval_combat_turn", "", unit) \
    X(naval_combat_unloaded, "naval_combat_unloaded", "", unit) \
    X(naval_decision_sequence, "naval_decision_sequence", "", game) \
    X(naval_escort, "naval_escort", "", nowhere) \
    X(naval_last_origin, "naval_last_origin", "zone", unit) \
    X(naval_loaded_completed_turns, "naval_loaded_completed_turns", "", unit) \
    X(naval_move_decisions, "naval_move_decisions", "", game) \
    X(naval_move_sequence, "naval_move_sequence", "", game) \
    X(naval_movement_immediate, "naval_movement_immediate", "", battle) \
    X(naval_movement_plan, "naval_movement_plan", "", battle) \
    X(naval_movement_spent, "naval_movement_spent", "", unit) \
    X(naval_operation_decision_sequence, "naval_operation_decision_sequence", "", game) \
    X(naval_raider, "naval_raider", "", nowhere) \
    X(naval_retreated, "naval_retreated", "", unit) \
    X(naval_roll_sequence, "naval_roll_sequence", "", game) \
    X(naval_scramble_origin, "naval_scramble_origin", "facility", unit) \
    X(naval_scramble_turn, "naval_scramble_turn", "", facility) \
    X(naval_scramble_used, "naval_scramble_used", "", facility) \
    X(naval_scrambled, "naval_scrambled", "", nowhere) \
    X(naval_screening_continuing, "naval_screening_continuing", "", unit) \
    X(naval_start_sea, "naval_start_sea", "zone", unit) \
    X(naval_strategic_destination, "naval_strategic_destination", "facility", unit) \
    X(naval_strategic_moved, "naval_strategic_moved", "", unit) \
    X(naval_unloaded, "naval_unloaded", "", unit) \
    X(newly_placed, "newly_placed", "", nowhere) \
    X(objective_evolution, "objective_evolution", "", nation) \
    X(objective_one_china, "objective_one_china", "", nation) \
    X(on_map, "on_map", "", unit) \
    X(one_china_bonus_awarded, "one_china_bonus_awarded", "", nation) \
    X(one_china_bonus_eligible_at_surrender, "one_china_bonus_eligible_at_surrender", "", nation) \
    X(original_owner, "original_owner", "nation", facility) \
    X(original_type, "original_type", "type", facility) \
    X(payment, "payment", "payment number", project) \
    X(placed_this_turn, "placed_this_turn", "", unit | facility) \
    X(politics_combat_finished, "politics_combat_finished", "", nation) \
    X(politics_sequence, "politics_sequence", "", game) \
    X(port_aa_done, "port_aa_done", "", battle) \
    X(port_crew_prepared, "port_crew_prepared", "", battle) \
    X(port_unloaded_round, "port_unloaded_round", "", unit) \
    X(possessed_land_ipp, "possessed_land_ipp", "", nation) \
    X(price, "price", "price method", project) \
    X(purchased, "purchased", "row or cap group", nation) \
    X(raider, "raider", "", unit) \
    X(rail_build_permission, "rail_build_permission", "nation:zone:zone", nation) \
    X(rail_declined, "rail_declined", "project", nation) \
    X(rail_permission, "rail_permission", "nation", nation) \
    X(rail_used, "rail_used", "player:region", nation) \
    X(recruitment_attempted, "recruitment_attempted", "", nation) \
    X(repair, "repair", "", unit) \
    X(repair_at, "repair_at", "facility", unit) \
    X(repairing, "repairing", "", unit) \
    X(researched_this_turn, "researched_this_turn", "", facility) \
    X(retreated, "retreated", "", unit) \
    X(rocket_launched, "rocket_launched", "", unit) \
    X(rocket_mission, "rocket_mission", "", battle) \
    X(row, "row", "build-chart row", project) \
    X(scrambled, "scrambled", "", unit) \
    X(ship_crew, "ship_crew", "unit", unit) \
    X(shore_bombardment, "shore_bombardment", "", unit) \
    X(shore_dispute_decided, "shore_dispute_decided", "", battle) \
    X(shore_resolved, "shore_resolved", "", battle) \
    X(skeleton_crew, "skeleton_crew", "", nowhere) \
    X(skeleton_crew_until_own_turn, "skeleton_crew_until_own_turn", "", unit) \
    X(slip_attempted, "slip_attempted", "", battle) \
    X(stages_paid, "stages_paid", "", project) \
    X(stages_total, "stages_total", "", project) \
    X(stranded_aircraft_lost, "stranded_aircraft_lost", "", game) \
    X(strategic_moved, "strategic_moved", "", unit) \
    X(strategic_naval_movement_in_progress, "strategic_naval_movement_in_progress", "", nowhere) \
    X(strategic_naval_used, "strategic_naval_used", "", nation) \
    X(submerged, "submerged", "", unit) \
    X(surprise_attack_available, "surprise_attack_available", "", nation) \
    X(surprise_attack_linked_land, "surprise_attack_linked_land", "zone", nation) \
    X(surprise_attack_naval_sea, "surprise_attack_naval_sea", "zone", nation) \
    X(surprise_attack_target, "surprise_attack_target", "nation", nation) \
    X(surprise_attack_used, "surprise_attack_used", "", nation) \
    X(surprise_attack_zone, "surprise_attack_zone", "zone", nation) \
    X(surrendered, "surrendered", "", nation) \
    X(target, "target", "repair target", project) \
    X(towed_by, "towed_by", "unit", unit) \
    X(towing, "towing", "unit", unit) \
    X(transport_unloaded, "transport_unloaded", "", unit) \
    X(truce_low_morale_eliminates, "truce_low_morale_eliminates", "", battle) \
    X(uncontested, "uncontested", "", battle) \
    X(under_construction, "under_construction", "", nowhere) \
    X(unit_upgrade, "unit_upgrade", "", project) \
    X(unloaded_combat, "unloaded_combat", "", unit) \
    X(unloaded_noncombat, "unloaded_noncombat", "", nowhere) \
    X(upgraded_this_turn, "upgraded_this_turn", "", facility)

// The bases whose argument follows an underscore instead of a colon.
#define GWRL_MARKS_JOINED_BY_UNDERSCORE(X) X(evolution_pending)

// The kinds of thing a mark can be on, as bits.
enum class MarkPlace : std::uint8_t {
    unit = 1 << 0,
    nation = 1 << 1,
    territory = 1 << 2,
    facility = 1 << 3,
    project = 1 << 4,
    battle = 1 << 5,
    game = 1 << 6,
};
inline constexpr std::pair<MarkPlace, std::string_view> markPlaceNames[] = {
    {MarkPlace::unit, "unit"},         {MarkPlace::nation, "nation"},   {MarkPlace::territory, "territory"},
    {MarkPlace::facility, "facility"}, {MarkPlace::project, "project"}, {MarkPlace::battle, "battle"},
    {MarkPlace::game, "game"}};

namespace mark_table {
// The table's fourth column names the kinds with these bits.
enum : std::uint8_t {
    nowhere = 0,
    unit = static_cast<std::uint8_t>(MarkPlace::unit),
    nation = static_cast<std::uint8_t>(MarkPlace::nation),
    territory = static_cast<std::uint8_t>(MarkPlace::territory),
    facility = static_cast<std::uint8_t>(MarkPlace::facility),
    project = static_cast<std::uint8_t>(MarkPlace::project),
    battle = static_cast<std::uint8_t>(MarkPlace::battle),
    game = static_cast<std::uint8_t>(MarkPlace::game),
};
struct Row {
    std::string_view name;
    std::string_view argument;
    std::uint8_t places;
};
inline constexpr Row rows[] = {
#define GWRL_ROW(identifier, name, argument, places) Row {name, argument, static_cast<std::uint8_t>(places)},
    GWRL_MARKS(GWRL_ROW)
#undef GWRL_ROW
};
inline constexpr std::size_t count = std::size(rows);
enum class Index : MarkKind::Rep {
#define GWRL_ROW(identifier, name, argument, places) identifier,
    GWRL_MARKS(GWRL_ROW)
#undef GWRL_ROW
};
inline constexpr std::string_view joinedByUnderscore[] = {
#define GWRL_ROW(identifier) #identifier,
    GWRL_MARKS_JOINED_BY_UNDERSCORE(GWRL_ROW)
#undef GWRL_ROW
};
constexpr char separator(std::size_t index) {
    for (const auto name : joinedByUnderscore)
        if (rows[index].name == name) return '_';
    return ':';
}
constexpr bool sorted() {
    for (std::size_t at = 1; at < count; ++at)
        if (!(rows[at - 1].name < rows[at].name)) return false;
    return true;
}
// A mark with an argument is written base, separator, argument. Number order
// is name order only if no other base continues this base's name with a
// character at or below the separator: "a:x" then sorts before "a_b", as
// number a sorts before number a_b. Sorted order puts such bases right after.
constexpr bool argumentsKeepNameOrder() {
    for (std::size_t at = 0; at < count; ++at) {
        if (rows[at].argument.empty()) continue;
        const auto& base = rows[at].name;
        for (std::size_t next = at + 1; next < count && rows[next].name.starts_with(base); ++next)
            if (static_cast<unsigned char>(rows[next].name[base.size()]) <= static_cast<unsigned char>(separator(at)))
                return false;
    }
    return true;
}
constexpr bool joinedBasesTakeArguments() {
    for (const auto name : joinedByUnderscore) {
        bool found = false;
        for (const auto& row : rows) found = found || (row.name == name && !row.argument.empty());
        if (!found) return false;
    }
    return true;
}
static_assert(count <= MarkKind::capacity, "More marks than MarkKind holds");
static_assert(sorted(), "GWRL_MARKS must list the marks in bytewise name order, the order of their numbers");
static_assert(argumentsKeepNameOrder(), "A mark's argument would sort it away from its number's place");
static_assert(joinedBasesTakeArguments(), "A base joined by an underscore must be a mark with an argument");
}  // namespace mark_table

// mark::placed_this_turn and so on: each base's number.
namespace mark {
#define GWRL_ROW(identifier, name, argument, places) \
    inline constexpr MarkId identifier = MarkId::fromIndex(static_cast<std::size_t>(mark_table::Index::identifier));
GWRL_MARKS(GWRL_ROW)
#undef GWRL_ROW
}  // namespace mark

// A base's name, what its argument names ("" for none) and the character
// between them.
inline std::string_view markName(MarkId base) {
    if (!base.valid() || base.index() >= mark_table::count) throw std::runtime_error("A mark number names no mark");
    return mark_table::rows[base.index()].name;
}
inline std::string_view markArgument(MarkId base) {
    markName(base);
    return mark_table::rows[base.index()].argument;
}
inline bool markTakesArgument(MarkId base) { return !markArgument(base).empty(); }
// Whether the rules put this mark on that kind of thing (the table's fourth column).
inline bool markOn(MarkId base, MarkPlace place) {
    markName(base);
    return (mark_table::rows[base.index()].places & static_cast<std::uint8_t>(place)) != 0;
}
inline char markSeparator(MarkId base) {
    markName(base);
    return mark_table::separator(base.index());
}
// A base's number by name, or nothing for a name that is no mark's base.
inline std::optional<MarkId> findMark(std::string_view base) {
    const auto* first = std::begin(mark_table::rows);
    const auto* last = std::end(mark_table::rows);
    const auto* found = std::lower_bound(first, last, base, [](const mark_table::Row& row, std::string_view name) {
        return row.name < name;
    });
    if (found == last || found->name != base) return std::nullopt;
    return MarkId::fromIndex(static_cast<std::size_t>(found - first));
}
inline MarkId markNumber(std::string_view base) {
    if (const auto found = findMark(base)) return *found;
    throw std::runtime_error("Unknown mark: " + std::string(base));
}
// Every base's name, in number order.
inline std::vector<std::string> markNames() {
    std::vector<std::string> names;
    for (const auto& row : mark_table::rows) names.emplace_back(row.name);
    return names;
}

// A mark to look up or set: its base and, if it has one, its argument. The key
// refers to its argument's text, so that text must outlive the key; a key
// cannot be made from a temporary string. Keys order as the marks' names do.
class MarkKey {
  public:
    constexpr MarkKey(MarkId base) : base_(base) {}  // A mark without an argument.
    constexpr MarkKey(MarkId base, std::string_view argument)
        : base_(base), argument_(argument), hasArgument_(true) {}
    template <std::size_t N>
    constexpr MarkKey(MarkId base, const char (&argument)[N]) : MarkKey(base, std::string_view(argument)) {}
    MarkKey(MarkId, std::string&&) = delete;
    MarkKey(MarkId, const std::string&&) = delete;

    constexpr MarkId base() const { return base_; }
    constexpr bool hasArgument() const { return hasArgument_; }
    constexpr std::string_view argument() const { return argument_; }
    // The mark's name, as saved positions write it.
    std::string name() const {
        std::string out(markName(base_));
        if (hasArgument_) {
            out += markSeparator(base_);
            out += argument_;
        }
        return out;
    }

    friend constexpr bool operator==(const MarkKey& a, const MarkKey& b) {
        return a.base_ == b.base_ && a.hasArgument_ == b.hasArgument_ && a.argument_ == b.argument_;
    }
    friend constexpr std::strong_ordering operator<=>(const MarkKey& a, const MarkKey& b) {
        if (const auto order = a.base_ <=> b.base_; order != 0) return order;
        if (const auto order = a.hasArgument_ <=> b.hasArgument_; order != 0) return order;
        return a.argument_.compare(b.argument_) <=> 0;
    }

  private:
    MarkId base_;
    std::string_view argument_;
    bool hasArgument_ {false};
};

// A mark read from its name, such as "naval_last_origin:sea_p15"; the key
// refers into the name. Nothing for a name the table lacks or whose argument
// does not fit its base, such as a catalog predicate that is no mark.
inline std::optional<MarkKey> findMarkKey(std::string_view name) {
    if (const auto colon = name.find(':'); colon != std::string_view::npos) {
        const auto base = findMark(name.substr(0, colon));
        if (base && markTakesArgument(*base) && markSeparator(*base) == ':')
            return MarkKey(*base, name.substr(colon + 1));
    } else if (const auto base = findMark(name)) {
        if (!markTakesArgument(*base)) return MarkKey(*base);
    } else {
        for (const auto joined : mark_table::joinedByUnderscore)
            if (name.size() > joined.size() && name.starts_with(joined) && name[joined.size()] == '_')
                return MarkKey(markNumber(joined), name.substr(joined.size() + 1));
    }
    return std::nullopt;
}
// The same, throwing "Unknown mark: <name>" for such a name.
inline MarkKey parseMark(std::string_view name) {
    if (const auto key = findMarkKey(name)) return *key;
    throw std::runtime_error("Unknown mark: " + std::string(name));
}

// The marks noted on one thing, each with its value, listed in the order of
// their names. It offers the parts of std::map's interface the rules use: an
// entry shows as {first: key, second: value}. The keys' arguments live in one
// buffer, so an entry's key is valid until the set changes.
class Marks {
    struct Slot {
        MarkId base;
        bool hasArgument {false};
        std::uint32_t offset {0};
        std::uint32_t length {0};
        int value {0};
    };

  public:
    using size_type = std::size_t;
    struct Entry {
        MarkKey first;
        int second;
    };
    struct MutableEntry {
        MarkKey first;
        int& second;
    };

    template <bool Const>
    class Iterator {
        using Owner = std::conditional_t<Const, const Marks, Marks>;
        using Shown = std::conditional_t<Const, Entry, MutableEntry>;

      public:
        using iterator_category = std::forward_iterator_tag;
        using value_type = Entry;
        using difference_type = std::ptrdiff_t;
        using reference = Shown;
        struct pointer {
            Shown shown;
            const Shown* operator->() const { return &shown; }
        };

        Iterator() = default;
        Iterator(Owner* owner, std::size_t at) : owner_(owner), at_(at) {}
        operator Iterator<true>() const { return Iterator<true>(owner_, at_); }

        Shown operator*() const {
            auto& slot = owner_->slots_[at_];
            return Shown {owner_->keyOf(slot), slot.value};
        }
        pointer operator->() const { return pointer {**this}; }
        Iterator& operator++() {
            ++at_;
            return *this;
        }
        Iterator operator++(int) {
            auto old = *this;
            ++at_;
            return old;
        }
        friend bool operator==(const Iterator& a, const Iterator& b) { return a.at_ == b.at_; }

      private:
        friend class Marks;
        Owner* owner_ {nullptr};
        std::size_t at_ {0};
    };
    using iterator = Iterator<false>;
    using const_iterator = Iterator<true>;

    Marks() = default;
    Marks(std::initializer_list<std::pair<MarkKey, int>> entries) {
        for (const auto& [key, value] : entries) (*this)[key] = value;
    }

    iterator begin() { return iterator(this, 0); }
    iterator end() { return iterator(this, slots_.size()); }
    const_iterator begin() const { return const_iterator(this, 0); }
    const_iterator end() const { return const_iterator(this, slots_.size()); }
    size_type size() const { return slots_.size(); }
    bool empty() const { return slots_.empty(); }
    void clear() {
        slots_.clear();
        text_.clear();
        garbage_ = 0;
    }

    iterator find(const MarkKey& key) {
        const auto at = lowerBound(key);
        return at < slots_.size() && keyOf(slots_[at]) == key ? iterator(this, at) : end();
    }
    const_iterator find(const MarkKey& key) const {
        const auto at = lowerBound(key);
        return at < slots_.size() && keyOf(slots_[at]) == key ? const_iterator(this, at) : end();
    }
    bool contains(const MarkKey& key) const { return find(key) != end(); }
    size_type count(const MarkKey& key) const { return contains(key) ? 1 : 0; }
    // The mark's value, 0 if it is absent.
    int value(const MarkKey& key) const {
        const auto found = find(key);
        return found == end() ? 0 : found->second;
    }
    int at(const MarkKey& key) const {
        const auto found = find(key);
        if (found == end()) throw std::out_of_range("Marks::at: no mark " + key.name());
        return found->second;
    }
    // The mark's value, added as 0 if it is absent. The reference is valid
    // until the set gains or loses a mark.
    int& operator[](const MarkKey& key) {
        const auto at = lowerBound(key);
        if (at < slots_.size() && keyOf(slots_[at]) == key) return slots_[at].value;
        if (markTakesArgument(key.base()) != key.hasArgument())
            throw std::logic_error("Mark " + key.name() + (key.hasArgument() ? " takes no argument" : " needs an argument"));
        Slot slot {key.base(), key.hasArgument(), static_cast<std::uint32_t>(text_.size()),
                   static_cast<std::uint32_t>(key.argument().size()), 0};
        const auto argument = key.argument();
        if (!argument.empty() && argument.data() >= text_.data() && argument.data() < text_.data() + text_.size())
            text_.append(std::string(argument));  // A key read from this set: its text may move as the buffer grows.
        else
            text_.append(argument);
        return slots_.insert(slots_.begin() + static_cast<std::ptrdiff_t>(at), slot)->value;
    }
    iterator erase(const_iterator position) {
        const auto at = position.at_;
        garbage_ += slots_[at].length;
        slots_.erase(slots_.begin() + static_cast<std::ptrdiff_t>(at));
        compactIfWasteful();
        return iterator(this, at);
    }
    iterator erase(iterator position) { return erase(const_iterator(position)); }
    size_type erase(const MarkKey& key) {
        const auto found = find(key);
        if (found == end()) return 0;
        erase(found);
        return 1;
    }

    // The argument of the first mark of this base, in name order, whose value
    // is not 0 and whose argument starts with `prefix`, without the prefix.
    std::optional<std::string> argumentAfter(MarkId base, std::string_view prefix = {}) const {
        for (auto at = lowerBound(MarkKey(base)); at < slots_.size() && slots_[at].base == base; ++at) {
            const auto argument = argumentOf(slots_[at]);
            if (slots_[at].value != 0 && slots_[at].hasArgument && argument.starts_with(prefix))
                return std::string(argument.substr(prefix.size()));
        }
        return std::nullopt;
    }

    friend bool operator==(const Marks& a, const Marks& b) {
        if (a.size() != b.size()) return false;
        for (std::size_t at = 0; at < a.slots_.size(); ++at)
            if (a.slots_[at].value != b.slots_[at].value || a.keyOf(a.slots_[at]) != b.keyOf(b.slots_[at])) return false;
        return true;
    }

  private:
    std::string_view argumentOf(const Slot& slot) const {
        return std::string_view(text_).substr(slot.offset, slot.length);
    }
    MarkKey keyOf(const Slot& slot) const {
        return slot.hasArgument ? MarkKey(slot.base, argumentOf(slot)) : MarkKey(slot.base);
    }
    std::size_t lowerBound(const MarkKey& key) const {
        std::size_t low = 0, high = slots_.size();
        while (low < high) {
            const auto middle = low + (high - low) / 2;
            if (keyOf(slots_[middle]) < key) low = middle + 1;
            else high = middle;
        }
        return low;
    }
    // Erased marks leave their argument's text behind; rewrite the buffer once
    // that is most of it.
    void compactIfWasteful() {
        if (garbage_ < 64 || garbage_ * 2 < text_.size()) return;
        std::size_t live = 0;
        for (const auto& slot : slots_) live += slot.length;
        std::string text;
        text.reserve(live);
        for (auto& slot : slots_) {
            const auto argument = argumentOf(slot);
            slot.offset = static_cast<std::uint32_t>(text.size());
            text.append(argument);
        }
        text_ = std::move(text);
        garbage_ = 0;
    }

    std::vector<Slot> slots_;  // In key order, which is name order.
    std::string text_;  // The arguments, back to back.
    std::size_t garbage_ {0};  // Bytes of text_ no slot uses.
};

// Marks without values: a unit's commitments, such as combat_move or
// air_battle:land_battle_9, listed in the order of their names.
class MarkSet {
  public:
    class const_iterator {
      public:
        using iterator_category = std::forward_iterator_tag;
        using value_type = MarkKey;
        using difference_type = std::ptrdiff_t;
        using reference = MarkKey;
        using pointer = void;
        const_iterator() = default;
        explicit const_iterator(Marks::const_iterator at) : at_(at) {}
        MarkKey operator*() const { return (*at_).first; }
        const_iterator& operator++() {
            ++at_;
            return *this;
        }
        const_iterator operator++(int) {
            auto old = *this;
            ++at_;
            return old;
        }
        friend bool operator==(const const_iterator& a, const const_iterator& b) { return a.at_ == b.at_; }

      private:
        Marks::const_iterator at_;
    };
    using iterator = const_iterator;

    MarkSet() = default;
    MarkSet(std::initializer_list<MarkKey> keys) {
        for (const auto& key : keys) insert(key);
    }
    const_iterator begin() const { return const_iterator(marks_.begin()); }
    const_iterator end() const { return const_iterator(marks_.end()); }
    std::size_t size() const { return marks_.size(); }
    bool empty() const { return marks_.empty(); }
    void clear() { marks_.clear(); }
    bool contains(const MarkKey& key) const { return marks_.contains(key); }
    std::size_t count(const MarkKey& key) const { return marks_.count(key); }
    // Whether the set lacked the mark.
    bool insert(const MarkKey& key) {
        if (marks_.contains(key)) return false;
        marks_[key] = 1;
        return true;
    }
    std::size_t erase(const MarkKey& key) { return marks_.erase(key); }
    // The argument of the first mark of this base whose argument starts with
    // `prefix`, without the prefix.
    std::optional<std::string> argumentAfter(MarkId base, std::string_view prefix = {}) const {
        return marks_.argumentAfter(base, prefix);
    }
    friend bool operator==(const MarkSet& a, const MarkSet& b) { return a.marks_ == b.marks_; }

  private:
    Marks marks_;
};

}  // namespace game::campaign
