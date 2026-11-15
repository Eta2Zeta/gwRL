"""Replacing a file waits out a reader on Windows and changes nothing elsewhere."""
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from studies.shared.file_replace import replace_file


class FileReplaceTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32", "Only Windows refuses to replace an open file")
    def test_a_reader_holding_the_target_only_delays_the_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            target, source = Path(directory) / "state.json", Path(directory) / "new.json"
            target.write_text("old", encoding="utf-8")
            source.write_text("new", encoding="utf-8")
            reader = open(target, encoding="utf-8")  # Opened without delete sharing.
            try:
                with self.assertRaises(PermissionError):
                    os.replace(source, target)
                threading.Timer(0.3, reader.close).start()
                replace_file(source, target)
            finally:
                reader.close()
            self.assertEqual(target.read_text(encoding="utf-8"), "new")

    def test_elsewhere_a_refused_replacement_raises_at_once(self):
        calls = []

        def refuse(source, target):
            calls.append((source, target))
            raise PermissionError("refused")

        with patch("studies.shared.file_replace.os.replace", side_effect=refuse), \
                patch("studies.shared.file_replace.sys.platform", "darwin"), self.assertRaises(PermissionError):
            replace_file("new.json", "state.json")
        self.assertEqual(calls, [("new.json", "state.json")])


if __name__ == "__main__":
    unittest.main()
