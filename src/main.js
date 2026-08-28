import {
  Scene, PerspectiveCamera, WebGLRenderer, Vector3, Mesh, Color,
  SRGBColorSpace, NoToneMapping,
} from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import Stats from 'stats.js';

import { PALETTE, PALETTE_HEX } from './art/palette.js';
import { createAdaptiveMaterial, createOutlinePass } from './shaders/index.js';
import { bevelBox } from './modules/geometry.js';
import { bakeMasks } from './art/bakeMasks.js';
import { REGISTRY, validateRegistry } from './modules/registry.js';
import { ModuleInstance, warmGeometryCache } from './modules/ModuleInstance.js';
import { createInstancedBatch, disposeBatch } from './modules/InstancedBatch.js';
import { Placement } from './build/placement.js';
import { findSocketSnap } from './build/snapping.js';
import { saveLocal, loadLocal, clearLocal } from './build/serialize.js';
import { buildGui } from './ui/gui.js';

validateRegistry();

// ---------------------------------------------------------------- renderer
const canvas = document.getElementById('app');
const renderer = new WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = SRGBColorSpace;
// no filmic curve — ACES desaturates exactly the limited palette we chose
renderer.toneMapping = NoToneMapping;

const scene = new Scene();
scene.background = new Color(PALETTE_HEX.backdrop);

const camera = new PerspectiveCamera(38, 1, 0.1, 200);
camera.position.set(4.6, 2.9, 5.4);

const controls = new OrbitControls(camera, canvas);
controls.target.set(0, 0.85, 0);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * 0.495;
controls.minDistance = 1.2;
controls.maxDistance = 40;

const stats = new Stats();
stats.dom.style.left = 'auto';
stats.dom.style.right = '0';
document.body.appendChild(stats.dom);

const outline = createOutlinePass({ renderer });

// -------------------------------------------------------------- the room
// §9 "Floor / wall panel — Tier C triplanar". Object space and post-deform, so
// the texture does not swim when a panel is moved or stretched.
function panel(w, h, d, position, color, textureScale) {
  const geo = bakeMasks(bevelBox(w, h, d, 0.05), { rays: 6, radius: 0.2 });
  const material = createAdaptiveMaterial({
    baseColor: color,
    middleColor: color,
    sourceHalfExtents: new Vector3(w / 2, h / 2, d / 2),
    margins: new Vector3(0, 0, 0),
    tier: 'C',
    textureScale,
  });
  const mesh = new Mesh(geo, material);
  mesh.position.set(...position);
  scene.add(mesh);
  return mesh;
}

const room = {
  floor: panel(24, 0.2, 24, [0, -0.1, 0], PALETTE.floorTile, 0.75),
  backWall: panel(24, 4.4, 0.24, [0, 2.2, -7], PALETTE.paper, 0.32),
  sideWall: panel(0.24, 4.4, 24, [-9, 2.2, 0], PALETTE.paper, 0.32),
};

warmGeometryCache();

// -------------------------------------------------------------------- app
const placement = new Placement(camera, canvas);
const placed = [];
let batch = null;

const app = {
  placed,
  room,
  scene,
  camera,
  controls,
  state: { moduleId: 'serving_counter', mode: 'place' },
  stats: { modules: 0, cost: 0, drawCalls: 0 },
  ghost: null,
  selected: null,
  onActiveChanged: () => {},
  outline,

  activeModule() {
    return this.state.mode === 'place' ? this.ghost : this.selected;
  },

  selectType(id) {
    this.state.moduleId = id;
    this.ghost?.dispose();
    this.ghost = new ModuleInstance(id, { ghost: true });
    scene.add(this.ghost.group);
    this.ghost.group.visible = false; // shown once the pointer is over the canvas
    this.onActiveChanged();
  },

  setMode(mode) {
    this.state.mode = mode;
    if (this.ghost) this.ghost.group.visible = mode === 'place' && placement.hasPointer;
    if (mode === 'place') this.select(null);
    this.onActiveChanged();
  },

  select(module) {
    this.selected?.setHighlight(0);
    this.selected = module;
    module?.setHighlight(0.35);
    this.onActiveChanged();
  },

  setParam(axis, value) {
    this.activeModule()?.setParams({ [axis]: value });
    this.refreshStats();
  },

  rotate() {
    const target = this.activeModule();
    if (target) target.group.rotation.y += Math.PI / 4;
  },

  commit() {
    const g = this.ghost;
    if (!g) return;
    const instance = new ModuleInstance(g.typeId, {
      params: { ...g.params },
      position: g.group.position.toArray(),
      rotY: g.group.rotation.y,
    });
    scene.add(instance.group);
    placed.push(instance);
    this.refreshStats();
  },

  deleteSelected() {
    if (!this.selected) return;
    const i = placed.indexOf(this.selected);
    if (i >= 0) placed.splice(i, 1);
    this.selected.dispose();
    this.selected = null;
    this.refreshStats();
    this.onActiveChanged();
  },

  clearScene() {
    while (placed.length) placed.pop().dispose();
    this.selected = null;
    this.refreshStats();
  },

  clear() {
    this.clearScene();
    clearLocal();
  },

  /** Run the snap resolver against the ghost where it currently stands. */
  snapDebug() {
    if (!this.ghost) return null;
    const snap = findSocketSnap(this.ghost, placed);
    if (snap) this.ghost.group.position.copy(snap.position);
    return snap;
  },

  save() {
    saveLocal(placed);
    console.log(`saved ${placed.length} modules`);
  },

  load() {
    const restored = loadLocal();
    if (!restored) return console.warn('nothing saved');
    this.clearScene();
    for (const m of restored) {
      scene.add(m.group);
      placed.push(m);
    }
    this.refreshStats();
  },

  /** Phase 6 acceptance: many modules, one draw call per module type. */
  stressTest(count = 200) {
    this.clearBatch();
    const entries = [];
    for (let i = 0; i < count; i++) {
      const row = Math.floor(i / 20);
      entries.push({
        position: [-4.5 + (i % 20) * 0.48, 0, 2.6 + row * 0.55],
        rotY: ((i * 37) % 90) * (Math.PI / 180),
        params: { x: 1 + (i % 3) },
      });
    }
    batch = createInstancedBatch('medicine_box', entries);
    scene.add(batch);
    console.log(`instanced ${entries.length} modules → ${batch.count} instances in 1 draw call`);
    return batch;
  },

  clearBatch() {
    if (batch) disposeBatch(batch);
    batch = null;
  },

  refreshStats() {
    this.stats.modules = placed.length;
    this.stats.cost = placed.reduce((sum, m) => {
      const def = REGISTRY[m.typeId];
      const bays = Object.entries(def.axes)
        .filter(([, s]) => s.mode === 'repeat')
        .reduce((n, [axis]) => n * m.params[axis], 1);
      return sum + def.cost * bays;
    }, 0);
  },
};

app.selectType(app.state.moduleId);
buildGui(app);
globalThis.__app = app; // handle for the smoke test and for poking at the scene

// --------------------------------------------------------------- pointer
let downAt = null;
canvas.addEventListener('pointerdown', (e) => { downAt = { x: e.clientX, y: e.clientY }; });
canvas.addEventListener('pointermove', (e) => placement.updatePointer(e));
canvas.addEventListener('pointerup', (e) => {
  const dragged = downAt && Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y) > 5;
  downAt = null;
  if (dragged) return; // that was an orbit, not a click
  placement.updatePointer(e);
  if (app.state.mode === 'place') app.commit();
  else app.select(placement.pick(placed));
});

addEventListener('keydown', (e) => {
  if (e.target !== document.body && e.target !== canvas) return;
  const k = e.key.toLowerCase();
  if (k === 'r') app.rotate();
  else if (k === 'x' || e.key === 'Delete') app.deleteSelected();
  else if (e.key === 'Escape') app.setMode(app.state.mode === 'place' ? 'select' : 'place');
});

// ------------------------------------------------------------------ loop
function resize() {
  const w = innerWidth, h = innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  outline.setSize(w, h, renderer.getPixelRatio());
}
addEventListener('resize', resize);
resize();

let hovered = null;
function frame() {
  stats.begin();
  controls.update();

  if (app.state.mode === 'place' && app.ghost && placement.hasPointer) {
    app.ghost.group.visible = true;
    const { snapped } = placement.place(app.ghost, placed);
    // the active snap reads as a ghost in the accent colour (§8.3)
    app.ghost.setHighlight(snapped ? 0.55 : 0.0);
  } else if (app.state.mode === 'select' && placement.hasPointer) {
    const next = placement.pick(placed);
    if (next !== hovered) {
      if (hovered && hovered !== app.selected) hovered.setHighlight(0);
      hovered = next;
      if (hovered && hovered !== app.selected) hovered.setHighlight(0.18);
    }
  }

  if (outline.enabled) outline.prepass(scene, camera);
  renderer.render(scene, camera);
  // read before the composite: renderer.info resets on every render() call
  app.stats.drawCalls = renderer.info.render.calls;
  if (outline.enabled) outline.composite();

  stats.end();
  requestAnimationFrame(frame);
}
frame();

// a small starting scene so the first frame is not an empty room
seed();
function seed() {
  const desk = new ModuleInstance('serving_counter', { params: { x: 1.9, z: 1.0 }, position: [0.4, 0, 1.0] });
  const run = new ModuleInstance('gondola_shelf', { params: { x: 3, y: 4, z: 1.0 }, position: [-2.6, 0, -2.6] });
  const fridge = new ModuleInstance('fridge_cabinet', { params: { x: 1 }, position: [2.8, 0, -2.6] });
  const till = new ModuleInstance('till_block', { position: [0.4, 0.955, 1.0] });
  const boxes = new ModuleInstance('medicine_box', { params: { x: 5 }, position: [-2.6, 0.775, -2.6] });
  const queue = new ModuleInstance('queue_barrier', { params: { x: 2 }, position: [0.4, 0, 3.4] });
  for (const m of [desk, run, fridge, till, boxes, queue]) {
    scene.add(m.group);
    placed.push(m);
  }
  app.refreshStats();
}
