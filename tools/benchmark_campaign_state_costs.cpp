#include "game/campaign.hpp"

#include <chrono>
#include <cmath>
#include <ctime>
#include <iostream>
#include <stdexcept>

// Single-thread primitive timings, deliberately separate from search/game
// throughput. The direct finite walk is a prototype of the existing final
// JSON-number validation, not a substitute for structural State::validate.
namespace {
using namespace game::campaign;
using V=game::json::Value;
using O=V::Object;
using A=V::Array;
using Steady=std::chrono::steady_clock;

std::size_t finiteNumbers(const V& value) {
    if(value.isNumber()) {
        if(!std::isfinite(value.asNumber()))throw std::runtime_error("JSON numbers must be finite");
        return 1;
    }
    if(value.isNull() || value.isBool() || value.isString())return 1;
    std::size_t visited=1;
    if(value.isArray())for(const auto& item:value.asArray())visited+=finiteNumbers(item);
    else for(const auto& [key,item]:value.asObject())visited+=finiteNumbers(item);
    return visited;
}

std::size_t finiteStatePayloads(const State& state) {
    std::size_t visited=finiteNumbers(state.actionInterface);
    for(const auto& [id,value]:state.politics.pending)visited+=finiteNumbers(value);
    for(const auto& decision:state.decisions)for(const auto& action:decision.options)visited+=finiteNumbers(action.parameters);
    for(const auto& [id,battle]:state.battles)visited+=finiteNumbers(battle.data);
    for(const auto& event:state.history)visited+=finiteNumbers(event.payload);
    return visited;
}

template<class Function>
V measure(const std::string& name,int repetitions,const Steady::time_point deadline,
          std::size_t& checksum,Function operation) {
    const auto start=Steady::now();
    const auto cpuStart=std::clock();
    for(int i=0;i<repetitions;++i) {
        if(Steady::now()>=deadline)throw std::runtime_error("Ten-second timing budget exhausted");
        checksum+=operation();
    }
    return V(O{{"operation",V(name)},{"repetitions",V(static_cast<double>(repetitions))},
        {"wall_seconds",V(std::chrono::duration<double>(Steady::now()-start).count())},
        {"process_cpu_seconds",V(static_cast<double>(std::clock()-cpuStart)/CLOCKS_PER_SEC)}});
}

V benchmark(const State& state,int repetitions,const std::string& source,
            const Steady::time_point deadline) {
    const auto full=state.toJson();
    const auto planning=state.toJson(false);
    const auto fullBytes=canonicalJson(full);
    const auto planningBytes=canonicalJson(planning);
    const auto initialKey=state.planningKey();
    std::size_t checksum=0;
    A timings;
    timings.push_back(measure("state_clone",repetitions,deadline,checksum,[&] {
        const auto copy=state.clone();return copy.units.size()+copy.history.size();
    }));
    timings.push_back(measure("state_validate_current",repetitions,deadline,checksum,[&] {state.validate();return std::size_t{1};}));
    timings.push_back(measure("to_json_with_history",repetitions,deadline,checksum,[&] {return state.toJson().asObject().size();}));
    timings.push_back(measure("canonical_prebuilt_full_json",repetitions,deadline,checksum,[&] {return canonicalJson(full).size();}));
    timings.push_back(measure("to_json_and_canonical_with_history",repetitions,deadline,checksum,[&] {return canonicalJson(state.toJson()).size();}));
    timings.push_back(measure("to_json_and_canonical_without_history",repetitions,deadline,checksum,[&] {return canonicalJson(state.toJson(false)).size();}));
    timings.push_back(measure("sha_prebuilt_without_history_bytes",repetitions,deadline,checksum,[&] {return contentDigest(planningBytes).size();}));
    timings.push_back(measure("state_planning_key_current",repetitions,deadline,checksum,[&] {return state.planningKey().size();}));
    timings.push_back(measure("direct_finite_payload_walk_prototype_only",repetitions,deadline,checksum,[&] {return finiteStatePayloads(state);}));
    if(canonicalJson(state.toJson())!=fullBytes || state.planningKey()!=initialKey)
        throw std::runtime_error("State primitive timing changed its input");
    return V(O{{"source",V(source)},{"round_index",V(static_cast<double>(state.clock.roundIndex))},
        {"phase",V(toString(state.clock.phase))},{"state_sha256",V(contentDigest(fullBytes))},
        {"planning_key",V(initialKey)},{"state_bytes",V(static_cast<double>(fullBytes.size()))},
        {"without_history_bytes",V(static_cast<double>(planningBytes.size()))},
        {"history_events",V(static_cast<double>(state.history.size()))},
        {"history_bytes",V(static_cast<double>(canonicalJson(full.require("history")).size()))},
        {"finite_payload_nodes",V(static_cast<double>(finiteStatePayloads(state)))},
        {"checksum",V(static_cast<double>(checksum))},{"timings",V(std::move(timings))}});
}
}

int main(int argc,char** argv) {
    try {
        if(argc<4)throw std::runtime_error("Usage: benchmark SCENARIO_DIR REPETITIONS STATE_OR_ENGINE_JSON [...]");
        const int repetitions=std::stoi(argv[2]);
        if(repetitions<1 || repetitions>10000)throw std::runtime_error("Repetitions must be within1..10000");
        const auto initial=loadScenario(argv[1]);
        // Load/validate snapshots outside all timing, retaining their history.
        std::vector<State> states;
        for(int i=3;i<argc;++i) {
            const auto encoded=game::json::parseFile(argv[i]);
            const auto* state=encoded.find("state");
            states.push_back(State::fromJson(initial.definition,state?*state:encoded));
        }
        const auto start=Steady::now(),deadline=start+std::chrono::seconds(10);
        A results;
        for(std::size_t i=0;i<states.size();++i)
            results.push_back(benchmark(states[i],repetitions,argv[i+3],deadline));
        std::cout<<canonicalJson(V(O{{"schema",V("campaign-state-costs-benchmark-v1")},
            {"scope",V("Matched state primitives; finite-only prototype excludes structural checks; not game throughput")},
            {"threads",V(1.0)},{"wall_seconds",V(std::chrono::duration<double>(Steady::now()-start).count())},
            {"results",V(std::move(results))}}))<<'\n';
        return 0;
    } catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
