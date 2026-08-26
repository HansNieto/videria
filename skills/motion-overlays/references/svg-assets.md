# Biblioteca de recursos vectoriales

Piezas base para componer ilustraciones. **No son iconos finales**: son puntos de partida
que se combinan, escalan y varían según la escena. Todas comparten el mismo estilo:
trazo de 3px, esquinas redondeadas, origen local en `(0,0)` = centro de la pieza,
colocadas con `transform="translate(x,y)"` y escaladas con `scale()`.

Estilo base (clase `.st` de `overlay.css`):

```css
.st { fill: none; stroke: var(--line); stroke-width: 3;
      stroke-linecap: round; stroke-linejoin: round; }
```

> **El color y el grosor van por clase, nunca por atributo.** En un elemento con `.st`,
> un `stroke="#0F0"` / `fill="…"` / `stroke-width="4"` es atributo de presentación y el CSS
> de `.st` lo anula: saldría blanco, sin relleno y con grosor 3. Usa `c-ok`, `c-warn`,
> `c-bad`, `c-accent`, `c-gold`, `c-dim`, `f-panel`, `f-ok`, `f-accent`, `hero`, `thin`,
> `dot`. Los atributos que `.st` **no** declara (`opacity`, `stroke-dasharray`,
> `transform`) sí funcionan. GSAP puede animar `stroke`/`fill` a un color literal porque
> escribe estilo inline, que gana sobre todo lo anterior.

Uso típico:

```html
<g class="module" transform="translate(960,540)">
  <g class="at" transform="translate(-320,0)">          <!-- coloca: no se anima -->
    <g class="o owner"> …persona… </g>                  <!-- anima: sin transform -->
  </g>
  <g class="at" transform="translate(300,40) scale(1.1)">
    <g class="o box"> …caja… </g>
  </g>
</g>
```

> **Colocación fuera, animación dentro.** GSAP reinterpreta el atributo `transform` como
> sus propios `x`/`y`: animar `y` sobre un grupo colocado con `translate(…)` lo desplaza
> a la posición equivocada. El `translate` va en `.at`; la clase animada `.o` no lleva
> transform propio.
>
> Todo lo que se anime individualmente va en su propio `<g>` con clase. Nunca animes un
> `<path>` suelto dentro de un grupo que también se mueve, salvo que sea intencional.

---

## Personas

### Persona base
```svg
<g class="person">
  <circle class="st" cx="0" cy="-34" r="16"/>
  <path   class="st" d="M-26,30 V22 A26,26 0 0 1 26,22 V30"/>
</g>
```

### Dueño (más presencia: trazo 4, ligeramente mayor, acento en el torso)
```svg
<g class="person owner">
  <circle class="st hero" cx="0" cy="-36" r="18"/>
  <path   class="st hero" d="M-29,32 V23 A29,29 0 0 1 29,23 V32"/>
  <path   class="st c-accent" d="M-14,32 V24 A14,14 0 0 1 14,24 V32"/>
</g>
```

### Empleado (torso secundario, misma altura, menos peso visual)
```svg
<g class="person employee">
  <circle class="st" cx="0" cy="-32" r="15"/>
  <path   class="st dim" d="M-24,28 V21 A24,24 0 0 1 24,21 V28"/>
</g>
```

### Cliente (anillo de acento: viene de fuera del sistema)
```svg
<g class="person client">
  <circle class="st c-accent" cx="0" cy="-32" r="15"/>
  <path   class="st" d="M-24,28 V21 A24,24 0 0 1 24,21 V28"/>
</g>
```

### Equipo (tres personas con solape y stagger)
```svg
<g class="team">
  <g class="person p1" transform="translate(-52,6) scale(.92)">…</g>
  <g class="person p2" transform="translate(0,0)">…</g>
  <g class="person p3" transform="translate(52,6) scale(.92)">…</g>
</g>
```
Anima con `stagger: {each:.08, from:"center"}`.

### Fila de clientes que espera
Repite `client` en `x = 0, 78, 156, 234` con `opacity` descendente (`1, .8, .6, .4`).
Para "esperando": un micro bob vertical desfasado (`y: -4`, yoyo, `repeat:-1`, `delay: i*.15`).

**Prohibido en personas:** caras, sonrisas, dedos, pelo, proporciones de caricatura.

---

## Dinero

### Moneda (con símbolo local)
```svg
<g class="coin">
  <circle class="st" r="26"/>
  <circle class="st c-gold" r="18" opacity=".55"/>
  <text class="tag t-gold" y="8" text-anchor="middle"
        style="font-size:22px">S/</text>
</g>
```
Variante metálica: añade `c-gold` también al círculo exterior.

### Pila de monedas
```svg
<g class="coin-stack">
  <ellipse class="st" cx="0" cy="24"  rx="30" ry="10"/>
  <ellipse class="st" cx="0" cy="8"   rx="30" ry="10"/>
  <ellipse class="st" cx="0" cy="-8"  rx="30" ry="10"/>
  <path    class="st" d="M-30,24 V-8 M30,24 V-8"/>
</g>
```
Anima cada elipse por separado (`stagger` desde abajo) para que la pila "crezca".

### Billete
```svg
<g class="bill">
  <rect class="st" x="-46" y="-26" width="92" height="52" rx="8"/>
  <circle class="st c-gold" r="13"/>
  <path class="st dim" d="M-36,-16 h8 M36,16 h-8"/>
</g>
```

### Billetera
```svg
<g class="wallet">
  <rect class="st" x="-52" y="-34" width="104" height="68" rx="12"/>
  <path class="st dim" d="M-52,-12 H24 a12,12 0 0 1 0,24 H-52"/>
  <circle class="dot" cx="24" cy="0" r="5"/>
</g>
```

### Caja del negocio (entra dinero por la ranura)
```svg
<g class="cashbox">
  <rect class="st" x="-74" y="-38" width="148" height="80" rx="12"/>
  <rect class="st" x="-20" y="-46" width="40" height="10" rx="5"/>
  <path class="st dim" d="M-74,-10 H74"/>
  <circle class="st dim" cx="0" cy="16" r="10"/>
</g>
```

### Dos recipientes: negocio vs. personal
Dos contenedores idénticos en forma pero distintos en color de acento
(`--accent` = negocio, `--line-2` = personal) y con etiqueta corta encima.
La idea "mezclar dinero" se cuenta moviendo monedas entre ellos, no con texto.

**Movimiento de dinero:** siempre en **arco** (`motionPath` o un tween x/y con dos pasos),
con rotación de 6–10° durante el vuelo y `scale` 1 → .9 al alejarse. El contenedor de
destino hace un `settle` corto al recibir.

---

## Dispositivos y archivos

### Celular
```svg
<g class="phone">
  <rect class="st" x="-42" y="-76" width="84" height="152" rx="14"/>
  <rect class="st dim" x="-33" y="-64" width="66" height="118" rx="6"/>
  <path class="st dim" d="M-12,64 h24"/>
</g>
```
Para "todo vive en tu celular": los archivos aparecen **dentro** del rect de pantalla con
`clip-path`, y luego salen en arco hacia el repositorio.

### Laptop
```svg
<g class="laptop">
  <rect class="st" x="-72" y="-58" width="144" height="94" rx="8"/>
  <path class="st" d="M-96,50 H96 L80,36 H-80 Z"/>
</g>
```

### Documento
```svg
<g class="doc">
  <path class="st" d="M-34,-46 H12 L34,-24 V46 H-34 Z"/>
  <path class="st dim" d="M12,-46 V-24 H34"/>
  <path class="st dim" d="M-20,4 H16 M-20,20 H6"/>
</g>
```

### Carpeta
```svg
<g class="folder">
  <path class="st" d="M-50,-30 h30 l12,14 h58 v50 a6,6 0 0 1 -6,6 h-88 a6,6 0 0 1 -6,-6 z"/>
  <path class="st dim" d="M-50,2 H50"/>
</g>
```

### Repositorio compartido (cilindro de datos)
```svg
<g class="repo">
  <ellipse class="st" cx="0" cy="-38" rx="46" ry="15"/>
  <path class="st" d="M-46,-38 V34 a46,15 0 0 0 92,0 V-38"/>
  <path class="st dim" d="M-46,-8 a46,15 0 0 0 92,0"/>
  <path class="st dim" d="M-46,14 a46,15 0 0 0 92,0"/>
</g>
```

### Servidor / rack
```svg
<g class="rack">
  <rect class="st" x="-52" y="-54" width="104" height="32" rx="7"/>
  <rect class="st" x="-52" y="-14" width="104" height="32" rx="7"/>
  <rect class="st" x="-52" y="26"  width="104" height="32" rx="7"/>
  <circle class="dot ok" r="4" cx="-34" cy="-38"/>
  <circle class="dot ok" r="4" cx="-34" cy="2"/>
  <circle class="dot ok" r="4" cx="-34" cy="42"/>
</g>
```

### Nube
```svg
<g class="cloud">
  <path class="st" d="M-46,20 C-64,20 -64,-6 -46,-9 C-49,-35 -12,-44 -1,-22
                       C12,-37 41,-30 38,-9 C56,-6 56,20 38,20 Z"/>
</g>
```

### Candado / llave
```svg
<g class="lock">
  <rect class="st" x="-26" y="-6" width="52" height="44" rx="9"/>
  <path class="st" d="M-14,-6 V-20 a14,14 0 0 1 28,0 V-6"/>
</g>
<g class="key">
  <circle class="st" cx="-26" cy="0" r="13"/>
  <path class="st" d="M-13,0 H32 M22,0 v10 M32,0 v12"/>
</g>
```

---

## Tiempo

### Calendario (rejilla de días)
```svg
<g class="calendar">
  <rect class="st" x="-56" y="-46" width="112" height="96" rx="10"/>
  <path class="st dim" d="M-56,-18 H56"/>
  <path class="st" d="M-30,-58 V-36 M30,-58 V-36"/>
  <!-- celdas: filas y=2, 22, 42 ; columnas x=-36,-12,12,36 -->
  <g class="days dot dim">
    <rect x="-42" y="-4" width="14" height="14" rx="4"/>
    <rect x="-18" y="-4" width="14" height="14" rx="4"/>
    <rect x="6"   y="-4" width="14" height="14" rx="4"/>
    <rect x="30"  y="-4" width="14" height="14" rx="4"/>
    <rect x="-42" y="20" width="14" height="14" rx="4"/>
    <rect x="-18" y="20" width="14" height="14" rx="4"/>
    <rect x="6"   y="20" width="14" height="14" rx="4"/>
  </g>
</g>
```
Para "7 días": anima las 7 celdas con `stagger .07` y colorea la última con `--bad`.

### Reloj
```svg
<g class="clock">
  <circle class="st" r="46"/>
  <path class="st hero" d="M0,-26 V2 H20"/>
  <path class="st dim" d="M0,-46 v8 M46,0 h-8 M0,46 v-8 M-46,0 h8"/>
</g>
```
La manecilla se anima con `rotation` y `transformOrigin: "0 0"` (o `svgOrigin`).

---

## Estructura, flujo y estado

### Nodo
```svg
<g class="node">
  <circle class="st" r="22"/>
  <circle class="dot" r="7"/>
</g>
```
Nodo central (el dueño): `r="30"` con clases `st hero f-accent`.

### Conexión + pulso que viaja
```svg
<path id="c1" class="st dim" d="M-300,-120 C-160,-120 -120,0 0,0"/>
<circle class="pulse dot accent" r="6"/>
```
```js
tl.fromTo("#c1", { drawSVG: "0% 0%" }, { drawSVG: "0% 100%", duration: .45, ease: "power2.inOut" })
  .fromTo(".pulse",
     { autoAlpha: 0 },
     { autoAlpha: 1, duration: .12 }, "<.15")
  .to(".pulse", { motionPath: { path: "#c1", align: "#c1", alignOrigin: [.5,.5] },
                  duration: .7, ease: "power1.inOut" }, "<");
```
**Conexión bloqueada:** `stroke: var(--line-3)`, `stroke-dasharray: "6 10"`, y el pulso se
detiene a mitad (`motionPath` con `end: .5`) y desaparece con `scale: .6`.

### Flecha
```svg
<g class="arrow">
  <path class="st" d="M-60,0 H52"/>
  <path class="st" d="M52,0 l-14,-10 M52,0 l-14,10"/>
</g>
```

### Límite / umbral
```svg
<path class="st limit c-warn" d="M-360,0 H360" stroke-dasharray="10 12"/>
<text class="tag t-warn" x="-360" y="-18">LÍMITE</text>
```

### Check, error, duda
```svg
<g class="ok">   <circle class="st c-ok" r="24"/>
                 <path class="st c-ok" d="M-10,1 L-2,9 L11,-8"/></g>
<g class="err">  <circle class="st c-bad" r="24"/>
                 <path class="st c-bad" d="M-8,-8 L8,8 M8,-8 L-8,8"/></g>
<g class="ask">  <circle class="st c-warn" r="24"/>
                 <text class="num t-warn" y="11" text-anchor="middle"
                       style="font-size:30px">?</text></g>
```

### Notificación / solicitud entrante
```svg
<g class="bubble">
  <rect class="st" x="-46" y="-34" width="92" height="58" rx="14"/>
  <path class="st" d="M-18,24 L-24,42 L-2,24"/>
  <path class="st dim" d="M-28,-10 H20 M-28,6 H4"/>
</g>
```
Contador de pendientes: círculo `--bad` r=13 en la esquina con la cifra dentro.

### Engranaje (proceso)
```svg
<g class="gear">
  <circle class="st" r="26"/>
  <circle class="st dim" r="10"/>
  <g class="teeth">
    <line y1="-30" y2="-40"/>
    <line y1="-30" y2="-40" transform="rotate(45)"/>
    <line y1="-30" y2="-40" transform="rotate(90)"/>
    <line y1="-30" y2="-40" transform="rotate(135)"/>
    <line y1="-30" y2="-40" transform="rotate(180)"/>
    <line y1="-30" y2="-40" transform="rotate(225)"/>
    <line y1="-30" y2="-40" transform="rotate(270)"/>
    <line y1="-30" y2="-40" transform="rotate(315)"/>
  </g>
</g>
```
Gira lento y constante (`rotation: 360, duration: 12, ease: "none", repeat: -1`); al fallar,
frena con `power3.out` y cambia a `--bad`.

---

## Objetos de negocio

### Caja / paquete (isométrico)
```svg
<g class="parcel">
  <path class="st" d="M-46,-14 L0,-38 L46,-14 V34 L0,58 L-46,34 Z"/>
  <path class="st dim" d="M-46,-14 L0,10 L46,-14 M0,10 V58"/>
</g>
```

### Tienda / local
```svg
<g class="store">
  <path class="st" d="M-72,-16 H72 V56 H-72 Z"/>
  <path class="st" d="M-84,-16 L-66,-46 H66 L84,-16 Z"/>
  <rect class="st dim" x="-18" y="14" width="36" height="42" rx="4"/>
</g>
```

### Mostrador con persona detrás
```svg
<g class="counter-scene">
  <g class="person owner" transform="translate(0,-46) scale(.9)">…</g>
  <path class="st" d="M-90,20 H90 V56 H-90 Z"/>
  <path class="st c-line" d="M-90,20 H90"/>
</g>
```

### Dashboard / gráfico
```svg
<g class="chart">
  <rect class="st dim" x="-90" y="-60" width="180" height="120" rx="10"/>
  <path class="st" d="M-64,36 V6 M-24,36 V-14 M16,36 V-2 M56,36 V-34"
        style="stroke-width:8" opacity=".9"/>
  <path class="st dim" d="M-90,52 H90"/>
</g>
```
Las barras crecen animando `scaleY` con `transformOrigin: "50% 100%"` y stagger .07.

### Moto de reparto
```svg
<g class="delivery">
  <circle class="st" cx="-46" cy="22" r="18"/>
  <circle class="st" cx="46"  cy="22" r="18"/>
  <path class="st" d="M-46,22 L-14,-6 H22 L46,22"/>
  <rect class="st c-accent" x="-40" y="-40" width="40" height="30" rx="5"/>
</g>
```

---

---

## Versión en masa (para `s-soft3d` y `s-flat`)

En los estilos de masa los objetos **no tienen contorno**: son formas rellenas. Estas son
las mismas piezas de arriba, reconstruidas. Clases: `solid` (masa blanca), `solid glass`
(superficie secundaria sobre otra masa), `solid accent|gold|ok|warn|bad`, `solid dark`
(pantallas), `spec` (brillo, **siempre arriba a la izquierda**), `rail` (conexión de 12px).

### Persona
```svg
<g class="o person">
  <circle class="solid" cx="0" cy="-34" r="18"/>
  <ellipse class="spec" cx="-7" cy="-41" rx="9" ry="6"/>
  <path class="solid accent" d="M-28,31 V22 A28,28 0 0 1 28,22 V31 Z"/>  <!-- dueño -->
</g>
```
Empleado: torso `solid` (blanco). Dueño: torso `solid accent`. Cliente: torso `solid alt`.
El torso es una **forma cerrada** (`Z`), no un arco de trazo.

### Nodo con icono dentro
```svg
<g class="o node">
  <circle class="solid glass" r="48"/>
  <ellipse class="spec" cx="-14" cy="-18" rx="22" ry="14"/>
  <!-- icono en masa blanca encima -->
</g>
```

### Conexión (nunca una línea)
```svg
<path id="c1" class="rail" d="M-192,-94 C-150,-94 -110,-60 -65,-32"/>
```
`rail` = 12px, cap redondo, blanco al 20 %. Se dibuja con `drawSVG` y admite `motionPath`
igual que un trazo fino. Bloqueada: `stroke` al 10 % + `strokeDasharray: '10 26'`.

### Moneda
```svg
<g class="o coin">
  <circle class="solid gold" r="30"/>
  <ellipse class="spec" cx="-8" cy="-10" rx="11" ry="7"/>
  <text class="tag t-ink" y="8" text-anchor="middle" style="font-size:24px">S/</text>
</g>
```
Sobre masa clara, el texto va en `t-ink` (tinta), nunca en blanco.

### Caja del negocio con display
```svg
<g class="o box">
  <rect class="solid" x="-130" y="-58" width="260" height="146" rx="22"/>
  <rect class="solid glass" x="-138" y="-80" width="276" height="28" rx="14"/>
  <rect class="slot" x="-30" y="-73" width="60" height="9" rx="4.5"/>
  <ellipse class="spec" cx="-56" cy="-40" rx="52" ry="16"/>
  <rect class="solid dark" x="-76" y="2" width="152" height="46" rx="11"/>
  <text class="num sm bal" y="36" text-anchor="middle" style="font-size:40px">S/0</text>
  <rect class="solid glass" x="-116" y="58" width="232" height="26" rx="11"/>  <!-- cajón -->
</g>
```
`.slot` y `.bal` se declaran en el `<style>` de la escena (`fill: rgba(11,18,32,.55)` y
`fill:#fff; font-variant-numeric: tabular-nums`).

### Billetera
```svg
<g class="o wallet">
  <rect class="solid glass" x="-58" y="-74" width="116" height="26" rx="7"/>   <!-- billete -->
  <rect class="solid" x="-85" y="-58" width="170" height="116" rx="18"/>
  <ellipse class="spec" cx="-32" cy="-38" rx="34" ry="12"/>
  <rect class="solid accent" x="-85" y="-4" width="170" height="52" rx="18"/>  <!-- solapa -->
  <circle class="solid gold" cx="52" cy="22" r="13"/>
</g>
```

### Teléfono
```svg
<g class="o phone">
  <rect class="solid" x="-44" y="-78" width="88" height="156" rx="16"/>
  <rect class="solid dark" x="-35" y="-66" width="70" height="122" rx="8"/>
  <ellipse class="spec" cx="-16" cy="-56" rx="18" ry="10"/>
  <rect class="solid" x="-11" y="64" width="22" height="6" rx="3"/>
</g>
```
Masa blanca con pantalla oscura: es lo que mejor se lee sobre cualquier metraje.

### Repositorio (cilindro)
```svg
<g class="o repo">
  <path class="solid glass" d="M-46,-38 V34 a46,15 0 0 0 92,0 V-38 Z"/>
  <ellipse class="solid" cx="0" cy="-38" rx="46" ry="15"/>
  <ellipse class="spec" cx="-16" cy="-40" rx="20" ry="7"/>
</g>
```
Para encenderlo en verde: duplica cuerpo y tapa con `solid ok` y haz crossfade.

### Bloque de día / celda de estado
```svg
<g class="o day">
  <rect class="solid glass dayblock" x="-32" y="-32" width="64" height="64" rx="15"/>
  <ellipse class="spec" cx="-9" cy="-16" rx="15" ry="9"/>
  <rect class="solid ok bar" x="-16" y="7" width="32" height="10" rx="5"/>
</g>
```
Apagar = `bar` a `scaleX: 0` + `dayblock` a `opacity: .3`.

### Marcas de estado (color plano, animables)
```svg
<circle class="mark" r="52"/>                      <!-- aro ámbar: identificado -->
<circle class="solid ok okdisc" r="26"/>           <!-- disco verde: resuelto -->
<path class="ckmark" d="M-11,0 L-3,9 L12,-9"/>     <!-- check blanco -->
```
```css
.mark   { fill: none; stroke: #FFB020; stroke-width: 9; }
.ckmark { fill: none; stroke: #fff; stroke-width: 6; stroke-linecap: round; }
```

### Icono en tinta sobre masa blanca
Cuando un objeto blanco necesita un símbolo dentro, se dibuja en tinta con tres tonos
para dar volumen (un cubo, por ejemplo):
```css
.ink-1 { fill: #0B1220; }   /* cara oscura   */
.ink-2 { fill: #17212F; }   /* cara media    */
.ink-3 { fill: #2A3646; }   /* cara superior */
.inkline { fill: none; stroke: #0B1220; stroke-width: 5; stroke-linecap: round; }
```
Un símbolo plano de un solo tono sobre un disco blanco se lee como mancha; con tres tonos
se lee como objeto.
## Composición de escenas completas

- **Dueño rodeado de solicitudes:** `owner` al centro, 5 `bubble` alrededor en un arco,
  conexiones curvas hacia el centro, pulsos que llegan y se acumulan sin salir.
- **Archivos saliendo del celular hacia el repositorio:** `phone` a la izquierda,
  `repo` a la derecha, 4 `doc`/`folder`/`key` que salen en arco y se ordenan en rejilla;
  después, 3 `employee` que se conectan al repo con líneas que se dibujan.
- **Decisión dentro de un límite de autoridad:** `employee` abajo, línea `limit` en medio,
  `owner` arriba; 3 decisiones pequeñas cruzan y se resuelven con `ok`; una grande rebota
  en el límite y sube al dueño.
- **Red que pierde el nodo central:** 6 `node` en anillo conectados al central; el central
  desaparece; 3 conexiones se apagan en cascada y sus nodos pasan a `--bad`, las otras
  siguen con su pulso.
- **Caja del negocio que se vacía:** `cashbox` al centro, `coin` entrando por la ranura,
  luego monedas saliendo en arco hacia `wallet`, y el contador perdiendo precisión
  (la cifra se sustituye por `?`).

## Reglas al crear recursos nuevos

1. Origen local en el centro de la pieza; nada de coordenadas absolutas dentro del grupo.
2. Coordenadas enteras, múltiplos de 2 donde sea posible.
3. Mismo grosor de trazo que el resto de la escena (no mezclar 2 y 4 sin motivo).
4. Cada parte que se anima por separado necesita su propio `<g class="…">`.
5. Si la pieza tiene que rotar, define `transform-origin`/`svgOrigin` explícito.
6. Verifica el `viewBox`: nada debe salirse del lienzo en ningún frame de la animación.
