# Lenguaje de movimiento

Lo que separa un motion graphic de "HTML que hace fade" es la coreografía: qué se mueve,
en qué orden, con qué peso y qué se queda quieto.

## 1. Escala de duraciones

| Token | Segundos | Uso |
|-------|----------|-----|
| `xs` | 0.18 | micro-reacciones, pulsos, cambios de estado de color |
| `s`  | 0.32 | salidas, elementos de apoyo, etiquetas |
| `m`  | 0.50 | entrada estándar de un objeto |
| `l`  | 0.80 | movimientos macro, traslados largos, reorganizaciones |
| `xl` | 1.10 | solo el gesto principal de la escena, una vez |

Regla: **la salida siempre es más rápida que la entrada** (≈ 60–70% de su duración).

## 2. Eases

```js
// registrados por lib/overlay.js
CustomEase.create("brand",  "M0,0 C0.16,1 0.3,1 1,1");   // entrada decidida, frena suave
CustomEase.create("swift",  "M0,0 C0.55,0 0.68,0.2 1,1"); // salida que acelera
CustomEase.create("settle", "M0,0 C0.2,0 0,1.06 1,1");    // overshoot ~6%, imperceptible
```

| Situación | Ease |
|-----------|------|
| Entrada de objeto | `brand` o `power3.out` |
| Salida | `swift` o `power2.in` |
| Traslado de A a B | `power2.inOut` |
| Aterrizaje con peso | `settle` o `back.out(1.3)` |
| Contador numérico | `power1.out` (o `none` si es una cuenta larga) |
| Trazo que se dibuja | `power2.inOut` |
| Colapso / caída | `power2.in` + rotación mínima (2–4°) |
| Estado de error | `none` en 0.1 + micro-shake, no elástico |

Prohibido: `elastic`, `bounce`, `back` > 1.6. Se leen como plantilla, no como diseño.

## 3. Los cuatro principios que más rinden aquí

**Anticipación.** Antes del gesto principal, 4–8px en dirección contraria durante ~0.12s.

```js
tl.to(el, { y: 8,   duration: .12, ease: "power2.in" })
  .to(el, { y: -60, duration: .5,  ease: "brand" });
```

**Stagger con intención.** 0.06–0.10 entre hermanos. `from:"start"` para lectura,
`from:"center"` para expansión, `from:"edges"` para cierre. Nunca `from:"random"` salvo
que la idea sea desorden.

**Movimiento secundario.** Nada llega solo: la etiqueta entra 0.08s después del objeto;
la línea de conexión se dibuja mientras el nodo aún está asentando; una sombra o un
resplandor acompaña con 0.05s de retraso.

**Continuidad.** Si un objeto sale por la derecha, el siguiente entra desde la izquierda.
Si un valor "viaja", debe verse el trayecto (usa `motionPath` o un tween de x/y), no
desaparecer y reaparecer.

## 4. Estructura obligatoria de cada overlay

```
[ENTRADA 0.4–0.8s]  →  [DESARROLLO 1.5–4s]  →  [SALIDA 0.3–0.6s]
     el sistema           ocurre la idea:         se retira con
     se establece         cambio, conflicto       intención
                          o resolución
```

- En `t=0` no hay nada visible. En `t=fin` tampoco.
- El **momento principal** (el frame que resume la idea) debe caer entre el 55% y el 75%
  del timeline, y sostenerse al menos 0.5s sin que nada más se mueva.
- Los "huecos" son diseño: si el narrador tarda 0.8s en llegar al siguiente concepto,
  el timeline espera 0.8s. Un `tl.to({}, {duration: .8})` explícito es válido y legible.

## 5. Coreografía: quién se mueve y cuándo

- **Un foco a la vez.** Cuando entra el elemento clave, todo lo demás está quieto o
  atenuado (`opacity: .35`, `scale: .98`).
- **Atenuar en vez de esconder.** Bajar a `.3` mantiene el contexto; ocultar rompe la
  continuidad.
- Máximo 2 grupos moviéndose simultáneamente, y con roles distintos (uno actúa, otro reacciona).
- El movimiento de reacción llega 0.1–0.2s después de la causa. Ese retraso es lo que
  hace que se lea como causa-efecto.

## 6. Recetas por tipo de escena

### Contador / cifra que cambia
```js
const v = { n: 0 };
tl.to(v, { n: 500, duration: .9, ease: "power2.out",
           onUpdate: () => el.textContent = "S/" + Math.round(v.n) }, "cash")
  .from(el, { yPercent: 30, autoAlpha: 0, duration: .4, ease: "brand" }, "cash")
  .to(chip, { scale: 1.06, duration: .16, yoyo: true, repeat: 1, ease: "power2.out" }, "cash+=.85");
```
La cifra se asienta y el contenedor "acusa el golpe" al final: eso da peso.

### Cambio de estado en estilos de masa

Los rellenos con degradado **no se pueden interpolar**. Un objeto que pasa de un estado a
otro se resuelve con dos formas superpuestas y un crossfade (ver `pitfalls.md` §6):

```svg
<circle class="solid accent" r="70"/>
<circle class="solid warn hubAlert" r="70"/>
```
```js
gsap.set('.hubAlert', { autoAlpha: 0 });
tl.to('.hubAlert', { autoAlpha: 1, duration: .35 }, BEATS.block);
```

Los indicadores pequeños (aros, barras, puntos, checks) van en color plano: ahí sí puedes
animar `fill`/`stroke` directamente.

### Dinero que sale de un contenedor
Moneda/billete con `motionPath` en arco (nunca línea recta), rotación de 6–10° durante el
vuelo, `scale` 1 → .9 al alejarse, y el contenedor reaccionando con un `scaleY: .97` breve.
Al llegar al destino, el destino hace un micro `settle`.

### Flujo / conexión entre nodos
1. Los nodos entran con stagger desde el centro.
2. Las líneas se dibujan con `drawSVG: "0% 0%" → "0% 100%"` (0.4s, `power2.inOut`).
3. Un pulso viaja por la línea: un círculo pequeño con `motionPath` sobre el mismo path,
   `opacity` en `fromTo` para que aparezca y muera en el trayecto.
4. Para bloquear: la línea pasa a `--line-3` + `stroke-dasharray` y el pulso se detiene
   a mitad de camino y desaparece.

### Acumulación / saturación
Repite el mismo elemento con `stagger: {each: .07, from: "start"}` y reduce el intervalo
progresivamente (`gsap.utils.interpolate`) para que se sienta que se descontrola. Al final,
un micro-shake del contenedor (`x: "+=3"` yoyo 2 veces, 0.06s).

### Límite / umbral
Una línea horizontal punteada (`LÍMITE`). Objetos pequeños la cruzan y se resuelven con
`--ok`. Un objeto grande la toca, rebota (`y` con `power2.out` corto de vuelta) y escala
hacia arriba con una curva.

### Antes / después
No usar un wipe. Transformar: el mismo objeto cambia de forma con `morphSVG`, o el grupo
se reorganiza con posiciones nuevas y `power2.inOut` de 0.7s. La transformación es la idea.

### Fallo en cascada
Los nodos fallan **uno tras otro** con 0.12–0.18s de separación, no a la vez. Cada uno:
color a `--bad` en 0.1s + `scale: .94` + una micro caída de 3px. El último falla y todo
se queda quieto medio segundo antes de la salida.

### Documento / archivo que se organiza
Los ítems salen de un contenedor con arco y llegan a una rejilla ordenada. Entre el caos
y el orden, un instante de suspensión: todos flotando 0.25s antes de encajar con stagger
`from:"center"`.

## 7. Salidas con intención

| La escena termina en… | Salida |
|-----------------------|--------|
| resolución / orden | contracción al centro, `scale: .96`, `autoAlpha: 0`, stagger `from:"edges"` |
| fallo / bloqueo | caída de 12–20px con `power2.in`, opacidad a 0, todo casi a la vez |
| continuidad (hay más que decir) | desplazamiento lateral con `power2.in`, como si pasara de largo |
| acumulación | todo se comprime hacia el elemento saturado y desaparece |

Nunca `tl.reverse()` como salida: leerlo hacia atrás se nota y desaprovecha el remate.

## 8. Loop limpio

El runtime repite con `repeatDelay` (por defecto 0.8s). Para que no salte:

- todo empieza invisible y termina invisible;
- ningún tween deja `transform` residual que el siguiente ciclo no vuelva a fijar
  (usa `fromTo` o `gsap.set` inicial en `build()`);
- nada depende del estado del ciclo anterior (nada de `"+="` sobre valores acumulables
  sin un `set` de arranque).

## 9. Rendimiento

- Solo `transform` y `opacity` (`autoAlpha` para ocultar de verdad).
- Un timeline por escena, con `defaults: { duration: .5, ease: "brand" }`.
- `stagger` en lugar de N tweens con `delay`.
- `will-change: transform` solo en los grupos que realmente se mueven.
- Filtros (`drop-shadow`) en el grupo contenedor, no en cada path.
