// The customer side. Gondolas, wall runs, the OTC counter, and the small
// things that make a shop floor read as a shop: baskets by the door, a dump
// bin of offers, a barrier that steers the queue.
import { PALETTE } from '../../art/palette.js';
import { POOLS } from '../decor.js';
import { AXIS, FIXED, onFloor, onSurface } from './schema.js';

export const RETAIL = {
  gondola_shelf: {
    id: 'gondola_shelf',
    label: 'Gondola shelving',
    category: 'retail',
    blurb: 'Free-standing retail run. The canonical repeat × repeat × stretch.',
    cost: 340,
    unit: [0.5, 0.18, 0.25],
    margins: [0, 0, 0.06],
    trimAxis: AXIS.z,
    trimDensity: 0.7,
    atlasCell: [0, 0],
    colors: { base: PALETTE.paper, middle: PALETTE.bone, accent1: PALETTE.oak, accent2: PALETTE.steelDark },
    axes: {
      x: { mode: 'repeat', unit: 1.0, min: 1, max: 8, default: 3, label: 'bays' },
      y: { mode: 'repeat', unit: 0.36, min: 2, max: 7, default: 4, label: 'shelves' },
      z: { mode: 'stretch', min: 0.6, max: 1.6, default: 1.0, label: 'depth' },
    },
    build: () => [
      { size: [0.96, 0.035, 0.46], at: [0, -0.16, 0.01], accent: 1 }, // shelf board
      { size: [0.04, 0.36, 0.46], at: [-0.48, 0, 0.01] }, // post
      { size: [0.04, 0.36, 0.46], at: [0.48, 0, 0.01] }, // post
      { size: [0.96, 0.36, 0.03], at: [0, 0, -0.235] }, // back panel
      { size: [0.9, 0.045, 0.02], at: [0, -0.128, 0.225], bevel: 0.008, strip: 'detail', accent: 2 }, // price rail
    ],
    mounts: onFloor,
    provides: (p, unit) => {
      const out = [
        { tag: 'gondola_side', pos: [unit[0] * p.x, unit[1] * p.y, 0], normal: [1, 0, 0] },
        { tag: 'gondola_side', pos: [-unit[0] * p.x, unit[1] * p.y, 0], normal: [-1, 0, 0] },
      ];
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
    decor: (p, unit) => {
      const slots = [];
      for (let i = 0; i < p.x; i++) {
        for (let j = 0; j < p.y; j++) {
          const x = (i - (p.x - 1) / 2) * unit[0] * 2;
          const y = j * unit[1] * 2 + 0.075;
          slots.push({ key: `s${i}.${j}.a`, pos: [x - 0.24, y, 0.02], pool: POOLS.shelf, chance: 0.85, jitter: 0.04, pair: 0.2 });
          slots.push({ key: `s${i}.${j}.b`, pos: [x + 0.02, y, 0.02], pool: POOLS.shelf, chance: 0.7, jitter: 0.04, pair: 0.2 });
          slots.push({ key: `s${i}.${j}.c`, pos: [x + 0.28, y, 0.02], pool: POOLS.shelf, chance: 0.55, jitter: 0.04, pair: 0.2 });
        }
      }
      return slots;
    },
  },

  // Wall-mounted, so it floats at fitting height rather than standing on the
  // floor. `hover` is what lets a module be placed against a wall without a
  // wall-socket system.
  wall_shelving: {
    id: 'wall_shelving',
    label: 'Wall shelving',
    category: 'retail',
    blurb: 'Bracketed wall run. Hangs at 1.35 m.',
    cost: 190,
    unit: [0.5, 0.19, 0.15],
    margins: [0, 0, 0],
    hover: 1.35,
    trimAxis: AXIS.x,
    trimDensity: 0.55,
    atlasCell: [1, 0],
    colors: { base: PALETTE.bone, middle: PALETTE.putty, accent1: PALETTE.oak, accent2: PALETTE.steelDark },
    axes: {
      x: { mode: 'repeat', unit: 1.0, min: 1, max: 8, default: 3, label: 'bays' },
      y: { mode: 'repeat', unit: 0.38, min: 1, max: 5, default: 3, label: 'shelves' },
      z: FIXED,
    },
    build: () => [
      { size: [0.98, 0.030, 0.28], at: [0, -0.175, 0.01], bevel: 0.008, accent: 1 }, // shelf board
      { size: [0.98, 0.38, 0.022], at: [0, 0, -0.139], bevel: 0.006 }, // back rail
      { size: [0.028, 0.13, 0.22], at: [-0.42, -0.115, 0.01], bevel: 0.006, accent: 2 }, // bracket
      { size: [0.028, 0.13, 0.22], at: [0.42, -0.115, 0.01], bevel: 0.006, accent: 2 }, // bracket
      { size: [0.94, 0.030, 0.012], at: [0, -0.148, 0.153], bevel: 0.004, strip: 'detail', accent: 2 }, // price strip
    ],
    mounts: onFloor,
    provides: (p, unit) => {
      const out = [];
      for (let i = 0; i < p.x; i++) {
        for (let j = 0; j < p.y; j++) {
          out.push({
            tag: 'shelf_surface',
            pos: [(i - (p.x - 1) / 2) * unit[0] * 2, j * unit[1] * 2 + 0.03, 0.01],
            normal: [0, 1, 0],
          });
        }
      }
      return out;
    },
    decor: (p, unit) => {
      const slots = [];
      for (let i = 0; i < p.x; i++) {
        for (let j = 0; j < p.y; j++) {
          const x = (i - (p.x - 1) / 2) * unit[0] * 2;
          const y = j * unit[1] * 2 + 0.03;
          slots.push({ key: `w${i}.${j}.a`, pos: [x - 0.26, y, 0.01], pool: POOLS.shelf, chance: 0.8, jitter: 0.03, pair: 0.15 });
          slots.push({ key: `w${i}.${j}.b`, pos: [x + 0.04, y, 0.01], pool: POOLS.shelf, chance: 0.65, jitter: 0.03, pair: 0.15 });
          slots.push({ key: `w${i}.${j}.c`, pos: [x + 0.30, y, 0.01], pool: POOLS.shelf, chance: 0.45, jitter: 0.03, pair: 0.15 });
        }
      }
      return slots;
    },
  },

  // The brief's catalogue entry, kept as the continuous alternative to the
  // dispensing bench: the same furniture with a stretched length instead of
  // repeated bays. Side by side the two are the whole §1 argument.
  serving_counter: {
    id: 'serving_counter',
    label: 'OTC counter (stretch)',
    category: 'retail',
    blurb: 'Continuous-length counter. The 9-slice reference case.',
    cost: 780,
    unit: [0.6, 0.475, 0.33],
    margins: [0.14, 0, 0.1],
    trimAxis: AXIS.x,
    trimDensity: 0.42,
    atlasCell: [1, 0],
    colors: { base: PALETTE.teal, middle: PALETTE.tealDeep, accent1: PALETTE.bone, accent2: PALETTE.steelDark },
    axes: {
      x: { mode: 'stretch', min: 1.0, max: 4.0, default: 1.8, label: 'length' },
      y: FIXED,
      z: { mode: 'stretch', min: 0.8, max: 1.6, default: 1.0, label: 'depth' },
    },
    build: () => [
      { size: [1.02, 0.10, 0.50], at: [0, -0.425, 0.0], bevel: 0.02, accent: 2 }, // kick plinth
      { size: [1.2, 0.72, 0.60], at: [0, -0.015, 0.02], bevel: 0.05 }, // carcass
      { size: [1.16, 0.17, 0.63], at: [0, 0.11, 0.02], bevel: 0.022, strip: 'detail' }, // drawer band
      { size: [1.0, 0.032, 0.05], at: [0, 0.11, 0.345], bevel: 0.014, accent: 2 }, // handle rail
      { size: [1.26, 0.075, 0.70], at: [0, 0.4375, 0.0], bevel: 0.03, accent: 1 }, // worktop
      { size: [1.1, 0.045, 0.16], at: [0, 0.32, 0.40], bevel: 0.018, strip: 'transition', accent: 1 }, // customer shelf
    ],
    mounts: onFloor,
    provides: (p, unit) => [
      { tag: 'counter_surface', pos: [0, unit[1] * 2 + 0.005, 0], normal: [0, 1, 0] },
      { tag: 'counter_side', pos: [unit[0] * p.x, unit[1], 0], normal: [1, 0, 0] },
      { tag: 'counter_side', pos: [-unit[0] * p.x, unit[1], 0], normal: [-1, 0, 0] },
    ],
    // A stretch axis has no bays to hang slots off, so the slots are spaced by
    // length instead: one every 0.55m, added at the ends as it grows.
    decor: (p, unit) => {
      const half = unit[0] * p.x;
      const n = Math.max(1, Math.floor((half * 2) / 0.55));
      const slots = [];
      for (let i = 0; i < n; i++) {
        const x = -half + (i + 0.5) * ((half * 2) / n);
        slots.push({ key: `c${i}`, pos: [x, unit[1] * 2 + 0.01, -0.02], pool: POOLS.counter, chance: 0.62, pair: 0.45 });
      }
      return slots;
    },
  },

  till_block: {
    id: 'till_block',
    label: 'Till / POS',
    category: 'retail',
    blurb: 'Screen, keypad, card reader. Sits on a counter.',
    cost: 190,
    unit: [0.17, 0.11, 0.14],
    margins: [0, 0, 0],
    trimAxis: AXIS.x,
    trimDensity: 1.4,
    atlasCell: [0, 1],
    colors: { base: PALETTE.steel, middle: PALETTE.steelDark, accent1: PALETTE.ink, accent2: PALETTE.steelDark },
    axes: { x: FIXED, y: FIXED, z: FIXED },
    build: () => [
      { size: [0.34, 0.07, 0.28], at: [0, -0.155, 0], bevel: 0.02 }, // base
      { size: [0.30, 0.03, 0.16], at: [0, -0.10, 0.06], bevel: 0.012, strip: 'detail', accent: 2 }, // keypad
      { size: [0.28, 0.24, 0.03], at: [0, -0.01, -0.04], bevel: 0.015, rotX: -0.22, accent: 1 }, // screen
      { size: [0.09, 0.13, 0.05], at: [0.19, -0.06, 0.09], bevel: 0.010, rotX: -0.35, accent: 2 }, // card reader
    ],
    mounts: onSurface,
    provides: () => [],
  },

  // A stack of baskets by the door. The stack height is the repeat axis, which
  // is about as literal as "repeat" gets.
  basket_stack: {
    id: 'basket_stack',
    label: 'Basket stack',
    category: 'retail',
    blurb: 'Shopping baskets. Stack taller and you get more baskets.',
    cost: 45,
    unit: [0.23, 0.065, 0.17],
    margins: [0, 0, 0],
    trimAxis: AXIS.x,
    trimDensity: 1.6,
    atlasCell: [1, 1],
    colors: { base: PALETTE.teal, middle: PALETTE.tealDeep, accent1: PALETTE.mint, accent2: PALETTE.steelDark },
    axes: {
      x: FIXED,
      y: { mode: 'repeat', unit: 0.13, min: 2, max: 9, default: 5, label: 'baskets' },
      z: FIXED,
    },
    build: () => [
      { size: [0.42, 0.020, 0.30], at: [0, -0.055, 0], bevel: 0.006 }, // base
      { size: [0.42, 0.10, 0.022], at: [0, 0.0, 0.145], bevel: 0.006, accent: 1 }, // side
      { size: [0.42, 0.10, 0.022], at: [0, 0.0, -0.145], bevel: 0.006, accent: 1 }, // side
      { size: [0.022, 0.10, 0.26], at: [0.20, 0.0, 0], bevel: 0.006, accent: 1 }, // end
      { size: [0.022, 0.10, 0.26], at: [-0.20, 0.0, 0], bevel: 0.006, accent: 1 }, // end
      { size: [0.24, 0.018, 0.018], at: [0, 0.058, 0], bevel: 0.005, accent: 2 }, // handle bar
    ],
    mounts: onFloor,
    provides: () => [],
  },

  // The offers bin by the till. A header card on a post, because that is what
  // makes it read as a promotion rather than a crate.
  promo_bin: {
    id: 'promo_bin',
    label: 'Offers dump bin',
    category: 'retail',
    blurb: 'Header card and a bin of stock. Fills as it widens.',
    cost: 120,
    unit: [0.33, 0.55, 0.28],
    margins: [0, 0, 0],
    trimAxis: AXIS.x,
    trimDensity: 0.9,
    atlasCell: [1, 0],
    colors: { base: PALETTE.signal, middle: PALETTE.oakDark, accent1: PALETTE.paper, accent2: PALETTE.steelDark },
    axes: {
      x: { mode: 'repeat', unit: 0.66, min: 1, max: 4, default: 1, label: 'bins' },
      y: FIXED,
      z: FIXED,
    },
    build: () => [
      { size: [0.60, 0.055, 0.48], at: [0, -0.520, 0], bevel: 0.010, accent: 2 }, // base
      { size: [0.62, 0.42, 0.50], at: [0, -0.280, 0], bevel: 0.018 }, // bin body
      { size: [0.66, 0.045, 0.54], at: [0, -0.060, 0], bevel: 0.010, accent: 2 }, // rim
      { size: [0.035, 0.46, 0.035], at: [-0.26, 0.180, -0.20], bevel: 0.008, accent: 2 }, // post
      { size: [0.035, 0.46, 0.035], at: [0.26, 0.180, -0.20], bevel: 0.008, accent: 2 }, // post
      { size: [0.64, 0.24, 0.022], at: [0, 0.420, -0.20], bevel: 0.008, accent: 1 }, // header card
      { size: [0.50, 0.06, 0.012], at: [0, 0.455, -0.185], bevel: 0.004, strip: 'detail', accent: 2 }, // header lettering
    ],
    mounts: onFloor,
    provides: (p, unit) => {
      const out = [];
      for (let i = 0; i < p.x; i++) {
        out.push({
          tag: 'shelf_surface',
          pos: [(i - (p.x - 1) / 2) * unit[0] * 2, 0.48, 0],
          normal: [0, 1, 0],
        });
      }
      return out;
    },
    decor: (p, unit) => {
      const slots = [];
      for (let i = 0; i < p.x; i++) {
        const x = (i - (p.x - 1) / 2) * unit[0] * 2;
        slots.push({ key: `p${i}.a`, pos: [x - 0.14, 0.47, 0.06], pool: POOLS.shelf, chance: 0.9, jitter: 0.05 });
        slots.push({ key: `p${i}.b`, pos: [x + 0.13, 0.47, -0.02], pool: POOLS.shelf, chance: 0.85, jitter: 0.05 });
        slots.push({ key: `p${i}.c`, pos: [x, 0.47, 0.13], pool: POOLS.shelf, chance: 0.7, jitter: 0.05 });
      }
      return slots;
    },
  },

  queue_barrier: {
    id: 'queue_barrier',
    label: 'Queue barrier',
    category: 'retail',
    blurb: 'Posts and a rail. Steers the queue away from the consultation door.',
    cost: 60,
    unit: [0.5, 0.5, 0.06],
    margins: [0, 0, 0],
    trimAxis: AXIS.x,
    trimDensity: 0.6,
    atlasCell: [1, 1],
    colors: { base: PALETTE.walnut, middle: PALETTE.oakDark, accent1: PALETTE.oak, accent2: PALETTE.steelDark },
    axes: {
      x: { mode: 'repeat', unit: 1.0, min: 1, max: 6, default: 2, label: 'spans' },
      y: FIXED,
      z: FIXED,
    },
    build: () => [
      { size: [0.08, 1.0, 0.08], at: [-0.46, 0, 0], bevel: 0.02 },
      { size: [0.08, 1.0, 0.08], at: [0.46, 0, 0], bevel: 0.02 },
      { size: [0.96, 0.06, 0.04], at: [0, 0.36, 0], bevel: 0.015, strip: 'detail', accent: 1 },
      { size: [0.14, 0.03, 0.14], at: [-0.46, -0.485, 0], bevel: 0.008, accent: 2 }, // foot
      { size: [0.14, 0.03, 0.14], at: [0.46, -0.485, 0], bevel: 0.008, accent: 2 }, // foot
    ],
    mounts: onFloor,
    provides: () => [],
  },

  medicine_box: {
    id: 'medicine_box',
    label: 'Stock boxes',
    category: 'retail',
    blurb: 'A run of boxes. Mostly here for the instancing stress test.',
    cost: 4,
    unit: [0.055, 0.09, 0.035],
    margins: [0, 0, 0],
    trimAxis: AXIS.y,
    trimDensity: 2.6,
    atlasCell: [1, 0],
    colors: { base: PALETTE.signal, middle: PALETTE.oak },
    axes: {
      x: { mode: 'repeat', unit: 0.115, min: 1, max: 8, default: 4, label: 'boxes' },
      y: FIXED,
      z: FIXED,
    },
    build: () => [
      { size: [0.11, 0.18, 0.07], at: [0, 0, 0], bevel: 0.012 },
      { size: [0.075, 0.05, 0.006], at: [0, 0.02, 0.037], bevel: 0.002, strip: 'detail', accent: 1 },
    ],
    mounts: onSurface,
    provides: () => [],
  },
};
