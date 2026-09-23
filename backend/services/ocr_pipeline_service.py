# from pathlib import Path

# from services.surya_ocr_service import SuryaOCRService
# from services.preprocessing_service import ImagePreprocessor
# from services.correction_service import OCRCorrectionService
# from services.level3_hybrid_service import Level3HybridOCRService


# class OCRPipelineService:
#     """
#     Astra-OCR hierarchical OCR pipeline.

#     LEVEL 1:
#         Surya OCR

#     LEVEL 2:
#         OCRCorrectionService
#         - Calculates Level 1 quality
#         - Decides whether correction is required
#         - Runs enhanced / threshold Surya OCR when required
#         - Applies post-OCR corrections

#     LEVEL 3:
#         OCR.space + Gemini hybrid
#         - Used when Level 2 quality remains below threshold
#         - If one API fails, use the other
#         - If both succeed, compare outputs
#         - Adjudicate when required
#     """

#     def __init__(
#         self,
#         output_dir="output/pipeline",
#         quality_threshold=80.0
#     ):
#         self.output_dir = Path(output_dir)

#         self.output_dir.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         self.quality_threshold = float(
#             quality_threshold
#         )

#         # =====================================================
#         # SERVICES
#         # =====================================================

#         self.preprocessor = ImagePreprocessor()

#         self.surya = SuryaOCRService()

#         self.correction_service = (
#             OCRCorrectionService()
#         )

#         self.level3 = (
#             Level3HybridOCRService()
#         )

#     # =========================================================
#     # QUALITY SCORE HELPER
#     # =========================================================

#     @staticmethod
#     def get_quality_score(
#         quality
#     ):
#         """
#         Safely extract quality score.
#         """

#         if not quality:
#             return 0.0

#         try:

#             return float(
#                 quality.get(
#                     "quality_score",
#                     0.0
#                 )
#             )

#         except (
#             TypeError,
#             ValueError
#         ):

#             return 0.0

#     # =========================================================
#     # QUALITY STATUS HELPER
#     # =========================================================

#     @staticmethod
#     def get_quality_status(
#         quality
#     ):
#         """
#         Safely extract quality status.
#         """

#         if not quality:

#             return "unknown"

#         return quality.get(
#             "status",
#             "unknown"
#         )

#     # =========================================================
#     # PROCESS ONE PAGE
#     # =========================================================

#     def process_page(
#         self,
#         image_path,
#         page_number,
#         preprocessing_outputs=None,
#         expected_language=None
#     ):
#         """
#         Process one page through the hierarchical OCR pipeline.

#         Flow:

#             Rendered page
#                 ↓
#             Preprocessing
#                 ↓
#             LEVEL 1 — Surya
#                 ↓
#             LEVEL 2 — OCRCorrectionService
#                 ↓
#             Quality check
#                 ↓
#             LEVEL 3 — OCR.space + Gemini
#                 ↓
#             Final result
#         """

#         image_path = Path(
#             image_path
#         )

#         if not image_path.exists():

#             raise FileNotFoundError(
#                 f"Image not found: {image_path}"
#             )

#         # =====================================================
#         # PAGE HEADER
#         # =====================================================

#         print("\n")
#         print("=" * 70)
#         print(
#             f"ASTRA-OCR PAGE {page_number}"
#         )
#         print("=" * 70)

#         # =====================================================
#         # PREPROCESSING
#         # =====================================================

#         print("\n")
#         print("=" * 70)
#         print("PREPROCESSING")
#         print("=" * 70)

#         # -----------------------------------------------------
#         # IMPORTANT:
#         #
#         # test_full_pipeline.py may already provide
#         # preprocessing_outputs.
#         #
#         # If they are provided, DO NOT preprocess again.
#         #
#         # Otherwise preprocess the image here.
#         # -----------------------------------------------------

#         if preprocessing_outputs is None:

#             preprocessing_outputs = (
#                 self.preprocessor.preprocess(
#                     image_path,
#                     page_number
#                 )
#             )

#         for name, path in (
#             preprocessing_outputs.items()
#         ):

#             print(
#                 f"{name:12} : {path}"
#             )

#         # =====================================================
#         # LEVEL 1 — SURYA OCR
#         # =====================================================

#         print("\n")
#         print("=" * 70)
#         print("LEVEL 1 — SURYA OCR")
#         print("=" * 70)

#         level1_output_dir = (
#             self.output_dir
#             / f"page_{page_number:03d}"
#             / "level1"
#         )

#         level1_output_dir.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         original_image = (
#             preprocessing_outputs.get(
#                 "original"
#             )
#         )

#         # -----------------------------------------------------
#         # FALLBACK
#         # -----------------------------------------------------

#         if not original_image:

#             original_image = str(
#                 image_path
#             )

#         print(
#             f"Level 1 input : "
#             f"{original_image}"
#         )

#         # =====================================================
#         # RUN SURYA
#         # =====================================================

#         level1_result = (
#             self.surya.run_ocr(
#                 original_image,
#                 output_dir=str(
#                     level1_output_dir
#                 )
#             )
#         )

#         print(
#             f"Level 1 blocks : "
#             f"{level1_result.get('total_blocks', 0)}"
#         )

#         # =====================================================
#         # LEVEL 2 — OCR SELF-CORRECTION
#         # =====================================================

#         print("\n")
#         print("=" * 70)
#         print("LEVEL 2 — OCR SELF-CORRECTION")
#         print("=" * 70)

#         correction_result = (
#             self.correction_service.correct_page(
#                 image_path=original_image,

#                 preprocessing_outputs=(
#                     preprocessing_outputs
#                 ),

#                 initial_result=level1_result,

#                 page_number=page_number,

#                 expected_language=(
#                     expected_language
#                 )
#             )
#         )

#         # =====================================================
#         # LEVEL 1 QUALITY
#         # =====================================================

#         #
#         # OCRCorrectionService calculates the Level 1 quality
#         # internally.
#         #
#         # We use that result here instead of calling
#         # OCRQualityService directly.
#         #

#         original_info = (
#             correction_result.get(
#                 "original",
#                 {}
#             )
#         )

#         level1_quality = (
#             original_info.get(
#                 "quality",
#                 {}
#             )
#         )

#         level1_score = (
#             self.get_quality_score(
#                 level1_quality
#             )
#         )

#         level1_status = (
#             self.get_quality_status(
#                 level1_quality
#             )
#         )

#         print("\n")
#         print(
#             f"Level 1 quality : "
#             f"{level1_score:.2f}"
#         )

#         print(
#             f"Level 1 status  : "
#             f"{level1_status}"
#         )

#         # =====================================================
#         # LEVEL 2 RESULT
#         # =====================================================

#         level2_result = (
#             correction_result.get(
#                 "final_result"
#             )
#         )

#         level2_quality = (
#             correction_result.get(
#                 "final_quality",
#                 {}
#             )
#         )

#         level2_score = (
#             self.get_quality_score(
#                 level2_quality
#             )
#         )

#         level2_status = (
#             self.get_quality_status(
#                 level2_quality
#             )
#         )

#         # =====================================================
#         # LEVEL 2 FLAGS
#         # =====================================================

#         ocr_rerun_attempted = bool(
#             correction_result.get(
#                 "ocr_rerun_attempted",
#                 False
#             )
#         )

#         post_ocr_correction_applied = bool(
#             correction_result.get(
#                 "post_ocr_correction_applied",
#                 False
#             )
#         )

#         selected_level2 = (
#             correction_result.get(
#                 "selected",
#                 "original"
#             )
#         )

#         # =====================================================
#         # LEVEL 2 REPORT
#         # =====================================================

#         print("\n")
#         print(
#             f"Level 2 OCR rerun : "
#             f"{ocr_rerun_attempted}"
#         )

#         print(
#             f"Level 2 selected  : "
#             f"{selected_level2}"
#         )

#         print(
#             f"Level 2 quality   : "
#             f"{level2_score:.2f}"
#         )

#         print(
#             f"Level 2 status    : "
#             f"{level2_status}"
#         )

#         # =====================================================
#         # DETECT LANGUAGES
#         # =====================================================

#         detected_languages = (
#             correction_result.get(
#                 "detected_languages",
#                 []
#             )
#         )

#         # =====================================================
#         # LEVEL 3 DECISION
#         # =====================================================

#         #
#         # IMPORTANT:
#         #
#         # Level 3 is NOT triggered merely because Level 1 is
#         # below the threshold.
#         #
#         # Level 2 gets its opportunity first.
#         #
#         # Only the FINAL Level 2 quality is compared against
#         # the Level 3 threshold.
#         #

#         level3_required = (
#             level2_score
#             < self.quality_threshold
#         )

#         print("\n")
#         print(
#             f"Level 3 required : "
#             f"{level3_required}"
#         )

#         print(
#             f"Level 3 threshold: "
#             f"{self.quality_threshold:.2f}"
#         )

#         # =====================================================
#         # FINAL LEVEL 1
#         # =====================================================

#         #
#         # This happens when:
#         #
#         # - Surya quality is sufficient
#         # - OCRCorrectionService did not rerun OCR
#         # - No post-OCR correction changed the result
#         # - Level 3 is not required
#         #

#         if (
#             not ocr_rerun_attempted
#             and not post_ocr_correction_applied
#             and not level3_required
#         ):

#             print("\n")
#             print("=" * 70)
#             print("FINAL RESULT — LEVEL 1")
#             print("=" * 70)

#             return {
#                 "page_number": page_number,

#                 "final_level": 1,

#                 "final_source": "surya",

#                 "final_result": level1_result,

#                 "final_quality": level1_quality,

#                 "detected_languages": (
#                     detected_languages
#                 ),

#                 "preprocessing_outputs": (
#                     preprocessing_outputs
#                 ),

#                 "level1": {
#                     "result": level1_result,
#                     "quality": level1_quality
#                 },

#                 "level2": correction_result,

#                 "level3": None,

#                 "level3_attempted": False
#             }

#         # =====================================================
#         # FINAL LEVEL 2
#         # =====================================================

#         if not level3_required:

#             print("\n")
#             print("=" * 70)
#             print("FINAL RESULT — LEVEL 2")
#             print("=" * 70)

#             return {
#                 "page_number": page_number,

#                 "final_level": 2,

#                 "final_source": (
#                     f"surya_correction:{selected_level2}"
#                 ),

#                 "final_result": level2_result,

#                 "final_quality": level2_quality,

#                 "detected_languages": (
#                     detected_languages
#                 ),

#                 "preprocessing_outputs": (
#                     preprocessing_outputs
#                 ),

#                 "level1": {
#                     "result": level1_result,
#                     "quality": level1_quality
#                 },

#                 "level2": correction_result,

#                 "level3": None,

#                 "level3_attempted": False
#             }

#         # =====================================================
#         # LEVEL 3 — OCR.SPACE + GEMINI
#         # =====================================================

#         print("\n")
#         print("=" * 70)
#         print("LEVEL 3 — OCR.SPACE + GEMINI HYBRID")
#         print("=" * 70)

#         print(
#             f"Level 2 quality "
#             f"{level2_score:.2f} is below "
#             f"threshold "
#             f"{self.quality_threshold:.2f}"
#         )

#         print(
#             "\nEscalating to Level 3..."
#         )

#         # =====================================================
#         # RUN LEVEL 3
#         # =====================================================

#         #
#         # Level3HybridOCRService is responsible for:
#         #
#         #   OCR.space
#         #       +
#         #   Gemini
#         #
#         # and deciding which result is best.
#         #

#         level3_result = (
#             self.level3.run(
#                 input_path=str(
#                     original_image
#                 ),
#                 page_number=page_number
#             )
#         )

#         # =====================================================
#         # LEVEL 3 FINAL RESULT
#         # =====================================================

#         level3_final_result = (
#             level3_result.get(
#                 "final_result"
#             )
#         )

#         level3_final_quality = (
#             level3_result.get(
#                 "final_quality",
#                 {}
#             )
#         )

#         level3_score = (
#             self.get_quality_score(
#                 level3_final_quality
#             )
#         )

#         level3_source = (
#             level3_result.get(
#                 "selected_source",
#                 level3_result.get(
#                     "source",
#                     "level3"
#                 )
#             )
#         )

#         # =====================================================
#         # FINAL LEVEL 3 REPORT
#         # =====================================================

#         print("\n")
#         print("=" * 70)
#         print("FINAL RESULT — LEVEL 3")
#         print("=" * 70)

#         print(
#             f"Level 3 source  : "
#             f"{level3_source}"
#         )

#         print(
#             f"Level 3 quality : "
#             f"{level3_score:.2f}"
#         )

#         return {
#             "page_number": page_number,

#             "final_level": 3,

#             "final_source": (
#                 f"level3:{level3_source}"
#             ),

#             "final_result": (
#                 level3_final_result
#             ),

#             "final_quality": (
#                 level3_final_quality
#             ),

#             "detected_languages": (
#                 detected_languages
#             ),

#             "preprocessing_outputs": (
#                 preprocessing_outputs
#             ),

#             "level1": {
#                 "result": level1_result,
#                 "quality": level1_quality
#             },

#             "level2": correction_result,

#             "level3": level3_result,

#             "level3_attempted": True
#         }

#     # =========================================================
#     # PROCESS MULTIPLE PAGES
#     # =========================================================

#     def process_pages(
#         self,
#         image_paths,
#         preprocessing_outputs_list=None,
#         expected_language=None
#     ):
#         """
#         Process multiple rendered pages.

#         preprocessing_outputs_list is optional.

#         If supplied, it must contain the preprocessing
#         dictionary corresponding to each image.
#         """

#         results = []

#         for index, image_path in enumerate(
#             image_paths
#         ):

#             page_number = index + 1

#             current_preprocessing = None

#             if (
#                 preprocessing_outputs_list
#                 and index
#                 < len(
#                     preprocessing_outputs_list
#                 )
#             ):

#                 current_preprocessing = (
#                     preprocessing_outputs_list[
#                         index
#                     ]
#                 )

#             try:

#                 result = (
#                     self.process_page(
#                         image_path=image_path,

#                         page_number=page_number,

#                         preprocessing_outputs=(
#                             current_preprocessing
#                         ),

#                         expected_language=(
#                             expected_language
#                         )
#                     )
#                 )

#                 results.append(
#                     result
#                 )

#             except Exception as exc:

#                 print("\n")
#                 print("=" * 70)
#                 print(
#                     f"ERROR — PAGE {page_number}"
#                 )
#                 print("=" * 70)

#                 print(
#                     f"{type(exc).__name__}: "
#                     f"{exc}"
#                 )

#                 results.append({
#                     "page_number": page_number,

#                     "final_level": None,

#                     "final_source": "error",

#                     "final_result": None,

#                     "final_quality": {
#                         "quality_score": 0.0,
#                         "status": "error"
#                     },

#                     "error": str(exc)
#                 })

#         return results

#     # =========================================================
#     # DOCUMENT SUMMARY
#     # =========================================================

#     @staticmethod
#     def build_document_summary(
#         page_results
#     ):
#         """
#         Build document-level OCR summary.
#         """

#         summary = {
#             "total_pages": len(
#                 page_results
#             ),

#             "level1_pages": 0,

#             "level2_pages": 0,

#             "level3_pages": 0,

#             "error_pages": 0,

#             "average_quality": 0.0
#         }

#         quality_scores = []

#         for result in page_results:

#             level = result.get(
#                 "final_level"
#             )

#             if level == 1:

#                 summary[
#                     "level1_pages"
#                 ] += 1

#             elif level == 2:

#                 summary[
#                     "level2_pages"
#                 ] += 1

#             elif level == 3:

#                 summary[
#                     "level3_pages"
#                 ] += 1

#             else:

#                 summary[
#                     "error_pages"
#                 ] += 1

#             quality = result.get(
#                 "final_quality",
#                 {}
#             )

#             try:

#                 score = float(
#                     quality.get(
#                         "quality_score",
#                         0
#                     )
#                 )

#                 if score > 0:

#                     quality_scores.append(
#                         score
#                     )

#             except (
#                 TypeError,
#                 ValueError
#             ):

#                 pass

#         if quality_scores:

#             summary[
#                 "average_quality"
#             ] = round(
#                 sum(
#                     quality_scores
#                 )
#                 / len(
#                     quality_scores
#                 ),
#                 2
#             )

#         return summary













































# from pathlib import Path

# from services.surya_ocr_service import SuryaOCRService
# from services.preprocessing_service import ImagePreprocessor
# from services.correction_service import OCRCorrectionService
# from services.level3_hybrid_service import Level3HybridOCRService


# class OCRPipelineService:
#     """
#     Astra-OCR optimized hierarchical OCR pipeline.

#     LEVEL 1:
#         Surya OCR

#     LEVEL 2:
#         Existing OCRCorrectionService
#         - Calculates Level 1 quality
#         - Decides whether correction is required
#         - Runs enhanced / threshold OCR when required
#         - Applies post-OCR corrections

#     LEVEL 3:
#         Existing OCR.space + Gemini hybrid
#         - ONLY executed when final Level 2 quality is below 90

#     Other OCR services are intentionally unchanged.
#     """

#     def __init__(
#         self,
#         output_dir="output/pipeline",
#         quality_threshold=90.0
#     ):
#         self.output_dir = Path(output_dir)
#         self.output_dir.mkdir(parents=True, exist_ok=True)

#         # Level 3 is triggered only below 90.
#         self.quality_threshold = float(quality_threshold)

#         # Existing services
#         self.preprocessor = ImagePreprocessor()
#         self.surya = SuryaOCRService()
#         self.correction_service = OCRCorrectionService()

#         # DO NOT MODIFY Level 3.
#         self.level3 = Level3HybridOCRService()

#     # =========================================================
#     # QUALITY HELPERS
#     # =========================================================

#     @staticmethod
#     def get_quality_score(quality):
#         """Safely extract a numeric quality score."""

#         if not quality:
#             return 0.0

#         try:
#             return float(
#                 quality.get("quality_score", 0.0)
#             )
#         except (TypeError, ValueError):
#             return 0.0

#     @staticmethod
#     def get_quality_status(quality):
#         """Safely extract quality status."""

#         if not quality:
#             return "unknown"

#         return quality.get("status", "unknown")

#     # =========================================================
#     # PROCESS ONE PAGE
#     # =========================================================

#     def process_page(
#         self,
#         image_path,
#         page_number,
#         preprocessing_outputs=None,
#         expected_language=None
#     ):
#         """
#         Process one page.

#         Flow:

#             Image
#               ↓
#             Preprocessing
#               ↓
#             Level 1 — Surya
#               ↓
#             Existing Level 2 correction service
#               ↓
#             Level 2 >= 90?
#               ├── YES → FINAL
#               └── NO  → Level 3

#         The correction service remains responsible for deciding
#         whether Level 2 OCR reruns are actually needed.
#         """

#         image_path = Path(image_path)

#         if not image_path.exists():
#             raise FileNotFoundError(
#                 f"Image not found: {image_path}"
#             )

#         # =====================================================
#         # PAGE HEADER
#         # =====================================================

#         print("\n")
#         print("=" * 70)
#         print(f"ASTRA-OCR PAGE {page_number}")
#         print("=" * 70)

#         # =====================================================
#         # PREPROCESSING
#         # =====================================================

#         print("\n")
#         print("=" * 70)
#         print("PREPROCESSING")
#         print("=" * 70)

#         # Reuse preprocessing when the caller already supplied it.
#         if preprocessing_outputs is None:
#             preprocessing_outputs = (
#                 self.preprocessor.preprocess(
#                     image_path,
#                     page_number
#                 )
#             )

#         for name, path in preprocessing_outputs.items():
#             print(f"{name:12} : {path}")

#         # =====================================================
#         # LEVEL 1 — SURYA OCR
#         # =====================================================

#         print("\n")
#         print("=" * 70)
#         print("LEVEL 1 — SURYA OCR")
#         print("=" * 70)

#         level1_output_dir = (
#             self.output_dir
#             / f"page_{page_number:03d}"
#             / "level1"
#         )

#         level1_output_dir.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         original_image = (
#             preprocessing_outputs.get("original")
#         )

#         if not original_image:
#             original_image = str(image_path)

#         print(f"Level 1 input : {original_image}")

#         level1_result = self.surya.run_ocr(
#             original_image,
#             output_dir=str(level1_output_dir)
#         )

#         print(
#             f"Level 1 blocks : "
#             f"{level1_result.get('total_blocks', 0)}"
#         )

#         # =====================================================
#         # LEVEL 2 — EXISTING OCR CORRECTION
#         # =====================================================

#         print("\n")
#         print("=" * 70)
#         print("LEVEL 2 — OCR SELF-CORRECTION")
#         print("=" * 70)

#         # IMPORTANT:
#         # We do NOT calculate quality ourselves here.
#         # OCRCorrectionService already owns this logic.
#         #
#         # This fixes the previous error:
#         #
#         # OCRQualityService.calculate_quality()
#         # got an unexpected keyword argument 'text_blocks'
#         #
#         correction_result = (
#             self.correction_service.correct_page(
#                 image_path=original_image,
#                 preprocessing_outputs=preprocessing_outputs,
#                 initial_result=level1_result,
#                 page_number=page_number,
#                 expected_language=expected_language
#             )
#         )

#         # =====================================================
#         # LEVEL 1 QUALITY
#         # =====================================================

#         original_info = correction_result.get(
#             "original",
#             {}
#         )

#         level1_quality = original_info.get(
#             "quality",
#             {}
#         )

#         level1_score = self.get_quality_score(
#             level1_quality
#         )

#         level1_status = self.get_quality_status(
#             level1_quality
#         )

#         print("\n")
#         print(
#             f"Level 1 quality : "
#             f"{level1_score:.2f}"
#         )

#         print(
#             f"Level 1 status  : "
#             f"{level1_status}"
#         )

#         # =====================================================
#         # LEVEL 2 RESULT
#         # =====================================================

#         level2_result = correction_result.get(
#             "final_result"
#         )

#         level2_quality = correction_result.get(
#             "final_quality",
#             {}
#         )

#         level2_score = self.get_quality_score(
#             level2_quality
#         )

#         level2_status = self.get_quality_status(
#             level2_quality
#         )

#         # =====================================================
#         # LEVEL 2 FLAGS
#         # =====================================================

#         ocr_rerun_attempted = bool(
#             correction_result.get(
#                 "ocr_rerun_attempted",
#                 False
#             )
#         )

#         post_ocr_correction_applied = bool(
#             correction_result.get(
#                 "post_ocr_correction_applied",
#                 False
#             )
#         )

#         selected_level2 = correction_result.get(
#             "selected",
#             "original"
#         )

#         detected_languages = correction_result.get(
#             "detected_languages",
#             []
#         )

#         # =====================================================
#         # LEVEL 2 REPORT
#         # =====================================================

#         print("\n")
#         print(
#             f"Level 2 OCR rerun : "
#             f"{ocr_rerun_attempted}"
#         )

#         print(
#             f"Level 2 selected  : "
#             f"{selected_level2}"
#         )

#         print(
#             f"Level 2 quality   : "
#             f"{level2_score:.2f}"
#         )

#         print(
#             f"Level 2 status    : "
#             f"{level2_status}"
#         )

#         # =====================================================
#         # LEVEL 3 DECISION
#         # =====================================================

#         # IMPORTANT:
#         # Level 3 is triggered ONLY from the final Level 2 score.
#         level3_required = (
#             level2_score < self.quality_threshold
#         )

#         print("\n")
#         print(
#             f"Level 3 required : "
#             f"{level3_required}"
#         )

#         print(
#             f"Level 3 threshold: "
#             f"{self.quality_threshold:.2f}"
#         )

#         # =====================================================
#         # FINAL LEVEL 2
#         # =====================================================

#         if not level3_required:

#             print("\n")
#             print("=" * 70)
#             print("FINAL RESULT — LEVEL 2")
#             print("=" * 70)

#             if level1_score >= self.quality_threshold:
#                 print(
#                     f"Level 1 was already "
#                     f"{level1_score:.2f} >= "
#                     f"{self.quality_threshold:.2f}"
#                 )
#             else:
#                 print(
#                     f"Level 2 improved/finalized result "
#                     f"at {level2_score:.2f}"
#                 )

#             print("Level 3 not required.")

#             # If correction service selected original and made no
#             # post-OCR changes, this is effectively the Level 1
#             # result even though the correction service was used
#             # to obtain the authoritative quality information.
#             if (
#                 selected_level2 == "original"
#                 and not ocr_rerun_attempted
#                 and not post_ocr_correction_applied
#             ):
#                 final_level = 1
#                 final_source = "surya"
#                 final_result = level1_result
#                 final_quality = level1_quality

#                 print(
#                     "Final result is the original "
#                     "Level 1 Surya output."
#                 )
#             else:
#                 final_level = 2
#                 final_source = (
#                     f"surya_correction:"
#                     f"{selected_level2}"
#                 )
#                 final_result = level2_result
#                 final_quality = level2_quality

#             return {
#                 "page_number": page_number,

#                 "final_level": final_level,

#                 "final_source": final_source,

#                 "final_result": final_result,

#                 "final_quality": final_quality,

#                 "detected_languages": detected_languages,

#                 "preprocessing_outputs": (
#                     preprocessing_outputs
#                 ),

#                 "level1": {
#                     "result": level1_result,
#                     "quality": level1_quality
#                 },

#                 "level2": correction_result,

#                 "level3": None,

#                 "level3_attempted": False
#             }

#         # =====================================================
#         # LEVEL 3 — OCR.SPACE + GEMINI
#         # =====================================================

#         print("\n")
#         print("=" * 70)
#         print("LEVEL 3 — OCR.SPACE + GEMINI HYBRID")
#         print("=" * 70)

#         print(
#             f"Level 2 quality "
#             f"{level2_score:.2f} is below "
#             f"threshold "
#             f"{self.quality_threshold:.2f}"
#         )

#         print("Escalating to Level 3...")

#         # =====================================================
#         # RUN LEVEL 3
#         # =====================================================

#         # Existing Level 3 call is intentionally unchanged.
#         level3_result = self.level3.run(
#             input_path=str(original_image),
#             page_number=page_number
#         )

#         # =====================================================
#         # LEVEL 3 FINAL RESULT
#         # =====================================================

#         level3_final_result = level3_result.get(
#             "final_result"
#         )

#         level3_final_quality = level3_result.get(
#             "final_quality",
#             {}
#         )

#         level3_score = self.get_quality_score(
#             level3_final_quality
#         )

#         level3_source = level3_result.get(
#             "selected_source",
#             level3_result.get(
#                 "source",
#                 "level3"
#             )
#         )

#         # =====================================================
#         # FINAL LEVEL 3 REPORT
#         # =====================================================

#         print("\n")
#         print("=" * 70)
#         print("FINAL RESULT — LEVEL 3")
#         print("=" * 70)

#         print(
#             f"Level 3 source  : "
#             f"{level3_source}"
#         )

#         print(
#             f"Level 3 quality : "
#             f"{level3_score:.2f}"
#         )

#         return {
#             "page_number": page_number,

#             "final_level": 3,

#             "final_source": (
#                 f"level3:{level3_source}"
#             ),

#             "final_result": level3_final_result,

#             "final_quality": level3_final_quality,

#             "detected_languages": detected_languages,

#             "preprocessing_outputs": (
#                 preprocessing_outputs
#             ),

#             "level1": {
#                 "result": level1_result,
#                 "quality": level1_quality
#             },

#             "level2": correction_result,

#             "level3": level3_result,

#             "level3_attempted": True
#         }

#     # =========================================================
#     # PROCESS MULTIPLE PAGES
#     # =========================================================

#     def process_pages(
#         self,
#         image_paths,
#         preprocessing_outputs_list=None,
#         expected_language=None
#     ):
#         """
#         Process multiple rendered pages.

#         preprocessing_outputs_list is optional.

#         If supplied, it must contain the preprocessing
#         dictionary corresponding to each image.
#         """

#         results = []

#         for index, image_path in enumerate(image_paths):

#             page_number = index + 1

#             current_preprocessing = None

#             if (
#                 preprocessing_outputs_list
#                 and index < len(
#                     preprocessing_outputs_list
#                 )
#             ):
#                 current_preprocessing = (
#                     preprocessing_outputs_list[index]
#                 )

#             try:
#                 result = self.process_page(
#                     image_path=image_path,
#                     page_number=page_number,
#                     preprocessing_outputs=(
#                         current_preprocessing
#                     ),
#                     expected_language=expected_language
#                 )

#                 results.append(result)

#             except Exception as exc:

#                 print("\n")
#                 print("=" * 70)
#                 print(
#                     f"ERROR — PAGE {page_number}"
#                 )
#                 print("=" * 70)

#                 print(
#                     f"{type(exc).__name__}: "
#                     f"{exc}"
#                 )

#                 results.append({
#                     "page_number": page_number,

#                     "final_level": None,

#                     "final_source": "error",

#                     "final_result": None,

#                     "final_quality": {
#                         "quality_score": 0.0,
#                         "status": "error"
#                     },

#                     "error": str(exc)
#                 })

#         return results

#     # =========================================================
#     # DOCUMENT SUMMARY
#     # =========================================================

#     @staticmethod
#     def build_document_summary(page_results):
#         """
#         Build document-level OCR summary.
#         """

#         summary = {
#             "total_pages": len(page_results),

#             "level1_pages": 0,

#             "level2_pages": 0,

#             "level3_pages": 0,

#             "error_pages": 0,

#             "average_quality": 0.0
#         }

#         quality_scores = []

#         for result in page_results:

#             level = result.get(
#                 "final_level"
#             )

#             if level == 1:

#                 summary["level1_pages"] += 1

#             elif level == 2:

#                 summary["level2_pages"] += 1

#             elif level == 3:

#                 summary["level3_pages"] += 1

#             else:

#                 summary["error_pages"] += 1

#             quality = result.get(
#                 "final_quality",
#                 {}
#             )

#             try:

#                 score = float(
#                     quality.get(
#                         "quality_score",
#                         0
#                     )
#                 )

#                 if score > 0:
#                     quality_scores.append(score)

#             except (
#                 TypeError,
#                 ValueError
#             ):
#                 pass

#         if quality_scores:

#             summary["average_quality"] = round(
#                 sum(quality_scores)
#                 / len(quality_scores),
#                 2
#             )

#         return summary






































































#####final change 





























from pathlib import Path

from services.surya_ocr_service import SuryaOCRService
from services.preprocessing_service import ImagePreprocessor
from services.correction_service import OCRCorrectionService
from services.level3_hybrid_service import Level3HybridOCRService


class OCRPipelineService:
    """
    Astra-OCR optimized hierarchical OCR pipeline.

    LEVEL 1:
        Surya OCR

    LEVEL 2:
        Existing OCRCorrectionService
        - Calculates Level 1 quality
        - Decides whether correction is required
        - Runs enhanced / threshold OCR when required
        - Applies post-OCR corrections

    LEVEL 3:
        Existing OCR.space + Gemini hybrid
        - ONLY executed when final Level 2 quality is below 90

    Other OCR services are intentionally unchanged.
    """

    def __init__(
        self,
        output_dir="output/pipeline",
        quality_threshold=90.0
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Level 3 is triggered only below 90.
        self.quality_threshold = float(quality_threshold)

        # Existing services
        self.preprocessor = ImagePreprocessor()
        self.surya = SuryaOCRService()
        self.correction_service = OCRCorrectionService()

        # DO NOT MODIFY Level 3.
        self.level3 = Level3HybridOCRService()

    # =========================================================
    # QUALITY HELPERS
    # =========================================================

    @staticmethod
    def get_quality_score(quality):
        """Safely extract a numeric quality score."""

        if not quality:
            return 0.0

        try:
            return float(
                quality.get("quality_score", 0.0)
            )
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def get_quality_status(quality):
        """Safely extract quality status."""

        if not quality:
            return "unknown"

        return quality.get("status", "unknown")

    # =========================================================
    # PROCESS ONE PAGE
    # =========================================================

    def process_page(
        self,
        image_path,
        page_number,
        preprocessing_outputs=None,
        expected_language=None
    ):
        """
        Process one page.

        Flow:

            Image
              ↓
            Preprocessing
              ↓
            Level 1 — Surya
              ↓
            Existing Level 2 correction service
              ↓
            Level 2 >= 90?
              ├── YES → FINAL
              └── NO  → Level 3

        The correction service remains responsible for deciding
        whether Level 2 OCR reruns are actually needed.
        """

        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        # =====================================================
        # PAGE HEADER
        # =====================================================

        print("\n")
        print("=" * 70)
        print(f"ASTRA-OCR PAGE {page_number}")
        print("=" * 70)

        # =====================================================
        # PREPROCESSING
        # =====================================================

        print("\n")
        print("=" * 70)
        print("PREPROCESSING")
        print("=" * 70)

        # Reuse preprocessing when the caller already supplied it.
        if preprocessing_outputs is None:
            preprocessing_outputs = (
                self.preprocessor.preprocess(
                    image_path,
                    page_number
                )
            )

        for name, path in preprocessing_outputs.items():
            print(f"{name:12} : {path}")

        # =====================================================
        # LEVEL 1 — SURYA OCR
        # =====================================================

        print("\n")
        print("=" * 70)
        print("LEVEL 1 — SURYA OCR")
        print("=" * 70)

        level1_output_dir = (
            self.output_dir
            / f"page_{page_number:03d}"
            / "level1"
        )

        level1_output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        original_image = (
            preprocessing_outputs.get("original")
        )

        if not original_image:
            original_image = str(image_path)

        print(f"Level 1 input : {original_image}")

        level1_result = self.surya.run_ocr(
            original_image,
            output_dir=str(level1_output_dir)
        )

        print(
            f"Level 1 blocks : "
            f"{level1_result.get('total_blocks', 0)}"
        )

        # =====================================================
        # LEVEL 2 — EXISTING OCR CORRECTION
        # =====================================================

        print("\n")
        print("=" * 70)
        print("LEVEL 2 — OCR SELF-CORRECTION")
        print("=" * 70)

        # IMPORTANT:
        # We do NOT calculate quality ourselves here.
        # OCRCorrectionService already owns this logic.
        #
        # This fixes the previous error:
        #
        # OCRQualityService.calculate_quality()
        # got an unexpected keyword argument 'text_blocks'
        #
        correction_result = (
            self.correction_service.correct_page(
                image_path=original_image,
                preprocessing_outputs=preprocessing_outputs,
                initial_result=level1_result,
                page_number=page_number,
                expected_language=expected_language
            )
        )

        # =====================================================
        # LEVEL 1 QUALITY
        # =====================================================

        original_info = correction_result.get(
            "original",
            {}
        )

        level1_quality = original_info.get(
            "quality",
            {}
        )

        level1_score = self.get_quality_score(
            level1_quality
        )

        level1_status = self.get_quality_status(
            level1_quality
        )

        print("\n")
        print(
            f"Level 1 quality : "
            f"{level1_score:.2f}"
        )

        print(
            f"Level 1 status  : "
            f"{level1_status}"
        )

        # =====================================================
        # LEVEL 2 RESULT
        # =====================================================

        level2_result = correction_result.get(
            "final_result"
        )

        level2_quality = correction_result.get(
            "final_quality",
            {}
        )

        level2_score = self.get_quality_score(
            level2_quality
        )

        level2_status = self.get_quality_status(
            level2_quality
        )

        # =====================================================
        # LEVEL 2 FLAGS
        # =====================================================

        ocr_rerun_attempted = bool(
            correction_result.get(
                "ocr_rerun_attempted",
                False
            )
        )

        post_ocr_correction_applied = bool(
            correction_result.get(
                "post_ocr_correction_applied",
                False
            )
        )

        selected_level2 = correction_result.get(
            "selected",
            "original"
        )

        detected_languages = correction_result.get(
            "detected_languages",
            []
        )

        # =====================================================
        # LEVEL 2 REPORT
        # =====================================================

        print("\n")
        print(
            f"Level 2 OCR rerun : "
            f"{ocr_rerun_attempted}"
        )

        print(
            f"Level 2 selected  : "
            f"{selected_level2}"
        )

        print(
            f"Level 2 quality   : "
            f"{level2_score:.2f}"
        )

        print(
            f"Level 2 status    : "
            f"{level2_status}"
        )

        # =====================================================
        # LEVEL 3 DECISION
        # =====================================================

        # IMPORTANT:
        # Level 3 is triggered ONLY from the final Level 2 score.
        level3_required = (
            level2_score < self.quality_threshold
        )

        print("\n")
        print(
            f"Level 3 required : "
            f"{level3_required}"
        )

        print(
            f"Level 3 threshold: "
            f"{self.quality_threshold:.2f}"
        )

        # =====================================================
        # FINAL LEVEL 2
        # =====================================================

        if not level3_required:

            print("\n")
            print("=" * 70)
            print("FINAL RESULT — LEVEL 2")
            print("=" * 70)

            if level1_score >= self.quality_threshold:
                print(
                    f"Level 1 was already "
                    f"{level1_score:.2f} >= "
                    f"{self.quality_threshold:.2f}"
                )
            else:
                print(
                    f"Level 2 improved/finalized result "
                    f"at {level2_score:.2f}"
                )

            print("Level 3 not required.")

            # If correction service selected original and made no
            # post-OCR changes, this is effectively the Level 1
            # result even though the correction service was used
            # to obtain the authoritative quality information.
            if (
                selected_level2 == "original"
                and not ocr_rerun_attempted
                and not post_ocr_correction_applied
            ):
                final_level = 1
                final_source = "surya"
                final_result = level1_result
                final_quality = level1_quality

                print(
                    "Final result is the original "
                    "Level 1 Surya output."
                )
            else:
                final_level = 2
                final_source = (
                    f"surya_correction:"
                    f"{selected_level2}"
                )
                final_result = level2_result
                final_quality = level2_quality

            return {
                "page_number": page_number,

                "final_level": final_level,

                "final_source": final_source,

                "final_result": final_result,

                "final_quality": final_quality,

                "detected_languages": detected_languages,

                "preprocessing_outputs": (
                    preprocessing_outputs
                ),

                "level1": {
                    "result": level1_result,
                    "quality": level1_quality
                },

                "level2": correction_result,

                "level3": None,

                "level3_attempted": False
            }

        # =====================================================
        # LEVEL 3 — OCR.SPACE + GEMINI
        # =====================================================

        print("\n")
        print("=" * 70)
        print("LEVEL 3 — OCR.SPACE + GEMINI HYBRID")
        print("=" * 70)

        print(
            f"Level 2 quality "
            f"{level2_score:.2f} is below "
            f"threshold "
            f"{self.quality_threshold:.2f}"
        )

        print("Escalating to Level 3...")

        # =====================================================
        # RUN LEVEL 3
        # =====================================================

        # Existing Level 3 call is intentionally unchanged.
        level3_result = self.level3.run(
            input_path=str(original_image),
            page_number=page_number
        )

        # =====================================================
        # LEVEL 3 FINAL RESULT
        # =====================================================

        level3_final_result = level3_result.get(
            "final_result"
        )

        level3_final_quality = level3_result.get(
            "final_quality",
            {}
        )

        level3_score = self.get_quality_score(
            level3_final_quality
        )

        level3_source = level3_result.get(
            "selected_source",
            level3_result.get(
                "source",
                "level3"
            )
        )

        # =====================================================
        # FINAL LEVEL 3 REPORT
        # =====================================================

        print("\n")
        print("=" * 70)
        print("FINAL RESULT — LEVEL 3")
        print("=" * 70)

        print(
            f"Level 3 source  : "
            f"{level3_source}"
        )

        print(
            f"Level 3 quality : "
            f"{level3_score:.2f}"
        )

        return {
            "page_number": page_number,

            "final_level": 3,

            "final_source": (
                f"level3:{level3_source}"
            ),

            "final_result": level3_final_result,

            "final_quality": level3_final_quality,

            "detected_languages": detected_languages,

            "preprocessing_outputs": (
                preprocessing_outputs
            ),

            "level1": {
                "result": level1_result,
                "quality": level1_quality
            },

            "level2": correction_result,

            "level3": level3_result,

            "level3_attempted": True
        }

    # =========================================================
    # PROCESS MULTIPLE PAGES
    # =========================================================

    def process_pages(
        self,
        image_paths,
        preprocessing_outputs_list=None,
        expected_language=None
    ):
        """
        Process multiple rendered pages.

        preprocessing_outputs_list is optional.

        If supplied, it must contain the preprocessing
        dictionary corresponding to each image.
        """

        results = []

        for index, image_path in enumerate(image_paths):

            page_number = index + 1

            current_preprocessing = None

            if (
                preprocessing_outputs_list
                and index < len(
                    preprocessing_outputs_list
                )
            ):
                current_preprocessing = (
                    preprocessing_outputs_list[index]
                )

            try:
                result = self.process_page(
                    image_path=image_path,
                    page_number=page_number,
                    preprocessing_outputs=(
                        current_preprocessing
                    ),
                    expected_language=expected_language
                )

                results.append(result)

            except Exception as exc:

                print("\n")
                print("=" * 70)
                print(
                    f"ERROR — PAGE {page_number}"
                )
                print("=" * 70)

                print(
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

                results.append({
                    "page_number": page_number,

                    "final_level": None,

                    "final_source": "error",

                    "final_result": None,

                    "final_quality": {
                        "quality_score": 0.0,
                        "status": "error"
                    },

                    "error": str(exc)
                })

        return results

    # =========================================================
    # DOCUMENT SUMMARY
    # =========================================================

    @staticmethod
    def build_document_summary(page_results):
        """
        Build document-level OCR summary.
        """

        summary = {
            "total_pages": len(page_results),

            "level1_pages": 0,

            "level2_pages": 0,

            "level3_pages": 0,

            "error_pages": 0,

            "average_quality": 0.0
        }

        quality_scores = []

        for result in page_results:

            level = result.get(
                "final_level"
            )

            if level == 1:

                summary["level1_pages"] += 1

            elif level == 2:

                summary["level2_pages"] += 1

            elif level == 3:

                summary["level3_pages"] += 1

            else:

                summary["error_pages"] += 1

            quality = result.get(
                "final_quality",
                {}
            )

            try:

                score = float(
                    quality.get(
                        "quality_score",
                        0
                    )
                )

                if score > 0:
                    quality_scores.append(score)

            except (
                TypeError,
                ValueError
            ):
                pass

        if quality_scores:

            summary["average_quality"] = round(
                sum(quality_scores)
                / len(quality_scores),
                2
            )

        return summary
