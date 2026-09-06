import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const root = new URL('../', import.meta.url);
const lock = new URL('docs/reference-lock/semantic-freezer-v1/', root);
const manifest = JSON.parse(readFileSync(new URL('public/textures/semantic-freezer-v1.json', root), 'utf8'));
const runtime = JSON.parse(readFileSync(new URL('runtime/audit.json', lock), 'utf8'));
const main = readFileSync(new URL('tools/semantic-freezer/main.js', root), 'utf8');
const style = readFileSync(new URL('tools/voxel-fridge/style.js', root), 'utf8');
const generator = readFileSync(new URL('tools/authoring/generate_semantic_freezer_v1.py', root), 'utf8');

assert.equal(manifest.schemaVersion, 1);
assert.match(manifest.generator, /Nano Banana 2/);
assert.deepEqual(manifest.profiles.map(({ name }) => name), [
  'roofTop', 'crownFront', 'cabinetSide', 'doorFrame',
  'shelfTop', 'shelfLip', 'baseFront', 'ventField',
]);
assert.deepEqual(manifest.fittings.map(({ name }) => name), [
  'medicalBadge', 'digitalStatus', 'statusStrip', 'sideRating',
  'rearWarning', 'cartonLabel', 'vialLabel', 'fanGrille',
]);
assert.equal(manifest.rejectedSourceRegions.length, 3);
assert.equal(manifest.checks.eightFaceRoles, true);
assert.equal(manifest.checks.eightFittings, true);
assert.equal(manifest.checks.allFacesIndexed, true);
assert.equal(manifest.checks.generationLayoutAccepted, false);
assert.equal(manifest.checks.reviewedSelectionCompiled, true);
assert.match(generator, /from concept_sheet import generate_image, load_key/);
assert.ok(existsSync(new URL('semantic-freezer-faces-source.png', lock)));
assert.ok(existsSync(new URL('semantic-freezer-fittings-source.png', lock)));
assert.ok(existsSync(new URL('public/textures/semantic-freezer-faces-v1.png', root)));
assert.ok(existsSync(new URL('public/textures/semantic-freezer-fittings-v1.png', root)));

assert.match(main, /semantic-freezer-faces-v1\.png/);
assert.match(main, /semantic-freezer-fittings-v1\.png/);
assert.match(main, /fixedFitting\('medicalBadge'/);
assert.match(main, /surfaceFaces: \{ top: 'shelfTop', front: 'shelfLip' \}/);
assert.match(style, /vNormal = normalize\(mat3\(modelMatrix\) \* normal\)/);

assert.equal(runtime.status, 'PASS');
assert.equal(runtime.rigidPartsMatch, true);
assert.equal(runtime.fixedFittingsMatch, true);
const normal = runtime.records.find(({ query }) => query === 'view=iso');
const resized = runtime.records.find(({ query }) => query.includes('sx=1.45'));
assert.ok(normal && resized);
assert.equal(normal.shelfCount, 4);
assert.equal(resized.shelfCount, 5);
assert.deepEqual(normal.rigidPartSizes, resized.rigidPartSizes);
assert.deepEqual(normal.fixedFittingSizes, resized.fixedFittingSizes);
for (const record of runtime.records) {
  assert.deepEqual(record.errors, []);
  assert.ok(record.paletteSize >= 25 && record.paletteSize <= 60);
  assert.ok(record.triangles >= 2000 && record.triangles <= 5000);
}

console.log('PASS semantic freezer v1: measured geometry, Nano masks, fixed fittings, adaptive structure');
