import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const auditUrl = new URL(
  '../docs/reference-lock/vaccine-fridge-v1/style-research-v7/style-fit-v7.audit.json',
  import.meta.url,
);
const audit = JSON.parse(readFileSync(auditUrl, 'utf8'));

assert.equal(audit.schemaVersion, 7);
assert.equal(audit.status, 'PASS');
assert.ok(Object.values(audit.checks).every(Boolean));
assert.ok(audit.metrics.changedObjectPixelShare >= 0.015);
assert.ok(audit.metrics.changedObjectPixelShare <= 0.10);
assert.ok(audit.metrics.meanMotifQuietShare >= 0.75);
assert.deepEqual(audit.metrics.samplers, [{ magFilter: 9728, minFilter: 9728 }]);

console.log('PASS fridge v7: researched geometry, Nano motifs, fixed margins, nearest sampler, and visual delta');
