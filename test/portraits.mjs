// One framed portrait per module — the missing half of the §11.1 loop.
//
//   npm run build && npm run preview &
//   node test/portraits.mjs test/shots/portraits
//
// docs/concept/ holds what each module is SUPPOSED to look like; this writes
// what it actually looks like, at the same framing, one file per module. Put
// the two side by side and the disagreements are obvious in a way that no
// amount of reading a part list will give you — it is how the racking was
// caught with cream shelf boards where its sheet has oak ones.
//
// Not part of `npm test`: it asserts nothing. It is for your eye, which §11.3
// is explicit is the thing the pipeline cannot supply.
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const out = process.argv[2] ?? 'test/shots/portraits';
mkdirSync(out, { recursive: true });

const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH,
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
});
const page = await browser.newPage({ viewport: { width: 640, height: 520 } });
page.on('pageerror', (e) => console.error('PAGEERROR', e.message));
await page.goto('http://localhost:4173/', { waitUntil: 'load' });
await page.waitForFunction(() => !!globalThis.__app, null, { timeout: 20000 });
await page.evaluate(() => __app.texturesReady);
await page.waitForTimeout(1200);

// the portrait is of the module, not of the UI
await page.addStyleTag({ content: '#catalogue, #help, .lil-gui, .stats { display: none !important }' });

const names = await page.evaluate(() => __app.moduleIds);
console.log(`${names.length} modules -> ${out}`);

for (const id of names) {
  await page.evaluate(({ mid, rot }) => {
    __app.clearScene();
    __app.selectType(mid);
    __app.ghost.group.position.set(0, 0, 0);
    __app.commit();
    __app.ghost.group.visible = false; // or it ghosts over the real one
    const m = __app.placed[__app.placed.length - 1];
    m.group.rotation.y = rot;

    // frame the camera on the module's own bounds, from the style bible's angle
    const box = { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] };
    m.group.updateMatrixWorld(true); // the rotation above is not in matrixWorld yet
    m.group.traverse((o) => {
      if (!o.isMesh) return;
      o.geometry.computeBoundingBox();
      const bb = o.geometry.boundingBox.clone().applyMatrix4(o.matrixWorld);
      for (const a of ['x', 'y', 'z']) {
        const i = { x: 0, y: 1, z: 2 }[a];
        box.min[i] = Math.min(box.min[i], bb.min[a]);
        box.max[i] = Math.max(box.max[i], bb.max[a]);
      }
    });
    const c = box.min.map((v, i) => (v + box.max[i]) / 2);
    // the diagonal, not the longest edge: a tall thin cabinet framed on its
    // height alone put the camera inside it and cropped the top off.
    const d = box.max.map((v, i) => v - box.min[i]);
    const r = Math.hypot(d[0], d[1], d[2]) * 0.62 + 0.35;
    __app.controls.target.set(c[0], c[1], c[2]);
    __app.camera.position.set(c[0] + r * 1.5, c[1] + r * 1.15, c[2] + r * 2.0);
    __app.camera.lookAt(c[0], c[1], c[2]);
    __app.controls.update();
  }, { mid: id, rot: Number(process.env.PORTRAIT_ROT ?? -0.62) });
  await page.waitForTimeout(450);
  await page.screenshot({ path: `${out}/${id}.png` });
  console.log(' ', id);
}

await browser.close();
