import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const root = new URL('../', import.meta.url);
const viewerPath = new URL('tools/semantic-freezer-viewer/index.html', root);
const viewer = readFileSync(viewerPath, 'utf8');
const renderer = readFileSync(new URL('tools/semantic-freezer/main.js', root), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('package.json', root), 'utf8'));

assert.ok(existsSync(viewerPath));
assert.ok(existsSync(new URL('tools/semantic-freezer-viewer/open-viewer.cmd', root)));
assert.match(viewer, /texture: 'v7'/);
assert.match(viewer, /condenserRails/);
assert.match(viewer, /ventBack/);
assert.match(viewer, /reference-front/);
assert.match(viewer, /reference-side/);
assert.match(viewer, /reference-back/);
assert.match(viewer, /id="evidencePass"/);
assert.match(viewer, /part-id/);
assert.match(viewer, /face-normal/);
assert.match(viewer, /linear-depth/);
assert.match(viewer, /anchor-id/);
assert.match(viewer, /id="scaleX"/);
assert.match(viewer, /id="scaleY"/);
assert.match(viewer, /id="scaleZ"/);
assert.match(viewer, /id="lockScale"/);
assert.match(viewer, /id="autoFit"/);
assert.match(viewer, /__SEMANTIC_FREEZER_SET_CAMERA__/);
assert.match(viewer, /Drag to orbit/);
assert.match(viewer, /COUNT-ADAPTIVE/);
assert.match(viewer, /fixed decals/);
assert.doesNotMatch(viewer, /transition:\s*all/);

assert.match(renderer, /view === 'orbit'/);
assert.match(renderer, /autoFitCamera/);
assert.match(renderer, /applyOrbitCamera/);
assert.match(renderer, /window\.__SEMANTIC_FREEZER_SET_CAMERA__/);
assert.match(packageJson.scripts['viewer:semantic-freezer'], /5186/);
assert.match(packageJson.scripts['viewer:semantic-freezer'], /semantic-freezer-viewer/);

console.log('PASS standalone semantic-freezer viewer: scale UI, orbit, diagnostics, launcher');
