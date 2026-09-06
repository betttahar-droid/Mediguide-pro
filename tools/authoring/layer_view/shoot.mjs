// Screenshot the PS1 textured prop page. Needs the dev server up:
//   npx vite --port 5173 &
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';
const out = process.argv[2] ?? '.';
mkdirSync(out, { recursive: true });
const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH,
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
});
const page = await browser.newPage({ viewport: { width: 1100, height: 1100 } });
page.on('pageerror', (e) => console.log('PAGEERROR: ' + e.message));
page.on('console', (m) => console.log('  ' + m.text()));
for (const q of process.argv.slice(3)) {
  await page.goto(`http://localhost:5173/tools/authoring/layer_view/index.html?${q}`, { waitUntil: 'load' });
  try { await page.waitForFunction(() => globalThis.__done === true, null, { timeout: 20000 }); }
  catch { console.log('never finished: ' + q); continue; }
  await (await page.$('canvas')).screenshot({ path: `${out}/${q.replace(/[^a-z0-9]+/gi, '-')}.png` });
}
await browser.close();
