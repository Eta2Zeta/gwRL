"""The zone numbers docs/engine/names.md lists are the ones the engine builds."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from print_name_tables import SCENARIO, table, tables  # noqa: E402


class NameTablesTest(unittest.TestCase):
    def test_the_page_lists_the_engines_zone_numbers(self):
        page = (ROOT / "docs/engine/names.md").read_text(encoding="utf-8")
        zones = tables(SCENARIO)["zones"]
        self.assertEqual(zones, sorted(zones), "Zone numbers do not follow the names' sorted order")
        self.assertIn(table(zones), page,
                      "docs/engine/names.md lists other zone numbers than the engine: "
                      "print them with tools/print_name_tables.py --kind zones")


if __name__ == "__main__":
    unittest.main()
