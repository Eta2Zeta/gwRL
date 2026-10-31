"""Training episodes played in separate processes, each with its own interpreter lock.

Each task plays one complete game from its environment seed with the batch's
frozen weights on CPU. Search evaluates one position at a time, so a game's
result depends only on the weights, its seed and the learning settings, not on
which process plays it or what runs beside it.
"""
from __future__ import annotations

import multiprocessing
import os
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from typing import Any, Callable, Mapping, Sequence

_WORKER: dict[str, Any] = {}


def _initialize(settings: Mapping[str, Any]) -> None:
    import torch
    # One busy core per game: tensors run on the search thread itself.
    torch.set_num_threads(1)
    if torch.get_num_interop_threads() != 1:
        torch.set_num_interop_threads(1)
    _WORKER.update(settings=dict(settings), version=None, evaluator=None)


def _play(task: Mapping[str, Any]) -> dict[str, Any]:
    from .curriculum import make_env
    from .learning import LearningConfig, play_episode
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
    env = make_env(task["seed"], calendar_rounds=settings["calendar_rounds"])
    started = time.perf_counter()
    try:
        result = play_episode(env, _WORKER["evaluator"], config=LearningConfig(**settings["learning_config"]),
                              rules_version=settings["rules_version"], numeric=settings["numeric"],
                              token_buckets=settings["model_config"]["token_buckets"],
                              batch_version=task["batch_version"], environment_seed=task["seed"],
                              max_transitions=task["max_transitions"])
    except Exception as error:
        # The game is lost and its batch is not; its seed and weights reproduce it.
        return {"root": task["root"], "seed": task["seed"], "failure": f"{type(error).__name__}: {error}",
                "seconds": time.perf_counter() - started}
    result.update(root=task["root"], seed=task["seed"], process=os.getpid(),
                  seconds=time.perf_counter() - started)
    return result


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
