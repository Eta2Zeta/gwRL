# Game content

This directory keeps source material and authored game data separate from engine and training code.

## Maps

- `gw36_manual_map.json` is the detailed world graph used for ongoing environment development.
- `gw36_nation_home_country.json` maps nations to their home-country land zones.
- `gw36map.png` is the primary full-map image.
- `gw36map-reference.png` is the alternate/reference map image formerly named `gw36map copy.png`.

Regenerate the JSON map files from the repository root with:

```sh
./.venv/bin/python tools/build_manual_map_json.py
./.venv/bin/python tools/build_nation_home_country_json.py
```

## Rules

- `Global War 1936 v4.3 Rulebook.pdf` is the main source rulebook.
- `rulebook.txt` is its extracted searchable text.
- `neutrals_setup_v4_3.pdf` contains the neutral-power setup material.

## Scenarios

- `china_simplified_setup.json` defines the six-zone China training environment.
- `manual_battles/` contains deterministic battle fixtures used by the debug runner.
