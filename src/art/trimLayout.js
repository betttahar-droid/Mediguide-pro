// The trim sheet layout, §4.1. Data only — this is the contract between the
// authored sheet in public/textures/trim.png and the aTrimV baked into every
// vertex by modules/geometry.js.
//
// These strips are MATERIALS. That is the whole point of the row, and getting
// it wrong is very visible: the sheet used to carry one generic "surface" strip
// of mottling and speckle that every part sampled, so a computer screen came
// out looking like rock, a pane of glass looked like rock, and a paper label
// looked like rock. A part now says what it is made of and gets a strip painted
// to look like that.
//
// The sheet is 128 WIDE and 256 TALL. Width sets the texel size along the
// tiling axis and has not changed; the extra height is what buys twelve
// materials at the same texel scale rather than one at twice the resolution.
//
// Change a row here and you must repaint the sheet:
// tools/authoring/make_textures.py holds the same table.
export const SHEET_W = 128;
export const SHEET_H = 256;

export const STRIPS = {
  edge: { y: 0, h: 12 }, //        painted bevels and borders
  detail: { y: 12, h: 16 }, //     screw heads, panel seams, label rails
  paint: { y: 28, h: 24 }, //      painted metal and plastic — the DEFAULT
  panel: { y: 52, h: 32 }, //      a big flat panel: drawn seam border, corner bolts
  wood: { y: 84, h: 32 }, //       real grain, drawn as broken dashes, one knot
  steel: { y: 116, h: 24 }, //     bare metal: flat, a faint sheen band, rivets
  grille: { y: 140, h: 16 }, //    hard dark slots with lit lips
  screen: { y: 156, h: 16 }, //    a lit display: near-black with a hard diagonal streak
  glass: { y: 172, h: 16 }, //     pale and flat, one diagonal streak
  paper: { y: 188, h: 16 }, //     card and labels: flat, the faintest fibre
  fabric: { y: 204, h: 24 }, //    upholstery: an even weave
  transition: { y: 228, h: 28 }, // wear gradients, dirt masks
};

/** Every material name, for the load-time check in registry.js. */
export const MATERIALS = Object.keys(STRIPS);

// Never sample the outermost rows of a strip. The sheet is mipmapped so that
// distant modules do not shimmer along the tiling axis, and a mip level blends
// rows together — which across a strip boundary means a near-black screen
// bleeding into the pale glass above it. Two rows of headroom at each end keeps
// the blend inside the material it belongs to. Each strip is painted full
// height, so the guard rows are real content, just never sampled directly.
const GUARD = 2;

/** The V range of a strip, in UV space. Textures load with flipY = false. */
export function stripV(name) {
  const s = STRIPS[name];
  if (!s) {
    throw new Error(
      `trim sheet has no material "${name}" — known: ${MATERIALS.join(', ')}`
    );
  }
  const guard = Math.min(GUARD, Math.floor((s.h - 1) / 2));
  return { v0: (s.y + guard) / SHEET_H, v1: (s.y + s.h - guard) / SHEET_H };
}
