import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { PNG } from 'pngjs';

const folder = fileURLToPath(new URL('../docs/reference-lock/vaccine-fridge-v1/', import.meta.url));
const metrics = {};

for (const view of ['front', 'side', 'back']) {
  const reference = PNG.sync.read(readFileSync(path.join(folder, `${view}-mask-candidate.png`)));
  const candidate = PNG.sync.read(readFileSync(path.join(folder, `candidate-${view}.png`)));
  if (reference.width !== candidate.width || reference.height !== candidate.height) {
    throw new Error(`${view} gate dimensions differ: reference ${reference.width}x${reference.height}, candidate ${candidate.width}x${candidate.height}`);
  }

  const overlay = new PNG({ width: reference.width, height: reference.height });
  let intersection = 0;
  let union = 0;
  let referencePixels = 0;
  let candidatePixels = 0;
  for (let pixel = 0; pixel < reference.width * reference.height; pixel++) {
    const offset = pixel * 4;
    const referenceVisible = reference.data[offset] >= 128;
    const candidateVisible = candidate.data[offset + 3] >= 128;
    if (referenceVisible) referencePixels++;
    if (candidateVisible) candidatePixels++;
    if (referenceVisible && candidateVisible) intersection++;
    if (referenceVisible || candidateVisible) union++;

    let rgba = [0, 0, 0, 0];
    if (referenceVisible && candidateVisible) rgba = [255, 255, 255, 180];
    else if (referenceVisible) rgba = [255, 40, 40, 220];
    else if (candidateVisible) rgba = [40, 255, 80, 220];
    overlay.data.set(rgba, offset);
  }
  writeFileSync(path.join(folder, `${view}-silhouette-overlay.png`), PNG.sync.write(overlay));
  metrics[view] = {
    referencePixels,
    candidatePixels,
    intersectionOverUnion: union ? intersection / union : 0,
    differentPixels: union - intersection,
  };
}

writeFileSync(path.join(folder, 'orthographic-gate-metrics.json'), `${JSON.stringify(metrics, null, 2)}\n`);
console.log(JSON.stringify(metrics, null, 2));

