// POS TERMINAL — the pharmacy till computer.
//
// THE FOURTH PROP, and the first that is not a cabinet. The three fridges are
// one tall mass with things on the front; this is WIDER THAN IT IS TALL, an
// assembly of five separate masses, and its biggest feature is a recessed dark
// rectangle rather than an opening. So the hollow-carcass recipe never comes up
// and almost nothing carries over except the module itself — which is the point
// of building it.
//
// Built by following docs/BUILDING-A-PROP.txt. Nothing in ../style.js changed
// except eight material families.
//
// MEASURED off docs/style-bible/props/pos_terminal.png (front 617 x 709 px,
// side 542 x 709 px, magenta ground) with tools/authoring/measure.py.
//
// EVERY FRACTION BELOW IS A SHEET FRACTION, not a fraction of the prop. The
// sheet's full width includes the card reader outrigger, which is NOT part of
// the base, so the two are different denominators and mixing them silently
// misplaces everything. px()/py() below convert one to the other, once.
//
//   base, in front-sheet fractions   x 0.005 .. 0.859   (centre 0.432)
//   base, in side-sheet fractions    u 0.002 .. 0.969   (centre 0.4855)
//   so the base is 527 x 524 px — SQUARE IN PLAN, unlike all three fridges
//   overall height / base width      709 / 527 = 1.345
//
//   VERTICAL (z as a fraction of the overall height, 0 at the floor)
//     feet                 0.000 .. 0.023
//     base bottom lip      0.023 .. 0.078
//     base plinth          0.078 .. 0.145
//     deck + keyboard      0.145 .. 0.222
//     rear riser (wedge)   0.145 .. 0.292
//     neck                 0.292 .. 0.362
//     monitor bottom flare 0.344 .. 0.375
//     monitor body         0.375 .. 0.944
//       screen             0.447 .. 0.870
//       power btn / lamp   0.375 .. 0.405
//     monitor top chamfer  0.944 .. 1.000
//       vent slots         0.965 .. 0.985
//     card reader stalk    0.138 .. 0.236
//     card reader head     0.236 .. 0.351
//
//   HORIZONTAL, front sheet (0 at the reference's LEFT edge)
//     monitor              0.034 .. 0.836
//     screen               0.123 .. 0.742   (bezel 0.089 left, 0.094 right)
//     bezel inner ring     0.108 .. 0.757
//     neck                 0.300 .. 0.571
//     power button         0.645 .. 0.699   lamp 0.715 .. 0.733
//     keys                 0.091 .. 0.600   pitch 0.0553, key 0.045
//     printer slot         0.585 .. 0.780   paper 0.614 .. 0.744
//     card reader stalk    0.877 .. 0.935   head 0.820 .. 0.998
//
//   SIDE SHEET (u, 0 at the FRONT)
//     monitor              0.164 .. 0.946   plus a CRT hump to 0.996
//     neck                 0.450 .. 0.820
//     rear riser           0.232 .. 0.956 at its base
//     feet                 0.057 .. 0.159 and 0.830 .. 0.930
import { STYLE, tableBox, decal, screws } from '../style.js';

export const objLo = 0;
export const objHi = 43.0;      // base width 32 x the measured 1.345, set ONCE
                                // at the default width
export const label = 'pos terminal';
// Wide AND deep, so the kit's 0.56 would clip it badly in iso. The card reader
// outrigger pushes the footprint out further on one side than any fridge.
export const aspect = 1.06;

export function build(THREE, MATS, kit, H) {
  const g = new THREE.Group();
  const add = (kind, a, b, opts) => g.add(tableBox(THREE, kind, a, b, MATS, opts));
  const tx = (n) => n * STYLE.texel;
  const T = STYLE.tint;

  // ---- HOW EACH PART BEHAVES WHEN THE PROP RESIZES ------------------------
  //   STRETCH  base, plinth, deck, riser, monitor body, screen, bezel.
  //   ANCHOR   feet, neck, power button, lamp, printer, card reader, keycap
  //            SIZE. A till's keys are the size a finger is, on any till.
  //   REPEAT   keycaps (count follows the deck), vent slots, screws.
  const W = H;                  // BASE half-width — the 100%
  const D = W * 0.994;          // half-depth: square in plan (524/527)
  const TOT = objHi - objLo;
  const z = (f) => f * TOT;

  // SHEET FRACTION -> WORLD. Two different denominators, converted once here.
  // px() also applies the front camera's x mirror (BUILDING-A-PROP 4.3), so
  // fractions read from the LEFT of the reference land on table +x.
  // 0.859, not 0.854. The base's own left edge reads 0.005 in the band where
  // the bottom lip is inset and 0.000 at the plinth; taking the first made the
  // denominator 0.6% small, which put EVERY hand-converted constant 0.6% out
  // and showed in the silhouette overlay as a uniform 0.007 shift on both
  // edges of the monitor at once. A width error and a centre error together
  // look like a part that has slid, and --bands scores it perfect.
  const SW = 0.859, CXF = 0.4295;     // base width / centre, FRONT sheet
  const SD = 0.967, CYF = 0.4855;     // base depth / centre, SIDE sheet
  const px = (f) => -((f - CXF) * 2 * W / SW);
  const py = (f) => (f - CYF) * 2 * D / SD;
  const wx = (df) => df * 2 * W / SW;  // a front-sheet SIZE -> world units
  const wy = (df) => df * 2 * D / SD;  // a side-sheet SIZE -> world units

  // ORDERED PAIRS, ALWAYS. px() is mirrored, so px(smaller) > px(larger) and
  // every box written straight from the measurements comes out back to front.
  // tableBox now warns and sorts, but a warning per box is not a design — these
  // three helpers mean the coordinates are right at the call site instead.
  const XR = (a, b) => { const p = px(a), q = px(b); return p < q ? [p, q] : [q, p]; };
  const YR = (a, b) => { const p = py(a), q = py(b); return p < q ? [p, q] : [q, p]; };
  // one box straight off the sheet: x-range, y-range, z-range, all as fractions
  const box = (kind, xa, xb, ya, yb, za, zb, opts) => {
    const [x1, x2] = XR(xa, xb), [y1, y2] = YR(ya, yb);
    add(kind, [x1, y1, z(za)], [x2, y2, z(zb)], opts);
  };

  // ---- ANCHOR CONSTANTS ---------------------------------------------------
  // FIXED WORLD SIZES, converted from the sheet ONCE at the default width.
  //
  // wx() and wy() scale with W, so they may only size things that genuinely
  // STRETCH — the case, the base, the screen. Every small bolted-on part sized
  // through wx() grows with the prop, and compare.py --margins caught exactly
  // that: 56% of the left edge strip differing at ?w=28, because the keycaps
  // were written as wx(0.045). A keycap is the size a finger is, on any till.
  // DERIVED FROM THE SHEET FRACTION, NOT HAND-CONVERTED. U is world units per
  // unit of sheet fraction AT THE DEFAULT WIDTH — note the literal 32, not
  // 2 * W, which is what keeps these fixed while the prop resizes. Writing the
  // arithmetic out means the measured fraction stays visible in the source and
  // cannot drift from SW when SW is re-measured, which is exactly what happened
  // when they were typed as decimals.
  const U = 32 / SW;
  const KEY_P = 0.0553 * U, KEY_W = 0.045 * U;      // keycap pitch and width
  const VENT_P = 0.0255 * U, VENT_W = 0.011 * U;    // slot pitch and width
  const BTN_A = 0.137 * U, BTN_W = 0.054 * U;       // in from the monitor edge
  const LAMP_W = 0.018 * U;
  const PRN_B = 0.284 * U;                          // in from the base edge
  const KEY_IN = 0.086 * U;                         // first key, in from the edge
  const KEY_DARK = 5;                               // function block, fixed count
  const MHW = 0.401 * U;                            // monitor half-width
  const MCX = -(0.4355 - CXF) * U;                  // its centre, off the base's

  // THE MONITOR IS NOT CENTRED ON THE BASE. The reference's monitor spans
  // x 0.034..0.836 (centre 0.4355) against a base centred at 0.432 — a 0.12
  // unit offset, trivially small and trivially free to honour, which the
  // silhouette overlay picks up as a 0.007 shift on both the neck and the case.
  // ---- named planes -------------------------------------------------------
  const F = -D;                 // the base's front face
  const EPS = 0.08;

  // BEVELS PER AXIS. Moulded plastic, so softer than the steel cabinets: the
  // case is rounded on the verticals and slightly on the horizontals, the deck
  // is crisp where it meets the floor, and everything recessed is flat.
  const CASE = { bevel: [1.3, 0.7, 1.3] };
  const CRISP = { bevel: [0.9, 0, 0.9] };

  // ---- feet ---------------------------------------------------------------
  // ANCHOR: measured 0.086 of the sheet across (3.2 units) and set 1.6 units in
  // from the base's corners. Four of them; the front view shows two.
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    const x1 = sx > 0 ? W - 4.8 : -W + 1.6, x2 = sx > 0 ? W - 1.6 : -W + 4.8;
    const y1 = sy > 0 ? D - 5.0 : -D + 1.8, y2 = sy > 0 ? D - 1.8 : -(D - 5.0);
    add('posFoot', [x1, y1, 0], [x2, y2, z(0.019)], { bevel: 0.45 });
  }

  // ---- base ---------------------------------------------------------------
  // REBUILT FROM THE SIDE PROFILE, which had never been compared. The front
  // view scored 98.65% IoU while the side scored 94.16%, and the whole deficit
  // was here: the reference's base is a KEYBOARD WEDGE whose front edge climbs
  // steadily from u 0.013 at z 0.13 to u 0.373 at z 0.23, and whose back drops
  // from u 0.969 to 0.819 above z 0.29. It was built as one flat deck and one
  // symmetric taper, which put a solid block of material across the whole rear
  // of the prop that the reference does not have.
  //
  //   REFERENCE SIDE PROFILE (u = depth fraction, 0 at the FRONT)
  //     z 0.06 .. 0.12   0.000 .. 0.969     full
  //     z 0.13           0.013 .. 0.969
  //     z 0.15           0.042 .. 0.969
  //     z 0.17           0.061 .. 0.969     end of the plinth's top chamfer
  //     z 0.19           0.161 .. 0.969     front-most is now a KEY
  //     z 0.21           0.229 .. 0.958
  //     z 0.22           0.275..0.327 + 0.373..0.919   a key, then the riser
  //     z 0.25           0.373 .. 0.919
  //     z 0.27           0.419 .. 0.906
  //     z 0.29           0.445 .. 0.819
  //     z 0.33           0.498 .. 0.819
  const uy = (u) => py(u);            // a side-sheet fraction -> world y

  // the bottom lip, inset all round so the plinth above reads as overhanging it
  // ASYMMETRIC, because the reference is: at z 0.030 it reads 0.023..0.846
  // against a deck of 0.000..0.859, so the lip is inset 0.86 units on the
  // reference's LEFT (table +x) and 0.50 on its right. And it starts at z 0.018
  // — the feet stop there, and a lip starting at 0.023 left a 1105-pixel band
  // of bare floor, the largest single disagreement on the front elevation.
  add('posCase', [-(W - 0.50), -(D - 0.78), z(0.019)], [W - 0.86, D - 0.78, z(0.056)],
      CRISP);

  // THE PLINTH, AND THE POINT OF PER-FACE BEVELS. The reference's base front is
  // a dead vertical face at u 0.000 from z 0.06 to 0.13, and only then chamfers
  // back to u 0.061 by z 0.17. One bevel number per AXIS cuts both ends of that
  // axis, so a 1.3-unit depth bevel pushed the ENTIRE front face back 1.3 units
  // — which is what "the bevel is uniform" looks like when you measure it.
  //
  //   [x-, x+, bottom, top, front, back]
  //
  // Bottom 0 and front 2.0 gives exactly the reference's profile: full depth at
  // the floor, a 2.0-unit chamfer running up to the deck. The chamfer between
  // two faces is set by BOTH their insets, so the top-front chamfer is 2.0 deep
  // and 1.7 tall and the bottom-front edge stays sharp.
  // THE PLINTH DOES OVERHANG in the reference — the base measures 0.846 at the
  // lip, 0.867 at the plinth and 0.859 at the deck — and it is left FLUSH here
  // anyway. Making it 0.3 units proud fixed a 381-pixel strip on each side and
  // cost 1821 pixels somewhere else entirely: the plinth then set the object's
  // BOUNDING BOX, the overlay aligns on that box, and the whole monitor
  // measured 0.006 of the width to one side. An error at the extreme of a
  // silhouette is worth more than its own size, because everything else is
  // measured from it.
  // AND IT OVERHANGS ON ONE SIDE ONLY. The reference's plinth reads 0.000..0.867
  // against a deck of 0.010..0.857, so it is proud on both — but its LEFT edge
  // is the object's bounding box, and widening that shifted every measurement
  // of every other part (1821 pixels lost to gain 381). The reference's RIGHT
  // side is not the bounding box, the card reader is, so the overhang can be
  // honoured there for free. An asymmetry that exists only because of how the
  // comparison is normalised, and worth saying so rather than hiding.
  add('posCase', [-(W + 0.30), -D, z(0.056)], [W, D, z(0.175)],
      // The reference's front profile is not a straight chamfer — 0.013 at
      // z 0.13, 0.042 at 0.15, 0.061 at 0.17, decelerating — so no single
      // linear chamfer fits it. Pushed to the clamp (2.3/2.6) it matched that
      // one band better and cost more on the front elevation than it gained on
      // the side, so 1.7/2.0 stands and the deviation is here in writing.
      // x bevel 0.4, not 1.3. A 1.3 chamfer on the vertical edges combines
      // with the 1.7 top bevel into a chamfer across the top corners, and the
      // reference's plinth holds full width right up to its top: 0.010..0.857
      // at z 0.150 against 0.000..0.867 lower down.
      // top 2.2 / front 2.4. The chamfer has to START lower to follow the
      // reference's slope: at 1.7/2.0 it began at z 0.135 and read u 0.023
      // where the reference reads 0.042. Safe now that the x bevel is 0.4 —
      // at 1.3 a chamfer this deep also cut the top corners on the front view.
      { bevel: [0.4, 0.4, 0, 2.2, 2.4, 0.4] });

  // THE RISER, in three steps rather than one symmetric taper. The reference's
  // wedge recedes far more at the FRONT than at the back and taperZ can only
  // narrow both ends equally; three boxes following the measured profile cost
  // 24 triangles more and are the difference between a wedge and a block.
  // Insets from the base's own edges are FIXED world units (see the resize
  // note above), and each step is crisp underneath and soft on top so they
  // stack without a visible rim at every joint.
  // NO TOP BEVEL ON A STACKED STEP. A top chamfer plus an x chamfer cuts the
  // corners off every step, and since each step's top is the next one's floor
  // it also cut a groove at every joint — the riser measured 0.025 of the width
  // narrow on BOTH sides at z 0.29. Soft vertical corners, crisp everywhere
  // else; the wedge's slope comes from the steps, not from their chamfers.
  const STEP = { bevel: [0.8, 0.8, 0, 0, 0, 0] };
  // EACH STEP TAPERS WITHIN ITSELF. Measured at its own bottom AND top the
  // riser draws in continuously — insets 0.021/0.008 of the width at z 0.175
  // and 0.049/0.044 by z 0.222 — so a step with vertical sides is up to 1.0
  // unit wide across the top half of its own band.
  add('posCase', [-(W - 0.30), uy(0.330), z(0.175)], [W - 0.78, uy(0.955), z(0.222)],
      { ...STEP, taperX: 1.0 });
  add('posCase', [-(W - 1.70), uy(0.373), z(0.222)], [W - 2.00, uy(0.919), z(0.268)],
      { ...STEP, taperX: 0.6 });
  // MEASURED at its own bottom, not its top: the reference reads insets 0.088
  // and 0.076 at z 0.271 and 0.109 and 0.099 by z 0.290, so the step tapers
  // within its own height. Built at the TOP figures it was a full 0.8 units
  // narrow across the whole band.
  add('posCase', [-(W - 2.83), uy(0.430), z(0.268)], [W - 3.28, uy(0.880), z(0.292)],
      { ...STEP, taperX: 0.8 });

  // ---- neck ---------------------------------------------------------------
  // Crisp. CASE chamfered the neck's bottom into the base, which the reference
  // draws as a straight 0.300..0.571 column all the way down.
  // Its front is at u 0.470 and draws back to 0.498 by z 0.33, not a straight
  // 0.450 column: 911 pixels of render-only material stood in front of it.
  add('posCase', [MCX - 0.1355 * U, uy(0.475), z(0.292)],
                 [MCX + 0.1355 * U, uy(0.820), z(0.366)],
      { bevel: [0.9, 0, 0.9], taperZ: 0.7 });

  // ---- monitor (ANCHOR — the whole assembly) ------------------------------
  // A MONITOR IS A BOUGHT-IN PART. Section 6's rule: could you buy it on its
  // own, in a box, in one size? Then it is ANCHOR. Written as sheet fractions
  // the monitor grew with the till, which is not what widening a counter unit
  // does — you get a longer desk and more keys, not a bigger screen. So the
  // whole assembly below is FIXED WORLD SIZE, centred on the base, converted
  // once from the sheet at the default width; only the base stretches under it.
  //
  // The consequence is worth naming: after this change the edge-strip resize
  // test cannot validate the monitor, because it is anchored to the CENTRE and
  // the strips are cut from the edges. compare.py --centre exists for that.
  // MY0 IS THE BODY'S FRONT, AND IT IS BEHIND THE FLARE'S. The side profile
  // reads u 0.164 at z 0.39 and 0.179 from z 0.44 up — the tube's bezel stands
  // proud at the bottom and the case runs back above it, which is what a CRT
  // does. Built at 0.164 for the whole height the body was forward of its own
  // flare, and the overlay showed it as a tall blue strip down the front edge.
  const MY0 = -10.09, MY1 = 15.15;    // its front and back faces
  const BODY_F = MY0 + 0.15;          // the CASE sits behind the bezel
  const mb = (kind, hx, y0, y1, za, zb, o) =>
    add(kind, [MCX - hx, y0, z(za)], [MCX + hx, y1, z(zb)], o);

  // The bottom FLARES, and it is CONCAVE: 12.63 half-width at z 0.344, still
  // 13.02 at z 0.362, and 15.03 by z 0.375 — most of the widening in the last
  // third. A negative taper is a flare, the one direction the fridges never
  // needed. One linear step put it 6% wide across the middle of the band.
  // Down to z 0.336, not 0.344: the reference holds the flare's bottom width
  // for one more band before the neck takes over.
  // THE UNDERSIDE IS NOT SOLID. At z 0.344 the reference reads TWO runs —
  // 0.251..0.430 and 0.513..0.819 — a front lip and the neck, with the tube's
  // underside recessed between them. Built as one slab it filled that gap and
  // ran 0.087 of the depth too far back, the worst single error on the prop.
  mb('posCase', 0.337 * U, uy(0.251), uy(0.430), 0.336, 0.360,
     { bevel: 0, taperX: -0.0105 * U });
  // Its front runs from u 0.230 to 0.179 over its own height — the reference
  // reads 0.245 at z 0.36 and 0.179 at 0.37 — so a flat 0.170 stood 287 pixels
  // in front of the reference's outline.
  mb('posCase', 0.3475 * U, uy(0.230), uy(0.907), 0.360, 0.375,
     { bevel: 0, taperX: -0.054 * U, taperZ: -1.7 });
  // and the bezel's bottom rim, which stands proud of the case above it: the
  // profile reads u 0.164 up to z 0.41 and 0.179 from z 0.44 on.
  mb('posCase', MHW - 0.6, uy(0.164), MY0, 0.375, 0.415, { bevel: [0.8, 0.8, 0, 0.8, 0, 0] });
  // NO BOTTOM CHAMFER. CASE bevels y as well, and a y-bevel cuts the top AND
  // the bottom — so the body pulled in just above the flare and the two met at
  // a waist. Visible in the overlay as a notch, invisible at a glance.
  // The rear steps back once. The reference reads 0.179..0.902 at z 0.37 and
  // 0.179..0.945 at z 0.39 — the tube's shoulder — so a body that is full depth
  // from 0.375 puts 480 pixels behind the reference's outline.
  mb('posCase', MHW, BODY_F, uy(0.905), 0.375, 0.390, { bevel: [1.3, 0, 1.3] });
  mb('posCase', MHW, BODY_F, MY1, 0.390, 0.944, { bevel: [1.3, 0, 1.3] });
  // The CRT hump on the back. Only the side view has it, and it is most of what
  // makes the silhouette read as a monitor rather than a box.
  mb('posCase', 0.345 * U, MY1, 16.79, 0.450, 0.884, { bevel: [1.6, 1.6, 0] });

  // The top chamfer, MEASURED in four steps and built as frusta — the same
  // rounding as a fridge shoulder, a different profile. Written out rather than
  // handed to capProfile() because the monitor is not centred in DEPTH (it sits
  // 2.3 units back) and capProfile centres on the origin.
  const CAP = [[0.944, 0], [0.962, 0.021 * U], [0.979, 0.042 * U], [1.000, 0.063 * U]];
  for (let i = 0; i < CAP.length - 1; i++) {
    const [z0, i0] = CAP[i], [z1, i1] = CAP[i + 1];
    mb('posFlat', MHW - i0, BODY_F + i0 * 0.25, MY1 - i0 * 0.55, z0, z1,
       { bevel: 0, taperX: i1 - i0, taperZ: (i1 - i0) * 0.40 });
  }

  // ---- the screen ---------------------------------------------------------
  // A dark rectangle inside a warm tan ring. The ring is the piece that makes
  // it read as a CRT: without it the dark panel sits on the case like a sticker.
  //
  // THE RING IS FOUR BARS, NOT A PANEL, and everything here stands PROUD of the
  // case. Written as one solid box at the case's own front plane, the ring was
  // inside the case and the screen was inside the ring — the buried-part check
  // reported both before this was ever rendered. Same rule as a fridge cavity:
  // a hollow is bars or panels, never a block, and a recess is built proud.
  // BARELY PROUD. A recess has to be built proud here, but 0.5 units of it is
  // 0.017 of the depth and the side view has no such lip — a 1920-pixel strip
  // down the monitor's whole front, the largest single error on that view.
  // 0.15 is enough for the ring to read in front of the screen and small
  // enough to disappear into the outline in profile.
  // MY0 IS THE BEZEL'S PLANE, and the case sits BEHIND it. A recess has to be
  // built proud, so the ring is always in front of the body — the only question
  // is which of the two the reference's outline is, and it is the ring. Setting
  // the body back 0.15 puts the ring exactly on the measured u 0.179 instead of
  // 0.0047 of the depth in front of it, which was a 1129-pixel strip down the
  // monitor's whole height.
  const RY = [MY0, MY0 + 0.40];           // the ring, ON the measured front
  const SY = [MY0 + 0.05, MY0 + 0.25];    // the screen, sunk inside it
  const RHW = 0.3245 * U, RT = 0.015 * U; // ring half-width and bar thickness
  const bar = (x1, x2, za, zb) =>
    add('posTrim', [x1, RY[0], z(za)], [x2, RY[1], z(zb)], { bevel: 0 });
  bar(-RHW, -RHW + RT, 0.432, 0.885);
  bar(RHW - RT, RHW, 0.432, 0.885);
  bar(-RHW, RHW, 0.432, 0.447);
  bar(-RHW, RHW, 0.870, 0.885);
  add('posScreen', [MCX - 0.3095 * U, SY[0], z(0.447)],
                   [MCX + 0.3095 * U, SY[1], z(0.870)], { bevel: 0 });
  // ONE soft glare, two thin blocks stepped across. A square reads as a sticker
  // stuck to the tube. A stepped diagonal is not worth attempting on glass you
  // see THROUGH (BUILDING-A-PROP 8.10) — but a CRT is opaque, so this is simply
  // a mark on a surface, and it stands proud of the screen like any other mark.
  for (const [ga, gb, za, zb] of [[0.2815, 0.2815 + 0.028, 0.760, 0.845],
                                  [0.2615, 0.2815, 0.795, 0.862]]) {
    add('posGlare', [MCX + ga * U, SY[0] - 0.12, z(za)],
                    [MCX + gb * U, SY[0] - 0.04, z(zb)],
        { bevel: 0 });
  }

  // ---- power button and lamp (ANCHOR) -------------------------------------
  // ANCHORED TO THE MONITOR'S OWN EDGE, fixed distance and fixed size. The
  // monitor stretches; the switch bolted to it does not.
  const monR = -MHW;                  // the monitor's -x edge, now fixed
  const by1 = MY0 - 0.35, by2 = MY0 + 0.1;
  add('posScreen', [monR + BTN_A, by1, z(0.375)],
                   [monR + BTN_A + BTN_W, by2, z(0.405)], { bevel: 0.25 });
  add('digit', [monR + BTN_A + BTN_W + 0.9, by1, z(0.385)],
               [monR + BTN_A + BTN_W + 0.9 + LAMP_W, by2, z(0.405)], { bevel: 0 });

  // ---- vent slots (REPEAT) ------------------------------------------------
  // MEASURED at a pitch of 0.0255 of the sheet — 0.96 world units — running
  // x 0.073 to 0.79. The count follows the case; the slot never changes size.
  const VX = 0.3585 * U;
  for (let s = MCX - VX; s < MCX + VX - VENT_W; s += VENT_P) {
    add('posScreen', [s, MY0 - 0.1, z(0.965)], [s + VENT_W, MY0 + 0.3, z(0.985)],
        { bevel: 0 });
  }

  // ---- keyboard (REPEAT across, ANCHORED key size) ------------------------
  // MEASURED: pitch 0.0553 of the sheet, keycap 0.045, from x 0.091. A key is
  // the size a finger is on every till ever made, so the SIZE is fixed and only
  // the COUNT follows the deck. Two rows, the back one sitting a step higher —
  // which is what puts two visible rows in a dead-on front elevation.
  // START AT A FIXED INSET FROM THE BASE'S LEFT EDGE and run until the printer
  // gets in the way. That is REPEAT done properly: the key, the pitch and both
  // margins are fixed, and only the COUNT follows the deck.
  const kx2 = W - KEY_IN;
  const KN = Math.max(3, Math.floor((kx2 - (-W + PRN_B + 1.6)) / KEY_P));
  // A small step under the BACK row. Two rows at the same height are one row in
  // a dead-on front elevation — the reference shows two because its deck slopes,
  // and this is the cheapest honest way to get the same reading.
  //
  // A KEYCAP IS ROUGHLY SQUARE IN PLAN. Written 3.9 units deep against a 1.7
  // unit width the keys came out as tall fins standing on the deck — correct
  // from the front, absurd from anywhere else. The reference's own side view
  // puts the whole keyboard inside 3.4 units of depth; two rows of 2.5 is the
  // nearest honest reading of that, and it is where the deviation is: its deck
  // slopes and ours steps, so ours needs slightly more room.
  // DEPTH IS ANCHORED TOO. D scales with W here, so a key placed at a depth
  // FRACTION grows in the other direction just as surely — the same mistake,
  // and the edge-strip check cannot see it because it never leaves the front
  // elevation. Offsets are from the base's front face.
  // THREE TIERS, stepping UP and BACK, because that is what the side view
  // shows: the front-most point of the whole prop at z 0.19 is a key at
  // u 0.161, at z 0.21 a key at 0.229, and at z 0.22 a key at 0.275..0.327 with
  // a gap behind it before the riser starts at 0.373. Two flat rows could not
  // produce that profile at any height.
  // A FRONT LIP ON THE DECK. The reference carries material at u 0.083..0.161
  // up to z 0.192 — the deck's own front edge, standing above the plinth's top
  // chamfer and in front of the first key row. Without it there is a 282-pixel
  // notch between the chamfer and the keys.
  add('posCase', [kx2 - KN * KEY_P - 0.7, uy(0.105), z(0.175)],
                 [kx2 + 0.7, uy(0.205), z(0.190)], { bevel: [0.8, 0.8, 0, 0.6, 0.8, 0] });
  const wedge = { bevel: [0.8, 0.8, 0, 0.8, 1.0, 0.6] };
  add('posCase', [kx2 - KN * KEY_P - 0.7, uy(0.205), z(0.175)],
                 [kx2 + 0.7, uy(0.332), z(0.196)], wedge);
  const ROW = [
    { u0: 0.161, u1: 0.213, lo: 0.175, hi: 0.205 },
    { u0: 0.216, u1: 0.272, lo: 0.188, hi: 0.218 },
    { u0: 0.268, u1: 0.324, lo: 0.196, hi: 0.226 },
  ];
  for (const r of ROW) {
    const ky1 = uy(r.u0), ky2 = uy(r.u1);
    for (let k = 0; k < KN; k++) {
      const s = kx2 - (k + 1) * KEY_P;
      // The reference's right-hand group is darker — a numeric or function
      // block, which every till has. Indexed by POSITION, not random, so two
      // renders of the same model are comparable and a wider deck extends the
      // pale block rather than reshuffling every key.
      // MEASURED: pale to reference x 0.35, darker from 0.36 to 0.60. px() is
      // mirrored, so kx1 is the reference's RIGHT-hand end — the comparison has
      // to run the other way, and written the obvious way round it put the
      // function block on the wrong side of the keyboard.
      // The dark block is the numeric/function keypad: a FIXED five keys at the
      // far end, not a fraction of the keyboard, or a wider till would get a
      // wider function block.
      const dark = k < KEY_DARK;
      add(dark ? 'posKeyDk' : 'posKey', [s, ky1, z(r.lo)], [s + KEY_W, ky2, z(r.hi)],
          { bevel: 0.18 });
    }
  }

  // ---- printer (ANCHOR) ---------------------------------------------------
  // It is on the base's FRONT FACE, not on top of the deck: the reference has
  // the slot at z 0.168..0.190 with the paper hanging BELOW it to z 0.128,
  // which only happens on a vertical face. Built proud of that face, and the
  // paper proud of the housing, because the base is solid — the first version
  // put the paper at a depth fraction that landed inside the plinth and the
  // check reported it.
  const fbox = (kind, xa, xb, y0, y1, za, zb, o) => {
    const [x1, x2] = XR(xa, xb);
    add(kind, [x1, F - y1, z(za)], [x2, F - y0, z(zb)], o);
  };
  // ANCHORED in x to the base's -x edge, in y to its front face, and fixed in
  // size. A receipt printer is a bought-in module; it does not get wider when
  // the till does.
  const R = -W;                 // the base's -x edge (reference RIGHT)
  const pbox = (kind, xa, xb, y0, y1, za, zb, o) =>
    add(kind, [R + xa, F - y1, z(za)], [R + xb, F - y0, z(zb)], o);
  // FLUSH, NOT PROUD. At 0.45 units proud the housing became the front-most
  // point of the whole prop, which shifted the side view's bounding box and so
  // shifted every depth measurement of every other part by 0.017 of the depth.
  // The reference's printer is a recess in the base's front face, not a box on
  // it, so only the paper leaves the silhouette.
  // AND IT SITS IN THE CHAMFER. The base's front face is chamfered back over
  // z 0.135..0.175, so a printer at the nominal front plane stands proud of it
  // — the side profile read u 0.004 where the reference reads 0.055. Set back
  // to the middle of the chamfer.
  pbox('posCase', 0.069 * U, PRN_B, -1.30, -1.05, 0.140, 0.200, { bevel: 0.4 });
  pbox('posScreen', 0.079 * U, 0.274 * U, -1.10, -0.85, 0.168, 0.190, { bevel: 0 });
  // The tail leaves the silhouette, which is what says the thing is loaded.
  // The tail lives in the chamfer band too. Recessed to the printer's own plane
  // it was inside the plinth and drew nothing; brought forward to the nominal
  // front face it would stand proud of the base and set the side view's
  // bounding box, which is the fault it was moved back to fix. z 0.140..0.172
  // is where the chamfer has opened far enough for it to show.
  pbox('boxPale', 0.115 * U, 0.245 * U, -1.05, -0.70, 0.140, 0.172, { bevel: 0 });
  pbox('posTrim', 0.115 * U, 0.245 * U, -0.80, -0.62, 0.140, 0.148, { bevel: 0 });

  // ---- card reader on its stalk (ANCHOR) ----------------------------------
  // An outrigger, and the reason this prop's sheet is wider than its base. It
  // is a bought-in part bolted to the side of the till: fixed size, fixed
  // distance from the base's right edge, never a fraction of anything.
  // The stalk runs all the way DOWN TO THE BASE, not to some point in mid-air.
  // Started at z 0.138 it left the reference's outline at z 0.078..0.138
  // unaccounted for, and compare.py --bands caught it as a 7.6% shortfall at
  // z 0.083 — a band nobody would ever have looked at twice.
  // ANCHORED the same way, and it is the clearest case on the prop: this is a
  // separate bought-in terminal bolted to the side. Offsets are from the base's
  // -x edge (negative = outboard of it) and from its BACK face.
  const BK = D;
  const rbox = (kind, xa, xb, ya, yb, za, zb, o) =>
    add(kind, [R + xa, BK - yb, z(za)], [R + xb, BK - ya, z(zb)], o);
  // WIDER, AND DOWN TO THE PLINTH. Measured 0.874..0.940 at z 0.23 and
  // 0.875..0.935 at z 0.15 — 2.4 units, against the 3.0 it was built at, and
  // fused with the base below z 0.14 rather than starting in mid-air at 0.078.
  // FROM z 0.090, NOT THE FLOOR, and FUSED with the plinth rather than standing
  // beside it. The reference reads 0.023..0.846 at z 0.04 (no stalk at all) and
  // one unbroken 0.000..0.935 from z 0.09 — so below 0.09 there is nothing, and
  // above it the stalk's foot runs into the base with no gap. Built from z 0.02
  // as a separate column it put 1651 pixels of render-only material exactly
  // where the reference has bare ground.
  rbox('posCase', -3.00, 0.40, 2.53, 4.31, 0.075, 0.150, { bevel: 0.5 });
  rbox('posCase', -3.02, -0.56, 2.74, 4.15, 0.150, 0.245, { bevel: 0.5 });
  // z 0.236..0.351, not 0.330. A plain transcription slip from the measurement
  // block at the top of this file, and the overlay found it as a red band where
  // the reference's reader head stands and ours does not.
  // IT IS TILTED. The front view puts the head at z 0.236..0.351, but the side
  // view shows it reaching u 0.919 at z 0.23 and nothing beyond 0.819 by z 0.29
  // — a reader angled back towards the operator. Two steps say that; one box
  // says a slab, and put a solid block across the rear of the side silhouette.
  // Top bevels cut back to 0.4: at 1.0 they chamfered the head's own top
  // corners, which is 155 pixels of reference the render simply does not reach.
  // And it starts at z 0.231, which is where the reference's does.
  // Tapered in DEPTH as it rises: the reference reads 0.919 at z 0.23 and only
  // 0.819 by z 0.29, which is the tilt seen edge-on.
  rbox('posCase', -5.20, 1.46, 1.78, 5.56, 0.231, 0.290,
       { bevel: [1.3, 1.3, 0, 0.4, 1.0, 1.0], taperZ: 1.6 });
  rbox('posCase', -4.95, 1.46, 4.90, 5.56, 0.290, 0.351,
       { bevel: [1.3, 1.3, 0, 0.4, 1.0, 1.0] });
  rbox('posRead', -4.61, 0.86, 5.49, 5.72, 0.252, 0.318, { bevel: 0 });
  rbox('posTrim', -1.53, 0.53, 5.79, 5.92, 0.258, 0.268, { bevel: 0 });
  // its own little keypad, three pips, so it reads as a reader and not a box
  for (let k = 0; k < 3; k++) {
    rbox('posKey', -2.20 - 0.974 * k, -1.53 - 0.974 * k, 5.63, 5.79,
         0.258, 0.272, { bevel: 0 });
  }

  // ---- screws (the style bible's one RULE, at a fixed inset) --------------
  for (const sx of [-1, 1]) {
    g.add(...screws(THREE, kit, sx > 0 ? 'right' : 'left',
                    0, z(0.111), D - 1.0, z(0.033),
                    sx * (W + EPS), 2.2, 1.0, T.side));
  }
  return g;
}
