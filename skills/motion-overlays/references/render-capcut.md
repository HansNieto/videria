# Render con transparencia y montaje en CapCut

Los overlays son HTML: para llevarlos a CapCut hay que convertirlos en video **con canal
alfa** o, si eso falla, en video sobre croma.

## Ruta A — Secuencia PNG con alfa (la más fiable)

Captura frame a frame con Chrome headless y luego arma el video con ffmpeg.

`assets/capture.mjs` (se copia junto con `lib/`) hace esto con Puppeteer:

```bash
npm i -D puppeteer                 # una sola vez, en la carpeta del proyecto
node capture.mjs 01_dependencia.html --fps 60
# → frames/01_dependencia/0000.png … (tamaño del viewBox, fondo transparente)
```

Funciona porque el script:
1. abre la página con `?paused=1` (el runtime no reproduce solo);
2. lee `Overlay.canvas`, fija el viewport al `viewBox` (1080×1920 en Videria) y usa
   `omitBackground: true` en cada screenshot;
3. hace `Overlay.seek(frame / fps)` y captura, frame a frame — así el resultado es
   determinista y no depende de la velocidad real de reproducción.

Después:

```bash
# WebM VP9 con alfa (ligero, ideal para web y para editores que lo soporten)
ffmpeg -framerate 60 -i frames/01_dependencia/%04d.png \
  -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 24 -auto-alt-ref 0 \
  01_dependencia.webm

# MOV ProRes 4444 con alfa (máxima compatibilidad con editores de escritorio)
ffmpeg -framerate 60 -i frames/01_dependencia/%04d.png \
  -c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le -alpha_bits 8 \
  01_dependencia.mov
```

Cuál importar en CapCut: prueba primero el **MOV ProRes 4444**. El soporte de alfa varía
entre versiones de CapCut (y entre CapCut PC y móvil), así que verifica en el propio
editor que el fondo se ve transparente antes de montar todo. Si no lo respeta, usa la ruta B.

## Ruta A-bis — Chrome headless sin instalar nada (probada)

Si no quieres tocar npm, Chrome captura PNG con alfa por sí solo. La clave es
`--default-background-color=00000000`:

```bash
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
BASE="file:///C:/ruta/al/proyecto/motion-overlays"
FPS=30; DUR=5.2; N=$(python -c "print(int($DUR*$FPS)+1)" 2>/dev/null || echo 157)
mkdir -p frames/01
for i in $(seq 0 $((N-1))); do
  T=$(awk "BEGIN{printf \"%.4f\", $i/$FPS}")
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
    --default-background-color=00000000 --window-size=1080,1920 \
    --virtual-time-budget=4000 \
    --screenshot="$PWD/frames/01/$(printf %04d $i).png" \
    "$BASE/01_dependencia.html?t=$T" >/dev/null 2>&1
done
```

Lanza un Chrome por frame, así que es lento (~0.6 s/frame: unos 90 s para 5 s a 30 fps).
Para tandas grandes usa la ruta A con Puppeteer, que reutiliza la misma pestaña.

Comprobar que un frame es realmente transparente:

```bash
ffprobe -v error -f lavfi -i "movie=frames/01/0000.png,alphaextract,signalstats" \
  -show_entries frame_tags=lavfi.signalstats.YMAX -of csv=p=0
# 0   = frame completamente transparente (correcto en el primer y último frame)
# 255 = hay contenido opaco
```

## Ruta B — Croma (funciona siempre)

Renderiza sobre un color plano y quita el fondo con el efecto de croma de CapCut.

```bash
node capture.mjs 01_dependencia.html --fps 60 --bg green   # #00E000, sin alfa
ffmpeg -framerate 60 -i frames/01_dependencia/%04d.png -c:v libx264 \
  -pix_fmt yuv420p -crf 16 01_dependencia_green.mp4
```

El runtime acepta `?bg=green` (verde croma) y `?bg=magenta`. Usa **magenta** si la escena
tiene elementos verdes (`--ok`), y verde si tiene rojos/dorados.

En CapCut: capa superior → *Eliminar fondo / Chroma key* → cuentagotas sobre el fondo →
ajusta *Intensidad* y *Sombra* hasta que los bordes queden limpios.

> El croma come un poco los bordes suaves y las sombras. Si la escena depende de
> `drop-shadow`, prioriza la ruta A.

## Ruta C — Grabación de pantalla (rápido y sucio)

Abrir el HTML en Chrome a pantalla completa (F11, ventana con la relación del proyecto) y grabar con
OBS/CapCut. Sin alfa: solo sirve con la ruta de croma o si el overlay va sobre fondo sólido.
El timing depende de la reproducción real, así que revisa que no se caigan frames.

## Ajustes útiles del runtime al capturar

| Parámetro | Efecto |
|-----------|--------|
| `?paused=1` | no reproduce; queda listo para `Overlay.seek(t)` |
| `?t=2.4` | salta a ese segundo y se queda ahí (útil para revisar un frame) |
| `?loop=0` | reproduce una sola vez |
| `?bg=green\|magenta\|dark\|light\|photo\|checker` | fondo de revisión o de croma |
| `Overlay.duration` | duración exacta del timeline, en segundos |
| `Overlay.canvas` | ancho, alto y orientación leídos del `viewBox` |
| `Overlay.audit()` | lista los elementos visibles en t=0 y t=fin (debe dar 0) |

## Montaje en CapCut

1. Pista de video principal: la toma del presentador.
2. Pista superior: el overlay (`.mov` con alfa o el `.mp4` verde + croma).
3. Alinea el inicio del clip con la **palabra de entrada** indicada en el README.
4. En Videria vertical, conserva el overlay a escala 100 %: ya está compuesto para
   1080×1920 y para la zona libre del presentador. Reposiciona solo si cambió el encuadre.
5. Si el overlay compite con el rostro, usa la variante `.pos-left` / `.pos-right`
   del propio HTML en lugar de recortar en CapCut (se conserva la resolución).
6. No apliques transiciones de CapCut al overlay: la entrada y la salida ya están animadas.

## Checklist antes de exportar

- [ ] El PNG 0000 es completamente transparente (nada visible en t=0).
- [ ] El último PNG también.
- [ ] 60 fps si hay movimiento rápido; 30 fps basta para escenas lentas y pesa la mitad.
- [ ] El `.mov`/`.webm` conserva el alfa (ábrelo en el editor antes de hacer los demás).
- [ ] La duración del clip coincide con `Overlay.duration`.
