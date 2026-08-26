# -*- coding: utf-8 -*-
"""Tipografia: encontrar fuentes, medirlas y partir el texto en lineas.

Aca vive el reparto de palabras en lineas y de lineas en tarjetas. Lo hace el
servidor con las metricas reales del .ttf (PIL), no el navegador, para que el
reparto sea el mismo en el preview y en el render: el editor y ffmpeg reciben
las lineas ya calculadas y ninguno de los dos vuelve a partir nada.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from . import util

# Donde buscar .ttf/.otf, en orden de preferencia. La carpeta del proyecto gana
# para que un proyecto pueda traer su propia tipografia.
def font_dirs(project_dir=None):
    dirs = []
    if project_dir:
        dirs.append(Path(project_dir) / "fonts")
    env = os.environ.get("VCUT_FONTS")
    if env:
        dirs += [Path(p) for p in env.split(os.pathsep) if p]
    dirs += [
        Path(__file__).resolve().parent.parent.parent / "assets" / "fonts",
        Path.home() / "MoneyPrinterTurbo" / "resource" / "fonts",
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
        Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts",
        Path("/usr/share/fonts"),
        Path.home() / ".local" / "share" / "fonts",
    ]
    return [d for d in dirs if d.exists()]


FONT_EXT = (".ttf", ".otf", ".ttc")
_CACHE = {}
_LIST = {}


def find_font(name, project_dir=None):
    """Ruta de una fuente por nombre de archivo o por familia aproximada."""
    if not name:
        name = "Inter-Black.ttf"
    key = (str(name).lower(), str(project_dir or ""))
    if key in _CACHE:
        return _CACHE[key]
    want = Path(str(name)).name.lower()
    stem = Path(want).stem.lower().replace(" ", "").replace("-", "").replace("_", "")
    exact = None
    loose = None
    for d in font_dirs(project_dir):
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for f in entries:
            if not f.is_file() or f.suffix.lower() not in FONT_EXT:
                continue
            fn = f.name.lower()
            if fn == want:
                exact = f
                break
            fs = f.stem.lower().replace(" ", "").replace("-", "").replace("_", "")
            if loose is None and (fs == stem or stem in fs):
                loose = f
        if exact:
            break
    hit = exact or loose
    if hit is None:
        # Ultimo recurso: algo que exista, para no romper el render por una
        # fuente que falta. El aviso lo da quien llama.
        for d in font_dirs(project_dir):
            for f in d.iterdir():
                if f.is_file() and f.suffix.lower() in FONT_EXT:
                    hit = f
                    break
            if hit:
                break
    _CACHE[key] = hit
    return hit


def list_fonts(project_dir=None, limit=400):
    """Fuentes disponibles para el selector del editor."""
    key = str(project_dir or "")
    if key in _LIST:
        return _LIST[key]
    seen, out = set(), []
    for d in font_dirs(project_dir):
        try:
            entries = sorted(d.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            continue
        for f in entries:
            if not f.is_file() or f.suffix.lower() not in FONT_EXT:
                continue
            if f.name.lower() in seen:
                continue
            seen.add(f.name.lower())
            out.append({"file": f.name, "label": _label(f.stem), "dir": str(d)})
            if len(out) >= limit:
                break
        if len(out) >= limit:
            break
    # Las de MoneyPrinterTurbo / del proyecto son las utiles: van primero.
    prio = ("Inter", "InterDisplay", "Anton", "BebasNeue", "BeVietnamPro",
            "DancingScript", "Charm", "UTM")
    out.sort(key=lambda x: (0 if x["file"].startswith(prio) else 1, x["file"].lower()))
    _LIST[key] = out
    return out


def _label(stem):
    s = re.sub(r"[-_]+", " ", stem)
    return re.sub(r"\s+", " ", s).strip()


# ------------------------------------------------------------ metricas

class Face:
    """Una fuente a un cuerpo concreto, con las medidas que necesitamos."""

    def __init__(self, path, size):
        from PIL import ImageFont
        self.path = str(path)
        self.size = float(size)
        self.font = ImageFont.truetype(self.path, max(1, int(round(size))))
        asc, desc = self.font.getmetrics()
        self.ascent = float(asc)
        self.descent = float(desc)

    def width(self, text, spacing=0.0):
        if not text:
            return 0.0
        w = float(self.font.getlength(text))
        if spacing:
            w += spacing * max(0, len(text) - 1)
        return w


_FACES = {}


def face(font_name, size, project_dir=None):
    path = find_font(font_name, project_dir)
    key = (str(path), round(float(size), 2))
    f = _FACES.get(key)
    if f is None:
        f = Face(path, size)
        _FACES[key] = f
    return f


# ------------------------------------------------------------ reparto

STOP = set("""
a al algo alguna algunas alguno algunos ante antes aqui asi aun aunque bien
cada casi como con contra cual cuales cuando cuanto de del desde donde dos el
ella ellas ello ellos en entre era eran es esa esas ese eso esos esta estan
estas este esto estos fue fueron ha haber habia hace hacer hasta hay la las le
les lo los mas me mi mientras muy nada ni no nos nosotros o os otra otras otro
otros para pero poco por porque pues que quien quienes se sea segun ser si sido
sin sobre solo somos son su sus tan tanto te tiene tienen todo todos tu tus un
una uno unos usted ustedes vamos ya yo
""".split())

_PUNCT_END = re.compile(r"[.!?]+[\"'\u201d\u00bb)]*\s*$")
_NUMISH = re.compile(r"[\d%$]")


def is_sentence_end(word):
    return bool(_PUNCT_END.search(word or ""))


def pick_keyword(words):
    """Palabra a resaltar en una tarjeta. Heuristica, editable en el editor.

    Prefiere cifras y porcentajes (es lo que la gente busca con la vista) y
    luego la palabra larga con mas contenido. Devuelve el indice o None.
    """
    best, best_score = None, 0.0
    for i, w in enumerate(words):
        raw = (w.get("w") or "").strip()
        clean = re.sub(r"[^\w%$]", "", raw, flags=re.UNICODE)
        if not clean:
            continue
        low = util.normalize(clean)
        if not low or low in STOP:
            continue
        score = len(clean) * 1.0
        if _NUMISH.search(clean):
            score += 12
        if clean[:1].isupper() and i > 0:
            score += 3
        if len(clean) <= 3:
            score -= 4
        if score > best_score:
            best, best_score = i, score
    return best if best_score >= 5 else None


def wrap(words, style, canvas_w, key_idx=None, project_dir=None):
    """Reparte palabras en lineas respetando ancho, palabras y caracteres.

    `words` son dicts {w, s, e}. Devuelve lista de lineas; cada linea es una
    lista de dicts {w, s, e, key}.
    """
    scale = canvas_w / 1080.0
    size = float(style.get("size") or 80) * scale
    spacing = float(style.get("letter_spacing") or 0) * scale
    max_w = float(style.get("box", {}).get("w") or 0.86) * canvas_w
    max_words = int(style.get("max_words_line") or 4)
    max_chars = int(style.get("max_chars_line") or 22)

    base = face(style.get("font"), size, project_dir)
    kf = face(style.get("keyword_font") or style.get("font"),
              size * float(style.get("keyword_size_ratio") or 1.0), project_dir)
    space_w = base.width(" ", spacing)

    lines, cur, cur_w, cur_chars = [], [], 0.0, 0
    for i, w in enumerate(words):
        txt = (w.get("w") or "").strip()
        if not txt:
            continue
        is_key = (key_idx is not None and i == key_idx)
        ww = (kf if is_key else base).width(txt, spacing)
        add = ww + (space_w if cur else 0.0)
        over = (cur and (cur_w + add > max_w
                         or len(cur) >= max_words
                         or cur_chars + 1 + len(txt) > max_chars))
        if over:
            lines.append(cur)
            cur, cur_w, cur_chars = [], 0.0, 0
            add = ww
        cur.append({"w": txt, "s": w.get("s"), "e": w.get("e"), "key": is_key})
        cur_w += add
        cur_chars += len(txt) + (1 if cur_chars else 0)
    if cur:
        lines.append(cur)
    return lines


def line_metrics(lines, style, canvas_w, project_dir=None):
    """Alto y ancho de cada linea, y el alto total del bloque.

    Es lo que usan el generador de ASS y el fondo de las notas. El preview
    calcula lo mismo en el navegador con la misma fuente y el mismo cuerpo.
    """
    scale = canvas_w / 1080.0
    size = float(style.get("size") or 80) * scale
    spacing = float(style.get("letter_spacing") or 0) * scale
    lh = float(style.get("line_height") or 1.16)
    ratio = float(style.get("keyword_size_ratio") or 1.0)
    base = face(style.get("font"), size, project_dir)
    kf = face(style.get("keyword_font") or style.get("font"), size * ratio, project_dir)
    space_w = base.width(" ", spacing)

    out, total = [], 0.0
    for ln in lines:
        w = 0.0
        big = size
        for j, word in enumerate(ln):
            f = kf if word.get("key") else base
            w += f.width(word["w"], spacing) + (space_w if j else 0.0)
            if word.get("key"):
                big = max(big, size * ratio)
        h = big * lh
        out.append({"w": round(w, 2), "h": round(h, 2), "size": round(big, 2)})
        total += h
    return {"lines": out, "total_h": round(total, 2), "size": round(size, 2),
            "space_w": round(space_w, 2)}
