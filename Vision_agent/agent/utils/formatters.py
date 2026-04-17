from __future__ import annotations

import re
import unicodedata
from typing import Any

_RTL_PATTERN = re.compile(
    "[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF"
    "\u0590-\u05FF\uFB1D-\uFB4F]"
)

_FSI = "\u2068"
_PDI = "\u2069"


def _has_rtl(text: str) -> bool:
    """Return True if the string contains any right-to-left (RTL) characters."""
    return bool(_RTL_PATTERN.search(text))


def sanitize_bidi(text: str, escape_pipe: bool = False) -> str:
    """NFC-normalize and wrap in bidi isolates when RTL characters are present."""
    text = unicodedata.normalize("NFC", text)
    if escape_pipe:
        text = text.replace("|", "\\|")
    if _has_rtl(text):
        return f"{_FSI}{text}{_PDI}"
    return text


def _fmt_table_cell(text: str) -> str:
    """Prepare a single table cell value for markdown, handling bidi and pipes."""
    return sanitize_bidi(text.strip(), escape_pipe=True) if text.strip() else ""


def _section(heading: str, body: str) -> str:
    """Wrap a body string in a markdown `## heading` section."""
    return f"## {heading}\n\n{body}\n\n"


def _format_text_section(text: str) -> str:
    if not text or not text.strip():
        return ""
    return _section("Extracted Text", sanitize_bidi(text))


def _format_form_fields(fields: list[dict[str, Any]]) -> str:
    """Format structured form field data from OCR into a markdown bullet list."""
    if not fields:
        return ""
    lines: list[str] = []
    for f in fields:
        name = sanitize_bidi(f.get("name", ""))
        value = sanitize_bidi(f.get("value", ""))
        conf = f.get("confidence")
        page = f.get("page")
        value_type = f.get("value_type", "")
        norm = f.get("normalized_value")

        parts = [f"- **{name}**: {value}"]
        meta: list[str] = []
        if value_type:
            meta.append(f"type: {value_type}")
        if norm:
            meta.append(f"normalized: {sanitize_bidi(str(norm))}")
        if conf is not None:
            meta.append(f"confidence: {conf}")
        if page is not None:
            meta.append(f"page {page}")
        if meta:
            parts.append(f"({', '.join(meta)})")
        lines.append(" ".join(parts))

    return _section("Form Fields", "\n".join(lines))


def _format_tables(tables: list[dict[str, Any]]) -> str:
    """Format table structures from OCR into GitHub-flavored markdown tables."""
    if not tables:
        return ""
    parts: list[str] = []
    for idx, tbl in enumerate(tables, 1):
        rows: list[list[str]] = tbl.get("rows", [])
        header_count: int = tbl.get("header_row_count", 0)
        page = tbl.get("page")
        if not rows:
            continue

        label = f"### Table {idx}"
        if page is not None:
            label += f" (Page {page})"
        parts.append(label)

        col_count = max(len(r) for r in rows) if rows else 0

        if header_count > 0:
            for h_row in rows[:header_count]:
                cells = [_fmt_table_cell(c) for c in h_row]
                cells += [""] * (col_count - len(cells))
                parts.append("| " + " | ".join(cells) + " |")
            parts.append("| " + " | ".join(["---"] * col_count) + " |")
            body_rows = rows[header_count:]
        else:
            parts.append("| " + " | ".join(["---"] * col_count) + " |")
            body_rows = rows

        for row in body_rows:
            cells = [_fmt_table_cell(c) for c in row]
            cells += [""] * (col_count - len(cells))
            parts.append("| " + " | ".join(cells) + " |")

    return _section("Tables", "\n".join(parts))


def _format_entities(entities: list[dict[str, Any]]) -> str:
    """Format detected entities (names, dates, etc.) into a markdown list."""
    if not entities:
        return ""
    lines: list[str] = []
    for e in entities:
        etype = sanitize_bidi(e.get("type", ""))
        mention = sanitize_bidi(e.get("mention_text", ""))
        conf = e.get("confidence")
        norm = e.get("normalized_value")
        page = e.get("page")

        parts = [f"- **{etype}**: {mention}"]
        meta: list[str] = []
        if norm:
            meta.append(f"normalized: {sanitize_bidi(str(norm))}")
        if conf is not None:
            meta.append(f"confidence: {conf}")
        if page is not None:
            meta.append(f"page {page}")
        if meta:
            parts.append(f"({', '.join(meta)})")
        lines.append(" ".join(parts))

    return _section("Entities", "\n".join(lines))


def _format_processor_metadata(meta: dict[str, Any] | None) -> str:
    """Format high-level processor metadata (type, pages, languages) as markdown."""
    if not meta:
        return ""
    parts: list[str] = []
    if meta.get("type"):
        parts.append(f"- **Processor**: {meta['type']}")
    if meta.get("page_count") is not None:
        parts.append(f"- **Pages**: {meta['page_count']}")
    if meta.get("languages"):
        parts.append(f"- **Languages**: {', '.join(meta['languages'])}")
    if not parts:
        return ""
    return _section("Processor Metadata", "\n".join(parts))


def _format_image_quality(quality: dict[str, Any] | None) -> str:
    """Format page-level image quality scores and defects as markdown."""
    if not quality:
        return ""
    lines: list[str] = []
    avg = quality.get("average_quality_score")
    if avg is not None:
        lines.append(f"- **Average Quality Score**: {avg}")
    for p in quality.get("pages", []):
        page_num = p.get("page")
        score = p.get("quality_score")
        defects = p.get("detected_defects", [])
        defect_strs = [f"{d['type']} ({d['confidence']})" for d in defects]
        defect_text = ", ".join(defect_strs) if defect_strs else "none"
        lines.append(f"- Page {page_num}: score {score}, defects: {defect_text}")
    if not lines:
        return ""
    return _section("Image Quality", "\n".join(lines))


def _format_word_confidence(wc: dict[str, Any] | None) -> str:
    """Format document and per-page word confidence statistics as markdown."""
    if not wc:
        return ""
    lines: list[str] = []
    avg = wc.get("average_confidence")
    if avg is not None:
        lines.append(f"- **Average Document Confidence**: {avg}")
    for p in wc.get("pages", []):
        page_num = p.get("page")
        page_avg = p.get("average_confidence")
        word_count = len(p.get("words", []))
        lines.append(
            f"- Page {page_num}: average confidence {page_avg}, {word_count} words"
        )
    if not lines:
        return ""
    return _section("Word Confidence", "\n".join(lines))


def format_ocr_as_markdown(ocr_result: dict[str, Any]) -> str:
    """Convert the full OCR result dict into structured markdown for the LLM.

    Layout blocks are not stored on the OCR dict (redundant with text/tables).
    """
    sections: list[str] = [
        "# OCR Output\n\n",
        _format_processor_metadata(ocr_result.get("processor_metadata")),
        _format_text_section(ocr_result.get("text", "")),
        _format_form_fields(ocr_result.get("form_fields", [])),
        _format_tables(ocr_result.get("tables", [])),
        _format_entities(ocr_result.get("entities", [])),
        _format_image_quality(ocr_result.get("image_quality")),
        _format_word_confidence(ocr_result.get("word_confidence")),
    ]
    return "".join(s for s in sections if s).rstrip("\n") + "\n"
