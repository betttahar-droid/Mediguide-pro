import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const lock = new URL('../docs/reference-lock/vaccine-fridge-v1/handbook-v12/', import.meta.url);
const surfaceAudit = JSON.parse(readFileSync(new URL('surface-masks-v12.audit.json', lock), 'utf8'));
const runtimeAudit = JSON.parse(readFileSync(new URL('runtime/audit.json', lock), 'utf8'));
const mainSource = readFileSync(new URL('../tools/voxel-fridge/main.js', import.meta.url), 'utf8');
const styleSource = readFileSync(new URL('../tools/voxel-fridge/style.js', import.meta.url), 'utf8');
const authoringSource = readFileSync(new URL('../tools/authoring/generate_fridge_surface_masks_v12.py', import.meta.url), 'utf8');
const referenceMeasurements = readFileSync(new URL('style-research-v7/reference-measurements.json', new URL('../docs/reference-lock/vaccine-fridge-v1/', import.meta.url)), 'utf8');

assert.equal(surfaceAudit.schemaVersion, 12);
assert.deepEqual(surfaceAudit.toneLevels, [0, 128, 255]);
assert.deepEqual(surfaceAudit.atlasSizePx, [100, 20]);
assert.equal(surfaceAudit.tiles.length, 5);
assert.equal(surfaceAudit.checks.islandCount, true);
assert.equal(surfaceAudit.checks.sourceRatiosConsistent, true);
assert.deepEqual(surfaceAudit.checks.normalizedLogicalSize, [20, 20]);
assert.equal(surfaceAudit.checks.allThreeTone, true);
assert.deepEqual(surfaceAudit.tiles.map((tile) => tile.middleMode), [
  'stretch', 'stretch', 'repeat', 'stretch', 'stretch',
]);
assert.ok(surfaceAudit.tiles.every((tile) => tile.marginPx >= 2));
assert.ok(existsSync(new URL('surface-masks-v12-source-guided.png', lock)));
assert.ok(existsSync(new URL('surface-masks-v12-compiled-preview.png', lock)));

// Nano Banana calls must stay behind the one audited project caller.
assert.match(authoringSource, /from concept_sheet import generate_image, load_key/);
assert.match(authoringSource, /surface-masks-v12-source-guided\.png/);

// The atlas is structure-only; face coordinates are reconstructed analytically.
assert.match(styleSource, /float nineAxis\(/);
assert.match(styleSource, /vec2\(vLocal\.x \+ uHalf\.x/);
assert.match(styleSource, /min\(span\.x, span\.y\) > 2\.0 \* uSurfaceMargin \+ 1\.0/);
assert.doesNotMatch(styleSource, /glassWideReflection|glassGlint|family:\s*['"]reflection['"]/);
assert.doesNotMatch(mainSource, /imageDecal|glassWideReflection|glassGlint/);

// Only semantic fittings survive as atlas decals, on named front planes.
assert.match(mainSource, /put\('controlBezel', 'front'/);
assert.match(mainSource, /put\('cautionPlate', 'front'/);
assert.match(mainSource, /const CONTROL_Y = H - tx\(6\)/);
assert.match(mainSource, /const controlsFit =/);
assert.match(mainSource, /const cautionFits =/);

// The handle is an anchored five-part assembly, never a scaled monolith.
assert.equal((mainSource.match(/name: 'handle_mount'/g) ?? []).length, 1); // emitted twice by its loop
for (const name of ['handle_grip', 'handle_catch', 'handle_return']) {
  assert.match(mainSource, new RegExp(`name: '${name}'`));
}
assert.doesNotMatch(mainSource, /macro_handle/);

// The two extra control colors are measured reference colors, not invented filler.
for (const color of ['#d7995f', '#9d6d59']) {
  assert.ok(referenceMeasurements.includes(color));
  assert.ok(styleSource.includes(color));
}

assert.equal(runtimeAudit.status, 'PASS');
assert.equal(runtimeAudit.fixedDecalsMatch, true);
assert.equal(runtimeAudit.rigidPartsMatch, true);
assert.equal(runtimeAudit.structuralCountsAdapt, true);
const normal = runtimeAudit.records.find((record) => record.query === 'view=iso');
const resized = runtimeAudit.records.find((record) => record.query.includes('sx=1.65'));
assert.ok(normal && resized);
assert.deepEqual(resized.protectedDecalSizes, normal.protectedDecalSizes);
assert.deepEqual(resized.rigidPartSizes, normal.rigidPartSizes);
assert.ok(resized.parts > normal.parts);
assert.equal(normal.decals, 2);
for (const record of runtimeAudit.records) {
  assert.deepEqual(record.errors, []);
  assert.ok(record.paletteSize >= 25 && record.paletteSize <= 60);
  assert.ok(record.triangles >= 2000 && record.triangles <= 5000);
}

console.log('PASS v12: handbook masks, anchored fittings, fixed handle, adaptive structure');
