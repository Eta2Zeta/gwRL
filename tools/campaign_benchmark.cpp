#include "game/campaign.hpp"

#include <chrono>
#include <iostream>
#include <memory>

namespace {
using namespace game::campaign;

// Explicit measurement fixture, not an implementation of production or combat.
class BenchmarkRules final : public Rules {
  public:
    Id id() const override { return "m2_control_flow_benchmark_v1"; }
    std::vector<Action> actions(const State&) const override { return {}; }
    bool phaseComplete(const State&) const override { return true; }
    void apply(State&, const Action&) const override { throw std::runtime_error("No benchmark gameplay action"); }
    void applyChance(State&, const ChanceRequest&, const ChanceOutcome&) const override {
        throw std::runtime_error("No benchmark chance event");
    }
    void finishTurn(State& state) const override { state.clock.incomeCollected = true; }
};

template<class Function> double measure(int iterations, Function operation) {
    const auto start = std::chrono::steady_clock::now();
    for (int index = 0; index < iterations; ++index) operation();
    const double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
    return iterations / seconds;
}
}

int main(int argc, char** argv) {
    try {
        const std::filesystem::path path = argc > 1 ? argv[1]
            : std::filesystem::path(GWRL_SOURCE_DIR) / "game_content/scenarios/japan_china_1936";
        const State initial = loadScenario(path);
        auto rules = std::make_shared<BenchmarkRules>();
        Engine engine = Engine::start(initial, rules, 42);
        std::size_t checksum = 0;
        const double clones = measure(2000, [&] { const auto copy = initial.clone(); checksum += copy.units.size(); });
        const double legal = measure(5000, [&] { checksum += engine.legalActions().size(); });
        const double keys = measure(200, [&] { checksum += initial.planningKey().size(); });
        const double transitions = measure(440, [&] {
            if (engine.state().terminal) engine = Engine::start(initial, rules, 42);
            engine.step(engine.legalActions().front());
        });
        std::cout << "{\n"
            << "  \"scope\": \"M2 control-flow fixture, 99 real setup units; no gameplay handlers\",\n"
            << "  \"clone_per_second\": " << clones << ",\n"
            << "  \"legal_actions_per_second\": " << legal << ",\n"
            << "  \"planning_keys_per_second\": " << keys << ",\n"
            << "  \"transition_per_second\": " << transitions << ",\n"
            << "  \"checksum\": " << checksum << "\n}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Benchmark failed: " << error.what() << '\n';
        return 1;
    }
}
