// §4.3 — vertex-baked geometric masks. The highest-value technique in the brief.
//
// Runs once per module type at load, on the UNDEFORMED merged geometry.
//   R — cavity : hemisphere raycast AO against the module's own geometry
//   G — edge   : per-vertex pointiness (signed dihedral angle at incident edges)
//   B — up     : max(dot(normal, +Y), 0)
//
// These are per-vertex quantities, so they deform correctly under 9-slice for free.
import { BufferAttribute, Vector3 } from 'three';

const KEY = 1e4; // position weld tolerance: 0.1mm

const keyOf = (x, y, z) =>
  `${Math.round(x * KEY)},${Math.round(y * KEY)},${Math.round(z * KEY)}`;

/**
 * @param {THREE.BufferGeometry} geometry non-indexed or indexed, already has normals
 * @param {{rays?:number, radius?:number}} opts
 * @returns {THREE.BufferGeometry} the same geometry, with `aMasks` (and `color`) set
 */
export function bakeMasks(geometry, { rays = 20, radius = 0.35 } = {}) {
  const pos = geometry.getAttribute('position');
  const nrm = geometry.getAttribute('normal');
  const count = pos.count;
  const index = geometry.getIndex();
  const triCount = index ? index.count / 3 : count / 3;
  const tri = (i) => (index ? index.getX(i) : i);

  // --- weld ------------------------------------------------------------
  const welds = new Map(); // key -> { verts:[i], faces:[{n,c}] }
  const buckets = new Array(count);
  for (let i = 0; i < count; i++) {
    const k = keyOf(pos.getX(i), pos.getY(i), pos.getZ(i));
    let w = welds.get(k);
    if (!w) welds.set(k, (w = { verts: [], faces: [] }));
    w.verts.push(i);
    buckets[i] = w;
  }

  // --- gather incident faces per welded vertex --------------------------
  const a = new Vector3(), b = new Vector3(), c = new Vector3();
  const ab = new Vector3(), ac = new Vector3();
  for (let f = 0; f < triCount; f++) {
    const i0 = tri(f * 3), i1 = tri(f * 3 + 1), i2 = tri(f * 3 + 2);
    a.fromBufferAttribute(pos, i0);
    b.fromBufferAttribute(pos, i1);
    c.fromBufferAttribute(pos, i2);
    const n = ab.subVectors(b, a).cross(ac.subVectors(c, a)).normalize().clone();
    if (!Number.isFinite(n.x)) continue; // degenerate
    const centroid = new Vector3().add(a).add(b).add(c).multiplyScalar(1 / 3);
    for (const i of [i0, i1, i2]) buckets[i].faces.push({ n, c: centroid });
  }

  // --- G: pointiness ----------------------------------------------------
  const edgeByWeld = new Map();
  const d = new Vector3();
  for (const [k, w] of welds) {
    let sharpest = 0;
    for (let i = 0; i < w.faces.length; i++) {
      for (let j = i + 1; j < w.faces.length; j++) {
        const fi = w.faces[i], fj = w.faces[j];
        const dot = Math.min(1, Math.max(-1, fi.n.dot(fj.n)));
        if (dot > 0.999) continue; // coplanar
        const angle = Math.acos(dot) / Math.PI; // 0..1
        // convex when each face leans away from the other's centroid
        const convex = fi.n.dot(d.subVectors(fj.c, fi.c)) < 0;
        const signed = convex ? angle : -angle;
        if (signed > sharpest) sharpest = signed;
      }
    }
    edgeByWeld.set(k, sharpest);
  }

  // --- R: hemisphere AO -------------------------------------------------
  // Every ray is at most `radius` long, so it can only ever hit a triangle
  // near its origin. Bucketing the triangles into a grid of exactly that cell
  // size means the 3×3×3 block around a vertex provably contains every
  // triangle it could reach, and the whole bake stops being quadratic in the
  // part count — which is what lets a module carry studs, vents and label
  // plates without the loader stalling.
  const grid = triangleGrid(pos, tri, triCount, radius);
  const dirs = hemisphereDirs(rays);
  const origin = new Vector3(), normal = new Vector3(), dir = new Vector3();
  const tangent = new Vector3(), bitangent = new Vector3();
  const aoByWeld = new Map();
  const candidates = new Set();
  for (const [k, w] of welds) {
    const i = w.verts[0];
    origin.fromBufferAttribute(pos, i);
    normal.fromBufferAttribute(nrm, i).normalize();
    basis(normal, tangent, bitangent);
    origin.addScaledVector(normal, 1e-3);
    grid.near(origin, candidates);
    let hits = 0;
    for (const s of dirs) {
      dir.set(0, 0, 0)
        .addScaledVector(tangent, s.x)
        .addScaledVector(bitangent, s.y)
        .addScaledVector(normal, s.z)
        .normalize();
      let nearest = radius;
      for (const t of candidates) {
        const d = grid.hit(t, origin, dir, nearest);
        if (d >= 0) nearest = d;
      }
      // near hits occlude more than distant ones
      if (nearest < radius) hits += 1 - nearest / radius;
    }
    aoByWeld.set(k, hits / dirs.length);
  }

  // --- scatter back -----------------------------------------------------
  const masks = new Float32Array(count * 3);
  for (const [k, w] of welds) {
    const cavity = Math.min(1, aoByWeld.get(k) * 1.6);
    const edge = Math.min(1, Math.max(0, edgeByWeld.get(k)) * 2.0);
    for (const i of w.verts) {
      const up = Math.max(0, nrm.getY(i));
      masks[i * 3 + 0] = cavity;
      masks[i * 3 + 1] = edge;
      masks[i * 3 + 2] = up;
    }
  }

  const attr = new BufferAttribute(masks, 3);
  geometry.setAttribute('aMasks', attr);
  geometry.setAttribute('color', attr); // COLOR_0, same buffer
  return geometry;
}

/**
 * Triangles bucketed by a grid whose cell is the ray length, plus the
 * ray/triangle test itself (Möller–Trumbore). Registering a triangle in every
 * cell its bounding box touches is what makes the 3×3×3 lookup exact rather
 * than approximate: a hit within `radius` of the origin lies in that block, and
 * whichever cell it lies in has the triangle.
 */
function triangleGrid(pos, tri, triCount, radius) {
  const cell = Math.max(radius, 1e-4);
  const verts = new Float32Array(triCount * 9);
  const cells = new Map();
  const key = (x, y, z) => `${x},${y},${z}`;
  const idx = (v) => Math.floor(v / cell);

  for (let f = 0; f < triCount; f++) {
    let lo = [Infinity, Infinity, Infinity];
    let hi = [-Infinity, -Infinity, -Infinity];
    for (let c = 0; c < 3; c++) {
      const i = tri(f * 3 + c);
      const p = [pos.getX(i), pos.getY(i), pos.getZ(i)];
      verts.set(p, f * 9 + c * 3);
      for (let a = 0; a < 3; a++) {
        if (p[a] < lo[a]) lo[a] = p[a];
        if (p[a] > hi[a]) hi[a] = p[a];
      }
    }
    for (let x = idx(lo[0]); x <= idx(hi[0]); x++) {
      for (let y = idx(lo[1]); y <= idx(hi[1]); y++) {
        for (let z = idx(lo[2]); z <= idx(hi[2]); z++) {
          const k = key(x, y, z);
          let bucket = cells.get(k);
          if (!bucket) cells.set(k, (bucket = []));
          bucket.push(f);
        }
      }
    }
  }

  return {
    /** Every triangle a ray of length `radius` from `p` could possibly reach. */
    near(p, out) {
      out.clear();
      const cx = idx(p.x), cy = idx(p.y), cz = idx(p.z);
      for (let x = cx - 1; x <= cx + 1; x++) {
        for (let y = cy - 1; y <= cy + 1; y++) {
          for (let z = cz - 1; z <= cz + 1; z++) {
            const bucket = cells.get(key(x, y, z));
            if (bucket) for (const f of bucket) out.add(f);
          }
        }
      }
      return out;
    },

    /** Distance along `dir` to triangle `f`, or -1 for no hit inside `far`. */
    hit(f, origin, dir, far) {
      const o = f * 9;
      const ax = verts[o], ay = verts[o + 1], az = verts[o + 2];
      const e1x = verts[o + 3] - ax, e1y = verts[o + 4] - ay, e1z = verts[o + 5] - az;
      const e2x = verts[o + 6] - ax, e2y = verts[o + 7] - ay, e2z = verts[o + 8] - az;
      const px = dir.y * e2z - dir.z * e2y;
      const py = dir.z * e2x - dir.x * e2z;
      const pz = dir.x * e2y - dir.y * e2x;
      const det = e1x * px + e1y * py + e1z * pz;
      if (det > -1e-12 && det < 1e-12) return -1; // parallel
      const inv = 1 / det;
      const tx = origin.x - ax, ty = origin.y - ay, tz = origin.z - az;
      const u = (tx * px + ty * py + tz * pz) * inv;
      if (u < 0 || u > 1) return -1;
      const qx = ty * e1z - tz * e1y;
      const qy = tz * e1x - tx * e1z;
      const qz = tx * e1y - ty * e1x;
      const v = (dir.x * qx + dir.y * qy + dir.z * qz) * inv;
      if (v < 0 || u + v > 1) return -1;
      const t = (e2x * qx + e2y * qy + e2z * qz) * inv;
      return t > 1e-6 && t < far ? t : -1;
    },
  };
}

function basis(n, t, b) {
  const up = Math.abs(n.y) < 0.99 ? UP : SIDE;
  t.crossVectors(up, n).normalize();
  b.crossVectors(n, t).normalize();
}
const UP = new Vector3(0, 1, 0);
const SIDE = new Vector3(1, 0, 0);

/** Cosine-ish hemisphere directions in tangent space (z = normal). */
function hemisphereDirs(n) {
  const out = [];
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < n; i++) {
    const z = Math.sqrt((i + 0.5) / n); // bias toward the normal
    const r = Math.sqrt(1 - z * z);
    const theta = i * golden;
    out.push({ x: Math.cos(theta) * r, y: Math.sin(theta) * r, z });
  }
  return out;
}
