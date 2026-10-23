"""Apply reviewed, explicit world-map facts without interpreting audit prose.

The historical builder supplies legacy records. Source-backed authoring operations
replace only reviewed fields. New fields are unknown until explicitly authored;
directional annotations never invent physical connections or reverse annotations.
"""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHORING = ROOT / "game_content/maps/authoring"
REGIONS = ("global_review", "americas_atlantic", "europe_africa_middle_east", "asia_pacific", "adopted_directional_values", "verified_existing_rail_gauges")
NODE_DEFAULTS = {
    "name": None, "type": "land", "terrain": None, "ipp_value": None,
    "original_owner": None, "current_owner": None, "is_city": None,
    "is_capital": None, "is_victory_city": False,
    "node_facilities": [], "node_facility_ids": [], "neighbors": [],
}
EDGE_DEFAULTS = {
    "border_terrain": None, "passable": None, "has_river": None,
    "river_crossing": None, "railway_connection": None, "gauge_change": None,
    "naval_facilities": [], "naval_facility_ids": [],
    "port_or_dock_connection": False, "canal_or_strait": None,
    "narrow_crossing": False, "narrow_crossings": 0,
    "source_rail_gauge": None, "target_rail_gauge": None,
}


def load(name):
    return json.loads((AUTHORING / f"{name}.json").read_text())


def edge(nodes, a, b):
    return next((e for e in nodes.get(a, {}).get("neighbors", []) if e["neighbor_id"] == b), None)


def pair_key(a, b):
    return tuple(sorted((a, b)))


def apply_authoring(document):
    nodes = document["nodes"]
    sources = {}
    operations = []
    findings = {}
    for name in REGIONS:
        path = AUTHORING / f"{name}.json"
        if not path.exists():
            if name == "verified_existing_rail_gauges":
                continue
            raise FileNotFoundError(path)
        data = load(name)
        sources[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        findings.update(data.get("findings", {}))
        operations.extend(dict(o, authoring_source=str(path.relative_to(ROOT))) for o in data["operations"])

    # A visually verified facility access independently establishes that coast.
    # This uses the re-audited symbol/access record, never a legacy port default.
    for row in load("naval_facilities")["territories"]:
        for facility in row["facilities"]:
            for sea in facility["sea_accesses"]:
                operations.append({"op":"set_edge","phase":40,
                    "source_id":row["land_id"],"target_id":sea,"reciprocal":True,
                    "values":{"passable":True},"finding_ids":facility.get("finding_ids",[]),
                    "evidence":facility.get("evidence",[]),
                    "authoring_source":"game_content/maps/authoring/naval_facilities.json"})

    global_review = load("global_review")
    rejected_pairs = {pair_key(o["source_id"], o["target_id"]) for o in operations if o["op"] == "remove_edge"}
    uncertain_pairs = {pair_key(r["source_id"], r["target_id"]) for r in global_review["physical_reviews"] if r["relation_status"] == "uncertain"}
    overlap = rejected_pairs & uncertain_pairs
    if overlap:
        raise ValueError(f"An operation would delete deferred physical pairs: {overlap}")
    review = {
        "schema_version": 2,
        "baseline_commit": "eeb5e90",
        "baseline_map_sha256": global_review["baseline_map_sha256"],
        "authoring_sources": sources,
        "legacy_field_policy": "Unlisted fields retained from the checkpoint are unreviewed, not source-certified. Unknown new fields are null. An adjacency review certifies no directional attributes.",
        "physical_pairs": {"|".join(pair_key(r["source_id"], r["target_id"])): {
            "status": r["relation_status"], "source_reviews": r["regional_source_reviews"]
        } for r in global_review["physical_reviews"]},
        "field_reviews": {}, "findings": findings,
        "deferred_findings": global_review["deferred_findings"],
        "skipped_annotations_on_absent_edges": [],
        "legacy_authoring_confidence": {},
    }
    for src,node in nodes.items():
        for e in node["neighbors"]:
            confidence=e.pop("authoring_confidence", None)
            if confidence is not None:
                review["legacy_authoring_confidence"][f"{src}/{e['neighbor_id']}"]={"confidence":confidence,"status":"legacy_estimate_not_source_verification"}

    def annotate(path, op, fields):
        for field in fields:
            review["field_reviews"][f"{path}/{field}"] = {
                "status": op.get("review_status", "confirmed") if op.get("values", {}).get(field) is not None else "unknown",
                "finding_ids": op.get("finding_ids", []),
                "source": op["authoring_source"],
                "evidence": op.get("evidence", []),
            }

    for op in sorted(operations, key=lambda o: o["phase"]):
        kind = op["op"]
        values = deepcopy(op.get("values", {}))
        if kind in ("upsert_node", "set_node"):
            nid = op["node_id"]
            if nid not in nodes:
                if kind != "upsert_node":
                    raise ValueError(f"Attribute for missing node: {nid}")
                nodes[nid] = dict(deepcopy(NODE_DEFAULTS), id=nid)
            if 'node_facilities' in values and 'node_facility_ids' not in values:
                old_ids=dict(zip(nodes[nid].get('node_facilities',[]),nodes[nid].get('node_facility_ids',[])))
                values['node_facility_ids']=[old_ids.get(t,f"facility_{nid.removeprefix('land_')}_{t}") for t in values['node_facilities']]
            nodes[nid].update(values)
            annotate(f"nodes/{nid}", op, values)
        elif kind == "remove_node":
            nid = op["node_id"]
            nodes.pop(nid, None)
            for node in nodes.values():
                node["neighbors"] = [e for e in node["neighbors"] if e["neighbor_id"] != nid]
        elif kind in ("set_edge", "remove_edge"):
            a, b = op["source_id"], op["target_id"]
            if a == b:
                raise ValueError(f"Self connection: {a}")
            directions = [(a, b)] + ([(b, a)] if op.get("reciprocal") else [])
            if kind == "remove_edge":
                for src, dst in directions:
                    if src in nodes:
                        nodes[src]["neighbors"] = [e for e in nodes[src]["neighbors"] if e["neighbor_id"] != dst]
                continue
            if pair_key(a, b) in rejected_pairs:
                review["skipped_annotations_on_absent_edges"].append({"source_id": a, "target_id": b, "finding_ids": op.get("finding_ids", []), "reason": "Reviewed physical deletion takes precedence."})
                continue
            if a not in nodes or b not in nodes:
                raise ValueError(f"Operation references missing node: {a}, {b}")
            for src, dst in directions:
                e = edge(nodes, src, dst)
                if e is None:
                    if op["phase"] >= 50:
                        review["skipped_annotations_on_absent_edges"].append({"source_id":src,"target_id":dst,"finding_ids":op.get("finding_ids",[]),"reason":"No approved physical connection; field annotation cannot invent one."})
                        continue
                    e = dict(deepcopy(EDGE_DEFAULTS), neighbor_id=dst)
                    nodes[src]["neighbors"].append(e)
                    review["physical_pairs"]["|".join(pair_key(src,dst))] = {"status":"confirmed","finding_ids":op.get("finding_ids",[]),"evidence":op.get("evidence",[])}
                directional_values = deepcopy(values)
                if src == b and op.get("reciprocal"):
                    if "source_rail_gauge" in values or "target_rail_gauge" in values:
                        directional_values["source_rail_gauge"] = values.get("target_rail_gauge")
                        directional_values["target_rail_gauge"] = values.get("source_rail_gauge")
                e.update(directional_values)
                annotate(f"edges/{src}/{dst}", op, directional_values)
        else:
            raise ValueError(f"Unknown authoring operation: {kind}")

    # Never silently repair a missing reverse by copying directional terrain.
    for src, node in nodes.items():
        for e in list(node["neighbors"]):
            dst = e["neighbor_id"]
            if edge(nodes, dst, src) is None:
                raise ValueError(f"Missing independently represented reverse: {src}->{dst}")
            e.pop("special_fortification", None)
            if node["type"] == "sea" and nodes[dst]["type"] == "sea":
                e["railway_connection"] = False
                e["source_rail_gauge"] = None
                e["target_rail_gauge"] = None
            if node["type"] == "land" and nodes[dst]["type"] == "sea":
                e["border_terrain"] = "coast"
            if e.get("narrow_crossing"):
                e["railway_connection"] = False
            if e.get("railway_connection") is False:
                e["gauge_change"] = False
                e["source_rail_gauge"] = None
                e["target_rail_gauge"] = None
            else:
                left, right = e.get("source_rail_gauge"), e.get("target_rail_gauge")
                e["source_rail_gauge"], e["target_rail_gauge"] = left, right
                e["gauge_change"] = left != right if left and right and e.get("railway_connection") is True else None
        node["neighbors"].sort(key=lambda e:e["neighbor_id"])
        if node["type"] == "land":
            rails=[e.get("railway_connection") for e in node["neighbors"] if nodes[e["neighbor_id"]]["type"]=="land"]
            node["printed_rail_coverage"] = True if True in rails else None

    apply_facilities(document, review)
    document["_meta"].update({
        "schema_version": 2,
        "description": "World geography generated from the legacy transcription and reconciled, source-backed authoring records.",
        "build": {"method":"reviewed_authoring_operations","coverage":"full_world_with_explicit_unreviewed_fields"},
        "warnings": [
            "Physical geography is reviewed within recorded field scopes; legacy attributes are not automatically certified.",
            "Uncertain findings and nested fields remain deferred in gw36_manual_map_review.json.",
            "Canada seam rulings and adopted China-theatre directional values remain project decisions; their source status is preserved.",
            "Special routes and geographic rule references do not implement runtime permissions, combat or scenario setup.",
        ],
        "authoring_directory": "game_content/maps/authoring",
        "unknown_values": "null means not source-reviewed; false means an authored negative or a retained legacy value whose review status is in the sidecar.",
        "field_review_file": "gw36_manual_map_review.json",
        "current_owner_semantics": "Legacy setup hint only; original_owner is static identity. Neither current_owner nor is_capital is runtime state.",
        "rail_semantics": "Land-border railway_connection describes printed rail. Legacy coast railway_connection artwork is retained pending AM-229 and grants no rail movement into a sea. printed_rail_coverage is true when a land-border railroad establishes coverage, otherwise unknown. Gauge changes require verified gauges on both sides, never ownership.",
    })
    review['derived_fields']={
        'gauge_change':{'rule':'Compare verified source_rail_gauge and target_rail_gauge on a confirmed railway; false if no railway, otherwise null.','finding_ids':['WG-015'],'source':'Rulebook 1.6 p10'},
        'printed_rail_coverage':{'rule':'A land-border railway establishes whole-zone coverage; absence of such a record does not prove no internal railway.','source':'Rulebook 13.2.8 p98'},
        'sea_identity':{'rule':'Printed sea code is canonical; sea owner/city/capital/victory-city fields are inapplicable.','finding_ids':['WG-013'],'source':'Rulebook 1.2 p10'},
        'naval_facility_arrays':{'rule':'Project canonical facility IDs/types onto each reviewed sea access. Unknown inventory is marked partial.'},
    }
    document["nodes"] = dict(sorted(nodes.items()))
    return review


def apply_facilities(document, review):
    data = load("naval_facilities")
    nodes = document["nodes"]
    registry = {}
    reviewed_lands = {r["land_id"] for r in data["territories"]}
    for src,node in nodes.items():
        for e in node["neighbors"]:
            if src in reviewed_lands or e["neighbor_id"] in reviewed_lands:
                e["naval_facilities"], e["naval_facility_ids"] = [], []
                e["port_or_dock_connection"] = False
    for row in data["territories"]:
        land = row["land_id"]
        if land not in nodes:
            raise ValueError(f"Facility roster references absent territory: {land}")
        n=nodes[land]
        n['naval_facility_inventory_status']='partial' if row['review_status'] in ('uncertain','type_unresolved') else 'confirmed'
        # Node arrays are intrinsic facilities only, not unlocated naval ports.
        pairs=[(t,i) for t,i in zip(n.get("node_facilities",[]),n.get("node_facility_ids",[])) if t=="airfield"]
        if "airfield" in n.get("node_facilities",[]) and not pairs:
            pairs=[("airfield",f"facility_{land.removeprefix('land_')}_airfield")]
        n["node_facilities"],n["node_facility_ids"]=[t for t,i in pairs],[i for t,i in pairs]
        for facility in row["facilities"]:
            f=deepcopy(facility)
            if f["id"] in registry:
                raise ValueError(f"Physical facility ID collision: {f['id']}")
            registry[f["id"]]=f
            for sea in f["sea_accesses"]:
                for a,b in ((land,sea),(sea,land)):
                    e=edge(nodes,a,b)
                    if e is None:
                        raise ValueError(f"Facility {f['id']} has no independently reviewed coast {a}->{b}")
                    e["naval_facilities"].append(f["type"])
                    e["naval_facility_ids"].append(f["id"])
                    e["port_or_dock_connection"]=True
    for unresolved in data['unresolved_facilities']:
        lands=[unresolved['land_id']] if unresolved.get('land_id') else unresolved['candidate_land_ids']
        seas=unresolved.get('verified_sea_accesses',unresolved.get('sea_accesses',[]))
        for land in lands:
            for sea in seas:
                for a,b in ((land,sea),(sea,land)):
                    e=edge(nodes,a,b)
                    if e is None:raise ValueError(f'Unresolved facility has missing verified coast: {a}->{b}')
                    e['naval_facility_inventory_status']='partial'
                    if not e['naval_facility_ids']:e['port_or_dock_connection']=None
    for land,n in nodes.items():
        if n["type"]!='land':continue
        types=n.get("node_facilities",[])
        ids=n.get("node_facility_ids",[])
        if len(types)!=len(ids):
            ids=[f"facility_{land.removeprefix('land_')}_{t}" for t in types]
            n["node_facility_ids"]=ids
        for kind,fid in zip(types,ids):
            if kind!='airfield':raise ValueError(f"Unlocated naval facility retained: {land}/{kind}")
            ref=review['field_reviews'].get(f'nodes/{land}/node_facilities')
            registry[fid]={'id':fid,'land_id':land,'type':kind,'sea_accesses':[],
                           'review_status':'confirmed' if ref else 'legacy_unreviewed',
                           'source_review':ref}
    document["facilities"]=dict(sorted(registry.items()))
    review["unresolved_facilities"]=data["unresolved_facilities"]
    review["facility_id_migrations"]=data["id_migrations"]
    review["authoring_sources"]["game_content/maps/authoring/naval_facilities.json"]=hashlib.sha256((AUTHORING/'naval_facilities.json').read_bytes()).hexdigest()


def validate_world(document):
    nodes=document['nodes']
    symmetric=('passable','has_river','railway_connection','gauge_change','naval_facilities','naval_facility_ids','narrow_crossing','narrow_crossings','narrow_crossing_sea_zones')
    for a,n in nodes.items():
        seen=set()
        for e in n['neighbors']:
            b=e['neighbor_id']
            if b not in nodes or b==a or b in seen:raise ValueError(f'Invalid adjacency {a}->{b}')
            seen.add(b)
            reverse=edge(nodes,b,a)
            if reverse is None:raise ValueError(f'Missing reverse {a}->{b}')
            for k in symmetric:
                if e.get(k)!=reverse.get(k):raise ValueError(f'Asymmetric {k}: {a}->{b}: {e.get(k)!r}/{reverse.get(k)!r}')
            if e.get('railway_connection') and (e.get('passable') is False or e.get('narrow_crossing')):
                raise ValueError(f'Rail crosses forbidden land route: {a}->{b}')
    if edge(nodes,'sea_a9','sea_p1') or edge(nodes,'sea_a9','sea_a14'):
        raise ValueError('Exceptional transit leaked into ordinary adjacency')
