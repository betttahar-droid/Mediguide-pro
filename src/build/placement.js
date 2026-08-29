// Pointer → world placement. Raycast against the floor and against anything
// already placed, then let snapping.js correct the result.
import { Raycaster, Vector2, Vector3, Plane } from 'three';
import { findSocketSnap } from './snapping.js';

const FLOOR = new Plane(new Vector3(0, 1, 0), 0);

export class Placement {
  constructor(camera, domElement) {
    this.camera = camera;
    this.dom = domElement;
    this.raycaster = new Raycaster();
    this.pointer = new Vector2();
    this.hasPointer = false;
  }

  updatePointer(event) {
    const rect = this.dom.getBoundingClientRect();
    this.pointer.set(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1
    );
    this.hasPointer = true;
  }

  /** World point under the pointer: a placed module's surface, else the floor. */
  surfacePoint(placed) {
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const meshes = placed.flatMap((m) => m.meshes);
    const hit = this.raycaster.intersectObjects(meshes, false)[0];
    if (hit) return hit.point.clone();
    const out = new Vector3();
    return this.raycaster.ray.intersectPlane(FLOOR, out) ? out : null;
  }

  /** The module under the pointer, or null. */
  pick(placed) {
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hit = this.raycaster.intersectObjects(placed.flatMap((m) => m.meshes), false)[0];
    return hit?.object.userData.module ?? null;
  }

  /**
   * Position `ghost` under the pointer and snap it.
   * @returns {{snapped:boolean, tag:string|null}}
   */
  place(ghost, placed) {
    const point = this.surfacePoint(placed);
    if (!point) return { snapped: false, tag: null };
    ghost.group.position.copy(point);

    const snap = findSocketSnap(ghost, placed);
    if (snap) {
      ghost.group.position.copy(snap.position);
      return { snapped: true, tag: snap.tag };
    }
    // Wall-mounted modules declare a hover height, which is what lets a sign or
    // a wall shelf be placed against a wall without a wall-socket system.
    ghost.group.position.y = Math.max(0, ghost.group.position.y) + (ghost.def.hover ?? 0);
    return { snapped: false, tag: null };
  }
}
