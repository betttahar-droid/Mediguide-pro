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

// The masks are PER-VERTEX quantities, so anything that maps them continuously
// to a colour paints a gradient across the interior of a face — and the whole
// point of the reference art is that a face is one flat value. So each mask is
// posterised to exactly two levels: off, or one flat painted step. The lo/hi
// pair no longer ramps, it names the threshold (their midpoint); the ±0.008
// window is only there so the border between the two levels is antialiased
// rather than stair-stepped. Read the result as a painted region with a clean
// edge crossing the face, which is exactly how the concept sheets draw AO.
export const masksGLSL = /* glsl */ `
// A tint's HUE only, as a multiplier near 1.0. Normalising by the tint's own
// luminance is the whole trick: the palette's shading tints are dark colours,
// and multiplying by one directly would turn a 15% AO step into a 90% one. This
// way the step's SIZE is set by its strength and the tint only bends its hue,
// so a pastel surface stays pastel.
vec3 hueOf(vec3 tint, float hueMix) {
  float lum = max(1e-4, dot(tint, vec3(0.2126, 0.7152, 0.0722)));
  return mix(vec3(1.0), tint / lum, hueMix);
}

vec3 applyMasks(vec3 albedo, vec3 masks) {
  // two levels, not a ramp
  float cavityEdge = 0.5 * (uCavityLo + uCavityHi);
  float edgeEdge   = 0.5 * (uEdgeLo + uEdgeHi);
  float cavity = smoothstep(cavityEdge - 0.008, cavityEdge + 0.008, masks.r);
  float edge   = smoothstep(edgeEdge - 0.008, edgeEdge + 0.008, masks.g);
  float up     = masks.b;

  // AO: one flat step of hue-preserved, faintly cool darkening.
  vec3 aoMul   = hueOf(uShadowTint, 0.18) * (1.0 - uCavityStrength);
  // convex edges: one flat step of warm lift.
  vec3 edgeMul = hueOf(uEdgeLightTint, 0.18) * (1.0 + uEdgeStrength);
  albedo *= mix(vec3(1.0), aoMul, cavity);
  albedo *= mix(vec3(1.0), edgeMul, edge);
  albedo += uDustTint * up * uDustStrength;
  return albedo;
}
`;
