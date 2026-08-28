import { ShaderMaterial, FrontSide } from 'three';
import { vertexStageGLSL } from './chunks/vertexStage.glsl.js';

// §7.1 — the prepass. Colour target holds encoded view-space normals; depth
// comes from a DepthTexture attached to the same render target.
//
// The vertex stage is the same string the beauty pass uses, and the deform
// uniforms are the same objects, so the two passes cannot disagree about where
// the geometry is.
const vertexShader = /* glsl */ `
${vertexStageGLSL}
void main() { deformStage(); }
`;

const fragmentShader = /* glsl */ `
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

void main() {
  gl_FragColor = vec4(normalize(vNormalV) * 0.5 + 0.5, 1.0);
}
`;

/**
 * @param {{share: THREE.ShaderMaterial}} opts the beauty material this twins
 */
export function createNormalDepthMaterial({ share }) {
  const deformUniforms = share.userData.deformUniforms;
  if (!deformUniforms) throw new Error('normal-depth material needs the beauty material to twin');

  return new ShaderMaterial({
    vertexShader,
    fragmentShader,
    side: FrontSide,
    defines: share.userData.instancedParams ? { USE_INSTANCED_PARAMS: '' } : {},
    uniforms: deformUniforms, // shared by reference — this is the whole point
  });
}
