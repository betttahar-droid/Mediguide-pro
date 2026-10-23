// Video 2: documentary explainer cut from free stock photos and public-domain
// archive film. One global shot list; hard cuts, as that style does.
window.NO_XF = true;
const Y = '#ffd400', INK = '#0b0b0f';
const FX = 0, FY = 340, FW = 1080, FH = 1000;

const IMG = {}, VID = {};
const PHOTOS = ['stopwatch', 'cmu', 'oxford', 'mit', 'ucla', 'exam', 'laptop', 'notes', 'bulb', 'answers', 'brain', 'lab', 'hourglass', 'paper', 'robot'];
const CLIPS = ['c_cpu', 'c_door', 'c_class', 'c_alone', 'c_board', 'c_write', 'c_puzzled', 'c_worried', 'c_machine', 'c_group', 'c_read2', 'c_switch', 'c_yawn'];
window.whenReady = () => Promise.all([
  ...PHOTOS.map(n => new Promise(ok => { const i = new Image(); i.onload = ok; i.onerror = ok; i.src = `media/${n}.jpg`; IMG[n] = i; })),
  ...CLIPS.map(n => new Promise(ok => { const v = document.createElement('video'); v.muted = true; v.preload = 'auto'; v.src = `media/${n}.webm`; v.onloadeddata = ok; v.onerror = ok; VID[n] = v; })),
]);

const T0 = b => BEATS[b - 1].start;
const W_ = (b, w, n) => T0(b) + at(b, w, n);
// [global start, media, {in, head, label, kb}]
const SHOTS = [
  [T0(1), 'stopwatch', { head: '10 MINUTES', kb: 1.35 }],
  [T0(2), 'laptop', { label: 'APRIL 2026' }],
  [W_(2, 'carnegie'), 'cmu', { label: 'CARNEGIE MELLON' }],
  [W_(2, 'oxford'), 'oxford', { label: 'OXFORD' }],
  [W_(2, 'mit'), 'mit', { label: 'MIT' }],
  [W_(2, 'ucla'), 'ucla', { label: 'UCLA' }],
  [W_(2, 'posted'), 'DOC', {}],
  [W_(2, 'short'), 'c_cpu', { in: 2.4, label: 'A SHORT BURST OF AI HELP' }],
  [W_(2, 'worse'), 'c_worried', { in: 3.0, head: 'WORSE AT THE NEXT TASK' }],
  [T0(3), 'c_class', { head: 'THE EXPERIMENT' }],
  [W_(3, 'hundreds'), 'c_alone', { label: 'HUNDREDS OF PEOPLE' }],
  [W_(3, 'fraction'), 'c_board', { label: 'FRACTION PROBLEMS' }],
  [W_(3, 'some'), 'robot', { label: 'SOME GOT AN AI ASSISTANT' }],
  [T0(4), 'c_door', { in: 2.0, head: 'AI: SWITCHED OFF' }],
  [W_(4, 'everyone'), 'c_write', { in: 3.0, head: 'ON THEIR OWN' }],
  [T0(5), 'CHART', {}],
  [W_(5, 'skipped'), 'paper', { label: 'SKIPPED QUESTIONS' }],
  [W_(5, 'as'), 'c_yawn', { in: 2.5, label: '…AS IF THEY STOPPED TRYING' }],
  [T0(6), 'bulb', { head: 'THE TWIST' }],
  [W_(6, 'people'), 'bulb', { head: 'ASKED FOR HINTS', mark: 'ok', markAt: W_(6, 'fine') }],
  [W_(6, 'ones'), 'answers', { head: 'ASKED FOR ANSWERS' }],
  [W_(6, 'fell'), 'c_puzzled', { mark: 'bad', label: 'FELL THE HARDEST' }],
  [T0(7), 'brain', { head: 'IS AI ROTTING OUR BRAINS?' }],
  [W_(7, 'not'), 'brain', { head: 'NOT SO FAST', kb: 1.0 }],
  [W_(7, 'pre'), 'lab', { stamp: true }],
  [W_(7, 'online'), 'exam', { stamp: true }],
  [T0(8), 'c_machine', { head: 'SMALLER. MORE USEFUL.', headAt: W_(8, 'smaller') }],
  [W_(8, 'tool'), 'c_switch', { label: "THE TOOL ISN'T THE PROBLEM" }],
  [W_(8, 'how'), 'c_cpu', { in: 3.8, head: 'HOW WE LEAN ON IT' }],
  [T0(9), 'c_group', {}],
  [W_(9, 'read'), 'c_read2', { head: 'READ IT TOGETHER' }],
  [W_(9, 'wait'), 'hourglass', { head: 'REPLICATION: PENDING' }],
].map((s, i, a) => ({ s: s[0], e: i + 1 < a.length ? a[i + 1][0] : END, m: s[1], o: s[2], i }));
const shotAt = t => SHOTS.find(s => t >= s.s && t < s.e) || SHOTS[SHOTS.length - 1];

window.prepare = async t => {
  const sh = shotAt(t);
  const v = VID[sh.m];
  if (!v) return;
  const want = Math.min((sh.o.in || 0) + (t - sh.s), v.duration - .05);
  if (Math.abs(v.currentTime - want) < 1e-3) return;
  await new Promise(ok => { v.onseeked = ok; v.currentTime = want; });
};

function cover(src, x, y, w, h, k, dir) {
  const sw = src.videoWidth || src.naturalWidth, shh = src.videoHeight || src.naturalHeight;
  if (!sw) return;
  const sc = Math.max(w / sw, h / shh) * k;
  const dw = sw * sc, dh = shh * sc;
  const px = (dw - w) * (dir > 0 ? .5 + .5 * (k - 1) / .2 : .5 - .5 * (k - 1) / .2);
  g.drawImage(src, x - clamp(px, 0, dw - w), y - (dh - h) / 2, dw, dh);
}
function tag(s, x, y, size, bg, fg, alignRight) {
  g.save(); g.font = `900 ${size}px Inter`; g.textBaseline = 'middle';
  const w = g.measureText(s).width, pad = size * .35;
  const fit = Math.min(1, (W - 80) / (w + 2 * pad));
  g.translate(x, y); g.scale(fit, fit);
  const x0 = alignRight ? -(w + 2 * pad) : 0;
  g.fillStyle = bg; g.fillRect(x0, -size * .7, w + 2 * pad, size * 1.4);
  g.fillStyle = fg; g.fillText(s, x0 + pad, size * .04);
  g.restore();
}
function doc(u) {
  g.fillStyle = '#e9e6df'; g.fillRect(FX, FY, FW, FH);
  const k = easeOut(u / .6);
  g.save(); g.translate(W / 2, FY + FH / 2 + (1 - k) * 200); g.rotate(-.02);
  g.fillStyle = 'rgba(0,0,0,.25)'; g.fillRect(-370, -320, 760, 680);
  g.fillStyle = '#fff'; g.fillRect(-380, -340, 760, 680);
  g.fillStyle = '#9a1c1c'; g.font = '800 26px Inter'; g.textAlign = 'left'; g.fillText('PREPRINT · APRIL 2026 · NOT PEER-REVIEWED', -330, -280);
  g.fillStyle = INK; g.font = '900 46px Inter';
  ['AI Assistance Reduces', 'Persistence and Hurts', 'Independent Performance'].forEach((l, i) => g.fillText(l, -330, -200 + i * 58));
  g.fillStyle = '#555'; g.font = '600 28px Inter'; g.fillText('Carnegie Mellon · Oxford · MIT · UCLA', -330, 2);
  g.fillStyle = '#d6d3cc'; for (let i = 0; i < 6; i++) g.fillRect(-330, 60 + i * 42, i % 3 === 2 ? 380 : 660, 16);
  g.restore();
  // highlighter sweep on "bold claim"
  const hk = ease((u - (at(2, 'bold') - at(2, 'posted'))) / .5);
  if (hk > 0) { g.save(); g.globalCompositeOperation = 'multiply'; g.fillStyle = Y; g.fillRect(W / 2 - 330, FY + FH / 2 - 225 + (1 - easeOut(clamp(u / .6))) * 200, 620 * hk, 58); g.restore(); }
}
function chart(u) {
  g.fillStyle = '#121219'; g.fillRect(FX, FY, FW, FH);
  const base = FY + FH - 140, maxH = 470, k = ease(u / 1.2), drop = ease((u - at(5, '20')) / .8);
  text('UNAIDED SOLVE RATE', W / 2, FY + 70, 40, '#aaa', { weight: 800 });
  [[330, '#3fb6ff', 'NO AI', 1], [750, Y, 'HAD AI', 1 - .2 * drop]].forEach(([x, col, lab, v]) => {
    const h = maxH * k * v; g.fillStyle = col; g.fillRect(x - 120, base - h, 240, h);
    text(lab, x, base + 60, 44, '#fff', { weight: 900 });
  });
  g.fillStyle = '#444'; g.fillRect(FX + 60, base, FW - 120, 4);
  if (drop > 0) text('≈ −20%', 750, base - maxH * .8 - 60, 80, Y, { weight: 900, alpha: drop });
  text('Illustrative; preprint reports ~20% lower', W / 2, FY + FH - 30, 26, '#777', { weight: 600 });
}
function mark(kind, k) {
  if (k <= 0) return;
  const s = back(clamp(k / .4)), x = FX + FW - 110, y = FY + 110;
  g.save(); g.translate(x, y); g.scale(s, s);
  g.fillStyle = kind === 'ok' ? '#21c25e' : '#e8283c'; g.beginPath(); g.arc(0, 0, 70, 0, 7); g.fill();
  g.strokeStyle = '#fff'; g.lineWidth = 16; g.lineCap = 'round'; g.beginPath();
  if (kind === 'ok') { g.moveTo(-30, 2); g.lineTo(-6, 26); g.lineTo(32, -22); } else { g.moveTo(-26, -26); g.lineTo(26, 26); g.moveTo(26, -26); g.lineTo(-26, 26); }
  g.stroke(); g.restore();
}

function draw(t) {
  const sh = shotAt(t), u = t - sh.s, len = sh.e - sh.s;
  const src = IMG[sh.m] || VID[sh.m];
  // blurred fill behind the frame
  g.fillStyle = INK; g.fillRect(0, 0, W, H);
  if (src) { g.save(); g.filter = 'blur(38px) brightness(.38) saturate(1.2)'; cover(src, -60, -60, W + 120, H + 120, 1, 1); g.restore(); }
  // the frame
  g.save(); g.beginPath(); g.rect(FX, FY, FW, FH); g.clip();
  if (sh.m === 'DOC') doc(u);
  else if (sh.m === 'CHART') chart(u);
  else if (src) {
    const kb = sh.o.kb || 1.12, k = lerp(1, kb, clamp(u / Math.max(len, 1)));
    if (VID[sh.m]) g.filter = 'contrast(1.08)';
    cover(src, FX, FY, FW, FH, k, sh.i % 2 ? 1 : -1); g.filter = 'none';
  }
  const vg = g.createRadialGradient(W / 2, FY + FH / 2, FH * .35, W / 2, FY + FH / 2, FH * .85);
  vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,.45)'); g.fillStyle = vg; g.fillRect(FX, FY, FW, FH);
  g.restore();
  g.strokeStyle = 'rgba(255,255,255,.9)'; g.lineWidth = 4; g.strokeRect(FX, FY, FW, FH);
  // a quick white flash on each cut
  alpha(1 - u / .12, () => { g.fillStyle = '#fff'; g.fillRect(FX, FY, FW, FH); });

  const o = sh.o;
  if (o.head && t >= (o.headAt || sh.s)) { const k = back(clamp((t - (o.headAt || sh.s)) / .3)); g.save(); g.translate(0, (1 - k) * 40); g.globalAlpha *= clamp(k); tag(o.head, FX, FY - 80, 66, Y, INK); g.restore(); }
  if (o.label) { const k = easeOut(u / .3); g.save(); g.translate((1 - k) * -300, 0); tag(o.label, FX + 30, FY + FH - 60, 44, INK, '#fff'); g.restore(); }
  if (o.mark) mark(o.mark, t - (o.markAt || sh.s));
  if (o.stamp) stampAndList(t);
  // source line, once the paper is on screen
  if (t >= W_(2, 'posted')) text('Source: arXiv 2604.04721 (preprint, April 2026)', W / 2, FY + FH + 50, 28, 'rgba(255,255,255,.65)', { weight: 600 });
  // fade out
  alpha((t - (END - 1.0)) / .9, () => { g.fillStyle = '#000'; g.fillRect(0, 0, W, H); });
}
function stampAndList(t) {
  const u = t - W_(7, 'pre');
  const k = clamp(u / .22), s = lerp(2.6, 1, easeOut(k));
  alpha(k * (1 - clamp((t - W_(7, 'peer')) / .4) * .6), () => {
    g.save(); g.translate(W / 2, FY + FH / 2 - 160); g.rotate(-.14); g.scale(s, s);
    g.strokeStyle = '#e8283c'; g.lineWidth = 14; g.strokeRect(-300, -80, 600, 160);
    text('PREPRINT', 0, 6, 110, '#e8283c', { weight: 900 }); g.restore();
  });
  const items = [['NOT PEER-REVIEWED', W_(7, 'peer') - .2], ['NOT REPLICATED', W_(7, 'replicated') - .1], ['ONLINE VOLUNTEERS', W_(7, 'online')], ['SIMPLE MATH', W_(7, 'simple')], ['MINUTES, NOT MONTHS', W_(7, 'measured')]];
  items.forEach(([lab, t0], i) => {
    const kk = easeOut((t - t0) / .3); if (kk <= 0) return;
    g.save(); g.translate((1 - kk) * -400, 0); g.globalAlpha *= kk;
    tag('✕ ' + lab, FX + 40, FY + 560 + i * 92, 46, i < 2 ? '#e8283c' : INK, '#fff'); g.restore();
  });
}

const SCENES = Array.from({ length: 9 }, () => (u, D, T) => draw(T));
const CAPTION = { size: 76, y: 1560, font: 'Inter', fg: '#ffffff', hi: Y, stroke: 18, strokeColor: '#000' };
