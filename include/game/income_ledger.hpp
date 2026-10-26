#pragma once
#include "game/campaign.hpp"

namespace game::campaign {
// Exact accounting substep of EconomyRules::finishTurn: refresh all income
// ledgers, collect the current nation's income at most once, mark collected.
// Placement/repair completion, political hooks and clock progression belong
// to the caller. Engine transactions provide rollback on an exception.
void applyIncomeLedger(State&);
}
