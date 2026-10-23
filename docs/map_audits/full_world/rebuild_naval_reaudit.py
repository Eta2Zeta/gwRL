#!/usr/bin/env python3
"""Validate source-authored naval reviews and render their proposed final roster.

This reads the checkpoint map for historical comparison. It never writes production data.
Run consolidate.py first so finding references reflect the latest authored review.
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from audit_baseline import read_baseline_map

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = HERE / "data"
REGIONS = ["americas_atlantic", "europe_africa_middle_east", "asia_pacific"]
TYPES = {
    "minor_port", "major_port", "minor_dockyard", "major_dockyard",
    "minor_shipyard", "major_shipyard", "seaplane_base", "submarine_base",
}


def dump(name, value):
    (DATA / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def evidence_path(value):
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path if str(path).startswith(("docs/", "game_content/")) else HERE / path


def validate_evidence(evidence, label, errors):
    for item in evidence:
        if not isinstance(item, dict):
            errors.append(f"Evidence needs explicit source/crop: {label}")
            continue
        if not item.get("source") or not evidence_path(item["source"]).exists():
            errors.append(f"Missing evidence source: {label}")
        if not item.get("crop") or not evidence_path(item["crop"]).exists():
            errors.append(f"Missing evidence crop: {label}")
        rect = item.get("rectangle")
        if rect is not None and (not isinstance(rect, list) or len(rect) != 4
                                 or not all(isinstance(n, (int, float)) for n in rect)
                                 or not (0 <= rect[0] < rect[2] <= 9900 and 0 <= rect[1] < rect[3] <= 4888)):
            errors.append(f"Invalid source rectangle: {label}: {rect}")


def stored_facilities(nodes):
    records = defaultdict(dict)
    for land, node in nodes.items():
        if node["type"] != "land":
            continue
        sources = [(None, node.get("node_facilities", []), node.get("node_facility_ids", []))]
        sources += [(e["neighbor_id"], e.get("naval_facilities", []), e.get("naval_facility_ids", []))
                    for e in node["neighbors"]]
        for sea, kinds, ids in sources:
            for i, kind in enumerate(kinds):
                if kind not in TYPES:
                    continue
                identity = ids[i] if i < len(ids) else "MISSING_ID"
                row = records[land].setdefault((identity, kind), {
                    "id": identity, "type": kind, "sea_accesses": [], "node_level_record": False,
                })
                if sea is None:
                    row["node_level_record"] = True
                elif sea not in row["sea_accesses"]:
                    row["sea_accesses"].append(sea)
    # Read sea-side records as well, so an asymmetric current claim cannot vanish
    # from the review just because the land-side record omitted it.
    for sea, node in nodes.items():
        if node["type"] != "sea":
            continue
        for edge in node["neighbors"]:
            land = edge["neighbor_id"]
            if nodes[land]["type"] != "land":
                continue
            for i, kind in enumerate(edge.get("naval_facilities", [])):
                if kind not in TYPES:
                    continue
                ids = edge.get("naval_facility_ids", [])
                identity = ids[i] if i < len(ids) else "MISSING_ID"
                row = records[land].setdefault((identity, kind), {
                    "id": identity, "type": kind, "sea_accesses": [], "node_level_record": False,
                })
                if sea not in row["sea_accesses"]:
                    row["sea_accesses"].append(sea)
    return {land: list(rows.values()) for land, rows in records.items()}


def signature(facilities):
    return sorted((f["type"], tuple(sorted(f.get("sea_accesses", [])))) for f in facilities)


def contains_naval_type(value):
    return bool(re.search(r"\b(?:" + "|".join(sorted(TYPES)) + r")\b", json.dumps(value)))


def facility_text(facilities):
    if not facilities:
        return "None"
    items = []
    for f in facilities:
        seas = ", ".join(s.removeprefix("sea_").upper() for s in f.get("sea_accesses", []))
        if not seas:
            seas = "access unassigned"
        items.append(f["type"].replace("_", " ") + " → " + seas)
    return "; ".join(items)


def main():
    nodes = read_baseline_map()["nodes"]
    current = stored_facilities(nodes)
    findings = json.loads((DATA / "all_findings.json").read_text())
    finding_ids = {f["id"] for f in findings}
    proposed_nodes = json.loads((DATA / "identified_missing_nodes.json").read_text())
    known_nodes = set(nodes) | {r["node_id"] for r in proposed_nodes}
    known_nodes.add("land_gbr_shetland_islands")  # documented alias
    by_land = {}
    errors = []
    physical_ids = {}
    source_ledgers = []
    unassigned = []
    for region in REGIONS:
        filename = f"naval_reaudit_{region}.json"
        ledger = json.loads((DATA / filename).read_text())
        source_ledgers.append(filename)
        for facility in ledger.get("unassigned_facilities", []):
            if facility["id"] in physical_ids:
                errors.append(f"Repeated unassigned physical ID: {facility['id']}")
            physical_ids[facility["id"]] = "unassigned"
            if facility["type"] not in TYPES or not facility.get("evidence"):
                errors.append(f"Unassigned facility lacks valid type/evidence: {facility['id']}")
            validate_evidence(facility.get("evidence", []), facility["id"], errors)
            for candidate in facility.get("candidate_land_ids", []):
                if candidate not in known_nodes:
                    errors.append(f"Unknown candidate owner territory: {candidate}")
            for sea in facility.get("sea_accesses", []):
                if sea not in known_nodes or not sea.startswith("sea_"):
                    errors.append(f"Unknown unassigned facility access: {sea}")
            unassigned.append(dict(facility, region=region))
        for entry in ledger["entries"]:
            land = entry["land_id"]
            row = dict(entry, region=region, current_facilities=current.get(land, []))
            if land not in known_nodes:
                errors.append(f"Unknown land ID: {land}")
            if land in by_land:
                errors.append(f"Duplicate regional review: {land}")
                continue
            if row["review_status"] not in {"confirmed", "uncertain"}:
                errors.append(f"Invalid review status: {land}")
            if not row["expected_facilities"] and not row.get("evidence"):
                errors.append(f"Empty facility decision lacks evidence: {land}")
            validate_evidence(row.get("evidence", []), land, errors)
            for fid in row.get("finding_ids", []):
                if fid not in finding_ids:
                    errors.append(f"Unknown finding: {land}: {fid}")
            for sea in row.get("reviewed_sea_ids", []):
                if sea not in known_nodes or not sea.startswith("sea_"):
                    errors.append(f"Unknown reviewed sea: {land}: {sea}")
            for facility in row["expected_facilities"]:
                if facility["type"] not in TYPES:
                    errors.append(f"Unknown facility type: {land}: {facility['type']}")
                identity = facility["id"]
                if identity in physical_ids:
                    errors.append(f"Repeated physical facility ID: {identity}")
                physical_ids[identity] = land
                if not facility.get("sea_accesses") and row["review_status"] == "confirmed":
                    errors.append(f"Confirmed facility has no sea access: {identity}")
                if not facility.get("evidence") and not row.get("evidence"):
                    errors.append(f"Facility lacks source evidence: {identity}")
                validate_evidence(facility.get("evidence", []), identity, errors)
                for sea in facility.get("sea_accesses", []):
                    if sea not in known_nodes or not sea.startswith("sea_"):
                        errors.append(f"Unknown facility access: {identity}: {sea}")
                for evidence in facility.get("evidence", []):
                    if isinstance(evidence, dict) and evidence.get("crop"):
                        if not evidence_path(evidence["crop"]).exists():
                            errors.append(f"Missing source crop: {evidence['crop']}")
            if row["review_status"] == "uncertain" and not row.get("uncertainties"):
                errors.append(f"Uncertain row lacks explanation: {land}")
            row["type_or_access_differs_from_current"] = signature(row["expected_facilities"]) != signature(row["current_facilities"])
            by_land[land] = row

    missing_current = sorted(set(current) - set(by_land))
    errors.extend(f"Stored facility territory not reviewed: {land}" for land in missing_current)
    claim_nodes = set()
    for finding in findings:
        if contains_naval_type(finding.get("proposed")):
            claim_nodes.update(n for n in finding.get("node_ids", []) if n.startswith("land_"))
    # Mixed findings can refer to land zones for topology alone. This is a
    # deliberately conservative coverage flag, never evidence of a facility.
    claim_gaps = sorted(claim_nodes - set(by_land))
    errors.extend(f"Proposed facility territory not reviewed: {land}" for land in claim_gaps)
    checked_shore_findings = []
    checked_inventory_findings = []
    for finding in findings:
        proposed = finding.get("proposed")
        lands = [n for n in finding.get("node_ids", []) if n.startswith("land_")]
        inventories = {}
        if finding["field"] == "naval_facility_inventory" and len(lands) == 1:
            inventories[lands[0]] = proposed
        if isinstance(proposed, dict) and isinstance(proposed.get("physical_instances"), dict):
            inventories.update(proposed["physical_instances"])
        if len(lands) == 1 and isinstance(proposed, dict) and isinstance(proposed.get("physical_facilities"), list):
            # These may be shore-specific subsets; compare their actual records
            # recursively below. A land-only empty list asserts a complete removal.
            if not proposed["physical_facilities"] and not any(n.startswith("sea_") for n in finding.get("node_ids", [])):
                inventories[lands[0]] = []
        if finding["field"] == "naval_facilities" and len(lands) == 1 and proposed == []:
            if not any(n.startswith("sea_") for n in finding.get("node_ids", [])):
                inventories[lands[0]] = []
        if finding["field"] == "naval_facilities" and isinstance(proposed, dict):
            inventories.update({k: v for k, v in proposed.items() if k.startswith("land_") and v == []})
        for land, inventory in inventories.items():
            if land not in by_land or not isinstance(inventory, list):
                errors.append(f"Invalid inventory proposal: {finding['id']} {land}")
                continue
            expected = by_land[land]["expected_facilities"]
            if signature(inventory) != signature(expected) or {f["id"] for f in inventory} != {f["id"] for f in expected}:
                errors.append(f"Complete inventory/roster disagreement: {finding['id']} {land}")
            checked_inventory_findings.append(finding["id"] + ":" + land)
        if isinstance(proposed, dict):
            for facility in proposed.get("verified_facilities", []):
                land = facility["land_id"]
                expected = by_land.get(land, {}).get("expected_facilities", [])
                if not any(f["id"] == facility["id"] and signature([f]) == signature([facility]) for f in expected):
                    errors.append(f"Global facility proposal/roster disagreement: {finding['id']} {facility['id']}")
                checked_inventory_findings.append(finding["id"] + ":" + facility["id"])
            for land in proposed.get("remove_facilities_from", []):
                if land not in by_land or by_land[land]["review_status"] != "confirmed" or by_land[land]["expected_facilities"]:
                    errors.append(f"Global facility removal/roster disagreement: {finding['id']} {land}")
    # Compare explicit physical objects even when nested in new-node, multi-sea,
    # grouped, or partly uncertain findings. Unassigned facilities remain distinct.
    canonical = {f["id"]: (r["land_id"], f) for r in by_land.values() for f in r["expected_facilities"]}
    canonical.update({f["id"]: (None, f) for f in unassigned})
    checked_physical_objects = []

    def inspect_objects(value, finding_id, land_context=None):
        if isinstance(value, list):
            for item in value:
                inspect_objects(item, finding_id, land_context)
        elif isinstance(value, dict):
            owner = value.get("land_id", land_context)
            if value.get("type") in TYPES and value.get("id") and "sea_accesses" in value:
                identity = value["id"]
                if identity not in canonical:
                    errors.append(f"Proposed physical facility absent from roster: {finding_id}: {identity}")
                else:
                    expected_owner, expected = canonical[identity]
                    if signature([value]) != signature([expected]) or (owner and expected_owner and owner != expected_owner):
                        errors.append(f"Nested facility/roster disagreement: {finding_id}: {identity}")
                checked_physical_objects.append(finding_id + ":" + identity)
            for key, child in value.items():
                inspect_objects(child, finding_id, key if key.startswith("land_") else owner)

    for finding in findings:
        lands = [n for n in finding.get("node_ids", []) if n.startswith("land_")]
        inspect_objects(finding.get("proposed"), finding["id"], lands[0] if len(lands) == 1 else None)
    for finding in findings:
        proposed = finding.get("proposed")
        naval_types = proposed.get("naval_facilities") if isinstance(proposed, dict) else proposed if finding["field"] == "naval_facilities" else None
        if not isinstance(naval_types, list):
            continue
        if any(not isinstance(value, str) or value not in TYPES for value in naval_types):
            continue
        lands = [n for n in finding.get("node_ids", []) if n.startswith("land_")]
        seas = [n for n in finding.get("node_ids", []) if n.startswith("sea_")]
        if len(lands) != 1 or len(seas) != 1 or lands[0] not in by_land:
            continue
        row = by_land[lands[0]]
        if row["review_status"] != "confirmed":
            continue
        expected = [f["type"] for f in row["expected_facilities"] if seas[0] in f["sea_accesses"]]
        if Counter(naval_types) != Counter(expected):
            errors.append(f"Finding/roster disagreement: {finding['id']} {lands[0]} {seas[0]}: {naval_types} vs {expected}")
        if isinstance(proposed, dict) and isinstance(proposed.get("naval_facility_ids"), list):
            expected_ids = [f["id"] for f in row["expected_facilities"] if seas[0] in f["sea_accesses"]]
            if Counter(proposed["naval_facility_ids"]) != Counter(expected_ids):
                errors.append(f"Finding/roster identity disagreement: {finding['id']}")
        checked_shore_findings.append(finding["id"])
    entries = sorted(by_land.values(), key=lambda r: (REGIONS.index(r["region"]), r["land_id"]))
    empty_current = [r["land_id"] for r in entries if r["current_facilities"]
                     and not r["expected_facilities"] and r["review_status"] == "confirmed"]
    ambiguous = [r["land_id"] for r in entries if r["review_status"] == "uncertain"]
    summary = {
        "review_date": "2026-10-06", "status": "passed" if not errors else "needs_correction",
        "scope": "Printed naval facilities only: ports, dockyards, shipyards, seaplane and submarine bases. No production edits.",
        "source_ledgers": source_ledgers,
        "territories_reviewed": len(entries), "regional_territory_counts": dict(Counter(r["region"] for r in entries)),
        "current_facility_bearing_territories": len(current),
        "unreviewed_current_facility_territories": missing_current,
        "conservative_proposal_reference_coverage_gaps": claim_gaps,
        "confirmed_no_facility_territories_with_current_claims": empty_current,
        "uncertain_territories": ambiguous,
        "proposed_facility_count": sum(len(r["expected_facilities"]) for r in entries),
        "unassigned_printed_facility_count": len(unassigned),
        "shore_findings_compared_with_roster": checked_shore_findings,
        "inventory_findings_compared_with_roster": checked_inventory_findings,
        "nested_physical_objects_compared_with_roster": checked_physical_objects,
        "proposed_facility_type_counts": dict(Counter(f["type"] for r in entries for f in r["expected_facilities"])),
        "territories_with_type_or_access_changes": sum(r["type_or_access_differs_from_current"] for r in entries),
        "validation_errors": errors,
        "limits": "Facility counts include only the explicitly listed proposals; unresolved symbols/ownership/accesses remain in uncertainties. Confirming a facility does not certify unrelated coast, terrain or rail attributes.",
    }
    dump("naval_facility_reaudit.json", {"summary": summary, "entries": entries, "unassigned_facilities": unassigned})
    dump("naval_facility_reaudit_summary.json", summary)
    lines = ["# Naval facilities — corrected proposed roster", "", "**Rechecked 6 October 2026. Audit proposals only; production map unchanged.**", "",
             "This is the proposed facility roster after reviewing the printed symbols again. It replaces the earlier conditional port-ID naming examples. A coast without a printed naval symbol has no printed facility. A named city, a railway, a convoy endpoint or an existing JSON field is not evidence that a port exists.", "",
             "Each listed facility has a type, a territory, one physical ID and explicit sea accesses. Different symbols receive different IDs. Multiple accesses share an ID only when they belong to the same physical facility. Proposed IDs and source-finding references in the ledger are review aids; this report does not apply a new map schema.", "",
             f"Reviewed **{len(entries)} territory records**, including **{len(current) - len(missing_current)} of {len(current)}** records with current naval-facility claims. **{len(empty_current)}** of those current records have an empty proposed naval inventory (including the retired Hispaniola aggregate). **{len(ambiguous)}** territory reviews retain specific uncertainties.", "",
             "Read [the source-reviewed ledger](data/naval_facility_reaudit.json) for exact IDs, evidence crops, reviewed sea zones and uncertainty details; [validation and counts](data/naval_facility_reaudit_summary.json) distinguish checked records from unresolved cases.", "",
             "## How to read the comparison", "", "“Current” reproduces the existing JSON, including incorrect sea IDs and facilities. “Proposed” lists the source-backed facility types and accesses. A deletion removes the facility claim, not a real coastline. Uncertain rows show only the settled facilities; the notes also need review before applying changes.", ""]
    for region in REGIONS:
        lines += ["## " + region.replace("_", " ").title(), "", "| Territory | Current naval facilities | Proposed naval facilities | Review |", "|---|---|---|---|"]
        no_claim = []
        for row in entries:
            if row["region"] != region:
                continue
            land = row["land_id"]
            name = nodes.get(land, {}).get("name", land.removeprefix("land_").replace("_", " ").title())
            if not row["current_facilities"] and not row["expected_facilities"] and row["review_status"] == "confirmed":
                no_claim.append(name)
                continue
            status = row["review_status"]
            refs = ", ".join(row.get("finding_ids", []))
            if refs:
                status += "; " + refs
            expected_text = facility_text(row["expected_facilities"])
            if row["review_status"] == "uncertain":
                expected_text = (expected_text + "; " if row["expected_facilities"] else "") + "unresolved details below"
            lines.append(f"| {name} (`{land}`) | {facility_text(row['current_facilities'])} | {expected_text} | {status} |")
        if no_claim:
            lines += ["", "Also inspected with **no printed naval facilities**: " + "; ".join(no_claim) + "."]
        lines.append("")
    if unassigned:
        lines += ["## Printed facilities with unresolved territory assignment", ""]
        for f in unassigned:
            candidates = ", ".join(f.get("candidate_land_ids", []))
            lines += [f"- `{f['id']}`: {facility_text([f])}; candidate territories: {candidates}. This is one facility, not one copy in each candidate territory."]
        lines.append("")
    lines += ["## Unresolved source details", ""]
    if not ambiguous:
        lines += ["No territory review is marked uncertain.", ""]
    for row in entries:
        if row["review_status"] != "uncertain":
            continue
        lines += ["### " + row["land_id"], ""]
        for uncertainty in row["uncertainties"]:
            lines += ["- " + (uncertainty if isinstance(uncertainty, str) else json.dumps(uncertainty, ensure_ascii=False))]
        lines.append("")
    if errors or claim_gaps:
        lines += ["## Coverage items requiring attention", ""]
        lines += ["- " + error for error in errors]
        lines += ["- Proposal references not represented in this ledger (some may be non-facility references in grouped findings): " + ", ".join(claim_gaps)] if claim_gaps else []
    lines += ["", "## Rebuild this comparison", "", "Run `consolidate.py`, then `rebuild_naval_reaudit.py` from this directory using the repository Python environment. Both commands update audit artifacts only. The regional ledgers contain the actual source review; this script checks and presents those decisions without deriving geography from the old map.", ""]
    (HERE / "naval_facility_reaudit.md").write_text("\n".join(lines))
    print(json.dumps(summary, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
