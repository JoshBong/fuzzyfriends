"""Best Friends Animal Society adoption centers (scrapes the public listing pages)."""
from __future__ import annotations

import html
import re

from ..http import fetch
from ..models import Pet, age_from_text, coat_from_breed

NAME = "bestfriends"
LABEL = "Best Friends Animal Society"
# location slug -> listing; override with options {"location": "los-angeles"}
DEFAULT_OPTIONS = {"location": "new-york-city"}

CARD = re.compile(
    r'<a href="(/[^"]+/adopt/(\d+)/[^"]+)">.*?alt="[^"]*? - ([^"]+)".*?'
    r'card-title">\s*<span>([^<]+)</span>.*?card-as">\s*([^<]+?)\s*</div>.*?card-status">\s*([^<]*?)\s*</div>',
    re.S)
CAT = re.compile(r"domestic|siamese|ragdoll|ragamuffin|birman|british|siberian|himalayan|persian|maine|bengal|russian|"
                 r"abyssinian|sphynx|bombay|tabby|norwegian|turkish|manx|burmese|tonkinese|\bcat\b", re.I)
SMALL = re.compile(r"rabbit|bunny|lop|rex|guinea|hamster|rat|mouse|chinchilla|ferret|bird", re.I)


def species_of(breed: str) -> str:
    if CAT.search(breed):
        return "cat"
    if SMALL.search(breed):
        return "rabbit" if re.search(r"rabbit|bunny|lop|rex", breed, re.I) else "other"
    return "dog"


def fetch_pets(options: dict, filters: dict) -> list[Pet]:
    loc = options.get("location") or DEFAULT_OPTIONS["location"]
    base = f"https://bestfriends.org/{loc}/adopt/adoptable-pets?page={{}}"
    pets: dict[str, Pet] = {}
    for page in range(30):
        cards = CARD.findall(fetch(base.format(page)))
        if not cards:
            break
        for path, pid, breed, name, age_sex, status in cards:
            breed = html.unescape(breed).strip()
            age_sex = age_sex.strip()
            sex = next((s for s in ("Female", "Male") if s in age_sex), None)
            pets.setdefault(pid, Pet(
                source=NAME, id=pid, name=html.unescape(name.strip()), species=species_of(breed),
                url="https://bestfriends.org" + path, breed=breed, age=age_from_text(age_sex), sex=sex,
                coat=coat_from_breed(breed), location=f"Best Friends {loc.replace('-', ' ').title()}",
                foster="foster" in status.lower()))
    return list(pets.values())


def detail(url: str) -> dict:
    """Page-level status for a watched pet: 'Coming Soon' / 'New Arrival' / offsite / bio / health notes."""
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", fetch(url), flags=re.S)
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))
    start = t.find("Hi my name is")
    end = t.find("How to adopt from Best Friends", start)
    bio = t[start:end].strip() if start >= 0 and end > start else ""
    m = re.search(r"Meet .+? — ([^!.]+)!", bio)
    if m:
        status = m.group(1).strip()
    elif "Offsite Notice" in bio:
        status = "At offsite partner"
    elif "almost ready for adoption" in bio:
        status = "Almost ready"
    else:
        status = "Available"
    return {
        "status": status,
        "bio": bio[:1500],
        "foster": "in foster" in bio.lower(),
        "medical": bool(re.search(r"medical|medication|diagnos|special needs|FIV|FeLV|URI|ringworm|vet", bio, re.I)),
    }
