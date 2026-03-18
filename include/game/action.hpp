#pragma once

#include <stdexcept>
#include <string_view>

namespace game {

enum class ActionKind {
    EndPhase,
};

struct Action {
    ActionKind kind {ActionKind::EndPhase};
};

inline std::string_view toString(ActionKind kind) {
    switch (kind) {
        case ActionKind::EndPhase:
            return "end_phase";
    }
    throw std::runtime_error("Unknown action kind");
}

}  // namespace game
