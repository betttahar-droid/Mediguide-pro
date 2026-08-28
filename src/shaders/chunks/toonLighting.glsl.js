// §4.4 — toon ramp, warm key + cool fill, rim light.
// Written here rather than reused from MeshToonMaterial so it composes with
// the deform and (later) the triplanar path.
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
uniform vec3 uAmbient;
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

  vec3 lit = albedo * uAmbient;
  lit += albedo * uKeyColor * key * uKeyIntensity;
  lit += albedo * uFillColor * fill * uFillIntensity;

  // rim — tinted toward the key, this is what separates silhouettes.
  // Suppressed on upward faces: a floor seen at a grazing angle is all fresnel,
  // and letting it rim washes the whole frame warm.
  float fresnel = pow(1.0 - clamp(dot(n, viewDir), 0.0, 1.0), uRimPower);
  float facing = clamp(dot(n, normalize(uKeyDir)) * 0.5 + 0.5, 0.0, 1.0);
  lit += uRimColor * fresnel * facing * uRimStrength * (1.0 - upMask);

  return lit;
}
`;
