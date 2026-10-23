"""Build reviewed world features without turning special routes into neighbors.

The authoring document is deliberately independent of the historical audit
reports. Unknown geography is recorded as unknown, never supplied by a nation
name, a convenient graph path, or an unreviewed reverse direction.
"""

from copy import deepcopy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FEATURE_SOURCE = ROOT / "game_content/maps/authoring/geographic_features.json"
RULES_PROFILE = "game_content/rules/map_geography_rules.json"
FEATURE_LAYERS = (
    "convoy_lines", "passages", "exceptional_routes", "narrow_crossings",
    "coast_restrictions",
)
NODE_REFERENCE_FIELDS = {
    "node_id", "land_id", "source_sea_id", "target_land_id",
    "land_ids", "controlling_land_ids", "sea_endpoints", "access_land_ids",
    "endpoint_ids", "via_land_ids", "blocking_sea_ids", "sea_zone_ids",
    "ordinary_edge_pairs",
}


def node_references(record):
    """Return explicit geographic references, without interpreting prose/IDs."""
    found = set()

    def flatten(value):
        if isinstance(value, str):
            found.add(value)
        elif isinstance(value, list):
            for item in value:
                flatten(item)

    def visit(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in NODE_REFERENCE_FIELDS:
                    flatten(item)
                elif key not in ("evidence", "source", "legacy_claim"):
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(record)
    return found


def _edges(nodes):
    return {
        (node_id, edge["neighbor_id"]): edge
        for node_id, node in nodes.items() for edge in node["neighbors"]
    }


def _require_nodes(nodes, node_ids, kind=None):
    for node_id in node_ids:
        if node_id not in nodes:
            raise ValueError(f"Geographic feature references missing node: {node_id}")
        if kind is not None and nodes[node_id]["type"] != kind:
            raise ValueError(f"Geographic feature requires {kind} node: {node_id}")


def validate_features(document):
    """Validate complete feature references and their physical prerequisites."""
    nodes = document["nodes"]
    edges = _edges(nodes)
    if "facilities" in document:
        registry = document["facilities"]
        if not isinstance(registry, dict):
            raise ValueError("facilities must be an ID-keyed registry")
        for identity, facility in registry.items():
            if not isinstance(facility, dict) or facility.get("id") != identity:
                raise ValueError(f"Canonical facility key/ID mismatch: {identity}")
            _require_nodes(nodes, [facility["land_id"]], "land")
            _require_nodes(nodes, facility["sea_accesses"], "sea")
            if len(set(facility["sea_accesses"])) != len(facility["sea_accesses"]):
                raise ValueError(f"Duplicate sea access for facility: {identity}")
            for sea in facility["sea_accesses"]:
                pair = facility["land_id"], sea
                if pair not in edges:
                    raise ValueError(f"Facility sea access has no coast: {identity}, {sea}")
                edge = edges[pair]
                if identity not in edge.get("naval_facility_ids", []):
                    raise ValueError(f"Facility access is absent from compatibility coast: {identity}, {sea}")
        for (left, right), edge in edges.items():
            for kind, identity in zip(edge.get("naval_facilities", []), edge.get("naval_facility_ids", [])):
                facility = registry.get(identity)
                if facility is None or facility.get("type") != kind:
                    raise ValueError(f"Coast references absent or differently typed facility: {identity}")
                sea = right if nodes[right]["type"] == "sea" else left
                land = left if nodes[left]["type"] == "land" else right
                if facility["land_id"] != land or sea not in facility["sea_accesses"]:
                    raise ValueError(f"Coast disagrees with canonical facility access: {identity}")
    all_ids = set()
    for layer in FEATURE_LAYERS:
        records = document.get(layer, [])
        if not isinstance(records, list):
            raise ValueError(f"{layer} must be a list")
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get("id"), str):
                raise ValueError(f"{layer} records need an ID")
            identity = record["id"]
            if identity in all_ids:
                raise ValueError(f"Duplicate geographic feature ID: {identity}")
            all_ids.add(identity)
            _require_nodes(nodes, node_references(record))

    for route in document.get("convoy_lines", []):
        seas = route["sea_zone_ids"]
        if not seas or len(seas) != len(set(seas)):
            raise ValueError(f"{route['id']}: convoy needs a non-repeating ordered sea path")
        _require_nodes(nodes, seas, "sea")
        for left, right in zip(seas, seas[1:]):
            if (left, right) not in edges or (right, left) not in edges:
                raise ValueError(f"{route['id']}: convoy path lacks {left} <-> {right}")
        endpoints = route.get("endpoints", [])
        if len(endpoints) != 2:
            raise ValueError(f"{route['id']}: convoy needs two resolved endpoints")
        for endpoint, sea in zip(endpoints, (seas[0], seas[-1])):
            node_id = endpoint.get("node_id")
            if endpoint.get("kind") not in ("land", "sea") or node_id not in nodes:
                raise ValueError(f"{route['id']}: unresolved convoy endpoint")
            _require_nodes(nodes, [node_id], endpoint["kind"])
            if endpoint["kind"] == "sea" and node_id != sea:
                raise ValueError(f"{route['id']}: sea endpoint differs from path terminal")
            if endpoint["kind"] == "land" and (node_id, sea) not in edges:
                raise ValueError(f"{route['id']}: land endpoint has no terminal coast")
        cap = route.get("maximum_ipp_loss")
        if cap is not None and (type(cap) is not int or cap < 0):
            raise ValueError(f"{route['id']}: invalid convoy loss cap")
        if (cap is None) != (route.get("loss_cap_status") == "no_numeric_cap_printed"):
            raise ValueError(f"{route['id']}: convoy loss-cap status disagrees")

    for passage in document.get("passages", []):
        _require_nodes(nodes, passage["controlling_land_ids"], "land")
        _require_nodes(nodes, passage["sea_endpoints"], "sea")
        for left, right in passage["ordinary_edge_pairs"]:
            if (left, right) not in edges or (right, left) not in edges:
                raise ValueError(f"{passage['id']}: missing passage access {left} <-> {right}")

    for crossing in document.get("narrow_crossings", []):
        _require_nodes(nodes, crossing["land_ids"], "land")
        _require_nodes(nodes, crossing["blocking_sea_ids"], "sea")
        if len(crossing["land_ids"]) != 2 or not crossing["blocking_sea_ids"]:
            raise ValueError(f"{crossing['id']}: crossing needs endpoints and blocking seas")
        left, right = crossing["land_ids"]
        for pair in ((left, right), (right, left)):
            edge = edges.get(pair)
            if edge is None or edge.get("railway_connection") is not False:
                raise ValueError(f"{crossing['id']}: narrow crossing cannot permit strategic rail")
            if edge.get("narrow_crossings") != crossing["unit_capacity"]:
                raise ValueError(f"{crossing['id']}: unit capacity differs from compatibility edge")

    for restriction in document.get("coast_restrictions", []):
        pair = restriction["source_sea_id"], restriction["target_land_id"]
        _require_nodes(nodes, [pair[0]], "sea")
        _require_nodes(nodes, [pair[1]], "land")
        if pair not in edges:
            raise ValueError(f"{restriction['id']}: restricted coast is missing")

    for route in document.get("exceptional_routes", []):
        if route.get("ordinary_adjacency") is not False:
            raise ValueError(f"{route['id']}: exceptional route cannot grant ordinary adjacency")
        if route["kind"] == "naval_special_transit":
            left, right = route["endpoint_ids"]
            if (left, right) in edges:
                raise ValueError(f"{route['id']}: restricted transit was added as an ordinary neighbor")


def apply_features(document):
    """Apply global approved facts after the regional graph corrections."""
    raw = FEATURE_SOURCE.read_bytes()
    authored = json.loads(raw)
    nodes = document["nodes"]
    edges = _edges(nodes)

    for node_id, node in nodes.items():
        if node["type"] == "sea":
            node["name"] = node_id.removeprefix("sea_").upper()
            node["original_owner"] = None
            node["current_owner"] = None
            node["is_city"] = False
            node["is_capital"] = False
            node["is_victory_city"] = False
            for edge in node["neighbors"]:
                if nodes[edge["neighbor_id"]]["type"] == "sea":
                    edge["border_terrain"] = "sea"
    for update in authored["victory_city_updates"]:
        nodes[update["node_id"]]["is_victory_city"] = update["is_victory_city"]

    for update in authored["narrow_crossing_blocker_updates"]:
        left, right = update["land_ids"]
        for pair in ((left, right), (right, left)):
            edge = edges[pair]
            if not edge.get("narrow_crossing"):
                raise ValueError(f"Expected reviewed narrow crossing: {pair}")
            edge["narrow_crossing_sea_zones"] = list(update["blocking_sea_ids"])
            edge["railway_connection"] = False
            edge["gauge_change"] = False

    for layer in ("convoy_lines", "passages", "exceptional_routes", "coast_restrictions"):
        document[layer] = deepcopy(authored[layer])

    # Old free-text annotations mixed controllers, coasts and actual transits.
    # Their replacement is a typed feature; keep only the verified edge aliases.
    for edge in edges.values():
        edge["canal_or_strait"] = None
        edge.pop("passage_ids", None)
        edge.pop("special_fortification", None)
    for passage in document["passages"]:
        for left, right in passage["ordinary_edge_pairs"]:
            for pair in ((left, right), (right, left)):
                if pair not in edges:
                    raise ValueError(f"{passage['id']}: missing reviewed access edge {pair}")
                edges[pair]["canal_or_strait"] = passage["name"]
                edges[pair]["passage_ids"] = [passage["id"]]

    crossings = []
    incomplete_crossings = []
    for (left, right), edge in sorted(edges.items()):
        if left >= right or not edge.get("narrow_crossing"):
            continue
        if nodes[left]["type"] != "land" or nodes[right]["type"] != "land":
            raise ValueError(f"Narrow crossing capacity belongs on land endpoints: {left}, {right}")
        seas = edge.get("narrow_crossing_sea_zones")
        if not seas:
            incomplete_crossings.append([left, right])
            continue
        reverse = edges[right, left]
        if seas != reverse.get("narrow_crossing_sea_zones"):
            raise ValueError(f"Narrow crossing blocking seas disagree: {left}, {right}")
        capacity = edge["narrow_crossings"]
        if capacity <= 0 or capacity != reverse["narrow_crossings"]:
            raise ValueError(f"Narrow crossing capacity disagrees: {left}, {right}")
        identity = "crossing_" + left.removeprefix("land_") + "__" + right.removeprefix("land_")
        crossings.append({
            "id": identity, "land_ids": [left, right], "unit_capacity": capacity,
            "blocking_sea_ids": list(seas), "rule_id": "narrow_crossing",
            "naval_transit_paths": None,
            "naval_transit_paths_review_status": "not_source_certified",
        })
        for direction in (edge, reverse):
            direction["unit_capacity"] = capacity
            direction["narrow_crossing_id"] = identity
            direction["railway_connection"] = False
            direction["gauge_change"] = False
    document["narrow_crossings"] = crossings

    for restriction in document["coast_restrictions"]:
        pair = restriction["source_sea_id"], restriction["target_land_id"]
        if pair not in edges:
            raise ValueError(f"Missing Great Barrier Reef coast: {pair}")
        edges[pair]["amphibious_assault_allowed"] = False
        edges[pair]["coast_restriction_ids"] = [restriction["id"]]

    document["rail_geography"] = {
        "region_ids": authored["rail_region_ids"],
        "membership_review_status": "not_source_certified",
        "memberships": {node_id: None for node_id, node in sorted(nodes.items()) if node["type"] == "land"},
        "rule_id": "strategic_rail",
        "notes": "Region capacities are defined; territory memberships remain unknown until individually reviewed.",
    }
    document.setdefault("_meta", {}).update({
        "geographic_features_source": FEATURE_SOURCE.relative_to(ROOT).as_posix(),
        "geographic_features_source_sha256": hashlib.sha256(raw).hexdigest(),
        "geographic_rules_profile": RULES_PROFILE,
        "feature_uncertainties": deepcopy(authored["deferred_schema_fields"]),
        "incomplete_legacy_narrow_crossings": incomplete_crossings,
    })
    validate_features(document)
    return document


def project_features(source, included, extracted_nodes):
    """Project complete routes; record cuts without inventing route fragments.

    Facilities keep their physical IDs. Their local sea-access list is projected
    like their corresponding coast edges, with removed accesses in the cut log.
    An intrinsic facility has no sea accesses and remains with its land node.
    """
    projected, cuts = {}, []
    retained_feature_ids = set()
    for layer in FEATURE_LAYERS:
        if layer not in source:
            continue
        projected[layer] = []
        for record in source[layer]:
            missing = sorted(node_references(record) - included)
            if missing:
                cuts.append({"layer": layer, "id": record["id"], "excluded_node_ids": missing})
            else:
                projected[layer].append(deepcopy(record))
                retained_feature_ids.add(record["id"])
    if "facilities" in source:
        projected["facilities"] = {}
        for facility_id, facility in source["facilities"].items():
            if facility["land_id"] not in included:
                cuts.append({"layer": "facilities", "id": facility_id, "excluded_node_ids": [facility["land_id"]]})
                continue
            seas = facility.get("sea_accesses", [])
            retained_seas = [sea for sea in seas if sea in included]
            excluded_seas = [sea for sea in seas if sea not in included]
            if excluded_seas:
                cuts.append({"layer": "facility_accesses", "id": facility_id, "excluded_node_ids": excluded_seas})
            if seas and not retained_seas:
                continue
            retained = deepcopy(facility)
            retained["sea_accesses"] = retained_seas
            projected["facilities"][facility_id] = retained
    if "rail_geography" in source:
        rail = deepcopy(source["rail_geography"])
        rail["memberships"] = {node_id: value for node_id, value in rail.get("memberships", {}).items() if node_id in included}
        projected["rail_geography"] = rail
    for node_id, node in extracted_nodes.items():
        for edge in node["neighbors"]:
            for feature_id in edge.get("passage_ids", []):
                if feature_id not in retained_feature_ids:
                    raise ValueError(f"{node_id}: retained passage requires excluded controller/access nodes: {feature_id}")
            if "facilities" in projected:
                for facility_id in edge.get("naval_facility_ids", []):
                    if facility_id not in projected["facilities"]:
                        raise ValueError(f"{node_id}: retained coast references missing facility {facility_id}")
    return projected, sorted(cuts, key=lambda row: (row["layer"], row["id"]))
