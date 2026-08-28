// Toon gradient maps. Built here, never inline (§4.4).
import { DataTexture, RGBAFormat, NearestFilter, NoColorSpace, UnsignedByteType } from 'three';

/**
 * N-step greyscale ramp as a Nx1 texture.
 * NearestFilter on both filters + NoColorSpace, per §4.4.
 */
export function makeToonRamp(steps = 4, { bias = 0.0, floor = 0.12 } = {}) {
  const data = new Uint8Array(steps * 4);
  for (let i = 0; i < steps; i++) {
    // ease the ramp so the terminator sits a little past halfway — reads as painted
    const t = (i + 1) / steps;
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
