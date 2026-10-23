# Annotated rules reader

Open [index.html](index.html) directly in a browser. The reader contains the main
v4.3 rulebook and all 13 local national sheets. All reader text, styles, scripts,
and three image-only setup pages are embedded in the generated HTML. Original
PDFs and Discord messages are links; neither is loaded to display the reader.

Source inclusion is separate from discussion review. The visible coverage banner
states the pilot window; it does not imply that all rules, channels, or later
messages have been reviewed. Current local source editions can postdate that
window. Such edition caveats remain visible beside the affected sources.

Regenerate after updating reviewed annotations:

```sh
python3 tools/build_rules_html.py \
  --sources game_content/rules/html/source_index.json \
  --annotations game_content/rules/html/annotations.json \
  --strict
```

`source_index.json` retains extracted paragraphs, headings, tables and page
references. National-sheet column layouts remain searchable fixed-width text;
three image-only setup pages are explicitly identified and retain their PNG bytes
as base64 data URLs. Regeneration uses those embedded bytes, so a fresh checkout
does not need the optional local PNG files. Their paths remain as provenance;
the repository's image-ignore policy is unchanged. Table transcriptions keep
blank merged cells and link to the original PDF layout. The original documents
remain authoritative for figures and exact layout.

Annotations are a separate JSON document:

```json
{
  "pilot": {
    "date_label": "26 Aug–26 Sep 2025",
    "coverage_note": "Describe exactly what was reviewed and any gaps."
  },
  "annotations": [
    {
      "id": "stable-discussion-id",
      "category": "clarification",
      "title": "Short finding",
      "body": "Source-backed explanation, separate from the original rule.",
      "section_ids": ["rb-4-9"],
      "quote": "Optional exact rule phrase for paragraph placement",
      "block_ids": [],
      "discord_url": "https://discord.com/channels/...",
      "date": "2025-09-01",
      "author": "Source author",
      "authority": "Developer / moderator / community / question",
      "authority_detail": "Optional evidence or limitation on that authority"
    }
  ]
}
```

Categories are `clarification` (blue text), `fix` (green text), `unresolved`
(amber text), and `project` (gray text for campaign choices without a verified
publisher ruling). They have distinct visible labels as well as colors. This
pilot found no qualifying new issues; the 12 existing reference notes are
explicitly marked as outside the pilot window. Their stable RCL IDs are visible
and searchable. Repeated placement beside relevant rules does not create new
issues: the reader reports both placements and unique notes.

`--strict` rejects unmatched section anchors. An annotation
with a matching block ID or rule quote appears immediately after that block;
otherwise it appears at the end of the referenced rule. HTML in source text or
annotation bodies is escaped.

Reader assets are maintained in `tools/rules_reader_template.html`,
`tools/rules_reader.css`, and `tools/rules_reader.js`. Source PDFs, the existing
clarification register, engine profiles, and historical milestone records are
not changed by this generator.
