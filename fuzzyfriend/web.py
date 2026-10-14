"""Local settings + matches page. Stdlib only so it runs anywhere Python does."""
from __future__ import annotations

import html
import re
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import engine, notify, store
from .config import load, save
from .models import AGES, COATS
from .sources import SOURCES

SPECIES = ["cat", "dog", "rabbit"]
CHECK_LOCK = threading.Lock()
LOG: list[str] = []


def log(msg: str) -> None:
    LOG.append(f"{time.strftime('%H:%M')} {msg}")
    del LOG[:-50]
    print(msg, flush=True)


def run_check() -> None:
    if CHECK_LOCK.acquire(blocking=False):
        try:
            engine.check(log)
        finally:
            CHECK_LOCK.release()


def esc(s) -> str:
    return html.escape(str(s or ""), quote=True)


def boxes(name: str, options: list, chosen: list) -> str:
    return "".join(f'<label class="chip"><input type="checkbox" name="{name}" value="{o}"'
                   f'{" checked" if o in chosen else ""}> {o}</label>' for o in options)


def page(cfg: dict) -> str:
    db = store.connect()
    all_pets = store.current(db)
    pets = [p for p in all_pets if engine.visible(p, cfg)]
    per_src = {}
    for p in all_pets:
        if engine.matches(p, cfg["filters"]):
            per_src[p["source"]] = per_src.get(p["source"], 0) + 1
    toggles = "".join(
        f'''<form method="post" action="/toggle" style="display:inline"><input type="hidden" name="src" value="{name}">
        <button class="tog{" on" if cfg["sources"].get(name, {}).get("enabled") else ""}">{esc(mod.LABEL.split(" (")[0])} · {per_src.get(name, 0)}</button></form>'''
        for name, mod in SOURCES.items())
    runs = {s: (at, n, err) for s, at, n, err in store.runs(db)}
    f, n = cfg["filters"], cfg["notify"]

    cards = "".join(f'''<div class="card">{f'<img src="{esc(p["photo"])}" loading="lazy">' if p.get("photo") else '<div class="noimg">🐾</div>'}
      <div class="body"><a href="{esc(p["url"])}" target="_blank"><b>{esc(p["name"])}</b></a>
      <div class="meta">{esc(" · ".join(x for x in (p.get("age"), p.get("sex"), p.get("breed")) if x))}</div>
      <div class="meta">{esc("foster" if p.get("foster") else p.get("location"))} — {esc(SOURCES[p["source"]].LABEL if p["source"] in SOURCES else p["source"])}</div>
      <form method="post" action="/watch"><input type="hidden" name="key" value="{esc(p["source"] + ":" + p["id"])}">
      <input type="hidden" name="name" value="{esc(p["name"])}"><button>{"👀 watching" if p["source"] + ":" + p["id"] in cfg["watch"] else "watch"}</button></form>
      </div></div>''' for p in pets) or '<p class="meta">No matches yet. Hit "Check now" (first check of a source just records what is listed).</p>'

    srcs = ""
    for name, mod in SOURCES.items():
        sc = cfg["sources"].get(name, {})
        at, cnt, err = runs.get(name, (None, None, None))
        status = f'<span class="err">error: {esc(err)}</span>' if err else \
            (f'{cnt} listed · {time.strftime("%a %H:%M", time.localtime(at))}' if at else "never checked")
        opts = {**mod.DEFAULT_OPTIONS, **sc.get("options", {})}
        opt_inputs = "".join(f'<label class="opt">{esc(k)} <input name="opt:{name}:{esc(k)}" value="{esc(v)}"></label>'
                             for k, v in opts.items() if not isinstance(v, dict))
        srcs += f'''<div class="src"><label><input type="checkbox" name="src" value="{name}"{" checked" if sc.get("enabled") else ""}>
          <b>{esc(mod.LABEL)}</b></label> <span class="meta">{status}</span> {opt_inputs}</div>'''

    urls = {p["source"] + ":" + p["id"]: p["url"] for p in all_pets}
    watch = "".join(f'<li><a href="{esc(urls.get(k, "#"))}" target="_blank">{esc(v)}</a> <form method="post" action="/unwatch" style="display:inline">'
                    f'<input type="hidden" name="key" value="{esc(k)}"><button>remove</button></form></li>'
                    for k, v in cfg["watch"].items()) or '<li class="meta">Nothing watched. Hit "watch" on a pet to get a ping if it gets adopted.</li>'

    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>fuzzyfriend</title><style>
:root{{--bg:#fffaf5;--fg:#2b2118;--muted:#8a7a6b;--card:#fff;--line:#eadfd3;--accent:#e07a2f}}
@media (prefers-color-scheme:dark){{:root{{--bg:#1b1612;--fg:#f3e9df;--muted:#a8998a;--card:#251e18;--line:#3a2f26;--accent:#f0954f}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 -apple-system,system-ui,sans-serif}}
main{{max-width:980px;margin:auto;padding:16px}} h1{{margin:.2em 0}} h2{{margin-top:1.6em;font-size:1.1em}}
a{{color:var(--accent)}} .meta{{color:var(--muted);font-size:.88em}} .err{{color:#d33;font-size:.88em}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(150px,100%),1fr));gap:12px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}}
.card img,.noimg{{width:100%;aspect-ratio:1;object-fit:cover;display:grid;place-items:center;font-size:40px;background:var(--line)}}
.body{{padding:8px 10px}} .chip{{display:inline-block;margin:2px 10px 2px 0}}
.src{{padding:6px 0;border-bottom:1px solid var(--line)}} .opt{{display:inline-block;margin-left:12px;font-size:.88em}}
input:not([type=checkbox]){{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:4px 6px;max-width:100%}}
button{{background:var(--accent);color:#fff;border:0;border-radius:8px;padding:6px 12px;cursor:pointer;margin-top:4px}}
.paste{{display:flex;gap:6px}} .paste input{{flex:1;min-width:0}}
.toggles{{margin:-4px 0 12px}} .tog{{background:transparent;color:var(--muted);border:1px solid var(--line);margin:3px 2px}}
.tog.on{{background:var(--accent);color:#fff;border-color:var(--accent)}}
fieldset{{border:1px solid var(--line);border-radius:10px;margin:10px 0}} pre{{white-space:pre-wrap;font-size:.8em;color:var(--muted)}}
</style></head><body><main>
<h1>🐾 fuzzyfriend</h1>
<form method="post" action="/check"><button>Check now</button> <span class="meta">auto-checks every {cfg["interval_min"]} min</span></form>
<h2>Matches ({len(pets)})</h2>
<div class="toggles"><span class="meta">Sites (tap to turn on/off):</span> {toggles}</div><div class="grid">{cards}</div>
<h2>Watching</h2>
<form method="post" action="/watch" class="paste"><input name="link" placeholder="paste a pet's link to watch it" required>
<button>Watch</button></form><ul>{watch}</ul>
<form method="post" action="/save">
<h2>What you want</h2>
<fieldset><legend>Animal</legend>{boxes("species", SPECIES, f["species"])}</fieldset>
<fieldset><legend>Age</legend>{boxes("age", AGES, f["age"])}</fieldset>
<fieldset><legend>Coat</legend>{boxes("coat", COATS, f["coat"])}</fieldset>
<label class="chip"><input type="checkbox" name="include_foster" value="1"{" checked" if f.get("include_foster", True) else ""}> include pets in foster homes</label>
<p class="meta">Leave a group empty to allow anything.</p>
<h2>Where to look</h2>{srcs}
<h2>Alerts</h2>
<fieldset><legend><label><input type="checkbox" name="ntfy" value="1"{" checked" if n["ntfy"]["enabled"] else ""}> Phone push (ntfy)</label></legend>
<p class="meta">Install the free ntfy app, subscribe to a hard-to-guess topic, put the same topic here.</p>
<input name="ntfy_topic" placeholder="topic" value="{esc(n["ntfy"]["topic"])}"> <input name="ntfy_server" value="{esc(n["ntfy"]["server"])}"></fieldset>
<fieldset><legend><label><input type="checkbox" name="email" value="1"{" checked" if n["email"]["enabled"] else ""}> Email (Gmail)</label></legend>
<input name="email_user" placeholder="you@gmail.com" value="{esc(n["email"]["user"])}">
<input name="email_pw" type="password" placeholder="{"app password saved" if n["email"]["app_password"] else "Gmail app password"}">
<input name="email_to" placeholder="send to (default: same)" value="{esc(n["email"]["to"])}"></fieldset>
<label class="chip"><input type="checkbox" name="desktop" value="1"{" checked" if n["desktop"]["enabled"] else ""}> desktop notification on this computer</label>
<p>Check every <input name="interval" type="number" min="5" value="{cfg["interval_min"]}" style="width:5em"> minutes</p>
<button>Save</button></form>
<form method="post" action="/test"><button>Send test alert</button></form>
<h2>Log</h2><pre>{esc(chr(10).join(LOG[-20:]))}</pre>
</main></body></html>'''


def find_by_link(link: str) -> dict | None:
    """Match a pasted listing URL to a stored pet (any filter, enabled or not)."""
    link = link.strip().split("?")[0].rstrip("/")
    for p in store.current(store.connect()):
        u = p["url"].split("?")[0].rstrip("/")
        if u == link or re.search(rf"/{re.escape(p['id'])}(/|$)", link):
            return p
    return None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body: str, code: int = 200) -> None:
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _back(self) -> None:
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def do_GET(self):
        if self.path != "/":
            return self._send("not found", 404)
        self._send(page(load()))

    def do_POST(self):
        form = urllib.parse.parse_qs(self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode(), keep_blank_values=True)
        one = lambda k, d="": (form.get(k) or [d])[0]
        cfg = load()
        if self.path == "/check":
            threading.Thread(target=run_check, daemon=True).start()
            time.sleep(1)
        elif self.path == "/test":
            errs = notify.send(cfg, "🐾 fuzzyfriend test", "Alerts are working.")
            log("test alert: " + ("; ".join(errs) if errs else "sent"))
        elif self.path == "/watch":
            if one("link"):
                p = find_by_link(one("link"))
                if not p:
                    log(f"watch: couldn't find {one('link')} — is that site turned on and checked yet?")
                    return self._back()
                cfg["watch"][p["source"] + ":" + p["id"]] = p["name"]
                log(f"watching {p['name']}")
            else:
                cfg["watch"][one("key")] = one("name")
            save(cfg)
        elif self.path == "/unwatch":
            cfg["watch"].pop(one("key"), None)
            save(cfg)
        elif self.path == "/toggle":
            sc = cfg["sources"].setdefault(one("src"), {"enabled": False, "options": {}})
            sc["enabled"] = not sc.get("enabled")
            save(cfg)
        elif self.path == "/save":
            cfg["filters"] = {"species": form.get("species", []), "age": form.get("age", []), "coat": form.get("coat", []),
                              "include_foster": bool(one("include_foster"))}
            enabled = set(form.get("src", []))
            for name, mod in SOURCES.items():
                sc = cfg["sources"].setdefault(name, {"enabled": False, "options": {}})
                sc["enabled"] = name in enabled
                for k, v in mod.DEFAULT_OPTIONS.items():
                    key = f"opt:{name}:{k}"
                    if key in form and not isinstance(v, dict):
                        sc.setdefault("options", {})[k] = type(v)(one(key)) if one(key) else v
            n = cfg["notify"]
            n["ntfy"].update(enabled=bool(one("ntfy")), topic=one("ntfy_topic").strip(), server=one("ntfy_server").strip() or "https://ntfy.sh")
            n["email"].update(enabled=bool(one("email")), user=one("email_user").strip(), to=one("email_to").strip())
            if one("email_pw"):
                n["email"]["app_password"] = one("email_pw").replace(" ", "")
            n["desktop"]["enabled"] = bool(one("desktop"))
            cfg["interval_min"] = max(5, int(one("interval") or 30))
            save(cfg)
        else:
            return self._send("not found", 404)
        self._back()


def serve(host: str, port: int) -> None:
    threading.Thread(target=engine.loop, args=(log,), daemon=True).start()
    print(f"fuzzyfriend on http://{host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
