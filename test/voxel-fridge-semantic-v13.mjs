import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const lock = new URL('../docs/reference-lock/vaccine-fridge-v1/semantic-v13/', import.meta.url);
const atlasAudit = JSON.parse(readFileSync(new URL('semantic-faces-v13.audit.json', lock), 'utf8'));
const runtimeAudit = JSON.parse(readFileSync(new URL('runtime/audit.json', lock), 'utf8'));
const mainSource = readFileSync(new URL('../tools/voxel-fridge/main.js', import.meta.url), 'utf8');
const styleSource = readFileSync(new URL('../tools/voxel-fridge/style.js', import.meta.url), 'utf8');
const generatorSource = readFileSync(new URL('../tools/authoring/generate_fridge_semantic_faces_v13.py', import.meta.url), 'utf8');

assert.equal(atlasAudit.schemaVersion, 13);
assert.match(atlasAudit.generator, /Nano Banana 2/);
assert.deepEqual(atlasAudit.atlasSizePx, [256, 32]);
assert.deepEqual(atlasAudit.logicalTileSizePx, [32, 32]);
assert.deepEqual(atlasAudit.toneLevels, [32, 96, 128, 192, 240]);
assert.deepEqual(atlasAudit.profiles.map((profile) => profile.name), [
  'roofTop', 'crownFront', 'cabinetSide', 'doorFrame',
  'shelfTop', 'shelfLip', 'baseFront', 'ventField',
]);
assert.equal(atlasAudit.rejectedSourceRegions.length, 3);
assert.equal(atlasAudit.checks.generationLayoutAccepted, false);
assert.equal(atlasAudit.checks.reviewedSelectionCompiled, true);
assert.equal(atlasAudit.checks.requestedProfileCount, true);
assert.equal(atlasAudit.checks.allIndexed, true);
assert.ok(existsSync(new URL('semantic-faces-v13-source.png', lock)));
assert.ok(existsSync(new URL('semantic-faces-v13-compiled-preview.png', lock)));
assert.match(generatorSource, /from concept_sheet import generate_image, load_key/);

// Unassigned role uniforms must remain disabled. Vector4() defaults w to 1.
assert.equal((styleSource.match(/new THREE\.Vector4\(0, 0, 0, 0\)/g) ?? []).length, 2);
assert.match(styleSource, /uRoleRectFront/);
assert.match(styleSource, /uRoleParamsFront/);
assert.match(styleSource, /\(uTexel \* \.5\)/);
assert.match(styleSource, /if\(tone>=\.44 && tone<\.63\) discard/);
assert.match(mainSource, /surfaceFaces: \{ top: 'roofTop' \}/);
assert.match(mainSource, /surfaceFaces: \{ front: 'crownFront' \}/);
assert.match(mainSource, /surfaceFaces: \{ front: 'shelfLip' \}/);
assert.match(mainSource, /surfaceFaces: \{ front: 'ventField' \}/);
assert.doesNotMatch(styleSource + mainSource, /glassWideReflection|glassGlint/);

assert.equal(runtimeAudit.status, 'PASS');
assert.equal(runtimeAudit.fixedDecalsMatch, true);
assert.equal(runtimeAudit.rigidPartsMatch, true);
assert.equal(runtimeAudit.adaptiveDecalsGrow, true);
assert.equal(runtimeAudit.structuralCountsAdapt, true);
const normal = runtimeAudit.records.find((record) => record.query === 'view=iso');
const resized = runtimeAudit.records.find((record) => record.query.includes('sx=1.65'));
assert.ok(normal && resized);
assert.equal(normal.decals, 12);
assert.equal(resized.decals, 13);
assert.deepEqual(normal.adaptiveDecalCounts, [['decal_semantic_shelfPatch', 4]]);
assert.deepEqual(resized.adaptiveDecalCounts, [['decal_semantic_shelfPatch', 5]]);
assert.deepEqual(resized.protectedDecalSizes, normal.protectedDecalSizes);
assert.deepEqual(resized.rigidPartSizes, normal.rigidPartSizes);
assert.ok(normal.semanticFacePrograms.every(([, faces]) => faces.length === 1));
for (const record of runtimeAudit.records) {
  assert.deepEqual(record.errors, []);
  assert.ok(record.paletteSize >= 25 && record.paletteSize <= 60);
  assert.ok(record.triangles >= 2000 && record.triangles <= 5000);
}

console.log('PASS v13: Nano semantic faces, fixed anchors, adaptive repeated details');
