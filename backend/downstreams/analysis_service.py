from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any


# ============================================================
# DATABASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "astra_ocr.db"


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def get_connection():
    connection = sqlite3.connect(
        DATABASE_PATH,
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():

    connection = get_connection()

    cursor = connection.cursor()

    # --------------------------------------------------------
    # OCR BLOCKS
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ocr_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            job_id TEXT NOT NULL,
            page INTEGER,
            line INTEGER,

            language TEXT,
            region_type TEXT,

            text TEXT NOT NULL,
            confidence REAL,

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --------------------------------------------------------
    # SEARCH HISTORY
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            job_id TEXT NOT NULL,
            query TEXT NOT NULL,
            result_count INTEGER DEFAULT 0,

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --------------------------------------------------------
    # DATA ENTRY
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS extracted_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            job_id TEXT NOT NULL,

            field_name TEXT,
            field_value TEXT,

            source_text TEXT,

            page INTEGER,
            line INTEGER,

            language TEXT,
            confidence REAL,

            extraction_method TEXT,

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --------------------------------------------------------
    # PATTERNS
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS extracted_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            job_id TEXT NOT NULL,

            pattern_type TEXT,
            pattern_value TEXT,

            source_text TEXT,

            page INTEGER,
            line INTEGER,

            confidence REAL,

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --------------------------------------------------------
    # COMPLIANCE
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS compliance_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            job_id TEXT NOT NULL,

            rule_id TEXT,
            rule_name TEXT,

            status TEXT,
            severity TEXT,

            field_name TEXT,
            actual_value TEXT,

            message TEXT,

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()

    connection.close()


initialize_database()


# ============================================================
# OCR RESULT NORMALIZATION
# ============================================================

def extract_blocks(result: dict[str, Any]) -> list[dict[str, Any]]:

    blocks = []

    pages = result.get("pages", [])

    if not isinstance(pages, list):
        return blocks

    for page_index, page in enumerate(pages, start=1):

        if not isinstance(page, dict):
            continue

        page_number = page.get(
            "page_number",
            page_index,
        )

        ocr_result = page.get(
            "ocr_result",
            {},
        )

        if not isinstance(ocr_result, dict):
            continue

        page_blocks = ocr_result.get(
            "results",
            [],
        )

        if not isinstance(page_blocks, list):
            continue

        for line_index, block in enumerate(
            page_blocks,
            start=1,
        ):

            if not isinstance(block, dict):
                continue

            text = str(
                block.get("text") or ""
            ).strip()

            if not text:
                continue

            confidence = block.get(
                "confidence"
            )

            try:
                confidence = float(confidence)
            except (
                TypeError,
                ValueError,
            ):
                confidence = None

            blocks.append(
                {
                    "page": page_number,

                    "line": block.get(
                        "reading_order",
                        line_index,
                    ),

                    "language": block.get(
                        "language",
                        "unknown",
                    ),

                    "region_type": block.get(
                        "region_type",
                        block.get(
                            "label",
                            "text",
                        ),
                    ),

                    "text": text,

                    "confidence": confidence,
                }
            )

    return blocks


# ============================================================
# SEARCH INDEXING
# ============================================================

def index_document(
    job_id: str,
    result: dict[str, Any],
) -> dict[str, Any]:

    blocks = extract_blocks(result)

    connection = get_connection()

    cursor = connection.cursor()

    # Prevent duplicate blocks for same job.
    cursor.execute(
        """
        DELETE FROM ocr_blocks
        WHERE job_id = ?
        """,
        (job_id,),
    )

    for block in blocks:

        cursor.execute(
            """
            INSERT INTO ocr_blocks (
                job_id,
                page,
                line,
                language,
                region_type,
                text,
                confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                block["page"],
                block["line"],
                block["language"],
                block["region_type"],
                block["text"],
                block["confidence"],
            ),
        )

    connection.commit()

    connection.close()

    return {
        "indexed": len(blocks),
        "status": "ready",
    }


# ============================================================
# SEARCH
# ============================================================

def search_document(
    job_id: str,
    query: str,
    limit: int = 20,
) -> list[dict[str, Any]]:

    query = str(query or "").strip()

    if not query:
        return []

    connection = get_connection()

    cursor = connection.cursor()

    # SQLite LIKE search.
    #
    # This is intentionally simple for the first integration.
    # Later we can replace this layer with Meilisearch without
    # changing the frontend API.

    pattern = f"%{query}%"

    cursor.execute(
        """
        SELECT
            page,
            line,
            language,
            region_type,
            text,
            confidence
        FROM ocr_blocks
        WHERE job_id = ?
          AND text LIKE ?
        ORDER BY page, line
        LIMIT ?
        """,
        (
            job_id,
            pattern,
            limit,
        ),
    )

    rows = cursor.fetchall()

    results = []

    for row in rows:

        results.append(
            {
                "page": row["page"],
                "line": row["line"],
                "language": row["language"],
                "region_type": row["region_type"],
                "text": row["text"],
                "confidence": row["confidence"],
            }
        )

    cursor.execute(
        """
        INSERT INTO search_history (
            job_id,
            query,
            result_count
        )
        VALUES (?, ?, ?)
        """,
        (
            job_id,
            query,
            len(results),
        ),
    )

    connection.commit()

    connection.close()

    return results


# ============================================================
# DATA ENTRY — REGEX
# ============================================================

EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+"
    r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

PHONE_RE = re.compile(
    r"(?<!\d)"
    r"(?:\+91[\s-]?)?"
    r"[6-9]\d{9}"
    r"(?!\d)"
)

DATE_RE = re.compile(
    r"\b\d{1,2}"
    r"[/-]"
    r"\d{1,2}"
    r"[/-]"
    r"\d{2,4}\b"
)

PAN_RE = re.compile(
    r"\b[A-Z]{5}\d{4}[A-Z]\b",
    re.IGNORECASE,
)

GSTIN_RE = re.compile(
    r"\b\d{2}[A-Z]{5}\d{4}"
    r"[A-Z]\d[A-Z0-9]\b",
    re.IGNORECASE,
)

URL_RE = re.compile(
    r"\b(?:https?://|www\.)"
    r"[^\s<>\"']+",
    re.IGNORECASE,
)

CURRENCY_RE = re.compile(
    r"(?:₹|Rs\.?|INR)\s*"
    r"\d[\d,]*(?:\.\d{1,2})?",
    re.IGNORECASE,
)


# ============================================================
# KEY VALUE EXTRACTION
# ============================================================

KEY_VALUE_RE = re.compile(
    r"^\s*(.{2,100}?)\s*"
    r"(?:\:|\s+-\s+|\s+\|\s+)"
    r"\s*(.+?)\s*$",
    re.UNICODE,
)


def extract_key_values(
    text: str,
) -> list[dict[str, Any]]:

    results = []

    for line in str(text).splitlines():

        line = line.strip()

        if not line:
            continue

        match = KEY_VALUE_RE.match(line)

        if not match:
            continue

        key = match.group(1).strip()
        value = match.group(2).strip()

        if len(key) < 2:
            continue

        if len(value) < 1:
            continue

        results.append(
            {
                "field_name": key,
                "field_value": value,
                "extraction_method":
                    "generic_key_value",
            }
        )

    return results


# ============================================================
# PATTERN EXTRACTION
# ============================================================

def extract_patterns(
    text: str,
) -> list[dict[str, Any]]:

    patterns = []

    regexes = [
        (
            "email",
            EMAIL_RE,
        ),
        (
            "phone",
            PHONE_RE,
        ),
        (
            "date",
            DATE_RE,
        ),
        (
            "pan",
            PAN_RE,
        ),
        (
            "gstin",
            GSTIN_RE,
        ),
        (
            "url",
            URL_RE,
        ),
        (
            "amount",
            CURRENCY_RE,
        ),
    ]

    for pattern_type, regex in regexes:

        for match in regex.finditer(
            text
        ):

            patterns.append(
                {
                    "pattern_type":
                        pattern_type,

                    "pattern_value":
                        match.group(0),
                }
            )

    return patterns


# ============================================================
# DATA ENTRY
# ============================================================

def run_data_entry(
    job_id: str,
    result: dict[str, Any],
) -> dict[str, Any]:

    blocks = extract_blocks(result)

    fields = []
    patterns = []

    for block in blocks:

        key_values = extract_key_values(
            block["text"]
        )

        for field in key_values:

            fields.append(
                {
                    **field,
                    "page":
                        block["page"],
                    "line":
                        block["line"],
                    "language":
                        block["language"],
                    "confidence":
                        block["confidence"],
                    "source_text":
                        block["text"],
                }
            )

        detected_patterns = extract_patterns(
            block["text"]
        )

        for pattern in detected_patterns:

            patterns.append(
                {
                    **pattern,
                    "page":
                        block["page"],
                    "line":
                        block["line"],
                    "confidence":
                        block["confidence"],
                    "source_text":
                        block["text"],
                }
            )

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM extracted_fields
        WHERE job_id = ?
        """,
        (job_id,),
    )

    cursor.execute(
        """
        DELETE FROM extracted_patterns
        WHERE job_id = ?
        """,
        (job_id,),
    )

    # --------------------------------------------------------
    # SAVE FIELDS
    # --------------------------------------------------------

    for field in fields:

        cursor.execute(
            """
            INSERT INTO extracted_fields (
                job_id,
                field_name,
                field_value,
                source_text,
                page,
                line,
                language,
                confidence,
                extraction_method
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                field["field_name"],
                field["field_value"],
                field["source_text"],
                field["page"],
                field["line"],
                field["language"],
                field["confidence"],
                field["extraction_method"],
            ),
        )

    # --------------------------------------------------------
    # SAVE PATTERNS
    # --------------------------------------------------------

    for pattern in patterns:

        cursor.execute(
            """
            INSERT INTO extracted_patterns (
                job_id,
                pattern_type,
                pattern_value,
                source_text,
                page,
                line,
                confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                pattern["pattern_type"],
                pattern["pattern_value"],
                pattern["source_text"],
                pattern["page"],
                pattern["line"],
                pattern["confidence"],
            ),
        )

    connection.commit()

    connection.close()

    return {
        "field_count": len(fields),
        "pattern_count": len(patterns),
        "fields": fields,
        "patterns": patterns,
    }


# ============================================================
# COMPLIANCE
# ============================================================

def add_compliance_rule(
    rules,
    rule_id,
    rule_name,
    status,
    severity,
    message,
    field_name=None,
    actual_value=None,
):

    rules.append(
        {
            "rule_id": rule_id,
            "rule_name": rule_name,
            "status": status,
            "severity": severity,
            "field_name": field_name,
            "actual_value": actual_value,
            "message": message,
        }
    )


def run_compliance(
    job_id: str,
    result: dict[str, Any],
    data_entry: dict[str, Any],
) -> dict[str, Any]:

    rules = []

    blocks = extract_blocks(result)

    fields = data_entry.get(
        "fields",
        [],
    )

    # --------------------------------------------------------
    # OCR QUALITY
    # --------------------------------------------------------

    confidences = [
        float(block["confidence"])
        for block in blocks
        if block.get("confidence") is not None
    ]

    average_confidence = (
        sum(confidences) / len(confidences)
        if confidences
        else 0
    )

    if average_confidence >= 0.90:

        add_compliance_rule(
            rules,
            "OCR_QUALITY",
            "OCR quality",
            "PASS",
            "LOW",
            f"Average OCR confidence is "
            f"{average_confidence:.1%}.",
        )

    elif average_confidence >= 0.75:

        add_compliance_rule(
            rules,
            "OCR_QUALITY",
            "OCR quality",
            "WARNING",
            "MEDIUM",
            f"Average OCR confidence is "
            f"{average_confidence:.1%}. Review recommended.",
        )

    else:

        add_compliance_rule(
            rules,
            "OCR_QUALITY",
            "OCR quality",
            "FAIL",
            "HIGH",
            f"Average OCR confidence is only "
            f"{average_confidence:.1%}.",
        )

    # --------------------------------------------------------
    # CONTENT
    # --------------------------------------------------------

    if blocks:

        add_compliance_rule(
            rules,
            "CONTENT_PRESENT",
            "Document content",
            "PASS",
            "LOW",
            f"{len(blocks)} OCR block(s) detected.",
        )

    else:

        add_compliance_rule(
            rules,
            "CONTENT_PRESENT",
            "Document content",
            "FAIL",
            "HIGH",
            "No OCR content was detected.",
        )

    # --------------------------------------------------------
    # EMPTY VALUES
    # --------------------------------------------------------

    empty_fields = [
        field
        for field in fields
        if not str(
            field.get("field_value") or ""
        ).strip()
    ]

    if empty_fields:

        add_compliance_rule(
            rules,
            "EMPTY_FIELDS",
            "Extracted field values",
            "WARNING",
            "MEDIUM",
            f"{len(empty_fields)} extracted field(s) "
            f"have empty values.",
        )

    else:

        add_compliance_rule(
            rules,
            "EMPTY_FIELDS",
            "Extracted field values",
            "PASS",
            "LOW",
            "No empty extracted field values detected.",
        )

    # --------------------------------------------------------
    # DATE VALIDATION
    # --------------------------------------------------------

    for field in fields:

        field_name = str(
            field.get("field_name") or ""
        ).lower()

        value = str(
            field.get("field_value") or ""
        )

        if (
            "date" not in field_name
            and "dob" not in field_name
        ):
            continue

        if DATE_RE.search(value):

            add_compliance_rule(
                rules,
                "DATE_FORMAT",
                "Date format",
                "PASS",
                "MEDIUM",
                "Date value has a recognized format.",
                field_name,
                value,
            )

        else:

            add_compliance_rule(
                rules,
                "DATE_FORMAT",
                "Date format",
                "FAIL",
                "MEDIUM",
                "Date value could not be recognized.",
                field_name,
                value,
            )

    # --------------------------------------------------------
    # PAN
    # --------------------------------------------------------

    for field in fields:

        name = str(
            field.get("field_name") or ""
        ).lower()

        value = str(
            field.get("field_value") or ""
        ).strip()

        if (
            "pan" in name
            and value
        ):

            status = (
                "PASS"
                if PAN_RE.fullmatch(value)
                else "FAIL"
            )

            add_compliance_rule(
                rules,
                "PAN_FORMAT",
                "PAN format",
                status,
                "MEDIUM",
                (
                    "PAN format is valid."
                    if status == "PASS"
                    else "PAN format appears invalid."
                ),
                name,
                value,
            )

    # --------------------------------------------------------
    # GSTIN
    # --------------------------------------------------------

    for field in fields:

        name = str(
            field.get("field_name") or ""
        ).lower()

        value = str(
            field.get("field_value") or ""
        ).strip()

        if (
            "gst" in name
            and value
        ):

            status = (
                "PASS"
                if GSTIN_RE.fullmatch(value)
                else "FAIL"
            )

            add_compliance_rule(
                rules,
                "GSTIN_FORMAT",
                "GSTIN format",
                status,
                "MEDIUM",
                (
                    "GSTIN format is valid."
                    if status == "PASS"
                    else "GSTIN format appears invalid."
                ),
                name,
                value,
            )

    # --------------------------------------------------------
    # FINAL COUNTS
    # --------------------------------------------------------

    passed = sum(
        rule["status"] == "PASS"
        for rule in rules
    )

    warnings = sum(
        rule["status"] == "WARNING"
        for rule in rules
    )

    failed = sum(
        rule["status"] == "FAIL"
        for rule in rules
    )

    if failed:

        overall_status = "NON_COMPLIANT"

    elif warnings:

        overall_status = "REVIEW_REQUIRED"

    else:

        overall_status = "COMPLIANT"

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM compliance_results
        WHERE job_id = ?
        """,
        (job_id,),
    )

    for rule in rules:

        cursor.execute(
            """
            INSERT INTO compliance_results (
                job_id,
                rule_id,
                rule_name,
                status,
                severity,
                field_name,
                actual_value,
                message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                rule["rule_id"],
                rule["rule_name"],
                rule["status"],
                rule["severity"],
                rule["field_name"],
                rule["actual_value"],
                rule["message"],
            ),
        )

    connection.commit()

    connection.close()

    return {
        "overall_status": overall_status,

        "total_rules": len(rules),

        "passed_rules": passed,

        "warning_rules": warnings,

        "failed_rules": failed,

        "rules": rules,
    }


# ============================================================
# COMPLETE ANALYSIS
# ============================================================

def run_downstream_analysis(
    job_id: str,
    result: dict[str, Any],
) -> dict[str, Any]:

    indexing = index_document(
        job_id,
        result,
    )

    data_entry = run_data_entry(
        job_id,
        result,
    )

    compliance = run_compliance(
        job_id,
        result,
        data_entry,
    )

    return {
        "search_indexing": indexing,

        "data_entry": data_entry,

        "compliance": compliance,
    }