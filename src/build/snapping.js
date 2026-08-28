// §8.3 — gridless snapping, evaluated in priority order.
//
//   1. socket-to-socket : matching tag, opposing normals, within `radius`
//   2. surface          : the raycast hit point itself (handled in placement.js)
//   3. edge alignment   : not built — see README "Not built"
import { Vector3 } from 'three';

const OPPOSING = -0.7; // cos of the max angle between two mating socket normals

/**
 * @param {ModuleInstance} ghost the module being placed, already positioned
 * @param {ModuleInstance[]} placed
 * @param {number} radius metres
 * @returns {{position:THREE.Vector3, tag:string, target:ModuleInstance}|null}
 */
export function findSocketSnap(ghost, placed, radius = 0.5) {
  const ghostSockets = ghost.worldSockets();
  if (ghostSockets.length === 0) return null;

  let best = null;
  const delta = new Vector3();

  for (const other of placed) {
    if (other === ghost) continue;
    for (const target of other.worldSockets()) {
      for (const g of ghostSockets) {
        if (g.tag !== target.tag) continue;
        if (g.normal.dot(target.normal) > OPPOSING) continue;
        const d = delta.subVectors(target.pos, g.pos).length();
        if (d > radius) continue;
        if (!best || d < best.distance) {
          best = {
            distance: d,
            tag: g.tag,
            target: other,
            position: ghost.group.position.clone().add(delta.subVectors(target.pos, g.pos)),
          };
        }
      }
    }
  }
  return best;
}
