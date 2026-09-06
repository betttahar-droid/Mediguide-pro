import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

function glbJson(path) {
  const bytes = readFileSync(new URL(path, import.meta.url));
  assert.equal(bytes.toString('ascii', 0, 4), 'glTF');
  const jsonLength = bytes.readUInt32LE(12);
  return JSON.parse(bytes.subarray(20, 20 + jsonLength).toString().trim());
}

const glb = glbJson('../public/models/vaccine-fridge-source-true.glb');
const authority = JSON.parse(readFileSync(new URL('../docs/reference-lock/vaccine-fridge-v1/geometry-authority.json', import.meta.url)));
const metrics = JSON.parse(readFileSync(new URL('../docs/reference-lock/vaccine-fridge-v1/orthographic-gate-metrics.json', import.meta.url)));
assert.equal(authority.schemaVersion, 3, 'canonical production spec includes explicit adaptive assembly rules');
assert.equal(authority.parts.length, 29, 'canonical spec owns every unique structural box');
assert.deepEqual(authority.shelfTemplate.elevationsPx, authority.frontFeaturesPx.shelvesZ);
assert.equal(authority.adaptive.doorBayWidthPx, 32);
const root = glb.nodes.find((node) => node.extras?.sourceTruthVersion === authority.schemaVersion);
assert.ok(root, 'GLB carries the source-truth root metadata');
assert.equal(root.extras.authoritySha256, authority.authoritySha256);
assert.equal(root.extras.pixelsPerUnit, 32);
assert.equal(root.extras.adaptivePolicy, authority.adaptive.policy);
assert.equal(root.extras.doorBayWidthPx, authority.adaptive.doorBayWidthPx);
for (const required of ['source_hull', 'nano_tile_side_panel', 'nano_tile_back_panel', 'nano_tile_top_surface', 'fixed_display', 'fixed_grille']) {
  assert.ok(glb.nodes.some((node) => node.name === required), `GLB contains ${required}`);
}
for (const required of ['front_glass', 'cavity_back', 'cavity_left', 'cavity_right', 'glass_reflection']) {
  assert.ok(glb.nodes.some((node) => node.name === required), `GLB contains real door component ${required}`);
}
assert.equal(glb.nodes.filter((node) => /^shelf_(36|48|60|72)$/.test(node.name)).length, 4);
assert.equal(glb.nodes.filter((node) => /^shelf_lip_(36|48|60|72)$/.test(node.name)).length, 4);
assert.ok(glb.samplers.every((sampler) => sampler.magFilter === 9728 && sampler.minFilter === 9728), 'all pixel textures disable mipmap filtering');
assert.ok(glb.materials.some((material) => material.name === 'nano_cream_microfield_front'));
assert.ok(glb.materials.some((material) => material.name === 'nano_steel_microfield_front'));
assert.ok(glb.materials.some((material) => material.name === 'nano_teal_microfield_front'));
assert.equal(glb.nodes.filter((node) => /^side_reference_panel_mark_\d$/.test(node.name)).length, 6);
assert.equal(glb.nodes.filter((node) => /^roof_inset_/.test(node.name)).length, 4);
assert.ok(glb.nodes.some((node) => node.name === 'side_panel_semantic_seam_dark'));
assert.ok(glb.nodes.some((node) => node.name === 'side_panel_semantic_seam_light'));
assert.equal(glb.nodes.filter((node) => /^door_trim_/.test(node.name)).length, 4);
assert.equal(glb.nodes.filter((node) => /^cream_fixed_corner_notch_/.test(node.name)).length, 2);
assert.equal(glb.nodes.filter((node) => /^shelf_lip_(dark|light)_/.test(node.name)).length, 8);
assert.ok(authority.textureOnly.includes('rust'));
assert.ok(authority.textureOnly.includes('paint chips'));
assert.ok(!glb.nodes.some((node) => node.name === 'source_skin_front'), 'front illustration is not doubled over real geometry');
assert.ok(!glb.nodes.some((node) => node.name === 'source_skin_back'), 'back illustration is replaced by a clean tiled material field');
assert.ok(!glb.nodes.some((node) => node.name === 'source_skin_side_panel'), 'side illustration is replaced by a clean tiled material field');
assert.ok(!glb.nodes.some((node) => node.name.startsWith('shelf_surface_')), 'shelf lips are not baked twice');
assert.ok(metrics.front.intersectionOverUnion >= 0.985);
assert.ok(metrics.side.intersectionOverUnion >= 0.96);
assert.ok(metrics.back.intersectionOverUnion >= 0.94);
console.log(`PASS source-true fridge: front=${metrics.front.intersectionOverUnion.toFixed(3)}, side=${metrics.side.intersectionOverUnion.toFixed(3)}, back=${metrics.back.intersectionOverUnion.toFixed(3)}`);
