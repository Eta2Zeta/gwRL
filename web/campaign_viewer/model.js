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

const POWER_STATUS = { major: 'Major power', minor: 'Minor power', warlord: 'Warlord' };
const ALLIANCES = ['axis', 'allies', 'comintern'];

/** Alliances, wars and standing political facts at one position. */
export function politicalStatus(state, replay) {
  const politics = state?.politics ?? {};
  const surrendered = politics.surrendered ?? [];
  const names = (ids) => ids.map((id) => displayName(id, replay)).join(', ');
  const groups = new Map([...ALLIANCES, null].map((id) => [id, { id, members: [], absorbed: [] }]));
  const wars = new Map();
  for (const [id, nation] of recordEntries(state?.nations ?? {})) {
    const group = groups.get(nation.alliance ?? null) ?? groups.get(null);
    if (nation.game_flags?.incorporated) {
      group.absorbed.push(id);
      continue;
    }
    const enemies = nation.at_war_with ?? [];
    const controller = nation.controller_nation;
    group.members.push({ id, status: POWER_STATUS[nation.power_status] ?? 'Status unknown', wars: enemies,
      capital: politics.capitals?.[id] ?? null, controller: controller && controller !== id ? controller : null,
      surrendered: surrendered.includes(id) });
    for (const enemy of enemies) {
      const [left, right] = [id, enemy].sort();
      wars.set(`${left}|${right}`, { key: `${left}|${right}`, left, right });
    }
  }
  const attacked = Object.entries(politics.attacked_warlords ?? {})
    .map(([warlord, attackers]) => `${displayName(warlord, replay)} by ${names(attackers)}`);
  const facts = [
    { label: 'Chinese Truce', value: politics.chinese_truce ? 'In force' : politics.truce_offer_pending ? 'Offer pending'
      : politics.truce_permanently_ended ? 'Ended for good' : 'Not in force' },
    { label: 'Foreign invader of China', value: politics.china_invader ? displayName(politics.china_invader, replay) : 'None' },
    { label: 'Evolved to Major power', value: names(politics.evolution_awarded ?? []) || 'None yet' },
    { label: 'Surrendered', value: names(surrendered) || 'None' }];
  if (attacked.length) facts.push({ label: 'Warlords attacked', value: attacked.join('; ') });
  if (politics.alignment_queue?.length) facts.push({ label: 'Warlords choosing a side', value: names(politics.alignment_queue) });
  return { groups: [...groups.values()].filter((group) => group.members.length || group.absorbed.length),
    wars: [...wars.values()].sort((first, second) => first.key.localeCompare(second.key)), facts };
}

const ROLL_LABELS = {
  land_combat_roll: 'Land combat fire', land_casualty_dispute: 'Casualty dispute roll',
  naval_combat_roll: 'Naval combat fire', naval_shore_roll: 'Shore bombardment and coastal fire',
  naval_shore_dispute: 'Shore casualty dispute roll', naval_casualty_dispute: 'Naval casualty dispute roll',
  naval_raider_discovery: 'Raider discovery roll', naval_port_aa: 'Port anti-aircraft fire',
  naval_port_capture: 'Captured-ship roll: 1–9 scuttled, 10–12 captured',
  air_interception_roll: 'Air interception', air_bomb_damage: 'Bombing damage',
  air_facility_aa: 'Facility anti-aircraft fire', air_rocket_aa: 'Anti-aircraft fire at a rocket',
  recruitment_roll: 'Recruitment roll', influence_roll: 'Influence roll',
};
// Battles record each die's firing unit and hit number under these data keys.
const SHOT_KEYS = { land_combat_roll: 'shots', naval_combat_roll: 'naval_shots',
  air_interception_roll: 'air_shots', naval_shore_roll: 'shore_shots' };

export function rollLabel(purpose, replay) {
  if (ROLL_LABELS[purpose]) return ROLL_LABELS[purpose];
  if (String(purpose).startsWith('economy_research:')) return `Research roll · ${displayName(String(purpose).slice(17), replay)}`;
  return displayName(purpose, replay);
}

// Naval movement orders share the battle records but are not fights.
const fighting = (battle) => battle?.stage !== 'finished' && !battle?.flags?.finished && !battle?.flags?.naval_movement_plan;
const STAGES = { awaiting_combat_rules: 'declared, not yet fought', attacker_fire: 'attacker fires',
  defender_fire: 'defender fires', air_fire: 'aircraft fire', first_strike: 'first strike',
  choose_hits: 'choosing casualties', retreat: 'retreat decision', retreat_air: 'aircraft retreat',
  retreat_assign: 'assigning retreats', awaiting_air_defence: 'awaiting air defence', post_capture: 'after capture',
  amphibious_declared: 'assault declared', amphibious_shore_selection: 'choosing shore bombardment',
  amphibious_shore_roll: 'shore bombardment', amphibious_shore_casualties: 'shore casualties',
  naval_attacker_fire: 'attacker fires', naval_defender_fire: 'defender fires' };
export function stageLabel(stage) {
  return STAGES[stage] || String(stage ?? '').replace(/_/g, ' ');
}
export function battleKind(battle) {
  const flags = battle?.flags || {};
  const id = String(battle?.id ?? '');
  if (flags.air_mission || id.startsWith('air_')) return 'Air mission';
  if (flags.naval_battle || id.startsWith('naval_')) return battle?.data?.context === 'port_attack' ? 'Port attack' : 'Naval battle';
  if (flags.amphibious_preparation || battle?.stage?.startsWith?.('amphibious')) return 'Amphibious assault';
  return 'Land battle';
}

// Before landing, an amphibious assault lists no combatants: its attacker is the
// landing force and bombarding ships, and its defenders are the units shore
// bombardment can hit, or else the defending nation's units in the zone.
function sideIds(battle, state, role) {
  const listed = role === 'attacker' ? battle?.attackers : battle?.defenders;
  const data = battle?.data;
  if (listed?.length || !Array.isArray(data?.cargo)) return listed;
  if (role === 'attacker') return [...data.cargo, ...(data.bombarding || [])];
  const bombarded = (data.shore_shots || []).find((shot) => shot.owner === battle.defender);
  return bombarded?.eligible ?? recordEntries(state?.units)
    .filter(([, unit]) => unit.zone === battle.zone && !unit.carried_by && ownerOf(unit) === battle.defender).map(([id]) => id);
}

/** Each side's surviving units, grouped by nation and type, from the recorded unit lists. */
export function battleSides(battle, state) {
  return [['attacker', sideIds(battle, state, 'attacker'), battle?.attacker],
    ['defender', sideIds(battle, state, 'defender'), battle?.defender]]
    .map(([role, ids, nation]) => {
      const nations = new Map();
      for (const id of ids || []) {
        const unit = state?.units?.[id];
        if (!unit) continue;
        const owner = ownerOf(unit);
        if (!nations.has(owner)) nations.set(owner, new Map());
        const types = nations.get(owner);
        types.set(unit.type, (types.get(unit.type) || 0) + 1);
      }
      return { role, nation, nations: [...nations].map(([owner, types]) => ({ nation: owner,
        units: [...types].map(([type, count]) => ({ type, count })) })) };
    });
}

export function activeBattles(state) {
  return recordEntries(state?.battles).filter(([, battle]) => fighting(battle)).map(([id, battle]) => ({
    id, kind: battleKind(battle), zone: battle.zone, attacker: battle.attacker, defender: battle.defender,
    stage: battle.data?.rolling_phase ?? battle.stage, round: battle.data?.round ?? null,
    sides: battleSides(battle, state) }));
}

// Shore shots name the side that takes the hit. The engine adds one die per
// bombarding ship in the battle's bombarding order, so ships match dice when the
// counts agree, then coastal artillery fires at the landing ships.
function shoreFirers(battle, shots, units) {
  const ships = (battle.data?.bombarding || []).filter((id) => units?.[id]);
  const bombardment = shots.filter((shot) => shot.owner === battle.defender).length;
  let next = 0;
  return shots.map((shot) => {
    if (shot.owner !== battle.defender) return { unit: null, type: 'coastal_artillery', nation: battle.defender, side: 'defender' };
    const unit = bombardment === ships.length ? ships[next++] : null;
    return { unit, type: null, nation: unit ? ownerOf(units[unit]) : battle.attacker, side: 'attacker' };
  });
}

/** A dice event as recorded: its purpose, roller, faces and, in battles, who fired each die. */
export function diceReport(step, before, replay) {
  const request = step?.chance?.request;
  if (!request) return null;
  const outcome = (step.chance.events || []).find((event) => event.kind === 'chance')?.payload?.outcome;
  const dice = (request.dice || []).map((die, index) => {
    const faces = outcome?.faces?.[index] || [];
    const modifier = Number(die.modifier || 0);
    return { sides: die.sides, modifier, faces,
      effective: faces.length ? Number(faces[faces.length - 1]) + modifier : null };
  });
  const report = { purpose: request.purpose, label: rollLabel(request.purpose, replay), roller: request.nation,
    battleId: request.continuation, dice, battle: null };
  const battle = before?.battles?.[request.continuation];
  if (!battle) return report;
  const shots = battle.data?.[SHOT_KEYS[request.purpose]];
  // A die maps to a shot only when the battle recorded exactly one shot per die.
  const mapped = Array.isArray(shots) && shots.length === dice.length;
  const firers = mapped && request.purpose === 'naval_shore_roll' ? shoreFirers(battle, shots, before.units) : null;
  report.dice = dice.map((die, index) => {
    const shot = mapped ? shots[index] : null;
    if (!shot) return die;
    const firer = firers?.[index];
    const unitId = firer ? firer.unit : shot.unit ?? null;
    const unit = unitId ? before.units?.[unitId] : null;
    const threshold = Number.isFinite(Number(shot.threshold)) ? Number(shot.threshold) : null;
    const side = firer ? firer.side : typeof shot.victim_attacker === 'boolean' ? (shot.victim_attacker ? 'defender' : 'attacker')
      : shot.target === 'defender' ? 'attacker' : shot.target === 'attacker' ? 'defender' : null;
    const target = Number(shot.target);
    return { ...die, unitId, unitType: unit?.type ?? firer?.type ?? null,
      nation: firer ? firer.nation : shot.nation ?? shot.owner ?? ownerOf(unit) ?? null, side, threshold,
      hit: threshold !== null && die.effective !== null ? die.effective <= threshold : null,
      targeted: Number.isFinite(target) && target > 0 && die.effective !== null && die.effective <= target };
  });
  report.battle = { id: request.continuation, kind: battleKind(battle), zone: battle.zone,
    attacker: battle.attacker, defender: battle.defender, round: battle.data?.round ?? null,
    stage: battle.data?.rolling_phase ?? battle.stage, sides: battleSides(battle, before) };
  report.hits = mapped ? report.dice.filter((die) => die.hit).length : null;
  return report;
}

function chanceSummary(step, replay) {
  const request = step.chance?.request;
  if (!request) return 'Dice event resolved';
  const battle = step.changes?.battles?.[request.continuation];
  const outcome = (step.chance.events || []).find((event) => event.kind === 'chance')?.payload?.outcome;
  const faces = (outcome?.faces || []).map((die) => die.join('→')).join(' ');
  const count = request.dice?.length || 0;
  // Battle dice are requested by the turn's nation even when defenders fire,
  // so only rolls outside battles name who rolled.
  const inBattle = Boolean(battle) || /battle|air_mission/.test(String(request.continuation));
  return `${rollLabel(request.purpose, replay)}${battle?.zone ? ` at ${displayName(battle.zone, replay)}` : ''} · ${inBattle ? '' : `${displayName(request.nation, replay)} rolls `}${count} ${count === 1 ? 'die' : 'dice'}${faces ? `: ${faces}` : ''}`;
}

export function eventSummary(step, replay) {
  if (!step) return 'Initial campaign position';
  const action = step.action || {};
  const summary = step.kind === 'chance' ? chanceSummary(step, replay) : step.summary ? String(step.summary)
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
