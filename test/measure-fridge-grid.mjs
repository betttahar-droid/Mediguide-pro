import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';

const manifestUrl = new URL('../docs/reference-lock/vaccine-fridge-v1/source-manifest.json', import.meta.url);
const authorityUrl = new URL('../docs/reference-lock/vaccine-fridge-v1/geometry-authority.json', import.meta.url);
const reportUrl = new URL('../docs/reference-lock/vaccine-fridge-v2/source-grid-measurements.json', import.meta.url);
const manifest = JSON.parse(readFileSync(manifestUrl));
const authority = JSON.parse(readFileSync(authorityUrl));
const totalHeight = authority.modelGridPx.totalHeight;

function calibrate(view, expectedHorizontalModelPx, semanticAxis) {
  const [x0, y0, x1, y1] = manifest.views[view].candidateObjectBoundsPx;
  const rasterWidthPx = x1 - x0;
  const rasterHeightPx = y1 - y0;
  const rasterPixelsPerModelPixel = rasterHeightPx / totalHeight;
  const measuredHorizontalModelPx = rasterWidthPx / rasterPixelsPerModelPixel;
  const absoluteErrorModelPx = measuredHorizontalModelPx - expectedHorizontalModelPx;
  return {
    view,
    semanticAxis,
    rasterObjectBoundsPx: [x0, y0, x1, y1],
    rasterSizePx: [rasterWidthPx, rasterHeightPx],
    heightAnchorModelPx: totalHeight,
    rasterPixelsPerModelPixel,
    expectedHorizontalModelPx,
    measuredHorizontalModelPx,
    absoluteErrorModelPx,
    relativeErrorPercent: 100 * absoluteErrorModelPx / expectedHorizontalModelPx,
    oneRasterPixelUncertaintyModelPx: 1 / rasterPixelsPerModelPixel,
  };
}

const report = {
  method: 'orthographic silhouette bounds calibrated from a known model-grid height',
  equation: 'model coordinate = (raster coordinate - calibrated origin) / rasterPixelsPerModelPixel',
  warning: 'AI-drawn grid lines are presentation pixels, not authority. Rectify the view and overlay a deterministic grid before measuring internal features.',
  front: calibrate('front', authority.modelGridPx.frontOverallWidth, 'width'),
  side: calibrate('side', authority.modelGridPx.sideOverallDepth, 'depth'),
  backDiagnostic: calibrate('back', authority.modelGridPx.mainCarcassWidth, 'width'),
};

assert.ok(Math.abs(report.front.relativeErrorPercent) < 0.5, 'front calibration stays below 0.5% error');
assert.ok(Math.abs(report.side.relativeErrorPercent) < 0.5, 'side calibration stays below 0.5% error');
writeFileSync(reportUrl, `${JSON.stringify(report, null, 2)}\n`);

console.log(
  `PASS grid calibration: front ${report.front.measuredHorizontalModelPx.toFixed(3)} px ` +
  `(${report.front.relativeErrorPercent.toFixed(3)}%), side ${report.side.measuredHorizontalModelPx.toFixed(3)} px ` +
  `(${report.side.relativeErrorPercent.toFixed(3)}%)`,
);

