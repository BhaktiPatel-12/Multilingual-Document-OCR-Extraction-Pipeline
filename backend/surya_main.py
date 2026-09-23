from services.surya_ocr_service import SuryaOCRService


def main():

    print("\n")
    print("========================================")
    print("       ASTRA-OCR SURYA TEST")
    print("========================================")

    service = SuryaOCRService()

    result = service.run_ocr(
        r"output/rendered/page_001.png"
    )

    print("\n\n")
    print("========================================")
    print("             FINAL RESULT")
    print("========================================")

    print(
        f"\nTotal text blocks: "
        f"{result['total_blocks']}"
    )

    for i, item in enumerate(
        result["results"],
        start=1
    ):

        print("\n----------------------------------------")

        print(f"Block {i}")
        print(f"Text     : {item['text']}")
        print(f"Language : {item['language']}")
        print(f"Confidence: {item['confidence']}")
        print(f"BBox     : {item['bbox']}")

    print("\n")
    print("========================================")
    print("          SURYA TEST COMPLETE")
    print("========================================")


if __name__ == "__main__":
    main()