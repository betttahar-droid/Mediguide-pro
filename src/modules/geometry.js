// Parametric beveled boxes (§11.1 step 4: rebuild from numbers, not from a mesh).
//
// Fat corner radii are most of the "chunky hand-painted" read, and a chamfered
// box gives the vertex-mask bake (§4.3) real convex edges to find.
import { BufferGeometry, BufferAttribute, Vector3 } from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

/**
 * Chamfered box centred on the origin, flat-shaded, non-indexed.
 * @param {number} w full width  (x)
 * @param {number} h full height (y)
 * @param {number} d full depth  (z)
 * @param {number} bevel chamfer size, clamped to a third of the smallest extent
 */
export function bevelBox(w, h, d, bevel = 0.03) {
  const e = [w / 2, h / 2, d / 2];
  const b = Math.min(bevel, Math.min(w, h, d) / 3);
  const inner = e.map((v) => v - b);
  const verts = [];

  const at = (i, vi, j, vj, k, vk) => {
    const p = [0, 0, 0];
    p[i] = vi; p[j] = vj; p[k] = vk;
    return p;
  };

  const tri = (a, bb, c) => {
    const n = normalOf(a, bb, c);
    const cx = (a[0] + bb[0] + c[0]) / 3;
    const cy = (a[1] + bb[1] + c[1]) / 3;
    const cz = (a[2] + bb[2] + c[2]) / 3;
    if (n[0] * cx + n[1] * cy + n[2] * cz < 0) verts.push(a, c, bb);
    else verts.push(a, bb, c);
  };
  const quad = (a, bb, c, d2) => { tri(a, bb, c); tri(a, c, d2); };

  // 6 inset faces
  for (let i = 0; i < 3; i++) {
    const j = (i + 1) % 3, k = (i + 2) % 3;
    for (const s of [1, -1]) {
      quad(
        at(i, s * e[i], j, -inner[j], k, -inner[k]),
        at(i, s * e[i], j, inner[j], k, -inner[k]),
        at(i, s * e[i], j, inner[j], k, inner[k]),
        at(i, s * e[i], j, -inner[j], k, inner[k])
      );
    }
  }

  // 12 chamfer quads
  for (let i = 0; i < 3; i++) {
    const j = (i + 1) % 3, k = (i + 2) % 3;
    for (const si of [1, -1]) {
      for (const sj of [1, -1]) {
        quad(
          at(i, si * e[i], j, sj * inner[j], k, -inner[k]),
          at(i, si * e[i], j, sj * inner[j], k, inner[k]),
          at(i, si * inner[i], j, sj * e[j], k, inner[k]),
          at(i, si * inner[i], j, sj * e[j], k, -inner[k])
        );
      }
    }
  }

  // 8 corner triangles
  for (const sx of [1, -1]) {
    for (const sy of [1, -1]) {
      for (const sz of [1, -1]) {
        tri(
          [sx * e[0], sy * inner[1], sz * inner[2]],
          [sx * inner[0], sy * e[1], sz * inner[2]],
          [sx * inner[0], sy * inner[1], sz * e[2]]
        );
      }
    }
  }

  const positions = new Float32Array(verts.length * 3);
  verts.forEach((v, i) => positions.set(v, i * 3));
  const geo = new BufferGeometry();
  geo.setAttribute('position', new BufferAttribute(positions, 3));
  geo.computeVertexNormals(); // non-indexed => faceted, per §4.4
  return geo;
}

function normalOf(a, b, c) {
  const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
  const vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
  const n = [uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx];
  const l = Math.hypot(...n) || 1;
  return n.map((v) => v / l);
}

/**
 * Merge a list of `{ size:[w,h,d], at:[x,y,z], bevel?, rotX? }` parts into one
 * faceted geometry. Parts are how every module in the registry is described.
 */
export function buildParts(parts) {
  const geos = parts.map((p) => {
    const g = bevelBox(p.size[0], p.size[1], p.size[2], p.bevel ?? 0.025);
    if (p.rotX) g.rotateX(p.rotX);
    g.translate(p.at?.[0] ?? 0, p.at?.[1] ?? 0, p.at?.[2] ?? 0);
    return g;
  });
  const merged = mergeGeometries(geos, false);
  geos.forEach((g) => g.dispose());
  merged.computeBoundingBox();
  return merged;
}

export const halfExtentsOf = (geometry) => {
  const bb = geometry.boundingBox;
  return new Vector3(
    Math.max(Math.abs(bb.min.x), Math.abs(bb.max.x)),
    Math.max(Math.abs(bb.min.y), Math.abs(bb.max.y)),
    Math.max(Math.abs(bb.min.z), Math.abs(bb.max.z))
  );
};
