import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import {
  createFridgeNineSliceMaterial,
  setFridgeNineSliceScale,
} from './fridgeNineSliceMaterial.js';
import { repeatedModuleCenters } from './adaptiveAssembly.js';

export const PIXELS_PER_UNIT = 32;

const materialCache = new Map();

export const FRIDGE_ADAPTIVE_ATLAS = Object.freeze({
  atlasSizePx: [256, 256],
  regions: Object.freeze({
    cream: { rectPx: [0, 192, 64, 64], mode: 'nine_slice', borderPx: [8, 8] },
    steel: { rectPx: [64, 128, 64, 128], mode: 'nine_slice', borderPx: [8, 8] },
    teal: { rectPx: [128, 192, 64, 64], mode: 'nine_slice', borderPx: [8, 8] },
    glass: { rectPx: [192, 128, 64, 128], mode: 'repeat_center', borderPx: [0, 0], transparent: true },
    grille: { rectPx: [0, 96, 128, 32], mode: 'fixed_ends_repeat_x', borderPx: [8, 4] },
    screen: { rectPx: [128, 96, 64, 32], mode: 'fixed_decal' },
    handle: { rectPx: [192, 64, 32, 64], mode: 'fixed_decal' },
    plum: { rectPx: [192, 64, 32, 64], mode: 'nine_slice', borderPx: [4, 4] },
    decal: { rectPx: [224, 96, 32, 32], mode: 'fixed_decal', transparent: true },
  }),
});

/** Exact geometry and texture allocation for complete 32 px door bays. */
export function createFridgeVariantPlan(doorCount = 1) {
  const doors = Math.max(1, Math.round(doorCount));
  const endCapsPx = 8;
  const bayWidthPx = 32;
  const bodyWidthPx = endCapsPx + doors * bayWidthPx;
  const doorCentersPx = repeatedModuleCenters(doors, bayWidthPx);
  return {
    doorCount: doors,
    bodyWidthPx,
    bodyHeightPx: 96,
    doorBayWidthPx: bayWidthPx,
    doorCentersPx,
    geometryPolicy: 'insert_complete_door_bays',
    textureTargetPx: {
      carcass: [bodyWidthPx, 96],
      condenser: [bodyWidthPx, 16],
      crown: [bodyWidthPx, 9],
      doorBay: [bayWidthPx, 60],
    },
    fixedDetails: {
      displayCount: 1,
      handleCentersPx: [...doorCentersPx],
      hingeCentersPx: [...doorCentersPx],
    },
  };
}

export function createFaceMaterial(texture, pixelX, pixelY, pixelWidth, pixelHeight, atlasWidth, atlasHeight) {
  const key = [texture.uuid, pixelX, pixelY, pixelWidth, pixelHeight, atlasWidth, atlasHeight].join(':');
  if (materialCache.has(key)) return materialCache.get(key);
  const clonedTexture = texture.clone();
  clonedTexture.magFilter = THREE.NearestFilter;
  clonedTexture.minFilter = THREE.NearestFilter;
  clonedTexture.generateMipmaps = false;
  clonedTexture.wrapS = clonedTexture.wrapT = THREE.ClampToEdgeWrapping;
  clonedTexture.repeat.set(pixelWidth / atlasWidth, pixelHeight / atlasHeight);
  clonedTexture.offset.set(pixelX / atlasWidth, 1 - ((pixelY + pixelHeight) / atlasHeight));
  clonedTexture.needsUpdate = true;
  const material = new THREE.MeshStandardMaterial({
    map: clonedTexture,
    emissiveMap: clonedTexture,
    emissive: new THREE.Color(0xffffff),
    emissiveIntensity: 0.82,
    flatShading: true,
    roughness: 0.9,
  });
  materialCache.set(key, material);
  return material;
}

export function enableTiledCenter(material, { tilePixels = 8, atlasPixels = 256, axis = 'x' } = {}) {
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uTilePeriod = { value: tilePixels / PIXELS_PER_UNIT };
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vFridgeLocal;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvFridgeLocal = position;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vFridgeLocal;\nuniform float uTilePeriod;')
      .replace('#include <map_fragment>', `
        #include <map_fragment>
        float tileCoord = fract(vFridgeLocal.${axis} / uTilePeriod);
        float tiledLine = step(tileCoord, 0.18);
        diffuseColor.rgb *= mix(1.0, 0.38, tiledLine);
      `);
    material.userData.tileUniforms = shader.uniforms;
  };
  material.customProgramCacheKey = () => `fridge-tile-${tilePixels}-${axis}-${atlasPixels}`;
  material.needsUpdate = true;
  return material;
}

export function sliceCoordinate(value, sourceHalf, margin, targetScale) {
  const sign = Math.sign(value);
  const distance = Math.abs(value);
  const inner = Math.max(0, sourceHalf - margin);
  if (distance <= inner) return value * targetScale;
  return sign * (inner * targetScale + (distance - inner));
}

export function deformSocketPosition(rest, sourceHalf, margins, targetScale, out = new THREE.Vector3()) {
  out.set(
    sliceCoordinate(rest.x, sourceHalf.x, margins.x, targetScale.x),
    sliceCoordinate(rest.y, sourceHalf.y, margins.y, targetScale.y),
    sliceCoordinate(rest.z, sourceHalf.z, margins.z, targetScale.z),
  );
  return out;
}

export function updateFridgeSockets(root, targetScale) {
  const sourceHalf = new THREE.Vector3(20, 14, 48).divideScalar(PIXELS_PER_UNIT);
  const margins = new THREE.Vector3(4, 4, 8).divideScalar(PIXELS_PER_UNIT);
  root.traverse((node) => {
    if (!node.name.startsWith('socket_')) return;
    const restPx = node.userData.restPositionPx;
    if (!restPx) return;
    const rest = new THREE.Vector3(...restPx).divideScalar(PIXELS_PER_UNIT);
    deformSocketPosition(rest, sourceHalf, margins, targetScale, node.position);
  });
}

function prepareAdaptiveLayers(root) {
  root.traverse((node) => {
    if (!node.isMesh || !node.userData.texturePolicy) return;
    node.userData.restPosition = node.position.toArray();
    node.userData.restScale = node.scale.toArray();
    const sourceMaterials = Array.isArray(node.material) ? node.material : [node.material];
    const materials = sourceMaterials.map((source) => {
      const material = source.clone();
      if (source.map) {
        material.map = source.map.clone();
        material.map.wrapS = material.map.wrapT = THREE.RepeatWrapping;
        material.map.magFilter = material.map.minFilter = THREE.NearestFilter;
        material.map.generateMipmaps = false;
        material.userData.baseRepeat = material.map.repeat.toArray();
      }
      if (source.emissiveMap === source.map) material.emissiveMap = material.map;
      return material;
    });
    node.material = Array.isArray(node.material) ? materials : materials[0];
  });
}

function updateAdaptiveLayers(root, targetScale) {
  const sourceHalf = new THREE.Vector3(20, 15, 48).divideScalar(PIXELS_PER_UNIT);
  const margins = new THREE.Vector3(4, 4, 8).divideScalar(PIXELS_PER_UNIT);
  root.traverse((node) => {
    const policy = node.userData.texturePolicy;
    const restPosition = node.userData.restPosition;
    const restScale = node.userData.restScale;
    if (!node.isMesh || !policy || !restPosition || !restScale) return;

    deformSocketPosition(
      new THREE.Vector3(...restPosition), sourceHalf, margins, targetScale, node.position,
    );
    const scale = new THREE.Vector3(...restScale);
    if (policy !== 'fixed_1to1') scale.multiply(targetScale);
    node.scale.copy(scale);

    // Tiled structural fields allocate more texels as the part grows. Fixed
    // decal islands never enter this branch and therefore stay exactly 1:1.
    if (policy === 'tile_center' || policy === 'structural' ||
        policy === 'repeat_per_bay' || policy === 'fixed_ends_repeat_x') {
      const materials = Array.isArray(node.material) ? node.material : [node.material];
      for (const material of materials) {
        if (material?.userData.adaptiveNineSlice) {
          setFridgeNineSliceScale(material, targetScale.x, targetScale.z);
        }
        if (!material?.map || !material.userData.baseRepeat) continue;
        const [rx, ry] = material.userData.baseRepeat;
        material.map.repeat.set(rx * targetScale.x, ry * targetScale.z);
        material.map.needsUpdate = true;
      }
    }
  });
}

export function attachSocketDecal(root, socketName, material, widthPx, heightPx) {
  const socket = root.getObjectByName(socketName);
  if (!socket) throw new Error(`Missing fridge socket ${socketName}`);
  const plane = new THREE.Mesh(
    new THREE.PlaneGeometry(widthPx / PIXELS_PER_UNIT, heightPx / PIXELS_PER_UNIT),
    material,
  );
  plane.name = `${socketName}_fixed_decal`;
  plane.position.set(0, 0, 0);
  socket.add(plane);
  return plane;
}

export async function loadProductionFridge({
  url = '/models/vaccine-fridge.glb',
  // Hybrid atlas: GPT-generated seamless material fields in scalable centers,
  // authority-extracted pixels for identity-critical decals and protected ends.
  atlasUrl = '/textures/vaccine-fridge-adaptive-gpt-v2.png',
  applyAtlas = false,
  attachTestDecals = false,
} = {}) {
  const needsAtlas = applyAtlas || attachTestDecals;
  const [gltf, atlas] = await Promise.all([
    new GLTFLoader().loadAsync(url),
    needsAtlas ? new THREE.TextureLoader().loadAsync(atlasUrl) : Promise.resolve(null),
  ]);
  if (atlas) {
    atlas.colorSpace = THREE.SRGBColorSpace;
    atlas.magFilter = atlas.minFilter = THREE.NearestFilter;
    atlas.generateMipmaps = false;
  }
  const root = gltf.scene;
  root.userData.textureAuthority = applyAtlas
    ? 'gpt_material_fields+locked_fixed_decals'
    : 'locked_exported_materials';
  const regionMaterial = (key) => {
    const region = FRIDGE_ADAPTIVE_ATLAS.regions[key];
    return createFaceMaterial(atlas, ...region.rectPx, ...FRIDGE_ADAPTIVE_ATLAS.atlasSizePx);
  };
  const adaptiveRegionMaterial = (key) => {
    const region = FRIDGE_ADAPTIVE_ATLAS.regions[key];
    const [, , width, height] = region.rectPx;
    return createFridgeNineSliceMaterial(atlas, {
      atlasRectPx: region.rectPx,
      atlasSizePx: FRIDGE_ADAPTIVE_ATLAS.atlasSizePx,
      sourceSizePx: [width, height],
      protectedBorderPx: region.borderPx,
      transparent: region.transparent,
    });
  };
  // The approved Blender file contains the reference-matched, baked pixel
  // materials. The game scene is intentionally unlit, so mirror their base
  // maps into emissive without replacing color, alpha, or texture detail.
  if (!applyAtlas) root.traverse((node) => {
    if (!node.isMesh) return;
    const materials = Array.isArray(node.material) ? node.material : [node.material];
    for (const material of materials) {
      if (!material) continue;
      if (material.map) {
        material.map.colorSpace = THREE.SRGBColorSpace;
        material.map.magFilter = material.map.minFilter = THREE.NearestFilter;
        material.map.generateMipmaps = false;
        material.emissiveMap = material.map;
        material.emissive.set(0xffffff);
      } else {
        material.emissive.copy(material.color);
      }
      material.emissiveIntensity = 0.82;
      material.flatShading = true;
      material.needsUpdate = true;
    }
  });
  if (applyAtlas) root.traverse((node) => {
      if (!node.isMesh) return;
      const n = node.name.toLowerCase();
      if (n.includes('frame') || n.includes('crown')) node.material = adaptiveRegionMaterial('cream');
      else if (n.includes('side') || n.includes('shelf')) node.material = adaptiveRegionMaterial('steel');
      else if (n.includes('door') || n.includes('base')) node.material = adaptiveRegionMaterial('teal');
      else if (n.includes('glass')) {
        node.material = adaptiveRegionMaterial('glass');
      } else if (n.includes('grille')) {
        node.material = adaptiveRegionMaterial('grille');
      } else if (n.includes('plinth')) node.material = adaptiveRegionMaterial('plum');
      else if (n.includes('handle')) node.material = regionMaterial('handle');
    });
  root.userData.targetScale = new THREE.Vector3(1, 1, 1);
  prepareAdaptiveLayers(root);
  root.userData.setAdaptiveScale = (x = 1, y = 1, z = 1) => {
    root.userData.targetScale.set(x, y, z);
    updateAdaptiveLayers(root, root.userData.targetScale);
    updateFridgeSockets(root, root.userData.targetScale);
  };
  updateAdaptiveLayers(root, root.userData.targetScale);
  updateFridgeSockets(root, root.userData.targetScale);
  if (attachTestDecals) {
    attachSocketDecal(root, 'socket_display', regionMaterial('screen'), 10, 4);
    attachSocketDecal(root, 'socket_glass_decal', regionMaterial('decal'), 6, 6);
  }
  return { root, atlas };
}
