import {
  Color, Matrix4, ShaderMaterial, Vector3,
} from 'three';

const axisScale = new Vector3();
const matrixColumn = new Vector3();

export function updateAnalyticBoxScale(material, object) {
  const elements = object.matrixWorld.elements;
  axisScale.set(
    matrixColumn.set(elements[0], elements[1], elements[2]).length(),
    matrixColumn.set(elements[4], elements[5], elements[6]).length(),
    matrixColumn.set(elements[8], elements[9], elements[10]).length(),
  );
  material.uniforms.uAxisScale.value.copy(axisScale);
}

/**
 * UV-less flat material for axis-aligned box faces.
 *
 * The edge distance is evaluated from local position and local bounds, then
 * multiplied by the current world-axis scale. A non-uniformly stretched box
 * therefore receives more center area without stretching its border widths.
 */
export function createAnalyticBoxMaterial({
  boundsMin,
  boundsMax,
  baseColor = '#617a80',
  shadowColor = '#4a5d62',
  highlightColor = '#76949c',
  outlineColor = '#38474a',
  tints = { top: 1.09, front: 1, side: 0.858, back: 0.9, bottom: 0.74 },
  outline = 1 / 32,
  catchWidth = 2 / 32,
  inset = 4 / 32,
  seamWidth = 0.75 / 32,
  gatePadding = 1 / 32,
  insetEnabled = true,
  opacity = 1,
} = {}) {
  if (!boundsMin || !boundsMax) throw new Error('Analytic box material requires local bounds');

  const material = new ShaderMaterial({
    uniforms: {
      uBoundsMin: { value: boundsMin.clone() },
      uBoundsMax: { value: boundsMax.clone() },
      uAxisScale: { value: new Vector3(1, 1, 1) },
      uBaseColor: { value: new Color(baseColor) },
      uShadowColor: { value: new Color(shadowColor) },
      uHighlightColor: { value: new Color(highlightColor) },
      uOutlineColor: { value: new Color(outlineColor) },
      uFaceTints: { value: new Matrix4().set(
        tints.side, tints.front, tints.top, 0,
        tints.side, tints.back, tints.bottom, 0,
        0, 0, 0, 0,
        0, 0, 0, 1,
      ) },
      uOutline: { value: outline },
      uCatch: { value: catchWidth },
      uInset: { value: inset },
      uSeamWidth: { value: seamWidth },
      uGatePadding: { value: gatePadding },
      uInsetEnabled: { value: insetEnabled ? 1 : 0 },
      uOpacity: { value: opacity },
    },
    vertexShader: /* glsl */`
      varying vec3 vBoxPosition;
      varying vec3 vBoxNormal;

      void main() {
        vBoxPosition = position;
        vBoxNormal = normal;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */`
      uniform vec3 uBoundsMin;
      uniform vec3 uBoundsMax;
      uniform vec3 uAxisScale;
      uniform vec3 uBaseColor;
      uniform vec3 uShadowColor;
      uniform vec3 uHighlightColor;
      uniform vec3 uOutlineColor;
      uniform mat4 uFaceTints;
      uniform float uOutline;
      uniform float uCatch;
      uniform float uInset;
      uniform float uSeamWidth;
      uniform float uGatePadding;
      uniform float uInsetEnabled;
      uniform float uOpacity;
      varying vec3 vBoxPosition;
      varying vec3 vBoxNormal;

      void main() {
        vec3 n = normalize(vBoxNormal);
        vec3 an = abs(n);
        vec3 fromMin = max(vec3(0.0), (vBoxPosition - uBoundsMin) * uAxisScale);
        vec3 fromMax = max(vec3(0.0), (uBoundsMax - vBoxPosition) * uAxisScale);

        float edgeDistance;
        float brightDistance;
        float darkDistance;
        float shorterSide;
        float tint;

        if (an.x >= an.y && an.x >= an.z) {
          edgeDistance = min(min(fromMin.y, fromMax.y), min(fromMin.z, fromMax.z));
          brightDistance = min(fromMin.y, fromMax.z); // front and top
          darkDistance = min(fromMax.y, fromMin.z);   // back and bottom
          shorterSide = min((uBoundsMax.y-uBoundsMin.y)*uAxisScale.y,
                            (uBoundsMax.z-uBoundsMin.z)*uAxisScale.z);
          tint = uFaceTints[0][0];
        } else if (an.y >= an.z) {
          edgeDistance = min(min(fromMin.x, fromMax.x), min(fromMin.z, fromMax.z));
          brightDistance = min(fromMin.x, fromMax.z); // left and top
          darkDistance = min(fromMax.x, fromMin.z);   // right and bottom
          shorterSide = min((uBoundsMax.x-uBoundsMin.x)*uAxisScale.x,
                            (uBoundsMax.z-uBoundsMin.z)*uAxisScale.z);
          tint = n.y < 0.0 ? uFaceTints[1][0] : uFaceTints[1][1];
        } else {
          edgeDistance = min(min(fromMin.x, fromMax.x), min(fromMin.y, fromMax.y));
          brightDistance = min(fromMin.x, fromMax.y);
          darkDistance = min(fromMax.x, fromMin.y);
          shorterSide = min((uBoundsMax.x-uBoundsMin.x)*uAxisScale.x,
                            (uBoundsMax.y-uBoundsMin.y)*uAxisScale.y);
          tint = n.z > 0.0 ? uFaceTints[2][0] : uFaceTints[2][1];
        }

        vec3 color = uBaseColor * tint;
        bool canInset = uInsetEnabled > 0.5 && shorterSide > (2.0 * uInset + uGatePadding);
        if (canInset && abs(edgeDistance - uInset) < uSeamWidth * 0.5) {
          color = mix(color, uShadowColor * tint, 0.72);
        }
        if (edgeDistance < uCatch) {
          color = (brightDistance <= darkDistance ? uHighlightColor : uShadowColor) * tint;
        }
        if (edgeDistance < uOutline) color = uOutlineColor * tint;

        gl_FragColor = vec4(color, uOpacity);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
  });

  material.transparent = opacity < 1;
  material.depthWrite = opacity >= 1;

  material.name = 'fridge_analytic_box_side_v1';
  material.userData.uvLessAnalytic = true;
  material.userData.worldUnitBands = { outline, catchWidth, inset, seamWidth, gatePadding };
  return material;
}

/** CPU twin used by tests to prove non-uniform scale compensation. */
export function analyticFaceMetrics(position, boundsMin, boundsMax, normal, scale) {
  const fromMin = position.clone().sub(boundsMin).multiply(scale);
  const fromMax = boundsMax.clone().sub(position).multiply(scale);
  const n = normal.clone();
  n.set(Math.abs(n.x), Math.abs(n.y), Math.abs(n.z));
  if (n.x >= n.y && n.x >= n.z) {
    return {
      edgeDistance: Math.min(fromMin.y, fromMax.y, fromMin.z, fromMax.z),
      shorterSide: Math.min((boundsMax.y - boundsMin.y) * scale.y,
        (boundsMax.z - boundsMin.z) * scale.z),
    };
  }
  if (n.y >= n.z) {
    return {
      edgeDistance: Math.min(fromMin.x, fromMax.x, fromMin.z, fromMax.z),
      shorterSide: Math.min((boundsMax.x - boundsMin.x) * scale.x,
        (boundsMax.z - boundsMin.z) * scale.z),
    };
  }
  return {
    edgeDistance: Math.min(fromMin.x, fromMax.x, fromMin.y, fromMax.y),
    shorterSide: Math.min((boundsMax.x - boundsMin.x) * scale.x,
      (boundsMax.y - boundsMin.y) * scale.y),
  };
}
