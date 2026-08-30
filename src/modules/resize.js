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
//
// -------------------------------------------------------------------------
// §C2 STRETCH AUDIT — every stretch axis left in the catalogue, and what sits
// in its smearable middle. A vertex is rigid only where |p| > unit − margin on
// that axis (see slice1D in shaders/chunks/deform.glsl.js); anything inside
// that band is scaled by the shader, so a fitting there stops being a fitting.
//
//  module               axis  middle band   what lives in it          verdict
//  ------------------------------------------------------------------------
//  dispensing_desk      z     |z| ≤ 0.23    the four foot blocks      note
//  dispensary_shelving  z     |z| ≤ 0.115   nothing                   clean
//  gondola_shelf        z     |z| ≤ 0.19    end panels (plain)        clean
//  serving_counter      z     |z| ≤ 0.23    nothing                   clean
//  sink_unit            z     |z| ≤ 0.23    the side vent stack       note
//  consultation_booth   x,z   |x|,|z| ≤0.64 the two roof vent boxes   note
//
// Every pull, plate, label window, knob, price rail and readout in the
// catalogue is in a cap. The three notes are all the same benign shape: the
// part is a plain block or a slot that RUNS ALONG the stretched axis, so it
// gets longer rather than distorted — a locker vent that grows from 22 to 29 cm
// still reads as a vent, where a stretched knob would read as a smear. Left
// where they are because the sheets put them there: docs/concept/views has the
// desk's feet under its corners, the sink's vents low on the side panel, and
// the booth's vent boxes standing on the roof away from its edges.
//
// The one axis this audit used to have to argue with is gone: serving_counter's
// x, where the drawer band, the pull rail and the customer shelf all widened
// with the middle. It is a steps axis now, so those parts are rebuilt per bay
// instead of stretched.
// -------------------------------------------------------------------------

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
  // A steps axis neither repeats a cell nor scales one — but its geometry is
  // built to fill `unit * v`, so on Y it is TALLER, and y is the one axis whose
  // origin is not the middle of the run but the floor under it. A three-tier
  // locker built about its own centre has to be lifted by its own half-height,
  // not by the unit's, or it sinks into the floor by the tier it just grew.
  // (§C2 — found by the locker bank, the first steps axis on y.)
  const stepLift = { x: 1, y: 1, z: 1 };

  for (const [axis, spec] of Object.entries(def.axes)) {
    if (spec.mode === 'repeat') counts[axis] = params[axis];
    else if (spec.mode === 'stretch') scale[axis] = params[axis];
    else if (spec.mode === 'steps') stepLift[axis] = params[axis];
  }

  const half = { x: hx, y: hy, z: hz };
  const out = [];
  for (let i = 0; i < counts.x; i++) {
    for (let j = 0; j < counts.y; j++) {
      for (let k = 0; k < counts.z; k++) {
        out.push({
          position: [
            (i - (counts.x - 1) / 2) * half.x * 2,
            j * half.y * 2 + half.y * scale.y * stepLift.y,
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
