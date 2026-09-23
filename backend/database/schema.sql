CREATE DATABASE IF NOT EXISTS astra_ocr
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE astra_ocr;


-- ============================================================
-- DOCUMENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS documents (

    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    job_id VARCHAR(100) NOT NULL,

    filename VARCHAR(500) NOT NULL,

    document_hash VARCHAR(128),

    raw_json LONGTEXT NOT NULL,

    total_pages INT DEFAULT 0,

    total_blocks INT DEFAULT 0,

    languages_json TEXT,

    quality_score DECIMAL(6,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uq_documents_job_id (job_id),

    INDEX idx_documents_filename (filename),

    INDEX idx_documents_hash (document_hash)

) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- DOCUMENT PAGES
-- ============================================================

CREATE TABLE IF NOT EXISTS document_pages (

    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    document_id BIGINT NOT NULL,

    page_number INT NOT NULL,

    page_json LONGTEXT,

    languages_json TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_document_page
    (
        document_id,
        page_number
    ),

    CONSTRAINT fk_document_pages_document

        FOREIGN KEY (document_id)

        REFERENCES documents(id)

        ON DELETE CASCADE

) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- OCR BLOCKS
-- ============================================================

CREATE TABLE IF NOT EXISTS ocr_blocks (

    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    document_id BIGINT NOT NULL,

    page_number INT NOT NULL,

    block_number INT NOT NULL,

    text LONGTEXT NOT NULL,

    language VARCHAR(100),

    region_type VARCHAR(100),

    confidence DECIMAL(7,3),

    bbox_json TEXT,

    source VARCHAR(100),

    block_json LONGTEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_ocr_blocks_document
    (
        document_id
    ),

    INDEX idx_ocr_blocks_page
    (
        document_id,
        page_number
    ),

    INDEX idx_ocr_blocks_language
    (
        language
    ),

    CONSTRAINT fk_ocr_blocks_document

        FOREIGN KEY (document_id)

        REFERENCES documents(id)

        ON DELETE CASCADE

) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- DOCUMENT SUMMARY
-- ============================================================

CREATE TABLE IF NOT EXISTS documents_summary (

    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    document_id BIGINT NOT NULL,

    total_pages INT DEFAULT 0,

    total_blocks INT DEFAULT 0,

    languages_json TEXT,

    quality_score DECIMAL(6,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uq_summary_document
    (
        document_id
    ),

    CONSTRAINT fk_summary_document

        FOREIGN KEY (document_id)

        REFERENCES documents(id)

        ON DELETE CASCADE

) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- LANGUAGE COUNTS
-- ============================================================

CREATE TABLE IF NOT EXISTS document_language_counts (

    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    document_id BIGINT NOT NULL,

    language VARCHAR(100) NOT NULL,

    block_count INT DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_language_document
    (
        document_id
    ),

    CONSTRAINT fk_language_document

        FOREIGN KEY (document_id)

        REFERENCES documents(id)

        ON DELETE CASCADE

) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- DATA ENTRY RUN
-- ============================================================

CREATE TABLE IF NOT EXISTS data_entry_runs (

    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    document_id BIGINT NOT NULL,

    job_id VARCHAR(100),

    status VARCHAR(50),

    total_blocks INT DEFAULT 0,

    selected_blocks INT DEFAULT 0,

    field_count INT DEFAULT 0,

    review_required BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    completed_at TIMESTAMP NULL,

    CONSTRAINT fk_data_entry_run_document

        FOREIGN KEY (document_id)

        REFERENCES documents(id)

        ON DELETE CASCADE

) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- DATA ENTRY FIELDS
-- ============================================================

CREATE TABLE IF NOT EXISTS data_entry_fields (

    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    document_id BIGINT NOT NULL,

    run_id BIGINT NOT NULL,

    field_name VARCHAR(255),

    field_value LONGTEXT,

    field_type VARCHAR(100),

    confidence DECIMAL(7,3),

    validation_status VARCHAR(50),

    source_text LONGTEXT,

    page_number INT,

    block_id BIGINT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_data_entry_document
    (
        document_id
    ),

    INDEX idx_data_entry_field_name
    (
        field_name
    ),

    CONSTRAINT fk_data_entry_fields_document

        FOREIGN KEY (document_id)

        REFERENCES documents(id)

        ON DELETE CASCADE,

    CONSTRAINT fk_data_entry_fields_run

        FOREIGN KEY (run_id)

        REFERENCES data_entry_runs(id)

        ON DELETE CASCADE

) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- EXTRACTED FIELDS
-- ============================================================

CREATE TABLE IF NOT EXISTS extracted_fields (

    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    document_id BIGINT NOT NULL,

    data_entry_run_id BIGINT NOT NULL,

    job_id VARCHAR(100),

    field_name VARCHAR(255),

    field_value LONGTEXT,

    normalized_value LONGTEXT,

    confidence DECIMAL(7,3),

    validation_status VARCHAR(50),

    source_text LONGTEXT,

    matched_language VARCHAR(100),

    page_number INT,

    line_number INT,

    block_id BIGINT,

    extraction_method VARCHAR(100),

    field_type VARCHAR(100),

    region_type VARCHAR(100),

    ocr_source VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_extracted_document
    (
        document_id
    ),

    INDEX idx_extracted_field_name
    (
        field_name
    ),

    CONSTRAINT fk_extracted_document

        FOREIGN KEY (document_id)

        REFERENCES documents(id)

        ON DELETE CASCADE

) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- FINAL DATA ENTRY RECORD
-- ============================================================

CREATE TABLE IF NOT EXISTS data_entry_records (

    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    document_id BIGINT NOT NULL,

    run_id BIGINT NOT NULL,

    record_json LONGTEXT NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uq_data_entry_record
    (
        document_id
    ),

    CONSTRAINT fk_data_entry_record_document

        FOREIGN KEY (document_id)

        REFERENCES documents(id)

        ON DELETE CASCADE,

    CONSTRAINT fk_data_entry_record_run

        FOREIGN KEY (run_id)

        REFERENCES data_entry_runs(id)

        ON DELETE CASCADE

) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- SEARCH HISTORY
-- ============================================================

CREATE TABLE IF NOT EXISTS search_history (

    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    document_id BIGINT,

    query_text TEXT,

    result_count INT DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_search_history_document
    (
        document_id
    )

) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- COMPLIANCE RUNS
-- ============================================================

CREATE TABLE IF NOT EXISTS compliance_runs (

    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    document_id BIGINT NOT NULL,

    profile VARCHAR(100),

    overall_status VARCHAR(50),

    passed_count INT DEFAULT 0,

    warning_count INT DEFAULT 0,

    failed_count INT DEFAULT 0,

    report_json LONGTEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_compliance_document

        FOREIGN KEY (document_id)

        REFERENCES documents(id)

        ON DELETE CASCADE

) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4;