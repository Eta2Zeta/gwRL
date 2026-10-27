#!/usr/bin/env python3
"""Guarded native-only recruitment worker scaling, with exact rule outputs.

Stage counters sum elapsed lane-wall durations, including waits/preemption;
they are not CPU time or proof of a particular lock/allocator cause. Complete
State/history/RNG and keys are checked outside timing. No MPS work or reserve.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import gc
import hashlib
from importlib import metadata
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from tools.benchmark_campaign_resident_recruitment_chance import FAMILIES, canonical_native, lanes, require_exact, templates
from tools.benchmark_campaign_device_state import atomic_json, require

SCHEMA = "campaign-native-worker-stage-profile-v1"
WORKERS = (1, 2, 4, 6, 8, 10)
STAGES = ("guard_worker_seconds", "resolve_worker_seconds", "output_key_worker_seconds")
MARGIN = 500_000_000


@dataclass(frozen=True)
class NativeWorkerConfig:
    seed: int = 1951
    batch_size: int = 512
    trials: int = 3
    worker_counts: tuple[int, ...] = WORKERS
    families: tuple[str, ...] = FAMILIES
    threads: int = 2
    cpu_budget: int = 12
    memory_bytes: int = 4_000_000_000
    seconds: float = 240.

    def __post_init__(self):
        require(type(self.seed) is int and 0 <= self.seed < 2**64, "Seed must be uint64")
        require(type(self.batch_size) is int and self.batch_size > 0 and type(self.trials) is int and self.trials > 0,
                "Lanes and trials must be positive integers; no truncation")
        require(self.worker_counts and tuple(sorted(set(self.worker_counts))) == self.worker_counts and
                all(type(k) is int and 1 <= k <= 10 for k in self.worker_counts), "Use distinct increasing native worker counts 1..10")
        require(self.families and len(set(self.families)) == len(self.families) and not set(self.families)-set(FAMILIES), "Select distinct supported fixture families")
        require(type(self.threads) is int and self.threads == 2 and type(self.cpu_budget) is int and
                max(self.worker_counts)+self.threads <= self.cpu_budget <= min(12, os.cpu_count() or 1), "Native workers plus two reserved threads must fit twelve cores")
        require(type(self.memory_bytes) is int and MARGIN < self.memory_bytes <= 4_000_000_000, "CPU-only complete-tree guard is at most4GB")
        require(type(self.seconds) in (int,float) and math.isfinite(self.seconds) and 0 < self.seconds <= 240, "Shared deadline must be at most240seconds")


def executions(config): return (("serial", None), *((f"pool_{k}", k) for k in config.worker_counts))


def provenance():
    import gwrl_cpp
    def git(*args): return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()
    files = git("ls-files").splitlines()
    return {"commit":git("rev-parse","HEAD"),"branch":git("branch","--show-current"),"git_status":git("status","--porcelain"),
        "root":str(ROOT),"python":sys.executable,"python_version":sys.version,
        "native":{"path":str(Path(gwrl_cpp.__file__).resolve()),"sha256":hashlib.sha256(Path(gwrl_cpp.__file__).read_bytes()).hexdigest()},
        "tracked_source_sha256":{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files},
        "tool_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "package_versions":{name:metadata.version(name) for name in ("numpy","torch")},
        "torch_imported":"torch" in sys.modules,"gpu_runtime_or_allocator_initialized":False}


def invoke_profile(context, envs, keys, trials, workers, *, probe=None, pool_factory=None):
    """Own one pool entirely inside this call, including exception unwinding."""
    if probe is None:
        import gwrl_cpp
        probe = gwrl_cpp.campaign_recruitment_chance_benchmark
    if pool_factory is None:
        import gwrl_cpp
        pool_factory = gwrl_cpp.CampaignDiagnosticPool
    before = time.perf_counter(); pool = None
    try:
        if workers is not None: pool = pool_factory(workers)
        startup = time.perf_counter()-before
        result = probe(context,envs,keys,trials,pool=pool,profile=True)
    finally:
        release = time.perf_counter(); pool = None
        release_seconds = time.perf_counter()-release
    return result,{"pool_creation_wall_seconds":startup,"pool_release_wall_seconds":release_seconds}


def valid_profile(value, config, workers):
    def durations(values):
        return isinstance(values,list) and len(values)==config.trials and all(type(t) in (int,float) and math.isfinite(t) and t >= 0 for t in values)
    return (isinstance(value,dict) and value.get("schema")=="campaign-native-recruitment-chance-timing-v1" and
        value.get("batch_size")==config.batch_size and value.get("trials")==config.trials and
        value.get("workers")== (workers if workers is not None else 1) and
        value.get("execution")== ("persistent_native_pool" if workers is not None else "serial_native") and
        value.get("profiled") is True and value.get("source_unchanged") is True and value.get("repeated_outputs_exact") is True and
        all(durations(value.get(k)) for k in ("seconds","input_clone_seconds","verification_seconds",*STAGES)) and
        isinstance(value.get("output_engine_keys"),list) and len(value["output_engine_keys"])==config.batch_size and
        all(isinstance(k,str) and len(k)==64 and not set(k)-set("0123456789abcdef") for k in value["output_engine_keys"]))


def summarize_profile(result):
    """Only derived elapsed-wall arithmetic, deliberately no CPU-time labels."""
    import statistics
    med = {name:statistics.median(result[name]) for name in ("seconds","input_clone_seconds","verification_seconds",*STAGES)}
    med["summed_lane_wall_seconds"] = statistics.median([sum(values) for values in zip(*(result[k] for k in STAGES),strict=True)])
    med["summed_lane_wall_over_total_wall"] = med["summed_lane_wall_seconds"]/med["seconds"] if med["seconds"] else None
    return med


def worker(config, output, deadline):
    import gwrl_cpp
    started=time.perf_counter();pinned=provenance();prepared=templates(config,deadline)
    report={"schema":SCHEMA,"status":"running","config":asdict(config),"provenance":pinned,"cases":[],"scope":__doc__,
        "profile_semantics":"guard/resolve/output counters are SUMMED LANE WALL, including waits/preemption; not CPU time or a cause diagnosis",
        "pool_lifetime":"One pool created/called/released before constructing the next; serial first, then increasing workers",
        "gpu_runtime_used":False,"mps_allocator_reserved_bytes":0,"declared_execution_order":[name for name,_ in executions(config)]}
    def guard():require(time.monotonic()<deadline,"Shared native-sweep deadline exhausted")
    def save():report["worker_elapsed_seconds"]=time.perf_counter()-started;atomic_json(output,report)
    save()
    for family in config.families:
        guard();setup=time.perf_counter();envs,evidence=lanes(prepared[family],config.batch_size,config.seed,deadline)
        context=gwrl_cpp.device_state_context(envs[0]);source_checkpoints=[e.serialize() for e in envs]
        keys=[e.planning_key() for e in envs]  # complete warmed keys, outside timers
        source=canonical_native(gwrl_cpp.capture_device_states(context,envs))
        reference_envs=[]
        for env in envs:
            guard();candidate=env.clone();candidate.resolve_chance();reference_envs.append(candidate)
        expected_keys=[e.planning_key() for e in reference_envs]
        reference=canonical_native(gwrl_cpp.capture_device_states(context,reference_envs))
        case={"family":family,"lanes":config.batch_size,"fixtures":evidence,"input_native_checkpoint_sha256":[hashlib.sha256(s.encode()).hexdigest() for s in source_checkpoints],
            "source_record_sha256":source[3],"expected_output_record_sha256":reference[3],"reference_engine_keys":expected_keys,
            "setup_and_reference_seconds":time.perf_counter()-setup,"executions":[]}
        report["cases"].append(case);save()
        del reference_envs,candidate
        for label,count in executions(config):
            guard();result,lifetime=invoke_profile(context,envs,keys,config.trials,count)
            require(valid_profile(result,config,count),"Native profile metadata/durations incomplete")
            checked=time.perf_counter();require_exact(result["original"],source);require_exact(result["output"],reference)
            require(result["output_engine_keys"]==expected_keys,"Native profile output Engine key differs")
            require([e.serialize() for e in envs]==source_checkpoints,"Native sweep changed original State/history/RNG")
            verification=time.perf_counter()-checked
            row={k:v for k,v in result.items() if k not in {"original","output"}}
            row.update(label=label,**lifetime,external_complete_verification_seconds=verification,
                all_native_state_history_rng_keys_exact=True,source_native_checkpoints_unchanged=True,summary=summarize_profile(result))
            case["executions"].append(row);save()
            del result;gc.collect()
        case["source_unchanged"]=True;save()
        del envs,context,source,reference,source_checkpoints,expected_keys
    report["sources_unchanged"]=pinned==provenance();report["status"]="completed" if report["sources_unchanged"] else "changed_inputs";save();return report


def finalize(report, config):
    def finite(value): return type(value) in (int,float) and math.isfinite(value) and value>=0
    names=[name for name,_ in executions(config)];expected={name:count for name,count in executions(config)}
    cases=report.get("cases",[])
    exact=(report.get("schema")==SCHEMA and report.get("status")=="completed" and report.get("sources_unchanged") is True and
        report.get("gpu_runtime_used") is False and report.get("mps_allocator_reserved_bytes")==0 and
        report.get("declared_execution_order")==names and
        json.dumps(report.get("config"),sort_keys=True)==json.dumps(asdict(config),sort_keys=True) and len(cases)==len(config.families) and {c.get("family") for c in cases}==set(config.families))
    for c in cases:
        rows=c.get("executions",[])
        exact=exact and c.get("lanes")==config.batch_size and c.get("source_unchanged") is True and [r.get("label") for r in rows]==names
        for row in rows:
            exact=(exact and row.get("label") in expected and valid_profile(row,config,expected.get(row.get("label"))) and row.get("all_native_state_history_rng_keys_exact") is True and row.get("source_native_checkpoints_unchanged") is True and row.get("output_engine_keys")==c.get("reference_engine_keys") and
                row.get("summary")==summarize_profile(row) and all(finite(row.get(k)) for k in
                    ("pool_creation_wall_seconds","pool_release_wall_seconds","external_complete_verification_seconds")))
    report["native_sweep_exact"]=bool(exact)
    if report.get("status")=="completed" and not exact:report["status"]="incomplete_or_mismatch"
    return report


def supervise(config, output, deadline):
    from tools.supervise_campaign_training import aggregate_rss,memory_metric,monitor_error_details
    started=time.monotonic();peak=0;stopped=None;diagnostic=None
    if started>=deadline:return {"schema":SCHEMA,"status":"wall_limit","cases":[]}
    with tempfile.TemporaryDirectory(prefix="campaign-native-workers-") as temporary:
        directory=Path(temporary);settings=directory/"config.json";progress=directory/"progress.json";atomic_json(settings,asdict(config))
        environment={**os.environ,"PYTHONHASHSEED":"0","OPENBLAS_NUM_THREADS":"1","OMP_NUM_THREADS":"2","MKL_NUM_THREADS":"2","VECLIB_MAXIMUM_THREADS":"2"}
        with (directory/"stderr").open("w") as stderr,(directory/"stdout").open("w") as stdout:
            process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),"--_worker",str(settings),"--_deadline",str(deadline),"--output",str(progress)],cwd=ROOT,env=environment,stdout=stdout,stderr=stderr,start_new_session=True)
            try:
                while process.poll() is None:
                    if time.monotonic()>=deadline:stopped="wall_limit";break
                    try:charged=aggregate_rss(os.getpid());peak=max(peak,charged)
                    except (OSError,ValueError,subprocess.SubprocessError) as error:
                        if process.poll() is not None:break
                        stopped="memory_monitor_failure";diagnostic=monitor_error_details(error,"native_worker_sweep",root_pid=os.getpid());break
                    if charged>=config.memory_bytes-MARGIN:stopped="memory_limit";break
                    time.sleep(.1)
            finally:
                if process.poll() is None:
                    try:os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                process.wait(timeout=5)
        report=json.loads(progress.read_text()) if progress.exists() else {"schema":SCHEMA,"cases":[]}
        if stopped:report["status"]=stopped
        elif process.returncode!=0 or report.get("status")!="completed":report.update(status="worker_error",error=(directory/"stderr").read_text()[-6000:])
        report["guard"]={"elapsed_seconds":time.monotonic()-started,"shared_deadline_monotonic":deadline,"sampled_peak_charged_bytes":peak,
            "memory_bytes":config.memory_bytes,"margin_bytes":MARGIN,"mps_allocator_reserved_bytes":0,"cpu_budget":config.cpu_budget,
            "metric":memory_metric()+" for coordinator+descendants; no GPU reserve","diagnostic":diagnostic}
        atomic_json(output,report);return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--seconds",type=float,default=240);parser.add_argument("--_worker",type=Path,help=argparse.SUPPRESS);parser.add_argument("--_deadline",type=float,help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    if args._worker:
        data=json.loads(args._worker.read_text())
        for key in ("worker_counts","families"):data[key]=tuple(data[key])
        worker(NativeWorkerConfig(**data),args.output,args._deadline);return 0
    config=NativeWorkerConfig(seconds=args.seconds);require(not args.output.exists(),"Choose a fresh evidence path")
    result=supervise(config,args.output,time.monotonic()+config.seconds);result=finalize(result,config);atomic_json(args.output,result)
    return 0 if result["native_sweep_exact"] else 2


if __name__=="__main__":raise SystemExit(main())
