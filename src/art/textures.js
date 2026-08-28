// §4.1 / §11.5 — the project's textures.
//
// The brief authors these by hand and commits them to public/textures. Nothing
// here is hand-painted: they are procedural stand-ins with the *correct layout
// and tiling behaviour*, so the material system is exercised for real and the
// files can be swapped for painted ones without touching a shader.
//
// They are authored as luminance detail around mid-grey and tinted by
// palette.js at sample time, which guarantees the limited palette holds across
// the catalogue (§4.4) — a painted albedo sheet would replace that multiply.
import { CanvasTexture, RepeatWrapping, LinearFilter, SRGBColorSpace, NoColorSpace } from 'three';

/** Standard trim sheet layout, §4.1. Rows run top-down; textures use flipY=false. */
export const STRIPS = {
  edge: { y: 0, h: 64 }, // painted bevels, borders
  detail: { y: 64, h: 128 }, // screw heads, panel seams, label holders
  surface: { y: 192, h: 512 }, // painted wood, laminate, painted metal
  transition: { y: 704, h: 128 }, // wear gradients, dirt masks
  alpha: { y: 832, h: 192 }, // cutouts — grilles, handles
};
export const SHEET = 1024;

/** Centre of a strip in UV space, and its half-height — used to bake aTrimV. */
export const stripV = (name) => {
  const s = STRIPS[name];
  return { v0: s.y / SHEET, v1: (s.y + s.h) / SHEET };
};

// Deterministic noise so every run produces the same sheet.
function rng(seed = 1) {
  let s = seed >>> 0;
  return () => (((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296));
}

function canvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  return { c, ctx: c.getContext('2d') };
}

/** Draw fn three times so anything crossing the seam wraps horizontally. */
function wrapX(ctx, w, draw) {
  for (const dx of [-w, 0, w]) {
    ctx.save();
    ctx.translate(dx, 0);
    draw();
    ctx.restore();
  }
}

function brushStrokes(ctx, { x0, y0, w, h, count, seed, length, thickness, light, dark }) {
  const rand = rng(seed);
  for (let i = 0; i < count; i++) {
    const x = x0 + rand() * w;
    const y = y0 + rand() * h;
    const len = length * (0.4 + rand() * 1.2);
    const t = thickness * (0.5 + rand());
    const tilt = (rand() - 0.5) * 0.08;
    ctx.strokeStyle = rand() > 0.5 ? light : dark;
    ctx.globalAlpha = 0.03 + rand() * 0.10;
    ctx.lineWidth = t;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + len, y + len * tilt);
    ctx.stroke();
  }
  ctx.globalAlpha = 1;
}

/**
 * The one 1024² trim sheet for the whole project. Tiles horizontally only:
 * U runs along the stretch axis, V selects the strip (§4.1 Tier B).
 */
export function makeTrimSheet() {
  const { c, ctx } = canvas(SHEET, SHEET);
  ctx.fillStyle = '#808080';
  ctx.fillRect(0, 0, SHEET, SHEET);

  // --- surface strip: painted wood / laminate --------------------------
  const s = STRIPS.surface;
  ctx.fillStyle = '#7d7d7d';
  ctx.fillRect(0, s.y, SHEET, s.h);
  wrapX(ctx, SHEET, () =>
    brushStrokes(ctx, {
      x0: 0, y0: s.y, w: SHEET, h: s.h, count: 900, seed: 7,
      length: 220, thickness: 3.5, light: '#a5a5a5', dark: '#5f5f5f',
    })
  );
  // long grain
  const grain = rng(21);
  wrapX(ctx, SHEET, () => {
    for (let i = 0; i < 130; i++) {
      const y = s.y + grain() * s.h;
      ctx.strokeStyle = grain() > 0.5 ? '#8f8f8f' : '#6d6d6d';
      ctx.globalAlpha = 0.06 + grain() * 0.12;
      ctx.lineWidth = 0.8 + grain() * 1.8;
      ctx.beginPath();
      ctx.moveTo(-40, y);
      for (let x = -40; x <= SHEET + 40; x += 64) ctx.lineTo(x, y + Math.sin(x * 0.01 + i) * 2.2);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  });
  // panel seams every quarter — these are what read when the middle stretches
  for (const x of [0, 256, 512, 768]) {
    ctx.fillStyle = '#5a5a5a';
    ctx.fillRect(x - 1.5, s.y, 3, s.h);
    ctx.fillStyle = '#9c9c9c';
    ctx.fillRect(x + 1.5, s.y, 2, s.h);
  }

  // --- edge trim: a painted bevel read across the strip -----------------
  {
    const e = STRIPS.edge;
    const g = ctx.createLinearGradient(0, e.y, 0, e.y + e.h);
    g.addColorStop(0.0, '#585858');
    g.addColorStop(0.22, '#767676');
    g.addColorStop(0.5, '#b4b4b4'); // the lit crest of the bevel
    g.addColorStop(0.78, '#8a8a8a');
    g.addColorStop(1.0, '#606060');
    ctx.fillStyle = g;
    ctx.fillRect(0, e.y, SHEET, e.h);
    wrapX(ctx, SHEET, () =>
      brushStrokes(ctx, {
        x0: 0, y0: e.y, w: SHEET, h: e.h, count: 220, seed: 3,
        length: 90, thickness: 2, light: '#d0d0d0', dark: '#4a4a4a',
      })
    );
  }

  // --- detail strip: screws, seams, a label holder ----------------------
  {
    const d = STRIPS.detail;
    ctx.fillStyle = '#7a7a7a';
    ctx.fillRect(0, d.y, SHEET, d.h);
    const mid = d.y + d.h / 2;
    for (let x = 32; x < SHEET; x += 128) {
      // screw head
      ctx.fillStyle = '#5c5c5c';
      ctx.beginPath();
      ctx.arc(x, mid, 9, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#9e9e9e';
      ctx.beginPath();
      ctx.arc(x - 1.5, mid - 1.5, 6.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#4f4f4f';
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.moveTo(x - 5, mid - 3);
      ctx.lineTo(x + 5, mid + 3);
      ctx.stroke();
    }
    // label holder rail
    ctx.fillStyle = '#6b6b6b';
    ctx.fillRect(0, d.y + d.h - 26, SHEET, 18);
    ctx.fillStyle = '#a8a8a8';
    ctx.fillRect(0, d.y + d.h - 26, SHEET, 4);
  }

  // --- transition: wear gradient ---------------------------------------
  {
    const t = STRIPS.transition;
    const g = ctx.createLinearGradient(0, t.y, 0, t.y + t.h);
    g.addColorStop(0, '#8c8c8c');
    g.addColorStop(1, '#5b5b5b');
    ctx.fillStyle = g;
    ctx.fillRect(0, t.y, SHEET, t.h);
    wrapX(ctx, SHEET, () =>
      brushStrokes(ctx, {
        x0: 0, y0: t.y, w: SHEET, h: t.h, count: 300, seed: 11,
        length: 140, thickness: 6, light: '#a0a0a0', dark: '#4c4c4c',
      })
    );
  }

  // --- alpha: grille cutouts (unused until a module needs one) ----------
  {
    const a = STRIPS.alpha;
    ctx.fillStyle = '#3d3d3d';
    ctx.fillRect(0, a.y, SHEET, a.h);
    ctx.fillStyle = '#c8c8c8';
    for (let x = 0; x < SHEET; x += 48) ctx.fillRect(x + 8, a.y + 24, 26, a.h - 48);
  }

  const tex = new CanvasTexture(c);
  tex.wrapS = RepeatWrapping;
  tex.wrapT = RepeatWrapping;
  tex.flipY = false; // so V maps straight to the strip table above
  tex.colorSpace = SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

/**
 * Tier A atlas — 2×2 painted panels. Cap regions sample this with the mesh's
 * own UVs, so the border and corner wear sit in a specific place.
 */
export function makeAtlas() {
  const size = 512;
  const cell = size / 2;
  const { c, ctx } = canvas(size, size);
  const panels = [
    { base: '#828282', border: '#5e5e5e', seed: 5 },
    { base: '#8a8a8a', border: '#666666', seed: 17 },
    { base: '#787878', border: '#565656', seed: 29 },
    { base: '#868686', border: '#616161', seed: 41 },
  ];
  panels.forEach((p, i) => {
    const x = (i % 2) * cell;
    const y = Math.floor(i / 2) * cell;
    ctx.save();
    ctx.beginPath();
    ctx.rect(x, y, cell, cell);
    ctx.clip();
    ctx.fillStyle = p.base;
    ctx.fillRect(x, y, cell, cell);
    brushStrokes(ctx, {
      x0: x, y0: y, w: cell, h: cell, count: 260, seed: p.seed,
      length: 90, thickness: 5, light: '#a6a6a6', dark: '#606060',
    });
    // painted inset border — the positional detail a trim sheet cannot give
    ctx.strokeStyle = p.border;
    ctx.lineWidth = 7;
    ctx.strokeRect(x + 16, y + 16, cell - 32, cell - 32);
    ctx.strokeStyle = '#a3a3a3';
    ctx.lineWidth = 2.5;
    ctx.strokeRect(x + 21, y + 21, cell - 42, cell - 42);
    // corner scuffs, where hands and trolleys land
    const rand = rng(p.seed + 100);
    for (const [cx, cy] of [[x + 18, y + 18], [x + cell - 18, y + cell - 18], [x + cell - 22, y + 20]]) {
      ctx.globalAlpha = 0.32;
      ctx.fillStyle = '#b8b8b8';
      for (let k = 0; k < 22; k++) {
        ctx.beginPath();
        ctx.arc(cx + (rand() - 0.5) * 40, cy + (rand() - 0.5) * 40, 1 + rand() * 3.5, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    }
    ctx.restore();
  });

  const tex = new CanvasTexture(c);
  tex.wrapS = tex.wrapT = RepeatWrapping;
  tex.flipY = false;
  tex.colorSpace = SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

/** Tier C — tiles on both axes, for the triplanar floor/wall path (§6). */
export function makeTilingSurface() {
  const size = 512;
  const { c, ctx } = canvas(size, size);
  ctx.fillStyle = '#8a8a8a';
  ctx.fillRect(0, 0, size, size);
  const rand = rng(97);
  // speckle first, so grout sits on top and stays crisp
  for (let i = 0; i < 9000; i++) {
    ctx.globalAlpha = 0.05 + rand() * 0.2;
    ctx.fillStyle = rand() > 0.5 ? '#9f9f9f' : '#767676';
    ctx.fillRect(rand() * size, rand() * size, 1 + rand() * 3, 1 + rand() * 3);
  }
  ctx.globalAlpha = 1;
  const tile = size / 4;
  ctx.strokeStyle = '#565656';
  ctx.lineWidth = 6;
  for (let i = 0; i <= 4; i++) {
    ctx.beginPath();
    ctx.moveTo(i * tile, 0); ctx.lineTo(i * tile, size);
    ctx.moveTo(0, i * tile); ctx.lineTo(size, i * tile);
    ctx.stroke();
  }
  ctx.strokeStyle = '#adadad';
  ctx.lineWidth = 2;
  for (let i = 0; i <= 4; i++) {
    ctx.beginPath();
    ctx.moveTo(i * tile + 3, 0); ctx.lineTo(i * tile + 3, size);
    ctx.moveTo(0, i * tile + 3); ctx.lineTo(size, i * tile + 3);
    ctx.stroke();
  }
  const tex = new CanvasTexture(c);
  tex.wrapS = tex.wrapT = RepeatWrapping;
  tex.flipY = false;
  tex.colorSpace = SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

/**
 * §4.5 — cross-hatching, sampled with the albedo's own coordinates so it is
 * locked to the surface rather than to the screen. Three densities in RGB;
 * the shader picks a channel from the lighting term.
 */
export function makeHatch() {
  const size = 256;
  const { c, ctx } = canvas(size, size);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, size, size);
  const strokes = (channel, spacing, angle, width) => {
    ctx.save();
    ctx.globalCompositeOperation = 'multiply';
    ctx.strokeStyle = channel;
    ctx.lineWidth = width;
    ctx.translate(size / 2, size / 2);
    ctx.rotate(angle);
    ctx.translate(-size / 2, -size / 2);
    for (let i = -size; i < size * 2; i += spacing) {
      ctx.beginPath();
      ctx.moveTo(i, -size);
      ctx.lineTo(i, size * 2);
      ctx.stroke();
    }
    ctx.restore();
  };
  // red channel = lightest hatch, blue = densest
  strokes('#00ffff', 26, Math.PI / 4, 3.0); // clears R
  strokes('#ff00ff', 15, Math.PI / 4, 3.0); // clears G
  strokes('#ffff00', 15, -Math.PI / 4, 3.0); // clears B, crossing the other way
  strokes('#ffff00', 9, Math.PI / 4, 2.0);

  const tex = new CanvasTexture(c);
  tex.wrapS = tex.wrapT = RepeatWrapping;
  tex.flipY = false;
  tex.colorSpace = NoColorSpace; // a mask, not colour
  tex.minFilter = LinearFilter;
  return tex;
}

let shared = null;
/** One set of textures for the whole app. */
export function sharedTextures() {
  if (!shared) {
    shared = {
      trim: makeTrimSheet(),
      atlas: makeAtlas(),
      tiling: makeTilingSurface(),
      hatch: makeHatch(),
    };
  }
  return shared;
}
