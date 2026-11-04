import asyncio
import io
import os
import shutil
import socket
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.request import urlopen
from unittest.mock import AsyncMock, patch

import jwt
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright
from quart import Quart
from werkzeug.datastructures import FileStorage

SERVER_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_DIR = SERVER_DIR.parent
EXAMPLES_DIR = REPOSITORY_DIR / "pcibex_examples"
RUNTIME_DIR = SERVER_DIR / "tests" / "fixtures" / "pcibex-runtime"
TEST_JWT_SECRET = "experiment-execution-test-secret"
EXPERIMENTS = (
    ("empty-example.zip", "empty-example"),
    ("spr-exmaple.zip", "spr-example"),
)

os.environ.setdefault("MONGO_USERNAME", "test")
os.environ.setdefault("MONGO_PASSWORD", "test")
os.environ.setdefault("JWT_SECRET_KEY", TEST_JWT_SECRET)
sys.path.insert(0, str(SERVER_DIR))

import auth
import experiments
import pcibex


class ExperimentExecutionSmokeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.public_directory = Path(self.temp_dir.name) / "ibex"
        self.private_directory = self.public_directory / "results"
        self.source_directory = self.public_directory / "source"
        self.source_directory.mkdir(parents=True)

        for directory in ("www", "css_includes", "other_includes"):
            shutil.copytree(RUNTIME_DIR / directory, self.public_directory / directory)

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
        self.patchers = [
            patch.object(auth, "JWT_SECRET", TEST_JWT_SECRET),
            patch.object(auth, "get_user_collection", return_value=user_collection),
            patch.object(experiments, "PUBLIC_DIRECTORY", str(self.public_directory)),
            patch.object(experiments, "PRIVATE_DIRECTORY", str(self.private_directory)),
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
                AsyncMock(return_value=None),
            ),
            patch.object(
                experiments,
                "create_experiment_entry",
                self.create_experiment_entry,
            ),
            patch.object(pcibex, "PUBLIC_DIRECTORY", str(self.public_directory)),
            patch.object(pcibex, "PRIVATE_DIRECTORY", str(self.private_directory)),
            patch.object(
                pcibex,
                "CHUNK_DIR",
                str(self.public_directory / "chunk_includes"),
            ),
            patch.object(
                pcibex,
                "get_experiment_entry_by_name",
                AsyncMock(
                    side_effect=lambda name: {
                        "name": name,
                        "redirect_url": "https://example.test/complete",
                    }
                ),
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

        with socket.socket() as port_socket:
            port_socket.bind(("127.0.0.1", 0))
            self.port = port_socket.getsockname()[1]
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.server_task = None

    async def asyncTearDown(self):
        if self.server_task is not None:
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass

    async def _import_example(self, archive_name, experiment_name):
        archive_path = EXAMPLES_DIR / archive_name
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
        self.assertEqual(
            response.status_code,
            201,
            await response.get_data(as_text=True),
        )

    async def _advance_dashed_sentence(self, page, next_button):
        for _ in range(100):
            if await next_button.is_visible():
                return
            await page.keyboard.press("Space")
            await page.wait_for_timeout(20)
        self.fail("DashedSentence did not finish after 100 spacebar presses")

    async def _wait_for_server(self):
        counter_url = f"{self.base_url}/counter?exp=empty-example"

        def probe():
            with urlopen(counter_url, timeout=1):
                return

        for _ in range(50):
            try:
                await asyncio.to_thread(probe)
                return
            except OSError:
                await asyncio.sleep(0.1)
        self.fail("The experiment test server did not start")

    async def test_examples_execute_and_submit_results_in_chromium(self):
        for archive_name, experiment_name in EXPERIMENTS:
            with self.subTest(experiment=experiment_name):
                await self._import_example(archive_name, experiment_name)

        self.server_task = asyncio.create_task(
            self.app.run_task(
                host="127.0.0.1",
                port=self.port,
                debug=False,
                use_reloader=False,
            )
        )
        await self._wait_for_server()

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                empty_page = await browser.new_page()
                await empty_page.goto(
                    f"{self.base_url}/www/empty-example/index.html",
                    wait_until="load",
                )
                hello_button = empty_page.get_by_role("button", name="Hello World")
                await hello_button.wait_for(state="visible", timeout=10_000)

                async with empty_page.expect_response(
                    lambda response: (
                        response.request.method == "POST"
                        and response.url.endswith("/server.py")
                    ),
                    timeout=10_000,
                ) as empty_submission:
                    await hello_button.click()

                self.assertEqual((await empty_submission.value).status, 200)
                await empty_page.get_by_text(
                    "The results were successfully sent to the server."
                ).wait_for(state="visible", timeout=10_000)
                empty_results = (
                    self.private_directory / "empty-example" / "results"
                ).read_text(encoding="utf-8")
                self.assertTrue(empty_results.strip())

                spr_page = await browser.new_page()
                await spr_page.goto(
                    f"{self.base_url}/www/spr-example/index.html",
                    wait_until="load",
                )
                await spr_page.locator("input").fill("smoke-test-participant")
                await spr_page.get_by_role("button", name="Start").click()
                await spr_page.get_by_role(
                    "button",
                    name="Start reading",
                ).click()
                await spr_page.locator(".sentence").wait_for(
                    state="visible",
                    timeout=10_000,
                )

                next_sentence_button = spr_page.get_by_role(
                    "button",
                    name="Next sentence please!",
                )
                await self._advance_dashed_sentence(spr_page, next_sentence_button)
                await next_sentence_button.click()
                await spr_page.locator(".sentence").wait_for(
                    state="visible",
                    timeout=10_000,
                )

                done_button = spr_page.get_by_role("button", name="I'm done")
                await self._advance_dashed_sentence(spr_page, done_button)

                async with spr_page.expect_response(
                    lambda response: (
                        response.request.method == "POST"
                        and response.url.endswith("/server.py")
                    ),
                    timeout=10_000,
                ) as spr_submission:
                    await done_button.click()

                self.assertEqual((await spr_submission.value).status, 200)
                await spr_page.get_by_text(
                    "Thank you for your participation!"
                ).wait_for(state="visible", timeout=10_000)
                spr_results = (
                    self.private_directory / "spr-example" / "results"
                ).read_text(encoding="utf-8")
                self.assertTrue(spr_results.strip())
                self.assertIn(
                    "smoke-test-participant",
                    spr_results,
                )
            finally:
                await browser.close()


if __name__ == "__main__":
    unittest.main()
