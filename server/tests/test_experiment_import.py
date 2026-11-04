import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import jwt
from jinja2 import Environment, FileSystemLoader
from quart import Quart
from werkzeug.datastructures import FileStorage

SERVER_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_DIR = SERVER_DIR.parent
EXAMPLES_DIR = REPOSITORY_DIR / "pcibex_examples"
TEST_JWT_SECRET = "experiment-import-test-secret"
EXPERIMENTS = (
    ("empty-example.zip", "empty-example"),
    ("spr-exmaple.zip", "spr-example"),
)

# db.py reads these when it is imported, even though this test replaces persistence.
os.environ.setdefault("MONGO_USERNAME", "test")
os.environ.setdefault("MONGO_PASSWORD", "test")
os.environ.setdefault("JWT_SECRET_KEY", TEST_JWT_SECRET)
sys.path.insert(0, str(SERVER_DIR))

import auth
import experiments
import pcibex


class ExperimentImportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.public_directory = Path(self.temp_dir.name) / "ibex"
        self.private_directory = self.public_directory / "results"
        self.source_directory = self.public_directory / "source"
        self.source_directory.mkdir(parents=True)

        user_collection = SimpleNamespace(
            find_one=AsyncMock(
                return_value={
                    "_id": "test-user",
                    "username": "test@example.test",
                    "role": "ADMIN",
                }
            )
        )
        self.create_experiment_entry = AsyncMock(return_value=object())
        self.find_experiment_entry = AsyncMock(return_value=None)
        self.patchers = [
            patch.object(auth, "JWT_SECRET", TEST_JWT_SECRET),
            patch.object(auth, "get_user_collection", return_value=user_collection),
            patch.object(
                experiments,
                "PUBLIC_DIRECTORY",
                str(self.public_directory),
            ),
            patch.object(
                experiments,
                "PRIVATE_DIRECTORY",
                str(self.private_directory),
            ),
            patch.object(
                experiments,
                "SOURCE_FILE_DIRECTORY",
                str(self.source_directory),
            ),
            patch.object(
                experiments,
                "jinja_env",
                Environment(
                    loader=FileSystemLoader(str(SERVER_DIR / "templates")),
                    autoescape=True,
                ),
            ),
            patch.object(
                experiments,
                "get_experiment_entry_by_name",
                self.find_experiment_entry,
            ),
            patch.object(
                experiments,
                "create_experiment_entry",
                self.create_experiment_entry,
            ),
            patch.object(
                pcibex,
                "PUBLIC_DIRECTORY",
                str(self.public_directory),
            ),
            patch.object(
                pcibex,
                "PRIVATE_DIRECTORY",
                str(self.private_directory),
            ),
            patch.object(
                pcibex,
                "CHUNK_DIR",
                str(self.public_directory / "chunk_includes"),
            ),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

        self.app = Quart(__name__)
        self.app.register_blueprint(
            experiments.experiments_routes,
            url_prefix="/api/experiments",
        )
        self.app.register_blueprint(pcibex.pcibex_routes)
        self.client = self.app.test_client()

        token = jwt.encode(
            {
                "user_id": "test-user",
                "username": "test@example.test",
                "role": "ADMIN",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            TEST_JWT_SECRET,
            algorithm=auth.JWT_ALGORITHM,
        )
        self.auth_headers = {"Authorization": f"Bearer {token}"}

    async def test_example_experiments_import_and_serve_without_errors(self):
        for archive_name, experiment_name in EXPERIMENTS:
            with self.subTest(experiment=experiment_name):
                archive_path = EXAMPLES_DIR / archive_name
                self.assertTrue(archive_path.is_file(), f"Missing fixture: {archive_path}")

                self.find_experiment_entry.reset_mock()
                self.create_experiment_entry.reset_mock()

                with archive_path.open("rb") as source_zip:
                    response = await self.client.post(
                        "/api/experiments/",
                        form={
                            "name": experiment_name,
                            "tags": "",
                            "redirect_url": "https://example.test/complete",
                        },
                        files={
                            "file": FileStorage(
                                stream=io.BytesIO(source_zip.read()),
                                filename=archive_name,
                                content_type="application/zip",
                            )
                        },
                        headers=self.auth_headers,
                    )

                self.assertEqual(response.status_code, 201, await response.get_data(as_text=True))
                self.assertEqual(
                    await response.get_json(),
                    {"message": "Experiment created successfully"},
                )

                source_copy = self.source_directory / f"temp_{experiment_name}.zip"
                self.assertEqual(source_copy.read_bytes(), archive_path.read_bytes())

                self.find_experiment_entry.assert_awaited_once_with(experiment_name)
                self.create_experiment_entry.assert_awaited_once()
                stored_experiment = self.create_experiment_entry.await_args.args[0]
                self.assertEqual(stored_experiment["name"], experiment_name)
                self.assertEqual(stored_experiment["created_by"], "test-user")

                html_path = self.public_directory / "www" / experiment_name / "index.html"
                self.assertTrue(html_path.is_file())
                generated_html = html_path.read_text(encoding="utf-8")
                self.assertIn(
                    f"data_includes/{experiment_name}/main.js",
                    generated_html,
                )
                self.assertNotIn("global_z.css", generated_html)

                html_response = await self.client.get(
                    f"/www/{experiment_name}/index.html"
                )
                self.assertEqual(html_response.status_code, 200)

                with zipfile.ZipFile(archive_path) as archive:
                    members = [
                        member
                        for member in archive.namelist()
                        if not member.endswith("/")
                        and not PurePosixPath(member).name.startswith(".")
                    ]
                    self.assertIn("data_includes/main.js", members)

                    for member in members:
                        parts = PurePosixPath(member).parts
                        self.assertEqual(len(parts), 2, f"Unexpected fixture path: {member}")
                        folder, filename = parts
                        extracted_file = (
                            self.public_directory / folder / experiment_name / filename
                        )
                        self.assertEqual(extracted_file.read_bytes(), archive.read(member))

                        asset_response = await self.client.get(
                            f"/{folder}/{experiment_name}/{filename}"
                        )
                        self.assertEqual(asset_response.status_code, 200, member)
                        self.assertEqual(await asset_response.get_data(), archive.read(member))

                empty_chunks = await self.client.get(
                    f"/www/{experiment_name}/server.py?allchunks"
                )
                self.assertEqual(empty_chunks.status_code, 200)
                self.assertEqual(await empty_chunks.get_json(), {})

                counter_response = await self.client.get(
                    f"/counter?exp={experiment_name}"
                )
                self.assertEqual(counter_response.status_code, 200)
                self.assertIn("= 0;", await counter_response.get_data(as_text=True))

                result_payload = json.dumps(
                    [False, 1, ["participant_id"], [[[0, "participant-1"]]]]
                )
                with patch.object(
                    pcibex,
                    "get_experiment_entry_by_name",
                    new=AsyncMock(
                        return_value={
                            "name": experiment_name,
                            "redirect_url": "https://example.test/complete",
                        }
                    ),
                ):
                    send_response = await self.client.post(
                        "/send",
                        data=result_payload,
                        headers={
                            "Referer": (
                                f"https://example.test/www/{experiment_name}/index.html"
                            )
                        },
                    )

                self.assertEqual(send_response.status_code, 200)
                self.assertEqual(
                    await send_response.get_json(),
                    {"url": "https://example.test/complete"},
                )
                results_path = self.private_directory / experiment_name / "results"
                self.assertEqual(results_path.read_text(encoding="utf-8").strip(), result_payload)
                counter_path = self.private_directory / experiment_name / "counter"
                self.assertEqual(counter_path.read_text(encoding="utf-8"), "1")

    async def test_generated_html_includes_global_z_css_only_when_present(self):
        experiment_name = "with-global-z"
        css_directory = (
            self.public_directory / "css_includes" / experiment_name
        )
        css_directory.mkdir(parents=True)

        experiments.write_experiment_html(experiment_name)
        html_path = self.public_directory / "www" / experiment_name / "index.html"
        self.assertNotIn("global_z.css", html_path.read_text(encoding="utf-8"))

        (css_directory / "global_z.css").write_text(
            "body { color: rebeccapurple; }",
            encoding="utf-8",
        )
        experiments.write_experiment_html(experiment_name)
        self.assertIn("global_z.css", html_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
