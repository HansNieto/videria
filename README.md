# videria

Edición de vídeo local, sin nube y sin suscripciones. Le das una carpeta con
grabaciones crudas y sale un MP4 vertical listo para subir: ordenado,
transcrito, sin silencios, sin tomas repetidas, con subtítulos estilo CapCut,
zooms con keyframes, transiciones con sonido y música con ducking.

No es una app que se instala. Son **skills para [Claude Code](https://claude.com/claude-code)**
más una herramienta de línea de comandos en Python (`vcut`) y un editor que se
abre en el navegador. Podés usarlo de dos maneras:

- **Hablándole a Claude Code** — «limpiá estas grabaciones y armá un TikTok».
  Él lee las skills y sabe qué comandos correr y en qué orden.
- **A mano**, con los comandos de `vcut` que están más abajo. No hace falta
  Claude Code para esto: es Python y ffmpeg.

Todo el procesamiento ocurre en tu máquina y tus vídeos no salen a ningún lado.
La única función que usa internet es el b-roll automático, que **descarga**
clips de stock de Pexels; es opcional y no sube nada tuyo.

---

## Qué hace, en concreto

**Fase 1 — cortar sin renderizar.** Ordena los archivos, los transcribe con
timestamps por palabra (faster-whisper), detecta silencios y tomas repetidas —
cuando repetiste una frase tres veces, se queda con la buena— y arma un timeline
que **apunta** a tus archivos originales con puntos de entrada y salida. No se
recodifica nada, así que no se pierde calidad y es casi instantáneo. Si vas a
terminar en DaVinci o Premiere, exportás a FCPXML/EDL y listo.

**Fase 2 — el studio.** Encima de esos cortes va todo lo demás, en un editor que
se abre en el navegador:

- **Subtítulos** apilados con la palabra resaltada, generados desde la
  transcripción. Las líneas las parte el servidor con las métricas reales de la
  fuente, así que el preview y el render cortan igual.
- **Zooms con keyframes** y editor de curvas bezier como el de CapCut: fijás
  puntos sobre la línea de tiempo del clip y dibujás la curva entre dos puntos
  arrastrando las manijas. Hay curvas listas (suave, frena, latigazo, rebote,
  anticipa, resorte) y sacando una manija fuera del cuadro el zoom se pasa de
  largo y vuelve.
- **B-roll automático**: lee la transcripción, busca en Pexels un clip que
  ilustre lo que se está diciendo y lo coloca sobre esa frase. Así el vídeo no
  es un plano fijo de alguien hablando. Es lo único que sale a internet, es
  opcional, y la clave de Pexels es gratis.
- **Textos** que se mueven arrastrando sobre el preview.
- **Transiciones** con golpe de sonido, que no consumen tiempo: son un acento
  centrado en el corte, no una mezcla de dos clips.
- **Música con ducking** — la música baja sola cuando hablás.
- **Overlays** animados, stickers, velocidad por clip y corrección de color.
- **Render final** a MP4 con ffmpeg, con NVENC si tu GPU lo permite.

Las dos fases viven en archivos separados a propósito: volver a analizar los
cortes no se lleva por delante el trabajo de post.

---

## Qué hace falta

| Qué | Para qué | Cómo |
|---|---|---|
| **Python 3.10+** | todo | [python.org](https://www.python.org/downloads/) |
| **ffmpeg y ffprobe** en el PATH | cortar, render, proxies | `winget install Gyan.FFmpeg` · `brew install ffmpeg` |
| **flask, numpy, pillow** | editor, ondas, medir texto | `pip install flask numpy pillow` |
| **faster-whisper** | transcribir | `pip install faster-whisper` |
| Chrome o Edge | rasterizar los stickers | ya lo tenés |
| Clave de Pexels | **solo** para el b-roll automático | gratis en [pexels.com/api](https://www.pexels.com/api/) |
| Claude Code | opcional, para manejarlo hablando | [claude.com/claude-code](https://claude.com/claude-code) |

Todo junto:

```bash
pip install flask numpy pillow faster-whisper
```

**GPU (opcional).** La transcripción usa CPU si faltan las DLL de CUDA — contá
más o menos un minuto por minuto de material. Para acelerarla unas 10×:

```bash
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

El render usa NVENC si el driver lo permite y si no cae a libx264. Las dos cosas
se detectan probando; no hay nada que configurar.

---

## Instalar

Clonás y corrés el instalador, que copia las tres skills a `~/.claude/skills/`.
Si ya tenés una skill con ese nombre, la guarda con un sufijo de fecha antes de
pisarla.

```powershell
git clone https://github.com/HansNieto/videria.git
cd videria
.\instalar.ps1
```

En macOS o Linux:

```bash
git clone https://github.com/HansNieto/videria.git
cd videria
bash instalar.sh
```

Si preferís hacerlo a mano, es copiar las carpetas de `skills/` a
`~/.claude/skills/` (en Windows, `C:\Users\<vos>\.claude\skills\`).

---

## Un vídeo de principio a fin

### El camino corto (Windows)

Un solo comando: ordena, transcribe, corta, aplica la plantilla y abre el
editor.

```powershell
.\nuevo-video.ps1 "C:\ruta\a\los\videos"
.\nuevo-video.ps1 "C:\ruta\a\los\videos" -Nombre tiktok-3 -Plantilla limpio
```

Opciones: `-Plantilla tiktok|limpio` · `-Modelo tiny|base|small|medium|large-v3`
· `-Orden name|date` · `-SoloCortes` · `-NoAbrir`.

El paso lento es la transcripción. Con `medium` en CPU, andá por un café.

### El camino largo, paso a paso

```bash
VCUT="$HOME/.claude/skills/video-cut/scripts/vcut.py"   # Windows: C:/Users/<vos>/.claude/...

# 1. Ordenar + transcribir + cortar + generar proxies y miniaturas
python $VCUT run "C:/ruta/videos" --project "C:/ruta/proyecto" --sort name

# 2. Contrastar el plan con el audio real (no con la transcripción)
python $VCUT qa --project "C:/ruta/proyecto" --write

# 3. Leer el informe y decidir qué toma se queda  ->  proyecto/review.md y qa.md
# 4. Aplicar esas decisiones
python $VCUT decide --project "C:/ruta/proyecto"

# 5. Subtítulos desde la transcripción
python $VCUT subs --project "C:/ruta/proyecto"

# 5.bis. Planos de recurso (opcional, pide clave de Pexels).
#        Primero el plan, se revisa, y después se descarga.
python $VCUT broll --project "C:/ruta/proyecto" --dry-run
python $VCUT broll --project "C:/ruta/proyecto" --plan "C:/ruta/proyecto/broll/plan.json"

# 6. Una plantilla de montaje (subtítulos + zooms + transiciones de una)
python $VCUT template apply --project "C:/ruta/proyecto" --name tiktok

# 7. Abrir el studio en el navegador y ajustar a mano
python $VCUT studio --project "C:/ruta/proyecto"

# 8. El MP4 final (--draft para un borrador rápido a 720p)
python $VCUT render --project "C:/ruta/proyecto"
```

Para llevárselo a otro editor en vez de renderizar acá:

```bash
python $VCUT export --project "C:/ruta/proyecto" --format fcpxml   # o edl
```

Cada comando imprime JSON por stdout y el progreso por stderr.

---

## Atajos del studio

`Espacio` reproducir · `←/→` un frame · `Shift+←/→` un segundo · `,`/`.` clip
anterior y siguiente · `V` mover · `Z` encuadrar (arrastrás sobre el preview para
mover el plano y la rueda acerca) · `S` cortar en el cabezal · `D` apagar clip ·
`T` título nuevo · `Supr` borrar lo seleccionado · `Ctrl+Z` deshacer · `Ctrl+S`
guardar · `B` borrador · `Ctrl+R` render · `+`/`−` zoom de timeline ·
`Ctrl+rueda` zoom sobre el cursor.

---

## Qué hay en este repo

```
skills/
├── video-cut/          la plataforma: vcut.py, el studio, plantillas
│   └── assets/         los 8 sonidos de las transiciones, las tipografías
│                       de los subtítulos y los stickers ya rasterizados
└── motion-overlays/    overlays animados en HTML+SVG+GSAP, fondo transparente,
                        pensados para superponer sobre el vídeo
nuevo-video.ps1         el atajo de un comando (Windows)
instalar.ps1 / .sh      copian las skills a ~/.claude/skills
```

La documentación de verdad está adentro de cada skill:

- `skills/video-cut/SKILL.md` — el manual completo, comando por comando.
- `skills/video-cut/references/project-schema.md` — la capa de cortes.
- `skills/video-cut/references/studio-schema.md` — la capa creativa: zooms,
  keyframes, curvas, transiciones, textos.
- `skills/video-cut/references/troubleshooting.md` — cuando algo falla.
- `skills/video-cut/assets/fonts/LICENCIAS.md` — las tres tipografías que trae y
  cómo cambiarlas.
- `skills/video-cut/assets/sfx/generar-sfx.py` — cómo están hechos los sonidos,
  por si querés otros.

---

## Editar entre dos máquinas

Lo caro es transcribir, generar los proxies y renderizar. Ajustar cortes, zooms
y textos es un navegador reproduciendo vídeo de 540p: eso corre en cualquier
portátil. Si uno de los dos tiene la máquina buena, el reparto sale solo.

```bash
# en la máquina fuerte
python $VCUT run   "C:/videos"    --project "C:/proyecto"
python $VCUT media --project "C:/proyecto" --proxy-all
python $VCUT pack  --project "C:/proyecto" --preview --out revisar.vcutpack

# en la otra: abre, ajusta todo, y devuelve
python $VCUT unpack revisar.vcutpack --project "C:/mi-revision"
python $VCUT studio --project "C:/mi-revision"
python $VCUT pack   --project "C:/mi-revision" --out revisado.vcutpack

# de vuelta en la fuerte: trae los cambios y renderiza en calidad real
python $VCUT merge  revisado.vcutpack --project "C:/proyecto"
python $VCUT render --project "C:/proyecto"
```

En un proyecto de 2:43 con 14 tomas eso son **743 MB de material contra 23 MB
de paquete**. `merge` trae solo las decisiones —los cortes y la capa creativa—,
nunca las rutas: tus originales siguen siendo los originales, y el render final
no sale de los proxies por accidente.

## Compartir un proyecto entero

```bash
python $VCUT pack --project "C:/ruta/proyecto" --out proyecto.vcutpack
python $VCUT unpack proyecto.vcutpack --project "C:/nuevo/proyecto" --media "C:/donde/estan/los/videos"
```

Sin `--preview`, el paquete lleva el timeline, la transcripción, las fuentes y
los overlays, pero no los vídeos: al abrirlo se vuelven a enlazar buscándolos
por nombre en la carpeta que le indiques. Lo que no encuentra lo reporta; no se
lo inventa.
