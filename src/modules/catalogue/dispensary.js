// Behind the counter. This is the working half of a pharmacy and it is where
// the domain detail lives: labelled racking, a fridge that has to hold 2–8 °C,
// a controlled-drugs cabinet that has to be steel and locked, and a bench with
// a sink because a lot of the job is measuring and washing up.
import { PALETTE } from '../../art/palette.js';
import { POOLS } from '../decor.js';
import { AXIS, FIXED, onFloor } from './schema.js';

export const DISPENSARY = {
  // The hero, and the project's §1 argument made visible. Real dispensing
  // furniture is built from carcasses, so the length axis is `repeat`: one
  // fully detailed 0.90m bay, instanced. Its UVs are never touched, so every
  // bolt, label holder and painted lip survives at full resolution however long
  // the run gets. Only the depth is genuinely continuous, and that one axis is
  // 9-sliced — which keeps the bullnose and the pull rigid while the middle
  // stretches.
  //
  // Numbers read off the concept sheet (§11.1 step 3), in metres:
  //   bay width 0.90 · worktop top 0.95 · worktop 0.055 thick, 0.06 overhang
  //   carcass 0.805 · kick recess 0.05 deep × 0.09 tall · stiles 0.055
  //   drawers 0.30 and 0.22 · rails 0.05 · upstand 0.10 · depth 0.66
  dispensing_desk: {
    id: 'dispensing_desk',
    label: 'Dispensing bench',
    category: 'dispensary',
    blurb: 'Worktop, drawers, upstand. Fills with work as it grows.',
    cost: 690,
    unit: [0.45, 0.525, 0.33],
    margins: [0, 0, 0.1],
    trimAxis: AXIS.x,
    trimDensity: 0.42,
    atlasCell: [0, 0],
    colors: {
      base: PALETTE.oak,
      middle: PALETTE.oakDark,
      accent1: PALETTE.bone, // worktop, upstand
      accent2: PALETTE.walnut, // pulls, kick, fittings
    },
    axes: {
      x: { mode: 'repeat', unit: 0.9, min: 1, max: 6, default: 2, label: 'bays' },
      y: FIXED,
      z: { mode: 'stretch', min: 0.85, max: 1.4, default: 1.0, label: 'depth' },
    },
    // One bay. Local origin is the bay centre; the floor is at local -0.525.
    build: () => [
      { size: [0.86, 0.09, 0.50], at: [0, -0.480, 0], bevel: 0.02, accent: 2 }, // recessed kick
      { size: [0.90, 0.805, 0.62], at: [0, -0.0325, 0], bevel: 0.04 }, // carcass
      { size: [0.055, 0.805, 0.635], at: [-0.4225, -0.0325, 0.005], bevel: 0.016 }, // stile
      { size: [0.055, 0.805, 0.635], at: [0.4225, -0.0325, 0.005], bevel: 0.016 }, // stile
      { size: [0.79, 0.050, 0.632], at: [0, -0.395, 0.006], bevel: 0.014 }, // bottom rail
      { size: [0.79, 0.045, 0.632], at: [0, -0.0175, 0.006], bevel: 0.014 }, // mid rail
      { size: [0.79, 0.050, 0.632], at: [0, 0.270, 0.006], bevel: 0.014 }, // top rail
      { size: [0.76, 0.300, 0.626], at: [0, -0.210, 0.008], bevel: 0.018 }, // deep drawer
      { size: [0.76, 0.220, 0.626], at: [0, 0.115, 0.008], bevel: 0.018 }, // shallow drawer
      { size: [0.30, 0.030, 0.050], at: [0, -0.210, 0.340], bevel: 0.012, accent: 2 }, // pull
      { size: [0.30, 0.030, 0.050], at: [0, 0.115, 0.340], bevel: 0.012, accent: 2 }, // pull
      { size: [0.15, 0.038, 0.014], at: [-0.245, -0.290, 0.334], bevel: 0.006, strip: 'detail', accent: 1 },
      { size: [0.15, 0.038, 0.014], at: [-0.245, 0.045, 0.334], bevel: 0.006, strip: 'detail', accent: 1 },
      { size: [0.94, 0.055, 0.700], at: [0, 0.3975, 0.02], bevel: 0.022, accent: 1 }, // worktop
      { size: [0.94, 0.032, 0.075], at: [0, 0.356, 0.352], bevel: 0.014, accent: 1 }, // bullnose lip
      { size: [0.94, 0.100, 0.045], at: [0, 0.475, -0.3275], bevel: 0.016, accent: 1 }, // rear upstand
      { size: [0.10, 0.050, 0.020], at: [0.28, 0.475, -0.300], bevel: 0.008, strip: 'detail', accent: 2 },
    ],
    mounts: onFloor,
    provides: (p, unit) => {
      const out = [
        { tag: 'counter_side', pos: [unit[0] * p.x, 0.5, 0], normal: [1, 0, 0] },
        { tag: 'counter_side', pos: [-unit[0] * p.x, 0.5, 0], normal: [-1, 0, 0] },
      ];
      for (let i = 0; i < p.x; i++) {
        out.push({
          tag: 'counter_surface',
          pos: [(i - (p.x - 1) / 2) * unit[0] * 2, 0.955, 0.02],
          normal: [0, 1, 0],
        });
      }
      return out;
    },
    decor: (p, unit) => {
      const slots = [];
      for (let i = 0; i < p.x; i++) {
        const x = (i - (p.x - 1) / 2) * unit[0] * 2;
        slots.push({ key: `d${i}.a`, pos: [x - 0.22, 0.955, 0.14], pool: POOLS.worktop, chance: 0.95 });
        slots.push({ key: `d${i}.b`, pos: [x + 0.19, 0.955, 0.02], pool: POOLS.worktop, chance: 0.8 });
        slots.push({ key: `d${i}.c`, pos: [x - 0.06, 0.955, -0.12], pool: POOLS.worktop, chance: 0.62 });
        if (p.x >= 3) {
          slots.push({ key: `d${i}.hero`, pos: [x + 0.10, 0.955, -0.22], pool: POOLS.worktopRare, chance: 0.45, jitter: 0.05 });
        }
      }
      return slots;
    },
  },

  // The racking a dispensed item is picked from. Shallow, densely stocked, and
  // every shelf carries a label strip — that strip is the whole reason this is
  // a separate module from retail shelving.
  dispensary_shelving: {
    id: 'dispensary_shelving',
    label: 'Dispensary racking',
    category: 'dispensary',
    blurb: 'Shallow labelled bays. Stocks itself as you add shelves.',
    cost: 260,
    unit: [0.4, 0.16, 0.16],
    margins: [0, 0, 0.045],
    trimAxis: AXIS.z,
    trimDensity: 0.8,
    atlasCell: [1, 0],
    colors: { base: PALETTE.paper, middle: PALETTE.bone, accent1: PALETTE.mint, accent2: PALETTE.steelDark },
    axes: {
      x: { mode: 'repeat', unit: 0.8, min: 1, max: 8, default: 3, label: 'bays' },
      y: { mode: 'repeat', unit: 0.32, min: 3, max: 9, default: 6, label: 'shelves' },
      z: { mode: 'stretch', min: 0.8, max: 1.5, default: 1.0, label: 'depth' },
    },
    build: () => [
      { size: [0.78, 0.028, 0.30], at: [0, -0.145, 0.005], bevel: 0.008 }, // shelf board
      { size: [0.03, 0.32, 0.30], at: [-0.385, 0, 0.005], bevel: 0.008 }, // upright
      { size: [0.03, 0.32, 0.30], at: [0.385, 0, 0.005], bevel: 0.008 }, // upright
      { size: [0.78, 0.32, 0.018], at: [0, 0, -0.151], bevel: 0.006 }, // back panel
      { size: [0.74, 0.035, 0.012], at: [0, -0.118, 0.148], bevel: 0.005, strip: 'detail', accent: 1 }, // label strip
      { size: [0.02, 0.30, 0.02], at: [0, 0, -0.14], bevel: 0.004, accent: 2 }, // bay divider
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
            pos: [(i - (p.x - 1) / 2) * unit[0] * 2, j * unit[1] * 2 + 0.045, 0.005],
            normal: [0, 1, 0],
          });
        }
      }
      return out;
    },
    // Dispensary shelves are full — that is what they look like in every real
    // dispensary, and an empty one reads as a shop that has closed down.
    decor: (p, unit) => {
      const slots = [];
      for (let i = 0; i < p.x; i++) {
        for (let j = 0; j < p.y; j++) {
          const x = (i - (p.x - 1) / 2) * unit[0] * 2;
          const y = j * unit[1] * 2 + 0.045;
          slots.push({ key: `r${i}.${j}.a`, pos: [x - 0.24, y, 0.0], pool: POOLS.dispensary, chance: 0.95, jitter: 0.02 });
          slots.push({ key: `r${i}.${j}.b`, pos: [x - 0.08, y, 0.0], pool: POOLS.dispensary, chance: 0.9, jitter: 0.02 });
          slots.push({ key: `r${i}.${j}.c`, pos: [x + 0.09, y, 0.0], pool: POOLS.dispensary, chance: 0.85, jitter: 0.02 });
          slots.push({ key: `r${i}.${j}.d`, pos: [x + 0.25, y, 0.0], pool: POOLS.dispensary, chance: 0.7, jitter: 0.02 });
        }
      }
      return slots;
    },
  },

  // BS 2881 controlled-drugs cabinet: steel, fixed, double-locked, and legally
  // required to be exactly this boring. The character is in the fittings —
  // three heavy hinges, a keypad, a warning plate.
  cd_cabinet: {
    id: 'cd_cabinet',
    label: 'CD cabinet',
    category: 'dispensary',
    blurb: 'Controlled drugs. Steel, keypad, behind the counter.',
    cost: 980,
    unit: [0.35, 0.55, 0.23],
    margins: [0, 0, 0],
    trimAxis: AXIS.y,
    trimDensity: 0.7,
    atlasCell: [0, 1],
    colors: { base: PALETTE.steel, middle: PALETTE.steelDark, accent1: PALETTE.signal, accent2: PALETTE.ink },
    axes: {
      x: { mode: 'repeat', unit: 0.7, min: 1, max: 3, default: 1, label: 'cabinets' },
      y: FIXED,
      z: FIXED,
    },
    build: () => [
      { size: [0.66, 0.07, 0.40], at: [0, -0.515, -0.01], bevel: 0.012, accent: 2 }, // plinth
      { size: [0.70, 1.03, 0.46], at: [0, 0.035, 0], bevel: 0.018 }, // carcass
      { size: [0.62, 0.94, 0.035], at: [0.01, 0.045, 0.240], bevel: 0.010 }, // door
      { size: [0.045, 0.10, 0.055], at: [-0.325, 0.400, 0.245], bevel: 0.008, accent: 2 }, // hinge
      { size: [0.045, 0.10, 0.055], at: [-0.325, 0.045, 0.245], bevel: 0.008, accent: 2 }, // hinge
      { size: [0.045, 0.10, 0.055], at: [-0.325, -0.310, 0.245], bevel: 0.008, accent: 2 }, // hinge
      { size: [0.035, 0.24, 0.045], at: [0.255, -0.06, 0.268], bevel: 0.008, accent: 2 }, // handle
      { size: [0.10, 0.14, 0.028], at: [0.225, 0.230, 0.268], bevel: 0.006, strip: 'detail', accent: 2 }, // keypad
      { size: [0.22, 0.10, 0.012], at: [-0.06, 0.400, 0.262], bevel: 0.004, strip: 'detail', accent: 1 }, // warning plate
      { size: [0.50, 0.012, 0.030], at: [0.01, -0.240, 0.262], bevel: 0.004, accent: 2 }, // door rail
    ],
    mounts: onFloor,
    provides: (p, unit) => [
      { tag: 'counter_side', pos: [unit[0] * p.x, 0.5, 0], normal: [1, 0, 0] },
      { tag: 'counter_side', pos: [-unit[0] * p.x, 0.5, 0], normal: [-1, 0, 0] },
    ],
  },

  // The vaccine fridge. Glass door so stock is visible without opening it, and
  // a temperature readout, because 2–8 °C is the whole point of the thing.
  fridge_cabinet: {
    id: 'fridge_cabinet',
    label: 'Vaccine fridge',
    category: 'dispensary',
    blurb: 'Glass door, temperature readout, 2–8 °C.',
    cost: 1450,
    unit: [0.4, 0.85, 0.32],
    margins: [0, 0, 0],
    trimAxis: AXIS.y,
    trimDensity: 0.5,
    atlasCell: [1, 1],
    colors: { base: PALETTE.steel, middle: PALETTE.steelDark, accent1: PALETTE.glass, accent2: PALETTE.tealDeep },
    axes: {
      x: { mode: 'repeat', unit: 0.8, min: 1, max: 4, default: 1, label: 'sections' },
      y: FIXED,
      z: FIXED,
    },
    build: () => [
      { size: [0.78, 1.70, 0.60], at: [0, 0, -0.02], bevel: 0.03 }, // carcass
      { size: [0.60, 1.24, 0.06], at: [0, 0.12, 0.30], bevel: 0.012, accent: 1 }, // door glass
      { size: [0.68, 0.05, 0.075], at: [0, 0.755, 0.285], bevel: 0.008, accent: 2 }, // door head rail
      { size: [0.68, 0.05, 0.075], at: [0, -0.515, 0.285], bevel: 0.008, accent: 2 }, // door foot rail
      { size: [0.035, 0.90, 0.045], at: [0.315, 0.12, 0.305], bevel: 0.008, accent: 2 }, // handle
      { size: [0.20, 0.09, 0.025], at: [-0.16, 0.800, 0.300], bevel: 0.006, strip: 'detail', accent: 2 }, // temp readout
      { size: [0.68, 0.16, 0.10], at: [0, -0.72, 0.28], bevel: 0.014, strip: 'detail', accent: 2 }, // grille
      { size: [0.72, 0.06, 0.50], at: [0, -0.83, -0.02], bevel: 0.010, accent: 2 }, // plinth
    ],
    mounts: onFloor,
    provides: (p, unit) => [
      { tag: 'gondola_side', pos: [unit[0] * p.x, unit[1], 0], normal: [1, 0, 0] },
      { tag: 'gondola_side', pos: [-unit[0] * p.x, unit[1], 0], normal: [-1, 0, 0] },
    ],
  },

  // A lot of the job is measuring and washing up.
  sink_unit: {
    id: 'sink_unit',
    label: 'Sink unit',
    category: 'dispensary',
    blurb: 'Stainless basin, mixer tap, cupboard under.',
    cost: 420,
    unit: [0.35, 0.475, 0.31],
    margins: [0, 0, 0.08],
    trimAxis: AXIS.x,
    trimDensity: 0.6,
    atlasCell: [0, 1],
    colors: { base: PALETTE.steel, middle: PALETTE.steelDark, accent1: PALETTE.bone, accent2: PALETTE.steelDark },
    axes: {
      x: { mode: 'repeat', unit: 0.7, min: 1, max: 4, default: 1, label: 'bays' },
      y: FIXED,
      z: { mode: 'stretch', min: 0.85, max: 1.3, default: 1.0, label: 'depth' },
    },
    build: () => [
      { size: [0.66, 0.09, 0.48], at: [0, -0.430, 0], bevel: 0.012, accent: 2 }, // kick
      { size: [0.70, 0.76, 0.58], at: [0, -0.005, 0], bevel: 0.022 }, // carcass
      { size: [0.32, 0.60, 0.028], at: [-0.17, -0.045, 0.295], bevel: 0.010 }, // door
      { size: [0.32, 0.60, 0.028], at: [0.17, -0.045, 0.295], bevel: 0.010 }, // door
      { size: [0.028, 0.16, 0.035], at: [-0.02, -0.045, 0.315], bevel: 0.006, accent: 2 }, // handle
      { size: [0.028, 0.16, 0.035], at: [0.02, -0.045, 0.315], bevel: 0.006, accent: 2 }, // handle
      { size: [0.74, 0.050, 0.62], at: [0, 0.400, 0], bevel: 0.014, accent: 1 }, // worktop
      { size: [0.42, 0.030, 0.34], at: [-0.02, 0.412, 0.03], bevel: 0.008, accent: 2 }, // basin rim
      { size: [0.34, 0.020, 0.27], at: [-0.02, 0.404, 0.03], bevel: 0.004, accent: 2 }, // basin well
      { size: [0.05, 0.24, 0.05], at: [-0.02, 0.545, -0.20], bevel: 0.010, accent: 2 }, // tap column
      { size: [0.045, 0.040, 0.20], at: [-0.02, 0.650, -0.11], bevel: 0.008, accent: 2 }, // spout
      { size: [0.16, 0.030, 0.030], at: [0.14, 0.645, -0.20], bevel: 0.006, accent: 2 }, // lever
    ],
    mounts: onFloor,
    provides: (p, unit) => {
      const out = [];
      for (let i = 0; i < p.x; i++) {
        out.push({
          tag: 'counter_surface',
          pos: [(i - (p.x - 1) / 2) * unit[0] * 2 + 0.24, 0.955, -0.16],
          normal: [0, 1, 0],
        });
      }
      return out;
    },
  },

  // Pharmaceutical waste and sharps. Yellow lid, foot pedal, hazard plate —
  // the one object in the room that is allowed to be ugly.
  waste_station: {
    id: 'waste_station',
    label: 'Waste & sharps',
    category: 'dispensary',
    blurb: 'Pedal bin with a sharps box on the lid.',
    cost: 85,
    unit: [0.24, 0.40, 0.23],
    margins: [0, 0, 0],
    trimAxis: AXIS.y,
    trimDensity: 1.4,
    atlasCell: [0, 1],
    colors: { base: PALETTE.bone, middle: PALETTE.putty, accent1: PALETTE.signal, accent2: PALETTE.ink },
    axes: { x: FIXED, y: FIXED, z: FIXED },
    build: () => [
      { size: [0.44, 0.60, 0.42], at: [0, -0.09, 0], bevel: 0.016 }, // body
      { size: [0.48, 0.07, 0.46], at: [0, 0.245, 0], bevel: 0.012, accent: 1 }, // lid
      { size: [0.24, 0.022, 0.16], at: [0, 0.285, 0.02], bevel: 0.005, accent: 2 }, // flap
      { size: [0.20, 0.14, 0.012], at: [0, 0.02, 0.216], bevel: 0.004, strip: 'detail', accent: 1 }, // hazard plate
      { size: [0.16, 0.035, 0.09], at: [0, -0.365, 0.235], bevel: 0.008, accent: 2 }, // pedal
      { size: [0.03, 0.30, 0.03], at: [-0.235, -0.09, -0.19], bevel: 0.006, accent: 2 }, // pedal linkage
      { size: [0.22, 0.16, 0.18], at: [0.10, 0.360, -0.06], bevel: 0.012, accent: 1 }, // sharps box
      { size: [0.14, 0.022, 0.10], at: [0.10, 0.442, -0.06], bevel: 0.004, accent: 2 }, // sharps aperture
    ],
    mounts: onFloor,
    provides: () => [],
  },
};
