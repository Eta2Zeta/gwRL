#include "game/catalog.hpp"

#include <algorithm>
#include <functional>
#include <iostream>
#include <stdexcept>

namespace {
using namespace game::campaign;
using V = game::json::Value;
const auto root = std::filesystem::path(GWRL_SOURCE_DIR);

void check(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}
void rejects(const std::function<void()>& operation, const std::string& message) {
    try { operation(); } catch (const std::exception&) { return; }
    throw std::runtime_error(message);
}
CatalogContext japan() {
    CatalogContext c;
    c.nation = "japan";
    c.powerStatus = "major";
    return c;
}
CatalogContext eligibleContext(const BuildChartRow& row) {
    CatalogContext c;
    c.nation = row.nation;
    c.powerStatus = row.powerStatus;
    const int date = row.availableFrom.value_or(193607);
    c.year = date / 100;
    c.month = date % 100;
    c.technologies = row.requiredTechnologies;
    for (const auto& flag : row.requiredFlags) c.flags[flag] = true;
    for (const auto& flag : row.placement) c.flags[flag] = true;
    return c;
}
const CatalogMode& mode(const std::vector<CatalogMode>& modes, const Id& id) {
    const auto found = std::find_if(modes.begin(), modes.end(), [&](const auto& x) { return x.id == id; });
    check(found != modes.end(), "Missing mode: " + id);
    return *found;
}
bool hasMode(const std::vector<CatalogMode>& modes, const Id& id) {
    return std::any_of(modes.begin(), modes.end(), [&](const auto& x) { return x.id == id; });
}
const V& rule(const V& rules, const Id& id) {
    for (const auto& r : rules.asArray()) if (r.require("id").asString() == id) return r.require("parameters");
    throw std::runtime_error("Missing structured rule: " + id);
}
bool hasRule(const V& rules, const Id& id) {
    return std::any_of(rules.asArray().begin(), rules.asArray().end(),
        [&](const auto& r) { return r.require("id").asString() == id; });
}
std::set<std::vector<int>> prices(const Catalog& catalog, const Id& row, const CatalogContext& c) {
    std::set<std::vector<int>> result;
    std::set<std::string> methods;
    for (const auto& option : catalog.priceOptions(row, c)) {
        check(methods.insert(option.method).second, "Duplicate construction method");
        result.insert(option.payments);
    }
    return result;
}

void coverageAndEveryPrintedRow(const Catalog& catalog) {
    check(catalog.units().size() == 53, "Expected 37 land/air and 16 naval unit types");
    check(catalog.sourceData().require("land_air").require("units").asArray().size() == 37,
          "Land/air source coverage changed");
    check(catalog.sourceData().require("naval").require("units").asArray().size() == 16,
          "Naval source coverage changed");
    check(catalog.facilities().size() == 15 && catalog.technologies().size() == 16,
          "Facility/technology coverage incomplete");
    catalog.requireComplete();
    check(catalog.unresolvedFields().empty(), "Unresolved source values survived M3 certification");
    const auto restored = Catalog::fromJson(catalog.sourceData());
    check(restored->fingerprint() == catalog.fingerprint(), "In-memory catalog reconstruction changed identity");

    const auto& coverage = catalog.sourceData().require("build_charts").require("coverage");
    check(coverage.require("printed_purchase_row_count").asInt() == 181, "Printed row count changed");
    std::set<Id> printed;
    std::map<std::pair<Id, std::string>, int> totals;
    for (const auto& value : coverage.require("printed_purchase_row_ids").asArray()) {
        const auto id = value.asString();
        check(printed.insert(id).second, "Printed source row counted twice: " + id);
        const auto& row = catalog.row(id);
        ++totals[{row.nation, row.powerStatus}];
        check(row.kind == "purchase" && !row.derivedFrom, "Printed row became a derived upgrade: " + id);
        auto c = eligibleContext(row);
        check(catalog.purchaseEligibility(id, c).allowed, "Source row rejected in its eligible context: " + id);
        check(catalog.placementEligibility(id, c).allowed, "Satisfied placement rejected: " + id);
        check(!row.sourceRefs.asArray().empty(), "Printed row lacks source citation: " + id);

        auto invalid = c;
        invalid.nation = "unlisted_nation";
        check(!catalog.purchaseEligibility(id, invalid).allowed, "Wrong nation can buy: " + id);
        invalid = c;
        invalid.powerStatus = c.powerStatus == "major" ? "minor" : "major";
        check(!catalog.purchaseEligibility(id, invalid).allowed, "Wrong power status can buy: " + id);
        for (const auto& tech : row.requiredTechnologies) {
            invalid = c;
            invalid.technologies.erase(tech);
            check(!catalog.purchaseEligibility(id, invalid).allowed, "Missing technology accepted: " + id);
        }
        for (const auto& tech : row.forbiddenTechnologies) {
            invalid = c;
            invalid.technologies.insert(tech);
            check(!catalog.purchaseEligibility(id, invalid).allowed, "Superseded purchase accepted: " + id);
        }
        for (const auto& flag : row.requiredFlags) {
            invalid = c;
            invalid.flags.erase(flag);
            check(!catalog.purchaseEligibility(id, invalid).allowed, "Unknown prerequisite treated as true: " + id);
            invalid.flags[flag] = true;
            invalid.disabledFlags.insert(flag);
            check(!catalog.purchaseEligibility(id, invalid).allowed, "Campaign exclusion overridden: " + id);
        }
        for (const auto& flag : row.placement) {
            invalid = c;
            invalid.flags.erase(flag);
            check(!catalog.placementEligibility(id, invalid).allowed, "Unknown placement predicate accepted: " + id);
        }
        if (row.cap) {
            check(catalog.purchaseEligibility(id, c, *row.cap).allowed, "Exact cap rejected: " + id);
            check(!catalog.purchaseEligibility(id, c, *row.cap + 1).allowed, "Over-cap batch accepted: " + id);
            c.purchases[row.capGroup.value_or(id)] = *row.cap;
            check(!catalog.purchaseEligibility(id, c).allowed, "Prior purchases ignored: " + id);
        }
    }
    check(printed.size() == 181, "Printed row inventory incomplete");
    for (const auto& nation : {"japan", "kmt", "ccp"})
        check(totals[{nation, "major"}] == 57, "Major-power chart lost a printed row");
    check(totals[{"kmt", "minor"}] == 5 && totals[{"ccp", "minor"}] == 5,
          "Chinese minor chart coverage incomplete");
}

void purchaseBoundariesAndForeignExclusion(const Catalog& catalog) {
    auto c = japan();
    c.year = 1939;
    check(catalog.purchaseEligibility("japan_major_cavalry", c).allowed, "July 1939 cavalry sunset is exclusive");
    for (const auto& type : {"mechanized_infantry", "tank_destroyer", "medium_armor", "strategic_bomber"}) {
        const std::string id = std::string("japan_major_") + type;
        check(!catalog.purchaseEligibility(id, c).allowed, "January 1940 unit available early: " + id);
        auto next = c;
        next.year = 1940;
        next.month = 1;
        check(catalog.purchaseEligibility(id, next).allowed, "January 1940 unit still unavailable: " + id);
    }
    c.year = 1940;
    c.month = 1;
    check(!catalog.purchaseEligibility("japan_major_cavalry", c).allowed, "Major cavalry remained purchasable after 1939");
    c.nation = "kmt";
    c.powerStatus = "minor";
    check(catalog.purchaseEligibility("kmt_minor_cavalry", c).allowed, "Minor cavalry incorrectly shares major sunset");
    check(!catalog.purchaseEligibility("kmt_minor_artillery", c).allowed, "Burma Road prerequisite omitted");
    c.flags["kmt_burma_road"] = true;
    check(catalog.purchaseEligibility("kmt_minor_artillery", c).allowed, "Explicit external prerequisite ignored");
    c.disabledFlags.insert("kmt_burma_road");
    check(!catalog.purchaseEligibility("kmt_minor_artillery", c).allowed, "Closed-theatre exclusion ignored");

    c = japan();
    c.purchases["airborne_infantry"] = 1;
    check(catalog.purchaseEligibility("japan_major_airborne_infantry", c).allowed, "Second airborne purchase rejected");
    c.technologies.insert("airborne_doctrine");
    check(!catalog.purchaseEligibility("japan_major_airborne_infantry", c).allowed, "Old airborne row not replaced");
    check(catalog.purchaseEligibility("japan_major_elite_airborne_infantry", c).allowed, "Elite replacement unavailable");
    check(!catalog.purchaseEligibility("japan_major_elite_airborne_infantry", c, 2).allowed,
          "Airborne and elite purchases do not share their cap");
    rejects([&] { catalog.purchaseEligibility("japan_major_infantry", c, 0); }, "Zero purchase count accepted");

    const std::set<Id> excluded {"torpedo_boat_destroyer", "coastal_defense_ship", "coastal_submarine",
        "colonial_infantry", "foreign_legion", "gurkha", "panzergrenadier", "t_34", "tiger_i",
        "katyusha_rocket_artillery", "b_29"};
    for (const auto& id : excluded) (void)catalog.unit(id);
    for (const auto& [id, row] : catalog.rows())
        check(!excluded.contains(row.type), "Source-only foreign/setup unit gained a campaign purchase row: " + id);
    for (const auto& id : {"torpedo_boat_destroyer", "coastal_defense_ship", "coastal_submarine"})
        check(!catalog.unit(id).assetValue && catalog.unit(id).purchaseCosts.empty(),
              "Unpriced source unit was assigned a generic purchase price");
    c.nation = "mongolia";
    c.powerStatus = "controlled_minor_not_incorporated";
    check(catalog.purchaseOptions(c).empty(), "Mongolia acquired an invented national build chart");
}

void modesAndConditionalStats(const Catalog& catalog) {
    auto c = japan();
    const auto aa = catalog.stats("anti_aircraft_artillery", 0, c);
    check(!aa.attack && !aa.defense && aa.attackDice == 0 && aa.defenseDice == 0,
          "AAA became an ordinary land combat roll");
    const auto aaModes = catalog.modes("anti_aircraft_artillery", c);
    const auto& fire = mode(aaModes, "anti_aircraft_fire");
    check(fire.threshold == 3 && fire.dieSides == 12 && fire.dice == 0,
          "AAA dynamic dice definition changed");
    check(fire.parameters.require("maximum_dice").asInt() == 3
              && fire.parameters.require("dice_formula").asString() == "min(enemy_aircraft_count,3)"
              && fire.parameters.require("rounds").asArray().size() == 1
              && fire.parameters.require("rounds").asArray()[0].asInt() == 1,
          "AAA three-aircraft/first-round limit lost");
    check(!catalog.stats("strategic_bomber", 0, c).attack, "Carpet bombing became unconditional attack");
    check(!hasMode(catalog.modes("strategic_bomber", c), "carpet_bombing"), "Carpet bombing lacks technology gate");
    c.technologies.insert("heavy_strategic_bombers");
    const auto ordinary = catalog.modes("strategic_bomber", c);
    const auto heavy = catalog.modes("heavy_strategic_bomber", c);
    check(mode(ordinary, "carpet_bombing").dice == 3 && mode(heavy, "carpet_bombing").dice == 5
              && mode(heavy, "carpet_bombing").threshold == 2,
          "Carpet bombing multi-die thresholds changed");
    check(mode(ordinary, "strategic_bombing").dieSides == 6 && mode(ordinary, "strategic_bombing").dice == 2
              && mode(heavy, "strategic_bombing").dice == 3,
          "Strategic bombing damage dice confused with carpet combat dice");
    const auto fighterModes = catalog.modes("fighter", c);
    check(mode(fighterModes, "interception").threshold == 3
              && mode(fighterModes, "interception").parameters.require("radar_bonus").asInt() == 1,
          "Interception/Radar source parameters lost");

    c = japan();
    check(catalog.stats("militia", 0, c).movement == 0, "Unknown homeland predicates grant militia movement");
    for (const auto& id : {"owner_is_major_power", "movement_starts_in_owner_home_country",
                           "movement_ends_in_owner_home_country"}) c.flags[id] = true;
    check(catalog.stats("militia", 0, c).movement == 1, "Major home-country militia movement missing");
    for (const auto& id : {"owner_is_major_power", "movement_starts_in_owner_home_country",
                           "movement_ends_in_owner_home_country"}) {
        auto blocked = c;
        blocked.flags[id] = false;
        check(catalog.stats("militia", 0, blocked).movement == 0, "Militia movement ignored predicate: " + std::string(id));
    }
    c = japan();
    c.technologies.insert("long_range_aircraft");
    check(catalog.stats("fighter", 0, c).movement == 5 && catalog.stats("air_transport", 0, c).movement == 7
              && catalog.stats("seaplane", 0, c).movement == 7 && catalog.stats("infantry", 0, c).movement == 1,
          "Long-range technology did not apply precisely to existing aircraft");
    c.technologies.insert("anti_submarine_warfare");
    check(catalog.stats("seaplane", 0, c).attack == 3, "ASW bonus applied outside patrol");
    c.flags["on_maritime_air_patrol"] = true;
    check(catalog.stats("seaplane", 0, c).attack == 3, "ASW bonus applied against non-submarine targets");
    c.flags["target_is_submarine"] = true;
    check(catalog.stats("seaplane", 0, c).attack == 5 && catalog.stats("fighter", 0, c).attack == 6,
          "ASW conditional modifier targets wrong aircraft");
    const auto mediumPatrol = catalog.modes("medium_bomber", c);
    const auto seaplanePatrol = catalog.modes("seaplane", c);
    check(mode(mediumPatrol, "maritime_air_patrol").parameters.require("range").asInt() == 2
              && mode(seaplanePatrol, "maritime_air_patrol").parameters.require("range").asInt() == 2,
          "Long-range patrol bonus ignored its seaplane-base condition");
    c.flags["starts_at_seaplane_base"] = true;
    const auto basedPatrol = catalog.modes("seaplane", c);
    check(mode(basedPatrol, "maritime_air_patrol").parameters.require("range").asInt() == 3,
          "Long-range seaplane patrol from base did not gain range");
    c.technologies.insert("radar");
    const auto radarFighter = catalog.modes("fighter", c);
    const auto radarBomber = catalog.modes("strategic_bomber", c);
    check(mode(radarFighter, "interception").threshold == 4 && mode(radarBomber, "interception").threshold == 2,
          "Completed Radar did not add one to interception thresholds");
}

void technologyAndConstruction(const Catalog& catalog) {
    const std::set<Id> thresholdSeven {"advanced_mechanized_infantry", "advanced_artillery", "radar",
        "anti_submarine_warfare", "improved_factories", "improved_construction", "airborne_doctrine", "amphibious_doctrine"};
    for (const auto& [id, tech] : catalog.technologies()) {
        const int threshold = thresholdSeven.contains(id) ? 7 : (id == "heavy_strategic_bombers" || id == "strategic_rockets" ? 9 : 8);
        check(tech.thresholds == std::vector<int>(4, threshold) && tech.stageThreeFrom == 193907,
              "Research chart thresholds or Stage III date changed: " + id);
    }
    auto c = japan();
    check(catalog.automaticConversions("airborne_infantry", c).empty(), "Airborne converted without doctrine");
    c.technologies.insert("airborne_doctrine");
    const auto converted = catalog.automaticConversions("airborne_infantry", c);
    check(converted.size() == 1 && converted[0].to == "elite_airborne_infantry"
              && converted[0].costIpp == 0 && converted[0].automatic,
          "Airborne Doctrine conversion absent, duplicated or charged");
    c.technologies.insert("advanced_mechanized_infantry");
    check(catalog.automaticConversions("mechanized_infantry", c).empty(), "Unstated automatic mechanized upgrade invented");

    c = japan();
    check(prices(catalog, "japan_major_heavy_cruiser", c) == std::set<std::vector<int>> {{5, 5}}, "Printed cruiser payments changed");
    c.technologies.insert("improved_construction");
    check(prices(catalog, "japan_major_heavy_cruiser", c) == std::set<std::vector<int>> {{5, 5}, {4, 4}, {10}},
          "Cruiser discount and acceleration combined or mispriced");
    check(prices(catalog, "japan_major_fleet_carrier", c) == std::set<std::vector<int>> {{5, 5, 5}, {4, 4, 4}, {10, 5}},
          "Three-stage carrier acceleration/discount wrong");
    check(prices(catalog, "japan_major_major_factory", c) == std::set<std::vector<int>> {{6, 6, 6}, {5, 5, 5}, {12, 6}},
          "Facility construction choices wrong");
    check(prices(catalog, "japan_major_minor_factory_to_medium_factory", c) == std::set<std::vector<int>> {{7}, {6}},
          "Improved Construction does not cover facility upgrades");
    check(prices(catalog, "japan_major_infantry", c) == std::set<std::vector<int>> {{3}}
              && prices(catalog, "japan_major_fighter", c) == std::set<std::vector<int>> {{10}},
          "Improved Construction discounts land or air units");
    check(catalog.unit("fleet_carrier").assetValue == 15 && catalog.facility("major_factory").assetValue == 18,
          "Discounted construction changed completed asset values");
    const auto& construction = rule(catalog.technology("improved_construction").rules, "improved_construction_choice");
    check(construction.require("mutually_exclusive").asBool(), "Construction alternatives lost explicit exclusivity");

    c = japan();
    const std::map<Id, std::pair<int, int>> capacities {{"minor_factory", {1, 2}}, {"medium_factory", {3, 5}},
        {"major_factory", {5, 8}}, {"minor_shipyard", {1, 2}}, {"major_shipyard", {5, 8}}};
    for (const auto& [id, values] : capacities) {
        check(catalog.productionCapacity(id, 0, c) == values.first, "Printed production capacity wrong: " + id);
        auto improved = c;
        improved.technologies.insert("improved_factories");
        check(catalog.productionCapacity(id, 0, improved) == values.second
                  && catalog.productionCapacity(id, 1, improved) == (id == "major_factory" ? 7 : 0),
              "Improved or damaged production capacity wrong: " + id);
    }
    c.technologies.insert("improved_factories");
    check(prices(catalog, "japan_major_major_factory", c) == std::set<std::vector<int>> {{6, 6, 6}},
          "Improved Factories incorrectly discounts construction");
    check(catalog.repairCapacity("minor_dockyard", 0) == 1 && catalog.repairCapacity("major_dockyard", 0) == 5
              && catalog.repairCapacity("major_shipyard", 0) == 5 && catalog.repairCapacity("major_shipyard", 1) == 0,
          "Repair capacity or damage disabling wrong");
    check(catalog.productionCapacity("major_factory", 2, japan()) == 3
              && catalog.productionCapacity("major_factory", 8, japan()) == 0
              && catalog.productionCapacity("major_factory", 2, c) == 6,
          "Major factory damage must subtract capacity, with a zero floor");
    for (const auto& id : {"minor_dockyard", "minor_shipyard"})
        check(catalog.repairCapacity(id, 0, c) == 2 && catalog.repairCapacity(id, 1, c) == 0,
              "Improved minor naval facility repair capacity wrong");
    for (const auto& id : {"major_dockyard", "major_shipyard"})
        check(catalog.repairCapacity(id, 0, c) == 8 && catalog.repairCapacity(id, 1, c) == 0,
              "Improved major naval facility repair capacity wrong");
}

void nationalRuleScopes(const Catalog& catalog) {
    // These are retained conditional handlers for later combat milestones,
    // not unconditional changes to shared unit stats.
    for (const auto& [id, unit] : catalog.units()) {
        const auto& surprise = rule(unit.rules, "japanese_surprise_attack_defense");
        check(surprise.require("defense_modifier").asInt() == -1
                  && surprise.require("defense_modifier_rounds").asArray().size() == 1
                  && surprise.require("defense_modifier_rounds").asArray()[0].asInt() == 1
                  && surprise.require("trigger").asString() == "first_japanese_declaration_of_war_against_an_allied_major_power"
                  && !surprise.require("scrambling_into_affected_combat_allowed").asBool()
                  && !surprise.require("inherent_facility_aaa_defends_in_affected_port_attack").asBool()
                  && !surprise.require("three_round_city_combat_limit_applies").asBool(),
              "Surprise Attack scope/effects incomplete: " + id);
        check(hasRule(unit.rules, "japanese_dug_in_defense") == unit.classes.contains("infantry_class"),
              "Dug In Defense attached to wrong unit class: " + id);
        check(hasRule(unit.rules, "japanese_surprise_attack_aircraft") == unit.classes.contains("aircraft"),
              "Surprise aircraft first strike attached to wrong unit class: " + id);
        check(hasRule(unit.rules, "kmt_low_morale") == (id == "infantry" || id == "cavalry"),
              "Low Morale attached beyond regular infantry and cavalry: " + id);
    }
    const auto& dugIn = rule(catalog.unit("infantry").rules, "japanese_dug_in_defense");
    check(dugIn.require("owner_nation").asString() == "japan" && dugIn.require("defense_bonus").asInt() == 1,
          "Dug In Defense national restriction missing");
    const auto& aircraft = rule(catalog.unit("fighter").rules, "japanese_surprise_attack_aircraft");
    check(aircraft.require("first_strike").asBool()
              && aircraft.require("combat_movement_bonus_if_embarked_on_carrier").asInt() == 1
              && aircraft.require("movement_bonus_requires_reaching_selected_surprise_attack_zone").asBool(),
          "Carrier aircraft surprise movement/first strike lost");
    const auto& morale = rule(catalog.unit("infantry").rules, "kmt_low_morale");
    check(morale.require("owner_power_status").asString() == "minor"
              && morale.require("retreat_on_roll_at_least").asInt() == 10
              && morale.require("roll_even_if_no_defending_units").asBool()
              && !morale.require("forced_retreat_units_may_be_taken_as_casualties").asBool()
              && morale.require("ceases_immediately_on_major_power_evolution").asBool(),
          "Low Morale timing or casualty restrictions lost");
    check(catalog.stats("infantry", 0, japan()).defense == 4 && catalog.stats("fighter", 0, japan()).defense == 6,
          "Conditional national abilities changed ordinary shared stats");
}

void navalDamage(const Catalog& catalog) {
    const auto c = japan();
    const auto battleship = catalog.stats("battleship", 1, c);
    check(battleship.attack == 6 && battleship.defense == 6 && battleship.bombardment == 2 && battleship.movement == 1,
          "Approved battleship damage ruling changed");
    const auto first = catalog.stats("heavy_battleship", 1, c);
    const auto second = catalog.stats("heavy_battleship", 2, c);
    check(first.attack == 8 && first.defense == 8 && first.bombardment == 3 && first.movement == 2
              && second.attack == 6 && second.defense == 6 && second.bombardment == 1 && second.movement == 2,
          "Heavy battleship per-hit fire reduction or flat movement penalty wrong");
    const auto battleshipModes = catalog.modes("battleship", c, 1);
    const auto heavyModes = catalog.modes("heavy_battleship", c, 2);
    check(mode(battleshipModes, "shore_bombardment").threshold == 2
              && mode(battleshipModes, "shore_bombardment").dice == 1
              && mode(heavyModes, "shore_bombardment").threshold == 1
              && mode(heavyModes, "shore_bombardment").dice == 1,
          "Combat-mode query ignored damaged shore-bombardment stats");
    for (const auto& id : {"fleet_carrier", "heavy_fleet_carrier"}) {
        const auto intact = catalog.stats(id, 0, c);
        const auto damaged = catalog.stats(id, 1, c);
        check(!damaged.attack && damaged.attackDice == 0 && damaged.defense == 1 && damaged.movement == 2
                  && damaged.carrierCapacity == intact.carrierCapacity,
              "Carrier damage invented attack or aircraft-capacity loss");
    }
    rejects([&] { catalog.stats("heavy_battleship", 3, c); }, "Destroyed ship has surviving stats");
    const auto& resolution = catalog.sourceData().require("naval").require("source_review").require("capital_damage_resolution");
    check(resolution.require("authority_id").asString() == "user_naval_damage_2026_10_21",
          "User ruling was relabeled as printed source certainty");
}

void scenarioIntegration(const Catalog& catalog) {
    auto state = loadScenario(root / "game_content/scenarios/japan_china_1936");
    check(state.definition->catalog && state.definition->catalog->fingerprint() == catalog.fingerprint(),
          "Campaign does not share the certified catalog");
    for (const auto& [id, unit] : state.units)
        check(unit.movementAllowance && unit.movementRemaining, "Starting unit lacks catalog movement: " + id);
    check(completedAssetValue(*state.definition, "torpedo_boat_destroyer") == 5
              && completedAssetValue(*state.definition, "coastal_submarine") == 4
              && completedAssetValue(*state.definition, "fleet_carrier") == 15,
          "Setup-only valuation overrides or printed completed value changed");
    rejects([&] { completedAssetValue(*state.definition, "coastal_defense_ship"); }, "Unapproved setup-only value guessed");

    auto& nation = state.nations.at("japan");
    nation.technologyStages["long_range_aircraft"] = 3;
    check(!catalogContext(state, "japan").technologies.contains("long_range_aircraft"), "Stage III treated as completed technology");
    nation.technologyStages["long_range_aircraft"] = 4;
    check(catalogContext(state, "japan").technologies.contains("long_range_aircraft"), "Completed technology absent from query context");
    nation.turnFlags["purchased:marine"] = 2;
    check(!catalog.purchaseEligibility("japan_major_marine", catalogContext(state, "japan")).allowed,
          "State purchase accounting not exposed to catalog");
    state.nations.at("ccp").gameFlags["ccp_soviet_rail_production"] = 1;
    const auto ccp = catalogContext(state, "ccp");
    check(!catalog.purchaseEligibility("ccp_minor_artillery", ccp).allowed,
          "Mongolia/control flag bypasses absent Soviet railroad");
    state.nations.at("kmt").gameFlags["kmt_burma_road"] = 1;
    check(!catalog.purchaseEligibility("kmt_minor_artillery", catalogContext(state, "kmt")).allowed,
          "Burma exclusion bypassed by a saved flag");

    Id land, sea;
    for (const auto& [id, node] : state.definition->geography.require("nodes").asObject()) {
        if (node.require("type").asString() == "land" && land.empty()) land = id;
        if (node.require("type").asString() == "sea" && sea.empty()) sea = id;
    }
    check(!land.empty() && !sea.empty(), "Scenario fixture lacks both zone kinds");
    state.units.clear();
    for (const auto& [type, definition] : catalog.units()) {
        for (const auto& [damage, stats] : definition.states) {
            UnitState u;
            u.id = "catalog_" + type + "_" + std::to_string(damage);
            u.type = type;
            u.owner = "japan";
            u.zone = definition.classes.contains("naval") ? sea : land;
            u.turnOrigin = u.zone;
            u.damage = damage;
            u.movementAllowance = catalog.stats(type, damage, catalogContext(state, u.owner, u.zone)).movement;
            u.movementRemaining = u.movementAllowance;
            state.units.emplace(u.id, u);
        }
    }
    state.validate();
    const auto serialized = state.serialize();
    const auto copy = State::fromJson(state.definition, game::json::parse(serialized));
    check(copy.serialize() == serialized, "Catalog unit/damage states did not round trip");
    const auto observation = copy.observation();
    for (const auto& [id, unit] : state.units) {
        const auto& observed = observation.require("units").require(id);
        check(observed.require("type").asString() == unit.type && observed.require("damage").asInt() == unit.damage,
              "Policy observation dropped type/damage identity: " + id);
    }
    auto invalid = state.clone();
    invalid.units.begin()->second.type = "invented_type";
    rejects([&] { invalid.validate(); }, "Unknown unit type accepted in campaign state");
    rejects([&] { State::fromJson(invalid.definition, invalid.toJson()); }, "Unknown unit accepted on restore");
    invalid = state.clone();
    invalid.units.at("catalog_heavy_battleship_2").damage = 3;
    rejects([&] { invalid.validate(); }, "Destroyed damage state accepted in campaign state");
    invalid = state.clone();
    invalid.facilities.begin()->second.type = "invented_facility";
    rejects([&] { invalid.validate(); }, "Unknown facility type accepted in campaign state");
}
}  // namespace

int main() {
    try {
        const auto catalog = Catalog::load(root / "game_content/catalog/gw36_v43");
        const std::vector<std::pair<std::string, std::function<void()>>> tests {
            {"catalog coverage and every printed national purchase row", [&] { coverageAndEveryPrintedRow(*catalog); }},
            {"date/status/shared-cap boundaries and foreign exclusions", [&] { purchaseBoundariesAndForeignExclusion(*catalog); }},
            {"AAA, bomber modes, militia and conditional technology stats", [&] { modesAndConditionalStats(*catalog); }},
            {"research, conversion, mutually exclusive prices and facility capacities", [&] { technologyAndConstruction(*catalog); }},
            {"approved capital-ship damage states", [&] { navalDamage(*catalog); }},
            {"conditional national-rule scope", [&] { nationalRuleScopes(*catalog); }},
            {"scenario integration and every surviving catalog state round trip", [&] { scenarioIntegration(*catalog); }}
        };
        for (const auto& [name, test] : tests) { test(); std::cout << "PASS " << name << '\n'; }
        return 0;
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
