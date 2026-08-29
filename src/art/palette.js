// The limited palette. One source of truth.
// No hex literals anywhere else in the codebase (§4.4).
import { Color } from 'three';

const hex = {
  // neutrals — warm off-whites, the pharmacy's clinical-but-friendly base
  paper: '#f9efdc',
  bone: '#ecdcc0',
  putty: '#d3c3a4',
  backdrop: '#b9c4c0', // the room beyond the build area
  // The room commits to a colour. Every isometric diorama in the reference that
  // reads well does this: cool walls, a warmer floor, warm furniture against
  // them. A neutral room makes everything in it float.
  wall: '#aed6c2', // mint. Pushed hard, because a strong warm key washes a pale cool out
  floorTile: '#c9c2b2', // warm putty, so it separates from the wall

  // woods
  oak: '#dda265',
  oakDark: '#b0763e',
  walnut: '#835531',

  // accents — the shop's brand greens and a single warm signal colour
  mint: '#9ad9b8',
  teal: '#57a98d',
  tealDeep: '#356f5e',
  signal: '#f5804f', // the one properly saturated accent; used sparingly

  // metals / glass
  steel: '#b0bcbd',
  steelDark: '#77868a',
  glass: '#d2e8e4',

  // light
  keyWarm: '#fff3de',
  fillCool: '#bcd2ea',
  rim: '#ffdfb4',

  // Shading tints used by the vertex-mask ramps (§4.3). Both of the cool ones
  // were pulled back and warmed when the catalogue was rebuilt from the concept
  // sheets: every module roughly doubled its part count, so the cavity mask now
  // covers far more of every surface, and a tint that read as a nice cool
  // crevice on a plain box turned the whole room lilac on a detailed one. The
  // strength came down with it — see uCavityStrength in AdaptiveMaterial.
  shadowTint: '#6a5f6a', // cool, for cavity
  edgeLightTint: '#fff0d2', // warm, for convex edges
  dustTint: '#f2e6d0',

  // hemisphere ambient — cool from above, warm bounce from the floor
  sky: '#d6e6f4',
  ground: '#f6e2c4',
  // shadows carry a hue rather than just less light
  shadowCool: '#9c90a6',

  // ink — outlines and UI. A dark saturated shadow tone, never black (§7.3)
  ink: '#413353',
  ghost: '#8878a0',
};

// three's ColorManagement converts these sRGB hexes into the linear working
// space on construction — do not convert again, or every light picks up a cast.
export const PALETTE = Object.fromEntries(
  Object.entries(hex).map(([k, v]) => [k, new Color(v)])
);

/** Raw sRGB hex — for CSS and for the style-bible prompts of §11.1. */
export const PALETTE_HEX = hex;

export const color = (name) => {
  const c = PALETTE[name];
  if (!c) throw new Error(`palette: unknown colour "${name}"`);
  return c.clone();
};
