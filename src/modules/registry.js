// §8.1 — the module registry.
//
// The definitions themselves live in catalogue/, grouped the way the UI groups
// them. This file is the merge point, the schema documentation, and the load-
// time validation.
//
// Note how few axes are `stretch`. That is deliberate (§1): every axis
// converted from stretch to repeat makes the art problem disappear.
//
// Margins are zero on axes that do not stretch. A margin on a fixed axis would
// classify its outer band as "cap" and hand the whole module to Tier A, which
// is why a counter's front face only reads as trim once z has a real margin.
import { Vector3 } from 'three';
import { buildParts } from './geometry.js';
import { DISPENSARY } from './catalogue/dispensary.js';
import { RETAIL } from './catalogue/retail.js';
import { CONSULTATION, STAFF, SIGNAGE } from './catalogue/rooms.js';

export { CATEGORIES } from './catalogue/schema.js';

/**
 * Schema
 *   unit          half-extents of the ONE repeatable mesh, [hx, hy, hz]
 *   margins       9-slice cap thickness per axis; 0 on non-stretch axes
 *   axes          per axis: { mode: 'repeat'|'stretch'|'fixed', ... }
 *                   repeat  → { unit, min, max }   discrete, CPU instancing
 *                   stretch → { min, max }         continuous, 9-sliced on the GPU
 *   hover         metres above the floor this module sits at when placed —
 *                 wall-mounted things, so they need no wall-socket system
 *   trimAxis      which axis the Tier B trim sheet tiles along
 *   atlasCell     which 2×2 cell of the Tier A atlas the caps sample
 *   build()       the part list: boxes with a size, a position, a trim strip
 *                 and an optional accent slot
 *   mounts        sockets on this module's underside: what it can sit on
 *   provides(p)   sockets this module offers to others, in group space
 *   decor(p)      §8.4 — slots for detail props, as a function of the params,
 *                 so growing a module fills the new space with things. Keys
 *                 must be stable: a slot keeps its prop when others appear.
 *   category      which UI shelf it appears on; see catalogue/schema.js
 *   blurb         one line, shown under the name in the catalogue
 */
export const REGISTRY = {
  ...DISPENSARY,
  ...RETAIL,
  ...CONSULTATION,
  ...STAFF,
  ...SIGNAGE,
};

export const MODULE_IDS = Object.keys(REGISTRY);

/** Build the unit geometry for a module, with its trim axis baked into aTrimV. */
export const buildGeometry = (def) => buildParts(def.build(), { trimAxis: def.trimAxis });

/** §5.2 guards 1 and 2, plus the §4.2 margin rule, asserted at load. */
export function validateRegistry() {
  for (const [id, def] of Object.entries(REGISTRY)) {
    if (def.id !== id) throw new Error(`module "${id}" declares a different id "${def.id}"`);
    if (!def.category) throw new Error(`module "${id}" has no category, so the catalogue cannot shelve it`);

    const h = def.unit;
    def.margins.forEach((m, i) => {
      if (m > h[i]) {
        throw new Error(`module "${id}": margin ${m} exceeds source half-extent ${h[i]} on axis ${'xyz'[i]} — no stretchable middle exists (§5.2)`);
      }
    });
    for (const [axis, spec] of Object.entries(def.axes)) {
      const i = 'xyz'.indexOf(axis);
      if (spec.mode !== 'stretch') {
        if (def.margins[i] !== 0) {
          throw new Error(`module "${id}": axis ${axis} does not stretch, so its margin must be 0 or the whole module reads as a cap (§4.2)`);
        }
        continue;
      }
      const minH = h[i] * spec.min;
      if (minH < def.margins[i]) {
        throw new Error(`module "${id}": minScale on ${axis} allows H=${minH.toFixed(3)} below margin ${def.margins[i]} — caps would overlap (§5.2)`);
      }
    }
  }
}

export const defaultParams = (def) =>
  Object.fromEntries(
    Object.entries(def.axes).map(([axis, spec]) => [axis, spec.default ?? 1])
  );

export const trimAxisVector = (def) => {
  const v = new Vector3();
  v.setComponent(def.trimAxis, 1);
  return v;
};

/** Modules grouped for the UI, in category order. */
export function byCategory(categories) {
  return categories.map((c) => ({
    ...c,
    modules: MODULE_IDS.map((id) => REGISTRY[id]).filter((d) => d.category === c.id),
  }));
}
