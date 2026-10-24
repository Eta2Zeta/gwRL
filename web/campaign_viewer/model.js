/** Replay-only state helpers. No engine, network policy, or game rules run here. */
export const COLLECTIONS = Object.freeze([
  'units', 'territories', 'nations', 'facilities', 'construction', 'repairs', 'rails',
]);
const UNSAFE_KEYS = new Set(['__proto__', 'prototype', 'constructor']);
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
export const clone = (value) => JSON.parse(JSON.stringify(value));

export function recordEntries(records) {
  if (Array.isArray(records)) return records.map((value, index) => [String(value.id ?? index), value]);
  return records && typeof records === 'object' ? Object.entries(records) : [];
}

export function validateReplay(data) {
  if (!data || typeof data !== 'object' || data.schema !== 'campaign-replay-v1') {
    throw new Error('This file is not a campaign-replay-v1 recording.');
  }
  if (!data.initial || typeof data.initial !== 'object' || Array.isArray(data.initial)) {
    throw new Error('The recording is missing its initial game position.');
  }
  if (!data.map?.nodes || typeof data.map.nodes !== 'object' || !Array.isArray(data.steps)) {
    throw new Error('The recording needs map nodes and an ordered list of events.');
  }
  for (const [index, step] of data.steps.entries()) {
    if (!step || typeof step !== 'object' || !step.changes || typeof step.changes !== 'object') {
      throw new Error(`Event ${index + 1} is missing its state changes.`);
    }
    for (const field of COLLECTIONS) {
      const patch = step.changes[field];
      if (patch && (typeof patch !== 'object' || Array.isArray(patch))) {
        throw new Error(`Event ${index + 1} has invalid ${field} changes.`);
      }
      if (patch?.remove && !Array.isArray(patch.remove)) {
        throw new Error(`Event ${index + 1} has an invalid ${field} removal list.`);
      }
    }
  }
  return data;
}

export function initialState(replay) {
  const result = clone(replay.initial);
  for (const field of COLLECTIONS) {
    result[field] = Object.fromEntries(recordEntries(result[field]));
  }
  return result;
}

/** Return a fresh state: collection records replace atomically; absent fields survive. */
export function applyChanges(state, changes) {
  const result = { ...state };
  for (const [field, patch] of Object.entries(changes || {})) {
    if (UNSAFE_KEYS.has(field)) continue;
    if (!COLLECTIONS.includes(field)) {
      result[field] = clone(patch);
      continue;
    }
    const records = { ...state[field] };
    for (const id of patch?.remove || []) {
      if (!UNSAFE_KEYS.has(String(id))) delete records[id];
    }
    for (const [id, value] of recordEntries(patch?.upsert)) {
      if (!UNSAFE_KEYS.has(id)) Object.defineProperty(records, id, {
        value: clone(value), enumerable: true, configurable: true, writable: true,
      });
    }
    result[field] = records;
  }
  return result;
}

/** Position 0 is the initial state; position n has applied exactly n recorded events. */
export function stateAt(replay, position) {
  if (!Number.isInteger(position) || position < 0 || position > replay.steps.length) {
    throw new RangeError('Replay position is outside the recording.');
  }
  let state = initialState(replay);
  for (let index = 0; index < position; index += 1) state = applyChanges(state, replay.steps[index].changes);
  return state;
}

/** Bounded seek cache keeps browsing long recordings independent of game execution. */
export function createReplayModel(replay) {
  validateReplay(replay);
  const checkpoints = new Map([[0, initialState(replay)]]);
  let current = 0;
  let state = checkpoints.get(0);
  return {
    replay,
    seek(position) {
      if (!Number.isInteger(position) || position < 0 || position > replay.steps.length) {
        throw new RangeError('Replay position is outside the recording.');
      }
      if (position === current) return state;
      let start = 0;
      if (current <= position) start = current;
      for (const key of checkpoints.keys()) if (key <= position && key > start) start = key;
      let next = start === current ? state : checkpoints.get(start);
      for (let index = start; index < position; index += 1) {
        next = applyChanges(next, replay.steps[index].changes);
        if ((index + 1) % 32 === 0) {
          checkpoints.set(index + 1, next);
          if (checkpoints.size > 9) checkpoints.delete([...checkpoints.keys()].find((key) => key !== 0));
        }
      }
      current = position;
      state = next;
      return state;
    },
  };
}

export function displayName(id, replay) {
  if (id === null || id === undefined || id === '') return '—';
  const value = String(id);
  if (replay?.map?.nodes?.[value]) return replay.map.nodes[value].name || value;
  if (replay?.factions?.[value]) return replay.factions[value].name || value;
  const names = { japan: 'Japan', kmt: 'KMT', ccp: 'CCP', mongolia: 'Mongolia',
    dadao: 'Dadao', axis: 'Axis', allies: 'Allies', comintern: 'Comintern',
    Axis: 'Axis', Allies: 'Allies', Comintern: 'Comintern' };
  return names[value] || value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function locationOf(record) {
  return record?.location ?? record?.zone ?? record?.territory ?? record?.land_id ?? record?.node_id ?? record?.site ?? record?.sea_zone ?? record?.sea_id ?? null;
}
export function ownerOf(record) {
  return record?.nation ?? record?.owner ?? record?.possessor ?? record?.current_owner ?? record?.faction ?? null;
}

export function factionColor(id) {
  const key = String(id || '').toLowerCase();
  if (key.includes('japan') || key === 'axis') return '#b54d43';
  if (key === 'kmt' || key === 'allies') return '#34658a';
  if (key === 'ccp' || key === 'comintern') return '#ad812b';
  if (key.includes('mongolia')) return '#4f7c63';
  if (key.includes('dadao')) return '#8c555a';
  if (key.includes('warlord') || key.includes('clique')) return '#858073';
  return '#7c8583';
}

export function eventSummary(step, replay) {
  if (!step) return 'Initial campaign position';
  if (step.summary) return String(step.summary);
  if (step.kind === 'chance') return 'Dice event resolved';
  const action = step.action || {};
  return `${displayName(step.actor ?? step.nation, replay)} · ${displayName(action.kind ?? step.kind, replay)}`;
}

export function changedLocations(before, after) {
  const result = new Set();
  for (const field of ['territories', 'units', 'facilities', 'construction', 'repairs']) {
    const prior = before?.[field] || {};
    const next = after?.[field] || {};
    for (const id of new Set([...Object.keys(prior), ...Object.keys(next)])) {
      if (JSON.stringify(prior[id]) === JSON.stringify(next[id])) continue;
      if (field === 'territories') result.add(id);
      for (const record of [prior[id], next[id]]) {
        const location = locationOf(record);
        if (location) result.add(location);
      }
    }
  }
  return result;
}
