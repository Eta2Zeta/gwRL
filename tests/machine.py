"""The most cores a test's configuration may use on this machine.

A machine profile in studies/campaign/profiles sets it under "tests": 9 on the
Mac and 7 on the Windows PC. GWRL_PROFILE names the profile; otherwise macOS
reads mac.json and Windows windows.json. Without a profile, tests may use the
owner's whole core allowance, and never more than this machine's logical cores.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from tools.supervise_campaign_training import CORE_ALLOWANCE

PROFILES = Path(__file__).resolve().parents[1] / "studies" / "campaign" / "profiles"
PLATFORM_PROFILES = {"darwin": "mac", "win32": "windows"}


def cpu_budget() -> int:
    name = os.environ.get("GWRL_PROFILE") or PLATFORM_PROFILES.get(sys.platform)
    budget = CORE_ALLOWANCE
    if name and (PROFILES / f"{name}.json").is_file():
        profile = json.loads((PROFILES / f"{name}.json").read_text(encoding="utf-8"))
        budget = profile.get("tests", {}).get("cpu_budget", budget)
    return min(budget, os.cpu_count() or 1)


CPU_BUDGET = cpu_budget()
