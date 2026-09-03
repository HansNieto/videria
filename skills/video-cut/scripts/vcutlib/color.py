"""Preserve source color by default. Tone mapping is an explicit export choice."""
from functools import lru_cache
from pathlib import Path

from . import util

CACHE_VERSION = "original-v3"
SDR_TAGS = ["-color_primaries", "bt709", "-color_trc", "bt709",
            "-colorspace", "bt709", "-color_range", "tv", "-map_metadata", "-1"]
SDR_PARAMS = "setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709"


@lru_cache(maxsize=256)
def _probe(path, modified, size):
    return util.probe(path)


def metadata(path):
    p = Path(path)
    stat = p.stat()
    return _probe(str(p.resolve()), stat.st_mtime_ns, stat.st_size)


def to_sdr(info):
    """Normalize before 8-bit conversion, compositing or creative looks."""
    transfer = info.get("color_transfer", "")
    primaries = info.get("color_primaries", "")
    if transfer in ("arib-std-b67", "smpte2084"):
        # tonemap works in linear floating-point RGB. zscale reads the input
        # HLG/PQ transfer and BT.2020 matrix, then converts gamut and transfer.
        return ("zscale=transfer=linear:npl=100,format=gbrpf32le,"
                "zscale=primaries=bt709,tonemap=hable:desat=2,"
                "zscale=transfer=bt709:matrix=bt709:range=limited,"
                "format=yuv420p," + SDR_PARAMS)
    if primaries == "bt2020":
        return ("zscale=primaries=bt709:transfer=bt709:matrix=bt709:range=limited,"
                "format=yuv420p," + SDR_PARAMS)
    # SD Rec.601 and full-range inputs need a matrix/range conversion too.
    matrix = info.get("color_space")
    args = "out_color_matrix=bt709:out_range=tv"
    if matrix in ("bt709", "smpte170m", "bt470bg"):
        args += ":in_color_matrix=" + ("bt709" if matrix == "bt709" else "bt601")
    return "scale=" + args + "," + SDR_PARAMS


def profile(info):
    hdr = info.get("color_transfer") in ("arib-std-b67", "smpte2084")
    def known(key, fallback):
        v = info.get(key)
        return v if v and v not in ("unknown", "unspecified", "reserved") else fallback
    return {
        "primaries": known("color_primaries", "bt2020" if hdr else "bt709"),
        "transfer": known("color_transfer", "arib-std-b67" if hdr else "bt709"),
        "matrix": known("color_space", "bt2020nc" if hdr else "bt709"),
        "range": "pc" if info.get("color_range") == "pc" else "tv",
        "hdr": hdr,
        "depth": 10 if hdr or any(x in info.get("pix_fmt", "") for x in ("10", "12", "16")) else 8,
    }


def pixel_format(p):
    return "yuv420p10le" if p["depth"] > 8 else "yuv420p"


def params(p):
    return "setparams=range=%s:color_primaries=%s:color_trc=%s:colorspace=%s" % (
        "full" if p["range"] == "pc" else "limited", p["primaries"], p["transfer"], p["matrix"])


def tags(p):
    return ["-color_primaries", p["primaries"], "-color_trc", p["transfer"],
            "-colorspace", p["matrix"], "-color_range", p["range"], "-map_metadata", "-1"]


def input_filter(path, target=None, mode="original"):
    info = metadata(path)
    if mode == "sdr":
        return to_sdr(info)
    source = profile(info)
    target = target or source
    if any(source[k] != target[k] for k in ("primaries", "transfer", "matrix", "range")):
        raise ValueError("Los clips tienen perfiles de color distintos. Para mezclarlos, "
                         "elige explícitamente «SDR compatible» al exportar.")
    # No eq, LUT, gamut conversion or tone mapping for an original-color clip.
    return "format=" + pixel_format(target) + "," + params(target)


def resource_filter(path, target):
    """Map added SDR artwork into the HDR working space, never grade the camera."""
    if not target["hdr"]:
        return "null"
    info = metadata(path)
    source = profile(info)
    if source["hdr"] and source["transfer"] == target["transfer"]:
        return "null"
    # Explicit input tags are needed for PNGs and other untagged SDR resources.
    # zscale preserves alpha in planar GBR; use 16-bit to keep transparent edges.
    return ("format=gbrap16le,zscale=primariesin=%s:transferin=%s:matrixin=gbr:rangein=full:"
            "primaries=%s:transfer=%s:matrix=%s:range=limited:npl=100"
            % (source["primaries"], source["transfer"], target["primaries"],
               target["transfer"], target["matrix"]))
