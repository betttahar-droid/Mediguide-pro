import GUI from 'lil-gui';
import { REGISTRY, MODULE_IDS } from '../modules/registry.js';
import { setSharedUniform, setSharedVector, setToonRampSteps } from '../shaders/index.js';
import { PALETTE_HEX } from '../art/palette.js';

export function buildGui(app) {
  const gui = new GUI({ title: 'Pharmacy Builder' });

  // ---- build -----------------------------------------------------------
  const build = gui.addFolder('Build');
  const labels = Object.fromEntries(MODULE_IDS.map((id) => [REGISTRY[id].label, id]));
  build.add(app.state, 'moduleId', labels).name('module').onChange(() => app.selectType(app.state.moduleId));
  build.add(app.state, 'mode', ['place', 'select']).name('mode').listen().onChange(() => app.setMode(app.state.mode));
  build.add({ rotate: () => app.rotate() }, 'rotate').name('rotate 45° (R)');
  build.add({ del: () => app.deleteSelected() }, 'del').name('delete selected (X)');

  const axesFolder = build.addFolder('Size');
  let axisControllers = [];

  function refreshAxes() {
    axisControllers.forEach((c) => c.destroy());
    axisControllers = [];
    const target = app.activeModule();
    if (!target) return;
    for (const [axis, spec] of Object.entries(target.def.axes)) {
      if (spec.mode === 'fixed') continue;
      const proxy = { [axis]: target.params[axis] };
      const c = axesFolder
        .add(proxy, axis, spec.min, spec.max, spec.mode === 'repeat' ? 1 : 0.01)
        .name(`${spec.label ?? axis} (${spec.mode})`)
        .onChange((v) => app.setParam(axis, v));
      axisControllers.push(c);
    }
  }
  app.onActiveChanged = refreshAxes;
  refreshAxes();

  // ---- scene -----------------------------------------------------------
  const scene = gui.addFolder('Scene');
  scene.add(app.stats, 'modules').name('modules').listen().disable();
  scene.add(app.stats, 'cost').name('cost (£)').listen().disable();
  scene.add({ save: () => app.save() }, 'save').name('save');
  scene.add({ load: () => app.load() }, 'load').name('load');
  scene.add({ clear: () => app.clear() }, 'clear').name('clear');

  // ---- look development (§4.3, §4.4) -----------------------------------
  const look = gui.addFolder('Look dev').close();

  const light = look.addFolder('Lighting');
  const lightState = { rampSteps: 4, key: 0.68, fill: 0.28, rim: 0.35, rimPower: 3.0, keyAzimuth: 37, keyElevation: 53 };
  light.add(lightState, 'rampSteps', 2, 8, 1).onChange((v) => setToonRampSteps(v));
  light.add(lightState, 'key', 0, 2).onChange((v) => setSharedUniform('uKeyIntensity', v));
  light.add(lightState, 'fill', 0, 1).onChange((v) => setSharedUniform('uFillIntensity', v));
  light.add(lightState, 'rim', 0, 1.5).onChange((v) => setSharedUniform('uRimStrength', v));
  light.add(lightState, 'rimPower', 1, 8).onChange((v) => setSharedUniform('uRimPower', v));
  const applyKeyDir = () => {
    const a = (lightState.keyAzimuth * Math.PI) / 180;
    const e = (lightState.keyElevation * Math.PI) / 180;
    setSharedVector('uKeyDir', Math.cos(e) * Math.sin(a), Math.sin(e), Math.cos(e) * Math.cos(a));
  };
  light.add(lightState, 'keyAzimuth', -180, 180, 1).onChange(applyKeyDir);
  light.add(lightState, 'keyElevation', 0, 89, 1).onChange(applyKeyDir);

  // The six ramp parameters of §4.3. These are tuned by eye, not by formula.
  const masks = look.addFolder('Vertex masks');
  const maskState = {
    cavityLo: 0.12, cavityHi: 0.62, cavityStrength: 0.75,
    edgeLo: 0.55, edgeHi: 0.95, edgeStrength: 0.45, dust: 0.05,
  };
  masks.add(maskState, 'cavityLo', 0, 1).onChange((v) => setSharedUniform('uCavityLo', v));
  masks.add(maskState, 'cavityHi', 0, 1).onChange((v) => setSharedUniform('uCavityHi', v));
  masks.add(maskState, 'cavityStrength', 0, 1).onChange((v) => setSharedUniform('uCavityStrength', v));
  masks.add(maskState, 'edgeLo', 0, 1).onChange((v) => setSharedUniform('uEdgeLo', v));
  masks.add(maskState, 'edgeHi', 0, 1).onChange((v) => setSharedUniform('uEdgeHi', v));
  masks.add(maskState, 'edgeStrength', 0, 1).onChange((v) => setSharedUniform('uEdgeStrength', v));
  masks.add(maskState, 'dust', 0, 0.3).onChange((v) => setSharedUniform('uDustStrength', v));

  const trim = look.addFolder('Trim (Tier B stand-in)');
  const trimState = { frequency: 2.0, strength: 0.9 };
  trim.add(trimState, 'frequency', 0.25, 8).onChange((v) => setSharedUniform('uTrimFrequency', v));
  trim.add(trimState, 'strength', 0, 1).onChange((v) => setSharedUniform('uTrimStrength', v));

  look.add({ palette: () => console.table(PALETTE_HEX) }, 'palette').name('log palette hexes');

  return gui;
}
