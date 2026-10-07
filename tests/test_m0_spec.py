"""M0 transcription/contract checks, not tests of unimplemented game mechanics."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "game_content/scenarios/japan_china_1936"


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(), object_pairs_hook=unique_object)


def unit_counts(rows):
    counts = Counter()
    for row in rows:
        for unit in row["units"]:
            counts[unit["type"]] += unit["count"]
    return counts


def map_facilities(nodes):
    """Collect ID/type/location; reciprocal coast copies are not extra assets."""
    result = {}
    for node_id, node in nodes.items():
        if node["type"] != "land":
            continue
        pairs = list(zip(node.get("node_facility_ids", []), node.get("node_facilities", [])))
        for edge in node["neighbors"]:
            pairs.extend(zip(edge.get("naval_facility_ids", []), edge.get("naval_facilities", [])))
        for facility_id, kind in pairs:
            value = (node_id, kind)
            if facility_id in result and result[facility_id] != value:
                raise AssertionError(f"Conflicting map facility: {facility_id}")
            result[facility_id] = value
    return result


class M0SpecificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = read_json(SCENARIO / "manifest.json")
        cls.contract = read_json(SCENARIO / "m0/scenario_contract.json")
        cls.japan = read_json(SCENARIO / "m0/japan_setup.json")
        cls.china = read_json(SCENARIO / "m0/china_minor_setup.json")
        cls.convoys = read_json(SCENARIO / "m0/convoy_audit.json")
        cls.nodes = read_json(SCENARIO / "map.json")["nodes"]

    def test_specification_not_playable_and_pending_choices_explicit(self):
        self.assertEqual(self.contract["status"], "m0_audit_ready_pending_decisions_not_playable")
        for document in (self.japan, self.china):
            self.assertEqual(document["status"], "audited_specification_not_playable")
        self.assertEqual(self.manifest["m0_specification"]["contract"], "m0/scenario_contract.json")
        decisions = [item["id"] for item in self.contract["pending_decisions"]]
        self.assertEqual(len(decisions), len(set(decisions)))
        self.assertIn("unpriced_setup_values", decisions)
        self.assertIn("japan_national_queue_scope", decisions)
        for filename in self.contract["setup_files"]:
            self.assertTrue((SCENARIO / "m0" / filename).is_file())

    def test_core_ledger_has_unique_traceable_fixture_ids(self):
        ledger = (ROOT / "docs/m0/core_rules_ledger.md").read_text()
        rows = re.findall(r"^\| (R\d{3}); (.+)$", ledger, flags=re.MULTILINE)
        self.assertEqual([row[0] for row in rows], [f"R{number:03d}" for number in range(143)])
        for fixture_id, cells in rows:
            self.assertIn("RB", cells, fixture_id)
            self.assertEqual(len(cells.split("|")), 7, fixture_id)

    def test_source_hashes_match_current_local_sources(self):
        seen = {}
        for document in (self.japan, self.china, self.convoys):
            for source in document["sources"].values():
                path = ROOT / source["path"]
                self.assertTrue(path.is_file(), path)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), source["sha256"], path)
                if path in seen:
                    self.assertEqual(source["sha256"], seen[path])
                seen[path] = source["sha256"]
        self.assertEqual(len(seen), 9)  # Seven PDFs, authoritative JSON and map image.

    def test_local_convoy_route_is_complete_and_cap_is_not_an_income_grant(self):
        lines = {line["id"]: line for line in self.convoys["audited_lines"]}
        line = lines["convoy_japan_nagasaki"]
        endpoints = [endpoint["node_id"] for endpoint in line["endpoints"]]
        route = [endpoints[0], *line["ordered_sea_zone_ids"], endpoints[1]]
        self.assertEqual(route, ["land_manchuria_rehe", "sea_p14", "sea_p15", "land_jap_kyushu"])
        self.assertTrue(set(route) <= set(self.nodes))
        for start, end in zip(route, route[1:]):
            self.assertIn(end, {edge["neighbor_id"] for edge in self.nodes[start]["neighbors"]})
        self.assertEqual(line["max_ipp_loss_per_player_turn"], 5)
        self.assertEqual(line["excluded_sea_zone_ids"], [])
        self.assertEqual(line["owner"], "japan")
        self.assertEqual(line["theatre_classification"], "retained_conditionally_raidable")
        self.assertTrue(self.convoys["rules"]["no_income_creation"])
        japan_cash = next(x for x in self.contract["starting_accounts"]["national_accounts"] if x["nation"] == "japan")
        self.assertEqual(japan_cash["treasury_ipp"], 15)

    def test_cut_tokyo_convoy_is_not_stitched_across_missing_seas(self):
        lines = {line["id"]: line for line in self.convoys["audited_lines"]}
        line = lines["convoy_japan_tokyo"]
        self.assertEqual(line["ordered_sea_zone_ids"],
                         ["sea_p16", "sea_p34", "sea_p33", "sea_p32", "sea_p41", "sea_p50"])
        self.assertEqual(set(line["ordered_sea_zone_ids"]) - set(self.nodes), {"sea_p34", "sea_p50"})
        self.assertEqual(line["excluded_sea_zone_ids"], ["sea_p34", "sea_p50"])
        self.assertEqual(line["theatre_classification"], "excluded_cut_route_and_terminal_outside_theatre")
        self.assertEqual(set(self.convoys["selected_zone_coverage"]),
                         {node_id for node_id, node in self.nodes.items() if node["type"] == "sea"})
        for node_id, line_ids in self.convoys["selected_zone_coverage"].items():
            self.assertEqual(set(line_ids), {key for key, entry in lines.items() if node_id in entry["ordered_sea_zone_ids"]})

    def test_setup_rows_have_provenance_and_no_unselected_locations(self):
        page_counts = {"japan_nrs": 9, "kmt_nrs": 7, "ccp_nrs": 7,
                       "fec_nrs": 6, "neutral_setup": 2, "rulebook": 108}
        for document, key in ((self.japan, "placements"), (self.china, "territories")):
            ids = []
            for row in document[key]:
                ids.append(row["node_id"])
                self.assertIn(row["node_id"], self.nodes)
                sources = [row["source"]] if "source" in row else row["source_refs"]
                self.assertTrue(sources)
                for source in sources:
                    source_id = source.get("source_id", source.get("id"))
                    self.assertIn(source_id, document["sources"])
                    self.assertGreaterEqual(source["pdf_page"], 1)
                    self.assertLessEqual(source["pdf_page"], page_counts[source_id])
                kinds = [unit["type"] for unit in row["units"]]
                self.assertEqual(len(kinds), len(set(kinds)))
                for unit in row["units"]:
                    self.assertIs(type(unit["count"]), int)
                    self.assertGreater(unit["count"], 0)
                self.assertEqual(row["construction"], [])
            self.assertEqual(len(ids), len(set(ids)))

    def test_all_land_setup_accounted_for_including_explicit_empty_tiles(self):
        covered = {row["node_id"] for row in self.japan["placements"] + self.china["territories"]}
        covered.update(self.japan["empty_retained_japanese_locations"])
        land_ids = {node_id for node_id, node in self.nodes.items() if node["type"] == "land"}
        self.assertEqual(covered & land_ids, land_ids)
        self.assertEqual(len(land_ids), 32)
        self.assertNotIn("land_mongolia_tannu_tuva", covered)
        china_rows = {row["node_id"]: row for row in self.china["territories"]}
        for node_id in ("land_hainan", "land_mongolia_kobdo", "land_mongolia_ulyassutai"):
            self.assertEqual(china_rows[node_id]["units"], [])

    def test_japan_column_totals_reconcile_without_parenthesized_carriers(self):
        deployed = unit_counts(self.japan["placements"])
        self.assertEqual(dict(deployed), self.japan["totals"]["deployed_by_type"])
        self.assertEqual(sum(deployed.values()), 48)
        all_pieces = deployed + unit_counts(self.japan["excluded_setup"])
        for queued in self.japan["starting_construction"]:
            all_pieces[queued["type"]] += queued["count"]
        for row in self.japan["placements"]:
            for facility in row["facilities"]:
                all_pieces[facility["type"]] += facility["count"]
        for row in self.japan["excluded_setup"]:
            for counter in row.get("ability_counters", []):
                all_pieces[counter["type"]] += counter["count"]
        self.assertEqual(dict(all_pieces), self.japan["totals"]["printed_total_row_by_type"])
        self.assertEqual(deployed["light_carrier"], 1)
        self.assertEqual(all_pieces["kamikaze"], 6)
        self.assertNotIn("kamikaze", deployed)

    def test_non_japanese_setup_totals_and_faction_identity(self):
        counts = unit_counts(self.china["territories"])
        self.assertEqual(dict(counts), self.china["audit_totals"]["units_by_type"])
        by_group = Counter()
        factions = {f["id"]: f for f in self.china["factions"]}
        for row in self.china["territories"]:
            owner = row["owner_id"]
            faction = factions[owner]
            group = "eight_warlords" if owner.startswith("warlord_") else owner
            by_group[group] += sum(unit["count"] for unit in row["units"])
            self.assertEqual(row["controller_id"], faction["controller_id"])
            self.assertEqual(row["alliance_id"], faction["alliance_id"])
            if self.nodes[row["node_id"]]["type"] == "land":
                self.assertEqual(self.nodes[row["node_id"]]["original_owner"], faction["map_owner_alias"])
        self.assertEqual(dict(by_group), {"kmt": 12, "ccp": 5, "eight_warlords": 32, "mongolia": 2, "fec": 4})
        self.assertEqual(dict(by_group), self.china["audit_totals"]["units_by_group"])
        warlords = [f for f in factions.values() if f["id"].startswith("warlord_")]
        self.assertEqual(len(warlords), 8)
        for faction in warlords:
            self.assertIsNone(faction["controller_id"])
            self.assertIsNone(faction["alliance_id"])
        self.assertEqual(sum(counts.values()) + sum(unit_counts(self.japan["placements"]).values()), 103)
        self.assertEqual(self.contract["inventory"]["deployed_units"], 103)

    def test_facility_references_cover_map_once_without_adding_duplicate_pieces(self):
        expected = map_facilities(self.nodes)
        references = []
        for row in self.japan["map_facility_references"]:
            for facility_id in row["facility_ids"]:
                self.assertEqual(expected[facility_id][0], row["node_id"])
                references.append(facility_id)
        for row in self.china["territories"]:
            for facility in row["facilities"]:
                self.assertEqual(expected[facility["facility_id"]], (row["node_id"], facility["type"]))
                references.append(facility["facility_id"])
        self.assertEqual(len(references), len(set(references)))
        self.assertEqual(set(references), set(expected))
        self.assertEqual(len(references), 21)
        factories = [(row["node_id"], f["type"], f["id"]) for row in self.japan["placements"] for f in row["facilities"]]
        self.assertEqual({(node_id, kind) for node_id, kind, _ in factories}, {
            ("land_jap_tokyo", "major_factory"), ("land_jap_kyushu", "medium_factory"),
            ("land_manchuria_rehe", "minor_factory"),
        })
        self.assertEqual(len(factories), 3)
        self.assertTrue(set(f[2] for f in factories).isdisjoint(references))
        self.assertEqual(self.contract["facility_type_aliases"], {"airfield": "airbase"})

    def test_source_color_places_fec_fighter_at_sea_and_japan_formosa_fighter_on_land(self):
        rows = {row["node_id"]: row for row in self.china["territories"]}
        self.assertEqual(unit_counts([rows["land_hong_kong"]]), {"infantry": 1})
        fleet = {unit["type"]: unit for unit in rows["sea_p41"]["units"]}
        self.assertEqual(fleet["fighter"]["embarked_on"], fleet["light_carrier"]["instance_id"])
        self.assertEqual(fleet["fighter"]["count"], 1)
        japan_rows = {row["node_id"]: row for row in self.japan["placements"]}
        self.assertEqual(unit_counts([japan_rows["land_formosa"]])["fighter"], 1)
        aircraft = [u for u in japan_rows["sea_p15"]["units"] if u["type"] in {"fighter", "tactical_bomber"}]
        self.assertEqual(sum(u["count"] for u in aircraft), 3)
        self.assertTrue(all(u["carrier_assignment"] is None for u in aircraft))

    def test_two_unpriced_types_are_missing_not_free_or_purchasable(self):
        missing = {entry["type"]: entry for entry in self.contract["unpriced_setup_types"]}
        self.assertEqual(set(missing), {"torpedo_boat_destroyer", "coastal_submarine"})
        all_counts = unit_counts(self.japan["placements"] + self.china["territories"])
        for kind, count in (("torpedo_boat_destroyer", 2), ("coastal_submarine", 3)):
            self.assertEqual(all_counts[kind], count)
            self.assertEqual(missing[kind]["count"], count)
            self.assertEqual(sum(missing[kind]["by_nation"].values()), count)
            self.assertIsNone(missing[kind]["valuation_ipp_per_piece"])
            self.assertFalse(missing[kind]["purchasable"])

    def test_unlocated_queue_stays_out_of_deployed_setup(self):
        queues = self.japan["starting_construction"]
        self.assertEqual({q["type"] for q in queues}, {"heavy_cruiser", "fleet_carrier"})
        self.assertEqual(len(queues), 2)
        for queued in queues:
            self.assertIsNone(queued["node_id"])
            self.assertIsNone(queued["paid_construction_value"])
            self.assertFalse(queued["included_in_deployed_totals"])
            self.assertEqual(queued["theatre_inclusion"], "unresolved_no_location_on_chart")
        annotation = self.japan["unresolved_setup_annotations"][0]
        self.assertEqual(annotation["id"], "japan_light_carrier_queue_annotations")
        self.assertIsNone(annotation["interpreted_count"])
        self.assertFalse(annotation["included_in_deployed_totals"])

    def test_starting_cash_derives_from_retained_direct_possessions(self):
        accounts = self.contract["starting_accounts"]
        actual = {}
        for account in accounts["national_accounts"]:
            retained = sum(node.get("ipp_value", 0) for node in self.nodes.values()
                           if node["type"] == "land" and node["original_owner"] == account["map_owner"])
            self.assertEqual(retained, account["retained_direct_land_ipp"])
            self.assertEqual(account["treasury_ipp"], min(account["official_starting_ipp"], retained))
            actual[account["nation"]] = account["treasury_ipp"]
        self.assertEqual(actual, {"japan": 15, "kmt": 6, "ccp": 2, "fec": 2})
        self.assertEqual(actual, self.manifest["m0_specification"]["starting_treasury_ipp"])
        for key in ("controlled_minor_treasury_ipp", "unaligned_minor_treasury_ipp", "local_ussr_initial_treasury_ipp"):
            self.assertEqual(accounts[key], 0)
        self.assertFalse(self.contract["politics"]["mongolia"]["collects_income"])

    def test_calendar_agent_turns_and_wealth_contract_stay_distinct(self):
        self.assertEqual(self.contract["agents"], self.manifest["agents"])
        self.assertEqual([x["slot"] for x in self.contract["national_turn_order"]],
                         ["ccp", "ussr", "japan", "british_commonwealth", "kmt"])
        self.assertEqual([x["agent"] for x in self.contract["national_turn_order"]],
                         ["comintern", "comintern", "axis", "allies", "allies"])
        for key in ("start", "end", "calendar_rounds"):
            self.assertEqual(self.contract["calendar"][key], self.manifest["campaign"][key])
        wealth = self.contract["wealth"]
        self.assertEqual(wealth["weights"], self.manifest["wealth_objective"]["component_weights"])
        self.assertEqual(wealth["minor_attribution_authority"], "user_confirmed")
        self.assertIsNone(wealth["minimum_surviving_asset_value"])
        rules = {r["rule"]: r["status"] for r in self.contract["rule_reachability"]}
        self.assertEqual(rules["ccp_plus_two_soviet_income_bonus"], "inactive")
        self.assertEqual(rules["ccp_comintern_brothers_artillery_aaa_purchase"], "conditional")
        self.assertEqual(rules["japan_surprise_attack_and_allies_major_war_triggers"], "conditional")


if __name__ == "__main__":
    unittest.main()
