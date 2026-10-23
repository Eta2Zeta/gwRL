#include "game/naval.hpp"

#include <algorithm>
#include <stdexcept>

namespace game::campaign {
namespace {
bool activeNavalBattle(const State &s) {
  for (const auto &[id, b] : s.battles)
    if (b.flags.contains("naval_battle") && b.flags.at("naval_battle") &&
        !(b.flags.contains("finished") && b.flags.at("finished")) &&
        b.stage != "naval_declared")
      return true;
  return false;
}
} // namespace

int navalCompletedTurns(const State &s, const Id &nation) {
  if (const auto found = s.completedTurns.find(nation);
      found != s.completedTurns.end())
    return found->second;
  const auto &n = s.nations.at(nation);
  if (n.controllerNation && s.completedTurns.contains(*n.controllerNation))
    return s.completedTurns.at(*n.controllerNation);
  if (nation == "dadao" &&
      n.gameFlags.contains("direct_axis_control_after_japan_surrender"))
    return s.completedTurns.at("japan");
  throw std::runtime_error("Nation has no operational calendar turn: " +
                           nation);
}

NavalRules::NavalRules(std::shared_ptr<const Rules> gameplay)
    : gameplay_(std::move(gameplay)) {}
Id NavalRules::id() const {
  return "gw36_naval_v43:" + (gameplay_ ? gameplay_->id() : Id("none"));
}
std::vector<Action> NavalRules::actions(const State &s) const {
  if (s.chance || !s.decisions.empty())
    return {};
  if (s.flags.contains("immediate_land_battles") &&
      s.flags.at("immediate_land_battles"))
    return gameplay_ ? gameplay_->actions(s) : std::vector<Action>{};
  auto combat = navalCombatActions(s);
  for (const auto &a : combat)
    if (a.kind == "naval_finish_battle")
      return {a};
  auto operations = navalOperationActions(s);
  combat.insert(combat.end(), operations.begin(), operations.end());
  if (activeNavalBattle(s) || (s.flags.contains("immediate_naval_battles") &&
                               s.flags.at("immediate_naval_battles")))
    return combat;
  auto out = gameplay_ ? gameplay_->actions(s) : std::vector<Action>{};
  out.insert(out.end(), combat.begin(), combat.end());
  auto movement = navalMovementActions(s);
  out.insert(out.end(), movement.begin(), movement.end());
  if (s.flags.contains("naval_berthing") && s.flags.at("naval_berthing"))
    out.erase(
        std::remove_if(
            out.begin(), out.end(),
            [&](const Action &a) {
              if (a.kind == "naval_enter_port")
                return false;
              const auto *id = a.parameters.find("unit");
              if (!id || !s.units.contains(id->asString()))
                return true;
              const auto &u = s.units.at(id->asString());
              const bool landing = u.turnFlags.contains("air_in_flight") &&
                                   u.turnFlags.at("air_in_flight") &&
                                   (a.kind == "air_land_noncombat" ||
                                    a.kind == "air_failed_landing");
              const bool withdrawal =
                  u.turnFlags.contains("must_withdraw_from_chinese_gift") &&
                  u.turnFlags.at("must_withdraw_from_chinese_gift") &&
                  (a.kind == "movement_route" || a.kind == "naval_load");
              return !landing && !withdrawal;
            }),
        out.end());
  return out;
}
std::vector<Action> NavalRules::interrupts(const State &s) const {
  if (activeNavalBattle(s))
    return {};
  return gameplay_ ? gameplay_->interrupts(s) : std::vector<Action>{};
}
bool NavalRules::phaseComplete(const State &s) const {
  return navalCombatPhaseComplete(s) && navalMovementPhaseComplete(s) &&
         navalOperationPhaseComplete(s) &&
         (!gameplay_ || gameplay_->phaseComplete(s));
}
void NavalRules::apply(State &s, const Action &a) const {
  if (a.kind == "naval_finish_battle") {
    const auto battle = a.parameters.require("battle").asString();
    const auto data = s.battles.at(battle).data;
    if (applyNavalCombatAction(s, a)) {
      if (const auto *facility = data.find("port_evacuation"))
        resumeDamagedPortEvacuation(
            s, facility->asString(),
            data.find("evacuation_selection_complete") &&
                    data.require("evacuation_selection_complete").asBool()
                ? 3
                : data.require("evacuated").asInt());
      return;
    }
  }
  if (applyNavalCombatAction(s, a) || applyNavalMovementAction(s, a) ||
      applyNavalOperationAction(s, a))
    return;
  if (!gameplay_)
    throw std::runtime_error("Unknown naval action: " + a.kind);
  gameplay_->apply(s, a);
}
void NavalRules::applyChance(State &s, const ChanceRequest &r,
                             const ChanceOutcome &o) const {
  if (applyNavalCombatChance(s, r, o) || applyNavalMovementChance(s, r, o) ||
      applyNavalOperationChance(s, r, o))
    return;
  if (!gameplay_)
    throw std::runtime_error("Unknown naval chance: " + r.purpose);
  gameplay_->applyChance(s, r, o);
}
void NavalRules::beginTurn(State &s) const {
  if (gameplay_)
    gameplay_->beginTurn(s);
  beginNavalMovementTurn(s);
  for (auto &[id, unit] : s.units)
    if (movementController(s, unit.owner) &&
        unit.gameFlags.contains("skeleton_crew") &&
        unit.gameFlags.at("skeleton_crew") &&
        !unit.gameFlags.contains("skeleton_crew_until_own_turn"))
      unit.gameFlags["skeleton_crew_until_own_turn"] =
          navalCompletedTurns(s, unit.owner) + 1;
}
void NavalRules::finishPhase(State &s) const {
  finishNavalMovementPhase(s);
  if (gameplay_)
    gameplay_->finishPhase(s);
  finishNavalOperationPhase(s);
}
void NavalRules::finishTurn(State &s) const {
  if (!gameplay_)
    throw std::runtime_error("Naval rules require income accounting");
  gameplay_->finishTurn(s);
  for (auto &[id, unit] : s.units) {
    unit.turnFlags.erase("submerged");
    unit.gameFlags.erase("submerged");
    if (!movementController(s, unit.owner))
      continue;
    const auto skeleton = unit.gameFlags.find("skeleton_crew_until_own_turn");
    if (skeleton != unit.gameFlags.end() &&
        navalCompletedTurns(s, unit.owner) + 1 >= skeleton->second) {
      unit.gameFlags.erase(skeleton);
      unit.gameFlags.erase("skeleton_crew");
    }
  }
}
} // namespace game::campaign
