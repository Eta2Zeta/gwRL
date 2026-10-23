#include "game/campaign.hpp"
#include "game/catalog.hpp"

#include <algorithm>
#include <fstream>
#include <iterator>
#include <sstream>
#include <stdexcept>

namespace game::campaign {
namespace {

struct Source {
    json::Value document;
    std::string bytes;
};

Source readSource(const std::filesystem::path& path) {
    std::ifstream stream(path, std::ios::binary);
    if (!stream) throw std::runtime_error("Unable to open campaign source: " + path.string());
    std::string bytes((std::istreambuf_iterator<char>(stream)), std::istreambuf_iterator<char>());
    return {json::parse(bytes), std::move(bytes)};
}

std::optional<Id> optionalId(const json::Value* value) {
    if (!value || value->isNull()) return std::nullopt;
    return value->asString();
}

int integerOr(const json::Value& record, const std::string& name, int fallback) {
    const auto* value = record.find(name);
    return value ? value->asInt() : fallback;
}

void verifyIndexSource(const json::Value& index, const std::string& name, const Source& source) {
    const auto& expected = index.require("sources").require(name).require("sha256").asString();
    if (contentDigest(source.bytes) != expected) {
        throw std::runtime_error("Stale M1 faction index: source hash differs for " + name);
    }
}

void addUnits(State& state, const Id& owner, const Id& zone, const json::Value& rows) {
    for (const auto& row : rows.asArray()) {
        const Id type = row.require("type").asString();
        const int count = row.require("count").asInt();
        if (count < 0) throw std::runtime_error("Negative setup unit count");
        const auto explicitId = optionalId(row.find("instance_id"));
        if (explicitId && count != 1) throw std::runtime_error("A setup instance ID must describe one unit");
        for (int index = 0; index < count; ++index) {
            UnitState unit;
            unit.type = type;
            unit.owner = owner;
            unit.zone = zone;
            unit.turnOrigin = zone;
            unit.damage = integerOr(row, "damage_points", 0);
            unit.carriedBy = optionalId(row.find("embarked_on"));
            if (explicitId) unit.id = *explicitId;
            else {
                const Id prefix = "setup_" + owner + "_" + zone + "_" + type + "_";
                int ordinal = index + 1;
                do { unit.id = prefix + std::to_string(ordinal++); } while (state.units.contains(unit.id));
            }
            if (!state.units.emplace(unit.id, unit).second) {
                throw std::runtime_error("Duplicate setup unit ID: " + unit.id);
            }
        }
    }
}

}  // namespace

State loadScenario(const std::filesystem::path& directory) {
    const Source map = readSource(directory / "map.json");
    const Source contract = readSource(directory / "m0/scenario_contract.json");
    const Source japan = readSource(directory / "m0/japan_setup.json");
    const Source china = readSource(directory / "m0/china_minor_setup.json");
    const Source index = readSource(directory / "m1/faction_index.json");
    const Source home = readSource(directory / "../../maps/gw36_nation_home_country.json");
    const Source politics = readSource(directory / "../../rules/gw36_politics_v43.json");
    const Source movement = readSource(directory / "../../rules/gw36_movement_v43.json");
    const Source landCombat = readSource(directory / "../../rules/gw36_land_combat_v43.json");
    const Source economy = readSource(directory / "../../rules/gw36_economy_v43.json");
    const Source air = readSource(directory / "../../rules/gw36_air_v43.json");
    const Source naval = readSource(directory / "../../rules/gw36_naval_v43.json");
    const auto repository=std::filesystem::absolute(directory).lexically_normal().parent_path().parent_path().parent_path();
    for(const auto& source:politics.document.require("sources").asArray()) {
        const auto* kind=source.find("kind");
        const auto id=source.require("id").asString();
        if(kind&&(kind->asString()=="map_artwork"||kind->asString()=="map_artwork_crop"))continue;
        // Generation evidence stays in the source profile; execution consumes
        // the reviewed homeland lists and the retained scenario sources below.
        if(id=="world_map")continue;
        const Source* loaded=id=="home_country_table"?&home:id=="faction_index"?&index:id=="scenario_contract"?&contract:nullptr;
        if(loaded) {
            if(contentDigest(loaded->bytes)!=source.require("sha256").asString())throw std::runtime_error("Stale political input: "+id);
            continue;
        }
        if(const auto* path=source.find("path")) {
            std::ifstream stream(repository/path->asString(),std::ios::binary);
            if(!stream)throw std::runtime_error("Missing political source: "+path->asString());
            const std::string bytes((std::istreambuf_iterator<char>(stream)),std::istreambuf_iterator<char>());
            if(contentDigest(bytes)!=source.require("sha256").asString())throw std::runtime_error("Stale political source: "+path->asString());
        }
    }
    for(const auto* profile:{&movement.document,&landCombat.document,&economy.document,&air.document,&naval.document})for(const auto& source:profile->require("sources").asArray()) {
        // Artwork is generation evidence; the reviewed overlay is consumed at runtime.
        const auto id=source.require("id").asString();
        if(id=="map"||!source.find("path"))continue;
        const Source* loaded=id=="scenario_contract"?&contract:id=="home_country_table"?&home:id=="faction_index"?&index:nullptr;
        if(loaded){if(contentDigest(loaded->bytes)!=source.require("sha256").asString())throw std::runtime_error("Stale campaign rule input: "+id);continue;}
        const auto path=repository/source.require("path").asString();
        std::ifstream input(path,std::ios::binary);if(!input)throw std::runtime_error("Missing campaign rule source: "+path.string());
        const std::string bytes((std::istreambuf_iterator<char>(input)),std::istreambuf_iterator<char>());
        if(contentDigest(bytes)!=source.require("sha256").asString())throw std::runtime_error("Stale campaign rule source: "+path.string());
    }
    verifyIndexSource(index.document, "theatre_map", map);
    verifyIndexSource(index.document, "japan_setup", japan);
    verifyIndexSource(index.document, "china_setup", china);
    if (!contract.document.require("pending_decisions").asArray().empty()) {
        throw std::runtime_error("Campaign contract still has pending decisions");
    }

    Definition definition;
    definition.scenarioId = contract.document.require("scenario_id").asString();
    definition.catalog = Catalog::load(directory / "../../catalog/gw36_v43");
    for (const auto* value : {&map.document.require("_meta"), &japan.document, &index.document}) {
        if (value->require("scenario_id").asString() != definition.scenarioId) {
            throw std::runtime_error("Campaign source scenario IDs disagree");
        }
    }
    definition.geography = map.document;
    definition.rules = json::Value::Object {
        {"scenario_contract", contract.document},
        {"home_country", home.document},
        {"faction_index", index.document},
        {"politics", politics.document},
        {"movement_profile", movement.document},
        {"land_combat_profile", landCombat.document},
        {"economy_profile", economy.document},
        {"air_profile", air.document},
        {"naval_profile", naval.document},
    };
    const auto& calendar = contract.document.require("calendar");
    const std::string start = calendar.require("start").asString();
    if (start.size() != 7 || start[4] != '-') throw std::runtime_error("Invalid campaign start date");
    for (std::size_t index = 0; index < start.size(); ++index) {
        if (index != 4 && (start[index] < '0' || start[index] > '9')) {
            throw std::runtime_error("Invalid campaign start date");
        }
    }
    definition.startYear = std::stoi(start.substr(0, 4));
    definition.startMonth = std::stoi(start.substr(5, 2));
    definition.calendarRounds = calendar.require("calendar_rounds").asInt();
    for (const auto& player : contract.document.require("agents").asArray()) {
        definition.players.insert(player.asString());
    }
    for (const auto& turn : contract.document.require("national_turn_order").asArray()) {
        definition.turnOrder.push_back(turn.require("slot").asString());
    }
    const auto& nodes = map.document.require("nodes").asObject();
    const auto& homeCountries = home.document.require("nations");
    for (const auto& [id, source] : index.document.require("factions").asObject()) {
        if (id != source.require("id").asString()) throw std::runtime_error("Faction index key/ID mismatch");
        FactionDefinition faction;
        faction.id = id;
        faction.displayName = source.require("display_name").asString();
        const auto* homeland = homeCountries.find(source.require("map_owner_alias").asString());
        if (homeland) {
            faction.homeCountryKnown = true;
            for (const auto& zone : homeland->require("home_country_land_zone_ids").asArray()) {
                if (nodes.contains(zone.asString())) faction.homeCountry.insert(zone.asString());
            }
        }
        definition.factions.emplace(id, std::move(faction));
    }
    for(const auto& [id,membership]:politics.document.require("home_country_memberships").asObject()) {
        if(id=="dadao")continue;
        auto& faction=definition.factions.at(id);
        faction.homeCountryKnown=membership.require("known").asBool();
        faction.homeCountry.clear();
        for(const auto& zone:membership.require("land_zone_ids").asArray())if(nodes.contains(zone.asString()))faction.homeCountry.insert(zone.asString());
    }
    FactionDefinition dadao;
    dadao.id="dadao";dadao.displayName="Dadao Government";dadao.homeCountryKnown=true;dadao.dormant=true;
    definition.factions.emplace(dadao.id,std::move(dadao));

    State state;
    state.definition = freezeDefinition(std::move(definition));
    state.politics.capitals["japan"]="land_jap_tokyo";
    for (const auto& [id, source] : index.document.require("factions").asObject()) {
        NationState nation;
        const auto& control = source.require("initial_control");
        nation.alliance = optionalId(control.find("alliance_id"));
        const auto controller = optionalId(control.find("controller_id"));
        if (controller) {
            if (state.definition->factions.contains(*controller)) nation.controllerNation = *controller;
            else if (state.definition->players.contains(*controller)) nation.player = *controller;
            else throw std::runtime_error("Unknown initial controller: " + *controller);
        }
        if (id == japan.document.require("nation").asString()) {
            nation.powerStatus = "major";
            nation.controllerNation = id;
        } else if (control.require("status").asString() == "unaligned_uncontrolled_warlord") {
            nation.powerStatus = "warlord";
        }
        state.nations.emplace(id, std::move(nation));
    }
    for (const auto& turn : contract.document.require("national_turn_order").asArray()) {
        state.nations.at(turn.require("slot").asString()).player = turn.require("agent").asString();
    }
    for (const auto& account : contract.document.require("starting_accounts").require("national_accounts").asArray()) {
        auto& nation = state.nations.at(account.require("nation").asString());
        nation.treasury = account.require("treasury_ipp").asInt();
    }
    for (auto& [id, nation] : state.nations) {
        // No minor account or Soviet income is created by retaining territory.
        if (!nation.treasury) nation.incomeKnown = true;
    }
    for (const auto& faction : china.document.require("factions").asArray()) {
        auto& nation = state.nations.at(faction.require("id").asString());
        if (const auto* wars = faction.find("at_war_with")) {
            for (const auto& other : wars->asArray()) nation.atWarWith.insert(other.asString());
        }
    }
    for (const auto& [zone, node] : nodes) {
        if (node.require("type").asString() != "land") continue;
        const auto& original = index.document.require("land_original_owners").require(zone);
        if (original.require("source_original_owner").asString() != node.require("original_owner").asString()) {
            throw std::runtime_error("Original owner differs from faction index: " + zone);
        }
        state.territories.emplace(zone, TerritoryState {original.require("original_faction_id").asString(), {}});
    }
    for (const auto& [id, source] : map.document.require("facilities").asObject()) {
        state.facilities.emplace(id, FacilityState {
            id, source.require("type").asString(), source.require("land_id").asString(), 0, {}});
    }
    for (const auto& [zone, node] : nodes) {
        if (node.require("type").asString() != "land") continue;
        for (const auto& edge : node.require("neighbors").asArray()) {
            const auto& other = edge.require("neighbor_id").asString();
            const auto& present = edge.require("railway_connection");
            if (zone >= other || !present.isBool() || !present.asBool()
                    || nodes.at(other).require("type").asString() != "land") continue;
            RailState rail;
            rail.id = "rail_" + zone + "__" + other;
            rail.endpointA = zone;
            rail.endpointB = other;
            rail.damageByEndpoint = {{zone, 0}, {other, 0}};
            state.rails.emplace(rail.id, std::move(rail));
        }
    }

    const Id japanId = japan.document.require("nation").asString();
    for (const auto& row : japan.document.require("placements").asArray()) {
        const Id zone = row.require("node_id").asString();
        addUnits(state, japanId, zone, row.require("units"));
        for (const auto& source : row.require("facilities").asArray()) {
            if (source.require("count").asInt() != 1) throw std::runtime_error("Setup facility ID must represent one instance");
            FacilityState facility;
            facility.id = source.require("id").asString();
            facility.type = source.require("type").asString();
            facility.zone = zone;
            facility.damage = integerOr(source, "damage_points", 0);
            if (!state.facilities.emplace(facility.id, facility).second) {
                throw std::runtime_error("Duplicate setup facility: " + facility.id);
            }
        }
    }
    for (const auto& row : china.document.require("territories").asArray()) {
        const Id zone = row.require("node_id").asString();
        state.territories.at(zone).possessor = row.require("owner_id").asString();
        addUnits(state, row.require("owner_id").asString(), zone, row.require("units"));
        // Existing facility references are provenance, not new instances.
        for (const auto& facility : row.require("facilities").asArray()) {
            if (!state.facilities.contains(facility.require("facility_id").asString())) {
                throw std::runtime_error("Setup references a missing map facility");
            }
        }
    }
    for (const auto& [id, unit] : state.units) {
        if (unit.carriedBy) state.units.at(*unit.carriedBy).cargo.push_back(id);
    }
    for (const auto& source : japan.document.require("starting_construction").asArray()) {
        BuildProject project;
        project.id = source.require("id").asString();
        project.owner = japanId;
        project.type = source.require("type").asString();
        project.site = optionalId(source.find("node_id"));
        project.queuePosition = source.require("queue_stage").asInt();
        project.paidIpp = source.require("paid_construction_value").asInt();
        for (const auto& payment : source.require("remaining_stage_payments_ipp").asArray()) {
            project.remainingPayments.push_back(payment.asInt());
        }
        if (!state.construction.emplace(project.id, project).second) {
            throw std::runtime_error("Duplicate construction ID");
        }
    }
    for (const auto& nation : state.definition->turnOrder) state.completedTurns.emplace(nation, 0);
    initializeCatalogState(state);
    state.captureTurnStart();
    state.validate();
    return state;
}

}  // namespace game::campaign
