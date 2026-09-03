"""Validated, per-job export settings; never resize the editable project."""
import math


def validate(raw):
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("Opciones de exportación inválidas")
    allowed = {
        "resolution": (0, 720, 1080, 1440, 2160),
        "fps": (0, 23.976, 24, 25, 29.97, 30, 50, 59.94, 60),
        "quality": (16, 18, 20, 23, 28),
        "encoder": ("auto", "x264", "nvenc"),
        "audio_bitrate": ("128k", "192k", "320k"),
        "color_mode": ("original", "sdr"),
    }
    result = {}
    for key, values in allowed.items():
        if key not in raw:
            continue
        value = raw[key]
        if isinstance(value, bool) or value not in values:
            raise ValueError("Valor no válido para " + key)
        result[key] = value
    if set(raw) - set(allowed):
        raise ValueError("Opción de exportación desconocida")
    return result


def canvas_for(canvas, options):
    result = dict(canvas)
    short = options.get("resolution", 0)
    if short:
        scale = short / min(canvas["width"], canvas["height"])
        for key in ("width", "height"):
            result[key] = max(2, round(canvas[key] * scale / 2) * 2)
        if max(result["width"], result["height"]) > 7680:
            raise ValueError("La proporción del lienzo excede el tamaño permitido")
    if options.get("fps"):
        result["fps"] = options["fps"]
    if not all(math.isfinite(float(result[k])) and result[k] > 0
               for k in ("width", "height", "fps")):
        raise ValueError("Lienzo inválido")
    return result
