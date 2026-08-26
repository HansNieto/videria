# -*- coding: utf-8 -*-
"""Servidor local del editor de cortes y del studio. Solo escucha en 127.0.0.1.

Dos frontales sobre el mismo proyecto:

* `/`        editor de cortes (project.json). El de siempre.
* `/studio`  plataforma completa: texto, zooms, transiciones, audio y render.

El studio escribe `timeline.json` y tambien puede escribir `project.json`, asi
que los cortes se editan en los dos sitios sin salir de la aplicacion.
"""
from __future__ import annotations

import os
import threading
import time
import traceback
import uuid
import webbrowser
from pathlib import Path

from flask import (Flask, abort, jsonify, request, send_file,
                   send_from_directory)

from . import (assbuild, exporters, library, media, plan, render, studio, subs,
               textlayer, util)

EDITOR_DIR = Path(__file__).resolve().parent.parent.parent / "editor"
STUDIO_DIR = Path(__file__).resolve().parent.parent.parent / "studio"


def create_app(project_dir):
    project_dir = Path(project_dir).resolve()
    project_file = project_dir / "project.json"
    app = Flask(__name__, static_folder=None)
    app.config["JSON_AS_ASCII"] = False
    lock = threading.Lock()
    jobs = {}
    jobs_lock = threading.Lock()

    def load():
        data = util.read_json(project_file)
        if data is None:
            abort(404, "No hay project.json en %s" % project_dir)
        return studio.resolve_paths(data, project_dir)

    def load_tl(project=None):
        return studio.load(project_dir, project or load())

    def find_source(project, sid):
        for s in project["sources"]:
            if s["id"] == sid:
                return s
        abort(404, "source %s no existe" % sid)

    def body():
        return request.get_json(force=True, silent=True) or {}

    # ---------------------------------------------------------- estaticos

    @app.route("/")
    def index():
        return send_from_directory(EDITOR_DIR, "index.html")

    @app.route("/assets/<path:name>")
    def assets(name):
        return send_from_directory(EDITOR_DIR, name)

    @app.route("/studio")
    @app.route("/studio/")
    def studio_index():
        return send_from_directory(STUDIO_DIR, "index.html")

    @app.route("/studio/<path:name>")
    def studio_assets(name):
        return send_from_directory(STUDIO_DIR, name)

    # ---------------------------------------------------------- proyecto

    @app.route("/api/project", methods=["GET"])
    def get_project():
        project = load()
        project["_paths"] = {
            "dir": str(project_dir),
            "exports": str(project_dir / "exports"),
        }
        return jsonify(project)

    @app.route("/api/project", methods=["POST"])
    def post_project():
        incoming = body()
        if "segments" not in incoming:
            abort(400, "payload invalido")
        with lock:
            current = util.read_json(project_file, {}) or {}
            # El cliente solo manda lo editable; el resto se conserva del disco.
            current["segments"] = incoming["segments"]
            if "groups" in incoming:
                current["groups"] = incoming["groups"]
            if "name" in incoming:
                current["name"] = incoming["name"]
            plan.rebuild(current)
            studio.save_project(project_dir, current, backup=True)
        return jsonify({"ok": True, "stats": current["stats"]})

    # ---------------------------------------------------------- timeline

    @app.route("/api/timeline", methods=["GET"])
    def get_timeline():
        project = load()
        tl = load_tl(project)
        return jsonify({"timeline": tl,
                        "resolved": studio.resolve(project, tl),
                        "warnings": studio.validate(project, tl)})

    @app.route("/api/timeline", methods=["POST"])
    def post_timeline():
        incoming = body()
        tl = incoming.get("timeline")
        if not isinstance(tl, dict) or "tracks" not in tl:
            abort(400, "timeline invalido")
        with lock:
            project = load()
            # Los cortes pueden venir en el mismo guardado: el studio tambien
            # los edita, y guardar las dos capas juntas evita que se separen.
            if isinstance(incoming.get("segments"), list):
                project["segments"] = incoming["segments"]
                if isinstance(incoming.get("groups"), list):
                    project["groups"] = incoming["groups"]
                plan.rebuild(project)
                studio.save_project(project_dir, project, backup=True)
            studio.migrate(tl, project)
            studio.save(project_dir, tl)
        return jsonify({"ok": True, "stats": project.get("stats"),
                        "resolved": studio.resolve(project, tl),
                        "warnings": studio.validate(project, tl)})

    @app.route("/api/timeline/gc", methods=["POST"])
    def timeline_gc():
        with lock:
            project = load()
            tl = load_tl(project)
            n = studio.gc(project, tl)
            studio.save(project_dir, tl)
        return jsonify({"ok": True, "removed": n})

    # ---------------------------------------------------------- catalogos

    @app.route("/api/catalog")
    def catalog():
        return jsonify({
            "transitions": render.transitions_catalog(),
            "anims": {k: [[p, dict(v)] for p, v in kfs]
                      for k, kfs in assbuild.ANIM.items()},
            "eases": list(studio.EASES),
            "ease_curves": studio.EASE_CURVES,
            "zoom_presets": studio.ZOOM_PRESETS,
            "styles": studio.DEFAULT_STYLES,
            "fonts": textlayer.list_fonts(project_dir),
            "library": library.scan(project_dir),
            "zmax": studio.ZMAX,
            "sref": studio.SREF,
            "nvenc": media.nvenc_available(),
        })

    @app.route("/api/font/<path:name>")
    def font(name):
        p = textlayer.find_font(name, project_dir)
        if not p or not Path(p).exists():
            abort(404, "sin fuente %s" % name)
        resp = send_file(str(p), conditional=True)
        resp.headers["Cache-Control"] = "public, max-age=604800"
        return resp

    @app.route("/api/asset")
    def asset():
        path = request.args.get("path") or ""
        if not library.allowed(project_dir, path):
            abort(403, "fuera de las carpetas del proyecto")
        resp = send_file(path, conditional=True)
        resp.headers["Cache-Control"] = "public, max-age=3600"
        return resp

    # ---------------------------------------------------------- media

    @app.route("/api/media/<sid>")
    def media_file(sid):
        # No se llama `media`: definir aqui ese nombre taparia el modulo
        # `media` para todo el resto de `create_app`.
        project = load()
        src = find_source(project, sid)
        path = src.get("proxy") or src["path"]
        if not Path(path).exists():
            path = src["path"]
        if not Path(path).exists():
            abort(404, "archivo no encontrado: %s" % path)
        # conditional=True habilita Range: sin esto el navegador no puede buscar.
        return send_file(path, conditional=True)

    @app.route("/api/waveform/<sid>")
    def waveform(sid):
        project = load()
        src = find_source(project, sid)
        wf = src.get("waveform")
        if not wf or not Path(wf).exists():
            abort(404, "sin waveform")
        resp = send_file(wf, mimetype="application/octet-stream", conditional=True)
        resp.headers["Cache-Control"] = "public, max-age=86400"
        return resp

    @app.route("/api/filmstrip/<sid>")
    def filmstrip(sid):
        project = load()
        src = find_source(project, sid)
        strip = src.get("filmstrip") or {}
        url = strip.get("url") if isinstance(strip, dict) else strip
        if not url or not Path(url).exists():
            abort(404, "sin filmstrip")
        resp = send_file(url, mimetype="image/jpeg", conditional=True)
        resp.headers["Cache-Control"] = "public, max-age=86400"
        return resp

    # ---------------------------------------------------------- texto

    @app.route("/api/wrap", methods=["POST"])
    def wrap():
        """Reparte texto en lineas con las metricas reales del .ttf.

        El navegador podria medir con canvas, pero entonces el corte de linea
        del preview y el del render podrian no coincidir. Con esto solo hay una
        opinion sobre donde se parte una linea.
        """
        b = body()
        project = load()
        tl = load_tl(project)
        style = dict(tl["styles"].get(b.get("style") or "capcut") or {})
        style.update(b.get("override") or {})
        words = b.get("words")
        if not words:
            words = [{"w": w, "s": 0.0, "e": 0.0}
                     for w in (b.get("text") or "").split()]
        dur = float(b.get("dur") or 0)
        if dur and not any(w.get("e") for w in words):
            # Sin tiempos por palabra, se reparten por igual: es lo que hace
            # falta para que el revelado tenga sentido en un texto escrito.
            n = max(1, len(words))
            for i, w in enumerate(words):
                w["s"] = round(dur * i / n, 3)
                w["e"] = round(dur * (i + 1) / n, 3)
        key = b.get("keyword")
        key_idx = None
        if key:
            kn = util.normalize(key)
            key_idx = next((i for i, w in enumerate(words)
                            if util.normalize(w["w"]) == kn), None)
        elif b.get("auto_keyword"):
            key_idx = textlayer.pick_keyword(words)
        canvas_w = int(b.get("canvas_w") or tl["canvas"]["width"])
        lines = textlayer.wrap(words, style, canvas_w, key_idx, project_dir)
        maxl = int(b.get("max_lines") or style.get("max_lines") or 3)
        return jsonify({"ok": True, "lines": lines[:maxl],
                        "overflow": max(0, len(lines) - maxl),
                        "metrics": textlayer.line_metrics(lines[:maxl], style,
                                                          canvas_w, project_dir)})

    @app.route("/api/subs", methods=["POST"])
    def make_subs():
        b = body()
        with lock:
            project = load()
            tl = load_tl(project)
            n = subs.generate(
                project, tl,
                style_name=b.get("style") or "capcut",
                track_id=b.get("track") or "t_sub",
                project_dir=project_dir,
                keywords=b.get("keywords"),
                no_keywords=bool(b.get("no_keywords")),
                replace=b.get("replace", True),
                only_segs=b.get("segs"),
            )
            studio.save(project_dir, tl)
        return jsonify({"ok": True, "cards": n, "timeline": tl,
                        "resolved": studio.resolve(project, tl)})

    @app.route("/api/relayout", methods=["POST"])
    def relayout():
        b = body()
        with lock:
            project = load()
            tl = load_tl(project)
            n = subs.relayout(tl, b.get("style"), project_dir,
                              b.get("track") or "t_sub")
            studio.save(project_dir, tl)
        return jsonify({"ok": True, "items": n, "timeline": tl})

    # ---------------------------------------------------------- render

    def _run_job(job_id, draft, range_, out):
        job = jobs[job_id]
        try:
            project = load()
            tl = load_tl(project)

            def prog(frac, secs):
                job["progress"] = round(frac, 4)
                job["done_secs"] = round(secs, 2)

            def stage(name):
                job["stage"] = name

            def started(proc):
                job["_proc"] = proc

            info = render.render(project, tl, project_dir, out, draft=draft,
                                 range_=range_, on_progress=prog,
                                 on_stage=stage, on_start=started)
            job.update(status="ok", progress=1.0, info=info,
                       stage="listo", ended=time.time())
        except Exception as exc:                      # noqa: BLE001
            if job.get("cancelled"):
                job.update(status="cancelado", stage="cancelado",
                           ended=time.time())
            else:
                job.update(status="error", error=str(exc), stage="error",
                           trace=traceback.format_exc()[-2000:],
                           ended=time.time())
        finally:
            job.pop("_proc", None)

    @app.route("/api/render", methods=["POST"])
    def start_render():
        b = body()
        draft = bool(b.get("draft"))
        rng = b.get("range")
        range_ = None
        if isinstance(rng, (list, tuple)) and len(rng) == 2:
            range_ = (max(0.0, float(rng[0])), float(rng[1]))
            if range_[1] - range_[0] < 0.2:
                abort(400, "el tramo es demasiado corto")
        name = b.get("name") or None
        project = load()
        base = util.normalize(name or project.get("name") or "render") \
            .replace(" ", "-") or "render"
        out_dir = project_dir / "exports"
        out_dir.mkdir(parents=True, exist_ok=True)
        suffix = "-borrador" if draft else ""
        if range_:
            suffix += "-tramo"
        out = out_dir / ("%s%s.mp4" % (base, suffix))
        job_id = uuid.uuid4().hex[:10]
        with jobs_lock:
            # Un render a la vez: dos ffmpeg pesados en paralelo tardan mas que
            # en serie y dejan la maquina inservible.
            for j in jobs.values():
                if j["status"] == "corriendo":
                    return jsonify({"ok": False, "error": "ya hay un render en marcha",
                                    "job": j["id"]}), 409
            jobs[job_id] = {"id": job_id, "status": "corriendo", "progress": 0.0,
                            "stage": "preparando", "out": str(out),
                            "draft": draft, "range": range_,
                            "started": time.time()}
        threading.Thread(target=_run_job, args=(job_id, draft, range_, out),
                         daemon=True).start()
        return jsonify({"ok": True, "job": job_id, "out": str(out)})

    @app.route("/api/render/<job_id>")
    def render_status(job_id):
        job = jobs.get(job_id)
        if not job:
            abort(404, "no existe el trabajo")
        return jsonify({k: v for k, v in job.items() if not k.startswith("_")})

    @app.route("/api/render/<job_id>/cancel", methods=["POST"])
    def render_cancel(job_id):
        job = jobs.get(job_id)
        if not job:
            abort(404, "no existe el trabajo")
        job["cancelled"] = True
        proc = job.get("_proc")
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass
        return jsonify({"ok": True})

    @app.route("/api/renders")
    def render_list():
        return jsonify([{k: v for k, v in j.items() if not k.startswith("_")}
                        for j in sorted(jobs.values(),
                                        key=lambda x: x["started"], reverse=True)])

    # ---------------------------------------------------------- acciones

    @app.route("/api/export", methods=["POST"])
    def do_export():
        b = body()
        fmt = b.get("format", "fcpxml")
        project = load()
        try:
            out = exporters.export(project, fmt, project_dir / "exports")
        except (ValueError, RuntimeError, OSError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return jsonify({"ok": True, "path": str(out)})

    @app.route("/api/reveal", methods=["POST"])
    def reveal():
        b = body()
        target = Path(b.get("path") or project_dir)
        if not target.exists():
            return jsonify({"ok": False, "error": "no existe"}), 404
        try:
            os.startfile(target if target.is_dir() else target.parent)  # noqa: S606
        except (AttributeError, OSError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return jsonify({"ok": True})

    return app


def serve(project_dir, host="127.0.0.1", port=7788, open_browser=True,
          path="/"):
    app = create_app(project_dir)
    url = "http://%s:%d%s" % (host, port, path)
    util.eprint("")
    util.eprint("  Listo -> %s" % url)
    util.eprint("  Ctrl+C para cerrar.")
    util.eprint("")
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host=host, port=port, threaded=True, debug=False, use_reloader=False)
