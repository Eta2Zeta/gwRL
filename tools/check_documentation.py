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
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".tif", ".tiff", ".heic", ".avif"}


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


def _repository_path(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute() or ".." in Path(value).parts:
        raise ValueError("expected a nonempty repository-relative path without '..'")
    result = (root / value).resolve()
    if not result.is_relative_to(root):
        raise ValueError("path escapes the repository")
    return result


def _archive_path(root: Path, value: str) -> Path:
    result = _repository_path(root, value)
    if Path(value).parts[:2] != ("docs", "archive"):
        raise ValueError("archive destination must stay inside docs/archive")
    return result


def resolve_legacy_document(root: Path, original_path: str) -> Path:
    """Resolve a frozen document reference without rewriting its recorded JSON.

    Current paths win. Relocated references use the last matching manifest entry,
    so append order selects the newest archived version. Maintained Markdown links
    do not use this compatibility helper and must name their current targets.
    """
    root = root.resolve()
    current = _repository_path(root, original_path)
    if current.exists():
        return current
    manifest = json.loads((root / "docs/archive/manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("entries"), list):
        raise ValueError("archive manifest must contain an entries list")
    for entry in reversed(manifest["entries"]):
        if isinstance(entry, dict) and entry.get("original_path") == original_path:
            archived = _archive_path(root, entry.get("archive_path"))
            if archived.exists():
                return archived
            raise FileNotFoundError(f"Archived document is missing: {archived}")
    raise FileNotFoundError(f"Document has no current or archived target: {original_path}")


def check_manifest(root: Path, manifest_path: Path) -> tuple[int, list[str]]:
    root = root.resolve()
    errors = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return 0, [f"{manifest_path}: {error}"]
    if not isinstance(manifest, dict):
        return 0, ["archive manifest: expected an object"]
    if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        errors.append("archive manifest: expected schema_version 1")
    if not isinstance(manifest.get("source_commit"), str) or not re.fullmatch(r"[0-9a-f]{40}", manifest["source_commit"]):
        errors.append("archive manifest: source_commit must be a full Git commit hash")
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        return 0, errors + ["archive manifest: entries must be a list"]
    optional = manifest.get("optional_local_assets", [])
    if not isinstance(optional, list):
        errors.append("archive manifest: optional_local_assets must be a list")
        optional = []
    seen_original, seen_archive = set(), set()
    local_images = set()
    records = [(f"entry {index}", entry, False) for index, entry in enumerate(entries)]
    records += [(f"optional local asset {index}", entry, True) for index, entry in enumerate(optional)]
    for label, entry, is_optional in records:
        if not isinstance(entry, dict):
            errors.append(f"archive manifest {label}: expected an object")
            continue
        original, archived = entry.get("original_path"), entry.get("archive_path")
        digest, size = entry.get("sha256"), entry.get("bytes")
        commit = entry.get("source_commit", manifest.get("source_commit"))
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
            errors.append(f"archive manifest {label}: source_commit must be a full Git commit hash")
            continue
        try:
            _repository_path(root, original)
            destination = _archive_path(root, archived)
        except ValueError as error:
            errors.append(f"archive manifest {label}: {error}")
            continue
        if (original, commit) in seen_original or archived in seen_archive:
            errors.append(f"archive manifest {label}: duplicate original/version or archive path")
        seen_original.add((original, commit))
        seen_archive.add(archived)
        if is_optional and (Path(original).suffix.lower() not in IMAGE_SUFFIXES
                            or destination.suffix.lower() not in IMAGE_SUFFIXES):
            errors.append(f"{archived}: optional local assets must be images")
            continue
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest) or type(size) is not int or size < 0:
            errors.append(f"{archived}: invalid SHA-256 or byte count")
            continue
        if is_optional:
            local_images.add(archived)
            if not destination.exists():
                continue
        try:
            data = destination.read_bytes()
        except OSError as error:
            errors.append(f"{archived}: {error}")
            continue
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            errors.append(f"{archived}: archived evidence differs from recorded bytes/SHA-256")
    if local_images:
        result = subprocess.run(
            ["git", "check-ignore", "--stdin", "-z"], cwd=root,
            input="\0".join(sorted(local_images)) + "\0", capture_output=True, text=True,
        )
        if result.returncode not in {0, 1}:
            errors.append("archive manifest: could not verify Git ignore policy for optional local images")
        else:
            ignored = set(result.stdout.rstrip("\0").split("\0")) if result.stdout else set()
            errors.extend(f"{path}: optional local image must be Git-ignored" for path in sorted(local_images - ignored))
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
