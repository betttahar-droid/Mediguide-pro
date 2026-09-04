// Voxel fridge prototype — matching the pixel-art reference by copying how the
// reference is AUTHORED.
//
//   geometry   axis-aligned boxes straight off the reference's FINAL IMMUTABLE
//              COORDINATE TABLE (Blender z-up, front -y → three y-up, front -z)
//   texturing  ONE hand-authored atlas (make_atlas.py), sampled with NINE-SLICE
//              UV math driven by the fragment's position on its own face. The
//              atlas kit labels itself: tileable centres, FIXED corners and edge
//              strips, FIXED decal islands. That is a nine-slice sprite kit, so
//              the renderer treats it as one.
//   shading    baked, not lit. The sheet paints shading per face, so materials
//              are unlit and the face normal alone picks a tint factor.
//   output     rendered small and nearest-upscaled: the screen pixel grid IS
//              the texture grid.
//
// WHY THIS IS ADAPTABLE. Nothing samples a UV attribute, so nothing can be
// stretched by scaling geometry. A fragment asks "how many texels am I from my
// own face's edge?", and the nine-slice map answers with a corner texel if it
// is in the fixed ring and a tiling centre texel otherwise. Grow a part and its
// corners stay native size while its centre tiles further — at any size,
// including fractional ones, with no per-size canvases and no UV work.
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
// A GENERATED sheet wins over the hand-authored one. import_atlas.py writes
// atlas-nano.* from a Nano Banana kit sheet; when those exist the renderer
// uses them and make_atlas.py's output becomes the fallback. Nothing else in
// the renderer changes, because the manifest is the whole interface.
const base = '/tools/voxel-fridge/';
async function loadAtlas() {
  for (const name of ['atlas-nano', 'atlas']) {
    // A dev server answers a MISSING file with index.html and a 200, so
    // response.ok is not evidence the manifest exists. Parse it and check it
    // is actually a manifest.
    let manifest;
    try {
      const r = await fetch(base + name + '.json');
      if (!r.ok) continue;
      manifest = await r.json();
      if (!manifest || !manifest.surfaces) continue;
    } catch { continue; }
    const tex = await new THREE.TextureLoader().loadAsync(base + name + '.png');
    console.info('atlas:', name);
    return [manifest, tex];
  }
  throw new Error('no atlas found — run make_atlas.py or import_atlas.py');
}
const [man, atlas] = await loadAtlas();

// The palette the post pass snaps to. Pixel art is a small locked set of
// colours; a 3D render is not, because every face tint multiplies every texel
// into a new value. nano_atlas.py derives this from the atlas at each face
// tint and reduces it to 32.
const palette = await new THREE.TextureLoader().loadAsync(base + 'palette.png');
palette.magFilter = palette.minFilter = THREE.NearestFilter;
palette.generateMipmaps = false;
palette.colorSpace = THREE.NoColorSpace;
atlas.magFilter = THREE.NearestFilter;
atlas.minFilter = THREE.NearestFilter;
atlas.generateMipmaps = false;
// NO colour management. A stock ShaderMaterial does not get three's output
// colour-space conversion appended, so a texture tagged sRGB is decoded to
// linear on sample and then written straight out — everything landed markedly
// darker than authored, which is why the mid-teal base was reading near-black.
// For flat pixel art the honest setup is raw texels in, raw texels out: what
// make_atlas.py writes is exactly what appears on screen, times the face tint.
atlas.colorSpace = THREE.NoColorSpace;
atlas.wrapS = atlas.wrapT = THREE.ClampToEdgeWrapping;
// three flips images on upload by default, which puts v=0 at the BOTTOM of the
// PNG. The manifest's rects are top-down pixel coordinates straight out of the
// authoring script, so the flip has to go: without it every sample lands in the
// sheet's dark background and the whole object renders black.
atlas.flipY = false;

// ---------------------------------------------------------------------------
// the nine-slice sampler
const VERT = /* glsl */ `
attribute vec3 aHalf;      // this box's half-extents, so one material serves many
varying vec3 vLocal;
varying vec3 vHalf;
varying vec3 vNrm;
void main() {
  vLocal = position;
  vHalf = aHalf;
  vNrm = normal;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

const FRAG = /* glsl */ `
precision highp float;
uniform sampler2D uAtlas;
uniform vec2 uAtlasSize;
uniform vec4 uRect;        // patch x, y, w, h in atlas pixels
uniform float uCorner;     // fixed ring width in atlas pixels
uniform vec2 uTile;        // per axis: 1 tile the middle, 0 clamp it
uniform float uTexels;     // texels per world unit
uniform float uOpacity;
varying vec3 vLocal;
varying vec3 vHalf;
varying vec3 vNrm;

// One axis of the nine-slice map, all in TEXELS.
//   p        how far along this face we are, 0..faceLen
//   faceLen  the face's length
//   corner   the fixed ring — never scales
//   srcLen   the patch's length in the atlas
// Inside a corner we read straight through; past it we tile the middle. The
// corner is clamped to half the face so a small part degrades to "all corner"
// rather than reading the middle backwards.
float sliceAxis(float p, float faceLen, float corner, float srcLen, float tile) {
  float c = min(corner, floor(faceLen * 0.5));
  if (p < c) return p;                       // start corner, native size
  float fromEnd = faceLen - p;
  if (fromEnd < c) return srcLen - fromEnd;  // end corner, native size
  float mid = max(srcLen - 2.0 * c, 1.0);
  // CLAMP: hold one line of the patch's middle for the whole span. Uniform
  // field, no repeat, no seam - the right answer for an axis whose pattern
  // must not recur (a plain band, or the grille's fixed row of slots).
  if (tile < 0.5) return c + floor(mid * 0.5);
  return c + mod(p - c, mid);                // TILE: repeat the middle
}

void main() {
  // Faces are axis-aligned and flat-shaded, so the dominant normal axis picks
  // the two in-plane axes with no blending and therefore no seams.
  // Each face needs a signed basis, not just a pair of axes: without the sign
  // the two faces of an axis mirror each other, and the temperature display
  // came out reading backwards on the one face anybody looks at.
  vec3 a = abs(vNrm);
  vec2 local, half2;
  if (a.x > a.y && a.x > a.z) {
    local = vec2((vNrm.x > 0.0 ? -1.0 : 1.0) * vLocal.z, vLocal.y); half2 = vHalf.zy;
  } else if (a.y > a.z) {
    local = vec2(vLocal.x, (vNrm.y > 0.0 ? -1.0 : 1.0) * vLocal.z); half2 = vHalf.xz;
  } else {
    local = vec2((vNrm.z > 0.0 ? 1.0 : -1.0) * vLocal.x, vLocal.y); half2 = vHalf.xy;
  }

  vec2 faceLen = half2 * 2.0 * uTexels;
  vec2 p = (local + half2) * uTexels;

  vec2 src = vec2(
    sliceAxis(p.x, faceLen.x, uCorner, uRect.z, uTile.x),
    sliceAxis(p.y, faceLen.y, uCorner, uRect.w, uTile.y)
  );
  // +0.5 lands on the texel centre; without it the nearest fetch straddles a
  // boundary and the sheet shimmers by a pixel as the object moves.
  vec2 uv = (uRect.xy + vec2(src.x, uRect.w - src.y) + 0.5) / uAtlasSize;
  vec4 texel = texture2D(uAtlas, uv);

  // Baked shading: the reference paints it per face, so the normal alone picks
  // the value. There are no lights in this scene at all.
  // Spread wider than before. With the textures now flat, per-face value is
  // the ONLY thing separating one form from the next, so it has to carry the
  // whole job the painted bevel rings were doing badly.
  float t = 0.86;
  if (vNrm.y > 0.5)       t = 1.09;
  else if (vNrm.y < -0.5) t = 0.74;
  else if (vNrm.z < -0.5) t = 1.00;
  else if (vNrm.z > 0.5)  t = 0.90;

  gl_FragColor = vec4(texel.rgb * t, texel.a * uOpacity);
}
`;

function surfaceMaterial(name, { opacity = 1 } = {}) {
  const s = man.surfaces[name] ?? man.decals[name];
  if (!s) throw new Error(`atlas has no surface "${name}"`);
  return new THREE.ShaderMaterial({
    vertexShader: VERT,
    fragmentShader: FRAG,
    transparent: opacity < 1,
    depthWrite: opacity >= 1,
    uniforms: {
      uAtlas: { value: atlas },
      uAtlasSize: { value: new THREE.Vector2(man.size[0], man.size[1]) },
      uRect: { value: new THREE.Vector4(s.rect[0], s.rect[1], s.rect[2], s.rect[3]) },
      uCorner: { value: s.corner ?? 1e6 }, // a decal is "all corner": never tiles
      uTile: { value: new THREE.Vector2(...(s.tile ?? [1, 1])) },
      uTexels: { value: man.texelsPerUnit },
      uOpacity: { value: opacity },
    },
  });
}

const MATS = {};
const matFor = (kind) => (MATS[kind] ??= surfaceMaterial(kind, { opacity: kind === 'glass' ? 0.12 : 1 }));

// ---------------------------------------------------------------------------
// a box from table coords [x1,y1,z1]-[x2,y2,z2] (Blender, z-up, front = -y)
function tableBox(kind, [x1, y1, z1], [x2, y2, z2]) {
  const sx = x2 - x1, sy = z2 - z1, sz = y2 - y1; // Blender z → three y
  const geo = new THREE.BoxGeometry(sx, sy, sz);
  const n = geo.attributes.position.count;
  const half = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    half[i * 3] = sx / 2; half[i * 3 + 1] = sy / 2; half[i * 3 + 2] = sz / 2;
  }
  geo.setAttribute('aHalf', new THREE.BufferAttribute(half, 3));
  const mesh = new THREE.Mesh(geo, matFor(kind));
  mesh.position.set((x1 + x2) / 2, (z1 + z2) / 2, (y1 + y2) / 2);
  mesh.renderOrder = kind === 'glass' ? 10 : 0;
  return mesh;
}

// THE RULE THIS SYSTEM RUNS ON: an atlas patch's pixel size IS its world size,
// at texelsPerUnit. A tiling surface may be any size along an axis it tiles on,
// but must match the patch on an axis it does not; and a FIXED decal has no
// tiling centre at all, so its geometry size must come FROM the atlas. Sizing a
// decal by hand reads outside its own rect and renders garbage — which is
// exactly what a hand-placed 11-unit-wide display did on the first attempt.
function decalBox(name, cx, y, cz, depth = 0.6) {
  const r = (man.decals[name] ?? man.surfaces[name]).rect;
  const w = r[2] / man.texelsPerUnit, h = r[3] / man.texelsPerUnit;
  return tableBox(name, [cx - w / 2, y, cz - h / 2], [cx + w / 2, y + depth, cz + h / 2]);
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
  add('grille', [-(W - 5), -15.2, 8], [W - 5, -14, 11]);    // P04 grille
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
  add('glass',   [-G, -16.4, 24], [G, -16.2, 78]);          // P13
  // ---- P14 handle ---------------------------------------------------------
  add('purple', [W - 3.5, -18.6, 41], [W - 1, -17.2, 63]);
  add('purple', [W - 3, -17.2, 42],   [W - 1.5, -16.2, 45]);
  add('purple', [W - 3, -17.2, 59],   [W - 1.5, -16.2, 62]);
  g.add(decalBox('display', 0, -15.6, 89));                 // P16
  return g;
}

// ---------------------------------------------------------------------------
// One screen pixel per texel. viewH units tall at texelsPerUnit px per unit is
// the only ratio at which a nearest-sampled pixel-art sheet stays crisp: above
// it the sheet aliases, below it the sheet blurs.
const viewH = 116, viewW = viewH * (0.56 + Math.max(0, (H - 17) * 0.030));
const Hpx = Math.round(viewH * man.texelsPerUnit);
const W = Math.round(viewW * man.texelsPerUnit);
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
scene.add(buildFridge(H));

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
    tPalette: { value: palette },
    uPaletteSize: { value: man.paletteSize ?? 32 },
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
      // this small and this deliberately spaced.
      vec3 best = c;
      float bestD = 1e9;
      for (int i = 0; i < 64; i++) {
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
