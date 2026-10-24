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

const identityKey = (value) => String(value ?? '').toLowerCase().replace(/[^a-z0-9]/g, '');
function factionIdentity(value, replay) {
  if (value === null || value === undefined || value === '') return null;
  if (own(replay?.factions || {}, value)) return value;
  const matches = recordEntries(replay?.factions).filter(([id, faction]) =>
    identityKey(id) === identityKey(value) || identityKey(faction.name) === identityKey(value));
  return matches.length === 1 ? matches[0][0] : value;
}
const possessionName = (value, replay) => value === null || value === undefined
  ? 'Unpossessed' : displayName(value, replay);

/** Current possession and original nationality are separate recorded facts. */
export function territoryIdentity(id, state, replay) {
  const territory = state?.territories?.[id];
  const node = replay?.map?.nodes?.[id] || {};
  // An explicit null records lost possession; it must not revive the map's starting owner.
  const owner = factionIdentity(territory && own(territory, 'possessor')
    ? territory.possessor : ownerOf(territory) ?? node.current_owner ?? node.original_owner, replay);
  const originalOwner = factionIdentity(territory && own(territory, 'original_owner')
    ? territory.original_owner : node.original_owner, replay);
  const ownerName = possessionName(owner, replay);
  const originalName = possessionName(originalOwner, replay);
  const changed = originalOwner !== null && identityKey(owner) !== identityKey(originalOwner);
  return { owner, originalOwner, ownerName, originalName, changed,
    subtitle: changed ? `${ownerName} · originally ${originalName}`
      : `${ownerName} · ${node.ipp_value ?? territory?.ipp_value ?? 0} IPP` };
}

const possessionCache = new WeakMap();
function possessionHistory(replay) {
  if (possessionCache.has(replay)) return possessionCache.get(replay);
  const owners = new Map(recordEntries(replay.initial.territories)
    .map(([id, territory]) => [id, territory.possessor]));
  const nations = new Map(recordEntries(replay.initial.nations));
  const indices = new Map();
  let politics = replay.initial.politics || {};
  const steps = replay.steps.map((step, index) => {
    indices.set(step, index);
    const changes = step.changes || {};
    for (const id of changes.nations?.remove || []) nations.delete(id);
    for (const [id, nation] of recordEntries(changes.nations?.upsert)) nations.set(id, nation);
    const result = [];
    const update = (zone, to) => {
      const from = owners.get(zone) ?? null;
      owners.set(zone, to);
      if (from === to) return;
      const nation = nations.get(from);
      const alignment = Boolean(nation?.game_flags?.incorporated && nation.controller_nation === to);
      const attackers = alignment ? [...(politics.attacked_warlords?.[from] || [])] : [];
      result.push({ zone, from, to, reason: alignment ? 'alignment' : 'possession',
        attackers, eventNumber: index + 1 });
    };
    for (const zone of changes.territories?.remove || []) update(zone, null);
    for (const [zone, territory] of recordEntries(changes.territories?.upsert)) {
      if (own(territory, 'possessor')) update(zone, territory.possessor);
    }
    if (own(changes, 'politics')) politics = changes.politics || {};
    return result;
  });
  const result = { steps, indices };
  possessionCache.set(replay, result);
  return result;
}

/** Index zero contains ownership changes caused by event one; no search branches. */
export function possessionChanges(replay) { return possessionHistory(replay).steps; }

export function possessionChangeText(change, replay) {
  let reason = '';
  if (change.reason === 'alignment') {
    const attackers = change.attackers.map((id) => displayName(id, replay)).join(' and ');
    reason = attackers ? ` (alignment after ${attackers} attack${change.attackers.length > 1 ? 's' : ''})`
      : ' (alignment)';
  }
  return `${displayName(change.zone, replay)}: ${possessionName(change.from, replay)} → ${possessionName(change.to, replay)}${reason}`;
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
  const action = step.action || {};
  const summary = step.summary ? String(step.summary) : step.kind === 'chance' ? 'Dice event resolved'
    : `${displayName(step.actor ?? step.nation, replay)} · ${displayName(action.kind ?? step.kind, replay)}`;
  const history = replay ? possessionHistory(replay) : null;
  const changes = history?.steps[history.indices.get(step)] || [];
  const details = changes.slice(0, 2).map((change) => possessionChangeText(change, replay));
  if (changes.length > 2) details.push(`${changes.length - 2} more possession changes`);
  return [summary, ...details].join(' · ');
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
