#!/usr/bin/env python3
"""Measure where shared-GPU self-play game processes spend CPU time, per game.

Runs the shared self-play of tools/benchmark_campaign_devices.py (game
processes with one thread per game, plus one MPS coordinator) at the settings
of the 2026-10-29 shared-GPU run, with every game process instrumented. That
run searched one-action roots; here they are played at once unless
--search-forced-roots asks for the search. Each game thread charges its own CPU
time (time.thread_time_ns) to the innermost category it is in, so time in nested
calls is counted once, in the inner one:

  search logic          VectorMCTS's tree code: everything in a search not below
  adapter               CampaignAdapter's Python layer around the engine
  rules engine          gwrl_cpp.CampaignEnv calls: legal moves, moves, dice, clones, keys
  input: graph compile  native graph compiles, including their Python token callbacks
  input: native         numeric snapshots and graph array exports
  input: python         shared_evaluator.prepare and the adapter's numeric_input
  messaging             the evaluator's own code, shared-memory writes and the pipe's CPU
  game loop             play_shared_game outside searches

Wrapped calls are charged per method, as "group/method". Freeing engine objects
is charged to the caller that drops them, mostly search logic; the optional
native samples (macOS /usr/bin/sample) show that cost inside the engine.

Each game record gains a "cpu_profile" with these totals, call counts, the
searches whose root had a single legal action, and evaluations by legal-menu
size. A wrapped call adds a fraction of a microsecond; the profile measures
that cost once per process and the summary multiplies it by the call counts.
The game processes' total CPU (rusage) also counts what no game thread
charged: start-up, queue threads and the main thread. Game processes inherit
the environment, including MallocNanoZone, which the report records.

Run with the PyTorch environment that has MPS (tmp/gpu-mps-env/bin/python) on
an otherwise idle machine; it takes as long as the run it profiles.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "campaign-game-process-cpu-profile-v1"
CATEGORIES = ("search logic", "adapter", "rules engine", "input: graph compile", "input: native",
              "input: python", "messaging", "game loop")
# studies/campaign/runs/shared-gpu-2026-10-29/command.sh
SETTINGS = dict(mode="selfplay", devices=("mps",), search_evaluation="per_search", threads=1, calendar_rounds=11,
                simulations=64, max_depth=16, max_transitions=20000, max_state_visits=20, hidden_dim=64,
                message_layers=2, token_buckets=16384, value_scale=100.0, model_seed=1951,
                memory_bytes=30_000_000_000, cpu_budget=12)

_clock = time.thread_time_ns
_local = threading.local()
_overhead_ns = 0.0


class _Account:
    """One game thread's exclusive CPU nanoseconds per category."""

    def __init__(self) -> None:
        self.stack, self.last = ["game loop"], _clock()
        self.totals, self.calls = Counter(), Counter()
        self.searches, self.search_ns = Counter(), Counter()
        self.evaluations, self.evaluation_ns = Counter(), Counter()

    def enter(self, category: str) -> None:
        now = _clock()
        self.totals[self.stack[-1]] += now - self.last
        self.stack.append(category)
        self.last = now
        self.calls[category] += 1

    def leave(self) -> None:
        now = _clock()
        self.totals[self.stack.pop()] += now - self.last
        self.last = now


def _account() -> _Account:
    account = getattr(_local, "account", None)
    if account is None:
        account = _local.account = _Account()
    return account


def _charged(function, category):
    def wrapper(*args, **kwargs):
        account = _account()
        account.enter(category)
        try:
            return function(*args, **kwargs)
        finally:
            account.leave()
    wrapper.__wrapped__ = function
    return wrapper


def _searches(search):
    """Search time as search logic, plus each search's inclusive CPU by root menu size."""
    def wrapper(self, env, *args, **kwargs):
        account = _account()
        forced = len(env.legal_actions()) == 1
        started = _clock()
        account.enter("search logic")
        try:
            return search(self, env, *args, **kwargs)
        finally:
            account.leave()
            spent = _clock() - started
            for name in ("all", "one legal action") if forced else ("all",):
                account.searches[name] += 1
                account.search_ns[name] += spent
    return wrapper


def _evaluations(evaluate):
    """The evaluator's own code as messaging, plus each request's inclusive CPU by menu size."""
    def wrapper(self, env, actions):
        account = _account()
        menu = "0" if not actions else "1" if len(actions) == 1 else "2+"
        started = _clock()
        account.enter("messaging/evaluate")
        try:
            return evaluate(self, env, actions)
        finally:
            account.leave()
            account.evaluations[menu] += 1
            account.evaluation_ns[menu] += _clock() - started
    return wrapper


def _install() -> float:
    """Wrap this process's engine, input, messaging and search calls.

    Returns the measured CPU cost of one wrapped call in nanoseconds.
    """
    import gwrl_cpp
    from multiprocessing.connection import Connection
    from studies.campaign import shared_evaluator
    from studies.shared import campaign_adapter, multiplayer_mcts

    def wrap(owner, names, group):
        for name in names:
            setattr(owner, name, _charged(getattr(owner, name), f"{group}/{name}"))

    wrap(gwrl_cpp.CampaignEnv, ("planning_key", "decision_kind", "current_decision_player", "is_terminal",
                                "legal_actions", "legal_interrupts", "apply_action", "apply_interrupt",
                                "resolve_chance", "clone", "clone_for_search", "returns"), "rules engine")
    wrap(gwrl_cpp.CampaignEnv, ("numeric_observation", "numeric_context"), "input: native")
    wrap(gwrl_cpp.CampaignNumericSnapshot, ("scheduled_observation", "scheduled_context", "factor_json"),
         "input: native")
    wrap(gwrl_cpp.CampaignAction, ("scheduled_snapshot",), "input: native")
    wrap(gwrl_cpp.CampaignNumericGraph, ("arrays", "external_references"), "input: native")
    wrap(gwrl_cpp.CampaignNumericGraphCompiler, ("compile",), "input: graph compile")
    wrap(campaign_adapter.CampaignAdapter, ("planning_key", "decision_kind", "current_decision_player",
                                            "is_terminal", "legal_actions", "apply_action", "resolve_chance",
                                            "clone", "clone_for_search", "returns"), "adapter")
    wrap(campaign_adapter.CampaignAdapter, ("numeric_input",), "input: python")
    wrap(shared_evaluator, ("prepare",), "input: python")
    wrap(shared_evaluator, ("write_arrays",), "messaging")
    wrap(Connection, ("send", "recv"), "messaging")
    shared_evaluator.RemoteEvaluator.evaluate = _evaluations(shared_evaluator.RemoteEvaluator.evaluate)
    multiplayer_mcts.VectorMCTS.search = _searches(multiplayer_mcts.VectorMCTS.search)

    # One wrapped call's cost against the bare call, on a throwaway account.
    def nothing():
        return None
    probe, count, saved = _charged(nothing, "calibration"), 200_000, getattr(_local, "account", None)
    _local.account = _Account()
    best = []
    for _ in range(3):
        began = _clock()
        for _ in range(count):
            nothing()
        bare = _clock() - began
        began = _clock()
        for _ in range(count):
            probe()
        best.append((_clock() - began - bare) / count)
    _local.account = saved
    return min(best)


def _profiled_game(play):
    def wrapper(config, seed, evaluator, deadline_epoch):
        _local.account = account = _Account()
        started = account.last
        record = play(config, seed, evaluator, deadline_epoch)
        now = _clock()
        account.totals[account.stack[-1]] += now - account.last
        record["cpu_profile"] = {
            "thread_cpu_seconds": (now - started) / 1e9,
            "seconds": {name: value / 1e9 for name, value in sorted(account.totals.items())},
            "calls": dict(sorted(account.calls.items())),
            "searches": dict(account.searches),
            "search_seconds": {name: value / 1e9 for name, value in account.search_ns.items()},
            "evaluations_by_menu_size": dict(sorted(account.evaluations.items())),
            "evaluation_seconds_by_menu_size": {name: value / 1e9
                                                for name, value in sorted(account.evaluation_ns.items())},
            "wrapped_call_overhead_ns": _overhead_ns}
        return record
    return wrapper


def _instrumented_game_process(*args):
    """A benchmark game process with this module's accounting installed first."""
    global _overhead_ns
    from tools import benchmark_campaign_devices as benchmark
    _overhead_ns = _install()
    benchmark.play_shared_game = _profiled_game(benchmark.play_shared_game)
    return benchmark._shared_game_process(*args)


def _worker(settings: Path, progress: Path) -> int:
    from tools import benchmark_campaign_devices as benchmark
    from tools import profile_game_process_cpu as importable  # Spawned processes import it by this name.
    values = json.loads(settings.read_text())
    for name in ("devices", "seeds", "batch_sizes", "position_labels"):
        values[name] = tuple(values[name])
    benchmark._shared_game_process = importable._instrumented_game_process
    report = benchmark.worker(benchmark.Config(**values), "mps", progress)
    return 0 if report["status"] == "completed" else 2


def _game_processes(worker_pid: int) -> list[int]:
    listing = subprocess.run(["ps", "-A", "-o", "pid=,ppid=,command="], capture_output=True, text=True).stdout
    return [int(fields[0]) for fields in (line.split(None, 2) for line in listing.splitlines())
            if len(fields) == 3 and int(fields[1]) == worker_pid and "spawn_main" in fields[2]]


def summarize(report: dict) -> dict:
    result = report["result"]
    games = [game for game in result["games"] if "cpu_profile" in game]
    complete = [game for game in games if game.get("terminal")]
    chosen = complete or games
    if not chosen:
        return {"games": 0}
    count = len(chosen)

    def mean(values):
        values = list(values)
        return sum(values) / len(values)

    profiles = [game["cpu_profile"] for game in chosen]
    thread = mean(profile["thread_cpu_seconds"] for profile in profiles)
    detail = {name: mean(profile["seconds"].get(name, 0.0) for profile in profiles)
              for name in {name for profile in profiles for name in profile["seconds"]}}
    seconds = {group: sum(value for name, value in detail.items() if name.split("/")[0] == group)
               for group in CATEGORIES}
    calls = {name: mean(profile["calls"].get(name, 0) for profile in profiles)
             for name in sorted({name for profile in profiles for name in profile["calls"]})}
    overhead = mean(sum(profile["calls"].values()) * profile["wrapped_call_overhead_ns"] / 1e9
                    for profile in profiles)
    searches = {name: mean(profile["searches"].get(name, 0) for profile in profiles)
                for name in ("all", "one legal action")}
    search_seconds = {name: mean(profile["search_seconds"].get(name, 0.0) for profile in profiles)
                      for name in ("all", "one legal action")}
    evaluations = {name: mean(profile["evaluations_by_menu_size"].get(name, 0) for profile in profiles)
                   for name in ("0", "1", "2+")}
    evaluation_seconds = {name: mean(profile["evaluation_seconds_by_menu_size"].get(name, 0.0)
                                     for profile in profiles) for name in ("0", "1", "2+")}
    summary = {
        "games": count, "complete_games": len(complete), "decisions": mean(game["decisions"] for game in chosen),
        "evaluations": mean(game["evaluations"] for game in chosen),
        "thread_cpu_seconds": thread, "seconds": seconds,
        "share": {name: value / thread for name, value in seconds.items()},
        "seconds_by_method": dict(sorted(detail.items(), key=lambda item: -item[1])),
        "calls": calls, "estimated_instrumentation_seconds": overhead,
        "searches": searches, "search_seconds": search_seconds, "evaluations_by_menu_size": evaluations,
        "evaluation_seconds_by_menu_size": evaluation_seconds,
        "wrapped_call_overhead_ns": mean(profile["wrapped_call_overhead_ns"] for profile in profiles)}
    if result.get("completed_games") and len(complete) == len(result["games"]):
        summary["game_process_cpu_seconds_per_game"] = result["game_process_cpu_seconds"] / result["completed_games"]
        summary["coordinator_cpu_seconds_per_game"] = result["coordinator_cpu_seconds"] / result["completed_games"]
        summary["steady_state_games_per_hour"] = result.get("steady_state_games_per_hour")
    return summary


def describe(summary: dict) -> str:
    if not summary.get("games"):
        return "No game finished with a profile."
    thread = summary["thread_cpu_seconds"]
    lines = [f"{summary['games']} games ({summary['complete_games']} complete): {summary['decisions']:.0f} decisions, "
             f"{summary['evaluations']:.0f} evaluations, {thread:.0f} thread CPU-s per game"]
    for name, value in summary["seconds"].items():
        lines.append(f"  {name:<22} {value:9.1f} s  {value / thread:6.1%}")
        for method, spent in summary["seconds_by_method"].items():
            if method.split("/")[0] == name and "/" in method and spent >= 0.01 * thread:
                lines.append(f"    {method.split('/', 1)[1]:<20} {spent:9.1f} s  {spent / thread:6.1%}  "
                             f"{summary['calls'].get(method, 0):12.0f} calls")
    lines.append(f"  of which instrumentation (est.) {summary['estimated_instrumentation_seconds']:.1f} s  "
                 f"{summary['estimated_instrumentation_seconds'] / thread:.1%}  "
                 f"({summary['wrapped_call_overhead_ns']:.0f} ns per wrapped call, a lower bound)")
    searches, spent = summary["searches"], summary["search_seconds"]
    if searches["all"]:
        lines.append(f"  searches with one legal action: {searches['one legal action']:.0f} of {searches['all']:.0f}, "
                     f"{spent['one legal action']:.0f} of {spent['all']:.0f} search CPU-s "
                     f"({spent['one legal action'] / thread:.1%} of thread CPU)")
    evaluations, cost = summary["evaluations_by_menu_size"], summary["evaluation_seconds_by_menu_size"]
    lines.append("  evaluations by legal-menu size: " + ", ".join(
        f"{name}: {evaluations[name]:.0f} ({cost[name]:.0f} CPU-s)" for name in ("0", "1", "2+")))
    if "game_process_cpu_seconds_per_game" in summary:
        lines.append(f"  game-process CPU (rusage) {summary['game_process_cpu_seconds_per_game']:.0f} s per game, "
                     f"coordinator {summary['coordinator_cpu_seconds_per_game']:.0f} s; "
                     f"{summary['steady_state_games_per_hour']:.1f} games/h steady state")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, help="New JSON report")
    parser.add_argument("--seeds", help="Comma-separated game seeds")
    parser.add_argument("--processes", type=int, default=8)
    parser.add_argument("--games-per-process", type=int, default=4)
    parser.add_argument("--seconds", type=float, default=21600.0)
    parser.add_argument("--sample-at", default="",
                        help="Comma-separated seconds into the run at which to sample one game process's native stacks")
    parser.add_argument("--sample-seconds", type=int, default=30)
    parser.add_argument("--search-forced-roots", action="store_true", help="Search one-action roots too")
    parser.add_argument("--_worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--_progress", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args._worker:
        return _worker(args._worker, args._progress)
    if args.output is None or not args.seeds:
        parser.error("--output and --seeds are required")
    output = args.output.resolve()
    if output.exists():
        parser.error("Choose a new output file")
    from dataclasses import asdict
    from tools.benchmark_campaign_devices import Config
    from tools.supervise_campaign_training import aggregate_rss
    values = {**asdict(Config()), **SETTINGS, "seeds": [int(seed) for seed in args.seeds.split(",")],
              "processes": args.processes, "games_per_process": args.games_per_process, "seconds": args.seconds,
              "search_forced_roots": args.search_forced_roots}
    Config(**{**values, **{name: tuple(values[name]) for name in ("devices", "seeds", "batch_sizes",
                                                                  "position_labels")}})
    output.parent.mkdir(parents=True, exist_ok=True)
    started, peak, stopped, sampled, samplers = time.monotonic(), 0, None, [], []
    pending = sorted(float(text) for text in args.sample_at.split(",") if text)
    with tempfile.TemporaryDirectory(prefix="campaign-cpu-profile-") as directory:
        directory = Path(directory)
        settings, progress = directory / "config.json", directory / "progress.json"
        settings.write_text(json.dumps(values))
        # The environment of tools/benchmark_campaign_devices.py's supervise_device.
        environment = {**os.environ, "PYTHONHASHSEED": "0", "OPENBLAS_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
                       "PYTORCH_ENABLE_MPS_FALLBACK": "0", "PYTORCH_MPS_FAST_MATH": "0",
                       **{name: "1" for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")}}
        environment.pop("PYTORCH_MPS_PREFER_METAL", None)
        with (directory / "stderr").open("w") as stderr:
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--_worker", str(settings),
                                        "--_progress", str(progress)], cwd=ROOT, env=environment,
                                       stdout=stderr, stderr=stderr, start_new_session=True)
            try:
                while process.poll() is None:
                    elapsed = time.monotonic() - started
                    if elapsed >= args.seconds + 120:
                        stopped = "wall_limit"
                        break
                    charged = aggregate_rss(process.pid)
                    if progress.exists():
                        try:
                            charged += json.loads(progress.read_text()).get("device_memory", {}).get(
                                "driver_allocated_bytes") or 0
                        except ValueError:
                            pass  # Read while the worker replaced it.
                    peak = max(peak, charged)
                    if charged >= SETTINGS["memory_bytes"] - 1_000_000_000:
                        stopped = "memory_limit"
                        break
                    if pending and elapsed >= pending[0]:
                        pids, at = _game_processes(process.pid), pending.pop(0)
                        if pids:
                            # Sampled in the background, so memory stays monitored meanwhile.
                            path = str(output.with_suffix(f".sample-{at:.0f}s.txt"))
                            samplers.append(subprocess.Popen(
                                ["/usr/bin/sample", str(pids[0]), str(args.sample_seconds), "-file", path],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
                            sampled.append(path)
                    time.sleep(1)
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(30)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                for sampler in samplers:
                    sampler.wait()
        errors = (directory / "stderr").read_text()[-20000:]
        report = json.loads(progress.read_text()) if progress.exists() else {}
    summary = summarize(report) if report.get("result") else {"games": 0}
    # MallocNanoZone=0 selects the slower small-object allocator; random games then use about 26-29% more CPU.
    out = {"schema": SCHEMA, "argv": sys.argv if argv is None else argv, "stopped": stopped,
           "malloc_nano_zone": environment.get("MallocNanoZone"),
           "worker_exit_code": process.returncode, "peak_charged_memory_bytes": peak,
           "native_samples": sampled, "summary": summary, "report": report, "stderr_tail": errors}
    output.write_text(json.dumps(out, indent=1))
    print(describe(summary))
    return 0 if report.get("status") == "completed" and stopped is None else 2


if __name__ == "__main__":
    raise SystemExit(main())
