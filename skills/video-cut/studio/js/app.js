/* Arranque, atajos y las acciones que hablan con el servidor. */
window.ST = window.ST || {};

ST.app = (() => {
  'use strict';
  const S = ST.S;
  const st = ST.state;
  const $ = (id) => document.getElementById(id);
  let toastTimer = 0, pollTimer = 0, curJob = null;

  /* ----------------------------------------------------------------- toast */

  function toast(msg, kind, action) {
    const box = $('toast');
    box.textContent = '';
    box.appendChild(Object.assign(document.createElement('span'), { textContent: msg }));
    if (action) {
      const b = document.createElement('button');
      b.textContent = action.label;
      b.onclick = () => { action.fn(); hideToast(); };
      box.appendChild(b);
    }
    box.className = 'show' + (kind === 'bad' ? ' bad' : '');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(hideToast, action ? 9000 : 2800);
  }
  const hideToast = () => { $('toast').className = ''; };

  function menu(x, y, items) {
    closeMenu();
    const m = document.createElement('div');
    m.className = 'menu';
    for (const it of items) {
      if (!it) { m.appendChild(document.createElement('hr')); continue; }
      const [label, fn] = it;
      const b = document.createElement('button');
      b.textContent = label;
      b.onclick = () => { closeMenu(); fn(); };
      m.appendChild(b);
    }
    m.style.left = Math.min(x, window.innerWidth - 210) + 'px';
    m.style.top = Math.min(y, window.innerHeight - 40 - items.length * 30) + 'px';
    $('menuHost').appendChild(m);
    setTimeout(() => document.addEventListener('mousedown', closeMenu, { once: true }), 0);
  }
  const closeMenu = () => { $('menuHost').textContent = ''; };

  /* ------------------------------------------------------------- pintado */

  const fmt = (t) => {
    t = Math.max(0, t || 0);
    const m = Math.floor(t / 60);
    return String(m).padStart(2, '0') + ':' + (t % 60).toFixed(2).padStart(5, '0');
  };

  function onTime() {
    $('tCur').textContent = fmt(S.t);
    $('tTot').textContent = fmt(S.total);
    ST.timeline.movePlayhead();
    if (S.playing) ST.timeline.autoScroll();
    const clip = st.clipAt(S.t);
    $('stageInfo').textContent = clip
      ? ('clip ' + (clip.index + 1) + '/' + S.clips.length +
         '  ·  ' + (S.t - clip.t0).toFixed(2) + 's de ' + clip.dur.toFixed(2) + 's')
      : '';
    const kf = document.querySelector('.kf');
    if (kf && kf._draw) kf._draw();
  }

  const onSelect = () => { ST.inspector.render(); ST.timeline.render(); };

  function renderAll() {
    st.markDirty(S.dirty);
    $('projName').textContent = S.project.name || 'sin nombre';
    const stt = S.project.stats || {};
    $('projStats').textContent =
      S.clips.length + ' clips · ' + S.total.toFixed(1) + ' s · ' +
      S.items.length + ' items · ' + (S.tl.transitions || []).length + ' transiciones' +
      (stt.removed_pct ? '  ·  ' + stt.removed_pct.toFixed(0) + '% del bruto eliminado' : '');
    ST.timeline.render();
    ST.inspector.render();
    ST.library.render();
    ST.player.paint();
    onTime();
  }

  function setMode(m) {
    S.mode = m;
    for (const b of document.querySelectorAll('#modeSeg button')) {
      b.classList.toggle('on', b.dataset.mode === m);
    }
    $('canvasBox').classList.toggle('frame', m === 'frame');
    ST.player.paint();
    ST.inspector.render();
  }

  /* ------------------------------------------------------------- servidor */

  async function post(url, payload) {
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.error || j.description || ('HTTP ' + r.status));
    return j;
  }

  async function save() {
    try {
      await st.save();
      toast('Guardado');
    } catch (e) {
      toast('No pude guardar: ' + e.message, 'bad');
    }
  }

  async function reload() {
    const warns = await st.boot('Recargando…');
    renderAll();
    if (warns.length) toast(warns[0], 'bad');
  }

  /* El reparto en lineas lo decide el servidor con las metricas del .ttf, para
     que el preview y el render partan las lineas en el mismo sitio. */
  async function rewrap(it, newText, keyword) {
    const old = (it.lines || []).flat();
    let words = old;
    if (newText != null) {
      const parts = newText.trim().split(/\s+/).filter(Boolean);
      words = parts.map((w, i) => (old[i] && parts.length === old.length
        ? { w, s: old[i].s, e: old[i].e }
        : { w, s: 0, e: 0 }));
    }
    if (keyword === undefined) {
      const k = old.find((w) => w.key);
      keyword = k ? k.w : '';
    }
    try {
      const j = await post('/api/wrap', {
        words: words.map((w) => ({ w: w.w, s: w.s, e: w.e })),
        style: it.style || 'capcut',
        override: it.override || {},
        keyword: keyword || null,
        dur: it.dur,
        canvas_w: S.tl.canvas.width,
      });
      it.lines = j.lines;
      it.text = j.lines.map((l) => l.map((w) => w.w).join(' ')).join(' ');
      it.auto = false;
      if (j.overflow) toast('Sobran ' + j.overflow + ' líneas: no caben en el estilo');
    } catch (e) {
      toast('No pude repartir el texto: ' + e.message, 'bad');
    }
  }

  async function regenSubs(segs, opts) {
    try {
      // El servidor genera desde el timeline GUARDADO y devuelve uno nuevo que
      // reemplaza al que hay en memoria. Sin guardar primero, lo que estuviera
      // sin guardar se perdería sin avisar.
      if (S.dirty) await st.save();
      const j = await post('/api/subs', Object.assign({ segs }, opts || {}));
      S.tl = j.timeline;
      await ST.text.preload(S.tl);
      st.resolve();
      renderAll();
      toast(j.cards + ' tarjetas de subtítulo');
    } catch (e) {
      toast('No pude generar los subtítulos: ' + e.message, 'bad');
    }
  }

  async function relayout(styleKey) {
    try {
      await st.save();
      const j = await post('/api/relayout', { style: styleKey || null });
      S.tl = j.timeline;
      st.resolve();
      renderAll();
      toast(j.items + ' textos re-partidos');
    } catch (e) {
      toast('No pude re-partir: ' + e.message, 'bad');
    }
  }

  /* --------------------------------------------------------------- render */

  async function startRender(draft, range) {
    if (S.dirty) {
      try { await st.save(); } catch (e) {
        return toast('Guardá antes de renderizar: ' + e.message, 'bad');
      }
    }
    $('renderModal').classList.remove('hidden');
    $('rmTitle').textContent = draft ? 'Borrador…' : 'Render final…';
    $('rmBar').style.width = '0%';
    $('rmPct').textContent = '0%';
    $('rmStage').textContent = 'preparando';
    $('rmErr').classList.add('hidden');
    $('rmOpen').classList.add('hidden');
    $('rmClose').classList.add('hidden');
    $('rmCancel').classList.remove('hidden');
    try {
      const j = await post('/api/render', { draft, range });
      curJob = j.job;
      poll();
    } catch (e) {
      $('rmErr').textContent = e.message;
      $('rmErr').classList.remove('hidden');
      $('rmCancel').classList.add('hidden');
      $('rmClose').classList.remove('hidden');
    }
  }

  function poll() {
    clearTimeout(pollTimer);
    pollTimer = setTimeout(async () => {
      if (!curJob) return;
      try {
        const j = await fetch('/api/render/' + curJob).then((r) => r.json());
        const pct = Math.round((j.progress || 0) * 100);
        $('rmBar').style.width = pct + '%';
        $('rmPct').textContent = pct + '%';
        $('rmStage').textContent = j.stage || j.status;
        if (j.status === 'corriendo') return poll();
        $('rmCancel').classList.add('hidden');
        $('rmClose').classList.remove('hidden');
        if (j.status === 'ok') {
          $('rmTitle').textContent = 'Listo';
          $('rmBar').style.width = '100%';
          $('rmPct').textContent = '100%';
          const mb = (j.info && j.info.size ? (j.info.size / 1048576).toFixed(1) + ' MB' : '');
          $('rmStage').textContent = (j.out || '').split(/[\\/]/).pop() + '  ' + mb;
          const open = $('rmOpen');
          open.classList.remove('hidden');
          open.onclick = () => post('/api/reveal', { path: j.out });
          const warns = (j.info && j.info.warnings) || [];
          if (warns.length) {
            $('rmErr').textContent = warns.join('\n');
            $('rmErr').classList.remove('hidden');
          }
        } else {
          $('rmTitle').textContent = j.status === 'cancelado' ? 'Cancelado' : 'Falló';
          if (j.error) {
            $('rmErr').textContent = j.error;
            $('rmErr').classList.remove('hidden');
          }
        }
      } catch (e) {
        $('rmErr').textContent = e.message;
        $('rmErr').classList.remove('hidden');
        $('rmCancel').classList.add('hidden');
        $('rmClose').classList.remove('hidden');
      }
    }, 550);
  }

  /* --------------------------------------------------------------- atajos */

  function gotoClip(dir) {
    const clip = st.clipAt(S.t);
    let i = clip ? clip.index : 0;
    if (dir > 0) i = Math.min(S.clips.length - 1, i + 1);
    else i = (clip && S.t - clip.t0 > 0.25) ? i : Math.max(0, i - 1);
    const c = S.clips[i];
    if (c) ST.player.seek(c.t0 + 0.001);
  }

  function delSelected() {
    if (!S.sel) return;
    if (S.sel.kind === 'item') {
      st.push(); st.delItem(S.sel.id); st.resolve(); renderAll();
    } else if (S.sel.kind === 'trans') {
      st.push(); st.delTransition(S.sel.id); st.resolve(); renderAll();
    } else if (S.sel.kind === 'clip') {
      st.push();
      st.segOf(S.sel.id).enabled = false;
      st.resolve(); renderAll();
    }
  }

  function keys(ev) {
    const tag = (ev.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') {
      if (ev.key === 'Escape') ev.target.blur();
      return;
    }
    const fps = S.tl.canvas.fps || 30;
    const mod = ev.ctrlKey || ev.metaKey;
    if (mod && ev.key.toLowerCase() === 'z') {
      ev.preventDefault();
      return ev.shiftKey ? st.redo() : st.undo();
    }
    if (mod && ev.key.toLowerCase() === 's') { ev.preventDefault(); return save(); }
    if (mod && ev.key.toLowerCase() === 'r') { ev.preventDefault(); return startRender(false); }
    if (mod) return;
    switch (ev.key) {
      case ' ': ev.preventDefault(); ST.player.toggle(); break;
      case 'ArrowLeft': ev.preventDefault();
        ST.player.seek(S.t - (ev.shiftKey ? 1 : 1 / fps)); break;
      case 'ArrowRight': ev.preventDefault();
        ST.player.seek(S.t + (ev.shiftKey ? 1 : 1 / fps)); break;
      case 'Home': ST.player.seek(0); break;
      case 'End': ST.player.seek(S.total); break;
      case ',': gotoClip(-1); break;
      case '.': gotoClip(1); break;
      case 'Delete': case 'Backspace': ev.preventDefault(); delSelected(); break;
      case 'Escape': st.select(null); ST.player.paint(); break;
      case '+': case '=': ST.timeline.setZoom(S.pps * 1.3); break;
      case '-': ST.timeline.setZoom(S.pps / 1.3); break;
      default: break;
    }
    const k = ev.key.toLowerCase();
    if (k === 'v') setMode('select');
    else if (k === 'z') setMode('frame');
    else if (k === 's') {
      const clip = st.clipAt(S.t);
      if (clip) ST.timeline.splitAtPlayhead(clip.seg);
    } else if (k === 'd') {
      const clip = st.clipAt(S.t);
      if (clip) {
        st.push();
        st.segOf(clip.seg).enabled = false;
        st.resolve(); renderAll();
      }
    } else if (k === 't') {
      ST.library.addText('titulo', S.t);
    } else if (k === 'b') {
      startRender(true);
    }
  }

  /* --------------------------------------------------------------- arranque */

  async function main() {
    let warns = [];
    try {
      warns = await st.boot();
    } catch (e) {
      $('bootMsg').textContent = 'No pude cargar el proyecto: ' + e.message;
      return;
    }
    $('boot').classList.add('hidden');
    $('app').classList.remove('hidden');

    ST.player.bind();
    ST.timeline.bind();
    ST.library.bind();
    ST.inspector.render();
    renderAll();
    if (!S.clips.length) toast('No hay clips encendidos. Encendé alguno en el editor de cortes.', 'bad');
    else if (warns.length) toast(warns[0], 'bad');

    $('btnPlay').onclick = () => ST.player.toggle();
    $('btnHome').onclick = () => ST.player.seek(0);
    $('btnEnd').onclick = () => ST.player.seek(S.total);
    $('btnPrev').onclick = () => gotoClip(-1);
    $('btnNext').onclick = () => gotoClip(1);
    $('btnBackFrame').onclick = () => ST.player.seek(S.t - 1 / (S.tl.canvas.fps || 30));
    $('btnForwardFrame').onclick = () => ST.player.seek(S.t + 1 / (S.tl.canvas.fps || 30));
    $('btnCutLeft').onclick = () => ST.timeline.trimAtPlayhead('left');
    $('btnSplit').onclick = () => {
      const clip = st.clipAt(S.t);
      if (clip) ST.timeline.splitAtPlayhead(clip.seg);
    };
    $('btnCutRight').onclick = () => ST.timeline.trimAtPlayhead('right');
    $('btnSave').onclick = save;
    $('btnUndo').onclick = () => st.undo();
    $('btnRedo').onclick = () => st.redo();
    $('btnRender').onclick = () => startRender(false);
    $('btnDraft').onclick = () => startRender(true);
    $('tlZoom').oninput = (ev) => ST.timeline.setZoom(+ev.target.value);
    $('chkGuides').onchange = (ev) => { S.guides = ev.target.checked; ST.player.paint(); };
    $('chkSafe').onchange = (ev) => { S.safe = ev.target.checked; ST.player.paint(); };
    $('chkTikTok').onchange = (ev) => { S.tiktokUi = ev.target.checked; ST.player.paint(); };
    $('chkAudio').onchange = (ev) => { S.audio = ev.target.checked; ST.player.seek(S.t); };
    for (const b of document.querySelectorAll('#modeSeg button')) {
      b.onclick = () => setMode(b.dataset.mode);
    }
    $('rmCancel').onclick = async () => {
      if (curJob) await post('/api/render/' + curJob + '/cancel');
      $('renderModal').classList.add('hidden');
    };
    $('rmClose').onclick = () => $('renderModal').classList.add('hidden');
    document.addEventListener('keydown', keys);
    window.addEventListener('beforeunload', (ev) => {
      if (S.dirty) { ev.preventDefault(); ev.returnValue = ''; }
    });
  }

  return { main, toast, menu, renderAll, onTime, onSelect, setMode, save,
           reload, rewrap, regenSubs, relayout, startRender, post };
})();

document.addEventListener('DOMContentLoaded', ST.app.main);
