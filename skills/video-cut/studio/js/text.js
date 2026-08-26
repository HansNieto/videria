/* Texto en canvas: el espejo exacto de assbuild.py.
   Las dos implementaciones tienen que decidir lo mismo (donde parte la linea,
   donde cae cada linea, cuando aparece cada palabra) porque una dibuja el
   preview y la otra el render. Cuando toques una, toca la otra.
   Las curvas de animacion NO se duplican: llegan de /api/catalog. */
window.ST = window.ST || {};

ST.text = (() => {
  'use strict';

  const SREF = 1080;
  const REVEAL_FADE = 0.07;         // igual que assbuild.REVEAL_FADE

  const mc = document.createElement('canvas').getContext('2d');
  const loaded = new Set();
  const pending = new Map();
  let ANIM = { none: [] };

  const famOf = (file) => 'vc_' + String(file || 'x').replace(/[^\w]+/g, '_');
  const cssFont = (file, px) => px.toFixed(2) + 'px "' + famOf(file) + '",system-ui,sans-serif';

  function setAnims(anims) { ANIM = anims || ANIM; }

  /* Registra el .ttf real que va a usar el render, no una familia parecida:
     si el navegador midiera con otra fuente, el reparto en lineas del preview
     dejaria de coincidir con el del ASS. */
  function ensureFont(file) {
    if (!file || loaded.has(file)) return Promise.resolve();
    if (pending.has(file)) return pending.get(file);
    const fam = famOf(file);
    const ff = new FontFace(fam, 'url(/api/font/' + encodeURIComponent(file) + ')');
    const p = ff.load().then((f) => {
      document.fonts.add(f);
      loaded.add(file);
    }).catch(() => { loaded.add(file); });
    pending.set(file, p);
    return p;
  }

  function fontsOf(tl) {
    const out = new Set();
    for (const st of Object.values(tl.styles || {})) {
      if (st.font) out.add(st.font);
      if (st.keyword_font) out.add(st.keyword_font);
    }
    for (const trk of tl.tracks || []) {
      for (const it of trk.items || []) {
        const ov = it.override || {};
        if (ov.font) out.add(ov.font);
        if (ov.keyword_font) out.add(ov.keyword_font);
      }
    }
    return [...out];
  }

  const preload = (tl) => Promise.all(fontsOf(tl).map(ensureFont));

  /* ------------------------------------------------------------ medidas */

  function sizes(style, W) {
    const k = W / SREF;
    const size = (+style.size || 80) * k;
    return {
      k, size,
      spacing: (+style.letter_spacing || 0) * k,
      ratio: +style.keyword_size_ratio || 1,
      lh: +style.line_height || 1.16,
    };
  }

  function wordW(word, file, px, spacing) {
    mc.font = cssFont(file, px);
    let w = mc.measureText(word).width;
    if (spacing) w += spacing * Math.max(0, word.length - 1);
    return w;
  }

  function spaceW(file, px) {
    mc.font = cssFont(file, px);
    return mc.measureText(' ').width;
  }

  function metrics(lines, style, W) {
    const s = sizes(style, W);
    const kfont = style.keyword_font || style.font;
    const sw = spaceW(style.font, s.size);
    const out = [];
    let total = 0;
    for (const ln of lines) {
      let w = 0, big = s.size;
      ln.forEach((word, j) => {
        const isK = !!word.key;
        w += wordW(word.w, isK ? kfont : style.font,
                   isK ? s.size * s.ratio : s.size, s.spacing) + (j ? sw : 0);
        if (isK) big = Math.max(big, s.size * s.ratio);
      });
      const h = big * s.lh;
      out.push({ w, h, size: big });
      total += h;
    }
    return { lines: out, total_h: total, size: s.size, space_w: sw };
  }

  /* Mismo reparto que textlayer.wrap. Sirve mientras se escribe; al confirmar,
     el servidor vuelve a partir con las metricas del .ttf y manda su version. */
  function wrap(words, style, W, keyIdx) {
    const s = sizes(style, W);
    const kfont = style.keyword_font || style.font;
    const maxW = (+(style.box && style.box.w) || 0.86) * W;
    const maxWords = +style.max_words_line || 4;
    const maxChars = +style.max_chars_line || 22;
    const sw = spaceW(style.font, s.size);
    const lines = [];
    let cur = [], curW = 0, curC = 0;
    words.forEach((word, i) => {
      const txt = (word.w || '').trim();
      if (!txt) return;
      const isK = keyIdx != null && i === keyIdx;
      const ww = wordW(txt, isK ? kfont : style.font,
                       isK ? s.size * s.ratio : s.size, s.spacing);
      let add = ww + (cur.length ? sw : 0);
      if (cur.length && (curW + add > maxW || cur.length >= maxWords ||
                         curC + 1 + txt.length > maxChars)) {
        lines.push(cur); cur = []; curW = 0; curC = 0; add = ww;
      }
      cur.push({ w: txt, s: word.s, e: word.e, key: isK });
      curW += add;
      curC += txt.length + (curC ? 1 : 0);
    });
    if (cur.length) lines.push(cur);
    return lines;
  }

  /* ------------------------------------------------------------ geometria */

  function geom(item, style, W, H, m) {
    const box = style.box || {};
    const bx = item.x != null ? +item.x : (box.x != null ? +box.x : 0.5);
    const by = item.y != null ? +item.y : (box.y != null ? +box.y : 0.66);
    const align = style.align || 'center';
    const bw = (+box.w || 0.86) * W;
    let an = 8, ax = bx * W;
    if (align === 'left') { an = 7; ax = bx * W - bw / 2; }
    else if (align === 'right') { an = 9; ax = bx * W + bw / 2; }
    const ys = [];
    let acc = 0;
    for (const l of m.lines) { ys.push(by * H + acc); acc += l.h; }
    return { an, ax, ys };
  }

  const lerp = (a, b, p) => a + (b - a) * p;

  function sampleAnim(kfs, p) {
    const st = { s: 1, a: 1, dx: 0, dy: 0 };
    if (!kfs || !kfs.length) return st;
    p = Math.max(0, Math.min(1, p));
    let prev = kfs[0];
    for (const cur of kfs) {
      if (p <= cur[0]) {
        const span = cur[0] - prev[0];
        const q = span <= 1e-6 ? 0 : (p - prev[0]) / span;
        for (const k of ['s', 'a', 'dx', 'dy']) {
          const a = prev[1][k] != null ? prev[1][k] : st[k];
          const b = cur[1][k] != null ? cur[1][k] : a;
          st[k] = lerp(a, b, q);
        }
        return st;
      }
      prev = cur;
    }
    const last = kfs[kfs.length - 1][1];
    for (const k of ['s', 'a', 'dx', 'dy']) if (last[k] != null) st[k] = last[k];
    return st;
  }

  function kfsFor(kind, out) {
    const kfs = ANIM[kind || 'none'] || [];
    if (!kfs.length) return kfs;
    if (!out) return kfs;
    return kfs.slice().reverse().map(([p, v]) => [1 - p, v]);
  }

  /* Estado de la animacion que le toca a un tramo. base = cuando aparecio la
     linea (en el apilado cada linea entra por su cuenta). */
  function animAt(rel, dur, base, dIn, dOut, aIn, aOut) {
    const t = rel - base;
    if (aIn !== 'none' && dIn > 0.01 && t < dIn) {
      return sampleAnim(kfsFor(aIn), t / dIn);
    }
    if (aOut !== 'none' && dOut > 0.01 && rel > dur - dOut) {
      return sampleAnim(kfsFor(aOut, true), (rel - (dur - dOut)) / dOut);
    }
    return { s: 1, a: 1, dx: 0, dy: 0 };
  }

  /* ------------------------------------------------------------ dibujo */

  function draw(ctx, item, style, W, H, rel) {
    const lines = item.lines || [];
    if (!lines.length) return null;
    const s = sizes(style, W);
    const m = metrics(lines, style, W);
    const g = geom(item, style, W, H, m);
    const reveal = item.reveal || style.reveal || 'none';
    const dur = +item.dur || 0;
    const aIn = item.anim_in || style.anim_in || 'none';
    const aOut = item.anim_out || style.anim_out || 'none';
    const ad = +(item.anim_dur != null ? item.anim_dur : style.anim_dur) || 0.22;
    const dIn = Math.min(ad, dur * 0.5), dOut = Math.min(ad, dur * 0.5);
    const kfont = style.keyword_font || style.font;
    const sh = style.shadow || {};
    const shOp = +sh.opacity || 0;
    const bg = style.bg || {};

    const bounds = { x0: 1e9, y0: 1e9, x1: -1e9, y1: -1e9 };

    if (+bg.opacity > 0) {
      const pad = (+bg.pad || 0) * s.k;
      const bw = Math.max(...m.lines.map((l) => l.w)) + pad * 2;
      const bh = m.total_h + pad * 2;
      const x0 = g.an === 7 ? g.ax - pad : (g.an === 9 ? g.ax - bw + pad : g.ax - bw / 2);
      ctx.save();
      ctx.globalAlpha = (+bg.opacity) / 255;
      ctx.fillStyle = bg.color || '#fff';
      ctx.fillRect(x0, g.ys[0] - pad, bw, bh);
      ctx.restore();
    }

    lines.forEach((ln, li) => {
      const nWords = ln.length;
      const base = reveal === 'word' ? (+ln[0].s || 0) : 0;
      if (reveal === 'word' && rel < base - 1e-6) return;

      const a = animAt(rel, dur, base, dIn, dOut, aIn, aOut);
      const lm = m.lines[li];
      const cy = g.ys[li];
      const x = g.an === 7 ? g.ax : (g.an === 9 ? g.ax - lm.w : g.ax - lm.w / 2);
      const cx = g.ax;
      // Una sola linea base para toda la fila: si cada palabra usara la suya,
      // la clave a 1,5x quedaria flotando respecto al resto. libass alinea por
      // la linea base de la fuente mas grande de la fila.
      const hasKey = ln.some((w) => w.key);
      mc.font = cssFont(hasKey ? kfont : style.font, lm.size);
      const lineAsc = mc.measureText('Hg').fontBoundingBoxAscent || lm.size * 0.8;
      const by = cy + lineAsc;

      // Las transformaciones se aplican sobre el ancla, igual que \an8 + \pos.
      const drawPass = (shadow) => {
        ctx.save();
        ctx.translate(cx + a.dx * W, cy + a.dy * H);
        if (Math.abs(a.s - 1) > 1e-4) ctx.scale(a.s, a.s);
        ctx.translate(-cx, -cy);
        if (shadow) {
          ctx.filter = 'blur(' + ((+sh.blur || 0) * s.k).toFixed(2) + 'px)';
          ctx.translate((+sh.dx || 0) * s.k, (+sh.dy || 0) * s.k);
        }
        ctx.textAlign = 'left';
        ctx.textBaseline = 'alphabetic';
        let wx = x;
        ln.forEach((word, j) => {
          const isK = !!word.key;
          const px = isK ? s.size * s.ratio : s.size;
          const file = isK ? kfont : style.font;
          ctx.font = cssFont(file, px);
          let al = 1;
          if (reveal === 'word') {
            const ws = +word.s || 0;
            al = rel < ws ? 0 : Math.min(1, (rel - ws) / REVEAL_FADE);
          }
          if (al > 0.002) {
            const mm = ctx.measureText(word.w);
            ctx.globalAlpha = al * (shadow ? shOp / 255 : a.a);
            ctx.fillStyle = shadow ? (sh.color || '#000')
                                   : (isK ? (style.keyword_color || '#4A90E0')
                                          : (style.color || '#fff'));
            if (!shadow && +style.outline > 0) {
              ctx.lineWidth = (+style.outline) * s.k * 2;
              ctx.strokeStyle = style.outline_color || '#000';
              ctx.lineJoin = 'round';
              ctx.strokeText(word.w, wx, by);
            }
            ctx.fillText(word.w, wx, by);
            if (!shadow) {
              bounds.x0 = Math.min(bounds.x0, wx);
              bounds.x1 = Math.max(bounds.x1, wx + mm.width);
              bounds.y0 = Math.min(bounds.y0, cy);
              bounds.y1 = Math.max(bounds.y1, cy + lm.h);
            }
          }
          wx += wordW(word.w, file, px, s.spacing) + (j < nWords - 1 ? m.space_w : 0);
        });
        ctx.restore();
      };

      if (shOp > 0) drawPass(true);
      drawPass(false);
    });
    ctx.filter = 'none';
    ctx.globalAlpha = 1;
    if (bounds.x1 < bounds.x0) return null;
    return bounds;
  }

  /* Caja aproximada de un item, para saber si un clic cae encima. */
  function hitBox(item, style, W, H) {
    const lines = item.lines || [];
    if (!lines.length) return null;
    const m = metrics(lines, style, W);
    const g = geom(item, style, W, H, m);
    const w = Math.max(...m.lines.map((l) => l.w));
    const x0 = g.an === 7 ? g.ax : (g.an === 9 ? g.ax - w : g.ax - w / 2);
    return { x0, y0: g.ys[0], x1: x0 + w, y1: g.ys[0] + m.total_h };
  }

  return { setAnims, ensureFont, preload, cssFont, famOf, metrics, wrap, geom,
           draw, hitBox, sampleAnim, kfsFor, sizes, SREF };
})();
