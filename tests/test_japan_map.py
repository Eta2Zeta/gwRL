"""Regression expectations independently read from the printed Japan map.

Run with: ./.venv/bin/python -m unittest discover -s tests -p 'test_japan_map.py'

These checks cover the four Japanese home-country tiles plus Okinawa. Real
connections to excluded scenario tiles remain present in the master map.
"""

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "game_content/maps/gw36_manual_map.json"
JAPAN_IDS = {
    name: f"land_jap_{name}"
    for name in ("tokyo", "honshu", "hokkaido", "kyushu", "okinawa")
}


class JapanMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nodes = json.loads(MAP_PATH.read_text())["nodes"]
        cls.edges = {
            (source, edge["neighbor_id"]): edge
            for source, node in cls.nodes.items()
            for edge in node["neighbors"]
        }
        spec = importlib.util.spec_from_file_location(
            "japan_map_builder", ROOT / "tools/build_manual_map_json.py"
        )
        cls.builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.builder)

    def edge(self, source, destination):
        self.assertIn((source, destination), self.edges)
        return self.edges[source, destination]

    def test_terrain_income_ownership_and_city_flags(self):
        income = {"tokyo": 2, "honshu": 2, "hokkaido": 1, "kyushu": 2, "okinawa": 0}
        for name, node_id in JAPAN_IDS.items():
            with self.subTest(territory=name):
                node = self.nodes[node_id]
                self.assertEqual(node["type"], "land")
                self.assertEqual(node["terrain"], "mountain")
                self.assertEqual(node["ipp_value"], income[name])
                self.assertEqual(node["original_owner"], "Japan")
                self.assertEqual(node["current_owner"], "Japan")
                # Nagasaki is a city within Kyushu, not a city land zone.
                for field in ("is_city", "is_capital", "is_victory_city"):
                    self.assertEqual(node[field], name == "tokyo", field)

    def test_intrinsic_airfields(self):
        for name, node_id in JAPAN_IDS.items():
            with self.subTest(territory=name):
                node = self.nodes[node_id]
                expected = ["airfield"] if name in {"tokyo", "honshu"} else []
                self.assertEqual(node["node_facilities"], expected)
                self.assertEqual(
                    node["node_facility_ids"],
                    [f"facility_{name}_airfield"] if expected else [],
                )

    def test_complete_neighbors_including_real_external_connections(self):
        expected = {
            "tokyo": {"land_jap_honshu", "sea_p16"},
            "honshu": {
                "land_jap_tokyo", "land_jap_hokkaido", "land_jap_kyushu",
                "sea_p15", "sea_p16",
            },
            "hokkaido": {
                "land_jap_honshu", "land_usr_south_sakhalin", "land_jap_kurile_islands",
                "sea_p7", "sea_p15", "sea_p16",
            },
            "kyushu": {"land_jap_honshu", "sea_p15"},
            "okinawa": {"sea_p33"},
        }
        for name, neighbors in expected.items():
            with self.subTest(territory=name):
                node_id = JAPAN_IDS[name]
                actual = {edge["neighbor_id"] for edge in self.nodes[node_id]["neighbors"]}
                self.assertEqual(actual, neighbors)
                for neighbor in neighbors:
                    self.assertIn((neighbor, node_id), self.edges)

    def test_coast_facilities_and_rail_connections(self):
        expected = {
            ("tokyo", "sea_p16"): (["major_shipyard"], True),
            ("honshu", "sea_p15"): (["major_shipyard", "major_shipyard"], True),
            ("honshu", "sea_p16"): (["major_port"], True),
            ("hokkaido", "sea_p7"): (["major_port"], True),
            ("hokkaido", "sea_p15"): ([], False),
            ("hokkaido", "sea_p16"): ([], False),
            ("kyushu", "sea_p15"): (["major_port", "major_shipyard"], True),
            ("okinawa", "sea_p33"): (["minor_port", "seaplane_base"], False),
        }
        for (name, sea), (facilities, rail) in expected.items():
            land = JAPAN_IDS[name]
            for source, destination in ((land, sea), (sea, land)):
                with self.subTest(source=source, destination=destination):
                    edge = self.edge(source, destination)
                    self.assertEqual(edge["naval_facilities"], facilities)
                    # AM-229 leaves legacy shore railway booleans in place;
                    # these are not permission to rail-move into a sea zone.
                    self.assertEqual(edge["railway_connection"], rail)
                    if rail:
                        self.assertIsNone(edge["gauge_change"])
                    else:
                        self.assertIs(edge["gauge_change"], False)
                    self.assertEqual(edge["port_or_dock_connection"], bool(facilities))
                    self.assertTrue(edge["passable"])
                    self.assertEqual(
                        edge["border_terrain"], "coast" if source == land else "mountain"
                    )
                    # The land pair owns crossing capacity, not a coastal edge.
                    self.assertFalse(edge["narrow_crossing"])
                    self.assertEqual(edge["narrow_crossings"], 0)
                    self.assertFalse(edge.get("narrow_crossing_sea_zones", []))
                    self.assertEqual(
                        edge["naval_facility_ids"],
                        self.edge(destination, source)["naval_facility_ids"],
                    )

    def test_honshu_two_physical_shipyards_are_not_deduplicated(self):
        for pair in (("land_jap_honshu", "sea_p15"), ("sea_p15", "land_jap_honshu")):
            with self.subTest(direction=pair):
                edge = self.edge(*pair)
                self.assertEqual(edge["naval_facilities"], ["major_shipyard", "major_shipyard"])
                self.assertEqual(
                    set(edge["naval_facility_ids"]),
                    {
                        "facility_honshu_northwest_major_shipyard",
                        "facility_honshu_south_major_shipyard",
                    },
                )
                self.assertEqual(len(edge["naval_facility_ids"]), 2)

    def test_ordinary_land_railways_and_directional_terrain(self):
        for first, second in (("tokyo", "honshu"), ("honshu", "kyushu")):
            land_a, land_b = JAPAN_IDS[first], JAPAN_IDS[second]
            for pair in ((land_a, land_b), (land_b, land_a)):
                with self.subTest(direction=pair):
                    edge = self.edge(*pair)
                    self.assertTrue(edge["passable"])
                    self.assertTrue(edge["railway_connection"])
                    # Existing Japanese crossing reviews did not separately
                    # author both printed gauges. Same owner proves neither.
                    self.assertIsNone(edge["gauge_change"])
                    self.assertEqual(edge["border_terrain"], "mountain")
                    self.assertFalse(edge["narrow_crossing"])
                    self.assertEqual(edge["narrow_crossings"], 0)

    def test_narrow_land_crossings_capacity_and_blocking_seas(self):
        # Rulebook 1.9: the printed number is capacity; no strategic rail crossing.
        expected = (
            ("land_jap_hokkaido", "land_jap_honshu", 2, {"sea_p16"}),
            (
                "land_jap_hokkaido", "land_usr_south_sakhalin", 1,
                {"sea_p7", "sea_p8", "sea_p16"},
            ),
            ("land_jap_hokkaido", "land_jap_kurile_islands", 1, {"sea_p9", "sea_p16"}),
        )
        for land_a, land_b, capacity, seas in expected:
            for pair in ((land_a, land_b), (land_b, land_a)):
                with self.subTest(direction=pair):
                    edge = self.edge(*pair)
                    self.assertTrue(edge["passable"])
                    self.assertTrue(edge["narrow_crossing"])
                    self.assertEqual(edge["narrow_crossings"], capacity)
                    self.assertFalse(edge["railway_connection"])
                    self.assertFalse(edge["gauge_change"])
                    self.assertEqual(edge["border_terrain"], "mountain")
                    self.assertEqual(set(edge["narrow_crossing_sea_zones"]), seas)
                    self.assertEqual(len(edge["narrow_crossing_sea_zones"]), len(seas))
                    self.assertEqual(
                        edge["narrow_crossing_sea_zones"],
                        self.edge(*reversed(pair))["narrow_crossing_sea_zones"],
                    )
                    for sea in seas:
                        self.assertEqual(self.nodes[sea]["type"], "sea")

    def test_no_invented_river_routes_or_combat_crossings(self):
        for (source, destination), edge in self.edges.items():
            if source in JAPAN_IDS.values() or destination in JAPAN_IDS.values():
                with self.subTest(source=source, destination=destination):
                    self.assertFalse(edge["has_river"])
                    self.assertFalse(edge["river_crossing"])

    def test_facility_normalization_preserves_and_sorts_type_id_pairs(self):
        types, ids = self.builder.normalize_naval_facility_instances(
            ["major_shipyard", "major_port", "major_shipyard"],
            ["shipyard_northwest", "port_northeast", "shipyard_south"],
            "land_jap_honshu",
        )
        self.assertEqual(types, ["major_port", "major_shipyard", "major_shipyard"])
        self.assertEqual(ids, ["port_northeast", "shipyard_northwest", "shipyard_south"])

    def test_facility_normalization_requires_unambiguous_distinct_instance_ids(self):
        with self.assertRaises(ValueError):
            self.builder.normalize_naval_facility_instances(
                ["major_shipyard", "major_shipyard"], [], "land_jap_honshu"
            )
        with self.assertRaises(ValueError):
            self.builder.normalize_naval_facility_instances(
                ["major_shipyard", "major_shipyard"],
                ["same_shipyard", "same_shipyard"],
                "land_jap_honshu",
            )


if __name__ == "__main__":
    unittest.main()
