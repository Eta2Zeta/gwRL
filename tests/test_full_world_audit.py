"""Independent examples from the world-map source audit.

These assertions use concrete board/glossary conclusions, not the authoring
operations or their implementation. They protect the uncertain-item boundary as
well as the corrections that originally prompted the naval re-audit.
"""

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
NAVAL_TYPES = {
    "minor_port", "major_port", "minor_dockyard", "major_dockyard",
    "minor_shipyard", "major_shipyard", "seaplane_base", "submarine_base",
}


class FullWorldAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(
            (ROOT / "game_content/maps/gw36_manual_map.json").read_text()
        )
        cls.nodes = cls.document["nodes"]
        cls.edges = {
            (source, edge["neighbor_id"]): edge
            for source, node in cls.nodes.items()
            for edge in node["neighbors"]
        }

    def edge(self, source, target):
        self.assertIn((source, target), self.edges)
        return self.edges[source, target]

    def naval_facilities(self, land_id):
        return {
            facility_id: (facility["type"], tuple(sorted(facility["sea_accesses"])))
            for facility_id, facility in self.document["facilities"].items()
            if facility["land_id"] == land_id and facility["type"] in NAVAL_TYPES
        }

    def test_complete_printed_sea_roster_and_land_identity_split(self):
        # The board has A1–A54, I1–I14, M1–M12 and P1–P78. The 79
        # missing land identities replace the one artificial Hispaniola node.
        expected_seas = {
            f"sea_{region}{number}"
            for region, count in (("a", 54), ("i", 14), ("m", 12), ("p", 78))
            for number in range(1, count + 1)
        }
        actual_seas = {
            node_id for node_id, node in self.nodes.items() if node["type"] == "sea"
        }
        self.assertEqual(actual_seas, expected_seas)
        self.assertEqual(len(actual_seas), 158)
        self.assertEqual(sum(node["type"] == "land" for node in self.nodes.values()), 381)
        self.assertNotIn("land_hispaniola", self.nodes)
        self.assertNotIn("land_gbr_shetland_islands", self.nodes)
        self.assertIn("land_shetland_islands", self.nodes)
        for node_id in ("land_haiti", "land_dominican_republic"):
            with self.subTest(node=node_id):
                self.assertEqual(self.nodes[node_id]["ipp_value"], 0)
                self.assertEqual(self.nodes[node_id]["terrain"], "mountain")
                self.assertEqual(self.naval_facilities(node_id), {})
        self.edge("land_haiti", "land_dominican_republic")
        self.edge("land_dominican_republic", "land_haiti")

    def test_egypt_has_three_distinct_printed_facilities(self):
        # EA-328–331: Alexandria-side dockyard and Red Sea port are separate
        # Lower Egypt symbols, while Western Egypt has its own major port.
        self.assertEqual(self.naval_facilities("land_western_egypt"), {
            "facility_western_egypt_major_port": ("major_port", ("sea_m8",)),
        })
        self.assertEqual(self.naval_facilities("land_lower_egypt"), {
            "facility_lower_egypt_major_dockyard": ("major_dockyard", ("sea_m8",)),
            "facility_lower_egypt_major_port": ("major_port", ("sea_i5",)),
        })
        self.assertEqual(self.naval_facilities("land_upper_egypt"), {})
        self.assertNotIn("facility_egypt_minor_port", self.document["facilities"])

    def test_empty_coastlines_do_not_acquire_phantom_ports(self):
        for land_id in (
            "land_french_morocco", "land_southwest_africa", "land_angola",
            "land_fra_corsica", "land_ita_sardinia", "land_bermuda",
            "land_suriname", "land_brazil_pampas",
        ):
            with self.subTest(land=land_id):
                self.assertEqual(self.naval_facilities(land_id), {})
                for edge in self.nodes[land_id]["neighbors"]:
                    if edge["neighbor_id"].startswith("sea_"):
                        self.assertEqual(edge["naval_facilities"], [])
                        self.assertEqual(edge["naval_facility_ids"], [])
        self.assertEqual(
            set(self.naval_facilities("land_south_africa").values()),
            {("major_port", ("sea_i1",))},
        )

    def test_uncertain_cape_town_facility_is_not_a_usable_claim(self):
        # The board's dockyard glyph and rulebook's minor-port example disagree.
        self.assertEqual(self.naval_facilities("land_cape_town"), {})
        for edge in self.nodes["land_cape_town"]["neighbors"]:
            if edge["neighbor_id"].startswith("sea_"):
                with self.subTest(sea=edge["neighbor_id"]):
                    self.assertEqual(edge["naval_facilities"], [])
                    self.assertEqual(edge["naval_facility_ids"], [])

    def test_facility_access_is_independent_of_other_coasts(self):
        # Iceland touches A3 and A4, but its anchor lies only on the A3 shore.
        self.edge("land_iceland", "sea_a3")
        self.edge("land_iceland", "sea_a4")
        self.assertEqual(
            set(self.naval_facilities("land_iceland").values()),
            {("minor_port", ("sea_a3",))},
        )
        self.assertEqual(self.edge("land_iceland", "sea_a4")["naval_facilities"], [])
        # Scotland's north port spans a sea divider; its two shipyards are
        # physically separate despite sharing a facility type.
        scotland = list(self.naval_facilities("land_gbr_scotland").values())
        self.assertCountEqual(scotland, [
            ("major_port", ("sea_a4", "sea_a6")),
            ("major_shipyard", ("sea_a4",)),
            ("major_shipyard", ("sea_a6",)),
        ])

    def test_false_shortcuts_are_removed(self):
        for source, target in (
            ("land_ger_eastern_germany", "land_ger_konigsberg"),
            ("land_pol_west_poland", "land_cze_bohemia"),
            ("land_pol_warsaw", "land_pol_podlachia"),
            ("land_tunisia", "land_tripoli"),
            ("land_usa_chicago", "land_usa_new_york"),
            ("sea_m11", "sea_m12"),
            ("sea_a36", "sea_p31"),
        ):
            with self.subTest(pair=(source, target)):
                self.assertNotIn((source, target), self.edges)
                self.assertNotIn((target, source), self.edges)

    def test_confirmed_new_borders_and_rail_crossings(self):
        for source, target in (
            ("land_denmark", "land_ger_western_germany"),
            ("land_gbr_northern_ireland", "land_ireland"),
            ("land_nor_northern_norway", "land_swe_norrland"),
            ("land_usa_great_lakes", "land_usa_washington_dc"),
        ):
            with self.subTest(pair=(source, target)):
                self.assertIs(self.edge(source, target)["railway_connection"], True)
                self.assertIs(self.edge(target, source)["railway_connection"], True)
        self.assertEqual(
            self.edge("sea_a40", "sea_p76")["canal_or_strait"], "Panama Canal"
        )

    def test_directed_combat_attributes_are_not_mirrored(self):
        # The adopted Abyssinia approach has additional mountain terrain only
        # when attacking inland; leaving the zone has desert terrain alone.
        self.assertEqual(
            set(self.edge("land_french_somaliland", "land_abyssinia")["border_terrain"]),
            {"desert", "mountain"},
        )
        self.assertEqual(
            self.edge("land_abyssinia", "land_french_somaliland")["border_terrain"],
            "desert",
        )
        self.assertEqual(
            set(self.edge("land_yemen", "land_aden")["border_terrain"]),
            {"desert", "mountain"},
        )
        self.assertIs(self.edge("sea_m3", "land_ita_rome")["river_crossing"], True)
        # The glossary establishes only the incoming combat penalty. It must
        # not create an outgoing penalty by mechanically mirroring the edge.
        self.assertIsNot(self.edge("land_ita_rome", "sea_m3")["river_crossing"], True)

    def test_unreviewed_new_rail_fields_are_explicitly_unknown(self):
        for source, target in (
            ("land_gre_peloponnese", "land_gre_thessaly"),
            ("land_ivory_coast", "land_french_sudan"),
        ):
            with self.subTest(pair=(source, target)):
                self.assertIsNone(self.edge(source, target)["railway_connection"])
                self.assertIsNone(self.edge(target, source)["railway_connection"])
        # Two point-contact candidates were never confirmed as physical edges.
        for source, target in (
            ("land_rio_de_oro", "land_western_algeria"),
            ("land_mauritania", "land_french_morocco"),
        ):
            with self.subTest(unconfirmed_pair=(source, target)):
                self.assertNotIn((source, target), self.edges)
                self.assertNotIn((target, source), self.edges)

    def test_existing_uncertain_physical_pairs_remain_for_user_review(self):
        # These seven pairs existed at the checkpoint. Their existence is
        # deliberately preserved; that does not certify their other attributes.
        for source, target in (
            ("land_can_alberta_saskatchewan", "land_can_manitoba"),
            ("land_can_district_of_keewatin", "land_can_district_of_mackenzie"),
            ("land_mongolia_kobdo", "land_usr_novosibirsk"),
            ("land_pol_lubelskie", "land_usr_western_ukraine"),
            ("land_usa_great_plains", "land_usa_texas"),
            ("land_usa_midwest", "land_usa_upper_midwest"),
            ("sea_p42", "sea_p50"),
        ):
            with self.subTest(pair=(source, target)):
                self.edge(source, target)
                self.edge(target, source)


if __name__ == "__main__":
    unittest.main()
