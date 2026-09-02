// Voxel fridge prototype — an exact-match attempt at the pixel-art vaccine
// fridge reference, built the way the reference's own texture kit is built:
//
//   geometry   every part is an axis-aligned box straight off the FINAL
//              IMMUTABLE COORDINATE TABLE (Blender units, z-up, front = -y;
//              mapped here to y-up, front = -z)
//   texturing  every face gets a canvas composited at exactly 32 px per unit
//              from named LAYERS: a tileable centre fill, bevel edge strips,
//              fixed corner islands (bolts), and fixed decals (display,
//              grille, glass streak). Centres tile with size; corners and
//              decals never scale — which is what makes the object adaptable.
//   shading    baked, not lit. The sheet paints its shading per face (front
//              brightest, sides cooler/darker, top lifted), so every material
//              is unlit and the face orientation picks a tint factor.
//   output     rendered small and CSS-upscaled with nearest so the screen
//              grid matches the reference's pixel grid.
//
// ?w=<halfWidth> overrides the body half-width (table value 22). Corners,
// bolts, the display and the handle stay put; centre fields and the grille's
// slot row tile wider. That is the "layers of details, fixed corners" demo.
import * as THREE from 'three';

const PX = 32; // texture pixels per Blender unit — the kit's own grid

// ---------------------------------------------------------------------------
// palette, read off the multi-view sheet
const C = {
  bg:          '#efebe4',
  cream:       '#ede4d3', // painted metal, front
  creamTop:    '#f4eddd',
  creamSide:   '#d8cebb',
  creamLine:   '#c7baa3', // bevel dark
  creamLite:   '#faf5e9', // bevel light
  outline:     '#8f8471', // soft dark outline on cream parts
  blueGrey:    '#c6cfd4', // side panels
  blueGreySide:'#b3bec5',
  blueGreyLine:'#98a5ad',
  bolt:        '#5a646e',
  teal:        '#4e8672', // base / condenser / door inner frame
  tealSide:    '#417460',
  tealLine:    '#2f5b4b',
  tealLite:    '#63997f',
  interior:    '#1f4a40', // cavity: the darkest thing on the object
  interiorDk:  '#173a32',
  shelf:       '#c3d0c9',
  shelfEdge:   '#9fb0a8',
  glass:       '#c9d6d9',
  streak:      '#eef4f2',
  grilleTan:   '#d9a75f',
  grilleDark:  '#b1813f',
  slot:        '#3f3a33',
  purple:      '#5a4966', // handle
  purpleDk:    '#443852', // plinth
  purpleLine:  '#332a3e',
  dispBg:      '#262b36',
  dispFrame:   '#4a3e58',
  dispGreen:   '#74de96',
  dispOrange:  '#e2894e',
};

// per-face tint: the sheet's baked shading
const FACE_TINT = { front: 1.0, back: 0.92, right: 0.90, left: 0.90, top: 1.05, bottom: 0.82 };

function tint(hex, f) {
  const n = parseInt(hex.slice(1), 16);
  const ch = (s) => Math.max(0, Math.min(255, Math.round(((n >> s) & 255) * f)));
  return `rgb(${ch(16)},${ch(8)},${ch(0)})`;
}

// ---------------------------------------------------------------------------
// the layer compositor
function faceTexture(wUnits, hUnits, layers) {
  const w = Math.max(2, Math.round(wUnits * PX));
  const h = Math.max(2, Math.round(hUnits * PX));
  const cv = document.createElement('canvas');
  cv.width = w; cv.height = h;
  const ctx = cv.getContext('2d');
  ctx.imageSmoothingEnabled = false;
  for (const layer of layers) layer(ctx, w, h);
  const tex = new THREE.CanvasTexture(cv);
  tex.magFilter = THREE.NearestFilter;
  tex.minFilter = THREE.NearestFilter;
  tex.generateMipmaps = false;
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

// --- layers ---------------------------------------------------------------
const fill = (c) => (ctx, w, h) => { ctx.fillStyle = c; ctx.fillRect(0, 0, w, h); };

// pixel-art bevel: dark outline, light inner top+left, dark inner bottom+right.
// The width scales with the face and is capped, because a fixed 6 px band eats
// a small part whole — that is what made the crown read as three stacked slabs
// instead of one moulded cap.
const bevel = (lite, dark, line, want = 5) => (ctx, w, h) => {
  const px = Math.max(2, Math.min(want, Math.floor(Math.min(w, h) / 6)));
  ctx.fillStyle = line;
  ctx.fillRect(0, 0, w, px); ctx.fillRect(0, h - px, w, px);
  ctx.fillRect(0, 0, px, h); ctx.fillRect(w - px, 0, px, h);
  ctx.fillStyle = lite;
  ctx.fillRect(px, px, w - 2 * px, px);
  ctx.fillRect(px, px, px, h - 2 * px);
  ctx.fillStyle = dark;
  ctx.fillRect(px, h - 2 * px, w - 2 * px, px);
  ctx.fillRect(w - 2 * px, px, px, h - 2 * px);
};

// sparse speckle, like the kit's tileable centres: a few 1-2px flecks only
const speckle = (c, n = 6, seed = 7) => (ctx, w, h) => {
  let s = seed;
  const rnd = () => ((s = (s * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);
  ctx.fillStyle = c;
  for (let i = 0; i < n; i++) {
    const px = 4 + Math.floor(rnd() * 3) * 2;
    ctx.fillRect(Math.floor(rnd() * (w - 8)), Math.floor(rnd() * (h - 8)), px, px);
  }
};

// fixed corner islands: the side panels' corner bolts
const cornerBolts = (c, inset = 20, size = 10) => (ctx, w, h) => {
  ctx.fillStyle = c;
  for (const x of [inset, w - inset - size])
    for (const y of [inset, h - inset - size]) ctx.fillRect(x, y, size, size);
};

// the grille: fixed end caps, slot rows tiled horizontally between them
const grilleLayer = () => (ctx, w, h) => {
  const cap = 30, rowH = 14, gap = 12;
  ctx.fillStyle = C.grilleDark;                     // frame shade
  ctx.fillRect(0, 0, w, h);
  ctx.fillStyle = C.grilleTan;
  ctx.fillRect(6, 6, w - 12, h - 12);
  const rows = 4, top = Math.floor((h - rows * rowH - (rows - 1) * gap) / 2);
  for (let r = 0; r < rows; r++) {
    const y = top + r * (rowH + gap);
    // dashes tile between the fixed caps; a wider grille gets more dashes
    const span = w - 2 * cap, dashW = 96, dashGap = 14;
    const n = Math.max(1, Math.floor((span + dashGap) / (dashW + dashGap)));
    const used = n * dashW + (n - 1) * dashGap;
    let x = cap + Math.floor((span - used) / 2);
    ctx.fillStyle = C.slot;
    for (let i = 0; i < n; i++) { ctx.fillRect(x, y, dashW, rowH); x += dashW + dashGap; }
  }
};

// temperature display decal: dark field, orange dot, green "4C" pixel digits
const displayLayer = () => (ctx, w, h) => {
  const pad = Math.max(3, Math.round(h * 0.12));
  ctx.fillStyle = C.dispFrame; ctx.fillRect(0, 0, w, h);
  ctx.fillStyle = C.dispBg; ctx.fillRect(pad, pad, w - 2 * pad, h - 2 * pad);
  const cell = Math.max(2, Math.floor((h - 2 * pad) / 7));
  ctx.fillStyle = C.dispOrange;
  ctx.fillRect(pad + cell, Math.floor(h / 2) - cell, cell * 2, cell * 2);
  const glyphs = {
    '4': [[1,0,1],[1,0,1],[1,1,1],[0,0,1],[0,0,1]],
    'C': [[1,1,1],[1,0,0],[1,0,0],[1,0,0],[1,1,1]],
  };
  ctx.fillStyle = C.dispGreen;
  let gx = pad + cell * 4;
  for (const g of ['4', 'C']) {
    const rows = glyphs[g];
    const gy = Math.floor(h / 2) - Math.floor((rows.length * cell) / 2);
    rows.forEach((row, ry) => row.forEach((v, rx) => {
      if (v) ctx.fillRect(gx + rx * cell, gy + ry * cell, cell, cell);
    }));
    gx += 4 * cell;
  }
};

// glass: translucent pale field with the kit's fixed diagonal streak
const glassLayer = () => (ctx, w, h) => {
  ctx.fillStyle = C.glass; ctx.fillRect(0, 0, w, h);
  ctx.fillStyle = C.streak;
  const step = 22;
  for (let i = 0; i < 10; i++) ctx.fillRect(w * 0.62 - i * step, h * 0.06 + i * step, step * 1.6, step);
  for (let i = 0; i < 6; i++) ctx.fillRect(w * 0.80 - i * step, h * 0.10 + i * step, step, step);
};

// ---------------------------------------------------------------------------
// material builders per surface kind; face ∈ front|back|left|right|top|bottom
function mat(kind, face, wU, hU) {
  const f = FACE_TINT[face];
  const L = [];
  const base = (c, lite, dark, line, extra = []) => {
    L.push(fill(tint(c, f)), ...extra, bevel(tint(lite, f), tint(dark, f), tint(line, f)));
  };
  switch (kind) {
    case 'cream':
      base(C.cream, C.creamLite, C.creamSide, C.creamLine, [speckle(tint(C.creamSide, f), 4)]);
      break;
    case 'blueGrey':
      base(C.blueGrey, '#dde4e8', C.blueGreySide, C.blueGreyLine, [speckle(tint(C.blueGreySide, f), 5)]);
      L.push(cornerBolts(tint(C.bolt, f)));
      break;
    case 'teal':
      base(C.teal, C.tealLite, C.tealSide, C.tealLine, [speckle(tint(C.tealSide, f), 5, 13)]);
      break;
    case 'purple':
      base(C.purple, '#6f5c7d', '#4a3b54', C.purpleLine);
      break;
    case 'plinth':
      base(C.purpleDk, '#544566', '#382e46', C.purpleLine);
      break;
    case 'interior':
      L.push(fill(tint(C.interior, f)), bevel(tint(C.interior, f), tint(C.interiorDk, f), tint(C.interiorDk, f)));
      break;
    case 'shelf':
      base(C.shelf, '#e6eae6', '#b9c3bd', C.shelfEdge);
      break;
    case 'grille':
      if (face === 'front') L.push(grilleLayer());
      else base(C.grilleTan, C.grilleTan, C.grilleDark, C.grilleDark);
      break;
    case 'display':
      if (face === 'front') L.push(displayLayer());
      else base(C.dispFrame, C.dispFrame, '#3a3046', '#3a3046');
      break;
    case 'glass':
      L.push(glassLayer());
      break;
    case 'gasket':
      base(C.tealLine, C.tealSide, C.tealLine, C.tealLine);
      break;
  }
  const tex = faceTexture(wU, hU, L);
  return new THREE.MeshBasicMaterial({
    map: tex,
    transparent: kind === 'glass',
    opacity: kind === 'glass' ? 0.20 : 1,
    depthWrite: kind !== 'glass',
  });
}

// a box from table coords [x1,y1,z1]-[x2,y2,z2] (Blender, z-up, front = -y)
function tableBox(kind, [x1, y1, z1], [x2, y2, z2]) {
  const sx = x2 - x1, sy = z2 - z1, sz = y2 - y1; // Blender z → three y
  const geo = new THREE.BoxGeometry(sx, sy, sz);
  // three material order: +x right, -x left, +y top, -y bottom, +z back, -z front
  const mats = [
    mat(kind, 'right', sz, sy), mat(kind, 'left', sz, sy),
    mat(kind, 'top', sx, sz), mat(kind, 'bottom', sx, sz),
    mat(kind, 'back', sx, sy), mat(kind, 'front', sx, sy),
  ];
  const mesh = new THREE.Mesh(geo, mats);
  mesh.position.set((x1 + x2) / 2, (z1 + z2) / 2, (y1 + y2) / 2);
  return mesh;
}

// ---------------------------------------------------------------------------
// the fridge, parametric in half-width H (table value 22). Every x extent is
// written relative to H with the table's insets, so widening keeps the frame,
// bolts and display fixed while the centre fields and grille slots tile.
function buildFridge(H = 22) {
  const g = new THREE.Group();
  const add = (kind, a, b) => g.add(tableBox(kind, a, b));

  add('plinth',   [-(H - 2), -13, 0],  [H - 2, 13, 4]);                 // PLINTH
  add('teal',     [-(H - 2), -14, 4],  [H - 2, 14, 18]);                // CONDENSER
  // CARCASS as a shell open at the front: two sides, top, and cavity liner
  add('blueGrey', [-(H - 2), -14, 18], [-(H - 8), 14, 84]);             // left side
  add('blueGrey', [H - 8, -14, 18],    [H - 2, 14, 84]);                // right side
  add('cream',    [-(H - 8), -14, 80], [H - 8, 14, 84]);                // top run
  // The cavity is a five-sided dark shell, not a single back panel. Looking
  // through glass into a pale void was what made the door read as a flat sheet
  // rather than as a window into a cold cabinet.
  add('interior', [-(H - 8), 10, 18],   [H - 8, 13, 80]);               // back
  add('interior', [-(H - 8), -14, 18],  [-(H - 9.5), 10, 80]);          // left liner
  add('interior', [H - 9.5, -14, 18],   [H - 8, 10, 80]);               // right liner
  add('interior', [-(H - 8), -14, 18],  [H - 8, 10, 20]);               // floor
  add('interior', [-(H - 8), -14, 78],  [H - 8, 10, 80]);               // ceiling
  // shelves: X ±(H-8), Y -10..10, Z 29/41/53/65, thickness 2
  // Shallower than the table's y range: at any angle above dead-on, a full-depth
  // shelf shows so much pale top face that it fills the cavity and the fridge
  // stops reading as a dark cold box with pale slabs in it.
  for (const z of [29, 41, 53, 65]) add('shelf', [-(H - 8), -10, z], [H - 8, 1, z + 1.5]);
  // Fixed cream corner posts (texture kit layer 4). Two units square whatever
  // the cabinet's width, which is exactly the point: corners never scale.
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    const x1 = sx > 0 ? H - 4 : -(H - 2), x2 = sx > 0 ? H - 2 : -(H - 4);
    const y1 = sy > 0 ? 12 : -14, y2 = sy > 0 ? 14 : -12;
    add('cream', [x1, y1, 18], [x2, y2, 84]);
  }
  // crown stack
  add('cream', [-H, -15, 84],       [H, 15, 88]);                       // CROWN_LOWER
  add('cream', [-(H - 3), -12, 88], [H - 3, 12, 94]);                   // CROWN_TOP
  // front frames, built as bars so the cavity shows through the glass
  const frame = (kind, xIn, xOut, zLo, zHi, y1, y2) => {
    add(kind, [-xOut, y1, zLo], [-xIn, y2, zHi]);                       // left bar
    add(kind, [xIn, y1, zLo],   [xOut, y2, zHi]);                       // right bar
    add(kind, [-xOut, y1, zHi - (xOut - xIn)], [xOut, y2, zHi]);        // head
    add(kind, [-xOut, y1, zLo], [xOut, y2, zLo + (xOut - xIn)]);        // foot
  };
  // Thinner stiles and a much bigger light. The first pass stacked a fat cream
  // frame on a fat teal frame and left a porthole; on the sheet the glass is
  // roughly 60% of the door width and the frames read as two slim borders.
  frame('cream', H - 6, H - 3, 20, 82, -15.5, -12);                     // OUTER_FRAME
  frame('teal',  H - 8, H - 6, 22, 80, -16.5, -15.5);                   // DOOR_FRAME
  add('glass',   [-(H - 8), -16.4, 24], [H - 8, -16.2, 78]);            // GLASS
  // HANDLE: vertical bar standing proud of the door's outer stile, with two
  // stubs bridging back to it. Mirrored from the table's x so it lands on the
  // same screen edge as the sheet's ISO, which is drawn from the other side.
  add('purple', [H - 5, -18.6, 43],  [H - 2, -17.2, 61]);
  add('purple', [H - 4.5, -17.2, 44], [H - 3, -16.2, 47]);
  add('purple', [H - 4.5, -17.2, 57], [H - 3, -16.2, 60]);
  // DISPLAY on the crown, fixed size and position whatever the width
  add('display', [0, -15.5, 84.8], [11, -14.9, 88.2]);
  // GRILLE on the condenser front
  add('grille', [-(H - 7), -15, 8], [H - 7, -14, 15]);
  // plinth feet, like the sheet's corner blocks
  for (const s of [-1, 1]) add('plinth', [s * (H - 2) - (s > 0 ? 4 : 0), -14, 0], [s * (H - 2) + (s > 0 ? 0 : 4), -10, 3]);
  return g;
}

// ---------------------------------------------------------------------------
const params = new URLSearchParams(location.search);
const H = Number(params.get('w') ?? 22);
const yaw = Number(params.get('yaw') ?? 30) * Math.PI / 180;
const pitch = Number(params.get('pitch') ?? 18) * Math.PI / 180;

const W = 380 + Math.max(0, (H - 22) * 10), Hpx = 500;
const renderer = new THREE.WebGLRenderer({ antialias: false });
renderer.setSize(W, Hpx, false);
renderer.domElement.style.width = W * 2 + 'px';
renderer.domElement.style.height = Hpx * 2 + 'px';
renderer.setClearColor(new THREE.Color(C.bg));
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.add(buildFridge(H));

const target = new THREE.Vector3(0, 48, 0);
const viewH = 118, viewW = viewH * W / Hpx;
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
