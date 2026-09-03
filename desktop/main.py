"""Entry point for source launches and the frozen Windows application."""
from __future__ import annotations

import argparse
import logging
import multiprocessing
import os
from pathlib import Path
import sys
import threading

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(ROOT / "skills/video-cut/scripts"))
sys.path.insert(0, str(ROOT / "desktop"))


def configure_ffmpeg():
    if all(os.environ.get(k) and Path(os.environ[k]).is_file()
           for k in ("VCUT_FFMPEG", "VCUT_FFPROBE")):
        return
    bins = [ROOT / "tools"]
    installed = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages"
    if installed.is_dir():
        bins += [p.parent for p in installed.glob("Gyan.FFmpeg*/**/ffmpeg.exe")]
    for folder in bins:
        if (folder / "ffmpeg.exe").is_file():
            os.environ["VCUT_FFMPEG"] = str(folder / "ffmpeg.exe")
            os.environ["VCUT_FFPROBE"] = str(folder / "ffprobe.exe")
            break


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--data-dir")
    args.add_argument("--projects-root", action="append", default=[])
    args.add_argument("--browser-only", action="store_true", help="Servidor local para pruebas, sin ventana")
    args.add_argument("--port", type=int, default=0)
    args.add_argument("--smoke-test", action="store_true", help="Verifica el binario sin mostrar ventanas")
    args.add_argument("--window-test", action="store_true", help="Abre WebView2 oculto y comprueba la carga inicial")
    options = args.parse_args()
    data = Path(options.data_dir or Path(os.environ.get("LOCALAPPDATA", Path.home())) / "VideriaData")
    data.mkdir(parents=True, exist_ok=True)
    log = open(data / "app.log", "a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
        sys.stdout = log
    if sys.stderr is None:
        sys.stderr = log
    configure_ffmpeg()
    from host import DesktopHost
    from vcutlib import util
    roots = [ROOT / "videos", Path.home() / "Documents/videria2.0/videria/videos",
             Path.home() / "Documents/Videria/Proyectos", *options.projects_root]
    app = DesktopHost(data, ROOT / "desktop/ui", roots=roots, port=options.port)
    if options.smoke_test:
        response = app.app.test_client().get('/desktop/projects', base_url=app.url)
        assert response.status_code == 200
        assert (ROOT / 'skills/video-cut/studio/js/player.js').is_file()
        assert (ROOT / 'skills/video-cut/assets/fonts/Inter-Black.ttf').is_file()
        util.run([util.FFMPEG, "-version"])
        # También verifica que la integración nativa esté realmente empaquetada.
        import webview
        import webview.platforms.edgechromium
        (data / "smoke-test.ok").write_text("Videria: host, UI, fuentes, WebView2 y FFmpeg OK", encoding="utf-8")
        app.http.server_close()
        return
    app.start()
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    if options.browser_only:
        print(app.url, flush=True)
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
        finally:
            app.stop()
        return
    import webview
    webview.settings['ALLOW_FILE_URLS'] = False
    webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = True
    window = webview.create_window("Videria", app.url, width=1500, height=960,
                                   min_size=(1100, 700), background_color="#0b0d12",
                                   text_select=True, confirm_close=not options.window_test,
                                   hidden=options.window_test)

    def verify_window():
        if window.events.loaded.wait(25):
            (data / "window-test.ok").write_text("WebView2 cargó la ventana de Videria", encoding="utf-8")
        window.destroy()

    def pick_folder():
        result = window.create_file_dialog(webview.FileDialog.FOLDER)
        return result[0] if result else None

    app.pick_folder = pick_folder
    try:
        webview.start(func=verify_window if options.window_test else None,
                      gui="edgechromium", private_mode=False, storage_path=str(data / "webview"),
                      icon=str(ROOT / "desktop/videria.ico"), localization={
                          "global.quitConfirmation": "¿Cerrar Videria? Guarda tus cambios con Ctrl+S antes de salir."})
    finally:
        app.stop()
    if options.window_test and not (data / "window-test.ok").exists():
        raise RuntimeError("La ventana nativa no llegó a cargar")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        if getattr(sys, "frozen", False) and not any(flag in sys.argv for flag in ("--smoke-test", "--window-test")):
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,
                "Videria no pudo iniciar. Revisa %LOCALAPPDATA%\\VideriaData\\app.log. "
                "Comprueba que Microsoft Edge WebView2 Runtime esté instalado.", "Videria", 16)
        sys.exit(1)
