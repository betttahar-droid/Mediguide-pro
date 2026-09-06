import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const root = new URL('../', import.meta.url);
const lock = new URL('docs/reference-lock/semantic-freezer-v5/', root);
const correspondence = JSON.parse(readFileSync(new URL('correspondence-v5.json', lock), 'utf8'));
const manifest = JSON.parse(readFileSync(new URL('public/textures/semantic-freezer-v5.json', root), 'utf8'));
const jobs = JSON.parse(readFileSync(new URL('nano-feature-jobs-v5.json', lock), 'utf8'));
const main = readFileSync(new URL('tools/semantic-freezer/main.js', root), 'utf8');

assert.equal(manifest.schemaVersion, 5);
assert.equal(manifest.status, 'PASS');
assert.equal(correspondence.policy.placementOwner, 'deterministic correspondence compiler');
assert.equal(correspondence.policy.nanoRole, 'masked pixel reconstruction only');
assert.equal(correspondence.correspondences.length, 17);
assert.deepEqual(Object.keys(correspondence.registrations).sort(), ['back', 'front', 'roof', 'side']);
assert.ok(correspondence.correspondences.every(item => item.evidence === 'direct'));
assert.ok(correspondence.correspondences.every(item => item.tolerance.positionTexels <= 1));
assert.equal(jobs.jobs.length, 6);
for (const job of jobs.jobs) {
  assert.deepEqual(job.nanoCanvasSizePx, [1024, 1024]);
  assert.equal(job.inputsInOrder.length, 4);
  for (const item of job.inputsInOrder) assert.ok(existsSync(new URL(item, root)));
}
assert.ok(Object.values(manifest.checks).every(Boolean));
assert.match(main, /textureVersion === 'v5'/);
assert.match(main, /runtimePlacements\.sidePanelSeeds/);
assert.match(main, /correspondenceId/);
console.log('PASS semantic freezer v5: registered faces, measured feature correspondence, masked Nano jobs');
