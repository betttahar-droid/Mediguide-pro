// Phase 6 — one InstancedMesh per module type, with aTargetScale and aMargins
// as instanced attributes so props of different sizes share a single draw call.
//
// This is why §5.3 keeps margins out of COLOR_0: a per-vertex margin is a
// per-mesh constant baked into the geometry, and baking it would have made this
// path impossible. As uniforms in Phases 2–5 and instanced attributes here, the
// same shader serves both.
import { InstancedMesh, InstancedBufferAttribute, Matrix4, Vector3, Euler, Quaternion } from 'three';
import { createAdaptiveMaterial } from '../shaders/index.js';
import { REGISTRY } from './registry.js';
import { unitGeometry, materialOptionsFor } from './ModuleInstance.js';
import { clampParams, layout } from './resize.js';

/**
 * @param {string} typeId
 * @param {{position:number[], rotY?:number, params?:object}[]} entries
 * @returns {THREE.InstancedMesh} one draw call for the whole list
 */
export function createInstancedBatch(typeId, entries) {
  const def = REGISTRY[typeId];
  if (!def) throw new Error(`unknown module type "${typeId}"`);

  // clone: the instanced attributes must not land on the shared unit geometry
  const geometry = unitGeometry(def).clone();
  const material = createAdaptiveMaterial(materialOptionsFor(def, { instancedParams: true }));

  // one instance per laid-out cell, so repeat axes batch too
  const cells = [];
  for (const entry of entries) {
    const params = clampParams(def, entry.params);
    const origin = new Vector3(...entry.position);
    const quat = new Quaternion().setFromEuler(new Euler(0, entry.rotY ?? 0, 0));
    for (const cell of layout(def, params)) {
      const offset = new Vector3(...cell.position).applyQuaternion(quat);
      cells.push({
        matrix: new Matrix4().compose(origin.clone().add(offset), quat, ONE),
        targetScale: cell.targetScale,
      });
    }
  }

  const mesh = new InstancedMesh(geometry, material, cells.length);
  const scales = new Float32Array(cells.length * 3);
  const margins = new Float32Array(cells.length * 3);

  cells.forEach((cell, i) => {
    mesh.setMatrixAt(i, cell.matrix);
    scales.set(cell.targetScale, i * 3);
    margins.set(def.margins, i * 3);
  });

  geometry.setAttribute('aTargetScale', new InstancedBufferAttribute(scales, 3));
  geometry.setAttribute('aMargins', new InstancedBufferAttribute(margins, 3));
  mesh.instanceMatrix.needsUpdate = true;
  mesh.frustumCulled = false;
  mesh.userData.instancedBatch = true;
  return mesh;
}

const ONE = new Vector3(1, 1, 1);

export function disposeBatch(mesh) {
  mesh.parent?.remove(mesh);
  mesh.geometry.dispose();
  mesh.material.dispose();
  mesh.dispose();
}
