import * as THREE from 'three';

/** CPU twin of the shader mapping, used by validation and authoring tools. */
export function nineSliceAxisPixel(targetPixel, sourcePixels, borderPixels, targetPixels) {
  const source = Math.max(1, Math.round(sourcePixels));
  const border = Math.max(0, Math.min(Math.round(borderPixels), Math.floor(source / 2)));
  const target = Math.max(border * 2 + 1, Math.round(targetPixels));
  const pixel = Math.max(0, Math.min(target - 1, Math.floor(targetPixel)));
  if (pixel < border) return pixel;
  if (pixel >= target - border) return source - (target - pixel);
  const center = Math.max(1, source - border * 2);
  return border + ((pixel - border) % center);
}

export function createFridgeNineSliceMaterial(texture, {
  atlasRectPx,
  atlasSizePx = [256, 256],
  sourceSizePx,
  protectedBorderPx = [4, 4],
  targetSizePx = sourceSizePx,
  transparent = false,
} = {}) {
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.magFilter = THREE.NearestFilter;
  texture.minFilter = THREE.NearestFilter;
  texture.generateMipmaps = false;
  texture.wrapS = texture.wrapT = THREE.ClampToEdgeWrapping;

  const material = new THREE.ShaderMaterial({
    transparent,
    depthWrite: !transparent,
    uniforms: {
      uAtlas: { value: texture },
      uAtlasRectPx: { value: new THREE.Vector4(...atlasRectPx) },
      uAtlasSizePx: { value: new THREE.Vector2(...atlasSizePx) },
      uSourceSizePx: { value: new THREE.Vector2(...sourceSizePx) },
      uProtectedBorderPx: { value: new THREE.Vector2(...protectedBorderPx) },
      uTargetSizePx: { value: new THREE.Vector2(...targetSizePx) },
      uOpacity: { value: transparent ? 0.42 : 1.0 },
    },
    vertexShader: /* glsl */`
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */`
      uniform sampler2D uAtlas;
      uniform vec4 uAtlasRectPx;
      uniform vec2 uAtlasSizePx;
      uniform vec2 uSourceSizePx;
      uniform vec2 uProtectedBorderPx;
      uniform vec2 uTargetSizePx;
      uniform float uOpacity;
      varying vec2 vUv;

      float nineSliceAxis(float normalizedCoord, float sourcePx,
                          float borderPx, float requestedTargetPx) {
        float targetSizePx = max(2.0 * borderPx + 1.0, floor(requestedTargetPx + 0.5));
        float targetPx = min(targetSizePx - 1.0, floor(normalizedCoord * targetSizePx));
        float centerSourcePx = max(1.0, floor(sourcePx - 2.0 * borderPx + 0.5));

        // Near edge: retain a literal one-pixel-to-one-pixel mapping.
        if (targetPx < borderPx) return targetPx;
        // Far edge: slide outward, but do not scale or mirror its pixels.
        if (targetPx >= targetSizePx - borderPx) {
          return sourcePx - (targetSizePx - targetPx);
        }
        // Center: allocate additional pixels by repeating the source center.
        // Modulo is deliberate: center texture never stretches like rubber.
        return borderPx + mod(targetPx - borderPx, centerSourcePx);
      }

      vec2 nineSliceUv(vec2 rawUv) {
        vec2 sourcePx = vec2(
          nineSliceAxis(rawUv.x, uSourceSizePx.x, uProtectedBorderPx.x, uTargetSizePx.x),
          nineSliceAxis(rawUv.y, uSourceSizePx.y, uProtectedBorderPx.y, uTargetSizePx.y)
        );
        // Address texel centres, never boundaries between an island and gutter.
        vec2 regionUv = (sourcePx + 0.5) / uSourceSizePx;
        // Atlas rectangles use a top-left pixel origin; WebGL UVs use bottom-left.
        vec2 atlasPx = vec2(
          uAtlasRectPx.x + regionUv.x * uAtlasRectPx.z,
          uAtlasRectPx.y + (1.0 - regionUv.y) * uAtlasRectPx.w
        );
        return vec2(atlasPx.x / uAtlasSizePx.x, 1.0 - atlasPx.y / uAtlasSizePx.y);
      }

      void main() {
        vec4 pixel = texture2D(uAtlas, nineSliceUv(vUv));
        gl_FragColor = vec4(pixel.rgb, pixel.a * uOpacity);
      }
    `,
  });
  material.userData.adaptiveNineSlice = true;
  material.userData.sourceSizePx = [...sourceSizePx];
  return material;
}

export function setFridgeNineSliceScale(material, x = 1, y = 1, z = 1) {
  const source = material.uniforms.uSourceSizePx.value;
  setFridgeNineSliceTargetSize(material, source.x * x, source.y * y);
}

export function setFridgeNineSliceTargetSize(material, widthPx, heightPx) {
  material.uniforms.uTargetSizePx.value.set(Math.round(widthPx), Math.round(heightPx));
}
