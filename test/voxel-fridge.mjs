import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

function manifest(path) {
  const bytes = readFileSync(new URL(path, import.meta.url));
  const jsonLength = bytes.readUInt32LE(12);
  return { bytes, json: JSON.parse(bytes.subarray(20, 20 + jsonLength).toString().trim()) };
}

function meshExtent(json, nodeName) {
  const node = json.nodes.find((candidate) => candidate.name === nodeName);
  assert.ok(node && Number.isInteger(node.mesh), `${nodeName} has a mesh`);
  const accessorIndex = json.meshes[node.mesh].primitives[0].attributes.POSITION;
  const accessor = json.accessors[accessorIndex];
  return accessor.max.map((value, axis) => Number((value - accessor.min[axis]).toFixed(6)));
}

const one = manifest('../public/models/vaccine-fridge-voxel-1door.glb');
const two = manifest('../public/models/vaccine-fridge-voxel-2door.glb');
const three = manifest('../public/models/vaccine-fridge-voxel-3door.glb');
const authority = JSON.parse(readFileSync(new URL('../docs/reference-lock/vaccine-fridge-v1/geometry-authority.json', import.meta.url)));
const roots = [one, two, three].map(({ json }) => json.nodes.find((node) => node.extras?.gridDerived));
for (const [index, root] of roots.entries()) {
  const doors = index + 1;
  assert.ok(root, `${doors}-door GLB carries authority metadata`);
  assert.equal(root.extras.authoritySha256, authority.authoritySha256);
  assert.equal(root.extras.sourceTruthVersion, authority.schemaVersion);
  assert.equal(root.extras.variantGeneratorVersion, 2);
  assert.equal(root.extras.doorCount, doors);
  assert.equal(root.extras.bodyWidthPx, authority.modelGridPx.frontOverallWidth + (doors - 1) * 32);
  assert.equal(root.extras.bodyDepthPx, authority.modelGridPx.sideOverallDepth);
  assert.equal(root.extras.bodyHeightPx, authority.modelGridPx.totalHeight);
}
assert.equal(roots[1].extras.bodyWidthPx - roots[0].extras.bodyWidthPx, 32);
assert.equal(roots[2].extras.bodyWidthPx - roots[1].extras.bodyWidthPx, 32);
for (const [index, { json }] of [one, two, three].entries()) {
  const doors = index + 1;
  if (doors === 1) {
    assert.equal(json.nodes.filter((node) => node.name === 'front_glass').length, 1);
    assert.equal(json.nodes.filter((node) => node.name === 'handle_grip').length, 1);
    assert.equal(json.nodes.filter((node) => node.name === 'fixed_grille').length, 1);
  } else {
    assert.equal(json.nodes.filter((node) => /^front_glass_bay\d+$/.test(node.name)).length, doors);
    assert.equal(json.nodes.filter((node) => /^handle_grip_bay\d+$/.test(node.name)).length, doors);
    assert.equal(json.nodes.filter((node) => /^fixed_display$/.test(node.name)).length, 1);
    assert.equal(json.nodes.filter((node) => /^fixed_grille_bay\d+$/.test(node.name)).length, doors);
    assert.equal(json.nodes.filter((node) => /^shelf_bay\d+_(36|48|60|72)$/.test(node.name)).length, doors * 4);
  }
  assert.equal(json.nodes.filter((node) => /source_skin_front/.test(node.name)).length, 0);
  assert.equal(json.nodes.filter((node) => /shelf_surface/.test(node.name)).length, 0);
  assert.equal(json.nodes.filter((node) => /^side_reference_panel_mark_\d$/.test(node.name)).length, 6);
  assert.equal(json.nodes.filter((node) => /^roof_inset_/.test(node.name)).length, 4);
  assert.match(roots[index].extras.textureMode, /reference_measured_v5_microfields/);
  assert.equal(json.nodes.filter((node) => /^door_trim_/.test(node.name)).length, doors * 4);
  assert.equal(json.nodes.filter((node) => /^cream_fixed_corner_notch_/.test(node.name)).length, doors * 2);
  assert.equal(json.nodes.filter((node) => /^shelf_lip_(dark|light)_/.test(node.name)).length, doors * 8);
}
const fixedMarkExtent = meshExtent(one.json, 'side_reference_panel_mark_0');
assert.deepEqual(meshExtent(two.json, 'side_reference_panel_mark_0'), fixedMarkExtent);
assert.deepEqual(meshExtent(three.json, 'side_reference_panel_mark_0'), fixedMarkExtent);
const fixedDisplayExtent = meshExtent(one.json, 'fixed_display');
assert.deepEqual(meshExtent(two.json, 'fixed_display'), fixedDisplayExtent);
assert.deepEqual(meshExtent(three.json, 'fixed_display'), fixedDisplayExtent);
const runtime = readFileSync(new URL('../src/production/voxelFridge.js', import.meta.url), 'utf8');
assert.match(runtime, /NearestFilter/, 'pixel textures use nearest filtering');
assert.doesNotMatch(runtime, /vaccine-fridge-atlas-v7/, 'runtime no longer substitutes the rejected legacy atlas');
assert.match(runtime, /semantic_bay_repeat/, 'runtime exposes the authority texture mode');
console.log(`PASS authority fridge variants ${roots.map((root) => root.extras.bodyWidthPx).join('/')}px; geometry and texture provenance locked`);
