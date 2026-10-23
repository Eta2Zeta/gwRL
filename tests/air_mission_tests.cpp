#include "game/air.hpp"
#include "game/catalog.hpp"
#include "game/economy.hpp"
#include "game/land_combat.hpp"
#include "game/movement.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <functional>
#include <iostream>
#include <stdexcept>

namespace {
using namespace game::campaign;
const Id beiping = "land_china_beiping", hopeh = "land_china_hopeh",
         shensi = "land_china_shensi", shantung = "land_china_shantung",
         nanking = "land_china_nanking";
void check(bool ok, const std::string &why) {
  if (!ok)
    throw std::runtime_error(why);
}
State fixture(Phase phase = Phase::CombatMovement) {
  static const auto initial =
      loadScenario(std::filesystem::path(GWRL_SOURCE_DIR) /
                   "game_content/scenarios/japan_china_1936");
  auto s = initial.clone();
  s.units.clear();
  s.facilities.clear();
  s.construction.clear();
  s.repairs.clear();
  s.battles.clear();
  s.battleOrder.clear();
  s.decisions.clear();
  s.chance.reset();
  s.history.clear();
  s.clock.nationIndex = 2;
  s.clock.playerTurnSerial = 2;
  s.clock.phase = phase;
  s.completedTurns["ccp"] = s.completedTurns["mongolia"] = 1;
  s.territories.at(beiping).possessor = "japan";
  s.territories.at(shantung).possessor = "japan";
  s.territories.at(hopeh).possessor = "kmt";
  s.nations.at("japan").atWarWith.insert("kmt");
  s.nations.at("kmt").atWarWith.insert("japan");
  s.captureTurnStart();
  return s;
}
void add(State &s, const Id &id, const Id &type, const Id &owner,
         const Id &zone) {
  UnitState u;
  u.id = id;
  u.type = type;
  u.owner = owner;
  u.zone = u.turnOrigin = zone;
  u.movementAllowance = u.movementRemaining =
      s.definition->catalog->stats(type, 0, catalogContext(s, owner, zone))
          .movement;
  s.units[id] = std::move(u);
}
std::shared_ptr<const Rules> rules() {
  return std::make_shared<PoliticsRules>(
      std::make_shared<MovementRules>(std::make_shared<LandCombatRules>(
          std::make_shared<AirRules>(std::make_shared<EconomyRules>()))));
}
Action select(
    const std::vector<Action> &actions, const Id &kind,
    const std::function<bool(const Action &)> &match = [](const Action &) {
      return true;
    }) {
  const auto a =
      std::find_if(actions.begin(), actions.end(),
                   [&](const auto &x) { return x.kind == kind && match(x); });
  if (a == actions.end())
    throw std::runtime_error("Missing action " + kind);
  return *a;
}
void choose(
    Engine &e, const Id &kind,
    const std::function<bool(const Action &)> &match = [](const Action &) {
      return true;
    }) {
  e.step(select(e.legalActions(), kind, match));
}
void declareRocket(Engine &e) {
  choose(e, "air_rocket_attack", [](const auto &a) {
    return a.parameters.require("target").asString() == "factory";
  });
  choose(e, "end_phase");
  choose(e, "air_begin_bombing");
}
void rocketRadarBeforeDamage() {
  auto s = fixture();
  add(s, "rocket", "strategic_rocket", "japan", beiping);
  s.facilities["factory"] = {"factory", "major_factory", hopeh, 0, {}};
  s.nations.at("kmt").technologyStages["radar"] = 4;
  Engine hit(s, rules());
  hit.setDiceTapeForTesting({1});
  declareRocket(hit);
  check(hit.state().chance && hit.state().chance->purpose == "air_rocket_aa",
        "Radar rocket AAA did not precede damage");
  hit.resolveChance();
  check(!hit.state().units.contains("rocket") &&
            hit.state().facilities.at("factory").damage == 0 &&
            hit.state().battles.empty(),
        "Intercepted rocket dealt damage or survived");
  Engine miss(s, rules());
  miss.setDiceTapeForTesting({12, 6});
  const auto initial = miss.serialize();
  declareRocket(miss);
  miss.resolveChance();
  check(miss.state().chance &&
            miss.state().chance->purpose == "air_bomb_damage",
        "Surviving rocket did not proceed to damage");
  miss.resolveChance();
  check(miss.state().facilities.at("factory").damage == 6 &&
            !miss.state().units.contains("rocket") &&
            miss.state().battles.empty(),
        "Rocket damage/one-use consumption incorrect");
  const auto replay =
      Engine::replay(s.definition, rules(), initial, miss.state().history);
  check(replay.exactReplayIdentity() == miss.exactReplayIdentity(),
        "Radar rocket replay diverged");
}
void rocketWithoutRadar() {
  auto s = fixture();
  add(s, "rocket", "strategic_rocket", "japan", beiping);
  s.facilities["factory"] = {"factory", "major_factory", hopeh, 0, {}};
  Engine e(s, rules());
  e.setDiceTapeForTesting({4});
  declareRocket(e);
  check(e.state().chance && e.state().chance->purpose == "air_bomb_damage",
        "Rocket faced AAA without Radar");
  e.resolveChance();
  check(e.state().facilities.at("factory").damage == 4 &&
            !e.state().units.contains("rocket") && e.state().battles.empty(),
        "Unopposed rocket did not finish as a consumed unit");
}
void selectedSurpriseBombingUsesFirstStrikeWithoutRemovingFacilityAA() {
  auto s=fixture();s.nations.at("kmt").powerStatus="major";
  s.nations.at("japan").turnFlags["surprise_attack_available"]=1;
  s.nations.at("japan").turnFlags["surprise_attack_target:kmt"]=1;
  add(s,"bomber","medium_bomber","japan",beiping);add(s,"escort","fighter","japan",beiping);
  add(s,"local","fighter","kmt",hopeh);add(s,"adjacent","fighter","kmt",shensi);
  s.territories.at(shensi).possessor="kmt";s.facilities["base"]={"base","airbase",shensi,0,{}};
  s.facilities["factory"]={"factory","major_factory",hopeh,0,{}};s.captureTurnStart();
  Engine e(s,rules(),32);e.setDiceTapeForTesting({1,12,4,12,12});const auto checkpoint=e.serialize();
  choose(e,"land_select_surprise_zone",[](const auto& a){return a.parameters.require("zone").asString()==hopeh;});
  choose(e,"air_bomb",[](const auto& a){return a.parameters.require("target").asString()=="factory";});
  choose(e,"air_escort");choose(e,"end_phase");choose(e,"air_begin_bombing");
  check(e.state().decisions.back().kind=="air_interception"&&
        e.state().decisions.back().options.front().parameters.require("unit").asString()=="local",
        "Surprise bombing allowed an adjacent scrambling interceptor");
  choose(e,"air_intercept");
  check(e.state().chance&&e.state().chance->dice.size()==2,"Surprise bombing did not fire Japanese interception first strike separately");
  e.resolveChance();choose(e,"air_choose_casualty");
  check(!e.state().units.contains("local")&&e.state().units.contains("adjacent")&&
        e.state().chance&&e.state().chance->purpose=="air_bomb_damage",
        "Eliminated interceptor returned fire or adjacent aircraft joined Surprise bombing");
  e.resolveChance();check(e.state().chance&&e.state().chance->purpose=="air_facility_aa",
        "Strategic Surprise bombing incorrectly inherited the port-only inherent-AAA exemption");
  e.resolveChance();choose(e,"air_land");choose(e,"air_land");
  check(e.state().facilities.at("factory").damage==4&&e.state().battles.empty(),"Selected Surprise bombing did not complete");
  auto replay=Engine::replay(s.definition,rules(),checkpoint,e.state().history);
  check(replay.exactReplayIdentity()==e.exactReplayIdentity(),"Surprise interception first strike replay diverged");
}
void rocketRangeIgnoresAircraftInterceptionAndRequiresNoTransport() {
  auto s=fixture();add(s,"rocket","strategic_rocket","japan",beiping);
  add(s,"blocker","fighter","kmt",hopeh);s.facilities["factory"]={"factory","major_factory",shensi,0,{}};
  s.territories.at(shensi).possessor="kmt";
  const auto actions=AirRules{}.actions(s);
  check(std::any_of(actions.begin(),actions.end(),[](const auto& a){return a.kind=="air_rocket_attack"&&
      a.parameters.require("zone").asString()==shensi;}),"Enemy fighter transit incorrectly screened a rocket's range");
  s.territories.at(hopeh).possessor="ccp";
  const auto neutral=AirRules{}.actions(s);
  check(std::none_of(neutral.begin(),neutral.end(),[](const auto& a){return a.kind=="air_rocket_attack"&&
      a.parameters.require("zone").asString()==shensi;}),"A rocket fired over a nation neither at war nor Aligned");
  add(s,"ship","naval_transport","japan",beiping);attachCargo(s,"ship","rocket");
  const auto carried=AirRules{}.actions(s);
  check(std::none_of(carried.begin(),carried.end(),[](const auto& a){return a.kind=="air_rocket_attack";}),
        "A transported rocket fired directly from its transport");
}
void artilleryCityBombingStaysAdjacentAndBypassesAirDefence() {
  for(const auto& type:{Id("advanced_artillery"),Id("advanced_self_propelled_artillery")}) {
    auto s=fixture();add(s,"gun",type,"japan",shantung);add(s,"lift","heavy_air_transport","japan",shantung);
    add(s,"interceptor","fighter","kmt",nanking);
    add(s,"aaa","anti_aircraft_artillery","kmt",nanking);
    s.facilities["fort"]={"fort","fortification",nanking,0,{}};
    s.nations.at("kmt").technologyStages["radar"]=4;s.captureTurnStart();
    Engine e(s,rules(),77);e.setDiceTapeForTesting({6});const auto checkpoint=e.serialize();
    choose(e,"air_artillery_city_bomb");
    check(e.state().units.at("gun").zone==shantung&&e.state().units.at("gun").movementRemaining==0&&
          e.state().units.at("gun").commitments.contains("attrition"),"City bombardment moved its artillery or retained movement");
    for(const auto& a:e.legalActions())check(a.kind!="air_artillery_city_bomb"&&
        !(a.kind=="land_declare_attrition"&&a.parameters.require("unit").asString()=="gun"),
        "City-bombarding artillery declared another mission");
    choose(e,"end_phase");choose(e,"air_begin_bombing");
    check(e.state().decisions.empty()&&e.state().chance&&e.state().chance->purpose=="air_bomb_damage"&&
          e.state().chance->dice.size()==1&&e.state().chance->dice.front().sides==6,
          "Artillery faced interception or rolled attrition hits instead of1D6 city damage");
    e.resolveChance();
    check(e.state().territories.at(nanking).flags.at("city_damage")==6&&e.state().battles.empty()&&
          !e.state().chance&&e.state().decisions.empty()&&e.state().units.at("gun").zone==shantung&&
          e.state().units.contains("interceptor")&&e.state().units.contains("aaa"),
          "Artillery bombardment used aircraft AAA, fort attrition reduction, or a landing phase");
    choose(e,"end_phase");for(const auto& a:e.legalActions())check(
        !(a.kind=="movement_route"&&a.parameters.require("unit").asString()=="gun")&&
        !(a.kind=="air_load"&&a.parameters.require("cargo").asString()=="gun"),
        "City-bombarding artillery moved during Noncombat Movement");
    auto replay=Engine::replay(s.definition,rules(),checkpoint,e.state().history);
    check(replay.exactReplayIdentity()==e.exactReplayIdentity(),"Artillery city-bombing replay diverged");
  }
}
void artilleryCityBombingRequiresAnUnmovedStartingNeighbor() {
  for(int invalid=0;invalid<5;++invalid) {
    auto s=fixture();add(s,"gun",invalid==4?"artillery":"advanced_artillery","japan",shantung);s.captureTurnStart();
    if(invalid==0)s.units.at("gun").route={shantung};
    if(invalid==1)s.units.at("gun").turnFlags["placed_this_turn"]=1;
    if(invalid==2)s.turnStart.units.erase("gun");
    if(invalid==3)s.units.at("gun").commitments.insert("attrition");
    const auto options=AirRules{}.actions(s);
    check(std::none_of(options.begin(),options.end(),[](const auto& a){return a.kind=="air_artillery_city_bomb";}),
          "City bombardment ignored its unit, starting-adjacency, movement or once-per-turn condition");
  }
  auto distant=fixture();add(distant,"gun","advanced_artillery","japan",beiping);distant.captureTurnStart();
  for(const auto& a:AirRules{}.actions(distant))if(a.kind=="air_artillery_city_bomb")
    check(a.parameters.require("zone").asString()!=nanking,"Artillery bombarded a nonadjacent city");
}
void artilleryCityDestructionUsesTheExistingTechnologyChoice() {
  auto s=fixture();add(s,"gun","advanced_artillery","japan",shantung);s.captureTurnStart();
  s.territories.at(nanking).flags["city_damage"]=44;s.nations.at("kmt").technologyStages["radar"]=1;
  Engine e(s,rules());e.setDiceTapeForTesting({1});choose(e,"air_artillery_city_bomb");
  choose(e,"end_phase");choose(e,"air_begin_bombing");e.resolveChance();
  check(e.state().territories.at(nanking).flags.at("city_destroyed")==1&&
        e.state().decisions.back().kind=="air_destroyed_city_technology","Artillery city destruction omitted technology loss");
  choose(e,"air_choose_technology_loss");
  check(e.state().nations.at("kmt").technologyStages.at("radar")==0&&e.state().battles.empty()&&
        e.state().units.contains("gun"),"Artillery city destruction did not complete after its technology choice");
}
void destroyedCityTechnologyChoice() {
  auto s = fixture();
  s.territories.at(nanking).possessor = "kmt";
  s.territories.at(nanking).flags["city_damage"] = 44;
  s.nations.at("kmt").technologyStages["radar"] = 1;
  s.nations.at("kmt").technologyStages["improved_logistics"] = 2;
  add(s, "bomber", "medium_bomber", "japan", shantung);
  s.captureTurnStart();
  Engine e(s, rules());
  e.setDiceTapeForTesting({1, 12});
  choose(e, "air_bomb", [](const auto &a) {
    return a.parameters.require("kind").asString() == "city" &&
           a.parameters.require("target").asString() == nanking;
  });
  choose(e, "end_phase");
  choose(e, "air_begin_bombing");
  check(e.state().chance->purpose == "air_bomb_damage",
        "City damage did not begin");
  e.resolveChance();
  check(e.state().territories.at(nanking).flags.at("city_destroyed") == 1 &&
            !e.state().decisions.empty() &&
            e.state().decisionPlayer() == "axis",
        "City destruction did not give attacker technology-loss choice");
  const auto restored = Engine::restore(s.definition, rules(), e.serialize());
  check(restored.planningKey() == e.planningKey(),
        "City technology-loss continuation did not survive checkpoint");
  choose(e, "air_choose_technology_loss", [](const auto &a) {
    return a.parameters.require("technology").asString() == "radar";
  });
  check(e.state().nations.at("kmt").technologyStages.at("radar") == 0 &&
            e.state().nations.at("kmt").technologyStages.at(
                "improved_logistics") == 2,
        "City destruction changed unchosen technology");
}
State scrambledFixture() {
  auto s = fixture(Phase::Combat);
  s.territories.at(shensi).possessor = "kmt";
  s.captureTurnStart();
  add(s, "attacker", "infantry", "japan", hopeh);
  add(s, "defender", "infantry", "kmt", hopeh);
  add(s, "scrambler", "fighter", "kmt", shensi);
  s.facilities["base"] = {"base", "airbase", shensi, 0, {}};
  const auto id = registerLandBattle(s, hopeh, "japan", {"attacker"},
                                     {{"attacker", beiping}});
  beginAirDefence(s, id);
  check(!s.decisions.empty(), "Scramble choice missing");
  const auto choice = select(s.decisions.back().options, "air_scramble");
  AirRules{}.apply(s, choice);
  check(s.units.at("scrambler").zone == hopeh,
        "Scrambled fighter did not reach defended battle");
  finishAirCombat(s, id);
  s.battles.clear();
  s.battleOrder.clear();
  return s;
}
void scrambleReturnAtPhaseEnd() {
  auto s = scrambledFixture();
  const int remaining = *s.units.at("scrambler").movementRemaining;
  check(s.units.at("scrambler").zone == hopeh &&
            s.units.at("scrambler").turnFlags.at("scrambled") == 1,
        "Scrambler returned before all Combat Phase battles ended");
  AirRules{}.finishPhase(s);
  check(s.units.at("scrambler").zone == shensi &&
            s.units.at("scrambler").movementRemaining == remaining &&
            !s.units.at("scrambler").turnFlags.contains("scrambled"),
        "Surviving scrambler did not return without spending movement");
  auto bombed = scrambledFixture();
  applyFacilityBombDamage(bombed, "base", 1);
  AirRules{}.finishPhase(bombed);
  check(bombed.units.contains("scrambler") &&
            bombed.units.at("scrambler").zone == shensi,
        "Scrambler could not return to friendly originating land after its "
        "base was damaged");
  auto captured = scrambledFixture();
  changePossession(captured, shensi, "japan", PossessionCause::Capture,
                   "japan");
  check(captured.units.contains("scrambler") &&
            captured.units.at("scrambler").zone == hopeh,
        "Scrambler was resolved before Combat Phase ended");
  AirRules{}.finishPhase(captured);
  check(!captured.units.contains("scrambler"),
        "Scrambler survived loss of its original base in a later battle");
}
void immediatePatrolLandingLoss() {
  auto s = fixture(Phase::Combat);
  s.territories.at(beiping).possessor = "kmt";
  s.territories.at(nanking).possessor = "japan";
  s.territories.at(shantung).possessor = "japan";
  s.territories.at(hopeh).possessor = "japan";
  s.captureTurnStart();
  add(s, "patrol", "fighter", "kmt", "sea_p14");
  auto &patrol = s.units.at("patrol");
  patrol.gameFlags["on_map"] = 1;
  patrol.gameFlags["map_range"] = 1;
  patrol.commitments.insert("maritime_air_patrol");
  enforcePatrolLandingAvailability(s);
  check(s.units.contains("patrol"),
        "Patrol with held landing spot was eliminated");
  changePossession(s, beiping, "japan", PossessionCause::Capture, "japan");
  check(!s.units.contains("patrol"),
        "Patrol survived immediate loss of its last landing spot");
}
void pairedAircraftBlitz() {
  auto s = fixture(Phase::Combat);
  add(s, "armor", "light_armor", "japan", beiping);
  add(s, "fighter", "fighter", "japan", beiping);
  auto &fighter = s.units.at("fighter");
  fighter.turnFlags["blitz_eligible"] = 1;
  fighter.commitments.insert("blitz_with:armor");
  auto before = AirRules{}.actions(s);
  check(std::none_of(before.begin(), before.end(),
                     [](const auto &a) { return a.kind == "air_blitz"; }),
        "Aircraft blitzed before paired armor moved");
  auto &armor = s.units.at("armor");
  armor.zone = hopeh;
  armor.commitments.insert("blitz_from:" + beiping);
  armor.commitments.insert("blitz_to:" + hopeh);
  const auto battle =
      registerLandBattle(s, hopeh, "japan", {"armor"}, {{"armor", beiping}});
  const auto remaining = *fighter.movementRemaining;
  const auto action = select(AirRules{}.actions(s), "air_blitz");
  AirRules{}.apply(s, action);
  check(s.units.at("fighter").zone == hopeh &&
            s.units.at("fighter").movementRemaining == remaining - 1 &&
            !s.units.at("fighter").turnFlags.contains("blitz_eligible"),
        "Paired aircraft blitz did not consume its route and eligibility");
  const auto &attackers = s.battles.at(battle).attackers;
  check(std::find(attackers.begin(), attackers.end(), "fighter") !=
            attackers.end(),
        "Aircraft blitz failed to join armor's pending battle");
}
} // namespace
int main() {
  try {
    rocketRadarBeforeDamage();
    rocketWithoutRadar();
    selectedSurpriseBombingUsesFirstStrikeWithoutRemovingFacilityAA();
    rocketRangeIgnoresAircraftInterceptionAndRequiresNoTransport();
    artilleryCityBombingStaysAdjacentAndBypassesAirDefence();
    artilleryCityBombingRequiresAnUnmovedStartingNeighbor();
    artilleryCityDestructionUsesTheExistingTechnologyChoice();
    destroyedCityTechnologyChoice();
    scrambleReturnAtPhaseEnd();
    immediatePatrolLandingLoss();
    pairedAircraftBlitz();
    std::cout << "11 air mission fixture groups passed\n";
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
