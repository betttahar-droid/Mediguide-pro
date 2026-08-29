// §8.5 — save format. Pure functions, so swapping localStorage for a backend
// is one call site.
import { ModuleInstance } from '../modules/ModuleInstance.js';
import { REGISTRY } from '../modules/registry.js';

const KEY = 'pharmacy-builder/scene/v1';

export function serialize(modules) {
  return {
    version: 1,
    units: 'meters',
    modules: modules.map((m) => m.toJSON()),
  };
}

export function deserialize(data) {
  if (!data || data.version !== 1) throw new Error('unsupported save format');
  return data.modules
    .filter((entry) => {
      if (REGISTRY[entry.type]) return true;
      console.warn(`skipping unknown module type "${entry.type}"`);
      return false;
    })
    .map((entry) => new ModuleInstance(entry.type, {
      params: entry.params,
      position: entry.pos,
      rotY: entry.rotY,
      seed: entry.seed, // keeps the decor identical across a reload
    }));
}

export function saveLocal(modules) {
  localStorage.setItem(KEY, JSON.stringify(serialize(modules)));
}

export function loadLocal() {
  const raw = localStorage.getItem(KEY);
  return raw ? deserialize(JSON.parse(raw)) : null;
}

export function clearLocal() {
  localStorage.removeItem(KEY);
}
