#include "game/air.hpp"

#include <algorithm>
#include <chrono>
#include <iostream>
#include <stdexcept>

// Standalone, single-thread comparison of the exact same aircraft menu with
// and without the derived geometry view. Link against the CMake gw_engine
// library; optional inputs are saved State or Engine JSON snapshots.
namespace {
using namespace game::campaign;
using V=game::json::Value;
using O=V::Object;
using A=V::Array;

std::string menuDigest(const std::vector<Action>& actions) {
    A encoded;for(const auto& action:actions)encoded.push_back(actionJson(action));
    return contentDigest(canonicalJson(V(std::move(encoded))));
}

V benchmark(const State& indexed,int iterations,const std::string& label) {
    if(!indexed.definition->indexedGeography)throw std::runtime_error("Snapshot has incomplete geography");
    auto source=std::make_shared<Definition>(*indexed.definition);
    source->indexedGeography.reset();
    auto reference=indexed.clone();reference.definition=source;
    const AirRules rules;
    const auto expected=rules.actions(reference);
    const auto fast=rules.actions(indexed);
    const auto digest=menuDigest(expected);
    if(menuDigest(fast)!=digest)throw std::runtime_error("Indexed aircraft menu differs from reference");
    const auto stateBefore=indexed.serialize();
    std::size_t checksum=0;
    auto once=[&](const State& state) {
        const auto start=std::chrono::steady_clock::now();
        checksum+=rules.actions(state).size();
        return std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    };
    double indexedSeconds=0,referenceSeconds=0;
    // Alternating execution order reduces warm-cache/order bias. Menus and
    // mutable states stay identical; no RNG, search budget or rule is changed.
    for(int i=0;i<iterations;++i) {
        if(i%2==0) {referenceSeconds+=once(reference);indexedSeconds+=once(indexed);}
        else {indexedSeconds+=once(indexed);referenceSeconds+=once(reference);}
    }
    if(indexed.serialize()!=stateBefore || reference.serialize()!=stateBefore ||
       menuDigest(rules.actions(indexed))!=digest || menuDigest(rules.actions(reference))!=digest)
        throw std::runtime_error("Benchmark mutated its position/menu");
    return V(O{{"position",V(label)},{"phase",V(toString(indexed.clock.phase))},
        {"round_index",V(static_cast<double>(indexed.clock.roundIndex))},
        {"state_sha256",V(contentDigest(stateBefore))},{"action_sha256",V(digest)},
        {"actions",V(static_cast<double>(expected.size()))},{"iterations_per_path",V(static_cast<double>(iterations))},
        {"reference_seconds",V(referenceSeconds)},{"indexed_seconds",V(indexedSeconds)},
        {"reference_over_indexed",V(referenceSeconds/indexedSeconds)},
        {"checksum",V(static_cast<double>(checksum))},{"matched",V(true)}});
}
}

int main(int argc,char** argv) {
    try {
        if(argc<3)throw std::runtime_error("Usage: benchmark SCENARIO_DIR ITERATIONS [STATE_OR_ENGINE_JSON ...]");
        const int iterations=std::stoi(argv[2]);
        if(iterations<1 || iterations>1000)throw std::runtime_error("Iterations must be within 1..1000");
        const auto initial=loadScenario(argv[1]);
        A results;
        if(argc>3) {
            for(int i=3;i<argc;++i) {
                const auto encoded=game::json::parseFile(argv[i]);
                const auto* state=encoded.find("state");
                results.push_back(benchmark(State::fromJson(initial.definition,state?*state:encoded),iterations,argv[i]));
            }
        } else {
            for(const auto phase:{Phase::CombatMovement,Phase::NonCombatMovement}) {
                auto state=initial.clone();
                const auto japan=std::find(state.definition->turnOrder.begin(),state.definition->turnOrder.end(),"japan");
                if(japan==state.definition->turnOrder.end())throw std::runtime_error("Default fixture requires Japan");
                state.clock.nationIndex=static_cast<int>(japan-state.definition->turnOrder.begin());
                state.clock.playerTurnSerial=state.clock.nationIndex;
                state.clock.phase=phase;
                for(std::size_t i=0;i<state.definition->turnOrder.size();++i)
                    state.completedTurns[state.definition->turnOrder[i]]=i<static_cast<std::size_t>(state.clock.nationIndex)?1:0;
                state.nations.at("japan").atWarWith.insert("kmt");
                state.nations.at("kmt").atWarWith.insert("japan");
                state.captureTurnStart();
                results.push_back(benchmark(state,iterations,"clock-edited setup fixture"));
            }
        }
        const auto& index=*initial.definition->indexedGeography;
        std::cout<<canonicalJson(V(O{{"schema",V("campaign-indexed-geography-benchmark-v1")},
            {"scope",V("Isolated aircraft legal-menu timing; not completed-game throughput")},
            {"nodes",V(static_cast<double>(index.nodeIds.size()))},
            {"distance_bytes",V(static_cast<double>(index.nodeIds.size()*index.nodeIds.size()*sizeof(int)))},
            {"results",V(std::move(results))}}))<<'\n';
        return 0;
    } catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
