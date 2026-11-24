"""Network evaluations for many self-play processes in one serving process.

Game processes keep the rules, the search and the network's input
preparation. For each position a search asks about, a game thread writes the
decision's zone input, a few integer arrays, into its own shared-memory buffer
and sends a short binary request through its own pipe; the C++ search does this
without Python (InferenceClient, include/game/inference_client.hpp, which also
describes the messages). The serving process merges every waiting position into
one pass of the networks, one network reading every position when it serves all
three alliances, as by default, or each alliance's network reading its own
alliance's positions, evaluates it on its device and replies with the priors
and values. A thread waits for its reply before preparing its next position, so
its buffer is never overwritten while the server reads it. When the server
stops, it closes the pipes still open, and a thread waiting for a reply raises
EvaluatorClosed instead of waiting forever.

Each game process also has a task pipe of its own, which brings its game
threads their games one at a time, numbered, and a result pipe of its own, which
takes each finished game's record back with its number. So the coordinator
knows which games each process holds, and a process that dies cannot leave a
shared pipe locked or half written. play_shared_games can then record the games
that process had not finished as failed and start a new process for its game
slots, while the other processes play on.

The server lays the waiting positions out with features.pack_zone_arrays and
runs neural.NetworkStack, whose pass is the one NeuralEvaluator's networks
run, so results match NeuralEvaluator's up to floating-point rounding. A pass
costs much more than its share of arithmetic, so one pass per round, rather
than one per alliance, saves most of that cost.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import itertools
import multiprocessing
from multiprocessing import shared_memory
import os
from multiprocessing.connection import Connection, wait
from multiprocessing.reduction import ForkingPickler
try:
    import resource
except ImportError:  # Windows has no open-file limit for these pipes and buffers.
    resource = None
import faulthandler
import json
from pathlib import Path
import shutil
import signal
import struct
import sys
import threading
import time
from typing import Any, Callable, Sequence

import numpy as np

import gwrl_cpp

from studies.shared.multiplayer_mcts import Evaluation, PLAYERS, vector

BUFFER_BYTES = 2 * 1024 * 1024  # One decision's zone input; the largest measured is 145 KB.

# A zone input's fields in the order InferenceClient writes them into a buffer.
ZONE_FIELDS = ("zone_index", "zone_column", "zone_value", "global_column", "global_value", "action_offsets",
               "action_column", "action_value", "action_source", "action_target", "path_offsets", "path_zone",
               "factor_groups")
# A request: kind 1, the actor's number (-1 at chance), the layout version's
# length, the option count and each field's length; the layout version follows.
REQUEST = struct.Struct("<BbHI" + "I" * len(ZONE_FIELDS))
# A reply: the option count and the network version's length; then the priors
# and the three values as doubles, and the network version.
REPLY = struct.Struct("<II")
VALUES = struct.Struct("<3d")
# A request of several positions, which a search sends when it gathers several
# simulations before asking (simulations_per_request): kind 2, a zero byte, the
# layout version's length and the number of positions; then for each position
# its actor's number (-1 at chance), its option count and each field's length,
# its fields lying in the buffer after the previous position's; the layout
# version follows. Its reply: the number of positions and the network version's
# length; then for each position its option count, its priors and its three
# values as doubles; then the network version.
SEVERAL = struct.Struct("<BBHI")
POSITION = struct.Struct("<iI" + "I" * len(ZONE_FIELDS))
COUNT = struct.Struct("<I")


def _arrays(buffer: memoryview, lengths: Sequence[int], offset: int) -> tuple[dict[str, np.ndarray], int]:
    arrays = {}
    for name, length in zip(ZONE_FIELDS, lengths):
        arrays[name] = np.ndarray((length,), np.int32, buffer=buffer, offset=offset)
        offset += 4 * length
    return arrays, offset


def read_request(buffer: memoryview, message: bytes) -> tuple[str | None, int, str, dict[str, np.ndarray]]:
    """A request's actor (None at chance), option count, layout version and the
    zone input's arrays, read in place from the thread's buffer."""
    kind, actor, layout_length, count, *lengths = REQUEST.unpack_from(message)
    if kind != 1 or not -1 <= actor < len(PLAYERS) or len(message) != REQUEST.size + layout_length:
        raise ValueError("A game sent a malformed inference request")
    layout = message[REQUEST.size:].decode()
    arrays, _ = _arrays(buffer, lengths, 0)
    return (None if actor < 0 else PLAYERS[actor]), count, layout, arrays


def read_positions(buffer: memoryview, message: bytes) -> tuple[list[tuple[str | None, int, dict[str, np.ndarray]]], str, bool]:
    """A request of one position or of several: each position's actor (None at
    chance), option count and zone-input arrays, read in place from the thread's
    buffer; the layout version; and whether the request was of several."""
    if message[:1] != bytes((2,)):
        actor, count, layout, arrays = read_request(buffer, message)
        return [(actor, count, arrays)], layout, False
    kind, zero, layout_length, positions = SEVERAL.unpack_from(message)
    start = SEVERAL.size + positions * POSITION.size
    if zero or not positions or len(message) != start + layout_length:
        raise ValueError("A game sent a malformed inference request")
    found, offset = [], 0
    for index in range(positions):
        actor, count, *lengths = POSITION.unpack_from(message, SEVERAL.size + index * POSITION.size)
        if not -1 <= actor < len(PLAYERS):
            raise ValueError("A game sent a malformed inference request")
        arrays, offset = _arrays(buffer, lengths, offset)
        found.append(((None if actor < 0 else PLAYERS[actor]), count, arrays))
    return found, message[start:].decode(), True


def reply_bytes(priors: Any, values: Sequence[float], version: str | None) -> bytes:
    """A reply's bytes: priors as float64, the values, and the network version when named."""
    named = b"" if version is None else version.encode()
    weights = np.asarray(priors, dtype=np.float64)
    return REPLY.pack(len(weights), len(named)) + weights.tobytes() + VALUES.pack(*values) + named


def several_reply_bytes(answers: Sequence[tuple[Any, Sequence[float]]], version: str | None) -> bytes:
    """The reply to a request of several positions: each position's priors and values, in order."""
    named = b"" if version is None else version.encode()
    parts = [REPLY.pack(len(answers), len(named))]
    for priors, values in answers:
        weights = np.asarray(priors, dtype=np.float64)
        parts += [COUNT.pack(len(weights)), weights.tobytes(), VALUES.pack(*values)]
    parts.append(named)
    return b"".join(parts)


@dataclass
class ClientStats:
    requests: int = 0
    prepare_seconds: float = 0.0
    wait_seconds: float = 0.0


# The server closed this thread's pipe; its game cannot continue. The C++
# client raises it, from a search or from RemoteEvaluator.evaluate.
EvaluatorClosed = gwrl_cpp.InferenceClosed


class RemoteEvaluator:
    """One game thread's evaluator: one request in flight through its own pipe.

    Its native client (gwrl_cpp.InferenceClient) is what the C++ search uses,
    without Python's lock. Windows pipes are not file descriptors, so there, or
    with native=False, Python sends the same messages, and the C++ search calls
    evaluate_zone for each position."""

    def __init__(self, connection: Connection, buffer_name: str, version: str, *,
                 native: bool = sys.platform != "win32") -> None:
        # `version` labels the search's cache within one decision and never changes.
        # `network_version` is the version of the networks that answered, which in
        # self-play that never stops changes between two inference batches; the
        # server names it in a reply only when it differs from the last it sent here.
        self.connection, self.version = connection, version
        self.client = gwrl_cpp.InferenceClient(connection.fileno(), buffer_name, BUFFER_BYTES) if native else None
        self.memory = None if native else shared_memory.SharedMemory(name=buffer_name)
        self._stats, self._network_version = ClientStats(), None

    @property
    def network_version(self) -> str | None:
        return self.client.network_version if self.client is not None else self._network_version

    @property
    def stats(self) -> ClientStats:
        if self.client is None:
            return self._stats
        return ClientStats(self.client.requests, self.client.prepare_seconds, self.client.wait_seconds)

    def evaluate(self, env: Any, actions: Sequence[Any]) -> Evaluation:
        """The Python search's way in."""
        if env.is_terminal():
            if actions:
                raise ValueError("A terminal state cannot have policy actions")
            return Evaluation([], vector(env.returns()))
        actor = env.current_decision_player()
        if actor is None and (env.decision_kind() != "chance" or actions):
            raise ValueError("An ownerless nonterminal evaluation must be a chance cutoff")
        if actor is not None and actor not in PLAYERS:
            raise ValueError(f"Unknown campaign decision player: {actor}")
        from .features import make_zone_input
        return self.evaluate_zone(make_zone_input(env, actions), actor)

    def evaluate_zone(self, zone: Any, actor: str | None) -> Evaluation:
        """One position from its zone input; actor None at a chance cutoff."""
        if self.client is not None:
            priors, values = self.client.evaluate(zone, actor)
            return Evaluation(priors, vector(values))
        started = time.perf_counter()
        arrays, buffer, offset, lengths = zone.arrays(), self.memory.buf, 0, []
        for name in ZONE_FIELDS:
            values = arrays[name]
            if offset + values.nbytes > len(buffer):
                raise ValueError("A decision's zone input does not fit its shared buffer")
            np.ndarray(values.shape, np.int32, buffer=buffer, offset=offset)[...] = values
            lengths.append(len(values))
            offset += values.nbytes
        layout = zone.version.encode()
        number = -1 if actor is None else PLAYERS.index(actor)
        sent = time.perf_counter()
        try:
            self.connection.send_bytes(REQUEST.pack(1, number, len(layout), zone.action_count, *lengths) + layout)
            reply = self.connection.recv_bytes()
        except (EOFError, OSError) as error:  # BrokenPipeError is an OSError.
            raise EvaluatorClosed("The shared evaluator closed this game thread's pipe") from error
        count, named = REPLY.unpack_from(reply)
        if count != zone.action_count:
            raise ValueError("The shared evaluator returned a different legal menu")
        priors = np.frombuffer(reply, np.float64, count, REPLY.size).tolist()
        values = VALUES.unpack_from(reply, REPLY.size + 8 * count)
        if named:
            self._network_version = reply[REPLY.size + 8 * count + VALUES.size:].decode()
        self._stats.requests += 1
        self._stats.prepare_seconds += sent - started
        self._stats.wait_seconds += time.perf_counter() - sent
        return Evaluation(priors, vector(values))

    def close(self) -> None:
        if self.client is not None:
            self.client.close()
        if self.memory is not None:
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


def joined_outputs(model: Any, scores: Any, raw: Any) -> Any:
    """Every logit and value of a pass in one array on the pass's device, values in NeuralEvaluator's units."""
    import torch
    # float(): a pass under automatic mixed precision may give 16-bit outputs, which numpy may not read.
    return torch.cat((scores, (raw * model.config.value_scale).reshape(-1))).float()


def collect(model: Any, scores: Any, lengths: Sequence[int], raw: Any,
            batch: Any = None, *, as_lists: bool = True) -> tuple[list[Any], list[list[float]]]:
    """Host priors and raw values from forward_prepared's device outputs.

    Each position's priors are a list, or with as_lists=False a float64 array of
    the same numbers. Reading them back waits for the device, after which
    `batch` may go."""
    return host_priors(joined_outputs(model, scores, raw).cpu().numpy(), lengths, as_lists=as_lists)


def host_priors(joined: np.ndarray, lengths: Sequence[int], *,
                as_lists: bool = True) -> tuple[list[Any], list[list[float]]]:
    """Each position's priors, by a softmax of its logits on the host, and its values, from joined_outputs on the host."""
    host = joined.astype(np.float64)
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
            weights = weights / weights.sum()
            priors.append(weights.tolist() if as_lists else weights)
        else:
            priors.append([] if as_lists else row)
    return priors, values.tolist()


@dataclass
class _Pass:
    """An inference batch whose network pass has been handed to the device and whose
    replies wait for its outputs (SharedEvaluatorServer.submit and finish)."""
    requests: Sequence[tuple[Connection, tuple]]
    first: list[int]                 # Each request's first position; then the number of positions.
    actors: list[str | None]
    order: list[int]                 # The positions in the pass's order, grouped by network.
    lengths: list[int]               # Each of the pass's positions' option count.
    outputs: Any                     # joined_outputs: on the host, or on its way there with `event`.
    event: Any                       # A device event after the copy to the host, or None.
    batch: Any                       # The laid-out positions, whose host buffers the device may still read.
    version: str | None              # The networks' version that answers it.
    seconds: float                   # The server's time on it so far.


def _device_event(device: Any) -> Any:
    """An event recorded on the device's stream after the work handed to it so far;
    None on the CPU, where the work is done when it has been handed over."""
    import torch
    if device.type == "cpu":
        return None
    event = torch.mps.Event() if device.type == "mps" else torch.cuda.Event()
    event.record()
    return event


@dataclass
class ServerStats:
    requests: int = 0                # Requests answered, each of one position or of several.
    evaluations: int = 0             # Positions answered: network evaluations.
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
    # The same seconds by the inference batch's number of positions, as positions_per_pass counts them.
    seconds_per_pass: dict[int, float] = field(default_factory=dict)


class SharedEvaluatorServer:
    """Answers every game thread's requests, batching whatever is waiting."""

    def __init__(self, models: dict[str, Any], device: Any, connections: Sequence[Connection],
                 buffer_names: Sequence[str], runtime_policy: Any = None, *, compiled_forward: bool = False,
                 overlapped: bool | None = None) -> None:
        if set(models) != set(PLAYERS):
            raise ValueError("Provide one campaign model for Axis, Allies and Comintern")
        self.models, self.device = models, device
        # On a GPU, the next inference batch is laid out and handed to the device
        # while the last one computes, and its outputs are copied back without
        # waiting for the next one (serve); on the CPU a pass computes as it is
        # handed over, so batches go one after another.
        self.overlapped = getattr(device, "type", "cpu") in ("mps", "cuda") if overlapped is None else overlapped
        # One network's zone and position layers compiled for fixed numbers of states,
        # unless the layers as written are asked for (answer_as_written).
        self.compiled_forward = compiled_forward
        self.as_written = False
        # MPS graph-cache housekeeping after completed forwards (device_runtime).
        self.runtime_policy = runtime_policy
        # The game threads' pipes still open, and the buffer each thread writes its
        # zone inputs into. A new game process for the same game slots reuses them.
        self.connections: list[Connection] = []
        self.memories: dict[Connection, shared_memory.SharedMemory] = {}
        self._buffers: dict[str, shared_memory.SharedMemory] = {}
        self._stack = None
        self._computing: _Pass | None = None  # The inference batch handed to the device and not yet finished.
        # A release of the device's caches another thread asked for (release_between_steps),
        # and the event that tells it the release is done.
        self._release_asked = threading.Event()
        self._released = threading.Event()
        self._release_done = False
        self._serving = False  # Inside serve(), which does the releases.
        self.stats = ServerStats()
        # The version of `models`, named in a game thread's next reply whenever it
        # differs from the last one sent there. None names no version.
        self.network_version: str | None = None
        self._named: dict[Connection, str] = {}
        self.add(connections, buffer_names)

    def add(self, connections: Sequence[Connection], buffer_names: Sequence[str]) -> None:
        """Serve these game threads too, each writing its zone inputs into the named buffer."""
        for connection, name in zip(connections, buffer_names, strict=True):
            if name not in self._buffers:
                self._buffers[name] = shared_memory.SharedMemory(name=name)
            self.memories[connection] = self._buffers[name]
            self.connections.append(connection)

    def drop(self, connections: Sequence[Connection]) -> None:
        """Stop serving these game threads and close their pipes: their game process has ended."""
        for connection in connections:
            self._forget(connection)
            connection.close()

    def _forget(self, connection: Connection) -> None:
        if connection in self.connections:
            self.connections.remove(connection)
        self.memories.pop(connection, None)
        self._named.pop(connection, None)

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
        queue can need the lock, which deadlocks the process. An inference batch
        still computing is finished first, so that no wait for the device runs
        while the trainer works on it; batches then go one after another (serve)."""
        if as_written and self._computing is not None:
            computing, self._computing = self._computing, None
            self._finished(computing)
        if as_written != self.as_written:
            self.as_written = as_written
            self._stack = None  # The next inference batch builds the stack it needs.

    def release_between_steps(self, timeout: float = 60.0) -> bool:
        """Have the serving thread release the device's caches between two inference
        batches, and wait until it has: for a network update's trainer thread, between
        two of its training steps. While a network update trains beside self-play nothing
        else may release them, since on PyTorch 2.14 a wait for all the device's work from
        one thread while another hands it work aborts the process; this thread waits
        meanwhile, so only the serving thread uses the device. Without the releases the
        GPU keeps a compiled graph for every shape of minibatch, about 50 MB a training
        step at 256x16. Returns whether the release was done within `timeout` seconds."""
        if self.runtime_policy is None or not self._serving:
            return False
        self._release_done = False
        self._released.clear()
        self._release_asked.set()
        done = self._released.wait(timeout) and self._release_done
        self._release_asked.clear()
        return done

    def _release_if_asked(self) -> None:
        if not self._release_asked.is_set():
            return
        if self._computing is not None:
            computing, self._computing = self._computing, None
            self._finished(computing)
        self.runtime_policy.release_now()
        self._release_asked.clear()
        self._release_done = True
        self._released.set()

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

    def serve(self, keep_running: Callable[[], bool], *, until_closed: bool = True) -> None:
        """Answer requests until keep_running() is false or, with until_closed, every
        game thread has closed its pipe. Without until_closed, serving goes on while
        keep_running() holds, for the game threads that `add` brings.

        With `overlapped`, an inference batch is handed to the device and the one
        handed over before it is then finished: its outputs read and its replies
        sent while the device computes the newer one. Not while the networks run
        as written beside a network update (answer_as_written), when each batch is
        finished before the next is handed over.

        A pipe that ends, or whose reply cannot be sent, is no longer served: its
        game process has ended. Stopping closes the pipes still open, so a thread
        still sending or waiting for its reply gets EvaluatorClosed rather than
        waiting forever."""
        self._serving = True
        try:
            self._serve(keep_running, until_closed)
        finally:
            # A thread still waiting for a release goes on without one.
            self._serving = False
            self._release_done = False
            self._released.set()

    def _serve(self, keep_running: Callable[[], bool], until_closed: bool) -> None:
        while self.connections or not until_closed:
            self._release_if_asked()
            # keep_running may hand the networks to a network update (answer_as_written),
            # which finishes the inference batch still computing.
            if not keep_running():
                if self._computing is not None:
                    computing, self._computing = self._computing, None
                    self._finished(computing)
                for connection in self.connections:
                    connection.close()
                self.connections = []
                return
            before = time.perf_counter()
            if not self.connections:  # Until a new game process's threads are added.
                time.sleep(0.05)
                self.stats.idle_seconds += time.perf_counter() - before
                continue
            ready = wait(self.connections, timeout=0 if self._computing is not None else 0.05)
            received = time.perf_counter()
            if self._computing is None:
                self.stats.idle_seconds += received - before
            requests = []
            for connection in ready:
                try:
                    message = connection.recv_bytes()
                except (EOFError, OSError):  # OSError: the pipe ended within a message.
                    self._forget(connection)
                    connection.close()
                    continue
                requests.append((connection, read_positions(self.memories[connection].buf, message)))
            receiving = time.perf_counter() - received
            self.stats.receive_seconds += receiving
            overlapping = self.overlapped and not self.as_written
            if requests and overlapping:
                handed = self.submit(requests, overlapped=True)
                handed.seconds += receiving
                computing, self._computing = self._computing, handed
                if computing is not None:
                    self._finished(computing)
                continue
            if self._computing is not None:
                computing, self._computing = self._computing, None
                self._finished(computing)
            if requests:
                handed = self.submit(requests, overlapped=False)
                handed.seconds += receiving
                self._finished(handed)

    def _finished(self, handed: _Pass) -> None:
        positions = self.finish(handed)
        for spent, key in ((self.stats.seconds_per_round, len(handed.requests)),
                           (self.stats.seconds_per_pass, positions)):
            spent[key] = spent.get(key, 0.0) + handed.seconds

    def answer(self, requests: Sequence[tuple[Connection, tuple]]) -> int:
        """Answer requests of one position or of several (read_positions) in one
        network pass; returns the pass's positions."""
        return self.finish(self.submit(requests, overlapped=False))

    def submit(self, requests: Sequence[tuple[Connection, tuple]], *, overlapped: bool) -> _Pass:
        """Lay the requests' positions out and hand their network pass to the device.
        With `overlapped`, the outputs start on their way to the host behind the pass,
        so that finishing this batch waits for its own work only."""
        import torch
        started = time.perf_counter()
        stack = self.stack
        rows: list[list[int]] = [[] for _ in stack.models]
        items, actors, first = [], [], []
        for connection, (positions, layout, _) in requests:
            first.append(len(items))
            for actor, count, arrays in positions:
                readers = PLAYERS if actor is None else (actor,)
                if any(self.models[player].layout_version != layout for player in readers):
                    raise ValueError("A game sent a zone input of another layout")
                if count != len(arrays["action_source"]):
                    raise ValueError("A game's request and zone input list different options")
                # A chance position is rated by every network, once by each.
                for network in sorted({self._network_of[player] for player in readers}):
                    rows[network].append(len(items))
                items.append(arrays)
                actors.append(actor)
        first.append(len(items))
        # One pass for every alliance's positions, grouped by network.
        order = [row for network_rows in rows for row in network_rows]
        with torch.inference_mode():
            scores, lengths, raw, batch = forward_prepared(stack, [items[row] for row in order], self.device,
                                                           [len(network_rows) for network_rows in rows])
            outputs = joined_outputs(stack, scores, raw)
            event = None
            if overlapped:
                outputs = outputs.to("cpu", non_blocking=True)
                event = _device_event(self.device)
        return _Pass(requests, first, actors, order, lengths, outputs, event, batch, self.network_version,
                     time.perf_counter() - started)

    def finish(self, handed: _Pass) -> int:
        """Read a handed-over batch's outputs, waiting for the device, and send its
        replies; returns the pass's positions."""
        started = time.perf_counter()
        if handed.event is not None:
            handed.event.synchronize()
        with_host = handed.outputs.cpu().numpy()  # Already on the host when it went with an event.
        row_priors, row_values = host_priors(with_host, handed.lengths, as_lists=False)
        handed.batch = handed.outputs = None  # The device has read the batch and written the outputs.
        requests, first, actors = handed.requests, handed.first, handed.actors
        priors: list[Any] = [[] for _ in actors]
        chance: dict[int, list[list[float]]] = {}
        values: list[list[float] | None] = [None] * len(actors)
        for row, prior, value in zip(handed.order, row_priors, row_values, strict=True):
            if actors[row] is None:
                chance.setdefault(row, []).append(value)
            else:
                priors[row], values[row] = prior, value
        for row, found in chance.items():
            values[row] = [sum(value[i] for value in found) / len(found) for i in range(3)]
        sending = time.perf_counter()
        version = handed.version
        for index, (connection, (_, _, several)) in enumerate(requests):
            naming = version is not None and self._named.get(connection) != version
            named = version if naming else None
            start, end = first[index], first[index + 1]
            reply = (several_reply_bytes([(priors[row], values[row]) for row in range(start, end)], named) if several
                     else reply_bytes(priors[start], values[start], named))
            try:
                connection.send_bytes(reply)
            except OSError:  # Its game process ended after sending the request.
                self._forget(connection)
                connection.close()
                continue
            if naming:
                self._named[connection] = version
        sent = time.perf_counter()
        if self.runtime_policy is not None:
            self.runtime_policy.completed(1)
        ended = time.perf_counter()
        stats = self.stats
        stats.requests += len(requests)
        stats.evaluations += len(actors)
        stats.rounds += 1
        stats.requests_per_round[len(requests)] = stats.requests_per_round.get(len(requests), 0) + 1
        stats.passes += 1
        stats.positions_per_pass[len(handed.order)] = stats.positions_per_pass.get(len(handed.order), 0) + 1
        stats.reply_seconds += sent - sending
        # Laying out and handing over, reading the outputs and graph-cache housekeeping count as device work.
        stats.forward_seconds += handed.seconds + (sending - started) + (ended - sent)
        handed.seconds += ended - started
        return len(handed.order)

    def close(self) -> None:
        for memory in self._buffers.values():
            memory.close()


def raise_descriptor_limit(wanted: int) -> None:
    """Raise the soft open-file limit towards `wanted`, never lowering it."""
    if resource is None:
        return
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    wanted = wanted if hard == resource.RLIM_INFINITY else min(wanted, hard)
    if soft != resource.RLIM_INFINITY and soft < wanted:
        resource.setrlimit(resource.RLIMIT_NOFILE, (wanted, hard))


def game_process(play: Callable[[Any, RemoteEvaluator], dict[str, Any]], version: str,
                 slots: Sequence[int], connections: Sequence[Connection], buffer_names: Sequence[str],
                 tasks: Connection, results: Connection) -> None:
    """A game process: one thread per game slot, each taking games until the task pipe ends.

    `tasks` brings numbered tasks, (number, task), to one game slot at a time,
    and ends when the coordinator closes it or dies. Each game's record goes back
    through `results` with its task's number. `play(task, evaluator)` returns a
    game's record and handles its own failures.
    """
    taking, sending = threading.Lock(), threading.Lock()

    def next_task() -> Any:
        with taking:
            try:
                return tasks.recv()
            except (EOFError, OSError):  # No more games, or the coordinator has gone.
                return None

    def slot(index: int, connection: Connection, name: str) -> None:
        evaluator = RemoteEvaluator(connection, name, version)
        try:
            while (item := next_task()) is not None:
                number, task = item
                message = ForkingPickler.dumps((number, {**play(task, evaluator), "slot": index}))
                with sending:
                    try:
                        results.send_bytes(message)
                    except OSError:  # The coordinator has gone, and the task pipe ends with it.
                        pass
        finally:
            evaluator.close()

    threads = [threading.Thread(target=slot, args=arguments, name=f"campaign-game-{arguments[0]}", daemon=True)
               for arguments in zip(slots, connections, buffer_names)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


def _game_process_main(target: Callable[..., None], *arguments: Any) -> None:
    # The coordinator stops games by closing their pipes. A signal to the process
    # group (Ctrl+Break on Windows) must reach it, not end games under it.
    for number in (signal.SIGINT, signal.SIGTERM, *([signal.SIGBREAK] if hasattr(signal, "SIGBREAK") else [])):
        signal.signal(number, signal.SIG_IGN)
    # A crash in native code (an abort, a bad memory access) writes every game
    # thread's Python stack to standard error, which the training process shares.
    faulthandler.enable(all_threads=True)
    target(*arguments)


# The signals after which macOS writes a crash report: an abort, a bad memory access, a bad instruction.
CRASH_SIGNALS = {getattr(signal, name) for name in ("SIGABRT", "SIGSEGV", "SIGBUS", "SIGILL", "SIGFPE", "SIGTRAP")
                 if hasattr(signal, name)}


def keep_crash_report(pid: int, folder: str, *, wait_seconds: float = 120.0,
                      reports: Path | None = None) -> threading.Thread | None:
    """Copy macOS's crash report of the process `pid` into `folder`, as
    game-process-PID.ips, from a thread of its own. macOS writes the report
    to ~/Library/Logs/DiagnosticReports a few seconds after the process dies,
    under the program's name and the time, and keeps it there for a while; the
    report holds every thread's native stack. Elsewhere it does nothing.
    Returns the thread, or None."""
    if sys.platform != "darwin" and reports is None:
        return None
    reports = reports if reports is not None else Path.home() / "Library" / "Logs" / "DiagnosticReports"
    target = Path(folder) / f"game-process-{pid}.ips"

    def find() -> None:
        deadline = time.monotonic() + wait_seconds
        while time.monotonic() < deadline:
            try:
                candidates = sorted(reports.glob("*.ips"), key=lambda path: path.stat().st_mtime, reverse=True)[:20]
            except OSError:
                candidates = []
            for path in candidates:
                try:
                    _, body = path.read_text(encoding="utf-8").split("\n", 1)
                    if json.loads(body).get("pid") != pid:
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
                except (OSError, ValueError):
                    continue
                print(f"Crash report of game process {pid}: {target}", file=sys.stderr, flush=True)
                return
            time.sleep(2.0)
        print(f"No crash report of game process {pid} appeared in {reports}", file=sys.stderr, flush=True)

    thread = threading.Thread(target=find, name=f"crash-report-{pid}", daemon=True)
    thread.start()
    return thread


@dataclass(eq=False)
class _GameProcess:
    """The coordinator's side of one game process: its game threads' pipes to the
    inference server, its task and result pipes, and the games it was given and has
    not reported, by number, each with its task and the time it was given."""
    group: int  # Which game slots it plays: games_per_process of them from group * games_per_process.
    process: Any
    connections: list[Connection]
    tasks: Connection | None  # None once closed: it gets no more games.
    results: Connection
    playing: dict[int, tuple[Any, float]] = field(default_factory=dict)
    reported: int = 0
    results_ended: bool = False  # Everything it sent has been read.
    seen_ended: float | None = None  # When its exit was first seen, before its results ended.


def play_shared_games(target: Callable[..., None], tasks: Sequence[Any], *, processes: int, games_per_process: int,
                      models: dict[str, Any], device: Any, runtime_policy: Any = None,
                      keep_playing: Callable[[SharedEvaluatorServer, list[Any]], bool] = lambda *_: True,
                      exit_seconds: float = 20.0, stop_seconds: float = 20.0,
                      feed: Callable[[], Any] | None = None,
                      lost_game: Callable[[Any, str, float], Any] | None = None,
                      compiled_forward: bool = False,
                      crash_reports: str | None = None) -> tuple[list[Any], ServerStats]:
    """Play tasks in game processes, evaluating every waiting position here.

    `target(slots, connections, buffer_names, tasks, results)` is the game process,
    normally game_process with its first arguments bound. Each process plays
    `games_per_process` games at once, one per thread, and is given a game whenever
    one of its game slots has none, so a finished game's slot starts the next.
    `keep_playing(server, records)` runs between serving rounds, with the records
    that arrived and were not taken: it may take records off the front of
    `records` once it has used them, because each process's games are counted
    apart from the list. Returning false closes every pipe, ending the running
    games. Processes get `exit_seconds` to exit after the last game and
    `stop_seconds` after a stop. Returns the records not taken and the server's
    statistics.

    With `feed`, games keep coming instead: `tasks` must be empty, and `feed()`
    returns the next game's task, or None once no more games should start; serving
    goes on until `keep_playing` returns false or every game fed has reported. A
    `keep_playing` that runs games without end must take each record it has used,
    or `records` would keep every game played.

    With `lost_game`, a game process that dies is replaced: each game it was given
    and had not reported gets the record `lost_game(task, reason, seconds)`, where
    `seconds` have passed since that game was given, and a new process takes its
    game slots while the other processes play on. A process that dies before
    reporting any game ends the play with ValueError, as any death does without
    `lost_game`: a new process would most likely die the same way.

    With `crash_reports`, a game process that a crash signal ends has its crash
    report copied into that folder (keep_crash_report), before the play ends if
    the death ends it.
    """
    if feed is not None and tasks:
        raise ValueError("Give either a list of tasks or a feed, not both")
    context = multiprocessing.get_context("spawn")
    if os.environ.get("GWRL_GAME_PYTHON"):
        # Another interpreter, or a script that starts one, for the game processes
        # alone: one that loads an engine built with memory checks, for example,
        # while the inference server here keeps the ordinary build.
        context.set_executable(os.environ["GWRL_GAME_PYTHON"])
    slots = processes * games_per_process
    # A game slot holds two pipe ends and its buffer mapped twice, a process four
    # more pipe ends, and a shell's default limit of 256 stops at eight processes of six games.
    raise_descriptor_limit(6 * slots + 8 * processes + 64)
    memories = [shared_memory.SharedMemory(create=True, size=BUFFER_BYTES) for _ in range(slots)]
    names = [memory.name for memory in memories]
    listed, unsent, numbers = iter(tasks), [], itertools.count()
    games: list[_GameProcess] = []  # The process now playing each group of game slots.
    received: deque = deque()  # (process, (number, record)) as read, until collected.
    records, unread, abandoned = [], [], []
    fed_out, stopping, server = False, False, None
    finished = threading.Event()

    def start(group: int) -> _GameProcess:
        members = range(group * games_per_process, (group + 1) * games_per_process)
        pipes = [context.Pipe() for _ in members]
        task_reader, task_writer = context.Pipe(duplex=False)
        result_reader, result_writer = context.Pipe(duplex=False)
        process = context.Process(target=_game_process_main, daemon=True, args=(
            target, list(members), [child for _, child in pipes], [names[member] for member in members],
            task_reader, result_writer))
        try:
            process.start()
        except BaseException:
            for connection in (*(parent for parent, _ in pipes), task_writer, result_reader):
                connection.close()
            raise
        finally:
            # Only the process holds these ends now, so its pipes end when it does.
            for connection in (*(child for _, child in pipes), task_reader, result_writer):
                connection.close()
        return _GameProcess(group, process, [parent for parent, _ in pipes], task_writer, result_reader)

    def next_task() -> Any:
        if unsent:
            return unsent.pop(0)
        return feed() if feed is not None else next(listed, None)

    def close_tasks(game: _GameProcess) -> None:
        if game.tasks is not None:
            game.tasks.close()  # Its game slots end once their games are done.
            game.tasks = None

    def top_up() -> None:
        # A game for each free game slot, to the process with the fewest games first.
        nonlocal fed_out
        while not fed_out:
            game = min((game for game in games if game.tasks is not None), key=lambda game: len(game.playing),
                       default=None)
            if game is None or len(game.playing) >= games_per_process:
                return
            task = next_task()
            if task is None:
                fed_out = True
                for each in games:
                    close_tasks(each)
                return
            number = next(numbers)
            try:
                game.tasks.send((number, task))
            except OSError:  # The process has died; check_processes handles that.
                close_tasks(game)
                unsent.append(task)
                continue
            game.playing[number] = (task, time.monotonic())

    def receive() -> None:
        # Only this thread reads results. A record far outgrows a pipe's buffer, and a
        # process that dies while sending one leaves half a message, which ends its
        # pipe as its exit does.
        while not finished.is_set():
            reading = {game.results: game for game in games if not game.results_ended}
            if not reading:
                finished.wait(0.05)
                continue
            try:
                ready = wait(list(reading), timeout=0.2)
            except (OSError, ValueError):  # A pipe was closed meanwhile.
                continue
            for connection in ready:
                game = reading[connection]
                try:
                    received.append((game, connection.recv()))
                except (EOFError, OSError):
                    game.results_ended = True
                except Exception as error:
                    unread.append(error)
                    return

    def collect() -> None:
        while received:
            game, (number, record) = received.popleft()
            if game.playing.pop(number, None) is None:
                continue  # Its process was taken for dead, and the game counted as lost.
            game.reported += 1
            records.append(record)

    def replace(game: _GameProcess, code: int) -> None:
        try:
            how = f"signal {signal.Signals(-code).name}" if code < 0 else f"exit code {code}"
        except ValueError:
            how = f"exit code {code}"
        reason = f"GameProcessEnded: game process {game.process.pid} ended with {how}"
        report = None
        if crash_reports is not None and code < 0 and -code in CRASH_SIGNALS:
            report = keep_crash_report(game.process.pid, crash_reports)
        server.drop(game.connections)
        close_tasks(game)
        if game.results_ended:
            game.results.close()
        else:  # The receiver may still be reading it; it is closed at the end.
            abandoned.append(game.results)
        lost, game.playing = list(game.playing.values()), {}
        if lost_game is None or not game.reported:
            if report is not None:
                # The play, and the training process with it, ends here: the crash
                # report, which appears seconds after the death, is copied first.
                report.join()
            raise ValueError(f"A game process exited abnormally: {reason}")
        now = time.monotonic()
        records.extend(lost_game(task, reason, now - given) for task, given in lost)
        failed = f"{reason}; {len(lost)} unfinished {'game' if len(lost) == 1 else 'games'} failed"
        if fed_out:  # No more games for its game slots.
            games.remove(game)
            print(failed, file=sys.stderr, flush=True)
            return
        new = start(game.group)
        games[games.index(game)] = new
        server.add(new.connections, [names[member] for member in range(
            new.group * games_per_process, (new.group + 1) * games_per_process)])
        print(f"{failed}; game process {new.process.pid} took its {games_per_process} game slots",
              file=sys.stderr, flush=True)

    def check_processes(ended: list[_GameProcess]) -> None:
        # A process that exited while it had games, or while games were still to come.
        now = time.monotonic()
        for game in list(games):
            code = game.process.exitcode
            if code is None or (code == 0 and fed_out and not game.playing):
                continue  # Playing, or done.
            if game not in ended:
                game.seen_ended = now if game.seen_ended is None else game.seen_ended
                if now - game.seen_ended < 10:
                    continue  # What it sent before it ended may still be on the way.
            replace(game, code)

    def keep_running() -> bool:
        nonlocal stopping, fed_out
        if unread:
            raise unread[0]
        ended = [game for game in games if game.results_ended]  # All they sent is collected next.
        collect()
        if fed_out and not any(game.playing for game in games):
            return False  # Every game has reported, whatever else still holds a pipe open.
        # A stop comes first: its signal may have killed processes still starting.
        stopping = not keep_playing(server, records)
        if stopping:
            fed_out = True  # Running games end as their pipes close, and none start.
            for game in games:
                close_tasks(game)
            return False
        check_processes(ended)
        top_up()
        return True

    receiver = threading.Thread(target=receive, name="campaign-game-records", daemon=True)
    try:
        for group in range(processes):
            games.append(start(group))
        server = SharedEvaluatorServer(models, device, [connection for game in games for connection in game.connections],
                                       names, runtime_policy, compiled_forward=compiled_forward)
        receiver.start()
        top_up()
        server.serve(keep_running, until_closed=False)
        # The server closed every pipe still open, so a thread still waiting for
        # an evaluation ends its game. A process exits once it has sent its
        # records, which the receiver reads meanwhile.
        stop = time.monotonic() + (stop_seconds if stopping else exit_seconds)
        while time.monotonic() < stop and any(game.process.is_alive() for game in games):
            time.sleep(0.05)
        stragglers = [game.process for game in games if game.process.is_alive()]
        for process in stragglers:
            process.kill()
        for process in stragglers:
            process.join(timeout=1)  # Reaped, so their CPU time is counted.
        # What the processes sent before they ended may still be in their pipes.
        stop = time.monotonic() + 5
        while not all(game.results_ended for game in games) and not unread and time.monotonic() < stop:
            time.sleep(0.05)
        collect()
    finally:
        finished.set()
        for game in games:
            if game.process.is_alive():
                game.process.kill()
        if receiver.ident is not None:
            receiver.join(timeout=2)
        if server is not None:
            server.close()
        for memory in memories:
            memory.close()
            memory.unlink()
        for game in games:
            for connection in (*game.connections, game.tasks, game.results):
                if connection is not None:
                    connection.close()
        for connection in abandoned:
            connection.close()
    return records, server.stats
