import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import {
  createAnalyticBoxMaterial,
  updateAnalyticBoxScale,
} from '../shaders/index.js';

const loader = new GLTFLoader();
const cache = new Map();
const controlMaterials = new WeakMap();
const analyticMaterials = new WeakMap();
const priorRenderHooks = new WeakMap();

const ANALYTIC_SIDE_STYLE = Object.freeze({
  baseColor: '#617a80',
  shadowColor: '#4a5d62',
  highlightColor: '#76949c',
  outlineColor: '#38474a',
  tints: Object.freeze({ top: 1.09, front: 1, side: 0.858, back: 0.9, bottom: 0.74 }),
  outline: 1 / 32,
  catchWidth: 2 / 32,
  inset: 4 / 32,
  seamWidth: 0.75 / 32,
  gatePadding: 1 / 32,
});

function setAnalyticSidePanel(root, enabled) {
  let changed = 0;
  root.traverse((node) => {
    if (!node.isMesh || node.name !== 'nano_tile_side_panel') return;
    if (!controlMaterials.has(node)) {
      controlMaterials.set(node, node.material);
      priorRenderHooks.set(node, node.onBeforeRender);
    }
    if (!enabled) {
      node.material = controlMaterials.get(node);
      node.onBeforeRender = priorRenderHooks.get(node);
      node.userData.analyticMaterialPilot = false;
      changed += 1;
      return;
    }
    let material = analyticMaterials.get(node);
    if (!material) {
      node.geometry.computeBoundingBox();
      const bounds = node.geometry.boundingBox;
      material = createAnalyticBoxMaterial({
        boundsMin: bounds.min,
        boundsMax: bounds.max,
        ...ANALYTIC_SIDE_STYLE,
      });
      analyticMaterials.set(node, material);
    }
    node.material = material;
    node.userData.analyticMaterialPilot = true;
    node.onBeforeRender = () => updateAnalyticBoxScale(material, node);
    changed += 1;
  });
  root.userData.analyticSidePanel = enabled;
  return changed;
}

function configureSourcePixels(root) {
  root.traverse((node) => {
    if (!node.isMesh) return;
    const materials = Array.isArray(node.material) ? node.material : [node.material];
    for (const material of materials) {
      if (!material) continue;
      if (material.map) {
        material.map.colorSpace = THREE.SRGBColorSpace;
        material.map.magFilter = THREE.NearestFilter;
        material.map.minFilter = THREE.NearestFilter;
        material.map.generateMipmaps = false;
        material.emissiveMap = material.map;
        material.emissive.set(0xffffff);
      } else if (material.color) {
        material.emissive.copy(material.color);
      }
      material.emissiveIntensity = 0.82;
      material.flatShading = true;
      material.needsUpdate = true;
    }
  });
}

async function masterFor(doors) {
  const count = Math.max(1, Math.min(3, Math.round(doors)));
  if (!cache.has(count)) {
    cache.set(count, loader.loadAsync(`/models/vaccine-fridge-voxel-${count}door.glb`)
      .then(({ scene }) => {
        configureSourcePixels(scene);
        return scene;
      }));
  }
  return cache.get(count);
}

export async function loadVoxelFridge(doors = 1, { analyticSidePanel = false } = {}) {
  const count = Math.max(1, Math.min(3, Math.round(doors)));
  const root = (await masterFor(count)).clone(true);
  root.userData.doorCount = count;
  root.userData.resizeMode = 'authority_grid_insert_complete_32px_door_bays';
  root.userData.voxelWorldSize = 1 / 32;
  root.userData.textureMode = count === 1
    ? 'reference_measured_v5_microfields+anchored_material_details+locked_identity_decals'
    : 'reference_measured_v5_microfields+semantic_bay_repeat+anchored_material_details+locked_identity_decals';
  const baseTextureMode = root.userData.textureMode;
  root.userData.setAnalyticSidePanel = (enabled = true) => {
    const changed = setAnalyticSidePanel(root, enabled);
    root.userData.textureMode = `${baseTextureMode}${enabled ? '+uvless_analytic_side_pilot' : ''}`;
    return changed;
  };
  if (analyticSidePanel) {
    const panelCount = root.userData.setAnalyticSidePanel(true);
    if (panelCount !== 1) throw new Error(`Expected one analytic side panel, found ${panelCount}`);
  }
  return root;
}
