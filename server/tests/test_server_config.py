import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[1]
PACKAGE_SRC_DIR = SERVER_DIR / "src"


class LinuxServerConfigurationTests(unittest.TestCase):
    def test_environment_paths_resolve_under_linux_data_root_outside_repo_cwd(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir) / "pcibex-data"
            env = os.environ.copy()
            env.update(
                {
                    "PYTHONPATH": str(PACKAGE_SRC_DIR),
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PCIBEX_DATA_DIR": str(data_root),
                    "PRIVATE_DIRECTORY": "results",
                    "PUBLIC_DIRECTORY": "",
                    "SOURCE_ZIP_DIRECTORY": "source",
                    "BASE_APPLICATION_URL": "https://pcibex.example.test",
                    "CORS_ALLOWED_ORIGINS": "",
                }
            )
            code = (
                "import json; "
                "from pcibex_server import server_conf as c; "
                "print(json.dumps({"
                "'data': c.DATA_ROOT, "
                "'private': c.PRIVATE_DIRECTORY, "
                "'public': c.PUBLIC_DIRECTORY, "
                "'source': c.SOURCE_ZIP_DIRECTORY, "
                "'base': c.BASE_APPLICATION_URL, "
                "'cors': c.CORS_ALLOWED_ORIGINS"
                "}))"
            )
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=temp_dir,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )

        config = json.loads(result.stdout)
        self.assertEqual(config["data"], str(data_root))
        self.assertEqual(config["private"], str(data_root / "results"))
        self.assertEqual(config["public"], str(data_root))
        self.assertEqual(config["source"], str(data_root / "source"))
        self.assertEqual(config["base"], "https://pcibex.example.test")
        self.assertEqual(config["cors"], [])
        for value in (config["data"], config["private"], config["public"], config["source"]):
            self.assertNotIn("\\", value)


if __name__ == "__main__":
    unittest.main()
