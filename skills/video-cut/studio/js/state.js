/* Modelo del studio. Dos capas, un solo estado:
     S.project  cortes (project.json)   -> que trozo de que archivo y en que orden
     S.tl       capa creativa (timeline.json) -> texto, zoom, transiciones, audio
   `resolve()` es el espejo de studio.resolve() en Python. Si las dos no
   calculan lo mismo, el preview y el render dejan de coincidir. */
window.ST = window.ST || {};

ST.S = {
  project: null, tl: null, cat: null,
  clips: [], items: [], trans: [], total: 0,
  t: 0, playing: false, sel: null,
  pps: 70, dirty: false, undo: [], redo: [],
  mode: 'select', guides: false, safe: false, tiktokUi: false, audio: true, snap: true,
  previewHQ: true,
  sources: {},
};

ST.state = (() => {
  'use strict';
  const S = ST.S;
  const clamp = (v, a, b) => (v < a ? a : (v > b ? b : v));

  /* ---------------------------------------------------------------- carga */

  async function boot(msg) {
    const say = (t) => { const n = document.getElementById('bootMsg'); if (n) n.textContent = t; };
    say(msg || 'Cargando proyecto…');
    const [pj, tlr, cat] = await Promise.all([
      fetch('/api/project').then((r) => r.json()),
      fetch('/api/timeline').then((r) => r.json()),
      fetch('/api/catalog').then((r) => r.json()),
    ]);
    S.project = pj;
    S.tl = tlr.timeline;
    S.cat = cat;
    S.sources = {};
    for (const s of pj.sources) S.sources[s.id] = s;
    ST.text.setAnims(cat.anims);
    say('Cargando tipografías…');
    await ST.text.preload(S.tl);
    resolve();
    return tlr.warnings || [];
  }

  /* ------------------------------------------------------------- resolver */

  function clipCfg(segId) {
    const raw = (S.tl.clips || {})[segId] || {};
    return Object.assign({
      speed: 1, volume: 0, zoom: null, look: null, flip: false,
      fit: null, mute: false,
    }, raw);
  }

  function clipSlot(segId) {
    S.tl.clips = S.tl.clips || {};
    if (!S.tl.clips[segId]) S.tl.clips[segId] = {};
    return S.tl.clips[segId];
  }

  function zoomKfs(cfg) {
    const z = cfg && cfg.zoom;
    if (!z || !z.kf) return [];
    return z.kf.slice().sort((a, b) => (+a.t || 0) - (+b.t || 0));
  }

  function zoomFlat(kfs) {
    if (!kfs.length) return true;
    return !kfs.some((k) => Math.abs((+k.scale || 1) - 1) > 0.002 ||
                            Math.abs(+k.x || 0) > 0.002 || Math.abs(+k.y || 0) > 0.002);
  }

  function resolve() {
    const clips = [];
    let t = 0;
    for (const seg of S.project.segments) {
      if (!seg.enabled) continue;
      const srcDur = Math.max(0, seg.out - seg.in);
      if (srcDur <= 0.01) continue;
      const cfg = clipCfg(seg.id);
      const spd = clamp(+cfg.speed || 1, 0.25, 4);
      const dur = srcDur / spd;
      const gap = Math.max(0, +cfg.gap_before || 0);
      const start = cfg.start == null ? t + gap : Math.max(0, +cfg.start || 0);
      const lane = track(cfg.track || '_video');
      clips.push({
        seg: seg.id, source: seg.source, in: seg.in, out: seg.out,
        srcDur, speed: spd, dur, gap_before: gap, t0: start, t1: start + dur,
        track: lane ? lane.id : '_video', z: lane ? (+lane.z || 0) : 0,
        hidden: !!(lane && lane.hidden),
        text: seg.text || '', cfg, index: clips.length,
      });
      t = Math.max(t, start + dur);
    }
    S.clips = clips;
    S.total = t;
    const bySeg = {};
    for (const c of clips) bySeg[c.seg] = c;

    const trans = [];
    for (const tr of S.tl.transitions || []) {
      const c = bySeg[tr.at_seg];
      if (!c || c.index === 0) continue;
      const prev = clips[c.index - 1];
      if (c.hidden || prev.hidden || c.track !== prev.track || Math.abs(prev.t1 - c.t0) > 0.03) continue;
      const dur = Math.min(+tr.dur || 0.3, prev.dur * 0.9, c.dur * 0.9);
      if (dur <= 0.02) continue;
      trans.push({
        id: tr.id, at_seg: c.seg, type: tr.type || 'flash', t: c.t0, dur,
        t0: Math.max(0, c.t0 - dur / 2), t1: Math.min(t, c.t0 + dur / 2),
        strength: tr.strength != null ? +tr.strength : 1,
        sfx: tr.sfx, sfx_gain: tr.sfx_gain,
      });
    }
    S.trans = trans;

    const items = [];
    for (const trk of (S.tl.tracks || []).slice().sort((a, b) => (a.z || 0) - (b.z || 0))) {
      for (const it of trk.items || []) {
        const r = resolveItem(it, trk, bySeg, t);
        if (r) items.push(r);
      }
    }
    items.sort((a, b) => (a.z - b.z) || (a.t - b.t));
    // Captions in the protected subtitle lane never draw over one another,
    // including when their source clips are moved into overlapping lanes.
    const captions = items.filter(it => it.subtitle).sort((a,b) => a.t-b.t);
    for (let i=0;i<captions.length-1;i++) {
      captions[i].t_end = Math.min(captions[i].t_end,captions[i+1].t);
      captions[i].dur = Math.max(0,captions[i].t_end-captions[i].t);
    }
    S.items = items.filter(it => it.dur > 0.01);
    S.total = S.items.reduce((m, it) => Math.max(m, it.t_end), t);
    S.t = clamp(S.t, 0, S.total);
    return S;
  }

  /* Un item anclado vive con su clip: si el clip se apaga, el texto se va con
     el; si el clip se mueve, el texto lo sigue. Sin ancla manda `t`. */
  function resolveItem(it, trk, bySeg, total) {
    if (it.hidden || trk.hidden) return null;
    let t;
    if (it.anchor) {
      const c = bySeg[it.anchor.seg];
      if (!c) return null;
      t = c.t0 + (+it.anchor.offset || 0);
      if (it.anchor.clamp !== false) t = Math.min(t, Math.max(c.t0, c.t1 - 0.02));
    } else {
      t = +it.t || 0;
    }
    let dur = +it.dur || 0;
    if (dur <= 0.01) return null;
    t = Math.max(0, t);
    const r = Object.assign({}, it, {
      t, dur, t_end: t + dur, track: trk.id, track_kind: trk.kind,
      z: trk.z || 10, _raw: it,
      subtitle: trk.id === 't_sub' || /subt[ií]tulo/i.test(trk.name || ''),
    });
    if (trk.kind === 'audio') {
      r.track_gain = +trk.gain || 0;
      r.duck = !!trk.duck;
    }
    return r;
  }

  const activeClips = (t) => S.clips.filter(c => !c.hidden && c.t0 <= t && t < c.t1)
    .sort((a,b) => a.z - b.z || a.index - b.index);
  const clipAt = (t) => activeClips(t).at(-1) || null;

  const clipOf = (segId) => S.clips.find((c) => c.seg === segId) || null;
  const segOf = (segId) => S.project.segments.find((s) => s.id === segId) || null;

  function anchorAt(t) {
    const c = clipAt(t);
    if (c) return { seg: c.seg, offset: +(t - c.t0).toFixed(4) };
    return null;
  }

  /* ------------------------------------------------------------- historial */

  const snap = () => ({
    tl: structuredClone(S.tl),
    segs: structuredClone(S.project.segments),
    groups: structuredClone(S.project.groups || []),
  });

  function push() {
    S.undo.push(snap());
    if (S.undo.length > 90) S.undo.shift();
    S.redo.length = 0;
    markDirty(true);
  }

  function restore(s) {
    S.tl = s.tl;
    S.project.segments = s.segs;
    S.project.groups = s.groups;
    resolve();
    ST.app.renderAll();
  }

  function undo() {
    if (!S.undo.length) return ST.app.toast('Nada que deshacer');
    S.redo.push(snap());
    restore(S.undo.pop());
    markDirty(true);
  }

  function redo() {
    if (!S.redo.length) return ST.app.toast('Nada que rehacer');
    S.undo.push(snap());
    restore(S.redo.pop());
    markDirty(true);
  }

  function markDirty(v) {
    S.dirty = !!v;
    const d = document.getElementById('saveDot');
    if (d) d.className = 'dot' + (v ? ' dirty' : '');
    const u = document.getElementById('btnUndo'), r = document.getElementById('btnRedo');
    if (u) u.disabled = !S.undo.length;
    if (r) r.disabled = !S.redo.length;
  }

  async function save() {
    const r = await fetch('/api/timeline', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        timeline: S.tl,
        segments: S.project.segments,
        groups: S.project.groups || [],
      }),
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok || !j.ok) throw new Error((j && j.error) || ('HTTP ' + r.status));
    if (j.stats) S.project.stats = j.stats;
    markDirty(false);
    return j;
  }

  /* ------------------------------------------------------------ mutaciones */

  function nextId(prefix) {
    S.tl.counter = (+S.tl.counter || 0) + 1;
    return prefix + String(S.tl.counter).padStart(4, '0');
  }

  const track = (id) => (S.tl.tracks || []).find((t) => t.id === id) || null;

  function findItem(id) {
    for (const trk of S.tl.tracks || []) {
      const it = (trk.items || []).find((x) => x.id === id);
      if (it) return { trk, it };
    }
    return { trk: null, it: null };
  }

  function addItem(trackId, item) {
    const trk = track(trackId);
    if (!trk) return null;
    item.id = item.id || nextId(trk.kind === 'text' ? 'x' : (trk.kind === 'audio' ? 'a' : 'o'));
    trk.items.push(item);
    return item;
  }

  function delItem(id) {
    const { trk } = findItem(id);
    if (!trk) return false;
    trk.items = trk.items.filter((x) => x.id !== id);
    if (S.sel && S.sel.id === id) S.sel = null;
    return true;
  }

  function addTrack(kind, name) {
    const same = (S.tl.tracks || []).filter((x) => x.kind === kind);
    const top = same.reduce((m, x) => Math.max(m, +x.z || 0), 0);
    const trk = {
      id: nextId(kind === 'text' ? 'tx' : kind === 'video' ? 'vd' : (kind === 'audio' ? 'au' : 'ov')),
      kind, name: name || (kind === 'text' ? 'Texto' : kind === 'audio' ? 'Audio' : kind === 'video' ? 'Vídeo' : 'Visual'),
      z: top + 10, hidden: false, locked: false, items: [],
    };
    if (kind === 'audio') { trk.gain = 0; trk.duck = false; }
    S.tl.tracks.push(trk);
    return trk;
  }

  function moveTrack(id, dir) {
    const trk = track(id);
    if (!trk) return false;
    const ordered = S.tl.tracks.filter((x) => x.kind === trk.kind)
      .sort((a, b) => (+b.z || 0) - (+a.z || 0));
    const i = ordered.indexOf(trk), j = i + dir;
    if (i < 0 || j < 0 || j >= ordered.length) return false;
    const z = +trk.z || 0;
    trk.z = +ordered[j].z || 0;
    ordered[j].z = z;
    return true;
  }

  function delTrack(id) {
    const trk = track(id);
    if (!trk || (trk.items || []).length || S.project.segments.some(s => clipCfg(s.id).track === id)) return false;
    S.tl.tracks = S.tl.tracks.filter((x) => x.id !== id);
    return true;
  }

  function moveItemToTrack(id, trackId) {
    const found = findItem(id), dst = track(trackId);
    if (!found.it || !dst || dst.kind !== found.trk.kind || dst === found.trk) return false;
    found.trk.items = found.trk.items.filter((x) => x.id !== id);
    dst.items = dst.items || [];
    dst.items.push(found.it);
    return true;
  }

  // Al borrar un clip, las capas paralelas dejan de estar ancladas al clip y
  // conservan su tiempo. Así Delete afecta solo al objeto seleccionado.
  function detachAnchors(segId) {
    pinClipPositions();
    const times = new Map(S.items.filter((x) => x.anchor && x.anchor.seg === segId)
      .map((x) => [x.id, x.t]));
    for (const trk of S.tl.tracks || []) for (const it of trk.items || []) {
      if (!it.anchor || it.anchor.seg !== segId) continue;
      it.t = +(times.get(it.id) || 0).toFixed(3);
      delete it.anchor;
    }
  }

  // First free edit freezes legacy concatenated clips without moving any of
  // them. Subsequent moves/trims/deletes cannot ripple unrelated elements.
  function pinClipPositions() {
    if (!track('_video')) S.tl.tracks.push({id:'_video', kind:'video', name:'Vídeo', z:0, items:[]});
    for (const c of S.clips) setClip(c.seg, {start:c.t0, track:c.track, gap_before:0});
  }

  const overlaps = (a, b, c, d) => a < d - 0.001 && b > c + 0.001;

  function placeClip(id, time, trackId, autoLayer = true) {
    const c = clipOf(id);
    if (!c) return null;
    pinClipPositions();
    let dst = track(trackId || c.track);
    if (!dst || dst.kind !== 'video' || dst.locked) return null;
    time = Math.max(0, time);
    if (autoLayer && S.clips.some(x => x.seg !== id && x.track === dst.id && overlaps(time,time+c.dur,x.t0,x.t1))) {
      dst = addTrack('video');
    }
    setClip(id, {start: +time.toFixed(4), track:dst.id});
    return dst;
  }

  function placeItem(id, time, trackId, autoLayer = true) {
    const {it, trk} = findItem(id);
    let dst = track(trackId || trk?.id);
    if (!it || !dst || dst.kind !== trk.kind || dst.locked) return null;
    const subtitle = trk.id === 't_sub' || /subt[ií]tulo/i.test(trk.name || '');
    if (autoLayer && !subtitle && S.items.some(x => x.id !== id && x.track === dst.id && overlaps(time,time+it.dur,x.t,x.t_end))) {
      const original = dst;
      dst = addTrack(trk.kind);
      if (trk.kind === 'audio') { dst.gain = original.gain || 0; dst.duck = !!original.duck; }
    }
    moveItemToTrack(id, dst.id);
    delete it.anchor;
    it.t = +Math.max(0, time).toFixed(4);
    return dst;
  }

  // Pixel-based magnetism: consider both borders and ignore unchanged edges
  // with no candidate (otherwise an unsnapped start defeats a snapped end).
  function snapTime(id, start, dur = 0, enabled = S.snap) {
    if (!enabled) return {time:Math.max(0,start), edge:null};
    const edges = [0, S.t];
    for (const c of S.clips) if (c.seg !== id) edges.push(c.t0,c.t1);
    for (const it of S.items) if (it.id !== id && it.anchor?.seg !== id) edges.push(it.t,it.t_end);
    let distance = 10 / Math.max(1,S.pps), best = start, guide = null;
    for (const edge of edges) for (const offset of dur ? [0,dur] : [0]) {
      const diff = Math.abs(edge - (start + offset));
      if (diff < distance && edge-offset >= 0) { distance=diff; best=edge-offset; guide=edge; }
    }
    return {time:+Math.max(0,best).toFixed(4), edge:guide};
  }

  function setClip(segId, patch) {
    const slot = clipSlot(segId);
    Object.assign(slot, patch);
    for (const k of Object.keys(slot)) if (slot[k] === undefined) delete slot[k];
  }

  const transOf = (segId) => (S.tl.transitions || []).find((t) => t.at_seg === segId) || null;

  function setTransition(segId, patch) {
    S.tl.transitions = S.tl.transitions || [];
    let tr = transOf(segId);
    if (!tr) {
      tr = { id: nextId('t'), at_seg: segId, type: 'flash', dur: 0.3, strength: 1 };
      S.tl.transitions.push(tr);
    }
    Object.assign(tr, patch);
    return tr;
  }

  function delTransition(segId) {
    S.tl.transitions = (S.tl.transitions || []).filter((t) => t.at_seg !== segId);
  }

  const styleOf = (item) => {
    const base = Object.assign({}, (S.tl.styles || {})[item.style || 'capcut'] ||
                               Object.values(S.tl.styles || {})[0] || {});
    const ov = item.override || {};
    for (const [k, v] of Object.entries(ov)) {
      if (v && typeof v === 'object' && !Array.isArray(v) && base[k] && typeof base[k] === 'object') {
        base[k] = Object.assign({}, base[k], v);
      } else if (v != null) base[k] = v;
    }
    return base;
  };

  const select = (kind, id) => {
    S.sel = kind ? { kind, id } : null;
    ST.app.onSelect();
  };

  return {
    boot, resolve, clipCfg, clipSlot, zoomKfs, zoomFlat, clipAt, activeClips, clipOf, segOf,
    anchorAt, push, undo, redo, markDirty, save, nextId, track, findItem,
    addItem, delItem, addTrack, moveTrack, delTrack, moveItemToTrack, detachAnchors,
    setClip, transOf, setTransition, delTransition, styleOf,
    select, clamp, pinClipPositions, placeClip, placeItem, overlaps, snapTime,
  };
})();
