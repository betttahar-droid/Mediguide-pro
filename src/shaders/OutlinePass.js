import {
  WebGLRenderTarget, DepthTexture, UnsignedIntType, NearestFilter, RGBAFormat,
  ShaderMaterial, PlaneGeometry, Mesh, OrthographicCamera, Scene, Vector2, Color,
  NoToneMapping, NormalBlending,
} from 'three';
import { createNormalDepthMaterial } from './NormalDepthMaterial.js';
import { PALETTE } from '../art/palette.js';

// §7 — outlines.
//
// The prepass renders view-space normals into a colour target with a
// DepthTexture attached. The composite runs a Roberts cross (4 samples, not
// Sobel's 8 — visually equivalent at 1px stylised ink and half the cost) over
// both, and draws the ink as a transparent overlay on top of the beauty frame.
const compositeFragment = /* glsl */ `
uniform sampler2D tNormal;
uniform sampler2D tDepth;
uniform vec2 uTexel;
uniform float uThickness;
uniform float uNormalThreshold;
uniform float uDepthThreshold;
uniform float uStrength;
uniform float uCameraNear;
uniform float uCameraFar;
uniform vec3 uInk;
varying vec2 vUv;

#include <common>
#include <packing>

// linearised, positive, in metres
float viewDistance(vec2 uv) {
  float d = texture2D(tDepth, uv).x;
  return -perspectiveDepthToViewZ(d, uCameraNear, uCameraFar);
}

void main() {
  vec2 o = uTexel * uThickness;

  vec2 uv0 = vUv + vec2(-o.x, -o.y);
  vec2 uv1 = vUv + vec2( o.x, -o.y);
  vec2 uv2 = vUv + vec2(-o.x,  o.y);
  vec2 uv3 = vUv + vec2( o.x,  o.y);

  vec3 n0 = texture2D(tNormal, uv0).rgb;
  vec3 n1 = texture2D(tNormal, uv1).rgb;
  vec3 n2 = texture2D(tNormal, uv2).rgb;
  vec3 n3 = texture2D(tNormal, uv3).rgb;
  float normalEdge = length(n0 - n3) + length(n1 - n2);

  float d0 = viewDistance(uv0);
  float d1 = viewDistance(uv1);
  float d2 = viewDistance(uv2);
  float d3 = viewDistance(uv3);
  float centre = viewDistance(vUv);

  // Normalise by view distance, or zooming out floods the frame with ink and
  // zooming in loses every interior line.
  float depthEdge = (abs(d0 - d3) + abs(d1 - d2)) / max(centre, 1.0);

  // Grazing angles: a shallow floor differences hard in depth without being an
  // edge, so scale its threshold by how side-on the surface is.
  vec3 nC = normalize(texture2D(tNormal, vUv).rgb * 2.0 - 1.0);
  float facing = clamp(abs(nC.z), 0.15, 1.0);
  float depthCut = uDepthThreshold / facing;

  float edge = max(
    smoothstep(uNormalThreshold, uNormalThreshold * 2.0, normalEdge),
    smoothstep(depthCut, depthCut * 2.0, depthEdge)
  );

  gl_FragColor = vec4(uInk, edge * uStrength);
  #include <colorspace_fragment>
}
`;

const compositeVertex = /* glsl */ `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = vec4(position.xy, 0.0, 1.0);
}
`;

/**
 * @param {{renderer: THREE.WebGLRenderer}} opts
 */
export function createOutlinePass({ renderer }) {
  const target = makeTarget(1, 1);

  const material = new ShaderMaterial({
    vertexShader: compositeVertex,
    fragmentShader: compositeFragment,
    transparent: true,
    blending: NormalBlending,
    depthTest: false,
    depthWrite: false,
    uniforms: {
      tNormal: { value: target.texture },
      tDepth: { value: target.depthTexture },
      uTexel: { value: new Vector2(1, 1) },
      uThickness: { value: 1.0 },
      uNormalThreshold: { value: 0.42 },
      uDepthThreshold: { value: 0.02 },
      uStrength: { value: 0.8 },
      uCameraNear: { value: 0.1 },
      uCameraFar: { value: 200 },
      uInk: { value: PALETTE.ink.clone() },
    },
  });

  const quadScene = new Scene();
  const quadCamera = new OrthographicCamera(-1, 1, 1, -1, 0, 1);
  quadScene.add(new Mesh(new PlaneGeometry(2, 2), material));

  const swapped = [];
  const hidden = [];
  const clearColor = new Color();

  function collect(scene) {
    swapped.length = 0;
    hidden.length = 0;
    scene.traverse((o) => {
      if (!o.isMesh || !o.material?.userData?.deformUniforms) return;
      if (o.material.transparent) {
        // ghosts are not part of the drawn scene, so they get no ink
        hidden.push(o);
        return;
      }
      let nd = o.material.userData.normalDepth;
      if (!nd) {
        nd = createNormalDepthMaterial({ share: o.material });
        o.material.userData.normalDepth = nd;
      }
      swapped.push({ mesh: o, beauty: o.material, nd });
    });
  }

  return {
    enabled: true,
    material,

    setSize(width, height, pixelRatio = 1) {
      const w = Math.max(1, Math.floor(width * pixelRatio));
      const h = Math.max(1, Math.floor(height * pixelRatio));
      target.setSize(w, h);
      material.uniforms.uTexel.value.set(1 / w, 1 / h);
    },

    /** Prepass. Call before the beauty render. */
    prepass(scene, camera) {
      collect(scene);
      const prevBackground = scene.background;
      const prevTone = renderer.toneMapping;
      renderer.getClearColor(clearColor);
      const prevAlpha = renderer.getClearAlpha();

      scene.background = null;
      renderer.toneMapping = NoToneMapping;
      renderer.setClearColor(0x000000, 1);
      for (const { mesh, nd } of swapped) mesh.material = nd;
      for (const mesh of hidden) mesh.visible = false;

      renderer.setRenderTarget(target);
      renderer.clear();
      renderer.render(scene, camera);
      renderer.setRenderTarget(null);

      for (const { mesh, beauty } of swapped) mesh.material = beauty;
      for (const mesh of hidden) mesh.visible = true;
      scene.background = prevBackground;
      renderer.toneMapping = prevTone;
      renderer.setClearColor(clearColor, prevAlpha);

      material.uniforms.uCameraNear.value = camera.near;
      material.uniforms.uCameraFar.value = camera.far;
    },

    /** Ink overlay. Call after the beauty render, straight onto the frame. */
    composite() {
      const prevAutoClear = renderer.autoClear;
      renderer.autoClear = false;
      renderer.render(quadScene, quadCamera);
      renderer.autoClear = prevAutoClear;
    },

    dispose() {
      target.dispose();
      material.dispose();
    },
  };
}

function makeTarget(w, h) {
  const depthTexture = new DepthTexture(w, h);
  depthTexture.type = UnsignedIntType;
  const rt = new WebGLRenderTarget(w, h, {
    format: RGBAFormat,
    minFilter: NearestFilter,
    magFilter: NearestFilter,
    depthBuffer: true,
    depthTexture,
  });
  return rt;
}
