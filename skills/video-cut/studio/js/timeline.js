/* Timeline multipista: clips, transiciones en los cortes, e items de texto,
   overlay y audio. Un solo eje de tiempo (segundos de salida) para todo. */
window.ST = window.ST || {};

ST.timeline = (() => {
  'use strict';
  const S = ST.S;
  const st = ST.state;
  const clamp = st.clamp;

  function rows() {
    const ordered = (kind) => (S.tl.tracks || []).filter((x) => x.kind === kind)
      .sort((a, b) => (+b.z || 0) - (+a.z || 0))
      .map((x) => ({ id: x.id, kind, h: kind === 'video' ? 78 : kind === 'audio' ? 30 : 32, label: x.name }));
    // En pantalla, lo de arriba se compone encima. El vídeo base separa las
    // capas visuales de las pistas de sonido.
    const video = ordered('video');
    if (!video.some(r => r.id === '_video')) video.push({id:'_video',kind:'video',h:78,label:'Vídeo'});
    return [...ordered('text'), ...ordered('overlay'), ...video, ...ordered('audio')];
  }

  const WAVES = Object.create(null);
  const STRIPS = Object.create(null);
  const PEAKS_PER_SEC = 40;
  let scroll, inner, tracks, gutter, ruler, rctx, playhead;
  let drag = null, dropTrack = null, snapGuide = null;

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
    const trk = st.track(row.id);
    const node = el('div', 'trk');
    node.style.height = row.h + 'px';
    node.dataset.row = row.id;
    if (row.kind === 'video') {
      buildClips(node, row);
    } else if (trk) {
      buildItems(node, trk, row);
    }
    return node;
  }

  function buildClips(node, row) {
    for (const clip of S.clips) {
      if (clip.track !== row.id) continue;
      const x = clip.t0 * S.pps;
      const w = Math.max(3, clip.dur * S.pps);
      const d = el('div', 'clip' + (S.sel && S.sel.kind === 'clip' && S.sel.id === clip.seg ? ' sel' : ''));
      d.style.left = x + 'px';
      d.style.width = w + 'px';
      d.style.height = (row.h - 6) + 'px';
      d.dataset.seg = clip.seg;
      d.title = 'Arrastrar libremente · Superponer crea una capa · Alt desactiva el imán';
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
    const visibleRows = rows();
    for (const row of visibleRows) {
      const trk = st.track(row.id);
      const n = el('div', 'trk-name');
      n.style.height = row.h + 'px';
      n.appendChild(el('b', null, (trk && trk.name) || row.label));
      const sp = el('div', 'spacer');
      n.appendChild(sp);
      if (trk) {
        const order = el('span', 'order');
        const up = el('button', 'tbtn', '▲');
        up.title = 'Subir capa (se verá por encima)';
        up.onclick = () => { st.push(); if (!st.moveTrack(trk.id, -1)) S.undo.pop(); st.resolve(); ST.app.renderAll(); };
        const down = el('button', 'tbtn', '▼');
        down.title = 'Bajar capa';
        down.onclick = () => { st.push(); if (!st.moveTrack(trk.id, 1)) S.undo.pop(); st.resolve(); ST.app.renderAll(); };
        order.append(up, down); n.appendChild(order);
        const eye = el('button', 'tbtn' + (trk.hidden ? ' off' : ''), trk.hidden ? '◌' : '◉');
        eye.title = trk.hidden ? 'Mostrar pista' : 'Ocultar pista';
        eye.onclick = () => { st.push(); trk.hidden = !trk.hidden; st.resolve(); ST.app.renderAll(); };
        n.appendChild(eye);
        const lock = el('button', 'tbtn' + (trk.locked ? ' off' : ''), trk.locked ? '🔒' : '🔓');
        lock.title = trk.locked ? 'Desbloquear' : 'Bloquear';
        lock.onclick = () => { st.push(); trk.locked = !trk.locked; ST.app.renderAll(); };
        n.appendChild(lock);
        if (!['_video', 't_txt', 't_sub', 't_ovl', 't_mus', 't_sfx'].includes(trk.id)) {
          const del = el('button', 'tbtn', '×');
          const occupied = (trk.items || []).length || S.project.segments.some(s => st.clipCfg(s.id).track === trk.id);
          del.title = occupied ? 'La capa debe estar vacía para borrarla' : 'Borrar capa vacía';
          del.disabled = !!occupied;
          del.onclick = () => { st.push(); st.delTrack(trk.id); st.resolve(); ST.app.renderAll(); };
          n.appendChild(del);
        }
      }
      gutter.appendChild(n);
    }
  }

  function render() {
    if (!tracks) return;
    const sc = scroll.scrollLeft;
    tracks.textContent = '';
    for (const row of rows()) tracks.appendChild(trackRow(row));
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
    return Math.max(0, (ev.clientX - r.left) / S.pps);
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
      if (st.track(clip.track)?.locked) return ST.app.toast('La pista está bloqueada');
      ST.player.pause();
      st.select('clip', seg);
      st.push();
      drag = { kind: edge ? 'trim' : 'move', side: edge, seg, t0: xToT(ev),
               in0: clip.in, out0: clip.out, pointerOffset: xToT(ev) - clip.t0,
               start: clip.t0, target: clip.track, y0: ev.clientY,
               gap0: clip.gap_before || 0, node: clipNode, moved: false };
      render();
      ev.preventDefault();
      return;
    }
    if (itemNode) {
      const id = itemNode.dataset.item;
      const { trk, it } = st.findItem(id);
      if (trk && trk.locked) return ST.app.toast('La pista está bloqueada');
      const r = S.items.find((x) => x.id === id);
      ST.player.pause();
      st.select('item', id);
      st.push();
      drag = { kind: edge ? 'iresize' : 'imove', side: edge, id, t0: xToT(ev),
               start: r ? r.t : +it.t || 0, dur: r ? r.dur : +it.dur || 0,
               target: trk.id, y0: ev.clientY, lines: structuredClone(it.lines || []), moved: false };
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
    showSnap(null);
    if (drag.kind !== 'scrub') {
      const rect = scroll.getBoundingClientRect();
      if (ev.clientX > rect.right - 35) scroll.scrollLeft += 14;
      else if (ev.clientX < rect.left + 170) scroll.scrollLeft = Math.max(0, scroll.scrollLeft - 14);
    }
    const t = xToT(ev);
    if (drag.kind === 'scrub') { ST.player.seek(t); movePlayhead(); return; }
    const dt = t - drag.t0;
    if (!drag.moved && Math.abs(dt)*S.pps < 3 && Math.abs(ev.clientY-drag.y0) < 4) return;
    if (!drag.moved && ['move','trim'].includes(drag.kind)) st.pinClipPositions();
    drag.moved = true;
    drag.noSnap = ev.altKey;

    if (drag.kind === 'trim') {
      const seg = st.segOf(drag.seg);
      const src = S.sources[seg.source] || {};
      const spd = st.clipCfg(seg.id).speed || 1;
      if (drag.side === 'l') {
        seg.in = clamp(drag.in0 + dt * spd, 0, seg.out - 0.1);
        st.setClip(seg.id, {start:Math.max(0,drag.start+(seg.in-drag.in0)/spd)});
      } else {
        seg.out = clamp(drag.out0 + dt * spd, seg.in + 0.1, src.duration || 1e6);
      }
      st.resolve();
      render();
    } else if (drag.kind === 'move') {
      const cur = st.clipOf(drag.seg);
      if (cur) {
        const targetNode = document.elementFromPoint(ev.clientX, ev.clientY)?.closest('.trk');
        const target = targetNode && st.track(targetNode.dataset.row);
        if (target?.kind === 'video' && !target.locked) drag.target = target.id;
        const snapped = st.snapTime(cur.seg, Math.max(0,t-drag.pointerOffset), cur.dur, S.snap && !ev.altKey);
        showSnap(snapped.edge);
        st.placeClip(cur.seg, snapped.time, drag.target, false);
        st.resolve();
        render();
        if (S.clips.some(c => c.seg !== cur.seg && c.track === drag.target && st.overlaps(snapped.time,snapped.time+cur.dur,c.t0,c.t1))) {
          tracks.querySelector(`[data-row="${drag.target}"]`)?.classList.add('drop-new');
        }
      }
    } else if (drag.kind === 'imove') {
      let { trk, it } = st.findItem(drag.id);
      if (!it) return;
      const targetNode = document.elementFromPoint(ev.clientX, ev.clientY)?.closest('.trk');
      const target = targetNode && st.track(targetNode.dataset.row);
      if (target && target.kind === trk.kind && !target.locked && target.id !== trk.id) {
        st.moveItemToTrack(drag.id, target.id);
        trk = target;
      }
      drag.target = trk.id;
      const snapped = snapItemTime(drag.id, Math.max(0, drag.start + dt), drag.dur);
      const nt = nonOverlappingStart(drag.id, snapped, drag.dur);
      st.placeItem(drag.id, nt, drag.target, false);
      st.resolve();
      render();
      if (!subtitleRanges(drag.id) && S.items.some(x => x.id !== drag.id && x.track === drag.target && st.overlaps(nt,nt+drag.dur,x.t,x.t_end))) {
        tracks.querySelector(`[data-row="${drag.target}"]`)?.classList.add('drop-new');
      }
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
        delete it.anchor;
        it.t = +Math.max(0, drag.start + shift).toFixed(3);
        it.lines = structuredClone(drag.lines);
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

  // Ajuste magnético global: al acercar un borde a cualquier inicio/final del
  // panel se alinea. No agrupa objetos ni bloquea el movimiento.
  function showSnap(t) {
    if (t == null) {
      if (snapGuide) snapGuide.remove();
      snapGuide = null; return;
    }
    if (!snapGuide) { snapGuide = el('div', 'snap-guide'); inner.appendChild(snapGuide); }
    snapGuide.style.left = (t * S.pps) + 'px';
  }

  function snapItemEdge(id, value) {
    const result = st.snapTime(id,value,0,S.snap && !drag?.noSnap);
    showSnap(result.edge);
    return result.time;
  }

  function snapItemTime(id, start, dur) {
    const result = st.snapTime(id,start,dur,S.snap && !drag?.noSnap);
    showSnap(result.edge);
    return result.time;
  }

  function subtitleRanges(id) {
    const { trk } = st.findItem(id);
    if (!trk || !(trk.id === 't_sub' || /subt[ií]tulo/i.test(trk.name || ''))) return null;
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
    gaps.push([from, Infinity]);
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
    showSnap(null);
    if (d.kind !== 'scrub' && d.moved) {
      if (d.kind === 'move') {
        const c = st.clipOf(d.seg);
        st.placeClip(d.seg, c.t0, d.target);
      } else if (d.kind === 'imove') {
        const r = S.items.find(x => x.id === d.id);
        if (r) st.placeItem(d.id, r.t, d.target);
      }
      st.resolve();
      st.markDirty(true);
      ST.inspector.render();
      if (d.kind === 'trim') ST.app.regenSubs([d.seg]);
    } else if (d.kind !== 'scrub') {
      S.undo.pop();                        // un clic no es una edicion
      st.markDirty(S.dirty);
      ST.inspector.render();
    }
    render();
    ST.player.seek(S.t, false);
  }

  function onDblClick(ev) {
    const clipNode = ev.target.closest('.clip');
    if (clipNode) {
      const seg = st.segOf(clipNode.dataset.seg);
      if (st.track(st.clipCfg(seg.id).track)?.locked) return;
      st.push();
      if (seg.enabled) st.detachAnchors(seg.id);
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
      items.push([s.enabled ? 'Borrar solo este clip' : 'Encender clip', () => {
        st.push();
        if (s.enabled) st.detachAnchors(seg);
        s.enabled = !s.enabled; st.resolve(); ST.app.renderAll();
      }]);
      items.push(['Cortar en el cabezal', () => splitAtPlayhead(seg)]);
      if ((st.clipCfg(seg).gap_before || 0) > 0) items.push(['Quitar espacio anterior', () => {
        st.push(); st.setClip(seg, { gap_before: 0 }); st.resolve(); ST.app.renderAll();
      }]);
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
    if (clip && st.track(clip.track)?.locked) return ST.app.toast('La pista está bloqueada');
    if (!clip || S.t <= clip.t0 + 0.06 || S.t >= clip.t1 - 0.06) {
      return ST.app.toast('Poné el cabezal dentro del clip', 'bad');
    }
    st.push();
    st.pinClipPositions();
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
    const second = structuredClone(st.clipCfg(segId));
    second.start = S.t;
    const splitOffset = S.t - clip.t0;
    const kfs = st.zoomKfs(second);
    if (kfs.length) second.zoom = {kf:[{t:0, scale:ST.player.pw(kfs,'scale',1,splitOffset),
      x:ST.player.pw(kfs,'x',0,splitOffset), y:ST.player.pw(kfs,'y',0,splitOffset)},
      ...kfs.filter(k => k.t > splitOffset).map(k => ({...k,t:k.t-splitOffset}))]};
    st.setClip(b.id, second);
    st.resolve();
    ST.app.renderAll();
    // Las tarjetas automaticas se derivan de las palabras de cada mitad. Se
    // regeneran solo para los dos clips nuevos, preservando textos manuales.
    await ST.app.regenSubs([seg.id, b.id]);
  }

  function trimAtPlayhead(side) {
    const clip = st.clipAt(S.t);
    if (clip && st.track(clip.track)?.locked) return ST.app.toast('La pista está bloqueada');
    if (!clip || S.t <= clip.t0 + 0.06 || S.t >= clip.t1 - 0.06) {
      return ST.app.toast('Poné el cabezal dentro del clip', 'bad');
    }
    st.push();
    st.pinClipPositions();
    const seg = st.segOf(clip.seg);
    const cutSrc = seg.in + (S.t - clip.t0) * clip.speed;
    if (side === 'left') { seg.in = cutSrc; st.setClip(clip.seg, {start:S.t}); }
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

  async function onDrop(ev) {
    const row = ev.target.closest('.trk');
    if (dropTrack) dropTrack.classList.remove('drop');
    dropTrack = null;
    if (!row) return;
    ev.preventDefault();
    if (ev.dataTransfer.files && ev.dataTransfer.files.length) {
      await ST.library.importFiles(ev.dataTransfer.files, row.dataset.row, xToT(ev));
      return;
    }
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

  return { bind, render, movePlayhead, autoScroll, setZoom, splitAtPlayhead, trimAtPlayhead, rows };
})();
