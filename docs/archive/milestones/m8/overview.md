# M8: air operations, bombing and defensive reactions

> Completed milestone reference. Test counts, timings and next steps below describe this delivery. Use the [project guide](../README.md) for current status and instructions.

**Status: complete, 22 October 2026.** RCL-013 is adopted: Advanced Artillery
city bombardment uses attrition's starting-adjacency and no-movement conditions,
while retaining its separate 1D6 city damage.

The air module covers flight permissions and range, Airbase bonuses, independent
carrier-aircraft movement, and joint return plans with weighted carrier capacity.
Plans reserve surviving scrambled and defending carrier aircraft's return seats;
a locally available seat cannot be promised to several aircraft at once.

Aircraft can screen Enemy Fighters and preserve a serialized continuing force.
Success permits further attacks using remaining flight; failure requires return.
Continuing aircraft cannot conduct an airborne assault. Transport capacity,
aligned foreign cargo timing, airborne drop/AAA linkage, retreat and failed landing
are resolved through the shared battle state, including developer-corrected RCL-001.

Strategic bombing covers escorts and interception, damage before facility AAA,
construction setbacks, permanent city IPP loss and destruction, technology loss,
and all railroad tracks on the selected border. Rockets use their printed range,
political overflight and single-use rules. Artillery city bombardment has no
bomber interception or anti-aircraft sequence. Selected Japanese Surprise Attacks
apply their separate interception/first-strike and scramble restrictions; the
facility-AAA exemption belongs to port attacks.

All choices and continuations are serialized and replayable. The four air suites
contain **40 fixture groups**: air 10, logistics 9, integration 10, missions 11.
They include actual airborne drop and aircraft retreat, shared carrier plans,
screening success/failure, source-specific rocket cases, and adopted bombardment.
M9 adds naval targets and port/MAP engagement rather than substituting dummy
naval outcomes. Damaged-port evacuation can suspend and resume bombing.

The [M8 verification record](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m8/verification.json)
records the source and artifact hashes and final checks. Earlier milestone records
remain historical snapshots. M9 and M10 are not certified by this air-layer gate.

On 23 October, RCL-001 was updated to the developer’s v4.4 correction at the
user’s request: both sides’ Fighters and AAA resolve in step 4, surviving
transports land in step 5, and transport/cargo casualties stay linked through
steps 3–4. The [dated correction record](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m8/airborne_correction_2026_10_23.json) supplements the original verification.
