import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const root = new URL('../', import.meta.url);
const manifest = JSON.parse(readFileSync(new URL('public/textures/semantic-freezer-v7.json', root), 'utf8'));
const main = readFileSync(new URL('tools/semantic-freezer/main.js', root), 'utf8');

assert.equal(manifest.schemaVersion, 7);
assert.equal(manifest.status, 'PASS');
assert.ok(Object.values(manifest.checks).every(Boolean));
assert.ok(existsSync(new URL(`public/textures/${manifest.atlases.fittings}`, root)));
assert.ok(existsSync(new URL(`public/textures/${manifest.atlases.microfields}`, root)));
assert.deepEqual(Object.keys(manifest.anchorContracts).sort(), [
  'fanGrille', 'rearDoNot', 'rearWarning', 'sideRating', 'sideVentPanel',
]);
assert.equal(manifest.anchorContracts.sideVentPanel.horizontal, 'back-fixed');
assert.equal(manifest.adaptiveTextureContracts.condenserField.scaleClass, 'count-adaptive');
assert.match(main, /textureVersion === 'v7'/);
assert.match(main, /adaptiveCondenserField/);
assert.match(main, /B - tx\(ventAnchor\.backOffsetTexels\)/);
assert.match(main, /pitchTexels/);
assert.match(main, /edgeDistancesTexels/);
console.log('PASS semantic freezer v7: edge anchors, adaptive fixed-pitch fields, audit evidence');
