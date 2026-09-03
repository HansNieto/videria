"""Ventana nativa + biblioteca local. La app nunca vive en el repo de un video."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import threading

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.serving import make_server

from vcutlib import server as studio_server

VERSION = "2.1.0"
RELEASES_URL = "https://github.com/HansNieto/videria/releases"
GITHUB_REPO = re.compile(r"https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")


def github_url(value):
    match = GITHUB_REPO.fullmatch(value.strip())
    if not match or match[2] in (".", ".."):
        raise ValueError("Pega la URL https://github.com/usuario/proyecto, sin claves ni parámetros.")
    return f"https://github.com/{match[1]}/{match[2]}.git", match[2]


class ProjectLibrary:
    def __init__(self, data_dir, roots=()):
        self.data_dir = Path(data_dir).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file = self.data_dir / "projects.json"
        self.lock = threading.RLock()
        self.paths = {}
        if self.file.exists():
            # Si el registro está dañado no se sobrescribe silenciosamente.
            entries = json.loads(self.file.read_text(encoding="utf-8"))
            for entry in entries:
                self._register(entry)
        for root in roots:
            root = Path(root)
            if root.is_dir():
                for path in sorted(root.iterdir()):
                    if (path / "project.json").is_file():
                        self._register(path)

    def _register(self, path):
        path = Path(path).expanduser().resolve()
        key = hashlib.sha256(os.path.normcase(str(path)).encode()).hexdigest()[:16]
        self.paths[key] = path
        return key

    def register(self, path):
        path = Path(path).expanduser().resolve()
        if path.name == "project.json":
            path = path.parent
        if not (path / "project.json").is_file():
            raise ValueError("Selecciona la carpeta de edición que contiene project.json (por ejemplo video17-proyecto).")
        project = json.loads((path / "project.json").read_text(encoding="utf-8-sig"))
        if not isinstance(project.get("segments"), list) or not isinstance(project.get("sources"), list):
            raise ValueError("Ese project.json no es un proyecto de Videria válido.")
        with self.lock:
            key = self._register(path)
            temp = self.file.with_suffix(".tmp")
            temp.write_text(json.dumps([str(p) for p in self.paths.values()], indent=2), encoding="utf-8")
            temp.replace(self.file)
        return key

    def get(self, key):
        with self.lock:
            path = self.paths.get(key)
        if not path or not (path / "project.json").is_file():
            raise ValueError("No se encuentra el proyecto. Vuelve a agregar su carpeta.")
        return path

    def list(self):
        with self.lock:
            entries = list(self.paths.items())
        out = []
        for key, path in entries:
            try:
                project = json.loads((path / "project.json").read_text(encoding="utf-8-sig"))
                out.append({"id": key, "path": str(path), "name": project.get("name") or path.name,
                            "clips": sum(bool(s.get("enabled")) for s in project.get("segments", [])),
                            "git": (path / ".git").exists(), "available": True})
            except (OSError, ValueError, TypeError):
                out.append({"id": key, "path": str(path), "name": path.name, "available": False})
        return out


def git_executable():
    hit = shutil.which("git")
    if hit:
        return hit
    candidate = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/cmd/git.exe"
    if candidate.is_file():
        return str(candidate)
    raise ValueError("Para descargar/recibir proyectos instala Git para Windows y entra a GitHub Desktop. También puedes agregar una carpeta ya descargada.")


def git_run(args, cwd, timeout=120):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    result = subprocess.run([git_executable(), *args], cwd=str(cwd), capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=timeout,
                            env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        raise ValueError((result.stderr or result.stdout).strip()[-900:] +
                         "\nSi es privado, acepta la invitación y autentícate con GitHub Desktop o Git Credential Manager.")
    return result.stdout.strip()


class DesktopHost:
    def __init__(self, data_dir, ui_dir, roots=(), projects_dir=None, port=0):
        self.library = ProjectLibrary(data_dir, roots)
        self.ui_dir = Path(ui_dir)
        self.projects_dir = Path(projects_dir or Path.home() / "Documents/Videria/Proyectos")
        self.token = secrets.token_urlsafe(32)
        self.services = {}
        self.lock = threading.RLock()
        self.pick_folder = None
        self.app = self._app()
        self.http = make_server("127.0.0.1", port, self.app, threaded=True)
        self.url = f"http://127.0.0.1:{self.http.server_port}"

    def _app(self):
        app = Flask("videria-desktop", static_folder=None)

        @app.before_request
        def local_only():
            if request.host.split(':')[0] != "127.0.0.1":
                return jsonify(error="Host no permitido"), 403
            if request.method == "POST" and not secrets.compare_digest(
                    request.headers.get("X-Videria-Token", ""), self.token):
                return jsonify(error="Sesión vencida. Vuelve a abrir Videria."), 403

        @app.after_request
        def no_cache(response):
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            return response

        @app.errorhandler(ValueError)
        def invalid(error):
            return jsonify(error=str(error)), 400

        @app.errorhandler(subprocess.TimeoutExpired)
        def timeout(_error):
            return jsonify(error="Git tardó demasiado. Comprueba la conexión o abre el proyecto desde GitHub Desktop."), 408

        @app.route("/")
        def index():
            return send_from_directory(self.ui_dir, "index.html")

        @app.route("/ui/<path:name>")
        def ui(name):
            return send_from_directory(self.ui_dir, name)

        @app.route("/help/<path:name>")
        def help_page(name):
            return send_from_directory(self.ui_dir.parent.parent / "docs", name)

        @app.route("/desktop/projects")
        def projects():
            return jsonify(projects=self.library.list(), version=VERSION, token=self.token,
                           projects_dir=str(self.projects_dir), releases=RELEASES_URL,
                           native_picker=self.pick_folder is not None)

        @app.post("/desktop/register")
        def register():
            payload = request.get_json() or {}
            path = payload.get("path")
            if not path and self.pick_folder:
                path = self.pick_folder()
            if not path:
                return jsonify(cancelled=True)
            return jsonify(id=self.library.register(path))

        @app.post("/desktop/open")
        def open_project():
            key = (request.get_json() or {}).get("id")
            return jsonify(url=self.open_project(key))

        @app.post("/desktop/reveal")
        def reveal_project():
            path = self.library.get((request.get_json() or {}).get("id"))
            os.startfile(path)
            return jsonify(ok=True)

        @app.post("/desktop/clone")
        def clone():
            payload = request.get_json() or {}
            url, name = github_url(payload.get("url", ""))
            # El destino no puede salir de Proyectos y jamás se sobreescribe.
            self.projects_dir.mkdir(parents=True, exist_ok=True)
            dest = self.projects_dir / name
            if dest.exists():
                raise ValueError("Esa carpeta ya existe. Usa Agregar carpeta o Recibir cambios; no se sobreescribió nada.")
            git_run(["clone", "--", url, str(dest)], self.projects_dir, timeout=600)
            return jsonify(id=self.library.register(dest))

        @app.post("/desktop/pull")
        def pull():
            path = self.library.get((request.get_json() or {}).get("id"))
            if not (path / ".git").exists():
                raise ValueError("No es un clon Git. Descarga el proyecto con GitHub Desktop o con Descargar de GitHub.")
            if git_run(["status", "--porcelain"], path):
                raise ValueError("Hay cambios locales. Publícalos primero con GitHub Desktop. No se tocó tu edición.")
            return jsonify(message=git_run(["pull", "--ff-only"], path))

        return app

    def start(self):
        threading.Thread(target=self.http.serve_forever, daemon=True).start()

    def open_project(self, key):
        path = self.library.get(key)
        with self.lock:
            if key not in self.services:
                app = studio_server.create_app(path)

                @app.get("/api/desktop")
                def desktop_info():
                    return jsonify(home=self.url, version=VERSION)

                http = make_server("127.0.0.1", 0, app, threaded=True)
                threading.Thread(target=http.serve_forever, daemon=True).start()
                self.services[key] = (http, app)
            http, _app = self.services[key]
        return f"http://127.0.0.1:{http.server_port}/studio"

    def stop(self):
        for http, app in self.services.values():
            cancel = app.extensions.get("vcut_cancel_jobs")
            if cancel:
                cancel()
            http.shutdown()
            http.server_close()
        self.http.shutdown()
        self.http.server_close()
