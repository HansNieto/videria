# Del guion al beat sheet

## 1. Marcado del guion

Lee el guion completo y anota, frase por frase, qué tipo de contenido es:

| Marca | Significado | ¿Overlay? |
|-------|-------------|-----------|
| `NUM` | cantidad, dinero, porcentaje, plazo | sí, casi siempre |
| `FLUJO` | algo va de A a B, alguien pide a alguien | sí |
| `ESTRUCT` | jerarquía, límite, sistema, dependencia | sí |
| `LISTA` | enumeración de 3–4 cosas concretas | sí, si son concretas |
| `CAMBIO` | antes/después, con/sin, problema→solución | sí |
| `TIEMPO` | días, semanas, rutina, calendario | sí |
| `ABS` | idea abstracta sin objeto | no |
| `META` | saludo, transición, CTA, opinión | no |

Densidad: **1 overlay cada 12–20 s**. Si dos frases seguidas piden overlay, elige la más
visual y deja la otra al presentador. Dos overlays consecutivos sin aire cansan.

## 2. Beat sheet (6 líneas por overlay, antes de tocar código)

```
CONCEPTO:  qué idea exacta tiene que entender el espectador
METÁFORA:  con qué objeto/relación se ve esa idea (una frase)
ENTRA:     qué aparece primero y establece el sistema
DESARROLLO:qué cambia, qué se acumula, qué se rompe
CLÍMAX:    el frame que resume todo (55–75% del timeline)
SALE:      cómo se retira, coherente con el final de la idea
```

Si "METÁFORA" no cabe en una frase, el concepto está mal recortado: divídelo o descártalo.

## 3. Sincronía con la narración

**Ritmo base: 2.6 palabras/segundo** (español explicativo, tono conversacional).
Ajusta a 2.9 si el locutor va rápido, a 2.2 si es pausado.

```
segundos_entre_beats = palabras_entre_anclas / 2.6
```

Procedimiento:

1. Elige la **palabra ancla de entrada**: la palabra exacta donde el overlay debe empezar
   a aparecer. Normalmente 1–2 palabras **antes** del concepto, para que el gráfico llegue
   junto con la idea, no después.
2. Elige la **palabra ancla de salida**: donde la idea deja de estar en el aire.
3. Para cada beat interno, cuenta las palabras desde el ancla de entrada.

Ejemplo real:

> "Hoy entran **quinientos** soles, sacas **cien** para una compra personal; mañana otros
> **cincuenta**…"

| Beat | Palabra ancla | Palabras desde el inicio | t |
|------|---------------|--------------------------|---|
| entrada del sistema | "Hoy" | 0 | 0.00 |
| `+S/500` | "quinientos" | 2 | 0.77 |
| `-S/100` | "cien" | 5 | 1.92 |
| **hueco** | "para una compra personal" | — | 1.92 → 3.10 (nada nuevo) |
| `-S/50` | "cincuenta" | 9 | 3.46 |
| pérdida de claridad | (final de frase) | — | 4.30 |
| salida | — | — | 5.00 |

La pausa entre `-100` y `-50` **no se rellena**. Como mucho, un movimiento residual muy
sutil (la cifra asentando, una moneda terminando su arco). Ese vacío es lo que hace que
la animación se sienta editada y no automática.

Escríbelo como constante al inicio del archivo:

```js
const BEATS = {
  in:   0.00,   // "Hoy entran"
  in500:0.77,   // "quinientos"
  out1: 1.92,   // "cien"
  // 1.92–3.10 hueco: "para una compra personal"
  out2: 3.46,   // "cincuenta"
  blur: 4.30,
  exit: 5.00
};
```

Y úsalo como parámetro de posición del timeline: `tl.to(x, {...}, BEATS.out1)`.

## 4. Margen de entrada

El overlay debe estar **completamente formado** cuando el narrador termina de decir el
concepto. Como la entrada dura 0.4–0.8 s, arranca ese margen antes:

```
inicio_overlay = tiempo_de_la_palabra_clave − duración_de_entrada
```

En la práctica: **entra 1 o 2 palabras antes** de la palabra clave.

## 5. Salida

Sale cuando la idea deja de sostener la frase, no cuando termina la oración. Si el
narrador ya pasó al siguiente concepto y el overlay sigue en pantalla, llega tarde.
Cola máxima recomendada tras la última palabra relevante: **0.6 s**.

## 6. Tabla de entrega

Para cada overlay, registra estos campos (van al README y a la respuesta final):

| Campo | Ejemplo |
|-------|---------|
| Archivo | `03_flujo_dinero.html` |
| Frase del guion | "Hoy entran quinientos soles, sacas cien…" |
| Palabra de entrada | **"Hoy"** |
| Palabra de salida | **"cincuenta"** (+0.6 s de cola) |
| Concepto visual | caja del negocio → billetera personal; el saldo pierde precisión |
| Duración | 5.0 s |
| Posición sugerida | tercio izquierdo (`.pos-left`), presentador a la derecha |

## 7. Errores frecuentes de sincronía

- Meter todos los datos de una frase larga al mismo tiempo (mata la narración).
- Empezar exactamente en la palabra clave: se ve tarde, porque la entrada tarda medio segundo.
- Dejar el overlay hasta el final del párrafo "por si acaso".
- Rellenar las pausas con movimiento decorativo.
- Animar a la misma velocidad frases que el locutor dice con ritmos distintos.
