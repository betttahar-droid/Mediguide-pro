// Shared frame engine for both Shorts. render.py calls window.renderFrame(t)
// for every frame and reads the canvas back; nothing here runs on a clock.
const W = 1080, H = 1920;
const cv = document.getElementById('c');
cv.width = W; cv.height = H;
const g = cv.getContext('2d');

const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, k) => a + (b - a) * k;
const ease = k => (k = clamp(k), k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
const easeOut = k => 1 - Math.pow(1 - clamp(k), 3);
const back = k => { k = clamp(k); const c = 1.9; return 1 + (c + 1) * Math.pow(k - 1, 3) + c * Math.pow(k - 1, 2); };
// 0→1 over [a, a+d]
const ramp = (u, a, d = .5) => clamp((u - a) / d);
function rng(seed) { let s = seed >>> 0; return () => (s = (s * 1664525 + 1013904223) >>> 0) / 4294967296; }

// Beats with word timings (local to the beat), glued back where whisper split
// "20" "%" or "pre" "-print".
const BEATS = WORDS.map(b => {
  const ws = [];
  for (const w of b.words) {
    if (ws.length && /^[-%]/.test(w.w)) { const p = ws[ws.length - 1]; p.w += w.w; p.e = w.e; }
    else ws.push({ ...w });
  }
  return { ...b, words: ws };
});
const END = BEATS[BEATS.length - 1].start + BEATS[BEATS.length - 1].dur + 1.2;
// local time of the n-th word that starts with `word` in beat b (1-based)
function at(b, word, n = 0) {
  const ws = BEATS[b - 1].words.filter(w => w.w.toLowerCase().replace(/[^a-z0-9%']/g, '').startsWith(word.toLowerCase()));
  return ws.length ? ws[Math.min(n, ws.length - 1)].s : 0;
}

// Captions: chunks of up to 3 words, current word highlighted.
const CHUNKS = [];
for (const b of BEATS) {
  let cur = [];
  b.words.forEach((w, i) => {
    cur.push(w);
    const brk = /[.,:?!]$/.test(w.w) || cur.length === 3 || i === b.words.length - 1;
    if (brk) { CHUNKS.push({ beat: b.beat, s: b.start + cur[0].s, e: b.start + cur[cur.length - 1].e, words: cur.map(x => ({ ...x, s: x.s + b.start, e: x.e + b.start })) }); cur = []; }
  });
}
function captions(t, style) {
  const c = CHUNKS.find((c, i) => t >= c.s - .05 && t < (CHUNKS[i + 1] ? Math.min(CHUNKS[i + 1].s - .05, c.e + .8) : c.e + .8));
  if (!c) return;
  const k = easeOut((t - c.s + .05) / .15);
  g.save();
  g.font = `900 ${style.size}px ${style.font}`;
  g.textAlign = 'left'; g.textBaseline = 'middle';
  const words = c.words.map(w => w.w.replace(/[.,:]$/, '').toUpperCase());
  const sp = style.size * .28;
  const widths = words.map(w => g.measureText(w).width);
  let total = widths.reduce((a, b) => a + b, 0) + sp * (words.length - 1);
  const fit = Math.min(1, (W - 120) / total);
  g.translate(W / 2 * (1 - fit), style.y * (1 - fit)); g.scale(fit, fit);
  let x = W / 2 - total / 2; const y = style.y + (1 - k) * 30;
  g.globalAlpha = k;
  words.forEach((w, i) => {
    const live = t >= c.words[i].s - .03;
    g.lineJoin = 'round'; g.lineWidth = style.stroke; g.strokeStyle = style.strokeColor;
    g.strokeText(w, x, y);
    g.fillStyle = live && t < c.words[i].e + .15 ? style.hi : style.fg;
    g.fillText(w, x, y);
    x += widths[i] + sp;
  });
  g.restore();
}

function alpha(a, f) { if (a <= 0) return; g.save(); g.globalAlpha *= clamp(a); f(); g.restore(); }
function rr(x, y, w, h, r) { g.beginPath(); g.roundRect(x, y, w, h, r); }
function text(s, x, y, size, color, opts = {}) {
  g.save();
  g.font = `${opts.weight || 800} ${size}px ${opts.font || 'Inter'}`;
  g.textAlign = opts.align || 'center'; g.textBaseline = 'middle';
  if (opts.alpha != null) g.globalAlpha *= opts.alpha;
  if (opts.stroke) { g.lineJoin = 'round'; g.lineWidth = opts.stroke; g.strokeStyle = opts.strokeColor || '#000'; g.strokeText(s, x, y); }
  g.fillStyle = color; g.fillText(s, x, y);
  g.restore();
}

// Each video supplies SCENES[0..8] (u = local time, D = time until next beat)
// and CAPTION style. Scenes paint the whole frame, so a cross-fade is just
// painting the next scene on top with alpha.
const XF = .35;
window.renderFrame = function (t) {
  g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1;
  let i = BEATS.length - 1;
  while (i > 0 && t < BEATS[i].start) i--;
  const D = i < BEATS.length - 1 ? BEATS[i + 1].start - BEATS[i].start : END - BEATS[i].start;
  SCENES[i](t - BEATS[i].start, D, t);
  if (!window.NO_XF && i < BEATS.length - 1) {
    const toNext = BEATS[i + 1].start - t;
    if (toNext < XF) {
      g.save(); g.globalAlpha = 1 - toNext / XF;
      const D2 = i + 1 < BEATS.length - 1 ? BEATS[i + 2].start - BEATS[i + 1].start : END - BEATS[i + 1].start;
      SCENES[i + 1](-toNext, D2, t); g.restore();
    }
  }
  g.globalAlpha = 1;
  if (window.OVERLAY) OVERLAY(t);
  captions(t, CAPTION);
};
window.END = END;
