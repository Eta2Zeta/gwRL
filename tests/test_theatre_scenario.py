"""Real-map regression checks for the closed Japan-China theatre projection."""

import copy
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "game_content/maps/gw36_manual_map.json"
SCENARIO_PATH = ROOT / "game_content/scenarios/japan_china_1936"
MANIFEST_PATH = SCENARIO_PATH / "manifest.json"
EXTRACTED_MAP_PATH = SCENARIO_PATH / "map.json"
SPEC = importlib.util.spec_from_file_location(
    "theatre_integration_builder", ROOT / "tools/build_theatre_scenario.py"
)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


EXPECTED_LAND_IDS = {
    f"land_china_{name}"
    for name in (
        "sinkiang", "tsinghai", "suiyuan", "beiping", "hopeh", "sikang",
        "yunnan", "shensi", "szechwan", "shantung", "kweichow", "hunan", "nanking",
    )
} | {
    f"land_mongolia_{name}"
    for name in ("kobdo", "ulyassutai", "central_mongolia", "kerulen")
} | {
    f"land_manchuria_{name}" for name in ("northern", "western", "eastern", "rehe")
} | {
    f"land_{name}" for name in ("tibet", "kwangtung", "hainan", "formosa", "hong_kong", "korea")
} | {
    f"land_jap_{name}" for name in ("hokkaido", "honshu", "tokyo", "kyushu", "okinawa")
}
EXPECTED_SEA_IDS = {f"sea_p{number}" for number in (14, 15, 16, 32, 33, 41)}
EXPECTED_IDS = EXPECTED_LAND_IDS | EXPECTED_SEA_IDS

# These sets were traced against the original map, independently of the
# generator. External endpoints must remain in the world graph and be removed
# only from the scenario projection.
MASTER_SEA_NEIGHBORS = {
    14: {15, 32},
    15: {7, 14, 16, 32, 33, 34},
    16: {7, 8, 9, 15, 17, 18, 26, 34, 35},
    32: {14, 15, 33, 41, 42, 43},
    33: {15, 32, 34, 43},
    41: {32, 42, 50},
}
MASTER_LAND_NEIGHBORS = {
    14: {
        "land_china_beiping", "land_china_hopeh", "land_china_shantung",
        "land_china_nanking", "land_manchuria_rehe", "land_korea",
    },
    15: {"land_korea", "land_jap_hokkaido", "land_jap_honshu", "land_jap_kyushu"},
    16: {"land_jap_hokkaido", "land_jap_honshu", "land_jap_tokyo"},
    32: {"land_china_nanking", "land_china_hunan", "land_formosa"},
    33: {"land_jap_okinawa"},
    41: {
        "land_annam_tonkin", "land_kwangtung", "land_hong_kong", "land_hainan",
        "land_formosa", "land_luzon_and_the_visayas",
    },
}


def indexed_edges(nodes):
    return {
        (source_id, edge["neighbor_id"]): edge
        for source_id, node in nodes.items()
        for edge in node["neighbors"]
    }


class TheatreScenarioIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source, cls.source_hash = builder.load_document(MAP_PATH)
        cls.manifest, cls.manifest_hash = builder.load_document(MANIFEST_PATH)
        cls.scenario, _ = builder.load_document(EXTRACTED_MAP_PATH)
        cls.source_edges = indexed_edges(cls.source["nodes"])
        cls.scenario_edges = indexed_edges(cls.scenario["nodes"])

    def test_manifest_is_exactly_the_requested_closed_38_tile_theatre(self):
        requested = self.manifest["included_node_ids"]
        self.assertEqual(len(EXPECTED_LAND_IDS), 32)
        self.assertEqual(len(EXPECTED_IDS), 38)
        self.assertEqual(len(requested), 38)
        self.assertEqual(set(requested), EXPECTED_IDS)
        self.assertEqual(set(self.scenario["nodes"]), EXPECTED_IDS)
        self.assertEqual(self.manifest["boundary_policy"], "closed")
        self.assertEqual(self.scenario["_meta"]["boundary_policy"], "closed")
        self.assertEqual(self.scenario["_meta"]["extracted_node_count"], 38)
        self.assertEqual(
            {node_id for node_id, node in self.scenario["nodes"].items() if node["type"] == "sea"},
            EXPECTED_SEA_IDS,
        )

    def test_confirmed_setup_and_wealth_specification_is_preserved(self):
        self.assertEqual(
            self.manifest["campaign"]["starting_piece_scope"],
            "official_setup_on_included_tiles_only",
        )
        objective = self.manifest["wealth_objective"]
        self.assertEqual(objective["status"], "planned_not_implemented")
        self.assertEqual(objective["income_definition"], "current_income_per_turn_rate_not_cumulative_collections")
        self.assertEqual(objective["completed_asset_valuation"], "purchase_price_minus_remaining_repair_price")
        self.assertTrue(objective["include_setup_asset_value"])
        self.assertEqual(objective["component_weights"], {
            "income_rate": 1,
            "unit_value": 0.1,
            "infrastructure_value": 0.1,
            "treasury": 0.1,
            "paid_construction_value": 0.1,
        })
        self.assertTrue(objective["interpretations"])
        self.assertEqual(self.scenario["_meta"]["scenario_manifest"]["wealth_objective"], objective)

    def test_tannu_tuva_is_excluded_without_deleting_it_from_the_world_map(self):
        excluded_id = "land_mongolia_tannu_tuva"
        self.assertIn(excluded_id, self.source["nodes"])
        self.assertNotIn(excluded_id, self.manifest["included_node_ids"])
        self.assertNotIn(excluded_id, self.scenario["nodes"])
        for source_id, neighbor_id in self.scenario_edges:
            self.assertNotEqual(source_id, excluded_id)
            self.assertNotEqual(neighbor_id, excluded_id)
        cuts = self.scenario["_meta"]["boundary_cuts"]
        actual = {cut["source_id"] for cut in cuts if cut["excluded_neighbor_id"] == excluded_id}
        expected = {"land_mongolia_central_mongolia", "land_mongolia_kobdo"}
        self.assertEqual(actual, expected)
        for source_id in expected:
            self.assertIn((source_id, excluded_id), self.source_edges)
            self.assertIn((excluded_id, source_id), self.source_edges)

    def test_regeneration_matches_checked_in_map_without_changing_inputs(self):
        paths = (MAP_PATH, MANIFEST_PATH, EXTRACTED_MAP_PATH)
        before = {path: path.read_bytes() for path in paths}
        with tempfile.TemporaryDirectory(prefix="gwrl-theatre-integration-") as directory:
            output = Path(directory) / "map.json"
            document = builder.build(MAP_PATH, MANIFEST_PATH, output)
            self.assertEqual(document, self.scenario)
            self.assertEqual(output.read_bytes(), before[EXTRACTED_MAP_PATH])
        self.assertEqual({path: path.read_bytes() for path in paths}, before)

    def test_provenance_hashes_and_metadata_match_current_inputs(self):
        meta = self.scenario["_meta"]
        self.assertEqual(meta["source_map_sha256"], hashlib.sha256(MAP_PATH.read_bytes()).hexdigest())
        self.assertEqual(meta["manifest_sha256"], hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest())
        self.assertEqual(meta["source_map_sha256"], self.source_hash)
        self.assertEqual(meta["manifest_sha256"], self.manifest_hash)
        self.assertEqual(meta["source_map"], MAP_PATH.relative_to(ROOT).as_posix())
        self.assertEqual(meta["manifest"], MANIFEST_PATH.relative_to(ROOT).as_posix())
        self.assertEqual(meta["source_map_meta"], self.source["_meta"])
        self.assertEqual(meta["scenario_manifest"], self.manifest)
        self.assertEqual(meta["artifact_type"], "closed_theatre_map")

    def test_all_retained_node_and_edge_fields_are_copied_exactly(self):
        for node_id, node in self.scenario["nodes"].items():
            with self.subTest(node_id=node_id):
                expected = copy.deepcopy(self.source["nodes"][node_id])
                expected["neighbors"] = [
                    edge for edge in expected["neighbors"] if edge["neighbor_id"] in EXPECTED_IDS
                ]
                self.assertEqual(node, expected)
                for edge in node["neighbors"]:
                    self.assertIn(edge["neighbor_id"], EXPECTED_IDS)
                    pair = (node_id, edge["neighbor_id"])
                    self.assertEqual(edge, self.source_edges[pair])
                    self.assertIn((pair[1], pair[0]), self.scenario_edges)

    def test_every_removed_neighbor_is_recorded_only_in_the_cut_audit(self):
        cuts = sorted(
            (
                {"source_id": node_id, "excluded_neighbor_id": edge["neighbor_id"]}
                for node_id in EXPECTED_IDS
                for edge in self.source["nodes"][node_id]["neighbors"]
                if edge["neighbor_id"] not in EXPECTED_IDS
            ),
            key=lambda cut: (cut["source_id"], cut["excluded_neighbor_id"]),
        )
        self.assertEqual(self.scenario["_meta"]["boundary_cuts"], cuts)
        self.assertEqual(self.scenario["_meta"]["excluded_neighbor_count"], len(cuts))
        self.assertGreater(len(cuts), 0)
        for cut in cuts:
            with self.subTest(cut=cut):
                self.assertNotIn(cut["excluded_neighbor_id"], self.scenario["nodes"])
                self.assertNotIn((cut["source_id"], cut["excluded_neighbor_id"]), self.scenario_edges)
        self.assertIn(
            {"source_id": "sea_p16", "excluded_neighbor_id": "sea_p35"}, cuts
        )
        self.assertIn(
            {"source_id": "sea_p41", "excluded_neighbor_id": "land_annam_tonkin"}, cuts
        )

    def test_shared_nanking_port_stays_one_physical_facility(self):
        for sea_id in ("sea_p14", "sea_p32"):
            for pair in (("land_china_nanking", sea_id), (sea_id, "land_china_nanking")):
                with self.subTest(pair=pair):
                    edge = self.scenario_edges[pair]
                    self.assertEqual(edge["naval_facilities"], ["major_port"])
                    self.assertEqual(edge["naval_facility_ids"], ["port_nanking_major"])
                    self.assertTrue(edge["railway_connection"])

    def test_honshu_keeps_two_distinct_shipyards_on_the_same_coast(self):
        pair = ("land_jap_honshu", "sea_p15")
        edge = self.scenario_edges[pair]
        shipyard_ids = [
            facility_id
            for facility_type, facility_id in zip(edge["naval_facilities"], edge["naval_facility_ids"])
            if facility_type == "major_shipyard"
        ]
        self.assertEqual(len(shipyard_ids), 2)
        self.assertEqual(len(set(shipyard_ids)), 2)
        self.assertEqual(edge["naval_facilities"], self.source_edges[pair]["naval_facilities"])
        self.assertEqual(edge["naval_facility_ids"], self.source_edges[pair]["naval_facility_ids"])
        reverse = self.scenario_edges[pair[::-1]]
        self.assertEqual(reverse["naval_facilities"], edge["naval_facilities"])
        self.assertEqual(reverse["naval_facility_ids"], edge["naval_facility_ids"])

    def test_honshu_hokkaido_narrow_crossing_keeps_its_touching_sea(self):
        for pair in (
            ("land_jap_honshu", "land_jap_hokkaido"),
            ("land_jap_hokkaido", "land_jap_honshu"),
        ):
            with self.subTest(pair=pair):
                edge = self.scenario_edges[pair]
                self.assertTrue(edge["narrow_crossing"])
                self.assertEqual(edge["narrow_crossings"], 2)
                self.assertFalse(edge["railway_connection"])
                self.assertEqual(edge["narrow_crossing_sea_zones"], ["sea_p16"])
                self.assertEqual(edge, self.source_edges[pair])
        for pair, edge in self.scenario_edges.items():
            with self.subTest(pair=pair):
                for sea_id in edge.get("narrow_crossing_sea_zones", []):
                    self.assertIn(sea_id, self.scenario["nodes"])
                    self.assertEqual(self.scenario["nodes"][sea_id]["type"], "sea")

    def test_world_map_retains_all_reviewed_sea_and_land_neighbors(self):
        for number, expected_seas in MASTER_SEA_NEIGHBORS.items():
            sea_id = f"sea_p{number}"
            expected = {f"sea_p{other}" for other in expected_seas} | MASTER_LAND_NEIGHBORS[number]
            with self.subTest(sea_id=sea_id):
                actual = {edge["neighbor_id"] for edge in self.source["nodes"][sea_id]["neighbors"]}
                self.assertEqual(actual, expected)
                projected = {
                    edge["neighbor_id"] for edge in self.scenario["nodes"][sea_id]["neighbors"]
                }
                self.assertEqual(projected, expected & EXPECTED_IDS)
                for other in expected:
                    self.assertIn((other, sea_id), self.source_edges)
                for other in expected_seas:
                    for pair in ((sea_id, f"sea_p{other}"), (f"sea_p{other}", sea_id)):
                        self.assertEqual(self.source_edges[pair]["border_terrain"], "sea")

    def test_p41_external_shore_is_correct_before_it_is_pruned(self):
        shore = self.source_edges["sea_p41", "land_annam_tonkin"]
        self.assertEqual(shore["border_terrain"], "jungle")
        self.assertEqual(shore["naval_facilities"], ["minor_port"])
        self.assertTrue(shore["railway_connection"])
        self.assertEqual(
            self.source_edges["sea_p41", "land_luzon_and_the_visayas"]["border_terrain"],
            "jungle",
        )
        self.assertNotIn(("sea_p41", "land_annam_tonkin"), self.scenario_edges)


if __name__ == "__main__":
    unittest.main()
