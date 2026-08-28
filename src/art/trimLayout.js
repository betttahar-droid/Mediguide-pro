// The standard trim sheet layout, §4.1. Data only — this is the contract
// between the authored sheet in public/textures/trim.png and the aTrimV baked
// into every vertex by modules/geometry.js.
//
// Keep every strip at a consistent real-world scale so detail on one module
// matches the next. Change a row here and you must repaint the sheet:
// tools/authoring/make_textures.py holds the same table.
export const SHEET = 1024;

export const STRIPS = {
  edge: { y: 0, h: 64 }, // painted bevels, borders
  detail: { y: 64, h: 128 }, // screw heads, panel seams, label holders
  surface: { y: 192, h: 512 }, // painted wood, laminate, painted metal
  transition: { y: 704, h: 128 }, // wear gradients, dirt masks
  alpha: { y: 832, h: 192 }, // cutouts — grilles, handles
};

/** The V range of a strip, in UV space. Textures load with flipY = false. */
export function stripV(name) {
  const s = STRIPS[name];
  if (!s) throw new Error(`trim sheet has no strip "${name}"`);
  return { v0: s.y / SHEET, v1: (s.y + s.h) / SHEET };
}
