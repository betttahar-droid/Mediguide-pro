// §4.3 — applying the three vertex-baked geometric masks.
// Six ramp parameters, all exposed in lil-gui. They are tuned by eye.
export const masksUniformsGLSL = /* glsl */ `
uniform float uCavityLo;
uniform float uCavityHi;
uniform float uCavityStrength;
uniform float uEdgeLo;
uniform float uEdgeHi;
uniform float uEdgeStrength;
uniform float uDustStrength;
uniform vec3 uShadowTint;
uniform vec3 uEdgeLightTint;
uniform vec3 uDustTint;
`;

export const masksGLSL = /* glsl */ `
vec3 applyMasks(vec3 albedo, vec3 masks) {
  float cavity = smoothstep(uCavityLo, uCavityHi, masks.r);
  float edge   = smoothstep(uEdgeLo, uEdgeHi, masks.g);
  float up     = masks.b;

  albedo = mix(albedo, uShadowTint, cavity * uCavityStrength);
  albedo = mix(albedo, uEdgeLightTint, edge * uEdgeStrength);
  albedo += uDustTint * up * uDustStrength;
  return albedo;
}
`;
