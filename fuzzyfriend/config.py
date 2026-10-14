from __future__ import annotations

import json
import os
from pathlib import Path

from .sources import SOURCES

HOME = Path(os.environ.get("FUZZYFRIEND_HOME", Path.home() / ".fuzzyfriend"))
CONFIG = HOME / "config.json"

DEFAULT = {
    "interval_min": 30,
    "port": 8484,
    "sources": {name: {"enabled": True, "options": {}} for name in SOURCES},
    # empty list = no filter on that field
    "filters": {"species": ["cat"], "age": ["baby", "young"], "coat": ["long", "medium"], "include_foster": True},
    "watch": {},  # "source:id" -> name; alert when the listing disappears
    "notify": {
        "ntfy": {"enabled": False, "server": "https://ntfy.sh", "topic": ""},
        "email": {"enabled": False, "user": "", "app_password": "", "to": ""},
        "desktop": {"enabled": True},
    },
}


def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        out[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def load() -> dict:
    if not CONFIG.exists():
        save(DEFAULT)
        return json.loads(json.dumps(DEFAULT))
    return _merge(DEFAULT, json.loads(CONFIG.read_text()))


def save(cfg: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=2))
    CONFIG.chmod(0o600)  # holds the email app password
