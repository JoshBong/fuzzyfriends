from __future__ import annotations

import json
import sqlite3
import time

from .config import HOME
from .models import Pet


def connect() -> sqlite3.Connection:
    HOME.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(HOME / "pets.db")
    db.execute("""CREATE TABLE IF NOT EXISTS pets (
        key TEXT PRIMARY KEY, source TEXT, data TEXT, first_seen REAL, last_seen REAL, gone INTEGER DEFAULT 0)""")
    db.execute("CREATE TABLE IF NOT EXISTS runs (source TEXT PRIMARY KEY, at REAL, count INTEGER, error TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS events (at REAL, key TEXT, kind TEXT, detail TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS details (key TEXT PRIMARY KEY, data TEXT, checked REAL)")
    cols = {c[1] for c in db.execute("PRAGMA table_info(pets)")}
    if "missing" not in cols:  # consecutive checks a listing was absent
        db.execute("ALTER TABLE pets ADD COLUMN missing INTEGER DEFAULT 0")
    return db


def event(db: sqlite3.Connection, key: str, kind: str, detail: str = "") -> None:
    db.execute("INSERT INTO events VALUES (?,?,?,?)", (time.time(), key, kind, detail))


# card fields whose change is worth telling someone about (e.g. foster -> center = arrived)
TRACKED = ("foster", "location", "age", "name")
GONE_AFTER = 2  # a listing must be missing this many checks in a row; one flaky page shouldn't "adopt" 40 cats
PARTIAL = 0.7   # a scrape returning < 70% of last count is treated as partial: nothing gets marked missing


def sync(db: sqlite3.Connection, source: str, pets: list[Pet]) -> tuple[list[Pet], list[dict], list[tuple], bool]:
    """Record a scrape. Returns (new pets, newly-gone pets, changes [(pet, field, old, new)], first_run_for_source)."""
    now = time.time()
    first = db.execute("SELECT 1 FROM pets WHERE source=? LIMIT 1", (source,)).fetchone() is None
    prev = db.execute("SELECT count FROM runs WHERE source=? AND count IS NOT NULL", (source,)).fetchone()
    partial = bool(prev and prev[0] and len(pets) < prev[0] * PARTIAL)
    stored = {k: (json.loads(d), g) for k, d, g in db.execute("SELECT key, data, gone FROM pets WHERE source=?", (source,))}
    current = {p.key: p for p in pets}
    new, changes = [], []
    for k, p in current.items():
        if k not in stored:
            new.append(p)
            if not first:
                event(db, k, "new", p.name)
        else:
            old, was_gone = stored[k]
            if was_gone:
                event(db, k, "back", p.name)
            for f in TRACKED:
                if old.get(f) != getattr(p, f):
                    changes.append((p, f, old.get(f), getattr(p, f)))
                    event(db, k, "changed", json.dumps([f, old.get(f), getattr(p, f)]))
        db.execute("""INSERT INTO pets (key, source, data, first_seen, last_seen) VALUES (?,?,?,?,?)
                      ON CONFLICT(key) DO UPDATE SET data=excluded.data, last_seen=excluded.last_seen, gone=0, missing=0""",
                   (k, source, json.dumps(p.to_dict()), now, now))
    gone = []
    if not partial:
        for k, (data, was_gone) in stored.items():
            if was_gone or k in current:
                continue
            db.execute("UPDATE pets SET missing=missing+1 WHERE key=?", (k,))
            (missing,) = db.execute("SELECT missing FROM pets WHERE key=?", (k,)).fetchone()
            if missing >= GONE_AFTER:
                db.execute("UPDATE pets SET gone=1 WHERE key=?", (k,))
                event(db, k, "gone", data["name"])
                gone.append(data)
    db.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?,?)",
               (source, now, len(pets), f"partial scrape ({len(pets)} vs {prev[0]}), skipped gone-detection" if partial else None))
    db.commit()
    return new, gone, changes, first


def get_detail(db: sqlite3.Connection, key: str) -> dict | None:
    row = db.execute("SELECT data FROM details WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else None


def put_detail(db: sqlite3.Connection, key: str, data: dict) -> None:
    db.execute("INSERT OR REPLACE INTO details VALUES (?,?,?)", (key, json.dumps(data), time.time()))
    db.commit()


def record_error(db: sqlite3.Connection, source: str, err: str) -> None:
    db.execute("INSERT OR REPLACE INTO runs VALUES (?,?,NULL,?)", (source, time.time(), err[:500]))
    db.commit()


def current(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute("SELECT data, first_seen FROM pets WHERE gone=0 ORDER BY first_seen DESC")
    return [{**json.loads(d), "first_seen": fs} for d, fs in rows]


def runs(db: sqlite3.Connection) -> list[tuple]:
    return db.execute("SELECT source, at, count, error FROM runs").fetchall()
