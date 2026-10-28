"""Batch inference across independent, otherwise unchanged VectorMCTS searches.

Each worker owns one search tree and its RNG. With ``evaluation="batched"`` it
waits at an evaluation boundary while the calling thread evaluates all ready
roots together. A wave ends when every live worker has requested inference or
finished; a short/terminal root therefore cannot hold the remaining roots at a
barrier. Only the calling thread invokes the evaluator (including when it uses
an accelerator).

With ``evaluation="per_search"`` each worker evaluates its own requests one at a
time on its own thread, so no root waits for another. Every request is a
single-position batch, which keeps results independent of thread timing and of
how many roots search together. The evaluator must allow concurrent CPU calls.
"""
from __future__ import annotations

import queue
import threading
import time
from concurrent.futures import CancelledError, Future, TimeoutError
from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

from studies.shared.multiplayer_mcts import (
    Evaluation, MctsConfig, OpponentPolicy, SearchEnv, SearchResult, VectorMCTS,
    probabilities, vector,
)


class BatchEvaluator(Protocol):
    version: str

    def evaluate_batch(self, requests: Sequence[tuple[SearchEnv, Sequence[Any]]]) -> Sequence[Evaluation]: ...


@dataclass
class BatchStats:
    """Per-call, measured inference traffic; batch size means actual requests.

    Per-search evaluation sums inference seconds across search threads, so they
    can exceed the elapsed wall time.
    """

    roots: int = 0
    requests: int = 0
    batches: int = 0
    batch_sizes: list[int] = field(default_factory=list)
    inference_seconds: float = 0.0
    elapsed_seconds: float = 0.0


@dataclass
class _Request:
    root: int
    env: SearchEnv
    actions: Sequence[Any]
    reply: Future[Evaluation] = field(default_factory=Future)


@dataclass
class _Finished:
    root: int
    result: SearchResult | None = None
    error: BaseException | None = None


class _Aborted(Exception):
    pass


class _Proxy:
    def __init__(self, root: int, version: str, events: queue.Queue, stop: threading.Event):
        self.root, self.version, self.events, self.stop = root, version, events, stop

    def evaluate(self, env: SearchEnv, actions: Sequence[Any]) -> Evaluation:
        if self.stop.is_set():
            raise _Aborted()
        request = _Request(self.root, env, tuple(actions))
        self.events.put(request)
        while not self.stop.is_set():
            try:
                return request.reply.result(timeout=0.05)
            except TimeoutError:
                continue
        raise _Aborted()


class _DirectProxy:
    """Evaluate each request alone on the calling search thread."""

    def __init__(self, evaluator: BatchEvaluator, version: str, stop: threading.Event,
                 cancel_event: threading.Event | None, metrics: BatchStats, lock: threading.Lock):
        self.evaluator, self.version, self.stop = evaluator, version, stop
        self.cancel_event, self.metrics, self.lock = cancel_event, metrics, lock

    def evaluate(self, env: SearchEnv, actions: Sequence[Any]) -> Evaluation:
        if self.stop.is_set():
            raise _Aborted()
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise CancelledError("Independent-root search cancelled")
        if self.evaluator.version != self.version:
            raise ValueError("Evaluator version changed during independent-root search")
        actions = tuple(actions)
        before = time.perf_counter()
        evaluations = list(self.evaluator.evaluate_batch([(env, actions)]))
        elapsed = time.perf_counter() - before
        if self.evaluator.version != self.version:
            raise ValueError("Evaluator version changed during independent-root search")
        if len(evaluations) != 1:
            raise ValueError("Batched evaluator must return one Evaluation per request")
        weights = tuple(evaluations[0].priors)
        probabilities(weights, len(actions))
        result = Evaluation(weights, vector(evaluations[0].values))
        with self.lock:
            self.metrics.inference_seconds += elapsed
            self.metrics.requests += 1
            self.metrics.batches += 1
            self.metrics.batch_sizes.append(1)
        return result


def search_many(
    envs: Sequence[SearchEnv], evaluator: BatchEvaluator, config: MctsConfig | None = None, *,
    configs: Sequence[MctsConfig] | None = None,
    opponent_policies: OpponentPolicy | Sequence[OpponentPolicy | None] | None = None,
    add_root_noise: bool = False, max_batch_size: int | None = None,
    cancel_event: threading.Event | None = None, stats: BatchStats | None = None,
    evaluation: str = "batched",
) -> list[SearchResult]:
    """Search independent roots and return results in input order.

    ``evaluate_batch`` receives ``(environment, legal_actions)`` tuples and must
    return one Evaluation per tuple in the same order, in raw three-player
    value units. A scalar ``config`` is shared; ``configs`` supplies one per
    root. Search caches are local to this call and never shared between roots.

    Cancellation is cooperative at inference boundaries. Pending workers are
    released on cancellation, evaluator errors, worker errors, or Ctrl-C; an
    evaluator already executing is allowed to return before cancellation is
    observed. No Python API can interrupt arbitrary evaluator/environment code.
    The evaluator's version must stay frozen throughout the call.

    ``evaluation="per_search"`` evaluates every request alone on its search's
    own thread (see the module notes). It takes no batch cap and refuses an
    evaluator whose ``concurrent_evaluation`` is false.
    """
    roots = list(envs)
    count = len(roots)
    if config is not None and configs is not None:
        raise ValueError("Use either one config or per-root configs")
    settings = list(configs) if configs is not None else [config or MctsConfig()] * count
    if len(settings) != count or any(not isinstance(item, MctsConfig) for item in settings):
        raise ValueError("Provide one MctsConfig per root")
    if isinstance(opponent_policies, OpponentPolicy) or opponent_policies is None:
        policies = [opponent_policies] * count
    else:
        policies = list(opponent_policies)
    if len(policies) != count or any(item is not None and not isinstance(item, OpponentPolicy) for item in policies):
        raise ValueError("Provide one opponent policy per root")
    if max_batch_size is not None and (not isinstance(max_batch_size, int) or max_batch_size <= 0):
        raise ValueError("Maximum batch size must be a positive integer")
    if evaluation not in ("batched", "per_search"):
        raise ValueError("Evaluation must be batched or per_search")
    if evaluation == "per_search":
        if max_batch_size is not None:
            raise ValueError("A batch cap applies only to batched evaluation")
        # Accelerated evaluators keep the single calling thread for device work.
        if getattr(evaluator, "concurrent_evaluation", True) is not True:
            raise ValueError("Per-search evaluation needs an evaluator that allows concurrent CPU calls")
    version = evaluator.version
    if not isinstance(version, str) or not version:
        raise ValueError("Batched evaluator needs a nonempty version")
    metrics = stats if stats is not None else BatchStats()
    metrics.roots, metrics.requests, metrics.batches = count, 0, 0
    metrics.batch_sizes.clear()
    metrics.inference_seconds, metrics.elapsed_seconds = 0.0, 0.0
    started = time.perf_counter()
    if cancel_event is not None and cancel_event.is_set():
        raise CancelledError("Independent-root search cancelled")
    if not roots:
        return []

    events: queue.Queue[_Request | _Finished] = queue.Queue()
    stop = threading.Event()
    results: list[SearchResult | None] = [None] * count
    active = set(range(count))
    pending: dict[int, _Request] = {}
    metrics_lock = threading.Lock()

    def worker(index: int) -> None:
        try:
            proxy = (_DirectProxy(evaluator, version, stop, cancel_event, metrics, metrics_lock)
                     if evaluation == "per_search" else _Proxy(index, version, events, stop))
            search = VectorMCTS(proxy, settings[index], opponent_policy=policies[index])
            result = search.search(roots[index], add_root_noise=add_root_noise)
            events.put(_Finished(index, result=result))
        except BaseException as error:
            events.put(_Finished(index, error=error))

    workers = [threading.Thread(target=worker, args=(index,), name=f"campaign-search-{index}", daemon=True)
               for index in range(count)]

    def check_cancelled() -> None:
        if cancel_event is not None and cancel_event.is_set():
            raise CancelledError("Independent-root search cancelled")

    try:
        for thread in workers:
            thread.start()
        while active and evaluation == "per_search":
            # Workers evaluate for themselves; only completions arrive here.
            check_cancelled()
            try:
                finished = events.get(timeout=0.05)
            except queue.Empty:
                continue
            active.remove(finished.root)
            if finished.error is not None:
                raise finished.error
            results[finished.root] = finished.result
        while active:
            # Every worker is either computing, awaiting its one outstanding
            # request, or finished. Finished roots leave this dynamic barrier.
            while len(pending) < len(active):
                check_cancelled()
                try:
                    event = events.get(timeout=0.05)
                except queue.Empty:
                    continue
                if isinstance(event, _Finished):
                    active.remove(event.root)
                    if event.error is not None:
                        raise event.error
                    results[event.root] = event.result
                else:
                    if event.root not in active or event.root in pending:
                        raise RuntimeError("A search issued overlapping inference requests")
                    pending[event.root] = event
            if not pending:
                continue
            wave = [pending[index] for index in sorted(pending)]
            pending.clear()
            limit = max_batch_size or len(wave)
            for offset in range(0, len(wave), limit):
                check_cancelled()
                if evaluator.version != version:
                    raise ValueError("Evaluator version changed during independent-root search")
                batch = wave[offset:offset + limit]
                before = time.perf_counter()
                evaluations = list(evaluator.evaluate_batch([(item.env, item.actions) for item in batch]))
                metrics.inference_seconds += time.perf_counter() - before
                metrics.requests += len(batch)
                metrics.batches += 1
                metrics.batch_sizes.append(len(batch))
                if evaluator.version != version:
                    raise ValueError("Evaluator version changed during independent-root search")
                if len(evaluations) != len(batch):
                    raise ValueError("Batched evaluator must return one Evaluation per request")
                # Validate the whole batch before releasing any member. This
                # includes ownerless chance-cutoff values with no legal moves.
                validated = []
                for item, result in zip(batch, evaluations):
                    weights = tuple(result.priors)
                    probabilities(weights, len(item.actions))
                    # MCTS performs normalization itself. Validating without
                    # normalizing twice preserves scalar-search arithmetic.
                    validated.append(Evaluation(weights, vector(result.values)))
                check_cancelled()
                for item, result in zip(batch, validated):
                    item.reply.set_result(result)
        if any(result is None for result in results):
            raise RuntimeError("An independent search finished without a result")
        return results  # type: ignore[return-value]
    finally:
        stop.set()
        # Never turn cancellation into an unbounded join on arbitrary user
        # environment code. Proxy waits poll stop, so normal workers exit now.
        deadline = time.monotonic() + 0.25
        for thread in workers:
            if thread.ident is not None:
                thread.join(timeout=max(0.0, deadline - time.monotonic()))
        metrics.elapsed_seconds = time.perf_counter() - started
