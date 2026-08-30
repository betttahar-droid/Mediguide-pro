// Headless smoke test — the acceptance checks this build can automate.
//
//   npm run build && npm run preview &   (or npm run dev)
//   node test/smoke.mjs [url] [screenshot-dir]
//
// Chromium here is software-rendered (SwiftShader), so it proves the shaders
// compile and the module system behaves — not that the frame rate is real.
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';
import { PNG } from 'pngjs';

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
await page.evaluate(() => __app.texturesReady); // the sheets must be decoded before any pixel check
await page.waitForTimeout(1500);

const results = [];
const check = (name, ok, detail = '') => {
  results.push({ name, ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`);
};

check('no page or shader errors', problems.length === 0, problems.slice(0, 3).join(' | '));

// --- the authored sheets actually loaded ----------------------------------
const sheets = await page.evaluate(() => {
  const m = __app.placed[0].material.uniforms;
  return ['uTrimMap', 'uAtlasMap', 'uTilingMap', 'uHatchMap'].map((k) => {
    const img = m[k].value?.image;
    return { k, w: img?.width ?? 0, h: img?.height ?? 0 };
  });
});
check(
  'the authored texture sheets are loaded from public/textures',
  sheets.every((s) => s.w > 0 && s.h > 0),
  sheets.map((s) => `${s.k.replace('u', '').replace('Map', '')} ${s.w}x${s.h}`).join(', ')
);

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
// The counter's length used to be this case; §C2 made it a steps axis, so the
// reference stretch is now the booth, whose walls really are featureless.
const stretchTest = await page.evaluate(() => {
  const c = __app.placed.find((m) => m.typeId === 'consultation_booth');
  c.setParams({ x: 2.1 });
  const out = { meshes: c.meshes.length, scale: c.material.uniforms.uTargetScale.value.toArray() };
  c.setParams({ x: 1.0 });
  return out;
});
check(
  'stretch axis stays one draw, drives uTargetScale',
  stretchTest.meshes === 1 && stretchTest.scale[0] === 2.1,
  `meshes ${stretchTest.meshes}, uTargetScale ${stretchTest.scale.join(', ')}`
);
await page.screenshot({ path: `${shotDir}/02-stretched-counter.png` });

// --- clamping (§5.2 guard 1) ----------------------------------------------
// Both kinds at once: a stretch axis clamps to its range, a steps axis snaps to
// its nearest step, and neither leaves a value the geometry cache cannot key.
const clampTest = await page.evaluate(() => {
  const c = __app.placed.find((m) => m.typeId === 'serving_counter');
  c.setParams({ x: 99, z: -5 });
  const out = { ...c.params };
  c.setParams({ x: 1.5, z: 1.0 });
  return out;
});
check('params clamp to the axis spec', clampTest.x === 2.5 && clampTest.z === 0.8, JSON.stringify(clampTest));

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

// --- §C1: a steps axis SNAPS to a rebuilt variant, out of one cache ---------
// The claim is not "it looks different at x=2" — it is that the fridge is a
// DIFFERENT BUILT OBJECT there (more parts, its own geometry), that coming back
// to x=1 returns the very same BufferGeometry rather than rebuilding one, and
// that two fridges at the same step share it — which is what lets the instanced
// batch group them.
const stepsTest = await page.evaluate(() => {
  const fridge = __app.placed.find((m) => m.typeId === 'fridge_cabinet');
  const geo = () => fridge.meshes[0].geometry;
  const verts = () => geo().getAttribute('position').count;

  fridge.setParams({ x: 1 });
  const one = { geo: geo(), verts: verts(), meshes: fridge.meshes.length };
  fridge.setParams({ x: 2 });
  const two = { geo: geo(), verts: verts(), meshes: fridge.meshes.length };
  fridge.setParams({ x: 1 });
  const back = geo();

  // a second fridge at the same step must land on the same cached geometry
  __app.selectType('fridge_cabinet');
  __app.ghost.group.position.set(3.1, 0, -0.9);
  __app.commit();
  const other = __app.placed[__app.placed.length - 1];
  other.setParams({ x: 2 });
  fridge.setParams({ x: 2 });
  const shared = other.meshes[0].geometry === fridge.meshes[0].geometry;

  // and a saved '2 doors' comes back as '2 doors', not as a number in between
  __app.save();
  __app.clearScene();
  const emptied = __app.placed.length;
  __app.load();
  const loaded = __app.placed.filter((m) => m.typeId === 'fridge_cabinet');
  const restored = loaded.length === 2 && loaded.every((m) => m.params.x === 2);
  const clamps = (() => {
    const m = loaded[0];
    m.setParams({ x: 2.6 }); // a stale/hand-edited save value
    const snapped = m.params.x;
    m.setParams({ x: 1 });
    return snapped;
  })();
  return {
    grew: two.verts > one.verts,
    rebuilt: one.geo !== two.geo,
    cacheHit: back === one.geo,
    oneMesh: one.meshes === 1 && two.meshes === 1,
    shared, emptied, restored, clamps,
    verts: [one.verts, two.verts],
  };
});
check(
  'a steps axis rebuilds the fridge as a wider variant, cached and shared',
  stepsTest.grew && stepsTest.rebuilt && stepsTest.cacheHit && stepsTest.oneMesh &&
    stepsTest.shared && stepsTest.emptied === 0 && stepsTest.restored && stepsTest.clamps === 3,
  `'1 door' ${stepsTest.verts[0]} verts → '2 doors' ${stepsTest.verts[1]} verts in one mesh (no repeat, no stretch); ` +
  `back to '1 door' is the same cached geometry object${stepsTest.cacheHit ? '' : ' [FAILED]'}, ` +
  `two fridges at '2 doors' share one${stepsTest.shared ? '' : ' [FAILED]'}, ` +
  `save → clear → load restores both at '2 doors'${stepsTest.restored ? '' : ' [FAILED]'}, ` +
  `and an off-step 2.6 snaps to ${stepsTest.clamps}`
);
// leave the scene as the rest of the checks expect it
await page.evaluate(() => {
  __app.clearScene();
  __app.load();
  const extra = __app.placed.filter((m) => m.typeId === 'fridge_cabinet').pop();
  const i = __app.placed.indexOf(extra);
  if (i >= 0) __app.placed.splice(i, 1);
  extra.dispose();
  __app.placed.find((m) => m.typeId === 'fridge_cabinet').setParams({ x: 1 });
  __app.setMode('select');
  __app.refreshStats();
  __app.save();
});


// --- §C2: the same trick on the two objects that most needed it ------------
// The counter's length was a stretch axis (one drawer three metres long); the
// lockers' height was FIXED because there was no honest way to stretch it. Both
// step now, and the claims are the same two: the default step is the object
// that was there before, part for part, and the other steps are DIFFERENT built
// objects — plus, on the lockers, that a steps axis composes with the repeat
// axis beside it (three bays of a three-tier bay, one geometry, three meshes,
// standing on the floor rather than sunk into it).
const c2 = await page.evaluate(() => {
  const counter = __app.placed.find((m) => m.typeId === 'serving_counter');
  const lockers = __app.placed.find((m) => m.typeId === 'locker_bank');
  const geo = (m) => m.meshes[0].geometry;
  const verts = (m) => geo(m).getAttribute('position').count;
  const tall = lockers.def.axes.y.steps[1].v;

  counter.setParams({ x: 1.5 });
  const two = { verts: verts(counter), geo: geo(counter), meshes: counter.meshes.length };
  counter.setParams({ x: 2.5 });
  const four = { verts: verts(counter), meshes: counter.meshes.length };
  counter.setParams({ x: 1.5 });
  const counterCached = geo(counter) === two.geo;

  lockers.setParams({ x: 3, y: 1 });
  const t2 = { verts: verts(lockers), meshes: lockers.meshes.length, floor: lockers.meshes[0].position.y };
  lockers.setParams({ y: tall });
  const t3 = {
    verts: verts(lockers),
    meshes: lockers.meshes.length,
    floor: lockers.meshes[0].position.y,
    shared: lockers.meshes.every((m) => m.geometry === geo(lockers)),
    spread: lockers.meshes.map((m) => m.position.x),
    height: lockers.footprint[1],
  };
  lockers.setParams({ y: 1 });
  // The default step has to BE the object that was there before the axis
  // existed: 26 parts is the pre-§C2 locker bay, part for part.
  const defaultParts = lockers.def.build({ x: 3, y: 1 }).length;
  return { two, four, counterCached, t2, t3, tall, defaultParts };
});
check(
  'a steps axis rebuilds the counter in bays and the lockers in tiers',
  c2.four.verts > c2.two.verts && c2.four.meshes === 1 && c2.two.meshes === 1 && c2.counterCached &&
    c2.t3.verts > c2.t2.verts && c2.t3.meshes === 3 && c2.t3.shared &&
    Math.abs(c2.t2.floor - 0.9) < 1e-6 && Math.abs(c2.t3.floor - 0.9 * c2.tall) < 1e-6 &&
    Math.abs(c2.t3.height - 0.9 * c2.tall) < 1e-6 && c2.defaultParts === 26,
  `counter '2 bays' ${c2.two.verts} verts → '4 bays' ${c2.four.verts} in one mesh, and back is the same cached ` +
  `geometry${c2.counterCached ? '' : ' [FAILED]'}; lockers '2 tiers' ${c2.t2.verts} verts → '3 tiers' ${c2.t3.verts}, ` +
  `still 3 repeat bays sharing one geometry${c2.t3.shared ? '' : ' [FAILED]'} at x ${c2.t3.spread.map((v) => v.toFixed(2)).join('/')}, ` +
  `lifted onto the floor at ${c2.t3.floor.toFixed(3)}m (2 tiers: ${c2.t2.floor.toFixed(3)}m); ` +
  `the default step is still the ${c2.defaultParts}-part bay it was before the axis existed${c2.defaultParts === 26 ? '' : ' [FAILED]'}`
);

// --- pixel helpers ---------------------------------------------------------
const grab = async (clip) => PNG.sync.read(await page.screenshot({ clip }));

function meanAbsDiff(a, b) {
  if (a.width !== b.width || a.height !== b.height) return Infinity;
  let sum = 0;
  for (let i = 0; i < a.data.length; i += 4) {
    sum += Math.abs(a.data[i] - b.data[i])
         + Math.abs(a.data[i + 1] - b.data[i + 1])
         + Math.abs(a.data[i + 2] - b.data[i + 2]);
  }
  return sum / (a.data.length / 4) / 3;
}

/** Fraction of pixels close to the ink colour — how much of the frame is line. */
function inkCoverage(png, [r, g, b] = [43, 31, 51], tol = 42) {
  let hits = 0, total = 0;
  for (let i = 0; i < png.data.length; i += 4) {
    total++;
    if (Math.abs(png.data[i] - r) < tol &&
        Math.abs(png.data[i + 1] - g) < tol &&
        Math.abs(png.data[i + 2] - b) < tol) hits++;
  }
  return hits / total;
}

// The software renderer can be down at a couple of frames a second, so wait on
// actual frames rather than on the clock.
const settle = (frames = 4) =>
  page.evaluate((n) => new Promise((resolve) => {
    let seen = 0;
    const tick = () => (++seen >= n ? resolve() : requestAnimationFrame(tick));
    requestAnimationFrame(tick);
  }), frames);
const CROP = { x: 340, y: 220, width: 340, height: 300 };
const CAP_CROP = { x: 420, y: 300, width: 440, height: 280 };

// --- Phase 2: the cap is pixel-identical before and after stretching -------
// The counter's DEPTH is its stretch axis now (§C2 made the length step), and
// the front face is where all its fittings live — the pull rails, the label
// plate, the customer shelf. Camera is anchored to that front plane and
// everything else is hidden, so the only thing that could change in the crop is
// the front cap itself.
async function capShot(scale) {
  await page.evaluate((s) => {
    const desk = __app.placed.find((m) => m.typeId === 'serving_counter');
    for (const m of __app.placed) for (const mesh of m.meshes) mesh.visible = m === desk;
    for (const m of __app.placed) if (m.shadow) m.shadow.visible = false;
    __app.setDecorVisible(false); // decor is atmosphere, not the geometry claim
    for (const k of ['floor', 'backWall', 'sideWall']) __app.room[k].visible = false;
    desk.setParams({ x: 1.5, z: s });
    // Anchor to the front cap wherever the counter actually stands and however
    // deep it is, so the crop frames the same fittings at any depth.
    const capZ = desk.group.position.z + desk.def.unit[2] * s;
    const x = desk.group.position.x - 1.0; // the end zone, with its vents on it
    // Eye level with the front, so the crop is front face and fittings and not
    // the worktop's top plane — the top is the one surface that genuinely gets
    // deeper, and framing it would be testing the stretch, not the cap.
    __app.camera.position.set(x - 0.85, 0.46, capZ + 1.75);
    __app.controls.target.set(x + 0.30, 0.34, capZ);
    __app.controls.update();
  }, scale);
  await settle();
  return grab(CAP_CROP);
}

const capAt1 = await capShot(0.8);
await page.screenshot({ path: `${shotDir}/04-cap-at-1x.png`, clip: CAP_CROP });
const capAt4 = await capShot(1.6);
// Write the artefact while the counter is still deep — after the restore it
// would be a picture of something else entirely.
await page.screenshot({ path: `${shotDir}/04-cap-at-4x.png`, clip: CAP_CROP });
await page.evaluate(() => {
  __app.placed.find((m) => m.typeId === 'serving_counter').setParams({ x: 1.5, z: 1.0 });
  __app.setDecorVisible(true);
});
const capDiff = meanAbsDiff(capAt1, capAt4);
check(
  'nine-slice: the front cap is unchanged from 0.8× to 1.6× depth',
  capDiff < 4,
  `mean channel difference ${capDiff.toFixed(2)}/255 over the cap crop`
);

// --- Phase 3: the triplanar floor does not swim ---------------------------
// Object space means the texture travels WITH the panel. Move the floor by half
// a texture period and the pattern under a fixed screen point must change; a
// world-space projection would leave it pinned and identical.
const swim = await (async () => {
  await page.evaluate(() => {
    for (const m of __app.placed) {
      for (const mesh of m.meshes) mesh.visible = false;
      if (m.shadow) m.shadow.visible = false;
    }
    __app.setDecorVisible(false);
    __app.room.floor.visible = true;
    __app.camera.position.set(0, 2.6, 2.4);
    __app.controls.target.set(0, 0, 0);
    __app.controls.update();
  });
  await settle();
  const before = await grab(CROP);
  await page.screenshot({ path: `${shotDir}/06-triplanar-floor.png`, clip: CROP });
  const period = await page.evaluate(() => 1 / __app.room.floor.material.uniforms.uTextureScale.value);

  await page.evaluate((d) => { __app.room.floor.position.x = d; }, period * 0.5);
  await settle();
  const half = await grab(CROP);

  await page.evaluate((d) => { __app.room.floor.position.x = d; }, period);
  await settle();
  const full = await grab(CROP);

  await page.evaluate(() => { __app.room.floor.position.x = 0; });
  return {
    period,
    halfMoved: meanAbsDiff(before, half),
    fullMoved: meanAbsDiff(before, full),
  };
})();
check(
  'triplanar is object space: the texture travels with the panel',
  swim.halfMoved > 0.25 && swim.fullMoved < swim.halfMoved / 4,
  `half a period (${(swim.period / 2).toFixed(2)}m) shifts the crop by ${swim.halfMoved.toFixed(2)}/255, a whole period by ${swim.fullMoved.toFixed(2)} — the pattern is carried by the panel, not pinned to the world`
);

// --- Phase 4: outlines stay ~1px and do not flood when zoomed out ---------
const inkAt = async (distance) => {
  await page.evaluate((d) => {
    __app.outline.enabled = true; // off in the shipped look; this checks the pass
    for (const m of __app.placed) {
      for (const mesh of m.meshes) mesh.visible = true;
      if (m.shadow) m.shadow.visible = true;
    }
    __app.setDecorVisible(true);
    for (const k of ['floor', 'backWall', 'sideWall']) __app.room[k].visible = true;
    __app.camera.position.set(d * 0.55, d * 0.42, d * 0.72);
    __app.controls.target.set(0, 0.8, 0);
    __app.controls.update();
  }, distance);
  await settle();
  return inkCoverage(await grab({ x: 0, y: 0, width: 1000, height: 800 }));
};
const inkNear = await inkAt(3);
const inkFar = await inkAt(30);
await page.evaluate(() => { __app.outline.enabled = false; });
check(
  'the outline pass holds from 3m to 30m without flooding (off by default)',
  inkNear > 0.001 && inkFar > 0.0005 && inkFar < 0.12,
  `ink covers ${(inkNear * 100).toFixed(2)}% of the frame at 3m and ${(inkFar * 100).toFixed(2)}% at 30m`
);
await page.screenshot({ path: `${shotDir}/05-zoomed-out.png` });

// --- §8.4: decor fills the module as it grows, and never reshuffles -------
const decorTest = await page.evaluate(() => {
  const desk = __app.placed.find((m) => m.typeId === 'dispensing_desk');
  const snapshot = () =>
    [...desk.decor.live.entries()].map(([k, v]) => `${k}:${v.type}`).sort();

  desk.setParams({ x: 2 });
  const two = snapshot();
  desk.setParams({ x: 5 });
  const five = snapshot();
  desk.setParams({ x: 2 });
  const back = snapshot();

  return {
    two: two.length,
    five: five.length,
    kept: two.filter((e) => five.includes(e)).length,
    stable: JSON.stringify(two) === JSON.stringify(back),
  };
});
check(
  'decor pops in with new bays and leaves the old ones alone',
  decorTest.five > decorTest.two && decorTest.kept === decorTest.two && decorTest.stable,
  `2 bays carry ${decorTest.two} props, 5 bays carry ${decorTest.five}; all ${decorTest.kept} original props unchanged, and resizing back restores exactly the same set`
);
await page.evaluate(() => {
  __app.placed.find((m) => m.typeId === 'dispensing_desk').setParams({ x: 3 });
});

// --- Phase 6: many modules, one draw call ---------------------------------
const instTest = await page.evaluate(async () => {
  const settle = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  await settle();
  const before = __app.stats.drawCalls;
  const batch = __app.stressTest(200);
  await settle();
  return { instances: batch.count, before, after: __app.stats.drawCalls };
});
check(
  'instanced batch adds one draw call for 200 modules',
  instTest.instances >= 200 && instTest.after - instTest.before <= 2,
  `${instTest.instances} instances cost ${instTest.after - instTest.before} extra draw call(s); scene total ${instTest.after} (every object is drawn twice — beauty plus the outline prepass)`
);
await page.evaluate(() => __app.clearBatch());

// --- AdaptivePropBase: 9-slice + slot spawner on a standalone prop ---------
// The interesting property is not "more props appear" — it is that the ones
// already there DO NOT MOVE OR CHANGE when more appear beside them. A spawner
// that reshuffles on every resize looks broken while you drag the handle.
const adaptive = await page.evaluate(async () => {
  await __app.nanoAtlasReady;
  const prop = __app.makeAdaptiveProp({
    parts: [
      { size: [1.2, 0.06, 0.6], at: [0, 0.44, 0], mat: 'wood' },
      { size: [1.1, 0.8, 0.55], at: [0, 0.02, 0], mat: 'panel' },
    ],
    halfExtents: [0.6, 0.47, 0.3],
    margins: [0.16, 0, 0],
    propSpacing: 0.4,
    socketY: 0.47,
    seed: 12345,
  });

  // Types and positions are checked separately on purpose. The prop grows
  // SYMMETRICALLY about its origin, so its left edge moves and every slot
  // shifts with it — positions are expected to change on a grow. What must not
  // change is what each slot HOLDS.
  const types = () => Object.fromEntries([...prop.decor.live].map(([k, v]) => [k, v.type]));
  const full = () => Object.fromEntries(
    [...prop.decor.live].map(([k, v]) => [k, `${v.type}@${v.mesh.position.x.toFixed(4)}`])
  );

  prop.updateSize(1, 1, 1);
  const small = { slots: prop.availableSlots, types: types(), full: full(), scale: prop.material.uniforms.uTargetScale.value.x };
  prop.updateSize(3, 1, 1);
  const big = { slots: prop.availableSlots, types: types(), scale: prop.material.uniforms.uTargetScale.value.x };
  prop.updateSize(1, 1, 1);
  const back = { slots: prop.availableSlots, full: full() };

  prop.dispose();
  return { small, big, back };
});

const keptOnGrow = Object.keys(adaptive.small.types)
  .every((k) => adaptive.big.types[k] === adaptive.small.types[k]);
const restored = JSON.stringify(adaptive.small.full) === JSON.stringify(adaptive.back.full);
const slotsScale = adaptive.big.slots === 3 * adaptive.small.slots;
check(
  'AdaptivePropBase resizes on the GPU and fills the new space without disturbing the old',
  slotsScale && adaptive.big.scale === 3 && adaptive.small.scale === 1 && keptOnGrow && restored,
  `${adaptive.small.slots} slots at 1x -> ${adaptive.big.slots} at 3x (uTargetScale.x drives the 9-slice, mesh transform untouched); ` +
  `all ${Object.keys(adaptive.small.types).length} original slots kept their prop on grow${keptOnGrow ? '' : ' [FAILED]'}, ` +
  `and shrinking restored them position-identical${restored ? '' : ' [FAILED]'}`
);

// --- screenshots ----------------------------------------------------------
await page.evaluate(() => {
  __app.setMode('select'); // put the ghost away
  __app.camera.position.set(8.4, 6.2, 9.6);
  __app.controls.target.set(-0.8, 0.9, -0.6);
  __app.controls.update();
});
await page.mouse.move(20, 780);
await page.waitForTimeout(500);
await page.screenshot({ path: `${shotDir}/01-scene.png` });

await page.evaluate(() => {
  __app.camera.position.set(1.75, 1.66, 2.35);
  __app.controls.target.set(-0.65, 0.72, -0.4);
  __app.controls.update();
});
await page.waitForTimeout(500);
await page.screenshot({ path: `${shotDir}/03-desk.png` });

await browser.close();

const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
if (problems.length) console.log('console output:\n' + problems.join('\n'));
process.exit(failed.length ? 1 : 0);
