// §D1 — the unique-UV atlas: one texel grid for the whole catalogue.
//
// WHY THIS EXISTS
//
// The reference set (docs/reference/, and the reception scene the user supplied
// with its 64x128 sheet visible in the corner) is not textured the way this
// project was. Every face there is unwrapped into ONE shared hand-painted sheet,
// so a filing-cabinet drawer front can carry grey metal, a dark recessed label
// slot, a white label and a chrome pull as PAINT on a single flat plane.
//
// Tier B could never do that. The trim sheet is greyscale detail modulating one
// per-part colour uniform, so a face is one hue by construction, and anything
// that needed a second colour had to become a second box — which at 3 cm texels
// is smaller than a texel. That is the same finding the style bible keeps
// arriving at from different directions ("print is a big flat area, not small
// geometry"; "ornament has to earn the distance"). It is not an art-direction
// failure, it is the material model pushing back.
//
// So: every face gets its own rectangle of a shared atlas, at a FIXED texel
// density, and the atlas carries colour. bevelBox already emits planar 0..1 UVs
// per face — the unwrap is done, the faces just all sit on top of each other.
// This file is what spreads them out.
//
// WHY DENSITY IS FIXED AND NOT PER-OBJECT
//
// The old Tier B/C mapping is repeats-per-metre (uTrimDensity, uTextureScale),
// so a small prop and a big carcass get visibly different texel sizes and the
// set never reads as one thing. Allocating by world size at a constant
// texels-per-metre is the entire fix, and it is why the reference's props look
// like they came out of the same box of Lego.

/**
 * Texels per world metre.
 *
 * 32 puts a texel at 3.1 cm. The style bible's stated target is ~2 cm (50/m),
 * but that was written against the tiling sheet, where density only had to look
 * right — here it multiplies out into real atlas area, and 50/m roughly doubles
 * it. 32 is the value that keeps the whole catalogue inside one 2048 sheet
 * while still reading as chunky Minecraft-ish texels at playing distance.
 *
 * Changing this changes the look. It is the single most important number in the
 * new pipeline: too high and the props stop reading as pixel art, too low and
 * the painted marks have no room to be drawn in.
 */
export const TEXELS_PER_METRE = 32;

/**
 * Guard texels around every island.
 *
 * Same reasoning as trimLayout's GUARD, for the same failure: the atlas is
 * mipmapped so distant modules do not shimmer, and a mip level blends
 * neighbouring texels — which across an island boundary means one part's
 * near-black screen bleeding onto the pale panel packed next to it. One texel
 * of padding is enough at the mip levels this atlas actually reaches; the
 * painter fills it by extending the island's edge texels outward (§D2), so the
 * blend samples the island's own colour rather than the gutter.
 */
export const ISLAND_PAD = 1;

/** No face gets less than this. A 1x1 island cannot carry a drawn mark. */
const MIN_ISLAND = 2;

/**
 * Shelf packer, allocating left-to-right along a row and starting a new row
 * when the current one fills.
 *
 * Deliberately streaming rather than sort-then-pack: islands are allocated
 * during geometry construction, inside bevelBox, at the one moment the face's
 * world size and its material are both known. Collecting every rect first and
 * packing optimally afterwards would mean either building all geometry twice or
 * threading an allocation id through the whole build — and shelf packing wastes
 * only the ragged right-hand end of each row, which at these island sizes is a
 * few percent. Measured occupancy for the full catalogue is printed by
 * tools/authoring/atlas_report.mjs.
 */
export class AtlasPacker {
  /**
   * @param {{texelsPerMetre?: number, width?: number}} opts
   *   width — atlas width in texels. Height grows as rows are added and is
   *   rounded up to a power of two by finish().
   */
  constructor({ texelsPerMetre = TEXELS_PER_METRE, width = 2048 } = {}) {
    this.texelsPerMetre = texelsPerMetre;
    this.width = width;
    this.rects = [];
    this._x = 0;
    this._y = 0;
    this._rowH = 0;
  }

  /** Texel size of a face that measures `metres` across, floor-clamped. */
  texels(metres) {
    return Math.max(MIN_ISLAND, Math.round(metres * this.texelsPerMetre));
  }

  /**
   * Allocate an island for one face.
   *
   * @param {number} wMetres face width in world metres (the U axis)
   * @param {number} hMetres face height in world metres (the V axis)
   * @param {object} meta what the painter needs to draw this island: at least
   *   { mat, accent }, plus whatever the caller knows about the face — its axis,
   *   its sign, and the module and part it belongs to. Carried through
   *   untouched; nothing in this file reads it.
   * @returns {{x:number, y:number, w:number, h:number, index:number}} the island
   *   in TEXELS, excluding padding.
   */
  alloc(wMetres, hMetres, meta = {}) {
    const w = this.texels(wMetres);
    const h = this.texels(hMetres);
    const stride = w + ISLAND_PAD * 2;

    if (this._x + stride > this.width) {
      // Row full: drop to the next shelf. The old row's leftover right-hand
      // strip is the packer's only waste.
      this._y += this._rowH;
      this._x = 0;
      this._rowH = 0;
    }

    const rect = {
      x: this._x + ISLAND_PAD,
      y: this._y + ISLAND_PAD,
      w,
      h,
      index: this.rects.length,
      meta,
    };
    this.rects.push(rect);

    this._x += stride;
    this._rowH = Math.max(this._rowH, h + ISLAND_PAD * 2);
    return rect;
  }

  /** Total atlas height needed, including the row in progress. */
  get height() {
    return this._y + this._rowH;
  }

  /**
   * Close the atlas and report its final size.
   *
   * Height is rounded to a power of two so the texture mips cleanly; three will
   * silently resize a non-power-of-two texture that asks for mipmaps, and a
   * silent resize would resample every island and undo the whole point of
   * NearestFilter.
   */
  finish() {
    const height = Math.max(1, nextPow2(this.height));
    return {
      width: this.width,
      height,
      rects: this.rects,
      texelsPerMetre: this.texelsPerMetre,
      /** Fraction of the sheet that is island rather than gutter or offcut. */
      occupancy:
        this.rects.reduce((sum, r) => sum + r.w * r.h, 0) /
        (this.width * height),
    };
  }
}

const nextPow2 = (n) => {
  let p = 1;
  while (p < n) p *= 2;
  return p;
};

/**
 * Map a face-local 0..1 coordinate into an island, in UV space.
 *
 * Sampling happens at texel CENTRES: an island's usable UV span runs from its
 * first texel's centre to its last texel's centre, not from its outer edges. At
 * NearestFilter with an island only a few texels wide, using the edges instead
 * puts the 0 and 1 ends of the face exactly on a texel boundary, where a hair
 * of interpolation error picks the neighbouring texel — i.e. the gutter. This
 * half-texel inset is the difference between a clean painted border and one
 * that flickers along the seam as the camera moves.
 */
export function islandUv(rect, atlas, u, v) {
  const x = (rect.x + 0.5 + u * (rect.w - 1)) / atlas.width;
  const y = (rect.y + 0.5 + v * (rect.h - 1)) / atlas.height;
  return [x, y];
}
