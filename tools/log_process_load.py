#!/usr/bin/env python3
"""Log the CPU load of a training batch and of the rest of the Mac, and summarize it.

`record` samples every few seconds, until the process given by --pid ends:
every process's CPU time and memory (ps), and macOS's own accounting of each
process in the tree under --pid (proc_pid_rusage, RUSAGE_INFO_V6): its CPU time
on all cores and on the performance cores, the time it was runnable (running,
or ready to run and waiting for a core), its instructions and cycles on each
kind of core, and its CPU time by quality-of-service class.

`summarize` reads such a log. While the batch's game processes run, it reports
the cores the batch and everything else kept busy in half-minute windows, and
for the coordinator (the trainer process, which answers every game thread's
evaluations), the game processes (the trainer's Python children) and the rest
of the tree: the share of CPU time on performance cores, the time spent waiting
for a core, instructions per cycle, clock rates, and how much work a second on
an efficiency core does compared with a second on a performance core.

Start the batch, then the logger with the batch's process id; the supervisor's
is enough, since its trainer and game processes are in its tree:

    .venv/bin/python tools/log_process_load.py record --pid PID --output LOAD.jsonl
    .venv/bin/python tools/log_process_load.py summarize LOAD.jsonl

macOS only: other systems have no proc_pid_rusage.
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

# struct rusage_info_v6 in <sys/resource.h>, after its 16-byte uuid.
_FIELDS = ("user_time", "system_time", "pkg_idle_wkups", "interrupt_wkups", "pageins", "wired_size",
           "resident_size", "phys_footprint", "proc_start_abstime", "proc_exit_abstime", "child_user_time",
           "child_system_time", "child_pkg_idle_wkups", "child_interrupt_wkups", "child_pageins",
           "child_elapsed_abstime", "diskio_bytesread", "diskio_byteswritten", "cpu_time_qos_default",
           "cpu_time_qos_maintenance", "cpu_time_qos_background", "cpu_time_qos_utility", "cpu_time_qos_legacy",
           "cpu_time_qos_user_initiated", "cpu_time_qos_user_interactive", "billed_system_time",
           "serviced_system_time", "logical_writes", "lifetime_max_phys_footprint", "instructions", "cycles",
           "billed_energy", "serviced_energy", "interval_max_phys_footprint", "runnable_time", "flags",
           "user_ptime", "system_ptime", "pinstructions", "pcycles", "energy_nj", "penergy_nj",
           "secure_time_in_system", "secure_ptime_in_system", "neural_footprint",
           "lifetime_max_neural_footprint", "interval_max_neural_footprint")
KEPT = ("user_time", "system_time", "user_ptime", "system_ptime", "runnable_time", "instructions", "cycles",
        "pinstructions", "pcycles", "cpu_time_qos_default", "cpu_time_qos_maintenance",
        "cpu_time_qos_background", "cpu_time_qos_utility", "cpu_time_qos_legacy",
        "cpu_time_qos_user_initiated", "cpu_time_qos_user_interactive", "phys_footprint", "resident_size")
RUSAGE_INFO_V6 = 6


class _RusageV6(ctypes.Structure):
    _fields_ = [("uuid", ctypes.c_uint8 * 16)] + [(name, ctypes.c_uint64) for name in _FIELDS] + \
               [("reserved", ctypes.c_uint64 * 9)]


class _Timebase(ctypes.Structure):
    _fields_ = [("numer", ctypes.c_uint32), ("denom", ctypes.c_uint32)]


def tick_seconds() -> float:
    """Seconds per unit of rusage time: Mach absolute time, 1/24 µs on Apple silicon."""
    timebase = _Timebase()
    ctypes.CDLL(None).mach_timebase_info(ctypes.byref(timebase))
    return timebase.numer / timebase.denom / 1e9


def reader():
    library = ctypes.CDLL(ctypes.util.find_library("proc") or "/usr/lib/libproc.dylib", use_errno=True)
    library.proc_pid_rusage.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(_RusageV6)]

    def read(pid: int) -> dict | None:
        info = _RusageV6()
        if library.proc_pid_rusage(pid, RUSAGE_INFO_V6, ctypes.byref(info)) != 0:
            return None
        return {name: getattr(info, name) for name in KEPT}
    return read


def _cpu_seconds(text: str) -> float:
    seconds = 0.0
    for part in text.split(":"):
        seconds = seconds * 60 + float(part)
    return seconds


def record(pid: int, output: Path, interval: float) -> None:
    read = reader()
    with output.open("a") as handle:
        while True:
            now = time.time()
            listing = subprocess.run(["ps", "-axo", "pid=,ppid=,cputime=,rss=,comm="],
                                     capture_output=True, text=True).stdout
            rows, children = [], {}
            for line in listing.splitlines():
                fields = line.split(None, 4)
                if len(fields) < 5:
                    continue
                rows.append([int(fields[0]), int(fields[1]), _cpu_seconds(fields[2]), int(fields[3]),
                             fields[4][-60:]])
                children.setdefault(int(fields[1]), []).append(int(fields[0]))
            family, stack = [], [pid]
            while stack:
                member = stack.pop()
                family.append(member)
                stack.extend(children.get(member, []))
            usage = {member: value for member in family if (value := read(member)) is not None}
            handle.write(json.dumps({"t": now, "ps": rows, "family": family, "rusage": usage}) + "\n")
            handle.flush()
            if not any(row[0] == pid for row in rows):
                return
            time.sleep(max(0.0, interval - (time.time() - now)))


def summarize(path: Path, window: float = 30.0) -> dict:
    samples = []
    for line in path.read_text().splitlines():
        entry = json.loads(line)
        family, rows = set(entry["family"]), {row[0]: row for row in entry["ps"]}
        children = {}
        for row in entry["ps"]:
            if row[0] in family:
                children.setdefault(row[1], []).append(row[0])
        trainer = max((member for member in family if member in children),
                      key=lambda member: len(children[member]), default=None)
        games = [child for child in children.get(trainer, []) if "python" in rows[child][4].lower()]
        samples.append({"t": entry["t"], "rows": rows, "family": family, "trainer": trainer, "games": games,
                        "rusage": {int(key): value for key, value in entry["rusage"].items()}})
    playing = [sample for sample in samples if len(sample["games"]) >= 2]
    if not playing:
        return {"error": "no sample with two or more game processes"}
    start, end = playing[0]["t"], playing[-1]["t"]

    windows, batch, other, elapsed, opened, previous = [], 0.0, 0.0, 0.0, start, playing[0]
    for sample in playing[1:]:
        for pid, row in sample["rows"].items():
            before = previous["rows"].get(pid)
            spent = row[2] - (before[2] if before and before[4] == row[4] else 0.0)
            if spent > 0:
                if pid in sample["family"]:
                    batch += spent
                else:
                    other += spent
        elapsed += sample["t"] - previous["t"]
        if sample["t"] - opened >= window:
            windows.append({"batch_cores": round(batch / elapsed, 2), "other_cores": round(other / elapsed, 2)})
            batch, other, elapsed, opened = 0.0, 0.0, 0.0, sample["t"]
        previous = sample

    first, last = {}, {}
    for sample in samples:
        if start <= sample["t"] <= end:
            for pid, value in sample["rusage"].items():
                first.setdefault(pid, (sample, value))
                last[pid] = (sample, value)
    tick = tick_seconds()
    totals = {}
    for pid, (after, value) in last.items():
        before, earlier = first[pid]
        change = {name: value[name] - earlier[name] for name in value if name not in ("phys_footprint", "resident_size")}
        role = ("coordinator" if pid in (before["trainer"], after["trainer"]) else
                "game processes" if pid in before["games"] or pid in after["games"] else "rest of the tree")
        if role == "game processes" and (change["user_time"] + change["system_time"]) * tick < 10:
            role = "rest of the tree"  # Such as multiprocessing's resource tracker.
        total = totals.setdefault(role, dict.fromkeys(change, 0) | {"processes": 0})
        total["processes"] += 1
        for name, amount in change.items():
            total[name] += amount
    processes = {}
    for role, total in totals.items():
        cpu = (total["user_time"] + total["system_time"]) * tick
        performance = (total["user_ptime"] + total["system_ptime"]) * tick
        efficiency = cpu - performance
        e_instructions, e_cycles = total["instructions"] - total["pinstructions"], total["cycles"] - total["pcycles"]
        p_rate = total["pinstructions"] / performance if performance else 0.0
        e_rate = e_instructions / efficiency if efficiency > 0 else 0.0
        ratio = e_rate / p_rate if p_rate and e_rate else None
        processes[role] = {
            "processes": total["processes"], "cpu_seconds": round(cpu, 1),
            "performance_core_share": round(performance / cpu, 3) if cpu else None,
            "waiting_for_a_core_seconds": round(total["runnable_time"] * tick - cpu, 1),
            "waiting_per_cpu_second": round((total["runnable_time"] * tick - cpu) / cpu, 3) if cpu else None,
            "instructions": total["instructions"], "cycles": total["cycles"],
            "instructions_per_cycle": {
                "performance": round(total["pinstructions"] / total["pcycles"], 2) if total["pcycles"] else None,
                "efficiency": round(e_instructions / e_cycles, 2) if e_cycles > 0 else None},
            "gigahertz": {"performance": round(total["pcycles"] / performance / 1e9, 2) if performance else None,
                          "efficiency": round(e_cycles / efficiency / 1e9, 2) if efficiency > 0 else None},
            "efficiency_second_vs_performance_second": round(ratio, 3) if ratio else None,
            "performance_core_equivalent_cpu_seconds": round(performance + efficiency * (ratio or 1.0), 1),
            "cpu_seconds_by_qos": {name.removeprefix("cpu_time_qos_"): round(total[name] * tick, 1)
                                   for name in total if name.startswith("cpu_time_qos_") and total[name] * tick >= 0.05},
        }
    return {"seconds_with_game_processes": round(end - start, 1),
            "batch_cores": {"mean_window": round(statistics.mean(w["batch_cores"] for w in windows), 2),
                            "median_window": round(statistics.median(w["batch_cores"] for w in windows), 2),
                            "highest_window": max(w["batch_cores"] for w in windows)} if windows else None,
            "other_work_cores": {"mean_window": round(statistics.mean(w["other_cores"] for w in windows), 2),
                                 "median_window": round(statistics.median(w["other_cores"] for w in windows), 2)}
            if windows else None,
            "windows": windows, "processes": processes}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    logging = commands.add_parser("record", help="Sample until the process ends")
    logging.add_argument("--pid", type=int, required=True, help="The supervisor's or the trainer's process id")
    logging.add_argument("--output", type=Path, required=True, help="JSON lines, appended to")
    logging.add_argument("--interval", type=float, default=5.0, help="Seconds between samples")
    summary = commands.add_parser("summarize", help="Summarize a recorded log as JSON")
    summary.add_argument("log", type=Path)
    summary.add_argument("--window", type=float, default=30.0, help="Seconds per load window")
    args = parser.parse_args(argv)
    if sys.platform != "darwin":
        parser.error("proc_pid_rusage exists on macOS only")
    if args.command == "record":
        record(args.pid, args.output, args.interval)
    else:
        print(json.dumps(summarize(args.log, args.window), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
