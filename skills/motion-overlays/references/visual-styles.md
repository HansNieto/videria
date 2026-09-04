# Estilos de ilustración

El estilo **se pregunta al usuario antes de diseñar** (ver SKILL.md §3, paso 1). No es
decoración: cambia cómo se construyen los SVG y, en algunos casos, cómo se mueven.

La clase va en `#stage`:

```html
<div id="stage" class="s-tech">
```

o se pasa al runtime: `Overlay.scene({ id: '…', style: 's-tech', build … })`.

Cada pack define al menos tres números: `--sw` (estándar), `--sw-thin` (detalle) y
`--sw-hero` (foco), en px del **lienzo de salida**. `overlay.js` compensa el `scale()` del
módulo, así que el número declarado es el que se ve (ver `design-system.md` §2).

Los filtros y degradados que necesitan los packs (`#ovRoughen`, `#ovSoft`, `#ovSpec`…)
los inyecta `overlay.js` automáticamente en el `<svg>`: no hay que copiarlos a mano.

Muestrario visual: `assets/estilos.html` (se copia al proyecto como `00-estilos.html`).

---

## Resumen

| Estilo | Clase | Trazo (px de lienzo)<br>`--sw / --sw-thin / --sw-hero` | Aguanta móvil<br>(≥9 px) | Coste | Mejor para |
|--------|-------|--------------|------|-------|-----------|
| **Neón editorial premium** | `s-neon` | **10 / 7 / 14** | **sí** | medio | Videria vertical, relaciones, decisiones, acabado de alta producción |
| **Línea mínima** | *(ninguna)* | 6 / 4 / 8 | no | bajo | procesos y datos en 16:9 |
| **Editorial técnico** | `s-tech` | 5 / 3.5 / 7 | no | bajo | métricas, sistemas, precisión, tono analítico |
| **Trazo grueso** | `s-bold` | **11 / 7 / 15** | **sí** | bajo | metraje ruidoso, vertical, redes sociales |
| **Dibujado a mano** | `s-hand` | 7 / 5 / 10 | casi | bajo | tono cercano, docente, "te lo explico" |
| **Isométrico** | `s-iso` | 5.5 / 4 / 7 | no | **alto** | infraestructura, flujos entre áreas, "el sistema" |
| **3D suave** | `s-soft3d` | 5 / 4 / 6.5 | la masa sí, el trazo no | **alto** | producto, dinero, algo tangible y premium |
| **Flat humanista** | `s-flat` | 9 / 6 / 12 | sí | medio | personas, equipos, tono amable de marca |

La columna "aguanta móvil" es el umbral medido en `design-system.md` §5: por debajo de
**9 px de lienzo** el trazo cae de 2 px reales cuando el video se ve en un teléfono.
Los packs de trazo fino están pensados para 16:9 a 1080p; **si el video es vertical o va
a redes, usa `s-neon` o `s-bold`**, no uno fino con la esperanza de que se lea.

**Recomendación por defecto:** `s-neon` para Videria vertical; *línea mínima* para 16:9;
*trazo grueso* para una alternativa vertical sobria. `s-neon` combina masa, trazo grueso,
profundidad y rutas animadas: está calibrado para sobrevivir a la compresión de un feed
sin quedarse en un clipart plano. Lee `neon-vertical.md` antes de construirlo.

### Estilos de trazo vs. estilos de masa

| | Trazo | Masa |
|---|---|---|
| Estilos | línea mínima, editorial técnico, trazo grueso, dibujado a mano | neón editorial, 3D suave, flat humanista |
| El dibujo es… | el contorno | la silueta rellena |
| Sobre metraje con detalle | puede perderse si el trazo es fino | siempre se ve |
| Coste | bajo | alto (hay que redibujar los objetos) |

**Si el usuario dice que no quiere líneas finas**, hay dos salidas distintas:

- **Mantener el dibujo y engordarlo** → `s-bold`. Es una clase, se aplica a escenas ya
  hechas y sube el trazo a 11 px de lienzo. Sigue siendo dibujo de contorno.
  Si ya estás en `s-bold` y aun así se ve fino, el problema no es el pack: revisa que la
  escena no esté usando `.thin` + `.dim` para elementos estructurales (7 px al 78 % es
  detalle, no estructura) y sube esos a `.st` a secas.
- **Cambiar a masa** → `s-soft3d` (con volumen) o `s-flat` (plano). Ya no hay contornos:
  las formas son sólidas. Obliga a redibujar los objetos y a repensar las conexiones
  (una línea de trazo pasa a ser un carril redondeado de `--sw-rail` px con un punto
  que lo recorre).

En los packs de masa y en `s-bold` ningún trazo baja de 4px de lienzo y las clases `thin`,
`dim` y `ghost` están reforzadas en el CSS: en esos estilos **no existe** el pelo
translúcido que desaparece en video comprimido.

---

## 0 · Neón editorial premium (`s-neon`) — predeterminado en Videria

**`--sw: 10 · --sw-thin: 7 · --sw-hero: 14 · --sw-rail: 16`**. Combina paneles azul
noche translúcidos, frente blanco/cian nítido y una aura de color controlada. Se construye
como una mini-historia de **3–5 nodos conectados**, no como un icono individual.

- **Sí:** video vertical, TikTok/Reels, decisiones, flujos entre personas, causa y efecto.
- **No:** más de cinco nodos simultáneos ni fondos completos.
- El glow se aplica a nodos heroicos y nunca reemplaza el contorno.
- Las conexiones son curvas, cortas y con dirección; una partícula puede recorrerlas.
- Rojo solo significa fallo. Azul/cian llevan la relación normal.
- La secuencia revela significado: nodo → ruta → actor → consecuencia → pausa → salida.
- Lee `neon-vertical.md` para composición sobre el presentador y criterios de rechazo.

---

## 1 · Línea mínima *(por defecto en 16:9)*

Trazo blanco, esquinas redondeadas, rellenos translúcidos puntuales, un acento.
Es el sistema descrito en `design-system.md`.

- **`--sw: 6 · --sw-thin: 4 · --sw-hero: 8`** (px de lienzo).
- **Sí:** cualquier tema; sobre todo procesos, cifras y relaciones, en 16:9.
- **No:** cuando el cliente pide explícitamente algo "con más producción", ni cuando el
  video se va a ver en móvil o vertical (ahí, `s-bold`).
- **Movimiento:** el estándar del `motion-language.md`.

---

## 2 · Editorial técnico (`s-tech`)

Blueprint de producto: **`--sw: 5 · --sw-thin: 3.5 · --sw-hero: 7`**, tipografía
**monoespaciada**, cotas, guías punteadas y un aire de plano técnico. Comunica rigor.
Es el pack más fino del catálogo: úsalo solo si el video se ve en 16:9.

```svg
<g class="o node">
  <rect class="st" x="-60" y="-40" width="120" height="80" rx="4"/>
  <path class="guide" d="M-90,-40 H-70 M-90,40 H-70"/>   <!-- cota -->
  <text class="micro" x="-104" y="4" text-anchor="end">80</text>
</g>
```

- Radios pequeños (2–6px): aquí lo redondeado resta.
- Las etiquetas son datos (`04`, `S/500`, `MAX`), no rótulos.
- Añade una guía o una cota por escena, nunca más: es condimento.
- **Movimiento:** más seco. `power2.out` en 0.35–0.45, sin overshoot, stagger 0.05.
  Las líneas se dibujan con `drawSVG` en vez de aparecer.

---

## 3 · Trazo grueso editorial (`s-bold`)

**`--sw: 11 · --sw-thin: 7 · --sw-hero: 15`**, sombra dura desplazada, contraste alto.
Es el único pack calibrado midiendo, no estimando: el frame renderizado a 430px de ancho
—la escala a la que se ve en un teléfono— sobre un fondo con zona clara, zona oscura y
textura fina. A 11px el trazo cae a 2.5px reales y sigue leyéndose; a 5–7px se deshace.

- También sube las opacidades, porque el grosor solo es la mitad del problema:
  `.dim` al 78 %, `.ghost` al 45 %, `.micro` al 62 %, `.dot.dim` al 78 %.
  En este pack **no existe** el pelo translúcido que desaparece en video comprimido.
- Menos elementos que en línea mínima: el grosor ya ocupa mucho.
- El acento en bloques, no en líneas finas.
- Cuidado con los detalles interiores: un círculo de r=12 con trazo de 7 aún respira;
  con menos radio se cierra. Si el glifo lleva detalle fino, agrándalo.
- **Movimiento:** con peso. Entradas 0.5–0.6 con `settle`, aterrizajes marcados,
  stagger 0.08. Evita movimientos pequeños: no se leen.

---

## 4 · Dibujado a mano (`s-hand`)

El pack aplica un filtro de desplazamiento (`#ovRoughen`) al módulo entero: el trazo
tiembla ligeramente, como dibujado. Se mantiene la tipografía limpia — nada de fuentes
tipo cómic, que rompen el tono corporativo.

- **Sí:** contenido docente, tono de consejo, "esto lo he vivido".
- **No:** dinero, cifras exactas, informes. El temblor resta autoridad.
- **Movimiento:** algo más suelto. Duraciones +15%, `back.out(1.4)` permitido,
  rotaciones de 1–3° en las entradas. Nunca perfecto.
- Cuidado: el filtro se aplica al grupo, así que **no lo pongas en un elemento que
  escale mucho** (el temblor escala con él). Si una pieza crece de 0.5 a 1.5, sácala
  del grupo filtrado.

---

## 5 · Isométrico (`s-iso`) — **construcción distinta**

Proyección 2:1. Todo vive en un plano inclinado y los objetos se extruyen hacia arriba.
Muy bueno para "el sistema visto desde fuera": áreas, capas, infraestructura.

```svg
<g class="iso">                      <!-- proyecta al plano isométrico -->
  <path class="iso-face" d="M-120,-120 H120 V120 H-120 Z"/>   <!-- suelo -->
  <path class="st" d="M-120,-40 H120"/>                        <!-- carril -->
</g>
<!-- el volumen NO se proyecta: se dibuja ya en isométrico -->
<g class="at" transform="translate(0,-60)">
  <g class="o block">
    <path class="st iso-top"  d="M0,-30 L52,0 L0,30 L-52,0 Z"/>
    <path class="st iso-side" d="M-52,0 L0,30 L0,86 L-52,56 Z"/>
    <path class="st iso-face" d="M52,0 L0,30 L0,86 L52,56 Z"/>
  </g>
</g>
```

- Los **planos** (suelo, rejilla, carriles) van dentro de `.iso`; los **volúmenes** se
  dibujan directamente con caras (top / side / face), no se proyectan.
- Una sola fuente de luz: la cara superior más clara, la izquierda media, la derecha
  más oscura. Siempre igual en toda la escena.
- Movimiento en ejes isométricos: subir = `y` negativo puro; avanzar en el plano =
  combinación (`x: 52, y: 30`). Un objeto que se mueve "recto" en pantalla rompe la ilusión.
- **Movimiento:** entradas verticales (los objetos "aterrizan" en el plano con
  `settle` y una sombra que crece), stagger 0.09. Nada de rotaciones libres.
- **Coste alto:** cada objeto son 3 caras. Máximo 4 objetos por escena.

---

## 6 · 3D suave (`s-soft3d`) — **construcción distinta**

Vector con volumen: formas **rellenas** con degradado vertical, un brillo especular
arriba a la izquierda y sombra suave. El aspecto "ilustración de producto SaaS".

```svg
<g class="o coin">
  <circle class="solid gold" r="46"/>          <!-- relleno con degradado -->
  <ellipse class="spec" cx="-12" cy="-16" rx="22" ry="14"/>   <!-- brillo -->
  <circle class="st" r="46"/>                  <!-- borde de luz, opcional -->
</g>
```

- Clases de relleno: `solid` (neutro), `solid accent`, `solid gold`, `solid ok`.
- El brillo (`.spec`) va **siempre arriba a la izquierda**, en todos los objetos.
- Nada de perspectiva real: es volumen sugerido, no 3D de verdad.
- **Movimiento:** el brillo se mueve un poco menos que el objeto (parallax de 3–5px):
  eso es lo que lo hace parecer sólido. Entradas con `settle` y `scale` 0.9 → 1.
- **Coste alto:** cada objeto necesita forma + brillo + borde. Máximo 4 por escena.

---

## 7 · Flat humanista (`s-flat`) — **construcción distinta**

La familia "corporate memphis" adaptada a overlay: siluetas sólidas de color, sin
contorno oscuro, personas abstractas con proporciones exageradas y paleta cálida
(coral, azul, verde, mostaza).

```svg
<g class="o person">
  <circle class="solid" cx="0" cy="-42" r="20"/>          <!-- cabeza -->
  <path class="solid alt" d="M-30,40 V6 a30,30 0 0 1 60,0 V40 Z"/>  <!-- torso -->
</g>
```

- **Sin contorno oscuro.** El estilo original vive sobre fondo claro; encima de video,
  un contorno `#101418` desaparece en metraje oscuro. Aquí el color plano es el dibujo.
- Máximo 3 colores planos + blanco.
- **No lo uses si:** el tema es dinero, control o fallos. El estilo tiene un tono
  optimista que choca con el contenido.
- **Movimiento:** rebote moderado (`back.out(1.5)`), stagger amplio 0.1, formas que
  crecen desde su base (`transformOrigin: '50% 100%'`).

---

## Mezclar

No. Un estilo por video. Lo único que puede convivir con cualquiera es la tipografía
de interfaz (etiquetas cortas en mayúscula), que se mantiene igual en todos los packs
salvo en `s-tech` (mono) y `s-flat` (peso 700).

## Cambiar de estilo a mitad de proyecto

Los packs que **solo** cambian acabado (`s-tech`, `s-bold`, `s-hand`) se aplican a
escenas ya hechas cambiando la clase de `#stage`: la animación no se toca, y el grosor
tampoco hay que recalcularlo (los tres números del pack están en px de lienzo y el
runtime compensa la escala del módulo).
`s-neon`, `s-iso`, `s-soft3d` y `s-flat` obligan a redibujar los objetos, aunque el timeline y los
BEATS se conservan.
