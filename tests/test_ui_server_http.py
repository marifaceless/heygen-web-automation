import importlib.util
import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path

from werkzeug.serving import make_server


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DummyProcess:
    def __init__(self, args, cwd=None):
        self.args = args
        self.cwd = cwd
        self.pid = 12345


class UIServerHarness:
    def __init__(self, app):
        self.app = app
        self.server = None
        self.thread = None
        self.port = None

    def start(self):
        self.server = make_server("127.0.0.1", 0, self.app)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=2)


class TestUIServerHTTP(unittest.TestCase):
    def setUp(self):
        repo_root = Path(__file__).resolve().parents[1]
        module_path = repo_root / "Headless Test" / "ui_server.py"
        self.ui_server = load_module("ui_server", module_path)

        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        self.ui_server.SCRIPT_DIR = str(self.temp_path)
        self.ui_server.QUEUE_FILE = str(self.temp_path / "ui_queue.json")
        self.ui_server.HEYGEN_SCRIPT = str(self.temp_path / "heygen_automation.py")
        self.ui_server.subprocess.Popen = DummyProcess

        self._write_config("available_avatars: Alpha, Beta\n")

        self.harness = UIServerHarness(self.ui_server.app)
        self.harness.start()

    def tearDown(self):
        self.harness.stop()
        self.temp_dir.cleanup()

    def _write_config(self, content):
        config_path = self.temp_path / "config.txt"
        config_path.write_text(content, encoding="utf-8")

    def _request(self, method, path, payload=None):
        url = f"http://127.0.0.1:{self.harness.port}{path}"
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)

    def test_avatars_get(self):
        status, data = self._request("GET", "/avatars")
        self.assertEqual(status, 200)
        self.assertEqual(data["avatars"], ["Alpha", "Beta"])

    def test_avatars_add_delete(self):
        status, data = self._request("POST", "/avatars", {"name": "Gamma"})
        self.assertEqual(status, 200)
        self.assertIn("Gamma", data["avatars"])

        status, data = self._request("DELETE", "/avatars", {"name": "Gamma"})
        self.assertEqual(status, 200)
        self.assertNotIn("Gamma", data["avatars"])

    def test_start_valid_payload(self):
        payload = {
            "avatar": "Alpha",
            "project_name": "Test Project",
            "items": [
                {"title": "Scene 1", "script": "Hello world"}
            ],
            "config": {"quality": "720p", "fps": "25", "subtitles": "yes"},
        }
        status, data = self._request("POST", "/start", payload)
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        queue_file = Path(self.ui_server.QUEUE_FILE)
        self.assertTrue(queue_file.exists())
        saved = json.loads(queue_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["avatar"], "Alpha")
        self.assertEqual(saved["project_name"], "Test Project")
        self.assertEqual(len(saved["items"]), 1)

    def test_start_missing_avatar(self):
        payload = {
            "project_name": "Test Project",
            "items": [{"title": "Scene 1", "script": "Hello world"}],
        }
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._request("POST", "/start", payload)
        self.assertEqual(ctx.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
