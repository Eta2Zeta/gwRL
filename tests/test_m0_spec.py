"""Approved scenario transcription/contract checks, separate from runtime rules."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unittest

from tools.check_documentation import resolve_legacy_document


ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "game_content/scenarios/japan_china_1936"
IGNORED_IMAGE_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff",
    ".svg", ".heic", ".avif",
}


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
        cls.catalog_sources = read_json(SCENARIO / "m0/catalog_source_checks.json")
        cls.map = read_json(SCENARIO / "map.json")
        cls.nodes = cls.map["nodes"]

    def test_settled_specification_remains_distinct_from_a_playable_game(self):
        self.assertIn(self.contract["status"], {
            "synchronized_pending_verification_not_playable", "m0_frozen_specification_not_playable",
        })
        for document in (self.japan, self.china):
            self.assertIn(document["status"], {
                "synchronized_pending_verification_not_playable", "frozen_specification_not_playable",
            })
        self.assertEqual(self.manifest["m0_specification"]["contract"], "m0/scenario_contract.json")
        self.assertEqual(self.contract["pending_decisions"], [])
        self.assertEqual(self.contract["decision_review"]["status"], "complete")
        for filename in self.contract["setup_files"]:
            self.assertTrue((SCENARIO / "m0" / filename).is_file())

    def test_core_ledger_has_unique_traceable_fixture_ids(self):
        ledger = (ROOT / "docs/reference/rules-ledger.md").read_text()
        rows = re.findall(r"^\| (R\d{3}); (.+)$", ledger, flags=re.MULTILINE)
        fixture_ids = [row[0] for row in rows]
        self.assertTrue(fixture_ids)
        self.assertEqual(len(fixture_ids), len(set(fixture_ids)))
        for fixture_id, cells in rows:
            self.assertIn("RB", cells, fixture_id)
            self.assertEqual(len(cells.split("|")), 7, fixture_id)

    def test_source_hashes_match_current_local_sources(self):
        seen = {}
        for document in (self.japan, self.china, self.convoys, self.catalog_sources):
            sources = document["sources"]
            for source in (sources.values() if isinstance(sources, dict) else sources):
                path = ROOT / source["path"]
                self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")
                # The user deliberately git-ignored source images. Retain
                # their recorded hashes and verify them whenever present.
                if path.exists() or path.suffix.lower() not in IGNORED_IMAGE_SUFFIXES:
                    self.assertTrue(path.is_file(), path)
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), source["sha256"], path)
                if path in seen:
                    self.assertEqual(source["sha256"], seen[path])
                seen[path] = source["sha256"]
        self.assertIn(ROOT / self.japan["sources"]["rulebook"]["path"], seen)
        self.assertIn(ROOT / self.japan["sources"]["global_map"]["path"], seen)

    def test_reference_convoy_route_does_not_enable_campaign_convoys(self):
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
        self.assertTrue(self.convoys["rules"]["no_income_creation"])
        self.assertIn("convoy_lines", self.manifest["excluded_feature_layers"])
        self.assertEqual(self.map["convoy_lines"], [])
        self.assertEqual(self.convoys["status"], "reference_only_excluded_from_campaign")
        self.assertFalse(self.convoys["campaign_applicability"]["enabled"])
        japan_cash = next(x for x in self.contract["starting_accounts"]["national_accounts"] if x["nation"] == "japan")
        self.assertEqual(japan_cash["treasury_ipp"], 15)

    def test_cut_tokyo_convoy_is_not_stitched_across_missing_seas(self):
        lines = {line["id"]: line for line in self.convoys["audited_lines"]}
        line = lines["convoy_japan_tokyo"]
        self.assertEqual(line["ordered_sea_zone_ids"],
                         ["sea_p16", "sea_p34", "sea_p33", "sea_p32", "sea_p41", "sea_p50"])
        self.assertEqual(set(line["ordered_sea_zone_ids"]) - set(self.nodes), {"sea_p34", "sea_p50"})
        self.assertEqual(line["excluded_sea_zone_ids"], ["sea_p34", "sea_p50"])
        self.assertEqual(line["theatre_classification"], "excluded_by_campaign_choice_and_cut_route")
        self.assertEqual(line["historical_audit_classification"], "excluded_cut_route_and_terminal_outside_theatre")
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
                # Identical aircraft types may be separate physical records
                # when they are assigned to different carriers.
                identities = [unit.get("instance_id", unit["type"]) for unit in row["units"]]
                self.assertEqual(len(identities), len(set(identities)))
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
        self.assertEqual(len(land_ids), 31)
        self.assertNotIn("land_mongolia_tannu_tuva", covered)
        self.assertNotIn("land_hong_kong", covered)
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
        self.assertEqual(dict(by_group), {"kmt": 12, "ccp": 5, "eight_warlords": 32, "mongolia": 2})
        self.assertEqual(dict(by_group), self.china["audit_totals"]["units_by_group"])
        warlords = [f for f in factions.values() if f["id"].startswith("warlord_")]
        self.assertEqual(len(warlords), 8)
        for faction in warlords:
            self.assertIsNone(faction["controller_id"])
            self.assertIsNone(faction["alliance_id"])
        self.assertEqual(sum(counts.values()), 51)
        self.assertEqual(sum(counts.values()) + sum(unit_counts(self.japan["placements"]).values()), 99)
        self.assertEqual(self.contract["inventory"]["deployed_units"], 99)
        self.assertNotIn("fec", factions)
        self.assertNotIn("ussr", factions)
        expected_aliases = {
            "warlord_sinkiang": "Sinkiang Clique", "warlord_tsinghai": "Ma Clique",
            "warlord_suiyuan": "Mengjiang", "warlord_beiping_hopeh": "Zhili Clique",
            "warlord_tibet": "Tibet", "warlord_sikang": "Szechwan Clique",
            "warlord_yunnan": "Yunnan Clique", "warlord_kwangtung_hainan": "Guangxi Clique",
        }
        self.assertEqual({f["id"]: f["map_owner_alias"] for f in warlords}, expected_aliases)
        mongolia = factions["mongolia"]
        self.assertEqual(mongolia["controller_id"], "comintern")
        self.assertEqual(mongolia["source_controller_id"], "ussr")
        for row in self.china["territories"]:
            if row["owner_id"] == "mongolia":
                self.assertEqual(row["controller_id"], "comintern")
                self.assertEqual(row["source_controller_id"], "ussr")

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
        self.assertEqual(len(references), 19)
        factories = [(row["node_id"], f["type"], f["id"]) for row in self.japan["placements"] for f in row["facilities"]]
        self.assertEqual({(node_id, kind) for node_id, kind, _ in factories}, {
            ("land_jap_tokyo", "major_factory"), ("land_jap_kyushu", "medium_factory"),
            ("land_manchuria_rehe", "minor_factory"),
        })
        self.assertEqual(len(factories), 3)
        self.assertTrue(set(f[2] for f in factories).isdisjoint(references))
        self.assertEqual(self.contract["facility_type_aliases"], {"airfield": "airbase"})

    def test_fec_source_pieces_are_preserved_as_excluded_evidence(self):
        rows = {row["node_id"]: row for row in self.china["excluded_setup"]}
        self.assertEqual(set(rows), {"land_hong_kong", "sea_p41"})
        self.assertEqual(unit_counts([rows["land_hong_kong"]]), {"infantry": 1})
        fleet = {unit["type"]: unit for unit in rows["sea_p41"]["units"]}
        self.assertEqual(fleet["fighter"]["embarked_on"], fleet["light_carrier"]["instance_id"])
        self.assertEqual(fleet["fighter"]["count"], 1)
        for row in rows.values():
            self.assertTrue(row["source_refs"])
            self.assertTrue(row["exclusion_reason"])
        self.assertFalse(any(row["owner_id"] == "fec" for row in self.china["territories"]))
        self.assertIn("sea_p41", self.nodes)
        self.assertNotIn("land_hong_kong", self.nodes)

    def test_japan_carrier_assignments_preserve_the_three_source_aircraft(self):
        japan_rows = {row["node_id"]: row for row in self.japan["placements"]}
        self.assertEqual(unit_counts([japan_rows["land_formosa"]])["fighter"], 1)
        fleet = japan_rows["sea_p15"]["units"]
        aircraft = [u for u in fleet if u["type"] in {"fighter", "tactical_bomber"}]
        self.assertEqual(sum(u["count"] for u in aircraft), 3)
        self.assertEqual(unit_counts([japan_rows["sea_p15"]])["fighter"], 2)
        self.assertEqual(len([u for u in aircraft if u["type"] == "fighter"]), 2)
        identified = [u for u in fleet if "instance_id" in u]
        self.assertEqual(len({u["instance_id"] for u in identified}), len(identified))
        carriers = {u["type"]: u for u in fleet if u["type"] in {"fleet_carrier", "light_carrier"}}
        self.assertEqual(set(carriers), {"fleet_carrier", "light_carrier"})
        expected_assignments = {"fleet_carrier": Counter({"fighter": 1, "tactical_bomber": 1}),
                                "light_carrier": Counter({"fighter": 1})}
        for carrier_type, expected in expected_assignments.items():
            carrier = carriers[carrier_type]
            embarked = [u for u in aircraft if u["embarked_on"] == carrier["instance_id"]]
            self.assertEqual(unit_counts([{"units": embarked}]), expected)
        self.assertTrue(all(u["embarked_on"] in {c["instance_id"] for c in carriers.values()} for u in aircraft))
        for unit in fleet:
            self.assertFalse("carrier_assignment" in unit and unit["carrier_assignment"] is None)

    def test_user_values_price_setup_only_ships_without_making_them_purchasable(self):
        values = {entry["type"]: entry for entry in self.contract["setup_only_unit_values"]}
        japan_values = {entry["type"]: entry for entry in self.japan["setup_only_asset_values"]}
        self.assertEqual(set(values), {"torpedo_boat_destroyer", "coastal_submarine"})
        self.assertEqual(set(values), set(japan_values))
        all_counts = unit_counts(self.japan["placements"] + self.china["territories"])
        for kind, count, price in (("torpedo_boat_destroyer", 2, 5), ("coastal_submarine", 2, 4)):
            self.assertEqual(all_counts[kind], count)
            for collection in (values, japan_values):
                count_key = "count" if collection is values else "retained_count"
                self.assertEqual(collection[kind][count_key], count)
                self.assertEqual(collection[kind]["valuation_ipp_per_piece"], price)
                self.assertFalse(collection[kind]["purchasable"])
            self.assertEqual(values[kind]["by_nation"], {"japan": count})

    def test_retained_national_queues_conserve_paid_and_remaining_cost_without_deployment(self):
        queues = self.japan["starting_construction"]
        self.assertEqual({q["type"] for q in queues}, {"heavy_cruiser", "fleet_carrier"})
        self.assertEqual(len(queues), 2)
        self.assertEqual(len({q["id"] for q in queues}), len(queues))
        expected = {"heavy_cruiser": ([5, 5], [5]), "fleet_carrier": ([5, 5, 5], [5, 5])}
        for queued in queues:
            self.assertIsNone(queued["node_id"])
            self.assertEqual(queued["count"], 1)
            self.assertEqual(queued["paid_construction_value"], 5)
            self.assertFalse(queued["included_in_deployed_totals"])
            self.assertEqual(queued["theatre_inclusion"], "included_national_queue_user_approved")
            costs, remaining = expected[queued["type"]]
            self.assertEqual(queued["stage_costs_ipp"], costs)
            self.assertEqual(queued["remaining_stage_payments_ipp"], remaining)
            self.assertEqual(queued["paid_construction_value"] + sum(remaining), queued["total_base_purchase_price"])
            self.assertEqual(sum(costs), queued["total_base_purchase_price"])
            self.assertEqual(queued["remaining_cost_ipp"], sum(remaining))
            self.assertEqual(queued["paid_stages"], 1)
            self.assertEqual(queued["queue_stage"], len(costs))
            self.assertEqual(queued["opening_treasury_debit_ipp"], 0)
            self.assertTrue(queued["source"])
        self.assertEqual(sum(q["paid_construction_value"] for q in queues), 10)
        self.assertEqual(self.japan["unresolved_setup_annotations"], [])
        resolved = self.japan["resolved_setup_annotations"]
        self.assertTrue(resolved)
        self.assertTrue(any(annotation["id"] == "japan_light_carrier_queue_annotations" for annotation in resolved))

    def test_starting_cash_derives_from_retained_direct_possessions(self):
        accounts = self.contract["starting_accounts"]
        actual = {}
        for account in accounts["national_accounts"]:
            retained = sum(node.get("ipp_value", 0) for node in self.nodes.values()
                           if node["type"] == "land" and node["original_owner"] == account["map_owner"])
            self.assertEqual(retained, account["retained_direct_land_ipp"])
            self.assertEqual(account["treasury_ipp"], min(account["official_starting_ipp"], retained))
            actual[account["nation"]] = account["treasury_ipp"]
        self.assertEqual(actual, {"japan": 15, "kmt": 6, "ccp": 2})
        self.assertEqual(actual, self.manifest["m0_specification"]["starting_treasury_ipp"])
        for key in ("controlled_minor_treasury_ipp", "unaligned_minor_treasury_ipp"):
            self.assertEqual(accounts[key], 0)
        self.assertNotIn("local_ussr_initial_treasury_ipp", accounts)
        self.assertFalse(self.contract["politics"]["mongolia"]["collects_income"])

    def test_calendar_agent_turns_and_wealth_contract_stay_distinct(self):
        self.assertEqual(self.contract["agents"], self.manifest["agents"])
        self.assertEqual([x["slot"] for x in self.contract["national_turn_order"]],
                         ["ccp", "mongolia", "japan", "kmt"])
        self.assertEqual([x["agent"] for x in self.contract["national_turn_order"]],
                         ["comintern", "comintern", "axis", "allies"])
        self.assertEqual([x["slot"] for x in self.contract["national_turn_order"]], self.manifest["campaign"]["national_turn_order"])
        for key in ("start", "end", "calendar_rounds"):
            self.assertEqual(self.contract["calendar"][key], self.manifest["campaign"][key])
        wealth = self.contract["wealth"]
        self.assertEqual(wealth["weights"], self.manifest["wealth_objective"]["component_weights"])
        self.assertEqual(wealth["minor_attribution_authority"], "user_confirmed")
        self.assertIsNone(wealth["minimum_surviving_asset_value"])
        self.assertEqual(wealth["completed_price_basis"]["value"], "undiscounted_catalog_price")
        self.assertEqual(wealth["standalone_city_asset_value"]["value_ipp"], 0)
        self.assertEqual(wealth["cross_owner_rail_attribution"]["status"], "user_confirmed")
        self.assertEqual(self.contract["calendar"]["terminal_timing"], "after_complete_july_1941_round")
        self.assertEqual(self.contract["calendar"]["early_terminal_rule"], "none_selected")
        rules = {r["rule"]: r["status"] for r in self.contract["rule_reachability"]}
        self.assertEqual(rules["ccp_plus_two_soviet_income_bonus"], "inactive")
        self.assertEqual(rules["ccp_comintern_brothers_artillery_aaa_purchase"], "inactive")
        self.assertEqual(rules["japan_surprise_attack_and_allies_major_war_triggers"], "conditional")

    def test_active_campaign_profile_has_no_external_participants_or_disabled_mechanics(self):
        self.assertEqual(self.contract["boundary"]["selected_node_count"], len(self.nodes))
        self.assertEqual(len(self.nodes), 37)
        self.assertNotIn("land_hong_kong", self.nodes)
        self.assertIn("sea_p41", self.nodes)
        self.assertEqual(self.map["convoy_lines"], [])
        accounts = {account["nation"] for account in self.contract["starting_accounts"]["national_accounts"]}
        self.assertEqual(accounts, {"japan", "kmt", "ccp"})
        mechanics = self.contract["mechanics"]
        enabled, disabled = set(mechanics["enabled"]), set(mechanics["disabled"])
        self.assertFalse(enabled & disabled)
        self.assertTrue({"convoys", "convoy_raiding", "interdiction", "kido_butai", "usa_triggered_light_carriers"} <= disabled)
        self.assertTrue({"blockades", "maritime_air_patrol", "ccp_major_power_evolution", "kmt_major_power_evolution"} <= enabled)
        self.assertTrue(set(self.manifest["campaign_mechanics"]["retained"]) <= enabled)
        self.assertTrue({"convoys", "interdiction", "kido_butai"} <= set(self.manifest["campaign_mechanics"]["excluded"]))
        mongolia = self.contract["politics"]["mongolia"]
        self.assertEqual(mongolia["controller"], "comintern")
        self.assertEqual(mongolia["national_identity"], "mongolia")
        self.assertEqual(mongolia["turn_slot"], "mongolia")
        self.assertEqual(mongolia["source_turn_slot"], "ussr")
        self.assertFalse(mongolia["incorporated_into_ussr"])
        self.assertFalse(mongolia["soviet_alignment_enabled"])

    def test_catalog_source_checks_trace_queue_values_without_claiming_runtime_implementation(self):
        checks = self.catalog_sources
        self.assertEqual(checks["status"], "source_reconciliation_only_not_executable_catalog")
        # Frozen source data retains its historical review path; the archive
        # manifest locates the byte-preserved document without rewriting it.
        self.assertTrue(resolve_legacy_document(ROOT, checks["review_document"]).is_file())
        source_ids = {source["id"] for source in checks["sources"]}
        self.assertEqual(len(source_ids), len(checks["sources"]))
        queues = {row["type"]: row for row in self.japan["starting_construction"]}
        source_queues = checks["japan_starting_queues"]
        self.assertEqual({row["type"] for row in source_queues}, set(queues))
        for row in source_queues:
            queue = queues[row["type"]]
            self.assertEqual(row["starting_queue_position"], queue["queue_stage"])
            self.assertEqual(row["stage_payments_ipp"], queue["stage_costs_ipp"])
            self.assertEqual(row["cumulative_paid_ipp"], queue["paid_construction_value"])
            self.assertEqual(row["remaining_normal_payments_ipp"], queue["remaining_stage_payments_ipp"])
            self.assertFalse(row["deduct_from_opening_treasury"])
            self.assertTrue(row["source_refs"])
            for source in row["source_refs"]:
                self.assertIn(source["source_id"], source_ids)
        self.assertEqual(checks["opening_queue_asset_total_ipp"], sum(row["paid_construction_value"] for row in queues.values()))
        self.assertEqual(checks["opening_queue_axis_wealth_contribution"], checks["opening_queue_asset_total_ipp"] * self.contract["wealth"]["weights"]["paid_construction_value"])
        research = checks["research_chart"]
        technologies = [row["technology_id"] for row in research["rows"]]
        self.assertTrue(technologies)
        self.assertEqual(len(technologies), len(set(technologies)))
        for row in research["rows"]:
            thresholds = row["minimum_success_roll_by_destination"]
            self.assertEqual(set(thresholds), set(research["destination_columns"]))
            self.assertTrue(all(type(value) is int and 1 <= value <= research["die_sides"] for value in thresholds.values()))
        for gate in checks["later_implementation_gates"]:
            self.assertFalse(gate["blocks_m0_source_reconciliation"])


if __name__ == "__main__":
    unittest.main()
