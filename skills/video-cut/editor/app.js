/* vcut — editor de cortes.
   No renderiza nada: edita el plan de cortes y lo guarda en project.json.
   La previsualizacion usa los proxies (o los originales si el navegador puede). */
(() => {
'use strict';

const $  = (id) => document.getElementById(id);
const el = (tag, cls, txt) => { const n = document.createElement(tag);
  if (cls) n.className = cls; if (txt != null) n.textContent = txt; return n; };

const PEAKS_PER_SEC = 40;
const CLIP_H = 118;
const MAX_VIDEOS = 8;

const S = {
  project: null, segs: [], groups: [], sources: {},
  timeline: [], total: 0, t: 0, curSeg: null,
  playing: false, rawPreview: null,
  selected: null, pps: 60, showOff: false,
  dirty: false, undo: [], redo: [],
  layoutW: 0, filter: '', idc: 0,
};

const WORDS   = Object.create(null);   // id -> [{w,s,e}]  (fuera del historial)
const VIDEOS  = Object.create(null);
const VIDORDER = [];
const WAVES   = Object.create(null);
const STRIPS  = Object.create(null);
const CLIPS   = new Map();

/* ------------------------------------------------------------ utilidades */

const clamp = (v, a, b) => v < a ? a : (v > b ? b : v);

function fmt(t, dec = 2) {
  t = Math.max(0, t || 0);
  const h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), s = t % 60;
  return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0') + ':' +
         s.toFixed(dec).padStart(dec ? 3 + dec : 2, '0');
}
function fmtShort(t) {
  t = Math.max(0, t || 0);
  const m = Math.floor(t / 60), s = Math.round(t % 60);
  return m + ':' + String(s).padStart(2, '0');
}

let toastTimer = 0;
function toast(msg, kind, action) {
  const box = $('toast');
  box.textContent = '';
  box.appendChild(el('span', null, msg));
  if (action) {
    const b = el('button', 'ghost', action.label);
    b.onclick = () => { action.fn(); hideToast(); };
    box.appendChild(b);
  }
  box.className = 'show' + (kind === 'bad' ? ' bad' : '');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(hideToast, action ? 7000 : 2600);
}
function hideToast() { $('toast').className = ''; }

/* ------------------------------------------------------------ historial */

function snapshot() {
  return { segs: S.segs.map(s => ({ ...s })), groups: S.groups.map(g => ({ ...g })) };
}
function pushUndo() {
  S.undo.push(snapshot());
  if (S.undo.length > 80) S.undo.shift();
  S.redo.length = 0;
  markDirty();
}
function restore(snap) {
  S.segs = snap.segs.map(s => ({ ...s }));
  S.groups = snap.groups.map(g => ({ ...g }));
  recompute(); renderAll();
}
function undo() {
  if (!S.undo.length) return toast('Nada que deshacer');
  S.redo.push(snapshot());
  restore(S.undo.pop());
  markDirty();
}
function redo() {
  if (!S.redo.length) return toast('Nada que rehacer');
  S.undo.push(snapshot());
  restore(S.redo.pop());
  markDirty();
}
function markDirty(v = true) {
  S.dirty = v;
  $('saveDot').className = 'dot' + (v ? ' dirty' : '');
  $('btnUndo').disabled = !S.undo.length;
  $('btnRedo').disabled = !S.redo.length;
}

/* ------------------------------------------------------------ modelo */

function recompute() {
  let t = 0;
  S.timeline = [];
  for (const s of S.segs) {
    s.dur = Math.max(0, s.out - s.in);
    if (s.enabled && s.dur > 0.01) { s.t = t; t += s.dur; S.timeline.push(s); }
    else s.t = null;
  }
  S.total = t;
  S.t = clamp(S.t, 0, S.total);
  if (!S.timeline.includes(S.curSeg)) S.curSeg = segAtTime(S.t);
}

function segAtTime(t) {
  const tl = S.timeline;
  if (!tl.length) return null;
  let lo = 0, hi = tl.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (tl[mid].t <= t) lo = mid; else hi = mid - 1;
  }
  return tl[lo];
}

function newId() {
  let id;
  do { id = 'm' + String(++S.idc).padStart(3, '0'); }
  while (S.segs.some(s => s.id === id));
  return id;
}

function groupOf(gid) { return S.groups.find(g => g.id === gid) || null; }

function detachFromGroups(id) {
  for (let i = S.groups.length - 1; i >= 0; i--) {
    const g = S.groups[i];
    if (!g.members.includes(id)) continue;
    g.members = g.members.filter(m => m !== id);
    if (g.chosen === id) g.chosen = g.members[g.members.length - 1] || null;
    if (g.members.length < 2) {
      for (const m of g.members) {
        const seg = S.segs.find(x => x.id === m);
        if (seg) { seg.group = null; seg.take_index = 0; seg.take_count = 0; }
      }
      S.groups.splice(i, 1);
    } else {
      g.members.forEach((m, k) => {
        const seg = S.segs.find(x => x.id === m);
        if (seg) { seg.take_index = k + 1; seg.take_count = g.members.length; }
      });
    }
  }
}

function setChosen(gid, id) {
  const g = groupOf(gid);
  if (!g) return;
  pushUndo();
  g.chosen = id;
  g.decided_by = 'editor';
  for (const m of g.members) {
    const seg = S.segs.find(x => x.id === m);
    if (!seg) continue;
    seg.enabled = (m === id);
    seg.reason = seg.enabled ? 'toma elegida a mano' : 'toma descartada';
  }
  recompute(); renderAll();
}

/* ------------------------------------------------------------ comandos */

function toggleSeg(id) {
  const seg = S.segs.find(s => s.id === id);
  if (!seg) return;
  pushUndo();
  const on = !seg.enabled;
  if (seg.group && on) {
    const g = groupOf(seg.group);
    if (g) {
      g.chosen = id; g.decided_by = 'editor';
      for (const m of g.members) {
        const o = S.segs.find(x => x.id === m);
        if (o) { o.enabled = (m === id); o.reason = o.enabled ? 'toma elegida a mano' : 'toma descartada'; }
      }
      recompute(); renderAll(); return;
    }
  }
  seg.enabled = on;
  seg.locked = true;
  seg.reason = on ? 'encendida a mano' : 'apagada a mano';
  if (seg.group && !on) { const g = groupOf(seg.group); if (g && g.chosen === id) g.chosen = null; }
  recompute(); renderAll();
}

function splitAt(seg, local) {
  local = clamp(local, seg.in + 0.05, seg.out - 0.05);
  if (!(local > seg.in && local < seg.out)) return toast('El cursor no está dentro del clip', 'bad');
  pushUndo();
  const words = WORDS[seg.id] || [];
  const aW = words.filter(w => w.s < local);
  const bW = words.filter(w => w.s >= local);
  const a = { ...seg, id: newId(), out: +local.toFixed(3), group: null, take_index: 0,
              take_count: 0, locked: true, reason: 'dividido a mano' };
  const b = { ...seg, id: newId(), in: +local.toFixed(3), group: null, take_index: 0,
              take_count: 0, locked: true, reason: 'dividido a mano' };
  WORDS[a.id] = aW; WORDS[b.id] = bW;
  a.text = aW.map(w => w.w).join(' ') || seg.text;
  b.text = bW.map(w => w.w).join(' ') || '…';
  detachFromGroups(seg.id);
  S.segs.splice(S.segs.indexOf(seg), 1, a, b);
  delete WORDS[seg.id];
  S.selected = b.id;
  recompute(); renderAll();
  toast('Clip dividido');
}

function splitAtPlayhead() {
  const seg = segAtTime(S.t);
  if (!seg) return;
  splitAt(seg, seg.in + (S.t - seg.t));
}

function trimToPlayhead(which) {
  const seg = segAtTime(S.t);
  if (!seg) return;
  const local = seg.in + (S.t - seg.t);
  pushUndo();
  if (which === 'in') seg.in = +clamp(local, 0, seg.out - 0.05).toFixed(3);
  else seg.out = +clamp(local, seg.in + 0.05, S.sources[seg.source].duration).toFixed(3);
  seg.locked = true;
  recompute(); renderAll();
  toast(which === 'in' ? 'Entrada en el cursor' : 'Salida en el cursor');
}

function trimToWord(segId, wordIdx, mode) {
  const seg = S.segs.find(s => s.id === segId);
  const w = (WORDS[segId] || [])[wordIdx];
  if (!seg || !w) return;
  if (mode === 'split') return splitAt(seg, w.s - 0.06);
  pushUndo();
  if (mode === 'in') seg.in = +clamp(w.s - 0.08, 0, seg.out - 0.05).toFixed(3);
  else seg.out = +clamp(w.e + 0.12, seg.in + 0.05, S.sources[seg.source].duration).toFixed(3);
  seg.locked = true;
  recompute(); renderAll();
}

function moveSeg(id, toIndex) {
  const from = S.segs.findIndex(s => s.id === id);
  if (from < 0) return;
  pushUndo();
  const [seg] = S.segs.splice(from, 1);
  if (from < toIndex) toIndex--;
  S.segs.splice(clamp(toIndex, 0, S.segs.length), 0, seg);
  recompute(); renderAll();
}

/* ------------------------------------------------------------ video */

function videoEl(sid) {
  let v = VIDEOS[sid];
  if (v) {
    const i = VIDORDER.indexOf(sid);
    if (i >= 0) { VIDORDER.splice(i, 1); VIDORDER.push(sid); }
    return v;
  }
  v = document.createElement('video');
  v.src = '/api/media/' + sid;
  v.preload = 'auto';
  v.playsInline = true;
  v.muted = true;
  v.addEventListener('error', () => toast('No se pudo cargar ' +
    (S.sources[sid] ? S.sources[sid].name : sid) +
    '. Generá proxies: vcut.py media --project …', 'bad'));
  $('videoWrap').appendChild(v);
  VIDEOS[sid] = v; VIDORDER.push(sid);
  while (VIDORDER.length > MAX_VIDEOS) {
    const old = VIDORDER.shift();
    if (old === (S.curSeg && S.curSeg.source)) { VIDORDER.push(old); break; }
    const ov = VIDEOS[old];
    if (ov) { ov.pause(); ov.removeAttribute('src'); ov.load(); ov.remove(); delete VIDEOS[old]; }
  }
  return v;
}

function setActive(sid) {
  for (const k in VIDEOS) {
    const v = VIDEOS[k];
    if (k === sid) { v.classList.add('active'); v.muted = false; }
    else { v.classList.remove('active'); v.muted = true; if (!v.paused) v.pause(); }
  }
  const src = S.sources[sid];
  $('badgeSrc').textContent = src ? src.name : '';
  $('stageEmpty').classList.toggle('hidden', !!sid);
}

function preloadNext(seg) {
  const i = S.timeline.indexOf(seg);
  const nxt = S.timeline[i + 1];
  if (!nxt || nxt.source === seg.source) return;
  const v = videoEl(nxt.source);
  if (Math.abs(v.currentTime - nxt.in) > 0.5) { try { v.currentTime = nxt.in; } catch (e) { /* aún sin metadata */ } }
}

function seek(t, keepPlaying) {
  S.rawPreview = null;
  $('badgeLive').classList.add('hidden');
  S.t = clamp(t, 0, S.total);
  const seg = segAtTime(S.t);
  S.curSeg = seg;
  if (!seg) { updateHUD(); return; }
  const v = videoEl(seg.source);
  setActive(seg.source);
  const local = clamp(seg.in + (S.t - seg.t), seg.in, seg.out);
  try { v.currentTime = local; } catch (e) { /* se aplicará al cargar metadata */ }
  preloadNext(seg);
  if (S.playing && keepPlaying !== false) v.play().catch(() => {});
  updateHUD();
}

function play() {
  if (!S.timeline.length) return toast('No hay clips activos', 'bad');
  if (S.t >= S.total - 0.03) S.t = 0;
  S.playing = true;
  $('btnPlay').textContent = '❚❚';
  seek(S.t, true);
  const seg = S.curSeg;
  if (seg) videoEl(seg.source).play().catch(() => {});
  requestAnimationFrame(tick);
}
function pause() {
  S.playing = false;
  S.rawPreview = null;
  $('badgeLive').classList.add('hidden');
  $('btnPlay').textContent = '▶';
  for (const k in VIDEOS) VIDEOS[k].pause();
}
function togglePlay() { S.playing ? pause() : play(); }

function previewRaw(sid, tin, tout) {
  pause();
  S.rawPreview = { sid, in: tin, out: tout };
  S.playing = true;
  $('btnPlay').textContent = '❚❚';
  $('badgeLive').classList.remove('hidden');
  const v = videoEl(sid);
  setActive(sid);
  try { v.currentTime = tin; } catch (e) { /* metadata aún no lista */ }
  v.play().catch(() => {});
  requestAnimationFrame(tick);
}

function tick() {
  if (!S.playing) return;

  if (S.rawPreview) {
    const v = VIDEOS[S.rawPreview.sid];
    if (!v || v.currentTime >= S.rawPreview.out - 0.02) { pause(); return; }
    requestAnimationFrame(tick);
    return;
  }

  const seg = S.curSeg;
  if (!seg) { pause(); return; }
  const v = VIDEOS[seg.source];
  if (!v) { pause(); return; }

  if (v.currentTime >= seg.out - 0.015 || v.ended) {
    const nxt = S.timeline[S.timeline.indexOf(seg) + 1];
    if (!nxt) { S.t = S.total; pause(); updateHUD(); return; }
    S.curSeg = nxt;
    S.t = nxt.t;
    const nv = videoEl(nxt.source);
    setActive(nxt.source);
    try { nv.currentTime = nxt.in; } catch (e) { /* se corrige en el siguiente frame */ }
    nv.play().catch(() => {});
    preloadNext(nxt);
  } else {
    S.t = seg.t + (v.currentTime - seg.in);
  }

  updateHUD();
  autoScroll();
  requestAnimationFrame(tick);
}

/* ------------------------------------------------------------ assets */

async function loadWave(sid) {
  try {
    const r = await fetch('/api/waveform/' + sid);
    if (!r.ok) return;
    WAVES[sid] = new Uint8Array(await r.arrayBuffer());
    invalidateClips(sid);
  } catch (e) { /* sin onda: el clip se dibuja liso */ }
}

function loadStrip(sid) {
  const meta = S.sources[sid] && S.sources[sid].filmstrip;
  if (!meta || !meta.cols) return;
  const img = new Image();
  img.onload = () => { STRIPS[sid] = { ...meta, img }; invalidateClips(sid); };
  img.onerror = () => { /* sin miniaturas: fondo liso */ };
  img.src = '/api/filmstrip/' + sid;
}

function invalidateClips(sid) {
  for (const [id, node] of CLIPS) {
    const seg = S.segs.find(s => s.id === id);
    if (seg && seg.source === sid) node.dataset.sig = '';
  }
  renderTrack();
}

/* ------------------------------------------------------------ timeline */

function layout() {
  let x = 0;
  const out = [];
  for (const s of S.segs) {
    const d = Math.max(0, s.out - s.in);
    if (!s.enabled && !S.showOff) { s._x = null; s._w = 0; continue; }
    const w = Math.max(2, d * S.pps);
    s._x = x; s._w = w;
    out.push(s);
    x += w;
  }
  S.layoutW = x;
  return out;
}

function playheadX() {
  const seg = S.curSeg || segAtTime(S.t);
  if (!seg || seg._x == null) return 0;
  return seg._x + (S.t - seg.t) * S.pps;
}

function drawClip(cv, seg) {
  const w = Math.round(seg._w), h = CLIP_H;
  if (w < 1) return;
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
  cv.style.width = w + 'px'; cv.style.height = h + 'px';
  const g = cv.getContext('2d');
  g.setTransform(dpr, 0, 0, dpr, 0, 0);

  const src = S.sources[seg.source] || {};
  const strip = STRIPS[seg.source];
  const dur = Math.max(0.001, seg.out - seg.in);
  const filmH = src.has_video && strip ? 74 : 0;
  const waveTop = filmH, waveH = h - filmH;

  if (filmH) {
    const scale = filmH / strip.th, dw = Math.max(6, strip.tw * scale);
    for (let x = 0; x < w; x += dw) {
      const t = seg.in + (x / w) * dur;
      const i = clamp(Math.floor(t / strip.interval), 0, strip.count - 1);
      g.drawImage(strip.img, (i % strip.cols) * strip.tw,
        Math.floor(i / strip.cols) * strip.th, strip.tw, strip.th,
        x, 0, Math.min(dw, w - x), filmH);
    }
  } else {
    g.fillStyle = '#1b2231'; g.fillRect(0, 0, w, waveTop || 0);
  }

  g.fillStyle = seg.enabled ? '#0e1420' : '#12141c';
  g.fillRect(0, waveTop, w, waveH);
  const peaks = WAVES[seg.source];
  if (peaks && peaks.length) {
    const mid = waveTop + waveH / 2, amp = waveH / 2 - 3;
    g.fillStyle = seg.enabled ? '#6ea8ff' : '#5c6884';
    for (let x = 0; x < w; x++) {
      const t0 = seg.in + (x / w) * dur, t1 = seg.in + ((x + 1) / w) * dur;
      let i0 = Math.floor(t0 * PEAKS_PER_SEC);
      const i1 = Math.max(i0 + 1, Math.ceil(t1 * PEAKS_PER_SEC));
      let m = 0;
      for (; i0 < i1 && i0 < peaks.length; i0++) if (peaks[i0] > m) m = peaks[i0];
      const a = Math.max(0.5, (m / 255) * amp);
      g.fillRect(x, mid - a, 1, a * 2);
    }
  }
}

function clipNode(seg) {
  let node = CLIPS.get(seg.id);
  if (!node) {
    node = el('div', 'clip');
    node.dataset.id = seg.id;
    node.appendChild(el('canvas'));
    node.appendChild(el('div', 'clip-label'));
    const take = el('div', 'clip-take');
    node.appendChild(take);
    node.appendChild(el('div', 'handle l'));
    node.appendChild(el('div', 'handle r'));
    CLIPS.set(seg.id, node);
    $('track').appendChild(node);
  }
  return node;
}

function renderTrack() {
  const items = layout();
  const track = $('track'), scroll = $('tlScroll');
  $('tlInner').style.width = Math.max(S.layoutW + 60, scroll.clientWidth) + 'px';
  track.style.width = S.layoutW + 'px';

  const lo = scroll.scrollLeft - 500, hi = scroll.scrollLeft + scroll.clientWidth + 500;
  const alive = new Set();

  for (const seg of items) {
    if (seg._x + seg._w < lo || seg._x > hi) continue;
    alive.add(seg.id);
    const node = clipNode(seg);
    node.style.transform = 'translateX(' + seg._x + 'px)';
    node.style.width = seg._w + 'px';
    node.className = 'clip' + (seg.enabled ? '' : ' off') + (S.selected === seg.id ? ' sel' : '');
    const sig = [Math.round(seg._w), seg.in, seg.out, seg.enabled, seg.source].join('|');
    if (node.dataset.sig !== sig) {
      node.dataset.sig = sig;
      drawClip(node.firstChild, seg);
    }
    const label = node.children[1];
    label.textContent = seg._w > 46 ? (seg.text || '').slice(0, 120) : '';
    const take = node.children[2];
    if (seg.take_count > 1 && seg._w > 60) {
      take.textContent = 'toma ' + seg.take_index + '/' + seg.take_count;
      take.style.display = '';
    } else take.style.display = 'none';
  }

  for (const [id, node] of CLIPS) {
    if (!alive.has(id)) { node.remove(); CLIPS.delete(id); }
  }
  drawRuler();
  $('playhead').style.transform = 'translateX(' + playheadX() + 'px)';
}

function drawRuler() {
  const cv = $('ruler'), scroll = $('tlScroll');
  const w = scroll.clientWidth, h = 22;
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
  cv.style.width = w + 'px'; cv.style.height = h + 'px';
  const g = cv.getContext('2d');
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.fillStyle = '#171b25'; g.fillRect(0, 0, w, h);
  g.strokeStyle = '#272d3c'; g.beginPath(); g.moveTo(0, h - .5); g.lineTo(w, h - .5); g.stroke();

  const steps = [0.1, 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600];
  const step = steps.find(s => s * S.pps >= 64) || 900;
  const off = scroll.scrollLeft;
  const t0 = Math.floor(off / S.pps / step) * step;
  g.fillStyle = '#68718c'; g.font = '10px ui-monospace,monospace';
  g.strokeStyle = '#333b4f';
  for (let t = t0; t * S.pps < off + w + 100; t += step) {
    const x = Math.round(t * S.pps - off) + .5;
    if (x < -40) continue;
    g.beginPath(); g.moveTo(x, 12); g.lineTo(x, h); g.stroke();
    g.fillText(step < 1 ? t.toFixed(1) + 's' : fmtShort(t), x + 4, 10);
  }
}

function autoScroll() {
  const scroll = $('tlScroll'), x = playheadX();
  const left = scroll.scrollLeft, w = scroll.clientWidth;
  if (x < left + 40 || x > left + w - 90) scroll.scrollLeft = Math.max(0, x - w * 0.35);
}

/* ------------------------------------------------------------ HUD */

function updateHUD() {
  $('tCur').textContent = fmt(S.t);
  $('playhead').style.transform = 'translateX(' + playheadX() + 'px)';
  highlightWord();
}

function updateStats() {
  const st = S.project.stats || {};
  $('tTotal').textContent = fmt(S.total);
  $('projStats').textContent =
    S.timeline.length + ' clips · ' + fmt(S.total, 0) + ' de ' +
    fmt(st.raw_duration || 0, 0) + ' bruto · ' +
    (st.raw_duration ? Math.round(100 * (1 - S.total / st.raw_duration)) : 0) + '% recortado';
  $('tlInfo').textContent = S.segs.length + ' segmentos · ' +
    S.timeline.length + ' activos · ' + S.groups.length + ' grupos de tomas';
  $('nGroups').textContent = '(' + S.groups.length + ')';
}

let lastWordKey = '';
function highlightWord() {
  const seg = S.curSeg;
  if (!seg) return;
  const local = seg.in + (S.t - seg.t);
  const ws = WORDS[seg.id] || [];
  let idx = -1;
  for (let i = 0; i < ws.length; i++) if (ws[i].s <= local && local <= ws[i].e + 0.05) { idx = i; break; }
  const key = seg.id + ':' + idx;
  if (key === lastWordKey) return;
  lastWordKey = key;
  const prev = document.querySelector('.w.playing');
  if (prev) prev.classList.remove('playing');
  if (idx < 0) return;
  const node = document.querySelector('.w[data-s="' + seg.id + '"][data-i="' + idx + '"]');
  if (node) node.classList.add('playing');
}

/* ------------------------------------------------------------ paneles */

function renderTranscript() {
  const box = $('tab-transcript');
  box.textContent = '';
  const frag = document.createDocumentFragment();
  const q = S.filter.trim().toLowerCase();
  let lastSrc = null, shown = 0;

  for (const seg of S.segs) {
    if (q && !(seg.text || '').toLowerCase().includes(q)) continue;
    shown++;
    if (seg.source !== lastSrc) {
      lastSrc = seg.source;
      const h = el('div', 'group-h');
      h.appendChild(el('b', null, (S.sources[seg.source] || {}).name || seg.source));
      frag.appendChild(h);
    }
    const row = el('div', 'utt' + (seg.enabled ? '' : ' off') + (S.selected === seg.id ? ' sel' : ''));
    row.dataset.id = seg.id;

    const tog = el('button', 'utt-tog' + (seg.enabled ? ' on' : ''), seg.enabled ? '✓' : '');
    tog.dataset.act = 'toggle';
    tog.title = 'Encender / apagar (D)';
    row.appendChild(tog);

    const right = el('div');
    const meta = el('div', 'utt-meta');
    meta.appendChild(el('span', 'pill src', fmt(seg.in, 1)));
    meta.appendChild(el('span', 'pill', (seg.out - seg.in).toFixed(1) + 's'));
    if (seg.take_count > 1) meta.appendChild(el('span', 'pill take', 'toma ' + seg.take_index + '/' + seg.take_count));
    if (seg.kind === 'filler') meta.appendChild(el('span', 'pill filler', 'muletilla'));
    right.appendChild(meta);

    const txt = el('div', 'utt-text');
    const ws = WORDS[seg.id] || [];
    if (ws.length) {
      ws.forEach((w, i) => {
        const sp = el('span', 'w', w.w);
        sp.dataset.s = seg.id; sp.dataset.i = i;
        txt.appendChild(sp);
        txt.appendChild(document.createTextNode(' '));
      });
    } else txt.textContent = seg.text || '';
    right.appendChild(txt);
    row.appendChild(right);
    frag.appendChild(row);
  }

  if (!shown) frag.appendChild(el('div', 'hint', q ? 'Nada coincide con la búsqueda.' : 'Sin segmentos.'));
  box.appendChild(frag);
}

function renderTakes() {
  const box = $('tab-takes');
  box.textContent = '';
  if (!S.groups.length) {
    box.appendChild(el('div', 'hint', 'No se detectaron tomas repetidas. Si sabés que las hay, ' +
      'bajá el umbral: vcut.py analyze --sim-ratio 0.55'));
    return;
  }
  const frag = document.createDocumentFragment();
  for (const g of S.groups) {
    const wrap = el('div', 'group');
    const head = el('div', 'group-h');
    head.appendChild(el('b', null, g.id));
    head.appendChild(el('span', null, g.members.length + ' tomas · elegida por ' + (g.decided_by || 'auto')));
    wrap.appendChild(head);

    g.members.forEach((mid, k) => {
      const seg = S.segs.find(s => s.id === mid);
      if (!seg) return;
      const row = el('div', 'take' + (g.chosen === mid ? ' chosen' : ''));
      const radio = el('input', 'take-radio');
      radio.type = 'radio'; radio.name = 'grp_' + g.id; radio.checked = g.chosen === mid;
      radio.dataset.gid = g.id; radio.dataset.mid = mid;
      row.appendChild(radio);

      const mid2 = el('div');
      const num = el('div', 'take-num',
        'toma ' + (k + 1) + ' · ' + (S.sources[seg.source] || {}).name + ' @ ' + fmt(seg.in, 1) +
        ' · ' + (seg.out - seg.in).toFixed(1) + 's · conf ' + (seg.conf || 0).toFixed(2));
      mid2.appendChild(num);
      mid2.appendChild(el('div', 'take-txt', seg.text || ''));
      row.appendChild(mid2);

      const acts = el('div', 'take-actions');
      const listen = el('button', 'ghost icon', '▶');
      listen.title = 'Escuchar solo esta toma';
      listen.dataset.listen = mid;
      acts.appendChild(listen);
      row.appendChild(acts);
      wrap.appendChild(row);
    });
    frag.appendChild(wrap);
  }
  box.appendChild(frag);
}

function renderClipPanel() {
  const box = $('tab-clip');
  box.textContent = '';
  const seg = S.segs.find(s => s.id === S.selected);
  if (!seg) { box.appendChild(el('div', 'hint', 'Seleccioná un clip en el timeline o en la transcripción.')); return; }
  const src = S.sources[seg.source] || {};

  const add = (label, value) => {
    const f = el('div', 'field');
    f.appendChild(el('label', null, label));
    f.appendChild(el('span', null, value));
    box.appendChild(f);
  };
  add('id', seg.id);
  add('archivo', src.name || seg.source);
  add('duración', (seg.out - seg.in).toFixed(3) + ' s');
  add('motivo', seg.reason || '—');
  if (seg.take_count > 1) add('toma', seg.take_index + ' de ' + seg.take_count + ' (' + seg.group + ')');

  for (const key of ['in', 'out']) {
    const f = el('div', 'field');
    f.appendChild(el('label', null, key === 'in' ? 'entrada (s)' : 'salida (s)'));
    const inp = el('input');
    inp.type = 'number'; inp.step = '0.01'; inp.value = seg[key].toFixed(3);
    inp.onchange = () => {
      pushUndo();
      const v = parseFloat(inp.value);
      if (!isFinite(v)) return;
      if (key === 'in') seg.in = +clamp(v, 0, seg.out - 0.05).toFixed(3);
      else seg.out = +clamp(v, seg.in + 0.05, src.duration || v).toFixed(3);
      seg.locked = true;
      recompute(); renderAll();
    };
    f.appendChild(inp);
    box.appendChild(f);
  }

  const acts = el('div', 'field');
  const bTog = el('button', null, seg.enabled ? 'Apagar clip' : 'Encender clip');
  bTog.onclick = () => toggleSeg(seg.id);
  const bPrev = el('button', 'ghost', '▶ escuchar');
  bPrev.onclick = () => previewRaw(seg.source, seg.in, seg.out);
  acts.appendChild(bTog); acts.appendChild(bPrev);
  box.appendChild(acts);

  const t = el('div', 'hint');
  t.appendChild(el('b', null, 'Texto: '));
  t.appendChild(document.createTextNode(seg.text || '—'));
  box.appendChild(t);
}

function renderAll() {
  updateStats();
  renderTrack();
  renderTranscript();
  renderTakes();
  renderClipPanel();
  markDirty(S.dirty);
}

/* ------------------------------------------------------------ interacción timeline */

function timeFromX(x) {
  // x en px dentro del track -> tiempo de linea de tiempo
  for (const seg of S.segs) {
    if (seg._x == null) continue;
    if (x >= seg._x && x <= seg._x + seg._w) {
      if (!seg.enabled) return seg.t != null ? seg.t : S.t;
      return seg.t + (x - seg._x) / S.pps;
    }
  }
  return S.total;
}

function setupTimeline() {
  const scroll = $('tlScroll'), track = $('track');
  let drag = null;

  scroll.addEventListener('scroll', () => renderTrack(), { passive: true });

  track.addEventListener('pointerdown', (ev) => {
    const clip = ev.target.closest('.clip');
    if (!clip) return;
    const seg = S.segs.find(s => s.id === clip.dataset.id);
    if (!seg) return;
    S.selected = seg.id;
    const isHandle = ev.target.classList.contains('handle');
    const side = isHandle ? (ev.target.classList.contains('l') ? 'l' : 'r') : null;
    track.setPointerCapture(ev.pointerId);
    drag = {
      seg, side, startX: ev.clientX, moved: false,
      in0: seg.in, out0: seg.out, x0: seg._x,
    };
    if (!isHandle) {
      const x = ev.clientX - track.getBoundingClientRect().left;
      seek(timeFromX(x));
    }
    renderTrack(); renderTranscript(); renderClipPanel();
    ev.preventDefault();
  });

  track.addEventListener('pointermove', (ev) => {
    if (!drag) return;
    const dx = ev.clientX - drag.startX;
    if (!drag.moved && Math.abs(dx) < 3) return;
    drag.moved = true;
    const seg = drag.seg, src = S.sources[seg.source] || { duration: 1e9 };
    const dt = dx / S.pps;

    if (drag.side === 'l') {
      seg.in = +clamp(drag.in0 + dt, 0, seg.out - 0.05).toFixed(3);
    } else if (drag.side === 'r') {
      seg.out = +clamp(drag.out0 + dt, seg.in + 0.05, src.duration).toFixed(3);
    } else {
      // reordenar: marca dónde caería
      const x = ev.clientX - track.getBoundingClientRect().left;
      let mark = $('dropMark');
      if (!mark) { mark = el('div', 'drop-mark'); mark.id = 'dropMark'; $('tlInner').appendChild(mark); }
      const idx = dropIndex(x);
      const target = S.segs.filter(s => s._x != null)[idx];
      mark.style.transform = 'translateX(' + (target ? target._x : S.layoutW) + 'px)';
      clipNode(seg).classList.add('dragging');
      return;
    }
    recompute();
    clipNode(seg).dataset.sig = '';
    renderTrack();
  });

  const endDrag = (ev) => {
    if (!drag) return;
    const seg = drag.seg;
    const mark = $('dropMark');
    if (mark) mark.remove();
    clipNode(seg).classList.remove('dragging');

    if (drag.moved && drag.side) {
      const changed = seg.in !== drag.in0 || seg.out !== drag.out0;
      if (changed) {
        const cur = { in: seg.in, out: seg.out };
        seg.in = drag.in0; seg.out = drag.out0;
        pushUndo();
        seg.in = cur.in; seg.out = cur.out;
        seg.locked = true;
      }
    } else if (drag.moved && !drag.side) {
      const x = ev.clientX - $('track').getBoundingClientRect().left;
      const visible = S.segs.filter(s => s._x != null);
      const idx = dropIndex(x);
      const targetSeg = visible[idx];
      const globalIdx = targetSeg ? S.segs.indexOf(targetSeg) : S.segs.length;
      if (globalIdx !== S.segs.indexOf(seg)) moveSeg(seg.id, globalIdx);
    }
    drag = null;
    recompute(); renderAll();
  };
  track.addEventListener('pointerup', endDrag);
  track.addEventListener('pointercancel', endDrag);

  track.addEventListener('dblclick', (ev) => {
    const clip = ev.target.closest('.clip');
    if (clip) toggleSeg(clip.dataset.id);
  });

  track.addEventListener('contextmenu', (ev) => {
    const clip = ev.target.closest('.clip');
    if (!clip) return;
    ev.preventDefault();
    const seg = S.segs.find(s => s.id === clip.dataset.id);
    const x = ev.clientX - $('track').getBoundingClientRect().left;
    openMenu(ev.clientX, ev.clientY, [
      { label: seg.enabled ? 'Apagar clip' : 'Encender clip', fn: () => toggleSeg(seg.id) },
      { label: 'Dividir aquí', fn: () => splitAt(seg, seg.in + (x - seg._x) / S.pps) },
      { label: '▶ Escuchar clip', fn: () => previewRaw(seg.source, seg.in, seg.out) },
      { sep: true },
      { label: 'Entrada en el cursor', fn: () => trimToPlayhead('in') },
      { label: 'Salida en el cursor', fn: () => trimToPlayhead('out') },
    ]);
  });

  // Clic en la regla o zona vacía: mover el cursor.
  $('tlInner').addEventListener('pointerdown', (ev) => {
    if (ev.target.closest('.clip')) return;
    const x = ev.clientX - $('track').getBoundingClientRect().left;
    seek(timeFromX(Math.max(0, x)));
  });

  scroll.addEventListener('wheel', (ev) => {
    if (!ev.ctrlKey) return;
    ev.preventDefault();
    const rect = scroll.getBoundingClientRect();
    const anchorX = ev.clientX - rect.left + scroll.scrollLeft;
    const tAnchor = anchorX / S.pps;
    setZoom(S.pps * (ev.deltaY < 0 ? 1.2 : 1 / 1.2));
    scroll.scrollLeft = tAnchor * S.pps - (ev.clientX - rect.left);
  }, { passive: false });
}

function dropIndex(x) {
  const visible = S.segs.filter(s => s._x != null);
  for (let i = 0; i < visible.length; i++) {
    if (x < visible[i]._x + visible[i]._w / 2) return i;
  }
  return visible.length;
}

function setZoom(pps) {
  S.pps = clamp(pps, 2, 600);
  $('zoom').value = Math.round(S.pps);
  renderTrack();
}

/* ------------------------------------------------------------ menú contextual */

function openMenu(x, y, items) {
  closeMenu();
  const m = el('div');
  m.id = 'menu';
  for (const it of items) {
    if (it.sep) { m.appendChild(el('div', 'sep')); continue; }
    const b = el('button', null, it.label);
    b.onclick = () => { closeMenu(); it.fn(); };
    m.appendChild(b);
  }
  document.body.appendChild(m);
  const r = m.getBoundingClientRect();
  m.style.left = Math.min(x, window.innerWidth - r.width - 8) + 'px';
  m.style.top = Math.min(y, window.innerHeight - r.height - 8) + 'px';
  setTimeout(() => document.addEventListener('pointerdown', closeMenu, { once: true }), 0);
}
function closeMenu() { const m = $('menu'); if (m) m.remove(); }

/* ------------------------------------------------------------ panel eventos */

function setupPanels() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.onclick = () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      ['transcript', 'takes', 'clip', 'help'].forEach(name => {
        $('tab-' + name).classList.toggle('hidden', name !== tab.dataset.tab);
      });
    };
  });

  $('search').oninput = (ev) => { S.filter = ev.target.value; renderTranscript(); };

  $('tab-transcript').addEventListener('click', (ev) => {
    const tog = ev.target.closest('[data-act="toggle"]');
    if (tog) { toggleSeg(tog.closest('.utt').dataset.id); return; }
    const word = ev.target.closest('.w');
    if (word) {
      const seg = S.segs.find(s => s.id === word.dataset.s);
      const w = (WORDS[word.dataset.s] || [])[+word.dataset.i];
      S.selected = seg.id;
      if (seg && w && seg.enabled) seek(seg.t + (w.s - seg.in));
      else if (seg && w) previewRaw(seg.source, Math.max(seg.in, w.s - 0.15), seg.out);
      renderTrack(); renderTranscript(); renderClipPanel();
      return;
    }
    const row = ev.target.closest('.utt');
    if (row) {
      const seg = S.segs.find(s => s.id === row.dataset.id);
      S.selected = row.dataset.id;
      if (seg && seg.enabled) seek(seg.t + 0.01);
      renderTrack(); renderTranscript(); renderClipPanel();
      scrollClipIntoView();
    }
  });

  $('tab-transcript').addEventListener('contextmenu', (ev) => {
    const word = ev.target.closest('.w');
    if (!word) return;
    ev.preventDefault();
    const segId = word.dataset.s, i = +word.dataset.i;
    openMenu(ev.clientX, ev.clientY, [
      { label: 'Empezar el clip aquí', fn: () => trimToWord(segId, i, 'in') },
      { label: 'Terminar el clip aquí', fn: () => trimToWord(segId, i, 'out') },
      { label: 'Dividir aquí', fn: () => trimToWord(segId, i, 'split') },
    ]);
  });

  $('tab-takes').addEventListener('click', (ev) => {
    const radio = ev.target.closest('.take-radio');
    if (radio) { setChosen(radio.dataset.gid, radio.dataset.mid); return; }
    const listen = ev.target.closest('[data-listen]');
    if (listen) {
      const seg = S.segs.find(s => s.id === listen.dataset.listen);
      if (seg) previewRaw(seg.source, seg.in, seg.out);
    }
  });
}

function scrollClipIntoView() {
  const seg = S.segs.find(s => s.id === S.selected);
  if (!seg || seg._x == null) return;
  const scroll = $('tlScroll');
  if (seg._x < scroll.scrollLeft || seg._x + seg._w > scroll.scrollLeft + scroll.clientWidth) {
    scroll.scrollLeft = Math.max(0, seg._x - 80);
  }
}

/* ------------------------------------------------------------ guardar / exportar */

function payload() {
  return {
    name: S.project.name,
    segments: S.segs.map(s => {
      const o = { ...s, words: WORDS[s.id] || [] };
      delete o._x; delete o._w;
      return o;
    }),
    groups: S.groups,
  };
}

async function save() {
  try {
    const r = await fetch('/api/project', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload()),
    });
    const data = await r.json();
    if (!r.ok || !data.ok) throw new Error(data.error || ('HTTP ' + r.status));
    S.project.stats = data.stats;
    markDirty(false);
    updateStats();
    toast('Guardado');
  } catch (e) {
    toast('No se pudo guardar: ' + e.message, 'bad');
  }
}

async function doExport() {
  const fmt2 = $('exportFmt').value;
  if (S.dirty) await save();
  try {
    const r = await fetch('/api/export', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ format: fmt2 }),
    });
    const data = await r.json();
    if (!data.ok) throw new Error(data.error || 'error');
    toast('Exportado: ' + data.path, null, {
      label: 'abrir carpeta',
      fn: () => fetch('/api/reveal', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: data.path }),
      }),
    });
  } catch (e) {
    toast('Falló la exportación: ' + e.message, 'bad');
  }
}

/* ------------------------------------------------------------ teclado */

function setupKeys() {
  document.addEventListener('keydown', (ev) => {
    const tag = (ev.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') {
      if (ev.key === 'Escape') ev.target.blur();
      return;
    }
    const frame = 1 / (S.project.sequence.fps || 30);
    const mod = ev.ctrlKey || ev.metaKey;

    if (mod && ev.key.toLowerCase() === 's') { ev.preventDefault(); save(); return; }
    if (mod && ev.key.toLowerCase() === 'z') { ev.preventDefault(); ev.shiftKey ? redo() : undo(); return; }
    if (mod && ev.key.toLowerCase() === 'y') { ev.preventDefault(); redo(); return; }
    if (mod) return;

    switch (ev.key) {
      case ' ': ev.preventDefault(); togglePlay(); break;
      case 'ArrowLeft': ev.preventDefault(); pause(); seek(S.t - (ev.shiftKey ? 1 : frame)); break;
      case 'ArrowRight': ev.preventDefault(); pause(); seek(S.t + (ev.shiftKey ? 1 : frame)); break;
      case 'Home': ev.preventDefault(); seek(0); break;
      case 'End': ev.preventDefault(); seek(S.total); break;
      case ',': gotoClip(-1); break;
      case '.': gotoClip(1); break;
      case 's': case 'S': splitAtPlayhead(); break;
      case 'd': case 'D': case 'Delete': case 'Backspace':
        ev.preventDefault();
        if (S.selected) toggleSeg(S.selected);
        else { const seg = segAtTime(S.t); if (seg) toggleSeg(seg.id); }
        break;
      case '[': trimToPlayhead('in'); break;
      case ']': trimToPlayhead('out'); break;
      case '+': case '=': setZoom(S.pps * 1.25); break;
      case '-': case '_': setZoom(S.pps / 1.25); break;
      case 'Escape': closeMenu(); break;
      default: break;
    }
  });
}

function gotoClip(dir) {
  const cur = segAtTime(S.t);
  const i = S.timeline.indexOf(cur);
  const next = S.timeline[clamp(i + dir, 0, S.timeline.length - 1)];
  if (next) { S.selected = next.id; seek(next.t + 0.005); renderAll(); scrollClipIntoView(); }
}

/* ------------------------------------------------------------ arranque */

async function boot() {
  let project;
  try {
    const r = await fetch('/api/project');
    project = await r.json();
    if (!r.ok) throw new Error(project.error || 'no se pudo leer el proyecto');
  } catch (e) {
    $('loading').textContent = 'Error cargando el proyecto: ' + e.message;
    return;
  }

  S.project = project;
  S.groups = project.groups || [];
  for (const src of project.sources) S.sources[src.id] = src;
  S.segs = (project.segments || []).map(s => {
    WORDS[s.id] = s.words || [];
    const o = { ...s };
    delete o.words;
    return o;
  });
  if (!S.segs.length) {
    $('loading').textContent = 'El proyecto no tiene segmentos. Corré: vcut.py analyze --project …';
    return;
  }

  $('projName').textContent = project.name;
  document.title = project.name + ' — vcut';
  recompute();

  for (const src of project.sources) {
    if (src.has_audio) loadWave(src.id);
    if (src.filmstrip) loadStrip(src.id);
  }

  setupTimeline();
  setupPanels();
  setupKeys();

  $('btnPlay').onclick = togglePlay;
  $('btnStart').onclick = () => { pause(); seek(0); };
  $('btnEnd').onclick = () => { pause(); seek(S.total); };
  $('btnPrevClip').onclick = () => gotoClip(-1);
  $('btnNextClip').onclick = () => gotoClip(1);
  $('btnSave').onclick = save;
  $('btnExport').onclick = doExport;
  $('btnUndo').onclick = undo;
  $('btnRedo').onclick = redo;
  $('zoom').oninput = (ev) => setZoom(+ev.target.value);
  $('showOff').onchange = (ev) => { S.showOff = ev.target.checked; renderTrack(); };
  window.addEventListener('resize', () => renderTrack());
  window.addEventListener('beforeunload', (ev) => {
    if (S.dirty) { ev.preventDefault(); ev.returnValue = ''; }
  });
  setInterval(() => { if (S.dirty) save(); }, 90000);

  $('loading').classList.add('hidden');
  $('app').classList.remove('hidden');
  setZoom(S.pps);
  renderAll();
  seek(0);
  markDirty(false);
}

boot();
})();
