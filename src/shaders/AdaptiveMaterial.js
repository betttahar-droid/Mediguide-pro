import { ShaderMaterial, Vector2, Vector3, DoubleSide, FrontSide } from 'three';
import { vertexStageGLSL } from './chunks/vertexStage.glsl.js';
import { toonLightingGLSL, toonLightingUniformsGLSL } from './chunks/toonLighting.glsl.js';
import { masksGLSL, masksUniformsGLSL } from './chunks/masks.glsl.js';
import { triplanarGLSL } from './chunks/triplanar.glsl.js';
import { PALETTE } from '../art/palette.js';
import { makeToonRamp } from '../art/ramps.js';
import { sharedTextures } from '../art/textures.js';

const vertexShader = /* glsl */ `
${vertexStageGLSL}
void main() { deformStage(); }
`;

const fragmentShader = /* glsl */ `
${toonLightingUniformsGLSL}
${masksUniformsGLSL}

uniform sampler2D uAtlasMap;   // Tier A — unique UV, hand-painted
uniform sampler2D uTrimMap;    // Tier B — one-axis trim sheet
uniform sampler2D uTilingMap;  // Tier C — triplanar
uniform sampler2D uHatchMap;

uniform vec3 uBaseColor;
uniform vec3 uMiddleColor;
uniform vec3 uAccent1;
uniform vec3 uAccent2;
uniform vec3 uAccent3;
uniform vec3 uAccent4;
uniform vec3 uAccent5;
uniform vec3 uTrimAxis;
uniform float uTrimDensity;    // trim repeats per metre along the stretch axis
uniform vec2 uAtlasScale;
uniform vec2 uAtlasOffset;
uniform float uTextureScale;   // triplanar, repeats per metre
uniform float uTriplanarSharpness;
uniform float uDetailGain;
uniform float uDetailContrast;
uniform float uHatchScale;
uniform float uHatchStrength;
uniform vec3 uInkTint;
uniform float uOpacity;
uniform vec3 uHighlight;
uniform float uHighlightAmount;

varying vec3 vMasks;
varying vec3 vObjPos;
varying vec3 vObjNormal;
varying vec3 vNormalW;
varying vec3 vViewDirW;
varying vec3 vNormalV;
varying vec2 vUv;
varying float vTrimV;
varying float vAccent;
varying float vCapMask;

// The sheets are authored as sRGB and every one is normalised to a mean of
// 132/255 by tools/authoring/make_textures.py. three decodes them to LINEAR on
// sample, and 132/255 sRGB is 0.231 linear — not 0.518. Mixing toward the
// linear value is what makes uDetailContrast flatten a surface without also
// darkening it. Getting this constant wrong in sRGB was half of a bug that
// made the whole scene read dull; see uDetailGain below for the other half.
const float SHEET_MEAN = 0.231;

// tone-mapping and colour-space helpers are already in the fragment prefix
#include <common>

${triplanarGLSL}
${toonLightingGLSL}
${masksGLSL}

void main() {
  // §4.2 — a narrow smoothstep on the cap mask, so the tier change reads as a
  // painted seam rather than a texture pop.
  float capBlend = smoothstep(0.35, 0.65, vCapMask);

  vec2 hatchUv;
  vec3 detail;
  vec3 tint;

#ifdef TIER_C
  vec3 tpPos = vObjPos * uTextureScale;
  detail = triplanarSample(uTilingMap, tpPos, vObjNormal, uTriplanarSharpness);
  hatchUv = triplanarUv(tpPos, vObjNormal) * uHatchScale;
  tint = uBaseColor;
#else
  // Tier B — U tiles along the stretch axis, V selects the strip. Both come
  // from the deformed position / a baked attribute, so stretching the middle
  // reveals more trim instead of smearing it.
  float u = dot(vObjPos, normalize(uTrimAxis)) * uTrimDensity;
  vec2 trimUv = vec2(u, vTrimV);
  vec3 trimDetail = texture2D(uTrimMap, trimUv).rgb;

  // Tier A — the mesh's own UVs into this module's atlas cell. Caps translate
  // rather than scale under the 9-slice, so this detail is never distorted.
  vec2 atlasUv = vUv * uAtlasScale + uAtlasOffset;
  vec3 uvDetail = texture2D(uAtlasMap, atlasUv).rgb;

  detail = mix(trimDetail, uvDetail, capBlend);
  // The hatch needs two axes that both vary across the surface; the trim's V is
  // a strip selector, not a surface coordinate, so project the object position
  // instead. Still surface-locked and still post-deform, so it never swims.
  hatchUv = triplanarUv(vObjPos, vObjNormal) * uHatchScale;
  tint = mix(uMiddleColor, uBaseColor, capBlend);
#endif

  // A part can opt into one of five accent colours from the module's palette
  // entry, so one material still paints a whole object: a light frame, the body
  // panels, a dark plinth or fitting, one saturated accent, glass where there
  // is glass — and a fifth NEUTRAL, which several sheets need for a cool grey
  // that is neither the frame nor a shadow (a bench carcass behind warm drawer
  // fronts, a pressed steel sink well). Note the test is on the TOP slot first:
  // an out-of-range index would otherwise land here silently, which is why
  // validateRegistry rejects one by number.
  if (vAccent > 4.5) tint = uAccent5;
  else if (vAccent > 3.5) tint = uAccent4;
  else if (vAccent > 2.5) tint = uAccent3;
  else if (vAccent > 1.5) tint = uAccent2;
  else if (vAccent > 0.5) tint = uAccent1;

  // the detail sheets are luminance around mid-grey; the palette supplies hue
  detail = mix(vec3(SHEET_MEAN), detail, uDetailContrast);
  vec3 albedo = tint * detail * uDetailGain;

  albedo = applyMasks(albedo, vMasks);
  albedo = mix(albedo, uHighlight, uHighlightAmount);

  vec3 n = normalize(vNormalW);
  float keyTerm;
  vec3 lit = toonLight(albedo, n, normalize(vViewDirW), vMasks.b, keyTerm);

  // §4.5 — cross-hatching in the beauty pass, driven by the lighting term and
  // locked to the surface: the same coordinates as the albedo for this region.
  float shade = clamp(1.0 - keyTerm, 0.0, 1.0) * 3.0;
  vec3 hatch = texture2D(uHatchMap, hatchUv).rgb;
  float h = shade < 1.0
    ? mix(1.0, hatch.r, shade)
    : (shade < 2.0 ? mix(hatch.r, hatch.g, shade - 1.0) : mix(hatch.g, hatch.b, shade - 2.0));
  lit = mix(lit, lit * uInkTint, (1.0 - h) * uHatchStrength);

  gl_FragColor = vec4(lit, uOpacity);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

/**
 * The deform uniforms are shared by reference with the normal-depth twin, so
 * the two passes cannot drift apart (§5.4).
 */
export function makeDeformUniforms({
  sourceHalfExtents = new Vector3(0.5, 0.5, 0.5),
  margins = new Vector3(0.06, 0.06, 0.06),
} = {}) {
  return {
    uSourceHalfExtents: { value: sourceHalfExtents.clone() },
    uMargins: { value: margins.clone() },
    uTargetScale: { value: new Vector3(1, 1, 1) },
  };
}

/**
 * One material for the whole catalogue: 9-slice deform, all three texturing
 * tiers, toon lighting, vertex-baked masks and surface-locked hatching.
 */
export function createAdaptiveMaterial(opts = {}) {
  const {
    baseColor = PALETTE.oak,
    middleColor = PALETTE.oakDark,
    accent1 = null,
    accent2 = null,
    accent3 = null,
    accent4 = null,
    accent5 = null,
    trimAxis = new Vector3(1, 0, 0),
    trimDensity = 0.45,
    atlasCell = [0, 0], // 2×2 atlas
    tier = 'AB', // 'AB' = atlas caps + trim middle, 'C' = triplanar
    textureScale = 0.5,
    transparent = false,
    opacity = 1,
    instancedParams = false,
    ramp = makeToonRamp(3),
    deformUniforms = makeDeformUniforms(opts),
  } = opts;

  const tex = sharedTextures();

  const material = new ShaderMaterial({
    vertexShader,
    fragmentShader,
    transparent,
    side: transparent ? DoubleSide : FrontSide,
    depthWrite: !transparent,
    defines: {
      ...(tier === 'C' ? { TIER_C: '' } : {}),
      ...(instancedParams ? { USE_INSTANCED_PARAMS: '' } : {}),
    },
    uniforms: {
      ...deformUniforms,
      // texturing
      uAtlasMap: { value: tex.atlas },
      uTrimMap: { value: tex.trim },
      uTilingMap: { value: tex.tiling },
      uHatchMap: { value: tex.hatch },
      uBaseColor: { value: baseColor.clone() },
      uMiddleColor: { value: middleColor.clone() },
      uAccent1: { value: (accent1 ?? baseColor).clone() },
      uAccent2: { value: (accent2 ?? middleColor).clone() },
      uAccent3: { value: (accent3 ?? accent1 ?? baseColor).clone() },
      uAccent4: { value: (accent4 ?? accent2 ?? middleColor).clone() },
      uAccent5: { value: (accent5 ?? accent1 ?? baseColor).clone() },
      uTrimAxis: { value: trimAxis.clone() },
      uTrimDensity: { value: trimDensity },
      uAtlasScale: { value: new Vector2(0.5, 0.5) },
      uAtlasOffset: { value: new Vector2(atlasCell[0] * 0.5, atlasCell[1] * 0.5) },
      uTextureScale: { value: textureScale },
      uTriplanarSharpness: { value: 8.0 },
      // A mid-grey texel must come out of the multiply NEUTRAL, and mid grey
      // is 0.231 in the linear space the shader works in, so the gain that
      // makes `tint * detail * gain == tint` is 1/0.231 = 4.33. It was 2.0 —
      // calibrated as though the sheet mean were 0.5 — which multiplied EVERY
      // surface in the scene by 0.46. That single constant was the ceiling on
      // the whole look: measured against the reference boards the build could
      // not get a pixel brighter than 189/255 where they reach 249-255.
      uDetailGain: { value: 4.33 },
      uDetailContrast: { value: 1.0 },
      uOpacity: { value: opacity },
      uHighlight: { value: PALETTE.mint.clone() },
      uHighlightAmount: { value: 0 },
      // lighting
      uToonRamp: { value: ramp },
      uKeyDir: { value: new Vector3(0.6, 0.8, 0.45) },
      uKeyColor: { value: PALETTE.keyWarm.clone() },
      uKeyIntensity: { value: 0.72 },
      uFillDir: { value: new Vector3(-0.7, 0.35, -0.5) },
      uFillColor: { value: PALETTE.fillCool.clone() },
      uFillIntensity: { value: 0.14 },
      uRimColor: { value: PALETTE.rim.clone() },
      uRimStrength: { value: 0.0 },
      uRimPower: { value: 3.2 },
      uSkyColor: { value: PALETTE.sky.clone() },
      uGroundColor: { value: PALETTE.ground.clone() },
      uAmbientStrength: { value: 0.16 },
      uShadowColor: { value: PALETTE.shadowCool.clone() },
      uUpLift: { value: 0.22 },
      // hatching
      uHatchScale: { value: 4.5 },
      uHatchStrength: { value: 0.0 },
      uInkTint: { value: PALETTE.ink.clone() },
      // mask ramps — all six tuned by eye in lil-gui (§4.3)
      uCavityLo: { value: 0.55 },
      uCavityHi: { value: 0.92 },
      uCavityStrength: { value: 0.22 },
      uEdgeLo: { value: 0.78 },
      uEdgeHi: { value: 0.99 },
      uEdgeStrength: { value: 0.14 },
      uDustStrength: { value: 0.0 },
      uShadowTint: { value: PALETTE.shadowTint.clone() },
      uEdgeLightTint: { value: PALETTE.edgeLightTint.clone() },
      uDustTint: { value: PALETTE.dustTint.clone() },
    },
  });

  material.userData.deformUniforms = deformUniforms;
  material.userData.instancedParams = instancedParams;
  return material;
}
