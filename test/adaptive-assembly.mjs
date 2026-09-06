import assert from 'node:assert/strict';
import {
  AxisPolicy,
  TexturePolicy,
  remapNineSliceCoordinate,
  repeatedModuleCenters,
  resolveFixedSocket,
  resolvePartBounds,
  validateAdaptiveDefinition,
} from '../src/production/adaptiveAssembly.js';

const source = { x: [-20, 20], y: [-16, 16], z: [0, 96] };
const wide = { x: [-36, 36], y: [-16, 16], z: [0, 96] };

assert.equal(remapNineSliceCoordinate(-18, source.x, wide.x, 4, 4), -34);
assert.equal(remapNineSliceCoordinate(18, source.x, wide.x, 4, 4), 34);
assert.equal(remapNineSliceCoordinate(0, source.x, wide.x, 4, 4), 0);

const display = resolveFixedSocket({
  id: 'display',
  positionPx: { x: 4, y: -16, z: 90 },
  sizePx: { x: 13, y: 0.25, z: 4 },
  anchor: {
    x: AxisPolicy.FIXED_CENTER,
    y: AxisPolicy.FIXED_MIN,
    z: AxisPolicy.FIXED_MAX,
  },
}, source, wide);
assert.deepEqual(display.positionPx, { x: 4, y: -16, z: 90 });
assert.deepEqual(display.sizePx, { x: 13, y: 0.25, z: 4 });
assert.deepEqual(display.scale, { x: 1, y: 1, z: 1 });

const rightCorner = resolveFixedSocket({
  id: 'right-corner',
  positionPx: { x: 19, y: -15, z: 3 },
  sizePx: { x: 2, y: 2, z: 2 },
  anchor: {
    x: AxisPolicy.FIXED_MAX,
    y: AxisPolicy.FIXED_MIN,
    z: AxisPolicy.FIXED_MIN,
  },
}, source, wide);
assert.equal(rightCorner.positionPx.x, 35);
assert.equal(rightCorner.sizePx.x, 2);

const rail = resolvePartBounds({
  id: 'top-rail',
  boundsPx: { x: [-20, 20], y: [-16, -14], z: [88, 92] },
  axes: {
    x: { policy: AxisPolicy.NINE_SLICE_SPAN, protectedNearPx: 4, protectedFarPx: 4 },
    y: { policy: AxisPolicy.FIXED_MIN },
    z: { policy: AxisPolicy.FIXED_MAX },
  },
}, source, wide);
assert.deepEqual(rail.boundsPx.x, [-36, 36]);
assert.deepEqual(rail.boundsPx.z, [88, 92]);

assert.deepEqual(repeatedModuleCenters(3, 32), [-32, 0, 32]);

const valid = validateAdaptiveDefinition({ parts: [{
  id: 'display',
  texturePolicy: TexturePolicy.FIXED_DECAL,
  axes: {
    x: { policy: AxisPolicy.FIXED_CENTER },
    y: { policy: AxisPolicy.FIXED_MIN },
    z: { policy: AxisPolicy.FIXED_MAX },
  },
}] });
assert.equal(valid.valid, true);

const invalid = validateAdaptiveDefinition({ parts: [{
  id: 'bad-logo',
  texturePolicy: TexturePolicy.FIXED_DECAL,
  axes: {
    x: { policy: AxisPolicy.PROPORTIONAL },
    y: { policy: AxisPolicy.FIXED_MIN },
    z: { policy: AxisPolicy.FIXED_CENTER },
  },
}] });
assert.equal(invalid.valid, false);
assert.match(invalid.errors.join('\n'), /must use a fixed anchor on x/);

console.log('PASS adaptive assembly: protected geometry, fixed sockets, repeated bays, and decal guards');

