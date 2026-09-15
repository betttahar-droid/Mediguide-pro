// Name the object under a pixel of the render, and say what it is made of.
//
//   node tools/authoring/parts_view/raycast.mjs \
//        "dir=/tools/img2threejs-work/v49_jukebox&w=1&h=1.7" 0.46,0.78 0.5,0.3
//
// Authoring tool. NOT a build, CI or runtime dependency.
//
// WHY. CLAUDE.md's second rule is "identify the object before theorising about
// the cause", and it records a session spent testing six theories about a white
// band -- tint, cap, shelf, carcass, atlas, decal -- which a raycast settled in
// a minute. The rule was written; the tool it recommends was not, so every time
// it was needed someone wrote it again in a scratch file. This session that
// happened twice, and the second time the answer was "material index 1", which
// killed a theory about the carcass fill immediately.
//
// UVs are fractions of the canvas, 0,0 top-left.
import { chromium } from 'playwright';

const query = process.argv[2];
const points = process.argv.slice(3).map((s) => s.split(',').map(Number));
if (!query || !points.length) {
  console.error('usage: raycast.mjs "<query string>" u,v [u,v ...]');
  process.exit(2);
}
const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH,
  args: ['--use-gl=angle', '--use-angle=swiftshader',
         '--enable-unsafe-swiftshader', '--no-sandbox'],
});
const page = await browser.newPage({ viewport: { width: 1024, height: 1024 } });
const base = process.env.VIEW_URL
  ?? 'http://127.0.0.1:5173/tools/authoring/parts_view/';
await page.goto(`${base}?${query}`, { waitUntil: 'networkidle' });
await page.waitForTimeout(4000);
const hits = await page.evaluate((pts) => {
  const T = globalThis.__three, sc = globalThis.__scene, cam = globalThis.__cam;
  if (!T || !sc || !cam) return [{ error: 'no __three/__scene/__cam handles' }];
  const rc = new T.Raycaster();
  return pts.map(([u, v]) => {
    rc.setFromCamera(new T.Vector2(u * 2 - 1, 1 - v * 2), cam);
    const h = rc.intersectObjects(sc.children, true)[0];
    if (!h) return { at: [u, v], miss: true };
    // a multi-material mesh hands back the ARRAY, and reading .map or
    // .vertexColors off an array is how a probe lies to you: Array.prototype
    // has a `map`, so "does it have a texture" answered yes for everything.
    const mi = h.face?.materialIndex ?? 0;
    const m = Array.isArray(h.object.material) ? h.object.material[mi]
                                               : h.object.material;
    return {
      at: [u, v], object: h.object.name || '(unnamed)', materialIndex: mi,
      material: m?.name || m?.type,
      map: m?.map?.image?.currentSrc?.split('/').pop() || (m?.map ? 'yes' : 'none'),
      vertexColors: !!m?.vertexColors,
      uv: h.uv ? [+h.uv.x.toFixed(4), +h.uv.y.toFixed(4)] : null,
      point: ['x', 'y', 'z'].map((k) => +h.point[k].toFixed(4)),
      part: h.object.userData?.part ?? null,
    };
  });
}, points);
console.log(JSON.stringify(hits, null, 1));
await browser.close();
