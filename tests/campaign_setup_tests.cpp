#include "game/campaign.hpp"

#include <chrono>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
namespace fs = std::filesystem;
using namespace game::campaign;
const fs::path source = fs::path(GWRL_SOURCE_DIR) / "game_content/scenarios/japan_china_1936";

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}
void rejects(const std::function<void()>& action) {
    try { action(); } catch (const std::exception&) { return; }
    throw std::runtime_error("Invalid scenario was accepted");
}
struct TemporaryScenario {
    fs::path root = fs::temp_directory_path() / ("gwrl-m2-setup-" + std::to_string(
        std::chrono::steady_clock::now().time_since_epoch().count()));
    fs::path scenario = root / "game_content/scenarios/campaign";
    TemporaryScenario() {
        fs::create_directories(scenario.parent_path());
        fs::copy(source, scenario, fs::copy_options::recursive);
        fs::create_directories(root / "game_content/maps");
        fs::copy_file(source / "../../maps/gw36_nation_home_country.json", root / "game_content/maps/gw36_nation_home_country.json");
        fs::create_directory_symlink(fs::path(GWRL_SOURCE_DIR) / "game_content/catalog", root / "game_content/catalog");
        fs::create_directory_symlink(fs::path(GWRL_SOURCE_DIR) / "game_content/rules", root / "game_content/rules");
    }
    ~TemporaryScenario() { std::error_code ignored; fs::remove_all(root, ignored); }
};
}

int main() {
    try {
        State state = loadScenario(source);
        require(state.units.size() == 99, "Starting unit total differs from M0");
        require(state.territories.size() == 31, "Land total differs from M0");
        require(state.nations.size() == 12, "Canonical faction count differs from M1");
        require(state.facilities.size() == 22, "Map facilities and setup factories not distinct");
        require(state.definition->geography.require("nodes").asObject().size() == 37, "Closed map changed");
        require(state.definition->geography.require("convoy_lines").asArray().empty(), "Convoys became active");
        require(state.definition->turnOrder == std::vector<Id> {"ccp", "mongolia", "japan", "kmt"}, "Turn order changed");
        std::map<Id, int> units;
        for (const auto& [id, unit] : state.units) {
            ++units[unit.owner];
            require(unit.movementRemaining && unit.movementAllowance, "M3 catalog movement missing");
        }
        require(units["japan"] == 48 && units["kmt"] == 12 && units["ccp"] == 5 && units["mongolia"] == 2,
                "National setup counts changed");
        require(state.nations.at("japan").treasury == 15 && state.nations.at("kmt").treasury == 6
                && state.nations.at("ccp").treasury == 2, "Opening accounts changed");
        require(!state.nations.at("mongolia").treasury && !state.nations.contains("ussr")
                && !state.nations.contains("fec"), "An excluded account was restored");
        require(state.nations.at("mongolia").player == "comintern"
                && !state.nations.at("mongolia").controllerNation, "Mongolia became another nation");
        require(state.nations.at("kmt").atWarWith.contains("ccp")
                && state.nations.at("ccp").atWarWith.contains("kmt")
                && state.nations.at("japan").atWarWith.empty(), "Initial diplomacy changed");
        require(state.currentNation() == "ccp" && state.decisionPlayer() == "comintern", "Initial decision owner wrong");
        require(state.calendarDate() == std::pair {1936, 7}, "Initial date wrong");
        std::cout << "PASS all retained setup, national accounts, politics and turn routing\n";

        const auto& fleet = state.units.at("japan_fleet_carrier_p15_setup_1");
        const auto& light = state.units.at("japan_light_carrier_p15_setup_1");
        require(fleet.cargo.size() == 2 && light.cargo.size() == 1, "Carrier assignments changed");
        for (const auto& aircraft : fleet.cargo) require(state.units.at(aircraft).carriedBy == fleet.id, "Carrier link not reciprocal");
        int paid = 0;
        require(state.construction.size() == 2, "National construction queues lost");
        for (const auto& [id, project] : state.construction) {
            require(!project.site && project.owner == "japan", "A queue was assigned an invented site");
            paid += project.paidIpp;
        }
        require(paid == 10, "Paid construction changed");
        require(state.construction.at("japan_queue_heavy_cruiser").remainingPayments == std::vector<int> {5}, "Cruiser queue wrong");
        require(state.construction.at("japan_queue_fleet_carrier").remainingPayments == std::vector<int> {5, 5}, "Carrier queue wrong");
        require(state.definition->factions.at("warlord_beiping_hopeh").displayName == "Zhili Clique", "User display name lost");
        require(state.definition->factions.at("japan").homeCountryKnown
                && state.definition->factions.at("japan").homeCountry.size() == 4, "Japan home-country table lost");
        require(state.definition->factions.at("ccp").homeCountry.contains("land_mongolia_kobdo"),
                "Home-country membership was inferred from possession");
        require(state.definition->factions.at("mongolia").homeCountryKnown
                && state.definition->factions.at("mongolia").homeCountry.size()==4,
                "M4 original mainland home-country predicate unresolved");
        require(!state.nations.at("japan").incomeKnown, "Printed IPP was silently treated as evaluated legal income");
        std::cout << "PASS carrier identities, queues, source names and independent home-country membership\n";

        require(State::fromJson(state.definition, game::json::parse(state.serialize())).serialize() == state.serialize(),
                "Actual campaign setup fails round trip");
        State clone = state.clone();
        require(clone.definition == state.definition, "Clone copied immutable definition");
        clone.nations.at("japan").treasury = 0;
        clone.territories.at("land_china_beiping").possessor = "kmt";
        require(state.nations.at("japan").treasury == 15
                && state.territories.at("land_china_beiping").possessor == "warlord_beiping_hopeh", "Clone leaked mutations");
        require(state.definition->geography.require("nodes").require("land_china_beiping").require("original_owner").asString() == "Zhili Clique",
                "Possession rewrote original nationality");
        std::cout << "PASS real setup clone isolation and serialization\n";

        {
            TemporaryScenario temporary;
            State loaded = loadScenario(temporary.scenario);
            fs::remove_all(temporary.root);
            require(loaded.clone().units.size() == 99, "Clone needs setup files after initial load");
            require(State::fromJson(loaded.definition, game::json::parse(loaded.serialize())).units.size() == 99,
                    "Restore with in-memory immutable definition needs source files");
        }
        std::cout << "PASS cloning and restore after setup files are removed\n";
        {
            TemporaryScenario temporary;
            std::ofstream changed(temporary.scenario / "m0/japan_setup.json", std::ios::app);
            changed << ' ';
            changed.close();
            rejects([&] { loadScenario(temporary.scenario); });
        }
        std::cout << "PASS stale source-index rejection\n";
        for (const auto& malformed : {"193x-07", "1936-7x", "1936-00", "1936-04"}) {
            TemporaryScenario temporary;
            const auto path = temporary.scenario / "m0/scenario_contract.json";
            auto contract = game::json::parseFile(path).asObject();
            auto calendar = contract.at("calendar").asObject();
            calendar["start"] = game::json::Value(std::string(malformed));
            contract["calendar"] = game::json::Value(std::move(calendar));
            std::ofstream changed(path);
            changed << canonicalJson(game::json::Value(std::move(contract)));
            changed.close();
            rejects([&] { loadScenario(temporary.scenario); });
        }
        std::cout << "PASS malformed calendar rejection\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL campaign setup: " << error.what() << '\n';
        return 1;
    }
}
