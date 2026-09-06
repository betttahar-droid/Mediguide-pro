import assert from 'node:assert/strict';
import { Vector3 } from 'three';
import {
  generateStrictSdfFridge,
  STRICT_STYLE_UNIT,
} from '../src/production/strictSdfFridge.js';

const W = 38.75 / 32;
const H = 96 / 32;
const D = 36.75 / 32;
const standard = generateStrictSdfFridge(W, H, D);
const wide = generateStrictSdfFridge(W * 2, H, D);

function meshes(root) {
  const result = [];
  root.traverse((node) => { if (node.isMesh) result.push(node); });
  return result;
}

for (const mesh of meshes(standard)) {
  assert.equal(mesh.geometry.getAttribute('uv'), undefined, `${mesh.name} has no UV attribute`);
  assert.equal(mesh.material.userData.uvLessAnalytic, true, `${mesh.name} uses analytic material`);
  assert.equal(mesh.material.map, undefined, `${mesh.name} has no texture map`);
  assert.doesNotMatch(mesh.material.fragmentShader, /texture2D|sampler2D/);
  assert.equal(mesh.userData.strictSdf, true);
}

assert.equal(standard.userData.texturePolicy, 'none');
assert.equal(standard.userData.lightingPolicy, 'unlit_normal_tints');
assert.ok(wide.userData.louvreCount > standard.userData.louvreCount,
  'wider grille creates additional real louvre boxes');

const standardHandle = standard.getObjectByName('strict_handle_0');
const wideHandle = wide.getObjectByName('strict_handle_0');
standardHandle.geometry.computeBoundingBox();
wideHandle.geometry.computeBoundingBox();
const standardHandleSize = standardHandle.geometry.boundingBox.getSize(new Vector3());
const wideHandleSize = wideHandle.geometry.boundingBox.getSize(new Vector3());
assert.ok(standardHandleSize.distanceTo(wideHandleSize) < 1e-9,
  'anchored handle keeps fixed world dimensions when W grows');

const standardFrame = standard.getObjectByName('strict_frame_left');
const wideFrame = wide.getObjectByName('strict_frame_left');
const standardFrameSize = standardFrame.geometry.boundingBox.getSize(new Vector3());
const wideFrameSize = wideFrame.geometry.boundingBox.getSize(new Vector3());
assert.ok(wideFrameSize.x > standardFrameSize.x,
  'structural frame dimension remains proportional to W');

assert.equal(standard.getObjectByName('strict_display_pixel_0').userData.dimensionPolicy,
  'fixed_style_units');
assert.equal(standardHandleSize.x, STRICT_STYLE_UNIT * 2.5);
assert.equal(meshes(standard).filter((mesh) => mesh.name.startsWith('strict_frame_rivet_')).length, 4);
assert.ok(meshes(standard).filter((mesh) => mesh.name.startsWith('strict_grille_louvre_')).length > 1);

console.log(`PASS strict SDF fridge: ${meshes(standard).length} UV-less boxes; grille ${standard.userData.louvreCount}->${wide.userData.louvreCount} louvres`);
