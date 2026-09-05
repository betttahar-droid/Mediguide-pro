// Shoot the voxel-fridge prototype at several views and COUNT what came out.
// The count is the point: a pixel-art palette is a couple of dozen colours, so
// "it looks about right" is not evidence and a colour count is.
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const out = process.argv[2] ?? '.';
const shots = process.argv.slice(3);
mkdirSync(out, { recursive: true });

const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH,
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
});
const page = await browser.newPage({ viewport: { width: 1400, height: 1100 } });
const errs = [];
page.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
page.on('console', (m) => {
  if (m.type() === 'error' && !m.text().includes('favicon')) errs.push('console: ' + m.text());
  else if (m.text().startsWith('palette:') || m.text().startsWith('geometry:'))
    console.log('   ' + m.text());
});

for (const q of shots) {
  const name = q.replace(/[^a-z0-9]+/gi, '-') || 'default';
  await page.goto(`http://localhost:5173/tools/voxel-fridge/index.html?${q}`,
                  { waitUntil: 'load' });
  await page.waitForFunction(() => globalThis.__done === true, null, { timeout: 20000 });
  const canvas = await page.$('canvas');
  await canvas.screenshot({ path: `${out}/${name}.png` });

  // distinct colours, and how much of the frame the object actually covers
  const stat = await page.evaluate(() => {
    const cv = document.querySelector('canvas');
    const c = document.createElement('canvas');
    c.width = cv.width; c.height = cv.height;
    c.getContext('2d').drawImage(cv, 0, 0);
    const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
    const seen = new Set();
    for (let i = 0; i < d.length; i += 4) seen.add((d[i] << 16) | (d[i + 1] << 8) | d[i + 2]);
    return { w: c.width, h: c.height, colours: seen.size };
  });
  console.log(`${name.padEnd(22)} ${stat.w}x${stat.h}  ${stat.colours} colours`);
}
if (errs.length) console.log('ERRORS:\n  ' + errs.slice(0, 8).join('\n  '));
await browser.close();
