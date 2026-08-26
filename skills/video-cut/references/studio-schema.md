# `timeline.json` — la capa creativa

Todo lo que no es un corte. `project.json` sigue siendo la verdad sobre qué
trozo de qué archivo va en qué orden; este archivo dice qué pasa encima. Están
separados para que `analyze` pueda reconstruir los cortes desde cero sin
llevarse por delante el trabajo de post.

```jsonc
{
  "studio_version": 1,
  "name": "mi proyecto",
  "canvas":  { "width": 1080, "height": 1920, "fps": 30, "bg": "#000000" },
  "render":  { "encoder": "auto", "quality": 20, "loudnorm": true,
               "loudnorm_i": -14.0, "fit": "cover", "draft_height": 720,
               "audio_bitrate": "192k" },
  "styles":  { "capcut": { … }, "titulo": { … }, "nota": { … } },
  "tracks":  [ { "id": "t_sub", "kind": "text", "z": 20, "items": [ … ] }, … ],
  "clips":   { "u0001": { "zoom": …, "speed": 1.0, "look": … } },
  "transitions": [ { "at_seg": "u0002", "type": "punch_zoom", "dur": 0.3 } ],
  "counter": 41
}
```

## Anclas: la costura entre las dos capas

Un item puede colgar de un tiempo absoluto (`t`) o de un clip
(`anchor: {seg, offset}`). Con ancla, `t` se calcula como `clip.t0 + offset`
cada vez que se resuelve el timeline. Consecuencias, todas deseadas:

- Recortar o reordenar un clip **arrastra su texto con él**.
- Apagar un clip **esconde** lo que colgaba de él (no lo borra: sigue en el
  archivo y vuelve si se enciende).
- Los subtítulos generados desde la transcripción **siempre** están anclados.
  Un título que el usuario coloca a mano puede no estarlo, y entonces se queda
  donde lo puso aunque los cortes cambien.

`anchor.clamp: false` deja que el item empiece antes que su clip; se usa para el
SFX de una transición, que tiene que sonar justo antes del corte.

`gc` (botón "Limpiar huérfanos", o `POST /api/timeline/gc`) borra lo que apunta
a segmentos que ya no existen. Sólo cuando se pide: un ancla huérfana es un
aviso, no un error.

## `tracks[]`

| campo | qué es |
|---|---|
| `id` | `t_sub`, `t_txt`, `t_ovl`, `t_mus`, `t_sfx`. Estables. |
| `kind` | `text` · `overlay` · `audio`. Decide qué controles ofrece el inspector y cómo entra en el render. |
| `z` | Orden de composición. Mayor va encima. Los textos por encima de los overlays. |
| `hidden` / `locked` | Ocultar quita la pista del render; bloquear sólo impide editarla. |
| `gain`, `duck` | Sólo en pistas de audio. `duck` baja la pista bajo la voz. |

## Items de texto

```jsonc
{
  "id": "s0007", "kind": "text", "style": "capcut", "auto": true,
  "anchor": { "seg": "u0003", "offset": 0.06 }, "dur": 2.82,
  "lines": [ [ {"w":"porque","s":0.0,"e":0.22,"key":false},
               {"w":"el","s":0.22,"e":0.31,"key":false} ],
             [ {"w":"SIMPLEMENTE","s":0.9,"e":1.4,"key":true} ] ],
  "x": null, "y": null,
  "reveal": null, "anim_in": null, "anim_out": null, "anim_dur": null,
  "override": { "size": 92, "color": "#FFE066" }
}
```

- **`lines` es la fuente de la verdad, no un texto plano.** El reparto en líneas
  ya está decidido, con las métricas reales del `.ttf` (PIL, en el servidor).
  Ni el preview ni ffmpeg vuelven a partir nada: si cada uno lo hiciera a su
  manera, el vídeo final no se vería como el preview. Cuando cambia la
  tipografía, el cuerpo o el ancho de la caja hay que volver a partir
  explícitamente (`/api/wrap` para un item, `/api/relayout` para todos).
- `s`/`e` de cada palabra son **relativos al inicio del item**, para que
  arrastrarlo no descoloque el revelado.
- `key: true` marca la palabra resaltada: otra fuente, otro color, otro cuerpo.
- `x`/`y` en `null` significa "usa la caja del estilo". Arrastrar sobre el
  preview los fija.
- `auto: true` marca las tarjetas generadas. Regenerar subtítulos borra sólo
  esas; en cuanto el usuario edita una, pasa a `false` y sobrevive.
- `override` pisa cualquier clave del estilo, sólo para ese item.

## Estilos de texto

El estilo `capcut` reproduce el subtitulado apilado ya calibrado en la skill
`subtitulo`: los valores salen de medir fotogramas reales.

| clave | qué hace |
|---|---|
| `font`, `size`, `color` | Nombre de archivo del `.ttf`, cuerpo en px y color. |
| `keyword_font`, `keyword_color`, `keyword_size_ratio` | La palabra resaltada. |
| `line_height`, `letter_spacing` | Interlineado (múltiplo del cuerpo) y tracking. |
| `shadow` | `{opacity, blur, dx, dy, color}`. Sombra difusa, sin contorno. |
| `outline`, `outline_color` | Contorno, si se quiere en vez de sombra. |
| `box` | `{x, y, w}` en fracciones del lienzo. `y` es el borde **superior** de la primera línea: por eso apilar no mueve lo que ya estaba escrito. |
| `align` | `center` · `left` · `right`. |
| `max_lines`, `max_words_line`, `max_chars_line` | Límites del reparto. |
| `stack_only_with_keyword` | Con `true`, sólo se apilan líneas en las tarjetas que tienen palabra resaltada. Así el apilado marca los momentos importantes en vez de ser el comportamiento constante. |
| `reveal` | `word` (palabra a palabra) o `none`. |
| `anim_in`, `anim_out`, `anim_dur` | Ver la tabla de animaciones. |
| `bg` | `{color, opacity, pad}` para estilos tipo etiqueta. Rectángulo recto. |

**Todos los px están medidos sobre 1080 de ancho** y se escalan por `W/1080`.
Cambiar el lienzo no rompe el diseño, aunque conviene revisar posiciones.

## Animaciones

`none` · `fade` · `pop` · `zoom_in` · `zoom_out` · `slide_up` · `slide_down` ·
`slide_left` · `slide_right` · `bounce`.

Las curvas están **una sola vez**, en `assbuild.ANIM`, y el preview las pide por
`/api/catalog`. La de salida es la de entrada recorrida al revés.

Dos límites del formato ASS que explican el resultado:

- El desplazamiento (`dx`/`dy`) sólo puede ser **un tramo lineal** (`\move`), así
  que un rebote con desplazamiento no se puede expresar; `bounce` es sólo escala.
- Con revelado por palabra, la animación de entrada **no toca el alfa**: el alfa
  ya lo maneja el revelado y los dos se pelearían por el mismo tag.

En el apilado, la animación de entrada de cada línea empieza cuando esa línea
aparece, no cuando arranca la tarjeta. Si se midiera desde la tarjeta, la
segunda y la tercera línea se perderían la animación entera.

## `clips` — ajustes por segmento

```jsonc
"u0004": {
  "zoom": { "kf": [ {"t":0.0,"scale":1.0,"x":0.0,"y":0.0,"ease":"inout"},
                    {"t":4.1,"scale":1.22,"x":0.0,"y":-0.08,"ease":"inout"} ],
            "preset": "push_lento" },
  "speed": 1.0, "volume": 0.0, "mute": false, "flip": false, "fit": null,
  "look": { "brightness":0, "contrast":1.12, "saturation":1.1,
            "temp":0.15, "vignette":0.35 }
}
```

- `t` de cada keyframe: **segundos desde el inicio del clip**, ya en tiempo de
  salida (afectado por la velocidad). Recortar el clip no descoloca el zoom.
- `scale`: 1 = plano completo, 2 = píxeles reales del original. El clip se
  encuadra a `canvas × ZMAX` antes del `zoompan`, así que hasta 2× no hay
  interpolación con material del doble de resolución que el lienzo.
- `x`/`y`: paneo en −1…1 sobre el margen que deja el zoom. A escala 1 no hay
  margen y el paneo no hace nada, igual que en el render.
- `ease`: la curva **de llegada** a ese keyframe. Tres formas, todas válidas:
  - un nombre: `linear` · `in` · `out` · `inout` · `expo` · `back` · `hold`;
  - el id de una curva del catálogo (`studio.EASE_CURVES`): `suave`,
    `entra_lento`, `frena`, `latigo`, `rebote`, `anticipa`, `resorte`;
  - un bezier a mano: `{"bezier": [x1, y1, x2, y2]}`, las dos manijas en el
    cuadrado unidad del tramo. `x` es el tiempo normalizado (se recorta a
    0…1 para que el tiempo no retroceda) y `y` la fracción de valor
    recorrida; `y` fuera de 0…1 se pasa de largo y vuelve.

  El preview resuelve el bezier exacto; el render lo **hornea** en tramos
  rectos (`render._bake_bezier`) porque las expresiones de ffmpeg no tienen
  bucles. La diferencia entre los dos es menor que 0,002 de escala. Un canal
  que no se mueve en el tramo (el paneo, casi siempre) no se hornea.
- `speed`: 0.25–4. Cambia la duración de salida del clip, y con ella el total
  de la secuencia y la posición de todo lo que va después.

## Transiciones

```jsonc
{ "id": "t0003", "at_seg": "u0005", "type": "punch_zoom",
  "dur": 0.30, "strength": 1.0, "sfx": "C:/…/2_swish.wav", "sfx_gain": -5 }
```

`at_seg` es el clip **de entrada**: la transición vive en el corte por el que ese
clip empieza. La del primer clip se ignora (no hay corte donde vivir) pero se
conserva en el archivo.

**No consumen tiempo.** Son efectos centrados en el corte, no mezclas de dos
clips. Un `xfade` real solapa material y acorta la secuencia, y entonces cada
texto, cada zoom y cada SFX posterior habría que recalcularlo contra un total
que cambia. Con efectos por ventana, la secuencia mide exactamente la suma de
los clips. Es también lo que hacen de verdad las transiciones de TikTok: un
golpe en el corte.

| tipo | cómo está hecho |
|---|---|
| `punch_zoom` | Pico de zoom triangular, en el `zoompan` de post. |
| `shake` | Zoom pequeño + jitter senoidal en x/y (dos frecuencias distintas). |
| `whip` | Rampa rápida de zoom para tener margen, y barrido lateral que salta de signo justo en el corte. |
| `flash` | `eq=brightness` por fotograma. |
| `blur` | `gblur` en escalones con `enable`: el filtro no acepta expresiones por fotograma. |
| `glitch` | `rgbashift` en escalones. |
| `pixelize` | `pixelize` en escalones. |
| `fade_black` | `eq` con brillo a −1 y saturación a 0. **No** con el filtro `fade`: `fade=t=in:st=X` deja en negro todo lo anterior a X, no sólo su ventana. |

Los escalones de un mismo tipo se agrupan por valor y comparten una sola
instancia del filtro con las ventanas sumadas en el `enable`, para no encadenar
decenas de filtros.

## Items de overlay y de audio

```jsonc
{ "kind": "overlay", "src": "…/assets/overlays/01_limite.webm",
  "seq": { "dir": "…/frames/01_limite", "first": 0, "fps": 30, "frames": 126 },
  "anchor": {…}, "dur": 4.17,
  "x": 0.5, "y": 0.30, "scale": 0.83, "opacity": 1, "fade": 0.28, "loop": false }

{ "kind": "audio", "src": "C:/…/musica.mp3", "t": 0.0, "dur": 84.8,
  "in": 0.0, "gain": -3, "fade_in": 1.5, "fade_out": 2.0, "loop": true }
```

- **`src` es para el preview y `seq` para el render.** Chrome reproduce WebM/VP9
  con alfa y el canal llega intacto al canvas; ffmpeg *escribe* WebM con alfa
  pero **no lo lee**, y al superponerlo el overlay sale sobre un rectángulo
  negro. Las dos cosas están medidas en este equipo. Si la carpeta de `seq`
  desaparece, el render avisa y usa `src` perdiendo la transparencia.
- Un `.mov` ProRes 4444 funciona en el render pero no en el preview.
- Los stickers son PNG normales: no llevan `seq` y no la necesitan.
- **B-roll** (`"broll": true`): un plano de recurso que puso `vcut broll`. Es un
  overlay corriente con `scale: 1` y del tamaño exacto del lienzo, porque el
  clip se recorta al encuadre y se queda mudo *al descargarlo*, no al
  renderizar. Lleva `stock: {query, autor, pagina, fuente}` para saber de dónde
  salió y poder citarlo. Volver a correr `vcut broll` reemplaza los que tengan
  esta marca y respeta el resto; con `--add` no borra nada.
- `in` de un audio es el punto de entrada dentro del archivo.
- El ducking usa la voz de los clips como cadena lateral
  (`sidechaincompress`), así que la música baja sola cuando alguien habla.

## Plantillas (`templates/*.json`)

```jsonc
{
  "vcut_template": 1, "name": "tiktok", "label": "TikTok vertical",
  "canvas": {…}, "render": {…}, "styles": null,
  "recipe": {
    "subs":        { "style": "capcut", "track": "t_sub" },
    "zooms":       { "pattern": ["push_lento","punch_in","ken_burns"],
                     "min_dur": 1.0 },
    "transitions": { "every": 3, "types": ["punch_zoom","whip","flash"],
                     "dur": 0.28, "sfx": true },
    "overlays":    { "place": true, "y": 0.30 }
  }
}
```

`styles: null` significa "los que trae el studio". `zooms.pattern` **rota**: el
clip 1 recibe el primero, el 2 el segundo, y vuelta a empezar. `transitions.every`
es cada cuántos cortes se pone una — con 1 en cada corte, el vídeo cansa a los
diez segundos.

## Paquetes (`*.vcutpack`)

Un zip con `pack.json` de manifiesto:

```
project.json  timeline.json  decisions.json  review.md  qa.md
transcripts/  fonts/
assets/audio/…    assets/media/…    assets/seq/<nombre>/…
media/…           (sólo con --media)
pack.json  LEEME.md
```

Al empaquetar, las rutas del timeline se reescriben a rutas **relativas al zip**;
al abrirlo, se vuelven absolutas contra la carpeta destino. Los originales se
enlazan buscando `sources[].name` dentro de `--media`, recursivamente; los
proxies, ondas y miniaturas se ponen a `null` porque son de la máquina que
empaquetó.

Cada secuencia viaja con su sidecar `_vcut.json` (`{title, fps}`): sin él, un
overlay que llega sin su HTML no sabría de qué habla y no se podría recolocar.

## El grafo del render

```
por clip   -ss/-t → fps → encuadre a canvas×2 → velocidad → zoompan → look
concat     video y audio de todos los clips a la vez
post       zoompan de transiciones → filtros por ventana → overlays → ASS
audio      voz + música con ducking + SFX → amix → loudnorm
```

- El `zoompan` de post se añade **sólo** si hay alguna transición geométrica:
  reescala todos los fotogramas, y ponerlo cuando no hace falta sería pagar
  calidad por nada.
- El reloj de `zoompan` es `it`, no `t`. Los filtros con `enable` usan `t`.
- El texto se compone **después** de los efectos de vídeo, así que sigue legible
  durante un fundido a negro o un desenfoque. Es deliberado.
- `cache/last_render_cmd.txt` guarda el comando completo y
  `cache/last_render.log` el stderr de ffmpeg. Para depurar un render negro o
  raro, cortar el grafo por etapas (`[vc]`, `[vg]`, `[vfx]`, `[vt]`) y sacar un
  fotograma de cada una.

## Texto en el render: por qué ASS

libass es vectorial, rápido y hace karaoke, sombras y transformaciones sin
generar PNGs. El precio es expresar el diseño en tags:

- **Un evento por línea**, con su `\pos`. ASS no permite ajustar el interlineado
  de otro modo.
- **El revelado no cambia el ancho de la línea**: se emite la línea completa y
  las palabras que aún no toca se ponen transparentes. Si se fuera añadiendo
  texto, la línea se recentraría en cada palabra y saltaría.
- **La sombra difusa es una copia borrosa debajo**, no el `Shadow` del formato
  (que es un desplazamiento duro). Con `\bord0`, `\blur` difumina el relleno.
- **El nombre de la fuente incluye la subfamilia** cuando no es Regular. Medido:
  con `Fontname: Inter` y `Bold: -1`, libass devuelve un Inter regular engordado
  a mano, no Inter Black, aunque Inter Black sea el único Inter del `fontsdir`.
  Con `Fontname: Inter Black` sale la fuente real, que es la que midió PIL.

## Endpoints

| método | ruta | para qué |
|---|---|---|
| GET/POST | `/api/timeline` | leer y guardar las dos capas juntas |
| POST | `/api/timeline/gc` | quitar anclas y ajustes huérfanos |
| GET | `/api/catalog` | transiciones, animaciones, presets, fuentes, librería |
| POST | `/api/wrap` | repartir un texto en líneas con las métricas del `.ttf` |
| POST | `/api/subs` | generar los subtítulos desde la transcripción |
| POST | `/api/relayout` | volver a partir todos los textos de una pista |
| POST | `/api/render` | lanzar un render (uno a la vez); devuelve un id |
| GET | `/api/render/<id>` | progreso, resultado o error |
| POST | `/api/render/<id>/cancel` | matar el ffmpeg |
| GET | `/api/asset?path=` | servir un archivo de la librería (sólo dentro de las raíces permitidas) |
| GET | `/api/font/<archivo>` | el `.ttf` para el `@font-face` del preview |

## Invariantes que conviene no romper

- Todo item de texto tiene `lines`, aunque sea de una sola palabra.
- Los `s`/`e` de las palabras son relativos al item y crecen monótonamente.
- `anchor.seg` apunta a un segmento existente, o el item no sale (y `gc` lo
  puede limpiar).
- Como mucho una transición por corte (`at_seg` único).
- `scale` de un keyframe está entre 1 y `ZMAX`; `x`/`y` entre −1 y 1.
- `speed` entre 0.25 y 4.
- El total de la secuencia es la suma de `dur/speed` de los clips encendidos.
  Nada de lo que hay en `timeline.json` lo cambia.
