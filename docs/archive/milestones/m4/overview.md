# M4: politics, warlords and national turns

> Completed milestone reference. Test counts, timings and next steps below describe this delivery. Use the [project guide](../README.md) for current status and instructions.

Status: **complete and verified on 21 October 2026**. All ten CTest suites and
all 128 Python tests pass. The three political suites cover 34 fixture groups.
No M4 user decision remains open.

M4 adds the political rule layer to the shared campaign engine. It covers
warlord alignment, influence and recruitment, the Chinese Truce, Chinese
major-power evolution, capture/liberation notifications and surrender. Movement,
combat resolution and final economy rules remain the following milestones.

The public interface is [politics.hpp](/Users/home/Desktop/gwRL/include/game/politics.hpp).
The implementation is split between common political events, warlords/truce,
and influence/recruitment. The [source profile](/Users/home/Desktop/gwRL/game_content/rules/gw36_politics_v43.json)
and [source coverage](/Users/home/Desktop/gwRL/docs/m4/source_coverage.md) retain
rulebook pages, national-sheet conditions, adopted rulings and campaign choices.

## Political transitions

- Each of the eight warlords remains a whole faction, including Beiping/Hopeh
  and Kwangtung/Hainan. Foreign-invasion alignment resolves at the end of Combat.
  Neighbor categories are captured before any outcome is applied, so an early
  result cannot change a later warlord's odds. Each eligible warlord receives
  one D12 result; the no-neighbor KMT result needs no roll.
- CCP/Dadao attacks and KMT's post-CCP-elimination attacks use their distinct
  alignment rules. CCP can be revived through the specified warlord alignment
  without treating its earlier loss of all units as surrender.
- CCP and Japan have one optional influence attempt per national turn. The
  qualifying garrison must date from turn start; impassable borders do not
  count. Adjacent zones count once across the whole warlord. Spending is paid
  before rolling, cannot exceed the original threshold or treasury, and never
  cancels the natural-12 backfire to KMT. Applying that adopted always-backfire
  rule after KMT surrendered reactivates KMT only with the transferred warlord's
  surviving assets; it restores no erased forces, cash, capital or used awards.
  The source-combination inference is identified in the source profile.
- Japanese influence creates or extends a separate Dadao minor. Control grants
  its named permissions and does not make those assets Japanese. Its eventual
  incorporation uses the printed triggers. Later transfers follow the existing
  incorporation destination rather than leaving assets under an inactive owner.
- CCP minor recruitment remains distinct from controlled-minor recruitment.
  Mongolia and Dadao can receive infantry, two militia (including split placement),
  a free ship-queue stage or a full facility repair. Their roll excludes offshore
  possessions; troop placement requires continuous possession since turn start.
  Free queue work does not increase the amount actually paid for construction.
- Both Chinese factions decide whether to form the Truce at the specified
  end-of-Combat opportunity. It permits shared access/defense, with voluntary
  separation in Combat Movement and termination in Combat. There is no invented
  earlier commitment to break it. Termination directly queues battles in remaining
  mixed stacks; M7 applies KMT's specified elimination on its actual attack rolls,
  with no preliminary political roll. Termination cannot be followed by signing
  the same treaty again (RB 6.2).
- KMT/CCP evolve immediately at 13 possessed territorial IPP, including during
  another nation's turn. The entitled Chinese player chooses a capital and may
  take one free Major Factory in a city or Medium Factory elsewhere. The national
  objective is the same award. CCP's minor recruitment/influence and KMT Low
  Morale stop immediately; only the explicit own-turn Decentralized Production
  exception continues for that turn. Evolution also terminates an active Truce.

## Identity, capture and surrender

All retained factions now have source-backed Home Country membership. The
unlisted-nation rule uses original mainland possessions; Guangxi's Hainan is
excluded from its own homeland while remaining Chinese Home Country. Mongolia
keeps its separate four-zone homeland. Current possession does not rewrite
original nationality. A shared enemy does not create a separate aligned
Mongolian/CCP army or substitute CCP for the absent USSR; the ordinary
Major-Power alignment and explicit Truce permissions remain distinct.

The loader still creates the approved 12 active nations, 99 deployed units,
22 facilities, two ship queues with 10 IPP already paid, and 23 IPP opening cash.
Dadao has a dormant definition and becomes an active nation only when created.
There is no added Soviet nation or calendar turn.

A resolved land-capture notification requires a surviving attacking land unit.
It updates possession and territorial IPP immediately, removes the specified
fortifications/coastal artillery and unfinished facilities, and applies capital
cash loss to the bank. Mandatory original-owner liberation takes precedence over
optional gifts of Chinese land. An unaligned Chinese gift requires eligibility
from the later route validator; the conquering units retain a withdrawal duty.
The political service itself does not validate a movement route or resolve combat.

KMT surrenders immediately upon losing all land; CCP never surrenders. Japan's
Tokyo condition is checked at the end of Japan's own turn. Surrender removes the
nation's forces and represents abandoned possessions explicitly as unpossessed,
not as territory still owned by the defeated nation. Each queued ship receives
its own D12: 1-7 scuttles, 8-12 transfers it with existing damage/progress/payments.
The turn waits for those rolls before advancing.

CCP's One China point condition is separate from its surrender-time unit bonus.
The latter becomes five free completed queue entitlements (three Cavalry, two
Infantry) only if CCP has land when KMT surrenders. M6 will place them using the
applicable ordinary placement rules; M4 does not invent a special destination.

The user's 21 October ruling keeps Dadao separate under direct Axis-agent
control if Japan surrenders with no other Axis controller available. Dadao keeps
its assets, wars and recruitment in the existing Japanese calendar slot. It
receives no ordinary IPP income. This is recorded as a campaign choice, not a
publisher rule.

## Scheduling and integration

The CCP -> Mongolia -> Japan -> KMT order and five phases remain unchanged.
A new phase-completion hook starts end-of-Combat political work before the
clock advances. Choices and dice pause that transition. Capital choices route to
the evolving nation's player even when another nation is taking its turn.

Major-power declarations are available through `legalInterrupts()` and
`interrupt()`, including during other national turns. The active nation and its
alliance receive declaration priority. Minor-power declarations remain attached
to land combat movement. Interrupts do not occur inside an unresolved atomic
choice/chance event or strategic naval movement.

All political continuations, capital choices, alignment snapshots, truce state,
surrender status and dormant/active identities participate in serialization,
observations and planning keys. Clone/restore/replay preserve pending work and
do not repeat awards or consume another turn. Missing political continuation
payloads are invalid checkpoints.

`PoliticsRules` composes with later `Rules` modules. Evaluated income can be
collected once at the turn boundary; controlled minors collect no ordinary income.
The actual starting national rates remain explicitly unevaluated until M6. M4
therefore fails closed if a caller tries to collect that unknown income without
an accounting module. The political timeline tests supply explicit known-income
fixtures; they do not demonstrate a playable full campaign.

Truce termination queues battles for the later combat rules. Supply/withdrawal
proofs, ordinary unit movement, purchasing, naval combat and campaign training
are not executed by this milestone.

## Verification

```sh
cmake -S . -B build/m4 -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
cmake --build build/m4 -j 4
ctest --test-dir build/m4 --output-on-failure
./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
git diff --check
```

The [M4 verification record](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m4/verification.json)
records final counts, checked artifacts and preservation of historical milestone
records. The new political suites cover evolution/capture/surrender and replay,
whole-warlord/truce timelines, and influence/recruitment boundaries.
