#!/usr/bin/env python3
"""Run a durable initial-evaluation / training / final-evaluation experiment.

Use ``python tools/run_three_round_experiment.py --plan /absolute/plan.json``.
Reissue the same command to resume. The immutable plan's absolute deadline never
resets. Finished evaluation seeds are reused; unfinished training games resume
from the runner checkpoint. No successful result is inferred from an unfinished
game or failed worker. The JSON plan is produced and reviewed before launch.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.supervise_campaign_training import (  # noqa: E402
    SupervisorConfig, aggregate_rss, atomic_json, exclusive_lock, process_group_alive,
    validate_training_arguments, memory_metric,
)

SCHEMA = "campaign-three-round-experiment-v1"
STAGES = ("initialize", "initial_evaluation", "training", "freeze_checkpoint", "final_evaluation")
HELDOUT_SEEDS = (40009, 40013, 40031, 40037, 40039, 40063, 40087, 40093)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def read_json(path: Path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def argument_value(arguments, name):
    matches = [index for index, value in enumerate(arguments) if value == name or value.startswith(name + "=")]
    if len(matches) != 1:
        raise ValueError(f"Supply exactly one {name}")
    index = matches[0]
    try:
        return arguments[index].split("=", 1)[1] if "=" in arguments[index] else arguments[index + 1]
    except IndexError as error:
        raise ValueError(f"Missing value for {name}") from error


def validate_plan(plan: dict):
    required = {"run_root", "working_directory", "python", "deadline_epoch", "training_arguments"}
    if not isinstance(plan, dict) or required - plan.keys():
        raise ValueError("Experiment plan is missing required fields")
    for key in ("run_root", "working_directory", "python"):
        if not isinstance(plan[key], str) or not Path(plan[key]).is_absolute():
            raise ValueError(f"Plan {key} must be an absolute path")
    if not isinstance(plan["deadline_epoch"], (int, float)) or not math.isfinite(plan["deadline_epoch"]):
        raise ValueError("Plan deadline must be finite")
    if plan["deadline_epoch"] > time.time() + 10 * 3600 + 1:
        raise ValueError("Plan deadline exceeds the pipeline's ten-hour hard ceiling")
    arguments = plan["training_arguments"]
    if not isinstance(arguments, list) or not all(isinstance(item, str) for item in arguments):
        raise ValueError("Training arguments must be an explicit string list")
    validate_training_arguments(arguments, SupervisorConfig(seconds=1))
    if argument_value(arguments, "--calendar-rounds") != "3" or "--full-campaign" in arguments:
        raise ValueError("This experiment requires the explicit three-round horizon")
    if "--complete-episodes" not in arguments or "--no-complete-episodes" in arguments:
        raise ValueError("This experiment requires complete-episode training")
    for key, default in (("final_eval_reserve_seconds", 3600), ("initial_eval_seconds", 1800),
                         ("shutdown_seconds", 180), ("initialize_seconds", 600)):
        value = plan.get(key, default)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"Plan {key} must be positive and finite")
    seeds = plan.get("heldout_seeds", list(HELDOUT_SEEDS))
    if not isinstance(seeds, list) or not seeds or len(set(seeds)) != len(seeds) or any(
            type(seed) is not int or not 0 <= seed < 2**64 for seed in seeds):
        raise ValueError("Held-out seeds must be unique unsigned integers")
    if "--record-replay" in arguments:
        raise ValueError("Resumable training cannot use the fresh-run-only replay writer")
    if "expected_training_episodes" in plan:
        expected = plan["expected_training_episodes"]
        if type(expected) is not int or expected <= 0:
            raise ValueError("Expected training episodes must be a positive integer")
        if int(argument_value(arguments, "--max-episodes")) != expected:
            raise ValueError("Expected training episodes must match --max-episodes")
        roots = int(argument_value(arguments, "--parallel-envs"))
        if int(argument_value(arguments, "--batches")) < math.ceil(expected / roots):
            raise ValueError("Training batch allowance cannot complete the expected episodes")
        start = plan.get("starting_training_episodes", 0)
        start_updates = plan.get("starting_training_updates", 0)
        if type(start) is not int or not 0 <= start < expected:
            raise ValueError("Starting training episodes must be a nonnegative offset below the total goal")
        if type(start_updates) is not int or start_updates < 0 or start_updates != math.ceil(start / roots):
            raise ValueError("Starting learning updates must match the completed collection batches")
        if (start or start_updates) and plan.get("initial_model_generation") != start_updates:
            raise ValueError("Continuation baseline generation must match the starting learning updates")
    elif "starting_training_episodes" in plan or "starting_training_updates" in plan:
        raise ValueError("Continuation offsets require an expected total training episode count")
    if "initial_model_generation" in plan and (type(plan["initial_model_generation"]) is not int
                                                or plan["initial_model_generation"] < 0):
        raise ValueError("Initial model generation must be a nonnegative integer")
    if "require_terminal_evaluation" in plan and type(plan["require_terminal_evaluation"]) is not bool:
        raise ValueError("require_terminal_evaluation must be boolean")
    if int(argument_value(arguments, "--threads")) + int(argument_value(arguments, "--parallel-envs")) + 4 > 12:
        raise ValueError("Tensor workers, search roots and four coordinators exceed 12 cores")
    memory = plan.get("memory_bytes", 26_000_000_000)
    if type(memory) is not int or not 1_000_000_000 < memory <= 30_000_000_000:
        raise ValueError("Plan memory allowance must fit 30 GB with a safety margin")
    poll = plan.get("poll_seconds", 0.5)
    if not isinstance(poll, (int, float)) or not math.isfinite(poll) or not 0 < poll <= 5:
        raise ValueError("Polling interval must be finite and between zero and five seconds")


def verify_runtime_manifest(plan):
    """Validate every pinned runtime byte, including the compiled game engine."""
    path, expected = plan.get("runtime_manifest_path"), plan.get("runtime_manifest_sha256")
    if path is None and expected is None:
        return None
    if not isinstance(path, str) or not Path(path).is_absolute() or not isinstance(expected, str):
        raise ValueError("Runtime manifest path and SHA-256 must both be supplied")
    manifest_path = Path(path)
    if digest(manifest_path) != expected:
        raise ValueError("Frozen runtime manifest changed")
    files = read_json(manifest_path).get("files")
    if not isinstance(files, dict) or not files or not any(name.endswith((".so", ".dylib")) for name in files):
        raise ValueError("Runtime manifest must include all files and the native extension")
    runtime = Path(plan["working_directory"]).resolve()
    actual = {str(path.relative_to(runtime)) for path in runtime.rglob("*")
              if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"}
    if set(files) != actual:
        raise ValueError("Frozen runtime file inventory changed")
    for name, value in files.items():
        path = (runtime / name).resolve()
        if not path.is_relative_to(runtime) or not isinstance(value, str) or digest(path) != value:
            raise ValueError(f"Frozen runtime file changed: {name}")
    return expected


def _terminal_three_round_clock(clock) -> bool:
    return (isinstance(clock, dict) and clock.get("completed_rounds") == 3
            and clock.get("round_index") == 2 and clock.get("nation_index") == 3
            and clock.get("phase") == "place_units" and clock.get("income_collected") is True)


def training_completion_contract(plan: dict, manifest: dict) -> dict:
    """Check exact completed work from durable metadata, without loading replay."""
    if "expected_training_episodes" not in plan:
        return {"required": False, "complete": True}
    expected = plan["expected_training_episodes"]
    roots = int(argument_value(plan["training_arguments"], "--parallel-envs"))
    start = plan.get("starting_training_episodes", 0)
    start_updates = plan.get("starting_training_updates", 0)
    expected_updates = start_updates + math.ceil((expected - start) / roots)
    counters = manifest.get("counters", {})
    updates = manifest.get("runner", {}).get("updates", [])
    errors = []
    if counters.get("episodes") != expected:
        errors.append(f"Expected {expected} completed training games; found {counters.get('episodes')}")
    if counters.get("updates") != expected_updates or counters.get("batches") != expected_updates:
        errors.append(f"Expected {expected_updates} completed learning batches and updates")
    episodes = []
    if not isinstance(updates, list) or len(updates) != expected_updates:
        errors.append(f"Expected {expected_updates} durable learning records")
    if isinstance(updates, list):
        for update in updates:
            rollout = update.get("rollout") if isinstance(update, dict) else None
            if not isinstance(rollout, dict) or type(rollout.get("bootstrap_samples")) is not int or rollout["bootstrap_samples"] != 0:
                errors.append("A learning record has missing or nonzero bootstrap samples")
            batch_episodes = update.get("episodes", []) if isinstance(update, dict) else []
            if not isinstance(batch_episodes, list):
                errors.append("A learning record has invalid game records")
                continue
            episodes.extend(batch_episodes)
    if len(episodes) != expected or any(not isinstance(episode, dict) or episode.get("terminal") is not True
            or not _terminal_three_round_clock(episode.get("clock")) for episode in episodes):
        errors.append("Training records do not describe exactly the required three-round terminal games")
    return {"required": True, "complete": not errors, "expected_episodes": expected,
            "actual_episodes": counters.get("episodes"), "expected_updates": expected_updates,
            "actual_updates": counters.get("updates"), "starting_episodes": start,
            "expected_additional_episodes": expected - start,
            "additional_episodes_completed": counters.get("episodes", 0) - start,
            "starting_updates": start_updates,
            "additional_updates_completed": counters.get("updates", 0) - start_updates,
            "errors": errors}


def evaluation_completion_contract(plan: dict, directory: Path, *, final: bool) -> dict:
    """A complete seed list alone is insufficient: every game must be terminal."""
    if not plan.get("require_terminal_evaluation", False):
        return {"required": False, "complete": True}
    report, contract = read_json(directory / "report.json", {}), read_json(directory / "plan.json", {})
    seeds = plan.get("heldout_seeds", list(HELDOUT_SEEDS))
    modes = ("network_only", "search")
    expected = {(mode, seed) for mode in modes for seed in seeds}
    errors, seen = [], set()
    contract_sha = fingerprint(contract)
    evaluation = contract.get("evaluation", {})
    if evaluation.get("seeds") != seeds or evaluation.get("modes") != list(modes):
        errors.append("Evaluation contract has different held-out seeds or modes")
    if report.get("status") != "completed" or report.get("contract_sha256") != contract_sha:
        errors.append("Evaluation report is incomplete or has a different contract")
    records = report.get("records", [])
    if not isinstance(records, list):
        records = []
        errors.append("Evaluation records must be a list")
    for row in records:
        if not isinstance(row, dict):
            errors.append("Invalid evaluation record")
            continue
        pair = row.get("mode"), row.get("seed")
        if pair not in expected or pair in seen or row.get("contract_sha256") != contract_sha:
            errors.append("Evaluation has a foreign, duplicate or mismatched seed/mode record")
        seen.add(pair)
        result = row.get("result", {})
        result = result if isinstance(result, dict) else {}
        games = result.get("games", [])
        game = games[0] if isinstance(games, list) and len(games) == 1 and isinstance(games[0], dict) else {}
        dadao = game.get("dadao_chinese_home_country", {})
        if (result.get("territorial_tracking_schema") != "campaign-national-chinese-possession-tracking-v2"
                or not isinstance(dadao, dict) or dadao.get("nation") != "dadao" or dadao.get("terminal") is not True
                or not isinstance(dadao.get("at_stop"), dict) or not isinstance(dadao.get("newly_held"), dict)
                or not isinstance(dadao.get("events"), list)):
            errors.append(f"Evaluation {pair} lacks the current separate Dadao territorial diagnostics")
        returns = game.get("observed_terminal_returns")
        valid_returns = (isinstance(returns, list) and len(returns) == 3
                         and all(type(value) in (int, float) and math.isfinite(value) for value in returns))
        if (game.get("seed") != row.get("seed") or game.get("terminal") is not True
                or game.get("truncated") is not False or game.get("stop_reason") != "terminal"
                or not _terminal_three_round_clock(game.get("clock"))
                or game.get("completed_turns_at_stop") != {"ccp": 3, "mongolia": 3, "japan": 3, "kmt": 3}
                or not valid_returns or result.get("terminal_games") != 1 or result.get("truncated_games") != 0):
            errors.append(f"Evaluation {pair} did not reach its genuine three-round terminal")
    if seen != expected or len(records) != len(expected):
        errors.append(f"Expected exactly {len(expected)} unique held-out evaluation games")
    for mode in modes:
        summary = report.get("by_mode", {}).get(mode, {})
        if summary.get("terminal_games") != len(seeds) or summary.get("truncated_games") != 0:
            errors.append(f"Evaluation {mode} terminal totals differ from the held-out set")
        paired = report.get("paired_comparison") or {}
        if final and paired.get("by_mode", {}).get(mode, {}).get("complete_pairs") != len(seeds):
            errors.append(f"Final evaluation {mode} lacks a complete paired comparison")
    return {"required": True, "complete": not errors, "expected_games": len(expected),
            "recorded_games": len(records), "errors": errors}


def _event(state: dict, kind: str, **details):
    state["events"].append({"kind": kind, "epoch": time.time(), **details})


def freeze_checkpoint(source: Path, target: Path) -> str:
    """An evaluation sees one immutable inode even after training is resumed."""
    if target.exists():
        return digest(target)
    if not source.is_file():
        raise ValueError("No complete training checkpoint is available for evaluation")
    descriptor, temporary = tempfile.mkstemp(prefix=".evaluation-checkpoint-", dir=target.parent)
    os.close(descriptor)
    os.unlink(temporary)
    try:
        try:
            os.link(source, temporary)
        except OSError:
            shutil.copyfile(source, temporary)
            with open(temporary, "rb") as handle:
                os.fsync(handle.fileno())
        os.replace(temporary, target)
        directory = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return digest(target)


def _known_groups(root_pid: int, known: set[int]) -> set[int]:
    result = subprocess.run(["ps", "-axo", "pid=,ppid=,pgid="], capture_output=True,
                            text=True, check=True, timeout=5)
    rows = [tuple(map(int, line.split())) for line in result.stdout.splitlines() if line.strip()]
    descendants = {root_pid}
    while True:
        expanded = descendants | {pid for pid, parent, group in rows
                                  if parent in descendants or group in known}
        if expanded == descendants:
            break
        descendants = expanded
    return known | {group for pid, _, group in rows if pid in descendants and group != os.getpgrp()}


def _signal_group(group: int, number):
    try:
        os.killpg(group, number)
    except ProcessLookupError:
        pass


@contextmanager
def prevent_sleep(enabled: bool, state: dict):
    process = None
    if enabled and sys.platform == "darwin" and shutil.which("caffeinate"):
        process = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _event(state, "sleep_prevention_started", pid=process.pid)
    try:
        yield
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


class Experiment:
    def __init__(self, plan: dict, *, rss_sampler=aggregate_rss, command_builder=None, guardian_starter=None):
        validate_plan(plan)
        self.plan = plan
        self.root = Path(plan["run_root"])
        self.runtime = Path(plan["working_directory"])
        self.training = self.root / "training"
        self.path = self.root / "pipeline-state.json"
        self.rss_sampler = rss_sampler
        self.command_builder = command_builder
        self.guardian_starter = guardian_starter
        self.stopped = None
        self.grace = plan.get("shutdown_seconds", 180)
        self.deadline = plan["deadline_epoch"]
        self.memory_bytes = plan.get("memory_bytes", 26_000_000_000)
        self.poll_seconds = plan.get("poll_seconds", 0.5)
        self.state = None
        self.guardian_process = None

    def ensure_guardian(self):
        if self.guardian_starter is not None:
            return self.guardian_starter(self)
        lock = self.root / "guardian.lock"
        with lock.open("a+") as handle:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                guardian = read_json(self.root / "guardian-state.json", {})
                if guardian.get("deadline_epoch") != self.deadline or guardian.get("status") not in {"watching", "stopping"}:
                    raise RuntimeError("Guardian lock is held without a matching active deadline record")
                _event(self.state, "deadline_guardian_reused")
                return
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        guardian_plan = self.root / "pipeline-plan.json"
        if guardian_plan.exists():
            if read_json(guardian_plan) != self.plan:
                raise ValueError("Guardian plan differs from the immutable experiment plan")
        else:
            atomic_json(guardian_plan, self.plan)
        logs = self.root / "logs"
        logs.mkdir(exist_ok=True)
        with (logs / "guardian.stdout.log").open("a") as stdout, (logs / "guardian.stderr.log").open("a") as stderr:
            process = subprocess.Popen([self.plan["python"], str(self.runtime / "tools/campaign_deadline_guardian.py"),
                                        "--plan", str(guardian_plan)], cwd=self.runtime, stdout=stdout,
                                       stderr=stderr, start_new_session=True,
                                       env={**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
                                            "MKL_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"})
        self.guardian_process = process
        self.state["guardian_pid"] = process.pid
        self.persist()
        # Confirm the independent process owns its lock before any game starts.
        ready_until = time.monotonic() + 5
        while time.monotonic() < ready_until:
            if process.poll() is not None:
                raise RuntimeError("Independent deadline guardian failed to start")
            with lock.open("a+") as handle:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    guardian = read_json(self.root / "guardian-state.json", {})
                    if guardian.get("guardian_pid") == process.pid and guardian.get("deadline_epoch") == self.deadline:
                        _event(self.state, "deadline_guardian_started", pid=process.pid)
                        return
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            time.sleep(0.05)
        process.terminate()
        process.wait(timeout=5)
        raise RuntimeError("Independent deadline guardian did not acquire its lock")

    def persist(self):
        self.state["remaining_global_seconds"] = max(0.0, self.deadline - time.time())
        atomic_json(self.path, self.state)

    def request_stop(self, number, _frame):
        self.stopped = signal.Signals(number).name

    def evaluation_source(self, *, initial: bool) -> Path:
        """New runs evaluate small policy exports; old runs keep their contract.

        An explicitly declared export must exist. Falling back to an older full
        checkpoint after an export error could silently evaluate different weights.
        """
        manifest = read_json(self.training / "manifest.json", {})
        metadata = manifest.get("latest_model_export")
        if metadata is None:
            if initial and self.plan.get("initial_model_generation", 0) != 0:
                raise ValueError("Continuation initialization did not publish its starting-generation model export")
            return self.training / ("initial.pt" if initial else "checkpoint.pt")
        if not isinstance(metadata, dict) or not isinstance(metadata.get("path"), str):
            raise ValueError("Invalid model export metadata in training manifest")
        initial_generation = self.plan.get("initial_model_generation", 0)
        candidate = (self.training / f"models/generation-{initial_generation:06d}.pt" if initial
                     else self.training / metadata["path"])
        if initial and initial_generation != 0 and metadata.get("generation") != initial_generation:
            raise ValueError("Initial evaluation generation differs from the continuation's starting networks")
        if not candidate.resolve().is_relative_to(self.training.resolve()):
            raise ValueError("Model export must belong to this training run")
        if not candidate.is_file():
            raise ValueError("Declared model export is missing; refusing older recovery weights")
        if not initial and candidate.stat().st_size != metadata.get("bytes"):
            raise ValueError("Declared model export size differs from training manifest")
        return candidate

    def command(self, stage: str, deadline: float):
        if self.command_builder is not None:
            return self.command_builder(stage, deadline, self)
        python, arguments = self.plan["python"], self.plan["training_arguments"]
        if stage == "initialize":
            command = [python, "-m", "studies.campaign.run", "train", "--run-dir", str(self.training),
                       *arguments, "--stop-after-waves", "1"]
            for filename in ("checkpoint.pt", "initial.pt"):
                if (self.training / filename).exists():
                    command.extend(["--resume", str(self.training / filename)])
                    break
            return command
        if stage == "training":
            return [python, str(self.runtime / "tools/supervise_campaign_training.py"),
                    "--control-dir", str(self.root / "training-control"), "--run-dir", str(self.training),
                    "--working-directory", str(self.runtime), "--seconds", str(self.state["training_seconds"]),
                    "--shutdown-seconds", str(self.grace), "--memory-bytes", str(self.memory_bytes),
                    "--poll-seconds", str(self.poll_seconds), "--adopt-checkpoint", "--", *arguments]
        initial = stage == "initial_evaluation"
        command = [python, str(self.runtime / "tools/evaluate_three_round_campaign.py"),
                   "--checkpoint", str(self.evaluation_source(initial=True) if initial
                                       else self.root / "evaluation-checkpoint.pt"),
                   "--output-dir", str(self.root / ("evaluation-initial" if initial else "evaluation-final")),
                   "--seeds", ",".join(map(str, self.plan.get("heldout_seeds", HELDOUT_SEEDS))),
                   "--modes", "network_only,search", "--simulations", "16", "--max-depth", "16",
                   "--max-transitions", "5000", "--max-state-visits", "20",
                   "--wall-seconds", str(max(0.01, deadline - time.time() - self.grace))]
        if not initial:
            command.extend(["--compare-to", str(self.root / "evaluation-initial")])
        return command

    def run_worker(self, stage, command, deadline, lock_handle):
        index = len(self.state["attempts"]) + 1
        logs = self.root / "logs"
        logs.mkdir(exist_ok=True)
        record = {"number": index, "stage": stage, "command": command, "deadline_epoch": deadline,
                  "stdout": f"logs/{index:03d}-{stage}.stdout.log", "stderr": f"logs/{index:03d}-{stage}.stderr.log"}
        self.state["attempts"].append(record)
        self.state["status"] = "running"
        self.persist()
        environment = {**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "4",
                       "MKL_NUM_THREADS": "4", "VECLIB_MAXIMUM_THREADS": "4",
                       "NUMEXPR_NUM_THREADS": "1", "PYTHONHASHSEED": "0"}
        groups = set()
        process = None
        with (self.root / record["stdout"]).open("a") as stdout, (self.root / record["stderr"]).open("a") as stderr:
            try:
                process = subprocess.Popen(command, cwd=self.runtime, env=environment, stdout=stdout, stderr=stderr,
                                           start_new_session=True, pass_fds=(lock_handle.fileno(),))
                groups.add(process.pid)
                self.state["child_process_group"] = process.pid
                self.state["known_process_groups"] = sorted(groups)
                self.persist()
                stopping = None
                stop_at = None
                while process.poll() is None:
                    now = time.time()
                    resident = None
                    monitor_failed = False
                    try:
                        resident = self.rss_sampler(process.pid)
                        self.state["aggregate_sampled_peak_rss_bytes"] = max(self.state["aggregate_sampled_peak_rss_bytes"], resident)
                        groups = _known_groups(process.pid, groups)
                        self.state["known_process_groups"] = sorted(groups)
                    except (OSError, ValueError, subprocess.SubprocessError):
                        monitor_failed = process.poll() is None
                    if resident is not None and resident >= self.memory_bytes:
                        stopping = "memory_limit"
                        record["forced_kill"] = True
                        for group in groups:
                            _signal_group(group, signal.SIGKILL)
                    if stopping is None:
                        if resident is not None and resident >= self.memory_bytes - 1_000_000_000:
                            stopping = "memory_limit"
                        if monitor_failed:
                            stopping = "memory_monitor_failure"
                        if self.stopped:
                            stopping = "interrupted"
                        elif now >= deadline - self.grace and stopping is None:
                            stopping = "wall_limit"
                        if stopping:
                            stop_at = now
                            _event(self.state, "graceful_stop_requested", stage=stage, reason=stopping)
                            _signal_group(process.pid, signal.SIGTERM)
                    elif stop_at is not None and now >= min(deadline, stop_at + self.grace):
                        record["forced_kill"] = True
                        for group in groups:
                            _signal_group(group, signal.SIGKILL)
                    self.persist()
                    time.sleep(min(self.poll_seconds, max(0.01, deadline - time.time())))
                process.wait()
                groups = _known_groups(process.pid, groups)
                for group in groups:
                    if process_group_alive(group):
                        _signal_group(group, signal.SIGKILL)
                        record.setdefault("orphan_groups_terminated", []).append(group)
                record.update(returncode=process.returncode, stop_reason=stopping)
                self.state["child_process_group"] = None
                self.persist()
                return record
            finally:
                if process is not None and process.poll() is None:
                    _signal_group(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=max(0.01, min(self.grace, deadline - time.time())))
                    except subprocess.TimeoutExpired:
                        for group in groups:
                            _signal_group(group, signal.SIGKILL)
                        process.wait(timeout=5)
                    self.state["child_process_group"] = None
                    self.persist()

    def stage_deadline(self, stage):
        if stage not in self.state["stage_deadlines"]:
            now = time.time()
            if stage == "initialize":
                deadline = min(self.deadline, now + self.plan.get("initialize_seconds", 600))
            elif stage == "initial_evaluation":
                deadline = min(self.deadline, now + self.plan.get("initial_eval_seconds", 1800))
            elif stage == "training":
                allowance = max(0.0, self.deadline - now - self.plan.get("final_eval_reserve_seconds", 3600) - self.grace)
                self.state["training_seconds"] = allowance
                deadline = now + allowance
            else:
                deadline = self.deadline
            self.state["stage_deadlines"][stage] = deadline
            self.persist()
        return self.state["stage_deadlines"][stage]

    def fail(self, reason, record=None):
        self.state["status"] = "attention_required"
        _event(self.state, "attention_required", reason=reason, attempt=record)
        self.persist()
        return self.state

    def run(self):
        self.root.mkdir(parents=True, exist_ok=True)
        with exclusive_lock(self.root / "pipeline.lock") as lock_handle:
            if self.path.exists():
                self.state = read_json(self.path)
                if self.state.get("schema") != SCHEMA or self.state.get("plan_sha256") != fingerprint(self.plan):
                    raise ValueError("Experiment plan changed; refusing to mix budgets, runtime or results")
                if process_group_alive(self.state.get("child_process_group")):
                    raise RuntimeError("A previous pipeline child is alive; refusing a duplicate experiment")
                if self.state["status"] in {"completed", "budget_exhausted"}:
                    return self.state
                _event(self.state, "pipeline_resumed", prior_status=self.state["status"])
            else:
                self.state = {"schema": SCHEMA, "plan": self.plan, "plan_sha256": fingerprint(self.plan),
                              "status": "initialized", "stage_index": 0, "stage_deadlines": {}, "commands": {},
                              "attempts": [], "events": [], "child_process_group": None,
                              "aggregate_sampled_peak_rss_bytes": 0, "known_process_groups": [],
                              "memory_metric": memory_metric(),
                              "resource_scope": "Pipeline, independent guardian, sleep prevention, supervisor and full child process tree; "
                                                + memory_metric() + "; sampled with 1 GB safety margin",
                              "deadline_scope": "Absolute plan deadline includes downtime; stage deadlines are persisted and never reset"}
                if "expected_training_episodes" in self.plan or self.plan.get("require_terminal_evaluation", False):
                    self.state["goal_achieved"] = False
                _event(self.state, "pipeline_initialized")
            self.state["pipeline_pid"] = os.getpid()
            try:
                self.state["runtime_manifest_sha256"] = verify_runtime_manifest(self.plan)
            except (OSError, ValueError) as error:
                return self.fail(f"Runtime verification failed: {error}")
            self.persist()
            handlers = {number: signal.signal(number, self.request_stop)
                        for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
            try:
                if time.time() >= self.deadline:
                    self.state["status"] = "budget_exhausted"
                    self.persist()
                    return self.state
                self.ensure_guardian()
                with prevent_sleep(self.plan.get("prevent_sleep", True), self.state):
                    while self.state["stage_index"] < len(STAGES):
                        stage = STAGES[self.state["stage_index"]]
                        self.state["stage"] = stage
                        if self.stopped:
                            self.state["status"] = "interrupted"
                            self.persist()
                            return self.state
                        if time.time() >= self.deadline:
                            self.state["status"] = "budget_exhausted"
                            self.persist()
                            return self.state
                        if stage == "freeze_checkpoint":
                            source = self.evaluation_source(initial=False)
                            value = freeze_checkpoint(source, self.root / "evaluation-checkpoint.pt")
                            old = self.state.get("evaluation_checkpoint_sha256")
                            if old is not None and value != old:
                                return self.fail("Frozen evaluation checkpoint changed")
                            self.state["evaluation_checkpoint_sha256"] = value
                            self.state["evaluation_model_source"] = str(source.relative_to(self.root))
                            self.state["stage_index"] += 1
                            self.persist()
                            continue
                        deadline = self.stage_deadline(stage)
                        checkpoint_ready = (self.training / "initial.pt").exists() and (self.training / "checkpoint.pt").exists()
                        if stage == "initialize" and checkpoint_ready:
                            _event(self.state, "initial_checkpoints_reused")
                        elif time.time() >= deadline - self.grace:
                            if stage == "initialize":
                                return self.fail("Initialization allowance expired before complete checkpoints were saved")
                            if stage == "initial_evaluation" and not (self.root / "evaluation-initial/plan.json").is_file():
                                return self.fail("Initial evaluation allowance expired before a comparison plan was saved")
                            _event(self.state, "stage_allowance_exhausted", stage=stage)
                        else:
                            if stage not in self.state["commands"] or stage == "initialize":
                                self.state["commands"][stage] = self.command(stage, deadline)
                                self.persist()
                            record = self.run_worker(stage, self.state["commands"][stage], deadline, lock_handle)
                            if record.get("stop_reason") == "interrupted" or self.stopped:
                                self.state["status"] = "interrupted"
                                self.persist()
                                return self.state
                            if record.get("stop_reason") in {"memory_limit", "memory_monitor_failure"}:
                                return self.fail(record["stop_reason"], record["number"])
                            if stage == "initialize":
                                if record["returncode"] not in (0, 130) or not all((self.training / filename).is_file()
                                                                                  for filename in ("initial.pt", "checkpoint.pt")):
                                    return self.fail("Initialization failed or did not save complete checkpoints", record["number"])
                            elif stage == "training":
                                status = read_json(self.root / "training-control/state.json", {}).get("status")
                                forced_wall_stop = record.get("forced_kill") and record.get("stop_reason") == "wall_limit" and (self.training / "checkpoint.pt").is_file()
                                if forced_wall_stop:
                                    _event(self.state, "training_shutdown_cut_off", checkpoint="last complete atomic checkpoint")
                                if status not in {"completed", "time_budget_exhausted", "interrupted"} and not forced_wall_stop:
                                    return self.fail(f"Training stopped with {status or 'no durable supervisor status'}", record["number"])
                                if record["returncode"] not in (0, 130) and not (record.get("forced_kill") and record.get("stop_reason") == "wall_limit"):
                                    return self.fail("Training supervisor failed", record["number"])
                            elif record["returncode"] not in (0, 130) and not (record.get("forced_kill") and record.get("stop_reason") == "wall_limit"):
                                return self.fail("Evaluation worker failed", record["number"])
                            elif stage == "initial_evaluation" and not (self.root / "evaluation-initial/plan.json").is_file():
                                return self.fail("Initial evaluation did not save a compatible comparison plan", record["number"])
                        if stage == "initial_evaluation" and self.plan.get("require_terminal_evaluation", False):
                            check = evaluation_completion_contract(self.plan, self.root / "evaluation-initial", final=False)
                            self.state.setdefault("completion_contracts", {})[stage] = check
                            if not check["complete"]:
                                return self.fail("Initial held-out evaluation did not complete: " + "; ".join(check["errors"][:3]))
                        if stage == "training" and "expected_training_episodes" in self.plan:
                            check = training_completion_contract(self.plan, read_json(self.training / "manifest.json", {}))
                            self.state.setdefault("completion_contracts", {})[stage] = check
                            if not check["complete"]:
                                _event(self.state, "training_goal_incomplete", contract=check)
                        self.state["stage_index"] += 1
                        self.persist()
                    report = read_json(self.root / "evaluation-final/report.json", {})
                    complete = report.get("status") == "completed"
                    if "expected_training_episodes" in self.plan or self.plan.get("require_terminal_evaluation", False):
                        checks = {"training": training_completion_contract(
                            self.plan, read_json(self.training / "manifest.json", {})),
                            "initial_evaluation": evaluation_completion_contract(
                                self.plan, self.root / "evaluation-initial", final=False),
                            "final_evaluation": evaluation_completion_contract(
                                self.plan, self.root / "evaluation-final", final=True)}
                        self.state["completion_contracts"] = checks
                        self.state["goal_achieved"] = all(check["complete"] for check in checks.values())
                        complete = complete and self.state["goal_achieved"]
                    self.state["status"] = "completed" if complete else "budget_exhausted"
                    _event(self.state, "pipeline_finished", final_evaluation_status=report.get("status", "not_saved"))
                    self.persist()
                    return self.state
            except BaseException as error:
                self.fail(f"{type(error).__name__}: {error}")
                raise
            finally:
                for number, handler in handlers.items():
                    signal.signal(number, handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.plan.is_absolute():
        parser.error("--plan must be an absolute path")
    state = Experiment(read_json(args.plan)).run()
    print(json.dumps({key: state.get(key) for key in ("status", "stage", "remaining_global_seconds", "aggregate_sampled_peak_rss_bytes")}), flush=True)
    return 0 if state["status"] in {"completed", "budget_exhausted", "interrupted"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
