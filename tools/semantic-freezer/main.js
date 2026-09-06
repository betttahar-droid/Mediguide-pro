import * as THREE from 'three';
import {
  MATS, STYLE, makeMaterials, tableBox, triangleCount, useRawColours,
} from '../voxel-fridge/style.js';

useRawColours();
STYLE.objLo = -2;
STYLE.objHi = 104;

const params = new URLSearchParams(location.search);
const view = params.get('view') ?? 'iso';
const diagnostic = params.get('diagnostic') ?? '';
const showSurfaces = params.get('surfaces') !== '0';
const showContents = params.get('contents') !== '0';
const showFittings = params.get('fittings') !== '0';
const textureVersion = params.get('texture') ?? 'v1';
const useV7 = textureVersion === 'v7';
const useV6 = textureVersion === 'v6' || useV7;
const useV5 = textureVersion === 'v5' || useV6;
const useV4 = textureVersion === 'v4' || useV5;
const useV3 = textureVersion === 'v3' || useV4;
const useV2 = textureVersion === 'v2' || useV3;
const backgroundHex = params.get('bg') === 'magenta' ? '#ff00ff' : '#101116';
const sx = Number(params.get('sx') ?? 1);
const sy = Number(params.get('sy') ?? 1);
const sz = Number(params.get('sz') ?? 1);
const autoFitCamera = params.get('fit') !== '0';
let orbitYaw = Number(params.get('yaw') ?? -36);
let orbitElevation = Number(params.get('elevation') ?? 2.5);
STYLE.objHi = 104 * sz;
const tx = (n) => n;

const scene = new THREE.Scene();
scene.background = new THREE.Color(backgroundHex);
const camera = new THREE.OrthographicCamera(-1.35, 1.35, 1.65, -1.65, .01, 30);
const renderer = new THREE.WebGLRenderer({ antialias: false, alpha: false });
renderer.setPixelRatio(1);
renderer.setSize(320, 400, false);
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);

const loader = new THREE.TextureLoader();
const v5Manifest = useV5
  ? await fetch(useV7 ? '/textures/semantic-freezer-v7.json'
    : (useV6 ? '/textures/semantic-freezer-v6.json' : '/textures/semantic-freezer-v5.json')).then((response) => response.json())
  : null;
const [surfaceTexture, semanticTexture, fittingTexture, microTexture] = await Promise.all([
  loader.loadAsync('/textures/vaccine-fridge-surfaces-v12.png'),
  loader.loadAsync('/textures/semantic-freezer-faces-v1.png'),
  loader.loadAsync(useV7
    ? '/textures/semantic-freezer-fittings-v7.png'
    : (useV6 ? '/textures/semantic-freezer-fittings-v6.png'
    : (useV5 ? '/textures/semantic-freezer-fittings-v5.png'
    : (useV4 ? '/textures/semantic-freezer-fittings-v4.png'
    : (useV2 ? '/textures/semantic-freezer-fittings-v2.png' : '/textures/semantic-freezer-fittings-v1.png'))))),
  useV7
    ? loader.loadAsync('/textures/semantic-freezer-microfields-v7.png')
    : (useV6 ? loader.loadAsync('/textures/semantic-freezer-microfields-v6.png')
    : (useV5 ? loader.loadAsync('/textures/semantic-freezer-microfields-v5.png')
    : (useV4 ? loader.loadAsync('/textures/semantic-freezer-microfields-v4.png')
    : (useV2 ? loader.loadAsync('/textures/semantic-freezer-microfields-v2.png') : Promise.resolve(null))))),
]);
for (const texture of [surfaceTexture, semanticTexture, fittingTexture, microTexture].filter(Boolean)) {
  texture.colorSpace = THREE.NoColorSpace;
  texture.magFilter = texture.minFilter = THREE.NearestFilter;
  texture.generateMipmaps = false;
  texture.wrapS = texture.wrapT = THREE.ClampToEdgeWrapping;
}
const M = makeMaterials(
  showSurfaces ? surfaceTexture : null,
  showSurfaces ? semanticTexture : null,
  showSurfaces && useV2 ? microTexture : null,
);
const g = new THREE.Group();
g.name = 'semantic_medical_freezer';
scene.add(g);
const add = (kind, a, b, opts = {}) => {
  const mesh = tableBox(kind, a, b, M, opts);
  g.add(mesh);
  return mesh;
};
const rigid = (mesh, size) => { mesh.userData.rigidTexelSize = size; return mesh; };
const semanticSupport = (mesh, id, measuredSize) => {
  mesh.userData.semanticSupport = id;
  mesh.userData.measuredTexelSize = measuredSize;
  return mesh;
};
const correspondence = (mesh, ...ids) => {
  mesh.userData.correspondenceIds = ids;
  return mesh;
};
const FITTINGS = useV2 ? {
  medicalIdentity: [0, 0, 32, 24], digitalStatus: [40, 0, 36, 16],
  sideRating: [84, 0, 18, 12], rearWarning: [110, 0, 36, 14],
  rearDoNot: [154, 0, 32, 10], fanGrille: [192, 0, 28, 28],
  cartonCovid: [0, 32, 16, 20], cartonMmr: [20, 32, 16, 20],
  cartonFlu: [40, 32, 16, 20], cartonBooster: [60, 32, 16, 20],
  vialCovid: [84, 32, 10, 14], vialMmr: [98, 32, 10, 14],
  vialFlu: [112, 32, 10, 14], vialPolio: [126, 32, 10, 14],
  sideBottomWear: [150, 32, 28, 18], sideTopWear: [182, 32, 28, 18],
  frontBaseWear: [214, 32, 32, 12],
  ...(useV6 ? {
    condenserField: [0, 72, 64, 112], sideVentPanel: [72, 72, 48, 56],
    compressorPlate: [128, 72, 24, 28],
  } : {}),
} : Object.fromEntries([
  'medicalBadge', 'digitalStatus', 'statusStrip', 'sideRating',
  'rearWarning', 'cartonLabel', 'vialLabel', 'fanGrille',
].map((name, index) => [name, [index * 32, 0, 32, 32]]));
const fittingAtlasHeight = useV6 ? 192 : (useV2 ? 64 : 32);
const fittingMaterials = new Map();
const fittingMaterial = (name) => {
  if (fittingMaterials.has(name)) return fittingMaterials.get(name);
  const [x, y, width, height] = FITTINGS[name];
  const material = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, side: THREE.DoubleSide,
    uniforms: {
      uMap: { value: fittingTexture },
      uRect: { value: new THREE.Vector4(
        x / 256, 1 - (y + height) / fittingAtlasHeight,
        width / 256, height / fittingAtlasHeight,
      ) },
    },
    vertexShader: 'varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
    fragmentShader: 'varying vec2 vUv;uniform sampler2D uMap;uniform vec4 uRect;void main(){vec4 c=texture2D(uMap,uRect.xy+vUv*uRect.zw);if(c.a<.5)discard;gl_FragColor=c;}',
  });
  fittingMaterials.set(name, material);
  return material;
};
const fixedFitting = (name, face, u, v, widthPx, heightPx, plane, options = {}) => {
  if (!showFittings) return null;
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(widthPx * STYLE.texel, heightPx * STYLE.texel),
    fittingMaterial(name),
  );
  mesh.name = `decal_${name}`;
  if (face === 'front') {
    mesh.rotation.y = Math.PI;
    mesh.position.set(u * STYLE.texel, v * STYLE.texel, plane * STYLE.texel);
  }
  if (face === 'back') {
    mesh.position.set(u * STYLE.texel, v * STYLE.texel, plane * STYLE.texel);
  }
  if (face === 'right') {
    mesh.rotation.y = Math.PI / 2;
    mesh.position.set(plane * STYLE.texel, v * STYLE.texel, u * STYLE.texel);
  }
  if (face === 'left') {
    mesh.rotation.y = -Math.PI / 2;
    mesh.position.set(plane * STYLE.texel, v * STYLE.texel, u * STYLE.texel);
  }
  mesh.renderOrder = options.renderOrder ?? 8;
  mesh.userData.fixedTexelSize = [widthPx, heightPx];
  mesh.userData.scaleClass = 'fixed';
  mesh.userData.mountPlane = face;
  mesh.userData.fittingRole = name;
  mesh.userData.textureLayer = options.layer ?? 'label';
  if (options.correspondenceId) mesh.userData.correspondenceId = options.correspondenceId;
  else if (useV5 && v5Manifest?.runtimePlacements?.fixedFittings?.[name]) {
    mesh.userData.correspondenceId = { condenserField: 'rear_condenser_field', sideVentPanel: 'side_vent' }[name] ?? name;
  }
  g.add(mesh);
  return mesh;
};

const seamMaterial = new THREE.MeshBasicMaterial({
  color: '#657178', side: THREE.DoubleSide, depthWrite: false,
});
const adaptiveStrip = (name, face, u, v, widthPx, heightPx, plane) => {
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(widthPx * STYLE.texel, heightPx * STYLE.texel),
    seamMaterial,
  );
  mesh.name = `adaptive_${name}`;
  if (face === 'left') {
    mesh.rotation.y = -Math.PI / 2;
    mesh.position.set(plane * STYLE.texel, v * STYLE.texel, u * STYLE.texel);
  }
  mesh.renderOrder = 6;
  mesh.userData.scaleClass = 'count-adaptive';
  mesh.userData.adaptiveRole = name;
  mesh.userData.fixedThicknessPx = Math.min(widthPx, heightPx);
  g.add(mesh);
  return mesh;
};

// Measured reference envelope: 44 wide × 43 deep × 104 high.
const W = tx(22) * sx;
const D = tx(21.5) * sy;
const H = tx(104) * sz;
const F = -D;
const B = D;
const BODY_TOP = H * .837;
const HEADER_TOP = H * .971;
const OPEN_LO = H * .115;
const OPEN_HI = H * .824;
const OPEN_HALF = W * .795;
const SHELL = tx(3);
const P_BODY = F;
const P_FRAME = F - tx(.65);
const P_FITTING = F - tx(1.25);
const REAR_COIL_LO = tx(32);
const REAR_COIL_HI = HEADER_TOP - tx(14);
const v5Fixed = v5Manifest?.runtimePlacements?.fixedFittings ?? {};
const anchorContracts = v5Manifest?.anchorContracts ?? {};
const condenserContract = v5Manifest?.adaptiveTextureContracts?.condenserField;
const condenserLayout = useV7 && condenserContract ? (() => {
  const left = -W + tx(condenserContract.horizontal.leftMarginTexels);
  const right = W - tx(condenserContract.horizontal.rightMarginTexels);
  const bottom = tx(condenserContract.vertical.bottomTexels);
  const top = HEADER_TOP - tx(condenserContract.vertical.topMarginTexels);
  return {
    left, right, bottom, top,
    width: right - left, height: top - bottom,
    centerX: (left + right) / 2, centerZ: (bottom + top) / 2,
  };
})() : null;
const placeV5Fitting = (name, plane, options = {}) => {
  const item = v5Fixed[name];
  if (!item) return null;
  const contract = useV7 ? anchorContracts[name] : null;
  let u = item.face === 'left' ? F + tx(item.fromFrontTexels) : tx(item.uTexels);
  let z = item.anchorMode === 'top-fixed' ? H - tx(item.topOffsetTexels) : tx(item.zTexels);
  if (contract?.horizontal === 'back-fixed') u = B - tx(contract.backOffsetTexels);
  if (contract?.horizontal === 'front-fixed') u = F + tx(contract.frontOffsetTexels);
  if (contract?.horizontal === 'center-fixed') u = tx(contract.centerTexels);
  if (contract?.horizontal === 'panel-center' && condenserLayout) {
    u = condenserLayout.centerX + tx(contract.centerOffsetTexels);
  }
  if (contract?.vertical === 'bottom-fixed') z = tx(contract.bottomCenterTexels);
  if (contract?.vertical === 'top-fixed') z = HEADER_TOP - tx(contract.topOffsetTexels);
  if (contract?.vertical === 'panel-top-fixed' && condenserLayout) {
    z = condenserLayout.top - tx(contract.topOffsetTexels);
  }
  if (contract?.vertical === 'panel-bottom-fixed' && condenserLayout) {
    z = condenserLayout.bottom + tx(contract.bottomOffsetTexels);
  }
  return fixedFitting(name, item.face, u, z, item.sizeTexels[0], item.sizeTexels[1], plane, {
    layer: item.layer, ...options,
  });
};

const adaptiveCondenserField = (layout, contract, plane) => {
  if (!showFittings || !layout || !contract) return null;
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(layout.width * STYLE.texel, layout.height * STYLE.texel),
    new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, side: THREE.DoubleSide,
      uniforms: {
        uSize: { value: new THREE.Vector2(layout.width, layout.height) },
        uRail: { value: new THREE.Vector2(contract.railPitchTexels, contract.railWidthTexels) },
        uRow: { value: new THREE.Vector2(contract.rowPitchTexels, contract.rowWidthTexels) },
        uDark: { value: new THREE.Color('#252b2d') },
        uMid: { value: new THREE.Color('#4e5b5e') },
        uLight: { value: new THREE.Color('#778281') },
      },
      vertexShader: 'varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
      fragmentShader: `
        varying vec2 vUv;
        uniform vec2 uSize;
        uniform vec2 uRail;
        uniform vec2 uRow;
        uniform vec3 uDark;
        uniform vec3 uMid;
        uniform vec3 uLight;
        void main(){
          vec2 p = vUv * uSize;
          float railPhase = mod(p.x + uRail.x * .18, uRail.x);
          float rowPhase = mod(p.y + uRow.x * .22, uRow.x);
          float rail = 1.0 - step(uRail.y, railPhase);
          float row = 1.0 - step(uRow.y, rowPhase);
          float railCatch = 1.0 - step(uRail.y * .34, railPhase);
          float rowCatch = 1.0 - step(uRow.y * .30, rowPhase);
          float mark = max(rail, row);
          if(mark < .5) discard;
          vec3 c = mix(uDark, uMid, max(railCatch, rowCatch));
          if(rail > .5 && row > .5) c = uLight;
          gl_FragColor = vec4(c, 1.0);
        }`,
    }),
  );
  mesh.name = 'adaptive_condenser_field';
  mesh.position.set(layout.centerX * STYLE.texel, layout.centerZ * STYLE.texel, plane * STYLE.texel);
  mesh.renderOrder = 7;
  mesh.userData.scaleClass = 'count-adaptive';
  mesh.userData.textureLayer = 'structural-graphic';
  mesh.userData.correspondenceId = 'rear_condenser_field';
  mesh.userData.adaptiveTexture = {
    id: 'condenserField',
    layer: mesh.userData.textureLayer,
    planeTexels: plane,
    renderOrder: mesh.renderOrder,
    sizeTexels: [layout.width, layout.height],
    boundsTexels: [layout.left, layout.bottom, layout.right, layout.top],
    pitchTexels: [contract.railPitchTexels, contract.rowPitchTexels],
    lineWidthTexels: [contract.railWidthTexels, contract.rowWidthTexels],
    repeatCounts: [Math.floor(layout.width / contract.railPitchTexels),
      Math.floor(layout.height / contract.rowPitchTexels)],
    marginsTexels: [contract.horizontal.leftMarginTexels, contract.horizontal.rightMarginTexels,
      contract.vertical.bottomTexels, contract.vertical.topMarginTexels],
  };
  g.add(mesh);
  return mesh;
};

// Cabinet masses.
correspondence(add('freezerSide', [-W, F, 0], [-W + SHELL, B, HEADER_TOP], {
  name: 'shell_left', taperX: .25, taperY: .25, disableGenericSurface: true,
  // Rounded/tapered boxes can expose different dominant face normals at the
  // silhouette, so the side recipe is valid on every shell face.
  surfaceFaces: useV5 ? {} : {
    left: 'cabinetSide', right: 'cabinetSide', front: 'cabinetSide',
    back: 'cabinetSide', top: 'cabinetSide', bottom: 'cabinetSide',
  },
}), 'side_upper_panel', 'side_lower_panel');
add('freezerSide', [W - SHELL, F, 0], [W, B, HEADER_TOP], {
  name: 'shell_right', taperX: .25, taperY: .25,
});
add('freezerSide', [-W + SHELL, B - SHELL, 0], [W - SHELL, B, HEADER_TOP], {
  name: 'shell_back', surfaceFaces: { back: 'cabinetSide' },
});
add('freezerEnamel', [-W * 1.01, F * 1.01, HEADER_TOP], [W * 1.01, B, H], {
  name: 'roof', taperX: .7, taperY: .55, surfaceFaces: { top: 'roofTop' },
});
correspondence(add('freezerEnamel', [-W, F - tx(.45), BODY_TOP], [W, F + tx(5.8), HEADER_TOP], {
  name: 'control_crown', taperX: .35, disableGenericSurface: true,
  surfaceFaces: useV2 ? {} : { front: 'crownFront' },
}), 'front_control_band');

// Bought-in fascia instruments retain their authored texel size under resizing.
const FASCIA_Y = useV3 ? H - tx(10.2) : H * .902;
if (useV5) placeV5Fitting('medicalIdentity', P_FITTING);
else if (useV2) fixedFitting('medicalIdentity', 'front', tx(11.5), FASCIA_Y, 13, 8, P_FITTING);
else fixedFitting('medicalBadge', 'front', tx(11.5), FASCIA_Y, 7, 7, P_FITTING);
if (!useV2) fixedFitting('statusStrip', 'front', -tx(1), H * .902, 11, 4, P_FITTING);
if (useV5) {
  placeV5Fitting('digitalStatus', P_FITTING);
  placeV5Fitting('sideRating', -W - tx(.22));
  placeV5Fitting('rearWarning', B + tx(1.45));
  placeV5Fitting('rearDoNot', B + tx(1.45));
} else {
  fixedFitting('digitalStatus', 'front', -tx(11.5), FASCIA_Y, useV2 ? 13 : 12, useV2 ? 5.8 : 4.8, P_FITTING);
  fixedFitting('sideRating', 'left', F + tx(7), useV3 ? HEADER_TOP - tx(19) : H * .73, useV2 ? 8 : 7, useV2 ? 5.3 : 8, -W - tx(.22));
  fixedFitting('rearWarning', 'back', -tx(12), useV3 ? REAR_COIL_HI - tx(4) : H * .89, 9, useV2 ? 3.5 : 7, B + tx(.22));
  fixedFitting('rearWarning', 'back', 0, useV3 ? (REAR_COIL_LO + REAR_COIL_HI) * .55 : H * .57, 16, useV2 ? 6.2 : 7, B + tx(1.45));
  if (useV2) fixedFitting('rearDoNot', 'back', 0, useV3 ? REAR_COIL_LO + tx(6) : H * .34, 16, 5, B + tx(1.45));
}
if (useV2) {
  // Meaningful damage is a corner-anchored fixed-size fitting.  The body may
  // grow, but these clusters neither stretch nor drift into face interiors.
  fixedFitting('frontBaseWear', 'front', 0, tx(5), 24, 8, P_FITTING, { layer: 'wear', renderOrder: 10 });
  fixedFitting('sideBottomWear', 'left', F + tx(8), tx(7), 14, 9, -W - tx(.24), { layer: 'wear', renderOrder: 10, correspondenceId: 'side_bottom_wear' });
  fixedFitting('sideBottomWear', 'left', B - tx(8), tx(7), 14, 9, -W - tx(.25), { layer: 'wear', renderOrder: 10, correspondenceId: 'side_bottom_wear' });
  fixedFitting('sideTopWear', 'left', B - tx(8), H - tx(9), 14, 9, -W - tx(.26), { layer: 'wear', renderOrder: 10 });
}

// True cavity and front construction.
add('freezerCavity', [-OPEN_HALF, B - SHELL - tx(.2), OPEN_LO], [OPEN_HALF, B - SHELL, OPEN_HI], {
  name: 'cavity_back', bevel: 0,
});
const FRAME = tx(3.2);
add('freezerSide', [-W * .94, P_FRAME, 0], [W * .94, P_BODY, OPEN_LO - FRAME], {
  name: 'front_plinth', bevel: .35, disableGenericSurface: true,
  surfaceFaces: useV2 ? {} : { front: 'baseFront' },
});
for (const [name, a, b] of [
  ['frame_left', [-W * .94, P_FRAME, OPEN_LO - FRAME], [-OPEN_HALF, P_BODY, OPEN_HI + FRAME]],
  ['frame_right', [OPEN_HALF, P_FRAME, OPEN_LO - FRAME], [W * .94, P_BODY, OPEN_HI + FRAME]],
  ['frame_top', [-OPEN_HALF, P_FRAME, OPEN_HI], [OPEN_HALF, P_BODY, OPEN_HI + FRAME]],
  ['frame_bottom', [-OPEN_HALF, P_FRAME, OPEN_LO - FRAME], [OPEN_HALF, P_BODY, OPEN_LO]],
]) correspondence(add('freezerEnamel', a, b, {
  name, bevel: .55, disableGenericSurface: true,
  surfaceFaces: useV2 ? {} : { front: 'doorFrame' },
}), 'front_door_opening');
const RAIL = tx(1.25);
add('medicalBlue', [-OPEN_HALF, P_FRAME - tx(.4), OPEN_LO], [-OPEN_HALF + RAIL, P_FRAME, OPEN_HI], { name: 'rail_left', bevel: 0 });
add('medicalBlue', [OPEN_HALF - RAIL, P_FRAME - tx(.4), OPEN_LO], [OPEN_HALF, P_FRAME, OPEN_HI], { name: 'rail_right', bevel: 0 });
add('medicalBlue', [-OPEN_HALF, P_FRAME - tx(.4), OPEN_HI - RAIL], [OPEN_HALF, P_FRAME, OPEN_HI], { name: 'rail_top', bevel: 0 });
add('medicalBlue', [-OPEN_HALF, P_FRAME - tx(.4), OPEN_LO], [OPEN_HALF, P_FRAME, OPEN_LO + RAIL], { name: 'rail_bottom', bevel: 0 });

// Fixed-pitch shelf structure.
const shelfLevels = [];
for (let z = OPEN_LO + tx(17); z < OPEN_HI - tx(3); z += tx(17)) {
  shelfLevels.push(z);
  add('freezerShelf', [-OPEN_HALF * .91, F + tx(2.0), z], [OPEN_HALF * .91, B - tx(5), z + tx(1.45)], {
    name: 'shelf', bevel: 0, disableGenericSurface: true,
    surfaceFaces: { top: 'shelfTop', front: 'shelfLip' },
  });
}

// Five-piece bought-in handle, fixed under axis scaling.
const HANDLE_X2 = W + tx(1.0);
const HANDLE_X1 = HANDLE_X2 - tx(3.2);
const HANDLE_LO = OPEN_LO + tx(30);
const HANDLE_HI = HANDLE_LO + tx(19);
for (const center of [HANDLE_LO + tx(1.5), HANDLE_HI - tx(1.5)]) {
  rigid(add('capGrey', [HANDLE_X1, F - tx(3.1), center - tx(1)], [HANDLE_X2, P_FITTING, center + tx(1)], {
    name: 'handle_mount', bevel: .25,
  }), [3.2, 1.85, 2]);
}
rigid(add('freezerEnamel', [HANDLE_X1 + tx(.45), F - tx(4), HANDLE_LO], [HANDLE_X2 - tx(.25), F - tx(2.9), HANDLE_HI], {
  name: 'handle_grip', bevel: .35,
}), [2.5, 1.1, 19]);
rigid(add('coil', [HANDLE_X1 + tx(.65), F - tx(4.15), HANDLE_LO + tx(.7)], [HANDLE_X1 + tx(1.05), F - tx(3.95), HANDLE_HI - tx(.7)], {
  name: 'handle_catch', bevel: 0,
}), [.4, .2, 17.6]);
rigid(add('coil', [HANDLE_X1 + tx(.5), F - tx(2.9), HANDLE_LO + tx(.5)], [HANDLE_X2 - tx(.35), F - tx(2.75), HANDLE_HI - tx(.5)], {
  name: 'handle_return', bevel: 0,
}), [2.35, .15, 18]);

// The vent needs a shallow physical mounting plate, while its closely spaced
// slats remain a texture detail in the PS1-style budget.
if (useV6) {
  const vent = v5Fixed.sideVentPanel;
  const ventAnchor = useV7 ? anchorContracts.sideVentPanel : null;
  const ventU = ventAnchor ? B - tx(ventAnchor.backOffsetTexels) : F + tx(vent.fromFrontTexels);
  const ventZ = ventAnchor ? tx(ventAnchor.bottomCenterTexels) : tx(vent.zTexels);
  const [ventW, ventH] = vent.sizeTexels.map(tx);
  correspondence(semanticSupport(add('capGrey',
    [-W - tx(.38), ventU - ventW / 2, ventZ - ventH / 2],
    [-W + tx(.05), ventU + ventW / 2, ventZ + ventH / 2],
    { name: 'side_vent_support', bevel: .2, disableGenericSurface: true }),
  'sideVentPanel', vent.sizeTexels), 'side_vent');
  const rim = tx(.8);
  for (const [name, a, b] of [
    ['side_vent_rim_front', [-W - tx(.48), ventU - ventW / 2, ventZ - ventH / 2], [-W - tx(.38), ventU + ventW / 2, ventZ - ventH / 2 + rim]],
    ['side_vent_rim_back', [-W - tx(.48), ventU - ventW / 2, ventZ + ventH / 2 - rim], [-W - tx(.38), ventU + ventW / 2, ventZ + ventH / 2]],
    ['side_vent_rim_low', [-W - tx(.48), ventU - ventW / 2, ventZ - ventH / 2], [-W - tx(.38), ventU - ventW / 2 + rim, ventZ + ventH / 2]],
    ['side_vent_rim_high', [-W - tx(.48), ventU + ventW / 2 - rim, ventZ - ventH / 2], [-W - tx(.38), ventU + ventW / 2, ventZ + ventH / 2]],
  ]) add('coilBar', a, b, { name, bevel: 0 });
  placeV5Fitting('sideVentPanel', -W - tx(.50), { renderOrder: 7 });
} else {
  add('coil', [-W - tx(.16), B - tx(20.5), tx(7)], [-W - tx(.02), B - tx(2), tx(27)], {
    name: 'side_vent_panel', bevel: 0, disableGenericSurface: true,
    surfaceFaces: {
      left: 'ventField', right: 'ventField', front: 'ventField',
      back: 'ventField', top: 'ventField', bottom: 'ventField',
    },
  });
}

// A panel center may expand, but seam thickness never does.  Counts derive
// from available physical span, so larger cabinets gain divisions instead of
// stretching the reference's panel layout.
if (useV5) {
  const seed = v5Manifest.runtimePlacements.sidePanelSeeds;
  const rowZ = H - tx(seed.baseFaceHeightTexels - seed.row.zTexels);
  const thickness = tx(seed.thicknessTexels);
  correspondence(adaptiveStrip('side_panel_row', 'left', 0, rowZ, 2 * D, thickness, -W - tx(.18)), 'side_panel_row_seed');
  const extraRows = Math.max(0, Math.floor((H - tx(seed.baseFaceHeightTexels)) / tx(seed.addedRowPitchTexels)));
  for (let index = 1; index <= extraRows; index += 1) {
    adaptiveStrip('side_panel_row', 'left', 0, rowZ - tx(seed.addedRowPitchTexels * index), 2 * D, thickness, -W - tx(.18));
  }
  const upperU = F + tx(seed.upperColumn.fromFrontTexels);
  correspondence(adaptiveStrip('side_panel_column', 'left', upperU, (rowZ + HEADER_TOP) / 2,
    thickness, HEADER_TOP - rowZ, -W - tx(.19)), 'side_upper_column_seed');
  const lowerU = B - tx(seed.baseFaceWidthTexels - seed.lowerColumn.fromFrontTexels);
  correspondence(adaptiveStrip('side_panel_column', 'left', lowerU, rowZ / 2,
    thickness, rowZ, -W - tx(.19)), 'side_lower_column_seed');
  const extraColumns = Math.max(0, Math.floor((2 * D - tx(seed.baseFaceWidthTexels)) / tx(seed.addedColumnPitchTexels)));
  for (let index = 0; index < extraColumns; index += 1) {
    const u = tx((index - (extraColumns - 1) / 2) * seed.addedColumnPitchTexels);
    adaptiveStrip('side_panel_column', 'left', u, rowZ / 2, thickness, rowZ, -W - tx(.19));
  }
} else if (useV3) {
  const margin = tx(4);
  const faceWidth = 2 * D - 2 * margin;
  const faceHeight = HEADER_TOP - 2 * margin;
  const rowCount = Math.max(2, Math.floor(faceHeight / tx(28)));
  const columnCount = Math.max(2, Math.floor(faceWidth / tx(18)));
  for (let index = 1; index < rowCount; index += 1) {
    adaptiveStrip('side_panel_row', 'left', 0, margin + faceHeight * index / rowCount,
      faceWidth, tx(.55), -W - tx(.18));
  }
  for (let index = 1; index < columnCount; index += 1) {
    adaptiveStrip('side_panel_column', 'left', F + margin + faceWidth * index / columnCount,
      margin + faceHeight * .5, tx(.5), faceHeight, -W - tx(.19));
  }
}

// Rear mechanical structure. V6 gives texture-scale mechanisms a measured
// support surface instead of turning each thin line into chunky geometry.
const COIL_PLANE = B + tx(.3);
if (!useV6) for (let z = REAR_COIL_LO; z <= REAR_COIL_HI; z += tx(7)) {
  add('coilBar', [-W + tx(5), COIL_PLANE, z], [W - tx(5), COIL_PLANE + tx(.8), z + tx(1.15)], {
    name: 'rear_coil_run', bevel: 0,
  });
}
if (!useV6) for (let x = -W + tx(6); x <= W - tx(6); x += tx(4.2)) {
  add('coilBar', [x, COIL_PLANE - tx(.15), REAR_COIL_LO - tx(3)], [x + tx(.75), COIL_PLANE + tx(1), REAR_COIL_HI + tx(4)], {
    name: 'rear_coil_rail', bevel: 0,
  });
}
if (useV6) {
  const condenser = v5Fixed.condenserField;
  const [coilW, coilH] = useV7
    ? [condenserLayout.width, condenserLayout.height]
    : condenser.sizeTexels.map(tx);
  const coilX = useV7 ? condenserLayout.centerX : tx(condenser.uTexels);
  const coilZ = useV7 ? condenserLayout.centerZ : tx(condenser.zTexels);
  correspondence(semanticSupport(add('freezerSide', [coilX - coilW / 2, B + tx(.08), coilZ - coilH / 2],
    [coilX + coilW / 2, B + tx(.62), coilZ + coilH / 2],
    { name: 'rear_condenser_support', bevel: 0, disableGenericSurface: true }),
  'condenserField', [coilW, coilH]), 'rear_condenser_field');
  const frame = tx(.8);
  for (const [name, a, b] of [
    ['condenser_frame_left', [coilX - coilW / 2, B + tx(.62), coilZ - coilH / 2], [coilX - coilW / 2 + frame, B + tx(1.18), coilZ + coilH / 2]],
    ['condenser_frame_right', [coilX + coilW / 2 - frame, B + tx(.62), coilZ - coilH / 2], [coilX + coilW / 2, B + tx(1.18), coilZ + coilH / 2]],
    ['condenser_frame_bottom', [coilX - coilW / 2, B + tx(.62), coilZ - coilH / 2], [coilX + coilW / 2, B + tx(1.18), coilZ - coilH / 2 + frame]],
    ['condenser_frame_top', [coilX - coilW / 2, B + tx(.62), coilZ + coilH / 2 - frame], [coilX + coilW / 2, B + tx(1.18), coilZ + coilH / 2]],
  ]) add('coilBar', a, b, { name, bevel: 0 });
  if (useV7) adaptiveCondenserField(condenserLayout, condenserContract, B + tx(1.22));
  else placeV5Fitting('condenserField', B + tx(1.22), { renderOrder: 7 });

  const bay = { x: tx(.638), z: tx(13.492), w: tx(38.828), h: tx(22.747) };
  correspondence(semanticSupport(add('coil', [bay.x - bay.w / 2, B + tx(.10), bay.z - bay.h / 2],
    [bay.x + bay.w / 2, B + tx(.70), bay.z + bay.h / 2],
    { name: 'rear_machine_bay_back', bevel: 0 }), 'rearMachineBay', [38.828, 22.747]), 'rear_machine_bay');
  const fan = v5Fixed.fanGrille;
  semanticSupport(add('capGrey', [tx(fan.uTexels - 7), B + tx(.72), tx(fan.zTexels - 7.5)],
    [tx(fan.uTexels + 7), B + tx(2.45), tx(fan.zTexels + 7.5)],
    { name: 'rear_fan_housing', bevel: .35 }), 'fanGrille', [14, 15]);
  add('coil', [tx(fan.uTexels - 6), B + tx(2.45), tx(fan.zTexels - 6)],
    [tx(fan.uTexels + 6), B + tx(2.65), tx(fan.zTexels + 6)],
    { name: 'rear_fan_aperture', bevel: 0 });
  placeV5Fitting('fanGrille', B + tx(2.70), { renderOrder: 9 });

  add('capGrey', [tx(1.5), B + tx(.72), tx(3)], [tx(16.8), B + tx(4.4), tx(15.8)], {
    name: 'compressor_body', bevel: 1.1, taperX: .7, taperY: .35,
  });
  add('freezerShelf', [tx(3.2), B + tx(4.35), tx(13.8)], [tx(15.1), B + tx(4.75), tx(16.4)], {
    name: 'compressor_cap', bevel: .65, taperX: .9,
  });
  add('coilBar', [tx(2.3), B + tx(4.5), tx(4.1)], [tx(15.8), B + tx(4.8), tx(6.0)], {
    name: 'compressor_base', bevel: 0,
  });
  fixedFitting('compressorPlate', 'back', tx(3.1), tx(9.9), 6.2, 5.2, B + tx(4.86), {
    layer: 'label', renderOrder: 8,
  });
  add('copper', [tx(15), B + tx(3.8), tx(9.8)], [tx(20), B + tx(4.6), tx(11.1)], {
    name: 'copper_pipe', bevel: 0,
  });
} else {
  add('coil', [-W + tx(4), B + tx(.15), tx(2)], [W - tx(4), B + tx(9), tx(24)], {
    name: 'rear_machine_bay', bevel: .35,
  });
  add('capGrey', [-W + tx(6), B + tx(8.5), tx(5)], [-tx(2), B + tx(13), tx(20)], {
    name: 'rear_fan', bevel: .4,
  });
  if (useV5) placeV5Fitting('fanGrille', B + tx(13.15));
  else fixedFitting('fanGrille', 'back', -W + tx(13), tx(12.5), 12, 12, B + tx(13.15));
  add('coil', [tx(2), B + tx(8.3), tx(3)], [W - tx(5), B + tx(14), tx(18)], {
    name: 'compressor', bevel: 1.1, taperX: .5, taperY: .4,
  });
  add('copper', [W - tx(7), B + tx(12.5), tx(11)], [W - tx(2), B + tx(13.3), tx(12.2)], {
    name: 'copper_pipe', bevel: 0,
  });
}
for (const x of [-W + tx(4), W - tx(8)]) {
  add('coil', [x, F + tx(3), -tx(2)], [x + tx(5), B - tx(3), 0], { name: 'foot', bevel: 0 });
}

// Contents are real objects; their fine labels will be semantic decals.
const cartonFittings = ['cartonCovid', 'cartonMmr', 'cartonFlu', 'cartonBooster'];
const vialFittings = ['vialCovid', 'vialMmr', 'vialFlu', 'vialPolio'];
let cartonFittingIndex = 0;
let vialFittingIndex = 0;
const carton = (x, z, width, height, accent = 'medicalBlue') => {
  if (!showContents) return;
  const packageKind = accent === 'capRed' ? 'medicineTan'
    : (accent === 'capGrey' ? 'medicineCool' : 'medicinePaper');
  add(packageKind, [x - width / 2, F + tx(3), z], [x + width / 2, F + tx(8), z + height], {
    // Stock is intentionally blocky: label graphics provide its readable detail.
    name: 'medicine_carton', bevel: 0,
  });
  const fittingName = useV2 ? cartonFittings[cartonFittingIndex++ % cartonFittings.length] : 'cartonLabel';
  fixedFitting(fittingName, 'front', x, z + height * .50, useV2 ? 5.3 : 4.8, useV2 ? 7.4 : 4.2, F + tx(2.82));
};
const vial = (x, z, cap = 'capRed', scale = 1, body = 'bottleAmber') => {
  if (!showContents) return;
  const w = tx(3.2) * scale;
  add(body, [x - w / 2, F + tx(3.3), z], [x + w / 2, F + tx(6.2), z + tx(6.4) * scale], {
    name: 'medicine_vial', bevel: 0,
  });
  add(cap, [x - w * .54, F + tx(3.15), z + tx(6.2) * scale], [x + w * .54, F + tx(6.35), z + tx(7.6) * scale], {
    name: 'vial_cap', bevel: 0,
  });
  const fittingName = useV2 ? vialFittings[vialFittingIndex++ % vialFittings.length] : 'vialLabel';
  fixedFitting(fittingName, 'front', x, z + tx(3.25) * scale, useV2 ? 2.8 : 2.6, useV2 ? 4.1 : 2.8, F + tx(3.12));
};

for (const [x, accent] of [[-12, 'capRed'], [-4, 'capBlue'], [5, 'capGrey'], [12, 'medicalBlue']]) {
  carton(tx(x), shelfLevels[2] + tx(1.5), tx(6.2), tx(10), accent);
}
for (const [row, shelf] of [[0, shelfLevels[1]], [1, shelfLevels[0]]]) {
  const capKinds = ['capRed', 'capBlue', 'capGreen'];
  [-12, -6, 0, 6, 12].forEach((x, index) => vial(
    tx(x), shelf + tx(1.5), capKinds[(index + row) % capKinds.length], row ? .92 : 1,
    (index + row) % 2 ? 'bottleWhite' : 'bottleAmber',
  ));
}
carton(tx(-10), OPEN_LO + tx(1.5), tx(8), tx(11), 'capRed');
carton(tx(0), OPEN_LO + tx(1.5), tx(8), tx(12), 'medicalBlue');
vial(tx(10), OPEN_LO + tx(1.5), 'capGrey', 1.25, 'bottleWhite');

// Diagnostic materials preserve exact geometry while exposing machine-readable
// evidence to the v4 authoring compiler. These passes never enter the shipped
// material; they are an authoring contract for image-model paintovers.
let diagnosticPalette = null;
let diagnosticLegend = null;
if (diagnostic === 'parts' || diagnostic === 'part-id') {
  const meshes = g.children.filter((node) => node.isMesh);
  diagnosticPalette = [new THREE.Color('#101116')];
  diagnosticLegend = [];
  meshes.forEach((mesh, index) => {
    const color = new THREE.Color().setHSL((index * .61803398875) % 1, .62, .56);
    diagnosticPalette.push(color);
    mesh.material = new THREE.MeshBasicMaterial({ color, toneMapped: false });
    diagnosticLegend.push({
      id: index + 1,
      name: mesh.name,
      kind: mesh.userData.kind ?? null,
      color: `#${color.getHexString()}`,
    });
  });
} else if (diagnostic === 'faces' || diagnostic === 'face-id') {
  const faceColors = ['#ef5350', '#ab47bc', '#42a5f5', '#26a69a', '#ffee58', '#ffa726'];
  diagnosticPalette = [new THREE.Color('#101116'), ...faceColors.map((color) => new THREE.Color(color))];
  diagnosticLegend = [
    ['right', faceColors[0]], ['left', faceColors[1]],
    ['top', faceColors[2]], ['bottom', faceColors[3]],
    ['back', faceColors[4]], ['front', faceColors[5]],
  ].map(([name, color], index) => ({ id: index + 1, name, color }));
  const faceMaterial = new THREE.ShaderMaterial({
    vertexShader: 'varying vec3 vN; void main(){vN=normalize(normalMatrix*normal);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
    fragmentShader: `varying vec3 vN; void main(){vec3 n=normalize(vN);vec3 a=abs(n);vec3 c;if(a.x>=a.y&&a.x>=a.z)c=n.x>0.0?vec3(.937,.325,.314):vec3(.671,.278,.737);else if(a.y>=a.z)c=n.y>0.0?vec3(.255,.647,.961):vec3(.149,.651,.604);else c=n.z>0.0?vec3(1.,.933,.345):vec3(1.,.655,.149);gl_FragColor=vec4(c,1.);}`,
  });
  g.children.filter((node) => node.isMesh).forEach((mesh) => { mesh.material = faceMaterial; });
} else if (diagnostic === 'normal' || diagnostic === 'face-normal') {
  diagnosticLegend = {
    encoding: 'rgb = world_normal * 0.5 + 0.5',
    axes: { right: '#ff8080', left: '#008080', top: '#80ff80', bottom: '#800080', back: '#8080ff', front: '#808000' },
  };
  const normalMaterial = new THREE.ShaderMaterial({
    vertexShader: 'varying vec3 vN;void main(){vN=normalize(mat3(modelMatrix)*normal);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
    fragmentShader: 'varying vec3 vN;void main(){gl_FragColor=vec4(normalize(vN)*.5+.5,1.0);}',
    toneMapped: false,
  });
  g.children.filter((node) => node.isMesh).forEach((mesh) => { mesh.material = normalMaterial; });
} else if (diagnostic === 'depth' || diagnostic === 'linear-depth') {
  diagnosticLegend = { encoding: 'black = camera near; white = camera far; orthographic linear clip depth' };
  const depthMaterial = new THREE.ShaderMaterial({
    vertexShader: 'varying float vDepth;void main(){vec4 clip=projectionMatrix*modelViewMatrix*vec4(position,1.0);vDepth=clip.z/clip.w*.5+.5;gl_Position=clip;}',
    fragmentShader: 'varying float vDepth;void main(){float d=clamp(vDepth,0.0,1.0);gl_FragColor=vec4(vec3(d),1.0);}',
    toneMapped: false,
  });
  g.children.filter((node) => node.isMesh).forEach((mesh) => { mesh.material = depthMaterial; });
} else if (diagnostic === 'anchors' || diagnostic === 'anchor-id') {
  const anchorColors = [
    '#e53935', '#fb8c00', '#fdd835',
    '#43a047', '#00acc1', '#1e88e5',
    '#5e35b1', '#8e24aa', '#d81b60',
  ];
  diagnosticLegend = [
    'bottom-left', 'bottom-center', 'bottom-right',
    'middle-left', 'center', 'middle-right',
    'top-left', 'top-center', 'top-right',
  ].map((name, index) => ({ id: index + 1, name, color: anchorColors[index] }));
  const colors = anchorColors.map((hex) => new THREE.Color(hex));
  const anchorMaterial = new THREE.ShaderMaterial({
    uniforms: Object.fromEntries(colors.map((color, index) => [`uC${index}`, { value: color }])),
    vertexShader: 'varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
    fragmentShader: `
      varying vec2 vUv;
      uniform vec3 uC0;uniform vec3 uC1;uniform vec3 uC2;
      uniform vec3 uC3;uniform vec3 uC4;uniform vec3 uC5;
      uniform vec3 uC6;uniform vec3 uC7;uniform vec3 uC8;
      void main(){
        int x=int(clamp(floor(vUv.x*3.0),0.0,2.0));
        int y=int(clamp(floor(vUv.y*3.0),0.0,2.0));
        int i=y*3+x;vec3 c=uC0;
        if(i==1)c=uC1;else if(i==2)c=uC2;else if(i==3)c=uC3;
        else if(i==4)c=uC4;else if(i==5)c=uC5;else if(i==6)c=uC6;
        else if(i==7)c=uC7;else if(i==8)c=uC8;
        float line=min(abs(fract(vUv.x*3.0)-.5),abs(fract(vUv.y*3.0)-.5));
        if(line>.47)c*=.35;
        gl_FragColor=vec4(c,1.0);
      }`,
    toneMapped: false,
  });
  g.children.filter((node) => node.isMesh).forEach((mesh) => { mesh.material = anchorMaterial; });
}

const targetY = H * STYLE.texel * .49;
const applyOrbitCamera = (yawDegrees, elevationDegrees) => {
  orbitYaw = yawDegrees;
  orbitElevation = Math.max(-12, Math.min(24, elevationDegrees));
  const yaw = THREE.MathUtils.degToRad(orbitYaw);
  const elevation = THREE.MathUtils.degToRad(orbitElevation);
  const radius = 8;
  camera.position.set(
    Math.sin(yaw) * radius,
    targetY + Math.tan(elevation) * radius,
    -Math.cos(yaw) * radius,
  );
};
if (view === 'orbit') applyOrbitCamera(orbitYaw, orbitElevation);
else if (view === 'front') camera.position.set(0, targetY, -8);
else if (view === 'side') camera.position.set(-8, targetY, 0);
else if (view === 'back') camera.position.set(0, targetY, 9);
else if (view === 'backIso') camera.position.set(-5.2, targetY + .35, 7.2);
else camera.position.set(-4.8, targetY + .35, -6.8);
camera.lookAt(0, targetY, 0);
camera.zoom = autoFitCamera ? .83 / Math.max(sx, sy, sz) : .83;
camera.updateProjectionMatrix();

const renderTarget = new THREE.WebGLRenderTarget(320, 400, {
  minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, generateMipmaps: false,
});
const usedKinds = [...new Set(g.children.map((node) => node.userData.kind).filter(Boolean))];
const materialPalette = usedKinds.flatMap((kind) => {
  const family = MATS[kind];
  return [
    new THREE.Color(family.shade).multiplyScalar(.72), new THREE.Color(family.shade),
    new THREE.Color(family.base), new THREE.Color(family.lit),
    new THREE.Color(family.lit).multiplyScalar(1.10),
  ];
});
const fittingPalette = [
  '#1a2023', '#30393c', '#4e5b5e', '#778281', '#aebcb8', '#dae0d7',
  '#315b7d', '#4f80a2', '#9e3e3d', '#578f54', '#d5973e',
].map((color) => new THREE.Color(color));
const palette = diagnosticPalette ?? [new THREE.Color(backgroundHex), ...materialPalette, ...fittingPalette];
const postFragment = diagnostic || (useV2 && !diagnostic)
  ? 'varying vec2 vUv;uniform sampler2D uMap;void main(){gl_FragColor=texture2D(uMap,vUv);}'
  : `varying vec2 vUv;uniform sampler2D uMap;uniform vec3 uPalette[${palette.length}];void main(){vec3 s=texture2D(uMap,vUv).rgb;vec3 b=uPalette[0];float d=dot(s-b,s-b);for(int i=1;i<${palette.length};i++){vec3 c=uPalette[i];float n=dot(s-c,s-c);if(n<d){b=c;d=n;}}gl_FragColor=vec4(b,1.);}`;
const postScene = new THREE.Scene();
const postCamera = new THREE.Camera();
postScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({
  uniforms: { uMap: { value: renderTarget.texture }, uPalette: { value: palette } },
  vertexShader: 'varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position,1.);}',
  fragmentShader: postFragment,
  depthTest: false, depthWrite: false,
}))); 
const draw = () => {
  renderer.setRenderTarget(renderTarget);
  renderer.render(scene, camera);
  renderer.setRenderTarget(null);
  renderer.render(postScene, postCamera);
};
draw();

window.__SEMANTIC_FREEZER_STATS__ = {
  ready: true, view, diagnostic, textureVersion, scale: [sx, sy, sz],
  faceBasis: v5Manifest?.faceBasis ?? null,
  textureLayers: v5Manifest?.textureLayers ?? [],
  diagnosticLegend,
  camera: { yaw: orbitYaw, elevation: orbitElevation, autoFit: autoFitCamera },
  triangles: triangleCount(g),
  parts: g.children.length,
  decals: g.children.filter((node) => node.name.startsWith('decal_')).length,
  shelfCount: shelfLevels.length,
  rigidPartSizes: g.children.filter((node) => node.userData.rigidTexelSize)
    .map((node) => [node.name, node.userData.rigidTexelSize]).sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b))),
  fixedFittingSizes: g.children.filter((node) => node.userData.fixedTexelSize)
    .map((node) => [node.name, node.userData.fixedTexelSize]).sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b))),
  correspondenceIds: [...new Set(g.children.flatMap((node) => [
    ...(node.userData.correspondenceIds ?? []),
    ...(node.userData.correspondenceId ? [node.userData.correspondenceId] : []),
  ]))].sort(),
  correspondenceFeatureCount: v5Manifest?.correspondence?.featureCount ?? 0,
  fittingPlacements: g.children.filter((node) => node.userData.fixedTexelSize).map((node) => {
    const face = node.userData.mountPlane;
    const sideFace = face === 'left' || face === 'right';
    const centerU = (sideFace ? node.position.z : node.position.x) / STYLE.texel;
    const centerZ = node.position.y / STYLE.texel;
    return {
      id: node.userData.fittingRole,
      face, layer: node.userData.textureLayer,
      centerTexels: [centerU, centerZ],
      sizeTexels: node.userData.fixedTexelSize,
      planeTexels: (sideFace ? node.position.x : node.position.z) / STYLE.texel,
      renderOrder: node.renderOrder,
      edgeDistancesTexels: sideFace ? {
        front: centerU - F,
        back: B - centerU,
        bottom: centerZ,
        headerTop: HEADER_TOP - centerZ,
      } : {
        left: centerU + W,
        right: W - centerU,
        bottom: centerZ,
        headerTop: HEADER_TOP - centerZ,
        panelLeft: condenserLayout ? centerU - condenserLayout.left : null,
        panelRight: condenserLayout ? condenserLayout.right - centerU : null,
        panelBottom: condenserLayout ? centerZ - condenserLayout.bottom : null,
        panelTop: condenserLayout ? condenserLayout.top - centerZ : null,
      },
    };
  }),
  semanticSupports: g.children.filter((node) => node.userData.semanticSupport).map((node) => ({
    id: node.userData.semanticSupport,
    sizeTexels: node.userData.measuredTexelSize,
    mesh: node.name,
  })).sort((a, b) => a.id.localeCompare(b.id)),
  adaptiveSurfaceCounts: [...new Set(g.children
    .map((node) => node.userData.adaptiveRole).filter(Boolean))]
    .map((name) => [name, g.children.filter((node) => node.userData.adaptiveRole === name).length])
    .sort(),
  adaptiveTexturePanels: g.children.filter((node) => node.userData.adaptiveTexture)
    .map((node) => node.userData.adaptiveTexture),
  repeatedStructureCounts: [
    ['rear_coil_run', g.children.filter((node) => node.name === 'rear_coil_run').length],
    ['rear_coil_rail', g.children.filter((node) => node.name === 'rear_coil_rail').length],
    ['shelf', shelfLevels.length],
  ],
  errors: [],
};
window.__SEMANTIC_FREEZER_SET_CAMERA__ = (yaw, elevation) => {
  applyOrbitCamera(Number(yaw), Number(elevation));
  camera.lookAt(0, targetY, 0);
  camera.updateProjectionMatrix();
  window.__SEMANTIC_FREEZER_STATS__.camera = {
    yaw: orbitYaw, elevation: orbitElevation, autoFit: autoFitCamera,
  };
  draw();
};
