// The limited palette. One source of truth.
// No hex literals anywhere else in the codebase (§4.4).
import { Color } from 'three';

const hex = {
  // neutrals — warm off-whites, the pharmacy's clinical-but-friendly base
  paper: '#f2e6d2',
  bone: '#ded0b6',
  putty: '#c4b294',
  backdrop: '#a7aeaa', // the room beyond the build area
  floorTile: '#b6bdb2', // cool floor, so the warm furniture reads against it

  // woods
  oak: '#c98f4e',
  oakDark: '#9a6531',
  walnut: '#6b4325',

  // accents — the shop's brand greens and a single warm signal colour
  mint: '#7fbfa4',
  teal: '#3f8a76',
  tealDeep: '#27594c',
  signal: '#e0704a',

  // metals / glass
  steel: '#9aa6a8',
  steelDark: '#5e6b6e',
  glass: '#bfd8d6',

  // light
  keyWarm: '#fff0d6',
  fillCool: '#a9c0dd',
  rim: '#ffd39b',

  // shading tints used by the vertex-mask ramps (§4.3)
  shadowTint: '#3c3a4c', // cool, for cavity
  edgeLightTint: '#ffdcae', // warm, for convex edges
  dustTint: '#e8dcc4',

  // ink — outlines and UI. A dark saturated shadow tone, never black (§7.3)
  ink: '#2b1f33',
  ghost: '#6d5a7a',
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
