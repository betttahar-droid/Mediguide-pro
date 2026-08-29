import { Group, Mesh, Vector3, Quaternion } from 'three';
import { createAdaptiveMaterial } from '../shaders/index.js';
import { bakeMasks } from '../art/bakeMasks.js';
import { REGISTRY, defaultParams, buildGeometry, trimAxisVector } from './registry.js';
import { clampParams, layout, footprint } from './resize.js';
import { contactShadowMaterial, contactShadowGeometry } from '../art/shadow.js';
import { DecorLayer, warmDecorCache } from './decor.js';

/** One baked geometry per module type — the masks are baked on the undeformed mesh. */
const geometryCache = new Map();

export function unitGeometry(def) {
  if (!geometryCache.has(def.id)) {
    geometryCache.set(def.id, bakeMasks(buildGeometry(def)));
  }
  return geometryCache.get(def.id);
}

/** Pre-bake everything up front so placement never stalls mid-drag. */
export function warmGeometryCache() {
  for (const def of Object.values(REGISTRY)) unitGeometry(def);
  warmDecorCache();
}

/** The material a module type wants, shared by ModuleInstance and the batches. */
export function materialOptionsFor(def, extra = {}) {
  return {
    baseColor: def.colors.base,
    middleColor: def.colors.middle,
    accent1: def.colors.accent1 ?? null,
    accent2: def.colors.accent2 ?? null,
    accent3: def.colors.accent3 ?? null,
    accent4: def.colors.accent4 ?? null,
    sourceHalfExtents: new Vector3(...def.unit),
    margins: new Vector3(...def.margins),
    trimAxis: trimAxisVector(def),
    trimDensity: def.trimDensity,
    atlasCell: def.atlasCell,
    ...extra,
  };
}

let nextId = 1;

export class ModuleInstance {
  constructor(typeId, { params, position, rotY = 0, ghost = false, seed } = {}) {
    this.def = REGISTRY[typeId];
    if (!this.def) throw new Error(`unknown module type "${typeId}"`);
    this.uid = nextId++;
    this.typeId = typeId;
    this.ghost = ghost;
    // Saved with the module, so decor survives a reload unchanged.
    this.seed = seed ?? (Math.random() * 0xffffffff) >>> 0;
    this.params = clampParams(this.def, params ?? defaultParams(this.def));

    this.group = new Group();
    this.group.name = `module:${typeId}:${this.uid}`;
    this.group.userData.module = this;
    if (position) this.group.position.set(...position);
    this.group.rotation.y = rotY;

    this.material = createAdaptiveMaterial(
      materialOptionsFor(this.def, {
        transparent: ghost,
        opacity: ghost ? 0.45 : 1,
      })
    );

    this.meshes = [];

    // grounds the module; excluded from this.meshes so it is never picked or
    // outlined, and skipped for ghosts
    if (!ghost && this.def.mounts.some((m) => m.tag === 'floor')) {
      this.shadow = new Mesh(contactShadowGeometry(), contactShadowMaterial());
      this.shadow.renderOrder = -1;
      this.group.add(this.shadow);
    }

    // Decor pops in and out as the module is resized. Ghosts stay bare so the
    // placement preview reads as a shape, not a shopping list.
    if (!ghost && this.def.decor) {
      this.decor = new DecorLayer();
      this.group.add(this.decor.group);
    }

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

    if (this.shadow) {
      this.shadow.scale.set(this.footprint[0] * 2.9, 1, this.footprint[2] * 3.0);
      this.shadow.position.y = 0.008;
    }

    if (this.decor) this.decor.update(this.seed, this.def.decor(this.params, this.def.unit));
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
      seed: this.seed,
    };
  }

  setDecorVisible(visible) {
    if (this.decor) this.decor.group.visible = visible;
  }

  dispose() {
    this.group.parent?.remove(this.group);
    this.decor?.dispose();
    this.material.dispose();
    this.meshes.length = 0;
  }
}

const round = (v, p = 3) => Number(v.toFixed(p));
