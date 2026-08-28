// §5 — nine-slice deformation. ONE shared chunk.
//
// Injected into both AdaptiveMaterial and (later) NormalDepthMaterial. Never
// duplicate this code: if the beauty pass and the prepass compute different
// geometry, outlines trace a mesh the player cannot see.
export const deformUniformsGLSL = /* glsl */ `
uniform vec3 uSourceHalfExtents; // h, per axis, of the undeformed mesh
uniform vec3 uMargins;           // m, cap thickness to preserve
uniform vec3 uTargetScale;       // H = uSourceHalfExtents * uTargetScale
`;

export const deformGLSL = /* glsl */ `
// returns deformed coordinate; writes the applied scale factor to outScale
float slice1D(float p, float h, float m, float H, out float outScale, out float outCapMask) {
  float inner = h - m;
  float target = max(H - m, 0.0);
  if (abs(p) <= inner) {
    outScale = (inner > 1e-5) ? target / inner : 1.0;
    outCapMask = 0.0;
    return (inner > 1e-5) ? p * outScale : 0.0;
  }
  outScale = 1.0;
  outCapMask = 1.0;
  return sign(p) * (target + (abs(p) - inner));
}

// Deforms a position, writing the per-axis applied scale and a 0..1 cap mask.
vec3 nineSlice(vec3 p, vec3 h, vec3 m, vec3 H, out vec3 appliedScale, out float capMask) {
  vec3 caps;
  vec3 outPos;
  outPos.x = slice1D(p.x, h.x, m.x, H.x, appliedScale.x, caps.x);
  outPos.y = slice1D(p.y, h.y, m.y, H.y, appliedScale.y, caps.y);
  outPos.z = slice1D(p.z, h.z, m.z, H.z, appliedScale.z, caps.z);
  // a vertex is "cap" if it is in a cap band on any stretched axis
  capMask = max(max(caps.x, caps.y), caps.z);
  return outPos;
}

// §5.2 guard 3 — the Jacobian is diagonal, so the inverse-transpose is a divide.
vec3 correctNormal(vec3 n, vec3 appliedScale) {
  return normalize(n / max(appliedScale, vec3(1e-5)));
}
`;
