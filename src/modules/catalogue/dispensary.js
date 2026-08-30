// Behind the counter. This is the working half of a pharmacy and it is where
// the domain detail lives: labelled racking, a fridge that has to hold 2–8 °C,
// a controlled-drugs cabinet that has to be steel and locked, and a bench with
// a sink because a lot of the job is measuring and washing up.
import { PALETTE } from '../../art/palette.js';
import { POOLS } from '../decor.js';
import { AXIS, FIXED, onFloor } from './schema.js';
import {
  ACCENT, DARK, FRAME, GLASS, NEUTRAL,
  capTray, keypad, plate, posts, vents, worktop,
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
      accent2: PALETTE.tealDeep, // ACCENT — the pulls, and only the pulls
      accent3: PALETTE.espresso, // DARK   — the plinth, the drawer reveal, shadow bands
      accent4: PALETTE.glass, // GLASS  — label windows
      accent5: PALETTE.steelDark, // NEUTRAL — the carcass sides, cool against the oak
    },
    axes: {
      x: { mode: 'repeat', unit: 0.9, min: 1, max: 6, default: 2, label: 'bays' },
      y: FIXED,
      z: { mode: 'stretch', min: 0.85, max: 1.4, default: 1.0, label: 'depth' },
    },
    // One bay. Local origin is the bay centre; the floor is at local -0.525.
    //
    // CHUNKIER, AND WITH LESS ON IT. Measured against docs/reference/, two
    // things were wrong. The proportions were realistic where the reference is
    // cartooned — its dumpsters and props have fat slabs, deep overhangs and
    // stubby legs, and a correctly-proportioned desk just reads as a desk. And
    // it carried ornament that does not survive the distance the game is played
    // at: sixteen 2 cm studs, two pull shadow bars and two drawer reveals, none
    // of which read at 3 m and all of which added noise to faces the reference
    // keeps flat.
    //
    // So: the worktop is half again as thick with a bigger oversail, the pulls
    // are fat enough to read as handles, the plinth and feet are heavier, and
    // the studs and shadow bars are gone. What stays is what says what this IS —
    // the frame, the two drawer depths, the pulls, the label holders, the
    // upstand. That is the test for every fitting now: does it name the object?
    build: () => [
      // The sheet's plinth is dark walnut, not teal: on a warm object the plinth
      // is the shadow the whole thing stands in, and a saturated colour down
      // there competes with the pulls for the one accent the object gets.
      { size: [0.86, 0.10, 0.50], at: [0, -0.475, 0], bevel: 0.02, mat: 'paint', accent: DARK }, // recessed kick
      // The sheet's carcass sides are a COOL grey against the oak drawer fronts.
      // Ours were warm on warm, so the drawers never separated from the box.
      { size: [0.90, 0.775, 0.62], at: [0, -0.0475, 0], bevel: 0.04, mat: 'panel', accent: NEUTRAL }, // carcass
      // the frame: four posts standing proud of the panels between them
      ...posts({ at: [0, -0.0475, 0.005], w: 0.90, h: 0.775, d: 0.64, thickness: 0.07 }),
      { size: [0.76, 0.060, 0.632], at: [0, -0.395, 0.006], bevel: 0.014, mat: 'paint', accent: FRAME }, // bottom rail
      // Between two drawers of ONE carcass there is no rail — there is a gap you
      // can see darkness through. A cream bar there read as a random white
      // stripe because that is what it was. It is now a recessed dark reveal.
      { size: [0.74, 0.030, 0.600], at: [0, -0.0325, -0.004], bevel: 0.008, mat: 'paint', accent: DARK }, // drawer gap
      { size: [0.76, 0.060, 0.632], at: [0, 0.268, 0.006], bevel: 0.014, mat: 'paint', accent: FRAME }, // top rail
      // the drawer fronts are the only wood on the object, so they get the grain
      { size: [0.74, 0.290, 0.626], at: [0, -0.222, 0.008], bevel: 0.018, mat: 'wood' }, // deep drawer
      { size: [0.74, 0.215, 0.626], at: [0, 0.1275, 0.008], bevel: 0.018, mat: 'wood' }, // shallow drawer
      // fat pulls, standing well proud — a handle you could actually grab
      { size: [0.38, 0.050, 0.075], at: [0, -0.222, 0.352], bevel: 0.016, mat: 'steel', accent: ACCENT },
      { size: [0.38, 0.050, 0.075], at: [0, 0.1275, 0.352], bevel: 0.016, mat: 'steel', accent: ACCENT },
      // Label holders: a dark recess routed into the drawer front with a paper
      // card in it. The default pale surround made a white blob on the wood.
      ...plate({ at: [-0.255, -0.315, 0.330], w: 0.17, h: 0.052, surround: DARK }), // label holder
      ...plate({ at: [-0.255, 0.035, 0.330], w: 0.17, h: 0.052, surround: DARK }),
      // The worktop, banded underneath: the band separates the top plane from
      // the carcass front by value, exactly where a drawn outline used to. A
      // dispensing bench top is wipe-clean laminate, not timber, so 'paint'.
      ...worktop({ at: [0, 0.3925, 0.02], w: 0.96, d: 0.740, thickness: 0.085, lip: 0.034, mat: 'paint' }),
      { size: [0.96, 0.115, 0.032], at: [0, 0.475, -0.354], bevel: 0.016, mat: 'paint', accent: FRAME }, // rear upstand
      { size: [0.11, 0.055, 0.11], at: [-0.345, -0.5375, 0.19], bevel: 0.014, mat: 'steel', accent: DARK }, // foot
      { size: [0.11, 0.055, 0.11], at: [0.345, -0.5375, 0.19], bevel: 0.014, mat: 'steel', accent: DARK },
      { size: [0.11, 0.055, 0.11], at: [-0.345, -0.5375, -0.19], bevel: 0.014, mat: 'steel', accent: DARK },
      { size: [0.11, 0.055, 0.11], at: [0.345, -0.5375, -0.19], bevel: 0.014, mat: 'steel', accent: DARK },
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
      { size: [0.78, 0.048, 0.30], at: [0, -0.136, 0.005], bevel: 0.010, mat: 'wood' }, // shelf board, oak like the sheet
      // The sheet draws a CARCASS — solid oak gables full depth, with the
      // shelves living inside it. Ours were two thin cream posts, so the object
      // read as an open cage with boards floating in it and threw no interior
      // shadow at all. Same timber as the shelves, because it is one piece of
      // joinery, not a frame with panels in it.
      { size: [0.060, 0.32, 0.32], at: [-0.380, 0, 0.005], bevel: 0.010, mat: 'wood' }, // gable
      { size: [0.060, 0.32, 0.32], at: [0.380, 0, 0.005], bevel: 0.010, mat: 'wood' }, // gable
      { size: [0.78, 0.32, 0.018], at: [0, 0, -0.151], bevel: 0.006, mat: 'panel' }, // back panel
      { size: [0.74, 0.030, 0.018], at: [0, -0.126, 0.150], bevel: 0.005, mat: 'paint', accent: FRAME }, // label strip
      { size: [0.70, 0.018, 0.010], at: [0, -0.126, 0.158], bevel: 0.003, mat: 'paper', accent: GLASS }, // its window
      { size: [0.76, 0.016, 0.020], at: [0, -0.152, 0.148], bevel: 0.005, mat: 'paint', accent: ACCENT }, // shelf front lip
      { size: [0.018, 0.28, 0.26], at: [-0.13, 0.015, -0.02], bevel: 0.004, mat: 'wood', accent: DARK }, // bay divider
      { size: [0.018, 0.28, 0.26], at: [0.17, 0.015, -0.02], bevel: 0.004, mat: 'wood', accent: DARK }, // bay divider
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
      base: PALETTE.charcoal, // door and side panels — near-black on the sheet
      middle: PALETTE.charcoal,
      accent1: PALETTE.paper, // FRAME  — posts, cap, plinth: the sheet's cage is pale, and that contrast is the object
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
      { size: [0.70, 0.94, 0.46], at: [0, 0.020, 0], bevel: 0.018, mat: 'panel' }, // carcass
      ...posts({ at: [0, 0.020, 0], w: 0.70, h: 0.95, d: 0.47, thickness: 0.05, bevel: 0.012 }),
      ...capTray({ at: [0, 0.520, 0], w: 0.72, d: 0.48, rim: 0.05 }),
      { size: [0.60, 0.86, 0.035], at: [0.015, 0.020, 0.242], bevel: 0.010, mat: 'panel' }, // door
      { size: [0.62, 0.020, 0.045], at: [0.015, 0.462, 0.245], bevel: 0.005, accent: DARK }, // door head reveal
      { size: [0.62, 0.020, 0.045], at: [0.015, -0.422, 0.245], bevel: 0.005, accent: DARK }, // door foot reveal
      // three heavy barrel hinges: the legal giveaway that this is a CD cabinet
      ...[0.360, 0.020, -0.320].flatMap((y) => [
        { size: [0.055, 0.105, 0.060], at: [-0.318, y, 0.248], bevel: 0.010, mat: 'steel', accent: DARK },
        { size: [0.070, 0.045, 0.030], at: [-0.318, y, 0.262], bevel: 0.006, mat: 'steel', accent: FRAME },
      ]),
      { size: [0.032, 0.26, 0.050], at: [0.262, -0.075, 0.270], bevel: 0.008, mat: 'steel', accent: DARK }, // handle
      { size: [0.048, 0.045, 0.030], at: [0.262, 0.048, 0.258], bevel: 0.006, mat: 'steel', accent: FRAME }, // handle bracket
      { size: [0.048, 0.045, 0.030], at: [0.262, -0.198, 0.258], bevel: 0.006, mat: 'steel', accent: FRAME },
      // The sheet's keypad is four big coral squares in a 2x2 you can count from
      // across the room. Ours was a 10 cm plate of 1.6 cm bands — invisible.
      ...keypad({ at: [0.205, 0.200, 0.268], w: 0.155, h: 0.185, depth: 0.032 }),
      ...plate({ at: [0.190, 0.395, 0.264], w: 0.19, h: 0.075 }), // warning plate
      ...vents({ at: [-0.352, -0.300, 0.06], n: 5, w: 0.18, thickness: 0.016, gap: 0.028, depth: 0.012, axis: 'x' }),
      { size: [0.024, 0.020, 0.40], at: [-0.352, 0.020, 0], bevel: 0.005, mat: 'steel', accent: DARK }, // side seam
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
    // Nothing in a vaccine fridge is made of wood. The first pass gave this one
    // oak sides and an oak condenser grille because the concept model has a
    // warm-tone bias and drew them tan — but a wood-clad cold cabinet is a
    // detail with no reason behind it, and it was the loudest wrong thing on
    // the object. A vaccine fridge is a painted steel box: pale steel body,
    // darker steel where it is in shadow, a glass door in a steel surround, a
    // dark stamped grille at the foot where the condenser breathes. The one
    // warm note it is allowed is the teal door handle, which is a colour choice
    // a manufacturer actually makes.
    colors: {
      base: PALETTE.steel, // painted steel body
      middle: PALETTE.steelDark,
      accent1: PALETTE.steel, // FRAME  — posts, door surround, top cap
      accent2: PALETTE.tealDeep, // ACCENT — the door handle
      accent3: PALETTE.charcoal, // DARK   — fittings, readout body, plinth, grille
      accent4: PALETTE.mint, // GLASS  — the door: a lit cabinet you see stock through, not a grey mirror
    },
    axes: {
      x: { mode: 'repeat', unit: 0.8, min: 1, max: 4, default: 1, label: 'sections' },
      y: FIXED,
      z: FIXED,
    },
    build: () => [
      { size: [0.72, 0.06, 0.52], at: [0, -0.820, -0.02], bevel: 0.010, accent: DARK }, // plinth
      { size: [0.78, 1.64, 0.60], at: [0, 0.010, -0.02], bevel: 0.03, mat: 'panel' }, // carcass
      ...posts({ at: [0, 0.010, -0.02], w: 0.78, h: 1.66, d: 0.61, thickness: 0.06, bevel: 0.014 }),
      // A plain steel cap. The teal band and the lipped tray that used to sit
      // here were decoration: a fridge does not carry a tray on its head, and
      // nothing about the top of a cold cabinet is a different colour.
      { size: [0.82, 0.055, 0.63], at: [0, 0.860, -0.02], bevel: 0.012, mat: 'paint', accent: FRAME }, // top cap
      // the door: glass set into a pale surround, not floating in the carcass
      { size: [0.68, 1.30, 0.055], at: [0, 0.075, 0.290], bevel: 0.012, mat: 'paint', accent: FRAME },
      { size: [0.56, 1.18, 0.030], at: [0, 0.075, 0.312], bevel: 0.008, mat: 'glass', accent: GLASS },
      { size: [0.68, 0.045, 0.075], at: [0, 0.700, 0.292], bevel: 0.008, accent: DARK }, // head rail
      { size: [0.68, 0.045, 0.075], at: [0, -0.550, 0.292], bevel: 0.008, accent: DARK }, // foot rail
      { size: [0.034, 0.86, 0.050], at: [0.300, 0.075, 0.322], bevel: 0.008, mat: 'steel', accent: ACCENT }, // handle
      { size: [0.052, 0.042, 0.032], at: [0.300, 0.470, 0.308], bevel: 0.006, mat: 'steel', accent: FRAME }, // handle bracket
      { size: [0.052, 0.042, 0.032], at: [0.300, -0.320, 0.308], bevel: 0.006, mat: 'steel', accent: FRAME },
      // a temperature readout is a lit display, not a printed label
      // The sheet puts the readout HIGH on the door head, at eye level, which is
      // where you would read it. Ours sat low on the surround where the door
      // furniture is.
      ...plate({ at: [-0.150, 0.700, 0.335], w: 0.24, h: 0.095, surround: DARK, mat: 'screen' }),
      // The condenser grille is stamped steel in shadow behind its own louvres,
      // so it is the darkest thing on the object, not the warmest.
      // On the sheet the grille is a bold black louvred band across the WHOLE
      // foot of the cabinet — it is the second-strongest mark on the object
      // after the door. Ours was a modest inset panel two-thirds the width.
      { size: [0.80, 0.22, 0.115], at: [0, -0.700, 0.285], bevel: 0.012, mat: 'grille', accent: DARK }, // condenser grille
      ...vents({ at: [0, -0.700, 0.348], n: 5, w: 0.72, thickness: 0.024, gap: 0.042, depth: 0.016 }),
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
      // The sheet puts TEAL cupboard doors under a pale steel top. Ours had grey
      // doors under a grey top, so the whole unit read as one undifferentiated
      // slab and the sink — the thing it is named for — disappeared into it.
      base: PALETTE.teal, // door panels
      middle: PALETTE.tealDeep,
      accent1: PALETTE.steel, // FRAME  — posts, worktop, rails
      accent2: PALETTE.signal, // ACCENT — the one warm mark on a cold object
      accent3: PALETTE.ink, // DARK   — basin well, vents, handles
      accent4: PALETTE.glass, // GLASS  — label windows
      accent5: PALETTE.steel, // NEUTRAL — the pressed well: a recess, not a void
    },
    axes: {
      x: { mode: 'repeat', unit: 0.7, min: 1, max: 4, default: 1, label: 'bays' },
      y: FIXED,
      z: { mode: 'stretch', min: 0.85, max: 1.3, default: 1.0, label: 'depth' },
    },
    build: () => [
      { size: [0.66, 0.085, 0.48], at: [0, -0.4325, 0], bevel: 0.012, accent: DARK }, // kick
      { size: [0.70, 0.79, 0.58], at: [0, 0.005, 0], bevel: 0.022, mat: 'panel' }, // carcass
      ...posts({ at: [0, 0.005, 0], w: 0.70, h: 0.80, d: 0.59, thickness: 0.05, bevel: 0.012 }),
      { size: [0.31, 0.62, 0.030], at: [-0.175, -0.030, 0.296], bevel: 0.010, mat: 'panel' }, // door
      { size: [0.31, 0.62, 0.030], at: [0.175, -0.030, 0.296], bevel: 0.010, mat: 'panel' }, // door
      { size: [0.022, 0.66, 0.034], at: [0, -0.030, 0.294], bevel: 0.005, mat: 'steel', accent: FRAME }, // meeting stile
      { size: [0.042, 0.042, 0.040], at: [-0.042, -0.030, 0.316], bevel: 0.008, mat: 'steel', accent: DARK }, // knob
      { size: [0.042, 0.042, 0.040], at: [0.042, -0.030, 0.316], bevel: 0.008, mat: 'steel', accent: DARK }, // knob
      ...vents({ at: [-0.352, -0.120, 0.10], n: 5, w: 0.22, thickness: 0.016, gap: 0.030, depth: 0.012, axis: 'x' }),
      ...plate({ at: [0.215, 0.310, 0.298], w: 0.14, h: 0.048 }),
      // a dispensary sink is a single pressed stainless top, so every part of
      // it from the worktop to the spout is the same 'steel'
      { size: [0.74, 0.055, 0.62], at: [0, 0.4475, 0], bevel: 0.014, mat: 'steel', accent: FRAME }, // worktop, top at 0.95
      { size: [0.44, 0.036, 0.36], at: [-0.02, 0.470, 0.03], bevel: 0.008, mat: 'steel', accent: FRAME }, // basin rim
      // The well is a pressed steel recess, not a hole into the object. It was
      // 'ink' — a purple-black — which read as a void punched in the worktop.
      { size: [0.36, 0.026, 0.28], at: [-0.02, 0.478, 0.03], bevel: 0.005, mat: 'steel', accent: NEUTRAL }, // the well
      { size: [0.30, 0.016, 0.22], at: [-0.02, 0.468, 0.03], bevel: 0.004, mat: 'steel', accent: NEUTRAL },
      // The tap is what says SINK from across the room, and ours was a stub.
      // The sheet draws a tall gooseneck: a column up, a long arm out over the
      // middle of the basin, and a short drop at the end of it.
      { size: [0.060, 0.40, 0.060], at: [-0.02, 0.672, -0.215], bevel: 0.012, mat: 'steel', accent: FRAME }, // mixer column
      { size: [0.052, 0.052, 0.30], at: [-0.02, 0.860, -0.090], bevel: 0.010, mat: 'steel', accent: FRAME }, // gooseneck arm
      { size: [0.046, 0.075, 0.046], at: [-0.02, 0.815, 0.045], bevel: 0.008, mat: 'steel', accent: FRAME }, // its drop
      { size: [0.15, 0.030, 0.032], at: [0.145, 0.800, -0.215], bevel: 0.006, mat: 'steel', accent: DARK }, // lever
      { size: [0.030, 0.030, 0.030], at: [0.075, 0.800, -0.215], bevel: 0.006, mat: 'paint', accent: ACCENT }, // lever boss
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
      accent3: PALETTE.charcoal, // DARK   — grille, pedal, linkage
      accent4: PALETTE.glass, // GLASS  — the sharps label
    },
    axes: { x: FIXED, y: FIXED, z: FIXED },
    build: () => [
      { size: [0.44, 0.58, 0.42], at: [0, -0.10, 0], bevel: 0.016, mat: 'panel' }, // body
      { size: [0.455, 0.13, 0.435], at: [0, 0.055, 0], bevel: 0.010, accent: FRAME }, // the belt
      { size: [0.46, 0.020, 0.44], at: [0, -0.015, 0], bevel: 0.005, accent: DARK }, // belt shadow
      { size: [0.48, 0.075, 0.46], at: [0, 0.242, 0], bevel: 0.012, mat: 'paint' }, // lid slab
      { size: [0.42, 0.030, 0.40], at: [0, 0.290, 0], bevel: 0.008, accent: FRAME }, // lid rim
      { size: [0.24, 0.026, 0.16], at: [0, 0.312, 0.02], bevel: 0.005, accent: DARK }, // flap
      { size: [0.26, 0.20, 0.020], at: [-0.04, 0.055, 0.215], bevel: 0.006, accent: DARK }, // grille panel
      ...vents({ at: [-0.04, 0.055, 0.228], n: 5, w: 0.21, thickness: 0.018, gap: 0.036, depth: 0.010, accent: FRAME }),
      ...plate({ at: [0.135, -0.230, 0.214], w: 0.13, h: 0.10, accent: ACCENT, surround: FRAME }), // hazard plate
      { size: [0.20, 0.026, 0.11], at: [0, -0.372, 0.245], bevel: 0.006, accent: FRAME }, // pedal tray
      { size: [0.15, 0.030, 0.075], at: [0, -0.348, 0.250], bevel: 0.008, mat: 'steel', accent: DARK }, // pedal
      { size: [0.026, 0.60, 0.026], at: [-0.222, 0.030, -0.196], bevel: 0.006, mat: 'steel', accent: DARK }, // linkage rod
      { size: [0.045, 0.030, 0.045], at: [-0.222, 0.300, -0.196], bevel: 0.006, mat: 'steel', accent: DARK }, // linkage elbow
      // One clean cream box, centred. The sheet has a single sharps container
      // sitting square on the lid; ours was split into a box plus a dark capped
      // aperture offset to one side, which read as two half-objects.
      { size: [0.26, 0.20, 0.22], at: [0, 0.380, -0.02], bevel: 0.014, accent: FRAME }, // sharps box
      { size: [0.15, 0.024, 0.10], at: [0, 0.482, -0.02], bevel: 0.005, accent: DARK }, // sharps aperture
      { size: [0.15, 0.075, 0.010], at: [0, 0.375, 0.093], bevel: 0.003, mat: 'paper', accent: GLASS }, // its label
    ],
    mounts: onFloor,
    provides: () => [],
  },
};
