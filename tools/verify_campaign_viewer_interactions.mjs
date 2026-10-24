/** Isolated transport/interaction regression checks; no browser or server starts. */
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import * as model from '../web/campaign_viewer/model.js';

class FakeElement {
  constructor() {
    this.childNodes = [];
    this.listeners = {};
    this.value = '';
    this.checked = false;
    this.disabled = false;
    this.attributes = {};
    this.style = { setProperty() {} };
  }
  append(...nodes) { this.childNodes.push(...nodes); }
  replaceChildren(...nodes) { this.childNodes = [...nodes]; }
  addEventListener(name, listener) { this.listeners[name] = listener; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return this.attributes[name] ?? null; }
  getBoundingClientRect() { return { width: 1400, height: 1000 }; }
  setPointerCapture(pointer) { this.capturedPointer = pointer; }
  get firstChild() { return this.childNodes[0]; }
}

const elements = new Map();
const getElement = (id) => {
  if (!elements.has(id)) elements.set(id, new FakeElement());
  return elements.get(id);
};
const timers = new Map();
let nextTimer = 0;
const requests = [];
const responses = [];
const context = vm.createContext({
  ...model, console, URL, Blob,
  history: { replaceState() {} },
  document: {
    getElementById: getElement,
    createElement: () => new FakeElement(),
    createElementNS: () => new FakeElement(),
    createTextNode: (text) => ({ textContent: text }),
    addEventListener() {},
  },
  window: {
    location: { href: 'http://localhost:8765/' },
    setTimeout(callback) { timers.set(++nextTimer, callback); return nextTimer; },
    clearTimeout(id) { timers.delete(id); },
  },
  fetch: async (url, options) => {
    requests.push([url, options]);
    assert.ok(responses.length, `Unexpected HTTP request: ${url}`);
    return responses.shift();
  },
});

// Run the actual app functions against a minimal DOM. Suppress only its startup
// dispatch, so tests explicitly control response ordering and do no real I/O.
const source = fs.readFileSync(new URL('../web/campaign_viewer/app.js', import.meta.url), 'utf8')
  .replace(/^import[\s\S]*?from '\.\/model\.js';\n/, '')
  .replace(/if \(globalThis\.CAMPAIGN_REPLAY\)[\s\S]*$/, '');
vm.runInContext(`${source}\nglobalThis.testApi = {
  UI, fetchRecording, refreshRecording, loadReplay, renderSearch, seek
};`, context);
const { UI, fetchRecording, refreshRecording, loadReplay, renderSearch, seek } = context.testApi;
const response = (status, data, etag = null) => ({
  status, ok: status >= 200 && status < 300,
  json: async () => data,
  headers: { get: () => etag },
});

responses.push(response(503));
await fetchRecording('live-next');
assert.equal(UI.sourceId, 'live-next');
assert.equal(UI.replay, null);
assert.equal(getElement('refresh').disabled, false);
assert.equal(getElement('follow-latest').disabled, false);
assert.equal(timers.size, 0, 'No polling until Follow is enabled');

getElement('follow-latest').checked = true;
responses.push(response(503));
await refreshRecording();
assert.ok(timers.size, 'Follow retries an episode not yet recorded');

const replay = {
  schema: 'campaign-replay-v1',
  map: { nodes: { land_china_hopeh: { name: 'Hopeh', type: 'land' } } },
  factions: {},
  metadata: { origin: 'training self-play', live_status: 'active' },
  initial: {
    clock: { round_index: 0 }, units: {},
    territories: { land_china_hopeh: { possessor: 'kmt' } },
  },
  steps: [
    { kind: 'action', changes: {}, action: { id: 'one' } },
    { kind: 'chance', changes: {}, chance: { faces: [3] } },
  ],
};
responses.push(response(200, replay, '"one"'));
await refreshRecording();
assert.equal(UI.position, 2, 'Follow loads the awaited episode at its tail');
assert.equal(UI.replaySourceId, 'live-next');

getElement('follow-latest').checked = false;
seek(1);
UI.selected = 'land_china_hopeh';
responses.push(response(304));
await refreshRecording();
assert.equal(UI.position, 1);
assert.equal(UI.selected, 'land_china_hopeh');
assert.equal(requests.at(-1)[1].headers['If-None-Match'], '"one"');
assert.equal(timers.size, 0, 'Manual refresh does not enable polling');

const updated = JSON.parse(JSON.stringify(replay));
updated.steps.push({ kind: 'action', changes: {}, action: { id: 'three' } });
responses.push(response(200, updated, '"two"'));
await refreshRecording();
assert.equal(UI.position, 1, 'Manual refresh preserves the selected position');
assert.equal(UI.selected, 'land_china_hopeh', 'Manual refresh preserves location selection');
renderSearch();
assert.match(getElement('search-caption').textContent, /dice resolution/,
  'A pending dice event cannot show a later action’s search');
seek(3);
assert.equal(getElement('search-caption').textContent, 'No further recorded decisions');

loadReplay(replay);
assert.equal(getElement('refresh').disabled, true);
assert.equal(getElement('follow-latest').disabled, true);
assert.equal(getElement('follow-latest').checked, false);
assert.equal(timers.size, 0, 'A standalone/local file cannot keep HTTP polling');
assert.equal(responses.length, 0);

// Dispatch real controls / pointer handlers, checking the actual SVG viewBox.
const map = getElement('map');
const viewBox = () => map.getAttribute('viewBox').split(' ').map(Number);
for (let index = 0; index < 20; index += 1) getElement('zoom-in').listeners.click();
assert.equal(UI.zoom, 4, 'Zoom cannot exceed 4×');
assert.deepEqual(viewBox().slice(2), [350, 250]);
assert.equal(getElement('zoom-in').disabled, true);
map.listeners.pointerdown({ button: 0, pointerId: 7, clientX: 100, clientY: 100 });
assert.equal(map.capturedPointer, undefined, 'An ordinary location click is not captured');
map.listeners.pointermove({ pointerId: 7, clientX: 100000, clientY: -100000 });
assert.equal(map.capturedPointer, 7, 'Dragging captures its pointer after a movement threshold');
map.listeners.pointerup({ pointerId: 7 });
assert.deepEqual(viewBox(), [0, 750, 350, 250], 'Panning remains inside the full map');
const panned = viewBox();
UI.selected = 'land_china_hopeh';
seek(1);
assert.deepEqual(viewBox(), panned, 'Seeking preserves the pan and zoom');
assert.equal(UI.selected, 'land_china_hopeh', 'Seeking preserves selected location');
getElement('reset-view').listeners.click();
assert.deepEqual(viewBox(), [0, 0, 1400, 1000], 'Reset restores the full map');
for (let index = 0; index < 20; index += 1) getElement('zoom-out').listeners.click();
assert.equal(UI.zoom, 1, 'Zoom cannot fall below the full map');
assert.equal(getElement('zoom-out').disabled, true);

// Native finished battles remain in snapshots for audit history, but are not
// active combats. Repair jobs resolve their target or rail endpoint location.
const inspectorFixture = JSON.parse(JSON.stringify(replay));
Object.assign(inspectorFixture.initial, {
  battles: {
    past: { id: 'past', zone: 'land_china_hopeh', stage: 'finished', attacker: 'japan', defender: 'kmt' },
    current: { id: 'current', zone: 'land_china_hopeh', stage: 'defender_fire', attacker: 'ccp', defender: 'kmt' },
  },
  facilities: {
    facility_here: { id: 'facility_here', zone: 'land_china_hopeh', type: 'airbase' },
    facility_elsewhere: { id: 'facility_elsewhere', zone: 'elsewhere', type: 'airbase' },
  },
  units: { unit_here: { id: 'unit_here', zone: 'land_china_hopeh', owner: 'kmt', type: 'infantry' } },
  repairs: {
    repair_facility: { id: 'repair_facility', target: 'facility_here', remaining_cost: 1 },
    repair_unit: { id: 'repair_unit', target: 'unit_here', remaining_cost: 2 },
    repair_rail: { id: 'repair_rail', target: 'rail_1', endpoint: 'land_china_hopeh', remaining_cost: 3 },
    repair_elsewhere: { id: 'repair_elsewhere', target: 'facility_elsewhere', remaining_cost: 4 },
  },
});
loadReplay(inspectorFixture);
UI.selected = 'land_china_hopeh';
seek(0);
const textOf = (node) => [node.textContent || '', ...(node.childNodes || []).map(textOf)].join(' ');
const inspectorText = textOf(getElement('location-details'));
assert.match(getElement('politics-status').textContent, /1 active battle/);
assert.match(inspectorText, /CCP attacks KMT/);
assert.doesNotMatch(inspectorText, /Japan attacks KMT/);
assert.match(inspectorText, /Repair Facility/);
assert.match(inspectorText, /Repair Unit/);
assert.match(inspectorText, /Repair Rail/);
assert.doesNotMatch(inspectorText, /Repair Elsewhere/);
// Possession changes must remain visible as actual game history, rather than
// making an initially independent warlord look like starting KMT territory.
const tsinghai = 'land_china_tsinghai';
const ownershipFixture = {
  schema:'campaign-replay-v1', metadata:{},
  map:{nodes:{[tsinghai]:{name:'Tsinghai',type:'land',original_owner:'Ma Clique',current_owner:'Ma Clique',ipp_value:0}}},
  factions:{warlord_tsinghai:{name:'Ma Clique'},kmt:{name:'KMT'},ccp:{name:'CCP'}},
  initial:{clock:{round_index:0},territories:{[tsinghai]:{possessor:'warlord_tsinghai'}},
    nations:{warlord_tsinghai:{game_flags:{}}},politics:{attacked_warlords:{}}},
  steps:[
    {kind:'action',summary:'CCP attacks Tsinghai',changes:{politics:{attacked_warlords:{warlord_tsinghai:['ccp']}}}},
    {kind:'action',summary:'Flags only',changes:{territories:{upsert:{[tsinghai]:{possessor:'warlord_tsinghai',flags:{test:true}}},remove:[]}}},
    {kind:'action',summary:'Finish combat',changes:{
      territories:{upsert:{[tsinghai]:{possessor:'kmt'}},remove:[]},
      nations:{upsert:{warlord_tsinghai:{game_flags:{incorporated:1},controller_nation:'kmt'}},remove:[]},
      politics:{attacked_warlords:{}}}},
    {kind:'action',summary:'Surrender',changes:{territories:{upsert:{[tsinghai]:{possessor:null}},remove:[]}}},
  ],
};
loadReplay(ownershipFixture);
UI.selected=tsinghai;
seek(0);
assert.match(textOf(getElement('map')),/Ma Clique · 0 IPP/);
assert.match(textOf(getElement('location-details')),/Current possessor: Ma Clique/);
seek(3);
assert.match(textOf(getElement('map')),/KMT · originally Ma Clique/);
assert.match(textOf(getElement('location-details')),/Starting possessor: Ma Clique/);
assert.match(textOf(getElement('location-details')),/alignment after CCP attack/);
assert.match(getElement('event-summary').textContent,/Tsinghai: Ma Clique → KMT/);
getElement('event-filter').value='ownership';seek(3);
assert.match(textOf(getElement('event-list')),/Ma Clique → KMT/);
assert.doesNotMatch(textOf(getElement('event-list')),/Flags only/);
seek(4);
assert.match(textOf(getElement('map')),/Unpossessed/);
assert.match(textOf(getElement('location-details')),/Unpossessed/);
seek(0);
assert.match(textOf(getElement('map')),/Ma Clique · 0 IPP/);
assert.doesNotMatch(textOf(getElement('location-details')),/KMT/,'Initial inspector cannot show later possession');
console.log('Campaign viewer interaction checks passed, including original nationality, alignment history and unpossessed land');
