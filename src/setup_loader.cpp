#include "game/setup_loader.hpp"

#include "game/simple_json.hpp"

#include <stdexcept>
#include <string>

namespace game {

namespace {

std::string readStringField(const json::Value& object, const std::string& key) {
    return object.require(key).asString();
}

int readIntField(const json::Value& object, const std::string& key) {
    return object.require(key).asInt();
}

int readIntFieldOrDefault(const json::Value& object, const std::string& key, int defaultValue) {
    if (const auto* field = object.find(key)) {
        return field->asInt();
    }
    return defaultValue;
}

std::vector<std::string> readStringArrayField(const json::Value& object, const std::string& key) {
    std::vector<std::string> values;
    if (const auto* field = object.find(key)) {
        for (const auto& value : field->asArray()) {
            values.push_back(value.asString());
        }
    }
    return values;
}

std::vector<UnitKind> readUnitKindArrayField(const json::Value& object, const std::string& key) {
    std::vector<UnitKind> values;
    if (const auto* field = object.find(key)) {
        for (const auto& value : field->asArray()) {
            values.push_back(parseUnitKind(value.asString()));
        }
    }
    return values;
}

std::vector<ZoneNeighbor> readNeighborsField(const json::Value& object, const std::string& key) {
    std::vector<ZoneNeighbor> neighbors;
    if (const auto* field = object.find(key)) {
        for (const auto& neighborValue : field->asArray()) {
            neighbors.push_back(ZoneNeighbor{
                .id = readStringField(neighborValue, "id"),
                .railway = neighborValue.require("railway").asBool(),
            });
        }
    }
    return neighbors;
}

}  // namespace

GameState SetupLoader::loadFromFile(const std::filesystem::path& filePath) {
    const json::Value root = json::parseFile(filePath);
    GameState game;

    for (const auto& nationValue : root.require("nations").asArray()) {
        Nation nation(
            readStringField(nationValue, "id"),
            readStringField(nationValue, "display_name"),
            readIntField(nationValue, "income"),
            readIntField(nationValue, "max_factory_output"),
            readIntFieldOrDefault(nationValue, "treasury", -1));
        nation.setAtWarWith(readStringArrayField(nationValue, "at_war_with"));
        nation.setAllies(readStringArrayField(nationValue, "allies"));
        game.addNation(std::move(nation));
    }

    for (const auto& zoneValue : root.require("zones").asArray()) {
        game.addZone(Zone{
            .id = readStringField(zoneValue, "id"),
            .displayName = readStringField(zoneValue, "display_name"),
            .kind = parseZoneKind(readStringField(zoneValue, "kind")),
            .terrain = [&]() {
                if (const auto* terrainValue = zoneValue.find("terrain")) {
                    return terrainValue->asString();
                }
                return std::string("normal");
            }(),
            .controller = readStringField(zoneValue, "controller"),
            .isCity = [&]() {
                if (const auto* isCityValue = zoneValue.find("is_city")) {
                    return isCityValue->asBool();
                }
                return false;
            }(),
            .incomeValue = readIntFieldOrDefault(zoneValue, "income_value", 0),
            .facilities = readStringArrayField(zoneValue, "facilities"),
            .neighbors = readNeighborsField(zoneValue, "neighbors"),
        });
    }

    for (const auto& nationValue : root.require("nations").asArray()) {
        auto& nation = game.nation(readStringField(nationValue, "id"));
        nation.setIncome(0);
    }
    for (const auto& [zoneId, zone] : game.zones()) {
        if (!game.hasNation(zone.controller)) {
            continue;
        }
        auto& nation = game.nation(zone.controller);
        nation.setIncome(nation.income() + zone.incomeValue);
    }

    std::vector<std::string> turnOrder;
    for (const auto& nationIdValue : root.require("turn_order").asArray()) {
        turnOrder.push_back(nationIdValue.asString());
    }
    game.setTurnOrder(std::move(turnOrder));
    if (const auto* turnLimit = root.find("turn_limit_per_nation")) {
        game.setTurnLimitPerNation(turnLimit->asInt());
    }

    std::vector<Phase> phases;
    for (const auto& phaseValue : root.require("phases").asArray()) {
        phases.push_back(parsePhase(phaseValue.asString()));
    }
    game.setPhaseOrder(std::move(phases));

    const auto& setup = root.require("setup").asObject();
    for (const auto& nationId : game.turnOrder()) {
        auto setupIt = setup.find(nationId);
        if (setupIt == setup.end()) {
            throw std::runtime_error("Missing setup block for nation: " + nationId);
        }

        const auto& units = setupIt->second.require("units").asArray();
        for (const auto& unitValue : units) {
            const auto unitKind = parseUnitKind(readStringField(unitValue, "type"));
            const auto zoneId = readStringField(unitValue, "zone");
            const auto ownerId = [&]() {
                if (const auto* ownerValue = unitValue.find("owner")) {
                    return ownerValue->asString();
                }
                return nationId;
            }();
            auto unit = makeUnit(unitKind, ownerId, zoneId);
            unit->setCargo(readUnitKindArrayField(unitValue, "cargo"));
            game.addUnit(std::move(unit));
        }
    }

    return game;
}

}  // namespace game
