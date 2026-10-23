#include "game/campaign_audit.hpp"

#include <iostream>
#include <fstream>
#include <iterator>

int main(int argc,char**argv) {
    using namespace game::campaign;
    try {
        const auto root=std::filesystem::path(GWRL_SOURCE_DIR);
        const auto directory=argc>1?std::filesystem::path(argv[1]):root/"output/campaign_trace";
        const auto seed=argc>2?std::stoull(argv[2]):1936;
        auto initial=loadScenario(root/"game_content/scenarios/japan_china_1936");
        auto rules=campaignRules();auto engine=Engine::start(initial,rules,seed);CampaignAuditLog log(engine);
        Id previousTurn;
        CampaignTraceOptions options{6000,8,seed};
        options.delayedJapaneseWar=argc>3&&std::string(argv[3])=="delayed";
        options.progress=[&](const State&s,std::size_t count){
            const auto serial=std::to_string(s.clock.playerTurnSerial);
            if(serial!=previousTurn){previousTurn=serial;std::cerr<<"Turn "<<serial<<" "<<s.currentNation()<<"; transitions "<<count<<'\n';}
        };
        try {runCampaignTrace(engine,log,options);}
        catch(...) {writeCampaignTrace(directory,log.report(engine));throw;}
        const auto replay=Engine::replay(initial.definition,rules,
            log.report(engine).require("initial_checkpoint").asString(),engine.state().history);
        if(replay.exactReplayIdentity()!=engine.exactReplayIdentity())throw std::runtime_error("Full trace replay differs");
        int turns=0;
        for(const auto&nation:initial.definition->turnOrder){
            if(engine.state().completedTurns.at(nation)!=11)throw std::runtime_error("Trace did not finish eleven turns for every included nation");
            turns+=engine.state().completedTurns.at(nation);
        }
        auto data=log.report(engine).asObject();
        data["provenance"]=game::json::Value(std::string("Engine::start(loadScenario(game_content/scenarios/japan_china_1936)); unchanged approved July1936 position; seeded actual RNG; no dice tape or direct state edits"));
        data["policy"]=game::json::Value(std::string(options.delayedJapaneseWar?"delayed Japanese war until KMT evolution":"early Japanese invasion, Chinese evolution and combined land/air/naval play"));
        data["seed"]=game::json::Value(std::to_string(seed));
        data["national_turns"]=game::json::Value(static_cast<double>(turns));
        data["exact_replay_verified"]=game::json::Value(true);
        game::json::Value::Object hashes;
        for(const auto&file:{"src/campaign_runtime.cpp","src/campaign_state.cpp","src/campaign_setup.cpp",
            "src/campaign_audit.cpp","src/campaign_objective.cpp","src/catalog.cpp","src/movement.cpp",
            "src/economy.cpp","src/economy_lendlease.cpp","src/politics.cpp","src/politics_warlords.cpp",
            "src/politics_influence.cpp","src/air.cpp","src/land_combat.cpp","src/naval.cpp",
            "src/naval_movement.cpp","src/naval_combat.cpp","src/naval_operations.cpp","src/simple_json.cpp",
            "include/game/campaign.hpp","include/game/campaign_audit.hpp","include/game/catalog.hpp",
            "include/game/air.hpp","include/game/economy.hpp","include/game/politics.hpp",
            "include/game/land_combat.hpp","include/game/movement.hpp","include/game/naval.hpp",
            "include/game/simple_json.hpp","tools/campaign_trace.cpp"}) {
            std::ifstream input(root/file,std::ios::binary);
            if(!input)throw std::runtime_error("Missing trace provenance source "+std::string(file));
            const std::string contents((std::istreambuf_iterator<char>(input)),std::istreambuf_iterator<char>());
            hashes[file]=game::json::Value(contentDigest(contents));
        }
        data["runtime_source_sha256"]=game::json::Value(std::move(hashes));
        const game::json::Value report(std::move(data));writeCampaignTrace(directory,report);
        std::cout<<"Campaign trace: "<<report.require("transitions").asArray().size()<<" transitions; "
            <<engine.state().clock.completedRounds<<" rounds; replay/invariants passed\n";
        return 0;
    }catch(const std::exception&e){std::cerr<<"Campaign trace failed: "<<e.what()<<'\n';return 1;}
}
