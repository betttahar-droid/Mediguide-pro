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
  texel: 1.0,
  ditherSpan: 5.0,   // how far the corner dither reaches in from a face edge

  // NINE-SLICE, for the surface mask tiles.
  //   marginWorld  how many WORLD units the tile's authored border occupies.
  //                Fixed, so the border and its bolts stay native at any size.
  //                Sized to the measured plate border: 5 of 40 texels over 2.6
  //                units is ~0.52 units a texel, matching the object's own grid.
  //   period       world length of one repeat of the tile's middle. 16 units
  //                across the tile's ~30 remaining texels keeps that same
  //                texel size, so margin and middle read as one grid.
  marginWorld: 2.6,
  period: 16.0,
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
            fleck: 0, grain: 0, dither: 0, perf: 0, surface: null };
const M = (o) => ({ ...D, ...o });

export const MATERIALS = {
  cream:    M({ base: '#e9e3d4', lit: '#f7f2e6', shade: '#dcd6c6', surface: 'plate' }),
  blueGrey: M({ base: '#adb6ba', lit: '#b7c2c5', shade: '#a3adb2', surface: 'plate2' }),
  teal:     M({ base: '#377c62', lit: '#3f8a6d', shade: '#2e6752', surface: 'plateSeam' }),
  frame:    M({ base: '#35785f', lit: '#3a8368', shade: '#2e6752', edge: 0.14, surface: 'trim' }),
  purple:   M({ base: '#5c4a70', lit: '#6b5780', shade: '#4a3e58', edge: 0.16 }),
  plinth:   M({ base: '#5c4a72', lit: '#6b5780', shade: '#4a3e58', edge: 0.16 }),
  interior: M({ base: '#458574', lit: '#4c8978', shade: '#3b7565', edge: 0.16 }),
  shelf:    M({ base: '#d7e7e2', lit: '#deebe6', shade: '#bed2cc', edge: 0.10 }),
  glint:    M({ base: '#5c9c88', lit: '#6aa896', shade: '#4c8978', edge: 0 }),
  tan:      M({ base: '#d9a95f', lit: '#e8bc76', shade: '#c08c45', edge: 0.14, grain: 0.30 }),
  tan2:     M({ base: '#c08c45', lit: '#d9a95f', shade: '#8e6529', edge: 0 }),
  slot:     M({ base: '#3f3a33', lit: '#4a4439', shade: '#20242b', edge: 0 }),
  disp:     M({ base: '#262b36', lit: '#333a48', shade: '#171b23', perf: 1.0, surface: 'recess' }),
  digit:    M({ base: '#74de96', lit: '#9bf0b4', shade: '#4fb673', edge: 0 }),
  lamp:     M({ base: '#e2894e', lit: '#f5a56d', shade: '#b96a37', edge: 0 }),
};

// Part names a model may use that map onto a material above.
export const ALIAS = {
  grille: 'tan', flank: 'blueGrey', cavity: 'interior', glass: 'glint',
};

export const VERT = /* glsl */ `
attribute vec3 aHalf;
varying vec3 vLocal, vHalf, vNrm;
void main() {
  vLocal = position; vHalf = aHalf; vNrm = normal;
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
uniform float uHasMask, uMarginW, uMarginF, uPeriod;
uniform float uOutline, uCatch, uInsetAt, uInsetLine, uSeamPitch, uSeamLine;
uniform float uTop, uFront, uSide, uBack, uBottom;
varying vec3 vLocal, vHalf, vNrm;

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
  return mf + fract((d - mw) / period) * (1.0 - 2.0 * mf);
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

  vec3 c = uBase;

  // ==== SURFACE MASK ========================================================
  // The atlas carries STRUCTURE, the material carries COLOUR. Each texel is one
  // of three levels — shade / base / lit — so a single "plate" tile renders
  // correctly on cream, teal and blue-grey alike, and no colour ever leaves the
  // texture. That is what keeps the frame snappable to a locked palette, and it
  // is the thing a colour atlas cannot do.
  if (uHasMask > 0.5) {
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
  if (uSeam > 0.5) {
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
  if (uInset > 0.5 && lim > uInsetAt + 1.0) {
    if (d > uInsetAt && d < uInsetAt + uInsetLine) c = uShade;
    else if (d > uInsetAt + uInsetLine && d < uInsetAt + uInsetLine * 2.0 && lit) c = uLit;
  }

  // The catch and the outline on the very rim. Both thin with the face once it
  // can no longer hold them at full width, so small trim keeps a hairline
  // instead of being eaten by its own border.
  float o = min(uOutline, lim * 0.34);
  float k = min(uCatch, lim * 0.34);
  if (uEdge > 0.0) {
    if (d < o + k && d > o && lit) c = uLit;
    if (d < o) c = uShade;
  }

  // Baked per-face value — the whole shading model.
  float t = uSide;
  if (vNrm.y > 0.5)       t = uTop;
  else if (vNrm.y < -0.5) t = uBottom;
  else if (vNrm.z < -0.5) t = uFront;
  else if (vNrm.z > 0.5)  t = uBack;
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
      uMarginW: f(STYLE.marginWorld), uPeriod: f(STYLE.period),
      uMarginF: f(m.surface && SURF.man
        ? SURF.man.tiles[m.surface].margin : 0.12),
      uCell: f(STYLE.wearCell),
      uOutline: f(m.edge || STYLE.outline),
      uCatch: f(STYLE.catch),
      uInsetAt: f(STYLE.inset), uInsetLine: f(STYLE.insetLine),
      uSeamPitch: f(STYLE.seam), uSeamLine: f(STYLE.seamLine),
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

// A box from table coords [x1,y1,z1]-[x2,y2,z2] (Blender z-up, front -y) into
// three (y-up, front -z). aHalf carries the half-extents the shader needs.
export function tableBox(THREE, kind, [x1, y1, z1], [x2, y2, z2], cache) {
  const sx = x2 - x1, sy = z2 - z1, sz = y2 - y1;
  const geo = new THREE.BoxGeometry(sx, sy, sz);
  const n = geo.attributes.position.count;
  const half = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    half[i * 3] = sx / 2; half[i * 3 + 1] = sy / 2; half[i * 3 + 2] = sz / 2;
  }
  geo.setAttribute('aHalf', new THREE.BufferAttribute(half, 3));
  const name = ALIAS[kind] ?? kind;
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
export function decal(THREE, kit, name, face, u, v, h, depth, tint = 1.0) {
  const t = kit.man.tiles[name];
  if (!t) throw new Error(`no fitting "${name}"`);
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
