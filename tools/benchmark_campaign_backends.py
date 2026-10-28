#!/usr/bin/env python3
"""Guarded plain/wrapped CPU rules replay measurements, never training results.

A sampled three-round scripted game supplies actual legal choices and complete
chance requests/faces. Both measured paths replay those explicit outcomes. The
current CPU wrapper is a sequential reference, not a GPU or MCTS implementation.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCHEMA = "campaign-backend-benchmark-v1"
FIXTURES = ("opening", "first_chance", "japan_combat_movement", "round2_japan_combat_movement")


@dataclass(frozen=True)
class Config:
    backend: str = "cpu"
    mode: str = "positions"
    seeds: tuple[int, ...] = (1951,)
    repetitions: int = 2
    warmups: int = 1
    buckets: int = 2048
    max_transitions: int = 5000
    max_state_visits: int = 20
    seconds: float = 120.0
    cpu_budget: int = 3
    memory_bytes: int = 30_000_000_000

    def __post_init__(self):
        if self.backend != "cpu":
            raise ValueError(f"Backend {self.backend!r} is unavailable; only the CPU reference is implemented")
        if self.mode not in {"positions", "scripted_games"}:
            raise ValueError("Mode must be positions or scripted_games")
        if not self.seeds or len(set(self.seeds)) != len(self.seeds) or any(
                type(seed) is not int or not 0 <= seed < 2**64 for seed in self.seeds):
            raise ValueError("Seeds must be distinct unsigned 64-bit integers")
        for name in ("repetitions", "warmups", "buckets", "max_transitions", "max_state_visits"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.buckets < 2:
            raise ValueError("Numerical vocabulary needs at least two buckets")
        if type(self.cpu_budget) is not int or not 3 <= self.cpu_budget <= min(12, os.cpu_count() or 1):
            raise ValueError("CPU allowance must fit three reserved processes and at most 12 available cores")
        if type(self.memory_bytes) is not int or not 1_000_000_000 < self.memory_bytes <= 30_000_000_000:
            raise ValueError("Aggregate memory allowance must be above the 1 GB margin and at most 30 GB")
        if isinstance(self.seconds, bool) or not isinstance(self.seconds, (int, float)) or not math.isfinite(self.seconds) or self.seconds <= 0:
            raise ValueError("Wall allowance must be finite and positive")


class WorkloadLimit(RuntimeError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def atomic_json(path, value):
    from tools.supervise_campaign_training import atomic_json as write
    write(Path(path), value)


def public_checkpoint(serialized):
    """Keep every state/history/scheduler field; exclude only execution RNG."""
    value = json.loads(serialized)
    raw = json.loads(value["raw"])
    require(set(raw) == {"schema_version", "rules_id", "state", "random"}, "Unknown native checkpoint fields")
    del raw["random"]
    return {**value, "raw": raw}


def numeric_digest(value):
    """Hash full numerical arrays and reference metadata, without a JSON round trip."""
    result = hashlib.sha256()

    def block(tag, data):
        result.update(tag + struct.pack("<Q", len(data)) + data)

    def visit(item):
        if hasattr(item, "arrays") and hasattr(item, "packed_state"):
            packed = item.packed_state()
            visit({"arrays": item.arrays(), "identities": packed["identities"],
                   "references": packed["references"], "leaf_count": item.leaf_count,
                   "buckets": item.token_buckets})
        elif hasattr(item, "dtype") and hasattr(item, "shape") and hasattr(item, "tobytes"):
            block(b"A", str(item.dtype).encode()); visit(tuple(item.shape)); block(b"B", item.tobytes())
        elif isinstance(item, dict):
            result.update(b"D")
            for key in sorted(item):
                visit(key); visit(item[key])
            result.update(b"d")
        elif isinstance(item, (tuple, list)):
            result.update(b"L" + struct.pack("<Q", len(item)))
            for child in item:
                visit(child)
        elif item is None:
            result.update(b"N")
        elif isinstance(item, bool):
            result.update(b"Y" if item else b"Z")
        elif isinstance(item, int):
            block(b"I", str(item).encode())
        elif isinstance(item, float):
            result.update(b"F" + struct.pack("<d", item))
        elif isinstance(item, str):
            block(b"S", item.encode())
        else:
            raise TypeError(f"Unknown numerical input component {type(item).__name__}")
    visit(value)
    return result.hexdigest()


def descriptor(env, actions=None):
    from studies.shared.multiplayer_mcts import action_key
    actions = env.legal_actions() if actions is None else actions
    return {"key": env.planning_key(), "actor": env.current_decision_player(), "kind": env.decision_kind(),
            "terminal": env.is_terminal(), "action_ids": [action_key(action) for action in actions],
            "action_features_sha256": digest([action.features() for action in actions]),
            "clock": env.observation()["state"]["clock"]}


def check_terminal(env, rounds=3):
    state = env.observation()["state"]
    clock = state["clock"]
    require(env.is_terminal() and clock["completed_rounds"] == rounds and clock["round_index"] == rounds - 1 and
            clock["nation_index"] == 3 and clock["phase"] == "place_units" and
            clock["income_collected"] is True and clock["player_turn_serial"] == str(4 * rounds),
            f"Workload did not reach the genuine {rounds}-round terminal")
    require(state["completed_turns"] == {"ccp": rounds, "mongolia": rounds, "japan": rounds, "kmt": rounds},
            f"{rounds}-round terminal lacks all {4 * rounds} completed national turns")


def sampled_step(env):
    """Prepare authoritative action/request/outcome evidence outside measured replay."""
    from studies.campaign.baselines import baseline_distribution
    from studies.shared.multiplayer_mcts import action_key
    actions = env.legal_actions()
    before = descriptor(env, actions)
    cursor = env.raw.history_size()
    row = {"decision": before, "chance_request": env.chance_request(), "faces": None, "selected_action": None}
    if before["kind"] == "chance":
        env.resolve_chance()
        events = env.raw.history_since(cursor)
        chance = [event for event in events if event["kind"] == "chance"]
        require(len(chance) == 1, "Expected one recorded native chance outcome")
        row["faces"] = chance[0]["payload"]["outcome"]["faces"]
    else:
        require(actions, "Nonterminal policy decision has no legal choices")
        weights = baseline_distribution(env, actions)
        chosen = actions[max(range(len(actions)), key=weights.__getitem__)]
        row["selected_action"] = action_key(chosen)
        env.apply_action(chosen)
    row.update(after_key=env.planning_key(), history_events=env.raw.history_since(cursor), terminal=env.is_terminal())
    return row


def prepare(config, *, factory=None, deadline=None):
    from collections import Counter
    from studies.campaign.curriculum import make_env, task_manifest
    factory = factory or (lambda seed: make_env(seed, calendar_rounds=3))
    plans, fixtures, task = [], [], None
    for seed in config.seeds:
        env, steps, found = factory(seed), [], set()
        task = task_manifest(env) if task is None else task
        initial = env.serialize()
        visits = Counter({env.planning_key(): 1})
        while not env.is_terminal():
            if deadline is not None and time.monotonic() >= deadline:
                raise WorkloadLimit("preparation_wall_limit")
            if len(steps) >= config.max_transitions or visits[env.planning_key()] > config.max_state_visits:
                raise WorkloadLimit("preparation_transition_or_repetition_limit")
            clock, kind = env.observation()["state"]["clock"], env.decision_kind()
            labels = []
            if not steps:
                labels.append("opening")
            if kind == "chance":
                labels.append("first_chance")
            if kind == "combat_movement" and clock["nation_index"] == 2 and clock["round_index"] in (0, 1):
                labels.append("japan_combat_movement" if clock["round_index"] == 0 else "round2_japan_combat_movement")
            for label in labels:
                if label not in found:
                    serialized = env.serialize()
                    fixtures.append({"label": label, "seed": seed, "step": len(steps), "serialized": serialized,
                                     "serialized_sha256": hashlib.sha256(serialized.encode()).hexdigest()})
                    found.add(label)
            steps.append(sampled_step(env))
            visits[env.planning_key()] += 1
        check_terminal(env)
        require(found == set(FIXTURES), f"Seed {seed} did not reach all real benchmark positions: {sorted(found)}")
        plans.append({"seed": seed, "initial": initial, "steps": steps,
                      "steps_sha256": digest(steps), "final_public_checkpoint_sha256": digest(public_checkpoint(env.serialize())),
                      "terminal_returns": list(env.returns())})
    return {"schema": "campaign-backend-recorded-workload-v1", "task": task, "plans": plans, "fixtures": fixtures,
            "selection": "campaign-active-baseline-v2:balanced, sampled preparation outside measurement",
            "chance": "Every complete request, die face and reroll is recorded; replay uses explicit outcomes preserving execution RNG."}


class PlainDriver:
    def __init__(self, envs):
        self.envs = envs

    def scalar(self, lane):
        return self.envs[lane]

    def decisions(self, lanes):
        from studies.shared.multiplayer_mcts import action_key
        actions = [tuple(self.envs[lane].legal_actions()) for lane in lanes]
        return actions, [{"key": self.envs[lane].planning_key(), "actor": self.envs[lane].current_decision_player(),
                          "kind": self.envs[lane].decision_kind(), "terminal": self.envs[lane].is_terminal(),
                          "action_ids": [action_key(action) for action in menu]}
                         for lane, menu in zip(lanes, actions)]

    def numeric(self, lanes, batch):
        from studies.campaign.features import make_numeric_input
        return [make_numeric_input(self.envs[lane], actions, self.buckets) for lane, actions in zip(lanes, batch)]

    def apply(self, lanes, batch, selected):
        from studies.shared.multiplayer_mcts import action_key
        choices = []
        for actions, chosen in zip(batch, selected):
            matches = [action for action in actions if action_key(action) == chosen]
            require(len(matches) == 1, "Recorded action is absent from direct legal menu")
            choices.append(matches[0])
        for lane, action in zip(lanes, choices):
            self.envs[lane].apply_action(action)

    def requests(self, lanes, _batch):
        return [self.envs[lane].chance_request() for lane in lanes]

    def chance(self, lanes, _batch, rows):
        for lane, row in zip(lanes, rows):
            self.envs[lane].apply_chance_outcome(row["decision"]["key"], row["faces"])


class WrappedDriver:
    def __init__(self, envs, backend="cpu"):
        from studies.campaign.backends import create_backend
        self.backend = create_backend(envs, backend=backend)

    def scalar(self, lane):
        return self.backend.scalar(lane)

    def decisions(self, lanes):
        batch = self.backend.decision_batch(lanes)
        rows = [{"key": row.key, "actor": row.actor, "kind": row.kind, "terminal": row.terminal,
                 "action_ids": list(row.action_ids)} for row in self.backend.inspect_decisions(batch)]
        return batch, rows

    def numeric(self, _lanes, batch):
        return self.backend.numeric_inputs(batch, buckets=self.buckets)

    def inspect_numeric(self, buffer):
        return self.backend.inspect_numeric(buffer)

    def apply(self, _lanes, batch, selected):
        self.backend.apply_actions(batch, tuple(selected))

    def requests(self, _lanes, batch):
        return self.backend.inspect_chance_requests(batch)

    def chance(self, _lanes, batch, rows):
        self.backend.resolve_chance(batch, outcomes=tuple(row["faces"] for row in rows))


def replay(config, cases, *, wrapped, whole_games, factory=None, deadline=None):
    """Time actual wrapper operations; keep host witness materialization explicit."""
    from studies.campaign.curriculum import make_env
    factory = factory or (lambda seed: make_env(seed, calendar_rounds=3))
    setup_started = time.perf_counter()
    envs = [factory(case["seed"]) for case in cases]
    for env, case in zip(envs, cases):
        env.restore(case["initial"])
    initial_random = [json.loads(json.loads(env.serialize())["raw"])["random"] for env in envs]
    driver = WrappedDriver(envs, config.backend) if wrapped else PlainDriver(envs)
    driver.buckets = config.buckets
    setup_seconds = time.perf_counter() - setup_started
    offsets, transcripts, numeric = [0] * len(cases), [[] for _ in cases], [[] for _ in cases]
    timings = {name: 0.0 for name in ("decisions", "numeric_export", "actions", "chance")}
    started = time.perf_counter()
    while any(offset < len(case["steps"]) for offset, case in zip(offsets, cases)):
        if deadline is not None and time.monotonic() >= deadline:
            raise WorkloadLimit("measured_replay_wall_limit")
        for chance in (False, True):
            lanes = [lane for lane, (offset, case) in enumerate(zip(offsets, cases)) if offset < len(case["steps"])
                     and (case["steps"][offset]["decision"]["kind"] == "chance") is chance]
            if not lanes:
                continue
            expected = [cases[lane]["steps"][offsets[lane]] for lane in lanes]
            before = time.perf_counter(); batch, rows = driver.decisions(lanes)
            timings["decisions"] += time.perf_counter() - before
            for lane, row, planned in zip(lanes, rows, expected):
                reference = planned["decision"]
                require(all(row[key] == reference[key] for key in ("key", "actor", "kind", "terminal", "action_ids")),
                        f"Backend decision/menu mismatch at lane {lane}, step {offsets[lane]}")
                require(descriptor(driver.scalar(lane)) == reference, "Full host state/menu witness differs")
            if not whole_games:
                before = time.perf_counter(); buffer = driver.numeric(lanes, batch)
                timings["numeric_export"] += time.perf_counter() - before
                # This is an explicit diagnostic host inspection, outside timed
                # backend operations. Future device buffers need not expose it in training.
                inspected = driver.inspect_numeric(buffer) if wrapped else buffer
                for lane, item in zip(lanes, inspected):
                    numeric[lane].append(numeric_digest(item))
            cursors = [driver.scalar(lane).raw.history_size() for lane in lanes]
            if chance:
                requests = driver.requests(lanes, batch)
                require(list(requests) == [row["chance_request"] for row in expected], "Full chance request metadata differs")
            before = time.perf_counter()
            if chance:
                driver.chance(lanes, batch, expected)
            else:
                driver.apply(lanes, batch, [row["selected_action"] for row in expected])
            timings["chance" if chance else "actions"] += time.perf_counter() - before
            for lane, cursor, planned in zip(lanes, cursors, expected):
                env = driver.scalar(lane)
                require(env.planning_key() == planned["after_key"] and env.is_terminal() == planned["terminal"],
                        "Backend state/terminal witness differs")
                history = env.raw.history_since(cursor)
                require(history == planned["history_events"], "Actual chance/action event history differs")
                transcripts[lane].append({**planned, "after_key": env.planning_key(), "history_events": history})
                offsets[lane] += 1
    elapsed = time.perf_counter() - started
    final, final_audit_started = [], time.perf_counter()
    for lane, case in enumerate(cases):
        env = driver.scalar(lane)
        serialized = env.serialize()
        require(json.loads(json.loads(serialized)["raw"])["random"] == initial_random[lane],
                f"Explicit-outcome replay changed execution RNG at lane {lane}")
        if whole_games:
            check_terminal(env)
            require(list(env.returns()) == case["terminal_returns"], "Terminal returns differ")
            require(digest(public_checkpoint(serialized)) == case["final_public_checkpoint_sha256"],
                    "Full final public state/history/scheduler differs")
        final.append({"seed": case["seed"], "steps": offsets[lane], "terminal": env.is_terminal(),
                      "execution_rng_unchanged": True,
                      "trace_sha256": digest(transcripts[lane]), "numeric_input_sha256": numeric[lane]})
    return {"path": "wrapped_cpu" if wrapped else "plain_cpu", "setup_seconds": setup_seconds,
            "audited_replay_wall_seconds": elapsed, "operations_seconds": timings,
            "final_state_audit_seconds": time.perf_counter() - final_audit_started,
            "host_audit_and_driver_seconds": max(0.0, elapsed - sum(timings.values())), "lanes": final,
            "completed_three_round_games": len(cases) if whole_games else 0,
            "completed_rules_replay_games_per_hour": len(cases) * 3600 / elapsed if whole_games else None}


def compare_results(reference, actual):
    fields = {"lanes": bool(reference.get("lanes")) and reference.get("lanes") == actual.get("lanes"),
              "complete_games": reference.get("completed_three_round_games") is not None and
                  reference.get("completed_three_round_games") == actual.get("completed_three_round_games")}
    return {"matched": all(fields.values()), "fields": fields}


def provenance():
    import gwrl_cpp
    from studies.campaign.run import source_hashes
    native = Path(gwrl_cpp.__file__).resolve()
    def git(*args):
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    return {"commit": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
            "dirty": git("status", "--porcelain"), "runtime_source_sha256": source_hashes(),
            "backend_source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                      for path in sorted((ROOT / "studies/campaign/backends").rglob("*.py"))},
            "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "native": str(native), "native_sha256": hashlib.sha256(native.read_bytes()).hexdigest()}


def run_case(config, output, workload_output):
    started = time.perf_counter(); deadline = time.monotonic() + config.seconds
    from studies.campaign.backends import create_backend
    from studies.campaign.curriculum import make_env
    # Reject unsupported backends at both configuration and construction boundaries.
    info = asdict(create_backend([make_env(config.seeds[0], calendar_rounds=3)], backend=config.backend).info)
    report = {"schema": SCHEMA, "status": "running", "config": asdict(config), "backend": info,
              "provenance": provenance(), "startup_seconds": time.perf_counter() - started,
              "measurements": [], "timing_scope": "Rules replay only. Policy selection and sampled-dice preparation are outside measurement. Timed operations use actual backend calls; audited replay wall also includes disclosed host witness checks and driver overhead.",
              "limits": ["No GPU implementation, neural search, self-play or training is measured.",
                         "Explicit outcome replay preserves execution RNG; only that RNG field is excluded from public-state parity.",
                         "Numerical export is included only in positions mode. Scripted games measure rules/interface replay without neural input generation.",
                         "Whole-game throughput includes step witness auditing and Python driver overhead; final full-state verification and environment construction are timed separately.",
                         "Small defaults establish a benchmark scaffold, not training feasibility or strategic strength."]}
    atomic_json(output, report)
    try:
        before = time.perf_counter(); workload = prepare(config, deadline=deadline)
        report["preparation_seconds"] = time.perf_counter() - before
        atomic_json(workload_output, workload)
        report.update(workload_path=str(workload_output), workload_sha256=digest(workload), task=workload["task"])
        if config.mode == "scripted_games":
            cases = workload["plans"]
        else:
            lookup = {plan["seed"]: plan for plan in workload["plans"]}
            cases = [{"seed": fixture["seed"], "label": fixture["label"], "initial": fixture["serialized"],
                      "steps": [lookup[fixture["seed"]]["steps"][fixture["step"]]]} for fixture in workload["fixtures"]]
            report["frozen_positions"] = [{"label": fixture["label"], "seed": fixture["seed"],
                "serialized_sha256": fixture["serialized_sha256"],
                "decision": lookup[fixture["seed"]]["steps"][fixture["step"]]["decision"]}
                for fixture in workload["fixtures"]]
        before = time.perf_counter()
        for _ in range(config.warmups):
            for wrapped in (False, True):
                replay(config, cases, wrapped=wrapped, whole_games=config.mode == "scripted_games", deadline=deadline)
        report["warmup_seconds"] = time.perf_counter() - before
        for repetition in range(config.repetitions):
            reference = replay(config, cases, wrapped=False, whole_games=config.mode == "scripted_games", deadline=deadline)
            actual = replay(config, cases, wrapped=True, whole_games=config.mode == "scripted_games", deadline=deadline)
            parity = compare_results(reference, actual)
            require(parity["matched"], "Plain/wrapped CPU numerical or replay parity failed")
            report["measurements"].append({"repetition": repetition, "plain_cpu": reference, "wrapped_cpu": actual, "parity": parity})
            atomic_json(output, report)
        report["status"] = "completed"
    except WorkloadLimit as error:
        report["status"] = "truncated"; report["stop_reason"] = str(error)
    report["elapsed_worker_seconds"] = time.perf_counter() - started
    final_sources = provenance()
    stable_fields = ("commit", "runtime_source_sha256", "backend_source_sha256", "harness_sha256", "native_sha256")
    report["source_and_native_unchanged"] = all(report["provenance"][key] == final_sources[key] for key in stable_fields)
    if not report["source_and_native_unchanged"]:
        report["status"] = "source_changed"
    atomic_json(output, report)
    return report


def supervise(config, output, *, sampler=None):
    from tools.supervise_campaign_training import aggregate_rss, memory_metric, monitor_error_details
    output = Path(output).resolve(); workload_output = output.with_suffix(".workload.json")
    require(not output.exists() and not workload_output.exists(), "Choose new output paths; existing artifacts are preserved")
    output.parent.mkdir(parents=True, exist_ok=True)
    sampler = sampler or aggregate_rss
    started, peak, stopped, diagnostic = time.monotonic(), 0, None, None
    with tempfile.TemporaryDirectory(prefix="campaign-backend-") as directory:
        directory = Path(directory); settings = directory / "config.json"; progress = directory / "progress.json"
        atomic_json(settings, asdict(config))
        environment = {**os.environ, "PYTHONHASHSEED": "0", **{name: "1" for name in (
            "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")}}
        with (directory / "stdout").open("w") as stdout, (directory / "stderr").open("w") as stderr:
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--_worker", str(settings),
                "--output", str(progress), "--_workload-output", str(workload_output)], env=environment,
                cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                while process.poll() is None:
                    if time.monotonic() - started >= config.seconds:
                        stopped = "wall_limit"; break
                    try:
                        charged = sampler(process.pid)
                        peak = max(peak, charged)
                    except (OSError, ValueError, subprocess.SubprocessError) as error:
                        if process.poll() is not None:
                            break
                        stopped = "memory_monitor_failure"
                        diagnostic = monitor_error_details(error, "aggregate_memory_sample", root_pid=process.pid)
                        break
                    if charged >= config.memory_bytes - 1_000_000_000:
                        stopped = "memory_limit"; break
                    time.sleep(.1)
            finally:
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                process.wait(timeout=5)
        report = json.loads(progress.read_text()) if progress.exists() else {"schema": SCHEMA, "config": asdict(config)}
        if stopped is not None:
            report["status"] = stopped
        elif (report.get("status") not in {"completed", "truncated", "source_changed"} or
              (process.returncode != 0 and not (process.returncode == 2 and report.get("status") in {
                  "truncated", "source_changed"}))):
            report["status"] = "worker_error"; report["worker_error"] = (directory / "stderr").read_text()[-4000:]
        report["watchdog"] = {"elapsed_seconds": time.monotonic() - started, "sampled_peak_charged_bytes": peak,
            "memory_limit_bytes": config.memory_bytes, "stop_threshold_bytes": config.memory_bytes - 1_000_000_000,
            "memory_metric": memory_metric(), "cpu_budget": config.cpu_budget, "worker_threads": 1,
            "reserved_processes": 3, "scope": "Supervisor, worker and all descendants including sampling overhead; sampled guard, not a kernel memory cap.",
            "worker_returncode": process.returncode, "monitor_failure": diagnostic}
        if report["status"] != "completed":
            report["complete_matched_throughput_claim_valid"] = False
        else:
            report["complete_matched_throughput_claim_valid"] = True
        atomic_json(output, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backend", default="cpu")
    parser.add_argument("--mode", default="positions", choices=("positions", "scripted_games"))
    parser.add_argument("--seeds", default="1951")
    for name, default in asdict(Config()).items():
        if name not in {"backend", "mode", "seeds", "seconds"}:
            parser.add_argument("--" + name.replace("_", "-"), type=int, default=default)
    parser.add_argument("--seconds", type=float, default=120.)
    parser.add_argument("--_worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--_workload-output", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args._worker:
            values = json.loads(args._worker.read_text()); values["seeds"] = tuple(values["seeds"])
            report = run_case(Config(**values), args.output, args._workload_output)
        else:
            values = {name: getattr(args, name) for name in asdict(Config())}
            values["seeds"] = tuple(int(seed) for seed in args.seeds.split(","))
            report = supervise(Config(**values), args.output)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps({"status": report["status"], "output": str(args.output.resolve())}), flush=True)
    return 0 if report["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
