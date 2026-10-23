"""Versioned active baselines; search and actual play use the same distribution.

These are inexpensive verification opponents, not claims of strategic strength.
Every choice comes from the authoritative legal menu, including reactions.
"""
from __future__ import annotations

import math
from collections import deque
from typing import Any, Sequence

from studies.shared.multiplayer_mcts import OpponentPolicy, action_key

BASELINE_VERSION = "campaign-active-baseline-v2"


def raw_action(action: Any) -> dict:
    if hasattr(action, "features"):
        features = action.features()
        return features.get("action") or features
    if isinstance(action, dict):
        return action.get("action") or action
    return {name: getattr(action, name) for name in ("kind", "nation", "parameters", "decision")}


def _costs(context: dict) -> dict[str, float]:
    result = {}
    for document in context["catalog"].values():
        if not isinstance(document, dict):
            continue
        for collection in ("units", "facilities"):
            for row in document.get(collection, []):
                if isinstance(row, dict) and row.get("asset_value") is not None:
                    result[row["id"]] = float(row["asset_value"])
    return result


def _distances(context: dict, state: dict, nation: str) -> dict[str, int]:
    nodes = context["geography"]["nodes"]
    targets = [zone for zone, land in state["territories"].items()
               if land.get("possessor") not in (None, nation)]
    distance = {zone: 0 for zone in targets}
    frontier = deque(targets)
    while frontier:
        zone = frontier.popleft()
        for edge in nodes[zone].get("neighbors", []):
            other = edge["neighbor_id"]
            if edge.get("passable") is False or other in distance:
                continue
            distance[other] = distance[zone] + 1
            frontier.append(other)
    return distance


def baseline_distribution(env: Any, actions: Sequence[Any], *, style: str = "balanced") -> list[float]:
    if style not in {"balanced", "cautious"}:
        raise ValueError("Unknown versioned baseline style")
    if not actions:
        return []
    observation = env.observation()
    state = observation["state"]
    context = env.context()
    costs = _costs(context)
    catalog_rows = {}
    for document in context["catalog"].values():
        if isinstance(document, dict):
            catalog_rows.update({row["id"]: row for row in document.get("rows", [])})
    distances = {}

    def score(action):
        outer_kind = getattr(action, "kind", None)
        raw = raw_action(action)
        kind, args = raw["kind"], raw.get("parameters", {})
        nation = raw.get("nation", "")
        if outer_kind == "pass_interrupt" or kind == "pass_interrupt":
            return 0.0
        if outer_kind == "interrupt":
            return 5.0 if style == "balanced" else -5.0
        if kind == "end_phase":
            return 0.0
        if kind == "politics_keep_capture":
            return 130.0
        if kind in {"economy_place", "economy_lease_place"} or kind.startswith("economy_complete"):
            return 120.0
        if kind in {"air_land", "air_end_patrol"}:
            return 110.0
        if kind == "air_land_noncombat":
            unit = state["units"].get(args.get("unit"), {})
            # This legal action is also offered for grounded aircraft, even
            # when the destination is their current zone. Give mandatory
            # in-flight returns priority without repeating a grounded landing.
            return 110.0 if unit.get("turn_flags", {}).get("air_in_flight") else -10.0
        if kind == "economy_finish_research":
            return 35.0
        if "take_casualty" in kind:
            unit = state["units"].get(args.get("unit"), {})
            return 100.0 - costs.get(unit.get("type"), 0)
        if "cancel" in kind or "remove" in kind or "decline" in kind:
            return -50.0
        if kind == "naval_force_add":
            return 5.0
        if "retreat" in kind:
            battle = next((b for b in state["battles"].values() if b.get("stage") != "finished"), {})
            round_number = battle.get("data", {}).get("round", 0)
            return 100.0 if style == "cautious" or round_number >= 3 else 10.0
        if any(word in kind for word in ("finish", "confirm", "accept", "approve")):
            return 70.0
        if kind in {"naval_route", "naval_screen_continue_route", "naval_strategic_continue"}:
            return 80.0
        if kind.startswith(("land_begin", "land_progress", "naval_begin", "naval_progress", "air_begin", "air_progress")):
            return 100.0
        if "continue_fighting" in kind:
            return 65.0
        if kind.startswith("recruitment_"):
            return 90.0
        if kind == "influence_roll":
            return 60.0 + min(5.0, float(args.get("spend", 0)))
        if kind == "economy_advance" or "repair" in kind:
            return 75.0
        if kind == "economy_research":
            return 65.0
        if kind == "economy_purchase":
            row = catalog_rows.get(args.get("row"), {})
            unit_type = row.get("type", "")
            return {"infantry": 60, "fighter": 56, "artillery": 52, "militia": 45}.get(unit_type, 15)
        if kind == "movement_route":
            path = args.get("path", [])
            target = path[-1] if path else args.get("zone")
            land = state["territories"].get(target, {})
            if target and land.get("possessor") not in (None, nation):
                defenders = [u for u in state["units"].values() if u["zone"] == target and u["owner"] != nation]
                income = context["geography"]["nodes"][target].get("ipp_value", 0) or 0
                return 80.0 + income - (len(defenders) * (5 if style == "balanced" else 15))
            if nation not in distances:
                distances[nation] = _distances(context, state, nation)
            source = path[0] if path else None
            progress = distances[nation].get(source, 100) - distances[nation].get(target, 100)
            return 20.0 + progress * 10 if progress > 0 else -10.0
        if kind in {"air_ground_attack", "air_support", "air_bomb", "naval_air_attack", "naval_port_attack", "naval_declare_assault"}:
            return 65.0 if style == "balanced" else 35.0
        if kind.startswith(("naval_load", "air_load")):
            return 40.0
        if kind == "naval_start_move":
            unit = state["units"].get(args.get("unit"), {})
            # A verification opponent makes one sea sortie per ship per turn
            # instead of spending its remaining movement on repeated zigzags.
            # The authoritative route is observable and checkpointed; this is
            # a policy preference, not an unrecorded action-history counter.
            if unit.get("route"):
                return -10.0
            return 30.0 if unit.get("cargo") else 10.0
        if raw.get("decision") is not None:
            return 40.0
        return -5.0

    scores = [float(score(action)) for action in actions]
    if not all(math.isfinite(x) for x in scores):
        raise ValueError("Nonfinite baseline score")
    while True:
        best = min(range(len(actions)), key=lambda i: (-scores[i], action_key(actions[i])))
        kind = raw_action(actions[best])["kind"]
        if kind not in {"naval_start_move", "naval_force_add"}:
            return [float(i == best) for i in range(len(actions))]
        # Opening/expanding the force picker is reversible bookkeeping. Only
        # choose it when the resulting legal menu contains an executable route
        # or engagement, rather than more edits followed by cancellation.
        # Probe the best candidate lazily: enumerating every ship's complete
        # route menu on every unrelated choice is unnecessarily expensive.
        probe = env.clone()
        probe.apply_action(actions[best])
        if any(raw_action(candidate)["kind"] in {"naval_route", "naval_engage_force"}
               for candidate in probe.legal_actions()):
            return [float(i == best) for i in range(len(actions))]
        scores[best] = -math.inf
        if all(score == -math.inf for score in scores):
            raise ValueError("A naval force picker has no executable route or cancellation")


def scripted_policy(style: str = "balanced") -> OpponentPolicy:
    if style not in {"balanced", "cautious"}:
        raise ValueError("Unknown versioned baseline style")
    return OpponentPolicy(f"{BASELINE_VERSION}:{style}",
                          lambda env, actions: baseline_distribution(env, actions, style=style))
