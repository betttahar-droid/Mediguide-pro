import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const audit = JSON.parse(readFileSync(new URL(
  '../docs/reference-lock/vaccine-fridge-v1/recipe-v10/audit.json',
  import.meta.url,
), 'utf8'));

assert.equal(audit.status, 'PASS');
assert.equal(audit.fixedDecalsMatch, true);
assert.equal(audit.rigidPartsMatch, true);
assert.equal(audit.adaptiveDecalsGrow, true);
assert.equal(audit.structuralCountsAdapt, true);

const normal = audit.records.find((record) => record.query === 'view=iso');
const resized = audit.records.find((record) => record.query.includes('sx=1.45'));
assert.ok(normal && resized);
assert.deepEqual(resized.protectedDecalSizes, normal.protectedDecalSizes);
assert.deepEqual(resized.rigidPartSizes, normal.rigidPartSizes);
assert.ok(resized.decals > normal.decals);

for (const record of audit.records) {
  assert.deepEqual(record.errors, []);
  assert.ok(record.paletteSize >= 25 && record.paletteSize <= 60);
  assert.ok(record.triangles >= 300 && record.triangles <= 5000);
}

console.log('PASS v10: rigid handle, protected fittings, adaptive fixed-texel decal fields');
