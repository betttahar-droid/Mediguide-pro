import { spawn, spawnSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { PNG } from 'pngjs';
import { chromium } from 'playwright';

const outDir = path.resolve(process.argv[2] ?? 'docs/reference-lock/semantic-freezer-v1/runtime');
const queries = process.argv.slice(3).length ? process.argv.slice(3) : ['view=front', 'view=iso'];
mkdirSync(outDir, { recursive: true });
const port = 5191;
const server = spawn(process.env.ComSpec ?? 'cmd.exe', ['/d', '/s', '/c', `npm.cmd run dev -- --host 127.0.0.1 --port ${port}`], {
  cwd: process.cwd(), shell: false, stdio: ['ignore', 'pipe', 'pipe'],
});
let serverLog = '';
server.stdout.on('data', (chunk) => { serverLog += chunk; });
server.stderr.on('data', (chunk) => { serverLog += chunk; });
const waitForServer = async () => {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try { if ((await fetch(`http://127.0.0.1:${port}/tools/semantic-freezer/index.html`)).ok) return; } catch {}
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Vite did not start\n${serverLog}`);
};

try {
  await waitForServer();
  const browser = await chromium.launch({ headless: true });
  const records = [];
  for (const query of queries) {
    const page = await browser.newPage({ viewport: { width: 640, height: 800 }, deviceScaleFactor: 1 });
    const errors = [];
    page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()); });
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(`http://127.0.0.1:${port}/tools/semantic-freezer/index.html?${query}`, { waitUntil: 'networkidle' });
    await page.waitForFunction(() => window.__SEMANTIC_FREEZER_STATS__?.ready);
    const stats = await page.evaluate(() => window.__SEMANTIC_FREEZER_STATS__);
    const label = query.replaceAll('=', '-').replaceAll('&', '-').replaceAll('.', '_');
    const output = path.join(outDir, `${label}.png`);
    const buffer = await page.screenshot({ path: output });
    const png = PNG.sync.read(buffer);
    const colors = new Set();
    for (let index = 0; index < png.data.length; index += 4) colors.add(`${png.data[index]},${png.data[index + 1]},${png.data[index + 2]}`);
    stats.paletteSize = colors.size;
    const diagnostic = new URLSearchParams(query).get('diagnostic') ?? '';
    const raw = query.includes('surfaces=0');
    const v2 = query.includes('texture=v2') || query.includes('texture=v3') || query.includes('texture=v4') || query.includes('texture=v5') || query.includes('texture=v6') || query.includes('texture=v7');
    const continuousDiagnostic = ['normal', 'face-normal', 'depth', 'linear-depth'].includes(diagnostic);
    const minimum = diagnostic ? 2 : (raw ? 10 : (v2 ? 32 : 25));
    const maximum = continuousDiagnostic ? 20000 : (diagnostic ? 500 : ((query.includes('texture=v6') || query.includes('texture=v7')) ? 4000 : (query.includes('texture=v5') ? 2000 : (v2 ? 600 : 60))));
    if (stats.paletteSize < minimum || stats.paletteSize > maximum) errors.push(`palette ${stats.paletteSize} outside ${minimum}-${maximum}`);
    if (stats.triangles < 1000 || stats.triangles > 5000) errors.push(`triangles ${stats.triangles} outside 1000-5000`);
    stats.errors = errors;
    records.push({ query, output, ...stats });
    console.log(JSON.stringify({ output, ...stats }));
    if (errors.length) throw new Error(errors.join('\n'));
    await page.close();
  }
  const normal = records.find((record) => record.scale.every((value) => value === 1));
  const resized = records.find((record) => record.scale.some((value) => value !== 1));
  const audit = {
    status: records.every((record) => !record.errors.length)
      && (!normal || !resized || (
        JSON.stringify(normal.rigidPartSizes) === JSON.stringify(resized.rigidPartSizes)
        && JSON.stringify(normal.fixedFittingSizes) === JSON.stringify(resized.fixedFittingSizes)
      )) ? 'PASS' : 'FAIL',
    rigidPartsMatch: !normal || !resized || JSON.stringify(normal.rigidPartSizes) === JSON.stringify(resized.rigidPartSizes),
    fixedFittingsMatch: !normal || !resized || JSON.stringify(normal.fixedFittingSizes) === JSON.stringify(resized.fixedFittingSizes),
    records,
  };
  writeFileSync(path.join(outDir, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
  if (audit.status !== 'PASS') throw new Error('semantic freezer audit failed');
  await browser.close();
} finally {
  if (process.platform === 'win32') spawnSync('taskkill.exe', ['/pid', String(server.pid), '/t', '/f'], { stdio: 'ignore' });
  else server.kill();
}
