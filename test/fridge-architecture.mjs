import assert from 'node:assert/strict';
import { existsSync, readFileSync, statSync } from 'node:fs';
import { Vector3 } from 'three';
import { deformSocketPosition } from '../src/production/fridgeArchitecture.js';

const glb = new URL('../public/models/vaccine-fridge.glb', import.meta.url);
assert.ok(existsSync(glb), 'production fridge GLB exists');
assert.ok(statSync(glb).size > 10_000, 'production fridge GLB is non-empty');
const bytes = readFileSync(glb);
const jsonLength = bytes.readUInt32LE(12);
const manifest = JSON.parse(bytes.subarray(20, 20 + jsonLength).toString().trim());
const policies = new Set(manifest.nodes.flatMap((node) => node.extras?.texturePolicy || []));
assert.ok(policies.has('tile_center'), 'GLB contains scalable tile-center layers');
assert.ok(policies.has('protected_edge'), 'GLB contains protected edge layers');
assert.ok(policies.has('fixed_1to1'), 'GLB contains invariant decal/detail layers');

const sourceHalf = new Vector3(20, 14, 48).divideScalar(32);
const margin = new Vector3(4, 4, 8).divideScalar(32);
const rest = new Vector3(18, -17, 52).divideScalar(32);
const unchanged = deformSocketPosition(rest, sourceHalf, margin, new Vector3(1, 1, 1));
assert.ok(unchanged.distanceTo(rest) < 1e-9, '1x deformation preserves socket position');

const grown = deformSocketPosition(rest, sourceHalf, margin, new Vector3(2, 1, 1));
assert.ok(grown.x > rest.x, 'width growth moves the side socket outward');
assert.equal(grown.y, rest.y, 'width growth does not move socket depth');
assert.equal(grown.z, rest.z, 'width growth does not move socket height');

console.log(`PASS production fridge GLB ${statSync(glb).size} bytes; layered policies ${[...policies].join(', ')}; socket x ${rest.x.toFixed(3)} -> ${grown.x.toFixed(3)}`);
