#pragma once

#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace game {

enum class Phase {
    DeclarationOfWar,
    PurchaseUnits,
    CombatMove,
    CombatResolve,
    NonCombat,
    PlaceUnits,
};

enum class ZoneKind {
    Land,
    Sea,
};

struct ZoneNeighbor {
    std::string id;
    bool railway {false};
};

struct Zone {
    std::string id;
    std::string displayName;
    ZoneKind kind {ZoneKind::Land};
    std::string terrain {"normal"};
    std::string controller;
    bool isCity {false};
    int incomeValue {0};
    std::vector<std::string> facilities;
    std::vector<ZoneNeighbor> neighbors;
};

inline std::string_view toString(Phase phase) {
    switch (phase) {
        case Phase::DeclarationOfWar:
            return "declaration_of_war";
        case Phase::PurchaseUnits:
            return "purchase_units";
        case Phase::CombatMove:
            return "combat_move";
        case Phase::CombatResolve:
            return "combat_resolve";
        case Phase::NonCombat:
            return "non_combat";
        case Phase::PlaceUnits:
            return "place_units";
    }
    throw std::runtime_error("Unknown phase");
}

inline std::string_view toString(ZoneKind zoneKind) {
    switch (zoneKind) {
        case ZoneKind::Land:
            return "land";
        case ZoneKind::Sea:
            return "sea";
    }
    throw std::runtime_error("Unknown zone kind");
}

inline Phase parsePhase(std::string_view value) {
    if (value == "declaration_of_war") {
        return Phase::DeclarationOfWar;
    }
    if (value == "purchase_units") {
        return Phase::PurchaseUnits;
    }
    if (value == "combat_move") {
        return Phase::CombatMove;
    }
    if (value == "combat_resolve") {
        return Phase::CombatResolve;
    }
    if (value == "non_combat") {
        return Phase::NonCombat;
    }
    if (value == "place_units") {
        return Phase::PlaceUnits;
    }
    throw std::runtime_error("Unsupported phase: " + std::string(value));
}

inline ZoneKind parseZoneKind(std::string_view value) {
    if (value == "land") {
        return ZoneKind::Land;
    }
    if (value == "sea") {
        return ZoneKind::Sea;
    }
    throw std::runtime_error("Unsupported zone kind: " + std::string(value));
}

}  // namespace game
