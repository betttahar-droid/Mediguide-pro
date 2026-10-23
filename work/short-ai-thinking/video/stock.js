// Video 2: documentary explainer cut from free stock photos and public-domain
// archive film. One global shot list; calm cross-fades, a steady slow push-in,
// and overlays that fade and settle. No flashes, pans or bounces.
window.NO_XF = true;
const Y = '#ffd400', INK = '#0b0b0f';
const FX = 0, FY = 340, FW = 1080, FH = 1000;
const XFADE = .6;

const IMG = {}, VID = {};
const PHOTOS = ['stopwatch', 'cmu', 'oxford', 'mit', 'ucla', 'exam', 'laptop', 'notes', 'bulb', 'answers', 'brain', 'lab', 'paper', 'robot'];
const CLIPS = ['c_cpu', 'c_door', 'c_alone', 'c_board', 'c_write', 'c_puzzled', 'c_machine', 'c_group', 'c_read2', 'c_yawn'];
window.whenReady = () => Promise.all([
  ...PHOTOS.map(n => new Promise(ok => { const i = new Image(); i.onload = ok; i.onerror = ok; i.src = `media/${n}.jpg`; IMG[n] = i; })),
  ...CLIPS.map(n => new Promise(ok => { const v = document.createElement('video'); v.muted = true; v.preload = 'auto'; v.src = `media/${n}.webm`; v.onloadeddata = ok; v.onerror = ok; VID[n] = v; })),
]);

const T0 = b => BEATS[b - 1].start;
const W_ = (b, w, n) => T0(b) + at(b, w, n);
// [global start, media, {in, head, head2, head2At, label, mark, markAt, stamp}]
const SHOTS = [
  [T0(1), 'stopwatch', { head: 'CAN AI MAKE YOU DUMBER?' }],
  [T0(2), 'notes', { label: 'STUCK ON A MATH PROBLEM' }],
  [W_(2, 'chatbot') - .3, 'laptop', { label: 'SO YOU ASK A CHATBOT', label2: 'IT GIVES YOU THE ANSWER', label2At: W_(2, 'answer') - .2 }],
  [W_(2, 'then') - .2, 'c_write', { in: 3.0, head: 'THEN IT DISAPPEARS' }],
  [W_(3, 'researchers') - .3, 'UNIS', {}],
  [W_(3, 'hundreds') - .2, 'c_alone', { label: 'HUNDREDS OF PEOPLE', label2: 'FRACTION PROBLEMS', label2At: W_(3, 'fraction') - .2 }],
  [W_(3, 'some') - .2, 'robot', { label: 'SOME GOT AN AI' }],
  [T0(4), 'c_door', { in: 2.0, head: 'AI: SWITCHED OFF' }],
  [T0(5), 'CHART', {}],
  [W_(5, 'skipped') - .3, 'paper', { label: 'SKIPPED QUESTIONS' }],
  [W_(5, 'gave') - .3, 'c_yawn', { in: 2.5, label: 'THEY GAVE UP MORE OFTEN' }],
  [T0(6), 'bulb', { head: 'THE TWIST', head2: 'HINTS: FINE', head2At: W_(6, 'hints'), mark: 'ok', markAt: W_(6, 'fine') }],
  [W_(6, 'people', 1) - .2, 'c_puzzled', { head: 'ANSWERS: HIT HARDEST', mark: 'bad', markAt: W_(6, 'hardest') }],
  [T0(7), 'brain', { head: 'IS AI MAKING US DUMBER?', head2: 'NOT SO FAST', head2At: W_(7, 'not') }],
  [W_(7, 'one') - .3, 'lab', { stamp: true }],
  [T0(8), 'c_machine', { head: 'THE LESSON IS SIMPLE' }],
  [W_(8, 'think') - .3, 'c_read2', { label: 'AI CAN THINK FOR YOU…', label2: '…OR THINK WITH YOU', label2At: W_(8, 'with') - .2 }],
  [W_(8, 'difference') - .3, 'answers', { head: 'ANSWER, OR HINT?' }],
  [T0(9), 'exam', { head: 'ASK FOR THE HINT' }],
  [W_(9, 'your') - .3, 'brain', { head: 'YOUR BRAIN WILL THANK YOU' }],
].map((s, i, a) => ({ s: s[0], e: i + 1 < a.length ? a[i + 1][0] : END, m: s[1], o: s[2], i }));
const shotAt = t => SHOTS.find(s => t >= s.s && t < s.e) || SHOTS[SHOTS.length - 1];
window.shotTable = () => SHOTS.map(s => [s.m, +(s.e - s.s).toFixed(2)]);

window.prepare = async t => {
  const sh = shotAt(t), list = [sh];
  if (SHOTS[sh.i - 1] && t - sh.s < XFADE) list.push(SHOTS[sh.i - 1]);
  for (const s of list) {
    const v = VID[s.m]; if (!v) continue;
    const want = Math.min((s.o.in || 0) + (t - s.s), v.duration - .05);
    if (Math.abs(v.currentTime - want) < 1e-3) continue;
    await new Promise(ok => { v.onseeked = ok; v.currentTime = want; });
  }
};

function cover(src, x, y, w, h, k) {
  const sw = src.videoWidth || src.naturalWidth, shh = src.videoHeight || src.naturalHeight;
  if (!sw) return;
  const sc = Math.max(w / sw, h / shh) * k, dw = sw * sc, dh = shh * sc;
  g.drawImage(src, x - (dw - w) / 2, y - (dh - h) / 2, dw, dh);
}
function tag(s, x, y, size, bg, fg) {
  g.save(); g.font = `900 ${size}px Inter`; g.textBaseline = 'middle';
  const w = g.measureText(s).width, pad = size * .35, fit = Math.min(1, (W - 2 * x) / (w + 2 * pad));
  g.translate(x, y); g.scale(fit, fit);
  g.fillStyle = bg; g.fillRect(0, -size * .7, w + 2 * pad, size * 1.4);
  g.fillStyle = fg; g.fillText(s, pad, size * .04);
  g.restore();
}
// fade in and settle 18px upward over .45s
function settle(t, t0, f) { const k = easeOut((t - t0) / .45); if (k <= 0) return; g.save(); g.translate(0, (1 - k) * 18); g.globalAlpha *= k; f(); g.restore(); }

function chart(u) {
  g.fillStyle = '#121219'; g.fillRect(FX, FY, FW, FH);
  const base = FY + FH - 160, maxH = 560, k = ease(u / 1.4), drop = ease((u - at(5, '20')) / 1.0);
  text('PROBLEMS SOLVED WITHOUT HELP', W / 2, FY + 80, 40, '#aaa', { weight: 800 });
  [[330, '#3fb6ff', 'NO AI', 1], [750, Y, 'HAD AI', 1 - .2 * drop]].forEach(([x, col, lab, v]) => {
    const h = maxH * k * v; g.fillStyle = col; g.fillRect(x - 130, base - h, 260, h);
    text(lab, x, base + 64, 46, '#fff', { weight: 900 });
  });
  g.fillStyle = '#444'; g.fillRect(FX + 80, base, FW - 160, 4);
  if (drop > 0) text('≈ −20%', 750, base - maxH * .8 - 64, 84, Y, { weight: 900, alpha: drop });
  text('Illustrative; the preprint reports ~20% lower', W / 2, FY + FH - 34, 26, '#777', { weight: 600 });
}
function unis(t) {
  g.fillStyle = INK; g.fillRect(FX, FY, FW, FH);
  [['cmu', 'CARNEGIE MELLON', 'carnegie'], ['oxford', 'OXFORD', 'oxford'], ['mit', 'MIT', 'mit'], ['ucla', 'UCLA', 'ucla']].forEach(([img, lab, w], i) => {
    const x = FX + (i % 2) * FW / 2, y = FY + Math.floor(i / 2) * FH / 2, t0 = W_(3, w) - .15, k = ease((t - t0) / .5);
    if (k <= 0) return;
    alpha(k, () => {
      g.save(); g.beginPath(); g.rect(x + 4, y + 4, FW / 2 - 8, FH / 2 - 8); g.clip();
      cover(IMG[img], x + 4, y + 4, FW / 2 - 8, FH / 2 - 8, 1 + .03 * clamp((t - t0) / 6)); g.restore();
      tag(lab, x + 24, y + FH / 2 - 50, 36, INK, '#fff');
    });
  });
}
function mark(kind, k) {
  if (k <= 0) return;
  g.save(); g.globalAlpha *= easeOut(k / .45); g.translate(FX + FW - 120, FY + 120);
  g.fillStyle = kind === 'ok' ? '#21c25e' : '#e8283c'; g.beginPath(); g.arc(0, 0, 70, 0, 7); g.fill();
  g.strokeStyle = '#fff'; g.lineWidth = 16; g.lineCap = 'round'; g.beginPath();
  if (kind === 'ok') { g.moveTo(-30, 2); g.lineTo(-6, 26); g.lineTo(32, -22); } else { g.moveTo(-26, -26); g.lineTo(26, 26); g.moveTo(26, -26); g.lineTo(-26, 26); }
  g.stroke(); g.restore();
}
function stampAndList(t) {
  const t0 = W_(7, 'one') - .1, k = easeOut((t - t0) / .45);
  alpha(k, () => {
    g.save(); g.translate(W / 2, FY + 230); g.rotate(-.1); g.scale(lerp(1.08, 1, k), lerp(1.08, 1, k));
    g.fillStyle = 'rgba(0,0,0,.35)'; g.fillRect(-310, -85, 620, 170);
    g.strokeStyle = '#e8283c'; g.lineWidth = 14; g.strokeRect(-300, -80, 600, 160);
    text('PREPRINT', 0, 6, 110, '#e8283c', { weight: 900 }); g.restore();
  });
  [['ONE STUDY', W_(7, 'one')], ['NOT PEER-REVIEWED', W_(7, 'peer')], ['NOT REPEATED YET', W_(7, 'repeated')], ['TESTED MINUTES LATER', W_(7, 'minutes')]]
    .forEach(([lab, t1], i) => settle(t, t1 - .1, () => tag('✕ ' + lab, FX + 40, FY + 500 + i * 100, 48, i === 0 ? INK : '#e8283c', '#fff')));
}

function drawShot(sh, t, ov = 1) {
  const u = t - sh.s, o = sh.o, src = IMG[sh.m] || VID[sh.m];
  g.fillStyle = INK; g.fillRect(0, 0, W, H);
  if (src) { g.save(); g.filter = 'blur(38px) brightness(.38) saturate(1.2)'; cover(src, -60, -60, W + 120, H + 120, 1); g.restore(); }
  g.save(); g.beginPath(); g.rect(FX, FY, FW, FH); g.clip();
  if (sh.m === 'CHART') chart(t - T0(5));
  else if (sh.m === 'UNIS') unis(t);
  else if (src) { if (VID[sh.m]) g.filter = 'contrast(1.08)'; cover(src, FX, FY, FW, FH, 1 + .04 * clamp(u / 8)); g.filter = 'none'; }
  const vg = g.createRadialGradient(W / 2, FY + FH / 2, FH * .35, W / 2, FY + FH / 2, FH * .85);
  vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,.45)'); g.fillStyle = vg; g.fillRect(FX, FY, FW, FH);
  g.restore();
  if (ov <= 0) return;
  g.save(); g.globalAlpha *= ov;
  const swap = o.head2At && t >= o.head2At;
  if (o.head) alpha(swap ? 1 - (t - o.head2At) / .3 : 1, () => settle(t, sh.s + .35, () => tag(o.head, FX + 40, FY - 80, 64, Y, INK)));
  if (swap) settle(t, o.head2At + .2, () => tag(o.head2, FX + 40, FY - 80, 64, Y, INK));
  const swapL = o.label2At && t >= o.label2At;
  if (o.label) alpha(swapL ? 1 - (t - o.label2At) / .3 : 1, () => settle(t, sh.s + .4, () => tag(o.label, FX + 40, FY + FH - 70, 44, INK, '#fff')));
  if (swapL) settle(t, o.label2At + .2, () => tag(o.label2, FX + 40, FY + FH - 70, 44, INK, '#fff'));
  if (o.mark) mark(o.mark, t - o.markAt);
  if (o.stamp) stampAndList(t);
  g.restore();
}
function draw(t) {
  const sh = shotAt(t), prev = SHOTS[sh.i - 1];
  if (prev && t - sh.s < XFADE) { drawShot(prev, t, 1 - (t - sh.s) / (XFADE * .5)); alpha(ease((t - sh.s) / XFADE), () => drawShot(sh, t)); }
  else drawShot(sh, t);
  if (t >= T0(3)) text('Source: arXiv 2604.04721 (preprint, April 2026)', W / 2, FY + FH + 50, 28, 'rgba(255,255,255,.65)', { weight: 600 });
  alpha((t - (END - 1.2)) / 1.1, () => { g.fillStyle = '#000'; g.fillRect(0, 0, W, H); });
}

const SCENES = Array.from({ length: 9 }, () => (u, D, T) => draw(T));
const CAPTION = { size: 76, y: 1560, font: 'Inter', fg: '#ffffff', hi: Y, stroke: 18, strokeColor: '#000' };
