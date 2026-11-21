# Looking for the defect behind the game process crashes — 21 November 2026

The owner stopped the long training run at 07:40 on 21 November 2026, after five
game process crashes in 32.6 hours of play, to look for their cause (Q-012,
choice A). The [evidence file](crash_diagnosis_2026_11_21.json) holds the five
crash reports' stacks, every sanitizer run and the timing of the checks the
training build now keeps.

## The crash reports

All five game processes aborted with macOS's allocator message that memory
being freed had not been allocated, all while freeing the game copies that the
search's tree nodes hold: four in `Searcher::retain` (`src/search.cpp`), which
frees the nodes the next search does not keep, and the first while a game's
whole search tree was freed after the game had failed. The memory being freed
was each time in another part of a game state (`State` in
`include/game/campaign.hpp`): a nation's state, a unit's state twice, the whole
state, and an entry of its build projects. At each crash 36 to 41 of the other
game threads were waiting for the inference server (`InferenceClient::readAll`
in `src/inference_client.cpp`); in the last two, four or five others were
running engine code.

## Reading the code

What the 42 game threads of one process share is the scenario's definition and
the rules, which are read-only; each game's menu table and decision caches,
which take a lock and belong to that game's engines; the zone encoder's cache
of encoding contexts, which takes a lock; and nothing else that changes: the
markers of the open position scope and of the checked menu action are
thread-local, each game thread has its own inference client and shared buffer,
and the three places that write a position's key into a decision cache without
its lock write into a cache that the transition has just made. The search tree
keeps its nodes in a deque, whose elements never move, and its nodes hold their
game copies through shared pointers. No defect was found by reading.

## The sanitizer runs

A script played games the way a training game process does: several game
threads in one process, each playing eleven-round games one after another, every
decision searched by the C++ search without Python's lock (64 simulations to
depth 16, with root noise) in a search tree kept from one decision to the next.
The priors came from the search's uniform evaluator, which encodes no position;
from a uniform evaluator that the search asks through `evaluate_zone`, so that
the zone encoder encodes every position evaluated; or from the network of the
newest training run's generation 10, on the CPU. The engine was built from the
current sources with ThreadSanitizer, or with AddressSanitizer, UndefinedBehaviorSanitizer
and libc++'s debug hardening, and in the last run also with the SlotMap check
(`GWRL_CHECK_SLOT_MAPS` in `include/game/slot_map.hpp`).

| Check | Priors | Game threads | Decisions | Reports |
| --- | --- | ---: | ---: | ---: |
| ThreadSanitizer | uniform, no encoding | 4 | 4,887 | 0 |
| ThreadSanitizer | uniform, every position encoded | 3 | 3,281 | 0 |
| AddressSanitizer | uniform, no encoding | 5, then 3 | 13,925 | 0 |
| AddressSanitizer | the network, every position encoded | 3 | 1,344 | 0 |
| AddressSanitizer with the SlotMap check | the network, every position encoded | 3 | 5,337 | 0 |

## The allocator's message

macOS's allocator printed nothing when a test process freed memory twice: the
process ended with SIGABRT, and neither its standard error nor a crash report
kept the message. With `MallocDebugReport=stderr` set, the allocator wrote its
message, with the address, to standard error. So the training runs kept no
allocator message, only the crash reports' stacks.

## The checks' cost

The training build now keeps libc++'s fast hardening, which checks every index
into a vector, string, span or array and every access to an optional, and the
SlotMap check, which throws when an iterator is used after its map gained or
lost a thing. With one game thread each, side by side on the busy Mac, on the
same seeds, the build with both checks played 6,576 decisions in 300 seconds
against 6,724 for the build without them, 2.2% fewer. Both played the same four
complete games, of 1,443, 1,446, 1,594 and 1,422 decisions, and no check fired.

## What this shows and does not show

It shows no data race and no memory error, out-of-bounds index or stale SlotMap
iterator on the code that about 8,000 decisions under ThreadSanitizer and about
21,000 under AddressSanitizer reach, the zone encoder and the network-guided
search among it. The defect is therefore not on a path that every game reaches
(inferred). It does not rule out a rarer one: the crashes came about once every
2.9 million decisions (32.6 hours at about 450,000 decisions an hour, five
crashes), about 140 times the decisions checked here, and the inference
client's own path was not exercised. The defect is not found.

What the next crash will leave is described in
[running training on the Mac](../../design/README.md#92-running-training-on-the-mac):
the move logs of the dead process's games, its crash report and Python stacks,
and the allocator's message; and the checks above may stop the defect where it
happens, if it is an out-of-bounds index or a stale SlotMap iterator.
