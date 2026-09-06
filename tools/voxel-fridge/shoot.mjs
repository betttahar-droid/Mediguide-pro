import { spawn, spawnSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { PNG } from 'pngjs';
import { chromium } from 'playwright';

const outDir = path.resolve(process.argv[2] ?? 'docs/reference-lock/vaccine-fridge-v1/recipe-v10');
const queries = process.argv.slice(3).length ? process.argv.slice(3) : ['view=front', 'view=iso'];
mkdirSync(outDir, { recursive: true });
const port = 5189;
const server = spawn(process.env.ComSpec ?? 'cmd.exe', [
  '/d', '/s', '/c', `npm.cmd run dev -- --host 127.0.0.1 --port ${port}`,
], {
  cwd: process.cwd(), shell: false, stdio: ['ignore', 'pipe', 'pipe'],
});
let serverLog = '';
server.stdout.on('data', (chunk) => { serverLog += chunk; });
server.stderr.on('data', (chunk) => { serverLog += chunk; });

const waitForServer = async () => {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/tools/voxel-fridge/index.html`);
      if (response.ok) return;
    } catch {}
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
    await page.goto(`http://127.0.0.1:${port}/tools/voxel-fridge/index.html?${query}`, { waitUntil: 'networkidle' });
    await page.waitForFunction(() => window.__VOXEL_FRIDGE_STATS__?.ready);
    const stats = await page.evaluate(() => window.__VOXEL_FRIDGE_STATS__);
    const label = query.replaceAll('=', '-').replaceAll('&', '-').replaceAll('.', '_');
    const output = path.join(outDir, `${label}.png`);
    const buffer = await page.screenshot({ path: output });
    const png = PNG.sync.read(buffer);
    const colors = new Set();
    const colorBuckets = new Set();
    for (let index = 0; index < png.data.length; index += 4) {
      colors.add(`${png.data[index]},${png.data[index + 1]},${png.data[index + 2]}`);
      colorBuckets.add(`${png.data[index] >> 3},${png.data[index + 1] >> 3},${png.data[index + 2] >> 3}`);
    }
    stats.paletteSize = colors.size;
    stats.paletteBuckets5Bit = colorBuckets.size;
    const diagnostic = query.includes('diagnostic=');
    const minimumPalette = diagnostic ? 2 : (query.includes('decals=0') ? 10 : 25);
    const maximumPalette = diagnostic ? 120 : 60;
    if (stats.paletteSize < minimumPalette || stats.paletteSize > maximumPalette) {
      errors.push(`palette size ${stats.paletteSize} is outside ${minimumPalette}-${maximumPalette}`);
    }
    if (stats.triangles < 300 || stats.triangles > 5000) {
      errors.push(`triangle count ${stats.triangles} is outside 300-5000`);
    }
    stats.errors = errors;
    records.push({ query, output, ...stats });
    console.log(JSON.stringify({ output, ...stats }));
    if (errors.length) throw new Error(errors.join('\n'));
    await page.close();
  }
  const oneX = records.find((item) => item.scale.every((value) => value === 1));
  const resized = records.find((item) => item.scale.some((value) => value !== 1));
  const fixedDecalsMatch = !oneX || !resized
    || JSON.stringify(oneX.protectedDecalSizes) === JSON.stringify(resized.protectedDecalSizes);
  const rigidPartsMatch = !oneX || !resized
    || JSON.stringify(oneX.rigidPartSizes) === JSON.stringify(resized.rigidPartSizes);
  const oneAdaptive = oneX?.adaptiveDecalCounts.reduce((sum, [, count]) => sum + count, 0) ?? 0;
  const resizedAdaptive = resized?.adaptiveDecalCounts.reduce((sum, [, count]) => sum + count, 0) ?? 0;
  const adaptiveDecalsGrow = !oneX || !resized || (oneAdaptive === 0 && resizedAdaptive === 0)
    || resizedAdaptive > oneAdaptive;
  const countsAdapt = !oneX || !resized || resized.parts > oneX.parts || adaptiveDecalsGrow;
  const audit = {
    status: records.every((item) => item.errors.length === 0)
      && fixedDecalsMatch && rigidPartsMatch && countsAdapt && adaptiveDecalsGrow ? 'PASS' : 'FAIL',
    fixedDecalsMatch,
    rigidPartsMatch,
    adaptiveDecalsGrow,
    structuralCountsAdapt: countsAdapt,
    records,
  };
  writeFileSync(path.join(outDir, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
  if (audit.status !== 'PASS') throw new Error(`acceptance audit failed: ${JSON.stringify(audit)}`);
  await browser.close();
} finally {
  if (process.platform === 'win32') {
    spawnSync('taskkill.exe', ['/pid', String(server.pid), '/t', '/f'], { stdio: 'ignore' });
  } else {
    server.kill();
  }
}
