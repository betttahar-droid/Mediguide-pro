// Consultation, staff and signage — the rooms off the shop floor, and the
// things that go on a wall.
import { PALETTE } from '../../art/palette.js';
import { POOLS } from '../decor.js';
import { AXIS, FIXED, onFloor } from './schema.js';
import { ACCENT, DARK, FRAME, GLASS, capTray, plate, studs, vents } from './fittings.js';

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
    // docs/concept/consultation_booth.png made the frame WALNUT — heavy dark
    // timber posts and a proper door surround, with cream infill panels below
    // and full pale glazing above. That reads as a room you would actually go
    // into for a private conversation, where the all-cream version read as a
    // shower cubicle. A mint skirting band grounds it and the steel roof cap
    // carries vent grilles, because a sealed room needs air.
    //
    // Both plan axes stretch, so every fitting sits in the 9-slice caps
    // (|x| and |z| beyond 0.64) and none of it smears as the room is sized.
    colors: {
      base: PALETTE.paper, // infill panels
      middle: PALETTE.bone,
      accent1: PALETTE.walnut, // FRAME  — posts, door surround, glazing beads
      accent2: PALETTE.mint, // ACCENT — the skirting band
      accent3: PALETTE.charcoal, // DARK   — roof cap, hinges, vents
      accent4: PALETTE.glass, // GLASS  — glazing and the sign face
    },
    axes: {
      x: { mode: 'stretch', min: 0.85, max: 2.1, default: 1.0, label: 'width' },
      y: FIXED,
      z: { mode: 'stretch', min: 0.85, max: 2.1, default: 1.0, label: 'depth' },
    },
    build: () => [
      { size: [1.80, 2.20, 0.09], at: [0, -0.05, -0.855], bevel: 0.02, mat: 'panel' }, // back wall
      { size: [1.44, 0.76, 0.03], at: [0, 0.53, -0.800], bevel: 0.008, mat: 'glass', accent: GLASS }, // glazed panel
      { size: [1.52, 0.050, 0.050], at: [0, 0.140, -0.794], bevel: 0.008, mat: 'wood', accent: FRAME }, // glazing bead
      { size: [1.52, 0.045, 0.045], at: [0, 0.930, -0.794], bevel: 0.008, mat: 'wood', accent: FRAME },
      { size: [0.09, 2.20, 1.80], at: [-0.855, -0.05, 0], bevel: 0.02, mat: 'panel' }, // side wall
      { size: [0.03, 0.76, 1.44], at: [-0.800, 0.53, 0], bevel: 0.008, mat: 'glass', accent: GLASS }, // glazed panel
      { size: [0.050, 0.050, 1.52], at: [-0.794, 0.140, 0], bevel: 0.008, mat: 'wood', accent: FRAME }, // glazing bead
      { size: [0.045, 0.045, 1.52], at: [-0.794, 0.930, 0], bevel: 0.008, mat: 'wood', accent: FRAME },
      { size: [0.09, 2.20, 0.80], at: [0.855, -0.05, -0.50], bevel: 0.02, mat: 'panel' }, // door-side return
      // the heavy timber frame: corner posts and a real door surround
      { size: [0.15, 2.24, 0.15], at: [-0.855, -0.05, -0.855], bevel: 0.018, mat: 'wood', accent: FRAME },
      { size: [0.15, 2.24, 0.15], at: [0.855, -0.05, -0.855], bevel: 0.018, mat: 'wood', accent: FRAME },
      { size: [0.15, 2.24, 0.15], at: [-0.855, -0.05, 0.855], bevel: 0.018, mat: 'wood', accent: FRAME },
      { size: [0.16, 2.24, 0.16], at: [0.855, -0.05, 0.30], bevel: 0.018, mat: 'wood', accent: FRAME }, // door post
      { size: [0.12, 0.24, 1.10], at: [0.855, 0.945, 0.35], bevel: 0.014, mat: 'wood', accent: FRAME }, // door head
      { size: [0.14, 0.16, 0.16], at: [0.860, 0.500, 0.395], bevel: 0.012, mat: 'steel', accent: DARK }, // hinge
      { size: [0.14, 0.16, 0.16], at: [0.860, -0.500, 0.395], bevel: 0.012, mat: 'steel', accent: DARK },
      { size: [1.94, 0.10, 1.94], at: [0, 1.115, 0], bevel: 0.02, mat: 'panel', accent: DARK }, // roof cap
      ...vents({ at: [-0.30, 1.170, -0.62], n: 3, w: 0.44, thickness: 0.030, gap: 0.070, depth: 0.030, accent: FRAME }),
      { size: [1.86, 0.13, 0.13], at: [0, -1.085, -0.855], bevel: 0.014, mat: 'paint', accent: ACCENT }, // skirting
      { size: [0.13, 0.13, 1.86], at: [-0.855, -1.085, 0], bevel: 0.014, mat: 'paint', accent: ACCENT },
      { size: [0.13, 0.13, 0.86], at: [0.855, -1.085, -0.50], bevel: 0.014, mat: 'paint', accent: ACCENT },
      // the sign over the door, on brackets
      { size: [0.05, 0.34, 0.86], at: [0.900, 0.86, 0.35], bevel: 0.010, mat: 'wood', accent: FRAME },
      { size: [0.03, 0.26, 0.76], at: [0.922, 0.86, 0.35], bevel: 0.006, mat: 'paper', accent: GLASS },
      { size: [0.02, 0.10, 0.46], at: [0.936, 0.86, 0.35], bevel: 0.004, mat: 'detail', accent: FRAME },
      ...studs({ at: [0.860, -0.70, 0.855], spread: [0, 0.30], size: 0.026 }),
      ...studs({ at: [-0.860, -0.70, 0.700], spread: [0, 0.30], size: 0.026 }),
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
    // docs/concept/consult_chair.png: a steel machine with two fat tan cushions
    // dropped into it. The cushions are proud of the frame and piped all round,
    // the back one is held by a pair of visible brackets, and the seat pan
    // carries a vent strip and a small warm label. It is the one piece of
    // furniture in the catalogue a person actually touches, so it earns them.
    colors: {
      base: PALETTE.steel, // frame, pan and legs
      middle: PALETTE.steelDark,
      accent1: PALETTE.oak, // FRAME  — the cushions
      accent2: PALETTE.signal, // ACCENT — the maker's label
      accent3: PALETTE.charcoal, // DARK   — piping, brackets, vents
      accent4: PALETTE.espresso, // the cushions' shadow edge
    },
    axes: { x: FIXED, y: FIXED, z: FIXED },
    build: () => [
      { size: [0.44, 0.105, 0.42], at: [0, -0.005, 0.02], bevel: 0.018, mat: 'fabric', accent: FRAME }, // seat cushion
      { size: [0.44, 0.020, 0.42], at: [0, -0.060, 0.02], bevel: 0.006, mat: 'fabric', accent: GLASS }, // its shadow edge
      { size: [0.42, 0.42, 0.10], at: [0, 0.235, -0.170], bevel: 0.018, mat: 'fabric', accent: FRAME }, // back cushion
      { size: [0.42, 0.020, 0.10], at: [0, 0.020, -0.170], bevel: 0.006, mat: 'fabric', accent: GLASS },
      { size: [0.46, 0.040, 0.44], at: [0, -0.078, 0.02], bevel: 0.008, mat: 'steel' }, // seat pan
      { size: [0.055, 0.50, 0.055], at: [-0.195, 0.190, -0.215], bevel: 0.010, mat: 'steel' }, // back post
      { size: [0.055, 0.50, 0.055], at: [0.195, 0.190, -0.215], bevel: 0.010, mat: 'steel' },
      { size: [0.075, 0.055, 0.055], at: [-0.195, 0.330, -0.208], bevel: 0.008, mat: 'steel', accent: DARK }, // bracket
      { size: [0.075, 0.055, 0.055], at: [-0.195, 0.130, -0.208], bevel: 0.008, mat: 'steel', accent: DARK },
      { size: [0.048, 0.42, 0.048], at: [-0.19, -0.290, 0.17], bevel: 0.008, mat: 'steel' }, // leg
      { size: [0.048, 0.42, 0.048], at: [0.19, -0.290, 0.17], bevel: 0.008, mat: 'steel' },
      { size: [0.048, 0.42, 0.048], at: [-0.19, -0.290, -0.15], bevel: 0.008, mat: 'steel' },
      { size: [0.048, 0.42, 0.048], at: [0.19, -0.290, -0.15], bevel: 0.008, mat: 'steel' },
      { size: [0.42, 0.032, 0.032], at: [0, -0.400, 0.17], bevel: 0.006, mat: 'steel', accent: DARK }, // stretcher
      { size: [0.46, 0.022, 0.028], at: [0, 0.046, 0.226], bevel: 0.006, mat: 'paint', accent: DARK }, // seat piping
      { size: [0.44, 0.026, 0.028], at: [0, 0.442, -0.170], bevel: 0.006, mat: 'paint', accent: DARK }, // back piping
      ...vents({ at: [0, -0.078, 0.244], n: 3, w: 0.16, thickness: 0.012, gap: 0.020, depth: 0.012 }),
      ...plate({ at: [0.145, -0.078, 0.244], w: 0.10, h: 0.030, accent: ACCENT, surround: DARK }),
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
    // docs/concept/locker_bank.png is the frame rule at its cleanest: a CREAM
    // cage of stiles and rails with deep-green doors dropped into it, and a
    // cream sloped crown on top. The old version had it exactly backwards —
    // mint carcass, dark doors flush with it — and the difference between the
    // two is the whole finding from the concept set in one object.
    colors: {
      base: PALETTE.tealDeep, // the doors
      middle: PALETTE.teal,
      accent1: PALETTE.paper, // FRAME  — stiles, rails, crown
      accent2: PALETTE.steel, // ACCENT — handles and hinges
      accent3: PALETTE.charcoal, // DARK   — plinth, vents, side seams
      accent4: PALETTE.glass, // GLASS  — the number plates
    },
    axes: {
      x: { mode: 'repeat', unit: 0.6, min: 1, max: 8, default: 3, label: 'bays' },
      y: FIXED,
      z: FIXED,
    },
    build: () => [
      { size: [0.60, 1.72, 0.50], at: [0, 0.04, 0], bevel: 0.016, mat: 'paint', accent: FRAME }, // carcass / frame
      { size: [0.56, 0.075, 0.46], at: [0, -0.858, 0], bevel: 0.010, mat: 'paint', accent: DARK }, // plinth
      { size: [0.53, 0.79, 0.035], at: [0.005, 0.455, 0.256], bevel: 0.010, mat: 'panel' }, // upper door
      { size: [0.53, 0.79, 0.035], at: [0.005, -0.395, 0.256], bevel: 0.010, mat: 'panel' }, // lower door
      // the frame reading through: stiles down the sides, a rail between doors
      { size: [0.045, 1.68, 0.045], at: [-0.2775, 0.04, 0.262], bevel: 0.010, accent: FRAME },
      { size: [0.045, 1.68, 0.045], at: [0.2775, 0.04, 0.262], bevel: 0.010, accent: FRAME },
      { size: [0.60, 0.055, 0.045], at: [0, 0.030, 0.262], bevel: 0.010, accent: FRAME }, // mid rail
      { size: [0.60, 0.045, 0.045], at: [0, 0.878, 0.262], bevel: 0.010, accent: FRAME }, // head rail
      { size: [0.60, 0.045, 0.045], at: [0, -0.798, 0.262], bevel: 0.010, accent: FRAME }, // foot rail
      ...vents({ at: [0, 0.745, 0.276], n: 3, w: 0.26, thickness: 0.024, gap: 0.046, depth: 0.016 }),
      ...vents({ at: [0, -0.105, 0.276], n: 3, w: 0.26, thickness: 0.024, gap: 0.046, depth: 0.016 }),
      { size: [0.034, 0.17, 0.050], at: [0.228, 0.300, 0.280], bevel: 0.006, mat: 'steel', accent: ACCENT }, // handle
      { size: [0.034, 0.17, 0.050], at: [0.228, -0.550, 0.280], bevel: 0.006, mat: 'steel', accent: ACCENT },
      ...plate({ at: [-0.165, 0.560, 0.276], w: 0.10, h: 0.060, depth: 0.010 }), // number plate
      ...plate({ at: [-0.165, -0.290, 0.276], w: 0.10, h: 0.060, depth: 0.010 }),
      { size: [0.024, 0.020, 0.44], at: [-0.302, 0.04, 0], bevel: 0.005, mat: 'steel', accent: DARK }, // side seam
      { size: [0.62, 0.050, 0.52], at: [0, 0.905, 0], bevel: 0.012, accent: DARK }, // top cap
      { size: [0.60, 0.055, 0.48], at: [0, 0.950, 0.02], bevel: 0.012, accent: FRAME }, // sloped crown
      ...studs({ at: [0, 0.905, 0.258], spread: [0.26, 0], size: 0.020 }),
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
    // docs/concept/filing_cabinet.png gives every drawer a fat CREAM PULL BLOCK
    // standing proud of the front with a dark label slot cut into it — one
    // fitting doing two jobs, handle and label holder, and it is the only
    // reason a stack of four identical grey rectangles reads as a filing
    // cabinet at all. Cheap to build, and it changes the object completely.
    colors: {
      base: PALETTE.steelDark, // drawer fronts
      middle: PALETTE.charcoal,
      accent1: PALETTE.steel, // FRAME  — stiles, rails, top cap
      accent2: PALETTE.paper, // ACCENT — the pull blocks
      accent3: PALETTE.ink, // DARK   — plinth, vents, label slots
      accent4: PALETTE.glass, // GLASS  — the cap's face
    },
    axes: { x: FIXED, y: FIXED, z: FIXED },
    build: () => [
      { size: [0.48, 1.29, 0.62], at: [0, 0.005, 0], bevel: 0.014, mat: 'paint', accent: FRAME }, // carcass / frame
      { size: [0.46, 0.070, 0.60], at: [0, -0.630, 0], bevel: 0.008, mat: 'paint', accent: DARK }, // plinth
      ...capTray({ at: [0, 0.670, 0], w: 0.52, d: 0.66, rim: 0.045, thickness: 0.036, panel: GLASS }),
      { size: [0.042, 1.26, 0.045], at: [-0.221, 0.005, 0.315], bevel: 0.008, mat: 'steel', accent: FRAME }, // stile
      { size: [0.042, 1.26, 0.045], at: [0.221, 0.005, 0.315], bevel: 0.008, mat: 'steel', accent: FRAME },
      ...[-0.475, -0.165, 0.145, 0.455].flatMap((y) => [
        { size: [0.42, 0.280, 0.030], at: [0, y, 0.312], bevel: 0.008, mat: 'panel' },
        { size: [0.42, 0.016, 0.036], at: [0, y - 0.148, 0.314], bevel: 0.004, mat: 'paint', accent: DARK }, // reveal
        // the pull block: proud, cream, with a dark label slot cut into it
        { size: [0.20, 0.075, 0.055], at: [0, y + 0.010, 0.342], bevel: 0.010, mat: 'paint', accent: ACCENT },
        { size: [0.15, 0.030, 0.030], at: [0, y + 0.020, 0.362], bevel: 0.005, mat: 'paper', accent: DARK },
        { size: [0.20, 0.020, 0.030], at: [0, y - 0.030, 0.356], bevel: 0.004, mat: 'paint', accent: DARK }, // its shadow
      ]),
      ...vents({ at: [-0.245, 0.330, 0.10], n: 4, w: 0.20, thickness: 0.016, gap: 0.028, depth: 0.012, axis: 'x' }),
      ...vents({ at: [-0.245, -0.330, 0.10], n: 4, w: 0.20, thickness: 0.016, gap: 0.028, depth: 0.012, axis: 'x' }),
      ...studs({ at: [0, 0.670, 0.320], spread: [0.20, 0], size: 0.018 }),
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
    // docs/concept/green_cross.png builds the cross in three layers rather than
    // two: a steel RIM standing proud all the way round a deep-teal body, with
    // the lit face inset inside that. The rim is what makes it glow — a pale
    // edge catching the light around a dark body reads as an illuminated sign
    // even with no emissive term anywhere in the renderer.
    colors: {
      base: PALETTE.tealDeep, // the cross body
      middle: PALETTE.teal,
      accent1: PALETTE.steel, // FRAME  — the rim
      accent2: PALETTE.mint, // ACCENT — the lit face's inner glow
      accent3: PALETTE.charcoal, // DARK   — back plate, stalk, screws
      accent4: PALETTE.glass, // GLASS  — the lit face
    },
    axes: { x: FIXED, y: FIXED, z: FIXED },
    build: () => [
      { size: [0.78, 0.78, 0.045], at: [0, 0, -0.055], bevel: 0.010, mat: 'panel', accent: DARK }, // back plate
      { size: [0.30, 0.80, 0.10], at: [0, 0, -0.004], bevel: 0.014, mat: 'steel', accent: FRAME }, // rim
      { size: [0.80, 0.30, 0.10], at: [0, 0, -0.004], bevel: 0.014, mat: 'steel', accent: FRAME },
      { size: [0.26, 0.76, 0.098], at: [0, 0, 0.004], bevel: 0.012, mat: 'paint' }, // body
      { size: [0.76, 0.26, 0.098], at: [0, 0, 0.004], bevel: 0.012, mat: 'paint' },
      { size: [0.20, 0.66, 0.024], at: [0, 0, 0.046], bevel: 0.006, mat: 'paint', accent: ACCENT }, // glow surround
      { size: [0.66, 0.20, 0.024], at: [0, 0, 0.046], bevel: 0.006, mat: 'paint', accent: ACCENT },
      // the lit face is an illuminated panel, so it takes the glass strip
      { size: [0.15, 0.61, 0.016], at: [0, 0, 0.056], bevel: 0.004, mat: 'glass', accent: GLASS },
      { size: [0.61, 0.15, 0.016], at: [0, 0, 0.056], bevel: 0.004, mat: 'glass', accent: GLASS },
      { size: [0.08, 0.08, 0.16], at: [0, 0, -0.14], bevel: 0.010, mat: 'steel', accent: DARK }, // wall stalk
      ...studs({ at: [0, 0.325, 0.046], spread: [0.10, 0], size: 0.020 }),
      ...studs({ at: [0, -0.325, 0.046], spread: [0.10, 0], size: 0.020 }),
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
    // docs/concept/aisle_sign.png sets an oak panel into a DEEP steel frame —
    // deep enough to cast a line of shadow across the panel from above — with
    // a cream lettering band across the middle and a few coral marks on it.
    // A flat panel on two rods was a placeholder; the frame is the object.
    colors: {
      base: PALETTE.oak, // the panel
      middle: PALETTE.oakDark,
      accent1: PALETTE.charcoal, // FRAME  — the deep surround and the rods
      accent2: PALETTE.signal, // ACCENT — the coral marks
      accent3: PALETTE.espresso, // DARK   — rod collars and the panel's shadow
      accent4: PALETTE.paper, // the lettering band
    },
    axes: {
      x: { mode: 'repeat', unit: 0.9, min: 1, max: 4, default: 1, label: 'panels' },
      y: FIXED,
      z: FIXED,
    },
    build: () => [
      { size: [0.90, 0.38, 0.075], at: [0, -0.02, 0], bevel: 0.010, mat: 'steel', accent: FRAME }, // the frame
      { size: [0.84, 0.32, 0.055], at: [0, -0.02, 0.014], bevel: 0.008, mat: 'wood' }, // panel
      { size: [0.84, 0.020, 0.030], at: [0, 0.128, 0.036], bevel: 0.004, mat: 'paint', accent: DARK }, // shadow under the head
      { size: [0.78, 0.115, 0.020], at: [0, 0.010, 0.044], bevel: 0.005, mat: 'paper', accent: GLASS }, // lettering band
      { size: [0.70, 0.055, 0.012], at: [0, 0.010, 0.056], bevel: 0.003, mat: 'detail', accent: FRAME },
      { size: [0.075, 0.045, 0.020], at: [-0.335, -0.115, 0.046], bevel: 0.004, mat: 'paint', accent: ACCENT }, // coral marks
      { size: [0.075, 0.045, 0.020], at: [0.290, -0.115, 0.046], bevel: 0.004, mat: 'paint', accent: ACCENT },
      { size: [0.90, 0.050, 0.085], at: [0, 0.190, 0], bevel: 0.008, mat: 'steel', accent: FRAME }, // top rail
      { size: [0.055, 0.050, 0.055], at: [-0.34, 0.205, 0], bevel: 0.008, mat: 'wood', accent: DARK }, // rod collar
      { size: [0.055, 0.050, 0.055], at: [0.34, 0.205, 0], bevel: 0.008, mat: 'wood', accent: DARK },
      { size: [0.028, 0.30, 0.028], at: [-0.34, 0.345, 0], bevel: 0.006, mat: 'steel', accent: FRAME }, // drop rod
      { size: [0.028, 0.30, 0.028], at: [0.34, 0.345, 0], bevel: 0.006, mat: 'steel', accent: FRAME },
      ...studs({ at: [0, -0.02, 0.040], spread: [0.405, 0.155], size: 0.018 }),
    ],
    mounts: onFloor,
    provides: () => [],
  },
};
