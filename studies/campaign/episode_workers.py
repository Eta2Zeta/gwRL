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
from pathlib import Path
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
                              rules_version=settings["rules_version"], batch_version=task["batch_version"],
                              environment_seed=task["seed"], max_transitions=task["max_transitions"])
    except Exception as error:
        # Its seed and weights reproduce it in EpisodeWorkers. A shared evaluator
        # need not repeat a game, so an error that carries a position keeps it:
        # a dead end's (NoLegalActionError) or a failed move's (FailedMoveError),
        # which may be one that search imagined.
        failure = {"root": task["root"], "seed": task["seed"], "failure": f"{type(error).__name__}: {error}",
                   "seconds": time.perf_counter() - started}
        state = getattr(error, "state", None)
        if state is not None:
            failure.update(_keep_failed_position(settings.get("failed_positions"), task, state))
        return failure
    result.update(root=task["root"], seed=task["seed"], process=os.getpid(),
                  seconds=time.perf_counter() - started)
    return result


def failed_position_name(game: Mapping[str, Any]) -> str:
    """The file a failed game's position is kept in, in its run's failed-positions/."""
    return f"game-{game['root']}-seed-{game['seed']}.json"


def _keep_failed_position(folder: str | None, task: Mapping[str, Any], state: str) -> dict[str, Any]:
    """Write a failed game's position into `folder` now, or hand it to the caller.

    A game process can abort while it frees a failed game, before the training
    process hears of the failure, as one did on 20 November 2026; a position
    written here survives that. Without a folder, or if writing fails, the
    position goes back with the failure for the training process to save.
    """
    if folder is None:
        return {"state": state}
    path = Path(folder) / failed_position_name(task)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # UTF-8 with bare newlines: Windows would otherwise write its code page.
        temporary.write_text(state, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    except OSError:
        return {"state": state}
    return {"position": f"{path.parent.name}/{path.name}"}


def _play(task: Mapping[str, Any]) -> dict[str, Any]:
    from .neural import CampaignModelConfig, NeuralEvaluator, alliance_networks, load_alliance_weights
    settings = _WORKER["settings"]
    if _WORKER["version"] != task["batch_version"]:
        models = alliance_networks(CampaignModelConfig(**settings["model_config"]),
                                   settings["learning_config"].get("networks", "one"))
        load_alliance_weights(models, task["weights"])
        _WORKER.update(version=task["batch_version"],
                       evaluator=NeuralEvaluator(models, version=task["batch_version"]))
    return _play_game(settings, _WORKER["evaluator"], task)


def _play_shared(settings: Mapping[str, Any], task: Mapping[str, Any], evaluator: Any) -> dict[str, Any]:
    return _play_game(settings, evaluator, task)


def _lost_game(task: Mapping[str, Any], reason: str, seconds: float) -> dict[str, Any]:
    """The record of a game whose process died before reporting it: a failed game,
    as _play_game reports one. Its position died with the process."""
    return {"root": task["root"], "seed": task["seed"], "failure": reason, "seconds": seconds}


def _shared_process(settings: Mapping[str, Any], batch_version: str, *arguments: Any) -> None:
    from .shared_evaluator import game_process
    game_process(partial(_play_shared, settings), batch_version, *arguments)


class EpisodeWorkers:
    """A fixed pool of spawned processes that play whole training episodes.

    A worker that dies raises BrokenProcessPool rather than leaving its game
    pending. Callers must start the pool from an importable main module.
    """

    def __init__(self, processes: int, *, calendar_rounds: int | None, model_config: Mapping[str, Any],
                 learning_config: Mapping[str, Any], rules_version: str, failed_positions: str | None = None):
        if type(processes) is not int or processes <= 0:
            raise ValueError("Episode workers must be a positive integer")
        self.processes = processes
        settings = {"calendar_rounds": calendar_rounds, "model_config": dict(model_config),
                    "learning_config": dict(learning_config), "rules_version": rules_version,
                    "failed_positions": failed_positions}
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
    fill. Processes last one batch, which is long enough that starting them
    costs little. A game process that dies after reporting a game is replaced, and
    the games it had not finished come back as failed games (_lost_game).
    """

    def __init__(self, processes: int, games_per_process: int, *, device: Any, runtime_policy: Any = None,
                 calendar_rounds: int | None, model_config: Mapping[str, Any], learning_config: Mapping[str, Any],
                 rules_version: str, compiled_forward: bool = False, failed_positions: str | None = None):
        from .neural import CampaignModelConfig, alliance_networks
        if type(processes) is not int or processes <= 0 or type(games_per_process) is not int or games_per_process <= 0:
            raise ValueError("Shared episode workers need positive process and game counts")
        self.processes, self.games_per_process = processes, games_per_process
        self.device, self.runtime_policy, self.compiled_forward = device, runtime_policy, compiled_forward
        self.settings = {"calendar_rounds": calendar_rounds, "model_config": dict(model_config),
                         "learning_config": dict(learning_config), "rules_version": rules_version,
                         "failed_positions": failed_positions}
        # The networks the inference server evaluates: one for all three alliances, or one for each.
        self.models = alliance_networks(CampaignModelConfig(**model_config),
                                        learning_config.get("networks", "one"), device=device)
        self.serving = None

    def play(self, games: Sequence[tuple[int, int]], *, weights: Mapping[str, Any], batch_version: str,
             max_transitions: int, stop: Callable[[], bool] = lambda: False) -> list[dict[str, Any]] | None:
        """Play (root, seed) games; results return in root order, or None if stopped."""
        from .neural import load_alliance_weights
        from .shared_evaluator import play_shared_games
        load_alliance_weights(self.models, weights)
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
                                                  exit_seconds=120.0, stop_seconds=15.0, lost_game=_lost_game,
                                                  compiled_forward=self.compiled_forward)
        if stopped or stop():
            return None
        if sorted(record["root"] for record in records) != sorted(root for root, _ in games):
            raise RuntimeError("A game process lost a game's result")
        return sorted(records, key=lambda record: record["root"])

    def play_continuously(self, feed: Callable[[], Mapping[str, Any] | None], *, weights: Mapping[str, Any],
                          version: str, keep_playing: Callable[[Any, list[dict[str, Any]]], bool]) -> list[dict[str, Any]]:
        """Self-play that never stops: games from `feed` until it returns None or
        `keep_playing(server, records)` returns false.

        `keep_playing` runs between two inference batches, where it may give the
        server new networks with `server.take_up(weights, version)`; every later
        request is answered with them. A game thread labels its search's cache with
        `version`, the version at the start, which the search needs to stay fixed
        within a decision; each reply names the version of the networks that
        answered. `keep_playing` must take each record off the front of `records`
        once it has used it, or the list would keep every game played. A game
        process that dies is replaced, as in play(), and its unfinished games reach
        `keep_playing` as failed games. Returns the records it did not take, games
        stopped by a stop included as failures.
        """
        from .neural import load_alliance_weights
        from .shared_evaluator import play_shared_games
        load_alliance_weights(self.models, weights)

        def keep(server: Any, records: list[dict[str, Any]]) -> bool:
            if server.network_version is None:  # Before the first inference batch.
                server.network_version = version
            return keep_playing(server, records)

        records, self.serving = play_shared_games(partial(_shared_process, self.settings, version), [],
                                                  processes=self.processes, games_per_process=self.games_per_process,
                                                  models=self.models, device=self.device,
                                                  runtime_policy=self.runtime_policy, keep_playing=keep,
                                                  exit_seconds=120.0, stop_seconds=15.0, feed=feed,
                                                  lost_game=_lost_game, compiled_forward=self.compiled_forward)
        return records

    def report(self, server: Any = None) -> dict[str, Any]:
        """The evaluator traffic of the last batch, or of a server still serving."""
        stats = self.serving if server is None else server.stats
        return {"evaluations": stats.requests, "serving_rounds": stats.rounds, "network_passes": stats.passes,
                "forward_seconds": stats.forward_seconds, "idle_seconds": stats.idle_seconds,
                # Requests in an inference batch: [inference batches, their seconds in serve()].
                "inference_batches": {str(size): [stats.requests_per_round[size], stats.seconds_per_round.get(size, 0.0)]
                                      for size in sorted(stats.requests_per_round)}}

    def terminate(self) -> None:
        """Nothing outlives a batch."""

    def close(self) -> None:
        """Nothing outlives a batch."""
