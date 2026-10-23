#include "game/catalog.hpp"
#include "game/economy.hpp"
#include "game/movement.hpp"
#include "game/politics.hpp"

#include <algorithm>
#include <functional>
#include <iostream>
#include <stdexcept>

namespace {
using namespace game::campaign;
using V = game::json::Value;
const auto root = std::filesystem::path(GWRL_SOURCE_DIR);
const Id tokyo = "land_jap_tokyo", shensi = "land_china_shensi", nanking = "land_china_nanking",
         beiping = "land_china_beiping";
void check(bool yes, const std::string &why) {
    if (!yes)
        throw std::runtime_error(why);
}
void rejects(const std::function<void()> &f, const std::string &why) {
    try {
        f();
    } catch (const std::exception &) {
        return;
    }
    throw std::runtime_error(why);
}
const State &baseline() {
    static const auto s = loadScenario(root / "game_content/scenarios/japan_china_1936");
    return s;
}
void turn(State &s, const Id &nation, Phase phase = Phase::Production, int round = 0) {
    s.clock.roundIndex = s.clock.completedRounds = round;
    const auto &order = s.definition->turnOrder;
    s.clock.nationIndex = static_cast<int>(std::find(order.begin(), order.end(), nation) - order.begin());
    s.clock.playerTurnSerial = static_cast<std::uint64_t>(round * order.size() + s.clock.nationIndex);
    s.clock.phase = phase;
    s.clock.incomeCollected = false;
    for (std::size_t i = 0; i < order.size(); ++i)
        s.completedTurns[order[i]] = round + (i < static_cast<std::size_t>(s.clock.nationIndex));
    s.nations.at(nation).turnFlags.clear();
    s.captureTurnStart();
    MovementRules{}.beginTurn(s);
    beginEconomyTurn(s);
}
State fixture(const Id &nation = "japan") {
    auto s = baseline().clone();
    turn(s, nation);
    return s;
}
Action pick(
    const State &s, const Id &kind,
    const std::function<bool(const Action &)> &predicate = [](const auto &) { return true; }) {
    auto options = economyActions(s);
    auto leases = lendLeaseActions(s);
    options.insert(options.end(), leases.begin(), leases.end());
    for (const auto &a : options)
        if (a.kind == kind && predicate(a))
            return a;
    throw std::runtime_error("Missing action " + kind);
}
bool offers(
    const State &s, const Id &kind,
    const std::function<bool(const Action &)> &predicate = [](const auto &) { return true; }) {
    try {
        (void)pick(s, kind, predicate);
        return true;
    } catch (...) {
        return false;
    }
}
void finishResearch(State &s) {
    if (offers(s, "economy_finish_research"))
        applyEconomyAction(s, pick(s, "economy_finish_research"));
}
void buy(State &s, const Id &row, const Id &price = "printed") {
    applyEconomyAction(s, pick(s, "economy_purchase", [&](const auto &a) {
                           return a.parameters.require("row").asString() == row &&
                                  a.parameters.require("price").asString() == price;
                       }));
}
void addUnit(State &s, const Id &id, const Id &type, const Id &nation, const Id &zone, int damage = 0) {
    UnitState u;
    u.id = id;
    u.type = type;
    u.owner = nation;
    u.zone = u.turnOrigin = zone;
    u.damage = damage;
    u.movementAllowance = u.movementRemaining =
        s.definition->catalog->stats(type, damage, catalogContext(s, nation, zone)).movement;
    s.units.emplace(id, std::move(u));
}
int paid(const State &s) {
    int n = 0;
    for (const auto &[id, p] : s.construction)
        n += p.paidIpp;
    return n;
}
void income() {
    auto s = fixture();
    check(evaluateIncome(s, "japan").total == 15, "Japan local initial income");
    check(evaluateIncome(s, "kmt").total == 6, "KMT initial income");
    check(evaluateIncome(s, "ccp").total == 2, "CCP initial income");
    check(!evaluateIncome(s, "mongolia").collectable, "Mongolia has no ordinary income");
    s.territories.at(beiping).possessor = "japan";
    check(evaluateIncome(s, "japan").total == 18, "Japan gets China bonus without Major war");
    s.territories.at(beiping).flags["city_damage"] = 20;
    s.territories.at(beiping).flags["city_ipp_lost"] = 1;
    check(evaluateIncome(s, "japan").total == 17, "City bombing changes territorial income");
    s.territories.at(beiping).flags["city_damage"] = 0;
    check(evaluateIncome(s, "japan").total == 17, "City repair does not restore permanent IPP");
    s.territories.at(tokyo).possessor = "ccp";
    check(evaluateIncome(s, "japan").total == 0 && !evaluateIncome(s, "japan").collectable,
          "Capital loss prevents collection");
    refreshIncome(s);
    check(s.nations.at("japan").incomeKnown, "Income state known");
}
void stagedQueues() {
    auto s = fixture();
    finishResearch(s);
    check(paid(s) == 10, "Opening paid amount retained");
    for (const auto &id : {"japan_queue_heavy_cruiser", "japan_queue_fleet_carrier"})
        applyEconomyAction(s, pick(s, "economy_advance", [&](const auto &a) {
                               return a.parameters.require("project").asString() == id;
                           }));
    check(*s.nations.at("japan").treasury == 5 && paid(s) == 20, "Advance charges only actual next stages");
    check(!offers(s, "economy_advance"), "Cannot pay twice in one Player Turn");
    check(s.construction.at("japan_queue_heavy_cruiser").remainingPayments.empty() &&
              s.construction.at("japan_queue_fleet_carrier").remainingPayments == std::vector<int>{5},
          "Opening stage progression");
    s.clock.phase = Phase::PlaceUnits;
    const auto before = s.units.size();
    applyEconomyAction(s, pick(s, "economy_place", [](const auto &a) {
                           return a.parameters.require("project").asString() == "japan_queue_heavy_cruiser";
                       }));
    check(s.units.size() == before + 1 && !s.construction.contains("japan_queue_heavy_cruiser") &&
              paid(s) == 10,
          "Completed asset replaces construction once");
    EconomyRules{}.finishTurn(s);
    check(*s.nations.at("japan").treasury == 20, "First-turn accounting");
    EconomyRules{}.finishTurn(s);
    check(*s.nations.at("japan").treasury == 20, "Income cannot collect twice");
    s.validate();
    turn(s, "japan", Phase::Production, 1);
    finishResearch(s);
    applyEconomyAction(s, pick(s, "economy_advance", [](const auto &a) {
                           return a.parameters.require("project").asString() == "japan_queue_fleet_carrier";
                       }));
    s.clock.phase = Phase::PlaceUnits;
    applyEconomyAction(s, pick(s, "economy_place", [](const auto &a) {
                           return a.parameters.require("project").asString() == "japan_queue_fleet_carrier";
                       }));
    check(paid(s) == 0 && *s.nations.at("japan").treasury == 15,
          "Second-turn carrier completion preserves every IPP");
    s.validate();
}
void productionRepair() {
    auto s = fixture();
    s.construction.clear();
    s.nations.at("japan").treasury = 100;
    for (auto it = s.facilities.begin(); it != s.facilities.end();)
        if (it->second.type.find("factory") != Id::npos && it->first != "setup_japan_tokyo_major_factory")
            it = s.facilities.erase(it);
        else
            ++it;
    s.facilities.at("setup_japan_tokyo_major_factory").damage = 3;
    turn(s, "japan");
    finishResearch(s);
    check(facilityCapacity(s, "japan", "setup_japan_tokyo_major_factory") == 2,
          "Damaged Major Factory capacity");
    applyEconomyAction(s, pick(s, "economy_repair", [](const auto &a) {
                           return a.parameters.require("target").asString() ==
                                      "setup_japan_tokyo_major_factory" &&
                                  a.parameters.require("damage").asInt() == 3;
                       }));
    buy(s, "japan_major_infantry");
    buy(s, "japan_major_infantry");
    check(!offers(
              s, "economy_purchase",
              [](const auto &a) { return a.parameters.require("row").asString() == "japan_major_infantry"; }),
          "Cannot exceed beginning capacity");
    s.clock.phase = Phase::PlaceUnits;
    while (offers(s, "economy_place"))
        applyEconomyAction(s, pick(s, "economy_place"));
    check(s.facilities.at("setup_japan_tokyo_major_factory").damage == 3,
          "Repair remains pending until placement end");
    finishEconomyPlacement(s);
    check(s.facilities.at("setup_japan_tokyo_major_factory").damage == 0 &&
              *s.nations.at("japan").treasury == 91,
          "Repairs and infantry conserve 9 IPP");
    check(facilityCapacity(s, "japan", "setup_japan_tokyo_major_factory") == 0,
          "Repair cannot increase same-turn production");
    turn(s, "japan", Phase::Production, 1);
    check(facilityCapacity(s, "japan", "setup_japan_tokyo_major_factory") == 5,
          "Next-turn repaired capacity");
    s.validate();
}
void decentralizedAndMilitia() {
    auto s = fixture("ccp");
    s.nations.at("ccp").treasury = 30;
    buy(s, "ccp_minor_infantry");
    buy(s, "ccp_minor_cavalry");
    s.clock.phase = Phase::PlaceUnits;
    check(offers(s, "economy_place",
                 [](const auto &a) { return a.parameters.require("zone").asString() == shensi; }),
          "CCP decentralized placement without factory/supply");
    while (offers(s, "economy_place"))
        applyEconomyAction(s, pick(s, "economy_place"));
    turn(s, "ccp");
    s.territories.at(nanking).possessor = "ccp";
    s.territories.at(nanking).flags["last_possession_change_turn"] =
        static_cast<int>(s.clock.playerTurnSerial);
    buy(s, "ccp_minor_infantry");
    s.clock.phase = Phase::PlaceUnits;
    check(!offers(s, "economy_place",
                  [](const auto &a) { return a.parameters.require("zone").asString() == nanking; }),
          "Captured this turn cannot receive decentralized production");
    auto j = fixture();
    j.construction.clear();
    j.nations.at("japan").treasury = 100;
    finishResearch(j);
    int purchases = 0;
    while (offers(j, "economy_purchase", [](const auto &a) {
        return a.parameters.require("row").asString() == "japan_major_militia";
    })) {
        buy(j, "japan_major_militia");
        check(++purchases < 100, "Militia purchasing must have finite per-zone capacity");
    }
    check(purchases > 0, "Militia placement capacity available");
}
void research() {
    auto s = fixture();
    s.nations.at("japan").technologyStages["radar"] = 2;
    turn(s, "japan", Phase::Production, 5);
    check(!offers(s, "economy_research",
                  [](const auto &a) { return a.parameters.require("technology").asString() == "radar"; }),
          "January1939 stageIII locked");
    turn(s, "japan", Phase::Production, 6);
    applyEconomyAction(s, pick(s, "economy_research", [](const auto &a) {
                           return a.parameters.require("technology").asString() == "radar";
                       }));
    const auto r = *s.chance;
    s.chance.reset();
    applyEconomyChance(s, r, ChanceOutcome{{{1}}});
    check(s.nations.at("japan").technologyStages.at("radar") == 3, "Research advances exact stage");
    check(!offers(s, "economy_research",
                  [](const auto &a) { return a.parameters.require("technology").asString() == "radar"; }),
          "Research technology once per calendar turn");
    auto t = fixture();
    t.nations.at("japan").technologyStages["airborne_doctrine"] = 3;
    addUnit(t, "airborne", "airborne_infantry", "japan", tokyo);
    applyEconomyAction(t, pick(t, "economy_research", [](const auto &a) {
                           return a.parameters.require("technology").asString() == "airborne_doctrine";
                       }));
    const auto req = *t.chance;
    t.chance.reset();
    applyEconomyChance(t, req, ChanceOutcome{{{1}}});
    check(t.units.at("airborne").type == "elite_airborne_infantry", "Technology conversion immediate");
    t.validate();
    auto f = fixture();
    f.nations.at("japan").technologyStages["improved_factories"] = 4;
    check(facilityCapacity(f, "japan", "setup_japan_tokyo_major_factory") == 8,
          "Technology capacity benefit immediate");
}
void constructionAndCapture() {
    auto s = fixture();
    s.construction.clear();
    s.nations.at("japan").treasury = 100;
    finishResearch(s);
    applyEconomyAction(s, pick(s, "economy_purchase", [](const auto &a) {
                           return a.parameters.require("row").asString() == "japan_major_major_factory" &&
                                  a.parameters.require("zone").asString() == tokyo;
                       }));
    const auto id = s.construction.begin()->first;
    turn(s, "japan", Phase::Production, 1);
    finishResearch(s);
    applyEconomyAction(s, pick(s, "economy_advance"));
    check(s.construction.at(id).paidIpp == 12, "Facility two paid stages");
    auto five = s.clone();
    damageConstruction(five, id, 5);
    check(five.construction.at(id).remainingPayments == std::vector<int>({6, 6}) &&
              five.construction.at(id).flags.at("damage") == 2 && five.construction.at(id).paidIpp == 12,
          "Printed five-damage setback example preserves cumulative paid");
    damageConstruction(s, id, 6);
    check(!s.construction.contains(id), "Printed six-damage construction destruction example");
    auto c = fixture();
    c.facilities.at("setup_japan_tokyo_major_factory").damage = 12;
    changePossession(c, tokyo, "ccp", PossessionCause::Capture, "ccp");
    check(c.facilities.at("setup_japan_tokyo_major_factory").type == "minor_factory" &&
              c.facilities.at("setup_japan_tokyo_major_factory").damage == 12,
          "Captured Major Factory downgrades retaining original damage cap");
    c.validate();
    changePossession(c, tokyo, "japan", PossessionCause::Liberation, "japan");
    check(c.facilities.at("setup_japan_tokyo_major_factory").type == "major_factory",
          "Original owner recovers factory tier");
    c.validate();
}
void cityAndRailRepair() {
    auto s = fixture();
    s.nations.at("japan").treasury = 100;
    s.territories.at(tokyo).flags["city_damage"] = 25;
    s.territories.at(tokyo).flags["city_ipp_lost"] = 1;
    finishResearch(s);
    applyEconomyAction(s, pick(s, "economy_repair", [](const auto &a) {
                           return a.parameters.require("target").asString() == tokyo &&
                                  a.parameters.require("damage").asInt() == 25;
                       }));
    s.validate();
    s.clock.phase = Phase::PlaceUnits;
    finishEconomyPlacement(s);
    check(s.territories.at(tokyo).flags.at("city_damage") == 0 && effectiveTerritorialIpp(s, tokyo) == 1 &&
              *s.nations.at("japan").treasury == 75,
          "City repairs cost actual damage without restoring IPP");
    turn(s, "japan", Phase::Production, 1);
    s.territories.at(tokyo).flags["city_destroyed"] = 1;
    s.territories.at(tokyo).flags["city_damage"] = 60;
    finishResearch(s);
    check(!offers(s, "economy_repair",
                  [](const auto &a) { return a.parameters.require("target").asString() == tokyo; }),
          "Destroyed city cannot repair");
    const auto rail = std::find_if(s.rails.begin(), s.rails.end(), [&](const auto &item) {
        return s.territories.at(item.second.endpointA).possessor == "japan";
    });
    check(rail != s.rails.end(), "Owned rail fixture");
    const auto id = rail->first, own = rail->second.endpointA, other = rail->second.endpointB;
    rail->second.damageByEndpoint[own] = 1;
    rail->second.damageByEndpoint[other] = 1;
    applyEconomyAction(s, pick(s, "economy_repair", [&](const auto &a) {
                           return a.parameters.require("target").asString() == id &&
                                  a.parameters.require("endpoint").asString() == own;
                       }));
    s.validate();
    s.clock.phase = Phase::PlaceUnits;
    finishEconomyPlacement(s);
    check(s.rails.at(id).damageByEndpoint.at(own) == 0 && s.rails.at(id).damageByEndpoint.at(other) == 1,
          "Rail repair preserves opposite side damage");
    s.validate();
}
void ladaoLease() {
    auto s = fixture();
    s.construction.clear();
    ensureDadao(s);
    s.territories.at(beiping).possessor = "dadao";
    turn(s, "japan");
    s.nations.at("japan").treasury = 100;
    finishResearch(s);
    check(s.definition->factions.at("dadao").homeCountry.empty(), "Dadao general homeland unchanged");
    check(lendLeasePermitted(s, "japan", "dadao"), "Named Japan-to-Dadao permission");
    buy(s, "japan_major_infantry");
    const auto id = s.construction.begin()->first;
    applyEconomyAction(s, pick(s, "economy_lease_declare", [&](const auto &a) {
                           return a.parameters.require("project").asString() == id &&
                                  a.parameters.require("recipient").asString() == "dadao";
                       }));
    check(!offers(s, "economy_lease_upgrade",
                  [](const auto &a) { return a.parameters.require("recipient").asString() == "dadao"; }),
          "Only one declaration per recipient per PlayerTurn");
    s.clock.phase = Phase::PlaceUnits;
    const auto count = s.units.size();
    applyEconomyAction(s, pick(s, "economy_lease_deliver", [](const auto &a) {
                           return a.parameters.require("zone").asString() == beiping;
                       }));
    check(s.units.size() == count + 1 && !s.construction.contains(id),
          "RCL010 delivers in Dadao possessed Chinese HomeCountry");
    check(std::any_of(s.units.begin(), s.units.end(),
                      [](const auto &x) {
                          return x.second.owner == "dadao" && x.second.zone == beiping &&
                                 x.second.type == "infantry";
                      }),
          "Delivered unit has recipient identity");
    s.validate();
}
void sharedShipyardRepair() {
    auto s = fixture();
    s.construction.clear();
    s.nations.at("japan").treasury = 100;
    for (auto it = s.facilities.begin(); it != s.facilities.end();)
        if (it->second.type.find("shipyard") != Id::npos && it->first != "facility_tokyo_major_shipyard")
            it = s.facilities.erase(it);
        else
            ++it;
    const auto seas = navalFacilitySeaZones(s, "facility_tokyo_major_shipyard");
    check(!seas.empty(), "Shipyard coast");
    addUnit(s, "repair_carrier", "fleet_carrier", "japan", seas.front(), 1);
    turn(s, "japan");
    finishResearch(s);
    applyEconomyAction(s, pick(s, "economy_repair", [](const auto &a) {
                           return a.parameters.require("target").asString() == "repair_carrier";
                       }));
    check(*s.nations.at("japan").treasury == 100 &&
              facilityCapacity(s, "japan", "facility_tokyo_major_shipyard") == 4,
          "Capital repair costs zero IPP and shares shipyard slots");
    for (int i = 0; i < 4; ++i)
        buy(s, "japan_major_destroyer");
    check(!offers(s, "economy_purchase",
                  [](const auto &a) {
                      return a.parameters.require("row").asString() == "japan_major_destroyer";
                  }),
          "Shared repair reservation limits ship production");
    s.clock.phase = Phase::PlaceUnits;
    while (offers(s, "economy_place"))
        applyEconomyAction(s, pick(s, "economy_place"));
    finishEconomyPlacement(s);
    check(s.units.at("repair_carrier").damage == 0 && *s.nations.at("japan").treasury == 72,
          "Four ships cost28; one carrier repairfree");
    s.validate();
}
void upgradesDiscountsAndCaps() {
    auto s = fixture();
    s.construction.clear();
    s.nations.at("japan").treasury = 100;
    s.nations.at("japan").technologyStages["improved_construction"] = 4;
    finishResearch(s);
    const auto target = "setup_japan_kyushu_medium_factory";
    applyEconomyAction(
        s, pick(s, "economy_purchase", [&](const auto &a) {
            return a.parameters.require("row").asString() == "japan_major_medium_factory_to_major_factory" &&
                   a.parameters.require("price").asString() == "improved_construction_discount";
        }));
    check(*s.nations.at("japan").treasury == 95, "Improved Construction discounts facility upgrade");
    s.clock.phase = Phase::PlaceUnits;
    applyEconomyAction(s, pick(s, "economy_place", [&](const auto &a) {
                           return a.parameters.require("target").asString() == target;
                       }));
    check(s.facilities.at(target).type == "major_factory" && facilityCapacity(s, "japan", target) == 3,
          "Upgraded factory retains starting tier capacity this turn");
    turn(s, "japan", Phase::Production, 1);
    check(facilityCapacity(s, "japan", target) == 5, "Upgraded capacity next turn");
    finishResearch(s);
    buy(s, "japan_major_battleship", "improved_construction_combine");
    check(s.construction.begin()->second.paidIpp == 12 &&
              s.construction.begin()->second.remainingPayments == std::vector<int>{6},
          "Combine original first two stages without simultaneous discount");
    buy(s, "japan_major_marine");
    buy(s, "japan_major_marine");
    check(
        !offers(s, "economy_purchase",
                [](const auto &a) { return a.parameters.require("row").asString() == "japan_major_marine"; }),
        "National specialty cap executes");
    check(!offers(s, "economy_purchase",
                  [](const auto &a) {
                      return a.parameters.require("row").asString() == "japan_major_medium_armor";
                  }),
          "1940 unit gate executes");
}
void foreignRailConsent() {
    auto s = fixture();
    s.construction.clear();
    s.nations.at("japan").treasury = 100;
    ensureDadao(s);
    const Id from = "land_manchuria_rehe", to = "land_china_suiyuan";
    s.territories.at(to).possessor = "dadao";
    turn(s, "japan");
    finishResearch(s);
    auto request = pick(s, "economy_request_rail", [&](const auto &a) {
        return a.parameters.require("zone").asString() == from &&
               a.parameters.require("border").asString() == to;
    });
    const auto cash = *s.nations.at("japan").treasury;
    applyEconomyAction(s, request);
    check(!s.decisions.empty() && s.decisions.back().nation == "dadao" &&
              *s.nations.at("japan").treasury == cash,
          "Foreign owner consent before spending");
    applyEconomyAction(s, pick(s, "economy_decline_rail"));
    check(s.construction.empty(), "Declined railroad leaves no construction");
    applyEconomyAction(s, request);
    applyEconomyAction(s, pick(s, "economy_approve_rail"));
    check(s.construction.size() == 1 && *s.nations.at("japan").treasury < cash,
          "Approved railroad purchases at actual terrain cost");
    s.clock.phase = Phase::PlaceUnits;
    const auto count = s.rails.size();
    applyEconomyAction(s, pick(s, "economy_place"));
    check(s.rails.size() == count + 1, "Dynamic railroad created once");
    s.validate();
}
void leaseCredits() {
    auto s = fixture();
    s.construction.clear();
    s.nations.at("japan").treasury = 100;
    ensureDadao(s);
    s.territories.at(beiping).possessor = "dadao";
    addUnit(s, "dadao_militia", "militia", "dadao", beiping);
    turn(s, "japan");
    finishResearch(s);
    applyEconomyAction(s, pick(s, "economy_lease_upgrade", [](const auto &a) {
                           return a.parameters.require("recipient").asString() == "dadao";
                       }));
    s.clock.phase = Phase::PlaceUnits;
    applyEconomyAction(s, pick(s, "economy_lease_deliver", [](const auto &a) {
                           return a.parameters.require("zone").asString() == beiping;
                       }));
    check(!offers(s, "economy_lease_place"), "Recipient upgrade waits until next recipient placement phase");
    turn(s, "japan", Phase::PlaceUnits, 1);
    check(offers(s, "economy_lease_place"),
          "Dadao upgrade available in next Japan-controlled placement slot");
    applyEconomyAction(s, pick(s, "economy_lease_place"));
    check(s.units.at("dadao_militia").type == "infantry" && *s.nations.at("japan").treasury == 98,
          "Delivered militia credit upgrades recipient for2paidIPP");
    s.validate();
    auto r = fixture();
    r.construction.clear();
    r.nations.at("japan").treasury = 100;
    ensureDadao(r);
    r.territories.at(beiping).possessor = "dadao";
    FacilityState f;
    f.id = "dadao_damaged_base";
    f.type = "airbase";
    f.zone = beiping;
    f.damage = 2;
    r.facilities.emplace(f.id, f);
    turn(r, "japan");
    finishResearch(r);
    applyEconomyAction(r, pick(r, "economy_lease_repair", [](const auto &a) {
                           return a.parameters.require("target").asString() == "dadao_damaged_base";
                       }));
    r.clock.phase = Phase::PlaceUnits;
    applyEconomyAction(r, pick(r, "economy_lease_deliver", [](const auto &a) {
                           return a.parameters.require("zone").asString() == beiping;
                       }));
    finishEconomyPlacement(r);
    check(r.facilities.at(f.id).damage == 2, "Lend-leased repairs wait recipient next turn");
    turn(r, "japan", Phase::PlaceUnits, 1);
    finishEconomyPlacement(r);
    check(r.facilities.at(f.id).damage == 0 && *r.nations.at("japan").treasury == 98,
          "Funded recipient facility repair conserves2IPP");
    r.validate();
}
void accountingReplay() {
    auto state = fixture();
    finishResearch(state);
    auto rules = std::make_shared<EconomyRules>();
    Engine engine(state, rules, 9);
    const auto checkpoint = engine.serialize();
    const auto count = engine.state().history.size();
    auto purchase = pick(engine.state(), "economy_purchase", [](const auto &a) {
        return a.parameters.require("row").asString() == "japan_major_infantry";
    });
    engine.step(purchase);
    const auto copy = Engine::restore(state.definition, rules, engine.serialize());
    check(copy.exactReplayIdentity() == engine.exactReplayIdentity(),
          "Economy checkpoint includes paid queues/cash");
    std::vector<Event> events(engine.state().history.begin() + static_cast<std::ptrdiff_t>(count),
                              engine.state().history.end());
    const auto replay = Engine::replay(state.definition, rules, checkpoint, events);
    check(replay.exactReplayIdentity() == engine.exactReplayIdentity(), "Economy action replay exact");
    auto all = Engine::start(baseline().clone(), rules, 19);
    int actions = 0;
    while (!all.state().terminal) {
        const auto legal = all.legalActions();
        const auto research = std::find_if(legal.begin(), legal.end(),
                                           [](const auto &a) { return a.kind == "economy_finish_research"; });
        const auto end =
            std::find_if(legal.begin(), legal.end(), [](const auto &a) { return a.kind == "end_phase"; });
        check(research != legal.end() || end != legal.end(),
              "Accounting-only fixture must advance all44nationalturns");
        all.step(research != legal.end() ? *research : *end);
        check(++actions < 300, "Accounting fixture finite");
    }
    check(*all.state().nations.at("japan").treasury == 180 && *all.state().nations.at("kmt").treasury == 72 &&
              *all.state().nations.at("ccp").treasury == 24,
          "Eleven complete rounds collect exact territorial accounts");
    check(paid(all.state()) == 10, "Unadvanced opening queue paid value unchanged throughout");
}

void replacementUpgradeAndEliteLease() {
    auto s = fixture();
    s.construction.clear();
    s.nations.at("japan").treasury = 100;
    addUnit(s, "militia_original", "militia", "japan", tokyo);
    addUnit(s, "militia_replacement", "militia", "japan", tokyo);
    finishResearch(s);
    buy(s, "japan_major_militia_to_infantry");
    s.units.erase("militia_original");
    s.clock.phase = Phase::PlaceUnits;
    applyEconomyAction(s, pick(s, "economy_place", [](const auto &a) {
                           return a.parameters.require("target").asString() == "militia_replacement";
                       }));
    check(s.units.at("militia_replacement").type == "infantry",
          "Purchased upgrade can select another surviving suitable unit");
    s.validate();
    auto e = fixture();
    e.construction.clear();
    e.nations.at("japan").treasury = 100;
    ensureDadao(e);
    e.territories.at(beiping).possessor = "dadao";
    e.nations.at("japan").technologyStages["airborne_doctrine"] = 4;
    turn(e, "japan");
    finishResearch(e);
    buy(e, "japan_major_elite_airborne_infantry");
    applyEconomyAction(e, pick(e, "economy_lease_declare", [](const auto &a) {
                           return a.parameters.require("recipient").asString() == "dadao";
                       }));
    e.clock.phase = Phase::PlaceUnits;
    applyEconomyAction(e, pick(e, "economy_lease_deliver", [](const auto &a) {
                           return a.parameters.require("zone").asString() == beiping;
                       }));
    check(std::any_of(e.units.begin(), e.units.end(),
                      [](const auto &item) {
                          return item.second.owner == "dadao" && item.second.zone == beiping &&
                                 item.second.type == "airborne_infantry";
                      }),
          "Explicit RB47 EliteAirborne lend-lease exception downgrades for receiver without doctrine");
    e.validate();
}

} // namespace
int main() {
    try {
        int count = 0;
        for (const auto &test : {income, stagedQueues, productionRepair, decentralizedAndMilitia, research,
                                 constructionAndCapture, cityAndRailRepair, ladaoLease, sharedShipyardRepair,
                                 upgradesDiscountsAndCaps, foreignRailConsent, leaseCredits, accountingReplay,
                                 replacementUpgradeAndEliteLease}) {
            test();
            ++count;
        }
        std::cout << count << " economy fixture groups passed\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "Economy test failure: " << e.what() << '\n';
        return 1;
    }
}
