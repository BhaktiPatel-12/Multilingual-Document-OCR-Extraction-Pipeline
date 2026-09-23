# Multilingual-Document-OCR-Extraction-Pipeline
Astra-OCR

Astra-OCR is a multilingual PDF OCR and document-processing application designed to extract text from scanned PDF documents and generate structured, searchable outputs.

Features

PDF upload and processing through a FastAPI backend

PDF page rendering and image preprocessing

Multilingual OCR using Surya OCR

OCR quality evaluation

Language detection

Structured text extraction

Searchable / structured PDF generation

Language-highlighted PDF generation

JSON and plain-text output

Optional MySQL database integration

Optional Meilisearch integration

Optional Gemini and Groq integrations for document/chat features

Project Structure

astra-ocr/
│
├── api.py
├── document_chat.py
├── create_searchable_pdf.py
├── setup_database.py
├── surya_main.py
├── test_pipeline.py
│
├── services/
│   └── OCR and document-processing services
│
├── fonts/
│   └── Fonts used for multilingual PDF generation
│
├── input/
│   └── Input documents / test files
│
├── uploads/
│   └── Uploaded documents
│
├── output/
│   └── Generated OCR results
│
├── downstreams/
│   └── Downstream processing components
│
├── database/
│   └── Database-related files
│
├── surya_direct_test/
│   └── Surya OCR experiments
│
└── requirements.txt

Local virtual environments such as surya_env, surya_env2, and .venv should not be committed to GitHub.

OCR Pipeline

The main processing flow is:

PDF
 │
 ▼
Page Rendering
 │
 ▼
Image Preprocessing
 │
 ▼
Surya OCR
 │
 ▼
Language Detection
 │
 ▼
OCR Quality Evaluation
 │
 ▼
Structure Reconstruction
 │
 ├──► JSON
 ├──► TXT
 ├──► Structured PDF
 └──► Language Highlighted PDF

Requirements

Python 3.10+ recommended

Git

A working Surya OCR installation

CUDA-compatible NVIDIA GPU is recommended for faster OCR processing

MySQL is required only if the database functionality is enabled

Meilisearch is required only if search functionality is enabled

Installation

1. Clone the repository

git clone https://github.com/YOUR_USERNAME/astra-ocr.git
cd astra-ocr

2. Create a virtual environment

Windows PowerShell:

python -m venv .venv
.\.venv\Scripts\Activate.ps1

Linux / macOS:

python3 -m venv .venv
source .venv/bin/activate

3. Install dependencies

pip install --upgrade pip
pip install -r requirements.txt

4. Configure environment variables

Create a .env file in the backend/project root.

Example:

# OCR / AI services
OCR_SPACE_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
GROQ_CHAT_MODEL=your_model_name

# Meilisearch
MEILI_URL=http://localhost:7700
MEILI_MASTER_KEY=your_meilisearch_key

# MySQL
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=astra_ocr

Never commit .env to GitHub.

If .env has already been committed to a public repository, rotate/revoke the exposed API keys and database credentials and then remove the file from Git history.

Running the API

From the project directory:

uvicorn api:app --reload --host 127.0.0.1 --port 8000

The API should then be available at:

http://127.0.0.1:8000

FastAPI documentation:

http://127.0.0.1:8000/docs

Main API Workflow

The frontend can send a PDF to:

POST /api/process

The response returns a job_id.

Processing status can then be checked with:

GET /api/status/{job_id}

Generated files can be downloaded using:

GET /api/download/{job_id}/json
GET /api/download/{job_id}/txt
GET /api/download/{job_id}/structured-pdf
GET /api/download/{job_id}/language-highlighted-pdf

Output Formats

OCR JSON

Contains document metadata, page-level OCR results, detected languages, preprocessing information, OCR levels, and quality information.

Plain Text

Text is stored page-by-page, making it easy to inspect or reuse in downstream applications.

Structured PDF

Produces a PDF reconstructed from OCR results while preserving document structure as closely as possible.

Language Highlighted PDF

Produces a PDF where recognized languages can be visually distinguished during document inspection.

OCR Quality

Astra-OCR includes an OCR quality evaluation stage. The quality system considers factors such as:

Extracted text quality

Language detection

Character quality

Text coverage

OCR confidence

The project uses a configurable quality threshold for deciding whether additional OCR processing or correction is required.

Development Notes

Large/generated directories should normally not be committed:

.venv/
surya_env/
surya_env2/
__pycache__/
output/
uploads/
input/
surya_output/
surya_direct_test/
.env
*.pyc

Keep source code, configuration templates, required fonts, and documentation in GitHub. Keep generated OCR results and local virtual environments outside the repository unless a particular sample is intentionally included.

Testing

The end-to-end OCR pipeline can be tested with:

python test_pipeline.py

For direct Surya experiments:

python surya_main.py

Use test/sample documents that you are legally permitted to process and publish.

Performance

OCR processing time depends on:

Number of PDF pages

Input resolution

Image preprocessing

OCR model execution

CPU vs GPU execution

PDF output generation

A CUDA-capable NVIDIA GPU can significantly reduce OCR inference time compared with CPU-only execution.

Roadmap

Possible future improvements:

Better mixed-language OCR handling

Improved OCR correction and confidence calibration

More document-layout-aware reconstruction

Search across processed documents

Document chat and question answering

Batch PDF processing

User authentication

Persistent job history

Docker deployment

Cloud deployment

License

Add the project's license here before publishing the repository.

Example:

MIT License

Do not add a license unless you intend to release the project under those terms.
