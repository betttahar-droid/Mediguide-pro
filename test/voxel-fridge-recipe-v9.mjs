import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const auditUrl = new URL(
  '../docs/reference-lock/vaccine-fridge-v1/recipe-v9/audit.json',
  import.meta.url,
);
const audit = JSON.parse(readFileSync(auditUrl, 'utf8'));

assert.equal(audit.status, 'PASS');
assert.equal(audit.fixedDecalsMatch, true);
assert.equal(audit.structuralCountsAdapt, true);
assert.equal(audit.records.length, 3);

for (const record of audit.records) {
  assert.equal(record.ready, true);
  assert.deepEqual(record.errors, []);
  assert.ok(record.paletteSize >= 25 && record.paletteSize <= 60);
  assert.ok(record.triangles >= 300 && record.triangles <= 5000);
  assert.equal(record.decals, 19);
}

const normal = audit.records.find((record) => record.query === 'view=iso');
const resized = audit.records.find((record) => record.query.includes('sx=1.45'));
assert.ok(normal);
assert.ok(resized);
assert.deepEqual(resized.decalTexelSizes, normal.decalTexelSizes);
assert.ok(resized.parts > normal.parts);

console.log('PASS recipe v9: fixed decals, adaptive structure, palette and triangle budgets');
