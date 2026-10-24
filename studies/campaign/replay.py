"""Export recorded real decisions as a browser replay, without search or learning.

The exporter replays only the recorded choices and actual dice from the original
seed. It rejects incompatible rules, illegal choices and broken state chains.
Model weights are neither loaded nor evaluated for benchmark/JSONL exports.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

from .curriculum import ROOT, make_env, task_manifest

SCHEMA = "campaign-replay-v1"
MAP_FIELDS = frozenset({"units", "territories", "nations", "facilities", "construction", "repairs", "rails"})


def digest(value: Any) -> str:
    encoded = value if isinstance(value, str) else json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sources(expected: dict[str, str], allow_source_drift: bool) -> dict:
    differences = []
    for filename, recorded in expected.items():
        path = (ROOT / filename).resolve()
        _require(path.is_relative_to(ROOT), "Source provenance contains a path outside the repository")
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if actual != recorded:
            authoritative = (filename.startswith(("include/", "src/")) or filename in {
                "studies/shared/campaign_adapter.py", "studies/campaign/curriculum.py"})
            differences.append({"path": filename, "recorded": recorded, "current": actual,
                                "authoritative_replay_source": authoritative})
    _require(allow_source_drift or not any(row["authoritative_replay_source"] for row in differences),
             "Authoritative replay sources changed; use --allow-source-drift to verify every transition against current rules")
    return {"recorded_source_sha256": expected, "source_differences": differences,
            "source_drift_allowed": allow_source_drift,
            "note": "Source agreement is separate from rule/context compatibility and per-transition replay verification."}


def snapshot(env) -> dict:
    """Detached full observable state, plus entitled actor and actual wealth."""
    observation = env.observation()
    result = copy.deepcopy(observation["state"])
    order = env.neural_context()["rules"].get("campaign", {}).get("national_turn_order")
    if order is None:
        order = ["ccp", "mongolia", "japan", "kmt"]
    index = result["clock"]["nation_index"]
    result.update(decision_player=env.current_decision_player(), decision_kind=env.decision_kind(),
                  current_nation=order[index], wealth=env.wealth(),
                  interrupt_scheduler=copy.deepcopy(observation["interrupt_scheduler"]))
    return result


def state_changes(before: dict, after: dict) -> dict:
    changes = {}
    for field in sorted(before.keys() | after.keys()):
        old, new = before.get(field), after.get(field)
        if old == new:
            continue
        if field in MAP_FIELDS:
            _require(isinstance(old, dict) and isinstance(new, dict), f"Expected map state for {field}")
            changes[field] = {"upsert": {key: value for key, value in new.items() if old.get(key) != value},
                              "remove": sorted(old.keys() - new.keys())}
        else:
            changes[field] = new
    return changes


def apply_changes(state: dict, changes: dict) -> dict:
    """Pure reducer shared by export validation and seek tests."""
    result = copy.deepcopy(state)
    for field, value in changes.items():
        if field in MAP_FIELDS:
            for key in value["remove"]:
                _require(key in result[field], f"Replay removes an absent {field} entry")
                del result[field][key]
            result[field].update(copy.deepcopy(value["upsert"]))
        else:
            result[field] = copy.deepcopy(value)
    return result


def frame_at(replay: dict, position: int) -> dict:
    _require(type(position) is int and 0 <= position <= len(replay["steps"]), "Replay position is outside the timeline")
    state = copy.deepcopy(replay["initial"])
    for step in replay["steps"][:position]:
        state = apply_changes(state, step["changes"])
    return state


def _raw(action: dict) -> dict:
    return action.get("action") or action


def action_label(action: dict, context: dict, state: dict | None = None) -> str:
    raw = _raw(action)
    kind = raw["kind"]
    parameters = raw.get("parameters", {})
    nodes = context["geography"]["nodes"]
    factions = context["factions"]
    units = state.get("units", {}) if state else {}

    def name(value):
        if isinstance(value, str):
            row = nodes.get(value) or factions.get(value)
            if row:
                return row.get("name", value)
            if value in units:
                return units[value]["type"].replace("_", " ")
            return value
        if isinstance(value, list):
            return " → ".join(str(name(item)) for item in value)
        return str(value)

    if kind == "pass_interrupt":
        return "Pass declaration opportunity"
    if kind == "end_phase" and state:
        return "Finish " + state["clock"]["phase"].replace("_", " ")
    if kind == "movement_route":
        return f"Move {name(parameters.get('unit', 'units'))} · {name(parameters.get('path', []))}"
    if kind == "politics_declare_war":
        return f"{name(raw.get('nation', ''))} declares war on {name(parameters.get('target', ''))}"
    if "take_casualty" in kind:
        return f"Remove casualty · {name(parameters.get('unit', 'unit'))}"
    label = kind.replace("_", " ")
    detail = ", ".join(f"{key.replace('_', ' ')}: {name(value)}" for key, value in parameters.items())
    return f"{label}: {detail}" if detail else label


def _search(env, result: dict, config: dict) -> dict:
    actions = [action.features() for action in env.legal_actions()]
    _require([action["id"] for action in actions] == result["action_ids"], "Recorded search action menu differs")
    if "action_features_sha256" in result:
        _require(digest(actions) == result["action_features_sha256"], "Recorded search action payload hash differs")
    size = len(actions)
    for key in ("visit_counts", "priors", "policy", "action_values"):
        _require(len(result[key]) == size, f"Recorded search {key} length differs from menu")
    _require(all(type(value) is int and value >= 0 for value in result["visit_counts"]), "Invalid search visit counts")
    for key in ("priors", "policy"):
        _require(all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x >= 0
                     for x in result[key]) and abs(sum(result[key]) - 1) < 1e-5, f"Invalid search {key}")
    simulations = config["simulations"]
    _require(type(simulations) is int and simulations > 0 and type(config["max_depth"]) is int
             and config["max_depth"] > 0, "Invalid recorded search budget")
    _require(sum(result["visit_counts"]) == simulations, "Search visits do not match simulation budget")
    # Unvisited actions have no estimated value. Preserve null rather than
    # inventing a zero estimate, which could look like a strategic preference.
    vectors = [result["values"], *(value for value in result["action_values"] if value is not None)]
    _require(all(isinstance(row, list) and len(row) == 3 and
                 all(isinstance(x, (float, int)) and not isinstance(x, bool) and math.isfinite(x) for x in row)
                 for row in vectors), "Invalid three-alliance search value vector")
    context = env.neural_context()
    state = env.neural_observation()["state"]
    return {"actions": [{"id": action["id"], "label": action_label(action, context, state),
                         "kind": _raw(action)["kind"], "parameters": _raw(action).get("parameters", {}),
                         "visits": result["visit_counts"][index], "prior": result["priors"][index],
                         "policy": result["policy"][index], "values": result["action_values"][index]}
                        for index, action in enumerate(actions)],
            "values": result["values"], "simulations": simulations, "depth_cap": config["max_depth"]}


def _new_replay(env, metadata: dict) -> dict:
    metadata = dict(metadata)
    # Episode seeds are 63-bit identifiers. JavaScript numbers would round
    # them before display/export, so the browser contract stores decimal text.
    if "seed" in metadata:
        metadata["seed"] = str(metadata["seed"])
    context = env.context()
    nations = env.observation()["state"]["nations"]
    return {"schema": SCHEMA, "metadata": metadata, "map": context["geography"],
            "factions": {key: {"name": value["name"], "player": nations.get(key, {}).get("player")}
                         for key, value in context["factions"].items()},
            "initial": snapshot(env), "steps": []}


def _transition(replay: dict, env, event: dict, *, search: dict | None = None,
                verification: str = "serialized", sequence: int | None = None) -> None:
    before_hash = digest(env.serialize()) if verification == "serialized" else env.planning_key()
    _require(before_hash == event["before"], "Recorded before-state or execution RNG differs")
    before = snapshot(env)
    raw_before = json.loads(env.raw.serialize())
    owner = env.current_decision_player()
    if "owner" in event:
        _require(event["owner"] == owner, "Recorded decision owner differs")
    chance = event["kind"] == "chance"
    action = None
    if chance:
        _require(env.decision_kind() == "chance", "Recorded chance has no pending dice event")
        env.resolve_chance()
    else:
        recorded_id = event.get("action_id", event.get("action"))
        actions = env.legal_actions()
        matches = [candidate for candidate in actions if candidate.id == recorded_id]
        _require(len(matches) == 1, "Recorded action is not uniquely legal in this decision")
        action = matches[0].features()
        if "action_features" in event:
            _require(action == event["action_features"], "Recorded selected action payload differs")
        if "action_kind" in event:
            _require(_raw(action)["kind"] == event["action_kind"] and
                     _raw(action).get("parameters", {}) == event["action_parameters"], "Recorded action fields differ")
        if search is not None:
            _require(recorded_id in {row["id"] for row in search["actions"]}, "Chosen action absent from search menu")
        env.apply_action(matches[0])
    after_hash = digest(env.serialize()) if verification == "serialized" else env.planning_key()
    _require(after_hash == event["after"], "Recorded after-state or execution RNG differs")
    if "terminal" in event:
        _require(event["terminal"] == env.is_terminal(), "Recorded terminal flag differs")
    after = snapshot(env)
    raw_after = json.loads(env.raw.serialize())
    events = raw_after["state"]["history"][len(raw_before["state"]["history"]):]
    if "events" in event:
        _require(event["events"] == events, "Recorded observed outcomes differ")
    changes = state_changes(before, after)
    _require(apply_changes(before, changes) == after, "Replay state reducer lost a field")
    nation = (_raw(action).get("nation") if action else None) or before["current_nation"]
    step = {"index": len(replay["steps"]), "kind": "chance" if chance else "action",
            "actor": owner, "nation": nation, "action": action,
            "summary": "Resolve dice" if chance else action_label(action, env.neural_context(), before),
            "clock": before["clock"], "changes": changes, "search": search,
            "verification": {"before": before_hash, "after": after_hash, "kind": verification}}
    if sequence is not None:
        step["source_sequence"] = sequence
    if chance:
        step["chance"] = {"request": before.get("chance"), "events": events}
    replay["steps"].append(step)


def _finish(replay: dict, env, *, verification: str) -> dict:
    state = snapshot(env)
    _require(frame_at(replay, len(replay["steps"])) == state, "Final replay state reconstruction differs")
    return _finish_metadata(replay, env, state, verification=verification)


def _finish_metadata(replay: dict, env, state: dict, *, verification: str) -> dict:
    replay["metadata"].update(terminal=env.is_terminal(), exact_replay_verified=True,
        verification=verification, final_state_sha256=digest(env.serialize()),
        final_frame_sha256=digest(state), transitions=len(replay["steps"]),
        observed_terminal_returns=list(env.returns()) if env.is_terminal() else None)
    return replay


def export_report(report_path: Path, *, root: int = 0, allow_source_drift: bool = False) -> dict:
    """Export a bounded benchmark's recorded actions, including every pass/die."""
    report_path = Path(report_path).resolve()
    report = json.loads(report_path.read_text())
    _require(report.get("schema") == "campaign-scaling-benchmark-v1", "Unsupported benchmark report")
    config = report["config"]
    _require(config["mode"] == "episode", "A fixed-position search is not a self-play game replay")
    _require(type(root) is int and 0 <= root < config["roots"], "Root is outside the recorded episode set")
    trace_path = report_path.with_suffix(".trace.jsonl")
    data = trace_path.read_bytes()
    lines = data.splitlines(keepends=True)
    declared = report.get("verification_trace", {})
    count = declared.get("event_count", len(lines))
    _require(type(count) is int and 0 <= count <= len(lines), "Trace has fewer events than the report declares")
    # A stopped worker can leave complete events after its last persisted report.
    # Export only that report's authenticated complete prefix, never guessed data.
    authenticated = b"".join(lines[:count])
    if "events_sha256" in declared:
        _require(hashlib.sha256(authenticated).hexdigest() == declared["events_sha256"], "Report/trace SHA256 differs")
    events = [json.loads(line) for line in lines[:count]]
    source = _sources(report.get("runtime_source_sha256", {}), allow_source_drift)
    env = make_env(config["seed"] + root, calendar_rounds=config["calendar_rounds"])
    _require(task_manifest(env)["compatibility"] == report["task"]["compatibility"], "Recorded task/rules are incompatible with current engine")
    _require(report["preparation"]["roots"][root]["transitions"] == 0, "Episode trace must begin at the approved initial position")
    _require(digest(env.serialize()) == report["prepared_state_sha256"][root], "Initial state/execution RNG hash differs")
    replay = _new_replay(env, {"title": f"Full campaign · seed {config['seed'] + root}" if config["calendar_rounds"] is None
            else f"{config['calendar_rounds']}-round self-play · seed {config['seed'] + root}",
        "origin": "fixed-policy self-play benchmark", "policy": "Neural-guided stochastic MCTS; fixed network weights",
        "source": str(report_path), "source_report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        "source_trace_sha256": hashlib.sha256(authenticated).hexdigest(), "root": root,
        "seed": config["seed"] + root, "horizon_rounds": report["task"]["calendar_rounds"],
        "training_updates": report["model"]["training_updates"], "task": report["task"],
        "model": report["model"], "provenance": source, "source_status": report["status"],
        "scope": "Actual recorded game only; search alternatives are root statistics, not executed moves or a recorded full search tree."})
    pending_search = None
    for sequence, event in enumerate(events):
        if event["kind"] == "search":
            if root in event["roots"]:
                index = event["roots"].index(root)
                _require(digest(env.serialize()) == event["before"][index], "Search was recorded for a different state/RNG")
                _require(pending_search is None, "Unconsumed search result before a new actual decision")
                pending_search = _search(env, event["results"][index], event["configs"][index])
        elif event.get("root") == root:
            _require(event["kind"] in {"action", "chance"}, "Unknown recorded transition kind")
            if event["kind"] == "chance":
                _require(pending_search is None, "Chance unexpectedly intervenes after a recorded search")
            _transition(replay, env, event, search=pending_search, sequence=sequence)
            pending_search = None
    progress = next((row for row in report.get("roots", report.get("root_progress", [])) if row["index"] == root), None)
    if progress:
        _require(progress["transitions"] == len(replay["steps"]), "Report transition count differs from trace")
        _require(progress["clock"] == snapshot(env)["clock"] and progress["terminal"] == env.is_terminal(), "Final report state differs from replay")
        if env.is_terminal():
            _require(progress["observed_terminal_returns"] == list(env.returns()), "Final report returns differ")
    return _finish(replay, env, verification="every recorded serialized state including execution RNG")


def export_trace(trace_path: Path, *, root: int = 0, episode: int = 0,
                 allow_source_drift: bool = False) -> dict:
    """Export the complete available newline-delimited prefix of one episode."""
    live = LiveReplay(trace_path, root=root, episode=episode, allow_source_drift=allow_source_drift)
    result = live.update()
    _require(result is not None, "Requested episode is not recorded yet")
    return _finish(result, live._env, verification=STREAM_VERIFICATION)


STREAM_VERIFICATION = "initial serialized state/RNG, every decision planning key, seed and any recorded past dice events"


def _stream_initial(trace_path: Path, run: dict, start: dict, context: dict,
                    *, root: int, episode: int, allow_source_drift: bool):
    _require(type(start.get("seed")) is int, "Recorded episode has no initial seed; exact replay is unavailable")
    _require(digest(context) == start["context_sha256"], "Recorded context SHA256 differs")
    env = make_env(start["seed"], calendar_rounds=run["config"]["calendar_rounds"])
    source = _sources(run.get("runtime_source_sha256", {}), allow_source_drift)
    _require(task_manifest(env)["compatibility"] == run["task"]["compatibility"], "Recorded task/rules are incompatible with current engine")
    _require(env.context() == context, "Recorded context differs from current engine")
    _require(digest(env.serialize()) == start["initial_state_sha256"], "Initial state/execution RNG hash differs")
    _require(env.planning_key() == start["initial_planning_key"], "Initial decision identity differs")
    if "initial_observation" in start:
        _require(env.observation() == start["initial_observation"], "Initial observation differs")
    origin = "training self-play" if run["kind"] == "training" else "fixed-policy self-play benchmark"
    replay = _new_replay(env, {"title": f"{'Training' if run['kind'] == 'training' else 'Benchmark'} self-play · seed {start['seed']}",
        "origin": origin, "policy": "Neural-guided stochastic MCTS; weights fixed for this collection batch",
        "source": str(trace_path),
        "root": root, "episode": episode, "episode_id": start["episode_id"], "seed": start["seed"],
        "horizon_rounds": run["task"]["calendar_rounds"], "training_updates": None if run["kind"] == "training" else 0,
        "task": run["task"], "model": run.get("model", {"config": run.get("model_config"),
                  "initial_versions": run.get("initial_model_versions")}), "provenance": source,
        "scope": "Actual recorded collection decisions; no search or learning rerun. Missing run_end denotes an interrupted or active recording."})
    return env, replay


def _stream_transition(replay: dict, env, row: dict) -> None:
    _require(row["root"] == replay["metadata"]["root"] and row["sequence"] == len(replay["steps"]),
             "Recorded transition sequence has a gap or wrong root")
    event = dict(row["event"])
    search = None
    if event["kind"] != "chance":
        menu = row["decision_menu"]
        _require(menu == [action.features() for action in env.legal_actions()], "Recorded decision menu differs")
        index = row["selected_index"]
        _require(type(index) is int and 0 <= index < len(menu), "Recorded selected index is outside the menu")
        _require(menu[index] == row["selected_action"] and menu[index]["id"] == event["action"], "Recorded selected action/index differs")
        event["action_features"] = row["selected_action"]
        result = {**row["search"], "action_ids": [action["id"] for action in menu],
                  "action_features_sha256": digest(menu)}
        search = _search(env, result, {"simulations": result["simulations"], "max_depth": result["max_depth"]})
        search["sampling_policy"] = result.get("sampling_policy")
        search["rollout_version"] = result.get("rollout_version")
    if row.get("observed_events") is not None:
        event["events"] = row["observed_events"]
    _transition(replay, env, event, search=search, verification="planning", sequence=row["sequence"])
    if row.get("terminal_returns") is not None:
        _require(env.is_terminal() and row["terminal_returns"] == list(env.returns()), "Recorded terminal returns differ")


class LiveReplay:
    """Follow a trusted local append-only inspection stream without old replays.

    ``update()`` returns None until the selected episode starts, then a borrowed
    read-only replay dict. The native environment and decoded prefix stay here;
    each poll applies only new complete records. A partial final line waits for
    its newline. Existing bytes are hashed to reject truncation/replacement or
    edits, including edits to a previously observed partial line. Thus polling
    reads old bytes for integrity but never reparses or simulates old records.

    An update stages its environment and new steps, publishing them together
    only after every new complete record passes validation. Failed updates keep
    the last verified replay and byte offset intact. Callers serialize access.
    """

    def __init__(self, trace_path: Path, *, root: int = 0, episode: int = 0,
                 allow_source_drift: bool = False):
        _require(type(root) is int and root >= 0 and type(episode) is int and episode >= 0,
                 "Root and episode must be nonnegative integers")
        self.path = Path(trace_path).resolve()
        self.root, self.episode = root, episode
        self.allow_source_drift = allow_source_drift
        self.offset = 0
        self.revision = 0
        self.status = "waiting_for_file"
        self.replay = None
        self._env = None
        self._identity = None
        self._observed_size = 0
        self._observed_sha256 = hashlib.sha256(b"").hexdigest()
        self._run = None
        self._contexts: dict[str, dict] = {}
        self._episodes: dict[str, tuple[int, int]] = {}
        self._matching_starts = 0
        self._ended = False

    def update(self) -> dict | None:
        if not self.path.exists() and self._identity is None:
            return None
        with self.path.open("rb") as handle:
            info = os.fstat(handle.fileno())
            identity = (info.st_dev, info.st_ino)
            _require(self._identity is None or identity == self._identity, "Live trace file was replaced")
            _require(info.st_size >= self._observed_size, "Live trace file was truncated")
            data = handle.read(info.st_size)
        _require(len(data) == info.st_size, "Live trace changed while reading")
        _require(hashlib.sha256(data[:self._observed_size]).hexdigest() == self._observed_sha256,
                 "Previously observed live trace bytes were edited")
        complete = data.rfind(b"\n", self.offset)
        next_offset = complete + 1 if complete >= self.offset else self.offset
        if next_offset == self.offset:
            # Remember even partial bytes so a writer cannot silently rewrite
            # them between polls. Do not parse them until a newline arrives.
            self._identity = identity
            self._observed_size, self._observed_sha256 = len(data), hashlib.sha256(data).hexdigest()
            if self._run is None:
                self.status = "waiting_for_run"
            return self.replay
        rows = []
        for line in data[self.offset:next_offset].splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError("Malformed complete replay trace record") from error
            _require(isinstance(row, dict) and row.get("schema") == "campaign-self-play-trace-v1",
                     "Unsupported inspection stream schema")
            rows.append(row)
        # Stage only small containers plus a native clone, never a deep copy of
        # the growing browser dataset or a replay of the existing timeline.
        run, contexts = self._run, self._contexts.copy()
        episodes = self._episodes.copy()
        matching, ended = self._matching_starts, self._ended
        env = self._env.clone() if self._env is not None else None
        replay = ({**self.replay, "metadata": self.replay["metadata"].copy(), "steps": self.replay["steps"].copy()}
                  if self.replay is not None else None)
        for row in rows:
            _require(not ended, "Live trace contains records after run_end")
            kind = row["type"]
            if run is None:
                _require(kind == "run_start", "Inspection stream has no run_start record")
            if kind == "run_start":
                _require(run is None, "Inspection stream contains a second run_start")
                _require(row["kind"] in {"training", "frozen_policy_benchmark"}, "Unknown inspection run kind")
                run = row
            elif kind == "context":
                key = row["context_sha256"]
                _require(digest(row["context"]) == key, "Recorded context SHA256 differs")
                _require(key not in contexts or contexts[key] == row["context"], "Recorded context was replaced")
                contexts[key] = row["context"]
            elif kind == "episode_start":
                key = row["episode_id"]
                _require(key not in episodes, "Episode identifier is repeated")
                _require(row["context_sha256"] in contexts, "Recorded episode has no matching static context")
                episodes[key] = (row["root"], 0)
                if row["root"] == self.root:
                    if matching == self.episode:
                        env, replay = _stream_initial(self.path, run, row, contexts[row["context_sha256"]],
                            root=self.root, episode=self.episode, allow_source_drift=self.allow_source_drift)
                    matching += 1
            elif kind == "transition":
                key = row["episode_id"]
                _require(key in episodes, "Transition has no recorded episode start")
                owner, sequence = episodes[key]
                _require(row["root"] == owner and row["sequence"] == sequence,
                         "Recorded transition sequence has a gap or wrong root")
                episodes[key] = (owner, sequence + 1)
                if replay is not None and key == replay["metadata"]["episode_id"]:
                    _stream_transition(replay, env, row)
            elif kind == "run_end":
                ended = True
            else:
                raise ValueError(f"Unknown inspection record type: {kind}")
        if replay is not None:
            _finish_metadata(replay, env, snapshot(env), verification=STREAM_VERIFICATION)
            replay["metadata"].update(source_trace_sha256=hashlib.sha256(data[:next_offset]).hexdigest(),
                source_authenticated_bytes=next_offset, source_observed_bytes=len(data),
                recording_complete=ended and next_offset == len(data), live=not ended,
                live_status="ended" if ended else "active")
        # Commit only after the entire new batch and its resulting state pass.
        self._run, self._contexts, self._episodes = run, contexts, episodes
        self._matching_starts, self._ended = matching, ended
        self._env, self.replay = env, replay
        self.offset, self._identity = next_offset, identity
        self.revision += 1
        self._observed_size, self._observed_sha256 = len(data), hashlib.sha256(data).hexdigest()
        self.status = "ended" if ended else "active" if replay is not None else "waiting_for_episode"
        return replay


def write_replay(output: Path, replay: dict) -> None:
    """Publish a complete JSON export atomically, preserving any existing file."""
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    _require(not output.exists(), "Existing replay output is preserved; choose a new output path")
    descriptor, temporary = tempfile.mkstemp(prefix=".replay-", suffix=".json", dir=output.parent)
    try:
        with os.fdopen(descriptor, "w") as handle:
            json.dump(replay, handle, sort_keys=True, separators=(",", ":"), allow_nan=False)
            handle.write("\n")
        # Atomic no-clobber publish: unlike os.replace, this cannot overwrite a
        # file created by another process after the existence check.
        os.link(temporary, output)
    finally:
        os.unlink(temporary)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--report", type=Path)
    inputs.add_argument("--trace", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=int, default=0)
    parser.add_argument("--episode", type=int, default=0, help="Zero-based episode within a root; inspection streams only")
    parser.add_argument("--allow-source-drift", action="store_true",
                        help="Record changed sources, while still requiring compatible rules and exact transition replay")
    args = parser.parse_args(argv)
    try:
        _require(not args.output.exists(), "Existing replay output is preserved")
        if args.report:
            _require(args.episode == 0, "Benchmark reports contain only one episode per root")
            result = export_report(args.report, root=args.root, allow_source_drift=args.allow_source_drift)
        else:
            result = export_trace(args.trace, root=args.root, episode=args.episode, allow_source_drift=args.allow_source_drift)
        write_replay(args.output, result)
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))
    print(json.dumps({"output": str(args.output.resolve()), "steps": len(result["steps"]),
                      "terminal": result["metadata"]["terminal"], "exact_replay_verified": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
