#pragma once

#include "game/campaign.hpp"

namespace game::campaign {

struct CatalogStats {
    std::optional<int> attack;
    std::optional<int> defense;
    int attackDice {0};
    int defenseDice {0};
    std::optional<int> movement;
    std::optional<int> bombardment;
    int bombardmentDice {0};
    std::optional<int> cargoCapacity;
    std::optional<int> carrierCapacity;
};

struct CatalogMode {
    Id id;
    std::optional<int> threshold;
    int dieSides {12};
    int dice {0};
    std::set<Id> requiredTechnologies;
    json::Value parameters;
    json::Value sourceRefs;
};

struct CatalogUpgrade {
    Id to;
    int costIpp {0};
    bool automatic {false};
    std::set<Id> requiredTechnologies;
    json::Value parameters;
    json::Value sourceRefs;
};

struct UnitDefinition {
    Id id;
    std::string name;
    std::set<Id> classes;
    std::vector<int> purchaseCosts;
    std::optional<int> assetValue;
    int maxHits {1};
    std::map<int, CatalogStats> states;
    std::set<Id> targetClasses;
    std::vector<CatalogMode> modes;
    std::set<Id> abilities;
    std::vector<CatalogUpgrade> upgrades;
    json::Value rules;
    json::Value repair;
    json::Value sourceRefs;
    json::Value unresolved;
};

struct FacilityDefinition {
    Id id;
    std::string name;
    std::vector<int> purchaseCosts;
    int assetValue {0};
    std::optional<int> maxDamage;
    std::optional<int> repairCost;
    int productionCapacity {0};
    int repairCapacity {0};
    std::optional<int> aaThreshold;
    int aaDice {0};
    std::set<Id> abilities;
    std::vector<CatalogUpgrade> upgrades;
    json::Value rules;
    json::Value sourceRefs;
};

struct TechnologyDefinition {
    Id id;
    std::string name;
    std::vector<int> thresholds;
    int stageThreeFrom {193907};
    std::set<Id> unlocks;
    std::set<Id> abilities;
    json::Value modifiers;
    json::Value conversions;
    json::Value rules;
    json::Value sourceRefs;
};

struct BuildChartRow {
    Id id;
    Id nation;
    std::string powerStatus;
    Id type;
    std::string kind;
    std::vector<int> purchaseCosts;
    std::optional<int> availableFrom;
    std::optional<int> availableThrough;
    std::set<Id> requiredTechnologies;
    std::set<Id> forbiddenTechnologies;
    std::optional<int> cap;
    std::optional<Id> capGroup;
    std::set<Id> requiredFlags;
    std::set<Id> placement;
    std::optional<Id> upgradesFrom;
    std::optional<Id> derivedFrom;
    json::Value sourceRefs;
    std::string notes;
};

struct CatalogContext {
    Id nation;
    std::string powerStatus;
    int year {1936};
    int month {7};
    std::set<Id> technologies;
    std::map<Id, bool> flags;
    std::set<Id> disabledFlags;
    std::map<Id, int> purchases;
    // Flag maps read in place after flags, in precedence order. Only
    // catalogStats sets them, for a context it uses at once.
    std::vector<const std::map<Id, int>*> flagSources;
};

struct Eligibility {
    bool allowed {false};
    std::vector<std::string> reasons;
};

struct PriceOption {
    std::string method;
    std::vector<int> payments;
};

class Catalog {
  public:
    static std::shared_ptr<const Catalog> load(const std::filesystem::path& directory);
    static std::shared_ptr<const Catalog> fromJson(const json::Value& documents);
    const std::string& fingerprint() const { return fingerprint_; }
    const UnitDefinition& unit(const Id& type) const;
    const FacilityDefinition& facility(const Id& type) const;
    const TechnologyDefinition& technology(const Id& type) const;
    const BuildChartRow& row(const Id& id) const;
    const std::map<Id, UnitDefinition>& units() const { return units_; }
    const std::map<Id, FacilityDefinition>& facilities() const { return facilities_; }
    const std::map<Id, TechnologyDefinition>& technologies() const { return technologies_; }
    const std::map<Id, BuildChartRow>& rows() const { return rows_; }
    const json::Value& sourceData() const { return sourceData_; }
    CatalogStats stats(const Id& type, int damage, const CatalogContext&) const;
    std::vector<CatalogMode> modes(const Id& type, const CatalogContext&, int damage = 0) const;
    Eligibility purchaseEligibility(const Id& rowId, const CatalogContext&, int count = 1) const;
    Eligibility placementEligibility(const Id& rowId, const CatalogContext&) const;
    std::vector<BuildChartRow> purchaseOptions(const CatalogContext&) const;
    std::vector<PriceOption> priceOptions(const Id& rowId, const CatalogContext&) const;
    std::vector<CatalogUpgrade> automaticConversions(const Id& type, const CatalogContext&) const;
    int productionCapacity(const Id& type, int damage, const CatalogContext&) const;
    int repairCapacity(const Id& type, int damage, const CatalogContext& = {}) const;
    std::vector<std::string> unresolvedFields() const;
    void requireComplete() const;

  private:
    std::string fingerprint_;
    json::Value sourceData_;
    std::map<Id, UnitDefinition> units_;
    std::map<Id, FacilityDefinition> facilities_;
    std::map<Id, TechnologyDefinition> technologies_;
    std::map<Id, BuildChartRow> rows_;
};

CatalogContext catalogContext(const State& state, const Id& nation, const std::optional<Id>& zone = std::nullopt);
// Catalog stats under catalogContext(state, nation, zone), reading the state's
// flags in place instead of copying them into a context.
CatalogStats catalogStats(const State& state, const Id& type, int damage, const Id& nation,
                          const std::optional<Id>& zone = std::nullopt);
void initializeCatalogState(State& state);
int completedAssetValue(const Definition& definition, const Id& type);

}  // namespace game::campaign
