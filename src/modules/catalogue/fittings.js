// The fittings vocabulary, read off the concept sheets in docs/concept/.
//
// Every sheet in that set is built the same way, and the consistency is the
// point: a LIGHT FRAME — corner posts, stiles, rails, a tray-like top cap —
// wrapped around DARKER BODY PANELS, with the same handful of small fittings
// recurring on all of them. Studs at the corner of every frame member, a stack
// of vent slots low on a side panel, a label plate or a readout, a keypad where
// something locks.
//
// Those fittings are what §11.1 means by reading a decision off a sheet. They
// are also what stops a module being a box: a plain carcass with three hinges,
// a keypad and a warning plate is a controlled-drugs cabinet, and a pharmacist
// reads it as one instantly.
//
// So they live here rather than being retyped per module. A part list then says
// what the object IS, and the repeated ornament is one call.

/**
 * Accent slots, used the same way by every module in the catalogue.
 *
 * A module's `colors` entry fills these in, and the material paints them from
 * one draw. Keeping the roles fixed across the catalogue is what makes twenty
 * objects look like one set — the same discipline as the shared prompt prefix.
 */
export const BODY = 0; //  carcass panels — takes base/middle, so it 9-slices
export const FRAME = 1; //  the light frame: posts, stiles, rails, caps, worktops
export const ACCENT = 2; //  the one saturated colour: pulls, price rails, signals
export const DARK = 3; //  plinths, hinges, vent slots, shadow beads
export const GLASS = 4; //  glass, lit faces, pale label windows and readouts
export const NEUTRAL = 5; // a cool grey that is neither the frame nor a shadow

// The names are the usual role, not a rule: these are slot numbers, and a
// module whose sheet wants an oak shelf board where most want a dark plinth
// says so in its own `colors` comment. What has to stay fixed is that a module
// uses each slot for ONE job, so the frame never drifts into the panels.

/**
 * Four corner studs on a face — the single most repeated mark in the sheets.
 *
 * They read at a distance as the dark dots that tell you a panel is bolted to a
 * frame, and up close they catch the edge-light ramp. Deliberately larger than
 * scale: at this texel density anything under about 2 cm stops reading at all.
 *
 * @param {{at:number[], spread:number[], size?:number, accent?:number}} o
 *   at     — centre of the face, [x, y, z]
 *   spread — half-distance to the studs, [dx, dy]
 */
export function studs({ at, spread, size = 0.022, accent = DARK, mat = 'steel' }) {
  const [x, y, z] = at;
  const [dx, dy] = spread;
  const out = [];
  for (const sx of [-1, 1]) {
    for (const sy of [-1, 1]) {
      out.push({
        size: [size, size, size * 0.6],
        at: [x + sx * dx, y + sy * dy, z],
        bevel: size * 0.25,
        mat,
        accent,
      });
    }
  }
  return out;
}

/**
 * A stack of horizontal vent slots. Lockers, fridges, waste bins and steel
 * cabinets all carry one in the sheets, and it is the cheapest fitting that
 * says "this is a manufactured steel thing" rather than "this is a box".
 */
export function vents({ at, n = 3, w = 0.24, thickness = 0.02, gap = 0.036, depth = 0.014, accent = DARK, axis = 'z', mat = 'grille' }) {
  const [x, y, z] = at;
  const out = [];
  for (let i = 0; i < n; i++) {
    out.push({
      size: axis === 'x' ? [depth, thickness, w] : [w, thickness, depth],
      at: [x, y + (i - (n - 1) / 2) * gap, z],
      bevel: thickness * 0.3,
      mat,
      accent,
    });
  }
  return out;
}

/**
 * A label plate, readout or warning notice: a pale window in a darker surround.
 *
 * Two parts, because one is a rectangle and two is a fitting — the surround is
 * what makes it read as screwed on rather than printed. The face samples the
 * trim sheet's detail strip, which is where the small crisp marks live (§4.1).
 */
export function plate({ at, w = 0.13, h = 0.05, depth = 0.012, accent = GLASS, surround = FRAME, mat = 'paper' }) {
  const [x, y, z] = at;
  return [
    { size: [w, h, depth], at: [x, y, z], bevel: 0.004, mat: 'paint', accent: surround },
    { size: [w - 0.022, h - 0.016, depth * 0.7], at: [x, y, z + depth * 0.4], bevel: 0.002, mat, accent },
  ];
}

/**
 * A keypad: a plate with three key rows on it. Rows rather than individual
 * keys on purpose — at 1.5 cm a key is one texel and twelve of them read as
 * noise, where three bands still read as a keypad.
 */
export function keypad({ at, w = 0.10, h = 0.13, depth = 0.026, accent = ACCENT }) {
  const [x, y, z] = at;
  const out = [{ size: [w, h, depth], at: [x, y, z], bevel: 0.006, mat: 'paint', accent: DARK }];
  for (let i = 0; i < 3; i++) {
    out.push({
      size: [w - 0.028, 0.016, depth * 0.5],
      at: [x, y - 0.028 + (i - 1) * -0.026, z + depth * 0.4],
      bevel: 0.003,
      mat: 'detail',
      accent,
    });
  }
  // the little readout above the keys is a display, so it gets the screen strip
  out.push({ size: [w - 0.028, 0.022, depth * 0.5], at: [x, y + 0.038, z + depth * 0.4], bevel: 0.003, mat: 'screen', accent: GLASS });
  return out;
}

/**
 * A top cap built as a tray: a light rim with the body panel inset into it.
 *
 * Every cabinet in the sheet set is finished this way, and it is the detail
 * that separates a piece of furniture from an extruded rectangle — the eye
 * reads the rim's shadow line as a lid sitting on a carcass.
 */
export function capTray({ at, w, d, rim = 0.030, thickness = 0.030, accent = FRAME, panel = BODY, mat = 'paint' }) {
  const [x, y, z] = at;
  return [
    { size: [w, thickness, d], at: [x, y, z], bevel: 0.010, mat: 'paint', accent },
    {
      size: [w - rim * 2, thickness * 0.55, d - rim * 2],
      at: [x, y + thickness * 0.35, z],
      bevel: 0.008,
      mat,
      accent: panel,
    },
  ];
}

/**
 * The four corner posts of a carcass, standing slightly proud of the panels
 * between them. This is the sheets' light frame in one call, and standing the
 * posts proud is what makes the panels read as infill rather than as the object.
 */
export function posts({ at = [0, 0, 0], w, h, d, thickness = 0.055, accent = FRAME, bevel = 0.014, mat = 'steel' }) {
  const [x, y, z] = at;
  const out = [];
  for (const sx of [-1, 1]) {
    for (const sz of [-1, 1]) {
      out.push({
        size: [thickness, h, thickness],
        at: [x + sx * (w / 2 - thickness / 2), y, z + sz * (d / 2 - thickness / 2)],
        bevel,
        mat,
        accent,
      });
    }
  }
  return out;
}

/**
 * A worktop with a darker edge band under its front lip.
 *
 * Straight off the OTC counter sheet, where a warm oak top is banded in dark
 * oak all the way round. The band does the job a drawn outline used to: it
 * separates the top plane from the carcass front by value, at exactly the line
 * where the two meet.
 */
export function worktop({ at, w, d, thickness = 0.055, lip = 0.030, accent = FRAME, band = DARK, mat = 'wood' }) {
  const [x, y, z] = at;
  return [
    { size: [w, thickness, d], at: [x, y, z], bevel: 0.028, mat, accent },
    { size: [w, lip, d + 0.012], at: [x, y - thickness / 2 - lip / 2 + 0.006, z], bevel: 0.008, mat, accent: band },
  ];
}
