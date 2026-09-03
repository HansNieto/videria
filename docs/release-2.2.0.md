# Videria 2.2.0

## Cambios

- Color: conversión HDR HLG/PQ a SDR Rec.709, compartida por el preview HQ y el render; caché nueva para evitar previsualizaciones antiguas. HQ hasta 1080 × 1920, sin inventar detalle si solo hay proxies.
- Exportar abre opciones de resolución, FPS, calidad H.264, CPU/NVIDIA y audio AAC. Conserva el lienzo del proyecto y numera archivos para no sobrescribir entregas.
- Arrastre libre a izquierda/derecha, huecos sin desplazar el resto y pistas automáticas al soltar sobre otro elemento. Se admiten varios clips de video simultáneos: el de arriba se ve delante y sus audios se mezclan.
- Imán en ambos bordes contra clips, recursos y cabezal. Alt lo desactiva temporalmente. Objetos arrastrados a mano dejan de estar limitados por el ancla de la preedición.
- División conserva velocidad, posición, pista y continuidad del zoom. Subtítulos protegidos contra solapamientos. Deshacer/rehacer y guardar conservan la composición.

## Instalar / actualizar

Guarda y cierra Videria. Descarga `Videria-2.2.0-Windows-x64.zip`, extrae todo y ejecuta `Instalar-Videria.cmd`. Abre el mismo icono y los mismos proyectos. No regeneres la preedición ni vuelvas a clonar.

Hans y MaykNE deben actualizar: versiones anteriores no interpretan las posiciones libres y pistas de video. No reordenes estos proyectos desde el editor clásico de cortes. Consulta `LEEME.html` o la ayuda de la app para el flujo por rol.

La salida es SDR, no HDR/Dolby Vision. Los renders antiguos no se corrigen solos: exporta de nuevo. Los proxies antiguos compartidos tampoco recuperan el HDR; Hans puede regenerarlos desde los originales cuando necesiten revisar color en la otra computadora.

## Verificación

13 pruebas Python; regresiones JavaScript del compositor y modelo de timeline; interacción real en navegador (arrastre izquierdo, capa automática, reproducción, división, deshacer, guardar/reabrir y exportación). Integración FFmpeg: superposición con colores de prueba, huecos, exportación por rango, 720 × 1280 / 60 FPS, y comparación de un mismo fotograma del original HDR en proxy/export. También se renderizó un fragmento del proyecto 17 con sus recursos y subtítulos, en una carpeta de pruebas separada.

## Referencias de diseño

- [Ajuste magnético de Premiere](https://helpx.adobe.com/premiere/desktop/edit-projects/change-clip-sequence/snap-clips.html).
- [Clips conectados y orden de capas en Final Cut Pro](https://support.apple.com/en-asia/guide/final-cut-pro/ver7a77ef9e/mac).
- [FFmpeg: tone mapping en luz lineal](https://ffmpeg.org/ffmpeg-filters.html#tonemap).

Videria adopta esos principios, no pretende reproducir todas las herramientas de CapCut. El texto y los overlays se ordenan dentro de sus grupos sobre las pistas de video.
