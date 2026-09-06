import * as THREE from 'three';
import {
  MATS, STYLE, decal, makeDecalKit, makeMaterials, semanticDecal, tableBox, triangleCount, useRawColours,
} from './style.js';

useRawColours();
STYLE.objLo = 0;
STYLE.objHi = 96;

const params = new URLSearchParams(location.search);
const view = params.get('view') ?? 'iso';
const diagnostic = params.get('diagnostic') ?? '';
const showDecals = params.get('decals') !== '0';
const showSurfaces = params.get('surfaces') !== '0';
const sx = Number(params.get('sx') ?? 1);
const sy = Number(params.get('sy') ?? 1);
const sz = Number(params.get('sz') ?? 1);
const tx = (n) => n;

const scene = new THREE.Scene();
scene.background = new THREE.Color('#101116');
const camera = new THREE.OrthographicCamera(-1.25, 1.25, 1.55, -1.55, .01, 30);
const renderer = new THREE.WebGLRenderer({ antialias: false, alpha: false });
renderer.setPixelRatio(1);
renderer.setSize(320, 400, false);
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);

const kit = await makeDecalKit();
const M = makeMaterials(showSurfaces ? kit.surfaces : null, showSurfaces ? kit.semanticFaces : null);
const g = new THREE.Group();
g.name = 'measured_recipe_fridge';
scene.add(g);
const add = (kind, a, b, opts = {}) => {
  const mesh = tableBox(kind, a, b, M, opts);
  g.add(mesh);
  return mesh;
};
const tagRigid = (mesh, size) => {
  mesh.userData.rigidTexelSize = size;
  return mesh;
};

// Phase 1: one measured half-width drives macro dimensions. Small borders and
// fittings stay literal texel sizes by design and are never transform-scaled.
const W = 19.5 * sx;
const H = 96 * sz;
const D = W * 0.949 * sy / sx;
const BASE_TOP = H * 0.208;
const CROWN_LO = H * 0.913;
const CROWN_HI = H * 0.974;
const ROOF = H;
const OPEN_LO = H * 0.229;
const OPEN_HI = H * 0.854;
const OPEN_HALF = W * 0.769;
const F = -D;
const P_BODY = F;
const P_FRAME = F - tx(.65);
const P_DECAL = F - tx(1.45);
const P_HANDLE = F - tx(4.0);

// Phase 2: only silhouette and structural depth are boxes.
const shell = tx(3.2);
add('steel', [-W, -D, BASE_TOP], [-W + shell, D, CROWN_LO], {
  name: 'macro_shell_left', taperX: .5, taperY: .5,
});
add('steel', [W - shell, -D, BASE_TOP], [W, D, CROWN_LO], {
  name: 'macro_shell_right', taperX: .5, taperY: .5,
});
add('steel', [-W + shell, D - shell, BASE_TOP], [W - shell, D, CROWN_LO], { name: 'macro_shell_back', taperX: .5 });
add('steel', [-W + shell, -D, CROWN_LO - shell], [W - shell, D - shell, CROWN_LO], { name: 'macro_shell_ceiling', taperX: .5, taperY: .5 });
add('teal', [-W * .98, -D * 1.01, 0], [W * .98, D, BASE_TOP], {
  name: 'macro_base', taperX: .6, surfaceFaces: { front: 'baseFront' },
});
add('plum', [-W * 1.02, -D * 1.04, 0], [W * 1.02, D * 1.03, H * .028], { name: 'macro_plinth', bevel: 0 });
add('steel', [-W * 1.03, -D * 1.03, CROWN_LO], [W * 1.03, D * .98, CROWN_HI], {
  name: 'macro_crown', taperX: 1.2, taperY: 1.0, surfaceFaces: { front: 'crownFront' },
});
add('cream', [-W * .82, -D * .82, CROWN_HI], [W * .82, D * .78, ROOF], {
  name: 'macro_roof', taperX: 1.0, taperY: .8, surfaceFaces: { top: 'roofTop' },
});

// The cavity color belongs on the rear wall. Putting it on the front mounting
// plane would occlude every shelf while still looking like a plausible door.
add('dark', [-OPEN_HALF, D - shell - tx(.3), OPEN_LO], [OPEN_HALF, D - shell, OPEN_HI], { name: 'door_cavity_back', bevel: 0 });
const border = tx(3);
add('cream', [-W * .92, P_FRAME, OPEN_LO - border], [-OPEN_HALF, P_BODY, OPEN_HI + border], {
  name: 'frame_left', bevel: .7,
});
add('cream', [OPEN_HALF, P_FRAME, OPEN_LO - border], [W * .92, P_BODY, OPEN_HI + border], {
  name: 'frame_right', bevel: .7,
});
add('cream', [-OPEN_HALF, P_FRAME, OPEN_HI], [OPEN_HALF, P_BODY, OPEN_HI + border], {
  name: 'frame_top', bevel: .7,
});
add('cream', [-OPEN_HALF, P_FRAME, OPEN_LO - border], [OPEN_HALF, P_BODY, OPEN_LO], {
  name: 'frame_bottom', bevel: .7,
});
const rail = tx(1.5);
add('teal', [-OPEN_HALF, P_FRAME - .45, OPEN_LO], [-OPEN_HALF + rail, P_FRAME, OPEN_HI], { name: 'door_rail_left', bevel: .45 });
add('teal', [OPEN_HALF - rail, P_FRAME - .45, OPEN_LO], [OPEN_HALF, P_FRAME, OPEN_HI], { name: 'door_rail_right', bevel: .45 });
add('teal', [-OPEN_HALF, P_FRAME - .45, OPEN_HI - rail], [OPEN_HALF, P_FRAME, OPEN_HI], { name: 'door_rail_top', bevel: .45 });
add('teal', [-OPEN_HALF, P_FRAME - .45, OPEN_LO], [OPEN_HALF, P_FRAME, OPEN_LO + rail], { name: 'door_rail_bottom', bevel: .45 });

const shelfPitch = tx(12);
const shelfLevels = [];
for (let z = OPEN_LO + tx(13); z < OPEN_HI - tx(2); z += shelfPitch) {
  shelfLevels.push(z);
  add('steel', [-OPEN_HALF * .82, F + tx(.4), z], [OPEN_HALF * .82, F + tx(14), z + tx(1.6)], {
    name: 'shelf', bevel: 0, surfaceFaces: { front: 'shelfLip' },
  });
}
const HANDLE_W = tx(3.2);
const HANDLE_H = tx(18);
const HANDLE_DEPTH = tx(2.55);
const HANDLE_INSET = tx(1.2);
const HANDLE_CENTER_Z = (OPEN_LO + OPEN_HI) * .5;
const HANDLE_X2 = W - HANDLE_INSET;
const HANDLE_X1 = HANDLE_X2 - HANDLE_W;
const HANDLE_LO = HANDLE_CENTER_Z - HANDLE_H * .5;
const HANDLE_HI = HANDLE_CENTER_Z + HANDLE_H * .5;
const HANDLE_MOUNT = tx(1.4);
for (const center of [HANDLE_LO + HANDLE_MOUNT, HANDLE_HI - HANDLE_MOUNT]) {
  tagRigid(add('plum',
    [HANDLE_X1 - tx(.45), P_HANDLE + tx(.9), center - tx(.9)],
    [HANDLE_X2 + tx(.45), P_DECAL + tx(.2), center + tx(.9)],
    { name: 'handle_mount', bevel: .3 },
  ), [HANDLE_W + tx(.9), P_DECAL + tx(.2) - (P_HANDLE + tx(.9)), tx(1.8)]);
}
tagRigid(add('plum', [HANDLE_X1, P_HANDLE, HANDLE_LO], [HANDLE_X2, P_HANDLE + tx(1.1), HANDLE_HI],
  { name: 'handle_grip', bevel: .45 }), [HANDLE_W, tx(1.1), HANDLE_H]);
tagRigid(add('shelf',
  [HANDLE_X1 + tx(.25), P_HANDLE - tx(.18), HANDLE_LO + tx(.6)],
  [HANDLE_X1 + tx(.75), P_HANDLE + tx(.02), HANDLE_HI - tx(.6)],
  { name: 'handle_catch', bevel: 0 }), [tx(.5), tx(.2), HANDLE_H - tx(1.2)]);
tagRigid(add('dark',
  [HANDLE_X1 + tx(.2), P_HANDLE + tx(1.1), HANDLE_LO + tx(.4)],
  [HANDLE_X2 - tx(.2), P_HANDLE + tx(1.25), HANDLE_HI - tx(.4)],
  { name: 'handle_return', bevel: 0 }), [HANDLE_W - tx(.4), tx(.15), HANDLE_H - tx(.8)]);

// Phase 5: every sub-4px fitting is a fixed-size texture decal.
const mount = (mesh, behavior = 'protected') => {
  mesh.userData.decalBehavior = behavior;
  mesh.visible = showDecals;
  g.add(mesh);
  return mesh;
};
const put = (...args) => mount(decal(...args, kit));
const putSemantic = (args, behavior = 'protected') => mount(semanticDecal(...args, kit), behavior);
// Only semantic fittings remain decals. Large-face character now comes from
// the measured three-level surface masks in style.js.
// These are corner anchors with fixed texel offsets. The guards are R2: a
// purchased fitting disappears when the supporting face cannot contain it.
const CONTROL_Y = H - tx(6);
const CONTROL_X = -W + tx(7);
const controlsFit = 2 * W >= tx(36) && CROWN_LO - BASE_TOP >= tx(12);
if (controlsFit) put('controlBezel', 'front', CONTROL_X, CONTROL_Y, tx(10), tx(5), P_DECAL - .14);
const cautionFits = 2 * W >= tx(14) && BASE_TOP >= tx(14);
if (cautionFits) put('cautionPlate', 'front', W - tx(5), tx(10), tx(8), tx(5), P_DECAL - .15);
// Unique marks are fixed-size semantic decals. They are deliberately removed
// from the nine-slice face programs so scaling can never elongate them.
for (const u of [-OPEN_HALF + tx(1.8), OPEN_HALF - tx(1.8)]) {
  putSemantic(['doorSocket', 'cream', 'front', u, OPEN_HI + tx(1.2), tx(2), tx(2), P_DECAL - .17]);
  putSemantic(['doorSocket', 'cream', 'front', u, OPEN_LO - tx(1.2), tx(2), tx(2), P_DECAL - .17]);
}
putSemantic(['serviceStripe', 'steel', 'left', -D + tx(8), CROWN_LO - tx(24), tx(8), tx(3), -W - tx(.08)]);
putSemantic(['serviceStripe', 'steel', 'left', -D + tx(9), BASE_TOP + tx(16), tx(8), tx(3), -W - tx(.08)]);
for (const z of shelfLevels) {
  putSemantic([
    'shelfPatch', 'steel', 'top', -OPEN_HALF * .48, F + tx(5), tx(4), tx(3), z + tx(1.62),
  ], 'adaptive');
}
// STRETCH panel with a REPEAT middle: fixed nine-slice rim, more vent slots.
add('ochre', [-W + tx(4), P_DECAL - tx(.16), tx(3)],
  [W - tx(4), P_DECAL - tx(.02), tx(17)], {
    name: 'vent_panel', bevel: 0, surfaceFaces: { front: 'ventField' },
  });
// Indicator lamps are fixed bought-in parts, not colours sampled from an atlas.
for (const [kind, offset] of [
  ['lampBlue', tx(13)], ['lampGreen', tx(15.2)], ['lampRed', tx(17.4)],
  ['lampCyan', tx(19.6)], ['lampWhite', tx(21.8)], ['lampAmber', tx(24)],
  ['lampRust', tx(26.2)],
]) {
  const x = -W + offset;
  if (controlsFit && x + tx(.65) <= W - tx(2)) {
    tagRigid(add(kind,
      [x - tx(.65), P_DECAL - tx(.18), CONTROL_Y - tx(.65)],
      [x + tx(.65), P_DECAL - tx(.02), CONTROL_Y + tx(.65)],
      { name: 'control_lamp', bevel: 0 }), [tx(1.3), tx(.16), tx(1.3)]);
  }
}

// Diagnostic renders are generated from the exact runtime geometry. Nano sees
// these together with the beauty render so it can distinguish a material mark
// from a part boundary. They never participate in the final art pass.
let diagnosticPalette = null;
if (diagnostic === 'parts') {
  const meshes = g.children.filter((node) => node.isMesh && !node.name.startsWith('decal_'));
  diagnosticPalette = [new THREE.Color('#101116')];
  meshes.forEach((mesh, index) => {
    const color = new THREE.Color().setHSL((index * .61803398875) % 1, .62, .56);
    diagnosticPalette.push(color);
    mesh.material = new THREE.MeshBasicMaterial({ color });
  });
  g.children.filter((node) => node.name.startsWith('decal_')).forEach((node) => { node.visible = false; });
} else if (diagnostic === 'faces') {
  const faceColors = ['#ef5350', '#ab47bc', '#42a5f5', '#26a69a', '#ffee58', '#ffa726'];
  diagnosticPalette = [new THREE.Color('#101116'), ...faceColors.map((color) => new THREE.Color(color))];
  const faceMaterial = new THREE.ShaderMaterial({
    vertexShader: 'varying vec3 vN; void main(){vN=normalize(normalMatrix*normal);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
    fragmentShader: `
      varying vec3 vN;
      void main(){
        vec3 n=normalize(vN); vec3 a=abs(n); vec3 c;
        if(a.x>=a.y && a.x>=a.z) c=n.x>0.0?vec3(0.937,0.325,0.314):vec3(0.671,0.278,0.737);
        else if(a.y>=a.z) c=n.y>0.0?vec3(0.255,0.647,0.961):vec3(0.149,0.651,0.604);
        else c=n.z>0.0?vec3(1.0,0.933,0.345):vec3(1.0,0.655,0.149);
        gl_FragColor=vec4(c,1.0);
      }
    `,
  });
  g.children.filter((node) => node.isMesh && !node.name.startsWith('decal_')).forEach((mesh) => { mesh.material = faceMaterial; });
  g.children.filter((node) => node.name.startsWith('decal_')).forEach((node) => { node.visible = false; });
}

g.rotation.y = view === 'front' ? 0 : -Math.PI / 4;
const targetY = H * STYLE.texel * .5;
camera.position.set(view === 'front' ? 0 : 4.2, view === 'front' ? targetY : 3.3, view === 'front' ? -8 : -6.2);
camera.lookAt(0, targetY, 0);
camera.zoom = .89;
camera.updateProjectionMatrix();

// Final PS1-style palette snap. The source atlas supplies shapes; this pass
// guarantees every rendered color belongs to the shared material ramps.
const renderTarget = new THREE.WebGLRenderTarget(320, 400, {
  minFilter: THREE.NearestFilter,
  magFilter: THREE.NearestFilter,
  generateMipmaps: false,
});
renderer.setRenderTarget(renderTarget);
renderer.render(scene, camera);
renderer.setRenderTarget(null);
const materialPalette = Object.values(MATS).flatMap((family) => [
  new THREE.Color(family.shade).multiplyScalar(.72),
  new THREE.Color(family.shade),
  new THREE.Color(family.base),
  new THREE.Color(family.lit),
  new THREE.Color(family.lit).multiplyScalar(1.10),
]);
const palette = diagnosticPalette ?? [new THREE.Color('#101116'), ...materialPalette, new THREE.Color('#8a6a49')];
const postScene = new THREE.Scene();
const postCamera = new THREE.Camera();
postScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({
  uniforms: { uMap: { value: renderTarget.texture }, uPalette: { value: palette } },
  vertexShader: 'varying vec2 vUv; void main(){vUv=uv;gl_Position=vec4(position,1.0);}',
  fragmentShader: `
    varying vec2 vUv;
    uniform sampler2D uMap;
    uniform vec3 uPalette[${palette.length}];
    void main(){
      vec3 source = texture2D(uMap, vUv).rgb;
      vec3 best = uPalette[0];
      float distanceBest = dot(source-best, source-best);
      for(int index=1; index<${palette.length}; index++){
        vec3 candidate = uPalette[index];
        float distanceNext = dot(source-candidate, source-candidate);
        if(distanceNext < distanceBest){ best=candidate; distanceBest=distanceNext; }
      }
      gl_FragColor=vec4(best,1.0);
    }
  `,
  depthTest: false,
  depthWrite: false,
})));
renderer.render(postScene, postCamera);
window.__VOXEL_FRIDGE_STATS__ = {
  ready: true,
  view,
  diagnostic,
  triangles: triangleCount(g),
  parts: g.children.filter((node) => !node.name.startsWith('decal_')).length,
  decals: g.children.filter((node) => node.name.startsWith('decal_')).length,
  protectedDecalSizes: g.children
    .filter((node) => node.name.startsWith('decal_') && node.userData.decalBehavior === 'protected')
    .map((node) => [node.name, node.userData.fixedTexelSize])
    .sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b))),
  adaptiveDecalCounts: Object.entries(g.children
    .filter((node) => node.name.startsWith('decal_') && node.userData.decalBehavior === 'adaptive')
    .reduce((counts, node) => ({ ...counts, [node.name]: (counts[node.name] ?? 0) + 1 }), {}))
    .sort((a, b) => a[0].localeCompare(b[0])),
  rigidPartSizes: g.children
    .filter((node) => node.userData.rigidTexelSize)
    .map((node) => [node.name, node.userData.rigidTexelSize])
    .sort((a, b) => a[0].localeCompare(b[0])),
  decalTexelSizes: g.children
    .filter((node) => node.name.startsWith('decal_'))
    .map((node) => [node.name, node.userData.fixedTexelSize])
    .sort((a, b) => a[0].localeCompare(b[0])),
  semanticFacePrograms: g.children
    .filter((node) => node.material?.uniforms?.uSemantic)
    .map((node) => [node.name, ['Left', 'Right', 'Bottom', 'Top', 'Front', 'Back']
      .filter((face) => node.material.uniforms[`uRoleParams${face}`].value.w > .5)])
    .filter(([, faces]) => faces.length),
  scale: [sx, sy, sz],
  errors: [],
};
