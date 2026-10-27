"""Archive integrity and legacy-reference compatibility without game execution."""

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.check_documentation import check_links, check_manifest, resolve_legacy_document


class DocumentationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="gwrl-docs-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, capture_output=True)
        (self.root / ".gitignore").write_text("*.png\n")
        self.manifest_path = self.root / "docs/archive/manifest.json"

    def archive(self, original, destination, data, **metadata):
        path = self.root / destination
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return {"original_path": original, "archive_path": destination,
                "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), **metadata}

    def manifest(self, entries, **metadata):
        value = {"schema_version": 1, "source_commit": "a" * 40,
                 "entries": entries, **metadata}
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(value))
        return check_manifest(self.root, self.manifest_path)[1]

    def test_required_evidence_rejects_changed_bytes_and_missing_files(self):
        entry = self.archive("docs/old.md", "docs/archive/old.md", b"original evidence")
        self.assertEqual(self.manifest([entry]), [])
        path = self.root / entry["archive_path"]
        path.write_bytes(b"different evidence")
        self.assertTrue(any("differs" in error for error in self.manifest([entry])))
        path.unlink()
        self.assertTrue(any(entry["archive_path"] in error for error in self.manifest([entry])))

    def test_versioned_archives_resolve_latest_with_existing_path_precedence(self):
        original = "docs/m0/README.md"
        first = self.archive(original, "docs/archive/m0/first.md", b"first")
        latest = self.archive(original, "docs/archive/m0/latest.md", b"latest",
                              source_commit="b" * 40)
        self.assertEqual(self.manifest([first, latest]), [])
        self.assertEqual(resolve_legacy_document(self.root, original), self.root / latest["archive_path"])
        current = self.root / original
        current.parent.mkdir(parents=True)
        current.write_text("current maintained document")
        self.assertEqual(resolve_legacy_document(self.root, original), current)
        latest["source_commit"] = "a" * 40
        self.assertTrue(any("duplicate" in error for error in self.manifest([first, latest])))

    def test_optional_local_images_may_be_absent_but_existing_bytes_must_match(self):
        image = self.archive("docs/m9/map.png", "docs/archive/m9/map.png", b"local image")
        path = self.root / image["archive_path"]
        self.assertEqual(self.manifest([], optional_local_assets=[image]), [])
        path.unlink()
        self.assertEqual(self.manifest([], optional_local_assets=[image]), [])
        path.write_bytes(b"changed local image")
        self.assertTrue(any("differs" in error for error in self.manifest([], optional_local_assets=[image])))

    def test_legacy_resolution_does_not_repair_broken_maintained_links(self):
        entry = self.archive("docs/m1/README.md", "docs/archive/m1/overview.md", b"history")
        self.assertEqual(self.manifest([entry]), [])
        self.assertEqual(resolve_legacy_document(self.root, entry["original_path"]), self.root / entry["archive_path"])
        current = self.root / "docs/current.md"
        current.write_text("Read [the old guide](m1/README.md).\n")
        checked, errors = check_links(self.root, [current])
        self.assertEqual(checked, 1)
        self.assertEqual(len(errors), 1)
        self.assertIn("missing target m1/README.md", errors[0])


if __name__ == "__main__":
    unittest.main()
