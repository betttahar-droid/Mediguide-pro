// Video 1: flat-vector explainer look. Original round characters, not any
// channel's own designs.
const C = {
  bg0: '#120f33', bg1: '#2c2069', ink: '#15122e', white: '#fdfcff',
  yellow: '#ffd23f', pink: '#ff5c8a', teal: '#2fd6c1', orange: '#ff8c42',
  blue: '#4f8cff', purple: '#9b6bff', green: '#5fe07a', red: '#ff4d5e', grey: '#8d86b8',
};
const BLOBS = [C.orange, C.blue, C.pink, C.teal, C.yellow, C.purple];

const STARS = (() => { const r = rng(7); return Array.from({ length: 140 }, () => ({ x: r() * W, y: r() * H, s: r() * 3 + 1, p: r() * 6.28, v: r() * 8 + 2 })); })();
function space(T, top = C.bg0, bot = C.bg1) {
  const gr = g.createLinearGradient(0, 0, 0, H);
  gr.addColorStop(0, top); gr.addColorStop(1, bot);
  g.fillStyle = gr; g.fillRect(0, 0, W, H);
  for (const s of STARS) {
    const y = (s.y + T * s.v) % H;
    g.save(); g.globalAlpha *= .35 + .45 * Math.sin(T * 2 + s.p) ** 2;
    g.fillStyle = '#fff'; g.beginPath(); g.arc(s.x, y, s.s, 0, 7); g.fill(); g.restore();
  }
}
function glow(x, y, r, col, a = .5) {
  g.save(); g.globalAlpha *= a;
  const gr = g.createRadialGradient(x, y, 0, x, y, r);
  gr.addColorStop(0, col); gr.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = gr; g.fillRect(x - r, y - r, 2 * r, 2 * r); g.restore();
}

// Round creature: o.look [-1..1, -1..1], o.mood smile|flat|sad|worried|happy|o
function blob(x, y, r, col, T, o = {}) {
  const sq = 1 + .03 * Math.sin(T * 3 + x);
  g.save(); g.translate(x, y); if (o.rot) g.rotate(o.rot); g.scale(1 / sq * (o.s || 1), sq * (o.s || 1));
  g.fillStyle = 'rgba(0,0,0,.25)'; g.beginPath(); g.ellipse(0, r * .98, r * .8, r * .14, 0, 0, 7); g.fill();
  g.fillStyle = col; g.beginPath(); g.arc(0, 0, r, 0, 7); g.fill();
  g.fillStyle = 'rgba(255,255,255,.18)'; g.beginPath(); g.ellipse(-r * .35, -r * .45, r * .32, r * .2, -.6, 0, 7); g.fill();
  const [lx, ly] = o.look || [0, 0];
  const blink = (Math.floor(T * 10 + x) % 37) === 0 ? .1 : 1;
  for (const sx of [-1, 1]) {
    g.fillStyle = C.white; g.beginPath(); g.ellipse(sx * r * .33, -r * .12, r * .24, r * .27 * blink, 0, 0, 7); g.fill();
    if (blink > .5) { g.fillStyle = C.ink; g.beginPath(); g.arc(sx * r * .33 + lx * r * .1, -r * .1 + ly * r * .1, r * .11, 0, 7); g.fill(); }
  }
  g.strokeStyle = C.ink; g.lineWidth = r * .07; g.lineCap = 'round'; g.beginPath();
  const m = o.mood || 'smile', my = r * .35;
  if (m === 'smile') g.arc(0, my - r * .1, r * .2, .2 * Math.PI, .8 * Math.PI);
  else if (m === 'happy') { g.fillStyle = C.ink; g.arc(0, my - r * .12, r * .22, 0, Math.PI); g.fill(); }
  else if (m === 'sad') g.arc(0, my + r * .12, r * .18, 1.2 * Math.PI, 1.8 * Math.PI);
  else if (m === 'worried') { g.moveTo(-r * .18, my + .02 * r); g.quadraticCurveTo(-r * .06, my - r * .06, 0, my); g.quadraticCurveTo(r * .08, my + r * .06, r * .18, my - r * .02); }
  else if (m === 'o') { g.arc(0, my, r * .08, 0, 7); }
  else { g.moveTo(-r * .15, my); g.lineTo(r * .15, my); }
  g.stroke();
  g.restore();
}
// Hovering helper bot
function bot(x, y, s, T, o = {}) {
  y += Math.sin(T * 2.4 + x * .01) * 10 * s;
  g.save(); g.translate(x, y); g.scale(s, s);
  glow(0, 0, 150, C.teal, .35);
  g.strokeStyle = C.grey; g.lineWidth = 6; g.beginPath(); g.moveTo(0, -62); g.lineTo(0, -95); g.stroke();
  g.fillStyle = (Math.floor(T * 2) % 2) ? C.yellow : C.orange; g.beginPath(); g.arc(0, -100, 11, 0, 7); g.fill();
  g.fillStyle = '#d9e4ff'; rr(-80, -62, 160, 124, 40); g.fill();
  g.fillStyle = C.ink; rr(-62, -44, 124, 88, 28); g.fill();
  g.fillStyle = C.teal;
  if (o.face === 'off') { g.fillRect(-30, -2, 60, 6); }
  else { for (const sx of [-1, 1]) { rr(sx * 26 - 10, -18, 20, 30, 10); g.fill(); } }
  g.restore();
}
function paper(x, y, w, h, rot = 0, o = {}) {
  g.save(); g.translate(x, y); g.rotate(rot);
  g.fillStyle = 'rgba(0,0,0,.25)'; rr(-w / 2 + 10, -h / 2 + 14, w, h, 18); g.fill();
  g.fillStyle = o.col || C.white; rr(-w / 2, -h / 2, w, h, 18); g.fill();
  g.fillStyle = '#c9c4e6';
  const n = o.lines ?? 6;
  for (let i = 0; i < n; i++) { rr(-w / 2 + w * .12, -h / 2 + h * .22 + i * h * .11, w * (i % 3 === 2 ? .5 : .76), h * .045, 6); g.fill(); }
  if (o.title) text(o.title, 0, -h / 2 + h * .11, h * .07, C.ink, { weight: 900 });
  g.restore();
}
function pennant(x, y, col, label, k) {
  const rise = (1 - back(k)) * 500;
  g.save(); g.translate(x, y + rise);
  g.fillStyle = '#e8e4ff'; rr(-6, -260, 12, 420, 6); g.fill();
  const wave = Math.sin(performanceT * 3 + x) * 10;
  g.fillStyle = col; g.beginPath(); g.moveTo(6, -255); g.quadraticCurveTo(110, -230 + wave, 220, -195); g.quadraticCurveTo(110, -165 - wave, 6, -135); g.fill();
  g.restore();
  text(label, x, y + rise + 210, 38, C.white, { weight: 900 });
}
let performanceT = 0;
function fraction(x, y, s) {
  text('¾ + ⅛ = ?', x, y, 40 * s, C.ink, { weight: 900 });
}
function desk(x, y, col, T, o = {}) {
  blob(x, y - 70, 78, col, T, o);
  g.fillStyle = '#6b4bbd'; rr(x - 130, y + 30, 260, 34, 12); g.fill();
  g.fillStyle = '#4e3699'; g.fillRect(x - 110, y + 64, 18, 60); g.fillRect(x + 92, y + 64, 18, 60);
  paper(x + 40, y + 8, 150, 52, -.05, { lines: 0 });
  fraction(x + 40, y + 8, .7);
}
function poof(x, y, k, col) {
  if (k <= 0 || k >= 1) return;
  const r = rng(Math.floor(x + y));
  for (let i = 0; i < 12; i++) {
    const a = r() * 6.28, d = easeOut(k) * (80 + r() * 90);
    alpha(1 - k, () => { g.fillStyle = col; g.beginPath(); g.arc(x + Math.cos(a) * d, y + Math.sin(a) * d, 18 * (1 - k) + 4, 0, 7); g.fill(); });
  }
}
function pill(x, y, w, label, col, k, icon) {
  const off = (1 - back(k)) * -W;
  alpha(k, () => {
    g.save(); g.translate(off, 0);
    g.fillStyle = 'rgba(255,255,255,.1)'; rr(x - w / 2, y - 52, w, 104, 52); g.fill();
    g.fillStyle = col; g.beginPath(); g.arc(x - w / 2 + 52, y, 36, 0, 7); g.fill();
    text(icon, x - w / 2 + 52, y + 2, 44, C.ink, { weight: 900 });
    text(label, x - w / 2 + 110, y + 2, 46, C.white, { weight: 900, align: 'left' });
    g.restore();
  });
}
function brain(x, y, s, T, mood) {
  g.save(); g.translate(x, y); g.scale(s, s); g.rotate(Math.sin(T * 2) * .04);
  glow(0, 0, 320, C.pink, .35);
  g.fillStyle = '#ff8fb1';
  for (const [cx, cy, r] of [[-110, -40, 120], [0, -90, 130], [110, -40, 120], [-60, 50, 115], [70, 50, 115]]) { g.beginPath(); g.arc(cx, cy, r, 0, 7); g.fill(); }
  g.strokeStyle = '#e0517d'; g.lineWidth = 12; g.lineCap = 'round';
  for (const [a, b, c, d] of [[-150, -60, -60, -120], [-20, -150, 30, -40], [80, -110, 160, -20], [-120, 60, -20, 100], [40, 30, 130, 80]]) { g.beginPath(); g.moveTo(a, b); g.quadraticCurveTo((a + c) / 2 + 40, (b + d) / 2 - 40, c, d); g.stroke(); }
  g.restore();
  for (const sx of [-1, 1]) { g.fillStyle = C.white; g.beginPath(); g.ellipse(x + sx * 60 * s, y - 10 * s, 34 * s, 40 * s, 0, 0, 7); g.fill(); g.fillStyle = C.ink; g.beginPath(); g.arc(x + sx * 60 * s + (mood === 'worried' ? sx * -8 : 0), y - 2 * s, 16 * s, 0, 7); g.fill(); }
}

const SCENES = [
  // 1 · Ten minutes
  (u, D, T) => {
    performanceT = T; space(T);
    const cx = W / 2, cy = 800, k = clamp(u / 3.0);
    glow(cx, cy, 520, C.yellow, .25);
    g.lineCap = 'round';
    g.strokeStyle = 'rgba(255,255,255,.12)'; g.lineWidth = 46; g.beginPath(); g.arc(cx, cy, 330, 0, 7); g.stroke();
    g.strokeStyle = C.yellow; g.beginPath(); g.arc(cx, cy, 330, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * (1 - ease(k)) + .0001); g.stroke();
    const secs = Math.round(600 * (1 - ease(k)));
    const flash = k >= 1 ? (Math.floor(u * 6) % 2 ? .4 : 1) : 1;
    text(`${String(Math.floor(secs / 60)).padStart(2, '0')}:${String(secs % 60).padStart(2, '0')}`, cx, cy, 190, C.white, { weight: 900, alpha: flash });
    blob(cx, 1300, 110, C.orange, T, { look: [0, -1], mood: k >= 1 ? 'o' : 'flat', s: back(u / .6) });
  },
  // 2 · The study
  (u, D, T) => {
    performanceT = T; space(T, '#151040', '#3a1f6b');
    const tUni = [at(2, 'carnegie'), at(2, 'oxford'), at(2, 'mit'), at(2, 'ucla')];
    const tPaper = at(2, 'posted'), tBold = at(2, 'bold'), tBurst = at(2, 'short'), tGone = at(2, 'gone');
    // calendar
    alpha(1 - ramp(u, tUni[0] - .2, .4), () => {
      const y = lerp(-300, 760, back(u / .7));
      g.fillStyle = C.white; rr(W / 2 - 240, y - 220, 480, 440, 40); g.fill();
      g.fillStyle = C.pink; rr(W / 2 - 240, y - 220, 480, 130, [40, 40, 0, 0]); g.fill();
      text('APRIL', W / 2, y - 155, 70, C.white, { weight: 900 });
      text('2026', W / 2, y + 60, 150, C.ink, { weight: 900 });
    });
    // pennants
    alpha(1 - ramp(u, tPaper, .5), () => {
      const cols = [C.red, C.blue, C.yellow, C.teal], labels = ['CARNEGIE\nMELLON', 'OXFORD', 'MIT', 'UCLA'];
      [0, 1, 2, 3].forEach(i => {
        const x = 170 + i * 250, k = ramp(u, tUni[i] - .1, .55);
        if (k <= 0) return;
        const lines = labels[i].split('\n');
        pennant(x, 900, cols[i], lines.length > 1 ? '' : lines[0], k);
        if (lines.length > 1) { const rise = (1 - back(k)) * 500; text(lines[0], x, 1100 + rise, 34, C.white, { weight: 900 }); text(lines[1], x, 1140 + rise, 34, C.white, { weight: 900 }); }
      });
    });
    // the paper
    alpha(ramp(u, tPaper, .4) * (1 - ramp(u, tBurst - .3, .5)), () => {
      const k = back(ramp(u, tPaper, .7)), pulse = 1 + .06 * Math.sin(clamp((u - tBold) / .5) * Math.PI);
      glow(W / 2, 780, 520, C.yellow, .3);
      g.save(); g.translate(W / 2, lerp(1400, 780, k)); g.scale(pulse, pulse);
      paper(0, 0, 520, 680, -.03, { title: 'PREPRINT', lines: 7 }); g.restore();
      if (u > tBold) { const s = back(ramp(u, tBold, .4)); g.save(); g.translate(W / 2 + 280, 470); g.scale(s, s); g.fillStyle = C.yellow; g.beginPath(); for (let i = 0; i < 16; i++) { const a = i / 16 * 6.28, r = i % 2 ? 70 : 120; g.lineTo(Math.cos(a) * r, Math.sin(a) * r); } g.fill(); text('!', 0, 6, 120, C.ink, { weight: 900 }); g.restore(); }
    });
    // AI help, then gone
    alpha(ramp(u, tBurst - .2, .5), () => {
      const off = 1 - ramp(u, tGone - .2, .4);
      desk(W / 2, 1050, C.blue, T, { look: off > .5 ? [.8, -.6] : [0, 0], mood: u > at(2, 'worse') ? 'worried' : 'smile' });
      alpha(off, () => bot(W / 2 + 230, 760, 1, T));
      poof(W / 2 + 230, 760, ramp(u, tGone - .2, .6), C.teal);
      const kw = ramp(u, at(2, 'worse'), .4);
      alpha(kw, () => {
        g.save(); g.translate(W / 2 - 280, 760 + (1 - back(kw)) * -60);
        g.fillStyle = C.red; g.beginPath(); g.moveTo(-50, -60); g.lineTo(50, -60); g.lineTo(50, 10); g.lineTo(90, 10); g.lineTo(0, 100); g.lineTo(-90, 10); g.lineTo(-50, 10); g.fill(); g.restore();
        text('NEXT TASK', W / 2, 1290, 54, C.white, { weight: 900, alpha: kw });
      });
    });
  },
  // 3 · Setup
  (u, D, T) => {
    performanceT = T; space(T, '#14123d', '#24305e');
    grid(u, T, { botsIn: at(3, 'some') - .1 });
    alpha(1 - ramp(u, at(3, 'hundreds') + .4, .4), () => text('THE EXPERIMENT', W / 2, 760, 96, C.yellow, { weight: 900 }));
  },
  // 4 · AI taken away
  (u, D, T) => {
    performanceT = T; space(T, '#0d0b2a', '#1a1f40');
    const tAway = at(4, 'taken'), tSolo = at(4, 'everyone');
    grid(u + 99, T, { botsIn: 0, botsOut: tAway + 99, worried: u > tSolo, look: [Math.sin(u * 3), 0] });
    alpha(ramp(u, tAway + .4, .6) * .55, () => { g.fillStyle = '#000'; g.fillRect(0, 0, W, H); });
    alpha(ramp(u, tSolo, .5), () => text('ON YOUR OWN', W / 2, 260, 96, C.white, { weight: 900 }));
  },
  // 5 · Result
  (u, D, T) => {
    performanceT = T; space(T, '#140f38', '#2b1c55');
    const base = 900, maxH = 560, k = ease(u / 1.2), drop = ease(ramp(u, at(5, '20'), .8));
    const bars = [[330, C.teal, 'NO AI', 1], [750, C.pink, 'HAD AI', 1 - .2 * drop]];
    g.fillStyle = 'rgba(255,255,255,.15)'; g.fillRect(140, base, 800, 6);
    for (const [x, col, lab, v] of bars) {
      const h = maxH * k * v;
      g.fillStyle = col; rr(x - 110, base - h, 220, h, [24, 24, 0, 0]); g.fill();
      text(lab, x, base + 60, 50, C.white, { weight: 900 });
    }
    alpha(drop, () => text('−20%', 750, base - maxH * .8 - 80, 110, C.pink, { weight: 900 }));
    // skipped questions pile
    const tSkip = at(5, 'skipped');
    const r = rng(3);
    for (let i = 0; i < 14; i++) {
      const t0 = tSkip + i * .2, kk = ease(ramp(u, t0, .5));
      if (kk <= 0) { r(); r(); continue; }
      const px = 560 + r() * 380, py = lerp(-100, 1300 - (i % 5) * 26 - Math.floor(i / 5) * 40, kk);
      g.fillStyle = '#e7e2ff'; g.beginPath(); g.arc(px, py, 38, 0, 7); g.fill();
      g.strokeStyle = '#b7b0de'; g.lineWidth = 5; g.beginPath(); g.moveTo(px - 20, py - 10); g.lineTo(px + 10, py + 14); g.moveTo(px + 18, py - 18); g.lineTo(px - 8, py + 4); g.stroke();
      r();
    }
    alpha(ramp(u, tSkip, .4), () => {
      const tired = u > at(5, 'stopped');
      blob(330, 1240, 90, C.pink, T, { mood: tired ? 'sad' : 'worried', look: [.6, .4], rot: tired ? -.3 * ease(ramp(u, at(5, 'stopped'), .6)) : 0 });
      text('SKIPPED', 750, 1060, 50, C.grey, { weight: 900 });
    });
  },
  // 6 · Hints vs answers
  (u, D, T) => {
    performanceT = T; space(T, '#121035', '#232a5c');
    const tR = at(6, 'ones'), tFine = at(6, 'fine'), tFell = at(6, 'fell');
    g.fillStyle = 'rgba(255,255,255,.08)'; g.fillRect(W / 2 - 3, 300, 6, 1100 * ramp(u, tR - .3, .5));
    // left: hints
    alpha(ramp(u, at(6, 'people') - .2, .4), () => {
      text('HINTS', 270, 360, 80, C.green, { weight: 900 });
      bot(270, 600, .8, T);
      const lk = ease(ramp(u, at(6, 'hints'), .8));
      const lx = lerp(270, 270, lk), ly = lerp(660, 900, lk);
      glow(lx, ly, 120, C.yellow, .6);
      g.fillStyle = C.yellow; g.beginPath(); g.arc(lx, ly, 34, 0, 7); g.fill(); g.fillStyle = '#c9a400'; g.fillRect(lx - 14, ly + 28, 28, 18);
      blob(270, 1110, 110, C.orange, T, { mood: u > tFine ? 'happy' : 'smile', look: [0, -1] });
      alpha(ramp(u, tFine, .3), () => { const s = back(ramp(u, tFine, .4)); g.save(); g.translate(400, 980); g.scale(s, s); g.fillStyle = C.green; g.beginPath(); g.arc(0, 0, 56, 0, 7); g.fill(); g.strokeStyle = C.ink; g.lineWidth = 14; g.lineCap = 'round'; g.beginPath(); g.moveTo(-22, 2); g.lineTo(-4, 20); g.lineTo(26, -16); g.stroke(); g.restore(); });
    });
    // right: answers
    alpha(ramp(u, tR - .2, .4), () => {
      text('ANSWERS', 810, 360, 80, C.red, { weight: 900 });
      bot(810, 600, .8, T);
      const ak = ease(ramp(u, tR + .4, .8));
      paper(810, lerp(640, 880, ak), 170, 210, .1, { title: 'x = 5', lines: 3 });
      const fall = ease(ramp(u, tFell, .7));
      blob(810, 1110 + fall * 150, 110, C.blue, T, { mood: u > tFell ? 'sad' : 'smile', rot: fall * .5 });
      alpha(fall, () => { g.fillStyle = C.red; g.save(); g.translate(950, 980 + fall * 60); g.beginPath(); g.moveTo(-36, -50); g.lineTo(36, -50); g.lineTo(36, 0); g.lineTo(66, 0); g.lineTo(0, 70); g.lineTo(-66, 0); g.lineTo(-36, 0); g.fill(); g.restore(); });
    });
    alpha(1 - ramp(u, at(6, 'people') - .3, .3), () => text('THE TWIST', W / 2, 800, 130, C.yellow, { weight: 900, alpha: back(u / .5) }));
  },
  // 7 · Not so fast
  (u, D, T) => {
    performanceT = T; space(T, '#1a0f3a', '#3b1d5e');
    const tNot = at(7, 'not'), tStamp = at(7, 'pre'), shrink = ease(ramp(u, tNot, .7));
    const by = lerp(820, 440, shrink), bs = lerp(1.25, .72, shrink);
    brain(W / 2, by, bs * back(u / .6), T, u > tNot ? 'worried' : '');
    alpha(1 - shrink, () => {
      g.fillStyle = C.yellow; rr(90, 1180, 900, 160, 30); g.fill();
      text('IS AI ROTTING', W / 2, 1230, 70, C.ink, { weight: 900 }); text('OUR BRAINS?', W / 2, 1300, 70, C.ink, { weight: 900 });
    });
    if (u > tStamp - .1) {
      const k = ramp(u, tStamp - .1, .25), s = lerp(3, 1, easeOut(k));
      alpha(k, () => { g.save(); g.translate(W / 2, by + 10); g.rotate(-.18); g.scale(s, s); g.strokeStyle = C.red; g.lineWidth = 16; rr(-330, -85, 660, 170, 20); g.stroke(); text('PREPRINT', 0, 6, 120, C.red, { weight: 900 }); g.restore(); });
    }
    const items = [['NOT PEER-REVIEWED', at(7, 'peer') - .25], ['NOT REPLICATED', at(7, 'replicated') - .15], ['ONLINE VOLUNTEERS', at(7, 'online')], ['SIMPLE MATH', at(7, 'simple')], ['MINUTES, NOT MONTHS', at(7, 'measured')]];
    items.forEach(([lab, t0], i) => pill(W / 2, 760 + i * 128, 820, lab, C.orange, ramp(u, t0, .45), '!'));
  },
  // 8 · The tool isn't the problem
  (u, D, T) => {
    performanceT = T; space(T, '#101235', '#1f3658');
    const tTool = at(8, 'tool'), tHow = at(8, 'how');
    // a big claim shrinking into a small, bright idea
    alpha(1 - ramp(u, tTool - .3, .4), () => {
      const k = ease(ramp(u, at(8, 'smaller'), 1.2));
      const r = lerp(330, 90, k);
      glow(W / 2, 780, r * 2.2, k > .5 ? C.yellow : C.pink, .4);
      g.fillStyle = k > .5 ? C.yellow : '#ff8fb1'; g.beginPath();
      for (let i = 0; i < 6; i++) { const a = i / 6 * 6.28 + T * .5; g.lineTo(W / 2 + Math.cos(a) * r, 780 + Math.sin(a) * r); } g.fill();
      alpha(ramp(u, at(8, 'useful'), .4), () => text('SMALLER · MORE USEFUL', W / 2, 1120, 60, C.yellow, { weight: 900 }));
    });
    alpha(ramp(u, tTool - .2, .4), () => {
      const lean = ease(ramp(u, tHow, .8)) * (1 - ease(ramp(u, at(8, 'be') + .3, .6)));
      bot(640, 840 + lean * 40, 1.1, T);
      blob(390, 1000, 120, C.purple, T, { rot: lean * .55, look: [1, -.4], mood: lean > .3 ? 'worried' : 'smile' });
      text('THE TOOL', 640, 600, 60, C.teal, { weight: 900, alpha: ramp(u, tTool, .3) });
      alpha(ramp(u, tHow, .4), () => text('HOW WE LEAN ON IT', W / 2, 1260, 64, C.yellow, { weight: 900 }));
    });
  },
  // 9 · Read it together
  (u, D, T) => {
    performanceT = T; space(T, '#130f36', '#2d2366');
    const tRead = at(9, 'read'), tWait = at(9, 'wait');
    glow(W / 2, 820, 600, C.purple, .35);
    const k = back(ramp(u, tRead - .5, .7));
    blob(250, 1080, 115, C.orange, T, { look: [1, -.5], s: k });
    blob(830, 1080, 115, C.teal, T, { look: [-1, -.5], s: k });
    paper(W / 2, lerp(1500, 850, ease(ramp(u, tRead - .3, .8))), 440, 560, 0, { title: 'PREPRINT', lines: 7 });
    alpha(ramp(u, tWait, .2), () => {
      const s = lerp(2.5, 1, easeOut(ramp(u, tWait, .3)));
      g.save(); g.translate(W / 2 + 150, 620); g.rotate(.15); g.scale(s, s);
      g.fillStyle = C.yellow; rr(-200, -70, 400, 140, 24); g.fill();
      text('REPLICATION', 0, -22, 46, C.ink, { weight: 900 }); text('PENDING…', 0, 32, 46, C.ink, { weight: 900 });
      g.restore();
    });
    alpha(ramp(u, D - 1.0, .9), () => { g.fillStyle = '#000'; g.fillRect(0, 0, W, H); });
  },
];
// 6 students; half get a bot.
function grid(u, T, o) {
  const pos = [[290, 620], [790, 620], [290, 960], [790, 960], [290, 1300], [790, 1300]];
  pos.forEach(([x, y], i) => {
    const k = back(ramp(u, at(3, 'hundreds') - .2 + i * .12, .5));
    if (k <= 0) return;
    g.save(); g.translate(x, y); g.scale(k, k); g.translate(-x, -y);
    desk(x, y, BLOBS[i], T, { look: o.look || [0, .6], mood: o.worried ? 'worried' : 'smile' });
    g.restore();
    if (i % 3 === 0 || i === 4) {
      const inK = back(ramp(u, o.botsIn + i * .1, .4)), outK = o.botsOut != null ? ramp(u, o.botsOut, .25) : 0;
      alpha(1 - outK, () => { if (inK > 0) bot(x + 150, y - 130, .55 * inK, T); });
      if (o.botsOut != null) poof(x + 150, y - 130, ramp(u, o.botsOut, .7), C.teal);
    }
  });
}
const CAPTION = { size: 82, y: 1590, font: 'Inter', fg: C.white, hi: C.yellow, stroke: 20, strokeColor: C.ink };
