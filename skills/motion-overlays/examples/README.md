# Ejemplos

## dependencia-del-dueno

Proyecto completo y verificado: seis overlays para un video de ~65 s sobre dependencia del
dueño, delegación y documentación. Estilo **3D suave** (`s-soft3d`).

Sirve como referencia de qué aspecto tiene una entrega correcta: densidad de la
composición, sincronía con las palabras, estructura del SVG (`.at` / `.o`), cambios de
estado por crossfade, contadores, y el `overlays.json` con el manifiesto de montaje.

Los HTML esperan un `lib/` al lado. Para ejecutarlos:

```bash
cd examples/dependencia-del-dueno
mkdir -p lib
cp -r ../../assets/vendor/* lib/
cp ../../assets/overlay.css ../../assets/overlay.js lib/
```

Y abre cualquiera de los `.html` en Chrome. En la consola:

```js
Overlay.duration   // 5.4, 5.88, 4.2, 4.78, 5.88, 5.89
Overlay.audit()    // start=0, end=0, ok=true en los seis
```

`contact-sheet.png` muestra el frame clímax de cada escena.
