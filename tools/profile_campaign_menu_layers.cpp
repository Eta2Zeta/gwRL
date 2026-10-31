// Native cost breakdown at a serialized three-round training position: legal-menu
// generation per composed rules layer, clone/validate/key costs and one transition
// per action kind. Positions come from `tools/decision_census.py export`.
//
//   g++ -O2 -std=c++20 -I include -DGWRL_SOURCE_DIR='"'"$PWD"'"' \
//       tools/profile_campaign_menu_layers.cpp build/<dir>/libgw_engine.a -o build/profile_menu_layers
//   build/profile_menu_layers POSITION.json [repetitions]
#include "game/air.hpp"
#include "game/campaign_actions.hpp"
#include "game/campaign_env.hpp"
#include "game/economy.hpp"
#include "game/land_combat.hpp"
#include "game/movement.hpp"
#include "game/naval.hpp"
#include "game/politics.hpp"
#include "game/position_facts.hpp"

#include <chrono>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>

using namespace game::campaign;
using Steady = std::chrono::steady_clock;

template <class F>
double timeMs(int repetitions, F operation) {
    const auto start = Steady::now();
    for (int i = 0; i < repetitions; ++i) operation();
    return std::chrono::duration<double, std::milli>(Steady::now() - start).count() / repetitions;
}

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "usage: profile_menu_layers POSITION.json [repetitions]\n";
        return 2;
    }
    const int repetitions = argc > 2 ? std::stoi(argv[2]) : 5;
    std::ifstream input(argv[1]);
    std::stringstream buffer;
    buffer << input.rdbuf();
    auto env = CampaignEnv::curriculum(std::filesystem::path(GWRL_SOURCE_DIR) / "game_content/scenarios/japan_china_1936",
                                       3, 1, true);
    env.restore(buffer.str());
    const State& state = env.engine().state();

    // The same decorator order as campaignRules(), built up one layer at a time.
    auto economy = std::make_shared<EconomyRules>();
    auto air = std::make_shared<AirRules>(economy);
    auto land = std::make_shared<LandCombatRules>(air);
    auto naval = std::make_shared<NavalRules>(land);
    auto movement = std::make_shared<MovementRules>(naval);
    auto politics = std::make_shared<PoliticsRules>(movement);
    auto training = trainingCampaignRules();
    const std::vector<std::pair<std::string, std::shared_ptr<const Rules>>> layers{
        {"economy", economy}, {"+air", air}, {"+land", land}, {"+naval", naval},
        {"+movement", movement}, {"+politics", politics}, {"+training", training}};
    std::cout << "history_events " << state.history.size() << " units " << state.units.size() << "\n";
    double previous = 0;
    for (const auto& [name, rules] : layers) {
        std::size_t count = 0;
        // The engine opens a position scope while it builds a menu, which enables the
        // per-position answers; each repetition gets a fresh one.
        const double ms = timeMs(repetitions, [&] {
            const PositionScope scope(state);
            count = rules->actions(state).size();
        });
        std::cout << "layer " << name << " actions=" << count << " cumulative_ms=" << ms
                  << " increment_ms=" << ms - previous << "\n";
        previous = ms;
    }
    // The complete engine menu from an engine with no cached menu.
    std::size_t engineCount = 0;
    const double engineMs = timeMs(repetitions, [&] {
        Engine fresh(state, training);
        engineCount = fresh.legalActions().size();
    });
    std::cout << "engine_menu_ms " << engineMs << " actions=" << engineCount << "\n";
    const auto menu = env.legalActions();
    std::map<std::string, int> kinds;
    for (const auto& action : menu) ++kinds[action.kind];
    for (const auto& [kind, count] : kinds) std::cout << "menu_kind " << kind << " " << count << "\n";
    std::cout << "engine_clone_ms " << timeMs(repetitions * 20, [&] { auto copy = env.engine().clone(); (void)copy; }) << "\n";
    std::cout << "state_validate_ms " << timeMs(repetitions * 4, [&] { state.validate(); }) << "\n";
    std::cout << "planning_key_ms " << timeMs(repetitions * 4, [&] { auto key = state.planningKey(); (void)key; }) << "\n";
    std::map<std::string, double> steps;
    for (const auto& action : menu) {
        if (steps.contains(action.kind)) continue;
        steps[action.kind] = timeMs(repetitions, [&] {
            Engine copy = env.engine().clone();
            copy.step(action);
        });
    }
    for (const auto& [kind, ms] : steps) std::cout << "transition_ms " << kind << " " << ms << "\n";
    return 0;
}
