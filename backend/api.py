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

# PyMuPDF is used only for Search Indexing PDF highlighting
# and Chatbot PDF text extraction.
# It does not change the OCR pipeline.
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
# These imports are intentionally isolated from the OCR pipeline.
#
# document_chat.py is responsible for:
# - extracting text from the structured PDF
# - generating summaries
# - answering questions with Groq
#
# The OCR pipeline itself is NOT changed.
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


# Cache extracted chatbot documents.
#
# Keys can be:
# - OCR job IDs
# - direct chatbot upload chat IDs
#
chat_document_cache: Dict[str, Dict[str, Any]] = {}

# Cache first generated document summaries.
chat_summary_cache: Dict[str, str] = {}


# ============================================================
# DIRECT CHATBOT PDF STORAGE
# ============================================================
#
# PDFs uploaded directly from the Chatbot page are stored here.
#
# IMPORTANT:
# These files are ALREADY-GENERATED STRUCTURED PDFs.
#
# They are NOT passed through /api/process.
# They are NOT sent to Surya OCR.
#
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
}


# ============================================================
# MYSQL CONFIGURATION
# ============================================================

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "astra_ocr")


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
# CHATBOT REQUEST MODEL
# ============================================================

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

    THIS IS THE AUTOMATIC DOCUMENT SAVE.
    DO NOT CONFUSE THIS WITH DATA ENTRY SAVE.
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

        pdf_id = ocr_result.get("pdf_id")
        page_count = ocr_result.get("total_pages", 0)

        # ----------------------------------------------------
        # Determine OCR provider
        # ----------------------------------------------------

        ocr_provider = "Surya OCR"

        pages = ocr_result.get("pages", [])

        if isinstance(pages, list):

            sources = []

            for page in pages:

                if not isinstance(page, dict):
                    continue

                final_source = page.get("final_source")

                if final_source:
                    sources.append(str(final_source))

            if sources:

                unique_sources = list(
                    dict.fromkeys(sources)
                )

                ocr_provider = " / ".join(
                    unique_sources
                )

        # ----------------------------------------------------
        # Fusion
        # ----------------------------------------------------

        fusion = ocr_result.get("fusion")

        if fusion is not None:
            fusion = str(fusion)

        # ----------------------------------------------------
        # Convert complete result to JSON
        # ----------------------------------------------------

        raw_json = json.dumps(
            ocr_result,
            ensure_ascii=False,
            default=str,
        )

        # ----------------------------------------------------
        # Insert / Update documents
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
            str(pdf_id) if pdf_id is not None else None,
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
        # Get database document ID
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
        print(f"Document ID    : {document_id}")
        print(f"Job ID         : {job_id}")
        print(f"Page Count     : {page_count}")
        print("=" * 70)
        print()

        return {
            "success": True,
            "document_id": document_id,
            "job_id": job_id,
            "message": "Document automatically saved to MySQL.",
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
# SAVE OCR TEXT TO SEARCH INDEX
# ============================================================

def save_search_index_to_database(
    job_id: str,
    ocr_result: Dict[str, Any],
):
    """
    Automatically saves OCR text blocks into the search_index table
    after the document itself has been saved.

    This does NOT change the OCR pipeline. It only indexes the
    already-generated OCR result for later searching.
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

        print(f"MySQL database : {MYSQL_DATABASE}")
        print(f"Job ID         : {job_id}")

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

        print(f"Document ID    : {document_id}")
        print(f"Filename       : {filename}")

        # Remove an older index for this document before rebuilding it.
        cursor.execute(
            """
            DELETE FROM search_index
            WHERE document_id = %s
            """,
            (document_id,),
        )

        rows = []
        pages = ocr_result.get("pages", [])

        if isinstance(pages, list):

            for page in pages:

                if not isinstance(page, dict):
                    continue

                page_number = page.get("page_number")

                final_result = page.get(
                    "final_result",
                    {},
                )

                if not isinstance(final_result, dict):
                    continue

                results = final_result.get(
                    "results",
                    [],
                )

                if not isinstance(results, list):
                    continue

                for block_number, block in enumerate(results):

                    text_content = ""

                    if isinstance(block, dict):

                        for key in (
                            "text",
                            "content",
                            "html",
                            "value",
                        ):
                            value = block.get(key)

                            if value is not None:
                                text_content = str(value)
                                break

                    elif isinstance(block, str):
                        text_content = block

                    # Remove HTML markup if present.
                    text_content = re.sub(
                        r"<[^>]*>",
                        " ",
                        text_content,
                    )

                    # Normalize whitespace.
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
        print("SEARCH INDEX SAVE SUCCESSFUL")
        print("-" * 70)
        print(f"Document ID    : {document_id}")
        print(f"Job ID         : {job_id}")
        print(f"Blocks indexed : {indexed_count}")
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
        print("SEARCH INDEX SAVE FAILED")
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
    Saves the Data Entry records into the data_entry table.

    Existing Data Entry rows for the same document are deleted
    first so that clicking "Save All to Database" always represents
    the current Data Entry section.
    """

    connection = None
    cursor = None

    try:

        print()
        print("=" * 70)
        print("SAVING DATA ENTRY RECORDS TO MYSQL")
        print("=" * 70)

        connection = connect_to_mysql()
        cursor = connection.cursor()

        print(f"MySQL database : {MYSQL_DATABASE}")
        print(f"Job ID         : {job_id}")

        # ----------------------------------------------------
        # Find the document saved automatically by OCR process
        # ----------------------------------------------------

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

        print(f"Document ID    : {document_id}")
        print(f"Filename       : {filename}")

        # ----------------------------------------------------
        # Remove previous Data Entry rows
        # ----------------------------------------------------

        cursor.execute(
            """
            DELETE FROM data_entry
            WHERE document_id = %s
            """,
            (document_id,),
        )

        # ----------------------------------------------------
        # Prepare rows
        # ----------------------------------------------------

        rows = []

        if isinstance(entries, list):

            for entry in entries:

                if not isinstance(entry, dict):
                    continue

                field_name = str(
                    entry.get("name", "")
                ).strip()

                field_value = str(
                    entry.get("value", "")
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

        # ----------------------------------------------------
        # Insert rows
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------

        connection.commit()

        saved_count = len(rows)

        print()
        print("DATA ENTRY SAVE SUCCESSFUL")
        print("-" * 70)
        print(f"Document ID    : {document_id}")
        print(f"Job ID         : {job_id}")
        print(f"Records saved  : {saved_count}")
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
        print("DATA ENTRY SAVE FAILED")
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

    jobs[job_id].update(kwargs)

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

    Surya OCR / OCR pipeline itself is NOT changed.
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
        print("OCR WORKER FAILED")
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
            output_dir=str(output_dir),
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
            input_file=str(input_pdf),
            ocr_result=result,
        )

        result["database"] = database_result

        # ----------------------------------------------------
        # Build Search Index automatically
        # ----------------------------------------------------

        update_job(
            job_id,
            progress=97,
            message=(
                "OCR JSON saved. "
                "Building search index..."
            ),
        )

        search_index_result = save_search_index_to_database(
            job_id=job_id,
            ocr_result=result,
        )

        result["search_index"] = search_index_result

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
        print("OCR JOB COMPLETED")
        print("=" * 70)
        print(f"Job ID         : {job_id}")
        print(f"Filename       : {filename}")
        print("=" * 70)
        print()

    except Exception as exc:

        print()
        print("=" * 70)
        print("OCR PROCESS FAILED")
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

        job_id = str(uuid.uuid4())

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
            "input_file": str(input_path),
            "output_dir": str(job_output_dir),
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
            "message": "OCR processing started.",
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
    job = jobs.get(job_id)

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
    job = jobs.get(job_id)

    if not job:

        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    return {
        "success": True,
        "job_id": job_id,
        "status": job.get("status"),
        "result": job.get("result"),
    }


# ============================================================
# SEARCH INDEX
# ============================================================

@app.get("/api/search/{job_id}")
def search_document(
    job_id: str,
    q: str,
):
    """
    Searches MySQL search_index and enriches each match with
    the corresponding OCR JSON block from documents.raw_json.
    """

    connection = None
    cursor = None

    try:

        query = str(q or "").strip()

        if not query:
            return {
                "success": True,
                "job_id": job_id,
                "query": "",
                "results": [],
                "total": 0,
            }

        connection = connect_to_mysql()
        cursor = connection.cursor(dictionary=True)

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
                int(row["page_number"])
                if row["page_number"] is not None
                else 1
            )

            block_number = (
                int(row["block_number"])
                if row["block_number"] is not None
                else 0
            )

            text_content = str(
                row["text_content"] or ""
            )

            ocr_block = None
            page_details = {}

            try:

                raw_json = row.get("raw_json")

                parsed_json = (
                    json.loads(raw_json)
                    if isinstance(raw_json, str)
                    else raw_json
                )

                pages = (
                    parsed_json.get("pages", [])
                    if isinstance(parsed_json, dict)
                    else []
                )

                page_obj = None

                if isinstance(pages, list):

                    for candidate in pages:

                        if not isinstance(candidate, dict):
                            continue

                        if int(
                            candidate.get(
                                "page_number",
                                0,
                            ) or 0
                        ) == page_number:

                            page_obj = candidate
                            break

                    if (
                        page_obj is None
                        and 1 <= page_number <= len(pages)
                    ):

                        candidate = pages[
                            page_number - 1
                        ]

                        if isinstance(candidate, dict):
                            page_obj = candidate

                elif isinstance(pages, dict):

                    page_obj = pages.get(
                        str(page_number)
                    )

                if isinstance(page_obj, dict):

                    final_result = page_obj.get(
                        "final_result",
                        {},
                    )

                    if isinstance(
                        final_result,
                        dict,
                    ):

                        final_results = final_result.get(
                            "results",
                            [],
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

                            candidate_block = final_results[
                                block_number
                            ]

                            if isinstance(
                                candidate_block,
                                dict,
                            ):

                                ocr_block = candidate_block

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
                # Legacy/malformed raw_json must not break search.
                ocr_block = None

            results.append(
                {
                    "page": page_number,
                    "blockIndex": block_number,
                    "text": text_content,
                    "type": (
                        ocr_block.get("label")
                        if isinstance(
                            ocr_block,
                            dict,
                        )
                        and ocr_block.get("label")
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
            "total": len(results),
        }

    except Error as exc:

        if connection:
            connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"MySQL search error: {str(exc)}",
        )

    except Exception as exc:

        if connection:
            connection.rollback()

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(exc)}",
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
    """
    Creates a temporary highlighted copy of the already-generated
    structured PDF. No OCR is run here.
    """

    connection = None
    cursor = None
    pdf_document = None

    try:

        query = str(q or "").strip()

        if not query:
            raise HTTPException(
                status_code=400,
                detail="Search query is required.",
            )

        connection = connect_to_mysql()
        cursor = connection.cursor(dictionary=True)

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
                detail="Document not found for this OCR job.",
            )

        raw_json = document.get("raw_json")

        try:

            parsed_json = (
                json.loads(raw_json)
                if isinstance(raw_json, str)
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
            parsed_json.get("outputs", {})
            if isinstance(parsed_json, dict)
            else {}
        )

        structured_pdf = (
            outputs.get("structured_pdf")
            if isinstance(outputs, dict)
            else None
        )

        if not structured_pdf:

            raise HTTPException(
                status_code=404,
                detail="Structured PDF output is not available.",
            )

        pdf_path = Path(
            str(structured_pdf)
        )

        if not pdf_path.is_absolute():
            pdf_path = BASE_DIR / pdf_path

        if not pdf_path.exists():

            raise HTTPException(
                status_code=404,
                detail="Structured PDF file does not exist.",
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

        matching_rows = cursor.fetchall()

        block_lookup = {}

        for row in matching_rows:

            page_number = (
                int(row["page_number"])
                if row["page_number"] is not None
                else 1
            )

            block_number = (
                int(row["block_number"])
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

        # Preferred: exact text highlighting in the searchable PDF.
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

                annot = page.add_highlight_annot(
                    rect
                )

                if annot:

                    annot.update()

                    total_highlights += 1

        # Fallback: highlight the OCR block identified by MySQL.
        if (
            total_highlights == 0
            and block_lookup
        ):

            try:

                parsed_pages = (
                    parsed_json.get("pages", [])
                    if isinstance(parsed_json, dict)
                    else []
                )

                for page_number, block_numbers in block_lookup.items():

                    page_index = page_number - 1

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

                            candidate = parsed_pages[
                                page_index
                            ]

                            if isinstance(
                                candidate,
                                dict,
                            ):

                                page_obj = candidate

                    elif isinstance(
                        parsed_pages,
                        dict,
                    ):

                        candidate = parsed_pages.get(
                            str(page_number)
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

                    final_result = page_obj.get(
                        "final_result",
                        {},
                    )

                    if not isinstance(
                        final_result,
                        dict,
                    ):
                        continue

                    final_results = final_result.get(
                        "results",
                        [],
                    )

                    if not isinstance(
                        final_results,
                        list,
                    ):
                        continue

                    pdf_page = pdf_document[
                        page_index
                    ]

                    for block_number in block_numbers:

                        if not (
                            0 <= block_number < len(
                                final_results
                            )
                        ):
                            continue

                        block = final_results[
                            block_number
                        ]

                        if not isinstance(
                            block,
                            dict,
                        ):
                            continue

                        geometry = (
                            block.get("polygon")
                            or block.get("bbox")
                            or block.get("box")
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

                                if len(point) >= 2:

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
                            and len(geometry) >= 4
                        ):

                            x1, y1, x2, y2 = geometry[
                                :4
                            ]

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

                        if len(points) < 2:
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

                            annot = pdf_page.add_highlight_annot(
                                rect
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
            path=str(output_path),
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
    """
    Find the exact structured PDF generated by the OCR pipeline.

    Priority:

    1. jobs[job_id]["result"]["outputs"]["structured_pdf"]
    2. jobs[job_id]["output_files"]["structured_pdf"]
    3. structured PDF inside the job output directory

    This is used when the chatbot is connected to an existing
    OCR job.

    No OCR is performed here.
    """

    # --------------------------------------------------------
    # 1. Exact path from OCR result
    # --------------------------------------------------------

    job = jobs.get(job_id)

    if job:

        result = job.get("result")

        if isinstance(result, dict):

            outputs = result.get(
                "outputs",
                {},
            )

            if isinstance(outputs, dict):

                structured_pdf = outputs.get(
                    "structured_pdf"
                )

                if structured_pdf:

                    path = Path(
                        str(structured_pdf)
                    )

                    if not path.is_absolute():
                        path = BASE_DIR / path

                    if path.exists():
                        return path

        # ----------------------------------------------------
        # 2. Exact path from verified output files
        # ----------------------------------------------------

        output_files = job.get(
            "output_files",
            {},
        )

        if isinstance(output_files, dict):

            structured_pdf = output_files.get(
                "structured_pdf"
            )

            if structured_pdf:

                path = Path(
                    str(structured_pdf)
                )

                if not path.is_absolute():
                    path = BASE_DIR / path

                if path.exists():
                    return path

    # --------------------------------------------------------
    # 3. Search job directory
    # --------------------------------------------------------

    job_output_dir = (
        API_JOBS_DIR /
        job_id
    )

    if not job_output_dir.exists():
        return None

    pdf_candidates = list(
        job_output_dir.rglob("*.pdf")
    )

    if not pdf_candidates:
        return None

    # Exact structured PDF preference.
    for pdf in pdf_candidates:

        if "structured" in pdf.name.lower():

            return pdf

    return None


# ============================================================
# CHATBOT - LOAD STRUCTURED PDF
# ============================================================

def load_chat_document(
    job_id: str,
) -> Dict[str, Any]:
    """
    Load and cache the structured PDF belonging to an OCR job.

    The PDF is extracted with document_chat.py.

    NO OCR is performed here.
    """

    # --------------------------------------------------------
    # Return cached document if already loaded
    # --------------------------------------------------------

    if job_id in chat_document_cache:

        return chat_document_cache[
            job_id
        ]

    # --------------------------------------------------------
    # Make sure OCR job exists
    # --------------------------------------------------------

    job = jobs.get(job_id)

    if not job:

        raise FileNotFoundError(
            "OCR job was not found."
        )

    # --------------------------------------------------------
    # Make sure OCR is complete
    # --------------------------------------------------------

    if job.get("status") != "completed":

        raise ValueError(
            "The OCR document is not ready yet. "
            "Please wait until processing is completed."
        )

    # --------------------------------------------------------
    # Resolve structured PDF
    # --------------------------------------------------------

    pdf_path = resolve_chat_structured_pdf(
        job_id
    )

    if not pdf_path:

        raise FileNotFoundError(
            "The structured PDF generated by the OCR pipeline "
            "could not be found."
        )

    print()
    print("=" * 70)
    print("CHATBOT DOCUMENT LOADING")
    print("=" * 70)
    print()

    print(
        f"Job ID         : {job_id}"
    )

    print(
        f"Structured PDF : {pdf_path}"
    )

    print()

    # --------------------------------------------------------
    # Extract text using document_chat.py
    # --------------------------------------------------------

    document_data = extract_pdf_text(
        str(pdf_path)
    )

    # --------------------------------------------------------
    # Validate extracted text
    # --------------------------------------------------------

    if not document_data.get(
        "has_text"
    ):

        raise ValueError(
            "The generated structured PDF does not contain "
            "usable selectable text."
        )

    # --------------------------------------------------------
    # Add OCR/job information
    # --------------------------------------------------------

    document_data["job_id"] = job_id

    document_data["structured_pdf"] = str(
        pdf_path
    )

    # --------------------------------------------------------
    # Cache document
    # --------------------------------------------------------

    chat_document_cache[
        job_id
    ] = document_data

    print()
    print("=" * 70)
    print("CHATBOT DOCUMENT LOADED")
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
    """
    Upload an already-generated structured PDF for chatbot use.

    IMPORTANT:

    This endpoint DOES NOT run OCR.

    It only:

        1. Receives the already-generated structured PDF.
        2. Saves the PDF.
        3. Extracts selectable text using document_chat.py.
        4. Creates a chatbot session ID.
        5. Caches the extracted document.

    It NEVER calls:

        /api/process

    It NEVER calls:

        PDFOCRService

    It NEVER calls:

        Surya OCR

    It NEVER performs OCR.
    """

    chat_directory = None

    try:

        # ----------------------------------------------------
        # Validate filename
        # ----------------------------------------------------

        if not file.filename:

            raise HTTPException(
                status_code=400,
                detail="No filename provided.",
            )

        safe_filename = Path(
            file.filename
        ).name

        # ----------------------------------------------------
        # Validate PDF
        # ----------------------------------------------------

        if (
            not safe_filename.lower().endswith(".pdf")
            and file.content_type != "application/pdf"
        ):

            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported.",
            )

        # ----------------------------------------------------
        # Create chatbot session ID
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Save uploaded PDF
        # ----------------------------------------------------

        with open(
            pdf_path,
            "wb",
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )

        # ----------------------------------------------------
        # Verify file exists
        # ----------------------------------------------------

        if not pdf_path.exists():

            raise HTTPException(
                status_code=500,
                detail="Uploaded PDF could not be saved.",
            )

        # ----------------------------------------------------
        # Extract text
        #
        # This uses PyMuPDF through document_chat.py.
        #
        # NO OCR.
        # ----------------------------------------------------

        print()
        print("=" * 70)
        print("CHATBOT PDF UPLOAD")
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
            str(pdf_path)
        )

        # ----------------------------------------------------
        # Validate extracted text
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Add chatbot information
        # ----------------------------------------------------

        document_data["chat_id"] = chat_id

        document_data["structured_pdf"] = str(
            pdf_path
        )

        document_data["filename"] = (
            document_data.get(
                "filename"
            )
            or safe_filename
        )

        # ----------------------------------------------------
        # Cache document
        # ----------------------------------------------------

        chat_document_cache[
            chat_id
        ] = document_data

        # Make sure no previous summary exists.
        chat_summary_cache.pop(
            chat_id,
            None,
        )

        # ----------------------------------------------------
        # Success logging
        # ----------------------------------------------------

        print()
        print("=" * 70)
        print("CHATBOT PDF READY")
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
        print("=" * 70)
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
        print("CHATBOT PDF UPLOAD FAILED")
        print("=" * 70)
        print()

        print(str(exc))

        traceback.print_exc()

        print()
        print("=" * 70)
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
    """
    Resolve a chatbot document.

    Supports BOTH:

    1. Direct chatbot-uploaded structured PDFs.
    2. Existing OCR jobs.

    Direct chatbot uploads are checked first.
    """

    # --------------------------------------------------------
    # 1. Direct chatbot uploaded PDF
    # --------------------------------------------------------

    if chat_id in chat_document_cache:

        return chat_document_cache[
            chat_id
        ]

    # --------------------------------------------------------
    # 2. Existing OCR job
    # --------------------------------------------------------

    if chat_id in jobs:

        return load_chat_document(
            chat_id
        )

    # --------------------------------------------------------
    # Nothing found
    # --------------------------------------------------------

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
    """
    Chat with a structured PDF.

    Supports BOTH:

    ------------------------------------------------------------
    A. Existing OCR job
    ------------------------------------------------------------

        POST /api/chat/{ocr_job_id}

    The structured PDF is resolved from the completed OCR job.

    ------------------------------------------------------------
    B. Direct chatbot PDF upload
    ------------------------------------------------------------

        POST /api/chat/upload

    returns:

        chat_id

    Then:

        POST /api/chat/{chat_id}

    The uploaded PDF is already the structured PDF.

    NO OCR is run.

    ------------------------------------------------------------
    FIRST REQUEST
    ------------------------------------------------------------

        1. Load document.
        2. Generate document summary.
        3. Answer user's question.

    ------------------------------------------------------------
    SUBSEQUENT REQUESTS
    ------------------------------------------------------------

        Use the same cached document and summary.
    """

    question = str(
        request.message or ""
    ).strip()

    # --------------------------------------------------------
    # Validate question
    # --------------------------------------------------------

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    # --------------------------------------------------------
    # Resolve chatbot document
    #
    # This handles:
    #
    # - direct uploaded structured PDF
    # - existing OCR job
    # --------------------------------------------------------

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
        print("CHATBOT DOCUMENT ERROR")
        print("=" * 70)
        print()

        print(str(exc))

        traceback.print_exc()

        print()

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not load chatbot document: "
                f"{str(exc)}"
            ),
        )

    # --------------------------------------------------------
    # Create Groq client
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Clean frontend conversation history
    # --------------------------------------------------------

    history = request.history or []

    clean_history = []

    if isinstance(history, list):

        for item in history:

            if not isinstance(item, dict):
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

    # --------------------------------------------------------
    # Determine first chatbot request
    # --------------------------------------------------------

    first_chat_request = (
        job_id not in chat_summary_cache
    )

    summary = None

    # --------------------------------------------------------
    # FIRST REQUEST -> GENERATE SUMMARY
    # --------------------------------------------------------

    if first_chat_request:

        print()
        print("=" * 70)
        print("GENERATING DOCUMENT SUMMARY FOR CHATBOT")
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
            print("CHATBOT SUMMARY ERROR")
            print("=" * 70)
            print()

            print(str(exc))

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

    # --------------------------------------------------------
    # ASK THE USER'S QUESTION
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("DOCUMENT CHAT REQUEST")
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
        print("GROQ CHAT ERROR")
        print("=" * 70)
        print()

        print(str(exc))

        traceback.print_exc()

        print()

        raise HTTPException(
            status_code=500,
            detail=(
                f"Chatbot error: "
                f"{str(exc)}"
            ),
        )

    # --------------------------------------------------------
    # RETURN SUMMARY + ANSWER
    # --------------------------------------------------------

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
    """
    Generate or return the cached summary.

    Supports BOTH:

    - existing OCR job IDs
    - direct chatbot PDF upload chat IDs
    """

    # --------------------------------------------------------
    # Resolve document
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Existing OCR job status validation
    #
    # Direct chatbot uploads do not have an OCR status.
    # --------------------------------------------------------

    if job_id in jobs:

        job = jobs.get(
            job_id
        )

        if not job:

            raise HTTPException(
                status_code=404,
                detail="OCR job not found.",
            )

        if job.get("status") != "completed":

            raise HTTPException(
                status_code=400,
                detail=(
                    "The OCR document is not ready yet."
                ),
            )

    # --------------------------------------------------------
    # Return cached summary
    # --------------------------------------------------------

    if job_id in chat_summary_cache:

        return {
            "success": True,

            "job_id": job_id,

            "chat_id": job_id,

            "summary": chat_summary_cache[
                job_id
            ],

            "document": {
                "filename": (
                    document_data.get(
                        "filename"
                    )
                ),

                "total_pages": (
                    document_data.get(
                        "total_pages"
                    )
                ),

                "total_characters": (
                    document_data.get(
                        "total_characters"
                    )
                ),
            },
        }

    # --------------------------------------------------------
    # Groq client
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Generate summary
    # --------------------------------------------------------

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
    """
    Saves the Data Entry records from the Results page.

    This endpoint is called ONLY when the user clicks:

        Save All to Database

    It does NOT affect the automatic documents-table save.
    """

    try:

        # ----------------------------------------------------
        # Convert Pydantic models to dictionaries
        # Compatible with Pydantic v1 and v2
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Save
        # ----------------------------------------------------

        result = save_data_entries_to_database(
            job_id=request.job_id,
            entries=entries,
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
            detail=f"MySQL error: {str(exc)}",
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
# DOWNLOAD
# ============================================================

@app.get("/api/download/{job_id}/{file_type}")
def download_file(
    job_id: str,
    file_type: str,
):

    job = jobs.get(job_id)

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

    result = job.get("result")

    if not result:

        raise HTTPException(
            status_code=404,
            detail="OCR result not available.",
        )

    outputs = result.get(
        "outputs",
        {},
    )

    output_key = DOWNLOAD_FILE_MAP[
        file_type
    ]

    file_path = outputs.get(
        output_key
    )

    if not file_path:

        raise HTTPException(
            status_code=404,
            detail="Requested output file not found.",
        )

    file_path = Path(
        str(file_path)
    )

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Requested output file does not exist.",
        )

    return FileResponse(
        path=str(file_path),
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

    job = jobs.get(job_id)

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

    result = job.get("result")

    if not result:

        raise HTTPException(
            status_code=404,
            detail="OCR result not available.",
        )

    outputs = result.get(
        "outputs",
        {},
    )

    output_key = DOWNLOAD_FILE_MAP[
        file_type
    ]

    file_path = outputs.get(
        output_key
    )

    if not file_path:

        raise HTTPException(
            status_code=404,
            detail="Preview file not found.",
        )

    file_path = Path(
        str(file_path)
    )

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Preview file does not exist.",
        )

    return FileResponse(
        path=str(file_path)
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
    print("ASTRA-OCR API SERVER")
    print("=" * 70)
    print(f"Backend : {BASE_DIR}")
    print(f"Uploads : {UPLOAD_DIR}")
    print(f"Output  : {OUTPUT_DIR}")
    print("API     : http://127.0.0.1:8000")
    print("Swagger : http://127.0.0.1:8000/docs")
    print("=" * 70)
    print()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
    )