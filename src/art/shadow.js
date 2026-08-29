// Contact shadows.
//
// The adaptive material does not receive shadow maps — the toon ramp is the
// shading model and a real shadow map would fight it. A soft blob under each
// floor-mounted module is what grounds the objects, and it is what hand-painted
// reference art does anyway.
import { CanvasTexture, MeshBasicMaterial, PlaneGeometry, DoubleSide, SRGBColorSpace } from 'three';
import { PALETTE_HEX } from './palette.js';

let material = null;
let geometry = null;

function blobTexture() {
  const size = 128;
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const ctx = c.getContext('2d');
  const g = ctx.createRadialGradient(size / 2, size / 2, size * 0.08, size / 2, size / 2, size / 2);
  g.addColorStop(0, 'rgba(255,255,255,0.9)');
  g.addColorStop(0.45, 'rgba(255,255,255,0.45)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const tex = new CanvasTexture(c);
  tex.colorSpace = SRGBColorSpace;
  return tex;
}

export function contactShadowMaterial() {
  if (!material) {
    material = new MeshBasicMaterial({
      map: blobTexture(),
      color: PALETTE_HEX.shadowCool,
      transparent: true,
      opacity: 0.4,
      depthWrite: false,
      side: DoubleSide,
    });
  }
  return material;
}

export function contactShadowGeometry() {
  if (!geometry) {
    geometry = new PlaneGeometry(1, 1);
    geometry.rotateX(-Math.PI / 2);
  }
  return geometry;
}
