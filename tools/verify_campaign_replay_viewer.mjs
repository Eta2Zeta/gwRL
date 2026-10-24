/** Verify the browser reducer against immutable synthetic and optional real data. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { applyChanges, createReplayModel, initialState, stateAt, validateReplay }
  from '../web/campaign_viewer/model.js';

const replay = {
  schema: 'campaign-replay-v1', map: { nodes: {} },
  initial: { units: { a: { id: 'a', zone: 'first', damage: 1 } },
    nations: { nation: { treasury: 5 } }, terminal: false, clock: { round: 0 } },
  steps: [
    { changes: { units: { upsert: { a: { id: 'a', zone: 'second' }, b: { id: 'b', zone: 'first' } }, remove: [] } } },
    { changes: { units: { upsert: {}, remove: ['a'] }, nations: { upsert: { nation: { treasury: 2 } }, remove: [] } } },
    { changes: { terminal: true, clock: { round: 1 } } },
  ],
};
const immutable = JSON.stringify(replay);
const model = createReplayModel(replay);
for (const n of [0, 1, 2, 3, 0, 3, 1, 2]) assert.deepEqual(model.seek(n), stateAt(replay, n));
assert.equal(model.seek(1).units.a.damage, undefined, 'upserts replace whole records');
assert.equal(model.seek(2).units.a, undefined, 'removals survive seek');
assert.equal(model.seek(3).terminal, true);
assert.equal(JSON.stringify(replay), immutable, 'browsing cannot mutate recorded data');
for (const n of [-1, 0.5, 4, NaN]) assert.throws(() => model.seek(n), RangeError);
assert.throws(() => validateReplay({ ...replay, steps: [{}] }));
const unsafe = JSON.parse('{"units":{"upsert":{"__proto__":{"polluted":true}},"remove":[]},"__proto__":{"polluted":true}}');
assert.equal(applyChanges(initialState(replay), unsafe).polluted, undefined);
assert.equal({}.polluted, undefined);

for (const path of process.argv.slice(2)) {
  const data = JSON.parse(fs.readFileSync(path, 'utf8'));
  const browsing = createReplayModel(data);
  let sequential = initialState(data);
  for (const step of data.steps) sequential = applyChanges(sequential, step.changes);
  for (const n of [data.steps.length, 0, 1, Math.floor(data.steps.length / 2), data.steps.length, 0]) {
    assert.deepEqual(browsing.seek(n), stateAt(data, n));
  }
  // Python JSON numeric spelling differs (1.0 versus 1); compare parsed frames
  // above rather than pretending a JavaScript JSON hash equals a Python hash.
  assert.deepEqual(browsing.seek(data.steps.length), sequential);
  console.log(`${path}: ${data.steps.length} events; final and backward seeks match`);
}
console.log('Campaign replay reducer checks passed');
