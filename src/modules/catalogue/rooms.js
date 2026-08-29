// Consultation, staff and signage — the rooms off the shop floor, and the
// things that go on a wall.
import { PALETTE } from '../../art/palette.js';
import { POOLS } from '../decor.js';
import { AXIS, FIXED, onFloor } from './schema.js';

export const CONSULTATION = {
  // The brief's stretch × fixed × stretch case. A private room has to be
  // genuinely sized to the space, so both plan axes are continuous and the
  // 9-slice keeps the door post, the corner returns and the glazing bead rigid
  // while the panels between them grow.
  consultation_booth: {
    id: 'consultation_booth',
    label: 'Consultation booth',
    category: 'consultation',
    blurb: 'Private room. Glazed upper panel, door opening, sign over the door.',
    cost: 2400,
    unit: [0.9, 1.15, 0.9],
    margins: [0.26, 0, 0.26],
    trimAxis: AXIS.x,
    trimDensity: 0.4,
    atlasCell: [1, 0],
    colors: { base: PALETTE.paper, middle: PALETTE.bone, accent1: PALETTE.glass, accent2: PALETTE.teal },
    axes: {
      x: { mode: 'stretch', min: 0.85, max: 2.1, default: 1.0, label: 'width' },
      y: FIXED,
      z: { mode: 'stretch', min: 0.85, max: 2.1, default: 1.0, label: 'depth' },
    },
    build: () => [
      { size: [1.80, 2.20, 0.09], at: [0, -0.05, -0.855], bevel: 0.02 }, // back wall
      { size: [1.44, 0.72, 0.03], at: [0, 0.52, -0.800], bevel: 0.008, accent: 1 }, // glazed panel
      { size: [1.52, 0.045, 0.045], at: [0, 0.155, -0.796], bevel: 0.008, accent: 2 }, // glazing bead
      { size: [0.09, 2.20, 1.80], at: [-0.855, -0.05, 0], bevel: 0.02 }, // side wall
      { size: [0.03, 0.72, 1.44], at: [-0.800, 0.52, 0], bevel: 0.008, accent: 1 }, // glazed panel
      { size: [0.09, 2.20, 0.80], at: [0.855, -0.05, -0.50], bevel: 0.02 }, // door-side return
      { size: [0.12, 2.20, 0.12], at: [0.855, -0.05, 0.30], bevel: 0.014, accent: 2 }, // door post
      { size: [0.09, 0.22, 1.10], at: [0.855, 0.945, 0.35], bevel: 0.014, accent: 2 }, // door head
      { size: [1.90, 0.08, 1.90], at: [0, 1.11, 0], bevel: 0.02, accent: 2 }, // roof cap
      { size: [1.80, 0.10, 0.10], at: [0, -1.10, -0.855], bevel: 0.012, accent: 2 }, // skirting
      { size: [0.10, 0.10, 1.80], at: [-0.855, -1.10, 0], bevel: 0.012, accent: 2 }, // skirting
      { size: [0.60, 0.18, 0.03], at: [0.30, 0.90, 0.885], bevel: 0.008, strip: 'detail', accent: 2 }, // sign over the door
    ],
    mounts: onFloor,
    provides: () => [],
  },

  consult_chair: {
    id: 'consult_chair',
    label: 'Consultation chair',
    category: 'consultation',
    blurb: 'Padded seat, steel frame. Two per booth, facing each other.',
    cost: 130,
    unit: [0.25, 0.45, 0.25],
    margins: [0, 0, 0],
    trimAxis: AXIS.x,
    trimDensity: 1.2,
    atlasCell: [1, 1],
    colors: { base: PALETTE.teal, middle: PALETTE.tealDeep, accent1: PALETTE.mint, accent2: PALETTE.steelDark },
    axes: { x: FIXED, y: FIXED, z: FIXED },
    build: () => [
      { size: [0.44, 0.09, 0.42], at: [0, -0.010, 0.02], bevel: 0.016, accent: 1 }, // seat cushion
      { size: [0.42, 0.40, 0.09], at: [0, 0.230, -0.175], bevel: 0.016, accent: 1 }, // back cushion
      { size: [0.46, 0.035, 0.44], at: [0, -0.065, 0.02], bevel: 0.008 }, // seat pan
      { size: [0.045, 0.42, 0.045], at: [-0.19, -0.275, 0.17], bevel: 0.008, accent: 2 }, // leg
      { size: [0.045, 0.42, 0.045], at: [0.19, -0.275, 0.17], bevel: 0.008, accent: 2 }, // leg
      { size: [0.045, 0.42, 0.045], at: [-0.19, -0.275, -0.15], bevel: 0.008, accent: 2 }, // leg
      { size: [0.045, 0.42, 0.045], at: [0.19, -0.275, -0.15], bevel: 0.008, accent: 2 }, // leg
      { size: [0.42, 0.03, 0.03], at: [0, -0.400, 0.17], bevel: 0.006, accent: 2 }, // stretcher
      { size: [0.46, 0.020, 0.026], at: [0, 0.036, 0.225], bevel: 0.006, accent: 2 }, // seat piping
      { size: [0.44, 0.024, 0.026], at: [0, 0.428, -0.175], bevel: 0.006, accent: 2 }, // back piping
    ],
    mounts: onFloor,
    provides: () => [],
  },
};

export const STAFF = {
  // Straight off the reference: green steel lockers, three vent slots per door,
  // a number plate and a stubby handle. Repeat them along the wall.
  locker_bank: {
    id: 'locker_bank',
    label: 'Staff lockers',
    category: 'staff',
    blurb: 'Two tiers per bay, vented doors, numbered.',
    cost: 240,
    unit: [0.3, 0.9, 0.25],
    margins: [0, 0, 0],
    trimAxis: AXIS.y,
    trimDensity: 0.55,
    atlasCell: [0, 1],
    colors: { base: PALETTE.mint, middle: PALETTE.teal, accent1: PALETTE.tealDeep, accent2: PALETTE.steelDark },
    axes: {
      x: { mode: 'repeat', unit: 0.6, min: 1, max: 8, default: 3, label: 'bays' },
      y: FIXED,
      z: FIXED,
    },
    build: () => [
      { size: [0.60, 1.72, 0.50], at: [0, 0.04, 0], bevel: 0.016 }, // carcass
      { size: [0.56, 0.06, 0.44], at: [0, -0.865, 0], bevel: 0.010, accent: 2 }, // plinth
      { size: [0.53, 0.82, 0.030], at: [0.005, 0.455, 0.253], bevel: 0.010, accent: 1 }, // upper door
      { size: [0.53, 0.82, 0.030], at: [0.005, -0.395, 0.253], bevel: 0.010, accent: 1 }, // lower door
      { size: [0.24, 0.022, 0.016], at: [0, 0.790, 0.268], bevel: 0.004, accent: 2 }, // vent
      { size: [0.24, 0.022, 0.016], at: [0, 0.745, 0.268], bevel: 0.004, accent: 2 }, // vent
      { size: [0.24, 0.022, 0.016], at: [0, 0.700, 0.268], bevel: 0.004, accent: 2 }, // vent
      { size: [0.24, 0.022, 0.016], at: [0, -0.060, 0.268], bevel: 0.004, accent: 2 }, // vent
      { size: [0.24, 0.022, 0.016], at: [0, -0.105, 0.268], bevel: 0.004, accent: 2 }, // vent
      { size: [0.24, 0.022, 0.016], at: [0, -0.150, 0.268], bevel: 0.004, accent: 2 }, // vent
      { size: [0.030, 0.16, 0.045], at: [0.225, 0.300, 0.276], bevel: 0.006, accent: 2 }, // handle
      { size: [0.030, 0.16, 0.045], at: [0.225, -0.550, 0.276], bevel: 0.006, accent: 2 }, // handle
      { size: [0.09, 0.055, 0.010], at: [-0.17, 0.790, 0.272], bevel: 0.003, strip: 'detail', accent: 2 }, // number
      { size: [0.09, 0.055, 0.010], at: [-0.17, -0.060, 0.272], bevel: 0.003, strip: 'detail', accent: 2 }, // number
      { size: [0.62, 0.040, 0.52], at: [0, 0.920, 0], bevel: 0.012, accent: 2 }, // top cap
      { size: [0.56, 0.026, 0.46], at: [0, 0.955, 0.02], bevel: 0.010, accent: 1 }, // sloped crown
    ],
    mounts: onFloor,
    provides: (p, unit) => [
      { tag: 'gondola_side', pos: [unit[0] * p.x, unit[1], 0], normal: [1, 0, 0] },
      { tag: 'gondola_side', pos: [-unit[0] * p.x, unit[1], 0], normal: [-1, 0, 0] },
    ],
  },

  // Four drawers, label holders, a top that things get left on.
  filing_cabinet: {
    id: 'filing_cabinet',
    label: 'Filing cabinet',
    category: 'staff',
    blurb: 'Four drawers, labelled. Paperwork accumulates on top.',
    cost: 160,
    unit: [0.24, 0.665, 0.31],
    margins: [0, 0, 0],
    trimAxis: AXIS.y,
    trimDensity: 0.9,
    atlasCell: [0, 1],
    colors: { base: PALETTE.steelDark, middle: PALETTE.steel, accent1: PALETTE.bone, accent2: PALETTE.ink },
    axes: { x: FIXED, y: FIXED, z: FIXED },
    build: () => [
      { size: [0.48, 1.29, 0.62], at: [0, 0.005, 0], bevel: 0.014 }, // carcass
      { size: [0.44, 0.055, 0.60], at: [0, -0.635, 0], bevel: 0.008, accent: 2 }, // plinth
      { size: [0.50, 0.030, 0.64], at: [0, 0.665, 0], bevel: 0.008, accent: 1 }, // top cap
      ...[-0.475, -0.165, 0.145, 0.455].flatMap((y, i) => [
        { size: [0.44, 0.285, 0.028], at: [0, y, 0.310], bevel: 0.008 },
        { size: [0.15, 0.028, 0.038], at: [0.09, y, 0.332], bevel: 0.006, accent: 2 },
        { size: [0.11, 0.045, 0.012], at: [-0.10, y, 0.328], bevel: 0.003, strip: 'detail', accent: 1 },
      ]),
    ],
    mounts: onFloor,
    provides: () => [
      { tag: 'shelf_surface', pos: [0, 1.345, 0], normal: [0, 1, 0] },
    ],
    decor: () => [
      { key: 'top.a', pos: [-0.09, 1.345, 0.02], pool: POOLS.worktop, chance: 0.8, jitter: 0.04 },
      { key: 'top.b', pos: [0.11, 1.345, -0.05], pool: POOLS.worktop, chance: 0.5, jitter: 0.04 },
    ],
  },
};

export const SIGNAGE = {
  // The green cross. In most of Europe it is the single thing that says
  // "pharmacy" from across the street, so it gets its own module and hangs at
  // fascia height.
  green_cross: {
    id: 'green_cross',
    label: 'Pharmacy cross',
    category: 'signage',
    blurb: 'The green cross, at fascia height.',
    cost: 320,
    unit: [0.4, 0.4, 0.07],
    margins: [0, 0, 0],
    hover: 2.2,
    trimAxis: AXIS.x,
    trimDensity: 1.0,
    atlasCell: [1, 1],
    colors: { base: PALETTE.mint, middle: PALETTE.teal, accent1: PALETTE.paper, accent2: PALETTE.steelDark },
    axes: { x: FIXED, y: FIXED, z: FIXED },
    build: () => [
      { size: [0.78, 0.78, 0.045], at: [0, 0, -0.052], bevel: 0.010, accent: 2 }, // back plate
      { size: [0.26, 0.76, 0.09], at: [0, 0, 0], bevel: 0.014 }, // vertical bar
      { size: [0.76, 0.26, 0.09], at: [0, 0, 0], bevel: 0.014 }, // horizontal bar
      { size: [0.18, 0.62, 0.012], at: [0, 0, 0.049], bevel: 0.004, accent: 1 }, // lit face
      { size: [0.62, 0.18, 0.012], at: [0, 0, 0.049], bevel: 0.004, accent: 1 }, // lit face
      { size: [0.06, 0.06, 0.14], at: [0, 0, -0.13], bevel: 0.008, accent: 2 }, // wall stalk
    ],
    mounts: onFloor,
    provides: () => [],
  },

  // A hanging aisle sign, so a customer can find the cough and cold shelf.
  aisle_sign: {
    id: 'aisle_sign',
    label: 'Aisle sign',
    category: 'signage',
    blurb: 'Hangs over an aisle. Widen it for more panels.',
    cost: 90,
    unit: [0.45, 0.22, 0.03],
    margins: [0, 0, 0],
    hover: 2.05,
    trimAxis: AXIS.x,
    trimDensity: 0.9,
    atlasCell: [1, 0],
    colors: { base: PALETTE.bone, middle: PALETTE.putty, accent1: PALETTE.teal, accent2: PALETTE.steelDark },
    axes: {
      x: { mode: 'repeat', unit: 0.9, min: 1, max: 4, default: 1, label: 'panels' },
      y: FIXED,
      z: FIXED,
    },
    build: () => [
      { size: [0.88, 0.34, 0.035], at: [0, -0.02, 0], bevel: 0.008 }, // panel
      { size: [0.80, 0.10, 0.012], at: [0, 0.02, 0.024], bevel: 0.004, strip: 'detail', accent: 1 }, // lettering band
      { size: [0.88, 0.045, 0.055], at: [0, 0.175, 0], bevel: 0.008, accent: 2 }, // top rail
      { size: [0.025, 0.30, 0.025], at: [-0.34, 0.330, 0], bevel: 0.006, accent: 2 }, // drop rod
      { size: [0.025, 0.30, 0.025], at: [0.34, 0.330, 0], bevel: 0.006, accent: 2 }, // drop rod
    ],
    mounts: onFloor,
    provides: () => [],
  },
};
