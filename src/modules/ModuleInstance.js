import { Group, Mesh, Vector3, Quaternion } from 'three';
import { createAdaptiveMaterial } from '../shaders/index.js';
import { bakeMasks } from '../art/bakeMasks.js';
import { REGISTRY, defaultParams } from './registry.js';
import { clampParams, layout, footprint } from './resize.js';

/** One baked geometry per module type — the masks are baked on the undeformed mesh. */
const geometryCache = new Map();

export function unitGeometry(def) {
  if (!geometryCache.has(def.id)) {
    const geo = bakeMasks(def.build());
    geometryCache.set(def.id, geo);
  }
  return geometryCache.get(def.id);
}

/** Pre-bake everything up front so placement never stalls mid-drag. */
export function warmGeometryCache() {
  for (const def of Object.values(REGISTRY)) unitGeometry(def);
}

let nextId = 1;

export class ModuleInstance {
  constructor(typeId, { params, position, rotY = 0, ghost = false } = {}) {
    this.def = REGISTRY[typeId];
    if (!this.def) throw new Error(`unknown module type "${typeId}"`);
    this.uid = nextId++;
    this.typeId = typeId;
    this.ghost = ghost;
    this.params = clampParams(this.def, params ?? defaultParams(this.def));

    this.group = new Group();
    this.group.name = `module:${typeId}:${this.uid}`;
    this.group.userData.module = this;
    if (position) this.group.position.set(...position);
    this.group.rotation.y = rotY;

    this.material = createAdaptiveMaterial({
      baseColor: this.def.colors.base,
      middleColor: this.def.colors.middle,
      sourceHalfExtents: new Vector3(...this.def.unit),
      margins: new Vector3(...this.def.margins),
      trimAxis: new Vector3(...this.def.trimAxis),
      transparent: ghost,
      opacity: ghost ? 0.45 : 1,
    });

    this.meshes = [];
    this.rebuild();
  }

  get position() { return this.group.position; }
  get rotY() { return this.group.rotation.y; }

  setParams(patch) {
    this.params = clampParams(this.def, { ...this.params, ...patch });
    this.rebuild();
  }

  rebuild() {
    const geo = unitGeometry(this.def);
    const cells = layout(this.def, this.params);

    // reuse meshes across rebuilds — resizing happens every frame while dragging
    while (this.meshes.length > cells.length) {
      const m = this.meshes.pop();
      this.group.remove(m);
    }
    while (this.meshes.length < cells.length) {
      const m = new Mesh(geo, this.material);
      m.userData.module = this;
      this.meshes.push(m);
      this.group.add(m);
    }
    cells.forEach((cell, i) => this.meshes[i].position.set(...cell.position));

    const s = cells[0]?.targetScale ?? [1, 1, 1];
    this.material.uniforms.uTargetScale.value.set(s[0], s[1], s[2]);
    this.footprint = footprint(this.def, this.params);
  }

  setHighlight(amount) {
    this.material.uniforms.uHighlightAmount.value = amount;
  }

  /** Sockets in world space: what this module offers, plus its own mounts. */
  worldSockets() {
    const q = new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), this.rotY);
    const out = [];
    const push = (tag, pos, normal) => {
      const p = new Vector3(...pos).applyQuaternion(q).add(this.group.position);
      const n = new Vector3(...normal).applyQuaternion(q).normalize();
      out.push({ tag, pos: p, normal: n, owner: this });
    };
    for (const s of this.def.provides(this.params, this.def.unit)) push(s.tag, s.pos, s.normal);
    for (const m of this.mountSockets()) push(m.tag, m.pos, m.normal);
    return out;
  }

  /** Sockets on this module's underside — where it can attach to something else. */
  mountSockets() {
    return this.def.mounts.map((m) => ({ tag: m.tag, pos: [0, 0, 0], normal: m.normal }));
  }

  toJSON() {
    return {
      type: this.typeId,
      pos: [
        round(this.group.position.x),
        round(this.group.position.y),
        round(this.group.position.z),
      ],
      rotY: round(this.rotY, 4),
      params: { ...this.params },
    };
  }

  dispose() {
    this.group.parent?.remove(this.group);
    this.material.dispose();
    this.meshes.length = 0;
  }
}

const round = (v, p = 3) => Number(v.toFixed(p));
