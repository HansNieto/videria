# Inventario de iconos para Videria Studio

La interfaz usa botones compactos y muestra el nombre completo con `title` al
poner el mouse encima. Para la versión definitiva conviene usar una sola
familia, preferentemente **Lucide**, con trazo de 1.75 px y tamaño de 18 px.

| Grupo | Acción | Icono Lucide sugerido | Atajo / tooltip |
|---|---|---|---|
| Reproducción | Inicio | `SkipBack` | Ir al inicio · Home |
| Reproducción | Clip anterior | `Rewind` | Clip anterior · , |
| Reproducción | Fotograma anterior | `StepBack` | Retroceder un fotograma · ← |
| Reproducción | Reproducir / pausar | `Play` / `Pause` | Reproducir o pausar · Espacio |
| Reproducción | Fotograma siguiente | `StepForward` | Avanzar un fotograma · → |
| Reproducción | Clip siguiente | `FastForward` | Clip siguiente · . |
| Reproducción | Final | `SkipForward` | Ir al final · End |
| Corte | Recortar izquierda | `PanelLeftClose` | Eliminar hasta el cabezal |
| Corte | Dividir | `Scissors` | Dividir clip · S |
| Corte | Recortar derecha | `PanelRightClose` | Eliminar desde el cabezal |
| Timeline | Ajuste magnético | `Magnet` | Alinear bordes · M |
| Timeline | Agregar capa | `Layers3` + `Plus` | Agregar capa |
| Timeline | Importar | `Upload` | Importar imagen, audio o video |
| Timeline | Subir / bajar capa | `ChevronUp` / `ChevronDown` | Cambiar orden visual |
| Timeline | Ocultar / mostrar | `EyeOff` / `Eye` | Visibilidad de capa |
| Timeline | Bloquear / liberar | `Lock` / `Unlock` | Bloquear edición |
| Historial | Deshacer / rehacer | `Undo2` / `Redo2` | Ctrl+Z / Ctrl+Shift+Z |
| Proyecto | Guardar | `Save` | Guardar · Ctrl+S |
| Proyecto | Render final | `Clapperboard` | Renderizar · Ctrl+R |
| Proyecto | Borrador | `Gauge` | Render rápido · B |
| Herramientas | Seleccionar / mover | `MousePointer2` | Seleccionar · V |
| Herramientas | Reencuadrar | `Scan` | Reencuadrar · Z |
| Capas | Texto | `Type` | Nueva capa de texto |
| Capas | Visual | `Image` | Nueva capa visual |
| Capas | Audio | `AudioLines` | Nueva capa de audio |
| Recursos | Música | `Music2` | Música |
| Recursos | Efectos | `AudioWaveform` | Efectos de sonido |
| Recursos | Stickers | `Sticker` | Stickers con miniatura |
| Recursos | Transición | `BetweenHorizontalStart` | Transiciones |
| Ayuda | Información | `CircleHelp` | Explicación contextual |

## Reglas visuales

- Un botón activo usa el color azul de acento; por ejemplo, el imán encendido.
- Acciones destructivas pasan a rojo solo al apuntarlas o confirmarlas.
- Los iconos no llevan texto fijo en la barra rápida; el texto aparece al pasar
  el mouse y también queda disponible como `aria-label` para accesibilidad.
- Un mismo icono conserva siempre el mismo significado en biblioteca,
  inspector y timeline.
