import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const root = new URL('../', import.meta.url);
const manifest = JSON.parse(readFileSync(new URL('public/textures/semantic-freezer-v6.json', root), 'utf8'));
const main = readFileSync(new URL('tools/semantic-freezer/main.js', root), 'utf8');
const style = readFileSync(new URL('tools/voxel-fridge/style.js', root), 'utf8');

assert.equal(manifest.schemaVersion, 6);
assert.equal(manifest.status, 'PASS');
assert.deepEqual(manifest.fittingAtlasSizePx, [256, 192]);
assert.ok(existsSync(new URL(`public/textures/${manifest.atlases.fittings}`, root)));
assert.ok(Object.values(manifest.checks).every(Boolean));
assert.match(main, /textureVersion === 'v6'/);
assert.match(main, /rear_condenser_support/);
assert.match(main, /rear_fan_housing/);
assert.match(main, /side_vent_support/);
assert.doesNotMatch(style, /cell\.x = 63\.0 - cell\.x/);
assert.doesNotMatch(style, /cell\.y = 63\.0 - cell\.y/);
console.log('PASS semantic freezer v6: support-owned textures, face basis, clean layers');
