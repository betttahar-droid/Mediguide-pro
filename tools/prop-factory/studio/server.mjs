import { createServer } from 'node:http';
import { readFile, writeFile, mkdir, readdir, stat } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { evidenceSchema, modelSpecSchema } from './model-schema.mjs';

const dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(dirname, '../../..');
const jobsRoot = path.join(root, 'work/prop-factory-studio');
const host = process.env.PROP_STUDIO_HOST ?? '127.0.0.1';
const port = Number(process.env.PROP_STUDIO_PORT ?? 5197);
const ollamaUrl = (process.env.OLLAMA_HOST ?? 'http://127.0.0.1:11434').replace(/\/$/, '');
const jobs = new Map();
let modelCache = { at: 0, models: [] };
const allowedImageTypes = new Map([
  ['image/png', '.png'], ['image/jpeg', '.jpg'], ['image/webp', '.webp'], ['image/gif', '.gif'],
]);

const json = (response, status, payload) => {
  response.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' });
  response.end(JSON.stringify(payload));
};
const safeId = (value) => String(value ?? '').toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-|-$/g, '').slice(0, 48);
const publicJob = (job) => ({
  id: job.id, title: job.title, prompt: job.prompt, status: job.status, phase: job.phase,
  message: job.message, progress: job.progress, iteration: job.iteration,
  createdAt: job.createdAt, updatedAt: job.updatedAt, models: job.models,
  referenceCount: job.references?.length ?? 0, audit: job.audit ?? null,
  modelSpec: job.modelSpec ?? null, evidence: job.evidence ?? null, error: job.error ?? null,
  viewerUrl: job.modelSpec ? `/runtime.html?job=${encodeURIComponent(job.id)}&revision=${job.iteration}` : null,
});
const saveJob = async (job) => {
  job.updatedAt = new Date().toISOString();
  await mkdir(job.directory, { recursive: true });
  await writeFile(path.join(job.directory, 'state.json'), `${JSON.stringify(publicJob(job), null, 2)}\n`);
};
const updateJob = async (job, patch) => { Object.assign(job, patch); await saveJob(job); };

const parseBody = async (request, maximum = 24 * 1024 * 1024) => {
  const chunks = []; let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > maximum) throw new Error('Request is larger than 24 MB');
    chunks.push(chunk);
  }
  return JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
};

const listModels = async () => {
  if (Date.now() - modelCache.at < 30_000) return modelCache.models;
  const result = await fetch(`${ollamaUrl}/api/tags`);
  if (!result.ok) throw new Error(`Ollama ${result.status}`);
  const payload = await result.json();
  const models = await Promise.all((payload.models ?? []).map(async model => {
    if (!model.capabilities?.includes('completion')) return model;
    try {
      const response = await fetch(`${ollamaUrl}/api/show`, {
        method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ model: model.name }),
      });
      if (!response.ok) return model;
      const details = await response.json();
      return { ...model, capabilities: [...new Set([...(model.capabilities ?? []), ...(details.capabilities ?? [])])] };
    } catch { return model; }
  }));
  modelCache = { at: Date.now(), models }; return models;
};

const ollamaChat = async ({ model, messages, format }) => {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12 * 60 * 1000);
  try {
    const response = await fetch(`${ollamaUrl}/api/chat`, {
      method: 'POST', headers: { 'content-type': 'application/json' }, signal: controller.signal,
      body: JSON.stringify({ model, messages, format, stream: false, keep_alive: '10m', options: { temperature: 0, seed: 7 } }),
    });
    if (!response.ok) throw new Error(`Ollama ${response.status}: ${await response.text()}`);
    const payload = await response.json();
    const content = payload.message?.content;
    if (!content) throw new Error('Ollama returned no message content');
    return { value: JSON.parse(content), usage: { prompt: payload.prompt_eval_count ?? 0, generated: payload.eval_count ?? 0 } };
  } finally { clearTimeout(timeout); }
};

const imagePayloads = async (job) => Promise.all(job.references.map(async (item) => (await readFile(item.path)).toString('base64')));
const analyze = async (job) => {
  if (!job.references.length) return {
    objectType: 'prompt-defined prop', confidence: .55, silhouette: job.prompt,
    visibleStructure: [], fixedDetails: [], materials: [], uncertainties: ['No image reference supplied'],
  };
  const images = await imagePayloads(job);
  const result = await ollamaChat({
    model: job.models.vision,
    format: evidenceSchema,
    messages: [{
      role: 'user', images,
      content: `Analyze these prop references for a retro low-poly adaptive 3D model. Treat visible evidence as authority. Separate silhouette structure from small fixed surface details. Do not invent hidden geometry. User request: ${job.prompt}`,
    }],
  });
  job.usage.vision = result.usage;
  return result.value;
};

const systemPrompt = `You are the planning stage of Prop Factory, a strict retro low-poly asset generator.
Return only the requested JSON schema. Build the silhouette from simple axis-aligned boxes. Use normalized bounds [left,bottom,front,right,top,back] from 0 to 1 and keep each lower bound smaller than its upper bound. Put handles, vents, labels, screens, fans, hinges and controls in fixedParts, not tiny geometry. Put only scalable repeated grids, panel divisions, or vent fields in adaptiveFields. Fixed parts use fixed world-unit sizes and corner anchors. Adaptive fields use fixed margins, pitch, and line width. Use a restrained five-color palette and readable PS1-era proportions. Do not include lighting gradients or random noise.`;
const generateSpec = async (job, revisionPrompt = '') => {
  const previous = job.modelSpec ? `\nPrevious model specification:\n${JSON.stringify(job.modelSpec)}` : '';
  const result = await ollamaChat({
    model: job.models.code,
    format: modelSpecSchema,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: `User request: ${job.prompt}\nReference evidence: ${JSON.stringify(job.evidence)}${previous}\nRevision request: ${revisionPrompt || 'Create the first accurate version.'}` },
    ],
  });
  job.usage.code = result.usage;
  return normalizeSpec(result.value, job.id);
};

const finite = (value, fallback) => Number.isFinite(Number(value)) ? Number(value) : fallback;
const clamp = (value, low, high) => Math.max(low, Math.min(high, finite(value, low)));
const normalizeSpec = (source, id) => {
  const spec = structuredClone(source);
  spec.id = id;
  for (const axis of ['width', 'depth', 'height']) spec.dimensions[axis] = clamp(spec.dimensions[axis], 8, axis === 'height' ? 240 : 200);
  const used = new Set();
  spec.parts = spec.parts.slice(0, 72).map((item, index) => {
    item.id = `structure-${safeId(item.id) || index + 1}`;
    while (used.has(item.id)) item.id = `${item.id}-${index + 1}`;
    used.add(item.id);
    item.role = 'structure';
    item.bevel = clamp(item.bevel, 0, Math.min(spec.dimensions.width, spec.dimensions.depth, spec.dimensions.height) * .025);
    item.bounds = item.bounds.map((value) => clamp(value, 0, 1));
    for (const [lo, hi] of [[0, 3], [1, 4], [2, 5]]) if (item.bounds[lo] >= item.bounds[hi]) {
      const center = (item.bounds[lo] + item.bounds[hi]) / 2;
      item.bounds[lo] = clamp(center - .025, 0, .95); item.bounds[hi] = clamp(center + .025, .05, 1);
    }
    return item;
  });
  spec.fixedParts = spec.fixedParts.slice(0, 32).map((item, index) => {
    item.id = `fixed-${safeId(item.id) || index + 1}`;
    while (used.has(item.id)) item.id = `${item.id}-${index + 1}`;
    used.add(item.id);
    item.offset = item.offset.map((value) => clamp(value, -48, 48));
    item.size = item.size.map((value) => clamp(value, .5, 64));
    item.depth = clamp(item.depth, .05, 8); item.text = String(item.text ?? '').slice(0, 24);
    return item;
  });
  spec.adaptiveFields = spec.adaptiveFields.slice(0, 16).map((item, index) => {
    item.id = `field-${safeId(item.id) || index + 1}`;
    while (used.has(item.id)) item.id = `${item.id}-${index + 1}`;
    used.add(item.id);
    item.margins = item.margins.map((value) => clamp(value, 0, 48));
    item.pitch = item.pitch.map((value) => clamp(value, 1, 32));
    item.lineWidth = item.lineWidth.map((value, axis) => clamp(value, .15, Math.max(.2, item.pitch[axis] * .45)));
    return item;
  });
  spec.style.topTint = clamp(spec.style.topTint, .9, 1.2);
  spec.style.frontTint = clamp(spec.style.frontTint, .78, 1.08);
  spec.style.sideTint = clamp(spec.style.sideTint, .58, .98);
  return spec;
};

const auditSpec = (spec) => {
  const ids = [...spec.parts, ...spec.fixedParts, ...spec.adaptiveFields].map((item) => item.id);
  const checks = {
    dimensionsSane: Object.values(spec.dimensions).every((value) => value >= 8 && value <= 240),
    enoughStructuralParts: spec.parts.length >= 3,
    uniqueIds: new Set(ids).size === ids.length,
    orderedBounds: spec.parts.every((item) => item.bounds[0] < item.bounds[3] && item.bounds[1] < item.bounds[4] && item.bounds[2] < item.bounds[5]),
    fixedPartsHaveWorldSizes: spec.fixedParts.every((item) => item.size.every((value) => value > 0) && item.anchor),
    adaptivePitchIsFixed: spec.adaptiveFields.every((item) => item.pitch.every((value) => value > 0) && item.lineWidth.every((value, axis) => value < item.pitch[axis])),
    paletteComplete: ['primary', 'secondary', 'dark', 'light', 'accent'].every((name) => /^#[0-9a-f]{6}$/i.test(spec.palette[name])),
    triangleBudget: spec.parts.length * 12 + spec.fixedParts.length * 2 <= 5000,
  };
  return { status: Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL', checks, counts: {
    structuralParts: spec.parts.length, fixedParts: spec.fixedParts.length, adaptiveFields: spec.adaptiveFields.length,
    estimatedTriangles: spec.parts.length * 12 + spec.fixedParts.length * 2,
  } };
};

const runJob = async (job, revisionPrompt = '') => {
  try {
    await updateJob(job, { status: 'running', phase: job.evidence ? 'planning' : 'analyzing', progress: job.evidence ? 36 : 12, message: job.evidence ? 'Planning revision' : 'Reading reference evidence', error: null });
    if (!job.evidence) {
      job.evidence = await analyze(job);
      await writeFile(path.join(job.directory, 'evidence.json'), `${JSON.stringify(job.evidence, null, 2)}\n`);
      await updateJob(job, { phase: 'planning', progress: 38, message: 'Building the adaptive prop specification' });
    }
    const modelSpec = await generateSpec(job, revisionPrompt);
    await updateJob(job, { phase: 'validating', progress: 76, message: 'Validating anchors, bounds, and texture behavior' });
    const audit = auditSpec(modelSpec);
    job.modelSpec = modelSpec; job.audit = audit;
    const revisionDirectory = path.join(job.directory, `revision-${String(job.iteration).padStart(3, '0')}`);
    await mkdir(revisionDirectory, { recursive: true });
    await writeFile(path.join(revisionDirectory, 'model-spec.json'), `${JSON.stringify(modelSpec, null, 2)}\n`);
    await writeFile(path.join(revisionDirectory, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
    await writeFile(path.join(job.directory, 'model-spec.json'), `${JSON.stringify(modelSpec, null, 2)}\n`);
    await updateJob(job, { status: audit.status === 'PASS' ? 'complete' : 'needs-revision', phase: 'complete', progress: 100,
      message: audit.status === 'PASS' ? 'Prop ready for visual review' : 'Specification needs another revision' });
  } catch (error) {
    await updateJob(job, { status: 'error', phase: 'error', message: 'Generation stopped', error: error.message, progress: 100 });
  }
};

const storeReferences = async (job, references) => {
  const directory = path.join(job.directory, 'references'); await mkdir(directory, { recursive: true });
  const saved = [];
  for (let index = 0; index < Math.min(references.length, 5); index += 1) {
    const item = references[index]; const extension = allowedImageTypes.get(item.type);
    if (!extension) continue;
    const match = String(item.data).match(/^data:[^;]+;base64,(.+)$/); if (!match) continue;
    const buffer = Buffer.from(match[1], 'base64'); if (buffer.length > 8 * 1024 * 1024) continue;
    const filename = `reference-${index + 1}${extension}`; const target = path.join(directory, filename);
    await writeFile(target, buffer); saved.push({ name: String(item.name ?? filename).slice(0, 100), type: item.type, path: target, url: `/api/jobs/${job.id}/references/${filename}` });
  }
  return saved;
};

const loadJobs = async () => {
  await mkdir(jobsRoot, { recursive: true });
  for (const name of await readdir(jobsRoot)) try {
    const state = JSON.parse(await readFile(path.join(jobsRoot, name, 'state.json'), 'utf8'));
    const modelSpec = await readFile(path.join(jobsRoot, name, 'model-spec.json'), 'utf8').then(JSON.parse).catch(() => null);
    jobs.set(name, { ...state, directory: path.join(jobsRoot, name), references: [], modelSpec, usage: {} });
  } catch {}
};

const mime = new Map([['.html', 'text/html; charset=utf-8'], ['.js', 'text/javascript; charset=utf-8'], ['.mjs', 'text/javascript; charset=utf-8'], ['.css', 'text/css; charset=utf-8'], ['.json', 'application/json; charset=utf-8'], ['.png', 'image/png'], ['.jpg', 'image/jpeg'], ['.webp', 'image/webp'], ['.gif', 'image/gif']]);
const sendFile = async (response, target) => {
  const content = await readFile(target); response.writeHead(200, { 'content-type': mime.get(path.extname(target)) ?? 'application/octet-stream' }); response.end(content);
};

await loadJobs();
const server = createServer(async (request, response) => {
  const url = new URL(request.url, `http://${request.headers.host}`);
  try {
    if (request.method === 'GET' && url.pathname === '/api/health') {
      try {
        const models = await listModels();
        return json(response, 200, { ok: true, ollama: true, url: ollamaUrl, models });
      } catch { return json(response, 200, { ok: true, ollama: false, url: ollamaUrl, models: [] }); }
    }
    if (request.method === 'GET' && url.pathname === '/api/jobs') return json(response, 200, [...jobs.values()].map(publicJob).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)));
    if (request.method === 'POST' && url.pathname === '/api/jobs') {
      const body = await parseBody(request); const base = safeId(body.id || body.prompt?.slice(0, 36)) || `prop-${Date.now()}`;
      let id = base; let suffix = 2; while (jobs.has(id)) id = `${base}-${suffix++}`;
      const job = { id, title: String(body.title || body.prompt || id).slice(0, 80), prompt: String(body.prompt || '').trim(),
        status: 'queued', phase: 'queued', message: 'Waiting to start', progress: 0, iteration: 1,
        createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), directory: path.join(jobsRoot, id),
        models: { vision: body.visionModel, code: body.codeModel }, references: [], evidence: null, modelSpec: null, audit: null, error: null, usage: {} };
      if (!job.prompt || !job.models.code) return json(response, 400, { error: 'Prompt and code model are required' });
      await mkdir(job.directory, { recursive: true }); job.references = await storeReferences(job, body.references ?? []);
      if (job.references.length && !job.models.vision) return json(response, 400, { error: 'A vision model is required when references are attached' });
      jobs.set(id, job); await saveJob(job); runJob(job); return json(response, 202, publicJob(job));
    }
    const match = url.pathname.match(/^\/api\/jobs\/([a-z0-9-]+)$/);
    if (request.method === 'GET' && match) { const job = jobs.get(match[1]); return job ? json(response, 200, publicJob(job)) : json(response, 404, { error: 'Job not found' }); }
    const revise = url.pathname.match(/^\/api\/jobs\/([a-z0-9-]+)\/revise$/);
    if (request.method === 'POST' && revise) {
      const job = jobs.get(revise[1]); if (!job) return json(response, 404, { error: 'Job not found' });
      if (job.status === 'running') return json(response, 409, { error: 'Job is already running' });
      const body = await parseBody(request, 1024 * 1024); const prompt = String(body.prompt ?? '').trim(); if (!prompt) return json(response, 400, { error: 'Revision prompt is required' });
      job.iteration += 1; runJob(job, prompt); return json(response, 202, publicJob(job));
    }
    const specMatch = url.pathname.match(/^\/api\/jobs\/([a-z0-9-]+)\/model-spec$/);
    if (request.method === 'GET' && specMatch) { const job = jobs.get(specMatch[1]); return job?.modelSpec ? json(response, 200, job.modelSpec) : json(response, 404, { error: 'Model not ready' }); }
    const refMatch = url.pathname.match(/^\/api\/jobs\/([a-z0-9-]+)\/references\/(reference-[1-5]\.(?:png|jpg|webp|gif))$/);
    if (request.method === 'GET' && refMatch) return sendFile(response, path.join(jobsRoot, refMatch[1], 'references', refMatch[2]));
    const threeModule = url.pathname.match(/^\/vendor\/(three(?:\.module|\.core)?\.js)$/);
    if (request.method === 'GET' && threeModule) return await sendFile(response, path.join(root, 'node_modules/three/build', threeModule[1]));
    if (request.method === 'GET') {
      const relative = url.pathname === '/' ? 'index.html' : url.pathname.slice(1);
      const target = path.resolve(dirname, relative); if (!target.startsWith(dirname)) return json(response, 403, { error: 'Forbidden' });
      return await sendFile(response, target);
    }
    return json(response, 404, { error: 'Not found' });
  } catch (error) { return json(response, error.code === 'ENOENT' ? 404 : 500, { error: error.message }); }
});
server.listen(port, h