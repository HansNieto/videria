# Revision de cortes: video18-proyecto

- Material bruto: **00:02:54** en 16 archivo(s)
- Propuesta automatica: **00:01:12** (58.7% eliminado)
- Frases: 24 totales, 17 encendidas, 3 grupos de tomas repetidas

## Notas de la revision anterior

Revisión manual: se retiraron una repetición sobre las confusiones y una toma repetida sobre anticiparse.

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


*-- IMG_0135.MOV --*

- `u0001` Estas son algunas señales de que tu negocio está creciendo de forma descontrolada.

*-- IMG_0136.MOV --*

- `u0002` Una señal aparece cuando
- `u0003` las ventas aumentan, pero casi todas las decisiones dependen de ti.

*-- IMG_0139.MOV --*

- `u0007` El negocio está creciendo, pero su forma de vender no, y eso termina generando retrasos. `[g001 toma 4/4]`

*-- IMG_0140.MOV --*

- `u0008` Con más clientes también aumenta la información.

*-- IMG_0141.MOV --*

- `u0009` Cuando esta termina repartida entre archivos, conversaciones y distintas personas

*-- IMG_0142.MOV --*

- `u0011` empiezan las confusiones, nadie sabe dónde está el dato dónde lo guardaron y empiezan las confusiones y los retrasos

*-- IMG_0143.MOV --*

- `u0012` Otra señal es que casi todo se resuelve con urgencia.

*-- IMG_0146.MOV --*

- `u0015` El equipo deja de anticiparse y pasa el día reaccionando a pedidos olvidados, `[g002 toma 2/2]`
- `u0016` errores o problemas que pudieron prevenirse.

*-- IMG_0147.MOV --*

- `u0017` Esto
- `u0018` ocurre
- `u0019` porque aumentó el trabajo, pero los procesos, trabajadores y las herramientas no crecieron al mismo ritmo.

*-- IMG_0148.MOV --*

- `u0020` Crecer con orden significa definir quien se encarga de cada tarea.

*-- IMG_0149.MOV --*

- `u0022` centralizar la información y definir una forma clara `[g003 toma 2/2]`
- `u0023` de trabajar antes de seguir aumentando las operaciones

*-- IMG_0150.MOV --*

- `u0024` guarda este vídeo y revisa cual de estas señales ya está apareciendo en tu negocio

## Grupos de tomas repetidas

### g001 -- 4 tomas (elegida ahora: `u0007`, por auto:last)

| toma | id | archivo @ tiempo | conf | score | texto |
|---|---|---|---|---|---|
| 1 | `u0004` | IMG_0137.MOV @ 00:00:00.00 | 0.96 | 0.98 | El negocio está creciendo, pero su forma de trabajar no, y eso aumenta los retrasos. |
| 2 | `u0005` | IMG_0138.MOV @ 00:00:00.00 | 0.78 | 0.62 | El negocio está creciendo, |
| 3 | `u0006` | IMG_0138.MOV @ 00:00:06.35 | 0.93 | 0.97 | el negocio está creciendo pero su forma de trabajar no y eso genera, el negocio está creciendo pero su forma de trabajar no y eso está empezando a crear retrasos. |
| 4 | `u0007` **<-** | IMG_0139.MOV @ 00:00:00.00 | 0.96 | 0.98 | El negocio está creciendo, pero su forma de vender no, y eso termina generando retrasos. |

### g002 -- 2 tomas (elegida ahora: `u0015`, por auto:last)

| toma | id | archivo @ tiempo | conf | score | texto |
|---|---|---|---|---|---|
| 1 | `u0014` | IMG_0145.MOV @ 00:00:00.83 | 0.91 | 0.97 | El equipo deja de anticiparse y pasa el día reaccionando a pedidos olvidados. |
| 2 | `u0015` **<-** | IMG_0146.MOV @ 00:00:00.42 | 0.93 | 0.97 | El equipo deja de anticiparse y pasa el día reaccionando a pedidos olvidados, |

### g003 -- 2 tomas (elegida ahora: `u0022`, por auto:last)

| toma | id | archivo @ tiempo | conf | score | texto |
|---|---|---|---|---|---|
| 1 | `u0021` | IMG_0149.MOV @ 00:00:00.00 | 0.95 | 0.83 | centralizar la información y definir una forma clara |
| 2 | `u0022` **<-** | IMG_0149.MOV @ 00:00:09.45 | 0.95 | 0.83 | centralizar la información y definir una forma clara |

## Apagadas por muletilla / ruido

- `u0010` (apagada por revision) empiezan las confusiones, nadie sabe cuál es el dato o la tarea
- `u0013` (apagada por revision) El equipo deja de anticiparse, el equipo deja de anticiparse y pasa todo el día respondiendo ventas que no han sido atendidas.

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