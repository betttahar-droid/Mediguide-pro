import * as THREE from '/vendor/three.module.js';

const params = new URLSearchParams(location.search);
const jobId = params.get('job');
const message = document.querySelector('#message');
const spec = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/model-spec`).then(async response => {
  if (!response.ok) throw new Error((await response.json()).error); return response.json();
});

const scene = new THREE.Scene();
scene.background = new THREE.Color('#0b0d11');
const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, .01, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: false });
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.prepend(renderer.domElement);
const group = new THREE.Group(); scene.add(group);
let scale = [1, 1, 1]; let yaw = -34; let elevation = 14;
const tint = (hex, amount) => new THREE.Color(hex).multiplyScalar(amount);
const materialCache = new Map();
const boxMaterials = (hex) => {
  const key = `${hex}:${spec.style.topTint}:${spec.style.frontTint}:${spec.style.sideTint}`;
  if (!materialCache.has(key)) materialCache.set(key, [
    new THREE.MeshBasicMaterial({ color: tint(hex, spec.style.sideTint * .92) }),
    new THREE.MeshBasicMaterial({ color: tint(hex, spec.style.sideTint) }),
    new THREE.MeshBasicMaterial({ color: tint(hex, spec.style.topTint) }),
    new THREE.MeshBasicMaterial({ color: tint(hex, .64) }),
    new THREE.MeshBasicMaterial({ color: tint(hex, spec.style.frontTint) }),
    new THREE.MeshBasicMaterial({ color: tint(hex, spec.style.frontTint * .87) }),
  ]);
  return materialCache.get(key);
};
const addBox = (id, center, size, material, role = '') => {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(...size), boxMaterials(spec.palette[material]));
  mesh.position.set(...center); mesh.name = id; mesh.userData.role = role; group.add(mesh);
  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry), new THREE.LineBasicMaterial({ color: spec.style.outline }));
  edges.renderOrder = 3; mesh.add(edges); return mesh;
};
const anchors = {
  'top-left': [-1, 1], 'top-center': [0, 1], 'top-right': [1, 1],
  'center-left': [-1, 0], center: [0, 0], 'center-right': [1, 0],
  'bottom-left': [-1, -1], 'bottom-center': [0, -1], 'bottom-right': [1, -1],
};
const resolveAnchor = (item, dimensions) => {
  const [horizontal, vertical] = anchors[item.anchor];
  const faceSpan = ['left', 'right'].includes(item.face) ? dimensions.depth : dimensions.width;
  const u = horizontal < 0 ? -faceSpan / 2 + item.size[0] / 2 + item.offset[0]
    : horizontal > 0 ? faceSpan / 2 - item.size[0] / 2 - item.offset[0] : item.offset[0];
  const v = vertical < 0 ? item.size[1] / 2 + item.offset[1]
    : vertical > 0 ? dimensions.height - item.size[1] / 2 - item.offset[1] : dimensions.height / 2 + item.offset[1];
  return [u, v];
};
const placeOnFace = (mesh, face, u, v, plane) => {
  if (face === 'front') { mesh.rotation.y = Math.PI; mesh.position.set(-u, v, -plane); }
  if (face === 'back') mesh.position.set(u, v, plane);
  if (face === 'left') { mesh.rotation.y = -Math.PI / 2; mesh.position.set(-plane, v, u); }
  if (face === 'right') { mesh.rotation.y = Math.PI / 2; mesh.position.set(plane, v, -u); }
};
const decalTexture = (item) => {
  const canvas = document.createElement('canvas'); canvas.width = 64; canvas.height = 64;
  const context = canvas.getContext('2d'); context.imageSmoothingEnabled = false; context.clearRect(0, 0, 64, 64);
  const base = spec.palette[item.material], accent = spec.palette[item.accent], dark = spec.palette.dark;
  context.fillStyle = base; context.fillRect(3, 3, 58, 58); context.strokeStyle = dark; context.lineWidth = 4; context.strokeRect(3, 3, 58, 58);
  context.fillStyle = accent; context.strokeStyle = accent;
  if (item.type === 'vent') for (let y = 11; y < 57; y += 7) context.fillRect(10, y, 44, 3);
  if (item.type === 'screen') { context.fillRect(10, 13, 44, 27); context.fillStyle = '#d5ef9a'; context.fillRect(16, 20, 5, 12); context.fillRect(25, 17, 4, 15); context.fillRect(34, 22, 13, 4); }
  if (item.type === 'fan') { context.lineWidth = 4; context.beginPath(); context.arc(32, 32, 21, 0, Math.PI * 2); context.stroke(); for (let i = 0; i < 5; i += 1) { context.save(); context.translate(32, 32); context.rotate(i * Math.PI * .4); context.fillRect(2, -4, 20, 8); context.restore(); } }
  if (item.type === 'warning') { context.beginPath(); context.moveTo(32, 10); context.lineTo(54, 51); context.lineTo(10, 51); context.closePath(); context.fill(); context.fillStyle = dark; context.fillRect(29, 24, 6, 15); context.fillRect(29, 43, 6, 5); }
  if (item.type === 'hinge') { context.fillRect(22, 7, 20, 50); context.fillStyle = dark; context.fillRect(28, 13, 8, 38); }
  if (['label', 'control'].includes(item.type)) { context.fillRect(9, 12, 46, 8); context.fillRect(9, 27, 34, 5); context.fillRect(9, 39, 41, 5); }
  if (item.text) { context.fillStyle = dark; context.font = 'bold 8px monospace'; context.textAlign = 'center'; context.fillText(item.text.slice(0, 10).toUpperCase(), 32, 56); }
  const texture = new THREE.CanvasTexture(canvas); texture.colorSpace = THREE.SRGBColorSpace; texture.magFilter = texture.minFilter = THREE.NearestFilter; texture.generateMipmaps = false; return texture;
};
const addFixed = (item, dimensions) => {
  const [u, v] = resolveAnchor(item, dimensions);
  const plane = ['front', 'back'].includes(item.face) ? dimensions.depth / 2 + item.depth : dimensions.width / 2 + item.depth;
  if (item.type === 'handle') {
    const thickness = Math.max(.7, Math.min(item.size) * .12), gap = item.depth + thickness * 2;
    if (['front', 'back'].includes(item.face)) {
      const sign = item.face === 'front' ? -1 : 1;
      addBox(item.id, [item.face === 'front' ? -u : u, v, sign * (dimensions.depth / 2 + gap)], [item.size[0], item.size[1], thickness], item.material, 'fixed');
      for (const dy of [-item.size[1] / 2 + thickness, item.size[1] / 2 - thickness]) addBox(`${item.id}-mount`, [item.face === 'front' ? -u : u, v + dy, sign * (dimensions.depth / 2 + gap / 2)], [item.size[0], thickness * 1.5, gap], item.accent, 'fixed');
    } else {
      const sign = item.face === 'left' ? -1 : 1;
      const z = item.face === 'left' ? u : -u;
      addBox(item.id, [sign * (dimensions.width / 2 + gap), v, z], [thickness, item.size[1], item.size[0]], item.material, 'fixed');
    }
    return;
  }
  const geometry = new THREE.PlaneGeometry(item.size[0], item.size[1]);
  const mesh = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ map: decalTexture(item), transparent: true, side: THREE.DoubleSide, depthWrite: false }));
  mesh.name = item.id; mesh.renderOrder = 6; mesh.userData.fixedSize = item.size; placeOnFace(mesh, item.face, u, v, plane); group.add(mesh);
};
const addAdaptive = (item, dimensions) => {
  const side = ['left', 'right'].includes(item.face); const span = side ? dimensions.depth : dimensions.width;
  const [left, bottom, right, top] = item.margins; const fieldWidth = span - left - right, fieldHeight = dimensions.height - bottom - top;
  if (fieldWidth <= 1 || fieldHeight <= 1) return;
  const material = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, side: THREE.DoubleSide,
    uniforms: { uSize: { value: new THREE.Vector2(fieldWidth, fieldHeight) }, uPitch: { value: new THREE.Vector2(...item.pitch) }, uLine: { value: new THREE.Vector2(...item.lineWidth) }, uColor: { value: new THREE.Color(spec.palette[item.accent]) }, uPattern: { value: ['grid', 'vertical-vents', 'horizontal-vents', 'panels'].indexOf(item.pattern) } },
    vertexShader: 'varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
    fragmentShader: 'varying vec2 vUv;uniform vec2 uSize,uPitch,uLine;uniform vec3 uColor;uniform int uPattern;void main(){vec2 p=vUv*uSize;float x=1.-step(uLine.x,mod(p.x,uPitch.x));float y=1.-step(uLine.y,mod(p.y,uPitch.y));float a=max(x,y);if(uPattern==1)a=x;if(uPattern==2)a=y;if(a<.5)discard;gl_FragColor=vec4(uColor,1.);}',
  });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(fieldWidth, fieldHeight), material); mesh.name = item.id; mesh.renderOrder = 5;
  const u = (left - right) / 2, v = bottom + fieldHeight / 2; const plane = side ? dimensions.width / 2 + .08 : dimensions.depth / 2 + .08;
  placeOnFace(mesh, item.face, u, v, plane); mesh.userData.adaptive = { size: [fieldWidth, fieldHeight], pitch: item.pitch, repeatCounts: [Math.floor(fieldWidth / item.pitch[0]), Math.floor(fieldHeight / item.pitch[1])] }; group.add(mesh);
};
const clear = () => { while (group.children.length) { const node = group.children.pop(); node.traverse(child => { child.geometry?.dispose(); if (Array.isArray(child.material)) child.material.forEach(material => material.dispose()); else child.material?.dispose(); }); } };
const build = () => {
  clear(); const dimensions = { width: spec.dimensions.width * scale[0], depth: spec.dimensions.depth * scale[1], height: spec.dimensions.height * scale[2] };
  for (const part of spec.parts) {
    const [x1, y1, z1, x2, y2, z2] = part.bounds;
    const size = [(x2 - x1) * dimensions.width, (y2 - y1) * dimensions.height, (z2 - z1) * dimensions.depth];
    const center = [((x1 + x2) / 2 - .5) * dimensions.width, ((y1 + y2) / 2) * dimensions.height, ((z1 + z2) / 2 - .5) * dimensions.depth];
    addBox(part.id, center, size, part.material, part.role);
  }
  spec.adaptiveFields.forEach(item => addAdaptive(item, dimensions)); spec.fixedParts.forEach(item => addFixed(item, dimensions));
  group.position.y = -dimensions.height / 2; fitCamera(dimensions); sendStats(dimensions); render();
};
const fitCamera = (dimensions) => {
  const aspect = innerWidth / innerHeight, extent = Math.max(dimensions.height * 1.16, dimensions.width * 1.65, dimensions.depth * 1.65);
  camera.left = -extent * aspect / 2; camera.right = extent * aspect / 2; camera.top = extent / 2; camera.bottom = -extent / 2; camera.near = .01; camera.far = extent * 8;
  const radius = extent * 2.4, yawRad = THREE.MathUtils.degToRad(yaw), elevationRad = THREE.MathUtils.degToRad(elevation);
  camera.position.set(Math.sin(yawRad) * radius, Math.sin(elevationRad) * radius, -Math.cos(yawRad) * radius); camera.lookAt(0, 0, 0); camera.updateProjectionMatrix();
};
const sendStats = (dimensions) => parent.postMessage({ type: 'prop-preview-stats', jobId, stats: { dimensions, parts: spec.parts.length, fixed: spec.fixedParts.length, adaptive: spec.adaptiveFields.map(item => { const node = group.getObjectByName(item.id); return { id: item.id, ...node?.userData.adaptive }; }) } }, location.origin);
const resize = () => { renderer.setSize(innerWidth, innerHeight, false); build(); };
const render = () => renderer.render(scene, camera);
addEventListener('resize', resize);
addEventListener('message', event => { if (event.origin !== location.origin) return; if (event.data?.type === 'prop-scale') { scale = event.data.scale; build(); } });
let dragging = false, lastX = 0, lastY = 0;
renderer.domElement.addEventListener('pointerdown', event => { dragging = true; lastX = event.clientX; lastY = event.clientY; renderer.domElement.setPointerCapture(event.pointerId); });
renderer.domElement.addEventListener('pointermove', event => { if (!dragging) return; yaw += (event.clientX - lastX) * .35; elevation = Math.max(-15, Math.min(35, elevation + (event.clientY - lastY) * .25)); lastX = event.clientX; lastY = event.clientY; const d = { width: spec.dimensions.width * scale[0], depth: spec.dimensions.depth * scale[1], height: spec.dimensions.height * scale[2] }; fitCamera(d); render(); });
renderer.domElement.addEventListener('pointerup', () => { dragging = false; });
message.textContent = `${spec.label} · drag to orbit`; resize();
