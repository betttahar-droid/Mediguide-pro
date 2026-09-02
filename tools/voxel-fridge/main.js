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
const H = Number(params.get('w') ?? 22);
const VIEWS = { front: [0, 0], side: [90, 0], back: [180, 0], iso: [30, 18] };
const [vYaw, vPitch] = VIEWS[params.get('view')] ?? VIEWS.iso;
const yaw = Number(params.get('yaw') ?? vYaw) * Math.PI / 180;
const pitch = Number(params.get('pitch') ?? vPitch) * Math.PI / 180;

const BG = '#efebe4';
const man = await (await fetch('/tools/voxel-fridge/atlas.json')).json();
const atlas = await new THREE.TextureLoader().loadAsync('/tools/voxel-fridge/atlas.png');
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
const matFor = (kind) => (MATS[kind] ??= surfaceMaterial(kind, { opacity: kind === 'glass' ? 0.17 : 1 }));

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

  // P02 plinth strip: inset, so the base overhangs it
  add('plinth',   [-(H - 2), -13, 0],  [H - 2, 13, 4]);
  // P03 condenser base
  add('teal',     [-(H - 2), -14, 4],  [H - 2, 14, 18]);
  // Carcass sides are SLIM. At six units they ate a third of the front and the
  // cabinet read squat; the sheet gives the glass roughly three quarters of the
  // width and keeps the frame to a narrow border.
  // P06: the sides are TWO stacked panels with a joint at z 50-52. SIDE and
  // BACK both show that seam at the same height, so it runs right round the
  // cabinet — a real carcass joint, not a mark on one face. Splitting it also
  // gives each half its own inset plate, which is what the sheet draws.
  add('blueGrey', [-(H - 2), -14, 18], [-(H - 6), 14, 50]);
  add('blueGrey', [-(H - 2), -14, 52], [-(H - 6), 14, 84]);
  add('blueGrey', [H - 6, -14, 18],    [H - 2, 14, 50]);
  add('blueGrey', [H - 6, -14, 52],    [H - 2, 14, 84]);
  add('cream',    [-(H - 2), -14.2, 50], [-(H - 6), 14.2, 52]);         // seam rail
  add('cream',    [H - 6, -14.2, 50],    [H - 2, 14.2, 52]);
  add('cream',    [-(H - 6), -14, 80], [H - 6, 14, 84]);                // top run
  // THE EXTERIOR BACK. Without it the back view looked straight into the dark
  // cavity liner, where the sheet's BACK is a pale panel in a cream frame.
  // P07: same split, same heights
  add('blueGrey', [-(H - 2), 11, 18],  [H - 2, 14, 50]);
  add('blueGrey', [-(H - 2), 11, 52],  [H - 2, 14, 84]);
  add('cream',    [-(H - 2), 11, 50],  [H - 2, 14.2, 52]);              // seam rail
  // five-sided dark cavity: seen through glass, a pale void reads as a flat sheet
  add('interior', [-(H - 6), 8, 18],   [H - 6, 11, 80]);
  add('interior', [-(H - 6), -14, 18], [-(H - 7.5), 8, 80]);
  add('interior', [H - 7.5, -14, 18],  [H - 6, 8, 80]);
  add('interior', [-(H - 6), -14, 18], [H - 6, 8, 20]);
  add('interior', [-(H - 6), -14, 78], [H - 6, 8, 80]);
  // P10: 2.5 thick. At 1.5 the front edge was too thin to read as a band in
  // FRONT, which is the view the sheet leads with.
  for (const z of [29, 41, 53, 65]) add('shelf', [-(H - 6), -10, z], [H - 6, 1, z + 2.5]);
  // fixed cream corner posts — the kit's "PROTECTED CORNERS", two units square
  // whatever the cabinet's width, which is exactly the point
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    const x1 = sx > 0 ? H - 4 : -(H - 2), x2 = sx > 0 ? H - 2 : -(H - 4);
    const y1 = sy > 0 ? 12 : -14, y2 = sy > 0 ? 14 : -12;
    add('cream', [x1, y1, 18], [x2, y2, 84]);
  }
  // A slim two-step moulding with a small overhang. Ours was a 6-unit top slab
  // inset only 3, which shows a big bright top face at any pitch and reads as a
  // separate box sitting on the cabinet rather than as its cap.
  add('cream', [-(H - 0.5), -14.5, 84], [H - 0.5, 14.5, 87]);           // CROWN_LOWER
  add('cream', [-(H - 2.5), -12.5, 87], [H - 2.5, 12.5, 91]);           // CROWN_TOP

  const frame = (kind, xIn, xOut, zLo, zHi, y1, y2) => {
    add(kind, [-xOut, y1, zLo], [-xIn, y2, zHi]);
    add(kind, [xIn, y1, zLo],   [xOut, y2, zHi]);
    add(kind, [-xOut, y1, zHi - (xOut - xIn)], [xOut, y2, zHi]);
    add(kind, [-xOut, y1, zLo], [xOut, y2, zLo + (xOut - xIn)]);
  };
  frame('cream', H - 4, H - 2, 20, 82, -15.5, -12);                     // OUTER_FRAME
  frame('teal',  H - 6, H - 4, 22, 80, -16.5, -15.5);                   // DOOR_FRAME
  add('glass',   [-(H - 6), -16.4, 24], [H - 6, -16.2, 78]);            // GLASS
  add('purple', [H - 3.5, -18.6, 41], [H - 1, -17.2, 63]);              // HANDLE
  add('purple', [H - 3, -17.2, 42],   [H - 1.5, -16.2, 45]);
  add('purple', [H - 3, -17.2, 59],   [H - 1.5, -16.2, 62]);
  // FIXED DECALS — the same pixel size at every cabinet width, sized by the
  // atlas rather than by hand
  g.add(decalBox('display', 0, -15.6, 86.4));
  // The grille tiles on x only, so its height must equal the patch height:
  // 96 px / 32 = 3 units. Left at 7 units it tiled vertically too and the slots
  // collapsed into a fine mesh.
  add('grille',  [-(H - 7), -15.2, 8], [H - 7, -14, 11]);
  // Cream corner blocks capping the base, front and back. They read clearly in
  // the sheet's FRONT and ISO views and are what stops the base reading as a
  // plain teal slab the cabinet happens to stand on.
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    const x1 = sx > 0 ? H - 5 : -(H - 2), x2 = sx > 0 ? H - 2 : -(H - 5);
    const y1 = sy > 0 ? 10 : -14, y2 = sy > 0 ? 14 : -10;
    add('cream', [x1, y1, 13], [x2, y2, 18]);   // P05
  }
  // Four distinct feet, one per corner, standing proud of the plinth strip.
  // Two stubs at the front only read as a purple band across the bottom.
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    // P01: outer faces flush with the base, not inset — the ISO view is
    // explicit about this, and inset feet read as castors rather than blocks.
    const x1 = sx > 0 ? H - 8 : -(H - 2), x2 = sx > 0 ? H - 2 : -(H - 8);
    const y1 = sy > 0 ? 9 : -14, y2 = sy > 0 ? 14 : -9;
    add('plinth', [x1, y1, -1.5], [x2, y2, 3.5]);
  }
  return g;
}

// ---------------------------------------------------------------------------
// One screen pixel per texel. viewH units tall at texelsPerUnit px per unit is
// the only ratio at which a nearest-sampled pixel-art sheet stays crisp: above
// it the sheet aliases, below it the sheet blurs.
const viewH = 116, viewW = viewH * (0.72 + Math.max(0, (H - 22) * 0.024));
const Hpx = Math.round(viewH * man.texelsPerUnit);
const W = Math.round(viewW * man.texelsPerUnit);
const renderer = new THREE.WebGLRenderer({ antialias: false });
renderer.outputColorSpace = THREE.LinearSRGBColorSpace; // see atlas.colorSpace
renderer.setSize(W, Hpx, false);
renderer.domElement.style.width = W + 'px';
renderer.domElement.style.height = Hpx + 'px';
renderer.setClearColor(new THREE.Color(BG));
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
renderer.render(scene, cam);
window.__done = true;
