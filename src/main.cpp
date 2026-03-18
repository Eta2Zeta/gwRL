#include "game/game_state.hpp"
#include "game/setup_loader.hpp"
#include "game/unit.hpp"

#include <filesystem>
#include <iostream>

namespace {

void printGameSummary(const game::GameState& gameState) {
    std::cout << "Current turn: " << gameState.currentNation() << " / " << game::toString(gameState.currentPhase())
              << "\n";

    std::cout << "\nNations\n";
    for (const auto& nationId : gameState.turnOrder()) {
        const auto& nation = gameState.nation(nationId);
        std::cout << "  " << nation.id() << " (" << nation.displayName() << ")"
                  << " income=" << nation.income()
                  << " max_factory_output=" << nation.maxFactoryOutput()
                  << " treasury=" << nation.treasury() << "\n";
    }

    std::cout << "\nUnits\n";
    for (const auto& unit : gameState.units()) {
        std::cout << "  " << unit->ownerId()
                  << " " << game::toString(unit->kind())
                  << " in " << unit->zoneId()
                  << " movement=" << unit->movementLeft() << "/" << unit->maxMovement() << "\n";
    }
}

}  // namespace

int main(int argc, char** argv) {
    const auto scenarioPath = argc > 1 ? std::filesystem::path(argv[1])
                                       : std::filesystem::path("data/china_simplified_setup.json");

    try {
        const auto gameState = game::SetupLoader::loadFromFile(scenarioPath);
        printGameSummary(gameState);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Failed to load scenario: " << error.what() << "\n";
        return 1;
    }
}
