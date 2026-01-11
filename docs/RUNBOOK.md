# Runbook

## Common issues

### Auto-download runs indefinitely
- UI submissions stay alive until all videos are downloaded.
- Use Ctrl+C to stop the automation manually if needed.

### Python not found
- Install Python 3.x or set `HEYGEN_PYTHON`.

### Playwright not installed
- Run: `python -m pip install playwright`
- Then: `python -m playwright install`

### Chrome not found
- Install Chrome, or set `HEYGEN_BROWSER_CHANNEL=chromium` to use bundled Chromium.

### Clipboard paste fails
- The automation falls back to direct text insert.
- If pastes are still incomplete, try switching to visible mode (`RUN_HEADLESS = False`).

### Stuck on login
- Delete `Headless Test/chrome_profile/` and run the launcher again to re-login.

### Avatar selected but AI Studio doesn't open
- New HeyGen UI shows a **"Use in video"** dialog after selecting an avatar.
- The automation now clicks that dialog first; AI Studio opens immediately if the editor is already visible.
- If the dialog appears but isn't clicked, update selectors in `Headless Test/heygen_automation.py` and re-run.

### Random modal blocks avatar menu
- Some sessions show a full-screen `tw-stack-dialog` rating popup after submissions.
- The automation now dismisses common modal overlays (Esc + Close/Not now/Skip).
- If you still get stuck, capture a screenshot + HTML and update the overlay selectors.

## Safe reset

1. Stop the UI and automation.
2. (Optional) back up `outputFiles/` and `Headless Test/tracking.json`.
3. Delete `Headless Test/chrome_profile/`.
4. Re-run the launcher and log in.
