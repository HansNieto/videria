"""Prueba manual real: upload MP4 -> fuente, proxy, onda y filmstrip."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "desktop"))
from main import configure_ffmpeg  # noqa: E402

configure_ffmpeg()
from vcutlib import server, util  # noqa: E402

project_dir = ROOT / "build" / "video-import-integration"
project_dir.mkdir(parents=True, exist_ok=True)
incoming = project_dir / "incoming.mp4"
util.run([
    util.FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
    "-f", "lavfi", "-i", "testsrc2=size=360x640:rate=30",
    "-f", "lavfi", "-i", "sine=frequency=523:sample_rate=48000",
    "-t", "1.5", "-c:v", "libx264", "-preset", "ultrafast",
    "-pix_fmt", "yuv420p", "-c:a", "aac", str(incoming),
])
util.write_json(project_dir / "project.json", {
    "name": "integración import", "input": {"paths": []},
    "sequence": {"fps": 30, "width": 1080, "height": 1920},
    "sources": [], "segments": [], "groups": [], "stats": {},
})

client = server.create_app(project_dir).test_client()
with incoming.open("rb") as stream:
    response = client.post(
        "/api/assets/import",
        data={"file": (stream, "clip-con-sonido.mp4"), "mode": "clip"},
        content_type="multipart/form-data",
    )
assert response.status_code == 200, response.get_data(as_text=True)
source = response.get_json()["source"]
assert source["has_audio"] and source["has_video"]
assert Path(source["path"]).is_file()
assert Path(source["proxy"]).is_file()
assert Path(source["waveform"]).is_file()
assert Path(source["filmstrip"]["url"]).is_file()
saved = util.read_json(project_dir / "project.json")
assert saved["sources"][0]["original_embedded"] is True
print("PASS: MP4 real importado con audio, proxy, onda y miniaturas.")
