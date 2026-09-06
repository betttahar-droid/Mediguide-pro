/**
 * Engine-independent rules for resizing modular assets without scaling their
 * identity-critical details. All coordinates are expressed in model pixels.
 */

export const AxisPolicy = Object.freeze({
  FIXED_MIN: 'fixed_min',
  FIXED_CENTER: 'fixed_center',
  FIXED_MAX: 'fixed_max',
  NINE_SLICE_SPAN: 'nine_slice_span',
  PROPORTIONAL: 'proportional',
});

export const TexturePolicy = Object.freeze({
  SOLID: 'solid',
  TILE_WORLD_SCALE: 'tile_world_scale',
  NINE_SLICE_TILE_CENTER: 'nine_slice_tile_center',
  FIXED_DECAL: 'fixed_decal',
  REPEAT_PER_MODULE: 'repeat_per_module',
});

const AXES = ['x', 'y', 'z'];

function validateRange(range, label) {
  if (!Array.isArray(range) || range.length !== 2 || !range.every(Number.isFinite)) {
    throw new TypeError(`${label} must be a finite [min, max] range`);
  }
  if (range[1] <= range[0]) throw new RangeError(`${label} must have positive length`);
}

function centerOf(range) {
  return (range[0] + range[1]) / 2;
}

/**
 * Geometry twin of nine-slice mapping. Protected end zones translate without
 * changing size; only the safe center changes length.
 */
export function remapNineSliceCoordinate(
  value,
  sourceRange,
  targetRange,
  protectedNear = 0,
  protectedFar = protectedNear,
) {
  validateRange(sourceRange, 'sourceRange');
  validateRange(targetRange, 'targetRange');
  if (protectedNear < 0 || protectedFar < 0) {
    throw new RangeError('protected borders cannot be negative');
  }

  const [sourceMin, sourceMax] = sourceRange;
  const [targetMin, targetMax] = targetRange;
  const sourceLength = sourceMax - sourceMin;
  const targetLength = targetMax - targetMin;
  const protectedTotal = protectedNear + protectedFar;
  if (protectedTotal >= sourceLength || protectedTotal >= targetLength) {
    throw new RangeError('source and target must contain a non-empty scalable center');
  }

  const sourceInnerMin = sourceMin + protectedNear;
  const sourceInnerMax = sourceMax - protectedFar;
  const targetInnerMin = targetMin + protectedNear;
  const targetInnerMax = targetMax - protectedFar;

  if (value <= sourceInnerMin) return targetMin + (value - sourceMin);
  if (value >= sourceInnerMax) return targetMax - (sourceMax - value);

  const t = (value - sourceInnerMin) / (sourceInnerMax - sourceInnerMin);
  return targetInnerMin + t * (targetInnerMax - targetInnerMin);
}

export function mapAnchoredCoordinate(value, sourceRange, targetRange, policy) {
  validateRange(sourceRange, 'sourceRange');
  validateRange(targetRange, 'targetRange');
  switch (policy) {
    case AxisPolicy.FIXED_MIN:
      return value + targetRange[0] - sourceRange[0];
    case AxisPolicy.FIXED_MAX:
      return value + targetRange[1] - sourceRange[1];
    case AxisPolicy.FIXED_CENTER:
      return value + centerOf(targetRange) - centerOf(sourceRange);
    case AxisPolicy.PROPORTIONAL: {
      const t = (value - sourceRange[0]) / (sourceRange[1] - sourceRange[0]);
      return targetRange[0] + t * (targetRange[1] - targetRange[0]);
    }
    default:
      throw new Error(`Unsupported anchored axis policy: ${policy}`);
  }
}

/** Resolve a fixed-size detail such as a display, logo, corner chip, or handle. */
export function resolveFixedSocket(socket, sourceBounds, targetBounds) {
  const positionPx = {};
  for (const axis of AXES) {
    const policy = socket.anchor?.[axis] ?? AxisPolicy.FIXED_CENTER;
    if (![AxisPolicy.FIXED_MIN, AxisPolicy.FIXED_CENTER, AxisPolicy.FIXED_MAX].includes(policy)) {
      throw new Error(`Fixed socket ${socket.id ?? '<unnamed>'} cannot use ${policy} on ${axis}`);
    }
    positionPx[axis] = mapAnchoredCoordinate(
      socket.positionPx[axis], sourceBounds[axis], targetBounds[axis], policy,
    );
  }
  return {
    ...socket,
    positionPx,
    sizePx: { ...socket.sizePx },
    scale: { x: 1, y: 1, z: 1 },
  };
}

/** Resolve a part's bounds using a separate semantic rule on every axis. */
export function resolvePartBounds(part, sourceBounds, targetBounds) {
  const boundsPx = {};
  for (const axis of AXES) {
    const sourceAxis = sourceBounds[axis];
    const targetAxis = targetBounds[axis];
    const partAxis = part.boundsPx[axis];
    const rule = part.axes?.[axis] ?? { policy: AxisPolicy.FIXED_CENTER };
    validateRange(partAxis, `${part.id}.${axis}`);

    if (rule.policy === AxisPolicy.NINE_SLICE_SPAN) {
      const near = rule.protectedNearPx ?? 0;
      const far = rule.protectedFarPx ?? near;
      boundsPx[axis] = partAxis.map((value) => remapNineSliceCoordinate(
        value, sourceAxis, targetAxis, near, far,
      ));
    } else {
      boundsPx[axis] = partAxis.map((value) => mapAnchoredCoordinate(
        value, sourceAxis, targetAxis, rule.policy,
      ));
    }
  }
  return { ...part, boundsPx };
}

/** Centers for discrete modules. Functional bays are inserted, never stretched. */
export function repeatedModuleCenters(count, moduleSizePx, centerPx = 0) {
  const safeCount = Math.max(1, Math.round(count));
  if (!(moduleSizePx > 0)) throw new RangeError('moduleSizePx must be positive');
  return Array.from(
    { length: safeCount },
    (_, index) => centerPx + (index - (safeCount - 1) / 2) * moduleSizePx,
  );
}

/** Fail early when a manifest would stretch a decal or omit a texture contract. */
export function validateAdaptiveDefinition(definition) {
  const errors = [];
  const ids = new Set();
  for (const part of definition.parts ?? []) {
    if (!part.id) errors.push('Every part needs an id');
    else if (ids.has(part.id)) errors.push(`Duplicate part id: ${part.id}`);
    else ids.add(part.id);

    if (!Object.values(TexturePolicy).includes(part.texturePolicy)) {
      errors.push(`${part.id ?? '<unnamed>'} has unknown texturePolicy ${part.texturePolicy}`);
    }
    if (part.texturePolicy === TexturePolicy.FIXED_DECAL) {
      for (const axis of AXES) {
        const policy = part.axes?.[axis]?.policy;
        if (![AxisPolicy.FIXED_MIN, AxisPolicy.FIXED_CENTER, AxisPolicy.FIXED_MAX].includes(policy)) {
          errors.push(`${part.id} fixed decal must use a fixed anchor on ${axis}`);
        }
      }
    }
  }
  return { valid: errors.length === 0, errors };
}

