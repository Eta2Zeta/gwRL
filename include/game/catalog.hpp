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

// The unit types and unit classes the rules name in their code. Each list is
// the single source for its names: a member of KnownUnitTypes or
// KnownUnitClasses is spelled as the catalog string it holds the number of, and
// loading a catalog that lacks one of them fails (Catalog::fromJson). A rule
// asks whether a unit is militia with `u.type == known.militia`, an integer
// compare. Add a name here when a rule starts to name it.
#define GWRL_KNOWN_UNIT_TYPES(X) \
    X(advanced_artillery) X(advanced_mechanized_infantry) X(advanced_self_propelled_artillery) \
    X(advanced_submarine) X(air_transport) X(airborne_infantry) X(anti_aircraft_artillery) \
    X(artillery) X(attack_naval_transport) X(battlecruiser) X(battleship) X(cavalry) \
    X(destroyer) X(elite_airborne_infantry) X(fighter) X(foreign_legion) X(gurkha) \
    X(heavy_air_transport) X(heavy_armor) X(heavy_battleship) X(heavy_cruiser) \
    X(heavy_fleet_carrier) X(infantry) X(jet_fighter) X(katyusha_rocket_artillery) \
    X(light_armor) X(marine) X(mechanized_infantry) X(medium_armor) X(medium_bomber) X(militia) \
    X(motorized_infantry) X(naval_transport) X(panzergrenadier) X(seaplane) \
    X(self_propelled_artillery) X(strategic_rocket) \
    X(t_34) X(tactical_bomber) X(tiger_i)
#define GWRL_UNIT_CLASSES(X) \
    X(aircraft) X(anti_aircraft_artillery_class) X(artillery_class) \
    X(capital_ship) X(carrier) X(fighter) X(infantry_class) X(land) X(naval) X(naval_transport) \
    X(rocket) X(strategic_bomber) X(submarine) X(surface_ship) X(surface_warship) \
    X(vehicle_class)

struct KnownUnitTypes {
#define GWRL_MEMBER(name) UnitTypeId name;
    GWRL_KNOWN_UNIT_TYPES(GWRL_MEMBER)
#undef GWRL_MEMBER
};
struct KnownUnitClasses {
#define GWRL_MEMBER(name) UnitClassId name;
    GWRL_UNIT_CLASSES(GWRL_MEMBER)
#undef GWRL_MEMBER
};

struct UnitDefinition {
    Id id;
    UnitTypeId number;  // id's number in the catalog's unit type table.
    std::string name;
    NumberSet<UnitClassId> classes;  // Numbers in the catalog's unit class table.
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
    // Unit types and classes by number (include/game/names.hpp): the tables
    // number the catalog's names, and units() lists the unit types in number
    // order, which is name order. unit(name) and isUnitType(name) are for the
    // places that read a name, such as a build-chart row's type.
    const NameTable<UnitTypeKind>& unitTypes() const { return unitTypes_; }
    const NameTable<UnitClassKind>& unitClasses() const { return unitClasses_; }
    const KnownUnitTypes& knownUnitTypes() const { return knownUnitTypes_; }
    const KnownUnitClasses& knownUnitClasses() const { return knownUnitClasses_; }
    const UnitDefinition& unit(UnitTypeId type) const;
    const UnitDefinition& unit(const Id& type) const;
    bool isUnitType(const Id& type) const { return unitTypes_.contains(type); }
    // Whether a unit type is of the class a name read from data names, such as
    // one of a hit's target classes; false for a name that is no unit class.
    bool unitHasClass(UnitTypeId type, std::string_view className) const {
        const auto found = unitClasses_.find(className);
        return found && unit(type).classes.contains(*found);
    }
    const FacilityDefinition& facility(const Id& type) const;
    const TechnologyDefinition& technology(const Id& type) const;
    const BuildChartRow& row(const Id& id) const;
    const std::vector<UnitDefinition>& units() const { return units_; }
    const std::map<Id, FacilityDefinition>& facilities() const { return facilities_; }
    const std::map<Id, TechnologyDefinition>& technologies() const { return technologies_; }
    const std::map<Id, BuildChartRow>& rows() const { return rows_; }
    const json::Value& sourceData() const { return sourceData_; }
    CatalogStats stats(UnitTypeId type, int damage, const CatalogContext&) const;
    std::vector<CatalogMode> modes(UnitTypeId type, const CatalogContext&, int damage = 0) const;
    Eligibility purchaseEligibility(const Id& rowId, const CatalogContext&, int count = 1) const;
    Eligibility placementEligibility(const Id& rowId, const CatalogContext&) const;
    std::vector<BuildChartRow> purchaseOptions(const CatalogContext&) const;
    std::vector<PriceOption> priceOptions(const Id& rowId, const CatalogContext&) const;
    std::vector<CatalogUpgrade> automaticConversions(UnitTypeId type, const CatalogContext&) const;
    int productionCapacity(const Id& type, int damage, const CatalogContext&) const;
    int repairCapacity(const Id& type, int damage, const CatalogContext& = {}) const;
    std::vector<std::string> unresolvedFields() const;
    void requireComplete() const;

  private:
    std::string fingerprint_;
    json::Value sourceData_;
    std::vector<UnitDefinition> units_;  // By unit type number.
    NameTable<UnitTypeKind> unitTypes_;
    NameTable<UnitClassKind> unitClasses_;
    KnownUnitTypes knownUnitTypes_;
    KnownUnitClasses knownUnitClasses_;
    std::map<Id, FacilityDefinition> facilities_;
    std::map<Id, TechnologyDefinition> technologies_;
    std::map<Id, BuildChartRow> rows_;
};

CatalogContext catalogContext(const State& state, NationId nation, std::optional<ZoneId> zone = std::nullopt);
// Catalog stats under catalogContext(state, nation, zone), reading the state's
// flags in place instead of copying them into a context.
CatalogStats catalogStats(const State& state, UnitTypeId type, int damage, NationId nation,
                          std::optional<ZoneId> zone = std::nullopt);
void initializeCatalogState(State& state);
int completedAssetValue(const Definition& definition, const Id& type);

}  // namespace game::campaign
