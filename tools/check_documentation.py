#!/usr/bin/env python3
"""Check maintained Markdown links and byte-preserved archived evidence.

Historical report prose can contain paths from its original checkout, so only
archive README indexes are link-checked. The archive manifest verifies relocated
evidence without rewriting its contents or depending on Git history.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit


INLINE_LINK = re.compile(r"!?\[[^\]\n]*\]\(\s*(<[^>\n]+>|[^\s)]+)")
REFERENCE_LINK = re.compile(r"^\s{0,3}\[[^\]\n]+\]:\s*(<[^>\n]+>|\S+)", re.MULTILINE)
HTML_LINK = re.compile(r"\b(?:href|src)\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
FROZEN_CHECKOUT = re.compile(r"^/Users/home/\.codex/worktrees/[^/]+/gwRL(?:/|$)")
PRIMARY_CHECKOUT = "/Users/home/Desktop/gwRL"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".tif", ".tiff", ".avif"}


def prose_only(markdown: str) -> str:
    """Remove fenced and inline examples without changing line numbers."""
    lines = []
    fence = None
    for line in markdown.splitlines(keepends=True):
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker and fence is None:
            fence = marker.group(1)
            lines.append("\n" if line.endswith("\n") else "")
        elif fence is not None:
            if marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence):
                fence = None
            lines.append("\n" if line.endswith("\n") else "")
        else:
            lines.append(re.sub(r"(`+).*?\1", "", line))
    return "".join(lines)


def markdown_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "*.md"],
        cwd=root, check=True, capture_output=True, text=True,
    )
    selected = set()
    for name in result.stdout.split("\0"):
        if not name:
            continue
        path = Path(name)
        in_scope = name == "README.md" or path.parts[0] in {"docs", "game_content", "studies", "web"}
        archived = name.startswith("docs/archive/")
        if in_scope and (not archived or path.name == "README.md") and (root / path).is_file():
            selected.add(root / path)
    return sorted(selected)


def local_target(root: Path, document: Path, target: str) -> Path | None:
    target = target.removeprefix("<").removesuffix(">")
    # Strip editor suffixes before URL parsing: ``file.py:12`` otherwise looks
    # like a URL with scheme "file.py".
    target = re.sub(r":\d+(?::\d+)?(?=[?#]|$)", "", target)
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    # Desktop file links can carry an editor line (and optional column).
    path = re.sub(r":\d+(?::\d+)?$", "", unquote(parsed.path))
    if path == PRIMARY_CHECKOUT or path.startswith(PRIMARY_CHECKOUT + "/"):
        return root / path[len(PRIMARY_CHECKOUT):].lstrip("/")
    frozen = FROZEN_CHECKOUT.match(path)
    if frozen:
        return root / path[frozen.end():]
    if path.startswith("/"):
        # Repository-root URLs are useful when rendered by a local doc server.
        rooted = root / path.lstrip("/")
        return rooted if rooted.exists() else Path(path)
    return document.parent / path


def check_links(root: Path, documents: list[Path], *, require_local_assets: bool = False,
                skipped_assets: set[str] | None = None) -> tuple[int, list[str]]:
    root = root.resolve()
    checked = 0
    errors = []
    missing = []
    for document in documents:
        prose = prose_only(document.read_text(encoding="utf-8"))
        for pattern in (INLINE_LINK, REFERENCE_LINK, HTML_LINK):
            for match in pattern.finditer(prose):
                target = local_target(root, document, match.group(1))
                if target is None:
                    continue
                checked += 1
                if not target.exists():
                    line = prose.count("\n", 0, match.start()) + 1
                    missing.append((document, line, match.group(1), target.resolve()))
    # Audit crops and other private local images follow the repository's ignore
    # policy. Check all missing image paths in one Git call so clean clones can
    # still verify maintained navigation without requiring those local assets.
    candidates = {str(target.relative_to(root)) for _, _, _, target in missing
                  if target.is_relative_to(root) and target.suffix.lower() in IMAGE_SUFFIXES}
    ignored = set()
    if candidates and not require_local_assets:
        result = subprocess.run(
            ["git", "check-ignore", "--stdin", "-z"], cwd=root,
            input="\0".join(sorted(candidates)) + "\0", capture_output=True, text=True,
        )
        if result.returncode not in {0, 1}:
            raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
        ignored = set(result.stdout.rstrip("\0").split("\0")) if result.stdout else set()
    for document, line, raw, target in missing:
        relative = str(target.relative_to(root)) if target.is_relative_to(root) else None
        if relative in ignored:
            if skipped_assets is not None:
                skipped_assets.add(relative)
        else:
            errors.append(f"{document.relative_to(root)}:{line}: missing target {raw}")
    return checked, errors


def check_manifest(root: Path, manifest_path: Path) -> tuple[int, list[str]]:
    root = root.resolve()
    errors = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return 0, [f"{manifest_path}: {error}"]
    if manifest.get("schema_version") != 1:
        errors.append("archive manifest: expected schema_version 1")
    if not re.fullmatch(r"[0-9a-f]{40}", str(manifest.get("source_commit", ""))):
        errors.append("archive manifest: source_commit must be a full Git commit hash")
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        return 0, errors + ["archive manifest: entries must be a list"]
    seen_original, seen_archive = set(), set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"archive manifest entry {index}: expected an object")
            continue
        original, archived = entry.get("original_path"), entry.get("archive_path")
        digest, size = entry.get("sha256"), entry.get("bytes")
        if not isinstance(original, str) or not isinstance(archived, str):
            errors.append(f"archive manifest entry {index}: missing original/archive paths")
            continue
        if original in seen_original or archived in seen_archive:
            errors.append(f"archive manifest entry {index}: duplicate path")
        seen_original.add(original)
        seen_archive.add(archived)
        destination = (root / archived).resolve()
        if not destination.is_relative_to(root) or not archived.startswith("docs/archive/"):
            errors.append(f"{archived}: archive destination must stay inside docs/archive")
            continue
        if not re.fullmatch(r"[0-9a-f]{64}", str(digest)) or type(size) is not int or size < 0:
            errors.append(f"{archived}: invalid SHA-256 or byte count")
            continue
        try:
            data = destination.read_bytes()
        except OSError as error:
            errors.append(f"{archived}: {error}")
            continue
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            errors.append(f"{archived}: archived evidence differs from recorded bytes/SHA-256")
    return len(entries), errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", type=Path, default=Path("docs/archive/manifest.json"))
    parser.add_argument("--require-local-assets", action="store_true",
                        help="Also require Git-ignored local images to exist")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    manifest_path = args.manifest if args.manifest.is_absolute() else root / args.manifest
    try:
        documents = markdown_files(root)
        skipped_assets = set()
        links, errors = check_links(root, documents, require_local_assets=args.require_local_assets,
                                    skipped_assets=skipped_assets)
    except (OSError, UnicodeError, subprocess.CalledProcessError) as error:
        print(f"Documentation check failed: {error}")
        return 1
    evidence, archive_errors = check_manifest(root, manifest_path)
    errors.extend(archive_errors)
    for error in errors[:50]:
        print(error)
    if len(errors) > 50:
        print(f"... {len(errors) - 50} additional errors omitted.")
    print(f"Documentation {'FAILED' if errors else 'OK'}: {len(documents)} Markdown files, "
          f"{links} local links, {evidence} archived evidence files, "
          f"{len(skipped_assets)} unavailable ignored local images skipped, {len(errors)} errors.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
