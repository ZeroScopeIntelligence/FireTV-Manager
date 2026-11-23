import json
from pathlib import Path

APP_DIR = Path.home() / ".config" / "zeroscope-fire-tv-manager"
CONFIG_FILE = APP_DIR / "settings.json"
DEFAULTS = {"adb_path": "", "default_port": 5555}

def load_settings():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return {**DEFAULTS, **data}
    except (OSError, json.JSONDecodeError):
        return DEFAULTS.copy()

def save_settings(settings):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
