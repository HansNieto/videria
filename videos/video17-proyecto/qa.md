## QA de audio (silencedetect)

- Cortes revisados: 16 | con aire muerto: 8 | recuperable: 3.53 s

| id | archivo | corte | sugerido | por que |
|---|---|---|---|---|
| `u0003` | IMG_0120.MOV | 5.02-5.92 | 5.02-5.72 (-0.20s) | aire muerto |
| `u0007` | IMG_0122.MOV | 7.56-13.74 | 8.05-13.74 (-0.49s) | aire muerto |
| `u0008` | IMG_0123.MOV | 0.26-8.08 | 0.52-8.08 (-0.26s) | arranque en falso (0.07s de voz + 0.31s de pausa) |
| `u0011` | IMG_0126.MOV | 0.00-8.13 | 1.18-8.13 (-1.18s) | arranque en falso (0.63s de voz + 0.67s de pausa) |
| `u0012` | IMG_0127.MOV | 0.00-1.12 | 0.00-0.65 (-0.47s) | aire muerto |
| `u0013` | IMG_0127.MOV | 1.50-5.66 | 1.50-5.34 (-0.32s) | aire muerto |
| `u0014` | IMG_0127.MOV | 6.76-8.36 | 6.76-8.13 (-0.23s) | aire muerto |
| `u0024` | IMG_0133.MOV | 12.18-17.24 | 12.56-17.24 (-0.38s) | aire muerto |

### Tomas abortadas dentro del corte

Whisper no las escribe (limpia los titubeos), asi que en el texto
no se ven. Estas son las islas de voz que mide el audio:

- `u0008` IMG_0123.MOV -> islas 0.00-0.07 0.38-0.82 1.01-4.15 4.58-5.80 6.15-7.59
  - arranque en falso: voz en 0.00-0.07, pausa de 0.31s, la toma buena entra en 0.38 (relativo al corte)
- `u0011` IMG_0126.MOV -> islas 0.00-0.63 1.30-3.11 3.57-4.30 4.45-5.80 6.05-7.90
  - arranque en falso: voz en 0.00-0.63, pausa de 0.67s, la toma buena entra en 1.30 (relativo al corte)

Palabras con duracion imposible (whisper tapo un titubeo;
escucha ese tramo antes de fiarte del corte):

- `u0011` IMG_0126.MOV @ 0.51-2.11 (1.60s) 'mensaje'
- `u0012` IMG_0127.MOV @ 0.00-0.90 (0.90s) 'Otro'
- `u0014` IMG_0127.MOV @ 7.24-8.14 (0.90s) 'permite...'

### Habla que no esta en ningun corte

Tramos con voz del original que el plan no cubre. Suele ser una
toma repetida que whisper borro al transcribir el archivo entero:
no existe ni como frase apagada, asi que nadie la puede elegir.

- IMG_0120.MOV 5.94-7.28 (1.34s), pegado a `u0002`, `u0003`
- IMG_0133.MOV 9.93-10.72 (0.79s), pegado a `u0023`, `u0024`

### Cortes que entran o salen a media palabra

La isla de voz sigue mas alla del corte: se esta partiendo una
frase. Casi siempre significa que el corte agarro solo un pedazo
de la toma buena. Requiere tu decision, no se aplica solo:

- `u0003` IMG_0120.MOV entra en 5.02 pero la isla va de 4.91 a 5.50 (0.11s de voz cortada) -> sugerido in 4.79
- `u0004` IMG_0120.MOV entra en 10.32 pero la isla va de 10.19 a 14.05 (0.13s de voz cortada) -> sugerido in 10.07
- `u0014` IMG_0127.MOV entra en 6.76 pero la isla va de 6.63 a 7.91 (0.13s de voz cortada) -> sugerido in 6.51
