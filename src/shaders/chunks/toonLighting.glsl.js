// §4.4 — lighting. This matters more than the textures.
//
// Four things carry the look, in order of how much they do:
//
//   1. HEMISPHERE AMBIENT. Fill light is not one colour: it comes cool from
//      above and warm from the floor bounce. One mix() on the world normal, and
//      every upward face picks up sky while every downward face picks up the
//      room. It is the single cheapest thing that stops a flat-shaded scene
//      looking like flat shading.
//   2. COLOURED SHADOW. The dark end of the ramp is tinted, not just darker.
//      Shadows that carry a hue read as chosen; shadows that are grey read as
//      an absence of light.
//   3. THE RAMP. Three flat steps with the terminator wrapped past halfway.
//   4. UP-LIFT. A small boost on upward faces and a small cut on downward ones,
//      independent of where the key is. This is the classic voxel trick: it
//      separates a worktop from the front of the carcass under it even when
//      both are in full light, and it is doing the job the outline pass used to.
export const toonLightingUniformsGLSL = /* glsl */ `
uniform sampler2D uToonRamp;
uniform vec3 uKeyDir;
uniform vec3 uKeyColor;
uniform float uKeyIntensity;
uniform vec3 uFillDir;
uniform vec3 uFillColor;
uniform float uFillIntensity;
uniform vec3 uRimColor;
uniform float uRimStrength;
uniform float uRimPower;
uniform vec3 uSkyColor;
uniform vec3 uGroundColor;
uniform float uAmbientStrength;
uniform vec3 uShadowColor;
uniform float uUpLift;
`;

export const toonLightingGLSL = /* glsl */ `
float rampStep(float ndl) {
  return texture2D(uToonRamp, vec2(clamp(ndl, 0.0, 1.0), 0.5)).r;
}

vec3 toonLight(vec3 albedo, vec3 n, vec3 viewDir, float upMask, out float keyTerm) {
  // wrap the terminator past the halfway point so the ramp steps read
  float key = rampStep(dot(n, normalize(uKeyDir)) * 0.62 + 0.38);
  keyTerm = key;
  float fill = clamp(dot(n, normalize(uFillDir)) * 0.5 + 0.5, 0.0, 1.0);

  // cool from the sky, warm from the floor
  vec3 ambient = mix(uGroundColor, uSkyColor, n.y * 0.5 + 0.5) * uAmbientStrength;

  vec3 light = ambient
             + uKeyColor * uKeyIntensity * key
             + uFillColor * uFillIntensity * fill;

  // tint the shaded end rather than only darkening it
  light *= mix(uShadowColor, vec3(1.0), key);

  // faces that point up catch more, undersides catch less — separates stacked
  // horizontal surfaces without needing a line between them
  light *= 1.0 + uUpLift * clamp(n.y, -1.0, 1.0);

  vec3 lit = albedo * light;

  // rim — tinted toward the key, this is what separates silhouettes.
  // Suppressed on upward faces: a floor seen at a grazing angle is all fresnel,
  // and letting it rim washes the whole frame warm.
  float fresnel = pow(1.0 - clamp(dot(n, viewDir), 0.0, 1.0), uRimPower);
  float facing = clamp(dot(n, normalize(uKeyDir)) * 0.5 + 0.5, 0.0, 1.0);
  lit += uRimColor * fresnel * facing * uRimStrength * (1.0 - upMask);

  return lit;
}
`;
