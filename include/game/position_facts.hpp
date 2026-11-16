#pragma once

#include "game/campaign.hpp"

#include <map>
#include <optional>
#include <set>
#include <tuple>
#include <functional>
#include <utility>

namespace game::campaign {

// Answers derived from one State while that State cannot change: the engine
// generating its menus, or a rule check reading a const probe. Helpers reuse an
// answer only for the exact State object it came from and compute it directly
// for any other State.
class PositionFacts {
  public:
    enum class Fact {
        HostileFighterZones,       // Air rules: Fighter class or type.
        HostileFighterClassZones,  // Movement rules: Fighter class only.
        SeaBlockaded,
        InSupply,
        AirLandingPlan,
        NavalAllowance,
        AirLandingReachable,   // Air rules: joint landing plan with ships still to move.
        AirLandingShortfall,   // Air rules: airborne aircraft that no such plan lands.
        AirLandingStandingShortfall,  // Air rules: those that cannot land as the carriers stand.
        AircraftReturnZones,   // Air rules: zones an airborne or carried aircraft can still reach.
        AircraftAshore,        // Air rules: a friendly land landing within that reach.
        NavalEndZones,         // Naval rules: zones a ship can still end this phase's move in.
    };

    // Lookups compare against the caller's strings without copying them.
    template <class Compute>
    bool remember(Fact fact, const Id& first, const Id& second, Compute&& compute) {
        if (const auto found = answers_.find(std::tie(fact, first, second)); found != answers_.end())
            return found->second;
        const bool answer = compute();
        answers_.emplace(std::make_tuple(fact, first, second), answer);
        return answer;
    }
    // The same for a question about one nation and one zone.
    template <class Compute>
    bool rememberAt(Fact fact, NationId nation, ZoneId zone, Compute&& compute) {
        if (const auto found = zoneAnswers_.find(std::tie(fact, nation, zone)); found != zoneAnswers_.end())
            return found->second;
        const bool answer = compute();
        zoneAnswers_.emplace(std::make_tuple(fact, nation, zone), answer);
        return answer;
    }

    template <class Compute>
    int number(Fact fact, const std::string& key, Compute&& compute) {
        return numberAt(fact, key, ZoneId {}, std::forward<Compute>(compute));
    }
    template <class Compute>
    int numberAt(Fact fact, const std::string& key, ZoneId zone, Compute&& compute) {
        if (const auto found = numbers_.find(std::tie(fact, key, zone)); found != numbers_.end()) return found->second;
        const int answer = compute();
        numbers_.emplace(std::make_tuple(fact, key, zone), answer);
        return answer;
    }

    // Zones found for one unit, by its id.
    template <class Compute>
    const NumberSet<ZoneId>& zones(Fact fact, const Id& unit, Compute&& compute) {
        if (const auto found = zones_.find(std::tie(fact, unit)); found != zones_.end()) return found->second;
        return zones_.emplace(std::make_tuple(fact, unit), compute()).first->second;
    }
    // Zones found for one nation.
    template <class Compute>
    const NumberSet<ZoneId>& nationZones(Fact fact, NationId nation, Compute&& compute) {
        if (const auto found = nationZones_.find(std::tie(fact, nation)); found != nationZones_.end()) return found->second;
        return nationZones_.emplace(std::make_tuple(fact, nation), compute()).first->second;
    }

  private:
    std::map<std::tuple<Fact, Id, Id>, bool, std::less<>> answers_;
    std::map<std::tuple<Fact, NationId, ZoneId>, bool, std::less<>> zoneAnswers_;
    std::map<std::tuple<Fact, std::string, ZoneId>, int, std::less<>> numbers_;
    std::map<std::tuple<Fact, Id>, NumberSet<ZoneId>, std::less<>> zones_;
    std::map<std::tuple<Fact, NationId>, NumberSet<ZoneId>, std::less<>> nationZones_;
};

// Facts for this exact State object while a scope for it is open, else null.
PositionFacts* positionFacts(const State&);

// Opens facts for a State that stays unchanged until the scope closes. Scopes
// nest; one for a State that already has open facts reuses them.
class PositionScope {
  public:
    explicit PositionScope(const State&);
    ~PositionScope();
    PositionScope(const PositionScope&) = delete;
    PositionScope& operator=(const PositionScope&) = delete;

    struct Open {
        const State* state;
        PositionFacts* facts;
        const Open* outer;
    };

  private:
    std::optional<PositionFacts> facts_;
    Open open_ {};
    const Open* previous_;
};

}  // namespace game::campaign
