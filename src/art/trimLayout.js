// The standard trim sheet layout, §4.1. Data only — this is the contract
// between the authored sheet in public/textures/trim.png and the aTrimV baked
// into every vertex by modules/geometry.js.
//
// Keep every strip at a consistent real-world scale so detail on one module
// matches the next. Change a row here and you must repaint the sheet:
// tools/authoring/make_textures.py holds the same table.
export const SHEET = 128;

// Pixel art: the sheet is small so a texel lands near 2cm in world space.
// Proportions still match the brief's 64/128/512/128/192 of 1024.
export const STRIPS = {
  edge: { y: 0, h: 8 }, // painted bevels, borders
  detail: { y: 8, h: 16 }, // screw heads, panel seams, label holders
  surface: { y: 24, h: 64 }, // painted wood, laminate, painted metal
  transition: { y: 88, h: 16 }, // wear gradients, dirt masks
  alpha: { y: 104, h: 24 }, // cutouts — grilles, handles
};

/** The V range of a strip, in UV space. Textures load with flipY = false. */
export function stripV(name) {
  const s = STRIPS[name];
  if (!s) throw new Error(`trim sheet has no strip "${name}"`);
  return { v0: s.y / SHEET, v1: (s.y + s.h) / SHEET };
}
