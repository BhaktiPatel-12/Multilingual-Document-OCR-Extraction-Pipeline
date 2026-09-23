# from pathlib import Path

# from services.surya_ocr_service import SuryaOCRService
# from services.quality_service import OCRQualityService
# from services.ocr_text_corrector import apply_corrections


# class OCRCorrectionService:

#     def __init__(
#         self,
#         output_dir="output/corrected"
#     ):
#         self.output_dir = Path(output_dir)
#         self.output_dir.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         self.surya = SuryaOCRService()
#         self.quality_service = OCRQualityService()

#     # =========================================================
#     # LANGUAGE NORMALIZATION
#     # =========================================================

#     def normalize_language(self, language):
#         """
#         Normalize language names used by different
#         Astra-OCR services.
#         """

#         if not language:
#             return "unknown"

#         language = str(
#             language
#         ).lower().strip()

#         mapping = {
#             "eng": "en",
#             "english": "en",
#             "en": "en",

#             "hin": "hin",
#             "hindi": "hin",

#             "guj": "guj",
#             "gujarati": "guj",

#             "mixed": "mixed",
#             "unknown": "unknown"
#         }

#         return mapping.get(
#             language,
#             language
#         )

#     # =========================================================
#     # GET DETECTED LANGUAGES
#     # =========================================================

#     def get_detected_languages(
#         self,
#         ocr_result
#     ):
#         """
#         Determine all languages present in the OCR result.

#         Mixed blocks are inspected through their text so that
#         Hindi + English documents are correctly reported.
#         """

#         detected = set()

#         if not ocr_result:
#             return []

#         results = ocr_result.get(
#             "results",
#             []
#         )

#         for item in results:

#             language = self.normalize_language(
#                 item.get(
#                     "language",
#                     "unknown"
#                 )
#             )

#             if language in {
#                 "en",
#                 "hin",
#                 "guj"
#             }:
#                 detected.add(language)

#             elif language == "mixed":

#                 text = item.get(
#                     "text",
#                     ""
#                 )

#                 text_languages = (
#                     self._detect_languages_from_text(
#                         text
#                     )
#                 )

#                 detected.update(
#                     text_languages
#                 )

#         language_order = [
#             "en",
#             "hin",
#             "guj"
#         ]

#         return [
#             language
#             for language in language_order
#             if language in detected
#         ]

#     # =========================================================
#     # DETECT LANGUAGES FROM TEXT
#     # =========================================================

#     def _detect_languages_from_text(
#         self,
#         text
#     ):
#         """
#         Detect supported scripts directly from OCR text.
#         """

#         if not text:
#             return set()

#         detected = set()

#         for character in text:

#             code = ord(character)

#             # Devanagari
#             if 0x0900 <= code <= 0x097F:
#                 detected.add("hin")

#             # Gujarati
#             elif 0x0A80 <= code <= 0x0AFF:
#                 detected.add("guj")

#             # Latin
#             elif (
#                 "A" <= character <= "Z"
#                 or "a" <= character <= "z"
#             ):
#                 detected.add("en")

#         return detected

#     # =========================================================
#     # QUALITY CALCULATION
#     # =========================================================

#     def calculate_result_quality(
#         self,
#         ocr_result,
#         expected_language=None
#     ):
#         """
#         Calculate quality using OCRQualityService.
#         """

#         if not ocr_result:
#             return {
#                 "quality_score": 0.0,
#                 "status": "retry",
#                 "text_score": 0.0,
#                 "language_score": 0.0,
#                 "character_score": 0.0,
#                 "coverage_score": 0.0,
#                 "confidence_score": 0.0
#             }

#         results = ocr_result.get(
#             "results",
#             []
#         )

#         # -----------------------------------------------------
#         # FULL TEXT
#         # -----------------------------------------------------

#         text_parts = []

#         for item in results:

#             text = item.get(
#                 "text",
#                 ""
#             )

#             if text:
#                 text_parts.append(
#                     str(text)
#                 )

#         full_text = "\n".join(
#             text_parts
#         )

#         # -----------------------------------------------------
#         # QUALITY BLOCKS
#         # -----------------------------------------------------

#         quality_blocks = []

#         for item in results:

#             block = {
#                 "text": item.get(
#                     "text",
#                     ""
#                 ),

#                 "language": self.normalize_language(
#                     item.get(
#                         "language",
#                         "unknown"
#                     )
#                 ),

#                 "bbox": item.get(
#                     "bbox"
#                 ),

#                 "confidence": item.get(
#                     "confidence",
#                     0.0
#                 )
#             }

#             if "layout_confidence" in item:

#                 block[
#                     "layout_confidence"
#                 ] = item[
#                     "layout_confidence"
#                 ]

#             quality_blocks.append(
#                 block
#             )

#         # -----------------------------------------------------
#         # PAGE DIMENSIONS
#         # -----------------------------------------------------

#         page_width = ocr_result.get(
#             "page_width"
#         )

#         page_height = ocr_result.get(
#             "page_height"
#         )

#         # If not directly available, inspect results.
#         if page_width is None:

#             for item in results:

#                 if item.get(
#                     "page_width"
#                 ) is not None:

#                     page_width = item[
#                         "page_width"
#                     ]

#                     break

#         if page_height is None:

#             for item in results:

#                 if item.get(
#                     "page_height"
#                 ) is not None:

#                     page_height = item[
#                         "page_height"
#                     ]

#                     break

#         # -----------------------------------------------------
#         # IMAGE BBOX FALLBACK
#         # -----------------------------------------------------

#         if (
#             page_width is None
#             or page_height is None
#         ):

#             for item in results:

#                 image_bbox = item.get(
#                     "image_bbox"
#                 )

#                 if (
#                     image_bbox
#                     and len(image_bbox) >= 4
#                 ):

#                     page_width = image_bbox[2]
#                     page_height = image_bbox[3]

#                     break

#         # -----------------------------------------------------
#         # LAYOUT CONFIDENCE
#         # -----------------------------------------------------

#         layout_confidences = []

#         for item in results:

#             value = item.get(
#                 "layout_confidence"
#             )

#             if value is not None:

#                 try:
#                     layout_confidences.append(
#                         float(value)
#                     )

#                 except (
#                     TypeError,
#                     ValueError
#                 ):
#                     pass

#         layout_confidence = None

#         if layout_confidences:

#             layout_confidence = (
#                 sum(layout_confidences)
#                 / len(layout_confidences)
#             )

#         # -----------------------------------------------------
#         # QUALITY SERVICE
#         # -----------------------------------------------------

#         return self.quality_service.calculate_quality(
#             text=full_text,
#             blocks=quality_blocks,
#             page_width=page_width,
#             page_height=page_height,
#             expected_language=expected_language,
#             layout_confidence=layout_confidence
#         )

#     # =========================================================
#     # SHOULD CORRECT
#     # =========================================================

#     def should_correct(
#         self,
#         quality
#     ):
#         if not quality:
#             return True

#         return quality.get(
#             "status",
#             "retry"
#         ) in {
#             "review",
#             "retry"
#         }

    

#     # =========================================================
#     # SELECT BEST RESULT
#     # =========================================================

#     def select_better_result(
#         self,
#         original_result,
#         original_quality,
#         corrected_result,
#         corrected_quality
#     ):
#         original_score = float(
#             original_quality.get(
#                 "quality_score",
#                 0
#             )
#         )

#         corrected_score = float(
#             corrected_quality.get(
#                 "quality_score",
#                 0
#             )
#         )

#         if corrected_score > original_score:

#             return (
#                 "corrected",
#                 corrected_result,
#                 corrected_quality
#             )

#         return (
#             "original",
#             original_result,
#             original_quality
#         )

#     # =========================================================
#     # POST-OCR TEXT CORRECTION
#     # =========================================================

#     def apply_post_ocr_corrections(
#         self,
#         final_result
#     ):
#         """
#         Apply safe post-OCR corrections.

#         Corrections include:

#         1. Fixed template labels using fuzzy matching.
#         2. Marks-table arithmetic validation.
#         3. Low-confidence corrections are flagged instead
#            of being guessed.

#         Free-form names, roll numbers and similar values
#         are not modified.
#         """

#         corrected_result, report = apply_corrections(
#             final_result
#         )

#         # -----------------------------------------------------
#         # LABEL CORRECTIONS
#         # -----------------------------------------------------

#         if report["labels_corrected"]:

#             print(
#                 f"\nAuto-corrected "
#                 f"{len(report['labels_corrected'])} "
#                 "label(s):"
#             )

#             for correction in report[
#                 "labels_corrected"
#             ]:

#                 print(
#                     f"  {correction['original']!r} -> "
#                     f"{correction['corrected']!r} "
#                     f"(score {correction['score']:.0f})"
#                 )

#         # -----------------------------------------------------
#         # MARKS TABLE CORRECTIONS
#         # -----------------------------------------------------

#         if report["marks_table_issues"]:

#             print(
#                 f"\nCorrected "
#                 f"{len(report['marks_table_issues'])} "
#                 "marks-table value(s):"
#             )

#             for issue in report[
#                 "marks_table_issues"
#             ]:

#                 print(
#                     f"  {issue['subject_code']} "
#                     f"{issue['subject_name']}: "
#                     f"{issue['issue']}"
#                 )

#         # -----------------------------------------------------
#         # MANUAL REVIEW ITEMS
#         # -----------------------------------------------------

#         if report["labels_needing_review"]:

#             print(
#                 f"\n{len(report['labels_needing_review'])} "
#                 "item(s) flagged for manual review "
#                 "(too uncertain to auto-correct):"
#             )

#             for flagged in report[
#                 "labels_needing_review"
#             ]:

#                 print(
#                     f"  {flagged['text']!r} "
#                     f"-- possible match: "
#                     f"{flagged['suggested_label']!r} "
#                     f"(score {flagged['score']:.0f})"
#                 )

#         return corrected_result, report

#     # =========================================================
#     # CORRECT PAGE
#     # =========================================================

#     def correct_page(
#         self,
#         image_path,
#         preprocessing_outputs,
#         initial_result,
#         page_number,
#         expected_language=None
#     ):
#         """
#         Adaptive OCR self-correction.

#         Attempts:

#         1. Original OCR
#         2. Enhanced preprocessing + OCR
#         3. Threshold preprocessing + OCR

#         The highest-quality OCR candidate is selected.

#         After candidate selection, safe post-OCR corrections
#         are applied to the selected result.

#         IMPORTANT:
#         Final quality is recalculated AFTER post-OCR corrections
#         so that final_quality represents the actual final text.
#         """

#         # =====================================================
#         # INITIAL QUALITY
#         # =====================================================

#         initial_quality = (
#             self.calculate_result_quality(
#                 initial_result,
#                 expected_language
#             )
#         )

#         print(
#             f"Initial quality score : "
#             f"{initial_quality['quality_score']}"
#         )

#         print(
#             f"Initial status       : "
#             f"{initial_quality['status']}"
#         )

#         # =====================================================
#         # IF GOOD, SKIP OCR RE-RUN
#         # BUT STILL APPLY POST-OCR CORRECTION
#         # =====================================================

#         if not self.should_correct(
#             initial_quality
#         ):

#             print(
#                 "OCR quality is good. "
#                 "No candidate re-run required."
#             )

#             corrected_result, correction_report = (
#                 self.apply_post_ocr_corrections(
#                     initial_result
#                 )
#             )

#             # -------------------------------------------------
#             # RECALCULATE QUALITY AFTER TEXT CORRECTION
#             # -------------------------------------------------

#             final_quality = (
#                 self.calculate_result_quality(
#                     corrected_result,
#                     expected_language
#                 )
#             )

#             # -------------------------------------------------
#             # REPORT QUALITY CHANGE
#             # -------------------------------------------------

#             initial_score = float(
#                 initial_quality.get(
#                     "quality_score",
#                     0
#                 )
#             )

#             final_score = float(
#                 final_quality.get(
#                     "quality_score",
#                     0
#                 )
#             )

#             if final_score != initial_score:

#                 print(
#                     f"\nPost-OCR quality update : "
#                     f"{initial_score:.2f} -> "
#                     f"{final_score:.2f}"
#                 )

#             else:

#                 print(
#                     f"\nPost-OCR quality unchanged : "
#                     f"{final_score:.2f}"
#                 )

#             # -------------------------------------------------
#             # LANGUAGE RESULT
#             # -------------------------------------------------

#             detected_languages = (
#                 self.get_detected_languages(
#                     corrected_result
#                 )
#             )

#             post_ocr_correction_applied = (
#                 bool(
#                     correction_report.get(
#                         "labels_corrected"
#                     )
#                 )
#                 or bool(
#                     correction_report.get(
#                         "marks_table_issues"
#                     )
#                 )
#             )

#             return {
#                 "correction_attempted": (
#                     post_ocr_correction_applied
#                 ),

#                 "ocr_rerun_attempted": False,

#                 "post_ocr_correction_applied":
#                     post_ocr_correction_applied,

#                 "selected": "original",

#                 "original": {
#                     "result": initial_result,
#                     "quality": initial_quality
#                 },

#                 "corrected": [],

#                 "final_result": corrected_result,

#                 "final_quality": final_quality,

#                 "text_correction_report":
#                     correction_report,

#                 "detected_languages":
#                     detected_languages
#             }

#         # =====================================================
#         # OCR RE-RUN REQUIRED
#         # =====================================================

#         print(
#             "OCR quality requires correction."
#         )

#         # =====================================================
#         # CANDIDATE RESULTS
#         # =====================================================

#         candidates = []

#         # Original candidate
#         candidates.append({
#             "name": "original",
#             "result": initial_result,
#             "quality": initial_quality
#         })

#         # =====================================================
#         # ENHANCED OCR
#         # =====================================================

#         enhanced_image = (
#             preprocessing_outputs.get(
#                 "enhanced"
#             )
#         )

#         if enhanced_image:

#             print(
#                 "\nTrying enhanced preprocessing..."
#             )

#             enhanced_output_dir = (
#                 self.output_dir
#                 / f"page_{page_number:03d}"
#                 / "enhanced"
#             )

#             enhanced_output_dir.mkdir(
#                 parents=True,
#                 exist_ok=True
#             )

#             print(
#                 f"Corrected image : "
#                 f"{enhanced_image}"
#             )

#             print(
#                 f"Correction output : "
#                 f"{enhanced_output_dir}"
#             )

#             enhanced_result = (
#                 self.surya.run_ocr(
#                     enhanced_image,
#                     output_dir=str(
#                         enhanced_output_dir
#                     )
#                 )
#             )

#             enhanced_quality = (
#                 self.calculate_result_quality(
#                     enhanced_result,
#                     expected_language
#                 )
#             )

#             print(
#                 f"Enhanced quality score : "
#                 f"{enhanced_quality['quality_score']}"
#             )

#             print(
#                 f"Enhanced status : "
#                 f"{enhanced_quality['status']}"
#             )

#             candidates.append({
#                 "name": "enhanced",
#                 "result": enhanced_result,
#                 "quality": enhanced_quality
#             })

#         # =====================================================
#         # THRESHOLD OCR
#         # =====================================================

#         threshold_image = (
#             preprocessing_outputs.get(
#                 "threshold"
#             )
#         )

#         if threshold_image:

#             print(
#                 "\nTrying threshold preprocessing..."
#             )

#             threshold_output_dir = (
#                 self.output_dir
#                 / f"page_{page_number:03d}"
#                 / "threshold"
#             )

#             threshold_output_dir.mkdir(
#                 parents=True,
#                 exist_ok=True
#             )

#             print(
#                 f"Threshold image : "
#                 f"{threshold_image}"
#             )

#             print(
#                 f"Correction output : "
#                 f"{threshold_output_dir}"
#             )

#             threshold_result = (
#                 self.surya.run_ocr(
#                     threshold_image,
#                     output_dir=str(
#                         threshold_output_dir
#                     )
#                 )
#             )

#             threshold_quality = (
#                 self.calculate_result_quality(
#                     threshold_result,
#                     expected_language
#                 )
#             )

#             print(
#                 f"Threshold quality score : "
#                 f"{threshold_quality['quality_score']}"
#             )

#             print(
#                 f"Threshold status : "
#                 f"{threshold_quality['status']}"
#             )

#             candidates.append({
#                 "name": "threshold",
#                 "result": threshold_result,
#                 "quality": threshold_quality
#             })

#         # =====================================================
#         # SELECT BEST CANDIDATE
#         # =====================================================

#         best_candidate = max(
#             candidates,
#             key=lambda candidate:
#                 float(
#                     candidate[
#                         "quality"
#                     ].get(
#                         "quality_score",
#                         0
#                     )
#                 )
#         )

#         selected = best_candidate[
#             "name"
#         ]

#         final_result = best_candidate[
#             "result"
#         ]

#         candidate_quality = best_candidate[
#             "quality"
#         ]

#         # =====================================================
#         # CANDIDATE COMPARISON
#         # =====================================================

#         print(
#             "\n========================================"
#         )

#         print(
#             "        CORRECTION COMPARISON"
#         )

#         print(
#             "========================================"
#         )

#         for candidate in candidates:

#             print(
#                 f"{candidate['name']:12} : "
#                 f"{candidate['quality']['quality_score']}"
#             )

#         print(
#             f"\nSelected result : {selected}"
#         )

#         print(
#             f"Selected OCR quality score : "
#             f"{candidate_quality['quality_score']}"
#         )

#         # =====================================================
#         # POST-OCR TEXT CORRECTION
#         # =====================================================

#         final_result, correction_report = (
#             self.apply_post_ocr_corrections(
#                 final_result
#             )
#         )

#         # =====================================================
#         # RECALCULATE FINAL QUALITY
#         #
#         # This is the important fix.
#         #
#         # candidate_quality = quality BEFORE text correction
#         # final_quality     = quality AFTER text correction
#         # =====================================================

#         final_quality = (
#             self.calculate_result_quality(
#                 final_result,
#                 expected_language
#             )
#         )

#         initial_score = float(
#             candidate_quality.get(
#                 "quality_score",
#                 0
#             )
#         )

#         final_score = float(
#             final_quality.get(
#                 "quality_score",
#                 0
#             )
#         )

#         if final_score != initial_score:

#             print(
#                 f"\nPost-OCR quality update : "
#                 f"{initial_score:.2f} -> "
#                 f"{final_score:.2f}"
#             )

#         else:

#             print(
#                 f"\nPost-OCR quality unchanged : "
#                 f"{final_score:.2f}"
#             )

#         # =====================================================
#         # LANGUAGE RESULT
#         # =====================================================

#         detected_languages = (
#             self.get_detected_languages(
#                 final_result
#             )
#         )

#         post_ocr_correction_applied = (
#             bool(
#                 correction_report.get(
#                     "labels_corrected"
#                 )
#             )
#             or bool(
#                 correction_report.get(
#                     "marks_table_issues"
#                 )
#             )
#         )

#         # =====================================================
#         # FINAL RESULT
#         # =====================================================

#         return {
#             "correction_attempted": True,

#             "ocr_rerun_attempted": True,

#             "post_ocr_correction_applied":
#                 post_ocr_correction_applied,

#             "selected": selected,

#             "original": {
#                 "result": initial_result,
#                 "quality": initial_quality
#             },

#             "corrected": candidates[1:],

#             "final_result": final_result,

#             "final_quality": final_quality,

#             "text_correction_report":
#                 correction_report,

#             "detected_languages":
#                 detected_languages
#         }






































# from pathlib import Path

# from services.surya_ocr_service import SuryaOCRService
# from services.quality_service import OCRQualityService
# from services.ocr_text_corrector import apply_corrections


# class OCRCorrectionService:

#     # Stop trying OCR candidates once this quality is reached.
#     QUALITY_TARGET = 90.0

#     def __init__(self, output_dir="output/corrected"):
#         self.output_dir = Path(output_dir)
#         self.output_dir.mkdir(parents=True, exist_ok=True)

#         self.surya = SuryaOCRService()
#         self.quality_service = OCRQualityService()

#     # =========================================================
#     # LANGUAGE NORMALIZATION
#     # =========================================================

#     def normalize_language(self, language):
#         if not language:
#             return "unknown"

#         language = str(language).lower().strip()

#         mapping = {
#             "eng": "en",
#             "english": "en",
#             "en": "en",
#             "hin": "hin",
#             "hindi": "hin",
#             "guj": "guj",
#             "gujarati": "guj",
#             "mixed": "mixed",
#             "unknown": "unknown",
#         }

#         return mapping.get(language, language)

#     # =========================================================
#     # GET DETECTED LANGUAGES
#     # =========================================================

#     def get_detected_languages(self, ocr_result):
#         detected = set()

#         if not ocr_result:
#             return []

#         results = ocr_result.get("results", [])

#         for item in results:
#             language = self.normalize_language(
#                 item.get("language", "unknown")
#             )

#             if language in {"en", "hin", "guj"}:
#                 detected.add(language)

#             elif language == "mixed":
#                 detected.update(
#                     self._detect_languages_from_text(
#                         item.get("text", "")
#                     )
#                 )

#         language_order = ["en", "hin", "guj"]

#         return [
#             language
#             for language in language_order
#             if language in detected
#         ]

#     # =========================================================
#     # DETECT LANGUAGES FROM TEXT
#     # =========================================================

#     def _detect_languages_from_text(self, text):
#         if not text:
#             return set()

#         detected = set()

#         for character in text:
#             code = ord(character)

#             if 0x0900 <= code <= 0x097F:
#                 detected.add("hin")
#             elif 0x0A80 <= code <= 0x0AFF:
#                 detected.add("guj")
#             elif (
#                 "A" <= character <= "Z"
#                 or "a" <= character <= "z"
#             ):
#                 detected.add("en")

#         return detected

#     # =========================================================
#     # QUALITY CALCULATION
#     # =========================================================

#     def calculate_result_quality(
#         self,
#         ocr_result,
#         expected_language=None
#     ):
#         if not ocr_result:
#             return {
#                 "quality_score": 0.0,
#                 "status": "retry",
#                 "text_score": 0.0,
#                 "language_score": 0.0,
#                 "character_score": 0.0,
#                 "coverage_score": 0.0,
#                 "confidence_score": 0.0,
#             }

#         results = ocr_result.get("results", [])

#         text_parts = []

#         for item in results:
#             text = item.get("text", "")
#             if text:
#                 text_parts.append(str(text))

#         full_text = "\n".join(text_parts)

#         quality_blocks = []

#         for item in results:
#             block = {
#                 "text": item.get("text", ""),
#                 "language": self.normalize_language(
#                     item.get("language", "unknown")
#                 ),
#                 "bbox": item.get("bbox"),
#                 "confidence": item.get("confidence", 0.0),
#             }

#             if "layout_confidence" in item:
#                 block["layout_confidence"] = item[
#                     "layout_confidence"
#                 ]

#             quality_blocks.append(block)

#         page_width = ocr_result.get("page_width")
#         page_height = ocr_result.get("page_height")

#         if page_width is None:
#             for item in results:
#                 if item.get("page_width") is not None:
#                     page_width = item["page_width"]
#                     break

#         if page_height is None:
#             for item in results:
#                 if item.get("page_height") is not None:
#                     page_height = item["page_height"]
#                     break

#         if page_width is None or page_height is None:
#             for item in results:
#                 image_bbox = item.get("image_bbox")

#                 if image_bbox and len(image_bbox) >= 4:
#                     page_width = image_bbox[2]
#                     page_height = image_bbox[3]
#                     break

#         layout_confidences = []

#         for item in results:
#             value = item.get("layout_confidence")

#             if value is not None:
#                 try:
#                     layout_confidences.append(float(value))
#                 except (TypeError, ValueError):
#                     pass

#         layout_confidence = None

#         if layout_confidences:
#             layout_confidence = (
#                 sum(layout_confidences)
#                 / len(layout_confidences)
#             )

#         return self.quality_service.calculate_quality(
#             text=full_text,
#             blocks=quality_blocks,
#             page_width=page_width,
#             page_height=page_height,
#             expected_language=expected_language,
#             layout_confidence=layout_confidence,
#         )

#     # =========================================================
#     # SHOULD CORRECT
#     # =========================================================

#     def should_correct(self, quality):
#         if not quality:
#             return True

#         return quality.get("status", "retry") in {
#             "review",
#             "retry",
#         }

#     # =========================================================
#     # SELECT BEST RESULT
#     # =========================================================

#     def select_better_result(
#         self,
#         original_result,
#         original_quality,
#         corrected_result,
#         corrected_quality
#     ):
#         original_score = float(
#             original_quality.get("quality_score", 0)
#         )

#         corrected_score = float(
#             corrected_quality.get("quality_score", 0)
#         )

#         if corrected_score > original_score:
#             return (
#                 "corrected",
#                 corrected_result,
#                 corrected_quality,
#             )

#         return (
#             "original",
#             original_result,
#             original_quality,
#         )

#     # =========================================================
#     # POST-OCR TEXT CORRECTION
#     # =========================================================

#     def apply_post_ocr_corrections(self, final_result):
#         corrected_result, report = apply_corrections(
#             final_result
#         )

#         if report["labels_corrected"]:
#             print(
#                 f"\nAuto-corrected "
#                 f"{len(report['labels_corrected'])} label(s):"
#             )

#             for correction in report["labels_corrected"]:
#                 print(
#                     f"  {correction['original']!r} -> "
#                     f"{correction['corrected']!r} "
#                     f"(score {correction['score']:.0f})"
#                 )

#         if report["marks_table_issues"]:
#             print(
#                 f"\nCorrected "
#                 f"{len(report['marks_table_issues'])} "
#                 "marks-table value(s):"
#             )

#             for issue in report["marks_table_issues"]:
#                 print(
#                     f"  {issue['subject_code']} "
#                     f"{issue['subject_name']}: "
#                     f"{issue['issue']}"
#                 )

#         if report["labels_needing_review"]:
#             print(
#                 f"\n{len(report['labels_needing_review'])} "
#                 "item(s) flagged for manual review "
#                 "(too uncertain to auto-correct):"
#             )

#             for flagged in report["labels_needing_review"]:
#                 print(
#                     f"  {flagged['text']!r} "
#                     f"-- possible match: "
#                     f"{flagged['suggested_label']!r} "
#                     f"(score {flagged['score']:.0f})"
#                 )

#         return corrected_result, report

#     # =========================================================
#     # CORRECT PAGE
#     # =========================================================

#     def correct_page(
#         self,
#         image_path,
#         preprocessing_outputs,
#         initial_result,
#         page_number,
#         expected_language=None
#     ):
#         """
#         Adaptive OCR self-correction.

#         Optimization:
#         - Good initial OCR: no OCR rerun.
#         - Enhanced OCR >= 90: skip threshold OCR.
#         - Otherwise: compare original, enhanced and threshold.
#         - Post-OCR corrections are always applied.
#         """

#         # =====================================================
#         # INITIAL QUALITY
#         # =====================================================

#         initial_quality = self.calculate_result_quality(
#             initial_result,
#             expected_language
#         )

#         initial_score = float(
#             initial_quality.get("quality_score", 0)
#         )

#         print(
#             f"Initial quality score : {initial_score:.2f}"
#         )

#         print(
#             f"Initial status       : "
#             f"{initial_quality['status']}"
#         )

#         # =====================================================
#         # GOOD OCR -> SKIP EXPENSIVE RERUNS
#         # =====================================================

#         if not self.should_correct(initial_quality):

#             print(
#                 "OCR quality is good. "
#                 "No candidate re-run required."
#             )

#             corrected_result, correction_report = (
#                 self.apply_post_ocr_corrections(
#                     initial_result
#                 )
#             )

#             final_quality = self.calculate_result_quality(
#                 corrected_result,
#                 expected_language
#             )

#             final_score = float(
#                 final_quality.get("quality_score", 0)
#             )

#             if final_score != initial_score:
#                 print(
#                     f"\nPost-OCR quality update : "
#                     f"{initial_score:.2f} -> "
#                     f"{final_score:.2f}"
#                 )
#             else:
#                 print(
#                     f"\nPost-OCR quality unchanged : "
#                     f"{final_score:.2f}"
#                 )

#             detected_languages = (
#                 self.get_detected_languages(corrected_result)
#             )

#             post_ocr_correction_applied = (
#                 bool(correction_report.get("labels_corrected"))
#                 or bool(correction_report.get("marks_table_issues"))
#             )

#             return {
#                 "correction_attempted": (
#                     post_ocr_correction_applied
#                 ),
#                 "ocr_rerun_attempted": False,
#                 "post_ocr_correction_applied":
#                     post_ocr_correction_applied,
#                 "selected": "original",
#                 "original": {
#                     "result": initial_result,
#                     "quality": initial_quality,
#                 },
#                 "corrected": [],
#                 "final_result": corrected_result,
#                 "final_quality": final_quality,
#                 "text_correction_report": correction_report,
#                 "detected_languages": detected_languages,
#             }

#         # =====================================================
#         # OCR RERUN REQUIRED
#         # =====================================================

#         print("OCR quality requires correction.")
#         print(
#             f"Correction target : "
#             f"{self.QUALITY_TARGET:.2f}"
#         )

#         candidates = [
#             {
#                 "name": "original",
#                 "result": initial_result,
#                 "quality": initial_quality,
#             }
#         ]

#         # =====================================================
#         # ENHANCED OCR
#         # =====================================================

#         enhanced_image = preprocessing_outputs.get("enhanced")

#         if enhanced_image:
#             print("\nTrying enhanced preprocessing...")

#             enhanced_output_dir = (
#                 self.output_dir
#                 / f"page_{page_number:03d}"
#                 / "enhanced"
#             )

#             enhanced_output_dir.mkdir(
#                 parents=True,
#                 exist_ok=True
#             )

#             print(f"Corrected image : {enhanced_image}")
#             print(f"Correction output : {enhanced_output_dir}")

#             enhanced_result = self.surya.run_ocr(
#                 enhanced_image,
#                 output_dir=str(enhanced_output_dir)
#             )

#             enhanced_quality = self.calculate_result_quality(
#                 enhanced_result,
#                 expected_language
#             )

#             enhanced_score = float(
#                 enhanced_quality.get("quality_score", 0)
#             )

#             print(
#                 f"Enhanced quality score : "
#                 f"{enhanced_score:.2f}"
#             )

#             print(
#                 f"Enhanced status : "
#                 f"{enhanced_quality['status']}"
#             )

#             candidates.append({
#                 "name": "enhanced",
#                 "result": enhanced_result,
#                 "quality": enhanced_quality,
#             })

#             # =================================================
#             # EARLY EXIT
#             # =================================================

#             if enhanced_score >= self.QUALITY_TARGET:
#                 print(
#                     f"\nEnhanced OCR reached "
#                     f"{enhanced_score:.2f} >= "
#                     f"{self.QUALITY_TARGET:.2f}."
#                 )
#                 print(
#                     "Skipping threshold OCR "
#                     "to save processing time."
#                 )

#             else:
#                 self._run_threshold_candidate(
#                     preprocessing_outputs,
#                     page_number,
#                     expected_language,
#                     candidates
#                 )

#         else:
#             # No enhanced image: use threshold directly.
#             self._run_threshold_candidate(
#                 preprocessing_outputs,
#                 page_number,
#                 expected_language,
#                 candidates
#             )

#         # =====================================================
#         # SELECT BEST CANDIDATE
#         # =====================================================

#         best_candidate = max(
#             candidates,
#             key=lambda candidate: float(
#                 candidate["quality"].get(
#                     "quality_score",
#                     0
#                 )
#             )
#         )

#         selected = best_candidate["name"]
#         final_result = best_candidate["result"]
#         candidate_quality = best_candidate["quality"]

#         print("\n========================================")
#         print("        CORRECTION COMPARISON")
#         print("========================================")

#         for candidate in candidates:
#             print(
#                 f"{candidate['name']:12} : "
#                 f"{float(candidate['quality'].get('quality_score', 0)):.2f}"
#             )

#         print(f"\nSelected result : {selected}")

#         print(
#             f"Selected OCR quality score : "
#             f"{float(candidate_quality.get('quality_score', 0)):.2f}"
#         )

#         # =====================================================
#         # POST-OCR TEXT CORRECTION
#         # =====================================================

#         final_result, correction_report = (
#             self.apply_post_ocr_corrections(
#                 final_result
#             )
#         )

#         # =====================================================
#         # FINAL QUALITY
#         # =====================================================

#         final_quality = self.calculate_result_quality(
#             final_result,
#             expected_language
#         )

#         candidate_score = float(
#             candidate_quality.get("quality_score", 0)
#         )

#         final_score = float(
#             final_quality.get("quality_score", 0)
#         )

#         if final_score != candidate_score:
#             print(
#                 f"\nPost-OCR quality update : "
#                 f"{candidate_score:.2f} -> "
#                 f"{final_score:.2f}"
#             )
#         else:
#             print(
#                 f"\nPost-OCR quality unchanged : "
#                 f"{final_score:.2f}"
#             )

#         detected_languages = (
#             self.get_detected_languages(final_result)
#         )

#         post_ocr_correction_applied = (
#             bool(correction_report.get("labels_corrected"))
#             or bool(correction_report.get("marks_table_issues"))
#         )

#         return {
#             "correction_attempted": True,
#             "ocr_rerun_attempted": True,
#             "post_ocr_correction_applied":
#                 post_ocr_correction_applied,
#             "selected": selected,
#             "original": {
#                 "result": initial_result,
#                 "quality": initial_quality,
#             },
#             "corrected": candidates[1:],
#             "final_result": final_result,
#             "final_quality": final_quality,
#             "text_correction_report": correction_report,
#             "detected_languages": detected_languages,
#         }

#     # =========================================================
#     # THRESHOLD CANDIDATE
#     # =========================================================

#     def _run_threshold_candidate(
#         self,
#         preprocessing_outputs,
#         page_number,
#         expected_language,
#         candidates
#     ):
#         """
#         Run threshold OCR only when enhanced OCR either:
#         - is unavailable, or
#         - failed to reach QUALITY_TARGET.
#         """

#         threshold_image = preprocessing_outputs.get("threshold")

#         if not threshold_image:
#             print(
#                 "\nThreshold image unavailable. "
#                 "No further OCR candidate to try."
#             )
#             return

#         print("\nTrying threshold preprocessing...")

#         threshold_output_dir = (
#             self.output_dir
#             / f"page_{page_number:03d}"
#             / "threshold"
#         )

#         threshold_output_dir.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         print(f"Threshold image : {threshold_image}")
#         print(f"Correction output : {threshold_output_dir}")

#         threshold_result = self.surya.run_ocr(
#             threshold_image,
#             output_dir=str(threshold_output_dir)
#         )

#         threshold_quality = self.calculate_result_quality(
#             threshold_result,
#             expected_language
#         )

#         threshold_score = float(
#             threshold_quality.get("quality_score", 0)
#         )

#         print(
#             f"Threshold quality score : "
#             f"{threshold_score:.2f}"
#         )

#         print(
#             f"Threshold status : "
#             f"{threshold_quality['status']}"
#         )

#         candidates.append({
#             "name": "threshold",
#             "result": threshold_result,
#             "quality": threshold_quality,
#         })



























# from pathlib import Path

# from services.surya_ocr_service import SuryaOCRService
# from services.quality_service import OCRQualityService
# from services.ocr_text_corrector import apply_corrections


# class OCRCorrectionService:

#     # =========================================================
#     # PERFORMANCE SETTINGS
#     # =========================================================

#     # Stop expensive OCR candidate processing once this
#     # quality is reached.
#     QUALITY_TARGET = 90.0

#     # Enhanced OCR must improve the original result by at
#     # least this many quality points before we spend another
#     # full Surya inference pass on threshold OCR.
#     MIN_ENHANCED_IMPROVEMENT = 1.0

#     def __init__(self, output_dir="output/corrected"):
#         self.output_dir = Path(output_dir)
#         self.output_dir.mkdir(parents=True, exist_ok=True)

#         self.surya = SuryaOCRService()
#         self.quality_service = OCRQualityService()

#     # =========================================================
#     # LANGUAGE NORMALIZATION
#     # =========================================================

#     def normalize_language(self, language):
#         if not language:
#             return "unknown"

#         language = str(language).lower().strip()

#         mapping = {
#             "eng": "en",
#             "english": "en",
#             "en": "en",
#             "hin": "hin",
#             "hindi": "hin",
#             "guj": "guj",
#             "gujarati": "guj",
#             "mixed": "mixed",
#             "unknown": "unknown",
#         }

#         return mapping.get(language, language)

#     # =========================================================
#     # GET DETECTED LANGUAGES
#     # =========================================================

#     def get_detected_languages(self, ocr_result):
#         detected = set()

#         if not ocr_result:
#             return []

#         results = ocr_result.get("results", [])

#         for item in results:
#             language = self.normalize_language(
#                 item.get("language", "unknown")
#             )

#             if language in {"en", "hin", "guj"}:
#                 detected.add(language)

#             elif language == "mixed":
#                 detected.update(
#                     self._detect_languages_from_text(
#                         item.get("text", "")
#                     )
#                 )

#         language_order = ["en", "hin", "guj"]

#         return [
#             language
#             for language in language_order
#             if language in detected
#         ]

#     # =========================================================
#     # DETECT LANGUAGES FROM TEXT
#     # =========================================================

#     def _detect_languages_from_text(self, text):
#         if not text:
#             return set()

#         detected = set()

#         for character in text:
#             code = ord(character)

#             # Devanagari
#             if 0x0900 <= code <= 0x097F:
#                 detected.add("hin")

#             # Gujarati
#             elif 0x0A80 <= code <= 0x0AFF:
#                 detected.add("guj")

#             # English / Latin
#             elif (
#                 "A" <= character <= "Z"
#                 or "a" <= character <= "z"
#             ):
#                 detected.add("en")

#         return detected

#     # =========================================================
#     # QUALITY CALCULATION
#     # =========================================================

#     def calculate_result_quality(
#         self,
#         ocr_result,
#         expected_language=None
#     ):
#         if not ocr_result:
#             return {
#                 "quality_score": 0.0,
#                 "status": "retry",
#                 "text_score": 0.0,
#                 "language_score": 0.0,
#                 "character_score": 0.0,
#                 "coverage_score": 0.0,
#                 "confidence_score": 0.0,
#             }

#         results = ocr_result.get("results", [])

#         text_parts = []

#         for item in results:
#             text = item.get("text", "")

#             if text:
#                 text_parts.append(str(text))

#         full_text = "\n".join(text_parts)

#         # -----------------------------------------------------
#         # QUALITY BLOCKS
#         # -----------------------------------------------------

#         quality_blocks = []

#         for item in results:

#             block = {
#                 "text": item.get("text", ""),
#                 "language": self.normalize_language(
#                     item.get("language", "unknown")
#                 ),
#                 "bbox": item.get("bbox"),
#                 "confidence": item.get("confidence", 0.0),
#             }

#             if "layout_confidence" in item:
#                 block["layout_confidence"] = item[
#                     "layout_confidence"
#                 ]

#             quality_blocks.append(block)

#         # -----------------------------------------------------
#         # PAGE DIMENSIONS
#         # -----------------------------------------------------

#         page_width = ocr_result.get("page_width")
#         page_height = ocr_result.get("page_height")

#         if page_width is None:

#             for item in results:

#                 if item.get("page_width") is not None:
#                     page_width = item["page_width"]
#                     break

#         if page_height is None:

#             for item in results:

#                 if item.get("page_height") is not None:
#                     page_height = item["page_height"]
#                     break

#         # -----------------------------------------------------
#         # IMAGE BBOX FALLBACK
#         # -----------------------------------------------------

#         if page_width is None or page_height is None:

#             for item in results:

#                 image_bbox = item.get("image_bbox")

#                 if image_bbox and len(image_bbox) >= 4:
#                     page_width = image_bbox[2]
#                     page_height = image_bbox[3]
#                     break

#         # -----------------------------------------------------
#         # LAYOUT CONFIDENCE
#         # -----------------------------------------------------

#         layout_confidences = []

#         for item in results:

#             value = item.get("layout_confidence")

#             if value is not None:

#                 try:
#                     layout_confidences.append(
#                         float(value)
#                     )

#                 except (TypeError, ValueError):
#                     pass

#         layout_confidence = None

#         if layout_confidences:

#             layout_confidence = (
#                 sum(layout_confidences)
#                 / len(layout_confidences)
#             )

#         # -----------------------------------------------------
#         # EXISTING QUALITY SERVICE
#         # -----------------------------------------------------

#         return self.quality_service.calculate_quality(
#             text=full_text,
#             blocks=quality_blocks,
#             page_width=page_width,
#             page_height=page_height,
#             expected_language=expected_language,
#             layout_confidence=layout_confidence,
#         )

#     # =========================================================
#     # SHOULD CORRECT
#     # =========================================================

#     def should_correct(self, quality):

#         if not quality:
#             return True

#         return quality.get("status", "retry") in {
#             "review",
#             "retry",
#         }

#     # =========================================================
#     # SELECT BEST RESULT
#     # =========================================================

#     def select_better_result(
#         self,
#         original_result,
#         original_quality,
#         corrected_result,
#         corrected_quality
#     ):
#         original_score = float(
#             original_quality.get("quality_score", 0)
#         )

#         corrected_score = float(
#             corrected_quality.get("quality_score", 0)
#         )

#         if corrected_score > original_score:

#             return (
#                 "corrected",
#                 corrected_result,
#                 corrected_quality,
#             )

#         return (
#             "original",
#             original_result,
#             original_quality,
#         )

#     # =========================================================
#     # POST-OCR TEXT CORRECTION
#     # =========================================================

#     def apply_post_ocr_corrections(self, final_result):

#         corrected_result, report = apply_corrections(
#             final_result
#         )

#         # -----------------------------------------------------
#         # LABEL CORRECTIONS
#         # -----------------------------------------------------

#         if report["labels_corrected"]:

#             print(
#                 f"\nAuto-corrected "
#                 f"{len(report['labels_corrected'])} label(s):"
#             )

#             for correction in report["labels_corrected"]:

#                 print(
#                     f"  {correction['original']!r} -> "
#                     f"{correction['corrected']!r} "
#                     f"(score {correction['score']:.0f})"
#                 )

#         # -----------------------------------------------------
#         # MARKS TABLE CORRECTIONS
#         # -----------------------------------------------------

#         if report["marks_table_issues"]:

#             print(
#                 f"\nCorrected "
#                 f"{len(report['marks_table_issues'])} "
#                 "marks-table value(s):"
#             )

#             for issue in report["marks_table_issues"]:

#                 print(
#                     f"  {issue['subject_code']} "
#                     f"{issue['subject_name']}: "
#                     f"{issue['issue']}"
#                 )

#         # -----------------------------------------------------
#         # MANUAL REVIEW ITEMS
#         # -----------------------------------------------------

#         if report["labels_needing_review"]:

#             print(
#                 f"\n{len(report['labels_needing_review'])} "
#                 "item(s) flagged for manual review "
#                 "(too uncertain to auto-correct):"
#             )

#             for flagged in report["labels_needing_review"]:

#                 print(
#                     f"  {flagged['text']!r} "
#                     f"-- possible match: "
#                     f"{flagged['suggested_label']!r} "
#                     f"(score {flagged['score']:.0f})"
#                 )

#         return corrected_result, report

#     # =========================================================
#     # CORRECT PAGE
#     # =========================================================

#     def correct_page(
#         self,
#         image_path,
#         preprocessing_outputs,
#         initial_result,
#         page_number,
#         expected_language=None
#     ):
#         """
#         Adaptive OCR self-correction.

#         PERFORMANCE LOGIC:

#         1. Initial OCR >= 90
#            -> no expensive Surya rerun.

#         2. Initial OCR < 90
#            -> run Enhanced OCR.

#         3. Enhanced OCR >= 90
#            -> stop. Do NOT run Threshold.

#         4. Enhanced OCR is worse than Original
#            -> stop. Do NOT run Threshold.

#         5. Enhanced OCR improves by less than
#            MIN_ENHANCED_IMPROVEMENT
#            -> stop. Do NOT run Threshold.

#         6. Enhanced OCR meaningfully improves the result
#            but remains below 90
#            -> run Threshold OCR.

#         7. Select the highest-quality candidate.

#         8. Always apply the existing post-OCR correction.

#         IMPORTANT:
#         The function signature is intentionally unchanged so
#         OCRPipelineService remains compatible.
#         """

#         # =====================================================
#         # INITIAL QUALITY
#         # =====================================================

#         initial_quality = self.calculate_result_quality(
#             initial_result,
#             expected_language
#         )

#         initial_score = float(
#             initial_quality.get("quality_score", 0)
#         )

#         print(
#             f"Initial quality score : "
#             f"{initial_score:.2f}"
#         )

#         print(
#             f"Initial status       : "
#             f"{initial_quality['status']}"
#         )

#         # =====================================================
#         # HARD QUALITY TARGET
#         # =====================================================

#         if initial_score >= self.QUALITY_TARGET:

#             print(
#                 f"Initial OCR already reached "
#                 f"{self.QUALITY_TARGET:.2f}+."
#             )

#             print(
#                 "Skipping all expensive OCR reruns."
#             )

#             corrected_result, correction_report = (
#                 self.apply_post_ocr_corrections(
#                     initial_result
#                 )
#             )

#             final_quality = self.calculate_result_quality(
#                 corrected_result,
#                 expected_language
#             )

#             final_score = float(
#                 final_quality.get("quality_score", 0)
#             )

#             if final_score != initial_score:

#                 print(
#                     f"\nPost-OCR quality update : "
#                     f"{initial_score:.2f} -> "
#                     f"{final_score:.2f}"
#                 )

#             else:

#                 print(
#                     f"\nPost-OCR quality unchanged : "
#                     f"{final_score:.2f}"
#                 )

#             detected_languages = (
#                 self.get_detected_languages(
#                     corrected_result
#                 )
#             )

#             post_ocr_correction_applied = (
#                 bool(
#                     correction_report.get(
#                         "labels_corrected"
#                     )
#                 )
#                 or bool(
#                     correction_report.get(
#                         "marks_table_issues"
#                     )
#                 )
#             )

#             return {
#                 "correction_attempted":
#                     post_ocr_correction_applied,

#                 "ocr_rerun_attempted": False,

#                 "post_ocr_correction_applied":
#                     post_ocr_correction_applied,

#                 "selected": "original",

#                 "original": {
#                     "result": initial_result,
#                     "quality": initial_quality,
#                 },

#                 "corrected": [],

#                 "final_result": corrected_result,

#                 "final_quality": final_quality,

#                 "text_correction_report":
#                     correction_report,

#                 "detected_languages":
#                     detected_languages,
#             }

#         # =====================================================
#         # EXISTING STATUS-BASED CORRECTION CHECK
#         # =====================================================

#         if not self.should_correct(initial_quality):

#             print(
#                 "OCR quality status does not require "
#                 "an OCR candidate re-run."
#             )

#             corrected_result, correction_report = (
#                 self.apply_post_ocr_corrections(
#                     initial_result
#                 )
#             )

#             final_quality = self.calculate_result_quality(
#                 corrected_result,
#                 expected_language
#             )

#             final_score = float(
#                 final_quality.get("quality_score", 0)
#             )

#             print(
#                 f"\nFinal quality score : "
#                 f"{final_score:.2f}"
#             )

#             detected_languages = (
#                 self.get_detected_languages(
#                     corrected_result
#                 )
#             )

#             post_ocr_correction_applied = (
#                 bool(
#                     correction_report.get(
#                         "labels_corrected"
#                     )
#                 )
#                 or bool(
#                     correction_report.get(
#                         "marks_table_issues"
#                     )
#                 )
#             )

#             return {
#                 "correction_attempted":
#                     post_ocr_correction_applied,

#                 "ocr_rerun_attempted": False,

#                 "post_ocr_correction_applied":
#                     post_ocr_correction_applied,

#                 "selected": "original",

#                 "original": {
#                     "result": initial_result,
#                     "quality": initial_quality,
#                 },

#                 "corrected": [],

#                 "final_result": corrected_result,

#                 "final_quality": final_quality,

#                 "text_correction_report":
#                     correction_report,

#                 "detected_languages":
#                     detected_languages,
#             }

#         # =====================================================
#         # OCR RERUN REQUIRED
#         # =====================================================

#         print(
#             "OCR quality requires correction."
#         )

#         print(
#             f"Correction target : "
#             f"{self.QUALITY_TARGET:.2f}"
#         )

#         candidates = [
#             {
#                 "name": "original",
#                 "result": initial_result,
#                 "quality": initial_quality,
#             }
#         ]

#         # =====================================================
#         # ENHANCED OCR
#         # =====================================================

#         enhanced_image = preprocessing_outputs.get(
#             "enhanced"
#         )

#         enhanced_result = None
#         enhanced_quality = None
#         enhanced_score = 0.0

#         if enhanced_image:

#             print()
#             print("=" * 60)
#             print("LEVEL 2 — ENHANCED OCR")
#             print("=" * 60)

#             print(
#                 f"Enhanced image : "
#                 f"{enhanced_image}"
#             )

#             enhanced_output_dir = (
#                 self.output_dir
#                 / f"page_{page_number:03d}"
#                 / "enhanced"
#             )

#             enhanced_output_dir.mkdir(
#                 parents=True,
#                 exist_ok=True
#             )

#             print(
#                 f"Correction output : "
#                 f"{enhanced_output_dir}"
#             )

#             # -------------------------------------------------
#             # SAME SURYA SERVICE
#             # -------------------------------------------------
#             #
#             # Your SuryaOCRService is configured for
#             # persistent llama.cpp server reuse.
#             #
#             # Therefore this call should attach to the
#             # existing server rather than starting a new one.
#             #

#             enhanced_result = self.surya.run_ocr(
#                 enhanced_image,
#                 output_dir=str(
#                     enhanced_output_dir
#                 )
#             )

#             enhanced_quality = (
#                 self.calculate_result_quality(
#                     enhanced_result,
#                     expected_language
#                 )
#             )

#             enhanced_score = float(
#                 enhanced_quality.get(
#                     "quality_score",
#                     0
#                 )
#             )

#             print(
#                 f"Enhanced quality score : "
#                 f"{enhanced_score:.2f}"
#             )

#             print(
#                 f"Enhanced status : "
#                 f"{enhanced_quality['status']}"
#             )

#             candidates.append({
#                 "name": "enhanced",
#                 "result": enhanced_result,
#                 "quality": enhanced_quality,
#             })

#             # =================================================
#             # SMART EARLY-STOP DECISION
#             # =================================================

#             improvement = (
#                 enhanced_score
#                 - initial_score
#             )

#             print(
#                 f"Enhanced improvement : "
#                 f"{improvement:+.2f}"
#             )

#             # -------------------------------------------------
#             # CASE 1: ENHANCED REACHED 90
#             # -------------------------------------------------

#             if enhanced_score >= self.QUALITY_TARGET:

#                 print()
#                 print(
#                     f"Enhanced OCR reached "
#                     f"{enhanced_score:.2f}."
#                 )

#                 print(
#                     "Quality target reached."
#                 )

#                 print(
#                     "Skipping threshold OCR."
#                 )

#             # -------------------------------------------------
#             # CASE 2: ENHANCED IS WORSE
#             # -------------------------------------------------

#             elif improvement <= 0:

#                 print()
#                 print(
#                     "Enhanced OCR did not improve "
#                     "the original result."
#                 )

#                 print(
#                     f"Original : "
#                     f"{initial_score:.2f}"
#                 )

#                 print(
#                     f"Enhanced : "
#                     f"{enhanced_score:.2f}"
#                 )

#                 print(
#                     "Skipping threshold OCR "
#                     "to save processing time."
#                 )

#             # -------------------------------------------------
#             # CASE 3: VERY SMALL IMPROVEMENT
#             # -------------------------------------------------

#             elif (
#                 improvement
#                 < self.MIN_ENHANCED_IMPROVEMENT
#             ):

#                 print()
#                 print(
#                     "Enhanced OCR improvement is too small."
#                 )

#                 print(
#                     f"Improvement : "
#                     f"{improvement:+.2f}"
#                 )

#                 print(
#                     f"Minimum required : "
#                     f"{self.MIN_ENHANCED_IMPROVEMENT:.2f}"
#                 )

#                 print(
#                     "Skipping threshold OCR "
#                     "to save processing time."
#                 )

#             # -------------------------------------------------
#             # CASE 4: MEANINGFUL IMPROVEMENT
#             # -------------------------------------------------

#             else:

#                 print()
#                 print(
#                     "Enhanced OCR produced a "
#                     "meaningful improvement."
#                 )

#                 print(
#                     f"Improvement : "
#                     f"{improvement:+.2f}"
#                 )

#                 print(
#                     "Enhanced result is still below "
#                     "the quality target."
#                 )

#                 print(
#                     "Running threshold OCR."
#                 )

#                 self._run_threshold_candidate(
#                     preprocessing_outputs,
#                     page_number,
#                     expected_language,
#                     candidates
#                 )

#         else:

#             print()
#             print(
#                 "Enhanced preprocessing image "
#                 "not available."
#             )

#             print(
#                 "Trying threshold OCR directly."
#             )

#             self._run_threshold_candidate(
#                 preprocessing_outputs,
#                 page_number,
#                 expected_language,
#                 candidates
#             )

#         # =====================================================
#         # SELECT BEST CANDIDATE
#         # =====================================================

#         best_candidate = max(
#             candidates,
#             key=lambda candidate: float(
#                 candidate["quality"].get(
#                     "quality_score",
#                     0
#                 )
#             )
#         )

#         selected = best_candidate["name"]

#         final_result = best_candidate["result"]

#         candidate_quality = best_candidate["quality"]

#         print()
#         print("=" * 60)
#         print("CORRECTION COMPARISON")
#         print("=" * 60)

#         for candidate in candidates:

#             score = float(
#                 candidate["quality"].get(
#                     "quality_score",
#                     0
#                 )
#             )

#             print(
#                 f"{candidate['name']:12} : "
#                 f"{score:.2f}"
#             )

#         print()
#         print(
#             f"Selected result : "
#             f"{selected}"
#         )

#         print(
#             f"Selected OCR quality score : "
#             f"{float(candidate_quality.get('quality_score', 0)):.2f}"
#         )

#         # =====================================================
#         # POST-OCR TEXT CORRECTION
#         # =====================================================

#         final_result, correction_report = (
#             self.apply_post_ocr_corrections(
#                 final_result
#             )
#         )

#         # =====================================================
#         # FINAL QUALITY
#         # =====================================================

#         final_quality = self.calculate_result_quality(
#             final_result,
#             expected_language
#         )

#         candidate_score = float(
#             candidate_quality.get(
#                 "quality_score",
#                 0
#             )
#         )

#         final_score = float(
#             final_quality.get(
#                 "quality_score",
#                 0
#             )
#         )

#         if final_score != candidate_score:

#             print(
#                 f"\nPost-OCR quality update : "
#                 f"{candidate_score:.2f} -> "
#                 f"{final_score:.2f}"
#             )

#         else:

#             print(
#                 f"\nPost-OCR quality unchanged : "
#                 f"{final_score:.2f}"
#             )

#         # =====================================================
#         # DETECT LANGUAGES
#         # =====================================================

#         detected_languages = (
#             self.get_detected_languages(
#                 final_result
#             )
#         )

#         # =====================================================
#         # POST-OCR CORRECTION FLAG
#         # =====================================================

#         post_ocr_correction_applied = (
#             bool(
#                 correction_report.get(
#                     "labels_corrected"
#                 )
#             )
#             or bool(
#                 correction_report.get(
#                     "marks_table_issues"
#                 )
#             )
#         )

#         # =====================================================
#         # FINAL RETURN
#         # =====================================================

#         return {
#             "correction_attempted": True,

#             "ocr_rerun_attempted": True,

#             "post_ocr_correction_applied":
#                 post_ocr_correction_applied,

#             "selected": selected,

#             "original": {
#                 "result": initial_result,
#                 "quality": initial_quality,
#             },

#             "corrected": candidates[1:],

#             "final_result": final_result,

#             "final_quality": final_quality,

#             "text_correction_report":
#                 correction_report,

#             "detected_languages":
#                 detected_languages,
#         }

#     # =========================================================
#     # THRESHOLD CANDIDATE
#     # =========================================================

#     def _run_threshold_candidate(
#         self,
#         preprocessing_outputs,
#         page_number,
#         expected_language,
#         candidates
#     ):
#         """
#         Run threshold OCR.

#         This method is only called when:
#         - Enhanced OCR is unavailable, OR
#         - Enhanced OCR remains below 90 AND
#           produced a meaningful improvement.
#         """

#         threshold_image = (
#             preprocessing_outputs.get(
#                 "threshold"
#             )
#         )

#         if not threshold_image:

#             print(
#                 "\nThreshold image unavailable."
#             )

#             print(
#                 "No further OCR candidate to try."
#             )

#             return

#         print()
#         print("=" * 60)
#         print("LEVEL 2 — THRESHOLD OCR")
#         print("=" * 60)

#         print(
#             f"Threshold image : "
#             f"{threshold_image}"
#         )

#         threshold_output_dir = (
#             self.output_dir
#             / f"page_{page_number:03d}"
#             / "threshold"
#         )

#         threshold_output_dir.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         print(
#             f"Correction output : "
#             f"{threshold_output_dir}"
#         )

#         # -----------------------------------------------------
#         # SAME PERSISTENT SURYA SERVER
#         # -----------------------------------------------------

#         threshold_result = self.surya.run_ocr(
#             threshold_image,
#             output_dir=str(
#                 threshold_output_dir
#             )
#         )

#         threshold_quality = (
#             self.calculate_result_quality(
#                 threshold_result,
#                 expected_language
#             )
#         )

#         threshold_score = float(
#             threshold_quality.get(
#                 "quality_score",
#                 0
#             )
#         )

#         print(
#             f"Threshold quality score : "
#             f"{threshold_score:.2f}"
#         )

#         print(
#             f"Threshold status : "
#             f"{threshold_quality['status']}"
#         )

#         candidates.append({
#             "name": "threshold",
#             "result": threshold_result,
#             "quality": threshold_quality,
#         })









































































#####final changed codes



from pathlib import Path

from services.surya_ocr_service import SuryaOCRService
from services.quality_service import OCRQualityService
from services.ocr_text_corrector import apply_corrections


class OCRCorrectionService:

    # =========================================================
    # PERFORMANCE SETTINGS
    # =========================================================

    # Stop expensive OCR candidate processing once this
    # quality is reached.
    QUALITY_TARGET = 50.0

    # Enhanced OCR must improve the original result by at
    # least this many quality points before we spend another
    # full Surya inference pass on threshold OCR.
    MIN_ENHANCED_IMPROVEMENT = 1.0

    def __init__(self, output_dir="output/corrected"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.surya = SuryaOCRService()
        self.quality_service = OCRQualityService()

    # =========================================================
    # LANGUAGE NORMALIZATION
    # =========================================================

    def normalize_language(self, language):
        if not language:
            return "unknown"

        language = str(language).lower().strip()

        mapping = {
            "eng": "en",
            "english": "en",
            "en": "en",
            "hin": "hin",
            "hindi": "hin",
            "guj": "guj",
            "gujarati": "guj",
            "mixed": "mixed",
            "unknown": "unknown",
        }

        return mapping.get(language, language)

    # =========================================================
    # GET DETECTED LANGUAGES
    # =========================================================

    def get_detected_languages(self, ocr_result):
        detected = set()

        if not ocr_result:
            return []

        results = ocr_result.get("results", [])

        for item in results:
            language = self.normalize_language(
                item.get("language", "unknown")
            )

            if language in {"en", "hin", "guj"}:
                detected.add(language)

            elif language == "mixed":
                detected.update(
                    self._detect_languages_from_text(
                        item.get("text", "")
                    )
                )

        language_order = ["en", "hin", "guj"]

        return [
            language
            for language in language_order
            if language in detected
        ]

    # =========================================================
    # DETECT LANGUAGES FROM TEXT
    # =========================================================

    def _detect_languages_from_text(self, text):
        if not text:
            return set()

        detected = set()

        for character in text:
            code = ord(character)

            # Devanagari
            if 0x0900 <= code <= 0x097F:
                detected.add("hin")

            # Gujarati
            elif 0x0A80 <= code <= 0x0AFF:
                detected.add("guj")

            # English / Latin
            elif (
                "A" <= character <= "Z"
                or "a" <= character <= "z"
            ):
                detected.add("en")

        return detected

    # =========================================================
    # QUALITY CALCULATION
    # =========================================================

    def calculate_result_quality(
        self,
        ocr_result,
        expected_language=None
    ):
        if not ocr_result:
            return {
                "quality_score": 0.0,
                "status": "retry",
                "text_score": 0.0,
                "language_score": 0.0,
                "character_score": 0.0,
                "coverage_score": 0.0,
                "confidence_score": 0.0,
            }

        results = ocr_result.get("results", [])

        text_parts = []

        for item in results:
            text = item.get("text", "")

            if text:
                text_parts.append(str(text))

        full_text = "\n".join(text_parts)

        # -----------------------------------------------------
        # QUALITY BLOCKS
        # -----------------------------------------------------

        quality_blocks = []

        for item in results:

            block = {
                "text": item.get("text", ""),
                "language": self.normalize_language(
                    item.get("language", "unknown")
                ),
                "bbox": item.get("bbox"),
                "confidence": item.get("confidence", 0.0),
            }

            if "layout_confidence" in item:
                block["layout_confidence"] = item[
                    "layout_confidence"
                ]

            quality_blocks.append(block)

        # -----------------------------------------------------
        # PAGE DIMENSIONS
        # -----------------------------------------------------

        page_width = ocr_result.get("page_width")
        page_height = ocr_result.get("page_height")

        if page_width is None:

            for item in results:

                if item.get("page_width") is not None:
                    page_width = item["page_width"]
                    break

        if page_height is None:

            for item in results:

                if item.get("page_height") is not None:
                    page_height = item["page_height"]
                    break

        # -----------------------------------------------------
        # IMAGE BBOX FALLBACK
        # -----------------------------------------------------

        if page_width is None or page_height is None:

            for item in results:

                image_bbox = item.get("image_bbox")

                if image_bbox and len(image_bbox) >= 4:
                    page_width = image_bbox[2]
                    page_height = image_bbox[3]
                    break

        # -----------------------------------------------------
        # LAYOUT CONFIDENCE
        # -----------------------------------------------------

        layout_confidences = []

        for item in results:

            value = item.get("layout_confidence")

            if value is not None:

                try:
                    layout_confidences.append(
                        float(value)
                    )

                except (TypeError, ValueError):
                    pass

        layout_confidence = None

        if layout_confidences:

            layout_confidence = (
                sum(layout_confidences)
                / len(layout_confidences)
            )

        # -----------------------------------------------------
        # EXISTING QUALITY SERVICE
        # -----------------------------------------------------

        return self.quality_service.calculate_quality(
            text=full_text,
            blocks=quality_blocks,
            page_width=page_width,
            page_height=page_height,
            expected_language=expected_language,
            layout_confidence=layout_confidence,
        )

    # =========================================================
    # SHOULD CORRECT
    # =========================================================

    def should_correct(self, quality):

        if not quality:
            return True

        return quality.get("status", "retry") in {
            "review",
            "retry",
        }

    # =========================================================
    # SELECT BEST RESULT
    # =========================================================

    def select_better_result(
        self,
        original_result,
        original_quality,
        corrected_result,
        corrected_quality
    ):
        original_score = float(
            original_quality.get("quality_score", 0)
        )

        corrected_score = float(
            corrected_quality.get("quality_score", 0)
        )

        if corrected_score > original_score:

            return (
                "corrected",
                corrected_result,
                corrected_quality,
            )

        return (
            "original",
            original_result,
            original_quality,
        )

    # =========================================================
    # POST-OCR TEXT CORRECTION
    # =========================================================

    def apply_post_ocr_corrections(self, final_result):

        corrected_result, report = apply_corrections(
            final_result
        )

        # -----------------------------------------------------
        # LABEL CORRECTIONS
        # -----------------------------------------------------

        if report["labels_corrected"]:

            print(
                f"\nAuto-corrected "
                f"{len(report['labels_corrected'])} label(s):"
            )

            for correction in report["labels_corrected"]:

                print(
                    f"  {correction['original']!r} -> "
                    f"{correction['corrected']!r} "
                    f"(score {correction['score']:.0f})"
                )

        # -----------------------------------------------------
        # MARKS TABLE CORRECTIONS
        # -----------------------------------------------------

        if report["marks_table_issues"]:

            print(
                f"\nCorrected "
                f"{len(report['marks_table_issues'])} "
                "marks-table value(s):"
            )

            for issue in report["marks_table_issues"]:

                print(
                    f"  {issue['subject_code']} "
                    f"{issue['subject_name']}: "
                    f"{issue['issue']}"
                )

        # -----------------------------------------------------
        # MANUAL REVIEW ITEMS
        # -----------------------------------------------------

        if report["labels_needing_review"]:

            print(
                f"\n{len(report['labels_needing_review'])} "
                "item(s) flagged for manual review "
                "(too uncertain to auto-correct):"
            )

            for flagged in report["labels_needing_review"]:

                print(
                    f"  {flagged['text']!r} "
                    f"-- possible match: "
                    f"{flagged['suggested_label']!r} "
                    f"(score {flagged['score']:.0f})"
                )

        return corrected_result, report

    # =========================================================
    # CORRECT PAGE
    # =========================================================

    def correct_page(
        self,
        image_path,
        preprocessing_outputs,
        initial_result,
        page_number,
        expected_language=None
    ):
        """
        Adaptive OCR self-correction.

        PERFORMANCE LOGIC:

        1. Initial OCR >= 90
           -> no expensive Surya rerun.

        2. Initial OCR < 90
           -> run Enhanced OCR.

        3. Enhanced OCR >= 90
           -> stop. Do NOT run Threshold.

        4. Enhanced OCR is worse than Original
           -> stop. Do NOT run Threshold.

        5. Enhanced OCR improves by less than
           MIN_ENHANCED_IMPROVEMENT
           -> stop. Do NOT run Threshold.

        6. Enhanced OCR meaningfully improves the result
           but remains below 90
           -> run Threshold OCR.

        7. Select the highest-quality candidate.

        8. Always apply the existing post-OCR correction.

        IMPORTANT:
        The function signature is intentionally unchanged so
        OCRPipelineService remains compatible.
        """

        # =====================================================
        # INITIAL QUALITY
        # =====================================================

        initial_quality = self.calculate_result_quality(
            initial_result,
            expected_language
        )

        initial_score = float(
            initial_quality.get("quality_score", 0)
        )

        print(
            f"Initial quality score : "
            f"{initial_score:.2f}"
        )

        print(
            f"Initial status       : "
            f"{initial_quality['status']}"
        )

        # =====================================================
        # HARD QUALITY TARGET
        # =====================================================

        if initial_score >= self.QUALITY_TARGET:

            print(
                f"Initial OCR already reached "
                f"{self.QUALITY_TARGET:.2f}+."
            )

            print(
                "Skipping all expensive OCR reruns."
            )

            corrected_result, correction_report = (
                self.apply_post_ocr_corrections(
                    initial_result
                )
            )

            final_quality = self.calculate_result_quality(
                corrected_result,
                expected_language
            )

            final_score = float(
                final_quality.get("quality_score", 0)
            )

            if final_score != initial_score:

                print(
                    f"\nPost-OCR quality update : "
                    f"{initial_score:.2f} -> "
                    f"{final_score:.2f}"
                )

            else:

                print(
                    f"\nPost-OCR quality unchanged : "
                    f"{final_score:.2f}"
                )

            detected_languages = (
                self.get_detected_languages(
                    corrected_result
                )
            )

            post_ocr_correction_applied = (
                bool(
                    correction_report.get(
                        "labels_corrected"
                    )
                )
                or bool(
                    correction_report.get(
                        "marks_table_issues"
                    )
                )
            )

            return {
                "correction_attempted":
                    post_ocr_correction_applied,

                "ocr_rerun_attempted": False,

                "post_ocr_correction_applied":
                    post_ocr_correction_applied,

                "selected": "original",

                "original": {
                    "result": initial_result,
                    "quality": initial_quality,
                },

                "corrected": [],

                "final_result": corrected_result,

                "final_quality": final_quality,

                "text_correction_report":
                    correction_report,

                "detected_languages":
                    detected_languages,
            }

        # =====================================================
        # EXISTING STATUS-BASED CORRECTION CHECK
        # =====================================================

        if not self.should_correct(initial_quality):

            print(
                "OCR quality status does not require "
                "an OCR candidate re-run."
            )

            corrected_result, correction_report = (
                self.apply_post_ocr_corrections(
                    initial_result
                )
            )

            final_quality = self.calculate_result_quality(
                corrected_result,
                expected_language
            )

            final_score = float(
                final_quality.get("quality_score", 0)
            )

            print(
                f"\nFinal quality score : "
                f"{final_score:.2f}"
            )

            detected_languages = (
                self.get_detected_languages(
                    corrected_result
                )
            )

            post_ocr_correction_applied = (
                bool(
                    correction_report.get(
                        "labels_corrected"
                    )
                )
                or bool(
                    correction_report.get(
                        "marks_table_issues"
                    )
                )
            )

            return {
                "correction_attempted":
                    post_ocr_correction_applied,

                "ocr_rerun_attempted": False,

                "post_ocr_correction_applied":
                    post_ocr_correction_applied,

                "selected": "original",

                "original": {
                    "result": initial_result,
                    "quality": initial_quality,
                },

                "corrected": [],

                "final_result": corrected_result,

                "final_quality": final_quality,

                "text_correction_report":
                    correction_report,

                "detected_languages":
                    detected_languages,
            }

        # =====================================================
        # OCR RERUN REQUIRED
        # =====================================================

        print(
            "OCR quality requires correction."
        )

        print(
            f"Correction target : "
            f"{self.QUALITY_TARGET:.2f}"
        )

        candidates = [
            {
                "name": "original",
                "result": initial_result,
                "quality": initial_quality,
            }
        ]

        # =====================================================
        # ENHANCED OCR
        # =====================================================

        enhanced_image = preprocessing_outputs.get(
            "enhanced"
        )

        enhanced_result = None
        enhanced_quality = None
        enhanced_score = 0.0

        if enhanced_image:

            print()
            print("=" * 60)
            print("LEVEL 2 — ENHANCED OCR")
            print("=" * 60)

            print(
                f"Enhanced image : "
                f"{enhanced_image}"
            )

            enhanced_output_dir = (
                self.output_dir
                / f"page_{page_number:03d}"
                / "enhanced"
            )

            enhanced_output_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            print(
                f"Correction output : "
                f"{enhanced_output_dir}"
            )

            # -------------------------------------------------
            # SAME SURYA SERVICE
            # -------------------------------------------------
            #
            # Your SuryaOCRService is configured for
            # persistent llama.cpp server reuse.
            #
            # Therefore this call should attach to the
            # existing server rather than starting a new one.
            #

            enhanced_result = self.surya.run_ocr(
                enhanced_image,
                output_dir=str(
                    enhanced_output_dir
                )
            )

            enhanced_quality = (
                self.calculate_result_quality(
                    enhanced_result,
                    expected_language
                )
            )

            enhanced_score = float(
                enhanced_quality.get(
                    "quality_score",
                    0
                )
            )

            print(
                f"Enhanced quality score : "
                f"{enhanced_score:.2f}"
            )

            print(
                f"Enhanced status : "
                f"{enhanced_quality['status']}"
            )

            candidates.append({
                "name": "enhanced",
                "result": enhanced_result,
                "quality": enhanced_quality,
            })

            # =================================================
            # SMART EARLY-STOP DECISION
            # =================================================

            improvement = (
                enhanced_score
                - initial_score
            )

            print(
                f"Enhanced improvement : "
                f"{improvement:+.2f}"
            )

            # -------------------------------------------------
            # CASE 1: ENHANCED REACHED 90
            # -------------------------------------------------

            if enhanced_score >= self.QUALITY_TARGET:

                print()
                print(
                    f"Enhanced OCR reached "
                    f"{enhanced_score:.2f}."
                )

                print(
                    "Quality target reached."
                )

                print(
                    "Skipping threshold OCR."
                )

            # -------------------------------------------------
            # CASE 2: ENHANCED IS WORSE
            # -------------------------------------------------

            elif improvement <= 0:

                print()
                print(
                    "Enhanced OCR did not improve "
                    "the original result."
                )

                print(
                    f"Original : "
                    f"{initial_score:.2f}"
                )

                print(
                    f"Enhanced : "
                    f"{enhanced_score:.2f}"
                )

                print(
                    "Skipping threshold OCR "
                    "to save processing time."
                )

            # -------------------------------------------------
            # CASE 3: VERY SMALL IMPROVEMENT
            # -------------------------------------------------

            elif (
                improvement
                < self.MIN_ENHANCED_IMPROVEMENT
            ):

                print()
                print(
                    "Enhanced OCR improvement is too small."
                )

                print(
                    f"Improvement : "
                    f"{improvement:+.2f}"
                )

                print(
                    f"Minimum required : "
                    f"{self.MIN_ENHANCED_IMPROVEMENT:.2f}"
                )

                print(
                    "Skipping threshold OCR "
                    "to save processing time."
                )

            # -------------------------------------------------
            # CASE 4: MEANINGFUL IMPROVEMENT
            # -------------------------------------------------

            else:

                print()
                print(
                    "Enhanced OCR produced a "
                    "meaningful improvement."
                )

                print(
                    f"Improvement : "
                    f"{improvement:+.2f}"
                )

                print(
                    "Enhanced result is still below "
                    "the quality target."
                )

                print(
                    "Running threshold OCR."
                )

                self._run_threshold_candidate(
                    preprocessing_outputs,
                    page_number,
                    expected_language,
                    candidates
                )

        else:

            print()
            print(
                "Enhanced preprocessing image "
                "not available."
            )

            print(
                "Trying threshold OCR directly."
            )

            self._run_threshold_candidate(
                preprocessing_outputs,
                page_number,
                expected_language,
                candidates
            )

        # =====================================================
        # SELECT BEST CANDIDATE
        # =====================================================

        best_candidate = max(
            candidates,
            key=lambda candidate: float(
                candidate["quality"].get(
                    "quality_score",
                    0
                )
            )
        )

        selected = best_candidate["name"]

        final_result = best_candidate["result"]

        candidate_quality = best_candidate["quality"]

        print()
        print("=" * 60)
        print("CORRECTION COMPARISON")
        print("=" * 60)

        for candidate in candidates:

            score = float(
                candidate["quality"].get(
                    "quality_score",
                    0
                )
            )

            print(
                f"{candidate['name']:12} : "
                f"{score:.2f}"
            )

        print()
        print(
            f"Selected result : "
            f"{selected}"
        )

        print(
            f"Selected OCR quality score : "
            f"{float(candidate_quality.get('quality_score', 0)):.2f}"
        )

        # =====================================================
        # POST-OCR TEXT CORRECTION
        # =====================================================

        final_result, correction_report = (
            self.apply_post_ocr_corrections(
                final_result
            )
        )

        # =====================================================
        # FINAL QUALITY
        # =====================================================

        final_quality = self.calculate_result_quality(
            final_result,
            expected_language
        )

        candidate_score = float(
            candidate_quality.get(
                "quality_score",
                0
            )
        )

        final_score = float(
            final_quality.get(
                "quality_score",
                0
            )
        )

        if final_score != candidate_score:

            print(
                f"\nPost-OCR quality update : "
                f"{candidate_score:.2f} -> "
                f"{final_score:.2f}"
            )

        else:

            print(
                f"\nPost-OCR quality unchanged : "
                f"{final_score:.2f}"
            )

        # =====================================================
        # DETECT LANGUAGES
        # =====================================================

        detected_languages = (
            self.get_detected_languages(
                final_result
            )
        )

        # =====================================================
        # POST-OCR CORRECTION FLAG
        # =====================================================

        post_ocr_correction_applied = (
            bool(
                correction_report.get(
                    "labels_corrected"
                )
            )
            or bool(
                correction_report.get(
                    "marks_table_issues"
                )
            )
        )

        # =====================================================
        # FINAL RETURN
        # =====================================================

        return {
            "correction_attempted": True,

            "ocr_rerun_attempted": True,

            "post_ocr_correction_applied":
                post_ocr_correction_applied,

            "selected": selected,

            "original": {
                "result": initial_result,
                "quality": initial_quality,
            },

            "corrected": candidates[1:],

            "final_result": final_result,

            "final_quality": final_quality,

            "text_correction_report":
                correction_report,

            "detected_languages":
                detected_languages,
        }

    # =========================================================
    # THRESHOLD CANDIDATE
    # =========================================================

    def _run_threshold_candidate(
        self,
        preprocessing_outputs,
        page_number,
        expected_language,
        candidates
    ):
        """
        Run threshold OCR.

        This method is only called when:
        - Enhanced OCR is unavailable, OR
        - Enhanced OCR remains below 90 AND
          produced a meaningful improvement.
        """

        threshold_image = (
            preprocessing_outputs.get(
                "threshold"
            )
        )

        if not threshold_image:

            print(
                "\nThreshold image unavailable."
            )

            print(
                "No further OCR candidate to try."
            )

            return

        print()
        print("=" * 60)
        print("LEVEL 2 — THRESHOLD OCR")
        print("=" * 60)

        print(
            f"Threshold image : "
            f"{threshold_image}"
        )

        threshold_output_dir = (
            self.output_dir
            / f"page_{page_number:03d}"
            / "threshold"
        )

        threshold_output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        print(
            f"Correction output : "
            f"{threshold_output_dir}"
        )

        # -----------------------------------------------------
        # SAME PERSISTENT SURYA SERVER
        # -----------------------------------------------------

        threshold_result = self.surya.run_ocr(
            threshold_image,
            output_dir=str(
                threshold_output_dir
            )
        )

        threshold_quality = (
            self.calculate_result_quality(
                threshold_result,
                expected_language
            )
        )

        threshold_score = float(
            threshold_quality.get(
                "quality_score",
                0
            )
        )

        print(
            f"Threshold quality score : "
            f"{threshold_score:.2f}"
        )

        print(
            f"Threshold status : "
            f"{threshold_quality['status']}"
        )

        candidates.append({
            "name": "threshold",
            "result": threshold_result,
            "quality": threshold_quality,
        })