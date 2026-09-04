# Videria 2.4.1 — portátil y compatible

- La interfaz aprovecha mejor pantallas de portátil y el escalado de Windows.
- El panel de inspección, la biblioteca y la línea de tiempo se compactan de
  forma gradual sin reducir la previsualización vertical a una franja.
- Los proyectos compartidos usan proxies H.264, 8 bits y BT.709 compatibles con
  WebView2. Esto corrige la previsualización negra en equipos sin códec HEVC.
- El cambio de proxy no modifica los originales ni el render final: Hans sigue
  renderizando desde los archivos de cámara y puede conservar el color HDR.

Instalación: descarga `Videria-2.4.1-Windows-x64.zip`, extrae todo y ejecuta
`Instalar-Videria.cmd`. Después pulsa “Recibir cambios” para bajar los proxies
compatibles del repositorio `HansNieto/videos`.
