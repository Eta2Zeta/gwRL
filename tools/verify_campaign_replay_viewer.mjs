/** Verify the browser reducer against immutable synthetic and optional real data. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { activeBattles, applyChanges, createReplayModel, diceReport, eventSummary, initialState,
  possessionChanges, possessionChangeText, stageLabel, stateAt, territoryIdentity, validateReplay }
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

// Combat panel: each die maps to the shot the battle recorded for it, hits are
// rolls at or under the hit number, and naval movement orders are not battles.
{
  const before = {
    units: { a1: { id: 'a1', type: 'infantry', owner: 'ccp', zone: 'z' },
      d1: { id: 'd1', type: 'cavalry', owner: 'kmt', zone: 'z' }, d2: { id: 'd2', type: 'infantry', owner: 'kmt', zone: 'z' } },
    battles: {
      land_battle_1: { id: 'land_battle_1', zone: 'z', attacker: 'ccp', defender: 'kmt', attackers: ['a1'],
        defenders: ['d1', 'd2'], stage: 'defender_fire', flags: {}, data: { round: 2, rolling_phase: 'defender_fire',
          shots: [{ unit: 'd1', nation: 'kmt', threshold: 2, target: 0, victim_attacker: true },
            { unit: 'd2', nation: 'kmt', threshold: 4, target: 0, victim_attacker: true }] } },
      naval_plan_1: { id: 'naval_plan_1', zone: 'sea', attacker: 'ccp', stage: 'naval_force_selection',
        flags: { naval_movement_plan: 1 }, data: {} },
    },
  };
  const roll = { kind: 'chance', changes: {}, chance: {
    request: { continuation: 'land_battle_1', purpose: 'land_combat_roll', nation: 'ccp',
      dice: [{ sides: 12, modifier: 0, reroll_faces: [], max_rerolls: 0 }, { sides: 12, modifier: 1, reroll_faces: [], max_rerolls: 0 }] },
    events: [{ kind: 'chance', payload: { outcome: { faces: [[2], [5]] } } }] } };
  const report = diceReport(roll, before, { map: { nodes: { z: { name: 'Zone' } } } });
  assert.equal(report.battle.kind, 'Land battle');
  assert.equal(report.battle.round, 2);
  assert.deepEqual(report.dice.map((die) => [die.unitType, die.side, die.threshold, die.effective, die.hit]),
    [['cavalry', 'defender', 2, 2, true], ['infantry', 'defender', 4, 6, false]]);
  assert.equal(report.hits, 1);
  assert.deepEqual(report.battle.sides.map((side) => side.nations.map((group) => group.units.map((unit) => `${unit.count} ${unit.type}`))),
    [[['1 infantry']], [['1 cavalry', '1 infantry']]]);
  assert.deepEqual(activeBattles(before).map((battle) => battle.id), ['land_battle_1']);
  assert.equal(stageLabel('awaiting_combat_rules'), 'declared, not yet fought');
  // Battle dice are requested by the turn's nation, so the summary names no roller.
  const recording = (steps) => ({ map: { nodes: {} }, initial: { territories: {}, nations: {} }, steps });
  assert.equal(eventSummary(roll, recording([roll])), 'Land combat fire · 2 dice: 2 5');
  const research = { kind: 'chance', changes: {}, chance: { request: { continuation: 'economy_research', purpose: 'economy_research:radar',
    nation: 'japan', dice: [{ sides: 12, modifier: 0 }] }, events: [{ kind: 'chance', payload: { outcome: { faces: [[7]] } } }] } };
  const outside = diceReport(research, before, { map: { nodes: {} } });
  assert.equal(outside.battle, null);
  assert.equal(outside.label, 'Research roll · Radar');
  assert.equal(eventSummary(research, recording([research])), 'Research roll · Radar · Japan rolls 1 die: 7');

  // Shore shots name the side hit: bombardment dice belong to the bombarding
  // ships in order, coastal artillery fires at the landing ships, and an
  // assault's sides come from its landing force before any land combat.
  const coast = {
    units: { bb: { id: 'bb', type: 'battleship', owner: 'japan', zone: 'sea' },
      ca: { id: 'ca', type: 'heavy_cruiser', owner: 'japan', zone: 'sea' },
      tr: { id: 'tr', type: 'transport', owner: 'japan', zone: 'sea', cargo: ['inf'] },
      inf: { id: 'inf', type: 'infantry', owner: 'japan', zone: 'sea', carried_by: 'tr' },
      mil: { id: 'mil', type: 'militia', owner: 'kmt', zone: 'shore' } },
    battles: { amphibious_1: { id: 'amphibious_1', zone: 'shore', attacker: 'japan', defender: 'kmt', attackers: [],
      defenders: [], stage: 'amphibious_shore_roll', flags: { amphibious_preparation: 1 },
      data: { sea: 'sea', cargo: ['inf'], bombarding: ['bb', 'ca'], shore_shots: [
        { owner: 'kmt', threshold: 4, eligible: ['mil'] }, { owner: 'kmt', threshold: 2, eligible: ['mil'] },
        { owner: 'japan', threshold: 3, eligible: ['tr'] }] } } },
  };
  const shore = { kind: 'chance', changes: {}, chance: {
    request: { continuation: 'amphibious_1', purpose: 'naval_shore_roll', nation: 'japan',
      dice: [{ sides: 12, modifier: 0 }, { sides: 12, modifier: 0 }, { sides: 12, modifier: 0 }] },
    events: [{ kind: 'chance', payload: { outcome: { faces: [[3], [4], [1]] } } }] } };
  const bombardment = diceReport(shore, coast, { map: { nodes: {} } });
  assert.equal(bombardment.battle.kind, 'Amphibious assault');
  assert.deepEqual(bombardment.dice.map((die) => [die.unitType, die.nation, die.side, die.hit]),
    [['battleship', 'japan', 'attacker', true], ['heavy_cruiser', 'japan', 'attacker', false],
      ['coastal_artillery', 'kmt', 'defender', true]]);
  assert.deepEqual(bombardment.battle.sides.map((side) => side.nations.map((group) => group.units.map((unit) => `${unit.count} ${unit.type}`))),
    [[['1 infantry', '1 battleship', '1 heavy_cruiser']], [['1 militia']]]);
}

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
