"""Replace a file atomically, waiting out the brief locks Windows gives readers."""
from __future__ import annotations

import os
import sys
import time


def replace_file(source, target, *, attempts: int = 100, pause: float = 0.05) -> None:
    """os.replace, retried for up to five seconds on Windows while another process has the target open.

    Windows refuses to replace a file that a reader, an indexer or a virus scanner
    holds open, with PermissionError, for as long as it stays open. macOS and Linux
    replace an open file at once, so there the first error is raised.
    """
    for attempt in range(attempts):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if sys.platform != "win32" or attempt == attempts - 1:
                raise
            time.sleep(pause)
