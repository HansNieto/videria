## QA de audio (silencedetect)

- Cortes revisados: 19 | con aire muerto: 4 | recuperable: 2.00 s

| id | archivo | corte | sugerido | por que |
|---|---|---|---|---|
| `u0002` | IMG_0136.MOV | 0.06-2.56 | 0.06-2.34 (-0.22s) | aire muerto |
| `u0015` | IMG_0146.MOV | 0.42-5.74 | 0.42-5.46 (-0.28s) | aire muerto |
| `u0018` | IMG_0147.MOV | 5.82-8.80 | 5.82-7.66 (-1.14s) | aire muerto |
| `u0022` | IMG_0149.MOV | 9.45-12.95 | 9.45-12.59 (-0.36s) | aire muerto |

Palabras con duracion imposible (whisper tapo un titubeo;
escucha ese tramo antes de fiarte del corte):

- `u0002` IMG_0136.MOV @ 1.46-2.34 (0.88s) 'cuando'
- `u0003` IMG_0136.MOV @ 5.94-7.74 (1.80s) 'las'
- `u0013` IMG_0144.MOV @ 11.04-11.94 (0.90s) 'anticiparse,'
- `u0015` IMG_0146.MOV @ 4.46-5.52 (1.06s) 'olvidados,'
- `u0018` IMG_0147.MOV @ 5.94-8.58 (2.64s) 'ocurre'
- `u0020` IMG_0148.MOV @ 1.88-8.42 (6.54s) 'definir'

### Habla que no esta en ningun corte

Tramos con voz del original que el plan no cubre. Suele ser una
toma repetida que whisper borro al transcribir el archivo entero:
no existe ni como frase apagada, asi que nadie la puede elegir.

- IMG_0142.MOV 0.00-1.00 (1.00s), pegado a `u0010`
- IMG_0147.MOV 4.37-5.29 (0.92s), pegado a `u0017`, `u0018`
- IMG_0147.MOV 10.92-11.48 (0.56s), pegado a `u0018`, `u0019`
- IMG_0149.MOV 8.91-9.45 (0.54s), pegado a `u0022`
- IMG_0149.MOV 18.59-20.95 (2.36s), pegado a `u0023`

### Cortes que entran o salen a media palabra

La isla de voz sigue mas alla del corte: se esta partiendo una
frase. Casi siempre significa que el corte agarro solo un pedazo
de la toma buena. Requiere tu decision, no se aplica solo:

- `u0010` IMG_0142.MOV sale en 5.90 pero la isla va de 1.82 a 6.12 (0.22s de voz cortada) -> sugerido out 6.34
- `u0016` IMG_0146.MOV entra en 10.21 pero la isla va de 9.99 a 12.51 (0.22s de voz cortada) -> sugerido in 9.87
- `u0017` IMG_0147.MOV sale en 1.66 pero la isla va de 1.12 a 1.88 (0.22s de voz cortada) -> sugerido out 2.10
- `u0019` IMG_0147.MOV entra en 11.48 pero la isla va de 10.92 a 16.92 (0.56s de voz cortada) -> sugerido in 10.80
- `u0022` IMG_0149.MOV entra en 9.45 pero la isla va de 8.91 a 12.37 (0.54s de voz cortada) -> sugerido in 8.79
