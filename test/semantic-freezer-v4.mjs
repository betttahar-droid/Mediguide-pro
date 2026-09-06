import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const root = new URL('../', import.meta.url);
const lock = new URL('docs/reference-lock/semantic-freezer-v4/', root);
const manifest = JSON.parse(readFileSync(new URL('public/textures/semantic-freezer-v4.json', root), 'utf8'));
const runtime = JSON.parse(readFileSync(new URL('runtime/audit.json', lock), 'utf8'));
const adaptive = JSON.parse(readFileSync(new URL('adaptive-audit-v4.json', lock), 'utf8'));
const spatial = JSON.parse(readFileSync(new URL('spatial-audit-v4.json', lock), 'utf8'));
const jobs = JSON.parse(readFileSync(new URL('paintover-jobs-v4.json', lock), 'utf8'));
const main = readFileSync(new URL('tools/semantic-freezer/main.js', root), 'utf8');

assert.equal(manifest.schemaVersion, 4);
assert.equal(manifest.status, 'PASS');
assert.deepEqual(manifest.diagnosticPasses, ['raw', 'part-id', 'face-normal', 'depth', 'anchor-id']);
assert.equal(manifest.regions.length, 25);
assert.ok(manifest.regions.every(region => region.decision.status === 'approved'));
assert.ok(manifest.regions.every(region => region.source.evidenceClass === 'direct'));
assert.ok(manifest.regions.every(region => region.pixelSource.class === 'reconstructed'));
assert.ok(manifest.regions.filter(region => region.scaleClass === 'fixed').every(region => region.anchor));
assert.ok(!manifest.regions.some(region => region.source.evidenceClass === 'invented'));
assert.ok(Object.values(manifest.checks).every(Boolean));

assert.equal(Object.keys(jobs.views).length, 3);
for (const job of Object.values(jobs.views)) {
  assert.equal(job.inputsInOrder.length, 8);
  assert.deepEqual(job.inputsInOrder.map(item => item.role), [
    'raw-target', 'matching-authority', 'cross-view-authority-a', 'cross-view-authority-b',
    'part-id', 'face-normal', 'linear-depth', 'anchor-id',
  ]);
  for (const item of job.inputsInOrder) assert.ok(existsSync(new URL(item.path, root)));
}

for (const token of ['part-id', 'face-normal', 'linear-depth', 'anchor-id', 'diagnosticLegend']) {
  assert.match(main, new RegExp(token));
}
assert.match(main, /textureVersion === 'v4'/);
assert.equal(runtime.status, 'PASS');
assert.equal(adaptive.status, 'PASS');
assert.equal(spatial.status, 'PASS');
assert.ok(Object.values(adaptive.checks).every(Boolean));

for (const name of [
  'view-front-texture-v4.png', 'view-iso-texture-v4.png', 'view-side-texture-v4.png',
  'view-backIso-texture-v4.png', 'view-iso-texture-v4-sx-1_45.png',
  'view-side-texture-v4-sy-1_5.png', 'view-iso-texture-v4-sz-1_3.png',
]) assert.ok(existsSync(new URL(`runtime/${name}`, lock)));

console.log('PASS semantic freezer v4: evidence provenance, five diagnostics, rejection gates, and adaptive runtime');
