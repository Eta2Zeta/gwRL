#!/usr/bin/env python3
"""Measure where self-play game processes spend their time, in a real training batch.

Runs a training batch exactly as tools/supervise_campaign_training.py runs one
(the same machine profile, flags, environment and limits), except that its
game processes keep accounts. Each game thread charges its own CPU time
(time.thread_time_ns) to the innermost instrumented call it is in, so time in
nested calls is counted once, in the inner one:

  search            VectorMCTS.search's own Python: the tree, selection, backing
                    up values, and freeing the copies a finished search drops
  engine/<call>     gwrl_cpp.CampaignEnv calls: legal moves, playing moves,
                    dice, copies of the game, planning keys, decision kinds
  encode/<call>     the engine's zone encoding of a decision (zone_input) and its arrays
  adapter/<call>    CampaignAdapter's Python layer around the engine
  input/<call>      readying the encoding for the coordinator: make_zone_input
                    and shared_evaluator.prepare_into
  messaging/<call>  the pipe to the coordinator (send, recv) and the remote
                    evaluator's own code
  game loop[/call]  everything else in a game: creating it (make_env), choosing
                    and recording each move (_decide) and play_episode's own code

Each game also records its wall time and how long its thread waited for the
coordinator's answers. A game process runs several game threads that share
Python's interpreter lock, so the rest of a thread's wall time, neither its own
CPU nor waiting for the coordinator, is mostly waiting for that lock. Optional
native samples (macOS /usr/bin/sample) of game processes show which engine
functions the engine calls spend their time in.

A wrapped call costs a fraction of a microsecond; each process measures that
cost once and the summary multiplies it by the call counts. The game processes'
own CPU totals (getrusage) also count what no game thread charged: starting the
process, its main thread and its queue threads.

Run from the repository root, with the supervisor's options plus --output, on
an otherwise idle machine; it takes as long as the batch:

    .venv/bin/python tools/profile_game_process_cpu.py --output OUT.json --profile mac \\
        --control-dir CONTROL --run-dir RUN --seconds 1800 --sample-at 150,360 -- \\
        --calendar-rounds 11 --complete-episodes --batches 1 ...
"""
from __future__ import annotations

import argparse
import json
import os
import re
import resource
import subprocess
import sys
import threading
import time
from collections import Counter
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "campaign-game-process-profile-v2"
ACCOUNTS_VARIABLE = "GWRL_GAME_PROFILE_DIR"
GROUPS = ("search", "engine", "encode", "adapter", "input", "messaging", "game loop")
ENGINE_CALLS = ("planning_key", "decision_kind", "current_decision_player", "is_terminal", "legal_actions",
                "legal_interrupts", "apply_action", "apply_interrupt", "resolve_chance", "clone",
                "clone_for_search", "clone_for_search_continuing", "returns", "wealth", "observation")
ADAPTER_CALLS = ("planning_key", "decision_kind", "current_decision_player", "is_terminal", "legal_actions",
                 "apply_action", "resolve_chance", "clone", "clone_for_search", "clone_for_search_continuing",
                 "returns", "zone_input")

_clock = time.thread_time_ns
_local = threading.local()
_overhead_ns = 0.0
_write_lock = threading.Lock()


class _Account:
    """One game thread's exclusive CPU nanoseconds per instrumented call."""

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
    """The search's own code, plus each search's inclusive CPU by its root's menu size."""
    def wrapper(self, env, *args, **kwargs):
        account = _account()
        forced = len(env.legal_actions()) == 1
        started = _clock()
        account.enter("search")
        try:
            return search(self, env, *args, **kwargs)
        finally:
            account.leave()
            spent = _clock() - started
            for name in ("all", "one legal move") if forced else ("all",):
                account.searches[name] += 1
                account.search_ns[name] += spent
    return wrapper


def _evaluations(evaluate):
    """The remote evaluator's own code, plus each request's inclusive CPU by menu size."""
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
    from studies.campaign import curriculum, features, learning, shared_evaluator
    from studies.shared import campaign_adapter, multiplayer_mcts

    def wrap(owner, names, group):
        for name in names:
            if hasattr(owner, name):
                setattr(owner, name, _charged(getattr(owner, name), f"{group}/{name}"))

    wrap(gwrl_cpp.CampaignEnv, ENGINE_CALLS, "engine")
    wrap(gwrl_cpp.CampaignEnv, ("zone_input",), "encode")
    wrap(gwrl_cpp.CampaignZoneInput, ("select", "arrays", "without_actions"), "encode")
    wrap(campaign_adapter.CampaignAdapter, ADAPTER_CALLS, "adapter")
    wrap(features, ("make_zone_input",), "input")
    wrap(shared_evaluator, ("prepare_into",), "input")
    wrap(Connection, ("send", "recv"), "messaging")
    wrap(curriculum, ("make_env",), "game loop")
    wrap(learning, ("_decide",), "game loop")
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


def _profiled_play(play, directory: Path):
    """A game whose thread keeps an account, written as one line when the game ends."""
    def wrapper(settings, task, evaluator):
        _local.account = account = _Account()
        started_cpu, started_wall = account.last, time.perf_counter()
        before = (evaluator.stats.requests, evaluator.stats.prepare_seconds, evaluator.stats.wait_seconds)
        record = play(settings, task, evaluator)
        now = _clock()
        account.totals[account.stack[-1]] += now - account.last
        stats = evaluator.stats
        entry = {
            "pid": os.getpid(), "root": task.get("root"), "seed": task.get("seed"),
            "failure": record.get("failure"), "terminal": record.get("terminal"), "counts": record.get("counts"),
            "wall_seconds": time.perf_counter() - started_wall, "thread_cpu_seconds": (now - started_cpu) / 1e9,
            "evaluator": {"requests": stats.requests - before[0], "prepare_seconds": stats.prepare_seconds - before[1],
                          "wait_seconds": stats.wait_seconds - before[2]},
            "seconds": {name: value / 1e9 for name, value in sorted(account.totals.items())},
            "calls": dict(sorted(account.calls.items())),
            "searches": dict(account.searches),
            "search_seconds": {name: value / 1e9 for name, value in account.search_ns.items()},
            "evaluations_by_menu_size": dict(sorted(account.evaluations.items())),
            "evaluation_seconds_by_menu_size": {name: value / 1e9 for name, value in sorted(account.evaluation_ns.items())},
            "wrapped_call_overhead_ns": _overhead_ns}
        with _write_lock, (directory / f"{os.getpid()}.games.jsonl").open("a") as stream:
            stream.write(json.dumps(entry) + "\n")
        return record
    return wrapper


def _profiled_shared_process(settings, batch_version, *arguments) -> None:
    """A training game process (episode_workers._shared_process) that keeps accounts."""
    global _overhead_ns
    from studies.campaign import episode_workers
    from studies.campaign.shared_evaluator import game_process
    directory = Path(os.environ[ACCOUNTS_VARIABLE])
    started = time.time()
    _overhead_ns = _install()
    try:
        game_process(partial(_profiled_play(episode_workers._play_shared, directory), settings),
                     batch_version, *arguments)
    finally:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        (directory / f"{os.getpid()}.process.json").write_text(json.dumps({
            "pid": os.getpid(), "user_seconds": usage.ru_utime, "system_seconds": usage.ru_stime,
            "max_rss_bytes": usage.ru_maxrss, "wall_seconds": time.time() - started,
            "wrapped_call_overhead_ns": _overhead_ns}))


def _worker(directory: Path, arguments: list[str]) -> int:
    """The supervised trainer: training as usual, with accounting game processes."""
    from studies.campaign import episode_workers, run
    from tools import profile_game_process_cpu as importable  # Spawned processes import it by this name.
    os.environ[ACCOUNTS_VARIABLE] = str(directory)
    episode_workers._shared_process = importable._profiled_shared_process
    return run.main(arguments)


def _game_processes(trainer: int) -> list[int]:
    listing = subprocess.run(["ps", "-A", "-o", "pid=,ppid=,command="], capture_output=True, text=True).stdout
    return sorted(int(fields[0]) for fields in (line.split(None, 2) for line in listing.splitlines())
                  if len(fields) == 3 and int(fields[1]) == trainer and "spawn_main" in fields[2])


def _sample_game_processes(control_dir: Path, times: list[float], seconds: int, output: Path,
                           finished: threading.Event, taken: list[dict]) -> None:
    """At each time, sample one game process's native stacks, a different one each time."""
    started = time.monotonic()
    for index, at in enumerate(times):
        if finished.wait(max(0.0, at - (time.monotonic() - started))):
            return
        try:
            trainer = json.loads((control_dir / "state.json").read_text()).get("child_process_group")
        except (OSError, ValueError):
            continue
        pids = _game_processes(trainer) if trainer else []
        if not pids:
            continue
        pid = pids[index % len(pids)]
        path = output.with_name(f"{output.stem}.sample-{at:.0f}s.txt")
        subprocess.run(["/usr/bin/sample", str(pid), str(seconds), "-file", str(path)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        taken.append({"at_seconds": at, "pid": pid, "seconds": seconds, "file": str(path)})


def top_of_stack(path: Path, count: int = 30) -> list[list]:
    """The sample report's most frequent innermost frames: [samples, function, library]."""
    text = path.read_text(errors="replace")
    section = text.split("Sort by top of stack, same collapsed")[-1] if "Sort by top of stack" in text else ""
    rows = []
    for line in section.splitlines()[1:]:
        match = re.match(r"\s+(.+?)\s+\(in ([^)]+)\)\s+(\d+)\s*$", line)
        if match:
            rows.append([int(match.group(3)), match.group(1), match.group(2)])
        elif rows and not line.strip():
            break
    return rows[:count]


def summarize(directory: Path) -> dict:
    games = [json.loads(line) for path in sorted(directory.glob("*.games.jsonl"))
             for line in path.read_text().splitlines() if line]
    processes = [json.loads(path.read_text()) for path in sorted(directory.glob("*.process.json"))]
    complete = [game for game in games if game.get("terminal") and not game.get("failure")]
    if not complete:
        return {"games": len(games), "complete_games": 0}
    count = len(complete)

    def mean(values):
        values = list(values)
        return sum(values) / len(values)

    names = sorted({name for game in complete for name in game["seconds"]})
    by_call = {name: mean(game["seconds"].get(name, 0.0) for game in complete) for name in names}
    calls = {name: mean(game["calls"].get(name, 0) for game in complete)
             for name in sorted({name for game in complete for name in game["calls"]})}
    thread = mean(game["thread_cpu_seconds"] for game in complete)
    groups = {group: sum(value for name, value in by_call.items() if name.split("/")[0] == group) for group in GROUPS}
    decisions = mean(game["counts"]["decisions"] for game in complete)
    wall = mean(game["wall_seconds"] for game in complete)
    waiting = mean(game["evaluator"]["wait_seconds"] for game in complete)
    overhead = mean(sum(game["calls"].values()) * game["wrapped_call_overhead_ns"] / 1e9 for game in complete)
    process_cpu = sum(process["user_seconds"] + process["system_seconds"] for process in processes)
    return {
        "games": len(games), "complete_games": count, "decisions_per_game": decisions,
        "chance_events_per_game": mean(game["counts"]["chance_events"] for game in complete),
        "evaluations_per_game": mean(game["evaluator"]["requests"] for game in complete),
        "thread_cpu_seconds_per_game": thread,
        "thread_cpu_ms_per_decision": thread / decisions * 1e3,
        "seconds_per_game": groups,
        "share_of_thread_cpu": {group: value / thread for group, value in groups.items()},
        "seconds_per_game_by_call": dict(sorted(by_call.items(), key=lambda item: -item[1])),
        "calls_per_game": calls,
        "microseconds_per_call": {name: by_call[name] / calls[name] * 1e6 for name in by_call
                                  if calls.get(name)},
        "estimated_instrumentation_seconds_per_game": overhead,
        "wrapped_call_overhead_ns": mean(game["wrapped_call_overhead_ns"] for game in complete),
        "searches_per_game": {name: mean(game["searches"].get(name, 0) for game in complete)
                              for name in ("all", "one legal move")},
        "search_seconds_per_game": {name: mean(game["search_seconds"].get(name, 0.0) for game in complete)
                                    for name in ("all", "one legal move")},
        "evaluations_by_menu_size": {name: mean(game["evaluations_by_menu_size"].get(name, 0) for game in complete)
                                     for name in ("0", "1", "2+")},
        "evaluation_seconds_by_menu_size": {name: mean(game["evaluation_seconds_by_menu_size"].get(name, 0.0)
                                                       for game in complete) for name in ("0", "1", "2+")},
        "wall_seconds_per_game": wall,
        "wall_share": {"own CPU": thread / wall, "waiting for the coordinator": waiting / wall,
                       "other, mostly the interpreter lock": max(0.0, wall - thread - waiting) / wall},
        "game_processes": len(processes),
        "process_cpu_seconds_per_game": process_cpu / count if len(complete) == len(games) else None,
        "unaccounted_process_cpu_seconds_per_game": (process_cpu / count - thread) if len(complete) == len(games) else None,
    }


def describe(summary: dict) -> str:
    if not summary.get("complete_games"):
        return "No game finished with an account."
    thread = summary["thread_cpu_seconds_per_game"]
    lines = [f"{summary['complete_games']} complete games: {summary['decisions_per_game']:.0f} decisions, "
             f"{summary['evaluations_per_game']:.0f} evaluations, {thread:.1f} game-thread CPU-s per game "
             f"({summary['thread_cpu_ms_per_decision']:.0f} ms per decision)"]
    for group, value in summary["seconds_per_game"].items():
        lines.append(f"  {group:<12} {value:8.1f} s  {value / thread:6.1%}")
        for name, spent in summary["seconds_per_game_by_call"].items():
            if name.split("/")[0] == group and "/" in name and spent >= 0.005 * thread:
                lines.append(f"    {name.split('/', 1)[1]:<28} {spent:8.1f} s  {spent / thread:6.1%}  "
                             f"{summary['calls_per_game'].get(name, 0):11.0f} calls  "
                             f"{summary['microseconds_per_call'].get(name, 0):8.1f} us each")
    lines.append(f"  instrumentation (estimated): {summary['estimated_instrumentation_seconds_per_game']:.1f} s per game, "
                 f"{summary['wrapped_call_overhead_ns']:.0f} ns per wrapped call")
    share = summary["wall_share"]
    lines.append(f"  a game thread's wall time {summary['wall_seconds_per_game']:.0f} s: " +
                 ", ".join(f"{name} {value:.0%}" for name, value in share.items()))
    if summary.get("process_cpu_seconds_per_game") is not None:
        lines.append(f"  game processes' own CPU {summary['process_cpu_seconds_per_game']:.1f} s per game, "
                     f"{summary['unaccounted_process_cpu_seconds_per_game']:.1f} s of it outside game threads")
    searches, spent = summary["searches_per_game"], summary["search_seconds_per_game"]
    lines.append(f"  searches with one legal move: {searches['one legal move']:.0f} of {searches['all']:.0f}, "
                 f"{spent['one legal move']:.1f} of {spent['all']:.1f} search CPU-s")
    return "\n".join(lines)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--_worker"]:
        rest = argv[2:]
        return _worker(Path(argv[1]), rest[1:] if rest[:1] == ["--"] else rest)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True, help="New JSON report")
    parser.add_argument("--profile", help="Machine profile in studies/campaign/profiles, such as mac")
    parser.add_argument("--control-dir", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--seconds", type=float, required=True)
    parser.add_argument("--sample-at", default="", help="Comma-separated seconds into the run at which to "
                        "sample one game process's native stacks, a different process each time")
    parser.add_argument("--sample-seconds", type=int, default=20)
    parser.add_argument("training_arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    from dataclasses import asdict
    from tools import supervise_campaign_training as supervisor
    output = args.output.resolve()
    if output.exists():
        parser.error("Choose a new output file")
    directory = output.with_name(output.stem + "-accounts")
    directory.mkdir(parents=True)
    arguments = args.training_arguments[1:] if args.training_arguments[:1] == ["--"] else args.training_arguments
    profile = supervisor.load_profile(args.profile) if args.profile else {}
    limits = profile.get("supervisor", {})
    python = str(ROOT / profile["python"]) if "python" in profile else sys.executable
    config = supervisor.SupervisorConfig(seconds=args.seconds, cpu_budget=limits.get("cpu_budget", 12),
                                         memory_bytes=limits.get("memory_bytes", 30_000_000_000),
                                         max_restarts=0)
    arguments = supervisor.profile_arguments(profile, arguments)

    def command(python, run_dir, arguments, resume, extension=None):
        trainer = supervisor.training_command(python, run_dir, arguments, resume, extension)
        return [python, str(Path(__file__).resolve()), "--_worker", str(directory), "--", *trainer[3:]]

    finished, samples = threading.Event(), []
    times = sorted(float(text) for text in args.sample_at.split(",") if text)
    sampler = threading.Thread(target=_sample_game_processes, daemon=True,
                               args=(args.control_dir.resolve(), times, args.sample_seconds, output, finished, samples))
    awake = supervisor.keep_awake() if profile.get("keep_awake") else None
    sampler.start()
    try:
        state = supervisor.supervise(args.control_dir, args.run_dir, config, arguments, python=python,
                                     profile=args.profile, unset_environment=tuple(profile.get("unset_environment", ())),
                                     command_factory=command)
    finally:
        finished.set()
        if awake is not None:
            awake.terminate()
    sampler.join()
    summary = summarize(directory)
    for sample in samples:
        path = Path(sample["file"])
        sample["top_of_stack"] = top_of_stack(path) if path.exists() else []
    batch = {}
    manifest = args.run_dir / "manifest.json"
    if manifest.exists():
        value = json.loads(manifest.read_text())
        playing, counters = value["timings_seconds_this_invocation"]["collection"], value["counters"]
        evaluator = value["runner"]["updates"][0]["evaluator"] if value["runner"].get("updates") else {}
        batch = {"playing_seconds": playing, "games": counters["episodes"],
                 "games_per_hour": counters["episodes"] / playing * 3600,
                 "decisions_per_hour": counters["decisions"] / playing * 3600,
                 "coordinator_busy": evaluator.get("forward_seconds", 0.0) / playing,
                 "evaluator": evaluator}
    report = {"schema": SCHEMA, "argv": argv, "profile": args.profile, "supervisor": asdict(config),
              "training_arguments": arguments, "status": state.get("status"),
              "peak_rss_bytes": state.get("aggregate_sampled_peak_rss_bytes"),
              "environment": {"MallocNanoZone": os.environ.get("MallocNanoZone"),
                              "unset_for_training": profile.get("unset_environment", [])},
              "batch": batch, "accounts": str(directory), "summary": summary, "native_samples": samples}
    output.write_text(json.dumps(report, indent=1))
    if batch:
        print(f"batch: {batch['games']} games, {batch['games_per_hour']:.1f} games/h and "
              f"{batch['decisions_per_hour']:,.0f} decisions/h while playing, coordinator busy "
              f"{batch['coordinator_busy']:.0%}")
    print(describe(summary))
    return 0 if state.get("status") == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
