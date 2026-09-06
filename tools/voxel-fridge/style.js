import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';

export const STYLE = {
  texel: 1 / 32,
  bevel: 1,
  objLo: 0,
  objHi: 96,
};

export const MATS = {
  cream: { base: '#d9c9a8', lit: '#fff4cc', shade: '#a89a81', surface: 'plate' },
  steel: { base: '#617a80', lit: '#76949c', shade: '#4a5d62', surface: 'plateSeam' },
  teal: { base: '#0d403b', lit: '#104e48', shade: '#0a312d', surface: 'recess' },
  glass: { base: '#0b302d', lit: '#0d3a37', shade: '#082522' },
  shelf: { base: '#93aaad', lit: '#d8ddd1', shade: '#697f83' },
  plum: { base: '#463750', lit: '#6a5074', shade: '#2b1f35' },
  ochre: { base: '#c38b4d', lit: '#ebb160', shade: '#85522a', surface: 'vent' },
  dark: { base: '#142b2a', lit: '#1b3937', shade: '#0a1d1c' },
  lampBlue: { base: '#60aeca', lit: '#60aeca', shade: '#60aeca' },
  lampGreen: { base: '#67a66b', lit: '#67a66b', shade: '#67a66b' },
  lampRed: { base: '#d56354', lit: '#d56354', shade: '#d56354' },
  lampCyan: { base: '#7ecbd1', lit: '#7ecbd1', shade: '#7ecbd1' },
  lampWhite: { base: '#e4dfcf', lit: '#e4dfcf', shade: '#e4dfcf' },
  // Fixed indicator colours measured from inspo 3.gif and inspo 1.jpg.
  lampAmber: { base: '#d7995f', lit: '#d7995f', shade: '#d7995f' },
  lampRust: { base: '#9d6d59', lit: '#9d6d59', shade: '#9d6d59' },
  // Paintover samples are material variation, not wallpaper.  Strength is kept
  // deliberately low on broad faces; semantic edge/seam masks carry the strong
  // marks seen in the authority images.
  freezerEnamel: { base: '#c2cac5', lit: '#dce3dc', shade: '#8e9b98', surface: 'plate', micro: 0, microStrength: .35 },
  freezerSide: { base: '#818a92', lit: '#9ba7ad', shade: '#606a72', surface: 'plateSeam', micro: 1, microStrength: .08 },
  freezerShelf: { base: '#aab7b7', lit: '#d4ddda', shade: '#738387', micro: 3, microStrength: .28 },
  freezerCavity: { base: '#29383d', lit: '#35484e', shade: '#18262b' },
  medicalBlue: { base: '#315b7d', lit: '#4f80a2', shade: '#203d57' },
  medicinePaper: { base: '#d9ddd5', lit: '#f0f0df', shade: '#a9afa8' },
  medicineTan: { base: '#b58a5e', lit: '#d5ad7a', shade: '#795d43' },
  medicineCool: { base: '#9fb4b7', lit: '#c7d1ca', shade: '#6b7c80' },
  bottleAmber: { base: '#a96637', lit: '#ca8651', shade: '#704225' },
  bottleWhite: { base: '#c1cbc5', lit: '#e3e6dc', shade: '#899693' },
  capRed: { base: '#9e3e3d', lit: '#c65a54', shade: '#68292c' },
  capBlue: { base: '#365c80', lit: '#507da2', shade: '#233c58' },
  capGreen: { base: '#4f765d', lit: '#72a37d', shade: '#314b3b' },
  capGrey: { base: '#777d7a', lit: '#aab0a9', shade: '#4e5553' },
  copper: { base: '#965c45', lit: '#bc7959', shade: '#613b31' },
  coil: { base: '#31383a', lit: '#596365', shade: '#191e20' },
  coilBar: { base: '#31383a', lit: '#596365', shade: '#191e20', micro: 7, microStrength: .30 },
};

export function useRawColours() {
  THREE.ColorManagement.enabled = false;
}

const SURFACES = {
  plate: { rect: [0, 0, 20, 20], margin: 2, repeat: 0 },
  plateSeam: { rect: [20, 0, 20, 20], margin: 2, repeat: 0 },
  vent: { rect: [40, 0, 20, 20], margin: 3, repeat: 1 },
  trim: { rect: [60, 0, 20, 20], margin: 2, repeat: 0 },
  recess: { rect: [80, 0, 20, 20], margin: 4, repeat: 0 },
};

// Per-face semantic profiles. Unlike material families, these describe what a
// face does on the prop. The atlas stores indexed tone roles, never colors.
const SEMANTIC_PROFILES = {
  roofTop: { index: 0, margin: 4, repeat: [0, 0] },
  crownFront: { index: 1, margin: 4, repeat: [1, 0] },
  cabinetSide: { index: 2, margin: 4, repeat: [0, 0] },
  doorFrame: { index: 3, margin: 4, repeat: [0, 0] },
  shelfTop: { index: 4, margin: 3, repeat: [1, 1] },
  shelfLip: { index: 5, margin: 3, repeat: [1, 0] },
  baseFront: { index: 6, margin: 4, repeat: [0, 0] },
  ventField: { index: 7, margin: 3, repeat: [1, 1] },
};

const SEMANTIC_MARKS = {
  cabinetService: { rect: [88, 8, 8, 16] },
  doorSocket: { rect: [96, 0, 8, 8] },
  shelfPatch: { rect: [128, 0, 12, 12] },
  serviceStripe: { rect: [160, 13, 32, 7] },
};

function familyMaterial(name, family, surfaceTexture, semanticTexture, microTexture) {
  const surface = SURFACES[family.surface];
  const roleUniforms = {};
  for (const face of ['Left', 'Right', 'Bottom', 'Top', 'Front', 'Back']) {
    roleUniforms[`uRoleRect${face}`] = { value: new THREE.Vector4(0, 0, 0, 0) };
    roleUniforms[`uRoleParams${face}`] = { value: new THREE.Vector4(0, 0, 0, 0) };
  }
  return new THREE.ShaderMaterial({
    name: `recipe_${name}`,
    uniforms: {
      uBase: { value: new THREE.Color(family.base) },
      uLit: { value: new THREE.Color(family.lit) },
      uShade: { value: new THREE.Color(family.shade) },
      uDeep: { value: new THREE.Color(family.shade).multiplyScalar(.72) },
      uCatch: { value: new THREE.Color(family.lit).multiplyScalar(1.10) },
      uLo: { value: STYLE.objLo * STYLE.texel },
      uHi: { value: STYLE.objHi * STYLE.texel },
      uSurface: { value: surfaceTexture ?? null },
      uSurfaceRect: { value: surface ? new THREE.Vector4(surface.rect[0] / 100, 0, .2, 1) : new THREE.Vector4() },
      uSurfaceMargin: { value: surface?.margin ?? 0 },
      uSurfaceRepeat: { value: surface?.repeat ?? 0 },
      uSurfaceEnabled: { value: surface && surfaceTexture ? 1 : 0 },
      uSemantic: { value: semanticTexture ?? null },
      uMicro: { value: microTexture ?? null },
      uMicroRect: { value: family.micro === undefined
        ? new THREE.Vector4()
        : new THREE.Vector4(family.micro / 8, 0, 1 / 8, 1) },
      uMicroEnabled: { value: microTexture && family.micro !== undefined ? 1 : 0 },
      uMicroStrength: { value: family.microStrength ?? 0 },
      ...roleUniforms,
      uHalf: { value: new THREE.Vector3(1) },
      uTexel: { value: STYLE.texel },
    },
    vertexShader: `
      varying vec3 vNormal;
      varying vec3 vWorld;
      varying vec3 vLocal;
      varying vec3 vAxisScale;
      void main() {
        // Face roles and fixed lighting must remain object/world aligned.
        // normalMatrix is camera-space and made roles change when the camera moved.
        vNormal = normalize(mat3(modelMatrix) * normal);
        vLocal = position;
        vAxisScale = vec3(
          length(modelMatrix[0].xyz),
          length(modelMatrix[1].xyz),
          length(modelMatrix[2].xyz)
        );
        vec4 world = modelMatrix * vec4(position, 1.0);
        vWorld = world.xyz;
        gl_Position = projectionMatrix * viewMatrix * world;
      }
    `,
    fragmentShader: `
      uniform vec3 uBase;
      uniform vec3 uLit;
      uniform vec3 uShade;
      uniform vec3 uDeep;
      uniform vec3 uCatch;
      uniform float uLo;
      uniform float uHi;
      uniform sampler2D uSurface;
      uniform vec4 uSurfaceRect;
      uniform float uSurfaceMargin;
      uniform float uSurfaceRepeat;
      uniform float uSurfaceEnabled;
      uniform sampler2D uSemantic;
      uniform sampler2D uMicro;
      uniform vec4 uMicroRect;
      uniform float uMicroEnabled;
      uniform float uMicroStrength;
      uniform vec4 uRoleRectLeft; uniform vec4 uRoleParamsLeft;
      uniform vec4 uRoleRectRight; uniform vec4 uRoleParamsRight;
      uniform vec4 uRoleRectBottom; uniform vec4 uRoleParamsBottom;
      uniform vec4 uRoleRectTop; uniform vec4 uRoleParamsTop;
      uniform vec4 uRoleRectFront; uniform vec4 uRoleParamsFront;
      uniform vec4 uRoleRectBack; uniform vec4 uRoleParamsBack;
      uniform vec3 uHalf;
      uniform float uTexel;
      varying vec3 vNormal;
      varying vec3 vWorld;
      varying vec3 vLocal;
      varying vec3 vAxisScale;
      float nineAxis(float p, float span, float margin, float repeatMiddle) {
        if (p < margin) return p;
        if (p > span - margin) return 20.0 - (span - p);
        float sourceMiddle = max(1.0, 20.0 - 2.0 * margin);
        if (repeatMiddle > 0.5) return margin + mod(p - margin, sourceMiddle);
        return margin + (p - margin) / max(1.0, span - 2.0 * margin) * sourceMiddle;
      }
      float nineAxis32(float p, float span, float margin, float repeatMiddle) {
        if (p < margin) return p;
        if (p > span - margin) return 32.0 - (span - p);
        float sourceMiddle = max(1.0, 32.0 - 2.0 * margin);
        if (repeatMiddle > 0.5) return margin + mod(p - margin, sourceMiddle);
        return margin + (p - margin) / max(1.0, span - 2.0 * margin) * sourceMiddle;
      }
      void main() {
        vec3 n = normalize(vNormal);
        float top = max(n.y, 0.0);
        float front = max(-n.z, 0.0);
        float side = max(n.x, 0.0);
        vec3 face = uBase;
        if (top > 0.55) face = mix(uBase, uLit, top * 0.82);
        else if (side > 0.55) face = mix(uBase, uShade, side * 0.42);
        else if (front < 0.25) face = mix(uBase, uShade, 0.22);
        vec3 axis = abs(n);
        float aligned = max(axis.x, max(axis.y, axis.z));
        // Convert local coordinates and extents into physical coordinates.
        // This keeps every texel and SDF margin stable even if a parent applies
        // a non-uniform model-matrix scale instead of rebuilding the generator.
        vec3 physicalP = (vLocal + uHalf) * vAxisScale;
        vec3 physicalSpan = (2.0 * uHalf) * vAxisScale;
        if (uMicroEnabled > .5 && aligned > .95) {
          vec2 microP;
          vec2 microSpan;
          if (axis.z >= axis.x && axis.z >= axis.y) {
            microP = physicalP.xy / (uTexel * .5);
            microSpan = physicalSpan.xy / (uTexel * .5);
            if (n.z < 0.0) microP.x = microSpan.x - microP.x;
          } else if (axis.x >= axis.y) {
            microP = physicalP.zy / (uTexel * .5);
            microSpan = physicalSpan.zy / (uTexel * .5);
            if (n.x > 0.0) microP.x = microSpan.x - microP.x;
          } else {
            microP = physicalP.xz / (uTexel * .5);
            microSpan = physicalSpan.xz / (uTexel * .5);
          }
          vec2 cell = mod(microP, 64.0);
          vec3 authored = texture2D(uMicro, uMicroRect.xy + ((cell + .5) / 64.0) * uMicroRect.zw).rgb;
          float fixedTint = top > .55 ? 1.06 : (side > .55 ? .96 : (front > .25 ? 1.0 : .90));
          // The source contributes restrained chroma/value breakup.  Strong
          // borders, seams and corner wear are applied below by semantic masks.
          // This prevents a quiet sheet-metal face becoming repeating noise.
          float edgeDistance = min(
            min(microP.x, microSpan.x - microP.x),
            min(microP.y, microSpan.y - microP.y)
          );
          // Hard bands are intentional: interpolated thresholds create hundreds
          // of accidental colours and stop reading as authored pixel clusters.
          float edgeAuthority = edgeDistance < 10.0 ? 1.0 : 0.0;
          float lowerAuthority = axis.y < .95
            ? (microP.y < 20.0 ? 1.0 : 0.0)
            : 0.0;
          float localStrength = clamp(
            uMicroStrength + max(edgeAuthority * .50, lowerAuthority * .34),
            0.0, .88
          );
          face = mix(face, clamp(authored * fixedTint, 0.0, 1.0), localStrength);
        }
        if (uSurfaceEnabled > 0.5 && aligned > 0.95) {
          vec2 p;
          vec2 span;
          if (axis.z >= axis.x && axis.z >= axis.y) {
            p = physicalP.xy / uTexel;
            span = physicalSpan.xy / uTexel;
            if (n.z < 0.0) p.x = span.x - p.x;
          } else if (axis.x >= axis.y) {
            p = physicalP.zy / uTexel;
            span = physicalSpan.zy / uTexel;
            if (n.x > 0.0) p.x = span.x - p.x;
          } else {
            p = physicalP.xz / uTexel;
            span = physicalSpan.xz / uTexel;
          }
          if (min(span.x, span.y) > 2.0 * uSurfaceMargin + 1.0) {
            vec2 samplePx = vec2(
              nineAxis(p.x, span.x, uSurfaceMargin, uSurfaceRepeat),
              nineAxis(p.y, span.y, uSurfaceMargin, uSurfaceRepeat)
            );
            vec2 maskUv = uSurfaceRect.xy + ((samplePx + .5) / 20.0) * uSurfaceRect.zw;
            float maskTone = texture2D(uSurface, maskUv).r;
            if (maskTone < .25) face = mix(face, uShade, .82);
            else if (maskTone > .75) face = mix(face, uLit, .72);
          }
        }
        vec4 roleRect;
        vec4 roleParams;
        if (axis.x >= axis.y && axis.x >= axis.z) {
          if (n.x > 0.0) { roleRect = uRoleRectRight; roleParams = uRoleParamsRight; }
          else { roleRect = uRoleRectLeft; roleParams = uRoleParamsLeft; }
        } else if (axis.y >= axis.z) {
          if (n.y > 0.0) { roleRect = uRoleRectTop; roleParams = uRoleParamsTop; }
          else { roleRect = uRoleRectBottom; roleParams = uRoleParamsBottom; }
        } else {
          if (n.z < 0.0) { roleRect = uRoleRectFront; roleParams = uRoleParamsFront; }
          else { roleRect = uRoleRectBack; roleParams = uRoleParamsBack; }
        }
        if (roleParams.w > .5 && aligned > .95) {
          vec2 p;
          vec2 span;
          if (axis.z >= axis.x && axis.z >= axis.y) {
            p = physicalP.xy / (uTexel * .5);
            span = physicalSpan.xy / (uTexel * .5);
            if (n.z < 0.0) p.x = span.x - p.x;
          } else if (axis.x >= axis.y) {
            p = physicalP.zy / (uTexel * .5);
            span = physicalSpan.zy / (uTexel * .5);
            if (n.x > 0.0) p.x = span.x - p.x;
          } else {
            p = physicalP.xz / (uTexel * .5);
            span = physicalSpan.xz / (uTexel * .5);
          }
          if (min(span.x, span.y) > 2.0 * roleParams.x + 1.0) {
            vec2 samplePx = vec2(
              nineAxis32(p.x, span.x, roleParams.x, roleParams.y),
              nineAxis32(p.y, span.y, roleParams.x, roleParams.z)
            );
            float tone = texture2D(uSemantic, roleRect.xy + ((samplePx + .5) / 32.0) * roleRect.zw).r;
            if (tone < .22) face = uDeep;
            else if (tone < .44) face = uShade;
            else if (tone < .63) { if (uMicroEnabled < .5) face = uBase; }
            else if (tone < .86) face = uLit;
            else face = uCatch;
          }
        }
        float ramp = clamp((vWorld.y-uLo) / max(0.001, uHi-uLo), 0.0, 1.0);
        float bayer = mod(gl_FragCoord.x + 2.0 * gl_FragCoord.y, 4.0) / 4.0;
        if (ramp * 0.22 > bayer) face = mix(face, uLit, 0.10);
        gl_FragColor = vec4(face, 1.0);
      }
    `,
  });
}

export function makeMaterials(surfaceTexture, semanticTexture, microTexture = null) {
  return Object.fromEntries(Object.entries(MATS).map(([key, value]) => [key, familyMaterial(key, value, surfaceTexture, semanticTexture, microTexture)]));
}

export function tableBox(kind, a, b, materials, opts = {}) {
  const min = a.map((value, index) => Math.min(value, b[index]));
  const max = a.map((value, index) => Math.max(value, b[index]));
  const width = (max[0] - min[0]) * STYLE.texel;
  const depth = (max[1] - min[1]) * STYLE.texel;
  const height = (max[2] - min[2]) * STYLE.texel;
  const bevelPx = opts.bevel ?? STYLE.bevel;
  const radius = Math.min(bevelPx * STYLE.texel, width * .18, depth * .18, height * .18);
  const geometry = bevelPx > 0
    ? new RoundedBoxGeometry(width, height, depth, 1, radius)
    : new THREE.BoxGeometry(width, height, depth, 1, 1, 1);

  const taperX = (opts.taperX ?? 0) * STYLE.texel;
  const taperY = (opts.taperY ?? opts.taperZ ?? 0) * STYLE.texel;
  if (taperX || taperY) {
    const positions = geometry.attributes.position;
    for (let index = 0; index < positions.count; index += 1) {
      const vertical = (positions.getY(index) / height) + .5;
      positions.setX(index, positions.getX(index) * (1 - vertical * taperX / Math.max(width, STYLE.texel)));
      positions.setZ(index, positions.getZ(index) * (1 - vertical * taperY / Math.max(depth, STYLE.texel)));
    }
    positions.needsUpdate = true;
    geometry.computeVertexNormals();
  }
  const material = materials[kind].clone();
  material.uniforms.uHalf.value = new THREE.Vector3(width * .5, height * .5, depth * .5);
  if (opts.disableGenericSurface) material.uniforms.uSurfaceEnabled.value = 0;
  const faceUniform = {
    left: 'Left', right: 'Right', bottom: 'Bottom', top: 'Top', front: 'Front', back: 'Back',
  };
  for (const [face, profileName] of Object.entries(opts.surfaceFaces ?? {})) {
    const profile = SEMANTIC_PROFILES[profileName];
    const suffix = faceUniform[face];
    if (!profile || !suffix) throw new Error(`Unknown semantic surface ${face}:${profileName}`);
    material.uniforms[`uRoleRect${suffix}`].value.set(profile.index / 8, 0, 1 / 8, 1);
    material.uniforms[`uRoleParams${suffix}`].value.set(
      profile.margin, profile.repeat[0], profile.repeat[1], material.uniforms.uSemantic.value ? 1 : 0,
    );
  }
  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = opts.name ?? `${kind}_box`;
  mesh.position.set(
    (min[0] + max[0]) * .5 * STYLE.texel,
    (min[2] + max[2]) * .5 * STYLE.texel,
    (min[1] + max[1]) * .5 * STYLE.texel,
  );
  mesh.userData.kind = kind;
  mesh.userData.referenceBounds = [min, max];
  mesh.userData.bevelPx = bevelPx;
  return mesh;
}

const REGIONS = {
  controlBezel: { rect: [4, 76, 16, 16], family: 'dark' },
  cautionPlate: { rect: [76, 76, 16, 16], family: 'ochre' },
};

function decalMaterial(texture, region, family) {
  const [x, y, width, height] = region;
  const palette = MATS[family];
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    uniforms: {
      uMap: { value: texture },
      uRect: { value: new THREE.Vector4(x / 96, 1 - (y + height) / 96, width / 96, height / 96) },
      uBase: { value: new THREE.Color(palette.base) },
      uLit: { value: new THREE.Color(palette.lit) },
      uShade: { value: new THREE.Color(palette.shade) },
    },
    vertexShader: `varying vec2 vUv; void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
    fragmentShader: `
      varying vec2 vUv;
      uniform sampler2D uMap;
      uniform vec4 uRect;
      uniform vec3 uBase;
      uniform vec3 uLit;
      uniform vec3 uShade;
      void main(){
        vec4 source = texture2D(uMap, uRect.xy + vUv * uRect.zw);
        if(source.a < 0.5) discard;
        float luma = dot(source.rgb, vec3(0.2126,0.7152,0.0722));
        vec3 color = luma < 0.25 ? uShade : (luma > 0.62 ? uLit : uBase);
        gl_FragColor = vec4(color, 1.0);
      }
    `,
  });
}

function semanticDecalMaterial(texture, region, family) {
  const [x, y, width, height] = region;
  const palette = MATS[family];
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    uniforms: {
      uMap: { value: texture },
      uRect: { value: new THREE.Vector4(x / 256, 1 - (y + height) / 32, width / 256, height / 32) },
      uDeep: { value: new THREE.Color(palette.shade).multiplyScalar(.72) },
      uShade: { value: new THREE.Color(palette.shade) },
      uLit: { value: new THREE.Color(palette.lit) },
      uCatch: { value: new THREE.Color(palette.lit).multiplyScalar(1.10) },
    },
    vertexShader: 'varying vec2 vUv; void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
    fragmentShader: `
      varying vec2 vUv;
      uniform sampler2D uMap;
      uniform vec4 uRect;
      uniform vec3 uDeep;
      uniform vec3 uShade;
      uniform vec3 uLit;
      uniform vec3 uCatch;
      void main(){
        float tone=texture2D(uMap,uRect.xy+vUv*uRect.zw).r;
        if(tone>=.44 && tone<.63) discard;
        vec3 color=tone<.22?uDeep:(tone<.44?uShade:(tone<.86?uLit:uCatch));
        gl_FragColor=vec4(color,1.0);
      }
    `,
  });
}

export async function makeDecalKit() {
  const loader = new THREE.TextureLoader();
  const [texture, grille, display, surfaces, semanticFaces] = await Promise.all([
    loader.loadAsync('/textures/vaccine-fridge-nano-paintover-atlas-v11.png'),
    loader.loadAsync('/textures/vaccine-fridge-grille.png'),
    loader.loadAsync('/textures/vaccine-fridge-display.png'),
    loader.loadAsync('/textures/vaccine-fridge-surfaces-v12.png'),
    loader.loadAsync('/textures/vaccine-fridge-semantic-faces-v13.png'),
  ]);
  for (const item of [texture, grille, display, surfaces, semanticFaces]) {
    item.colorSpace = item === surfaces || item === semanticFaces ? THREE.NoColorSpace : THREE.SRGBColorSpace;
    item.magFilter = item.minFilter = THREE.NearestFilter;
    item.generateMipmaps = false;
    item.wrapS = item.wrapT = THREE.ClampToEdgeWrapping;
  }
  const oneTexel = (rgb) => {
    const item = new THREE.DataTexture(new Uint8Array([...rgb, 255]), 1, 1, THREE.RGBAFormat);
    // Values already belong to the raw post-palette; do not decode them twice.
    item.colorSpace = THREE.NoColorSpace;
    item.magFilter = item.minFilter = THREE.NearestFilter;
    item.generateMipmaps = false;
    item.needsUpdate = true;
    return item;
  };
  return {
    texture, grille, display, surfaces, semanticFaces,
    statusBlue: oneTexel([96, 174, 202]),
    statusGreen: oneTexel([103, 166, 107]),
    statusRed: oneTexel([213, 99, 84]),
    statusAmber: oneTexel([235, 177, 96]),
    statusCyan: oneTexel([126, 203, 209]),
    handleHighlight: oneTexel([106, 80, 116]),
    materials: new Map(),
  };
}

export function decal(name, face, u, v, widthPx, heightPx, plane, kit) {
  const region = REGIONS[name];
  if (!region) throw new Error(`Unknown decal ${name}`);
  const key = `${name}:${region.family}`;
  if (!kit.materials.has(key)) kit.materials.set(key, decalMaterial(kit.texture, region.rect, region.family));
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(widthPx * STYLE.texel, heightPx * STYLE.texel),
    kit.materials.get(key),
  );
  mesh.name = `decal_${name}`;
  if (face === 'front') {
    mesh.position.set(u * STYLE.texel, v * STYLE.texel, plane * STYLE.texel);
  } else if (face === 'right') {
    mesh.rotation.y = Math.PI / 2;
    mesh.position.set(plane * STYLE.texel, v * STYLE.texel, u * STYLE.texel);
  } else if (face === 'top') {
    mesh.rotation.x = -Math.PI / 2;
    mesh.position.set(u * STYLE.texel, plane * STYLE.texel, v * STYLE.texel);
  }
  mesh.renderOrder = 4;
  mesh.userData.fixedTexelSize = [widthPx, heightPx];
  mesh.userData.mountPlane = face;
  return mesh;
}

export function semanticDecal(name, family, face, u, v, widthPx, heightPx, plane, kit) {
  const mark = SEMANTIC_MARKS[name];
  if (!mark) throw new Error(`Unknown semantic decal ${name}`);
  const key = `semantic:${name}:${family}`;
  if (!kit.materials.has(key)) {
    kit.materials.set(key, semanticDecalMaterial(kit.semanticFaces, mark.rect, family));
  }
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(widthPx * STYLE.texel, heightPx * STYLE.texel),
    kit.materials.get(key),
  );
  mesh.name = `decal_semantic_${name}`;
  if (face === 'front') mesh.position.set(u * STYLE.texel, v * STYLE.texel, plane * STYLE.texel);
  if (face === 'right') {
    mesh.rotation.y = Math.PI / 2;
    mesh.position.set(plane * STYLE.texel, v * STYLE.texel, u * STYLE.texel);
  }
  if (face === 'left') {
    mesh.rotation.y = -Math.PI / 2;
    mesh.position.set(plane * STYLE.texel, v * STYLE.texel, u * STYLE.texel);
  }
  if (face === 'top') {
    mesh.rotation.x = -Math.PI / 2;
    mesh.position.set(u * STYLE.texel, plane * STYLE.texel, v * STYLE.texel);
  }
  mesh.renderOrder = 6;
  mesh.userData.fixedTexelSize = [widthPx, heightPx];
  mesh.userData.mountPlane = face;
  mesh.userData.semanticRole = name;
  return mesh;
}

export function imageDecal(name, face, u, v, widthPx, heightPx, plane, kit) {
  const texture = kit[name];
  if (!texture) throw new Error(`Unknown image decal ${name}`);
  const material = new THREE.MeshBasicMaterial({
    map: texture,
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(widthPx * STYLE.texel, heightPx * STYLE.texel),
    material,
  );
  mesh.name = `decal_${name}`;
  if (face === 'front') mesh.position.set(u * STYLE.texel, v * STYLE.texel, plane * STYLE.texel);
  if (face === 'right') {
    mesh.rotation.y = Math.PI / 2;
    mesh.position.set(plane * STYLE.texel, v * STYLE.texel, u * STYLE.texel);
  }
  mesh.renderOrder = 5;
  mesh.userData.fixedTexelSize = [widthPx, heightPx];
  mesh.userData.mountPlane = face;
  return mesh;
}

export function triangleCount(root) {
  let count = 0;
  root.traverse((node) => {
    if (!node.isMesh) return;
    const geometry = node.geometry;
    count += geometry.index ? geometry.index.count / 3 : geometry.attributes.position.count / 3;
  });
  return count;
}
