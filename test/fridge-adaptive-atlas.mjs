import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import * as THREE from 'three';
import {
  createFridgeNineSliceMaterial,
  nineSliceAxisPixel,
  setFridgeNineSliceTargetSize,
} from '../src/production/fridgeNineSliceMaterial.js';
import {
  createFridgeVariantPlan,
  FRIDGE_ADAPTIVE_ATLAS,
} from '../src/production/fridgeArchitecture.js';

// A 2 px protected edge remains literal while the 4 px center repeats.
const mapped = Array.from({ length: 12 }, (_, pixel) => nineSliceAxisPixel(pixel, 8, 2, 12));
assert.deepEqual(mapped, [0, 1, 2, 3, 4, 5, 2, 3, 4, 5, 6, 7]);

for (const doors of [1, 2, 3]) {
  const plan = createFridgeVariantPlan(doors);
  assert.equal(plan.bodyWidthPx, 8 + doors * 32);
  assert.equal(plan.doorCentersPx.length, doors);
  assert.equal(plan.fixedDetails.handleCentersPx.length, doors);
  assert.deepEqual(plan.textureTargetPx.doorBay, [32, 60]);
}
assert.deepEqual(createFridgeVariantPlan(3).doorCentersPx, [-32, 0, 32]);

const texture = new THREE.Texture();
const material = createFridgeNineSliceMaterial(texture, {
  atlasRectPx: FRIDGE_ADAPTIVE_ATLAS.regions.cream.rectPx,
  atlasSizePx: FRIDGE_ADAPTIVE_ATLAS.atlasSizePx,
  sourceSizePx: [64, 64],
  protectedBorderPx: [8, 8],
});
setFridgeNineSliceTargetSize(material, 72, 96);
assert.deepEqual(material.uniforms.uTargetSizePx.value.toArray(), [72, 96]);
assert.deepEqual(material.uniforms.uProtectedBorderPx.value.toArray(), [8, 8]);
assert.equal(material.userData.adaptiveNineSlice, true);
assert.equal(FRIDGE_ADAPTIVE_ATLAS.regions.screen.mode, 'fixed_decal');
assert.equal(FRIDGE_ADAPTIVE_ATLAS.regions.grille.mode, 'fixed_ends_repeat_x');

const textureAudit = new URL(
  '../docs/reference-lock/vaccine-fridge-v1/nano-banana-v5/nano-reference-material-primitives-v5.audit.json',
  import.meta.url,
);
const adaptiveManifest = new URL(
  '../docs/reference-lock/vaccine-fridge-v1/adaptive-texture-manifest.json', import.meta.url,
);
const audit = JSON.parse(readFileSync(textureAudit, 'utf8'));
assert.equal(audit.schemaVersion, 5);
assert.equal(audit.materials.length, 4, 'four Nano material fields passed');
assert.ok(audit.materials.every((entry) => entry.periodicEdges));
assert.ok(audit.materials.every((entry) => entry.largestAccentClusterPx <= 2));
assert.ok(audit.materials.every((entry) => entry.worldPeriodPx[0] === 16));
assert.match(audit.identityDecals.grille, /vaccine-fridge-grille\.png$/);
assert.match(audit.identityDecals.display, /vaccine-fridge-display\.png$/);
const adaptive = JSON.parse(readFileSync(adaptiveManifest, 'utf8'));
assert.equal(adaptive.schemaVersion, 3);
assert.equal(adaptive.exportedMaterialMode, 'embedded_nano_microtiles');
assert.equal(Object.keys(adaptive.generatedMaterialTiles).length, 4);
assert.match(adaptive.generatedPanelTile, /nano-steel-panel-microtile-v5\.png$/);
assert.equal(adaptive.logicalTexelPolicy.ordinaryMaterials.worldPeriodPx[0], 16);
assert.equal(adaptive.logicalTexelPolicy.largePanels.worldPeriodPx[0], 32);

console.log('PASS adaptive atlas: Nano microfields, authority decals, protected borders, and 1/2/3-door plans');
