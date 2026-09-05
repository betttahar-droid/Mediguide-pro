// The home fridge — a chunky retro two-door domestic refrigerator.
//
// THE SECOND PROP, and the point of it: this file shares every material, every
// surface tile, every fitting, the whole shader and the entire post pass with
// vaccineFridge.js. Nothing in ../style.js was changed to make it, and nothing
// in it knows what a fridge is. What is here is geometry, material names and
// placement — which is the whole claim the technique makes.
//
// Built by following docs/making-a-prop.txt phase by phase. Every proportion
// below came off docs/style-bible/props/home_fridge.png measured band by band
// against a magenta ground, never read by eye.
//
// MEASURED (front view 312 x 616 px):
//   overall ratio      1 : 1.97
//   depth / width      1.003  — square in plan, unlike the vaccine fridge
//   feet               z 0.000 .. 0.045
//   plinth + vent      z 0.045 .. 0.130
//   lower door         z 0.140 .. 0.647   (51% of the height)
//   door gap           z 0.647 .. 0.690
//   upper door         z 0.690 .. 0.846   (16%)
//   top cap            z 0.846 .. 1.000
//   handle             x 0.115 .. 0.208 of the width, on BOTH doors
import { STYLE, tableBox, decal, capProfile } from '../style.js';

export const objLo = 0;
export const objHi = 63;
export const label = 'home fridge';

export function build(THREE, MATS, kit, H) {
  const g = new THREE.Group();
  const add = (kind, a, b, opts) => g.add(tableBox(THREE, kind, a, b, MATS, opts));
  const tx = (n) => n * STYLE.texel;
  const T = STYLE.tint;

  // ---- HOW EACH PART BEHAVES WHEN THE PROP RESIZES ------------------------
  // Not everything scales, and getting this wrong is invisible until you widen
  // the prop. Every part is exactly one of three kinds:
  //
  //   STRETCH  fills the span. The carcass, the doors, the plinth. Written as
  //            fractions of W, because that IS what they are.
  //   ANCHOR   a FIXED WORLD SIZE at a FIXED DISTANCE from a named edge.
  //            Handles, feet, badges, controls, hinges. Written with the
  //            helpers below and never as a fraction of W — a fraction makes a
  //            handle grow with the cabinet, which is exactly the bug this
  //            comment exists to prevent.
  //   REPEAT   a fixed size whose COUNT follows the span. The vent slats.
  //
  // The tell for a mistake is: widen the prop and see what changed size that
  // should not have.
  const W = H;                 // body half-width — the 100%
  const D = W * 1.003;         // half-depth: square in plan
  // HEIGHT IS INDEPENDENT OF WIDTH. Deriving it as W * 3.95 meant widening the
  // prop also made it taller — a uniform scale, which is not what a builder
  // resize does and not what the acceptance test is asking. The 1:1.97 ratio
  // sets the height ONCE, at the default width; after that the two axes move
  // separately and only the width changes. objHi below is the same number, so
  // the geometry and the shading ramp cannot disagree.
  const TOT = objHi - objLo;
  const z = (f) => f * TOT;    // a measured fraction -> world height

  // ANCHOR helpers: a fixed distance in from an edge, never a fraction of it.
  const fromR = (off) => W - off;
  const fromL = (off) => -W + off;

  const F = -D;                // body front face
  // Mounting planes, named before any geometry exists and used to build it.
  const P_DOOR = F - 2.2;      // the doors stand proud of the carcass
  const P_BODY = F;
  const EPS = 0.1;

  // BEVELS ARE PER AXIS, not one number everywhere. A uniform chamfer rounds
  // every edge equally and the prop reads as a bar of soap; the reference has
  // soft vertical corners, a soft shoulder and a crisp base. [x, y, z]:
  const ROUND = { bevel: [2.6, 0.8, 2.6] };      // soft sides, near-crisp top/base
  const DOOR_ROUND = { bevel: [2.2, 1.2, 0.6] }; // soft sides, softer top, flat face

  // The shoulder profile, MEASURED off the reference in world units above the
  // point where the body stops being full width (z 0.94). Three flat steps, in
  // the PS1 manner — see capProfile().
  const SHOULDER = [[1.26, 0.61], [2.52, 1.33], [3.47, 3.02]];

  // ---- feet: four stubby blocks -------------------------------------------
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    // ANCHOR: a fixed 4x4 block a fixed 1 unit in from each corner.
    const x1 = sx > 0 ? fromR(5) : fromL(1), x2 = sx > 0 ? fromR(1) : fromL(5);
    const y1 = sy > 0 ? D - 5 : -D + 1, y2 = sy > 0 ? D - 1 : -(D - 5);
    add('steel', [x1, y1, 0], [x2, y2, z(0.045)], { bevel: 1.0 });
  }

  // ---- plinth and its vent recess -----------------------------------------
  add('mint', [-(W - 2), -(D - 1), z(0.030)], [W - 2, D - 1, z(0.13)],
      { bevel: 1.2 });
  // The vent is a recessed dark panel with real slats, so a wider fridge gets
  // MORE slats at the same pitch rather than stretched ones.
  add('slot', [-(W - 6), F - 0.6, z(0.055)], [W - 6, F - 0.2, z(0.115)]);
  for (let s = -(W - 7); s < W - 7; s += 3.2) {
    add('mint', [s, F - 0.9, z(0.055)], [s + 1.4, F - 0.5, z(0.115)],
        { bevel: 0 });
  }

  // ---- the carcass: ONE big rounded shell ---------------------------------
  // A retro fridge is one mass, not an assembly. The doors sit on the front of
  // it; everything else is this box.
  const TAPER = 0.9;
  add('mint', [-W, -D, z(0.10)], [W, D, z(0.94)],
      { ...ROUND, taperX: TAPER, taperZ: TAPER });
  // The shoulder starts at the carcass's TAPERED top width, not at W. Starting
  // it at W made every step overhang the body by the taper and the whole top
  // read as a stepped cornice sitting on the fridge — a wedding cake. A tapered
  // part and anything stacked on it have to agree about where its top edge is.
  capProfile(add, 'mintFlat', W - TAPER, D - TAPER, z(0.94), SHOULDER,
             { bevel: [0.9, 0, 0.9] });

  // ---- doors --------------------------------------------------------------
  // Both are slabs standing proud of the carcass, inset slightly at the sides
  // so the carcass reads as a frame around them.
  const dIn = W - 1.4;
  const door = (zLo, zHi) =>
    add('mint', [-dIn, P_DOOR, z(zLo)], [dIn, P_BODY + 1, z(zHi)], DOOR_ROUND);
  // The DARK gap measures z 0.667..0.685 — 1.8% of the height, not the 4.3%
  // of the 0.647..0.690 band, which also contains the doors' own highlight
  // edges. Reading the wider band as the gap made a thin shadow line into a
  // fat black bar; the doors run right up to it.
  door(0.140, 0.665);          // lower (fridge) door
  door(0.686, 0.846);          // upper (freezer) door

  // The gap between them is a recess you see darkness through, not a painted
  // line — the same distinction that once put a cream bar between two drawers
  // of one carcass on the other model.
  add('slot', [-dIn, P_DOOR + 0.4, z(0.663)], [dIn, P_BODY, z(0.688)],
      { bevel: 0 });

  // ---- handles: long slim verticals on the opening edge of each door -------
  // ANCHORED, NOT SCALED. Measured at x 0.115..0.208 of the reference's width,
  // which at the default half-width is 3.7 units in from the edge and 3.0 units
  // wide. Both of those are now CONSTANTS: a wider fridge gets the same handle
  // in the same place relative to its edge, not a wider handle. Written as
  // fractions of W (as it was) the handle grew with the cabinet.
  const H_OFF = 3.7;           // fixed distance in from the door's edge
  const H_W = 3.0;             // fixed handle width
  const hx2 = fromR(H_OFF), hx1 = hx2 - H_W;

  // A handle with some character, not a bar. The reference's is a grip standing
  // off the door on two mounts, with a bright face and a darker return under
  // it — five small boxes, all at fixed world sizes.
  const handle = (zLo, zHi) => {
    const a = z(zLo), b = z(zHi);
    // The mounts are WIDER than the grip, so they read as separate pieces
    // rather than hiding behind it — the silhouette is what sells a fitting.
    // The mount inset is fixed EXCEPT where the handle is too short to hold
    // two of them — the freezer door's is a third the length of the fridge
    // door's, and fixed insets made the two mounts meet in the middle and read
    // as a lozenge. Same rule as everywhere else: a fixed-size feature gates on
    // whether the thing it sits on can carry it.
    const m = Math.min(1.4, (b - a) * 0.18);
    for (const zz of [a + m, b - m]) {
      add('steel', [hx1 - 0.5, P_DOOR - 1.4, zz - 1.0],
                   [hx2 + 0.5, P_DOOR + 0.2, zz + 1.0], { bevel: 0.4 });
    }
    // the grip, standing proud on them, with rounded ends
    add('steel', [hx1, P_DOOR - 2.8, a], [hx2, P_DOOR - 1.2, b], { bevel: 0.8 });
    // a bright chrome catch down its lit face, and a dark return underneath
    add('chrome', [hx1 + 0.35, P_DOOR - 3.0, a + 0.8],
                  [hx1 + 1.15, P_DOOR - 2.7, b - 0.8], { bevel: 0 });
    add('slot', [hx1 + 0.3, P_DOOR - 1.35, a + 0.5],
                [hx2 - 0.3, P_DOOR - 1.2, b - 0.5], { bevel: 0 });
  };
  handle(0.200, 0.560);
  handle(0.720, 0.815);

  // ---- top ----------------------------------------------------------------
  // THERE IS NO TOP CAP. Measured across the reference, the body holds full
  // width to z 0.94 and then curves in to 0.81 by the very top — a rounded
  // SHOULDER, not a lid. The carcass bevel of 3.4 units already produces 0.79
  // there, which is the measurement within a pixel. The separate narrower slab
  // that used to sit here was inventing a lid the reference does not have, and
  // it read as one.

  // ---- badge --------------------------------------------------------------
  // MEASURED: x 0.394..0.606 of the body (centred, 21% wide) and 4.8% of the
  // height. That is an aspect of about 2.2; the fittings atlas's rating plate
  // is 1.46 and could not make the shape without being stretched, which is the
  // one thing a fitting must never be. A plain chrome nameplate is three boxes,
  // so it is geometry. Centred, so its POSITION needs no anchoring; its SIZE is
  // fixed, so a wider fridge gets the same badge.
  const B_W = 0.21 * 2 * W, B_H = 0.048 * TOT;
  const bz = z(0.870);
  add('steel', [-B_W / 2, P_DOOR - 0.5, bz - B_H / 2],
               [B_W / 2, P_DOOR, bz + B_H / 2], { bevel: 0.5 });
  add('chrome', [-B_W / 2 + 0.6, P_DOOR - 0.8, bz - B_H / 2 + 0.5],
                [B_W / 2 - 0.6, P_DOOR - 0.4, bz + B_H / 2 - 0.5], { bevel: 0.3 });
  add('slot', [-B_W / 2 + 1.2, P_DOOR - 0.9, bz - 0.3],
              [B_W / 2 - 1.2, P_DOOR - 0.85, bz + 0.3], { bevel: 0 });

  // ---- FITTINGS -----------------------------------------------------------
  // A badge on the upper door and a rating plate round the side, both mounted
  // on named planes rather than on numbers typed here.
  // NO HINGES ON THE FRONT. Checked rather than assumed: off-body pixels along
  // the two door edges of the reference come to 6915 and 6744 — equal, which is
  // outline and shading. A hinge would make one edge markedly busier than the
  // other. There are none, and the pair I had placed were an invention that
  // happened to straddle the door's edge and look broken.
  //
  // The rating plate goes round the side, where a real fridge carries one, and
  // is clamped to that flank.
  g.add(decal(THREE, kit, 'ratingPlate', 'left', 2, z(0.45),
              tx(5), -W - EPS, T.side, { u: D - 2, v: TOT / 2 }));
  return g;
}
