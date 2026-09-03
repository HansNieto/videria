import io
import sys
import tempfile
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
