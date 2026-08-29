// AdaptivePropBase — a resizable prop that fills itself with clutter.
//
// WHAT THIS IS, AND WHAT IT DELIBERATELY IS NOT.
//
// Everything this class is asked to do already exists in this project, and it
// would be a mistake to build a second copy:
//
//   9-slice piecewise vertex shader   shaders/chunks/deform.glsl.js — slice1D()
//                                     and nineSlice(), shared by the beauty pass
//                                     and the outline prepass so they cannot
//                                     drift apart, and correcting the normal by
//                                     the inverse-transpose of the (diagonal)
//                                     Jacobian, which a naive piecewise scale
//                                     gets wrong and which shows up as flat
//                                     shading on the stretched middle.
//   updateSize()                      ModuleInstance.setParams()
//   a slot spawner                    decor.js — resolveDecor() + DecorLayer,
//                                     and serving_counter already computes
//                                     floor(length / spacing) exactly the way
//                                     the brief describes.
//
// So this is a FACADE with the named API over those systems, plus the one thing
// they genuinely do not cover: a STANDALONE prop. ModuleInstance requires an
// entry in the registry — an id, axes, sockets, a category, a catalogue blurb.
// A factory generated from a reference image has none of that and should not
// have to invent it just to be resized on screen. AdaptivePropBase takes a part
// list (or foreign geometry, via adaptGeometry) and gives it the full adaptive
// behaviour with no registry entry at all.
//
// Two properties are worth keeping when you read the spawner below, because
// they are what separate this from `for (i < n) add(box)`:
//
//   1. Slot contents are a pure function of (seed, slot key). Growing the prop
//      never reshuffles the props already on it, and shrinking and regrowing
//      restores exactly the set you had. `npm test` asserts this.
//   2. Meshes are reused across an update by key, so a resize drag does not
//      churn the scene graph.
import { Group, Mesh, Vector3 } from 'three';
import { BufferAttribute } from 'three';
import { createAdaptiveMaterial } from '../shaders/index.js';
import { buildParts } from './geometry.js';
import { bakeMasks } from '../art/bakeMasks.js';
import { DecorLayer, POOLS } from './decor.js';
import { PALETTE } from '../art/palette.js';
import { stripV } from '../art/trimLayout.js';

/**
 * Give foreign geometry the per-vertex attributes the adaptive material needs.
 *
 * This is the bridge for a mesh this project did not build — the output of an
 * image-to-code factory, say, which will be plain BoxGeometry with position,
 * normal and uv and nothing else. Without `aTrimV` and `aAccent` the shader
 * reads garbage from unbound attributes; without `aMasks` it loses the §4.3
 * cavity and edge shading that does the work of an outline pass.
 *
 * The masks are baked properly (they are a real raycast against the geometry).
 * The material and accent default to a single flat material, because a foreign
 * mesh has not told us what its parts are made of — assign `mat` and `accent`
 * yourself if you want more than one.
 */
export function adaptGeometry(geometry, { mat = 'paint', accent = 0, bake = true } = {}) {
  const count = geometry.getAttribute('position').count;
  if (!geometry.getAttribute('aTrimV')) {
    const strip = stripV(mat);
    const mid = (strip.v0 + strip.v1) / 2;
    geometry.setAttribute('aTrimV', new BufferAttribute(new Float32Array(count).fill(mid), 1));
  }
  if (!geometry.getAttribute('aAccent')) {
    geometry.setAttribute('aAccent', new BufferAttribute(new Float32Array(count).fill(accent), 1));
  }
  if (bake && !geometry.getAttribute('aMasks')) bakeMasks(geometry);
  return geometry;
}

export class AdaptivePropBase {
  /**
   * @param {object} o
   *   parts        the part list, as in a catalogue module's build()
   *   geometry     foreign geometry instead of `parts` (run adaptGeometry first)
   *   halfExtents  [hx, hy, hz] of the undeformed mesh
   *   margins      [mx, my, mz] 9-slice cap thickness; 0 on axes that do not stretch
   *   colors       { base, middle, accent1..accent4 }
   *   propSpacing  metres of top surface each spawned prop is given
   *   propPool     which decor props may appear (see decor.js POOLS)
   *   socketY      height of the top surface the props snap to, in local space
   *   seed         stable across resizes; save it to reload a prop identically
   */
  constructor({
    parts = null,
    geometry = null,
    halfExtents = [0.5, 0.5, 0.5],
    margins = [0, 0, 0],
    colors = {},
    trimAxis = 0,
    trimDensity = 0.45,
    atlasCell = [0, 0],
    propSpacing = 0.55,
    propPool = POOLS.worktop,
    socketY = null,
    socketZ = 0,
    seed = (Math.random() * 0xffffffff) >>> 0,
  } = {}) {
    if (!parts && !geometry) throw new Error('AdaptivePropBase needs `parts` or `geometry`');

    this.halfExtents = new Vector3(...halfExtents);
    this.margins = new Vector3(...margins);
    this.propSpacing = propSpacing;
    this.propPool = propPool;
    this.seed = seed;
    this.scale = new Vector3(1, 1, 1);
    // default the socket to the top of the undeformed box
    this.socketY = socketY ?? this.halfExtents.y;
    this.socketZ = socketZ;

    this.geometry = geometry
      ? adaptGeometry(geometry)
      : bakeMasks(buildParts(parts, { trimAxis }));

    const axis = new Vector3();
    axis.setComponent(trimAxis, 1);
    this.material = createAdaptiveMaterial({
      baseColor: colors.base ?? PALETTE.paper,
      middleColor: colors.middle ?? colors.base ?? PALETTE.bone,
      accent1: colors.accent1 ?? null,
      accent2: colors.accent2 ?? null,
      accent3: colors.accent3 ?? null,
      accent4: colors.accent4 ?? null,
      sourceHalfExtents: this.halfExtents,
      margins: this.margins,
      trimAxis: axis,
      trimDensity,
      atlasCell,
    });

    this.group = new Group();
    this.group.name = 'adaptive-prop';
    this.mesh = new Mesh(this.geometry, this.material);
    this.group.add(this.mesh);

    // The clutter lives in its own layer so the base mesh can be replaced or
    // re-scaled without disturbing what is standing on it.
    this.decor = new DecorLayer();
    this.group.add(this.decor.group);

    this.updateSize(1, 1, 1);
  }

  /**
   * How many props the current width has room for.
   *
   * floor(), not round(): a slot that does not fit a whole prop should stay
   * empty rather than crowd the one beside it, and `Math.max(1, ...)` because a
   * prop at minimum scale should still carry something — an empty worktop reads
   * as a shop that has closed.
   *
   * The epsilon is not defensive padding, it is a correctness fix, and the
   * smoke test caught it on its first run. A 1.2 m top at 0.4 m spacing fits
   * exactly three props, but `0.6 * 2 / 0.4` evaluates to 2.9999999999999996 in
   * binary floating point, so a bare floor() returns TWO — and the error
   * compounds with scale, giving 8 where 9 fit. Any spacing that divides the
   * width evenly is a candidate, which is to say all the round numbers a person
   * would actually type.
   */
  get availableSlots() {
    const width = this.halfExtents.x * 2 * this.scale.x;
    return Math.max(1, Math.floor(width / this.propSpacing + 1e-9));
  }

  /**
   * Resize, and refill.
   *
   * The scale goes to the GPU as `uTargetScale`, where the 9-slice reads it —
   * the mesh's own transform is untouched, which is the whole point: scaling
   * the Object3D would squash the corners, and this stretches only the middle
   * band between the margins.
   */
  updateSize(scaleX = 1, scaleY = 1, scaleZ = 1) {
    this.scale.set(scaleX, scaleY, scaleZ);
    this.material.uniforms.uTargetScale.value.copy(this.scale);
    this.spawnProps();
    return this;
  }

  /**
   * The slot spawner. Declares slots, then lets resolveDecor fill them.
   *
   * Slots are declared from the CURRENT width and given keys derived from their
   * index, so slot `s3` holds the same prop whatever else changes around it.
   * That is what makes growing the prop additive rather than a reshuffle, and
   * it is why the keys are index-based rather than position-based: a
   * position-keyed slot moves when the spacing changes and loses its contents.
   */
  spawnProps() {
    const n = this.availableSlots;
    const half = this.halfExtents.x * scaleOr1(this.scale.x);
    const step = (half * 2) / n;
    const y = this.socketY * scaleOr1(this.scale.y);
    const slots = [];
    for (let i = 0; i < n; i++) {
      slots.push({
        key: `s${i}`,
        pos: [-half + (i + 0.5) * step, y, this.socketZ],
        pool: this.propPool,
        chance: 0.85,
        jitter: 0.04,
        pair: 0.35,
      });
    }
    this.liveProps = this.decor.update(this.seed, slots);
    return this.liveProps;
  }

  dispose() {
    this.decor.dispose();
    this.group.parent?.remove(this.group);
    this.geometry.dispose();
    this.material.dispose();
  }
}

// A stretched axis scales its middle band only, so the overall half-extent
// grows by the target scale; a fixed axis (margin 0, scale 1) does not move.
const scaleOr1 = (s) => (Number.isFinite(s) && s > 0 ? s : 1);
