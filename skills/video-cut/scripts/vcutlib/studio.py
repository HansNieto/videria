# -*- coding: utf-8 -*-
"""Capa creativa del proyecto: `timeline.json`.

`project.json` sigue siendo la verdad sobre los CORTES (que trozo de que
archivo, en que orden). Este modulo anade encima lo que no es un corte: texto,
zooms, transiciones, overlays, musica, velocidad y look. Vive en un archivo
aparte a proposito, para que `analyze` pueda reconstruir los cortes desde cero
sin llevarse por delante el trabajo de post.

La union entre las dos capas son las **anclas**: un item puede fijarse a un
segmento (`anchor: {seg, offset}`) en vez de a un tiempo absoluto. Asi, si mas
tarde se recorta o se mueve un clip, su texto lo sigue. Los subtitulos
generados desde la transcripcion siempre estan anclados; un titulo que el
usuario coloca a mano puede estar suelto.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from . import util

TIMELINE_VERSION = 1

# Ancho de referencia. Todos los tamanos en px del estilo (cuerpo de letra,
# desenfoque de sombra, desplazamientos) estan medidos sobre 1080 px de ancho y
# se escalan por W/1080. Cambiar el canvas no rompe el diseno.
SREF = 1080.0

# Zoom maximo que el render deja disponible. El material se prepara a
# canvas*ZMAX para que un zoom 2x salga de pixeles reales y no de una
# interpolacion.
ZMAX = 2.0

EASES = ("linear", "in", "out", "inout", "expo", "back", "hold")

# Curvas bezier con nombre, al estilo de las de CapCut. Un keyframe puede traer
# `"ease": "inout"` (nombre de EASES) o `"ease": {"bezier": [x1,y1,x2,y2]}` con
# las dos manijas en el cuadrado unidad del tramo: x es el tiempo normalizado y
# `y` la fraccion recorrida del valor. `y` fuera de 0..1 sobrepasa y vuelve.
EASE_CURVES = [
    {"id": "suave", "label": "Suave", "bezier": [0.42, 0.0, 0.58, 1.0],
     "hint": "Arranca y termina calmado. El equivalente al inout de siempre."},
    {"id": "entra_lento", "label": "Entra lento", "bezier": [0.6, 0.0, 1.0, 1.0],
     "hint": "Sale despacio y llega disparado."},
    {"id": "frena", "label": "Frena", "bezier": [0.0, 0.0, 0.35, 1.0],
     "hint": "Salta de entrada y se posa. Lo mas parecido a una camara real."},
    {"id": "latigo", "label": "Latigazo", "bezier": [0.85, 0.0, 0.15, 1.0],
     "hint": "Se queda quieto, cruza de golpe y se queda quieto."},
    {"id": "rebote", "label": "Rebote", "bezier": [0.34, 1.56, 0.64, 1.0],
     "hint": "Se pasa de largo y vuelve. Para acentos."},
    {"id": "anticipa", "label": "Anticipa", "bezier": [0.36, -0.4, 0.66, 1.0],
     "hint": "Retrocede un poco antes de arrancar."},
    {"id": "resorte", "label": "Resorte", "bezier": [0.5, -0.6, 0.4, 1.7],
     "hint": "Carga hacia atras y se pasa al llegar."},
]


def ease_bezier(ease):
    """Las 4 manijas si `ease` es una curva bezier; None si es un nombre.

    Acepta el objeto {"bezier":[...]}, el id de una curva de EASE_CURVES y la
    lista pelada de 4 numeros, que es como llegan los presets viejos a mano.
    """
    if isinstance(ease, dict):
        ease = ease.get("bezier") or ease.get("curve")
    if isinstance(ease, str):
        for c in EASE_CURVES:
            if c["id"] == ease:
                return list(c["bezier"])
        return None
    if isinstance(ease, (list, tuple)) and len(ease) == 4:
        try:
            b = [float(v) for v in ease]
        except (TypeError, ValueError):
            return None
        # x fuera de 0..1 haria retroceder el tiempo dentro del tramo.
        b[0] = min(1.0, max(0.0, b[0]))
        b[2] = min(1.0, max(0.0, b[2]))
        return b
    return None

ANIMS = ("none", "fade", "pop", "slide_up", "slide_down", "slide_left",
         "slide_right", "zoom_in", "zoom_out", "bounce")

TRACK_KINDS = ("text", "overlay", "audio")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------- estilos

# El estilo "capcut" reproduce el subtitulado apilado ya calibrado en la skill
# `subtitulo`: los valores vienen de medir fotogramas reales, no de estimarlos.
DEFAULT_STYLES = {
    "capcut": {
        "name": "CapCut apilado",
        "font": "Inter-Black.ttf",
        "size": 80,
        "color": "#FFFFFF",
        "keyword_font": "DancingScript-Bold.ttf",
        "keyword_color": "#4A90E0",
        "keyword_size_ratio": 1.5,
        "line_height": 1.16,
        "letter_spacing": 0,
        "shadow": {"opacity": 190, "blur": 9, "dx": 0, "dy": 6, "color": "#000000"},
        "outline": 0,
        "outline_color": "#000000",
        "box": {"x": 0.5, "y": 0.66, "w": 0.86},
        "align": "center",
        "max_lines": 3,
        "max_words_line": 4,
        "max_chars_line": 22,
        "stack_only_with_keyword": True,
        "reveal": "word",
        "anim_in": "pop",
        "anim_out": "none",
        "anim_dur": 0.22,
    },
    "titulo": {
        "name": "Titular",
        "font": "Anton-Regular.ttf",
        "size": 104,
        "color": "#FFFFFF",
        "keyword_font": "Anton-Regular.ttf",
        "keyword_color": "#FFD166",
        "keyword_size_ratio": 1.0,
        "line_height": 1.05,
        "letter_spacing": 0,
        "shadow": {"opacity": 150, "blur": 14, "dx": 0, "dy": 8, "color": "#000000"},
        "outline": 0,
        "outline_color": "#000000",
        "box": {"x": 0.5, "y": 0.16, "w": 0.9},
        "align": "center",
        "max_lines": 3,
        "max_words_line": 4,
        "max_chars_line": 20,
        "stack_only_with_keyword": False,
        "reveal": "none",
        "anim_in": "slide_up",
        "anim_out": "fade",
        "anim_dur": 0.3,
    },
    "nota": {
        "name": "Nota / etiqueta",
        "font": "BebasNeue-Regular.ttf",
        "size": 56,
        "color": "#0D0F14",
        "keyword_font": "BebasNeue-Regular.ttf",
        "keyword_color": "#5B8CFF",
        "keyword_size_ratio": 1.0,
        "line_height": 1.1,
        "letter_spacing": 2,
        "shadow": {"opacity": 0, "blur": 0, "dx": 0, "dy": 0, "color": "#000000"},
        "outline": 0,
        "outline_color": "#000000",
        "box": {"x": 0.5, "y": 0.85, "w": 0.8},
        "align": "center",
        "max_lines": 2,
        "max_words_line": 5,
        "max_chars_line": 26,
        "stack_only_with_keyword": False,
        "reveal": "none",
        "anim_in": "pop",
        "anim_out": "fade",
        "anim_dur": 0.2,
        "bg": {"color": "#FFFFFF", "opacity": 235, "pad": 22, "radius": 14},
    },
}


# Presets de zoom. `tf` es fraccion de la duracion del clip y `t` segundos
# absolutos desde su inicio; el que este definido manda. Asi un empuje lento
# dura lo que dure el clip y un punch siempre son los mismos 0,22 s.
ZOOM_PRESETS = [
    {"id": "push_lento", "label": "Empuje lento",
     "hint": "Acerca durante todo el clip. El recurso por defecto para hablar a camara.",
     "kf": [{"tf": 0.0, "scale": 1.0, "x": 0.0, "y": 0.0},
            {"tf": 1.0, "scale": 1.22, "x": 0.0, "y": -0.08, "ease": "inout"}]},
    {"id": "pull_out", "label": "Alejar",
     "hint": "Empieza cerca y abre. Sirve para revelar el contexto.",
     "kf": [{"tf": 0.0, "scale": 1.28, "x": 0.0, "y": -0.1},
            {"tf": 1.0, "scale": 1.0, "x": 0.0, "y": 0.0, "ease": "out"}]},
    {"id": "punch_in", "label": "Punch in",
     "hint": "Salta al plano corto en 0,22 s y se queda.",
     "kf": [{"t": 0.0, "scale": 1.0, "x": 0.0, "y": 0.0},
            {"t": 0.22, "scale": 1.24, "x": 0.0, "y": -0.12, "ease": "back"}]},
    {"id": "punch_out", "label": "Punch out",
     "hint": "Arranca cerca y se abre de golpe.",
     "kf": [{"t": 0.0, "scale": 1.24, "x": 0.0, "y": -0.12},
            {"t": 0.22, "scale": 1.0, "x": 0.0, "y": 0.0, "ease": "out"}]},
    {"id": "ken_burns", "label": "Ken Burns",
     "hint": "Deriva diagonal lenta. Da vida a un plano quieto.",
     "kf": [{"tf": 0.0, "scale": 1.12, "x": -0.18, "y": -0.12},
            {"tf": 1.0, "scale": 1.3, "x": 0.16, "y": 0.1, "ease": "linear"}]},
    {"id": "latido", "label": "Latido",
     "hint": "Un acento y vuelve. Para remarcar una palabra.",
     "kf": [{"t": 0.0, "scale": 1.0},
            {"t": 0.16, "scale": 1.09, "ease": "out"},
            {"t": 0.42, "scale": 1.0, "ease": "inout"}]},
    {"id": "cara", "label": "Foco en la cara",
     "hint": "Plano corto fijo en el tercio superior. Sin movimiento.",
     "kf": [{"tf": 0.0, "scale": 1.4, "x": 0.0, "y": -0.28}]},
    {"id": "reencuadre", "label": "Reencuadre",
     "hint": "Recorta un poco de aire, sin movimiento.",
     "kf": [{"tf": 0.0, "scale": 1.14, "x": 0.0, "y": -0.06}]},
]


DEFAULT_RENDER = {
    "encoder": "auto",          # auto | nvenc | x264
    "quality": 20,              # crf / cq
    "audio_bitrate": "192k",
    "loudnorm": True,
    "loudnorm_i": -14.0,        # objetivo de plataformas sociales
    "fit": "cover",             # como entra el material en el canvas
    "draft_height": 720,
}


def default_canvas(project):
    """Canvas de salida a partir del material, normalizado a algo publicable."""
    seq = project.get("sequence") or {}
    w = int(seq.get("width") or 1080)
    h = int(seq.get("height") or 1920)
    fps = float(seq.get("fps") or 30.0)
    if w <= 0 or h <= 0:
        w, h = 1080, 1920
    vertical = h >= w
    long_side = 1920
    if vertical:
        out_h = min(long_side, h)
        out_w = int(round(out_h * w / float(h)))
    else:
        out_w = min(long_side, w)
        out_h = int(round(out_w * h / float(w)))
    out_w -= out_w % 2
    out_h -= out_h % 2
    # 24 fps de camara de movil se ve a saltos en redes; como igual
    # re-encodeamos, subir a 30 no cuesta nada.
    if fps < 26:
        fps = 30.0
    return {"width": out_w, "height": out_h, "fps": round(fps, 3), "bg": "#000000"}


def new_timeline(project):
    return {
        "studio_version": TIMELINE_VERSION,
        "name": project.get("name", ""),
        "created_at": _now(),
        "updated_at": _now(),
        "canvas": default_canvas(project),
        "render": dict(DEFAULT_RENDER),
        "styles": {k: dict(v) for k, v in DEFAULT_STYLES.items()},
        "tracks": [
            {"id": "t_sub", "kind": "text", "name": "Subtitulos", "z": 20,
             "hidden": False, "locked": False, "items": []},
            {"id": "t_txt", "kind": "text", "name": "Titulos", "z": 30,
             "hidden": False, "locked": False, "items": []},
            {"id": "t_ovl", "kind": "overlay", "name": "Overlays", "z": 10,
             "hidden": False, "locked": False, "items": []},
            {"id": "t_mus", "kind": "audio", "name": "Musica", "z": 0,
             "hidden": False, "locked": False, "gain": -17.0, "duck": True,
             "items": []},
            {"id": "t_sfx", "kind": "audio", "name": "SFX", "z": 0,
             "hidden": False, "locked": False, "gain": -5.0, "duck": False,
             "items": []},
        ],
        "clips": {},
        "transitions": [],
        "counter": 0,
    }


# --------------------------------------------------------------- io

def path_of(project_dir):
    return Path(project_dir) / "timeline.json"


def load(project_dir, project, create=True):
    tl = util.read_json(path_of(project_dir))
    if tl is None:
        if not create:
            return None
        tl = new_timeline(project)
    return migrate(tl, project)


def save(project_dir, tl):
    tl["updated_at"] = _now()
    return util.write_json(path_of(project_dir), tl, backup=True)


def migrate(tl, project):
    """Completa lo que falte. Un timeline.json a medias sigue abriendo."""
    base = new_timeline(project)
    tl.setdefault("studio_version", TIMELINE_VERSION)
    tl.setdefault("canvas", base["canvas"])
    for k, v in base["canvas"].items():
        tl["canvas"].setdefault(k, v)
    tl.setdefault("render", {})
    for k, v in DEFAULT_RENDER.items():
        tl["render"].setdefault(k, v)
    tl.setdefault("styles", {})
    for k, v in DEFAULT_STYLES.items():
        if k not in tl["styles"]:
            tl["styles"][k] = dict(v)
        else:
            for kk, vv in v.items():
                tl["styles"][k].setdefault(kk, vv)
    tl.setdefault("tracks", base["tracks"])
    have = {t["id"] for t in tl["tracks"]}
    for t in base["tracks"]:
        if t["id"] not in have:
            tl["tracks"].append(t)
    for t in tl["tracks"]:
        t.setdefault("items", [])
        t.setdefault("hidden", False)
        t.setdefault("locked", False)
        t.setdefault("z", 10)
    tl.setdefault("clips", {})
    tl.setdefault("transitions", [])
    tl.setdefault("counter", 0)
    return tl


def new_id(tl, prefix):
    tl["counter"] = int(tl.get("counter") or 0) + 1
    return "%s%04d" % (prefix, tl["counter"])


def track(tl, tid):
    for t in tl["tracks"]:
        if t["id"] == tid:
            return t
    return None


def all_items(tl):
    for t in tl["tracks"]:
        for it in t["items"]:
            yield t, it


def find_item(tl, iid):
    for t, it in all_items(tl):
        if it.get("id") == iid:
            return t, it
    return None, None


# ------------------------------------------------- rutas y maquina local

# Lo que es de esta maquina y no del proyecto: donde viven los originales.
# Va en .gitignore, asi que cada uno tiene el suyo y nunca chocan.
LOCAL_FILE = "local.json"


def _abs(v, pdir):
    if not v:
        return v
    p = Path(v)
    return str(v) if p.is_absolute() else str((Path(pdir) / p).resolve())


def _rel(v, pdir):
    """Relativa si el archivo vive dentro del proyecto; si no, tal cual."""
    if not v:
        return v
    p = Path(v)
    if not p.is_absolute():
        return str(v).replace("\\", "/")
    try:
        return str(p.relative_to(Path(pdir).resolve())).replace("\\", "/")
    except ValueError:
        return str(p)


def resolve_paths(project, pdir):
    """Deja el proyecto con rutas absolutas de ESTA maquina. Muta y devuelve.

    Dos capas: lo que esta commiteado trae rutas relativas al proyecto (los
    proxies, las ondas, las miniaturas), y `local.json` dice donde tiene cada
    maquina el material original. Sin local.json el proyecto abre igual,
    reproduciendo los proxies: es lo que le pasa a quien solo revisa.
    """
    pdir = Path(pdir)
    local = util.read_json(pdir / LOCAL_FILE, {}) or {}
    mios = local.get("sources") or {}
    for s in project.get("sources", []):
        mio = mios.get(s.get("id")) or {}
        original = mio.get("path")
        if original and Path(original).exists():
            s["path"] = original
            s["tiene_original"] = True
        else:
            s["path"] = _abs(s.get("path"), pdir)
            s["tiene_original"] = False
        s["proxy"] = _abs(s.get("proxy"), pdir)
        s["waveform"] = _abs(s.get("waveform"), pdir)
        fs = s.get("filmstrip")
        if isinstance(fs, dict) and fs.get("url"):
            s["filmstrip"] = dict(fs, url=_abs(fs["url"], pdir))
        elif isinstance(fs, str):
            s["filmstrip"] = _abs(fs, pdir)
    return project


def save_project(pdir, project, backup=False):
    """Escribe project.json con las rutas de dentro del proyecto en relativo.

    Lo que quede absoluto es material que vive fuera: eso no se commitea, se
    guarda en `local.json`. Asi el mismo archivo sirve en las dos maquinas.
    """
    pdir = Path(pdir)
    fuera = {}
    salida = dict(project)
    fuentes = []
    for s in project.get("sources", []):
        c = dict(s)
        c.pop("tiene_original", None)
        p = c.get("path")
        if p and Path(p).is_absolute() and Path(pdir).resolve() not in Path(p).parents:
            # El original vive fuera del proyecto: es de esta maquina.
            fuera[c["id"]] = {"path": str(p)}
            c["path"] = _rel(c.get("proxy") or p, pdir)
        else:
            c["path"] = _rel(p, pdir)
        c["proxy"] = _rel(c.get("proxy"), pdir)
        c["waveform"] = _rel(c.get("waveform"), pdir)
        fs = c.get("filmstrip")
        if isinstance(fs, dict) and fs.get("url"):
            c["filmstrip"] = dict(fs, url=_rel(fs["url"], pdir))
        elif isinstance(fs, str):
            c["filmstrip"] = _rel(fs, pdir)
        fuentes.append(c)
    salida["sources"] = fuentes

    if fuera:
        local = util.read_json(pdir / LOCAL_FILE, {}) or {}
        local.setdefault("sources", {}).update(fuera)
        local["maquina"] = local.get("maquina") or os.environ.get("COMPUTERNAME")             or os.environ.get("HOSTNAME") or "?"
        util.write_json(pdir / LOCAL_FILE, local)

    util.write_json(pdir / "project.json", salida, backup=backup)
    return salida


# --------------------------------------------------------------- clips

DEFAULT_CLIP = {
    "speed": 1.0,
    "volume": 0.0,          # dB
    "zoom": None,           # {"kf":[{t,scale,x,y,ease}]}
    "look": None,           # {"brightness","contrast","saturation","temp","vignette"}
    "flip": False,
    "fit": None,            # hereda de render.fit
    "mute": False,
    "gap_before": 0.0,     # espacio negro/silencioso antes del clip
}


def clip_cfg(tl, seg_id):
    """Ajustes de un segmento con los defaults rellenados. No muta el timeline."""
    raw = (tl.get("clips") or {}).get(seg_id) or {}
    cfg = dict(DEFAULT_CLIP)
    cfg.update(raw)
    return cfg


def clip_slot(tl, seg_id):
    """Ajustes de un segmento, creandolos si no existen. Muta el timeline."""
    return tl.setdefault("clips", {}).setdefault(seg_id, {})


def zoom_kfs(cfg):
    z = cfg.get("zoom")
    if not z:
        return []
    kfs = [k for k in (z.get("kf") or []) if isinstance(k, dict)]
    kfs.sort(key=lambda k: float(k.get("t") or 0.0))
    return kfs


def zoom_is_flat(kfs):
    """True si el zoom no hace nada: no vale la pena pagar el filtro."""
    if not kfs:
        return True
    for k in kfs:
        if abs(float(k.get("scale") or 1.0) - 1.0) > 0.002:
            return False
        if abs(float(k.get("x") or 0.0)) > 0.002 or abs(float(k.get("y") or 0.0)) > 0.002:
            return False
    return True


# --------------------------------------------------------------- resolucion

def resolve(project, tl):
    """Traduce las dos capas a algo plano que el render y el editor comparten.

    Devuelve `clips` (en orden, con t0/t1 en tiempo de SALIDA, ya afectados por
    la velocidad), `items` (anclas resueltas, pistas ocultas fuera) y `total`.
    """
    smap = {s["id"]: s for s in project.get("sources", [])}
    clips, t = [], 0.0
    for seg in project.get("segments", []):
        if not seg.get("enabled"):
            continue
        src_dur = max(0.0, float(seg["out"]) - float(seg["in"]))
        if src_dur <= 0.01:
            continue
        cfg = clip_cfg(tl, seg["id"])
        spd = min(max(float(cfg.get("speed") or 1.0), 0.25), 4.0)
        out_dur = src_dur / spd
        gap = max(0.0, float(cfg.get("gap_before") or 0.0))
        t += gap
        clips.append({
            "seg": seg["id"],
            "source": seg["source"],
            "src_name": (smap.get(seg["source"]) or {}).get("name", seg["source"]),
            "in": round(float(seg["in"]), 4),
            "out": round(float(seg["out"]), 4),
            "src_dur": round(src_dur, 4),
            "speed": spd,
            "dur": round(out_dur, 4),
            "gap_before": round(gap, 4),
            "t0": round(t, 4),
            "t1": round(t + out_dur, 4),
            "text": seg.get("text", ""),
            "cfg": cfg,
            "index": len(clips),
        })
        t += out_dur

    total = round(t, 4)
    by_seg = {c["seg"]: c for c in clips}

    # Transiciones: viven en el corte de ENTRADA de un clip. La del primero no
    # tiene corte donde vivir, asi que se ignora (se conserva en el archivo).
    trans = []
    for tr in tl.get("transitions", []):
        c = by_seg.get(tr.get("at_seg"))
        if not c or c["index"] == 0:
            continue
        dur = float(tr.get("dur") or 0.3)
        prev = clips[c["index"] - 1]
        # No puede comerse mas de la mitad de ninguno de los dos clips.
        dur = min(dur, prev["dur"] * 0.9, c["dur"] * 0.9)
        if dur <= 0.02:
            continue
        trans.append({
            "id": tr.get("id"),
            "at_seg": c["seg"],
            "type": tr.get("type") or "flash",
            "t": c["t0"],
            "dur": round(dur, 4),
            "t0": round(max(0.0, c["t0"] - dur / 2.0), 4),
            "t1": round(min(total, c["t0"] + dur / 2.0), 4),
            "strength": float(tr.get("strength") if tr.get("strength") is not None else 1.0),
            "sfx": tr.get("sfx"),
            "sfx_gain": float(tr.get("sfx_gain") if tr.get("sfx_gain") is not None else -5.0),
        })
    trans.sort(key=lambda x: x["t"])

    items = []
    for trk in sorted(tl["tracks"], key=lambda x: x.get("z", 0)):
        if trk.get("hidden"):
            continue
        for it in trk["items"]:
            r = resolve_item(it, trk, by_seg, total)
            if r:
                items.append(r)
    items.sort(key=lambda x: (x["z"], x["t"]))

    return {"clips": clips, "total": total, "items": items,
            "transitions": trans, "canvas": tl["canvas"]}


def resolve_item(it, trk, by_seg, total):
    """Un item con su tiempo absoluto ya calculado, o None si no debe salir."""
    if it.get("hidden"):
        return None
    anchor = it.get("anchor")
    if anchor:
        c = by_seg.get(anchor.get("seg"))
        if not c:
            return None          # su clip esta apagado: el texto se va con el
        t = c["t0"] + float(anchor.get("offset") or 0.0)
        if anchor.get("clamp") is not False:
            t = min(t, max(c["t0"], c["t1"] - 0.02))
    else:
        t = float(it.get("t") or 0.0)
    dur = float(it.get("dur") or 0.0)
    if dur <= 0.01:
        return None
    t = max(0.0, t)
    if t >= total:
        return None
    dur = min(dur, total - t)
    r = dict(it)
    r["t"] = round(t, 4)
    r["dur"] = round(dur, 4)
    r["t_end"] = round(t + dur, 4)
    r["track"] = trk["id"]
    r["track_kind"] = trk["kind"]
    r["z"] = trk.get("z", 10)
    if trk["kind"] == "audio":
        r["track_gain"] = float(trk.get("gain") or 0.0)
        r["duck"] = bool(trk.get("duck"))
    return r


def anchor_at(clips, t):
    """Ancla que corresponde a un tiempo absoluto de la timeline."""
    for c in clips:
        if c["t0"] <= t < c["t1"]:
            return {"seg": c["seg"], "offset": round(t - c["t0"], 4)}
    if clips:
        c = clips[-1]
        return {"seg": c["seg"], "offset": round(max(0.0, t - c["t0"]), 4)}
    return None


# --------------------------------------------------------------- validacion

def validate(project, tl):
    """Devuelve una lista de avisos. Nunca lanza: el proyecto debe abrir igual."""
    warn = []
    segs = {s["id"] for s in project.get("segments", [])}
    for trk, it in all_items(tl):
        a = it.get("anchor")
        if a and a.get("seg") not in segs:
            warn.append("%s: ancla a un segmento que ya no existe (%s)"
                        % (it.get("id"), a.get("seg")))
        if trk["kind"] in ("overlay", "audio") and not it.get("src"):
            warn.append("%s: sin archivo" % it.get("id"))
        if trk["kind"] == "text" and it.get("style") not in tl["styles"]:
            warn.append("%s: estilo desconocido (%s)" % (it.get("id"), it.get("style")))
    for sid in tl.get("clips", {}):
        if sid not in segs:
            warn.append("ajustes de clip huerfanos: %s" % sid)
    for tr in tl.get("transitions", []):
        if tr.get("at_seg") not in segs:
            warn.append("transicion huerfana: %s" % tr.get("id"))
    return warn


def gc(project, tl):
    """Quita lo que apunta a segmentos borrados. Solo cuando se pide."""
    segs = {s["id"] for s in project.get("segments", [])}
    removed = 0
    for trk in tl["tracks"]:
        keep = []
        for it in trk["items"]:
            a = it.get("anchor")
            if a and a.get("seg") not in segs:
                removed += 1
                continue
            keep.append(it)
        trk["items"] = keep
    for sid in list(tl.get("clips", {})):
        if sid not in segs:
            del tl["clips"][sid]
            removed += 1
    before = len(tl.get("transitions", []))
    tl["transitions"] = [t for t in tl["transitions"] if t.get("at_seg") in segs]
    removed += before - len(tl["transitions"])
    return removed
