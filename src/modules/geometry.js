// Parametric beveled boxes (§11.1 step 4: rebuild from numbers, not from a mesh).
//
// Fat corner radii are most of the "chunky hand-painted" read, and a chamfered
// box gives the vertex-mask bake (§4.3) real convex edges to find.
//
// Each vertex carries:
//   position, normal   faceted, non-indexed
//   uv                 planar per face, 0..1 — Tier A, remapped to an atlas cell
//   aTrimV             the trim sheet row for this vertex — Tier B (§4.1)
//
// aTrimV is baked rather than computed in the shader because it is exactly the
// kind of per-vertex quantity that survives the 9-slice deform for free.
import { BufferGeometry, BufferAttribute, Vector3 } from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { stripV } from '../art/trimLayout.js';

const EDGE = stripV('edge');

// Pixel-art / voxel forms have hard edges. The chamfer is kept — the vertex
// mask bake needs convex edges to find, and the trim sheet's edge strip needs
// somewhere to land — but scaled down until it reads as a crisp corner with a
// one-texel painted highlight rather than a rounded bevel.
const EDGE_SOFTNESS = 0.4;

/**
 * Chamfered box centred on the origin.
 * @param {number} w full width (x)
 * @param {number} h full height (y)
 * @param {number} d full depth (z)
 * @param {number} bevel chamfer size, clamped to a third of the smallest extent
 * @param {{trimAxis?:number, strip?:string}} opts
 *   trimAxis — index of the axis the trim sheet tiles along (U)
 *   strip    — which trim strip this part's flat faces sample
 *   accent   — 0 base colour, 1 or 2 an accent from the module's palette entry
 */
export function bevelBox(w, h, d, bevel = 0.03, opts = {}) {
  const trimAxis = opts.trimAxis ?? 0;
  const accent = opts.accent ?? 0;
  const flat = stripV(opts.strip ?? 'surface');

  const e = [w / 2, h / 2, d / 2];
  const b = Math.min(bevel, Math.min(w, h, d) / 3);
  const inner = e.map((v) => v - b);
  const verts = [];

  const vert = (p, uv, trimV) => ({ p, uv, trimV });
  const at = (i, vi, j, vj, k, vk) => {
    const p = [0, 0, 0];
    p[i] = vi; p[j] = vj; p[k] = vk;
    return p;
  };
  const norm01 = (value, half) => (half > 1e-6 ? value / (2 * half) + 0.5 : 0.5);

  const tri = (a, bb, c) => {
    const n = normalOf(a.p, bb.p, c.p);
    const cx = (a.p[0] + bb.p[0] + c.p[0]) / 3;
    const cy = (a.p[1] + bb.p[1] + c.p[1]) / 3;
    const cz = (a.p[2] + bb.p[2] + c.p[2]) / 3;
    if (n[0] * cx + n[1] * cy + n[2] * cz < 0) verts.push(a, c, bb);
    else verts.push(a, bb, c);
  };
  const quad = (a, bb, c, d2) => { tri(a, bb, c); tri(a, c, d2); };

  // --- 6 inset faces ---------------------------------------------------
  // V axis for the trim is the in-plane axis that is NOT the tiling axis, so
  // painted borders run parallel to the stretch and survive it.
  for (let i = 0; i < 3; i++) {
    const j = (i + 1) % 3, k = (i + 2) % 3;
    const vAxis = i === trimAxis ? j : (j === trimAxis ? k : j);
    const face = (pos) => {
      const t = norm01(pos[vAxis], e[vAxis]);
      return vert(
        pos,
        [norm01(pos[j], e[j]), norm01(pos[k], e[k])],
        flat.v0 + t * (flat.v1 - flat.v0)
      );
    };
    for (const s of [1, -1]) {
      quad(
        face(at(i, s * e[i], j, -inner[j], k, -inner[k])),
        face(at(i, s * e[i], j, inner[j], k, -inner[k])),
        face(at(i, s * e[i], j, inner[j], k, inner[k])),
        face(at(i, s * e[i], j, -inner[j], k, inner[k]))
      );
    }
  }

  // --- 12 chamfer quads: the painted bevel strip -----------------------
  for (let i = 0; i < 3; i++) {
    const j = (i + 1) % 3, k = (i + 2) % 3;
    for (const si of [1, -1]) {
      for (const sj of [1, -1]) {
        const edge = (pos, t) =>
          vert(pos, [norm01(pos[k], e[k]), t], EDGE.v0 + t * (EDGE.v1 - EDGE.v0));
        quad(
          edge(at(i, si * e[i], j, sj * inner[j], k, -inner[k]), 0),
          edge(at(i, si * e[i], j, sj * inner[j], k, inner[k]), 0),
          edge(at(i, si * inner[i], j, sj * e[j], k, inner[k]), 1),
          edge(at(i, si * inner[i], j, sj * e[j], k, -inner[k]), 1)
        );
      }
    }
  }

  // --- 8 corner triangles ----------------------------------------------
  const mid = (EDGE.v0 + EDGE.v1) / 2;
  for (const sx of [1, -1]) {
    for (const sy of [1, -1]) {
      for (const sz of [1, -1]) {
        tri(
          vert([sx * e[0], sy * inner[1], sz * inner[2]], [0.5, 0.0], EDGE.v0),
          vert([sx * inner[0], sy * e[1], sz * inner[2]], [0.5, 1.0], EDGE.v1),
          vert([sx * inner[0], sy * inner[1], sz * e[2]], [0.5, 0.5], mid)
        );
      }
    }
  }

  const count = verts.length;
  const positions = new Float32Array(count * 3);
  const uvs = new Float32Array(count * 2);
  const trimV = new Float32Array(count);
  const accents = new Float32Array(count).fill(accent);
  verts.forEach((v, i) => {
    positions.set(v.p, i * 3);
    uvs.set(v.uv, i * 2);
    trimV[i] = v.trimV;
  });

  const geo = new BufferGeometry();
  geo.setAttribute('position', new BufferAttribute(positions, 3));
  geo.setAttribute('uv', new BufferAttribute(uvs, 2));
  geo.setAttribute('aTrimV', new BufferAttribute(trimV, 1));
  geo.setAttribute('aAccent', new BufferAttribute(accents, 1));
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
 * Merge a list of parts into one faceted geometry. Parts are how every module
 * in the registry is described.
 * @param {{size:number[], at?:number[], bevel?:number, rotX?:number, strip?:string, accent?:number}[]} parts
 * @param {{trimAxis?:number}} opts
 */
export function buildParts(parts, opts = {}) {
  const geos = parts.map((p) => {
    const g = bevelBox(p.size[0], p.size[1], p.size[2], (p.bevel ?? 0.025) * EDGE_SOFTNESS, {
      trimAxis: opts.trimAxis ?? 0,
      strip: p.strip,
      accent: p.accent,
    });
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
