// WATERTIGHTNESS CHECK for shapedBox. Run after ANY change to its topology.
//
//     node tools/voxel-fridge/watertight.mjs
//
// A BOUNDS CHECK CANNOT SEE A TOPOLOGY BUG. Every vertex of a broken box is
// still inside the box, so "are all the vertices in range" passes while the
// mesh has holes at some corners and loose triangles at others. That exact bug
// shipped once here: the corner triangles were inset on ONE axis where they
// need two. What finds it is the manifold property — in a closed surface every
// edge is shared by exactly two triangles, and V - E + F = 2.
//
// docs/BUILDING-A-PROP.txt names this check in its troubleshooting section and
// there was no tool for it, so it was never run. It exists now because the
// bevel was generalised from one number per AXIS to one per FACE, which touches
// every triangle the function emits.
import * as THREE from 'three';
import { shapedBox } from './style.js';

const key = (p) => p.map((v) => Math.round(v * 1e4) / 1e4).join(',');
let failed = 0;

function check(label, bevel, taperX = 0, taperZ = 0) {
  const g = shapedBox(THREE, 20, 14, 26, bevel, taperX, taperZ);
  const P = g.attributes.position.array;
  const n = P.length / 9;
  const verts = new Set(), edges = new Map();
  for (let t = 0; t < n; t++) {
    const v = [0, 1, 2].map((i) =>
      key([P[t * 9 + i * 3], P[t * 9 + i * 3 + 1], P[t * 9 + i * 3 + 2]]));
    v.forEach((x) => verts.add(x));
    for (let i = 0; i < 3; i++) {
      const e = [v[i], v[(i + 1) % 3]].sort().join('|');
      edges.set(e, (edges.get(e) ?? 0) + 1);
    }
  }
  const bad = [...edges.values()].filter((c) => c !== 2).length;
  const V = verts.size, E = edges.size, F = n;
  const euler = V - E + F;
  const ok = bad === 0 && euler === 2;
  if (!ok) failed++;
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${label.padEnd(34)}`
    + ` ${String(F).padStart(3)} tris  V-E+F=${euler}`
    + `  ${bad === 0 ? 'every edge used twice' : bad + ' EDGES NOT USED TWICE'}`);
}

console.log('shapedBox watertightness');
check('bevel 0', 0);
check('bevel 1.6, uniform', 1.6);
check('bevel [2, 0, 2], per axis', [2, 0, 2]);
check('bevel [0.6, 3.4, 0.6], per axis', [0.6, 3.4, 0.6]);
check('bevel [2,2, 0,1.5, 0,2], per face', [2, 2, 0, 1.5, 0, 2]);
check('bevel [0,3, 0,0, 0,0], one face', [0, 3, 0, 0, 0, 0]);
check('bevel [1,2, 3,0.5, 0,4], all six', [1, 2, 3, 0.5, 0, 4]);
check('bevel [2,2, 0,1.5, 0,2] + taper', [2, 2, 0, 1.5, 0, 2], 1.5, 1.5);
check('bevel clamped past half', [99, 99, 99, 99, 99, 99]);

console.log(failed ? `\n${failed} FAILED` : '\nall watertight');
process.exit(failed ? 1 : 0);
