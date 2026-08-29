import { ShaderMaterial, Vector2, Vector3, Color, DoubleSide, FrontSide } from 'three';
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
uniform vec3 uTrimAxis;
uniform float uTrimDensity;    // trim repeats per metre along the stretch axis
uniform vec2 uAtlasScale;
uniform vec2 uAtlasOffset;
uniform float uTextureScale;   // triplanar, repeats per metre
uniform float uTriplanarSharpness;
uniform float uDetailGain;
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

  // a part can opt into one of two accent colours from the module's palette
  // entry, so one material still paints a two-tone desk
  if (vAccent > 1.5) tint = uAccent2;
  else if (vAccent > 0.5) tint = uAccent1;

  // the detail sheets are luminance around mid-grey; the palette supplies hue
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
      uTrimAxis: { value: trimAxis.clone() },
      uTrimDensity: { value: trimDensity },
      uAtlasScale: { value: new Vector2(0.5, 0.5) },
      uAtlasOffset: { value: new Vector2(atlasCell[0] * 0.5, atlasCell[1] * 0.5) },
      uTextureScale: { value: textureScale },
      uTriplanarSharpness: { value: 8.0 },
      uDetailGain: { value: 2.0 },
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
      uRimStrength: { value: 0.16 },
      uRimPower: { value: 3.0 },
      uAmbient: { value: new Color(0.26, 0.25, 0.29) },
      // hatching
      uHatchScale: { value: 4.5 },
      uHatchStrength: { value: 0.0 },
      uInkTint: { value: PALETTE.ink.clone() },
      // mask ramps — all six tuned by eye in lil-gui (§4.3)
      uCavityLo: { value: 0.12 },
      uCavityHi: { value: 0.62 },
      uCavityStrength: { value: 0.34 },
      uEdgeLo: { value: 0.55 },
      uEdgeHi: { value: 0.95 },
      uEdgeStrength: { value: 0.26 },
      uDustStrength: { value: 0.03 },
      uShadowTint: { value: PALETTE.shadowTint.clone() },
      uEdgeLightTint: { value: PALETTE.edgeLightTint.clone() },
      uDustTint: { value: PALETTE.dustTint.clone() },
    },
  });

  material.userData.deformUniforms = deformUniforms;
  material.userData.instancedParams = instancedParams;
  return material;
}
