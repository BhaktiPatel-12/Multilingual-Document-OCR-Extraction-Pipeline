import os
import sys
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_PATH)


MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "astra_ocr")


# ============================================================
# DATABASE CONNECTION
# ============================================================

def connect_to_mysql(database=None):
    config = {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
    }

    if database:
        config["database"] = database

    return mysql.connector.connect(**config)


# ============================================================
# CREATE DATABASE
# ============================================================

def create_database():
    print()
    print("=" * 70)
    print("ASTRA-OCR DATABASE SETUP")
    print("=" * 70)
    print()

    print("Connecting to MySQL Server...")
    print(f"Host     : {MYSQL_HOST}")
    print(f"Port     : {MYSQL_PORT}")
    print(f"User     : {MYSQL_USER}")
    print()

    connection = None
    cursor = None

    try:
        connection = connect_to_mysql()
        cursor = connection.cursor()

        print("✓ Connected to MySQL Server")

        cursor.execute(
            f"""
            CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}`
            CHARACTER SET utf8mb4
            COLLATE utf8mb4_unicode_ci
            """
        )

        connection.commit()

        print(f"✓ Database ready: {MYSQL_DATABASE}")

        return True

    except Error as error:
        print()
        print("❌ Could not connect to MySQL.")
        print()
        print(f"MySQL error: {error}")
        print()

        print("Check:")
        print("  1. MySQL Server is running")
        print("  2. MYSQL_USER is correct")
        print("  3. MYSQL_PASSWORD is correct")
        print("  4. MYSQL_PORT is correct")
        print()

        return False

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# TABLE DEFINITIONS
# ============================================================

TABLES = [

    # --------------------------------------------------------
    # DOCUMENTS
    # --------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS documents (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        job_id VARCHAR(128) NOT NULL UNIQUE,

        doc_id VARCHAR(255),

        filename VARCHAR(512),

        input_file VARCHAR(1024),

        ocr_provider VARCHAR(100),

        fusion VARCHAR(100),

        page_count INT DEFAULT 0,

        raw_json JSON,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ON UPDATE CURRENT_TIMESTAMP,

        INDEX idx_documents_doc_id (doc_id),

        INDEX idx_documents_filename (filename)
    )
    """,

    # --------------------------------------------------------
    # DOCUMENT PAGES
    # --------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS document_pages (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        document_id BIGINT NOT NULL,

        page_number INT NOT NULL,

        page_text LONGTEXT,

        image_path VARCHAR(1024),

        quality_score DECIMAL(6,2),

        language VARCHAR(100),

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (document_id)
            REFERENCES documents(id)
            ON DELETE CASCADE,

        UNIQUE KEY uq_document_page (
            document_id,
            page_number
        ),

        INDEX idx_pages_document (
            document_id
        )
    )
    """,

    # --------------------------------------------------------
    # OCR BLOCKS
    # --------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS ocr_blocks (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        document_id BIGINT NOT NULL,

        page_id BIGINT,

        block_id VARCHAR(255),

        page_number INT,

        line_number INT,

        region_type VARCHAR(100),

        language VARCHAR(50),

        text LONGTEXT,

        confidence DECIMAL(8,5),

        low_confidence BOOLEAN DEFAULT FALSE,

        bbox JSON,

        label VARCHAR(255),

        raw_label VARCHAR(255),

        ocr_source VARCHAR(100),

        source VARCHAR(255),

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (document_id)
            REFERENCES documents(id)
            ON DELETE CASCADE,

        FOREIGN KEY (page_id)
            REFERENCES document_pages(id)
            ON DELETE SET NULL,

        INDEX idx_blocks_document (
            document_id
        ),

        INDEX idx_blocks_page (
            page_number
        ),

        INDEX idx_blocks_language (
            language
        ),

        INDEX idx_blocks_confidence (
            confidence
        )
    )
    """,

    # --------------------------------------------------------
    # DOCUMENT SUMMARY
    # --------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS documents_summary (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        document_id BIGINT NOT NULL UNIQUE,

        doc_id VARCHAR(255),

        input_file VARCHAR(1024),

        ocr_provider VARCHAR(100),

        fusion VARCHAR(100),

        page_count INT DEFAULT 0,

        total_blocks INT DEFAULT 0,

        paragraph_count INT DEFAULT 0,

        heading_count INT DEFAULT 0,

        table_row_count INT DEFAULT 0,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (document_id)
            REFERENCES documents(id)
            ON DELETE CASCADE,

        INDEX idx_summary_doc_id (
            doc_id
        )
    )
    """,

    # --------------------------------------------------------
    # LANGUAGE COUNTS
    # --------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS document_language_counts (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        document_id BIGINT NOT NULL,

        language VARCHAR(50) NOT NULL,

        count INT DEFAULT 0,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (document_id)
            REFERENCES documents(id)
            ON DELETE CASCADE,

        UNIQUE KEY uq_document_language (
            document_id,
            language
        )
    )
    """,

    # --------------------------------------------------------
    # DATA ENTRY RUNS
    # --------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS data_entry_runs (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        document_id BIGINT NOT NULL,

        status VARCHAR(50),

        total_blocks INT DEFAULT 0,

        extracted_blocks INT DEFAULT 0,

        extracted_fields INT DEFAULT 0,

        review_required INT DEFAULT 0,

        threshold DECIMAL(6,4) DEFAULT 0.75,

        started_at TIMESTAMP NULL,

        completed_at TIMESTAMP NULL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (document_id)
            REFERENCES documents(id)
            ON DELETE CASCADE,

        INDEX idx_data_entry_document (
            document_id
        )
    )
    """,

    # --------------------------------------------------------
    # DATA ENTRY BLOCKS
    # --------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS data_entry_blocks (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        data_entry_run_id BIGINT NOT NULL,

        document_id BIGINT NOT NULL,

        block_id VARCHAR(255),

        page_number INT,

        language VARCHAR(50),

        region_type VARCHAR(100),

        text LONGTEXT,

        confidence DECIMAL(8,5),

        extraction_status VARCHAR(50),

        review_required BOOLEAN DEFAULT FALSE,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (data_entry_run_id)
            REFERENCES data_entry_runs(id)
            ON DELETE CASCADE,

        FOREIGN KEY (document_id)
            REFERENCES documents(id)
            ON DELETE CASCADE,

        INDEX idx_de_blocks_run (
            data_entry_run_id
        ),

        INDEX idx_de_blocks_document (
            document_id
        )
    )
    """,

    # --------------------------------------------------------
    # DATA ENTRY FIELDS
    # --------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS data_entry_fields (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        data_entry_run_id BIGINT NOT NULL,

        document_id BIGINT NOT NULL,

        block_id VARCHAR(255),

        field_name VARCHAR(255),

        field_value LONGTEXT,

        normalized_value LONGTEXT,

        confidence DECIMAL(8,5),

        validation_status VARCHAR(50),

        source_text LONGTEXT,

        matched_language VARCHAR(50),

        page_number INT,

        line_number INT,

        extraction_method VARCHAR(100),

        field_type VARCHAR(100),

        region_type VARCHAR(100),

        ocr_source VARCHAR(100),

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (data_entry_run_id)
            REFERENCES data_entry_runs(id)
            ON DELETE CASCADE,

        FOREIGN KEY (document_id)
            REFERENCES documents(id)
            ON DELETE CASCADE,

        INDEX idx_fields_document (
            document_id
        ),

        INDEX idx_fields_name (
            field_name
        )
    )
    """,

    # --------------------------------------------------------
    # DATA ENTRY PATTERNS
    # --------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS data_entry_patterns (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        data_entry_run_id BIGINT NOT NULL,

        pattern_name VARCHAR(255),

        pattern_type VARCHAR(100),

        matched_text LONGTEXT,

        confidence DECIMAL(8,5),

        page_number INT,

        block_id VARCHAR(255),

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (data_entry_run_id)
            REFERENCES data_entry_runs(id)
            ON DELETE CASCADE,

        INDEX idx_patterns_run (
            data_entry_run_id
        )
    )
    """,

    # --------------------------------------------------------
    # DATA ENTRY RECORDS
    # --------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS data_entry_records (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        data_entry_run_id BIGINT NOT NULL,

        document_id BIGINT NOT NULL,

        record_type VARCHAR(100),

        record_json JSON,

        status VARCHAR(50),

        confidence DECIMAL(8,5),

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (data_entry_run_id)
            REFERENCES data_entry_runs(id)
            ON DELETE CASCADE,

        FOREIGN KEY (document_id)
            REFERENCES documents(id)
            ON DELETE CASCADE,

        INDEX idx_records_document (
            document_id
        )
    )
    """,

    # --------------------------------------------------------
    # DATA ENTRY REVIEW LOG
    # --------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS data_entry_review_log (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        data_entry_run_id BIGINT NOT NULL,

        document_id BIGINT NOT NULL,

        block_id VARCHAR(255),

        reason VARCHAR(255),

        source_text LONGTEXT,

        confidence DECIMAL(8,5),

        status VARCHAR(50) DEFAULT 'pending',

        reviewer VARCHAR(255),

        review_notes LONGTEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        reviewed_at TIMESTAMP NULL,

        FOREIGN KEY (data_entry_run_id)
            REFERENCES data_entry_runs(id)
            ON DELETE CASCADE,

        FOREIGN KEY (document_id)
            REFERENCES documents(id)
            ON DELETE CASCADE,

        INDEX idx_review_document (
            document_id
        ),

        INDEX idx_review_status (
            status
        )
    )
    """,

    # --------------------------------------------------------
    # SEARCH HISTORY
    # --------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS search_history (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        query_text LONGTEXT NOT NULL,

        filters JSON,

        result_count INT DEFAULT 0,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        INDEX idx_search_history_created (
            created_at
        )
    )
    """,

    # --------------------------------------------------------
    # SEARCH RESULTS
    # --------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS search_results (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        search_history_id BIGINT NOT NULL,

        document_id BIGINT,

        block_id VARCHAR(255),

        rank_position INT,

        score DECIMAL(12,6),

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (search_history_id)
            REFERENCES search_history(id)
            ON DELETE CASCADE,

        FOREIGN KEY (document_id)
            REFERENCES documents(id)
            ON DELETE SET NULL,

        INDEX idx_search_results_history (
            search_history_id
        )
    )
    """,

    # --------------------------------------------------------
    # COMPLIANCE RUNS
    # --------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS compliance_runs (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        document_id BIGINT NOT NULL,

        data_entry_run_id BIGINT,

        profile VARCHAR(100),

        overall_status VARCHAR(100),

        total_rules INT DEFAULT 0,

        passed_rules INT DEFAULT 0,

        warning_rules INT DEFAULT 0,

        failed_rules INT DEFAULT 0,

        not_applicable_rules INT DEFAULT 0,

        report_path VARCHAR(1024),

        report_json JSON,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (document_id)
            REFERENCES documents(id)
            ON DELETE CASCADE,

        FOREIGN KEY (data_entry_run_id)
            REFERENCES data_entry_runs(id)
            ON DELETE SET NULL,

        INDEX idx_compliance_document (
            document_id
        ),

        INDEX idx_compliance_status (
            overall_status
        )
    )
    """,

    # --------------------------------------------------------
    # COMPLIANCE RESULTS
    # --------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS compliance_results (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        compliance_run_id BIGINT NOT NULL,

        document_id BIGINT NOT NULL,

        rule_id VARCHAR(255),

        rule_name VARCHAR(255),

        category VARCHAR(100),

        status VARCHAR(50),

        severity VARCHAR(50),

        message LONGTEXT,

        field_name VARCHAR(255),

        field_value LONGTEXT,

        evidence LONGTEXT,

        confidence DECIMAL(8,5),

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (compliance_run_id)
            REFERENCES compliance_runs(id)
            ON DELETE CASCADE,

        FOREIGN KEY (document_id)
            REFERENCES documents(id)
            ON DELETE CASCADE,

        INDEX idx_compliance_results_run (
            compliance_run_id
        ),

        INDEX idx_compliance_results_document (
            document_id
        ),

        INDEX idx_compliance_results_status (
            status
        )
    )
    """,

    # --------------------------------------------------------
    # EXTRACTED FIELDS
    # --------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS extracted_fields (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        document_id BIGINT NOT NULL,

        data_entry_run_id BIGINT,

        doc_id VARCHAR(255),

        field_name VARCHAR(255),

        field_value LONGTEXT,

        normalized_value LONGTEXT,

        confidence DECIMAL(8,5),

        validation_status VARCHAR(50),

        source_text LONGTEXT,

        matched_language VARCHAR(50),

        page_number INT,

        line_number INT,

        block_id VARCHAR(255),

        extraction_method VARCHAR(100),

        field_type VARCHAR(100),

        region_type VARCHAR(100),

        ocr_source VARCHAR(100),

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (document_id)
            REFERENCES documents(id)
            ON DELETE CASCADE,

        FOREIGN KEY (data_entry_run_id)
            REFERENCES data_entry_runs(id)
            ON DELETE SET NULL,

        INDEX idx_extracted_document (
            document_id
        ),

        INDEX idx_extracted_field_name (
            field_name
        ),

        INDEX idx_extracted_block (
            block_id
        )
    )
    """
]


# ============================================================
# CREATE TABLES
# ============================================================

def create_tables():
    print()
    print("=" * 70)
    print("CREATING ASTRA-OCR TABLES")
    print("=" * 70)
    print()

    connection = None
    cursor = None

    try:
        connection = connect_to_mysql(MYSQL_DATABASE)
        cursor = connection.cursor()

        print(f"Using database: {MYSQL_DATABASE}")
        print()

        for index, table_sql in enumerate(TABLES, start=1):

            # Extract table name for display
            cleaned = table_sql.strip()

            table_name = "unknown"

            if "CREATE TABLE IF NOT EXISTS" in cleaned:
                after = cleaned.split(
                    "CREATE TABLE IF NOT EXISTS",
                    1
                )[1].strip()

                table_name = after.split("(", 1)[0].strip()

            print(
                f"[{index:02d}/{len(TABLES):02d}] "
                f"Creating {table_name}..."
            )

            cursor.execute(table_sql)

            print(f"       ✓ {table_name}")

        connection.commit()

        print()
        print("✓ All tables created successfully.")

        return True

    except Error as error:
        print()
        print("❌ Error while creating tables.")
        print()
        print(f"MySQL error: {error}")
        print()

        if connection:
            connection.rollback()

        return False

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# VERIFY DATABASE
# ============================================================

def verify_database():
    print()
    print("=" * 70)
    print("VERIFYING DATABASE")
    print("=" * 70)
    print()

    connection = None
    cursor = None

    try:
        connection = connect_to_mysql(MYSQL_DATABASE)
        cursor = connection.cursor()

        cursor.execute("SHOW TABLES")

        tables = cursor.fetchall()

        print(
            f"Database `{MYSQL_DATABASE}` contains "
            f"{len(tables)} tables:"
        )
        print()

        for table in tables:
            print(f"  ✓ {table[0]}")

        print()

        expected_tables = [
            "documents",
            "document_pages",
            "ocr_blocks",
            "documents_summary",
            "document_language_counts",
            "data_entry_runs",
            "data_entry_blocks",
            "data_entry_fields",
            "data_entry_patterns",
            "data_entry_records",
            "data_entry_review_log",
            "search_history",
            "search_results",
            "compliance_runs",
            "compliance_results",
            "extracted_fields",
        ]

        actual_tables = {
            table[0]
            for table in tables
        }

        missing_tables = [
            table
            for table in expected_tables
            if table not in actual_tables
        ]

        if missing_tables:
            print("❌ Missing tables:")
            for table in missing_tables:
                print(f"   - {table}")

            return False

        print("✓ Verification successful.")
        print("✓ All expected Astra-OCR tables exist.")

        return True

    except Error as error:
        print()
        print("❌ Verification failed.")
        print(f"MySQL error: {error}")
        return False

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("              ASTRA-OCR MYSQL SETUP")
    print("=" * 70)
    print()

    if not os.path.exists(ENV_PATH):
        print("⚠ .env file was not found.")
        print()
        print(f"Expected location:")
        print(ENV_PATH)
        print()

        print("Create/update your backend .env first.")
        sys.exit(1)

    if not create_database():
        sys.exit(1)

    if not create_tables():
        sys.exit(1)

    if not verify_database():
        sys.exit(1)

    print()
    print("=" * 70)
    print("              DATABASE SETUP COMPLETE")
    print("=" * 70)
    print()
    print(f"Database : {MYSQL_DATABASE}")
    print("Status   : READY")
    print()
    print("Astra-OCR can now connect to MySQL.")
    print()


if __name__ == "__main__":
    main()