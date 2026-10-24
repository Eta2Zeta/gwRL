/** Verify the browser reducer against immutable synthetic and optional real data. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { applyChanges, createReplayModel, eventSummary, initialState, possessionChanges,
  possessionChangeText, stateAt, territoryIdentity, validateReplay }
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

const tsinghai = 'land_china_tsinghai';
const maClique = 'warlord_tsinghai';
const ownershipReplay = {
  schema: 'campaign-replay-v1',
  map: { nodes: { [tsinghai]: { name: 'Tsinghai', type: 'land', ipp_value: 0,
    original_owner: 'Ma Clique', current_owner: 'Ma Clique' } } },
  factions: { [maClique]: { name: 'Ma Clique' }, kmt: { name: 'KMT' }, ccp: { name: 'CCP' } },
  initial: { territories: { [tsinghai]: { possessor: maClique, flags: {} } },
    nations: { [maClique]: { controller_nation: null, game_flags: {} } },
    politics: { attacked_warlords: {} } },
  steps: [
    { summary: 'Flags updated', changes: {
      territories: { upsert: { [tsinghai]: { possessor: maClique, flags: { visited: 1 } } } } } },
    { summary: 'CCP attacks', changes: { politics: { attacked_warlords: { [maClique]: ['ccp'] } } } },
    { summary: 'Finish combat', changes: {
      territories: { upsert: { [tsinghai]: { possessor: 'kmt', flags: {} } } },
      nations: { upsert: { [maClique]: { controller_nation: 'kmt', game_flags: { incorporated: 1 } } } },
      politics: { attacked_warlords: {} } } },
    { summary: 'Possession lost', changes: {
      territories: { upsert: { [tsinghai]: { possessor: null, flags: {} } } } } },
  ],
};
const ownershipSource = JSON.stringify(ownershipReplay);
const ownershipModel = createReplayModel(ownershipReplay);
const initialIdentity = territoryIdentity(tsinghai, ownershipModel.seek(0), ownershipReplay);
assert.equal(initialIdentity.owner, maClique);
assert.equal(initialIdentity.originalOwner, maClique, 'printed owner name resolves to the same canonical faction');
assert.equal(initialIdentity.changed, false);
assert.equal(initialIdentity.subtitle, 'Ma Clique · 0 IPP');
const alignedIdentity = territoryIdentity(tsinghai, ownershipModel.seek(3), ownershipReplay);
assert.equal(alignedIdentity.subtitle, 'KMT · originally Ma Clique');
assert.equal(alignedIdentity.changed, true);
const unpossessedIdentity = territoryIdentity(tsinghai, ownershipModel.seek(4), ownershipReplay);
assert.equal(unpossessedIdentity.owner, null, 'explicit null cannot fall back to starting map ownership');
assert.equal(unpossessedIdentity.ownerName, 'Unpossessed');
assert.equal(unpossessedIdentity.subtitle, 'Unpossessed · originally Ma Clique');
assert.deepEqual(territoryIdentity(tsinghai, ownershipModel.seek(0), ownershipReplay), initialIdentity);
assert.deepEqual(territoryIdentity(tsinghai, ownershipModel.seek(3), ownershipReplay), alignedIdentity);
const ownershipChanges = possessionChanges(ownershipReplay);
assert.equal(possessionChanges(ownershipReplay), ownershipChanges, 'history is derived once per replay');
assert.deepEqual(ownershipChanges.map((changes) => changes.length), [0, 0, 1, 1],
  'flags and political metadata alone are not possession changes');
assert.deepEqual(ownershipChanges[2][0], { zone: tsinghai, from: maClique, to: 'kmt',
  reason: 'alignment', attackers: ['ccp'], eventNumber: 3 });
assert.equal(ownershipChanges[3][0].reason, 'possession');
assert.equal(possessionChangeText(ownershipChanges[2][0], ownershipReplay),
  'Tsinghai: Ma Clique → KMT (alignment after CCP attack)');
assert.equal(eventSummary(ownershipReplay.steps[2], ownershipReplay),
  'Finish combat · Tsinghai: Ma Clique → KMT (alignment after CCP attack)');
assert.equal(JSON.stringify(ownershipReplay), ownershipSource, 'ownership annotations cannot mutate evidence');

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
  if (data.initial.territories?.[tsinghai]?.possessor === maClique) {
    assert.equal(territoryIdentity(tsinghai, browsing.seek(0), data).subtitle, 'Ma Clique · 0 IPP');
  }
  // This specific recorded benchmark contains the reported Ma Clique transfer;
  // another user's full_campaign.json can legitimately have different play.
  if (data.metadata?.source_report_sha256 === '50bc15604e180f4301359c572f7098b67513fc4c8dc2e7262af25195e72e6e3b') {
    assert.equal(territoryIdentity(tsinghai, browsing.seek(11), data).owner, maClique);
    assert.equal(territoryIdentity(tsinghai, browsing.seek(12), data).owner, 'kmt');
    assert.equal(territoryIdentity(tsinghai, browsing.seek(0), data).owner, maClique);
    const changes = possessionChanges(data);
    const change = changes[11].find((item) => item.zone === tsinghai);
    assert.equal(change.eventNumber, 12);
    assert.equal(change.reason, 'alignment');
    assert.deepEqual(change.attackers, ['ccp']);
    assert.match(eventSummary(data.steps[11], data), /Tsinghai: Ma Clique → KMT \(alignment after CCP attack\)/);
  }
  console.log(`${path}: ${data.steps.length} events; final and backward seeks match`);
}
console.log('Campaign replay reducer checks passed');
