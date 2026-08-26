/* Librería: tarjetas arrastrables a la timeline (o clic para aplicar a lo
   seleccionado). Es el único sitio donde se crean items nuevos. */
window.ST = window.ST || {};

ST.library = (() => {
  'use strict';
  const S = ST.S;
  const st = ST.state;
  let tab = 'zoom';
  let bodyEl;
  let audition = null;
  const filters = {};

  const el = (tag, cls, txt) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (txt != null) n.textContent = txt;
    return n;
  };

  function card(title, hint, payload, onClick, extra) {
    const c = el('div', 'card');
    c.draggable = true;
    const row = el('div', 'row');
    row.appendChild(el('b', null, title));
    if (extra) row.appendChild(extra);
    c.appendChild(row);
    if (hint) c.appendChild(el('i', null, hint));
    c.ondragstart = (ev) => {
      ev.dataTransfer.setData('text/plain', JSON.stringify(payload));
      ev.dataTransfer.effectAllowed = 'copy';
      c.classList.add('drag');
    };
    c.ondragend = () => c.classList.remove('drag');
    if (onClick) c.onclick = onClick;
    return c;
  }

  function search(key, placeholder, onInput) {
    const i = el('input', 'lib-search');
    i.type = 'search';
    i.placeholder = placeholder;
    i.value = filters[key] || '';
    i.oninput = () => { filters[key] = i.value; onInput(i.value); };
    return i;
  }

  /* ------------------------------------------------------------- paneles */

  function zoomPanel() {
    const f = document.createDocumentFragment();
    f.appendChild(el('div', 'lib-title', 'zooms'));
    f.appendChild(el('p', 'lib-hint',
      'Arrastrá sobre un clip, o clic para aplicarlo al clip seleccionado. ' +
      'Después se ajusta keyframe a keyframe en el inspector.'));
    for (const p of S.cat.zoom_presets) {
      f.appendChild(card(p.label, p.hint, { type: 'zoom_preset', id: p.id },
        () => applyZoom(selectedSeg(), p.id)));
    }
    f.appendChild(el('div', 'lib-title', 'aplicar a'));
    f.appendChild(card('Todos los clips', 'Reparte el zoom del clip seleccionado por toda la secuencia',
      { type: 'noop' }, () => {
        const seg = selectedSeg();
        if (!seg) return ST.app.toast('Seleccioná un clip primero', 'bad');
        st.select('clip', seg);
        ST.inspector.render();
        ST.app.toast('Usá "A todos los clips" en el inspector');
      }));
    f.appendChild(card('Quitar el zoom de todo', 'Deja todos los clips con el plano completo',
      { type: 'noop' }, () => {
        st.push();
        for (const c of S.clips) st.setClip(c.seg, { zoom: null });
        st.resolve(); ST.app.renderAll();
      }));
    return f;
  }

  function transPanel() {
    const f = document.createDocumentFragment();
    f.appendChild(el('div', 'lib-title', 'transiciones'));
    f.appendChild(el('p', 'lib-hint',
      'Arrastrá sobre la pista de vídeo, cerca del corte donde la querés. ' +
      'No consumen tiempo: son un golpe en el corte.'));
    for (const t of S.cat.transitions) {
      const extra = el('button', 'play', t.sfx ? '♪' : '');
      if (t.sfx) {
        extra.title = 'Escuchar ' + t.sfx;
        extra.onclick = (ev) => {
          ev.stopPropagation();
          const hit = (S.cat.library.sfx || []).find((x) => x.name === t.sfx);
          if (hit) audit(hit.path);
        };
      }
      f.appendChild(card(t.label, t.hint, { type: 'transition', id: t.id },
        () => applyTrans(selectedSeg(), t.id), extra));
    }
    f.appendChild(el('div', 'lib-title', 'en bloque'));
    f.appendChild(card('En todos los cortes', 'Pone la misma transición en cada corte de la secuencia',
      { type: 'noop' }, () => bulkTrans()));
    f.appendChild(card('Quitar todas', null, { type: 'noop' }, () => {
      st.push();
      S.tl.transitions = [];
      st.resolve(); ST.app.renderAll();
    }));
    return f;
  }

  function textPanel() {
    const f = document.createDocumentFragment();
    f.appendChild(el('div', 'lib-title', 'texto nuevo'));
    f.appendChild(el('p', 'lib-hint',
      'Arrastralo a una pista de texto, o clic para ponerlo en el cabezal.'));
    for (const [key, sv] of Object.entries(S.tl.styles)) {
      f.appendChild(card(sv.name || key,
        sv.font + ' · ' + sv.size + 'px' + (sv.reveal === 'word' ? ' · palabra a palabra' : ''),
        { type: 'text', style: key },
        () => addText(key, S.t)));
    }
    f.appendChild(el('div', 'lib-title', 'subtítulos'));
    f.appendChild(card('Regenerar desde la transcripción',
      'Vuelve a crear las tarjetas automáticas; respeta las que editaste',
      { type: 'noop' }, () => ST.app.regenSubs(null)));
    f.appendChild(card('Re-partir líneas',
      'Recalcula dónde parte cada línea con la tipografía actual',
      { type: 'noop' }, () => ST.app.relayout()));
    return f;
  }

  function assetPanel(cat, rowHint) {
    const f = document.createDocumentFragment();
    const list = (S.cat.library[cat] || []);
    f.appendChild(search(cat, 'Buscar…', () => render()));
    f.appendChild(el('p', 'lib-hint', rowHint));
    const q = (filters[cat] || '').toLowerCase();
    const shown = list.filter((x) => !q || x.name.toLowerCase().includes(q) ||
                                     x.dir.toLowerCase().includes(q));
    if (!shown.length) {
      f.appendChild(el('p', 'lib-hint', list.length
        ? 'Nada coincide con la búsqueda.'
        : 'No encontré archivos. Poné los tuyos en una carpeta del proyecto ' +
          'llamada assets, musica o transiciones.'));
    }
    for (const a of shown.slice(0, 140)) {
      const extra = el('button', 'play', a.kind === 'audio' ? '▶' : '◱');
      extra.title = a.kind === 'audio' ? 'Escuchar' : a.path;
      extra.onclick = (ev) => {
        ev.stopPropagation();
        if (a.kind === 'audio') audit(a.path);
      };
      const meta = a.dur ? a.dir + ' · ' + a.dur.toFixed(2) + ' s'
        : a.dir + ' · ' + (a.size / 1024 > 999
          ? (a.size / 1048576).toFixed(1) + ' MB'
          : Math.round(a.size / 1024) + ' kB');
      f.appendChild(card(a.name, meta,
        { type: 'asset', path: a.path, kind: a.kind, cat,
          seq: a.seq || null, dur: a.dur || null },
        () => addAsset(a, cat, S.t), extra));
    }
    return f;
  }

  function audit(path) {
    if (audition) { audition.pause(); audition = null; }
    audition = new Audio('/api/asset?path=' + encodeURIComponent(path));
    audition.volume = 0.8;
    audition.play().catch(() => ST.app.toast('No pude reproducir ese archivo', 'bad'));
  }

  /* ------------------------------------------------------------- acciones */

  const selectedSeg = () => {
    if (S.sel && S.sel.kind === 'clip') return S.sel.id;
    const c = st.clipAt(S.t);
    return c ? c.seg : null;
  };

  function applyZoom(seg, presetId) {
    if (!seg) return ST.app.toast('No hay clip en el cabezal', 'bad');
    const preset = S.cat.zoom_presets.find((p) => p.id === presetId);
    const clip = st.clipOf(seg);
    if (!preset || !clip) return;
    st.push();
    st.setClip(seg, {
      zoom: {
        kf: preset.kf.map((k) => ({
          t: +(k.t != null ? k.t : (k.tf || 0) * clip.dur).toFixed(3),
          scale: k.scale != null ? k.scale : 1,
          x: k.x || 0, y: k.y || 0, ease: k.ease || 'inout',
        })),
        preset: preset.id,
      },
    });
    st.resolve();
    st.select('clip', seg);
    ST.app.renderAll();
    ST.app.toast(preset.label + ' → ' + ((S.sources[clip.source] || {}).name || seg));
  }

  function applyTrans(seg, typeId) {
    if (!seg) return ST.app.toast('No hay corte cerca del cabezal', 'bad');
    const clip = st.clipOf(seg);
    if (!clip || clip.index === 0) {
      return ST.app.toast('El primer clip no tiene corte de entrada', 'bad');
    }
    const spec = S.cat.transitions.find((t) => t.id === typeId);
    st.push();
    st.setTransition(seg, { type: typeId, dur: spec.dur, strength: 1 });
    st.resolve();
    st.select('trans', seg);
    ST.app.renderAll();
  }

  function bulkTrans() {
    const type = (S.sel && S.sel.kind === 'trans' && (st.transOf(S.sel.id) || {}).type)
      || 'flash';
    const spec = S.cat.transitions.find((t) => t.id === type);
    st.push();
    for (const c of S.clips) {
      if (c.index === 0) continue;
      st.setTransition(c.seg, { type, dur: spec.dur, strength: 1 });
    }
    st.resolve();
    ST.app.renderAll();
    ST.app.toast(spec.label + ' en ' + Math.max(0, S.clips.length - 1) + ' cortes');
  }

  function addText(styleKey, t) {
    const style = S.tl.styles[styleKey] || {};
    st.push();
    const words = 'Texto nuevo'.split(' ').map((w, i) => ({ w, s: i * 0.25, e: i * 0.25 + 0.25 }));
    const it = st.addItem(styleKey === 'capcut' ? 't_sub' : 't_txt', {
      kind: 'text', style: styleKey, auto: false,
      anchor: st.anchorAt(t), dur: 2.2,
      lines: ST.text.wrap(words, style, S.tl.canvas.width, null),
      text: 'Texto nuevo', x: null, y: null,
    });
    st.resolve();
    ST.app.renderAll();
    if (it) ST.inspector.focusText(it.id);
  }

  function addAsset(a, cat, t) {
    st.push();
    let it;
    if (a.kind === 'audio') {
      const trackId = cat === 'sfx' ? 't_sfx' : 't_mus';
      it = st.addItem(trackId, {
        kind: 'audio', src: a.path, in: 0,
        gain: cat === 'sfx' ? -3 : 0,
        anchor: cat === 'sfx' ? st.anchorAt(t) : null,
        t: cat === 'sfx' ? undefined : +t.toFixed(3),
        dur: cat === 'sfx' ? 1.2 : Math.max(4, S.total - t),
        fade_in: cat === 'sfx' ? 0 : 1.2,
        fade_out: cat === 'sfx' ? 0 : 1.8,
        loop: cat !== 'sfx',
      });
    } else {
      const esVideo = /\.(webm|mp4|mkv|mov|gif)$/i.test(a.name);
      it = st.addItem('t_ovl', {
        kind: 'overlay', src: a.path, anchor: st.anchorAt(t),
        // Un motion graphic dura lo que dura su animación; un sticker, lo que
        // le pongas.
        dur: a.dur ? +a.dur.toFixed(2) : (esVideo ? 2.5 : 1.8),
        // `seq` es la secuencia de PNG: ffmpeg no lee el alfa del WebM, así que
        // sin esto el render pondría un rectángulo negro detrás.
        seq: a.seq || null,
        scale: cat === 'sticker' ? STICKER_SCALE : START_SCALE,
        opacity: 1, x: 0.5, y: cat === 'sticker' ? 0.3 : 0.42,
        fade: cat === 'sticker' ? 0.12 : 0.2,
        loop: esVideo && !a.dur,
      });
    }
    st.resolve();
    ST.app.renderAll();
    if (it) st.select('item', it.id);
  }

  /* Un PNG de 1080 de ancho no debe entrar al 100% en un lienzo de 1080: 0.6
     es un tamaño de overlay razonable del que partir. Los stickers vienen a
     1080 px de lado a propósito (para poder agrandarlos sin que pixelen), así
     que su punto de partida es mucho menor. */
  const START_SCALE = 0.6;
  const STICKER_SCALE = 0.28;

  function dropOn(rowId, t, payload) {
    if (!payload || !payload.type) return;
    if (payload.type === 'zoom_preset') {
      const clip = st.clipAt(t);
      return applyZoom(clip && clip.seg, payload.id);
    }
    if (payload.type === 'transition') {
      const clip = nearestCut(t);
      return applyTrans(clip && clip.seg, payload.id);
    }
    if (payload.type === 'text') {
      return addText(payload.style, t);
    }
    if (payload.type === 'asset') {
      // La pista decide la categoría, salvo los stickers: ésos van a la pista
      // de overlays pero conservan su tamaño y su fundido de sticker.
      let cat = payload.cat;
      if (rowId === 't_sfx') cat = 'sfx';
      else if (rowId === 't_mus') cat = 'musica';
      else if (rowId === 't_ovl' && cat !== 'sticker') cat = 'overlay';
      if ((cat === 'sfx' || cat === 'musica') && payload.kind !== 'audio') {
        return ST.app.toast('Eso no es un audio', 'bad');
      }
      if ((cat === 'overlay' || cat === 'sticker') && payload.kind === 'audio') {
        return ST.app.toast('Un audio no va en la pista de overlays', 'bad');
      }
      return addAsset({ path: payload.path, kind: payload.kind,
                        seq: payload.seq, dur: payload.dur,
                        name: payload.path.split(/[\\/]/).pop() }, cat, t);
    }
  }

  /* El corte mas cercano al punto donde se solto, no el clip: una transicion
     vive en un corte. */
  function nearestCut(t) {
    let best = null, bd = 1e9;
    for (const c of S.clips) {
      if (c.index === 0) continue;
      const d = Math.abs(c.t0 - t);
      if (d < bd) { bd = d; best = c; }
    }
    return best;
  }

  /* --------------------------------------------------------------- render */

  function render() {
    bodyEl = bodyEl || document.getElementById('libBody');
    bodyEl.textContent = '';
    if (tab === 'zoom') bodyEl.appendChild(zoomPanel());
    else if (tab === 'trans') bodyEl.appendChild(transPanel());
    else if (tab === 'text') bodyEl.appendChild(textPanel());
    else if (tab === 'sfx') {
      bodyEl.appendChild(el('div', 'lib-title', 'efectos de sonido'));
      bodyEl.appendChild(assetPanel('sfx', 'Arrastralos a la pista SFX. Suelen ir en el corte.'));
      bodyEl.appendChild(el('div', 'lib-title', 'música'));
      bodyEl.appendChild(assetPanel('musica',
        'A la pista Música. Baja sola bajo la voz si el ducking está activo.'));
    } else if (tab === 'ovl') {
      bodyEl.appendChild(el('div', 'lib-title', 'motion graphics'));
      bodyEl.appendChild(assetPanel('overlay',
        'Los que tienen duración vienen de una secuencia de PNG y conservan la ' +
        'transparencia en el render. Un .mov ProRes se verá en el render pero ' +
        'no en el preview del navegador.'));
    } else if (tab === 'stk') {
      bodyEl.appendChild(el('div', 'lib-title', 'stickers'));
      bodyEl.appendChild(assetPanel('sticker',
        'Flechas, resaltes, números y etiquetas. Se arrastran a la pista de ' +
        'overlays y se colocan moviéndolos sobre el preview.'));
    }
  }

  function bind() {
    for (const b of document.querySelectorAll('.lt')) {
      b.onclick = () => {
        tab = b.dataset.lib;
        for (const o of document.querySelectorAll('.lt')) o.classList.toggle('active', o === b);
        render();
      };
    }
    render();
  }

  return { bind, render, dropOn, addText, applyZoom, applyTrans };
})();
