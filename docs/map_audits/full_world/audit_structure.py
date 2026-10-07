#!/usr/bin/env python3
"""Read-only, exhaustive inventory of the stored world graph, not a visual certification.

Run from anywhere with Python 3. Writes audit artifacts beside this script only.
Never invokes a production map builder or edits a game-content file.
"""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = HERE / "data"
MAP = ROOT / "game_content/maps/gw36_manual_map.json"


def save_json(name, value):
    (DATA / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def write_csv(name, rows):
    with (DATA / name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)


def main():
    DATA.mkdir(exist_ok=True)
    doc = json.loads(MAP.read_text())
    nodes = doc["nodes"]
    edges = {(src, e["neighbor_id"]): e for src, n in nodes.items() for e in n["neighbors"]}
    findings = []
    node_issues = defaultdict(list)
    edge_issues = defaultdict(list)
    counts = Counter()

    def flag(kind, ids, message, field, current, proposed=None, severity="review"):
        counts[kind] += 1
        issue_id = f"ST-{len(findings) + 1:04d}"
        findings.append({
            "id": issue_id, "check": kind, "category": "uncertain",
            "severity": severity, "subject": message, "node_ids": ids,
            "field": field, "current": current, "proposed": proposed,
            "evidence": [{"source": "game_content/maps/gw36_manual_map.json",
                          "method": "exhaustive stored-graph check"}],
            "confidence": "certain_observation_not_necessarily_a_map_error",
            "notes": "Diagnostic only; source inspection decides the correction."
        })
        for nid in ids:
            node_issues[nid].append(issue_id)
        if len(ids) == 2 and tuple(ids) in edges:
            edge_issues[tuple(ids)].append(issue_id)

    reciprocal = ["passable", "has_river", "railway_connection", "gauge_change",
                  "naval_facilities", "naval_facility_ids", "port_or_dock_connection",
                  "canal_or_strait", "narrow_crossing", "narrow_crossings",
                  "narrow_crossing_sea_zones"]
    node_terrains = {"normal", "mountain", "desert", "jungle", "marsh", "tundra", "sea"}
    facilities = defaultdict(list)
    for src, n in nodes.items():
        if n["id"] != src:
            flag("node_key_mismatch", [src], "Node ID differs from dictionary key", "id", n["id"], src, "error")
        if not n["neighbors"]:
            flag("isolated_node", [src], "No stored adjacency", "neighbors", [], severity="error")
        dests = [e["neighbor_id"] for e in n["neighbors"]]
        if len(set(dests)) != len(dests):
            flag("duplicate_neighbor", [src], "Repeated directed neighbor", "neighbors", dests, severity="error")
        terrain = n["terrain"] if isinstance(n["terrain"], list) else [n["terrain"]]
        if any(t not in node_terrains for t in terrain):
            flag("non_rulebook_node_terrain", [src], "Terrain category needs rules/source reconciliation", "terrain", n["terrain"])
        if n["type"] == "land" and (not isinstance(n["ipp_value"], int) or isinstance(n["ipp_value"], bool) or n["ipp_value"] < 0):
            flag("invalid_land_ipp", [src], "Invalid land IPP representation", "ipp_value", n["ipp_value"], severity="error")
        if len(n["node_facilities"]) != len(n["node_facility_ids"]):
            flag("node_facility_pair_length", [src], "Facility type/ID length mismatch", "node_facilities", n["node_facilities"], severity="error")
        for kind, identity in zip(n["node_facilities"], n["node_facility_ids"]):
            facilities[identity].append({"land": src, "kind": kind, "sea": None, "source": "node"})
            if "port" in kind or "dockyard" in kind or "shipyard" in kind:
                flag("naval_facility_without_sea_access", [src], "Node-held naval facility has no explicit access sea in this record", "node_facilities", {"type": kind, "id": identity})

    for (src, dst), e in edges.items():
        if dst not in nodes:
            flag("dangling_edge", [src, dst], "Target node is missing", "neighbor_id", dst, severity="error")
            continue
        if src == dst:
            flag("self_edge", [src, dst], "Self adjacency", "neighbor_id", dst, severity="error")
        rev = edges.get((dst, src))
        if rev is None:
            flag("missing_reverse", [src, dst], "No reciprocal adjacency", "neighbors", e, severity="error")
        elif src < dst:
            for field in reciprocal:
                if e.get(field) != rev.get(field):
                    flag("reciprocal_field_mismatch", [src, dst], "Reciprocal infrastructure differs", field,
                         {"forward": e.get(field), "reverse": rev.get(field)}, severity="error")
        a, b = nodes[src]["type"], nodes[dst]["type"]
        if a == b == "sea" and e["border_terrain"] != "sea":
            flag("sea_edge_land_terrain", [src, dst], "Sea-to-sea edge uses a land terrain default", "border_terrain", e["border_terrain"], "sea")
        if a == b == "land" and e["narrow_crossing"] and not e.get("narrow_crossing_sea_zones") and src < dst:
            flag("narrow_missing_blocking_seas", [src, dst], "Narrow crossing lacks blocking sea references", "narrow_crossing_sea_zones", None)
        if e["narrow_crossing"] and (a != "land" or b != "land") and src < dst:
            flag("narrow_on_non_land_pair", [src, dst], "Narrow capacity is attached to a coast/sea edge", "narrow_crossings", e["narrow_crossings"])
        for sid in e.get("narrow_crossing_sea_zones", []):
            if sid not in nodes or nodes[sid]["type"] != "sea":
                flag("invalid_blocking_sea", [src, dst], "Crossing blocker is not an existing sea", "narrow_crossing_sea_zones", sid, severity="error")
        if e["gauge_change"] and not e["railway_connection"]:
            flag("gauge_without_rail", [src, dst], "Gauge change without railway", "gauge_change", True, severity="error")
        if e["gauge_change"] and a != b and src < dst:
            flag("gauge_on_coast", [src, dst], "USSR ownership heuristic creates a rail-gauge change on a coastal facility access", "gauge_change", True)
        if not e["passable"] and e["railway_connection"] and src < dst:
            flag("rail_across_impassable", [src, dst], "Rail presence on an impassable connection requires source review", "railway_connection", True)
        if len(e["naval_facilities"]) != len(e["naval_facility_ids"]):
            flag("edge_facility_pair_length", [src, dst], "Facility type/ID length mismatch", "naval_facilities", e["naval_facilities"], severity="error")
        if a == "land" and b == "sea":
            for kind, identity in zip(e["naval_facilities"], e["naval_facility_ids"]):
                facilities[identity].append({"land": src, "kind": kind, "sea": dst, "source": "edge"})
        if e["port_or_dock_connection"] != bool(e["naval_facilities"]):
            flag("facility_boolean_mismatch", [src, dst], "Naval facility presence flag differs from its instances", "port_or_dock_connection", e["port_or_dock_connection"], severity="error")

    for identity, records in facilities.items():
        lands, kinds = {r["land"] for r in records}, {r["kind"] for r in records}
        if len(lands) > 1 or len(kinds) > 1:
            flag("facility_id_collision", sorted(lands), "Same physical facility ID used for different lands/types", "facility_id", {"id": identity, "records": records}, severity="error")

    remaining = set(nodes)
    components = []
    while remaining:
        stack = [min(remaining)]
        component = set()
        while stack:
            nid = stack.pop()
            if nid in component or nid not in nodes:
                continue
            component.add(nid)
            stack.extend(e["neighbor_id"] for e in nodes[nid]["neighbors"])
        remaining -= component
        components.append(sorted(component))

    node_rows = []
    for nid, n in nodes.items():
        outgoing = n["neighbors"]
        node_rows.append({
            "node_id": nid, "name": n["name"], "type": n["type"], "terrain": json.dumps(n["terrain"]),
            "ipp_value": n["ipp_value"], "original_owner": n["original_owner"], "current_owner": n["current_owner"],
            "is_city": n["is_city"], "is_capital": n["is_capital"], "is_victory_city": n["is_victory_city"],
            "land_neighbors": "|".join(e["neighbor_id"] for e in outgoing if nodes.get(e["neighbor_id"], {}).get("type") == "land"),
            "sea_neighbors": "|".join(e["neighbor_id"] for e in outgoing if nodes.get(e["neighbor_id"], {}).get("type") == "sea"),
            "node_facilities": json.dumps(n["node_facilities"]), "node_facility_ids": json.dumps(n["node_facility_ids"]),
            "structural_diagnostics": "|".join(node_issues[nid]),
            "source_verification": "See regional review and finding ledgers; structural pass is not visual certification"
        })
    edge_rows = []
    for (src, dst), e in edges.items():
        edge_rows.append({"source_id": src, "target_id": dst,
                          **{k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in e.items() if k != "neighbor_id"},
                          "narrow_crossing_sea_zones": json.dumps(e.get("narrow_crossing_sea_zones")),
                          "has_reverse": (dst, src) in edges, "structural_diagnostics": "|".join(edge_issues[(src, dst)])})
    summary = {
        "scope": "Every stored node and every directed edge; no source-image completeness implied",
        "node_count": len(nodes), "node_types": dict(Counter(n["type"] for n in nodes.values())),
        "directed_edge_count": len(edges), "undirected_pair_count": len({tuple(sorted(pair)) for pair in edges}),
        "edge_kinds": dict(Counter(f"{nodes[a]['type']}->{nodes.get(b, {}).get('type')}" for a, b in edges)),
        "component_sizes": sorted(map(len, components), reverse=True), "diagnostic_counts": dict(counts),
        "node_terrain_counts": dict(Counter(str(n["terrain"]) for n in nodes.values())),
        "edge_terrain_counts": dict(Counter(str(e["border_terrain"]) for e in edges.values())),
        "unique_facility_ids": len(facilities), "node_facility_count": sum(len(n["node_facilities"]) for n in nodes.values()),
        "directed_river_route_edges": sum(e["has_river"] for e in edges.values()),
        "directed_river_crossing_edges": sum(e["river_crossing"] for e in edges.values()),
        "directed_rail_edges": sum(e["railway_connection"] for e in edges.values()),
        "directed_special_fortification_edges": sum(bool(e["special_fortification"]) for e in edges.values()),
        "convoy_layer_present": any("convoy" in key.lower() for key in doc),
        "top_level_keys": list(doc),
        "checks_with_zero_findings": [k for k in ["node_key_mismatch", "isolated_node", "duplicate_neighbor", "invalid_land_ipp",
            "node_facility_pair_length", "dangling_edge", "self_edge", "missing_reverse", "reciprocal_field_mismatch",
            "invalid_blocking_sea", "gauge_without_rail", "rail_across_impassable", "edge_facility_pair_length",
            "facility_boolean_mismatch", "facility_id_collision"] if counts[k] == 0],
        "limitations": ["Graph consistency cannot establish printed adjacency, terrain, income or facility correctness.",
                        "Missing printed nodes are outside this inventory and listed in the regional findings.",
                        "Directional terrain and river_crossing are intentionally not required to be symmetric.",
                        "A rail/coast flag may mean access to a facility; it does not itself authorize a land unit to enter the sea."]
    }
    inputs = [MAP, ROOT / "game_content/maps/gw36_nation_home_country.json", ROOT / "game_content/maps/gw36map.png",
              ROOT / "tools/build_manual_map_json.py", ROOT / "tools/build_nation_home_country_json.py",
              ROOT / "game_content/scenarios/japan_china_1936/m0/convoy_audit.json",
              ROOT / "docs/map_audits/japan_and_nearby_seas.md",
              *sorted((ROOT / "game_content/rules").glob("*.pdf"))]
    manifest = {"audit_date": "2026-10-05", "files": [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
                  "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in inputs]}
    save_json("input_manifest.json", manifest)
    save_json("structural_summary.json", summary)
    save_json("structural_findings.json", findings)
    save_json("facility_inventory.json", facilities)
    write_csv("node_inventory.csv", node_rows)
    write_csv("edge_inventory.csv", edge_rows)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
