import http.server
import threading
import unittest
from pathlib import Path
import sys
from functools import partial

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        return


class TestClipboardSimulation(unittest.TestCase):
    @unittest.skipUnless(PLAYWRIGHT_AVAILABLE, "Playwright not installed")
    def test_clipboard_paste_into_contenteditable(self):
        html = """
        <html>
          <body>
            <div id=\"editor\" contenteditable=\"true\"></div>
          </body>
        </html>
        """

        with self._serve_html(html) as base_url:
            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch(headless=True)
                except Exception as exc:
                    self.skipTest(f"Playwright browser not installed: {exc}")
                context = browser.new_context()
                context.grant_permissions(["clipboard-read", "clipboard-write"], origin=base_url)
                page = context.new_page()
                page.goto(base_url + "/index.html")
                page.click("#editor")

                test_text = "Clipboard test"
                try:
                    page.evaluate("text => navigator.clipboard.writeText(text)", test_text)
                except Exception:
                    self.skipTest("Clipboard API not available")

                modifier = "Meta" if sys.platform == "darwin" else "Control"
                page.keyboard.press(f"{modifier}+v")
                content = page.eval_on_selector("#editor", "el => el.textContent")

                browser.close()

        self.assertEqual(content, test_text)

    def _serve_html(self, html):
        temp_dir = Path(__file__).parent / "_tmp_clipboard"
        temp_dir.mkdir(exist_ok=True)
        index_path = temp_dir / "index.html"
        index_path.write_text(html, encoding="utf-8")

        handler = partial(QuietHandler, directory=str(temp_dir))

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        class _Context:
            def __enter__(self_inner):
                return f"http://127.0.0.1:{port}"

            def __exit__(self_inner, exc_type, exc, tb):
                server.shutdown()
                thread.join(timeout=2)
                try:
                    index_path.unlink()
                    temp_dir.rmdir()
                except Exception:
                    pass

        return _Context()


if __name__ == "__main__":
    unittest.main()
