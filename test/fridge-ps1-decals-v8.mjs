import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const url = new URL(
  '../docs/reference-lock/vaccine-fridge-v1/style-research-v7/ps1-decals-v8.audit.json',
  import.meta.url,
);
const audit = JSON.parse(readFileSync(url, 'utf8'));

assert.equal(audit.schemaVersion, 8);
assert.equal(audit.status, 'PASS');
assert.ok(Object.values(audit.checks).every(Boolean));
assert.ok(audit.metrics.hullVertexReduction >= 0.25);
assert.equal(audit.metrics.replacementDecals, 6);

console.log('PASS PS1 v8: coarse macro hull and fixed decals for sub-4px details');
