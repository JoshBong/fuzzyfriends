from __future__ import annotations

import json
import time
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"


def fetch(url: str, tries: int = 3, timeout: int = 60, headers: dict | None = None) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    for i in range(tries):
        try:
            return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
        except OSError:
            if i == tries - 1:
                raise
            time.sleep(10)
    raise AssertionError("unreachable")


def fetch_json(url: str, **kw):
    return json.loads(fetch(url, headers={"Accept": "application/json", **kw.pop("headers", {})}, **kw))
