// Behind the counter. This is the working half of a pharmacy and it is where
// the domain detail lives: labelled racking, a fridge that has to hold 2–8 °C,
// a controlled-drugs cabinet that has to be steel and locked, and a bench with
// a sink because a lot of the job is measuring and washing up.
import { PALETTE } from '../../art/palette.js';
import { POOLS } from '../decor.js';
import { AXIS, FIXED, onFloor } from './schema.js';
import {
  ACCENT, DARK, FRAME, GLASS,
  capTray, keypad, plate, posts, studs, vents, worktop,
} from './fittings.js';

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
    // Rebuilt from docs/concept/dispensing_desk.png. The sheet reorganised the
    // whole object around a PROUD STEEL FRAME: four corner posts standing off
    // the panels, studded top and bottom, with warm oak drawer fronts infilled
    // between them and a cream worktop banded in shadow where it meets the
    // carcass. That inversion — light frame, dark panels — is the single thing
    // the twenty sheets have in common, and it is what the catalogue now does.
    colors: {
      base: PALETTE.oak, // drawer fronts and carcass
      middle: PALETTE.oakDark,
      accent1: PALETTE.paper, // FRAME  — posts, rails, worktop, upstand
      accent2: PALETTE.tealDeep, // ACCENT — plinth and pulls
      accent3: PALETTE.steelDark, // DARK   — studs, shadow band, reveals
      accent4: PALETTE.glass, // GLASS  — label windows
    },
    axes: {
      x: { mode: 'repeat', unit: 0.9, min: 1, max: 6, default: 2, label: 'bays' },
      y: FIXED,
      z: { mode: 'stretch', min: 0.85, max: 1.4, default: 1.0, label: 'depth' },
    },
    // One bay. Local origin is the bay centre; the floor is at local -0.525.
    build: () => [
      { size: [0.86, 0.075, 0.50], at: [0, -0.4875, 0], bevel: 0.02, accent: ACCENT }, // recessed kick
      { size: [0.90, 0.805, 0.62], at: [0, -0.0325, 0], bevel: 0.04 }, // carcass
      // the frame: four posts standing proud of the panels between them
      ...posts({ at: [0, -0.0325, 0.005], w: 0.90, h: 0.805, d: 0.64, thickness: 0.055 }),
      { size: [0.79, 0.050, 0.632], at: [0, -0.395, 0.006], bevel: 0.014, accent: FRAME }, // bottom rail
      { size: [0.79, 0.045, 0.632], at: [0, -0.0175, 0.006], bevel: 0.014, accent: FRAME }, // mid rail
      { size: [0.79, 0.050, 0.632], at: [0, 0.270, 0.006], bevel: 0.014, accent: FRAME }, // top rail
      ...studs({ at: [-0.4225, 0.230, 0.335], spread: [0, 0.055] }),
      ...studs({ at: [0.4225, 0.230, 0.335], spread: [0, 0.055] }),
      ...studs({ at: [-0.4225, -0.355, 0.335], spread: [0, 0.055] }),
      ...studs({ at: [0.4225, -0.355, 0.335], spread: [0, 0.055] }),
      { size: [0.76, 0.300, 0.626], at: [0, -0.210, 0.008], bevel: 0.018 }, // deep drawer
      { size: [0.76, 0.220, 0.626], at: [0, 0.115, 0.008], bevel: 0.018 }, // shallow drawer
      { size: [0.74, 0.016, 0.020], at: [0, -0.052, 0.320], bevel: 0.005, accent: DARK }, // drawer reveal
      { size: [0.74, 0.016, 0.020], at: [0, 0.232, 0.320], bevel: 0.005, accent: DARK }, // drawer reveal
      { size: [0.34, 0.032, 0.055], at: [0, -0.210, 0.342], bevel: 0.012, accent: ACCENT }, // pull
      { size: [0.34, 0.032, 0.055], at: [0, 0.115, 0.342], bevel: 0.012, accent: ACCENT }, // pull
      { size: [0.36, 0.014, 0.022], at: [0, -0.232, 0.352], bevel: 0.004, accent: DARK }, // pull shadow
      { size: [0.36, 0.014, 0.022], at: [0, 0.093, 0.352], bevel: 0.004, accent: DARK },
      ...plate({ at: [-0.255, -0.300, 0.330], w: 0.16, h: 0.045 }), // label holder
      ...plate({ at: [-0.255, 0.035, 0.330], w: 0.16, h: 0.045 }),
      // the worktop, banded underneath: the band separates the top plane from
      // the carcass front by value, exactly where a drawn outline used to
      ...worktop({ at: [0, 0.3975, 0.02], w: 0.94, d: 0.700, thickness: 0.055, lip: 0.028 }),
      { size: [0.94, 0.030, 0.078], at: [0, 0.352, 0.352], bevel: 0.012, accent: FRAME }, // front lip
      { size: [0.94, 0.100, 0.045], at: [0, 0.475, -0.3275], bevel: 0.016, accent: FRAME }, // rear upstand
      ...plate({ at: [0.29, 0.478, -0.298], w: 0.13, h: 0.052 }), // socket block
      { size: [0.075, 0.030, 0.075], at: [-0.36, -0.535, 0.19], bevel: 0.010, accent: DARK }, // foot pad
      { size: [0.075, 0.030, 0.075], at: [0.36, -0.535, 0.19], bevel: 0.010, accent: DARK }, // foot pad
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
        slots.push({ key: `d${i}.a`, pos: [x - 0.22, 0.955, 0.14], pool: POOLS.worktop, chance: 0.95, pair: 0.55 });
        slots.push({ key: `d${i}.b`, pos: [x + 0.19, 0.955, 0.02], pool: POOLS.worktop, chance: 0.8, pair: 0.4 });
        slots.push({ key: `d${i}.c`, pos: [x - 0.06, 0.955, -0.12], pool: POOLS.worktop, chance: 0.62, pair: 0.3 });
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
    // From docs/concept/dispensary_shelving.png: a warm oak carcass, and a
    // CREAM LABEL STRIP running the full front edge of every single shelf. On
    // the sheet those strips are the loudest thing about the object — they are
    // what makes a bank of open shelves read as a dispensary rather than as
    // a bookcase, so here the strip is a full-width fitting with its own window
    // rather than the thin bead it was.
    colors: {
      base: PALETTE.oak,
      middle: PALETTE.oakDark,
      accent1: PALETTE.paper, // FRAME  — uprights, shelf boards, label strips
      accent2: PALETTE.teal, // ACCENT — the front lip
      accent3: PALETTE.walnut, // DARK   — bay dividers, back shadow
      accent4: PALETTE.glass, // GLASS  — the label window
    },
    axes: {
      x: { mode: 'repeat', unit: 0.8, min: 1, max: 8, default: 3, label: 'bays' },
      y: { mode: 'repeat', unit: 0.32, min: 3, max: 9, default: 6, label: 'shelves' },
      z: { mode: 'stretch', min: 0.8, max: 1.5, default: 1.0, label: 'depth' },
    },
    build: () => [
      { size: [0.78, 0.028, 0.30], at: [0, -0.145, 0.005], bevel: 0.008 }, // shelf board, oak like the sheet
      { size: [0.045, 0.32, 0.31], at: [-0.3875, 0, 0.005], bevel: 0.010, accent: FRAME }, // upright
      { size: [0.045, 0.32, 0.31], at: [0.3875, 0, 0.005], bevel: 0.010, accent: FRAME }, // upright
      { size: [0.78, 0.32, 0.018], at: [0, 0, -0.151], bevel: 0.006 }, // back panel
      { size: [0.74, 0.030, 0.018], at: [0, -0.126, 0.150], bevel: 0.005, accent: FRAME }, // label strip
      { size: [0.70, 0.018, 0.010], at: [0, -0.126, 0.158], bevel: 0.003, strip: 'detail', accent: GLASS }, // its window
      { size: [0.76, 0.016, 0.020], at: [0, -0.152, 0.148], bevel: 0.005, accent: ACCENT }, // shelf front lip
      { size: [0.018, 0.28, 0.26], at: [-0.13, 0.015, -0.02], bevel: 0.004, accent: DARK }, // bay divider
      { size: [0.018, 0.28, 0.26], at: [0.17, 0.015, -0.02], bevel: 0.004, accent: DARK }, // bay divider
      ...studs({ at: [-0.3875, 0, 0.163], spread: [0, 0.115], size: 0.018 }),
      ...studs({ at: [0.3875, 0, 0.163], spread: [0, 0.115], size: 0.018 }),
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
          slots.push({ key: `r${i}.${j}.a`, pos: [x - 0.24, y, 0.0], pool: POOLS.dispensary, chance: 0.95, jitter: 0.02, pair: 0 });
          slots.push({ key: `r${i}.${j}.b`, pos: [x - 0.08, y, 0.0], pool: POOLS.dispensary, chance: 0.9, jitter: 0.02, pair: 0 });
          slots.push({ key: `r${i}.${j}.c`, pos: [x + 0.09, y, 0.0], pool: POOLS.dispensary, chance: 0.85, jitter: 0.02, pair: 0 });
          slots.push({ key: `r${i}.${j}.d`, pos: [x + 0.25, y, 0.0], pool: POOLS.dispensary, chance: 0.7, jitter: 0.02, pair: 0 });
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
    // docs/concept/cd_cabinet.png is the clearest statement of the frame rule in
    // the whole set: a pale steel cage — four posts, a lidded top tray, a
    // plinth band — with near-black door and side panels dropped into it. Every
    // frame member is studded at both ends. Nothing else about the shape
    // changed; the object went from a grey box to a safe on the strength of
    // where the light and dark went.
    colors: {
      base: PALETTE.steelDark, // door and side panels
      middle: PALETTE.steelDark,
      accent1: PALETTE.steel, // FRAME  — posts, cap, plinth
      accent2: PALETTE.signal, // ACCENT — the keypad's live keys
      accent3: PALETTE.ink, // DARK   — hinges, handle, vents
      accent4: PALETTE.glass, // GLASS  — the warning plate
    },
    axes: {
      x: { mode: 'repeat', unit: 0.7, min: 1, max: 3, default: 1, label: 'cabinets' },
      y: FIXED,
      z: FIXED,
    },
    build: () => [
      { size: [0.66, 0.055, 0.42], at: [0, -0.5225, -0.01], bevel: 0.010, accent: DARK }, // plinth shadow
      { size: [0.68, 0.055, 0.44], at: [0, -0.472, -0.005], bevel: 0.010, accent: FRAME }, // plinth band
      { size: [0.70, 0.94, 0.46], at: [0, 0.020, 0], bevel: 0.018 }, // carcass
      ...posts({ at: [0, 0.020, 0], w: 0.70, h: 0.95, d: 0.47, thickness: 0.05, bevel: 0.012 }),
      ...capTray({ at: [0, 0.520, 0], w: 0.72, d: 0.48, rim: 0.05 }),
      ...studs({ at: [0, 0.520, 0.245], spread: [0.31, 0], size: 0.020 }),
      { size: [0.60, 0.86, 0.035], at: [0.015, 0.020, 0.242], bevel: 0.010 }, // door
      { size: [0.62, 0.020, 0.045], at: [0.015, 0.462, 0.245], bevel: 0.005, accent: DARK }, // door head reveal
      { size: [0.62, 0.020, 0.045], at: [0.015, -0.422, 0.245], bevel: 0.005, accent: DARK }, // door foot reveal
      // three heavy barrel hinges: the legal giveaway that this is a CD cabinet
      ...[0.360, 0.020, -0.320].flatMap((y) => [
        { size: [0.055, 0.105, 0.060], at: [-0.318, y, 0.248], bevel: 0.010, accent: DARK },
        { size: [0.070, 0.045, 0.030], at: [-0.318, y, 0.262], bevel: 0.006, accent: FRAME },
      ]),
      { size: [0.032, 0.26, 0.050], at: [0.262, -0.075, 0.270], bevel: 0.008, accent: DARK }, // handle
      { size: [0.048, 0.045, 0.030], at: [0.262, 0.048, 0.258], bevel: 0.006, accent: FRAME }, // handle bracket
      { size: [0.048, 0.045, 0.030], at: [0.262, -0.198, 0.258], bevel: 0.006, accent: FRAME },
      ...keypad({ at: [0.215, 0.210, 0.268] }),
      ...plate({ at: [0.190, 0.395, 0.264], w: 0.19, h: 0.075 }), // warning plate
      ...vents({ at: [-0.352, -0.300, 0.06], n: 5, w: 0.18, thickness: 0.016, gap: 0.028, depth: 0.012, axis: 'x' }),
      { size: [0.024, 0.020, 0.40], at: [-0.352, 0.020, 0], bevel: 0.005, accent: DARK }, // side seam
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
    // docs/concept/fridge_cabinet.png: warm oak side panels in a steel cage,
    // a glass door set into a thick pale surround rather than floating in the
    // carcass, a dark readout right above the door where you would actually
    // read it, and an oak condenser grille along the foot. The oak is the
    // surprise and it is why the sheet works — a clinical object with a warm
    // body sits in this room instead of punching a grey hole in it.
    colors: {
      base: PALETTE.oak, // side panels and grille
      middle: PALETTE.oakDark,
      accent1: PALETTE.steel, // FRAME  — posts, door surround, top tray
      accent2: PALETTE.tealDeep, // ACCENT — the cold band under the cap
      accent3: PALETTE.steelDark, // DARK   — fittings, readout body, plinth
      accent4: PALETTE.glass, // GLASS  — the door and the readout face
    },
    axes: {
      x: { mode: 'repeat', unit: 0.8, min: 1, max: 4, default: 1, label: 'sections' },
      y: FIXED,
      z: FIXED,
    },
    build: () => [
      { size: [0.72, 0.06, 0.52], at: [0, -0.820, -0.02], bevel: 0.010, accent: DARK }, // plinth
      { size: [0.78, 1.64, 0.60], at: [0, 0.010, -0.02], bevel: 0.03 }, // carcass
      ...posts({ at: [0, 0.010, -0.02], w: 0.78, h: 1.66, d: 0.61, thickness: 0.06, bevel: 0.014 }),
      { size: [0.80, 0.055, 0.62], at: [0, 0.775, -0.02], bevel: 0.010, accent: ACCENT }, // cold band
      ...capTray({ at: [0, 0.828, -0.02], w: 0.80, d: 0.62, rim: 0.055 }),
      // the door: glass set into a pale surround, not floating in the carcass
      { size: [0.68, 1.30, 0.055], at: [0, 0.075, 0.290], bevel: 0.012, accent: FRAME },
      { size: [0.56, 1.18, 0.030], at: [0, 0.075, 0.312], bevel: 0.008, accent: GLASS },
      { size: [0.68, 0.045, 0.075], at: [0, 0.700, 0.292], bevel: 0.008, accent: DARK }, // head rail
      { size: [0.68, 0.045, 0.075], at: [0, -0.550, 0.292], bevel: 0.008, accent: DARK }, // foot rail
      { size: [0.034, 0.86, 0.050], at: [0.300, 0.075, 0.322], bevel: 0.008, accent: DARK }, // handle
      { size: [0.052, 0.042, 0.032], at: [0.300, 0.470, 0.308], bevel: 0.006, accent: FRAME }, // handle bracket
      { size: [0.052, 0.042, 0.032], at: [0.300, -0.320, 0.308], bevel: 0.006, accent: FRAME },
      ...plate({ at: [-0.135, 0.775, 0.300], w: 0.22, h: 0.085, surround: DARK }), // temperature readout
      { size: [0.70, 0.17, 0.10], at: [0, -0.715, 0.285], bevel: 0.012 }, // condenser grille
      ...vents({ at: [0, -0.715, 0.340], n: 4, w: 0.60, thickness: 0.018, gap: 0.040, depth: 0.014 }),
      { size: [0.016, 0.075, 0.14], at: [-0.394, 0.400, 0.10], bevel: 0.004, accent: DARK }, // side data plate
      { size: [0.010, 0.052, 0.115], at: [-0.400, 0.400, 0.10], bevel: 0.003, strip: 'detail', accent: GLASS },
      ...studs({ at: [0, 0.828, 0.290], spread: [0.34, 0], size: 0.022 }),
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
    // docs/concept/sink_unit.png. Two things came off that sheet. The basin is
    // a genuine WELL — a dark recess inside a raised rim, not a plate laid on
    // the top — and the mixer is square-sectioned, a column with a square
    // spout, which is both truer to real dispensary fittings and the only
    // version of a tap this part system can express honestly.
    //
    // Its worktop also now lands at 0.95, the same height as the dispensing
    // bench, so the two run together instead of stepping 5 cm.
    colors: {
      base: PALETTE.steelDark, // door panels
      middle: PALETTE.steelDark,
      accent1: PALETTE.steel, // FRAME  — posts, worktop, rails
      accent2: PALETTE.signal, // ACCENT — the one warm mark on a cold object
      accent3: PALETTE.ink, // DARK   — basin well, vents, handles
      accent4: PALETTE.glass, // GLASS  — label windows
    },
    axes: {
      x: { mode: 'repeat', unit: 0.7, min: 1, max: 4, default: 1, label: 'bays' },
      y: FIXED,
      z: { mode: 'stretch', min: 0.85, max: 1.3, default: 1.0, label: 'depth' },
    },
    build: () => [
      { size: [0.66, 0.085, 0.48], at: [0, -0.4325, 0], bevel: 0.012, accent: DARK }, // kick
      { size: [0.70, 0.79, 0.58], at: [0, 0.005, 0], bevel: 0.022 }, // carcass
      ...posts({ at: [0, 0.005, 0], w: 0.70, h: 0.80, d: 0.59, thickness: 0.05, bevel: 0.012 }),
      { size: [0.31, 0.62, 0.030], at: [-0.175, -0.030, 0.296], bevel: 0.010 }, // door
      { size: [0.31, 0.62, 0.030], at: [0.175, -0.030, 0.296], bevel: 0.010 }, // door
      { size: [0.022, 0.66, 0.034], at: [0, -0.030, 0.294], bevel: 0.005, accent: FRAME }, // meeting stile
      { size: [0.042, 0.042, 0.040], at: [-0.042, -0.030, 0.316], bevel: 0.008, accent: DARK }, // knob
      { size: [0.042, 0.042, 0.040], at: [0.042, -0.030, 0.316], bevel: 0.008, accent: DARK }, // knob
      ...studs({ at: [-0.325, 0.005, 0.298], spread: [0, 0.345], size: 0.020 }),
      ...studs({ at: [0.325, 0.005, 0.298], spread: [0, 0.345], size: 0.020 }),
      ...vents({ at: [-0.352, -0.120, 0.10], n: 5, w: 0.22, thickness: 0.016, gap: 0.030, depth: 0.012, axis: 'x' }),
      ...plate({ at: [0.215, 0.310, 0.298], w: 0.14, h: 0.048 }),
      { size: [0.74, 0.055, 0.62], at: [0, 0.4475, 0], bevel: 0.014, accent: FRAME }, // worktop, top at 0.95
      // the basin: a raised rim with a real recess inside it
      { size: [0.44, 0.036, 0.36], at: [-0.02, 0.470, 0.03], bevel: 0.008, accent: FRAME },
      { size: [0.36, 0.026, 0.28], at: [-0.02, 0.478, 0.03], bevel: 0.005, accent: DARK },
      { size: [0.30, 0.016, 0.22], at: [-0.02, 0.468, 0.03], bevel: 0.004, accent: DARK },
      { size: [0.055, 0.26, 0.055], at: [-0.02, 0.600, -0.21], bevel: 0.010, accent: FRAME }, // mixer column
      { size: [0.048, 0.048, 0.22], at: [-0.02, 0.708, -0.115], bevel: 0.008, accent: FRAME }, // square spout
      { size: [0.15, 0.030, 0.032], at: [0.145, 0.705, -0.21], bevel: 0.006, accent: DARK }, // lever
      { size: [0.030, 0.030, 0.030], at: [0.075, 0.705, -0.21], bevel: 0.006, accent: ACCENT }, // lever boss
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
    // docs/concept/waste_station.png. The sheet BANDS the body — a cream belt
    // across a mint carcass — and puts a real grille on the front, and those
    // two things do all the work: the band gives a small object a horizontal
    // line to read against, and the grille says clinical waste rather than
    // kitchen bin. The pedal sits on a projecting tray with the linkage rod
    // visibly running up the back corner to the lid, which is how the thing
    // actually works.
    colors: {
      base: PALETTE.mint, // body
      middle: PALETTE.teal,
      accent1: PALETTE.paper, // FRAME  — the belt, the sharps box
      accent2: PALETTE.signal, // ACCENT — the hazard plate
      accent3: PALETTE.steelDark, // DARK   — grille, pedal, linkage
      accent4: PALETTE.glass, // GLASS  — the sharps label
    },
    axes: { x: FIXED, y: FIXED, z: FIXED },
    build: () => [
      { size: [0.44, 0.58, 0.42], at: [0, -0.10, 0], bevel: 0.016 }, // body
      { size: [0.455, 0.13, 0.435], at: [0, 0.055, 0], bevel: 0.010, accent: FRAME }, // the belt
      { size: [0.46, 0.020, 0.44], at: [0, -0.015, 0], bevel: 0.005, accent: DARK }, // belt shadow
      { size: [0.48, 0.075, 0.46], at: [0, 0.242, 0], bevel: 0.012 }, // lid slab
      { size: [0.42, 0.030, 0.40], at: [0, 0.290, 0], bevel: 0.008, accent: FRAME }, // lid rim
      { size: [0.24, 0.026, 0.16], at: [0, 0.312, 0.02], bevel: 0.005, accent: DARK }, // flap
      { size: [0.26, 0.20, 0.020], at: [-0.04, 0.055, 0.215], bevel: 0.006, accent: DARK }, // grille panel
      ...vents({ at: [-0.04, 0.055, 0.228], n: 5, w: 0.21, thickness: 0.018, gap: 0.036, depth: 0.010, accent: FRAME }),
      ...plate({ at: [0.135, -0.230, 0.214], w: 0.13, h: 0.10, accent: ACCENT, surround: FRAME }), // hazard plate
      { size: [0.20, 0.026, 0.11], at: [0, -0.372, 0.245], bevel: 0.006, accent: FRAME }, // pedal tray
      { size: [0.15, 0.030, 0.075], at: [0, -0.348, 0.250], bevel: 0.008, accent: DARK }, // pedal
      { size: [0.026, 0.60, 0.026], at: [-0.222, 0.030, -0.196], bevel: 0.006, accent: DARK }, // linkage rod
      { size: [0.045, 0.030, 0.045], at: [-0.222, 0.300, -0.196], bevel: 0.006, accent: DARK }, // linkage elbow
      { size: [0.22, 0.17, 0.19], at: [0.10, 0.365, -0.06], bevel: 0.012, accent: FRAME }, // sharps box
      { size: [0.16, 0.026, 0.11], at: [0.10, 0.455, -0.06], bevel: 0.005, accent: DARK }, // sharps aperture
      { size: [0.13, 0.070, 0.010], at: [0.10, 0.360, 0.038], bevel: 0.003, strip: 'detail', accent: GLASS }, // its label
    ],
    mounts: onFloor,
    provides: () => [],
  },
};
