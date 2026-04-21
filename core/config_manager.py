import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".myfi"
CONFIG_FILE = CONFIG_DIR / "config.json"

def ensure_config_dir():
    CONFIG_DIR.mkdir(exist_ok=True)

def load_config():
    ensure_config_dir()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(config):
    ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def is_configured():
    config = load_config()
    return bool(config.get("interface")) and config.get("dependencies_ok", False)