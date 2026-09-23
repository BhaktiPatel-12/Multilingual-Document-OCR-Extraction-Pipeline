# """
# Astra-OCR OCR Result Ingestion
# ==============================

# Takes the exact OCR result produced by Astra-OCR and stores it
# in MySQL.

# Stored information:

# 1. Document
# 2. Complete raw OCR JSON
# 3. Pages
# 4. OCR blocks
# 5. Summary information
# """

# import json
# import hashlib
# from typing import Any, Dict, List, Optional

# from .database import database_connection


# # ==============================================================
# # HELPERS
# # ==============================================================

# def safe_string(value: Any) -> str:
#     if value is None:
#         return ""

#     if isinstance(value, str):
#         return value

#     return str(value)


# def json_string(value: Any) -> str:
#     """
#     Convert arbitrary Python data into JSON text.
#     """

#     return json.dumps(
#         value,
#         ensure_ascii=False,
#         default=str,
#     )


# def get_pages(result: Dict[str, Any]) -> List[Dict[str, Any]]:
#     """
#     Support Astra OCR page formats.
#     """

#     pages = result.get("pages")

#     if isinstance(pages, list):
#         return pages

#     if isinstance(pages, dict):
#         return list(pages.values())

#     nested = result.get("result")

#     if isinstance(nested, dict):

#         nested_pages = nested.get("pages")

#         if isinstance(nested_pages, list):
#             return nested_pages

#         if isinstance(nested_pages, dict):
#             return list(nested_pages.values())

#     return []


# def get_blocks(
#     page: Dict[str, Any]
# ) -> List[Dict[str, Any]]:

#     for key in (
#         "blocks",
#         "ocr_blocks",
#         "text_blocks",
#     ):

#         value = page.get(key)

#         if isinstance(value, list):
#             return value

#     return []


# def get_block_text(
#     block: Dict[str, Any]
# ) -> str:

#     for key in (
#         "text",
#         "content",
#         "html",
#         "value",
#     ):

#         value = block.get(key)

#         if value is not None:

#             text = safe_string(value).strip()

#             if text:
#                 return text

#     return ""


# def get_confidence(
#     block: Dict[str, Any]
# ) -> float:

#     for key in (
#         "confidence",
#         "score",
#         "rec_score",
#     ):

#         value = block.get(key)

#         try:

#             number = float(value)

#             if 0 <= number <= 1:
#                 number *= 100

#             return number

#         except (
#             TypeError,
#             ValueError,
#         ):

#             continue

#     return 0.0


# def get_languages(
#     result: Dict[str, Any]
# ) -> List[str]:

#     languages = set()

#     def add(value):

#         if not value:
#             return

#         if isinstance(value, list):

#             for item in value:

#                 if item:
#                     languages.add(
#                         safe_string(item).strip()
#                     )

#         elif isinstance(value, str):

#             for item in value.replace(
#                 "/",
#                 ",",
#             ).replace(
#                 "+",
#                 ",",
#             ).split(","):

#                 item = item.strip()

#                 if item:
#                     languages.add(item)

#     add(result.get("detected_languages"))
#     add(result.get("languages"))
#     add(result.get("language"))

#     for page in get_pages(result):

#         add(page.get("detected_languages"))
#         add(page.get("languages"))
#         add(page.get("language"))

#         final_result = page.get(
#             "final_result"
#         )

#         if isinstance(final_result, dict):
#             add(
#                 final_result.get(
#                     "detected_languages"
#                 )
#             )

#     return sorted(languages)


# def get_quality_score(
#     result: Dict[str, Any]
# ) -> Optional[float]:

#     candidates = [

#         result.get("quality_score"),

#         result.get("accuracy"),

#         (
#             result.get("final_quality") or {}
#         ).get("score"),

#         (
#             result.get("final_quality") or {}
#         ).get("quality_score"),

#         (
#             result.get("final_quality") or {}
#         ).get("total_score"),
#     ]

#     for value in candidates:

#         try:

#             number = float(value)

#             if number <= 1:
#                 number *= 100

#             return number

#         except (
#             TypeError,
#             ValueError,
#         ):

#             continue

#     return None


# # ==============================================================
# # DOCUMENT ID
# # ==============================================================

# def make_document_hash(
#     job_id: str,
#     filename: str,
# ) -> str:

#     value = f"{job_id}:{filename}"

#     return hashlib.sha256(
#         value.encode("utf-8")
#     ).hexdigest()


# # ==============================================================
# # MAIN INGESTION
# # ==============================================================

# def ingest_ocr_result(
#     *,
#     job_id: str,
#     filename: str,
#     ocr_result: Dict[str, Any],
# ) -> Dict[str, Any]:

#     if not job_id:
#         raise ValueError(
#             "job_id is required."
#         )

#     if not filename:
#         filename = "Processed Document"

#     if not isinstance(
#         ocr_result,
#         dict,
#     ):
#         raise ValueError(
#             "ocr_result must be a JSON object."
#         )

#     pages = get_pages(
#         ocr_result
#     )

#     languages = get_languages(
#         ocr_result
#     )

#     quality = get_quality_score(
#         ocr_result
#     )

#     raw_json = json_string(
#         ocr_result
#     )

#     document_hash = make_document_hash(
#         job_id,
#         filename,
#     )

#     total_blocks = 0

#     for page in pages:
#         total_blocks += len(
#             get_blocks(page)
#         )

#     # ==========================================================
#     # DATABASE TRANSACTION
#     # ==========================================================

#     with database_connection() as connection:

#         cursor = connection.cursor(
#             dictionary=True
#         )

#         try:

#             # --------------------------------------------------
#             # Check existing document
#             # --------------------------------------------------

#             cursor.execute(
#                 """
#                 SELECT id
#                 FROM documents
#                 WHERE job_id = %s
#                 LIMIT 1
#                 """,
#                 (job_id,),
#             )

#             existing = cursor.fetchone()

#             if existing:

#                 document_id = existing["id"]

#                 # Update raw JSON so repeated save is idempotent.
#                 cursor.execute(
#                     """
#                     UPDATE documents
#                     SET
#                         filename = %s,
#                         raw_json = %s,
#                         document_hash = %s,
#                         total_pages = %s,
#                         total_blocks = %s,
#                         languages_json = %s,
#                         quality_score = %s,
#                         updated_at = CURRENT_TIMESTAMP
#                     WHERE id = %s
#                     """,
#                     (
#                         filename,
#                         raw_json,
#                         document_hash,
#                         len(pages),
#                         total_blocks,
#                         json_string(languages),
#                         quality,
#                         document_id,
#                     ),
#                 )

#                 # Remove old child rows so the database reflects
#                 # the latest exact OCR result.
#                 cursor.execute(
#                     """
#                     DELETE FROM ocr_blocks
#                     WHERE document_id = %s
#                     """,
#                     (document_id,),
#                 )

#                 cursor.execute(
#                     """
#                     DELETE FROM document_pages
#                     WHERE document_id = %s
#                     """,
#                     (document_id,),
#                 )

#             else:

#                 cursor.execute(
#                     """
#                     INSERT INTO documents
#                     (
#                         job_id,
#                         filename,
#                         document_hash,
#                         raw_json,
#                         total_pages,
#                         total_blocks,
#                         languages_json,
#                         quality_score
#                     )
#                     VALUES
#                     (
#                         %s,
#                         %s,
#                         %s,
#                         %s,
#                         %s,
#                         %s,
#                         %s,
#                         %s
#                     )
#                     """,
#                     (
#                         job_id,
#                         filename,
#                         document_hash,
#                         raw_json,
#                         len(pages),
#                         total_blocks,
#                         json_string(languages),
#                         quality,
#                     ),
#                 )

#                 document_id = cursor.lastrowid

#             # --------------------------------------------------
#             # Insert pages and blocks
#             # --------------------------------------------------

#             block_counter = 0

#             for page_index, page in enumerate(
#                 pages,
#                 start=1,
#             ):

#                 page_json = json_string(
#                     page
#                 )

#                 page_languages = []

#                 page_language_value = page.get(
#                     "detected_languages"
#                 )

#                 if isinstance(
#                     page_language_value,
#                     list,
#                 ):
#                     page_languages = page_language_value

#                 elif isinstance(
#                     page_language_value,
#                     str,
#                 ):
#                     page_languages = [
#                         item.strip()
#                         for item in page_language_value.split(
#                             ","
#                         )
#                         if item.strip()
#                     ]

#                 cursor.execute(
#                     """
#                     INSERT INTO document_pages
#                     (
#                         document_id,
#                         page_number,
#                         page_json,
#                         languages_json
#                     )
#                     VALUES
#                     (
#                         %s,
#                         %s,
#                         %s,
#                         %s
#                     )
#                     """,
#                     (
#                         document_id,
#                         page_index,
#                         page_json,
#                         json_string(
#                             page_languages
#                         ),
#                     ),
#                 )

#                 blocks = get_blocks(
#                     page
#                 )

#                 for block_index, block in enumerate(
#                     blocks,
#                     start=1,
#                 ):

#                     text = get_block_text(
#                         block
#                     )

#                     if not text:
#                         continue

#                     block_counter += 1

#                     bbox = (
#                         block.get("bbox")
#                         or block.get("polygon")
#                         or block.get("box")
#                     )

#                     language = (
#                         block.get("language")
#                         or block.get("lang")
#                         or ""
#                     )

#                     region_type = (
#                         block.get("label")
#                         or block.get("type")
#                         or block.get("region_type")
#                         or "text"
#                     )

#                     source = (
#                         block.get("source")
#                         or block.get("ocr_source")
#                         or "surya"
#                     )

#                     confidence = get_confidence(
#                         block
#                     )

#                     cursor.execute(
#                         """
#                         INSERT INTO ocr_blocks
#                         (
#                             document_id,
#                             page_number,
#                             block_number,
#                             text,
#                             language,
#                             region_type,
#                             confidence,
#                             bbox_json,
#                             source,
#                             block_json
#                         )
#                         VALUES
#                         (
#                             %s,
#                             %s,
#                             %s,
#                             %s,
#                             %s,
#                             %s,
#                             %s,
#                             %s,
#                             %s,
#                             %s
#                         )
#                         """,
#                         (
#                             document_id,
#                             page_index,
#                             block_index,
#                             text,
#                             safe_string(language),
#                             safe_string(region_type),
#                             confidence,
#                             json_string(bbox),
#                             safe_string(source),
#                             json_string(block),
#                         ),
#                     )

#             # --------------------------------------------------
#             # Summary
#             # --------------------------------------------------

#             cursor.execute(
#                 """
#                 INSERT INTO documents_summary
#                 (
#                     document_id,
#                     total_pages,
#                     total_blocks,
#                     languages_json,
#                     quality_score
#                 )
#                 VALUES
#                 (
#                     %s,
#                     %s,
#                     %s,
#                     %s,
#                     %s
#                 )
#                 ON DUPLICATE KEY UPDATE
#                     total_pages = VALUES(total_pages),
#                     total_blocks = VALUES(total_blocks),
#                     languages_json = VALUES(languages_json),
#                     quality_score = VALUES(quality_score),
#                     updated_at = CURRENT_TIMESTAMP
#                 """,
#                 (
#                     document_id,
#                     len(pages),
#                     total_blocks,
#                     json_string(languages),
#                     quality,
#                 ),
#             )

#             # --------------------------------------------------
#             # Language counts
#             # --------------------------------------------------

#             cursor.execute(
#                 """
#                 DELETE FROM document_language_counts
#                 WHERE document_id = %s
#                 """,
#                 (document_id,),
#             )

#             language_counts = {}

#             for page in pages:

#                 for block in get_blocks(page):

#                     language = safe_string(
#                         block.get("language")
#                         or block.get("lang")
#                         or "unknown"
#                     ).strip()

#                     if not language:
#                         language = "unknown"

#                     language_counts[language] = (
#                         language_counts.get(
#                             language,
#                             0,
#                         )
#                         + 1
#                     )

#             for language, count in language_counts.items():

#                 cursor.execute(
#                     """
#                     INSERT INTO document_language_counts
#                     (
#                         document_id,
#                         language,
#                         block_count
#                     )
#                     VALUES
#                     (
#                         %s,
#                         %s,
#                         %s
#                     )
#                     """,
#                     (
#                         document_id,
#                         language,
#                         count,
#                     ),
#                 )

#             connection.commit()

#             return {
#                 "success": True,
#                 "document_id": document_id,
#                 "job_id": job_id,
#                 "filename": filename,
#                 "pages_saved": len(pages),
#                 "blocks_saved": block_counter,
#                 "languages": languages,
#                 "quality_score": quality,
#             }

#         except Exception:

#             connection.rollback()

#             raise

#         finally:

#             cursor.close()































"""
Astra-OCR Database Ingestion
=============================

Saves the complete Astra-OCR result into the `documents` table.

Current scope:
    OCR Result
        ↓
    documents table

The complete OCR JSON is stored in:
    documents.raw_json

Document metadata is stored in:
    documents.job_id
    documents.doc_id
    documents.filename
    documents.document_hash
    documents.input_file
    documents.ocr_provider
    documents.fusion
    documents.page_count
    documents.total_pages
    documents.total_blocks
    documents.languages_json
    documents.quality_score

This version intentionally does NOT write to:
    document_pages
    ocr_blocks
    data_entry_*
    compliance_*
    search tables
"""

import hashlib
import json
from typing import Any, Dict

from .database import database_connection


# ==============================================================
# HELPERS
# ==============================================================

def _extract_pages(ocr_result: Dict[str, Any]):
    """
    Return the pages object from the OCR result.
    """

    pages = ocr_result.get("pages")

    if isinstance(pages, (list, dict)):
        return pages

    nested_result = ocr_result.get("result")

    if isinstance(nested_result, dict):
        pages = nested_result.get("pages")

        if isinstance(pages, (list, dict)):
            return pages

    return None


def _get_page_count(ocr_result: Dict[str, Any]) -> int:
    """
    Determine the number of pages in the OCR result.
    """

    pages = _extract_pages(ocr_result)

    if isinstance(pages, list):
        return len(pages)

    if isinstance(pages, dict):
        return len(pages)

    # ----------------------------------------------------------
    # Support page-number dictionary structures such as:
    #
    # {
    #     "1": {...},
    #     "2": {...},
    #     "3": {...}
    # }
    # ----------------------------------------------------------

    numeric_keys = [
        key
        for key in ocr_result.keys()
        if str(key).isdigit()
    ]

    if numeric_keys:
        return len(numeric_keys)

    return 0


def _get_total_blocks(ocr_result: Dict[str, Any]) -> int:
    """
    Count OCR blocks from the result when possible.
    """

    total_blocks = 0

    pages = _extract_pages(ocr_result)

    if isinstance(pages, list):

        for page in pages:

            if not isinstance(page, dict):
                continue

            blocks = (
                page.get("blocks")
                or page.get("ocr_blocks")
                or page.get("text_blocks")
                or []
            )

            if isinstance(blocks, list):
                total_blocks += len(blocks)

            elif isinstance(blocks, dict):
                total_blocks += len(blocks)

        return total_blocks

    if isinstance(pages, dict):

        for page in pages.values():

            if not isinstance(page, dict):
                continue

            blocks = (
                page.get("blocks")
                or page.get("ocr_blocks")
                or page.get("text_blocks")
                or []
            )

            if isinstance(blocks, list):
                total_blocks += len(blocks)

            elif isinstance(blocks, dict):
                total_blocks += len(blocks)

        return total_blocks

    # ----------------------------------------------------------
    # Some Astra/Surya outputs may have blocks directly
    # ----------------------------------------------------------

    blocks = (
        ocr_result.get("blocks")
        or ocr_result.get("ocr_blocks")
        or ocr_result.get("text_blocks")
        or []
    )

    if isinstance(blocks, list):
        return len(blocks)

    if isinstance(blocks, dict):
        return len(blocks)

    return 0


def _extract_languages(ocr_result: Dict[str, Any]):
    """
    Extract language information from the OCR result.

    Returns a JSON-serializable object.
    """

    languages = (
        ocr_result.get("languages")
        or ocr_result.get("language")
        or ocr_result.get("language_counts")
    )

    if languages is not None:
        return languages

    pages = _extract_pages(ocr_result)

    found_languages = []

    if isinstance(pages, list):

        for page in pages:

            if not isinstance(page, dict):
                continue

            page_languages = (
                page.get("languages")
                or page.get("language")
                or page.get("language_counts")
            )

            if isinstance(page_languages, list):
                found_languages.extend(page_languages)

            elif isinstance(page_languages, str):
                found_languages.append(page_languages)

            elif isinstance(page_languages, dict):
                found_languages.extend(
                    page_languages.keys()
                )

    elif isinstance(pages, dict):

        for page in pages.values():

            if not isinstance(page, dict):
                continue

            page_languages = (
                page.get("languages")
                or page.get("language")
                or page.get("language_counts")
            )

            if isinstance(page_languages, list):
                found_languages.extend(page_languages)

            elif isinstance(page_languages, str):
                found_languages.append(page_languages)

            elif isinstance(page_languages, dict):
                found_languages.extend(
                    page_languages.keys()
                )

    # Remove duplicates while preserving order
    unique_languages = []

    for language in found_languages:

        if language not in unique_languages:
            unique_languages.append(language)

    return unique_languages


def _extract_quality_score(
    ocr_result: Dict[str, Any]
):
    """
    Try to obtain the OCR quality score.

    Returns None when the OCR result does not contain one.
    """

    candidates = [
        ocr_result.get("quality_score"),
        ocr_result.get("accuracy"),
    ]

    final_quality = ocr_result.get("final_quality")

    if isinstance(final_quality, dict):

        candidates.extend(
            [
                final_quality.get("score"),
                final_quality.get("quality_score"),
                final_quality.get("total_score"),
            ]
        )

    for value in candidates:

        if value is None:
            continue

        try:
            return float(value)
        except (TypeError, ValueError):
            continue

    return None


def _build_document_hash(
    job_id: str,
    filename: str,
) -> str:
    """
    Generate a deterministic SHA-256 hash for the document/job.
    """

    source = f"{job_id}:{filename}"

    return hashlib.sha256(
        source.encode("utf-8")
    ).hexdigest()


# ==============================================================
# MAIN INGESTION
# ==============================================================

def ingest_ocr_result(
    *,
    job_id: str,
    filename: str,
    ocr_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Save the complete OCR result to the documents table.

    Existing job_id:
        UPDATE existing document

    New job_id:
        INSERT new document

    The complete OCR result is stored in raw_json.
    """

    # ----------------------------------------------------------
    # Validation
    # ----------------------------------------------------------

    if not job_id:
        raise ValueError(
            "job_id is required"
        )

    if not filename:
        filename = "Processed Document"

    if not isinstance(ocr_result, dict):
        raise ValueError(
            "ocr_result must be a dictionary"
        )

    # ----------------------------------------------------------
    # Prepare JSON
    # ----------------------------------------------------------

    raw_json = json.dumps(
        ocr_result,
        ensure_ascii=False,
        default=str,
    )

    # ----------------------------------------------------------
    # Metadata
    # ----------------------------------------------------------

    page_count = _get_page_count(
        ocr_result
    )

    total_blocks = _get_total_blocks(
        ocr_result
    )

    languages = _extract_languages(
        ocr_result
    )

    quality_score = _extract_quality_score(
        ocr_result
    )

    languages_json = json.dumps(
        languages,
        ensure_ascii=False,
        default=str,
    )

    document_hash = _build_document_hash(
        job_id,
        filename,
    )

    # ----------------------------------------------------------
    # Database
    # ----------------------------------------------------------

    with database_connection() as connection:

        cursor = connection.cursor(
            dictionary=True
        )

        try:

            # ==================================================
            # CHECK EXISTING DOCUMENT
            # ==================================================

            cursor.execute(
                """
                SELECT
                    id,
                    job_id
                FROM documents
                WHERE job_id = %s
                LIMIT 1
                """,
                (job_id,),
            )

            existing = cursor.fetchone()

            # ==================================================
            # UPDATE EXISTING DOCUMENT
            # ==================================================

            if existing:

                document_id = existing["id"]

                cursor.execute(
                    """
                    UPDATE documents
                    SET
                        doc_id = %s,
                        filename = %s,
                        document_hash = %s,
                        input_file = %s,
                        ocr_provider = %s,
                        fusion = %s,
                        page_count = %s,
                        total_pages = %s,
                        total_blocks = %s,
                        raw_json = %s,
                        languages_json = %s,
                        quality_score = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (
                        job_id,
                        filename,
                        document_hash,
                        filename,
                        "Surya OCR",
                        "Surya",
                        page_count,
                        page_count,
                        total_blocks,
                        raw_json,
                        languages_json,
                        quality_score,
                        document_id,
                    ),
                )

                operation = "updated"

            # ==================================================
            # INSERT NEW DOCUMENT
            # ==================================================

            else:

                cursor.execute(
                    """
                    INSERT INTO documents
                    (
                        job_id,
                        doc_id,
                        filename,
                        document_hash,
                        input_file,
                        ocr_provider,
                        fusion,
                        page_count,
                        total_pages,
                        total_blocks,
                        raw_json,
                        languages_json,
                        quality_score
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    """,
                    (
                        job_id,
                        job_id,
                        filename,
                        document_hash,
                        filename,
                        "Surya OCR",
                        "Surya",
                        page_count,
                        page_count,
                        total_blocks,
                        raw_json,
                        languages_json,
                        quality_score,
                    ),
                )

                document_id = cursor.lastrowid

                operation = "inserted"

            # ==================================================
            # COMMIT
            # ==================================================

            connection.commit()

            return {
                "success": True,
                "operation": operation,
                "document_id": document_id,
                "job_id": job_id,
                "filename": filename,
                "document_hash": document_hash,
                "page_count": page_count,
                "total_pages": page_count,
                "total_blocks": total_blocks,
                "languages": languages,
                "quality_score": quality_score,
                "raw_json_saved": True,
            }

        except Exception:
            connection.rollback()
            raise

        finally:
            cursor.close()