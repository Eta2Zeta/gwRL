"""Geographic features must retain their rule scope across map projections."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

from tools import world_map_features as features
from tools import build_theatre_scenario as theatre
from tools import build_nation_home_country_json as home


ROOT = Path(__file__).resolve().parents[1]


def edge(target):
    return {
        "neighbor_id": target, "border_terrain": "sea", "passable": True,
        "has_river": False, "river_crossing": False, "railway_connection": False,
        "gauge_change": False, "naval_facilities": [], "naval_facility_ids": [],
        "port_or_dock_connection": False, "canal_or_strait": None,
        "narrow_crossing": False, "narrow_crossings": 0,
    }


def fixture():
    nodes = {
        identity: {
            "id": identity, "name": identity, "type": kind,
            "terrain": "sea" if kind == "sea" else ["mountain", "jungle"],
            "original_owner": None if kind == "sea" else "Example",
            "current_owner": None, "node_facilities": [], "node_facility_ids": [],
            "neighbors": [],
        }
        for identity, kind in (("port", "land"), ("s1", "sea"), ("s2", "sea"), ("s3", "sea"))
    }
    for a, b in (("port", "s1"), ("s1", "s2"), ("s2", "s3")):
        nodes[a]["neighbors"].append(edge(b))
        nodes[b]["neighbors"].append(edge(a))
    return {
        "_meta": {"schema_version": 2}, "nodes": nodes,
        "convoy_lines": [{
            "id": "convoy_example", "sea_zone_ids": ["s1", "s2", "s3"],
            "endpoints": [{"kind": "land", "node_id": "port"}, {"kind": "sea", "node_id": "s3"}],
            "maximum_ipp_loss": 5, "loss_cap_status": "numeric_cap_printed",
        }],
    }


class WorldMapFeatureTests(unittest.TestCase):
    def test_convoy_has_one_shared_limit_and_requires_complete_path(self):
        document = fixture()
        features.validate_features(document)
        self.assertEqual(document["convoy_lines"][0]["maximum_ipp_loss"], 5)
        self.assertTrue(all("maximum_ipp_loss" not in node for node in document["nodes"].values()))
        document["nodes"]["s2"]["neighbors"] = [edge("s1")]
        with self.assertRaisesRegex(ValueError, "convoy path lacks"):
            features.validate_features(document)

    def test_closed_projection_omits_entire_incomplete_convoy(self):
        document = fixture()
        manifest = {"schema_version": 1, "scenario_id": "fixture", "included_node_ids": ["port", "s1", "s2"]}
        result = theatre.extract_document(document, manifest)
        self.assertEqual(result["convoy_lines"], [])
        self.assertEqual(result["_meta"]["feature_cuts"], [{
            "layer": "convoy_lines", "id": "convoy_example", "excluded_node_ids": ["s3"],
        }])
        manifest["included_node_ids"].append("s3")
        result = theatre.extract_document(document, manifest)
        self.assertEqual(result["convoy_lines"], document["convoy_lines"])

    def test_version_two_preserves_unknown_direction_without_false_default(self):
        document = fixture()
        incoming = document["nodes"]["s1"]["neighbors"][0]
        incoming["border_terrain"] = None
        incoming["river_crossing"] = None
        manifest = {"schema_version": 1, "scenario_id": "fixture", "included_node_ids": list(document["nodes"])}
        result = theatre.extract_document(document, manifest)
        self.assertIsNone(result["nodes"]["s1"]["neighbors"][0]["river_crossing"])
        self.assertIsNone(result["nodes"]["s1"]["neighbors"][0]["border_terrain"])
        self.assertFalse(result["nodes"]["port"]["neighbors"][0]["river_crossing"])
        document["_meta"]["schema_version"] = 1
        with self.assertRaises(ValueError):
            theatre.validate_source(document)

    def test_exceptional_route_does_not_create_ordinary_movement(self):
        document = fixture()
        document["exceptional_routes"] = [{
            "id": "route_special", "kind": "naval_special_transit",
            "endpoint_ids": ["s1", "s3"], "ordinary_adjacency": False,
        }]
        features.validate_features(document)
        document["nodes"]["s1"]["neighbors"].append(edge("s3"))
        document["nodes"]["s3"]["neighbors"].append(edge("s1"))
        with self.assertRaisesRegex(ValueError, "ordinary neighbor"):
            features.validate_features(document)

    def test_unresolved_facility_inventory_stays_unknown_in_projection(self):
        document = fixture()
        for source, target in (("port", "s1"), ("s1", "port")):
            coast = next(row for row in document["nodes"][source]["neighbors"] if row["neighbor_id"] == target)
            coast["port_or_dock_connection"] = None
            coast["naval_facility_inventory_status"] = "partial"
        manifest = {"schema_version": 1, "scenario_id": "fixture", "included_node_ids": ["port", "s1"]}
        result = theatre.extract_document(document, manifest)
        for source in ("port", "s1"):
            self.assertIsNone(result["nodes"][source]["neighbors"][0]["port_or_dock_connection"])
            self.assertEqual(result["nodes"][source]["neighbors"][0]["naval_facility_inventory_status"], "partial")

        # Null is not an unrestricted substitute for an omitted boolean field.
        document["nodes"]["port"]["neighbors"][0]["naval_facility_inventory_status"] = "confirmed"
        with self.assertRaisesRegex(ValueError, "port_or_dock_connection must be a boolean"):
            theatre.validate_source(document)
        document["nodes"]["port"]["neighbors"][0]["naval_facility_inventory_status"] = "partial"
        document["_meta"]["schema_version"] = 1
        with self.assertRaisesRegex(ValueError, "port_or_dock_connection must be a boolean"):
            theatre.validate_source(document)

    def test_facility_projection_preserves_identity_and_review_status(self):
        document = fixture()
        document["facilities"] = {
            "facility_one": {"id": "facility_one", "land_id": "port", "type": "major_port", "sea_accesses": ["s1", "s3"], "review_status": "source_verified"},
            "facility_two": {"id": "facility_two", "land_id": "port", "type": "major_port", "sea_accesses": ["s1"], "review_status": "source_verified"},
            "airfield": {"id": "airfield", "land_id": "port", "type": "airfield", "sea_accesses": [], "review_status": "source_verified"},
        }
        projected, cuts = features.project_features(document, {"port", "s1"}, {})
        self.assertEqual(set(projected["facilities"]), {"facility_one", "facility_two", "airfield"})
        self.assertEqual(projected["facilities"]["facility_one"]["sea_accesses"], ["s1"])
        self.assertEqual(projected["facilities"]["facility_one"]["review_status"], "source_verified")
        self.assertIn({"layer": "facility_accesses", "id": "facility_one", "excluded_node_ids": ["s3"]}, cuts)
        self.assertEqual(document["facilities"]["facility_one"]["sea_accesses"], ["s1", "s3"])

    def test_usa_home_country_does_not_depend_on_routes_or_current_control(self):
        nodes = {identity: {"id": identity, "name": identity, "type": "land", "neighbors": [], "current_owner": "Other"} for identity in home.USA_MAINLAND_IDS}
        ids = home.contiguous_us_home(nodes)
        self.assertIn("land_usa_new_england", ids)
        self.assertEqual(len(ids), 19)
        nodes["land_usa_alaska"] = {"id": "land_usa_alaska", "name": "Alaska", "type": "land", "neighbors": []}
        nodes["land_usa_washington_dc"]["neighbors"].append({"neighbor_id": "land_usa_alaska"})
        self.assertEqual(home.contiguous_us_home(nodes), ids)

    def test_authored_features_exclude_unresolved_route_and_keep_reef_specific(self):
        authored = json.loads(features.FEATURE_SOURCE.read_text())
        self.assertEqual(len(authored["convoy_lines"]), 15)
        self.assertNotIn("Manila Line", [line["printed_name"] for line in authored["convoy_lines"]])
        arctic = next(line for line in authored["convoy_lines"] if line["printed_name"] == "Soviet Arctic Line")
        self.assertIsNone(arctic["maximum_ipp_loss"])
        self.assertEqual(arctic["loss_cap_status"], "no_numeric_cap_printed")
        reef = authored["coast_restrictions"]
        self.assertEqual({row["source_sea_id"] for row in reef}, {"sea_p64", "sea_p71", "sea_p72"})
        self.assertTrue(all(row["amphibious_assault_allowed"] is False and "passable" not in row for row in reef))
        for crossing in authored["narrow_crossing_blocker_updates"]:
            self.assertEqual(len(crossing["land_ids"]), 2)
            self.assertTrue(all(identity.startswith("land_") for identity in crossing["land_ids"]))
            self.assertTrue(all(identity.startswith("sea_") for identity in crossing["blocking_sea_ids"]))
        rules = json.loads((ROOT / features.RULES_PROFILE).read_text())
        self.assertIn("japan_kamikaze", rules["rules"])
        self.assertNotIn("kamikaze", authored)
        capacities = rules["rules"]["strategic_rail"]["capacity_per_player_turn"]
        self.assertEqual(set(capacities), set(authored["rail_region_ids"]))
        for layer in ("convoy_lines", "passages", "exceptional_routes", "coast_restrictions"):
            for row in authored[layer]:
                self.assertIn(row["rule_id"], rules["rules"])


if __name__ == "__main__":
    unittest.main()
