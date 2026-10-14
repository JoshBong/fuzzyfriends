"""Each source module exposes NAME, LABEL, DEFAULT_OPTIONS and fetch_pets(options, filters) -> list[Pet].
Add a site by dropping a module here and listing it in SOURCES."""
from . import adoptapet, bestfriends, kittykind, nycacc, shelterluv

SOURCES = {m.NAME: m for m in (bestfriends, adoptapet, nycacc, shelterluv, kittykind)}
