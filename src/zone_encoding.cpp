#include "game/zone_encoding.hpp"

#include "game/catalog.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <cmath>
#include <functional>
#include <mutex>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <unordered_map>

namespace game::campaign {
namespace {
using V = json::Value;

// Names of flags, option kinds, decision kinds, battle stages, dice purposes,
// pending political records and battle-data fields. Collected from the engine
// source and from random games; a name missing here is counted in its list's
// "other" column and reported by zoneEncodingUnknowns, never dropped.
const std::vector<std::string> kActorFlags{
    "access_to_resources_completed", "air_allied_loaded_turn", "air_battle", "air_battle_turn", "air_combat",
    "air_defending_carrier", "air_in_flight", "air_landed_after_combat", "air_scramble_origin", "air_scramble_source",
    "air_screening_continued", "air_screening_ready", "air_screening_wait", "air_transport_unloaded",
    "airborne_assault", "amphibious_assault", "amphibious_transport", "assault_declared", "assault_zone", "attrition",
    "benchmark_destroyed_enemy_value", "benchmark_initial_budget", "benchmark_lost_value", "benchmark_purchased",
    "benchmark_unspent_budget", "blitz_eligible", "blitz_from", "blitz_to", "blitz_with", "captured_port_pending",
    "civil_war_eliminated", "combat", "combat_move", "controller_unresolved", "crossed_enemy_fortification",
    "direct_axis_control_after_japan_surrender", "economy_militia_placed", "economy_militia_upgrades",
    "economy_production_cap", "economy_repair_cap", "economy_repairs_finished", "economy_research_capacity",
    "economy_research_finished", "economy_research_used", "economy_researched_round", "economy_start_damage",
    "economy_start_type", "economy_used", "escort", "evolved_during_own_turn", "evolved_turn_serial",
    "first_allies_major_war_declared", "from_attack_naval_transport", "in_port", "incorporated",
    "influence_attempted", "land_retreating", "launched_from_carrier", "lease_declared", "lease_delivered",
    "lease_repair_wait", "logistics_last_turn_start", "map_declined_combat", "map_range", "maritime_air_patrol",
    "must_withdraw_from_chinese_gift", "naval_combat", "naval_combat_turn", "naval_combat_unloaded", "naval_escort",
    "naval_last_origin", "naval_loaded_completed_turns", "naval_movement_spent", "naval_raider", "naval_retreated",
    "naval_scramble_origin", "naval_scrambled", "naval_screening_continuing", "naval_start_sea",
    "naval_strategic_destination", "naval_strategic_moved", "naval_unloaded", "newly_placed", "objective_evolution",
    "objective_one_china", "on_map", "one_china_bonus_awarded", "one_china_bonus_eligible_at_surrender",
    "placed_this_turn", "politics_combat_finished", "port_unloaded_round", "possessed_land_ipp", "purchased",
    "raider", "rail_build_permission", "rail_declined", "rail_permission", "rail_used", "recruitment_attempted",
    "repair", "repair_at", "repairing", "retreated", "rocket_launched", "scrambled", "ship_crew", "shore_bombardment",
    "skeleton_crew", "skeleton_crew_until_own_turn", "strategic_moved", "strategic_naval_used", "submerged",
    "surprise_attack_available", "surprise_attack_linked_land", "surprise_attack_naval_sea", "surprise_attack_target",
    "surprise_attack_used", "surprise_attack_zone", "surrendered", "towed_by", "towing", "transport_unloaded",
    "unloaded_combat", "unloaded_noncombat"
};
const std::vector<std::string> kRecordFlags{
    "__campaign_started", "air_decision_sequence", "air_mission", "air_mission_sequence", "air_roll_sequence",
    "air_scramble_turn", "air_scramble_used", "air_waiting_port_evacuation", "airborne_assault", "aligned_turn",
    "amphibious_assault", "amphibious_preparation", "amphibious_sequence", "artillery_city_bombing",
    "attack_rolled", "attrition", "benchmark_battle_finished", "benchmark_composition_ready",
    "benchmark_unit_sequence", "blitz_pairing_done", "bomb_damage", "border", "capture_done", "captured_max_damage",
    "carpet_return_started", "casualty_dispute_decided", "chinese_truce_termination", "city_damage",
    "city_destroyed", "city_ipp_lost", "coastal_fire_turn", "coastal_shots_used", "completed", "crossing_used",
    "damage", "economy_last_paid_turn", "economy_purchased", "economy_sequence", "economy_start_damage",
    "evolution_pending", "facility_upgrade", "finished", "foreign_consent", "ignore_fortification", "immediate",
    "immediate_land_battles", "immediate_naval_battles", "japanese_surprise_attack", "land_battle_sequence",
    "land_decision_sequence", "land_roll_sequence", "last_possession_change_turn", "lease_available_after_turns",
    "lease_militia_upgrade", "lease_received", "lease_repair", "lease_repair_target", "lease_sender",
    "lease_wait_controller", "lend_to", "logistics_damaged_turn", "logistics_rail_created_turn",
    "logistics_start_damaged", "moved_this_turn", "movement_ends_in_owner_home_country",
    "movement_starts_in_owner_home_country", "national_objective_award", "naval_battle", "naval_battle_sequence",
    "naval_berthing", "naval_casualty_dispute_decided", "naval_decision_sequence", "naval_move_decisions",
    "naval_move_sequence", "naval_movement_immediate", "naval_movement_plan", "naval_operation_decision_sequence",
    "naval_roll_sequence", "naval_scramble_turn", "naval_scramble_used", "original_owner", "original_type",
    "owner_is_major_power", "payment", "placed_this_turn", "politics_sequence", "port_aa_done",
    "port_crew_prepared", "price", "researched_this_turn", "rocket_mission", "row", "shore_dispute_decided",
    "shore_resolved", "slip_attempted", "stages_paid", "stages_total", "starts_at_seaplane_base",
    "stranded_aircraft_lost", "strategic_naval_movement_in_progress", "surprise_attack_naval_sea",
    "surprise_attack_target", "surprise_attack_used", "surprise_attack_zone", "target", "towards",
    "truce_low_morale_eliminates", "uncontested", "under_construction", "unit_upgrade", "upgraded_this_turn"
};
const std::vector<std::string> kActionKinds{
    "air_allied_load", "air_allied_unload", "air_artillery_city_bomb", "air_assault", "air_begin_bombing",
    "air_blitz", "air_bomb", "air_choose_casualty", "air_choose_rail_border", "air_choose_technology_loss",
    "air_decline_intercept", "air_decline_scramble", "air_defend", "air_end_patrol", "air_escort",
    "air_failed_landing", "air_fly", "air_ground", "air_ground_attack", "air_intercept", "air_land",
    "air_land_noncombat", "air_load", "air_resume_bombing", "air_rocket_attack", "air_scramble",
    "air_screen_continue", "air_start_patrol", "air_support", "air_unload", "benchmark_compose_units",
    "benchmark_finish_composition", "economy_advance", "economy_approve_rail", "economy_decline_rail",
    "economy_finish_research", "economy_lease_declare", "economy_lease_deliver", "economy_lease_place",
    "economy_lease_repair", "economy_lease_upgrade", "economy_place", "economy_purchase", "economy_repair",
    "economy_request_rail", "economy_research", "end_phase", "influence_roll", "land_begin_battle",
    "land_casualty_accept", "land_casualty_dispute", "land_continue_fighting", "land_declare_attrition",
    "land_finish_blitz_pairing", "land_pair_artillery", "land_pair_blitz", "land_progress_battle",
    "land_retreat_begin", "land_retreat_unit", "land_select_surprise_zone", "land_take_casualty",
    "movement_factory_rail", "movement_grant_rail", "movement_route", "naval_air_attack", "naval_begin_assault",
    "naval_begin_battle", "naval_cancel_move", "naval_carrier_land", "naval_casualty_accept",
    "naval_casualty_dispute", "naval_continue_fighting", "naval_declare_assault", "naval_decline_evacuation",
    "naval_decline_pair", "naval_decline_scramble", "naval_designate_raider", "naval_discover_raider",
    "naval_engage_force", "naval_enter_port", "naval_entry_declare", "naval_entry_defender_declare",
    "naval_entry_neutral", "naval_entry_peaceful", "naval_evacuate_port", "naval_finish_battle",
    "naval_finish_evacuation", "naval_finish_shore_selection", "naval_force_add", "naval_force_remove",
    "naval_ignore_raider", "naval_load", "naval_pair_destroyer", "naval_patrol_attack", "naval_port_attack",
    "naval_progress_battle", "naval_raider_slip", "naval_raider_stay", "naval_reaction_decline",
    "naval_reaction_engage", "naval_remove_raider", "naval_retreat_begin", "naval_retreat_unit",
    "naval_roll_capture", "naval_route", "naval_scramble", "naval_screen_add", "naval_screen_confirm",
    "naval_screen_continue_route", "naval_screen_remove", "naval_screen_stop_route", "naval_select_bombardment",
    "naval_select_surprise_zone", "naval_shore_accept", "naval_shore_casualty", "naval_shore_dispute",
    "naval_start_move", "naval_strategic_continue", "naval_strategic_pickup", "naval_sub_decline",
    "naval_sub_protected", "naval_sub_unprotected", "naval_take_casualty", "naval_unload", "pass_interrupt",
    "politics_choose_capital", "politics_declare_war", "politics_give_capture", "politics_keep_capture",
    "politics_priority_declare", "politics_priority_decline", "politics_relocate_neutral",
    "recruitment_advance_ship", "recruitment_place_infantry", "recruitment_place_militia",
    "recruitment_repair_facility", "recruitment_roll", "truce_accept", "truce_break", "truce_decline_offer",
    "truce_offer", "truce_reject"
};
const std::vector<std::string> kDecisionKinds{
    "air_casualty", "air_destroyed_city_technology", "air_ground_or_defend", "air_interception", "air_landing",
    "air_rail_border", "air_scramble", "economy_rail_permission", "land_artillery_pairing", "land_blitz_pairing",
    "land_casualty", "land_casualty_consent", "land_retreat_destination", "land_retreat_or_continue",
    "naval_carrier_landing", "naval_casualty", "naval_casualty_consent", "naval_destroyer_pairing",
    "naval_engage_raider", "naval_entry_intent", "naval_entry_response", "naval_force_selection",
    "naval_movement_reaction", "naval_port_evacuation", "naval_raider_slip_choice", "naval_retreat_destination",
    "naval_retreat_or_continue", "naval_scramble", "naval_screening_continuation", "naval_screening_force",
    "naval_shore_casualty", "naval_shore_consent", "naval_shore_selection", "naval_strategic_pickup",
    "naval_submarine_participation", "politics_chinese_liberation", "politics_declaration_priority",
    "politics_evolution", "politics_neutral_relocation", "recruitment_choice", "truce_offer_decision",
    "truce_response_decision"
};
const std::vector<std::string> kBattleStages{
    "air_declared", "air_fire", "air_resolving", "airborne_drop", "amphibious_declared",
    "amphibious_shore_casualties", "amphibious_shore_roll", "amphibious_shore_selection", "artillery_done",
    "attacker_fire", "attrition_fire", "awaiting_air_defence", "awaiting_combat_rules", "choose_hits",
    "city_airborne_aaa", "damage", "defender_fire", "facility_aa", "finished", "first_strike",
    "interception_choices", "interception_return", "interception_roll", "landing", "naval_aftermath",
    "naval_air_defence", "naval_air_superiority", "naval_attacker_fire", "naval_choose_hits", "naval_complete",
    "naval_declared", "naval_defender_fire", "naval_first_strike", "naval_force_selection", "naval_moving",
    "naval_pairing", "naval_raider_discovery", "naval_retreat", "naval_retreat_assign", "naval_round_end",
    "naval_scrambling", "naval_screen_selection", "naval_submarine_choices", "pair_attack", "pair_defense",
    "post_capture", "retreat", "retreat_air", "retreat_assign", "rocket_aa", "rocket_consumed", "round_end"
};
const std::vector<std::string> kChancePurposes{
    "air_bomb_damage", "air_facility_aa", "air_interception_roll", "air_rocket_aa", "economy_research",
    "influence_roll", "land_casualty_dispute", "land_combat_roll", "naval_casualty_dispute", "naval_combat_roll",
    "naval_movement_slip", "naval_port_aa", "naval_port_capture", "naval_raider_discovery", "naval_shore_dispute",
    "naval_shore_roll", "politics_surrender_queues", "recruitment_roll", "warlord_alignment"
};
const std::vector<std::string> kPendingNames{
    "dadao_attacked_by", "economy_rail_permission", "influence_roll", "last_conqueror", "politics_chinese_liberation", "politics_declaration_priority", "politics_evolution",
    "recruitment_choice", "recruitment_roll", "truce_foreign_declaration", "warlord_alignment",
    "warlord_combat_resolution", "warlord_defense_player"
};
const std::vector<std::string> kBattleDataKeys{
    "after_hits", "after_pairing", "after_roll", "air_after_landing", "air_defence_choices", "air_defence_ready",
    "air_hit_queue", "air_interception_choices", "air_landing_done", "air_landing_queue", "air_pending_dead",
    "air_screening_continuing", "air_shots", "air_stage", "airborne_drop_ready", "airborne_return_fire",
    "amphibious_sea", "amphibious_waiting", "attack_pairs", "blitz_pairs", "bombarding", "cargo",
    "carpet_return_done", "casualty_consents", "casualty_proposal", "context", "continuing", "cursor", "declined",
    "defenders", "defense_pairs", "disputing_nations", "entry_compelled", "entry_nation", "entry_processed",
    "entry_zone", "evacuated", "evacuation_selection_complete", "exited_aircraft", "facility", "forced_retreat",
    "grounded", "hit_index", "hits", "kind", "land_entry_origins", "map_attack", "naval_after_roll",
    "naval_attacker_shots", "naval_carrier_landing_queue", "naval_casualty_consents", "naval_casualty_proposal",
    "naval_destroyer_pairs", "naval_discovering_raider", "naval_disputing_nations", "naval_entry_origins",
    "naval_excluded", "naval_hit_index", "naval_hits", "naval_immediate_hits", "naval_movement", "naval_pairing_done",
    "naval_pending_dead", "naval_protected_submarines", "naval_raider_choices", "naval_round_shots",
    "naval_scramble_choices", "naval_shots", "naval_submarine_choices", "no_scramble", "one_round", "origins",
    "pair_after", "pending_dead", "port_evacuation", "reaction_context", "reaction_units", "request", "result",
    "retreated_units", "rolling_phase", "round", "scramble_origins", "scramble_sources", "screening", "sea",
    "selected", "shore_consents", "shore_disputing_nations", "shore_hit_index", "shore_hits", "shore_proposal",
    "shore_shots", "shots", "submarines_initiated", "target", "target_kind", "truce_breaker", "waiting_ports"
};

// Battle notes whose values can be words rather than units, zones or numbers:
// a battle's next step, its situation, its result, a bombing target, the side
// or unit classes a hit may take, nations and players.
const std::vector<std::string> kBattleWordKeys{
    "after_hits", "after_pairing", "after_roll", "air_after_landing", "air_hit_queue", "air_shots", "air_stage",
    "casualty_consents", "context", "disputing_nations", "entry_compelled", "entry_nation", "hits", "kind",
    "naval_after_roll", "naval_attacker_shots", "naval_casualty_consents", "naval_disputing_nations", "naval_hits",
    "naval_immediate_hits", "naval_movement", "naval_shots", "pair_after", "reaction_context", "result",
    "rolling_phase", "shore_consents", "shore_disputing_nations", "shore_hits", "shore_shots", "shots", "target_kind",
    "truce_breaker"
};
// Words such notes use besides battle stages, unit classes, nations and players.
const std::vector<std::string> kBattleWords{
    "attacker", "attacker_wins", "attrition_complete", "carpet_round_end", "city", "construction", "defender",
    "defender_wins", "drop", "facility", "finish", "forced_retreat", "movement_map", "movement_submarines",
    "mutual_destruction", "one_round", "port_attack", "rail", "retreated", "screening", "stalemate", "standard"
};

const std::vector<std::string> kPhases{"combat", "combat_movement", "non_combat_movement", "place_units", "production"};
const std::vector<std::string> kScheduleKinds{"interrupt", "pass_interrupt", "play"};
const std::vector<std::string> kUnitClasses{"aircraft", "land", "naval"};
const std::vector<std::string> kPowerStatuses{"major", "minor", "warlord"};
const std::vector<std::string> kIncomeComponents{"china_control_bonus", "territorial"};
const std::vector<std::string> kEnumValues{
    "blitz", "city", "construction", "facility", "improved_construction_combine", "improved_construction_discount",
    "local", "narrow_crossing", "ordinary", "printed", "rail", "strategic_rail", "strategic_river"
};
const std::vector<std::string> kParameterKeys{
    "actor", "air_only", "air_priority", "aircraft", "armor", "artillery", "attacker", "attacking", "authority",
    "battle", "beneficiary", "bombarding", "border", "border2", "cargo", "carriers", "ccp_neighbor", "combat",
    "companion", "context", "dadao_neighbor", "damage", "declaring_nation", "declined", "declined_rail_requests", "defenders",
    "destination", "destination_facility", "eligible", "endpoint", "evacuated", "evacuation_selection_complete",
    "facility", "factory", "id", "in_port", "kind", "land_entry_origins", "land_only", "low_morale", "map_attack",
    "mode", "moved", "nation", "neighbor", "origin", "origin_facility", "origins", "owner", "path", "plan",
    "port_evacuation", "price", "project", "raiders", "range", "reason", "recipient", "relocation", "request",
    "requester", "requires_withdrawal", "round", "row", "rule", "schema", "sea", "selected", "sender", "ships",
    "source", "spend", "strategic", "submarines_initiated", "target", "target_classes", "targeted", "technology",
    "threshold", "towed", "transport", "truce_breaker", "truce_eligible", "type", "unit", "unit_destruction",
    "units", "unload", "victim_attacker", "visited_configurations", "warlord", "zone", "zones"};
const std::vector<std::string> kRoleGroups{"source", "path", "target", "other"};
const std::vector<std::string> kRepairTargets{"city", "construction", "facility", "rail", "unit"};
const std::vector<std::string> kRepairStats{"count", "remaining_cost", "remaining_damage", "restricts_action"};
const std::vector<std::string> kFacilityStats{"count", "damage", "damaged"};
const std::vector<std::string> kProjectClasses{"facility", "unit"};
const std::vector<std::string> kProjectStats{"count", "paid_ipp", "queue_position", "remaining_payments", "payments_left"};
const std::vector<std::string> kChanceStats{"dice", "modifier", "rerolls", "sides"};
// Counted for every unit by (alliance of its nation, unit type). The flags here
// change what a unit may do this turn; every other flag is counted by unit class.
const std::vector<std::string> kUnitBaseStats{"count", "move_0", "move_1", "move_2", "move_3", "move_4", "move_5",
                                              "move_6", "move_7", "moved", "damaged", "aboard", "carrying", "route",
                                              "origin_elsewhere", "attacker", "defender"};
const std::vector<std::string> kTopUnitFlags{
    "air_battle", "air_combat", "air_in_flight", "air_landed_after_combat", "air_screening_ready",
    "air_screening_wait", "air_transport_unloaded", "airborne_assault", "amphibious_assault", "amphibious_transport",
    "assault_declared", "assault_zone", "attrition", "blitz_eligible", "blitz_from", "blitz_to", "blitz_with",
    "captured_port_pending", "combat", "combat_move", "crossed_enemy_fortification", "escort",
    "from_attack_naval_transport", "in_port", "land_retreating", "launched_from_carrier", "map_range",
    "maritime_air_patrol", "must_withdraw_from_chinese_gift", "naval_combat", "naval_combat_unloaded", "naval_escort",
    "naval_loaded_completed_turns", "naval_movement_spent", "naval_raider", "naval_retreated", "naval_scrambled",
    "naval_strategic_moved", "naval_unloaded", "newly_placed", "on_map", "placed_this_turn", "raider", "repair",
    "retreated", "rocket_launched", "scrambled", "shore_bombardment", "skeleton_crew", "skeleton_crew_until_own_turn",
    "strategic_moved", "submerged", "towed_by", "towing", "transport_unloaded", "unloaded_combat",
    "unloaded_noncombat"};
// Unit flags whose argument names a place; the unit is also counted there.
const std::vector<std::string> kRefKinds{
    "air_battle", "air_defending_carrier", "air_scramble_origin", "air_scramble_source", "amphibious_transport",
    "assault_zone", "blitz_from", "blitz_to", "blitz_with", "captured_port_pending", "in_port", "naval_last_origin",
    "naval_scramble_origin", "naval_start_sea", "naval_strategic_destination", "repair_at", "route", "ship_crew",
    "surprise_attack_naval_sea", "surprise_attack_target", "surprise_attack_zone", "towed_by", "towing",
    "turn_origin"};

std::mutex unknownMutex;
std::map<std::string, long> unknownNames;

void noteUnknown(const std::string& family, const std::string& name) {
    const std::lock_guard lock(unknownMutex);
    ++unknownNames[family + ":" + name];
}

class Vocabulary {
  public:
    Vocabulary() = default;
    Vocabulary(std::string family, std::vector<std::string> values, bool other, bool sorted = true)
        : family_(std::move(family)) {
        if (sorted) {
            std::sort(values.begin(), values.end());
            values.erase(std::unique(values.begin(), values.end()), values.end());
        }
        names_ = values;
        if (other) {
            names_.push_back("other");
            other_ = static_cast<int>(names_.size()) - 1;
        }
        for (int i = 0; i < static_cast<int>(values.size()); ++i) index_.emplace(values[i], i);
    }
    int size() const { return static_cast<int>(names_.size()); }
    int other() const { return other_; }
    const std::vector<std::string>& names() const { return names_; }
    int find(const std::string& name) const {
        const auto found = index_.find(name);
        return found == index_.end() ? -1 : found->second;
    }
    // The column for a name; unknown names go to "other" and are reported.
    int operator()(const std::string& name) const {
        if (const int index = find(name); index >= 0) return index;
        if (other_ < 0) throw std::logic_error("Zone encoding has no " + family_ + " named " + name);
        noteUnknown(family_, name);
        return other_;
    }

  private:
    std::string family_;
    std::vector<std::string> names_;
    std::unordered_map<std::string, int> index_;
    int other_{-1};
};

// A column list made of named families, each a grid over a few vocabularies.
// A family given an `allowed` rule keeps only the cells it allows: the others
// are combinations the rules of the game never produce. They share one
// "~impossible" column, and any that occurs is reported (zoneEncodingUnknowns)
// rather than dropped.
class Layout {
  public:
    using Allowed = std::function<bool(const std::vector<int>&)>;
    int add(const std::string& name, std::vector<const Vocabulary*> axes, const Allowed& allowed = {}) {
        Family f{name, size_, std::move(axes), {}, -1};
        int count = 1;
        for (const auto* axis : f.axes) count *= axis->size();
        if (allowed) {
            f.cells.assign(static_cast<std::size_t>(count), -1);
            std::vector<int> index(f.axes.size(), 0);
            int kept = 0;
            for (auto& cell : f.cells) {
                if (allowed(index)) cell = f.base + kept++;
                std::size_t i = f.axes.size();
                while (i > 0 && ++index[i - 1] == f.axes[i - 1]->size()) index[--i] = 0;
            }
            f.impossible = f.base + kept;
            count = kept + 1;
        }
        families_.push_back(std::move(f));
        size_ += count;
        return static_cast<int>(families_.size()) - 1;
    }
    int at(int family, std::initializer_list<int> coordinates) const {
        const auto& f = families_.at(static_cast<std::size_t>(family));
        if (coordinates.size() != f.axes.size()) throw std::logic_error("Zone encoding column rank differs: " + f.name);
        int column = 0;
        std::size_t axis = 0;
        for (const int x : coordinates) {
            const int size = f.axes[axis++]->size();
            if (x < 0 || x >= size) throw std::logic_error("Zone encoding coordinate out of range: " + f.name);
            column = column * size + x;
        }
        if (f.cells.empty()) return f.base + column;
        if (const int kept = f.cells[static_cast<std::size_t>(column)]; kept >= 0) return kept;
        std::string cell;
        axis = 0;
        for (const int x : coordinates) {
            if (axis) cell += ':';
            cell += f.axes[axis++]->names()[static_cast<std::size_t>(x)];
        }
        noteUnknown("impossible_" + f.name, cell);
        return f.impossible;
    }
    int size() const { return size_; }
    std::vector<std::string> names() const {
        std::vector<std::string> out;
        out.reserve(static_cast<std::size_t>(size_));
        for (const auto& f : families_) {
            std::vector<int> index(f.axes.size(), 0);
            for (std::size_t cell = 0;; ++cell) {
                if (f.cells.empty() || f.cells[cell] >= 0) {
                    std::string name = f.name;
                    for (std::size_t i = 0; i < f.axes.size(); ++i) name += ":" + f.axes[i]->names()[index[i]];
                    out.push_back(std::move(name));
                }
                std::size_t i = f.axes.size();
                while (i > 0 && ++index[i - 1] == f.axes[i - 1]->size()) index[--i] = 0;
                if (i == 0) break;
            }
            if (!f.cells.empty()) out.push_back(f.name + ":~impossible");
        }
        return out;
    }

  private:
    struct Family {
        std::string name;
        int base;
        std::vector<const Vocabulary*> axes;
        std::vector<int> cells;  // Column of each grid cell, -1 if ruled out; empty when all are kept.
        int impossible;
    };
    std::vector<Family> families_;
    int size_{0};
};

struct Context {
    ZoneEncodingSpec spec;
    Vocabulary zones, nations, nationOrNone, players, playerOrNone, unitTypes, facilityTypes, technologies, projectTypes,
        rows, terrains, unitClasses, actorFlags, topUnitFlags, unitStats, refKinds, recordFlags, actionKinds,
        decisionKinds, adapterKinds, battleStages, chancePurposes, pendingNames, dataKeys, phases, scheduleKinds,
        powerStatuses, incomeComponents, enumValues, parameterKeys, roleGroups, repairTargets, repairStats,
        facilityStats, projectClasses, projectStats, chanceStats, positions, ranks, battleWordKeys, battleWords;
    std::vector<int> unitClassOfType;
    std::vector<int> wordKeyOfDataKey;  // Each battle-note key's row in battleWordKeys, or its other.
    std::unordered_map<std::string, int> roleOfKey;
    Layout zone, global, action;
    // Zone families.
    int zPossessor, zStartPossessor, zChanged, zAligned, zTerritoryFlag, zCapitalOf, zDeclinedRail, zUnitNationType,
        zUnitStat, zUnitClassFlag, zUnitRef, zUnitAtFacility, zUnitFacilityBorder, zCarried, zNationHere, zFacility, zFacilityFlag, zFacilityBorder,
        zFacilityOriginalOwner, zFacilityOriginalType, zProject, zProjectStat, zProjectFlag, zProjectRow, zProjectBorder,
        zRepair, zRail, zRailDamage, zRailRepair, zBattle, zBattleStage, zBattleRound, zBattleAttacker, zBattleDefender, zBattleFlag,
        zBattleData, zBattleDataUnit, zBattleDataRank, zBattleDataZone, zBattleDataWord, zBattleHits, zBattleOrder;
    // Global families.
    int gRound, gCompletedRounds, gRoundsLeft, gPhase, gTurnNation, gIncomeCollected, gTerminal, gPresent, gAlliance,
        gPlayer, gPower, gController, gTreasury, gHasTreasury, gIncome, gIncomeKnown, gTech, gWar, gAlly, gNationFlag,
        gResearched, gCompletedTurns, gSurrendered, gEvolved, gTruce, gTruceEnded, gForeignWarPending,
        gTruceOfferPending, gInvader, gAttackedWarlord, gAlignmentQueue, gPending, gPendingNation, gPendingValue,
        gDecisionKind, gDecisionNation, gDecisionReaction, gDecisionDepth, gDecisionStack, gAdapterKind, gOwner,
        gOffered, gPassed, gOrder, gChance, gChancePurpose, gChanceTech, gChanceNation, gChanceStat, gStateFlag,
        gStateFlagNation, gVisited, gDeclinedRails, gUnsitedProject, gUnsitedProjectStat, gUnsitedProjectRow,
        gUnsitedProjectFlag;
    // Option families.
    int aScheduleKind, aPlayer, aKind, aNation, aDecision, aKey, aUnitNationType, aUnitStat, aUnitZone, aUnitRank,
        aUnitOrigin, aUnitRefPlace, aUnitRefFacility, aUnitRefBorder, aUnitCargo, aUnitCargoOrigin, aUnitCargoFlag,
        aUnitLaterPeers, aUnitCarrier,
        aProjectStat, aProjectBorder, aProjectFlag, aFacilityBorder, aFacilityFlag, aFacilityDamage, aBattleAttacker, aBattleDefender, aBattleZone,
        aBattleUnits, aZone, aFacility,
        aBattleStage, aProject, aProjectOwner, aRailEndpoint, aRailDamage, aRow, aNationRef, aTech, aEnum, aNumber, aTrue, aFalse, aNull,
        aListLength;
};

std::string baseName(const std::string& name, std::string* argument = nullptr) {
    const auto colon = name.find(':');
    std::string base = name.substr(0, colon);
    if (argument) *argument = colon == std::string::npos ? std::string() : name.substr(colon + 1);
    // Sequence numbers such as recruitment_roll_14 name an instance, not a kind.
    auto end = base.size();
    while (end > 0 && std::isdigit(static_cast<unsigned char>(base[end - 1]))) --end;
    if (end < base.size() && end > 0 && base[end - 1] == '_') base.resize(end - 1);
    return base;
}

// Splits a trailing nation from names such as last_conqueror_kmt or evolution_pending_ccp.
std::string withoutNation(const Context& c, const std::string& base, std::string* nation) {
    for (const auto& id : c.nations.names()) {
        if (base.size() > id.size() + 1 && base.compare(base.size() - id.size(), id.size(), id) == 0 &&
            base[base.size() - id.size() - 1] == '_') {
            if (nation) *nation = id;
            return base.substr(0, base.size() - id.size() - 1);
        }
    }
    return base;
}

bool temporal(const std::string& base) {
    const auto ends = [&](const std::string& suffix) {
        return base.size() >= suffix.size() && base.compare(base.size() - suffix.size(), suffix.size(), suffix) == 0;
    };
    // "placed_this_turn" and its kind are yes/no marks, not turn numbers.
    return (ends("_turn") && !ends("_this_turn")) || ends("_turn_serial") || ends("_round") || ends("_turn_start");
}

int clampValue(long value) { return static_cast<int>(std::clamp<long>(value, -100000, 100000)); }

// A flag's value as the network sees it: a turn or round number becomes how
// many turns or rounds ago it was set (1 for the current one), anything else stays.
int flagValue(const State& s, const std::string& base, int value) {
    if (!temporal(base)) return clampValue(value);
    const long now = base.size() >= 6 && base.compare(base.size() - 6, 6, "_round") == 0
                         ? s.clock.roundIndex
                         : static_cast<long>(s.clock.playerTurnSerial);
    return static_cast<int>(1 + std::clamp<long>(now - value, 0, 30));
}

std::optional<Id> playerOf(const State& s, const Id& nation, int depth = 0) {
    const auto found = s.nations.find(nation);
    if (found == s.nations.end() || depth > 4) return std::nullopt;
    if (found->second.player) return found->second.player;
    if (found->second.controllerNation) return playerOf(s, *found->second.controllerNation, depth + 1);
    if (const auto it = s.politics.pending.find("warlord_defense_player:" + nation);
        it != s.politics.pending.end() && it->second.isString())
        return it->second.asString();
    return std::nullopt;
}

std::vector<std::string> mapIds(const State& s) {
    std::vector<std::string> ids;
    for (const auto& [id, node] : s.definition->geography.require("nodes").asObject()) ids.push_back(id);
    return ids;
}

std::vector<std::string> terrainsOf(const V& value) {
    if (value.isString()) return {value.asString()};
    std::vector<std::string> out;
    if (value.isArray())
        for (const auto& item : value.asArray())
            if (item.isString()) out.push_back(item.asString());
    return out;
}

double numberOr(const V* value, double fallback = 0) {
    if (!value || value->isNull()) return fallback;
    if (value->isBool()) return value->asBool() ? 1 : 0;
    if (value->isNumber()) return value->asNumber();
    if (value->isArray()) return static_cast<double>(value->asArray().size());
    return fallback;
}

std::shared_ptr<const Context> buildContext(const State& s) {
    if (!s.definition || !s.definition->catalog) throw std::runtime_error("Zone encoding requires a frozen catalog");
    auto c = std::make_shared<Context>();
    const auto& catalog = *s.definition->catalog;
    std::vector<std::string> nations, types, facilities, technologies, rows, terrains;
    for (const auto& [id, faction] : s.definition->factions) nations.push_back(id);
    for (const auto& [id, unit] : catalog.units()) types.push_back(id);
    for (const auto& [id, facility] : catalog.facilities()) facilities.push_back(id);
    for (const auto& [id, technology] : catalog.technologies()) technologies.push_back(id);
    for (const auto& [id, row] : catalog.rows()) rows.push_back(id);
    const auto& nodes = s.definition->geography.require("nodes").asObject();
    for (const auto& [id, node] : nodes) {
        for (const auto& terrain : terrainsOf(node.require("terrain"))) terrains.push_back(terrain);
        if (const auto* neighbors = node.find("neighbors"))
            for (const auto& edge : neighbors->asArray()) {
                if (const auto* border = edge.find("border_terrain"); border && border->isString())
                    terrains.push_back(border->asString());
                if (const auto* contains = edge.find("border_terrain_contains"))
                    for (const auto& terrain : terrainsOf(*contains)) terrains.push_back(terrain);
            }
    }
    std::vector<std::string> projects = types;
    projects.insert(projects.end(), facilities.begin(), facilities.end());
    std::vector<std::string> adapter = kDecisionKinds;
    adapter.insert(adapter.end(), kPhases.begin(), kPhases.end());
    adapter.insert(adapter.end(), {"chance", "declaration_offer", "terminal"});
    std::vector<std::string> unitStats = kUnitBaseStats;
    std::vector<std::string> topFlags = kTopUnitFlags;
    std::sort(topFlags.begin(), topFlags.end());
    unitStats.insert(unitStats.end(), topFlags.begin(), topFlags.end());

    c->zones = Vocabulary("zone", mapIds(s), false);
    c->nations = Vocabulary("nation", nations, false);
    std::vector<std::string> nationOrNone = nations;
    nationOrNone.push_back("~none");
    c->nationOrNone = Vocabulary("nation", nationOrNone, false);
    c->players = Vocabulary("player", {"allies", "axis", "comintern"}, false);
    c->playerOrNone = Vocabulary("player", {"allies", "axis", "comintern", "~none"}, false);
    c->unitTypes = Vocabulary("unit_type", types, false);
    c->facilityTypes = Vocabulary("facility_type", facilities, true);
    c->technologies = Vocabulary("technology", technologies, true);
    c->projectTypes = Vocabulary("project_type", projects, true);
    c->rows = Vocabulary("row", rows, true);
    c->terrains = Vocabulary("terrain", terrains, true);
    c->unitClasses = Vocabulary("unit_class", kUnitClasses, true);
    c->actorFlags = Vocabulary("actor_flag", kActorFlags, true);
    c->topUnitFlags = Vocabulary("top_unit_flag", kTopUnitFlags, false);
    // Base statistics keep their listed order; unitFacts emits them by position.
    c->unitStats = Vocabulary("unit_stat", unitStats, false, false);
    c->refKinds = Vocabulary("unit_reference", kRefKinds, true);
    c->recordFlags = Vocabulary("record_flag", kRecordFlags, true);
    c->actionKinds = Vocabulary("action_kind", kActionKinds, true);
    c->decisionKinds = Vocabulary("decision_kind", kDecisionKinds, true);
    c->adapterKinds = Vocabulary("adapter_kind", adapter, true);
    c->battleStages = Vocabulary("battle_stage", kBattleStages, true);
    c->chancePurposes = Vocabulary("chance_purpose", kChancePurposes, true);
    c->pendingNames = Vocabulary("pending", kPendingNames, true);
    c->dataKeys = Vocabulary("battle_data", kBattleDataKeys, true);
    std::vector<std::string> battleWords = kBattleWords;
    battleWords.insert(battleWords.end(), kBattleStages.begin(), kBattleStages.end());
    for (const auto& [id, unit] : catalog.units()) battleWords.insert(battleWords.end(), unit.classes.begin(), unit.classes.end());
    battleWords.insert(battleWords.end(), nations.begin(), nations.end());
    for (const std::string player : {"allies", "axis", "comintern"}) battleWords.push_back(player);
    c->battleWords = Vocabulary("battle_word", battleWords, true);
    c->battleWordKeys = Vocabulary("battle_word_note", kBattleWordKeys, true);
    for (const auto& key : c->dataKeys.names()) {
        const int row = c->battleWordKeys.find(key);
        c->wordKeyOfDataKey.push_back(row >= 0 ? row : c->battleWordKeys.other());
    }
    c->phases = Vocabulary("phase", kPhases, false);
    c->scheduleKinds = Vocabulary("schedule_kind", kScheduleKinds, true);
    c->powerStatuses = Vocabulary("power_status", kPowerStatuses, true);
    c->incomeComponents = Vocabulary("income_component", kIncomeComponents, true);
    c->enumValues = Vocabulary("enum_value", kEnumValues, true);
    c->parameterKeys = Vocabulary("parameter", kParameterKeys, true);
    c->roleGroups = Vocabulary("role", {"0_source", "1_path", "2_target", "3_other"}, false);
    c->repairTargets = Vocabulary("repair_target", kRepairTargets, true);
    c->repairStats = Vocabulary("repair_stat", kRepairStats, false);
    c->facilityStats = Vocabulary("facility_stat", kFacilityStats, false);
    c->projectClasses = Vocabulary("project_class", kProjectClasses, false);
    c->projectStats = Vocabulary("project_stat", kProjectStats, false);
    c->chanceStats = Vocabulary("chance_stat", kChanceStats, false);
    c->positions = Vocabulary("position", {"0", "1", "2"}, false);
    c->ranks = Vocabulary("rank", {"0", "1", "2", "3", "4", "5", "6", "7+"}, false);

    c->unitClassOfType.assign(static_cast<std::size_t>(c->unitTypes.size()), c->unitClasses.other());
    for (const auto& [id, unit] : catalog.units()) {
        int cls = c->unitClasses.other();
        for (const auto& name : kUnitClasses)
            if (unit.classes.contains(name)) cls = c->unitClasses.find(name);
        c->unitClassOfType[static_cast<std::size_t>(c->unitTypes.find(id))] = cls;
    }
    for (const std::string key : {"artillery", "battle", "facility", "factory", "origin_facility", "plan", "project",
                                  "row", "source", "transport", "unit", "units"})
        c->roleOfKey[key] = 0;
    c->roleOfKey["path"] = 1;
    for (const std::string key : {"beneficiary", "border", "border2", "declaring_nation", "destination",
                                  "destination_facility", "endpoint", "neighbor", "recipient", "sea", "target",
                                  "technology", "zone", "zones"})
        c->roleOfKey[key] = 2;

    // Cells the rules of the whole game rule out, whatever the scenario; a rare
    // situation keeps its column. A type the rulebook reserves for some nations
    // (its national_exclusive_type rule) belongs to them alone: Japan never
    // fields a Tiger I, while Germany would.
    const int typeCount = c->unitTypes.size(), nationCount = c->nations.size();
    const auto cell = [&](int a, int b) { return static_cast<std::size_t>(a * typeCount + b); };
    std::vector<char> ownable(static_cast<std::size_t>(nationCount * typeCount), 1);
    for (const auto& [id, unit] : catalog.units())
        if (unit.rules.isArray())
            for (const auto& rule : unit.rules.asArray())
                if (const auto* name = rule.find("id"); name && name->asString() == "national_exclusive_type") {
                    std::set<std::string> owners;
                    for (const auto& nation : rule.require("parameters").require("nations").asArray())
                        owners.insert(nation.asString());
                    for (int n = 0; n < nationCount; ++n)
                        ownable[cell(n, c->unitTypes.find(id))] = owners.contains(c->nations.names()[n]);
                }
    std::vector<char> owned(static_cast<std::size_t>(typeCount), 0);  // Some nation here may own the type.
    for (int t = 0; t < typeCount; ++t)
        for (int n = 0; n < nationCount; ++n) owned[t] |= ownable[cell(n, t)];
    // Which types may carry which (navalCargoFits, carrierEligible and the
    // catalog's cargo rules): naval transports take land units, Japan's
    // destroyers a Marine, carriers fighters and tactical bombers (medium
    // bombers on heavy fleet carriers), air transports and strategic bombers the
    // cargo their rules accept.
    std::vector<char> carries(static_cast<std::size_t>(typeCount * typeCount), 0);
    const auto allow = [&](int carrier, const std::function<bool(const UnitDefinition&)>& cargo) {
        for (const auto& [id, unit] : catalog.units())
            if (cargo(unit)) carries[cell(carrier, c->unitTypes.find(id))] = 1;
    };
    const auto named = [](const V& list) {
        std::set<std::string> out;
        for (const auto& name : list.asArray()) out.insert(name.asString());
        return out;
    };
    for (const auto& [id, unit] : catalog.units()) {
        const int carrier = c->unitTypes.find(id);
        if (unit.classes.contains("naval_transport"))
            allow(carrier, [](const UnitDefinition& u) { return u.classes.contains("land") || u.classes.contains("rocket"); });
        if (unit.classes.contains("carrier"))
            allow(carrier, [&](const UnitDefinition& u) {
                return u.classes.contains("fighter") || u.id == "tactical_bomber" ||
                       (u.id == "medium_bomber" && id == "heavy_fleet_carrier");
            });
        if (!unit.rules.isArray()) continue;
        for (const auto& rule : unit.rules.asArray()) {
            const auto* name = rule.find("id");
            const auto* p = rule.find("parameters");
            if (!name || !p) continue;
            std::set<std::string> types, classes;
            if (name->asString() == "japanese_destroyer_marine_transport") types = named(p->require("unit_types"));
            else if (name->asString() == "strategic_bomber_airborne_cargo") types = named(p->require("accepted_cargo"));
            else if (name->asString() == "air_transport_cargo") {
                types = named(p->require("combat_cargo_types"));
                types.merge(named(p->require("noncombat_extra_cargo_types")));
                classes = named(p->require("noncombat_cargo_classes"));
            }
            allow(carrier, [&](const UnitDefinition& u) {
                return types.contains(u.id) ||
                       std::any_of(classes.begin(), classes.end(), [&](const auto& k) { return u.classes.contains(k); });
            });
        }
    }
    std::vector<char> canCarry(static_cast<std::size_t>(typeCount), 0), canBeCarried(canCarry);
    for (int a = 0; a < typeCount; ++a)
        for (int b = 0; b < typeCount; ++b)
            if (carries[cell(a, b)] && owned[a] && owned[b]) canCarry[a] = canBeCarried[b] = 1;
    // Units point at facilities only from ships (in port, repairing, scrambling,
    // a strategic move's destination) and aircraft (scramble sources), and only
    // naval facilities, which face the sea, have borders a unit can see.
    const int landClass = c->unitClasses.find("land");
    const auto atFacility = [&](int t) { return owned[t] && c->unitClassOfType[static_cast<std::size_t>(t)] != landClass; };
    std::vector<char> sea(static_cast<std::size_t>(c->zones.size()), 0);
    for (int zone = 0; zone < c->zones.size(); ++zone)
        if (const auto* type = nodes.at(c->zones.names()[zone]).find("type"); type && type->isString())
            sea[zone] = type->asString() == "sea";
    // Projects of a unit type follow its owners; facility projects are open to all.
    const auto projectOf = [&](int n, int p) {
        const int t = c->unitTypes.find(c->projectTypes.names()[static_cast<std::size_t>(p)]);
        return t < 0 || (n < 0 ? owned[t] != 0 : ownable[cell(n, t)] != 0);
    };
    using Cell = std::vector<int>;

    auto& z = c->zone;
    c->zPossessor = z.add("possessor", {&c->nationOrNone});
    c->zStartPossessor = z.add("turn_start_possessor", {&c->nationOrNone});
    c->zChanged = z.add("changed_hands_this_turn", {});
    c->zAligned = z.add("aligned_this_turn", {});
    c->zTerritoryFlag = z.add("territory_flag", {&c->recordFlags});
    c->zCapitalOf = z.add("capital_of", {&c->nations});
    c->zDeclinedRail = z.add("declined_rail_request", {});
    c->zUnitNationType = z.add("units", {&c->nations, &c->unitTypes},
                               [&](const Cell& x) { return ownable[cell(x[0], x[1])] != 0; });
    c->zUnitStat = z.add("unit_stat", {&c->playerOrNone, &c->unitTypes, &c->unitStats},
                         [&](const Cell& x) { return owned[x[1]] != 0; });
    c->zUnitClassFlag = z.add("unit_flag", {&c->playerOrNone, &c->unitClasses, &c->actorFlags});
    c->zUnitRef = z.add("unit_reference_here", {&c->playerOrNone, &c->unitTypes, &c->refKinds},
                        [&](const Cell& x) { return owned[x[1]] != 0; });
    c->zCarried = z.add("carried", {&c->playerOrNone, &c->unitTypes, &c->unitTypes},
                        [&](const Cell& x) { return carries[cell(x[1], x[2])] && owned[x[1]] && owned[x[2]]; });
    c->zUnitAtFacility = z.add("unit_facility", {&c->playerOrNone, &c->unitTypes, &c->facilityTypes},
                               [&](const Cell& x) { return atFacility(x[1]); });
    c->zUnitFacilityBorder = z.add("unit_facility_border", {&c->playerOrNone, &c->unitTypes, &c->zones},
                                   [&](const Cell& x) { return atFacility(x[1]) && sea[x[2]]; });
    c->zNationHere = z.add("nation_flag_here", {&c->nations, &c->actorFlags});
    c->zFacility = z.add("facility", {&c->facilityTypes, &c->facilityStats});
    c->zFacilityFlag = z.add("facility_flag", {&c->facilityTypes, &c->recordFlags});
    c->zFacilityBorder = z.add("facility_border", {&c->facilityTypes, &c->zones});
    c->zFacilityOriginalOwner = z.add("facility_original_owner", {&c->facilityTypes, &c->nations});
    c->zFacilityOriginalType = z.add("facility_original_type", {&c->facilityTypes, &c->facilityTypes});
    c->zProject = z.add("project", {&c->nations, &c->projectTypes},
                        [&](const Cell& x) { return projectOf(x[0], x[1]); });
    c->zProjectStat = z.add("project_stat", {&c->projectTypes, &c->projectStats},
                            [&](const Cell& x) { return projectOf(-1, x[0]); });
    c->zProjectFlag = z.add("project_flag", {&c->projectClasses, &c->recordFlags});
    c->zProjectRow = z.add("project_row", {&c->rows});
    c->zProjectBorder = z.add("project_border", {&c->zones});
    c->zRepair = z.add("repair", {&c->nations, &c->repairTargets, &c->repairStats});
    c->zRail = z.add("rail_to", {&c->zones});
    c->zRailDamage = z.add("rail_damage_toward", {&c->zones});
    c->zRailRepair = z.add("rail_repair_toward", {&c->zones}, [&](const Cell& x) { return !sea[x[0]]; });
    c->zBattle = z.add("battle", {});
    c->zBattleStage = z.add("battle_stage", {&c->battleStages});
    c->zBattleRound = z.add("battle_round", {});
    c->zBattleAttacker = z.add("battle_attacker", {&c->nations});
    c->zBattleDefender = z.add("battle_defender", {&c->nationOrNone});
    c->zBattleFlag = z.add("battle_flag", {&c->recordFlags});
    c->zBattleData = z.add("battle_data", {&c->dataKeys});
    c->zBattleDataUnit = z.add("battle_data_unit", {&c->dataKeys, &c->unitTypes},
                               [&](const Cell& x) { return owned[x[1]] != 0; });
    c->zBattleDataRank = z.add("battle_data_unit_rank", {&c->dataKeys, &c->ranks});
    c->zBattleDataZone = z.add("battle_data_zone", {&c->dataKeys, &c->zones});
    c->zBattleDataWord = z.add("battle_data_word", {&c->battleWordKeys, &c->battleWords});
    c->zBattleHits = z.add("battle_pending_hits", {});
    c->zBattleOrder = z.add("battle_order", {});

    auto& g = c->global;
    c->gRound = g.add("round", {});
    c->gCompletedRounds = g.add("completed_rounds", {});
    c->gRoundsLeft = g.add("rounds_left", {});
    c->gPhase = g.add("phase", {&c->phases});
    c->gTurnNation = g.add("turn_nation", {&c->nations});
    c->gIncomeCollected = g.add("income_collected", {});
    c->gTerminal = g.add("terminal", {});
    c->gPresent = g.add("nation_present", {&c->nations});
    c->gAlliance = g.add("alliance", {&c->nations, &c->playerOrNone});
    c->gPlayer = g.add("player", {&c->nations, &c->playerOrNone});
    c->gPower = g.add("power_status", {&c->nations, &c->powerStatuses});
    c->gController = g.add("controller", {&c->nations, &c->nationOrNone});
    c->gTreasury = g.add("treasury", {&c->nations});
    c->gHasTreasury = g.add("has_treasury", {&c->nations});
    c->gIncome = g.add("income", {&c->nations, &c->incomeComponents});
    c->gIncomeKnown = g.add("income_known", {&c->nations});
    c->gTech = g.add("technology_stage", {&c->nations, &c->technologies});
    c->gWar = g.add("at_war", {&c->nations, &c->nations});
    c->gAlly = g.add("allied", {&c->nations, &c->nations});
    c->gNationFlag = g.add("nation_flag", {&c->nations, &c->actorFlags});
    c->gResearched = g.add("researched_round", {&c->nations, &c->technologies});
    c->gCompletedTurns = g.add("completed_turns", {&c->nations});
    c->gSurrendered = g.add("surrendered", {&c->nations});
    c->gEvolved = g.add("evolution_awarded", {&c->nations});
    c->gTruce = g.add("chinese_truce", {});
    c->gTruceEnded = g.add("truce_permanently_ended", {});
    c->gForeignWarPending = g.add("foreign_china_war_pending", {});
    c->gTruceOfferPending = g.add("truce_offer_pending", {});
    c->gInvader = g.add("china_invader", {&c->nations});
    c->gAttackedWarlord = g.add("attacked_warlord", {&c->nations, &c->nations});
    c->gAlignmentQueue = g.add("alignment_queue", {&c->nations});
    c->gPending = g.add("pending", {&c->pendingNames});
    c->gPendingNation = g.add("pending_nation", {&c->pendingNames, &c->nations});
    c->gPendingValue = g.add("pending_value", {&c->pendingNames});
    c->gDecisionKind = g.add("decision", {&c->decisionKinds});
    c->gDecisionNation = g.add("decision_nation", {&c->nations});
    c->gDecisionReaction = g.add("decision_reaction", {});
    c->gDecisionDepth = g.add("decision_depth", {});
    c->gDecisionStack = g.add("decision_below", {&c->decisionKinds});
    c->gAdapterKind = g.add("scheduled_decision", {&c->adapterKinds});
    c->gOwner = g.add("deciding_player", {&c->playerOrNone});
    c->gOffered = g.add("interrupt_offered_to", {&c->playerOrNone});
    c->gPassed = g.add("interrupt_passed", {&c->players});
    c->gOrder = g.add("interrupt_order", {&c->players, &c->positions});
    c->gChance = g.add("chance", {});
    c->gChancePurpose = g.add("chance_purpose", {&c->chancePurposes});
    c->gChanceTech = g.add("chance_technology", {&c->technologies});
    c->gChanceNation = g.add("chance_nation", {&c->nations});
    c->gChanceStat = g.add("chance_stat", {&c->chanceStats});
    c->gStateFlag = g.add("state_flag", {&c->recordFlags});
    c->gStateFlagNation = g.add("state_flag_nation", {&c->recordFlags, &c->nations});
    c->gVisited = g.add("visited_configurations", {});
    c->gDeclinedRails = g.add("declined_rail_requests", {});
    c->gUnsitedProject = g.add("unsited_project", {&c->nations, &c->projectTypes},
                               [&](const Cell& x) { return projectOf(x[0], x[1]); });
    c->gUnsitedProjectStat = g.add("unsited_project_stat", {&c->projectTypes, &c->projectStats},
                                   [&](const Cell& x) { return projectOf(-1, x[0]); });
    c->gUnsitedProjectRow = g.add("unsited_project_row", {&c->rows});
    c->gUnsitedProjectFlag = g.add("unsited_project_flag", {&c->projectClasses, &c->recordFlags});

    auto& a = c->action;
    c->aScheduleKind = a.add("schedule", {&c->scheduleKinds});
    c->aPlayer = a.add("player", {&c->playerOrNone});
    c->aKind = a.add("kind", {&c->actionKinds});
    c->aNation = a.add("nation", {&c->nations});
    c->aDecision = a.add("answers_decision", {});
    c->aKey = a.add("parameter", {&c->parameterKeys});
    c->aUnitNationType = a.add("unit", {&c->roleGroups, &c->nations, &c->unitTypes},
                               [&](const Cell& x) { return ownable[cell(x[1], x[2])] != 0; });
    c->aUnitStat = a.add("unit_stat", {&c->roleGroups, &c->unitStats});
    c->aUnitZone = a.add("unit_zone", {&c->roleGroups, &c->zones});
    c->aUnitRank = a.add("unit_rank", {&c->roleGroups, &c->ranks});
    c->aUnitOrigin = a.add("unit_turn_origin", {&c->roleGroups, &c->zones});
    c->aUnitRefPlace = a.add("unit_reference_place", {&c->roleGroups, &c->refKinds, &c->zones});
    c->aUnitRefFacility = a.add("unit_facility", {&c->roleGroups, &c->facilityTypes});
    c->aUnitRefBorder = a.add("unit_facility_border", {&c->roleGroups, &c->zones},
                              [&](const Cell& x) { return sea[x[1]] != 0; });
    c->aUnitCargo = a.add("unit_cargo", {&c->roleGroups, &c->unitTypes},
                          [&](const Cell& x) { return canBeCarried[x[1]] != 0; });
    c->aUnitCargoOrigin = a.add("unit_cargo_turn_origin", {&c->roleGroups, &c->zones});
    c->aUnitCargoFlag = a.add("unit_cargo_flag", {&c->roleGroups, &c->actorFlags});
    c->aUnitLaterPeers = a.add("unit_later_peers", {&c->roleGroups, &c->unitTypes},
                               [&](const Cell& x) { return owned[x[1]] != 0; });
    c->aProjectStat = a.add("project_stat", {&c->roleGroups, &c->projectStats});
    c->aProjectBorder = a.add("project_border", {&c->roleGroups, &c->zones});
    c->aProjectFlag = a.add("project_flag", {&c->roleGroups, &c->recordFlags});
    c->aFacilityBorder = a.add("facility_border", {&c->roleGroups, &c->zones});
    c->aFacilityFlag = a.add("facility_flag", {&c->roleGroups, &c->recordFlags});
    c->aFacilityDamage = a.add("facility_damage", {&c->roleGroups});
    c->aUnitCarrier = a.add("unit_carried_by", {&c->roleGroups, &c->unitTypes},
                            [&](const Cell& x) { return canCarry[x[1]] != 0; });
    c->aBattleAttacker = a.add("battle_attacker", {&c->roleGroups, &c->nations});
    c->aBattleDefender = a.add("battle_defender", {&c->roleGroups, &c->nationOrNone});
    c->aBattleZone = a.add("battle_place", {&c->roleGroups, &c->zones});
    c->aBattleUnits = a.add("battle_units", {&c->roleGroups, &c->unitTypes},
                            [&](const Cell& x) { return owned[x[1]] != 0; });
    c->aZone = a.add("zone", {&c->roleGroups, &c->zones});
    c->aFacility = a.add("facility", {&c->roleGroups, &c->facilityTypes});
    c->aBattleStage = a.add("battle_stage", {&c->roleGroups, &c->battleStages});
    c->aProject = a.add("project", {&c->roleGroups, &c->projectTypes},
                        [&](const Cell& x) { return projectOf(-1, x[1]); });
    c->aProjectOwner = a.add("project_owner", {&c->roleGroups, &c->nations});
    c->aRailEndpoint = a.add("rail_endpoint", {&c->roleGroups, &c->zones}, [&](const Cell& x) { return !sea[x[1]]; });
    c->aRailDamage = a.add("rail_damage", {&c->roleGroups, &c->zones}, [&](const Cell& x) { return !sea[x[1]]; });
    c->aRow = a.add("row", {&c->rows});
    c->aNationRef = a.add("nation_named", {&c->roleGroups, &c->nations});
    c->aTech = a.add("technology", {&c->technologies});
    c->aEnum = a.add("value", {&c->parameterKeys, &c->enumValues});
    c->aNumber = a.add("number", {&c->parameterKeys});
    c->aTrue = a.add("true", {&c->parameterKeys});
    c->aFalse = a.add("false", {&c->parameterKeys});
    c->aNull = a.add("null", {&c->parameterKeys});
    c->aListLength = a.add("list_length", {&c->parameterKeys});

    auto& spec = c->spec;
    spec.zones = c->zones.names();
    spec.nations = nations;
    spec.unitTypes = types;
    spec.facilityTypes = facilities;
    spec.technologies = technologies;
    spec.projectTypes = c->projectTypes.names();
    spec.rows = rows;
    spec.zoneColumns = z.size();
    spec.globalColumns = g.size();
    spec.actionColumns = a.size();
    spec.zoneColumnNames = z.names();
    spec.globalColumnNames = g.names();
    spec.actionColumnNames = a.names();

    // Fixed map facts. Nations hold land through possession columns, so only
    // facts that never change are here.
    std::vector<std::string> statics{"land", "sea", "ipp_value", "capital", "city", "victory_city"};
    for (const auto& terrain : c->terrains.names()) statics.push_back("terrain:" + terrain);
    for (const auto& nation : nations) statics.push_back("original_owner:" + nation);
    for (const auto& nation : nations) statics.push_back("home_country_of:" + nation);
    spec.staticFeatureNames = statics;
    spec.staticFeatures = static_cast<int>(statics.size());
    spec.zoneStatic.assign(static_cast<std::size_t>(c->zones.size() * spec.staticFeatures), 0.0F);
    const int terrainBase = 6;
    const int ownerBase = terrainBase + c->terrains.size();
    const int homeBase = ownerBase + static_cast<int>(nations.size());
    for (int zi = 0; zi < c->zones.size(); ++zi) {
        const auto& id = c->zones.names()[static_cast<std::size_t>(zi)];
        const auto& node = nodes.at(id);
        float* row = spec.zoneStatic.data() + static_cast<std::size_t>(zi * spec.staticFeatures);
        const bool land = node.require("type").asString() == "land";
        row[0] = land ? 1.0F : 0.0F;
        row[1] = land ? 0.0F : 1.0F;
        row[2] = static_cast<float>(numberOr(node.find("ipp_value")));
        row[3] = static_cast<float>(numberOr(node.find("is_capital")));
        row[4] = static_cast<float>(numberOr(node.find("is_city")));
        row[5] = static_cast<float>(numberOr(node.find("is_victory_city")));
        for (const auto& terrain : terrainsOf(node.require("terrain"))) row[terrainBase + c->terrains(terrain)] = 1.0F;
        if (land) {
            try {
                row[ownerBase + c->nations(originalNation(s, id))] = 1.0F;
            } catch (const std::exception&) {
                noteUnknown("original_owner", id);
            }
        }
        for (const auto& [nation, faction] : s.definition->factions)
            if (faction.homeCountry.contains(id)) row[homeBase + c->nations(nation)] = 1.0F;
    }
    std::vector<std::string> edges{"land_to_land", "land_to_sea", "sea_to_land", "sea_to_sea", "has_river",
                                   "river_crossing", "narrow_crossing", "narrow_crossings", "railway_connection",
                                   "gauge_change", "port_or_dock_connection", "naval_facilities", "passable",
                                   "unit_capacity", "narrow_gauge"};
    for (const auto& terrain : c->terrains.names()) edges.push_back("border_terrain:" + terrain);
    spec.edgeFeatureNames = edges;
    spec.edgeFeatures = static_cast<int>(edges.size());
    const int borderBase = 15;
    for (int zi = 0; zi < c->zones.size(); ++zi) {
        const auto& from = nodes.at(c->zones.names()[static_cast<std::size_t>(zi)]);
        const bool fromLand = from.require("type").asString() == "land";
        const auto* neighbors = from.find("neighbors");
        if (!neighbors) continue;
        for (const auto& edge : neighbors->asArray()) {
            const int to = c->zones.find(edge.require("neighbor_id").asString());
            if (to < 0) continue;
            const bool toLand = nodes.at(edge.require("neighbor_id").asString()).require("type").asString() == "land";
            spec.edgeSource.push_back(zi);
            spec.edgeTarget.push_back(to);
            std::vector<float> row(static_cast<std::size_t>(spec.edgeFeatures), 0.0F);
            row[fromLand ? (toLand ? 0 : 1) : (toLand ? 2 : 3)] = 1.0F;
            row[4] = static_cast<float>(numberOr(edge.find("has_river")));
            row[5] = static_cast<float>(numberOr(edge.find("river_crossing")));
            row[6] = static_cast<float>(numberOr(edge.find("narrow_crossing")));
            row[7] = static_cast<float>(numberOr(edge.find("narrow_crossings")));
            row[8] = static_cast<float>(numberOr(edge.find("railway_connection")));
            row[9] = static_cast<float>(numberOr(edge.find("gauge_change")));
            row[10] = static_cast<float>(numberOr(edge.find("port_or_dock_connection")));
            row[11] = static_cast<float>(numberOr(edge.find("naval_facilities")));
            row[12] = static_cast<float>(numberOr(edge.find("passable"), 1));
            row[13] = static_cast<float>(numberOr(edge.find("unit_capacity")));
            const auto* source = edge.find("source_rail_gauge");
            const auto* target = edge.find("target_rail_gauge");
            row[14] = ((source && source->isString()) || (target && target->isString())) ? 1.0F : 0.0F;
            if (const auto* border = edge.find("border_terrain"); border && border->isString())
                row[borderBase + c->terrains(border->asString())] = 1.0F;
            if (const auto* contains = edge.find("border_terrain_contains"))
                for (const auto& terrain : terrainsOf(*contains)) row[borderBase + c->terrains(terrain)] = 1.0F;
            spec.edgeStatic.insert(spec.edgeStatic.end(), row.begin(), row.end());
        }
    }
    std::string fingerprint;
    for (const auto* names : {&spec.zoneColumnNames, &spec.globalColumnNames, &spec.actionColumnNames,
                              &spec.staticFeatureNames, &spec.edgeFeatureNames})
        for (const auto& name : *names) fingerprint += name + "\n";
    std::ostringstream numbers;
    for (const float x : spec.zoneStatic) numbers << x << ',';
    for (const float x : spec.edgeStatic) numbers << x << ',';
    for (std::size_t i = 0; i < spec.edgeSource.size(); ++i) numbers << spec.edgeSource[i] << '>' << spec.edgeTarget[i] << ',';
    spec.version = "campaign-zone-v1-" + contentDigest(fingerprint + numbers.str()).substr(0, 16);
    return c;
}

std::shared_ptr<const Context> contextFor(const State& s) {
    static std::mutex mutex;
    static std::map<std::string, std::shared_ptr<const Context>> cache;
    const std::lock_guard lock(mutex);
    auto& entry = cache[s.definition->fingerprint];
    if (!entry) entry = buildContext(s);
    return entry;
}

class Builder {
  public:
    explicit Builder(const Context& c) : c_(c) {}
    void zone(int zone, int column, long value) {
        if (value) zones_.push_back({zone, column, clampValue(value)});
    }
    void global(int column, long value) {
        if (value) globals_.push_back({column, clampValue(value)});
    }
    void option(int column, long value, int role) {
        if (!value) return;
        option_.push_back({column, clampValue(value)});
        if (role >= 0 && role < 3) groups_[static_cast<std::size_t>(role)].push_back({column, clampValue(value)});
    }
    void zoneRef(int role, int zone) {
        if (zone < 0) return;
        if (role == 0 && source_ < 0) source_ = zone;
        if (role == 1) path_.push_back(zone);
        if (role == 2 && target_ < 0) target_ = zone;
        if (role == 3 && other_ < 0) other_ = zone;
    }
    void finishOption(ZoneInput& out, const std::string& kind) {
        merge(option_);
        for (const auto& [column, value] : option_) {
            out.actionColumn.push_back(column);
            out.actionValue.push_back(value);
        }
        out.actionOffsets.push_back(static_cast<std::int32_t>(out.actionColumn.size()));
        out.actionSource.push_back(source_ >= 0 ? source_ : other_);
        out.actionTarget.push_back(!path_.empty() ? path_.back() : target_);
        for (const int zone : path_) out.pathZone.push_back(zone);
        out.pathOffsets.push_back(static_cast<std::int32_t>(out.pathZone.size()));
        std::array<std::string, 4> factors{kind, "", "", ""};
        for (std::size_t g = 0; g < 3; ++g) {
            merge(groups_[g]);
            std::string text;
            for (const auto& [column, value] : groups_[g]) text += std::to_string(column) + "=" + std::to_string(value) + ";";
            factors[g + 1] = std::move(text);
        }
        if (!path_.empty()) {
            factors[2] += "|";
            for (const int zone : path_) factors[2] += std::to_string(zone) + ",";
        }
        factorText_.push_back(std::move(factors));
        option_.clear();
        for (auto& group : groups_) group.clear();
        path_.clear();
        source_ = target_ = other_ = -1;
    }
    void finishPosition(ZoneInput& out) {
        std::sort(zones_.begin(), zones_.end());
        for (std::size_t i = 0; i < zones_.size();) {
            auto [zone, column, value] = zones_[i];
            long total = 0;
            for (; i < zones_.size() && zones_[i][0] == zone && zones_[i][1] == column; ++i) total += zones_[i][2];
            if (!total) continue;
            out.zoneIndex.push_back(zone);
            out.zoneColumn.push_back(column);
            out.zoneValue.push_back(clampValue(total));
        }
        merge(globals_);
        for (const auto& [column, value] : globals_) {
            out.globalColumn.push_back(column);
            out.globalValue.push_back(value);
        }
    }

    // Numbers the options' policy groups, level by level.
    void finishGroups(ZoneInput& out) {
        std::unordered_map<std::string, int> first;
        std::array<std::map<std::pair<int, std::string>, int>, 3> deeper;
        out.factorGroups.reserve(factorText_.size() * 4);
        for (auto& text : factorText_) {
            int id = first.try_emplace(std::move(text[0]), static_cast<int>(first.size())).first->second;
            out.factorGroups.push_back(id);
            for (std::size_t level = 0; level < deeper.size(); ++level) {
                auto& groups = deeper[level];
                id = groups.try_emplace({id, std::move(text[level + 1])}, static_cast<int>(groups.size())).first->second;
                out.factorGroups.push_back(id);
            }
        }
        factorText_.clear();
    }

  private:
    static void merge(std::vector<std::pair<int, int>>& entries) {
        std::sort(entries.begin(), entries.end());
        std::size_t write = 0;
        for (std::size_t i = 0; i < entries.size();) {
            const int column = entries[i].first;
            long total = 0;
            for (; i < entries.size() && entries[i].first == column; ++i) total += entries[i].second;
            if (total) entries[write++] = {column, clampValue(total)};
        }
        entries.resize(write);
    }
    const Context& c_;
    std::vector<std::array<int, 3>> zones_;
    std::vector<std::pair<int, int>> globals_, option_;
    std::array<std::vector<std::pair<int, int>>, 3> groups_;
    std::vector<std::array<std::string, 4>> factorText_;
    std::vector<int> path_;
    int source_{-1}, target_{-1}, other_{-1};
};

int playerColumn(const Context& c, const State& s, const Id& nation) {
    const auto player = playerOf(s, nation);
    return c.playerOrNone(player ? *player : "~none");
}

struct UnitRoles {
    std::unordered_map<std::string, int> role;  // 1 attacker, 2 defender
    // Place among units that differ only in their IDs (same zone, owner, type,
    // movement, damage, carrier, cargo, route and flags), in ID order. Rules
    // that build groups in ID order make the first and second of two identical
    // battleships different choices, though the units are interchangeable.
    std::unordered_map<std::string, int> rank;
};

std::string unitSignature(const UnitState& u) {
    std::string out = u.owner + '|' + u.type + '|' + u.zone + '|' + std::to_string(u.damage) + '|' +
                      std::to_string(u.movementRemaining.value_or(-1)) + '|' + std::to_string(u.movementAllowance.value_or(-1)) +
                      '|' + u.carriedBy.value_or("") + '|' + u.turnOrigin + '|';
    for (const auto& id : u.cargo) out += id + ',';
    out += '|';
    for (const auto& zone : u.route) out += zone + ',';
    out += '|';
    for (const auto& name : u.commitments) out += name + ',';
    out += '|';
    for (const auto& [name, value] : u.turnFlags) out += name + '=' + std::to_string(value) + ',';
    out += '|';
    for (const auto& [name, value] : u.gameFlags) out += name + '=' + std::to_string(value) + ',';
    return out;
}

void rankUnits(const State& s, UnitRoles& roles) {
    std::unordered_map<std::string, int> next;
    // s.units is ordered by ID, so the first unit of each signature ranks 0.
    for (const auto& [id, u] : s.units) roles.rank[id] = next[unitSignature(u)]++;
}

// Emits a unit's statistics through `emit(stat, value)`, and hands every flag
// with a place argument to `place(refKind, zone)`.
template <class Emit, class Place, class Other>
void unitFacts(const Context& c, const State& s, const UnitState& u, const UnitRoles& roles, Emit&& emit,
               Place&& place, Other&& other) {
    emit(0, 1);
    emit(1 + std::clamp(u.movementRemaining.value_or(0), 0, 7), 1);
    if (u.movementAllowance && u.movementRemaining && *u.movementRemaining < *u.movementAllowance) emit(9, 1);
    if (u.damage) emit(10, u.damage);
    if (u.carriedBy) emit(11, 1);
    if (!u.cargo.empty()) emit(12, static_cast<long>(u.cargo.size()));
    if (!u.route.empty()) emit(13, static_cast<long>(u.route.size()));
    if (!u.turnOrigin.empty() && u.turnOrigin != u.zone) emit(14, 1);
    if (const auto found = roles.role.find(u.id); found != roles.role.end()) emit(found->second == 1 ? 15 : 16, 1);
    const auto resolve = [&](const std::string& argument, const FacilityState** facility) -> int {
        if (argument.empty()) return -1;
        if (const int zone = c.zones.find(argument); zone >= 0) return zone;
        if (const auto f = s.facilities.find(argument); f != s.facilities.end()) {
            *facility = &f->second;
            return c.zones.find(f->second.zone);
        }
        if (const auto b = s.battles.find(argument); b != s.battles.end()) return c.zones.find(b->second.zone);
        if (const auto other = s.units.find(argument); other != s.units.end()) return c.zones.find(other->second.zone);
        return -1;
    };
    const auto flagged = [&](const std::string& name, int value) {
        std::string argument;
        const auto base = baseName(name, &argument);
        const int v = flagValue(s, base, value);
        if (!v) return;
        if (const int top = c.topUnitFlags.find(base); top >= 0)
            emit(static_cast<int>(kUnitBaseStats.size()) + top, v);
        else
            other(c.actorFlags(base), v);
        if (!argument.empty() && c.refKinds.find(base) >= 0) {
            const FacilityState* facility = nullptr;
            const int zone = resolve(argument, &facility);
            place(c.refKinds.find(base), zone, facility);
        }
    };
    for (const auto& name : u.commitments) flagged(name, 1);
    for (const auto& [name, value] : u.turnFlags) flagged(name, value);
    for (const auto& [name, value] : u.gameFlags) flagged(name, value);
    if (!u.turnOrigin.empty() && u.turnOrigin != u.zone)
        place(c.refKinds.find("turn_origin"), c.zones.find(u.turnOrigin), nullptr);
    for (const auto& zone : u.route) place(c.refKinds.find("route"), c.zones.find(zone), nullptr);
}

// The sea zones a facility opens onto, from its border flags.
template <class Each>
void facilityBorders(const Context& c, const FacilityState& f, Each&& each) {
    for (const auto& [name, value] : f.flags) {
        std::string argument;
        if (value && baseName(name, &argument) == "border")
            if (const int zone = c.zones.find(argument); zone >= 0) each(zone);
    }
}

void encodeUnits(const Context& c, const State& s, Builder& b, const UnitRoles& roles) {
    for (const auto& [id, u] : s.units) {
        const int zone = c.zones.find(u.zone);
        if (zone < 0) {
            noteUnknown("unit_zone", u.zone);
            continue;
        }
        const int nation = c.nations(u.owner);
        const int type = c.unitTypes(u.type);
        const int player = playerColumn(c, s, u.owner);
        const int cls = c.unitClassOfType[static_cast<std::size_t>(type)];
        b.zone(zone, c.zone.at(c.zUnitNationType, {nation, type}), 1);
        if (u.carriedBy)
            if (const auto carrier = s.units.find(*u.carriedBy); carrier != s.units.end())
                b.zone(zone, c.zone.at(c.zCarried, {player, c.unitTypes(carrier->second.type), type}), 1);
        unitFacts(c, s, u, roles,
                  [&](int stat, long value) { b.zone(zone, c.zone.at(c.zUnitStat, {player, type, stat}), value); },
                  [&](int kind, int where, const FacilityState* facility) {
                      if (where >= 0) b.zone(where, c.zone.at(c.zUnitRef, {player, type, kind}), 1);
                      if (!facility) return;
                      b.zone(zone, c.zone.at(c.zUnitAtFacility, {player, type, c.facilityTypes(facility->type)}), 1);
                      facilityBorders(c, *facility, [&](int sea) {
                          b.zone(zone, c.zone.at(c.zUnitFacilityBorder, {player, type, sea}), 1);
                      });
                  },
                  [&](int flag, long value) { b.zone(zone, c.zone.at(c.zUnitClassFlag, {player, cls, flag}), value); });
    }
}

void encodeTerritories(const Context& c, const State& s, Builder& b) {
    for (const auto& [id, t] : s.territories) {
        const int zone = c.zones.find(id);
        if (zone < 0) continue;
        b.zone(zone, c.zone.at(c.zPossessor, {c.nationOrNone(t.possessor ? *t.possessor : "~none")}), 1);
        const auto start = s.turnStart.possessions.find(id);
        const Id held = start != s.turnStart.possessions.end() && start->second ? *start->second : "~none";
        b.zone(zone, c.zone.at(c.zStartPossessor, {c.nationOrNone(held)}), 1);
        for (const auto& [name, value] : t.flags) {
            const auto base = baseName(name);
            if (base == "last_possession_change_turn") {
                if (value == static_cast<int>(s.clock.playerTurnSerial)) b.zone(zone, c.zone.at(c.zChanged, {}), 1);
            } else if (base == "aligned_turn") {
                if (value == static_cast<int>(s.clock.playerTurnSerial)) b.zone(zone, c.zone.at(c.zAligned, {}), 1);
            } else {
                b.zone(zone, c.zone.at(c.zTerritoryFlag, {c.recordFlags(base)}), flagValue(s, base, value));
            }
        }
    }
    for (const auto& [nation, zone] : s.politics.capitals)
        if (const int z = c.zones.find(zone); z >= 0) b.zone(z, c.zone.at(c.zCapitalOf, {c.nations(nation)}), 1);
}

void encodeFacilities(const Context& c, const State& s, Builder& b) {
    for (const auto& [id, f] : s.facilities) {
        const int zone = c.zones(f.zone);
        const int type = c.facilityTypes(f.type);
        b.zone(zone, c.zone.at(c.zFacility, {type, c.facilityStats.find("count")}), 1);
        if (f.damage) {
            b.zone(zone, c.zone.at(c.zFacility, {type, c.facilityStats.find("damage")}), f.damage);
            b.zone(zone, c.zone.at(c.zFacility, {type, c.facilityStats.find("damaged")}), 1);
        }
        for (const auto& [name, value] : f.flags) {
            std::string argument;
            const auto base = baseName(name, &argument);
            if (base == "border" && c.zones.find(argument) >= 0)
                b.zone(zone, c.zone.at(c.zFacilityBorder, {type, c.zones.find(argument)}), 1);
            else if (base == "original_owner" && c.nations.find(argument) >= 0)
                b.zone(zone, c.zone.at(c.zFacilityOriginalOwner, {type, c.nations.find(argument)}), 1);
            else if (base == "original_type")
                b.zone(zone, c.zone.at(c.zFacilityOriginalType, {type, c.facilityTypes(argument)}), 1);
            else
                b.zone(zone, c.zone.at(c.zFacilityFlag, {type, c.recordFlags(base)}), flagValue(s, base, value));
        }
    }
}

void projectFacts(const Context& c, const State& s, const BuildProject& p, int type,
                  const std::function<void(int column, long value)>& stat, const std::function<void(int row)>& row,
                  const std::function<void(int flag, long value)>& flag, const std::function<void(int zone)>& border) {
    long remaining = 0;
    for (const int payment : p.remainingPayments) remaining += payment;
    stat(c.projectStats.find("count"), 1);
    stat(c.projectStats.find("paid_ipp"), p.paidIpp);
    stat(c.projectStats.find("queue_position"), p.queuePosition);
    stat(c.projectStats.find("remaining_payments"), remaining);
    stat(c.projectStats.find("payments_left"), static_cast<long>(p.remainingPayments.size()));
    (void)type;
    for (const auto& [name, value] : p.flags) {
        std::string argument;
        const auto base = baseName(name, &argument);
        if (base == "row") row(c.rows(argument));
        else if (base == "border" && c.zones.find(argument) >= 0) border(c.zones.find(argument));
        else flag(c.recordFlags(base), flagValue(s, base, value));
    }
}

void encodeProjects(const Context& c, const State& s, Builder& b) {
    for (const auto& [id, p] : s.construction) {
        const int type = c.projectTypes(p.type);
        const int nation = c.nations(p.owner);
        const int cls = c.unitTypes.find(p.type) >= 0 ? c.projectClasses.find("unit") : c.projectClasses.find("facility");
        const int site = p.site ? c.zones.find(*p.site) : -1;
        if (site >= 0) {
            b.zone(site, c.zone.at(c.zProject, {nation, type}), 1);
            projectFacts(c, s, p, type,
                [&](int stat, long value) { b.zone(site, c.zone.at(c.zProjectStat, {type, stat}), value); },
                [&](int row) { b.zone(site, c.zone.at(c.zProjectRow, {row}), 1); },
                [&](int flag, long value) { b.zone(site, c.zone.at(c.zProjectFlag, {cls, flag}), value); },
                [&](int zone) { b.zone(site, c.zone.at(c.zProjectBorder, {zone}), 1); });
        } else {
            if (p.site) noteUnknown("project_site", *p.site);
            b.global(c.global.at(c.gUnsitedProject, {nation, type}), 1);
            projectFacts(c, s, p, type,
                [&](int stat, long value) { b.global(c.global.at(c.gUnsitedProjectStat, {type, stat}), value); },
                [&](int row) { b.global(c.global.at(c.gUnsitedProjectRow, {row}), 1); },
                [&](int flag, long value) { b.global(c.global.at(c.gUnsitedProjectFlag, {cls, flag}), value); },
                [&](int) {});
        }
    }
}

void encodeRepairs(const Context& c, const State& s, Builder& b) {
    for (const auto& [id, r] : s.repairs) {
        int zone = -1, toward = -1;
        std::string kind = "other";
        if (const auto u = s.units.find(r.target); u != s.units.end()) {
            zone = c.zones.find(u->second.zone);
            kind = "unit";
        } else if (const auto f = s.facilities.find(r.target); f != s.facilities.end()) {
            zone = c.zones.find(f->second.zone);
            kind = "facility";
        } else if (s.territories.contains(r.target)) {
            zone = c.zones.find(r.target);
            kind = "city";
        } else if (const auto p = s.construction.find(r.target); p != s.construction.end()) {
            if (p->second.site) {
                const auto site = s.facilities.find(*p->second.site);
                zone = c.zones.find(site != s.facilities.end() ? site->second.zone : *p->second.site);
            }
            kind = "construction";
        } else if (const auto rail = s.rails.find(r.target); rail != s.rails.end()) {
            // A railroad repair mends one side: it is filed at that side's zone,
            // with the zone across the border.
            const Id& side = r.endpoint ? *r.endpoint : rail->second.endpointA;
            zone = c.zones.find(side);
            toward = c.zones.find(side == rail->second.endpointA ? rail->second.endpointB : rail->second.endpointA);
            kind = "rail";
        }
        if (zone < 0) {
            noteUnknown("repair_target", r.target);
            continue;
        }
        const int nation = c.nations(r.owner);
        const int target = c.repairTargets(kind);
        b.zone(zone, c.zone.at(c.zRepair, {nation, target, c.repairStats.find("count")}), 1);
        b.zone(zone, c.zone.at(c.zRepair, {nation, target, c.repairStats.find("remaining_damage")}), r.remainingDamage);
        b.zone(zone, c.zone.at(c.zRepair, {nation, target, c.repairStats.find("remaining_cost")}), r.remainingCost);
        b.zone(zone, c.zone.at(c.zRepair, {nation, target, c.repairStats.find("restricts_action")}), r.restrictsAction);
        if (toward >= 0) b.zone(zone, c.zone.at(c.zRailRepair, {toward}), r.remainingDamage);
    }
}

void encodeRails(const Context& c, const State& s, Builder& b) {
    for (const auto& [id, r] : s.rails) {
        const int a = c.zones.find(r.endpointA), z = c.zones.find(r.endpointB);
        if (a < 0 || z < 0) continue;
        b.zone(a, c.zone.at(c.zRail, {z}), 1);
        b.zone(z, c.zone.at(c.zRail, {a}), 1);
        for (const auto& [endpoint, damage] : r.damageByEndpoint) {
            if (endpoint == r.endpointA) b.zone(a, c.zone.at(c.zRailDamage, {z}), damage);
            else if (endpoint == r.endpointB) b.zone(z, c.zone.at(c.zRailDamage, {a}), damage);
        }
    }
}

void dataUnit(const Context& c, Builder& b, const UnitRoles& roles, int zone, int key, const UnitState& u) {
    b.zone(zone, c.zone.at(c.zBattleDataUnit, {key, c.unitTypes(u.type)}), 1);
    if (const auto rank = roles.rank.find(u.id); rank != roles.rank.end())
        b.zone(zone, c.zone.at(c.zBattleDataRank, {key, std::min(rank->second, 7)}), 1);
}

// A word in a battle note, filed under the note when it is one that holds words.
// Unlisted words and words in other notes still count, in "other" columns, and
// are reported.
void dataWord(const Context& c, Builder& b, int zone, int key, const std::string& word) {
    const int note = c.wordKeyOfDataKey[static_cast<std::size_t>(key)];
    if (note == c.battleWordKeys.other()) noteUnknown("battle_word_note", c.dataKeys.names()[static_cast<std::size_t>(key)]);
    b.zone(zone, c.zone.at(c.zBattleDataWord, {note, c.battleWords(word)}), 1);
}

void dataFacts(const Context& c, const State& s, Builder& b, const UnitRoles& roles, int zone, int key,
               const V& value, int depth) {
    if (depth > 6) return;
    if (value.isString()) {
        const auto& text = value.asString();
        if (text.empty()) return;
        if (const auto u = s.units.find(text); u != s.units.end()) {
            dataUnit(c, b, roles, zone, key, u->second);
        } else if (const int z = c.zones.find(text); z >= 0) {
            b.zone(zone, c.zone.at(c.zBattleDataZone, {key, z}), 1);
        } else if (const auto f = s.facilities.find(text); f != s.facilities.end()) {
            b.zone(zone, c.zone.at(c.zBattleDataZone, {key, c.zones(f->second.zone)}), 1);
        } else if (const auto p = s.construction.find(text); p != s.construction.end()) {
            if (p->second.site) {
                const auto site = s.facilities.find(*p->second.site);
                const int where = c.zones.find(site != s.facilities.end() ? site->second.zone : *p->second.site);
                if (where >= 0) b.zone(zone, c.zone.at(c.zBattleDataZone, {key, where}), 1);
            }
        } else if (const auto r = s.rails.find(text); r != s.rails.end()) {
            for (const auto& side : {r->second.endpointA, r->second.endpointB})
                if (const int where = c.zones.find(side); where >= 0) b.zone(zone, c.zone.at(c.zBattleDataZone, {key, where}), 1);
        } else if (!s.turnStart.units.contains(text) &&
                   std::none_of(text.begin(), text.end(), [](unsigned char x) { return std::isdigit(x); })) {
            // Names of units lost this turn, and of anything else no longer in the
            // game, end in a number; words never contain digits.
            dataWord(c, b, zone, key, text);
        }
    } else if (value.isNumber() || value.isBool()) {
        b.zone(zone, c.zone.at(c.zBattleData, {key}), static_cast<long>(std::lround(numberOr(&value))));
    } else if (value.isArray()) {
        for (const auto& item : value.asArray()) dataFacts(c, s, b, roles, zone, key, item, depth + 1);
    } else if (value.isObject()) {
        for (const auto& [name, item] : value.asObject()) {
            // Keys naming units, nations or players count as those, as values do;
            // other keys only name the note's fields.
            if (const auto u = s.units.find(name); u != s.units.end()) dataUnit(c, b, roles, zone, key, u->second);
            else if (c.nations.find(name) >= 0 || c.players.find(name) >= 0) dataWord(c, b, zone, key, name);
            dataFacts(c, s, b, roles, zone, key, item, depth + 1);
        }
    }
}

void encodeBattles(const Context& c, const State& s, Builder& b, UnitRoles& roles) {
    for (const auto& [id, battle] : s.battles) {
        const int zone = c.zones.find(battle.zone);
        if (zone < 0) {
            noteUnknown("battle_zone", battle.zone);
            continue;
        }
        b.zone(zone, c.zone.at(c.zBattle, {}), 1);
        b.zone(zone, c.zone.at(c.zBattleStage, {c.battleStages(battle.stage)}), 1);
        if (const int attacker = c.nations.find(battle.attacker); attacker >= 0)
            b.zone(zone, c.zone.at(c.zBattleAttacker, {attacker}), 1);
        b.zone(zone, c.zone.at(c.zBattleDefender, {c.nationOrNone(c.nations.find(battle.defender) >= 0 ? battle.defender : "~none")}), 1);
        for (const auto& [name, value] : battle.flags) {
            const auto base = baseName(name);
            b.zone(zone, c.zone.at(c.zBattleFlag, {c.recordFlags(base)}), flagValue(s, base, value));
        }
        long hits = 0;
        for (const auto& [side, count] : battle.pendingHits) hits += count;
        b.zone(zone, c.zone.at(c.zBattleHits, {}), hits);
        if (battle.data.isObject())
            for (const auto& [key, value] : battle.data.asObject()) {
                const int k = c.dataKeys(key);
                b.zone(zone, c.zone.at(c.zBattleData, {k}), 1);
                if (key == "round") b.zone(zone, c.zone.at(c.zBattleRound, {}), static_cast<long>(numberOr(&value)));
                dataFacts(c, s, b, roles, zone, k, value, 0);
            }
        for (const auto& unit : battle.attackers) roles.role[unit] = 1;
        for (const auto& unit : battle.defenders) roles.role[unit] = 2;
    }
    for (std::size_t i = 0; i < s.battleOrder.size(); ++i)
        if (const auto battle = s.battles.find(s.battleOrder[i]); battle != s.battles.end())
            if (const int zone = c.zones.find(battle->second.zone); zone >= 0)
                b.zone(zone, c.zone.at(c.zBattleOrder, {}), static_cast<long>(i + 1));
}

void encodeNations(const Context& c, const State& s, Builder& b) {
    for (const auto& [id, n] : s.nations) {
        const int nation = c.nations.find(id);
        if (nation < 0) {
            noteUnknown("nation_state", id);
            continue;
        }
        b.global(c.global.at(c.gPresent, {nation}), 1);
        b.global(c.global.at(c.gAlliance, {nation, c.playerOrNone(n.alliance ? *n.alliance : "~none")}), 1);
        b.global(c.global.at(c.gPlayer, {nation, c.playerOrNone(n.player ? *n.player : "~none")}), 1);
        b.global(c.global.at(c.gPower, {nation, c.powerStatuses(n.powerStatus)}), 1);
        b.global(c.global.at(c.gController, {nation, c.nationOrNone(n.controllerNation ? *n.controllerNation : "~none")}), 1);
        if (n.treasury) {
            b.global(c.global.at(c.gHasTreasury, {nation}), 1);
            b.global(c.global.at(c.gTreasury, {nation}), *n.treasury);
        }
        for (const auto& [name, value] : n.incomeComponents)
            b.global(c.global.at(c.gIncome, {nation, c.incomeComponents(name)}), value);
        b.global(c.global.at(c.gIncomeKnown, {nation}), n.incomeKnown);
        for (const auto& [name, stage] : n.technologyStages) b.global(c.global.at(c.gTech, {nation, c.technologies(name)}), stage);
        for (const auto& other : n.atWarWith)
            if (const int m = c.nations.find(other); m >= 0) b.global(c.global.at(c.gWar, {nation, m}), 1);
        for (const auto& other : n.allies)
            if (const int m = c.nations.find(other); m >= 0) b.global(c.global.at(c.gAlly, {nation, m}), 1);
        const auto flagged = [&](const std::string& name, int value) {
            std::string argument;
            const auto base = baseName(name, &argument);
            if (base == "economy_researched_round" && c.technologies.find(argument) >= 0) {
                b.global(c.global.at(c.gResearched, {nation, c.technologies.find(argument)}),
                         1 + std::clamp(s.clock.roundIndex - value, 0, 30));
                return;
            }
            const int flag = c.actorFlags(base);
            const int v = flagValue(s, base, value);
            b.global(c.global.at(c.gNationFlag, {nation, flag}), v);
            // Capacities used at a facility or zone also count where they are.
            if (!argument.empty()) {
                int zone = c.zones.find(argument);
                if (const auto f = s.facilities.find(argument); zone < 0 && f != s.facilities.end()) zone = c.zones.find(f->second.zone);
                if (zone >= 0) b.zone(zone, c.zone.at(c.zNationHere, {nation, flag}), v);
            }
        };
        for (const auto& [name, value] : n.turnFlags) flagged(name, value);
        for (const auto& [name, value] : n.gameFlags) flagged(name, value);
    }
    for (const auto& [nation, count] : s.completedTurns)
        if (const int n = c.nations.find(nation); n >= 0) b.global(c.global.at(c.gCompletedTurns, {n}), count);
}

void pendingFacts(const Context& c, Builder& b, int name, const V& value, int depth) {
    if (depth > 6) return;
    if (value.isString()) {
        if (const int n = c.nations.find(value.asString()); n >= 0) b.global(c.global.at(c.gPendingNation, {name, n}), 1);
    } else if (value.isNumber() || value.isBool()) {
        b.global(c.global.at(c.gPendingValue, {name}), static_cast<long>(std::lround(numberOr(&value))));
    } else if (value.isArray()) {
        for (const auto& item : value.asArray()) pendingFacts(c, b, name, item, depth + 1);
    } else if (value.isObject()) {
        for (const auto& [key, item] : value.asObject()) {
            if (const int n = c.nations.find(key); n >= 0) b.global(c.global.at(c.gPendingNation, {name, n}), 1);
            pendingFacts(c, b, name, item, depth + 1);
        }
    }
}

void encodePolitics(const Context& c, const State& s, Builder& b) {
    const auto& p = s.politics;
    b.global(c.global.at(c.gTruce, {}), p.chineseTruce);
    b.global(c.global.at(c.gTruceEnded, {}), p.trucePermanentlyEnded);
    b.global(c.global.at(c.gForeignWarPending, {}), p.foreignChinaWarPending);
    b.global(c.global.at(c.gTruceOfferPending, {}), p.truceOfferPending);
    if (p.chinaInvader) b.global(c.global.at(c.gInvader, {c.nations(*p.chinaInvader)}), 1);
    for (const auto& [warlord, attackers] : p.attackedWarlords)
        for (const auto& attacker : attackers)
            b.global(c.global.at(c.gAttackedWarlord, {c.nations(warlord), c.nations(attacker)}), 1);
    for (std::size_t i = 0; i < p.alignmentQueue.size(); ++i)
        b.global(c.global.at(c.gAlignmentQueue, {c.nations(p.alignmentQueue[i])}), static_cast<long>(i + 1));
    for (const auto& nation : p.surrendered) b.global(c.global.at(c.gSurrendered, {c.nations(nation)}), 1);
    for (const auto& nation : p.evolutionAwarded) b.global(c.global.at(c.gEvolved, {c.nations(nation)}), 1);
    for (const auto& [key, value] : p.pending) {
        std::string argument, suffix;
        auto base = withoutNation(c, baseName(key, &argument), &suffix);
        const int name = c.pendingNames(base);
        b.global(c.global.at(c.gPending, {name}), 1);
        for (const auto* nation : {&argument, &suffix})
            if (const int n = c.nations.find(*nation); n >= 0) b.global(c.global.at(c.gPendingNation, {name, n}), 1);
        pendingFacts(c, b, name, value, 0);
    }
}

void encodeClock(const Context& c, const State& s, Builder& b, const ZoneSchedule& schedule) {
    b.global(c.global.at(c.gRound, {}), s.clock.roundIndex + 1);
    b.global(c.global.at(c.gCompletedRounds, {}), s.clock.completedRounds);
    b.global(c.global.at(c.gRoundsLeft, {}), s.definition->calendarRounds - s.clock.completedRounds);
    b.global(c.global.at(c.gPhase, {c.phases(toString(s.clock.phase))}), 1);
    b.global(c.global.at(c.gTurnNation, {c.nations(s.currentNation())}), 1);
    b.global(c.global.at(c.gIncomeCollected, {}), s.clock.incomeCollected);
    b.global(c.global.at(c.gTerminal, {}), s.terminal);
    if (!s.decisions.empty()) {
        const auto& top = s.decisions.back();
        b.global(c.global.at(c.gDecisionKind, {c.decisionKinds(top.kind)}), 1);
        if (const int n = c.nations.find(top.nation); n >= 0) b.global(c.global.at(c.gDecisionNation, {n}), 1);
        b.global(c.global.at(c.gDecisionReaction, {}), top.reaction);
        b.global(c.global.at(c.gDecisionDepth, {}), static_cast<long>(s.decisions.size()));
        for (std::size_t i = 0; i + 1 < s.decisions.size(); ++i)
            b.global(c.global.at(c.gDecisionStack, {c.decisionKinds(s.decisions[i].kind)}), 1);
    }
    b.global(c.global.at(c.gAdapterKind, {c.adapterKinds(schedule.decisionKind)}), 1);
    b.global(c.global.at(c.gOwner, {c.playerOrNone(schedule.owner ? *schedule.owner : "~none")}), 1);
    if (schedule.offered) b.global(c.global.at(c.gOffered, {c.playerOrNone(*schedule.offered)}), 1);
    for (const auto& player : schedule.passed) b.global(c.global.at(c.gPassed, {c.players(player)}), 1);
    for (std::size_t i = 0; i < schedule.order.size() && i < 3; ++i)
        b.global(c.global.at(c.gOrder, {c.players(schedule.order[i]), static_cast<int>(i)}), 1);
    if (s.chance) {
        const auto& request = *s.chance;
        std::string argument;
        const auto base = baseName(request.purpose, &argument);
        b.global(c.global.at(c.gChance, {}), 1);
        b.global(c.global.at(c.gChancePurpose, {c.chancePurposes(base)}), 1);
        if (const int t = c.technologies.find(argument); t >= 0) b.global(c.global.at(c.gChanceTech, {t}), 1);
        if (const int n = c.nations.find(request.nation); n >= 0) b.global(c.global.at(c.gChanceNation, {n}), 1);
        long modifier = 0, rerolls = 0;
        for (const auto& die : request.dice) {
            modifier += die.modifier;
            rerolls += die.maxRerolls;
        }
        b.global(c.global.at(c.gChanceStat, {c.chanceStats.find("dice")}), static_cast<long>(request.dice.size()));
        if (!request.dice.empty())
            b.global(c.global.at(c.gChanceStat, {c.chanceStats.find("sides")}), request.dice.front().sides);
        b.global(c.global.at(c.gChanceStat, {c.chanceStats.find("modifier")}), modifier);
        b.global(c.global.at(c.gChanceStat, {c.chanceStats.find("rerolls")}), rerolls);
    }
    for (const auto& [name, value] : s.flags) {
        std::string argument, suffix;
        auto base = withoutNation(c, baseName(name, &argument), &suffix);
        // Sequence counters only number records; they say nothing about play.
        if (base.size() > 9 && base.compare(base.size() - 9, 9, "_sequence") == 0) continue;
        const int flag = c.recordFlags(base);
        const int n = c.nations.find(!suffix.empty() ? suffix : argument);
        if (n >= 0) b.global(c.global.at(c.gStateFlagNation, {flag, n}), flagValue(s, base, value));
        else b.global(c.global.at(c.gStateFlag, {flag}), flagValue(s, base, value));
    }
    if (s.actionInterface.isObject()) {
        if (const auto* visited = s.actionInterface.find("visited_configurations"); visited && visited->isArray())
            b.global(c.global.at(c.gVisited, {}), static_cast<long>(visited->asArray().size()));
        if (const auto* declined = s.actionInterface.find("declined_rail_requests"); declined && declined->isArray()) {
            b.global(c.global.at(c.gDeclinedRails, {}), static_cast<long>(declined->asArray().size()));
            for (const auto& item : declined->asArray())
                if (item.isString())
                    if (const int z = c.zones.find(item.asString()); z >= 0) b.zone(z, c.zone.at(c.zDeclinedRail, {}), 1);
        }
    }
}

int roleOf(const Context& c, const std::string& key) {
    const auto found = c.roleOfKey.find(key);
    return found == c.roleOfKey.end() ? 3 : found->second;
}

void optionValue(const Context& c, const State& s, Builder& b, const UnitRoles& roles, const std::string& key,
                 const V& value, int depth, bool listItem = false) {
    if (depth > 6) return;
    const int k = c.parameterKeys(key);
    const int role = roleOf(c, key);
    if (!listItem) b.option(c.action.at(c.aKey, {k}), 1, -1);
    if (value.isNull()) {
        b.option(c.action.at(c.aNull, {k}), 1, role);
    } else if (value.isBool()) {
        b.option(c.action.at(value.asBool() ? c.aTrue : c.aFalse, {k}), 1, role);
    } else if (value.isNumber()) {
        b.option(c.action.at(c.aNumber, {k}), static_cast<long>(std::lround(value.asNumber())), role);
    } else if (value.isArray()) {
        b.option(c.action.at(c.aListLength, {k}), static_cast<long>(value.asArray().size()), role);
        for (const auto& item : value.asArray()) optionValue(c, s, b, roles, key, item, depth + 1, true);
    } else if (value.isObject()) {
        for (const auto& [name, item] : value.asObject()) optionValue(c, s, b, roles, name, item, depth + 1);
    } else if (value.isString()) {
        const auto& text = value.asString();
        if (const auto u = s.units.find(text); u != s.units.end()) {
            const auto& unit = u->second;
            b.option(c.action.at(c.aUnitNationType, {role, c.nations(unit.owner), c.unitTypes(unit.type)}), 1, role);
            if (const int where = c.zones.find(unit.zone); where >= 0)
                b.option(c.action.at(c.aUnitZone, {role, where}), 1, role);
            if (const auto rank = roles.rank.find(unit.id); rank != roles.rank.end())
                b.option(c.action.at(c.aUnitRank, {role, std::min(rank->second, 7)}), 1, role);
            unitFacts(c, s, unit, roles,
                      [&](int stat, long v) { b.option(c.action.at(c.aUnitStat, {role, stat}), v, role); },
                      [&](int kind, int where, const FacilityState* facility) {
                          if (where >= 0) b.option(c.action.at(c.aUnitRefPlace, {role, kind, where}), 1, role);
                          if (!facility) return;
                          b.option(c.action.at(c.aUnitRefFacility, {role, c.facilityTypes(facility->type)}), 1, role);
                          facilityBorders(c, *facility, [&](int sea) {
                              b.option(c.action.at(c.aUnitRefBorder, {role, sea}), 1, role);
                          });
                      },
                      [](int, long) {});
            if (const int origin = c.zones.find(unit.turnOrigin); origin >= 0)
                b.option(c.action.at(c.aUnitOrigin, {role, origin}), 1, role);
            for (const auto& cargo : unit.cargo)
                if (const auto carried = s.units.find(cargo); carried != s.units.end()) {
                    const auto& load = carried->second;
                    b.option(c.action.at(c.aUnitCargo, {role, c.unitTypes(load.type)}), 1, role);
                    if (const int origin = c.zones.find(load.turnOrigin); origin >= 0)
                        b.option(c.action.at(c.aUnitCargoOrigin, {role, origin}), 1, role);
                    const auto cargoFlag = [&](const std::string& name, int value) {
                        const auto base = baseName(name);
                        b.option(c.action.at(c.aUnitCargoFlag, {role, c.actorFlags(base)}), flagValue(s, base, value), role);
                    };
                    for (const auto& name : load.commitments) cargoFlag(name, 1);
                    for (const auto& [name, value] : load.turnFlags) cargoFlag(name, value);
                    for (const auto& [name, value] : load.gameFlags) cargoFlag(name, value);
                }
            // Orders are built in ID order, so the units that may still join
            // one started with this unit are its owner's later units here.
            for (auto later = s.units.upper_bound(unit.id); later != s.units.end(); ++later)
                if (later->second.zone == unit.zone && later->second.owner == unit.owner && !later->second.carriedBy)
                    b.option(c.action.at(c.aUnitLaterPeers, {role, c.unitTypes(later->second.type)}), 1, role);
            if (unit.carriedBy)
                if (const auto carrier = s.units.find(*unit.carriedBy); carrier != s.units.end())
                    b.option(c.action.at(c.aUnitCarrier, {role, c.unitTypes(carrier->second.type)}), 1, role);
            b.zoneRef(role == 1 ? 3 : role, c.zones.find(unit.zone));
        } else if (const int zone = c.zones.find(text); zone >= 0) {
            b.option(c.action.at(c.aZone, {role, zone}), 1, role);
            b.zoneRef(role, zone);
        } else if (const auto f = s.facilities.find(text); f != s.facilities.end()) {
            const auto& facility = f->second;
            b.option(c.action.at(c.aFacility, {role, c.facilityTypes(facility.type)}), 1, role);
            b.option(c.action.at(c.aFacilityDamage, {role}), facility.damage, role);
            for (const auto& [name, flagged] : facility.flags) {
                std::string argument;
                const auto base = baseName(name, &argument);
                if (base == "border" && c.zones.find(argument) >= 0)
                    b.option(c.action.at(c.aFacilityBorder, {role, c.zones.find(argument)}), 1, role);
                else if (base != "original_owner" && base != "original_type")
                    b.option(c.action.at(c.aFacilityFlag, {role, c.recordFlags(base)}), flagValue(s, base, flagged), role);
            }
            b.zoneRef(role == 1 ? 3 : role, c.zones.find(f->second.zone));
        } else if (const auto battle = s.battles.find(text); battle != s.battles.end()) {
            const auto& record = battle->second;
            b.option(c.action.at(c.aBattleStage, {role, c.battleStages(record.stage)}), 1, role);
            if (const int n = c.nations.find(record.attacker); n >= 0) b.option(c.action.at(c.aBattleAttacker, {role, n}), 1, role);
            b.option(c.action.at(c.aBattleDefender, {role, c.nationOrNone(c.nations.find(record.defender) >= 0 ? record.defender : "~none")}), 1, role);
            for (const auto* side : {&record.attackers, &record.defenders})
                for (const auto& id : *side)
                    if (const auto u = s.units.find(id); u != s.units.end())
                        b.option(c.action.at(c.aBattleUnits, {role, c.unitTypes(u->second.type)}), 1, role);
            // Places the battle's own record names, such as the sea an assault comes from.
            std::function<void(const V&, int)> places = [&](const V& value, int level) {
                if (level > 6) return;
                if (value.isString()) {
                    if (const int z = c.zones.find(value.asString()); z >= 0) b.option(c.action.at(c.aBattleZone, {role, z}), 1, role);
                } else if (value.isArray()) {
                    for (const auto& item : value.asArray()) places(item, level + 1);
                } else if (value.isObject()) {
                    for (const auto& [key, item] : value.asObject()) places(item, level + 1);
                }
            };
            places(record.data, 0);
            b.zoneRef(role == 1 ? 3 : role, c.zones.find(record.zone));
        } else if (const auto project = s.construction.find(text); project != s.construction.end()) {
            const int type = c.projectTypes(project->second.type);
            b.option(c.action.at(c.aProject, {role, type}), 1, role);
            b.option(c.action.at(c.aProjectOwner, {role, c.nations(project->second.owner)}), 1, role);
            projectFacts(c, s, project->second, type,
                [&](int stat, long v) { b.option(c.action.at(c.aProjectStat, {role, stat}), v, role); },
                [&](int row) { b.option(c.action.at(c.aRow, {row}), 1, role); },
                [&](int flag, long v) { b.option(c.action.at(c.aProjectFlag, {role, flag}), v, role); },
                [&](int zone) { b.option(c.action.at(c.aProjectBorder, {role, zone}), 1, role); });
            if (project->second.site) b.zoneRef(role == 1 ? 3 : role, c.zones.find(*project->second.site));
        } else if (const auto rail = s.rails.find(text); rail != s.rails.end()) {
            // A railroad is described by the two zones it joins and the damage on
            // each side; one border holds at most one railroad (RCL-019).
            for (const auto& side : {rail->second.endpointA, rail->second.endpointB}) {
                const int where = c.zones.find(side);
                if (where < 0) {
                    noteUnknown("rail_endpoint", side);
                    continue;
                }
                b.option(c.action.at(c.aRailEndpoint, {role, where}), 1, role);
                if (const auto damage = rail->second.damageByEndpoint.find(side); damage != rail->second.damageByEndpoint.end())
                    b.option(c.action.at(c.aRailDamage, {role, where}), damage->second, role);
                b.zoneRef(role == 1 ? 3 : role, where);
            }
        } else if (const int row = c.rows.find(text); row >= 0) {
            b.option(c.action.at(c.aRow, {row}), 1, role);
        } else if (const int nation = c.nations.find(text); nation >= 0) {
            b.option(c.action.at(c.aNationRef, {role, nation}), 1, role);
        } else if (const int tech = c.technologies.find(text); tech >= 0) {
            b.option(c.action.at(c.aTech, {tech}), 1, role);
        } else {
            b.option(c.action.at(c.aEnum, {k, c.enumValues(text)}), 1, role);
        }
    }
}

}  // namespace

std::size_t ZoneInput::bytes() const {
    std::size_t total = 0;
    for (const auto* v : {&zoneIndex, &zoneColumn, &zoneValue, &globalColumn, &globalValue, &actionOffsets,
                          &actionColumn, &actionValue, &actionSource, &actionTarget, &pathOffsets, &pathZone})
        total += v->size() * sizeof(std::int32_t);
    return total + factorGroups.size() * sizeof(std::int32_t);
}

std::shared_ptr<const ZoneEncodingSpec> zoneEncodingSpec(const State& s) {
    auto owner = contextFor(s);
    const auto* spec = &owner->spec;
    return std::shared_ptr<const ZoneEncodingSpec>(std::move(owner), spec);
}

ZoneInput encodeZoneInput(const State& s, const ZoneSchedule& schedule, const std::vector<ZoneOption>& options) {
    const auto owner = contextFor(s);
    const auto& c = *owner;
    Builder b(c);
    UnitRoles roles;
    rankUnits(s, roles);
    encodeBattles(c, s, b, roles);
    encodeTerritories(c, s, b);
    encodeUnits(c, s, b, roles);
    encodeFacilities(c, s, b);
    encodeProjects(c, s, b);
    encodeRepairs(c, s, b);
    encodeRails(c, s, b);
    encodeNations(c, s, b);
    encodePolitics(c, s, b);
    encodeClock(c, s, b, schedule);
    ZoneInput out;
    b.finishPosition(out);
    for (const auto& option : options) {
        b.option(c.action.at(c.aScheduleKind, {c.scheduleKinds(option.kind)}), 1, -1);
        b.option(c.action.at(c.aPlayer, {c.playerOrNone(option.player.empty() ? "~none" : option.player)}), 1, -1);
        std::string kind = option.kind;
        if (option.action) {
            const auto& action = *option.action;
            b.option(c.action.at(c.aKind, {c.actionKinds(action.kind)}), 1, -1);
            if (const int n = c.nations.find(action.nation); n >= 0) b.option(c.action.at(c.aNation, {n}), 1, -1);
            if (action.decision) b.option(c.action.at(c.aDecision, {}), 1, -1);
            if (action.parameters.isObject())
                for (const auto& [key, value] : action.parameters.asObject()) optionValue(c, s, b, roles, key, value, 0);
            kind += ":" + action.kind;
        }
        b.finishOption(out, kind);
    }
    b.finishGroups(out);
    return out;
}

std::map<std::string, long> zoneEncodingUnknowns(bool reset) {
    const std::lock_guard lock(unknownMutex);
    auto result = unknownNames;
    if (reset) unknownNames.clear();
    return result;
}

}  // namespace game::campaign
