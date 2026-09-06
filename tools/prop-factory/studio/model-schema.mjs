const color = { type: 'string', pattern: '^#[0-9a-fA-F]{6}$' };
const vec2 = { type: 'array', minItems: 2, maxItems: 2, items: { type: 'number' } };

export const modelSpecSchema = {
  type: 'object',
  additionalProperties: false,
  required: ['label', 'summary', 'dimensions', 'palette', 'parts', 'fixedParts', 'adaptiveFields', 'style'],
  properties: {
    label: { type: 'string' },
    summary: { type: 'string' },
    dimensions: {
      type: 'object', additionalProperties: false, required: ['width', 'depth', 'height'],
      properties: {
        width: { type: 'number', minimum: 8, maximum: 200 },
        depth: { type: 'number', minimum: 8, maximum: 200 },
        height: { type: 'number', minimum: 8, maximum: 240 },
      },
    },
    palette: {
      type: 'object', additionalProperties: false,
      required: ['primary', 'secondary', 'dark', 'light', 'accent'],
      properties: { primary: color, secondary: color, dark: color, light: color, accent: color },
    },
    parts: {
      type: 'array', minItems: 3, maxItems: 72,
      items: {
        type: 'object', additionalProperties: false,
        required: ['id', 'role', 'material', 'bounds', 'bevel'],
        properties: {
          id: { type: 'string' }, role: { type: 'string' },
          material: { enum: ['primary', 'secondary', 'dark', 'light', 'accent'] },
          bounds: { type: 'array', minItems: 6, maxItems: 6, items: { type: 'number', minimum: 0, maximum: 1 } },
          bevel: { type: 'number', minimum: 0, maximum: 2 },
        },
      },
    },
    fixedParts: {
      type: 'array', maxItems: 32,
      items: {
        type: 'object', additionalProperties: false,
        required: ['id', 'type', 'face', 'anchor', 'offset', 'size', 'depth', 'material', 'accent', 'text'],
        properties: {
          id: { type: 'string' },
          type: { enum: ['handle', 'vent', 'screen', 'label', 'warning', 'fan', 'hinge', 'control'] },
          face: { enum: ['front', 'back', 'left', 'right'] },
          anchor: { enum: ['top-left', 'top-center', 'top-right', 'center-left', 'center', 'center-right', 'bottom-left', 'bottom-center', 'bottom-right'] },
          offset: vec2, size: vec2,
          depth: { type: 'number', minimum: 0.05, maximum: 8 },
          material: { enum: ['primary', 'secondary', 'dark', 'light', 'accent'] },
          accent: { enum: ['primary', 'secondary', 'dark', 'light', 'accent'] },
          text: { type: 'string' },
        },
      },
    },
    adaptiveFields: {
      type: 'array', maxItems: 16,
      items: {
        type: 'object', additionalProperties: false,
        required: ['id', 'face', 'pattern', 'margins', 'pitch', 'lineWidth', 'material', 'accent'],
        properties: {
          id: { type: 'string' }, face: { enum: ['front', 'back', 'left', 'right'] },
          pattern: { enum: ['grid', 'vertical-vents', 'horizontal-vents', 'panels'] },
          margins: { type: 'array', minItems: 4, maxItems: 4, items: { type: 'number', minimum: 0, maximum: 48 } },
          pitch: vec2, lineWidth: vec2,
          material: { enum: ['primary', 'secondary', 'dark', 'light', 'accent'] },
          accent: { enum: ['primary', 'secondary', 'dark', 'light', 'accent'] },
        },
      },
    },
    style: {
      type: 'object', additionalProperties: false,
      required: ['outline', 'topTint', 'frontTint', 'sideTint'],
      properties: {
        outline: color,
        topTint: { type: 'number', minimum: .8, maximum: 1.3 },
        frontTint: { type: 'number', minimum: .7, maximum: 1.2 },
        sideTint: { type: 'number', minimum: .5, maximum: 1.1 },
      },
    },
  },
};

export const evidenceSchema = {
  type: 'object', additionalProperties: false,
  required: ['objectType', 'confidence', 'silhouette', 'visibleStructure', 'fixedDetails', 'materials', 'uncertainties'],
  properties: {
    objectType: { type: 'string' }, confidence: { type: 'number', minimum: 0, maximum: 1 },
    silhouette: { type: 'string' },
    visibleStructure: { type: 'array', items: { type: 'string' }, maxItems: 24 },
    fixedDetails: { type: 'array', items: { type: 'string' }, maxItems: 24 },
    materials: { type: 'array', items: { type: 'string' }, maxItems: 16 },
    uncertainties: { type: 'array', items: { type: 'string' }, maxItems: 16 },
  },
};
