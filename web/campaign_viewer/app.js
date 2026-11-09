import { createReplayModel, displayName, eventSummary, factionColor, locationOf,
  ownerOf, recordEntries, changedLocations, territoryIdentity, possessionChanges,
  possessionChangeText, diceReport, activeBattles, stageLabel, politicalStatus, movementPath,
  movementStops } from './model.js';
import { BOARD_WIDTH, BOARD_HEIGHT, BOARD_POSITIONS } from './map-layout.js';

const $ = (id) => document.getElementById(id);
const SVG = 'http://www.w3.org/2000/svg';
const MAX_MAP_ZOOM = 8;
const UI = { replay: null, model: null, position: 0, state: null, selected: null,
  playing: false, timer: null, showConnections: false, catalog: [], loadToken: 0,
  sourceId: null, replaySourceId: null, etag: null, followTimer: null, refreshInFlight: false,
  zoom: 1, view: { x: 0, y: 0, width: BOARD_WIDTH, height: BOARD_HEIGHT },
  pointers: new Map(), mapDragging: false, suppressClickUntil: 0 };
const present = (value) => value !== null && value !== undefined && value !== '';
const number = (value, digits = 0) => present(value) && Number.isFinite(Number(value))
  ? Number(value).toLocaleString(undefined, { maximumFractionDigits: digits }) : '—';
const percent = (value) => present(value) && Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(1)}%` : '—';
const human = (value) => displayName(value, UI.replay);
let mapLabels = [];
let lastMapScale = 0;
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}
function svgElement(tag, attributes = {}, text) {
  const node = document.createElementNS(SVG, tag);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
  if (text !== undefined) node.textContent = String(text);
  return node;
}
function notice(message = '') {
  $('notice').textContent = message;
  $('notice').hidden = !message;
}
function positionFor(id, index = 0) {
  if (Object.hasOwn(BOARD_POSITIONS, id)) return BOARD_POSITIONS[id];
  const custom = UI.replay?.map?.nodes?.[id]?.display_position;
  if (Array.isArray(custom) && custom.length === 2 && custom.every(Number.isFinite)) return custom;
  return [120 + (index % 7) * 180, 110 + Math.floor(index / 7) * 150];
}
function clockText(clock) {
  if (!clock) return '—';
  const round = Number(clock.round_index ?? 0);
  const date = new Date(Date.UTC(1936, 6 + round * 6, 1));
  return `${date.toLocaleDateString('en', { month: 'short', year: 'numeric', timeZone: 'UTC' })} · Round ${round + 1}`;
}
function phaseText(value) {
  return String(value ?? '—').replace(/([a-z])([A-Z])/g, '$1 $2').replace(/_/g, ' ');
}
function stop() {
  UI.playing = false;
  window.clearTimeout(UI.timer);
  $('play').textContent = '▶';
  $('play').setAttribute('aria-label', 'Play replay');
}
function schedule() {
  window.clearTimeout(UI.timer);
  if (!UI.playing) return;
  UI.timer = window.setTimeout(() => {
    if (UI.position >= UI.replay.steps.length) { stop(); return; }
    seek(UI.position + 1);
    schedule();
  }, Number($('speed').value));
}
function togglePlay() {
  if (!UI.replay) return;
  if (UI.playing) { stop(); return; }
  if (UI.position >= UI.replay.steps.length) seek(0);
  UI.playing = true;
  $('play').textContent = 'Ⅱ';
  $('play').setAttribute('aria-label', 'Pause replay');
  schedule();
}
function seek(position) {
  if (!UI.model) return;
  UI.position = Math.max(0, Math.min(UI.replay.steps.length, Number(position)));
  UI.state = UI.model.seek(UI.position);
  const before = UI.position ? UI.model.seek(UI.position - 1) : UI.state;
  // Restore the seek cache's current position after obtaining the prior event.
  UI.model.seek(UI.position);
  const changed = changedLocations(before, UI.state);
  const step = UI.replay.steps[UI.position - 1];
  UI.dice = step?.kind === 'chance' ? diceReport(step, before, UI.replay) : null;
  renderClock(); renderMap(changed, before); renderInspector(); renderLedger();
  renderPlayback(); renderCombat(); renderPolitics(before); renderSearch(); renderEvents();
  if (UI.position === UI.replay.steps.length && UI.playing) stop();
}
function renderClock() {
  const state = UI.state;
  $('clock').textContent = clockText(state.clock);
  $('phase').textContent = phaseText(state.clock?.phase);
  const nation = human(state.current_nation);
  const player = human(state.decision_player ?? state.decisions?.player);
  $('decision-owner').textContent = state.terminal ? 'Campaign finished'
    : `${player}${nation !== '—' ? ` · ${nation}’s calendar turn` : ''}`;
  $('decision-kind').textContent = state.terminal ? '' : phaseText(state.decision_kind);
  const truce=state.politics?.chinese_truce;
  const battles=recordEntries(state.battles).filter(([,battle])=>battle.stage!=='finished').length;
  $('politics-status').textContent=[`Chinese Truce: ${truce ? 'active' : 'not active'}`,`${battles} active ${battles===1?'battle':'battles'}`,state.politics?.surrendered?.length?`Surrendered: ${state.politics.surrendered.map(human).join(', ')}`:''].filter(Boolean).join(' · ');
  $('position-count').textContent = `${number(UI.position)} / ${number(UI.replay.steps.length)}`;
}
function unitsAt(id) {
  return recordEntries(UI.state.units).map(([, record]) => record).filter((record) => locationOf(record) === id);
}
// The SVG fits its viewBox with xMidYMid meet. Account for the margins when
// converting pointer coordinates in CSS pixels to positions on the board.
function mapViewport() {
  const rect = $('map').getBoundingClientRect();
  const scale = Math.min(rect.width / UI.view.width, rect.height / UI.view.height) || 1;
  return { scale, left: rect.left + (rect.width - UI.view.width * scale) / 2,
    top: rect.top + (rect.height - UI.view.height * scale) / 2 };
}

function updateMapView() {
  const view = UI.view;
  $('map').setAttribute('viewBox', `${view.x} ${view.y} ${view.width} ${view.height}`);
  $('map').style.cursor = UI.mapDragging ? 'grabbing' : UI.zoom > 1 ? 'grab' : '';
  $('zoom-level').textContent = `${Math.round(UI.zoom * 100)}%`;
  $('zoom-out').disabled = UI.zoom <= 1;
  $('zoom-in').disabled = UI.zoom >= MAX_MAP_ZOOM;
  layoutMapNodes();
}

function setMapView(zoom, x, y) {
  const width = BOARD_WIDTH / zoom;
  const height = BOARD_HEIGHT / zoom;
  UI.view = { x: Math.max(0, Math.min(BOARD_WIDTH - width, x)),
    y: Math.max(0, Math.min(BOARD_HEIGHT - height, y)), width, height };
  UI.zoom = zoom;
  updateMapView();
}

// A wheel or button keeps one point fixed. A drag or pinch can move that
// point between frames, so its old board coordinate must land under 'to'.
function zoomMap(factor, from, to = from) {
  const zoom = Math.max(1, Math.min(MAX_MAP_ZOOM, UI.zoom * factor));
  const { left, top, scale } = mapViewport();
  if (!from) {
    from = to = { x: left + UI.view.width * scale / 2, y: top + UI.view.height * scale / 2 };
  }
  const nextScale = scale * zoom / UI.zoom;
  const x = UI.view.x + (from.x - left) / scale - (to.x - left) / nextScale;
  const y = UI.view.y + (from.y - top) / scale - (to.y - top) / nextScale;
  setMapView(zoom, x, y);
}

function resetMapView() {
  UI.pointers.clear();
  UI.mapDragging = false;
  setMapView(1, 0, 0);
}
function renderMap(changed = new Set(), before = null) {
  const map = $('map-overlays');
  map.replaceChildren();
  mapLabels = [];
  lastMapScale = 0;
  const nodes = recordEntries(UI.replay.map.nodes);
  const indexes = new Map(nodes.map(([id], index) => [id,index]));
  const fighting = new Set(activeBattles(UI.state).map((battle) => battle.zone));
  if (UI.dice?.battle?.zone) fighting.add(UI.dice.battle.zone);
  if (UI.showConnections) {
    const edges = new Set();
    for (const [id, node] of nodes) {
      for (const link of node.neighbors || []) {
        const other = typeof link === 'string' ? link : link.neighbor_id ?? link.id;
        if (!indexes.has(other) || link.passable === false) continue;
        const key = [id,other].sort().join('|');
        if (edges.has(key)) continue;
        edges.add(key);
        const [x1,y1] = positionFor(id,indexes.get(id));
        const [x2,y2] = positionFor(other,indexes.get(other));
        map.append(svgElement('line', { x1,y1,x2,y2,class:`map-connection${id.startsWith('sea_') || other.startsWith('sea_') ? ' sea' : ''}` }));
      }
    }
  }
  if (before) {
    const route = movementPath(UI.replay.steps[UI.position-1]);
    const movements = new Set();
    for (const [id, unit] of recordEntries(UI.state.units)) {
      const old = locationOf(before.units?.[id]); const next = locationOf(unit);
      if (old && next && old !== next && indexes.has(old) && indexes.has(next)) {
        const stops = movementStops(route,old,next).filter((zone) => indexes.has(zone));
        const key = stops.join('|');
        if (movements.has(key)) continue;
        movements.add(key);
        const points = stops.map((zone) => positionFor(zone,indexes.get(zone)));
        const legs = points.slice(1).map(([x2,y2],index) => {
          const [x1,y1] = points[index];
          return `Q ${(x1+x2)/2+15} ${(y1+y2)/2-28} ${x2} ${y2}`;
        });
        const d = `M ${points[0][0]} ${points[0][1]} ${legs.join(' ')}`;
        map.append(svgElement('path', { d, class:'movement-casing' }),
          svgElement('path', { d, class:'movement-line' }));
      }
    }
  }
  for (const [index, [id,node]] of nodes.entries()) {
    const [x, y] = positionFor(id, index);
    const name = node.name || id;
    const identity = territoryIdentity(id, UI.state, UI.replay);
    const sea = node.type === 'sea' || id.startsWith('sea_');
    const subtitle = sea ? 'Sea zone' : identity.subtitle;
    const units = unitsAt(id);
    const counts = new Map();
    for (const unit of units) {
      const nation = ownerOf(unit);
      counts.set(nation, (counts.get(nation) || 0) + 1);
    }
    const stacks = [...counts].sort((a, b) => b[1] - a[1]);
    const description = `${name} · ${subtitle} · ${units.length} units`;
    const inBattle = fighting.has(id);
    const isChanged = changed.has(id);
    const group = svgElement('g', { transform:`translate(${x},${y})`, class:
      `map-node${sea ? ' sea-node' : ''}${inBattle ? ' battle' : ''}${isChanged ? ' changed' : ''}`,
      tabindex:0, role:'button', 'aria-label':description, 'data-location':id, 'aria-pressed':id === UI.selected });
    const color = sea ? '#426975' : factionColor(identity.owner);
    const symbol = svgElement('g');
    const leader = svgElement('line', { class:'map-leader' });
    const pin = svgElement('circle', { r:3, class:'board-pin', fill:color });
    const card = svgElement('g');
    symbol.append(leader, pin, card);
    group.append(svgElement('title', {}, description), symbol);
    const label = { id, x, y, name, subtitle, color, total:units.length, stacks, inBattle,
      isCity:node.is_city, isChanged, group, symbol, card, leader };
    const select = () => {
      if (Date.now() < UI.suppressClickUntil) return;
      UI.selected = id;
      for (const item of mapLabels) item.group.setAttribute('aria-pressed', item.id === id);
      renderInspector();
    };
    group.addEventListener('click', select);
    group.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(); }
    });
    mapLabels.push(label);
    map.append(group);
  }
  updateMapView();
}
// Measure labels in screen pixels. Their pins and every replay route stay in board pixels.
function layoutMapNodes() {
  const scale = mapViewport().scale;
  if (!mapLabels.length || scale === lastMapScale) return;
  lastMapScale = scale;
  const occupied = mapLabels.map(({ x, y }) => ({
    x: x * scale - 4, y: y * scale - 4, width: 8, height: 8,
  }));
  // Give every zone a counter before spending the remaining space on names and
  // stack details. A large label can never displace another zone's counter.
  const sizes = scale >= 0.4 ? ['counter', 'compact', 'detail'] : ['counter', 'compact'];
  for (const size of sizes) {
    for (const [index, label] of mapLabels.entries()) {
      const slot = mapLabels.length + index;
      const previous = occupied[slot];
      occupied[slot] = null;
      const nameWidth = Math.ceil(label.name.length * 7.1);
      let width = nameWidth + 38;
      let height = 24;
      if (size === 'counter') width = Math.max(25, String(label.total).length * 8 + 14);
      if (size === 'detail') {
        width = Math.max(116, nameWidth + 23, Math.min(200, label.subtitle.length * 6.1 + 16));
        height = 53;
      }
      const box = placeMapLabel(label.x * scale, label.y * scale, width, height, scale, occupied,
        size === 'counter' ? occupied[index] : null);
      occupied[slot] = !previous || !box.overlap ? { ...box, size } : previous;
    }
  }
  for (const [index, label] of mapLabels.entries()) {
    const box = occupied[mapLabels.length + index];
    const { width, height, size } = box;
    const x = label.x * scale;
    const y = label.y * scale;
    label.symbol.setAttribute('transform', `scale(${1 / scale})`);
    label.card.setAttribute('transform', `translate(${box.x - x},${box.y - y})`);
    label.leader.setAttribute('x2', Math.max(box.x, Math.min(x, box.x + width)) - x);
    label.leader.setAttribute('y2', Math.max(box.y, Math.min(y, box.y + height)) - y);
    if (label.size !== size) {
      drawMapLabel(label, size, width, height);
      label.size = size;
    }
  }
}

function placeMapLabel(x, y, width, height, scale, occupied, ownPin) {
  const gap = 6;
  const above = -height - gap;
  const left = -width - gap;
  const candidates = [
    [-width / 2, above], [-width / 2, gap], [gap, -height / 2], [left, -height / 2],
    [gap, above], [left, above], [gap, gap], [left, gap],
  ];
  if (ownPin) {
    candidates.unshift([-width/2, -height/2]);
    for (const distance of [14, 28, 42]) {
      candidates.push([left-distance, -height/2], [gap+distance, -height/2],
        [-width/2, above-distance], [-width/2, gap+distance],
        [left-distance, above-distance], [gap+distance, above-distance],
        [left-distance, gap+distance], [gap+distance, gap+distance]);
    }
  }
  let best;
  for (const [dx, dy] of candidates) {
    const bx = Math.max(2, Math.min(x + dx, BOARD_WIDTH * scale - width - 2));
    const by = Math.max(2, Math.min(y + dy, BOARD_HEIGHT * scale - height - 2));
    let overlap = 0;
    for (const other of occupied) {
      if (!other || other === ownPin) continue;
      const w = Math.min(bx + width + 2, other.x + other.width) - Math.max(bx - 2, other.x);
      const h = Math.min(by + height + 2, other.y + other.height) - Math.max(by - 2, other.y);
      overlap += Math.max(0, w) * Math.max(0, h);
    }
    if (!best || overlap < best.overlap) best = { x: bx, y: by, width, height, overlap };
    if (!overlap) break;
  }
  return best;
}

function drawMapLabel(label, size, width, height) {
  const { card, name, color, total, stacks } = label;
  card.replaceChildren();
  card.setAttribute('data-size', size);
  if (label.isChanged) card.append(svgElement('rect', { x:-3, y:-3, width:width+6, height:height+6, rx:7, class:'change-ring' }));
  card.append(svgElement('rect', { width, height, rx:4, class:'node-card' }),
    svgElement('rect', { x:2, y:3, width:3, height:height-6, rx:1.5, fill:color }));
  if (size === 'counter') {
    card.append(svgElement('text', { x:width/2+2, y:15, 'text-anchor':'middle', class:'counter-total' }, total));
  } else if (size === 'compact') {
    card.append(svgElement('text', { x:9, y:15.5, class:'node-label' }, name),
      svgElement('rect', { x:width-23, y:4, width:19, height:15, rx:4, class:'total-pill' }),
      svgElement('text', { x:width-13.5, y:15.5, 'text-anchor':'middle', class:'counter-total' }, total));
  } else {
    card.append(svgElement('text', { x:width/2, y:15, 'text-anchor':'middle', class:'node-label' }, name),
      svgElement('text', { x:width/2, y:30, 'text-anchor':'middle', class:'node-subtitle' },
        label.subtitle.length > 30 ? label.subtitle.slice(0, 29) + '…' : label.subtitle));
    if (label.isCity) card.append(svgElement('circle', { cx:width-8, cy:7, r:2, class:'city-dot' }));
    const shown = stacks.slice(0, 4);
    shown.forEach(([nation, count], index) => {
      const x = (width - shown.length * 25) / 2 + index * 25;
      card.append(svgElement('rect', { x, y:34, width:22, height:15, rx:3, fill:factionColor(nation) }),
        svgElement('text', { x:x+11, y:45.5, 'text-anchor':'middle', class:'unit-count' }, count));
    });
    if (!shown.length) card.append(svgElement('text', { x:width/2, y:45, 'text-anchor':'middle', class:'node-subtitle' }, 'No units'));
    if (stacks.length > shown.length) card.append(svgElement('text', { x:width-9, y:45, class:'node-subtitle' }, '+'));
  }
  if (label.inBattle) {
    card.append(svgElement('circle', { cx:width-1, cy:0, r:8, class:'battle-disc' }),
      svgElement('text', { x:width-1, y:4, 'text-anchor':'middle', class:'battle-mark' }, '⚔'));
  }
}

function factsRow(container,label,value) {
  const cell = element('div'); cell.append(element('dt','',label),element('dd','',value)); container.append(cell);
}
function recordsAt(field,id) {
  return recordEntries(UI.state[field]).filter(([key,value]) => {
    if(field==='battles'&&value.stage==='finished')return false;
    const repairLocation=field==='repairs' ? value.endpoint
      || locationOf(UI.state.facilities?.[value.target])
      || locationOf(UI.state.units?.[value.target])
      || (UI.replay.map.nodes[value.target] ? value.target : null) : null;
    return locationOf(value) === id || repairLocation === id
      || locationOf(UI.replay.map.facilities?.[key]) === id || key === id
      || (field === 'rails' && [value.endpoint_a,value.endpoint_b].includes(id));
  });
}
function renderInspector() {
  const box = $('location-details');
  if (!UI.selected || !UI.replay.map.nodes[UI.selected]) return;
  const id = UI.selected; const node = UI.replay.map.nodes[id];
  const territory = UI.state.territories?.[id] || {};
  const identity = territoryIdentity(id, UI.state, UI.replay);
  const owner = identity.owner;
  box.replaceChildren();
  $('location-type').textContent = node.type === 'sea' ? 'SEA ZONE' : node.is_city ? 'CITY' : 'LAND ZONE';
  box.append(element('h3','location-title',node.name || id));
  const label = element('div','owner-label');
  const dot = element('i'); dot.style.background=factionColor(owner);
  label.append(dot,document.createTextNode(node.type === 'sea' ? 'Sea zone · no land possessor'
    : owner == null ? 'Unpossessed' : `Current possessor: ${identity.ownerName}`));box.append(label);
  const facts=element('dl','facts');
  factsRow(facts,'Land value',node.type === 'sea' ? '—' : `${node.ipp_value ?? 0} IPP`);
  factsRow(facts,'Terrain',node.type === 'sea' ? 'Sea' : human(node.terrain || 'normal'));
  factsRow(facts,'Original nation',identity.originalName);
  factsRow(facts,'Units present',unitsAt(id).length);
  box.append(facts);
  if(node.type!=='sea'){
    const history=element('section','detail-section');history.append(element('h4','','Possession history'));
    const initial=territoryIdentity(id,UI.replay.initial,UI.replay);
    history.append(element('p','empty-copy',`Starting possessor: ${initial.ownerName}`));
    const changes=possessionChanges(UI.replay).flat().filter(change=>change.zone===id&&change.eventNumber<=UI.position);
    for(const change of changes){
      const button=element('button','ownership-event',`Event ${change.eventNumber} · ${possessionChangeText(change,UI.replay)}`);
      button.type='button';button.addEventListener('click',()=>{stop();seek(change.eventNumber);});history.append(button);
    }
    box.append(history);
  }
  const section=element('section','detail-section');section.append(element('h4','','Units by nation'));
  const grouped=new Map();
  for (const unit of unitsAt(id)) { const nation=ownerOf(unit); if (!grouped.has(nation)) grouped.set(nation,[]);grouped.get(nation).push(unit); }
  for (const [nation,units] of grouped) {
    const stack=element('div','unit-stack');stack.style.setProperty('--faction',factionColor(nation));
    stack.append(element('strong','',human(nation)));
    const types=new Map();for (const unit of units) types.set(unit.type,(types.get(unit.type)||0)+1);
    stack.append(element('p','',[...types].map(([type,count])=>`${count} × ${human(type)}`).join(' · ')));
    const damaged=units.filter(unit=>Number(unit.damage)>0).length;
    const carried=units.filter(unit=>unit.carried_by).length;
    if (damaged || carried) stack.append(element('small','',[damaged ? `${damaged} damaged` : '',carried ? `${carried} carried / embarked` : ''].filter(Boolean).join(' · ')));
    section.append(stack);
  }
  if (!grouped.size) section.append(element('p','empty-copy','No units at this location.'));
  box.append(section);
  const battles=recordsAt('battles',id);
  if(battles.length){
    const group=element('section','detail-section');group.append(element('h4','','Active combat'));
    for(const [,battle] of battles){
      const item=element('div','detail-item');item.append(element('strong','',`${human(battle.attacker)} attacks ${human(battle.defender)}`),element('br'),element('span','',`${phaseText(battle.stage)}${battle.data?.round?` · Combat round ${battle.data.round}`:''}`));group.append(item);
    }
    box.append(group);
  }
  for (const [field,title] of [['facilities','Facilities'],['construction','Construction queue'],['repairs','Repairs'],['rails','Railways']]) {
    const records=recordsAt(field,id);
    if (!records.length && field!=='facilities') continue;
    const group=element('section','detail-section');group.append(element('h4','',title));
    for (const [key,value] of records) {
      const item=element('div','detail-item');item.append(element('strong','',human(value.type ?? value.kind ?? key)));
      const fields=Object.entries(value).filter(([name])=>!['id','type','kind','zone','land_id','location'].includes(name));
      if (fields.length) item.append(element('br'),element('span','',fields.map(([name,entry])=>`${phaseText(name)}: ${typeof entry==='object' ? JSON.stringify(entry) : human(entry)}`).join(' · ')));
      group.append(item);
    }
    if (!records.length) group.append(element('p','empty-copy','No facilities recorded.'));
    box.append(group);
  }
  const details=element('details','raw-details');details.append(element('summary','','Recorded location and unit details'));
  details.append(element('pre','',JSON.stringify({territory,units:unitsAt(id)},null,2)));box.append(details);
}
function allianceFor(nationId,record={}) {
  const player=record.player ?? UI.replay.factions?.[nationId]?.player;
  return String(player ?? '').toLowerCase();
}
function wealthValue(player) {
  const wealth=UI.state.wealth;
  if (Array.isArray(wealth)) return wealth[['axis','allies','comintern'].indexOf(player)];
  const value=wealth?.[player] ?? wealth?.[human(player)];
  return value && typeof value==='object' ? value.wealth ?? value.total ?? value.value : value;
}
function renderLedger() {
  const box=$('wealth-cards');box.replaceChildren();
  for (const player of ['axis','allies','comintern']) {
    const card=element('div','wealth-card');card.style.setProperty('--faction',factionColor(player));
    const title=element('h3');title.append(element('i'),document.createTextNode(human(player)));card.append(title);
    const figure=element('div','wealth-number',number(wealthValue(player),1));figure.append(element('small','',' pts'));card.append(figure,element('p','','Campaign wealth score'));
    const cash=element('div','cash-list');
    for (const [id,nation] of recordEntries(UI.state.nations)) if (allianceFor(id,nation)===player) {
      const value=nation.treasury ?? nation.cash ?? nation.ipp;
      cash.append(element('div','',`${human(id)} cash ${number(value,1)}`));
    }
    if (!cash.childNodes.length) cash.append(element('div','','No controlled treasury recorded'));
    card.append(cash);box.append(card);
  }
}
function renderPolitics(before) {
  const status=politicalStatus(UI.state,UI.replay), previous=politicalStatus(before,UI.replay);
  const known=new Set(previous.wars.map((war)=>war.key));
  const count=status.wars.length;
  $('politics-tag').textContent=JSON.stringify(status)!==JSON.stringify(previous)?'CHANGED THIS EVENT':`${count} ${count===1?'WAR':'WARS'}`;
  const box=$('politics-details');box.replaceChildren();
  const cards=element('div','politics-alliances');
  for (const group of status.groups) {
    const card=element('div','politics-card');card.style.setProperty('--faction',factionColor(group.id));
    card.append(element('h3','',group.id?human(group.id):'Unaligned'));
    const quiet=group.id?[]:group.members.filter((member)=>!member.wars.length);
    for (const member of group.members) {
      if (quiet.includes(member)) continue;
      const row=element('div','politics-member');
      const title=element('div','politics-name');title.append(element('strong','',human(member.id)),element('span','small-tag',member.status.toUpperCase()));
      if (member.surrendered) title.append(element('span','small-tag','SURRENDERED'));
      row.append(title,element('p','',member.wars.length?`At war with ${member.wars.map(human).join(', ')}`:'At peace'));
      if (member.capital) row.append(element('p','',`Capital ${human(member.capital)}`));
      if (member.controller) row.append(element('p','',`Controlled by ${human(member.controller)}`));
      card.append(row);
    }
    if (quiet.length) card.append(element('p','politics-absorbed',`At peace: ${quiet.map((member)=>human(member.id)).join(', ')}`));
    if (group.absorbed.length) card.append(element('p','politics-absorbed',`Absorbed warlords: ${group.absorbed.map(human).join(', ')}`));
    cards.append(card);
  }
  box.append(cards);
  const wars=element('div','politics-wars');wars.append(element('h3','','Wars in progress'));
  const list=element('div','politics-war-list');
  for (const war of status.wars) list.append(element('span',known.has(war.key)?'politics-war':'politics-war new',`${human(war.left)} vs ${human(war.right)}${known.has(war.key)?'':' · new'}`));
  if (!count) list.append(element('span','politics-none','No wars yet'));
  wars.append(list);box.append(wars);
  const facts=element('dl','politics-facts');
  for (const fact of status.facts) {
    const item=element('div');item.append(element('dt','',fact.label),element('dd','',fact.value));facts.append(item);
  }
  box.append(facts);
}
function renderPlayback() {
  const step=UI.replay.steps[UI.position-1];
  $('event-kind').textContent=!step ? 'INITIAL POSITION' : step.kind==='chance' ? 'ACTUAL DICE EVENT' : 'ACTUAL ACTION';
  $('event-summary').textContent=eventSummary(step,UI.replay);
  $('timeline').value=String(UI.position);
  $('timeline').setAttribute('aria-valuetext',`Position ${UI.position} of ${UI.replay.steps.length}: ${eventSummary(step,UI.replay)}`);
  $('event-record').hidden=!step;
  $('event-record-json').textContent=step ? JSON.stringify(step.kind==='chance' ? {kind:'chance',actor:step.actor,chance:step.chance} : {kind:'action',actor:step.actor,nation:step.nation,action:step.action},null,2) : '';
  $('first').disabled=$('prev').disabled=UI.position===0;
  $('next').disabled=$('last').disabled=UI.position===UI.replay.steps.length;
}
function sidesView(battle, rolling) {
  const sides = element('div', 'combat-sides');
  for (const side of battle.sides) {
    const card = element('div', `combat-side${side.role === rolling ? ' rolling' : ''}`);
    card.style.setProperty('--faction', factionColor(side.nation));
    const heading = element('h4', '', side.role === 'attacker' ? 'ATTACKER' : 'DEFENDER');
    if (side.role === rolling) heading.append(element('span', 'rolling-tag', 'ROLLING'));
    card.append(heading);
    if (!side.nations.length) card.append(element('span', 'side-nation', human(side.nation)), element('p', 'side-units', 'No units'));
    for (const group of side.nations) {
      card.append(element('span', 'side-nation', human(group.nation)));
      card.append(element('p', 'side-units', group.units.map((unit) => `${unit.count} × ${human(unit.type)}`).join(' · ')));
    }
    sides.append(card);
  }
  return sides;
}
function battleView(battle, rolling = null, meta = null) {
  const item = element('div', 'combat-battle');
  item.append(element('h3', 'combat-title', `${battle.kind} at ${human(battle.zone)}`));
  item.append(element('p', 'combat-meta', meta ?? [`${human(battle.attacker)} attacks ${human(battle.defender)}`,
    battle.round ? `Combat round ${battle.round}` : '', battle.stage ? stageLabel(battle.stage) : ''].filter(Boolean).join(' · ')));
  item.append(sidesView(battle, rolling));
  return item;
}
function diceTable(report) {
  const table = element('table', 'dice-table'); const head = element('tr');
  for (const label of ['Die', 'Fired by', 'Hits on', 'Rolled', 'Result']) head.append(element('th', '', label));
  const thead = element('thead'); thead.append(head); table.append(thead);
  const body = element('tbody');
  report.dice.forEach((die, index) => {
    const row = element('tr', die.hit ? 'hit' : '');
    const shooter = die.unitType ? `${human(die.unitType)}${die.nation ? ` (${human(die.nation)})` : ''}`
      : die.side ? `${die.side === 'attacker' ? 'Attacking' : 'Defending'} unit${die.nation ? ` (${human(die.nation)})` : ''}` : '—';
    const faces = die.faces.length ? die.faces.join(' → ') : '—';
    const modified = die.modifier ? ` ${die.modifier > 0 ? '+' : '−'} ${Math.abs(die.modifier)} = ${die.effective}` : '';
    const result = element('td');
    if (die.hit === true) result.append(element('span', 'result-chip hit', die.targeted ? 'HIT · TARGETED' : 'HIT'));
    else if (die.hit === false) result.append(element('span', 'result-chip miss', 'MISS'));
    else result.textContent = '—';
    row.append(element('td', '', `${index + 1} · d${die.sides}`), element('td', '', shooter),
      element('td', '', die.threshold !== null && die.threshold !== undefined ? `1–${die.threshold}` : '—'),
      element('td', 'die-face', `${faces}${modified}`), result);
    body.append(row);
  });
  table.append(body);
  return table;
}
function renderCombat() {
  const box = $('combat-details'); box.replaceChildren();
  const report = UI.dice;
  const battles = activeBattles(UI.state);
  if (report) {
    $('combat-tag').textContent = 'DICE ROLLED';
    $('combat-caption').textContent = `Event ${UI.position} · actual dice, not imagined search`;
    const battle = report.battle;
    const sides = [...new Set(report.dice.map((die) => die.side).filter(Boolean))];
    const rolling = sides.length === 1 ? sides[0] : sides.length > 1 ? null : battle?.attacker === report.roller ? 'attacker'
      : battle?.defender === report.roller ? 'defender' : null;
    const count = `${report.dice.length} ${report.dice.length === 1 ? 'die' : 'dice'}`;
    if (battle) {
      const firing = rolling === 'attacker' ? battle.attacker : rolling === 'defender' ? battle.defender : report.roller;
      box.append(battleView(battle, rolling, [report.label, battle.round ? `Combat round ${battle.round}` : '',
        stageLabel(battle.stage), sides.length > 1 ? `Both sides fire ${count}`
          : `${human(firing)}${rolling ? ` (${rolling})` : ''} fires ${count}`].filter(Boolean).join(' · ')));
    } else {
      box.append(element('h3', 'combat-title', report.label),
        element('p', 'combat-meta', `${human(report.roller)} rolls ${count}`));
    }
    box.append(diceTable(report));
    if (Number.isInteger(report.hits)) box.append(element('p', 'combat-total', `${report.hits} ${report.hits === 1 ? 'hit' : 'hits'} from ${count}. A die hits when it rolls at or under its unit’s hit number.`));
    else box.append(element('p', 'combat-note', battle ? 'This recording does not say which unit fired each die for this kind of roll.' : 'This roll is not part of a battle.'));
    const others = battles.filter((item) => item.id !== report.battleId);
    if (others.length) {
      const list = element('div', 'other-battles'); list.append(element('h4', '', 'OTHER BATTLES IN PROGRESS'));
      for (const item of others) list.append(battleView(item));
      box.append(list);
    }
  } else if (battles.length) {
    $('combat-tag').textContent = `${battles.length} ACTIVE`;
    $('combat-caption').textContent = 'Battles in progress at the selected position';
    for (const battle of battles) box.append(battleView(battle));
  } else {
    $('combat-tag').textContent = 'NO COMBAT';
    $('combat-caption').textContent = 'Battles and dice rolls at the selected position';
    box.append(element('p', 'empty-copy', 'No battle is in progress at this position. Step to a dice event, or filter the event journal by Combat or Dice events.'));
  }
}
function valuesPanel(values) {
  const panel=element('div','value-estimates');
  for (const [index,player] of ['axis','allies','comintern'].entries()) {
    const item=element('span','',`${human(player)} estimate`);
    item.append(element('strong','',number(Array.isArray(values) ? values[index] : values?.[player] ?? values?.[human(player)],3)));panel.append(item);
  }
  return panel;
}
function renderSearch() {
  const box=$('search-details');box.replaceChildren();
  const index=UI.position;
  // A future action after unresolved dice belongs to a different board. Never
  // display its search statistics as though they describe the selected position.
  const step=UI.replay.steps[index];const search=step?.search;
  if(step?.kind==='chance'){
    $('search-caption').textContent=`Next event ${index+1} · dice resolution (no MCTS decision)`;
    box.append(element('p','empty-copy','The next recorded event resolves actual dice. There is no action search at this position. Step forward to inspect the resulting board and the next decision.'));
    return;
  }
  $('search-caption').textContent=step ? `Before event ${index+1} · ${human(step.actor)}’s recorded decision` : 'No further recorded decisions';
  if(!step){box.append(element('p','empty-copy','You are at the end of this recording. No further recorded decision is available.'));return;}
  if (!search) {
    box.append(element('p','empty-copy','No MCTS statistics were saved for this decision. The board and event journal still show the actual game.'));
    box.append(element('p','search-info','A scripted or initial-position recording has no search visits. Statistics are shown only when they are present in the saved recording.'));
    return;
  }
  const stats=element('div','search-stats');
  for (const [label,value] of [['Simulations',search.simulations],['Depth cap',search.depth_cap],['Legal choices',search.actions?.length]]) {
    const item=element('span','',label);item.append(element('strong','',number(value)));stats.append(item);
  }
  if (search.simulations===0) box.append(element('p','search-info','Only one legal move here, so it was played without a search.'));
  box.append(stats,element('p','search-info','Simulations are imagined continuations for one choice. The depth cap is a maximum number of search steps, not a number of turns. Visits count exploration; prior is the network preference; policy is the resulting search distribution.'));
  if (search.values) box.append(valuesPanel(search.values));
  box.append(element('p','search-info','Value estimates predict the campaign’s score target. They are not win probabilities. Highlighted choice is the action that was actually played.'));
  const table=element('table','search-table');const head=element('thead');const headings=element('tr');
  for (const label of ['Action considered','Visits','Prior','Policy']) headings.append(element('th','',label));head.append(headings);table.append(head);
  const body=element('tbody');const actions=[...(search.actions||[])].sort((a,b)=>(b.visits??0)-(a.visits??0));
  const selected=String(step.action?.id ?? step.action?.action_id ?? '');
  for (const action of actions) {
    const chosen=selected && String(action.id)===selected;
    const row=element('tr',chosen?'chosen':'');const label=element('td');
    if (chosen) label.append(element('span','chosen-tag','PLAYED'));
    label.append(document.createTextNode(action.label || phaseText(action.kind) || action.id));
    const bar=element('div','policy-bar');const fill=element('i');fill.style.width=`${Math.max(0,Math.min(100,Number(action.policy||0)*100))}%`;bar.append(fill);label.append(bar);
    label.title=JSON.stringify(action.parameters || {});
    row.append(label,element('td','',number(action.visits)),element('td','',percent(action.prior)),element('td','',percent(action.policy)));body.append(row);
  }
  table.append(body);box.append(table);
}
function eventMatches(step,filter,index) {
  if (filter==='all') return true;
  if (filter==='chance') return step.kind==='chance';
  if (filter==='action') return step.kind!=='chance';
  if (filter==='ownership') return (possessionChanges(UI.replay)[index]?.length??0)>0;
  return /combat|battle|casualt|attack|retreat|attrition|bombard/i.test(JSON.stringify([step.action?.kind,step.summary,step.chance]));
}
function renderEvents() {
  const box=$('event-list');box.replaceChildren();
  const entries=UI.replay.steps.map((step,index)=>({step,index})).filter(({step,index})=>eventMatches(step,$('event-filter').value,index));
  // Bound DOM work on very long recordings while keeping the current event in view.
  let center=entries.findIndex(({index})=>index>=UI.position-1);if(center<0)center=entries.length-1;
  const start=Math.max(0,Math.min(entries.length-160,center-60));const visible=entries.slice(start,start+160);
  if(start>0)box.append(element('p','event-end-note',`${number(start)} earlier matching events · move the timeline to view`));
  for(const {step,index} of visible){
    const button=element('button',`event-row${index===UI.position-1?' current':''}`);button.type='button';
    button.setAttribute('aria-label',`Go to event ${index+1}: ${eventSummary(step,UI.replay)}`);
    button.append(element('span','event-index',String(index+1)));
    const detail=element('span');detail.append(element('span','event-label',eventSummary(step,UI.replay)),element('span','event-meta',`${human(step.actor ?? step.nation)} · ${phaseText(step.clock?.phase)}${step.kind==='chance'?' · DICE':''}`));
    button.append(detail,element('span','event-icon',step.kind==='chance'?'⚄':'↗'));
    button.addEventListener('click',()=>{stop();seek(index+1);});box.append(button);
  }
  if(!visible.length)box.append(element('p','empty-copy','No events match this filter.'));
  if(start+visible.length<entries.length)box.append(element('p','event-end-note',`${number(entries.length-start-visible.length)} later matching events · move the timeline to view`));
}
function metadataBadges(metadata) {
  const box=$('record-badges');box.replaceChildren(element('span','badge','REPLAY ONLY'));
  const origin=metadata.origin || 'Recorded game';
  box.append(element('span','badge',phaseText(origin).toUpperCase()));
  if(metadata.live_status==='active'||metadata.live===true)box.append(element('span','badge success','ACTIVE RECORDING'));
  else if(metadata.live_status==='ended')box.append(element('span','badge','RECORDING ENDED'));
  if(metadata.exact_replay_verified)box.append(element('span','badge success','EXACT REPLAY VERIFIED'));
  if(metadata.terminal===false)box.append(element('span','badge warning','PARTIAL RECORDING'));
  if((metadata.training_updates??metadata.model?.training_updates)===0)box.append(element('span','badge','NO LEARNING UPDATES'));
}
function loadReplay(data,label='',options={}) {
  const model=createReplayModel(data);
  const previousPosition=UI.position;const previousSelection=UI.selected;
  stop();UI.replay=data;UI.model=model;UI.position=0;UI.state=model.seek(0);UI.selected=null;
  UI.sourceId=options.sourceId??null;UI.replaySourceId=UI.sourceId;UI.etag=options.etag??null;
  if(!options.preservePosition)resetMapView();
  $('replay-title').textContent=data.metadata?.title || label || 'China campaign recording';
  const metadata=data.metadata||{};
  $('replay-subtitle').textContent=[metadata.seed!=null?`Seed ${metadata.seed}`:'',`${number(data.steps.length)} recorded events`,metadata.horizon_rounds?`${metadata.horizon_rounds}-round horizon`:'',metadata.policy?`${metadata.policy}`:'',metadata.source?`Source: ${metadata.source}`:''].filter(Boolean).join(' · ');
  metadataBadges(metadata);
  $('timeline').max=String(data.steps.length);$('timeline').disabled=false;$('play').disabled=data.steps.length===0;$('download').disabled=false;
  $('refresh').disabled=!UI.sourceId;
  $('follow-latest').disabled=!UI.sourceId;
  if(!UI.sourceId){$('follow-latest').checked=false;window.clearTimeout(UI.followTimer);}
  $('map-empty').hidden=true;
  $('location-type').textContent='MAP';
  $('location-details').replaceChildren();const empty=element('div','empty-detail');empty.append(element('span','','⌖'),element('h3','','Select a location'),element('p','','Inspect its possessor, units, facilities and work in progress.'));$('location-details').append(empty);
  if(options.preservePosition&&data.map.nodes[previousSelection])UI.selected=previousSelection;
  notice();seek(options.tail ? data.steps.length : options.preservePosition ? Math.min(previousPosition,data.steps.length) : 0);
}
async function fetchRecording(id) {
  if(!id)return;
  const token=++UI.loadToken;stop();notice('Loading recording…');
  // A live episode can be selected before its first position exists. Retain its
  // identity on a 503 so Refresh / Follow can wait for that same source.
  if(UI.sourceId!==id)UI.etag=null;
  UI.sourceId=id;$('refresh').disabled=false;$('follow-latest').disabled=false;
  const url=new URL(window.location.href);url.searchParams.set('replay',id);history.replaceState(null,'',url);
  try{
    const response=await fetch(`/api/replays/${encodeURIComponent(id)}`,{cache:'no-store'});
    if(token!==UI.loadToken)return;
    if(response.status===503){notice('This recording has not reached the selected episode yet, or is still being written. Use Refresh or enable Follow latest to wait for it.');return;}
    if(!response.ok)throw new Error(`Recording could not be loaded (${response.status}).`);
    const data=await response.json();if(token!==UI.loadToken)return;
    loadReplay(data,id,{sourceId:id,etag:response.headers.get('ETag'),tail:$('follow-latest').checked});
  }catch(error){if(token===UI.loadToken)notice(error.message);}
  finally{scheduleFollow();}
}
function scheduleFollow(){
  window.clearTimeout(UI.followTimer);
  if(UI.sourceId&&$('follow-latest').checked&&!UI.refreshInFlight)UI.followTimer=window.setTimeout(()=>refreshRecording(),2000);
}
async function refreshRecording(){
  if(!UI.sourceId||UI.refreshInFlight)return;
  const sourceId=UI.sourceId;const token=UI.loadToken;
  UI.refreshInFlight=true;window.clearTimeout(UI.followTimer);$('refresh').disabled=true;
  try{
    const headers=UI.etag?{'If-None-Match':UI.etag}:{};
    const response=await fetch(`/api/replays/${encodeURIComponent(sourceId)}`,{cache:'no-store',headers});
    if(token!==UI.loadToken||sourceId!==UI.sourceId)return;
    if(response.status===304){notice();return;}
    if(response.status===503){notice('Waiting for the selected episode to be recorded. Refresh will keep this source selected; Follow latest retries automatically.');return;}
    if(!response.ok)throw new Error(`Recording refresh failed (${response.status}).`);
    const data=await response.json();
    if(token!==UI.loadToken||sourceId!==UI.sourceId)return;
    const etag=response.headers.get('ETag');
    // An unchanged full response from a server without conditional-request support
    // should not interrupt playback or rebuild the selected position.
    if(etag&&etag===UI.etag)return;
    loadReplay(data,sourceId,{sourceId,etag,preservePosition:UI.replaySourceId===sourceId,tail:$('follow-latest').checked});
  }catch(error){if(token===UI.loadToken)notice(error.message);}
  finally{UI.refreshInFlight=false;$('refresh').disabled=!UI.sourceId;scheduleFollow();}
}
async function loadCatalog() {
  try{
    const response=await fetch('/api/replays',{cache:'no-store'});
    if(!response.ok)throw new Error('No replay catalog available.');
    const result=await response.json();UI.catalog=Array.isArray(result.replays)?result.replays:[];
    $('recordings').replaceChildren(element('option','',UI.catalog.length?'Choose a recording':'No saved recordings'));
    $('recordings').firstChild.value='';
    for(const replay of UI.catalog){const option=element('option','',replay.title||replay.id);option.value=replay.id;$('recordings').append(option);}
    const requested=new URL(window.location.href).searchParams.get('replay');
    const selected=requested || UI.catalog[0]?.id;
    if(selected){$('recordings').value=selected;await fetchRecording(selected);}
  }catch(error){$('recordings').replaceChildren(element('option','','Open a JSON recording'));notice('Open a saved replay JSON above, or start the local viewer server to browse recordings.');}
}
$('recordings').addEventListener('change',(event)=>fetchRecording(event.target.value));
$('refresh').addEventListener('click',()=>refreshRecording());
$('follow-latest').addEventListener('change',()=>{
  if($('follow-latest').checked&&UI.replay&&UI.replaySourceId===UI.sourceId){stop();seek(UI.replay.steps.length);}
  scheduleFollow();
});
$('file-input').addEventListener('change',async(event)=>{
  const file=event.target.files[0];if(!file)return;
  const token=++UI.loadToken;
  try{if(file.size>100*1024*1024)throw new Error('This recording is larger than the 100 MB browser import limit.');
    const data=JSON.parse(await file.text());if(token!==UI.loadToken)return;loadReplay(data,file.name);$('recordings').value='';
  }catch(error){notice(`Could not open recording: ${error.message}`);}finally{event.target.value='';}
});
$('download').addEventListener('click',()=>{
  if(!UI.replay)return;const blob=new Blob([JSON.stringify(UI.replay)],{type:'application/json'});const url=URL.createObjectURL(blob);
  const link=element('a');link.href=url;link.download='campaign-replay.json';link.click();window.setTimeout(()=>URL.revokeObjectURL(url),1000);
});
$('play').addEventListener('click',togglePlay);
for(const [id,position] of [['first',()=>0],['prev',()=>UI.position-1],['next',()=>UI.position+1],['last',()=>UI.replay?.steps.length||0]]){
  $(id).addEventListener('click',()=>{stop();seek(position());});
}
$('timeline').addEventListener('input',(event)=>{stop();seek(Number(event.target.value));});
$('speed').addEventListener('change',schedule);
$('event-filter').addEventListener('change',()=>{if(UI.replay)renderEvents();});
$('show-connections').addEventListener('change',(event)=>{UI.showConnections=event.target.checked;if(UI.replay)seek(UI.position);});
$('zoom-in').addEventListener('click',()=>zoomMap(1.4));
$('zoom-out').addEventListener('click',()=>zoomMap(1/1.4));
$('reset-view').addEventListener('click',()=>{resetMapView();UI.selected=null;if(UI.replay){seek(UI.position);$('location-type').textContent='MAP';$('location-details').replaceChildren(element('p','empty-copy','Choose a location on the map to inspect its units and facilities.'));}});
const mapSurface = $('map');
if (window.ResizeObserver) new ResizeObserver(updateMapView).observe(mapSurface);

mapSurface.addEventListener('wheel', (event) => {
  if (!UI.replay || !event.deltaY) return;
  const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? mapSurface.clientHeight : 1;
  const factor = Math.exp(-event.deltaY * unit * 0.002);
  if (!event.ctrlKey && ((UI.zoom === 1 && factor < 1) || (UI.zoom === MAX_MAP_ZOOM && factor > 1))) return;
  event.preventDefault();
  zoomMap(factor, { x: event.clientX, y: event.clientY });
}, { passive: false });

function gestureCenter() {
  const [first, second] = UI.pointers.values();
  if (!second) return first;
  return { x: (first.x + second.x) / 2, y: (first.y + second.y) / 2,
    distance: Math.hypot(first.x - second.x, first.y - second.y) };
}
function startMapDrag() {
  UI.mapDragging = true;
  for (const id of UI.pointers.keys()) mapSurface.setPointerCapture(id);
}
mapSurface.addEventListener('pointerdown', (event) => {
  if (!UI.replay || event.button !== 0 || UI.pointers.size >= 2) return;
  if (!UI.pointers.size) UI.suppressClickUntil = 0;
  UI.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
  if (UI.pointers.size === 2) startMapDrag();
});
mapSurface.addEventListener('pointermove', (event) => {
  const previous = UI.pointers.get(event.pointerId);
  if (!previous) return;
  if (!UI.mapDragging) {
    if (Math.hypot(event.clientX - previous.x, event.clientY - previous.y) <= 4) return;
    startMapDrag();
  }
  const before = gestureCenter();
  UI.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
  const after = gestureCenter();
  zoomMap(before.distance ? after.distance / before.distance : 1, before, after);
});
function endMapDrag(event) {
  if (!UI.pointers.delete(event.pointerId) || !UI.mapDragging) return;
  UI.suppressClickUntil = Date.now() + 300;
  if (!UI.pointers.size) {
    UI.mapDragging = false;
    mapSurface.style.cursor = UI.zoom > 1 ? 'grab' : '';
  }
}
mapSurface.addEventListener('pointerup', endMapDrag);
mapSurface.addEventListener('pointercancel', endMapDrag);
mapSurface.addEventListener('lostpointercapture', (event) => {
  // Touch initially captures the node that received the press. Transferring
  // capture to the map sends a bubbling lost event from that old target.
  if (event.target === mapSurface) endMapDrag(event);
});
mapSurface.addEventListener('pointerleave', (event) => {
  if (!UI.mapDragging) endMapDrag(event);
});
mapSurface.addEventListener('keydown', (event) => {
  if (!UI.replay || event.ctrlKey || event.metaKey || event.altKey) return;
  const { x, y, width, height } = UI.view;
  switch (event.key) {
    case '+': case '=': zoomMap(1.4); break;
    case '-': zoomMap(1 / 1.4); break;
    case '0': resetMapView(); break;
    case 'ArrowLeft': setMapView(UI.zoom, x - width / 5, y); break;
    case 'ArrowRight': setMapView(UI.zoom, x + width / 5, y); break;
    case 'ArrowUp': setMapView(UI.zoom, x, y - height / 5); break;
    case 'ArrowDown': setMapView(UI.zoom, x, y + height / 5); break;
    default: return;
  }
  event.preventDefault();
  event.stopPropagation();
});
document.addEventListener('keydown',(event)=>{
  if(!UI.replay||event.altKey||event.ctrlKey||event.metaKey||event.target.closest('input,select,textarea,button,[role=button],a'))return;
  if(event.key===' '){event.preventDefault();togglePlay();}
  else if(event.key==='ArrowLeft'){event.preventDefault();stop();seek(UI.position-1);}
  else if(event.key==='ArrowRight'){event.preventDefault();stop();seek(UI.position+1);}
  else if(event.key==='Home'){event.preventDefault();stop();seek(0);}
  else if(event.key==='End'){event.preventDefault();stop();seek(UI.replay.steps.length);}
});
const boardArt = $('board-art');
$('map-art-status').hidden = boardArt.getAttribute('data-missing') !== 'true';
boardArt.addEventListener('error', () => { $('map-art-status').hidden = false; });
if (globalThis.CAMPAIGN_REPLAY) {
  $('recordings').replaceChildren(element('option','','Embedded campaign recording'));
  try { loadReplay(globalThis.CAMPAIGN_REPLAY); }
  catch (error) { notice(`Could not open embedded recording: ${error.message}`); }
} else loadCatalog();
