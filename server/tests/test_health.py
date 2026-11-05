import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from quart import Quart

SERVER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER_DIR / "src"))

from pcibex_server.server import healthz


class HealthCheckTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        app = Quart(__name__)
        app.add_url_rule("/healthz", view_func=healthz, methods=["GET"])
        self.client = app.test_client()

    async def test_health_check_returns_ok_when_database_is_ready(self):
        with patch("pcibex_server.server.ping_db", new=AsyncMock()):
            response = await self.client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(await response.get_json(), {"status": "ok"})

    async def test_health_check_does_not_expose_database_errors(self):
        with patch(
            "pcibex_server.server.ping_db",
            new=AsyncMock(side_effect=RuntimeError("database unavailable")),
        ):
            response = await self.client.get("/healthz")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(await response.get_json(), {"status": "unavailable"})


if __name__ == "__main__":
    unittest.main()
