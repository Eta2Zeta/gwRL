"""Map invariants and reviewed Canadian / China-theatre connections.

Run with: ./.venv/bin/python -m unittest discover -s tests -p 'test_manual_map.py'
"""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "game_content/maps/gw36_manual_map.json"

# Readable aliases for the independently reviewed China-theatre expectations.
THEATRE_IDS = {
    name: f"land_china_{name}"
    for name in (
        "sinkiang", "tsinghai", "suiyuan", "beiping", "hopeh", "sikang",
        "yunnan", "shensi", "szechwan", "shantung", "kweichow", "hunan", "nanking",
    )
}
THEATRE_IDS.update({
    name: f"land_mongolia_{name}"
    for name in ("kobdo", "ulyassutai", "central_mongolia", "kerulen", "tannu_tuva")
})
THEATRE_IDS.update({
    name: f"land_manchuria_{name}" for name in ("northern", "western", "eastern", "rehe")
})
THEATRE_IDS.update({
    name: f"land_{name}"
    for name in (
        "tibet", "kwangtung", "hainan", "formosa", "hong_kong", "korea",
        "annam_tonkin", "burma", "kashmir", "nepal",
    )
})
THEATRE_IDS.update({
    name: f"land_usr_{name}"
    for name in (
        "eastern_kazakhstan", "novosibirsk", "angara", "buryatia", "chita",
        "amur", "primorsky_krai", "turkestan",
    )
})
THEATRE_IDS.update({
    name: f"land_india_{name}" for name in ("bengal", "calcutta", "benares")
})
THEATRE_IDS.update({f"p{number}": f"sea_p{number}" for number in range(1, 60)})


def unique_object(pairs):
    """Reject duplicate JSON keys instead of silently accepting the last value."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


class ManualMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(MAP_PATH.read_text(), object_pairs_hook=unique_object)
        cls.nodes = cls.document["nodes"]
        cls.edges = {
            (source, edge["neighbor_id"]): edge
            for source, node in cls.nodes.items()
            for edge in node["neighbors"]
        }

    def edge(self, source, destination):
        self.assertIn((source, destination), self.edges)
        return self.edges[source, destination]

    def theatre_edge(self, source, destination):
        return self.edge(THEATRE_IDS[source], THEATRE_IDS[destination])

    def assert_theatre_fields(self, source, destination, **expected):
        with self.subTest(source=source, destination=destination):
            edge = self.theatre_edge(source, destination)
            for field, value in expected.items():
                self.assertEqual(edge[field], value, field)

    def assert_theatre_pair(self, source, destination, **expected):
        self.assert_theatre_fields(source, destination, **expected)
        self.assert_theatre_fields(destination, source, **expected)

    def test_generator_reproduces_checked_in_map(self):
        spec = importlib.util.spec_from_file_location(
            "manual_map_builder", ROOT / "tools/build_manual_map_json.py"
        )
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory(prefix="gwrl-map-test-") as directory:
            output = Path(directory) / "map.json"
            with patch.object(builder, "OUTPUT", output), contextlib.redirect_stdout(io.StringIO()):
                builder.build()
            generated = json.loads(output.read_text(), object_pairs_hook=unique_object)
        self.assertEqual(generated, self.document)

    def test_graph_ids_and_references(self):
        for source, node in self.nodes.items():
            with self.subTest(source=source):
                self.assertEqual(node["id"], source)
                neighbors = [edge["neighbor_id"] for edge in node["neighbors"]]
                self.assertEqual(len(neighbors), len(set(neighbors)))
                self.assertNotIn(source, neighbors)
                for destination in neighbors:
                    self.assertIn(destination, self.nodes)
                    self.assertIn((destination, source), self.edges)

    def test_home_country_data_matches_current_map(self):
        spec = importlib.util.spec_from_file_location(
            "home_country_builder", ROOT / "tools/build_nation_home_country_json.py"
        )
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        path = ROOT / "game_content/maps/gw36_nation_home_country.json"
        checked_in = json.loads(path.read_text(), object_pairs_hook=unique_object)
        with tempfile.TemporaryDirectory(prefix="gwrl-home-test-") as directory:
            output = Path(directory) / "home.json"
            with patch.object(builder, "OUTPUT_PATH", output), contextlib.redirect_stdout(io.StringIO()):
                builder.build()
            self.assertEqual(json.loads(output.read_text()), checked_in)
        for nation, entry in checked_in["nations"].items():
            with self.subTest(nation=nation):
                ids = entry["home_country_land_zone_ids"]
                self.assertEqual(len(ids), len(set(ids)))
                for node_id in ids:
                    self.assertIn(node_id, self.nodes)
                    self.assertEqual(self.nodes[node_id]["type"], "land")
                self.assertEqual(
                    entry["home_country_land_zone_names"],
                    [self.nodes[node_id]["name"] for node_id in ids],
                )
        self.assertIn("land_usr_turkestan", checked_in["nations"]["USSR"]["home_country_land_zone_ids"])
        self.assertNotIn("land_india_bengal", checked_in["nations"]["FEC"]["home_country_land_zone_ids"])

    def test_reciprocal_route_metadata(self):
        # Border terrain and river_crossing are intentionally directional.
        reciprocal_fields = (
            "has_river", "railway_connection", "gauge_change",
            "naval_facilities", "naval_facility_ids", "narrow_crossings",
        )
        for (source, destination), edge in self.edges.items():
            with self.subTest(source=source, destination=destination):
                reverse = self.edge(destination, source)
                for field in reciprocal_fields:
                    self.assertEqual(edge[field], reverse[field], field)

    def test_rail_and_facility_metadata_consistency(self):
        for node_id, node in self.nodes.items():
            with self.subTest(node=node_id):
                facilities = node["node_facilities"]
                ids = node["node_facility_ids"]
                self.assertEqual(len(facilities), len(ids))
                self.assertEqual(len(ids), len(set(ids)))
                self.assertTrue(all(isinstance(value, str) and value for value in ids))
        for (source, destination), edge in self.edges.items():
            with self.subTest(source=source, destination=destination):
                # Rule 10.6.2 damages all railroads on the same border together.
                # Reviewed existence is boolean; null preserves an unreviewed
                # new border. Gauge changes require two verified gauge values.
                self.assertIn(type(edge["railway_connection"]), (bool, type(None)))
                self.assertIn(type(edge["gauge_change"]), (bool, type(None)))
                self.assertNotIn("railroads", edge)
                self.assertNotIn("rail_id", edge)
                if edge["railway_connection"] is False:
                    self.assertIs(edge["gauge_change"], False)
                elif edge["railway_connection"] is None:
                    self.assertIsNone(edge["gauge_change"])
                elif source.startswith("land_") and destination.startswith("land_"):
                    gauges = (edge.get("source_rail_gauge"), edge.get("target_rail_gauge"))
                    if all(gauges):
                        self.assertEqual(edge["gauge_change"], gauges[0] != gauges[1])
                    else:
                        self.assertIsNone(edge["gauge_change"])
                facilities = edge["naval_facilities"]
                ids = edge["naval_facility_ids"]
                self.assertEqual(len(facilities), len(ids))
                self.assertEqual(len(ids), len(set(ids)))
                self.assertTrue(all(isinstance(value, str) and value for value in ids))
                for facility_type, facility_id in zip(facilities, ids):
                    facility = self.document["facilities"][facility_id]
                    self.assertEqual(facility["type"], facility_type)
                    land, sea = (source, destination) if source.startswith("land_") else (destination, source)
                    self.assertEqual(facility["land_id"], land)
                    self.assertIn(sea, facility["sea_accesses"])
                self.assertIsInstance(edge["narrow_crossings"], int)
                self.assertGreaterEqual(edge["narrow_crossings"], 0)
                self.assertEqual(edge["narrow_crossing"], edge["narrow_crossings"] > 0)

    def test_canadian_river_routes_and_directional_crossings(self):
        # A river route can exist without a crossing penalty, and vice versa.
        routes = (
            ("land_usa_alaska", "land_can_yukon_territory", True, False),
            ("land_can_yukon_territory", "land_can_british_columbia", False, False),
            ("land_can_ontario", "land_can_ottawa", False, False),
            ("land_can_ottawa", "land_can_quebec", False, False),
            ("land_can_ontario", "land_usa_great_lakes", True, True),
            ("land_can_ontario", "land_usa_the_northeast", True, True),
        )
        expected = set()
        for source, destination, forward_crossing, reverse_crossing in routes:
            expected.update(((source, destination), (destination, source)))
            with self.subTest(source=source, destination=destination):
                forward = self.edge(source, destination)
                reverse = self.edge(destination, source)
                self.assertTrue(forward["has_river"])
                self.assertTrue(reverse["has_river"])
                self.assertEqual(forward["river_crossing"], forward_crossing)
                self.assertEqual(reverse["river_crossing"], reverse_crossing)
        actual = {
            (source, destination)
            for (source, destination), edge in self.edges.items()
            if edge["has_river"]
            and (source.startswith("land_can_") or destination.startswith("land_can_"))
        }
        self.assertEqual(actual, expected)

    def test_quebec_south_bank_crossings_are_not_river_routes(self):
        for neighbor in ("land_can_nova_scotia", "land_usa_new_england"):
            with self.subTest(neighbor=neighbor):
                outbound = self.edge("land_can_quebec", neighbor)
                inbound = self.edge(neighbor, "land_can_quebec")
                self.assertFalse(outbound["has_river"])
                self.assertFalse(inbound["has_river"])
                self.assertFalse(outbound["river_crossing"])
                self.assertTrue(inbound["river_crossing"])

    def test_accepted_seams_restored_borders_and_excluded_corner_contacts(self):
        for source, destination in (
            ("land_can_district_of_mackenzie", "land_can_district_of_keewatin"),
            ("land_can_alberta_saskatchewan", "land_can_manitoba"),
        ):
            with self.subTest(accepted=(source, destination)):
                self.assertTrue(self.edge(source, destination)["passable"])
                self.assertTrue(self.edge(destination, source)["passable"])
        # AM-241 resolved these finite borders from the enlarged board and
        # explicit glossary approaches; they are no longer corner exclusions.
        for source, destination in (
            ("land_can_alberta_saskatchewan", "land_usa_pacific_northwest"),
            ("land_can_yukon_territory", "land_usa_southeast_alaska"),
            ("land_can_alberta_saskatchewan", "land_usa_upper_midwest"),
        ):
            with self.subTest(restored=(source, destination)):
                self.assertIs(self.edge(source, destination)["railway_connection"], False)
                self.assertIs(self.edge(destination, source)["railway_connection"], False)
        for source, destination in (
            ("land_can_british_columbia", "land_usa_alaska"),
            ("land_can_ottawa", "land_usa_new_england"),
            ("land_can_ottawa", "land_usa_the_northeast"),
            ("land_can_ottawa", "land_can_nova_scotia"),
        ):
            with self.subTest(excluded=(source, destination)):
                self.assertNotIn((source, destination), self.edges)
                self.assertNotIn((destination, source), self.edges)

    def test_printed_narrow_crossings_are_not_railways(self):
        pairs = (
            ("land_can_district_of_keewatin", "land_can_baffin_island"),
            ("land_can_labrador", "land_can_newfoundland"),
            ("land_can_newfoundland", "land_can_st_pierre_island"),
        )
        for source, destination in pairs:
            for direction in ((source, destination), (destination, source)):
                with self.subTest(direction=direction):
                    edge = self.edge(*direction)
                    self.assertTrue(edge["passable"])
                    self.assertTrue(edge["narrow_crossing"])
                    self.assertEqual(edge["narrow_crossings"], 1)
                    self.assertFalse(edge["railway_connection"])
        for pair in (
            ("land_can_baffin_island", "land_can_labrador"),
            ("land_can_nova_scotia", "land_can_st_pierre_island"),
        ):
            self.assertNotIn(pair, self.edges)
            self.assertNotIn(tuple(reversed(pair)), self.edges)

    def test_canadian_railways_use_one_boolean_per_border(self):
        for direction in (
            ("land_can_ontario", "land_can_ottawa"),
            ("land_can_ottawa", "land_can_ontario"),
        ):
            edge = self.edge(*direction)
            self.assertTrue(edge["railway_connection"])
            self.assertNotIn("railroads", edge)
            self.assertIsNone(edge["gauge_change"])
        rail_pairs = (
            ("land_can_british_columbia", "land_can_alberta_saskatchewan"),
            ("land_can_british_columbia", "land_usa_pacific_northwest"),
            ("land_can_manitoba", "land_can_ontario"),
            ("land_can_ottawa", "land_can_quebec"),
            ("land_can_quebec", "land_can_nova_scotia"),
            ("land_can_quebec", "land_usa_new_england"),
            ("land_can_ontario", "land_usa_midwest"),
            ("land_can_ontario", "land_usa_great_lakes"),
        )
        no_rail_pairs = (
            ("land_can_yukon_territory", "land_can_british_columbia"),
            ("land_can_manitoba", "land_can_district_of_keewatin"),
            ("land_can_manitoba", "land_usa_midwest"),
            ("land_can_ontario", "land_can_quebec"),
            ("land_can_quebec", "land_can_labrador"),
            ("land_can_nova_scotia", "land_usa_new_england"),
            ("land_can_ontario", "land_usa_the_northeast"),
        )
        # Alberta-Manitoba rail remains unverified: do not bless it as audited.
        for expected, pairs in ((True, rail_pairs), (False, no_rail_pairs)):
            for source, destination in pairs:
                for direction in ((source, destination), (destination, source)):
                    with self.subTest(direction=direction):
                        edge = self.edge(*direction)
                        self.assertEqual(edge["railway_connection"], expected)
                        if expected:
                            # The Canadian rail review confirmed the crossing;
                            # it did not independently record both gauges.
                            self.assertIsNone(edge["gauge_change"])
                        else:
                            self.assertIs(edge["gauge_change"], False)

    def test_china_territory_inventory_terrain_and_income(self):
        expected = {
            "sinkiang": ("mountain", 0), "tsinghai": ("mountain", 0),
            "suiyuan": ("mountain", 1), "beiping": ("normal", 2),
            "hopeh": ("normal", 1), "tibet": ("mountain", 0),
            "sikang": ("mountain", 0), "yunnan": ("mountain", 1),
            "kwangtung": ("mountain", 2), "hainan": (["mountain", "jungle"], 1),
            "shensi": ("mountain", 2), "szechwan": ("mountain", 0),
            "shantung": ("normal", 2), "kweichow": ("mountain", 0),
            "hunan": ("normal", 2), "nanking": ("normal", 2),
            "kobdo": ("mountain", 0), "ulyassutai": ("normal", 0),
            "central_mongolia": ("normal", 1), "kerulen": ("normal", 1),
            "northern": ("normal", 1), "western": ("normal", 1),
            "eastern": ("normal", 1), "rehe": ("normal", 1),
            "formosa": ("mountain", 2), "hong_kong": ("mountain", 2),
            "tannu_tuva": ("mountain", 0), "korea": ("mountain", 2),
            "bengal": ("jungle", 1), "turkestan": ("normal", 0),
        }
        for name, (terrain, income) in expected.items():
            with self.subTest(territory=name):
                node = self.nodes[THEATRE_IDS[name]]
                self.assertEqual(node["terrain"], terrain)
                self.assertEqual(node["ipp_value"], income)
                self.assertEqual(node["is_city"], name in {"beiping", "nanking", "hong_kong"})
                self.assertEqual(node["is_victory_city"], name == "nanking")
        self.assertEqual(
            sum(node["ipp_value"] for node in self.nodes.values() if node["original_owner"] == "KMT"),
            6,
        )
        for name, owner in (("bengal", "FEC"), ("turkestan", "Soviet Union")):
            node = self.nodes[THEATRE_IDS[name]]
            self.assertEqual(node["original_owner"], owner)
            self.assertEqual(node["current_owner"], owner)
        for name in ("hong_kong", "korea"):
            self.assertIn("airfield", self.nodes[THEATRE_IDS[name]]["node_facilities"])

    def test_china_corrected_land_adjacencies_and_himalayan_barriers(self):
        # Definite removals and independently reviewed non-neighbors only;
        # do not encode a verdict on the held Kobdo/Novosibirsk or Tibet corners.
        excluded = (
            ("sinkiang", "szechwan"), ("tibet", "benares"),
            ("tibet", "calcutta"), ("sikang", "calcutta"),
            ("western", "suiyuan"), ("rehe", "kerulen"),
            ("korea", "p7"), ("formosa", "p42"),
        )
        for source, destination in excluded:
            for a, b in ((source, destination), (destination, source)):
                with self.subTest(excluded=(a, b)):
                    self.assertNotIn((THEATRE_IDS[a], THEATRE_IDS[b]), self.edges)
        for source, destination in (
            ("sinkiang", "eastern_kazakhstan"), ("sinkiang", "turkestan"),
            ("tibet", "tsinghai"),
        ):
            # Sinkiang -> Eastern Kazakhstan's combat crossing remains unreviewed.
            self.assert_theatre_pair(
                source, destination, passable=True, railway_connection=False, has_river=False,
            )
        for source, destination in (
            ("tibet", "kashmir"), ("tibet", "nepal"), ("sikang", "bengal"),
            ("tibet", "bengal"), ("yunnan", "bengal"), ("yunnan", "burma"),
        ):
            self.assert_theatre_pair(source, destination, passable=False, railway_connection=False)
        self.assert_theatre_pair("tibet", "tsinghai", border_terrain="mountain")
        self.assert_theatre_pair(
            "hainan", "kwangtung", passable=True, border_terrain="mountain",
            narrow_crossing=True, narrow_crossings=1, railway_connection=False,
        )

    def test_china_northern_directional_border_terrain(self):
        mountain_pairs = (
            ("tannu_tuva", "novosibirsk"), ("tannu_tuva", "angara"),
            ("central_mongolia", "angara"), ("central_mongolia", "buryatia"),
            ("central_mongolia", "chita"), ("kobdo", "eastern_kazakhstan"),
            ("sinkiang", "eastern_kazakhstan"),
        )
        for source, destination in mountain_pairs:
            self.assert_theatre_pair(source, destination, border_terrain="mountain")
        mountain_directions = (
            ("central_mongolia", "kobdo"), ("central_mongolia", "tannu_tuva"),
            ("ulyassutai", "kobdo"), ("kobdo", "tannu_tuva"),
            ("kerulen", "chita"), ("sinkiang", "kobdo"),
            ("beiping", "suiyuan"), ("hopeh", "suiyuan"), ("rehe", "suiyuan"),
            ("suiyuan", "shensi"), ("turkestan", "sinkiang"),
            ("tsinghai", "sinkiang"),
        )
        for source, destination in mountain_directions:
            self.assert_theatre_fields(source, destination, border_terrain="mountain")
        mixed_directions = (
            ("ulyassutai", "tsinghai"), ("central_mongolia", "tsinghai"),
            ("kobdo", "sinkiang"), ("ulyassutai", "sinkiang"),
            ("sinkiang", "tsinghai"), ("tsinghai", "suiyuan"),
            ("suiyuan", "tsinghai"), ("central_mongolia", "suiyuan"),
            ("kerulen", "suiyuan"), ("sinkiang", "turkestan"),
        )
        for source, destination in mixed_directions:
            self.assert_theatre_fields(source, destination, border_terrain=["desert", "mountain"])
        for source, destination in (
            ("tsinghai", "ulyassutai"), ("tsinghai", "central_mongolia"),
            ("suiyuan", "central_mongolia"), ("suiyuan", "kerulen"),
        ):
            self.assert_theatre_fields(source, destination, border_terrain="desert")

    def test_china_inland_directional_border_terrain(self):
        mountain_entries = {
            "shensi": ("hopeh", "suiyuan", "tsinghai"),
            "szechwan": ("hopeh", "shantung", "hunan", "shensi", "tsinghai"),
            "kweichow": ("hunan", "kwangtung", "sikang", "yunnan", "szechwan"),
            "sikang": ("tibet", "yunnan", "szechwan"),
            "yunnan": ("annam_tonkin", "kwangtung", "burma"),
            "tsinghai": ("sikang", "szechwan"),
            "kwangtung": ("hunan", "kweichow", "hong_kong", "yunnan"),
            "hong_kong": ("kwangtung",),
        }
        for destination, sources in mountain_entries.items():
            for source in sources:
                self.assert_theatre_fields(source, destination, border_terrain="mountain")
        self.assert_theatre_fields(
            "annam_tonkin", "kwangtung", border_terrain=["jungle", "mountain"],
        )
        self.assert_theatre_fields("kwangtung", "annam_tonkin", border_terrain="jungle")

    def test_manchurian_directional_border_terrain(self):
        for source, destination in (
            ("northern", "amur"), ("northern", "chita"), ("western", "chita"),
            ("eastern", "primorsky_krai"), ("eastern", "korea"),
        ):
            self.assert_theatre_pair(source, destination, border_terrain="mountain")
        for source, destination in (
            ("eastern", "amur"), ("rehe", "korea"), ("primorsky_krai", "korea"),
        ):
            self.assert_theatre_fields(source, destination, border_terrain="mountain")
        self.assert_theatre_fields("western", "kerulen", border_terrain="normal")
        self.assert_theatre_fields("kerulen", "western", border_terrain="mountain")
        self.assert_theatre_pair("northern", "western", border_terrain="normal")

    def test_china_river_routes_are_distinct_from_combat_crossings(self):
        route_pairs = (
            ("tsinghai", "suiyuan"), ("yunnan", "annam_tonkin"), ("hunan", "nanking"),
            ("suiyuan", "hopeh"), ("tibet", "sikang"), ("sikang", "yunnan"),
            ("yunnan", "kweichow"), ("kweichow", "hunan"), ("hunan", "kwangtung"),
        )
        expected_routes = {
            (THEATRE_IDS[a], THEATRE_IDS[b])
            for source, destination in route_pairs
            for a, b in ((source, destination), (destination, source))
        }
        reviewed_ids = {
            node_id for node_id in self.nodes
            if node_id.startswith(("land_china_", "land_mongolia_", "land_manchuria_"))
        } | {THEATRE_IDS[name] for name in (
            "tibet", "kwangtung", "hainan", "formosa", "hong_kong", "korea",
        )}
        actual_routes = {
            (source, destination)
            for (source, destination), edge in self.edges.items()
            if edge["has_river"] and (source in reviewed_ids or destination in reviewed_ids)
        }
        self.assertEqual(actual_routes, expected_routes)
        for source, destination in route_pairs[:3]:
            self.assert_theatre_pair(source, destination, has_river=True, river_crossing=False)
        one_way_crossings = (
            ("shensi", "hopeh"), ("szechwan", "hopeh"), ("szechwan", "tsinghai"),
            ("szechwan", "sikang"), ("szechwan", "hunan"), ("kwangtung", "hunan"),
            ("kwangtung", "kweichow"), ("kweichow", "yunnan"), ("kweichow", "sikang"),
            ("tsinghai", "sikang"), ("shensi", "tsinghai"), ("shensi", "suiyuan"),
            ("shantung", "hopeh"), ("shantung", "hunan"), ("shantung", "nanking"),
            ("tannu_tuva", "angara"), ("central_mongolia", "angara"),
            ("kobdo", "eastern_kazakhstan"),
        )
        for source, destination in one_way_crossings:
            self.assert_theatre_fields(source, destination, river_crossing=True)
            self.assert_theatre_fields(destination, source, river_crossing=False)
        self.assert_theatre_pair("kweichow", "hunan", river_crossing=True)
        self.assert_theatre_pair("annam_tonkin", "kwangtung", has_river=False, river_crossing=False)

    def test_china_railways_and_international_gauge_changes(self):
        regular_rail_pairs = (
            ("hopeh", "beiping"), ("hopeh", "shensi"), ("hopeh", "shantung"),
            ("suiyuan", "beiping"), ("northern", "western"), ("western", "eastern"),
            ("western", "rehe"), ("eastern", "rehe"), ("eastern", "korea"),
            ("rehe", "korea"), ("rehe", "beiping"), ("hunan", "shantung"),
            ("hunan", "nanking"), ("hunan", "kwangtung"), ("yunnan", "annam_tonkin"),
            ("annam_tonkin", "kwangtung"), ("kwangtung", "p41"),
            ("hong_kong", "p41"), ("nanking", "p14"), ("nanking", "p32"),
            ("rehe", "p14"), ("korea", "p14"), ("beiping", "p14"),
        )
        for source, destination in regular_rail_pairs:
            self.assert_theatre_pair(source, destination, railway_connection=True)
        # Explicitly checked track colors, rather than owner differences,
        # establish these two gauge outcomes (rulebook 1.6 / WG-015).
        self.assert_theatre_pair("northern", "western", gauge_change=False)
        self.assert_theatre_pair("chita", "northern", railway_connection=True, gauge_change=True)
        # The old Soviet-only heuristic asserted a change here without a
        # separately recorded source/target gauge review.
        self.assert_theatre_pair("eastern", "primorsky_krai", railway_connection=True, gauge_change=None)
        for source, destination in (("hopeh", "beiping"), ("kwangtung", "p41")):
            self.assert_theatre_pair(source, destination, gauge_change=None)
        for source, destination in (
            ("northern", "amur"), ("tibet", "kashmir"), ("tibet", "nepal"),
            ("suiyuan", "tsinghai"), ("korea", "p15"),
        ):
            self.assert_theatre_pair(source, destination, railway_connection=False, gauge_change=False)
        for node_id, node in self.nodes.items():
            if node_id.startswith("land_mongolia_"):
                for edge in node["neighbors"]:
                    with self.subTest(mongolian_rail=(node_id, edge["neighbor_id"])):
                        self.assertFalse(edge["railway_connection"])

    def test_china_coasts_facilities_and_amphibious_terrain(self):
        expected_coasts = {
            "beiping": {"p14"}, "hopeh": {"p14"}, "shantung": {"p14"},
            "nanking": {"p14", "p32"}, "hunan": {"p32"}, "kwangtung": {"p41"},
            "hainan": {"p41"}, "hong_kong": {"p41"}, "rehe": {"p14"},
            "korea": {"p14", "p15"}, "formosa": {"p32", "p41"}, "eastern": set(),
        }
        for name, seas in expected_coasts.items():
            with self.subTest(coast=name):
                actual = {
                    edge["neighbor_id"] for edge in self.nodes[THEATRE_IDS[name]]["neighbors"]
                    if edge["neighbor_id"].startswith("sea_")
                }
                self.assertEqual(actual, {THEATRE_IDS[sea] for sea in seas})
                for sea in seas:
                    self.assert_theatre_fields(name, sea, border_terrain="coast")
        expected_facilities = (
            ("beiping", "p14", ["minor_port"]), ("hopeh", "p14", []),
            ("shantung", "p14", ["major_port", "minor_dockyard"]),
            ("nanking", "p14", ["major_port"]), ("nanking", "p32", ["major_port"]),
            ("hunan", "p32", []), ("kwangtung", "p41", ["major_port"]),
            ("hainan", "p41", []), ("hong_kong", "p41", ["major_dockyard"]),
            ("rehe", "p14", ["major_port"]), ("korea", "p14", ["minor_port"]),
            ("korea", "p15", []), ("formosa", "p32", ["major_port"]),
            ("formosa", "p41", []),
        )
        for source, destination, facilities in expected_facilities:
            self.assert_theatre_pair(source, destination, naval_facilities=facilities)
        for sea in ("p14", "p32"):
            self.assert_theatre_pair("nanking", sea, naval_facility_ids=["port_nanking_major"])
        for name, seas in expected_coasts.items():
            for sea in seas:
                terrain = "mountain" if name in {
                    "korea", "formosa", "kwangtung", "hainan", "hong_kong",
                } else "normal"
                self.assert_theatre_fields(sea, name, border_terrain=terrain)

    def test_china_adjacent_sea_graph_and_names(self):
        expected = {
            "p7": {"p2", "p8", "p15", "p16"},
            "p14": {"p15", "p32"},
            "p15": {"p7", "p14", "p16", "p32", "p33", "p34"},
            "p32": {"p14", "p15", "p33", "p41", "p42", "p43"},
            "p41": {"p32", "p42", "p50"},
        }
        for sea, neighbors in expected.items():
            with self.subTest(sea=sea):
                actual = {
                    edge["neighbor_id"] for edge in self.nodes[THEATRE_IDS[sea]]["neighbors"]
                    if edge["neighbor_id"].startswith("sea_")
                }
                self.assertEqual(actual, {THEATRE_IDS[neighbor] for neighbor in neighbors})
                for neighbor in neighbors:
                    self.assert_theatre_pair(sea, neighbor, border_terrain="sea")
        self.assertEqual(self.nodes[THEATRE_IDS["p15"]]["name"], "P15")
        self.assertEqual(self.nodes[THEATRE_IDS["p32"]]["name"], "P32")

    def test_printed_gauge_changes_are_independent_of_original_owner(self):
        for source, destination, change in (
            ("land_swe_norrland", "land_fin_lapland", True),
            ("land_fin_viipuri_province", "land_usr_leningrad", False),
        ):
            with self.subTest(pair=(source, destination)):
                self.assertIs(self.edge(source, destination)["railway_connection"], True)
                self.assertIs(self.edge(source, destination)["gauge_change"], change)
                self.assertIs(self.edge(destination, source)["gauge_change"], change)


if __name__ == "__main__":
    unittest.main()
