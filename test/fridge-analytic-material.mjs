import assert from 'node:assert/strict';
import { Vector3 } from 'three';
import {
  analyticFaceMetrics,
  createAnalyticBoxMaterial,
} from '../src/shaders/index.js';

const min = new Vector3(-0.5, -0.4, 0);
const max = new Vector3(0.5, 0.4, 2);
const sideNormal = new Vector3(1, 0, 0);

const material = createAnalyticBoxMaterial({ boundsMin: min, boundsMax: max });
assert.equal(material.userData.uvLessAnalytic, true);
assert.equal(material.uniforms.uOutline.value, 1 / 32);

// A point one logical pixel from the front edge remains one world pixel from
// it when an unrelated axis grows.
const point = new Vector3(0.5, -0.4 + 1 / 32, 1);
const normal = analyticFaceMetrics(point, min, max, sideNormal, new Vector3(1, 1, 1));
const wider = analyticFaceMetrics(point, min, max, sideNormal, new Vector3(2, 1, 1));
assert.equal(normal.edgeDistance, 1 / 32);
assert.equal(wider.edgeDistance, normal.edgeDistance);

// Stretching the face axis increases center capacity while the threshold is
// still expressed in world units.
const deeper = analyticFaceMetrics(point, min, max, sideNormal, new Vector3(1, 2, 1));
assert.equal(deeper.edgeDistance, 2 / 32);
assert.ok(deeper.shorterSide > normal.shorterSide);

assert.doesNotMatch(material.vertexShader, /\buv\b/);
assert.doesNotMatch(material.fragmentShader, /texture2D|sampler2D/);
assert.match(material.fragmentShader, /uAxisScale/);
assert.match(material.fragmentShader, /canInset/);

console.log('PASS fridge analytic material: UV-less bands, small-face gate, and world-scale compensation');
