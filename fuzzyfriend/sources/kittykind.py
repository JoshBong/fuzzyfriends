"""KittyKind (NYC cat rescue), plain HTML listing."""
from __future__ import annotations

import html
import re

from ..http import fetch
from ..models import Pet, age_from_duration, coat_from_breed

NAME = "kittykind"
LABEL = "KittyKind (cats)"
DEFAULT_OPTIONS = {}

CARD = re.compile(r'<a class="recap" href="/detail\?id=(\d+)">.*?<img src="([^"]*)".*?class="name">([^<]+)</div>(.*?)</a>', re.S)


def _field(block: str, label: str) -> str:
    m = re.search(rf'{label}:</span>\s*([^<]+)', block)
    return html.unescape(m.group(1)).strip() if m else ""


def fetch_pets(options: dict, filters: dict) -> list[Pet]:
    pets = []
    for pid, img, name, block in CARD.findall(fetch("https://kittykind.org/adopt/")):
        name = html.unescape(name).strip()
        if "pending" in name.lower():
            continue
        breed = _field(block, "BREED")
        pets.append(Pet(
            source=NAME, id=pid, name=name.split(":")[0].strip(), species="cat",
            url=f"https://kittykind.org/detail?id={pid}", breed=breed, age=age_from_duration(_field(block, "AGE")),
            sex=_field(block, "SEX") or None, coat=coat_from_breed(breed), location="KittyKind", photo=img))
    return pets
