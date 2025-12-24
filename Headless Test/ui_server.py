"""Local UI server for creating and submitting HeyGen automation queues."""

import json
import os
import sys
import subprocess
import threading
import webbrowser

try:
    from flask import Flask, render_template, request, jsonify
except ImportError:
    print("Flask is not installed. Run: python3 -m pip install flask")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
QUEUE_FILE = os.path.join(SCRIPT_DIR, "ui_queue.json")
HEYGEN_SCRIPT = os.path.join(SCRIPT_DIR, "heygen_automation.py")

app = Flask(__name__, static_folder="ui_static", template_folder="ui_templates")


def load_avatars():
    """Load avatar names from config.txt."""
    config_path = os.path.join(SCRIPT_DIR, "config.txt")
    avatars = []
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
                for line in content.splitlines():
                    if "available_avatars:" in line:
                        parts = line.split("available_avatars:")[1].split(",")
                        avatars = [nominal.strip() for nominal in parts if nominal.strip()]
    except Exception as exc:
        print(f"Warning: failed to load avatars: {exc}")
    return avatars


def save_avatars(avatars):
    """Persist avatar names to config.txt."""
    config_path = os.path.join(SCRIPT_DIR, "config.txt")
    line = "available_avatars:"
    if avatars:
        line += " " + ", ".join(avatars)
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(line + "\n")


@app.route("/")
def index():
    """Render the main UI page."""
    avatars = load_avatars()
    return render_template("index.html", avatars=avatars)


@app.route("/avatars", methods=["GET"])
def avatars_get():
    """Return the current avatar list."""
    return jsonify({"avatars": load_avatars()})


@app.route("/avatars", methods=["POST"])
def avatars_add():
    """Add a new avatar name to config."""
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"ok": False, "error": "Avatar name is required."}), 400

    avatars = load_avatars()
    if name not in avatars:
        avatars.append(name)
        save_avatars(avatars)

    return jsonify({"ok": True, "avatars": avatars})


@app.route("/avatars", methods=["DELETE"])
def avatars_delete():
    """Remove an avatar name from config."""
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"ok": False, "error": "Avatar name is required."}), 400

    avatars = [avatar for avatar in load_avatars() if avatar != name]
    save_avatars(avatars)
    return jsonify({"ok": True, "avatars": avatars})


@app.route("/start", methods=["POST"])
def start():
    """Validate UI payload, write queue file, and launch automation."""
    data = request.get_json(silent=True) or {}

    items = data.get("items", [])
    avatar = (data.get("avatar") or "").strip()
    project_name = (data.get("project_name") or "Pasted Scripts").strip()
    config_in = data.get("config", {}) or {}

    config = {
        "quality": config_in.get("quality", "720p"),
        "fps": config_in.get("fps", "25"),
        "subtitles": config_in.get("subtitles", "yes"),
    }

    if not avatar:
        return jsonify({"ok": False, "error": "Avatar is required."}), 400

    if not items:
        return jsonify({"ok": False, "error": "Queue is empty."}), 400

    safe_items = []
    for item in items:
        title = str(item.get("title", "")).strip()
        script = str(item.get("script", "")).strip()
        if not script:
            continue
        safe_items.append({"title": title, "script": script})

    if not safe_items:
        return jsonify({"ok": False, "error": "All scripts were empty."}), 400

    payload = {
        "project_name": project_name,
        "avatar": avatar,
        "config": config,
        "items": safe_items,
    }

    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    process = subprocess.Popen(
        [sys.executable, HEYGEN_SCRIPT, "--ui-queue", QUEUE_FILE],
        cwd=SCRIPT_DIR,
    )

    return jsonify({"ok": True, "pid": process.pid})


if __name__ == "__main__":
    print("HeyGen UI running at http://127.0.0.1:5000")
    threading.Timer(0.6, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
