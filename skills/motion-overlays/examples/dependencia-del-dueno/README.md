# Motion overlays — dependencia del dueño

Seis overlays animados (HTML + SVG + GSAP) con **fondo transparente**, pensados para
superponerse a la toma del presentador en CapCut. El video ya lleva subtítulos, así que
**ninguno escribe las frases del guion**: solo texto de interfaz (`7 DÍAS`, `LÍMITE`, `S/`, `?`, `%`).

**Estilo visual:** *3D suave* (`s-soft3d`). Estilo de **masa**: los objetos son formas
rellenas con degradado, brillo especular y sombra; no hay contornos ni líneas finas.
Las conexiones son carriles de 12px, no trazos. Para compararlo con los otros seis
estilos, abre `00-estilos.html`.

La versión anterior en *línea mínima* está guardada en **`linea-minima/`** por si quieres
volver a ella: son los mismos archivos con el mismo timeline, solo cambia el dibujo.

Ábrelos con doble clic en Chrome. Se reproducen en bucle con una pausa entre repeticiones.

- `00-estilos.html` → los siete estilos con la misma escena, sobre fondo oscuro o claro.
- `00-preview.html` → galería con las seis escenas a la vez, cambio de fondo y botón de repetir.
- Teclas dentro de un overlay: `espacio` play/pausa · `R` repetir · `H` HUD con el tiempo ·
  `←/→` avance por frame · en consola, `Overlay.audit()` verifica que entra y sale limpio.

## Las escenas

| Archivo | Parte del diálogo | Concepto visual | Duración |
|---------|-------------------|-----------------|----------|
| `01_semana_sin_ti.html` | “¿Qué **pasaría** con tu negocio si mañana no pudieras trabajar durante una **semana**?” | El mostrador sigue; tú no. Los 7 días se apagan uno a uno | 5,40 s |
| `02_cuello_de_botella.html` | “Si nadie **puede** comprar, pagar, resolver un reclamo o tomar una decisión hasta que tú **respondas**…” | Cuatro operaciones viajan a una sola persona y se atascan a mitad de camino | 5,88 s |
| `03_lo_que_llega_hasta_ti.html` | “…llegan innecesariamente hasta **ti**: descuentos pequeños, compras rutinarias, devoluciones o decisiones **operativas**” | Cuatro cosas suben en paralelo a tu bandeja y quedan marcadas | 4,20 s |
| `04_limite_de_autoridad.html` | “…qué puede decidir **cada** persona sin pedir permiso y hasta qué **límite**” | Lo pequeño se resuelve bajo la raya; lo grande la toca y escala al dueño | 4,78 s |
| `05_del_celular_al_repositorio.html` | “…que **las** cuentas, proveedores y archivos necesarios no existan solamente en tu **celular**” | La información sale del teléfono a un repositorio al que entra el equipo | 5,88 s |
| `06_dinero_mezclado.html` ⚠️ | “**Hoy** entran quinientos soles, sacas cien para una compra personal; mañana otros **cincuenta**…” | La caja del negocio alimenta la billetera personal y el saldo deja de significar algo | 5,89 s |

> ⚠️ **La 06 no pertenece al guion de siete frases.** Esa frase venía en el brief como
> ejemplo de sincronía, no en la locución. Está construida con los tiempos de ese ejemplo;
> si en tu guion real la frase es otra, hay que reajustar los `BEATS` a sus palabras.

## Qué ocurre en cada animación

### 01 · Una semana sin ti
Entra el mostrador con el dueño detrás y, debajo, la semana como siete celdas con actividad
verde. En “mañana no pudieras trabajar” el dueño se desvanece y el mostrador acusa el vacío.
Entonces los siete días se apagan **en cascada** —uno detrás de otro, no a la vez— y en el
hueco que dejó la persona aparece un interrogante ámbar mientras `7 DÍAS` cambia de color.
Cierra contrayéndose desde los bordes hacia el centro.

### 02 · Cuello de botella
El dueño se establece como nodo central. Con cada palabra del guion entra una operación
—comprar, pagar, reclamo, decisión—, se abre su carril y un pulso viaja hasta él; el centro
reacciona a cada llegada. En “hasta que tú respondas” los cuatro pulsos salen a la vez, pero
**se detienen antes de llegar**: los carriles pasan a punteado apagado, los pulsos se hinchan en
ámbar, los nodos se atenúan y el centro vibra. Eso es la dependencia, sin escribir la palabra.

### 03 · Lo que llega hasta ti
Arriba, tú y tu bandeja. Con cada palabra sube un objeto por su propio carril: un `%`
(descuento), una caja (compra rutinaria), una flecha de retorno (devolución) y un engranaje
(decisión operativa). Cuando están las cuatro, un aro ámbar las marca con stagger y los carriles
pasan a ámbar: quedan **identificadas** como lo que no debería llegar. Salen por donde
vinieron.

### 04 · Límite de autoridad
El empleado entra y sobre él se traza el `LÍMITE` como barra punteada ámbar. Tres decisiones
pequeñas suben, se quedan **debajo** de la raya y se resuelven en verde una tras otra. Después
sube una decisión grande que **golpea el límite**, rebota —la barra pulsa— y escala en diagonal
hasta el dueño, que aparece arriba para recibirla. La escena cierra con lo resuelto abajo y lo
escalado arriba.

### 05 · Del celular al repositorio
Dentro del teléfono aparecen tres cosas: una contraseña, un proveedor y un archivo. En
“solamente” se cierra un candado ámbar sobre el marco y el teléfono tiembla: todo vive en un
único sitio. Justo cuando el narrador dice “en tu celular”, el candado salta y los tres
elementos **salen en arco** hacia un repositorio, que se enciende en verde; tres miembros del
equipo se conectan por carriles que se abren. Es la única escena que termina en resolución.

### 06 · Dinero mezclado *(fuera del guion de siete frases)*
La caja del negocio con su display en cero y, apagada al lado, la billetera personal. En
“quinientos” cae una moneda por la ranura y el saldo cuenta hasta `S/500`. En “cien” una
moneda sale en arco hacia la billetera, que se enciende; el saldo baja a `S/400`.
Entonces **no pasa nada durante segundo y medio**: es la pausa de “para una compra
personal”, y respetarla es el punto de la escena. En “mañana otros cincuenta” sale la
segunda moneda y el saldo cae a `S/350`. Al final el display parpadea y se queda en
`S/ ?`: el número ya no dice nada.

## Montaje en CapCut

1. Alinea el inicio de cada clip con la **palabra de entrada** de la tabla.
2. El contenido vive en un módulo central: puedes reducirlo al 60–70 % y llevarlo a un lado
   sin que se corte nada.
3. Si el overlay compite con tu cara, abre el HTML y cambia `pos-center` por `pos-left`,
   `pos-right`, `pos-top` o `pos-bottom` en el `<g class="frame …">`. Es una sola palabra.
4. No apliques transiciones de CapCut: la entrada y la salida ya están animadas, y en el
   primer y último frame no hay nada visible.

## Render con transparencia

Los HTML no son video: hay que capturarlos. Dos rutas (detalle en la skill `motion-overlays`,
`references/render-capcut.md`):

```bash
# rápida, con Puppeteer (npm i -D puppeteer)
node capture.mjs 01_semana_sin_ti.html --fps 30
ffmpeg -framerate 30 -i frames/01_semana_sin_ti/%04d.png \
  -c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le 01_semana_sin_ti.mov
```

```bash
# sin instalar nada: Chrome escribe PNG con alfa si le pasas
#   --default-background-color=00000000  y  ?t=<segundo>
```

Si tu versión de CapCut no respeta el alfa del `.mov`, usa `?bg=green` y quita el fondo con
el croma del propio CapCut.

## Frases sin overlay (a propósito)

- **“El objetivo no es desaparecer del negocio…”** — es una idea de intención, sin objeto que
  mostrar. Funciona mejor mirando a cámara.
- **“Haz la prueba: imagina que mañana faltas siete días…”** — el cierre es una pregunta
  directa al espectador, y los 7 días ya se usaron en el overlay 01. Repetir la metáfora
  restaría fuerza al remate.
