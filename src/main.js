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
import { MODULE_IDS, REGISTRY, validateRegistry } from './modules/registry.js';
import { AdaptivePropBase } from './modules/AdaptivePropBase.js';
import { nanoAtlasReady } from './art/nanoAtlas.js';
import { ModuleInstance, warmGeometryCache } from './modules/ModuleInstance.js';
import { createInstancedBatch, disposeBatch } from './modules/InstancedBatch.js';
import { Placement } from './build/placement.js';
import { findSocketSnap } from './build/snapping.js';
import { saveLocal, loadLocal, clearLocal } from './build/serialize.js';
import { buildGui } from './ui/gui.js';
import { buildCatalogue } from './ui/catalogue.js';
import { texturesReady } from './art/textures.js';

validateRegistry();

// ---------------------------------------------------------------- renderer
const canvas = document.getElementById('app');
// The game is authored as low-resolution pixel art. MSAA and retina-resolution
// rendering soften the one-texel marks and tiny stepped silhouettes that give
// the furniture its character, so keep the 3D buffer deliberately crisp. The
// HTML UI remains normal-resolution because only the WebGL canvas is affected.
const renderer = new WebGLRenderer({ canvas, antialias: false });
renderer.setPixelRatio(1);
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
function panel(w, h, d, position, color, textureScale, contrast = 1.0) {
  const geo = bakeMasks(bevelBox(w, h, d, 0.05), { rays: 6, radius: 0.2 });
  const material = createAdaptiveMaterial({
    baseColor: color,
    middleColor: color,
    sourceHalfExtents: new Vector3(w / 2, h / 2, d / 2),
    margins: new Vector3(0, 0, 0),
    tier: 'C',
    textureScale,
  });
  // The room is a backdrop. Every isometric sheet in docs/concept/ sits its
  // object on a plain ground, and the walls here were competing with the
  // furniture's own detail — so the panels get a flatter reading of the same
  // tiling sheet rather than a different one.
  material.uniforms.uDetailContrast.value = contrast;
  const mesh = new Mesh(geo, material);
  mesh.position.set(...position);
  scene.add(mesh);
  return mesh;
}

// The room commits to a colour: cool mint walls against a warm putty floor, so
// the warm oak furniture has something to sit against. Every isometric diorama
// in the reference that reads well does this; a neutral room makes its contents
// float.
const room = {
  floor: panel(24, 0.2, 24, [0, -0.1, 0], PALETTE.floorTile, 0.34, 0.80),
  backWall: panel(24, 4.4, 0.24, [0, 2.2, -7], PALETTE.wall, 0.32, 0.45),
  sideWall: panel(0.24, 4.4, 24, [-9, 2.2, 0], PALETTE.wall, 0.32, 0.45),
};

warmGeometryCache();

// -------------------------------------------------------------------- app
const placement = new Placement(camera, canvas);
const placed = [];
let batch = null;

const app = {
  placed,
  moduleIds: MODULE_IDS, // test/portraits.mjs walks these
  texturesReady: texturesReady(),
  room,
  scene,
  camera,
  controls,
  state: { moduleId: 'dispensing_desk', mode: 'place' },
  catalogue: null,
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

  /** Decor is atmosphere, not geometry — the 9-slice checks hide it. */
  setDecorVisible(visible) {
    for (const m of placed) m.setDecorVisible(visible);
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
        // steps counts too: a double-door fridge is two fridges' worth of cabinet
        .filter(([, s]) => s.mode === 'repeat' || s.mode === 'steps')
        .reduce((n, [axis]) => n * m.params[axis], 1);
      return sum + def.cost * bays;
    }, 0);
    this.catalogue?.refresh();
  },
};

app.selectType(app.state.moduleId);
buildGui(app);
app.catalogue = buildCatalogue(app);
// The standalone adaptive prop, exposed for the smoke test and for driving a
// generated factory that has no registry entry. Nothing is spawned until
// something asks for one — a scene full of modules does not need this path.
app.nanoAtlasReady = nanoAtlasReady();

// The img2threejs reconstruction, driven through THIS renderer. The spec is the
// artefact the skill produced; src/modules/fromSculptSpec.js turns its component
// tree into a part list so it is built faceted, with the trim strips and the
// 9-slice attributes, instead of by the generated factory's photoreal stack.
// See the long note at the top of fromSculptSpec.js for why.
app.spawnFromSpec = async (url = 'spec/counter-run.json', at = [0, 0, 0], scaleX = 1) => {
  const spec = await (await fetch(url)).json();
  const { partsFromSpec } = await import('./modules/fromSculptSpec.js');
  const built = partsFromSpec(spec);
  const prop = app.makeAdaptiveProp({
    parts: built.parts,
    halfExtents: built.unit,
    margins: built.margins,
    colors: built.colors,
    repeat: built.repeat,
    propSpacing: 0.45,
    socketY: built.unit[1],
    socketZ: 0.02,
    seed: 4242,
  });
  // The spec's origin is the bay CENTRE, so lift by a half-height to stand it
  // on the floor rather than burying half of it.
  prop.group.position.set(at[0], at[1] + built.unit[1], at[2]);
  prop.updateSize(scaleX, 1, 1);
  prop.spec = spec;
  return prop;
};
app.makeAdaptiveProp = (opts) => {
  const prop = new AdaptivePropBase(opts);
  scene.add(prop.group);
  return prop;
};

// Production architecture proof: strict pixel-grid GLB + adaptive sockets.
app.spawnProductionFridge = async (at = [0, 0, 0], scaleX = 1) => {
  const { loadProductionFridge } = await import('./production/fridgeArchitecture.js');
  const built = await loadProductionFridge();
  built.root.position.set(...at);
  built.root.userData.setAdaptiveScale(scaleX, 1, 1);
  scene.add(built.root);
  return built.root;
};

// Voxel-derived adaptive proof. Door-count variants are cached GLBs built by
// inserting complete 32 px bays; no mesh or texture is conventionally scaled.
app.spawnVoxelFridge = async (doors = 1, at = [0, 0, 0]) => {
  const { loadVoxelFridge } = await import('./production/voxelFridge.js');
  const root = await loadVoxelFridge(doors);
  root.position.set(...at);
  scene.add(root);
  return root;
};

app.previewVoxelFridges = async () => {
  // Keep this preview deterministic and unobstructed even in the seeded room.
  scene.getObjectsByProperty('name', 'voxel_fridge_preview').forEach((node) => node.removeFromParent());
  placed.forEach((module) => { module.group.visible = false; });
  if (app.ghost?.group) app.ghost.group.visible = false;
  const { loadVoxelFridge } = await import('./production/voxelFridge.js');
  const [one, two, three] = await Promise.all([
    loadVoxelFridge(1), loadVoxelFridge(2), loadVoxelFridge(3),
  ]);
  one.name = two.name = three.name = 'voxel_fridge_preview';
  one.position.set(-2.8, 0, 0);
  two.position.set(0, 0, 0);
  three.position.set(3.4, 0, 0);
  scene.add(one, two, three);
  camera.position.set(7.2, 3.8, 8.4);
  controls.target.set(0.8, 1.45, 0);
  controls.update();
  return { one, two, three };
};

// Runtime material A/B: identical geometry, camera and decals. The left model
// retains the reference-measured v5 tile; the right replaces only its broad
// steel side panel with the UV-less analytic material pilot.
app.previewAnalyticFridgeComparison = async () => {
  scene.getObjectsByProperty('name', 'fridge_analytic_comparison').forEach((node) => node.removeFromParent());
  placed.forEach((module) => { module.group.visible = false; });
  if (app.ghost?.group) app.ghost.group.visible = false;
  const { loadVoxelFridge } = await import('./production/voxelFridge.js');
  const [control, analytic] = await Promise.all([
    loadVoxelFridge(1, { analyticSidePanel: false }),
    loadVoxelFridge(1, { analyticSidePanel: true }),
  ]);
  control.name = analytic.name = 'fridge_analytic_comparison';
  control.position.set(-1.25, 0, 0);
  analytic.position.set(1.25, 0, 0);
  scene.add(control, analytic);
  camera.position.set(5.1, 2.9, 6.1);
  controls.target.set(0, 1.4, 0);
  controls.update();
  return { control, analytic };
};

app.previewStrictSdfFridge = async () => {
  scene.getObjectsByProperty('name', 'strict_sdf_comparison').forEach((node) => node.removeFromParent());
  placed.forEach((module) => { module.group.visible = false; });
  if (app.ghost?.group) app.ghost.group.visible = false;
  const [{ loadVoxelFridge }, { generateStrictSdfFridge }] = await Promise.all([
    import('./production/voxelFridge.js'),
    import('./production/strictSdfFridge.js'),
  ]);
  const control = await loadVoxelFridge(1, { analyticSidePanel: false });
  const strict = generateStrictSdfFridge(38.75 / 32, 96 / 32, 36.75 / 32);
  control.name = strict.name = 'strict_sdf_comparison';
  control.position.set(-1.2, 0, 0);
  strict.position.set(1.2, 0, 0);
  scene.add(control, strict);
  camera.position.set(5.1, 3.0, 6.4);
  controls.target.set(0, 1.4, 0);
  controls.update();
  return { control, strict };
};

if (new URLSearchParams(location.search).get('preview') === 'fridge-analytic') {
  app.previewAnalyticFridgeComparison();
}
if (new URLSearchParams(location.search).get('preview') === 'fridge-strict') {
  app.previewStrictSdfFridge();
}

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
  else if (e.key === 'Escape') {
    app.setMode(app.state.mode === 'place' ? 'select' : 'place');
    app.catalogue?.refresh();
  }
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
  // A plausible small pharmacy: the dispensary along the back wall with its
  // racking behind the bench, the CD cabinet and fridge beside it, the retail
  // floor in front, and the consultation room in the corner.
  const layout = [
    ['dispensing_desk', { x: 3, z: 1.0 }, [-0.6, 0, -0.4], 0],
    ['dispensary_shelving', { x: 4, y: 6, z: 1.0 }, [-0.6, 0, -2.4], 0],
    ['cd_cabinet', { x: 1 }, [2.1, 0, -2.4], 0],
    ['fridge_cabinet', { x: 1 }, [3.1, 0, -2.4], 0],
    ['sink_unit', { x: 1, z: 1.0 }, [-3.0, 0, -0.4], 0],
    ['waste_station', {}, [-4.0, 0, -0.4], 0],
    ['till_block', {}, [0.3, 0.955, -0.2], 0],
    ['serving_counter', { x: 1.3, z: 1.0 }, [3.6, 0, -0.4], 0],
    ['gondola_shelf', { x: 3, y: 4, z: 1.0 }, [-2.4, 0, 2.4], 0],
    ['gondola_shelf', { x: 3, y: 4, z: 1.0 }, [1.4, 0, 2.4], 0],
    ['promo_bin', { x: 1 }, [4.2, 0, 1.6], 0],
    ['basket_stack', { y: 5 }, [5.0, 0, 3.4], 0],
    ['queue_barrier', { x: 2 }, [0.4, 0, 1.1], 0],
    ['consultation_booth', { x: 1.1, z: 1.0 }, [-4.6, 0, 3.0], 0],
    ['consult_chair', {}, [-4.9, 0, 2.6], 0.6],
    ['locker_bank', { x: 3 }, [-7.4, 0, -1.2], Math.PI / 2],
    ['filing_cabinet', {}, [-7.4, 0, 0.9], Math.PI / 2],
    ['wall_shelving', { x: 3, y: 3 }, [3.2, 0, -6.4], 0],
    ['green_cross', {}, [0.0, 0, -6.6], 0],
    ['aisle_sign', { x: 1 }, [-0.5, 0, 3.9], 0],
  ];
  for (const [type, params, position, rotY] of layout) {
    const m = new ModuleInstance(type, { params, position, rotY });
    if (REGISTRY[type].hover) m.group.position.y += REGISTRY[type].hover;
    scene.add(m.group);
    placed.push(m);
  }
  app.refreshStats();
}
