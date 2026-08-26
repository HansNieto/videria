# Skill · motion-overlays

**v1.2.1** · Convierte un guion hablado en un set de **overlays HTML animados con GSAP**,
con fondo transparente, listos para renderizar con canal alfa y montar encima del video.

Pensada para funcionar con un agente (Claude Code, Cursor o cualquiera que soporte el
formato Agent Skills) y para que sus salidas puedan consumirse **también por otra
herramienta**: el sistema visual, el catálogo de estilos y el contrato de entrega están
en JSON, no solo en prosa.

---

## Qué hace

1. **Pregunta el estilo visual** antes de dibujar nada — 7 packs, de línea mínima a 3D suave.
2. **Analiza el guion** y elige solo los momentos donde un motion graphic aporta
   (≈ 1 cada 12–20 s) en vez de animar cada frase.
3. **Escribe un HTML independiente por escena**, sincronizado palabra a palabra con la
   locución (2.6 palabras/segundo) y respetando las pausas semánticas.
4. **Verifica cada overlay**: transparencia real, entrada y salida limpias, duración 2–6 s.
5. **Entrega** galería de revisión, README, hoja de contactos y `overlays.json` —el
   manifiesto de montaje— más el script de captura a video.

## Estructura

```
motion-overlays/
├── SKILL.md                    instrucciones principales (lo que el agente lee siempre)
├── README.md                   este archivo
├── CHANGELOG.md                qué cambió en cada versión y por qué
├── sync.sh                     instala esta carpeta como skill activa
├── spec/                       ← especificaciones legibles por máquina
│   ├── design-tokens.json          color, tipografía, tiempos, densidad, lienzo
│   ├── styles.json                 los 7 estilos, cuándo usarlos, cómo se construyen
│   └── overlay-manifest.schema.json  contrato del overlays.json de cada proyecto
├── references/
│   ├── pitfalls.md             8 fallos silenciosos y su arreglo — leer antes de depurar
│   ├── visual-styles.md        estilos de trazo vs. de masa
│   ├── design-system.md        paleta, trazo, tipografía, layout y densidad
│   ├── motion-language.md      eases, tiempos, coreografía, recetas por tipo de escena
│   ├── svg-assets.md           biblioteca vectorial (versión de trazo y versión de masa)
│   ├── script-to-beats.md      guion → beats → tabla de entrega
│   └── render-capcut.md        render con alfa y montaje en CapCut
├── assets/
│   ├── vendor/                 GSAP 3.15 completo, local (sin CDN)
│   ├── overlay.css             tokens, fondo transparente, 7 packs de estilo
│   ├── overlay.js              runtime: escalado, loop, captura, defs, Overlay.audit()
│   ├── overlay-template.html   plantilla de escena
│   ├── preview-template.html   galería 00-preview.html
│   ├── estilos.html            muestrario 00-estilos.html
│   └── capture.mjs             captura frame a frame con alfa
└── spec/                       esquema del manifiesto y tokens del sistema
```

## Instalar

```bash
bash sync.sh          # copia esta carpeta a ~/.claude/skills/motion-overlays/
bash sync.sh --pull   # trae los cambios hechos en la instalada
```

Para otro equipo o agente, copia la carpeta dentro de su directorio de skills
(`~/.claude/skills/`, `~/.cursor/skills/`, `~/.codex/skills/`…).

> **Edita siempre en la copia que uses como fuente** y sincroniza en una sola dirección:
> `sync.sh` sobrescribe la instalada con esta carpeta.

## Contrato en tiempo de ejecución

Cada HTML generado expone:

```js
Overlay.duration     // duración exacta en segundos
Overlay.seek(t)      // salto determinista a un frame (para capturar)
Overlay.audit()      // { start: [], end: [], ok: true }
```

y acepta `?paused=1&t=<s>` (captura), `?bg=dark|light|photo|checker|green|magenta`
(revisión o croma) y `?loop=0`. Con eso se renderiza una secuencia PNG con alfa
reproducible sin depender de la reproducción en tiempo real.

## Salida para editores y agentes

Cada proyecto entrega un `overlays.json` conforme a
`spec/overlay-manifest.schema.json`: por clip, duración exacta, **palabra de entrada y de
salida**, beats anclados a palabras, encuadre sugerido y auditoría; y a nivel de proyecto,
el estilo, el ritmo de narración y las frases descartadas **con su motivo**.

Como los beats están anclados a palabras y no a segundos absolutos, si cambia la locución
no hay que rediseñar: se recalculan con `palabras / 2.6`.

## Dependencias

Ninguna en tiempo de ejecución: GSAP va vendorizado y el SVG es inline. Para renderizar a
video hacen falta **ffmpeg** y, opcionalmente, **puppeteer** (la ruta con Chrome headless
no necesita npm).

## Reglas que no se negocian

- Fondo transparente; nada opaco que tape el video.
- No se escriben las frases del guion (el video ya lleva subtítulos): solo etiquetas de
  interfaz muy cortas.
- En `t=0` y en `t=fin` no hay nada visible.
- Duración 2–6 s con entrada, desarrollo y salida.
- Colocación fuera (`.at`), animación dentro (`.o`).
- El color y el grosor van por clase, nunca por atributo `stroke=`/`fill=`.
- El hueco entre objetos relacionados no pasa de 0.6× su tamaño.

## Origen

Construida sobre las skills oficiales de GSAP
([`greensock/gsap-skills`](https://github.com/greensock/gsap-skills)), instaladas junto a
esta como `gsap-core`, `gsap-timeline`, `gsap-plugins`, `gsap-utils`, `gsap-performance`,
`gsap-scrolltrigger`, `gsap-react` y `gsap-frameworks`. GSAP y todos sus plugins son
gratuitos, incluido uso comercial.

Licencia MIT.
