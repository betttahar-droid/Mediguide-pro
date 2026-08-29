// The generated 16-bit atlas, loaded with crisp-retro filtering.
//
// public/textures/nano-atlas.png comes from tools/authoring/nano_assets.py and
// is cleaned by tools/authoring/pixelate.py — 344x192, 32 colours, one texel
// per pixel. It is an irregular atlas: cells of different sizes separated by
// dark gutters, which is how the image model reads the word "atlas". So the
// cell table below is measured off the sheet rather than being a uniform grid,
// and every cell is inset by one texel so a UV never lands on a gutter.
import { TextureLoader, NearestFilter, RepeatWrapping, ClampToEdgeWrapping, SRGBColorSpace, Vector4 } from 'three';

export const ATLAS_URL = 'textures/nano-atlas.png';
export const ATLAS_W = 344;
export const ATLAS_H = 192;

/**
 * The sheet's cells, in TEXELS, as [x, y, w, h] from the top-left.
 *
 * Read off the cleaned sheet by eye. The generated atlas is 8 columns x 4 rows
 * of unequal cells, so this cannot be computed — it has to be measured, and it
 * has to be re-measured if the atlas is ever regenerated. That is the cost of
 * letting a model lay out the sheet, and it is worth naming rather than hiding
 * behind a grid function that would silently sample gutters.
 */
export const ATLAS_CELLS = {
  metal_panel: [0, 0, 43, 48], //      riveted green panel, the default carcass
  metal_panel_seam: [43, 0, 43, 48], //  the same with a horizontal seam
  wood_plank_h: [86, 0, 86, 48], //    warm plank run, grain across
  shelf_green: [172, 0, 86, 48], //    open shelf with two boards
  wood_door_pair: [258, 0, 43, 48], //  two tall wooden doors
  shelf_narrow: [301, 0, 43, 48],

  metal_double: [0, 48, 86, 48], //    two-leaf green panel
  wood_plank_v: [86, 48, 86, 48], //   plank run, grain along
  shelf_stacked: [172, 48, 43, 48],
  drawers_2x2: [215, 48, 86, 48], //   four drawers with pulls
  bench_green: [301, 48, 43, 48],

  shelf_boards: [0, 96, 86, 48],
  wood_board_wide: [86, 96, 86, 48],
  drawers_label: [172, 96, 86, 48], //  drawers with label holders
  bottles_shelf: [258, 96, 86, 48], //  a stocked apothecary shelf
  bottles_label: [301, 96, 43, 48],

  metal_tall: [0, 144, 86, 48],
  drawers_3: [86, 144, 43, 48], //     a stack of three drawers
  counter_wood: [129, 144, 86, 48], //  worktop over a green carcass
  counter_plain: [215, 144, 86, 48],
  bench_tools: [301, 144, 43, 48], //   mortar, tools, a tray
};

/**
 * UV transform for a cell: (offsetX, offsetY, repeatX, repeatY).
 *
 * Inset by a texel on every side. Nothing here is mipmapped, but a UV that
 * lands exactly on a cell boundary still picks up the neighbour under
 * bilinear-free NearestFilter once the geometry is scaled, and the gutters on
 * this sheet are near-black — one texel of that on the edge of a worktop reads
 * as a dirty line.
 */
export function cellUv(name, inset = 1) {
  const cell = ATLAS_CELLS[name];
  if (!cell) {
    throw new Error(`nano atlas has no cell "${name}" — known: ${Object.keys(ATLAS_CELLS).join(', ')}`);
  }
  const [x, y, w, h] = cell;
  return new Vector4(
    (x + inset) / ATLAS_W,
    // three's UV origin is bottom-left and the cell table is measured from the
    // top, so flip. Getting this wrong samples a different cell entirely.
    1 - (y + h - inset) / ATLAS_H,
    (w - inset * 2) / ATLAS_W,
    (h - inset * 2) / ATLAS_H
  );
}

let cached = null;
let readyPromise = null;

/**
 * The atlas texture, configured for pixel art.
 *
 * These four settings are the whole crisp-retro contract and each one matters:
 *
 *   magFilter NearestFilter    a texel magnified is a hard square, not a blur.
 *                              This is the one that makes it look 16-bit.
 *   minFilter NearestFilter    no averaging when minified either.
 *   generateMipmaps false      required — a mipmapped texture with a NEAREST
 *                              minFilter and no mip chain renders BLACK in
 *                              WebGL, so these two go together or not at all.
 *   colorSpace SRGB            the sheet is authored in sRGB; three decodes it
 *                              to linear on sample. Skipping this is what makes
 *                              a scene read dull — see docs/style-bible.md.
 *
 * The cost is aliasing: with no mip chain a distant, minified prop shimmers as
 * the camera moves, because each pixel takes one texel from wherever it lands
 * rather than an average of the ones it covers. That is the authentic retro
 * behaviour and it is the trade the style asks for; `sharedTextures()` in
 * art/textures.js keeps mipmaps for the trim sheet, which is sampled across
 * whole rooms and would shimmer badly without them.
 */
export function nanoAtlas() {
  if (!cached) {
    const loader = new TextureLoader();
    let resolve;
    readyPromise = new Promise((r) => { resolve = r; });
    cached = loader.load(ATLAS_URL, resolve, undefined, (err) => {
      console.error(`nano atlas failed to load: ${ATLAS_URL}`, err);
      resolve();
    });
    cached.magFilter = NearestFilter;
    cached.minFilter = NearestFilter;
    cached.generateMipmaps = false;
    cached.colorSpace = SRGBColorSpace;
    // A cell is a sub-rectangle, so a UV outside it must not wrap into the
    // neighbouring cell; the sheet as a whole may still tile on U for a plank
    // run, which is what setCellRepeat() below opts into.
    cached.wrapS = ClampToEdgeWrapping;
    cached.wrapT = ClampToEdgeWrapping;
    cached.flipY = false;
  }
  return cached;
}

/** Resolves once the sheet has decoded — the smoke test waits on this. */
export function nanoAtlasReady() {
  nanoAtlas();
  return readyPromise;
}

/** Let a cell tile along U, for a plank run on a stretched worktop. */
export function setCellRepeat(texture, wrap = RepeatWrapping) {
  texture.wrapS = wrap;
  return texture;
}
