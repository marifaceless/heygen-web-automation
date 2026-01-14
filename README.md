# HeyGen Browser Automation

Local UI and automation scripts for submitting and downloading HeyGen videos with a persistent Chrome profile.

## Quick start

macOS:
1. Double-click `heygen.command`.
2. If prompted, log in to HeyGen in the opened Chrome window.
3. The UI opens at http://127.0.0.1:5000.

Windows:
1. Double-click `heygen.bat`.
2. If prompted, log in to HeyGen in the opened Chrome window.
3. The UI opens at http://127.0.0.1:5000.

## Requirements

- Python 3.x
- Playwright installed for Python
- Chrome installed (fallback to bundled Chromium is supported)

## What runs

- `heygen.command` / `heygen.bat`:
  - Ensures the profile exists (runs `Headless Test/setup_profile.py` if missing)
  - Starts the UI server (`Headless Test/ui_server.py`)

## Folder layout

- `Headless Test/heygen_automation.py`: Main automation logic
- `Headless Test/ui_server.py`: Local UI server
- `Headless Test/setup_profile.py`: One-time login/profile setup
- `Headless Test/chrome_profile/`: Persistent Chrome profile storage
- `inputFiles/`: Optional project/scene input folder
- `outputFiles/`: Downloaded video outputs
- `Headless Test/ui_queue.json`: UI submission queue (auto-generated)
- `Headless Test/tracking.json`: Submission/download tracking

## Configuration

- `Headless Test/config.txt`
  - Format: `available_avatars: Name 1, Name 2, Name 3`

## Environment overrides

- `HEYGEN_PYTHON`: Python command used by launchers
- `HEYGEN_BROWSER_CHANNEL`: Browser channel for Playwright (default: `chrome`)
  - Set to `chromium` or `none` to use bundled Chromium
- `HEYGEN_UI_HOST`: UI bind host (default: `127.0.0.1`)
- `HEYGEN_UI_PORT`: UI port (default: `5000`, auto-increments if busy)

## Documentation

- `docs/ARCHITECTURE.md`: System overview and data flow
- `docs/CONFIG.md`: Config and environment reference
- `docs/UI.md`: UI endpoints and payloads
- `docs/RUNBOOK.md`: Troubleshooting and recovery
- `docs/TESTING.md`: Test strategy and commands

## Notes

- `heygen.command` creates/uses a local `.venv` if system Python is externally managed.
- Clipboard permissions are requested automatically to improve paste reliability.
- The automation falls back to direct text insertion if clipboard paste fails.
- UI submissions keep running to auto-download completed videos into `outputFiles/` (Ctrl+C to stop).
