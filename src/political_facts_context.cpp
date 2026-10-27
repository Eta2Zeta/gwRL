#include "game/political_facts_context.hpp"
#include "game/device_state.hpp"

#include <algorithm>
#include <stdexcept>

namespace game::campaign {
PoliticalFactsContext::PoliticalFactsContext(const Engine& engine):definition(engine.state().definition),
    wireContextFingerprint(DeviceStateContext(engine).wireContextFingerprint) {
    if(!definition||definition->fingerprint.empty())throw std::invalid_argument("Political facts require a frozen definition");
    const auto message=[&](const std::string& text){
        auto found=std::find(messages.begin(),messages.end(),text);
        if(found==messages.end()){messages.push_back(text);return static_cast<std::int64_t>(messages.size()-1);}
        return static_cast<std::int64_t>(std::distance(messages.begin(),found));
    };
    const auto& nodes=definition->geography.require("nodes").asObject();
    for(const auto& [id,node]:nodes){
        territories.push_back(id);std::int64_t value=0,error=0,text=-1;
        try{value=node.require("ipp_value").asInt();}
        catch(const std::out_of_range& e){error=1;text=message(e.what());}
        catch(const std::exception& e){error=2;text=message(e.what());}
        ipp.insert(ipp.end(),{value,error,text});
    }
    for(const auto& [id,_]:definition->factions)nations.push_back(id);
    chineseHome.assign(territories.size(),0);
    try {
        const auto& ccp=definition->factions.at("ccp");
        if(ccp.homeCountryKnown)for(std::size_t t=0;t<territories.size();++t)
            chineseHome[t]=ccp.homeCountry.contains(territories[t]);
    }catch(const std::out_of_range& e){homeError=1;homeMessage=message(e.what());}
     catch(const std::exception& e){homeError=2;homeMessage=message(e.what());}
}
} // namespace game::campaign
