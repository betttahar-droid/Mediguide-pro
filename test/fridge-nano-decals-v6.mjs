import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const auditUrl = new URL(
  '../docs/reference-lock/vaccine-fridge-v1/nano-banana-v6/nano-fixed-decals-v6.audit.json',
  import.meta.url,
);
const audit = JSON.parse(readFileSync(auditUrl, 'utf8'));

assert.equal(audit.schemaVersion, 6);
assert.equal(audit.atlasSizePx[0], audit.atlasSizePx[1]);
assert.equal(audit.decals.length, 8);
assert.equal(new Set(audit.decals.map((decal) => decal.name)).size, audit.decals.length);

for (const decal of audit.decals) {
  const [x, y, width, height] = decal.atlasRectPx;
  const [slotX, slotY, slotWidth, slotHeight] = decal.slotRectPx;
  assert.ok(decal.atlasMarginPx >= 4, `${decal.name} needs a four-pixel atlas gutter`);
  assert.ok(decal.internalMarginPx >= 2, `${decal.name} needs transparent internal breathing room`);
  assert.ok(x >= slotX + decal.atlasMarginPx);
  assert.ok(y >= slotY + decal.atlasMarginPx);
  assert.ok(x + width <= slotX + slotWidth - decal.atlasMarginPx);
  assert.ok(y + height <= slotY + slotHeight - decal.atlasMarginPx);
}

const atlasUrl = new URL(`../${audit.output.replaceAll('\\', '/')}`, import.meta.url);
assert.ok(existsSync(atlasUrl), 'compiled Nano decal atlas must exist');

console.log('PASS Nano decal atlas: eight deliberate motifs with protected internal and atlas margins');
