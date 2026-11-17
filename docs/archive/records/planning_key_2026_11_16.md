# A planning key from a binary writing of the position — 16 November 2026

The engine works out a position's planning key after every move and every dice
roll: for the recorded history, for the list of moves it shares between copies
of a game, and for the search, which names its tree's positions by it. The key
was the SHA-256 digest of the position's whole canonical text. It is now the
digest of a compact binary writing of the same content, which the same walk of
the position produces ([keys](../../engine/README.md#8-copies-saved-games-and-replays)),
and the digest of the canonical text survives as the *canonical key*, for
comparing builds. Play is the same at every step of 300 random games and 4
searched games. The [evidence file](planning_key_2026_11_16.json) holds the
exact values.

## Why the key mattered

- **How often:** one searched game (seed 41) worked out 70,672 planning keys,
  53,173 after moves and 17,485 after dice. The shared lists of moves looked a
  key up 54,441 times and found a list already made 9,498 times, so the key
  pays for itself there; it was its cost that was too high.
- **What it cost:** a profile of a searched game on the slot maps build
  (`525a542`) put 15.6% of the engine's samples in the planning key: 11.1% in
  writing the canonical text and 4.0% in its SHA-256. Escaping the text's
  strings (`appendEscaped`) took 7.0% by itself, through the thousands of short
  strings a position holds rather than their length: scanning sixteen bytes at
  a time with NEON took a key only from 68 µs to 60 µs at the first position.

## The binary writing

The writer of the canonical text (`writeState` in `src/campaign_state.cpp`)
became a template over its output, with a second, binary output. That leaves
out what the text spells for a reader: field names, which the walk writes in a
fixed order, quotes and escapes, and the names of zones, nations, unit types,
facility types and technologies, which it writes as their numbers. Every value
starts with a tag byte, text carries its length, integers take one byte when
small, and containers are closed, so two positions give the same bytes exactly
when they give the same text. A test plays a random game and checks at every
position that equal planning keys and equal canonical keys always pair up
(`tests/campaign_env_tests.cpp`).

Each key on positions of a random game (seed 7), every 150 steps:

| Step | Canonical text key before (`525a542`) | Canonical key now | Planning key now |
| ---: | ---: | ---: | ---: |
| 0 | 68.5 µs | 60.4 µs | 20.9 µs |
| 150 | 94.1 µs | 78.9 µs | 29.8 µs |
| 300 | 75.6 µs | 71.5 µs | 28.5 µs |
| 450 | 82.3 µs | 73.3 µs | 30.2 µs |
| 600 | 82.1 µs | 75.6 µs | 32.3 µs |
| 750 | 85.7 µs | 79.0 µs | 33.3 µs |

About a third of what remains is the SHA-256 of the binary writing.

## The same play

The planning keys of the two builds differ, so `tools/compare_engine_builds.py`
now identifies positions by the canonical key, and by the planning key on
builds older than the canonical key, which computed it the same way. With that
tool the records of the engine before any of the names work (`9519ea7`) and of
the slot maps build were made again; the slot maps build matched `9519ea7`
again at all 443,974 steps.

- **Random games:** the same legal moves, chosen moves and positions at all
  443,974 steps of the 300 games, compared with `9519ea7` and with the slot
  maps build.
- **Searched games:** the same kind and move at all 4,985 events of the 4
  games, and the same final positions, compared with `9519ea7`.

## What it saves

| Workload | Slot maps build | This change | Change |
| --- | ---: | ---: | ---: |
| Random games: instructions to list the moves, per call | 5.74 M | 5.68 M | −1.0% |
| Random games: instructions to play a move, per call | 3.02 M | 2.08 M | −31.1% |
| Random games: instructions to roll the dice, per call | 2.41 M | 1.47 M | −39.0% |
| Four searched games: instructions, bracketed runs | 5,170 G | 4,889 G and 4,883 G | −5.5% |

Listing the moves barely changes: the key it needs was already worked out when
the move before was played. In a searched game, playing moves and rolling dice
are only part of the engine's work, and the engine about half of the game's,
the search in Python and the network the rest, so the saving comes to 5.5% of
the game's instructions. Against the engine before any of
the names work, a searched game now runs 27.8% fewer instructions (6,766 G to
4,886 G in this pair of runs).

The slot maps build's searched games ran between two runs of this change, back
to back: it took 433.9 s of CPU time, this change 396.0 s and 377.8 s, 10.8%
less. The Mac's other work rose to a five-minute load average near 18 during
those runs, so the CPU times are rough; the instruction counts are not.

## What this does and does not show

- **Measured:** identical play in 300 random and 4 searched games; the
  instructions each engine call and each searched game ran; the time of each
  key on positions of a random game; how often one searched game needed a key.
- **Not measured:** decisions per hour in a training batch.
- **Not done:** the planning key still digests its bytes with SHA-256, about a
  third of its cost; a faster hash of 128 bits would take most of that, at the
  price of a hash function of the project's own.
