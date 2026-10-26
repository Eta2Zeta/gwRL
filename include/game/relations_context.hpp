#pragma once
#include "game/campaign.hpp"
#include <memory>
#include <vector>

namespace game::campaign {
struct RelationsContext {
    std::shared_ptr<const Definition> definition;
    std::vector<Id> nations, players;
    std::vector<Id> territories;
    std::vector<std::int64_t> chineseHome, warlords;
    bool chineseHomeValid {false};
    explicit RelationsContext(std::shared_ptr<const Definition>);
};
struct RelationsOracleBatch {
    std::shared_ptr<const RelationsContext> context;
    std::size_t rows;
    // [B,N,N,7]: direct control, directed war, friendliness, logistics,
    // optional-alliance equality, shared nonempty alliance, rail permission.
    std::vector<std::int64_t> pairs, pairErrors;
    // [B,N,3]: political player index, at-war-with-major, movement controller.
    std::vector<std::int64_t> nations, nationErrors, present;
    std::vector<std::int64_t> landAttack, landAttackErrors;
    explicit RelationsOracleBatch(std::shared_ptr<const RelationsContext>,std::size_t);
    void capture(std::size_t,const State&);
};
}
