"""The documentation holds together: links resolve, cited documents exist, history stays in the archive.

`docs/README.md` is the starting point of the documentation. These checks keep
it navigable when pages move: every relative link in a tracked Markdown file
must lead to an existing file and, in a Markdown file, to an existing heading;
every document the game data or the code cites must exist; dated records may
live only under `docs/archive`; and nothing outside it is named after one of
the engine's build stages.
"""
from __future__ import annotations

import re
import subprocess
import unittest
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
# Source scans, map crops and rulebook PDFs are deliberately not in git, so a
# clean clone lacks them. A link to one is checked only where the file exists.
LOCAL_ONLY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf"}

LINK = re.compile(r"!?\[(?:[^\[\]]|\[[^\[\]]*\])*\]\(\s*<?([^()\s<>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
FENCED = re.compile(r"^(```|~~~).*?^\1[^\n]*$", re.MULTILINE | re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")
HEADING = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)
HTML_ANCHOR = re.compile(r"<a\s+(?:id|name)=\"([^\"]+)\"")
CITED_DOCUMENT = re.compile(r"\bdocs/[A-Za-z0-9_./-]*[A-Za-z0-9_/]")
DATED_NAME = re.compile(r"(19|20)\d\d[_-]\d\d[_-]\d\d")
STAGE_NAME = re.compile(r"^(m\d+|milestones?|stage_\w+)$")
STAGE_FILE = re.compile(r"(^|_)m\d+_")
# The labels of the engine's build stages. "M4 Max" is the machine, not a stage.
STAGE_LABEL = re.compile(r"\bM(?:1[0-2]|\d)\b(?! Max)|\bStage [A-D]\b")
# Pages about the board, whose Mediterranean sea zones are printed M1 to M12.
BOARD_PAGES = ("docs/map_audits/", "game_content/maps/")
# The page that states this rule has to name the labels it rules out.
STATES_THE_RULE = "AGENTS.md"


def tracked(*patterns: str) -> list[str]:
    result = subprocess.run(["git", "ls-files", "--", *patterns], cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise unittest.SkipTest("the documentation checks read the file list from git")
    return [line for line in result.stdout.splitlines() if (ROOT / line).is_file()]


def prose(text: str) -> str:
    """The text without code blocks and code spans, where link syntax is not a link."""
    return INLINE_CODE.sub("", FENCED.sub("", text))


@lru_cache(maxsize=None)
def anchors(path: Path) -> frozenset[str]:
    """The anchors GitHub gives a Markdown file's headings, plus explicit HTML anchors."""
    text = path.read_text()
    found: set[str] = set(HTML_ANCHOR.findall(text))
    seen: dict[str, int] = {}
    for title in HEADING.findall(FENCED.sub("", text)):
        title = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", title).replace("`", "").replace("*", "")
        slug = re.sub(r"[^\w\- ]", "", title.strip().lower()).replace(" ", "-")
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        found.add(slug if count == 0 else f"{slug}-{count}")
    return frozenset(found)


class DocumentationTests(unittest.TestCase):
    def test_every_relative_link_leads_somewhere(self):
        broken = []
        for name in tracked("*.md"):
            source = ROOT / name
            for target in LINK.findall(prose(source.read_text())):
                if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target) or target.startswith("//"):
                    continue
                if target.startswith("/"):
                    broken.append(f"{name}: {target} is an absolute path; link relatively")
                    continue
                path, _, anchor = target.partition("#")
                destination = (source.parent / unquote(path)).resolve() if path else source
                if not destination.exists():
                    if destination.suffix.lower() not in LOCAL_ONLY_SUFFIXES:
                        broken.append(f"{name}: {target} does not exist")
                    continue
                if anchor and destination.suffix == ".md" and unquote(anchor) not in anchors(destination):
                    broken.append(f"{name}: {target} names no heading of that page")
        self.assertEqual(broken, [], "\n" + "\n".join(broken))

    def test_documents_cited_by_data_and_code_exist(self):
        missing = []
        cited_from = tracked("game_content/*.json", "src", "include", "studies/*.py", "tools/*.py", "tests/*.py",
                             "tests/*.cpp")
        for name in cited_from:
            if name.startswith("game_content/maps/authoring/"):
                continue
            if name == "tests/test_documentation.py":
                continue
            for cited in set(CITED_DOCUMENT.findall((ROOT / name).read_text(errors="replace"))):
                path = ROOT / cited
                if not path.exists() and path.suffix.lower() not in LOCAL_ONLY_SUFFIXES:
                    missing.append(f"{name} cites {cited}")
        self.assertEqual(missing, [], "\n" + "\n".join(sorted(missing)))

    def test_history_lives_in_the_archive(self):
        """Outside docs/archive no document is named after a date."""
        current = [name for name in tracked("docs") if not name.startswith("docs/archive/")]
        dated = [name for name in current if DATED_NAME.search(name)]
        self.assertEqual(dated, [], "Dated records belong in docs/archive/records:\n" + "\n".join(dated))
        self.assertTrue((ROOT / "docs/README.md").is_file(), "docs/README.md is the documentation's starting point")

    def test_nothing_current_is_named_after_a_build_stage(self):
        """A stage label says when a thing was built, not what it is; only the archive uses them."""
        current = [name for name in tracked() if not name.startswith("docs/archive/")]
        staged = [name for name in current
                  if any(STAGE_NAME.match(part) for part in Path(name).parts[:-1])
                  or STAGE_FILE.search(Path(name).name)]
        self.assertEqual(staged, [], "Name files and folders by subject, not by build stage:\n" + "\n".join(staged))
        labelled = []
        for name in current:
            if not name.endswith(".md") or name.startswith(BOARD_PAGES) or name == STATES_THE_RULE:
                continue
            for label in sorted(set(STAGE_LABEL.findall(prose((ROOT / name).read_text())))):
                labelled.append(f"{name}: {label}")
        self.assertEqual(labelled, [], "Say what the thing is, not the stage that built it:\n" + "\n".join(labelled))


if __name__ == "__main__":
    unittest.main()
