# -*- coding: utf-8 -*-
"""Recursos graficos: de secuencias de PNG con alfa a overlays usables.

La skill `motion-overlays` deja los overlays como `frames/<nombre>/0000.png`.
Eso no se puede poner en una timeline tal cual, y aqui aparece un reparto de
tareas que conviene entender antes de tocar nada:

* **El preview usa un WebM/VP9 con alfa.** Medido en este equipo: Chrome lo
  reproduce y el canal alfa llega intacto al canvas (esquina 0,0,0,0).
* **El render usa la secuencia de PNG, no el WebM.** Medido tambien: ffmpeg
  *escribe* WebM con alfa pero **no lo lee**; al superponerlo, el overlay sale
  con un rectangulo negro detras. Asi que el item guarda las dos cosas: `src`
  (el WebM, para el editor) y `seq` (la secuencia, para ffmpeg). Si la carpeta
  de frames desaparece, el render avisa y cae al WebM perdiendo el alfa.

Tambien coloca los overlays en el timeline buscando de que habla cada uno: el
`<title>` del HTML original describe la escena, y se compara contra el texto de
los segmentos igual que `analyze` compara tomas repetidas.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path

from . import studio, util

FPS_DEFAULT = 30.0
SEQ_RE = re.compile(r"^(\d{4})\.png$", re.IGNORECASE)
MIN_FRAMES = 4
# Sidecar que deja la conversion dentro de la carpeta de frames, para que la
# secuencia diga por si sola de que habla aunque viaje sin su HTML.
SIDECAR = "_vcut.json"

# Carpetas que no vale la pena recorrer buscando secuencias.
SKIP = {"node_modules", ".git", "__pycache__", "cache", "proxy", "waveform",
        "filmstrip", "transcripts", "exports"}


def find_sequences(roots, max_depth=4, own=None):
    """Carpetas que contienen una secuencia `NNNN.png`.

    Devuelve `{name, dir, frames, first, html, title}`. `name` sale de la
    carpeta; si al lado hay un `.html` con el mismo nombre, se lee su `<title>`
    para saber de que habla el overlay.

    `own` es el proyecto para el que se busca: cualquier otra carpeta que tenga
    un `project.json` se salta entera. Sin eso, un proyecto nuevo creado al lado
    de otro se trae los overlays del vecino, los convierte y luego no sabe donde
    ponerlos.
    """
    out, seen = [], set()
    own = Path(own).resolve() if own else None
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        for d in _walk_dirs(root, max_depth, own):
            key = str(d).lower()
            if key in seen:
                continue
            try:
                # Una carpeta que el sistema no deja leer no puede tumbar el
                # montaje entero: se salta y se sigue.
                frames = sorted(f for f in d.iterdir()
                                if f.is_file() and SEQ_RE.match(f.name))
            except OSError:
                continue
            if len(frames) < MIN_FRAMES:
                continue
            seen.add(key)
            html, title = _source_html(d)
            if not title:
                # Sin el HTML al lado (por ejemplo en un proyecto que llego en
                # un paquete) el titulo se lee del sidecar que dejo la
                # conversion. Sin el, no habria con que buscarle su clip.
                title = (util.read_json(d / SIDECAR, {}) or {}).get("title", "")
            out.append({
                "name": d.name,
                "dir": str(d),
                "frames": len(frames),
                "first": int(SEQ_RE.match(frames[0].name).group(1)),
                "html": str(html) if html else None,
                "title": title,
            })
    out.sort(key=lambda x: x["name"].lower())
    return out


def _walk_dirs(root, depth, own=None):
    stack = [(root, 0)]
    while stack:
        d, lvl = stack.pop()
        yield d
        if lvl >= depth:
            continue
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for e in entries:
            if not e.is_dir() or e.name.lower() in SKIP:
                continue
            if (e / "project.json").exists():
                # Otro proyecto: lo que tenga dentro es suyo.
                if own is None or e.resolve() != own:
                    continue
            stack.append((e, lvl + 1))


def _source_html(seq_dir):
    """El .html del que salio la secuencia, si esta al lado (`frames/<n>/`).

    Devuelve `(ruta, texto)`, donde el texto es el titulo **mas las palabras que
    el overlay muestra en pantalla**. Con el titulo solo no basta: uno que dice
    "lo que hay que definir antes de conectar una IA" y ensena SABER / RESPONDER
    / HABLAR se colocaba sobre la frase que hablaba de "conectar una IA" en vez
    de sobre la que enumera esas tres cosas. Las palabras de pantalla son las
    que de verdad dicen de que va la escena.
    """
    candidates = [seq_dir.parent.parent / ("%s.html" % seq_dir.name),
                  seq_dir.parent / ("%s.html" % seq_dir.name)]
    for c in candidates:
        if not c.exists():
            continue
        try:
            raw = c.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return c, ""
        m = re.search(r"<title>(.*?)</title>", raw, re.S | re.I)
        title = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
        shown = re.findall(r"<(?:text|tspan)\b[^>]*>(.*?)</(?:text|tspan)>",
                           raw, re.S | re.I)
        words = " ".join(re.sub(r"<[^>]+>", " ", s) for s in shown)
        words = re.sub(r"\s+", " ", words).strip()
        return c, (title + " " + words).strip()
    return None, ""


# ------------------------------------------------------------ conversion

def seq_to_webm(seq, out_path, fps=FPS_DEFAULT, crf=30, force=False):
    """Secuencia -> WebM VP9 con alfa. Devuelve (ruta, duracion)."""
    out = Path(out_path)
    dur = round(max(1, seq["frames"] - 1) / float(fps), 3)
    if out.exists() and not force and out.stat().st_size > 2048:
        return out, dur
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp.webm")
    util.run([
        util.FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", "%.4f" % fps,
        "-start_number", str(seq["first"]),
        "-i", str(Path(seq["dir"]) / "%04d.png"),
        # yuva420p es lo que hace que el alfa sobreviva; sin -auto-alt-ref 0
        # libvpx puede tirar el canal alfa en algunos frames.
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
        "-b:v", "0", "-crf", str(crf), "-row-mt", "1",
        "-auto-alt-ref", "0", "-deadline", "good", "-cpu-used", "2",
        "-an", str(tmp),
    ])
    tmp.replace(out)
    return out, dur


def convert_all(project_dir, roots=None, fps=FPS_DEFAULT, force=False,
                on_step=None):
    """Convierte todas las secuencias que encuentre a `<proyecto>/assets/overlays`."""
    from . import library
    project_dir = Path(project_dir)
    dest = project_dir / "assets" / "overlays"
    if roots is None:
        # Primero lo propio. Solo si el proyecto no trae secuencias se busca en
        # las carpetas padre, que es la comodidad del primer uso.
        seqs = find_sequences([project_dir], own=project_dir)
        roots = [project_dir] if seqs else library.roots(project_dir)
    made, vistos = [], set()
    for seq in find_sequences(roots, own=project_dir):
        # Dos carpetas con el mismo nombre acabarian en el mismo WebM: gana la
        # primera, que viene de la raiz mas cercana al proyecto.
        if seq["name"].lower() in vistos:
            continue
        vistos.add(seq["name"].lower())
        if on_step:
            on_step(seq["name"])
        if seq["title"]:
            side = Path(seq["dir"]) / SIDECAR
            if not side.exists():
                util.write_json(side, {"title": seq["title"], "fps": float(fps)})
        out, dur = seq_to_webm(seq, dest / ("%s.webm" % seq["name"]), fps, force=force)
        made.append({"name": seq["name"], "path": str(out), "dur": dur,
                     "frames": seq["frames"], "title": seq["title"],
                     "seq": {"dir": seq["dir"], "first": seq["first"],
                             "fps": float(fps), "frames": seq["frames"]}})
    if made:
        # Indice para que la libreria del editor sepa que WebM tiene secuencia
        # detras: sin esto, arrastrar uno a mano perderia el alfa en el render
        # sin avisar.
        util.write_json(dest / "index.json",
                        {Path(m["path"]).name: {"seq": m["seq"], "dur": m["dur"],
                                                "title": m["title"]}
                         for m in made})
    return made


def seq_index(project_dir):
    """Lo que escribio `convert_all`: nombre de archivo -> {seq, dur, title}."""
    return util.read_json(Path(project_dir) / "assets" / "overlays" / "index.json",
                          {}) or {}


# ------------------------------------------------------------ colocacion

STOP = set("""
a al ante antes como con contra de del desde donde durante en entre hacia hasta
la las lo los mediante para por que se segun sin so sobre tras un una unas uno
unos y o u e es esta estan hay
""".split())


def _keywords(text):
    toks = [t for t in util.tokens(text) if t not in STOP and len(t) > 2]
    return toks


def match_segment(title, project):
    """Segmento cuyo texto habla de lo mismo que el overlay.

    Puntua solape de palabras y, como desempate, la similitud de la cadena.
    Devuelve `(segmento, puntaje)` o `(None, 0)`.
    """
    want = set(_keywords(title))
    if not want:
        return None, 0.0
    nt = util.normalize(title)
    best, best_score = None, 0.0
    for seg in project.get("segments", []):
        if not seg.get("enabled"):
            continue
        got = set(_keywords(seg.get("text", "")))
        if not got:
            continue
        overlap = len(want & got) / float(len(want))
        ratio = SequenceMatcher(None, nt, util.normalize(seg.get("text", ""))).ratio()
        score = overlap * 0.8 + ratio * 0.2
        if score > best_score:
            best, best_score = seg, score
    return best, round(best_score, 3)


def place(project, tl, items, track_id="t_ovl", min_score=0.28, y=0.30,
          scale=None, fade=0.28, replace=True):
    """Pone cada overlay sobre el segmento del que habla.

    `items` son los dicts que devuelve `convert_all`. Los que no encuentran a
    que segmento pertenecer se devuelven en `sin_sitio` para que quien llame
    decida: colocar a ciegas seria peor que no colocar.
    """
    trk = studio.track(tl, track_id)
    if trk is None:
        raise ValueError("no existe la pista %s" % track_id)
    if replace:
        trk["items"] = [it for it in trk["items"] if not it.get("auto")]

    canvas = tl["canvas"]
    res = studio.resolve(project, tl)
    by_seg = {c["seg"]: c for c in res["clips"]}
    placed, orphan = [], []

    for ov in items:
        seg, score = match_segment(ov.get("title") or ov["name"], project)
        clip = by_seg.get(seg["id"]) if seg else None
        if not clip or score < min_score:
            orphan.append({"name": ov["name"], "score": score,
                           "title": ov.get("title")})
            continue
        # Centrado si cabe en el clip. Si dura más, puede continuar encima de
        # los clips siguientes: la pista de overlays es independiente y cortar
        # aquí elimina precisamente el clímax o la salida de la animación.
        dur = float(ov["dur"])
        offset = max(0.0, (clip["dur"] - dur) / 2.0)
        # Solo se limita contra el final real de la secuencia.
        total = float(res.get("duration") or 0.0)
        if total:
            dur = min(dur, max(0.0, total - (clip["t0"] + offset)))
        sc = scale if scale is not None else _fit_scale(ov, canvas)
        item = {
            "id": studio.new_id(tl, "o"),
            "kind": "overlay", "auto": True, "src": ov["path"],
            # La secuencia es la que usa el render: ffmpeg no lee el alfa del
            # WebM, que existe solo para que el editor pueda mostrarlo.
            "seq": ov.get("seq"),
            "anchor": {"seg": clip["seg"], "offset": round(offset, 3)},
            "dur": round(dur, 3),
            "x": 0.5, "y": y, "scale": round(sc, 4),
            "opacity": 1.0, "fade": fade, "loop": False,
        }
        trk["items"].append(item)
        placed.append({"name": ov["name"], "seg": clip["seg"], "score": score,
                       "t": round(clip["t0"] + offset, 2), "dur": item["dur"],
                       "text": (seg.get("text") or "")[:70]})

    trk["items"].sort(key=lambda it: (it.get("anchor") or {}).get("seg", ""))
    return {"colocados": placed, "sin_sitio": orphan}


def content_box(seq, samples=7):
    """Rectangulo que ocupa lo opaco, mirando varios fotogramas.

    Se mide el contenido y no el lienzo porque las escenas de motion-overlays
    son 1920x1080 con el modulo centrado y mucho aire alrededor: escalar por el
    ancho del archivo deja el dibujo diminuto. Se muestrean varios fotogramas
    porque al principio y al final casi todo esta transparente.
    """
    try:
        from PIL import Image
    except ImportError:
        return None
    d = Path(seq["dir"])
    n, first = int(seq.get("frames") or 0), int(seq.get("first") or 0)
    if n < 2:
        return None
    idx = [first + int(round((n - 1) * i / float(samples - 1)))
           for i in range(samples)]
    box = None
    for i in idx:
        f = d / ("%04d.png" % i)
        if not f.exists():
            continue
        try:
            with Image.open(f) as im:
                b = im.convert("RGBA").getchannel("A").getbbox()
        except OSError:
            continue
        if not b:
            continue
        box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]),
                                     max(box[2], b[2]), max(box[3], b[3]))
    return box


def _fit_scale(ov, canvas):
    """Escala para que el CONTENIDO del overlay entre a lo ancho, con margen."""
    seq = ov.get("seq")
    box = content_box(seq) if seq else None
    if box:
        w = max(1, box[2] - box[0])
    else:
        try:
            w = util.probe(ov["path"]).get("width") or 1920
        except (RuntimeError, OSError, ValueError):
            w = 1920
    return round(min(1.4, (int(canvas["width"]) * 0.92) / float(w)), 4)
