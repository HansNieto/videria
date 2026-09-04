## QA de audio (silencedetect)

- Cortes revisados: 18 | con aire muerto: 6 | recuperable: 3.10 s

| id | archivo | corte | sugerido | por que |
|---|---|---|---|---|
| `u0001` | IMG_0151.MOV | 0.78-2.47 | 1.85-2.47 (-1.07s) | aire muerto, arranque en falso (0.31s de voz + 0.46s de pausa) |
| `u0006` | IMG_0155.MOV | 0.00-1.88 | 0.00-1.55 (-0.33s) | aire muerto |
| `u0019` | IMG_0162.MOV | 11.49-12.61 | 11.84-12.61 (-0.35s) | aire muerto |
| `u0020` | IMG_0162.MOV | 14.74-18.84 | 14.74-18.54 (-0.30s) | aire muerto |
| `u0023` | IMG_0165.MOV | 18.50-24.14 | 18.82-24.14 (-0.32s) | arranque en falso (0.09s de voz + 0.35s de pausa) |
| `u0026` | IMG_0167.MOV | 7.28-16.34 | 8.01-16.34 (-0.73s) | aire muerto |

### Tomas abortadas dentro del corte

Whisper no las escribe (limpia los titubeos), asi que en el texto
no se ven. Estas son las islas de voz que mide el audio:

- `u0001` IMG_0151.MOV -> islas 0.42-0.73 1.19-1.46
  - arranque en falso: voz en 0.42-0.73, pausa de 0.46s, la toma buena entra en 1.19 (relativo al corte)
- `u0023` IMG_0165.MOV -> islas 0.00-0.09 0.44-1.12 1.36-5.36 5.56-5.64
  - arranque en falso: voz en 0.00-0.09, pausa de 0.35s, la toma buena entra en 0.44 (relativo al corte)

Palabras con duracion imposible (whisper tapo un titubeo;
escucha ese tramo antes de fiarte del corte):

- `u0004` IMG_0153.MOV @ 7.60-8.52 (0.92s) 'probablemente'
- `u0005` IMG_0154.MOV @ 7.07-8.21 (1.14s) 'y'
- `u0022` IMG_0165.MOV @ 1.21-3.25 (2.04s) 'es'
- `u0023` IMG_0165.MOV @ 18.62-20.98 (2.36s) 'programas'
- `u0023` IMG_0165.MOV @ 21.04-22.88 (1.84s) 'se'
- `u0025` IMG_0167.MOV @ 1.55-4.69 (3.14s) 'conceptos'
- `u0025` IMG_0167.MOV @ 5.75-6.61 (0.86s) 'sencilla,'
- `u0026` IMG_0167.MOV @ 7.40-11.62 (4.22s) 'síguenos'
- `u0026` IMG_0167.MOV @ 11.76-12.88 (1.12s) 'y'

### Habla que no esta en ningun corte

Tramos con voz del original que el plan no cubre. Suele ser una
toma repetida que whisper borro al transcribir el archivo entero:
no existe ni como frase apagada, asi que nadie la puede elegir.

- IMG_0154.MOV 0.00-1.67 (1.67s), pegado a `u0005`
- IMG_0162.MOV 12.61-13.39 (0.78s), pegado a `u0018`, `u0019`, `u0020`
- IMG_0162.MOV 13.60-14.32 (0.72s), pegado a `u0018`, `u0019`, `u0020`
- IMG_0162.MOV 19.47-20.10 (0.63s), pegado a `u0020`

### Cortes que entran o salen a media palabra

La isla de voz sigue mas alla del corte: se esta partiendo una
frase. Casi siempre significa que el corte agarro solo un pedazo
de la toma buena. Requiere tu decision, no se aplica solo:

- `u0013` IMG_0159.MOV entra en 8.44 pero la isla va de 8.23 a 9.41 (0.21s de voz cortada) -> sugerido in 8.11
- `u0015` IMG_0159.MOV entra en 14.85 pero la isla va de 14.74 a 17.15 (0.11s de voz cortada) -> sugerido in 14.62
- `u0019` IMG_0162.MOV sale en 12.61 pero la isla va de 11.96 a 13.39 (0.78s de voz cortada) -> sugerido out 13.61
- `u0025` IMG_0167.MOV sale en 6.83 pero la isla va de 6.53 a 7.08 (0.25s de voz cortada) -> sugerido out 7.30
