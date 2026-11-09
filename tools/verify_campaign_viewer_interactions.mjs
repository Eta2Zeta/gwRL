/** Isolated transport/interaction regression checks; no browser or server starts. */
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import * as model from '../web/campaign_viewer/model.js';
import * as layout from '../web/campaign_viewer/map-layout.js';

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
  getBoundingClientRect() { return { left: 30, top: 80, width: 1150, height: 700 }; }
  setPointerCapture(pointer) { this.capturedPointer = pointer; }
  get firstChild() { return this.childNodes[0]; }
}

const elements = new Map();
const getElement = (id) => {
  if (!elements.has(id)) elements.set(id, new FakeElement());
  return elements.get(id);
};
getElement('map').append(getElement('board-art'), getElement('map-overlays'));
const timers = new Map();
let nextTimer = 0;
const requests = [];
const responses = [];
const context = vm.createContext({
  ...model, ...layout, console, URL, Blob,
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
  .replace(/^import\s+\{[^}]+\}\s+from '\.\/(model|map-layout)\.js';\s*/gm, '')
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

// Dispatch the real controls against a viewport with margins and a page offset.
const map = getElement('map');
const viewBox = () => map.getAttribute('viewBox').split(' ').map(Number);
const { BOARD_WIDTH: boardWidth, BOARD_HEIGHT: boardHeight } = layout;
const fit = [0, 0, boardWidth, boardHeight];
const pointer = (id, x, y) => ({ pointerId: id, clientX: x, clientY: y, button: 0 });
function worldPoint(clientX, clientY) {
  const [x, y, w, h] = viewBox();
  const rect = map.getBoundingClientRect();
  const scale = Math.min(rect.width / w, rect.height / h);
  return [x + (clientX - rect.left - (rect.width - w * scale) / 2) / scale,
    y + (clientY - rect.top - (rect.height - h * scale) / 2) / scale];
}
const near = (actual, expected, why) => assert.ok(Math.abs(actual - expected) < 0.000001,
  `${why}: expected ${expected}, got ${actual}`);

// A wheel zoom preserves the point under an off-center cursor, including on
// letterboxed layouts. A trackpad pinch that sends ctrl-wheel uses this path.
const anchor = worldPoint(425, 420);
let prevented = false;
map.listeners.wheel({ clientX: 425, clientY: 420, deltaY: -200, deltaMode: 0,
  preventDefault() { prevented = true; } });
assert.ok(prevented);
assert.ok(UI.zoom > 1);
const afterWheel = worldPoint(425, 420);
near(afterWheel[0], anchor[0], 'Wheel zoom keeps cursor longitude');
near(afterWheel[1], anchor[1], 'Wheel zoom keeps cursor latitude');

for (let index = 0; index < 20; index += 1) getElement('zoom-in').listeners.click();
assert.equal(UI.zoom, 8, 'Zoom cannot exceed 8×');
assert.deepEqual(viewBox().slice(2), [boardWidth / 8, boardHeight / 8]);
assert.equal(getElement('zoom-in').disabled, true);
map.listeners.pointerdown(pointer(7, 300, 300));
assert.equal(map.capturedPointer, undefined, 'An ordinary location click is not captured');
map.listeners.pointermove(pointer(7, 100000, -100000));
assert.equal(map.capturedPointer, 7, 'Dragging captures its pointer after a movement threshold');
map.listeners.pointerup({ pointerId: 7 });
assert.deepEqual(viewBox(), [0, boardHeight * 7 / 8, boardWidth / 8, boardHeight / 8],
  'Panning remains inside the full map');
const panned = viewBox();
UI.selected = 'land_china_hopeh';
seek(1);
assert.deepEqual(viewBox(), panned, 'Seeking preserves the pan and zoom');
assert.equal(UI.selected, 'land_china_hopeh', 'Seeking preserves selected location');
getElement('reset-view').listeners.click();
assert.deepEqual(viewBox(), fit, 'Reset restores the full map');
for (let index = 0; index < 20; index += 1) getElement('zoom-out').listeners.click();
assert.equal(UI.zoom, 1, 'Zoom cannot fall below the full map');
assert.equal(getElement('zoom-out').disabled, true);

const pinchAnchor = worldPoint(550, 400);
map.listeners.pointerdown(pointer(1, 500, 400));
map.listeners.pointerdown(pointer(2, 600, 400));
map.listeners.lostpointercapture({ target: getElement('map-overlays'), pointerId: 2 });
map.listeners.pointermove(pointer(2, 700, 400));
near(UI.zoom, 2, 'Two-finger spread doubles magnification');
const midpoint = worldPoint(600, 400);
near(midpoint[0], pinchAnchor[0], 'Pinch midpoint translates along with zoom');
near(midpoint[1], pinchAnchor[1], 'Pinch midpoint stays over same board point');
map.listeners.pointerup({ pointerId: 2 });
const pinchedView = viewBox();
map.listeners.pointermove(pointer(1, 515, 430));
assert.ok(viewBox()[0] < pinchedView[0] && viewBox()[1] < pinchedView[1],
  'The remaining finger can pan after a pinch');
map.listeners.pointercancel({ pointerId: 1 });
assert.equal(UI.pointers.size, 0);
assert.ok(UI.suppressClickUntil > Date.now(), 'Pinching must not select a location');

function mapKey(key, target = map) {
  map.listeners.keydown({ target, key, preventDefault() {}, stopPropagation() {} });
}
const beforeKey = viewBox();
mapKey('ArrowRight');
assert.ok(viewBox()[0] > beforeKey[0], 'Keyboard pans the focused map');
mapKey('+', getElement('map-overlays').childNodes.at(-1));
assert.ok(UI.zoom > 2, 'A focused location can zoom the map');
mapKey('0');
assert.deepEqual(viewBox(), fit, 'Keyboard fit restores the board');

// Old exported replays get their anchors from the board layout. Their own
// scenario still supplies the actual adjacency and any movement route.
const scenario = JSON.parse(fs.readFileSync(
  new URL('../game_content/scenarios/japan_china_1936/map.json', import.meta.url), 'utf8'));
assert.deepEqual(Object.keys(layout.BOARD_POSITIONS).sort(), Object.keys(scenario.nodes).sort());
const route = ['land_formosa', 'sea_p32', 'sea_p14'];
const fighter = { id: 'plane', type: 'fighter', owner: 'japan', zone: route[0] };
loadReplay({ ...replay, map: scenario, initial: { ...replay.initial, units: { plane: fighter } },
  steps: [{ kind: 'action', action: { parameters: { path: route } },
    changes: { units: { upsert: { plane: { ...fighter, zone: route[2] } }, remove: [] } } }] });
const overlays = getElement('map-overlays');
function descendants(node) {
  return (node.childNodes || []).flatMap((child) => [child, ...descendants(child)]);
}
const nodesWith = (className) => descendants(overlays).filter((item) =>
  item.getAttribute?.('class')?.split(/\s+/).includes(className));
function validateLocationAnchors() {
  const nodes = nodesWith('map-node');
  assert.equal(nodes.length, Object.keys(scenario.nodes).length);
  for (const node of nodes) {
    const id = node.getAttribute('data-location');
    const [x, y] = layout.BOARD_POSITIONS[id];
    assert.ok(x > 0 && x < boardWidth && y > 0 && y < boardHeight, `Anchor on board for ${id}`);
    const translate = node.getAttribute('transform').match(/^translate\(([^)]+)\)/);
    assert.deepEqual(translate[1].trim().split(/[ ,]+/).map(Number), [x, y], `Map coordinates for ${id}`);
  }
}
validateLocationAnchors();
getElement('show-connections').listeners.change({ target: { checked: true } });
const connections = nodesWith('map-connection');
assert.ok(connections.some((edge) => {
  const endpoints = ['1','2'].map((n) => [Number(edge.getAttribute('x' + n)), Number(edge.getAttribute('y' + n))]);
  return ['land_formosa', 'sea_p32'].every((id) =>
    endpoints.some(([x, y]) => x === layout.BOARD_POSITIONS[id][0] && y === layout.BOARD_POSITIONS[id][1]));
}), 'A scenario connection joins the actual Formosa and P32 anchors');
seek(1);
assert.deepEqual(map.childNodes, [getElement('board-art'), overlays], 'The board image persists behind replay overlays');
const movement = nodesWith('movement-line');
assert.equal(movement.length, 1);
const coordinates = movement[0].getAttribute('d').match(/[MLQ][^MLQ]+/gi).map((leg) =>
  leg.slice(1).trim().split(/[ ,]+/).map(Number).slice(-2));
assert.deepEqual(coordinates, route.map((id) => layout.BOARD_POSITIONS[id]), 'Movement follows all actual route anchors');
getElement('zoom-in').listeners.click();
validateLocationAnchors();
getElement('show-connections').listeners.change({ target: { checked: false } });

// At phone fit, hit targets should remain legible and separately selectable.
const previousBounds = map.getBoundingClientRect;
map.getBoundingClientRect = () => ({ left:0, top:0, width:360, height:360*boardHeight/boardWidth });
mapKey('0');
const fitScale = 360 / boardWidth;
const rectangles = [];
for (const item of nodesWith('map-node')) {
  const [x, y] = layout.BOARD_POSITIONS[item.getAttribute('data-location')];
  const symbol = item.childNodes.find((child) => child.getAttribute?.('transform')?.startsWith('scale('));
  const scale = Number(symbol.getAttribute('transform').slice(6, -1)) * fitScale;
  const card = symbol.childNodes.find((child) => child.getAttribute('data-size'));
  const [dx, dy] = card.getAttribute('transform').slice(10, -1).split(',').map(Number);
  const face = card.childNodes.find((child) => child.getAttribute('class') === 'node-card');
  const left = x * fitScale + dx * scale, top = y * fitScale + dy * scale;
  const width = Number(face.getAttribute('width')) * scale, height = Number(face.getAttribute('height')) * scale;
  assert.ok(height >= 24 - 1e-6 && width >= 24 - 1e-6, 'The map target is at least 24 CSS pixels');
  assert.ok(rectangles.every((r) => left >= r.right || top >= r.bottom ||
    left + width <= r.left || top + height <= r.top), 'Phone labels have separate click targets');
  rectangles.push({ left, top, right:left+width, bottom:top+height });
}
map.getBoundingClientRect = previousBounds;

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
