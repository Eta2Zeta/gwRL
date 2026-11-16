"""The numbers docs/engine/names.md lists for each kind of name are the ones the engine builds."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from print_name_tables import SCENARIO, kind_table, tables  # noqa: E402


class NameTablesTest(unittest.TestCase):
    def test_the_page_lists_the_engines_numbers(self):
        page = (ROOT / "docs/engine/names.md").read_text(encoding="utf-8")
        found = tables(SCENARIO)
        self.assertEqual(sorted(found), ["marks", "nations", "unit_classes", "unit_types", "zones"],
                         "The engine numbers other kinds of name")
        for kind, names in found.items():
            with self.subTest(kind=kind):
                self.assertEqual(names, sorted(names), f"{kind.capitalize()} numbers do not follow the names' sorted order")
                self.assertIn(kind_table(kind, names), page,
                              f"docs/engine/names.md lists other {kind} numbers than the engine: "
                              f"print them with tools/print_name_tables.py --kind {kind}")


if __name__ == "__main__":
    unittest.main()
