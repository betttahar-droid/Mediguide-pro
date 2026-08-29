// The catalogue panel — how you pick something to place.
//
// A DOM overlay rather than a lil-gui dropdown, because the catalogue is the
// main thing you interact with: it needs shelves you can scan, a name, a line
// saying what the thing is for, and a price. lil-gui keeps the look-dev knobs.
import { REGISTRY, CATEGORIES, byCategory } from '../modules/registry.js';
import { PALETTE_HEX as C } from '../art/palette.js';

const css = `
#catalogue {
  position: fixed; left: 12px; top: 12px; width: 260px;
  max-height: calc(100vh - 24px); display: flex; flex-direction: column;
  font: 12px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace;
  color: ${C.ink}; background: ${C.paper};
  border: 3px solid ${C.ink}; box-shadow: 4px 4px 0 rgba(43,31,51,0.35);
  user-select: none; z-index: 10;
}
#catalogue header {
  padding: 7px 10px; background: ${C.ink}; color: ${C.paper};
  font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
  display: flex; justify-content: space-between; align-items: baseline;
}
#catalogue header span { font-weight: 400; letter-spacing: 0; opacity: 0.7; }
#cat-tabs { display: flex; flex-wrap: wrap; gap: 2px; padding: 6px; background: ${C.bone}; }
#cat-tabs button {
  flex: 1 1 auto; padding: 4px 6px; font: inherit; cursor: pointer;
  color: ${C.ink}; background: ${C.putty};
  border: 2px solid ${C.ink}; border-radius: 0;
}
#cat-tabs button[aria-selected="true"] { background: ${C.mint}; font-weight: 700; }
#cat-blurb { padding: 4px 10px 6px; background: ${C.bone}; font-size: 11px; opacity: 0.75; }
#cat-list { overflow-y: auto; padding: 6px; display: flex; flex-direction: column; gap: 4px; }
#cat-list button {
  text-align: left; padding: 6px 8px; font: inherit; cursor: pointer;
  color: ${C.ink}; background: ${C.bone};
  border: 2px solid ${C.putty}; border-radius: 0;
}
#cat-list button:hover { border-color: ${C.ink}; background: ${C.paper}; }
#cat-list button[aria-current="true"] { background: ${C.mint}; border-color: ${C.ink}; }
#cat-list .name { display: flex; justify-content: space-between; font-weight: 700; }
#cat-list .cost { font-weight: 400; opacity: 0.65; }
#cat-list .blurb { font-size: 11px; opacity: 0.72; margin-top: 2px; }
#cat-list .axes { font-size: 10px; margin-top: 3px; letter-spacing: 0.04em; opacity: 0.6; }
#cat-foot {
  padding: 6px 10px; background: ${C.bone}; border-top: 2px solid ${C.putty};
  font-size: 11px; display: flex; justify-content: space-between;
}
#cat-foot b { font-weight: 700; }
`;

/** "3 bays · 6 shelves · depth" — how this module resizes, at a glance. */
function axisSummary(def) {
  const parts = [];
  for (const [axis, spec] of Object.entries(def.axes)) {
    if (spec.mode === 'fixed') continue;
    parts.push(`${spec.label ?? axis} ${spec.mode === 'repeat' ? '▦' : '↔'}`);
  }
  return parts.length ? parts.join(' · ') : 'fixed size';
}

export function buildCatalogue(app) {
  const style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  const root = document.createElement('div');
  root.id = 'catalogue';
  root.innerHTML = `
    <header>Catalogue <span id="cat-mode">place</span></header>
    <div id="cat-tabs" role="tablist"></div>
    <div id="cat-blurb"></div>
    <div id="cat-list"></div>
    <div id="cat-foot"><span id="cat-count">0 placed</span><b id="cat-total">£0</b></div>
  `;
  document.body.appendChild(root);

  const tabs = root.querySelector('#cat-tabs');
  const list = root.querySelector('#cat-list');
  const blurb = root.querySelector('#cat-blurb');
  const shelves = byCategory(CATEGORIES);
  let active = shelves[0].id;

  function renderList() {
    const shelf = shelves.find((s) => s.id === active);
    blurb.textContent = shelf.blurb;
    list.innerHTML = '';
    for (const def of shelf.modules) {
      const b = document.createElement('button');
      b.type = 'button';
      b.setAttribute('aria-current', String(def.id === app.state.moduleId));
      b.innerHTML = `
        <span class="name">${def.label}<span class="cost">£${def.cost}</span></span>
        <span class="blurb">${def.blurb ?? ''}</span>
        <span class="axes">${axisSummary(def)}</span>
      `;
      b.addEventListener('click', () => {
        app.setMode('place');
        app.selectType(def.id);
        refresh();
      });
      list.appendChild(b);
    }
  }

  function renderTabs() {
    tabs.innerHTML = '';
    for (const shelf of shelves) {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = shelf.label;
      b.setAttribute('role', 'tab');
      b.setAttribute('aria-selected', String(shelf.id === active));
      b.addEventListener('click', () => {
        active = shelf.id;
        renderTabs();
        renderList();
      });
      tabs.appendChild(b);
    }
  }

  /** Called whenever the selection, the mode or the scene total changes. */
  function refresh() {
    const def = REGISTRY[app.state.moduleId];
    if (def && def.category !== active) {
      active = def.category; // follow the selection to its shelf
      renderTabs();
    }
    renderList();
    root.querySelector('#cat-mode').textContent = app.state.mode;
    root.querySelector('#cat-count').textContent =
      `${app.stats.modules} placed`;
    root.querySelector('#cat-total').textContent =
      `£${app.stats.cost.toLocaleString('en-GB')}`;
  }

  renderTabs();
  refresh();
  return { refresh };
}
