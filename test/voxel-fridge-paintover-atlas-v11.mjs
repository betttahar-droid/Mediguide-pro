import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const root = new URL('../docs/reference-lock/vaccine-fridge-v1/paintover-v11/', import.meta.url);
const atlasAudit = JSON.parse(readFileSync(new URL('paintover-atlas-v11.audit.json', root), 'utf8'));
const runtimeAudit = JSON.parse(readFileSync(new URL('runtime/audit.json', root), 'utf8'));

assert.equal(atlasAudit.schemaVersion, 11);
assert.match(atlasAudit.model, /Nano Banana 2/);
assert.equal(atlasAudit.checks.allCellsCompiled, true);
assert.equal(atlasAudit.checks.allMarginsAtLeast3, true);
assert.equal(atlasAudit.decals.length, 16);
assert.ok(existsSync(new URL('paintover-iso-nano-v11.png', root)));
assert.ok(existsSync(new URL('paintover-front-nano-v11.png', root)));

assert.equal(runtimeAudit.status, 'PASS');
assert.equal(runtimeAudit.fixedDecalsMatch, true);
assert.equal(runtimeAudit.rigidPartsMatch, true);
assert.equal(runtimeAudit.adaptiveDecalsGrow, true);
const normal = runtimeAudit.records.find((record) => record.query === 'view=iso');
const resized = runtimeAudit.records.find((record) => record.query.includes('sx=1.45'));
assert.ok(normal && resized);
assert.deepEqual(normal.rigidPartSizes, [['macro_handle', [3.2, 2.55, 18]]]);
assert.deepEqual(resized.rigidPartSizes, normal.rigidPartSizes);
assert.deepEqual(resized.protectedDecalSizes, normal.protectedDecalSizes);
assert.ok(resized.decals > normal.decals);

for (const record of runtimeAudit.records) {
  assert.deepEqual(record.errors, []);
  assert.ok(record.paletteSize >= 25 && record.paletteSize <= 60);
  assert.ok(record.triangles >= 300 && record.triangles <= 5000);
}

console.log('PASS v11: raw render -> Nano paintover -> gated atlas -> adaptive runtime');
