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
const H = Number(params.get('w') ?? 16);   // BODY half-width; everything else
                                           // is a measured fraction of it
const VIEWS = { front: [0, 0], side: [90, 0], back: [180, 0], iso: [30, 18] };
const [vYaw, vPitch] = VIEWS[params.get('view')] ?? VIEWS.iso;
const yaw = Number(params.get('yaw') ?? vYaw) * Math.PI / 180;
const pitch = Number(params.get('pitch') ?? vPitch) * Math.PI / 180;

// The reference sheet's own card ground. A cream ground against a cream
// cabinet is what once let a measurement classify the door frame AS
// background; this is warmer and greyer, and separates the silhouette.
const BG = '#dcd4c6';

// ---------------------------------------------------------------------------
// MATERIALS AND SHADING LIVE IN style.js, which knows nothing about fridges.
// This file is now only GEOMETRY: a list of boxes with material names. That
// split is the point — a second model imports the same module and gets the
// identical look with no art work, and a style change lands on every object at
// once. See style.js for the technique and where each constant was measured.
import { STYLE, MATERIALS, buildPalette, tableBox, useRawColours } from './style.js';

// Before any THREE.Color exists — see style.js. The authored hex is the
// output pixel; nothing here wants a linear round trip.
useRawColours(THREE);

const paletteRGB = buildPalette(THREE);
const paletteCount = paletteRGB.length;
const paletteTexture = new THREE.DataTexture(
  new Uint8Array(paletteRGB.flatMap((c) => [...c, 255])), paletteCount, 1,
  THREE.RGBAFormat);
paletteTexture.magFilter = paletteTexture.minFilter = THREE.NearestFilter;
paletteTexture.needsUpdate = true;
console.info(`palette: ${paletteCount} colours, ${Object.keys(MATERIALS).length} materials`);

const MATS = new Map();

// ---------------------------------------------------------------------------
function buildFridge(H) {
  const g = new THREE.Group();
  const add = (kind, a, b) => g.add(tableBox(THREE, kind, a, b, MATS));
  // MEASURED OFF THE DRAWN SHEET, band by band, against the sheet's own card
  // ground. The front view's body is 240 px wide and 749 px tall (1:2.75), and
  // across it: cream door border 21 px, teal door frame 5 px, glass 188 px,
  // frame 5, border 21. As fractions of the body: border 8.75% a side, frame
  // 2.1%, glass 78%. The crown runs 270 px = 1.125x the body.
  //
  // These replace hand-typed offsets that had the border at 15.5% and the glass
  // at 61% — nearly double and two thirds respectively, which is why the door
  // read as a narrow slot in a wide cream slab. The earlier note claiming a 74%
  // glass "sprawled" was itself the mis-measurement: 78% is what the sheet says.
  // Written as fractions rather than magic numbers so a re-measure is a one-line
  // change and so every proportion survives a change of H.
  const W = H;                 // body half-width — the 100% everything is of
  const BORDER = W * 0.175;    // cream door border, each side
  const FRAME = W * 0.042;     // teal door frame, each side
  const S = W - BORDER;        // inside the border: cavity, shelves, opening
  const G = S - FRAME;         // glass half-width (78% of the body)
  const C = W * 1.13;          // crown half-width — it overhangs the body
  const GR = W * 0.70;         // grille half-width (70% of the body, measured)
  // Depth, from the SIDE view the same way: its body runs 230 px against the
  // front's 240, so the cabinet is very nearly square in plan. It had been
  // hard-coded at 14 against a half-width of 16 — 12% too shallow, which is the
  // sort of error that only ever reads as "the iso view looks a bit off".
  const D = W * 0.958;         // body half-depth
  const F = -D;                // the body's FRONT face; everything on the door
                               // is placed relative to it, so a depth change
                               // moves the door with the cabinet
  const CF = -(D + 0.5);       // the crown's front face — it overhangs too

  // ---- P01 feet: four corner blocks, outer faces flush with the base -------
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    const x1 = sx > 0 ? W - 6 : -W, x2 = sx > 0 ? W : -(W - 6);
    const y1 = sy > 0 ? D - 5 : -D, y2 = sy > 0 ? D : -(D - 5);
    add('plinth', [x1, y1, -1.5], [x2, y2, 3.5]);
  }
  add('plinth', [-(W - 1), -(D - 1), 0], [W - 1, D - 1, 4]); // P02 plinth strip
  add('teal',   [-W, -D, 4],             [W, D, 18]);        // P03 condenser base
  // P04 grille — real louvres now, not a picture of louvres. The slot count
  // follows the width, so a wider base gets MORE slots at the same pitch: the
  // adaptive behaviour that used to need a tiling texture, done with a loop.
  add('tan',  [-GR, F - 1.2, 7.5], [GR, F, 11.5]);
  add('tan2', [-GR, F - 1.4, 7.5], [GR, F - 1.2, 11.5]);
  for (let z = 8.2; z < 11.2; z += 1.1) {
    add('slot', [-(GR - 1), F - 1.5, z], [GR - 1, F - 1.1, z + 0.6]);
  }
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {     // P05 corner blocks
    const x1 = sx > 0 ? W - 3 : -W, x2 = sx > 0 ? W : -(W - 3);
    const y1 = sy > 0 ? D - 4 : -D, y2 = sy > 0 ? D : -(D - 4);
    add('cream', [x1, y1, 13], [x2, y2, 18]);
  }

  // ---- P06 flanks, split at the carcass joint ------------------------------
  for (const sx of [-1, 1]) {
    const x1 = sx > 0 ? S : -W, x2 = sx > 0 ? W : -S;
    add('blueGrey', [x1, -D, 18], [x2, D, 50]);
    add('blueGrey', [x1, -D, 52], [x2, D, 84]);
    // The joint needs a rail. Left as an open 2-unit gap it showed the dark
    // cavity straight through, and SIDE and BACK both read a green stripe
    // across the flank.
    add('cream',    [x1, -(D + 0.2), 50], [x2, D + 0.2, 52]);
  }
  // ---- P07 back, same joint -----------------------------------------------
  add('blueGrey', [-W, D - 3, 18], [W, D, 50]);
  add('blueGrey', [-W, D - 3, 52], [W, D, 84]);
  add('cream',    [-W, D - 3, 50], [W, D + 0.2, 52]);
  add('cream',    [-W, -D, 80],    [W, D, 84]);             // top run

  // ---- P09 cavity: five dark faces ----------------------------------------
  const BW = D - 6;                       // where the cavity's back wall stands
  add('interior', [-S, BW, 18],        [S, D - 3, 80]);
  add('interior', [-S, -D, 18],        [-(S - 1.5), BW, 80]);
  add('interior', [S - 1.5, -D, 18],   [S, BW, 80]);
  add('interior', [-S, -D, 18],        [S, BW, 20]);
  add('interior', [-S, -D, 78],        [S, BW, 80]);
  // Shelves run the FULL interior depth, as the reference's iso view draws
  // them; they used to stop at the midline, which is invisible head-on and
  // wrong from every other angle.
  for (const z of [29, 41, 53, 65]) add('shelf', [-S, -(D - 1), z], [S, BW, z + 2.5]);

  // ---- P08 corner posts ---------------------------------------------------
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    const x1 = sx > 0 ? W - 2 : -W, x2 = sx > 0 ? W : -(W - 2);
    const y1 = sy > 0 ? D - 2 : -D, y2 = sy > 0 ? D : -(D - 2);
    add('cream', [x1, y1, 18], [x2, y2, 84]);
  }

  // ---- P15 crown: 11% of height, a lip and one block ----------------------
  // BOTH crown pieces overhang the body, and their heights are close: a top
  // block narrower than the carcass and twice the lip's height read as a lid
  // resting on the cabinet rather than as its cap.
  add('cream', [-C, -(D + 1), 84],   [C, D + 1, 88]);
  add('cream', [-(C - 0.5), CF, 88], [C - 0.5, D + 0.5, 93]);

  // ---- P11/P12 door: a wide light between two NARROW borders ---------------
  const frame = (kind, xIn, xOut, zLo, zHi, y1, y2) => {
    add(kind, [-xOut, y1, zLo], [-xIn, y2, zHi]);
    add(kind, [xIn, y1, zLo],   [xOut, y2, zHi]);
    add(kind, [-xOut, y1, zHi - (xOut - xIn)], [xOut, y2, zHi]);
    add(kind, [-xOut, y1, zLo], [xOut, y2, zLo + (xOut - xIn)]);
  };
  frame('cream', S, W, 20, 82, F - 1.5, F + 2);
  frame('frame', G, S, 22, 80, F - 2.5, F - 1.5);
  // P13 glass — NOT a transparent pane. Alpha blending produces colours that
  // are in no palette, so the snap sent them to whatever grey was nearest and
  // the door went dead. The sheet does not draw a pane either: you see the
  // interior directly, with a reflection drawn ON it. So the pane is gone and
  // the reflection is a staircase of small boxes, which is how pixel art draws
  // a diagonal and costs nothing here.
  for (const [x0, z0, n] of [[G - 4.5, 70, 5], [G - 10.5, 66, 4]]) {
    for (let i = 0; i < n; i++) {
      add('glint', [x0 - i * 1.5, F - 2.4, z0 - i * 2.2],
                   [x0 - i * 1.5 + 1.2, F - 2.2, z0 - i * 2.2 + 2.4]);
    }
  }
  // ---- P14 handle ---------------------------------------------------------
  add('purple', [W - 3.5, F - 4.6, 41], [W - 1, F - 3.2, 63]);
  add('purple', [W - 3, F - 3.2, 42],   [W - 1.5, F - 2.2, 45]);
  add('purple', [W - 3, F - 3.2, 59],   [W - 1.5, F - 2.2, 62]);
  // P16 display — geometry, not a decal. Exactly one, at the centre, at any
  // width: the case a tiling texture fundamentally cannot express. It rides the
  // CROWN's front face, which overhangs the body, so it moves with the cap.
  add('disp',  [-5.8, CF - 0.7, 88.6], [5.8, CF, 92.2]);
  add('lamp',  [-4.2, CF - 0.9, 89.8], [-2.7, CF - 0.6, 91.0]);
  add('digit', [-1.2, CF - 0.9, 89.8], [3.6, CF - 0.6, 91.0]);
  return g;
}

// ---------------------------------------------------------------------------
// One screen pixel per texel. viewH units tall at texelsPerUnit px per unit is
// the only ratio at which a nearest-sampled pixel-art sheet stays crisp: above
// it the sheet aliases, below it the sheet blurs.
const viewH = 116, viewW = viewH * (0.56 + Math.max(0, (H - 16) * 0.030));
// Pixels per world unit. With no texture there is no texel density to match,
// so this is a free choice: it sets how chunky the pixels are, nothing more.
// The reference draws its 96-unit cabinet about 850 px tall, so 8 is its own.
const PPU = Number(params.get('ppu') ?? 8);
const Hpx = Math.round(viewH * PPU);
const W = Math.round(viewW * PPU);
// preserveDrawingBuffer, because this scene renders exactly ONCE at load and
// never again — there is no animation loop to redraw it. Without it the buffer
// is discarded at the first composite and both a screenshot and a readback come
// back as a single flat colour, which is not a blank render but a blank READ,
// and the two look identical from the outside.
const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true });
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
