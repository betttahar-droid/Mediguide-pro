import {
  Scene, PerspectiveCamera, WebGLRenderer, Vector3, Mesh, GridHelper, Color,
  SRGBColorSpace, NoToneMapping, Fog,
} from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import Stats from 'stats.js';

import { PALETTE, PALETTE_HEX } from './art/palette.js';
import { createAdaptiveMaterial } from './shaders/index.js';
import { bevelBox } from './modules/geometry.js';
import { bakeMasks } from './art/bakeMasks.js';
import { REGISTRY, validateRegistry } from './modules/registry.js';
import { ModuleInstance, warmGeometryCache } from './modules/ModuleInstance.js';
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
scene.fog = new Fog(new Color(PALETTE_HEX.backdrop).getHex(), 18, 55);

const camera = new PerspectiveCamera(42, 1, 0.1, 200);
camera.position.set(5.5, 4.2, 6.5);

const controls = new OrbitControls(camera, canvas);
controls.target.set(0, 0.9, 0);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * 0.49;
controls.minDistance = 1.5;
controls.maxDistance = 40;

const stats = new Stats();
stats.dom.style.left = 'auto';
stats.dom.style.right = '0';
document.body.appendChild(stats.dom);

// ------------------------------------------------------------------ floor
// Tier C (triplanar) is not built — the floor uses the same adaptive material
// with a flat palette colour so nothing outside src/shaders/ touches GLSL.
{
  const slab = bakeMasks(bevelBox(30, 0.2, 30, 0.06), { rays: 6, radius: 0.2 });
  const material = createAdaptiveMaterial({
    baseColor: PALETTE.floorTile,
    middleColor: PALETTE.floorTile,
    sourceHalfExtents: new Vector3(15, 0.1, 15),
    margins: new Vector3(0.1, 0.05, 0.1),
  });
  const floor = new Mesh(slab, material);
  floor.position.y = -0.1;
  scene.add(floor);

  const grid = new GridHelper(30, 30, PALETTE_HEX.ghost, PALETTE_HEX.ghost);
  grid.material.opacity = 0.16;
  grid.material.transparent = true;
  grid.position.y = 0.002;
  scene.add(grid);
}

warmGeometryCache();

// -------------------------------------------------------------------- app
const placement = new Placement(camera, canvas);
const placed = [];

const app = {
  placed,
  state: { moduleId: 'gondola_shelf', mode: 'place' },
  stats: { modules: 0, cost: 0 },
  ghost: null,
  selected: null,
  onActiveChanged: () => {},

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
    // the active snap reads as a ghost in the ink/accent colour (§8.3)
    app.ghost.setHighlight(snapped ? 0.55 : 0.0);
  } else if (app.state.mode === 'select' && placement.hasPointer) {
    const next = placement.pick(placed);
    if (next !== hovered) {
      if (hovered && hovered !== app.selected) hovered.setHighlight(0);
      hovered = next;
      if (hovered && hovered !== app.selected) hovered.setHighlight(0.18);
    }
  }

  renderer.render(scene, camera);
  stats.end();
  requestAnimationFrame(frame);
}
frame();

// a small starting scene so the first frame is not an empty room
seed();
function seed() {
  const run = new ModuleInstance('gondola_shelf', { params: { x: 3, y: 4, z: 1.0 }, position: [-2.2, 0, -2] });
  const counter = new ModuleInstance('serving_counter', { params: { x: 2.4, z: 1.0 }, position: [1.8, 0, 1.2] });
  const till = new ModuleInstance('till_block', { position: [1.8, 0.955, 1.2] });
  for (const m of [run, counter, till]) {
    scene.add(m.group);
    placed.push(m);
  }
  app.refreshStats();
}
