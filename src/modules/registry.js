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
import { STRIPS } from '../art/trimLayout.js';
import { NEUTRAL } from './catalogue/fittings.js';
import { DISPENSARY } from './catalogue/dispensary.js';
import { RETAIL } from './catalogue/retail.js';
import { CONSULTATION, STAFF, SIGNAGE } from './catalogue/rooms.js';

export { CATEGORIES } from './catalogue/schema.js';

/**
 * Schema
 *   unit          half-extents of the ONE repeatable mesh, [hx, hy, hz]
 *   margins       9-slice cap thickness per axis; 0 on non-stretch axes
 *   axes          per axis: { mode: 'repeat'|'steps'|'stretch'|'fixed', ... }
 *                   repeat  → { unit, min, max }   discrete, CPU instancing
 *                   steps   → { steps: [{ v, label }] }  discrete, REBUILT
 *                   stretch → { min, max }         continuous, 9-sliced on the GPU
 *
 *                 §C1 — `steps` is the snap-between-variants axis: instead of
 *                 scaling or instancing, the module is rebuilt as a different
 *                 object when the axis crosses a step, which is how a fridge
 *                 becomes a double-door fridge instead of a smeared wide one.
 *                 `v` is the multiplier on `unit` half-extents for that axis —
 *                 the same convention as a repeat axis's bay count, so every
 *                 `unit[i] * p.i` placement/socket expression is unchanged.
 *                 A steps axis, like a repeat one, must have margin 0.
 *   hover         metres above the floor this module sits at when placed —
 *                 wall-mounted things, so they need no wall-socket system
 *   trimAxis      which axis the Tier B trim sheet tiles along
 *   atlasCell     which 2×2 cell of the Tier A atlas the caps sample
 *   build(p)      the part list: boxes with a size, a position, a trim strip
 *                 and an optional accent slot. The params object is optional:
 *                 a build declared with no arguments (`build: () => [...]`) is
 *                 params-independent and gets ONE cached geometry, while a
 *                 build that declares `p` is rebuilt per discrete-param value
 *                 (see geometryKey below). `def.build.length` is the test, so
 *                 no existing zero-arg build needs an edit.
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
export const buildGeometry = (def, p) =>
  buildParts(def.build(p ?? defaultParams(def)), { trimAxis: def.trimAxis });

/** The axis modes whose value is a whole number and therefore keyable. */
export const DISCRETE_MODES = new Set(['repeat', 'steps']);

/**
 * The cache/batch identity of a built geometry.
 *
 * Only the DISCRETE axes are in the key: a stretch axis is a GPU-side deform of
 * the same buffer, so keying on it would shatter the cache for nothing. And a
 * module whose build ignores its params keys on its id alone — otherwise 200
 * medicine boxes at three different bay counts would become three batches
 * instead of one, which is exactly the draw-call property Phase 6 bought.
 */
export function geometryKey(def, p) {
  if (def.build.length === 0) return def.id;
  const parts = Object.entries(def.axes)
    .filter(([, spec]) => DISCRETE_MODES.has(spec.mode))
    .map(([axis]) => `${axis}${p?.[axis] ?? def.axes[axis].default ?? 1}`);
  return parts.length ? `${def.id}|${parts.join(',')}` : def.id;
}

/** Every discrete-param combination a module can be built at, for pre-baking. */
export function geometryVariants(def) {
  if (def.build.length === 0) return [defaultParams(def)];
  let out = [defaultParams(def)];
  for (const [axis, spec] of Object.entries(def.axes)) {
    if (spec.mode !== 'steps') continue; // repeat axes place the same mesh N times
    out = out.flatMap((p) => spec.steps.map((s) => ({ ...p, [axis]: s.v })));
  }
  return out;
}

const PART_KEYS = new Set(['size', 'at', 'bevel', 'rotX', 'rotY', 'rotZ', 'mat', 'accent', 'taper']);

/** §5.2 guards 1 and 2, plus the §4.2 margin rule, asserted at load. */
export function validateRegistry() {
  for (const [id, def] of Object.entries(REGISTRY)) {
    if (def.id !== id) throw new Error(`module "${id}" declares a different id "${def.id}"`);
    if (!def.category) throw new Error(`module "${id}" has no category, so the catalogue cannot shelve it`);

    // A part says what it is MADE OF, and a typo would silently fall back to
    // whatever strip happened to be at that V — which is exactly how a computer
    // screen ended up textured like rock. Fail loudly instead.
    // Every variant a steps axis can produce is a different part list, so each
    // one gets the same scrutiny as the default build.
    for (const variant of geometryVariants(def)) def.build(variant).forEach((part, i) => {
      if (part.mat !== undefined && !STRIPS[part.mat]) {
        throw new Error(
          `module "${id}" part ${i}: unknown material "${part.mat}" — known: ${Object.keys(STRIPS).join(', ')}`
        );
      }
      // A key nobody reads is a change that silently does not happen — a
      // `rotZ` written against a build that only handled `rotX` cost a rebuild
      // to notice, and would have cost a lot more had it looked plausible.
      for (const key of Object.keys(part)) {
        if (!PART_KEYS.has(key)) {
          throw new Error(
            `module "${id}" part ${i}: unknown key "${key}" — known: ${[...PART_KEYS].join(', ')}`
          );
        }
      }
      // The shader picks an accent with a descending chain of comparisons, so
      // an index past the top slot lands on the top slot instead of failing —
      // the part comes out a plausible wrong colour and nobody notices. Same
      // failure shape as the unknown material above, so the same treatment.
      if (part.accent !== undefined) {
        const a = part.accent;
        if (!Number.isInteger(a) || a < 0 || a > NEUTRAL) {
          throw new Error(
            `module "${id}" part ${i}: accent ${a} is not a slot — 0=BODY 1=FRAME 2=ACCENT 3=DARK 4=GLASS ${NEUTRAL}=NEUTRAL`
          );
        }
        if (a === NEUTRAL && def.colors.accent5 === undefined) {
          throw new Error(
            `module "${id}" part ${i}: uses NEUTRAL but the module declares no accent5, so it would fall back to accent1`
          );
        }
      }
    });

    const h = def.unit;
    def.margins.forEach((m, i) => {
      if (m > h[i]) {
        throw new Error(`module "${id}": margin ${m} exceeds source half-extent ${h[i]} on axis ${'xyz'[i]} — no stretchable middle exists (§5.2)`);
      }
    });
    for (const [axis, spec] of Object.entries(def.axes)) {
      const i = 'xyz'.indexOf(axis);
      if (spec.mode === 'steps') {
        if (!Array.isArray(spec.steps) || spec.steps.length === 0) {
          throw new Error(`module "${id}": axis ${axis} is a steps axis with no steps to snap between`);
        }
        for (const s of spec.steps) {
          if (!Number.isFinite(s.v) || s.v <= 0) {
            throw new Error(`module "${id}": axis ${axis} step "${s.label}" has v=${s.v}, which is not a unit multiplier`);
          }
          if (!s.label) throw new Error(`module "${id}": axis ${axis} step v=${s.v} has no label, and the Size panel shows labels`);
        }
        if (!spec.steps.some((s) => s.v === (spec.default ?? 1))) {
          throw new Error(`module "${id}": axis ${axis} default ${spec.default ?? 1} is not one of its steps`);
        }
        // A steps axis rebuilds; a build that ignores p would just place the
        // same mesh and silently do nothing.
        if (def.build.length === 0) {
          throw new Error(`module "${id}": axis ${axis} steps between variants, but build() takes no params, so nothing would change`);
        }
      }
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
