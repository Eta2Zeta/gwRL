# Two attacks on one land zone by Japan and Dadao — 23 November 2026

At 20:07 on 23 November 2026 a game of the memory-checked first part of the
training run under the land-weighted score
(`studies/campaign/runs/training-land-weighted-2026-11-22/1-memory-checked`,
commit `1101c2e`) failed: game 5967, seed 76431325591368820. Its game process
kept the position before the failing move, and the move, in the part's
`failed-positions/` folder, and the game's move log in the part's
`game-moves/` folder. The
[evidence file](japan_dadao_one_zone_2026_11_23.json) holds the
failure, the replays, every battle of the five orders below, the count in the
kept self-play games, and the SHA-256 of the kept files.

- **The two attacks.** In game round 4, in Japan's Combat Movement Phase, Japan
  declared an amphibious assault on Manchuria-Rehe, which the KMT held, with
  one Artillery aboard a Naval Transport in sea zone P14 (move 369 of the
  game), and Dadao attacked Rehe overland with one Infantry from Suiyuan (move
  370). One KMT Infantry stood in Rehe. Dadao, the Dadao Government, is a Minor
  Power that Japan controls (rulebook section 15.4, page 105; Japan sheet,
  page 1), so it shares Japan's Player Turn (section 7.1, page 43). The engine
  gives each nation's attack its own battle: `registerLandBattle` in
  `src/land_combat.cpp` refuses to put two nations' units in one battle.
- **The failing move.** At the start of the Combat Phase that followed, the
  search for the game's next decision imagined a line of play in which Dadao's
  battle was fought first and won in its second combat round. Rehe was Japan's at the start of the game, so Dadao had
  to give it back to Japan at once (section 10.10.1, page 73; `captureLand` in
  `src/politics.cpp`). Japan's assault then went ahead: with no enemy unit left
  in Rehe, its Artillery landed, and the engine registered a land battle of
  Japan against Rehe's holder, which was now Japan itself. The engine's check
  of the state (`State::validate` in `src/campaign_state.cpp`) refused that
  battle with the error "Battle opponents must differ except uncontested land
  or an explicit movement plan", and the game stopped.
- **The replay.** `tools/replay_failed_move.py`, run with the run's own code,
  played the move again from the kept position and failed with the same error:
  `same_failure`, a defect of the rules as the engine applies them, not damaged
  memory. Today's code (`fa18dcb`) refuses to load the kept position, whose
  rules fingerprint is the run's. With the fingerprint changed to today's
  (`evaluations/replay_5967_current_code.py` in the run's folder), the move
  fails the same way. Since `1101c2e` the rules data have changed only in
  source references and one pinned hash, and the engine only by the blitz fix
  of `f7b7c2d`, so the defect is in today's engine too.
- **How rare.** It is the second game of this part to fail, after game 1316 at
  00:19 on a different defect. By the part's 372nd network update, at 20:05,
  5,952 games had finished.

## The same two attacks in other orders

The attacking player chooses the order in which the declared combats are
fought (section 10.1, page 61). From the game's position at the start of
Japan's Combat Movement in game round 4, before move 369,
`evaluations/same_zone_orders.py` in the run's folder declared two attacks on
one land zone, one by Japan and one by Dadao, and played their battles in five
orders, with the run's code. The dice were chosen, not drawn: every roll of the
side named to win each battle hit, and every roll of the other side missed.
In game round 4 the KMT held both zones of the table: Hopeh, a warlord's at the
start of the game, and Rehe, Japan's at the start.

| Attacks | Battles, in order | What the engine did |
| --- | --- | --- |
| Rehe: Japan's Artillery by sea from P14, Dadao's Infantry overland from Suiyuan | Dadao's, then Japan's assault | Dadao won, and Rehe went back to Japan; Japan's assault stopped the game, as in game 5967 |
| Rehe: Japan's Infantry overland from Eastern Manchuria, Dadao's Infantry overland from Suiyuan | Dadao's, then Japan's | Dadao won, and Rehe went back to Japan; Japan's battle ended with nothing to fight, and the Japanese and Dadao Infantry stood together in Rehe |
| Hopeh: Japan's Infantry by sea from P14, Dadao's Infantry overland from Suiyuan | Dadao's, then Japan's assault | Dadao won and kept Hopeh; Japan's Infantry landed in Dadao's Hopeh, the engine registered a battle of Japan against Dadao, and that battle took Hopeh from Dadao |
| Hopeh: the same | Japan's landing, Dadao's battle, Japan's battle | Japan's Infantry landed; Dadao won Hopeh from the KMT; Japan's battle, with no KMT unit left, took Hopeh from Dadao |
| Hopeh: the same | Japan's landing and battle, then Dadao's | Japan won Hopeh from the KMT and kept it; Dadao's battle, with no KMT unit left, took Hopeh from Japan |

In every order after the first, Japanese and Dadao units stood together in the
zone after the last battle.

## How often Japan and Dadao attack one zone

`evaluations/same_zone_attacks.py` in the run's folder replayed, with the run's
code and without searching, the 118 self-play games whose move logs the run's
evaluations had kept: the 16 games in play at 06:07, up to the game round each
had reached, the 36 that finished from 13:42 to 13:57, after the 288th network
update, and the 66 that finished from 19:31 to 19:46, after the 363rd. At the
end of each of Japan's Combat Movement Phases it read the battles registered in
the state. In none of the 118 games did Japan and Dadao attack the same land
zone in one Player Turn. Game 5967, replayed the same way to its failure,
had one such turn: the one above.

## What this shows and does not show

It shows that the engine lets Japan and Dadao attack one land zone in one
Player Turn, and that once the first of the two battles is won, the engine
either stops the game or reaches a position that the printed rules forbid. A
nation may not declare war
on a member of its own alliance (section 5.1, page 35), and both are in the
Axis, yet the second battle can take the zone from the nation that won the
first. Nations that are not Aligned may not share a land zone (section 0.3,
page 8), and Dadao is not Aligned with Japan while Japan controls it (section
15.4, page 105; it joins Japan only when Japan is at war with China and a
Major Power, `considerDadaoAlignment` in `src/politics_warlords.cpp`), yet
their units end up together. When the zone was originally Japan's, a second
attack from the sea stops the game.

Whether the two may attack one zone at all is a question of reading section
7.1 (page 43): controlled Minor Powers share their controller's Player Turn,
and "They may not attack together".
[Q-019](../../questions.md#q-019-two-attacks-on-one-land-zone-by-japan-and-dadao)
asks the owner which reading to apply.

It does not show which order Japan would have chosen in the real game: the
failure came in a line of play that the search imagined at the start of the
Combat Phase, before the game had fought either battle.
