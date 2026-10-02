import json
from pathlib import Path

from structured_ocr_service import AstraStructuredOCRService


# ============================================================
# TEST INPUT
# ============================================================

TEST_INPUT = {
    "results": [
        {
            "text": "Name",
            "page": 1,
            "bbox": [100, 100, 200, 125],
            "confidence": 0.98,
            "reading_order": 1,
            "language": "en"
        },
        {
            "text": "SHRUSTI DALWADI",
            "page": 1,
            "bbox": [220, 100, 450, 125],
            "confidence": 0.97,
            "reading_order": 2,
            "language": "en"
        },
        {
            "text": "Enrollment Number",
            "page": 1,
            "bbox": [100, 150, 250, 175],
            "confidence": 0.96,
            "reading_order": 3,
            "language": "en"
        },
        {
            "text": "202302626010017",
            "page": 1,
            "bbox": [270, 150, 500, 175],
            "confidence": 0.95,
            "reading_order": 4,
            "language": "en"
        },
        {
            "text": "Date of Birth",
            "page": 1,
            "bbox": [100, 200, 220, 225],
            "confidence": 0.94,
            "reading_order": 5,
            "language": "en"
        },
        {
            "text": "15/08/2004",
            "page": 1,
            "bbox": [240, 200, 380, 225],
            "confidence": 0.93,
            "reading_order": 6,
            "language": "en"
        },
        {
            "text": "College",
            "page": 1,
            "bbox": [100, 250, 180, 275],
            "confidence": 0.92,
            "reading_order": 7,
            "language": "en"
        },
        {
            "text": "ABC Engineering College",
            "page": 1,
            "bbox": [200, 250, 500, 275],
            "confidence": 0.91,
            "reading_order": 8,
            "language": "en"
        },
        {
            "text": "Result: PASS",
            "page": 1,
            "bbox": [100, 300, 300, 325],
            "confidence": 0.96,
            "reading_order": 9,
            "language": "en"
        },
        {
            "text": "This document is generated for testing.",
            "page": 1,
            "bbox": [100, 350, 500, 380],
            "confidence": 0.90,
            "reading_order": 10,
            "language": "en"
        }
    ],

    "detected_languages": ["en"],
    "multilingual": False,
    "total_blocks": 10,
    "source_json": "test_input.json"
}


# ============================================================
# CREATE TEMPORARY INPUT JSON
# ============================================================

def create_test_input():

    test_input_path = (
        Path(__file__).parent / "test_input.json"
    )

    with test_input_path.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            TEST_INPUT,
            file,
            ensure_ascii=False,
            indent=2
        )

    return test_input_path


# ============================================================
# RUN TEST
# ============================================================

def main():

    print()
    print("=" * 70)
    print("       TESTING ASTRA STRUCTURED OCR SERVICE")
    print("=" * 70)
    print()

    # --------------------------------------------------------
    # Create temporary JSON input
    # --------------------------------------------------------

    input_path = create_test_input()

    output_path = (
        Path(__file__).parent
        / "test_structured_output.json"
    )

    print(f"Test input : {input_path}")
    print(f"Test output: {output_path}")
    print()

    # --------------------------------------------------------
    # Initialize service
    # --------------------------------------------------------

    try:

        service = AstraStructuredOCRService()

        print("✅ AstraStructuredOCRService imported successfully.")

    except Exception as exc:

        print("❌ Failed to initialize service.")
        print(f"Error: {exc}")
        return

    print()

    # --------------------------------------------------------
    # Process JSON
    # --------------------------------------------------------

    try:

        structured, output_file = service.process_file(
            input_path,
            output_path
        )

    except Exception as exc:

        print("❌ STRUCTURING FAILED")
        print()
        print(f"Error: {exc}")
        return

    # --------------------------------------------------------
    # Show results
    # --------------------------------------------------------

    print("✅ STRUCTURING SUCCESSFUL")
    print()

    print("-" * 70)
    print("DOCUMENT")
    print("-" * 70)

    print(
        json.dumps(
            structured["document"],
            indent=2,
            ensure_ascii=False
        )
    )

    print()

    print("-" * 70)
    print("STRUCTURED FIELDS")
    print("-" * 70)

    if structured["fields"]:

        for key, field in structured["fields"].items():

            print(
                f"{key}: {field.get('value')}"
            )

    else:

        print("No structured fields detected.")

    print()

    print("-" * 70)
    print("GENERIC KEY/VALUE PAIRS")
    print("-" * 70)

    for pair in structured["key_value_pairs"]:

        print(
            f"{pair.get('label')} -> "
            f"{pair.get('value')}"
        )

    print()

    print("-" * 70)
    print("SUMMARY")
    print("-" * 70)

    print(
        f"Structured fields : "
        f"{len(structured['fields'])}"
    )

    print(
        f"Key/value pairs   : "
        f"{len(structured['key_value_pairs'])}"
    )

    print(
        f"Tables            : "
        f"{len(structured['tables'])}"
    )

    print(
        f"Paragraphs        : "
        f"{len(structured['paragraphs'])}"
    )

    print()

    print("-" * 70)
    print(f"Output written to:")
    print(output_file)
    print("-" * 70)

    print()

    print("=" * 70)
    print("       TEST COMPLETE")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()