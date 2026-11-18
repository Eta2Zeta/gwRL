# Compiling one network's zone and position layers — 18 November 2026

Compiled whole and as it was written, the forward pass had never been faster
([record](coordinator_rounds_2026_11_17.md#compiling)): PyTorch compiled it again
for each new mix of states, and on the GPU it wrote code with atomic additions
that did not build. With one network serving all three alliances
([Q-010](../../questions.md#answered)), a forward pass can be written for
compiling. This record measures two changes on the 853 inference batches saved
on 17 November:

- **A new layout of the zone and position layers**, used everywhere. Each state's
  zone vectors stay together, an array of states by 37 zones by the width, and
  each message-passing layer reads the map's borders as fixed indices along the
  zones.
- **Those layers compiled** for fixed numbers of states, with
  `--compiled-forward`, for the inference server only.

The [evidence file](compiled_forward_2026_11_18.json) holds every value.

- **The new layout** gives exactly the earlier outputs on one core, and on the
  GPU outputs within 0.000003. Its speed is within a few percent of the
  earlier layout's, about as far apart as two timings of the same code.
- **The compiled layers** took 6% to 9% less time per inference batch on the
  Mac's GPU than the same layers as written, at 256×8 and 512×16 with about 9
  states, and 21% to 24% less with about 60. At 64×2 they were 9% slower on the
  GPU and about as fast on one core.
- **Compiling** took 17 to 36 seconds on the GPU and about a minute on one core
  with PyTorch's compile cache empty, and seconds with the cache.

## How it was measured

- **Code.** `tools/compare_forward_passes.py`, added with this record, runs
  an earlier forward pass, loaded from a copy of its `neural.py`, and the
  checkout's in turn in one process, on the same inference batches; the first
  run of each includes its warm-up, and for compiled layers their compiling, and
  the tables give the best of the later runs. The new layout was compared with
  commit `27e67c4`, four runs each. The compiled layers were compared with the
  same layers as written, each in a process of its own (the tool's earlier side
  a copy of the checkout's `neural.py`), five runs each, in the order written,
  compiled, compiled, written, and each is the mean of its two processes: within
  one process, compiled code slowed the GPU's other work (below). PyTorch 2.14.0
  on the Mac's Apple M4 Max, one tensor thread, `MallocNanoZone` unset.

```
tmp/gpu-mps-env/bin/python tools/compare_forward_passes.py --old-root OLD --rounds ROUNDS --device mps --hidden-dim 256 --message-layers 8 --merge 8 --limit 300 --repeat 4
```

`OLD` is `git archive 27e67c4` unpacked, with the compiled engine module copied
in. For the compiled layers, `--old-root` names a folder holding only a copy of
the checkout's `studies/campaign/neural.py`, with `--repeat 5`, once with
`--compiled` and once without.

- **Inference batches.** The 853 that `tools/profile_coordinator.py` saved from
  a training iteration of the Mac profile on 17 November
  ([record](coordinator_rounds_2026_11_17.md#setup)), as saved and merged 3 or 8
  at a time into one inference batch, the first 300 after merging: 9.1 states an
  inference batch as saved, 22.3 merged 3 and 59.7 merged 8.
- **Networks.** One network served every state, with the same weights on both
  sides: a fresh network whose three column tables were filled with random
  numbers, since a fresh network's rows are zero, at 64×2, 256×8 and 512×16.
- **Compile times** come from the first run of the compiled layers with
  `TORCHINDUCTOR_CACHE_DIR` set to an empty folder, and two runs in all.
- **The Mac's other work** kept the load average at about 3 during the final
  runs.

## What changed in the forward pass

- **The layout** (`_state_layers` in `studies/campaign/neural.py`). Before, the
  forward pass laid all states' zones out as one long list of rows, and each
  message-passing layer built, for its number of states, the rows each border
  reads and writes. Now a message-passing layer gathers each border's source zone
  with the map's 160 fixed indices along the zone axis, adds the messages into
  their target zones along that axis (`index_add_`) and divides by the zone's
  number of incoming borders, the same additions in the same order as before;
  the position vector is placed beside each zone by `expand` instead of
  `repeat_interleave`.
- **The compiled layers** (`compiled_state_layers`). From the zone vectors to
  the state vectors and values, compiled by `torch.compile` for fixed numbers of
  states, the *state buckets* 1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24, 32 and so on
  to 512, each at most a third more than the one below. An inference batch is
  padded with empty states to its bucket; their zone and position lookups are
  empty, so their vectors start at zero, and their outputs are dropped. On a GPU
  `index_add_` adds with atomic additions, which the compiler could not build
  there, so the compiled layers average each zone's messages with a fixed matrix
  of 37 rows and 160 columns instead, holding 1 divided by the zone's number of
  incoming borders where a border ends at the zone. The lookups, the actions'
  vectors and the policy readout run as written. One compiled function serves
  every network of a size, and reads the weights at each call, so new weights
  copied in after a network update need no new compiling.

## PyTorch calls

Counted as every operation that reaches PyTorch's dispatcher in one forward pass
of 8 decisions, after a first, uncounted one:

| Network | One network, one core | One network, GPU | A network for each alliance, one core | A network for each alliance, GPU |
| --- | ---: | ---: | ---: | ---: |
| 64×2 | 138 | 162 | 247 | 272 |
| 256×8 | 264 | 288 | 493 | 518 |
| 512×16 | 432 | 456 | 821 | 846 |

A message-passing layer is now 21 PyTorch calls with one network: 3 `linear`, 3
`gelu`, 3 `add`, 2 `layer_norm`, 2 `cat`, and one each of `select`,
`index_select`, `new_zeros`, `index_add_`, `div`, `unsqueeze`, `expand` and
`mean`. With a network for each alliance it is 41. Before, a forward pass was 146
PyTorch calls at 64×2 for states of one alliance and 258 for states of all
three, and a message-passing layer 20 and 42
([record](pass_calls_2026_11_17.md#how-many-calls-a-pass-makes)).

## Speed

**The new layout against the forward pass of `27e67c4`**, in one process:

| Device | Network | States per inference batch | Before | New layout | Change |
| --- | --- | ---: | ---: | ---: | ---: |
| One core | 64×2 | 9.1 | 1,131 µs | 1,102 µs | −2.5% |
| One core | 64×2 | 22.3 | 2,505 µs | 2,664 µs | +6.3% |
| GPU | 64×2 | 9.1 | 2,157 µs | 2,166 µs | +0.4% |
| GPU | 64×2 | 59.7 | 3,500 µs | 3,627 µs | +3.6% |
| GPU | 256×8 | 9.1 | 4,138 µs | 4,053 µs | −2.0% |
| GPU | 256×8 | 59.7 | 8,968 µs | 9,151 µs | +2.0% |
| GPU | 512×16 | 9.1 | 7,915 µs | 7,976 µs | +0.8% |
| GPU | 512×16 | 59.7 | 27,601 µs | 28,274 µs | +2.4% |

**The compiled layers against the same layers as written**, each in a process
of its own:

| Device | Network | States per inference batch | As written | Compiled | Change |
| --- | --- | ---: | ---: | ---: | ---: |
| One core | 64×2 | 9.1 | 1,229 µs | 1,194 µs | −2.8% |
| GPU | 64×2 | 9.1 | 2,251 µs | 2,445 µs | +8.7% |
| GPU | 256×8 | 9.1 | 3,825 µs | 3,584 µs | −6.3% |
| GPU | 512×16 | 9.1 | 8,035 µs | 7,313 µs | −9.0% |
| GPU | 256×8 | 59.7 | 9,378 µs | 7,442 µs | −20.6% |
| GPU | 512×16 | 59.7 | 29,099 µs | 22,056 µs | −24.2% |

- **The new layout's speed is the earlier one's** within the spread of these
  measurements. Two runs of the tool on the same code differed by 0.1%, but runs
  an hour apart, and other ways of timing the same layouts, put the one-core
  case with 22.3 states anywhere between 5% faster and 7.5% slower.
- **The compiled layers pay for the larger networks on the GPU**: 6% to 9% less
  time with about 9 states and 21% to 24% with about 60, where the zone and
  position layers are most of an inference batch's time.
- **At 64×2 they do not pay**: 9% slower on the GPU, and on one core 3% faster,
  within the spread. The layers they compile are a smaller part of an inference
  batch's time there, and padding adds empty states. With a prototype of the
  same compiled layers, timed stage by stage with a device synchronization after
  each, the zone and position layers took 42% of an inference batch's time as
  saved on one core at 64×2, 26% on the GPU at 64×2, and 72% on the GPU at
  512×16 merged 8. The rest, the same in every version, was laying the inference
  batch out on the host (5% to 17%), the lookups, the actions' vectors and the
  policy head (14% at 64×2 on one core) and the policy readout (17% and 20% at
  64×2, 8% at 512×16).
- **Compiled code slowed the GPU's other work in the same process.** The layers
  as written, run beside compiled ones in one process, took 12% longer at 64×2
  than in a process of their own, and 2% to 3% longer at 256×8 and 512×16 with
  about 9 states, so comparisons within one process overstated the compiled
  layers' gain there: 5.7%, 9.2% and 10.9% instead of the slowing at 64×2 and
  6.3% and 9.0%. With about 60 states the two ways agreed within 3%. The forward
  pass of `27e67c4`, compared with the compiled layers in one process, was
  slowed the same way; the evidence file keeps those runs. Why the GPU's work
  slows is not measured.

## Averaging the messages

Before choosing, three ways of averaging each zone's incoming messages were
timed alone: adding them in (`index_add_`), the fixed matrix, and a gather of
each zone's incoming borders padded to the largest in-degree, 8.

- **Alone, the fixed matrix was the fastest on the GPU**: 32 to 99 µs against 32
  to 289 µs for adding in, at widths 64 to 512 and 8 or 64 states, though it does
  5,920 multiply-adds per state and number of the width against 160 additions.
  On one core the two were about equal. The padded gather was the slowest
  everywhere.
- **In whole forward passes as written the fixed matrix was 5% to 10% slower on
  the GPU** than the earlier forward pass: eight ways of writing the layers were
  tried at 64×2 and 256×8 as saved, and the four with the matrix were all slower
  by that much, while the layout chosen, adding in, came within 1%, 1.0% and
  0.6% slower. So the layers as written add in, and only the compiled layers use
  the matrix.

## Compiling time

| Device | Network | Inference batches | Time to compile, cache empty |
| --- | --- | --- | ---: |
| One core | 64×2 | 300 as saved | about 58 s |
| GPU | 256×8 | 300 as saved | about 17 s |
| GPU | 512×16 | 106 merged 8 | about 36 s |

Each is the first run's time less a later run's. PyTorch keeps compiled code on
disk, and with it the first runs of the final comparisons, running included,
took 3 to 33 seconds.
This morning's very first compiles of the same layers on the GPU, by a prototype
of them, took 155 to 279 seconds before the first timed run ended; what else the
Mac had cached by the later runs, such as the GPU's compiled programs, was not
measured.

## What this does and does not show

- **Measured:** saved inference batches through the forward pass alone, one
  network, on the Mac's CPU and GPU: one comparison of the new layout and two
  processes of each kind for the compiled layers, for each setting.
- **The compiled layers make the GPU forward pass of large networks 6% to 24%
  faster** at 9 to 60 states an inference batch; larger inference batches gain
  more. For the 64×2 network they make the GPU forward pass slower.
- **Not measured:** a training run with `--compiled-forward` on the GPU; the
  laying out, reading and replying that the inference server does around the
  forward pass; the Windows PC, whose PyTorch would need its compiler's GPU code
  generator, which was not checked; compiling the actions' vectors and the policy
  readout, whose sizes follow the legal actions; a CUDA graph.
