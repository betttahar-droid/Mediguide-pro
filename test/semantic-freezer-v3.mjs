import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const root = new URL('../', import.meta.url);
const lock = new URL('docs/reference-lock/semantic-freezer-v3/', root);
const manifest = JSON.parse(readFileSync(new URL('public/textures/semantic-freezer-v3.json', root), 'utf8'));
const runtime = JSON.parse(readFileSync(new URL('runtime/audit.json', lock), 'utf8'));
const adaptive = JSON.parse(readFileSync(new URL('adaptive-audit-v3.json', lock), 'utf8'));
const spatial = JSON.parse(readFileSync(new URL('spatial-audit-v3.json', lock), 'utf8'));
const main = readFileSync(new URL('tools/semantic-freezer/main.js', root), 'utf8');
const style = readFileSync(new URL('tools/voxel-fridge/style.js', root), 'utf8');

assert.equal(manifest.schemaVersion, 3);
assert.deepEqual(Object.keys(manifest.scaleClasses).sort(), [
  'count-adaptive', 'expand', 'fixed', 'repeat',
]);
assert.ok(manifest.scaleClasses.fixed.includes('handle_assembly'));
assert.ok(manifest.scaleClasses.fixed.includes('medicalIdentity'));
assert.ok(manifest.scaleClasses.repeat.includes('sideMetal'));
assert.ok(manifest.scaleClasses['count-adaptive'].includes('side_panel_row'));
assert.ok(manifest.scaleClasses['count-adaptive'].includes('rear_coil_run'));
assert.equal(manifest.evidence.inventedHiddenStructure, 'excluded');
assert.ok(Object.values(manifest.checks).every(Boolean));

assert.match(style, /vAxisScale/);
assert.match(style, /physicalP/);
assert.match(style, /physicalSpan/);
assert.match(main, /textureVersion === 'v3'/);
assert.match(main, /adaptiveStrip/);
assert.match(main, /fixedThicknessPx/);
assert.match(main, /REAR_COIL_HI/);

assert.equal(runtime.status, 'PASS');
assert.equal(adaptive.status, 'PASS');
assert.equal(spatial.status, 'PASS');
assert.ok(Object.values(adaptive.checks).every(Boolean));
for (const record of runtime.records) {
  assert.equal(record.textureVersion, 'v3');
  assert.deepEqual(record.errors, []);
  assert.ok(record.paletteSize >= 32 && record.paletteSize <= 600);
  assert.ok(record.triangles >= 2000 && record.triangles <= 5000);
}

for (const name of [
  'view-iso-texture-v3.png',
  'view-iso-texture-v3-sx-1_45.png',
  'view-side-texture-v3-sy-1_5.png',
  'view-iso-texture-v3-sz-1_3.png',
]) assert.ok(existsSync(new URL(`runtime/${name}`, lock)));

console.log('PASS semantic freezer v3: four scale classes and independent-axis adaptation');
