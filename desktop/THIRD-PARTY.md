# Dependencias incluidas en Videria

Videria incluye Python, pywebview (BSD-3-Clause), Flask (BSD-3-Clause), NumPy
(BSD-3-Clause), Pillow (MIT-CMU) y sus dependencias. Las licencias de las
distribuciones están en `licenses/python` dentro del paquete.

El reproductor nativo usa Microsoft Edge WebView2 Runtime instalado en Windows.
No se incluye el navegador ni claves, credenciales, modelos de IA o proyectos.

FFmpeg y FFprobe proceden de la distribución Windows de Gyan. Se distribuyen
sin modificaciones. Su licencia GPL v3 y el README de su compilador se incluyen
en `licenses/ffmpeg`. FFmpeg es un proyecto independiente de Videria.

Versión incluida: **8.0.1 full_build**, compatible con NVENC API 13.0.
Paquete de origen: https://github.com/GyanD/codexffmpeg/releases/tag/8.0.1
SHA-256 del ZIP: `467cde100a47ed4b03a897988aeb4a296890c1e2b2d2864204657d002bc5fb90`.
No se instala ni actualiza el controlador NVIDIA.

- Binarios, información de compilación y fuentes: https://www.gyan.dev/ffmpeg/builds/
- Código fuente FFmpeg: https://ffmpeg.org/download.html#get-sources
- Repositorio FFmpeg: https://git.ffmpeg.org/ffmpeg.git
- pywebview: https://github.com/r0x0r/pywebview
- PyInstaller: https://pyinstaller.org/ (excepción que permite distribuir ejecutables)

Las tipografías y stickers conservan sus avisos originales dentro de `skills/video-cut/assets`.
