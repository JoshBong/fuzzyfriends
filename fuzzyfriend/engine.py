from __future__ import annotations

import time
from datetime import datetime

from . import notify, store
from .config import load
from .models import Pet
from .sources import SOURCES


def matches(p: Pet | dict, f: dict) -> bool:
    g = p if isinstance(p, dict) else p.to_dict()
    for field in ("species", "age", "coat"):
        want = f.get(field) or []
        if want and g.get(field) not in want:
            return False
    return f.get("include_foster", True) or not g.get("foster")


def visible(p: dict, cfg: dict) -> bool:
    return cfg["sources"].get(p["source"], {}).get("enabled", False) and matches(p, cfg["filters"])


def check(log=print) -> None:
    cfg = load()
    db = store.connect()
    hits: list[Pet] = []
    for name, sc in cfg["sources"].items():
        mod = SOURCES.get(name)
        if not mod or not sc.get("enabled"):
            continue
        try:
            pets = mod.fetch_pets({**mod.DEFAULT_OPTIONS, **sc.get("options", {})}, cfg["filters"])
            if not pets:
                raise RuntimeError("0 pets returned — site layout may have changed")
        except Exception as e:
            store.record_error(db, name, str(e))
            log(f"{name}: ERROR {e}")
            continue
        new, gone, first = store.sync(db, name, pets)
        log(f"{name}: {len(pets)} listed, {len(new)} new, {len(gone)} gone" + (" (baseline)" if first else ""))
        if not first:  # first run only seeds; existing listings are shown in the UI instead of spamming
            hits += [p for p in new if matches(p, cfg["filters"])]
        for g in gone:
            key = f"{g['source']}:{g['id']}"
            if key in cfg["watch"]:
                notify.send(cfg, f"💔 {g['name']} is no longer listed", f"{g['name']} was adopted or pulled.\n{g['url']}")
    if hits:
        title = f"🐾 {len(hits)} new: " + ", ".join(p.name for p in hits[:4])
        body = "\n\n".join(f"{p.line()}\n{p.url}" for p in hits)
        for err in notify.send(cfg, title, body, click=hits[0].url if len(hits) == 1 else ""):
            log(f"notify {err}")


def loop(log=print) -> None:
    while True:
        log(f"--- {datetime.now():%F %H:%M}")
        try:
            check(log)
        except Exception as e:
            log(f"check failed: {e}")
        time.sleep(max(5, load()["interval_min"]) * 60)
