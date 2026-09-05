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
import { STYLE, tableBox, decal } from '../style.js';

export const objLo = 0;
export const objHi = 63;
export const label = 'home fridge';

export function build(THREE, MATS, kit, H) {
  const g = new THREE.Group();
  const add = (kind, a, b, opts) => g.add(tableBox(THREE, kind, a, b, MATS, opts));
  const tx = (n) => n * STYLE.texel;
  const T = STYLE.tint;

  // ---- PHASE 1: proportions, as fractions of one driving dimension ---------
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

  const F = -D;                // body front face
  // Mounting planes, named before any geometry exists and used to build it.
  const P_DOOR = F - 2.2;      // the doors stand proud of the carcass
  const P_BODY = F;
  const EPS = 0.1;

  // THE ROUNDING IS THE WHOLE CHARACTER of a 1950s fridge, so the body and the
  // doors carry a much heavier chamfer than the default. shapedBox clamps it to
  // a third of the smallest side, so the thin door slabs stay sane on their own.
  const ROUND = { bevel: 3.4 };
  const DOOR_ROUND = { bevel: 2.6 };

  // ---- feet: four stubby blocks -------------------------------------------
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    const x1 = sx > 0 ? W - 5 : -W + 1, x2 = sx > 0 ? W - 1 : -(W - 5);
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
  add('mint', [-W, -D, z(0.10)], [W, D, z(1.0)],
      { ...ROUND, taperX: 0.9, taperZ: 0.9 });

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
  // Measured at x 0.115..0.208 of the width, which is 0.115*2W in from the left.
  // Measured from the reference's LEFT edge; +x renders on the image left
  // with this camera, so the measurement mirrors into positive x.
  const hx2 = W - 0.115 * 2 * W, hx1 = W - 0.208 * 2 * W;
  const handle = (zLo, zHi) => {
    add('steel', [hx1, P_DOOR - 1.8, z(zLo)], [hx2, P_DOOR - 0.2, z(zHi)],
        { bevel: 0.7 });
    for (const zz of [zLo, zHi]) {          // the two mounts
      add('steel', [hx1 + 0.4, P_DOOR - 0.4, z(zz) - 0.6],
                   [hx2 - 0.4, P_DOOR, z(zz) + 0.6], { bevel: 0 });
    }
  };
  handle(0.200, 0.560);
  handle(0.720, 0.815);

  // ---- top cap ------------------------------------------------------------
  add('mint', [-(W - 0.6), -(D - 0.6), z(0.965)], [W - 0.6, D - 0.6, z(1.0)],
      { bevel: 2.0 });

  // ---- FITTINGS -----------------------------------------------------------
  // A badge on the upper door and a rating plate round the side, both mounted
  // on named planes rather than on numbers typed here.
  g.add(decal(THREE, kit, 'ratingPlate', 'front', -W * 0.12, z(0.812),
              tx(2.2), P_DOOR - EPS, T.front));
  g.add(decal(THREE, kit, 'labelHolder', 'left', 2, z(0.45),
              tx(5), -W - EPS, T.side));
  g.add(decal(THREE, kit, 'hinge', 'front', -(W - 2.2), z(0.30),
              tx(3), P_DOOR - EPS, T.front));
  g.add(decal(THREE, kit, 'hinge', 'front', -(W - 2.2), z(0.76),
              tx(3), P_DOOR - EPS, T.front));
  return g;
}
