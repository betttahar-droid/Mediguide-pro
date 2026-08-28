// §6 — Tier C only: floor, wall and ceiling panels, and any UV-less mesh.
//
// Object space, not world space: a world-space projection makes a moving object
// slide through a stationary texture.
// Post-deformation position, not the original: sampling the deformed position
// keeps texel density constant, so stretching reveals more texture instead of
// smearing it. That is what "scale-invariant" means here.
export const triplanarGLSL = /* glsl */ `
vec3 triplanarSample(sampler2D map, vec3 tpPos, vec3 tpNormal, float sharpness) {
  vec2 uvX = tpPos.zy;
  vec2 uvY = tpPos.xz;
  vec2 uvZ = tpPos.xy;

  vec3 axisSign = sign(tpNormal);
  uvX.x *= axisSign.x;
  uvY.x *= axisSign.y;
  uvZ.x *= -axisSign.z;

  vec3 w = pow(abs(tpNormal), vec3(sharpness));
  w /= max(w.x + w.y + w.z, 1e-5);

  return texture2D(map, uvX).rgb * w.x
       + texture2D(map, uvY).rgb * w.y
       + texture2D(map, uvZ).rgb * w.z;
}

// Hatching and any other co-located sample needs one stable 2D coordinate
// rather than three; take the dominant axis' projection.
vec2 triplanarUv(vec3 tpPos, vec3 tpNormal) {
  vec3 a = abs(tpNormal);
  if (a.y >= a.x && a.y >= a.z) return tpPos.xz;
  if (a.x >= a.z) return tpPos.zy;
  return tpPos.xy;
}
`;

// Normal maps under triplanar need UDN blending (mesh tangents are invalid) —
// see bgolus/Normal-Mapping-for-a-Triplanar-Shader. Not implemented: this
// project authors albedo only and puts AO in vertex colours (§6.3), so there is
// no normal map to blend yet.
