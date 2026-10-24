"""Explicit horizon variants of the same authoritative regional campaign.

The full target always uses the original eleven rounds. Short tasks have their
own definition fingerprint and real terminal condition; a runtime transition cap
is a separate truncation and never changes that condition.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import gwrl_cpp

from studies.shared.campaign_adapter import CampaignAdapter, SCHEMA as ADAPTER_SCHEMA

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = ROOT / "game_content/scenarios/japan_china_1936"
CURRICULUM_VERSION = "regional-horizon-curriculum-v1"


def make_env(seed: int, *, calendar_rounds: int | None = None,
             scenario: Path = SCENARIO, training_actions: bool = True) -> CampaignAdapter:
    raw = (gwrl_cpp.CampaignEnv(str(scenario), seed, training_actions=training_actions) if calendar_rounds is None else
           gwrl_cpp.CampaignEnv.curriculum(str(scenario), calendar_rounds, seed, training_actions=training_actions))
    return CampaignAdapter(raw)


def compatibility(env: CampaignAdapter) -> dict[str, str]:
    state = json.loads(env.raw.serialize())
    context = env.context()
    encoded = json.dumps(context["rules"], sort_keys=True, separators=(",", ":"))
    result = {"scenario": state["state"]["definition_fingerprint"],
            "rules": hashlib.sha256(encoded.encode()).hexdigest(),
            "schema": f"{gwrl_cpp.CAMPAIGN_SCHEMA}+{ADAPTER_SCHEMA}",
            "curriculum": CURRICULUM_VERSION}
    if "action_interface" in context:
        result["actions"] = context["action_interface"]
    return result


def task_manifest(env: CampaignAdapter) -> dict:
    curriculum = env.context()["rules"].get("curriculum")
    return {"version": CURRICULUM_VERSION, "compatibility": compatibility(env),
            "full_target_game": curriculum is None,
            "calendar_rounds": 11 if curriculum is None else curriculum["calendar_rounds"],
            "setup": "unchanged approved 99-piece,37-node July1936 setup",
            "reward": "terminal wealth gap; zero intermediate reward; gamma=1",
            "short_task_limit": "Horizon variants are curriculum tasks, not July1941 campaign results."}
