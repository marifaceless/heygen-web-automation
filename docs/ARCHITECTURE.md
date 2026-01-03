# Architecture

## Overview

This app provides a local UI that collects scripts and configuration, writes them to a queue file, and launches the automation runner. The automation uses a persistent Chrome profile so you only log in once.

## Data flow

```
User -> UI (Flask) -> ui_queue.json -> heygen_automation.py -> HeyGen web app
                                        -> tracking.json -> outputFiles/
```

## Key modules

- `Headless Test/ui_server.py`
  - Serves the local UI and accepts `/start` submissions.
  - Writes `ui_queue.json` and launches the automation process (submission + auto-download).

- `Headless Test/heygen_automation.py`
  - Opens a persistent browser context and performs HeyGen UI actions.
  - Reads `ui_queue.json` (or inputFiles projects) and updates `tracking.json`.
  - Downloads completed videos into `outputFiles/`.

- `Headless Test/setup_profile.py`
  - Creates the persistent Chrome profile used by the automation.

## Storage and artifacts

- `Headless Test/chrome_profile/`: persistent browser profile
- `Headless Test/ui_queue.json`: UI queue payload
- `Headless Test/tracking.json`: submission/download tracking
- `outputFiles/`: downloaded results
