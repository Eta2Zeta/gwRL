"""Network evaluations for many self-play processes in one serving process.

Game processes keep the rules, the search and the network's input
preparation. For each position a search asks about, a game thread writes the
decision's zone input, a few integer arrays, into its own shared-memory buffer
and sends a short header through its own pipe. The serving process merges
every waiting position into one pass of the networks, one network reading
every position when it serves all three alliances, as by default, or each
alliance's network reading its own alliance's positions, evaluates it on its
device and replies with the priors and values. A thread waits for its reply before
preparing its next position, so its buffer is never overwritten while the
server reads it. When the server stops, it closes the pipes still open, and a
thread waiting for a reply raises EvaluatorClosed instead of waiting forever.

The server lays the waiting positions out with features.pack_zone_arrays and
runs neural.NetworkStack, whose pass is the one NeuralEvaluator's networks
run, so results match NeuralEvaluator's up to floating-point rounding. A pass
costs much more than its share of arithmetic, so one pass per round, rather
than one per alliance, saves most of that cost.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import multiprocessing
from multiprocessing import shared_memory
from multiprocessing.connection import Connection, wait
import queue
try:
    import resource
except ImportError:  # Windows has no open-file limit for these pipes and buffers.
    resource = None
import signal
import threading
import time
from typing import Any, Callable, Sequence

import numpy as np

from studies.shared.multiplayer_mcts import Evaluation, PLAYERS, vector

BUFFER_BYTES = 2 * 1024 * 1024  # One decision's zone input; the largest measured is 145 KB.


def prepare_into(buffer: memoryview, env: Any, actions: Sequence[Any]) -> tuple[str, list[tuple[str, str, tuple, int]]]:
    """Write a decision's zone input into `buffer`; return its layout version and header."""
    from .features import make_zone_input
    zone = make_zone_input(env, actions)
    header, offset = [], 0
    for name, values in zone.arrays().items():
        if offset + values.nbytes > len(buffer):
            raise ValueError("A decision's zone input does not fit its shared buffer")
        np.ndarray(values.shape, values.dtype, buffer=buffer, offset=offset)[...] = values
        header.append((name, values.dtype.str, values.shape, offset))
        offset += values.nbytes
    return zone.version, header


def read_arrays(buffer: memoryview, header: Sequence[tuple[str, str, tuple, int]]) -> dict[str, np.ndarray]:
    return {name: np.ndarray(shape, np.dtype(dtype), buffer=buffer, offset=offset)
            for name, dtype, shape, offset in header}


@dataclass
class ClientStats:
    requests: int = 0
    prepare_seconds: float = 0.0
    wait_seconds: float = 0.0


class EvaluatorClosed(RuntimeError):
    """The serving process closed this thread's pipe; its game cannot continue."""


class RemoteEvaluator:
    """One game thread's evaluator: one request in flight through its own pipe."""

    def __init__(self, connection: Connection, buffer_name: str, version: str) -> None:
        # `version` labels the search's cache within one decision and never changes.
        # `network_version` is the version of the networks that answered, which in
        # self-play that never stops changes between two inference batches; the
        # server names it in a reply only when it differs from the last it sent here.
        self.connection, self.version = connection, version
        self.network_version: str | None = None
        self.memory = shared_memory.SharedMemory(name=buffer_name)
        self.stats = ClientStats()

    def evaluate(self, env: Any, actions: Sequence[Any]) -> Evaluation:
        if env.is_terminal():
            if actions:
                raise ValueError("A terminal state cannot have policy actions")
            return Evaluation([], vector(env.returns()))
        actor = env.current_decision_player()
        if actor is None and (env.decision_kind() != "chance" or actions):
            raise ValueError("An ownerless nonterminal evaluation must be a chance cutoff")
        if actor is not None and actor not in PLAYERS:
            raise ValueError(f"Unknown campaign decision player: {actor}")
        started = time.perf_counter()
        layout, header = prepare_into(self.memory.buf, env, actions)
        sent = time.perf_counter()
        try:
            self.connection.send((actor, len(actions), layout, header))
            reply = self.connection.recv()
        except (EOFError, OSError) as error:  # BrokenPipeError is an OSError.
            raise EvaluatorClosed("The shared evaluator closed this game thread's pipe") from error
        self.stats.requests += 1
        self.stats.prepare_seconds += sent - started
        self.stats.wait_seconds += time.perf_counter() - sent
        priors, values = reply[0], reply[1]
        if len(reply) > 2:
            self.network_version = reply[2]
        if len(priors) != len(actions):
            raise ValueError("The shared evaluator returned a different legal menu")
        return Evaluation(priors, vector(values))

    def close(self) -> None:
        self.memory.close()
        self.connection.close()


def forward_prepared(model: Any, items: Sequence[dict[str, np.ndarray]], device: Any,
                     network_positions: Sequence[int] | None = None) -> tuple[Any, list[int], Any, Any]:
    """One network pass for positions already in arrays.

    `model` is a CampaignPolicyValueNet, or a neural.NetworkStack whose networks
    have network_positions[i] positions each, in order. Returns every legal
    option's logit in position order, each position's option count, the raw
    value rows, and the batch, whose host buffers the device copies read and
    which must stay alive until the outputs are collected.
    """
    from .features import pack_zone_arrays
    batch = pack_zone_arrays(items, model.spec, network_positions)
    # Device copies may still read the batch's host buffers; it stays alive until collect.
    scores, values = model.forward_packed(batch, non_blocking=True)
    return scores, batch.option_counts, values, batch


def evaluate_prepared(model: Any, items: Sequence[dict[str, np.ndarray]],
                      device: Any) -> tuple[list[list[float]], list[list[float]]]:
    """Each position's priors and raw values in NeuralEvaluator's units.

    One device-to-host copy carries every logit and value; each position's
    softmax then runs on the host, where a short menu costs microseconds rather
    than one accelerator dispatch per position.
    """
    return collect(model, *forward_prepared(model, items, device))


def collect(model: Any, scores: Any, lengths: Sequence[int], raw: Any,
            batch: Any = None) -> tuple[list[list[float]], list[list[float]]]:
    """Host priors and raw values from forward_prepared's device outputs.

    Reading them back waits for the device, after which `batch` may go."""
    import torch
    # float(): a pass under automatic mixed precision may give 16-bit outputs, which numpy may not read.
    host = torch.cat((scores, (raw * model.config.value_scale).reshape(-1))).float().cpu().numpy().astype(np.float64)
    if not np.isfinite(host).all():
        raise ValueError("Neural evaluation returned a nonfinite logit or value")
    split = int(sum(lengths))
    logits, values = host[:split], host[split:].reshape(-1, 3)
    priors, offset = [], 0
    for count in lengths:
        row = logits[offset:offset + count]
        offset += count
        if count:
            weights = np.exp(row - row.max())
            priors.append((weights / weights.sum()).tolist())
        else:
            priors.append([])
    return priors, values.tolist()


@dataclass
class ServerStats:
    requests: int = 0
    rounds: int = 0                  # Serving rounds: the waiting requests answered together.
    requests_per_round: dict[int, int] = field(default_factory=dict)
    passes: int = 0                  # Network passes: one per round, for every alliance's positions.
    # Positions per pass; a chance position counts once for each network.
    positions_per_pass: dict[int, int] = field(default_factory=dict)
    receive_seconds: float = 0.0     # Reading requests from the ready pipes.
    forward_seconds: float = 0.0     # Answering: reading, laying out, the pass and host outputs.
    reply_seconds: float = 0.0       # Sending priors and values back.
    idle_seconds: float = 0.0
    # Seconds of the inference batches of each size, by their number of requests:
    # reading the requests, answering them and replying, as in serve().
    seconds_per_round: dict[int, float] = field(default_factory=dict)


class SharedEvaluatorServer:
    """Answers every game thread's requests, batching whatever is waiting."""

    def __init__(self, models: dict[str, Any], device: Any, connections: Sequence[Connection],
                 buffer_names: Sequence[str], runtime_policy: Any = None, *, compiled_forward: bool = False) -> None:
        if set(models) != set(PLAYERS):
            raise ValueError("Provide one campaign model for Axis, Allies and Comintern")
        self.models, self.device = models, device
        # One network's zone and position layers compiled for fixed numbers of states,
        # unless the layers as written are asked for (answer_as_written).
        self.compiled_forward = compiled_forward
        self.as_written = False
        # MPS graph-cache housekeeping after completed forwards (device_runtime).
        self.runtime_policy = runtime_policy
        self.connections = list(connections)
        self.memories = {connection: shared_memory.SharedMemory(name=name)
                         for connection, name in zip(connections, buffer_names, strict=True)}
        self._stack = None
        self.stats = ServerStats()
        # The version of `models`, named in a game thread's next reply whenever it
        # differs from the last one sent there. None names no version.
        self.network_version: str | None = None
        self._named: dict[Connection, str] = {}

    def take_up(self, weights: dict[str, Any], version: str) -> None:
        """Answer every later request with these weights: between two inference batches."""
        from .neural import load_alliance_weights
        load_alliance_weights(self.models, weights)  # One network serving all three alliances loads once.
        self._stack = None  # The stack copied the old tables; the next batch builds a new one.
        self.network_version = version

    def answer_as_written(self, as_written: bool) -> None:
        """Run the layers as written, not compiled, from the next inference batch while
        as_written holds: while a network update trains beside self-play on the same
        device. On PyTorch 2.14 a compiled MPS kernel waits for the GPU's dispatch
        queue while it holds Python's lock, and a trainer's operation already on that
        queue can need the lock, which deadlocks the process."""
        if as_written != self.as_written:
            self.as_written = as_written
            self._stack = None  # The next inference batch builds the stack it needs.

    @property
    def stack(self) -> Any:
        """The networks for one pass, which reads their weights once, at the first request:
        the three alliances' networks, or one network that serves all three."""
        if self._stack is None:
            from .neural import NetworkStack, distinct_networks
            networks = distinct_networks(self.models)
            self._network_of = {player: next(index for index, network in enumerate(networks)
                                             if network is self.models[player]) for player in PLAYERS}
            self._stack = NetworkStack(networks, compiled=self.compiled_forward and not self.as_written)
        return self._stack

    def serve(self, keep_running: Callable[[], bool]) -> None:
        """Answer requests until every client closes its pipe or keep_running() is false.

        Stopping closes the pipes still open, so a thread still sending or waiting
        for its reply gets EvaluatorClosed rather than waiting forever."""
        open_connections = list(self.connections)
        while open_connections:
            if not keep_running():
                for connection in open_connections:
                    connection.close()
                return
            before = time.perf_counter()
            ready = wait(open_connections, timeout=0.05)
            received = time.perf_counter()
            self.stats.idle_seconds += received - before
            requests = []
            for connection in ready:
                try:
                    message = connection.recv()
                except EOFError:
                    open_connections.remove(connection)
                    continue
                requests.append((connection, message))
            self.stats.receive_seconds += time.perf_counter() - received
            if requests:
                self.answer(requests)
                spent = self.stats.seconds_per_round
                spent[len(requests)] = spent.get(len(requests), 0.0) + time.perf_counter() - received

    def answer(self, requests: Sequence[tuple[Connection, tuple]]) -> None:
        import torch
        started = time.perf_counter()
        stack = self.stack
        rows: list[list[int]] = [[] for _ in stack.models]
        items = []
        for row, (connection, (actor, count, layout, header)) in enumerate(requests):
            readers = PLAYERS if actor is None else (actor,)
            if any(self.models[player].layout_version != layout for player in readers):
                raise ValueError("A game sent a zone input of another layout")
            items.append(read_arrays(self.memories[connection].buf, header))
            # A chance position is rated by every network, once by each.
            for network in sorted({self._network_of[player] for player in readers}):
                rows[network].append(row)
        # One pass for every alliance's positions, grouped by network.
        order = [row for network_rows in rows for row in network_rows]
        with torch.inference_mode():
            outputs = forward_prepared(stack, [items[row] for row in order], self.device,
                                       [len(network_rows) for network_rows in rows])
            row_priors, row_values = collect(stack, *outputs)
        priors: list[list[float]] = [[] for _ in requests]
        chance: dict[int, list[list[float]]] = {}
        values: list[list[float] | None] = [None] * len(requests)
        for row, prior, value in zip(order, row_priors, row_values, strict=True):
            if requests[row][1][0] is None:
                chance.setdefault(row, []).append(value)
            else:
                priors[row], values[row] = prior, value
        for row, found in chance.items():
            values[row] = [sum(value[i] for value in found) / len(found) for i in range(3)]
        sending = time.perf_counter()
        version = self.network_version
        for (connection, _), row_priors, value in zip(requests, priors, values, strict=True):
            if version is not None and self._named.get(connection) != version:
                connection.send((row_priors, value, version))
                self._named[connection] = version
            else:
                connection.send((row_priors, value))
        sent = time.perf_counter()
        if self.runtime_policy is not None:
            self.runtime_policy.completed(1)
        stats = self.stats
        stats.requests += len(requests)
        stats.rounds += 1
        stats.requests_per_round[len(requests)] = stats.requests_per_round.get(len(requests), 0) + 1
        stats.passes += 1
        stats.positions_per_pass[len(order)] = stats.positions_per_pass.get(len(order), 0) + 1
        stats.reply_seconds += sent - sending
        # Graph-cache housekeeping after the replies counts as device work.
        stats.forward_seconds += (sending - started) + (time.perf_counter() - sent)

    def close(self) -> None:
        for memory in self.memories.values():
            memory.close()


def raise_descriptor_limit(wanted: int) -> None:
    """Raise the soft open-file limit towards `wanted`, never lowering it."""
    if resource is None:
        return
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    wanted = wanted if hard == resource.RLIM_INFINITY else min(wanted, hard)
    if soft != resource.RLIM_INFINITY and soft < wanted:
        resource.setrlimit(resource.RLIMIT_NOFILE, (wanted, hard))


def _next_task(tasks: Any) -> Any:
    """A blocking get, since get_nowait can report an empty queue before queued
    tasks reach this process. A process orphaned by its coordinator's death stops."""
    while True:
        try:
            return tasks.get(timeout=5)
        except queue.Empty:
            parent = multiprocessing.parent_process()
            if parent is not None and not parent.is_alive():
                return None


def game_process(play: Callable[[Any, RemoteEvaluator], dict[str, Any]], version: str,
                 slots: Sequence[int], connections: Sequence[Connection], buffer_names: Sequence[str],
                 tasks: Any, results: Any) -> None:
    """A game process: one thread per game slot, each taking tasks until its stop marker.

    `play(task, evaluator)` returns a game's record and handles its own failures.
    """

    def slot(index: int, connection: Connection, name: str) -> None:
        evaluator = RemoteEvaluator(connection, name, version)
        try:
            while (task := _next_task(tasks)) is not None:
                results.put({**play(task, evaluator), "slot": index})
        finally:
            evaluator.close()

    threads = [threading.Thread(target=slot, args=arguments, name=f"campaign-game-{arguments[0]}", daemon=True)
               for arguments in zip(slots, connections, buffer_names)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    parent = multiprocessing.parent_process()
    if parent is not None and not parent.is_alive():
        results.cancel_join_thread()  # Exit must not wait for a reader that has gone.


def _game_process_main(target: Callable[..., None], *arguments: Any) -> None:
    # The coordinator stops games by closing their pipes. A signal to the process
    # group (Ctrl+Break on Windows) must reach it, not end games under it.
    for number in (signal.SIGINT, signal.SIGTERM, *([signal.SIGBREAK] if hasattr(signal, "SIGBREAK") else [])):
        signal.signal(number, signal.SIG_IGN)
    target(*arguments)


def play_shared_games(target: Callable[..., None], tasks: Sequence[Any], *, processes: int, games_per_process: int,
                      models: dict[str, Any], device: Any, runtime_policy: Any = None,
                      keep_playing: Callable[[SharedEvaluatorServer, list[Any]], bool] = lambda *_: True,
                      exit_seconds: float = 20.0, stop_seconds: float = 20.0,
                      feed: Callable[[], Any] | None = None,
                      compiled_forward: bool = False) -> tuple[list[Any], ServerStats]:
    """Play tasks in game processes, evaluating every waiting position here.

    `target(slots, connections, buffer_names, tasks, results)` is the game process,
    normally game_process with its first arguments bound. Each process plays
    `games_per_process` games at once, one per thread, taking tasks from one queue,
    so a finished game's slot starts the next. `keep_playing(server, records)` runs
    between serving rounds; returning false closes every pipe, ending the running
    games. Processes get `exit_seconds` to exit after the last game and
    `stop_seconds` after a stop. Returns the records that arrived and the server's
    statistics.

    With `feed`, games keep coming instead: `tasks` must be empty, and `feed()`
    returns the next game's task, or None once no more games should start. A few
    tasks wait queued beyond the game slots, so a slot that finishes a game starts
    the next at once, and serving goes on until `keep_playing` returns false or
    every game fed has reported.
    """
    if feed is not None and tasks:
        raise ValueError("Give either a list of tasks or a feed, not both")
    context = multiprocessing.get_context("spawn")
    slots = processes * games_per_process
    # A slot holds two pipe ends and its buffer mapped twice, and a shell's default
    # limit of 256 stops at eight processes of six games.
    raise_descriptor_limit(6 * slots + 64)
    pipes = [context.Pipe() for _ in range(slots)]
    memories = [shared_memory.SharedMemory(create=True, size=BUFFER_BYTES) for _ in range(slots)]
    waiting, results = context.Queue(), context.Queue()
    fed, fed_out = 0, feed is None

    def top_up() -> None:
        # Fed games beyond those already reported: the slots' games and a few queued.
        nonlocal fed, fed_out
        while not fed_out and fed - len(records) < slots + max(2, slots // 4):
            task = feed()
            if task is None:
                fed_out = True
                for _ in range(slots):  # One stop marker per game slot.
                    waiting.put(None)
                return
            waiting.put(task)
            fed += 1

    if feed is None:
        for task in [*tasks, *[None] * slots]:  # One stop marker per game slot.
            waiting.put(task)
    spawned, records, unread, server = [], [], [], None
    finished, stopping = threading.Event(), False

    def receive() -> None:
        # A record far outgrows a pipe's buffer, and a process that dies sending one
        # leaves half a message. Reading it would wait forever, because this process
        # also holds the pipe's write end, so only this thread reads.
        while not finished.is_set():
            try:
                records.append(results.get(timeout=0.2))
            except queue.Empty:
                pass
            except Exception as error:
                unread.append(error)
                return

    receiver = threading.Thread(target=receive, name="campaign-game-records", daemon=True)
    try:
        receiver.start()
        if feed is not None:
            top_up()
        for index in range(processes):
            members = range(index * games_per_process, (index + 1) * games_per_process)
            process = context.Process(target=_game_process_main, daemon=True, args=(
                target, list(members), [pipes[member][1] for member in members],
                [memories[member].name for member in members], waiting, results))
            process.start()
            spawned.append(process)
        for _, child in pipes:
            child.close()
        server = SharedEvaluatorServer(models, device, [parent for parent, _ in pipes],
                                       [memory.name for memory in memories], runtime_policy,
                                       compiled_forward=compiled_forward)

        def keep_running() -> bool:
            nonlocal stopping, fed_out
            if unread:
                raise unread[0]
            # Every game has reported, whatever else still holds a pipe open.
            if fed_out and len(records) >= (len(tasks) if feed is None else fed):
                return False
            # A stop comes first: its signal may have killed processes still starting.
            stopping = not keep_playing(server, records)
            if stopping:
                if not fed_out:  # Queued games end at once, then each slot's marker stops it.
                    fed_out = True
                    for _ in range(slots):
                        waiting.put(None)
                return False
            if not all(process.is_alive() or process.exitcode == 0 for process in spawned):
                raise ValueError("A game process exited abnormally")
            if feed is not None:
                top_up()
            return True

        server.serve(keep_running)
        # The server closed every pipe still open, so a thread still waiting for
        # an evaluation ends its game. A process exits only once its queued
        # results reach the pipe, which the receiver reads meanwhile.
        stop = time.monotonic() + (stop_seconds if stopping else exit_seconds)
        while time.monotonic() < stop and any(process.is_alive() for process in spawned):
            time.sleep(0.05)
        stragglers = [process for process in spawned if process.is_alive()]
        for process in stragglers:
            process.kill()
        for process in stragglers:
            process.join(timeout=1)  # Reaped, so their CPU time is counted.
        # What a clean exit flushed may still be in the pipe.
        clean = all(process.exitcode == 0 for process in spawned)
        stop = time.monotonic() + 5
        while clean and len(records) < (len(tasks) if feed is None else fed) and time.monotonic() < stop:
            time.sleep(0.05)
    finally:
        finished.set()
        for process in spawned:
            if process.is_alive():
                process.kill()
        if server is not None:
            server.close()
        for memory in memories:
            memory.close()
            memory.unlink()
        for parent, _ in pipes:
            parent.close()
    return records, server.stats
