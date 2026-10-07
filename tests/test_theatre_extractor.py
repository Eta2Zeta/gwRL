"""Closed-theatre extraction must be a lossless, validated map projection."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/build_theatre_scenario.py"
SPEC = importlib.util.spec_from_file_location("theatre_builder", SCRIPT)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def edge(target, **updates):
    result = {
        "neighbor_id": target, "border_terrain": "normal", "passable": True,
        "has_river": False, "river_crossing": False, "railway_connection": False,
        "gauge_change": False, "naval_facilities": [], "naval_facility_ids": [],
        "port_or_dock_connection": False, "canal_or_strait": None,
        "narrow_crossing": False, "narrow_crossings": 0,
        "special_fortification": None,
    }
    result.update(updates)
    return result


def fixture():
    shared_port = {
        "naval_facilities": ["major_port"], "naval_facility_ids": ["port_a"],
        "port_or_dock_connection": True, "railway_connection": True,
    }
    nodes = {
        node_id: {
            "id": node_id, "name": node_id.upper(), "type": "land" if node_id == "a" else "sea",
            "terrain": "mountain" if node_id == "a" else "sea", "ipp_value": 3,
            "node_facilities": ["airfield"] if node_id == "a" else [],
            "node_facility_ids": ["airfield_a"] if node_id == "a" else [],
            "future_node_data": {"custom": [1, 2]}, "neighbors": [],
        }
        for node_id in ("a", "b", "c", "outside")
    }
    # The same physical facility serves two sea zones. Never re-ID or duplicate it.
    nodes["a"]["neighbors"] = [
        edge("c", **shared_port, border_terrain="sea"),
        edge("outside"),
        edge("b", **shared_port, border_terrain="sea"),
    ]
    nodes["b"]["neighbors"] = [edge("a", **shared_port, border_terrain=["desert", "mountain"], river_crossing=True)]
    nodes["c"]["neighbors"] = [edge("a", **shared_port, border_terrain="mountain")]
    nodes["outside"]["neighbors"] = [edge("a", border_terrain="jungle")]
    nodes["a"]["neighbors"][2]["future_edge_data"] = {"directional": ["unchanged"]}
    return {"_meta": {"warnings": ["Unresolved source boundary"]}, "nodes": nodes}, {
        "schema_version": 1, "scenario_id": "test_campaign", "boundary_policy": "closed",
        "included_node_ids": ["c", "a", "b"],
        "campaign": {"start": "1936-07", "end": "1941-07"},
    }


class TheatreExtractorTests(unittest.TestCase):
    def setUp(self):
        self.source, self.manifest = fixture()

    def test_exact_induced_subgraph_preserves_all_data(self):
        source_before, manifest_before = copy.deepcopy(self.source), copy.deepcopy(self.manifest)
        result = builder.extract_document(self.source, self.manifest)
        self.assertEqual(list(result["nodes"]), ["a", "b", "c"])
        for node_id, node in result["nodes"].items():
            expected = copy.deepcopy(self.source["nodes"][node_id])
            expected["neighbors"] = [e for e in expected["neighbors"] if e["neighbor_id"] != "outside"]
            self.assertEqual(node, expected)
        self.assertEqual([e["neighbor_id"] for e in result["nodes"]["a"]["neighbors"]], ["c", "b"])
        self.assertEqual(result["_meta"]["excluded_neighbor_count"], 1)
        self.assertEqual(result["_meta"]["boundary_cuts"], [{"source_id": "a", "excluded_neighbor_id": "outside"}])
        self.assertEqual(result["_meta"]["source_map_meta"], self.source["_meta"])
        self.assertEqual(result["_meta"]["scenario_manifest"], self.manifest)
        result["nodes"]["a"]["future_node_data"]["custom"].append(3)
        result["nodes"]["a"]["neighbors"][1]["future_edge_data"]["directional"].append("new")
        result["_meta"]["source_map_meta"]["warnings"].append("new")
        result["_meta"]["scenario_manifest"]["campaign"]["start"] = "other"
        self.assertEqual(self.source, source_before)
        self.assertEqual(self.manifest, manifest_before)

    def test_directional_terrain_and_crossing_are_not_symmetrized(self):
        result = builder.extract_document(self.source, self.manifest)
        forward = result["nodes"]["a"]["neighbors"][1]
        reverse = result["nodes"]["b"]["neighbors"][0]
        self.assertEqual(forward["border_terrain"], "sea")
        self.assertEqual(reverse["border_terrain"], ["desert", "mountain"])
        self.assertFalse(forward["river_crossing"])
        self.assertTrue(reverse["river_crossing"])

    def test_shared_facility_ids_remain_shared(self):
        nodes = builder.extract_document(self.source, self.manifest)["nodes"]
        self.assertEqual([e["naval_facility_ids"] for e in nodes["a"]["neighbors"]], [["port_a"], ["port_a"]])
        self.assertEqual(nodes["a"]["node_facility_ids"], ["airfield_a"])

    def test_single_node_is_allowed_and_cannot_escape(self):
        self.manifest["included_node_ids"] = ["a"]
        result = builder.extract_document(self.source, self.manifest)
        self.assertEqual(result["nodes"]["a"]["neighbors"], [])
        self.assertEqual(result["_meta"]["excluded_neighbor_count"], 3)

    def test_invalid_manifests_fail(self):
        for updates, message in (
            ({"schema_version": 2}, "schema_version"),
            ({"schema_version": True}, "schema_version"),
            ({"scenario_id": "  "}, "scenario_id"),
            ({"included_node_ids": []}, "nonempty list"),
            ({"included_node_ids": ["a", "a"]}, "duplicate IDs"),
            ({"included_node_ids": ["missing"]}, "missing source nodes"),
            ({"included_node_ids": [1]}, "nonempty strings"),
            ({"boundary_policy": "open"}, "boundary_policy"),
        ):
            with self.subTest(updates=updates):
                with self.assertRaisesRegex(ValueError, message):
                    builder.extract_document(self.source, {**self.manifest, **updates})

    def test_bad_source_graphs_fail_even_outside_selection(self):
        mutations = (
            (lambda n: n["outside"].update(id="bad"), "key/id mismatch"),
            (lambda n: n["outside"]["neighbors"].append(edge("missing")), "unknown neighbor"),
            (lambda n: n["outside"]["neighbors"].append(edge("outside")), "self-loop"),
            (lambda n: n["outside"]["neighbors"].append(edge("a")), "duplicate neighbor"),
            (lambda n: n["outside"].update(neighbors=[]), "Missing reverse neighbor"),
        )
        for mutate, message in mutations:
            with self.subTest(message=message):
                source = copy.deepcopy(self.source)
                mutate(source["nodes"])
                with self.assertRaisesRegex(ValueError, message):
                    builder.extract_document(source, self.manifest)

    def test_reciprocal_infrastructure_must_agree(self):
        for field, value in (
            ("passable", False), ("has_river", True), ("railway_connection", False),
            ("gauge_change", True), ("naval_facilities", ["minor_port"]),
            ("naval_facility_ids", ["other_port"]), ("port_or_dock_connection", False),
            ("canal_or_strait", "canal"),
        ):
            with self.subTest(field=field):
                source = copy.deepcopy(self.source)
                source["nodes"]["b"]["neighbors"][0][field] = value
                with self.assertRaisesRegex(ValueError, "reciprocal " + field):
                    builder.extract_document(source, self.manifest)

    def test_malformed_edge_fields_fail(self):
        for updates, message in (
            ({"railway_connection": 1}, "must be a boolean"),
            ({"railway_connection": False, "gauge_change": True}, "requires a railway"),
            ({"narrow_crossings": True}, "nonnegative integer"),
            ({"narrow_crossings": 1}, "flag/count disagree"),
            ({"naval_facility_ids": []}, "equal lengths"),
            ({"border_terrain": []}, "border_terrain"),
        ):
            with self.subTest(updates=updates):
                source = copy.deepcopy(self.source)
                source["nodes"]["b"]["neighbors"][0].update(updates)
                with self.assertRaisesRegex(ValueError, message):
                    builder.extract_document(source, self.manifest)

    def test_strict_json_loader(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for text, message in (
                ('{"nodes": {}, "nodes": {}}', "Duplicate JSON key"),
                ('{"a": {"id": 1, "id": 2}}', "Duplicate JSON key"),
                ('{"a": NaN}', "Non-finite"),
                ('{"a": Infinity}', "Non-finite"),
                ('[]', "Expected a JSON object"),
            ):
                with self.subTest(text=text):
                    path.write_text(text)
                    with self.assertRaisesRegex(ValueError, message):
                        builder.load_document(path)

    def test_narrow_crossing_dependencies_are_preserved_and_validated(self):
        nodes = self.source["nodes"]
        nodes["b"]["type"] = "land"
        for source, target in (("a", "b"), ("b", "a")):
            crossing = next(e for e in nodes[source]["neighbors"] if e["neighbor_id"] == target)
            crossing.update(railway_connection=False, narrow_crossing=True,
                            narrow_crossings=2, narrow_crossing_sea_zones=["c"])
        result = builder.extract_document(self.source, self.manifest)
        self.assertEqual(result["nodes"]["b"]["neighbors"][0]["narrow_crossing_sea_zones"], ["c"])
        with self.assertRaisesRegex(ValueError, "excluded blocking seas"):
            builder.extract_document(self.source, {**self.manifest, "included_node_ids": ["a", "b"]})
        nodes["b"]["neighbors"][0]["narrow_crossing_sea_zones"] = ["outside"]
        with self.assertRaisesRegex(ValueError, "reciprocal narrow_crossing_sea_zones"):
            builder.extract_document(self.source, self.manifest)
        nodes["b"]["neighbors"][0]["narrow_crossing_sea_zones"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "must reference sea nodes"):
            builder.extract_document(self.source, self.manifest)

    def test_malformed_crossing_targets_and_blocking_seas_fail_cleanly(self):
        nodes = self.source["nodes"]
        nodes["b"]["type"] = "land"
        for source, target in (("a", "b"), ("b", "a")):
            crossing = next(e for e in nodes[source]["neighbors"] if e["neighbor_id"] == target)
            crossing.update(railway_connection=False, narrow_crossing=True,
                            narrow_crossings=2, narrow_crossing_sea_zones=["c"])
        for node_id in ("b", "c"):
            for malformed in (None, [], "not a node"):
                with self.subTest(node_id=node_id, malformed=malformed):
                    source = copy.deepcopy(self.source)
                    source["nodes"][node_id] = malformed
                    with self.assertRaisesRegex(ValueError, "key/id mismatch"):
                        builder.extract_document(source, self.manifest)

    def write_inputs(self, directory):
        source_path, manifest_path = Path(directory) / "world.json", Path(directory) / "manifest.json"
        source_path.write_text(json.dumps(self.source))
        manifest_path.write_text(json.dumps(self.manifest))
        return source_path, manifest_path

    def test_build_is_reproducible_hashed_and_does_not_change_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path, manifest_path = self.write_inputs(directory)
            before = [p.read_bytes() for p in (source_path, manifest_path)]
            output = Path(directory) / "nested" / "map.json"
            document = builder.build(source_path, manifest_path, output)
            original = output.read_bytes()
            builder.build(source_path, manifest_path, output)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual([p.read_bytes() for p in (source_path, manifest_path)], before)
            self.assertEqual(document["_meta"]["source_map_sha256"], hashlib.sha256(before[0]).hexdigest())
            self.assertEqual(document["_meta"]["manifest_sha256"], hashlib.sha256(before[1]).hexdigest())
            self.assertEqual(document["_meta"]["source_map"], "world.json")
            self.assertEqual(json.loads(original), document)

    def test_invalid_input_never_overwrites_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path, manifest_path = self.write_inputs(directory)
            output = Path(directory) / "map.json"
            output.write_text("keep this output")
            manifest_path.write_text('{"schema_version": 99}')
            with self.assertRaises(ValueError):
                builder.build(source_path, manifest_path, output)
            self.assertEqual(output.read_text(), "keep this output")

    def test_source_manifest_and_symlink_cannot_be_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path, manifest_path = self.write_inputs(directory)
            link_path = Path(directory) / "alias.json"
            link_path.symlink_to(source_path)
            for output in (source_path, manifest_path, link_path):
                with self.subTest(output=output):
                    with self.assertRaisesRegex(ValueError, "must not overwrite"):
                        builder.build(source_path, manifest_path, output)

    def test_cli_reports_success_and_readable_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path, manifest_path = self.write_inputs(directory)
            output = Path(directory) / "map.json"
            command = [sys.executable, str(SCRIPT), "--map", str(source_path), "--manifest", str(manifest_path), "--output", str(output)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("3 nodes, 1 excluded neighbor entries removed", result.stdout)
            source_path.write_text("{bad")
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("Invalid JSON", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_current_full_map_can_be_projected_without_mutation(self):
        source_path = ROOT / "game_content/maps/gw36_manual_map.json"
        source, _ = builder.load_document(source_path)
        manifest = {
            "schema_version": 1, "scenario_id": "smoke_test",
            "included_node_ids": ["land_china_nanking", "sea_p14", "sea_p32"],
        }
        result = builder.extract_document(source, manifest)
        included = set(manifest["included_node_ids"])
        for node_id, node in result["nodes"].items():
            expected = copy.deepcopy(source["nodes"][node_id])
            expected["neighbors"] = [e for e in expected["neighbors"] if e["neighbor_id"] in included]
            self.assertEqual(node, expected)
        self.assertGreater(result["_meta"]["excluded_neighbor_count"], 0)


if __name__ == "__main__":
    unittest.main()
