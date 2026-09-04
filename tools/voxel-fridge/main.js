// Voxel fridge prototype — matching the pixel-art reference by copying how the
// reference is AUTHORED.
//
//   geometry   axis-aligned boxes straight off the reference's FINAL IMMUTABLE
//              COORDINATE TABLE (Blender z-up, front -y → three y-up, front -z)
//   texturing  NONE. Detail is geometry and colour is a locked palette, which
//              is how the reference voxel kits do it and why they have none of
//              the texture problems this file used to be mostly about.
//   shading    baked, not lit: the face normal alone picks a tint factor.
//   output     rendered small and nearest-upscaled: the screen pixel grid IS
//              the texture grid.
//
// WHY THIS IS ADAPTABLE. There is nothing to stretch. Every piece of detail is
// its own box with its own size, so a border stays the width it was authored
// while the panel behind it grows, and a repeating feature is a loop over the
// current size rather than a texture that has to tile. The adaptability
// problem was never solved — it was deleted, by moving the detail out of the
// texture and into the geometry that was going to be there anyway.
//
//   ?w=<halfWidth>  body half-width (table value 22); try 40, or 28.5
//   ?yaw= ?pitch=   camera
import * as THREE from 'three';

const params = new URLSearchParams(location.search);
const H = Number(params.get('w') ?? 17);
const VIEWS = { front: [0, 0], side: [90, 0], back: [180, 0], iso: [30, 18] };
const [vYaw, vPitch] = VIEWS[params.get('view')] ?? VIEWS.iso;
const yaw = Number(params.get('yaw') ?? vYaw) * Math.PI / 180;
const pitch = Number(params.get('pitch') ?? vPitch) * Math.PI / 180;

const BG = '#efebe4';

// ---------------------------------------------------------------------------
// FLAT COLOUR, NO TEXTURES AT ALL.
//
// Every texture problem this prototype has had — texel density against render
// density, mip levels, which nine-slice zone a piece of detail may live in,
// sRGB round-tripping, a patch's pixel size dictating a part's world size —
// existed only because the detail was in a texture and the geometry was not.
// The reference voxel kits do not have those problems because they do not have
// textures: detail is geometry, colour is flat per surface.
//
// So detail is geometry here too. A recessed panel is a recessed BOX. That is
// adaptable for free, because the border is four thin boxes that keep their
// size while the middle grows, and it can never smear, because there is
// nothing to sample. What remains of the pixel-art look is done by the post
// pass, which was always the part carrying it.
export const PALETTE = {
  cream:    '#e9e3d4',
  cream2:   '#d8d1bf',   // the crown's lower step, a panel's shadowed reveal
  creamLit: '#f4efe2',   // a catch along a lit edge
  flank:    '#c3ced2',
  flank2:   '#aebac0',
  teal:     '#35785f',
  teal2:    '#2b6350',
  cavity:   '#357a67',
  shelf:    '#dbe9e4',
  glass:    '#bcd8d2',
  glint:    '#f2f8f6',
  tan:      '#d9a95f',
  tan2:     '#b8873f',
  slot:     '#3f3a33',
  purple:   '#5c4a70',
  purple2:  '#48395a',
  disp:     '#262b36',
  digit:    '#74de96',
  lamp:     '#e2894e',
};
// The part list's own names for the same colours, kept so a part says what it
// IS rather than which swatch it happens to use.
PALETTE.blueGrey = PALETTE.flank;
PALETTE.plinth = PALETTE.purple;
PALETTE.interior = PALETTE.cavity;
PALETTE.grille = PALETTE.tan;

const VERT = /* glsl */ `
varying vec3 vNrm;
void main() {
  vNrm = normal;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

const FRAG = /* glsl */ `
precision highp float;
uniform vec3 uColor;
uniform float uOpacity;
varying vec3 vNrm;
void main() {
  // Baked per-face value, exactly as the sheets paint it. This is the entire
  // shading model and it is three lines, because with flat colour there is
  // nothing else to compute.
  float t = 0.86;
  if (vNrm.y > 0.5)       t = 1.09;
  else if (vNrm.y < -0.5) t = 0.74;
  else if (vNrm.z < -0.5) t = 1.00;
  else if (vNrm.z > 0.5)  t = 0.90;
  gl_FragColor = vec4(uColor * t, uOpacity);
}
`;

// The exact set of colours this object can produce: every palette entry at
// every face tint. The post pass snaps to it, so the frame cannot contain a
// value nobody chose. Derived rather than authored, because deriving it by
// hand is how the grille lost its tan and went grey.
const TINTS = [1.09, 1.00, 0.90, 0.86, 0.74];
const paletteColours = [];
for (const hex of Object.values(PALETTE)) {
  const c = new THREE.Color(hex);
  for (const t of TINTS) {
    paletteColours.push(
      Math.min(255, Math.round(c.r * 255 * t)),
      Math.min(255, Math.round(c.g * 255 * t)),
      Math.min(255, Math.round(c.b * 255 * t)), 255);
  }
}
const paletteCount = paletteColours.length / 4;
const paletteTexture = new THREE.DataTexture(
  new Uint8Array(paletteColours), paletteCount, 1, THREE.RGBAFormat);
paletteTexture.magFilter = paletteTexture.minFilter = THREE.NearestFilter;
paletteTexture.needsUpdate = true;

const MATS = new Map();
function matFor(kind) {
  if (!MATS.has(kind)) {
    const hex = PALETTE[kind];
    if (!hex) throw new Error(`no palette entry "${kind}"`);
    const glassy = kind === 'glass';
    MATS.set(kind, new THREE.ShaderMaterial({
      vertexShader: VERT,
      fragmentShader: FRAG,
      transparent: glassy,
      depthWrite: !glassy,
      uniforms: {
        uColor: { value: new THREE.Color(hex) },
        uOpacity: { value: glassy ? 0.30 : 1 },
      },
    }));
  }
  return MATS.get(kind);
}

// ---------------------------------------------------------------------------
// a box from table coords [x1,y1,z1]-[x2,y2,z2] (Blender, z-up, front = -y)
function tableBox(kind, [x1, y1, z1], [x2, y2, z2]) {
  const sx = x2 - x1, sy = z2 - z1, sz = y2 - y1; // Blender z → three y
  const geo = new THREE.BoxGeometry(sx, sy, sz);
  const mesh = new THREE.Mesh(geo, matFor(kind));
  mesh.position.set((x1 + x2) / 2, (z1 + z2) / 2, (y1 + y2) / 2);
  mesh.renderOrder = kind === 'glass' ? 10 : 0;
  return mesh;
}

// ---------------------------------------------------------------------------
function buildFridge(H) {
  const g = new THREE.Group();
  const add = (kind, a, b) => g.add(tableBox(kind, a, b));
  // MEASURED OFF THE DRAWN SHEET, not the coordinate table. The table's 44x96
  // is 1:2.18; the reference's own FRONT view is 290x780 px = 1:2.7, its crown
  // is 11% of the height and its glass 72% of the width. PARTS.md says the
  // drawn views win where the two disagree, so the body is 2H = 32 against 96.
  // MEASURED ACROSS THE SHEET'S FRONT VIEW, band by band. Its cream border is
  // 15.5% of the width on EACH side, the teal door frame 4%, and the glass 61%
  // between them. An earlier pass widened the glass to 74% and left a 4.7%
  // cream strip, which is why the door sprawled and the frame vanished: the
  // vertical proportions were already right and the whole error was here.
  const W = H - 1;        // carcass / base half-width      (100%)
  const S = W - 5;        // inside the flanks: cavity, shelves, door opening
  const G = W - 6.5;      // glass half-width               (~61%)

  // ---- P01 feet: four corner blocks, outer faces flush with the base -------
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    const x1 = sx > 0 ? W - 6 : -W, x2 = sx > 0 ? W : -(W - 6);
    const y1 = sy > 0 ? 9 : -14, y2 = sy > 0 ? 14 : -9;
    add('plinth', [x1, y1, -1.5], [x2, y2, 3.5]);
  }
  add('plinth', [-(W - 1), -13, 0],   [W - 1, 13, 4]);      // P02 plinth strip
  add('teal',   [-W, -14, 4],         [W, 14, 18]);         // P03 condenser base
  // P04 grille — real louvres now, not a picture of louvres. The slot count
  // follows the width, so a wider base gets MORE slots at the same pitch: the
  // adaptive behaviour that used to need a tiling texture, done with a loop.
  add('tan',  [-(W - 5), -15.2, 7.5], [W - 5, -14.0, 11.5]);
  add('tan2', [-(W - 5), -15.4, 7.5], [W - 5, -15.2, 11.5]);
  for (let z = 8.2; z < 11.2; z += 1.1) {
    add('slot', [-(W - 6), -15.5, z], [W - 6, -15.1, z + 0.6]);
  }
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {     // P05 corner blocks
    const x1 = sx > 0 ? W - 3 : -W, x2 = sx > 0 ? W : -(W - 3);
    const y1 = sy > 0 ? 10 : -14, y2 = sy > 0 ? 14 : -10;
    add('cream', [x1, y1, 13], [x2, y2, 18]);
  }

  // ---- P06 flanks, split at the carcass joint ------------------------------
  for (const sx of [-1, 1]) {
    const x1 = sx > 0 ? S : -W, x2 = sx > 0 ? W : -S;
    add('blueGrey', [x1, -14, 18], [x2, 14, 50]);
    add('blueGrey', [x1, -14, 52], [x2, 14, 84]);
    // The joint needs a rail. Left as an open 2-unit gap it showed the dark
    // cavity straight through, and SIDE and BACK both read a green stripe
    // across the flank.
    add('cream',    [x1, -14.2, 50], [x2, 14.2, 52]);
  }
  // ---- P07 back, same joint -----------------------------------------------
  add('blueGrey', [-W, 11, 18], [W, 14, 50]);
  add('blueGrey', [-W, 11, 52], [W, 14, 84]);
  add('cream',    [-W, 11, 50], [W, 14.2, 52]);
  add('cream',    [-W, -14, 80], [W, 14, 84]);              // top run

  // ---- P09 cavity: five dark faces ----------------------------------------
  add('interior', [-S, 8, 18],        [S, 11, 80]);
  add('interior', [-S, -14, 18],      [-(S - 1.5), 8, 80]);
  add('interior', [S - 1.5, -14, 18], [S, 8, 80]);
  add('interior', [-S, -14, 18],      [S, 8, 20]);
  add('interior', [-S, -14, 78],      [S, 8, 80]);
  for (const z of [29, 41, 53, 65]) add('shelf', [-S, -10, z], [S, 1, z + 2.5]);  // P10

  // ---- P08 corner posts ---------------------------------------------------
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    const x1 = sx > 0 ? W - 2 : -W, x2 = sx > 0 ? W : -(W - 2);
    const y1 = sy > 0 ? 12 : -14, y2 = sy > 0 ? 14 : -12;
    add('cream', [x1, y1, 18], [x2, y2, 84]);
  }

  // ---- P15 crown: 11% of height, a lip and one block ----------------------
  // BOTH crown pieces overhang the body, and their heights are close: a top
  // block narrower than the carcass and twice the lip's height read as a lid
  // resting on the cabinet rather than as its cap.
  add('cream', [-H, -15, 84],           [H, 15, 88]);
  add('cream', [-(H - 0.5), -14.5, 88], [H - 0.5, 14.5, 93]);

  // ---- P11/P12 door: a wide light between two NARROW borders ---------------
  const frame = (kind, xIn, xOut, zLo, zHi, y1, y2) => {
    add(kind, [-xOut, y1, zLo], [-xIn, y2, zHi]);
    add(kind, [xIn, y1, zLo],   [xOut, y2, zHi]);
    add(kind, [-xOut, y1, zHi - (xOut - xIn)], [xOut, y2, zHi]);
    add(kind, [-xOut, y1, zLo], [xOut, y2, zLo + (xOut - xIn)]);
  };
  frame('cream', S, W, 20, 82, -15.5, -12);
  frame('teal',  G, S, 22, 80, -16.5, -15.5);
  // P13 glass — NOT a transparent pane. Alpha blending produces colours that
  // are in no palette, so the snap sent them to whatever grey was nearest and
  // the door went dead. The sheet does not draw a pane either: you see the
  // interior directly, with a reflection drawn ON it. So the pane is gone and
  // the reflection is a staircase of small boxes, which is how pixel art draws
  // a diagonal and costs nothing here.
  for (let i = 0; i < 9; i++) {
    add('glint', [G - 5 - i * 1.6, -16.4, 66 - i * 2.4],
                 [G - 3 - i * 1.6, -16.2, 69 - i * 2.4]);
  }
  // ---- P14 handle ---------------------------------------------------------
  add('purple', [W - 3.5, -18.6, 41], [W - 1, -17.2, 63]);
  add('purple', [W - 3, -17.2, 42],   [W - 1.5, -16.2, 45]);
  add('purple', [W - 3, -17.2, 59],   [W - 1.5, -16.2, 62]);
  // P16 display — geometry, not a decal. Exactly one, at the centre, at any
  // width: the case a tiling texture fundamentally cannot express.
  add('disp',  [-5.5, -15.7, 87.5], [5.5, -15.0, 91.5]);
  add('lamp',  [-4.0, -15.9, 89.0], [-2.5, -15.6, 90.0]);
  add('digit', [-1.0, -15.9, 89.0], [3.5, -15.6, 90.0]);
  return g;
}

// ---------------------------------------------------------------------------
// One screen pixel per texel. viewH units tall at texelsPerUnit px per unit is
// the only ratio at which a nearest-sampled pixel-art sheet stays crisp: above
// it the sheet aliases, below it the sheet blurs.
const viewH = 116, viewW = viewH * (0.56 + Math.max(0, (H - 17) * 0.030));
// Pixels per world unit. With no texture there is no texel density to match,
// so this is a free choice: it sets how chunky the pixels are, nothing more.
// The reference draws its 96-unit cabinet about 850 px tall, so 8 is its own.
const PPU = Number(params.get('ppu') ?? 8);
const Hpx = Math.round(viewH * PPU);
const W = Math.round(viewW * PPU);
const renderer = new THREE.WebGLRenderer({ antialias: false });
renderer.outputColorSpace = THREE.LinearSRGBColorSpace; // see atlas.colorSpace
renderer.setSize(W, Hpx, false);
renderer.domElement.style.width = W + 'px';
renderer.domElement.style.height = Hpx + 'px';
// ?bg= overrides the clear colour. Measuring the render against the normal
// cream ground silently classified the cream door frame AS ground - the two
// are within a few values of each other - and reported a frame three times
// thinner than it is. A contrasting ground makes the silhouette unambiguous.
renderer.setClearColor(new THREE.Color(params.get('bg') ?? BG));
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();

// ?carved=<url> builds from a voxel_carve.py result instead of buildFridge().
// Every box is a flat colour lifted from the reference views, so this is the
// carve shown raw - no atlas, no nine-slice, nothing of mine between the
// reference and the screen.
const carvedUrl = params.get('carved');
if (carvedUrl) {
  const data = await (await fetch(carvedUrl)).json();
  const [gw, gd, gh] = data.grid;
  const g = new THREE.Group();
  const mats = new Map();
  for (const b of data.boxes) {
    const [x0, y0, z0] = b.min, [x1, y1, z1] = b.max;
    const geo = new THREE.BoxGeometry(x1 - x0, z1 - z0, y1 - y0);
    let m = mats.get(b.colour);
    if (!m) {
      m = new THREE.MeshBasicMaterial({ color: new THREE.Color(b.colour) });
      mats.set(b.colour, m);
    }
    const mesh = new THREE.Mesh(geo, m);
    mesh.position.set((x0 + x1) / 2 - gw / 2, (z0 + z1) / 2, (y0 + y1) / 2 - gd / 2);
    g.add(mesh);
  }
  console.info(`carved: ${data.boxes.length} boxes, ${mats.size} colours, grid ${gw}x${gd}x${gh}`);
  scene.add(g);
} else {
  scene.add(buildFridge(H));
}

const target = new THREE.Vector3(0, 47, 0);
const cam = new THREE.OrthographicCamera(-viewW / 2, viewW / 2, viewH / 2, -viewH / 2, 1, 1000);
const d = 400;
cam.position.set(
  target.x - d * Math.sin(yaw) * Math.cos(pitch),
  target.y + d * Math.sin(pitch),
  target.z - d * Math.cos(yaw) * Math.cos(pitch)
);
cam.lookAt(target);

// ---------------------------------------------------------------------------
// THE POST PASS — the two stages that separate a 3D render from pixel art.
// Rendering small with nearest filtering is necessary and not sufficient; the
// literature on 3D-to-pixel-art is consistent that you also need
//
//   PALETTE QUANTISATION  snap every pixel to a small locked palette, or the
//                         frame carries hundreds of near-identical values that
//                         no pixel artist would ever have drawn
//   AN EDGE PASS          a dark outline at depth and normal discontinuities.
//                         Hand-drawn pixel art outlines every form; a renderer
//                         separates forms by value alone, which is the single
//                         biggest reason ours read as "a render of a fridge"
//                         rather than "pixel art of a fridge".
//
// Disable either with ?post=0 to see the difference.
const usePost = params.get('post') !== '0';
const rtColor = new THREE.WebGLRenderTarget(W, Hpx, {
  minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter,
  depthTexture: new THREE.DepthTexture(W, Hpx),
});
const rtNormal = new THREE.WebGLRenderTarget(W, Hpx, {
  minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter,
});

const post = new THREE.ShaderMaterial({
  uniforms: {
    tColor: { value: rtColor.texture },
    tNormal: { value: rtNormal.texture },
    tDepth: { value: rtColor.depthTexture },
    tPalette: { value: paletteTexture },
    uPaletteSize: { value: carvedUrl ? 0 : paletteCount },
    uTexel: { value: new THREE.Vector2(1 / W, 1 / Hpx) },
    uOutline: { value: 0.55 },   // how far an edge darkens its own colour
    uNormalEdge: { value: 0.20 },
    uDepthEdge: { value: 0.0012 },
  },
  vertexShader: `
    varying vec2 vUv;
    void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }
  `,
  fragmentShader: /* glsl */ `
    precision highp float;
    uniform sampler2D tColor, tNormal, tDepth, tPalette;
    uniform vec2 uTexel;
    uniform float uPaletteSize, uOutline, uNormalEdge, uDepthEdge;
    varying vec2 vUv;

    void main() {
      vec3 c = texture2D(tColor, vUv).rgb;
      vec3 n0 = texture2D(tNormal, vUv).rgb;
      float d0 = texture2D(tDepth, vUv).r;

      // Four-neighbour discontinuity test. A normal break catches the join
      // between two faces of one object; a depth break catches the silhouette
      // and one part standing in front of another.
      float edge = 0.0;
      for (int i = 0; i < 4; i++) {
        vec2 o = i == 0 ? vec2(1.0, 0.0) : i == 1 ? vec2(-1.0, 0.0)
               : i == 2 ? vec2(0.0, 1.0) : vec2(0.0, -1.0);
        vec2 uv = vUv + o * uTexel;
        edge = max(edge, step(uNormalEdge, length(texture2D(tNormal, uv).rgb - n0)));
        edge = max(edge, step(uDepthEdge, abs(texture2D(tDepth, uv).r - d0)));
      }
      // Darken the pixel's OWN colour rather than stamping one ink: a single
      // black outline over a cream cabinet and a teal base reads as ink, where
      // pixel art shades its outline from the form it belongs to.
      c = mix(c, c * uOutline, edge);

      // Snap to the palette. Nearest in RGB is crude but correct for a palette
      // this small and this deliberately spaced. Size 0 passes through: a
      // carved model brings its OWN colours, lifted from the reference views,
      // and snapping those to this object's palette turned the cabinet dark.
      if (uPaletteSize < 0.5) { gl_FragColor = vec4(c, 1.0); return; }
      vec3 best = c;
      float bestD = 1e9;
      for (int i = 0; i < 128; i++) {
        if (float(i) >= uPaletteSize) break;
        vec3 p = texture2D(tPalette, vec2((float(i) + 0.5) / uPaletteSize, 0.5)).rgb;
        float dd = distance(p, c);
        if (dd < bestD) { bestD = dd; best = p; }
      }
      gl_FragColor = vec4(best, 1.0);
    }
  `,
});
const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), post);
const postScene = new THREE.Scene().add(quad);
const postCam = new THREE.Camera();

if (usePost) {
  renderer.setRenderTarget(rtColor);
  renderer.render(scene, cam);
  scene.overrideMaterial = new THREE.MeshNormalMaterial();
  renderer.setRenderTarget(rtNormal);
  renderer.render(scene, cam);
  scene.overrideMaterial = null;
  renderer.setRenderTarget(null);
  renderer.render(postScene, postCam);
} else {
  renderer.render(scene, cam);
}
window.__done = true;
