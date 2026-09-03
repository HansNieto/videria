"""One SDR/Rec.709 pipeline for camera originals, preview and export.

Read the actual input, never the project's original metadata when using a
proxy. In particular, an already tone-mapped proxy must not be mapped twice.
"""
from functools import lru_cache
from pathlib import Path

from . import util

CACHE_VERSION = "sdr-hable-v2"
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


def input_filter(path):
    return to_sdr(metadata(path))
