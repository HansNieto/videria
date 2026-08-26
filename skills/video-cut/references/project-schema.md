# Formato de `project.json`

Es la fuente de verdad del proyecto. El editor lo lee y lo reescribe; los
exportadores lo traducen a FCPXML/EDL. Se puede editar a mano (es JSON), pero
conviene pasar por `vcut decide` para que se recalculen las estadísticas.

```jsonc
{
  "vcut_version": 1,
  "name": "mi proyecto",
  "created_at": "2026-08-19T17:20:00+00:00",
  "updated_at": "2026-08-19T17:45:12+00:00",
  "language": "es",

  "input": {
    "paths": ["C:/videos"],       // lo que se pasó a `new`
    "sort": "name",               // name | date | none
    "recursive": false
  },

  "config": { /* umbrales usados en el último `analyze`, ver abajo */ },

  "sequence": { "fps": 25.0, "width": 1920, "height": 1080 },

  "stats": {
    "sources": 3,
    "raw_duration": 41.76,        // suma de los originales
    "cut_duration": 15.3,
    "timeline_duration": 15.3,    // suma de los segmentos encendidos
    "removed": 26.46,
    "removed_pct": 63.4,
    "segments_total": 10,
    "segments_enabled": 6
  },

  "sources": [ /* un objeto por archivo, ver abajo */ ],
  "segments": [ /* los cortes, EN ORDEN DE TIMELINE */ ],
  "groups": [ /* grupos de tomas repetidas */ ]
}
```

## `sources[]`

Un archivo de cámara. **Nunca se modifica.**

| campo | qué es |
|---|---|
| `id` | `s001`, `s002`… Estable dentro del proyecto. |
| `index` | Posición en el orden elegido (1-based). |
| `name`, `path` | Nombre y ruta absoluta del original. |
| `duration`, `fps`, `width`, `height`, `rotation` | Metadatos de ffprobe. `width`/`height` ya vienen corregidos por rotación. |
| `vcodec`, `acodec`, `pix_fmt`, `has_audio`, `has_video`, `size` | Para decidir si hace falta proxy. |
| `start_timecode` | Timecode de origen (para el EDL). `00:00:00:00` si no hay. |
| `recorded_at`, `recorded_ts` | Fecha de grabación (tag del contenedor, o mtime si no hay tag). Es lo que usa `--sort date`. |
| `needs_proxy` | `true` si el navegador no podría reproducir el original. |
| `proxy`, `waveform`, `filmstrip` | Rutas dentro de `cache/`. `null` si no se generaron. `filmstrip` es un objeto con `{url, cols, rows, count, tw, th, interval}`. |

## `segments[]`

**El orden del array es el orden del timeline.** Un segmento apagado sigue en el
array (no se pierde nada), simplemente no aparece en la secuencia.

| campo | qué es |
|---|---|
| `id` | `u0001`… Los creados a mano en el editor son `m001`… |
| `source` | Id del archivo del que sale. |
| `in`, `out` | Segundos **dentro del archivo original**. Es lo único que define el corte. |
| `dur`, `t` | Calculados: duración y posición en el timeline. `t` es `null` si está apagado. |
| `enabled` | Si entra en la secuencia final. |
| `text` | Lo que se dice en ese tramo. |
| `words` | `[{w, s, e}]` con tiempos absolutos del archivo original. Es lo que permite cortar por palabra. |
| `conf` | Confianza media de whisper (0–1). |
| `kind` | `speech` o `filler` (muletilla suelta). |
| `group`, `take_index`, `take_count` | A qué grupo de tomas pertenece y cuál es dentro del grupo. |
| `locked` | Marca que alguien lo tocó a mano. Es informativo, no protege: `analyze` reconstruye todo desde cero y `decide` re-aplica los grupos antes de tus overrides. `decisions.json` debe expresar la intención completa cada vez, no un delta. |
| `reason` | Por qué está encendido o apagado. Sólo informativo. |

`in`/`out` incluyen el padding (`pad_in`/`pad_out`); `speech_in`/`speech_out`
guardan dónde empieza y termina el habla real, sin aire.

## `groups[]`

| campo | qué es |
|---|---|
| `id` | `g001`… |
| `kind` | `repeated_take`. |
| `members` | Ids de segmentos, en orden cronológico. |
| `texts`, `scores` | Texto y puntaje de cada miembro. |
| `last` | El último miembro (la regla por defecto). |
| `best_scored` | El de mejor puntaje. Puede no ser el último. |
| `chosen` | El que queda encendido. `null` = todos apagados. |
| `decided_by` | `auto:last`, `modelo` o `editor`. |
| `links` | Por qué se agruparon: `{from, to, why, score}` con `why` en `repeticion`, `contenida` o `arranque-fallido`. |

El puntaje combina longitud (45%), confianza de whisper (35%) y ausencia de
muletillas (20%). **No decide nada por sí solo**: la elección por defecto es la
última toma, y `best_scored` está ahí como segunda opinión.

## `config`

Umbrales del último `analyze`. Cambiarlos y volver a correr `analyze` reconstruye
`segments` y `groups` desde las transcripciones (no re-transcribe).

| clave | default | qué hace |
|---|---|---|
| `pause` | 0.55 | Hueco (s) que corta una frase. También define qué es silencio. |
| `pad_in` / `pad_out` | 0.12 / 0.22 | Aire antes y después del habla. |
| `min_dur` | 0.18 | Frases más cortas se descartan. |
| `max_utt` | 14.0 | Frases más largas se parten por su hueco interno mayor. |
| `lookahead` | 8 | Cuántas frases adelante se buscan repeticiones. |
| `window` | 90.0 | Segundos de habla dentro de los que una retoma todavía cuenta. |
| `sim_ratio` | 0.68 | Similitud global para "misma toma". |
| `contain` | 0.80 | Cuánto de la frase corta debe aparecer en la larga. |
| `prefix` | 0.60 | Prefijo común para detectar arranques fallidos. |

## Invariantes que conviene no romper

- `0 <= in < out <= sources[source].duration`.
- Los ids de `segments` son únicos.
- Todo `groups[].members` y `groups[].chosen` apunta a un segmento existente.
- Un segmento con `group` no nulo aparece en `members` de ese grupo.
- Como mucho un miembro de cada grupo está `enabled` (el `chosen`).

`vcut decide` valida lo que puede y devuelve `warnings` con lo que no cuadró en
vez de romper el proyecto.
