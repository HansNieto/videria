# Videria 2.1.1 — escritorio y proyectos portables

Incluye la app de escritorio y las correcciones de botones de 2.1.0, más una
corrección de rutas cortas de Windows detectada por las pruebas en GitHub.

## Instalar (Hans y MaykNE)

1. Descarga **Videria-2.1.1-Windows-x64.zip** de Assets, no Source code.
2. Extrae todo el ZIP y ejecuta **Instalar-Videria.cmd**.
3. Abre **Videria** desde su icono del Escritorio y elige el proyecto.

La app incluye Python, FFmpeg, fuentes y stickers. Requiere Windows 10/11 x64
y Microsoft Edge WebView2 Runtime. Ejecutable sin firma comercial; se adjunta
SHA-256 para verificar la descarga.

La instalación no mueve ni reemplaza proyectos u originales. Las preediciones
17–20 se abren desde sus mismas carpetas. El código de la app se actualiza por
Releases; GitHub Desktop sirve para publicar las revisiones de los proyectos.

**Guía de uso** en la app y **LEEME.html** en el ZIP explican instalación,
repositorios privados, revisión creativa, entrega, render y actualizaciones.

La generación de nuevas preediciones con IA sigue en el pipeline/skills de Hans;
todavía no se inicia desde un botón de la app. No incluye claves ni modelos IA.

Comprobaciones: 8 pruebas Python, 24 casos del compositor JavaScript, controles
en navegador, arranque nativo WebView2 y render de prueba H.264/AAC de 8 segundos
a 1080×1920. No se alteraron las ediciones de producción.
