#include "game/relations_context.hpp"
#include "game/politics.hpp"
#include "game/movement.hpp"
#include <algorithm>
#include <limits>
#include <stdexcept>

namespace game::campaign {
namespace {
std::size_t product(std::size_t a,std::size_t b) {
    if(b&&a>std::numeric_limits<std::size_t>::max()/b)throw std::length_error("Relations allocation overflow");
    return a*b;
}
template<class F> void query(std::int64_t& value,std::int64_t& error,F function) {
    try{value=function();}catch(const std::out_of_range&){error=1;}catch(const std::exception&){error=2;}
}
}
RelationsContext::RelationsContext(std::shared_ptr<const Definition> value):definition(std::move(value)) {
    if(!definition)throw std::invalid_argument("Relations context requires a definition");
    for(const auto& [id,faction]:definition->factions)nations.push_back(id);
    players.assign(definition->players.begin(),definition->players.end());
    for(const auto& id:nations)warlords.push_back(isWarlord(id));
    const auto china=definition->factions.find("ccp");chineseHomeValid=china!=definition->factions.end();
    for(const auto& [id,node]:definition->geography.require("nodes").asObject()) {
        territories.push_back(id);chineseHome.push_back(chineseHomeValid&&china->second.homeCountryKnown&&china->second.homeCountry.contains(id));
    }
}
RelationsOracleBatch::RelationsOracleBatch(std::shared_ptr<const RelationsContext> value,std::size_t count):
    context(std::move(value)),rows(count) {
    if(!context)throw std::invalid_argument("Missing relations context");
    const auto N=context->nations.size(),nodes=product(count,N),pairsCount=product(product(nodes,N),7);
    pairs.assign(pairsCount,0);pairErrors.assign(pairsCount,0);
    nations.assign(product(nodes,3),0);nationErrors.assign(product(nodes,3),0);present.assign(nodes,0);
    landAttack.assign(product(nodes,N),0);landAttackErrors.assign(product(nodes,N),0);
}
void RelationsOracleBatch::capture(std::size_t row,const State& state) {
    if(row>=rows)throw std::out_of_range("Relations oracle lane");
    if(!state.definition||state.definition->fingerprint!=context->definition->fingerprint)
        throw std::invalid_argument("Relations context definition mismatch");
    const auto N=context->nations.size();
    for(std::size_t a=0;a<N;++a){const auto& actor=context->nations[a];const auto ni=(row*N+a)*3;
        present[row*N+a]=state.nations.contains(actor);
        query(nations[ni],nationErrors[ni],[&] {
            // Native recursive politicalPlayer has no cycle guard. Reject a
            // cycle before calling it rather than allowing oracle stack overflow.
            auto current=actor;std::set<Id> visited;
            while(true){const auto& n=state.nations.at(current);if(n.player)break;
                if(!n.controllerNation)break;
                if(!visited.insert(current).second)throw std::runtime_error("Cyclic political controller");
                current=*n.controllerNation;}
            const auto result=politicalPlayer(state,actor);
            const auto it=std::find(context->players.begin(),context->players.end(),result);
            if(it==context->players.end())throw std::runtime_error("Unknown political player");
            return static_cast<std::int64_t>(it-context->players.begin());
        });
        query(nations[ni+1],nationErrors[ni+1],[&]{return atWarWithMajor(state,actor);});
        query(nations[ni+2],nationErrors[ni+2],[&]{return movementController(state,actor);});
        for(std::size_t b=0;b<N;++b){const auto& owner=context->nations[b];const auto base=((row*N+a)*N+b)*7;
            query(pairs[base],pairErrors[base],[&]{return controlledBy(state,actor,owner);});
            query(pairs[base+1],pairErrors[base+1],[&]{return areAtWar(state,actor,owner);});
            query(pairs[base+2],pairErrors[base+2],[&]{return politicallyFriendly(state,actor,owner);});
            query(pairs[base+3],pairErrors[base+3],[&]{return logisticsFriendly(state,actor,owner);});
            query(pairs[base+4],pairErrors[base+4],[&]{return state.nations.at(actor).alliance==state.nations.at(owner).alliance;});
            query(pairs[base+5],pairErrors[base+5],[&]{const auto& n=state.nations.at(actor);return n.alliance&&n.alliance==state.nations.at(owner).alliance;});
            query(pairs[base+6],pairErrors[base+6],[&]{return strategicRailPermission(state,actor,owner);});
            query(landAttack[(row*N+a)*N+b],landAttackErrors[(row*N+a)*N+b],
                  [&]{return mayDeclareWar(state,actor,owner,DeclarationMode::LandAttack).allowed;});
        }
    }
}
}
