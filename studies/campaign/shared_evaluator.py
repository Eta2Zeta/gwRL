"""Network evaluations for many self-play processes in one serving process.

Game processes keep the rules, the search and the network's input
preparation. For each position a search asks about, a game thread writes the
prepared arrays into its own shared-memory buffer and sends a short header
through its own pipe. The serving process merges every waiting position into
one batch per alliance model, evaluates it on its device and replies with the
priors and values. A thread waits for its reply before preparing its next
position, so its buffer is never overwritten while the server reads it. When
the server stops, it closes the pipes still open, and a thread waiting for a
reply raises EvaluatorClosed instead of waiting forever.

The forward pass repeats CampaignPolicyValueNet.forward_batch for positions
whose graphs, external references and policy factors arrive already laid out,
so the server does no per-graph Python work. Results match NeuralEvaluator's
up to floating-point summation order.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import multiprocessing
from multiprocessing import shared_memory
from multiprocessing.connection import Connection, wait
import queue
import resource
import signal
import threading
import time
from typing import Any, Callable, Sequence

import numpy as np

from studies.shared.multiplayer_mcts import Evaluation, PLAYERS, vector

BUFFER_BYTES = 8 * 1024 * 1024  # One prepared position; 11-round inputs take about 1 MB.
GRAPH_FIELDS = (("ids", "token_ids", np.int32), ("offsets", "token_offsets", np.int32), ("types", "types", np.int32),
                ("numbers", "numeric", np.float32), ("sources", "sources", np.int32),
                ("targets", "targets", np.int32), ("relations", "relations", np.int32))


def _graph_arrays(graph: Any, prefix: str) -> dict[str, np.ndarray]:
    arrays = graph.arrays()
    return {prefix + name: np.ascontiguousarray(arrays[source], dtype=dtype) for name, source, dtype in GRAPH_FIELDS}


def prepare_into(buffer: memoryview, env: Any, actions: Sequence[Any],
                 buckets: int) -> tuple[str, list[tuple[str, str, tuple, int]], Any]:
    """Write a position's complete network input into `buffer`.

    Returns its context key, the header read_arrays reads it by, and its context
    graph. The legal menu's action graphs are joined into one block, as the
    model's encoder layout joins them; their node indices and external references
    stay local to the block and to the position's own observation.
    """
    from .features import make_numeric_input
    item = make_numeric_input(env, tuple(actions), buckets)
    if not isinstance(item, dict) or "packed_graph" not in item:
        raise ValueError("The shared evaluator needs native numerical inputs")
    packed = item["packed_graph"]
    header = packed["observation"].write_evaluation(buffer, packed["context"], packed["actions"],
                                                    packed["action_factors"])
    return item["context_key"], header, packed["context"]


def prepare(env: Any, actions: Sequence[Any], buckets: int) -> tuple[str, dict[str, np.ndarray], Any]:
    """prepare_into for a caller that keeps the arrays instead of sending them."""
    buffer = memoryview(bytearray(8 * 1024 * 1024))
    key, header, context = prepare_into(buffer, env, actions, buckets)
    return key, {name: array.copy() for name, array in read_arrays(buffer, header).items()}, context


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

    def __init__(self, connection: Connection, buffer_name: str, buckets: int, version: str) -> None:
        self.connection, self.buckets, self.version = connection, buckets, version
        self.memory = shared_memory.SharedMemory(name=buffer_name)
        self.sent_contexts: set[str] = set()
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
        key, header, context = prepare_into(self.memory.buf, env, actions, self.buckets)
        context_arrays = None
        if key not in self.sent_contexts:
            context_arrays = {**_graph_arrays(context, "ctx_"), "ctx_nodes": np.asarray([context.node_count])}
        sent = time.perf_counter()
        try:
            self.connection.send((actor, key, len(actions), header, context_arrays))
            priors, values = self.connection.recv()
        except (EOFError, OSError) as error:  # BrokenPipeError is an OSError.
            raise EvaluatorClosed("The shared evaluator closed this game thread's pipe") from error
        # Only an answered request shows that the server holds the context.
        self.sent_contexts.add(key)
        self.stats.requests += 1
        self.stats.prepare_seconds += sent - started
        self.stats.wait_seconds += time.perf_counter() - sent
        if len(priors) != len(actions):
            raise ValueError("The shared evaluator returned a different legal menu")
        return Evaluation(priors, vector(values))

    def close(self) -> None:
        self.memory.close()
        self.connection.close()


def _encode(encoder: Any, layout: dict[str, Any], rows: int, external: Any) -> tuple[Any, Any]:
    """_GraphEncoder.forward on a layout built outside it."""
    import torch
    encoded = encoder.tokens(layout["ids"], layout["offsets"]) + encoder.types(layout["types"])
    encoded = encoder.input_norm(encoded + encoder.numbers(layout["numbers"]))
    for message, update in zip(encoder.messages, encoder.updates, strict=True):
        bank = torch.cat((encoded, external)) if external is not None else encoded
        gathered = bank.index_select(0, layout["sources"]) + encoder.relations(layout["relations"])
        aggregate = torch.zeros_like(encoded)
        aggregate.index_add_(0, layout["targets"], message(gathered))
        encoded = encoded + update(torch.cat((encoded, aggregate / layout["degree"]), dim=1))
    summed = encoded.new_zeros((rows, encoded.shape[1]))
    summed.index_add_(0, layout["owners"], encoded)
    maximum = encoded.new_full(summed.shape, -torch.inf)
    maximum.scatter_reduce_(0, layout["owners"].unsqueeze(1).expand_as(encoded), encoded, reduce="amax",
                            include_self=True)
    pooled = encoder.pool(torch.cat((summed / layout["counts"], maximum, layout["counts"].log1p()), dim=1))
    return encoded, pooled


class _Transfer:
    """Host arrays sent to the device as one integer and one float buffer.

    Each separate host-to-device copy costs a fixed overhead on MPS, larger
    than moving the data itself, so a batch's index arrays travel together.
    """

    def __init__(self) -> None:
        self.integers: list[tuple[str, np.ndarray]] = []
        self.floats: list[tuple[str, np.ndarray]] = []

    def integer(self, name: str, values: Any) -> None:
        self.integers.append((name, np.asarray(values, dtype=np.int64).ravel()))

    def real(self, name: str, values: Any) -> None:
        values = np.asarray(values, dtype=np.float32)
        self.floats.append((name, values))

    def send(self, device: Any) -> dict[str, Any]:
        """Device views of every array. A blocking copy would first wait for the
        device's queued work; the host buffers stay referenced under "_host"
        until the caller drops the views, after the copies have run."""
        import torch
        out: dict[str, Any] = {"_host": []}
        for parts, dtype in ((self.integers, np.int64), (self.floats, np.float32)):
            if not parts:
                continue
            host = torch.from_numpy(np.concatenate([values.ravel() for _, values in parts]).astype(dtype, copy=False))
            out["_host"].append(host)
            joined = host.to(device, non_blocking=True)
            offset = 0
            for name, values in parts:
                out[name] = joined[offset:offset + values.size].view(values.shape)
                offset += values.size
        return out


def _layout(graphs: Sequence[dict[str, np.ndarray]], prefix: str, external: Sequence[tuple[np.ndarray, np.ndarray]],
            node_counts: np.ndarray, transfer: _Transfer, name: str) -> None:
    """Join laid-out graph blocks, adding external edges after each block's own.

    `external` gives each block's (destination, joined bank index) arrays; the
    caller has already offset the bank indices.
    """
    from .features import EXTERNAL_REFERENCE
    nodes = np.array([len(graph[prefix + "offsets"]) - 1 for graph in graphs], dtype=np.int64)
    node_starts = np.concatenate(([0], np.cumsum(nodes)[:-1]))
    token_starts = np.concatenate(([0], np.cumsum([len(graph[prefix + "ids"]) for graph in graphs])[:-1]))
    total = int(nodes.sum())
    ext_total = int(sum(len(dest) for dest, _ in external))
    sources = np.concatenate([graph[prefix + "sources"] + start for graph, start in zip(graphs, node_starts)]
                             + [total + np.arange(ext_total, dtype=np.int64)])
    targets = np.concatenate([graph[prefix + "targets"] + start for graph, start in zip(graphs, node_starts)]
                             + [dest + start for (dest, _), start in zip(external, node_starts)])
    relations = np.concatenate([graph[prefix + "relations"] for graph in graphs]
                               + [np.full(ext_total, EXTERNAL_REFERENCE, dtype=np.int32)])
    offsets = np.concatenate([graph[prefix + "offsets"][:-1] + start for graph, start in zip(graphs, token_starts)]
                             + [[sum(len(graph[prefix + "ids"]) for graph in graphs)]])
    for field, values in (("ids", np.concatenate([graph[prefix + "ids"] for graph in graphs])), ("offsets", offsets),
                          ("types", np.concatenate([graph[prefix + "types"] for graph in graphs])),
                          ("sources", sources), ("targets", targets), ("relations", relations),
                          ("owners", np.repeat(np.arange(len(node_counts)), node_counts)),
                          ("external_index", np.concatenate([index for _, index in external]) if external else ())):
        transfer.integer(f"{name}.{field}", values)
    transfer.real(f"{name}.numbers", np.concatenate([graph[prefix + "numbers"] for graph in graphs]))
    transfer.real(f"{name}.degree", np.maximum(np.bincount(targets, minlength=total), 1)[:, None])
    transfer.real(f"{name}.counts", np.asarray(node_counts)[:, None])


def _fields(device_arrays: dict[str, Any], name: str) -> dict[str, Any]:
    prefix = name + "."
    return {key[len(prefix):]: value for key, value in device_arrays.items() if key.startswith(prefix)}


class _Contexts:
    """Each context graph's arrays, and each model's encoding of it, by key."""

    def __init__(self) -> None:
        self.arrays: dict[str, dict[str, np.ndarray]] = {}
        self.encoded: dict[tuple[int, str], tuple[Any, Any]] = {}

    def encoding(self, model: Any, key: str, device: Any) -> tuple[Any, Any]:
        found = self.encoded.get((id(model), key))
        if found is None:
            arrays = self.arrays[key]
            transfer = _Transfer()
            _layout([arrays], "ctx_", [(np.zeros(0, np.int32), np.zeros(0, np.int32))],
                    np.asarray([int(arrays["ctx_nodes"][0])]), transfer, "ctx")
            device_arrays = transfer.send(device)
            found = self.encoded[(id(model), key)] = _encode(model.encoder, _fields(device_arrays, "ctx"), 1, None)
            found[1].cpu()  # Once per model: the copies' host buffers may go now.
        return found


def forward_prepared(model: Any, items: Sequence[tuple[str, dict[str, np.ndarray]]], contexts: _Contexts,
                     device: Any) -> tuple[Any, list[int], Any, list[Any]]:
    """CampaignPolicyValueNet.forward_batch for prepared positions.

    Returns every legal action's logit in position order, each position's action
    count, the raw value rows, and the host buffers the device copies read,
    which must stay alive until the outputs are collected. All host arrays reach
    the device in two copies.
    """
    import torch
    keys = list(dict.fromkeys(key for key, _ in items))
    static = [contexts.encoding(model, key, device) for key in keys]
    bank_offsets = np.concatenate(([0], np.cumsum([nodes.shape[0] for nodes, _ in static])[:-1]))
    context_row = {key: index for index, key in enumerate(keys)}
    positions = [arrays for _, arrays in items]
    rows = len(positions)
    lengths = [len(arrays["act_nodes"]) for arrays in positions]
    obs_nodes = np.array([len(arrays["obs_offsets"]) - 1 for arrays in positions], dtype=np.int64)
    transfer = _Transfer()
    _layout(positions, "obs_", [(arrays["obs_ref_dest"], arrays["obs_ref_index"] + bank_offsets[context_row[key]])
                                for key, arrays in items], obs_nodes, transfer, "obs")
    transfer.integer("context_rows", [context_row[key] for key, _ in items])
    if sum(lengths):
        # Action graphs read their own position's observation nodes, which follow
        # one another in the encoder output, then the context nodes after them.
        obs_starts = np.concatenate(([0], np.cumsum(obs_nodes)[:-1]))
        dynamic_total = int(obs_nodes.sum())
        act_external = [(np.concatenate((arrays["act_obs_dest"], arrays["act_ctx_dest"])),
                         np.concatenate((arrays["act_obs_index"] + start,
                                         arrays["act_ctx_index"] + dynamic_total + bank_offsets[context_row[key]])))
                        for (key, arrays), start in zip(items, obs_starts)]
        graph_nodes = np.concatenate([arrays["act_nodes"] for arrays in positions]).astype(np.int64)
        _layout(positions, "act_", act_external, graph_nodes, transfer, "act")
        transfer.integer("policy_owners", np.repeat(np.arange(rows), lengths))
        factor_sizes = _factor_transfer(positions, lengths, transfer) if model.config.policy_factorization else None
    device_arrays = transfer.send(device)
    context_bank = static[0][0] if len(static) == 1 else torch.cat([nodes for nodes, _ in static])
    observation = _fields(device_arrays, "obs")
    dynamic_nodes, dynamic_pooled = _encode(model.encoder, observation, rows,
                                            context_bank.index_select(0, observation["external_index"]))
    context_pooled = (torch.cat([pooled for _, pooled in static]) if len(static) > 1 else static[0][1])
    states = model.state_encoder(torch.cat((dynamic_pooled, context_pooled.index_select(0, device_arrays["context_rows"])),
                                           dim=1))
    values = model.value_head(states)
    if not sum(lengths):
        return values.new_empty((0,)), lengths, values, device_arrays["_host"]
    actions = _fields(device_arrays, "act")
    bank = torch.cat((dynamic_nodes, context_bank))
    _, action_pooled = _encode(model.encoder, actions, len(graph_nodes), bank.index_select(0, actions["external_index"]))
    scores = model.policy_head(torch.cat((states.index_select(0, device_arrays["policy_owners"]), action_pooled),
                                         dim=1)).squeeze(1)
    if factor_sizes is not None:
        scores = _factored(model, states, action_pooled, scores, device_arrays, factor_sizes)
    return scores, lengths, values, device_arrays["_host"]


def evaluate_prepared(model: Any, items: Sequence[tuple[str, dict[str, np.ndarray]]], contexts: _Contexts,
                      device: Any) -> tuple[list[list[float]], list[list[float]]]:
    """Each position's priors and raw values in NeuralEvaluator's units.

    One device-to-host copy carries every logit and value; each position's
    softmax then runs on the host, where a short menu costs microseconds rather
    than one accelerator dispatch per position.
    """
    return collect(model, *forward_prepared(model, items, contexts, device))


def collect(model: Any, scores: Any, lengths: Sequence[int], raw: Any,
            host_buffers: Sequence[Any] = ()) -> tuple[list[list[float]], list[list[float]]]:
    """Host priors and raw values from forward_prepared's device outputs.

    Reading them back waits for the device, after which `host_buffers` may go."""
    import torch
    host = torch.cat((scores, (raw * model.config.value_scale).reshape(-1))).cpu().numpy().astype(np.float64)
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


def _factor_transfer(positions: Sequence[dict[str, np.ndarray]], lengths: Sequence[int], transfer: _Transfer) -> list[int]:
    """The batched factor levels of CampaignPolicyValueNet._batched_factor_layout."""
    present = [(row, arrays) for row, (arrays, count) in enumerate(zip(positions, lengths)) if count]
    sizes = []
    for level in range(1, 5):
        owners, counts, parents, state_rows = [], [], [], []
        group_offset = parent_offset = 0
        for row, arrays in present:
            group_counts = arrays[f"f{level}_counts"]
            owners.append(arrays[f"f{level}_owners"] + group_offset)
            counts.append(group_counts)
            parents.append(arrays[f"f{level}_parents"] + parent_offset)
            state_rows.append(np.full(len(group_counts), row))
            group_offset += len(group_counts)
            parent_offset += int(arrays["f_parent_counts"][level - 1])
        for field, values in (("owners", owners), ("parents", parents), ("state_rows", state_rows)):
            transfer.integer(f"f{level}.{field}", np.concatenate(values))
        transfer.real(f"f{level}.counts", np.concatenate(counts)[:, None])
        sizes += [group_offset, parent_offset]
    return sizes  # Group and parent counts per level, kept on the host for shapes.


def _factored(model: Any, states: Any, latent: Any, scores: Any, device_arrays: dict[str, Any],
              sizes: Sequence[int]) -> Any:
    """CampaignPolicyValueNet._factored_logits_batch on prepared factor levels."""
    import torch
    joint = torch.zeros_like(scores)
    for level, head in zip(range(1, 5), model.factor_heads, strict=True):
        fields = _fields(device_arrays, f"f{level}")
        groups, parent_count = sizes[2 * level - 2], sizes[2 * level - 1]
        means = latent.new_zeros((groups, latent.shape[1]))
        means.index_add_(0, fields["owners"], latent)
        group_scores = head(torch.cat((states.index_select(0, fields["state_rows"]), means / fields["counts"]),
                                      dim=1)).squeeze(1)
        conditional = model._conditional_log_softmax(group_scores, fields["parents"], parent_count)
        joint = joint + conditional.index_select(0, fields["owners"])
    return joint + model._conditional_log_softmax(scores, fields["owners"], groups)


@dataclass
class ServerStats:
    requests: int = 0
    rounds: int = 0                  # Serving rounds: the waiting requests answered together.
    requests_per_round: dict[int, int] = field(default_factory=dict)
    forwards: int = 0                # Model forwards: one per alliance model with positions in a round.
    positions_per_forward: dict[int, int] = field(default_factory=dict)
    receive_seconds: float = 0.0     # Reading requests from the ready pipes.
    forward_seconds: float = 0.0     # Merge, transfer, forward and host outputs.
    reply_seconds: float = 0.0       # Sending priors and values back.
    idle_seconds: float = 0.0


class SharedEvaluatorServer:
    """Answers every game thread's requests, batching whatever is waiting."""

    def __init__(self, models: dict[str, Any], device: Any, connections: Sequence[Connection],
                 buffer_names: Sequence[str], runtime_policy: Any = None) -> None:
        if set(models) != set(PLAYERS):
            raise ValueError("Provide one campaign model for Axis, Allies and Comintern")
        self.models, self.device = models, device
        # MPS graph-cache housekeeping after completed forwards (device_runtime).
        self.runtime_policy = runtime_policy
        self.connections = list(connections)
        self.memories = {connection: shared_memory.SharedMemory(name=name)
                         for connection, name in zip(connections, buffer_names, strict=True)}
        self.contexts = _Contexts()
        self.stats = ServerStats()

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

    def answer(self, requests: Sequence[tuple[Connection, tuple]]) -> None:
        import torch
        started = time.perf_counter()
        groups: dict[str, list[int]] = {player: [] for player in PLAYERS}
        items = []
        for row, (connection, (actor, key, count, header, context_arrays)) in enumerate(requests):
            if context_arrays is not None and key not in self.contexts.arrays:
                self.contexts.arrays[key] = context_arrays
            items.append((key, read_arrays(self.memories[connection].buf, header)))
            for player in PLAYERS if actor is None else (actor,):
                groups[player].append(row)
        priors: list[list[float]] = [[] for _ in requests]
        chance: dict[int, list[list[float]]] = {}
        values: list[list[float] | None] = [None] * len(requests)
        with torch.inference_mode():
            # Queue every model's work before reading any result back, so the
            # host lays out one model's batch while the device runs another's.
            launched = [(player, rows, forward_prepared(self.models[player], [items[row] for row in rows],
                                                        self.contexts, self.device))
                        for player, rows in groups.items() if rows]
            for player, rows, outputs in launched:
                row_priors, row_values = collect(self.models[player], *outputs)
                for row, prior, value in zip(rows, row_priors, row_values, strict=True):
                    if requests[row][1][0] is None:
                        chance.setdefault(row, []).append(value)
                    else:
                        priors[row], values[row] = prior, value
        for row, rows in chance.items():
            values[row] = [sum(value[i] for value in rows) / len(PLAYERS) for i in range(3)]
        sending = time.perf_counter()
        for (connection, _), row_priors, value in zip(requests, priors, values, strict=True):
            connection.send((row_priors, value))
        sent = time.perf_counter()
        if self.runtime_policy is not None:
            self.runtime_policy.completed(len(launched))
        stats = self.stats
        stats.requests += len(requests)
        stats.rounds += 1
        stats.requests_per_round[len(requests)] = stats.requests_per_round.get(len(requests), 0) + 1
        stats.forwards += len(launched)
        for _, rows, _ in launched:
            stats.positions_per_forward[len(rows)] = stats.positions_per_forward.get(len(rows), 0) + 1
        stats.reply_seconds += sent - sending
        # Graph-cache housekeeping after the replies counts as device work.
        stats.forward_seconds += (sending - started) + (time.perf_counter() - sent)

    def close(self) -> None:
        for memory in self.memories.values():
            memory.close()


def raise_descriptor_limit(wanted: int) -> None:
    """Raise the soft open-file limit towards `wanted`, never lowering it."""
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


def game_process(play: Callable[[Any, RemoteEvaluator], dict[str, Any]], buckets: int, version: str,
                 slots: Sequence[int], connections: Sequence[Connection], buffer_names: Sequence[str],
                 tasks: Any, results: Any) -> None:
    """A game process: one thread per game slot, each taking tasks until its stop marker.

    `play(task, evaluator)` returns a game's record and handles its own failures.
    """
    # The coordinator stops games by closing their pipes. A signal to the process
    # group must reach it, not end games under it.
    for number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(number, signal.SIG_IGN)

    def slot(index: int, connection: Connection, name: str) -> None:
        evaluator = RemoteEvaluator(connection, name, buckets, version)
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


def play_shared_games(target: Callable[..., None], tasks: Sequence[Any], *, processes: int, games_per_process: int,
                      models: dict[str, Any], device: Any, runtime_policy: Any = None,
                      keep_playing: Callable[[SharedEvaluatorServer, list[Any]], bool] = lambda *_: True,
                      exit_seconds: float = 20.0, stop_seconds: float = 20.0) -> tuple[list[Any], ServerStats]:
    """Play tasks in game processes, evaluating every waiting position here.

    `target(slots, connections, buffer_names, tasks, results)` is the game process,
    normally game_process with its first arguments bound. Each process plays
    `games_per_process` games at once, one per thread, taking tasks from one queue,
    so a finished game's slot starts the next. `keep_playing(server, records)` runs
    between serving rounds; returning false closes every pipe, ending the running
    games. Processes get `exit_seconds` to exit after the last game and
    `stop_seconds` after a stop. Returns the records that arrived and the server's
    statistics.
    """
    context = multiprocessing.get_context("spawn")
    slots = processes * games_per_process
    # A slot holds two pipe ends and its buffer mapped twice, and a shell's default
    # limit of 256 stops at eight processes of six games.
    raise_descriptor_limit(6 * slots + 64)
    pipes = [context.Pipe() for _ in range(slots)]
    memories = [shared_memory.SharedMemory(create=True, size=BUFFER_BYTES) for _ in range(slots)]
    waiting, results = context.Queue(), context.Queue()
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
        for index in range(processes):
            members = range(index * games_per_process, (index + 1) * games_per_process)
            process = context.Process(target=target, daemon=True, args=(
                list(members), [pipes[member][1] for member in members], [memories[member].name for member in members],
                waiting, results))
            process.start()
            spawned.append(process)
        for _, child in pipes:
            child.close()
        server = SharedEvaluatorServer(models, device, [parent for parent, _ in pipes],
                                       [memory.name for memory in memories], runtime_policy)

        def keep_running() -> bool:
            nonlocal stopping
            if unread:
                raise unread[0]
            # Every game has reported, whatever else still holds a pipe open.
            if len(records) >= len(tasks):
                return False
            # A stop comes first: its signal may have killed processes still starting.
            stopping = not keep_playing(server, records)
            if stopping:
                return False
            if not all(process.is_alive() or process.exitcode == 0 for process in spawned):
                raise ValueError("A game process exited abnormally")
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
        while clean and len(records) < len(tasks) and time.monotonic() < stop:
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
