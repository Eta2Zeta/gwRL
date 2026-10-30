"""Held-out fixed opponents, true terminal metrics, and bounded operation profiles."""
from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
import time
from collections import Counter
from dataclasses import asdict
from typing import Any, Callable, Mapping, Sequence

from studies.shared.multiplayer_mcts import PLAYERS, MctsConfig, action_key, probabilities, vector
from .baselines import raw_action, scripted_policy
from .batching import BatchStats, search_many

EVALUATION_SCHEMA = "campaign-heldout-evaluation-v1"
PROFILE_SCHEMA = "campaign-operation-profile-v1"
TERRITORY_TRACKING_SCHEMA = "campaign-national-chinese-possession-tracking-v2"


def _seeds(values: Sequence[int], *, unique: bool, label: str) -> list[int]:
    result = list(values)
    if any(type(seed) is not int or seed < 0 or seed >= 2**64 for seed in result):
        raise ValueError(f"{label} must contain unsigned 64-bit integer seeds")
    if unique and len(set(result)) != len(result):
        raise ValueError(f"{label} must be unique within each target")
    return result


def validate_heldout_seeds(heldout_by_target: Mapping[str, Sequence[int]],
                           training_seeds: Sequence[int]) -> dict[str, Any]:
    """Exclude every training seed; permit paired seeds across different targets."""
    if set(heldout_by_target) != set(PLAYERS):
        raise ValueError("Held-out seed validation must include all three targets")
    training = set(_seeds(training_seeds, unique=False, label="Training seeds"))
    heldout = {}
    for player in PLAYERS:
        values = _seeds(heldout_by_target[player], unique=True, label=f"{player} held-out seeds")
        if not values:
            raise ValueError("Each target needs at least one held-out seed")
        overlap = training.intersection(values)
        if overlap:
            raise ValueError(f"{player} held-out seeds overlap training: {sorted(overlap)}")
        heldout[player] = values
    return {"heldout_by_target": heldout, "distinct_training_seeds": len(training),
            "disjoint_from_training": True, "cross_target_seed_reuse_allowed": True}


def uncertainty(values: Sequence[float]) -> dict[str, Any]:
    """An explicitly approximate normal interval, absent for zero/one game."""
    values = [float(value) for value in values]
    if any(not math.isfinite(value) for value in values):
        raise ValueError("Evaluation statistics require finite observations")
    if not values:
        return {"n": 0, "mean": None, "standard_error": None, "approximate_95_percent_interval": None}
    mean = statistics.fmean(values)
    error = statistics.stdev(values) / math.sqrt(len(values)) if len(values) > 1 else None
    return {"n": len(values), "mean": mean, "standard_error": error,
            "approximate_95_percent_interval": [mean - 1.96 * error, mean + 1.96 * error] if error is not None else None}


def _plain(value: Any) -> Any:
    return json.loads(json.dumps(value, allow_nan=False))


def _context_key(env: Any) -> str:
    encoded = json.dumps(env.context(), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _units(env: Any, *, state: Mapping[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    # Snapshot even if a toy/public observation returns mutable unit objects.
    state = env.observation()["state"] if state is None else state
    return {identity: {"owner": unit["owner"], "type": unit.get("type", "unspecified")}
            for identity, unit in state["units"].items()}


def _merge_stats(total: BatchStats, wave: BatchStats) -> None:
    total.roots += wave.roots
    total.requests += wave.requests
    total.batches += wave.batches
    total.batch_sizes.extend(wave.batch_sizes)
    total.inference_seconds += wave.inference_seconds
    total.elapsed_seconds += wave.elapsed_seconds


class JapanTerritoryTracker:
    """Separate national possession changes in Chinese Home Country.

    Japan remains the default and the primary metric. Dadao uses an independent
    tracker so its exact zones and IPP never count as Japanese expansion.

    Acquisition is deliberately broader than a combat capture: influence,
    alignment and postcombat possession choices can also change possession.
    These are evaluation diagnostics, never additional learning rewards.
    """
    def __init__(self, context: Mapping[str, Any], state: Mapping[str, Any], *, nation: str = "japan"):
        if nation not in {"japan", "dadao"}:
            raise ValueError("Chinese possession diagnostics require Japan or Dadao")
        self.nation = nation
        faction = context.get("factions", {}).get("kmt", {})
        if not faction.get("home_country_known") or not faction.get("home_country"):
            raise ValueError("Japanese expansion metrics require known Chinese Home Country")
        nodes = context["geography"]["nodes"]
        self.values = {zone: float(nodes[zone].get("ipp_value") or 0)
                       for zone in faction["home_country"] if zone in state["territories"]}
        if not self.values or any(not math.isfinite(value) or value < 0 for value in self.values.values()):
            raise ValueError("Chinese Home Country metrics need finite nonnegative land values")
        self.previous = {zone: state["territories"][zone].get("possessor") for zone in self.values}
        self.initial = {zone for zone, owner in self.previous.items() if owner == self.nation}
        self.events: list[dict[str, Any]] = []

    def record(self, state: Mapping[str, Any], transition: int, kind: str) -> None:
        for zone, previous in self.previous.items():
            current = state["territories"][zone].get("possessor")
            if current != previous and self.nation in (previous, current):
                self.events.append({"zone": zone, "ipp_value": self.values[zone],
                    "previous_possessor": previous, "possessor": current,
                    "transition": transition, "action_kind": kind,
                    "clock": _plain(state["clock"])})
            self.previous[zone] = current

    def summary(self, *, terminal: bool) -> dict[str, Any]:
        final = {zone for zone, owner in self.previous.items() if owner == self.nation}

        def holdings(zones):
            return {"zones": sorted(zones), "count": len(zones),
                    "ipp": math.fsum(self.values[zone] for zone in zones)}

        acquisitions = [event for event in self.events if event["possessor"] == self.nation]
        losses = [event for event in self.events if event["previous_possessor"] == self.nation]
        return {"scope": "KMT Chinese Home Country intersected with campaign land zones",
            "scope_zones": sorted(self.values), "nation": self.nation, "terminal": terminal,
            "initial": holdings(self.initial), "at_stop": holdings(final),
            "newly_held": holdings(final - self.initial),
            "initial_holdings_lost": holdings(self.initial - final),
            "net_ipp_change": math.fsum(self.values[zone] for zone in final) -
                              math.fsum(self.values[zone] for zone in self.initial),
            "gross_acquisition_events": len(acquisitions),
            "gross_acquired_ipp": math.fsum(event["ipp_value"] for event in acquisitions),
            "gross_loss_events": len(losses),
            "gross_lost_ipp": math.fsum(event["ipp_value"] for event in losses),
            "new_acquisitions_lost_again": holdings(
                {event["zone"] for event in acquisitions} - self.initial - final),
            "events": self.events,
            "interpretation": "Possession acquisitions include influence/alignment, not only combat captures; "
                              "gross events include recaptures. At-stop holdings are not terminal results unless terminal=true."}


def evaluate(env_factory: Callable[[int], Any], evaluator: Any, *, target_player: str,
             seeds: Sequence[int], baseline_style: str = "balanced", simulations: int = 2,
             max_depth: int = 4, max_transitions: int = 500,
             target_script: str | None = None, max_state_visits: int | None = 20,
             selection_mode: str = "search", track_japan: bool = False,
             stop_requested: Callable[[], bool] | None = None) -> dict[str, Any]:
    """Search the target; sample the same fixed opponents in search and play.

    A transition cap stops collection only. Cutoff snapshots contribute neither
    observed returns nor calibration/terminal wealth confidence intervals.
    target_script supplies an explicit baseline-versus-baseline control.
    A repeated-state guard counts the initial state and each real transition;
    it is a nonterminal collection cutoff, not proof of an inescapable loop.
    Set max_state_visits=None to use the transition budget alone.
    Call validate_heldout_seeds with the training seed log before a study run.
    """
    seeds = _seeds(seeds, unique=True, label="Evaluation seeds")
    if selection_mode not in {"search", "network_only"}:
        raise ValueError("Evaluation selection mode must be search or network_only")
    if target_script is not None and selection_mode != "search":
        raise ValueError("A scripted control cannot also use network_only selection")
    if target_player not in PLAYERS or not seeds:
        raise ValueError("Evaluation requires an actor and held-out seeds")
    if type(max_transitions) is not int or max_transitions <= 0:
        raise ValueError("Evaluation transition budget must be a positive integer")
    if max_state_visits is not None and (type(max_state_visits) is not int or max_state_visits <= 0):
        raise ValueError("Repeated-state visit threshold must be a positive integer or None")
    if type(simulations) is not int or type(max_depth) is not int:
        raise ValueError("Search budgets must be positive integers")
    MctsConfig(simulations=simulations, max_depth=max_depth)
    opponent = scripted_policy(baseline_style)
    target_policy = scripted_policy(target_script) if target_script is not None else None
    if target_policy is None and (not isinstance(getattr(evaluator, "version", None), str) or not evaluator.version):
        raise ValueError("Search evaluation requires versioned frozen weights")
    evaluator_version = evaluator.version if target_policy is None else None
    envs = [env_factory(seed) for seed in seeds]
    if len({id(env) for env in envs}) != len(envs):
        raise ValueError("Evaluation seeds must produce independent environments")
    rngs = [random.Random(seed ^ 0xD1B54A32D192ED03) for seed in seeds]
    search_rngs = [random.Random(seed ^ 0x9E3779B97F4A7C15) for seed in seeds]
    counts = [Counter({"transitions": 0, "chance_events": 0}) for _ in seeds]
    owners = [Counter({player: 0 for player in PLAYERS}) for _ in seeds]
    previous_units = [_units(env) for env in envs]
    territory_trackers = [JapanTerritoryTracker(env.context(), env.observation()["state"])
                          if track_japan else None for env in envs]
    dadao_trackers = [JapanTerritoryTracker(env.context(), env.observation()["state"], nation="dadao")
                      if track_japan else None for env in envs]
    casualties, casualty_types = [Counter() for _ in seeds], [Counter() for _ in seeds]
    predictions, prediction_points = [None] * len(seeds), [None] * len(seeds)
    initial = [{"planning_key": env.planning_key(), "context_sha256": _context_key(env),
                "clock": _plain(env.observation()["state"]["clock"]), "wealth": _plain(env.wealth())}
               for env in envs]
    state_visits = [Counter({start["planning_key"]: 1}) for start in initial]
    decisions, search_calls = 0, 0
    batch_stats = BatchStats()
    started = time.perf_counter()

    def repeated_state_limit(index: int) -> bool:
        return (max_state_visits is not None and
                state_visits[index][envs[index].planning_key()] >= max_state_visits)

    def record(index: int, kind: str, owner: str | None) -> None:
        nonlocal decisions
        counts[index]["transitions"] += 1
        counts[index][kind] += 1
        if owner is not None:
            decisions += 1
            owners[index][owner] += 1
        state = envs[index].observation()["state"]
        units = _units(envs[index], state=state)
        for identity in previous_units[index].keys() - units.keys():
            unit = previous_units[index][identity]
            casualties[index][unit["owner"]] += 1
            casualty_types[index][(unit["owner"], unit["type"])] += 1
        previous_units[index] = units
        if territory_trackers[index] is not None:
            territory_trackers[index].record(state, counts[index]["transitions"], kind)
        if dadao_trackers[index] is not None:
            dadao_trackers[index].record(state, counts[index]["transitions"], kind)
        state_visits[index][envs[index].planning_key()] += 1

    externally_stopped = False
    while True:
        if stop_requested is not None and stop_requested():
            externally_stopped = True
            break
        active = [i for i, env in enumerate(envs)
                  if not env.is_terminal() and counts[i]["transitions"] < max_transitions and
                  not repeated_state_limit(i)]
        if not active:
            break
        searches, configs, indices = [], [], []
        for index in active:
            env = envs[index]
            if env.decision_kind() == "chance":
                env.resolve_chance()
                record(index, "chance_events", None)
                continue
            owner = env.current_decision_player()
            actions = list(env.legal_actions())
            if owner not in PLAYERS or not actions:
                raise ValueError("A nonterminal evaluation decision must have an entitled actor and legal actions")
            if owner == target_player and target_policy is None:
                indices.append(index)
                searches.append(env)
                configs.append(MctsConfig(simulations=simulations, max_depth=max_depth,
                    seed=search_rngs[index].getrandbits(64), mode="fixed_opponents", target_player=target_player))
                continue
            policy = target_policy if owner == target_player else opponent
            action = actions[policy.sample(env, actions, rngs[index])]
            env.apply_action(action)
            record(index, raw_action(action)["kind"], owner)
        if searches:
            if evaluator.version != evaluator_version:
                raise ValueError("Evaluation weights version changed between search waves")
            # The coordinator resets per-call stats; retain every wave.
            wave = BatchStats()
            if selection_mode == "search":
                results = search_many(searches, evaluator, configs=configs,
                                      opponent_policies=[opponent] * len(searches), add_root_noise=False, stats=wave)
                selected = [result.best_action() for result in results]
                search_calls += 1
            else:
                menus = [list(env.legal_actions()) for env in searches]
                before = time.perf_counter()
                results = evaluator.evaluate_batch(list(zip(searches, menus, strict=True)))
                seconds = time.perf_counter() - before
                wave.roots = wave.requests = len(searches)
                wave.batches, wave.batch_sizes = 1, [len(searches)]
                wave.inference_seconds = wave.elapsed_seconds = seconds
                selected = []
                for result, actions in zip(results, menus, strict=True):
                    priors = probabilities(result.priors, len(actions))
                    best = min(range(len(actions)), key=lambda i: (-priors[i], action_key(actions[i])))
                    selected.append(actions[best])
            _merge_stats(batch_stats, wave)
            for index, result, action in zip(indices, results, selected, strict=True):
                env = envs[index]
                # A one-action root has no search value; the next searched decision gives it.
                if predictions[index] is None and result.values is not None:
                    predictions[index] = list(vector(result.values))
                    prediction_points[index] = {"planning_key": env.planning_key(),
                                                "transitions": counts[index]["transitions"],
                                                "clock": _plain(env.observation()["state"]["clock"])}
                env.apply_action(action)
                record(index, raw_action(action)["kind"], target_player)
    elapsed = time.perf_counter() - started
    if target_policy is None and evaluator.version != evaluator_version:
        raise ValueError("Evaluation weights version changed during held-out games")
    games = []
    for index, (seed, env) in enumerate(zip(seeds, envs, strict=True)):
        state = env.observation()["state"]
        terminal = bool(env.is_terminal())
        guarded = not terminal and repeated_state_limit(index)
        repeated_key, max_seen = state_visits[index].most_common(1)[0]
        returns = list(vector(env.returns())) if terminal else None
        prediction = predictions[index]
        errors = [p - value for p, value in zip(prediction, returns, strict=True)] if prediction is not None and returns is not None else None
        type_losses: dict[str, dict[str, int]] = {}
        for (nation, kind), amount in casualty_types[index].items():
            type_losses.setdefault(nation, {})[kind] = amount
        games.append({"seed": seed, "terminal": terminal, "truncated": not terminal,
            "stop_reason": "terminal" if terminal else "external_stop" if externally_stopped else
                           "repeated_state_guard" if guarded else "transition_budget",
            "transition_budget": max_transitions,
            "repeated_state_guard": {"threshold": max_state_visits, "max_seen": max_seen,
                "repeated_key": repeated_key if max_seen > 1 else None,
                "includes_initial_state": True, "triggered": guarded},
            "initial": initial[index], "clock": state["clock"], "counts": dict(counts[index]),
            "completed_turns_at_stop": state.get("completed_turns", {}),
            "decisions_by_actor": dict(owners[index]), "casualties_by_nation": dict(casualties[index]),
            "casualties_by_nation_and_type": type_losses,
            "territorial_control": dict(Counter(land.get("possessor") or "unpossessed" for land in state["territories"].values())),
            "wealth_components_at_stop": env.wealth(), "observed_terminal_returns": returns,
            "first_search_value_prediction": prediction if selection_mode == "search" else None,
            "first_search_prediction_point": prediction_points[index] if selection_mode == "search" else None,
            "first_network_value_prediction": prediction if selection_mode == "network_only" else None,
            "first_network_prediction_point": prediction_points[index] if selection_mode == "network_only" else None,
            "terminal_value_error": errors,
            "terminal_squared_value_error": [error ** 2 for error in errors] if errors is not None else None,
            "final_planning_key": env.planning_key(), "illegal_actions": 0,
            **({"japan_chinese_home_country": territory_trackers[index].summary(terminal=terminal),
                "dadao_chinese_home_country": dadao_trackers[index].summary(terminal=terminal)}
               if territory_trackers[index] is not None else {})})
    terminal_games = [game for game in games if game["terminal"]]
    calibrated = [game for game in terminal_games if game["terminal_value_error"] is not None]
    components = sorted({key for game in games for player in PLAYERS
                         for key in game["wealth_components_at_stop"][player]})
    return _plain({"schema": EVALUATION_SCHEMA,
        **({"territorial_tracking_schema": TERRITORY_TRACKING_SCHEMA} if track_japan else {}),
        "target_player": target_player,
        "target_policy": target_policy.version if target_policy else evaluator_version,
        "opponent_policy": opponent.version, "search_mode": ("fixed_opponents" if selection_mode == "search" else "network_only")
            if target_policy is None else "scripted_control",
        "root_noise": False, "simulations": simulations if selection_mode == "search" else 0,
        "max_depth": max_depth if selection_mode == "search" else 0,
        "max_transitions": max_transitions, "max_state_visits": max_state_visits, "seeds": seeds, "games": games,
        "terminal_games": len(terminal_games), "truncated_games": len(games) - len(terminal_games),
        "observed_return_statistics": {player: uncertainty([game["observed_terminal_returns"][i] for game in terminal_games])
            for i, player in enumerate(PLAYERS)},
        "observed_terminal_wealth_statistics": {player: {
            component: uncertainty([game["wealth_components_at_stop"][player][component] for game in terminal_games
                                    if component in game["wealth_components_at_stop"][player]])
            for component in components} for player in PLAYERS},
        "value_calibration": {"prediction_source": ("first target MCTS root mean" if selection_mode == "search" else
                                                   "first target network value") + ", in raw three-vector units",
            "complete_games": len(calibrated),
            "error": {player: uncertainty([game["terminal_value_error"][i] for game in calibrated]) for i, player in enumerate(PLAYERS)},
            "squared_error": {player: uncertainty([game["terminal_squared_value_error"][i] for game in calibrated]) for i, player in enumerate(PLAYERS)}},
        "decision_throughput": {"wall_seconds": elapsed, "decisions": decisions,
                                "decisions_per_second": decisions / elapsed if elapsed else None},
        "inference_batches": {**asdict(batch_stats), "search_calls": search_calls},
        "limits": ["Short horizon variants are curriculum tasks, not full July1941 target results.",
                   "Truncated snapshots contribute no observed terminal return, terminal wealth interval, or calibration.",
                   "The repeated-state guard is a nonterminal collection limit, not proof of an infinite loop; changing search seeds or execution RNG may allow escape.",
                   "Casualties count removed unit identities, including combat, surrender and forced removal; ownership transfers are not casualties.",
                   "Intervals use a normal approximation; very small or dependent samples do not establish strategic strength.",
                   "Illegal rule actions raise an error rather than being silently replaced."]})


def _synchronize(evaluator: Any) -> None:
    models = getattr(evaluator, "models", {})
    devices = {next(model.parameters()).device for model in models.values()}
    if devices:
        import torch
        for device in devices:
            if device.type == "cuda":
                torch.cuda.synchronize(device)
            elif device.type == "mps":
                torch.mps.synchronize()


def profile(envs: Sequence[Any], evaluator: Any, repeats: int = 3) -> dict[str, Any]:
    """Time real operations/inference; apply rule transitions on clones only."""
    envs = list(envs)
    if not envs or type(repeats) is not int or repeats <= 0:
        raise ValueError("Profiling needs environments and a positive repeat count")
    checkpoints = [env.serialize() for env in envs]
    samples = {name: [] for name in ("clone", "legal_actions", "observation", "context", "rule_transition", "inference_scalar", "inference_batch")}
    menus = [list(env.legal_actions()) if env.decision_kind() not in {"chance", "terminal"} else [] for env in envs]

    def measured(name: str, operation: Callable[[], Any], *, inference: bool = False) -> None:
        if inference:
            _synchronize(evaluator)
        start = time.perf_counter()
        operation()
        if inference:
            _synchronize(evaluator)
        samples[name].append(time.perf_counter() - start)

    for _ in range(repeats):
        for env, actions in zip(envs, menus, strict=True):
            measured("clone", env.clone)
            measured("legal_actions", env.legal_actions)
            measured("observation", env.observation)
            measured("context", env.context)
            clone = env.clone()
            if clone.decision_kind() == "chance":
                measured("rule_transition", clone.resolve_chance)
            elif not clone.is_terminal():
                chosen = min(clone.legal_actions(), key=action_key)
                measured("rule_transition", lambda: clone.apply_action(chosen))
            measured("inference_scalar", lambda: evaluator.evaluate(env, actions), inference=True)
        measured("inference_batch", lambda: evaluator.evaluate_batch(list(zip(envs, menus, strict=True))), inference=True)
    unchanged = all(env.serialize() == checkpoint for env, checkpoint in zip(envs, checkpoints, strict=True))
    if not unchanged:
        raise RuntimeError("Profiling mutated a live environment or its execution RNG")
    return _plain({"schema": PROFILE_SCHEMA, "evaluator_version": evaluator.version, "repeats": repeats,
        "environments": len(envs), "actual_state_unchanged": unchanged,
        "decision_kinds": [env.decision_kind() for env in envs], "legal_menu_sizes": [len(menu) for menu in menus],
        "inference_batch_sizes": [len(envs)] * repeats,
        "timings_seconds": {name: {"samples": values, "mean": statistics.fmean(values) if values else None,
                                    "median": statistics.median(values) if values else None,
                                    "total": math.fsum(values)} for name, values in samples.items()},
        "limits": ["Timings include first-use token parsing and later warm calls.",
                   "A rule transition is one legal action or chance on a clone, not an entire turn."]})
