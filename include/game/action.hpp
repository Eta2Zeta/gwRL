#pragma once

#include <cstddef>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>

namespace game {

enum class ActionKind {
    DeclareWarOnChina,
    MoveCombatUnit,
    EndPhase,
};

struct Action {
    ActionKind kind {ActionKind::EndPhase};
    std::optional<std::size_t> unitIndex;
    std::optional<std::string> targetZoneId;
};

inline std::string_view toString(ActionKind kind) {
    switch (kind) {
        case ActionKind::DeclareWarOnChina:
            return "declare_war_on_china";
        case ActionKind::MoveCombatUnit:
            return "move_combat_unit";
        case ActionKind::EndPhase:
            return "end_phase";
    }
    throw std::runtime_error("Unknown action kind");
}

}  // namespace game
