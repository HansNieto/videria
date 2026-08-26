/* ==========================================================================
   motion-overlays — runtime
   Resuelve: escalado del lienzo, plugins, eases de marca, reproducción,
   loop limpio, control por teclado, captura frame a frame y auditoría.

   Parámetros de URL:
     ?paused=1      no reproduce (modo captura)
     ?t=2.4         salta a ese segundo y se queda ahí
     ?loop=0        reproduce una sola vez
     ?gap=1.2       hueco entre repeticiones (por defecto 0.8 s)
     ?bg=dark|light|photo|checker|green|magenta   fondo de revisión / croma
     ?hud=1         muestra el HUD (tecla H lo alterna)

   Teclado: espacio play/pausa · R repetir · H hud · ←/→ frame · 0 al inicio
   ========================================================================== */
(function () {
  'use strict';

  var P = new URLSearchParams(location.search);
  var opt = {
    paused: P.get('paused') === '1' || P.has('t'),
    t: P.has('t') ? parseFloat(P.get('t')) : null,
    loop: P.get('loop') !== '0',
    gap: P.has('gap') ? parseFloat(P.get('gap')) : 0.8,
    bg: P.get('bg') || null,
    hud: P.get('hud') === '1'
  };

  /* --- plugins ---------------------------------------------------------- */
  var plugins = ['CustomEase', 'DrawSVGPlugin', 'MorphSVGPlugin', 'MotionPathPlugin',
                 'Physics2DPlugin', 'CustomWiggle', 'CustomBounce', 'SplitText']
    .map(function (n) { return window[n]; })
    .filter(Boolean);
  if (window.gsap && plugins.length) gsap.registerPlugin.apply(gsap, plugins);

  /* --- eases de marca --------------------------------------------------- */
  function ease(name, path, fallback) {
    try {
      if (window.CustomEase) { CustomEase.create(name, path); return; }
    } catch (e) { /* cae al fallback */ }
    gsap.registerEase(name, gsap.parseEase(fallback));
  }
  ease('brand',  'M0,0 C0.16,1 0.3,1 1,1', 'power3.out');
  ease('swift',  'M0,0 C0.55,0 0.68,0.2 1,1', 'power2.in');
  ease('settle', 'M0,0 C0.14,0 0.2,1.06 0.5,1.03 C0.7,1.008 0.84,1 1,1', 'back.out(1.3)');

  /* --- fondo de revisión ------------------------------------------------ */
  function applyBg() {
    if (!opt.bg) return;
    document.body.classList.add('bg-' + opt.bg);
  }

  /* --- escala real del módulo -------------------------------------------
     Los grosores de trazo se declaran en px del lienzo 1920 (--sw, --sw-thin,
     --sw-hero) y las reglas .st dividen por --mscale. Aquí se mide la escala
     acumulada del grupo .module con getCTM() y se publica, de modo que el
     grosor declarado sea el grosor renderizado sin que el autor tenga que
     compensar a mano el scale() del transform.

     Por qué no vector-effect:"non-scaling-stroke", que haría lo mismo de una
     línea: el patrón de guiones pasa a calcularse en unidades del viewport
     mientras DrawSVG lo calcula en unidades locales, y toda animación de
     drawSVG sale fragmentada. Ver references/pitfalls.md §10.
     ---------------------------------------------------------------------- */
  var moduleScale = 1;
  function measureModule() {
    if (!stage) return 1;
    var mod = stage.querySelector('.module');
    if (!mod || !mod.getCTM) return 1;
    var m = mod.getCTM();
    if (!m) return 1;
    var sc = Math.sqrt(m.a * m.a + m.b * m.b);
    if (!isFinite(sc) || sc <= 0) return 1;
    moduleScale = sc;
    stage.style.setProperty('--mscale', String(sc));
    API.moduleScale = sc;
    return sc;
  }

  /* Grosores efectivos en px del lienzo, tal y como saldrán en el render. */
  function strokeWidths() {
    var cs = getComputedStyle(stage);
    var n = function (v) { return parseFloat(cs.getPropertyValue(v)) || 0; };
    return { base: n('--sw'), thin: n('--sw-thin'), hero: n('--sw-hero') };
  }

  /* --- escalado del lienzo --------------------------------------------- */
  var stage;
  function fit() {
    if (!stage) return;
    var s = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
    stage.style.transform = 'translate(-50%,-50%) scale(' + s + ')';
  }

  /* --- defs compartidos (filtros y degradados de los packs de estilo) ---- */
  var DEFS =
    '<filter id="ovRoughen" x="-10%" y="-10%" width="120%" height="120%">' +
      '<feTurbulence type="fractalNoise" baseFrequency="0.026" numOctaves="2" seed="7" result="n"/>' +
      '<feDisplacementMap in="SourceGraphic" in2="n" scale="3.4" ' +
        'xChannelSelector="R" yChannelSelector="G"/>' +
    '</filter>' +
    '<filter id="ovGrain" x="0" y="0" width="100%" height="100%">' +
      '<feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="1" result="g"/>' +
      '<feColorMatrix in="g" type="saturate" values="0" result="gm"/>' +
      '<feComposite in="gm" in2="SourceAlpha" operator="in" result="gi"/>' +
      '<feBlend in="SourceGraphic" in2="gi" mode="overlay"/>' +
    '</filter>' +
    '<linearGradient id="ovSoft" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="#ffffff" stop-opacity=".95"/>' +
      '<stop offset="1" stop-color="#D3DCE8" stop-opacity=".72"/></linearGradient>' +
    '<linearGradient id="ovSoftGlass" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="#ffffff" stop-opacity=".30"/>' +
      '<stop offset="1" stop-color="#ffffff" stop-opacity=".08"/></linearGradient>' +
    '<linearGradient id="ovSoftWarn" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="#FFD37A"/><stop offset="1" stop-color="#E08A00"/></linearGradient>' +
    '<linearGradient id="ovSoftBad" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="#FF9A96"/><stop offset="1" stop-color="#D83934"/></linearGradient>' +
    '<linearGradient id="ovSoftDark" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="#1B2331" stop-opacity=".92"/>' +
      '<stop offset="1" stop-color="#0C1119" stop-opacity=".92"/></linearGradient>' +
    '<linearGradient id="ovSoftAccent" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="#8FB0FF"/><stop offset="1" stop-color="#3A67D8"/></linearGradient>' +
    '<linearGradient id="ovSoftGold" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="#FFDF95"/><stop offset="1" stop-color="#D9A227"/></linearGradient>' +
    '<linearGradient id="ovSoftOk" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="#7BE7BC"/><stop offset="1" stop-color="#1FA871"/></linearGradient>' +
    '<radialGradient id="ovSpec" cx="30%" cy="20%" r="62%">' +
      '<stop offset="0" stop-color="#ffffff" stop-opacity=".55"/>' +
      '<stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>';

  function injectDefs(root) {
    var svg = root.querySelector('svg.canvas') || root.querySelector('svg');
    if (!svg || svg.querySelector('#ov-defs')) return;
    var defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    defs.setAttribute('id', 'ov-defs');
    defs.innerHTML = DEFS;
    svg.insertBefore(defs, svg.firstChild);
  }

  /* --- HUD -------------------------------------------------------------- */
  var hudEl;
  function buildHud(id) {
    hudEl = document.createElement('div');
    hudEl.id = 'hud';
    document.body.appendChild(hudEl);
    if (opt.hud) document.body.classList.add('hud');
    hudEl.textContent = id;
  }
  function updateHud(id) {
    if (!hudEl || !document.body.classList.contains('hud')) return;
    var t = API.tl ? API.tl.time() : 0;
    hudEl.textContent = id + '   ' + t.toFixed(2) + ' / ' + API.duration.toFixed(2) + ' s';
  }

  /* --- auditoría de limpieza ------------------------------------------- */
  function effOpacity(node, root) {
    var o = 1, n = node;
    while (n && n.nodeType === 1) {
      var cs = getComputedStyle(n);
      if (cs.display === 'none' || cs.visibility === 'hidden') return 0;
      o *= parseFloat(cs.opacity || 1);
      if (o < 0.02) return 0;
      if (n === root) break;
      n = n.parentNode;
    }
    return o;
  }
  var LEAF = 'path,rect,circle,ellipse,line,polyline,polygon,text,image,foreignObject';
  function visibleObjects() {
    var out = [];
    var list = stage.querySelectorAll('.o');
    for (var i = 0; i < list.length; i++) {
      var el = list[i];
      var leaves = el.querySelectorAll(LEAF);
      var nodes = leaves.length ? leaves : [el];
      for (var j = 0; j < nodes.length; j++) {
        if (effOpacity(nodes[j], stage) < 0.02) continue;
        var r = nodes[j].getBoundingClientRect();
        if (r.width > 0.5 && r.height > 0.5) {
          out.push({ el: el, clase: el.getAttribute('class') });
          break;
        }
      }
    }
    return out;
  }

  function audit() {
    var tl = API.tl;
    if (!tl) { console.warn('[overlay] no hay timeline'); return []; }
    var wasPaused = tl.paused(), t0 = tl.time(), rep = tl.repeat();
    tl.pause(); tl.repeat(0);

    tl.time(0, true);
    var atStart = visibleObjects();
    tl.time(API.duration, true);
    var atEnd = visibleObjects();

    tl.repeat(rep); tl.time(t0, true);
    if (!wasPaused) tl.play();

    var sw = strokeWidths();
    var swOk = sw.base >= 6;
    var swMobile = sw.base >= 9;

    var ok = !atStart.length && !atEnd.length && swOk;
    console.log('%c[overlay] audit ' + API.id, 'font-weight:700');
    console.log('  duración: ' + API.duration.toFixed(2) + ' s  ' +
      (API.duration >= 2 && API.duration <= 6 ? '✔ (2–6 s)' : '✖ fuera del rango 2–6 s'));
    console.log('  escala del módulo: ×' + moduleScale.toFixed(3) +
      '  (compensada: el grosor declarado es el renderizado)');
    console.log('  trazo en el lienzo: ' + sw.base + ' / ' + sw.thin + ' / ' + sw.hero +
      ' px (base/fino/héroe)  ' +
      (swMobile ? '✔ vale también en móvil y vertical'
                : swOk ? '✔ 16:9 a 1080p · ✖ para móvil usa s-bold (≥9)'
                       : '✖ por debajo de 6 px: se pierde sobre video'));
    console.log('  visibles en t=0:   ' + atStart.length + (atStart.length ? ' ✖' : ' ✔'));
    console.log('  visibles en t=fin: ' + atEnd.length + (atEnd.length ? ' ✖' : ' ✔'));
    if (atStart.length) console.table(atStart.map(function (x) { return x.clase; }));
    if (atEnd.length) console.table(atEnd.map(function (x) { return x.clase; }));
    if (!atStart.length && !atEnd.length)
      console.log('  overlay limpio: entra y sale sin residuos ✔');
    return { start: atStart, end: atEnd, ok: ok,
             moduleScale: moduleScale, stroke: sw };
  }

  /* --- API -------------------------------------------------------------- */
  var API = {
    id: null,
    tl: null,
    duration: 0,
    moduleScale: 1,
    scene: scene,
    audit: audit,
    play: function () { API.tl && API.tl.play(); },
    pause: function () { API.tl && API.tl.pause(); },
    replay: function () { API.tl && API.tl.restart(true); },
    seek: function (t) {
      if (!API.tl) return;
      API.tl.pause();
      /* sin suppressEvents: los contadores (onUpdate) y los .call() tienen que
         ejecutarse también al saltar a un frame, o la captura sale con las
         cifras congeladas en su valor inicial. */
      API.tl.time(Math.max(0, Math.min(t, API.duration)));
      updateHud(API.id);
    }
  };

  function q(sel) { return stage.querySelector(sel); }
  function qa(sel) { return Array.prototype.slice.call(stage.querySelectorAll(sel)); }

  function scene(cfg) {
    stage = document.getElementById('stage');
    if (!stage) throw new Error('[overlay] falta #stage');
    API.id = cfg.id || document.title || 'overlay';

    applyBg();
    injectDefs(stage);
    if (cfg.style) stage.classList.add(cfg.style);
    measureModule();
    fit();
    window.addEventListener('resize', fit);
    buildHud(API.id);

    var tl = gsap.timeline({
      paused: true,
      defaults: cfg.defaults || { duration: 0.5, ease: 'brand' },
      onUpdate: function () { updateHud(API.id); }
    });

    cfg.build(tl, { stage: stage, q: q, qa: qa, gsap: gsap, BEATS: cfg.BEATS });

    API.tl = tl;
    API.duration = Math.round(tl.duration() * 1000) / 1000;

    if (opt.loop && !opt.paused) { tl.repeat(-1); tl.repeatDelay(opt.gap); }

    if (opt.t !== null) API.seek(opt.t);
    else if (!opt.paused) tl.play();
    else tl.time(0, true);

    keys();
    if (window.parent !== window) {
      window.parent.postMessage({ __overlay: 'ready', id: API.id, duration: API.duration }, '*');
    }
    console.log('[overlay] ' + API.id + ' · ' + API.duration.toFixed(2) +
                ' s · Overlay.audit() para revisar');
    return tl;
  }

  /* --- control ---------------------------------------------------------- */
  function keys() {
    window.addEventListener('keydown', function (e) {
      var tl = API.tl; if (!tl) return;
      var f = 1 / 60 * (e.shiftKey ? 10 : 1);
      switch (e.key) {
        case ' ': e.preventDefault(); tl.paused() ? tl.play() : tl.pause(); break;
        case 'r': case 'R': tl.restart(true); break;
        case 'h': case 'H': document.body.classList.toggle('hud'); updateHud(API.id); break;
        case '0': API.seek(0); break;
        case 'ArrowRight': e.preventDefault(); API.seek(tl.time() + f); break;
        case 'ArrowLeft': e.preventDefault(); API.seek(tl.time() - f); break;
      }
    });
    window.addEventListener('message', function (e) {
      var d = e.data || {};
      if (!d.__overlay || !API.tl) return;
      if (d.__overlay === 'replay') API.replay();
      else if (d.__overlay === 'play') API.play();
      else if (d.__overlay === 'pause') API.pause();
      else if (d.__overlay === 'seek') API.seek(d.t || 0);
      else if (d.__overlay === 'bg') {
        var hud = document.body.classList.contains('hud');
        document.body.className = (d.bg ? 'bg-' + d.bg : '') + (hud ? ' hud' : '');
      }
    });
  }

  window.Overlay = API;
})();
