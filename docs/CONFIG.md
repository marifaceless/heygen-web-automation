# Configuration

## Avatars

`Headless Test/config.txt`

Format:
```
available_avatars: Avatar 1, Avatar 2, Avatar 3
```

The UI reads and updates this file.

## Environment overrides

- `HEYGEN_PYTHON`
  - Python command used by launchers (e.g., `C:\Python311\python.exe`)

- `HEYGEN_BROWSER_CHANNEL`
  - Playwright browser channel (default: `chrome`)
  - Use `chromium` or `none` to fall back to bundled Chromium

## Paths

The automation derives paths from the project root:

- `inputFiles/`: optional input projects
- `outputFiles/`: downloads
- `Headless Test/chrome_profile/`: browser profile storage
- `Headless Test/ui_queue.json`: UI queue file
- `Headless Test/tracking.json`: tracking metadata
