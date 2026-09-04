# -*- coding: utf-8 -*-
"""Assets para el editor: proxies de preview, waveforms y tiras de miniaturas.

Nada de esto toca el material original: son archivos de apoyo dentro de
`<proyecto>/cache/`. El export final siempre apunta a los archivos de camara.
"""
from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from . import color, util

PEAKS_PER_SEC = 40
THUMB_H = 48
THUMB_COLS = 20
THUMB_MAX = 240
REVIEW_PROXY_VERSION = "browser-sdr-v1"


@lru_cache(maxsize=2)
def nvenc_available(codec="h264"):
    """Prueba un encode real.

    Que `-encoders` liste h264_nvenc no significa que funcione: el driver de la
    maquina puede ser mas viejo que la API que pide este build de ffmpeg.
    """
    try:
        util.run([util.FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
                  "-f", "lavfi", "-i", "color=c=black:s=256x144:r=25:d=0.2",
                  "-pix_fmt", "p010le" if codec == "hevc" else "yuv420p",
                  "-c:v", codec + "_nvenc", "-f", "null", "-"])
        return True
    except (RuntimeError, OSError):
        return False


# ------------------------------------------------------------ proxy

def _proxy_cmd(source, out, height, encoder):
    cmd = [util.FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
           "-i", str(source["path"])]
    p = color.profile({})
    if source.get("has_video"):
        info = color.metadata(source["path"])
        p = color.profile(info)
        high_depth = p["depth"] > 8
        target_h = min(height, info.get("display_height") or height)
        quality = "18" if height >= 1080 else "24"
        if encoder == "nvenc":
            cmd += ["-c:v", "hevc_nvenc" if high_depth else "h264_nvenc", "-preset", "p4", "-rc", "vbr",
                    "-cq", quality, "-b:v", "0"]
        else:
            cmd += ["-c:v", "libx265" if high_depth else "libx264", "-preset", "veryfast", "-crf", quality]
        if high_depth:
            cmd += ["-profile:v", "main10", "-tag:v", "hvc1"]
        # GOP de 1 s: el scrub en el navegador es casi instantaneo.
        cmd += ["-vf", color.input_filter(source["path"]) + ",scale=-2:%d:flags=lanczos" % target_h,
                "-pix_fmt", color.pixel_format(p),
                "-force_key_frames", "expr:gte(t,n_forced*1)",
                "-map", "0:v:0"]
    else:
        cmd += ["-vn"]

    if source.get("has_audio"):
        cmd += ["-map", "0:a:0", "-c:a", "aac", "-b:a", "128k", "-ac", "2"]
    else:
        cmd += ["-an"]

    return cmd + color.tags(p) + ["-movflags", "+faststart", str(out)]


def build_proxy(source, cache_dir, height=540, force=False):
    """Copia ligera sin tone mapping; HDR/10-bit usa HEVC Main10."""
    cache_dir = Path(cache_dir)
    out = cache_dir / "proxy" / ("%s-%s.mp4" % (source["id"], color.CACHE_VERSION))
    if out.exists() and not force and out.stat().st_size > 1024:
        return out
    out.parent.mkdir(parents=True, exist_ok=True)

    p = color.profile(color.metadata(source["path"])) if source.get("has_video") else color.profile({})
    encoders = ["nvenc", "x264"] if nvenc_available("hevc" if p["depth"] > 8 else "h264") else ["x264"]
    last = None
    for enc in encoders:
        try:
            util.run(_proxy_cmd(source, out, height, enc))
            return out
        except RuntimeError as exc:
            last = exc
            if out.exists():
                out.unlink()
            if enc != encoders[-1]:
                util.eprint("    nvenc fallo, reintento con libx264")
    raise RuntimeError("No se pudo generar el proxy de %s: %s" % (source["name"], last))


def build_review_proxy(source, out_dir, height=540, force=False):
    """Proxy H.264/SDR que abre en WebView2 aunque el equipo no tenga HEVC.

    Es exclusivamente para revisar. El render final sigue leyendo el original
    y conserva su perfil HDR cuando se elige «Color original».
    """
    out_dir = Path(out_dir)
    out = out_dir / ("%s-%s.mp4" % (source["id"], REVIEW_PROXY_VERSION))
    if out.exists() and not force and out.stat().st_size > 1024:
        return out
    input_path = Path(source.get("path") or "")
    if not input_path.is_file():
        input_path = Path(source.get("proxy") or "")
    if not input_path.is_file():
        raise RuntimeError("No hay video para crear el proxy compatible de %s" % source["name"])
    info = color.metadata(input_path)
    target_h = min(height, info.get("display_height") or height)
    base = [util.FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(input_path), "-map", "0:v:0",
            "-vf", color.input_filter(input_path, mode="sdr") +
                   ",scale=-2:%d:flags=lanczos" % target_h,
            "-pix_fmt", "yuv420p", "-force_key_frames", "expr:gte(t,n_forced*1)"]
    audio = (["-map", "0:a:0?", "-c:a", "aac", "-b:a", "128k", "-ac", "2"]
             if source.get("has_audio") else ["-an"])
    encoders = ["nvenc", "x264"] if nvenc_available("h264") else ["x264"]
    out.parent.mkdir(parents=True, exist_ok=True)
    last = None
    for encoder in encoders:
        video = (["-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr",
                  "-cq", "24", "-b:v", "0"] if encoder == "nvenc" else
                 ["-c:v", "libx264", "-preset", "veryfast", "-crf", "24"])
        try:
            util.run(base + video + audio + color.SDR_TAGS +
                     ["-movflags", "+faststart", str(out)])
            return out
        except RuntimeError as exc:
            last = exc
            if out.exists():
                out.unlink()
    raise RuntimeError("No se pudo crear el proxy compatible de %s: %s" %
                       (source["name"], last))


# ------------------------------------------------------------ waveform

def build_waveform(source, cache_dir, force=False):
    """Picos de audio en uint8 (40/s) para dibujar la onda en el timeline."""
    import numpy as np

    cache_dir = Path(cache_dir)
    out = cache_dir / "waveform" / ("%s.bin" % source["id"])
    if out.exists() and not force and out.stat().st_size > 0:
        return out
    if not source.get("has_audio"):
        return None

    out.parent.mkdir(parents=True, exist_ok=True)
    rate = 8000
    pcm = util.run_bytes([
        util.FFMPEG, "-hide_banner", "-loglevel", "error",
        "-i", str(source["path"]),
        "-vn", "-ac", "1", "-ar", str(rate), "-f", "s16le", "-",
    ])
    if not pcm:
        return None

    samples = np.frombuffer(pcm, dtype="<i2")
    bucket = max(1, rate // PEAKS_PER_SEC)
    usable = (len(samples) // bucket) * bucket
    if usable == 0:
        return None
    blocks = np.abs(samples[:usable].astype(np.int32)).reshape(-1, bucket)
    peaks = blocks.max(axis=1)
    # Escala perceptual: la raiz levanta los pasajes bajos sin saturar los picos.
    norm = np.sqrt(peaks / 32768.0)
    out.write_bytes((norm * 255).clip(0, 255).astype(np.uint8).tobytes())
    return out


# ------------------------------------------------------------ filmstrip

def build_filmstrip(source, cache_dir, force=False):
    """Sprite sheet de miniaturas para el fondo de los clips del timeline."""
    cache_dir = Path(cache_dir)
    out = cache_dir / "filmstrip" / ("%s.jpg" % source["id"])
    if not source.get("has_video") or not source.get("duration"):
        return None

    w, h = source["width"] or 16, source["height"] or 9
    tw = int(round(THUMB_H * (w / float(h))))
    tw += tw % 2
    tw = max(tw, 8)

    count = min(THUMB_MAX, max(4, int(source["duration"])))
    rows = max(1, -(-count // THUMB_COLS))
    interval = source["duration"] / float(count)
    meta = {"url": None, "cols": THUMB_COLS, "rows": rows, "count": count,
            "tw": tw, "th": THUMB_H, "interval": round(interval, 4)}

    if out.exists() and not force and out.stat().st_size > 1024:
        meta["url"] = str(out)
        return meta

    out.parent.mkdir(parents=True, exist_ok=True)
    vf = color.input_filter(source["path"]) + ",fps=%.6f,scale=%d:%d,tile=%dx%d" % (1.0 / interval, tw, THUMB_H,
                                              THUMB_COLS, rows)
    try:
        util.run([
            util.FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(source["path"]), "-vf", vf,
            "-frames:v", "1", "-q:v", "5", "-update", "1", str(out),
        ])
    except RuntimeError as exc:
        util.eprint("  ! sin filmstrip para %s (%s)" % (source["name"],
                                                        str(exc).splitlines()[0]))
        return None
    meta["url"] = str(out)
    return meta


# ------------------------------------------------------------ orquestacion

def build_all(project, project_dir, force=False, proxy_height=540,
              proxies=True, waveforms=True, filmstrips=True, proxy_all=False):
    """Genera los assets que falten y anota las rutas en el proyecto."""
    cache = Path(project_dir) / "cache"
    for s in project["sources"]:
        label = s["name"]
        if proxies and (proxy_all or s.get("needs_proxy")):
            util.eprint("  proxy   %s" % label)
            s["proxy"] = str(build_proxy(s, cache, proxy_height, force))
        if waveforms and s.get("has_audio"):
            util.eprint("  onda    %s" % label)
            wf = build_waveform(s, cache, force)
            s["waveform"] = str(wf) if wf else None
        if filmstrips and s.get("has_video"):
            util.eprint("  tiras   %s" % label)
            s["filmstrip"] = build_filmstrip(s, cache, force)
    return project
