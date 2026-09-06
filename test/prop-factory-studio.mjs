import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const port = 5199;
const origin = `http://127.0.0.1:${port}`;
const child = spawn(process.execPath, ['tools/prop-factory/studio/server.mjs'], {
  cwd: root,
  env: { ...process.env, PROP_STUDIO_PORT: String(port) },
  stdio: ['ignore', 'pipe', 'pipe'],
});

const started = new Promise((resolve, reject) => {
  const timer = setTimeout(() => reject(new Error('Studio server did not start')), 10_000);
  child.stdout.on('data', chunk => {
    if (String(chunk).includes(origin)) { clearTimeout(timer); resolve(); }
  });
  child.stderr.on('data', chunk => process.stderr.write(chunk));
  child.once('exit', code => reject(new Error(`Studio server exited with ${code}`)));
});

let browser;
try {
  await started;
  const health = await fetch(`${origin}/api/health`).then(response => response.json());
  assert.equal(health.ok, true);
  assert.equal(health.ollama, true, 'Ollama should be reachable for the Studio smoke test');
  assert(health.models.some(model => model.capabilities?.includes('completion')));
  assert(health.models.some(model => model.capabilities?.includes('vision')), 'Vision capability discovery should use /api/show');
  assert.equal((await fetch(`${origin}/vendor/three.module.js`)).status, 200);
  assert.equal((await fetch(`${origin}/vendor/three.core.js`)).status, 200);

  const invalid = await fetch(`${origin}/api/jobs`, {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({}),
  });
  assert.equal(invalid.status, 400);

  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  await page.goto(origin, { waitUntil: 'networkidle' });
  assert.equal(await page.locator('#emptyStage').isVisible(), true);
  assert.equal(await page.locator('#stageProgress').isVisible(), false);
  assert.equal(await page.locator('#stageError').isVisible(), false);
  assert(await page.locator('#visionModel option').count() >= 1);
  assert.deepEqual(pageErrors, []);
  console.log('Prop Factory Studio smoke test passed');
} finally {
  await browser?.close();
  child.kill();
}
