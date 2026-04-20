from __future__ import annotations

from google.cloud import documentai_v1 as documentai


def layout_to_text(layout, full_text: str) -> str:
    if not layout or not layout.text_anchor or not layout.text_anchor.text_segments:
        return ""
    return "".join(
        full_text[int(seg.start_index): int(seg.end_index)]
        for seg in layout.text_anchor.text_segments
    )


def extract_languages(document: documentai.Document) -> list[str]:
    languages: set[str] = set()
    for page in document.pages:
        for lang in page.detected_languages:
            if lang.language_code:
                languages.add(lang.language_code)
    return sorted(languages)


def extract_entities(document: documentai.Document) -> list[dict]:
    entities = []
    for entity in document.entities:
        page_index = 0
        if entity.page_anchor and entity.page_anchor.page_refs:
            page_ref = entity.page_anchor.page_refs[0]
            page_index = int(page_ref.page) if page_ref.page else 0

        entities.append(
            {
                "type": entity.type_,
                "mention_text": entity.mention_text,
                "confidence": round(entity.confidence, 4),
                "normalized_value": (
                    entity.normalized_value.text
                    if entity.normalized_value
                    else None
                ),
                "page": page_index + 1,
            }
        )
    return entities


def extract_form_fields(document: documentai.Document) -> list[dict]:
    fields = []
    for i, page in enumerate(document.pages):
        for field in page.form_fields:
            name = layout_to_text(field.field_name, document.text)
            value = layout_to_text(field.field_value, document.text)

            fields.append(
                {
                    "name": name.strip(),
                    "value": value.strip(),
                    "confidence": (
                        round(field.field_value.confidence, 4)
                        if field.field_value
                        else 0.0
                    ),
                    "page": i + 1,
                    "value_type": field.value_type,
                    "normalized_value": None,
                }
            )
    return fields


def process_table_row(row, document_text):
    return [layout_to_text(cell.layout, document_text).strip() for cell in row.cells]


def extract_tables(document: documentai.Document) -> list[dict]:
    tables = []
    for i, page in enumerate(document.pages):
        for table in page.tables:
            header_rows = [
                process_table_row(row, document.text)
                for row in table.header_rows
            ]
            body_rows = [
                process_table_row(row, document.text)
                for row in table.body_rows
            ]

            rows = header_rows + body_rows

            tables.append(
                {
                    "rows": rows,
                    "header_row_count": len(header_rows),
                    "page": i + 1,
                }
            )
    return tables


def extract_word_confidence(document: documentai.Document) -> dict:
    pages_data: list[dict] = []
    all_confidences: list[float] = []

    for i, page in enumerate(document.pages):
        words: list[dict] = []
        page_confidences: list[float] = []

        for token in page.tokens:
            word_text = layout_to_text(token.layout, document.text).strip()
            if not word_text:
                continue

            confidence = round(token.layout.confidence, 4)
            words.append(
                {
                    "text": word_text,
                    "confidence": confidence,
                }
            )
            page_confidences.append(confidence)
            all_confidences.append(confidence)

        average_page_confidence = (
            round(sum(page_confidences) / len(page_confidences), 4)
            if page_confidences
            else None
        )

        pages_data.append(
            {
                "page": i + 1,
                "average_confidence": average_page_confidence,
                "words": words,
            }
        )

    average_document_confidence = (
        round(sum(all_confidences) / len(all_confidences), 4)
        if all_confidences
        else None
    )

    return {
        "average_confidence": average_document_confidence,
        "pages": pages_data,
    }


def extract_image_quality(document: documentai.Document) -> dict | None:
    pages_data: list[dict] = []
    quality_scores: list[float] = []

    for i, page in enumerate(document.pages):
        scores = page.image_quality_scores
        if not scores:
            continue

        quality_score = round(scores.quality_score, 4)
        quality_scores.append(quality_score)
        pages_data.append(
            {
                "page": i + 1,
                "quality_score": quality_score,
                "detected_defects": [
                    {
                        "type": defect.type_,
                        "confidence": round(defect.confidence, 4),
                    }
                    for defect in scores.detected_defects
                ],
            }
        )

    if not pages_data:
        return None

    average_quality_score = round(sum(quality_scores) / len(quality_scores), 4)
    return {
        "average_quality_score": average_quality_score,
        "pages": pages_data,
    }
