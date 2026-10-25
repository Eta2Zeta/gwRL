"""Native calls release Python's lock without changing campaign state or dice.

Each probe runs in a bounded child process so a lock-order regression fails the
test instead of hanging the entire suite. These are correctness checks, not
parallel-throughput benchmarks.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import gwrl_cpp


SCENARIO = ROOT / "game_content/scenarios/japan_china_1936"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def root(seed=11):
    return gwrl_cpp.CampaignEnv.curriculum(str(SCENARIO), 3, seed, training_actions=True)


def end_phase(env):
    env.apply_action(next(action for action in env.legal_actions() if action.kind == "end_phase"))


def placement_root():
    env = root()
    for _ in range(4):
        end_phase(env)
    require(env.decision_kind() == "place_units", "Expected the CCP recruitment opportunity")
    return env


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def independent_chance_probe():
    env = placement_root()
    env.apply_action(next(action for action in env.legal_actions() if action.kind == "recruitment_roll"))
    require(env.decision_kind() == "chance", "Expected a pending real recruitment roll")
    before = env.serialize()
    reference_actual = env.clone()

    def advance(seed):
        simulation = env.clone_for_search(seed)
        events = []
        for _ in range(12):
            if simulation.is_terminal():
                break
            key = simulation.planning_key()
            if simulation.decision_kind() == "chance":
                simulation.resolve_chance()
                selected = "chance"
            else:
                actions = simulation.legal_actions()
                require(actions, "A nonterminal decision must have a legal action")
                ends = [action for action in actions if action.kind == "end_phase"]
                action = ends[0] if ends else min(actions, key=lambda item: item.describe())
                selected = action.describe()
                simulation.apply_action(action)
            events.append((key, selected, simulation.planning_key()))
        return simulation.serialize(), events, simulation.returns()

    seeds = [17, 51, 94, 123]
    serial = [advance(seed) for seed in seeds]
    with ThreadPoolExecutor(max_workers=4) as pool:
        threaded = list(pool.map(advance, seeds))
    require(serial == threaded, "Concurrent simulations changed exact states, choices or random streams")
    require(env.serialize() == before, "Simulated dice consumed or mutated the actual root")
    env.resolve_chance()
    reference_actual.resolve_chance()
    require(env.serialize() == reference_actual.serialize(), "Actual dice changed after concurrent search clones")
    return {"independent_workers": 4, "exact_serial_match": True, "actual_rng_preserved": True}


def shared_clone_cache_probe():
    env = root(91)
    initial = env.serialize()
    # Clone before warming observation/planning caches: all four share those
    # immutable-state cache containers until their own successful mutations.
    clones = [env.clone() for _ in range(4)]
    barrier = threading.Barrier(4)

    def read(clone):
        barrier.wait(timeout=5)
        values = []
        for _ in range(4):
            values.append((clone.observation(), clone.planning_key(),
                           [action.describe() for action in clone.legal_actions()], clone.context()))
        require(all(value == values[0] for value in values), "Concurrent cached reads changed a snapshot")
        return values[0]

    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(pool.map(read, clones))
    require(all(value == values[0] for value in values), "Clones disagree on their shared initial state")
    end_phase(clones[0])
    require(clones[0].serialize() != initial, "Independent clone did not advance")
    require(env.serialize() == initial, "A clone mutation changed the original")
    require(all(clone.serialize() == initial for clone in clones[1:]), "Clone mutation invalidated another board")
    require(clones[0].observation() != values[0][0], "Mutated clone retained its old observation")
    return {"cold_shared_cache_reads": True, "independent_mutation": True}


def same_env_snapshot_probe():
    env = root(31)
    first = env.serialize()
    next_state = env.clone()
    end_phase(next_state)
    second = next_state.serialize()
    allowed = {first, second}
    clocks = [json.loads(value)["state"]["clock"] for value in allowed]
    barrier = threading.Barrier(4)

    def writer():
        barrier.wait(timeout=5)
        for index in range(18):
            env.restore(first if index % 2 else second)
        return True

    def reader():
        barrier.wait(timeout=5)
        for _ in range(12):
            require(env.serialize() in allowed, "Serialized state was torn by an overlapping restore")
            require(env.observation()["state"]["clock"] in clocks, "Observation was not a complete valid snapshot")
            require(env.clone().serialize() in allowed, "Clone was torn by an overlapping restore")
        return True

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(writer), *(pool.submit(reader) for _ in range(3))]
        require(all(future.result() for future in futures), "Concurrent same-environment operation failed")
    require(env.serialize() in allowed, "Same-environment operations corrupted the final state")
    return {"same_env_atomic_snapshots": True, "readers": 3, "restores": 18}


def stale_action_and_exception_probe():
    env = placement_root()
    action = next(action for action in env.legal_actions() if action.kind == "recruitment_roll")
    reference = env.clone()
    reference.apply_action(action)
    barrier = threading.Barrier(2)

    def apply():
        barrier.wait(timeout=5)
        try:
            env.apply_action(action)
        except RuntimeError:
            return "stale"
        return "applied"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [future.result() for future in [pool.submit(apply), pool.submit(apply)]]
    require(sorted(results) == ["applied", "stale"], "Overlapping actions bypassed authoritative stale-action validation")
    require(env.serialize() == reference.serialize(), "Atomic action application changed the expected chance state")
    saved = env.serialize()
    bad = json.loads(saved)
    bad["state"]["definition_fingerprint"] = "incompatible-test-definition"
    try:
        env.restore(json.dumps(bad))
    except RuntimeError:
        pass
    else:
        raise AssertionError("Incompatible restore was accepted")
    require(env.serialize() == saved, "Failed native operation left a partial state or locked the environment")
    env.resolve_chance()
    reference.resolve_chance()
    require(env.serialize() == reference.serialize(), "Exceptions changed the RNG or prevented future calls")
    return {"one_action_applied": True, "stale_action_rejected": True, "exception_unlocks": True}


def mcts_probe():
    from studies.campaign.batching import search_many
    from studies.shared.campaign_adapter import CampaignAdapter
    from studies.shared.multiplayer_mcts import MctsConfig, UniformEvaluator, VectorMCTS, action_key

    class BatchedUniform(UniformEvaluator):
        def evaluate_batch(self, requests):
            return [self.evaluate(env, actions) for env, actions in requests]

    env = CampaignAdapter(placement_root())
    envs = [env.clone() for _ in range(4)]
    snapshots = [item.serialize() for item in envs]
    configs = [MctsConfig(simulations=16, max_depth=16, seed=900 + index, record_trace=True)
               for index in range(4)]
    serial = [VectorMCTS(BatchedUniform(), config).search(item, add_root_noise=True)
              for item, config in zip(envs, configs)]
    threaded = search_many(envs, BatchedUniform(), configs=configs, add_root_noise=True)
    fields = ("visit_counts", "policy", "priors", "values", "action_values", "cache_identity", "simulations")
    for expected, actual in zip(serial, threaded):
        require([action_key(a) for a in expected.actions] == [action_key(a) for a in actual.actions],
                "Concurrent MCTS changed the legal action order")
        for field in fields:
            require(getattr(expected, field) == getattr(actual, field), f"Concurrent MCTS changed {field}")
    require(snapshots == [item.serialize() for item in envs], "MCTS changed actual game state or dice")
    return {"roots": 4, "simulations_each": 16, "exact_search_match": True,
            "state_sha256": [sha(snapshot) for snapshot in snapshots]}


def gil_release_probe():
    env = root(17)
    value = json.loads(env.serialize())
    # A sizeable but valid unknown flag map makes ONE native restore long enough
    # for the waiting Python thread to be scheduled. No throughput threshold or
    # comparison between machine-dependent durations is used.
    value["state"]["flags"].update({f"test_concurrency_padding:{index}": 0 for index in range(64_000)})
    checkpoint = json.dumps(value, separators=(",", ":"))
    ready, go, ran = threading.Event(), threading.Event(), threading.Event()

    def heartbeat():
        ready.set()
        go.wait(timeout=10)
        ran.set()

    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    require(ready.wait(timeout=5), "Heartbeat thread did not start")
    interval = sys.getswitchinterval()
    try:
        # Suppress ordinary Python bytecode switching. Between opening the gate
        # and reading ran, the only intentional GIL release is the native call.
        sys.setswitchinterval(100.0)
        go.set()
        env.restore(checkpoint)
        progressed_during_native_call = ran.is_set()
    finally:
        sys.setswitchinterval(interval)
        go.set()
        thread.join(timeout=5)
    require(not thread.is_alive(), "Heartbeat thread failed to exit")
    require(progressed_during_native_call, "Python heartbeat could not run during the native engine call")
    require(env.observation()["state"]["flags"]["test_concurrency_padding:63999"] == 0,
            "Native restore did not preserve the complete state")
    return {"python_progress_during_native_call": True, "padded_flags": 64_000}


PROBES = {"independent_chance": independent_chance_probe, "shared_clone_cache": shared_clone_cache_probe,
          "same_env_snapshot": same_env_snapshot_probe, "stale_action_exception": stale_action_and_exception_probe,
          "mcts": mcts_probe, "gil_release": gil_release_probe}


class CampaignNativeConcurrencyTests(unittest.TestCase):
    def probe(self, name):
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--probe", name],
                                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr[-5000:] + result.stdout[-1000:])
        return json.loads(result.stdout)

    def test_independent_threads_preserve_full_states_and_actual_search_rng(self):
        self.assertTrue(self.probe("independent_chance")["exact_serial_match"])

    def test_shared_cold_clone_caches_remain_consistent_after_independent_mutation(self):
        self.assertTrue(self.probe("shared_clone_cache")["independent_mutation"])

    def test_overlapping_restore_and_reads_of_one_environment_are_atomic(self):
        self.assertTrue(self.probe("same_env_snapshot")["same_env_atomic_snapshots"])

    def test_stale_action_validation_and_exception_unlocking_are_preserved(self):
        self.assertTrue(self.probe("stale_action_exception")["exception_unlocks"])

    def test_real_threaded_mcts_matches_serial_search_and_retains_live_rng(self):
        self.assertTrue(self.probe("mcts")["exact_search_match"])

    def test_python_can_progress_during_a_single_native_engine_operation(self):
        self.assertTrue(self.probe("gil_release")["python_progress_during_native_call"])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--probe":
        print(json.dumps(PROBES[sys.argv[2]]()))
    else:
        unittest.main()
