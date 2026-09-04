# Sistema visual

Estética objetivo: motion graphics editorial premium. Para Videria vertical se usa por
defecto `s-neon`: masa translúcida local, frente nítido, aura controlada y conexiones
animadas. Para 16:9 sigue disponible el sistema SaaS de trazo. Nada de degradados sucios,
skeuomorfismo ni iconografía de stock.

El formato no está fijado en CSS: el `viewBox` de cada escena es la fuente de verdad y
`overlay.js` expone `Overlay.canvas`. Presets soportados: **1080×1920** (Videria,
predeterminado) y **1920×1080** (horizontal).

## 1. Tokens (ya definidos en `lib/overlay.css`)

```css
:root {
  /* base — legible sobre casi cualquier metraje */
  --ink:        #0B1220;   /* texto oscuro sobre chips claros */
  --paper:      #FFFFFF;
  --line:       rgba(255,255,255,.94);  /* trazo primario */
  --line-2:     rgba(255,255,255,.55);  /* trazo secundario / estructura */
  --line-3:     rgba(255,255,255,.30);  /* guías, rejilla, punteados */
  --muted:      rgba(255,255,255,.58);

  /* acento y semánticos */
  --accent:     #5B8CFF;
  --accent-2:   #8B7CFF;   /* solo si hace falta un segundo estado */
  --ok:         #2FD08A;
  --warn:       #FFB020;
  --bad:        #FF5D5D;
  --gold:       #F2C14E;   /* dinero */

  /* superficies translúcidas (nunca opacas) */
  --fill-1:     rgba(10,14,24,.55);   /* scrim de panel */
  --fill-2:     rgba(255,255,255,.06);
  --fill-accent:rgba(91,140,255,.16);

  /* sombras: transparentes, para legibilidad sobre video claro */
  --shadow-soft: drop-shadow(0 8px 24px rgba(0,0,0,.45));
  --shadow-hard: drop-shadow(0 2px 6px rgba(0,0,0,.6));

  /* geometría */
  --r-s: 8px; --r-m: 14px; --r-l: 22px;
  --u: 8px;       /* unidad de rejilla */

  /* grosor de trazo, en px del lienzo de salida (ver §2) */
  --sw:       6;  /* estándar */
  --sw-thin:  4;  /* detalle  */
  --sw-hero:  8;  /* foco     */
  --sw-rail: 14;  /* conexión en packs de masa */
}
```

Reglas de color:

- Base blanco/gris + **un** acento por escena. Los semánticos entran solo cuando el
  guion habla de estado (bien / mal / alerta / dinero).
- El rojo aparece únicamente cuando algo **falla**; el verde solo cuando algo **se resuelve**.
- No colorear todo: un objeto de color entre objetos neutros es el foco. Si todo tiene
  color, no hay foco.
- El dorado (`--gold`) es exclusivo de dinero. No lo uses de decoración.

## 2. Trazo y forma

### El grosor se declara en píxeles del lienzo de salida, no en unidades locales

Esta es la regla que más se equivoca, porque falla en silencio.

Un `stroke-width: 3` dentro de un módulo con `transform="translate(960,540) scale(1.44)"`
**no** se dibuja de 3px: se dibuja de 4.3. Y como el sistema pide expresamente escalar el
módulo hasta que llene el encuadre (§4), esa deriva no es un accidente puntual sino algo
que le pasa a todas las escenas, cada una con un factor distinto. Dos overlays del mismo
proyecto acaban con grosores diferentes sin que nadie lo haya decidido.

Solución del sistema: **los tokens `--sw`, `--sw-thin`, `--sw-hero` y `--sw-rail` están en
px del lienzo de salida**, y `overlay.js` mide con `getCTM()` la escala real del grupo `.module`
y la publica en `--mscale`. Las reglas `.st` dividen por ella:

```css
.st       { stroke-width: calc(var(--sw)      / var(--mscale)); }
.st.thin  { stroke-width: calc(var(--sw-thin) / var(--mscale)); }
.st.hero  { stroke-width: calc(var(--sw-hero) / var(--mscale)); }
```

Consecuencias prácticas:

- Escala el módulo lo que necesites para llenar el encuadre: el grosor no se mueve.
- **No escribas `stroke-width` literal** en el SVG ni en el `<style>` de la escena. Si una
  pieza necesita un grosor propio, decláralo también dividido:
  `stroke-width: calc(9 / var(--mscale))`.
- `Overlay.audit()` reporta la escala medida y el grosor resultante en px de lienzo.

> No uses `vector-effect: non-scaling-stroke`, que parece resolver lo mismo en una línea:
> **rompe `drawSVG`** (el patrón de guiones pasa a unidades del viewport mientras DrawSVG
> lo calcula en unidades locales, y las líneas salen fragmentadas). Ver `pitfalls.md` §10.

### Construcción

- `fill: none; stroke: var(--line); stroke-linecap: round; stroke-linejoin: round`
  es la construcción por defecto (clase `.st` en `overlay.css`).
- Tres pesos y nada más: `.st.thin` detalle · `.st` estándar · `.st.hero` foco.
  Los valores concretos los pone el pack de estilo (`visual-styles.md`).
- Radios: 8 (chips), 14 (tarjetas), 22 (contenedores grandes). Coherencia sobre variedad.
- Todo se dibuja sobre una rejilla de 8px. Coordenadas enteras: medio píxel = trazo borroso.
- Los rellenos existen solo como translúcidos (`--fill-1`, `--fill-accent`) o como
  puntos/nodos sólidos pequeños.
- Punteado para lo potencial / inactivo / futuro: `stroke-dasharray: 6 10` con `--line-3`.
- Con trazo grueso, **el hueco interior de un glifo tiene que seguir siendo hueco**: un
  círculo de r=12 con trazo de 7 deja 8px de aire y se lee; con trazo de 11 se cierra.
  Si subes el grosor, sube también el tamaño de los detalles interiores.

## 3. Tipografía

```css
font-family: system-ui, "Segoe UI Variable Display", "Segoe UI", Inter, Roboto,
             "Helvetica Neue", Arial, sans-serif;
```

| Rol | Tamaño (en lienzo 1920) | Peso | Tracking |
|-----|--------------------------|------|----------|
| Cifra héroe (`.num`) | 88–140px | 700 | -0.02em |
| Cifra secundaria | 48–64px | 600 | -0.01em |
| Etiqueta UI (`.tag`) | 22–26px | 600 | .14em, MAYÚSCULAS |
| Micro-dato (`.micro`) | 16–18px | 500 | .10em, MAYÚSCULAS |

- Siempre `font-variant-numeric: tabular-nums` en cifras que cambian.
- Máx. 2 tamaños tipográficos por escena.
- El texto es UI, no discurso: `S/500`, `-S/100`, `7 DÍAS`, `LÍMITE`, `OK`, `?`, `03/12`.
- Prohibido escribir frases del guion.

## 4. Layout según el proyecto

### Videria vertical 1080×1920 — predeterminado

```
┌────────────────────────────┐
│ margen 60 px               │
│ ┌────────────────────────┐ │
│ │ MOTION 820–960 ×       │ │  ← normalmente y=120…820
│ │ 520–760                │ │
│ └────────────────────────┘ │
│    cara / manos libres      │
│                            │
│    subtítulos libres        │
└────────────────────────────┘
```

El módulo no se centra por costumbre: se coloca sobre la zona realmente libre del clip.
Hay que inspeccionar un frame del video antes de fijar coordenadas. La plantilla usa
`translate(540,500)` porque está pensada para un presentador centrado en la mitad inferior.

| Medida vertical | Objetivo |
|---|---|
| Margen seguro | ≥60 px |
| Ancho del módulo | 820–960 px (máx. 980) |
| Alto del módulo | 520–760 px |
| Nodo protagonista | 150–230 px |
| Elementos en clímax | 3–5 nodos + conexiones cuando exista causalidad |

### Horizontal 1920×1080

```
┌────────────────────────────────────────────────────────┐  1920×1080
│  margen de seguridad 96px                              │
│   ┌──────────────────────────────────────────────┐     │
│   │      MÓDULO PRINCIPAL  ~1250×780             │     │  ← todo lo importante
│   │      (centrado, o en el tercio izq/der)      │     │     vive aquí
│   └──────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────┘
```

### Densidad (aplica a ambos formatos)

Un overlay se ve "suelto" o "profesional" según la **relación entre el tamaño de los
objetos y el hueco que los separa**, no según el tamaño del lienzo. Reglas:

| Medida | Objetivo |
|--------|----------|
| Hueco entre dos objetos relacionados | **≤ 0.6 ×** el diámetro del objeto mayor |
| Ancho del módulo completo | **1150–1350 px** de los 1920 (nunca más de 1450) |
| Alto del módulo completo | **650–850 px** de los 1080 |
| Objeto protagonista | **200–260 px** de diámetro |
| Objeto secundario | 120–180 px |
| Separación entre hermanos de una serie (días, ítems) | 10–20 % de su ancho |

Cómo se aplica en la práctica: se dibuja la escena con las distancias que "parecen bien",
se miden, y luego se **multiplican las distancias por ~0.7 y la escala del módulo hasta que
el conjunto llene el encuadre** (dos tercios del ancho, tres cuartos del alto).
El resultado tiene objetos grandes y poco aire: eso es
lo que hace que se lea como una sola pieza y no como elementos repartidos.

Excepción: un hueco grande **solo** se justifica cuando algo lo recorre (una moneda que
viaja, un pulso que avanza). Ahí el hueco es el trayecto, y acortarlo mata la animación.
Si nada lo cruza, sobra.

- El módulo se agrupa en un `<g>` o `<div>` único (`.module`) para que en CapCut se pueda
  escalar y reposicionar como una sola pieza.
- Variantes de encuadre listas en `overlay.css`: `.pos-center`, `.pos-left`, `.pos-right`,
  `.pos-top`, `.pos-bottom`. Cambian la posición del módulo sin tocar la animación.
- Deja el tercio donde está la persona libre: si el presentador está a la derecha,
  usa `.pos-left`.
- Nunca pegues nada a menos de 96px del borde.
- **Centra el contenido, no el sistema de coordenadas.** Si la escena ocupa de -232 a +98,
  su centro está en -67: compensa el `translate` del módulo (`translate(960, 540+67*escala)`)
  o la cabeza de la persona se saldrá del lienzo al escalar.

## 5. Legibilidad sobre video

El overlay no se ve en un monitor con fondo negro: se ve encima de metraje comprimido, a
veces en un móvil. Un trazo que en el editor parece correcto puede desaparecer ahí.

### Mínimos medidos

El lienzo son 1920px, pero el espectador casi nunca los ve. Lo que importa es a cuánto
queda el trazo **en la pantalla real**:

| Dónde se ve | Escala respecto al lienzo | Un trazo de 6px queda en | Uno de 11px queda en |
|---|---|---|---|
| Monitor, 16:9 a 1080p | 0.56 | 3.4 px ✔ | 6.2 px ✔ |
| Móvil horizontal / feed | 0.22 | 1.3 px — al límite | 2.5 px ✔ |
| Vertical recortado, metraje con detalle | 0.22 y peor contraste | se pierde ✖ | 2.5 px ✔ |

De ahí los dos umbrales que usa `Overlay.audit()`:

- **≥ 6 px** de lienzo: mínimo para 16:9 a 1080p.
- **≥ 9 px** de lienzo: mínimo para móvil, vertical o metraje con mucho detalle.
  Es el motivo de que `s-bold` exista y esté en 11 px.

**El grosor es solo la mitad.** La otra es la opacidad: un trazo de 11px al 30 % de blanco
se pierde igual que uno de 3px. Por eso los tokens secundarios se mantienen altos
(`--line-2` al 55 %, `--line-3` al 30 %) y los packs pensados para video los suben más.
Si un elemento tiene que leerse, no lo bajes de **55 %** de opacidad, por grueso que sea.

### Cómo medirlo en vez de estimarlo

No confíes en cómo se ve a pantalla completa. Renderiza el frame a **430px de ancho**
—que es la escala a la que se ve en un móvil— sobre un fondo difícil, y míralo a tamaño
nativo, sin ampliar:

```js
await page.setViewport({ width: 430, height: 242 });   // 0.22 × el lienzo
await page.addStyleTag({ content: fondoConTexturaYZonasClaras });
```

Si a ese tamaño no distingues qué es cada objeto, el trazo es demasiado fino, la opacidad
demasiado baja o hay demasiados elementos. Los tres se arreglan antes de entregar.

### El resto

- Todo grupo claro lleva `filter: var(--shadow-soft)` (ya aplicado por `.module`).
  Es sombra transparente: separa del metraje sin introducir una caja.
- Si un dato es crítico y el metraje puede ser muy claro, usa un chip translúcido
  (`--fill-1`) con radio y trazo `--line-2`, no un rectángulo opaco.
- **Atenuar tiene suelo.** Bajar un elemento a `opacity: .3` funciona sobre metraje oscuro
  y lo hace desaparecer sobre metraje claro. Para "esto queda fuera" no bajes de `.5`:
  comunícalo con lo que hace la escena (una conexión que se retrae, un carril que se
  apaga), no solo con opacidad.
- Prohibido `backdrop-filter`: en el render con alpha no hay nada detrás que desenfocar,
  y en CapCut el overlay es una capa independiente.
- Verifica en `?bg=light`, `?bg=dark`, `?bg=photo`.

## 6. Personas (estilo corporativo simplificado)

- Construcción: círculo de cabeza (r 22–28) + torso como forma redondeada (no palito),
  hombros rectos, sin cara, sin manos con dedos.
- Diferenciación por **rol**, no por detalle facial:
  - **Dueño:** trazo `--line` grueso (4), postura frontal, un poco más grande, a veces
    con acento en el torso.
  - **Empleado:** trazo 3, `--line-2` en el torso, tamaño normal.
  - **Cliente:** trazo 3 con acento en `--accent`, suele estar en fila o fuera del sistema.
  - **Proveedor:** con caja/paquete al lado.
  - **Equipo:** tres personas iguales con stagger, ligeramente superpuestas.
- Nunca: ojos, sonrisas, pelo detallado, proporciones de caricatura, poses exageradas.
- La emoción se comunica con **posición, ritmo y color**, no con expresión facial.

## 7. Composición

- Regla de 3–5 elementos por escena. Si necesitas más, el concepto está mal recortado.
- Jerarquía por tamaño → por color → por movimiento (en ese orden).
- El foco entra al centro óptico (≈ 45% de altura), no al centro geométrico.
- Simetría para orden/sistema; asimetría deliberada para tensión/desequilibrio.
- Espacio negativo generoso: el overlay compite con el video, no lo tapa.

## 8. Densidad de color por estado

| Estado narrativo | Tratamiento |
|------------------|-------------|
| Normal / funcionando | `--line` + acento puntual, movimiento fluido |
| Acumulación / saturación | mismo color pero más elementos, ritmo más rápido, stagger corto |
| Bloqueo / fallo | `--bad` solo en el punto que falla, resto atenuado a `.35` |
| Resolución | `--ok`, movimiento que se ordena y se detiene |
| Potencial / propuesta | punteado `--line-3` que se vuelve sólido |
