"""Prueba real: blanco SDR de un PNG debe llegar a 75% HLG, no oscuro."""
from pathlib import Path
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "desktop"))
from main import configure_ffmpeg  # noqa: E402

configure_ffmpeg()
from vcutlib import color, util  # noqa: E402

out = ROOT / "build" / "hdr-graphics-white"
out.mkdir(parents=True, exist_ok=True)
png = out / "white-alpha.png"
Image.new("RGBA", (32, 32), (255, 255, 255, 255)).save(png)
hlg = color.profile({
    "color_transfer": "arib-std-b67", "color_primaries": "bt2020",
    "color_space": "bt2020nc", "color_range": "tv",
    "pix_fmt": "yuv420p10le",
})
chain = color.resource_filter(png, hlg) + ",format=yuv420p10le"
raw = util.run_bytes([
    util.FFMPEG, "-hide_banner", "-loglevel", "error", "-i", str(png),
    "-vf", chain, "-frames:v", "1", "-f", "rawvideo", "-",
])
y = np.frombuffer(raw, dtype="<u2")[:32 * 32]
# Limited-range 10-bit: 75% HLG = 64 + .75*(940-64) = 721.
assert 710 <= int(y.max()) <= 730, int(y.max())
print("PASS: graphics white SDR -> HLG 75%% (Y10=%d)." % int(y.max()))
