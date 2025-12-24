import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestConfigAndTracking(unittest.TestCase):
    def setUp(self):
        repo_root = Path(__file__).resolve().parents[1]
        module_path = repo_root / "Headless Test" / "heygen_automation.py"
        self.automation_mod = load_module("heygen_automation", module_path)

        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.tracking_file = self.temp_path / "tracking.json"
        self.config_file = self.temp_path / "config.txt"

        self.automation = self.automation_mod.HeyGenAutomation()
        self.automation.tracking_file = str(self.tracking_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_config(self):
        self.config_file.write_text("available_avatars: Alpha, Beta, Gamma\n", encoding="utf-8")
        avatars = self.automation.load_config()
        self.assertEqual(avatars, ["Alpha", "Beta", "Gamma"])

    def test_tracking_roundtrip(self):
        data = {"session_start": "now", "projects": []}
        ok = self.automation.save_tracking(data)
        self.assertTrue(ok)
        loaded = self.automation.load_tracking()
        self.assertEqual(loaded, data)

    def test_tracking_missing_file(self):
        if self.tracking_file.exists():
            self.tracking_file.unlink()
        loaded = self.automation.load_tracking()
        self.assertIsNone(loaded)


if __name__ == "__main__":
    unittest.main()
