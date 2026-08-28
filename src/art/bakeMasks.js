// §4.3 — vertex-baked geometric masks. The highest-value technique in the brief.
//
// Runs once per module type at load, on the UNDEFORMED merged geometry.
//   R — cavity : hemisphere raycast AO against the module's own geometry
//   G — edge   : per-vertex pointiness (signed dihedral angle at incident edges)
//   B — up     : max(dot(normal, +Y), 0)
//
// These are per-vertex quantities, so they deform correctly under 9-slice for free.
import { BufferAttribute, Mesh, MeshBasicMaterial, Raycaster, Vector3 } from 'three';

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
  const collider = new Mesh(geometry, new MeshBasicMaterial());
  collider.updateMatrixWorld();
  const raycaster = new Raycaster();
  raycaster.far = radius;
  const dirs = hemisphereDirs(rays);
  const origin = new Vector3(), normal = new Vector3(), dir = new Vector3();
  const tangent = new Vector3(), bitangent = new Vector3();
  const aoByWeld = new Map();
  for (const [k, w] of welds) {
    const i = w.verts[0];
    origin.fromBufferAttribute(pos, i);
    normal.fromBufferAttribute(nrm, i).normalize();
    basis(normal, tangent, bitangent);
    origin.addScaledVector(normal, 1e-3);
    let hits = 0;
    for (const s of dirs) {
      dir.set(0, 0, 0)
        .addScaledVector(tangent, s.x)
        .addScaledVector(bitangent, s.y)
        .addScaledVector(normal, s.z)
        .normalize();
      raycaster.set(origin, dir);
      const hit = raycaster.intersectObject(collider, false)[0];
      // near hits occlude more than distant ones
      if (hit) hits += 1 - hit.distance / radius;
    }
    aoByWeld.set(k, hits / dirs.length);
  }
  collider.material.dispose();

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
