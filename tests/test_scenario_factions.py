"""The M1 identity bridge must not rewrite nationality or frozen setup policy."""

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools import scenario_factions as factions


ROOT = Path(__file__).resolve().parents[1]


def fixture():
    japan = {"scenario_id": "example", "nation": "japan", "alliance": "axis"}
    china = {
        "factions": [
            {"id": "kmt", "printed_name": "KMT", "map_owner_alias": "KMT",
             "controller_id": "kmt", "alliance_id": "allies"},
            {"id": "mongolia", "printed_name": "Mongolia", "map_owner_alias": "Mongolia",
             "controller_id": "comintern", "source_controller_id": "ussr", "alliance_id": "comintern"},
            {"id": "warlord_beiping_hopeh", "printed_name": "Beiping and Hopeh",
             "map_owner_alias": "Zhili Clique", "display_name": "Zhili Clique",
             "controller_id": None, "alliance_id": None},
        ],
        "territories": [{"node_id": "land_warlord", "owner_id": "warlord_beiping_hopeh"}],
    }
    theatre = {
        "_meta": {"scenario_id": "example"},
        "nodes": {
            "land_japan": {"id": "land_japan", "type": "land", "original_owner": "Japan"},
            "land_kmt": {"id": "land_kmt", "type": "land", "original_owner": "KMT"},
            "land_mongolia": {"id": "land_mongolia", "type": "land", "original_owner": "Mongolia"},
            "land_warlord": {"id": "land_warlord", "type": "land", "original_owner": "Zhili Clique"},
            "sea": {"id": "sea", "type": "sea", "original_owner": None},
        },
    }
    return japan, china, theatre


class ScenarioFactionTests(unittest.TestCase):
    def setUp(self):
        self.japan, self.china, self.theatre = fixture()

    def test_whitespace_and_case_resolve_without_fuzzy_matching(self):
        index = factions.build_index(self.japan, self.china, self.theatre)
        for alias in ("Zhili Clique", "ZhiliClique", "  zHILI\tCLIQUE\n", "warlord_beiping_hopeh"):
            self.assertEqual(factions.resolve_faction(alias, index["alias_to_id"]), "warlord_beiping_hopeh")
        for unknown in ("ZhiliClque", "Zhili-Clique", "USSR", "China"):
            with self.subTest(unknown=unknown), self.assertRaisesRegex(ValueError, "Unknown faction alias"):
                factions.resolve_faction(unknown, index["alias_to_id"])

    def test_empty_or_non_string_aliases_are_rejected(self):
        for alias in (None, "", " \t", 1, []):
            with self.subTest(alias=alias), self.assertRaisesRegex(ValueError, "nonempty strings"):
                factions.normalize_alias(alias)

    def test_duplicate_canonical_ids_are_rejected(self):
        self.china["factions"].append(copy.deepcopy(self.china["factions"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate canonical faction ID: kmt"):
            factions.build_index(self.japan, self.china, self.theatre)

    def test_ambiguous_aliases_including_canonical_id_collisions_are_rejected(self):
        for ambiguous in (" k M t ", "japan"):
            self.china["factions"][2]["printed_name"] = ambiguous
            with self.subTest(ambiguous=ambiguous), self.assertRaisesRegex(ValueError, "Ambiguous faction alias"):
                factions.build_index(self.japan, self.china, self.theatre)

    def test_in_memory_build_preserves_sources_and_separates_identity_from_control(self):
        before = copy.deepcopy((self.japan, self.china, self.theatre))
        index = factions.build_index(self.japan, self.china, self.theatre)
        self.assertEqual((self.japan, self.china, self.theatre), before)
        self.assertEqual(index["land_original_owners"]["land_warlord"]["original_faction_id"], "warlord_beiping_hopeh")
        self.assertEqual(index["factions"]["warlord_beiping_hopeh"]["display_name"], "Zhili Clique")
        self.assertEqual(index["factions"]["warlord_beiping_hopeh"]["printed_name"], "Beiping and Hopeh")
        self.assertIsNone(index["factions"]["warlord_beiping_hopeh"]["initial_control"]["controller_id"])
        mongolia = index["factions"]["mongolia"]
        self.assertEqual(mongolia["initial_control"]["controller_id"], "comintern")
        self.assertEqual(mongolia["initial_control"]["source_controller_id"], "ussr")
        self.assertEqual(index["land_original_owners"]["land_mongolia"]["original_faction_id"], "mongolia")
        self.assertNotIn("ussr", index["factions"])
        self.assertNotIn("comintern", index["factions"])
        self.assertNotIn("sea", index["land_original_owners"])
        mongolia["initial_control"]["controller_id"] = "changed"
        self.assertEqual(self.china["factions"][1]["controller_id"], "comintern")

    def test_unknown_map_and_setup_owner_references_are_rejected(self):
        self.theatre["nodes"]["land_warlord"]["original_owner"] = "Unlisted Clique"
        with self.assertRaisesRegex(ValueError, "Unknown faction alias"):
            factions.build_index(self.japan, self.china, self.theatre)
        self.theatre["nodes"]["land_warlord"]["original_owner"] = "Zhili Clique"
        self.china["territories"][0]["owner_id"] = "not_a_faction"
        with self.assertRaisesRegex(ValueError, "unknown canonical setup owner"):
            factions.build_index(self.japan, self.china, self.theatre)

    def test_setup_owner_override_does_not_rewrite_static_nationality(self):
        self.china["territories"][0]["owner_id"] = "kmt"
        index = factions.build_index(self.japan, self.china, self.theatre)
        self.assertEqual(index["land_original_owners"]["land_warlord"], {
            "source_original_owner": "Zhili Clique",
            "original_faction_id": "warlord_beiping_hopeh",
        })
        self.assertEqual(self.china["territories"][0]["owner_id"], "kmt")

    def test_mismatched_scenario_ids_are_rejected(self):
        self.theatre["_meta"]["scenario_id"] = "other_scenario"
        with self.assertRaisesRegex(ValueError, "scenario_id values disagree"):
            factions.build_index(self.japan, self.china, self.theatre)

    def write_inputs(self, directory):
        paths = {}
        for key, document in (("japan", self.japan), ("china", self.china), ("map", self.theatre)):
            paths[key] = Path(directory) / f"{key}.json"
            paths[key].write_text(json.dumps(document))
        return paths

    def test_invalid_input_does_not_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.write_inputs(directory)
            output = Path(directory) / "index.json"
            output.write_text("preserve output")
            paths["china"].write_text('{"factions": [], "factions": []}')
            with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
                factions.build(paths["map"], paths["japan"], paths["china"], output)
            self.assertEqual(output.read_text(), "preserve output")

    def test_source_inputs_and_symlinks_cannot_be_output(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.write_inputs(directory)
            alias = Path(directory) / "alias.json"
            alias.symlink_to(paths["map"])
            for output in [*paths.values(), alias]:
                with self.subTest(output=output), self.assertRaisesRegex(ValueError, "must not overwrite"):
                    factions.build(paths["map"], paths["japan"], paths["china"], output)

    def test_cli_reports_counts_and_readable_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.write_inputs(directory)
            output = Path(directory) / "index.json"
            command = [sys.executable, str(ROOT / "tools/scenario_factions.py"),
                       "--map", str(paths["map"]), "--japan-setup", str(paths["japan"]),
                       "--china-setup", str(paths["china"]), "--output", str(output)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("4 canonical factions, 4 retained land identities", result.stdout)
            paths["map"].write_text("{bad")
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("Invalid JSON", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_real_index_covers_every_retained_original_owner_with_source_identities(self):
        japan, _ = factions.load_document(factions.DEFAULT_JAPAN_SETUP)
        china, _ = factions.load_document(factions.DEFAULT_CHINA_SETUP)
        theatre, _ = factions.load_document(factions.DEFAULT_MAP)
        index = factions.build_index(japan, china, theatre)
        land_ids = {node_id for node_id, node in theatre["nodes"].items() if node["type"] == "land"}
        self.assertEqual(set(index["land_original_owners"]), land_ids)
        self.assertEqual(len(land_ids), 31)
        self.assertEqual(set(index["factions"]), {japan["nation"], *[f["id"] for f in china["factions"]]})
        self.assertEqual(len(index["factions"]), 12)
        for source in china["factions"]:
            faction = index["factions"][source["id"]]
            self.assertEqual(faction["printed_name"], source["printed_name"])
            self.assertEqual(faction["display_name"], source.get("display_name", source["map_owner_alias"]))
            self.assertEqual(faction["map_owner_alias"], source["map_owner_alias"])
            self.assertEqual(faction["initial_control"]["controller_id"], source["controller_id"])
        for node_id, owner in index["land_original_owners"].items():
            self.assertEqual(owner["source_original_owner"], theatre["nodes"][node_id]["original_owner"])
            self.assertEqual(factions.resolve_faction(owner["source_original_owner"], index["alias_to_id"]), owner["original_faction_id"])
        # Reconciliation evidence for this frozen setup only. The identity
        # bridge also permits valid scenario possession overrides.
        for row in china["territories"]:
            self.assertEqual(index["land_original_owners"][row["node_id"]]["original_faction_id"], row["owner_id"])

    def test_real_build_matches_checked_in_index_without_changing_frozen_inputs(self):
        inputs = (factions.DEFAULT_MAP, factions.DEFAULT_JAPAN_SETUP, factions.DEFAULT_CHINA_SETUP)
        before = {path: path.read_bytes() for path in inputs}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested/faction_index.json"
            document = factions.build(output_path=output)
            original = output.read_bytes()
            factions.build(output_path=output)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(original, factions.DEFAULT_OUTPUT.read_bytes())
            for source in document["sources"].values():
                path = ROOT / source["path"]
                self.assertEqual(source["sha256"], hashlib.sha256(before[path]).hexdigest())
        self.assertEqual({path: path.read_bytes() for path in inputs}, before)


if __name__ == "__main__":
    unittest.main()
