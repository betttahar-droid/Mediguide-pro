import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { PNG } from 'pngjs';

const workspace = resolve(import.meta.dirname, '..', '..');
const boardPath = resolve(
  workspace,
  'docs/reference-lock/vaccine-fridge-v1/gpt-image/gpt-image-pixel-material-kit-v2.png',
);
const baseAtlasPath = resolve(workspace, 'public/textures/vaccine-fridge-adaptive-source-atlas.png');
const outputAtlasPath = resolve(workspace, 'public/textures/vaccine-fridge-adaptive-gpt-v2.png');
const auditPath = resolve(
  workspace,
  'docs/reference-lock/vaccine-fridge-v1/gpt-image/gpt-image-pixel-material-kit-v2.audit.json',
);

function pixel(png, x, y) {
  const i = (y * png.width + x) * 4;
  return [png.data[i], png.data[i + 1], png.data[i + 2], png.data[i + 3]];
}

function setPixel(png, x, y, rgba) {
  const i = (y * png.width + x) * 4;
  png.data[i] = rgba[0];
  png.data[i + 1] = rgba[1];
  png.data[i + 2] = rgba[2];
  png.data[i + 3] = rgba[3];
}

function isGridPixel(rgba) {
  return rgba[0] < 100 && rgba[1] < 100 && rgba[2] < 100;
}

function findGridLines(png, axis) {
  const length = axis === 'x' ? png.width : png.height;
  const cross = axis === 'x' ? png.height : png.width;
  const hits = [];
  for (let primary = 0; primary < length; primary += 1) {
    let count = 0;
    for (let secondary = 0; secondary < cross; secondary += 1) {
      const rgba = axis === 'x' ? pixel(png, primary, secondary) : pixel(png, secondary, primary);
      if (isGridPixel(rgba)) count += 1;
    }
    if (count > cross * 0.65) hits.push(primary);
  }
  // Collapse adjacent antialiased line pixels to one coordinate.
  return hits.filter((value, index) => index === 0 || value - hits[index - 1] > 1);
}

function findContentBounds(png, cellBounds) {
  const inset = 24;
  const [left, top, right, bottom] = cellBounds;
  let minX = right;
  let minY = bottom;
  let maxX = left;
  let maxY = top;
  for (let y = top + inset; y < bottom - inset; y += 1) {
    for (let x = left + inset; x < right - inset; x += 1) {
      const [r, g, b] = pixel(png, x, y);
      // Generated sheet background is neutral white. Cream content still has
      // a blue channel safely below this threshold.
      if (r > 242 && g > 242 && b > 242) continue;
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      maxX = Math.max(maxX, x);
      maxY = Math.max(maxY, y);
    }
  }
  if (maxX < minX || maxY < minY) throw new Error('No texture content found in generated cell');
  return [minX, minY, maxX + 1, maxY + 1];
}

function averagePixelBlock(source, left, top, right, bottom) {
  const sum = [0, 0, 0, 0];
  let count = 0;
  for (let y = top; y < bottom; y += 1) {
    for (let x = left; x < right; x += 1) {
      const rgba = pixel(source, x, y);
      for (let channel = 0; channel < 4; channel += 1) sum[channel] += rgba[channel];
      count += 1;
    }
  }
  return sum.map((value) => value / Math.max(1, count));
}

function makeSeamlessMirroredTile(source, bounds, halfSize = 16, baseCells = 8) {
  const [left, top, right, bottom] = bounds;
  const sourceWidth = right - left;
  const sourceHeight = bottom - top;
  const sampleLeft = left + Math.floor(sourceWidth * 0.25);
  const sampleTop = top + Math.floor(sourceHeight * 0.25);
  const sampleWidth = Math.max(1, Math.floor(sourceWidth * 0.5));
  const sampleHeight = Math.max(1, Math.floor(sourceHeight * 0.5));
  const tile = new PNG({ width: halfSize * 2, height: halfSize * 2 });

  for (let y = 0; y < tile.height; y += 1) {
    const mirroredY = y < halfSize ? y : tile.height - 1 - y;
    const cellY = Math.min(baseCells - 1, Math.floor(mirroredY * baseCells / halfSize));
    const sourceY0 = sampleTop + Math.floor(cellY * sampleHeight / baseCells);
    const sourceY1 = sampleTop + Math.max(
      Math.floor((cellY + 1) * sampleHeight / baseCells),
      Math.floor(cellY * sampleHeight / baseCells) + 1,
    );
    for (let x = 0; x < tile.width; x += 1) {
      const mirroredX = x < halfSize ? x : tile.width - 1 - x;
      const cellX = Math.min(baseCells - 1, Math.floor(mirroredX * baseCells / halfSize));
      const sourceX0 = sampleLeft + Math.floor(cellX * sampleWidth / baseCells);
      const sourceX1 = sampleLeft + Math.max(
        Math.floor((cellX + 1) * sampleWidth / baseCells),
        Math.floor(cellX * sampleWidth / baseCells) + 1,
      );
      const rgba = averagePixelBlock(source, sourceX0, sourceY0, sourceX1, sourceY1);
      // Quantization removes soft AI sampling noise and restores deliberate
      // pixel clusters while preserving the generated palette.
      setPixel(tile, x, y, [
        Math.min(255, Math.round(rgba[0] / 16) * 16),
        Math.min(255, Math.round(rgba[1] / 16) * 16),
        Math.min(255, Math.round(rgba[2] / 16) * 16),
        255,
      ]);
    }
  }
  return tile;
}

function assertPeriodicEdges(tile, name) {
  for (let y = 0; y < tile.height; y += 1) {
    if (pixel(tile, 0, y).join() !== pixel(tile, tile.width - 1, y).join()) {
      throw new Error(`${name} left/right seam mismatch at row ${y}`);
    }
  }
  for (let x = 0; x < tile.width; x += 1) {
    if (pixel(tile, x, 0).join() !== pixel(tile, x, tile.height - 1).join()) {
      throw new Error(`${name} top/bottom seam mismatch at column ${x}`);
    }
  }
}

function compressTileContrast(tile, strength) {
  const average = [0, 0, 0];
  const pixels = tile.width * tile.height;
  for (let i = 0; i < tile.data.length; i += 4) {
    average[0] += tile.data[i];
    average[1] += tile.data[i + 1];
    average[2] += tile.data[i + 2];
  }
  for (let channel = 0; channel < 3; channel += 1) average[channel] /= pixels;
  for (let i = 0; i < tile.data.length; i += 4) {
    for (let channel = 0; channel < 3; channel += 1) {
      const mixed = average[channel] + (tile.data[i + channel] - average[channel]) * strength;
      tile.data[i + channel] = Math.min(255, Math.max(0, Math.round(mixed / 8) * 8));
    }
  }
  return tile;
}

function makeTransparentSprite(source, bounds, width, height) {
  const [left, top, right, bottom] = bounds;
  const sprite = new PNG({ width, height });
  for (let y = 0; y < height; y += 1) {
    const sourceY = top + Math.min(bottom - top - 1, Math.floor((y + 0.5) * (bottom - top) / height));
    for (let x = 0; x < width; x += 1) {
      const sourceX = left + Math.min(right - left - 1, Math.floor((x + 0.5) * (right - left) / width));
      const rgba = pixel(source, sourceX, sourceY);
      const whiteDistance = Math.hypot(255 - rgba[0], 255 - rgba[1], 255 - rgba[2]);
      setPixel(sprite, x, y, whiteDistance < 24 ? [0, 0, 0, 0] : [
        Math.min(255, Math.round(rgba[0] / 16) * 16),
        Math.min(255, Math.round(rgba[1] / 16) * 16),
        Math.min(255, Math.round(rgba[2] / 16) * 16),
        255,
      ]);
    }
  }
  if (![...sprite.data].some((value, index) => index % 4 === 3 && value > 0)) {
    throw new Error('Generated sprite became fully transparent');
  }
  return sprite;
}

function fillAtlasRegion(atlas, rect, tile, borderX, borderY) {
  const [left, top, width, height] = rect;
  for (let y = borderY; y < height - borderY; y += 1) {
    for (let x = borderX; x < width - borderX; x += 1) {
      setPixel(atlas, left + x, top + y, pixel(tile, x % tile.width, y % tile.height));
    }
  }
}

const board = PNG.sync.read(readFileSync(boardPath));
if (board.width !== 1254 || board.height !== 1254) {
  throw new Error(`Pixel material kit v2 must remain 1254x1254; got ${board.width}x${board.height}`);
}
// GPT emitted separated cell rectangles rather than shared grid boundaries.
// Lock their measured bounds so a changed generation cannot silently shift a
// crop and still enter production.
const columnBounds = [[18, 310], [326, 616], [633, 923], [941, 1232]];
const rowBounds = [[18, 311], [327, 621], [636, 930], [946, 1240]];

const materialCells = [
  { name: 'cream', column: 0, row: 0, atlasRect: [0, 192, 64, 64], border: [8, 8], strength: 0.42 },
  { name: 'steel', column: 1, row: 0, atlasRect: [64, 128, 64, 128], border: [8, 8], strength: 0.48 },
  { name: 'teal', column: 2, row: 0, atlasRect: [128, 192, 64, 64], border: [8, 8], strength: 0.52 },
  { name: 'glass', column: 3, row: 0, atlasRect: [192, 128, 64, 128], border: [0, 0], strength: 0.45 },
];

const atlas = PNG.sync.read(readFileSync(baseAtlasPath));
mkdirSync(dirname(outputAtlasPath), { recursive: true });
const accepted = [];
let derivedPanelTile;
for (const cell of materialCells) {
  const cellBounds = [
    columnBounds[cell.column][0],
    rowBounds[cell.row][0],
    columnBounds[cell.column][1],
    rowBounds[cell.row][1],
  ];
  const contentBounds = findContentBounds(board, cellBounds);
  const tile = compressTileContrast(makeSeamlessMirroredTile(board, contentBounds), cell.strength);
  assertPeriodicEdges(tile, cell.name);
  const tilePath = resolve(workspace, `public/textures/vaccine-fridge-gpt-${cell.name}-tile-v2.png`);
  writeFileSync(tilePath, PNG.sync.write(tile));
  if (cell.name === 'steel') {
    const panelTile = PNG.sync.read(PNG.sync.write(tile));
    compressTileContrast(panelTile, 0.22);
    derivedPanelTile = 'public/textures/vaccine-fridge-gpt-steel-panel-tile-v2.png';
    writeFileSync(resolve(workspace, derivedPanelTile), PNG.sync.write(panelTile));
  }
  fillAtlasRegion(atlas, cell.atlasRect, tile, cell.border[0], cell.border[1]);
  accepted.push({
    cell: cell.row * 4 + cell.column + 1,
    role: cell.name,
    contentBoundsPx: contentBounds,
    output: tilePath.slice(workspace.length + 1).replaceAll('\\', '/'),
    seamGate: 'pass',
  });
}
writeFileSync(outputAtlasPath, PNG.sync.write(atlas));

const spriteCells = [
  { name: 'cream-corner', column: 0, row: 2, size: [8, 8] },
  { name: 'steel-corner', column: 1, row: 2, size: [8, 8] },
  { name: 'teal-corner', column: 2, row: 2, size: [8, 8] },
  { name: 'bolt', column: 3, row: 2, size: [4, 4] },
  { name: 'glass-reflection', column: 0, row: 3, size: [8, 16] },
  { name: 'shelf-band', column: 1, row: 3, size: [16, 4] },
  { name: 'steel-patch', column: 2, row: 3, size: [16, 8] },
  { name: 'teal-patch', column: 3, row: 3, size: [16, 8] },
];
const acceptedSprites = [];
for (const cell of spriteCells) {
  const cellBounds = [
    columnBounds[cell.column][0], rowBounds[cell.row][0],
    columnBounds[cell.column][1], rowBounds[cell.row][1],
  ];
  const contentBounds = findContentBounds(board, cellBounds);
  const sprite = makeTransparentSprite(board, contentBounds, ...cell.size);
  const spritePath = resolve(workspace, `public/textures/vaccine-fridge-gpt-${cell.name}-v2.png`);
  writeFileSync(spritePath, PNG.sync.write(sprite));
  acceptedSprites.push({
    cell: cell.row * 4 + cell.column + 1,
    role: cell.name,
    sizePx: cell.size,
    output: spritePath.slice(workspace.length + 1).replaceAll('\\', '/'),
    alphaGate: 'pass',
  });
}

const audit = {
  schemaVersion: 2,
  sourceBoard: boardPath.slice(workspace.length + 1).replaceAll('\\', '/'),
  generatedAtlas: outputAtlasPath.slice(workspace.length + 1).replaceAll('\\', '/'),
  boardSizePx: [board.width, board.height],
  cellBoundsPx: { columns: columnBounds, rows: rowBounds },
  accepted,
  derivedPanelTile,
  acceptedSprites,
  identityDecalsExcludedFromGeneration: ['grille', 'display'],
  fallbackDecals: {
    grille: 'public/textures/vaccine-fridge-grille.png',
    display: 'public/textures/vaccine-fridge-display.png',
  },
};
writeFileSync(auditPath, `${JSON.stringify(audit, null, 2)}\n`);
console.log(`PASS GPT pixel kit: ${accepted.length} seamless material tiles, ${acceptedSprites.length} fixed-detail sprites; identity decals retain authority crops`);
