// The vaccine fridge — a tall glass-door display cabinet.
//
// A MODEL IS ONLY GEOMETRY AND PLACEMENT. Everything about how it looks lives
// in ../style.js, which knows nothing about fridges; this file names materials
// and fittings and says where they go. That split is what makes a second prop
// cheap: see homeFridge.js, which shares every material, every surface tile,
// every fitting and the whole shader, and is a different object entirely.
//
// See docs/making-a-prop.txt for the procedure this was built by.
import { STYLE, tableBox, decal, screws } from '../style.js';

// The object's vertical extent, for the baked shading ramp.
export const objLo = -2.5;
export const objHi = 93;
export const label = 'vaccine fridge';

export function build(THREE, MATS, kit, H) {
  const g = new THREE.Group();
  const add = (kind, a, b, opts) => g.add(tableBox(THREE, kind, a, b, MATS, opts));
  // MEASURED OFF THE DRAWN SHEET, band by band, against the sheet's own card
  // ground. The front view's body is 240 px wide and 749 px tall (1:2.75), and
  // across it: cream door border 21 px, teal door frame 5 px, glass 188 px,
  // frame 5, border 21. As fractions of the body: border 8.75% a side, frame
  // 2.1%, glass 78%. The crown runs 270 px = 1.125x the body.
  //
  // These replace hand-typed offsets that had the border at 15.5% and the glass
  // at 61% — nearly double and two thirds respectively, which is why the door
  // read as a narrow slot in a wide cream slab. The earlier note claiming a 74%
  // glass "sprawled" was itself the mis-measurement: 78% is what the sheet says.
  // Written as fractions rather than magic numbers so a re-measure is a one-line
  // change and so every proportion survives a change of H.
  // CHUNKIER THAN THE TURNAROUND, deliberately. The measured fractions below
  // came off the fridge sheet, which is a clean orthographic drawing with thin
  // frames. The prop kit this is actually meant to sit in is heavier: a whole
  // door in 138 triangles and a 64x32 texture, forms that are a handful of big
  // blocks with thick edges and stepped corners. So the door border is widened
  // from a measured 0.175 to 0.24 and the trim thickened to match. This is a
  // STYLE CHOICE overriding a measurement, which is worth flagging rather than
  // burying: the sheet is no longer the authority on proportion, the kit is.
  const W = H;                 // body half-width — the 100% everything is of
  const BORDER = W * 0.24;     // cream door border, each side (was 0.175)
  const FRAME = W * 0.055;     // teal door frame, each side (was 0.042)
  const S = W - BORDER;        // inside the border: cavity, shelves, opening
  const G = S - FRAME;         // glass half-width (78% of the body)
  const C = W * 1.16;          // crown half-width — it overhangs the body
  const GR = W * 0.70;         // grille half-width (70% of the body, measured)
  // Depth, from the SIDE view the same way: its body runs 230 px against the
  // front's 240, so the cabinet is very nearly square in plan. It had been
  // hard-coded at 14 against a half-width of 16 — 12% too shallow, which is the
  // sort of error that only ever reads as "the iso view looks a bit off".
  const D = W * 0.958;         // body half-depth
  const F = -D;                // the body's FRONT face; everything on the door
                               // is placed relative to it, so a depth change
                               // moves the door with the cabinet
  const CF = -(D + 0.5);       // the crown's front face — it overhangs too

  // NAMED MOUNTING PLANES. Every decal is placed on one of these rather than on
  // a number typed at the call site, and the geometry below is built from the
  // same constants, so the two cannot drift apart.
  //
  // This fixes decals sinking under geometry. A hinge was placed on the cream
  // border's plane, but it is wide enough to reach over the door opening, where
  // the teal frame stands 1 unit FURTHER FORWARD — so half of every hinge was
  // genuinely behind a part, not z-fighting with it. No offset or render order
  // could have fixed that; the decal was simply in the wrong place.
  //
  // The rule: a decal mounts to the FRONTMOST surface it could overlap. Where
  // two planes are in play, take the forward one and accept that the decal
  // stands proud of the other — which is what a real hinge does anyway.
  const P_BORDER = F - 1.5;    // cream door border, front plane
  const P_DOOR = F - 2.5;      // teal door frame — the frontmost door surface
  const P_BASE = F;            // base block front
  const EPS = 0.08;

  // ---- P01 feet: four corner blocks, outer faces flush with the base -------
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    const x1 = sx > 0 ? W - 8 : -W, x2 = sx > 0 ? W : -(W - 8);
    const y1 = sy > 0 ? D - 7 : -D, y2 = sy > 0 ? D : -(D - 7);
    add('plinth', [x1, y1, -2.5], [x2, y2, 4.0]);
  }
  add('plinth', [-(W - 1), -(D - 1), 0], [W - 1, D - 1, 4]); // P02 plinth strip
  // The base block TAPERS inward toward its foot, as the reference dumpster's
  // body does. A prism here read as a plinth; a taper reads as a moulded shell.
  add('teal',   [-W, -D, 4],             [W, D, 18],
      { taperX: 1.6, taperZ: 1.6 });                            // P03 condenser base
  // Tapered NARROWER AT THE TOP, so the block flares out to its foot. The sign
  // is not cosmetic: with the taper the other way the front face leaned out
  // over its own base plane, and the switch and dial mounted on that plane
  // ended up inside the solid. Tapering inward keeps the mounting plane the
  // widest cross-section, so anything mounted on it is in front of the whole
  // part at every height. A tapered part and a flat mounting plane only
  // coexist in that direction.
  // P04 grille — real louvres now, not a picture of louvres. The slot count
  // follows the width, so a wider base gets MORE slots at the same pitch: the
  // adaptive behaviour that used to need a tiling texture, done with a loop.
  add('tan',  [-GR, F - 1.2, 7.5], [GR, F, 11.5]);
  add('tan2', [-GR, F - 1.4, 7.5], [GR, F - 1.2, 11.5]);
  for (let z = 8.2; z < 11.2; z += 1.1) {
    add('slot', [-(GR - 1), F - 1.5, z], [GR - 1, F - 1.1, z + 0.6]);
  }
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {     // P05 corner blocks
    const x1 = sx > 0 ? W - 3 : -W, x2 = sx > 0 ? W : -(W - 3);
    const y1 = sy > 0 ? D - 4 : -D, y2 = sy > 0 ? D : -(D - 4);
    add('cream', [x1, y1, 13], [x2, y2, 18]);
  }

  // ---- P06 flanks, split at the carcass joint ------------------------------
  for (const sx of [-1, 1]) {
    const x1 = sx > 0 ? S : -W, x2 = sx > 0 ? W : -S;
    add('blueGrey', [x1, -D, 18], [x2, D, 50]);
    add('blueGrey', [x1, -D, 52], [x2, D, 84]);
    // The joint needs a rail. Left as an open 2-unit gap it showed the dark
    // cavity straight through, and SIDE and BACK both read a green stripe
    // across the flank.
    add('cream',    [x1, -(D + 0.2), 50], [x2, D + 0.2, 52]);
  }
  // ---- P07 back, same joint -----------------------------------------------
  add('blueGrey', [-W, D - 3, 18], [W, D, 50]);
  add('blueGrey', [-W, D - 3, 52], [W, D, 84]);
  add('cream',    [-W, D - 3, 50], [W, D + 0.2, 52]);
  add('cream',    [-W, -D, 80],    [W, D, 84]);             // top run

  // ---- P09 cavity: five dark faces ----------------------------------------
  const BW = D - 6;                       // where the cavity's back wall stands
  add('interior', [-S, BW, 18],        [S, D - 3, 80]);
  add('interior', [-S, -D, 18],        [-(S - 1.5), BW, 80]);
  add('interior', [S - 1.5, -D, 18],   [S, BW, 80]);
  add('interior', [-S, -D, 18],        [S, BW, 20]);
  add('interior', [-S, -D, 78],        [S, BW, 80]);
  // Shelves run the FULL interior depth, as the reference's iso view draws
  // them; they used to stop at the midline, which is invisible head-on and
  // wrong from every other angle.
  for (const z of [29, 41, 53, 65]) add('shelf', [-S, -(D - 1), z], [S, BW, z + 2.5]);

  // ---- P08 corner posts, now a STEP rather than a single square post -------
  // The reference kit's corners do not meet sharp: each one steps back once, so
  // the silhouette reads as chunky and slightly crude instead of machined. Two
  // nested boxes at each corner is the cheapest way to get that at this scale —
  // it is a voxel chamfer, and at 20 texels across a face it is exactly as much
  // corner as the style can resolve.
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    for (const [inx, iny, zLo, zHi] of [[3.2, 3.2, 18, 84], [5.4, 1.6, 18, 84]]) {
      const x1 = sx > 0 ? W - inx : -W, x2 = sx > 0 ? W : -(W - inx);
      const y1 = sy > 0 ? D - iny : -D, y2 = sy > 0 ? D : -(D - iny);
      add('cream', [x1, y1, zLo], [x2, y2, zHi]);
    }
  }

  // ---- P15 crown: 11% of height, a lip and one block ----------------------
  // BOTH crown pieces overhang the body, and their heights are close: a top
  // block narrower than the carcass and twice the lip's height read as a lid
  // resting on the cabinet rather than as its cap.
  add('cream', [-C, -(D + 1), 84],   [C, D + 1, 88], { taperX: -1.2, taperZ: -1.2 });
  add('cream', [-(C - 0.5), CF, 88], [C - 0.5, D + 0.5, 93]);

  // ---- P11/P12 door: a wide light between two NARROW borders ---------------
  const frame = (kind, xIn, xOut, zLo, zHi, y1, y2) => {
    add(kind, [-xOut, y1, zLo], [-xIn, y2, zHi]);
    add(kind, [xIn, y1, zLo],   [xOut, y2, zHi]);
    add(kind, [-xOut, y1, zHi - (xOut - xIn)], [xOut, y2, zHi]);
    add(kind, [-xOut, y1, zLo], [xOut, y2, zLo + (xOut - xIn)]);
  };
  frame('cream', S, W, 20, 82, P_BORDER, F + 2);
  frame('frame', G, S, 22, 80, P_DOOR, P_BORDER);
  // P13 glass — NOT a transparent pane. Alpha blending produces colours that
  // are in no palette, so the snap sent them to whatever grey was nearest and
  // the door went dead. The sheet does not draw a pane either: you see the
  // interior directly, with a reflection drawn ON it. So the pane is gone and
  // the reflection is a staircase of small boxes, which is how pixel art draws
  // a diagonal and costs nothing here.
  // The glass reflection is GONE. It was a staircase of small light boxes, and
  // with the door otherwise bare it was the only thing on it; next to real
  // fittings it reads as exactly what the noise pass read as — scattered marks
  // that mean nothing. The reference's own streaks are barely visible, and a
  // sticker on the glass carries the door far better.
  // ---- P14 handle ---------------------------------------------------------
  add('purple', [W - 3.5, F - 4.6, 41], [W - 1, F - 3.2, 63]);
  add('purple', [W - 3, F - 3.2, 42],   [W - 1.5, F - 2.2, 45]);
  add('purple', [W - 3, F - 3.2, 59],   [W - 1.5, F - 2.2, 62]);
  // P16 display — geometry, not a decal. Exactly one, at the centre, at any
  // width: the case a tiling texture fundamentally cannot express. It rides the
  // CROWN's front face, which overhangs the body, so it moves with the cap.
  add('disp',  [-5.8, CF - 0.7, 88.6], [5.8, CF, 92.2]);
  add('lamp',  [-4.2, CF - 0.9, 89.8], [-2.7, CF - 0.6, 91.0]);
  add('digit', [-1.2, CF - 0.9, 89.8], [3.6, CF - 0.6, 91.0]);

  // ---- FITTINGS ------------------------------------------------------------
  // Every one of these is placed where the thing it represents would actually
  // be, which is the whole point: a rating plate goes on the flank at eye
  // height because that is where you read one, hinges go on the edge the door
  // turns on, the biohazard sticker goes on the door of a vaccine fridge. They
  // are quads of fixed WORLD size anchored to a face, so widening the cabinet
  // moves them with their corner and never stretches them.
  //
  // NOTE these go beyond the fridge turnaround, which carries no fittings at
  // all. They come from the prop kit in docs/reference, which is where the
  // style's character lives — the turnaround is a clean orthographic drawing.
  const T = STYLE.tint;
  // Fitting sizes are given in TEXELS and converted, so every decal lands on
  // the same pixel grid as the surfaces and the geometry. Sized in raw world
  // units they were fractions of a texel across — the screws were under one
  // texel wide, which is why they minified to featureless blobs.
  const tx = (n) => n * STYLE.texel;
  const L = -W - EPS, R = W + EPS;        // just proud of each flank
  for (const [x, face] of [[L, 'left'], [R, 'right']]) {
    // Screws at the corners of both flank panels — the one fitting the
    // reference applies as a rule rather than a placement.
    for (const cv of [34, 68]) {
      for (const m of screws(THREE, kit, face, 0, cv, D, 16, x, tx(3), tx(2), T.side)) {
        g.add(m);
      }
    }
  }
  // Rating plate and a paper label, on the left flank only: a real cabinet has
  // one of each, not one per side.
  g.add(decal(THREE, kit, 'ratingPlate', 'left', 1, 70, tx(7), L, T.side));
  g.add(decal(THREE, kit, 'labelHolder', 'left', 1, 34, tx(6), L, T.side));
  // Door: hinges on the side away from the handle, a biohazard sticker low on
  // the glass where one gets stuck.
  for (const z of [30, 72]) {
    g.add(decal(THREE, kit, 'hinge', 'front', -(W - 3.4), z, tx(5), P_DOOR - EPS, T.front));
  }
  // Between two shelves, not across one. At its old size and height it
  // straddled the bottom shelf and read as an object inside the cabinet
  // rather than a sticker on the door.
  g.add(decal(THREE, kit, 'biohazard', 'front', -(G - 6), 47, tx(5), P_DOOR - EPS, T.front));
  // Base block: the switch and thermostat live on the plant, next to the grille.
  g.add(decal(THREE, kit, 'rocker', 'front', W - 6.0, 14, tx(3), P_BASE - EPS, T.front));
  g.add(decal(THREE, kit, 'dialA', 'front', W - 11.5, 14, tx(3), P_BASE - EPS, T.front));
  return g;
}
