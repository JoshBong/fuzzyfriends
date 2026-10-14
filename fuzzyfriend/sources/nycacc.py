"""NYC Animal Care Centers (the city shelter), via the GraphQL feed behind nycacc.app."""
from __future__ import annotations

import http.client
import json
import uuid

from ..models import Pet, age_from_duration, coat_from_breed

NAME = "nycacc"
LABEL = "NYC Animal Care Centers (city shelter)"
DEFAULT_OPTIONS = {}

# public key shipped in nycacc.app's own JS
API_KEY = "jKbOSNYtJn5qhYbsv9IKL6OEt7etN6jcALlerH82"
QUERY = "{ feed { pets { id name age species breeds link location } } }"


def _post(path: str, body: dict, token: str = "") -> dict:
    # http.client, not urllib: the server matches the lowercase "x-api-key" header name exactly
    headers = {"Content-Type": "application/json; charset=UTF-8", "x-api-key": API_KEY, "User-Agent": "Mozilla/5.0"}
    if token:
        headers["Authorization"] = "Bearer " + token
    c = http.client.HTTPSConnection("nycacc.app", timeout=60)
    c.request("POST", path, json.dumps(body), headers)
    return json.loads(c.getresponse().read())


def fetch_pets(options: dict, filters: dict) -> list[Pet]:
    token = _post("/token", {"deviceId": str(uuid.uuid4()), "organization": "accofnyc"})["access_token"]
    feed = _post("/graphql", {"query": QUERY}, token)["data"]["feed"]["pets"]
    pets = []
    for r in feed:
        breed = " / ".join(r.get("breeds") or [])
        loc = r.get("location") or ""
        pets.append(Pet(
            source=NAME, id=str(r["id"]), name=r["name"].strip(), species=(r.get("species") or "").lower(),
            url=r.get("link") or f"https://nycacc.app/browse/{r['id']}", breed=breed,
            age=age_from_duration(r.get("age") or ""), coat=coat_from_breed(breed),
            location=f"NYC ACC {loc}".strip(), foster="foster" in loc.lower()))
    return pets
