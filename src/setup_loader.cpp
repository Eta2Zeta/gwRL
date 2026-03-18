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

}  // namespace

GameState SetupLoader::loadFromFile(const std::filesystem::path& filePath) {
    const json::Value root = json::parseFile(filePath);
    GameState game;

    for (const auto& nationValue : root.require("nations").asArray()) {
        game.addNation(
            Nation(
                readStringField(nationValue, "id"),
                readStringField(nationValue, "display_name"),
                readIntField(nationValue, "income"),
                readIntField(nationValue, "max_factory_output")));
    }

    for (const auto& zoneValue : root.require("zones").asArray()) {
        game.addZone(Zone{
            .id = readStringField(zoneValue, "id"),
            .displayName = readStringField(zoneValue, "display_name"),
            .kind = parseZoneKind(readStringField(zoneValue, "kind")),
            .controller = readStringField(zoneValue, "controller"),
        });
    }

    std::vector<std::string> turnOrder;
    for (const auto& nationIdValue : root.require("turn_order").asArray()) {
        turnOrder.push_back(nationIdValue.asString());
    }
    game.setTurnOrder(std::move(turnOrder));

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
            game.addUnit(makeUnit(unitKind, nationId, zoneId));
        }
    }

    return game;
}

}  // namespace game
