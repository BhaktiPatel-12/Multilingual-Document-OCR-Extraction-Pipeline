from pathlib import Path

from services.pdf_ocr_service import PDFOCRService


# ==============================================================
# CONFIGURATION
# ==============================================================


# --------------------------------------------------------------
# INPUT PDF
# --------------------------------------------------------------
#
# Put the FULL path of the PDF you want to process here.
#
# Windows example:
#
# INPUT_PDF = Path(
#     r"C:\Users\dalwa\Desktop\astra-ocr\input\certificate.pdf"
# )
#
# The r before the string is important for Windows paths.
# --------------------------------------------------------------

INPUT_PDF = Path(
    r"C:\Users\dalwa\Desktop\astra-ocr\backend\input\input4.pdf"
)


# --------------------------------------------------------------
# QUALITY THRESHOLD
# --------------------------------------------------------------

QUALITY_THRESHOLD = 60.0


# --------------------------------------------------------------
# OUTPUT DIRECTORY
# --------------------------------------------------------------

OUTPUT_DIR = "output"


# ==============================================================
# MAIN
# ==============================================================

def main():

    print()
    print("=" * 70)
    print(
        "          ASTRA-OCR PDF END-TO-END TEST"
    )
    print("=" * 70)

    # ----------------------------------------------------------
    # INPUT PDF
    # ----------------------------------------------------------

    pdf_path = INPUT_PDF

    print()
    print(
        f"Input PDF: {pdf_path}"
    )

    # ----------------------------------------------------------
    # CHECK INPUT
    # ----------------------------------------------------------

    if not pdf_path.exists():

        print()
        print(
            "ERROR: Input PDF not found."
        )

        print()
        print(
            f"Expected path:"
        )

        print(
            pdf_path
        )

        print()

        raise FileNotFoundError(
            f"Input PDF not found: {pdf_path}"
        )

    if not pdf_path.is_file():

        raise ValueError(
            f"Input path is not a file: {pdf_path}"
        )

    if pdf_path.suffix.lower() != ".pdf":

        raise ValueError(
            f"Input file must be a PDF: {pdf_path}"
        )

    # ----------------------------------------------------------
    # SERVICE
    # ----------------------------------------------------------

    print()
    print(
        "Initializing Astra-OCR PDF service..."
    )

    service = PDFOCRService(
        output_dir=OUTPUT_DIR,
        quality_threshold=QUALITY_THRESHOLD,
    )

    # ----------------------------------------------------------
    # PROCESS COMPLETE PDF
    # ----------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "              PROCESSING PDF"
    )
    print("=" * 70)

    print()

    result = service.process_pdf(
        pdf_path
    )

    # ----------------------------------------------------------
    # SUMMARY
    # ----------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "                  FINAL OUTPUT"
    )
    print("=" * 70)

    print()

    print(
        "Input:"
    )

    print(
        result["input_pdf"]
    )

    print()

    print(
        "Pages:"
    )

    print(
        result["total_pages"]
    )

    # ----------------------------------------------------------
    # JSON
    # ----------------------------------------------------------

    print()

    print(
        "JSON:"
    )

    print(
        result["outputs"]["json"]
    )

    # ----------------------------------------------------------
    # TXT
    # ----------------------------------------------------------

    print()

    print(
        "TXT:"
    )

    print(
        result["outputs"]["txt"]
    )

    # ----------------------------------------------------------
    # STRUCTURED PDF
    # ----------------------------------------------------------

    print()

    print(
        "Structured PDF:"
    )

    print(
        result["outputs"]["structured_pdf"]
    )

    # ----------------------------------------------------------
    # LANGUAGE HIGHLIGHTED PDF
    # ----------------------------------------------------------

    print()

    print(
        "Language Highlighted PDF:"
    )

    print(
        result["outputs"][
            "language_highlighted_pdf"
        ]
    )

    # ----------------------------------------------------------
    # COMPLETE
    # ----------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "                  TEST COMPLETE"
    )
    print("=" * 70)

    print()


# ==============================================================
# ENTRY POINT
# ==============================================================

if __name__ == "__main__":

    main()