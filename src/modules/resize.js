// §8.2 — the two resize modes.
//
//   stretch → 9-slice, continuous, GPU vertex shader (one mesh, uTargetScale)
//   repeat  → discrete, CPU: the unit mesh is placed N times along the axis
//   steps   → discrete, CPU: the module is REBUILT as a different variant
//             (§C1). One mesh, never scaled, never repeated — the param is only
//             a multiplier on the unit half-extents so footprints and sockets
//             read the same as a repeat axis.
//
// Default to repeat when the real object is modular. This is the primary lever
// on art quality — a repeated bay keeps its untouched UVs and full detail.

/** Clamp a param to its axis spec, honouring §5.2 guard 1 for stretch axes. */
export function clampParam(spec, value) {
  if (spec.mode === 'fixed') return 1;
  if (spec.mode === 'repeat') {
    return Math.max(spec.min, Math.min(spec.max, Math.round(value)));
  }
  // A saved file carries plain numbers, so a value between (or outside) the
  // declared steps snaps to the nearest one rather than becoming a variant that
  // has no geometry.
  if (spec.mode === 'steps') {
    const n = Number(value);
    if (!Number.isFinite(n)) return spec.default ?? spec.steps[0].v;
    return spec.steps.reduce((best, s) =>
      Math.abs(s.v - n) < Math.abs(best - n) ? s.v : best, spec.steps[0].v);
  }
  return Math.max(spec.min, Math.min(spec.max, value));
}

export function clampParams(def, params) {
  const out = {};
  for (const [axis, spec] of Object.entries(def.axes)) {
    out[axis] = clampParam(spec, params?.[axis] ?? spec.default ?? 1);
  }
  return out;
}

/**
 * Lay the unit mesh out for the given params.
 * @returns {{position:[number,number,number], targetScale:[number,number,number]}[]}
 *   positions are relative to the module's group origin, which sits on the floor
 *   at the centre of the run.
 */
export function layout(def, params) {
  const [hx, hy, hz] = def.unit;
  const counts = { x: 1, y: 1, z: 1 };
  const scale = { x: 1, y: 1, z: 1 };

  for (const [axis, spec] of Object.entries(def.axes)) {
    // 'steps' is deliberately absent: its size is already in the geometry, so
    // it neither repeats a cell nor scales one — count 1, scale 1.
    if (spec.mode === 'repeat') counts[axis] = params[axis];
    else if (spec.mode === 'stretch') scale[axis] = params[axis];
  }

  const half = { x: hx, y: hy, z: hz };
  const out = [];
  for (let i = 0; i < counts.x; i++) {
    for (let j = 0; j < counts.y; j++) {
      for (let k = 0; k < counts.z; k++) {
        out.push({
          position: [
            (i - (counts.x - 1) / 2) * half.x * 2,
            j * half.y * 2 + half.y * scale.y,
            (k - (counts.z - 1) / 2) * half.z * 2,
          ],
          targetScale: [scale.x, scale.y, scale.z],
        });
      }
    }
  }
  return out;
}

/** Half-extents of the whole laid-out module, in group space. */
export function footprint(def, params) {
  const [hx, hy, hz] = def.unit;
  const n = (axis, h) => {
    const spec = def.axes[axis];
    // steps shares repeat's convention on purpose: the variant is built to fill
    // exactly `unit * v`, so the footprint and the sockets need no special case.
    if (spec.mode === 'repeat' || spec.mode === 'steps') return h * params[axis];
    if (spec.mode === 'stretch') return h * params[axis];
    return h;
  };
  return [n('x', hx), n('y', hy), n('z', hz)];
}
