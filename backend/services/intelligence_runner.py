"""
Astra Intelligence Runner
-------------------------

This file connects:

    Existing SuryaOCRService
                ↓
    AstraIntelligenceService
                ↓
        Intelligence Result

IMPORTANT:
- surya_ocr_service.py is NOT modified.
- intelligence_service.py is NOT modified.
- This file only coordinates them.
"""

from pathlib import Path
from typing import Optional


# ================================================================
# EXISTING OCR SERVICE
# ================================================================

from surya_ocr_service import (
    SuryaOCRService,
)


# ================================================================
# NEW ASTRA INTELLIGENCE SERVICE
# ================================================================

from intelligence_service import (
    AstraIntelligenceService,
)


class AstraIntelligenceRunner:
    """
    Orchestrates the first Astra Intelligence pipeline.

    Current pipeline:

        Image
          ↓
        Existing Surya OCR
          ↓
        OCR blocks
          ↓
        Astra Intelligence
          ↓
        Suspicious regions

    No correction or re-OCR happens here yet.
    """

    # ============================================================
    # INITIALIZATION
    # ============================================================

    def __init__(
        self,
        output_dir="surya_output",
        llama_cpp_binary=None,
    ):
        """
        Initialize both services.

        Surya is the existing OCR engine.

        AstraIntelligenceService is our new
        independent analysis layer.
        """

        self.ocr_service = (
            SuryaOCRService(
                output_dir=output_dir,
                llama_cpp_binary=llama_cpp_binary,
            )
        )

        self.intelligence_service = (
            AstraIntelligenceService()
        )

    # ============================================================
    # RUN INTELLIGENCE
    # ============================================================

    def analyze_image(
        self,
        image_path,
        output_dir=None,
        timeout=300,
        save_json=True,
    ):
        """
        Run the complete first-stage intelligence pipeline.

        Steps:

            1. Validate image
            2. Run existing Surya OCR
            3. Receive normalized OCR result
            4. Analyze OCR result
            5. Return combined result

        Existing OCR code is not changed.
        """

        image_path = Path(
            image_path
        ).resolve()

        if not image_path.exists():

            raise FileNotFoundError(
                f"Image not found: "
                f"{image_path}"
            )

        print()
        print("=" * 60)
        print(
            "       ASTRA INTELLIGENCE PIPELINE"
        )
        print("=" * 60)

        print()
        print(
            f"Input image:"
        )

        print(
            image_path
        )

        # ========================================================
        # STEP 1
        # EXISTING SURYA OCR
        # ========================================================

        print()
        print("-" * 60)
        print(
            "STEP 1: EXISTING SURYA OCR"
        )
        print("-" * 60)

        ocr_result = (
            self.ocr_service.run_ocr(
                image_path=image_path,
                output_dir=output_dir,
                timeout=timeout,
                save_json=save_json,
            )
        )

        # ========================================================
        # SAFETY CHECK
        # ========================================================

        if not isinstance(
            ocr_result,
            dict,
        ):

            raise RuntimeError(
                "Surya OCR returned an "
                "unexpected result."
            )

        blocks = ocr_result.get(
            "results",
            [],
        )

        print()
        print(
            f"Surya returned "
            f"{len(blocks)} OCR blocks."
        )

        # ========================================================
        # STEP 2
        # ASTRA INTELLIGENCE
        # ========================================================

        print()
        print("-" * 60)
        print(
            "STEP 2: ASTRA INTELLIGENCE ANALYSIS"
        )
        print("-" * 60)

        intelligence_result = (
            self.intelligence_service.analyze(
                ocr_result
            )
        )

        # ========================================================
        # STEP 3
        # DISPLAY SUMMARY
        # ========================================================

        suspicious_count = (
            intelligence_result.get(
                "suspicious_blocks",
                0,
            )
        )

        total_blocks = (
            intelligence_result.get(
                "total_blocks",
                0,
            )
        )

        print()
        print(
            f"Total OCR blocks: "
            f"{total_blocks}"
        )

        print(
            f"Suspicious blocks: "
            f"{suspicious_count}"
        )

        # ========================================================
        # DISPLAY SUSPICIOUS REGIONS
        # ========================================================

        suspicious_regions = (
            intelligence_result.get(
                "suspicious_regions",
                [],
            )
        )

        if suspicious_regions:

            print()
            print(
                "Suspicious regions detected:"
            )

            for region in suspicious_regions:

                print()
                print(
                    f"Block index: "
                    f"{region.get('index')}"
                )

                print(
                    f"Text: "
                    f"{region.get('text')}"
                )

                print(
                    f"Confidence: "
                    f"{region.get('surya_confidence')}"
                )

                print(
                    f"Uncertainty: "
                    f"{region.get('uncertainty_score')}"
                )

                print(
                    f"BBox: "
                    f"{region.get('bbox')}"
                )

                print(
                    f"Signals: "
                    f"{region.get('signals')}"
                )

        else:

            print()
            print(
                "No suspicious regions detected."
            )

        # ========================================================
        # COMBINED RESULT
        # ========================================================

        combined_result = {

            "success": True,

            "image": str(
                image_path
            ),

            # ----------------------------------------------------
            # Original OCR result
            # ----------------------------------------------------

            "ocr": ocr_result,

            # ----------------------------------------------------
            # Astra analysis
            # ----------------------------------------------------

            "intelligence": (
                intelligence_result
            ),

            # ----------------------------------------------------
            # Convenient summary
            # ----------------------------------------------------

            "summary": {
                "total_blocks": total_blocks,

                "suspicious_blocks": (
                    suspicious_count
                ),

                "safe_blocks": (
                    total_blocks
                    - suspicious_count
                ),
            },
        }

        # ========================================================
        # FINAL
        # ========================================================

        print()
        print("=" * 60)
        print(
            "     ASTRA INTELLIGENCE COMPLETE"
        )
        print("=" * 60)

        return combined_result


# ================================================================
# DIRECT TEST
# ================================================================

if __name__ == "__main__":

    """
    IMPORTANT:

    Change this path to an ACTUAL image from
    your Astra project before running.

    Example:

        output/rendered/page_002.png
    """

    TEST_IMAGE = (
        r"../output/image.png"
    )

    runner = (
        AstraIntelligenceRunner()
    )

    try:

        result = runner.analyze_image(
            image_path=TEST_IMAGE,
        )

        print()
        print("=" * 60)
        print(
            "              FINAL SUMMARY"
        )
        print("=" * 60)

        print()

        print(
            f"Image: "
            f"{result['image']}"
        )

        print(
            f"Total blocks: "
            f"{result['summary']['total_blocks']}"
        )

        print(
            f"Suspicious blocks: "
            f"{result['summary']['suspicious_blocks']}"
        )

        print(
            f"Safe blocks: "
            f"{result['summary']['safe_blocks']}"
        )

    except Exception as exc:

        print()
        print("=" * 60)
        print(
            "             PIPELINE ERROR"
        )
        print("=" * 60)

        print()
        print(
            str(exc)
        )

        raise