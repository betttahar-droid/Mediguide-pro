// THE STYLE, as a module any model can import.
//
// This file is the answer to "make the technique reproducible on other models".
// Nothing in it knows what a fridge is. A model is a list of boxes with material
// names; this supplies the materials, the shading and the palette, so a second
// object gets the identical look for free and a style change lands on every
// object at once.
//
// ---------------------------------------------------------------------------
// THE TECHNIQUE, and why it is neither of the two the industry usually offers.
//
// Asked how to texture a modular kit that resizes, the field gives two answers:
//
//   TRIM SHEETS      strips of detail that tile along one axis. Resizable along
//                    that axis only, and every part must be UV'd onto the right
//                    strip at a matched texel density.
//   TRIPLANAR / world-space UV
//                    project a texture along the world axes. Scale-independent,
//                    but it cannot place anything RELATIVE TO A PART — the
//                    detail slides across a part as it grows, because the
//                    projection knows about the world and not about the box.
//
// A resizable prop kit needs both properties at once: marks that keep their
// size (triplanar's strength) AND marks that stay anchored to a part's own
// corners and edges (the trim sheet's strength). So this takes the coordinate
// that gives you both:
//
//   *** DISTANCE FROM THE FRAGMENT TO THE EDGE OF ITS OWN FACE, IN WORLD UNITS ***
//
// It is a per-face signed distance field, computed from the fragment's object
// position and the box's half-extents — two numbers the geometry already has.
// From it, every mark in this art style falls out as a threshold:
//
//   d < 0.22                       the dark outline
//   0.22 < d < 0.48                the light catch on the lit edges
//   0.95 < d < 1.21                the recessed inner border of a pressed plate
//   fract(p / 14) near 0           a seam subdividing a large panel
//
// Because d is in world units, a mark is 0.22 units wide on a part of any size:
// nothing stretches, and a bigger part gets MORE marks rather than bigger ones.
// Because d is measured from the part's OWN face, marks stay welded to its
// corners however it grows. There is no UV, no atlas, no texel density to match
// against the render, no mip chain, and no patch whose pixel size dictates a
// part's world size. The adaptability is structural rather than something the
// art has to be careful about.
//
// ---------------------------------------------------------------------------
// COLOUR MANAGEMENT OFF, and it must be off before the first THREE.Color is
// built. This renderer's premise is that the authored hex IS the output pixel:
// flat shading, a locked palette, nearest sampling, no lights. Three's default
// converts every `new THREE.Color('#e9e3d4')` from sRGB into its linear working
// space, and this renderer writes linear straight out — so the cream authored
// at #e9e3d4 was landing on screen as #d5ccb6 and the interior at #458574 as
// #0c3f26. Every colour in every render was ~14% dark.
//
// It reads as an art problem, which is the dangerous part: the interior looked
// too dark, and the obvious "fix" is to lighten the hex until it looks right —
// which bakes the gamma error permanently into a palette that was correctly
// sampled in the first place. The palette was never wrong. The pipeline was.
export function useRawColours(THREE) {
  THREE.ColorManagement.enabled = false;
}

// EVERY CONSTANT BELOW IS MEASURED, NOT CHOSEN. Re-derive them all with:
//     python3 tools/authoring/style_bible.py
// which generates the reference sheets with Nano Banana from docs/reference/,
// measures them, and writes docs/style-spec.json.
export const STYLE = {
  // Face tints — the entire lighting model; nothing in the scene is a light.
  // Measured off the reference turnaround's ISO view: cream reads #fef7e7 on
  // top, #e9e3d4 head-on and #c8c3b6 on the side (254/233/200), and its teal
  // agrees at 0.855. NOTE: the style bible's own cube, generated from the voxel
  // prop catalogue, comes out far punchier at 1.35 / 1.00 / 0.746 — the two
  // reference sets genuinely disagree about how hard faces darken. These are
  // the fridge sheet's numbers, because that sheet is the object being matched.
  tint: { top: 1.090, front: 1.000, side: 0.858, back: 0.900, bottom: 0.740 },

  // Edge marks, in WORLD UNITS. The style bible's scale-ladder settles that
  // these are fixed rather than relative: the same border measured 45, 40 and
  // 44 px on panels 208, 262 and 486 px wide — an 11% spread in WIDTH against
  // an 82% spread in FRACTION. A border that were relative would have grown
  // from 45 px to over 100.
  outline: 0.22,   // dark rim on the very edge of every face
  catch: 0.26,     // lighter line just inside it, on the lit edges only

  // The pressed-plate border. Two independent measurements agree: the ladder's
  // inner line sits 0.96 units in (scaling its band ratios by the outline), and
  // the reference fridge's own flank border sits 8 px off a 269 px flank = 0.95
  // units. It replaces a hand-typed 1.4 that was never measured.
  inset: 0.95,
  insetLine: 0.26,

  // Seam pitch. The style bible's surface-marks sheet answered a question that
  // had been argued from taste for three passes: what goes on a big empty
  // painted panel. Not speckle, not nothing — the style SUBDIVIDES it into a
  // few flat sub-panels separated by seams, then puts fasteners at the
  // sub-panel corners. So a face wider than two pitches gets a seam every
  // `seam` units, which is adaptive in exactly the right way: a bigger panel
  // gets MORE sub-panels of the same size, never one huge field and never a
  // stretched pattern.
  seam: 14.0,
  seamLine: 0.28,

  // Zero everywhere for this object, and that is a measurement. An earlier pass
  // hashed a speckle onto every painted surface; the reference's flank runs 81%
  // a single value and its door field 84 unbroken pixels, and the ~1.7% of
  // darker pixels on that flank cluster into the panel border, the joint rail
  // and the door edge rather than into flecks. Kept because the dumpster and
  // vehicle kits in docs/reference DO carry patchy variation.
  wearCell: 2.0,

  // ONE TEXTURE PIXEL, IN WORLD UNITS. This is the pixel grid the whole retro
  // look sits on. The reference swatches run about 32 texels across a panel;
  // this cabinet's flank is ~30 units, so one unit per texel puts it on the
  // same grid. At the prototype's 8 px/unit that is a chunky, unmistakably
  // pixelated 8 screen pixels per texel.
  // Raised from 1.0. A published prop in this style states its budget outright:
  // 138 triangles and a 64x32 pixel texture for an entire door. At one unit per
  // texel this cabinet's front carried 32 texels; at 1.6 it carries 20, which is
  // the scale that actually reads as PlayStation-era rather than as neat modern
  // pixel art. The mask atlas is cut to the same grid, so mask detail can never
  // be finer than the model's own pixels again.
  texel: 1.6,
  ditherSpan: 5.0,   // how far the corner dither reaches in from a face edge

  // Default chamfer on every edge, in world units — one texel. The reference
  // kit never leaves a form a plain prism; this is the cheapest move that stops
  // one reading as a box. shapedBox clamps it to a third of the smallest side,
  // so a louvre slot keeps a hairline rather than turning inside out.
  bevel: 1.6,

  // The baked vertical ramp: everything below objLo*..*objHi darkens toward
  // aoFloor at the base. Set per object by the model before it builds.
  objLo: 0, objHi: 100, aoFloor: 0.80,

  // NINE-SLICE, for the surface mask tiles.
  //   marginWorld  how many WORLD units the tile's authored border occupies.
  //                Fixed, so the border and its bolts stay native at any size.
  //                Sized to the measured plate border: 5 of 40 texels over 2.6
  //                units is ~0.52 units a texel, matching the object's own grid.
  //   period       world length of one repeat of the tile's middle. 16 units
  //                across the tile's ~30 remaining texels keeps that same
  //                texel size, so margin and middle read as one grid.
  // Derived per tile from its OWN measured margin, in cut_surfaces.json, times
  // `texel` below — see marginFor(). Held as a fallback only.
  marginWorld: 3.0,
  period: 24.0,
};

// Colour families plus the rules each material runs. Sampled from the
// reference, never picked.
//
//   TEXTURE, on a world-space texel grid
//     fleck   fraction of texels taking the lit or shade tone — scattered
//             single-pixel variation, the base texture of any painted surface
//     grain   directional runs, for wood and brushed metal
//     dither  a checkerboard that thins away from the face edge: the retro
//             value ramp, which is how this style shades a corner
//     perf    a regular dot grid, for grilles and speaker cloth
//   FORM
//     bevel   chamfer width, or 0. THE SILHOUETTE RULE: "if it doesn't add to
//             the silhouette, you don't need it." A bevelled box is 44
//             triangles against a plain box's 12, so bevelling everything
//             quadrupled the model to 2598 triangles - hero-prop budget for a
//             prop that should sit at 300-1500. Interior walls, shelves,
//             louvre slots and display glyphs never break the outline, so they
//             pay the plain price.
//     tileMid true only when the tile's middle carries content (a vent):
//             it then repeats at a fixed world period instead of stretching
//     surface a nine-slice tone-mask tile from surfaces.png. Its outer margin
//             maps to a FIXED world width so the authored border and its bolts
//             stay native at any part size, and only the middle tiles. This is
//             the decal idea applied to the whole surface, and it replaces the
//             procedural `inset` on any material that carries one — running
//             both drew two pressed borders on top of each other.
//     inset   the pressed-plate border, on faces big enough to hold one
//     edge    outline+catch width, or 0 for trim too small to carry one
//     seam    subdivide large faces with seams
//
// FLECK AND DITHER ARE OFF ON EVERY PAINTED SURFACE, and that is the third and
// final position on this question, so it is worth saying why it is not a
// flip-flop. The texture swatches genuinely do measure 12-20% of texels off the
// base tone — but a SWATCH is not an OBJECT. The character-ab sheet settles it
// by drawing the same cabinet plain and finished: both halves have flat fields,
// and every bit of the difference is placed fittings. Spraying that 14% over a
// whole cabinet produced uniform noise, which reads as grime rather than as
// character, because character is detail that MEANS something and a hash cannot
// mean anything.
//
// What survives procedurally is the detail that is genuinely a property of the
// MATERIAL rather than of the object: `grain` runs along brushed metal wherever
// it appears, `perf` is what a speaker or a vent IS. Everything else moved into
// the fittings atlas at the bottom of this file, where it can be placed.
const D = { lit: null, shade: null, inset: 0, edge: 0.22, seam: 0,
            fleck: 0, grain: 0, dither: 0, perf: 0, surface: null,
            tileMid: false, bevel: undefined };
const M = (o) => ({ ...D, ...o });

export const MATERIALS = {
  cream:    M({ base: '#e9e3d4', lit: '#f7f2e6', shade: '#dcd6c6', surface: 'plate' }),
  blueGrey: M({ base: '#adb6ba', lit: '#b7c2c5', shade: '#a3adb2', surface: 'plateSeam' }),
  teal:     M({ base: '#377c62', lit: '#3f8a6d', shade: '#2e6752', surface: 'trim' }),
  frame:    M({ bevel: 0, base: '#35785f', lit: '#3a8368', shade: '#2e6752', edge: 0.14, surface: 'trim' }),
  purple:   M({ base: '#5c4a70', lit: '#6b5780', shade: '#4a3e58', edge: 0.16 }),
  plinth:   M({ base: '#5c4a72', lit: '#6b5780', shade: '#4a3e58', edge: 0.16 }),
  interior: M({ bevel: 0, base: '#458574', lit: '#4c8978', shade: '#3b7565', edge: 0.16 }),
  shelf:    M({ bevel: 0, base: '#d7e7e2', lit: '#deebe6', shade: '#bed2cc', edge: 0.10 }),
  glint:    M({ bevel: 0, base: '#5c9c88', lit: '#6aa896', shade: '#4c8978', edge: 0 }),
  // Sampled off docs/style-bible/props/home_fridge.png for the second prop.
  // Adding a prop should cost a colour family and nothing else — no shader
  // change, no new tile, no new rule.
  // Same colour family, no edge rule. The outline+catch is drawn on every box,
  // which is right for a part and wrong for a SLICE OF ONE SURFACE: a stacked
  // shoulder of three slices drew three rims and read as a ziggurat. Anything
  // built from stacked slices wants this variant.
  mintFlat: M({ base: '#a5d6b6', lit: '#c5f3d4', shade: '#95baa7', edge: 0 }),
  mint:     M({ base: '#a5d6b6', lit: '#c5f3d4', shade: '#95baa7', surface: 'trim' }),
  // Bright steel for a highlight ON steel. `glint` could not serve here: it was
  // repurposed to a GREEN for the other model's glass reflection, so a handle
  // highlighted with it had a green stripe down its face that read as a hole
  // through the handle. A material named for an effect rather than a substance
  // stops being reusable the moment a second object wants the effect.
  chrome:   M({ base: '#dde6f7', lit: '#f2f6fd', shade: '#bcc9e2', edge: 0.10 }),
  steel:    M({ base: '#c0ceeb', lit: '#d6e2f8', shade: '#a3b0cc', edge: 0.16 }),
  tan:      M({ base: '#d9a95f', lit: '#e8bc76', shade: '#c08c45', edge: 0.14, grain: 0.30 }),
  tan2:     M({ bevel: 0, base: '#c08c45', lit: '#d9a95f', shade: '#8e6529', edge: 0 }),
  slot:     M({ bevel: 0, base: '#3f3a33', lit: '#4a4439', shade: '#20242b', edge: 0 }),
  disp:     M({ bevel: 0, base: '#262b36', lit: '#333a48', shade: '#171b23', perf: 1.0, surface: 'recess' }),
  digit:    M({ bevel: 0, base: '#74de96', lit: '#9bf0b4', shade: '#4fb673', edge: 0 }),
  lamp:     M({ bevel: 0, base: '#e2894e', lit: '#f5a56d', shade: '#b96a37', edge: 0 }),
};

// Part names a model may use that map onto a material above.
export const ALIAS = {
  grille: 'tan', flank: 'blueGrey', cavity: 'interior', glass: 'glint',
};

// NOTE FOR ANY EDIT BELOW: the two shaders are JS TEMPLATE LITERALS, so a
// backtick anywhere inside them — including inside a // comment — terminates
// the string and the file stops parsing. This has bitten three times; the
// symptom is a JS "Unexpected identifier" naming a word from a comment, which
// points nowhere near the real cause. Use plain quotes in shader comments.
export const VERT = /* glsl */ `
attribute vec3 aHalf;
varying vec3 vLocal, vHalf, vNrm;
varying float vWorldY;
void main() {
  vLocal = position; vHalf = aHalf; vNrm = normal;
  vWorldY = (modelMatrix * vec4(position, 1.0)).y;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

export const FRAG = /* glsl */ `
precision highp float;
uniform vec3 uBase, uLit, uShade;
uniform float uInset, uWear, uEdge, uSeam, uCell;
uniform float uFleck, uGrain, uDither, uPerf, uTexel, uDitherSpan;
uniform sampler2D uMask;
uniform vec4 uTile;          // the tile's rect in the atlas, normalised
uniform float uHasMask, uMarginW, uMarginF, uPeriod, uTileMid;
uniform float uOutline, uCatch, uInsetAt, uInsetLine, uSeamPitch, uSeamLine;
uniform float uTop, uFront, uSide, uBack, uBottom;
varying vec3 vLocal, vHalf, vNrm;
varying float vWorldY;
uniform float uObjLo, uObjHi, uAOFloor;

float hash(vec2 p) {
  return fract(sin(dot(floor(p), vec2(127.1, 311.7))) * 43758.5453);
}

// NINE-SLICE ALONG ONE AXIS: face position -> position within the tile.
//
// This is the decal idea applied to the whole surface. The outer mw WORLD
// units of the face map onto the tile's outer mf fraction -- its authored
// border, with the bolts in it — and the remainder tiles the middle at a fixed
// world period. So the border keeps its width and its corners stay native
// however the part grows, and only the flat middle repeats.
//
//   p      position along the face, in [-half, half]
//   hf     the face's half-extent, world units
//   mw     margin width in WORLD units (fixed: this is the resize property)
//   mf     the same margin as a fraction of the tile, measured from the art
//   period world length of one repeat of the tile's middle
// NOTE half cannot be a parameter name: it is a RESERVED WORD in GLSL ES.
// Using it made the whole shader fail to compile, and three then drew the
// geometry not at all — the render came back as bare decals floating on the
// background, which looks nothing like a shader error and cost a detour.
float slice1(float p, float hf, float mw, float mf, float period) {
  float L = 2.0 * hf;
  float d = p + hf;                         // 0..L from the low edge
  // A face too narrow to hold two margins has no middle left. Squeeze the
  // whole tile onto it rather than letting the two margins overlap and fight,
  // which mirrored the border back on itself and read as a smear.
  if (L <= 2.0 * mw) return d / L;
  if (d < mw)      return (d / mw) * mf;
  if (d > L - mw)  return 1.0 - ((L - d) / mw) * mf;
  float inner = (d - mw) / (L - 2.0 * mw);        // 0..1 across the middle
  // STRETCH the middle by default, tile it only when it has content.
  //
  // Tiling a middle that is one flat tone is all cost and no benefit: the
  // repeat is invisible where the tone is uniform and shows as a grid of faint
  // squares everywhere it is not, which is exactly what covered the flanks.
  // Stretching a flat region cannot produce an artefact — there is nothing in
  // it to distort — and the border, which is the part that must not stretch,
  // is already held fixed by the margin. That is the classic UI nine-slice
  // bargain and it applies here for the same reason.
  //
  // A vent is the exception: its middle IS content, so it repeats at a fixed
  // world period and a taller vent gets MORE slots, never longer ones.
  if (uTileMid > 0.5) inner = fract((d - mw) / period);
  return mf + inner * (1.0 - 2.0 * mf);
}

void main() {
  // A SIGNED per-face basis. Two faces of one axis must not mirror each other,
  // or the display reads backwards from behind — which it did, until this
  // stopped being a bare pair of axes.
  vec3 a = abs(vNrm);
  vec2 local, half2;
  if (a.x > a.y && a.x > a.z) {
    local = vec2((vNrm.x > 0.0 ? -1.0 : 1.0) * vLocal.z, vLocal.y); half2 = vHalf.zy;
  } else if (a.y > a.z) {
    local = vec2(vLocal.x, (vNrm.y > 0.0 ? -1.0 : 1.0) * vLocal.z); half2 = vHalf.xz;
  } else {
    local = vec2((vNrm.z > 0.0 ? 1.0 : -1.0) * vLocal.x, vLocal.y); half2 = vHalf.xy;
  }

  // THE COORDINATE EVERYTHING KEYS OFF: world-unit distance to this face's own
  // edge. Fixed-size marks anchored to a part's own corners, at any part size.
  vec2 fromEdge = half2 - abs(local);
  float d = min(fromEdge.x, fromEdge.y);

  // How much room this face has. Every mark gates on it, because a rule that
  // ignores the size of what it is drawn on is how you get a cream bar between
  // two drawers of one carcass: mechanically correct, physically meaningless.
  // A face too small for a mark does not get a squashed version — it does not
  // get the mark.
  float lim = min(half2.x, half2.y);
  bool lit = (local.x < 0.0 || local.y > 0.0);   // the lit edges: top and left

  // IS THIS AN AXIS FACE, OR A CHAMFER FACET? max(|n|) is 1 on a box face and
  // about 0.707 on a 45-degree bevel. It matters because every mark below keys
  // off distance-to-the-edge-of-the-face, and on a chamfer every fragment IS at
  // the box's extreme — d collapses to ~0, so the whole facet was painted the
  // outline colour. The corner facets then read as dark triangular spikes
  // sticking out of the silhouette, which looks exactly like broken geometry
  // and is not: the mesh was fine, the shading rule simply did not apply there.
  // A bevel facet wants nothing but its blended tint.
  // (Named axisFace, not flat: 'flat' is an interpolation qualifier in GLSL
  // and will not parse as an identifier -- the same class of collision as
  // 'half' earlier, and just as silent, since a shader that fails to compile
  // draws nothing rather than complaining in the picture.)
  bool axisFace = max(a.x, max(a.y, a.z)) > 0.95;

  vec3 c = uBase;

  // ==== SURFACE MASK ========================================================
  // The atlas carries STRUCTURE, the material carries COLOUR. Each texel is one
  // of three levels — shade / base / lit — so a single "plate" tile renders
  // correctly on cream, teal and blue-grey alike, and no colour ever leaves the
  // texture. That is what keeps the frame snappable to a locked palette, and it
  // is the thing a colour atlas cannot do.
  if (axisFace && uHasMask > 0.5) {
    vec2 t = vec2(slice1(local.x, half2.x, uMarginW, uMarginF, uPeriod),
                  slice1(local.y, half2.y, uMarginW, uMarginF, uPeriod));
    // Half-texel inset so nearest sampling cannot pick up the neighbouring
    // tile across the atlas gutter.
    vec2 auv = uTile.xy + clamp(t, 0.002, 0.998) * uTile.zw;
    float m = texture2D(uMask, vec2(auv.x, 1.0 - auv.y)).r;
    if (m < 0.4) c = uShade;
    else if (m > 0.6) c = uLit;
  }

  // ==== TEXTURE =============================================================
  // THE TEXEL GRID. Every pattern below is drawn on it and it is measured in
  // WORLD UNITS, so a part twice the size gets twice as MANY texels rather than
  // texels twice as big. That is the whole reason this can be pixel texture and
  // still be perfectly resizable: there is no image to stretch and no texel
  // density to reconcile with the render.
  vec2 tex = floor(local / uTexel);

  // FLECKS — scattered single texels off the base tone. The base texture of any
  // painted surface here; measured at 12-20% coverage on the reference swatches.
  // Density varies across the face: a coarse cell decides how busy its patch
  // is, then the texel decides individual pixels. Hashing the texel alone gives
  // an even salt-and-pepper that reads as noise; the reference's swatches are
  // clustered — busier in some areas, calm in others — and two scales is what
  // buys that. Both scales are in world units, so the clustering does not
  // change as the part resizes either.
  if (uFleck > 0.0) {
    float region = hash(floor(local / (uTexel * 6.0)) + 3.1);
    float amt = uFleck * (0.35 + 1.5 * region * region);
    float h = hash(tex);
    if (h < amt * 0.55) c = uShade;
    else if (h > 1.0 - amt * 0.45) c = uLit;
  }

  // GRAIN — directional runs. The hash coordinate is stretched along one axis
  // so one value covers several texels in a column, which is what makes wood
  // read as grain instead of as noise.
  if (uGrain > 0.0) {
    float g = hash(vec2(tex.x, floor(local.y / (uTexel * 5.0))));
    if (g < uGrain * 0.5) c = uShade;
    else if (g > 1.0 - uGrain * 0.3) c = uLit;
  }

  // DITHER — a checkerboard that thins out away from the face edge. This is the
  // retro value ramp: how the style darkens a corner without a gradient, and
  // the thing that most separates pixel art from flat-shaded polygons.
  if (uDither > 0.0) {
    float zone = 1.0 - clamp(d / uDitherSpan, 0.0, 1.0);
    if (mod(tex.x + tex.y, 2.0) < 0.5 && hash(tex + 19.7) < zone * 0.9) c = uShade;
  }

  // PERFORATION — a regular dot grid, for grilles and speaker cloth.
  if (uPerf > 0.0) {
    vec2 f = abs(fract(local / uPerf) - 0.5);
    if (max(f.x, f.y) < 0.26) c = uShade;
  }

  if (uWear > 0.0 && lim > uCell) {
    float h = hash(local / uCell);
    if (h < uWear) c = uShade;
    else if (h > 1.0 - uWear) c = uLit;
  }

  // SEAMS. A large face is subdivided into flat sub-panels rather than left as
  // one field — the style bible's surface-marks sheet is unambiguous about it.
  // Each seam is a dark line with a light catch under it, which is how the
  // edge-vocab sheet draws a horizontal joint. The seam count follows the size,
  // so a wider panel gets more sub-panels of the SAME size.
  if (axisFace && uSeam > 0.5) {
    vec2 n = floor(half2 / uSeamPitch);          // sub-panels along each axis
    for (int ax = 0; ax < 2; ax++) {
      float span = ax == 0 ? half2.x : half2.y;
      float p    = ax == 0 ? local.x : local.y;
      float k    = ax == 0 ? n.x : n.y;
      if (k < 1.0) continue;
      float pitch = span / (k + 1.0) * 2.0;
      float m = abs(mod(p + span, pitch) - pitch * 0.5);
      float e = pitch * 0.5 - m;                  // distance to nearest seam
      if (e < uSeamLine && d > uInsetAt) c = uShade;
      else if (e < uSeamLine * 2.0 && e > uSeamLine && d > uInsetAt) c = uLit;
    }
  }

  // The pressed-plate border. It needs room for the border AND a field inside
  // it, or it is just a second outline.
  if (axisFace && uInset > 0.5 && lim > uInsetAt + 1.0) {
    if (d > uInsetAt && d < uInsetAt + uInsetLine) c = uShade;
    else if (d > uInsetAt + uInsetLine && d < uInsetAt + uInsetLine * 2.0 && lit) c = uLit;
  }

  // The catch and the outline on the very rim. Both thin with the face once it
  // can no longer hold them at full width, so small trim keeps a hairline
  // instead of being eaten by its own border.
  float o = min(uOutline, lim * 0.34);
  float k = min(uCatch, lim * 0.34);
  if (axisFace && uEdge > 0.0) {
    if (d < o + k && d > o && lit) c = uLit;
    if (d < o) c = uShade;
  }

  // Baked per-face value — the whole shading model.
  //
  // WEIGHTED BY THE NORMAL rather than switched on it. A hard switch was fine
  // while every face was axis-aligned, but a 45-degree chamfer has |z| = 0.707,
  // so it tripped the same branch as the front face and came out the identical
  // value — the new facets existed in the mesh and were invisible in the image.
  // Weighting by |n| gives an axis face exactly its own tint (the other two
  // weights are zero) and a chamfer the blend of the two it sits between, which
  // is what makes an angled facet read at all.
  float tX = uSide;
  float tY = vNrm.y > 0.0 ? uTop : uBottom;
  float tZ = vNrm.z < 0.0 ? uFront : uBack;
  float t = (a.x * tX + a.y * tY + a.z * tZ) / max(0.001, a.x + a.y + a.z);

  // BAKED VERTEX SHADING. The PlayStation had no lighting at all: it shaded
  // with vertex colours, and the era's assets bake an ambient gradient into
  // them. The reference kit does exactly this - the lower half of every car
  // and dumpster is visibly darker than its top, with no light in the scene.
  // A single vertical ramp over the whole object buys most of that, and it is
  // per-vertex rather than per-face so it crosses part boundaries the way
  // baked AO does.
  float hgt = clamp((vWorldY - uObjLo) / max(1.0, uObjHi - uObjLo), 0.0, 1.0);
  t *= mix(uAOFloor, 1.0, smoothstep(0.0, 0.55, hgt));

  gl_FragColor = vec4(c * t, 1.0);
}
`;

// The surface atlas, set once at boot by loadSurfaces(). Held module-level so
// materials can be built lazily without every call site threading it through.
const SURF = { tex: null, man: null };

export function loadSurfaces(THREE, tex, manifest) {
  tex.magFilter = tex.minFilter = THREE.NearestFilter;
  tex.colorSpace = THREE.NoColorSpace;   // it is a mask, not colour
  tex.generateMipmaps = false;
  tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping;
  SURF.tex = tex;
  SURF.man = manifest;
}

// A tile's rect in the atlas, normalised, as the vec4 the shader reads.
// The tile's nine-slice margin in WORLD units, and the world period of one
// repeat of its middle — both derived from the tile's own texel counts so the
// mask always renders at exactly STYLE.texel per texel. Hand-setting these
// let the mask drift to roughly half the model's texel size, which is how the
// surface ended up finer than the geometry it sat on.
function sliceOf(name) {
  const t = SURF.man && name ? SURF.man.tiles[name] : null;
  if (!t) return { m: STYLE.marginWorld, p: STYLE.period };
  const n = SURF.man.texels;
  return { m: t.marginTexels * STYLE.texel,
           p: Math.max(STYLE.texel, (n - 2 * t.marginTexels) * STYLE.texel) };
}

function tileRect(THREE, name) {
  if (!name || !SURF.man) return new THREE.Vector4(0, 0, 0, 0);
  const [w, h] = SURF.man.size;
  const [rx, ry, rw, rh] = SURF.man.tiles[name].rect;
  return new THREE.Vector4(rx / w, ry / h, rw / w, rh / h);
}

export function makeMaterial(THREE, kind) {
  const name = ALIAS[kind] ?? kind;
  const m = MATERIALS[name];
  if (!m) throw new Error(`no material "${name}"`);
  const f = (v) => ({ value: v });
  return new THREE.ShaderMaterial({
    vertexShader: VERT,
    fragmentShader: FRAG,
    uniforms: {
      uBase: f(new THREE.Color(m.base)),
      uLit: f(new THREE.Color(m.lit ?? m.base)),
      uShade: f(new THREE.Color(m.shade ?? m.base)),
      uInset: f(m.inset), uWear: f(0), uEdge: f(m.edge), uSeam: f(m.seam),
      uFleck: f(m.fleck), uGrain: f(m.grain),
      uDither: f(m.dither), uPerf: f(m.perf),
      uTexel: f(STYLE.texel), uDitherSpan: f(STYLE.ditherSpan),
      uMask: f(SURF.tex), uTile: f(tileRect(THREE, m.surface)),
      uHasMask: f(m.surface && SURF.man ? 1 : 0),
      uMarginW: f(sliceOf(m.surface).m), uPeriod: f(sliceOf(m.surface).p),
      uTileMid: f(m.tileMid ? 1 : 0),
      uMarginF: f(m.surface && SURF.man
        ? SURF.man.tiles[m.surface].margin : 0.12),
      uCell: f(STYLE.wearCell),
      uOutline: f(m.edge || STYLE.outline),
      uCatch: f(STYLE.catch),
      uInsetAt: f(STYLE.inset), uInsetLine: f(STYLE.insetLine),
      uSeamPitch: f(STYLE.seam), uSeamLine: f(STYLE.seamLine),
      uObjLo: f(STYLE.objLo), uObjHi: f(STYLE.objHi), uAOFloor: f(STYLE.aoFloor),
      uTop: f(STYLE.tint.top), uFront: f(STYLE.tint.front),
      uSide: f(STYLE.tint.side), uBack: f(STYLE.tint.back),
      uBottom: f(STYLE.tint.bottom),
    },
  });
}

// Every colour the style can produce — each material's three tones at each face
// tint — thinned so near-duplicates collapse. Derived rather than typed, because
// typing a palette by hand is how the atlas grille once lost its tan and went
// grey. The post pass snaps to this, so a frame cannot hold a value nobody
// chose; the thinning also keeps it inside the snap loop's bound.
export function buildPalette(THREE, limit = 64) {
  const tints = Object.values(STYLE.tint);
  const cand = [];
  for (const m of Object.values(MATERIALS)) {
    for (const hex of [m.base, m.lit ?? m.base, m.shade ?? m.base]) {
      const c = new THREE.Color(hex);
      for (const t of tints) {
        cand.push([c.r, c.g, c.b].map((v) => Math.min(255, Math.round(v * 255 * t))));
      }
    }
  }
  cand.sort((a, b) => (a[0] + a[1] + a[2]) - (b[0] + b[1] + b[2]));
  let kept = [];
  for (let thresh = 6; ; thresh += 2) {
    kept = [];
    for (const c of cand) {
      if (kept.every((k) => Math.hypot(k[0] - c[0], k[1] - c[1], k[2] - c[2]) >= thresh)) {
        kept.push(c);
      }
    }
    if (kept.length <= limit) break;
  }
  return kept;
}

// ---------------------------------------------------------------------------
// SHAPED BOXES: bevel and taper.
//
// A study of the reference kit says the one thing it never does is leave a form
// as a plain prism. Its dumpster tapers inward toward the base, its lid slopes,
// its prominent vertical corner is cut by a narrow angled facet, and its rim
// overhangs with an angled underside. Everything here had been axis-aligned
// boxes, which is why it read as neat rather than as modelled.
//
//   bevel  a 45-degree facet cutting every edge, one chamfer wide
//   taper  the top narrowed relative to the bottom, in world units
//
// 44 triangles for a fully bevelled box: 6 face quads, 12 edge quads, 8 corner
// triangles. That is squarely in the reference's own budget - a whole door in
// that kit is 138.
//
// WINDING IS COMPUTED, NOT REASONED. Every triangle's normal is taken from its
// own cross product and flipped if it points inward, which is unambiguous for a
// convex solid centred on the origin. Enumerating 44 triangles by hand and
// getting each one's vertex order right is a guaranteed source of invisible
// inside-out faces, and the check costs nothing.
// `bevel` is a NUMBER for a uniform chamfer, or [bx, by, bz] to chamfer each
// axis by a different amount — which is what stops the bevel being a rule
// applied everywhere without asking what the part is. [1.6, 0, 1.6] rounds the
// four vertical edges and leaves the top and bottom crisp; [0.6, 3.4, 0.6]
// does the opposite, which is the profile of a fridge with a rounded shoulder
// and square sides. A single number everywhere reads as a soap bar.
export function shapedBox(THREE, sx, sy, sz, bevel = 0, taperX = 0, taperZ = 0) {
  const h = [sx / 2, sy / 2, sz / 2];
  const size = [sx, sy, sz];
  const raw = Array.isArray(bevel) ? bevel : [bevel, bevel, bevel];
  // Each inset is bounded by ITS OWN axis: bv[i] moves vertices along axis i,
  // so the only way to invert the solid is bv[i] >= size[i]/2. The clamp used
  // to be 0.34 * the min of the OTHER two axes, which is the wrong axis
  // entirely — it throttled a thin slice's horizontal bevel to 0.43 because the
  // slice was thin VERTICALLY, so a stacked cap could not match the corner
  // radius of the body it sat on and the join showed a step.
  const bv = raw.map((v, i) => Math.max(0, Math.min(v, 0.45 * size[i])));
  const b = Math.max(...bv);
  const V = (a, va, bb, vb, c, vc) => {
    const q = [0, 0, 0]; q[a] = va; q[bb] = vb; q[c] = vc; return q;
  };
  const tris = [];
  const quad = (p, q, r, t) => { tris.push([p, q, r], [p, r, t]); };

  for (let a = 0; a < 3; a++) {                      // 6 face quads
    const u = (a + 1) % 3, v = (a + 2) % 3;
    for (const s of [-1, 1]) {
      const P = (su, sv) =>
        V(a, s * h[a], u, su * (h[u] - bv[u]), v, sv * (h[v] - bv[v]));
      quad(P(-1, -1), P(1, -1), P(1, 1), P(-1, 1));
    }
  }
  // With no bevel the edge quads and corner triangles collapse to zero area —
  // but they are still emitted, still transformed, and still counted. Skipping
  // them is what actually makes `bevel: 0` cheap: 12 triangles instead of 44.
  // Without this the silhouette exemptions above changed nothing at all.
  if (b > 1e-4) {
  for (let a = 0; a < 3; a++) {                      // 12 edge quads
    for (let c = a + 1; c < 3; c++) {
      const o = 3 - a - c;
      for (const sa of [-1, 1]) for (const sc of [-1, 1]) {
        if (bv[a] < 1e-4 && bv[c] < 1e-4) continue;   // no chamfer on this edge
        quad(V(a, sa * h[a], c, sc * (h[c] - bv[c]), o, h[o] - bv[o]),
             V(a, sa * h[a], c, sc * (h[c] - bv[c]), o, -(h[o] - bv[o])),
             V(a, sa * (h[a] - bv[a]), c, sc * h[c], o, -(h[o] - bv[o])),
             V(a, sa * (h[a] - bv[a]), c, sc * h[c], o, h[o] - bv[o]));
      }
    }
  }
  }
  if (b > 1e-4)
  for (const sx_ of [-1, 1]) for (const sy_ of [-1, 1]) for (const sz_ of [-1, 1]) {
    // Each corner vertex lies on ONE original face and is inset by the bevel
    // on the OTHER TWO axes -- which is also exactly how the face quads and
    // edge quads name their corners, so the three meet. Insetting only one axis
    // per vertex (the obvious-looking version) puts these triangles somewhere
    // no other face reaches: holes at some corners, loose triangles floating
    // outside the silhouette at others. A vertex-bounds check cannot see that,
    // because every vertex is still inside the box; see the watertightness
    // check in the header note.
    tris.push([[sx_ * h[0], sy_ * (h[1] - bv[1]), sz_ * (h[2] - bv[2])],
               [sx_ * (h[0] - bv[0]), sy_ * h[1], sz_ * (h[2] - bv[2])],
               [sx_ * (h[0] - bv[0]), sy_ * (h[1] - bv[1]), sz_ * h[2]]]);
  }

  // Taper: narrow the top. Applied after the bevel so the two compose, and as a
  // vertex transform so no triangle has to know about it.
  const shape = (p) => {
    if (!taperX && !taperZ) return p;
    const t = (p[1] / h[1] + 1) * 0.5;               // 0 at the base, 1 at the top
    return [p[0] * (1 - (taperX / sx) * t * 2), p[1], p[2] * (1 - (taperZ / sz) * t * 2)];
  };

  const pos = [], nrm = [], half = [];
  const sub = (u, v) => [u[0] - v[0], u[1] - v[1], u[2] - v[2]];
  for (let [p, q, r] of tris) {
    [p, q, r] = [shape(p), shape(q), shape(r)];
    const e1 = sub(q, p), e2 = sub(r, p);
    let n = [e1[1] * e2[2] - e1[2] * e2[1],
             e1[2] * e2[0] - e1[0] * e2[2],
             e1[0] * e2[1] - e1[1] * e2[0]];
    const len = Math.hypot(...n) || 1;
    n = n.map((v) => v / len);
    const mid = [(p[0] + q[0] + r[0]) / 3, (p[1] + q[1] + r[1]) / 3, (p[2] + q[2] + r[2]) / 3];
    if (n[0] * mid[0] + n[1] * mid[1] + n[2] * mid[2] < 0) {
      [q, r] = [r, q];
      n = n.map((v) => -v);
    }
    for (const vtx of [p, q, r]) {
      pos.push(...vtx); nrm.push(...n); half.push(h[0], h[1], h[2]);
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3));
  geo.setAttribute('aHalf', new THREE.Float32BufferAttribute(half, 3));
  return geo;
}

// PS1-STYLE ROUNDING: a curve is a few flat steps, not a smooth surface.
//
// A single 45-degree chamfer gives a straight diagonal cut. A rounded shoulder
// like the reference fridge's needs the inset to grow non-linearly, and the era
// did that the only way it could — with two or three flat facets. This emits
// exactly that: a stack of slices, each inset by a measured amount.
//
// THE PROFILE IS MEASURED, NOT A FORMULA. The obvious move is a quarter circle,
// and the reference's top is not one: measured off it, the inset runs 0, 0.61,
// 1.33, 3.02 units over heights 0, 1.26, 2.52, 3.47 — nearly linear and then
// rolling off hard at the very top. Any arc formula fitted to the endpoints
// misses the middle by a third of the shoulder. So `profile` is a list of
// [height above the base, inset each side] read straight off the reference.
//
// `add` is the model's own add(), so the slices land in its group with its
// materials and every slice is a normal shapedBox — watertight, bevelled, and
// carrying the surface mask like anything else.
// Each entry is [height above the base, inset AT that height], and the slice
// reaching that height is drawn at that inset — so the silhouette passes
// through every measured point exactly. Using the PREVIOUS entry's inset (the
// obvious-looking version) shifts the whole profile down one step and drops the
// last one entirely, so the cap never reaches its measured top width.
//
// The slices carry NO vertical bevel. Bevelled on all three axes a 1.26-unit
// slice is mostly chamfer and reads as a separate rounded bar; the stack came
// out looking like a pile of pipes. Flat top and bottom faces let them meet
// flush, and the horizontal bevel alone rounds the corners.
export function capProfile(add, kind, hx, hy, zBase, profile, opts = {}) {
  let prevZ = 0, prevIn = 0;
  for (const [dz, inset] of profile) {
    // TAPERED, not stacked. A box slice has a flat TOP FACE, and a stack of
    // them shows that face as a horizontal ledge at every step — which is why
    // the first version read as a pile of slabs rather than a rounded top. A
    // frustum has no ledge: its side is one angled facet running from the inset
    // below it to the inset above, so consecutive slices form a continuous
    // surface broken only by a slight change of angle. That is what a
    // PlayStation-era rounded edge actually is — a few angled facets, not a few
    // steps. Three of them read as round; three steps read as geometry.
    //
    // taperX is expressed in half-width, and shapedBox narrows the top by
    // exactly that, so the amount is simply the change in inset.
    add(kind, [-(hx - prevIn), -(hy - prevIn), zBase + prevZ],
              [hx - prevIn, hy - prevIn, zBase + dz],
              { ...opts, taperX: inset - prevIn, taperZ: inset - prevIn });
    prevZ = dz; prevIn = inset;
  }
}

// A box from table coords [x1,y1,z1]-[x2,y2,z2] (Blender z-up, front -y) into
// three (y-up, front -z). aHalf carries the half-extents the shader needs.
export function tableBox(THREE, kind, [x1, y1, z1], [x2, y2, z2], cache, opts = {}) {
  const sx = x2 - x1, sy = z2 - z1, sz = y2 - y1;
  const name = ALIAS[kind] ?? kind;
  const m = MATERIALS[name] ?? {};
  const geo = shapedBox(THREE, sx, sy, sz,
    opts.bevel ?? m.bevel ?? STYLE.bevel,
    opts.taperX ?? 0, opts.taperZ ?? 0);
  if (cache && !cache.has(name)) cache.set(name, makeMaterial(THREE, kind));
  const mesh = new THREE.Mesh(geo, cache ? cache.get(name) : makeMaterial(THREE, kind));
  mesh.position.set((x1 + x2) / 2, (z1 + z2) / 2, (y1 + y2) / 2);
  return mesh;
}


// ---------------------------------------------------------------------------
// FITTINGS — the part that actually gives a model character.
//
// The style bible's character-ab sheet draws the same cabinet plain and
// finished. Both halves have perfectly FLAT fields; the whole difference is
// things placed ON them — a vent where air moves, a rating plate where you
// would read one, screws at the corners of each panel. That is why the
// procedural pass before this one failed: a hash spread over every face at 14%
// coverage is the opposite of character, because the placement IS the meaning,
// and a hash has no way to mean anything. It read as dirt, correctly.
//
// So detail comes from a small atlas of authored fittings, placed deliberately.
//
// HOW THIS STAYS PERFECTLY RESIZABLE. A decal is a quad of FIXED WORLD SIZE
// anchored to a face's own corner (or centre) with a world-unit offset. Widen
// the cabinet and the rating plate does not stretch and does not drift: it
// stays the same plate the same distance from the same corner, exactly as a
// nine-slice keeps its corners native. The UVs here are the decal's own — six
// vertices with a rect out of the atlas — and never the cabinet's, so there is
// no unwrap to stretch and no texel density to reconcile with the body.
//
// ANCHORS: 'c' centre, and any of tl tr bl br t b l r, measured in the face's
// own (u, v) with +u right and +v up as seen from outside that face.
const FACES = {
  front: { rot: [0, Math.PI, 0], put: (u, v, d) => [u, v, d] },
  back: { rot: [0, 0, 0], put: (u, v, d) => [u, v, d] },
  left: { rot: [0, -Math.PI / 2, 0], put: (u, v, d) => [d, v, u] },
  right: { rot: [0, Math.PI / 2, 0], put: (u, v, d) => [d, v, u] },
  top: { rot: [-Math.PI / 2, 0, 0], put: (u, v, d) => [u, d, v] },
};

export function loadFittings(THREE, tex, manifest) {
  tex.magFilter = tex.minFilter = THREE.NearestFilter;
  tex.colorSpace = THREE.NoColorSpace;   // colours are already output-ready
  tex.generateMipmaps = false;
  return { tex, man: manifest };
}

// One fitting, as its own quad. `h` is its world HEIGHT; the width follows the
// tile's aspect so a fitting is never squashed.
// `fit` is the face's half-extent in (u, v). Given it, the decal is nudged
// inward until it sits entirely on the face. Without it a fitting placed near
// an edge hangs off the geometry into thin air — a hinge anchored a fixed
// distance from a door's edge is wider than that distance, so half of it
// overhung the door and floated.
//
// It nudges rather than shrinks on purpose: a fitting is a FIXED WORLD SIZE, so
// scaling it to fit would silently break the one property the whole system is
// built on. If it genuinely cannot fit, it is placed flush and left overhanging,
// because a visibly wrong decal is better than a quietly resized one.
export function decal(THREE, kit, name, face, u, v, h, depth, tint = 1.0, fit = null) {
  const t = kit.man.tiles[name];
  if (!t) throw new Error(`no fitting "${name}"`);
  if (fit) {
    const hw = h * t.aspect / 2, hh = h / 2;
    if (fit.u != null) u = Math.max(-fit.u + hw, Math.min(fit.u - hw, u));
    if (fit.v != null) v = Math.max(-fit.v + hh, Math.min(fit.v - hh, v));
  }
  const [rx, ry, rw, rh] = t.rect;
  const [aw, ah] = kit.man.size;
  const geo = new THREE.PlaneGeometry(h * t.aspect, h);
  // Remap the quad's UVs onto this tile's rect. Half-texel inset, or nearest
  // filtering picks up the neighbouring tile along the shared edge.
  const uv = geo.attributes.uv;
  const e = 0.5;
  for (let i = 0; i < uv.count; i++) {
    uv.setXY(i,
      (rx + e + uv.getX(i) * (rw - 2 * e)) / aw,
      1 - (ry + e + (1 - uv.getY(i)) * (rh - 2 * e)) / ah);
  }
  uv.needsUpdate = true;
  const f = FACES[face];
  const mesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({
    map: kit.tex, transparent: true, alphaTest: 0.5,
    // Tinted to the face it sits on, so a fitting on a side panel darkens with
    // that panel instead of floating in front of it at full brightness.
    color: new THREE.Color(tint, tint, tint),
    // The quad sits a hair off the surface; polygonOffset keeps it there under
    // any camera without the gap becoming visible at a grazing angle.
    polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4,
  }));
  mesh.rotation.set(...f.rot);
  mesh.position.set(...f.put(u, v, depth));
  return mesh;
}

// Screws at the corners of a panel — the one fitting the reference applies as a
// RULE rather than a placement. character-ab puts them on every sub-panel it
// draws, always the same size, always the same inset from the corner. Inset is
// in world units, so a bigger panel gets its screws in the same place relative
// to its corners rather than proportionally further in.
export function screws(THREE, kit, face, cu, cv, halfU, halfV, depth,
                       inset = 1.6, size = 1.1, tint = 1.0, name = 'screwCross') {
  const out = [];
  for (const su of [-1, 1]) {
    for (const sv of [-1, 1]) {
      out.push(decal(THREE, kit, name, face,
        cu + su * (halfU - inset), cv + sv * (halfV - inset), size, depth, tint));
    }
  }
  return out;
}
