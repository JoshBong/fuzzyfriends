from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Optional

AGES = ["baby", "young", "adult", "senior"]
COATS = ["short", "medium", "long", "hairless"]


@dataclass
class Pet:
    source: str
    id: str  # unique within source
    name: str
    species: str  # cat, dog, rabbit, ...
    url: str
    breed: str = ""
    age: Optional[str] = None  # one of AGES
    sex: Optional[str] = None
    coat: Optional[str] = None  # one of COATS
    location: str = ""
    foster: bool = False
    photo: str = ""

    @property
    def key(self) -> str:
        return f"{self.source}:{self.id}"

    def to_dict(self) -> dict:
        return asdict(self)

    def line(self) -> str:
        bits = [self.age, self.sex, self.breed, "foster" if self.foster else self.location]
        return f"{self.name} — " + ", ".join(b for b in bits if b)


def coat_from_breed(breed: str) -> Optional[str]:
    b = breed.lower()
    if re.search(r"long|ragdoll|ragamuffin|persian|maine|siberian|himalayan|birman|norwegian", b):
        return "long"
    if "medium" in b:
        return "medium"
    if re.search(r"sphynx|hairless", b):
        return "hairless"
    if "short" in b:
        return "short"
    return None


def age_from_text(text: str) -> Optional[str]:
    t = text.lower()
    if re.search(r"baby|kitten|puppy", t):
        return "baby"
    for a in AGES[1:]:
        if a in t:
            return a
    return None


def age_from_months(months: float) -> str:
    # rough shelter convention: <6mo baby, <2y young, <8y adult
    if months < 6:
        return "baby"
    if months < 24:
        return "young"
    return "adult" if months < 96 else "senior"


def age_from_duration(text: str) -> Optional[str]:
    """'21 weeks.', '6 Months', '3 years 11 months', '1 Year' -> age bucket."""
    t = text.lower()
    months = 0.0
    for n, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(year|yr|month|mo|week|wk|day)", t):
        n = float(n)
        months += n * 12 if unit in ("year", "yr") else n if unit in ("month", "mo") else \
            n / 4.3 if unit in ("week", "wk") else n / 30
    return age_from_months(months) if months else age_from_text(t)
