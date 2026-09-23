# """
# Astra-OCR
# =========

# LEVEL 3 HYBRID OCR SERVICE

# Final fallback OCR layer:

#     OCR.space + Gemini

# Decision flow:

#     OCR.space succeeds + Gemini succeeds
#         -> compare results
#         -> highly similar
#             -> choose best result
#         -> moderately similar
#             -> choose best result
#         -> substantially different
#             -> Gemini adjudication

#     OCR.space succeeds + Gemini fails
#         -> use OCR.space

#     OCR.space fails + Gemini succeeds
#         -> use Gemini

#     OCR.space fails + Gemini fails
#         -> Level3HybridError

# IMPORTANT
# ---------

# This service is designed to work with the EXISTING
# OCRPipelineService call:

#     self.level3.run(
#         input_path=str(original_image),
#         page_number=page_number
#     )

# Do NOT modify OCRPipelineService just to accommodate this service.

# This service does NOT modify:

#     - Surya OCR
#     - preprocessing
#     - Level 2 correction
#     - OCR quality service
#     - database
#     - API routing
# """

# from __future__ import annotations

# import logging
# import re

# from difflib import SequenceMatcher
# from typing import Any, Dict, Optional

# from services.ocrspace_ocr_service import OCRSpaceOCRService
# from services.gemini_ocr_service import GeminiOCRService
# from services.quality_service import OCRQualityService


# logger = logging.getLogger(__name__)


# class Level3HybridError(Exception):
#     """Controlled Level 3 hybrid OCR error."""


# class Level3HybridOCRService:
#     """
#     Level 3 fallback OCR service.

#     OCR.space and Gemini are executed independently.

#     Their outputs are then compared.

#     The service returns a structure compatible with
#     OCRPipelineService.
#     """

#     # ==============================================================
#     # DECISION THRESHOLDS
#     # ==============================================================

#     # Below this -> substantial disagreement.
#     SIMILARITY_THRESHOLD = 0.72

#     # At or above this -> very close agreement.
#     CLOSE_MATCH_THRESHOLD = 0.92

#     # ==============================================================
#     # CONSTRUCTOR
#     # ==============================================================

#     def __init__(
#         self,
#         ocrspace_service: Optional[
#             OCRSpaceOCRService
#         ] = None,
#         gemini_service: Optional[
#             GeminiOCRService
#         ] = None,
#     ):
#         self.ocrspace = (
#             ocrspace_service
#             if ocrspace_service is not None
#             else OCRSpaceOCRService()
#         )

#         self.gemini = (
#             gemini_service
#             if gemini_service is not None
#             else GeminiOCRService()
#         )

#         self.quality_service = OCRQualityService()

#     # ==============================================================
#     # MAIN
#     # ==============================================================

#     def run(
#         self,
#         input_path: Optional[str] = None,
#         image_path: Optional[str] = None,
#         pdf_path: Optional[str] = None,
#         page_number: Optional[int] = None,
#     ) -> Dict[str, Any]:
#         """
#         Run Level 3 hybrid OCR.

#         IMPORTANT:

#         `input_path` is the primary compatibility argument because
#         OCRPipelineService calls:

#             level3.run(
#                 input_path=str(original_image),
#                 page_number=page_number
#             )

#         If input_path is supplied, it is treated as image_path
#         unless an explicit image_path/pdf_path is already provided.
#         """

#         # ==========================================================
#         # INPUT COMPATIBILITY
#         # ==========================================================

#         if (
#             input_path is not None
#             and image_path is None
#             and pdf_path is None
#         ):
#             image_path = input_path

#         if image_path is None and pdf_path is None:
#             raise Level3HybridError(
#                 "Level 3 OCR requires an input image or PDF."
#             )

#         logger.info("=" * 70)
#         logger.info("LEVEL 3 HYBRID OCR")
#         logger.info("=" * 70)

#         logger.info(
#             "Input image : %s",
#             image_path
#         )

#         logger.info(
#             "Input PDF   : %s",
#             pdf_path
#         )

#         logger.info(
#             "Page number : %s",
#             page_number
#         )

#         # ==========================================================
#         # ENGINE RESULT HOLDERS
#         # ==========================================================

#         ocrspace_result = None
#         gemini_result = None

#         ocrspace_error = None
#         gemini_error = None

#         # ==========================================================
#         # OCR.SPACE
#         # ==========================================================

#         try:

#             logger.info("-" * 70)
#             logger.info("Starting OCR.space...")

#             ocrspace_result = (
#                 self.ocrspace.run_ocr(
#                     image_path=image_path,
#                     pdf_path=pdf_path,
#                     page_number=page_number,
#                 )
#             )

#             if not isinstance(
#                 ocrspace_result,
#                 dict
#             ):
#                 raise ValueError(
#                     "OCR.space returned an invalid result."
#                 )

#             logger.info(
#                 "OCR.space succeeded."
#             )

#         except Exception as exc:

#             ocrspace_error = str(exc)

#             logger.warning(
#                 "OCR.space failed: %s",
#                 exc
#             )

#         # ==========================================================
#         # GEMINI
#         # ==========================================================

#         try:

#             logger.info("-" * 70)
#             logger.info("Starting Gemini OCR...")

#             gemini_result = (
#                 self.gemini.run_ocr(
#                     image_path=image_path,
#                     pdf_path=pdf_path,
#                     page_number=page_number,
#                 )
#             )

#             if not isinstance(
#                 gemini_result,
#                 dict
#             ):
#                 raise ValueError(
#                     "Gemini returned an invalid result."
#                 )

#             logger.info(
#                 "Gemini OCR succeeded."
#             )

#         except Exception as exc:

#             gemini_error = str(exc)

#             logger.warning(
#                 "Gemini OCR failed: %s",
#                 exc
#             )

#         # ==========================================================
#         # BOTH FAILED
#         # ==========================================================

#         if (
#             ocrspace_result is None
#             and gemini_result is None
#         ):

#             raise Level3HybridError(
#                 "Both Level 3 OCR engines failed.\n"
#                 f"OCR.space: {ocrspace_error}\n"
#                 f"Gemini: {gemini_error}"
#             )

#         # ==========================================================
#         # ONLY OCR.SPACE WORKED
#         # ==========================================================

#         if (
#             ocrspace_result is not None
#             and gemini_result is None
#         ):

#             logger.info(
#                 "Gemini failed."
#             )

#             logger.info(
#                 "Using OCR.space result."
#             )

#             return self._finalize(
#                 selected_result=ocrspace_result,
#                 selected_source="ocrspace",
#                 ocrspace_result=ocrspace_result,
#                 gemini_result=None,
#                 similarity=None,
#                 adjudicated=False,
#                 errors={
#                     "ocrspace": None,
#                     "gemini": gemini_error,
#                 },
#                 page_number=page_number,
#             )

#         # ==========================================================
#         # ONLY GEMINI WORKED
#         # ==========================================================

#         if (
#             ocrspace_result is None
#             and gemini_result is not None
#         ):

#             logger.info(
#                 "OCR.space failed."
#             )

#             logger.info(
#                 "Using Gemini result."
#             )

#             return self._finalize(
#                 selected_result=gemini_result,
#                 selected_source="gemini",
#                 ocrspace_result=None,
#                 gemini_result=gemini_result,
#                 similarity=None,
#                 adjudicated=False,
#                 errors={
#                     "ocrspace": ocrspace_error,
#                     "gemini": None,
#                 },
#                 page_number=page_number,
#             )

#         # ==========================================================
#         # BOTH WORKED
#         # ==========================================================

#         logger.info(
#             "Both OCR.space and Gemini succeeded."
#         )

#         ocrspace_text = self._clean_text(
#             ocrspace_result.get(
#                 "text",
#                 ""
#             )
#         )

#         gemini_text = self._clean_text(
#             gemini_result.get(
#                 "text",
#                 ""
#             )
#         )

#         # ==========================================================
#         # EMPTY RESULTS
#         # ==========================================================

#         if (
#             not ocrspace_text
#             and not gemini_text
#         ):

#             raise Level3HybridError(
#                 "Both OCR engines returned empty text."
#             )

#         if not ocrspace_text:

#             logger.warning(
#                 "OCR.space returned empty text."
#             )

#             logger.info(
#                 "Using Gemini."
#             )

#             return self._finalize(
#                 selected_result=gemini_result,
#                 selected_source="gemini",
#                 ocrspace_result=ocrspace_result,
#                 gemini_result=gemini_result,
#                 similarity=0.0,
#                 adjudicated=False,
#                 errors={
#                     "ocrspace": None,
#                     "gemini": None,
#                 },
#                 page_number=page_number,
#             )

#         if not gemini_text:

#             logger.warning(
#                 "Gemini returned empty text."
#             )

#             logger.info(
#                 "Using OCR.space."
#             )

#             return self._finalize(
#                 selected_result=ocrspace_result,
#                 selected_source="ocrspace",
#                 ocrspace_result=ocrspace_result,
#                 gemini_result=gemini_result,
#                 similarity=0.0,
#                 adjudicated=False,
#                 errors={
#                     "ocrspace": None,
#                     "gemini": None,
#                 },
#                 page_number=page_number,
#             )

#         # ==========================================================
#         # TEXT SIMILARITY
#         # ==========================================================

#         similarity = self.text_similarity(
#             ocrspace_text,
#             gemini_text
#         )

#         logger.info(
#             "OCR similarity : %.4f",
#             similarity
#         )

#         # ==========================================================
#         # HIGH AGREEMENT
#         # ==========================================================

#         if (
#             similarity
#             >= self.CLOSE_MATCH_THRESHOLD
#         ):

#             logger.info(
#                 "Results are highly similar."
#             )

#             logger.info(
#                 "No adjudication required."
#             )

#             selected_source = (
#                 self.choose_best_without_adjudication(
#                     ocrspace_result,
#                     gemini_result
#                 )
#             )

#             selected_result = (
#                 ocrspace_result
#                 if selected_source == "ocrspace"
#                 else gemini_result
#             )

#             return self._finalize(
#                 selected_result=selected_result,
#                 selected_source=selected_source,
#                 ocrspace_result=ocrspace_result,
#                 gemini_result=gemini_result,
#                 similarity=similarity,
#                 adjudicated=False,
#                 errors={
#                     "ocrspace": None,
#                     "gemini": None,
#                 },
#                 page_number=page_number,
#             )

#         # ==========================================================
#         # MODERATE AGREEMENT
#         # ==========================================================

#         if (
#             similarity
#             >= self.SIMILARITY_THRESHOLD
#         ):

#             logger.info(
#                 "Results are sufficiently similar."
#             )

#             logger.info(
#                 "No adjudication required."
#             )

#             selected_source = (
#                 self.choose_best_without_adjudication(
#                     ocrspace_result,
#                     gemini_result
#                 )
#             )

#             selected_result = (
#                 ocrspace_result
#                 if selected_source == "ocrspace"
#                 else gemini_result
#             )

#             return self._finalize(
#                 selected_result=selected_result,
#                 selected_source=selected_source,
#                 ocrspace_result=ocrspace_result,
#                 gemini_result=gemini_result,
#                 similarity=similarity,
#                 adjudicated=False,
#                 errors={
#                     "ocrspace": None,
#                     "gemini": None,
#                 },
#                 page_number=page_number,
#             )

#         # ==========================================================
#         # SUBSTANTIAL DISAGREEMENT
#         # ==========================================================

#         logger.warning(
#             "OCR.space and Gemini substantially disagree."
#         )

#         logger.info(
#             "Starting Gemini adjudication..."
#         )

#         try:

#             adjudication = (
#                 self.gemini.adjudicate(
#                     ocrspace_text=ocrspace_text,
#                     gemini_text=gemini_text,
#                     page_number=page_number,
#                 )
#             )

#             if not isinstance(
#                 adjudication,
#                 dict
#             ):
#                 raise ValueError(
#                     "Gemini adjudication returned an invalid result."
#                 )

#             logger.info(
#                 "Gemini adjudication succeeded."
#             )

#             return self._finalize(
#                 selected_result=adjudication,
#                 selected_source="gemini_adjudication",
#                 ocrspace_result=ocrspace_result,
#                 gemini_result=gemini_result,
#                 similarity=similarity,
#                 adjudicated=True,
#                 errors={
#                     "ocrspace": None,
#                     "gemini": None,
#                 },
#                 page_number=page_number,
#             )

#         except Exception as exc:

#             logger.warning(
#                 "Gemini adjudication failed: %s",
#                 exc
#             )

#             logger.info(
#                 "Using deterministic fallback."
#             )

#             selected_source = (
#                 self.choose_best_without_adjudication(
#                     ocrspace_result,
#                     gemini_result
#                 )
#             )

#             selected_result = (
#                 ocrspace_result
#                 if selected_source == "ocrspace"
#                 else gemini_result
#             )

#             return self._finalize(
#                 selected_result=selected_result,
#                 selected_source=selected_source,
#                 ocrspace_result=ocrspace_result,
#                 gemini_result=gemini_result,
#                 similarity=similarity,
#                 adjudicated=False,
#                 adjudication_failed=True,
#                 errors={
#                     "ocrspace": None,
#                     "gemini": None,
#                     "adjudication": str(exc),
#                 },
#                 page_number=page_number,
#             )

#     # ==============================================================
#     # FINALIZE LEVEL 3 RESULT
#     # ==============================================================

#     def _finalize(
#         self,
#         selected_result: Dict[str, Any],
#         selected_source: str,
#         ocrspace_result: Optional[
#             Dict[str, Any]
#         ],
#         gemini_result: Optional[
#             Dict[str, Any]
#         ],
#         similarity: Optional[float],
#         adjudicated: bool,
#         errors: Dict[str, Any],
#         page_number: Optional[int],
#         adjudication_failed: bool = False,
#     ) -> Dict[str, Any]:
#         """
#         Build the result expected by OCRPipelineService.

#         IMPORTANT:

#         OCRPipelineService expects:

#             final_result
#             final_quality
#             selected_source

#         Therefore Level 3 provides those fields here.
#         """

#         if not isinstance(
#             selected_result,
#             dict
#         ):
#             selected_result = {
#                 "text": str(
#                     selected_result
#                 )
#             }

#         final_text = self._clean_text(
#             selected_result.get(
#                 "text",
#                 ""
#             )
#         )

#         # ----------------------------------------------------------
#         # Calculate Level 3 quality.
#         # ----------------------------------------------------------

#         final_quality = (
#             self._calculate_quality(
#                 selected_result=selected_result,
#                 text=final_text
#             )
#         )

#         logger.info(
#             "Level 3 final quality : %.2f",
#             final_quality.get(
#                 "quality_score",
#                 0.0
#             )
#         )

#         logger.info(
#             "Level 3 selected source : %s",
#             selected_source
#         )

#         return {
#             # ------------------------------------------------------
#             # Pipeline-compatible fields
#             # ------------------------------------------------------

#             "final_result": selected_result,

#             "final_quality": final_quality,

#             "selected_source": selected_source,

#             # ------------------------------------------------------
#             # Level information
#             # ------------------------------------------------------

#             "level": 3,

#             "source": selected_source,

#             "text": final_text,

#             # ------------------------------------------------------
#             # Full selected result
#             # ------------------------------------------------------

#             "selected_result": selected_result,

#             # ------------------------------------------------------
#             # Comparison information
#             # ------------------------------------------------------

#             "comparison": {
#                 "similarity": similarity,
#                 "adjudicated": adjudicated,
#                 "adjudication_failed": (
#                     adjudication_failed
#                 ),
#             },

#             # ------------------------------------------------------
#             # Raw engine results
#             # ------------------------------------------------------

#             "engines": {
#                 "ocrspace": ocrspace_result,
#                 "gemini": gemini_result,
#             },

#             # ------------------------------------------------------
#             # Errors
#             # ------------------------------------------------------

#             "errors": errors,

#             # ------------------------------------------------------
#             # Page information
#             # ------------------------------------------------------

#             "page_number": page_number,
#         }

#     # ==============================================================
#     # QUALITY
#     # ==============================================================

#     def _calculate_quality(
#         self,
#         selected_result: Dict[str, Any],
#         text: str,
#     ) -> Dict[str, Any]:
#         """
#         Calculate a Level 3 quality score.

#         This uses the existing OCRQualityService so the Level 3
#         result follows the same quality concept as the rest of
#         Astra-OCR.

#         If the external OCR engine provides structured blocks,
#         they are used when available.
#         """

#         # ----------------------------------------------------------
#         # Extract blocks when available.
#         # ----------------------------------------------------------

#         raw_blocks = selected_result.get(
#             "results",
#             []
#         )

#         quality_blocks = []

#         if isinstance(
#             raw_blocks,
#             list
#         ):

#             for block in raw_blocks:

#                 if not isinstance(
#                     block,
#                     dict
#                 ):
#                     continue

#                 quality_blocks.append({
#                     "text": block.get(
#                         "text",
#                         ""
#                     ),

#                     "language": block.get(
#                         "language",
#                         "unknown"
#                     ),

#                     "bbox": block.get(
#                         "bbox"
#                     ),

#                     "confidence": block.get(
#                         "confidence",
#                         0.0
#                     ),
#                 })

#         # ----------------------------------------------------------
#         # Page dimensions.
#         # ----------------------------------------------------------

#         page_width = selected_result.get(
#             "page_width"
#         )

#         page_height = selected_result.get(
#             "page_height"
#         )

#         if (
#             page_width is None
#             or page_height is None
#         ):

#             image_bbox = selected_result.get(
#                 "image_bbox"
#             )

#             if (
#                 image_bbox
#                 and len(image_bbox) >= 4
#             ):

#                 page_width = image_bbox[2]
#                 page_height = image_bbox[3]

#         # ----------------------------------------------------------
#         # Layout confidence.
#         # ----------------------------------------------------------

#         layout_confidences = []

#         for block in quality_blocks:

#             value = block.get(
#                 "layout_confidence"
#             )

#             if value is None:
#                 continue

#             try:

#                 layout_confidences.append(
#                     float(value)
#                 )

#             except (
#                 TypeError,
#                 ValueError
#             ):

#                 pass

#         layout_confidence = None

#         if layout_confidences:

#             layout_confidence = (
#                 sum(
#                     layout_confidences
#                 )
#                 / len(
#                     layout_confidences
#                 )
#             )

#         # ----------------------------------------------------------
#         # If no structured blocks exist, create one text block.
#         # ----------------------------------------------------------

#         if not quality_blocks:

#             confidence = (
#                 self._extract_confidence(
#                     selected_result
#                 )
#             )

#             quality_blocks = [{
#                 "text": text,

#                 "language": selected_result.get(
#                     "language",
#                     "unknown"
#                 ),

#                 "bbox": None,

#                 "confidence": (
#                     confidence
#                     if confidence is not None
#                     else 0.0
#                 ),
#             }]

#         # ----------------------------------------------------------
#         # Calculate quality.
#         # ----------------------------------------------------------

#         try:

#             quality = (
#                 self.quality_service.calculate_quality(
#                     text=text,

#                     blocks=quality_blocks,

#                     page_width=page_width,

#                     page_height=page_height,

#                     expected_language=None,

#                     layout_confidence=(
#                         layout_confidence
#                     ),
#                 )
#             )

#             if isinstance(
#                 quality,
#                 dict
#             ):
#                 return quality

#         except Exception as exc:

#             logger.warning(
#                 "Level 3 quality calculation failed: %s",
#                 exc
#             )

#         # ----------------------------------------------------------
#         # Safe fallback.
#         # ----------------------------------------------------------

#         fallback_score = (
#             self._text_quality_score(
#                 text
#             )
#             * 100.0
#         )

#         status = "good"

#         if fallback_score < 60:
#             status = "retry"

#         elif fallback_score < 80:
#             status = "review"

#         return {
#             "quality_score": round(
#                 fallback_score,
#                 2
#             ),

#             "status": status,

#             "text_score": round(
#                 fallback_score,
#                 2
#             ),

#             "language_score": 0.0,

#             "character_score": 0.0,

#             "coverage_score": 0.0,

#             "confidence_score": 0.0,
#         }

#     # ==============================================================
#     # TEXT SIMILARITY
#     # ==============================================================

#     @staticmethod
#     def text_similarity(
#         text_a: str,
#         text_b: str,
#     ) -> float:
#         """
#         Compare OCR outputs.

#         Hindi, Gujarati, English and mixed-language Unicode
#         characters are preserved.
#         """

#         a = (
#             Level3HybridOCRService
#             ._normalize_for_similarity(
#                 text_a
#             )
#         )

#         b = (
#             Level3HybridOCRService
#             ._normalize_for_similarity(
#                 text_b
#             )
#         )

#         if not a and not b:
#             return 1.0

#         if not a or not b:
#             return 0.0

#         return SequenceMatcher(
#             None,
#             a,
#             b
#         ).ratio()

#     # ==============================================================
#     # CHOOSE BEST RESULT
#     # ==============================================================

#     def choose_best_without_adjudication(
#         self,
#         ocrspace_result: Dict[str, Any],
#         gemini_result: Dict[str, Any],
#     ) -> str:
#         """
#         Deterministically select the better result.

#         Priority:

#             1. Table structure
#             2. Form structure
#             3. Text quality
#             4. Confidence
#             5. Gemini deterministic tie-breaker
#         """

#         ocrspace_text = self._clean_text(
#             ocrspace_result.get(
#                 "text",
#                 ""
#             )
#         )

#         gemini_text = self._clean_text(
#             gemini_result.get(
#                 "text",
#                 ""
#             )
#         )

#         if not ocrspace_text:
#             return "gemini"

#         if not gemini_text:
#             return "ocrspace"

#         # ----------------------------------------------------------
#         # TABLE
#         # ----------------------------------------------------------

#         ocrspace_table = (
#             self._table_structure_score(
#                 ocrspace_text
#             )
#         )

#         gemini_table = (
#             self._table_structure_score(
#                 gemini_text
#             )
#         )

#         logger.info(
#             "OCR.space table score : %.3f",
#             ocrspace_table
#         )

#         logger.info(
#             "Gemini table score    : %.3f",
#             gemini_table
#         )

#         if gemini_table > ocrspace_table:
#             return "gemini"

#         if ocrspace_table > gemini_table:
#             return "ocrspace"

#         # ----------------------------------------------------------
#         # FORM
#         # ----------------------------------------------------------

#         ocrspace_form = (
#             self._form_structure_score(
#                 ocrspace_text
#             )
#         )

#         gemini_form = (
#             self._form_structure_score(
#                 gemini_text
#             )
#         )

#         logger.info(
#             "OCR.space form score : %.3f",
#             ocrspace_form
#         )

#         logger.info(
#             "Gemini form score    : %.3f",
#             gemini_form
#         )

#         if gemini_form > ocrspace_form:
#             return "gemini"

#         if ocrspace_form > gemini_form:
#             return "ocrspace"

#         # ----------------------------------------------------------
#         # TEXT QUALITY
#         # ----------------------------------------------------------

#         ocrspace_quality = (
#             self._text_quality_score(
#                 ocrspace_text
#             )
#         )

#         gemini_quality = (
#             self._text_quality_score(
#                 gemini_text
#             )
#         )

#         logger.info(
#             "OCR.space text quality : %.3f",
#             ocrspace_quality
#         )

#         logger.info(
#             "Gemini text quality    : %.3f",
#             gemini_quality
#         )

#         if gemini_quality > ocrspace_quality:
#             return "gemini"

#         if ocrspace_quality > gemini_quality:
#             return "ocrspace"

#         # ----------------------------------------------------------
#         # CONFIDENCE
#         # ----------------------------------------------------------

#         ocrspace_confidence = (
#             self._extract_confidence(
#                 ocrspace_result
#             )
#         )

#         gemini_confidence = (
#             self._extract_confidence(
#                 gemini_result
#             )
#         )

#         if (
#             ocrspace_confidence is not None
#             and gemini_confidence is not None
#         ):

#             logger.info(
#                 "OCR.space confidence : %.3f",
#                 ocrspace_confidence
#             )

#             logger.info(
#                 "Gemini confidence    : %.3f",
#                 gemini_confidence
#             )

#             if (
#                 gemini_confidence
#                 > ocrspace_confidence
#             ):
#                 return "gemini"

#             if (
#                 ocrspace_confidence
#                 > gemini_confidence
#             ):
#                 return "ocrspace"

#         # ----------------------------------------------------------
#         # SAFE DEFAULT
#         # ----------------------------------------------------------

#         return "gemini"

#     # ==============================================================
#     # CONFIDENCE EXTRACTION
#     # ==============================================================

#     @staticmethod
#     def _extract_confidence(
#         result: Dict[str, Any]
#     ) -> Optional[float]:
#         """
#         Extract confidence from common OCR result formats.
#         """

#         if not isinstance(
#             result,
#             dict
#         ):
#             return None

#         possible_keys = (
#             "confidence",
#             "overall_confidence",
#             "score",
#         )

#         for key in possible_keys:

#             value = result.get(
#                 key
#             )

#             if value is None:
#                 continue

#             try:

#                 value = float(
#                     value
#                 )

#                 if (
#                     value > 1.0
#                     and value <= 100.0
#                 ):
#                     value /= 100.0

#                 return max(
#                     0.0,
#                     min(
#                         value,
#                         1.0
#                     )
#                 )

#             except (
#                 TypeError,
#                 ValueError
#             ):

#                 pass

#         # ----------------------------------------------------------
#         # Block-level confidence
#         # ----------------------------------------------------------

#         blocks = result.get(
#             "results"
#         )

#         if isinstance(
#             blocks,
#             list
#         ):

#             confidences = []

#             for block in blocks:

#                 if not isinstance(
#                     block,
#                     dict
#                 ):
#                     continue

#                 value = block.get(
#                     "confidence"
#                 )

#                 if value is None:
#                     continue

#                 try:

#                     value = float(
#                         value
#                     )

#                     if (
#                         value > 1.0
#                         and value <= 100.0
#                     ):
#                         value /= 100.0

#                     confidences.append(
#                         max(
#                             0.0,
#                             min(
#                                 value,
#                                 1.0
#                             )
#                         )
#                     )

#                 except (
#                     TypeError,
#                     ValueError
#                 ):

#                     continue

#             if confidences:

#                 return (
#                     sum(
#                         confidences
#                     )
#                     / len(
#                         confidences
#                     )
#                 )

#         return None

#     # ==============================================================
#     # TEXT QUALITY
#     # ==============================================================

#     @staticmethod
#     def _text_quality_score(
#         text: str
#     ) -> float:
#         """
#         Lightweight language-independent OCR quality heuristic.
#         """

#         if not text:
#             return 0.0

#         score = 0.0

#         length = len(
#             text
#         )

#         # ----------------------------------------------------------
#         # Length
#         # ----------------------------------------------------------

#         if length >= 20:
#             score += 0.20

#         if length >= 100:
#             score += 0.10

#         if length >= 300:
#             score += 0.10

#         # ----------------------------------------------------------
#         # Words
#         # ----------------------------------------------------------

#         words = text.split()

#         if len(words) >= 5:
#             score += 0.10

#         if len(words) >= 20:
#             score += 0.10

#         # ----------------------------------------------------------
#         # Hindi
#         # ----------------------------------------------------------

#         if any(
#             "\u0900" <= char <= "\u097F"
#             for char in text
#         ):
#             score += 0.10

#         # ----------------------------------------------------------
#         # Gujarati
#         # ----------------------------------------------------------

#         if any(
#             "\u0A80" <= char <= "\u0AFF"
#             for char in text
#         ):
#             score += 0.10

#         # ----------------------------------------------------------
#         # English
#         # ----------------------------------------------------------

#         if re.search(
#             r"[A-Za-z]",
#             text
#         ):
#             score += 0.05

#         # ----------------------------------------------------------
#         # Replacement character
#         # ----------------------------------------------------------

#         if "\ufffd" not in text:
#             score += 0.05

#         # ----------------------------------------------------------
#         # Punctuation noise
#         # ----------------------------------------------------------

#         if not re.search(
#             r"[!?.,:;]{5,}",
#             text
#         ):
#             score += 0.05

#         return min(
#             score,
#             1.0
#         )

#     # ==============================================================
#     # TABLE STRUCTURE
#     # ==============================================================

#     @staticmethod
#     def _table_structure_score(
#         text: str
#     ) -> float:
#         """
#         Estimate whether OCR output preserves table structure.
#         """

#         if not text:
#             return 0.0

#         lines = [
#             line.strip()
#             for line in text.splitlines()
#             if line.strip()
#         ]

#         if not lines:
#             return 0.0

#         score = 0.0

#         pipe_lines = sum(
#             1
#             for line in lines
#             if line.count("|") >= 2
#         )

#         if pipe_lines >= 2:
#             score += 0.5

#         if pipe_lines >= 4:
#             score += 0.3

#         if re.search(
#             r"\|\s*:?-{2,}:?\s*\|",
#             text
#         ):
#             score += 0.2

#         return min(
#             score,
#             1.0
#         )

#     # ==============================================================
#     # FORM STRUCTURE
#     # ==============================================================

#     @staticmethod
#     def _form_structure_score(
#         text: str
#     ) -> float:
#         """
#         Estimate label:value form structure.
#         """

#         if not text:
#             return 0.0

#         lines = [
#             line.strip()
#             for line in text.splitlines()
#             if line.strip()
#         ]

#         if not lines:
#             return 0.0

#         label_value_lines = 0

#         for line in lines:

#             if re.search(
#                 r"^[^:\n]{1,80}:\s*.+$",
#                 line
#             ):
#                 label_value_lines += 1

#         if label_value_lines >= 5:
#             return 1.0

#         if label_value_lines >= 3:
#             return 0.7

#         if label_value_lines >= 1:
#             return 0.3

#         return 0.0

#     # ==============================================================
#     # CLEAN TEXT
#     # ==============================================================

#     @staticmethod
#     def _clean_text(
#         text: Any
#     ) -> str:
#         """
#         Clean line endings without destroying multilingual
#         Unicode text or document structure.
#         """

#         if text is None:
#             return ""

#         text = str(
#             text
#         )

#         text = text.replace(
#             "\r\n",
#             "\n"
#         )

#         text = text.replace(
#             "\r",
#             "\n"
#         )

#         lines = [
#             line.rstrip()
#             for line in text.splitlines()
#         ]

#         return "\n".join(
#             lines
#         ).strip()

#     # ==============================================================
#     # NORMALIZE FOR SIMILARITY
#     # ==============================================================

#     @staticmethod
#     def _normalize_for_similarity(
#         text: str
#     ) -> str:
#         """
#         Normalize text for comparison.

#         Hindi, Gujarati and English characters are preserved.
#         """

#         text = (
#             Level3HybridOCRService
#             ._clean_text(
#                 text
#             )
#         )

#         text = re.sub(
#             r"\s+",
#             " ",
#             text
#         )

#         return text.strip().casefold()






































"""
Astra-OCR
=========

LEVEL 3 HYBRID OCR SERVICE

Final fallback OCR layer:

    OCR.space + Gemini

Decision flow:

    OCR.space succeeds + Gemini succeeds
        -> compare results
        -> highly similar
            -> choose best result
        -> moderately similar
            -> choose best result
        -> substantially different
            -> Gemini adjudication

    OCR.space succeeds + Gemini fails
        -> use OCR.space

    OCR.space fails + Gemini succeeds
        -> use Gemini

    OCR.space fails + Gemini fails
        -> Level3HybridError

PERFORMANCE OPTIMIZATION
-------------------------

OCR.space and Gemini are independent OCR engines.

They are executed concurrently so Level 3 does not wait for
OCR.space to finish before starting Gemini.

The Level 3 decision logic itself is unchanged.

This service is designed to work with the EXISTING
OCRPipelineService call:

    self.level3.run(
        input_path=str(original_image),
        page_number=page_number
    )

Do NOT modify OCRPipelineService just to accommodate this service.

This service does NOT modify:

    - Surya OCR
    - preprocessing
    - Level 2 correction
    - OCR quality service
    - database
    - API routing
"""

from __future__ import annotations

import logging
import re

from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from typing import Any, Dict, Optional

from services.ocrspace_ocr_service import OCRSpaceOCRService
from services.gemini_ocr_service import GeminiOCRService
from services.quality_service import OCRQualityService


logger = logging.getLogger(__name__)


class Level3HybridError(Exception):
    """Controlled Level 3 hybrid OCR error."""


class Level3HybridOCRService:
    """
    Level 3 fallback OCR service.

    OCR.space and Gemini are executed independently and concurrently.

    Their outputs are then compared.

    The service returns a structure compatible with
    OCRPipelineService.
    """

    # ==============================================================
    # DECISION THRESHOLDS
    # ==============================================================

    # Below this -> substantial disagreement.
    SIMILARITY_THRESHOLD = 0.72

    # At or above this -> very close agreement.
    CLOSE_MATCH_THRESHOLD = 0.92

    # ==============================================================
    # CONSTRUCTOR
    # ==============================================================

    def __init__(
        self,
        ocrspace_service: Optional[
            OCRSpaceOCRService
        ] = None,
        gemini_service: Optional[
            GeminiOCRService
        ] = None,
    ):
        self.ocrspace = (
            ocrspace_service
            if ocrspace_service is not None
            else OCRSpaceOCRService()
        )

        self.gemini = (
            gemini_service
            if gemini_service is not None
            else GeminiOCRService()
        )

        self.quality_service = OCRQualityService()

    # ==============================================================
    # MAIN
    # ==============================================================

    def run(
        self,
        input_path: Optional[str] = None,
        image_path: Optional[str] = None,
        pdf_path: Optional[str] = None,
        page_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run Level 3 hybrid OCR.

        IMPORTANT:

        `input_path` is the primary compatibility argument because
        OCRPipelineService calls:

            level3.run(
                input_path=str(original_image),
                page_number=page_number
            )

        If input_path is supplied, it is treated as image_path
        unless an explicit image_path/pdf_path is already provided.
        """

        # ==========================================================
        # INPUT COMPATIBILITY
        # ==========================================================

        if (
            input_path is not None
            and image_path is None
            and pdf_path is None
        ):
            image_path = input_path

        if image_path is None and pdf_path is None:
            raise Level3HybridError(
                "Level 3 OCR requires an input image or PDF."
            )

        logger.info("=" * 70)
        logger.info("LEVEL 3 HYBRID OCR")
        logger.info("=" * 70)

        logger.info(
            "Input image : %s",
            image_path
        )

        logger.info(
            "Input PDF   : %s",
            pdf_path
        )

        logger.info(
            "Page number : %s",
            page_number
        )

        # ==========================================================
        # ENGINE RESULT HOLDERS
        # ==========================================================

        ocrspace_result = None
        gemini_result = None

        ocrspace_error = None
        gemini_error = None

        # ==========================================================
        # OCR.SPACE + GEMINI
        # RUN CONCURRENTLY
        # ==========================================================
        #
        # OLD:
        #
        #     OCR.space
        #        ↓
        #     wait
        #        ↓
        #     Gemini
        #
        # NEW:
        #
        #     OCR.space ──┐
        #                 ├── results
        #     Gemini ─────┘
        #
        # Both engines are independent, so this reduces the total
        # waiting time to approximately the slower engine's time.
        #
        # No Level 3 decision logic is changed.
        # ==========================================================

        def run_ocrspace():
            logger.info("-" * 70)
            logger.info("Starting OCR.space...")

            result = self.ocrspace.run_ocr(
                image_path=image_path,
                pdf_path=pdf_path,
                page_number=page_number,
            )

            if not isinstance(
                result,
                dict
            ):
                raise ValueError(
                    "OCR.space returned an invalid result."
                )

            return result

        def run_gemini():
            logger.info("-" * 70)
            logger.info("Starting Gemini OCR...")

            result = self.gemini.run_ocr(
                image_path=image_path,
                pdf_path=pdf_path,
                page_number=page_number,
            )

            if not isinstance(
                result,
                dict
            ):
                raise ValueError(
                    "Gemini returned an invalid result."
                )

            return result

        logger.info(
            "Starting OCR.space and Gemini concurrently..."
        )

        # ----------------------------------------------------------
        # Two workers are enough because there are exactly two
        # independent OCR engines.
        # ----------------------------------------------------------

        with ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="level3"
        ) as executor:

            future_ocrspace = executor.submit(
                run_ocrspace
            )

            future_gemini = executor.submit(
                run_gemini
            )

            futures = {
                future_ocrspace: "ocrspace",
                future_gemini: "gemini",
            }

            for future in as_completed(
                futures
            ):

                engine_name = futures[
                    future
                ]

                try:

                    result = future.result()

                    if engine_name == "ocrspace":

                        ocrspace_result = result

                        logger.info(
                            "OCR.space succeeded."
                        )

                    else:

                        gemini_result = result

                        logger.info(
                            "Gemini OCR succeeded."
                        )

                except Exception as exc:

                    if engine_name == "ocrspace":

                        ocrspace_error = str(
                            exc
                        )

                        logger.warning(
                            "OCR.space failed: %s",
                            exc
                        )

                    else:

                        gemini_error = str(
                            exc
                        )

                        logger.warning(
                            "Gemini OCR failed: %s",
                            exc
                        )

        logger.info(
            "Concurrent Level 3 OCR execution completed."
        )

        # ==========================================================
        # BOTH FAILED
        # ==========================================================

        if (
            ocrspace_result is None
            and gemini_result is None
        ):

            raise Level3HybridError(
                "Both Level 3 OCR engines failed.\n"
                f"OCR.space: {ocrspace_error}\n"
                f"Gemini: {gemini_error}"
            )

        # ==========================================================
        # ONLY OCR.SPACE WORKED
        # ==========================================================

        if (
            ocrspace_result is not None
            and gemini_result is None
        ):

            logger.info(
                "Gemini failed."
            )

            logger.info(
                "Using OCR.space result."
            )

            return self._finalize(
                selected_result=ocrspace_result,
                selected_source="ocrspace",
                ocrspace_result=ocrspace_result,
                gemini_result=None,
                similarity=None,
                adjudicated=False,
                errors={
                    "ocrspace": None,
                    "gemini": gemini_error,
                },
                page_number=page_number,
            )

        # ==========================================================
        # ONLY GEMINI WORKED
        # ==========================================================

        if (
            ocrspace_result is None
            and gemini_result is not None
        ):

            logger.info(
                "OCR.space failed."
            )

            logger.info(
                "Using Gemini result."
            )

            return self._finalize(
                selected_result=gemini_result,
                selected_source="gemini",
                ocrspace_result=None,
                gemini_result=gemini_result,
                similarity=None,
                adjudicated=False,
                errors={
                    "ocrspace": ocrspace_error,
                    "gemini": None,
                },
                page_number=page_number,
            )

        # ==========================================================
        # BOTH WORKED
        # ==========================================================

        logger.info(
            "Both OCR.space and Gemini succeeded."
        )

        ocrspace_text = self._clean_text(
            ocrspace_result.get(
                "text",
                ""
            )
        )

        gemini_text = self._clean_text(
            gemini_result.get(
                "text",
                ""
            )
        )

        # ==========================================================
        # EMPTY RESULTS
        # ==========================================================

        if (
            not ocrspace_text
            and not gemini_text
        ):

            raise Level3HybridError(
                "Both OCR engines returned empty text."
            )

        if not ocrspace_text:

            logger.warning(
                "OCR.space returned empty text."
            )

            logger.info(
                "Using Gemini."
            )

            return self._finalize(
                selected_result=gemini_result,
                selected_source="gemini",
                ocrspace_result=ocrspace_result,
                gemini_result=gemini_result,
                similarity=0.0,
                adjudicated=False,
                errors={
                    "ocrspace": None,
                    "gemini": None,
                },
                page_number=page_number,
            )

        if not gemini_text:

            logger.warning(
                "Gemini returned empty text."
            )

            logger.info(
                "Using OCR.space."
            )

            return self._finalize(
                selected_result=ocrspace_result,
                selected_source="ocrspace",
                ocrspace_result=ocrspace_result,
                gemini_result=gemini_result,
                similarity=0.0,
                adjudicated=False,
                errors={
                    "ocrspace": None,
                    "gemini": None,
                },
                page_number=page_number,
            )

        # ==========================================================
        # TEXT SIMILARITY
        # ==========================================================

        similarity = self.text_similarity(
            ocrspace_text,
            gemini_text
        )

        logger.info(
            "OCR similarity : %.4f",
            similarity
        )

        # ==========================================================
        # HIGH AGREEMENT
        # ==========================================================

        if (
            similarity
            >= self.CLOSE_MATCH_THRESHOLD
        ):

            logger.info(
                "Results are highly similar."
            )

            logger.info(
                "No adjudication required."
            )

            selected_source = (
                self.choose_best_without_adjudication(
                    ocrspace_result,
                    gemini_result
                )
            )

            selected_result = (
                ocrspace_result
                if selected_source == "ocrspace"
                else gemini_result
            )

            return self._finalize(
                selected_result=selected_result,
                selected_source=selected_source,
                ocrspace_result=ocrspace_result,
                gemini_result=gemini_result,
                similarity=similarity,
                adjudicated=False,
                errors={
                    "ocrspace": None,
                    "gemini": None,
                },
                page_number=page_number,
            )

        # ==========================================================
        # MODERATE AGREEMENT
        # ==========================================================

        if (
            similarity
            >= self.SIMILARITY_THRESHOLD
        ):

            logger.info(
                "Results are sufficiently similar."
            )

            logger.info(
                "No adjudication required."
            )

            selected_source = (
                self.choose_best_without_adjudication(
                    ocrspace_result,
                    gemini_result
                )
            )

            selected_result = (
                ocrspace_result
                if selected_source == "ocrspace"
                else gemini_result
            )

            return self._finalize(
                selected_result=selected_result,
                selected_source=selected_source,
                ocrspace_result=ocrspace_result,
                gemini_result=gemini_result,
                similarity=similarity,
                adjudicated=False,
                errors={
                    "ocrspace": None,
                    "gemini": None,
                },
                page_number=page_number,
            )

        # ==========================================================
        # SUBSTANTIAL DISAGREEMENT
        # ==========================================================

        logger.warning(
            "OCR.space and Gemini substantially disagree."
        )

        logger.info(
            "Starting Gemini adjudication..."
        )

        try:

            adjudication = (
                self.gemini.adjudicate(
                    ocrspace_text=ocrspace_text,
                    gemini_text=gemini_text,
                    page_number=page_number,
                )
            )

            if not isinstance(
                adjudication,
                dict
            ):
                raise ValueError(
                    "Gemini adjudication returned an invalid result."
                )

            logger.info(
                "Gemini adjudication succeeded."
            )

            return self._finalize(
                selected_result=adjudication,
                selected_source="gemini_adjudication",
                ocrspace_result=ocrspace_result,
                gemini_result=gemini_result,
                similarity=similarity,
                adjudicated=True,
                errors={
                    "ocrspace": None,
                    "gemini": None,
                },
                page_number=page_number,
            )

        except Exception as exc:

            logger.warning(
                "Gemini adjudication failed: %s",
                exc
            )

            logger.info(
                "Using deterministic fallback."
            )

            selected_source = (
                self.choose_best_without_adjudication(
                    ocrspace_result,
                    gemini_result
                )
            )

            selected_result = (
                ocrspace_result
                if selected_source == "ocrspace"
                else gemini_result
            )

            return self._finalize(
                selected_result=selected_result,
                selected_source=selected_source,
                ocrspace_result=ocrspace_result,
                gemini_result=gemini_result,
                similarity=similarity,
                adjudicated=False,
                adjudication_failed=True,
                errors={
                    "ocrspace": None,
                    "gemini": None,
                    "adjudication": str(exc),
                },
                page_number=page_number,
            )

    # ==============================================================
    # FINALIZE LEVEL 3 RESULT
    # ==============================================================

    def _finalize(
        self,
        selected_result: Dict[str, Any],
        selected_source: str,
        ocrspace_result: Optional[
            Dict[str, Any]
        ],
        gemini_result: Optional[
            Dict[str, Any]
        ],
        similarity: Optional[float],
        adjudicated: bool,
        errors: Dict[str, Any],
        page_number: Optional[int],
        adjudication_failed: bool = False,
    ) -> Dict[str, Any]:
        """
        Build the result expected by OCRPipelineService.

        IMPORTANT:

        OCRPipelineService expects:

            final_result
            final_quality
            selected_source

        Therefore Level 3 provides those fields here.
        """

        if not isinstance(
            selected_result,
            dict
        ):
            selected_result = {
                "text": str(
                    selected_result
                )
            }

        final_text = self._clean_text(
            selected_result.get(
                "text",
                ""
            )
        )

        # ----------------------------------------------------------
        # Calculate Level 3 quality.
        # ----------------------------------------------------------

        final_quality = (
            self._calculate_quality(
                selected_result=selected_result,
                text=final_text
            )
        )

        logger.info(
            "Level 3 final quality : %.2f",
            final_quality.get(
                "quality_score",
                0.0
            )
        )

        logger.info(
            "Level 3 selected source : %s",
            selected_source
        )

        return {
            # ------------------------------------------------------
            # Pipeline-compatible fields
            # ------------------------------------------------------

            "final_result": selected_result,

            "final_quality": final_quality,

            "selected_source": selected_source,

            # ------------------------------------------------------
            # Level information
            # ------------------------------------------------------

            "level": 3,

            "source": selected_source,

            "text": final_text,

            # ------------------------------------------------------
            # Full selected result
            # ------------------------------------------------------

            "selected_result": selected_result,

            # ------------------------------------------------------
            # Comparison information
            # ------------------------------------------------------

            "comparison": {
                "similarity": similarity,
                "adjudicated": adjudicated,
                "adjudication_failed": (
                    adjudication_failed
                ),
            },

            # ------------------------------------------------------
            # Raw engine results
            # ------------------------------------------------------

            "engines": {
                "ocrspace": ocrspace_result,
                "gemini": gemini_result,
            },

            # ------------------------------------------------------
            # Errors
            # ------------------------------------------------------

            "errors": errors,

            # ------------------------------------------------------
            # Page information
            # ------------------------------------------------------

            "page_number": page_number,
        }

    # ==============================================================
    # QUALITY
    # ==============================================================

    def _calculate_quality(
        self,
        selected_result: Dict[str, Any],
        text: str,
    ) -> Dict[str, Any]:
        """
        Calculate a Level 3 quality score.

        This uses the existing OCRQualityService so the Level 3
        result follows the same quality concept as the rest of
        Astra-OCR.

        If the external OCR engine provides structured blocks,
        they are used when available.
        """

        # ----------------------------------------------------------
        # Extract blocks when available.
        # ----------------------------------------------------------

        raw_blocks = selected_result.get(
            "results",
            []
        )

        quality_blocks = []

        if isinstance(
            raw_blocks,
            list
        ):

            for block in raw_blocks:

                if not isinstance(
                    block,
                    dict
                ):
                    continue

                quality_blocks.append({
                    "text": block.get(
                        "text",
                        ""
                    ),

                    "language": block.get(
                        "language",
                        "unknown"
                    ),

                    "bbox": block.get(
                        "bbox"
                    ),

                    "confidence": block.get(
                        "confidence",
                        0.0
                    ),
                })

        # ----------------------------------------------------------
        # Page dimensions.
        # ----------------------------------------------------------

        page_width = selected_result.get(
            "page_width"
        )

        page_height = selected_result.get(
            "page_height"
        )

        if (
            page_width is None
            or page_height is None
        ):

            image_bbox = selected_result.get(
                "image_bbox"
            )

            if (
                image_bbox
                and len(image_bbox) >= 4
            ):

                page_width = image_bbox[2]
                page_height = image_bbox[3]

        # ----------------------------------------------------------
        # Layout confidence.
        # ----------------------------------------------------------

        layout_confidences = []

        for block in quality_blocks:

            value = block.get(
                "layout_confidence"
            )

            if value is None:
                continue

            try:

                layout_confidences.append(
                    float(value)
                )

            except (
                TypeError,
                ValueError
            ):

                pass

        layout_confidence = None

        if layout_confidences:

            layout_confidence = (
                sum(
                    layout_confidences
                )
                / len(
                    layout_confidences
                )
            )

        # ----------------------------------------------------------
        # If no structured blocks exist, create one text block.
        # ----------------------------------------------------------

        if not quality_blocks:

            confidence = (
                self._extract_confidence(
                    selected_result
                )
            )

            quality_blocks = [{
                "text": text,

                "language": selected_result.get(
                    "language",
                    "unknown"
                ),

                "bbox": None,

                "confidence": (
                    confidence
                    if confidence is not None
                    else 0.0
                ),
            }]

        # ----------------------------------------------------------
        # Calculate quality.
        # ----------------------------------------------------------

        try:

            quality = (
                self.quality_service.calculate_quality(
                    text=text,

                    blocks=quality_blocks,

                    page_width=page_width,

                    page_height=page_height,

                    expected_language=None,

                    layout_confidence=(
                        layout_confidence
                    ),
                )
            )

            if isinstance(
                quality,
                dict
            ):
                return quality

        except Exception as exc:

            logger.warning(
                "Level 3 quality calculation failed: %s",
                exc
            )

        # ----------------------------------------------------------
        # Safe fallback.
        # ----------------------------------------------------------

        fallback_score = (
            self._text_quality_score(
                text
            )
            * 100.0
        )

        status = "good"

        if fallback_score < 60:
            status = "retry"

        elif fallback_score < 80:
            status = "review"

        return {
            "quality_score": round(
                fallback_score,
                2
            ),

            "status": status,

            "text_score": round(
                fallback_score,
                2
            ),

            "language_score": 0.0,

            "character_score": 0.0,

            "coverage_score": 0.0,

            "confidence_score": 0.0,
        }

    # ==============================================================
    # TEXT SIMILARITY
    # ==============================================================

    @staticmethod
    def text_similarity(
        text_a: str,
        text_b: str,
    ) -> float:
        """
        Compare OCR outputs.

        Hindi, Gujarati, English and mixed-language Unicode
        characters are preserved.
        """

        a = (
            Level3HybridOCRService
            ._normalize_for_similarity(
                text_a
            )
        )

        b = (
            Level3HybridOCRService
            ._normalize_for_similarity(
                text_b
            )
        )

        if not a and not b:
            return 1.0

        if not a or not b:
            return 0.0

        return SequenceMatcher(
            None,
            a,
            b
        ).ratio()

    # ==============================================================
    # CHOOSE BEST RESULT
    # ==============================================================

    def choose_best_without_adjudication(
        self,
        ocrspace_result: Dict[str, Any],
        gemini_result: Dict[str, Any],
    ) -> str:
        """
        Deterministically select the better result.

        Priority:

            1. Table structure
            2. Form structure
            3. Text quality
            4. Confidence
            5. Gemini deterministic tie-breaker
        """

        ocrspace_text = self._clean_text(
            ocrspace_result.get(
                "text",
                ""
            )
        )

        gemini_text = self._clean_text(
            gemini_result.get(
                "text",
                ""
            )
        )

        if not ocrspace_text:
            return "gemini"

        if not gemini_text:
            return "ocrspace"

        # ----------------------------------------------------------
        # TABLE
        # ----------------------------------------------------------

        ocrspace_table = (
            self._table_structure_score(
                ocrspace_text
            )
        )

        gemini_table = (
            self._table_structure_score(
                gemini_text
            )
        )

        logger.info(
            "OCR.space table score : %.3f",
            ocrspace_table
        )

        logger.info(
            "Gemini table score    : %.3f",
            gemini_table
        )

        if gemini_table > ocrspace_table:
            return "gemini"

        if ocrspace_table > gemini_table:
            return "ocrspace"

        # ----------------------------------------------------------
        # FORM
        # ----------------------------------------------------------

        ocrspace_form = (
            self._form_structure_score(
                ocrspace_text
            )
        )

        gemini_form = (
            self._form_structure_score(
                gemini_text
            )
        )

        logger.info(
            "OCR.space form score : %.3f",
            ocrspace_form
        )

        logger.info(
            "Gemini form score    : %.3f",
            gemini_form
        )

        if gemini_form > ocrspace_form:
            return "gemini"

        if ocrspace_form > gemini_form:
            return "ocrspace"

        # ----------------------------------------------------------
        # TEXT QUALITY
        # ----------------------------------------------------------

        ocrspace_quality = (
            self._text_quality_score(
                ocrspace_text
            )
        )

        gemini_quality = (
            self._text_quality_score(
                gemini_text
            )
        )

        logger.info(
            "OCR.space text quality : %.3f",
            ocrspace_quality
        )

        logger.info(
            "Gemini text quality    : %.3f",
            gemini_quality
        )

        if gemini_quality > ocrspace_quality:
            return "gemini"

        if ocrspace_quality > gemini_quality:
            return "ocrspace"

        # ----------------------------------------------------------
        # CONFIDENCE
        # ----------------------------------------------------------

        ocrspace_confidence = (
            self._extract_confidence(
                ocrspace_result
            )
        )

        gemini_confidence = (
            self._extract_confidence(
                gemini_result
            )
        )

        if (
            ocrspace_confidence is not None
            and gemini_confidence is not None
        ):

            logger.info(
                "OCR.space confidence : %.3f",
                ocrspace_confidence
            )

            logger.info(
                "Gemini confidence    : %.3f",
                gemini_confidence
            )

            if (
                gemini_confidence
                > ocrspace_confidence
            ):
                return "gemini"

            if (
                ocrspace_confidence
                > gemini_confidence
            ):
                return "ocrspace"

        # ----------------------------------------------------------
        # SAFE DEFAULT
        # ----------------------------------------------------------

        return "gemini"

    # ==============================================================
    # CONFIDENCE EXTRACTION
    # ==============================================================

    @staticmethod
    def _extract_confidence(
        result: Dict[str, Any]
    ) -> Optional[float]:
        """
        Extract confidence from common OCR result formats.
        """

        if not isinstance(
            result,
            dict
        ):
            return None

        possible_keys = (
            "confidence",
            "overall_confidence",
            "score",
        )

        for key in possible_keys:

            value = result.get(
                key
            )

            if value is None:
                continue

            try:

                value = float(
                    value
                )

                if (
                    value > 1.0
                    and value <= 100.0
                ):
                    value /= 100.0

                return max(
                    0.0,
                    min(
                        value,
                        1.0
                    )
                )

            except (
                TypeError,
                ValueError
            ):

                pass

        # ----------------------------------------------------------
        # Block-level confidence
        # ----------------------------------------------------------

        blocks = result.get(
            "results"
        )

        if isinstance(
            blocks,
            list
        ):

            confidences = []

            for block in blocks:

                if not isinstance(
                    block,
                    dict
                ):
                    continue

                value = block.get(
                    "confidence"
                )

                if value is None:
                    continue

                try:

                    value = float(
                        value
                    )

                    if (
                        value > 1.0
                        and value <= 100.0
                    ):
                        value /= 100.0

                    confidences.append(
                        max(
                            0.0,
                            min(
                                value,
                                1.0
                            )
                        )
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    continue

            if confidences:

                return (
                    sum(
                        confidences
                    )
                    / len(
                        confidences
                    )
                )

        return None

    # ==============================================================
    # TEXT QUALITY
    # ==============================================================

    @staticmethod
    def _text_quality_score(
        text: str
    ) -> float:
        """
        Lightweight language-independent OCR quality heuristic.
        """

        if not text:
            return 0.0

        score = 0.0

        length = len(
            text
        )

        # ----------------------------------------------------------
        # Length
        # ----------------------------------------------------------

        if length >= 20:
            score += 0.20

        if length >= 100:
            score += 0.10

        if length >= 300:
            score += 0.10

        # ----------------------------------------------------------
        # Words
        # ----------------------------------------------------------

        words = text.split()

        if len(words) >= 5:
            score += 0.10

        if len(words) >= 20:
            score += 0.10

        # ----------------------------------------------------------
        # Hindi
        # ----------------------------------------------------------

        if any(
            "\u0900" <= char <= "\u097F"
            for char in text
        ):
            score += 0.10

        # ----------------------------------------------------------
        # Gujarati
        # ----------------------------------------------------------

        if any(
            "\u0A80" <= char <= "\u0AFF"
            for char in text
        ):
            score += 0.10

        # ----------------------------------------------------------
        # English
        # ----------------------------------------------------------

        if re.search(
            r"[A-Za-z]",
            text
        ):
            score += 0.05

        # ----------------------------------------------------------
        # Replacement character
        # ----------------------------------------------------------

        if "\ufffd" not in text:
            score += 0.05

        # ----------------------------------------------------------
        # Punctuation noise
        # ----------------------------------------------------------

        if not re.search(
            r"[!?.,:;]{5,}",
            text
        ):
            score += 0.05

        return min(
            score,
            1.0
        )

    # ==============================================================
    # TABLE STRUCTURE
    # ==============================================================

    @staticmethod
    def _table_structure_score(
        text: str
    ) -> float:
        """
        Estimate whether OCR output preserves table structure.
        """

        if not text:
            return 0.0

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        if not lines:
            return 0.0

        score = 0.0

        pipe_lines = sum(
            1
            for line in lines
            if line.count("|") >= 2
        )

        if pipe_lines >= 2:
            score += 0.5

        if pipe_lines >= 4:
            score += 0.3

        if re.search(
            r"\|\s*:?-{2,}:?\s*\|",
            text
        ):
            score += 0.2

        return min(
            score,
            1.0
        )

    # ==============================================================
    # FORM STRUCTURE
    # ==============================================================

    @staticmethod
    def _form_structure_score(
        text: str
    ) -> float:
        """
        Estimate label:value form structure.
        """

        if not text:
            return 0.0

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        if not lines:
            return 0.0

        label_value_lines = 0

        for line in lines:

            if re.search(
                r"^[^:\n]{1,80}:\s*.+$",
                line
            ):
                label_value_lines += 1

        if label_value_lines >= 5:
            return 1.0

        if label_value_lines >= 3:
            return 0.7

        if label_value_lines >= 1:
            return 0.3

        return 0.0

    # ==============================================================
    # CLEAN TEXT
    # ==============================================================

    @staticmethod
    def _clean_text(
        text: Any
    ) -> str:
        """
        Clean line endings without destroying multilingual
        Unicode text or document structure.
        """

        if text is None:
            return ""

        text = str(
            text
        )

        text = text.replace(
            "\r\n",
            "\n"
        )

        text = text.replace(
            "\r",
            "\n"
        )

        lines = [
            line.rstrip()
            for line in text.splitlines()
        ]

        return "\n".join(
            lines
        ).strip()

    # ==============================================================
    # NORMALIZE FOR SIMILARITY
    # ==============================================================

    @staticmethod
    def _normalize_for_similarity(
        text: str
    ) -> str:
        """
        Normalize text for comparison.

        Hindi, Gujarati and English characters are preserved.
        """

        text = (
            Level3HybridOCRService
            ._clean_text(
                text
            )
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip().casefold()