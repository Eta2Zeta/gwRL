# The coordinator's column lookups, and a fused replacement — 4 November 2026

Since the search keeps copies of its positions
([record](search_copies_2026_11_04.md)), the coordinator, the one process that
evaluates every game's positions, limits the Mac layout: it was busy 90% of the
time in a matched batch. On 2 November the network's forward pass was about three
quarters of its time, and the column lookups were the largest single part, 26%
([profile](search_replays_2026_11_04.md#2-november-one-profiled-training-batch)).
This measurement times those lookups inside the real forward pass and a fused
replacement. The replacement is not in the code yet. The
[evidence file](coordinator_lookups_2026_11_04.json) holds the exact values.

## What a lookup does

Every answer in a position's input adds its column's learned vector, weighted, to
one row: a zone of a position, a position, or a legal move. `_bag` in
`studies/campaign/neural.py` gathers the answered columns' vectors into one large
temporary array, multiplies each by its weight and adds them into their rows:
three operations, three times per forward pass (zones, positions and moves).
PyTorch's `embedding_bag` does the same sum in one operation without the
temporary array. It needs each row's answers to be consecutive, and the packed
batches already are.

## Measurement

Commit `c58942a`, PyTorch 2.11 on the CPU with one thread, a fresh 64×2 network,
574 positions from three random games (seeds 5000, 5001 and 5002, every 7th
decision with more than one legal move). For each batch size, 280 timed batches
drawn from them, after 20 warm-up passes:

| Positions per call | Answers looked up | Forward pass | Of which lookups | Forward pass, fused lookups | Largest output difference |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1,484 | 0.695 ms | 0.156 ms | 0.537 ms | 0 |
| 4 | 6,056 | 1.384 ms | 0.519 ms | 0.973 ms | 0 |
| 16 | 24,180 | 4.631 ms | 2.275 ms | 2.380 ms | 0 |

In the 2 November batch the coordinator's calls carried 3.9 positions on average,
so the forward pass would be about 30% faster, and the gain grows with larger
calls. The fused outputs were identical to the last bit for every batch.

## What this does and does not show

- **Measured:** the forward-pass times above, on random-play positions with
  fresh networks.
- **Inferred:** with the forward pass about three quarters of the coordinator's
  busy time, fused lookups would cut that time by roughly a fifth to a quarter.
  The game processes would then use about 10 of the 11 training cores again, so
  the cores, not the coordinator, would set the next limit.
- **Open:** training's backward pass through the fused lookup, and the gain in a
  whole training batch, are unmeasured.
