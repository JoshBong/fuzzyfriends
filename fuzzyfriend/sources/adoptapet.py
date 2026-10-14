"""Adopt-a-Pet radius search (aggregates many shelters). Filtering is pushed to their server to keep requests low."""
from __future__ import annotations

import html
import re
import json
import urllib.parse

from ..http import fetch
from ..models import Pet, age_from_duration, coat_from_breed

NAME = "adoptapet"
LABEL = "Adopt-a-Pet (many shelters & rescues)"
DEFAULT_OPTIONS = {"postal_code": "10001", "radius": 15}

SPECIES_ID = {"dog": 1, "cat": 2}
AGE_PARAM = {"baby": "kitten", "young": "young", "adult": "adult", "senior": "senior"}
SEX = {"f": "Female", "m": "Male"}


def _page(params: list, page: int) -> list[dict]:
    t = html.unescape(fetch("https://www.adoptapet.com/pet-search?" + urllib.parse.urlencode(params + [("page", page)])))
    i = t.find('"petsCollection":[')
    return json.JSONDecoder().raw_decode(t, i + len('"petsCollection":'))[0] if i >= 0 else []


def fetch_pets(options: dict, filters: dict) -> list[Pet]:
    species = [s for s in (filters.get("species") or SPECIES_ID) if s in SPECIES_ID]
    pets: dict[str, Pet] = {}
    for sp in species:
        params = [("postalCode", options["postal_code"]), ("speciesId", SPECIES_ID[sp]), ("radius", options["radius"])]
        params += [("hair[]", c) for c in filters.get("coat") or [] if c in ("short", "medium", "long")]
        params += [("age[]", AGE_PARAM[a]) for a in filters.get("age") or [] if a in AGE_PARAM]
        for page in range(1, 40):
            rows = _page(params, page)
            for r in rows:
                pid = str(r["petId"])
                if r.get("adopted") or pid in pets:
                    continue
                breed = r.get("breed") or ""
                age = r.get("age") or ""
                addr = r.get("address") or {}
                pets[pid] = Pet(
                    source=NAME, id=pid, name=re.sub(r"\s*\*[^*]*\*\s*", " ", r["name"]).strip(), species=sp, url=f"https://www.adoptapet.com/pet/{pid}",
                    breed=breed, age="baby" if age == "kitten" or age == "puppy" else age_from_duration(age),
                    sex=SEX.get(r.get("sex")), coat=coat_from_breed(breed),
                    location=", ".join(x for x in (addr.get("city"), addr.get("state")) if x), photo=r.get("photoUrl") or "")
            if len(rows) < 42:  # page size
                break
    return list(pets.values())
