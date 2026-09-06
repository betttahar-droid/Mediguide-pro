import {
  BoxGeometry, Group, Mesh, Vector3,
} from 'three';
import {
  createAnalyticBoxMaterial,
  updateAnalyticBoxScale,
} from '../shaders/index.js';

// One invariant style unit. Structural geometry is always a W/H/D fraction;
// only borders, fittings and their offsets may use this fixed world measure.
export const STRICT_STYLE_UNIT = 1 / 32;

export const STRICT_SDF_STYLE = Object.freeze({
  pixelsPerUnit: 32,
  tints: Object.freeze({ top: 1.09, front: 1, side: 0.858, back: 0.9, bottom: 0.74 }),
  rules: Object.freeze({
    outline: STRICT_STYLE_UNIT,
    catchWidth: STRICT_STYLE_UNIT * 2,
    inset: STRICT_STYLE_UNIT * 4,
    seamWidth: STRICT_STYLE_UNIT * 0.75,
    gatePadding: STRICT_STYLE_UNIT,
  }),
  palette: Object.freeze({
    cream: Object.freeze(['#dbc9a8', '#a89a81', '#fff4cc', '#6b665d']),
    steel: Object.freeze(['#617a80', '#4a5d62', '#76949c', '#38474a']),
    teal: Object.freeze(['#0d403b', '#0a312d', '#10504a', '#071e1c']),
    glass: Object.freeze(['#123f3b', '#0a2927', '#246a62', '#061a19']),
    plum: Object.freeze(['#2d1738', '#1b0d23', '#4a2a59', '#100817']),
    ochre: Object.freeze(['#c58b42', '#845a2c', '#e1aa5c', '#55371f']),
    display: Object.freeze(['#16272a', '#0c1517', '#31575b', '#070c0d']),
  }),
});

const RATIOS = Object.freeze({
  frameRailW: 3 / 38.75,
  frameTopH: 5 / 96,
  frameBottomH: 2 / 96,
  crownH: 5.55 / 96,
  roofW: 31.4 / 38.75,
  roofD: 27.5 / 36.75,
  roofH: 1.5 / 96,
  doorBottom: 22 / 96,
  doorTop: 82 / 96,
  doorWidth: 30 / 38.75,
  glassWidthInDoor: 24 / 30,
  glassBottom: 27 / 96,
  glassTop: 79 / 96,
  condenserBottom: 3.25 / 96,
  condenserTop: 19 / 96,
  grilleWidth: 26 / 38.75,
  grilleBottom: 5 / 96,
  grilleTop: 16 / 96,
  shelfThickness: 1.5 / 96,
  shelfDepth: 23 / 36.75,
});

function materialOptions(role, rule = 'structural', opacity = 1) {
  const [baseColor, shadowColor, highlightColor, outlineColor] = STRICT_SDF_STYLE.palette[role];
  const panel = rule === 'panel';
  const flat = rule === 'flat';
  return {
    baseColor,
    shadowColor,
    highlightColor,
    outlineColor,
    tints: STRICT_SDF_STYLE.tints,
    outline: flat ? 0 : STRICT_SDF_STYLE.rules.outline,
    catchWidth: flat ? 0 : STRICT_SDF_STYLE.rules.catchWidth,
    inset: STRICT_SDF_STYLE.rules.inset,
    seamWidth: STRICT_SDF_STYLE.rules.seamWidth,
    gatePadding: STRICT_SDF_STYLE.rules.gatePadding,
    insetEnabled: panel,
    opacity,
  };
}

function box(name, role, size, at, { rule = 'structural', opacity = 1, kind = 'structure' } = {}) {
  const geometry = new BoxGeometry(size.x, size.y, size.z, 1, 1, 1);
  geometry.deleteAttribute('uv');
  geometry.computeBoundingBox();
  const material = createAnalyticBoxMaterial({
    boundsMin: geometry.boundingBox.min,
    boundsMax: geometry.boundingBox.max,
    ...materialOptions(role, rule, opacity),
  });
  const mesh = new Mesh(geometry, material);
  mesh.name = name;
  mesh.position.copy(at);
  mesh.userData.strictSdf = true;
  mesh.userData.role = role;
  mesh.userData.partKind = kind;
  mesh.userData.materialRule = rule;
  mesh.userData.dimensionPolicy = kind === 'structure' ? 'fraction_of_W_H_D' : 'fixed_style_units';
  mesh.onBeforeRender = () => updateAnalyticBoxScale(material, mesh);
  return mesh;
}

function addFrontBox(parts, name, role, width, height, depth, x, z, D, options = {}) {
  const layer = (options.layer ?? 1) * STRICT_STYLE_UNIT;
  parts.push(box(name, role, new Vector3(width, depth, height),
    new Vector3(x, -D / 2 - depth / 2 - layer, z), options));
}

function hardware(parts, prefix, panel, D, layer = 5) {
  const U = STRICT_STYLE_UNIT;
  const size = U * 0.72;
  const margin = U * 1.35;
  let index = 0;
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
    addFrontBox(parts, `${prefix}_rivet_${index}`, 'plum', size, size, U * 0.35,
      panel.x + sx * (panel.width / 2 - margin),
      panel.z + sz * (panel.height / 2 - margin), D,
      { rule: 'flat', kind: 'hardware', layer });
    index += 1;
  }
}

function addDisplay(parts, W, H, D) {
  const U = STRICT_STYLE_UNIT;
  const width = U * 13;
  const height = U * 4;
  // Top-right anchor with fixed dimensions and fixed offsets.
  const x = W / 2 - U * 4 - width / 2;
  const z = H - U * 4 - height / 2;
  addFrontBox(parts, 'strict_display_plate', 'display', width, height, U * 0.6,
    x, z, D, { rule: 'structural', kind: 'fitting', layer: 6 });
  const pixels = [
    [-4, 0, 'ochre'], [-1, 0, 'cream'], [2, 0, 'teal'], [4, 0, 'cream'],
  ];
  pixels.forEach(([dx, dz, role], index) => {
    addFrontBox(parts, `strict_display_pixel_${index}`, role, U, U, U * 0.25,
      x + dx * U, z + dz * U, D,
      { rule: 'flat', kind: 'fitting', layer: 7 });
  });
}

function addHandle(parts, bayWidth, H, D, doorIndex, doorCenter) {
  const U = STRICT_STYLE_UNIT;
  const gripWidth = U * 2.5;
  const gripHeight = U * 15;
  const gripDepth = U * 1.4;
  // Left-edge/top anchor. Door index only selects which complete bay owns it.
  const x = doorCenter - bayWidth / 2 - U * 1.5;
  const z = H - U * 34 - gripHeight / 2;
  addFrontBox(parts, `strict_handle_${doorIndex}`, 'plum', gripWidth, gripHeight,
    gripDepth, x, z, D, { rule: 'structural', kind: 'fitting', layer: 8 });
  for (const direction of [-1, 1]) {
    addFrontBox(parts, `strict_handle_mount_${doorIndex}_${direction}`, 'cream',
      U * 2.5, U * 2, U * 1.2, x, z + direction * (gripHeight / 2 - U), D,
      { rule: 'flat', kind: 'fitting', layer: 7 });
  }
}

function addGrille(parts, W, H, D) {
  const U = STRICT_STYLE_UNIT;
  const width = W * RATIOS.grilleWidth;
  const height = H * (RATIOS.grilleTop - RATIOS.grilleBottom);
  const z = H * (RATIOS.grilleTop + RATIOS.grilleBottom) / 2;
  addFrontBox(parts, 'strict_grille_panel', 'ochre', width, height, U,
    0, z, D, { rule: 'structural', layer: 4 });

  // Every louvre is real fixed-size geometry. Wider cabinets gain more slots.
  const sideMargin = U * 2;
  const pitch = U * 4;
  const louvreWidth = U * 2;
  const louvreHeight = height - U * 4;
  const count = Math.max(1, Math.floor((width - sideMargin * 2) / pitch));
  const occupied = (count - 1) * pitch;
  for (let index = 0; index < count; index += 1) {
    const x = -occupied / 2 + index * pitch;
    addFrontBox(parts, `strict_grille_louvre_${index}`, 'display', louvreWidth,
      louvreHeight, U * 0.45, x, z, D,
      { rule: 'flat', kind: 'repeated_structure', layer: 5 });
  }
  return count;
}

/** Generate a textureless, axis-aligned refrigerator in local Z-up space. */
export function generateStrictSdfFridge(W, H, D, { doorCount = 1 } = {}) {
  if (!(W > 0 && H > 0 && D > 0)) throw new Error('W, H and D must be positive');
  const doors = Math.max(1, Math.round(doorCount));
  const U = STRICT_STYLE_UNIT;
  const parts = [];

  const sideWall = W * (1 / 38.75);
  const backWall = D * (1 / 36.75);
  parts.push(box('strict_body_back', 'steel', new Vector3(W, backWall, H),
    new Vector3(0, D / 2 - backWall / 2, H / 2), { rule: 'panel' }));
  for (const direction of [-1, 1]) {
    parts.push(box(`strict_body_side_${direction}`, 'steel', new Vector3(sideWall, D, H),
      new Vector3(direction * (W / 2 - sideWall / 2), 0, H / 2), { rule: 'panel' }));
  }

  const crownHeight = H * RATIOS.crownH;
  parts.push(box('strict_crown', 'cream', new Vector3(W, D, crownHeight),
    new Vector3(0, 0, H - crownHeight / 2), { rule: 'structural' }));
  const roofHeight = H * RATIOS.roofH;
  parts.push(box('strict_roof', 'cream',
    new Vector3(W * RATIOS.roofW, D * RATIOS.roofD, roofHeight),
    new Vector3(0, 0, H + roofHeight / 2), { rule: 'panel' }));

  const condenserBottom = H * RATIOS.condenserBottom;
  const condenserTop = H * RATIOS.condenserTop;
  addFrontBox(parts, 'strict_condenser', 'teal', W, condenserTop - condenserBottom,
    D * (0.8 / 36.75), 0, (condenserBottom + condenserTop) / 2, D,
    { rule: 'panel', layer: 2 });
  const louvreCount = addGrille(parts, W, H, D);

  const frameSide = W * RATIOS.frameRailW;
  const frameTop = H * RATIOS.frameTopH;
  const frameBottom = H * RATIOS.frameBottomH;
  const doorBottom = H * RATIOS.doorBottom;
  const doorTop = H * RATIOS.doorTop;
  const doorHeight = doorTop - doorBottom;
  const completeDoorWidth = W * RATIOS.doorWidth;
  const bayWidth = completeDoorWidth / doors;
  const railWidth = bayWidth * (3 / 30);
  const glassWidth = bayWidth * RATIOS.glassWidthInDoor;
  const glassBottom = H * RATIOS.glassBottom;
  const glassTop = H * RATIOS.glassTop;
  const glassHeight = glassTop - glassBottom;

  addFrontBox(parts, 'strict_frame_left', 'cream', frameSide, doorHeight, D * (0.4 / 36.75),
    -completeDoorWidth / 2 - frameSide / 2, (doorBottom + doorTop) / 2, D,
    { rule: 'structural', layer: 3 });
  addFrontBox(parts, 'strict_frame_right', 'cream', frameSide, doorHeight, D * (0.4 / 36.75),
    completeDoorWidth / 2 + frameSide / 2, (doorBottom + doorTop) / 2, D,
    { rule: 'structural', layer: 3 });
  addFrontBox(parts, 'strict_frame_top', 'cream', completeDoorWidth, frameTop,
    D * (0.4 / 36.75), 0, doorTop + frameTop / 2, D,
    { rule: 'structural', layer: 3 });
  addFrontBox(parts, 'strict_frame_bottom', 'cream', completeDoorWidth, frameBottom,
    D * (0.4 / 36.75), 0, doorBottom - frameBottom / 2, D,
    { rule: 'structural', layer: 3 });

  for (let door = 0; door < doors; door += 1) {
    const center = -completeDoorWidth / 2 + bayWidth * (door + 0.5);
    const cavityDepth = D * (0.3 / 36.75);
    parts.push(box(`strict_cavity_${door}`, 'display',
      new Vector3(glassWidth, cavityDepth, glassHeight),
      new Vector3(center, D / 2 - backWall - cavityDepth / 2,
        (glassBottom + glassTop) / 2),
      { rule: 'flat' }));
    addFrontBox(parts, `strict_glass_${door}`, 'glass', glassWidth, glassHeight,
      D * (0.2 / 36.75), center, (glassBottom + glassTop) / 2, D,
      { rule: 'panel', opacity: 0.42, layer: 5 });
    for (const direction of [-1, 1]) {
      addFrontBox(parts, `strict_door_rail_${door}_${direction}`, 'teal', railWidth,
        doorHeight, D * (0.3 / 36.75), center + direction * (bayWidth / 2 - railWidth / 2),
        (doorBottom + doorTop) / 2, D, { rule: 'structural', layer: 4 });
    }
    addHandle(parts, bayWidth, H, D, door, center);
    for (const shelfFraction of [36 / 96, 48 / 96, 60 / 96, 72 / 96]) {
      parts.push(box(`strict_shelf_${door}_${shelfFraction}`, 'steel',
        new Vector3(glassWidth - railWidth, D * RATIOS.shelfDepth, H * RATIOS.shelfThickness),
        new Vector3(center, -D * (0.5 / 36.75), H * shelfFraction),
        { rule: 'structural' }));
    }
  }

  addDisplay(parts, W, H, D);
  hardware(parts, 'strict_frame', {
    x: 0,
    z: (doorBottom + doorTop) / 2,
    width: completeDoorWidth + frameSide * 2,
    height: doorHeight,
  }, D);

  const root = new Group();
  root.name = 'strict_sdf_fridge';
  // The generator itself stays Z-up like the measured authority; this single
  // coordinate-system transform presents it in Three.js' Y-up world.
  root.rotation.x = -Math.PI / 2;
  root.add(...parts);
  root.userData.strictSdf = true;
  root.userData.surfaceUvPolicy = 'none';
  root.userData.texturePolicy = 'none';
  root.userData.lightingPolicy = 'unlit_normal_tints';
  root.userData.dimensions = { W, H, D };
  root.userData.doorCount = doors;
  root.userData.louvreCount = louvreCount;
  root.userData.styleUnit = U;
  return root;
}
