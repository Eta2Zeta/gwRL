# Fast searches that count a reused tree's visits — 25 November 2026

On 25 November 2026 the owner answered Q-023 with choice C: a fast search, the
search of 150 simulations at a decision not kept as a training sample, counts
the visits its root already holds from the reused tree toward its budget, and
runs only as many new simulations as bring its root's actions to 150 visits,
none when they already hold that many; a full search still runs its 800 new
simulations ([design document, section 4.7](../../design/README.md#47-more-detail-on-the-search)).
The record of 24 November had inferred from 407 searches that this would run
17.7% fewer simulations
([record](self_play_speed_256x16_2026_11_24.md)). This record measures the
setting as built (`SearchSettings::countReusedVisits` in
`include/game/search.hpp`). The [evidence file](reused_visits_counted_2026_11_25.json)
holds every number below.

- **The fast searches asked for about half as many network evaluations.** Along
  two games, a fast search asked for 82.2 network evaluations on average
  instead of 150, and 19.9% of the fast searches asked for none and chose their
  move from the reused visits alone. A fast search's root ended with 150 visits
  at the median, against 206 when every search ran its whole budget, and 203.7
  on average, against 276.6.
- **All the searches together asked for about a seventh fewer.** A searched
  decision asked for 262.9 network evaluations on average, against 304.9, 13.8%
  fewer. In these games 25.2% of the searches were full searches with
  counting, against 23.8% without. With full searches at exactly a quarter, the
  averages give $0.25 \times 800 + 0.75 \times 82.2 \approx 261.7$ network
  evaluations a searched decision, against $0.25 \times 800 + 0.75 \times 150 = 312.5$,
  16.3% fewer.
- **The full searches were unchanged:** 800 network evaluations each, with and
  without counting.

## How it was measured

`studies/campaign/runs/reused-visits-2026-11-25/counted_visits.py` played the
same two eleven-round games' seeds, 51 and 52, twice: once with every search
running its whole budget and once with the fast searches counting the reused
visits, 250 searched decisions a game at most. The search settings were the
training run's: a quarter of the decisions, drawn at random, searched with 800
simulations and exploration noise, the rest with 150 and none, 8 simulations a
request, no depth limit, the move drawn from the visit shares in game round 1
and the most visited after. The network was a stand-in that gives every
position made-up priors and values from a hash of its input, as in the record
of 24 November. A search's network evaluations are the stand-in's calls during
it.

## What it shows and does not show

It shows that the setting does what Q-023 chose: the fast searches ask for
fewer network evaluations, the full searches as many as before. It does not
show the saving in the training run: the two settings played different games
once a move differed, the stand-in network's priors are not a trained
network's, and a trained network may send more of a search's simulations down
the move the game then plays, which would leave more visits to the next
decision and save more (inferred).
