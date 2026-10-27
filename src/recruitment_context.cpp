#include "game/recruitment_context.hpp"
#include "game/catalog.hpp"
#include <algorithm>
#include <stdexcept>

namespace game::campaign {
RecruitmentContext::RecruitmentContext(const Engine& engine):definition(engine.state().definition) {
    if(!definition)throw std::invalid_argument("Recruitment requires a definition");
    wireContextFingerprint=DeviceStateContext(engine).wireContextFingerprint;
    const auto ccp=definition->factions.find("ccp");chineseHomePresent=ccp!=definition->factions.end();
    for(const auto& [id,node]:definition->geography.require("nodes").asObject()) {
        territories.push_back(id);
        chineseHome.push_back(chineseHomePresent&&ccp->second.homeCountryKnown&&ccp->second.homeCountry.contains(id));
    }
    catalogPresent=bool(definition->catalog);
    if(catalogPresent)for(const auto& [id,unit]:definition->catalog->units())if(unit.classes.contains("naval"))navalTypes.push_back(id);
    const auto remember=[&](const std::string& text) {
        const auto found=std::find(messages.begin(),messages.end(),text);
        if(found!=messages.end())return static_cast<std::int64_t>(found-messages.begin());
        messages.push_back(text);return static_cast<std::int64_t>(messages.size()-1);
    };
    try {
        const auto* politics=definition->rules.find("politics");
        const auto* zones=politics?politics->find("offshore_land_zone_ids"):nullptr;
        if(!zones)throw std::runtime_error("Recruitment requires reviewed offshore classification");
        for(const auto& item:zones->asArray()) {
            std::array<std::int64_t,3> row{-1,0,0};
            try{row[0]=static_cast<std::int64_t>(offshoreIds.size());offshoreIds.push_back(item.asString());}
            catch(const std::out_of_range& e){row[0]=-1;row[1]=1;row[2]=remember(e.what());}
            catch(const std::exception& e){row[0]=-1;row[1]=2;row[2]=remember(e.what());}
            offshoreSteps.insert(offshoreSteps.end(),row.begin(),row.end());
        }
    }catch(const std::out_of_range& e){offshoreError=1;offshoreMessage=remember(e.what());}
     catch(const std::exception& e){offshoreError=2;offshoreMessage=remember(e.what());}
}
}
