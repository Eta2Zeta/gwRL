#!/usr/bin/env python3
"""Assemble authored regional findings into review documents; never patch the map."""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = HERE / "data"
SOURCES = ["global", "americas_atlantic", "europe_africa_middle_east", "asia_pacific"]
REGIONS = {
    "global": "generation_and_integrity.md",
    "americas_atlantic": "regions/americas_atlantic.md",
    "europe_africa_middle_east": "regions/europe_africa_middle_east.md",
    "asia_pacific": "regions/asia_pacific.md",
}


def dump(name, data):
    (DATA / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def pretty(value):
    if isinstance(value, str):
        return value
    return "```json\n" + json.dumps(value, indent=2, ensure_ascii=False) + "\n```"


def main():
    nodes = json.loads((ROOT / "game_content/maps/gw36_manual_map.json").read_text())["nodes"]
    findings = []
    ids = set()
    by_node = defaultdict(list)
    for source in SOURCES:
        entries = json.loads((DATA / f"{source}_findings.json").read_text())
        for entry in entries:
            assert entry["id"] not in ids, entry["id"]
            ids.add(entry["id"])
            assert entry["category"] in {"add", "change", "delete", "uncertain"}, entry
            assert entry.get("evidence"), entry["id"]
            entry = dict(entry, report=REGIONS[source], region=source)
            findings.append(entry)
            for nid in entry.get("node_ids", []):
                by_node[nid].append(entry["id"])
    dump("all_findings.json", findings)
    # Roster additions require an explicit node-addition finding. References in a
    # proposed coast, convoy or Home Country record alone do not create a node.
    missing_nodes = defaultdict(list)
    aliases = {"land_gbr_shetland_islands": "land_shetland_islands"}
    for row in findings:
        if row["category"] != "add" or row["field"] not in {"node", "nodes"}:
            continue
        for nid in row.get("node_ids", []):
            if nid not in nodes:
                missing_nodes[aliases.get(nid, nid)].append({"finding_id": row["id"], "suggested_id": nid})
    missing_roster = [{"node_id": nid, "type": "sea" if nid.startswith("sea_") else "land",
                       "proposal_references": refs,
                       "scope": "Identified missing printed identity only; consult findings for attributes and contacts."}
                      for nid, refs in sorted(missing_nodes.items())]
    dump("identified_missing_nodes.json", missing_roster)
    sea_ids = {nid for nid, node in nodes.items() if node["type"] == "sea"} | {nid for nid in missing_nodes if nid.startswith("sea_")}
    sea_roster = [{"node_id": nid, "printed_code": nid.removeprefix("sea_").upper(),
                   "present_in_current_map": nid in nodes,
                   "addition_findings": missing_nodes.get(nid, [])}
                  for nid in sorted(sea_ids, key=lambda value: (value[4], int(value[5:])))]
    dump("proposed_sea_roster.json", sea_roster)
    with (DATA / "findings.csv").open("w", newline="") as stream:
        fields = ["id", "category", "region", "severity", "subject", "node_ids", "field", "current", "proposed", "confidence", "evidence", "notes"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in findings:
            writer.writerow({k: json.dumps(row.get(k), ensure_ascii=False) if isinstance(row.get(k), (dict, list)) else row.get(k) for k in fields})
    for category, filename in [("add", "additions.md"), ("change", "changes.md"), ("delete", "deletions.md"), ("uncertain", "uncertain.md")]:
        group = [row for row in findings if row["category"] == category]
        lines = [f"# {filename[:-3].capitalize()} — complete finding register", "",
                 f"{len(group)} finding records. Group findings may contain multiple fields or nodes; these are not edit counts.", "",
                 "Proposals only. Apply neither uncertain values nor incomplete new-node records automatically. "
                 "Each confidence rating applies only to the described fields. Regional reports explain dependencies and unresolved source coverage.", "",
                 "See [overview](README.md), [mechanism proposals](mechanisms_and_schema.md), and [machine-readable register](data/all_findings.json).", "",
                 "**Naval facilities were rechecked on 6 October 2026.** Start with the "
                 "[corrected current-to-proposed facility roster](naval_facility_reaudit.md) "
                 "for ports, dockyards, shipyards and naval bases. Earlier conditional port-ID "
                 "renaming examples must not be applied as a list of real facilities.", ""]
        if category == "uncertain":
            lines.extend(["This register also needs to be read with [per-node review coverage](data/review_coverage.json) "
                          "and [per-edge coverage](data/edge_review_coverage.json). Those ledgers explicitly retain "
                          "unverified fields even where no single ambiguous feature has a separate finding ID.", ""])
            naval_uncertainties = []
            for source in SOURCES[1:]:
                naval_path = DATA / f"naval_reaudit_{source}.json"
                if naval_path.exists():
                    naval_uncertainties.extend(row for row in json.loads(naval_path.read_text())["entries"]
                                               if row["review_status"] == "uncertain")
            if naval_uncertainties:
                lines.extend(["## Naval-facility source conflicts and ownership ambiguities", "",
                              "The 6 October naval recheck retains these territory-level uncertainties. "
                              "They supplement the finding register; the two Philippine rows concern "
                              "the same single physical port, already discussed in WG-031/AP-095. "
                              "See the [corrected facility roster](naval_facility_reaudit.md) for the proposed values.", ""])
                for row in naval_uncertainties:
                    name = nodes.get(row["land_id"], {}).get("name", row["land_id"])
                    lines.extend([f"### {name}", "", pretty(row["uncertainties"]), ""])
        for row in group:
            lines.extend([f"## {row['id']} — {row['subject']}", "",
                          f"**Field:** `{row['field']}` · **Confidence:** {row['confidence']} · **Severity:** {row['severity']}", "",
                          f"**Regional context:** [{row['region']}]({row['report']})", "",
                          "**Nodes:** " + (", ".join(f"`{nid}`" for nid in row.get("node_ids", [])) or "Global authoring/schema"), "",
                          "**Current:**", "", pretty(row.get("current")), "", "**Proposed:**", "", pretty(row.get("proposed")), "",
                          "**Evidence:**", "", *["- " + (ev if isinstance(ev, str) else json.dumps(ev, ensure_ascii=False)) for ev in row["evidence"]], ""])
            if row.get("notes"):
                lines.extend(["**Scope / dependency:** " + row["notes"], ""])
        (HERE / filename).write_text("\n".join(lines))

    reviews = defaultdict(list)
    for source in SOURCES[1:]:
        entries = json.loads((DATA / f"{source}_review.json").read_text())
        local_ids = set()
        for row in entries:
            assert row["node_id"] in nodes, (source, row["node_id"])
            assert row["node_id"] not in local_ids, (source, row["node_id"])
            local_ids.add(row["node_id"])
            reviews[row["node_id"]].append(dict(row, region=source))
    coverage = []
    for nid, node in nodes.items():
        coverage.append({"node_id": nid, "name": node["name"], "type": node["type"],
                         "structural_inventory": "complete", "regional_source_reviews": reviews[nid],
                         "finding_ids": by_node[nid],
                         "full_field_certification": False,
                         "coverage_note": "Read the exact field scope and uncertainties in each regional review. No finding is not a pass."})
    dump("review_coverage.json", coverage)
    with (DATA / "review_coverage.csv").open("w", newline="") as stream:
        fields = ["node_id", "name", "type", "structural_inventory", "regional_source_reviews", "finding_ids", "full_field_certification", "coverage_note"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in coverage:
            writer.writerow({k: json.dumps(row[k], ensure_ascii=False) if isinstance(row[k], (dict, list)) else row[k] for k in fields})
    # A physical contact and its directional attributes have separate evidence.
    # Regional pair reviews must come from source inspection, not graph symmetry.
    pair_reviews = defaultdict(list)
    pair_review_files = []
    for source in SOURCES[1:]:
        path = DATA / f"{source}_edge_review.json"
        if not path.exists():
            continue
        pair_review_files.append(path.name)
        local_pairs = set()
        for row in json.loads(path.read_text()):
            src, dst = row["source_id"], row["target_id"]
            assert src in nodes and dst in nodes, (source, src, dst)
            assert any(e["neighbor_id"] == dst for e in nodes[src]["neighbors"]), (source, src, dst)
            key = tuple(sorted((src, dst)))
            assert key not in local_pairs, (source, key)
            local_pairs.add(key)
            assert row["relation_status"] in {"confirmed", "proposed_delete", "uncertain"}, row
            assert row.get("evidence"), (source, key)
            assert not set(row.get("finding_ids", [])) - ids, (source, key, row.get("finding_ids"))
            pair_reviews[key].append(dict(row, region=source))
    physical_coverage = []
    stored_pairs = sorted({tuple(sorted((src, edge["neighbor_id"])))
                           for src, node in nodes.items() for edge in node["neighbors"]})
    for src, dst in stored_pairs:
        regional = pair_reviews[(src, dst)]
        statuses = {row["relation_status"] for row in regional}
        contradiction = {"confirmed", "proposed_delete"} <= statuses
        if not regional:
            status = "not_source_reviewed"
        elif contradiction:
            status = "conflicting_reviews"
        elif "uncertain" in statuses:
            status = "uncertain"
        else:
            status = next(iter(statuses))
        physical_coverage.append({"source_id": src, "target_id": dst,
                                  "relation_status": status,
                                  "regional_source_reviews": regional,
                                  "conflicting_conclusions": contradiction,
                                  "scope": "Physical relation only; directional attributes retain each review's exact field scope."})
    dump("physical_connection_review.json", physical_coverage)
    removed_pairs = [row for row in physical_coverage if row["relation_status"] == "proposed_delete"]
    with (HERE / "deletions.md").open("a") as stream:
        stream.write("\n\n## Complete stored-connection deletion index\n\n")
        stream.write(f"The source pair review proposes removing {len(removed_pairs)} stored physical relations. "
                     "Some are already grouped in the findings above or in coast-replacement changes. "
                     "This index exposes each individual pair; it does not add independent finding counts. "
                     "Both stored directions and their attached attributes would be removed.\n\n")
        for row in removed_pairs:
            stream.write(f"- `{row['source_id']}` ↔ `{row['target_id']}`. ")
            notes = [r.get("notes", "See the regional source review.") for r in row["regional_source_reviews"]
                     if r["relation_status"] == "proposed_delete"]
            stream.write(" ".join(dict.fromkeys(notes)) + "\n")
    unsettled = [row for row in physical_coverage if row["relation_status"] in
                 {"uncertain", "conflicting_reviews", "not_source_reviewed"}]
    with (HERE / "uncertain.md").open("a") as stream:
        stream.write("\n\n## Stored physical connections with unresolved review status\n\n")
        stream.write("These are pair-level review outcomes, supplementary to the finding register above. "
                     "They are not extra finding IDs. Directional attributes may have their own "
                     "uncertainties even when the physical relation is confirmed.\n\n")
        if not unsettled:
            stream.write("Every stored pair has a settled physical-relation proposal.\n")
        for row in unsettled:
            stream.write(f"- `{row['source_id']}` ↔ `{row['target_id']}`: **{row['relation_status']}**. ")
            notes = [r.get("notes", "See the regional source review.") for r in row["regional_source_reviews"]]
            stream.write(" ".join(dict.fromkeys(notes)) if notes else "No source review has been recorded yet.")
            stream.write("\n")
    pair_status = {(row["source_id"], row["target_id"]): row["relation_status"] for row in physical_coverage}
    # Incident finding references remain navigation aids. They never imply that a
    # group finding adjudicates an individual edge or its terrain/rail attributes.
    edge_coverage = []
    for src, node in nodes.items():
        for edge in node["neighbors"]:
            dst = edge["neighbor_id"]
            both = sorted(set(by_node[src]) & set(by_node[dst]))
            edge_coverage.append({"source_id": src, "target_id": dst,
                                  "structural_inventory": "complete",
                                  "physical_relation_status": pair_status[tuple(sorted((src, dst)))],
                                  "regional_physical_reviews": pair_reviews[tuple(sorted((src, dst)))],
                                  "findings_referencing_both_endpoints": both,
                                  "source_validation": "Consult exact checked fields, uncertain fields and finding direction. Physical contact confirmation does not certify every stored attribute.",
                                  "full_directional_certification": False})
    dump("edge_review_coverage.json", edge_coverage)
    unknown_references = sorted({nid for row in findings for nid in row.get("node_ids", []) if nid not in nodes})
    summary = {"finding_count": len(findings), "category_counts": dict(Counter(row["category"] for row in findings)),
               "regional_counts": dict(Counter(row["region"] for row in findings)),
               "stored_node_count": len(nodes), "stored_nodes_with_regional_review": sum(bool(reviews[nid]) for nid in nodes),
               "stored_nodes_without_regional_review": [nid for nid in nodes if not reviews[nid]],
               "stored_directed_edges_in_coverage": len(edge_coverage),
               "identified_missing_node_counts": dict(Counter(row["type"] for row in missing_roster)),
               "proposed_sea_roster_count": len(sea_roster),
               "physical_pair_review_files": pair_review_files,
               "physical_pair_status_counts": dict(Counter(row["relation_status"] for row in physical_coverage)),
               "physical_pairs_without_source_review": [[row["source_id"], row["target_id"]] for row in physical_coverage if row["relation_status"] == "not_source_reviewed"],
               "physical_pairs_with_conflicting_reviews": [[row["source_id"], row["target_id"]] for row in physical_coverage if row["conflicting_conclusions"]],
               "proposed_or_unresolved_ids_not_in_current_map": unknown_references,
               "non_executable_proposal_register": True,
               "count_notes": "Finding records overlap and group edits. Unknown-reference list includes proposed IDs/aliases; it is not a certified count of missing printed tiles."}
    dump("audit_summary.json", summary)
    verbose = {"proposed_or_unresolved_ids_not_in_current_map", "physical_pairs_without_source_review",
               "physical_pairs_with_conflicting_reviews"}
    print(json.dumps({k: v for k, v in summary.items() if k not in verbose}, indent=2))


if __name__ == "__main__":
    main()
