# Testing

## Test goals

- Validate config and tracking behavior without a browser.
- Validate the UI API contract with real HTTP calls.
- Simulate clipboard and editor behavior where possible.

## Run unit tests

```
python -m unittest discover -s tests
```

## Test coverage

- Config parsing and tracking persistence
- UI server endpoints (`/avatars`, `/start`)
- Queue file creation and automation spawn wiring
- Clipboard/editor simulation (skipped if Playwright is unavailable)

## Notes

- UI HTTP tests start a local server on an ephemeral port.
- Clipboard tests require Playwright and a functional browser install.
