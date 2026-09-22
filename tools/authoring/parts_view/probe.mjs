// Load the prop page at a given size and print what is actually in the scene.
//
//   node tools/authoring/parts_view/probe.mjs \
//        "dir=/tools/img2threejs-work/v8_arcade_cabinet&w=2"
//
// Authoring tool. NOT a build, CI or runtime dependency. Needs the dev server.
//
// WHY. raycast.mjs answers "what is under this pixel"; this answers "what is in
// the scene and how big is it", which is the question every resize invariant
// needs and which a screenshot cannot answer at all. It had been written inline
// in a scratch file three times before it earned a name.
//
// Prints one JSON object: the prop's own frame, and for every placed part its
// world axis-aligned box, its instance count, and the rules it was built from.
import { chromium } from 'playwright';

const query = process.argv[2];
if (!query) {
  console.error('usage: probe.mjs "<query string>"');
  process.exit(2);
}
const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH
    || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-gl=angle', '--use-angle=swiftshader',
         '--enable-unsafe-swiftshader', '--no-sandbox'],
});
const page = await browser.newPage({ viewport: { width: 700, height: 700 } });
const errs = [];
page.on('pageerror', (e) => errs.push(e.message));
await page.goto(
  `http://localhost:5173/tools/authoring/parts_view/index.html?${query}`,
  { waitUntil: 'load' });
try {
  await page.waitForFunction(() => globalThis.__done === true, null,
                             { timeout: 40000 });
} catch {
  console.log(JSON.stringify({ error: 'never finished', errs }));
  await browser.close();
  process.exit(1);
}
const out = await page.evaluate(() => {
  const T = globalThis.__three, sc = globalThis.__scene;
  const body = sc.getObjectByName('body');
  const bb = new T.Box3().setFromObject(body);
  const parts = {};
  // THE PART'S OWN MESHES, NOT ITS SUBTREE. A rider is re-parented to the host
  // it is bolted to, so setFromObject on a pivot returns the host AND whatever
  // travels with it: v26_arcade_cabinet's start button came back 12 times its
  // own width on a cabinet twice as wide, because a per-bay decal hosted on it
  // put one copy at each end of the machine. Nothing was wrong with the button.
  const boxOf = (o) => {
    const b = new T.Box3();
    const walk = (n, root) => {
      if (!root && n.userData && n.userData.part) return;   // another part
      if (n.isMesh) b.expandByObject(n);
      for (const c of n.children) walk(c, false);
    };
    walk(o, true);
    return b;
  };
  sc.traverse((o) => {
    const u = o.userData;
    if (!u || !u.part) return;
    const b = boxOf(o);
    if (!isFinite(b.min.x)) return;
    const e = parts[u.part] || (parts[u.part] = {
      n: 0, resize: u.resize, resize_y: u.resize_y, lengthens: u.lengthens,
      drawn: u.drawn, reach: u.reach,
      anchor: u.anchor, depth: u.depth,
      motion: u.motion, bays: u.bays || 1, tiers: u.tiers || 1, boxes: [],
    });
    e.n += 1;
    e.boxes.push([b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z]
      .map((v) => +v.toFixed(5)));
    // AND ITS SIZE IN ITS OWN FRAME, WHICH IS THE ONE "held at its drawn size"
    // IS ABOUT. A world box is axis-aligned, so a part turned ten degrees to
    // lie in a chamfer reports its own DEPTH swung into its width -- and on a
    // part a few hundredths wide that is a fifth of it. v15_arcade_cabinet's
    // decal came back 1.19x on a cabinet twice as wide and had not changed size
    // at all: with ?twist=0 the same measurement is 1.001x.
    const lb = new T.Box3();
    const walkL = (n, root) => {
      if (!root && n.userData && n.userData.part) return;
      if (n.isMesh && n.geometry) {
        n.geometry.computeBoundingBox();
        const g = n.geometry.boundingBox.clone();
        g.applyMatrix4(n.matrix);
        lb.union(g);
      }
      for (const c of n.children) walkL(c, false);
    };
    walkL(o, true);
    e.local = [+(lb.max.x - lb.min.x).toFixed(5),
               +(lb.max.y - lb.min.y).toFixed(5),
               +(lb.max.z - lb.min.z).toFixed(5)];
  });
  return {
    body: [bb.min.x, bb.min.y, bb.min.z, bb.max.x, bb.max.y, bb.max.z]
      .map((v) => +v.toFixed(5)),
    parts,
  };
});
out.errs = errs;
console.log(JSON.stringify(out));
await browser.close();
