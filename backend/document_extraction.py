"""
document_extraction.py
======================

Groq-powered, document-agnostic field extraction for ASTRA-OCR.

What this module does
---------------------
It powers the three buttons on the Chatbot page:

    1. Show fields & values        POST /api/extract/{job_id}/fields
    2. Generate database-ready JSON GET  /api/extract/{job_id}/json
    3. Save to database            POST /api/extract/{job_id}/save

    (plus GET /api/extract/latest-job, used by the chatbot to find the
     most recently scanned document so the user never has to upload one)

How it works
------------
    scanned document (already OCR'd structured PDF of the job)
        |  PyMuPDF text   (existing document_chat.extract_pdf_text)
        v
    Groq chat completion  <-- the LLM decides, per document, WHICH fields
        |                     matter for downstream systems and returns
        |                     them as JSON. Nothing is read from
        |                     structured.json and there is no fixed
        |                     field list in this file.
        v
    validated JSON  -->  shown in chat / shown as DB-ready JSON
        |
        v
    MySQL (tables are created automatically if they do not exist)

Python code in this file only VALIDATES and CLEANS what Groq returns
(types, duplicate keys, empty values). It never decides which fields exist.

Optional .env settings (all have defaults):

    GROQ_API_KEY                        required (already in your .env)
    GROQ_CHAT_MODEL                     default openai/gpt-oss-20b
    GROQ_EXTRACTION_MODEL               overrides the model for extraction only
    GROQ_EXTRACTION_REASONING_EFFORT    low | medium | high   (gpt-oss only, default medium)
    EXTRACTION_CHUNK_CHARS              characters of OCR text per Groq call, default 30000
    EXTRACTION_MAX_OUTPUT_TOKENS        default 16000
"""

import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from mysql.connector import Error as MySQLError
except Exception:  # pragma: no cover - mysql connector is installed in the app

    class MySQLError(Exception):
        pass


SCHEMA_VERSION = "1.0"

EXTRACTION_FILENAME = "ai_extraction.json"

ALLOWED_DATA_TYPES = {
    "string",
    "number",
    "currency",
    "percentage",
    "date",
    "datetime",
    "phone",
    "email",
    "id",
    "address",
    "boolean",
    "text",
}


# ======================================================================
# SETTINGS (read lazily so .env loading order never matters)
# ======================================================================

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def get_extraction_model() -> str:
    return (
        os.getenv("GROQ_EXTRACTION_MODEL")
        or os.getenv("GROQ_CHAT_MODEL")
        or "openai/gpt-oss-20b"
    )


# ======================================================================
# GROQ PROMPT
# ======================================================================

EXTRACTION_SYSTEM_PROMPT = """You are the data-extraction engine of an OCR platform.
You receive the OCR text of a scanned PDF and must return the information that
downstream systems (ERP, accounting, banking / KYC, student or HR records,
document management, analytics) would need from it.

There is NO fixed template. Work out what each document is, then decide which
fields matter for that kind of document.

RULES
1. A PDF can contain several different documents (for example three invoices,
   or a marksheet followed by a certificate). Detect every document separately
   and report it separately with its own page range. Never mix fields of
   different documents.
2. For each document return: document_type (short snake_case English label such
   as invoice, purchase_order, receipt, bank_statement, marksheet, certificate,
   id_card, passport, resume, contract, letter, medical_report, form, other),
   title (as printed, or a short descriptive title), language (main language or
   languages), page_start, page_end, summary (one sentence), fields, tables.
3. fields = the important facts only: identifiers (invoice / ID / account /
   reference numbers), dates, people and organisations (issuer, recipient,
   customer, vendor, student, patient ...), addresses, contact details (phone,
   email, website), tax / registration numbers, monetary amounts (subtotal,
   tax, discount, total, balance, currency), totals / results / grades, status,
   key terms, and anything else a downstream system would need to index,
   validate, reconcile or act on. Typically 8 to 40 fields per document.
   Skip boilerplate, slogans, terms-and-conditions text, repeated headers and
   footers, page numbers, stamps, watermarks and OCR noise.
4. Every field object has:
   key              snake_case English, specific (invoice_number, vendor_gstin,
                    student_name, total_amount ...)
   label            the label as printed in the document, or a clear English label
   value            exactly as printed, in the original language / script
                    (never translate)
   normalized_value clean machine-friendly form: dates -> YYYY-MM-DD, amounts ->
                    plain number such as 12450.50 (no currency symbol, no
                    thousands separator), phone -> digits with country code if
                    shown, email -> lowercase, otherwise identical to value
   data_type        one of: string, number, currency, percentage, date,
                    datetime, phone, email, id, address, boolean, text
   page             page number where the value was found
5. Repeating structures (line items, marks per subject, transactions ...) go in
   tables: {"name": "...", "columns": ["..."], "rows": [["...", "..."]]}.
   Every row is a list of strings aligned with columns. Do not repeat table
   cells as fields.
6. Use ONLY what is in the text. Never invent, guess or calculate values. If a
   value is missing or unreadable, leave it out (no null or empty fields).
   Correct obvious OCR spacing only when the intent is unambiguous.
7. Keys must be unique inside one document.
8. Reply with ONE JSON object and nothing else (no markdown, no commentary):
{"documents":[{"document_type":"","title":"","language":"","page_start":1,"page_end":1,"summary":"","fields":[{"key":"","label":"","value":"","normalized_value":"","data_type":"string","page":1}],"tables":[{"name":"","columns":[""],"rows":[[""]]}]}]}"""


CONTINUATION_NOTE = (
    "\n9. The text you receive is PART {part} of {total} of a longer PDF. If the "
    "first page of this part continues a document that began in the previous "
    "part, still return it as its own document object and add "
    "\"continues_previous\": true to it."
)


# ======================================================================
# SMALL HELPERS
# ======================================================================

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clean_str(value: Any, limit: Optional[int] = None) -> str:
    if value is None:
        return ""

    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)

    text = text.replace("\x00", "").strip()

    if limit and len(text) > limit:
        text = text[:limit]

    return text


def _to_int(value: Any) -> Optional[int]:
    try:
        if value is None or isinstance(value, bool):
            return None
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _slug_key(text: Any, fallback: str = "field") -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", _clean_str(text).lower()).strip("_")

    if not slug:
        slug = fallback

    return slug[:100]


# ======================================================================
# VALIDATION OF WHAT GROQ RETURNED
# ======================================================================

def _normalize_field(
    raw: Any,
    default_page: Optional[int],
) -> Optional[Dict[str, Any]]:

    if not isinstance(raw, dict):
        return None

    value = _clean_str(raw.get("value"))

    if not value:
        return None

    label = _clean_str(raw.get("label"), 255)

    key = _slug_key(raw.get("key") or label, "field")

    normalized = _clean_str(raw.get("normalized_value")) or value

    data_type = _clean_str(raw.get("data_type")).lower()

    if data_type not in ALLOWED_DATA_TYPES:
        data_type = "string"

    page = _to_int(raw.get("page"))

    if page is None:
        page = default_page

    return {
        "key": key,
        "label": label or key.replace("_", " ").title(),
        "value": value,
        "normalized_value": normalized,
        "data_type": data_type,
        "page": page,
    }


def _normalize_table(raw: Any) -> Optional[Dict[str, Any]]:

    if not isinstance(raw, dict):
        return None

    columns = raw.get("columns")
    rows = raw.get("rows")

    if not isinstance(rows, list) or not rows:
        return None

    if not isinstance(columns, list):
        columns = []

    columns = [_clean_str(column, 255) for column in columns]

    clean_rows: List[List[str]] = []

    for row in rows:

        if isinstance(row, dict):

            if not columns:
                columns = [_clean_str(key, 255) for key in row.keys()]

            row = [row.get(column, "") for column in columns]

        if not isinstance(row, (list, tuple)):
            continue

        cells = [_clean_str(cell) for cell in row]

        if any(cells):
            clean_rows.append(cells)

    if not clean_rows:
        return None

    width = max(len(columns), max(len(row) for row in clean_rows))

    while len(columns) < width:
        columns.append(f"column_{len(columns) + 1}")

    clean_rows = [row + [""] * (width - len(row)) for row in clean_rows]

    return {
        "name": _clean_str(raw.get("name"), 255) or "table",
        "columns": columns,
        "rows": clean_rows,
    }


def _dedupe_fields(fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Keys must be unique inside one document.

    - same key + same value  -> duplicate, dropped
    - same key + other value -> key_2, key_3 ...
    """

    result: List[Dict[str, Any]] = []
    seen: Dict[str, str] = {}

    for field in fields:

        key = field["key"]

        if key in seen:

            if seen[key] == field["value"]:
                continue

            counter = 2

            while f"{key}_{counter}" in seen:
                counter += 1

            key = f"{key}_{counter}"
            field = dict(field, key=key)

        seen[key] = field["value"]
        result.append(field)

    return result


def _normalize_document(
    raw: Any,
    default_pages: Tuple[Optional[int], Optional[int]],
) -> Optional[Dict[str, Any]]:

    if not isinstance(raw, dict):
        return None

    page_start = _to_int(raw.get("page_start"))
    page_end = _to_int(raw.get("page_end"))

    if page_start is None:
        page_start = default_pages[0]

    if page_end is None:
        page_end = default_pages[1]

    if (
        page_start is not None
        and page_end is not None
        and page_end < page_start
    ):
        page_end = page_start

    fields = []

    for item in raw.get("fields") or []:

        field = _normalize_field(item, page_start)

        if field:
            fields.append(field)

    tables = []

    for item in raw.get("tables") or []:

        table = _normalize_table(item)

        if table:
            tables.append(table)

    if not fields and not tables:
        return None

    document_type = _slug_key(raw.get("document_type"), "other")

    return {
        "document_type": document_type,
        "title": _clean_str(raw.get("title"), 512),
        "language": _clean_str(raw.get("language"), 100),
        "page_start": page_start,
        "page_end": page_end,
        "summary": _clean_str(raw.get("summary")),
        "fields": _dedupe_fields(fields),
        "tables": tables,
        "continues_previous": bool(raw.get("continues_previous")),
    }


def parse_json_loose(text: str) -> Any:
    """
    Parse the model output even if it is wrapped in code fences or has a
    sentence before / after the JSON object.
    """

    if text is None:
        raise ValueError("Groq returned an empty response.")

    cleaned = text.strip()

    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start != -1 and end > start:
        return json.loads(cleaned[start:end + 1])

    raise ValueError("Groq did not return valid JSON.")


# ======================================================================
# GROQ CALL
# ======================================================================

def _is_rate_limit(exc: Exception) -> bool:
    if getattr(exc, "status_code", None) == 429:
        return True

    return "rate limit" in str(exc).lower()


def _retry_delay(exc: Exception, attempt: int) -> float:
    match = re.search(
        r"try again in\s+([\d.]+)\s*(ms|s|m)\b",
        str(exc),
        flags=re.IGNORECASE,
    )

    if match:
        amount = float(match.group(1))
        unit = match.group(2).lower()

        seconds = (
            amount / 1000.0
            if unit == "ms"
            else amount * 60.0
            if unit == "m"
            else amount
        )

        return min(max(seconds + 1.0, 2.0), 60.0)

    return min(4.0 * (attempt + 1), 30.0)


def call_groq_for_json(
    client: Any,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    One Groq chat completion that must return a JSON object.

    Strategy:
      1. JSON mode (response_format=json_object).
      2. If Groq rejects / fails the JSON mode, retry once as plain text and
         parse the JSON ourselves.
      3. Rate limits (HTTP 429) are retried with a short wait.
    """

    model = model or get_extraction_model()

    max_tokens = _env_int("EXTRACTION_MAX_OUTPUT_TOKENS", 16000)

    last_error: Optional[Exception] = None

    for json_mode in (True, False):

        rate_limit_retries = 0

        while True:

            kwargs: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": 0.1,
                "max_completion_tokens": max_tokens,
                "stream": False,
            }

            if "gpt-oss" in model:
                kwargs["include_reasoning"] = False
                kwargs["reasoning_effort"] = os.getenv(
                    "GROQ_EXTRACTION_REASONING_EFFORT",
                    "medium",
                )

            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            try:

                response = client.chat.completions.create(**kwargs)

            except Exception as exc:

                last_error = exc

                if _is_rate_limit(exc) and rate_limit_retries < 3:
                    time.sleep(_retry_delay(exc, rate_limit_retries))
                    rate_limit_retries += 1
                    continue

                break  # leave the while loop, try the next mode

            if not response.choices:
                last_error = RuntimeError("Groq returned no response choices.")
                break

            choice = response.choices[0]
            content = choice.message.content

            if getattr(choice, "finish_reason", None) == "length":
                raise RuntimeError(
                    "Groq stopped because the output limit was reached. "
                    "Lower EXTRACTION_CHUNK_CHARS or raise "
                    "EXTRACTION_MAX_OUTPUT_TOKENS in .env."
                )

            try:
                parsed = parse_json_loose(content)
            except Exception as exc:
                last_error = exc
                break

            if not isinstance(parsed, dict):
                last_error = ValueError("Groq returned JSON that is not an object.")
                break

            return parsed

    raise RuntimeError(f"Groq extraction failed: {last_error}")


# ======================================================================
# CHUNKING
# ======================================================================

def build_page_chunks(
    pages: List[Dict[str, Any]],
    max_chars: int,
) -> List[List[Dict[str, Any]]]:
    """
    Group pages into chunks that stay below max_chars of OCR text.
    Pages are never split, so a page range is always exact.
    """

    chunks: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    size = 0

    for page in pages:

        text = page.get("text") or ""

        if not text.strip():
            continue

        if current and size + len(text) > max_chars:
            chunks.append(current)
            current = []
            size = 0

        current.append(page)
        size += len(text)

    if current:
        chunks.append(current)

    return chunks


def _chunk_text(chunk: List[Dict[str, Any]]) -> str:
    return "\n\n".join(
        f"===== PAGE {page['page']} =====\n\n{page['text']}"
        for page in chunk
    )


def _merge_continuation(
    previous: Dict[str, Any],
    current: Dict[str, Any],
) -> None:

    existing = {field["key"]: field["value"] for field in previous["fields"]}

    for field in current["fields"]:

        key = field["key"]

        if key in existing:

            if existing[key] == field["value"]:
                continue

            counter = 2

            while f"{key}_{counter}" in existing:
                counter += 1

            field = dict(field, key=f"{key}_{counter}")

        existing[field["key"]] = field["value"]
        previous["fields"].append(field)

    previous["tables"].extend(current["tables"])

    if current.get("page_end") is not None:
        previous["page_end"] = max(
            previous.get("page_end") or 0,
            current["page_end"],
        )

    if not previous.get("summary"):
        previous["summary"] = current.get("summary", "")


# ======================================================================
# MAIN EXTRACTION
# ======================================================================

def extract_document_fields(
    client: Any,
    document_data: Dict[str, Any],
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send the scanned document text to Groq and return the validated result.

    document_data is the dict produced by document_chat.extract_pdf_text():
        {"filename", "pages": [{"page", "text"}], "total_pages", ...}
    """

    pages = document_data.get("pages") or []

    chunks = build_page_chunks(
        pages,
        max(_env_int("EXTRACTION_CHUNK_CHARS", 30000), 2000),
    )

    if not chunks:
        raise ValueError(
            "The scanned document has no readable text to extract from."
        )

    model = get_extraction_model()
    filename = document_data.get("filename") or ""

    documents: List[Dict[str, Any]] = []

    for index, chunk in enumerate(chunks, start=1):

        first_page = chunk[0]["page"]
        last_page = chunk[-1]["page"]

        system_prompt = EXTRACTION_SYSTEM_PROMPT

        if len(chunks) > 1:
            system_prompt += CONTINUATION_NOTE.format(
                part=index,
                total=len(chunks),
            )

        user_prompt = (
            f"FILE NAME: {filename}\n"
            f"PAGES IN THIS TEXT: {first_page} to {last_page} "
            f"(PDF has {document_data.get('total_pages', len(pages))} pages)\n\n"
            f"{_chunk_text(chunk)}"
        )

        payload = call_groq_for_json(
            client,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=model,
        )

        raw_documents = payload.get("documents")

        if not isinstance(raw_documents, list):
            # tolerate a single document object returned at the top level
            raw_documents = [payload] if payload.get("fields") else []

        for raw in raw_documents:

            document = _normalize_document(raw, (first_page, last_page))

            if not document:
                continue

            if (
                document["continues_previous"]
                and documents
                and index > 1
            ):
                _merge_continuation(documents[-1], document)
                continue

            documents.append(document)

    if not documents:
        raise ValueError(
            "Groq could not find any extractable fields in this document."
        )

    for position, document in enumerate(documents, start=1):
        document.pop("continues_previous", None)
        document["document_index"] = position
        document["fields"] = _dedupe_fields(document["fields"])

    ordered_keys = (
        "document_index",
        "document_type",
        "title",
        "language",
        "page_start",
        "page_end",
        "summary",
        "fields",
        "tables",
    )

    documents = [
        {key: document[key] for key in ordered_keys}
        for document in documents
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "job_id": job_id,
        "filename": filename,
        "source": document_data.get("source"),
        "model": model,
        "extracted_at": _now_iso(),
        "total_pages": document_data.get("total_pages"),
        "documents": documents,
    }


# ======================================================================
# DATABASE-READY JSON
# ======================================================================

def count_fields(extraction: Dict[str, Any]) -> int:
    return sum(
        len(document.get("fields") or [])
        for document in extraction.get("documents") or []
    )


def build_db_record(extraction: Dict[str, Any]) -> Dict[str, Any]:
    """
    The JSON that is stored in MySQL.

    Per document:
        fields         flat {key: normalized_value}  -> easy to map to columns
        field_details  full detail (label, raw value, type, page)
        tables         line items etc.
    """

    documents = []

    for document in extraction.get("documents") or []:

        fields = document.get("fields") or []

        documents.append(
            {
                "document_index": document.get("document_index"),
                "document_type": document.get("document_type"),
                "title": document.get("title"),
                "language": document.get("language"),
                "page_start": document.get("page_start"),
                "page_end": document.get("page_end"),
                "summary": document.get("summary"),
                "fields": {
                    field["key"]: field["normalized_value"]
                    for field in fields
                },
                "field_details": fields,
                "tables": document.get("tables") or [],
            }
        )

    return {
        "schema_version": extraction.get("schema_version", SCHEMA_VERSION),
        "job_id": extraction.get("job_id"),
        "filename": extraction.get("filename"),
        "model": extraction.get("model"),
        "extracted_at": extraction.get("extracted_at"),
        "document_count": len(documents),
        "field_count": count_fields(extraction),
        "documents": documents,
    }


# ======================================================================
# MYSQL: TABLES (CREATE IF NOT EXISTS) AND SAVE
# ======================================================================

CREATE_TABLE_STATEMENTS: List[str] = [

    # One row per scanned job (the complete DB-ready JSON is kept here too)
    """
    CREATE TABLE IF NOT EXISTS ai_extractions (
        id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        job_id          VARCHAR(100)    NOT NULL,
        filename        VARCHAR(512)    NULL,
        model           VARCHAR(100)    NULL,
        schema_version  VARCHAR(20)     NOT NULL DEFAULT '1.0',
        document_count  INT             NOT NULL DEFAULT 0,
        field_count     INT             NOT NULL DEFAULT 0,
        extraction_json JSON            NOT NULL,
        extracted_at    DATETIME        NULL,
        created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
                                        ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uq_ai_extractions_job (job_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # One row per document found inside the PDF
    """
    CREATE TABLE IF NOT EXISTS ai_extracted_documents (
        id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        extraction_id   BIGINT UNSIGNED NOT NULL,
        job_id          VARCHAR(100)    NOT NULL,
        document_index  INT             NOT NULL,
        document_type   VARCHAR(100)    NULL,
        title           VARCHAR(512)    NULL,
        language        VARCHAR(100)    NULL,
        page_start      INT             NULL,
        page_end        INT             NULL,
        summary         TEXT            NULL,
        fields_json     JSON            NULL,
        tables_json     JSON            NULL,
        created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uq_ai_documents_extraction_index (extraction_id, document_index),
        KEY idx_ai_documents_job (job_id),
        KEY idx_ai_documents_type (document_type),
        CONSTRAINT fk_ai_documents_extraction
            FOREIGN KEY (extraction_id)
            REFERENCES ai_extractions (id)
            ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # One row per extracted field (easy to query / join downstream)
    """
    CREATE TABLE IF NOT EXISTS ai_extracted_fields (
        id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        document_id      BIGINT UNSIGNED NOT NULL,
        job_id           VARCHAR(100)    NOT NULL,
        document_index   INT             NOT NULL,
        field_key        VARCHAR(128)    NOT NULL,
        field_label      VARCHAR(255)    NULL,
        field_value      TEXT            NULL,
        normalized_value TEXT            NULL,
        data_type        VARCHAR(30)     NULL,
        page_number      INT             NULL,
        created_at       TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uq_ai_fields_document_key (document_id, field_key),
        KEY idx_ai_fields_job (job_id),
        KEY idx_ai_fields_key (field_key),
        CONSTRAINT fk_ai_fields_document
            FOREIGN KEY (document_id)
            REFERENCES ai_extracted_documents (id)
            ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]

EXTRACTION_TABLE_NAMES = [
    "ai_extractions",
    "ai_extracted_documents",
    "ai_extracted_fields",
]

_tables_ready = False
_tables_lock = threading.Lock()


def ensure_extraction_tables(
    connect_to_mysql: Callable[[], Any],
    force: bool = False,
) -> None:
    """
    CREATE TABLE IF NOT EXISTS for the three extraction tables.
    Safe to call any number of times.
    """

    global _tables_ready

    if _tables_ready and not force:
        return

    with _tables_lock:

        if _tables_ready and not force:
            return

        connection = None
        cursor = None

        try:

            connection = connect_to_mysql()
            cursor = connection.cursor()

            for statement in CREATE_TABLE_STATEMENTS:
                cursor.execute(statement)

            connection.commit()

            _tables_ready = True

        finally:

            if cursor:
                cursor.close()

            if connection:
                connection.close()


def _iso_to_mysql_datetime(value: Any) -> Optional[datetime]:
    try:
        return datetime.strptime(str(value), "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return None


def save_extraction_to_database(
    connect_to_mysql: Callable[[], Any],
    record: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Store a DB-ready record (see build_db_record) in MySQL.

    Saving the same job again replaces its previous rows (no duplicates);
    the parent row keeps its id.
    """

    job_id = record.get("job_id")

    if not job_id:
        raise ValueError("The extraction record has no job_id.")

    ensure_extraction_tables(connect_to_mysql)

    try:
        return _save_extraction_once(connect_to_mysql, record, job_id)
    except MySQLError as exc:
        # 1146 = table doesn't exist (e.g. dropped while the server runs)
        if getattr(exc, "errno", None) == 1146:
            ensure_extraction_tables(connect_to_mysql, force=True)
            return _save_extraction_once(connect_to_mysql, record, job_id)
        raise


def _save_extraction_once(
    connect_to_mysql: Callable[[], Any],
    record: Dict[str, Any],
    job_id: str,
) -> Dict[str, Any]:

    connection = None
    cursor = None

    try:

        connection = connect_to_mysql()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO ai_extractions (
                job_id, filename, model, schema_version,
                document_count, field_count, extraction_json, extracted_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                id              = LAST_INSERT_ID(id),
                filename        = VALUES(filename),
                model           = VALUES(model),
                schema_version  = VALUES(schema_version),
                document_count  = VALUES(document_count),
                field_count     = VALUES(field_count),
                extraction_json = VALUES(extraction_json),
                extracted_at    = VALUES(extracted_at)
            """,
            (
                job_id,
                record.get("filename"),
                record.get("model"),
                record.get("schema_version", SCHEMA_VERSION),
                record.get("document_count", 0),
                record.get("field_count", 0),
                json.dumps(record, ensure_ascii=False, default=str),
                _iso_to_mysql_datetime(record.get("extracted_at")),
            ),
        )

        extraction_id = cursor.lastrowid

        # Replace the children of this job (fields are removed by CASCADE).
        cursor.execute(
            "DELETE FROM ai_extracted_documents WHERE extraction_id = %s",
            (extraction_id,),
        )

        saved_fields = 0

        for document in record.get("documents") or []:

            details = document.get("field_details") or []

            cursor.execute(
                """
                INSERT INTO ai_extracted_documents (
                    extraction_id, job_id, document_index, document_type,
                    title, language, page_start, page_end, summary,
                    fields_json, tables_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    extraction_id,
                    job_id,
                    document.get("document_index"),
                    document.get("document_type"),
                    document.get("title"),
                    document.get("language"),
                    document.get("page_start"),
                    document.get("page_end"),
                    document.get("summary"),
                    json.dumps(
                        document.get("fields") or {},
                        ensure_ascii=False,
                        default=str,
                    ),
                    json.dumps(
                        document.get("tables") or [],
                        ensure_ascii=False,
                        default=str,
                    ),
                ),
            )

            document_id = cursor.lastrowid

            rows = [
                (
                    document_id,
                    job_id,
                    document.get("document_index"),
                    field["key"][:128],
                    field.get("label"),
                    field.get("value"),
                    field.get("normalized_value"),
                    field.get("data_type"),
                    field.get("page"),
                )
                for field in details
            ]

            if rows:

                cursor.executemany(
                    """
                    INSERT INTO ai_extracted_fields (
                        document_id, job_id, document_index, field_key,
                        field_label, field_value, normalized_value,
                        data_type, page_number
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    rows,
                )

                saved_fields += len(rows)

        connection.commit()

        return {
            "extraction_id": extraction_id,
            "job_id": job_id,
            "document_count": len(record.get("documents") or []),
            "field_count": saved_fields,
            "tables": EXTRACTION_TABLE_NAMES,
        }

    except Exception:

        if connection:
            try:
                connection.rollback()
            except Exception:
                pass

        raise

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ======================================================================
# DOCUMENT TEXT FALLBACK (OCR JSON stored in MySQL)
# ======================================================================

def _collect_text(node: Any, parts: List[str]) -> None:

    if isinstance(node, str):
        if node.strip():
            parts.append(node.strip())
        return

    if isinstance(node, list):
        for item in node:
            _collect_text(item, parts)
        return

    if isinstance(node, dict):

        value = node.get("text")

        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
            return

        for key, child in node.items():
            if isinstance(child, (list, dict)):
                _collect_text(child, parts)


def _page_text(page: Any) -> str:

    if isinstance(page, str):
        return page.strip()

    if isinstance(page, dict):

        for key in ("text", "full_text", "final_text", "ocr_text", "content"):

            value = page.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

        parts: List[str] = []
        _collect_text(page, parts)

        return "\n".join(parts)

    return ""


def document_data_from_raw_json(
    raw_json: Any,
    filename: Optional[str],
) -> Optional[Dict[str, Any]]:
    """
    Last-resort source: documents.raw_json (the OCR result saved at scan time).
    """

    try:
        data = json.loads(raw_json) if isinstance(raw_json, (str, bytes)) else raw_json
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    source_pages = data.get("pages")

    if not isinstance(source_pages, list):
        return None

    pages = []

    for position, page in enumerate(source_pages, start=1):

        number = (
            _to_int(page.get("page") or page.get("page_number"))
            if isinstance(page, dict)
            else None
        ) or position

        text = _page_text(page)

        pages.append(
            {
                "page": number,
                "text": text,
                "characters": len(text),
            }
        )

    total = sum(page["characters"] for page in pages)

    if total <= 50:
        return None

    return {
        "filename": filename or "document",
        "pages": pages,
        "full_text": "\n\n".join(
            f"===== PAGE {page['page']} =====\n\n{page['text']}"
            for page in pages
        ),
        "total_pages": len(pages),
        "total_characters": total,
        "has_text": True,
        "source": "OCR JSON stored in MySQL",
    }


# ======================================================================
# FASTAPI ROUTER
# ======================================================================

def create_extraction_router(
    *,
    jobs: Dict[str, Dict[str, Any]],
    jobs_dir: Path,
    connect_to_mysql: Callable[[], Any],
    get_chat_document: Callable[[str], Dict[str, Any]],
    resolve_structured_pdf: Callable[[str], Optional[Path]],
    create_groq_client: Callable[[], Any],
    extract_pdf_text: Callable[[str], Dict[str, Any]],
):
    """
    Build the /api/extract router.

    Everything it needs from api.py is passed in, so this file never imports
    api.py (no circular imports).
    """

    from fastapi import APIRouter, HTTPException

    router = APIRouter(prefix="/api/extract", tags=["AI field extraction"])

    extraction_cache: Dict[str, Dict[str, Any]] = {}
    document_cache: Dict[str, Dict[str, Any]] = {}
    job_locks: Dict[str, threading.Lock] = {}
    locks_guard = threading.Lock()

    def lock_for(job_id: str) -> threading.Lock:
        with locks_guard:
            return job_locks.setdefault(job_id, threading.Lock())

    # ------------------------------------------------------------------
    # Which scanned document?
    # ------------------------------------------------------------------

    def load_document(job_id: str) -> Dict[str, Any]:

        job = jobs.get(job_id)

        if job and job.get("status") != "completed":
            raise HTTPException(
                status_code=400,
                detail=(
                    "The document is still being scanned. "
                    "Please wait until processing is completed."
                ),
            )

        if job_id in document_cache:
            return document_cache[job_id]

        # 1. The structured PDF text the chatbot already uses
        if job:
            try:
                document = get_chat_document(job_id)
                if document and document.get("has_text"):
                    return document
            except Exception:
                pass

        # 2. Structured PDF on disk (works after a server restart too)
        try:
            pdf_path = resolve_structured_pdf(job_id)

            if pdf_path:
                document = extract_pdf_text(str(pdf_path))

                if document.get("has_text"):
                    document_cache[job_id] = document
                    return document
        except Exception:
            pass

        # 3. OCR JSON saved in MySQL
        connection = None
        cursor = None

        try:
            connection = connect_to_mysql()
            cursor = connection.cursor()
            cursor.execute(
                "SELECT filename, raw_json FROM documents WHERE job_id = %s",
                (job_id,),
            )
            row = cursor.fetchone()

            if row:
                document = document_data_from_raw_json(row[1], row[0])

                if document:
                    document_cache[job_id] = document
                    return document
        except Exception:
            pass
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        raise HTTPException(
            status_code=404,
            detail=(
                "No scanned document text was found for this job. "
                "Scan a document first on the Documents page."
            ),
        )

    # ------------------------------------------------------------------
    # Extraction (Groq) with cache
    # ------------------------------------------------------------------

    def extraction_path(job_id: str) -> Path:
        return Path(jobs_dir) / job_id / EXTRACTION_FILENAME

    def read_saved_extraction(job_id: str) -> Optional[Dict[str, Any]]:

        if job_id in extraction_cache:
            return extraction_cache[job_id]

        path = extraction_path(job_id)

        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("documents"):
                    extraction_cache[job_id] = data
                    return data
            except Exception:
                return None

        return None

    def write_extraction(job_id: str, extraction: Dict[str, Any]) -> None:

        extraction_cache[job_id] = extraction

        try:
            path = extraction_path(job_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(extraction, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            print(f"WARNING: could not write {EXTRACTION_FILENAME}: {exc}")

    def get_extraction(job_id: str, refresh: bool):
        """
        returns (extraction, from_cache)
        """

        with lock_for(job_id):

            if not refresh:

                cached = read_saved_extraction(job_id)

                if cached:
                    return cached, True

            document = load_document(job_id)

            try:
                client = create_groq_client()
            except SystemExit:
                raise HTTPException(
                    status_code=500,
                    detail="GROQ_API_KEY is not configured in .env.",
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=500,
                    detail=f"Could not create Groq client: {exc}",
                )

            try:
                extraction = extract_document_fields(
                    client,
                    document,
                    job_id=job_id,
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc))
            except Exception as exc:
                print(f"GROQ EXTRACTION ERROR: {exc}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Groq extraction failed: {exc}",
                )

            write_extraction(job_id, extraction)

            return extraction, False

    # ------------------------------------------------------------------
    # Endpoints
    # ------------------------------------------------------------------

    @router.get("/latest-job")
    def latest_job():
        """
        The most recently scanned document, so the chatbot needs no upload.
        """

        completed = [
            (job.get("updated_at") or 0, job_id, job)
            for job_id, job in jobs.items()
            if isinstance(job, dict) and job.get("status") == "completed"
        ]

        if completed:

            completed.sort(key=lambda item: item[0], reverse=True)

            _, job_id, job = completed[0]

            return {
                "success": True,
                "job_id": job_id,
                "filename": job.get("filename"),
                "source": "running_jobs",
            }

        connection = None
        cursor = None

        try:
            connection = connect_to_mysql()
            cursor = connection.cursor()
            cursor.execute(
                "SELECT job_id, filename FROM documents "
                "ORDER BY id DESC LIMIT 1"
            )
            row = cursor.fetchone()

            if row:
                return {
                    "success": True,
                    "job_id": row[0],
                    "filename": row[1],
                    "source": "database",
                }
        except Exception as exc:
            print(f"latest-job lookup failed: {exc}")
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        raise HTTPException(
            status_code=404,
            detail=(
                "No scanned document found yet. "
                "Scan a document on the Documents page first."
            ),
        )

    @router.post("/{job_id}/fields")
    def extract_fields(job_id: str, refresh: bool = True):
        """
        Button 1: Groq reads the scanned document and returns its fields.
        """

        extraction, from_cache = get_extraction(job_id, refresh)

        return {
            "success": True,
            "job_id": job_id,
            "filename": extraction.get("filename"),
            "model": extraction.get("model"),
            "extracted_at": extraction.get("extracted_at"),
            "document_count": len(extraction.get("documents") or []),
            "field_count": count_fields(extraction),
            "documents": extraction.get("documents"),
            "from_cache": from_cache,
        }

    @router.get("/{job_id}/json")
    def extraction_json(job_id: str, refresh: bool = False):
        """
        Button 2: the database-ready JSON of the Groq extraction.
        """

        extraction, from_cache = get_extraction(job_id, refresh)

        return {
            "success": True,
            "job_id": job_id,
            "from_cache": from_cache,
            "record": build_db_record(extraction),
        }

    @router.post("/{job_id}/save")
    def save_extraction(job_id: str):
        """
        Button 3: store the Groq extraction in MySQL.
        """

        extraction, from_cache = get_extraction(job_id, False)

        record = build_db_record(extraction)

        try:
            result = save_extraction_to_database(connect_to_mysql, record)
        except MySQLError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"MySQL error: {exc}",
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            print(f"SAVE EXTRACTION ERROR: {exc}")
            raise HTTPException(
                status_code=500,
                detail=f"Saving to the database failed: {exc}",
            )

        return {
            "success": True,
            "message": "Extracted fields saved to MySQL.",
            "from_cache": from_cache,
            **result,
        }

    return router