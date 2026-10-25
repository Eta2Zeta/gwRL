#!/usr/bin/env python3
"""Independently enforce a campaign experiment's persisted deadline and RAM cap.

The pipeline starts this small standard-library process in its own session. It
continues watching registered worker groups if the pipeline or training
supervisor disappears. It never signals its own or the pipeline's shell group.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import json
import math
import os
from pathlib import Path
import signal
import shlex
import subprocess
import tempfile
import time

SCHEMA = "campaign-deadline-guardian-v1"


@dataclass(frozen=True)
class Process:
    pid: int
    parent: int
    group: int
    rss: int
    identity: str
    command: str


def process_table() -> list[Process]:
    result = subprocess.run(["ps", "-axo", "pid=,ppid=,pgid=,rss=,stat=,lstart=,command="],
                            capture_output=True, text=True, check=True, timeout=5)
    values = []
    for line in result.stdout.splitlines():
        row = line.split(maxsplit=10)
        if len(row) < 11 or row[4].startswith("Z"):
            continue
        values.append(Process(*map(int, row[:3]), int(row[3]) * 1024,
                              " ".join(row[5:10]), row[10]))
    return values


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def atomic_json(path: Path, value: dict) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=".guardian-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as handle:
            json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def guardian_lock(path: Path):
    with path.open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()) + "\n")
        handle.flush()
        try:
            yield True
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _positive(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{label} must be finite and positive")
    return float(value)


def run_command(process: Process, run_root: Path) -> bool:
    """A durable registry alone is insufficient after a numeric PGID is reused."""
    try:
        arguments = shlex.split(process.command)
    except ValueError:
        return False
    scripts = {Path(argument).name for argument in arguments}
    flag = None
    if "run_three_round_experiment.py" in scripts:
        flag = "--plan"
    elif "supervise_campaign_training.py" in scripts:
        flag = "--control-dir"
    elif "evaluate_three_round_campaign.py" in scripts:
        flag = "--output-dir"
    elif any(arguments[index:index + 2] == ["-m", "studies.campaign.run"]
             for index in range(len(arguments) - 1)):
        flag = "--run-dir"
    if flag is None:
        return False
    for index, argument in enumerate(arguments):
        try:
            location = (argument.split("=", 1)[1] if argument.startswith(flag + "=") else
                        arguments[index + 1] if argument == flag else None)
        except IndexError:
            return False
        if location is not None and Path(location).resolve().is_relative_to(run_root):
            return True
    return False


def pipeline_command(process: Process, run_root: Path, plan: dict) -> bool:
    if "run_three_round_experiment.py" not in process.command or str(run_root) not in process.command:
        return False
    try:
        arguments = shlex.split(process.command)
        location = Path(arguments[arguments.index("--plan") + 1]).resolve()
    except (ValueError, IndexError):
        return False
    return location.is_relative_to(run_root) and read_json(location) == plan


def guard(plan_path: Path, *, sampler=process_table, now=time.time, sleep=time.sleep,
          send_group=os.killpg, send_process=os.kill) -> dict:
    plan_path = plan_path.resolve()
    plan = read_json(plan_path)
    run_root = Path(plan["run_root"]).resolve()
    deadline = _positive(plan["deadline_epoch"], "deadline_epoch")
    hard_memory = _positive(plan.get("memory_bytes", 26_000_000_000), "memory_bytes")
    soft_memory = _positive(plan.get("memory_soft_bytes", 25_000_000_000), "memory_soft_bytes")
    shutdown = _positive(plan.get("shutdown_seconds", 180), "shutdown_seconds")
    poll = _positive(plan.get("poll_seconds", 0.5), "poll_seconds")
    if hard_memory > 26_000_000_000 or soft_memory > hard_memory or poll > 5:
        raise ValueError("Guardian limits must fit 26 GB, soft <= hard, and at most five-second polling")
    run_root.mkdir(parents=True, exist_ok=True)
    state_path = run_root / "guardian-state.json"
    own_pid, own_group = os.getpid(), os.getpgrp()
    with guardian_lock(run_root / "guardian.lock") as acquired:
        if not acquired:
            return {"schema": SCHEMA, "status": "already_running"}
        previous = read_json(state_path)
        if previous and (previous.get("schema") != SCHEMA or previous.get("deadline_epoch") != deadline):
            raise ValueError("Guardian state belongs to another deadline or schema")
        state = {"schema": SCHEMA, "guardian_pid": own_pid, "status": "watching",
            "deadline_epoch": deadline, "memory_bytes": hard_memory, "memory_soft_bytes": soft_memory,
            "known_process_groups": previous.get("known_process_groups", []),
            "group_leaders": previous.get("group_leaders", {}),
            "group_members": previous.get("group_members", {}),
            "pipeline_identities": previous.get("pipeline_identities", {}),
            "peak_rss_bytes": previous.get("peak_rss_bytes", 0), "events": previous.get("events", []),
            "event_reason": previous.get("event_reason"), "started_epoch": now()}
        known = {group for group in state["known_process_groups"] if type(group) is int and group > 1}
        empty_groups = set()
        term_groups, kill_groups, term_pipelines, kill_pipelines = set(), set(), set(), set()
        stopping = previous.get("event_reason") if previous.get("status") == "stopping" else None
        stop_deadline = previous.get("stop_deadline_epoch", deadline)
        interrupted = False

        def event(reason, **details):
            state["events"].append({"epoch": now(), "reason": reason, **details})
            state["events"] = state["events"][-200:]
            state["event_reason"] = reason

        def stop(_number, _frame):
            nonlocal interrupted
            interrupted = True

        handlers = {number: signal.signal(number, stop) for number in (signal.SIGTERM, signal.SIGINT)}
        try:
            while True:
                rows = sampler()
                by_pid = {process.pid: process for process in rows}
                pipeline = read_json(run_root / "pipeline-state.json")
                training = read_json(run_root / "training-control" / "state.json")
                pipeline_pid = pipeline.get("pipeline_pid")
                candidate = by_pid.get(pipeline_pid)
                accepted_pipeline = None
                if candidate is not None and candidate.pid > 1 and candidate.pid != own_pid:
                    identity = state["pipeline_identities"].get(str(candidate.pid))
                    matches_command = pipeline_command(candidate, run_root, plan)
                    if candidate.pid == os.getppid() or identity == candidate.identity or matches_command:
                        accepted_pipeline = candidate
                        state["pipeline_identities"][str(candidate.pid)] = candidate.identity
                forbidden = {own_group, 0, 1}
                if accepted_pipeline is not None:
                    forbidden.add(accepted_pipeline.group)
                # Persisted groups bridge coordinator death/reparenting. A
                # changed group leader birth invalidates a reused numeric PID.
                registered = [pipeline.get("child_process_group"), training.get("child_process_group"),
                              *pipeline.get("known_process_groups", [])]
                roots = {accepted_pipeline.pid} if accepted_pipeline is not None else set()
                for group in tuple(known):
                    leader = by_pid.get(group)
                    recorded = state["group_leaders"].get(str(group))
                    members = [process for process in rows if process.group == group]
                    saved_members = state["group_members"].get(str(group), {})
                    verified_member = any(saved_members.get(str(process.pid)) == process.identity
                                          for process in members)
                    if leader is not None and recorded is not None and leader.identity != recorded:
                        empty_groups.add(group)
                        known.discard(group)
                        event("reused_process_group_ignored", group=group)
                    elif not verified_member and not (leader is not None and recorded == leader.identity) and not any(
                            run_command(process, run_root) for process in members):
                        known.discard(group)
                        empty_groups.add(group)
                    elif group not in empty_groups:
                        roots.update(process.pid for process in rows if process.group == group)
                descendants = set(roots)
                while True:
                    expanded = descendants | {process.pid for process in rows if process.parent in descendants}
                    if expanded == descendants:
                        break
                    descendants = expanded
                discovered = {process.group for process in rows if process.pid in descendants and
                              (accepted_pipeline is None or process.pid != accepted_pipeline.pid)}
                for group in [*registered, *discovered]:
                    if type(group) is not int or group <= 1 or group in forbidden:
                        continue
                    if group in empty_groups and group not in discovered:
                        continue
                    members = [process for process in rows if process.group == group]
                    if not members:
                        continue
                    # Fresh descendants are direct evidence. Orphan recovery
                    # from a state file also requires the pinned run location
                    # and a known experiment command, or an already verified
                    # live group identity retained by this guardian.
                    if group not in discovered and group not in known and not any(
                            run_command(process, run_root) for process in members):
                        continue
                    known.add(group)
                    empty_groups.discard(group)
                    if group in by_pid:
                        state["group_leaders"][str(group)] = by_pid[group].identity
                active_groups = {group for group in known - empty_groups - forbidden
                                 if any(process.group == group for process in rows)}
                empty_groups.update(known - active_groups - forbidden)
                owned_pids = {process.pid for process in rows if process.group in active_groups}
                owned_pids.add(own_pid)
                if accepted_pipeline is not None:
                    owned_pids.add(accepted_pipeline.pid)
                rss = sum(process.rss for process in rows if process.pid in owned_pids)
                state["peak_rss_bytes"] = max(state["peak_rss_bytes"], rss)
                state.update(sample_epoch=now(), rss_bytes=rss,
                             known_process_groups=sorted(active_groups),
                             group_members={str(group): {str(process.pid): process.identity for process in rows
                                            if process.group == group} for group in active_groups},
                             active_process_groups=sorted(active_groups),
                             pipeline_pid=accepted_pipeline.pid if accepted_pipeline is not None else None)
                current = now()
                if stopping is None:
                    if rss >= hard_memory:
                        stopping = "hard_memory_limit"
                        stop_deadline = current
                    elif rss >= soft_memory:
                        stopping = "soft_memory_limit"
                        stop_deadline = min(deadline, current + shutdown)
                    elif interrupted:
                        stopping = "guardian_stop_signal"
                        stop_deadline = min(deadline, current + shutdown)
                    elif current >= deadline - shutdown:
                        stopping = "deadline_shutdown"
                        stop_deadline = deadline
                    if stopping is not None:
                        event(stopping)
                if stopping is not None:
                    # RSS remains sampled every iteration during graceful
                    # shutdown; a hard-memory breach escalates immediately.
                    kill = current >= min(stop_deadline, deadline) or rss >= hard_memory
                    if rss >= hard_memory and state["event_reason"] != "hard_memory_limit":
                        event("hard_memory_limit")
                    number = signal.SIGKILL if kill else signal.SIGTERM
                    sent_groups = kill_groups if kill else term_groups
                    for group in active_groups - sent_groups:
                        try:
                            send_group(group, number)
                            event("group_signal", group=group, signal=number.name)
                        except ProcessLookupError:
                            pass
                        sent_groups.add(group)
                    sent_pipelines = kill_pipelines if kill else term_pipelines
                    if accepted_pipeline is not None:
                        key = (accepted_pipeline.pid, accepted_pipeline.identity)
                        if key not in sent_pipelines:
                            try:
                                send_process(accepted_pipeline.pid, number)
                                event("pipeline_signal", pid=accepted_pipeline.pid, signal=number.name)
                            except ProcessLookupError:
                                pass
                            sent_pipelines.add(key)
                    state.update(status="stopping", stop_deadline_epoch=stop_deadline,
                                 stop_reason=stopping)
                    if not active_groups and accepted_pipeline is None:
                        state["status"] = "budget_exhausted" if stopping == "deadline_shutdown" else "stopped"
                        atomic_json(state_path, state)
                        return state
                elif pipeline.get("status") in {"completed", "budget_exhausted"} and not active_groups:
                    state["status"] = "completed"
                    event("pipeline_terminal_no_live_groups", pipeline_status=pipeline["status"])
                    atomic_json(state_path, state)
                    return state
                atomic_json(state_path, state)
                sleep(min(poll, max(0.01, deadline - now())))
        finally:
            for number, handler in handlers.items():
                signal.signal(number, handler)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args(argv)
    result = guard(args.plan)
    print(json.dumps({"status": result["status"], "guardian_pid": result.get("guardian_pid")}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
