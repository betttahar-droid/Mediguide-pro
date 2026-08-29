// The sole public entry point to the shader layer (§2).
//
// No other file in the project may import GLSL, construct a ShaderMaterial, or
// touch a render target. When this is ported to TSL/NodeMaterial, this folder is
// rewritten and nothing outside it changes. This boundary is a hard requirement.
import { createAdaptiveMaterial as build, makeDeformUniforms } from './AdaptiveMaterial.js';
import { createNormalDepthMaterial as buildNormalDepth } from './NormalDepthMaterial.js';
import { createOutlinePass as buildOutline } from './OutlinePass.js';
import { makeToonRamp } from '../art/ramps.js';

/** Every live material, so shared look-dev uniforms can be driven from the UI. */
const live = new Set();

/** The one shared ramp texture — swapping it re-lights the whole scene. */
let sharedRamp = makeToonRamp(3);

export function createAdaptiveMaterial(opts = {}) {
  const material = build({ ramp: sharedRamp, ...opts });
  live.add(material);
  const dispose = material.dispose.bind(material);
  material.dispose = () => {
    live.delete(material);
    material.userData.normalDepth?.dispose();
    dispose();
  };
  return material;
}

export const createNormalDepthMaterial = buildNormalDepth;
export const createOutlinePass = buildOutline;
export { makeDeformUniforms };

/** Uniforms the look-dev UI is allowed to drive across every material at once. */
export const SHARED_UNIFORMS = [
  'uKeyIntensity', 'uFillIntensity', 'uRimStrength', 'uRimPower',
  'uCavityLo', 'uCavityHi', 'uCavityStrength',
  'uEdgeLo', 'uEdgeHi', 'uEdgeStrength', 'uDustStrength',
  'uTrimDensity', 'uDetailGain', 'uTextureScale', 'uTriplanarSharpness',
  'uHatchScale', 'uHatchStrength',
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
