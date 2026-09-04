# Movimiento construido por secuencia

Usa este método cuando un gráfico tenga varios actores o explique causa y efecto. El
objetivo no es “meter un sticker con una transición”, sino hacer que la idea exista a
medida que la narración la nombra.

## Contrato

Cada objeto complejo se divide en capas animables:

1. profundidad o sombra;
2. borde o silueta;
3. cara o volumen;
4. símbolo interior;
5. brillo o detalle;
6. conexión con el siguiente actor.

La unidad `.o` sirve para colocación semántica y auditoría. Sus hijos `.piece` son lo que
se anima. En la entrada está prohibido resolver un objeto complejo con un único tween de
`autoAlpha + scale` sobre `.o`.

## Orden narrativo

El orden visual sigue el orden de las palabras:

- cuando se nombra al actor, se construye la persona;
- cuando aparece la duda, nace el globo y después se escribe `?`;
- cuando se habla del precio, se arma la placa y después se escriben `S`, `/`, `.`;
- la conexión se dibuja solo cuando existen sus dos extremos;
- cuando llega el fallo, se construye el aro rojo y la X se dibuja con dos trazos.

Si el guion cambia el orden, cambia el timeline. No fuerces siempre esta secuencia.

## Patrones de construcción

- forma sólida: profundidad → borde → cara → brillo;
- persona: contenedor → cabeza → torso;
- tarjeta: marco desde un borde → superficie → dato por caracteres;
- ruta: trazo de profundidad → trazo principal → punta → pulso viajero;
- error: aro → cara roja → primer trazo → segundo trazo → rayos;
- salida: desarma en orden inverso o retrae la relación; no hagas fade global.

Un tween corto de opacidad sí es válido para una pieza individual, una partícula o un
brillo. Lo inválido es usarlo para esconder que el objeto entero ya estaba terminado.

## Tiempo

Una construcción debe ser rápida y legible:

- capa estructural: 0.22–0.36 s;
- símbolo: 0.18–0.28 s;
- stagger entre caracteres o piezas: 0.06–0.10 s;
- conexión: 0.35–0.55 s;
- impacto: 0.20–0.35 s;
- pausa final: 0.35–0.70 s.

Las fases pueden solaparse 20–35 %. No esperes a que una pieza termine por completo para
iniciar la siguiente: eso hace que la escena se sienta lenta y mecánica.

## QA

Reproduce a 0.5× y verifica:

- se puede nombrar qué capa se está construyendo en cada instante;
- ningún objeto aparece ya terminado;
- la ruta no existe antes que sus extremos;
- el símbolo clave llega exactamente con su palabra;
- el frame final se entiende como una sola composición;
- `t=0` y `t=fin` siguen vacíos.
