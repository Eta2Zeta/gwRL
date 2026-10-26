"""Backend implementation code is pinned; ignored run snapshots are not."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from studies.campaign.run import source_hashes


class BackendSourceProvenanceTests(unittest.TestCase):
    def test_nested_backend_changes_are_pinned_without_hashing_run_archives(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = (
                "studies/campaign/run.py", "studies/campaign/backends/protocol.py",
                "studies/campaign/backends/gpu/kernel.py",
                "studies/shared/campaign_adapter.py", "studies/shared/multiplayer_mcts.py",
                "studies/shared/immutable_json.py", "include/game/fixture.hpp", "src/fixture.cpp",
                "studies/campaign/runs/ignored/runtime/studies/campaign/old.py",
            )
            for name in paths:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("original\n")
            with patch("studies.campaign.run.ROOT", root):
                before = source_hashes()
                self.assertIn("studies/campaign/backends/gpu/kernel.py", before)
                self.assertIn("studies/campaign/backends/protocol.py", before)
                self.assertEqual(len(before), len(paths) - 1)
                self.assertFalse(any("/runs/" in name for name in before))
                (root / paths[-1]).write_text("scratch output changes\n")
                self.assertEqual(source_hashes(), before)
                (root / "studies/campaign/backends/gpu/kernel.py").write_text("new implementation\n")
                after = source_hashes()
                self.assertEqual([key for key in before if before[key] != after[key]],
                                 ["studies/campaign/backends/gpu/kernel.py"])


if __name__ == "__main__":
    unittest.main()
