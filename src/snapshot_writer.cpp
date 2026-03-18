#include "game/snapshot_writer.hpp"

#include "game/unit.hpp"

#include <algorithm>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace game {

namespace {

void writeIndent(std::ostream& output, int indent) {
    for (int i = 0; i < indent; ++i) {
        output << "  ";
    }
}

void writeJsonString(std::ostream& output, const std::string& value) {
    output << '"';
    for (const char ch : value) {
        switch (ch) {
            case '\\':
                output << "\\\\";
                break;
            case '"':
                output << "\\\"";
                break;
            case '\n':
                output << "\\n";
                break;
            case '\r':
                output << "\\r";
                break;
            case '\t':
                output << "\\t";
                break;
            default:
                output << ch;
                break;
        }
    }
    output << '"';
}

struct UnitView {
    std::string owner;
    std::string type;
    int movementLeft {0};
};

}  // namespace

void SnapshotWriter::writeState(
    const GameState& gameState,
    const std::filesystem::path& filePath,
    int stepIndex) {
    std::ofstream output(filePath);
    if (!output) {
        throw std::runtime_error("Unable to write snapshot file: " + filePath.string());
    }

    std::vector<std::string> zoneIds;
    zoneIds.reserve(gameState.zones().size());
    for (const auto& [zoneId, zone] : gameState.zones()) {
        zoneIds.push_back(zoneId);
    }
    std::sort(zoneIds.begin(), zoneIds.end());

    output << "{\n";
    writeIndent(output, 1);
    output << "\"step_index\": " << stepIndex << ",\n";
    writeIndent(output, 1);
    output << "\"terminal\": " << (gameState.isTerminal() ? "true" : "false") << ",\n";
    if (!gameState.isTerminal()) {
        writeIndent(output, 1);
        output << "\"current_nation\": ";
        writeJsonString(output, std::string(gameState.currentNation()));
        output << ",\n";
        writeIndent(output, 1);
        output << "\"current_phase\": ";
        writeJsonString(output, std::string(toString(gameState.currentPhase())));
        output << ",\n";
    }
    writeIndent(output, 1);
    output << "\"nodes\": [\n";

    for (std::size_t i = 0; i < zoneIds.size(); ++i) {
        const auto& zone = gameState.zone(zoneIds[i]);

        std::vector<UnitView> unitViews;
        for (const auto& unit : gameState.units()) {
            if (unit->zoneId() == zone.id) {
                unitViews.push_back(UnitView{
                    .owner = unit->ownerId(),
                    .type = std::string(toString(unit->kind())),
                    .movementLeft = unit->movementLeft(),
                });
            }
        }
        std::sort(
            unitViews.begin(),
            unitViews.end(),
            [](const UnitView& lhs, const UnitView& rhs) {
                if (lhs.owner != rhs.owner) {
                    return lhs.owner < rhs.owner;
                }
                return lhs.type < rhs.type;
            });

        writeIndent(output, 2);
        output << "{\n";
        writeIndent(output, 3);
        output << "\"id\": ";
        writeJsonString(output, zone.id);
        output << ",\n";
        writeIndent(output, 3);
        output << "\"name\": ";
        writeJsonString(output, zone.displayName);
        output << ",\n";
        writeIndent(output, 3);
        output << "\"current_owner\": ";
        writeJsonString(output, zone.controller);
        output << ",\n";

        writeIndent(output, 3);
        output << "\"units\": [";
        if (!unitViews.empty()) {
            output << "\n";
            for (std::size_t unitIndex = 0; unitIndex < unitViews.size(); ++unitIndex) {
                const auto& unitView = unitViews[unitIndex];
                writeIndent(output, 4);
                output << "{";
                output << "\"owner\": ";
                writeJsonString(output, unitView.owner);
                output << ", \"type\": ";
                writeJsonString(output, unitView.type);
                output << ", \"movement_left\": " << unitView.movementLeft;
                output << "}";
                if (unitIndex + 1 < unitViews.size()) {
                    output << ",";
                }
                output << "\n";
            }
            writeIndent(output, 3);
        }
        output << "],\n";

        writeIndent(output, 3);
        output << "\"facilities\": [";
        for (std::size_t facilityIndex = 0; facilityIndex < zone.facilities.size(); ++facilityIndex) {
            if (facilityIndex > 0) {
                output << ", ";
            }
            writeJsonString(output, zone.facilities[facilityIndex]);
        }
        output << "],\n";

        writeIndent(output, 3);
        output << "\"neighbors\": [";
        if (!zone.neighbors.empty()) {
            output << "\n";
            for (std::size_t neighborIndex = 0; neighborIndex < zone.neighbors.size(); ++neighborIndex) {
                const auto& neighbor = zone.neighbors[neighborIndex];
                writeIndent(output, 4);
                output << "{";
                output << "\"id\": ";
                writeJsonString(output, neighbor.id);
                output << ", \"railway\": " << (neighbor.railway ? "true" : "false");
                output << "}";
                if (neighborIndex + 1 < zone.neighbors.size()) {
                    output << ",";
                }
                output << "\n";
            }
            writeIndent(output, 3);
        }
        output << "]\n";

        writeIndent(output, 2);
        output << "}";
        if (i + 1 < zoneIds.size()) {
            output << ",";
        }
        output << "\n";
    }

    writeIndent(output, 1);
    output << "]\n";
    output << "}\n";
}

}  // namespace game
