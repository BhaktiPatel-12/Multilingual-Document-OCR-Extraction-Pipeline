"""
Astra-OCR Data Entry Service
============================

Extracts structured fields from ingested OCR blocks.

This is intentionally conservative.

It supports:

- Names
- Father's / Mother's name
- Roll number
- Registration number
- Date of birth
- School / institution
- Email
- Phone
- PAN
- GSTIN
- URLs
- Dates
- Amounts
- Percentages
- Generic key/value OCR lines
"""

import re
from typing import Any, Dict, List, Optional

from .database import database_connection


# ==============================================================
# FIELD PATTERNS
# ==============================================================

FIELD_PATTERNS = [

    (
        "Name",
        "Person",
        re.compile(
            r"(?:student\s+name|candidate\s+name|name\s+of\s+(?:the\s+)?student)"
            r"\s*[:\-]?\s*([A-Za-z][A-Za-z .'-]{2,80})",
            re.I,
        ),
    ),

    (
        "Father's Name",
        "Person",
        re.compile(
            r"(?:father'?s?\s*(?:\/\s*guardian'?s?)?\s*name)"
            r"\s*[:\-]?\s*([A-Za-z][A-Za-z .'-]{2,80})",
            re.I,
        ),
    ),

    (
        "Mother's Name",
        "Person",
        re.compile(
            r"(?:mother'?s?\s*name)"
            r"\s*[:\-]?\s*([A-Za-z][A-Za-z .'-]{2,80})",
            re.I,
        ),
    ),

    (
        "Roll Number",
        "Identifier",
        re.compile(
            r"(?:roll\s*(?:no|number)\.?)"
            r"\s*[:\-]?\s*([A-Za-z0-9\/-]+)",
            re.I,
        ),
    ),

    (
        "Registration Number",
        "Identifier",
        re.compile(
            r"(?:regn\.?\s*no\.?|registration\s*(?:no|number))"
            r"\s*[:\-]?\s*([A-Za-z0-9\/-]+)",
            re.I,
        ),
    ),

    (
        "Date of Birth",
        "Date",
        re.compile(
            r"(?:date\s+of\s+birth|dob)"
            r"\s*[:\-]?\s*(\d{1,2}[\/.-]\d{1,2}[\/.-]\d{2,4})",
            re.I,
        ),
    ),

    (
        "School",
        "Organization",
        re.compile(
            r"(?:school|institution)"
            r"\s*(?:name)?"
            r"\s*[:\-]?\s*([A-Za-z0-9 .,'&()\/-]{4,120})",
            re.I,
        ),
    ),

    (
        "Email",
        "Contact",
        re.compile(
            r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b",
            re.I,
        ),
    ),

    (
        "Phone",
        "Contact",
        re.compile(
            r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b"
        ),
    ),

    (
        "PAN",
        "Identifier",
        re.compile(
            r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
            re.I,
        ),
    ),

    (
        "GSTIN",
        "Identifier",
        re.compile(
            r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b",
            re.I,
        ),
    ),

    (
        "Percentage",
        "Numeric",
        re.compile(
            r"\b\d+(?:\.\d+)?\s*%"
        ),
    ),

    (
        "Amount",
        "Amount",
        re.compile(
            r"(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d{1,2})?",
            re.I,
        ),
    ),

    (
        "Date",
        "Date",
        re.compile(
            r"\b\d{1,2}[\/.-]\d{1,2}[\/.-]\d{2,4}\b"
        ),
    ),
]


# ==============================================================
# HELPERS
# ==============================================================

def normalize_value(
    value: str
) -> str:

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip(
        " \t\r\n:|-"
    )


def confidence_status(
    confidence: float
) -> str:

    if confidence >= 85:
        return "accepted"

    if confidence >= 70:
        return "review"

    return "low_confidence"


def extract_from_text(
    text: str,
) -> List[Dict[str, Any]]:

    fields = []

    for field_name, field_type, pattern in FIELD_PATTERNS:

        match = pattern.search(
            text
        )

        if not match:
            continue

        value = (
            match.group(1)
            if match.lastindex
            else match.group(0)
        )

        value = normalize_value(
            value
        )

        if not value:
            continue

        fields.append(
            {
                "field_name": field_name,
                "field_type": field_type,
                "field_value": value,
                "extraction_method": "pattern",
            }
        )

    # ----------------------------------------------------------
    # Generic key:value extraction
    # ----------------------------------------------------------

    if ":" in text:

        left, right = text.split(
            ":",
            1,
        )

        key = normalize_value(
            left
        )

        value = normalize_value(
            right
        )

        if (
            key
            and value
            and len(key) <= 80
            and len(value) <= 300
        ):

            fields.append(
                {
                    "field_name": key,
                    "field_type": "Text",
                    "field_value": value,
                    "extraction_method": "key_value",
                }
            )

    return fields


# ==============================================================
# MAIN DATA ENTRY
# ==============================================================

def run_data_entry(
    *,
    document_id: int,
    job_id: str,
    filename: str,
) -> Dict[str, Any]:

    with database_connection() as connection:

        cursor = connection.cursor(
            dictionary=True
        )

        try:

            # --------------------------------------------------
            # Get OCR blocks
            # --------------------------------------------------

            cursor.execute(
                """
                SELECT
                    id,
                    document_id,
                    page_number,
                    block_number,
                    text,
                    language,
                    region_type,
                    confidence,
                    source
                FROM ocr_blocks
                WHERE document_id = %s
                ORDER BY page_number, block_number
                """,
                (document_id,),
            )

            blocks = cursor.fetchall()

            # --------------------------------------------------
            # New run
            # --------------------------------------------------

            cursor.execute(
                """
                INSERT INTO data_entry_runs
                (
                    document_id,
                    job_id,
                    status,
                    total_blocks,
                    selected_blocks
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    document_id,
                    job_id,
                    "processing",
                    len(blocks),
                    len(blocks),
                ),
            )

            run_id = cursor.lastrowid

            # --------------------------------------------------
            # Clear previous extracted fields for this document
            # --------------------------------------------------

            cursor.execute(
                """
                DELETE FROM extracted_fields
                WHERE document_id = %s
                """,
                (document_id,),
            )

            cursor.execute(
                """
                DELETE FROM data_entry_fields
                WHERE document_id = %s
                """,
                (document_id,),
            )

            # --------------------------------------------------
            # Extract fields
            # --------------------------------------------------

            extracted_fields = []

            seen = set()

            for block in blocks:

                text = (
                    block.get("text")
                    or ""
                ).strip()

                if not text:
                    continue

                confidence = float(
                    block.get(
                        "confidence"
                    )
                    or 0
                )

                matches = extract_from_text(
                    text
                )

                for match in matches:

                    field_name = match[
                        "field_name"
                    ]

                    field_value = match[
                        "field_value"
                    ]

                    dedupe_key = (
                        field_name.lower(),
                        field_value.lower(),
                    )

                    if dedupe_key in seen:
                        continue

                    seen.add(
                        dedupe_key
                    )

                    status = confidence_status(
                        confidence
                    )

                    record = {
                        "document_id": document_id,
                        "data_entry_run_id": run_id,
                        "job_id": job_id,
                        "field_name": field_name,
                        "field_value": field_value,
                        "normalized_value": field_value.lower(),
                        "confidence": confidence,
                        "validation_status": status,
                        "source_text": text,
                        "matched_language": (
                            block.get("language")
                            or ""
                        ),
                        "page_number": block.get(
                            "page_number"
                        ),
                        "line_number": block.get(
                            "block_number"
                        ),
                        "block_id": block.get(
                            "id"
                        ),
                        "extraction_method": match[
                            "extraction_method"
                        ],
                        "field_type": match[
                            "field_type"
                        ],
                        "region_type": (
                            block.get("region_type")
                            or "text"
                        ),
                        "ocr_source": (
                            block.get("source")
                            or "surya"
                        ),
                    }

                    extracted_fields.append(
                        record
                    )

            # --------------------------------------------------
            # Insert extracted fields
            # --------------------------------------------------

            for field in extracted_fields:

                cursor.execute(
                    """
                    INSERT INTO extracted_fields
                    (
                        document_id,
                        data_entry_run_id,
                        job_id,
                        field_name,
                        field_value,
                        normalized_value,
                        confidence,
                        validation_status,
                        source_text,
                        matched_language,
                        page_number,
                        line_number,
                        block_id,
                        extraction_method,
                        field_type,
                        region_type,
                        ocr_source
                    )
                    VALUES
                    (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        field["document_id"],
                        field["data_entry_run_id"],
                        field["job_id"],
                        field["field_name"],
                        field["field_value"],
                        field["normalized_value"],
                        field["confidence"],
                        field["validation_status"],
                        field["source_text"],
                        field["matched_language"],
                        field["page_number"],
                        field["line_number"],
                        field["block_id"],
                        field["extraction_method"],
                        field["field_type"],
                        field["region_type"],
                        field["ocr_source"],
                    ),
                )

                cursor.execute(
                    """
                    INSERT INTO data_entry_fields
                    (
                        document_id,
                        run_id,
                        field_name,
                        field_value,
                        field_type,
                        confidence,
                        validation_status,
                        source_text,
                        page_number,
                        block_id
                    )
                    VALUES
                    (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        field["document_id"],
                        field["data_entry_run_id"],
                        field["field_name"],
                        field["field_value"],
                        field["field_type"],
                        field["confidence"],
                        field["validation_status"],
                        field["source_text"],
                        field["page_number"],
                        field["block_id"],
                    ),
                )

            # --------------------------------------------------
            # Final record
            # --------------------------------------------------

            final_record = {}

            for field in extracted_fields:

                name = field[
                    "field_name"
                ]

                if name not in final_record:

                    final_record[name] = (
                        field["field_value"]
                    )

            review_required = any(
                field[
                    "validation_status"
                ] != "accepted"
                for field in extracted_fields
            )

            status = (
                "review_required"
                if review_required
                else "completed"
            )

            # --------------------------------------------------
            # Save final materialized record
            # --------------------------------------------------

            import json

            cursor.execute(
                """
                INSERT INTO data_entry_records
                (
                    document_id,
                    run_id,
                    record_json
                )
                VALUES
                (
                    %s,
                    %s,
                    %s
                )
                ON DUPLICATE KEY UPDATE
                    record_json = VALUES(record_json),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    document_id,
                    run_id,
                    json.dumps(
                        final_record,
                        ensure_ascii=False,
                    ),
                ),
            )

            # --------------------------------------------------
            # Complete run
            # --------------------------------------------------

            cursor.execute(
                """
                UPDATE data_entry_runs
                SET
                    status = %s,
                    field_count = %s,
                    review_required = %s,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (
                    status,
                    len(extracted_fields),
                    1 if review_required else 0,
                    run_id,
                ),
            )

            connection.commit()

            return {
                "success": True,
                "document_id": document_id,
                "job_id": job_id,
                "filename": filename,
                "run_id": run_id,
                "total_blocks": len(blocks),
                "selected_blocks": len(blocks),
                "field_count": len(
                    extracted_fields
                ),
                "status": status,
                "review_required": review_required,
                "final_record": final_record,
                "fields": extracted_fields,
            }

        except Exception:

            connection.rollback()

            raise

        finally:

            cursor.close()