# Videria 2.5.2 — color correcto en stickers y motion graphics

- Corrige los stickers, PNG transparentes y motion graphics que se veían
  demasiado oscuros al renderizar sobre grabaciones HLG/HDR.
- Los recursos SDR se integran ahora con blanco de gráficos de 203 nits,
  equivalente al nivel de referencia de 75 % en HLG.
- La grabación original permanece sin corrección de color automática y conserva
  HLG, BT.2020 y 10 bits cuando se renderiza en modo Original.
- La corrección funciona tanto con CPU como con NVIDIA NVENC y conserva la
  transparencia de los recursos.

Los MP4 renderizados con una versión anterior no cambian solos: instala esta
versión y vuelve a renderizar el proyecto.

Instalación: descarga `Videria-2.5.2-Windows-x64.zip`, extrae todo y ejecuta
`Instalar-Videria.cmd`.
