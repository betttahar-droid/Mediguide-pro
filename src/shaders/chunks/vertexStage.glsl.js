// The one vertex stage. Both the beauty pass and the normal-depth prepass are
// built from this string, so they cannot compute different geometry — the
// failure the brief calls the most likely hard-to-diagnose bug in the project
// (§5.4). It presents as "the outline shader is broken" when it is not.
import { deformGLSL, deformUniformsGLSL } from './deform.glsl.js';

export const vertexStageGLSL = /* glsl */ `
attribute vec3 aMasks;
attribute float aTrimV;
attribute float aAccent;

${deformUniformsGLSL}
${deformGLSL}

#ifdef USE_INSTANCED_PARAMS
  attribute vec3 aTargetScale;
  attribute vec3 aMargins;
#endif

varying vec3 vMasks;
varying vec3 vObjPos;      // deformed, module-local — triplanar and trim read this
varying vec3 vObjNormal;   // deformed-corrected, module-local
varying vec3 vNormalW;
varying vec3 vViewDirW;
varying vec3 vNormalV;     // view space, for the prepass
varying vec2 vUv;
varying float vTrimV;
varying float vAccent;
varying float vCapMask;

void deformStage() {
  #ifdef USE_INSTANCED_PARAMS
    vec3 targetScale = aTargetScale;
    vec3 margins = aMargins;
  #else
    vec3 targetScale = uTargetScale;
    vec3 margins = uMargins;
  #endif

  vec3 appliedScale;
  float capMask;
  vec3 H = uSourceHalfExtents * targetScale;
  vec3 deformed = nineSlice(position, uSourceHalfExtents, margins, H, appliedScale, capMask);
  vec3 n = correctNormal(normal, appliedScale);

  vObjPos = deformed;
  vObjNormal = n;
  vMasks = aMasks;
  vTrimV = aTrimV;
  vAccent = aAccent;
  vUv = uv;
  vCapMask = capMask;

  vec4 localPos = vec4(deformed, 1.0);
  #ifdef USE_INSTANCING
    localPos = instanceMatrix * localPos;
    n = normalize(mat3(instanceMatrix) * n);
  #endif

  vec4 worldPos = modelMatrix * localPos;
  vNormalW = normalize(mat3(modelMatrix) * n);
  vNormalV = normalize(mat3(viewMatrix) * vNormalW);
  vViewDirW = normalize(cameraPosition - worldPos.xyz);

  gl_Position = projectionMatrix * viewMatrix * worldPos;
}
`;
