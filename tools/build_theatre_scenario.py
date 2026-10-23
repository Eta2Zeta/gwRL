"""Extract a closed map projection without changing any retained game data.

This builds map data, not a playable scenario or an initial unit setup. Campaign
configuration is retained as provenance. Explicit feature-layer exclusions are
applied without changing the authoritative world map or retained node/edge data.

    ./.venv/bin/python tools/build_theatre_scenario.py

Only explicit manifest IDs are retained. Every outbound neighbor entry outside
that set is removed; no substitute external routes or reinforcement interfaces
are created. Internal directional terrain/crossing data is copied verbatim.
"""

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile

try:
    from world_map_features import project_features, validate_features
except ModuleNotFoundError:
    from tools.world_map_features import project_features, validate_features


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP = ROOT / "game_content/maps/gw36_manual_map.json"
DEFAULT_MANIFEST = ROOT / "game_content/scenarios/japan_china_1936/manifest.json"
DEFAULT_OUTPUT = DEFAULT_MANIFEST.with_name("map.json")

BOOLEAN_EDGE_FIELDS = (
    "passable", "has_river", "river_crossing", "railway_connection",
    "gauge_change", "port_or_dock_connection", "narrow_crossing",
)
NULLABLE_EDGE_FIELDS = {
    "passable", "has_river", "river_crossing", "railway_connection", "gauge_change",
}
RECIPROCAL_EDGE_FIELDS = (
    "passable", "has_river", "railway_connection", "gauge_change",
    "naval_facilities", "naval_facility_ids", "port_or_dock_connection",
    "canal_or_strait", "narrow_crossing", "narrow_crossings",
)


def unique_object(pairs):
    """Do not let JSON silently discard duplicate object keys."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"Non-finite JSON number is not allowed: {value}")


def load_document(path):
    raw = path.read_bytes()
    try:
        document = json.loads(
            raw, object_pairs_hook=unique_object, parse_constant=reject_constant
        )
    except (ValueError, UnicodeError) as error:
        raise ValueError(f"Invalid JSON in {path}: {error}") from error
    if not isinstance(document, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return document, hashlib.sha256(raw).hexdigest()


def validate_facilities(record, facilities_key, ids_key, location):
    facilities, ids = record.get(facilities_key), record.get(ids_key)
    if not isinstance(facilities, list) or not isinstance(ids, list):
        raise ValueError(f"{location}: {facilities_key} and {ids_key} must be lists")
    if len(facilities) != len(ids):
        raise ValueError(f"{location}: facility types and IDs must have equal lengths")
    if any(not isinstance(value, str) or not value for value in facilities + ids):
        raise ValueError(f"{location}: facility types and IDs must be nonempty strings")
    if len(ids) != len(set(ids)):
        raise ValueError(f"{location}: duplicate facility IDs")


def validate_source(source):
    """Validate IDs and topology globally; never silently repair a bad source."""
    nodes = source.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        raise ValueError("Source map must contain a nonempty 'nodes' object")
    if not isinstance(source.get("_meta", {}), dict):
        raise ValueError("Source map '_meta' must be an object")
    version = source.get("_meta", {}).get("schema_version", 1)
    if type(version) is not int or version not in (1, 2):
        raise ValueError("Source map schema_version must be 1 or 2")
    edges = {}
    for node_id, node in nodes.items():
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("Source node IDs must be nonempty strings")
        if not isinstance(node, dict) or node.get("id") != node_id:
            raise ValueError(f"Source node key/id mismatch: {node_id}")
        if node.get("type") not in ("land", "sea"):
            raise ValueError(f"{node_id}: type must be 'land' or 'sea'")
        terrain = node.get("terrain")
        terrains = terrain if isinstance(terrain, list) else [terrain]
        if not (version == 2 and terrain is None) and (
                not terrains or any(not isinstance(value, str) or not value for value in terrains)):
            raise ValueError(f"{node_id}: terrain must be a string or nonempty string list")
        if not isinstance(node.get("neighbors"), list):
            raise ValueError(f"{node_id}: neighbors must be a list")
        validate_facilities(node, "node_facilities", "node_facility_ids", node_id)
    # Validate every node record before dereferencing neighbor/blocking-sea
    # records; malformed targets must produce a readable error, not AttributeError.
    for node_id, node in nodes.items():
        for edge in node["neighbors"]:
            if not isinstance(edge, dict):
                raise ValueError(f"{node_id}: neighbor entries must be objects")
            neighbor_id = edge.get("neighbor_id")
            if not isinstance(neighbor_id, str) or neighbor_id not in nodes:
                raise ValueError(f"{node_id}: unknown neighbor {neighbor_id!r}")
            if neighbor_id == node_id:
                raise ValueError(f"{node_id}: self-loop is not allowed")
            pair = (node_id, neighbor_id)
            if pair in edges:
                raise ValueError(f"{node_id}: duplicate neighbor {neighbor_id}")
            location = f"{node_id} -> {neighbor_id}"
            for field in BOOLEAN_EDGE_FIELDS:
                value = edge.get(field)
                unknown = version == 2 and field in NULLABLE_EDGE_FIELDS and value is None and field in edge
                if (version == 2 and field == "port_or_dock_connection"
                        and value is None and field in edge
                        and edge.get("naval_facility_inventory_status") == "partial"):
                    unknown = True
                if type(value) is not bool and not unknown:
                    raise ValueError(f"{location}: {field} must be a boolean")
            if edge["gauge_change"] and edge["railway_connection"] is not True:
                raise ValueError(f"{location}: gauge_change requires a railway")
            count = edge.get("narrow_crossings")
            if type(count) is not int or count < 0:
                raise ValueError(f"{location}: narrow_crossings must be a nonnegative integer")
            if edge["narrow_crossing"] != (count > 0):
                raise ValueError(f"{location}: narrow crossing flag/count disagree")
            if "narrow_crossing_sea_zones" in edge:
                seas = edge["narrow_crossing_sea_zones"]
                if (not edge["narrow_crossing"] or node["type"] != "land"
                        or nodes[neighbor_id].get("type") != "land"):
                    raise ValueError(f"{location}: blocking seas require a direct land narrow crossing")
                if (not isinstance(seas, list) or not seas
                        or any(not isinstance(sea, str) or sea not in nodes
                               or nodes[sea].get("type") != "sea" for sea in seas)):
                    raise ValueError(f"{location}: narrow_crossing_sea_zones must reference sea nodes")
                if len(seas) != len(set(seas)):
                    raise ValueError(f"{location}: duplicate blocking sea IDs")
                if edge["railway_connection"]:
                    raise ValueError(f"{location}: strategic rail cannot cross a narrow crossing")
            terrain = edge.get("border_terrain")
            terrains = terrain if isinstance(terrain, list) else [terrain]
            if not (version == 2 and terrain is None and "border_terrain" in edge) and (
                    not terrains or any(not isinstance(item, str) or not item for item in terrains)):
                raise ValueError(f"{location}: border_terrain must be a string or nonempty string list")
            validate_facilities(edge, "naval_facilities", "naval_facility_ids", location)
            edges[pair] = edge
    for source_id, target_id in edges:
        if (target_id, source_id) not in edges:
            raise ValueError(f"Missing reverse neighbor: {target_id} -> {source_id}")
    validate_features(source)
    return nodes, edges


def validate_manifest(manifest, nodes):
    if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise ValueError("Manifest schema_version must be 1")
    if not isinstance(manifest.get("scenario_id"), str) or not manifest["scenario_id"].strip():
        raise ValueError("Manifest scenario_id must be a nonempty string")
    if manifest.get("boundary_policy", "closed") != "closed":
        raise ValueError("Only boundary_policy='closed' is supported")
    requested = manifest.get("included_node_ids")
    if not isinstance(requested, list) or not requested:
        raise ValueError("Manifest included_node_ids must be a nonempty list")
    if any(not isinstance(node_id, str) or not node_id for node_id in requested):
        raise ValueError("Manifest included_node_ids must contain nonempty strings")
    if len(requested) != len(set(requested)):
        raise ValueError("Manifest included_node_ids contains duplicate IDs")
    missing = sorted(set(requested) - nodes.keys())
    if missing:
        raise ValueError("Manifest requests missing source nodes: " + ", ".join(missing))
    excluded_layers = manifest.get("excluded_feature_layers", [])
    if (not isinstance(excluded_layers, list)
            or any(layer != "convoy_lines" for layer in excluded_layers)
            or len(excluded_layers) != len(set(excluded_layers))):
        raise ValueError("Manifest excluded_feature_layers must be a unique list containing only 'convoy_lines'")
    return set(requested)


def extract_document(source, manifest):
    """Return a deep-copied induced subgraph and a non-navigable cut audit."""
    nodes, edges = validate_source(source)
    included = validate_manifest(manifest, nodes)
    for (source_id, target_id), edge in edges.items():
        if source_id in included and target_id in included:
            reverse = edges[target_id, source_id]
            for field in RECIPROCAL_EDGE_FIELDS:
                if field not in edge or field not in reverse or edge[field] != reverse[field]:
                    raise ValueError(
                        f"{source_id} <-> {target_id}: reciprocal {field} disagrees"
                    )
            if edge.get("narrow_crossing_sea_zones") != reverse.get("narrow_crossing_sea_zones"):
                raise ValueError(f"{source_id} <-> {target_id}: reciprocal narrow_crossing_sea_zones disagrees")
            missing_seas = set(edge.get("narrow_crossing_sea_zones", [])) - included
            if missing_seas:
                raise ValueError(
                    f"{source_id} <-> {target_id}: retained crossing has excluded blocking seas: "
                    + ", ".join(sorted(missing_seas))
                    + "; include them or omit a crossing endpoint; extraction never rewrites retained rules"
                )
    extracted, cuts = {}, []
    for node_id in sorted(included):
        node = copy.deepcopy(nodes[node_id])
        node["neighbors"] = [
            edge for edge in node["neighbors"] if edge["neighbor_id"] in included
        ]
        extracted[node_id] = node
        cuts.extend(
            {"source_id": node_id, "excluded_neighbor_id": edge["neighbor_id"]}
            for edge in nodes[node_id]["neighbors"]
            if edge["neighbor_id"] not in included
        )
    cuts.sort(key=lambda cut: (cut["source_id"], cut["excluded_neighbor_id"]))
    feature_layers, feature_cuts = project_features(source, included, extracted)
    feature_exclusions = []
    for layer in manifest.get("excluded_feature_layers", []):
        # Disable the entire campaign layer, including routes whose complete
        # geography is inside the boundary. Keep source records and their IDs
        # available in world data; no clipped or locally active convoy is made.
        if layer in feature_layers:
            feature_exclusions.append({
                "layer": layer,
                "reason": "disabled_by_scenario_manifest",
                "excluded_feature_ids": [record["id"] for record in feature_layers[layer]],
            })
            feature_layers[layer] = []
    result = {
        "_meta": {
            "schema_version": source.get("_meta", {}).get("schema_version", 1),
            "scenario_id": manifest["scenario_id"],
            "artifact_type": "closed_theatre_map",
            "boundary_policy": "closed",
            "source_map_meta": copy.deepcopy(source.get("_meta", {})),
            "scenario_manifest": copy.deepcopy(manifest),
            "extracted_node_count": len(extracted),
            "excluded_neighbor_count": len(cuts),
            "boundary_cuts": cuts,
            "notes": [
                "Static map projection only; not a playable scenario or initial unit setup.",
                "Internal node/edge data is unchanged; all excluded neighbors are removed.",
                "boundary_cuts is provenance only and must not create movement or supply routes.",
            ],
        },
        "nodes": extracted,
    }
    result.update(feature_layers)
    if feature_layers:
        result["_meta"]["feature_cuts"] = feature_cuts
        result["_meta"]["notes"].append(
            "Complete geographic routes are retained only when all endpoints, path nodes and controllers are included; facility sea accesses follow retained coasts."
        )
    if feature_exclusions:
        result["_meta"]["feature_exclusions"] = feature_exclusions
        result["_meta"]["notes"].append(
            "Manifest-disabled feature layers remain empty even when their complete geography is retained."
        )
    validate_features(result)
    return result


def portable_path(path):
    """Use repo-relative provenance without embedding a user's home directory."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def same_file(left, right):
    return left.resolve() == right.resolve() or (
        left.exists() and right.exists() and left.samefile(right)
    )


def build(map_path=DEFAULT_MAP, manifest_path=DEFAULT_MANIFEST, output_path=None):
    map_path, manifest_path = Path(map_path), Path(manifest_path)
    output_path = Path(output_path) if output_path is not None else manifest_path.with_name("map.json")
    if same_file(output_path, map_path) or same_file(output_path, manifest_path):
        raise ValueError("Output must not overwrite the source map or manifest")
    source, source_hash = load_document(map_path)
    manifest, manifest_hash = load_document(manifest_path)
    document = extract_document(source, manifest)
    document["_meta"].update({
        "source_map": portable_path(map_path),
        "source_map_sha256": source_hash,
        "manifest": portable_path(manifest_path),
        "manifest_sha256": manifest_hash,
    })
    serialized = json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    # Validation and serialization finish before even creating an output directory.
    # Replacing a completed temporary file prevents partial JSON on interruption.
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
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP, help="Authoritative full map JSON")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Explicit tile selection JSON")
    parser.add_argument("--output", type=Path, help="Extracted map JSON (default: map.json beside the manifest)")
    args = parser.parse_args()
    output_path = args.output if args.output is not None else args.manifest.with_name("map.json")
    try:
        document = build(args.map, args.manifest, output_path)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    meta = document["_meta"]
    print(
        f"Wrote {output_path}: {meta['extracted_node_count']} nodes, "
        f"{meta['excluded_neighbor_count']} excluded neighbor entries removed "
        f"(boundary_policy=closed)."
    )


if __name__ == "__main__":
    main()
