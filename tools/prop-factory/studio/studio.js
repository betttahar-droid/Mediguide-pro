const elements = Object.fromEntries([...document.querySelectorAll('[id]')].map(element => [element.id, element]));
let jobs = []; let activeJob = null; let references = []; let polling = null; let toastTimer = null;
const phases = ['analyzing', 'planning', 'validating', 'complete'];
const presets = {
  'Medical cabinet': 'Make a compact vaccine refrigerator with a glass door, fixed side vent, rear condenser, readable controls and chunky PS1-era proportions.',
  'Retro terminal': 'Make a squat industrial computer terminal with a recessed screen, keyboard shelf, side vents, warning label and chunky retro-futurist construction.',
  'Industrial crate': 'Make a reusable medical supply crate with reinforced corners, fixed latches, warning marks and adaptive rib spacing.',
};
const request = async (url, options = {}) => {
  const response = await fetch(url, { headers: { 'content-type': 'application/json', ...(options.headers ?? {}) }, ...options });
  const payload = await response.json(); if (!response.ok) throw new Error(payload.error ?? `Request failed: ${response.status}`); return payload;
};
const toast = (text) => { clearTimeout(toastTimer); elements.toast.textContent = text; elements.toast.dataset.visible = 'true'; toastTimer = setTimeout(() => { elements.toast.dataset.visible = 'false'; }, 2600); };
const pretty = value => String(value).replace(/([a-z])([A-Z])/g, '$1 $2').replace(/^./, letter => letter.toUpperCase());
const setVisible = (element, visible) => { element.hidden = !visible; };

const loadHealth = async () => {
  const health = await request('/api/health'); elements.localStatus.dataset.online = String(health.ollama);
  elements.localStatus.querySelector('strong').textContent = health.ollama ? 'Ollama connected' : 'Ollama offline';
  const completion = health.models.filter(model => model.capabilities?.includes('completion'));
  const vision = completion.filter(model => model.capabilities?.includes('vision'));
  const fill = (select, models, preferred) => {
    select.replaceChildren(...models.map(model => Object.assign(document.createElement('option'), { value: model.name, textContent: `${model.name} · ${model.details?.parameter_size ?? ''}` })));
    const match = models.find(model => model.name === preferred); if (match) select.value = match.name;
  };
  fill(elements.codeModel, completion, 'qwen2.5:7b-instruct-q4_K_M'); fill(elements.visionModel, vision, 'gemma4:e4b');
  if (!health.ollama) elements.generate.disabled = true;
};
const loadJobs = async () => { jobs = await request('/api/jobs'); renderJobs(); if (activeJob) { const latest = jobs.find(job => job.id === activeJob.id); if (latest) showJob(latest); } };
const renderJobs = () => {
  elements.projectList.replaceChildren(...jobs.map(job => {
    const button = document.createElement('button'); button.className = 'project-item'; button.dataset.active = String(activeJob?.id === job.id); button.dataset.status = job.status;
    button.innerHTML = `<i></i><span><strong>${escapeHtml(job.title)}</strong><small>Revision ${job.iteration} · ${escapeHtml(job.status)}</small></span>`;
    button.addEventListener('click', () => showJob(job)); return button;
  }));
};
const escapeHtml = value => String(value).replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[char]);
const updatePhases = (job) => {
  const current = Math.max(0, phases.indexOf(job.phase));
  for (const item of elements.phaseList.children) { const index = phases.indexOf(item.dataset.phase); item.dataset.state = index < current || job.status === 'complete' ? 'done' : index === current ? 'active' : ''; }
  elements.processStatus.textContent = job.status === 'complete' ? 'Complete' : job.status === 'error' ? 'Stopped' : `Phase ${Math.min(current + 1, 4)} / 4`;
};
const renderAudit = audit => {
  setVisible(elements.auditSection, Boolean(audit)); if (!audit) return;
  elements.auditStatus.textContent = audit.status; elements.auditStatus.dataset.status = audit.status;
  elements.auditGrid.replaceChildren(...Object.entries(audit.checks).map(([name, pass]) => {
    const item = document.createElement('div'); item.className = 'audit-item'; item.dataset.pass = String(pass); item.title = pretty(name); item.innerHTML = `<i></i><span>${escapeHtml(pretty(name))}</span>`; return item;
  }));
};
const showJob = job => {
  activeJob = job; renderJobs(); elements.workspaceTitle.textContent = job.modelSpec?.label ?? job.title; elements.revisionBadge.textContent = `Revision ${job.iteration}`;
  elements.prompt.value = ''; elements.prompt.placeholder = job.status === 'complete' ? 'Describe what should change without repeating the full request…' : job.prompt;
  elements.generateLabel.textContent = job.modelSpec ? 'Generate revision' : 'Generate prop'; elements.references.disabled = Boolean(job.modelSpec); elements.dropZone.style.display = job.modelSpec ? 'none' : 'flex';
  const running = job.status === 'running' || job.status === 'queued'; setVisible(elements.processSection, true); updatePhases(job);
  setVisible(elements.stageProgress, running); setVisible(elements.emptyStage, !running && !job.modelSpec && job.status !== 'error'); setVisible(elements.stageError, job.status === 'error');
  if (job.status === 'error') elements.errorMessage.textContent = job.error; elements.generate.disabled = running;
  elements.progressTitle.textContent = pretty(job.phase); elements.progressMessage.textContent = job.message; elements.progressBar.style.width = `${job.progress}%`;
  if (job.modelSpec) { elements.preview.src = job.viewerUrl; setVisible(elements.preview, true); setVisible(elements.scaleDock, true); elements.downloadSpec.href = `/api/jobs/${job.id}/model-spec`; setVisible(elements.downloadSpec, true); }
  else { setVisible(elements.preview, false); setVisible(elements.scaleDock, false); setVisible(elements.downloadSpec, false); }
  renderAudit(job.audit);
  clearInterval(polling); if (running) polling = setInterval(async () => { const latest = await request(`/api/jobs/${job.id}`); showJob(latest); }, 900);
};
const newProject = () => {
  clearInterval(polling); activeJob = null; references = []; renderReferences(); renderJobs(); elements.workspaceTitle.textContent = 'New adaptive prop'; elements.revisionBadge.textContent = 'Draft'; elements.prompt.value = ''; elements.prompt.placeholder = 'Make a compact vaccine refrigerator with a glass door, fixed side vent, rear condenser and chunky PS1-era proportions.'; elements.generateLabel.textContent = 'Generate prop'; elements.generate.disabled = false; elements.references.disabled = false; elements.dropZone.style.display = 'flex';
  for (const id of ['preview', 'scaleDock', 'processSection', 'auditSection', 'stageProgress', 'stageError', 'downloadSpec']) setVisible(elements[id], false); setVisible(elements.emptyStage, true);
};
const filesToReferences = async files => {
  for (const file of [...files].slice(0, 5 - references.length)) if (file.type.startsWith('image/') && file.size <= 8 * 1024 * 1024) references.push({ name: file.name, type: file.type, data: await new Promise(resolve => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.readAsDataURL(file); }) });
  renderReferences();
};
const renderReferences = () => { elements.referenceStrip.replaceChildren(...references.map((reference, index) => { const node = document.createElement('div'); node.className = 'reference-thumb'; node.innerHTML = `<img alt="${escapeHtml(reference.name)}"><button aria-label="Remove reference">×</button>`; node.querySelector('img').src = reference.data; node.querySelector('button').onclick = () => { references.splice(index, 1); renderReferences(); }; return node; })); };
const generate = async () => {
  const prompt = elements.prompt.value.trim(); if (!prompt) return toast('Describe the prop or the revision first');
  elements.generate.disabled = true;
  try {
    if (activeJob?.modelSpec) {
      const job = await request(`/api/jobs/${activeJob.id}/revise`, { method: 'POST', body: JSON.stringify({ prompt }) }); showJob(job);
    } else {
      const job = await request('/api/jobs', { method: 'POST', body: JSON.stringify({ prompt, codeModel: elements.codeModel.value, visionModel: elements.visionModel.value, references }) }); jobs.unshift(job); showJob(job);
    }
  } catch (error) { elements.generate.disabled = false; toast(error.message); }
};
elements.newProject.addEventListener('click', newProject); elements.generate.addEventListener('click', generate); elements.prompt.addEventListener('keydown', event => { if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') generate(); });
elements.references.addEventListener('change', event => filesToReferences(event.target.files));
for (const type of ['dragenter', 'dragover']) elements.dropZone.addEventListener(type, event => { event.preventDefault(); elements.dropZone.dataset.drag = 'true'; });
for (const type of ['dragleave', 'drop']) elements.dropZone.addEventListener(type, event => { event.preventDefault(); elements.dropZone.dataset.drag = 'false'; if (type === 'drop') filesToReferences(event.dataTransfer.files); });
elements.promptPresets.addEventListener('click', event => { if (event.target.tagName === 'BUTTON') elements.prompt.value = presets[event.target.textContent]; });
const scaleInputs = [elements.scaleX, elements.scaleY, elements.scaleZ]; const updateScale = () => { const values = scaleInputs.map(input => Number(input.value)); scaleInputs.forEach((input, index) => { input.nextElementSibling.textContent = `${values[index].toFixed(2)}×`; }); elements.preview.contentWindow?.postMessage({ type: 'prop-scale', scale: values }, location.origin); };
scaleInputs.forEach(input => input.addEventListener('input', updateScale)); elements.resetScale.addEventListener('click', () => { scaleInputs.forEach(input => { input.value = 1; }); updateScale(); });
addEventListener('message', event => { if (event.origin === location.origin && event.data?.type === 'prop-preview-stats') elements.revisionBadge.title = `${event.data.stats.parts} structural · ${event.data.stats.fixed} fixed`; });
await loadHealth(); await loadJobs(); newProject();
