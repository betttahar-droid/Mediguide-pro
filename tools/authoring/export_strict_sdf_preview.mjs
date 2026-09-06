import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { Vector3 } from 'three';
import {
  generateStrictSdfFridge,
  STRICT_SDF_STYLE,
} from '../../src/production/strictSdfFridge.js';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '../..');
const fridge = generateStrictSdfFridge(38.75 / 32, 96 / 32, 36.75 / 32);
const parts = [];
fridge.traverse((node) => {
  if (!node.isMesh) return;
  node.geometry.computeBoundingBox();
  parts.push({
    name: node.name,
    role: node.userData.role,
    rule: node.userData.materialRule,
    kind: node.userData.partKind,
    size: node.geometry.boundingBox.getSize(new Vector3()).toArray(),
    position: node.position.toArray(),
    opacity: node.material.uniforms.uOpacity.value,
  });
});
const output = resolve(root, 'docs/reference-lock/vaccine-fridge-v1/strict-sdf-preview-manifest-v1.json');
writeFileSync(output, `${JSON.stringify({ style: STRICT_SDF_STYLE, parts }, null, 2)}\n`);
console.log(output);
