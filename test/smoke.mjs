// Headless smoke test — the acceptance checks this build can automate.
//
//   npm run build && npm run preview &   (or npm run dev)
//   node test/smoke.mjs [url] [screenshot-dir]
//
// Chromium here is software-rendered (SwiftShader), so it proves the shaders
// compile and the module system behaves — not that the frame rate is real.
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const url = process.argv[2] ?? 'http://localhost:4173/';
const shotDir = process.argv[3] ?? 'test/shots';
mkdirSync(shotDir, { recursive: true });

const exe = process.env.CHROMIUM_PATH; // set when the system chromium is not Playwright's
const browser = await chromium.launch({
  ...(exe ? { executablePath: exe } : {}),
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
});
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });

const problems = [];
page.on('console', (m) => {
  const t = m.text();
  if (m.type() === 'error') problems.push(`[console] ${t}`);
  if (t.includes('Shader Error') || t.includes('ERROR:')) problems.push(`[gl] ${t}`);
});
page.on('pageerror', (e) => problems.push(`[pageerror] ${e.message}`));

await page.goto(url, { waitUntil: 'load' });
await page.waitForFunction(() => !!globalThis.__app, null, { timeout: 15000 });
await page.waitForTimeout(1500);

const results = [];
const check = (name, ok, detail = '') => {
  results.push({ name, ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`);
};

check('no page or shader errors', problems.length === 0, problems.slice(0, 3).join(' | '));

// --- repeat axis: more shelves, not taller shelves (§8.2 / Phase 5 test) ----
const repeatTest = await page.evaluate(() => {
  const g = __app.placed.find((m) => m.typeId === 'gondola_shelf');
  const before = { meshes: g.meshes.length, params: { ...g.params } };
  g.setParams({ y: 6 });
  const after = { meshes: g.meshes.length, scaleY: g.material.uniforms.uTargetScale.value.y };
  g.setParams({ y: before.params.y });
  return { before, after, bays: before.params.x };
});
check(
  'repeat axis instances the unit mesh',
  repeatTest.after.meshes === repeatTest.bays * 6 && repeatTest.after.scaleY === 1,
  `3 bays × 6 shelves → ${repeatTest.after.meshes} meshes, targetScale.y ${repeatTest.after.scaleY}`
);

// --- stretch axis: one mesh, 9-slice in the vertex shader ------------------
const stretchTest = await page.evaluate(() => {
  const c = __app.placed.find((m) => m.typeId === 'serving_counter');
  c.setParams({ x: 4.0 });
  return { meshes: c.meshes.length, scale: c.material.uniforms.uTargetScale.value.toArray() };
});
check(
  'stretch axis stays one draw, drives uTargetScale',
  stretchTest.meshes === 1 && stretchTest.scale[0] === 4,
  `meshes ${stretchTest.meshes}, uTargetScale ${stretchTest.scale.join(', ')}`
);
await page.screenshot({ path: `${shotDir}/02-stretched-counter.png` });

// --- clamping (§5.2 guard 1) ----------------------------------------------
const clampTest = await page.evaluate(() => {
  const c = __app.placed.find((m) => m.typeId === 'serving_counter');
  c.setParams({ x: 99, z: -5 });
  const out = { ...c.params };
  c.setParams({ x: 2.4, z: 1.0 });
  return out;
});
check('params clamp to the axis spec', clampTest.x === 4 && clampTest.z === 0.8, JSON.stringify(clampTest));

// --- vertex masks were baked ----------------------------------------------
const maskTest = await page.evaluate(() => {
  const g = __app.placed[0].meshes[0].geometry.getAttribute('aMasks');
  let cavity = 0, edge = 0;
  for (let i = 0; i < g.count; i++) {
    cavity = Math.max(cavity, g.getX(i));
    edge = Math.max(edge, g.getY(i));
  }
  return { count: g.count, cavity, edge, hasColor0: !!__app.placed[0].meshes[0].geometry.getAttribute('color') };
});
check(
  'COLOR_0 masks baked with signal in cavity and edge',
  maskTest.cavity > 0.05 && maskTest.edge > 0.2 && maskTest.hasColor0,
  `max cavity ${maskTest.cavity.toFixed(2)}, max edge ${maskTest.edge.toFixed(2)} over ${maskTest.count} verts`
);

// --- socket snapping -------------------------------------------------------
const snapTest = await page.evaluate(() => {
  const run = __app.placed.find((m) => m.typeId === 'gondola_shelf');
  __app.selectType('gondola_shelf');
  // hold it just past the right-hand end of the run, deliberately misaligned
  const side = run.worldSockets().find((s) => s.tag === 'gondola_side' && s.normal.x > 0.5);
  const halfRun = __app.ghost.footprint[0];
  __app.ghost.group.position.set(side.pos.x + halfRun + 0.22, 0, side.pos.z + 0.13);
  const before = __app.ghost.group.position.clone();
  const snap = __app.snapDebug();
  return {
    before: before.toArray(),
    after: __app.ghost.group.position.toArray(),
    snapped: !!snap,
    tag: snap?.tag ?? null,
  };
});
check(
  'socket-to-socket snap pulls a gondola into a flush run',
  snapTest.snapped && snapTest.tag === 'gondola_side',
  `${snapTest.before.map((v) => v.toFixed(2))} → ${snapTest.after.map((v) => v.toFixed(2))}`
);

// --- save / load round trip -----------------------------------------------
const saveTest = await page.evaluate(() => {
  __app.save();
  const before = JSON.stringify(__app.placed.map((m) => m.toJSON()));
  __app.clearScene();
  const emptied = __app.placed.length;
  __app.load();
  const after = JSON.stringify(__app.placed.map((m) => m.toJSON()));
  return { emptied, identical: before === after, count: __app.placed.length };
});
check(
  'save → clear → load restores an identical scene',
  saveTest.emptied === 0 && saveTest.identical,
  `${saveTest.count} modules restored`
);

await page.mouse.move(560, 430);
await page.waitForTimeout(400);
await page.screenshot({ path: `${shotDir}/01-scene.png` });

await browser.close();

const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
if (problems.length) console.log('console output:\n' + problems.join('\n'));
process.exit(failed.length ? 1 : 0);
