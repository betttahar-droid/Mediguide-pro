import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const root = new URL('../', import.meta.url);
const lock = new URL('docs/reference-lock/semantic-freezer-v2/', root);
const manifest = JSON.parse(readFileSync(new URL('public/textures/semantic-freezer-v2.json', root), 'utf8'));
const runtime = JSON.parse(readFileSync(new URL('runtime/audit.json', lock), 'utf8'));
const spatial = JSON.parse(readFileSync(new URL('spatial-audit-v2.json', lock), 'utf8'));
const main = readFileSync(new URL('tools/semantic-freezer/main.js', root), 'utf8');
const style = readFileSync(new URL('tools/voxel-fridge/style.js', root), 'utf8');
const compiler = readFileSync(new URL('tools/authoring/compile_semantic_freezer_v2.py', root), 'utf8');

assert.equal(manifest.schemaVersion, 2);
assert.match(manifest.authoring, /geometry-locked paintovers/);
assert.equal(manifest.microfields.length, 8);
assert.ok(manifest.fittings.length >= 17);
assert.ok(manifest.fittings.some(({ name }) => name === 'sideBottomWear'));
assert.ok(manifest.fittings.some(({ name }) => name === 'frontBaseWear'));
assert.ok(manifest.fittings.filter(({ name }) => name.startsWith('carton')).length >= 4);
assert.ok(existsSync(new URL('public/textures/semantic-freezer-microfields-v2.png', root)));
assert.ok(existsSync(new URL('public/textures/semantic-freezer-fittings-v2.png', root)));
assert.ok(existsSync(new URL('paintovers/iso-paintover-gpt.png', lock)));
assert.ok(existsSync(new URL('paintovers/side-paintover-gpt.png', lock)));
assert.ok(existsSync(new URL('paintovers/back-paintover-gpt.png', lock)));

assert.match(main, /textureVersion === 'v2'/);
assert.match(main, /semantic-freezer-microfields-v2\.png/);
assert.match(main, /fixedFitting\('frontBaseWear'/);
assert.match(main, /H - tx\(9\)/);
assert.match(style, /uMicroStrength/);
assert.match(style, /edgeAuthority/);
assert.match(style, /Hard bands are intentional/);
assert.match(compiler, /masked_wear/);
assert.match(compiler, /transparent fixed-size corner wear/);

assert.equal(runtime.status, 'PASS');
assert.equal(runtime.rigidPartsMatch, true);
assert.equal(runtime.fixedFittingsMatch, true);
const normal = runtime.records.find(({ scale }) => scale.every((value) => value === 1));
const resized = runtime.records.find(({ scale }) => scale.some((value) => value !== 1));
assert.ok(normal && resized);
assert.equal(normal.textureVersion, 'v2');
assert.equal(normal.shelfCount, 4);
assert.equal(resized.shelfCount, 5);
assert.deepEqual(normal.rigidPartSizes, resized.rigidPartSizes);
assert.deepEqual(normal.fixedFittingSizes, resized.fixedFittingSizes);
assert.ok(normal.fixedFittingSizes.some(([name]) => name === 'decal_sideBottomWear'));
for (const record of runtime.records) {
  assert.deepEqual(record.errors, []);
  assert.ok(record.paletteSize >= 32 && record.paletteSize <= 600);
  assert.ok(record.triangles >= 2000 && record.triangles <= 5000);
}

assert.equal(spatial.status, 'PASS');
for (const record of Object.values(spatial.records)) {
  assert.equal(record.status, 'PASS');
  assert.ok(record.hardEdgeRatio >= .30 && record.hardEdgeRatio <= 1.70);
}

console.log('PASS semantic freezer v2: aligned color fields, semantic wear, fixed decals, resize invariance');
