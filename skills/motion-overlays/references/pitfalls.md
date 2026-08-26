# Trampas conocidas

Diez fallos reales detectados construyendo overlays con esta skill, con su causa y su
arreglo. Todos se manifiestan como "se ve mal" o "no pasa nada", nunca como un error en
consola: por eso hay que conocerlos de antemano.

---

## 1 · El CSS de `.st` anula `stroke=` y `fill=`

**Síntoma:** dibujas `<circle class="st" stroke="#2FD08A" fill="rgba(...)"/>` y sale
blanco y sin relleno.

**Causa:** un atributo de presentación tiene menos prioridad que **cualquier** regla CSS.
`.st { fill: none; stroke: var(--line); stroke-width: calc(...) }` gana siempre.

**Arreglo:** el color y el grosor van por clase — `c-ok`, `c-warn`, `c-bad`, `c-accent`,
`c-gold`, `f-panel`, `f-ok`, `dot ok`, `hero`, `thin`. Los atributos que `.st` **no**
declara (`opacity`, `stroke-dasharray`, `transform`) sí funcionan.

> GSAP sí puede animar `stroke`/`fill` a un color literal: escribe estilo inline, que gana
> sobre todo lo demás. Por eso `to('.x', {stroke:'#FFB020'})` funciona aunque el atributo no.

---

## 2 · Animar `x`/`y` sobre un grupo que lleva `transform="translate(…)"`

**Síntoma:** una pieza colocada en `translate(0,152)` salta al centro en cuanto se anima.

**Causa:** GSAP parsea el atributo `transform` y lo convierte en sus propios `x`/`y`.
Un tween de `y: 0` la manda a la coordenada absoluta 0, no a "su sitio".

**Arreglo:** **colocación fuera, animación dentro**. El `translate` vive en un `<g class="at">`
y el grupo animado `<g class="o">` no lleva transform propio. Animar `scale`/`rotation`
sí conserva la posición; solo `x`/`y` la destruyen.

---

## 3 · `drawSVG` se come el `stroke-dasharray`

**Síntoma:** una línea punteada se dibuja con `drawSVG` y termina sólida.

**Causa:** DrawSVG implementa el trazado con `stroke-dasharray`/`stroke-dashoffset`;
al acabar deja su propio dasharray.

**Arreglo:** aplica el punteado **después** del trazado:

```js
tl.fromTo('#lim', { drawSVG: '0% 0%' }, { drawSVG: '0% 100%', duration: .6 }, t)
  .set('#lim', { strokeDasharray: '20 18' }, t + .62);
```

---

## 4 · `seek()` con `suppressEvents` congela los contadores

**Síntoma:** en la captura frame a frame todas las cifras salen con su valor inicial
(`S/0`) y los `.call()` no ocurren, aunque en reproducción normal todo funciona.

**Causa:** `tl.time(t, true)` — ese `true` es `suppressEvents` y silencia `onUpdate`,
`onStart` y `call()`.

**Arreglo:** el runtime ya usa `tl.time(t)` sin suprimir. Si escribes tu propio seek,
no suprimas eventos o **el .mov saldrá con los números congelados**.

---

## 5 · Los filtros SVG desplazan el color

**Síntoma:** con `s-hand`, los rellenos oscuros se tiñen de verde.

**Causa:** los filtros SVG interpolan en linearRGB por defecto.

**Arreglo:** `color-interpolation-filters="sRGB"` en el `<filter>`. Ya está en los defs
que inyecta `overlay.js`.

---

## 6 · Un degradado no se puede interpolar

**Síntoma:** en `s-soft3d` quieres que un objeto pase de azul a ámbar y el tween de `fill`
no hace nada (o salta de golpe).

**Causa:** los rellenos son `url(#ovSoftAccent)`; GSAP no interpola entre dos referencias
a degradados.

**Arreglo:** **crossfade**. Dibuja la forma dos veces, una por estado, la segunda con
`autoAlpha: 0`, y funde:

```svg
<circle class="solid accent" r="70"/>
<circle class="solid warn hubAlert" r="70"/>   <!-- oculta al inicio -->
```
```js
gsap.set('.hubAlert', { autoAlpha: 0 });
tl.to('.hubAlert', { autoAlpha: 1, duration: .35 }, BEATS.block);
```

Para indicadores pequeños (puntos, barras, aros) usa color plano en vez de degradado:
ahí sí se puede animar `fill` directamente.

---

## 7 · `filter: url(#id)` inexistente hace desaparecer el elemento

**Síntoma:** aplicas un pack de estilo y la escena se queda en blanco.

**Causa:** si el `<filter>` referenciado no está en el documento, Chrome no renderiza el
elemento (no es que ignore el filtro: no dibuja nada).

**Arreglo:** `overlay.js` inyecta los defs en el `<svg>` al arrancar cada escena. No
borres esa llamada ni referencies filtros propios sin declararlos.

---

## 8 · Las siluetas con relleno translúcido desaparecen sobre metraje oscuro

**Síntoma:** en `s-soft3d`, una persona con torso `.solid glass` se ve solo la cabeza.

**Causa:** `glass` es blanco al 30 %→8 %. Sobre video oscuro no hay contraste.

**Arreglo:** las figuras (personas, objetos protagonistas) van en `.solid` (masa blanca).
Reserva `glass` para superficies secundarias que están **encima** de otra masa: caras de
una caja, la solapa de una billetera, el interior de un nodo.

---

## 9 · El `scale()` del módulo cambiaba el grosor del trazo

**Síntoma:** las escenas de un mismo proyecto tienen trazos de grosores distintos sin
que nadie lo haya decidido, y todas se ven más finas de lo que dice el estilo. Sobre
video comprimido o en móvil, las líneas desaparecen.

**Causa:** `stroke-width` se aplica en el espacio local del elemento. Un `3` dentro de
`<g class="module" transform="translate(960,540) scale(1.44)">` se dibuja de 4.3px. Y el
propio sistema pide escalar el módulo hasta llenar el encuadre (`design-system.md` §4),
con un factor distinto en cada escena: la deriva es sistemática, no accidental.

**Arreglo:** ya está en el sistema. Los grosores se declaran en px del **lienzo 1920**
(`--sw`, `--sw-thin`, `--sw-hero`, `--sw-rail`), `overlay.js` mide la escala real del
módulo con `getCTM()` y la publica en `--mscale`, y las reglas `.st` dividen por ella.
Lo único que tienes que hacer tú:

- **no escribir `stroke-width` literal** en el SVG ni en el `<style>` de la escena;
- si una pieza necesita un grosor propio, dividirlo también:
  `stroke-width: calc(9 / var(--mscale))`;
- comprobar con `Overlay.audit()`, que ahora imprime la escala medida y el grosor
  resultante en px de lienzo.

---

## 10 · `vector-effect: non-scaling-stroke` rompe `drawSVG`

**Síntoma:** cambias el grosor a `non-scaling-stroke` para que no le afecte el `scale()`
del módulo, y todas las líneas animadas con `drawSVG` salen **fragmentadas**: en vez de
crecer de forma continua aparecen trozos sueltos a lo largo del trazado.

**Causa:** `non-scaling-stroke` no solo fija el ancho; hace que **toda la geometría del
trazo, guiones incluidos**, se calcule en unidades del viewport. DrawSVG calcula su
`stroke-dasharray` a partir de `getTotalLength()`, que está en unidades **locales**. Con
un módulo a `scale(1.44)` el patrón queda 1.44 veces corto y se repite a lo largo del path.

**Arreglo:** no lo uses. Para desacoplar el grosor de la escala, la vía correcta es la
del §9 (`calc(var(--sw) / var(--mscale))`), que no toca la geometría de los guiones.

Comprobado en Chrome: mismo frame, mismo `dasharray` (`235.7 187.1`), mismo `dashoffset`;
solo cambia `vector-effect`, y el trazado pasa de continuo a roto.

---

## Comprobación rápida antes de entregar

```js
Overlay.audit()   // 0 visibles en t=0 y t=fin, duración en rango,
                  // escala del módulo medida y grosor real en px de lienzo
```

Y a ojo, en `?bg=light` y `?bg=photo`: si un elemento desaparece sobre fondo claro,
es que dependía de un blanco translúcido sin masa detrás.
