// The customer side. Gondolas, wall runs, the OTC counter, and the small
// things that make a shop floor read as a shop: baskets by the door, a dump
// bin of offers, a barrier that steers the queue.
import { PALETTE } from '../../art/palette.js';
import { POOLS } from '../decor.js';
import { AXIS, FIXED, onFloor, onSurface } from './schema.js';
import { ACCENT, DARK, FRAME, GLASS, plate, studs, vents, worktop } from './fittings.js';

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
    // docs/concept/gondola_shelf.png. The posts on that sheet stand PROUD of
    // the carcass, full height and capped, with the cream panels reading as
    // infill between them — the same frame-and-panel move as the dispensary,
    // and it is what stops a long retail run reading as one extruded slab. The
    // shelf boards went warm oak against the cream, so a stocked shelf has a
    // ground to sit on.
    colors: {
      base: PALETTE.paper, // carcass and back panels
      middle: PALETTE.bone,
      accent1: PALETTE.steel, // FRAME  — the proud end posts and their caps
      accent2: PALETTE.teal, // ACCENT — the price rail
      accent3: PALETTE.oak, // shelf boards and the front band: warm, not dark
      accent4: PALETTE.glass, // GLASS  — price windows
    },
    axes: {
      x: { mode: 'repeat', unit: 1.0, min: 1, max: 8, default: 3, label: 'bays' },
      y: { mode: 'repeat', unit: 0.36, min: 2, max: 7, default: 4, label: 'shelves' },
      z: { mode: 'stretch', min: 0.6, max: 1.6, default: 1.0, label: 'depth' },
    },
    build: () => [
      { size: [0.96, 0.035, 0.46], at: [0, -0.16, 0.01], bevel: 0.008, mat: 'wood', accent: DARK }, // shelf board
      { size: [0.94, 0.030, 0.035], at: [0, -0.150, 0.222], bevel: 0.006, mat: 'wood', accent: DARK }, // front band
      { size: [0.055, 0.36, 0.055], at: [-0.4875, 0, 0.222], bevel: 0.012, mat: 'steel', accent: FRAME }, // proud post
      { size: [0.055, 0.36, 0.055], at: [0.4875, 0, 0.222], bevel: 0.012, mat: 'steel', accent: FRAME },
      { size: [0.045, 0.36, 0.44], at: [-0.4825, 0, 0.005], bevel: 0.010, mat: 'panel', accent: FRAME }, // end panel
      { size: [0.045, 0.36, 0.44], at: [0.4825, 0, 0.005], bevel: 0.010, mat: 'panel', accent: FRAME },
      { size: [0.96, 0.36, 0.03], at: [0, 0, -0.235], mat: 'panel' }, // back panel
      { size: [0.88, 0.038, 0.022], at: [0, -0.126, 0.235], bevel: 0.008, mat: 'paint', accent: ACCENT }, // price rail
      { size: [0.20, 0.022, 0.010], at: [-0.26, -0.126, 0.244], bevel: 0.003, mat: 'paper', accent: GLASS },
      { size: [0.20, 0.022, 0.010], at: [0.22, -0.126, 0.244], bevel: 0.003, mat: 'paper', accent: GLASS },
      ...studs({ at: [-0.4825, 0, 0.222], spread: [0, 0.15], size: 0.018 }),
      ...studs({ at: [0.4825, 0, 0.222], spread: [0, 0.15], size: 0.018 }),
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
    // docs/concept/wall_shelving.png. The sheet's identity is a TEAL PRICE RAIL
    // with cream label windows punched along it, running the full front edge of
    // an oak board. That rail is the only saturated thing on the object and it
    // reads from across the room, which is exactly what shop signage is for.
    colors: {
      base: PALETTE.oak, // shelf board
      middle: PALETTE.oakDark,
      accent1: PALETTE.steel, // FRAME  — wall rail and brackets
      accent2: PALETTE.teal, // ACCENT — the price rail
      accent3: PALETTE.walnut, // DARK   — the board's shadow edge
      accent4: PALETTE.paper, // label windows
    },
    axes: {
      x: { mode: 'repeat', unit: 1.0, min: 1, max: 8, default: 3, label: 'bays' },
      y: { mode: 'repeat', unit: 0.38, min: 1, max: 5, default: 3, label: 'shelves' },
      z: FIXED,
    },
    build: () => [
      { size: [0.98, 0.034, 0.28], at: [0, -0.175, 0.01], bevel: 0.008, mat: 'wood' }, // shelf board
      { size: [0.98, 0.014, 0.26], at: [0, -0.196, 0.01], bevel: 0.004, mat: 'wood', accent: DARK }, // its shadow edge
      { size: [0.98, 0.38, 0.026], at: [0, 0, -0.137], bevel: 0.006, mat: 'steel', accent: FRAME }, // wall rail
      { size: [0.034, 0.14, 0.22], at: [-0.42, -0.118, 0.01], bevel: 0.006, mat: 'steel', accent: FRAME }, // bracket
      { size: [0.034, 0.14, 0.22], at: [0.42, -0.118, 0.01], bevel: 0.006, mat: 'steel', accent: FRAME },
      { size: [0.96, 0.050, 0.026], at: [0, -0.166, 0.152], bevel: 0.006, mat: 'paint', accent: ACCENT }, // price rail
      ...[-0.32, 0, 0.32].map((x) => ({
        size: [0.19, 0.026, 0.012], at: [x, -0.166, 0.163], bevel: 0.003, mat: 'paper', accent: GLASS,
      })), // label windows
      ...studs({ at: [-0.42, -0.118, 0.122], spread: [0, 0.05], size: 0.016 }),
      ...studs({ at: [0.42, -0.118, 0.122], spread: [0, 0.05], size: 0.016 }),
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
    // docs/concept/serving_counter.png changed this object's mind about its own
    // colour. It had been the teal one; the sheet made it CREAM with a warm oak
    // top banded in dark oak, and that is much better — the counter is the
    // thing a customer stands at, so it should be the calm object and let the
    // dispensing bench behind it carry the colour.
    //
    // Every fitting sits inside the 9-slice CAPS (|x| > 0.46), which is the
    // whole discipline of a stretch axis: ornament in the middle band would
    // smear as the counter grows, and ornament in the caps never moves.
    colors: {
      base: PALETTE.paper, // carcass
      middle: PALETTE.bone,
      accent1: PALETTE.oak, // FRAME  — worktop, customer shelf, pull rail
      accent2: PALETTE.signal, // ACCENT — the label plate and its buttons
      accent3: PALETTE.walnut, // DARK   — the dark oak band under both tops
      accent4: PALETTE.tealDeep, // no glass on this one: slot 4 buys the plinth
    },
    axes: {
      x: { mode: 'stretch', min: 1.0, max: 4.0, default: 1.8, label: 'length' },
      y: FIXED,
      z: { mode: 'stretch', min: 0.8, max: 1.6, default: 1.0, label: 'depth' },
    },
    build: () => [
      { size: [1.02, 0.10, 0.50], at: [0, -0.425, 0.0], bevel: 0.02, accent: GLASS }, // plinth
      { size: [1.2, 0.72, 0.60], at: [0, -0.015, 0.02], bevel: 0.05, mat: 'panel' }, // carcass
      { size: [1.16, 0.17, 0.63], at: [0, 0.11, 0.02], bevel: 0.022, mat: 'detail' }, // drawer band
      { size: [1.18, 0.016, 0.635], at: [0, 0.020, 0.02], bevel: 0.005, mat: 'paint', accent: DARK }, // band shadow
      { size: [1.0, 0.034, 0.05], at: [0, 0.11, 0.345], bevel: 0.014, mat: 'steel', accent: FRAME }, // pull rail
      // the oak top and the customer shelf are genuinely timber here
      ...worktop({ at: [0, 0.4375, 0.0], w: 1.26, d: 0.70, thickness: 0.075, lip: 0.034, mat: 'wood' }),
      { size: [1.1, 0.045, 0.16], at: [0, 0.32, 0.40], bevel: 0.018, mat: 'wood', accent: FRAME }, // customer shelf
      { size: [1.1, 0.020, 0.17], at: [0, 0.297, 0.40], bevel: 0.006, mat: 'wood', accent: DARK }, // its edge band
      ...plate({ at: [-0.52, 0.24, 0.345], w: 0.16, h: 0.05, accent: ACCENT, surround: FRAME }),
      ...studs({ at: [-0.545, -0.10, 0.325], spread: [0, 0.22], size: 0.020 }),
      ...studs({ at: [0.545, -0.10, 0.325], spread: [0, 0.22], size: 0.020 }),
      ...vents({ at: [0.545, -0.30, 0.325], n: 3, w: 0.14, thickness: 0.016, gap: 0.030, depth: 0.012 }),
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
    unit: [0.24, 0.20, 0.18],
    margins: [0, 0, 0],
    trimAxis: AXIS.x,
    trimDensity: 1.4,
    atlasCell: [0, 1],
    // docs/concept/till_block.png is the most characterful thing in the set: a
    // fat retro CRT in a steel shell with a warm oak bezel around a pale green
    // screen, sitting on a cream base with a real keypad and a receipt slot.
    // It was four boxes and it is now a machine, and the module grew a third
    // taller to make room for it — a POS terminal that reads as a toy till is
    // worth more than one that fits in the old bounding box.
    colors: {
      base: PALETTE.paper, // base body and keys
      middle: PALETTE.bone,
      accent1: PALETTE.steel, // FRAME  — monitor shell, reader shell
      accent2: PALETTE.oak, // ACCENT — the bezel and the receipt slot
      accent3: PALETTE.steelDark, // DARK   — stalk, vents, shadow lines
      accent4: PALETTE.glass, // GLASS  — the screen and the reader display
    },
    axes: { x: FIXED, y: FIXED, z: FIXED },
    build: () => [
      { size: [0.46, 0.10, 0.34], at: [0, -0.15, 0], bevel: 0.016, mat: 'panel' }, // base
      { size: [0.44, 0.020, 0.32], at: [0, -0.092, 0], bevel: 0.005, mat: 'paint', accent: FRAME }, // base top plate
      // the keypad, as four rows of keys rather than twenty separate ones
      ...[0, 1, 2, 3].map((i) => ({
        size: [0.17, 0.022, 0.032], at: [0.06, -0.078, 0.10 - i * 0.042], bevel: 0.005, mat: 'detail',
      })),
      { size: [0.20, 0.026, 0.055], at: [0, -0.196, 0.175], bevel: 0.006, mat: 'paint', accent: ACCENT }, // receipt slot
      ...vents({ at: [-0.16, -0.150, 0.172], n: 3, w: 0.11, thickness: 0.014, gap: 0.026, depth: 0.010 }),
      // The CRT. The screen gets the 'screen' strip — a near-black field with a
      // hard diagonal reflection staircase across it, which is exactly what a
      // display is in docs/reference/03-retro-computers. It had been sampling
      // the generic surface strip, so the monitor was showing mottled rock.
      { size: [0.07, 0.06, 0.07], at: [-0.06, -0.062, -0.055], bevel: 0.010, mat: 'steel', accent: DARK }, // neck
      { size: [0.34, 0.30, 0.20], at: [-0.06, 0.075, -0.055], bevel: 0.020, rotX: -0.12, mat: 'panel', accent: FRAME }, // shell
      { size: [0.29, 0.25, 0.03], at: [-0.06, 0.079, 0.048], bevel: 0.010, rotX: -0.12, mat: 'paint', accent: ACCENT }, // bezel
      { size: [0.235, 0.195, 0.02], at: [-0.06, 0.079, 0.060], bevel: 0.005, rotX: -0.12, mat: 'screen', accent: GLASS }, // screen
      ...vents({ at: [-0.06, 0.205, -0.15], n: 3, w: 0.20, thickness: 0.016, gap: 0.028, depth: 0.012 }),
      // the card reader, on its own stalk beside the till
      { size: [0.05, 0.09, 0.05], at: [0.185, -0.055, -0.02], bevel: 0.008, mat: 'steel', accent: ACCENT }, // stalk
      { size: [0.14, 0.055, 0.17], at: [0.185, 0.020, -0.02], bevel: 0.012, mat: 'paint', accent: DARK }, // body
      { size: [0.13, 0.030, 0.15], at: [0.185, 0.052, -0.01], bevel: 0.008, mat: 'paint', accent: FRAME }, // face
      { size: [0.09, 0.014, 0.06], at: [0.185, 0.070, -0.045], bevel: 0.004, mat: 'screen', accent: GLASS }, // display
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
    // The one sheet the model argued with: asked for nesting baskets, it drew a
    // slatted crate. It stays a basket — that is what the module is for — but
    // the sheet's colour language was too good to waste, so the panels went
    // teal, every rim got a cream rail, and the corners got walnut posts. A
    // stack of them by the door now reads as a stack of *something*, which the
    // flat teal trays did not.
    colors: {
      base: PALETTE.teal, // basket panels
      middle: PALETTE.tealDeep,
      accent1: PALETTE.paper, // FRAME  — the rim rails
      accent2: PALETTE.signal, // ACCENT — the handle bar
      accent3: PALETTE.walnut, // DARK   — corner posts
      accent4: PALETTE.glass, // GLASS  — the label window
    },
    axes: {
      x: FIXED,
      y: { mode: 'repeat', unit: 0.13, min: 2, max: 9, default: 5, label: 'baskets' },
      z: FIXED,
    },
    build: () => [
      { size: [0.42, 0.020, 0.30], at: [0, -0.055, 0], bevel: 0.006, mat: 'paint' }, // base
      { size: [0.42, 0.10, 0.022], at: [0, 0.0, 0.145], bevel: 0.006, mat: 'panel' }, // side
      { size: [0.42, 0.10, 0.022], at: [0, 0.0, -0.145], bevel: 0.006, mat: 'panel' }, // side
      { size: [0.022, 0.10, 0.26], at: [0.20, 0.0, 0], bevel: 0.006, mat: 'panel' }, // end
      { size: [0.022, 0.10, 0.26], at: [-0.20, 0.0, 0], bevel: 0.006, mat: 'panel' }, // end
      { size: [0.44, 0.024, 0.030], at: [0, 0.050, 0.148], bevel: 0.006, accent: FRAME }, // rim rail
      { size: [0.44, 0.024, 0.030], at: [0, 0.050, -0.148], bevel: 0.006, accent: FRAME },
      { size: [0.030, 0.024, 0.30], at: [0.204, 0.050, 0], bevel: 0.006, accent: FRAME },
      { size: [0.030, 0.024, 0.30], at: [-0.204, 0.050, 0], bevel: 0.006, accent: FRAME },
      { size: [0.034, 0.13, 0.034], at: [0.198, 0.0, 0.143], bevel: 0.008, mat: 'wood', accent: DARK }, // corner post
      { size: [0.034, 0.13, 0.034], at: [-0.198, 0.0, 0.143], bevel: 0.008, mat: 'wood', accent: DARK },
      { size: [0.034, 0.13, 0.034], at: [0.198, 0.0, -0.143], bevel: 0.008, mat: 'wood', accent: DARK },
      { size: [0.034, 0.13, 0.034], at: [-0.198, 0.0, -0.143], bevel: 0.008, mat: 'wood', accent: DARK },
      { size: [0.13, 0.040, 0.012], at: [0, -0.010, 0.156], bevel: 0.003, mat: 'paper', accent: GLASS }, // label
      { size: [0.26, 0.020, 0.020], at: [0, 0.062, 0], bevel: 0.005, mat: 'steel', accent: ACCENT }, // handle bar
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
    // docs/concept/promo_bin.png put the bin on a PALLET — real slats and real
    // feet, not a plinth — and that one substitution is what makes it read as
    // stock dumped on the shop floor this morning rather than as fitted
    // furniture. The thick deep-teal rim around the top is the other half: it
    // caps the open box so the eye stops at the rim instead of falling in.
    colors: {
      base: PALETTE.oak, // bin body
      middle: PALETTE.oakDark,
      accent1: PALETTE.paper, // FRAME  — pallet slats, header card
      accent2: PALETTE.tealDeep, // ACCENT — the rim and the header frame
      accent3: PALETTE.walnut, // DARK   — posts, pallet feet, seams
      accent4: PALETTE.glass, // GLASS  — the header's lettering band
    },
    axes: {
      x: { mode: 'repeat', unit: 0.66, min: 1, max: 4, default: 1, label: 'bins' },
      y: FIXED,
      z: FIXED,
    },
    build: () => [
      // the pallet
      ...[-0.19, 0, 0.19].map((z) => ({
        size: [0.64, 0.030, 0.11], at: [0, -0.520, z], bevel: 0.006, mat: 'wood', accent: FRAME,
      })),
      ...[-0.26, 0, 0.26].map((x) => ({
        size: [0.075, 0.055, 0.46], at: [x, -0.522, 0], bevel: 0.008, mat: 'wood', accent: DARK,
      })),
      { size: [0.62, 0.40, 0.50], at: [0, -0.285, 0], bevel: 0.018, mat: 'panel' }, // bin body
      { size: [0.60, 0.018, 0.48], at: [0, -0.170, 0], bevel: 0.005, mat: 'paint', accent: DARK }, // panel seam
      { size: [0.018, 0.36, 0.49], at: [0.06, -0.285, 0], bevel: 0.004, mat: 'paint', accent: DARK }, // panel seam
      { size: [0.68, 0.070, 0.56], at: [0, -0.055, 0], bevel: 0.012, mat: 'paint', accent: ACCENT }, // rim
      { size: [0.60, 0.040, 0.48], at: [0, -0.040, 0], bevel: 0.008, mat: 'paint', accent: DARK }, // the hole in it
      ...vents({ at: [0.22, -0.330, 0.253], n: 3, w: 0.13, thickness: 0.016, gap: 0.030, depth: 0.012 }),
      ...plate({ at: [-0.20, -0.230, 0.252], w: 0.15, h: 0.05, surround: FRAME }),
      { size: [0.045, 0.46, 0.045], at: [-0.24, 0.180, -0.20], bevel: 0.008, mat: 'wood', accent: DARK }, // post
      { size: [0.045, 0.46, 0.045], at: [0.24, 0.180, -0.20], bevel: 0.008, mat: 'wood', accent: DARK },
      { size: [0.66, 0.26, 0.026], at: [0, 0.420, -0.20], bevel: 0.008, mat: 'paint', accent: ACCENT }, // header frame
      { size: [0.60, 0.20, 0.020], at: [0, 0.420, -0.188], bevel: 0.006, mat: 'paper', accent: FRAME }, // header card
      { size: [0.46, 0.060, 0.012], at: [0, 0.440, -0.176], bevel: 0.004, mat: 'detail', accent: GLASS },
      ...studs({ at: [0, 0.420, -0.176], spread: [0.30, 0.11], size: 0.018 }),
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
    // docs/concept/queue_barrier.png took the least interesting object in the
    // catalogue — two posts and a rail — and gave it more character than most
    // of the furniture: cream posts with teal panels let into them, oak caps
    // and oak base plinths, an oak top rail with a slim steel one slung below
    // it. Two rails rather than one is most of it; a single rail reads as a
    // barrier prop and two read as a thing that was manufactured.
    colors: {
      base: PALETTE.paper, // posts
      middle: PALETTE.bone,
      accent1: PALETTE.oak, // FRAME  — caps, base plinths, top rail
      accent2: PALETTE.tealDeep, // ACCENT — the inset panels
      accent3: PALETTE.steelDark, // DARK   — the lower rail and the studs
      accent4: PALETTE.glass, // GLASS  — the notice plate
    },
    axes: {
      x: { mode: 'repeat', unit: 1.0, min: 1, max: 6, default: 2, label: 'spans' },
      y: FIXED,
      z: FIXED,
    },
    build: () => [
      { size: [0.11, 0.94, 0.11], at: [-0.46, -0.015, 0], bevel: 0.016, mat: 'panel' }, // post
      { size: [0.11, 0.94, 0.11], at: [0.46, -0.015, 0], bevel: 0.016, mat: 'panel' },
      { size: [0.06, 0.56, 0.026], at: [-0.46, -0.055, 0.058], bevel: 0.006, mat: 'paint', accent: ACCENT }, // inset panel
      { size: [0.06, 0.56, 0.026], at: [0.46, -0.055, 0.058], bevel: 0.006, mat: 'paint', accent: ACCENT },
      { size: [0.15, 0.055, 0.15], at: [-0.46, 0.478, 0], bevel: 0.010, mat: 'wood', accent: FRAME }, // cap
      { size: [0.15, 0.055, 0.15], at: [0.46, 0.478, 0], bevel: 0.010, mat: 'wood', accent: FRAME },
      { size: [0.19, 0.055, 0.19], at: [-0.46, -0.472, 0], bevel: 0.010, mat: 'wood', accent: FRAME }, // base plinth
      { size: [0.19, 0.055, 0.19], at: [0.46, -0.472, 0], bevel: 0.010, mat: 'wood', accent: FRAME },
      { size: [0.96, 0.085, 0.075], at: [0, 0.345, 0], bevel: 0.014, mat: 'wood', accent: FRAME }, // oak top rail
      { size: [0.90, 0.020, 0.030], at: [0, 0.315, 0.040], bevel: 0.005, mat: 'detail', accent: DARK },
      { size: [0.94, 0.040, 0.040], at: [0, 0.085, 0], bevel: 0.010, mat: 'steel', accent: DARK }, // steel lower rail
      { size: [0.055, 0.055, 0.055], at: [-0.42, 0.085, 0], bevel: 0.008, mat: 'steel', accent: FRAME }, // rail boss
      { size: [0.055, 0.055, 0.055], at: [0.42, 0.085, 0], bevel: 0.008, mat: 'steel', accent: FRAME },
      { size: [0.075, 0.11, 0.014], at: [-0.46, 0.300, 0.060], bevel: 0.003, mat: 'paper', accent: GLASS }, // notice
      ...studs({ at: [-0.46, 0.420, 0.058], spread: [0.028, 0.028], size: 0.016 }),
      ...studs({ at: [0.46, 0.420, 0.058], spread: [0.028, 0.028], size: 0.016 }),
      ...studs({ at: [-0.46, -0.415, 0.058], spread: [0.028, 0.028], size: 0.016 }),
      ...studs({ at: [0.46, -0.415, 0.058], spread: [0.028, 0.028], size: 0.016 }),
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
      // a dispensing carton is printed card, not a painted surface
      { size: [0.11, 0.18, 0.07], at: [0, 0, 0], bevel: 0.012, mat: 'paper' },
      { size: [0.075, 0.05, 0.006], at: [0, 0.02, 0.037], bevel: 0.002, mat: 'detail', accent: 1 },
    ],
    mounts: onSurface,
    provides: () => [],
  },
};
