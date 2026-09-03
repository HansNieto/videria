/* Inspector: el panel cambia segun lo seleccionado (clip, texto, overlay,
   audio, transicion) y, sin seleccion, muestra los ajustes del proyecto. */
window.ST = window.ST || {};

ST.inspector = (() => {
  'use strict';
  const S = ST.S;
  const st = ST.state;
  const clamp = st.clamp;
  let body, head, kfSel = -1;

  const el = (tag, cls, txt) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (txt != null) n.textContent = txt;
    return n;
  };

  /* ------------------------------------------------------------ controles */

  function grp(title, extra) {
    const g = el('div', 'grp');
    if (title) {
      const h = el('h4', null, title);
      if (extra) { h.appendChild(el('div', 'spacer')); h.appendChild(extra); }
      g.appendChild(h);
    }
    return g;
  }

  function field(label, node, wide) {
    const f = el('div', 'f' + (wide ? ' wide' : ''));
    if (label) f.appendChild(el('label', null, label));
    f.appendChild(node);
    return f;
  }

  function slider(label, val, min, max, step, fmt, onInput) {
    const pair = el('div', 'pair');
    const r = el('input');
    r.type = 'range'; r.min = min; r.max = max; r.step = step; r.value = val;
    const v = el('span', 'val', fmt(val));
    r.oninput = () => { v.textContent = fmt(+r.value); onInput(+r.value, false); };
    r.onchange = () => onInput(+r.value, true);
    pair.appendChild(r); pair.appendChild(v);
    const f = field(label, pair);
    f._set = (x) => { r.value = x; v.textContent = fmt(+x); };
    return f;
  }

  function select(label, opts, val, onChange) {
    const s = el('select');
    for (const o of opts) {
      const op = el('option', null, o.label);
      op.value = o.value;
      s.appendChild(op);
    }
    s.value = val == null ? '' : String(val);
    s.onchange = () => onChange(s.value);
    return field(label, s);
  }

  function colorSlider(key, label, val, min, max, step, onInput) {
    const pair = el('div', 'pair color-pair');
    const range = el('input'), number = el('input');
    range.type = 'range'; number.type = 'number';
    for (const i of [range, number]) {
      i.min = min; i.max = max; i.step = step; i.value = val;
      i.setAttribute('aria-label', label + (i === number ? ' (valor)' : ' (barra)'));
      i.dataset.colorKey = key;
    }
    let changing = false, current = +val;
    const apply = (raw, syncNumber = true) => {
      if (raw.trim() === '' || !Number.isFinite(Number(raw))) return false;
      const v = +clamp(Number(raw), min, max).toFixed(2);
      if (v !== current) {
        if (!changing) { st.push(); changing = true; }
        current = v; onInput(v);
      }
      range.value = v; if (syncNumber) number.value = v.toFixed(2);
      return true;
    };
    range.oninput = () => apply(range.value);
    range.onchange = () => { apply(range.value); changing = false; };
    number.oninput = () => apply(number.value, false);
    number.onchange = () => {
      if (!apply(number.value)) number.value = current.toFixed(2);
      changing = false;
    };
    number.onblur = () => { number.value = current.toFixed(2); changing = false; };
    number.onkeydown = (ev) => { if (ev.key === 'Enter') { ev.preventDefault(); number.blur(); } };
    pair.appendChild(range); pair.appendChild(number);
    return field(label, pair);
  }

  function num(label, val, step, onChange, min, max) {
    const i = el('input');
    i.type = 'number'; i.step = step; i.value = val;
    if (min != null) i.min = min;
    if (max != null) i.max = max;
    i.onchange = () => onChange(+i.value);
    const f = field(label, i);
    f._set = (x) => { i.value = x; };
    return f;
  }

  function color(label, val, onChange) {
    const wrapEl = el('div', 'pair');
    const c = el('input');
    c.type = 'color'; c.value = val || '#ffffff';
    const t = el('input');
    t.type = 'text'; t.value = val || '#ffffff';
    c.oninput = () => { t.value = c.value; onChange(c.value); };
    t.onchange = () => { c.value = t.value; onChange(t.value); };
    wrapEl.appendChild(c); wrapEl.appendChild(t);
    return field(label, wrapEl);
  }

  function chips(opts, val, onPick) {
    const c = el('div', 'chips');
    for (const o of opts) {
      const b = el('button', 'chip' + (String(o.value) === String(val) ? ' on' : ''), o.label);
      if (o.hint) b.title = o.hint;
      b.onclick = () => onPick(o.value);
      c.appendChild(b);
    }
    return c;
  }

  function buttons(list) {
    const d = el('div', 'btns');
    for (const [label, fn, hint] of list) {
      const b = el('button', null, label);
      if (hint) b.title = hint;
      b.onclick = fn;
      d.appendChild(b);
    }
    return d;
  }

  const commit = (rerenderTimeline) => {
    st.resolve();
    st.markDirty(true);
    ST.player.paint();
    if (rerenderTimeline !== false) ST.timeline.render();
  };

  /* ---------------------------------------------------------------- clip */

  function clipPanel(seg) {
    const clip = st.clipOf(seg);
    if (!clip) return el('div', 'note', 'Ese clip está apagado.');
    const cfg = st.clipCfg(seg);
    const frag = document.createDocumentFragment();
    const kfs = st.zoomKfs(cfg);

    // ---- zoom
    const gz = grp('Zoom y encuadre', (() => {
      const b = el('button', null, S.mode === 'frame' ? '✓ encuadrando' : 'encuadrar');
      b.title = 'Arrastrá sobre el preview para mover el encuadre y usá la rueda para acercar (Z)';
      b.onclick = () => ST.app.setMode(S.mode === 'frame' ? 'select' : 'frame');
      return b;
    })());
    gz.appendChild(el('p', 'note',
      'Los keyframes son en segundos desde el inicio del clip, así que sobreviven a un recorte. ' +
      'Escala 1 es el plano completo; 2 son píxeles reales del original.'));
    gz.appendChild(kfEditor(clip, kfs));
    gz.appendChild(el('div', 'lib-title', 'presets'));
    const pc = el('div', 'chips');
    for (const p of S.cat.zoom_presets) {
      const b = el('button', 'chip', p.label);
      b.title = p.hint;
      b.onclick = () => applyPreset(seg, p);
      pc.appendChild(b);
    }
    gz.appendChild(pc);
    gz.appendChild(buttons([
      ['Keyframe aquí', () => addKfHere(clip), 'Añade un keyframe en el cabezal con el valor actual'],
      ['Quitar zoom', () => { st.push(); st.setClip(seg, { zoom: null }); commit(); render(); }],
      ['A todos los clips', () => applyZoomToAll(seg),
       'Copia este zoom a todos los clips de la secuencia'],
    ]));
    frag.appendChild(gz);

    // ---- tiempo
    const gt = grp('Tiempo');
    gt.appendChild(slider('velocidad', cfg.speed, 0.25, 4, 0.05,
      (v) => v.toFixed(2) + '×', (v, done) => {
        if (done) st.push();
        st.setClip(seg, { speed: +v.toFixed(3) });
        commit();
        // Los tiempos de palabra se expresan en tiempo de salida: al cambiar
        // velocidad, regenerarlos evita que los subtitulos se adelanten o atrasen.
        if (done) ST.app.regenSubs([seg]);
      }));
    gt.appendChild(el('p', 'note', 'Duración: ' + clip.srcDur.toFixed(2) + 's de origen → ' +
      clip.dur.toFixed(2) + 's en la secuencia.'));
    gt.appendChild(buttons([
      ['Cortar aquí', () => ST.timeline.splitAtPlayhead(seg)],
      ['Apagar clip', () => {
        st.push();
        st.segOf(seg).enabled = false;
        st.resolve(); ST.app.renderAll();
      }],
    ]));
    frag.appendChild(gt);

    // ---- audio
    const ga = grp('Audio del clip');
    ga.appendChild(slider('volumen', cfg.volume, -30, 12, 0.5,
      (v) => (v > 0 ? '+' : '') + v.toFixed(1) + ' dB', (v, done) => {
        if (done) st.push();
        st.setClip(seg, { volume: v });
        commit(false);
      }));
    const mute = el('input'); mute.type = 'checkbox'; mute.checked = !!cfg.mute;
    mute.onchange = () => { st.push(); st.setClip(seg, { mute: mute.checked }); commit(); };
    ga.appendChild(field('silenciar', mute));
    frag.appendChild(ga);

    // ---- look
    const look = cfg.look || {};
    const gl = grp('Color · ajustes manuales');
    gl.appendChild(el('p', 'note', 'Sin corrección automática. Brillo 0, contraste 1, saturación 1, temperatura 0 y viñeta 0 conservan el color de origen.'));
    const enabled = el('input'); enabled.type = 'checkbox'; enabled.checked = cfg.look_enabled !== false;
    enabled.setAttribute('aria-label', 'Aplicar ajustes de color');
    enabled.onchange = () => { st.push(); st.setClip(seg, { look_enabled: enabled.checked }); commit(false); };
    gl.appendChild(field('aplicar ajustes', enabled));
    const lk = (key, label, min, max, step, dflt) =>
      colorSlider(key, label, look[key] != null ? look[key] : dflt, min, max, step,
        (v) => {
          const nl = Object.assign({}, st.clipCfg(seg).look || {});
          nl[key] = v;
          st.setClip(seg, { look: nl, look_enabled: true }); enabled.checked = true;
          commit(false);
        });
    gl.appendChild(lk('brightness', 'brillo', -0.4, 0.4, 0.01, 0, (v) => v.toFixed(2)));
    gl.appendChild(lk('contrast', 'contraste', 0.5, 2, 0.01, 1, (v) => v.toFixed(2)));
    gl.appendChild(lk('saturation', 'saturación', 0, 2.5, 0.01, 1, (v) => v.toFixed(2)));
    gl.appendChild(lk('temp', 'temperatura', -1, 1, 0.01, 0));
    gl.appendChild(lk('vignette', 'viñeta', 0, 1, 0.01, 0));
    gl.appendChild(buttons([['Restablecer color', () => {
      st.push(); st.setClip(seg, { look: {}, look_enabled: true }); commit(false); render();
    }, 'Vuelve a valores neutros solo en este clip; se puede deshacer con Ctrl+Z']]));
    const flip = el('input'); flip.type = 'checkbox'; flip.checked = !!cfg.flip;
    flip.onchange = () => { st.push(); st.setClip(seg, { flip: flip.checked }); commit(); };
    gl.appendChild(field('espejar', flip));
    gl.appendChild(select('encaje', [
      { value: '', label: 'heredar del proyecto' },
      { value: 'cover', label: 'llenar (recorta)' },
      { value: 'contain', label: 'caber (bandas)' },
    ], cfg.fit || '', (v) => {
      st.push(); st.setClip(seg, { fit: v || null }); commit();
    }));
    frag.appendChild(gl);

    // ---- transicion de entrada
    if (clip.index > 0) {
      const gtr = grp('Transición de entrada');
      const tr = st.transOf(seg);
      gtr.appendChild(tr ? transControls(seg, tr)
        : buttons([['Añadir transición', () => {
            st.push();
            const d = S.cat.transitions[0];
            st.setTransition(seg, { type: d.id, dur: d.dur, strength: 1 });
            commit(); render();
          }]]));
      frag.appendChild(gtr);
    }
    return frag;
  }

  /* --------------------------------------------- editor de keyframes de zoom */

  /* Son dos graficos. El de arriba es la linea de tiempo del clip: la escala en
     morado, el paneo en tenue, un punto por keyframe. El de abajo es la curva
     del tramo que llega al keyframe seleccionado, dibujada en el cuadrado
     unidad — x es el tiempo del tramo y `y` cuanto valor lleva recorrido —, con
     las dos manijas bezier. Una manija por encima de 1 se pasa de largo y
     vuelve; por debajo de 0, retrocede antes de arrancar. */

  const KF_PAD = 10;                     // margen vertical del grafico, en px
  const CV_PAD = 18;                     // margen del editor de curva
  const CV_MIN = -0.75, CV_MAX = 1.75;   // recorrido vertical: deja ver el sobrepico

  /* Bezier equivalente a cada nombre. Al agarrar una manija de un tramo que
     todavia usa una curva con nombre, se convierte por aca y no da un salto. */
  const NAMED_BEZ = {
    linear: [0, 0, 1, 1],
    in: [0.42, 0, 1, 1],
    out: [0, 0, 0.58, 1],
    inout: [0.42, 0, 0.58, 1],
    expo: [0.76, 0, 0.9, 0.2],
    back: [0.34, 1.56, 0.64, 1],
  };

  function bezOfKf(kf) {
    const e = (kf && kf.ease) || 'inout';
    if (e === 'hold') return null;
    return ST.player.bezOf(e) || NAMED_BEZ[e] || NAMED_BEZ.inout;
  }

  function easeLabel(e) {
    const bz = ST.player.bezOf(e);
    if (!bz) return e || 'inout';
    const c = (S.cat.ease_curves || []).find(
      (x) => x.bezier.every((v, i) => Math.abs(v - bz[i]) < 5e-3));
    return c ? c.label : 'curva';
  }

  function kfEditor(clip, kfs) {
    const ZMAX = S.cat.zmax || 2;
    const dur = Math.max(0.01, clip.dur);
    if (kfSel >= kfs.length) kfSel = kfs.length - 1;
    const wrapEl = document.createDocumentFragment();
    const boxEl = el('div', 'kf');
    const cv = el('canvas');
    boxEl.appendChild(cv);
    const head = el('div', 'kfhead');
    boxEl.appendChild(head);

    const yOf = (h, z) => h - KF_PAD -
      ((clamp(z, 1, ZMAX) - 1) / (ZMAX - 1)) * (h - 2 * KF_PAD);

    const draw = () => {
      const w = boxEl.clientWidth || 300, h = boxEl.clientHeight || 150;
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      cv.width = w * dpr; cv.height = h * dpr;
      const c = cv.getContext('2d');
      c.setTransform(dpr, 0, 0, dpr, 0, 0);
      c.clearRect(0, 0, w, h);

      c.strokeStyle = '#242c3c'; c.lineWidth = 1;
      for (let i = 0; i <= 4; i++) {
        const y = KF_PAD + ((h - 2 * KF_PAD) * i) / 4;
        c.beginPath(); c.moveTo(0, y + 0.5); c.lineTo(w, y + 0.5); c.stroke();
      }
      c.fillStyle = '#656e88'; c.font = '10px system-ui, sans-serif';
      c.fillText(ZMAX.toFixed(1) + '×', 4, KF_PAD - 2);
      c.fillText('1.0×', 4, h - 2);

      // paneo: -1..1 sobre todo el alto, para ver que se mueve junto al zoom
      c.setLineDash([3, 3]); c.lineWidth = 1;
      for (const [key, col] of [['x', '#3ba0ff'], ['y', '#f0a13a']]) {
        if (!kfs.some((k) => Math.abs(+k[key] || 0) > 0.002)) continue;
        c.strokeStyle = col + '80';
        c.beginPath();
        for (let x = 0; x <= w; x += 2) {
          const v = clamp(ST.player.pw(kfs, key, 0, (x / w) * dur), -1, 1);
          const y = h - KF_PAD - ((v + 1) / 2) * (h - 2 * KF_PAD);
          if (x === 0) c.moveTo(x, y); else c.lineTo(x, y);
        }
        c.stroke();
      }
      c.setLineDash([]);

      // escala
      const pts = [];
      for (let x = 0; x <= w; x += 2) {
        pts.push([x, yOf(h, ST.player.pw(kfs, 'scale', 1, (x / w) * dur))]);
      }
      c.beginPath();
      pts.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y)));
      c.lineTo(w, h); c.lineTo(0, h); c.closePath();
      c.fillStyle = 'rgba(139,92,246,0.13)'; c.fill();
      c.beginPath();
      pts.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y)));
      c.strokeStyle = '#8b5cf6'; c.lineWidth = 2; c.stroke();

      // el tramo seleccionado, resaltado
      if (kfSel > 0 && kfSel < kfs.length) {
        const t0 = clamp(+kfs[kfSel - 1].t || 0, 0, dur);
        const t1 = clamp(+kfs[kfSel].t || 0, 0, dur);
        let started = false;
        c.beginPath();
        for (const [x, y] of pts) {
          const t = (x / w) * dur;
          if (t < t0 || t > t1) continue;
          if (!started) { c.moveTo(x, y); started = true; } else c.lineTo(x, y);
        }
        c.strokeStyle = '#ffb454'; c.lineWidth = 2.5; c.stroke();
      }

      boxEl.querySelectorAll('.kfdot').forEach((d) => d.remove());
      kfs.forEach((kf, i) => {
        const t = clamp(+kf.t || 0, 0, dur);
        const d = el('div', 'kfdot' + (i === kfSel ? ' sel' : ''));
        d.style.left = ((t / dur) * 100) + '%';
        d.style.top = yOf(h, +kf.scale || 1) + 'px';
        d.title = t.toFixed(2) + 's · ' + (+kf.scale || 1).toFixed(2) + '× · ' +
          (i ? easeLabel(kf.ease) : 'inicio');
        d.onmousedown = (ev) => startKfDrag(ev, clip, kfs, i, boxEl, ZMAX);
        boxEl.appendChild(d);
      });
      head.style.left = ((clamp(S.t - clip.t0, 0, dur) / dur) * 100) + '%';
    };

    boxEl.onclick = (ev) => {
      if (ev.target !== cv) return;
      const r = boxEl.getBoundingClientRect();
      const t = +(((ev.clientX - r.left) / r.width) * dur).toFixed(3);
      st.push();
      const cur = ST.player.zoomAt(clip, t);
      const slot = st.clipSlot(clip.seg);
      slot.zoom = slot.zoom || { kf: [] };
      slot.zoom.kf.push({ t, scale: +cur.z.toFixed(3),
                          x: +cur.px.toFixed(3), y: +cur.py.toFixed(3), ease: 'inout' });
      slot.zoom.kf.sort((a, b) => (+a.t || 0) - (+b.t || 0));
      kfSel = slot.zoom.kf.findIndex((k) => k.t === t);
      commit(); render();
    };

    requestAnimationFrame(draw);
    boxEl._draw = draw;
    wrapEl.appendChild(boxEl);

    if (kfSel > 0 && kfSel < kfs.length) wrapEl.appendChild(curvePanel(kfs, kfSel));

    const list = el('div', 'kflist');
    kfs.forEach((kf, i) => {
      const row = el('div', 'kfrow' + (i === kfSel ? ' sel' : ''));
      const t = el('input'); t.type = 'number'; t.step = '0.05'; t.value = (+kf.t || 0).toFixed(2);
      t.title = 'segundos desde el inicio del clip';
      t.onchange = () => {
        st.push(); kf.t = clamp(+t.value, 0, clip.dur); sortKf(clip.seg); commit(); render();
      };
      const z = el('input'); z.type = 'number'; z.step = '0.02'; z.min = 1; z.max = ZMAX;
      z.value = (+kf.scale || 1).toFixed(2);
      z.title = 'escala';
      z.onchange = () => { st.push(); kf.scale = clamp(+z.value, 1, ZMAX); commit(); render(); };
      const e = el('button', 'kfease', i ? easeLabel(kf.ease) : '—');
      e.title = i ? 'Curva de llegada a este keyframe. Clic para editarla.'
                  : 'El primer keyframe no tiene tramo de entrada.';
      e.disabled = !i;
      e.onclick = () => { kfSel = i; render(); };
      const del = el('button', null, '×');
      del.title = 'Quitar keyframe';
      del.onclick = () => {
        st.push();
        const slot = st.clipSlot(clip.seg);
        slot.zoom.kf.splice(i, 1);
        if (!slot.zoom.kf.length) slot.zoom = null;
        if (kfSel >= i) kfSel--;
        commit(); render();
      };
      row.appendChild(t); row.appendChild(z); row.appendChild(e); row.appendChild(del);
      row.onmousedown = (ev) => { if (ev.target === row) { kfSel = i; render(); } };
      list.appendChild(row);
    });
    if (kfs.length) wrapEl.appendChild(list);
    else wrapEl.appendChild(el('p', 'note',
      'Sin zoom. Clic en la curva para poner un keyframe, o elegí un preset.'));
    return wrapEl;
  }

  /* ------------------------------------------------ editor de curva bezier */

  function curvePanel(kfs, i) {
    const kf = kfs[i];
    const prev = kfs[i - 1];
    const hold = kf.ease === 'hold';
    const wrapEl = document.createDocumentFragment();

    const cap = el('div', 'kfcap');
    cap.appendChild(el('span', null, 'curva ' + (+prev.t || 0).toFixed(2) + 's → ' +
      (+kf.t || 0).toFixed(2) + 's'));
    const val = el('span', 'kfval');
    cap.appendChild(val);
    wrapEl.appendChild(cap);

    const boxEl = el('div', 'kfcurve');
    const cv = el('canvas');
    boxEl.appendChild(cv);
    wrapEl.appendChild(boxEl);

    const geom = () => {
      const w = boxEl.clientWidth || 260, h = boxEl.clientHeight || 130;
      return {
        w, h,
        X: (p) => CV_PAD + p * (w - 2 * CV_PAD),
        Y: (v) => h - CV_PAD - ((v - CV_MIN) / (CV_MAX - CV_MIN)) * (h - 2 * CV_PAD),
        toP: (px) => clamp((px - CV_PAD) / Math.max(1, w - 2 * CV_PAD), 0, 1),
        toV: (py) => clamp(CV_MIN + ((h - CV_PAD - py) / Math.max(1, h - 2 * CV_PAD)) *
          (CV_MAX - CV_MIN), CV_MIN, CV_MAX),
      };
    };

    const draw = () => {
      const g = geom();
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      cv.width = g.w * dpr; cv.height = g.h * dpr;
      const c = cv.getContext('2d');
      c.setTransform(dpr, 0, 0, dpr, 0, 0);
      c.clearRect(0, 0, g.w, g.h);

      // el cuadrado unidad: de "todavia no arranco" a "ya llego"
      c.strokeStyle = '#242c3c'; c.lineWidth = 1;
      c.strokeRect(g.X(0) + 0.5, g.Y(1) + 0.5, g.X(1) - g.X(0), g.Y(0) - g.Y(1));
      c.fillStyle = '#656e88'; c.font = '10px system-ui, sans-serif';
      c.fillText('llega', 3, g.Y(1) - 3);
      c.fillText('sale', 3, g.Y(0) + 11);

      const bz = bezOfKf(kf);
      c.strokeStyle = hold ? '#656e88' : '#8b5cf6'; c.lineWidth = 2;
      c.beginPath();
      if (hold) {
        c.moveTo(g.X(0), g.Y(0)); c.lineTo(g.X(1), g.Y(0)); c.lineTo(g.X(1), g.Y(1));
      } else {
        for (let s = 0; s <= 64; s++) {
          const u = s / 64;
          const x = g.X(ST.player.bez1(bz[0], bz[2], u));
          const y = g.Y(ST.player.bez1(bz[1], bz[3], u));
          if (!s) c.moveTo(x, y); else c.lineTo(x, y);
        }
      }
      c.stroke();

      boxEl.querySelectorAll('.kfh').forEach((d) => d.remove());
      if (hold) { val.textContent = 'salto seco'; return; }
      val.textContent = bz.map((v) => v.toFixed(2)).join(', ');
      [[0, 0, bz[0], bz[1]], [1, 1, bz[2], bz[3]]].forEach(([ax, ay, hx, hy], n) => {
        c.strokeStyle = 'rgba(255,180,84,0.55)'; c.lineWidth = 1;
        c.beginPath(); c.moveTo(g.X(ax), g.Y(ay)); c.lineTo(g.X(hx), g.Y(hy)); c.stroke();
        c.fillStyle = '#8b5cf6';
        c.beginPath(); c.arc(g.X(ax), g.Y(ay), 3.5, 0, 7); c.fill();
        const d = el('div', 'kfh');
        d.style.left = g.X(hx) + 'px';
        d.style.top = g.Y(hy) + 'px';
        d.title = 'manija ' + (n ? 'de llegada' : 'de salida');
        d.onmousedown = (ev) => startHandleDrag(ev, kf, n, boxEl, geom, draw);
        boxEl.appendChild(d);
      });
    };

    requestAnimationFrame(draw);
    boxEl._draw = draw;

    const opts = (S.cat.ease_curves || []).map((c) => ({
      value: 'bez:' + c.id, label: c.label, hint: c.hint,
    }));
    opts.unshift({ value: 'linear', label: 'Recta', hint: 'Velocidad constante.' });
    opts.push({ value: 'hold', label: 'Salto', hint: 'Se queda quieto y salta al llegar.' });
    let cur = '';
    if (hold) cur = 'hold';
    else if (kf.ease === 'linear') cur = 'linear';
    else {
      const bz = ST.player.bezOf(kf.ease);
      const c = bz && (S.cat.ease_curves || []).find(
        (x) => x.bezier.every((v, k) => Math.abs(v - bz[k]) < 5e-3));
      if (c) cur = 'bez:' + c.id;
    }
    wrapEl.appendChild(chips(opts, cur, (v) => {
      st.push();
      if (v === 'hold' || v === 'linear') kf.ease = v;
      else {
        const c = (S.cat.ease_curves || []).find((x) => 'bez:' + x.id === v);
        kf.ease = { bezier: c.bezier.slice() };
      }
      commit(); render();
    }));
    wrapEl.appendChild(el('p', 'note',
      'Arrastrá las manijas para dibujar la curva. Por arriba del cuadro el zoom se ' +
      'pasa de largo y vuelve; por debajo retrocede antes de arrancar, pero nunca ' +
      'baja de 1× porque ahí ya se ve el plano entero.'));
    return wrapEl;
  }

  function startHandleDrag(ev, kf, n, boxEl, geom, draw) {
    ev.preventDefault();
    ev.stopPropagation();
    const bz = bezOfKf(kf).slice();
    const r = boxEl.getBoundingClientRect();
    let pushed = false;
    const move = (e) => {
      if (!pushed) { st.push(); pushed = true; }
      const g = geom();
      bz[n * 2] = +g.toP(e.clientX - r.left).toFixed(3);
      bz[n * 2 + 1] = +g.toV(e.clientY - r.top).toFixed(3);
      kf.ease = { bezier: bz.slice() };
      st.resolve();
      ST.player.paint();
      draw();
      const graph = body.querySelector('.kf');
      if (graph && graph._draw) graph._draw();
    };
    const up = () => {
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
      if (pushed) { commit(); render(); }
    };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
  }

  function sortKf(seg) {
    const slot = st.clipSlot(seg);
    if (slot.zoom && slot.zoom.kf) slot.zoom.kf.sort((a, b) => (+a.t || 0) - (+b.t || 0));
  }

  function startKfDrag(ev, clip, kfs, i, boxEl, ZMAX) {
    ev.preventDefault();
    ev.stopPropagation();
    // El primer clic solo selecciona: asi aparece la curva de su tramo sin que
    // el punto se mueva de donde estaba.
    const reselect = kfSel !== i;
    kfSel = i;
    let pushed = false;
    const r = boxEl.getBoundingClientRect();
    const move = (e) => {
      if (!pushed) { st.push(); pushed = true; }
      const kf = kfs[i];
      kf.t = +clamp(((e.clientX - r.left) / r.width) * clip.dur, 0, clip.dur).toFixed(3);
      const p = 1 - clamp((e.clientY - r.top - KF_PAD) / (r.height - 2 * KF_PAD), 0, 1);
      kf.scale = +(1 + p * (ZMAX - 1)).toFixed(3);
      st.resolve();
      ST.player.paint();
      if (boxEl._draw) boxEl._draw();
    };
    const up = () => {
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
      // Sin arrastre fue un clic para seleccionar: solo hay que repintar el
      // panel para que aparezca la curva de su tramo.
      if (!pushed) { if (reselect) render(); return; }
      sortKf(clip.seg);
      commit(); render();
    };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
  }

  function applyPreset(seg, preset) {
    const clip = st.clipOf(seg);
    if (!clip) return;
    st.push();
    const kf = preset.kf.map((k) => ({
      t: +(k.t != null ? k.t : (k.tf || 0) * clip.dur).toFixed(3),
      scale: k.scale != null ? k.scale : 1,
      x: k.x || 0, y: k.y || 0, ease: k.ease || 'inout',
    }));
    st.setClip(seg, { zoom: { kf, preset: preset.id } });
    commit(); render();
  }

  function applyZoomToAll(seg) {
    const src = st.clipCfg(seg).zoom;
    if (!src) return ST.app.toast('Este clip no tiene zoom', 'bad');
    const base = st.clipOf(seg);
    st.push();
    let n = 0;
    for (const c of S.clips) {
      if (c.seg === seg) continue;
      // Los keyframes se reescalan a la duracion del clip destino: si no, en
      // un clip corto el zoom no llegaria a moverse.
      const k = c.dur / Math.max(0.01, base.dur);
      st.setClip(c.seg, {
        zoom: {
          kf: src.kf.map((x) => Object.assign({}, x, { t: +((+x.t || 0) * k).toFixed(3) })),
          preset: src.preset,
        },
      });
      n++;
    }
    commit(); render();
    ST.app.toast('Zoom copiado a ' + n + ' clips');
  }

  function addKfHere(clip) {
    const rel = clamp(S.t - clip.t0, 0, clip.dur);
    st.push();
    const cur = ST.player.zoomAt(clip, rel);
    const slot = st.clipSlot(clip.seg);
    slot.zoom = slot.zoom || { kf: [] };
    slot.zoom.kf.push({ t: +rel.toFixed(3), scale: +cur.z.toFixed(3),
                        x: +cur.px.toFixed(3), y: +cur.py.toFixed(3), ease: 'inout' });
    sortKf(clip.seg);
    commit(); render();
  }

  /* ----------------------------------------------------------- transicion */

  function transControls(seg, tr) {
    const frag = document.createDocumentFragment();
    const cat = S.cat.transitions;
    frag.appendChild(chips(cat.map((c) => ({ value: c.id, label: c.label, hint: c.hint })),
      tr.type, (v) => {
        st.push();
        const spec = cat.find((c) => c.id === v);
        st.setTransition(seg, { type: v, dur: spec.dur });
        commit(); render();
      }));
    const spec = cat.find((c) => c.id === tr.type) || {};
    if (spec.hint) frag.appendChild(el('p', 'note', spec.hint));
    frag.appendChild(slider('duración', +tr.dur || 0.3, 0.08, 1.2, 0.02,
      (v) => v.toFixed(2) + ' s', (v, done) => {
        if (done) st.push();
        st.setTransition(seg, { dur: v });
        commit();
      }));
    frag.appendChild(slider('fuerza', tr.strength != null ? +tr.strength : 1, 0.2, 2, 0.05,
      (v) => v.toFixed(2), (v, done) => {
        if (done) st.push();
        st.setTransition(seg, { strength: v });
        commit();
      }));
    const sfxName = tr.sfx ? String(tr.sfx).split(/[\\/]/).pop() : '(ninguno)';
    frag.appendChild(field('sonido', el('span', 'muted', sfxName)));
    frag.appendChild(buttons([
      ['Sonido sugerido', () => addSuggestedSfx(seg, spec)],
      ['Quitar', () => { st.push(); st.delTransition(seg); commit(); render(); }],
    ]));
    frag.appendChild(el('p', 'note',
      'Las transiciones no consumen tiempo: son un golpe centrado en el corte, ' +
      'así que nada de lo que viene después se descoloca.'));
    return frag;
  }

  function addSuggestedSfx(seg, spec) {
    if (!spec.sfx) return ST.app.toast('Esta transición no lleva sonido');
    const lib = (S.cat.library.sfx || []);
    const hit = lib.find((f) => f.name === spec.sfx) || lib.find((f) => f.name.includes(spec.sfx.split('_')[1] || ''));
    if (!hit) return ST.app.toast('No encontré ' + spec.sfx + ' en la librería', 'bad');
    st.push();
    st.setTransition(seg, { sfx: hit.path, sfx_gain: -5 });
    const clip = st.clipOf(seg);
    st.addItem('t_sfx', {
      kind: 'audio', src: hit.path, dur: 1.0, gain: -4,
      anchor: { seg, offset: -0.07, clamp: false },
    });
    commit(); render();
  }

  /* ---------------------------------------------------------------- texto */

  function textPanel(item) {
    const style = st.styleOf(item);
    const { it } = st.findItem(item.id);
    const frag = document.createDocumentFragment();

    const gc = grp('Contenido');
    const ta = el('textarea');
    ta.id = 'inspText';
    ta.value = (it.lines || []).map((l) => l.map((w) => w.w).join(' ')).join(' ');
    ta.rows = 3;
    ta.onchange = async () => {
      st.push();
      await ST.app.rewrap(it, ta.value);
      commit(); render();
    };
    gc.appendChild(field(null, ta, true));
    const kw = el('input');
    kw.type = 'text';
    kw.placeholder = 'palabra a resaltar';
    kw.value = (it.lines || []).flat().filter((w) => w.key).map((w) => w.w).join(' ');
    kw.onchange = async () => {
      st.push();
      await ST.app.rewrap(it, null, kw.value.trim());
      commit(); render();
    };
    gc.appendChild(field('resaltar', kw));
    gc.appendChild(select('estilo', Object.entries(S.tl.styles).map(([k, v]) =>
      ({ value: k, label: v.name || k })), it.style || 'capcut', async (v) => {
        st.push(); it.style = v; await ST.app.rewrap(it); commit(); render();
      }));
    gc.appendChild(select('revelado', [
      { value: '', label: 'según el estilo (' + (style.reveal || 'none') + ')' },
      { value: 'word', label: 'palabra por palabra' },
      { value: 'none', label: 'todo de golpe' },
    ], it.reveal || '', (v) => { st.push(); it.reveal = v || null; commit(); }));
    frag.appendChild(gc);

    const gp = grp('Posición y tamaño');
    const bx = it.x != null ? it.x : (style.box || {}).x;
    const by = it.y != null ? it.y : (style.box || {}).y;
    gp.appendChild(slider('x', bx, 0, 1, 0.005, (v) => (v * 100).toFixed(1) + '%',
      (v, done) => { if (done) st.push(); it.x = +v.toFixed(4); commit(false); }));
    gp.appendChild(slider('y', by, 0, 1, 0.005, (v) => (v * 100).toFixed(1) + '%',
      (v, done) => { if (done) st.push(); it.y = +v.toFixed(4); commit(false); }));
    gp.appendChild(slider('cuerpo', ovr(it, style, 'size'), 24, 200, 1,
      (v) => Math.round(v) + ' px', async (v, done) => {
        if (done) { st.push(); setOvr(it, 'size', Math.round(v)); await ST.app.rewrap(it); commit(); }
        else { setOvr(it, 'size', Math.round(v)); commit(false); }
      }));
    gp.appendChild(buttons([
      ['Centrar', () => { st.push(); it.x = 0.5; commit(); }],
      ['Arriba', () => { st.push(); it.y = 0.14; commit(); }],
      ['Medio', () => { st.push(); it.y = 0.45; commit(); }],
      ['Abajo', () => { st.push(); it.y = 0.66; commit(); }],
      ['Como el estilo', () => { st.push(); it.x = null; it.y = null; commit(); }],
    ]));
    frag.appendChild(gp);

    const gf = grp('Tipografía');
    gf.appendChild(fontSelect('fuente', ovr(it, style, 'font'), async (v) => {
      st.push(); setOvr(it, 'font', v);
      await ST.text.ensureFont(v);
      await ST.app.rewrap(it); commit();
    }));
    gf.appendChild(color('color', ovr(it, style, 'color'), (v) => {
      setOvr(it, 'color', v); commit(false);
    }));
    gf.appendChild(fontSelect('fuente clave', ovr(it, style, 'keyword_font'), async (v) => {
      st.push(); setOvr(it, 'keyword_font', v);
      await ST.text.ensureFont(v);
      await ST.app.rewrap(it); commit();
    }));
    gf.appendChild(color('color clave', ovr(it, style, 'keyword_color'), (v) => {
      setOvr(it, 'keyword_color', v); commit(false);
    }));
    gf.appendChild(slider('interlínea', ovr(it, style, 'line_height'), 0.8, 2, 0.01,
      (v) => v.toFixed(2), (v, done) => {
        if (done) st.push(); setOvr(it, 'line_height', v); commit(false);
      }));
    frag.appendChild(gf);

    const gs = grp('Sombra y contorno');
    const sh = style.shadow || {};
    const shSet = (key, v) => {
      const cur = Object.assign({}, (it.override || {}).shadow || {});
      cur[key] = v;
      setOvr(it, 'shadow', cur);
      commit(false);
    };
    gs.appendChild(slider('opacidad', +sh.opacity || 0, 0, 255, 5,
      (v) => Math.round((v / 255) * 100) + '%', (v, done) => { if (done) st.push(); shSet('opacity', Math.round(v)); }));
    gs.appendChild(slider('difusión', +sh.blur || 0, 0, 40, 1,
      (v) => v.toFixed(0), (v, done) => { if (done) st.push(); shSet('blur', v); }));
    gs.appendChild(slider('desplaz. Y', +sh.dy || 0, -30, 30, 1,
      (v) => v.toFixed(0), (v, done) => { if (done) st.push(); shSet('dy', v); }));
    gs.appendChild(slider('contorno', ovr(it, style, 'outline') || 0, 0, 12, 0.5,
      (v) => v.toFixed(1), (v, done) => { if (done) st.push(); setOvr(it, 'outline', v); commit(false); }));
    frag.appendChild(gs);

    const ga = grp('Animación');
    const anims = Object.keys(S.cat.anims).map((a) => ({ value: a, label: a }));
    ga.appendChild(select('entrada', anims, it.anim_in || style.anim_in || 'none',
      (v) => { st.push(); it.anim_in = v; commit(false); }));
    ga.appendChild(select('salida', anims, it.anim_out || style.anim_out || 'none',
      (v) => { st.push(); it.anim_out = v; commit(false); }));
    ga.appendChild(slider('duración', it.anim_dur != null ? it.anim_dur : (style.anim_dur || 0.22),
      0.05, 1, 0.01, (v) => v.toFixed(2) + ' s',
      (v, done) => { if (done) st.push(); it.anim_dur = v; commit(false); }));
    frag.appendChild(ga);

    frag.appendChild(timingGroup(it, item));
    frag.appendChild(buttons([
      ['Borrar texto', () => { st.push(); st.delItem(item.id); commit(); render(); }],
    ]));
    return frag;
  }

  const ovr = (it, style, key) => {
    const o = it.override || {};
    return o[key] != null ? o[key] : style[key];
  };

  function setOvr(it, key, val) {
    it.override = it.override || {};
    it.override[key] = val;
  }

  function fontSelect(label, val, onChange) {
    const s = el('select');
    for (const f of S.cat.fonts) {
      const o = el('option', null, f.label + '  (' + f.file + ')');
      o.value = f.file;
      s.appendChild(o);
    }
    if (val && !S.cat.fonts.some((f) => f.file === val)) {
      const o = el('option', null, val); o.value = val; s.appendChild(o);
    }
    s.value = val || '';
    s.onchange = () => onChange(s.value);
    return field(label, s);
  }

  /* ------------------------------------------------------- overlay / audio */

  function overlayPanel(item) {
    const { it } = st.findItem(item.id);
    const frag = document.createDocumentFragment();
    const g = grp('Overlay');
    g.appendChild(field('archivo', el('span', 'muted',
      (it.src || '').split(/[\\/]/).pop() || '—')));
    if (it.seq) {
      g.appendChild(el('p', 'note',
        'Tiene la secuencia de PNG detrás, así que el render conserva la ' +
        'transparencia. El WebM es sólo para verlo acá.'));
    } else if (/\.webm$/i.test(it.src || '')) {
      g.appendChild(el('p', 'warn',
        'WebM sin secuencia: se verá bien acá pero el render le pondrá un ' +
        'fondo negro. Convertilo con: vcut overlays --project …'));
    }
    g.appendChild(slider('escala', +it.scale || 1, 0.05, 3, 0.01,
      (v) => (v * 100).toFixed(0) + '%',
      (v, done) => { if (done) st.push(); it.scale = v; commit(false); }));
    g.appendChild(slider('opacidad', it.opacity != null ? +it.opacity : 1, 0, 1, 0.01,
      (v) => (v * 100).toFixed(0) + '%',
      (v, done) => { if (done) st.push(); it.opacity = v; commit(false); }));
    g.appendChild(slider('x', it.x != null ? +it.x : 0.5, 0, 1, 0.005,
      (v) => (v * 100).toFixed(1) + '%',
      (v, done) => { if (done) st.push(); it.x = v; commit(false); }));
    g.appendChild(slider('y', it.y != null ? +it.y : 0.5, 0, 1, 0.005,
      (v) => (v * 100).toFixed(1) + '%',
      (v, done) => { if (done) st.push(); it.y = v; commit(false); }));
    g.appendChild(slider('fundido', +it.fade || 0, 0, 1.5, 0.02,
      (v) => v.toFixed(2) + ' s',
      (v, done) => { if (done) st.push(); it.fade = v; commit(false); }));
    const lp = el('input'); lp.type = 'checkbox'; lp.checked = !!it.loop;
    lp.onchange = () => { st.push(); it.loop = lp.checked; commit(); };
    g.appendChild(field('repetir', lp));
    frag.appendChild(g);
    frag.appendChild(timingGroup(it, item));
    frag.appendChild(buttons([
      ['Borrar overlay', () => { st.push(); st.delItem(item.id); commit(); render(); }],
    ]));
    return frag;
  }

  function audioPanel(item) {
    const { it, trk } = st.findItem(item.id);
    const frag = document.createDocumentFragment();
    const g = grp('Audio');
    g.appendChild(field('archivo', el('span', 'muted',
      (it.src || '').split(/[\\/]/).pop() || '—')));
    g.appendChild(slider('ganancia', +it.gain || 0, -40, 12, 0.5,
      (v) => (v > 0 ? '+' : '') + v.toFixed(1) + ' dB',
      (v, done) => { if (done) st.push(); it.gain = v; commit(false); }));
    g.appendChild(num('desde (s)', +it.in || 0, 0.1, (v) => {
      st.push(); it.in = Math.max(0, v); commit();
    }, 0));
    g.appendChild(slider('fundido entra', +it.fade_in || 0, 0, 5, 0.1,
      (v) => v.toFixed(1) + ' s',
      (v, done) => { if (done) st.push(); it.fade_in = v; commit(false); }));
    g.appendChild(slider('fundido sale', +it.fade_out || 0, 0, 5, 0.1,
      (v) => v.toFixed(1) + ' s',
      (v, done) => { if (done) st.push(); it.fade_out = v; commit(false); }));
    const lp = el('input'); lp.type = 'checkbox'; lp.checked = !!it.loop;
    lp.onchange = () => { st.push(); it.loop = lp.checked; commit(); };
    g.appendChild(field('repetir', lp));
    frag.appendChild(g);

    const gt = grp('Pista: ' + (trk.name || trk.id));
    gt.appendChild(slider('ganancia pista', +trk.gain || 0, -40, 12, 0.5,
      (v) => (v > 0 ? '+' : '') + v.toFixed(1) + ' dB',
      (v, done) => { if (done) st.push(); trk.gain = v; commit(false); }));
    const dk = el('input'); dk.type = 'checkbox'; dk.checked = !!trk.duck;
    dk.onchange = () => { st.push(); trk.duck = dk.checked; commit(); };
    gt.appendChild(field('bajar bajo la voz', dk));
    gt.appendChild(el('p', 'note',
      'El ducking usa la voz de los clips como referencia: la música baja sola ' +
      'cuando alguien habla y vuelve cuando calla.'));
    frag.appendChild(gt);

    frag.appendChild(timingGroup(it, item));
    frag.appendChild(buttons([
      ['Borrar', () => { st.push(); st.delItem(item.id); commit(); render(); }],
    ]));
    return frag;
  }

  function timingGroup(it, resolved) {
    const g = grp('Tiempos');
    g.appendChild(field('empieza', el('span', 'muted', resolved.t.toFixed(2) + ' s')));
    g.appendChild(num('duración', +it.dur || 0, 0.05, (v) => {
      st.push(); it.dur = Math.max(0.1, v); commit();
    }, 0.1));
    if (resolved.track === 't_sub') {
      g.appendChild(slider('velocidad', +it.subtitle_speed || 1, 0.5, 2, 0.05,
        (v) => v.toFixed(2) + '×', (v, done) => {
          if (done) st.push();
          const oldRate = +it.subtitle_speed || 1;
          const oldDur = Math.max(0.1, +it.dur || resolved.dur || 0.1);
          let newDur = oldDur * oldRate / Math.max(0.01, v);
          const next = S.items.filter((x) => x.track === 't_sub' && x.id !== it.id &&
                                      x.t >= resolved.t + 0.001)
            .sort((a, b) => a.t - b.t)[0];
          if (next) newDur = Math.min(newDur, Math.max(0.1, next.t - resolved.t));
          const ratio = newDur / oldDur;
          for (const ln of it.lines || []) {
            for (const w of ln) {
              w.s = +((+w.s || 0) * ratio).toFixed(3);
              w.e = +((+w.e || 0) * ratio).toFixed(3);
            }
          }
          it.dur = +newDur.toFixed(3);
          it.subtitle_speed = +(oldRate / ratio).toFixed(3);
          it.auto = false;
          commit();
        }));
      g.appendChild(el('p', 'note',
        'Acelera o ralentiza el revelado de palabras sin invadir el siguiente subtítulo.'));
    }
    const anchored = !!it.anchor;
    const a = el('input'); a.type = 'checkbox'; a.checked = anchored;
    a.title = 'Anclado a un clip: si el clip se mueve o se recorta, esto lo sigue';
    a.onchange = () => {
      st.push();
      if (a.checked) it.anchor = st.anchorAt(resolved.t);
      else { it.t = resolved.t; it.anchor = null; }
      commit(); render();
    };
    g.appendChild(field('anclado', a));
    if (anchored) {
      g.appendChild(el('p', 'note', 'Ancla: ' + it.anchor.seg + ' + ' +
        (+it.anchor.offset || 0).toFixed(2) + ' s'));
    }
    g.appendChild(buttons([
      ['Empezar aquí', () => {
        st.push();
        if (it.anchor) it.anchor = st.anchorAt(S.t);
        else it.t = +S.t.toFixed(3);
        commit(); render();
      }],
      ['Terminar aquí', () => {
        st.push();
        it.dur = +Math.max(0.1, S.t - resolved.t).toFixed(3);
        commit(); render();
      }],
    ]));
    return g;
  }

  /* -------------------------------------------------------------- proyecto */

  function projectPanel() {
    const frag = document.createDocumentFragment();
    const cvs = S.tl.canvas;
    const g = grp('Lienzo');
    g.appendChild(field('tamaño', el('span', 'muted', cvs.width + ' × ' + cvs.height)));
    g.appendChild(select('formato', [
      { value: '1080x1920', label: '9:16 vertical  1080×1920' },
      { value: '1080x1350', label: '4:5 retrato  1080×1350' },
      { value: '1080x1080', label: '1:1 cuadrado  1080×1080' },
      { value: '1920x1080', label: '16:9 apaisado  1920×1080' },
    ], cvs.width + 'x' + cvs.height, (v) => {
      const [w, h] = v.split('x').map(Number);
      st.push();
      cvs.width = w; cvs.height = h;
      ST.player.layout(); commit();
      ST.app.toast('Revisá la posición de los textos: el lienzo cambió');
    }));
    g.appendChild(num('fps', cvs.fps, 1, (v) => {
      st.push(); cvs.fps = clamp(v, 12, 60); commit();
    }, 12, 60));
    g.appendChild(color('fondo', cvs.bg || '#000000', (v) => { cvs.bg = v; commit(false); }));
    frag.appendChild(g);

    const r = S.tl.render;
    const gr = grp('Render');
    gr.appendChild(select('codificador', [
      { value: 'auto', label: 'auto' + (S.cat.nvenc === false ? '' : ' (usa la GPU si puede)') },
      { value: 'nvenc', label: 'NVIDIA nvenc' },
      { value: 'x264', label: 'CPU libx264' },
    ], r.encoder, (v) => { st.push(); r.encoder = v; commit(false); }));
    gr.appendChild(slider('calidad', r.quality, 14, 32, 1,
      (v) => 'crf ' + v + (v <= 18 ? ' (alta)' : (v >= 26 ? ' (baja)' : '')),
      (v, done) => { if (done) st.push(); r.quality = v; commit(false); }));
    gr.appendChild(select('encaje', [
      { value: 'cover', label: 'llenar (recorta)' },
      { value: 'contain', label: 'caber (bandas)' },
    ], r.fit, (v) => { st.push(); r.fit = v; commit(); }));
    const ln = el('input'); ln.type = 'checkbox'; ln.checked = !!r.loudnorm;
    ln.onchange = () => { st.push(); r.loudnorm = ln.checked; commit(false); };
    gr.appendChild(field('normalizar audio', ln));
    gr.appendChild(el('p', 'note',
      'La normalización deja el audio a ' + (r.loudnorm_i || -14) +
      ' LUFS, que es lo que piden las redes. Se salta en los borradores.'));
    frag.appendChild(gr);

    const gs = grp('Subtítulos');
    gs.appendChild(el('p', 'note',
      'Se generan desde la transcripción y quedan anclados a su clip. ' +
      'Regenerar borra los automáticos, no los que editaste a mano.'));
    gs.appendChild(buttons([
      ['Regenerar todos', () => ST.app.regenSubs(null)],
      ['Sin palabra clave', () => ST.app.regenSubs(null, { no_keywords: true })],
      ['Re-partir líneas', () => ST.app.relayout()],
    ]));
    frag.appendChild(gs);

    const st2 = grp('Estilos de texto');
    for (const [key, sv] of Object.entries(S.tl.styles)) {
      const row = el('div', 'card');
      row.draggable = false;
      row.style.cursor = 'default';
      row.appendChild(el('b', null, sv.name || key));
      row.appendChild(el('i', null, sv.font + ' · ' + sv.size + 'px · ' +
        (sv.max_lines || 1) + ' líneas'));
      row.onclick = () => editStyle(key);
      row.style.cursor = 'pointer';
      st2.appendChild(row);
    }
    frag.appendChild(st2);

    const gi = grp('Proyecto');
    const stt = S.project.stats || {};
    gi.appendChild(el('p', 'note',
      (stt.segments_enabled || 0) + ' clips encendidos de ' + (stt.segments_total || 0) +
      ' · ' + (S.total).toFixed(1) + ' s de secuencia · ' +
      S.items.length + ' items en las pistas.'));
    gi.appendChild(buttons([
      ['Abrir carpeta', () => fetch('/api/reveal', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: (S.project._paths || {}).exports }),
      })],
      ['Limpiar huérfanos', async () => {
        const r = await fetch('/api/timeline/gc', { method: 'POST' }).then((x) => x.json());
        ST.app.toast('Quitados ' + r.removed + ' elementos huérfanos');
        await ST.app.reload();
      }],
    ]));
    frag.appendChild(gi);
    return frag;
  }

  function editStyle(key) {
    const sv = S.tl.styles[key];
    body.textContent = '';
    head.textContent = '';
    head.appendChild(el('span', 'tag', 'estilo'));
    head.appendChild(el('span', null, sv.name || key));
    const back = el('button', 'ghost', '← volver');
    back.onclick = () => render();
    body.appendChild(back);
    const g = grp('Aplica a todos los textos con este estilo');
    const set = async (k, v, rewrap) => {
      st.push();
      sv[k] = v;
      if (rewrap) await ST.app.relayout(key);
      commit();
    };
    g.appendChild(fontSelect('fuente', sv.font, async (v) => {
      await ST.text.ensureFont(v); await set('font', v, true);
      editStyle(key);
    }));
    g.appendChild(slider('cuerpo', sv.size, 24, 220, 1, (v) => Math.round(v) + ' px',
      async (v, done) => { if (done) await set('size', Math.round(v), true); }));
    g.appendChild(color('color', sv.color, (v) => set('color', v)));
    g.appendChild(fontSelect('fuente clave', sv.keyword_font, async (v) => {
      await ST.text.ensureFont(v); await set('keyword_font', v, true);
      editStyle(key);
    }));
    g.appendChild(color('color clave', sv.keyword_color, (v) => set('keyword_color', v)));
    g.appendChild(slider('clave ×', sv.keyword_size_ratio, 0.8, 2.2, 0.05,
      (v) => v.toFixed(2) + '×', async (v, done) => { if (done) await set('keyword_size_ratio', v, true); }));
    g.appendChild(slider('interlínea', sv.line_height, 0.8, 2, 0.01, (v) => v.toFixed(2),
      (v, done) => { if (done) set('line_height', v); }));
    g.appendChild(num('líneas máx', sv.max_lines, 1, (v) => set('max_lines', clamp(v, 1, 6), true), 1, 6));
    g.appendChild(num('palabras/línea', sv.max_words_line || 4, 1,
      (v) => set('max_words_line', clamp(v, 1, 10), true), 1, 10));
    g.appendChild(slider('ancho caja', (sv.box || {}).w || 0.86, 0.3, 1, 0.01,
      (v) => (v * 100).toFixed(0) + '%', async (v, done) => {
        if (done) { sv.box = Object.assign({}, sv.box, { w: v }); await set('box', sv.box, true); }
      }));
    g.appendChild(slider('y', (sv.box || {}).y || 0.66, 0, 1, 0.005,
      (v) => (v * 100).toFixed(1) + '%', (v, done) => {
        sv.box = Object.assign({}, sv.box, { y: v });
        if (done) st.push();
        commit(false);
      }));
    const sk = el('input'); sk.type = 'checkbox'; sk.checked = !!sv.stack_only_with_keyword;
    sk.title = 'Con esto, el apilado de líneas sólo ocurre en las tarjetas que tienen palabra resaltada';
    sk.onchange = () => set('stack_only_with_keyword', sk.checked);
    g.appendChild(field('apilar sólo con clave', sk));
    body.appendChild(g);
  }

  /* ---------------------------------------------------------------- render */

  function render() {
    body = body || document.getElementById('inspBody');
    head = head || document.getElementById('inspHead');
    body.textContent = '';
    head.textContent = '';
    const sel = S.sel;
    if (!sel) {
      head.appendChild(el('span', 'tag', 'proyecto'));
      head.appendChild(el('span', null, S.project.name || 'sin nombre'));
      body.appendChild(projectPanel());
      return;
    }
    if (sel.kind === 'clip') {
      const clip = st.clipOf(sel.id);
      head.appendChild(el('span', 'tag', 'clip'));
      head.appendChild(el('span', null, clip
        ? ((S.sources[clip.source] || {}).name || sel.id) : sel.id));
      body.appendChild(clipPanel(sel.id));
      return;
    }
    if (sel.kind === 'trans') {
      const tr = st.transOf(sel.id);
      head.appendChild(el('span', 'tag', 'transición'));
      head.appendChild(el('span', null, 'en el corte de ' + sel.id));
      if (!tr) { body.appendChild(el('p', 'note', 'Sin transición en este corte.')); return; }
      body.appendChild(transControls(sel.id, tr));
      return;
    }
    const item = S.items.find((x) => x.id === sel.id);
    if (!item) { S.sel = null; return render(); }
    head.appendChild(el('span', 'tag', item.track_kind === 'text' ? 'texto'
      : (item.track_kind === 'overlay' ? 'overlay' : 'audio')));
    head.appendChild(el('span', null, item.id));
    if (item.track_kind === 'text') body.appendChild(textPanel(item));
    else if (item.track_kind === 'overlay') body.appendChild(overlayPanel(item));
    else body.appendChild(audioPanel(item));
  }

  /* Actualiza lo que cambia al arrastrar sobre el preview, sin reconstruir el
     panel (reconstruirlo mataria el foco y el arrastre). */
  function refreshValues() {
    if (!body) return;
    body.querySelectorAll('.kf, .kfcurve').forEach((n) => { if (n._draw) n._draw(); });
  }

  function focusText(id) {
    st.select('item', id);
    render();
    const ta = document.getElementById('inspText');
    if (ta) { ta.focus(); ta.select(); }
  }

  return { render, refreshValues, focusText };
})();
