---
name: video-cut
description: >-
  Plataforma de edición de vídeo completa y local, tipo CapCut. Fase 1 ordena
  varios vídeos, los transcribe, elimina silencios, detecta tomas repetidas y
  arma un timeline sin renderizar. Fase 2 añade subtítulos, textos, zooms,
  transiciones, música, overlays, velocidad y color, y renderiza a MP4. Úsala
  para recortar o limpiar grabaciones, elegir tomas, transcribir, editar el
  vídeo completo o exportar a DaVinci Resolve, Premiere o Final Cut.
---

# vcut — cortar sin render, y editar todo lo demás encima

Dos fases sobre el mismo proyecto:

1. **Cortes** (`project.json`): de grabaciones crudas —varias tomas, silencios,
   arranques fallidos— a un timeline limpio **sin tocar los archivos
   originales**. No se recodifica nada: el plan apunta a los archivos de cámara
   con puntos de entrada y salida, y se exporta a FCPXML/EDL.
2. **Studio** (`timeline.json`): encima de esos cortes, lo que no es un corte —
   subtítulos, textos, zooms con keyframes, transiciones, música, overlays,
   velocidad, color— y un render final a MP4.

Las dos capas viven en archivos separados a propósito: volver a analizar los
cortes no se lleva por delante el trabajo de post, porque los items del studio
se **anclan** a su clip en vez de a un tiempo absoluto.

Si el usuario va a terminar en DaVinci o Premiere, la fase 1 sola ya le sirve
(`export`). Si quiere el MP4 listo para subir, la fase 2 lo hace sin salir de
aquí.

## Script

```bash
VCUT="$HOME/.claude/skills/video-cut/scripts/vcut.py"   # Windows: C:/Users/<usuario>/.claude/...
```

Usar `python` (no `python3`: en esta máquina es un stub roto de Microsoft Store).
Todo comando imprime JSON en stdout y progreso en stderr.

## Flujo completo

```bash
# 1. Todo el pipeline automático (ordenar + transcribir + cortar + assets)
python $VCUT run "C:/ruta/a/los/videos" --project "C:/ruta/proyecto" --sort name

# 2. Contrastar el plan con el audio real (no con la transcripcion)
python $VCUT qa --project "C:/ruta/proyecto" --write

# 3. LEER el informe y decidir (este paso es tuyo, ver abajo)
#    -> C:/ruta/proyecto/review.md  +  C:/ruta/proyecto/qa.md

# 4. Aplicar tus decisiones
python $VCUT decide --project "C:/ruta/proyecto"

# 5. Abrir el editor de cortes para que el usuario ajuste a mano
python $VCUT edit --project "C:/ruta/proyecto"

# 6. Subtítulos desde la transcripción y plataforma completa
python $VCUT broll  --project "C:/ruta/proyecto" --dry-run   # planos de recurso
python $VCUT subs   --project "C:/ruta/proyecto"
python $VCUT studio --project "C:/ruta/proyecto"

# 7. MP4 final (o --draft para un borrador rápido a 720p)
python $VCUT render --project "C:/ruta/proyecto"
```

`run` es equivalente a `new` + `transcribe` + `analyze` + `media`.

**`media` no es opcional para el studio**: el preview compone cada fotograma en
un canvas, y hacerlo desde un original 4K va a tirones. Con proxies va fluido.
Para material vertical de móvil: `media --proxy-all --height 640`.

## Paso 2: qa — el titubeo no está en la transcripción

**Whisper borra los arranques en falso.** Está entrenado para escribir texto
legible, así que si el locutor dice *"es defin… es definir qué debes saber"*, en
el `.json` vas a leer `es definir que debes saber` — limpio, como si nunca
hubiera dudado. Buscar el titubeo en el texto no sirve: no está.

Lo que sí queda es la huella en los tiempos: whisper mete el tramo dudoso
**dentro de la palabra siguiente**. Caso real de `IMG_0423.MOV`:

```
texto:   "es definir que debes saber de tu negocio,"
palabras: es[0.63-1.15]  definir[2.03-4.73]  que[4.91-5.05]  debes[5.05-5.31]
                         ^^^^^^^^^^^^^^^^^^ 2.70 s para una palabra de 3 sílabas
```

Ahí adentro hay dos intentos abortados. El audio real:

```
0.83-1.32 + 1.54-1.82   "es saber que…"    <- intento 1
3.15-3.49               "es defin…"         <- intento 2
4.17-6.21 + 6.68-7.63   "es definir que debes saber…"   <- la buena
```

`vcut qa` mide eso con `silencedetect` y busca dos patrones:

- **Arranque en falso**: isla de voz corta (≤1 s) + pausa (≥0.28 s) al principio
  del corte. Propone entrar después de la pausa. Es el caso de arriba.
- **Aire muerto**: silencio pegado al inicio o al final del corte.
- **Habla huérfana**: voz del original que no cae dentro de ningún corte, ni
  siquiera de uno apagado. Es la señal de una **toma repetida que whisper
  borró**, y es el caso más dañino porque no genera grupo de tomas: nadie puede
  elegir la buena, y el plan termina pegando media toma con media otra.
- **Corte a media isla**: el corte entra o sale con la voz sonando, o sea que
  parte una palabra. Casi siempre es la otra cara de la habla huérfana: el corte
  agarró solo un pedazo de la toma buena. Te dice el `in`/`out` exacto que la
  deja entera.
- Además lista **palabras con duración imposible** (>0.85 s) y **colas
  sospechosas** al final. Esas dos solo se avisan, no se recortan solas: una
  frase corta después de respirar ("que debes responder,") es habla legítima.

Caso real de `IMG_0432.MOV`, dos tomas de la misma línea:

```
16.28-18.31   "y cómo integrarse al"                       <- toma 1, abandonada
21.11-24.23   "y cómo integrarse al proceso comercial…"    <- toma 2, la buena
```

Whisper transcribió el archivo entero y borró la repetición, así que el arranque
de la toma 2 (21.11-22.23) no llegó a ser ni un segmento apagado. El plan quedó
uniendo la **cabeza de la toma 1** con la **cola de la toma 2**: sonaba
*"integrarse al… al proceso comercial"*, con el "al" doblado y un salto de
entonación. `qa` lo detecta por partida doble y te deja el arreglo servido:

```
huerfanas:   IMG_0432.MOV 21.11-22.23 (1.12s) junto a u0017, u0018 -> 'y como integrarse.'
media isla:  u0018 entra en 22.23 pero la isla va de 21.11 a 24.23 -> sugerido in 20.99
```

La solución es siempre la misma: apagar el pedazo de la toma mala y abrir el
corte de la buena hasta los bordes de su isla. Eso no se aplica solo —agrega
palabras al montaje, así que la decisión es tuya—; el aire muerto y el arranque
en falso sí se escriben con `--write`.

`--write` fusiona los recortes sugeridos en `decisions.json` (no pisa lo tuyo).

Para confirmar un tramo dudoso con tus propios oídos, hay un truco: **pedile a
whisper solo ese fragmento**. Sin contexto alrededor no puede "arreglar" la
frase y escribe el titubeo tal cual:

```bash
ffmpeg -hide_banner -loglevel error -y -ss 3.0 -to 4.6 -i "IMG_0423.MOV" -vn -ac 1 -ar 16000 frag.wav
# whisper sobre frag.wav -> 'es defin... es defini...'   (sobre el archivo entero -> 'es definir')
```

Y para ver dónde está la voz de verdad, sin transcripción de por medio:

```bash
ffmpeg -hide_banner -nostats -ss 0 -to 9 -i "IMG_0423.MOV" -vn   -af "silencedetect=noise=-45dB:d=0.12" -f null -
```

Los bloques que salen ahí son la verdad; el texto de whisper, no.

## Paso 2.bis: la segunda pasada verbatim

`qa` detecta el titubeo midiendo el audio. Hay una segunda via, independiente,
que dice las **palabras exactas** que la pasada legible se comio: transcribir
otra vez cebando a whisper con un prompt lleno de titubeos.

```bash
python $VCUT transcribe --project "proj" --verbatim   # segunda pasada
python $VCUT disfluencias --project "proj"            # -> disfluencias.md
```

Por que funciona: whisper es seq2seq con modelo de lenguaje y repara lo que oye.
El prompt inicial condiciona lo que espera encontrar, asi que uno disfluente le
hace transcribir los titubeos. Medido sobre `IMG_0423.MOV`:

```
prompt de vocabulario -> "es definir que debe saber de tu negocio"
prompt disfluente     -> "Es saber que... es definir que debe saber..."
```

**No sustituye a la pasada normal.** El prompt disfluente no alucina titubeos
donde no los hay (comprobado en tomas limpias), pero SI desplaza el registro:
en una toma limpia paso "necesitas" a "necesita". Por eso la verbatim se guarda
aparte, en `<id>.verbatim.json`, y solo se usa para localizar. El texto que va a
los subtitulos sale siempre de la pasada con el prompt de vocabulario.

`disfluencias` compara las dos con difflib y lista las inserciones del lado
verbatim. Ejemplo real:

```
IMG_0432.MOV @ 20.61  4 palabras  "y como integrarse al"
IMG_0434.MOV @ 22.81  4 palabras  "practi... de una forma"
```

El primero es la toma abortada que `qa` tambien senala midiendo el audio: dos
metodos independientes en el mismo punto, correccion segura. El segundo trae una
palabra truncada, `practi...`, que la pasada legible borro entera.

`--minimo 2` por defecto: los tramos de una sola palabra son casi siempre el
desacuerdo de registro entre las dos pasadas (debe/debes), no titubeos. Medido
en un proyecto real, con `--minimo 1` salen 9 hallazgos de los que 7 son ruido;
con 2 salen los 2 reales.

Si hace falta mas precision de la que da esto, el siguiente paso es un modelo
**CTC** (wav2vec2 y familia): no llevan modelo de lenguaje, asi que transcriben
lo que suena, titubeos incluidos. Cuesta torch + transformers (~1.5 GB) y es
lento en CPU, asi que solo merece la pena si el prompt disfluente se queda corto.


## Paso 3: tu trabajo de juicio

Después de `run` y `qa`, **leé `<proyecto>/review.md` completo**. Ese archivo trae el
diálogo propuesto y los grupos de tomas repetidas. El pipeline aplica una regla
mecánica (se queda con la última toma de cada grupo); vos tenés que verificar
que el resultado **tenga sentido como discurso continuo**:

- ¿El diálogo se lee corrido, sin saltos ni ideas duplicadas?
- ¿Alguna "última toma" quedó incompleta o cortada, y encaja mejor la anterior?
- ¿Quedó encendida alguna frase que rompe la secuencia (comentario fuera de
  guion, "a ver, otra vez", una idea que se repite sin ser el mismo grupo)?
- ¿Se apagó algo que sí hacía falta para que se entienda?

Escribí `<proyecto>/decisions.json` con el veredicto y corré `decide`:

```json
{
  "groups":  { "g001": "u0007", "g004": "u0031" },
  "disable": ["u0018", "u0044"],
  "enable":  ["u0012"],
  "trim":    { "u0005": {"in": 12.40, "out": 15.90} },
  "order":   ["u0001", "u0003", "u0002"],
  "notes":   "g004: la última toma se corta en 'entonces'; uso la segunda."
}
```

Todos los campos son opcionales. `groups` elige la toma buena de cada grupo,
`disable`/`enable` fuerzan frases sueltas, `trim` ajusta tiempos en segundos del
**archivo original**, `order` reordena (sólo si hace falta cambiar el orden).

Después de `decide`, `review.md` se regenera: releelo para confirmar que el
diálogo quedó bien antes de pasarle el editor al usuario.

## Comandos

```bash
# NEW — descubre archivos y los ordena
python $VCUT new "C:/videos" --project "proj" --sort name|date|none [-r] [--filter "regex"] [--name "Mi proyecto"]

# TRANSCRIBE — faster-whisper con timestamps por palabra
python $VCUT transcribe --project "proj" [--model medium] [--lang es] [--device auto|cuda|cpu]
                                         [--prompt "vocabulario, nombres propios"] [--force]
                                         [--verbatim]   # 2a pasada, ver §2.bis

# DISFLUENCIAS — lo que la pasada legible se comio -> disfluencias.md
python $VCUT disfluencias --project "proj" [--minimo 2]

# ANALYZE — corta silencios y agrupa tomas repetidas -> review.md
python $VCUT analyze --project "proj" [--pause 0.55] [--sim-ratio 0.68] [...]

# QA — contrasta los cortes con el audio real -> qa.md
python $VCUT qa --project "proj" [--write] [--listen] [--noise -45]
                                 [--min-lead 0.4] [--min-tail 0.4] [--min-orphan 0.5]

# DECIDE — aplica decisions.json
python $VCUT decide --project "proj" [--file otro.json]

# REVIEW — regenera review.md
python $VCUT review --project "proj"

# MEDIA — proxies, ondas y miniaturas para el editor
python $VCUT media --project "proj" [--proxy-all] [--height 540] [--force] [--no-filmstrip]

# EDIT — levanta el editor de cortes en el navegador (127.0.0.1)
python $VCUT edit --project "proj" [--port 7788] [--no-open]

# SUBS — subtítulos apilados desde la transcripción -> timeline.json
python $VCUT subs --project "proj" [--style capcut] [--keywords "IA,ventas"]
                                   [--no-keywords] [--add]

# OVERLAYS — secuencias de PNG con alfa -> WebM, y los coloca donde toca
python $VCUT overlays --project "proj" [--place] [--fps 30] [--y 0.30]
                                       [--min-score 0.28] [--add] [--force]

# BROLL — planos de recurso de Pexels sobre lo que se está diciendo
python $VCUT broll --project "proj" --dry-run          # el plan, sin tocar la red
python $VCUT broll --project "proj" [--plan broll/plan.json] [--every 3]
                                    [--max 8] [--dur 2.6] [--kind video|photo]
                                    [--candidates 10] [--add]

# STICKERS — genera la librería (SVG editables -> PNG con alfa)
python $VCUT stickers [--force] [--scale 3]

# TEMPLATE — el mismo montaje en otro pack de vídeos
python $VCUT template list
python $VCUT template apply --project "proj" --name tiktok
python $VCUT template save  --project "proj" --name mi-estilo --label "Mi estilo"

# REPO — compartir el proyecto por git (init deja todo listo y lo sube)
python $VCUT repo init   --project "proj" --usuario TU-USUARIO-GITHUB
                         [--nombre mi-video] [--publico] [--sin-remoto]
python $VCUT repo estado --project "proj"

# MERGE — traer la edicion que hizo otra maquina (sin perder tus originales)
python $VCUT merge "revisado.vcutpack" --project "proj" [--no-cortes]

# PACK / UNPACK — pasarle el proyecto (o la herramienta) a otra persona
python $VCUT pack   --project "proj" [--media] [--out algo.vcutpack]
python $VCUT pack   --skill --out video-cut-studio.zip
python $VCUT unpack algo.vcutpack --project "proj-nuevo" --media "C:/ruta/videos"

# STUDIO — plataforma completa: texto, zooms, transiciones, audio, render
python $VCUT studio --project "proj" [--port 7788] [--no-open]

# RENDER — quema todo a un MP4
python $VCUT render --project "proj" [--draft] [--from 12 --to 30]
                                     [--out archivo.mp4] [--name base]

# EXPORT — a formatos de NLE
python $VCUT export --project "proj" --format fcpxml edl srt csv cutlist ffmpeg

# INFO — resumen
python $VCUT info --project "proj"
```

## Perillas de ajuste

Si el resultado no convence, no edites a mano: reanalizá con otros umbrales
(`analyze` es instantáneo, no re-transcribe).

| Síntoma | Ajuste |
|---|---|
| Corta demasiado, se come respiros naturales | `--pause 0.8 --pad-out 0.35` |
| Quedan silencios largos | `--pause 0.35` |
| Cortes "secos", sin aire | `--pad-in 0.2 --pad-out 0.35` |
| No detecta tomas repetidas obvias | `--sim-ratio 0.55 --lookahead 12` |
| Agrupa frases distintas como si fueran la misma toma | `--sim-ratio 0.8 --contain 0.9` |
| Las retomas están muy separadas en el tiempo | `--window 180` |
| Transcripción con errores (nombres, jerga) | `transcribe --model large-v3 --prompt "nombres, términos"` |
| Frases larguísimas sin cortar | `--max-utt 8` |
| Quedó un titubeo o silencio dentro de un corte | `qa --write` y `decide` |
| Un corte suena a dos tomas pegadas (palabra doblada, salto de tono) | `qa --listen`: buscá habla huérfana |

Modelos whisper: `tiny` `base` `small` `medium` `large-v3`. `medium` y `small`
ya están en caché en esta máquina; `large-v3` se descarga (~3 GB) la primera vez.

## Formatos de exportación

| Formato | Para qué |
|---|---|
| `fcpxml` | DaVinci Resolve, Final Cut, Premiere 2023+. **El principal.** Timeline completo con cortes, apuntando a los originales. |
| `edl` | CMX3600. Compatible con todo, pero sólo una pista y sin nombres largos. |
| `srt` | Subtítulos ya conformados a la línea de tiempo cortada. |
| `csv` / `cutlist` | Lista de cortes para revisar o procesar con otra herramienta. |
| `ffmpeg` | Script PowerShell de corte con `-c copy`. **No se ejecuta solo.** Cortes pegados al keyframe (±1 s), sirve de preview; el master exacto es el FCPXML. |

## El editor

`vcut edit` levanta un servidor Flask en `127.0.0.1` y abre el navegador.

- **Timeline**: arrastrar el borde de un clip recorta; arrastrar el cuerpo
  reordena; doble clic apaga/enciende; clic derecho abre el menú.
- **Transcripción**: clic en una palabra salta ahí; clic derecho ofrece
  "empezar / terminar / dividir" en esa palabra.
- **Tomas**: cada grupo con radio para elegir la toma y ▶ para escucharla sin
  tocar el timeline.
- **Atajos**: `Espacio` play · `←/→` un frame · `Shift+←/→` 1 s · `,`/`.` clip
  anterior/siguiente · `S` dividir · `D` apagar/encender · `[`/`]` entrada/salida
  en el cursor · `Ctrl+Z` deshacer · `Ctrl+S` guardar · `+`/`−` zoom ·
  `Ctrl+rueda` zoom sobre el cursor.

Guardar escribe `project.json` (con `.bak`). Exportar desde el editor deja el
archivo en `<proyecto>/exports/`.

## El studio

`vcut studio` levanta el mismo servidor en `/studio`. Es la plataforma completa:
edita los cortes **y** todo lo que va encima. El editor de cortes clásico sigue
en `/` (hay un enlace en la barra).

**Cuatro paneles**: librería (izquierda, arrastrable a la timeline), preview con
compositor en canvas, inspector contextual (derecha) y timeline multipista.

| Pista | Qué lleva |
|---|---|
| Títulos | textos sueltos, con animación de entrada y salida |
| Subtítulos | las tarjetas que genera `subs`, apiladas y ancladas a su clip |
| Overlays | PNG con alfa, WebM con alfa, motion graphics |
| Vídeo | los cortes, con miniaturas, onda y la curva de zoom dibujada encima |
| Música | con ducking automático bajo la voz |
| SFX | los golpes de las transiciones |

**Zooms** (lo que el inspector llama *Zoom y encuadre*): cada clip tiene su
curva de escala con keyframes. Clic en la curva pone un keyframe; se arrastran
los puntos, o se escriben los valores. Los 8 presets (empuje lento, punch in,
Ken Burns, latido, foco en la cara…) son un punto de partida, no una caja negra:
dejan keyframes normales que después se retocan. En modo **encuadre** (`Z`) se
arrastra directamente sobre el preview para mover el plano y la rueda acerca;
eso escribe en el keyframe más cercano, o crea uno.

Los tiempos de los keyframes son **segundos desde el inicio del clip**, así que
recortar el clip no descoloca el zoom. Escala 1 es el plano completo y 2 son
píxeles reales del original (el material se prepara a canvas×2 antes del
`zoompan`), así que en material 4K vertical el zoom no cuesta calidad.

**La curva entre dos keyframes se dibuja.** Al seleccionar un punto aparece
debajo del gráfico el tramo que llega hasta él, en el cuadrado unidad y con dos
manijas bezier, como el editor de curvas de CapCut: horizontal es el tiempo del
tramo y vertical cuánto valor lleva recorrido. Hay chips con las curvas de
siempre (*suave, frena, latigazo, rebote, anticipa, resorte*) y arrastrando una
manija fuera del cuadro el zoom se pasa de largo y vuelve. Se guarda como
`"ease": {"bezier":[x1,y1,x2,y2]}` en el keyframe; los nombres de toda la vida
(`inout`, `back`, `hold`…) siguen valiendo. El preview resuelve la curva exacta
y el render la hornea en tramos rectos, porque las expresiones de ffmpeg no
tienen bucles; se diferencian en menos de 0,002 de escala.

**Textos**: se arrastran sobre el preview. El reparto en líneas lo decide
siempre el servidor con las métricas reales del `.ttf`, no el navegador, para
que el preview y el render partan las líneas en el mismo sitio.

**Transiciones**: se sueltan sobre la pista de vídeo, cerca del corte. **No
consumen tiempo**: son un golpe centrado en el corte, no una mezcla de dos
clips. Por eso la secuencia mide exactamente la suma de los clips y nada de lo
que viene después se descoloca. Con "Sonido sugerido" el inspector busca el SFX
de la librería que le corresponde y lo pone en la pista SFX.

**Render**: *Borrador* saca 720p con proxies y sin normalizar (≈10× tiempo real
en esta máquina); *Renderizar* saca el MP4 final desde los originales con el
audio a −14 LUFS. Los dos van a `<proyecto>/exports/`.

**Atajos**: `Espacio` play · `←/→` un frame · `Shift+←/→` 1 s · `,`/`.` clip
anterior/siguiente · `V` mover · `Z` encuadre · `S` cortar en el cabezal ·
`D` apagar clip · `T` título nuevo · `Supr` borrar lo seleccionado ·
`Ctrl+Z` deshacer · `Ctrl+S` guardar · `Ctrl+R` render · `B` borrador ·
`+`/`−` zoom de timeline · `Ctrl+rueda` zoom sobre el cursor.

Guardar escribe `timeline.json` y, si se tocaron los cortes, también
`project.json`. Ver `references/studio-schema.md` para el formato y para las
decisiones de diseño que hay detrás.

## B-roll: que no sea un plano fijo de alguien hablando

`vcut broll` lee la transcripción, saca de cada tramo las palabras que lo
describen, busca un clip en **Pexels** y lo deja puesto encima de esa frase. El
resultado es un item normal de la pista de overlays: se mueve, se recorta y se
borra como cualquier otro.

**El paso obligatorio es mirar el plan antes de gastar peticiones.** La
heurística elige por rareza de la palabra, y en castellano se le cuela algún
verbo conjugado. Vos entendés la frase; ella no:

```bash
python $VCUT broll --project "proj" --dry-run     # escribe broll/plan.json
# corregí las consultas que no describan una imagen
python $VCUT broll --project "proj" --plan "proj/broll/plan.json"
```

Una consulta buena es un sustantivo concreto que se pueda fotografiar
(*"factura electrónica"*, *"reunión equipo"*). Una mala es un verbo o un
abstracto (*"definir debe"*, *"verdadero problema"*).

**Qué pasa con cada clip.** Se descarga a `cache/broll/`, se recorta al encuadre
del proyecto, se le quita el audio y se deja en `broll/` a la duración pedida.
Por eso entra en el render y en el preview sin ningún tratamiento especial: para
los dos es un overlay del tamaño exacto del lienzo. La voz sigue sonando debajo,
porque el clip de stock llega mudo.

**La clave** se busca en `PEXELS_API_KEY`, en `<proyecto>/credenciales.json` o en
`~/.vcut/credenciales.json`, por ese orden. Es gratis
(https://www.pexels.com/api/) y nunca se escribe en el proyecto. Sin clave, el
comando explica dónde ponerla y no hace nada más.

**Créditos.** Pexels no exige atribución pero la pide. Cada pasada deja
`broll/CREDITOS.md` con el autor y el enlace de cada clip.

## Editar entre dos máquinas, por git

Es el mismo reparto que con paquetes, pero sin mandarse archivos. `timeline.json`
es texto, así que cada push se lee como un diff de verdad: qué zoom cambió, qué
texto se movió.

```bash
# una vez, en la máquina que tiene el material
python $VCUT media --project "C:/proyecto" --proxy-all
python $VCUT repo init --project "C:/proyecto" --usuario TU-USUARIO

# el otro, cada vez que trabaja
git clone <url> mi-revision && python $VCUT studio --project mi-revision
git add -A && git commit -m "ajusté los zooms" && git push

# vos, cuando te llega el aviso
git -C "C:/proyecto" pull
python $VCUT render --project "C:/proyecto"
```

`repo init` hace cuatro cosas: mueve los proxies, las ondas y las miniaturas a
`preview/` (que es lo que se commitea); separa las rutas; escribe `.gitignore`,
`LEEME.md` y el workflow del aviso; y crea el repo **privado** en GitHub con
`gh` si está disponible.

**Las rutas son el problema real, y se resuelve con dos archivos.**
`project.json` se commitea con rutas **relativas** al proyecto, así que el mismo
archivo abre bien en las dos máquinas. Dónde tiene cada una sus originales vive
en **`local.json`**, que está en el `.gitignore`: nunca viaja y nunca choca.
Quien clona sin `local.json` abre igual, reproduciendo los proxies.

**El render final está protegido.** Si a esta máquina le falta el material
original, `render` se niega y lo dice; `--draft` sigue funcionando. Sin esa
guarda, quien solo revisa sacaría un MP4 de 540p estirado y solo se notaría al
abrirlo.

**El aviso.** GitHub no notifica los push a secas, así que
`.github/workflows/aviso.yml` abre un issue mencionando a `--usuario` cuando
empuja alguien que no sea él. Llega por correo y al móvil.

**Una regla de convivencia**: uno a la vez. `git` no sabe fusionar dos
`timeline.json` y no lo intenta. `pull` antes de empezar, `push` al terminar.

## Editar entre dos máquinas, con paquetes

Lo caro de este flujo es transcribir (minutos de CPU), generar los proxies y
renderizar. Ajustar cortes, zooms y textos no cuesta nada: es un navegador
reproduciendo vídeo de 540p. Así que se pueden repartir.

```bash
# 1. la máquina fuerte hace lo caro
python $VCUT run   "C:/videos" --project "C:/proyecto"
python $VCUT media --project "C:/proyecto" --proxy-all      # proxy para todos

# 2. y arma el paquete de revisión: proxies, sin material original
python $VCUT pack  --project "C:/proyecto" --preview --out "revisar.vcutpack"

# 3. la otra máquina abre, ajusta y devuelve
python $VCUT unpack "revisar.vcutpack" --project "C:/mi-revision"
python $VCUT studio --project "C:/mi-revision"
python $VCUT pack   --project "C:/mi-revision" --out "revisado.vcutpack"

# 4. la primera máquina trae los cambios y renderiza en calidad real
python $VCUT merge  "revisado.vcutpack" --project "C:/proyecto"
python $VCUT render --project "C:/proyecto"
```

Medido en un proyecto de 2:43 con 14 tomas: **743 MB de originales → 23 MB de
paquete**, y de vuelta 15 MB.

**Por qué `merge` y no reemplazar el proyecto.** El que vuelve apunta a los
proxies. Copiarlo entero encima dejaría el render final saliendo de vídeo de
540p sin que nadie lo notara hasta ver el MP4. Así que del paquete solo entran
las decisiones —los `segments` y el `timeline.json` completo—; las `sources`
son siempre las de esta máquina. Con `--no-cortes` vuelve solo la capa
creativa y tus cortes se quedan como estaban.

Los archivos que la otra persona haya sumado (un sonido, un b-roll) se copian a
`assets/recibidos/`, y los que ya tenías se reconocen por nombre y no se
duplican. Antes de escribir nada, `project.json` y `timeline.json` quedan con
su `.bak`.

**Lo que la otra máquina no puede hacer**: el render final en calidad real, ni
`broll` sin su propia clave de Pexels. El botón *Renderizar* del studio le
sacaría el MP4 desde los proxies — sirve para mirarlo, no para publicar.

## Recursos gráficos y stickers

**Motion graphics.** La skill `motion-overlays` deja sus escenas como
`frames/<nombre>/0000.png`. `vcut overlays` las empaqueta y las coloca:

```bash
python $VCUT overlays --project "proj" --place
```

Cada overlay se coloca **sobre el clip del que habla**: se compara el `<title>`
del HTML *más el texto que la escena muestra en pantalla* contra el texto de los
segmentos. Con el título solo no basta — uno que se llamaba "lo que hay que
definir antes de conectar una IA" y enseñaba SABER / RESPONDER / HABLAR se iba a
la frase que decía "conectar una IA" en vez de a la que enumera las tres cosas.
Los que no encuentran sitio salen en `sin_sitio` con su puntaje, para colocarlos
a mano; colocar a ciegas sería peor.

**Un overlay guarda dos rutas y hay que saber por qué**: `src` es un WebM/VP9 con
alfa, y `seq` es la secuencia de PNG. El preview usa el WebM porque Chrome lo
reproduce con transparencia; el render usa la secuencia porque **ffmpeg escribe
WebM con alfa pero no lo lee** — medido en este equipo: al superponer el WebM, el
overlay sale sobre un rectángulo negro. Si la carpeta de frames desaparece, el
render avisa y usa el WebM perdiendo la transparencia. El inspector lo dice en el
panel del overlay.

La escala inicial se calcula sobre el **contenido**, no sobre el archivo: las
escenas son 1920×1080 con el módulo centrado y mucho aire, así que escalar por el
ancho del archivo las dejaba diminutas. Se mide la caja de lo opaco en varios
fotogramas.

**Stickers.** 41 piezas en el lenguaje visual de motion-overlays (flechas,
resaltes, números, etiquetas, check/cruz, foco, rayo, moneda…), a 1080 px de lado
con alfa y sombra oscura para que se lean también sobre una pared blanca a
mediodía. Viven en la skill, no en el proyecto: sirven para todos.

```bash
python $VCUT stickers            # los que falten
python $VCUT stickers --force    # rehacer todo tras editar un SVG
```

Los fuentes son SVG en `stickers/*.svg` y se rasterizan con Chrome (ni ffmpeg ni
PIL leen SVG en este equipo). Para añadir uno propio: poné el `.svg` en esa
carpeta y corré el comando; aparece en la pestaña ★ del studio.

## Plantillas: el mismo montaje en otro pack de vídeos

Una plantilla guarda **el look y la receta**, no el contenido: lienzo, ajustes de
render, estilos de texto, y con qué patrón repartir subtítulos, zooms y
transiciones.

```bash
python $VCUT run "C:/ruta/videos-nuevos" --project "C:/ruta/proyecto2"
python $VCUT template apply --project "C:/ruta/proyecto2" --name tiktok
python $VCUT studio --project "C:/ruta/proyecto2"
```

Eso deja el montaje hecho —subtítulos puestos, un zoom en cada clip, una
transición con su golpe cada tres cortes, overlays colocados— para empezar a
editar en vez de empezar de cero.

| plantilla | qué hace |
|---|---|
| `tiktok` | 9:16, subtítulos apilados con palabra resaltada, zoom rotando 6 presets, golpe cada 3 cortes con SFX. |
| `limpio` | Sólo subtítulos y un empuje lento. Sin transiciones ni golpes. |

`template save` saca una plantilla del proyecto abierto: lee el orden real en que
aparecen los presets de zoom y cada cuántos cortes hay transición. Los zooms se
reparten **rotando el patrón**, no al azar: al azar, dos clips seguidos salen con
el mismo movimiento y se nota como un error.

Con `--no-subs`, `--no-zooms`, `--no-transitions` o `--no-overlays` se aplica sólo
una parte.

## Pasarle el proyecto a alguien

```bash
# el proyecto (edición + assets, sin los vídeos): ~15 MB
python $VCUT pack --project "proj"

# con los vídeos dentro: pesa lo que pese el material
python $VCUT pack --project "proj" --media

# la herramienta entera, para quien no la tiene: ~3,5 MB
python $VCUT pack --skill --out video-cut-studio.zip
```

El paquete lleva los cortes, el timeline, las transcripciones (no hay que
re-transcribir), y **todos los assets que la edición usa** —SFX, música,
secuencias de overlay, tipografías— con las rutas reescritas a rutas relativas
dentro del zip. Los vídeos de cámara quedan fuera salvo `--media`, porque son el
99% del peso.

Al abrirlo, los vídeos se **vuelven a enlazar buscándolos por nombre**:

```bash
python $VCUT unpack algo.vcutpack --project "proj-nuevo" --media "C:/ruta/videos"
python $VCUT media  --project "proj-nuevo" --proxy-all --height 640
python $VCUT studio --project "proj-nuevo"
```

Lo que no encuentra se lista en `sin_enlazar`; el proyecto abre igual y esos
clips se ven en negro hasta que aparezcan los archivos. Los proxies del emisor no
viajan: son de su máquina y se regeneran con `media`.

El zip de la herramienta trae un `INSTALAR.md` con las dependencias y un primer
comando que probar.

## Estructura del proyecto

```
<proyecto>/
  project.json          <- el plan de cortes (la fuente de verdad)
  project.json.bak      <- copia previa automática
  review.md             <- informe para decidir
  qa.md                 <- lo que dice el audio (silencedetect)
  decisions.json        <- tu veredicto
  timeline.json         <- capa creativa del studio (texto, zoom, transiciones)
  audio/                <- wav temporales de la transcripcion
  transcripts/s001.json <- transcripción por archivo (cacheada)
  fonts/                <- opcional: tipografías propias del proyecto
  assets/               <- opcional: SFX, música y overlays del proyecto
  assets/overlays/*.webm       <- motion graphics para el preview
  assets/overlays/index.json   <- qué WebM tiene secuencia de PNG detrás
  assets/seq/<nombre>/         <- secuencias de PNG (si vino en un paquete)
  cache/proxy|waveform|filmstrip/   <- assets de preview, borrables
  cache/fonts/          <- las fuentes que necesita el render (fontsdir)
  cache/burn.ass        <- el texto del último render
  cache/last_render_cmd.txt|last_render.log  <- para depurar un render
  exports/              <- FCPXML, EDL, SRT, y los MP4 del render
```

`cache/` es descartable: se regenera con `vcut media` y con el siguiente render.
Los archivos originales nunca se modifican ni se copian.

La librería del studio también busca SFX, música y overlays en las **dos
carpetas padre** del proyecto, con los nombres habituales (`transiciones/`,
`musica/`, `recursos graficos/`), y los stickers en la propia skill.
`/api/asset` sólo sirve archivos dentro de esas raíces.

`vcut overlays` en cambio busca **primero dentro del proyecto** y sólo mira las
carpetas padre si el proyecto no trae ninguna secuencia. Sin esa regla, dos
proyectos hermanos se roban los overlays el uno al otro.

Y en la skill:

```
~/.claude/skills/video-cut/
  stickers/*.svg          <- fuentes de los stickers, editables
  assets/stickers/*.png   <- rasterizados, es lo que ve la librería
  templates/*.json        <- plantillas de montaje
```

## Detalles de esta máquina

- **GPU**: la RTX 4060 está, pero faltan las DLL de CUDA para ctranslate2, así
  que whisper corre en CPU. Para habilitar GPU (~10x más rápido):
  `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`. El script detecta la falta
  y cae a CPU solo.
- **NVENC**: el driver es más viejo que el que pide este build de ffmpeg, así que
  los proxies y los renders se codifican con libx264. Es automático (`encoder:
  auto` prueba un encode real antes de decidir, no se fía de `-encoders`).
- **Render medido**: 84 s de secuencia con 25 clips, 6 zooms, 8 transiciones,
  37 textos y música con ducking → 8 s en borrador 720p, ~2 min en final 1080p
  desde originales 4K.
- **Tipografías**: las tres de los estilos por defecto (Inter Black, Anton,
  Bebas Neue) viajan en `assets/fonts/`. Se buscan antes en `<proyecto>/fonts/`,
  en `VCUT_FONTS` y en las del sistema, así que para usar otra basta con
  dejarla ahí.
- **Atajo**: `videria2.0/nuevo-video.ps1 "C:/ruta/videos"` corre la cadena
  entera (run → qa → decide → plantilla → studio). Acepta `-Plantilla limpio`,
  `-Modelo small`, `-SoloCortes` y `-NoAbrir`. Medido: 3 clips y 20 s de
  material con `small`, 25 s de punta a punta.

Ver `references/troubleshooting.md` para errores concretos,
`references/project-schema.md` para el formato de `project.json` y
`references/studio-schema.md` para `timeline.json`, el render y las transiciones.
