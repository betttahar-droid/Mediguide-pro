import { ShaderMaterial, Vector3, Color, DoubleSide, FrontSide } from 'three';
import { deformGLSL, deformUniformsGLSL } from './chunks/deform.glsl.js';
import { toonLightingGLSL, toonLightingUniformsGLSL } from './chunks/toonLighting.glsl.js';
import { masksGLSL, masksUniformsGLSL } from './chunks/masks.glsl.js';
import { PALETTE } from '../art/palette.js';
import { makeToonRamp } from '../art/ramps.js';

const vertexShader = /* glsl */ `
attribute vec3 aMasks;

${deformUniformsGLSL}
${deformGLSL}

varying vec3 vMasks;
varying vec3 vNormalW;
varying vec3 vViewDirW;
varying vec3 vObjPos;
varying float vCapMask;

void main() {
  vec3 appliedScale;
  float capMask;
  vec3 H = uSourceHalfExtents * uTargetScale;
  vec3 deformed = nineSlice(position, uSourceHalfExtents, uMargins, H, appliedScale, capMask);
  vec3 n = correctNormal(normal, appliedScale);

  vec4 worldPos = modelMatrix * vec4(deformed, 1.0);

  vMasks = aMasks;
  vCapMask = capMask;
  vObjPos = deformed;
  vNormalW = normalize(mat3(modelMatrix) * n);
  vViewDirW = normalize(cameraPosition - worldPos.xyz);

  gl_Position = projectionMatrix * viewMatrix * worldPos;
}
`;

const fragmentShader = /* glsl */ `
${toonLightingUniformsGLSL}
${masksUniformsGLSL}

uniform vec3 uBaseColor;      // Tier A stand-in: flat painted albedo in the caps
uniform vec3 uMiddleColor;    // Tier B stand-in: the trim strip's surface colour
uniform vec3 uTrimAxis;       // which object axis the trim tiles along
uniform float uTrimFrequency; // painted panel seams per metre
uniform float uTrimStrength;
uniform float uOpacity;
uniform vec3 uHighlight;
uniform float uHighlightAmount;

varying vec3 vMasks;
varying vec3 vNormalW;
varying vec3 vViewDirW;
varying vec3 vObjPos;
varying float vCapMask;

// tone-mapping and colour-space helpers are already in the fragment prefix
#include <common>

${toonLightingGLSL}
${masksGLSL}

void main() {
  // Tier B stand-in — one-axis "trim": painted seams running along the stretch
  // axis only, so they survive arbitrary stretching (§4.1).
  float along = dot(vObjPos, normalize(uTrimAxis));
  float seam = abs(fract(along * uTrimFrequency) - 0.5) * 2.0;
  seam = smoothstep(0.78, 0.98, seam);
  vec3 trimColor = mix(uMiddleColor, uMiddleColor * 0.82, seam * uTrimStrength);

  // §4.2 — narrow smoothstep on the cap mask so the tier change reads as a
  // painted seam rather than a texture pop.
  float capBlend = smoothstep(0.35, 0.65, vCapMask);
  vec3 albedo = mix(trimColor, uBaseColor, capBlend);

  albedo = applyMasks(albedo, vMasks);
  albedo = mix(albedo, uHighlight, uHighlightAmount);

  vec3 n = normalize(vNormalW);
  vec3 lit = toonLight(albedo, n, normalize(vViewDirW), vMasks.b);

  gl_FragColor = vec4(lit, uOpacity);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

/**
 * The single material for the whole catalogue: 9-slice deform + toon lighting +
 * vertex-baked masks, with the Tier A / Tier B region blend driven by capMask.
 * Tier C (triplanar) is not built yet — see README "Not built".
 */
export function createAdaptiveMaterial(opts = {}) {
  const {
    baseColor = PALETTE.oak,
    middleColor = PALETTE.oakDark,
    sourceHalfExtents = new Vector3(0.5, 0.5, 0.5),
    margins = new Vector3(0.06, 0.06, 0.06),
    trimAxis = new Vector3(1, 0, 0),
    transparent = false,
    opacity = 1,
    ramp = makeToonRamp(4),
  } = opts;

  const material = new ShaderMaterial({
    vertexShader,
    fragmentShader,
    transparent,
    side: transparent ? DoubleSide : FrontSide,
    depthWrite: !transparent,
    uniforms: {
      // deform
      uSourceHalfExtents: { value: sourceHalfExtents.clone() },
      uMargins: { value: margins.clone() },
      uTargetScale: { value: new Vector3(1, 1, 1) },
      // albedo
      uBaseColor: { value: baseColor.clone() },
      uMiddleColor: { value: middleColor.clone() },
      uTrimAxis: { value: trimAxis.clone() },
      uTrimFrequency: { value: 2.0 },
      uTrimStrength: { value: 0.9 },
      uOpacity: { value: opacity },
      uHighlight: { value: PALETTE.mint.clone() },
      uHighlightAmount: { value: 0 },
      // lighting
      uToonRamp: { value: ramp },
      uKeyDir: { value: new Vector3(0.6, 0.8, 0.45) },
      uKeyColor: { value: PALETTE.keyWarm.clone() },
      uKeyIntensity: { value: 0.68 },
      uFillDir: { value: new Vector3(-0.7, 0.35, -0.5) },
      uFillColor: { value: PALETTE.fillCool.clone() },
      uFillIntensity: { value: 0.28 },
      uRimColor: { value: PALETTE.rim.clone() },
      uRimStrength: { value: 0.35 },
      uRimPower: { value: 3.0 },
      uAmbient: { value: new Color(0.26, 0.25, 0.29) },
      // mask ramps — all six tuned by eye in lil-gui (§4.3)
      uCavityLo: { value: 0.12 },
      uCavityHi: { value: 0.62 },
      uCavityStrength: { value: 0.75 },
      uEdgeLo: { value: 0.55 },
      uEdgeHi: { value: 0.95 },
      uEdgeStrength: { value: 0.45 },
      uDustStrength: { value: 0.05 },
      uShadowTint: { value: PALETTE.shadowTint.clone() },
      uEdgeLightTint: { value: PALETTE.edgeLightTint.clone() },
      uDustTint: { value: PALETTE.dustTint.clone() },
    },
  });

  return material;
}
