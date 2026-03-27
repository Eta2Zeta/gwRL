#pragma once

#include "game/unit.hpp"

#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>

namespace game {

enum class ActionKind {
    DeclareWarOnChina,
    PurchaseUnit,
    MoveCombatUnit,
    ResolveCombat,
    PlaceUnit,
    EndPhase,
};

struct Action {
    ActionKind kind {ActionKind::EndPhase};
    std::optional<std::string> sourceZoneId;
    std::optional<std::string> targetZoneId;
    std::optional<int> unitCount;
    std::optional<UnitKind> unitKind;
};

inline std::string_view toString(ActionKind kind) {
    switch (kind) {
        case ActionKind::DeclareWarOnChina:
            return "declare_war_on_china";
        case ActionKind::PurchaseUnit:
            return "purchase_unit";
        case ActionKind::MoveCombatUnit:
            return "move_combat_unit";
        case ActionKind::ResolveCombat:
            return "resolve_combat";
        case ActionKind::PlaceUnit:
            return "place_unit";
        case ActionKind::EndPhase:
            return "end_phase";
    }
    throw std::runtime_error("Unknown action kind");
}

}  // namespace game
