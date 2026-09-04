# Changelog

Formato: cambios agrupados por versión, con el motivo cuando no es evidente.

## 2.0.0 — vertical real y neón editorial premium

Corregido a partir de la comparación visual del usuario entre el overlay generado y el
acabado esperado:

- Nuevo pack `s-neon`: paneles azul noche translúcidos, frente blanco/cian nítido,
  resplandor controlado, rutas curvas, pulsos y rojo exclusivamente semántico.
- La plantilla dejó de ser una tarjeta genérica 16:9. Ahora es una escena 1080×1920 de
  referencia con cuatro nodos conectados, animación causal y espacio reservado para el
  presentador y los subtítulos.
- Nueva regla de composición: una idea compleja necesita 3–5 nodos y al menos dos
  conexiones cuando exista causalidad. Se rechaza “icono grande + línea larga + X”.
- `overlay.js`, `capture.mjs` y la galería leen el `viewBox`; horizontal y vertical se
  previsualizan y capturan en su tamaño real, sin estirar uno dentro del otro.
- `Overlay.canvas` expone ancho, alto y orientación. La auditoría lo reporta.
- Nueva guía `references/neon-vertical.md`: zona libre sobre un frame real, capas de un
  nodo premium, paleta, movimiento, canal alfa y criterios de rechazo.
- Esquema, tokens y catálogo actualizados a lienzos adaptables y ocho estilos.

## 1.3.0 — el grosor del trazo deja de depender de la escala

Corregido, a partir de un aviso del usuario ("las líneas son muy delgadas y se van a
perder cuando lo superponga a un video")

- **El `scale()` del módulo cambiaba el grosor sin que nadie lo decidiera.** `stroke-width`
  se aplica en el espacio local, así que un `3` dentro de `scale(1.44)` se dibujaba de 4.3.
  Como el sistema pide expresamente escalar el módulo hasta llenar el encuadre (§4 del
  diseño), y cada escena acaba con un factor distinto, la deriva era sistemática: overlays
  del mismo proyecto con grosores diferentes, todos más finos de lo que decía el estilo.
  Ahora los grosores se declaran en **px del lienzo 1920** (`--sw`, `--sw-thin`,
  `--sw-hero`, `--sw-rail`), `overlay.js` mide la escala real del grupo `.module` con
  `getCTM()` y la publica en `--mscale`, y las reglas `.st` dividen por ella. El número
  declarado es el número renderizado. Nueva trampa documentada: `pitfalls.md` §9.
- **Descartado `vector-effect: non-scaling-stroke`**, que resolvía lo mismo en una línea:
  hace que el patrón de guiones se calcule en unidades del viewport mientras DrawSVG lo
  calcula en unidades locales, y **toda animación de `drawSVG` sale fragmentada**.
  Comprobado en Chrome con el mismo frame y el mismo `dasharray`. `pitfalls.md` §10.
- **Grosores recalibrados midiendo, no estimando.** El método: renderizar el frame de
  clímax a **430 px de ancho** —la escala a la que se ve el video en un teléfono— sobre un
  fondo con zona clara, zona oscura y textura fina, y mirarlo sin ampliar. De ahí salen los
  dos umbrales que ahora comprueba `Overlay.audit()`: **≥6 px de lienzo** para 16:9 a
  1080p, **≥9 px** para móvil o vertical.

  | | s-line | s-tech | s-bold | s-hand | s-iso | s-soft3d | s-flat |
  |---|---|---|---|---|---|---|---|
  | antes (declarado) | 3 | 2 | 5 | 3.6 | 2.6 | 2.4 | 4.5 |
  | ahora (px de lienzo) | 6 | 5 | **11** | 7 | 5.5 | 5 | 9 |

- **El grosor era solo la mitad del problema: la otra era la opacidad.** `--line-2` sube de
  42 % a 55 % y `--line-3` de 18 % a 30 %. En `s-bold`, `.dim` va al 78 %, `.ghost` al 45 %,
  `.micro` al 62 % y `.dot.dim` al 78 %: ese pack ya no tiene ningún pelo translúcido.
  Nueva regla: nada que deba leerse baja del 55 % de opacidad, y "esto queda fuera" no se
  cuenta con `opacity: .3` —desaparece sobre metraje claro— sino con lo que hace la escena.
- `Overlay.audit()` reporta ahora la escala medida del módulo y el grosor resultante en px
  de lienzo, con los dos umbrales. `Overlay.moduleScale` queda expuesto.
- `estilos.html` declara su propia `--mscale` (dibuja en un viewBox de 420, no de 1920) para
  que el muestrario represente los grosores reales y no unos 4.6 veces más gruesos.
- Nueva regla dura en `SKILL.md`: **nunca escribir `stroke-width` literal**. Si una pieza
  necesita grosor propio, `calc(9 / var(--mscale))`.

Nota de migración
- Los proyectos ya entregados tienen su propia copia de `lib/`, así que no cambian solos.
  Para actualizar uno: copiar `assets/overlay.css` y `assets/overlay.js` sobre su `lib/`
  y quitar cualquier `stroke-width` literal de las escenas.


## 1.2.1 — escala del encuadre corregida

Corregido, a partir de una referencia visual del usuario
- El rango de tamaño del módulo era demasiado conservador: 900–1100 px de ancho y objetos
  de 120–180 px hacían que el overlay se leyera "pequeño y suelto" sobre el video. Nuevo
  objetivo: **1150–1350 px de ancho, 650–850 de alto y objetos protagonistas de 200–260 px**,
  es decir, el módulo llena unos dos tercios del ancho del encuadre.
- Nueva regla: **centrar el contenido, no el sistema de coordenadas**. Una escena que va
  de -232 a +98 tiene su centro en -67; al escalar sin compensar el `translate` del módulo,
  la cabeza de la persona se salía del lienzo.
- Las seis escenas del ejemplo reescaladas y reencuadradas con la nueva especificación.


## 1.2.0 — empaquetado para consumo automático

Añadido
- `spec/design-tokens.json`, `spec/styles.json` y `spec/overlay-manifest.schema.json`:
  el sistema visual, el catálogo de estilos y el contrato de salida en formato legible
  por máquina, para que otra herramienta (un agente de edición de video) pueda generar,
  validar o montar sin interpretar prosa.
- `overlays.json` como pieza de entrega obligatoria de cada proyecto: duración exacta,
  palabra de entrada y de salida por clip, beats anclados a palabras, encuadre sugerido,
  resultado de la auditoría y **las frases descartadas con su motivo**.
- `references/pitfalls.md`: ocho fallos reales, todos silenciosos (no dan error en
  consola). Es la referencia que más tiempo ahorra.
- `examples/dependencia-del-dueno/`: proyecto completo y verificado — seis escenas, su
  manifiesto, su README y la hoja de contactos.
- Regla de **densidad** en `design-system.md` y en las reglas duras: el hueco entre
  objetos relacionados no pasa de 0.6× su tamaño y el módulo mide 900–1100 px.
  Es lo que más se corrigió en revisión con un usuario real.
- Biblioteca de recursos **en masa** en `svg-assets.md` (persona, nodo, carril, moneda,
  caja con display, billetera, teléfono, repositorio, celda de estado, marcas, iconos en
  tinta de tres tonos) para los estilos `s-soft3d` y `s-flat`.
- Patrón de **cambio de estado por crossfade** en `motion-language.md`: los rellenos con
  degradado no se pueden interpolar.

Corregido
- `Overlay.seek()` usaba `tl.time(t, true)`. Ese `suppressEvents` silenciaba `onUpdate` y
  `call()`, así que **cualquier contador salía congelado en su valor inicial al capturar
  a video**. Ahora no suprime eventos.
- Los filtros SVG desplazaban el color de los rellenos oscuros (verde en `s-hand`):
  `color-interpolation-filters="sRGB"`.
- `s-soft3d`, `s-flat` y `s-bold` permitían trazos de 2px al 18 % de opacidad heredados de
  las clases `thin`/`dim`/`ghost` — invisibles sobre metraje comprimido. Ahora ningún
  trazo baja de 3px en esos packs.
- La sombra dura de `s-bold` duplicaba el texto (9px → 6px).

Ampliado
- Paleta de masa: `--fill-warn`, degradados `ovSoftWarn`, `ovSoftBad`, `ovSoftGlass`,
  `ovSoftDark`, clases `.solid.warn|bad|glass|dark`, `.rail`, `.dot`, `.c-line`, `.c-dim`,
  `.t-ink`.

## 1.1.0 — estilos de ilustración

Añadido
- Siete packs de estilo aplicables como clase en `#stage`: `s-line` (por defecto),
  `s-tech`, `s-bold`, `s-hand`, `s-iso`, `s-soft3d`, `s-flat`.
- Paso 1 del flujo: **preguntar el estilo antes de diseñar**, con guía de qué ofrecer
  según el tema del guion.
- `references/visual-styles.md` y `assets/estilos.html` (muestrario visual con la misma
  escena en los siete acabados, fondo claro/oscuro y reproducción de la entrada).
- `overlay.js` inyecta los filtros y degradados que necesitan los packs, para que
  `filter: url(#…)` nunca apunte a un id inexistente (eso hace desaparecer el elemento).

## 1.0.0 — base

- Flujo guion → beats → HTML con GSAP, fondo transparente, 1920×1080, 2–6 s por escena.
- Runtime `overlay.js`: escalado, loop limpio, control por teclado, captura determinista
  por `?t=`, fondos de revisión y croma, y `Overlay.audit()`.
- Sistema visual de trazo, biblioteca de recursos SVG, lenguaje de movimiento,
  sincronía a 2.6 palabras/segundo y guía de render con alfa para CapCut.
- GSAP 3.15 vendorizado (core + CustomEase, DrawSVG, MorphSVG, MotionPath, Physics2D,
  CustomWiggle). Sin dependencias en tiempo de ejecución.
- Reglas estructurales: colocación fuera (`.at`) y animación dentro (`.o`); el color por
  clase, nunca por atributo.
