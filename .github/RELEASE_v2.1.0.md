# Videria 2.1.0 — app de escritorio

## Instalar en Windows x64

1. Descarga **Videria-2.1.0-Windows-x64.zip** de Assets (no Source code).
2. Extrae todo el ZIP.
3. Doble clic en **Instalar-Videria.cmd**.
4. Abre el icono **Videria** en el Escritorio y selecciona tu proyecto.

Incluye Python, FFmpeg, fuentes y stickers. Requiere Windows 10/11 x64 y
Microsoft Edge WebView2 Runtime. El paquete aún no tiene firma comercial.
Se publica un archivo SHA-256 para comprobar la integridad de la descarga.

## Cambios

- Ventana de aplicación nativa, sin tener que arrancar un servidor a mano.
- Biblioteca de proyectos y selector de carpetas. Detecta las preediciones 17–20 de Hans.
- Descargar/recibir proyectos de GitHub cuando Git está autenticado; GitHub Desktop
  sirve para clonar repositorios privados y publicar las correcciones.
- Corregido el error del compositor que detenía el inicio antes de enlazar botones.
- El divisor de biblioteca ya no intercepta clics en la barra de controles.
- Recursos del timeline portables entre equipos e instalación con datos separados.
- Guardado al regresar al selector; pruebas de regresión en cada cambio de main.

## Tutorial para Hans y MaykNE

Abre **LEEME.html** del ZIP, o **Guía de uso** en la app. Incluye instalación,
videos 17–20, permisos de repos privados, revisión, entrega, render y actualizaciones.

Los repositorios de los videos y sus enlaces **no cambian**. No necesitas regenerar
preediciones. El instalador no modifica originales ni proyectos.

## Alcance y comprobaciones

La aplicación permite abrir, editar y renderizar. La generación de nuevas
preediciones con IA y recursos sigue en el pipeline/skills de la máquina de Hans;
todavía no es un botón dentro de la app. No incluye claves ni modelos de IA.

Verificado en Windows: arranque del EXE, carga nativa WebView2, controles de
reproducción/corte/capas, importación, guardar/reabrir, selector, apertura de
video17 y render ficticio H.264/AAC de 8 segundos a 1080×1920. Se añadieron
7 pruebas Python y 24 casos del compositor JavaScript. No se han probado otras
computadoras ni se han renderizado de nuevo los videos de producción.
