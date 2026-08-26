---
name: subtitulo
description: Genera vídeos verticales con subtítulos estilo CapCut — líneas cortas que se apilan hacia abajo, revelado palabra por palabra, y una palabra clave en otra tipografía y color, con sombra difusa y sin contorno. Úsala cuando el usuario pida un vídeo con este subtitulado, quiera cambiar el estilo de los subtítulos (posición, color, fuente, número de líneas, palabra resaltada), o pida rehacer un vídeo con otro tema manteniendo el mismo look. Triggers: "subtítulos", "subtitulado", "estilo CapCut", "palabra resaltada", "genera un video de", "cambia la posición del texto".
---

# Subtitulado apilado estilo CapCut

Genera el vídeo con MoneyPrinterTurbo aplicando un estilo de subtítulo ya
medido y afinado. No reinventes los valores: están calibrados contra
fotogramas de referencia reales y cada uno tiene su razón documentada en
`aplicar_estilo.py`.

## Cómo se ve

Las líneas se **acumulan** ancladas por su borde superior, no se reemplazan:

```
paso 1:   El calentamiento
paso 2:   El calentamiento
          global actual          <- línea nueva; la de arriba NO se mueve
paso 3:   El calentamiento
          global actual
          está impulsado
```

Dentro de la línea en curso las palabras entran una a una.

**El apilado sólo ocurre cuando hay una palabra resaltada.** Si la tarjeta no
contiene ninguna, aparece una sola línea y se sustituye por la siguiente. Con
clave, se acumulan hasta **3 filas** y las líneas vecinas entran como contexto
de esa palabra. Así el apilado marca los momentos importantes en lugar de ser
el comportamiento constante. Se desactiva con
`subtitle_stack_only_with_keyword = false`.

La tarjeta también se cierra al terminar una oración: arrastrar el comienzo de
la frase siguiente al pie de la anterior mezclaría dos ideas.

## Ejecución

Directorio de trabajo: esta carpeta. Un solo comando:

```bash
python aplicar_estilo.py --tema "El calentamiento global"
```

El helper aplica el estilo a `~/MoneyPrinterTurbo/config.toml`, renderiza y
copia el resultado a la raíz del proyecto. Imprime `VIDEO=<ruta>` al terminar.

Opciones útiles:

| Flag | Para qué |
|---|---|
| `--guion archivo.txt` | usar un guion ya escrito, sin llamar al LLM |
| `--terminos "glacier,drought"` | fijar las keywords de Pexels, sin llamar al LLM |
| `--voz es-MX-JorgeNeural-Male` | otra voz de Edge TTS |
| `--parrafos 3` | vídeo más largo (~30s por párrafo) |
| `--nombre clima` | nombre del archivo de salida |
| `--solo-config` | ajustar el estilo sin renderizar |

## Iterar sobre el aspecto sin gastar LLM

Cuando ya hay un guion que gusta, **guárdalo y pásalo con `--guion` junto a
`--terminos`**. Así el render no llama a Gemini en ningún punto y deja de
depender de su disponibilidad; sólo quedan Edge TTS y Pexels. Es lo que
convierte un reintento en algo determinista.

El guion generado queda en `~/MoneyPrinterTurbo/storage/tasks/<id>/script.json`.
Si un render falla a mitad, el guion también está en el log: rescátalo de ahí
antes de volver a pedirlo.

## Ajustes del estilo

Todos viven en `config.toml` y se cambian sin tocar código. Los define
`ESTILO` en `aplicar_estilo.py`, que es la fuente de la verdad:

| Clave | Valor | Nota |
|---|---|---|
| `subtitle_vertical_offset` | `300` | desde el CENTRO; positivo baja |
| `subtitle_keyword_color` | `#4A90E0` | muestreado de la referencia |
| `subtitle_keyword_font` | `DancingScript-Bold.ttf` | en `resource/fonts` |
| `subtitle_keyword_size_ratio` | `1.5` | compensa la altura de x de la script |
| `subtitle_lines_per_card` | `3` | filas en pantalla, no grupos |
| `subtitle_stack_only_with_keyword` | `true` | apilar sólo si hay palabra resaltada |
| `subtitle_karaoke_max_chars` | `18` | a cuerpo 80 caben ~22 en 1080px |

## Cosas que ya se aprendieron a base de fallos

**Los 503 de Gemini son por petición, no por modelo.** Comprobar que el modelo
responde justo antes no sirve de nada: puede fallar el siguiente request.
`gemini-flash-latest` es el que más se satura porque es el alias que todos
usan; los pinneados (`gemini-3.6-flash`) aguantan mucho mejor.

**Edge TTS no da una palabra por cue.** Las cantidades llegan juntas
(`'85 mil'`, `'420 partes'`) y los decimales en tres piezas (`'1'`, `','`,
`'1'`). Tres bugs distintos salieron de ahí. Si aparece otro defecto raro en un
subtítulo, mirar primero los cues crudos antes de tocar reglas.

**Reducir el cuerpo para que quepa una línea larga es peor que partirla.** Deja
tarjetas de tamaños distintos, y la tipografía inconsistente se nota mucho más
que una línea repartida en dos filas. El cuerpo es fijo a propósito.

**Los guiones con cifras, fechas y siglas son los que destapan los fallos.**
Los textos "bonitos" pasan siempre. Para probar el agrupador, usar temas con
datos.

## Límite conocido

El emparejamiento de imágenes es por keywords del tema completo, no frase por
frase, así que el clip que se ve no corresponde a lo que dice la voz en ese
segundo. Además Pexels empareja por palabras sueltas: buscar "titan security
key" devuelve stock genérico de seguridad. Para temas visualmente concretos,
usar material propio con `--video-source local` da un resultado mucho mejor.
