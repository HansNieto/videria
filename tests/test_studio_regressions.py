import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "video-cut" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from vcutlib import server, studio  # noqa: E402


class StudioRegressions(unittest.TestCase):
    def test_gap_before_changes_clip_positions_and_total(self):
        project = {
            "sources": [{"id": "s1", "name": "cam.mov"}],
            "segments": [
                {"id": "a", "source": "s1", "in": 0, "out": 2, "enabled": True},
                {"id": "b", "source": "s1", "in": 2, "out": 4, "enabled": True},
            ],
        }
        timeline = {
            "canvas": {"width": 1080, "height": 1920, "fps": 30},
            "clips": {"b": {"gap_before": 1.5}},
            "tracks": [],
            "transitions": [],
        }
        result = studio.resolve(project, timeline)
        self.assertEqual(result["total"], 5.5)
        self.assertEqual(result["clips"][1]["t0"], 3.5)
        self.assertEqual(result["clips"][1]["gap_before"], 1.5)

    def test_browser_import_is_copied_inside_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = server.create_app(tmp)
            client = app.test_client()
            response = client.post(
                "/api/assets/import",
                data={"file": (io.BytesIO(b"not-a-real-png"), "mi sticker.png")},
                content_type="multipart/form-data",
            )
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            imported = Path(data["asset"]["path"])
            self.assertTrue(imported.is_file())
            self.assertEqual(imported.parent.name, "importados")
            self.assertEqual(data["asset"]["kind"], "image")

    def test_video_import_registers_real_source_for_clip_and_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project.json").write_text(json.dumps({
                "name": "demo", "sources": [], "segments": [], "groups": [],
                "input": {"paths": []}, "stats": {},
            }), encoding="utf-8")

            def fake_source(files, sort_by="name"):
                path = Path(files[0])
                return [{
                    "id": "s001", "index": 1, "name": path.name,
                    "path": str(path), "duration": 3.5, "fps": 30,
                    "width": 1080, "height": 1920, "rotation": 0,
                    "vcodec": "h264", "acodec": "aac", "pix_fmt": "yuv420p",
                    "has_audio": True, "has_video": True, "size": path.stat().st_size,
                    "needs_proxy": False, "proxy": None, "waveform": None,
                    "filmstrip": None,
                }]

            app = server.create_app(root)
            client = app.test_client()
            with mock.patch.object(server.ingest, "build_sources", side_effect=fake_source), \
                 mock.patch.object(server.media, "build_review_proxy",
                                   return_value=root / "cache/proxy/s001.mp4"), \
                 mock.patch.object(server.media, "build_waveform",
                                   return_value=root / "cache/waveform/s001.bin"), \
                 mock.patch.object(server.media, "build_filmstrip",
                                   return_value={"url": str(root / "cache/filmstrip/s001.jpg"),
                                                 "cols": 1, "rows": 1, "count": 1,
                                                 "tw": 28, "th": 48, "interval": 3.5}):
                response = client.post(
                    "/api/assets/import",
                    data={"file": (io.BytesIO(b"fake-mp4"), "clip extra.mp4"),
                          "mode": "clip"},
                    content_type="multipart/form-data",
                )

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data["source"]["name"], "clip_extra.mp4")
            self.assertTrue(data["source"]["has_audio"])
            self.assertTrue(data["source"]["original_embedded"])
            saved = json.loads((root / "project.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["sources"][0]["path"],
                             "assets/importados/clip_extra.mp4")
            self.assertEqual(saved["sources"][0]["proxy"], "cache/proxy/s001.mp4")


if __name__ == "__main__":
    unittest.main()
