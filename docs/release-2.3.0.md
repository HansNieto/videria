# Videria 2.3.0 — color original y GPU

- Color original por defecto: sin Hable ni conversión automática a SDR. HLG/PQ y BT.2020 se conservan en HEVC de 10 bits. SDR compatible es una elección explícita.
- Vista Original mediante vídeo nativo, sin copiar la cámara al canvas SDR. Indicador de proxy cuando no hay originales.
- Barras de color con valores numéricos, interruptor para desactivar sin perder ajustes, restablecer y deshacer. Saturación cero funciona.
- GPU NVIDIA automática mediante prueba real del codificador. FFmpeg 8.0.1 evita la incompatibilidad del motor 9.0.1 (NVENC API 13.1) con el driver 595.79 (API 13.0).
- La ventana de exportación y su progreso identifican CPU/GPU. Los efectos y subtítulos pueden seguir usando CPU.
- Se conservan proyectos, originales, ajustes anteriores y versiones instaladas. No se alteran controladores ni credenciales. La línea de tiempo no cambia.

Pruebas en RTX 4060 Laptop: 4 s HLG 1080×1920/30, calidad 18, sin efectos: CPU 3,87 s; NVENC 1,59 s (~2,4×). Diferencia media de muestras YUV de 10 bits contra cámara: CPU 2,65/1023; GPU 2,37/1023. Son codificaciones con pérdida, no copias bit a bit ni un benchmark universal. Se verificó la negociación de formatos con zoom, transparencia, efectos y ASS sin reducir la cámara a 8 bits.

La reproducción HDR depende del equipo. La salida conserva la base HLG/PQ, no los metadatos dinámicos Dolby Vision del original. Los proxies SDR antiguos no recuperan HDR al actualizar. Ajustes manuales y efectos elegidos sí modifican la imagen. Reexportar para obtener un archivo nuevo; los MP4 antiguos no se reemplazan.

Instalación: descarga el ZIP de esta versión, extrae y ejecuta `Instalar-Videria.cmd` con la app cerrada. Abre Videria desde su icono; elige tu proyecto y Renderizar → Color original → Automático.
