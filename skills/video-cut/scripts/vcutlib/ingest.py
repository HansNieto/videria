# -*- coding: utf-8 -*-
"""Descubre los archivos de la carpeta, los ordena y saca metadatos."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from . import util


def _natural_key(name):
    """Orden natural: clip2 < clip10 (no alfabetico puro)."""
    parts = re.split(r"(\d+)", name.lower())
    return [int(p) if p.isdigit() else p for p in parts]


def _parse_creation(info, path):
    """Fecha de grabacion: tag del contenedor, si no el mtime del archivo."""
    raw = (info.get("creation_time") or "").strip()
    if raw:
        txt = raw.replace("Z", "+00:00")
        for fmt in (None, "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.fromisoformat(txt) if fmt is None \
                    else datetime.strptime(txt[:19], fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.timestamp(), raw
            except ValueError:
                continue
    st = Path(path).stat()
    ts = min(st.st_mtime, getattr(st, "st_ctime", st.st_mtime))
    return ts, datetime.fromtimestamp(ts, timezone.utc).isoformat()


def discover(inputs, recursive=False, pattern=None):
    """Devuelve la lista de archivos multimedia a partir de carpetas/archivos."""
    found = []
    for item in inputs:
        p = Path(item).expanduser()
        if p.is_dir():
            it = p.rglob("*") if recursive else p.glob("*")
            for f in it:
                if f.is_file() and f.suffix.lower() in util.MEDIA_EXT:
                    found.append(f)
        elif p.is_file():
            found.append(p)
        else:
            matches = sorted(Path().glob(str(p)))
            if not matches:
                raise FileNotFoundError("No existe: %s" % p)
            found.extend(m for m in matches if m.is_file())
    if pattern:
        rx = re.compile(pattern, re.IGNORECASE)
        found = [f for f in found if rx.search(f.name)]
    # Sin duplicados, preservando el orden de aparicion.
    seen, unique = set(), []
    for f in found:
        key = str(f.resolve()).lower()
        if key not in seen:
            seen.add(key)
            unique.append(f.resolve())
    return unique


def build_sources(files, sort_by="name"):
    """Sondea cada archivo, ordena y devuelve la lista de sources del proyecto."""
    entries = []
    for f in files:
        try:
            info = util.probe(f)
        except RuntimeError as exc:
            util.eprint("  ! omito %s (%s)" % (f.name, str(exc).splitlines()[0]))
            continue
        if info["duration"] <= 0:
            util.eprint("  ! omito %s (duracion 0)" % f.name)
            continue
        ts, iso = _parse_creation(info, f)
        entries.append({"path": f, "info": info, "ts": ts, "iso": iso})

    if sort_by == "date":
        entries.sort(key=lambda e: (e["ts"], _natural_key(e["path"].name)))
    elif sort_by == "none":
        pass
    else:
        entries.sort(key=lambda e: _natural_key(e["path"].name))

    sources = []
    for i, e in enumerate(entries, 1):
        info = e["info"]
        sources.append({
            "id": "s%03d" % i,
            "index": i,
            "name": e["path"].name,
            "path": str(e["path"]),
            "duration": info["duration"],
            "fps": info["fps"] or 30.0,
            "width": info["display_width"],
            "height": info["display_height"],
            "rotation": info["rotation"],
            "vcodec": info["vcodec"],
            "acodec": info["acodec"],
            "pix_fmt": info["pix_fmt"],
            "has_audio": info["has_audio"],
            "has_video": info["has_video"],
            "size": info["size"],
            "start_timecode": info["start_timecode"] or "00:00:00:00",
            "recorded_at": e["iso"],
            "recorded_ts": e["ts"],
            "needs_proxy": util.needs_proxy(info),
            "proxy": None,
            "waveform": None,
            "filmstrip": None,
        })
    return sources


def sequence_fps(sources):
    """FPS dominante del lote (el mas frecuente, desempata el mayor)."""
    counts = {}
    for s in sources:
        if s["fps"]:
            key = round(s["fps"], 3)
            counts[key] = counts.get(key, 0) + 1
    if not counts:
        return 30.0
    return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]


def sequence_size(sources):
    """Resolucion dominante del lote."""
    counts = {}
    for s in sources:
        if s["width"] and s["height"]:
            key = (s["width"], s["height"])
            counts[key] = counts.get(key, 0) + 1
    if not counts:
        return 1920, 1080
    return max(counts.items(), key=lambda kv: (kv[1], kv[0][0] * kv[0][1]))[0]
