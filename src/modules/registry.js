// §8.1 — module definitions.
//
// Note how few axes are `stretch`. That is deliberate (§1): every axis
// converted from stretch to repeat makes the art problem disappear.
//
// Margins are zero on axes that do not stretch. A margin on a fixed axis would
// classify its outer band as "cap" and hand the whole module to Tier A, which
// is why the counter's front face only reads as trim once z has a real margin.
import { Vector3 } from 'three';
import { buildParts } from './geometry.js';
import { PALETTE } from '../art/palette.js';

const AXIS = { x: 0, y: 1, z: 2 };

/**
 * Schema
 *   unit          half-extents of the ONE repeatable mesh, [hx, hy, hz]
 *   margins       9-slice cap thickness per axis; 0 on non-stretch axes
 *   axes          per axis: { mode: 'repeat'|'stretch'|'fixed', ... }
 *                   repeat  → { unit, min, max }   discrete, CPU instancing
 *                   stretch → { min, max }         continuous, 9-slice on the GPU
 *   trimAxis      which axis the Tier B trim sheet tiles along
 *   atlasCell     which 2×2 cell of the Tier A atlas the caps sample
 *   mounts        sockets on this module's underside: what it can sit on
 *   provides(p)   sockets this module offers to others, in group space
 */
export const REGISTRY = {
  gondola_shelf: {
    id: 'gondola_shelf',
    label: 'Gondola shelving',
    category: 'shelving',
    cost: 340,
    unit: [0.5, 0.18, 0.25],
    margins: [0, 0, 0.06],
    trimAxis: AXIS.z,
    trimDensity: 1.6,
    atlasCell: [0, 0],
    colors: { base: PALETTE.paper, middle: PALETTE.bone, accent1: PALETTE.oak, accent2: PALETTE.steelDark },
    axes: {
      x: { mode: 'repeat', unit: 1.0, min: 1, max: 8, default: 3, label: 'bays' },
      y: { mode: 'repeat', unit: 0.36, min: 2, max: 7, default: 4, label: 'shelves' },
      z: { mode: 'stretch', min: 0.6, max: 1.6, default: 1.0, label: 'depth' },
    },
    // One bay, one tier. Repeating this in x and y is the whole module.
    build: () => [
      { size: [0.96, 0.035, 0.46], at: [0, -0.16, 0.01], accent: 1 }, // shelf board
      { size: [0.04, 0.36, 0.46], at: [-0.48, 0, 0.01] }, // post
      { size: [0.04, 0.36, 0.46], at: [0.48, 0, 0.01] }, // post
      { size: [0.96, 0.36, 0.03], at: [0, 0, -0.235] }, // back panel
      { size: [0.9, 0.045, 0.02], at: [0, -0.128, 0.225], bevel: 0.008, strip: 'detail', accent: 2 }, // label rail
    ],
    mounts: [{ tag: 'floor', normal: [0, -1, 0] }],
    provides: (p, unit) => {
      const out = [];
      out.push({ tag: 'gondola_side', pos: [unit[0] * p.x, unit[1] * p.y, 0], normal: [1, 0, 0] });
      out.push({ tag: 'gondola_side', pos: [-unit[0] * p.x, unit[1] * p.y, 0], normal: [-1, 0, 0] });
      for (let i = 0; i < p.x; i++) {
        for (let j = 0; j < p.y; j++) {
          out.push({
            tag: 'shelf_surface',
            pos: [(i - (p.x - 1) / 2) * unit[0] * 2, j * unit[1] * 2 + 0.055, 0.01],
            normal: [0, 1, 0],
          });
        }
      }
      return out;
    },
  },

  // The hero. Proportions are deliberately squat and chunky: a 0.95 worktop on
  // a 0.72 carcass, a recessed kick, a fat 0.06 worktop overhang, and a drawer
  // band on the trim sheet's detail strip so screws and a label rail land on it.
  serving_counter: {
    id: 'serving_counter',
    label: 'Dispensing desk',
    category: 'counters',
    cost: 780,
    unit: [0.6, 0.475, 0.33],
    margins: [0.14, 0, 0.1],
    trimAxis: AXIS.x,
    trimDensity: 0.85,
    atlasCell: [1, 0],
    colors: { base: PALETTE.teal, middle: PALETTE.tealDeep, accent1: PALETTE.bone, accent2: PALETTE.steelDark },
    axes: {
      x: { mode: 'stretch', min: 1.0, max: 4.0, default: 1.8, label: 'length' },
      y: { mode: 'fixed' },
      z: { mode: 'stretch', min: 0.8, max: 1.6, default: 1.0, label: 'depth' },
    },
    build: () => [
      { size: [1.02, 0.10, 0.50], at: [0, -0.425, 0.0], bevel: 0.02, accent: 2 }, // recessed kick plinth
      { size: [1.2, 0.72, 0.60], at: [0, -0.015, 0.02], bevel: 0.05 }, // carcass
      { size: [1.16, 0.17, 0.63], at: [0, 0.11, 0.02], bevel: 0.022, strip: 'detail' }, // drawer band
      { size: [1.0, 0.032, 0.05], at: [0, 0.11, 0.345], bevel: 0.014, accent: 2 }, // handle rail
      { size: [1.26, 0.075, 0.70], at: [0, 0.4375, 0.0], bevel: 0.03, accent: 1 }, // worktop, overhanging
      { size: [1.1, 0.045, 0.16], at: [0, 0.32, 0.40], bevel: 0.018, strip: 'transition', accent: 1 }, // customer shelf
    ],
    mounts: [{ tag: 'floor', normal: [0, -1, 0] }],
    provides: (p, unit) => [
      { tag: 'counter_surface', pos: [0, unit[1] * 2 + 0.005, 0], normal: [0, 1, 0] },
      { tag: 'counter_side', pos: [unit[0] * p.x, unit[1], 0], normal: [1, 0, 0] },
      { tag: 'counter_side', pos: [-unit[0] * p.x, unit[1], 0], normal: [-1, 0, 0] },
    ],
  },

  till_block: {
    id: 'till_block',
    label: 'Till / POS',
    category: 'props',
    cost: 190,
    unit: [0.17, 0.11, 0.14],
    margins: [0, 0, 0],
    trimAxis: AXIS.x,
    trimDensity: 3.0,
    atlasCell: [0, 1],
    colors: { base: PALETTE.steel, middle: PALETTE.steelDark, accent1: PALETTE.ink, accent2: PALETTE.steelDark },
    axes: { x: { mode: 'fixed' }, y: { mode: 'fixed' }, z: { mode: 'fixed' } },
    build: () => [
      { size: [0.34, 0.07, 0.28], at: [0, -0.155, 0], bevel: 0.02 }, // base
      { size: [0.3, 0.03, 0.16], at: [0, -0.1, 0.06], bevel: 0.012, strip: 'detail', accent: 2 }, // keypad
      { size: [0.28, 0.24, 0.03], at: [0, -0.01, -0.04], bevel: 0.015, rotX: -0.22, accent: 1 }, // screen
    ],
    mounts: [
      { tag: 'counter_surface', normal: [0, -1, 0] },
      { tag: 'floor', normal: [0, -1, 0] },
    ],
    provides: () => [],
  },

  fridge_cabinet: {
    id: 'fridge_cabinet',
    label: 'Refrigerated cabinet',
    category: 'cold',
    cost: 1450,
    unit: [0.4, 0.85, 0.32],
    margins: [0, 0, 0],
    trimAxis: AXIS.y,
    trimDensity: 1.1,
    atlasCell: [1, 1],
    colors: { base: PALETTE.steel, middle: PALETTE.steelDark, accent1: PALETTE.glass, accent2: PALETTE.tealDeep },
    axes: {
      x: { mode: 'repeat', unit: 0.8, min: 1, max: 4, default: 1, label: 'sections' },
      y: { mode: 'fixed' },
      z: { mode: 'fixed' },
    },
    build: () => [
      { size: [0.78, 1.7, 0.6], at: [0, 0, -0.02], bevel: 0.05 }, // carcass
      { size: [0.6, 1.24, 0.06], at: [0, 0.12, 0.3], bevel: 0.02, accent: 1 }, // door glass
      { size: [0.68, 0.16, 0.1], at: [0, -0.72, 0.28], bevel: 0.03, strip: 'detail', accent: 2 }, // grille
    ],
    mounts: [{ tag: 'floor', normal: [0, -1, 0] }],
    provides: (p, unit) => [
      { tag: 'gondola_side', pos: [unit[0] * p.x, unit[1], 0], normal: [1, 0, 0] },
      { tag: 'gondola_side', pos: [-unit[0] * p.x, unit[1], 0], normal: [-1, 0, 0] },
    ],
  },

  medicine_box: {
    id: 'medicine_box',
    label: 'Medicine box',
    category: 'props',
    cost: 4,
    unit: [0.055, 0.09, 0.035],
    margins: [0, 0, 0],
    trimAxis: AXIS.y,
    trimDensity: 6.0,
    atlasCell: [0, 1],
    colors: { base: PALETTE.signal, middle: PALETTE.oak },
    axes: {
      x: { mode: 'repeat', unit: 0.115, min: 1, max: 8, default: 4, label: 'boxes' },
      y: { mode: 'fixed' },
      z: { mode: 'fixed' },
    },
    build: () => [{ size: [0.11, 0.18, 0.07], at: [0, 0, 0], bevel: 0.012 }],
    mounts: [
      { tag: 'shelf_surface', normal: [0, -1, 0] },
      { tag: 'counter_surface', normal: [0, -1, 0] },
      { tag: 'floor', normal: [0, -1, 0] },
    ],
    provides: () => [],
  },

  queue_barrier: {
    id: 'queue_barrier',
    label: 'Queue barrier',
    category: 'props',
    cost: 60,
    unit: [0.5, 0.5, 0.06],
    margins: [0, 0, 0],
    trimAxis: AXIS.x,
    trimDensity: 1.4,
    atlasCell: [1, 1],
    colors: { base: PALETTE.walnut, middle: PALETTE.oakDark, accent1: PALETTE.oak, accent2: PALETTE.steelDark },
    axes: {
      x: { mode: 'repeat', unit: 1.0, min: 1, max: 6, default: 2, label: 'spans' },
      y: { mode: 'fixed' },
      z: { mode: 'fixed' },
    },
    build: () => [
      { size: [0.08, 1.0, 0.08], at: [-0.46, 0, 0], bevel: 0.02 },
      { size: [0.08, 1.0, 0.08], at: [0.46, 0, 0], bevel: 0.02 },
      { size: [0.96, 0.06, 0.04], at: [0, 0.36, 0], bevel: 0.015, strip: 'detail', accent: 1 },
    ],
    mounts: [{ tag: 'floor', normal: [0, -1, 0] }],
    provides: () => [],
  },
};

export const MODULE_IDS = Object.keys(REGISTRY);

/** Build the unit geometry for a module, with its trim axis baked into aTrimV. */
export const buildGeometry = (def) => buildParts(def.build(), { trimAxis: def.trimAxis });

/** §5.2 guards 1 and 2, asserted at load with the offending module named. */
export function validateRegistry() {
  for (const [id, def] of Object.entries(REGISTRY)) {
    const h = def.unit;
    def.margins.forEach((m, i) => {
      if (m > h[i]) {
        throw new Error(`module "${id}": margin ${m} exceeds source half-extent ${h[i]} on axis ${'xyz'[i]} — no stretchable middle exists (§5.2)`);
      }
    });
    for (const [axis, spec] of Object.entries(def.axes)) {
      const i = 'xyz'.indexOf(axis);
      if (spec.mode !== 'stretch') {
        if (def.margins[i] !== 0) {
          throw new Error(`module "${id}": axis ${axis} does not stretch, so its margin must be 0 or the whole module reads as a cap (§4.2)`);
        }
        continue;
      }
      const minH = h[i] * spec.min;
      if (minH < def.margins[i]) {
        throw new Error(`module "${id}": minScale on ${axis} allows H=${minH.toFixed(3)} below margin ${def.margins[i]} — caps would overlap (§5.2)`);
      }
    }
  }
}

export const defaultParams = (def) =>
  Object.fromEntries(
    Object.entries(def.axes).map(([axis, spec]) => [axis, spec.default ?? 1])
  );

export const trimAxisVector = (def) => {
  const v = new Vector3();
  v.setComponent(def.trimAxis, 1);
  return v;
};
