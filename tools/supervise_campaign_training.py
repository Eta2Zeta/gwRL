#!/usr/bin/env python3
"""Durably supervise one resumable campaign training run, within a fixed budget.

The budget is active wall time, including process startup, retries and shutdown;
time while the supervisor is stopped does not replenish or consume it. Before
each short execution lease the supervisor atomically charges that lease, so a
crash cannot reset the budget. This conservatively overcounts a final partial
lease by at most one polling interval. It never treats unfinished games as done.

Example (run from the repository root)::

    .venv/bin/python tools/supervise_campaign_training.py \
      --control-dir studies/campaign/runs/example-control \
      --run-dir studies/campaign/runs/example --seconds 35000 -- \
      --calendar-rounds 3 --complete-episodes --batches 1000 \
      --parallel-envs 6 --threads 4 --cpu-budget 11

Repeat exactly that command to resume, including the original --seconds value.
The runner validates source/binary/checkpoint compatibility. An exhausted episode
guard requires an explicit --extend-episode-budget N on a subsequent invocation;
the supervisor does not change the learning configuration or horizon.
"""
from __future__ import annotations

import argparse
import ctypes
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import errno
import fcntl
from functools import lru_cache
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

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "campaign-training-supervisor-v1"
MEMORY_MARGIN_BYTES = 1_000_000_000
# Source/configuration errors normally exit 1 and must stop for inspection.
RETRYABLE_RETURNCODES = {-signal.SIGKILL, -signal.SIGSEGV, -signal.SIGBUS, 75}


def memory_metric() -> str:
    return ("sum of per-process max(RSS, macOS physical footprint including compressed pages)"
            if sys.platform == "darwin" else "sum of per-process RSS")


def monitor_error_details(error: BaseException, operation: str, *, root_pid: int | None = None) -> dict:
    """Bounded, JSON-safe diagnostics; callers retain their existing stop policy."""
    def describe(value):
        details = {"exception_type": type(value).__name__,
                   "error": f"{type(value).__name__}: {value}"[:2000]}
        for attribute in ("errno", "returncode", "timeout"):
            field = getattr(value, attribute, None)
            if type(field) in (int, float) and math.isfinite(field):
                details[attribute] = field
        pid = getattr(value, "monitor_pid", None)
        if type(pid) is int:
            details["sampled_pid"] = pid
        command = getattr(value, "cmd", None)
        if command is not None:
            details["command"] = ([str(part)[:256] for part in command[:32]]
                                  if isinstance(command, (list, tuple)) else str(command)[:2000])
        for attribute in ("stdout", "stderr"):
            field = getattr(value, attribute, None)
            if field:
                details[attribute] = str(field)[:2000]
        return details

    details = {"operation": operation, **describe(error)}
    if root_pid is not None:
        details["root_pid"] = root_pid
    contexts, seen = [], {id(error)}
    context = error.__cause__ or (None if error.__suppress_context__ else error.__context__)
    while context is not None and id(context) not in seen and len(contexts) < 3:
        seen.add(id(context))
        contexts.append(describe(context))
        context = context.__cause__ or (None if context.__suppress_context__ else context.__context__)
    if contexts:
        details["exception_context"] = contexts
    return details


@lru_cache(maxsize=1)
def _darwin_rusage_function():
    try:
        library = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
        function = library.proc_pid_rusage
    except (OSError, AttributeError) as error:
        raise OSError("macOS physical-footprint monitoring is unavailable") from error
    function.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
    function.restype = ctypes.c_int
    return function


def _darwin_physical_footprint(pid: int) -> int:
    # SDK-verified rusage_info_v4 ABI: 296 bytes, ri_resident_size at 64,
    # ri_phys_footprint at 72. The buffer belongs to this one sample only.
    buffer = ctypes.create_string_buffer(296)
    ctypes.set_errno(0)
    if _darwin_rusage_function()(pid, 4, buffer) != 0:
        number = ctypes.get_errno() or errno.EIO
        raise OSError(number, f"Cannot read macOS physical footprint for PID {pid}")
    return struct.unpack_from("=Q", buffer.raw, 72)[0]


def _process_disappeared(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except OSError:
        return False  # Permission failure does not prove that a process exited.
    # kill(pid, 0) succeeds for zombies. The fresh table omits them, and also
    # closes the race where a process exits immediately after the signal probe.
    return not any(row[0] == pid for row in _process_table())


def process_memory_charge(pid: int, resident_bytes: int) -> int:
    """Charge compressed Darwin pages too; a live API failure is never ignored."""
    if type(pid) is not int or not 0 < pid <= 2**31 - 1:
        raise ValueError("Memory sampling requires a positive C-int PID")
    if type(resident_bytes) is not int or resident_bytes < 0:
        raise ValueError("Resident memory must be a nonnegative byte count")
    if sys.platform != "darwin":
        return resident_bytes
    for attempt in range(3):
        try:
            return max(resident_bytes, _darwin_physical_footprint(pid))
        except OSError as error:
            error.monitor_pid = pid
            if _process_disappeared(pid):
                return 0
            # Concurrent samplers can briefly see each other's setuid ps
            # process. Its live footprint is inaccessible until ps exits.
            # Retry only these exit/permission races; an inaccessible process
            # that stays live still fails closed after at most 40 ms of waits.
            if error.errno not in (errno.EPERM, errno.ESRCH) or attempt == 2:
                raise
            time.sleep(0.02)


@dataclass(frozen=True)
class SupervisorConfig:
    seconds: float
    cpu_budget: int = 12
    memory_bytes: int = 30_000_000_000
    poll_seconds: float = 1.0
    shutdown_seconds: float = 60.0
    max_restarts: int = 2

    def __post_init__(self):
        for name in ("seconds", "poll_seconds", "shutdown_seconds"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if self.poll_seconds > 5:
            raise ValueError("Polling interval must be at most five seconds")
        if type(self.cpu_budget) is not int or not 2 <= self.cpu_budget <= 12:
            raise ValueError("CPU allowance must reserve a coordinator within the authorized 12 cores")
        if type(self.memory_bytes) is not int or not MEMORY_MARGIN_BYTES < self.memory_bytes <= 30_000_000_000:
            raise ValueError("Memory allowance must fit the authorized 30 GB with a safety margin")
        if type(self.max_restarts) is not int or not 0 <= self.max_restarts <= 10:
            raise ValueError("Automatic restarts must be bounded between zero and ten")


def atomic_json(path: Path, value):
    """Flush the new contents before replacing the last complete status file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".supervisor-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as handle:
            json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def exclusive_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("Another supervisor already owns this run") from error
        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()) + "\n")
        handle.flush()
        # Closing this descriptor releases our ownership, while an inherited
        # live worker keeps the shared open description locked. Explicit
        # LOCK_UN would also unlock that worker after a cleanup failure.
        yield handle


def _process_table():
    result = subprocess.run(["ps", "-axo", "pid=,ppid=,pgid=,rss=,stat="], capture_output=True,
                            text=True, check=True, timeout=5)
    # Exited grandchildren may briefly remain zombies awaiting their reaper;
    # they consume no compute and cannot receive a further stop signal.
    rows = [line.split() for line in result.stdout.splitlines() if line.strip()]
    return [tuple(map(int, row[:4])) for row in rows if not row[4].startswith("Z")]


def aggregate_rss(child_pid: int) -> int:
    """Legacy API name: sample the charged memory of this full process tree."""
    rows = _process_table()
    included = {os.getpid(), child_pid}
    while True:
        expanded = included | {pid for pid, parent, group, _ in rows
                               if parent in included or group == child_pid}
        if expanded == included:
            break
        included = expanded
    return sum(process_memory_charge(pid, resident * 1024)
               for pid, _, _, resident in rows if pid in included)


def process_group_alive(group: int | None) -> bool:
    return group is not None and any(pgid == group for _, _, pgid, _ in _process_table())


def _send(process, number):
    try:
        os.killpg(process.pid, number)
    except ProcessLookupError:
        pass


def _event(state: dict, kind: str, **details):
    state["events"].append({"kind": kind, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **details})


def _runner_status(run_dir: Path):
    path = run_dir / "manifest.json"
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return value.get("status")


def training_command(python: str, run_dir: Path, arguments: list[str], resume: bool | Path,
                     extension: int | None = None) -> list[str]:
    command = [python, "-m", "studies.campaign.run", "train", "--run-dir", str(run_dir)]
    command.extend(arguments)
    if resume:
        command.extend(["--resume", str(resume if isinstance(resume, Path) else run_dir / "checkpoint.pt")])
    if extension is not None:
        command.extend(["--extend-episode-budget", str(extension)])
    return command


def validate_training_arguments(arguments: list[str], config: SupervisorConfig):
    """Do not import torch in the lightweight coordinator or weaken runner checks."""
    forbidden = {"--run-dir", "--resume", "--extend-episode-budget", "--stop-after-waves"}
    if any(argument.split("=", 1)[0] in forbidden for argument in arguments):
        raise ValueError("Run location, resume, stopping and guard extension belong to the supervisor")
    # Explicit values make the aggregate CPU contract inspectable before launch.
    values = {}
    for name in ("threads", "parallel-envs", "cpu-budget"):
        flag = "--" + name
        matches = [index for index, token in enumerate(arguments) if token == flag or token.startswith(flag + "=")]
        if len(matches) != 1:
            raise ValueError(f"Training must explicitly supply one {flag}")
        index = matches[0]
        token = arguments[index]
        try:
            values[name] = int(token.split("=", 1)[1] if "=" in token else arguments[index + 1])
        except (ValueError, IndexError) as error:
            raise ValueError(f"Invalid {flag}") from error
    if min(values.values()) <= 0 or values["cpu-budget"] > config.cpu_budget - 1:
        raise ValueError("Training CPU budget must leave one core for its supervisor")
    if values["threads"] + values["parallel-envs"] + 1 > values["cpu-budget"]:
        raise ValueError("Tensor threads, search workers and coordinator exceed training CPU budget")


def supervise(control_dir: Path, run_dir: Path, config: SupervisorConfig, arguments: list[str], *,
              python: str = sys.executable, extension: int | None = None,
              resume_previous: bool = False,
              adopt_checkpoint: bool = False,
              working_directory: Path = ROOT,
              command_factory=training_command, rss_sampler=aggregate_rss) -> dict:
    """Run/restart the same job. Injectable child construction supports tiny tests."""
    control_dir, run_dir, working_directory = control_dir.resolve(), run_dir.resolve(), working_directory.resolve()
    if control_dir == run_dir or control_dir.is_relative_to(run_dir):
        raise ValueError("Control directory must be outside the runner's output directory")
    validate_training_arguments(arguments, config)
    if extension is not None and (type(extension) is not int or extension <= 0):
        raise ValueError("Episode guard extension must be a positive integer")
    control_dir.mkdir(parents=True, exist_ok=True)
    path = control_dir / "state.json"
    identity = {"run_dir": str(run_dir), "python": str(Path(python).resolve()),
                "working_directory": str(working_directory), "training_arguments": arguments,
                "adopt_checkpoint": adopt_checkpoint, "config": asdict(config)}
    # The location lock also excludes a second control directory targeting the
    # same output. Both locks survive a coordinator crash in the running child.
    run_lock_path = run_dir.parent / ("." + run_dir.name + ".training.lock")
    with exclusive_lock(control_dir / "supervisor.lock") as lock_handle, exclusive_lock(run_lock_path) as run_lock:
        if path.exists():
            state = json.loads(path.read_text())
            if state.get("schema") != SCHEMA or state.get("identity") != identity:
                raise ValueError("Supervisor identity or budget changed; use the original command")
            if process_group_alive(state.get("child_process_group")):
                raise RuntimeError("The previous training process group is still alive; refusing a duplicate")
            if state["status"] == "completed":
                return state
            _event(state, "supervisor_resumed", prior_status=state["status"])
        else:
            if run_dir.exists() and any(run_dir.iterdir()):
                if not adopt_checkpoint or not (run_dir / "checkpoint.pt").is_file():
                    raise ValueError("A new supervisor requires an empty training directory or explicit checkpoint adoption; existing output is preserved")
            elif adopt_checkpoint:
                raise ValueError("Checkpoint adoption requires an existing checkpoint.pt")
            state = {"schema": SCHEMA, "identity": identity, "status": "initialized", "events": [],
                     "charged_seconds": 0.0, "attempts": [], "error_restarts": 0,
                     "child_process_group": None, "aggregate_sampled_peak_rss_bytes": 0,
                     "timing_scope": "Conservatively reserved active wall time; startup, retries and shutdown included; downtime excluded",
                     "memory_metric": memory_metric(),
                     "memory_scope": "Supervisor and complete child process tree; " + memory_metric()
                                     + "; 1 GB safety margin, not a kernel allocation cap"}
            _event(state, "supervisor_initialized")
        if extension is not None:
            _event(state, "explicit_episode_budget_extension", new_limit=extension)
        if resume_previous:
            previous = run_dir / "checkpoint.pt.previous"
            if not previous.is_file():
                raise ValueError("No previous complete checkpoint exists")
            _event(state, "explicit_previous_checkpoint_restore", checkpoint=previous.name)
        started = time.monotonic()
        initially_charged = state["charged_seconds"]
        deadline = started + max(0.0, config.seconds - initially_charged)
        requested_stop = None

        def request_stop(number, _frame):
            nonlocal requested_stop
            requested_stop = signal.Signals(number).name

        handlers = {number: signal.signal(number, request_stop)
                    for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)}

        def persist():
            elapsed = max(0.0, time.monotonic() - started)
            reservation = elapsed + config.poll_seconds
            state["charged_seconds"] = min(config.seconds, max(state["charged_seconds"], initially_charged + reservation))
            state["remaining_seconds"] = max(0.0, config.seconds - state["charged_seconds"])
            atomic_json(path, state)

        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= config.shutdown_seconds:
                    state["status"] = "time_budget_exhausted"
                    persist()
                    return state
                if requested_stop:
                    state["status"] = "interrupted"
                    _event(state, "stop_requested", signal=requested_stop)
                    persist()
                    return state
                checkpoint = run_dir / "checkpoint.pt"
                resume = (run_dir / "checkpoint.pt.previous") if resume_previous else checkpoint if checkpoint.exists() else False
                attempt = len(state["attempts"]) + 1
                command = command_factory(python, run_dir, arguments, resume, extension)
                environment = {**os.environ, "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                               "OPENBLAS_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1",
                               "NUMEXPR_NUM_THREADS": "1", "PYTHONHASHSEED": "0"}
                stdout_path, stderr_path = control_dir / f"attempt-{attempt:03d}.stdout.log", control_dir / f"attempt-{attempt:03d}.stderr.log"
                record = {"number": attempt, "command": command, "resume": str(resume) if resume else None,
                          "stdout": stdout_path.name, "stderr": stderr_path.name}
                state["attempts"].append(record)
                state["status"] = "starting"
                persist()  # Charge a lease before launching any child compute.
                with stdout_path.open("a") as stdout, stderr_path.open("a") as stderr:
                    process = subprocess.Popen(command, cwd=working_directory, env=environment, stdout=stdout,
                                               stderr=stderr, start_new_session=True,
                                               pass_fds=(lock_handle.fileno(), run_lock.fileno()))
                    state["child_process_group"] = process.pid
                    state["status"] = "running"
                    _event(state, "child_started", attempt=attempt, pid=process.pid, resume=bool(resume))
                    persist()
                    stop_reason = None
                    stopping_at = None
                    while process.poll() is None:
                        now = time.monotonic()
                        # Keep monitoring while safe shutdown is pending: a
                        # checkpoint or unfinished wave can still allocate RAM.
                        try:
                            resident = rss_sampler(process.pid)
                            state["aggregate_sampled_peak_rss_bytes"] = max(state["aggregate_sampled_peak_rss_bytes"], resident)
                        except (OSError, ValueError, subprocess.SubprocessError) as error:
                            resident = None
                            _event(state, "memory_monitor_error", phase="worker",
                                   **monitor_error_details(error, "aggregate_memory_sample", root_pid=process.pid))
                            if process.poll() is None and stop_reason is None:
                                stop_reason = "memory_monitor_failure"
                                stopping_at = now
                                _send(process, signal.SIGTERM)
                        if resident is not None and resident >= config.memory_bytes:
                            stop_reason = "memory_limit"
                            _event(state, "forced_stop", reason=stop_reason, resident_bytes=resident)
                            record["forced_kill"] = True
                            _send(process, signal.SIGKILL)
                            stopping_at = now
                        if stop_reason is None:
                            if requested_stop:
                                stop_reason = "interrupted"
                            elif now >= deadline - config.shutdown_seconds:
                                stop_reason = "time_budget_exhausted"
                            if resident is not None and resident >= config.memory_bytes - MEMORY_MARGIN_BYTES:
                                stop_reason = "memory_limit"
                            if stop_reason:
                                stopping_at = now
                                state["status"] = "stopping"
                                _event(state, "graceful_stop_requested", reason=stop_reason, signal=requested_stop)
                                _send(process, signal.SIGTERM)
                        elif now >= min(deadline, stopping_at + config.shutdown_seconds):
                            _event(state, "forced_stop", reason=stop_reason)
                            record["forced_kill"] = True
                            _send(process, signal.SIGKILL)
                        persist()
                        time.sleep(min(config.poll_seconds, max(0.01, deadline - time.monotonic())))
                    process.wait()
                # A crashed process leader does not imply that its descendant
                # workers stopped. Reap their process group before any retry.
                if process_group_alive(process.pid):
                    _event(state, "orphan_group_stop", group=process.pid)
                    _send(process, signal.SIGTERM)
                    cleanup_deadline = min(deadline, time.monotonic() + config.shutdown_seconds)
                    while process_group_alive(process.pid) and time.monotonic() < cleanup_deadline:
                        try:
                            resident = rss_sampler(process.pid)
                            state["aggregate_sampled_peak_rss_bytes"] = max(state["aggregate_sampled_peak_rss_bytes"], resident)
                            if resident >= config.memory_bytes - MEMORY_MARGIN_BYTES:
                                stop_reason = "memory_limit"
                                _send(process, signal.SIGKILL)
                                break
                        except (OSError, ValueError, subprocess.SubprocessError) as error:
                            _event(state, "memory_monitor_error", phase="orphan_cleanup",
                                   **monitor_error_details(error, "aggregate_memory_sample", root_pid=process.pid))
                            stop_reason = "memory_monitor_failure"
                            _send(process, signal.SIGKILL)
                            break
                        persist()
                        time.sleep(config.poll_seconds)
                    if process_group_alive(process.pid):
                        _send(process, signal.SIGKILL)
                        for _ in range(20):
                            if not process_group_alive(process.pid):
                                break
                            time.sleep(0.05)
                    if process_group_alive(process.pid):
                        raise RuntimeError("Previous worker process group did not stop; refusing to retry")
                state["child_process_group"] = None
                record["returncode"] = process.returncode
                record["runner_status"] = _runner_status(run_dir)
                _event(state, "child_exited", attempt=attempt, returncode=process.returncode,
                       runner_status=record["runner_status"], stop_reason=stop_reason)
                if stop_reason:
                    state["status"] = stop_reason
                elif process.returncode == 0 and record["runner_status"] == "completed":
                    state["status"] = "completed"
                elif record["runner_status"] == "episode_budget_exhausted" and process.returncode == 2:
                    state["status"] = "episode_budget_exhausted"
                elif record["runner_status"] == "interrupted" and process.returncode in (0, 130):
                    state["status"] = "interrupted"
                elif process.returncode in RETRYABLE_RETURNCODES and checkpoint.exists() and state["error_restarts"] < config.max_restarts:
                    state["error_restarts"] += 1
                    state["status"] = "retrying"
                    _event(state, "bounded_error_retry", count=state["error_restarts"])
                    persist()
                    resume_previous = False
                    if extension is not None:
                        manifest = run_dir / "manifest.json"
                        value = json.loads(manifest.read_text()) if manifest.exists() else {}
                        if value.get("runner", {}).get("episode_wave_limit", 0) >= extension:
                            extension = None  # The checkpoint records the guard increase.
                    continue
                else:
                    state["status"] = "worker_error"
                persist()
                return state
        except BaseException as error:
            state["status"] = "supervisor_error"
            _event(state, "supervisor_error", error_type=type(error).__name__, message=str(error))
            persist()
            raise
        finally:
            # Unexpected coordinator exceptions still request the runner's safe save.
            if "process" in locals() and process.poll() is None:
                _send(process, signal.SIGTERM)
                try:
                    process.wait(timeout=min(config.shutdown_seconds, max(0.01, deadline - time.monotonic())))
                except subprocess.TimeoutExpired:
                    _send(process, signal.SIGKILL)
                    process.wait(timeout=5)
                state["child_process_group"] = None
                state["status"] = "supervisor_error"
                persist()
            for number, handler in handlers.items():
                signal.signal(number, handler)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--control-dir", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--working-directory", type=Path, default=ROOT,
                        help="Frozen runtime checkout used by the child; fixed across resumes")
    parser.add_argument("--seconds", type=float, required=True, help="Original fixed active-wall allowance; never reset on resume")
    parser.add_argument("--cpu-budget", type=int, default=12)
    parser.add_argument("--memory-bytes", type=int, default=30_000_000_000)
    parser.add_argument("--max-restarts", type=int, default=2)
    parser.add_argument("--shutdown-seconds", type=float, default=60)
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    parser.add_argument("--adopt-checkpoint", action="store_true",
                        help="Explicitly adopt an existing initialized checkpoint on the first controller launch")
    parser.add_argument("--extend-episode-budget", type=int)
    parser.add_argument("--resume-previous-checkpoint", action="store_true",
                        help="Explicit recovery of checkpoint.pt.previous; runtime validation still applies")
    parser.add_argument("training_arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    arguments = args.training_arguments[1:] if args.training_arguments[:1] == ["--"] else args.training_arguments
    config = SupervisorConfig(seconds=args.seconds, cpu_budget=args.cpu_budget, memory_bytes=args.memory_bytes,
                              max_restarts=args.max_restarts, shutdown_seconds=args.shutdown_seconds,
                              poll_seconds=args.poll_seconds)
    state = supervise(args.control_dir, args.run_dir, config, arguments, extension=args.extend_episode_budget,
                      resume_previous=args.resume_previous_checkpoint, adopt_checkpoint=args.adopt_checkpoint,
                      working_directory=args.working_directory)
    print(json.dumps({key: state.get(key) for key in ("status", "charged_seconds", "remaining_seconds", "aggregate_sampled_peak_rss_bytes")}), flush=True)
    return 0 if state["status"] in {"completed", "time_budget_exhausted", "interrupted"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
