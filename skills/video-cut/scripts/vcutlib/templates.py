# -*- coding: utf-8 -*-
"""Plantillas: el mismo montaje aplicado a otro pack de videos.

Una plantilla guarda **el look y la receta**, no el contenido: lienzo, ajustes
de render, estilos de texto, y con que patron repartir zooms, transiciones y
subtitulos. Aplicarla a un proyecto recien analizado deja el montaje hecho —
subtitulos puestos, zooms alternados, transiciones con su golpe de sonido— para
empezar a editar en vez de empezar de cero.

Los zooms se reparten **rotando un patron** y no al azar: al azar, dos clips
seguidos pueden salir con el mismo movimiento y se nota como un error. Y las
transiciones van cada N cortes, porque una en cada corte cansa a los diez
segundos.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from . import studio, util

DIR = util.skill_root() / "templates"
VERSION = 1


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# La receta con la que se monto el primer video vertical de este equipo.
BUILTIN = {
    "tiktok": {
        "vcut_template": VERSION,
        "name": "tiktok",
        "label": "TikTok vertical",
        "hint": "9:16, subtitulos apilados con palabra resaltada, zoom en cada "
                "clip y un golpe cada tres cortes.",
        "canvas": {"width": 1080, "height": 1920, "fps": 30, "bg": "#000000"},
        "render": {"encoder": "auto", "quality": 20, "loudnorm": True,
                   "loudnorm_i": -14.0, "fit": "cover", "draft_height": 720,
                   "audio_bitrate": "192k"},
        "styles": None,          # None = los que trae studio por defecto
        "recipe": {
            "subs": {"style": "capcut", "track": "t_sub"},
            "zooms": {"pattern": ["push_lento", "punch_in", "ken_burns",
                                  "reencuadre", "pull_out", "latido"],
                      "min_dur": 1.0},
            "transitions": {"every": 3, "types": ["punch_zoom", "whip", "flash"],
                            "dur": 0.28, "sfx": True},
            "overlays": {"place": True, "y": 0.30},
        },
    },
    "limpio": {
        "vcut_template": VERSION,
        "name": "limpio",
        "label": "Limpio",
        "hint": "Solo subtitulos y un empuje lento. Sin transiciones ni golpes: "
                "para hablar a camara sin adornos.",
        "canvas": {"width": 1080, "height": 1920, "fps": 30, "bg": "#000000"},
        "render": {"encoder": "auto", "quality": 19, "loudnorm": True,
                   "loudnorm_i": -14.0, "fit": "cover", "draft_height": 720,
                   "audio_bitrate": "192k"},
        "styles": None,
        "recipe": {
            "subs": {"style": "capcut", "track": "t_sub"},
            "zooms": {"pattern": ["push_lento", "reencuadre"], "min_dur": 1.5},
            "transitions": {"every": 0, "types": [], "dur": 0.28, "sfx": False},
            "overlays": {"place": False, "y": 0.30},
        },
    },
}


def path_of(name):
    return DIR / ("%s.json" % _slug(name))


def _slug(name):
    s = util.normalize(name).replace(" ", "-")
    return s or "plantilla"


def ensure_builtins():
    """Escribe las plantillas que trae la skill si no estan en el disco."""
    DIR.mkdir(parents=True, exist_ok=True)
    for name, tpl in BUILTIN.items():
        p = path_of(name)
        if not p.exists():
            util.write_json(p, tpl)


def list_all():
    ensure_builtins()
    out = []
    for f in sorted(DIR.glob("*.json")):
        tpl = util.read_json(f) or {}
        out.append({"name": tpl.get("name") or f.stem,
                    "label": tpl.get("label") or f.stem,
                    "hint": tpl.get("hint", ""),
                    "file": str(f),
                    "builtin": f.stem in BUILTIN})
    return out


def load(name):
    ensure_builtins()
    tpl = util.read_json(path_of(name))
    if tpl is None:
        raise ValueError("no existe la plantilla %s (mira `vcut template list`)"
                         % name)
    return tpl


def extract(project, tl, name, label=None, hint=None):
    """Saca una plantilla del proyecto abierto: su look y lo que se ve usado."""
    res = studio.resolve(project, tl)
    # El patron de zooms se lee del orden real en que aparecen los presets, sin
    # repetir seguidos: es lo que hace que aplicarla a otro video se parezca.
    pattern, last = [], None
    for c in res["clips"]:
        pid = ((c["cfg"].get("zoom") or {}).get("preset")) if c["cfg"].get("zoom") else None
        if pid and pid != last:
            pattern.append(pid)
            last = pid
    types, gaps, prev_idx = [], [], None
    for tr in res["transitions"]:
        c = next((x for x in res["clips"] if x["seg"] == tr["at_seg"]), None)
        if not c:
            continue
        if tr["type"] not in types:
            types.append(tr["type"])
        if prev_idx is not None:
            gaps.append(c["index"] - prev_idx)
        prev_idx = c["index"]
    every = int(round(sum(gaps) / float(len(gaps)))) if gaps else (3 if types else 0)
    durs = [tr["dur"] for tr in res["transitions"]]
    subs_items = [it for it in res["items"]
                  if it.get("track_kind") == "text" and it.get("auto")]

    return {
        "vcut_template": VERSION,
        "name": _slug(name),
        "label": label or name,
        "hint": hint or ("Sacada de %s el %s" % (project.get("name", "?"),
                                                 _now()[:10])),
        "created_at": _now(),
        "canvas": dict(tl["canvas"]),
        "render": dict(tl["render"]),
        "styles": {k: dict(v) for k, v in (tl.get("styles") or {}).items()},
        "recipe": {
            "subs": {"style": (subs_items[0].get("style") if subs_items else "capcut"),
                     "track": "t_sub"},
            "zooms": {"pattern": pattern or ["push_lento"], "min_dur": 1.0},
            "transitions": {"every": max(0, every), "types": types,
                            "dur": round(sum(durs) / len(durs), 3) if durs else 0.28,
                            "sfx": any(tr.get("sfx") for tr in tl.get("transitions", []))},
            "overlays": {"place": bool([it for it in res["items"]
                                        if it.get("track_kind") == "overlay"]),
                         "y": 0.30},
        },
    }


def save(tpl):
    DIR.mkdir(parents=True, exist_ok=True)
    return util.write_json(path_of(tpl["name"]), tpl, backup=True)


# ------------------------------------------------------------ aplicar

def apply(project, tl, tpl, project_dir, do_subs=True, do_zooms=True,
          do_transitions=True, do_overlays=True, on_step=None):
    """Deja el proyecto montado segun la plantilla. Devuelve un informe."""
    from . import overlays as ovlmod
    from . import render as rendermod
    from . import subs as submod

    rec = tpl.get("recipe") or {}
    rep = {"plantilla": tpl.get("name")}

    tl["canvas"] = dict(tpl.get("canvas") or tl["canvas"])
    tl["render"] = dict(tpl.get("render") or tl["render"])
    if tpl.get("styles"):
        tl["styles"] = {k: dict(v) for k, v in tpl["styles"].items()}

    if do_subs:
        cfg = rec.get("subs") or {}
        if on_step:
            on_step("subtitulos")
        rep["subtitulos"] = submod.generate(
            project, tl, style_name=cfg.get("style") or "capcut",
            track_id=cfg.get("track") or "t_sub", project_dir=project_dir)

    res = studio.resolve(project, tl)

    if do_zooms:
        cfg = rec.get("zooms") or {}
        pattern = cfg.get("pattern") or []
        if on_step:
            on_step("zooms")
        rep["zooms"] = _apply_zooms(tl, res, pattern,
                                    float(cfg.get("min_dur") or 0.0))

    if do_transitions:
        cfg = rec.get("transitions") or {}
        if on_step:
            on_step("transiciones")
        rep["transiciones"] = _apply_transitions(
            tl, res, cfg, project_dir, rendermod)

    if do_overlays and (rec.get("overlays") or {}).get("place"):
        if on_step:
            on_step("overlays")
        made = ovlmod.convert_all(project_dir)
        if made:
            rep["overlays"] = ovlmod.place(
                project, tl, made, y=float((rec["overlays"]).get("y") or 0.30))
        else:
            rep["overlays"] = {"colocados": [], "sin_sitio": []}
    return rep


def _apply_zooms(tl, res, pattern, min_dur):
    if not pattern:
        return 0
    presets = {p["id"]: p for p in studio.ZOOM_PRESETS}
    n, i = 0, 0
    for c in res["clips"]:
        if c["dur"] < min_dur:
            continue
        pid = pattern[i % len(pattern)]
        pr = presets.get(pid)
        i += 1
        if not pr:
            continue
        kf = [{"t": round(k["t"] if k.get("t") is not None
                          else (k.get("tf") or 0) * c["dur"], 3),
               "scale": k.get("scale", 1), "x": k.get("x", 0),
               "y": k.get("y", 0), "ease": k.get("ease", "inout")}
              for k in pr["kf"]]
        studio.clip_slot(tl, c["seg"])["zoom"] = {"kf": kf, "preset": pid}
        n += 1
    return n


def _apply_transitions(tl, res, cfg, project_dir, rendermod):
    from . import library
    every = int(cfg.get("every") or 0)
    types = cfg.get("types") or []
    if every <= 0 or not types:
        tl["transitions"] = []
        return 0
    dur = float(cfg.get("dur") or 0.28)
    want_sfx = bool(cfg.get("sfx"))
    lib = library.scan(project_dir).get("sfx", []) if want_sfx else []
    sfx_track = studio.track(tl, "t_sfx")
    if sfx_track is not None:
        sfx_track["items"] = [it for it in sfx_track["items"] if not it.get("auto")]
    tl["transitions"] = []
    n, k = 0, 0
    for c in res["clips"]:
        if c["index"] == 0 or c["index"] % every:
            continue
        tipo = types[k % len(types)]
        k += 1
        spec = rendermod.TRANSITIONS.get(tipo) or {}
        tr = {"id": studio.new_id(tl, "t"), "at_seg": c["seg"], "type": tipo,
              "dur": min(dur, c["dur"] * 0.9), "strength": 1.0}
        hit = None
        if want_sfx and spec.get("sfx"):
            hit = next((f for f in lib if f["name"] == spec["sfx"]), None)
        if hit:
            tr["sfx"] = hit["path"]
            tr["sfx_gain"] = -5.0
            if sfx_track is not None:
                sfx_track["items"].append({
                    "id": studio.new_id(tl, "a"), "kind": "audio", "auto": True,
                    "src": hit["path"], "gain": -5.0, "dur": 0.9,
                    "anchor": {"seg": c["seg"], "offset": -0.08, "clamp": False},
                })
        tl["transitions"].append(tr)
        n += 1
    return n
