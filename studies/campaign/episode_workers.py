"""Training episodes played in separate processes, each with its own interpreter lock.

Each task plays one complete game from its environment seed with the batch's
frozen weights. With EpisodeWorkers, search evaluates one position at a time on
CPU, so a game's result depends only on the weights, its seed and the learning
settings, not on which process plays it or what runs beside it. With
SharedEpisodeWorkers, the main process evaluates every game's waiting positions
together on its device. That plays more games per hour, but a position's batch
changes its outputs in the last digits, so a game need not repeat exactly.
"""
from __future__ import annotations

import multiprocessing
import os
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from functools import partial
from typing import Any, Callable, Mapping, Sequence

_WORKER: dict[str, Any] = {}


def _initialize(settings: Mapping[str, Any]) -> None:
    import torch
    # One busy core per game: tensors run on the search thread itself.
    torch.set_num_threads(1)
    if torch.get_num_interop_threads() != 1:
        torch.set_num_interop_threads(1)
    _WORKER.update(settings=dict(settings), version=None, evaluator=None)


def _play_game(settings: Mapping[str, Any], evaluator: Any, task: Mapping[str, Any]) -> dict[str, Any]:
    """One complete game from its seed; a failure costs this game, not its batch."""
    from .curriculum import make_env
    from .learning import LearningConfig, play_episode
    started = time.perf_counter()
    try:
        env = make_env(task["seed"], calendar_rounds=settings["calendar_rounds"])
        result = play_episode(env, evaluator, config=LearningConfig(**settings["learning_config"]),
                              rules_version=settings["rules_version"], numeric=settings["numeric"],
                              token_buckets=settings["model_config"]["token_buckets"],
                              batch_version=task["batch_version"], environment_seed=task["seed"],
                              max_transitions=task["max_transitions"])
    except Exception as error:
        # Its seed and weights reproduce it.
        return {"root": task["root"], "seed": task["seed"], "failure": f"{type(error).__name__}: {error}",
                "seconds": time.perf_counter() - started}
    result.update(root=task["root"], seed=task["seed"], process=os.getpid(),
                  seconds=time.perf_counter() - started)
    return result


def _play(task: Mapping[str, Any]) -> dict[str, Any]:
    from .neural import CampaignModelConfig, CampaignPolicyValueNet, NeuralEvaluator
    settings = _WORKER["settings"]
    if _WORKER["version"] != task["batch_version"]:
        model_config = CampaignModelConfig(**settings["model_config"])
        models = {}
        for player, weights in task["weights"].items():
            model = CampaignPolicyValueNet(model_config)
            model.load_state_dict(weights)
            models[player] = model.eval()
        _WORKER.update(version=task["batch_version"],
                       evaluator=NeuralEvaluator(models, version=task["batch_version"]))
    return _play_game(settings, _WORKER["evaluator"], task)


def _play_shared(settings: Mapping[str, Any], task: Mapping[str, Any], evaluator: Any) -> dict[str, Any]:
    return _play_game(settings, evaluator, task)


def _shared_process(settings: Mapping[str, Any], batch_version: str, *arguments: Any) -> None:
    from .numeric_storage import pack_as_bytes
    from .shared_evaluator import game_process
    pack_as_bytes()
    game_process(partial(_play_shared, settings), settings["model_config"]["token_buckets"], batch_version, *arguments)


class EpisodeWorkers:
    """A fixed pool of spawned processes that play whole training episodes.

    A worker that dies raises BrokenProcessPool rather than leaving its game
    pending. Callers must start the pool from an importable main module.
    """

    def __init__(self, processes: int, *, calendar_rounds: int | None, model_config: Mapping[str, Any],
                 learning_config: Mapping[str, Any], rules_version: str, numeric: bool):
        if type(processes) is not int or processes <= 0:
            raise ValueError("Episode workers must be a positive integer")
        self.processes = processes
        settings = {"calendar_rounds": calendar_rounds, "model_config": dict(model_config),
                    "learning_config": dict(learning_config), "rules_version": rules_version, "numeric": numeric}
        self._executor = ProcessPoolExecutor(processes, mp_context=multiprocessing.get_context("spawn"),
                                             initializer=_initialize, initargs=(settings,))

    def play(self, games: Sequence[tuple[int, int]], *, weights: Mapping[str, Any], batch_version: str,
             max_transitions: int, stop: Callable[[], bool] = lambda: False) -> list[dict[str, Any]] | None:
        """Play (root, seed) games; results return in root order, or None if stopped."""
        futures = [self._executor.submit(_play, {"root": root, "seed": seed, "weights": weights,
                                                 "batch_version": batch_version, "max_transitions": max_transitions})
                   for root, seed in games]
        pending = set(futures)
        while pending:
            if stop():
                self.terminate()
                return None
            done, pending = wait(pending, timeout=0.2, return_when=FIRST_COMPLETED)
            for future in done:
                future.result()  # Surface a failed game or a dead worker immediately.
        return [future.result() for future in futures]

    def terminate(self) -> None:
        """Stop now; running games cannot finish, so their processes are killed."""
        # No public kill before Python 3.14; a finished shutdown leaves None.
        processes = list((getattr(self._executor, "_processes", None) or {}).values())
        self._executor.shutdown(wait=False, cancel_futures=True)
        for process in processes:
            if process.is_alive():
                process.terminate()
        for process in processes:
            process.join(timeout=5)

    def close(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=True)


class SharedEpisodeWorkers:
    """Game processes for one batch at a time, with their positions evaluated here.

    Several games share each process, one per thread, so the evaluator's batches
    fill. Processes last one batch: a batch's context encodings and the record of
    contexts already sent belong to its weights, and a batch is long enough that
    starting them costs little.
    """

    def __init__(self, processes: int, games_per_process: int, *, device: Any, runtime_policy: Any = None,
                 calendar_rounds: int | None, model_config: Mapping[str, Any], learning_config: Mapping[str, Any],
                 rules_version: str, numeric: bool):
        from studies.shared.multiplayer_mcts import PLAYERS
        from .neural import CampaignModelConfig, CampaignPolicyValueNet
        if type(processes) is not int or processes <= 0 or type(games_per_process) is not int or games_per_process <= 0:
            raise ValueError("Shared episode workers need positive process and game counts")
        if not numeric:
            raise ValueError("The shared evaluator needs native numerical inputs")
        self.processes, self.games_per_process = processes, games_per_process
        self.device, self.runtime_policy = device, runtime_policy
        self.settings = {"calendar_rounds": calendar_rounds, "model_config": dict(model_config),
                         "learning_config": dict(learning_config), "rules_version": rules_version, "numeric": numeric}
        config = CampaignModelConfig(**model_config)
        self.models = {player: CampaignPolicyValueNet(config, device=device).eval() for player in PLAYERS}
        self.serving = None

    def play(self, games: Sequence[tuple[int, int]], *, weights: Mapping[str, Any], batch_version: str,
             max_transitions: int, stop: Callable[[], bool] = lambda: False) -> list[dict[str, Any]] | None:
        """Play (root, seed) games; results return in root order, or None if stopped."""
        from .shared_evaluator import play_shared_games
        for player, model in self.models.items():
            model.load_state_dict(weights[player])
        stopped = False

        def keep_playing(_server: Any, _records: Any) -> bool:
            nonlocal stopped
            stopped = stopped or stop()
            return not stopped

        tasks = [{"root": root, "seed": seed, "batch_version": batch_version, "max_transitions": max_transitions}
                 for root, seed in games]
        records, self.serving = play_shared_games(partial(_shared_process, self.settings, batch_version), tasks,
                                                  processes=self.processes, games_per_process=self.games_per_process,
                                                  models=self.models, device=self.device,
                                                  runtime_policy=self.runtime_policy, keep_playing=keep_playing,
                                                  exit_seconds=120.0)
        if stopped:
            return None
        if sorted(record["root"] for record in records) != sorted(root for root, _ in games):
            raise RuntimeError("A game process lost a game's result")
        return sorted(records, key=lambda record: record["root"])

    def report(self) -> dict[str, Any]:
        """The last batch's evaluator traffic."""
        stats = self.serving
        return {"evaluations": stats.requests, "serving_rounds": stats.rounds, "model_forwards": stats.forwards,
                "forward_seconds": stats.forward_seconds, "idle_seconds": stats.idle_seconds}

    def terminate(self) -> None:
        """Nothing outlives a batch."""

    def close(self) -> None:
        """Nothing outlives a batch."""
