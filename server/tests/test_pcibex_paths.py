import sys
import tempfile
import unittest
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER_DIR))

from quart import Quart
import pcibex
from utils import extractMediaFilePath, getExperimentFromHeaders, getExperimentNameFromPath


class ExperimentPathHelperTests(unittest.TestCase):
    def test_header_extraction_handles_missing_or_short_paths(self):
        self.assertIsNone(getExperimentFromHeaders(None))
        self.assertIsNone(getExperimentFromHeaders("https://example.test/"))
        self.assertIsNone(getExperimentFromHeaders("https://example.test/www"))
        self.assertEqual(
            getExperimentFromHeaders("https://example.test/www/my-experiment/index.html"),
            "my-experiment",
        )

    def test_request_path_extraction_validates_shape(self):
        self.assertIsNone(getExperimentNameFromPath(None))
        self.assertIsNone(getExperimentNameFromPath("www"))
        self.assertEqual(getExperimentNameFromPath("/www/my-experiment/server.py"), "my-experiment")
        self.assertEqual(getExperimentNameFromPath("www//my-experiment/server.py"), "my-experiment")

    def test_media_path_extraction_validates_shape(self):
        self.assertIsNone(extractMediaFilePath("image.wav"))
        self.assertEqual(extractMediaFilePath("www/my-experiment/audio.wav"), ("my-experiment", "audio.wav"))


class ExperimentRequestRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.old_private_directory = pcibex.PRIVATE_DIRECTORY
        self.old_chunk_dir = pcibex.CHUNK_DIR
        pcibex.PRIVATE_DIRECTORY = self.tempdir.name
        pcibex.CHUNK_DIR = str(Path(self.tempdir.name) / "chunks")
        self.app = Quart(__name__)
        self.app.register_blueprint(pcibex.pcibex_routes)
        self.client = self.app.test_client()

    async def asyncTearDown(self):
        pcibex.PRIVATE_DIRECTORY = self.old_private_directory
        pcibex.CHUNK_DIR = self.old_chunk_dir
        self.tempdir.cleanup()

    async def test_setsquare_uses_request_path_without_referer(self):
        (Path(self.tempdir.name) / "my-experiment").mkdir()
        response = await self.client.get("/www/my-experiment/server.py?setsquare=7")
        self.assertEqual(response.status_code, 200)
        self.assertEqual((Path(self.tempdir.name) / "my-experiment" / "counter").read_text(), "7")

    async def test_allchunks_returns_empty_object_when_chunk_directory_is_absent(self):
        response = await self.client.get("/www/my-experiment/server.py?allchunks")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(await response.get_json(), {})

    async def test_send_rejects_missing_referer_cleanly(self):
        response = await self.client.post("/send", data="[]")
        self.assertEqual(response.status_code, 400)

    async def test_malformed_media_path_returns_404(self):
        response = await self.client.get("/image.wav")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
