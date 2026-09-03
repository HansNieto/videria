# Videria de escritorio

Windows x64, Python 3.13, pywebview + Edge WebView2. Incluye el mismo Studio y
servidor de render, no una segunda implementación. Selector local de proyectos,
instalación por usuario, datos separados, recursos relativos y empaquetado
mediante lista permitida (nunca `.env`, originales ni proyectos).

## Ejecutar desde el código

```powershell
python -m venv .venv-desktop
.venv-desktop\Scripts\python -m pip install -r desktop\requirements.txt
.venv-desktop\Scripts\python desktop\main.py
```

## Compilar una versión

En una venv limpia con las dependencias anteriores:

```powershell
.venv-desktop\Scripts\python -m unittest discover -s tests -v
node tests/player_startup.test.cjs
.venv-desktop\Scripts\python desktop\build.py --ffmpeg-dir "C:\ffmpeg\bin"
dist\Videria\Videria.exe --smoke-test --data-dir "C:\ruta\a\videria\build\smoke"
dist\Videria\Videria.exe --window-test --data-dir "C:\ruta\a\videria\build\native-smoke"
```

`ffmpeg-dir` debe contener FFmpeg/FFprobe; su carpeta padre debe contener
`LICENSE` y `README.txt` de la distribución usada. Se adjuntan sin modificarlos.
Revisar dependencias/licencias antes de cambiar de distribución.

Publicar `dist/Videria-VERSION-Windows-x64.zip` y su `.sha256` como Assets de una
GitHub Release. No subir `dist/`, la venv, datos privados o proyectos al código.
Mantener la misma VERSION en host.py, build.py e Instalar-Videria.ps1.

## Pruebas del navegador

`desktop/main.py --browser-only --port 7799 --data-dir build/qa-settings` sirve
la misma UI. Usar `tests/make_desktop_fixture.py` para crear un proyecto ficticio
en build/qa-project; no guardar ni renderizar pruebas sobre proyectos del usuario.
Probar reproducción, avanzar/retroceder, cortes, capas, deshacer/rehacer,
guardar, render y volver al selector. Probar también `--smoke-test` del EXE.

El instalador no borra versiones anteriores, ediciones ni originales. El EXE
no incorpora transcripción/Whisper, agentes ni APIs de generación: esos pasos
siguen en la máquina de preedición. GitHub Desktop sigue siendo la interfaz
para commit/push y resolución de conflictos; nunca se fuerza un pull ni se
descartan cambios desde el selector.
