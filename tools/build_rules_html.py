#!/usr/bin/env python3
"""Build the offline rules reader from source indexes and reviewed annotations.

Example:
  python3 tools/build_rules_html.py --sources source_index.json national_index.json \
      --annotations game_content/rules/html/annotations.json

Input indexes have sources and sections arrays. Text is always escaped; source
PDFs remain the authority for figures, merged table cells, and original layout.
The output embeds its styles, script, and text: no server or network is needed.
"""
from __future__ import annotations

import argparse
import base64
import mimetypes
import html
import json
import os
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = {
    "clarification": ("Clarification", "i"),
    "fix": ("Correction / fix", "✓"),
    "unresolved": ("Unresolved", "?"),
    "project": ("Project choice", "◇"),
}


def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def path_from(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def file_link(value, output, page=None):
    path = path_from(value)
    relative = Path(os.path.relpath(path, output.parent)).as_posix()
    return quote(relative, safe="/.") + (f"#page={page}" if page else "")


def prose_blocks(text):
    """Conservative fallback for text indexes without structured blocks."""
    out = []
    for part in re.split(r"\n\s*\n", text.replace("\f", "\n\n")):
        lines = part.strip().splitlines()
        if not lines:
            continue
        columns = sum(bool(re.search(r"\S\s{3,}\S", line)) for line in lines)
        layout = columns >= max(2, len(lines) // 2)
        out.append({"type": "layout" if layout else "paragraph", "text": "\n".join(lines) if layout else clean(" ".join(lines))})
    return out


def load_indexes(paths):
    sources, sections = {}, []
    for path in paths:
        data = json.loads(path.read_text())
        entries = data.get("sources", [])
        if isinstance(entries, dict):
            entries = [dict(value, id=key) for key, value in entries.items()]
        for entry in entries:
            source = dict(entry)
            source.setdefault("file_path", source.get("source"))
            source.setdefault("id", re.sub(r"[^a-z0-9]+", "-", Path(source["file_path"]).stem.lower()).strip("-"))
            source.setdefault("title", Path(source["file_path"]).stem)
            source.setdefault("pages", source.get("pdf_pages", 0))
            if source["id"] in sources and sources[source["id"]]["file_path"] != source["file_path"]:
                raise ValueError(f"Conflicting source id {source['id']}")
            sources[source["id"]] = source
            # An extraction manifest is usable while a structured index is being
            # prepared. Its fixed-width blocks retain table column relationships.
            if not data.get("sections") and source.get("page_texts"):
                for page, text_file in enumerate(source["page_texts"], 1):
                    text = path_from(text_file).read_text()
                    sections.append({"id": f"{source['id']}-p{page:03}", "title": f"Page {page}",
                                     "source_id": source["id"], "pdf_page": page,
                                     "blocks": prose_blocks(text), "layout_text": text})
        sections.extend(data.get("sections", []))
    seen = set()
    for section in sections:
        if section["id"] in seen:
            raise ValueError(f"Duplicate section id {section['id']}")
        seen.add(section["id"])
        if section["source_id"] not in sources:
            raise ValueError(f"Unknown source for section {section['id']}")
        section.setdefault("blocks", prose_blocks(section.get("text", "")))
    if not sources or not sections:
        raise ValueError("The source indexes contain no readable rules")
    return sources, sections


def annotation_html(note, instance):
    category = note["category"]
    label, icon = CATEGORIES[category]
    paragraphs = "".join(f"<p>{esc(p)}</p>" for p in str(note.get("body", "")).split("\n\n") if p.strip())
    metadata = [note.get("date"), note.get("author"), note.get("authority")]
    metadata = " · ".join(esc(part) for part in metadata if part)
    authority_detail = f'<p class="authority-detail">{esc(note["authority_detail"])}</p>' if note.get("authority_detail") else ""
    discord_url = note.get("discord_url", "")
    url = discord_url or note.get("reference_url", "")
    link_label = "Discord message" if discord_url else note.get("reference_label", "Reference")
    source = f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(link_label)} <span aria-hidden="true">↗</span></a>' if url else '<span class="missing-source">Source reference pending</span>'
    quotation = f'<blockquote>{esc(note["discussion_quote"])}</blockquote>' if note.get("discussion_quote") else ""
    scope_labels = {"prior_register_outside_pilot": "Existing register · outside pilot dates", "pilot": "Pilot review"}
    scope = note.get("scope_label", scope_labels.get(note.get("scope"), ""))
    scope_html = f'<div class="annotation-scope">{esc(scope)}</div>' if scope else ""
    return f'''<aside class="annotation {category}" id="note-{esc(note['id'])}-{instance}" data-category="{category}" data-note-id="{esc(note['id'])}" aria-label="{label}: {esc(note['id'])}">
      <div class="annotation-kicker"><span class="note-symbol" aria-hidden="true">{icon}</span>{label}<span class="annotation-id">{esc(note.get("rcl_id", note["id"]))}</span></div>{scope_html}
      <h3>{esc(note.get('title', label))}</h3>{paragraphs}{quotation}
      <footer><span>{metadata}</span>{source}</footer>{authority_detail}</aside>'''


def block_html(block, source, output):
    kind = block.get("type", "paragraph")
    anchor = f' id="{esc(block["id"])}"' if block.get("id") else ""
    text = block.get("text", "")
    if kind == "table":
        rows = block.get("rows", [])
        rendered = []
        for i, row in enumerate(rows):
            tag = "th" if i == 0 and block.get("header", True) else "td"
            scope = ' scope="col"' if tag == "th" else ""
            cells = "".join(f'<{tag}{scope}>{esc(cell)}</{tag}>' for cell in row)
            rendered.append(f"<tr>{cells}</tr>")
        caption = f'<caption>{esc(block["caption"])}</caption>' if block.get("caption") else ""
        return f'<div class="table-wrap"{anchor}><table>{caption}<tbody>{"".join(rendered)}</tbody></table><div class="table-source">Table transcription · <a href="{file_link(source["file_path"], output, block.get("pdf_page"))}">Check original layout ↗</a></div></div>'
    if kind in ("heading", "subheading"):
        return f'<h3 class="rule-heading"{anchor}>{esc(text)}</h3>'
    if kind in ("layout", "pre", "source_layout"):
        return f'<div class="layout-block"{anchor}><span class="layout-label">Source layout</span><pre>{esc(text)}</pre></div>'
    if kind == "list":
        items = block.get("items", [text])
        tag = "ol" if block.get("ordered") else "ul"
        return f'<{tag} class="rule-list"{anchor}>' + "".join(f"<li>{esc(item)}</li>" for item in items) + f'</{tag}>'
    if kind == "image":
        data_url = block.get("data_url")
        if data_url:
            header, encoded = data_url.split(",", 1)
            image_type = re.fullmatch(r"data:(image/[a-zA-Z0-9.+-]+);base64", header)
            if not image_type:
                raise ValueError(f"Invalid embedded image type for {block.get('id', 'source image')}")
            mime = image_type[1]
            image_bytes = base64.b64decode(encoded, validate=True)
        else:
            value = block.get("file_path", block.get("path"))
            if not value:
                return ""
            path = path_from(value)
            mime = mimetypes.guess_type(path.name)[0] or "image/png"
            image_bytes = path.read_bytes()
        encoded = base64.b64encode(image_bytes).decode("ascii")
        dimensions = ""
        if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            width = int.from_bytes(image_bytes[16:20], "big")
            height = int.from_bytes(image_bytes[20:24], "big")
            dimensions = f' width="{width}" height="{height}"'
        caption = block.get("caption", block.get("text", ""))
        return f'<figure{anchor}><img loading="lazy"{dimensions} src="data:{mime};base64,{encoded}" alt="{esc(block.get("alt", caption or "Source rule figure"))}"><figcaption>{esc(caption)}</figcaption></figure>'
    return f'<p class="rule-paragraph"{anchor}>{esc(text)}</p>'


def render(sources, sections, annotation_data, output):
    pilot = annotation_data.get("pilot", {})
    notes = annotation_data.get("annotations", [])
    known_sections = {s["id"] for s in sections}
    by_section = defaultdict(list)
    unplaced = []
    for i, note in enumerate(notes, 1):
        note.setdefault("id", f"discussion-{i:03}")
        if note.get("category") not in CATEGORIES:
            raise ValueError(f"Unknown annotation category: {note.get('category')}")
        targets = note.get("section_ids", [note["section_id"]] if note.get("section_id") else [])
        if not targets and note.get("anchor", {}).get("section_id"):
            targets = [note["anchor"]["section_id"]]
        valid = [target for target in targets if target in known_sections]
        for target in valid:
            by_section[target].append(note)
        if not valid or any(target not in known_sections for target in targets):
            unplaced.append(note)
    grouped = defaultdict(list)
    for section in sections:
        grouped[section["source_id"]].append(section)
    toc, articles, source_options = [], [], []
    counts = {key: sum(n["category"] == key for n in notes) for key in CATEGORIES}
    for source_id, source in sources.items():
        source_options.append(f'<option value="{esc(source_id)}">{esc(source["title"])}</option>')
        links = []
        for section in grouped[source_id]:
            number = section.get("number") or ""
            title = section.get("title", "Untitled section")
            label = f"{number} {title}".strip()
            links.append(f'<a href="#{esc(section["id"])}" data-source="{esc(source_id)}"><span>{esc(number)}</span>{esc(title)}' + (f'<b aria-label="{len(by_section[section["id"]])} annotations">{len(by_section[section["id"]])}</b>' if by_section[section["id"]] else "") + '</a>')
            remaining = list(by_section[section["id"]])
            body = []
            if section == grouped[source_id][0] and source.get("historical_scope_note"):
                body.append(f'<p class="edition-caveat">Edition note: {esc(source["historical_scope_note"])}</p>')
            for block in section["blocks"]:
                body.append(block_html(block, source, output))
                matched = []
                for note in remaining:
                    block_ids = note.get("block_ids", [])
                    quotation = note.get("quote", note.get("anchor", {}).get("quote", ""))
                    if (block.get("id") and block["id"] in block_ids) or (quotation and clean(quotation).casefold() in clean(block.get("text", "")).casefold()):
                        matched.append(note)
                        body.append(annotation_html(note, esc(section["id"])))
                remaining = [n for n in remaining if n not in matched]
            if remaining:
                body.append('<div class="related-notes"><span class="related-label">Discussion attached to this rule</span>')
                body.extend(annotation_html(note, esc(section["id"])) for note in remaining)
                body.append('</div>')
            layout = section.get("layout_text", section.get("raw_layout", ""))
            if isinstance(layout, dict):
                layout = "\n\n".join(f"Page {page}\n{text}" for page, text in layout.items())
            if layout:
                body.append(f'<details class="original-layout"><summary>Text in original page layout</summary><pre>{esc(layout)}</pre></details>')
            page = section.get("pdf_page")
            end_page = section.get("pdf_page_end", page)
            page_label = f"PDF p. {page}" + (f"–{end_page}" if end_page and end_page != page else "") if page else "Original PDF"
            source_link = file_link(source["file_path"], output, page)
            articles.append(f'''<article class="rule-section" id="{esc(section['id'])}" data-source="{esc(source_id)}" data-note-count="{len(by_section[section['id']])}">
              <header class="section-header"><div class="section-meta">{esc(source['title'])} <span>·</span> <a href="{source_link}">{page_label} ↗</a></div>
              <h2><span class="rule-number">{esc(number)}</span>{esc(title)}<a class="permalink" href="#{esc(section['id'])}" aria-label="Link to {esc(label)}">#</a></h2></header>
              <div class="rule-body">{''.join(body)}</div></article>''')
        toc.append(f'<details class="toc-document"{" open" if source_id == next(iter(sources)) else ""}><summary>{esc(source["title"])}<small>{len(links)} sections</small></summary><nav aria-label="{esc(source["title"])}">{"".join(links)}</nav></details>')
    if unplaced:
        articles.append('<article class="rule-section unplaced" id="unplaced-discussions" data-source="" data-note-count="' + str(len(unplaced)) + '"><header class="section-header"><h2>Discussions awaiting a rule anchor</h2><p>These reviewed messages are retained here until their source section is identified.</p></header>' + ''.join(annotation_html(n, 'unplaced') for n in unplaced) + '</article>')
    coverage = pilot.get("coverage_note", "Discord review covers the pilot window only. The full source text below does not imply that every rule or later discussion has been reviewed.")
    window = pilot.get("date_label", "26 Aug–26 Sep 2025")
    sources_summary = "".join(f'<li><div><a href="{file_link(s["file_path"], output)}">{esc(s["title"])}</a>' + (f'<small class="source-caveat">{esc(s["historical_scope_note"])}</small>' if s.get("historical_scope_note") else "") + f'<span>{esc(s.get("version", ""))} · {esc(s.get("pages", ""))} PDF pages</span></div></li>' for s in sources.values())
    context = {
        "CSS": (ROOT / "tools/rules_reader.css").read_text(), "JS": (ROOT / "tools/rules_reader.js").read_text(),
        "TOC": "".join(toc), "ARTICLES": "".join(articles), "OPTIONS": "".join(source_options),
        "COVERAGE": esc(coverage), "WINDOW": esc(window), "SOURCE_COUNT": str(len(sources)),
        "SECTION_COUNT": str(len(sections)), "NOTE_COUNT": str(len(notes)), "SOURCES": sources_summary,
        "CLARIFICATIONS": str(counts["clarification"]), "FIXES": str(counts["fix"]), "UNRESOLVED": str(counts["unresolved"]),
        "PROJECT_LEGEND": '<span class="legend-item project"><b>◇</b>Project choice <small>User-adopted interpretation</small></span>' if counts["project"] else "",
        "PROJECT_FILTER": f'<button class="category-filter project" data-category="project" aria-pressed="true">Project choices <span>{counts["project"]}</span></button>' if counts["project"] else "",
        "PILOT_METRICS": f'<p class="pilot-metrics"><strong>{esc(pilot["reviewed_messages"])}</strong> messages reviewed <span>·</span> <strong>{esc(pilot.get("new_findings", 0))}</strong> new rule issues in this pilot</p>' if "reviewed_messages" in pilot else "",
        "BUILD_DATE": date.today().isoformat(), "UNPLACED": str(len(unplaced)),
    }
    template = (ROOT / "tools/rules_reader_template.html").read_text()
    for key, value in context.items():
        template = template.replace("{{" + key + "}}", value)
    return template, unplaced


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, nargs="+", required=True)
    parser.add_argument("--annotations", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "game_content/rules/html/index.html")
    parser.add_argument("--strict", action="store_true", help="Fail if any annotation cannot be placed")
    args = parser.parse_args()
    sources, sections = load_indexes(args.sources)
    annotation_file = args.annotations or ROOT / "game_content/rules/html/annotations.json"
    annotations = json.loads(annotation_file.read_text()) if annotation_file.exists() else {"annotations": []}
    if args.annotations and not annotation_file.exists():
        raise SystemExit(f"Annotation file does not exist: {annotation_file}")
    output = args.output.resolve()
    text, unplaced = render(sources, sections, annotations, output)
    if unplaced and args.strict:
        raise SystemExit("Unmatched annotations: " + ", ".join(n["id"] for n in unplaced))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text)
    print(f"Built {output}: {len(sources)} sources, {len(sections)} sections, {len(annotations.get('annotations', []))} annotations, {len(unplaced)} awaiting anchors")


if __name__ == "__main__":
    main()
