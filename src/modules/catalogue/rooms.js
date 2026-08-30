// Consultation, staff and signage — the rooms off the shop floor, and the
// things that go on a wall.
import { PALETTE } from '../../art/palette.js';
import { POOLS } from '../decor.js';
import { AXIS, FIXED, onFloor } from './schema.js';
import { ACCENT, DARK, FRAME, GLASS, capTray, plate, vents } from './fittings.js';

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
      // THE WALLS ARE SPLIT, and that split is the whole object. A consultation
      // booth is solid to waist height so nobody outside sees who is sitting
      // down, and glazed above so the pharmacist can be seen but not heard.
      // Ours had full-height opaque walls with a glass panel stuck on the INNER
      // face, which from outside is invisible — the booth read as a solid shed,
      // and before the front wall existed at all, as a canopy on legs.
      //
      // Lower panel to y = 0.10, glazing from there to the head, on all four
      // faces including the one you look at it from.
      { size: [1.80, 1.25, 0.09], at: [0, -0.525, -0.855], bevel: 0.02, mat: 'panel' }, // back: infill
      { size: [1.72, 0.94, 0.05], at: [0, 0.585, -0.855], bevel: 0.010, mat: 'glass', accent: GLASS }, // back: glazing
      { size: [1.80, 0.060, 0.11], at: [0, 0.115, -0.855], bevel: 0.010, mat: 'wood', accent: FRAME }, // glazing bead
      { size: [1.80, 0.055, 0.11], at: [0, 1.055, -0.855], bevel: 0.010, mat: 'wood', accent: FRAME },
      { size: [0.09, 1.25, 1.80], at: [-0.855, -0.525, 0], bevel: 0.02, mat: 'panel' }, // side: infill
      { size: [0.05, 0.94, 1.72], at: [-0.855, 0.585, 0], bevel: 0.010, mat: 'glass', accent: GLASS }, // side: glazing
      { size: [0.11, 0.060, 1.80], at: [-0.855, 0.115, 0], bevel: 0.010, mat: 'wood', accent: FRAME }, // glazing bead
      { size: [0.11, 0.055, 1.80], at: [-0.855, 1.055, 0], bevel: 0.010, mat: 'wood', accent: FRAME },
      { size: [1.80, 1.25, 0.09], at: [0, -0.525, 0.855], bevel: 0.02, mat: 'panel' }, // front: infill
      { size: [1.72, 0.94, 0.05], at: [0, 0.585, 0.855], bevel: 0.010, mat: 'glass', accent: GLASS }, // front: glazing
      { size: [1.80, 0.060, 0.11], at: [0, 0.115, 0.855], bevel: 0.010, mat: 'wood', accent: FRAME }, // glazing bead
      { size: [1.80, 0.055, 0.11], at: [0, 1.055, 0.855], bevel: 0.010, mat: 'wood', accent: FRAME },
      { size: [0.09, 1.25, 0.80], at: [0.855, -0.525, -0.50], bevel: 0.02, mat: 'panel' }, // door-side return
      { size: [0.05, 0.94, 0.72], at: [0.855, 0.585, -0.50], bevel: 0.010, mat: 'glass', accent: GLASS },
      { size: [0.11, 0.060, 0.80], at: [0.855, 0.115, -0.50], bevel: 0.010, mat: 'wood', accent: FRAME },
      { size: [0.11, 0.055, 0.80], at: [0.855, 1.055, -0.50], bevel: 0.010, mat: 'wood', accent: FRAME },
      // A DOOR LEAF in the opening. There was a door post, a door head and two
      // hinges hung on nothing — the booth had a doorway you could walk through
      // and the sheet has a heavy timber door filling it.
      { size: [0.075, 2.00, 0.86], at: [0.855, -0.150, 0.345], bevel: 0.016, mat: 'wood', accent: FRAME }, // door leaf
      { size: [0.030, 1.60, 0.62], at: [0.900, -0.150, 0.345], bevel: 0.012, mat: 'wood', accent: DARK }, // its sunk panel
      { size: [0.045, 0.045, 0.20], at: [0.905, -0.150, 0.700], bevel: 0.008, mat: 'steel', accent: DARK }, // handle
      // the heavy timber frame: corner posts and a real door surround
      { size: [0.15, 2.24, 0.15], at: [-0.855, -0.05, -0.855], bevel: 0.018, mat: 'wood', accent: FRAME },
      { size: [0.15, 2.24, 0.15], at: [0.855, -0.05, -0.855], bevel: 0.018, mat: 'wood', accent: FRAME },
      { size: [0.15, 2.24, 0.15], at: [-0.855, -0.05, 0.855], bevel: 0.018, mat: 'wood', accent: FRAME },
      { size: [0.16, 2.24, 0.16], at: [0.855, -0.05, 0.30], bevel: 0.018, mat: 'wood', accent: FRAME }, // door post
      { size: [0.12, 0.24, 1.10], at: [0.855, 0.945, 0.35], bevel: 0.014, mat: 'wood', accent: FRAME }, // door head
      { size: [0.14, 0.16, 0.16], at: [0.860, 0.500, 0.395], bevel: 0.012, mat: 'steel', accent: DARK }, // hinge
      { size: [0.14, 0.16, 0.16], at: [0.860, -0.500, 0.395], bevel: 0.012, mat: 'steel', accent: DARK },
      { size: [1.94, 0.10, 1.94], at: [0, 1.115, 0], bevel: 0.02, mat: 'panel', accent: DARK }, // roof cap
      // The sheet stands two real vent boxes on the roof. Slots cut into the cap
      // read as nothing from below, which is the only angle this roof is seen
      // from; a box breaks the roofline and is visible from across the room.
      { size: [0.42, 0.15, 0.34], at: [-0.34, 1.240, -0.30], bevel: 0.014, mat: 'panel', accent: DARK },
      ...vents({ at: [-0.34, 1.240, -0.135], n: 3, w: 0.34, thickness: 0.030, gap: 0.055, depth: 0.020, accent: FRAME }),
      { size: [0.34, 0.12, 0.30], at: [0.36, 1.225, 0.22], bevel: 0.014, mat: 'panel', accent: DARK },
      ...vents({ at: [0.36, 1.225, 0.375], n: 3, w: 0.26, thickness: 0.026, gap: 0.048, depth: 0.018, accent: FRAME }),
      { size: [1.86, 0.13, 0.13], at: [0, -1.085, -0.855], bevel: 0.014, mat: 'paint', accent: ACCENT }, // skirting
      { size: [0.13, 0.13, 1.86], at: [-0.855, -1.085, 0], bevel: 0.014, mat: 'paint', accent: ACCENT },
      { size: [0.13, 0.13, 0.86], at: [0.855, -1.085, -0.50], bevel: 0.014, mat: 'paint', accent: ACCENT },
      // the sign over the door, on brackets
      { size: [0.05, 0.34, 0.86], at: [0.900, 0.86, 0.35], bevel: 0.010, mat: 'wood', accent: FRAME },
      { size: [0.03, 0.26, 0.76], at: [0.922, 0.86, 0.35], bevel: 0.006, mat: 'paper', accent: GLASS },
      { size: [0.02, 0.10, 0.46], at: [0.936, 0.86, 0.35], bevel: 0.004, mat: 'detail', accent: FRAME },
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
    // Reproportioned to the reference's cartooned build. It was a correctly
    // sized chair — thin legs, thin cushions, a tall thin back — and a
    // correctly sized chair reads as spindly next to everything else here.
    // The legs are half again as thick and a third shorter, the cushions are
    // fat slabs, and the frame is heavy enough to carry them.
    //
    // The seat-pan vent strip and the coral maker's label are gone. A chair
    // seat does not need to breathe through its front edge, and nothing in
    // this room is read at a distance where a 3 cm label is anything but a
    // coral speck — neither could survive the question of why it was there.
    build: () => [
      { size: [0.46, 0.160, 0.44], at: [0, 0.020, 0.02], bevel: 0.020, mat: 'fabric', accent: FRAME }, // seat cushion
      { size: [0.46, 0.024, 0.44], at: [0, -0.052, 0.02], bevel: 0.006, mat: 'fabric', accent: GLASS }, // its shadow edge
      // A contract chair's back FLOATS on its posts, with daylight between it
      // and the seat. Ours sat the back cushion straight down on the seat, which
      // reads as an armchair. That gap is the single thing that identifies the
      // object in the sheet, so the back starts 9 cm higher and loses the depth
      // it does not need.
      { size: [0.44, 0.330, 0.13], at: [0, 0.290, -0.165], bevel: 0.020, mat: 'fabric', accent: FRAME }, // back cushion
      { size: [0.44, 0.024, 0.13], at: [0, 0.137, -0.165], bevel: 0.006, mat: 'fabric', accent: GLASS },
      { size: [0.48, 0.060, 0.46], at: [0, -0.080, 0.02], bevel: 0.010, mat: 'steel' }, // seat pan
      { size: [0.085, 0.46, 0.075], at: [-0.190, 0.160, -0.215], bevel: 0.012, mat: 'steel' }, // back post
      { size: [0.085, 0.46, 0.075], at: [0.190, 0.160, -0.215], bevel: 0.012, mat: 'steel' },
      { size: [0.100, 0.070, 0.060], at: [-0.190, 0.340, -0.205], bevel: 0.010, mat: 'steel', accent: DARK }, // bracket
      { size: [0.100, 0.070, 0.060], at: [-0.190, 0.100, -0.205], bevel: 0.010, mat: 'steel', accent: DARK },
      { size: [0.075, 0.34, 0.075], at: [-0.180, -0.280, 0.17], bevel: 0.012, mat: 'steel' }, // leg
      { size: [0.075, 0.34, 0.075], at: [0.180, -0.280, 0.17], bevel: 0.012, mat: 'steel' },
      { size: [0.075, 0.34, 0.075], at: [-0.180, -0.280, -0.15], bevel: 0.012, mat: 'steel' },
      { size: [0.075, 0.34, 0.075], at: [0.180, -0.280, -0.15], bevel: 0.012, mat: 'steel' },
      { size: [0.42, 0.045, 0.045], at: [0, -0.360, 0.17], bevel: 0.008, mat: 'steel', accent: DARK }, // stretcher
      { size: [0.48, 0.030, 0.030], at: [0, 0.050, 0.232], bevel: 0.008, mat: 'paint', accent: DARK }, // seat piping
      { size: [0.46, 0.034, 0.034], at: [0, 0.442, -0.165], bevel: 0.008, mat: 'paint', accent: DARK }, // back piping
    ],
    mounts: onFloor,
    provides: () => [],
  },
};

/** One tier of locker: a 0.79 m door and the rail under it. */
const LOCKER_TIER = 0.85;

/**
 * One BAY of lockers at a given tier count — two doors, or three.
 *
 * A locker bank does not get taller by having taller doors; it gets taller by
 * having another tier of them, which is 0.85 m of object each time. So the
 * doors, their vents, their handles and their number plates come per tier,
 * while the things there is only ever one of — the sloped crown, the cap under
 * it, the plinth, the two full-height stiles and the carcass — stay singular
 * and simply grow with the bank.
 *
 * Everything is a literal per tier count rather than derived arithmetic, so the
 * two-tier bay is the original part list to the last bit. The origin is the
 * centre of the bay's own height (unit[1] * v above the floor), which is what
 * resize.layout's stepLift exists to place.
 */
function lockerParts(v) {
  const three = v > 1;
  const carcassH = three ? 2.57 : 1.72;
  const stileH = three ? 2.53 : 1.68;
  const plinthY = three ? -1.300 : -0.875;
  const footY = three ? -1.223 : -0.798;
  const headY = three ? 1.303 : 0.878;
  const capY = three ? 1.330 : 0.905;
  const crownY = three ? 1.375 : 0.950;
  const doorY = three ? [0.880, 0.030, -0.820] : [0.455, -0.395]; // top down
  const railY = three ? [0.455, -0.395] : [0.030]; // one between each pair
  const ventY = three ? [1.125, 0.275, -0.575] : [0.700, -0.150];
  const handleY = three ? [0.725, -0.125, -0.975] : [0.300, -0.550];
  const plateY = three ? [0.905, 0.055, -0.795] : [0.480, -0.370];

  return [
    { size: [0.60, carcassH, 0.50], at: [0, 0.04, 0], bevel: 0.032, mat: 'paint', accent: FRAME }, // carcass / frame
    { size: [0.62, 0.115, 0.52], at: [0, plinthY, 0], bevel: 0.012, mat: 'paint', accent: DARK }, // plinth
    ...doorY.map((y) => ({ size: [0.53, 0.79, 0.035], at: [0.005, y, 0.256], bevel: 0.010, mat: 'panel' })), // door
    // the frame reading through: stiles down the sides, a rail between doors
    { size: [0.045, stileH, 0.045], at: [-0.2775, 0.04, 0.262], bevel: 0.010, accent: FRAME },
    { size: [0.045, stileH, 0.045], at: [0.2775, 0.04, 0.262], bevel: 0.010, accent: FRAME },
    ...railY.map((y) => ({ size: [0.60, 0.055, 0.045], at: [0, y, 0.262], bevel: 0.010, accent: FRAME })), // mid rail
    { size: [0.60, 0.045, 0.045], at: [0, headY, 0.262], bevel: 0.010, accent: FRAME }, // head rail
    { size: [0.60, 0.045, 0.045], at: [0, footY, 0.262], bevel: 0.010, accent: FRAME }, // foot rail
    // Both fittings were drawn at the size a real locker has them, which at
    // playing distance is nothing. On the sheet the vent stack and the number
    // plate are the two things you read on a door, so they are sized to be read.
    ...ventY.flatMap((y) => vents({ at: [0, y, 0.276], n: 4, w: 0.34, thickness: 0.030, gap: 0.052, depth: 0.018 })),
    ...handleY.map((y) => ({ size: [0.034, 0.17, 0.050], at: [0.228, y, 0.280], bevel: 0.006, mat: 'steel', accent: ACCENT })), // handle
    ...plateY.flatMap((y) => plate({ at: [-0.150, y, 0.278], w: 0.17, h: 0.090, depth: 0.014 })), // number plate
    { size: [0.024, 0.020, 0.44], at: [-0.302, 0.04, 0], bevel: 0.005, mat: 'steel', accent: DARK }, // side seam
    { size: [0.62, 0.050, 0.52], at: [0, capY, 0], bevel: 0.012, accent: DARK }, // top cap
    { size: [0.60, 0.055, 0.48], at: [0, crownY, 0.02], bevel: 0.012, accent: FRAME }, // sloped crown
  ];
}

export const STAFF = {
  // Straight off the reference: green steel lockers, three vent slots per door,
  // a number plate and a stubby handle. Repeat them along the wall.
  locker_bank: {
    id: 'locker_bank',
    label: 'Staff lockers',
    category: 'staff',
    blurb: 'Two or three tiers per bay, vented doors, numbered.',
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
      base: PALETTE.teal, // the doors: green on the sheet, and tealDeep went to black in shadow
      middle: PALETTE.teal,
      accent1: PALETTE.paper, // FRAME  — stiles, rails, crown
      accent2: PALETTE.steel, // ACCENT — handles and hinges
      accent3: PALETTE.charcoal, // DARK   — plinth, vents, side seams
      accent4: PALETTE.glass, // GLASS  — the number plates
    },
    // §C2 — height used to be FIXED, because the only honest way to make a
    // locker bank taller is to put another tier of doors in it, and a stretch
    // axis would have given you one 1.6 m door with the vents pulled into
    // stripes. It steps now: one more tier is one more 0.85 m of locker, so the
    // step's v is exactly that as a multiple of the 1.8 m unit height. Width
    // stays repeat — a bay of lockers really is one bay repeated — and the two
    // compose: the bay geometry is rebuilt at the current tier count and then
    // instanced along x, which is one geometry per (tiers × nothing) and N
    // meshes per bank.
    axes: {
      x: { mode: 'repeat', unit: 0.6, min: 1, max: 8, default: 3, label: 'bays' },
      y: {
        mode: 'steps',
        default: 1,
        label: 'tiers',
        steps: [
          { v: 1, label: '2 tiers' },
          { v: (1.8 + LOCKER_TIER) / 1.8, label: '3 tiers' },
        ],
      },
      z: FIXED,
    },
    build: (p) => lockerParts(p.y),
    mounts: onFloor,
    provides: (p, unit) => [
      { tag: 'gondola_side', pos: [unit[0] * p.x, unit[1] * p.y, 0], normal: [1, 0, 0] },
      { tag: 'gondola_side', pos: [-unit[0] * p.x, unit[1] * p.y, 0], normal: [-1, 0, 0] },
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
      { size: [0.48, 1.29, 0.62], at: [0, 0.005, 0], bevel: 0.032, mat: 'paint', accent: FRAME }, // carcass / frame
      { size: [0.46, 0.070, 0.60], at: [0, -0.630, 0], bevel: 0.008, mat: 'paint', accent: DARK }, // plinth
      ...capTray({ at: [0, 0.670, 0], w: 0.52, d: 0.66, rim: 0.045, thickness: 0.036, panel: GLASS }),
      { size: [0.042, 1.26, 0.045], at: [-0.221, 0.005, 0.315], bevel: 0.008, mat: 'steel', accent: FRAME }, // stile
      { size: [0.042, 1.26, 0.045], at: [0.221, 0.005, 0.315], bevel: 0.008, mat: 'steel', accent: FRAME },
      ...[-0.475, -0.165, 0.145, 0.455].flatMap((y) => [
        { size: [0.42, 0.280, 0.030], at: [0, y, 0.312], bevel: 0.008, mat: 'panel' },
        // A 16 mm reveal is invisible, so the cabinet read as one grey box with
        // handles stuck on it instead of as four drawers. This is the seam that
        // does the identifying, so it gets the width to do it.
        { size: [0.44, 0.032, 0.042], at: [0, y - 0.152, 0.316], bevel: 0.005, mat: 'paint', accent: DARK }, // reveal
        // the pull block: proud, cream, with a dark label slot cut into it
        { size: [0.20, 0.075, 0.055], at: [0, y + 0.010, 0.342], bevel: 0.010, mat: 'paint', accent: ACCENT },
        { size: [0.165, 0.038, 0.030], at: [0, y + 0.020, 0.362], bevel: 0.005, mat: 'paper', accent: DARK },
        { size: [0.20, 0.020, 0.030], at: [0, y - 0.030, 0.356], bevel: 0.004, mat: 'paint', accent: DARK }, // its shadow
      ]),
      ...vents({ at: [-0.245, 0.330, 0.10], n: 4, w: 0.20, thickness: 0.016, gap: 0.028, depth: 0.012, axis: 'x' }),
      ...vents({ at: [-0.245, -0.330, 0.10], n: 4, w: 0.20, thickness: 0.016, gap: 0.028, depth: 0.012, axis: 'x' }),
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
      // The back plate was 0.78 square behind a cross 0.80 across, so from any
      // angle off-axis the object read as a dark SQUARE with a cross on it. The
      // silhouette is the entire job of this sign. The plate is now small enough
      // to hide behind the cross's own arms, which is what the sheet shows.
      { size: [0.26, 0.26, 0.045], at: [0, 0, -0.055], bevel: 0.010, mat: 'panel', accent: DARK }, // back plate
      { size: [0.30, 0.80, 0.10], at: [0, 0, -0.004], bevel: 0.014, mat: 'steel', accent: FRAME }, // rim
      { size: [0.80, 0.30, 0.10], at: [0, 0, -0.004], bevel: 0.014, mat: 'steel', accent: FRAME },
      { size: [0.26, 0.76, 0.098], at: [0, 0, 0.004], bevel: 0.012, mat: 'paint' }, // body
      { size: [0.76, 0.26, 0.098], at: [0, 0, 0.004], bevel: 0.012, mat: 'paint' },
      // Narrower than it was. The pale glow surround had eaten most of the
      // face, leaving a thin green edge; on the sheet the deep green border is
      // wide and the lit panel sits well inside it, which is what stops the
      // sign reading as a white cross.
      { size: [0.15, 0.58, 0.024], at: [0, 0, 0.046], bevel: 0.006, mat: 'paint', accent: ACCENT }, // glow surround
      { size: [0.58, 0.15, 0.024], at: [0, 0, 0.046], bevel: 0.006, mat: 'paint', accent: ACCENT },
      // the lit face is an illuminated panel, so it takes the glass strip
      { size: [0.15, 0.61, 0.016], at: [0, 0, 0.056], bevel: 0.004, mat: 'glass', accent: GLASS },
      { size: [0.61, 0.15, 0.016], at: [0, 0, 0.056], bevel: 0.004, mat: 'glass', accent: GLASS },
      { size: [0.08, 0.08, 0.16], at: [0, 0, -0.14], bevel: 0.010, mat: 'steel', accent: DARK }, // wall stalk
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
      accent3: PALETTE.ink, // DARK   — rod collars and the panel's shadow: dark steel
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
      // ONE band. The panel had been sliced into four horizontal stripes — a
      // shadow bead, a lettering band, a detail band and two coral marks — and
      // at any distance that reads as a venetian blind rather than as a sign.
      // The sheet is an oak panel with a single wide cream band across it and
      // one coral mark at the end of the line.
      { size: [0.80, 0.150, 0.024], at: [0, 0.010, 0.046], bevel: 0.005, mat: 'paper', accent: GLASS }, // lettering band
      { size: [0.075, 0.055, 0.016], at: [0.300, -0.115, 0.046], bevel: 0.004, mat: 'paint', accent: ACCENT }, // its one mark
      { size: [0.90, 0.050, 0.085], at: [0, 0.190, 0], bevel: 0.008, mat: 'steel', accent: FRAME }, // top rail
      // The collar is the fitting that clamps a steel rod to a steel rail. It
      // was carrying wood grain and a timber colour, which no such part has.
      { size: [0.055, 0.050, 0.055], at: [-0.34, 0.205, 0], bevel: 0.008, mat: 'steel', accent: DARK }, // rod collar
      { size: [0.055, 0.050, 0.055], at: [0.34, 0.205, 0], bevel: 0.008, mat: 'steel', accent: DARK },
      { size: [0.028, 0.30, 0.028], at: [-0.34, 0.345, 0], bevel: 0.006, mat: 'steel', accent: FRAME }, // drop rod
      { size: [0.028, 0.30, 0.028], at: [0.34, 0.345, 0], bevel: 0.006, mat: 'steel', accent: FRAME },
    ],
    mounts: onFloor,
    provides: () => [],
  },
};
