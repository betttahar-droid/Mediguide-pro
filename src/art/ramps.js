// Toon gradient maps. Built here, never inline (§4.4).
import { DataTexture, RGBAFormat, NearestFilter, NoColorSpace, UnsignedByteType } from 'three';

/**
 * N-step greyscale ramp as a Nx1 texture.
 * NearestFilter on both filters + NoColorSpace, per §4.4.
 */
export function makeToonRamp(steps = 4, { bias = 0.0, floor = 0.10 } = {}) {
  const data = new Uint8Array(steps * 4);
  for (let i = 0; i < steps; i++) {
    // Span the full range: the first step IS the floor and the last IS 1.0.
    //
    // This was `(i + 1) / steps`, which for a 3-step ramp emitted 0.41 / 0.71 /
    // 1.0 — so the darkest a face could ever be lit was 41%, and the shipped
    // look had no dark values in it at all. Measured against the reference
    // boards the build's 2nd percentile sat at 60–89/255 where theirs is 5–36.
    // A toon ramp's whole job is a small number of steps across the WHOLE
    // range; starting at 1/steps throws the darkest one away.
    const t = steps > 1 ? i / (steps - 1) : 1;
    const v = floor + (1 - floor) * Math.min(1, Math.max(0, Math.pow(t, 1.0 + bias)));
    const b = Math.round(v * 255);
    data.set([b, b, b, 255], i * 4);
  }
  const tex = new DataTexture(data, steps, 1, RGBAFormat, UnsignedByteType);
  tex.minFilter = NearestFilter;
  tex.magFilter = NearestFilter;
  tex.colorSpace = NoColorSpace;
  tex.generateMipmaps = false;
  tex.needsUpdate = true;
  return tex;
}
