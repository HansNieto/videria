/* Timeline multipista: clips, transiciones en los cortes, e items de texto,
   overlay y audio. Un solo eje de tiempo (segundos de salida) para todo. */
window.ST = window.ST || {};

ST.timeline = (() => {
  'use strict';
  const S = ST.S;
  const st = ST.state;
  const clamp = st.clamp;

  const ROWS = [
    { id: 't_txt', kind: 'text', h: 30, label: 'Títulos' },
    { id: 't_sub', kind: 'text', h: 30, label: 'Subtítulos' },
    { id: 't_ovl', kind: 'overlay', h: 30, label: 'Overlays' },
    { id: '_video', kind: 'video', h: 78, label: 'Vídeo' },
    { id: 't_mus', kind: 'audio', h: 30, label: 'Música' },
    { id: 't_sfx', kind: 'audio', h: 28, label: 'SFX' },
  ];

  const WAVES = Object.create(null);
  const STRIPS = Object.create(null);
  const PEAKS_PER_SEC = 40;
  let scroll, inner, tracks, gutter, ruler, rctx, playhead;
  let drag = null, dropTrack = null;

  const el = (tag, cls, txt) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (txt != null) n.textContent = txt;
    return n;
  };
  const fmt = (t) => {
    t = Math.max(0, t || 0);
    const m = Math.floor(t / 60);
    return m + ':' + (t % 60).toFixed(2).padStart(5, '0');
  };

  /* ------------------------------------------------------------- assets */

  async function loadWave(sid) {
    if (WAVES[sid]) return;
    WAVES[sid] = new Uint8Array(0);
    try {
      const r = await fetch('/api/waveform/' + sid);
      if (!r.ok) return;
      WAVES[sid] = new Uint8Array(await r.arrayBuffer());
      render();
    } catch (e) { /* sin onda: el clip se dibuja liso */ }
  }

  function loadStrip(sid) {
    if (STRIPS[sid]) return;
    const meta = (S.sources[sid] || {}).filmstrip;
    if (!meta || !meta.cols) { STRIPS[sid] = { none: true }; return; }
    STRIPS[sid] = { none: true };
    const img = new Image();
    img.onload = () => { STRIPS[sid] = Object.assign({}, meta, { img }); render(); };
    img.onerror = () => { /* fondo liso */ };
    img.src = '/api/filmstrip/' + sid;
  }

  /* ------------------------------------------------------------- dibujo */

  function drawClip(cv, clip, w, h) {
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    cv.width = Math.max(1, Math.round(w * dpr));
    cv.height = Math.round(h * dpr);
    cv.style.width = w + 'px';
    cv.style.height = h + 'px';
    const c = cv.getContext('2d');
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.clearRect(0, 0, w, h);

    const strip = STRIPS[clip.source];
    const half = Math.round(h * 0.62);
    if (strip && strip.img) {
      const { img, cols, count, tw, th, interval } = strip;
      const step = Math.max(1, Math.round((tw * (half / th)) || 1));
      for (let x = 0; x < w; x += step) {
        const tsrc = clip.in + ((x / w) * clip.srcDur);
        const i = clamp(Math.floor(tsrc / interval), 0, count - 1);
        const sx = (i % cols) * tw, sy = Math.floor(i / cols) * th;
        const dw = Math.min(step, w - x);
        c.drawImage(img, sx, sy, tw * (dw / step), th, x, 0, dw, half);
      }
    } else {
      c.fillStyle = '#26344d';
      c.fillRect(0, 0, w, half);
    }

    const peaks = WAVES[clip.source];
    const wy = half, wh = h - half;
    c.fillStyle = '#101623';
    c.fillRect(0, wy, w, wh);
    if (peaks && peaks.length) {
      c.fillStyle = '#4d7fd6';
      const mid = wy + wh / 2;
      for (let x = 0; x < w; x++) {
        const tsrc = clip.in + ((x / w) * clip.srcDur);
        const i = Math.round(tsrc * PEAKS_PER_SEC);
        const v = (peaks[clamp(i, 0, peaks.length - 1)] || 0) / 255;
        const half2 = Math.max(0.5, (v * wh) / 2);
        c.fillRect(x, mid - half2, 1, half2 * 2);
      }
    }
    // Marca de zoom: una linea que sigue la escala a lo largo del clip.
    const kfs = st.zoomKfs(clip.cfg);
    if (kfs.length && !st.zoomFlat(kfs)) {
      c.strokeStyle = '#8b5cf6';
      c.lineWidth = 1.5;
      c.beginPath();
      for (let x = 0; x <= w; x += 2) {
        const rel = (x / w) * clip.dur;
        const z = ST.player.pw(kfs, 'scale', 1, rel);
        const y = half - ((clamp(z, 1, 2) - 1) / 1) * (half - 4) - 2;
        if (x === 0) c.moveTo(x, y); else c.lineTo(x, y);
      }
      c.stroke();
    }
  }

  function drawRuler() {
    ruler = ruler || document.getElementById('ruler');
    rctx = rctx || ruler.getContext('2d');
    const w = Math.max(inner.scrollWidth, scroll.clientWidth);
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    ruler.width = Math.round(w * dpr);
    ruler.height = Math.round(22 * dpr);
    ruler.style.width = w + 'px';
    rctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    rctx.clearRect(0, 0, w, 22);
    rctx.fillStyle = '#151924';
    rctx.fillRect(0, 0, w, 22);
    const steps = [0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300];
    const step = steps.find((s) => s * S.pps > 58) || 600;
    rctx.strokeStyle = '#2a3244';
    rctx.fillStyle = '#68718c';
    rctx.font = '10px ui-monospace,monospace';
    for (let t = 0; t <= S.total + step; t += step) {
      const x = Math.round(t * S.pps) + 0.5;
      rctx.beginPath(); rctx.moveTo(x, 13); rctx.lineTo(x, 22); rctx.stroke();
      rctx.fillText(fmt(t).replace(/\.00$/, ''), x + 3, 10);
    }
  }

  /* --------------------------------------------------------- construccion */

  function trackRow(row) {
    const trk = row.id === '_video' ? null : st.track(row.id);
    const node = el('div', 'trk');
    node.style.height = row.h + 'px';
    node.dataset.row = row.id;
    if (row.id === '_video') {
      buildClips(node, row);
    } else if (trk) {
      buildItems(node, trk, row);
    }
    return node;
  }

  function buildClips(node, row) {
    for (const clip of S.clips) {
      const x = clip.t0 * S.pps;
      const w = Math.max(3, clip.dur * S.pps);
      const d = el('div', 'clip' + (S.sel && S.sel.kind === 'clip' && S.sel.id === clip.seg ? ' sel' : ''));
      d.style.left = x + 'px';
      d.style.width = w + 'px';
      d.style.height = (row.h - 6) + 'px';
      d.dataset.seg = clip.seg;
      const cv = el('canvas');
      d.appendChild(cv);
      drawClip(cv, clip, w, row.h - 6);
      loadStrip(clip.source);
      loadWave(clip.source);
      const lbl = el('span', 'lbl', clip.text || (S.sources[clip.source] || {}).name || clip.seg);
      d.appendChild(lbl);
      const marks = [];
      if (Math.abs(clip.speed - 1) > 0.01) marks.push(clip.speed.toFixed(2) + '×');
      if (!st.zoomFlat(st.zoomKfs(clip.cfg))) marks.push('zoom');
      if (clip.cfg.mute) marks.push('mute');
      if (marks.length) d.appendChild(el('span', 'zi', marks.join(' · ')));
      d.appendChild(el('div', 'edge l'));
      d.appendChild(el('div', 'edge r'));
      node.appendChild(d);

      if (clip.index > 0) {
        const tr = st.transOf(clip.seg);
        const rtr = S.trans.find((t) => t.at_seg === clip.seg);
        const m = el('div', 'tmark' + (tr && rtr ? '' : ' add') +
                     (S.sel && S.sel.kind === 'trans' && S.sel.id === clip.seg ? ' sel' : ''));
        m.style.left = x + 'px';
        m.dataset.seg = clip.seg;
        m.title = tr ? ((S.cat.transitions.find((c) => c.id === tr.type) || {}).label || tr.type) +
                       ' · ' + (tr.dur || 0).toFixed(2) + 's'
                     : 'Sin transición — clic para añadir';
        m.appendChild(el('i'));
        node.appendChild(m);
      }
    }
  }

  function buildItems(node, trk, row) {
    for (const it of trk.items || []) {
      const r = S.items.find((x) => x.id === it.id);
      const t = r ? r.t : (it.anchor ? null : +it.t || 0);
      if (t == null) continue;              // su clip está apagado
      const dur = r ? r.dur : +it.dur || 0;
      const cls = row.kind === 'audio'
        ? (trk.id === 't_sfx' ? 'sfxi' : 'audio')
        : row.kind;
      const d = el('div', 'item ' + cls + (it.hidden ? ' hid' : '') +
                   (S.sel && S.sel.kind === 'item' && S.sel.id === it.id ? ' sel' : ''));
      d.style.left = (t * S.pps) + 'px';
      d.style.width = Math.max(6, dur * S.pps) + 'px';
      d.style.height = (row.h - 10) + 'px';
      d.dataset.item = it.id;
      d.title = label(it, trk) + '  ·  ' + fmt(t) + ' → ' + fmt(t + dur);
      d.appendChild(el('span', null, label(it, trk)));
      d.appendChild(el('div', 'edge l'));
      d.appendChild(el('div', 'edge r'));
      node.appendChild(d);
    }
  }

  function label(it, trk) {
    if (trk.kind === 'text') {
      return it.text || (it.lines || []).map((l) => l.map((w) => w.w).join(' ')).join(' ') || '(texto)';
    }
    return (it.src || '').split(/[\\/]/).pop() || it.id;
  }

  function buildGutter() {
    gutter.textContent = '';
    for (const row of ROWS) {
      const trk = row.id === '_video' ? null : st.track(row.id);
      const n = el('div', 'trk-name');
      n.style.height = row.h + 'px';
      n.appendChild(el('b', null, (trk && trk.name) || row.label));
      const sp = el('div', 'spacer');
      n.appendChild(sp);
      if (trk) {
        const eye = el('button', 'tbtn' + (trk.hidden ? ' off' : ''), trk.hidden ? '◌' : '◉');
        eye.title = trk.hidden ? 'Mostrar pista' : 'Ocultar pista';
        eye.onclick = () => { st.push(); trk.hidden = !trk.hidden; st.resolve(); ST.app.renderAll(); };
        n.appendChild(eye);
        const lock = el('button', 'tbtn' + (trk.locked ? ' off' : ''), trk.locked ? '🔒' : '🔓');
        lock.title = trk.locked ? 'Desbloquear' : 'Bloquear';
        lock.onclick = () => { st.push(); trk.locked = !trk.locked; ST.app.renderAll(); };
        n.appendChild(lock);
      }
      gutter.appendChild(n);
    }
  }

  function render() {
    if (!tracks) return;
    const sc = scroll.scrollLeft;
    tracks.textContent = '';
    for (const row of ROWS) tracks.appendChild(trackRow(row));
    inner.style.width = Math.max(S.total * S.pps + 260, scroll.clientWidth) + 'px';
    buildGutter();
    drawRuler();
    movePlayhead();
    scroll.scrollLeft = sc;
  }

  function movePlayhead() {
    playhead = playhead || document.getElementById('playhead');
    playhead.style.left = (S.t * S.pps) + 'px';
    const rw = document.querySelector('.tl-ruler-wrap');
    if (rw) rw.scrollLeft = scroll.scrollLeft;
  }

  function autoScroll() {
    const x = S.t * S.pps;
    const left = scroll.scrollLeft, w = scroll.clientWidth - 104;
    if (x < left + 40) scroll.scrollLeft = Math.max(0, x - 60);
    else if (x > left + w - 60) scroll.scrollLeft = x - w + 140;
  }

  /* ------------------------------------------------------------ eventos */

  const xToT = (ev) => {
    const r = inner.getBoundingClientRect();
    return clamp((ev.clientX - r.left) / S.pps, 0, S.total);
  };

  function onDown(ev) {
    if (ev.button !== 0) return;
    const mark = ev.target.closest('.tmark');
    if (mark) {
      const seg = mark.dataset.seg;
      if (!st.transOf(seg)) {
        st.push();
        const def = S.cat.transitions[0];
        st.setTransition(seg, { type: def.id, dur: def.dur, strength: 1 });
        st.resolve();
      }
      st.select('trans', seg);
      render();
      return;
    }
    const clipNode = ev.target.closest('.clip');
    const itemNode = ev.target.closest('.item');
    const edge = ev.target.classList.contains('edge')
      ? (ev.target.classList.contains('l') ? 'l' : 'r') : null;

    if (clipNode) {
      const seg = clipNode.dataset.seg;
      const clip = st.clipOf(seg);
      st.select('clip', seg);
      st.push();
      drag = { kind: edge ? 'trim' : 'move', side: edge, seg, t0: xToT(ev),
               in0: clip.in, out0: clip.out, node: clipNode, moved: false };
      render();
      ev.preventDefault();
      return;
    }
    if (itemNode) {
      const id = itemNode.dataset.item;
      const { trk, it } = st.findItem(id);
      if (trk && trk.locked) return ST.app.toast('La pista está bloqueada');
      const r = S.items.find((x) => x.id === id);
      st.select('item', id);
      st.push();
      drag = { kind: edge ? 'iresize' : 'imove', side: edge, id, t0: xToT(ev),
               start: r ? r.t : +it.t || 0, dur: r ? r.dur : +it.dur || 0,
               moved: false };
      render();
      ev.preventDefault();
      return;
    }
    // fondo: mover el cabezal
    drag = { kind: 'scrub' };
    ST.player.seek(xToT(ev));
    movePlayhead();
  }

  function onMove(ev) {
    if (!drag) return;
    const t = xToT(ev);
    if (drag.kind === 'scrub') { ST.player.seek(t); movePlayhead(); return; }
    const dt = t - drag.t0;
    if (Math.abs(dt) > 0.01) drag.moved = true;

    if (drag.kind === 'trim') {
      const seg = st.segOf(drag.seg);
      const src = S.sources[seg.source] || {};
      const spd = st.clipCfg(seg.id).speed || 1;
      if (drag.side === 'l') {
        seg.in = clamp(drag.in0 + dt * spd, 0, seg.out - 0.1);
      } else {
        seg.out = clamp(drag.out0 + dt * spd, seg.in + 0.1, src.duration || 1e6);
      }
      st.resolve();
      render();
    } else if (drag.kind === 'move') {
      const target = clipIndexAt(t);
      const cur = st.clipOf(drag.seg);
      if (cur && target != null && target !== cur.index) {
        moveClip(drag.seg, target);
        st.resolve();
        render();
      }
    } else if (drag.kind === 'imove') {
      const { it } = st.findItem(drag.id);
      if (!it) return;
      const snapped = snapItemTime(drag.id, Math.max(0, drag.start + dt), drag.dur);
      const nt = nonOverlappingStart(drag.id, snapped, drag.dur);
      if (it.anchor) {
        const a = st.anchorAt(nt);
        if (a) it.anchor = Object.assign({}, it.anchor, a);
      } else {
        it.t = +nt.toFixed(3);
      }
      st.resolve();
      render();
    } else if (drag.kind === 'iresize') {
      const { it } = st.findItem(drag.id);
      if (!it) return;
      if (drag.side === 'r') {
        let end = snapItemEdge(drag.id, drag.start + Math.max(0.1, drag.dur + dt));
        end = Math.min(end, subtitleRightLimit(drag.id, drag.start));
        it.dur = +Math.max(0.1, end - drag.start).toFixed(3);
      } else {
        const raw = clamp(drag.start + dt, 0, drag.start + drag.dur - 0.1);
        const snapped = Math.max(snapItemEdge(drag.id, raw),
                                 subtitleLeftLimit(drag.id, drag.start + drag.dur));
        const shift = snapped - drag.start;
        it.dur = +Math.max(0.1, drag.dur - shift).toFixed(3);
        if (it.anchor) {
          it.anchor.offset = +((+it.anchor.offset || 0) + shift).toFixed(3);
        } else {
          it.t = +Math.max(0, drag.start + shift).toFixed(3);
        }
        shiftWordTimes(it, -shift);
      }
      st.resolve();
      render();
    }
  }

  /* Al recortar por la izquierda, los tiempos de palabra son relativos al
     inicio del item: si no se corrigen, el revelado se descoloca. */
  function shiftWordTimes(it, delta) {
    if (!it.lines || !delta) return;
    for (const ln of it.lines) {
      for (const w of ln) {
        w.s = +((+w.s || 0) + delta).toFixed(3);
        w.e = +((+w.e || 0) + delta).toFixed(3);
      }
    }
  }

  // Ajuste magnetico: al acercar un borde a otro objeto de la misma pista,
  // se alinea. No crea grupos ni cambia la duracion de nadie mas.
  const SNAP_PX = 8;
  function snapItemEdge(id, value) {
    const { trk } = st.findItem(id);
    if (!trk) return value;
    const edges = [];
    for (const other of trk.items || []) {
      if (other.id === id || other.hidden) continue;
      const r = S.items.find((x) => x.id === other.id);
      if (!r) continue;
      edges.push(r.t, r.t_end);
    }
    let best = value, dist = SNAP_PX / Math.max(1, S.pps);
    for (const edge of edges) {
      const d = Math.abs(edge - value);
      if (d < dist) { best = edge; dist = d; }
    }
    return +best.toFixed(3);
  }

  function snapItemTime(id, start, dur) {
    const a = snapItemEdge(id, start);
    const b = snapItemEdge(id, start + dur);
    // Si ambos bordes encuentran candidatos, gana el que este mas cerca.
    return Math.abs(a - start) <= Math.abs(b - (start + dur)) ? a : +(b - dur).toFixed(3);
  }

  function subtitleRanges(id) {
    const { trk } = st.findItem(id);
    if (!trk || trk.id !== 't_sub') return null;
    return S.items.filter((x) => x.track === trk.id && x.id !== id)
      .map((x) => ({ t: x.t, end: x.t_end })).sort((a, b) => a.t - b.t);
  }

  // Busca el hueco valido mas cercano. Asi una tarjeta de subtitulo puede
  // moverse libremente, pero nunca queda dibujada encima de otra.
  function nonOverlappingStart(id, wanted, dur) {
    const ranges = subtitleRanges(id);
    if (!ranges) return wanted;
    const gaps = [];
    let from = 0;
    for (const r of ranges) {
      if (r.t - from >= dur) gaps.push([from, r.t - dur]);
      from = Math.max(from, r.end);
    }
    if (S.total - from >= dur) gaps.push([from, S.total - dur]);
    if (!gaps.length) return wanted;
    let best = gaps[0][0], dist = Infinity;
    for (const [a, b] of gaps) {
      const v = clamp(wanted, a, b);
      const d = Math.abs(v - wanted);
      if (d < dist) { best = v; dist = d; }
    }
    return +best.toFixed(3);
  }

  function subtitleRightLimit(id, start) {
    const ranges = subtitleRanges(id);
    if (!ranges) return Infinity;
    const next = ranges.find((r) => r.t >= start + 0.001);
    return next ? next.t : Infinity;
  }

  function subtitleLeftLimit(id, end) {
    const ranges = subtitleRanges(id);
    if (!ranges) return 0;
    let limit = 0;
    for (const r of ranges) if (r.end <= end + 0.001) limit = Math.max(limit, r.end);
    return limit;
  }

  function onUp() {
    if (!drag) return;
    const d = drag;
    drag = null;
    if (d.kind !== 'scrub' && d.moved) {
      st.markDirty(true);
      ST.inspector.render();
    } else if (d.kind !== 'scrub') {
      S.undo.pop();                        // un clic no es una edicion
      st.markDirty(S.dirty);
      ST.inspector.render();
    }
    render();
  }

  function clipIndexAt(t) {
    for (const c of S.clips) if (t >= c.t0 && t < c.t1) return c.index;
    return t <= 0 ? 0 : S.clips.length - 1;
  }

  /* Reordena dentro de project.segments, que incluye los apagados: hay que
     buscar la posicion real del clip destino, no el indice visible. */
  function moveClip(segId, toIndex) {
    const segs = S.project.segments;
    const cur = st.clipOf(segId);
    if (!cur) return;
    const target = S.clips[clamp(toIndex, 0, S.clips.length - 1)];
    if (!target || target.seg === segId) return;
    const from = segs.findIndex((s) => s.id === segId);
    if (from < 0) return;
    const [moved] = segs.splice(from, 1);
    let to = segs.findIndex((s) => s.id === target.seg);
    if (to < 0) to = segs.length;
    segs.splice(toIndex > cur.index ? to + 1 : to, 0, moved);
  }

  function onDblClick(ev) {
    const clipNode = ev.target.closest('.clip');
    if (clipNode) {
      const seg = st.segOf(clipNode.dataset.seg);
      st.push();
      seg.enabled = !seg.enabled;
      st.resolve();
      ST.app.renderAll();
      return;
    }
    const itemNode = ev.target.closest('.item');
    if (itemNode) ST.inspector.focusText(itemNode.dataset.item);
  }

  function onContext(ev) {
    const clipNode = ev.target.closest('.clip');
    const itemNode = ev.target.closest('.item');
    const mark = ev.target.closest('.tmark');
    if (!clipNode && !itemNode && !mark) return;
    ev.preventDefault();
    const items = [];
    if (mark) {
      const seg = mark.dataset.seg;
      items.push(['Cambiar transición…', () => { st.select('trans', seg); }]);
      if (st.transOf(seg)) items.push(['Quitar transición', () => {
        st.push(); st.delTransition(seg); st.resolve(); ST.app.renderAll();
      }]);
    } else if (clipNode) {
      const seg = clipNode.dataset.seg;
      const s = st.segOf(seg);
      items.push([s.enabled ? 'Apagar clip' : 'Encender clip', () => {
        st.push(); s.enabled = !s.enabled; st.resolve(); ST.app.renderAll();
      }]);
      items.push(['Cortar en el cabezal', () => splitAtPlayhead(seg)]);
      items.push(['Quitar zoom', () => {
        st.push(); st.setClip(seg, { zoom: null }); st.resolve(); ST.app.renderAll();
      }]);
      items.push(['Regenerar subtítulos de este clip', async () => {
        await ST.app.regenSubs([seg]);
      }]);
    } else if (itemNode) {
      const id = itemNode.dataset.item;
      const { it } = st.findItem(id);
      items.push([it.hidden ? 'Mostrar' : 'Ocultar', () => {
        st.push(); it.hidden = !it.hidden; st.resolve(); ST.app.renderAll();
      }]);
      items.push(['Duplicar', () => {
        st.push();
        const { trk } = st.findItem(id);
        const copy = structuredClone(it);
        copy.id = st.nextId(trk.kind === 'text' ? 'x' : (trk.kind === 'audio' ? 'a' : 'o'));
        copy.auto = false;
        if (copy.anchor) copy.anchor.offset = (+copy.anchor.offset || 0) + (+copy.dur || 0);
        else copy.t = (+copy.t || 0) + (+copy.dur || 0);
        trk.items.push(copy);
        st.resolve(); ST.app.renderAll();
      }]);
      items.push(['Borrar', () => {
        st.push(); st.delItem(id); st.resolve(); ST.app.renderAll();
      }]);
    }
    ST.app.menu(ev.clientX, ev.clientY, items);
  }

  async function splitAtPlayhead(segId) {
    const clip = st.clipOf(segId);
    if (!clip || S.t <= clip.t0 + 0.06 || S.t >= clip.t1 - 0.06) {
      return ST.app.toast('Poné el cabezal dentro del clip', 'bad');
    }
    st.push();
    const segs = S.project.segments;
    const i = segs.findIndex((s) => s.id === segId);
    const seg = segs[i];
    const cutSrc = seg.in + (S.t - clip.t0) * clip.speed;
    const b = structuredClone(seg);
    b.id = 'm' + Math.random().toString(36).slice(2, 6);
    b.in = cutSrc;
    seg.out = cutSrc;
    b.words = (seg.words || []).filter((w) => w.s >= cutSrc);
    seg.words = (seg.words || []).filter((w) => w.s < cutSrc);
    b.text = b.words.map((w) => w.w).join(' ');
    seg.text = seg.words.map((w) => w.w).join(' ');
    b.group = null; b.locked = true; seg.locked = true;
    segs.splice(i + 1, 0, b);
    // Los ajustes de zoom/velocidad del original valen para la primera mitad;
    // la segunda arranca limpia para no heredar un zoom a medias.
    st.resolve();
    ST.app.renderAll();
    // Las tarjetas automaticas se derivan de las palabras de cada mitad. Se
    // regeneran solo para los dos clips nuevos, preservando textos manuales.
    await ST.app.regenSubs([seg.id, b.id]);
  }

  function trimAtPlayhead(side) {
    const clip = st.clipAt(S.t);
    if (!clip || S.t <= clip.t0 + 0.06 || S.t >= clip.t1 - 0.06) {
      return ST.app.toast('Poné el cabezal dentro del clip', 'bad');
    }
    st.push();
    const seg = st.segOf(clip.seg);
    const cutSrc = seg.in + (S.t - clip.t0) * clip.speed;
    if (side === 'left') seg.in = cutSrc;
    else seg.out = cutSrc;
    seg.words = (seg.words || []).filter((w) => side === 'left' ? w.e > cutSrc : w.s < cutSrc);
    seg.text = seg.words.map((w) => w.w).join(' ');
    seg.locked = true;
    st.resolve();
    ST.app.renderAll();
    ST.app.regenSubs([seg.id]);
  }

  /* -------------------------------------------------------- arrastrar aqui */

  function onDragOver(ev) {
    const row = ev.target.closest('.trk');
    if (!row) return;
    ev.preventDefault();
    if (dropTrack && dropTrack !== row) dropTrack.classList.remove('drop');
    dropTrack = row;
    row.classList.add('drop');
  }

  function onDrop(ev) {
    const row = ev.target.closest('.trk');
    if (dropTrack) dropTrack.classList.remove('drop');
    dropTrack = null;
    if (!row) return;
    ev.preventDefault();
    let payload;
    try { payload = JSON.parse(ev.dataTransfer.getData('text/plain')); } catch (e) { return; }
    ST.library.dropOn(row.dataset.row, xToT(ev), payload);
  }

  function bind() {
    scroll = document.getElementById('tlScroll');
    inner = document.getElementById('tlInner');
    tracks = document.getElementById('tracks');
    gutter = document.getElementById('tlGutter');
    inner.addEventListener('mousedown', onDown);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    inner.addEventListener('dblclick', onDblClick);
    inner.addEventListener('contextmenu', onContext);
    inner.addEventListener('dragover', onDragOver);
    inner.addEventListener('drop', onDrop);
    scroll.addEventListener('scroll', () => {
      const rw = document.querySelector('.tl-ruler-wrap');
      if (rw) rw.scrollLeft = scroll.scrollLeft;
    });
    scroll.addEventListener('wheel', (ev) => {
      if (!ev.ctrlKey) return;
      ev.preventDefault();
      setZoom(S.pps * (ev.deltaY < 0 ? 1.15 : 1 / 1.15));
    }, { passive: false });
    render();
  }

  function setZoom(pps) {
    S.pps = clamp(pps, 8, 400);
    document.getElementById('tlZoom').value = Math.round(S.pps);
    render();
  }

  return { bind, render, movePlayhead, autoScroll, setZoom, splitAtPlayhead, trimAtPlayhead, ROWS };
})();
