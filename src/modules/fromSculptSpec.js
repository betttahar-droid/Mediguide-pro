// Bridge: an img2threejs ObjectSculptSpec -> this project's part list.
//
// WHY A BRIDGE RATHER THAN THE GENERATED FACTORY.
//
// `src/generated/createObjectModel.ts` is the factory img2threejs produced, and
// it is a real reconstruction: correct hierarchy, correct pivots, named sockets,
// dimensions in metres, every component carrying its spec in `userData`. That
// part is good and it is why the spec was worth authoring.
//
// Its RENDERING is the opposite of what this project needs, and not by mistake —
// the skill is built for photoreal reconstruction:
//
//   * `new THREE.BoxGeometry(1, 1, 1, 12, 12, 12)` — 12 subdivisions per axis on
//     a box whose every face is flat. Nearly 1,700 triangles where 12 would do,
//     and subdivision is actively harmful here: it gives the toon ramp interior
//     vertices to interpolate across, which is how a flat face grows a gradient.
//   * `flatShading: spec.flatShading === true` — off unless asked.
//   * a presentation stack of RoomEnvironment, UnrealBloomPass and BokehPass.
//     Bloom and depth-of-field on 16-bit pixel art undo the entire style: both
//     are blur, and this look is defined by not blurring.
//
// So the bridge takes the RECONSTRUCTION — what the parts are, where they are,
// how big, what they are made of — and builds it with `buildParts`, which gives
// non-indexed faceted geometry, the material strips, the accent slots and the
// 9-slice attributes. The spec stays the source of truth; only the renderer
// changes. Re-run the skill, re-import, and the numbers update.
import { PALETTE } from '../art/palette.js';

// The spec carries a per-component `baseColorHex`. This project forbids hex
// literals outside palette.js (§4.4), so a spec colour is matched to the
// nearest palette entry rather than used directly — which also keeps a
// regenerated spec inside the limited palette instead of drifting out of it.
const PALETTE_CHOICES = [
  'teal', 'tealDeep', 'mint', 'oak', 'oakDark', 'walnut', 'espresso',
  'paper', 'bone', 'steel', 'steelDark', 'charcoal', 'signal', 'glass',
];

function nearestPaletteName(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex ?? '');
  if (!m) return 'teal';
  const v = parseInt(m[1], 16);
  const r = (v >> 16) & 255, g = (v >> 8) & 255, b = v & 255;
  let best = 'teal', bestD = Infinity;
  for (const name of PALETTE_CHOICES) {
    const c = PALETTE[name];
    // compare in sRGB-ish space: PALETTE holds linear Colors, so undo it
    const cr = Math.round(255 * Math.pow(c.r, 1 / 2.2));
    const cg = Math.round(255 * Math.pow(c.g, 1 / 2.2));
    const cb = Math.round(255 * Math.pow(c.b, 1 / 2.2));
    const d = (cr - r) ** 2 + (cg - g) ** 2 + (cb - b) ** 2;
    if (d < bestD) { bestD = d; best = name; }
  }
  return best;
}

/**
 * Turn a spec's componentTree into `{ parts, colors, unit, margins }`.
 *
 * Positions in the spec are LOCAL TO THE PARENT, and this project's part list is
 * flat and local to the module, so parents are accumulated on the way down. That
 * is the one genuinely fiddly bit: a spec that nests four deep and a part list
 * that does not will silently disagree about where anything is if you skip it.
 *
 * @param {object} spec a validated ObjectSculptSpec
 * @param {{skip?: string[]}} opts component ids to leave out
 */
export function partsFromSpec(spec, { skip = [] } = {}) {
  const byId = new Map(spec.componentTree.map((c) => [c.id, c]));
  const skipped = new Set(skip);

  const worldPos = (c) => {
    const at = [0, 0, 0];
    for (let node = c; node; node = node.parent ? byId.get(node.parent) : null) {
      const p = node.transform?.position ?? [0, 0, 0];
      at[0] += p[0]; at[1] += p[1]; at[2] += p[2];
    }
    return at;
  };

  // Accent slots are assigned per DISTINCT COLOUR, not per material — and that
  // distinction is not academic. The plaque and the fascia band share the
  // 'brass-fitting' material but the spec gives them different colours, so a
  // per-material assignment collided them and rendered the GREEN CROSS CORAL.
  // That is the exact failure this spec's own featureReviewTargets names as
  // critical ("wrong hue — a blue or grey cross reads as a hospital"), and it
  // is what the render-and-review step exists to catch.
  const slotFor = new Map();
  const slotName = ['', '', '', '', ''];
  const assignSlot = (hex) => {
    const name = nearestPaletteName(hex);
    if (slotFor.has(name)) return slotFor.get(name);
    const slot = slotFor.size; // 0 is the base colour, then 1..4
    if (slot > 4) return 0; // more colours than slots: fall back to the body
    slotFor.set(name, slot);
    slotName[slot] = name;
    return slot;
  };

  const parts = [];
  for (const c of spec.componentTree) {
    if (skipped.has(c.id)) continue;
    const d = c.dimensions ?? {};
    // The root is the bounding volume, not a part: emitting it would render a
    // solid box around everything else.
    if (!c.parent) continue;

    const recipe = c.colorMaterialRecipe ?? {};
    parts.push({
      size: [d.width ?? 0.1, d.height ?? 0.1, d.depth ?? 0.1],
      at: worldPos(c),
      // The spec's bevelRadius is a real authored number; this project scales
      // every bevel by EDGE_SOFTNESS on top, which is where the hard-edged
      // 16-bit read comes from.
      bevel: c.geometryDescriptor?.edgeTreatment?.bevelRadius ?? 0.008,
      mat: recipe.trimStrip ?? 'paint',
      accent: assignSlot(recipe.baseColorHex),
      name: c.id,
    });
  }

  const root = spec.componentTree.find((c) => !c.parent);
  const rd = root?.dimensions ?? { width: 1, height: 1, depth: 1 };
  const repeat = (spec.repetitionSystems ?? [])[0];

  return {
    parts,
    unit: [rd.width / 2, rd.height / 2, rd.depth / 2],
    // Margins are 0 on the repeat axis: a repeated axis must never be 9-sliced,
    // and validateRegistry() rejects a margin on a non-stretch axis by name.
    margins: [0, 0, 0],
    repeat: repeat && {
      axis: repeat.axis, unit: repeat.unit,
      min: repeat.min, max: repeat.max, default: repeat.default,
    },
    colors: {
      base: PALETTE[slotName[0]] ?? PALETTE.teal,
      middle: PALETTE.tealDeep,
      accent1: PALETTE[slotName[1]] ?? PALETTE.oak,
      accent2: PALETTE[slotName[2]] ?? PALETTE.signal,
      accent3: PALETTE[slotName[3]] ?? PALETTE.espresso,
      accent4: PALETTE[slotName[4]] ?? PALETTE.glass,
    },
    slotName,
  };
}
