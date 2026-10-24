"""Local viewer boundaries and portable packaging; no browser or training needed."""
from http.client import HTTPConnection
import json
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from studies.campaign import viewer


def fixture():
    return {"schema": viewer.SCHEMA, "metadata": {"title": "Test game", "terminal": False},
            "map": {"nodes": {}}, "factions": {}, "initial": {"clock": {}}, "steps": []}


class CampaignViewerTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.path = Path(self.scratch.name) / "recording.json"
        self.path.write_text(json.dumps(fixture()))

    def server(self):
        server = viewer.make_server([self.path], port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server

    def request(self, server, path, *, method="GET", headers=None):
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_only_selected_recordings_and_fixed_assets_are_served(self):
        server = self.server()
        self.assertEqual(server.server_address[0], "127.0.0.1")
        status, headers, body = self.request(server, "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Campaign Observatory", body)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        status, _, body = self.request(server, "/api/replays")
        self.assertEqual(status, 200)
        identity = json.loads(body)["replays"][0]["id"]
        route = f"/api/replays/{identity}"
        status, headers, body = self.request(server, route)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), fixture())
        status, _, body = self.request(server, route, headers={"If-None-Match": headers["ETag"]})
        self.assertEqual((status, body), (304, b""))
        status, headers, body = self.request(server, "/app.js", method="HEAD")
        self.assertEqual((status, body), (200, b""))
        self.assertGreater(int(headers["Content-Length"]), 0)
        for path in ("/AGENTS.md", "/%2e%2e/AGENTS.md", "/api/replays/../../AGENTS.md", "/api/replays/missing"):
            self.assertEqual(self.request(server, path)[0], 404, path)
        self.assertEqual(self.request(server, "/", method="POST")[0], 501)
        self.assertEqual(self.request(server, "/", headers={"Host": "unrelated.example"})[0], 403)

    def test_changed_recording_gets_new_etag(self):
        server = self.server()
        _, _, body = self.request(server, "/api/replays")
        route = "/api/replays/" + json.loads(body)["replays"][0]["id"]
        _, headers, _ = self.request(server, route)
        replay = fixture()
        replay["steps"].append({"changes": {"terminal": True}})
        self.path.write_text(json.dumps(replay))
        status, next_headers, body = self.request(server, route, headers={"If-None-Match": headers["ETag"]})
        self.assertEqual(status, 200)
        self.assertNotEqual(next_headers["ETag"], headers["ETag"])
        self.assertEqual(len(json.loads(body)["steps"]), 1)

    def test_portable_page_embeds_data_without_script_injection_or_external_assets(self):
        replay = fixture()
        replay["metadata"]["title"] = '</script><img src="https://example.invalid/leak">&\u2028'
        page = viewer.standalone_html(replay)
        self.assertNotIn(replay["metadata"]["title"], page)
        self.assertIn(r"\u003c/script\u003e", page)
        self.assertNotIn('src="./app.js"', page)
        self.assertNotIn('href="./style.css"', page)
        self.assertNotRegex(page, r"from\s+['\"]\./model.js")
        scripts = re.findall(r'<script type="module">([\s\S]*?)</script>', page)
        self.assertEqual(len(scripts), 1)
        script = Path(self.scratch.name) / "viewer.mjs"
        script.write_text(scripts[0])
        checked = subprocess.run(["node", "--check", str(script)], capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_portable_export_never_overwrites_existing_file(self):
        output = Path(self.scratch.name) / "viewer.html"
        self.assertEqual(viewer.main(["--replay", str(self.path), "--export-html", str(output)]), 0)
        before = output.read_bytes()
        with self.assertRaises(SystemExit):
            viewer.main(["--replay", str(self.path), "--export-html", str(output)])
        self.assertEqual(output.read_bytes(), before)

    def test_invalid_data_is_rejected_cleanly(self):
        for value in (None, [], {"schema": viewer.SCHEMA, "steps": [], "initial": {}, "map": None}):
            self.path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                viewer.read_replay(self.path)

    def test_live_waiting_following_and_conditional_requests(self):
        class FakeLive:
            revision = 0
            value = None

            def __init__(self, *_args, **_kwargs):
                pass

            def update(self):
                return self.value

        with patch("studies.campaign.replay.LiveReplay", FakeLive):
            server = viewer.make_server([], port=0, live_traces=[self.path])
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        _, _, body = self.request(server, "/api/replays")
        entry = json.loads(body)["replays"][0]
        self.assertTrue(entry["live"])
        route = "/api/replays/" + entry["id"]
        self.assertEqual(self.request(server, route)[0], 503)
        FakeLive.value = fixture()
        FakeLive.revision = 1
        status, headers, body = self.request(server, route)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), fixture())
        self.assertEqual(self.request(server, route, headers={"If-None-Match": headers["ETag"]})[0], 304)
        FakeLive.value["steps"].append({"changes": {"terminal": True}})
        FakeLive.revision = 2
        status, next_headers, body = self.request(server, route, headers={"If-None-Match": headers["ETag"]})
        self.assertEqual(status, 200)
        self.assertNotEqual(next_headers["ETag"], headers["ETag"])
        self.assertEqual(len(json.loads(body)["steps"]), 1)


if __name__ == "__main__":
    unittest.main()
