"""Independent source fixtures for the v4.3 catalog; no PDF runtime required.

Prices and chart coverage below were checked against complete rendered national
reference sheets. Page counts describe the locally hashed source editions.
"""

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "game_content/catalog/gw36_v43"
FILES = ("land_air.json", "naval.json", "facilities.json", "build_charts.json", "technologies.json")
SOURCE_PAGES = {
    "Global War 1936 v4.3 Rulebook.pdf": 108,
    "GW36 - NRS - Japan v4.3.pdf": 9,
    "GW36 - NRS - KMT v4.3.pdf": 7,
    "GW36 - NRS - CCP v4.3.pdf": 7,
}

# The three major-power charts have the same 57 printed type/price rows.
# Japan pp5-8; KMT pp4-7; CCP pp4-7. Railroad's printed alternative is not
# a second payment stage: the ordinary-route fixture is [2], with [4] derived.
MAJOR_PRICES = {
    "militia": [2], "infantry": [3], "airborne_infantry": [3],
    "elite_airborne_infantry": [3], "marine": [4], "mountain_infantry": [4],
    "cavalry": [3], "motorized_infantry": [4], "mechanized_infantry": [4],
    "advanced_mechanized_infantry": [4], "tank_destroyer": [4],
    "light_armor": [4], "medium_armor": [6], "heavy_armor": [7],
    "artillery": [4], "self_propelled_artillery": [5], "advanced_artillery": [4],
    "advanced_self_propelled_artillery": [5], "anti_aircraft_artillery": [4],
    "fighter": [10], "jet_fighter": [11], "tactical_bomber": [10],
    "medium_bomber": [10], "strategic_bomber": [10], "heavy_strategic_bomber": [11],
    "seaplane": [7], "air_transport": [8], "heavy_air_transport": [9],
    "strategic_rocket": [3], "destroyer": [7], "light_cruiser": [9],
    "heavy_cruiser": [5, 5], "battlecruiser": [7, 7], "battleship": [6, 6, 6],
    "heavy_battleship": [7, 7, 7], "light_carrier": [4, 4],
    "fleet_carrier": [5, 5, 5], "heavy_fleet_carrier": [6, 6, 6],
    "submarine": [6], "advanced_submarine": [7], "naval_transport": [7],
    "attack_naval_transport": [7], "minor_factory": [8], "medium_factory": [7, 7],
    "major_factory": [6, 6, 6], "airbase": [3, 3], "seaplane_base": [3],
    "submarine_base": [3], "minor_port": [3], "major_port": [3, 3],
    "minor_dockyard": [2, 2], "major_dockyard": [4, 4], "minor_shipyard": [3, 3],
    "major_shipyard": [5, 5], "fortification": [5, 5], "coastal_artillery": [6],
    "railroad": [2],
}
MINOR_PRICES = {"militia": [2], "infantry": [3], "cavalry": [3], "artillery": [4], "anti_aircraft_artillery": [4]}
TECH_UNLOCKS = {
    "elite_airborne_infantry": "airborne_doctrine",
    "advanced_mechanized_infantry": "advanced_mechanized_infantry",
    "advanced_artillery": "advanced_artillery",
    "advanced_self_propelled_artillery": "advanced_artillery",
    "heavy_armor": "heavy_armor", "jet_fighter": "jet_fighters",
    "heavy_strategic_bomber": "heavy_strategic_bombers",
    "heavy_air_transport": "airborne_doctrine", "strategic_rocket": "strategic_rockets",
    "heavy_battleship": "large_ship_construction", "heavy_fleet_carrier": "large_ship_construction",
    "advanced_submarine": "advanced_submarines", "attack_naval_transport": "amphibious_doctrine",
}
CAPPED_TYPES = {"airborne_infantry", "elite_airborne_infantry", "marine", "mountain_infantry",
                "tank_destroyer", "jet_fighter", "strategic_bomber", "heavy_strategic_bomber", "strategic_rocket"}
FACILITY_UPGRADES = {
    ("minor_factory", "medium_factory"): 7, ("medium_factory", "major_factory"): 6,
    ("minor_port", "major_port"): 4, ("minor_dockyard", "major_dockyard"): 5,
    ("minor_shipyard", "major_shipyard"): 5,
}


def objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate catalog key: {key}")
        result[key] = value
    return result


class CatalogSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents = {name: json.loads((CATALOG / name).read_text(), object_pairs_hook=unique_object) for name in FILES}
        cls.chart = cls.documents["build_charts.json"]
        cls.rows = {row["id"]: row for row in cls.chart["rows"]}
        cls.units = {unit["id"]: unit for name in ("land_air.json", "naval.json")
                     for unit in cls.documents[name]["units"]}
        cls.facilities = {item["id"]: item for item in cls.documents["facilities.json"]["facilities"]}
        cls.technologies = {item["id"]: item for item in cls.documents["technologies.json"]["technologies"]}

    def test_source_bytes_hashes_and_reference_page_bounds(self):
        for name, document in self.documents.items():
            with self.subTest(file=name):
                self.assertEqual(document["schema_version"], 1)
                sources = {source["id"]: source for source in document["sources"]}
                self.assertEqual(len(sources), len(document["sources"]))
                for source in sources.values():
                    if source.get("kind") == "user_ruling":
                        self.assertTrue(source["text"])
                        self.assertTrue(source["date"])
                        self.assertNotIn("path", source)
                        self.assertNotIn("sha256", source)
                        continue
                    path = ROOT / source["path"]
                    self.assertIn(path.name, SOURCE_PAGES)
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), source["sha256"])
                    self.assertEqual(source["version"], "4.3")
                for value in objects(document):
                    if "source_refs" in value:
                        self.assertTrue(value["source_refs"])
                    for reference in value.get("source_refs", []):
                        self.assertIn(reference["source_id"], sources)
                        if sources[reference["source_id"]].get("kind") == "user_ruling":
                            self.assertNotIn("pdf_page", reference)
                            continue
                        maximum = SOURCE_PAGES[Path(sources[reference["source_id"]]["path"]).name]
                        self.assertIs(type(reference["pdf_page"]), int)
                        self.assertGreaterEqual(reference["pdf_page"], 1)
                        self.assertLessEqual(reference["pdf_page"], maximum)
                        self.assertTrue(reference["section"])

    def test_every_printed_purchase_row_exactly_once(self):
        expected = {(nation, "major", kind) for nation in ("japan", "kmt", "ccp") for kind in MAJOR_PRICES}
        expected |= {(nation, "minor", kind) for nation in ("kmt", "ccp") for kind in MINOR_PRICES}
        printed = [row for row in self.chart["rows"] if not row.get("derived_from")]
        self.assertEqual(len(self.rows), len(self.chart["rows"]))
        self.assertEqual(len(printed), 181)
        self.assertEqual({(row["nation"], row["power_status"], row["type"]) for row in printed}, expected)
        self.assertEqual(set(self.chart["coverage"]["printed_purchase_row_ids"]), {row["id"] for row in printed})
        self.assertEqual(self.chart["coverage"]["printed_purchase_row_count"], 181)
        for row in printed:
            self.assertEqual(row["kind"], "purchase")
            fixture = MAJOR_PRICES if row["power_status"] == "major" else MINOR_PRICES
            self.assertEqual(row["purchase_costs"], fixture[row["type"]], row["id"])
            self.assertIsNone(row["upgrades_from"])
            source = row["source_refs"][0]
            self.assertEqual(source["source_id"], row["nation"] + "_nrs")
        for row in self.chart["rows"]:
            if row.get("derived_from"):
                self.assertIn(row["derived_from"], self.rows)
                self.assertFalse(self.rows[row["derived_from"]].get("derived_from"))

    def test_major_dates_technology_and_shared_caps(self):
        dated = {"mechanized_infantry", "tank_destroyer", "medium_armor", "strategic_bomber"}
        for nation in ("japan", "kmt", "ccp"):
            for kind in MAJOR_PRICES:
                row = self.rows[f"{nation}_major_{kind}"]
                self.assertEqual(row["available_from"], "1940-01" if kind in dated else None)
                self.assertEqual(row["available_through"], "1939-07" if kind == "cavalry" else None)
                self.assertEqual(row["requires_technology"], [TECH_UNLOCKS[kind]] if kind in TECH_UNLOCKS else [])
                self.assertEqual(row["forbids_technology"], ["airborne_doctrine"] if kind == "airborne_infantry" else [])
                self.assertEqual(row["cap_per_turn"], 2 if kind in CAPPED_TYPES else None)
            self.assertEqual(self.rows[f"{nation}_major_airborne_infantry"]["cap_group"],
                             self.rows[f"{nation}_major_elite_airborne_infantry"]["cap_group"])
        for nation in ("kmt", "ccp"):
            self.assertIsNone(self.rows[f"{nation}_minor_cavalry"]["available_through"])

    def test_cross_references_and_every_surviving_damage_level(self):
        all_types = set(self.units) | set(self.facilities)
        self.assertFalse(set(self.units) & set(self.facilities))
        self.assertEqual(len(self.units), sum(len(self.documents[name]["units"]) for name in ("land_air.json", "naval.json")))
        self.assertEqual(len(self.facilities), 15)
        for unit in self.units.values():
            self.assertFalse(unit.get("unresolved_fields"), unit["id"])
            self.assertEqual([state["damage"] for state in unit["states"]], list(range(unit["max_hits"])), unit["id"])
            for state in unit["states"]:
                for key in ("attack", "defense", "bombardment"):
                    self.assertTrue(state[key] is None or type(state[key]) is int, (unit["id"], key))
                for key in ("attack_dice", "defense_dice", "movement", "bombardment_dice", "cargo_capacity", "carrier_capacity"):
                    self.assertIs(type(state[key]), int)
                    self.assertGreaterEqual(state[key], 0)
            for upgrade in unit["upgrades"]:
                self.assertIn(upgrade["to"], self.units)
        for row in self.rows.values():
            self.assertIn(row["type"], all_types)
            if row["upgrades_from"]:
                self.assertIn(row["upgrades_from"], all_types)
            self.assertLessEqual(set(row["requires_technology"] + row["forbids_technology"]), set(self.technologies))
            self.assertLessEqual(set(row["requires_flags"] + row["placement"]), set(self.chart["predicate_definitions"]))
        for document in self.documents.values():
            for value in objects(document):
                self.assertLessEqual(set(value.get("requires_technology", [])), set(self.technologies))
        for technology in self.technologies.values():
            self.assertLessEqual(set(technology["unlocks"]), all_types)
            for conversion in technology["conversions"]:
                self.assertIn(conversion["from"], all_types)
                self.assertIn(conversion["to"], all_types)

    def test_facility_prices_capacities_and_upgrade_costs(self):
        capacities = {"minor_factory": 1, "medium_factory": 3, "major_factory": 5,
                      "minor_shipyard": 1, "major_shipyard": 5}
        repairs = {"minor_dockyard": 1, "major_dockyard": 5, "minor_shipyard": 1, "major_shipyard": 5}
        actual_upgrades = {}
        for kind, facility in self.facilities.items():
            self.assertEqual(facility["purchase_costs"], MAJOR_PRICES[kind])
            self.assertEqual(facility["asset_value"], sum(MAJOR_PRICES[kind]))
            self.assertEqual(facility["production_capacity"], capacities.get(kind, 0))
            self.assertEqual(facility["repair_capacity"], repairs.get(kind, 0))
            for upgrade in facility["upgrades"]:
                actual_upgrades[kind, upgrade["to"]] = upgrade["cost_ipp"]
        self.assertEqual(actual_upgrades, FACILITY_UPGRADES)
        major_rules = {rule["id"]: rule for rule in self.facilities["major_factory"]["rules"]}
        damage = major_rules["major_factory_damage_capacity"]["parameters"]
        self.assertEqual(damage["production_capacity_loss_per_damage"], 1)
        self.assertEqual(damage["minimum_production_capacity"], 0)
        improved = next(rule for rule in self.technologies["improved_factories"]["rules"]
                        if rule["id"] == "improved_factories_capacity")["parameters"]
        self.assertEqual(improved["repair_capacity_by_type"],
                         {"minor_dockyard": 2, "major_dockyard": 8, "minor_shipyard": 2, "major_shipyard": 8})
        for nation in ("japan", "kmt", "ccp"):
            for (old, new), cost in FACILITY_UPGRADES.items():
                row = self.rows[f"{nation}_major_{old}_to_{new}"]
                self.assertEqual(row["purchase_costs"], [cost])
                self.assertIn("upgrade_in_supply_path", row["placement"])
                self.assertNotIn("facility_undamaged", row["placement"])

    def test_exact_minor_artillery_prerequisites_and_placement(self):
        for kind in ("artillery", "anti_aircraft_artillery"):
            ccp = self.rows[f"ccp_minor_{kind}"]
            self.assertEqual(ccp["requires_flags"], ["ccp_soviet_rail_production"])
            self.assertIn("ccp_soviet_rail_connected_land", ccp["placement"])
            self.assertIn("RCL-004", ccp["notes"])
            kmt = self.rows[f"kmt_minor_{kind}"]
            self.assertEqual(kmt["requires_flags"], ["kmt_burma_road"])
            self.assertEqual(kmt["available_from"], "1938-07")
            self.assertIn("kmt_burma_road_yunnan", kmt["placement"])
        gate = self.chart["predicate_definitions"]["ccp_soviet_rail_production"]["parameters"]
        self.assertEqual((gate["origin_possessor"], gate["destination_possessor"]), ("ccp", "ussr"))
        self.assertTrue(gate["railroad_undamaged"])
        self.assertEqual(gate["phase"], "production")
        self.assertNotIn("campaign_enabled", gate)
        self.assertNotIn("campaign_enabled", self.chart["predicate_definitions"]["kmt_burma_road"]["parameters"])

    def test_railroads_are_route_priced_and_not_two_stages(self):
        for nation in ("japan", "kmt", "ccp"):
            ordinary = self.rows[f"{nation}_major_railroad"]
            difficult = self.rows[f"{nation}_major_railroad_route_cost_4"]
            self.assertEqual(ordinary["purchase_costs"], [2])
            self.assertEqual(difficult["purchase_costs"], [4])
            self.assertEqual(difficult["derived_from"], ordinary["id"])
            self.assertIn("railroad_route_cost_2", ordinary["placement"])
            self.assertIn("railroad_route_cost_4", difficult["placement"])
        route = self.chart["predicate_definitions"]["railroad_route_cost_4"]["parameters"]
        self.assertEqual(set(route["route_terrain_any"]), {"desert", "jungle", "marsh", "mountain", "tundra"})
        self.assertEqual(route["route_definition"], "most_direct_roundel_to_roundel_line_at_border_crossing")

    def test_no_source_only_unit_gains_national_purchase_access(self):
        excluded = {"torpedo_boat_destroyer", "coastal_submarine", "coastal_defense_ship", "t_34", "tiger_i",
                    "katyusha_rocket_artillery", "panzergrenadier", "b_29", "colonial_infantry", "foreign_legion", "gurkha"}
        self.assertFalse(excluded & {row["type"] for row in self.rows.values()})
        self.assertIsNone(self.units["torpedo_boat_destroyer"]["asset_value"])
        self.assertIsNone(self.units["coastal_submarine"]["asset_value"])
        self.assertNotIn("airfield", self.facilities)

    def test_port_aaa_is_one_per_attacker_with_separate_surprise_exception(self):
        for facility in self.facilities.values():
            rules = {rule["id"]: rule for rule in facility["rules"]}
            if "inherent_facility_aaa" not in rules:
                continue
            ordinary = rules["inherent_facility_aaa"]["parameters"]
            self.assertEqual(ordinary["port_attack_shots_per_attacking_aircraft"], 1)
            self.assertTrue(ordinary["port_attack_requires_this_facility_to_berth_targeted_ships"])
            self.assertIsNone(ordinary["maximum_shots"])
            surprise = rules["japanese_surprise_attack_port_aaa_suppression"]["parameters"]
            self.assertEqual(surprise["attacking_nation"], "japan")
            self.assertTrue(surprise["requires_surprise_attack_active"])
            self.assertEqual(surprise["port_attack_shots_per_attacking_aircraft"], 0)


if __name__ == "__main__":
    unittest.main()
