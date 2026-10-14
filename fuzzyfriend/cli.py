from __future__ import annotations

import argparse

from . import engine, store
from .config import CONFIG, load


def main() -> None:
    ap = argparse.ArgumentParser(prog="fuzzyfriend", description="Get pinged when the pet you want is listed for adoption.")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("serve", help="settings page + background checks (default)")
    s.add_argument("--host", default="127.0.0.1", help="0.0.0.0 to open the page from your phone on the same network")
    s.add_argument("--port", type=int)
    sub.add_parser("check", help="check every enabled source once and alert")
    sub.add_parser("list", help="print current matches")
    sub.add_parser("config", help="print the config file path")
    a = ap.parse_args()

    if a.cmd == "check":
        engine.check()
    elif a.cmd == "list":
        cfg = load()
        for p in store.current(store.connect()):
            if engine.visible(p, cfg):
                print(f"{p['name']} — {p.get('age')}, {p.get('breed')}, {'foster' if p.get('foster') else p.get('location')}\n  {p['url']}")
    elif a.cmd == "config":
        load()
        print(CONFIG)
    else:
        from .web import serve
        serve(getattr(a, "host", "127.0.0.1"), getattr(a, "port", None) or load()["port"])


if __name__ == "__main__":
    main()
