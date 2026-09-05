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
  const SW = 0.854, CXF = 0.432;      // base width / centre, FRONT sheet
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
  const KEY_P = 2.07, KEY_W = 1.69;                 // keycap pitch and width
  const VENT_P = 0.96, VENT_W = 0.41;               // slot pitch and width
  const BTN_A = 5.13, BTN_W = 2.02, LAMP_W = 0.67;  // in from the monitor edge
  const PRN_B = 10.64;                              // in from the base edge
  const KEY_IN = 3.22;                              // first key, in from the edge
  const KEY_DARK = 5;                               // function block, fixed count

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
    add('posFoot', [x1, y1, 0], [x2, y2, z(0.023)], { bevel: 0.45 });
  }

  // ---- base ---------------------------------------------------------------
  // bottom lip, inset all round so the plinth above reads as overhanging it
  add('posCase', [-(W - 0.6), -(D - 0.6), z(0.023)], [W - 0.6, D - 0.6, z(0.078)],
      CRISP);
  add('posCase', [-W, -D, z(0.078)], [W, D, z(0.145)], CASE);

  // THE WEDGE. The side view's top edge runs from u 0.002 at z 0.13 back to
  // u 0.232 at z 0.214 and on to u 0.44 by z 0.29 — a keyboard deck sloping up
  // to a riser that carries the monitor. Built as a low deck plus one tapered
  // riser rather than as a true slope, because tableBox has no slope and three
  // stacked steps would read as steps. The taper is symmetric and the real
  // wedge recedes about 2 units more at the front than at the back; at 0.05 of
  // the depth that is under the outline width, and it is a deliberate
  // simplification rather than a measurement.
  // NO SEPARATE DECK BOX. There was one, z 0.145..0.180, and it swallowed the
  // bottom 40% of every keycap — the keys were sitting IN the deck rather than
  // ON it, which in the front view read as a row of tan lozenges rather than as
  // a keyboard. The plinth's top face at z 0.145 IS the deck; the keys sit on
  // it and the riser rises from it.
  // TWO STAGES, because the reference holds full width to z 0.214 and only then
  // draws in. Tapered from z 0.145 the whole way, the base was 9% narrow at
  // z 0.194 — which compare.py --bands reported and which reads, if you look at
  // it at all, as "the base is a bit small".
  // BEHIND THE KEYBOARD ONLY. Spanning the full depth it enclosed the whole
  // keyboard — ten keys and their step, all drawing nothing.
  //
  // INSETS AND TAPERS ARE FIXED, not fractions. The riser is part of the base
  // and its OVERALL size stretches with it, but the moulding step at its edge
  // is a fixed 0.7 units on any size of till. Written through px() the step
  // grew from 0.71 to 1.24 units at ?w=28 — 53% of the left edge strip,
  // reported by compare.py --margins, and completely invisible by eye.
  add('posCase', [-(W - 0.49), -7.90, z(0.145)], [W - 0.71, D - 0.14, z(0.214)],
      CRISP);
  add('posCase', [-(W - 0.90), -8.34, z(0.214)], [W - 1.09, D - 0.43, z(0.292)],
      { ...CRISP, taperX: 2.81, taperZ: 4.93 });

  // ---- neck ---------------------------------------------------------------
  add('posCase', [-5.08, -1.17, z(0.292)], [5.08, 11.00, z(0.366)], CASE);

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
  const MHW = 15.03;                  // monitor half-width
  const MY0 = -10.57, MY1 = 15.15;    // its front and back faces
  const mb = (kind, hx, y0, y1, za, zb, o) =>
    add(kind, [-hx, y0, z(za)], [hx, y1, z(zb)], o);

  // The bottom FLARES, and it is CONCAVE: 12.63 half-width at z 0.344, still
  // 13.02 at z 0.362, and 15.03 by z 0.375 — most of the widening in the last
  // third. A negative taper is a flare, the one direction the fridges never
  // needed. One linear step put it 6% wide across the middle of the band.
  mb('posCase', 12.63, -10.21, 13.70, 0.344, 0.362,
     { bevel: 0, taperX: -0.39, taperZ: -0.16 });
  mb('posCase', 13.02, -10.38, 13.86, 0.362, 0.375,
     { bevel: 0, taperX: -2.02, taperZ: -0.72 });
  mb('posCase', MHW, MY0, MY1, 0.375, 0.944, CASE);
  // The CRT hump on the back. Only the side view has it, and it is most of what
  // makes the silhouette read as a monitor rather than a box.
  mb('posCase', 12.93, MY1, 16.79, 0.450, 0.884, { bevel: [1.6, 1.6, 0] });

  // The top chamfer, MEASURED in four steps and built as frusta — the same
  // rounding as a fridge shoulder, a different profile. Written out rather than
  // handed to capProfile() because the monitor is not centred in DEPTH (it sits
  // 2.3 units back) and capProfile centres on the origin.
  const CAP = [[0.944, 0.00], [0.962, 0.79], [0.979, 1.57], [1.000, 2.36]];
  for (let i = 0; i < CAP.length - 1; i++) {
    const [z0, i0] = CAP[i], [z1, i1] = CAP[i + 1];
    mb('posFlat', MHW - i0, MY0 + i0 * 0.55, MY1 - i0 * 0.55, z0, z1,
       { bevel: 0, taperX: i1 - i0, taperZ: (i1 - i0) * 0.55 });
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
  const RY = [MY0 - 0.5, MY0 - 0.1];      // the ring's own plane
  const SY = [MY0 - 0.35, MY0 - 0.15];    // the screen, sunk inside it
  const RHW = 12.16, RT = 0.56;           // ring half-width and bar thickness
  const bar = (x1, x2, za, zb) =>
    add('posTrim', [x1, RY[0], z(za)], [x2, RY[1], z(zb)], { bevel: 0 });
  bar(-RHW, -RHW + RT, 0.432, 0.885);
  bar(RHW - RT, RHW, 0.432, 0.885);
  bar(-RHW, RHW, 0.432, 0.447);
  bar(-RHW, RHW, 0.870, 0.885);
  add('posScreen', [-11.60, SY[0], z(0.447)], [11.60, SY[1], z(0.870)], { bevel: 0 });
  // ONE soft glare, two thin blocks stepped across. A square reads as a sticker
  // stuck to the tube. A stepped diagonal is not worth attempting on glass you
  // see THROUGH (BUILDING-A-PROP 8.10) — but a CRT is opaque, so this is simply
  // a mark on a surface, and it stands proud of the screen like any other mark.
  for (const [ga, gb, za, zb] of [[9.59, 10.64, 0.760, 0.845],
                                  [8.84, 9.59, 0.795, 0.862]]) {
    add('posGlare', [ga, SY[0] - 0.12, z(za)], [gb, SY[0] - 0.04, z(zb)],
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
  for (let s = -13.43; s < 13.43 - VENT_W; s += VENT_P) {
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
  add('posCase', [kx2 - KN * KEY_P - 0.7, F + 4.5, z(0.145)],
                 [kx2 + 0.7, F + 7.7, z(0.160)], { bevel: 0.35 });
  const ROW = [
    { y0: 0.058, y1: 0.133, lo: 0.145, hi: 0.186 },
    { y0: 0.148, y1: 0.223, lo: 0.160, hi: 0.201 },
  ];
  for (const r of ROW) {
    const ky1 = F + r.y0, ky2 = F + r.y1;
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
  pbox('posCase', 2.59, 10.64, 0.0, 0.45, 0.140, 0.200, { bevel: 0.4 });
  pbox('posScreen', 2.96, 10.27, 0.4, 0.75, 0.168, 0.190, { bevel: 0 });
  // The tail leaves the silhouette, which is what says the thing is loaded.
  pbox('boxPale', 4.31, 9.18, 0.7, 1.05, 0.128, 0.172, { bevel: 0 });
  pbox('posTrim', 4.31, 9.18, 1.05, 1.15, 0.128, 0.136, { bevel: 0 });

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
  rbox('posCase', -3.03, -0.04, 2.53, 4.31, 0.078, 0.150, { bevel: 0.5 });
  rbox('posCase', -2.85, -0.68, 2.74, 4.15, 0.150, 0.245, { bevel: 0.5 });
  rbox('posCase', -5.20, 1.46, 1.28, 5.56, 0.236, 0.330, CASE);
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
