# Decision 612's path to its values — 18 November 2026

The [design document](../../design/README.md#67-the-values) draws how decision
612's feature values become the three values of the Comintern's network, with
the numbers each step gives. This record says how those numbers were obtained.
The [evidence file](value_path_2026_11_18.json) holds them, with every zone's
vector after the message-passing layers.

## How it was made

**The decision, reached again.** The sources of commit `d64117d`, the commit of
the [5 November sample run](training_sample_2026_11_05.md), were extracted and
built apart from the working tree. With generation 1 of that run, `play_episode`
replayed the game of the training sample record as it was played: 64
simulations, depth 16, exploration noise, temperature 1, run seed 1936,
environment seed 1105. The replay stopped at the 613th call of `_decide`: the
training sample record counts decisions from 0, so its decision 612 is the
613th. That decision had 5 legal actions, and the Comintern's network gave the
record's values there to within $10^{-6}$.

**The steps.** At that decision the Comintern's network's modules were applied
one at a time, in the order of `CampaignPolicyValueNet.forward_packed` at that
commit: the embedding lookups (`_bag`), the identity embeddings and static
features, the layer normalizations, the two message-passing layers, the average
and the largest of the 37 zone vectors, `state_encoder` and `value_head`. The
values at the end equal the network's own forward pass to within $10^{-6}$.
Today's network computes the same steps in the same order (`_state_layers` in
`studies/campaign/neural.py`).

## The numbers

Each vector by its first 4 of 64 numbers:

| Step | First 4 numbers |
| --- | --- |
| Shensi's embedding-layer output | −0.001, 0.137, −0.118, −0.104 |
| Shensi's identity embedding | 0.204, 1.874, −1.609, 0.437 |
| Shensi's static features, through their linear layer | −0.449, −0.205, 0.425, −0.504 |
| Shensi's zone vector | −0.294, 1.957, −1.422, −0.203 |
| Shensi after message-passing layer 1 | −0.934, 1.513, −0.295, 1.622 |
| Shensi after message-passing layer 2 | 0.027, 1.158, −0.829, 1.170 |
| The global features' embedding-layer output | −1.179, −1.182, −1.184, 1.185 |
| The global vector | −1.063, −1.073, −1.086, 0.935 |
| The global vector after message-passing layer 1 | −0.581, −0.248, −1.655, 0.333 |
| The global vector after message-passing layer 2 | −1.064, −0.207, −2.095, −0.117 |
| The average of the 37 zone vectors after layer 2 | 0.159, −1.371, 0.093, 0.126 |
| The largest of the 37, number by number | 1.995 (Eastern Manchuria), 1.158 (Shensi), 2.248 (Tokyo), 3.327 (Kobdo) |
| The summary vector | −0.597, 3.316, 1.445, −0.710 |
| The value head's 64 numbers in between, after GELU | −0.154, −0.154, −0.155, 0.395 |
| The three values, in hundreds of points | 0.251, −0.424, −1.024 |

The first four rows are the numbers of the design document's section 6.4, found
again. 31 of the value head's 64 numbers in between are positive. Across the 64
numbers, the largest zone value came from 30 of the 37 zones; Kobdo gave 5 of
them, more than any other zone.

## What this does and does not show

It shows one network at one decision: the Comintern's network after one network
update of a run that has ended, with the input layout and sources of 5 November.
The steps are those of today's network, but the numbers belong to that network
only; a network after more training gives other numbers along the same path.
The numbers say nothing about how good the values are: that is measured against
the games' final scores (the design document's section 8.1).
