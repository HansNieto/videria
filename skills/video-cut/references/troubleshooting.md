# Problemas concretos

## Transcripción

**`Library cublas64_12.dll is not found or cannot be loaded`**
Faltan las DLL de CUDA que necesita ctranslate2. El script lo detecta y cae a CPU
solo, así que no bloquea nada — sólo va más lento. Para habilitar la GPU:

```bash
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

No confundir con torch: faster-whisper no usa torch para inferir, usa
ctranslate2. Que `torch.cuda.is_available()` diga `False` es irrelevante acá.

**Se cuelga cargando el modelo en CUDA**
Si CUDA falla, reintentar con otro `compute_type` **no** falla rápido: se queda
colgado cargando kernels. Por eso hay un solo intento por dispositivo. Si querés
forzar: `--device cpu`.

**Transcribe mal nombres propios o jerga**
`--prompt "Brajan, UTEC, ctranslate2, FCPXML"` sesga el vocabulario. Si sigue
mal, `--model large-v3` (se descarga ~3 GB la primera vez).

**Detecta el idioma equivocado**
`--lang es`. El idioma del primer archivo se fija para todos los demás, así que
un archivo corto que arranque con ruido no arrastra al resto.

**Volver a transcribir**
La transcripción se cachea por huella (ruta + tamaño + mtime). Si editaste el
archivo original, se re-transcribe solo. Para forzar: `--force`.

## Cortes

**Se come el final de las frases**
`--pad-out 0.35`. Whisper suele cerrar el timestamp de la última palabra un poco
antes de que termine el sonido.

**Deja silencios largos entre frases**
`--pause 0.35`. Ojo: por debajo de ~0.25 empieza a cortar dentro de frases.

**No detecta tomas que obviamente son la misma**
Primero mirá `review.md`: si la transcripción de las dos tomas difiere mucho, el
problema es de transcripción, no de detección — subí el modelo. Si el texto es
parecido, bajá `--sim-ratio 0.55` y subí `--lookahead 12`.

**Agrupa como misma toma frases que son distintas**
Pasa con frases cortas y comunes ("y bueno", "entonces"). `--sim-ratio 0.8
--contain 0.9`. También podés apagar la agrupación de arranques fallidos con
`--prefix 1.0`.

**Las retomas están separadas por mucho material**
`--window 180` (son segundos de *habla*, no de grabación: los silencios no
cuentan).

**Volver a cortar sin volver a transcribir**
`analyze` es instantáneo y reconstruye todo desde `transcripts/`. Correrlo
descarta los ajustes manuales hechos en el editor — guardá una copia de
`project.json` si te importan.

## Editor

**El video no se reproduce / pantalla negra**
El navegador no puede con ese codec (HEVC, ProRes, 10 bits). Generá proxies:

```bash
python $VCUT media --project "proj" --proxy-all
```

Los proxies son sólo para previsualizar: el export sigue apuntando a los
originales. `--height 360` si el scrub va lento.

**Los saltos entre clips se notan**
Es esperable: la previsualización salta entre archivos con `<video>`, no hay
motor de composición. En el NLE queda sin saltos. Con proxies (GOP de 1 s) los
saltos se acortan bastante.

**El timeline va lento con material largo**
Bajá el zoom, y generá proxies. Sólo se dibujan los clips visibles, pero cada uno
redibuja onda y miniaturas al cambiar de escala.

**El puerto está ocupado**
`--port 7799`.

**Perdí cambios**
Cada guardado deja `project.json.bak` con la versión anterior. El editor
autoguarda cada 90 s si hay cambios pendientes, y avisa al cerrar la pestaña.

## Studio

**El preview va a tirones o el vídeo sale negro**
El compositor dibuja cada fotograma en un canvas, y desde un original 4K eso no
da. `vcut media --proxy-all --height 1080` y va fluido. Si el clip sigue negro,
el navegador no puede con ese codec: el badge de arriba a la izquierda dice de
qué archivo se trata.

**El texto del render no se ve como en el preview**
El reparto en líneas lo decide el servidor con las métricas del `.ttf`, así que
sólo se desvía si cambió el estilo y no se volvió a partir: "Re-partir líneas"
en el inspector, o `POST /api/relayout`. Si además la fuente sale distinta,
mirá `info.ass.fonts` del render: ahí está el nombre exacto que usó libass.

**Los subtítulos desaparecieron de un clip**
Están anclados a su segmento. Si el clip se apagó, su texto se esconde con él
(no se borró: vuelve al encenderlo). Si el segmento se borró de verdad, el item
queda huérfano y lo limpia "Limpiar huérfanos".

**Regenerar subtítulos me borró ediciones**
Sólo borra las tarjetas con `auto: true`. En cuanto editás una pasa a `false` y
sobrevive. Si perdiste algo, `timeline.json.bak` es el guardado anterior.

**El render sale negro**
Cortar el grafo por etapas y sacar un fotograma de cada una; el comando completo
está en `cache/last_render_cmd.txt`. Mapear una etapa intermedia obliga a
truncar el grafo, porque ffmpeg exige que toda salida etiquetada se consuma. El
caso conocido: el filtro `fade` no se limita a su ventana —`fade=t=in:st=30`
deja en negro los primeros 30 segundos—, y por eso el fundido a negro está hecho
con `eq`.

**El zoom no se mueve al arrastrar sobre el preview**
A escala 1 no hay margen que mover: el paneo necesita zoom > 1. Es igual en el
render, no es un límite del preview.

**"ya hay un render en marcha"**
A propósito: dos ffmpeg pesados en paralelo tardan más que en serie y dejan la
máquina inservible. Cancelá el que corre o esperá a que termine.

**El overlay `.mov` no se ve en el preview**
ProRes 4444 con alfa lo entiende ffmpeg pero no el navegador. Se verá en el
render. Para verlo también en el preview, convertirlo a WebM con alfa
(VP9 + `yuva420p`).

**El overlay sale con un rectángulo negro en el render**
ffmpeg **escribe** WebM con alfa pero **no lo lee**. Por eso cada overlay guarda
también `seq`, la secuencia de PNG, que es la que usa el render. Si el item no
tiene `seq` (porque arrastraste un WebM a mano), el inspector lo avisa: pasalo por
`vcut overlays --project …` para que quede registrado con su secuencia.

**`vcut overlays` no encuentra nada**
Busca carpetas con `0000.png`, `0001.png`… Genéralas con `capture.mjs` de la
skill `motion-overlays`. Si el HTML no está al lado, el título se lee del sidecar
`_vcut.json` que deja la conversión.

**Un overlay se colocó en el clip equivocado**
El emparejamiento es por palabras. Subí `--min-score` para que sólo coloque lo
que está claro, o colocalo a mano arrastrándolo en la timeline. Con
`--min-score 1` no coloca nada y sólo convierte.

**Los stickers no aparecen en el studio**
`vcut stickers` los rasteriza a `assets/stickers` dentro de la skill. Necesita
Chrome o Edge instalado. Después, recargar la página.

**Abrí un paquete y los clips se ven en negro**
Los vídeos no se enlazaron. Mirá `sin_enlazar` en la salida de `unpack`: se
buscan **por nombre de archivo** dentro de `--media`, recursivamente. Si los
renombraste, hay que corregir `sources[].path` en `project.json` a mano.

**El paquete pesa mucho**
Sin `--media` el peso es casi todo secuencias de PNG de overlays. Un paquete de
ejemplo: 14 MB, de los que 13 son las tres secuencias.

## Exportación

**Resolve importa el timeline pero no encuentra los medios**
El FCPXML lleva rutas absolutas (`file:///C:/...`). Si moviste los archivos,
volvé a correr `new` sobre la ruta nueva, o usá "Relink media" en Resolve.

**Los cortes quedan un frame corridos**
Los `offset` del FCPXML se derivan de la suma de duraciones ya redondeadas a
frame, así que el spine no acumula huecos. Si igual pasa, revisá que `sequence.fps`
del proyecto coincida con el fps del timeline en el NLE.

**Premiere no abre el FCPXML**
Sólo Premiere 2023 en adelante lee FCPXML. Para versiones viejas usá `--format edl`
(pierde nombres largos y queda en una sola pista).

**El script `ffmpeg` corta en el lugar equivocado**
Usa `-c copy`, que sólo puede cortar en keyframes: se desplaza hasta ~1-2 s. Es
un preview, no el master. Para cortes exactos hace falta recomprimir, que es
justamente lo que este flujo evita.

## General

**`python3` no funciona**
En esta máquina `python3` es un stub de Microsoft Store. Usar `python`.

**NVENC falla al generar proxies**
El driver es más viejo que la API que pide este build de ffmpeg. La detección
prueba un encode real y cae a libx264 sola; sólo se nota en la velocidad.

**Se llenó el disco**
`cache/` es descartable: borralo entero y regeneralo con `vcut media` cuando
haga falta. Los proxies son lo que más pesa.
