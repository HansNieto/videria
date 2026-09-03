/* Divisores de panel persistentes. No forman parte del proyecto de video: la
   disposición se guarda solo en este navegador. */
window.ST = window.ST || {};

ST.layout = (() => {
  'use strict';
  const root = document.documentElement;
  const defaults = { lib: 236, preview: Math.round(innerWidth * 0.42), timeline: 320 };
  const limits = {
    lib: (v) => Math.max(150, Math.min(v, innerWidth * 0.35)),
    preview: (v) => Math.max(300, Math.min(v, innerWidth * 0.62)),
    timeline: (v) => Math.max(170, Math.min(v, innerHeight * 0.68)),
  };
  const prop = { lib: '--w-lib', preview: '--w-preview', timeline: '--h-tl' };
  let active = null;

  function set(kind, value, save) {
    value = Math.round(limits[kind](value));
    root.style.setProperty(prop[kind], value + 'px');
    if (save) localStorage.setItem('vcut-layout-' + kind, String(value));
    requestAnimationFrame(() => {
      if (ST.S && ST.S.tl && ST.player && ST.player.resize) ST.player.resize();
      if (ST.S && ST.S.tl && ST.timeline && ST.timeline.render) ST.timeline.render();
    });
  }

  function bind() {
    for (const kind of Object.keys(prop)) {
      const saved = +localStorage.getItem('vcut-layout-' + kind);
      if (saved) set(kind, saved, false);
    }
    for (const h of document.querySelectorAll('[data-resize]')) {
      h.addEventListener('pointerdown', (ev) => {
        active = { kind: h.dataset.resize, startX: ev.clientX, startY: ev.clientY,
          start: parseFloat(getComputedStyle(root).getPropertyValue(prop[h.dataset.resize])) };
        h.setPointerCapture(ev.pointerId); h.classList.add('active');
        document.body.classList.add(active.kind === 'timeline' ? 'resizing-y' : 'resizing');
      });
      h.addEventListener('pointermove', (ev) => {
        if (!active || active.kind !== h.dataset.resize) return;
        const delta = active.kind === 'lib' ? ev.clientX - active.startX
          : active.kind === 'preview' ? active.startX - ev.clientX
          : active.startY - ev.clientY;
        set(active.kind, active.start + delta, false);
      });
      const done = () => {
        if (!active) return;
        const v = parseFloat(getComputedStyle(root).getPropertyValue(prop[active.kind]));
        localStorage.setItem('vcut-layout-' + active.kind, String(Math.round(v)));
        active = null; h.classList.remove('active');
        document.body.classList.remove('resizing', 'resizing-y');
      };
      h.addEventListener('pointerup', done);
      h.addEventListener('pointercancel', done);
      h.addEventListener('dblclick', () => set(h.dataset.resize, defaults[h.dataset.resize], true));
    }
  }
  document.addEventListener('DOMContentLoaded', bind);
  return { bind, set };
})();
