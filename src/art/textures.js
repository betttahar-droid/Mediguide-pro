// The project's textures, loaded from public/textures/.
//
// They are authored offline by tools/authoring/make_textures.py and committed
// as PNGs (§11: the generation workflow is manual and produces files; it is
// never a build, CI, or runtime dependency). Nothing here draws.
//
// Every sheet is painted as LUMINANCE around mid-grey and tinted by palette.js
// at sample time, which is what holds the limited palette across a catalogue
// authored in separate passes (§4.4).
import { TextureLoader, RepeatWrapping, NearestFilter, NearestMipmapLinearFilter, SRGBColorSpace, NoColorSpace } from 'three';

const loader = new TextureLoader();
const pending = [];

function load(url, { colorSpace = SRGBColorSpace, anisotropy = 8 } = {}) {
  let resolve;
  pending.push(new Promise((r) => { resolve = r; }));
  const tex = loader.load(url, resolve, undefined, (err) => {
    console.error(`texture failed to load: ${url}`, err);
    resolve();
  });
  tex.wrapS = RepeatWrapping;
  tex.wrapT = RepeatWrapping;
  // V indexes the trim sheet's strip table, so the image must not be flipped
  tex.flipY = false;
  tex.colorSpace = colorSpace;
  tex.anisotropy = anisotropy;
  // Pixel art: NEAREST on magnification is the whole look. Mipmaps stay linear
  // between levels so distant modules do not shimmer, which is the one place
  // sharpness costs more than it buys.
  tex.minFilter = NearestMipmapLinearFilter;
  tex.magFilter = NearestFilter;
  return tex;
}

let shared = null;

/** One set of textures for the whole app. */
export function sharedTextures() {
  if (!shared) {
    shared = {
      trim: load('textures/trim.png'), // Tier B — one-axis trim sheet
      atlas: load('textures/atlas.png'), // Tier A — unique UV
      tiling: load('textures/tiling.png'), // Tier C — triplanar
      hatch: load('textures/hatch.png', { colorSpace: NoColorSpace }), // a mask
    };
  }
  return shared;
}

/** Resolves once every sheet is decoded — the smoke test waits on this. */
export function texturesReady() {
  sharedTextures();
  return Promise.all(pending);
}
