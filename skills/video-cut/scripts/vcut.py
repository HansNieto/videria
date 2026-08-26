# -*- coding: utf-8 -*-
"""vcut - ordena, transcribe, quita silencios y tomas repetidas, y abre un editor.

Nunca recodifica el material original: el resultado es un proyecto de cortes
(project.json) mas exports para NLE. Los proxies del editor son solo preview.

Uso rapido:
    python vcut.py run "C:/ruta/videos" --project "C:/ruta/mi-proyecto"
    python vcut.py edit --project "C:/ruta/mi-proyecto"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vcutlib import (disfluencias, analyze, exporters, ingest, media, overlays,  # noqa: E402
                     pack as packmod, plan, qa, render as rendermod,
                     stickers as stickermod, studio, subs as submod, templates,
                     transcribe, util)

util.setup_stdio()


def out(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def project_paths(args):
    pdir = Path(args.project).expanduser().resolve()
    return pdir, pdir / "project.json"


def load_project(args):
    pdir, pfile = project_paths(args)
    data = util.read_json(pfile)
    if data is None:
        raise SystemExit("No encuentro %s. Corre primero: vcut.py new / run" % pfile)
    return pdir, pfile, data


def cfg_from_args(args, base=None):
    cfg = dict(base or analyze.DEFAULTS)
    for key in analyze.DEFAULTS:
        val = getattr(args, key.replace("-", "_"), None)
        if val is not None:
            cfg[key] = val
    return cfg


# ------------------------------------------------------------ comandos

def cmd_new(args):
    pdir, pfile = project_paths(args)
    util.eprint("Buscando archivos...")
    files = ingest.discover(args.inputs, recursive=args.recursive, pattern=args.filter)
    if not files:
        raise SystemExit("No encontre archivos multimedia en la entrada dada.")
    util.eprint("  %d archivo(s); leyendo metadatos..." % len(files))
    sources = ingest.build_sources(files, sort_by=args.sort)
    if not sources:
        raise SystemExit("Ningun archivo se pudo leer con ffprobe.")

    project = plan.new_project(
        name=args.name or pdir.name,
        sources=sources, utterances=[], groups=[],
        cfg=cfg_from_args(args),
        inputs={"paths": [str(Path(i).resolve()) for i in args.inputs],
                "sort": args.sort, "recursive": bool(args.recursive)},
        seq_fps=ingest.sequence_fps(sources),
        seq_size=ingest.sequence_size(sources),
    )
    util.write_json(pfile, project)
    out({"ok": True, "project": str(pfile), "sources": [
        {"id": s["id"], "name": s["name"], "duration": s["duration"],
         "fps": s["fps"], "size": "%dx%d" % (s["width"], s["height"]),
         "recorded_at": s["recorded_at"], "needs_proxy": s["needs_proxy"]}
        for s in sources]})


def cmd_transcribe(args):
    pdir, pfile, project = load_project(args)
    util.eprint("Transcribiendo %d archivo(s)..." % len(project["sources"]))
    transcripts = transcribe.transcribe_all(
        project["sources"], pdir,
        model_size=args.model, language=args.lang, device=args.device,
        compute_type=args.compute_type, initial_prompt=args.prompt,
        beam_size=args.beam, force=args.force,
    )
    verbatim = 0
    if getattr(args, "verbatim", False):
        # Segunda pasada con prompt disfluente. NO reemplaza a la anterior: se
        # guarda en "<id>.verbatim.json" y sirve para localizar titubeos y tomas
        # repetidas. Medido, ese prompt recupera arranques en falso que la
        # pasada legible repara, pero cambia el registro del texto, asi que el
        # texto bueno sigue siendo el de la pasada normal.
        util.eprint("Segunda pasada (verbatim) para localizar titubeos...")
        v = transcribe.transcribe_all(
            project["sources"], pdir,
            model_size=args.model, language=args.lang, device=args.device,
            compute_type=args.compute_type,
            initial_prompt=transcribe.VERBATIM_PROMPT,
            beam_size=args.beam, force=args.force, suffix=".verbatim",
        )
        verbatim = len(v)

    langs = {t.get("language") for t in transcripts.values() if t.get("language")}
    project["language"] = sorted(langs)[0] if langs else ""
    util.write_json(pfile, project)
    out({"ok": True, "language": project["language"],
         "transcribed": len(transcripts), "verbatim": verbatim,
         "words": sum(len(s["words"]) for t in transcripts.values()
                      for s in t.get("segments", []))})


def cmd_disfluencias(args):
    pdir, _pfile, project = load_project(args)
    res = disfluencias.informe(pdir, project["sources"], minimo=args.minimo)
    out({"ok": True, **res})


def cmd_analyze(args):
    pdir, pfile, project = load_project(args)
    transcripts = {}
    for s in project["sources"]:
        t = util.read_json(pdir / "transcripts" / ("%s.json" % s["id"]))
        if t is None:
            raise SystemExit("Falta la transcripcion de %s. Corre: vcut.py transcribe"
                             % s["name"])
        transcripts[s["id"]] = t

    cfg = cfg_from_args(args, project.get("config"))
    util.eprint("Cortando silencios y buscando tomas repetidas...")
    utts = analyze.build_utterances(project["sources"], transcripts, cfg)
    groups = analyze.detect_takes(utts, cfg)
    analyze.apply_groups(utts, groups)

    project["config"] = cfg
    project["segments"] = utts
    project["groups"] = groups
    plan.rebuild(project)
    util.write_json(pfile, project, backup=True)

    review = pdir / "review.md"
    review.write_text(plan.to_review_markdown(project), encoding="utf-8")
    out({"ok": True, "stats": project["stats"], "groups": len(groups),
         "review": str(review), "project": str(pfile)})


def cmd_review(args):
    pdir, pfile, project = load_project(args)
    review = pdir / "review.md"
    review.write_text(plan.to_review_markdown(project), encoding="utf-8")
    out({"ok": True, "review": str(review), "stats": project["stats"]})


def cmd_qa(args):
    """Contrasta el plan con el audio real y sugiere recortes."""
    pdir, pfile, project = load_project(args)
    report = qa.check(project, noise_db=args.noise, min_sil=args.min_sil,
                      min_lead=args.min_lead, min_tail=args.min_tail)
    if not args.no_orphans:
        cov = qa.coverage(project, noise_db=args.noise, min_sil=args.min_sil,
                          min_orphan=args.min_orphan)
        if cov["orphans"] and args.listen:
            cov["orphans"] = qa.listen(project, cov["orphans"],
                                       model_size=args.model,
                                       language=project.get("language"))
        report["orphans"] = cov["orphans"]
        report["mid_island"] = cov["mid_island"]
    if args.write:
        dfile = pdir / "decisions.json"
        decisions = util.read_json(dfile, {}) or {}
        trim = decisions.get("trim", {})
        trim.update(report["decisions_trim"])
        decisions["trim"] = trim
        util.write_json(dfile, decisions, backup=True)
        report["written"] = str(dfile)
    (pdir / "qa.md").write_text(qa.to_markdown(report), encoding="utf-8")
    report["md"] = str(pdir / "qa.md")
    out(report)


def cmd_decide(args):
    pdir, pfile, project = load_project(args)
    src = Path(args.file) if args.file else (pdir / "decisions.json")
    decisions = util.read_json(src)
    if decisions is None:
        raise SystemExit("No encuentro %s" % src)
    report = plan.apply_decisions(project, decisions)
    util.write_json(pfile, project, backup=True)
    (pdir / "review.md").write_text(plan.to_review_markdown(project), encoding="utf-8")
    out({"ok": True, "applied": report, "stats": project["stats"]})


def cmd_media(args):
    pdir, pfile, project = load_project(args)
    util.eprint("Generando assets de preview (no toca los originales)...")
    media.build_all(project, pdir, force=args.force, proxy_height=args.height,
                    proxies=not args.no_proxy, waveforms=not args.no_waveform,
                    filmstrips=not args.no_filmstrip, proxy_all=args.proxy_all)
    util.write_json(pfile, project, backup=True)
    out({"ok": True, "cache": str(pdir / "cache"),
         "proxies": sum(1 for s in project["sources"] if s.get("proxy"))})


def cmd_edit(args):
    from vcutlib import server
    pdir, pfile, _ = load_project(args)
    server.serve(pdir, port=args.port, open_browser=not args.no_open)


def cmd_studio(args):
    from vcutlib import server
    pdir, pfile, project = load_project(args)
    tl = studio.load(pdir, project)
    if not studio.path_of(pdir).exists():
        studio.save(pdir, tl)
        util.eprint("  timeline.json creado (canvas %dx%d @ %g fps)"
                    % (tl["canvas"]["width"], tl["canvas"]["height"],
                       tl["canvas"]["fps"]))
    for w in studio.validate(project, tl):
        util.eprint("  ! %s" % w)
    server.serve(pdir, port=args.port, open_browser=not args.no_open,
                 path="/studio")


def cmd_subs(args):
    pdir, pfile, project = load_project(args)
    tl = studio.load(pdir, project)
    kws = [k.strip() for k in (args.keywords or "").split(",") if k.strip()]
    n = submod.generate(project, tl, style_name=args.style, track_id=args.track,
                        project_dir=pdir, keywords=kws or None,
                        no_keywords=args.no_keywords, replace=not args.add)
    studio.save(pdir, tl)
    out({"ok": True, "cards": n, "track": args.track, "style": args.style,
         "timeline": str(studio.path_of(pdir))})


def cmd_overlays(args):
    pdir, pfile, project = load_project(args)
    tl = studio.load(pdir, project)
    util.eprint("Buscando secuencias de PNG con alfa...")
    made = overlays.convert_all(pdir, fps=args.fps, force=args.force,
                                on_step=lambda n: util.eprint("  %s" % n))
    res = {"ok": True, "convertidos": [
        {k: m[k] for k in ("name", "path", "dur", "frames", "title")} for m in made]}
    if not made:
        res["nota"] = ("No encontre secuencias `frames/<nombre>/0000.png`. "
                       "Generalas con la skill motion-overlays (capture.mjs).")
    if args.place and made:
        rep = overlays.place(project, tl, made, y=args.y, replace=not args.add,
                             min_score=args.min_score)
        studio.save(pdir, tl)
        res.update(rep)
    out(res)


def cmd_stickers(args):
    util.eprint("Generando la libreria de stickers...")
    info = stickermod.build(force=args.force, scale=args.scale,
                            on_step=lambda s: util.eprint("  %s" % s))
    out({"ok": True, "svg": info["svg"], "nuevos": info["nuevos"],
         "rasterizados": len(info["rasterizados"]),
         "svg_dir": info["svg_dir"], "png_dir": info["png_dir"]})


def cmd_template(args):
    if args.action == "list":
        out({"ok": True, "plantillas": templates.list_all()})
        return
    pdir, pfile, project = load_project(args)
    tl = studio.load(pdir, project)
    if args.action == "save":
        if not args.name:
            raise SystemExit("Falta --name")
        tpl = templates.extract(project, tl, args.name, args.label, args.hint)
        p = templates.save(tpl)
        out({"ok": True, "guardada": str(p), "receta": tpl["recipe"]})
        return
    # apply
    tpl = templates.load(args.name or "tiktok")
    rep = templates.apply(project, tl, tpl, pdir,
                          do_subs=not args.no_subs,
                          do_zooms=not args.no_zooms,
                          do_transitions=not args.no_transitions,
                          do_overlays=not args.no_overlays,
                          on_step=lambda s: util.eprint("  %s..." % s))
    studio.save(pdir, tl)
    res = studio.resolve(project, tl)
    out({"ok": True, **rep, "total": res["total"],
         "items": len(res["items"]), "avisos": studio.validate(project, tl)})


def cmd_pack(args):
    if args.skill:
        target = Path(args.out).expanduser() if args.out else \
            Path.cwd() / "video-cut-studio.zip"
        util.eprint("Empaquetando la herramienta...")
        out({"ok": True, **packmod.pack_skill(
            target, on_step=lambda s: util.eprint("  %s" % s))})
        return
    pdir, pfile, project = load_project(args)
    target = Path(args.out).expanduser() if args.out else \
        (pdir / "exports" / ("%s.vcutpack" % (project.get("name") or pdir.name)))
    util.eprint("Empaquetando el proyecto%s..."
                % (" con los videos" if args.media else ""))
    out({"ok": True, **packmod.pack_project(
        pdir, target, with_media=args.media,
        on_step=lambda s: util.eprint("  %s" % s))})


def cmd_unpack(args):
    pdir = Path(args.project).expanduser().resolve()
    util.eprint("Abriendo el paquete en %s..." % pdir)
    rep = packmod.unpack_project(args.zip, pdir, media_dir=args.media,
                                 on_step=lambda s: util.eprint("  %s" % s))
    out({"ok": True, **rep})


def cmd_render(args):
    pdir, pfile, project = load_project(args)
    tl = studio.load(pdir, project)
    range_ = None
    if args.from_t is not None or args.to_t is not None:
        res = studio.resolve(project, tl)
        range_ = (float(args.from_t or 0.0),
                  float(args.to_t if args.to_t is not None else res["total"]))
    base = args.name or project.get("name") or "render"
    target = Path(args.out).expanduser() if args.out else \
        (pdir / "exports" / ("%s%s.mp4" % (base, "-borrador" if args.draft else "")))
    target.parent.mkdir(parents=True, exist_ok=True)

    width = [0]

    def prog(frac, secs):
        bar = int(frac * 34)
        line = "  [%s%s] %3d%%  %.1fs" % ("#" * bar, "." * (34 - bar),
                                          frac * 100, secs)
        width[0] = max(width[0], len(line))
        print("\r%-*s" % (width[0], line), end="", file=sys.stderr, flush=True)

    info = rendermod.render(project, tl, pdir, target, draft=args.draft,
                            range_=range_, on_progress=prog,
                            on_stage=lambda s: util.eprint("\n  %s..." % s))
    util.eprint("")
    out({"ok": True, **info})


def cmd_export(args):
    pdir, pfile, project = load_project(args)
    target = Path(args.out).expanduser() if args.out else (pdir / "exports")
    written = []
    for fmt in args.format:
        written.append(str(exporters.export(project, fmt, target, args.basename)))
    out({"ok": True, "written": written,
         "cuts": len(plan.timeline(project)),
         "duration": project["stats"].get("timeline_duration")})


def cmd_info(args):
    pdir, pfile, project = load_project(args)
    out({"name": project["name"], "sequence": project["sequence"],
         "stats": project["stats"], "config": project.get("config"),
         "groups": len(project.get("groups", [])),
         "sources": [{"id": s["id"], "name": s["name"], "duration": s["duration"],
                      "proxy": bool(s.get("proxy"))} for s in project["sources"]]})


def cmd_run(args):
    cmd_new(args)
    cmd_transcribe(args)
    cmd_analyze(args)
    if not args.skip_media:
        cmd_media(args)
    pdir, pfile, project = load_project(args)
    out({"ok": True, "listo": True, "project": str(pfile),
         "review": str(pdir / "review.md"), "stats": project["stats"],
         "grupos_de_tomas": len(project["groups"]),
         "siguiente": "lee review.md, escribe decisions.json, "
                      "corre 'vcut.py decide' y luego 'vcut.py edit'"})


# ------------------------------------------------------------ cli

def build_parser():
    p = argparse.ArgumentParser(prog="vcut", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_project(sp):
        sp.add_argument("--project", "-p", required=True,
                        help="Carpeta del proyecto (se crea si no existe)")

    def add_analysis_opts(sp):
        sp.add_argument("--pause", type=float, help="Hueco (s) que corta frase [0.55]")
        sp.add_argument("--pad-in", dest="pad_in", type=float, help="Aire antes [0.12]")
        sp.add_argument("--pad-out", dest="pad_out", type=float, help="Aire despues [0.22]")
        sp.add_argument("--min-dur", dest="min_dur", type=float, help="Frase minima [0.18]")
        sp.add_argument("--max-utt", dest="max_utt", type=float, help="Frase maxima [14]")
        sp.add_argument("--lookahead", type=int, help="Frases adelante a comparar [8]")
        sp.add_argument("--window", type=float, help="Ventana de retoma en s de habla [90]")
        sp.add_argument("--sim-ratio", dest="sim_ratio", type=float, help="Similitud [0.68]")
        sp.add_argument("--contain", type=float, help="Contencion [0.80]")
        sp.add_argument("--prefix", type=float, help="Prefijo comun [0.60]")

    def add_transcribe_opts(sp):
        sp.add_argument("--model", default="medium",
                        help="tiny|base|small|medium|large-v3 [medium]")
        sp.add_argument("--lang", default=None, help="Codigo ISO (es, en...). Auto si se omite")
        sp.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
        sp.add_argument("--compute-type", dest="compute_type", default=None)
        sp.add_argument("--prompt", default=None, help="Vocabulario/contexto para whisper")
        sp.add_argument("--beam", type=int, default=5)
        sp.add_argument("--verbatim", action="store_true",
                        help="Segunda pasada con prompt disfluente, para localizar "
                             "titubeos y tomas repetidas que la pasada normal repara")

    def add_media_opts(sp):
        sp.add_argument("--height", type=int, default=540, help="Alto del proxy [540]")
        sp.add_argument("--proxy-all", dest="proxy_all", action="store_true",
                        help="Proxy para todos, no solo los que el navegador no puede")
        sp.add_argument("--no-proxy", action="store_true")
        sp.add_argument("--no-waveform", action="store_true")
        sp.add_argument("--no-filmstrip", action="store_true")

    sp = sub.add_parser("new", help="Descubre y ordena los archivos")
    sp.add_argument("inputs", nargs="+", help="Carpetas o archivos")
    add_project(sp)
    sp.add_argument("--sort", default="name", choices=["name", "date", "none"])
    sp.add_argument("--name", default=None, help="Nombre del proyecto")
    sp.add_argument("--recursive", "-r", action="store_true")
    sp.add_argument("--filter", default=None, help="Regex sobre el nombre de archivo")
    add_analysis_opts(sp)
    sp.set_defaults(func=cmd_new)

    sp = sub.add_parser("transcribe", help="Transcribe con timestamps por palabra")
    add_project(sp)
    add_transcribe_opts(sp)
    sp.add_argument("--force", action="store_true", help="Ignora la cache")
    sp.set_defaults(func=cmd_transcribe)

    sp = sub.add_parser("disfluencias",
                        help="Compara la pasada legible con la verbatim y lista lo omitido")
    add_project(sp)
    sp.add_argument("--minimo", type=int, default=2,
                    help="Palabras minimas para reportar un tramo [2]. Con 1 "
                         "entran los desacuerdos de una sola palabra entre las "
                         "dos pasadas (debe/debes, necesita/necesitas), que son "
                         "cambio de registro del prompt y no titubeos: medido "
                         "en un proyecto real, 9 hallazgos con 1 y 2 con 2, "
                         "ambos reales")
    sp.set_defaults(func=cmd_disfluencias)

    sp = sub.add_parser("analyze", help="Quita silencios y agrupa tomas repetidas")
    add_project(sp)
    add_analysis_opts(sp)
    sp.set_defaults(func=cmd_analyze)

    sp = sub.add_parser("review", help="Regenera review.md")
    add_project(sp)
    sp.set_defaults(func=cmd_review)

    sp = sub.add_parser("decide", help="Aplica decisions.json")
    add_project(sp)
    sp.add_argument("--file", "-f", default=None, help="Ruta de decisions.json")
    sp.set_defaults(func=cmd_decide)

    sp = sub.add_parser("qa", help="Verifica los cortes contra el audio real")
    sp.add_argument("--project", "-p", required=True)
    sp.add_argument("--noise", type=int, default=-45, help="Umbral de silencio en dB [-45]")
    sp.add_argument("--min-sil", type=float, default=0.15, help="Silencio minimo a detectar [0.15]")
    sp.add_argument("--min-lead", type=float, default=0.4, help="Aire al inicio que se marca [0.4]")
    sp.add_argument("--min-tail", type=float, default=0.4, help="Aire al final que se marca [0.4]")
    sp.add_argument("--write", action="store_true", help="Vuelca los recortes en decisions.json")
    sp.add_argument("--min-orphan", type=float, default=0.5,
                    help="Habla sin cubrir que se reporta, en s [0.5]")
    sp.add_argument("--no-orphans", action="store_true",
                    help="No buscar habla fuera del plan (mas rapido)")
    sp.add_argument("--listen", action="store_true",
                    help="Transcribe los tramos huerfanos para saber que dicen")
    sp.add_argument("--model", default="medium", help="Modelo para --listen [medium]")
    sp.set_defaults(func=cmd_qa)

    sp = sub.add_parser("media", help="Proxies, ondas y miniaturas del editor")
    add_project(sp)
    add_media_opts(sp)
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(func=cmd_media)

    sp = sub.add_parser("edit", help="Abre el editor en el navegador")
    add_project(sp)
    sp.add_argument("--port", type=int, default=7788)
    sp.add_argument("--no-open", action="store_true")
    sp.set_defaults(func=cmd_edit)

    sp = sub.add_parser("studio", help="Abre la plataforma completa "
                                       "(texto, zooms, transiciones, render)")
    add_project(sp)
    sp.add_argument("--port", type=int, default=7788)
    sp.add_argument("--no-open", action="store_true")
    sp.set_defaults(func=cmd_studio)

    sp = sub.add_parser("subs", help="Genera los subtitulos desde la transcripcion")
    add_project(sp)
    sp.add_argument("--style", default="capcut", help="Estilo de texto [capcut]")
    sp.add_argument("--track", default="t_sub", help="Pista destino [t_sub]")
    sp.add_argument("--keywords", default=None,
                    help="Palabras a resaltar, separadas por coma. Si se omite "
                         "las elige la heuristica")
    sp.add_argument("--no-keywords", action="store_true",
                    help="Sin palabra resaltada (y por tanto sin apilado)")
    sp.add_argument("--add", action="store_true",
                    help="No borrar los subtitulos generados antes")
    sp.set_defaults(func=cmd_subs)

    sp = sub.add_parser("overlays", help="Secuencias de PNG con alfa -> WebM, "
                                        "y los coloca donde se habla de eso")
    add_project(sp)
    sp.add_argument("--fps", type=float, default=overlays.FPS_DEFAULT,
                    help="fps con el que se capturaron los PNG [30]")
    sp.add_argument("--place", action="store_true",
                    help="Colocarlos en la pista de overlays buscando su clip")
    sp.add_argument("--y", type=float, default=0.30,
                    help="Altura en el lienzo, 0 arriba y 1 abajo [0.30]")
    sp.add_argument("--min-score", dest="min_score", type=float, default=0.28,
                    help="Parecido minimo con el texto del clip [0.28]. Los que "
                         "no llegan salen en sin_sitio con su puntaje")
    sp.add_argument("--add", action="store_true",
                    help="No quitar los overlays colocados antes")
    sp.add_argument("--force", action="store_true", help="Reconvertir aunque exista")
    sp.set_defaults(func=cmd_overlays)

    sp = sub.add_parser("stickers", help="Genera la libreria de stickers "
                                        "(SVG editables -> PNG con alfa)")
    sp.add_argument("--force", action="store_true",
                    help="Reescribir los SVG del catalogo y rasterizar todo")
    sp.add_argument("--scale", type=int, default=stickermod.RENDER_SCALE,
                    help="Multiplicador de resolucion [%d]" % stickermod.RENDER_SCALE)
    sp.set_defaults(func=cmd_stickers)

    sp = sub.add_parser("template", help="Plantillas de montaje: el mismo look "
                                        "y la misma receta en otro pack de videos")
    sp.add_argument("action", choices=["list", "apply", "save"])
    sp.add_argument("--project", "-p", default=None,
                    help="Carpeta del proyecto (no hace falta para `list`)")
    sp.add_argument("--name", default=None, help="Nombre de la plantilla")
    sp.add_argument("--label", default=None, help="Nombre visible (con `save`)")
    sp.add_argument("--hint", default=None, help="Descripcion (con `save`)")
    sp.add_argument("--no-subs", action="store_true")
    sp.add_argument("--no-zooms", action="store_true")
    sp.add_argument("--no-transitions", action="store_true")
    sp.add_argument("--no-overlays", action="store_true")
    sp.set_defaults(func=cmd_template)

    sp = sub.add_parser("pack", help="Empaqueta el proyecto (o la herramienta) "
                                     "en un zip para pasarlo")
    sp.add_argument("--project", "-p", default=None)
    sp.add_argument("--out", default=None, help="Archivo de salida")
    sp.add_argument("--media", action="store_true",
                    help="Incluir los videos originales (el paquete pesara igual "
                         "que el material)")
    sp.add_argument("--skill", action="store_true",
                    help="Empaquetar la herramienta en vez de un proyecto")
    sp.set_defaults(func=cmd_pack)

    sp = sub.add_parser("unpack", help="Abre un paquete y vuelve a enlazar los videos")
    sp.add_argument("zip", help="El .vcutpack")
    add_project(sp)
    sp.add_argument("--media", default=None,
                    help="Carpeta donde estan los videos, para reenlazarlos")
    sp.set_defaults(func=cmd_unpack)

    sp = sub.add_parser("render", help="Quema todo a un MP4 listo para subir")
    add_project(sp)
    sp.add_argument("--out", default=None, help="Archivo de salida")
    sp.add_argument("--name", default=None, help="Nombre base del archivo")
    sp.add_argument("--draft", action="store_true",
                    help="Borrador rapido: menos resolucion, proxies y sin loudnorm")
    sp.add_argument("--from", dest="from_t", type=float, default=None,
                    help="Renderizar solo desde este segundo")
    sp.add_argument("--to", dest="to_t", type=float, default=None,
                    help="Renderizar solo hasta este segundo")
    sp.set_defaults(func=cmd_render)

    sp = sub.add_parser("export", help="Exporta a formatos de NLE")
    add_project(sp)
    sp.add_argument("--format", "-F", nargs="+", default=["fcpxml"],
                    choices=sorted(exporters.EXPORTERS))
    sp.add_argument("--out", default=None)
    sp.add_argument("--basename", default=None)
    sp.set_defaults(func=cmd_export)

    sp = sub.add_parser("info", help="Resumen del proyecto")
    add_project(sp)
    sp.set_defaults(func=cmd_info)

    sp = sub.add_parser("run", help="new + transcribe + analyze + media")
    sp.add_argument("inputs", nargs="+")
    add_project(sp)
    sp.add_argument("--sort", default="name", choices=["name", "date", "none"])
    sp.add_argument("--name", default=None)
    sp.add_argument("--recursive", "-r", action="store_true")
    sp.add_argument("--filter", default=None)
    sp.add_argument("--skip-media", action="store_true")
    sp.add_argument("--force", action="store_true")
    add_transcribe_opts(sp)
    add_analysis_opts(sp)
    add_media_opts(sp)
    sp.set_defaults(func=cmd_run)

    return p


def main():
    args = build_parser().parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        util.eprint("\nCancelado.")
        sys.exit(130)
    except (RuntimeError, OSError, ValueError) as exc:
        out({"ok": False, "error": str(exc)})
        sys.exit(1)


if __name__ == "__main__":
    main()
