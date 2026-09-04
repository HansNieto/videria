## QA de audio (silencedetect)

- Cortes revisados: 31 | con aire muerto: 10 | recuperable: 9.31 s

| id | archivo | corte | sugerido | por que |
|---|---|---|---|---|
| `u0003` | IMG_0171.MOV | 3.58-11.88 | 4.09-11.88 (-0.51s) | aire muerto |
| `u0020` | IMG_0185.MOV | 15.08-19.84 | 16.35-19.84 (-1.27s) | arranque en falso (0.96s de voz + 0.43s de pausa) |
| `u0023` | IMG_0186.MOV | 4.52-9.98 | 5.50-9.98 (-0.98s) | aire muerto, arranque en falso (0.07s de voz + 0.54s de pausa) |
| `u0024` | IMG_0187.MOV | 1.00-2.06 | 1.00-1.77 (-0.29s) | aire muerto |
| `u0026` | IMG_0188.MOV | 1.41-5.99 | 1.41-5.60 (-0.39s) | aire muerto |
| `u0028` | IMG_0188.MOV | 25.82-30.44 | 26.93-30.01 (-1.54s) | aire muerto |
| `u0030` | IMG_0190.MOV | 0.96-4.32 | 0.96-4.06 (-0.26s) | aire muerto |
| `u0032` | IMG_0191.MOV | 0.00-5.87 | 1.65-5.50 (-2.02s) | aire muerto, arranque en falso (0.95s de voz + 0.82s de pausa) |
| `u0035` | IMG_0192.MOV | 9.81-11.19 | 10.48-11.19 (-0.67s) | aire muerto |
| `u0038` | IMG_0193.MOV | 0.00-4.14 | 0.82-3.58 (-1.38s) | aire muerto, arranque en falso (0.44s de voz + 0.50s de pausa) |

### Tomas abortadas dentro del corte

Whisper no las escribe (limpia los titubeos), asi que en el texto
no se ven. Estas son las islas de voz que mide el audio:

- `u0020` IMG_0185.MOV -> islas 0.00-0.96 1.39-4.48
  - arranque en falso: voz en 0.00-0.96, pausa de 0.43s, la toma buena entra en 1.39 (relativo al corte)
- `u0023` IMG_0186.MOV -> islas 0.48-0.55 1.10-3.23 3.66-5.46
  - arranque en falso: voz en 0.48-0.55, pausa de 0.54s, la toma buena entra en 1.10 (relativo al corte)
- `u0032` IMG_0191.MOV -> islas 0.00-0.95 1.77-3.80 4.02-5.28
  - arranque en falso: voz en 0.00-0.95, pausa de 0.82s, la toma buena entra en 1.77 (relativo al corte)
- `u0038` IMG_0193.MOV -> islas 0.00-0.44 0.94-2.34 3.00-3.36
  - arranque en falso: voz en 0.00-0.44, pausa de 0.50s, la toma buena entra en 0.94 (relativo al corte)

Palabras con duracion imposible (whisper tapo un titubeo;
escucha ese tramo antes de fiarte del corte):

- `u0003` IMG_0171.MOV @ 3.70-5.46 (1.76s) 'elijas'
- `u0003` IMG_0171.MOV @ 6.84-9.92 (3.08s) 'ni'
- `u0005` IMG_0173.MOV @ 3.90-4.80 (0.90s) 'calcula'
- `u0008` IMG_0176.MOV @ 0.95-1.85 (0.90s) 'incluyendo'
- `u0012` IMG_0180.MOV @ 2.44-3.46 (1.02s) 'transportes,'
- `u0016` IMG_0182.MOV @ 11.58-12.86 (1.28s) 'a'
- `u0017` IMG_0183.MOV @ 0.57-1.57 (1.00s) 'después'
- `u0017` IMG_0183.MOV @ 1.57-3.33 (1.76s) 'considera'
- `u0017` IMG_0183.MOV @ 3.47-4.33 (0.86s) 'complejidad,'
- `u0018` IMG_0184.MOV @ 3.28-4.26 (0.98s) 'responsabilidades'
- `u0020` IMG_0185.MOV @ 15.20-16.90 (1.70s) 'agregue'
- `u0020` IMG_0185.MOV @ 18.66-19.62 (0.96s) 'utilidades,'
- `u0023` IMG_0186.MOV @ 4.64-6.74 (2.10s) 'define'
- `u0023` IMG_0186.MOV @ 7.26-8.14 (0.88s) 'clara'
- `u0025` IMG_0187.MOV @ 3.78-4.74 (0.96s) 'finalmente'
- `u0026` IMG_0188.MOV @ 2.71-4.65 (1.94s) 'crear'
- `u0026` IMG_0188.MOV @ 4.65-5.77 (1.12s) 'paquetes'
- `u0028` IMG_0188.MOV @ 25.94-29.42 (3.48s) 'niveles'
- `u0029` IMG_0188.MOV @ 34.04-36.60 (2.56s) 'sin'
- `u0032` IMG_0191.MOV @ 0.32-1.36 (1.04s) 'decisión,'
- `u0032` IMG_0191.MOV @ 4.63-5.65 (1.02s) 'requerir,'
- `u0035` IMG_0192.MOV @ 9.93-10.97 (1.04s) 'tiempo,'
- `u0038` IMG_0193.MOV @ 0.00-1.06 (1.06s) 'a'
- `u0039` IMG_0193.MOV @ 5.68-6.66 (0.98s) 'recuerda'

### Habla que no esta en ningun corte

Tramos con voz del original que el plan no cubre. Suele ser una
toma repetida que whisper borro al transcribir el archivo entero:
no existe ni como frase apagada, asi que nadie la puede elegir.

- IMG_0171.MOV 0.64-1.15 (0.51s), pegado a `u0002`, `u0003`
- IMG_0188.MOV 12.96-13.97 (1.01s), pegado a `u0027`
- IMG_0188.MOV 21.02-21.55 (0.53s), pegado a nada

### Cortes que entran o salen a media palabra

La isla de voz sigue mas alla del corte: se esta partiendo una
frase. Casi siempre significa que el corte agarro solo un pedazo
de la toma buena. Requiere tu decision, no se aplica solo:

- `u0002` IMG_0171.MOV sale en 0.64 pero la isla va de 0.00 a 1.15 (0.51s de voz cortada) -> sugerido out 1.37
- `u0020` IMG_0185.MOV entra en 15.08 pero la isla va de 14.84 a 16.04 (0.24s de voz cortada) -> sugerido in 14.72
- `u0024` IMG_0187.MOV entra en 1.00 pero la isla va de 0.50 a 1.55 (0.50s de voz cortada) -> sugerido in 0.38
- `u0027` IMG_0188.MOV sale en 12.96 pero la isla va de 11.30 a 13.97 (1.01s de voz cortada) -> sugerido out 14.19
- `u0031` IMG_0190.MOV entra en 10.85 pero la isla va de 10.64 a 11.46 (0.21s de voz cortada) -> sugerido in 10.52
