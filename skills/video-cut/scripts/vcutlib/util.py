# -*- coding: utf-8 -*-
"""Utilidades compartidas: ffmpeg/ffprobe, normalizacion de texto, timecodes."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from fractions import Fraction
from pathlib import Path

FFMPEG = os.environ.get("VCUT_FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = os.environ.get("VCUT_FFPROBE") or shutil.which("ffprobe") or "ffprobe"

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".mts", ".m2ts", ".webm",
             ".wmv", ".mpg", ".mpeg", ".3gp", ".flv", ".ts"}
AUDIO_EXT = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma"}
MEDIA_EXT = VIDEO_EXT | AUDIO_EXT

# Codecs que un navegador Chromium reproduce sin proxy.
BROWSER_VIDEO = {"h264", "vp8", "vp9", "av1"}
BROWSER_AUDIO = {"aac", "mp3", "opus", "vorbis", "flac"}
BROWSER_PIXFMT = {"yuv420p", "yuvj420p", "yuv420p10le"}


def eprint(*args):
    print(*args, file=sys.stderr, flush=True)


def run(cmd, check=True, capture=True):
    """Ejecuta un proceso. Devuelve stdout (str) cuando capture=True."""
    cmd = [str(c) for c in cmd]
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
    )
    if check and proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()[-12:]
        raise RuntimeError(
            "Fallo el comando (exit %d):\n  %s\n%s"
            % (proc.returncode, " ".join(cmd[:6]), "\n".join(tail))
        )
    return proc.stdout or ""


def run_bytes(cmd):
    """Ejecuta un proceso y devuelve stdout crudo en bytes."""
    proc = subprocess.run([str(c) for c in cmd], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    if proc.returncode != 0:
        tail = proc.stderr.decode("utf-8", "replace").strip().splitlines()[-12:]
        raise RuntimeError("Fallo el comando:\n%s" % "\n".join(tail))
    return proc.stdout


def probe(path):
    """ffprobe -> dict normalizado con los datos que necesita el pipeline."""
    raw = run([FFPROBE, "-v", "error", "-print_format", "json",
               "-show_format", "-show_streams", str(path)])
    data = json.loads(raw)
    fmt = data.get("format", {}) or {}
    vstreams = [s for s in data.get("streams", [])
                if s.get("codec_type") == "video"
                and (s.get("disposition") or {}).get("attached_pic", 0) != 1]
    astreams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    v = vstreams[0] if vstreams else None
    a = astreams[0] if astreams else None

    dur = _f(fmt.get("duration"))
    if not dur and v:
        dur = _f(v.get("duration"))
    if not dur and a:
        dur = _f(a.get("duration"))

    tags = {k.lower(): val for k, val in (fmt.get("tags") or {}).items()}
    if v:
        for k, val in (v.get("tags") or {}).items():
            tags.setdefault(k.lower(), val)

    fps = 0.0
    if v:
        fps = _rate(v.get("avg_frame_rate")) or _rate(v.get("r_frame_rate")) or 0.0

    info = {
        "duration": round(dur or 0.0, 6),
        "size": int(fmt.get("size") or 0),
        "container": fmt.get("format_name", ""),
        "creation_time": tags.get("creation_time", ""),
        "start_timecode": tags.get("timecode", ""),
        "has_video": v is not None,
        "has_audio": a is not None,
        "vcodec": (v or {}).get("codec_name", ""),
        "pix_fmt": (v or {}).get("pix_fmt", ""),
        "width": int((v or {}).get("width") or 0),
        "height": int((v or {}).get("height") or 0),
        "fps": round(fps, 6),
        "rotation": _rotation(v),
        "acodec": (a or {}).get("codec_name", ""),
        "sample_rate": int((a or {}).get("sample_rate") or 0),
        "channels": int((a or {}).get("channels") or 0),
    }
    if info["rotation"] in (90, 270) and info["width"] and info["height"]:
        info["display_width"], info["display_height"] = info["height"], info["width"]
    else:
        info["display_width"], info["display_height"] = info["width"], info["height"]
    return info


def _f(x):
    try:
        v = float(x)
        return v if v == v and abs(v) != float("inf") else 0.0
    except (TypeError, ValueError):
        return 0.0


def _rate(s):
    if not s or s in ("0/0", "N/A"):
        return 0.0
    try:
        num, _, den = str(s).partition("/")
        den = den or "1"
        return float(num) / float(den) if float(den) else 0.0
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


def _rotation(v):
    if not v:
        return 0
    rot = (v.get("tags") or {}).get("rotate")
    if rot:
        try:
            return int(float(rot)) % 360
        except ValueError:
            pass
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            try:
                return int(-float(sd["rotation"])) % 360
            except (ValueError, TypeError):
                pass
    return 0


def needs_proxy(info):
    """True si el navegador probablemente no pueda reproducir el original."""
    if not info.get("has_video"):
        return True
    if info["vcodec"] not in BROWSER_VIDEO:
        return True
    if info["vcodec"] == "h264" and info["pix_fmt"] not in ("yuv420p", "yuvj420p"):
        return True
    if info["pix_fmt"] and info["pix_fmt"] not in BROWSER_PIXFMT:
        return True
    if info["has_audio"] and info["acodec"] not in BROWSER_AUDIO:
        return True
    # Archivos enormes: el scrub en el navegador sufre aunque el codec sirva.
    if info.get("size", 0) > 1_500_000_000:
        return True
    return False


# ---------------------------------------------------------------- texto

_MARKS = re.compile(r"[̀-ͯ]")
_NONWORD = re.compile(r"[^\w\s]", re.UNICODE)

FILLERS = {
    "eh", "ehh", "ehhh", "em", "emm", "mm", "mmm", "hmm", "ah", "ahh", "este",
    "esteee", "pues", "digamos", "uy", "ay", "uhm", "uh", "erm", "um", "aja",
}
FILLER_PHRASES = {"o sea", "a ver", "es decir", "ya esta", "no se"}


def normalize(text):
    """Minusculas, sin tildes, sin puntuacion, espacios colapsados."""
    text = unicodedata.normalize("NFD", (text or "").lower())
    text = _MARKS.sub("", text)
    text = _NONWORD.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokens(text):
    n = normalize(text)
    return n.split() if n else []


def is_filler_text(text):
    """True si la frase es solo muletillas / ruido sin contenido."""
    toks = tokens(text)
    if not toks:
        return True
    if len(toks) > 4:
        return False
    joined = " ".join(toks)
    if joined in FILLER_PHRASES:
        return True
    return all(t in FILLERS for t in toks)


# ---------------------------------------------------------------- tiempo

def fps_fraction(fps):
    """(numerador, denominador) de la duracion de frame, para FCPXML."""
    if not fps:
        return 1, 30
    common = {23.976: (1001, 24000), 23.98: (1001, 24000), 29.97: (1001, 30000),
              59.94: (1001, 60000), 47.952: (1001, 48000), 119.88: (1001, 120000)}
    for k, val in common.items():
        if abs(fps - k) < 0.01:
            return val
    fr = Fraction(fps).limit_denominator(1000)
    if fr.numerator == 0:
        return 1, 30
    return fr.denominator, fr.numerator


def sec_to_tc(seconds, fps, sep=":"):
    """Timecode no-drop HH:MM:SS:FF."""
    fps_i = max(int(round(fps or 30)), 1)
    total = int(round((seconds or 0) * fps_i))
    ff = total % fps_i
    total //= fps_i
    ss = total % 60
    total //= 60
    mm = total % 60
    hh = total // 60
    return "%02d:%02d:%02d%s%02d" % (hh, mm, ss, sep, ff)


def sec_to_hhmmss(seconds, decimals=2):
    seconds = max(0.0, float(seconds or 0))
    hh = int(seconds // 3600)
    mm = int((seconds % 3600) // 60)
    ss = seconds % 60
    width = decimals + 3 if decimals else 2
    return "%02d:%02d:%0*.*f" % (hh, mm, width, decimals, ss)


def snap_frame(seconds, fps):
    """Alinea un tiempo al frame mas cercano (evita cortes a mitad de frame)."""
    if not fps:
        return round(seconds, 3)
    return round(round(seconds * fps) / fps, 6)


# ---------------------------------------------------------------- io

def read_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def json_dumps(data):
    """El mismo formato que write_json, para escribir dentro de un zip."""
    return json.dumps(data, ensure_ascii=False, indent=2)


def json_loads(text):
    return json.loads(text)


def write_json(path, data, backup=False):
    """Escritura atomica (tmp + replace) para no corromper el proyecto."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if backup and p.exists():
        shutil.copy2(p, p.with_suffix(p.suffix + ".bak"))
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)
    return p


def setup_stdio():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
