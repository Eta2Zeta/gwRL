#!/usr/bin/env python3
"""Print the tables that number the scenario's names.

Inside the engine a zone, a nation, a unit type, a unit class or the base of a
mark is held as a number, not as its name: its place in the sorted list of the
names of that kind, counted from 0, the definition's for zones and nations, the
catalog's for unit types and classes, and the engine's mark table for marks
(include/game/names.hpp, include/game/marks.hpp and docs/engine/names.md). Saved positions, actions and
the Python interface keep the names. This prints each kind's table, number and
name, as Markdown, for the scenario the training plays, or for another scenario
folder:

    .venv/bin/python tools/print_name_tables.py
    .venv/bin/python tools/print_name_tables.py --kind nations --scenario game_content/scenarios/japan_china_1936
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gwrl_cpp  # noqa: E402

SCENARIO = ROOT / "game_content/scenarios/japan_china_1936"


def tables(scenario: Path) -> dict[str, list[str]]:
    """Each kind of name with its names in number order."""
    return gwrl_cpp.CampaignEnv(str(scenario)).name_tables()


def table(names: list[str], arguments: list[str] | None = None) -> str:
    """One kind's table as Markdown: each number with its name, and for marks what
    each one's argument names (a dash for a mark without one)."""
    if arguments is None:
        lines = ["| Number | Name |", "| ---: | --- |"]
        lines += [f"| {number} | `{name}` |" for number, name in enumerate(names)]
    else:
        lines = ["| Number | Name | Argument |", "| ---: | --- | --- |"]
        lines += [f"| {number} | `{name}` | {argument or '—'} |"
                  for number, (name, argument) in enumerate(zip(names, arguments, strict=True))]
    return "\n".join(lines)


def kind_table(kind: str, names: list[str]) -> str:
    """A kind's table; the mark table also says what each argument names."""
    return table(names, gwrl_cpp.mark_arguments() if kind == "marks" else None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scenario", type=Path, default=SCENARIO, help="Scenario folder (default: the training scenario)")
    parser.add_argument("--kind", help="Print only this kind of name: zones, nations, unit_types, unit_classes or marks")
    args = parser.parse_args(argv)
    found = tables(args.scenario)
    kinds = [args.kind] if args.kind else sorted(found)
    unknown = [kind for kind in kinds if kind not in found]
    if unknown:
        parser.error(f"no table of {', '.join(unknown)}; the tables are {', '.join(sorted(found))}")
    print("\n\n".join(f"## {kind.replace('_', ' ').capitalize()} ({len(found[kind])})\n\n{kind_table(kind, found[kind])}"
                      for kind in kinds))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
