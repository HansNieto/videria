# Neón editorial premium para video vertical

Esta referencia define el nivel mínimo de acabado de `s-neon`. No es “poner glow” sobre
un icono: es construir una explicación visual breve, con profundidad, jerarquía y una
relación que se revela mediante movimiento.

Las reglas de **composición vertical, cantidad de nodos, zona libre y salida con alfa**
también aplican a `s-sticker3d`. Para ese pack, sustituye las capas de aura/vidrio por
profundidad/borde/cara y sigue `constructed-motion.md`; no copies la paleta neón.

## Composición en 1080×1920

Antes de dibujar, toma un frame representativo del clip y marca tres zonas:

1. **ocupada:** cara, cuerpo y manos del presentador;
2. **reservada:** subtítulos y zona segura de la plataforma;
3. **disponible:** donde puede vivir el motion graphic.

En el formato habitual de Videria, el presentador está en el centro inferior. El módulo
debe ocupar aproximadamente `x=60…1020`, `y=120…820`: grande, pero sin tocar la cara ni
competir con el subtítulo. Si el encuadre cambia, cambia también la composición; no
reutilices coordenadas a ciegas.

## Anatomía de una escena

Una idea relacional usa **3–5 nodos**:

- actor o entrada;
- objeto de decisión;
- estado, condición o pregunta;
- consecuencia o salida.

Los nodos forman un conjunto compacto. Conéctalos con curvas Bézier cortas, flechas
claras y, solo donde ayude, una partícula que recorra la ruta. En el clímax debe poder
entenderse la dirección de la historia en un solo vistazo.

Ejemplos de estructuras válidas:

- solicitud → cliente → precio → rechazo;
- dato → decisión → acción → resultado;
- problema → proceso → bloqueo → alternativa;
- entrada → transformación → salida.

La estructura se adapta al guion; no se usa siempre el mismo teléfono ni el mismo ciclo.

## Capas visuales

Cada nodo importante se construye con estas capas, de atrás hacia delante:

1. **aura:** radial muy suave, transparente en el borde;
2. **superficie local:** panel azul noche al 55–65 %, nunca una caja que tape el cuadro;
3. **borde de luz:** cian, azul, blanco o rojo semántico;
4. **frente nítido:** el símbolo que debe seguir leyéndose sin glow;
5. **detalle breve:** una cifra, `?`, `S/`, tres líneas de UI; nunca una frase del guion.

El filtro no sustituye el dibujo. Si se quita el glow y el símbolo deja de entenderse,
falta contraste o estructura.

## Paleta

- blanco frío: estructura y símbolos;
- cian `#36DEFF`: circulación, información y conexiones;
- azul `#347BFF`: actor o decisión principal;
- rojo `#FF4353`: fallo o rechazo, solo cuando el significado lo exige;
- azul noche translúcido: superficie local.

No uses rojo como decoración. No agregues arcoíris ni ilumines todos los elementos con
la misma intensidad.

## Movimiento

La secuencia recomendada es:

1. aparece el primer nodo con escala corta y aterrizaje;
2. se dibuja la ruta hacia el siguiente actor;
3. aparece el actor o decisión;
4. una partícula confirma la dirección;
5. entra la consecuencia y recibe un único acento;
6. breve pausa para leer;
7. salida limpia, más rápida que la entrada.

Las líneas punteadas pueden animar `strokeDashoffset`; no uses `drawSVG` sobre un trazo
discontinuo porque puede fragmentarse. El glow no parpadea. Una “respiración” de escala
entre 1 y 1.06 en el foco es suficiente.

## Lista de rechazo

Rehaz la escena si ocurre cualquiera de estos casos:

- un icono ocupa casi todo y los demás parecen adornos;
- hay una línea recta larga que no explica ninguna relación;
- el conjunto vive en una esquina y deja vacío más del 70 % de la zona disponible;
- todos los elementos tienen el mismo tamaño, color y animación;
- se usó una captura del video como fondo del propio overlay;
- el PNG/WebM pierde el canal alfa;
- el resplandor está recortado por el `filter` o por el borde del `viewBox`;
- el gráfico tapa cara, manos o subtítulos.

## Salida

HTML + SVG inline + GSAP es el formato editable preferido. La entrega para montaje puede
ser PNG secuencial, ProRes 4444 o WebM con alfa. El formato es secundario; son obligatorios
la animación, el fondo transparente, la nitidez del frente y la composición aprobada.
