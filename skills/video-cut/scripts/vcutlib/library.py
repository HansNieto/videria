# -*- coding: utf-8 -*-
"""Catalogo de assets: SFX, musica y overlays que el editor puede arrastrar.

No hay una carpeta oficial. Se buscan nombres habituales dentro del proyecto y
de sus dos carpetas padre, que es donde la gente deja de verdad los sonidos y
los graficos ("transiciones/audio", "recursos graficos", "musica"). Lo que se
encuentra se sirve por `/api/asset` con la ruta absoluta firmada contra estas
raices: sin eso, el editor podria pedir cualquier archivo del disco.
"""
from __future__ import annotations

from pathlib import Path

AUDIO_EXT = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
VIDEO_EXT = {".webm", ".mov", ".mp4", ".mkv"}
IMAGE_EXT = {".png", ".webp", ".gif", ".jpg", ".jpeg"}

# Carpeta -> categoria. El primer patron que casa manda.
HINTS = [
    ("stickers", "sticker"),
    ("sticker", "sticker"),
    ("audio_reales", "sfx"),
    ("transiciones", "sfx"),
    ("sfx", "sfx"),
    ("efectos", "sfx"),
    ("musica", "musica"),
    ("music", "musica"),
    ("overlay", "overlay"),
    ("motion", "overlay"),
    ("recursos graficos", "overlay"),
    ("graficos", "overlay"),
]

MAX_PER_CAT = 300
MAX_DEPTH = 3


SKILL_ASSETS = Path(__file__).resolve().parent.parent.parent / "assets"


def roots(project_dir):
    """Carpetas donde se busca, de la mas cercana al proyecto a la mas lejana.

    La ultima es la de la skill: ahi viven los stickers, que son de la
    herramienta y valen para todos los proyectos.
    """
    p = Path(project_dir).resolve()
    out = [p, p / "assets"]
    for up in (p.parent, p.parent.parent):
        if up and up.exists() and up != p:
            out.append(up)
    out.append(SKILL_ASSETS)
    seen, uniq = set(), []
    for d in out:
        k = str(d).lower()
        if k not in seen and d.exists():
            seen.add(k)
            uniq.append(d)
    return uniq


def _category(path):
    low = str(path).lower().replace("\\", "/")
    for needle, cat in HINTS:
        if "/%s" % needle in low or low.endswith("/%s" % needle):
            return cat
    ext = path.suffix.lower()
    if ext in AUDIO_EXT:
        return "musica"
    if ext in VIDEO_EXT or ext in IMAGE_EXT:
        return "overlay"
    return None


def _kind(path):
    ext = path.suffix.lower()
    if ext in AUDIO_EXT:
        return "audio"
    if ext in VIDEO_EXT:
        return "video"
    if ext in IMAGE_EXT:
        return "image"
    return None


def scan(project_dir):
    """{categoria: [ {name, path, kind, size, dir} ]}."""
    from . import overlays
    out = {"sfx": [], "musica": [], "overlay": [], "sticker": []}
    index = overlays.seq_index(project_dir)
    seen = set()
    for root in roots(project_dir):
        for path in _walk(root, MAX_DEPTH):
            kind = _kind(path)
            if not kind:
                continue
            key = str(path).lower()
            if key in seen:
                continue
            cat = _category(path)
            if not cat:
                continue
            # Un audio suelto en una carpeta de transiciones es un SFX; uno
            # largo casi nunca lo es.
            if cat == "sfx" and kind != "audio":
                cat = "overlay"
            if len(out[cat]) >= MAX_PER_CAT:
                continue
            seen.add(key)
            try:
                size = path.stat().st_size
            except OSError:
                continue
            entry = {"name": path.name, "path": str(path), "kind": kind,
                     "size": size, "dir": path.parent.name}
            meta = index.get(path.name)
            if meta:
                # Este WebM tiene la secuencia de PNG detras: el render la usa
                # para no perder la transparencia.
                entry["seq"] = meta.get("seq")
                entry["dur"] = meta.get("dur")
                entry["title"] = meta.get("title")
            out[cat].append(entry)
    for cat in out:
        out[cat].sort(key=lambda x: (x["dir"].lower(), x["name"].lower()))
    return out


def _walk(root, depth):
    """Recorrido controlado: nada de bajar por cache/, proxies o node_modules."""
    skip = {"cache", "proxy", "node_modules", ".git", "transcripts", "exports",
            "__pycache__", "filmstrip", "waveform"}
    stack = [(Path(root), 0)]
    while stack:
        d, lvl = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for e in entries:
            if e.is_dir():
                if lvl < depth and e.name.lower() not in skip:
                    stack.append((e, lvl + 1))
            elif e.is_file():
                yield e


def allowed(project_dir, path):
    """True si `path` cae dentro de alguna raiz permitida."""
    try:
        target = Path(path).resolve()
    except OSError:
        return False
    if not target.exists() or not target.is_file():
        return False
    for root in roots(project_dir):
        try:
            target.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False
