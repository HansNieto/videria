# Revision de cortes: video19-proyecto

- Material bruto: **00:02:30** en 17 archivo(s)
- Propuesta automatica: **00:01:04** (57.0% eliminado)
- Frases: 26 totales, 12 encendidas, 3 grupos de tomas repetidas

## Notas de la revision anterior

Revisión manual: se retiraron la prueba de flash, repeticiones, fragmentos de toma y la corrección hablada fuera del guion.

## Tu tarea

1. Lee el **dialogo propuesto**: debe leerse como un discurso continuo y
   con sentido. Si hay saltos, frases cortadas o ideas duplicadas, se
   eligio mal alguna toma.
2. Revisa cada **grupo de tomas**. La regla por defecto es quedarse con la
   ultima, pero manda la coherencia: si la ultima esta incompleta o la
   anterior encaja mejor con lo que sigue, elige esa.
3. Marca para apagar lo que sobre (muletillas sueltas, frases que se
   repiten sin ser el mismo grupo, comentarios fuera de guion).
4. Escribe `decisions.json` con tu veredicto y aplicalo con `vcut decide`.

## Dialogo propuesto (lo que quedaria encendido)


*-- IMG_0154.MOV --*

- `u0005` Sabías que la mayoría de apps que usas todos los días no funcionarían sin las APIs y probablemente no te diste cuenta. `[g001 toma 3/3]`

*-- IMG_0155.MOV --*

- `u0006` imagina que estas en un restaurante,
- `u0007` tu eres el cliente, la cocina es el servidor y el mesero es la API.

*-- IMG_0156.MOV --*

- `u0008` que tú le pides una hamburguesa al mesero. Él lleva el pedido a la cocina y regresa con la comida.

*-- IMG_0157.MOV --*

- `u0009` si hace exactamente eso.

*-- IMG_0159.MOV --*

- `u0015` Recibe una solicitud de una aplicación la lleva al server y devuelve la respuesta. `[g002 toma 5/5]`

*-- IMG_0162.MOV --*

- `u0018` le hace la petición mediante la API y recibe los resultados en segundos

*-- IMG_0164.MOV --*

- `u0021` Por ejemplo, cuando la app del clima muestra la temperatura de tu ciudad. `[g003 toma 3/3]`

*-- IMG_0165.MOV --*

- `u0022` En resumen, el API es el puente que permite que se comuniquen entre diferentes
- `u0023` programas que se comuniquen entre sí.

*-- IMG_0167.MOV --*

- `u0025` Si quieres aprender más conceptos de tecnología de forma sencilla,
- `u0026` síguenos y dinos en los comentarios cual quieres que expliquemos en el siguiente video.

## Grupos de tomas repetidas

### g001 -- 3 tomas (elegida ahora: `u0005`, por auto:last)

| toma | id | archivo @ tiempo | conf | score | texto |
|---|---|---|---|---|---|
| 1 | `u0002` | IMG_0152.MOV @ 00:00:00.00 | 0.88 | 0.77 | que la mayoría de apps que usas. |
| 2 | `u0003` | IMG_0153.MOV @ 00:00:00.35 | 0.93 | 0.98 | ¿Sabías que la mayoría de apps que usas todos los días no funcionarían sin las APIs? |
| 3 | `u0005` **<-** | IMG_0154.MOV @ 00:00:02.33 | 0.91 | 0.97 | Sabías que la mayoría de apps que usas todos los días no funcionarían sin las APIs y probablemente no te diste cuenta. |

### g002 -- 5 tomas (elegida ahora: `u0015`, por auto:last)

| toma | id | archivo @ tiempo | conf | score | texto |
|---|---|---|---|---|---|
| 1 | `u0010` | IMG_0158.MOV @ 00:00:00.00 | 0.91 | 0.97 | Sigue una solicitud de una aplicación, la lleva al servidor y regresa con la respuesta. |
| 2 | `u0011` | IMG_0159.MOV @ 00:00:00.00 | 0.92 | 0.75 | recibe la solicitud de una aplicación, |
| 3 | `u0012` | IMG_0159.MOV @ 00:00:05.94 | 0.96 | 0.76 | recibe la solicitud de una aplicación, |
| 4 | `u0014` | IMG_0159.MOV @ 00:00:10.55 | 0.62 | 0.68 | server, recibe la respuesta de una aplicación. |
| 5 | `u0015` **<-** | IMG_0159.MOV @ 00:00:14.85 | 0.83 | 0.94 | Recibe una solicitud de una aplicación la lleva al server y devuelve la respuesta. |

### g003 -- 3 tomas (elegida ahora: `u0021`, por auto:last)

| toma | id | archivo @ tiempo | conf | score | texto |
|---|---|---|---|---|---|
| 1 | `u0016` | IMG_0160.MOV @ 00:00:00.00 | 0.95 | 0.76 | cuando la aplicación del clima muestra |
| 2 | `u0017` | IMG_0161.MOV @ 00:00:00.00 | 0.93 | 0.97 | Por ejemplo, cuando la app del clima muestra la temperatura de tu ciudad. |
| 3 | `u0021` **<-** | IMG_0164.MOV @ 00:00:00.61 | 0.95 | 0.98 | Por ejemplo, cuando la app del clima muestra la temperatura de tu ciudad. |

## Apagadas por muletilla / ruido

- `u0001` (apagada por revision) Está con flash? No, no
- `u0004` (apagada por revision) Y probablemente las usas pero no te diste cuenta.
- `u0013` (apagada por revision) la lleves al
- `u0019` (apagada por revision) acá dice
- `u0020` (apagada por revision) no pero dije por ejemplo tu dices no de no y vuelvo a decir por ejemplo mira revisa
- `u0024` (apagada por revision) a aprender más conceptos.

## Formato de decisions.json

```json
{
  "groups":  { "g001": "u0007" },
  "disable": ["u0031", "u0044"],
  "enable":  ["u0012"],
  "trim":    { "u0005": {"in": 12.40, "out": 15.90} },
  "order":   ["u0001", "u0003", "u0002"],
  "notes":   "por que se decidio asi"
}
```

Todo es opcional. `groups` elige la toma buena; `disable`/`enable` fuerzan
frases sueltas; `trim` ajusta tiempos en segundos del archivo original;
`order` reordena la secuencia (solo hace falta si cambia el orden).