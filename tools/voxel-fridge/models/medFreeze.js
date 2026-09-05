// MED-FREEZE — a tall single-door commercial vaccine fridge with a glass front.
//
// THE THIRD PROP, and the one that tests the guide rather than the technique.
// vaccineFridge.js and homeFridge.js were built while docs/making-a-prop.txt
// was being written, so they cannot be evidence that it works. This one was
// built by following it start to finish and changing nothing in ../style.js
// except adding material families — no shader work, no new atlas, no new
// geometry primitive. Every number below came off
// docs/style-bible/props/med_freeze.png measured against its magenta ground.
//
// MEASURED (front view 346 x 630 px, side view 300 x 630 px):
//   overall ratio      1 : 1.821
//   depth / width      0.867
//   door stands proud  0.070 of the depth  (= 1.95 units at the default width)
//
//   VERTICAL (z as a fraction of the total height, 0 at the floor)
//     feet                 0.000 .. 0.024
//     base skirt           0.024 .. 0.051
//     plinth recess        0.051 .. 0.107   dark, full width less a margin
//     base lip (bright)    0.107 .. 0.135
//     door                 0.135 .. 0.884
//       bottom rail        0.135 .. 0.150
//       glass opening      0.150 .. 0.830
//       top rail           0.830 .. 0.884
//     separator groove     0.884 .. 0.897   dark
//     control band         0.898 .. 1.000
//     shelves (4)          0.176, 0.354, 0.532, 0.710   pitch 0.178
//     handle               0.417 .. 0.619
//
//   HORIZONTAL (x as a fraction of the width, 0 at the left edge)
//     body edge highlight  0.012 .. 0.026
//     handle               0.026 .. 0.061   ANCHORED, see below
//     door stile           0.012 .. 0.095
//     glass opening        0.095 .. 0.905   (81% of the width)
//     cross logo           0.055 .. 0.170   z 0.913 .. 0.976
//     indicator lamp       0.671 .. 0.714   z 0.937 .. 0.960
//     display              0.751 .. 0.951   z 0.921 .. 0.972
//
//   SIDE VIEW (u as a fraction of the depth, 0 at the FRONT)
//     door leading edge    0.013 .. 0.083
//     rating label         0.130 .. 0.340   z 0.055 .. 0.118
//     vent grille          0.537 .. 0.947   z 0.060 .. 0.286, slat pitch 0.019
//
// NO HINGES. Checked rather than assumed, the same way as on homeFridge: the
// side view's leading edge is a CONTINUOUS strip from z 0.024 to the top, broken
// only at z 0.887..0.892 and z 0.129..0.133 — which is where the door STOPS and
// the carcass lip shows, not where a hinge sits. Nothing on either elevation is
// a hinge, so there are none here.
import { STYLE, tableBox, decal, screws, capProfile } from '../style.js';

export const objLo = 0;
export const objHi = 58.3;          // 32 wide x 1.821 — set ONCE, at the
                                    // default width; see the note below
export const label = 'med-freeze';
// How wide a frame this prop needs, as a fraction of its height. Squatter and
// deeper than the first two, so the kit's 0.56 clipped its back flank in iso.
export const aspect = 0.80;

export function build(THREE, MATS, kit, H) {
  const g = new THREE.Group();
  const add = (kind, a, b, opts) => g.add(tableBox(THREE, kind, a, b, MATS, opts));
  const tx = (n) => n * STYLE.texel;
  const T = STYLE.tint;

  // ---- HOW EACH PART BEHAVES WHEN THE PROP RESIZES ------------------------
  //   STRETCH  fills the span — carcass, door rails, plinth, glass opening,
  //            shelves. Written as fractions of W, because that IS what it is.
  //   ANCHOR   a FIXED WORLD SIZE at a FIXED DISTANCE from a named edge —
  //            handle, feet, cross logo, lamp, display, rating plate. Written
  //            with fromRefL/fromRefR and NEVER as a fraction of W.
  //   REPEAT   a fixed size whose COUNT follows the span — the vent slats and
  //            every box and vial on the shelves. Widen the cabinet and it gets
  //            MORE stock, not fatter stock.
  const W = H;                 // body half-width — the 100%
  const D = W * 0.867;         // half-depth, measured off the side view
  // HEIGHT IS INDEPENDENT OF WIDTH. Deriving it from W turns ?w= into a uniform
  // scale, which is not what a builder resize does and would make the whole
  // acceptance test vacuous. objHi above is this same number, so the geometry
  // and the shading ramp cannot drift apart.
  const TOT = objHi - objLo;
  const z = (f) => f * TOT;    // a measured fraction -> world height
  // THE FRONT CAMERA MIRRORS X. It sits at -z looking toward +z with up +y, so
  // its screen-right is table -x (three.js right-handed; see main.js VIEWS). An
  // orthographic front elevation rendered that way is a mirror image, which is
  // invisible on a symmetric prop and was invisible on both earlier ones — this
  // is the first model with a feature that is only on one side, so it is the
  // first that could show it. Rather than let the render disagree with the
  // sheet it was measured from, fractions read from the LEFT of the reference
  // map to table +x, and everything on the front is placed through these.
  const px = (f) => W - f * 2 * W;    // reference x fraction -> world x
  const py = (f) => -D + f * 2 * D;   // reference depth fraction -> world y
  //                                     (the side view is not mirrored)

  // ANCHOR helpers: a fixed distance in from an EDGE OF THE REFERENCE, never a
  // fraction of it. refL/refR are named for the reference's left and right, so
  // the mirror above is applied once, here, and not remembered at each call.
  const fromRefL = (off) => W - off;
  const fromRefR = (off) => -W + off;

  // NAMED MOUNTING PLANES, so nothing is placed on a number typed at a call
  // site and a depth change moves every fitting with the cabinet.
  const F = -D;                // carcass front face
  const P_DOOR = F - 1.95;     // door and control band — the frontmost surface
  const P_GLASS = F - 0.5;     // the glass sits recessed inside the door frame
  const BACK = D - 1.4;        // interior back wall
  const EPS = 0.08;

  // BEVELS ARE PER AXIS. This cabinet is a crisp industrial box, not the soap
  // bar the retro fridge is: soft vertical corners, a small chamfer where the
  // top meets the sides, and dead flat everywhere a panel is recessed. [x,y,z].
  const BOX = { bevel: [1.1, 0, 1.1] };
  const SOFT = { bevel: [0.8, 0.5, 0.4] };

  // ---- feet ---------------------------------------------------------------
  // ANCHOR: a fixed 4.5 x 4.5 block a fixed 1.2 units in from each corner. The
  // reference's feet are 68 px across the pair on a 346 px body — they do not
  // grow with the cabinet, and writing them as a fraction of W is exactly the
  // bug the handle had on the previous prop.
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    const x1 = sx > 0 ? W - 5.7 : -W + 1.2, x2 = sx > 0 ? W - 1.2 : -W + 5.7;
    const y1 = sy > 0 ? D - 5.7 : -D + 1.2, y2 = sy > 0 ? D - 1.2 : -(D - 5.7);
    add('medDark', [x1, y1, 0], [x2, y2, z(0.024)], { bevel: 0.5 });
  }

  // ---- base skirt, plinth recess and the bright lip above it ---------------
  // The skirt is the body carried down past the recess, so the recess reads as
  // something cut INTO the cabinet rather than a dark bar stuck under it.
  add('medBody', [-(W - 0.6), -(D - 0.6), z(0.024)], [W - 0.6, D - 0.6, z(0.135)],
      BOX);
  // The recess: dark, inset 1.6 units from each side — a FIXED margin, so a
  // wider cabinet gets a wider vent rather than a thicker frame.
  add('medDark', [-(W - 2.2), F - 0.9, z(0.051)], [W - 2.2, F - 0.4, z(0.107)],
      { bevel: 0 });
  // and its own bottom sill, which is what stops the recess reading as a hole
  add('medFlat', [-(W - 2.2), F - 1.0, z(0.046)], [W - 2.2, F - 0.4, z(0.053)],
      { bevel: 0 });
  // The bright lip. MEASURED at #d4dedc against a body of #a5b5aa — nearly the
  // material's own lit tone, so it is medTrim rather than a separate colour.
  add('medTrim', [-(W - 0.3), -(D - 0.3), z(0.107)], [W - 0.3, D - 0.3, z(0.135)],
      { bevel: [0.7, 0.4, 0.4] });

  // ---- the carcass --------------------------------------------------------
  // A SHELL — two flanks, a back, and a run above and below the opening. Not a
  // solid box: this cabinet is a glass-fronted display case and you look
  // straight through the door into it, so the volume behind the opening has to
  // be genuinely absent. Building it solid first and then putting the shelves
  // "inside" it hid every one of them, which is the same class of mistake as
  // the solid cavity below and worth naming twice.
  //
  // G is the glass opening's half-width, and it is W MINUS A FIXED STILE, not a
  // fraction of W. MEASURED at 0.095 of the width, which is 3.04 units at the
  // default size — a door frame is a pressed steel section and a wider cabinet
  // gets a wider WINDOW, not a fatter frame. Written as 0.81 * W (which is the
  // same number at the default width, and the reason this was easy to miss) the
  // stiles visibly thickened at ?w=28. Clamped so a narrow cabinet still has a
  // window rather than an inverted one.
  const STILE = 3.04;
  const G = Math.max(W * 0.5, W - STILE);
  const CAV_LO = z(0.150), CAV_HI = z(0.830);
  const CAR_LO = z(0.130), CAR_HI = z(0.986);
  add('medBody', [-W, -D, CAR_LO], [-G, D, CAR_HI], BOX);      // left flank
  add('medBody', [G, -D, CAR_LO], [W, D, CAR_HI], BOX);        // right flank
  add('medBody', [-W, D - 1.6, CAR_LO], [W, D, CAR_HI], BOX);  // back
  add('medBody', [-W, -D, CAR_LO], [W, D, CAV_LO], BOX);       // under the opening
  add('medBody', [-W, -D, CAV_HI], [W, D, CAR_HI], BOX);       // over the opening
  // The top. MEASURED FLAT: the front view holds the full 346 px right up to
  // z 0.992 and only the outline is above that, so there is no shoulder here
  // and no cap to profile — one small chamfer, as a single frustum, is the
  // whole of it. This is the same capProfile() the retro fridge rounds its top
  // with; a different measurement, not a different technique.
  capProfile(add, 'medFlat', W, D, z(0.986), [[z(0.014), 0.9]], { bevel: 0 });

  // ---- interior -----------------------------------------------------------
  // A LINER, NOT A CAVITY. There is no boolean subtract here and there does not
  // need to be one — but the first attempt filled the opening with a solid
  // medGlass block, whose FRONT FACE then occluded every shelf and every box
  // behind it. The cabinet rendered as an empty green panel and read exactly
  // like a modelling mistake, because it was one: a hollow is five thin panels,
  // not one thick one.
  //
  const LIN = 0.7;
  add('medDark', [-G, BACK - LIN, CAV_LO], [G, BACK, CAV_HI], { bevel: 0 });
  add('medGlass', [-G, F + 0.4, CAV_LO], [-G + LIN, BACK, CAV_HI], { bevel: 0 });
  add('medGlass', [G - LIN, F + 0.4, CAV_LO], [G, BACK, CAV_HI], { bevel: 0 });
  add('medGlass', [-G, F + 0.4, CAV_LO], [G, BACK, CAV_LO + LIN], { bevel: 0 });
  add('medGlass', [-G, F + 0.4, CAV_HI - LIN], [G, BACK, CAV_HI], { bevel: 0 });

  // ---- shelves and their stock --------------------------------------------
  // MEASURED at z 0.176, 0.354, 0.532, 0.710 — a pitch of 0.178, which at the
  // default height is 10.4 units. Four of them, as counted off the reference.
  const SHELF = [0.176, 0.354, 0.532, 0.710];
  const SY0 = F + 1.6, SY1 = BACK - 1.2;   // the depth band stock occupies

  // REPEAT, not STRETCH. Items are a fixed world size laid left to right at a
  // fixed pitch until the shelf runs out, so widening the cabinet puts MORE
  // vaccine on the shelf. A wider box would be a bigger box of vaccine, which
  // is not what happens when you buy a wider fridge.
  //
  // The pattern is indexed rather than random: a seeded shuffle would change
  // every box every time the file is touched, and then no render could be
  // compared with the one before it.
  const ITEM = [
    // [width, height, body, stripe, stripe height]
    [4.6, 4.4, 'boxPale', 'boxBlue', 0.9],
    [4.0, 5.4, 'boxBlue', 'boxPale', 1.1],
    [5.4, 3.2, 'boxPale', 'boxWarm', 0.8],
    [3.4, 3.8, 'boxWarm', 'boxPale', 0.7],
    [4.8, 4.0, 'boxPale', 'medDark', 0.6],
    [null], // vial cluster, handled below
  ];
  const GAP = 0.7;               // fixed gap between items, in world units
  const VIALS = 4, VPITCH = 1.5; // a vial cluster is itself a fixed size
  const widthOf = (spec) => (spec[0] === null ? VIALS * VPITCH : spec[0]);
  const pick = (i, seed) => ITEM[(i * 5 + seed * 3) % ITEM.length];

  const stockRow = (zBase, seed) => {
    const base = z(zBase) + 0.45;
    const lo = -G + 1.4, hi = G - 1.4;
    // MEASURE THE ROW, THEN LAY IT OUT. Placing greedily from the left leaves
    // whatever did not fit as one wide gap at the right end, and a shelf with a
    // quarter of it empty reads as a modelling accident rather than as stock.
    // Centring the leftover is still REPEAT — the item sizes and the gap are
    // fixed and only the COUNT follows the span.
    let n = 0, used = -GAP;
    while (used + GAP + widthOf(pick(n, seed)) <= hi - lo) {
      used += GAP + widthOf(pick(n, seed));
      n++;
    }
    let x = lo + (hi - lo - used) / 2;
    for (let i = 0; i < n; i++) {
      const spec = pick(i, seed);
      if (spec[0] === null) {
        // A cluster of vials: four small cylinders-as-boxes with a darker cap.
        // Same REPEAT rule one level down — the cluster is a fixed size.
        for (let v = 0; v < VIALS; v++) {
          const vx = x + v * VPITCH;
          add('vial', [vx, SY0 + 1.2, base], [vx + 1.0, SY0 + 2.2, base + 3.0],
              { bevel: 0 });
          add('medDark', [vx, SY0 + 1.2, base + 3.0],
                         [vx + 1.0, SY0 + 2.2, base + 3.5], { bevel: 0 });
        }
        x += VIALS * VPITCH + GAP;
      } else {
        const [w, h, body, stripe, sh] = spec;
        const back = SY0 + 1.0 + (i % 2) * 1.4;   // a little depth variation
        add(body, [x, back, base], [x + w, Math.min(back + 5.2, SY1), base + h],
            { bevel: 0 });
        // The label band. This is the whole reason the stock reads as MEDICINE
        // and not as grey blocks: every box on the reference carries a printed
        // stripe, and one flat band of a second colour is enough to say so.
        add(stripe, [x + 0.5, back - 0.15, base + h * 0.55],
                    [x + w - 0.5, back - 0.1, base + h * 0.55 + sh], { bevel: 0 });
        add('medDark', [x + 0.5, back - 0.15, base + h * 0.30],
                       [x + w - 1.6, back - 0.1, base + h * 0.30 + 0.35],
            { bevel: 0 });
        x += w + GAP;
      }
    }
  };

  for (let s = 0; s < SHELF.length; s++) {
    // The shelf itself: a thin wire tray, so it is FLAT — a bevel on a 0.4-unit
    // slab is mostly chamfer and reads as a rounded bar.
    add('medTrim', [-G + 0.5, SY0 - 0.4, z(SHELF[s])],
                   [G - 0.5, SY1, z(SHELF[s]) + 0.4], { bevel: 0 });
    // its front edge rail, a shade brighter, which is what makes the shelves
    // read as separate planes through the glass rather than as pale stripes
    add('shelf', [-G + 0.5, SY0 - 0.55, z(SHELF[s])],
                 [G - 0.5, SY0 - 0.4, z(SHELF[s]) + 0.4], { bevel: 0 });
    stockRow(SHELF[s], s);
  }

  // ---- the door: a FRAME, not a slab --------------------------------------
  // Four rails around the opening, standing 1.95 units proud of the carcass.
  // Built as rails rather than as a slab with a hole because there is no hole
  // primitive here and there does not need to be one.
  const dIn = W - 0.4;
  const DOOR_LO = z(0.135), DOOR_HI = z(0.884);
  const stile = (x1, x2) =>
    add('medBody', [x1, P_DOOR, DOOR_LO], [x2, F + 0.6, DOOR_HI], SOFT);
  stile(-dIn, -G);             // left stile, the one the handle is on
  stile(G, dIn);               // right stile
  add('medBody', [-dIn, P_DOOR, DOOR_LO], [dIn, F + 0.6, z(0.150)], SOFT);
  add('medBody', [-dIn, P_DOOR, z(0.830)], [dIn, F + 0.6, DOOR_HI], SOFT);

  // The dark inner lip. MEASURED as a 4 px black line at x 0.081..0.095 and
  // 0.905..0.919 — the gasket, and the single thing that makes the glass read
  // as set INTO a frame rather than painted onto the front of one.
  const lip = 0.6;
  add('medDark', [-G - lip, P_GLASS, CAV_LO - lip], [-G, P_GLASS + 0.4, CAV_HI + lip],
      { bevel: 0 });
  add('medDark', [G, P_GLASS, CAV_LO - lip], [G + lip, P_GLASS + 0.4, CAV_HI + lip],
      { bevel: 0 });
  add('medDark', [-G - lip, P_GLASS, CAV_LO - lip], [G + lip, P_GLASS + 0.4, CAV_LO],
      { bevel: 0 });
  add('medDark', [-G - lip, P_GLASS, CAV_HI], [G + lip, P_GLASS + 0.4, CAV_HI + lip],
      { bevel: 0 });

  // ---- handle -------------------------------------------------------------
  // ANCHORED, NOT SCALED — the lesson from the retro fridge, applied first
  // rather than fixed afterwards. MEASURED at x 0.026..0.061 of the width and
  // z 0.417..0.619 of the height: 0.83 units in from the door's edge and 1.12
  // wide at the default size. Both are CONSTANTS. A wider cabinet gets the same
  // handle in the same place relative to its edge.
  const H_OFF = 0.9;           // fixed distance in from the door's left edge
  const H_W = 1.4;             // fixed handle width
  const hx2 = fromRefL(H_OFF), hx1 = hx2 - H_W;
  const ha = z(0.417), hb = z(0.619);
  // Two mounts wider than the grip, so the fitting has a silhouette instead of
  // being a bar glued to a panel.
  for (const zz of [ha + 1.4, hb - 1.4]) {
    add('steel', [hx1 - 0.45, P_DOOR - 1.1, zz - 0.9],
                 [hx2 + 0.45, P_DOOR + 0.2, zz + 0.9], { bevel: 0.3 });
  }
  add('steel', [hx1, P_DOOR - 2.1, ha], [hx2, P_DOOR - 1.0, hb], { bevel: 0.45 });
  // a bright catch down its lit face and a dark return under it
  add('chrome', [hx1 + 0.25, P_DOOR - 2.25, ha + 0.6],
                [hx1 + 0.75, P_DOOR - 2.05, hb - 0.6], { bevel: 0 });
  add('slot', [hx1 + 0.2, P_DOOR - 1.15, ha + 0.4],
              [hx2 - 0.2, P_DOOR - 1.0, hb - 0.4], { bevel: 0 });

  // ---- separator groove and control band ----------------------------------
  add('medDark', [-dIn, P_DOOR + 0.3, z(0.884)], [dIn, F + 0.6, z(0.897)],
      { bevel: 0 });
  add('medBody', [-dIn, P_DOOR, z(0.897)], [dIn, F + 0.6, z(0.992)], SOFT);
  const cf = P_DOOR - 0.35;    // the control band's own front plane

  // EVERYTHING ON THE CONTROL BAND IS ANCHORED IN WORLD UNITS, not placed at a
  // measured FRACTION. px() converts a fraction to a position and that position
  // moves with W — which is right for a panel and wrong for a badge. Placed
  // through px() the logo drifted away from the corner and the display grew
  // wider as the cabinet did, both visible only at ?w=28. The fractions below
  // are converted to fixed offsets ONCE, at the default width, and the offsets
  // are what the geometry uses.
  //
  // The medical cross. MEASURED at x 0.055..0.170, z 0.913..0.976 — 3.7 x 3.7
  // units, which is square, so it is a real cross and not a stretched one, and
  // its centre is 3.6 units in from the reference's left edge.
  const CX = fromRefL(3.6), CZ = z(0.945), CR = 1.85, CA = 0.62;
  add('medBlue', [CX - CR, cf, CZ - CA], [CX + CR, P_DOOR, CZ + CA], { bevel: 0 });
  add('medBlue', [CX - CA, cf, CZ - CR], [CX + CA, P_DOOR, CZ + CR], { bevel: 0 });

  // The indicator lamp, MEASURED at x 0.671..0.714, z 0.937..0.960 — 1.4 units
  // square. 'digit' is the kit's green; a lamp material named for an EFFECT is
  // the mistake that once put a green stripe on a steel handle.
  const LX = fromRefR(9.9), LZ = z(0.948);
  add('medDark', [LX - 1.0, cf, LZ - 1.0], [LX + 1.0, P_DOOR, LZ + 1.0],
      { bevel: 0 });
  add('digit', [LX - 0.6, cf - 0.15, LZ - 0.6], [LX + 0.6, P_DOOR, LZ + 0.6],
      { bevel: 0 });

  // The temperature display. MEASURED at x 0.751..0.951, z 0.921..0.972 —
  // 6.4 x 3.0 units, in a bezel. It reads DARK on the reference, so it stays
  // dark: inventing digits here would be the same mistake as inventing hinges.
  // 6.4 units wide, its right-hand end 1.6 units in from the reference's right
  // edge — both FIXED. dx1 is the reference-LEFT end, so it is the larger x.
  const dx2 = fromRefR(1.6), dx1 = dx2 + 6.4;
  const dz1 = z(0.921), dz2 = z(0.972);
  add('steel', [dx2 - 0.5, cf, dz1 - 0.5], [dx1 + 0.5, P_DOOR, dz2 + 0.5],
      { bevel: 0.4 });
  add('disp', [dx2, cf - 0.2, dz1], [dx1, P_DOOR, dz2], { bevel: 0 });

  // ---- side vent grille ---------------------------------------------------
  // MEASURED off the side view at u 0.537..0.947 of the depth and z 0.060..0.286
  // of the height, slats at a pitch of 0.019 (1.1 units). REPEAT: the slats are
  // a fixed size and the count follows the panel, so a deeper cabinet gets more
  // of them at the same pitch instead of a stretched grille.
  //
  // The reference only draws the LEFT flank. It goes on both, deliberately: the
  // vent is the condenser's air path and the cabinet is symmetric in plan, so
  // one bald flank would be an artefact of having only one drawing rather than
  // a fact about the object.
  const VY1 = py(0.537), VY2 = py(0.947);
  const VZ1 = z(0.060), VZ2 = z(0.286);
  const PITCH = 1.1;
  // A RECESS IS BUILT PROUD. The flank is solid, so a panel placed INSIDE it at
  // x < W is simply invisible — the first version put the grille there and the
  // side view came back with a flat dark patch and no slats at all. The recess
  // is faked the way the plinth vent and the condenser grille on the other two
  // props are: a dark panel standing a hair off the surface, lighter slats
  // standing a hair off THAT, and a rim around both. The shading does the rest.
  for (const sx of [-1, 1]) {
    const p = (o) => sx * (W + o);
    const dk = [Math.min(p(0.02), p(0.16)), Math.max(p(0.02), p(0.16))];
    const sl = [Math.min(p(0.12), p(0.26)), Math.max(p(0.12), p(0.26))];
    add('medDark', [dk[0], VY1, VZ1], [dk[1], VY2, VZ2], { bevel: 0 });
    // the rim, standing out level with the slats so the panel reads as sunk
    for (const [a, b] of [[VY1, VY1 + 0.8], [VY2 - 0.8, VY2]]) {
      add('medFlat', [sl[0], a, VZ1], [sl[1], b, VZ2], { bevel: 0 });
    }
    for (const [a, b] of [[VZ1, VZ1 + 0.7], [VZ2 - 0.7, VZ2]]) {
      add('medFlat', [sl[0], VY1, a], [sl[1], VY2, b], { bevel: 0 });
    }
    // the slats
    for (let s = VZ1 + 1.5; s < VZ2 - 1.2; s += PITCH) {
      add('medFlat', [sl[0], VY1 + 1.0, s], [sl[1] - 0.15, VY2 - 1.0, s + 0.55],
          { bevel: 0 });
    }
    // Screws at the panel's corners — the one fitting the style bible applies
    // as a RULE rather than a placement, at a fixed inset in world units.
    g.add(...screws(THREE, kit, sx > 0 ? 'right' : 'left',
                    (VY1 + VY2) / 2, (VZ1 + VZ2) / 2,
                    (VY2 - VY1) / 2, (VZ2 - VZ1) / 2,
                    sx * (W + 0.28 + EPS), 1.4, 1.0, T.side));
  }

  // ---- rating plate -------------------------------------------------------
  // MEASURED on the side view at u 0.130..0.340, z 0.055..0.118 — 3.7 units
  // tall, low on the flank near the front. Clamped to the flank with `fit`, so
  // it can never hang off the geometry the way the hinges once did.
  g.add(decal(THREE, kit, 'ratingPlate', 'left', py(0.235), z(0.087),
              tx(4), -W - EPS, T.side, { u: D - 1.0, v: TOT / 2 }));
  return g;
}
