/* Reproduccion y compositor del preview.
   Todo se dibuja en coordenadas del canvas del proyecto (p.ej. 1080x1920) y el
   contexto se escala al final. Asi el zoom, el texto y los overlays usan los
   mismos numeros que el render y no hay dos sistemas de coordenadas. */
window.ST = window.ST || {};

ST.player = (() => {
  'use strict';
  const S = ST.S;
  const st = ST.state;
  const MAX_VIDEOS = 6;

  const VID = Object.create(null);
  const ORDER = [];
  const OVL = Object.create(null);      // id -> {el, kind, ok}
  const AUD = Object.create(null);      // id -> HTMLAudioElement
  let cv, ctx, box, wrap, k = 1, dispW = 0, dispH = 0;
  let raf = 0, activeSid = null;
  let drag = null;

  const dbToLin = (db) => Math.pow(10, (+db || 0) / 20);
  const clamp = st.clamp;

  /* ---------------------------------------------------------------- easing */

  /* Las 4 manijas si `kind` es una curva bezier; null si es un nombre.
     Espejo de studio.ease_bezier. */
  function bezOf(kind) {
    let b = kind;
    if (b && typeof b === 'object' && !Array.isArray(b)) b = b.bezier || b.curve;
    if (typeof b === 'string') {
      const c = (S.cat.ease_curves || []).find((x) => x.id === b);
      b = c ? c.bezier : null;
    }
    if (!Array.isArray(b) || b.length !== 4) return null;
    const n = b.map(Number);
    if (n.some((v) => !isFinite(v))) return null;
    n[0] = clamp(n[0], 0, 1);
    n[2] = clamp(n[2], 0, 1);
    return n;
  }

  /* Coordenada de un bezier cubico con extremos en 0 y 1. */
  function bez1(a, b, u) {
    const m = 1 - u;
    return 3 * m * m * u * a + 3 * m * u * u * b + u * u * u;
  }

  /* Aca el bezier se resuelve exacto (Newton, con biseccion de respaldo);
     el render lo hornea en rectas. La diferencia es < 0,002 de escala. */
  function bezEase(p, bz) {
    const [x1, y1, x2, y2] = bz;
    if (Math.abs(x1 - y1) < 1e-4 && Math.abs(x2 - y2) < 1e-4) return p;
    let u = p;
    for (let i = 0; i < 5; i++) {
      const x = bez1(x1, x2, u) - p;
      if (Math.abs(x) < 1e-5) return bez1(y1, y2, u);
      const m = 1 - u;
      const d = 3 * m * m * x1 + 6 * m * u * (x2 - x1) + 3 * u * u * (1 - x2);
      if (Math.abs(d) < 1e-6) break;
      u = clamp(u - x / d, 0, 1);
    }
    let lo = 0, hi = 1;
    for (let i = 0; i < 24; i++) {
      u = (lo + hi) / 2;
      if (bez1(x1, x2, u) < p) lo = u; else hi = u;
    }
    return bez1(y1, y2, u);
  }

  /* Mismas curvas que render._ease: si difieren, el preview miente. */
  function ease(p, kind) {
    p = clamp(p, 0, 1);
    const bz = bezOf(kind);
    if (bz) return bezEase(p, bz);
    switch (kind) {
      case 'hold': return 0;
      case 'linear': return p;
      case 'in': return p * p;
      case 'out': return 1 - (1 - p) * (1 - p);
      case 'expo': return p <= 0 ? 0 : Math.pow(2, 10 * (p - 1));
      case 'back': return 1 + 2.70158 * Math.pow(p - 1, 3) + 1.70158 * Math.pow(p - 1, 2);
      default: return p < 0.5 ? 2 * p * p : 1 - 2 * (1 - p) * (1 - p);
    }
  }

  /* Espejo de render.piecewise: fuera de los extremos mantiene el valor. */
  function pw(kfs, key, dflt, t) {
    if (!kfs.length) return dflt;
    const val = (kf) => (kf[key] != null ? +kf[key] : dflt);
    if (t <= (+kfs[0].t || 0)) return val(kfs[0]);
    for (let i = 0; i < kfs.length - 1; i++) {
      const t0 = +kfs[i].t || 0, t1 = +kfs[i + 1].t || 0;
      if (t < t1) {
        if (t1 - t0 < 1e-6) continue;
        const p = ease((t - t0) / (t1 - t0), kfs[i + 1].ease || 'inout');
        return val(kfs[i]) + (val(kfs[i + 1]) - val(kfs[i])) * p;
      }
    }
    return val(kfs[kfs.length - 1]);
  }

  function zoomAt(clip, rel) {
    const kfs = st.zoomKfs(clip.cfg);
    if (!kfs.length) return { z: 1, px: 0, py: 0 };
    return {
      z: clamp(pw(kfs, 'scale', 1, rel), 1, S.cat.zmax || 2),
      px: clamp(pw(kfs, 'x', 0, rel), -1, 1),
      py: clamp(pw(kfs, 'y', 0, rel), -1, 1),
    };
  }

  /* Aporte de las transiciones geometricas, igual que render.geom_stage. */
  function transGeom(t) {
    let z = 0, px = 0, py = 0, flash = 0, blur = 0, pix = 0, glitch = 0, fade = 0;
    for (const tr of S.trans) {
      if (t < tr.t0 || t > tr.t1) continue;
      const d = tr.dur, s = clamp(tr.strength, 0.1, 2);
      const env = 1 - Math.abs((2 * (t - tr.t0)) / d - 1);
      switch (tr.type) {
        case 'punch_zoom': z += 0.22 * s * env; break;
        case 'shake':
          z += 0.09 * s * env;
          px += 0.55 * s * env * Math.sin((t - tr.t0) * 118);
          py += 0.45 * s * env * Math.sin((t - tr.t0) * 151);
          break;
        case 'whip': {
          const half = Math.max(1e-3, d / 2);
          z += 0.28 * s * Math.min(1, 6 * Math.min(t - tr.t0, tr.t1 - t) / d);
          px += t < tr.t ? 0.95 * s * ((t - tr.t0) / half)
                         : -0.95 * s * (1 - (t - tr.t) / half);
          break;
        }
        case 'flash': flash = Math.max(flash, 0.95 * s * env); break;
        case 'blur': blur = Math.max(blur, 18 * s * env); break;
        case 'pixelize': pix = Math.max(pix, 2 + 46 * s * env); break;
        case 'glitch': glitch = Math.max(glitch, 26 * s * env); break;
        case 'fade_black': fade = Math.max(fade, env); break;
        default: break;
      }
    }
    return { z, px, py, flash, blur, pix, glitch, fade };
  }

  /* ----------------------------------------------------------------- video */

  function videoEl(sid) {
    let v = VID[sid];
    if (v) {
      const i = ORDER.indexOf(sid);
      if (i >= 0) { ORDER.splice(i, 1); ORDER.push(sid); }
      return v;
    }
    v = document.createElement('video');
    v.src = '/api/media/' + sid;
    v.preload = 'auto';
    v.playsInline = true;
    v.muted = true;
    v.crossOrigin = 'anonymous';
    // Cuando no se está reproduciendo no hay bucle de dibujo, así que el
    // fotograma nuevo tras un salto hay que pintarlo al recibirlo: si no, el
    // canvas se queda con el anterior (o en negro la primera vez).
    for (const evt of ['seeked', 'loadeddata', 'canplay']) {
      v.addEventListener(evt, () => { if (!S.playing) paint(); });
    }
    v.addEventListener('error', () => ST.app.toast(
      'No pude cargar ' + ((S.sources[sid] || {}).name || sid) +
      '. Generá proxies con: vcut.py media --project …', 'bad'));
    document.getElementById('vhost').appendChild(v);
    VID[sid] = v; ORDER.push(sid);
    while (ORDER.length > MAX_VIDEOS) {
      const old = ORDER.shift();
      if (old === activeSid) { ORDER.push(old); break; }
      const ov = VID[old];
      if (ov) { ov.pause(); ov.removeAttribute('src'); ov.load(); ov.remove(); delete VID[old]; }
    }
    return v;
  }

  function setActive(sid, clip) {
    activeSid = sid;
    for (const key of Object.keys(VID)) {
      const v = VID[key];
      if (key === sid) {
        v.muted = !S.audio || !!(clip && (clip.cfg.mute));
        v.volume = clamp(dbToLin(clip ? clip.cfg.volume : 0), 0, 1);
      } else {
        v.muted = true;
        if (!v.paused) v.pause();
      }
    }
    const src = S.sources[sid];
    const b = document.getElementById('badgeSrc');
    if (b) b.textContent = src ? src.name : '';
  }

  function preloadNext(clip) {
    const nxt = S.clips[clip.index + 1];
    if (!nxt || nxt.source === clip.source) return;
    const v = videoEl(nxt.source);
    if (Math.abs(v.currentTime - nxt.in) > 0.6) {
      try { v.currentTime = nxt.in; } catch (e) { /* aún sin metadata */ }
    }
  }

  function seek(t, keepPlaying) {
    S.t = clamp(t, 0, S.total);
    const clip = st.clipAt(S.t);
    if (!clip) { paint(); ST.app.onTime(); return; }
    const v = videoEl(clip.source);
    setActive(clip.source, clip);
    const local = clamp(clip.in + (S.t - clip.t0) * clip.speed, clip.in, clip.out);
    try { v.currentTime = local; } catch (e) { /* se aplica al cargar metadata */ }
    v.playbackRate = clamp(clip.speed, 0.25, 4);
    preloadNext(clip);
    if (S.playing && keepPlaying !== false) v.play().catch(() => {});
    syncAudio(true);
    ST.app.onTime();
    paint();
  }

  function play() {
    if (!S.clips.length) return ST.app.toast('No hay clips activos', 'bad');
    if (S.t >= S.total - 0.04) S.t = 0;
    S.playing = true;
    document.getElementById('btnPlay').textContent = '❚❚';
    seek(S.t, true);
    const c = st.clipAt(S.t);
    if (c) videoEl(c.source).play().catch(() => {});
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(tick);
  }

  function pause() {
    S.playing = false;
    document.getElementById('btnPlay').textContent = '▶';
    for (const key of Object.keys(VID)) VID[key].pause();
    for (const key of Object.keys(AUD)) AUD[key].pause();
    for (const key of Object.keys(OVL)) {
      const o = OVL[key];
      if (o && o.kind === 'video' && o.el.pause) o.el.pause();
    }
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(tick);        // un último frame limpio
  }

  const toggle = () => (S.playing ? pause() : play());

  function tick() {
    if (S.playing) {
      const clip = st.clipAt(S.t);
      const v = clip && VID[clip.source];
      if (!clip || !v) { pause(); return; }
      const localEnd = clip.out - 0.02;
      if (v.currentTime >= localEnd || v.ended) {
        const nxt = S.clips[clip.index + 1];
        if (!nxt) { S.t = S.total; pause(); ST.app.onTime(); paint(); return; }
        S.t = nxt.t0;
        const nv = videoEl(nxt.source);
        setActive(nxt.source, nxt);
        try { nv.currentTime = nxt.in; } catch (e) { /* siguiente frame */ }
        nv.playbackRate = clamp(nxt.speed, 0.25, 4);
        nv.play().catch(() => {});
        preloadNext(nxt);
      } else {
        S.t = clip.t0 + (v.currentTime - clip.in) / clip.speed;
      }
      syncAudio(false);
      ST.app.onTime();
    }
    paint();
    if (S.playing) raf = requestAnimationFrame(tick);
  }

  /* ----------------------------------------------------------------- audio */

  function audioEl(item) {
    let a = AUD[item.id];
    if (!a) {
      a = new Audio('/api/asset?path=' + encodeURIComponent(item.src));
      a.preload = 'auto';
      AUD[item.id] = a;
    }
    a.volume = clamp(dbToLin((+item.gain || 0) + (+item.track_gain || 0)), 0, 1);
    return a;
  }

  function syncAudio(hard) {
    const on = S.audio && S.playing;
    for (const it of S.items) {
      if (it.track_kind !== 'audio' || !it.src) continue;
      const inside = S.t >= it.t && S.t < it.t_end;
      const a = AUD[it.id];
      if (!inside) { if (a && !a.paused) a.pause(); continue; }
      const el = audioEl(it);
      const want = (+it.in || 0) + (S.t - it.t);
      if (hard || Math.abs(el.currentTime - want) > 0.28) {
        try { el.currentTime = want; } catch (e) { /* aún sin metadata */ }
      }
      if (on && el.paused) el.play().catch(() => {});
      if (!on && !el.paused) el.pause();
    }
  }

  /* -------------------------------------------------------------- overlays */

  function overlayEl(it) {
    let o = OVL[it.id];
    if (o && o.src === it.src) return o;
    const url = '/api/asset?path=' + encodeURIComponent(it.src);
    const isVid = /\.(webm|mov|mp4|mkv)$/i.test(it.src || '');
    if (isVid) {
      const v = document.createElement('video');
      v.src = url; v.muted = true; v.playsInline = true; v.loop = !!it.loop;
      v.preload = 'auto';
      o = { el: v, kind: 'video', ok: true, src: it.src };
      v.addEventListener('error', () => { o.ok = false; });
    } else {
      const im = new Image();
      im.src = url;
      o = { el: im, kind: 'image', ok: true, src: it.src };
      im.onerror = () => { o.ok = false; };
    }
    OVL[it.id] = o;
    return o;
  }

  /* ---------------------------------------------------------------- dibujo */

  function layout() {
    cv = cv || document.getElementById('view');
    ctx = ctx || cv.getContext('2d');
    box = box || document.getElementById('canvasBox');
    wrap = wrap || document.getElementById('canvasWrap');
    const cw = S.tl.canvas.width, ch = S.tl.canvas.height;
    const aw = wrap.clientWidth - 24, ah = wrap.clientHeight - 24;
    if (aw <= 0 || ah <= 0) return;
    const scale = Math.min(aw / cw, ah / ch);
    dispW = Math.max(80, Math.floor(cw * scale));
    dispH = Math.max(80, Math.floor(ch * scale));
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    box.style.width = dispW + 'px';
    box.style.height = dispH + 'px';
    cv.style.width = dispW + 'px';
    cv.style.height = dispH + 'px';
    cv.width = Math.round(dispW * dpr);
    cv.height = Math.round(dispH * dpr);
    k = cv.width / cw;
  }

  let scratch = null;

  function paint() {
    if (!cv) layout();
    if (!ctx) return;
    const W = S.tl.canvas.width, H = S.tl.canvas.height;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = S.tl.canvas.bg || '#000';
    ctx.fillRect(0, 0, cv.width, cv.height);
    ctx.setTransform(k, 0, 0, k, 0, 0);

    const clip = st.clipAt(S.t);
    document.getElementById('canvasEmpty').classList.toggle('hidden', !!clip);
    if (!clip) return;
    const g = transGeom(S.t);
    const rel = S.t - clip.t0;
    const zm = zoomAt(clip, rel);
    const z = clamp(zm.z + g.z, 1, 3);
    const px = clamp(zm.px + g.px, -1.4, 1.4);
    const py = clamp(zm.py + g.py, -1.4, 1.4);

    const v = VID[clip.source];
    const vw = v && v.videoWidth, vh = v && v.videoHeight;
    if (v && vw && vh) {
      const fit = clip.cfg.fit || (S.tl.render && S.tl.render.fit) || 'cover';
      const cs = fit === 'cover' ? Math.max(W / vw, H / vh) : Math.min(W / vw, H / vh);
      const dw = vw * cs * z, dh = vh * cs * z;
      const rx = (W * (z - 1)) / 2, ry = (H * (z - 1)) / 2;
      const dx = (W - dw) / 2 - px * rx;
      const dy = (H - dh) / 2 - py * ry;
      ctx.save();
      if (g.blur > 0.4) ctx.filter = 'blur(' + (g.blur * 0.5).toFixed(1) + 'px)';
      if (clip.cfg.flip) { ctx.translate(W, 0); ctx.scale(-1, 1); }
      const look = clip.cfg.look || {};
      const fl = [];
      if (Math.abs(+look.brightness || 0) > 1e-3) fl.push('brightness(' + (1 + (+look.brightness)) + ')');
      if (Math.abs((+look.contrast || 1) - 1) > 1e-3) fl.push('contrast(' + (+look.contrast) + ')');
      if (Math.abs((+look.saturation || 1) - 1) > 1e-3) fl.push('saturate(' + (+look.saturation) + ')');
      if (Math.abs(+look.temp || 0) > 1e-3) fl.push('sepia(' + Math.min(0.5, Math.abs(+look.temp) * 0.4) + ')');
      if (fl.length) ctx.filter = (ctx.filter === 'none' || !ctx.filter ? '' : ctx.filter + ' ') + fl.join(' ');
      if (g.pix > 3) {
        // Pixelado: se baja a un canvas chico y se sube sin suavizado.
        scratch = scratch || document.createElement('canvas');
        const bw = Math.max(8, Math.round(W / g.pix)), bh = Math.max(8, Math.round(H / g.pix));
        scratch.width = bw; scratch.height = bh;
        const s2 = scratch.getContext('2d');
        s2.setTransform(bw / W, 0, 0, bh / H, 0, 0);
        s2.drawImage(v, dx, dy, dw, dh);
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(scratch, 0, 0, W, H);
        ctx.imageSmoothingEnabled = true;
      } else {
        ctx.drawImage(v, dx, dy, dw, dh);
        if (g.glitch > 1) {
          ctx.globalCompositeOperation = 'screen';
          ctx.globalAlpha = 0.5;
          ctx.filter = 'hue-rotate(-25deg)';
          ctx.drawImage(v, dx + g.glitch, dy, dw, dh);
          ctx.filter = 'hue-rotate(140deg)';
          ctx.drawImage(v, dx - g.glitch, dy, dw, dh);
          ctx.globalAlpha = 1;
          ctx.globalCompositeOperation = 'source-over';
        }
      }
      ctx.restore();
      ctx.filter = 'none';
    }

    // overlays
    for (const it of S.items) {
      if (it.track_kind !== 'overlay' || !it.src) continue;
      if (S.t < it.t || S.t >= it.t_end) continue;
      const o = overlayEl(it);
      if (!o.ok) continue;
      const el = o.el;
      if (o.kind === 'video') {
        const want = S.t - it.t;
        if (Math.abs(el.currentTime - want) > 0.3) {
          try { el.currentTime = want; } catch (e) { /* metadata */ }
        }
        if (S.playing && el.paused) el.play().catch(() => {});
        if (!S.playing && !el.paused) el.pause();
      }
      const nw = o.kind === 'video' ? el.videoWidth : el.naturalWidth;
      const nh = o.kind === 'video' ? el.videoHeight : el.naturalHeight;
      if (!nw || !nh) continue;
      const sc = +it.scale || 1;
      const w = nw * sc, h = nh * sc;
      const x = (it.x != null ? +it.x : 0.5) * W - w / 2;
      const y = (it.y != null ? +it.y : 0.5) * H - h / 2;
      let a = it.opacity != null ? +it.opacity : 1;
      const fd = +it.fade || 0;
      if (fd > 0.01) {
        a *= Math.min(1, (S.t - it.t) / fd) * Math.min(1, (it.t_end - S.t) / fd);
      }
      ctx.globalAlpha = clamp(a, 0, 1);
      ctx.drawImage(el, x, y, w, h);
      ctx.globalAlpha = 1;
    }

    // texto
    for (const it of S.items) {
      if (it.track_kind !== 'text') continue;
      if (S.t < it.t || S.t >= it.t_end) continue;
      ST.text.draw(ctx, it, st.styleOf(it), W, H, S.t - it.t);
    }

    if (g.flash > 0.01) {
      ctx.globalAlpha = clamp(g.flash, 0, 1);
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, W, H);
      ctx.globalAlpha = 1;
    }
    if (g.fade > 0.01) {
      ctx.globalAlpha = clamp(g.fade, 0, 1);
      ctx.fillStyle = '#000';
      ctx.fillRect(0, 0, W, H);
      ctx.globalAlpha = 1;
    }

    drawGuides(W, H, clip, z, px, py);
  }

  function drawGuides(W, H, clip, z, px, py) {
    ctx.save();
    ctx.lineWidth = 1 / k;
    if (S.guides) {
      ctx.strokeStyle = '#ffffff2e';
      for (let i = 1; i < 3; i++) {
        ctx.beginPath(); ctx.moveTo((W * i) / 3, 0); ctx.lineTo((W * i) / 3, H); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(0, (H * i) / 3); ctx.lineTo(W, (H * i) / 3); ctx.stroke();
      }
    }
    if (S.safe) {
      // Margen que las apps de redes tapan con su interfaz.
      ctx.strokeStyle = '#ffb45480';
      ctx.setLineDash([8 / k, 6 / k]);
      ctx.strokeRect(W * 0.06, H * 0.10, W * 0.88, H * 0.74);
      ctx.setLineDash([]);
    }
    if (S.tiktokUi) {
      // Referencia visual solamente: se pinta despues de todo el preview y
      // nunca entra en timeline.json ni en el grafo de ffmpeg.
      ctx.save();
      ctx.fillStyle = '#ffffffd9';
      ctx.strokeStyle = '#000b';
      ctx.lineWidth = 5 / k;
      ctx.font = '700 ' + (42 / k) + 'px system-ui,sans-serif';
      ctx.textAlign = 'center';
      const x = W * 0.91;
      const ys = [H * 0.53, H * 0.63, H * 0.73, H * 0.83];
      const icons = ['♡', '◌', '↗', '♫'];
      for (let i = 0; i < icons.length; i++) {
        ctx.strokeText(icons[i], x, ys[i]);
        ctx.fillText(icons[i], x, ys[i]);
      }
      ctx.strokeStyle = '#ff5f7ea8';
      ctx.setLineDash([10 / k, 7 / k]);
      ctx.strokeRect(W * 0.765, H * 0.485, W * 0.20, H * 0.38);
      ctx.setLineDash([]);
      ctx.font = '600 ' + (20 / k) + 'px system-ui,sans-serif';
      ctx.fillStyle = '#ffb4c2';
      ctx.fillText('zona TikTok', W * 0.84, H * 0.47);
      ctx.restore();
    }
    // Caja del texto seleccionado y encuadre del clip en modo reencuadre.
    if (S.sel && S.sel.kind === 'item') {
      const it = S.items.find((x) => x.id === S.sel.id);
      if (it && it.track_kind === 'text') {
        const b = ST.text.hitBox(it, st.styleOf(it), W, H);
        if (b) {
          ctx.strokeStyle = '#5b8cff';
          ctx.setLineDash([6 / k, 4 / k]);
          ctx.strokeRect(b.x0 - 6, b.y0 - 6, b.x1 - b.x0 + 12, b.y1 - b.y0 + 12);
          ctx.setLineDash([]);
        }
      } else if (it && it.track_kind === 'overlay') {
        const o = OVL[it.id];
        if (o && o.ok) {
          const nw = o.kind === 'video' ? o.el.videoWidth : o.el.naturalWidth;
          const nh = o.kind === 'video' ? o.el.videoHeight : o.el.naturalHeight;
          const sc = +it.scale || 1;
          const w = nw * sc, h = nh * sc;
          ctx.strokeStyle = '#2fd4a4';
          ctx.strokeRect((it.x != null ? it.x : 0.5) * W - w / 2,
                         (it.y != null ? it.y : 0.5) * H - h / 2, w, h);
        }
      }
    }
    if (S.mode === 'frame' && clip) {
      ctx.strokeStyle = '#8b5cf6cc';
      ctx.setLineDash([10 / k, 7 / k]);
      const iw = W / z, ih = H / z;
      ctx.strokeRect((W - iw) / 2 + (px * (W - iw)) / 2,
                     (H - ih) / 2 + (py * (H - ih)) / 2, iw, ih);
      ctx.setLineDash([]);
      ctx.fillStyle = '#8b5cf6';
      ctx.font = (16 / k).toFixed(0) + 'px system-ui';
      ctx.fillText(z.toFixed(2) + '×', 14, 30);
    }
    ctx.restore();
  }

  /* ---------------------------------------------------- interaccion canvas */

  function toProject(ev) {
    const r = cv.getBoundingClientRect();
    return {
      x: ((ev.clientX - r.left) / r.width) * S.tl.canvas.width,
      y: ((ev.clientY - r.top) / r.height) * S.tl.canvas.height,
    };
  }

  function itemAtPoint(p) {
    const W = S.tl.canvas.width, H = S.tl.canvas.height;
    // De arriba hacia abajo: gana el que se ve.
    for (let i = S.items.length - 1; i >= 0; i--) {
      const it = S.items[i];
      if (S.t < it.t || S.t >= it.t_end) continue;
      if (it.track_kind === 'text') {
        const b = ST.text.hitBox(it, st.styleOf(it), W, H);
        if (b && p.x >= b.x0 - 12 && p.x <= b.x1 + 12 && p.y >= b.y0 - 10 && p.y <= b.y1 + 10) return it;
      } else if (it.track_kind === 'overlay') {
        const o = OVL[it.id];
        if (!o || !o.ok) continue;
        const nw = o.kind === 'video' ? o.el.videoWidth : o.el.naturalWidth;
        const nh = o.kind === 'video' ? o.el.videoHeight : o.el.naturalHeight;
        if (!nw) continue;
        const sc = +it.scale || 1;
        const w = nw * sc, h = nh * sc;
        const x0 = (it.x != null ? it.x : 0.5) * W - w / 2;
        const y0 = (it.y != null ? it.y : 0.5) * H - h / 2;
        if (p.x >= x0 && p.x <= x0 + w && p.y >= y0 && p.y <= y0 + h) return it;
      }
    }
    return null;
  }

  function onDown(ev) {
    if (ev.button !== 0) return;
    const p = toProject(ev);
    const clip = st.clipAt(S.t);
    if (S.mode === 'frame') {
      if (!clip) return;
      const zm = zoomAt(clip, S.t - clip.t0);
      drag = { kind: 'frame', seg: clip.seg, p, zm, rel: S.t - clip.t0 };
      box.classList.add('moving');
      st.push();
      ev.preventDefault();
      return;
    }
    const it = itemAtPoint(p);
    if (!it) { st.select(null); paint(); return; }
    st.select('item', it.id);
    const W = S.tl.canvas.width, H = S.tl.canvas.height;
    const style = it.track_kind === 'text' ? st.styleOf(it) : null;
    const cx = it.x != null ? +it.x : (style ? ((style.box || {}).x != null ? +style.box.x : 0.5) : 0.5);
    const cy = it.y != null ? +it.y : (style ? ((style.box || {}).y != null ? +style.box.y : 0.66) : 0.5);
    drag = { kind: 'item', id: it.id, p, cx, cy, W, H };
    box.classList.add('moving');
    st.push();
    ev.preventDefault();
  }

  function onMove(ev) {
    if (!drag) return;
    const p = toProject(ev);
    if (drag.kind === 'item') {
      const { it } = st.findItem(drag.id);
      if (!it) return;
      it.x = +clamp(drag.cx + (p.x - drag.p.x) / drag.W, -0.4, 1.4).toFixed(4);
      it.y = +clamp(drag.cy + (p.y - drag.p.y) / drag.H, -0.4, 1.4).toFixed(4);
      st.resolve();
      paint();
      ST.inspector.refreshValues();
    } else if (drag.kind === 'frame') {
      const W = S.tl.canvas.width, H = S.tl.canvas.height;
      const z = drag.zm.z;
      // El contenido se desplaza -px*rx, asi que mover el raton dx pide
      // -dx/rx de pan. Sin zoom no hay margen: rx = 0 y no se puede mover.
      const rx = (W * (z - 1)) / 2, ry = (H * (z - 1)) / 2;
      if (rx < 1 && ry < 1) return;
      const nx = rx < 1 ? drag.zm.px : clamp(drag.zm.px - (p.x - drag.p.x) / rx, -1, 1);
      const ny = ry < 1 ? drag.zm.py : clamp(drag.zm.py - (p.y - drag.p.y) / ry, -1, 1);
      setFrame(drag.seg, drag.rel, { x: +nx.toFixed(4), y: +ny.toFixed(4) });
      paint();
    }
  }

  function onUp() {
    if (!drag) return;
    drag = null;
    box.classList.remove('moving');
    ST.timeline.render();
    ST.inspector.render();
  }

  function onWheel(ev) {
    if (S.mode !== 'frame') return;
    const clip = st.clipAt(S.t);
    if (!clip) return;
    ev.preventDefault();
    const rel = S.t - clip.t0;
    const cur = zoomAt(clip, rel);
    const z = clamp(cur.z * (ev.deltaY < 0 ? 1.06 : 1 / 1.06), 1, S.cat.zmax || 2);
    setFrame(clip.seg, rel, { scale: +z.toFixed(4) });
    paint();
    ST.inspector.refreshValues();
  }

  /* Escribe el encuadre en el keyframe mas cercano, o crea uno si el clip aun
     no tiene zoom. Es lo que hace que "arrastrar el encuadre" sea edicion real
     y no un ajuste que se pierde. */
  function setFrame(segId, rel, patch) {
    const slot = st.clipSlot(segId);
    slot.zoom = slot.zoom || { kf: [] };
    const kfs = slot.zoom.kf;
    if (!kfs.length) {
      kfs.push({ t: 0, scale: 1, x: 0, y: 0, ease: 'inout' });
    }
    let near = kfs[0], best = 1e9;
    for (const kf of kfs) {
      const d = Math.abs((+kf.t || 0) - rel);
      if (d < best) { best = d; near = kf; }
    }
    if (best > 0.12 && kfs.length) {
      const cur = zoomAt({ cfg: { zoom: slot.zoom } }, rel);
      near = { t: +rel.toFixed(3), scale: cur.z, x: cur.px, y: cur.py, ease: 'inout' };
      kfs.push(near);
      kfs.sort((a, b) => (+a.t || 0) - (+b.t || 0));
    }
    Object.assign(near, patch);
    st.resolve();
    st.markDirty(true);
  }

  function bind() {
    layout();
    cv.addEventListener('mousedown', onDown);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    cv.addEventListener('wheel', onWheel, { passive: false });
    cv.addEventListener('dblclick', (ev) => {
      const it = itemAtPoint(toProject(ev));
      if (it) ST.inspector.focusText(it.id);
    });
    new ResizeObserver(() => { layout(); paint(); })
      .observe(document.getElementById('canvasWrap'));
    raf = requestAnimationFrame(tick);
  }

  return { bind, layout, paint, seek, play, pause, toggle, zoomAt, pw, ease,
    bezOf, bez1,
           setFrame, videoEl };
})();
