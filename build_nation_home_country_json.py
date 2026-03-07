import json
from collections import deque

MAP_PATH = "gw36_manual_map.json"
OUTPUT_PATH = "gw36_nation_home_country.json"


def load_nodes(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["nodes"]


def build_land_name_index(nodes):
    index = {}
    for node_id, node in nodes.items():
        if node.get("type") != "land":
            continue
        name = node["name"]
        if name in index:
            raise ValueError(f"Duplicate land node name: {name}")
        index[name] = node_id
    return index


def sort_zone_ids(zone_ids, nodes):
    return sorted(zone_ids, key=lambda node_id: (nodes[node_id]["name"], node_id))


def zone_names(zone_ids, nodes):
    return [nodes[node_id]["name"] for node_id in zone_ids]


def resolve_named_zones(names, name_to_id):
    zone_ids = []
    missing = []
    for name in names:
        node_id = name_to_id.get(name)
        if node_id:
            zone_ids.append(node_id)
        else:
            missing.append(name)
    return zone_ids, missing


def contiguous_us_home(nodes, name_to_id):
    start = name_to_id.get("Washington, D.C.")
    if start is None:
        return []

    allowed = {
        node_id
        for node_id, node in nodes.items()
        if node.get("type") == "land" and node.get("original_owner") == "United States"
    }
    if start not in allowed:
        return []

    visited = {start}
    queue = deque([start])

    while queue:
        node_id = queue.popleft()
        for edge in nodes[node_id].get("neighbors", []):
            neighbor_id = edge["neighbor_id"]
            if neighbor_id in allowed and neighbor_id not in visited:
                visited.add(neighbor_id)
                queue.append(neighbor_id)

    return sort_zone_ids(visited, nodes)


def make_entry(zone_ids, nodes, rulebook_definition, missing_named_zones=None):
    ordered_ids = sort_zone_ids(zone_ids, nodes)
    entry = {
        "rulebook_definition": rulebook_definition,
        "home_country_land_zone_ids": ordered_ids,
        "home_country_land_zone_names": zone_names(ordered_ids, nodes),
    }
    if missing_named_zones:
        entry["missing_named_zones_in_map"] = sorted(missing_named_zones)
    return entry


def build():
    nodes = load_nodes(MAP_PATH)
    name_to_id = build_land_name_index(nodes)

    nations = {}

    explicit_named = {
        "Germany": ["Berlin", "Western Germany", "Eastern Germany", "Bavaria"],
        "Japan": ["Tokyo", "Honshu", "Hokkaido", "Kyushu"],
        "Italy": ["Rome", "Northern Italy", "Lazio", "Southern Italy"],
        "Great Britain": ["London", "Northern England", "Southern England", "Scotland", "Northern Ireland"],
        "FEC": ["Punjab", "Maharashtra", "Delhi", "Benares", "Calcutta", "Southern India"],
        "France": ["Paris", "Picardy", "Alsace-Lorraine", "Southern France", "Aquitaine", "Normandy"],
        "Vichy": ["Corsica", "Southern France"],
    }

    for nation, names in explicit_named.items():
        ids, missing = resolve_named_zones(names, name_to_id)
        nations[nation] = make_entry(
            ids,
            nodes,
            "Explicit nation list from Home Country Land Zones table.",
            missing_named_zones=missing,
        )

    ussr_ids = [
        node_id
        for node_id, node in nodes.items()
        if node.get("type") == "land" and node.get("original_owner") == "Soviet Union"
    ]
    nations["USSR"] = make_entry(
        ussr_ids,
        nodes,
        "All originally possessed land zones with a Soviet roundel.",
    )

    anzac_ids = [
        node_id
        for node_id in nodes
        if node_id.startswith("land_aus_") or node_id.startswith("land_nz_")
    ]
    nations["ANZAC"] = make_entry(
        anzac_ids,
        nodes,
        "All land zones in Australia and New Zealand.",
    )

    usa_ids = contiguous_us_home(nodes, name_to_id)
    nations["USA"] = make_entry(
        usa_ids,
        nodes,
        "Contiguous USA zones adjoining Washington, D.C.",
    )

    china_ids = {
        node_id
        for node_id, node in nodes.items()
        if node.get("type") == "land" and node.get("original_owner") in {"China", "Mongolia"}
    }
    china_ids.update(
        node_id for node_id in nodes if node_id.startswith("land_manchuria_")
    )
    extra_ids, missing_extra = resolve_named_zones(["Formosa", "Hong Kong"], name_to_id)
    china_ids.update(extra_ids)

    ccp_kmt_rule = (
        "All zones originally with Chinese warlord/KMT/CCP/Manchukuo/Mongolian roundels, "
        "plus Formosa and Hong Kong."
    )
    nations["CCP"] = make_entry(
        list(china_ids),
        nodes,
        ccp_kmt_rule,
        missing_named_zones=missing_extra,
    )
    nations["KMT"] = make_entry(
        list(china_ids),
        nodes,
        ccp_kmt_rule,
        missing_named_zones=missing_extra,
    )

    nations["Free France"] = {
        "rulebook_definition": "Does not have a Home Country.",
        "home_country_land_zone_ids": [],
        "home_country_land_zone_names": [],
    }

    doc = {
        "_meta": {
            "game": "Global War 1936 v4.3",
            "source_rulebook_section": "Home Country (rulebook.txt lines 187-214)",
            "description": "Nation-level Home Country data extracted from the rulebook definition and mapped to land node ids.",
            "inputs": [MAP_PATH, "rulebook.txt"],
        },
        "non_listed_nation_rule": (
            "Non-listed nations: all originally possessed land zones except offshore territories."
        ),
        "nations": nations,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {OUTPUT_PATH} with {len(nations)} nation entries")


if __name__ == "__main__":
    build()
