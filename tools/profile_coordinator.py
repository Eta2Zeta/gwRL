#!/usr/bin/env python3
"""Measure where the self-play coordinator spends its time, in a real training batch.

Runs a training batch exactly as tools/supervise_campaign_training.py runs one
(the same machine profile, flags, environment and limits), except that the
coordinator, the trainer's main process answering every game thread's requests
(studies/campaign/shared_evaluator.py), times each step of its serving rounds:

  waiting     waiting for a request on the game threads' pipes
  receiving   reading the requests' headers from the pipes
  reading     mapping each request's arrays in its shared buffer (read_arrays)
  packing     laying the positions out for a pass (pack_zone_arrays)
  forward     the network pass (neural._forward)
  collecting  priors and values from a pass's outputs (collect)
  replying    sending priors and values back
  other       the rest of answering: grouping requests by model, averaging the
              three models' values at chance positions, statistics

With --save-every N it also keeps every Nth serving round's requests (each
request's alliance and arrays) in a pickle beside the report, so that
candidate coordinators can be timed and compared offline on real rounds
(tools/replay_coordinator_rounds.py). With --sample-at it records the
coordinator's native call stacks with macOS's /usr/bin/sample.

A timed step costs about a microsecond of the coordinator's time, a few
percent of a round; compare batch throughput with unprofiled batches only.

Run from the repository root, with the supervisor's options plus --output, on
an otherwise idle machine; it takes as long as the batch:

    .venv/bin/python tools/profile_coordinator.py --output OUT.json --profile mac \\
        --control-dir CONTROL --run-dir RUN --seconds 1800 --save-every 200 -- \\
        --calendar-rounds 11 --complete-episodes --batches 1 ...
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
try:
    import resource
except ImportError:  # Windows has no getrusage; see _usage.
    resource = None
import sys
import threading
import time
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "campaign-coordinator-profile-v1"
OUTPUT_VARIABLE = "GWRL_COORDINATOR_PROFILE"
SAVE_VARIABLE = "GWRL_COORDINATOR_SAVE_EVERY"
STEPS = ("waiting", "receiving", "reading", "packing", "forward", "collecting", "replying", "other")


class _Accounts:
    """Seconds and calls per timed step, and pass times by positions per pass."""

    def __init__(self) -> None:
        self.serving = False
        self.seconds, self.calls = Counter(), Counter()
        self.forward_by_positions: dict[int, list[float]] = defaultdict(lambda: [0, 0.0])
        self.rounds_seen, self.saved = 0, []


_accounts = _Accounts()


def _usage():
    """This process's user and system CPU seconds, as getrusage reports them."""
    if resource is not None:
        return resource.getrusage(resource.RUSAGE_SELF)
    times = os.times()  # Windows reads the same process CPU times here.
    return SimpleNamespace(ru_utime=times.user, ru_stime=times.system)


def _timed(function, step):
    def wrapper(*args, **kwargs):
        if not _accounts.serving:
            return function(*args, **kwargs)
        started = time.perf_counter()
        try:
            return function(*args, **kwargs)
        finally:
            _accounts.seconds[step] += time.perf_counter() - started
            _accounts.calls[step] += 1
    wrapper.__wrapped__ = function
    return wrapper


def _install(save_every: int) -> None:
    import numpy as np
    from studies.campaign import features, neural, shared_evaluator

    shared_evaluator.read_arrays = _timed(shared_evaluator.read_arrays, "reading")
    shared_evaluator.collect = _timed(shared_evaluator.collect, "collecting")
    features.pack_zone_arrays = _timed(features.pack_zone_arrays, "packing")
    forward = neural._forward

    def timed_forward(networks, batch, **kwargs):
        if not _accounts.serving:
            return forward(networks, batch, **kwargs)
        started = time.perf_counter()
        try:
            return forward(networks, batch, **kwargs)
        finally:
            spent = time.perf_counter() - started
            _accounts.seconds["forward"] += spent
            _accounts.calls["forward"] += 1
            entry = _accounts.forward_by_positions[batch.positions]
            entry[0] += 1
            entry[1] += spent

    neural._forward = timed_forward
    server = shared_evaluator.SharedEvaluatorServer
    answer, serve = server.answer, server.serve

    def saving_answer(self, requests):
        _accounts.rounds_seen += 1
        if save_every and _accounts.rounds_seen % save_every == 0:
            _accounts.saved.append([
                (actor, count, {name: np.array(values) for name, values in
                                shared_evaluator.read_arrays.__wrapped__(self.memories[connection].buf,
                                                                         header).items()})
                for connection, (actor, count, layout, header) in requests])
        return answer(self, requests)

    def profiled_serve(self, keep_running):
        usage, started = _usage(), time.perf_counter()
        thread_started = time.thread_time()
        _accounts.serving = True
        try:
            return serve(self, keep_running)
        finally:
            _accounts.serving = False
            after = _usage()
            _write(self.stats, time.perf_counter() - started, time.thread_time() - thread_started,
                   (after.ru_utime - usage.ru_utime) + (after.ru_stime - usage.ru_stime))

    server.answer = saving_answer if save_every else answer
    server.serve = profiled_serve


def _write(stats, wall: float, thread_cpu: float, process_cpu: float) -> None:
    output = Path(os.environ[OUTPUT_VARIABLE])
    seconds = dict(_accounts.seconds)
    seconds.update(waiting=stats.idle_seconds, receiving=stats.receive_seconds, replying=stats.reply_seconds)
    inside = sum(seconds.get(step, 0.0) for step in ("reading", "packing", "forward", "collecting"))
    seconds["other"] = stats.forward_seconds - inside
    value = {"serve_wall_seconds": wall, "serve_thread_cpu_seconds": thread_cpu,
             "process_cpu_seconds_while_serving": process_cpu,
             "requests": stats.requests, "rounds": stats.rounds, "passes": stats.passes,
             "seconds": {step: seconds.get(step, 0.0) for step in STEPS},
             "calls": dict(_accounts.calls),
             "requests_per_round": {str(key): count for key, count in sorted(stats.requests_per_round.items())},
             "positions_per_pass": {str(key): count for key, count in sorted(stats.positions_per_pass.items())},
             "forward_by_positions": {str(key): {"passes": entry[0], "seconds": entry[1]}
                                      for key, entry in sorted(_accounts.forward_by_positions.items())},
             "saved_rounds": len(_accounts.saved)}
    output.with_suffix(".coordinator.json").write_text(json.dumps(value, indent=1))
    if _accounts.saved:
        with output.with_suffix(".rounds.pickle").open("wb") as stream:
            pickle.dump(_accounts.saved, stream, protocol=pickle.HIGHEST_PROTOCOL)


def _worker(output: Path, save_every: int, arguments: list[str]) -> int:
    """The supervised trainer: training as usual, with a profiled coordinator."""
    from studies.campaign import run
    os.environ[OUTPUT_VARIABLE] = str(output)
    _install(save_every)
    return run.main(arguments)


def _sample_coordinator(control_dir: Path, times: list[float], seconds: int, output: Path,
                        finished: threading.Event, taken: list[dict]) -> None:
    import subprocess
    started = time.monotonic()
    for at in times:
        if finished.wait(max(0.0, at - (time.monotonic() - started))):
            return
        try:
            trainer = json.loads((control_dir / "state.json").read_text()).get("child_process_group")
        except (OSError, ValueError):
            continue
        if not trainer:
            continue
        path = output.with_name(f"{output.stem}.sample-{at:.0f}s.txt")
        subprocess.run(["/usr/bin/sample", str(trainer), str(seconds), "-file", str(path)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        taken.append({"at_seconds": at, "pid": trainer, "seconds": seconds, "file": str(path)})


def describe(coordinator: dict, batch: dict) -> str:
    wall = coordinator["serve_wall_seconds"]
    lines = []
    if batch:
        lines.append(f"batch: {batch['games']} games, {batch['decisions_per_hour']:,.0f} decisions/h while playing")
    lines.append(f"coordinator: {coordinator['requests']:,} requests in {coordinator['rounds']:,} rounds "
                 f"({coordinator['requests'] / coordinator['rounds']:.2f} per round), {coordinator['passes']:,} passes "
                 f"({coordinator['requests'] / coordinator['passes']:.2f} requests per pass), "
                 f"{coordinator['serve_thread_cpu_seconds']:.1f} CPU-s on its thread over {wall:.1f} s")
    for step in STEPS:
        spent = coordinator["seconds"][step]
        lines.append(f"  {step:<11} {spent:8.1f} s  {spent / wall:6.1%}  "
                     f"{spent / coordinator['requests'] * 1e6:7.1f} us per request")
    return "\n".join(lines)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--_worker"]:
        rest = argv[3:]
        return _worker(Path(argv[1]), int(argv[2]), rest[1:] if rest[:1] == ["--"] else rest)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True, help="New JSON report")
    parser.add_argument("--profile", help="Machine profile in studies/campaign/profiles, such as mac")
    parser.add_argument("--control-dir", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--seconds", type=float, required=True)
    parser.add_argument("--save-every", type=int, default=0, help="Keep every Nth serving round's requests")
    parser.add_argument("--sample-at", default="", help="Comma-separated seconds into the run at which to "
                        "sample the coordinator's native stacks")
    parser.add_argument("--sample-seconds", type=int, default=20)
    parser.add_argument("training_arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    from dataclasses import asdict
    from tools import supervise_campaign_training as supervisor
    output = args.output.resolve()
    if output.exists():
        parser.error("Choose a new output file")
    arguments = args.training_arguments[1:] if args.training_arguments[:1] == ["--"] else args.training_arguments
    profile = supervisor.load_profile(args.profile) if args.profile else {}
    limits = profile.get("supervisor", {})
    python = str(ROOT / Path(profile["python"]).expanduser()) if "python" in profile else sys.executable
    config = supervisor.SupervisorConfig(seconds=args.seconds, cpu_budget=limits.get("cpu_budget", 12),
                                         memory_bytes=limits.get("memory_bytes", 30_000_000_000),
                                         max_restarts=0)
    arguments = supervisor.profile_arguments(profile, arguments)

    def command(python, run_dir, arguments, resume, extension=None):
        trainer = supervisor.training_command(python, run_dir, arguments, resume, extension)
        return [python, str(Path(__file__).resolve()), "--_worker", str(output), str(args.save_every), "--",
                *trainer[3:]]

    finished, samples = threading.Event(), []
    times = sorted(float(text) for text in args.sample_at.split(",") if text)
    sampler = threading.Thread(target=_sample_coordinator, daemon=True,
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
    coordinator_path = output.with_suffix(".coordinator.json")
    coordinator = json.loads(coordinator_path.read_text()) if coordinator_path.exists() else None
    batch = {}
    manifest = args.run_dir / "manifest.json"
    if manifest.exists():
        value = json.loads(manifest.read_text())
        playing, counters = value["timings_seconds_this_invocation"]["collection"], value["counters"]
        evaluator = value["runner"]["updates"][0]["evaluator"] if value["runner"].get("updates") else {}
        batch = {"playing_seconds": playing, "games": counters["episodes"], "decisions": counters["decisions"],
                 "games_per_hour": counters["episodes"] / playing * 3600,
                 "decisions_per_hour": counters["decisions"] / playing * 3600,
                 "coordinator_busy": evaluator.get("forward_seconds", 0.0) / playing,
                 "evaluator": evaluator}
    report = {"schema": SCHEMA, "argv": argv, "profile": args.profile, "supervisor": asdict(config),
              "training_arguments": arguments, "status": state.get("status"),
              "peak_rss_bytes": state.get("aggregate_sampled_peak_rss_bytes"),
              "batch": batch, "coordinator": coordinator, "native_samples": samples}
    output.write_text(json.dumps(report, indent=1))
    if coordinator:
        print(describe(coordinator, batch))
    return 0 if state.get("status") == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
