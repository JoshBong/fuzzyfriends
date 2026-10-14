"""Any rescue that uses Shelterluv. Find an org's numeric id in the "shelterId" field of
https://new.shelterluv.com/matchme/adopt/<CODE>/Cat"""
from __future__ import annotations

import time

from ..http import fetch_json
from ..models import Pet, age_from_months, age_from_text, coat_from_breed

NAME = "shelterluv"
LABEL = "Shelterluv rescues"
DEFAULT_OPTIONS = {"orgs": {
    "100000084": "Puppy Kitty NYC",
    "100002831": "NYC Second Chance Rescue",
    "1235": "Animal Haven",
    "17976": "AdvoCat Rescue",
}}


def fetch_pets(options: dict, filters: dict) -> list[Pet]:
    pets = []
    for org_id, org in options["orgs"].items():
        for r in fetch_json(f"https://new.shelterluv.com/api/v3/available-animals/{org_id}").get("animals", []):
            breed = " / ".join(b for b in (r.get("breed"), r.get("secondary_breed")) if b)
            bday = r.get("birthday")
            age = age_from_months((time.time() - int(bday)) / 86400 / 30.4) if bday else \
                age_from_text((r.get("age_group") or {}).get("name") or "")
            photos = r.get("photos") or []
            if isinstance(photos, dict):  # some orgs return {"<order>": photo}
                photos = list(photos.values())
            cover = next((ph for ph in photos if ph.get("isCover")), photos[0] if photos else {})
            pets.append(Pet(
                source=NAME, id=str(r["nid"]), name=r["name"].strip(), species=(r.get("species") or "").lower(),
                url=r.get("public_url") or f"https://new.shelterluv.com/embed/animal/{r['nid']}", breed=breed, age=age,
                sex=r.get("sex"), coat=coat_from_breed(breed), location=org,
                foster="foster" in (r.get("location") or "").lower(), photo=cover.get("url", "")))
    return pets
