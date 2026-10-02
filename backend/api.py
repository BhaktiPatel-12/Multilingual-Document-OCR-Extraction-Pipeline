import json
import re
import os
import shutil
import subprocess
import sys
import threading
import time
import traceback
import uuid

from pathlib import Path
from typing import Any, Dict, List, Optional

from services.pdf_ocr_service import PDFOCRService
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# PyMuPDF
try:
    import pymupdf as fitz
except ImportError:
    import fitz

from pydantic import BaseModel


# ============================================================
# ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


# ============================================================
# DIRECTORIES
# ============================================================

UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
API_JOBS_DIR = OUTPUT_DIR / "api_jobs"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
API_JOBS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="ASTRA-OCR API",
    description="ASTRA-OCR backend API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# JOB STORAGE
# ============================================================

jobs: Dict[str, Dict[str, Any]] = {}


# ============================================================
# CHATBOT
# ============================================================

try:
    from document_chat import (
        create_groq_client,
        extract_pdf_text,
        ask_question,
        summarize_document,
    )
except ImportError as exc:
    raise RuntimeError(
        "Could not import document_chat.py. "
        "Make sure document_chat.py is located in the backend folder."
    ) from exc


chat_document_cache: Dict[str, Dict[str, Any]] = {}

chat_summary_cache: Dict[str, str] = {}


# ============================================================
# DIRECT CHATBOT PDF STORAGE
# ============================================================

CHAT_UPLOAD_DIR = API_JOBS_DIR / "chat_documents"

CHAT_UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# DOWNLOAD MAP
# ============================================================

DOWNLOAD_FILE_MAP = {
    "json": "json",
    "txt": "txt",
    "structured-pdf": "structured_pdf",
    "language-highlighted-pdf": "language_highlighted_pdf",
    "structured-ocr-json": "structured_ocr_json",
}


# ============================================================
# STRUCTURED OCR JSON HELPERS
# ============================================================

def find_structured_ocr_json(
    job_id: str,
) -> Optional[Path]:
    """
    Find the fifth ASTRA structured OCR JSON output.

    Expected filename:

        <original_filename>_structured.json

    Priority:

    1. result["outputs"]["structured_ocr_json"]
    2. expected filename inside job directory
    3. any *_structured.json inside job directory
    """

    job = jobs.get(job_id)

    if not job:
        return None

    # --------------------------------------------------------
    # 1. Check OCR result
    # --------------------------------------------------------

    result = job.get("result")

    if isinstance(result, dict):

        outputs = result.get(
            "outputs",
            {},
        )

        if isinstance(outputs, dict):

            structured_json = outputs.get(
                "structured_ocr_json"
            )

            if structured_json:

                path = Path(
                    str(structured_json)
                )

                if not path.is_absolute():
                    path = BASE_DIR / path

                if path.exists() and path.is_file():
                    return path

    # --------------------------------------------------------
    # 2. Search job directory
    # --------------------------------------------------------

    job_output_dir = (
        API_JOBS_DIR /
        job_id
    )

    if not job_output_dir.exists():
        return None

    filename = job.get("filename")

    if filename:

        original_stem = Path(
            str(filename)
        ).stem

        expected_name = (
            f"{original_stem}_structured.json"
        )

        matches = list(
            job_output_dir.rglob(
                expected_name
            )
        )

        if matches:
            return matches[0]

    # --------------------------------------------------------
    # 3. Generic fallback
    # --------------------------------------------------------

    json_candidates = list(
        job_output_dir.rglob(
            "*_structured.json"
        )
    )

    if json_candidates:
        return json_candidates[0]

    return None


def load_structured_ocr_json(
    job_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Load the fifth structured OCR JSON output.

    Returns:
        parsed dictionary
        or None if unavailable.
    """

    json_path = find_structured_ocr_json(
        job_id
    )

    if not json_path:
        return None

    try:

        with open(
            json_path,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if isinstance(data, dict):
            return data

    except Exception as exc:

        print()
        print("=" * 70)
        print("STRUCTURED OCR JSON LOAD FAILED")
        print("=" * 70)
        print(str(exc))
        print("=" * 70)
        print()

    return None


# ============================================================
# INVOICE EXTRACTION
# ============================================================

INVOICE_FIELDS = (
    "invoice_number",
    "invoice_date",
    "customer",
    "address",
    "phone",
    "email",
    "total",
)


def normalize_invoice_value(
    value: Any,
) -> Optional[str]:
    """
    Convert an invoice field into a clean string.

    Missing/empty values become None so MySQL stores NULL.
    """

    if value is None:
        return None

    if isinstance(value, str):

        value = value.strip()

        if not value:
            return None

        return value

    if isinstance(value, (int, float)):

        return str(value)

    if isinstance(value, list):

        parts = []

        for item in value:

            normalized = normalize_invoice_value(
                item
            )

            if normalized:
                parts.append(normalized)

        if parts:
            return ", ".join(parts)

        return None

    if isinstance(value, dict):

        # Prefer common value-like keys.
        for key in (
            "value",
            "text",
            "content",
            "name",
            "label",
        ):

            if key in value:

                normalized = normalize_invoice_value(
                    value.get(key)
                )

                if normalized:
                    return normalized

        return None

    return str(value).strip() or None


def recursively_find_invoice_documents(
    value: Any,
) -> List[Dict[str, Any]]:
    """
    Recursively search a structured OCR JSON object.

    A document is considered an invoice ONLY when:

        document["type"] == "invoice"

    The comparison is exact after trimming/lowercasing.

    No guessing is performed.
    """

    found = []

    if isinstance(value, dict):

        document_type = value.get(
            "type"
        )

        if (
            isinstance(document_type, str)
            and document_type.strip().lower() == "invoice"
        ):
            found.append(value)

        for child_value in value.values():

            found.extend(
                recursively_find_invoice_documents(
                    child_value
                )
            )

    elif isinstance(value, list):

        for item in value:

            found.extend(
                recursively_find_invoice_documents(
                    item
                )
            )

    return found


def extract_invoice_documents(
    structured_json: Dict[str, Any],
) -> List[Dict[str, Optional[str]]]:
    """
    Extract ALL exact invoice documents from the structured OCR JSON.

    Every object with:

        type == "invoice"

    becomes one invoice record.

    This is intentionally strict about document type, but tolerant
    about where invoice fields are stored.
    """

    invoice_documents = recursively_find_invoice_documents(
        structured_json
    )

    extracted_documents = []

    for invoice_document in invoice_documents:

        fields_source = invoice_document.get("fields")

        if not isinstance(fields_source, dict):
            fields_source = invoice_document

        extracted = {}

        for field_name in INVOICE_FIELDS:

            value = None

            if isinstance(fields_source, dict):
                value = fields_source.get(field_name)

                if isinstance(value, dict):
                    value = value.get("value")

            if value is None:
                value = invoice_document.get(field_name)

            # Useful aliases produced by different structured OCR layouts.
            if value is None and isinstance(fields_source, dict):
                aliases = {
                    "invoice_number": ("invoice_no", "invoice_id", "number"),
                    "invoice_date": ("date", "bill_date"),
                    "customer": ("customer_name", "client", "client_name", "bill_to"),
                    "address": ("customer_address", "billing_address", "bill_to_address"),
                    "phone": ("telephone", "mobile", "contact"),
                    "email": ("email_address", "customer_email"),
                    "total": ("grand_total", "total_amount", "amount_total", "amount_due"),
                }
                for alias in aliases.get(field_name, ()):
                    if alias in fields_source:
                        value = fields_source.get(alias)
                        if isinstance(value, dict):
                            value = value.get("value")
                        if value is not None:
                            break

            extracted[field_name] = normalize_invoice_value(value)

        # --------------------------------------------------------
        # Fallback for totals that are present in the invoice text
        # but were not copied into fields.
        # --------------------------------------------------------
        if not extracted.get("total"):
            text_values = invoice_document.get("text")
            if isinstance(text_values, list):
                for text_value in text_values:
                    text = normalize_invoice_value(text_value)
                    if not text:
                        continue

                    match = re.search(
                        r"\btotal\s*\$?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
                        text,
                        flags=re.IGNORECASE,
                    )
                    if match:
                        extracted["total"] = "$ " + match.group(1)
                        break

        # --------------------------------------------------------
        # Fallback for customer/address from common text layouts.
        # We only use this when the structured fields are missing.
        # --------------------------------------------------------
        if not extracted.get("address"):
            address_value = invoice_document.get("address")
            extracted["address"] = normalize_invoice_value(address_value)

        extracted_documents.append(extracted)

    return extracted_documents


def extract_invoice_fields(
    structured_json: Dict[str, Any],
) -> Optional[Dict[str, Optional[str]]]:
    """Backward-compatible helper returning the first invoice only."""

    invoices = extract_invoice_documents(structured_json)

    if not invoices:
        return None

    return invoices[0]


# ============================================================
# MYSQL CONFIGURATION
# ============================================================

MYSQL_HOST = os.getenv(
    "MYSQL_HOST",
    "localhost",
)

MYSQL_PORT = int(
    os.getenv(
        "MYSQL_PORT",
        "3306",
    )
)

MYSQL_USER = os.getenv(
    "MYSQL_USER",
    "root",
)

MYSQL_PASSWORD = os.getenv(
    "MYSQL_PASSWORD",
    "",
)

MYSQL_DATABASE = os.getenv(
    "MYSQL_DATABASE",
    "astra_ocr",
)


def connect_to_mysql():
    """
    Create a MySQL connection.
    """

    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
    )


# ============================================================
# DATA ENTRY REQUEST MODELS
# ============================================================

class DataEntryItem(BaseModel):
    name: str
    type: Optional[str] = None
    value: Optional[str] = None
    confidence: Optional[float] = None
    status: Optional[str] = "Ready"


class DataEntrySaveRequest(BaseModel):
    job_id: str
    entries: List[DataEntryItem]


# ============================================================
# INVOICE REQUEST MODEL
# ============================================================

class InvoiceSaveRequest(BaseModel):
    job_id: str

    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    customer: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    total: Optional[str] = None


# ============================================================
# CHATBOT REQUEST MODEL
# ============================================================

class InvoiceUpdateRequest(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    customer: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    total: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = None


# ============================================================
# SAVE DOCUMENT JSON TO MYSQL
# ============================================================

def save_document_to_database(
    job_id: str,
    filename: str,
    input_file: str,
    ocr_result: Dict[str, Any],
):
    """
    Automatically saves the complete OCR JSON result
    into the documents table.
    """

    connection = None
    cursor = None

    try:

        print()
        print("=" * 70)
        print("SAVING OCR JSON TO MYSQL")
        print("=" * 70)

        connection = connect_to_mysql()
        cursor = connection.cursor()

        pdf_id = ocr_result.get(
            "pdf_id"
        )

        page_count = ocr_result.get(
            "total_pages",
            0,
        )

        # ----------------------------------------------------
        # Determine OCR provider
        # ----------------------------------------------------

        ocr_provider = "Surya OCR"

        pages = ocr_result.get(
            "pages",
            [],
        )

        if isinstance(pages, list):

            sources = []

            for page in pages:

                if not isinstance(
                    page,
                    dict,
                ):
                    continue

                final_source = page.get(
                    "final_source"
                )

                if final_source:
                    sources.append(
                        str(final_source)
                    )

            if sources:

                unique_sources = list(
                    dict.fromkeys(
                        sources
                    )
                )

                ocr_provider = " / ".join(
                    unique_sources
                )

        # ----------------------------------------------------
        # Fusion
        # ----------------------------------------------------

        fusion = ocr_result.get(
            "fusion"
        )

        if fusion is not None:
            fusion = str(fusion)

        # ----------------------------------------------------
        # Complete OCR JSON
        # ----------------------------------------------------

        raw_json = json.dumps(
            ocr_result,
            ensure_ascii=False,
            default=str,
        )

        # ----------------------------------------------------
        # Insert / update
        # ----------------------------------------------------

        sql = """
            INSERT INTO documents (
                job_id,
                doc_id,
                filename,
                input_file,
                ocr_provider,
                fusion,
                page_count,
                raw_json
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            ON DUPLICATE KEY UPDATE
                doc_id = VALUES(doc_id),
                filename = VALUES(filename),
                input_file = VALUES(input_file),
                ocr_provider = VALUES(ocr_provider),
                fusion = VALUES(fusion),
                page_count = VALUES(page_count),
                raw_json = VALUES(raw_json)
        """

        values = (
            job_id,
            str(pdf_id)
            if pdf_id is not None
            else None,
            filename,
            input_file,
            ocr_provider,
            fusion,
            page_count,
            raw_json,
        )

        cursor.execute(
            sql,
            values,
        )

        connection.commit()

        # ----------------------------------------------------
        # Database document ID
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM documents
            WHERE job_id = %s
            """,
            (job_id,),
        )

        row = cursor.fetchone()

        document_id = (
            row[0]
            if row
            else None
        )

        print()
        print("DOCUMENT SAVE SUCCESSFUL")
        print("-" * 70)
        print(
            f"Document ID    : {document_id}"
        )
        print(
            f"Job ID         : {job_id}"
        )
        print(
            f"Page Count     : {page_count}"
        )
        print("=" * 70)
        print()

        return {
            "success": True,
            "document_id": document_id,
            "job_id": job_id,
            "message": (
                "Document automatically saved to MySQL."
            ),
        }

    except Error as exc:

        if connection:
            connection.rollback()

        print()
        print("DOCUMENT SAVE FAILED")
        print(str(exc))
        print()

        raise

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# SAVE INVOICE TO MYSQL
# ============================================================

def save_invoices_to_database(
    job_id: str,
    invoice_data_list: List[Dict[str, Any]],
):
    """
    Save ALL invoices belonging to one OCR job.

    The invoices table uses (job_id, invoice_index) as the stable
    identity of each invoice. Existing rows are UPDATED in place and
    new invoice indexes are INSERTED. This prevents duplicate rows and
    avoids consuming AUTO_INCREMENT IDs when the same document is saved
    again.
    """

    if not invoice_data_list:
        raise ValueError("No invoice records were found.")

    connection = None
    cursor = None

    try:
        connection = connect_to_mysql()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id
            FROM documents
            WHERE job_id = %s
            LIMIT 1
            """,
            (job_id,),
        )

        document = cursor.fetchone()

        if not document:
            raise ValueError(
                f"No document found for job_id: {job_id}"
            )

        saved_invoices = []

        for index, invoice_data in enumerate(
            invoice_data_list,
            start=1,
        ):
            values = {
                "invoice_number": normalize_invoice_value(
                    invoice_data.get("invoice_number")
                ),
                "invoice_date": normalize_invoice_value(
                    invoice_data.get("invoice_date")
                ),
                "customer": normalize_invoice_value(
                    invoice_data.get("customer")
                ),
                "address": normalize_invoice_value(
                    invoice_data.get("address")
                ),
                "phone": normalize_invoice_value(
                    invoice_data.get("phone")
                ),
                "email": normalize_invoice_value(
                    invoice_data.get("email")
                ),
                "total": normalize_invoice_value(
                    invoice_data.get("total")
                ),
            }

            # ----------------------------------------------------
            # Check first. UPDATE existing rows instead of issuing
            # a duplicate INSERT. This keeps AUTO_INCREMENT clean.
            # ----------------------------------------------------
            cursor.execute(
                """
                SELECT id
                FROM invoices
                WHERE job_id = %s
                  AND invoice_index = %s
                LIMIT 1
                """,
                (job_id, index),
            )

            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    """
                    UPDATE invoices
                    SET invoice_number = %s,
                        invoice_date = %s,
                        customer = %s,
                        address = %s,
                        phone = %s,
                        email = %s,
                        total = %s
                    WHERE id = %s
                    """,
                    (
                        values["invoice_number"],
                        values["invoice_date"],
                        values["customer"],
                        values["address"],
                        values["phone"],
                        values["email"],
                        values["total"],
                        existing[0],
                    ),
                )
                invoice_id = existing[0]
            else:
                cursor.execute(
                    """
                    INSERT INTO invoices (
                        job_id,
                        invoice_index,
                        invoice_number,
                        invoice_date,
                        customer,
                        address,
                        phone,
                        email,
                        total
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        job_id,
                        index,
                        values["invoice_number"],
                        values["invoice_date"],
                        values["customer"],
                        values["address"],
                        values["phone"],
                        values["email"],
                        values["total"],
                    ),
                )
                invoice_id = cursor.lastrowid

            saved_invoices.append(
                {
                    "id": invoice_id,
                    "invoice_index": index,
                    **values,
                }
            )

        # Remove stale rows if the user re-saves a document after the
        # number of detected invoices has decreased.
        cursor.execute(
            """
            DELETE FROM invoices
            WHERE job_id = %s
              AND invoice_index > %s
            """,
            (job_id, len(invoice_data_list)),
        )

        connection.commit()

        print()
        print("INVOICE SAVE SUCCESSFUL")
        print("-" * 70)
        print(f"Job ID       : {job_id}")
        print(f"Invoice count: {len(saved_invoices)}")
        for invoice in saved_invoices:
            print(
                f"  #{invoice['invoice_index']} "
                f"ID={invoice['id']} "
                f"Number={invoice['invoice_number']}"
            )
        print("=" * 70)
        print()

        return {
            "success": True,
            "job_id": job_id,
            "saved_count": len(saved_invoices),
            "invoices": saved_invoices,
            "message": (
                f"{len(saved_invoices)} invoice(s) saved successfully."
            ),
        }

    except Error:
        if connection:
            connection.rollback()
        raise

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def save_invoice_to_database(
    job_id: str,
    invoice_data: Dict[str, Any],
):
    """Backward-compatible single-invoice wrapper."""

    return save_invoices_to_database(
        job_id=job_id,
        invoice_data_list=[invoice_data],
    )


# ============================================================
# AUTOMATIC INVOICE PROCESSING
# ============================================================

def process_invoice_from_structured_json(
    job_id: str,
):
    """
    Detect ALL invoices in the structured OCR JSON.

    IMPORTANT: this function ONLY detects and returns invoice data.
    It does NOT write to MySQL. Database saving happens only when the
    user clicks "Save Invoice" in Results.jsx.
    """

    structured_json_path = find_structured_ocr_json(job_id)

    if not structured_json_path:
        return {
            "success": True,
            "is_invoice": False,
            "saved": False,
            "invoice_count": 0,
            "invoices": [],
            "reason": "Structured OCR JSON not found.",
        }

    try:
        with open(
            structured_json_path,
            "r",
            encoding="utf-8",
        ) as file:
            structured_json = json.load(file)
    except Exception as exc:
        return {
            "success": False,
            "is_invoice": False,
            "saved": False,
            "invoice_count": 0,
            "invoices": [],
            "reason": f"Could not read structured JSON: {exc}",
        }

    if not isinstance(structured_json, dict):
        return {
            "success": True,
            "is_invoice": False,
            "saved": False,
            "invoice_count": 0,
            "invoices": [],
            "reason": "Structured JSON is not an object.",
        }

    invoices = extract_invoice_documents(structured_json)

    if not invoices:
        return {
            "success": True,
            "is_invoice": False,
            "saved": False,
            "invoice_count": 0,
            "invoices": [],
            "structured_json": str(structured_json_path),
            "reason": 'No exact document type "invoice" found.',
        }

    return {
        "success": True,
        "is_invoice": True,
        "saved": False,
        "invoice_count": len(invoices),
        "invoices": invoices,
        "structured_json": str(structured_json_path),
        "message": (
            f"Detected {len(invoices)} invoice(s). "
            "Nothing was written to MySQL yet."
        ),
    }


# ============================================================
# SAVE OCR TEXT TO SEARCH INDEX
# ============================================================

def save_search_index_to_database(
    job_id: str,
    ocr_result: Dict[str, Any],
):
    """
    Automatically saves OCR text blocks into search_index.
    """

    connection = None
    cursor = None

    try:

        print()
        print("=" * 70)
        print("SAVING OCR TEXT TO SEARCH INDEX")
        print("=" * 70)

        connection = connect_to_mysql()
        cursor = connection.cursor()

        print(
            f"MySQL database : {MYSQL_DATABASE}"
        )

        print(
            f"Job ID         : {job_id}"
        )

        cursor.execute(
            """
            SELECT id, filename
            FROM documents
            WHERE job_id = %s
            """,
            (job_id,),
        )

        document = cursor.fetchone()

        if not document:

            raise ValueError(
                f"No document found for job_id: {job_id}"
            )

        document_id = document[0]
        filename = document[1]

        print(
            f"Document ID    : {document_id}"
        )

        print(
            f"Filename       : {filename}"
        )

        # ----------------------------------------------------
        # Remove old index
        # ----------------------------------------------------

        cursor.execute(
            """
            DELETE FROM search_index
            WHERE document_id = %s
            """,
            (document_id,),
        )

        rows = []

        pages = ocr_result.get(
            "pages",
            [],
        )

        if isinstance(pages, list):

            for page in pages:

                if not isinstance(
                    page,
                    dict,
                ):
                    continue

                page_number = page.get(
                    "page_number"
                )

                final_result = page.get(
                    "final_result",
                    {},
                )

                if not isinstance(
                    final_result,
                    dict,
                ):
                    continue

                results = final_result.get(
                    "results",
                    [],
                )

                if not isinstance(
                    results,
                    list,
                ):
                    continue

                for block_number, block in enumerate(
                    results
                ):

                    text_content = ""

                    if isinstance(
                        block,
                        dict,
                    ):

                        for key in (
                            "text",
                            "content",
                            "html",
                            "value",
                        ):

                            value = block.get(
                                key
                            )

                            if value is not None:

                                text_content = str(
                                    value
                                )

                                break

                    elif isinstance(
                        block,
                        str,
                    ):

                        text_content = block

                    text_content = re.sub(
                        r"<[^>]*>",
                        " ",
                        text_content,
                    )

                    text_content = re.sub(
                        r"\s+",
                        " ",
                        text_content,
                    ).strip()

                    if not text_content:
                        continue

                    rows.append(
                        (
                            document_id,
                            job_id,
                            filename,
                            page_number,
                            block_number,
                            text_content,
                        )
                    )

        if rows:

            insert_sql = """
                INSERT INTO search_index (
                    document_id,
                    job_id,
                    filename,
                    page_number,
                    block_number,
                    text_content
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
            """

            cursor.executemany(
                insert_sql,
                rows,
            )

        connection.commit()

        indexed_count = len(rows)

        print()
        print(
            "SEARCH INDEX SAVE SUCCESSFUL"
        )
        print("-" * 70)
        print(
            f"Document ID    : {document_id}"
        )
        print(
            f"Job ID         : {job_id}"
        )
        print(
            f"Blocks indexed : {indexed_count}"
        )
        print("=" * 70)
        print()

        return {
            "success": True,
            "document_id": document_id,
            "job_id": job_id,
            "indexed_count": indexed_count,
            "message": (
                f"{indexed_count} OCR blocks "
                "indexed successfully."
            ),
        }

    except Exception as exc:

        if connection:
            connection.rollback()

        print()
        print("=" * 70)
        print(
            "SEARCH INDEX SAVE FAILED"
        )
        print("=" * 70)
        print(str(exc))
        print("=" * 70)
        print()

        raise

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# SAVE DATA ENTRY TO MYSQL
# ============================================================

def save_data_entries_to_database(
    job_id: str,
    entries: list,
):
    """
    Saves Data Entry records.
    """

    connection = None
    cursor = None

    try:

        print()
        print("=" * 70)
        print(
            "SAVING DATA ENTRY RECORDS TO MYSQL"
        )
        print("=" * 70)

        connection = connect_to_mysql()
        cursor = connection.cursor()

        print(
            f"MySQL database : {MYSQL_DATABASE}"
        )

        print(
            f"Job ID         : {job_id}"
        )

        cursor.execute(
            """
            SELECT id, filename
            FROM documents
            WHERE job_id = %s
            """,
            (job_id,),
        )

        document = cursor.fetchone()

        if not document:

            raise ValueError(
                f"No document found for job_id: {job_id}"
            )

        document_id = document[0]
        filename = document[1]

        print(
            f"Document ID    : {document_id}"
        )

        print(
            f"Filename       : {filename}"
        )

        # ----------------------------------------------------
        # Delete old entries
        # ----------------------------------------------------

        cursor.execute(
            """
            DELETE FROM data_entry
            WHERE document_id = %s
            """,
            (document_id,),
        )

        rows = []

        if isinstance(
            entries,
            list,
        ):

            for entry in entries:

                if not isinstance(
                    entry,
                    dict,
                ):
                    continue

                field_name = str(
                    entry.get(
                        "name",
                        "",
                    )
                ).strip()

                field_value = str(
                    entry.get(
                        "value",
                        "",
                    )
                ).strip()

                if not field_name:
                    continue

                rows.append(
                    (
                        document_id,
                        job_id,
                        field_name,
                        field_value,
                        None,
                    )
                )

        if rows:

            insert_sql = """
                INSERT INTO data_entry (
                    document_id,
                    job_id,
                    field_name,
                    field_value,
                    page_number
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
            """

            cursor.executemany(
                insert_sql,
                rows,
            )

        connection.commit()

        saved_count = len(rows)

        print()
        print(
            "DATA ENTRY SAVE SUCCESSFUL"
        )
        print("-" * 70)
        print(
            f"Document ID    : {document_id}"
        )
        print(
            f"Job ID         : {job_id}"
        )
        print(
            f"Records saved  : {saved_count}"
        )
        print("=" * 70)
        print()

        return {
            "success": True,
            "document_id": document_id,
            "job_id": job_id,
            "saved_count": saved_count,
            "message": (
                f"{saved_count} data entries "
                "saved successfully."
            ),
        }

    except Exception as exc:

        if connection:
            connection.rollback()

        print()
        print("=" * 70)
        print(
            "DATA ENTRY SAVE FAILED"
        )
        print("=" * 70)
        print(str(exc))
        print("=" * 70)
        print()

        raise

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# JOB UPDATE
# ============================================================

def update_job(
    job_id: str,
    **kwargs,
):
    if job_id not in jobs:
        jobs[job_id] = {}

    jobs[job_id].update(
        kwargs
    )

    jobs[job_id]["updated_at"] = time.time()


# ============================================================
# OCR WORKER
# ============================================================

def start_ocr_process(
    job_id: str,
    input_pdf: Path,
    output_dir: Path,
):
    """
    Runs the existing OCR pipeline.
    """

    try:

        update_job(
            job_id,
            status="processing",
            progress=5,
            message="Starting OCR process...",
        )

        monitor_ocr_process(
            job_id=job_id,
            input_pdf=input_pdf,
            output_dir=output_dir,
        )

    except Exception as exc:

        print()
        print("=" * 70)
        print(
            "OCR WORKER FAILED"
        )
        print("=" * 70)
        print(str(exc))
        traceback.print_exc()
        print("=" * 70)
        print()

        update_job(
            job_id,
            status="failed",
            progress=0,
            message=str(exc),
            error=str(exc),
        )


# ============================================================
# OCR PROCESS MONITOR
# ============================================================

def monitor_ocr_process(
    job_id: str,
    input_pdf: Path,
    output_dir: Path,
):
    """
    Existing end-to-end OCR execution.

    The OCR pipeline itself is unchanged.
    """

    try:

        from services.pdf_ocr_service import PDFOCRService

        filename = input_pdf.name

        # ----------------------------------------------------
        # Start
        # ----------------------------------------------------

        update_job(
            job_id,
            progress=10,
            message="Processing PDF...",
        )

        # ----------------------------------------------------
        # OCR service
        # ----------------------------------------------------

        service = PDFOCRService(
            output_dir=str(
                output_dir
            ),
            quality_threshold=80,
        )

        update_job(
            job_id,
            progress=20,
            message="Running OCR...",
        )

        result = service.process_pdf(
            str(input_pdf)
        )

        update_job(
            job_id,
            progress=85,
            message="OCR processing completed.",
        )

        # ----------------------------------------------------
        # Save OCR JSON automatically
        # ----------------------------------------------------

        update_job(
            job_id,
            progress=95,
            message=(
                "OCR completed. "
                "Saving JSON to MySQL..."
            ),
        )

        database_result = save_document_to_database(
            job_id=job_id,
            filename=filename,
            input_file=str(
                input_pdf
            ),
            ocr_result=result,
        )

        result["database"] = (
            database_result
        )

        # ----------------------------------------------------
        # Build Search Index
        # ----------------------------------------------------

        update_job(
            job_id,
            progress=97,
            message=(
                "OCR JSON saved. "
                "Building search index..."
            ),
        )

        search_index_result = (
            save_search_index_to_database(
                job_id=job_id,
                ocr_result=result,
            )
        )

        result["search_index"] = (
            search_index_result
        )

        # ----------------------------------------------------
        # Verify output files
        # ----------------------------------------------------

        outputs = result.get(
            "outputs",
            {},
        )

        output_urls = {}

        for key, value in outputs.items():

            if value:

                output_path = Path(
                    str(value)
                )

                if output_path.exists():

                    output_urls[key] = str(
                        output_path
                    )

        # ----------------------------------------------------
        # Fifth output: Structured OCR JSON
        #
        # Find it separately because some versions of the
        # OCR service do not put it into outputs correctly.
        # ----------------------------------------------------

        structured_json_path = (
            find_structured_ocr_json(
                job_id
            )
        )

        if structured_json_path:

            # Make sure result outputs contains it.
            result.setdefault(
                "outputs",
                {},
            )

            result["outputs"][
                "structured_ocr_json"
            ] = str(
                structured_json_path
            )

            output_urls[
                "structured_ocr_json"
            ] = str(
                structured_json_path
            )

        # ----------------------------------------------------
        # Temporarily store result/output information so the
        # invoice processor can locate the structured JSON.
        # ----------------------------------------------------

        update_job(
            job_id,
            result=result,
            output_files=output_urls,
        )

        # ----------------------------------------------------
        # AUTOMATIC INVOICE DETECTION
        #
        # This does NOT affect non-invoice documents.
        # ----------------------------------------------------

        update_job(
            job_id,
            progress=98,
            message=(
                "Checking structured document type..."
            ),
        )

        try:

            invoice_result = (
                process_invoice_from_structured_json(
                    job_id
                )
            )

            result["invoice"] = (
                invoice_result
            )

        except Exception as invoice_exc:

            # Invoice processing should not destroy an otherwise
            # successful OCR job.
            #
            # The OCR result remains available.
            print()
            print("=" * 70)
            print(
                "INVOICE PROCESSING WARNING"
            )
            print("=" * 70)
            print(str(invoice_exc))
            traceback.print_exc()
            print("=" * 70)
            print()

            result["invoice"] = {
                "success": False,
                "is_invoice": False,
                "saved": False,
                "error": str(
                    invoice_exc
                ),
            }

        # ----------------------------------------------------
        # Complete
        # ----------------------------------------------------

        update_job(
            job_id,
            status="completed",
            progress=100,
            message="OCR completed successfully.",
            result=result,
            output_files=output_urls,
        )

        print()
        print("=" * 70)
        print(
            "OCR JOB COMPLETED"
        )
        print("=" * 70)
        print(
            f"Job ID         : {job_id}"
        )
        print(
            f"Filename       : {filename}"
        )
        print("=" * 70)
        print()

    except Exception as exc:

        print()
        print("=" * 70)
        print(
            "OCR PROCESS FAILED"
        )
        print("=" * 70)
        print(str(exc))
        traceback.print_exc()
        print("=" * 70)
        print()

        update_job(
            job_id,
            status="failed",
            progress=0,
            message=str(exc),
            error=str(exc),
        )


# ============================================================
# PROCESS PDF
# ============================================================

@app.post("/api/process")
async def process_pdf(
    file: UploadFile = File(...),
):
    try:

        if not file.filename:

            raise HTTPException(
                status_code=400,
                detail="No filename provided.",
            )

        job_id = str(
            uuid.uuid4()
        )

        safe_filename = Path(
            file.filename
        ).name

        input_path = (
            UPLOAD_DIR /
            f"{job_id}_{safe_filename}"
        )

        job_output_dir = (
            API_JOBS_DIR /
            job_id
        )

        job_output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ----------------------------------------------------
        # Save upload
        # ----------------------------------------------------

        with open(
            input_path,
            "wb",
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )

        # ----------------------------------------------------
        # Initialize job
        # ----------------------------------------------------

        jobs[job_id] = {
            "job_id": job_id,
            "filename": safe_filename,
            "status": "queued",
            "progress": 0,
            "message": "Job queued.",
            "input_file": str(
                input_path
            ),
            "output_dir": str(
                job_output_dir
            ),
            "created_at": time.time(),
            "updated_at": time.time(),
        }

        # ----------------------------------------------------
        # Start worker
        # ----------------------------------------------------

        thread = threading.Thread(
            target=start_ocr_process,
            args=(
                job_id,
                input_path,
                job_output_dir,
            ),
            daemon=True,
        )

        thread.start()

        return {
            "success": True,
            "job_id": job_id,
            "filename": safe_filename,
            "message": (
                "OCR processing started."
            ),
        }

    except HTTPException:
        raise

    except Exception as exc:

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# STATUS
# ============================================================

@app.get("/api/status/{job_id}")
def get_status(
    job_id: str,
):

    job = jobs.get(
        job_id
    )

    if not job:

        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    return job


# ============================================================
# RESULT
# ============================================================

@app.get("/api/result/{job_id}")
def get_result(
    job_id: str,
):

    job = jobs.get(
        job_id
    )

    if not job:

        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    return {
        "success": True,
        "job_id": job_id,
        "status": job.get(
            "status"
        ),
        "result": job.get(
            "result"
        ),
    }


# ============================================================
# STRUCTURED OCR JSON API
# ============================================================

@app.get("/api/structured-ocr/{job_id}")
def get_structured_ocr_json(
    job_id: str,
):
    """
    Return the fifth structured OCR JSON.

    This is separate from the original OCR JSON.
    """

    job = jobs.get(
        job_id
    )

    if not job:

        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    structured_json_path = (
        find_structured_ocr_json(
            job_id
        )
    )

    if not structured_json_path:

        raise HTTPException(
            status_code=404,
            detail=(
                "Structured OCR JSON output "
                "not found."
            ),
        )

    try:

        with open(
            structured_json_path,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(
                file
            )

        return {
            "success": True,
            "job_id": job_id,
            "filename": (
                structured_json_path.name
            ),
            "data": data,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not read structured OCR JSON: "
                f"{str(exc)}"
            ),
        )


# ============================================================
# SEARCH INDEX
# ============================================================

@app.get("/api/search/{job_id}")
def search_document(
    job_id: str,
    q: str,
):

    connection = None
    cursor = None

    try:

        query = str(
            q or ""
        ).strip()

        if not query:

            return {
                "success": True,
                "job_id": job_id,
                "query": "",
                "results": [],
                "total": 0,
            }

        connection = connect_to_mysql()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                s.page_number,
                s.block_number,
                s.text_content,
                d.raw_json,
                d.filename
            FROM search_index AS s
            INNER JOIN documents AS d
                ON d.id = s.document_id
            WHERE s.job_id = %s
              AND s.text_content LIKE %s
            ORDER BY
                s.page_number ASC,
                s.block_number ASC
            """,
            (
                job_id,
                f"%{query}%",
            ),
        )

        rows = cursor.fetchall()

        results = []

        for row in rows:

            page_number = (
                int(
                    row["page_number"]
                )
                if row["page_number"] is not None
                else 1
            )

            block_number = (
                int(
                    row["block_number"]
                )
                if row["block_number"] is not None
                else 0
            )

            text_content = str(
                row["text_content"] or ""
            )

            ocr_block = None
            page_details = {}

            try:

                raw_json = row.get(
                    "raw_json"
                )

                parsed_json = (
                    json.loads(raw_json)
                    if isinstance(
                        raw_json,
                        str,
                    )
                    else raw_json
                )

                pages = (
                    parsed_json.get(
                        "pages",
                        [],
                    )
                    if isinstance(
                        parsed_json,
                        dict,
                    )
                    else []
                )

                page_obj = None

                if isinstance(
                    pages,
                    list,
                ):

                    for candidate in pages:

                        if not isinstance(
                            candidate,
                            dict,
                        ):
                            continue

                        if int(
                            candidate.get(
                                "page_number",
                                0,
                            )
                            or 0
                        ) == page_number:

                            page_obj = candidate
                            break

                    if (
                        page_obj is None
                        and 1 <= page_number <= len(
                            pages
                        )
                    ):

                        candidate = pages[
                            page_number - 1
                        ]

                        if isinstance(
                            candidate,
                            dict,
                        ):

                            page_obj = candidate

                elif isinstance(
                    pages,
                    dict,
                ):

                    page_obj = pages.get(
                        str(page_number)
                    )

                if isinstance(
                    page_obj,
                    dict,
                ):

                    final_result = page_obj.get(
                        "final_result",
                        {},
                    )

                    if isinstance(
                        final_result,
                        dict,
                    ):

                        final_results = (
                            final_result.get(
                                "results",
                                [],
                            )
                        )

                        if (
                            isinstance(
                                final_results,
                                list,
                            )
                            and 0 <= block_number < len(
                                final_results
                            )
                        ):

                            candidate_block = (
                                final_results[
                                    block_number
                                ]
                            )

                            if isinstance(
                                candidate_block,
                                dict,
                            ):

                                ocr_block = (
                                    candidate_block
                                )

                            else:

                                ocr_block = {
                                    "text": str(
                                        candidate_block
                                    )
                                }

                    page_details = {
                        "page_number": page_number,
                        "final_level": page_obj.get(
                            "final_level"
                        ),
                        "final_source": page_obj.get(
                            "final_source"
                        ),
                        "final_quality": page_obj.get(
                            "final_quality"
                        ),
                        "detected_languages": page_obj.get(
                            "detected_languages"
                        ),
                    }

            except Exception:

                ocr_block = None

            results.append(
                {
                    "page": page_number,
                    "blockIndex": block_number,
                    "text": text_content,
                    "type": (
                        ocr_block.get(
                            "label"
                        )
                        if isinstance(
                            ocr_block,
                            dict,
                        )
                        and ocr_block.get(
                            "label"
                        )
                        else "Text Block"
                    ),
                    "filename": row.get(
                        "filename"
                    ),
                    "json_details": {
                        "query": query,
                        "matched_text": text_content,
                        "page_number": page_number,
                        "block_number": block_number,
                        "ocr_block": ocr_block,
                        "page": page_details,
                    },
                }
            )

        return {
            "success": True,
            "job_id": job_id,
            "query": query,
            "results": results,
            "total": len(
                results
            ),
        }

    except Error as exc:

        if connection:
            connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                f"MySQL search error: "
                f"{str(exc)}"
            ),
        )

    except Exception as exc:

        if connection:
            connection.rollback()

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=(
                f"Search failed: "
                f"{str(exc)}"
            ),
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# SEARCH HIGHLIGHTED PDF
# ============================================================

@app.get("/api/search/{job_id}/pdf")
def search_highlighted_pdf(
    job_id: str,
    q: str,
):

    connection = None
    cursor = None
    pdf_document = None

    try:

        query = str(
            q or ""
        ).strip()

        if not query:

            raise HTTPException(
                status_code=400,
                detail="Search query is required.",
            )

        connection = connect_to_mysql()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                d.raw_json,
                d.filename
            FROM documents AS d
            WHERE d.job_id = %s
            LIMIT 1
            """,
            (job_id,),
        )

        document = cursor.fetchone()

        if not document:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Document not found for this OCR job."
                ),
            )

        raw_json = document.get(
            "raw_json"
        )

        try:

            parsed_json = (
                json.loads(raw_json)
                if isinstance(
                    raw_json,
                    str,
                )
                else raw_json
            )

        except Exception as exc:

            raise HTTPException(
                status_code=500,
                detail=(
                    f"Could not read stored OCR JSON: "
                    f"{str(exc)}"
                ),
            )

        outputs = (
            parsed_json.get(
                "outputs",
                {},
            )
            if isinstance(
                parsed_json,
                dict,
            )
            else {}
        )

        structured_pdf = (
            outputs.get(
                "structured_pdf"
            )
            if isinstance(
                outputs,
                dict,
            )
            else None
        )

        if not structured_pdf:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Structured PDF output "
                    "is not available."
                ),
            )

        pdf_path = Path(
            str(structured_pdf)
        )

        if not pdf_path.is_absolute():
            pdf_path = (
                BASE_DIR /
                pdf_path
            )

        if not pdf_path.exists():

            raise HTTPException(
                status_code=404,
                detail=(
                    "Structured PDF file "
                    "does not exist."
                ),
            )

        cursor.execute(
            """
            SELECT
                page_number,
                block_number
            FROM search_index
            WHERE job_id = %s
              AND text_content LIKE %s
            ORDER BY
                page_number ASC,
                block_number ASC
            """,
            (
                job_id,
                f"%{query}%",
            ),
        )

        matching_rows = (
            cursor.fetchall()
        )

        block_lookup = {}

        for row in matching_rows:

            page_number = (
                int(
                    row["page_number"]
                )
                if row["page_number"] is not None
                else 1
            )

            block_number = (
                int(
                    row["block_number"]
                )
                if row["block_number"] is not None
                else 0
            )

            block_lookup.setdefault(
                page_number,
                [],
            ).append(
                block_number
            )

        pdf_document = fitz.open(
            str(pdf_path)
        )

        total_highlights = 0

        # ----------------------------------------------------
        # Exact text highlighting
        # ----------------------------------------------------

        for page in pdf_document:

            try:

                hits = page.search_for(
                    query,
                    quads=False,
                )

            except TypeError:

                hits = page.search_for(
                    query
                )

            for rect in hits:

                annot = (
                    page.add_highlight_annot(
                        rect
                    )
                )

                if annot:

                    annot.update()

                    total_highlights += 1

        # ----------------------------------------------------
        # OCR block fallback
        # ----------------------------------------------------

        if (
            total_highlights == 0
            and block_lookup
        ):

            try:

                parsed_pages = (
                    parsed_json.get(
                        "pages",
                        [],
                    )
                    if isinstance(
                        parsed_json,
                        dict,
                    )
                    else []
                )

                for page_number, block_numbers in (
                    block_lookup.items()
                ):

                    page_index = (
                        page_number - 1
                    )

                    if not (
                        0 <= page_index < len(
                            pdf_document
                        )
                    ):
                        continue

                    page_obj = None

                    if isinstance(
                        parsed_pages,
                        list,
                    ):

                        if page_index < len(
                            parsed_pages
                        ):

                            candidate = (
                                parsed_pages[
                                    page_index
                                ]
                            )

                            if isinstance(
                                candidate,
                                dict,
                            ):

                                page_obj = (
                                    candidate
                                )

                    elif isinstance(
                        parsed_pages,
                        dict,
                    ):

                        candidate = (
                            parsed_pages.get(
                                str(page_number)
                            )
                        )

                        if isinstance(
                            candidate,
                            dict,
                        ):

                            page_obj = candidate

                    if not isinstance(
                        page_obj,
                        dict,
                    ):
                        continue

                    final_result = (
                        page_obj.get(
                            "final_result",
                            {},
                        )
                    )

                    if not isinstance(
                        final_result,
                        dict,
                    ):
                        continue

                    final_results = (
                        final_result.get(
                            "results",
                            [],
                        )
                    )

                    if not isinstance(
                        final_results,
                        list,
                    ):
                        continue

                    pdf_page = (
                        pdf_document[
                            page_index
                        ]
                    )

                    for block_number in (
                        block_numbers
                    ):

                        if not (
                            0 <= block_number < len(
                                final_results
                            )
                        ):
                            continue

                        block = (
                            final_results[
                                block_number
                            ]
                        )

                        if not isinstance(
                            block,
                            dict,
                        ):
                            continue

                        geometry = (
                            block.get(
                                "polygon"
                            )
                            or block.get(
                                "bbox"
                            )
                            or block.get(
                                "box"
                            )
                        )

                        if not geometry:
                            continue

                        points = []

                        if (
                            isinstance(
                                geometry,
                                list,
                            )
                            and geometry
                            and isinstance(
                                geometry[0],
                                (list, tuple),
                            )
                        ):

                            for point in geometry:

                                if len(
                                    point
                                ) >= 2:

                                    points.append(
                                        (
                                            float(
                                                point[0]
                                            ),
                                            float(
                                                point[1]
                                            ),
                                        )
                                    )

                        elif (
                            isinstance(
                                geometry,
                                (list, tuple),
                            )
                            and len(
                                geometry
                            ) >= 4
                        ):

                            x1, y1, x2, y2 = (
                                geometry[
                                    :4
                                ]
                            )

                            points = [
                                (
                                    float(x1),
                                    float(y1),
                                ),
                                (
                                    float(x2),
                                    float(y2),
                                ),
                            ]

                        if len(
                            points
                        ) < 2:
                            continue

                        x_values = [
                            point[0]
                            for point in points
                        ]

                        y_values = [
                            point[1]
                            for point in points
                        ]

                        rect = fitz.Rect(
                            min(x_values),
                            min(y_values),
                            max(x_values),
                            max(y_values),
                        )

                        rect &= pdf_page.rect

                        if (
                            rect.width > 0
                            and rect.height > 0
                        ):

                            annot = (
                                pdf_page.add_highlight_annot(
                                    rect
                                )
                            )

                            if annot:

                                annot.update()

                                total_highlights += 1

            except Exception:
                pass

        search_dir = (
            API_JOBS_DIR /
            job_id /
            "search"
        )

        search_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        safe_query = re.sub(
            r"[^A-Za-z0-9_-]+",
            "_",
            query,
        ).strip("_") or "query"

        output_path = (
            search_dir /
            f"highlighted_{safe_query}.pdf"
        )

        pdf_document.save(
            str(output_path),
            garbage=4,
            deflate=True,
        )

        pdf_document.close()
        pdf_document = None

        return FileResponse(
            path=str(
                output_path
            ),
            media_type="application/pdf",
            filename=output_path.name,
            headers={
                "Content-Disposition": (
                    f'inline; filename="{output_path.name}"'
                )
            },
        )

    except HTTPException:
        raise

    except Exception as exc:

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=(
                f"PDF highlighting failed: "
                f"{str(exc)}"
            ),
        )

    finally:

        if pdf_document is not None:
            pdf_document.close()

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# CHATBOT - STRUCTURED PDF RESOLVER
# ============================================================

def resolve_chat_structured_pdf(
    job_id: str,
) -> Optional[Path]:

    job = jobs.get(
        job_id
    )

    if job:

        result = job.get(
            "result"
        )

        if isinstance(
            result,
            dict,
        ):

            outputs = result.get(
                "outputs",
                {},
            )

            if isinstance(
                outputs,
                dict,
            ):

                structured_pdf = (
                    outputs.get(
                        "structured_pdf"
                    )
                )

                if structured_pdf:

                    path = Path(
                        str(
                            structured_pdf
                        )
                    )

                    if not path.is_absolute():
                        path = (
                            BASE_DIR /
                            path
                        )

                    if path.exists():
                        return path

        output_files = job.get(
            "output_files",
            {},
        )

        if isinstance(
            output_files,
            dict,
        ):

            structured_pdf = (
                output_files.get(
                    "structured_pdf"
                )
            )

            if structured_pdf:

                path = Path(
                    str(
                        structured_pdf
                    )
                )

                if not path.is_absolute():
                    path = (
                        BASE_DIR /
                        path
                    )

                if path.exists():
                    return path

    job_output_dir = (
        API_JOBS_DIR /
        job_id
    )

    if not job_output_dir.exists():
        return None

    pdf_candidates = list(
        job_output_dir.rglob(
            "*.pdf"
        )
    )

    if not pdf_candidates:
        return None

    for pdf in pdf_candidates:

        if (
            "structured"
            in pdf.name.lower()
        ):

            return pdf

    return None


# ============================================================
# CHATBOT - LOAD STRUCTURED PDF
# ============================================================

def load_chat_document(
    job_id: str,
) -> Dict[str, Any]:

    if job_id in chat_document_cache:

        return chat_document_cache[
            job_id
        ]

    job = jobs.get(
        job_id
    )

    if not job:

        raise FileNotFoundError(
            "OCR job was not found."
        )

    if job.get(
        "status"
    ) != "completed":

        raise ValueError(
            "The OCR document is not ready yet. "
            "Please wait until processing is completed."
        )

    pdf_path = (
        resolve_chat_structured_pdf(
            job_id
        )
    )

    if not pdf_path:

        raise FileNotFoundError(
            "The structured PDF generated by the OCR pipeline "
            "could not be found."
        )

    print()
    print("=" * 70)
    print(
        "CHATBOT DOCUMENT LOADING"
    )
    print("=" * 70)
    print()

    print(
        f"Job ID         : {job_id}"
    )

    print(
        f"Structured PDF : {pdf_path}"
    )

    print()

    document_data = extract_pdf_text(
        str(
            pdf_path
        )
    )

    if not document_data.get(
        "has_text"
    ):

        raise ValueError(
            "The generated structured PDF does not contain "
            "usable selectable text."
        )

    document_data[
        "job_id"
    ] = job_id

    document_data[
        "structured_pdf"
    ] = str(
        pdf_path
    )

    chat_document_cache[
        job_id
    ] = document_data

    print()
    print("=" * 70)
    print(
        "CHATBOT DOCUMENT LOADED"
    )
    print("=" * 70)
    print()

    print(
        f"Document       : "
        f"{document_data.get('filename')}"
    )

    print(
        f"Pages          : "
        f"{document_data.get('total_pages')}"
    )

    print(
        f"Characters     : "
        f"{document_data.get('total_characters'):,}"
    )

    print(
        f"Source         : "
        f"{document_data.get('source')}"
    )

    print()

    return document_data


# ============================================================
# CHATBOT - DIRECT STRUCTURED PDF UPLOAD
# ============================================================

@app.post("/api/chat/upload")
async def upload_chat_document(
    file: UploadFile = File(...),
):

    chat_directory = None

    try:

        if not file.filename:

            raise HTTPException(
                status_code=400,
                detail="No filename provided.",
            )

        safe_filename = Path(
            file.filename
        ).name

        if (
            not safe_filename.lower().endswith(
                ".pdf"
            )
            and file.content_type
            != "application/pdf"
        ):

            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported.",
            )

        chat_id = str(
            uuid.uuid4()
        )

        chat_directory = (
            CHAT_UPLOAD_DIR /
            chat_id
        )

        chat_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        pdf_path = (
            chat_directory /
            safe_filename
        )

        with open(
            pdf_path,
            "wb",
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )

        if not pdf_path.exists():

            raise HTTPException(
                status_code=500,
                detail=(
                    "Uploaded PDF could not be saved."
                ),
            )

        print()
        print("=" * 70)
        print(
            "CHATBOT PDF UPLOAD"
        )
        print("=" * 70)
        print()

        print(
            f"Chat ID        : {chat_id}"
        )

        print(
            f"Filename       : {safe_filename}"
        )

        print(
            f"PDF            : {pdf_path}"
        )

        print(
            "OCR            : NOT RUN"
        )

        print()

        document_data = extract_pdf_text(
            str(
                pdf_path
            )
        )

        if not document_data.get(
            "has_text"
        ):

            try:

                shutil.rmtree(
                    chat_directory,
                    ignore_errors=True,
                )

            except Exception:
                pass

            raise HTTPException(
                status_code=400,
                detail=(
                    "The uploaded structured PDF does not contain "
                    "usable selectable text."
                ),
            )

        document_data[
            "chat_id"
        ] = chat_id

        document_data[
            "structured_pdf"
        ] = str(
            pdf_path
        )

        document_data[
            "filename"
        ] = (
            document_data.get(
                "filename"
            )
            or safe_filename
        )

        chat_document_cache[
            chat_id
        ] = document_data

        chat_summary_cache.pop(
            chat_id,
            None,
        )

        print()
        print("=" * 70)
        print(
            "CHATBOT PDF READY"
        )
        print("=" * 70)
        print()

        print(
            f"Chat ID        : {chat_id}"
        )

        print(
            f"Document       : "
            f"{document_data.get('filename')}"
        )

        print(
            f"Pages          : "
            f"{document_data.get('total_pages')}"
        )

        print(
            f"Characters     : "
            f"{document_data.get('total_characters'):,}"
        )

        print(
            "OCR            : NOT RUN"
        )

        print(
            f"Source         : "
            f"{document_data.get('source')}"
        )

        print()

        return {
            "success": True,
            "chat_id": chat_id,
            "filename": safe_filename,
            "message": (
                "PDF uploaded successfully. "
                "The document is ready for chatbot."
            ),
            "document": {
                "filename": document_data.get(
                    "filename"
                ),
                "total_pages": document_data.get(
                    "total_pages"
                ),
                "total_characters": document_data.get(
                    "total_characters"
                ),
                "source": document_data.get(
                    "source"
                ),
                "structured_pdf": document_data.get(
                    "structured_pdf"
                ),
            },
        }

    except HTTPException:
        raise

    except Exception as exc:

        print()
        print("=" * 70)
        print(
            "CHATBOT PDF UPLOAD FAILED"
        )
        print("=" * 70)
        print()

        print(
            str(exc)
        )

        traceback.print_exc()

        print()

        if chat_directory is not None:

            try:

                shutil.rmtree(
                    chat_directory,
                    ignore_errors=True,
                )

            except Exception:
                pass

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not load uploaded PDF: "
                f"{str(exc)}"
            ),
        )


# ============================================================
# CHATBOT - GET DOCUMENT
# ============================================================

def get_chat_document(
    chat_id: str,
) -> Dict[str, Any]:

    if chat_id in chat_document_cache:

        return chat_document_cache[
            chat_id
        ]

    if chat_id in jobs:

        return load_chat_document(
            chat_id
        )

    raise FileNotFoundError(
        "Chatbot document was not found."
    )


# ============================================================
# CHATBOT - ASK QUESTION
# ============================================================

@app.post("/api/chat/{job_id}")
def chat_with_document(
    job_id: str,
    request: ChatRequest,
):

    question = str(
        request.message or ""
    ).strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    try:

        document_data = get_chat_document(
            job_id
        )

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:

        print()
        print("=" * 70)
        print(
            "CHATBOT DOCUMENT ERROR"
        )
        print("=" * 70)
        print()

        print(
            str(exc)
        )

        traceback.print_exc()

        print()

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not load chatbot document: "
                f"{str(exc)}"
            ),
        )

    try:

        client = create_groq_client()

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not create Groq client: "
                f"{str(exc)}"
            ),
        )

    history = request.history or []

    clean_history = []

    if isinstance(
        history,
        list,
    ):

        for item in history:

            if not isinstance(
                item,
                dict,
            ):
                continue

            role = item.get(
                "role"
            )

            content = item.get(
                "content"
            )

            if role not in {
                "user",
                "assistant",
            }:
                continue

            if content is None:
                continue

            content = str(
                content
            ).strip()

            if not content:
                continue

            clean_history.append(
                {
                    "role": role,
                    "content": content,
                }
            )

    first_chat_request = (
        job_id
        not in chat_summary_cache
    )

    summary = None

    if first_chat_request:

        print()
        print("=" * 70)
        print(
            "GENERATING DOCUMENT SUMMARY FOR CHATBOT"
        )
        print("=" * 70)
        print()

        print(
            f"Chat ID / Job ID : {job_id}"
        )

        print(
            f"Document         : "
            f"{document_data.get('filename')}"
        )

        print()

        try:

            summary = summarize_document(
                client=client,
                document_data=document_data,
            )

            if not summary:

                summary = (
                    "A summary could not be generated "
                    "for this document."
                )

            chat_summary_cache[
                job_id
            ] = summary

        except Exception as exc:

            print()
            print("=" * 70)
            print(
                "CHATBOT SUMMARY ERROR"
            )
            print("=" * 70)
            print()

            print(
                str(exc)
            )

            traceback.print_exc()

            print()

            raise HTTPException(
                status_code=500,
                detail=(
                    f"Document summary failed: "
                    f"{str(exc)}"
                ),
            )

    else:

        summary = chat_summary_cache.get(
            job_id
        )

    print()
    print("=" * 70)
    print(
        "DOCUMENT CHAT REQUEST"
    )
    print("=" * 70)
    print()

    print(
        f"Chat ID / Job ID : {job_id}"
    )

    print(
        f"Question         : {question}"
    )

    print()

    try:

        answer = ask_question(
            client=client,
            document_data=document_data,
            question=question,
            conversation_history=clean_history,
        )

    except Exception as exc:

        print()
        print("=" * 70)
        print(
            "GROQ CHAT ERROR"
        )
        print("=" * 70)
        print()

        print(
            str(exc)
        )

        traceback.print_exc()

        print()

        raise HTTPException(
            status_code=500,
            detail=(
                f"Chatbot error: "
                f"{str(exc)}"
            ),
        )

    return {
        "success": True,
        "job_id": job_id,
        "chat_id": job_id,
        "question": question,
        "summary": summary,
        "answer": answer,
        "document": {
            "filename": document_data.get(
                "filename"
            ),
            "total_pages": document_data.get(
                "total_pages"
            ),
            "total_characters": document_data.get(
                "total_characters"
            ),
            "source": document_data.get(
                "source"
            ),
            "structured_pdf": document_data.get(
                "structured_pdf"
            ),
        },
    }


# ============================================================
# CHATBOT - MANUAL SUMMARY ENDPOINT
# ============================================================

@app.get("/api/chat/{job_id}/summary")
def summarize_document_api(
    job_id: str,
):

    try:

        document_data = get_chat_document(
            job_id
        )

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    if job_id in jobs:

        job = jobs.get(
            job_id
        )

        if not job:

            raise HTTPException(
                status_code=404,
                detail="OCR job not found.",
            )

        if job.get(
            "status"
        ) != "completed":

            raise HTTPException(
                status_code=400,
                detail=(
                    "The OCR document is not ready yet."
                ),
            )

    if job_id in chat_summary_cache:

        return {
            "success": True,
            "job_id": job_id,
            "chat_id": job_id,
            "summary": chat_summary_cache[
                job_id
            ],
            "document": {
                "filename": document_data.get(
                    "filename"
                ),
                "total_pages": document_data.get(
                    "total_pages"
                ),
                "total_characters": document_data.get(
                    "total_characters"
                ),
            },
        }

    try:

        client = create_groq_client()

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not create Groq client: "
                f"{str(exc)}"
            ),
        )

    try:

        summary = summarize_document(
            client=client,
            document_data=document_data,
        )

        chat_summary_cache[
            job_id
        ] = summary

        return {
            "success": True,
            "job_id": job_id,
            "chat_id": job_id,
            "summary": summary,
            "document": {
                "filename": document_data.get(
                    "filename"
                ),
                "total_pages": document_data.get(
                    "total_pages"
                ),
                "total_characters": document_data.get(
                    "total_characters"
                ),
            },
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Summary generation failed: "
                f"{str(exc)}"
            ),
        )


# ============================================================
# AI FIELD EXTRACTION (GROQ) - CHATBOT ACTION BUTTONS
# ============================================================
#
# POST /api/extract/{job_id}/fields   -> Groq reads the scanned document and
#                                        returns fields + values
# GET  /api/extract/{job_id}/json     -> database-ready JSON of that result
# POST /api/extract/{job_id}/save     -> stores it in MySQL
# GET  /api/extract/latest-job        -> latest scanned document (no upload)
#
# All logic lives in document_extraction.py (keep it next to api.py).

try:
    from document_extraction import (
        create_extraction_router,
        ensure_extraction_tables,
    )
except ImportError as exc:
    raise RuntimeError(
        "Could not import document_extraction.py. "
        "Make sure document_extraction.py is located in the backend folder."
    ) from exc

app.include_router(
    create_extraction_router(
        jobs=jobs,
        jobs_dir=API_JOBS_DIR,
        connect_to_mysql=connect_to_mysql,
        get_chat_document=get_chat_document,
        resolve_structured_pdf=resolve_chat_structured_pdf,
        create_groq_client=create_groq_client,
        extract_pdf_text=extract_pdf_text,
    )
)

# CREATE TABLE IF NOT EXISTS for the extraction tables.
# (Also done again automatically on every save, so a MySQL that was
#  offline at start-up is not a problem.)
try:
    ensure_extraction_tables(connect_to_mysql)
    print("AI extraction tables are ready.")
except Exception as exc:
    print(
        "WARNING: could not prepare the AI extraction tables yet: "
        f"{exc}"
    )


# ============================================================
# DATABASE HEALTH
# ============================================================

@app.get("/api/database/health")
def database_health():

    connection = None

    try:

        connection = connect_to_mysql()

        return {
            "success": True,
            "database": MYSQL_DATABASE,
            "connected": connection.is_connected(),
        }

    except Error as exc:

        return {
            "success": False,
            "database": MYSQL_DATABASE,
            "connected": False,
            "error": str(exc),
        }

    finally:

        if connection:
            connection.close()


# ============================================================
# DATA ENTRY SAVE
# ============================================================

@app.post("/api/data-entry/save")
def save_data_entry(
    request: DataEntrySaveRequest,
):

    try:

        entries = []

        for entry in request.entries:

            if hasattr(
                entry,
                "model_dump",
            ):

                entries.append(
                    entry.model_dump()
                )

            else:

                entries.append(
                    entry.dict()
                )

        result = (
            save_data_entries_to_database(
                job_id=request.job_id,
                entries=entries,
            )
        )

        return {
            "success": True,
            "data_entry": result,
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except Error as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"MySQL error: {str(exc)}"
            ),
        )

    except Exception as exc:

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=(
                f"Data Entry save failed: "
                f"{str(exc)}"
            ),
        )


# ============================================================
# INVOICE DATABASE READ / UPDATE
# ============================================================

@app.get("/api/invoice/{job_id}")
def get_invoices_from_database(
    job_id: str,
):
    """
    Fetch invoices already stored in the invoices table.

    IMPORTANT:
    This endpoint reads the invoices table directly. It does not
    regenerate invoice data from OCR JSON and it does not use the
    documents.document_id column.
    """

    connection = None
    cursor = None

    try:
        connection = connect_to_mysql()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                job_id,
                invoice_index,
                invoice_number,
                invoice_date,
                customer,
                address,
                phone,
                email,
                total
            FROM invoices
            WHERE job_id = %s
            ORDER BY invoice_index ASC, id ASC
            """,
            (job_id,),
        )

        rows = cursor.fetchall()

        return {
            "success": True,
            "job_id": job_id,
            "invoices": rows,
            "total": len(rows),
        }

    except Error as exc:
        raise HTTPException(
            status_code=500,
            detail=f"MySQL invoice fetch error: {str(exc)}",
        )

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Invoice fetch failed: {str(exc)}",
        )

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.put("/api/invoice/{job_id}/{invoice_index}")
def update_invoice_in_database(
    job_id: str,
    invoice_index: int,
    request: InvoiceUpdateRequest,
):
    """
    Update one existing invoice in the invoices table.

    The stable identity is:
        (job_id, invoice_index)

    This intentionally does NOT reference documents.document_id.
    """

    connection = None
    cursor = None

    try:
        connection = connect_to_mysql()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                job_id,
                invoice_index,
                invoice_number,
                invoice_date,
                customer,
                address,
                phone,
                email,
                total
            FROM invoices
            WHERE job_id = %s
              AND invoice_index = %s
            LIMIT 1
            """,
            (job_id, invoice_index),
        )

        existing = cursor.fetchone()

        if not existing:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Invoice index {invoice_index} was not found "
                    f"for job_id {job_id}."
                ),
            )

        values = {
            "invoice_number": request.invoice_number,
            "invoice_date": request.invoice_date,
            "customer": request.customer,
            "address": request.address,
            "phone": request.phone,
            "email": request.email,
            "total": request.total,
        }

        for key, value in values.items():
            if isinstance(value, str):
                values[key] = value.strip() or None

        cursor.execute(
            """
            UPDATE invoices
            SET invoice_number = %s,
                invoice_date = %s,
                customer = %s,
                address = %s,
                phone = %s,
                email = %s,
                total = %s
            WHERE job_id = %s
              AND invoice_index = %s
            """,
            (
                values["invoice_number"],
                values["invoice_date"],
                values["customer"],
                values["address"],
                values["phone"],
                values["email"],
                values["total"],
                job_id,
                invoice_index,
            ),
        )

        connection.commit()

        cursor.execute(
            """
            SELECT
                id,
                job_id,
                invoice_index,
                invoice_number,
                invoice_date,
                customer,
                address,
                phone,
                email,
                total
            FROM invoices
            WHERE job_id = %s
              AND invoice_index = %s
            LIMIT 1
            """,
            (job_id, invoice_index),
        )

        updated = cursor.fetchone()

        return {
            "success": True,
            "job_id": job_id,
            "invoice": updated,
            "message": (
                f"Invoice #{invoice_index} updated successfully."
            ),
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Error as exc:
        if connection:
            connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"MySQL invoice update error: {str(exc)}",
        )

    except Exception as exc:
        if connection:
            connection.rollback()
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Invoice update failed: {str(exc)}",
        )

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# ============================================================
# MANUAL INVOICE SAVE
# ============================================================

@app.post("/api/invoice/save")
def save_invoice_api(
    request: InvoiceSaveRequest,
):
    """
    Save ALL invoices found in the structured OCR JSON for this job.

    One OCR job may contain multiple invoices. Each invoice gets its
    own row in the invoices table using invoice_index = 1, 2, 3, ...
    """

    try:
        job_id = request.job_id

        if not jobs.get(job_id):
            raise HTTPException(
                status_code=404,
                detail="Job not found.",
            )

        structured_json = load_structured_ocr_json(job_id)

        if not structured_json:
            raise HTTPException(
                status_code=404,
                detail="Structured OCR JSON not found.",
            )

        invoices = extract_invoice_documents(structured_json)

        if not invoices:
            raise HTTPException(
                status_code=400,
                detail=(
                    'This document does not contain any exact '
                    'type == "invoice" records.'
                ),
            )

        database_result = save_invoices_to_database(
            job_id=job_id,
            invoice_data_list=invoices,
        )

        return {
            "success": True,
            "saved": True,
            "job_id": job_id,
            "saved_count": database_result["saved_count"],
            "invoices": database_result["invoices"],
            "message": database_result["message"],
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except Error as exc:
        raise HTTPException(
            status_code=500,
            detail=f"MySQL invoice error: {str(exc)}",
        )

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Invoice save failed: {str(exc)}",
        )


# ============================================================
# DOWNLOAD
# ============================================================

@app.get("/api/download/{job_id}/{file_type}")
def download_file(
    job_id: str,
    file_type: str,
):

    job = jobs.get(
        job_id
    )

    if not job:

        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    if file_type not in DOWNLOAD_FILE_MAP:

        raise HTTPException(
            status_code=400,
            detail="Invalid file type.",
        )

    result = job.get(
        "result"
    )

    if not result:

        raise HTTPException(
            status_code=404,
            detail=(
                "OCR result not available."
            ),
        )

    outputs = result.get(
        "outputs",
        {},
    )

    output_key = DOWNLOAD_FILE_MAP[
        file_type
    ]

    # --------------------------------------------------------
    # FIFTH OUTPUT: STRUCTURED OCR JSON
    # --------------------------------------------------------

    if output_key == "structured_ocr_json":

        structured_json_path = (
            find_structured_ocr_json(
                job_id
            )
        )

        if not structured_json_path:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Structured OCR JSON output "
                    "file not found."
                ),
            )

        return FileResponse(
            path=str(
                structured_json_path
            ),
            filename=(
                structured_json_path.name
            ),
            media_type=(
                "application/json"
            ),
            headers={
                "Content-Disposition": (
                    f'attachment; filename="'
                    f'{structured_json_path.name}"'
                )
            },
        )

    # --------------------------------------------------------
    # Existing four outputs
    # --------------------------------------------------------

    file_path = outputs.get(
        output_key
    )

    if not file_path:

        raise HTTPException(
            status_code=404,
            detail=(
                "Requested output file not found."
            ),
        )

    file_path = Path(
        str(file_path)
    )

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "Requested output file "
                "does not exist."
            ),
        )

    return FileResponse(
        path=str(
            file_path
        ),
        filename=file_path.name,
    )


# ============================================================
# PREVIEW
# ============================================================

@app.get("/api/preview/{job_id}/{file_type}")
def preview_file(
    job_id: str,
    file_type: str,
):

    job = jobs.get(
        job_id
    )

    if not job:

        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    if file_type not in DOWNLOAD_FILE_MAP:

        raise HTTPException(
            status_code=400,
            detail="Invalid file type.",
        )

    result = job.get(
        "result"
    )

    if not result:

        raise HTTPException(
            status_code=404,
            detail=(
                "OCR result not available."
            ),
        )

    outputs = result.get(
        "outputs",
        {},
    )

    output_key = DOWNLOAD_FILE_MAP[
        file_type
    ]

    # --------------------------------------------------------
    # FIFTH OUTPUT: STRUCTURED OCR JSON
    # --------------------------------------------------------

    if output_key == "structured_ocr_json":

        structured_json_path = (
            find_structured_ocr_json(
                job_id
            )
        )

        if not structured_json_path:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Structured OCR JSON preview "
                    "file not found."
                ),
            )

        return FileResponse(
            path=str(
                structured_json_path
            ),
            filename=(
                structured_json_path.name
            ),
            media_type=(
                "application/json"
            ),
            headers={
                "Content-Disposition": (
                    f'inline; filename="'
                    f'{structured_json_path.name}"'
                )
            },
        )

    # --------------------------------------------------------
    # Existing outputs
    # --------------------------------------------------------

    file_path = outputs.get(
        output_key
    )

    if not file_path:

        raise HTTPException(
            status_code=404,
            detail=(
                "Preview file not found."
            ),
        )

    file_path = Path(
        str(file_path)
    )

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "Preview file does not exist."
            ),
        )

    # --------------------------------------------------------
    # Correct media types
    # --------------------------------------------------------

    media_type = None

    if output_key == "json":

        media_type = (
            "application/json"
        )

    elif output_key == "txt":

        media_type = (
            "text/plain"
        )

    elif output_key in {
        "structured_pdf",
        "language_highlighted_pdf",
    }:

        media_type = (
            "application/pdf"
        )

    return FileResponse(
        path=str(
            file_path
        ),
        media_type=media_type,
        filename=file_path.name,
        headers={
            "Content-Disposition": (
                f'inline; filename="'
                f'{file_path.name}"'
            )
        },
    )


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "success": True,
        "name": "ASTRA-OCR API",
        "version": "1.0.0",
        "status": "running",
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
    }


# ============================================================
# SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    print()
    print("=" * 70)
    print(
        "ASTRA-OCR API SERVER"
    )
    print("=" * 70)
    print(
        f"Backend : {BASE_DIR}"
    )
    print(
        f"Uploads : {UPLOAD_DIR}"
    )
    print(
        f"Output  : {OUTPUT_DIR}"
    )
    print(
        "API     : http://127.0.0.1:8000"
    )
    print(
        "Swagger : http://127.0.0.1:8000/docs"
    )
    print("=" * 70)
    print()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
    )