#!/usr/bin/env python3
"""List every place the engine's source gives a mark a value, and the kind of thing it lands on.

A mark (include/game/marks.hpp) is held on one of seven kinds of thing: a unit,
a nation, a territory, a facility, a construction project, a battle or the
game as a whole (the state). The engine's mark table says, for each mark, the
kinds it can be on, and the network's input asks about a mark only there
(docs/design/network_input.md, section 8). This reads the rule code for the
statements that give a mark a value and works out, from the declaration of the
thing written to, which kind it is:

    u.turnFlags[mark::scrambled] = 1;                    a unit (UnitState& u)
    ++s.nations.at(n).turnFlags[mark::purchased];        a nation
    b.flags[MarkKey(mark::air_battle, id)] = 1;          a battle (BattleState& b)
    auto& ledger = s.nations.at(x).turnFlags; ledger[key] = v;   a nation, through another name

A write it cannot attribute is listed as unresolved, never guessed.
tests/test_campaign_zone_encoding.py checks every write against the mark table.

    ./.venv/bin/python tools/mark_writes.py             # one line per mark: the kinds it is written on
    ./.venv/bin/python tools/mark_writes.py --sites     # every write, with its file and line
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KINDS = ("unit", "nation", "territory", "facility", "project", "battle", "game")
# Which kinds hold each container of marks (include/game/campaign.hpp).
HOLDERS = {"turnFlags": {"unit", "nation"}, "gameFlags": {"unit", "nation"}, "commitments": {"unit"},
           "flags": {"territory", "facility", "project", "battle", "game"}}
# The engine's collections and types, and the kind each holds.
COLLECTIONS = {"units": "unit", "nations": "nation", "territories": "territory", "facilities": "facility",
               "construction": "project", "battles": "battle"}
TYPES = {"CatalogContext": "catalog", "UnitState": "unit", "NationState": "nation", "TerritoryState": "territory", "FacilityState": "facility",
         "BuildProject": "project", "BattleState": "battle", "State": "game"}
# Files that only read or copy whole sets of marks: the encoder, the bindings, and
# saving and loading positions, which give back the marks a saved position held.
SKIP = {"zone_encoding.cpp", "python_bindings.cpp", "campaign_state.cpp"}
ACCESS = re.compile(r"(\.|->)\s*(turnFlags|gameFlags|flags|commitments)\b")
MARK = re.compile(r"\bmark::([a-z_0-9]+)\b")
IDENT = re.compile(r"[A-Za-z_]\w*")


@dataclass(frozen=True)
class Write:
    mark: str
    kind: str | None  # None: unresolved
    file: str
    line: int
    receiver: str
    why: str


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def blank_strings(text: str) -> str:
    """Strings replaced by spaces of the same length, so brackets in them do not count."""
    return re.sub(r'"(?:\\.|[^"\\])*"', lambda m: '"' + " " * (len(m.group(0)) - 2) + '"', text)


def matching(text: str, at: int, step: int) -> int:
    """The index of the bracket matching the one at `at`, searching forward (+1) or back (-1)."""
    pairs = {"(": ")", "[": "]", "{": "}", ")": "(", "]": "[", "}": "{"}
    mine, other, depth = text[at], pairs[text[at]], 0
    i = at
    while 0 <= i < len(text):
        if text[i] == mine:
            depth += 1
        elif text[i] == other:
            depth -= 1
            if depth == 0:
                return i
        i += step
    return -1


def receiver_before(text: str, at: int) -> tuple[str, int]:
    """The expression ending just before `at` (a '.' or '->'): its text and start."""
    i = at - 1
    while i >= 0 and text[i].isspace():
        i -= 1
    end = i + 1
    while i >= 0:
        if text[i] in ")]":
            i = matching(text, i, -1) - 1
            continue
        if text[i].isalnum() or text[i] == "_":
            while i >= 0 and (text[i].isalnum() or text[i] == "_"):
                i -= 1
            j = i
            while j >= 0 and text[j].isspace():
                j -= 1
            if j >= 0 and text[j] == "." :
                i = j - 1
                continue
            if j >= 1 and text[j - 1:j + 1] == "->":
                i = j - 2
                continue
            if j >= 1 and text[j - 1:j + 1] == "::":
                i = j - 2
                continue
            break
        if text[i] == "*":  # (*it).flags
            i -= 1
            continue
        break
    return text[i + 1:end].strip(), i + 1


def chain(expression: str) -> str:
    """The expression with every bracketed group emptied: s.nations.at(x) -> s.nations.at()."""
    out, i = [], 0
    while i < len(expression):
        if expression[i] in "([":
            j = matching(expression, i, 1)
            out.append(expression[i] + expression[j])
            i = j + 1
        else:
            out.append(expression[i])
            i += 1
    return "".join(out)


def function_start(text: str, at: int) -> int:
    """The start of the function body containing `at`: the last '{' at depth zero before it."""
    depth, i, start = 0, 0, 0
    # Walk forward once, tracking top-level braces; cheap enough for these files.
    for match in re.finditer(r"[{}]", text[:at]):
        if match.group(0) == "{":
            if depth == 0:
                start = match.start()
            depth += 1
        else:
            depth -= 1
    # Include the signature: back to the previous ';' or '}' at depth zero.
    head = max(text.rfind(";", 0, start), text.rfind("}", 0, start))
    return head + 1


def kind_of_type(text: str) -> str | None:
    names = IDENT.findall(text)
    for name in names:
        if name in TYPES and not (name == "State" and len([n for n in names if n in TYPES]) > 1):
            return TYPES[name]
    return None


class Resolver:
    def __init__(self, text: str):
        self.text = text

    def kind(self, expression: str, at: int, depth: int = 0) -> tuple[str | None, str]:
        """The kind of thing `expression` (written at `at`) is, and why."""
        if depth > 6:
            return None, "too deep"
        flat = chain(expression)
        if re.search(r"\bcatalogContext\(", flat):
            return "catalog", "a catalog context"
        found = [name for name in re.findall(r"\b(\w+)\b", flat) if name in COLLECTIONS]
        if found:
            return COLLECTIONS[found[-1]], f"from {found[-1]}"
        names = IDENT.findall(flat)
        if not names:
            return None, f"no name in {expression}"
        if names[-1] == "state_":
            return "game", "the state"
        if re.fullmatch(r"\w+(\.|->)(second|first)", flat) or re.fullmatch(r"\*\w+", flat):
            return self.kind_of_name(names[0], at, depth, element=True)
        if len(names) == 1:
            return self.kind_of_name(names[0], at, depth)
        if names[-1] == "state_":
            return "game", "the state"
        return None, f"cannot read {expression}"

    def kind_of_name(self, name: str, at: int, depth: int, element: bool = False) -> tuple[str | None, str]:
        start = function_start(self.text, at)
        body = self.text[start:at]
        candidates = []
        patterns = [
            (rf"(?:^|[(,;{{}}])\s*(?:const\s+)?(?!auto\b)([\w:<>]+)\s*(?:&(?!&)|\*)\s*{name}\b(?!\s*\()", "type"),  # Type& name
            (rf"\bauto\s*[&*]*\s*{name}\s*=\s*([^;]+);", "expr"),                     # auto& name = expr;
            (rf"\bauto\s*[&*]*\s*{name}\s*\{{([^;]+)\}};", "expr"),
            (rf"\[\s*[\w&]*\s*,\s*{name}\s*\]\s*:\s*([^)]+)\)", "element"),           # [id, name] : coll)
            (rf"\bfor\s*\(\s*(?:const\s+)?auto\s*[&*]*\s*{name}\s*:\s*([^)]+)\)", "element"),
            (rf"\b(?:const\s+)?([A-Z]\w*)\s+{name}\s*[;({{=]", "type"),               # Type name;
        ]
        for pattern, how in patterns:
            for match in re.finditer(pattern, body):
                candidates.append((match.start(), how, match.group(1)))
        if not candidates:
            return None, f"no declaration of {name}"
        _, how, source = max(candidates)
        if how == "type":
            kind = kind_of_type(source)
            if kind:
                return kind, f"{name} is a {source}"
            return None, f"{name} is a {source}"
        if how == "element":
            kind, why = self.kind(source.strip(), at, depth + 1)
            return kind, f"{name} from {source.strip()}: {why}"
        # An expression: auto& name = expr;
        expr = source.strip()
        if element and re.search(r"\.(find|begin|lower_bound)\(", expr):
            expr = chain(expr)
        kind, why = self.kind(expr, at, depth + 1)
        return kind, f"{name} = {expr[:60]}: {why}"


def key_marks(key: str, body: str) -> tuple[set[str], str]:
    marks = set(MARK.findall(key))
    if marks:
        return marks, "named"
    name = re.fullmatch(r"\s*([A-Za-z_]\w*)\s*", key)
    if not name:
        return set(), f"key {key.strip()[:50]}"
    name = name.group(1)
    # The nearest binding of the name before the write decides:
    #   const auto key = MarkKey(mark::x, ...), other = ...;   MarkKey key(mark::x);
    #   for (const auto &[key, v] : other.flags) if (key.base() == mark::x) ...
    bindings = []
    for match in re.finditer(rf"\b{name}\b\s*(?:=(?!=)|\(|\{{)([^;]*);", body):
        named = set(MARK.findall(re.split(rf",\s*\w+\s*=", match.group(1))[0]))
        if named:
            bindings.append((match.start(), named, f"through {name}"))
    for match in re.finditer(rf"\[\s*{name}\s*,\s*\w+\s*\]\s*:\s*([^)]+)\)", body):
        tested = set(re.findall(rf"\b{name}\.base\(\)\s*==\s*mark::(\w+)", body[match.end():]))
        bindings.append((match.start(), tested, f"copied from {match.group(1).strip()}"))
    if bindings:
        _, named, how = max(bindings, key=lambda b: b[0])
        return named, how
    return set(), f"key {name}"


def writes(root: Path = ROOT) -> list[Write]:
    out: list[Write] = []
    files = sorted((root / "src").glob("*.cpp")) + sorted((root / "include" / "game").glob("*.hpp"))
    for path in files:
        if path.name in SKIP or path.name == "marks.hpp":
            continue
        text = blank_strings(strip_comments(path.read_text()))
        resolver = Resolver(text)
        sites = []
        for access in ACCESS.finditer(text):
            receiver, start = receiver_before(text, access.start())
            container = access.group(2)
            rest = access.end()
            while rest < len(text) and text[rest].isspace():
                rest += 1
            if text.startswith("[", rest):
                close = matching(text, rest, 1)
                key = text[rest + 1:close]
                after = text[close + 1:close + 4].lstrip()
                before = text[max(0, start - 3):start]
                written = bool(re.match(r"(=(?!=)|\+=|-=|\*=|\|=|\+\+|--)", after)) or "++" in before or "--" in before
                if not written and re.search(r"&\s*\w+\s*=\s*$", text[max(0, start - 50):start]):
                    written = True  # int& slot = marks[key]; slot = ...
            elif re.match(r"\.\s*(insert|emplace|try_emplace|insert_or_assign)\s*\(", text[rest:]):
                open_at = text.index("(", rest)
                key = text[open_at + 1:matching(text, open_at, 1)]
                written = True
            else:
                continue
            if written:
                sites.append((start, receiver, container, key, start))
        # Another name for a set of marks: auto& ledger = s.nations.at(x).turnFlags;
        for alias in re.finditer(r"\bauto\s*&\s*(\w+)\s*=\s*([^;]+?)\s*(?:\.|->)\s*(turnFlags|gameFlags|flags|commitments)\s*;", text):
            name, holder, container = alias.groups()
            end = text.find("\n}", alias.end())
            for use in re.finditer(rf"(\+\+|--)?(?<![.\w>]){name}\s*\[", text[alias.end():end]):
                at = alias.end() + use.start(2) if use.group(1) else alias.end() + use.start()
                open_at = alias.end() + use.end() - 1
                close = matching(text, open_at, 1)
                after = text[close + 1:close + 4].lstrip()
                if use.group(1) or re.match(r"(=(?!=)|\+=|-=|\|=|\+\+|--)", after):
                    sites.append((alias.start(), holder.strip(), container, text[open_at + 1:close], open_at))
        for start, receiver, container, key, use in sites:
            line = text.count("\n", 0, start) + 1
            kind, why = resolver.kind(receiver, start)
            if kind == "catalog":
                continue  # a catalog context's facts about a unit, not a mark
            if kind is not None and kind not in HOLDERS[container]:
                kind, why = None, f"{why}, but a {kind} holds no {container}"
            body = text[function_start(text, use):use]
            marks, how = key_marks(key, body)
            if not marks:
                out.append(Write("?", kind, path.name, line, receiver, f"{why}; {how}"))
            for mark in sorted(marks):
                out.append(Write(mark, kind, path.name, line, receiver, f"{why}; {how}"))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--sites", action="store_true", help="list every write")
    args = parser.parse_args()
    found = writes()
    if args.sites:
        for w in found:
            print(f"{w.file}:{w.line}\t{w.mark}\t{w.kind or 'UNRESOLVED'}\t{w.receiver}\t{w.why}")
        return
    kinds = defaultdict(set)
    for w in found:
        kinds[w.mark].add(w.kind or "UNRESOLVED")
    for mark in sorted(kinds):
        print(f"{mark}\t{' '.join(sorted(kinds[mark]))}")


if __name__ == "__main__":
    main()
