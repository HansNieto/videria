/* Motion graphics específicos del video 17 v2.
   Cada nodo se construye por piezas: profundidad, borde, cara, símbolo y brillo. */
(function () {
  'use strict';

  const scenes = {
    price: {
      id: '01_precio_sin_contexto',
      markup: `
        <g class="module" transform="translate(540,500)">
          <g class="o node" data-beat="0.06" transform="translate(-330,-105)">
            <circle class="piece sticker-depth" cy="16" r="112"/>
            <circle class="piece sticker-rim" r="108"/>
            <circle class="piece sticker-blue" r="94"/>
            <path class="piece sticker-shine" d="M-66,-63 A91,91 0 0 1 62,-66 A76,76 0 0 0 -66,-63 Z"/>
            <circle class="piece sticker-white" cy="-29" r="29"/>
            <path class="piece sticker-white" d="M-57,58 V36 Q-57,-3 0,-3 Q57,-3 57,36 V58 Q0,76 -57,58 Z"/>
          </g>
          <g class="o node" data-beat="0.66" transform="translate(-272,-272)">
            <path class="piece sticker-depth" d="M-76,-42 H65 Q94,-42 94,-13 V44 Q94,73 65,73 H19 L-22,108 L-16,73 H-76 Q-105,73 -105,44 V-13 Q-105,-42 -76,-42 Z"/>
            <path class="piece sticker-rim" d="M-76,-57 H65 Q94,-57 94,-28 V29 Q94,58 65,58 H19 L-22,93 L-16,58 H-76 Q-105,58 -105,29 V-28 Q-105,-57 -76,-57 Z"/>
            <path class="piece sticker-blue" d="M-67,-44 H56 Q80,-44 80,-20 V21 Q80,45 56,45 H12 L-4,61 L0,45 H-67 Q-91,45 -91,21 V-20 Q-91,-44 -67,-44 Z"/>
            <text class="piece v17-label v17-big" x="-7" y="25" text-anchor="middle">?</text>
          </g>
          <g class="o route" data-beat="1.02">
            <path class="piece route-line sticker-route-depth" d="M-205,-98 C-95,-145,-30,-120,43,-62"/>
            <path class="piece route-line sticker-route" d="M-205,-98 C-95,-145,-30,-120,43,-62"/>
            <path class="piece route-arrow sticker-cyan" d="M24,-83 L60,-48 L11,-45 Z"/>
          </g>
          <g class="o node emphasis" data-beat="1.45" transform="translate(75,-52)">
            <path class="piece sticker-depth" d="M-132,-60 H79 L144,8 L80,90 H-132 Q-160,90 -160,62 V-32 Q-160,-60 -132,-60 Z"/>
            <path class="piece sticker-rim" d="M-132,-76 H79 L144,-8 L80,74 H-132 Q-160,74 -160,46 V-48 Q-160,-76 -132,-76 Z"/>
            <path class="piece sticker-blue" d="M-123,-61 H70 L124,-7 L70,59 H-123 Q-144,59 -144,38 V-40 Q-144,-61 -123,-61 Z"/>
            <path class="piece sticker-shine" d="M-116,-50 H57 L86,-21 H-132 V-36 Q-132,-50 -116,-50 Z"/>
            <circle class="piece sticker-rim" cx="82" cy="-8" r="14"/>
            <text class="piece v17-label v17-big" x="-20" y="24" text-anchor="middle">S/.</text>
          </g>
          <g class="o route" data-beat="2.18">
            <path class="piece route-line sticker-route-depth" d="M220,-46 C290,-16 306,41 310,105"/>
            <path class="piece route-line sticker-route" d="M220,-46 C290,-16 306,41 310,105"/>
            <path class="piece route-arrow sticker-cyan" d="M286,88 L312,128 L333,84 Z"/>
          </g>
          <g class="o node emphasis" data-beat="2.62" transform="translate(310,190)">
            <circle class="piece sticker-depth" cy="16" r="111"/>
            <circle class="piece sticker-rim" r="108"/>
            <circle class="piece sticker-red" r="94"/>
            <path class="piece sticker-shine" d="M-64,-62 A91,91 0 0 1 62,-65 A76,76 0 0 0 -64,-62 Z"/>
            <path class="piece route-line st hero" d="M-39,-39 L39,39"/>
            <path class="piece route-line st hero" d="M39,-39 L-39,39"/>
            <path class="piece route-line st c-bad" d="M90,-68 L118,-92 M108,-38 L141,-44 M79,-94 L90,-125"/>
          </g>
        </g>`
    },

    overload: {
      id: '02_mensaje_sobrecarga',
      markup: `
        <g class="module" transform="translate(540,500)">
          <g class="o node" data-beat="0.06" transform="translate(-310,5)">
            <rect class="piece sticker-depth" x="-116" y="-190" width="232" height="380" rx="47" transform="translate(0,16)"/>
            <rect class="piece sticker-rim" x="-116" y="-190" width="232" height="380" rx="47"/>
            <rect class="piece sticker-blue" x="-98" y="-164" width="196" height="318" rx="30"/>
            <path class="piece route-line st thin" d="M-55,-119 H55 M-55,-78 H31 M-55,88 H54"/>
            <circle class="piece sticker-white" cy="121" r="13"/>
            <path class="piece sticker-shine" d="M-74,-147 H55 Q77,-147 80,-126 H-83 Q-82,-140 -74,-147 Z"/>
          </g>
          <g class="o node" data-beat="0.72" transform="translate(-60,-190)">
            <path class="piece sticker-depth" d="M-118,-52 H104 Q132,-52 132,-24 V38 Q132,66 104,66 H-33 L-72,101 L-66,66 H-118 Q-146,66 -146,38 V-24 Q-146,-52 -118,-52 Z"/>
            <path class="piece sticker-rim" d="M-118,-67 H104 Q132,-67 132,-39 V23 Q132,51 104,51 H-33 L-72,86 L-66,51 H-118 Q-146,51 -146,23 V-39 Q-146,-67 -118,-67 Z"/>
            <path class="piece sticker-blue" d="M-107,-53 H93 Q116,-53 116,-30 V14 Q116,37 93,37 H-43 L-58,51 L-54,37 H-107 Q-130,37 -130,14 V-30 Q-130,-53 -107,-53 Z"/>
            <path class="piece route-line st thin" d="M-91,-24 H77 M-91,8 H52"/>
          </g>
          <g class="o node" data-beat="1.30" transform="translate(35,-25)">
            <path class="piece sticker-depth" d="M-138,-58 H121 Q150,-58 150,-29 V42 Q150,71 121,71 H-49 L-90,108 L-83,71 H-138 Q-167,71 -167,42 V-29 Q-167,-58 -138,-58 Z"/>
            <path class="piece sticker-rim" d="M-138,-73 H121 Q150,-73 150,-44 V27 Q150,56 121,56 H-49 L-90,93 L-83,56 H-138 Q-167,56 -167,27 V-44 Q-167,-73 -138,-73 Z"/>
            <path class="piece sticker-cyan" d="M-126,-58 H109 Q133,-58 133,-34 V18 Q133,42 109,42 H-58 L-75,58 L-70,42 H-126 Q-150,42 -150,18 V-34 Q-150,-58 -126,-58 Z"/>
            <path class="piece route-line st thin" d="M-108,-26 H90 M-108,5 H105 M-108,34 H47"/>
          </g>
          <g class="o node" data-beat="1.88" transform="translate(94,145)">
            <path class="piece sticker-depth" d="M-128,-55 H111 Q138,-55 138,-28 V37 Q138,64 111,64 H-41 L-80,99 L-74,64 H-128 Q-155,64 -155,37 V-28 Q-155,-55 -128,-55 Z"/>
            <path class="piece sticker-rim" d="M-128,-70 H111 Q138,-70 138,-43 V22 Q138,49 111,49 H-41 L-80,84 L-74,49 H-128 Q-155,49 -155,22 V-43 Q-155,-70 -128,-70 Z"/>
            <path class="piece sticker-blue" d="M-116,-56 H99 Q122,-56 122,-33 V13 Q122,36 99,36 H-51 L-66,50 L-62,36 H-116 Q-139,36 -139,13 V-33 Q-139,-56 -116,-56 Z"/>
            <path class="piece route-line st thin" d="M-97,-24 H80 M-97,7 H95"/>
          </g>
          <g class="o route" data-beat="2.36">
            <path class="piece route-line sticker-route-depth" d="M218,83 C283,75 309,64 342,33"/>
            <path class="piece route-line sticker-route" d="M218,83 C283,75 309,64 342,33"/>
            <path class="piece route-arrow sticker-cyan" d="M321,26 L365,12 L348,57 Z"/>
          </g>
          <g class="o node emphasis" data-beat="2.72" transform="translate(348,-50)">
            <circle class="piece sticker-depth" cy="16" r="106"/>
            <circle class="piece sticker-rim" r="103"/>
            <circle class="piece sticker-red" r="89"/>
            <path class="piece sticker-shine" d="M-60,-59 A86,86 0 0 1 59,-61 A72,72 0 0 0 -60,-59 Z"/>
            <text class="piece v17-label v17-big" x="0" y="27" text-anchor="middle">?</text>
            <path class="piece route-line st c-bad" d="M-68,90 L-84,121 M0,105 V140 M68,90 L84,121"/>
          </g>
        </g>`
    },

    direction: {
      id: '03_iniciativa_sin_direccion',
      markup: `
        <g class="module" transform="translate(540,500)">
          <g class="o node" data-beat="0.06" transform="translate(-325,-35)">
            <circle class="piece sticker-depth" cy="16" r="110"/><circle class="piece sticker-rim" r="107"/><circle class="piece sticker-blue" r="93"/>
            <circle class="piece sticker-white" cy="-29" r="28"/><path class="piece sticker-white" d="M-55,57 V37 Q-55,0 0,0 Q55,0 55,37 V57 Q0,74 -55,57 Z"/>
            <path class="piece sticker-shine" d="M-64,-62 A90,90 0 0 1 61,-64 A75,75 0 0 0 -64,-62 Z"/>
          </g>
          <g class="o node" data-beat="0.62" transform="translate(-292,-205)">
            <path class="piece sticker-depth" d="M-72,-40 H60 Q88,-40 88,-12 V39 Q88,67 60,67 H18 L-19,99 L-14,67 H-72 Q-100,67 -100,39 V-12 Q-100,-40 -72,-40 Z"/>
            <path class="piece sticker-rim" d="M-72,-55 H60 Q88,-55 88,-27 V24 Q88,52 60,52 H18 L-19,84 L-14,52 H-72 Q-100,52 -100,24 V-27 Q-100,-55 -72,-55 Z"/>
            <path class="piece sticker-blue" d="M-62,-42 H50 Q73,-42 73,-19 V15 Q73,38 50,38 H10 L-4,51 L0,38 H-62 Q-85,38 -85,15 V-19 Q-85,-42 -62,-42 Z"/>
            <text class="piece v17-label" x="-5" y="16" text-anchor="middle">OK</text>
          </g>
          <g class="o route" data-beat="1.10">
            <path id="dirPath" class="piece route-line sticker-route-depth" d="M-202,-35 C-78,-105 53,-104 180,-34"/>
            <path class="piece route-line sticker-route" d="M-202,-35 C-78,-105 53,-104 180,-34"/>
            <path class="piece route-arrow sticker-cyan" d="M155,-52 L199,-22 L150,-12 Z"/>
          </g>
          <g class="o node initiative" data-beat="1.48" transform="translate(-168,-67)">
            <circle class="piece sticker-depth" cy="10" r="52"/><circle class="piece sticker-rim" r="50"/><circle class="piece sticker-cyan" r="39"/>
            <path class="piece sticker-shine" d="M-25,-25 A38,38 0 0 1 25,-27 A31,31 0 0 0 -25,-25 Z"/>
            <path class="piece route-line st hero" d="M-14,0 H15 M4,-12 L17,0 L4,12"/>
          </g>
          <g class="o node" data-beat="2.08" transform="translate(310,-35)">
            <circle class="piece sticker-depth" cy="16" r="110"/><circle class="piece sticker-rim" r="107"/><circle class="piece sticker-blue" r="93"/>
            <circle class="piece sticker-white" cy="-29" r="28"/><path class="piece sticker-white" d="M-55,57 V37 Q-55,0 0,0 Q55,0 55,37 V57 Q0,74 -55,57 Z"/>
            <path class="piece sticker-shine" d="M-64,-62 A90,90 0 0 1 61,-64 A75,75 0 0 0 -64,-62 Z"/>
          </g>
          <g class="o node emphasis" data-beat="2.70" transform="translate(310,-205)">
            <path class="piece sticker-depth" d="M-74,-42 H62 Q91,-42 91,-13 V41 Q91,70 62,70 H20 L-20,104 L-14,70 H-74 Q-103,70 -103,41 V-13 Q-103,-42 -74,-42 Z"/>
            <path class="piece sticker-rim" d="M-74,-57 H62 Q91,-57 91,-28 V26 Q91,55 62,55 H20 L-20,89 L-14,55 H-74 Q-103,55 -103,26 V-28 Q-103,-57 -74,-57 Z"/>
            <path class="piece sticker-red" d="M-64,-44 H52 Q76,-44 76,-20 V17 Q76,41 52,41 H11 L-5,55 L0,41 H-64 Q-88,41 -88,17 V-20 Q-88,-44 -64,-44 Z"/>
            <text class="piece v17-label v17-big" x="-6" y="25" text-anchor="middle">?</text>
            <path class="piece route-line st c-bad" d="M-74,86 L-88,118 M0,100 V136 M74,86 L88,118"/>
          </g>
        </g>`
    },

    guide: {
      id: '04_guiar_siguiente_paso',
      markup: `
        <g class="module" transform="translate(540,500)">
          <g class="o node" data-beat="0.06" transform="translate(-348,-50)">
            <circle class="piece sticker-depth" cy="16" r="106"/><circle class="piece sticker-rim" r="103"/><circle class="piece sticker-blue" r="89"/>
            <circle class="piece sticker-white" cy="-28" r="27"/><path class="piece sticker-white" d="M-53,54 V35 Q-53,0 0,0 Q53,0 53,35 V54 Q0,71 -53,54 Z"/>
            <path class="piece sticker-shine" d="M-61,-59 A86,86 0 0 1 58,-61 A72,72 0 0 0 -61,-59 Z"/>
          </g>
          <g class="o node" data-beat="0.56" transform="translate(-314,-210)">
            <path class="piece sticker-depth" d="M-70,-39 H58 Q86,-39 86,-11 V37 Q86,65 58,65 H17 L-18,96 L-13,65 H-70 Q-98,65 -98,37 V-11 Q-98,-39 -70,-39 Z"/>
            <path class="piece sticker-rim" d="M-70,-54 H58 Q86,-54 86,-26 V22 Q86,50 58,50 H17 L-18,81 L-13,50 H-70 Q-98,50 -98,22 V-26 Q-98,-54 -70,-54 Z"/>
            <path class="piece sticker-cyan" d="M-60,-41 H48 Q71,-41 71,-18 V13 Q71,36 48,36 H9 L-4,49 L0,36 H-60 Q-83,36 -83,13 V-18 Q-83,-41 -60,-41 Z"/>
            <text class="piece v17-label v17-big" x="-5" y="23" text-anchor="middle">?</text>
          </g>
          <g class="o route" data-beat="0.98"><path class="piece route-line sticker-route-depth" d="M-235,-47 C-175,-83 -131,-97 -76,-96"/><path class="piece route-line sticker-route" d="M-235,-47 C-175,-83 -131,-97 -76,-96"/><path class="piece route-arrow sticker-cyan" d="M-99,-116 L-55,-96 L-98,-72 Z"/></g>
          <g class="o node" data-beat="1.28" transform="translate(-5,-188)">
            <circle class="piece sticker-depth" cy="12" r="78"/><circle class="piece sticker-rim" r="75"/><circle class="piece sticker-blue" r="62"/>
            <path class="piece sticker-shine" d="M-42,-42 A61,61 0 0 1 41,-43 A51,51 0 0 0 -42,-42 Z"/>
            <path class="piece route-line st hero" d="M-25,9 L-7,27 L30,-22"/>
          </g>
          <g class="o node" data-beat="1.76" transform="translate(-5,8)">
            <circle class="piece sticker-depth" cy="12" r="78"/><circle class="piece sticker-rim" r="75"/><circle class="piece sticker-cyan" r="62"/>
            <path class="piece sticker-shine" d="M-42,-42 A61,61 0 0 1 41,-43 A51,51 0 0 0 -42,-42 Z"/>
            <text class="piece v17-label v17-small" x="0" y="14" text-anchor="middle">STOCK</text>
          </g>
          <g class="o node" data-beat="2.22" transform="translate(-5,204)">
            <circle class="piece sticker-depth" cy="12" r="78"/><circle class="piece sticker-rim" r="75"/><circle class="piece sticker-blue" r="62"/>
            <path class="piece sticker-shine" d="M-42,-42 A61,61 0 0 1 41,-43 A51,51 0 0 0 -42,-42 Z"/>
            <text class="piece v17-label v17-big" x="0" y="25" text-anchor="middle">?</text>
          </g>
          <g class="o route" data-beat="2.58"><path class="piece route-line sticker-route-depth" d="M75,-188 C177,-155 181,-39 236,-34 M75,8 C159,8 181,-20 236,-25 M75,204 C182,168 181,28 236,-16"/><path class="piece route-line sticker-route" d="M75,-188 C177,-155 181,-39 236,-34 M75,8 C159,8 181,-20 236,-25 M75,204 C182,168 181,28 236,-16"/><path class="piece route-arrow sticker-cyan" d="M215,-45 L257,-24 L214,-1 Z"/></g>
          <g class="o node emphasis" data-beat="2.92" transform="translate(330,-22)">
            <circle class="piece sticker-depth" cy="16" r="112"/><circle class="piece sticker-rim" r="109"/><circle class="piece sticker-blue" r="95"/>
            <path class="piece sticker-shine" d="M-66,-64 A92,92 0 0 1 63,-67 A78,78 0 0 0 -66,-64 Z"/>
            <path class="piece route-line st hero" d="M-43,7 L-13,38 L49,-38"/>
            <text class="piece v17-label v17-small" x="0" y="78" text-anchor="middle">SIGUE</text>
          </g>
        </g>`
    }
  };

  function start(kind) {
    const scene = scenes[kind];
    if (!scene) throw new Error('Escena desconocida: ' + kind);
    const svg = document.querySelector('svg.canvas');
    svg.innerHTML = scene.markup;

    Overlay.scene({
      id: scene.id,
      style: 's-sticker3d',
      build(tl) {
        const nodes = Array.from(document.querySelectorAll('.o.node'));
        const routes = Array.from(document.querySelectorAll('.o.route'));
        gsap.set('.o, .piece', { autoAlpha: 0 });
        gsap.set('.piece', { transformOrigin: '50% 50%' });

        nodes.forEach((node) => {
          const at = Number(node.dataset.beat || 0);
          const pieces = Array.from(node.querySelectorAll(':scope > .piece'));
          tl.set(node, { autoAlpha: 1 }, at);
          pieces.forEach((piece, index) => {
            const isLine = piece.classList.contains('route-line');
            if (isLine) {
              tl.fromTo(piece, { autoAlpha: 0, drawSVG: '0%' }, {
                autoAlpha: 1, drawSVG: '100%', duration: .24,
                ease: 'power2.out'
              }, at + index * .075);
            } else {
              tl.fromTo(piece, { autoAlpha: 0, scale: index < 2 ? .30 : .52, y: index === 0 ? 15 : 0 }, {
                autoAlpha: 1, scale: 1, y: 0, duration: index < 2 ? .30 : .24,
                ease: index < 2 ? 'brand' : 'settle'
              }, at + index * .075);
            }
          });
        });

        routes.forEach((route) => {
          const at = Number(route.dataset.beat || 0);
          tl.set(route, { autoAlpha: 1 }, at)
            .fromTo(route.querySelectorAll('.route-line'), { autoAlpha: 0, drawSVG: '0%' }, {
              autoAlpha: 1, drawSVG: '100%', duration: .45, stagger: .05,
              ease: 'power2.inOut'
            }, at)
            .fromTo(route.querySelectorAll('.route-arrow'), { autoAlpha: 0, scale: .18 }, {
              autoAlpha: 1, scale: 1, duration: .20, ease: 'settle'
            }, at + .36);
        });

        tl.to('.emphasis', { scale: 1.055, duration: .15, yoyo: true, repeat: 1, ease: 'power2.out', transformOrigin: '50% 50%' }, 3.56)
          .to({}, { duration: .01 }, 4.18)
          .to('.route-arrow, .v17-label', { autoAlpha: 0, scale: .65, duration: .18, stagger: .018, ease: 'swift' }, 4.22)
          .to('.route-line', { drawSVG: '0%', autoAlpha: 0, duration: .28, stagger: .018, ease: 'swift' }, 4.31)
          .to('.sticker-shine, .sticker-white', { autoAlpha: 0, scale: .55, duration: .21, stagger: .015, ease: 'swift' }, 4.42)
          .to('.sticker-blue, .sticker-cyan, .sticker-red', { autoAlpha: 0, scale: .42, duration: .23, stagger: .018, ease: 'swift' }, 4.53)
          .to('.sticker-rim', { autoAlpha: 0, scale: .30, duration: .22, stagger: .018, ease: 'swift' }, 4.64)
          .to('.sticker-depth', { autoAlpha: 0, scale: .25, duration: .20, stagger: .015, ease: 'swift' }, 4.76)
          .set('.o', { autoAlpha: 0 }, 5.02);
      }
    });
  }

  window.V17Scene = { start };
})();

