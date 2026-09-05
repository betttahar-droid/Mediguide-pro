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
import { STYLE, MATERIALS, buildPalette, tableBox, useRawColours,
         loadFittings, loadSurfaces } from './style.js';
import * as vaccineFridge from './models/vaccineFridge.js';
import * as homeFridge from './models/homeFridge.js';
import * as medFreeze from './models/medFreeze.js';
import * as posTerminal from './models/posTerminal.js';

// ?model=home / ?model=med render the second and third props. All three share
// every material, every surface tile, every fitting and the whole shader; the
// only difference between them is geometry and placement.
const MODELS = { vaccine: vaccineFridge, home: homeFridge, med: medFreeze,
                 pos: posTerminal };
const MODEL = MODELS[params.get('model') ?? 'vaccine'] ?? vaccineFridge;

// Before any THREE.Color exists — see style.js. The authored hex is the
// output pixel; nothing here wants a linear round trip.
useRawColours(THREE);

// The fittings atlas, and its own colours folded into the palette. Without the
// merge the post pass would snap the hazard yellow and the rating plate's warm
// grey to whatever cabinet colour sat nearest and the decals would come out as
// smears.
// The surface atlas must load BEFORE the first material is built: materials
// bake the tile rect into their uniforms at construction.
loadSurfaces(THREE,
  await new THREE.TextureLoader().loadAsync('/tools/voxel-fridge/surfaces.png'),
  await (await fetch('/tools/voxel-fridge/surfaces.json')).json());

const kitMan = await (await fetch('/tools/voxel-fridge/fittings.json')).json();
const kit = loadFittings(THREE,
  await new THREE.TextureLoader().loadAsync('/tools/voxel-fridge/fittings.png'),
  kitMan);

// The object's vertical extent, for the baked shading ramp. Set BEFORE any
// material is built, since materials bake it into their uniforms.
STYLE.objLo = MODEL.objLo;
STYLE.objHi = MODEL.objHi;

// MATS is filled as the model is built, and it is the record of which material
// families this object actually uses — which is what the palette is built from,
// further down, AFTER the scene exists. See buildPalette().
const MATS = new Map();

// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// One screen pixel per texel. viewH units tall at texelsPerUnit px per unit is
// the only ratio at which a nearest-sampled pixel-art sheet stays crisp: above
// it the sheet aliases, below it the sheet blurs.
// A model declares its own frame aspect. The first two props are tall and
// narrow and 0.56 framed them; the third is squatter and deeper, and at 0.56 an
// iso view cut its back flank — including the vent grille, which is the one
// feature only that view shows. Framing is a property of the object, so it
// belongs to the model rather than to a constant that fitted the first one.
const viewH = (MODEL.objHi - MODEL.objLo) * 1.24;
const viewW = viewH * ((MODEL.aspect ?? 0.56) + Math.max(0, (H - 16) * 0.030));
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
} else if (params.get('solo')) {
  // ?solo=1 renders ONE shaped box, for isolating a geometry bug from a scene
  // of ninety of them.
  const g = new THREE.Group();
  g.add(tableBox(THREE, 'plinth', [-8, -7, 40], [8, 7, 54], MATS));
  scene.add(g);
} else {
  scene.add(MODEL.build(THREE, MATS, kit, H));
}

// ---------------------------------------------------------------------------
// THE PALETTE, built now that the scene exists — from the materials this model
// actually used, not from every family in the kit. See buildPalette().
const paletteRGB = buildPalette(THREE, 64, [...MATS.keys()]);
// The fittings atlas's own colours, and the CLEAR COLOUR. The ground is a
// colour in the frame like any other, and once the palette stopped containing
// every family in the kit it stopped containing anything near the cream card —
// so the background snapped to whichever body tone was nearest and the object
// sat on a ground made of itself. A quantiser can only keep what it is given.
for (const hex of [...(kitMan.palette ?? []), params.get('bg') ?? BG]) {
  const c = new THREE.Color(hex);
  paletteRGB.push([c.r, c.g, c.b].map((v) => Math.round(v * 255)));
}
const paletteCount = paletteRGB.length;
const paletteTexture = new THREE.DataTexture(
  new Uint8Array(paletteRGB.flatMap((c) => [...c, 255])), paletteCount, 1,
  THREE.RGBAFormat);
paletteTexture.magFilter = paletteTexture.minFilter = THREE.NearestFilter;
paletteTexture.needsUpdate = true;
console.info(`palette: ${paletteCount} colours from ${MATS.size} of `
  + `${Object.keys(MATERIALS).length} material families`);

// Frame the model by its own height rather than the first one's.
const target = new THREE.Vector3(0, (MODEL.objLo + MODEL.objHi) / 2, 0);
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
    // Ordered-dither amplitude, about one palette step. ?dither=0 turns it off,
    // and THE RESIZE TEST NEEDS THAT: the Bayer pattern is keyed on
    // gl_FragCoord, so two renders at different canvas widths get a different
    // dither PHASE and up to a third of every flat field lands on the other of
    // two neighbouring palette entries. Comparing them pixel for pixel then
    // reports a systematic, column-shaped difference that has nothing whatever
    // to do with the geometry — which is indistinguishable, by eye or by
    // arithmetic, from a part that really did move.
    uDither: { value: Number(params.get('dither') ?? 0.055) },
    uOutline: { value: 0.55 },   // how far an edge darkens its own colour
    // Raised from 0.20 once every form was bevelled. In the normal buffer a
    // 45-degree chamfer differs from its neighbour by about 0.38 and a true
    // 90-degree corner by about 0.71, so 0.20 inked EVERY bevel facet — the
    // heavily rounded second model came out looking like a wireframe box.
    // The bevel already IS the edge treatment; drawing a line on it doubles up.
    uNormalEdge: { value: 0.52 },
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
    uniform float uPaletteSize, uOutline, uNormalEdge, uDepthEdge, uDither;
    varying vec2 vUv;

    // ORDERED (BAYER) DITHER. The PlayStation's signature, and the piece that
    // makes a tiny palette work: it fakes intermediate colours by alternating
    // two real ones in a fixed 4x4 pattern. Note this is NOT the random
    // speckle removed earlier - that was noise over flat fields and read as
    // dirt. This is a regular pattern applied only where a value falls BETWEEN
    // two palette entries, which now happens constantly because the baked
    // vertical shading is a gradient. Without it that gradient snaps into hard
    // horizontal bands.
    float bayer2(vec2 a) { a = floor(a); return fract(a.x / 2.0 + a.y * a.y * 0.75); }
    float bayer4(vec2 a) { return bayer2(0.5 * a) * 0.25 + bayer2(a); }

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

      // Nudge by the dither pattern BEFORE snapping, so a value sitting between
      // two palette entries lands on one or the other depending on its position
      // in the 4x4 cell — which is what produces the checkered transition
      // instead of a hard edge.
      c += (bayer4(gl_FragCoord.xy) - 0.47) * uDither;

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
// POLY BUDGET, reported rather than assumed. The literature puts a simple prop
// at 300-1500 triangles and a hero prop at 2-5k; a bevelled box costs 44 where
// a plain one costs 12, so the bevel pass roughly quadrupled this and it is
// worth knowing by how much rather than hoping.
// Counted off the GEOMETRY, not renderer.info: info.render is reset by every
// render call, and the last one here is the post-pass fullscreen quad, so it
// reported the scene as 2 triangles.
window.__stats = (() => {
  let tris = 0, parts = 0, decals = 0;
  scene.traverse((o) => {
    const g = o.geometry;
    if (!g) return;
    const n = (g.index ? g.index.count : g.attributes.position.count) / 3;
    tris += n;
    if (o.material?.isShaderMaterial) parts++; else decals++;
  });
  return { triangles: tris, parts, decals };
})();
console.info(`geometry: ${window.__stats.triangles} triangles, `
  + `${window.__stats.parts} parts + ${window.__stats.decals} decals`);

// ---------------------------------------------------------------------------
// BURIED PARTS — the single most repeated mistake in this project, made
// mechanical instead of remembered.
//
// There is no boolean subtract here, so a box placed inside another box is
// simply invisible. It has happened on every prop and three times on one of
// them: a solid cavity that hid four shelves of stock, a vent recessed INTO a
// flank, and a compressor placed inside the carcass that rendered as two pipes
// running down to nothing. None of those symptoms looks anything like its
// cause, and each cost a render cycle to find by eye.
//
// A pair of axis-aligned boxes is trivial to test, and the CORRECT pattern in
// this kit is to build a recess PROUD, which is never contained — so the false
// positive rate is low by construction. Reported, never thrown: a part may be
// deliberately hidden, and this prints evidence rather than a verdict.
window.__buried = (() => {
  const boxes = [];
  scene.traverse((o) => {
    const t = o.userData?.table;
    if (t) boxes.push({ name: o.name, t, tapered: !!o.userData.tapered });
  });
  const inside = (a, b, eps) =>
    a[0] >= b[0] - eps && a[1] >= b[1] - eps && a[2] >= b[2] - eps &&
    a[3] <= b[3] + eps && a[4] <= b[4] + eps && a[5] <= b[5] + eps;
  const vol = (t) => (t[3] - t[0]) * (t[4] - t[1]) * (t[5] - t[2]);
  const out = [];
  for (const a of boxes) {
    for (const b of boxes) {
      if (a === b || vol(b) <= vol(a) || b.tapered) continue;
      if (!inside(a.t, b.t, 0.02)) continue;
      // clearance on the tightest axis: 0 means a face is flush (z-fighting,
      // probably survivable), > 0 means genuinely sealed inside.
      const clear = Math.min(
        a.t[0] - b.t[0], a.t[1] - b.t[1], a.t[2] - b.t[2],
        b.t[3] - a.t[3], b.t[4] - a.t[4], b.t[5] - a.t[5]);
      out.push({ part: a.name, inside: b.name, clearance: +clear.toFixed(2),
                 at: a.t.map((v) => +v.toFixed(1)) });
      break;
    }
  }
  return out;
})();
if (window.__buried.length) {
  console.info(`buried: ${window.__buried.length} part(s) fully inside another`);
  for (const b of window.__buried.slice(0, 20)) {
    console.info(`buried:   ${b.part} inside ${b.inside}`
      + ` (clearance ${b.clearance}) at [${b.at.slice(0, 3)}]..[${b.at.slice(3)}]`);
  }
} else {
  console.info('buried: none');
}
window.__done = true;
