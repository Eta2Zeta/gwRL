"""Build a strict faction-identity bridge without changing frozen scenario data.

    ./.venv/bin/python tools/scenario_factions.py

Aliases differ only by case or whitespace unless the approved setup explicitly
supplies another name. Original nationality and initial control stay separate;
this index does not implement possession, alignment, turns or game state.
"""

import argparse
import copy
import json
import os
from pathlib import Path
import re
import tempfile

try:
    from build_theatre_scenario import load_document, portable_path, same_file
except ModuleNotFoundError:
    from tools.build_theatre_scenario import load_document, portable_path, same_file


ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "game_content/scenarios/japan_china_1936"
DEFAULT_MAP = SCENARIO / "map.json"
DEFAULT_JAPAN_SETUP = SCENARIO / "m0/japan_setup.json"
DEFAULT_CHINA_SETUP = SCENARIO / "m0/china_minor_setup.json"
DEFAULT_OUTPUT = SCENARIO / "m1/faction_index.json"
CONTROL_FIELDS = (
    "controller_id", "alliance_id", "status", "source_controller_id",
    "turn_slot", "source_turn_slot", "national_identity_retained",
)


def normalize_alias(alias):
    """Remove whitespace and fold case; preserve punctuation and spelling."""
    if not isinstance(alias, str) or not alias.strip():
        raise ValueError("Faction aliases must be nonempty strings")
    return "".join(alias.split()).casefold()


def build_alias_index(factions):
    """Map declared aliases to canonical IDs, rejecting duplicate/ambiguous IDs."""
    if not isinstance(factions, list) or not factions:
        raise ValueError("Factions must be a nonempty list")
    canonical_ids, aliases = set(), {}
    for faction in factions:
        if not isinstance(faction, dict):
            raise ValueError("Faction records must be objects")
        faction_id = faction.get("id")
        if not isinstance(faction_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", faction_id):
            raise ValueError(f"Invalid canonical faction ID: {faction_id!r}")
        if faction_id in canonical_ids:
            raise ValueError(f"Duplicate canonical faction ID: {faction_id}")
        canonical_ids.add(faction_id)
        declared = faction.get("aliases", [])
        if not isinstance(declared, list):
            raise ValueError(f"{faction_id}: aliases must be a list")
        for alias in [faction_id, *declared]:
            normalized = normalize_alias(alias)
            if normalized in aliases and aliases[normalized] != faction_id:
                raise ValueError(
                    f"Ambiguous faction alias {alias!r}: {aliases[normalized]} and {faction_id}"
                )
            aliases[normalized] = faction_id
    return dict(sorted(aliases.items()))


def resolve_faction(alias, alias_to_id):
    """Resolve only a declared alias or its case/whitespace equivalent."""
    normalized = normalize_alias(alias)
    if normalized not in alias_to_id:
        raise ValueError(f"Unknown faction alias: {alias!r}")
    return alias_to_id[normalized]


def derive_factions(japan_setup, china_setup, theatre_map):
    """Copy approved identities; never interpret a controller as nationality."""
    nodes = theatre_map.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        raise ValueError("Theatre map requires a nonempty nodes object")
    for node_id, node in nodes.items():
        if (not isinstance(node, dict) or node.get("id") != node_id
                or node.get("type") not in ("land", "sea")):
            raise ValueError(f"Invalid theatre node: {node_id}")
    source_factions = china_setup.get("factions")
    if not isinstance(source_factions, list) or not source_factions:
        raise ValueError("China setup requires a nonempty factions list")
    factions = []
    for index, source in enumerate(source_factions):
        if not isinstance(source, dict):
            raise ValueError("China setup faction records must be objects")
        printed_name, map_alias = source.get("printed_name"), source.get("map_owner_alias")
        display_name = source.get("display_name", map_alias)
        normalize_alias(printed_name)
        normalize_alias(map_alias)
        normalize_alias(display_name)
        factions.append({
            "id": source.get("id"),
            "display_name": display_name,
            "printed_name": printed_name,
            "map_owner_alias": map_alias,
            "aliases": sorted({printed_name, map_alias, display_name}),
            "initial_control": {key: copy.deepcopy(source[key]) for key in CONTROL_FIELDS if key in source},
            "source_record": {"source_id": "china_setup", "json_pointer": f"/factions/{index}"},
        })
    nation = japan_setup.get("nation")
    normalized_nation = normalize_alias(nation)
    map_aliases = sorted({
        node["original_owner"] for node in nodes.values()
        if node["type"] == "land" and normalize_alias(node.get("original_owner")) == normalized_nation
    })
    if not map_aliases:
        raise ValueError(f"Japan setup nation {nation!r} has no matching retained original-owner alias")
    factions.append({
        "id": nation,
        "display_name": map_aliases[0],
        "map_owner_alias": map_aliases[0],
        "aliases": map_aliases,
        "initial_control": {"alliance_id": copy.deepcopy(japan_setup.get("alliance"))},
        "source_record": {"source_id": "japan_setup", "json_pointer": "/nation"},
    })
    build_alias_index(factions)
    return sorted(factions, key=lambda faction: faction["id"])


def build_index(japan_setup, china_setup, theatre_map):
    """Return identity data only; retain source labels and copied control fields."""
    scenario_id = japan_setup.get("scenario_id")
    if not isinstance(scenario_id, str) or not scenario_id:
        raise ValueError("Japan setup requires a scenario_id")
    for other in (china_setup.get("scenario_id", scenario_id),
                  theatre_map.get("_meta", {}).get("scenario_id")):
        if other != scenario_id:
            raise ValueError("Setup and theatre map scenario_id values disagree")
    factions = derive_factions(japan_setup, china_setup, theatre_map)
    aliases = build_alias_index(factions)
    faction_ids = {faction["id"] for faction in factions}
    nodes = theatre_map["nodes"]
    original_owners = {}
    for node_id, node in sorted(nodes.items()):
        if node["type"] == "land":
            original_owners[node_id] = {
                "source_original_owner": node["original_owner"],
                "original_faction_id": resolve_faction(node["original_owner"], aliases),
            }
    seen_territories = set()
    for row in china_setup.get("territories", []):
        node_id = row.get("node_id")
        if node_id not in nodes or nodes[node_id]["type"] != "land":
            raise ValueError(f"China setup territory is not retained land: {node_id}")
        if node_id in seen_territories:
            raise ValueError(f"Duplicate China setup territory: {node_id}")
        seen_territories.add(node_id)
        if row.get("owner_id") not in faction_ids:
            raise ValueError(f"{node_id}: unknown canonical setup owner {row.get('owner_id')!r}")
    return {
        "schema_version": 1,
        "scenario_id": scenario_id,
        "artifact_type": "scenario_faction_index",
        "status": "bridge_identity_data_not_playable",
        "alias_normalization": "remove_whitespace_then_casefold; preserve_punctuation_and_spelling",
        "scope": "Original national identity and approved setup control are separate. This index does not align factions, transfer possession or implement runtime state.",
        "factions": {faction["id"]: faction for faction in factions},
        "alias_to_id": aliases,
        "land_original_owners": original_owners,
    }


def build(map_path=DEFAULT_MAP, japan_setup_path=DEFAULT_JAPAN_SETUP,
          china_setup_path=DEFAULT_CHINA_SETUP, output_path=DEFAULT_OUTPUT):
    """Build reproducibly and atomically, without overwriting any source input."""
    paths = {"theatre_map": Path(map_path), "japan_setup": Path(japan_setup_path),
             "china_setup": Path(china_setup_path)}
    output_path = Path(output_path)
    if any(same_file(output_path, path) for path in paths.values()):
        raise ValueError("Output must not overwrite a source input")
    documents, sources = {}, {}
    for source_id, path in paths.items():
        documents[source_id], digest = load_document(path)
        sources[source_id] = {"path": portable_path(path), "sha256": digest}
    document = build_index(documents["japan_setup"], documents["china_setup"], documents["theatre_map"])
    document["sources"] = sources
    serialized = json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output_path.parent,
            prefix=f".{output_path.name}.", suffix=".tmp", delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(serialized)
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP, help="Frozen theatre map JSON")
    parser.add_argument("--japan-setup", type=Path, default=DEFAULT_JAPAN_SETUP)
    parser.add_argument("--china-setup", type=Path, default=DEFAULT_CHINA_SETUP)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        document = build(args.map, args.japan_setup, args.china_setup, args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"Wrote {args.output}: {len(document['factions'])} canonical factions, "
          f"{len(document['land_original_owners'])} retained land identities.")


if __name__ == "__main__":
    main()
