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
    return db


def sync(db: sqlite3.Connection, source: str, pets: list[Pet]) -> tuple[list[Pet], list[dict], bool]:
    """Record a scrape. Returns (new pets, newly-gone pets, first_run_for_source)."""
    now = time.time()
    first = db.execute("SELECT 1 FROM pets WHERE source=? LIMIT 1", (source,)).fetchone() is None
    known = {k for (k,) in db.execute("SELECT key FROM pets WHERE source=? AND gone=0", (source,))}
    seen_ever = {k for (k,) in db.execute("SELECT key FROM pets WHERE source=?", (source,))}
    current = {p.key: p for p in pets}
    new = [p for k, p in current.items() if k not in seen_ever]
    for p in pets:
        db.execute("""INSERT INTO pets (key, source, data, first_seen, last_seen) VALUES (?,?,?,?,?)
                      ON CONFLICT(key) DO UPDATE SET data=excluded.data, last_seen=excluded.last_seen, gone=0""",
                   (p.key, source, json.dumps(p.to_dict()), now, now))
    gone_keys = known - current.keys()
    gone = []
    for k in gone_keys:
        (data,) = db.execute("SELECT data FROM pets WHERE key=?", (k,)).fetchone()
        gone.append(json.loads(data))
        db.execute("UPDATE pets SET gone=1 WHERE key=?", (k,))
    db.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?,NULL)", (source, now, len(pets)))
    db.commit()
    return new, gone, first


def record_error(db: sqlite3.Connection, source: str, err: str) -> None:
    db.execute("INSERT OR REPLACE INTO runs VALUES (?,?,NULL,?)", (source, time.time(), err[:500]))
    db.commit()


def current(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute("SELECT data, first_seen FROM pets WHERE gone=0 ORDER BY first_seen DESC")
    return [{**json.loads(d), "first_seen": fs} for d, fs in rows]


def runs(db: sqlite3.Connection) -> list[tuple]:
    return db.execute("SELECT source, at, count, error FROM runs").fetchall()
