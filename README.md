# 🐾 fuzzyfriend

Get pinged the moment the pet you want is listed for adoption. Pick the animal, age and coat. Pick which shelters to
watch. Get a phone push or an email with the link. It runs on your own computer or a Raspberry Pi, with no account
and no server, and needs nothing but Python 3.9+.

## Install (Pi, Linux or Mac)

```sh
curl -fsSL https://raw.githubusercontent.com/JoshBong/fuzzyfriends/main/install.sh | sh
```

It starts right away, comes back after a reboot (via an `@reboot` cron line), and prints the address of the settings
page. Open that address from your phone or laptop to change what you're looking for. Run the same command again to
update.

The settings page has no login, so anyone on your Wi-Fi can open it. Keep it on a home network or Tailscale; don't
port-forward it to the internet.

Manual run: `python3 -m fuzzyfriend serve` (add `--host 0.0.0.0` to open it from other devices).

Open the page and set what you want, where to look and how to get alerted. It checks on its own every N minutes while
`serve` runs. The first check of each source only records what's already listed, so it won't spam you. After that you
only hear about **new** listings. Hit **watch** on a pet (or paste its link) to get pinged when it's adopted or pulled, when it moves from foster to the center, and, for Best Friends, when its page changes: "Coming Soon" → arrived, bio filled in, or health notes posted.

Other commands (`python3 -m fuzzyfriend ...`): `check` (one pass, for cron), `list` (current matches), `config`
(where the config lives: `~/.fuzzyfriend/`, override with `FUZZYFRIEND_HOME`).

## Alerts

- **Phone push via [ntfy](https://ntfy.sh)**: free app, no account. Subscribe to a hard-to-guess topic and enter the
  same topic on the settings page.
- **Email**: a Gmail address plus an [app password](https://myaccount.google.com/apppasswords).
- **Desktop**: macOS / Linux notifications on the machine running it.

## Sources (NYC-focused for now)

| Source | Covers |
|---|---|
| Best Friends | Best Friends adoption centers (any city: set `location`, e.g. `los-angeles`) |
| Adopt-a-Pet | radius search around a ZIP; aggregates many shelters and rescues |
| NYC ACC | NYC's city shelter |
| Shelterluv | any rescue on Shelterluv (Puppy Kitty NYC, NYC Second Chance, Animal Haven, AdvoCat by default) |
| KittyKind | NYC cat rescue |

To add a site, drop a module into `fuzzyfriend/sources/` that exposes `NAME`, `LABEL`, `DEFAULT_OPTIONS` and
`fetch_pets(options, filters) -> list[Pet]`, then list it in `sources/__init__.py`.

Be polite: the default interval is 30 min, and these are shelters' own sites.
