// The sole public entry point to the shader layer (§2).
//
// No other file in the project may import GLSL, construct a ShaderMaterial, or
// touch EffectComposer. When this is ported to TSL/NodeMaterial, this folder is
// rewritten and nothing outside it changes. This boundary is a hard requirement.
import { createAdaptiveMaterial as build } from './AdaptiveMaterial.js';
import { makeToonRamp } from '../art/ramps.js';

/** Every live material, so shared look-dev uniforms can be driven from the UI. */
const live = new Set();

/** The one shared ramp texture — swapping it re-lights the whole scene. */
let sharedRamp = makeToonRamp(4);

export function createAdaptiveMaterial(opts = {}) {
  const material = build({ ramp: sharedRamp, ...opts });
  live.add(material);
  const dispose = material.dispose.bind(material);
  material.dispose = () => {
    live.delete(material);
    dispose();
  };
  return material;
}

/** Uniforms the look-dev UI is allowed to drive across every material at once. */
export const SHARED_UNIFORMS = [
  'uKeyIntensity', 'uFillIntensity', 'uRimStrength', 'uRimPower',
  'uCavityLo', 'uCavityHi', 'uCavityStrength',
  'uEdgeLo', 'uEdgeHi', 'uEdgeStrength', 'uDustStrength',
  'uTrimFrequency', 'uTrimStrength',
];

export function setSharedUniform(name, value) {
  if (!SHARED_UNIFORMS.includes(name)) {
    throw new Error(`shaders: "${name}" is not a shared look-dev uniform`);
  }
  for (const m of live) m.uniforms[name].value = value;
}

export function setSharedVector(name, x, y, z) {
  for (const m of live) m.uniforms[name].value.set(x, y, z);
}

export function setToonRampSteps(steps) {
  const next = makeToonRamp(steps);
  sharedRamp.dispose();
  sharedRamp = next;
  for (const m of live) m.uniforms.uToonRamp.value = next;
}

/** Read a starting value for the UI without reaching into a material. */
export function defaultUniform(name) {
  const probe = build({ ramp: sharedRamp });
  const v = probe.uniforms[name]?.value;
  probe.dispose();
  return typeof v === 'number' ? v : v?.clone?.() ?? v;
}

// Phase 4 (not built): createNormalDepthMaterial(), createOutlinePass(). Both
// will consume chunks/deform.glsl.js unchanged — see README.
