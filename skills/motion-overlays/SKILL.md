---
name: motion-overlays
description: Diseña y programa motion graphics overlays (HTML + SVG inline + GSAP) con fondo transparente para superponer sobre video en CapCut, Premiere o DaVinci. Úsala cuando el usuario entregue un guion, locución, script o transcripción de video y pida animaciones, overlays, motion graphics, gráficos explicativos, B-roll animado, visuales para acompañar la narración, o cuando pida ilustraciones vectoriales SVG animadas (personas, dinero, procesos, flujos, diagramas, contadores, calendarios, dispositivos) sincronizadas con el ritmo del habla. También aplica a "animación para video", "overlay transparente", "motion graphics SaaS", "explainer visual".
license: MIT
---

# Motion Overlays — motion graphics para video

Convierte un guion hablado en un set de overlays HTML animados con GSAP, con fondo
transparente, listos para renderizar y montar encima del video.

## 0. Antes de diseñar (obligatorio)

1. **Pregunta el estilo visual al usuario** (§3, paso 1). Nunca empieces a dibujar sin
   esa respuesta: cambia cómo se construyen los SVG.
2. Carga las skills **gsap-core**, **gsap-timeline** y **gsap-plugins** (y **gsap-performance**
   si la escena tiene muchos elementos). Este skill asume su API correcta.
3. Lee `references/motion-language.md` y `references/design-system.md`.
4. Lee `references/visual-styles.md` para el estilo elegido.
5. Lee `references/svg-assets.md` cuando la escena necesite un objeto concreto
   (persona, moneda, caja, celular, carpeta, reloj…). No inventes iconos genéricos
   si ya hay un recurso base que puedes componer y variar.

## 1. Qué se entrega

```
motion-overlays/
├── lib/                 ← copiado tal cual desde assets/ de este skill
│   ├── gsap.min.js, CustomEase.min.js, DrawSVGPlugin.min.js, …
│   ├── overlay.css
│   └── overlay.js
├── 00-preview.html      ← galería para revisar todo
├── 00-estilos.html      ← muestrario de estilos (para elegir en el paso 1)
├── 01_<concepto>.html
├── 02_<concepto>.html
├── overlays.json        ← manifiesto de montaje (contrato para editores y agentes)
└── README.md            ← tabla + explicación de cada animación
```

Scaffold (una sola vez por proyecto):

```bash
mkdir -p motion-overlays/lib
cp -r ~/.claude/skills/motion-overlays/assets/vendor/*  motion-overlays/lib/
cp ~/.claude/skills/motion-overlays/assets/overlay.css  motion-overlays/lib/
cp ~/.claude/skills/motion-overlays/assets/overlay.js   motion-overlays/lib/
cp ~/.claude/skills/motion-overlays/assets/preview-template.html motion-overlays/00-preview.html
cp ~/.claude/skills/motion-overlays/assets/estilos.html          motion-overlays/00-estilos.html
```

Cada overlay se escribe partiendo de `assets/overlay-template.html`.

## 2. Reglas duras (no negociables)

| # | Regla |
|---|-------|
| 1 | `html, body { background: transparent }`. **Ningún** rectángulo, panel opaco o color que tape el video. Los scrims translúcidos (`rgba(…, .5)`) sí se permiten. |
| 2 | **No** escribir las frases del guion. Ya hay subtítulos. Texto solo como UI corta: `S/500`, `7 DÍAS`, `LÍMITE`, `OK`, `?`, `03`. Máx. ~3 palabras por etiqueta. |
| 3 | Lienzo **1920×1080**. El módulo **llena el encuadre**: 1150–1350 px de ancho y 650–850 de alto, objetos protagonistas de 200–260 px. El hueco entre objetos relacionados no pasa de **0.6× su tamaño**, y solo se justifica si algo lo recorre (ver `design-system.md` §4). |
| 4 | Duración **2–6 s**. Estructura obligatoria: **entrada → desarrollo → salida**. |
| 5 | En `t=0` y en `t=duración` **nada visible**. El overlay entra y sale limpio. |
| 6 | Solo `transform` + `opacity` para el movimiento (más `drawSVG`, `morphSVG`, color y `strokeDashoffset` cuando aportan). Nunca `top/left/width/height` para mover. |
| 6b | **Nunca escribas `stroke-width` literal.** El grosor lo ponen los tokens `--sw`, `--sw-thin`, `--sw-hero`, en px del lienzo 1920, y el runtime compensa el `scale()` del módulo. Si necesitas uno propio: `calc(9 / var(--mscale))`. Ver `design-system.md` §2. |
| 7 | Nada de `backdrop-filter`: en el render con alpha no hay nada detrás que desenfocar. Usa rellenos `rgba()`. |
| 8 | Una idea visual por archivo. Mejor 4 elementos coreografiados que 20 moviéndose a la vez. |
| 9 | Sin emojis, sin clipart, sin estilo PowerPoint, sin infografía escolar. Estética SaaS: editorial, técnica, premium. |
| 10 | Cero dependencias externas en runtime: GSAP va en `lib/`, el SVG va inline. Sin fuentes remotas. |
| 11 | **Colocación fuera, animación dentro** (ver §3, «Estructura del SVG»). Nunca animes `x`/`y` sobre un grupo que lleva `transform="translate(…)"`. |

## 3. Flujo de trabajo

### Paso 1 — Preguntar el estilo visual (obligatorio, antes de diseñar)

Usa **AskUserQuestion** con las 3–4 opciones que mejor encajen con el tema del guion
(el catálogo completo está en `references/visual-styles.md`). Marca una como
*(Recomendado)* y explica en una línea qué gana y qué cuesta cada una.

Guía para elegir qué ofrecer:

| Si el guion va de… | Ofrece |
|--------------------|--------|
| procesos, decisiones, cifras (caso general) | **Línea mínima** *(recomendado)*, Editorial técnico, Trazo grueso |
| datos, métricas, precisión, análisis | Editorial técnico *(recomendado)*, Línea mínima, 3D suave |
| consejo cercano, docente, personal | Dibujado a mano, Línea mínima *(recomendado)*, Flat humanista |
| infraestructura, áreas, "el sistema" | Isométrico, Línea mínima *(recomendado)*, Editorial técnico |
| producto, dinero, algo tangible | 3D suave, Trazo grueso, Línea mínima *(recomendado)* |
| equipos, personas, cultura | Flat humanista, Línea mínima *(recomendado)*, Dibujado a mano |
| se verá en móvil / metraje ruidoso | Trazo grueso *(recomendado)*, Línea mínima, Flat humanista |

Si el usuario ya indicó estilo en su mensaje, no preguntes: confírmalo en una línea y sigue.
Si el proyecto ya tiene overlays hechos, tampoco: mantén el estilo existente salvo que
pida cambiarlo.

La respuesta se aplica como clase en `#stage` (`s-tech`, `s-bold`, `s-hand`, `s-iso`,
`s-soft3d`, `s-flat`; sin clase = línea mínima) y **se anota en el README**.

### Paso 2 — Leer el guion completo antes de escribir nada

Marca dónde hay: cantidades, comparaciones, procesos, jerarquías, listas de 3–4 ítems,
antes/después, tiempo, dependencias, flujos entre actores.

### Paso 3 — Seleccionar momentos (ser restrictivo)

**Sí merece overlay:**
- números, dinero, cantidades que cambian
- un proceso o flujo entre actores (quién le pide qué a quién)
- estructura o jerarquía (nodo central, límites, capas)
- antes / después, con o sin
- tiempo (7 días, un calendario, un reloj)
- una lista corta de cosas concretas que se enumeran
- una metáfora que el audio insinúa pero no muestra (cuello de botella, caja negra, silo)

**No merece overlay:**
- saludos, transiciones, opiniones, CTA, frases de relleno
- ideas abstractas sin objeto ("es importante", "hay que mejorar")
- algo que se resuelve mejor con B-roll o con el presentador en cámara
- lo mismo que otro overlay ya dijo (no repetir metáfora)

Densidad objetivo: **1 overlay cada 12–20 s de narración**. Un guion de 60–70 s admite
4–6 overlays, no 12.

### Paso 4 — Beat sheet por overlay

Antes de programar, escribe las 6 líneas de `references/script-to-beats.md`:
concepto → metáfora → qué entra primero → qué pasa después → momento principal → cómo sale.
Si no puedes escribir la metáfora en una frase, la escena no está lista.

### Paso 5 — Sincronizar con la narración

Español explicativo ≈ **2.6 palabras/segundo**. Cuenta las palabras entre la palabra ancla
de un beat y la del siguiente, divide entre 2.6, y ese es el hueco.
Respeta las pausas semánticas: si el narrador dice "…sacas cien **para una compra personal**;
mañana otros cincuenta", el `-50` no aparece hasta que llega "mañana". Ese silencio visual
es parte del diseño. Declara los tiempos arriba del archivo:

```js
const BEATS = {
  in:    0.00,  // "Hoy entran"
  cash:  0.55,  // "quinientos soles"
  out1:  1.85,  // "sacas cien"
  hold:  2.45,  // "para una compra personal" ← pausa visual, no entra nada nuevo
  out2:  3.40,  // "mañana otros cincuenta"
  blur:  4.30,  // el saldo pierde claridad
  exit:  5.10
};
```

### Paso 6 — Programar

Un archivo por overlay, desde `assets/overlay-template.html`. Contrato:

```js
Overlay.scene({
  id: '01_dependencia',
  build(tl, ctx) {          // tl = timeline pausado ya creado por el runtime
    // ctx.q('.sel')  → primer elemento dentro de #stage
    // ctx.qa('.sel') → array de elementos
  }
});
```

El runtime resuelve: escalado a la ventana, fondo transparente, autoplay, loop con hueco,
`?paused=1&t=…` para captura frame a frame, `?bg=` para revisar contraste, y `Overlay.audit()`.

**Estructura del SVG — colocación fuera, animación dentro:**

```svg
<g class="frame pos-center">                    <!-- encuadre, solo CSS -->
  <g class="module" transform="translate(960,540)">   <!-- centro; NO se anima -->
    <g class="at" transform="translate(-320,40)">     <!-- COLOCA; NO se anima -->
      <g class="o coin"> … </g>                       <!-- ANIMA; sin transform -->
    </g>
  </g>
</g>
```

GSAP convierte el atributo `transform` en sus propios `x`/`y`: si animas `y` sobre un grupo
colocado con `translate(0,152)`, GSAP lo manda a `y=0` y la pieza salta de sitio.
Por eso la colocación vive en `.at` y la animación en `.o`. `.o` es además lo que
inspecciona `Overlay.audit()`.

### Paso 7 — QA (§6), y después README + preview

## 4. Sistema visual (resumen)

Detalle completo en `references/design-system.md`; los packs de estilo, en
`references/visual-styles.md`. Lo de abajo es la base **línea mínima**, sobre la que
cada pack cambia grosor, relleno, textura, paleta y —en `s-iso`, `s-soft3d` y `s-flat`—
también la forma de construir los objetos.

- **Trazo, no relleno.** La base del estilo son líneas de trazo, esquinas redondeadas,
  `stroke-linecap: round`, y rellenos translúcidos puntuales.
- **El grosor se declara en px del lienzo 1920**, no en unidades locales: los tokens
  `--sw` / `--sw-thin` / `--sw-hero` y `overlay.js` compensando el `scale()` del módulo.
  Mínimos: **6 px** para 16:9 a 1080p, **9 px** si el video se ve en móvil o vertical
  (por eso `s-bold` está en 11). Nunca `stroke-width` literal en el SVG.
- **El color va por clase, nunca por atributo.** En un elemento con `.st`, un
  `stroke="#..."` o `fill="..."` es atributo de presentación y el CSS de `.st` lo anula:
  el elemento saldría blanco sin relleno. Usa `.c-ok`, `.c-warn`, `.c-accent`, `.c-bad`,
  `.c-gold`, `.f-panel`, `.f-ok`, `.dot ok`, `.hero`, `.thin`. (GSAP sí puede animar
  `stroke`/`fill` a un color literal: eso se aplica como estilo inline y gana.)
- **Paleta:** blanco/gris claro como color base (legible sobre casi cualquier metraje),
  **un** acento (`--accent #5B8CFF`), y semánticos `--ok #2FD08A`, `--warn #FFB020`,
  `--bad #FF5D5D`, `--gold #F2C14E` (dinero). Máximo 2 colores además del base por escena.
- **Legibilidad sobre video:** todo elemento claro lleva `drop-shadow` oscuro suave
  (`var(--shadow-soft)`). Las sombras son transparentes, nunca cajas. El grosor es solo
  la mitad: nada que deba leerse baja del **55 %** de opacidad, y "esto queda fuera" no
  se cuenta con `opacity: .3` (desaparece sobre metraje claro) sino con lo que hace la
  escena.
- **Tipografía:** system-ui / Segoe UI. Etiquetas en mayúscula, `letter-spacing: .14em`,
  peso 600. Cifras con `font-variant-numeric: tabular-nums` para que no bailen al contar.
- **Personas:** vectoriales simplificadas, corporativas (cabeza + torso geométrico + trazo),
  diferenciadas por postura, accesorio y color de acento —nunca caricatura ni emoji—.

## 5. Lenguaje de movimiento (resumen)

Detalle y recetas en `references/motion-language.md`.

- **Duraciones:** micro `.18` · corta `.32` · estándar `.5` · macro `.8`.
- **Eases:** entrada `power3.out` o `"brand"`; salida `power2.in` (siempre más rápida que
  la entrada); traslados `power2.inOut`; acento `back.out(1.4)` — nunca más de 1.6.
- **Anticipación:** 4–8px en contra antes del movimiento principal, ~0.12s.
- **Stagger:** 0.06–0.10. Nunca todo a la vez; nunca todo estrictamente secuencial.
- **Movimiento secundario:** etiquetas y sombras entran 0.06–0.12s después de su objeto.
- **Jerarquía:** en cada instante hay **un** foco. Lo demás sostiene, se atenúa (`opacity .35`)
  o espera.
- **Salida con intención:** no es el reverso de la entrada. Sale por donde tiene sentido
  narrativo (lo que falla cae, lo resuelto se contrae al centro, lo que fluye se va con el flujo).

## 6. QA obligatorio antes de entregar

Abre cada archivo en Chrome y verifica:

- [ ] `Overlay.audit()` en consola: **0 elementos visibles** en `t=0` y en `t=fin`.
- [ ] Nada recortado: todo dentro de 1920×1080 con 64px de margen en cualquier frame.
- [ ] SVG alineados: `viewBox` correcto, trazos en la misma escala, sin medio píxel borroso.
- [ ] El loop no salta (start y end limpios → el bucle es continuo).
- [ ] `?bg=light`, `?bg=dark` y `?bg=photo`: legible en los tres.
- [ ] **Prueba de tamaño real:** el frame de clímax renderizado a **430 px de ancho**
      (la escala de un móvil) sobre un fondo con textura y zonas claras, mirado sin
      ampliar. Si a ese tamaño no distingues qué es cada objeto, sube el pack a `s-bold`,
      sube la opacidad de lo secundario o quita elementos.
- [ ] `Overlay.audit()` reporta el grosor en px de lienzo: **≥6** siempre, **≥9** si el
      video va a móvil o vertical.
- [ ] Duración entre 2 y 6 s (`Overlay.duration`).
- [ ] Ningún movimiento gratuito: si quitas un tween y la idea no se pierde, quítalo.
- [ ] Ninguna frase del guion escrita en pantalla.

## 6.bis Manifiesto de montaje (`overlays.json`)

Además del README en prosa, cada proyecto entrega un **`overlays.json`**: la misma
información en formato legible por máquina, para que un editor —humano o agente— coloque
los clips sin abrir los HTML. Esquema en `spec/overlay-manifest.schema.json`;
ejemplo completo en `examples/dependencia-del-dueno/overlays.json`.

Contiene, por overlay: archivo, duración exacta, concepto, metáfora, frase del guion,
**palabra de entrada y de salida** (con su índice dentro de la frase), los beats internos
anclados a palabras, el encuadre sugerido y el resultado de la auditoría. Y a nivel de
proyecto: el estilo aplicado, el ritmo de narración y las frases que **deliberadamente no
llevan overlay**, con su motivo —para que otro agente no "complete" lo que se descartó a
propósito—.

Con los beats anclados a palabras, si cambia la locución no hay que rediseñar: se
recalculan los tiempos con `palabras / 2.6` y se actualizan las constantes `BEATS`.

## 7. Informe final al usuario

Además del `README.md`, responde con:

1. qué HTML se crearon;
2. a qué frase del guion corresponde cada uno;
3. **en qué palabra exacta** debería entrar el overlay;
4. **en qué palabra exacta** debería salir;
5. confirmación de que se abren con doble clic en Chrome.

El README abre indicando el **estilo elegido** y su clase, y lleva esta tabla:

| Archivo | Parte del diálogo | Concepto visual | Duración |
|---------|-------------------|-----------------|----------|

Y debajo, 2–4 líneas por archivo explicando qué ocurre en la animación.

## 8. Anti-patrones

- ❌ Convertir cada párrafo en una tarjeta con texto.
- ❌ Fade in / fade out como toda la animación.
- ❌ Un panel de fondo oscuro que cubre el video "para que se lea".
- ❌ Iconos de librería genéricos pegados en fila.
- ❌ Todos los elementos moviéndose al mismo tiempo con el mismo ease.
- ❌ Overshoot exagerado, rebotes elásticos, giros de 360°.
- ❌ Elementos que quedan visibles al final del timeline.
- ❌ `position: absolute` animado con `top/left` en vez de `x/y`.

## 9. Para agentes automáticos

Si quien ejecuta esto no es una persona sino otra herramienta (un agente de edición de
video, un pipeline de generación), el contrato es:

| Necesita | Dónde está |
|----------|------------|
| Grosor de trazo y su compensación de escala | `design-system.md` §2 · `spec/design-tokens.json` → `stroke` |
| Tokens del sistema visual (color, tipografía, tiempos, densidad) | `spec/design-tokens.json` |
| Catálogo de estilos y cuándo aplicar cada uno | `spec/styles.json` |
| Forma del manifiesto de salida | `spec/overlay-manifest.schema.json` |
| Ejemplo completo y funcionando | `examples/dependencia-del-dueno/` |
| Errores conocidos que no dan error en consola | `references/pitfalls.md` |

Y en tiempo de ejecución, cada HTML expone:

```js
Overlay.duration        // duración exacta en segundos
Overlay.moduleScale     // escala real del grupo .module, medida con getCTM()
Overlay.seek(t)         // salta a un frame de forma determinista (para capturar)
Overlay.audit()         // { start:[], end:[], ok, moduleScale, stroke:{base,thin,hero} }
```

más los parámetros de URL `?paused=1&t=<s>` (captura), `?bg=<fondo>` (revisión o croma)
y `?loop=0`. Eso permite renderizar sin depender de la reproducción en tiempo real:
`Overlay.seek(i/fps)` + captura con `--default-background-color=00000000` da una secuencia
PNG con alfa reproducible frame a frame.

## Referencias

- `references/pitfalls.md` — **léelo antes de depurar**: ocho fallos que se ven como "está mal dibujado" y no dan error.
- `references/visual-styles.md` — los 7 estilos, cuándo usar cada uno y cómo se construyen.
- `references/design-system.md` — tokens, paleta, trazo, tipografía, layout, temas.
- `references/motion-language.md` — eases, tiempos, coreografía, recetas por tipo de escena.
- `references/svg-assets.md` — biblioteca de recursos vectoriales listos para componer.
- `references/script-to-beats.md` — del guion al beat sheet y a la tabla de entrega.
- `references/render-capcut.md` — render con transparencia y montaje en CapCut.

**Base técnica:** GSAP 3.15 vendorizado en `assets/vendor/` (core + CustomEase + DrawSVG +
MorphSVG + MotionPath + Physics2D + CustomWiggle). Todos los plugins de GSAP son gratuitos
desde la adquisición por Webflow, incluido uso comercial. La API correcta está en las
skills oficiales `gsap-core`, `gsap-timeline`, `gsap-plugins`, `gsap-utils`,
`gsap-performance` (repo `greensock/gsap-skills`).
