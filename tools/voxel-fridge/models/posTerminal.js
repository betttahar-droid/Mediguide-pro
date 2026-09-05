// POS TERMINAL — the pharmacy till computer.
//
// THE FOURTH PROP, and the first that is not a cabinet. The three fridges are
// one tall mass with things on the front; this is WIDER THAN IT IS TALL, an
// assembly of five separate masses, and its biggest feature is a recessed dark
// rectangle rather than an opening. So the hollow-carcass recipe never comes up
// and almost nothing carries over except the module itself — which is the point
// of building it.
//
// BUILT AS AN ASSEMBLY, NOT AS A SILHOUETTE. This file was first written the
// other way round — boxes nudged about until the overlay stopped complaining —
// and it reached 99% match while containing a power button sunk inside the
// bezel it was meant to sit on, a glare mark floating 0.04 units off the glass,
// and a bezel rim held 0.15 in front of the case with nothing between them.
// None of that shows in a front elevation, which is the only thing the overlay
// looks at. So the order below is the order the thing would be ASSEMBLED:
//
//     floor -> feet -> bottom shell -> moulded base
//            -> keyboard deck  -> keycaps
//            -> rear riser (3 steps) -> neck -> tube flare
//            -> CRT case -> cap -> bezel -> glass -> glare
//     bought-in modules bolted to a named face: printer, card reader, switch
//
// and every part declares { part, mount } — WHAT IT IS and WHAT IT IS BOLTED
// TO. main.js walks those declarations and proves each part actually touches
// its mount. A part that floats is a part whose position came from a picture
// rather than from the thing it is attached to.
//
// TWO RULES THAT FOLLOW FROM THAT, and are worth more than any measurement:
//   1. A JOINT IS A NAMED PLANE, SHARED. The top of the plinth and the bottom
//      of the deck are not two numbers that agree; they are ZP.plinthTop, used
//      twice. Move it and the deck moves with it.
//   2. A PART THAT STANDS PROUD STILL REACHES BACK IN. A detail on a surface is
//      not a sticker hovering in front of it — the switch's body runs into the
//      moulding, the glare mark starts at the glass. The visible half is what
//      you measured; the buried half is what makes it a part.
//
// Built by following docs/BUILDING-A-PROP.txt. Nothing in ../style.js changed
// except eight material families and the two userData fields the join-check
// reads.
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
import { STYLE, tableBox, screws } from '../style.js';

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
  const T = STYLE.tint;

  // Every add() below goes through at(): the part's own name, the part it is
  // mounted to, then its shape options. Reading the file top to bottom you can
  // follow the chain from the floor up, and main.js checks the chain holds.
  const at = (part, mount, o = {}) => ({ ...o, part, mount });

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
  const uy = (u) => py(u);            // a side-sheet fraction -> world y

  // ORDERED PAIRS, ALWAYS. px() is mirrored, so px(smaller) > px(larger) and a
  // box written straight from the front-sheet measurements comes out back to
  // front. tableBox warns and sorts, but a warning per box is not a design —
  // which is one more reason nothing below is placed from a raw front-sheet
  // pair any more: every x is an offset from a named face of the part beneath.

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
  // 2 * W, which is what keeps these fixed while the prop resizes.
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

  // ---- DATUM PLANES: THE JOINTS, NAMED ONCE -------------------------------
  // Every one of these is where two parts MEET. Written as a plane and used
  // from both sides, a joint cannot drift: the deck cannot end 0.3 above the
  // plinth, because it starts at the plinth's own top. Where a number appears
  // only once it is a free face, not a joint, and stays inline.
  const ZP = {
    floor:     0,
    footTop:   z(0.019),   // feet        -> bottom shell
    shellTop:  z(0.056),   // shell rim   -> moulded plinth
    plinthTop: z(0.175),   // plinth      -> deck, riser, keys
    deckLip:   z(0.190),   // the deck's own front edge
    deckTop:   z(0.196),   // deck wedge  -> keycaps
    step1Top:  z(0.222),   // riser step 1 -> step 2
    step2Top:  z(0.268),   // step 2      -> step 3
    riserTop:  z(0.292),   // riser       -> neck
    flareLo:   z(0.336),   // the tube's underside lip
    flareMid:  z(0.360),   // lip         -> flare
    caseLo:    z(0.375),   // flare       -> CRT case, bezel rim
    shoulder:  z(0.390),   // the tube's shoulder, where the case steps back
    capLo:     z(0.944),   // case        -> top chamfer
    capHi:     z(1.000),
    neckTop:   z(0.366),
  };
  // The base's own four faces. Named because five other parts hang off them.
  const BASE = { xOut: -W, xIn: W, front: -D, back: D };
  const EPS = 0.08;

  // BEVELS PER AXIS. Moulded plastic, so softer than the steel cabinets: the
  // case is rounded on the verticals and slightly on the horizontals, the deck
  // is crisp where it meets the floor, and everything recessed is flat.
  const CASE = { bevel: [1.3, 0.7, 1.3] };
  const CRISP = { bevel: [0.9, 0, 0.9] };

  // =========================================================================
  // 1. FEET -> the floor
  // =========================================================================
  // ANCHOR: measured 0.086 of the sheet across (3.2 units) and set 1.6 units in
  // from the base's corners. Four of them; the front view shows two.
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    const x1 = sx > 0 ? W - 4.8 : -W + 1.6, x2 = sx > 0 ? W - 1.6 : -W + 4.8;
    const y1 = sy > 0 ? D - 5.0 : -D + 1.8, y2 = sy > 0 ? D - 1.8 : -(D - 5.0);
    add('posFoot', [x1, y1, ZP.floor], [x2, y2, ZP.footTop],
        at('foot', 'floor', { bevel: 0.45 }));
  }

  // =========================================================================
  // 2. BOTTOM SHELL -> the feet
  // =========================================================================
  // The lower rim the case sits on, inset all round so the plinth above reads
  // as overhanging it. ASYMMETRIC, because the reference is: at z 0.030 it
  // reads 0.023..0.846 against a deck of 0.000..0.859, so the lip is inset 0.86
  // units on the reference's LEFT (table +x) and 0.50 on its right. It starts
  // where the feet stop — ZP.footTop, not a fraction of its own — and a lip
  // starting 0.004 higher left a 1105-pixel band of bare floor, the largest
  // single disagreement on the front elevation.
  add('posCase', [-(W - 0.50), -(D - 0.78), ZP.footTop],
                 [W - 0.86, D - 0.78, ZP.shellTop],
      at('shell', 'foot', CRISP));

  // =========================================================================
  // 3. MOULDED BASE (the plinth) -> the shell
  // =========================================================================
  // THE POINT OF PER-FACE BEVELS. The reference's base front is a dead vertical
  // face at u 0.000 from z 0.06 to 0.13, and only then chamfers back to u 0.061
  // by z 0.17. One bevel number per AXIS cuts both ends of that axis, so a
  // 1.3-unit depth bevel pushed the ENTIRE front face back 1.3 units — which is
  // what "the bevel is uniform" looks like when you measure it.
  //
  //   [x-, x+, bottom, top, front, back]
  //
  // Bottom 0 and front 2.4 gives the reference's profile: full depth at the
  // floor, a chamfer running up to the deck. The chamfer between two faces is
  // set by BOTH their insets, so the top-front chamfer is 2.4 deep and 2.2 tall
  // and the bottom-front edge stays sharp.
  //
  // IT OVERHANGS ON ONE SIDE ONLY, and that asymmetry is an artefact of the
  // measurement, not of the object. The reference's plinth reads 0.000..0.867
  // against a deck of 0.010..0.857, so it is proud on both — but its LEFT edge
  // is the object's bounding box, the overlay aligns on that box, and widening
  // it shifted every measurement of every other part (1821 pixels lost to gain
  // 381). On the right the card reader sets the box instead, so the overhang is
  // free there. Worth saying rather than hiding.
  // x bevel 0.4, not 1.3: a 1.3 chamfer on the verticals combines with the 2.2
  // top bevel into a chamfer across the top corners, and the reference's plinth
  // holds full width right up to its top.
  const PLINTH_PROUD = 0.30;
  add('posCase', [BASE.xOut - PLINTH_PROUD, BASE.front, ZP.shellTop],
                 [BASE.xIn, BASE.back, ZP.plinthTop],
      at('plinth', 'shell', { bevel: [0.4, 0.4, 0, 2.2, 2.4, 0.4] }));

  // =========================================================================
  // 4. KEYBOARD DECK -> the plinth   (and the keycaps -> the deck)
  // =========================================================================
  // The deck is the top face of the same moulding, so it starts at the plinth's
  // own top plane and is TWO pieces for one mechanical reason: the front edge
  // of a keyboard is a flat lip you rest a wrist on, and the keys sit on a
  // wedge behind it that rises towards the screen. The reference's side profile
  // says exactly that — material at u 0.083..0.161 up to z 0.192, then keys.
  //
  // The deck's extent in x is not a measurement: it is WHERE THE KEYS GO plus a
  // margin, so widening the till lengthens the deck and the keyboard together.
  // The keys are ANCHOR (a finger is one size) and the count is what follows.
  const kx2 = BASE.xIn - KEY_IN;                       // the first key's edge
  const KN = Math.max(3, Math.floor((kx2 - (BASE.xOut + PRN_B + 1.6)) / KEY_P));
  const DECK_X = [kx2 - KN * KEY_P - 0.7, kx2 + 0.7];  // the keys, plus margin

  add('posCase', [DECK_X[0], uy(0.105), ZP.plinthTop],
                 [DECK_X[1], uy(0.205), ZP.deckLip],
      at('deck', 'plinth', { bevel: [0.8, 0.8, 0, 0.6, 0.8, 0] }));
  add('posCase', [DECK_X[0], uy(0.205), ZP.plinthTop],
                 [DECK_X[1], uy(0.332), ZP.deckTop],
      at('deck', 'plinth', { bevel: [0.8, 0.8, 0, 0.8, 1.0, 0.6] }));

  // THREE TIERS OF KEYS, stepping UP and BACK, because that is what the side
  // view shows: the front-most point of the whole prop at z 0.19 is a key at
  // u 0.161, at z 0.21 a key at 0.229, and at z 0.22 a key at 0.275..0.327 with
  // a gap behind it before the riser starts at 0.373. Two flat rows could not
  // produce that profile at any height, and two rows at the SAME height are one
  // row in a dead-on front elevation.
  //
  // A KEYCAP IS ROUGHLY SQUARE IN PLAN. Written 3.9 units deep against a 1.7
  // unit width the keys came out as tall fins standing on the deck — correct
  // from the front, absurd from anywhere else. DEPTH IS ANCHORED TOO: D scales
  // with W, so a key placed at a depth FRACTION grows in the other direction
  // just as surely, and the edge-strip check cannot see it because it never
  // leaves the front elevation.
  const ROW = [
    { u0: 0.161, u1: 0.213, lo: ZP.plinthTop,  hi: z(0.205) },
    { u0: 0.216, u1: 0.272, lo: z(0.188),      hi: z(0.218) },
    { u0: 0.268, u1: 0.324, lo: ZP.deckTop,    hi: z(0.226) },
  ];
  for (const r of ROW) {
    const ky1 = uy(r.u0), ky2 = uy(r.u1);
    for (let k = 0; k < KN; k++) {
      const s = kx2 - (k + 1) * KEY_P;
      // The reference's right-hand group is darker — a numeric or function
      // block, which every till has. Indexed by POSITION, not random, so two
      // renders of the same model are comparable and a wider deck extends the
      // pale block rather than reshuffling every key. A FIXED five keys at the
      // far end, not a fraction of the keyboard, or a wider till would get a
      // wider function block. px() is mirrored, so k = 0 is the reference's
      // right-hand end: written the obvious way round it put the function block
      // on the wrong side of the keyboard.
      const dark = k < KEY_DARK;
      add(dark ? 'posKeyDk' : 'posKey', [s, ky1, r.lo], [s + KEY_W, ky2, r.hi],
          at('key', 'deck', { bevel: 0.18 }));
    }
  }

  // =========================================================================
  // 5. REAR RISER -> the plinth, each step on the one below
  // =========================================================================
  // The wedge that carries the screen. THREE STEPS, not one symmetric taper:
  // the reference's wedge recedes far more at the FRONT than at the back and
  // taperZ can only narrow both ends equally. 24 triangles more, and the
  // difference between a wedge and a block.
  //
  // NO TOP BEVEL ON A STACKED STEP. Each step's top IS the next one's floor, so
  // a top chamfer cuts a groove at every joint — the riser measured 0.025 of
  // the width narrow on BOTH sides at z 0.29. Soft vertical corners, crisp
  // everywhere else; the slope comes from the steps, not from their chamfers.
  const STEP = { bevel: [0.8, 0.8, 0, 0, 0, 0] };
  // EACH STEP TAPERS WITHIN ITSELF. Measured at its own bottom AND top the
  // riser draws in continuously — insets 0.021/0.008 of the width at z 0.175
  // and 0.049/0.044 by z 0.222 — so a step with vertical sides is up to 1.0
  // unit wide across the top half of its own band. Insets are FIXED world units
  // off the base's own edges, never fractions.
  add('posCase', [BASE.xOut + 0.30, uy(0.330), ZP.plinthTop],
                 [BASE.xIn - 0.78, uy(0.955), ZP.step1Top],
      at('riser', 'plinth', { ...STEP, taperX: 1.0 }));
  add('posCase', [BASE.xOut + 1.70, uy(0.373), ZP.step1Top],
                 [BASE.xIn - 2.00, uy(0.919), ZP.step2Top],
      at('riser', 'riser', { ...STEP, taperX: 0.6 }));
  add('posCase', [BASE.xOut + 2.83, uy(0.430), ZP.step2Top],
                 [BASE.xIn - 3.28, uy(0.880), ZP.riserTop],
      at('riser', 'riser', { ...STEP, taperX: 0.8 }));

  // =========================================================================
  // 6. NECK -> the riser
  // =========================================================================
  // Crisp where it leaves the riser: CASE chamfered the neck's bottom into the
  // base, which the reference draws as a straight 0.300..0.571 column all the
  // way down. Its front draws BACK as it rises — u 0.475 at the riser, 0.498 by
  // z 0.33 — so a straight column stood 911 pixels in front of the reference.
  const NECK_HW = 0.1355 * U;
  add('posCase', [MCX - NECK_HW, uy(0.475), ZP.riserTop],
                 [MCX + NECK_HW, uy(0.820), ZP.neckTop],
      at('neck', 'riser', { bevel: [0.9, 0, 0.9], taperZ: 0.7 }));

  // =========================================================================
  // 7. THE MONITOR — flare -> case -> cap, all carried by the neck
  // =========================================================================
  // A MONITOR IS A BOUGHT-IN PART. Section 6's rule: could you buy it on its
  // own, in a box, in one size? Then it is ANCHOR. Written as sheet fractions
  // the monitor grew with the till, which is not what widening a counter unit
  // does — you get a longer desk and more keys, not a bigger screen. So the
  // whole assembly below is FIXED WORLD SIZE, centred on the base, converted
  // once from the sheet at the default width; only the base stretches under it.
  //
  // The consequence is worth naming: after this the edge-strip resize test
  // cannot validate the monitor, because it is anchored to the CENTRE and the
  // strips are cut from the edges. compare.py --centre exists for that.
  //
  // MY0 IS THE BEZEL'S PLANE, AND THE CASE SITS BEHIND IT. The side profile
  // reads u 0.164 at z 0.39 and 0.179 from z 0.44 up — the tube's bezel stands
  // proud at the bottom and the case runs back above it, which is what a CRT
  // does. Built at one plane for the whole height the body was forward of its
  // own flare, and the overlay showed it as a tall blue strip down the front.
  const MY0 = -10.09, MY1 = 15.15;    // the tube's front and back faces
  const BODY_F = MY0 + 0.15;          // the case, set behind the bezel
  const mb = (kind, hx, y0, y1, za, zb, o) =>
    add(kind, [MCX - hx, y0, za], [MCX + hx, y1, zb], o);

  // The tube's underside, and IT IS NOT SOLID. At z 0.344 the reference reads
  // TWO runs — 0.251..0.430 and 0.513..0.819 — a front lip and the neck, with
  // the underside recessed between them. Built as one slab it filled that gap
  // and ran 0.087 of the depth too far back, the worst single error on the prop.
  // The lip hangs off the flare above it, which is what carries it.
  mb('posCase', 0.337 * U, uy(0.251), uy(0.430), ZP.flareLo, ZP.flareMid,
     at('tube-lip', 'tube-flare', { bevel: 0, taperX: -0.0105 * U }));
  // The flare itself is CONCAVE — 12.63 half-width at z 0.344, still 13.02 at
  // 0.362, 15.03 by 0.375, most of the widening in the last third. A negative
  // taper is a flare, the one direction the fridges never needed; one linear
  // step put it 6% wide across the middle of the band. Its front runs from
  // u 0.230 to 0.179 over its own height, so a flat face stood 287 pixels
  // proud of the reference's outline.
  mb('posCase', 0.3475 * U, uy(0.230), uy(0.907), ZP.flareMid, ZP.caseLo,
     at('tube-flare', 'neck', { bevel: 0, taperX: -0.054 * U, taperZ: -1.7 }));

  // THE CASE, in two pieces because the tube has a shoulder: the reference
  // reads 0.179..0.902 at z 0.37 and 0.179..0.945 at z 0.39, so a body at full
  // depth from 0.375 puts 480 pixels behind the reference's outline.
  // NO BOTTOM CHAMFER — a y-bevel cuts the top AND the bottom, so the body
  // pulled in just above the flare and the two met at a waist. Visible in the
  // overlay as a notch, invisible at a glance.
  mb('posCase', MHW, BODY_F, uy(0.905), ZP.caseLo, ZP.shoulder,
     at('crt-case', 'tube-flare', { bevel: [1.3, 0, 1.3] }));
  mb('posCase', MHW, BODY_F, MY1, ZP.shoulder, ZP.capLo,
     at('crt-case', 'crt-case', { bevel: [1.3, 0, 1.3] }));
  // The CRT hump on the back. Only the side view has it, and it is most of what
  // makes the silhouette read as a monitor rather than a box.
  mb('posCase', 0.345 * U, MY1, 16.79, z(0.450), z(0.884),
     at('crt-hump', 'crt-case', { bevel: [1.6, 1.6, 0] }));

  // The top chamfer, MEASURED in four steps and built as frusta — the same
  // rounding as a fridge shoulder, a different profile. Written out rather than
  // handed to capProfile() because the monitor is not centred in DEPTH (it sits
  // 2.3 units back) and capProfile centres on the origin.
  const CAP = [[ZP.capLo, 0], [z(0.962), 0.021 * U],
               [z(0.979), 0.042 * U], [ZP.capHi, 0.063 * U]];
  for (let i = 0; i < CAP.length - 1; i++) {
    const [z0, i0] = CAP[i], [z1, i1] = CAP[i + 1];
    mb('posFlat', MHW - i0, BODY_F + i0 * 0.25, MY1 - i0 * 0.55, z0, z1,
       at('crt-cap', i ? 'crt-cap' : 'crt-case',
          { bevel: 0, taperX: i1 - i0, taperZ: (i1 - i0) * 0.40 }));
  }

  // ---- the bezel rim, the glass, and the ring -----------------------------
  // The rim is the front lip of the same moulding, standing proud of the case
  // at the bottom of the tube: the profile reads u 0.164 up to z 0.41 and 0.179
  // from z 0.44 on. IT REACHES BACK INTO THE CASE. Written to stop dead on the
  // bezel plane it was a plate hanging 0.15 in front of the body with nothing
  // joining the two — invisible from the front, absurd in section, and the
  // first thing the join-check reported. The buried half costs no triangles
  // anyone sees and makes it a moulding instead of a sticker.
  const RIM_F = uy(0.164);            // the front-most point of the whole prop
  mb('posCase', MHW - 0.6, RIM_F, MY0 + 2.0, ZP.caseLo, z(0.415),
     at('bezel-rim', 'crt-case', { bevel: [0.8, 0.8, 0, 0.8, 0, 0] }));

  // A dark rectangle inside a warm tan ring. The ring is the piece that makes
  // it read as a CRT: without it the dark panel sits on the case like a sticker.
  //
  // THE RING IS FOUR BARS, NOT A PANEL, and everything here stands PROUD of the
  // case. Written as one solid box at the case's own front plane, the ring was
  // inside the case and the screen was inside the ring — the buried-part check
  // reported both before this was ever rendered. Same rule as a fridge cavity:
  // a hollow is bars or panels, never a block, and a recess is built proud.
  // BARELY PROUD: 0.5 units of it is 0.017 of the depth and the side view has
  // no such lip — a 1920-pixel strip down the monitor's whole front. 0.15 is
  // enough to read in front of the screen and small enough to vanish in profile.
  const RY = [MY0, MY0 + 0.40];           // the ring, ON the measured front
  const SY = [MY0 + 0.05, MY0 + 0.25];    // the glass, sunk inside it
  const RHW = 0.3245 * U, RT = 0.015 * U; // ring half-width and bar thickness
  const bar = (x1, x2, za, zb) =>
    add('posTrim', [MCX + x1, RY[0], za], [MCX + x2, RY[1], zb],
        at('bezel', 'crt-case', { bevel: 0 }));
  const SZ = [z(0.447), z(0.870)];        // the glass, top and bottom
  bar(-RHW, -RHW + RT, SZ[0] - z(0.015), SZ[1] + z(0.015));
  bar(RHW - RT, RHW, SZ[0] - z(0.015), SZ[1] + z(0.015));
  bar(-RHW, RHW, SZ[0] - z(0.015), SZ[0]);
  bar(-RHW, RHW, SZ[1], SZ[1] + z(0.015));
  const SHW = 0.3095 * U;
  add('posScreen', [MCX - SHW, SY[0], SZ[0]], [MCX + SHW, SY[1], SZ[1]],
      at('glass', 'bezel', { bevel: 0 }));

  // ONE soft glare, two thin blocks stepped across. A square reads as a sticker
  // stuck to the tube. A stepped diagonal is not worth attempting on glass you
  // see THROUGH (BUILDING-A-PROP 8.10) — but a CRT is opaque, so this is simply
  // a mark on a surface. IT STARTS AT THE GLASS: written 0.04 in front of it,
  // the mark floated, which is a reflection with nothing to reflect off.
  for (const [ga, gb, za, zb] of [[0.2815, 0.2815 + 0.028, 0.760, 0.845],
                                  [0.2615, 0.2815, 0.795, 0.862]]) {
    add('posGlare', [MCX + ga * U, SY[0] - 0.12, z(za)],
                    [MCX + gb * U, SY[0] + 0.02, z(zb)],
        at('glare', 'glass', { bevel: 0 }));
  }

  // ---- power button and lamp -> the bezel rim -----------------------------
  // ANCHORED TO THE MONITOR'S OWN EDGE, fixed distance and fixed size: the
  // monitor stretches, the switch bolted to it does not.
  //
  // IT SITS ON THE RIM'S FACE. Written on the CASE's plane it was 0.14 behind
  // the rim's front — a switch buried inside the moulding it is meant to be
  // mounted in, which no elevation shows and which the join-check does. Proud
  // of RIM_F by a third of a unit, and running back into the moulding.
  const monEdge = MCX - MHW;          // the monitor's own -x face
  const BY = [RIM_F - 0.30, RIM_F + 1.2];
  add('posScreen', [monEdge + BTN_A, BY[0], ZP.caseLo],
                   [monEdge + BTN_A + BTN_W, BY[1], z(0.405)],
      at('power-switch', 'bezel-rim', { bevel: 0.25 }));
  add('digit', [monEdge + BTN_A + BTN_W + 0.9, BY[0], z(0.385)],
               [monEdge + BTN_A + BTN_W + 0.9 + LAMP_W, BY[1], z(0.405)],
      at('lamp', 'bezel-rim', { bevel: 0 }));

  // ---- vent slots (REPEAT) -> the cap -------------------------------------
  // MEASURED at a pitch of 0.0255 of the sheet — 0.96 world units — running
  // x 0.073 to 0.79. The count follows the case; the slot never changes size.
  // A SLOT IS CUT IN THE FACE IT VENTS THROUGH. The cap's front is stepped back
  // as it rises (BODY_F + a quarter of each step's inset), so vents written on
  // the case's own plane stood 0.45 units off the front of the cap — a comb of
  // fins in mid-air over the monitor, which shows in the side silhouette and in
  // nothing else. They now start just proud of the shallower step and run back
  // into the moulding, which is the only way a slot in a face can be built with
  // no boolean subtract.
  const VX = 0.3585 * U;
  for (let s = MCX - VX; s < MCX + VX - VENT_W; s += VENT_P) {
    add('posScreen', [s, MY0 + 0.25, z(0.965)], [s + VENT_W, MY0 + 0.9, z(0.985)],
        at('vent', 'crt-cap', { bevel: 0 }));
  }

  // =========================================================================
  // 8. BOUGHT-IN MODULES, bolted to a named face of the base
  // =========================================================================
  // ---- receipt printer -> the plinth's front face -------------------------
  // It is IN the base's front face, not on top of the deck: the reference has
  // the slot at z 0.168..0.190 with the paper hanging BELOW it to z 0.128,
  // which only happens on a vertical face.
  //
  // FLUSH, NOT PROUD. At 0.45 units proud the housing became the front-most
  // point of the whole prop, which shifted the side view's bounding box and so
  // every depth measurement of every other part. The reference's printer is a
  // recess in the face, not a box on it, so only the paper leaves the outline.
  // AND IT SITS IN THE CHAMFER: the front face is chamfered back over
  // z 0.135..0.175, so a printer at the nominal plane stands proud of it.
  // Offsets are from the base's -x edge and from its front face, both named.
  const F = BASE.front, R = BASE.xOut;
  const pbox = (kind, xa, xb, y0, y1, za, zb, o) =>
    add(kind, [R + xa, F - y1, za], [R + xb, F - y0, zb], o);
  pbox('posCase', 0.069 * U, PRN_B, -1.30, -1.05, z(0.140), z(0.200),
       at('printer', 'plinth', { bevel: 0.4 }));
  pbox('posScreen', 0.079 * U, 0.274 * U, -1.10, -0.85, z(0.168), z(0.190),
       at('printer-slot', 'printer', { bevel: 0 }));
  // The tail leaves the silhouette, which is what says the thing is loaded. It
  // lives in the chamfer band too: recessed to the printer's own plane it was
  // inside the plinth and drew nothing, brought forward to the nominal front
  // face it would set the side view's bounding box. z 0.140..0.172 is where the
  // chamfer has opened far enough for it to show.
  pbox('boxPale', 0.115 * U, 0.245 * U, -1.05, -0.70, z(0.140), z(0.172),
       at('paper', 'printer', { bevel: 0 }));
  pbox('posTrim', 0.115 * U, 0.245 * U, -0.80, -0.62, z(0.140), z(0.148),
       at('tear-strip', 'paper', { bevel: 0 }));

  // ---- card reader on its stalk -> the plinth's side ----------------------
  // An outrigger, and the reason this prop's sheet is wider than its base: a
  // separate bought-in terminal bolted to the side of the till. Fixed size,
  // fixed distance from the base's -x edge, never a fraction of anything.
  //
  // ITS FOOT IS FUSED INTO THE PLINTH, from z 0.075. The reference reads
  // 0.023..0.846 at z 0.04 (no stalk at all) and one unbroken 0.000..0.935 from
  // z 0.09 — so below that there is nothing, and above it the foot runs into
  // the base with no gap. Built from z 0.02 as a separate column standing on
  // the floor it put 1651 pixels of render-only material exactly where the
  // reference has bare ground: a part attached to the wrong thing.
  const BK = BASE.back;
  const rbox = (kind, xa, xb, ya, yb, za, zb, o) =>
    add(kind, [R + xa, BK - yb, za], [R + xb, BK - ya, zb], o);
  rbox('posCase', -3.00, 0.40, 2.53, 4.31, z(0.075), z(0.150),
       at('reader-foot', 'plinth', { bevel: 0.5 }));
  rbox('posCase', -3.02, -0.56, 2.74, 4.15, z(0.150), z(0.245),
       at('reader-stalk', 'reader-foot', { bevel: 0.5 }));
  // THE HEAD IS TILTED BACK towards the operator, which is why it is two steps:
  // the front view puts it at z 0.236..0.351, but the side view shows it
  // reaching u 0.919 at z 0.23 and nothing beyond 0.819 by z 0.29. One box says
  // a slab, and put a solid block across the rear of the side silhouette.
  // Top bevels at 0.4: at 1.0 they chamfered the head's own top corners.
  rbox('posCase', -5.20, 1.46, 1.78, 5.56, z(0.231), z(0.290),
       at('reader-head', 'reader-stalk',
          { bevel: [1.3, 1.3, 0, 0.4, 1.0, 1.0], taperZ: 1.6 }));
  rbox('posCase', -4.95, 1.46, 4.90, 5.56, z(0.290), z(0.351),
       at('reader-head', 'reader-head', { bevel: [1.3, 1.3, 0, 0.4, 1.0, 1.0] }));
  rbox('posRead', -4.61, 0.86, 5.49, 5.72, z(0.252), z(0.318),
       at('reader-face', 'reader-head', { bevel: 0 }));
  // the card slot, ON the face rather than in front of it
  rbox('posTrim', -1.53, 0.53, 5.72, 5.92, z(0.258), z(0.268),
       at('card-slot', 'reader-face', { bevel: 0 }));
  // its own little keypad, three pips, so it reads as a reader and not a box
  for (let k = 0; k < 3; k++) {
    rbox('posKey', -2.20 - 0.974 * k, -1.53 - 0.974 * k, 5.63, 5.79,
         z(0.258), z(0.272), at('reader-key', 'reader-face', { bevel: 0 }));
  }

  // ---- screws (the style bible's one RULE, at a fixed inset) --------------
  for (const sx of [-1, 1]) {
    g.add(...screws(THREE, kit, sx > 0 ? 'right' : 'left',
                    0, z(0.111), D - 1.0, z(0.033),
                    sx * (W + EPS), 2.2, 1.0, T.side));
  }
  return g;
}
