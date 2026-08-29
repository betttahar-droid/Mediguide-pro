// Decor — the small stuff that appears when a module grows.
//
// §8.4 says detail props "do more for the atmosphere than any shader in this
// document", and the reference scenes agree: what makes a desk read as a desk
// someone works at is the paper, the mug and the clipboard on it, not the
// joinery. So decor is not decoration you place by hand — a module declares
// SLOTS as a function of its parameters, and adding a bay adds slots.
//
// Two rules make that feel designed rather than random:
//
//   1. A slot's contents are a pure function of (module seed, slot key). Add a
//      bay and the existing bays keep exactly the props they had; only the new
//      bay fills in. Resize back and forth and nothing reshuffles.
//   2. The seed is saved with the module, so a scene reloads identically.
//
// Props are fixed-size, so one geometry and one material per prop type serve
// the whole scene.
import { Group, Mesh, Vector3 } from 'three';
import { createAdaptiveMaterial } from '../shaders/index.js';
import { buildParts } from './geometry.js';
import { bakeMasks } from '../art/bakeMasks.js';
import { PALETTE } from '../art/palette.js';

// Every prop is built with its base at y = 0, so a slot is just a point on a
// surface. Sizes are in metres and deliberately chunky — at this texel density
// anything under about 4 cm stops reading.
export const PROPS = {
  paper_stack: {
    colors: { base: PALETTE.paper, accent1: PALETTE.mint, accent2: PALETTE.steelDark },
    atlasCell: [1, 0],
    trimDensity: 2.2,
    parts: [
      { size: [0.21, 0.012, 0.15], at: [0, 0.006, 0], bevel: 0.004 },
      { size: [0.20, 0.010, 0.145], at: [0.006, 0.017, 0.004], bevel: 0.004 },
      { size: [0.205, 0.010, 0.15], at: [-0.004, 0.027, -0.003], bevel: 0.004 },
      { size: [0.09, 0.004, 0.06], at: [0.03, 0.034, 0.01], bevel: 0.002, accent: 1 },
    ],
  },

  clipboard: {
    colors: { base: PALETTE.oakDark, accent1: PALETTE.paper, accent2: PALETTE.steelDark },
    atlasCell: [0, 0],
    trimDensity: 2.4,
    parts: [
      { size: [0.17, 0.012, 0.23], at: [0, 0.006, 0], bevel: 0.004 },
      { size: [0.15, 0.008, 0.20], at: [0, 0.015, -0.008], bevel: 0.003, accent: 1 },
      { size: [0.07, 0.016, 0.03], at: [0, 0.020, 0.095], bevel: 0.005, accent: 2 },
    ],
  },

  mug: {
    colors: { base: PALETTE.signal, accent1: PALETTE.paper, accent2: PALETTE.walnut },
    atlasCell: [1, 0],
    trimDensity: 4.0,
    parts: [
      { size: [0.075, 0.095, 0.075], at: [0, 0.048, 0], bevel: 0.012 },
      { size: [0.022, 0.045, 0.020], at: [0.048, 0.055, 0], bevel: 0.006 },
      { size: [0.055, 0.008, 0.055], at: [0, 0.092, 0], bevel: 0.003, accent: 2 },
    ],
  },

  pen_pot: {
    colors: { base: PALETTE.steelDark, accent1: PALETTE.signal, accent2: PALETTE.teal },
    atlasCell: [0, 1],
    trimDensity: 4.0,
    parts: [
      { size: [0.07, 0.10, 0.07], at: [0, 0.05, 0], bevel: 0.008 },
      { size: [0.012, 0.09, 0.012], at: [-0.015, 0.135, 0.01], bevel: 0.003, accent: 1 },
      { size: [0.012, 0.10, 0.012], at: [0.012, 0.14, -0.008], bevel: 0.003, accent: 2 },
      { size: [0.012, 0.075, 0.012], at: [0.004, 0.125, 0.02], bevel: 0.003, accent: 1 },
    ],
  },

  med_box: {
    colors: { base: PALETTE.signal, accent1: PALETTE.paper, accent2: PALETTE.teal },
    atlasCell: [1, 0],
    trimDensity: 3.0,
    parts: [
      { size: [0.10, 0.16, 0.06], at: [0, 0.08, 0], bevel: 0.006 },
      { size: [0.07, 0.045, 0.005], at: [0, 0.10, 0.032], bevel: 0.002, accent: 1 },
    ],
  },

  bottle: {
    colors: { base: PALETTE.glass, accent1: PALETTE.paper, accent2: PALETTE.signal },
    atlasCell: [1, 1],
    trimDensity: 4.5,
    parts: [
      { size: [0.065, 0.13, 0.065], at: [0, 0.065, 0], bevel: 0.010 },
      { size: [0.035, 0.05, 0.035], at: [0, 0.152, 0], bevel: 0.006 },
      { size: [0.042, 0.022, 0.042], at: [0, 0.185, 0], bevel: 0.005, accent: 2 },
      { size: [0.055, 0.05, 0.005], at: [0, 0.07, 0.034], bevel: 0.002, accent: 1 },
    ],
  },

  till_roll: {
    colors: { base: PALETTE.paper, accent1: PALETTE.bone, accent2: PALETTE.steelDark },
    atlasCell: [1, 0],
    trimDensity: 3.5,
    parts: [
      { size: [0.085, 0.085, 0.085], at: [0, 0.043, 0], bevel: 0.014 },
      { size: [0.075, 0.006, 0.10], at: [0, 0.086, 0.05], bevel: 0.002, accent: 1 },
    ],
  },

  scales: {
    colors: { base: PALETTE.steel, accent1: PALETTE.ink, accent2: PALETTE.steelDark },
    atlasCell: [0, 1],
    trimDensity: 3.0,
    parts: [
      { size: [0.22, 0.045, 0.18], at: [0, 0.022, 0], bevel: 0.008 },
      { size: [0.14, 0.012, 0.13], at: [0, 0.051, -0.01], bevel: 0.004, accent: 2 },
      { size: [0.10, 0.035, 0.012], at: [0, 0.062, 0.078], bevel: 0.004, accent: 1 },
    ],
  },

  terminal: {
    colors: { base: PALETTE.steelDark, accent1: PALETTE.mint, accent2: PALETTE.ink },
    atlasCell: [0, 1],
    trimDensity: 2.4,
    parts: [
      { size: [0.20, 0.020, 0.14], at: [0, 0.010, 0.02], bevel: 0.005 },
      { size: [0.045, 0.10, 0.045], at: [0, 0.070, -0.03], bevel: 0.008 },
      { size: [0.30, 0.20, 0.022], at: [0, 0.220, -0.04], bevel: 0.008, accent: 2 },
      { size: [0.26, 0.155, 0.006], at: [0, 0.222, -0.026], bevel: 0.002, accent: 1 },
    ],
  },

  basket: {
    colors: { base: PALETTE.teal, accent1: PALETTE.tealDeep, accent2: PALETTE.steelDark },
    atlasCell: [1, 1],
    trimDensity: 2.6,
    parts: [
      { size: [0.24, 0.020, 0.17], at: [0, 0.010, 0], bevel: 0.005 },
      { size: [0.24, 0.085, 0.018], at: [0, 0.052, 0.078], bevel: 0.005, accent: 1 },
      { size: [0.24, 0.085, 0.018], at: [0, 0.052, -0.078], bevel: 0.005, accent: 1 },
      { size: [0.018, 0.085, 0.14], at: [0.112, 0.052, 0], bevel: 0.005, accent: 1 },
      { size: [0.018, 0.085, 0.14], at: [-0.112, 0.052, 0], bevel: 0.005, accent: 1 },
    ],
  },

  plant: {
    colors: { base: PALETTE.oakDark, accent1: PALETTE.mint, accent2: PALETTE.teal },
    atlasCell: [0, 0],
    trimDensity: 3.0,
    parts: [
      { size: [0.11, 0.10, 0.11], at: [0, 0.05, 0], bevel: 0.012 },
      { size: [0.13, 0.022, 0.13], at: [0, 0.098, 0], bevel: 0.005 },
      { size: [0.10, 0.09, 0.03], at: [-0.02, 0.15, 0.01], bevel: 0.008, accent: 1 },
      { size: [0.03, 0.11, 0.09], at: [0.03, 0.17, -0.01], bevel: 0.008, accent: 2 },
      { size: [0.08, 0.07, 0.05], at: [0.005, 0.215, 0.02], bevel: 0.008, accent: 1 },
    ],
  },

  folders: {
    colors: { base: PALETTE.bone, accent1: PALETTE.signal, accent2: PALETTE.teal },
    atlasCell: [1, 0],
    trimDensity: 3.0,
    parts: [
      { size: [0.035, 0.20, 0.14], at: [-0.05, 0.10, 0], bevel: 0.004 },
      { size: [0.035, 0.20, 0.14], at: [-0.012, 0.10, 0], bevel: 0.004, accent: 1 },
      { size: [0.035, 0.20, 0.14], at: [0.026, 0.10, 0], bevel: 0.004 },
      { size: [0.035, 0.19, 0.14], at: [0.064, 0.095, 0], bevel: 0.004, accent: 2 },
    ],
  },
};

/** Named pools, so a registry entry reads as intent rather than a list. */
export const POOLS = {
  worktop: ['paper_stack', 'clipboard', 'mug', 'pen_pot', 'till_roll', 'scales', 'folders'],
  worktopRare: ['terminal', 'plant', 'basket', 'scales'],
  shelf: ['med_box', 'bottle', 'med_box', 'bottle', 'basket', 'folders'],
  counter: ['paper_stack', 'mug', 'basket', 'till_roll', 'plant'],
};

const cache = new Map();

function propAssets(type) {
  if (!cache.has(type)) {
    const def = PROPS[type];
    if (!def) throw new Error(`unknown decor prop "${type}"`);
    const geometry = bakeMasks(buildParts(def.parts, { trimAxis: 0 }), { rays: 12, radius: 0.12 });
    geometry.computeBoundingBox();
    const bb = geometry.boundingBox;
    const material = createAdaptiveMaterial({
      baseColor: def.colors.base,
      middleColor: def.colors.accent1 ?? def.colors.base,
      accent1: def.colors.accent1 ?? null,
      accent2: def.colors.accent2 ?? null,
      sourceHalfExtents: new Vector3(
        Math.max(bb.max.x, -bb.min.x),
        Math.max(bb.max.y, -bb.min.y),
        Math.max(bb.max.z, -bb.min.z)
      ),
      margins: new Vector3(0, 0, 0), // props never stretch
      trimDensity: def.trimDensity,
      atlasCell: def.atlasCell,
    });
    cache.set(type, { geometry, material });
  }
  return cache.get(type);
}

/** Build every prop up front so a resize never stalls mid-drag. */
export function warmDecorCache() {
  for (const type of Object.keys(PROPS)) propAssets(type);
}

export function propMesh(type) {
  const { geometry, material } = propAssets(type);
  const mesh = new Mesh(geometry, material);
  mesh.userData.decor = true;
  return mesh;
}

/** Stable 32-bit hash of (seed, key) — the whole determinism story. */
function hash(seed, key) {
  let h = (2166136261 ^ seed) >>> 0;
  for (let i = 0; i < key.length; i++) {
    h ^= key.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h;
}

const unit01 = (h) => (h >>> 8) / 16777216;

/**
 * Resolve a module's slots into concrete props.
 * @param {number} seed the module's saved seed
 * @param {{key:string,pos:number[],pool:string[],chance?:number,jitter?:number,faceZ?:number}[]} slots
 */
export function resolveDecor(seed, slots) {
  const out = [];
  for (const slot of slots) {
    const h = hash(seed, slot.key);
    if (slot.chance !== undefined && unit01(h) > slot.chance) continue;

    const pool = slot.pool;
    const type = pool[hash(seed, `${slot.key}#type`) % pool.length];
    const jitter = slot.jitter ?? 0.03;
    const jx = (unit01(hash(seed, `${slot.key}#jx`)) - 0.5) * 2 * jitter;
    const jz = (unit01(hash(seed, `${slot.key}#jz`)) - 0.5) * 2 * jitter;
    // a lazy quarter-turn plus a few degrees, so nothing sits perfectly square
    const spin = Math.round(unit01(hash(seed, `${slot.key}#r`)) * 3) * (Math.PI / 2);
    const lean = (unit01(hash(seed, `${slot.key}#l`)) - 0.5) * 0.5;

    out.push({
      key: slot.key,
      type,
      position: [slot.pos[0] + jx, slot.pos[1], slot.pos[2] + jz],
      rotY: (slot.faceZ ?? 0) + spin + lean,
    });
  }
  return out;
}

/** A group of resolved props, reused across rebuilds by slot key. */
export class DecorLayer {
  constructor() {
    this.group = new Group();
    this.group.name = 'decor';
    this.live = new Map(); // key -> { type, mesh }
  }

  update(seed, slots) {
    const wanted = resolveDecor(seed, slots);
    const seen = new Set();

    for (const item of wanted) {
      seen.add(item.key);
      let entry = this.live.get(item.key);
      if (entry && entry.type !== item.type) {
        this.group.remove(entry.mesh);
        entry = null;
      }
      if (!entry) {
        entry = { type: item.type, mesh: propMesh(item.type) };
        this.group.add(entry.mesh);
        this.live.set(item.key, entry);
      }
      entry.mesh.position.set(...item.position);
      entry.mesh.rotation.y = item.rotY;
    }

    for (const [key, entry] of this.live) {
      if (seen.has(key)) continue;
      this.group.remove(entry.mesh);
      this.live.delete(key);
    }
    return this.live.size;
  }

  dispose() {
    this.group.parent?.remove(this.group);
    this.live.clear();
  }
}
