#!/usr/bin/env python3
"""Prove a legacy campaign checkpoint is compatible before operational migration.

This trusted-local tool never executes a game action or draws game dice. Past
public states are rehydrated with synthetic RNG/history solely to regenerate
menus; only original serialized active games are eligible for continuation.
The large checkpoint load must run under the caller's process-tree memory guard.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "campaign-exact-continuation-proof-v1"
FEATURE_BINDINGS = {"SCHEMA", "NODE_TYPES", "NUMERIC_DIM", "RELATIONS", "PARENT_TO_CHILD",
                    "CHILD_TO_PARENT", "IDENTITY_REFERENCE", "REFERENCE_BACK", "ADJACENT",
                    "EXTERNAL_REFERENCE", "ENTITY_COLLECTIONS", "LEXEMES"}
FEATURE_FUNCTIONS = ("canonical", "lexical_ids", "compile_graph_python", "_string_descriptor",
                     "_cached_numeric_features", "_numeric_features", "make_input", "action_factors")
PERFORMANCE_SOURCE_CHANGES = {
    "include/game/campaign.hpp", "include/game/campaign_env.hpp", "src/air.cpp",
    "src/campaign_env.cpp", "src/campaign_runtime.cpp", "src/campaign_state.cpp",
    "src/python_bindings.cpp", "src/numeric_graph.cpp", "include/game/numeric_graph.hpp",
    "studies/campaign/features.py", "studies/campaign/neural.py", "studies/campaign/learning.py",
    "studies/campaign/run.py", "studies/campaign/evaluation.py", "studies/campaign/model_export.py",
    "studies/campaign/numeric_storage.py", "studies/campaign/scaling_benchmark.py",
    "studies/shared/campaign_adapter.py",
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def source_fingerprint(value):
    # Matches existing learner env_context, which uses JSON's default ASCII mode.
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def digest_file(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".continuation-proof-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as handle:
            handle.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ast_functions(path, names):
    tree = ast.parse(Path(path).read_text())
    found = {item.name: ast.dump(item, include_attributes=False) for item in tree.body
             if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name in names}
    require(set(found) == set(names), f"Missing semantic feature definitions in {path}")
    return found


def ast_feature_bindings(path):
    result, names = [], set()
    for item in ast.parse(Path(path).read_text()).body:
        if not isinstance(item, ast.Assign):
            continue
        bound = {node.id for target in item.targets for node in ast.walk(target) if isinstance(node, ast.Name)}
        if bound & FEATURE_BINDINGS:
            names.update(bound & FEATURE_BINDINGS)
            result.append(ast.dump(item, include_attributes=False))
    require(names == FEATURE_BINDINGS, f"Missing semantic feature constants in {path}")
    return result


def audit_sources(runner, legacy_runtime, current_hashes):
    legacy_runtime = Path(legacy_runtime).resolve()
    old = runner["runtime_source_sha256"]
    require(isinstance(old, dict) and old, "Legacy checkpoint has no source pin")
    for name, expected in old.items():
        path = (legacy_runtime / name).resolve()
        require(path.is_relative_to(legacy_runtime) and path.is_file() and digest_file(path) == expected,
                f"Legacy runtime differs from checkpoint source: {name}")
    legacy_functions = ast_functions(legacy_runtime / "studies/campaign/features.py", FEATURE_FUNCTIONS)
    current_functions = ast_functions(ROOT / "studies/campaign/features.py", FEATURE_FUNCTIONS)
    require(legacy_functions == current_functions, "Raw neural feature semantics changed")
    require(ast_feature_bindings(legacy_runtime / "studies/campaign/features.py") ==
            ast_feature_bindings(ROOT / "studies/campaign/features.py"), "Neural feature constants changed")
    for name in ("studies/shared/multiplayer_mcts.py", "src/neural_graph.cpp",
                 "studies/campaign/baselines.py", "studies/campaign/curriculum.py"):
        require(old.get(name) == current_hashes.get(name), f"Required unchanged semantics changed: {name}")
    changed = sorted(name for name in set(old) | set(current_hashes) if old.get(name) != current_hashes.get(name))
    unexpected = set(changed) - PERFORMANCE_SOURCE_CHANGES
    require(not unexpected, f"Unreviewed continuation source changes: {sorted(unexpected)}")
    return {"legacy_files_verified": len(old), "feature_function_ast_identical": list(FEATURE_FUNCTIONS),
            "feature_constant_ast_identical": sorted(FEATURE_BINDINGS),
            "unchanged_search_and_raw_native_compiler": True,
            "changed_reviewed_source_paths": changed,
            "current_runtime_source_sha256": current_hashes,
            "scope": "Explicit reviewed performance/serialization/evidence changes; every saved row and active game is separately verified."}


def sample_groups(learner):
    for name in ("replay", "pending", "batch_records"):
        rows = learner.get(name)
        require(isinstance(rows, list), f"Invalid learner {name}")
        yield name, rows
    parallel = learner.get("parallel_pending")
    require(isinstance(parallel, list), "Invalid parallel pending rows")
    for index, rows in enumerate(parallel):
        require(isinstance(rows, list), "Invalid parallel pending group")
        yield f"parallel_pending[{index}]", rows


def core_digest(value):
    """Type- and bit-exact digest for non-sample learner bookkeeping/tensors."""
    import numpy as np
    import torch
    result = hashlib.sha256()
    def block(tag, data):
        result.update(tag + struct.pack("<Q", len(data)) + data)
    def visit(item):
        if isinstance(item, torch.Tensor):
            tensor = item.detach().cpu().contiguous()
            block(b"T", str(tensor.dtype).encode()); visit(tuple(tensor.shape))
            block(b"B", tensor.reshape(-1).view(torch.uint8).numpy().tobytes())
        elif isinstance(item, np.ndarray):
            block(b"A", item.dtype.str.encode()); visit(tuple(item.shape)); block(b"B", item.tobytes())
        elif isinstance(item, dict):
            result.update(b"D" + struct.pack("<Q", len(item)))
            for key in sorted(item, key=lambda key: (type(key).__name__, repr(key))):
                visit(key); visit(item[key])
        elif isinstance(item, (tuple, list)):
            result.update((b"U" if isinstance(item, tuple) else b"L") + struct.pack("<Q", len(item)))
            for child in item: visit(child)
        elif item is None: result.update(b"N")
        elif isinstance(item, bool): result.update(b"Y" if item else b"Z")
        elif isinstance(item, int): block(b"I", str(item).encode())
        elif isinstance(item, float): result.update(b"F" + struct.pack("<d", item))
        elif isinstance(item, str): block(b"S", item.encode())
        else: raise TypeError(f"Unsupported continuation bookkeeping: {type(item).__name__}")
    visit(value)
    return result.hexdigest()


def active_snapshots(learner):
    result = []
    if learner.get("env") is not None:
        result.append({"name": "primary", "state": learner["env"], "context": learner["env_context"]})
    for index, item in enumerate(learner.get("parallel_envs", [])):
        result.append({"name": f"parallel[{index}]", **item})
    return result


def environment_record(env):
    from studies.campaign.features import make_input
    actions = env.legal_actions() if env.decision_kind() not in {"chance", "terminal"} else []
    return {"serialized": env.serialize(), "planning_key": env.planning_key(),
            "owner": env.current_decision_player(), "kind": env.decision_kind(),
            "context_sha256": source_fingerprint(env.context()), "input": make_input(env, actions)}


def legacy_worker(runtime, request_path, output_path):
    sys.path.insert(0, str(Path(runtime).resolve()))
    import gwrl_cpp
    from studies.campaign.curriculum import make_env
    require(Path(gwrl_cpp.__file__).resolve().is_relative_to(Path(runtime).resolve()),
            "Legacy witness imported the wrong native engine")
    request = json.loads(Path(request_path).read_text())
    template = make_env(request["seed"], calendar_rounds=request["calendar_rounds"])
    rows = []
    for item in request["snapshots"]:
        env = template.clone(); env.restore(item["state"])
        actual = environment_record(env)
        require(actual["serialized"] == item["state"], "Legacy active snapshot does not round-trip exactly")
        rows.append({"name": item["name"], "record": actual})
    write_json(output_path, {"schema": SCHEMA, "records": rows,
        "native_sha256": digest_file(gwrl_cpp.__file__)})


def rehydrate_public_state(template, observation, context_by_order, *, base_engine=None):
    """Synthetic RNG/history are used ONLY to inspect an old row's legal menu."""
    from studies.shared.campaign_adapter import CampaignAdapter, SCHEMA as SCHEDULER_SCHEMA
    from studies.shared.multiplayer_mcts import PLAYERS
    state = observation["state"]
    require("history" not in state and "definition_fingerprint" not in state,
            "Past neural input unexpectedly contains execution history/fingerprint")
    scheduler = observation["interrupt_scheduler"]
    require(scheduler.get("schema") == SCHEDULER_SCHEMA, "Invalid saved scheduler schema")
    order, passed = tuple(scheduler["order"]), scheduler["passed"]
    require(len(order) == 3 and set(order) == set(PLAYERS), "Invalid saved scheduler order")
    require(len(set(passed)) == len(passed) and set(passed).issubset(PLAYERS), "Invalid saved scheduler passes")
    base_engine = json.loads(template.raw.serialize()) if base_engine is None else base_engine
    encoded = {**base_engine, "state": {**state,
        "definition_fingerprint": base_engine["state"]["definition_fingerprint"], "history": []}}
    raw = template.raw.clone(); raw.restore(canonical(encoded))
    env = CampaignAdapter(raw, interrupt_order=order)
    # Scheduler data was explicitly validated above. Cache only its immutable
    # context; never cache/replace any pending choices or board fields.
    env._passed = set(passed)
    if order not in context_by_order:
        context_by_order[order] = env.neural_context()
    env._neural_context, env._context_order = context_by_order[order], order
    return env


def verify_payload(payload, legacy_runtime, progress=None, row_limit=None):
    from studies.campaign.curriculum import compatibility, make_env, task_manifest
    from studies.campaign.features import SCHEMA as INPUT_SCHEMA, make_input
    from studies.campaign.run import RUN_SCHEMA, RunConfig, source_hashes
    from studies.shared.multiplayer_mcts import PLAYERS
    require(isinstance(payload, dict) and set(payload) == {"schema", "runner", "learner"}
            and payload["schema"] == RUN_SCHEMA, "Unsupported legacy foreground checkpoint")
    runner, learner = payload["runner"], payload["learner"]
    audit = audit_sources(runner, legacy_runtime, source_hashes())
    config = RunConfig(**runner["config"])
    require(config.calendar_rounds == 3 and config.complete_episodes, "Continuation requires genuine three-round self-play")
    template = make_env(config.seed, calendar_rounds=3)
    require(runner["task"] == task_manifest(template), "Scenario/task changed")
    require(learner["metadata"]["compatibility"] == compatibility(template), "Learner rules/scenario changed")
    snapshots = active_snapshots(learner)
    with tempfile.TemporaryDirectory(prefix="campaign-active-witness-") as temporary:
        request, output = Path(temporary) / "request.json", Path(temporary) / "witness.json"
        write_json(request, {"seed": config.seed, "calendar_rounds": 3, "snapshots": snapshots})
        child = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--legacy-worker", str(request),
                                "--legacy-runtime", str(legacy_runtime), "--legacy-output", str(output)],
                               capture_output=True, text=True, timeout=600)
        require(child.returncode == 0, f"Legacy active-state witness failed: {child.stderr[-3000:]}")
        witness = json.loads(output.read_text())
    active = []
    for item, old in zip(snapshots, witness["records"], strict=True):
        env = template.clone(); env.restore(item["state"])
        actual = environment_record(env)
        require(canonical(actual) == canonical(old["record"]), f"Active environment changed: {item['name']}")
        require(actual["serialized"] == item["state"] and actual["context_sha256"] == item["context"],
                f"Original active state/RNG/history changed: {item['name']}")
        active.append({"name": item["name"], "serialized_sha256": hashlib.sha256(item["state"].encode()).hexdigest(),
                       "planning_key": actual["planning_key"], "observation_and_menu_sha256": source_fingerprint(actual["input"])})
    history_keys = {event["before"] for event in learner["action_history"] if event.get("owner") in PLAYERS}
    contexts, context_by_order, generated_contexts, counts = {}, {}, {}, Counter()
    base_engine = json.loads(template.raw.serialize())
    old_inputs, current_inputs, sample_digest = hashlib.sha256(), hashlib.sha256(), hashlib.sha256()
    ordered_menus = True
    for group, rows in sample_groups(learner):
        counts[group] += 0
        for index, sample in enumerate(rows):
            if row_limit is not None and sum(counts.values()) >= row_limit:
                return {"schema": SCHEMA, "status": "partial", "audit": audit, "active_environments": active,
                        "rows_verified": dict(counts), "scope": "Partial diagnostic proof; migration forbidden"}
            item = sample["input"]
            require(item.get("schema") == INPUT_SCHEMA and set(item) == {"schema", "observation", "context", "actions"},
                    f"Unsupported past policy input at {group}[{index}]")
            context = item["context"]
            if id(context) not in contexts:
                value = source_fingerprint(context)
                require(value == learner["env_context"], f"Past source context differs at {group}[{index}]")
                contexts[id(context)] = value
            observation = item["observation"]
            env = rehydrate_public_state(template, observation, context_by_order, base_engine=base_engine)
            order = tuple(observation["interrupt_scheduler"]["order"])
            if order not in generated_contexts:
                generated_contexts[order] = source_fingerprint(context_by_order[order])
            require(generated_contexts[order] == contexts[id(context)], "Rehydrated context differs")
            require(env.current_decision_player() == sample["owner"] == observation["current_decision_player"],
                    f"Decision ownership changed at {group}[{index}]")
            actions = env.legal_actions()
            by_id = {action.id: action for action in actions}
            saved = item["actions"]
            saved_ids = [action["id"] for action in saved]
            require(len(saved_ids) == len(set(saved_ids)) == len(by_id) and set(saved_ids) == set(by_id),
                    f"Complete legal menu changed at {group}[{index}]: saved={len(saved_ids)}, current={len(by_id)}, "
                    f"missing={sorted(set(saved_ids) - set(by_id))[:8]}, extra={sorted(set(by_id) - set(saved_ids))[:8]}")
            ordered_menus &= saved_ids == [action.id for action in actions]
            regenerated = make_input(env, [by_id[identity] for identity in saved_ids])
            first = canonical({key: value for key, value in item.items() if key != "context"})
            second = canonical({key: value for key, value in regenerated.items() if key != "context"})
            require(first == second, f"Full public state/interrupt/menu/action features changed at {group}[{index}]")
            require(env.planning_key() in history_keys, f"Past state key absent from original real action history at {group}[{index}]")
            old_inputs.update(first.encode()); current_inputs.update(second.encode())
            sample_digest.update(canonical({key: value for key, value in sample.items() if key != "input"}).encode())
            counts[group] += 1
            if progress and sum(counts.values()) % 100 == 0:
                progress({"rows_verified": dict(counts), "last_group": group, "last_index": index})
    excluded = {"replay", "pending", "batch_records", "parallel_pending"}
    return {"schema": SCHEMA, "status": "verified", "audit": audit, "active_environments": active,
            "original_generation": learner.get("generation"), "original_counters": learner.get("counters"),
            "original_parallel_pending_rows": [len(rows) for rows in learner["parallel_pending"]],
            "rows_verified": dict(counts), "saved_input_sha256": old_inputs.hexdigest(),
            "regenerated_input_sha256": current_inputs.hexdigest(), "sample_labels_policy_versions_sha256": sample_digest.hexdigest(),
            "non_sample_learner_bitwise_sha256": core_digest({k: v for k, v in learner.items() if k not in excluded}),
            "all_saved_action_orders_equal_native_order": ordered_menus,
            "stored_action_order_retained": True, "legacy_witness_native_sha256": witness["native_sha256"],
            "no_actions_or_dice_executed": True,
            "synthetic_past_state_scope": "Menu/observation proof only; original active serialized games alone continue."}


def migrated_payload(payload, proof, current_hashes, *, additional_games=60):
    """Change operational runner limits only, retaining the original learner."""
    from dataclasses import asdict
    from studies.campaign.run import RunConfig
    require(proof.get("status") == "verified" and proof["saved_input_sha256"] == proof["regenerated_input_sha256"],
            "Exhaustive compatibility proof required before migration")
    require(proof["audit"]["current_runtime_source_sha256"] == current_hashes, "Sources changed after verification")
    require(type(additional_games) is int and additional_games > 0 and additional_games % 4 == 0,
            "Continuation allocation must be a positive whole four-game batch count")
    cfg = asdict(RunConfig(**payload["runner"]["config"]))
    completed, updates = payload["learner"]["counters"]["episodes"], payload["learner"]["counters"]["updates"]
    cfg.update(batches=updates + additional_games // 4, max_episodes=completed + additional_games,
               checkpoint_every_waves=None, checkpoint_interval_seconds=1800.)
    runner = {**payload["runner"], "config": cfg, "runtime_source_sha256": dict(current_hashes)}
    return {**payload, "runner": runner}


def validate_output_paths(checkpoint, legacy_runtime, report, migrate_to=None):
    original, legacy_root = Path(checkpoint).resolve(), Path(legacy_runtime).resolve().parent
    outputs = [Path(report).resolve(), *([Path(migrate_to).resolve()] if migrate_to else [])]
    require(len(set(outputs)) == len(outputs), "Proof report and migrated checkpoint require distinct paths")
    for output in outputs:
        require(output != original and not output.is_relative_to(legacy_root),
                "Proof outputs must not replace any original experiment file")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--legacy-runtime", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--expected-checkpoint-sha256")
    parser.add_argument("--migrate-to", type=Path)
    parser.add_argument("--additional-games", type=int, default=60)
    parser.add_argument("--row-limit", type=int)
    parser.add_argument("--legacy-worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--legacy-output", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.legacy_worker:
        legacy_worker(args.legacy_runtime, args.legacy_worker, args.legacy_output)
        return 0
    if args.checkpoint is None or args.report is None:
        parser.error("--checkpoint and --report are required")
    validate_output_paths(args.checkpoint, args.legacy_runtime, args.report, args.migrate_to)
    if args.migrate_to and args.migrate_to.exists():
        parser.error("Migration destination already exists; original files are never overwritten")
    sys.path.insert(0, str(ROOT))
    import torch
    from studies.campaign.run import source_hashes
    torch.set_num_threads(1)
    source_digest = digest_file(args.checkpoint)
    if args.expected_checkpoint_sha256 is not None:
        require(source_digest == args.expected_checkpoint_sha256, "Original checkpoint SHA-256 differs from authorized source")
    verifier_digest = digest_file(__file__)
    report = {"schema": SCHEMA, "status": "loading", "verifier_sha256": verifier_digest,
              "legacy_runtime": str(args.legacy_runtime.resolve()),
              "source_checkpoint": str(args.checkpoint.resolve()),
              "source_checkpoint_sha256": source_digest, "started_epoch": time.time()}
    write_json(args.report, report)
    payload = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    def progress(value):
        report.update(status="verifying", **value); write_json(args.report, report)
    try:
        proof = verify_payload(payload, args.legacy_runtime, progress, args.row_limit)
        require(source_hashes() == proof["audit"]["current_runtime_source_sha256"], "Sources changed during verification")
        require(digest_file(__file__) == verifier_digest, "Verifier changed during verification")
        require(digest_file(args.checkpoint) == source_digest, "Original checkpoint bytes changed during proof")
        report.update(proof, source_checkpoint_unchanged=True, completed_epoch=time.time())
        if args.migrate_to:
            migrated = migrated_payload(payload, proof, source_hashes(), additional_games=args.additional_games)
            require(migrated["learner"] is payload["learner"], "Learner replacement is forbidden")
            args.migrate_to.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(prefix=".verified-continuation-", dir=args.migrate_to.parent)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    torch.save(migrated, handle, pickle_protocol=5); handle.flush(); os.fsync(handle.fileno())
                os.link(temporary, args.migrate_to)  # fails closed if a destination appeared
                directory = os.open(args.migrate_to.parent, os.O_RDONLY)
                try: os.fsync(directory)
                finally: os.close(directory)
            finally:
                if os.path.exists(temporary): os.unlink(temporary)
            require(digest_file(args.checkpoint) == source_digest, "Original checkpoint bytes changed during publication")
            report["migration"] = {"checkpoint": str(args.migrate_to.resolve()), "sha256": digest_file(args.migrate_to),
                "runner_config": migrated["runner"]["config"], "learner_object_unchanged": True,
                "bootstrap_required": "Restore/validate unchanged learner, create gen15 export/manifest and link initial.pt before pipeline launch."}
        write_json(args.report, report)
        return 0 if report["status"] == "verified" else 2
    except Exception as error:
        report.update(status="failed", error=f"{type(error).__name__}: {error}", completed_epoch=time.time())
        write_json(args.report, report)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
