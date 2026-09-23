# # 




# from pathlib import Path
# import json
# import hashlib
# from datetime import datetime

# import fitz

# from services.ocr_pipeline_service import (
#     OCRPipelineService
# )

# from services.preprocessing_service import (
#     ImagePreprocessor
# )

# from services.structured_pdf_service import (
#     StructuredPDFService
# )

# from services.language_highlighted_pdf_service import (
#     LanguageHighlightedPDFService
# )


# class PDFOCRService:
#     """
#     Complete Astra-OCR PDF processing service.

#     INPUT:
#         PDF

#     PIPELINE:
#         PDF
#         ↓
#         Render
#         ↓
#         Preprocess
#         ↓
#         OCRPipelineService
#         ↓
#         Level 1
#         ↓
#         Level 2
#         ↓
#         Level 3 if required
#         ↓
#         Final OCR

#     OUTPUT:
#         JSON
#         TXT
#         Structured PDF
#         Language Highlighted PDF
#     """

#     def __init__(
#         self,
#         output_dir="output",
#         quality_threshold=80.0,
#     ):

#         self.output_dir = Path(
#             output_dir
#         )

#         self.output_dir.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         self.quality_threshold = float(
#             quality_threshold
#         )

#         # =====================================================
#         # DIRECTORIES
#         # =====================================================

#         self.rendered_root = (
#             self.output_dir
#             / "rendered"
#         )

#         self.preprocessed_root = (
#             self.output_dir
#             / "preprocessed"
#         )

#         self.pipeline_root = (
#             self.output_dir
#             / "pipeline"
#         )

#         self.pdf_root = (
#             self.output_dir
#             / "pdf"
#         )

#         self.rendered_root.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         self.preprocessed_root.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         self.pipeline_root.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         self.pdf_root.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         # =====================================================
#         # SERVICES
#         # =====================================================

#         self.pipeline = OCRPipelineService(
#             output_dir=str(
#                 self.pipeline_root
#             ),
#             quality_threshold=(
#                 self.quality_threshold
#             ),
#         )

#         self.preprocessor = ImagePreprocessor(
#             output_dir=str(
#                 self.preprocessed_root
#             )
#         )

#     # =========================================================
#     # PDF ID
#     # =========================================================

#     @staticmethod
#     def get_pdf_id(
#         pdf_path
#     ):

#         pdf_path = Path(
#             pdf_path
#         )

#         sha256 = hashlib.sha256()

#         with open(
#             pdf_path,
#             "rb"
#         ) as file:

#             while True:

#                 chunk = file.read(
#                     1024 * 1024
#                 )

#                 if not chunk:
#                     break

#                 sha256.update(
#                     chunk
#                 )

#         short_hash = (
#             sha256.hexdigest()[:8]
#         )

#         return (
#             f"{pdf_path.stem}_"
#             f"{short_hash}"
#         )

#     # =========================================================
#     # RENDER PDF
#     # =========================================================

#     def render_pdf(
#         self,
#         pdf_path
#     ):

#         pdf_path = Path(
#             pdf_path
#         )

#         pdf_id = self.get_pdf_id(
#             pdf_path
#         )

#         rendered_dir = (
#             self.rendered_root
#             / pdf_id
#         )

#         rendered_dir.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         print()
#         print("=" * 70)
#         print("RENDERING PDF")
#         print("=" * 70)

#         print(
#             f"PDF       : {pdf_path}"
#         )

#         print(
#             f"PDF ID    : {pdf_id}"
#         )

#         print(
#             f"Pages dir : {rendered_dir}"
#         )

#         document = fitz.open(
#             str(pdf_path)
#         )

#         rendered_pages = []

#         try:

#             for index, page in enumerate(
#                 document,
#                 start=1
#             ):

#                 output_path = (
#                     rendered_dir
#                     / f"page_{index:03d}.png"
#                 )

#                 if output_path.exists():

#                     print(
#                         f"Using existing rendered "
#                         f"page {index}"
#                     )

#                 else:

#                     print(
#                         f"Rendering page {index}..."
#                     )

#                     pixmap = page.get_pixmap(
#                         matrix=fitz.Matrix(
#                             2.0,
#                             2.0
#                         ),
#                         alpha=False
#                     )

#                     pixmap.save(
#                         str(output_path)
#                     )

#                 rendered_pages.append(
#                     output_path
#                 )

#         finally:

#             document.close()

#         return pdf_id, rendered_pages

#     # =========================================================
#     # PREPROCESS ONE PAGE
#     # =========================================================

#     def preprocess_page(
#         self,
#         image_path,
#         page_number,
#         pdf_id
#     ):

#         page_dir = (
#             self.preprocessed_root
#             / pdf_id
#         )

#         page_dir.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         original_path = (
#             page_dir
#             / f"page_{page_number:03d}_original.png"
#         )

#         enhanced_path = (
#             page_dir
#             / f"page_{page_number:03d}_enhanced.png"
#         )

#         threshold_path = (
#             page_dir
#             / f"page_{page_number:03d}_threshold.png"
#         )

#         if (
#             original_path.exists()
#             and enhanced_path.exists()
#             and threshold_path.exists()
#         ):

#             print(
#                 f"Using existing preprocessing "
#                 f"for page {page_number}"
#             )

#             return {
#                 "original": str(
#                     original_path
#                 ),
#                 "enhanced": str(
#                     enhanced_path
#                 ),
#                 "threshold": str(
#                     threshold_path
#                 ),
#             }

#         print(
#             f"Preprocessing page {page_number}..."
#         )

#         # -----------------------------------------------------
#         # IMPORTANT
#         #
#         # Existing ImagePreprocessor writes to its configured
#         # output directory.
#         #
#         # We use a temporary instance for this PDF.
#         # -----------------------------------------------------

#         page_preprocessor = ImagePreprocessor(
#             output_dir=str(
#                 page_dir
#             )
#         )

#         outputs = (
#             page_preprocessor.preprocess(
#                 str(image_path),
#                 page_number=page_number
#             )
#         )

#         return outputs

#     # =========================================================
#     # EXTRACT FINAL TEXT
#     # =========================================================

#     @staticmethod
#     def extract_final_text(
#         final_result
#     ):

#         if not isinstance(
#             final_result,
#             dict
#         ):

#             return ""

#         results = final_result.get(
#             "results",
#             []
#         )

#         if not isinstance(
#             results,
#             list
#         ):

#             return ""

#         text_parts = []

#         for item in results:

#             if not isinstance(
#                 item,
#                 dict
#             ):

#                 continue

#             text = item.get(
#                 "text",
#                 ""
#             )

#             if text is None:
#                 continue

#             text = str(
#                 text
#             ).strip()

#             if text:

#                 text_parts.append(
#                     text
#                 )

#         return "\n".join(
#             text_parts
#         )

#     # =========================================================
#     # EXTRACT LANGUAGES
#     # =========================================================

#     @staticmethod
#     def extract_languages(
#         result
#     ):

#         if not isinstance(
#             result,
#             dict
#         ):

#             return []

#         languages = []

#         detected = result.get(
#             "detected_languages",
#             []
#         )

#         if isinstance(
#             detected,
#             list
#         ):

#             for language in detected:

#                 if (
#                     language
#                     not in languages
#                 ):

#                     languages.append(
#                         language
#                     )

#         if languages:
#             return languages

#         final_result = result.get(
#             "final_result",
#             {}
#         )

#         if not isinstance(
#             final_result,
#             dict
#         ):

#             return languages

#         blocks = final_result.get(
#             "results",
#             []
#         )

#         if not isinstance(
#             blocks,
#             list
#         ):

#             return languages

#         for block in blocks:

#             if not isinstance(
#                 block,
#                 dict
#             ):

#                 continue

#             language = block.get(
#                 "language"
#             )

#             if (
#                 language
#                 and language not in languages
#             ):

#                 languages.append(
#                     language
#                 )

#         return languages

#     # =========================================================
#     # SAVE JSON
#     # =========================================================

#     def save_json(
#         self,
#         pdf_path,
#         pdf_id,
#         page_results
#     ):

#         pdf_path = Path(
#             pdf_path
#         )

#         quality_scores = []

#         language_set = set()

#         level_counts = {
#             "1": 0,
#             "2": 0,
#             "3": 0,
#             "error": 0,
#         }

#         pages = []

#         for result in page_results:

#             final_quality = (
#                 result.get(
#                     "final_quality",
#                     {}
#                 )
#                 or {}
#             )

#             try:

#                 quality_score = float(
#                     final_quality.get(
#                         "quality_score",
#                         0
#                     )
#                 )

#             except (
#                 TypeError,
#                 ValueError
#             ):

#                 quality_score = 0.0

#             if quality_score > 0:

#                 quality_scores.append(
#                     quality_score
#                 )

#             level = result.get(
#                 "final_level"
#             )

#             if level in (
#                 1,
#                 2,
#                 3
#             ):

#                 level_counts[
#                     str(level)
#                 ] += 1

#             else:

#                 level_counts[
#                     "error"
#                 ] += 1

#             languages = (
#                 self.extract_languages(
#                     result
#                 )
#             )

#             for language in languages:

#                 language_set.add(
#                     language
#                 )

#             text = (
#                 self.extract_final_text(
#                     result.get(
#                         "final_result"
#                     )
#                 )
#             )

#             pages.append({
#                 "page_number": result.get(
#                     "page_number"
#                 ),

#                 "final_level": level,

#                 "final_source": result.get(
#                     "final_source"
#                 ),

#                 "detected_languages": (
#                     languages
#                 ),

#                 "quality": final_quality,

#                 "text": text,

#                 "ocr_result": result.get(
#                     "final_result"
#                 ),

#                 "level1": result.get(
#                     "level1"
#                 ),

#                 "level2": result.get(
#                     "level2"
#                 ),

#                 "level3": result.get(
#                     "level3"
#                 ),

#                 "level3_attempted": result.get(
#                     "level3_attempted",
#                     False
#                 ),

#                 "preprocessing_outputs": (
#                     result.get(
#                         "preprocessing_outputs"
#                     )
#                 ),
#             })

#         if quality_scores:

#             average_quality = round(
#                 sum(
#                     quality_scores
#                 )
#                 / len(
#                     quality_scores
#                 ),
#                 2
#             )

#         else:

#             average_quality = 0.0

#         document_json = {
#             "success": True,

#             "document": {
#                 "filename": pdf_path.name,
#                 "file_type": "application/pdf",
#                 "pdf_id": pdf_id,
#             },

#             "processing": {
#                 "processed_at": (
#                     datetime.now().isoformat()
#                 ),

#                 "quality_threshold": (
#                     self.quality_threshold
#                 ),

#                 "total_pages": len(
#                     page_results
#                 ),

#                 "cache_directories": {
#                     "rendered": str(
#                         self.rendered_root
#                         / pdf_id
#                     ),

#                     "preprocessed": str(
#                         self.preprocessed_root
#                         / pdf_id
#                     ),

#                     "pipeline": str(
#                         self.pipeline_root
#                     ),
#                 },
#             },

#             "summary": {
#                 "average_quality": (
#                     average_quality
#                 ),

#                 "languages": sorted(
#                     language_set
#                 ),

#                 "final_level_counts": (
#                     level_counts
#                 ),
#             },

#             "pages": pages,
#         }

#         output_path = (
#             self.output_dir
#             / f"{pdf_path.stem}.json"
#         )

#         with open(
#             output_path,
#             "w",
#             encoding="utf-8"
#         ) as file:

#             json.dump(
#                 document_json,
#                 file,
#                 ensure_ascii=False,
#                 indent=2,
#             )

#         print()
#         print(
#             f"JSON saved to:"
#         )

#         print(
#             output_path
#         )

#         return output_path

#     # =========================================================
#     # SAVE TXT
#     # =========================================================

#     def save_txt(
#         self,
#         pdf_path,
#         page_results
#     ):

#         pdf_path = Path(
#             pdf_path
#         )

#         output_path = (
#             self.output_dir
#             / f"{pdf_path.stem}.txt"
#         )

#         with open(
#             output_path,
#             "w",
#             encoding="utf-8"
#         ) as file:

#             for index, result in enumerate(
#                 page_results,
#                 start=1
#             ):

#                 page_number = result.get(
#                     "page_number",
#                     index
#                 )

#                 text = (
#                     self.extract_final_text(
#                         result.get(
#                             "final_result"
#                         )
#                     )
#                 )

#                 file.write(
#                     f"--- PAGE {page_number} ---\n\n"
#                 )

#                 if text:

#                     file.write(
#                         text
#                     )

#                 file.write(
#                     "\n\n"
#                 )

#         print()
#         print(
#             f"TXT saved to:"
#         )

#         print(
#             output_path
#         )

#         return output_path

#     # =========================================================
#     # FIND RAW SURYA JSON
#     # =========================================================

#     def find_surya_json_files(
#         self,
#         page_results
#     ):

#         json_files = []

#         for result in page_results:

#             page_number = result.get(
#                 "page_number"
#             )

#             page_dir = (
#                 self.pipeline_root
#                 / f"page_{page_number:03d}"
#                 / "level1"
#             )

#             candidates = list(
#                 page_dir.rglob(
#                     "results.json"
#                 )
#             )

#             if not candidates:

#                 raise FileNotFoundError(
#                     "Could not find raw Surya "
#                     f"results.json for page "
#                     f"{page_number}.\n"
#                     f"Search directory: "
#                     f"{page_dir}"
#                 )

#             candidates.sort(
#                 key=lambda path: path.stat().st_mtime,
#                 reverse=True
#             )

#             json_files.append(
#                 candidates[0]
#             )

#         return json_files

#     # =========================================================
#     # CREATE TWO PDFS
#     # =========================================================

#     def create_pdfs(
#         self,
#         pdf_path,
#         page_results
#     ):

#         pdf_path = Path(
#             pdf_path
#         )

#         print()
#         print("=" * 70)
#         print(
#             "CREATING STRUCTURED PDF OUTPUTS"
#         )
#         print("=" * 70)

#         json_files = (
#             self.find_surya_json_files(
#                 page_results
#             )
#         )

#         # -----------------------------------------------------
#         # NORMAL STRUCTURED PDF
#         # -----------------------------------------------------

#         normal_output = (
#             self.output_dir
#             / f"{pdf_path.stem}_structured.pdf"
#         )

#         print()
#         print(
#             "Building normal structured PDF..."
#         )

#         normal_service = (
#             StructuredPDFService()
#         )

#         normal_service.create_from_surya_json(
#             json_paths=json_files,
#             output_path=normal_output
#         )

#         # -----------------------------------------------------
#         # LANGUAGE HIGHLIGHTED PDF
#         # -----------------------------------------------------

#         highlighted_output = (
#             self.output_dir
#             / f"{pdf_path.stem}_language_highlighted.pdf"
#         )

#         print()
#         print(
#             "Building language highlighted PDF..."
#         )

#         highlighted_service = (
#             LanguageHighlightedPDFService(
#                 output_dir=str(
#                     self.pdf_root
#                 ),
#                 fonts_dir="fonts",
#             )
#         )

#         highlighted_service.create_from_surya_json(
#             json_paths=json_files,
#             output_path=highlighted_output
#         )

#         return {
#             "structured_pdf": str(
#                 normal_output
#             ),

#             "language_highlighted_pdf": str(
#                 highlighted_output
#             ),
#         }

#     # =========================================================
#     # COMPLETE PDF PIPELINE
#     # =========================================================

#     def process_pdf(
#         self,
#         pdf_path
#     ):

#         pdf_path = Path(
#             pdf_path
#         )

#         if not pdf_path.exists():

#             raise FileNotFoundError(
#                 f"PDF not found: {pdf_path}"
#             )

#         if pdf_path.suffix.lower() != ".pdf":

#             raise ValueError(
#                 "Input must be a PDF file."
#             )

#         print()
#         print("=" * 70)
#         print(
#             "        ASTRA-OCR COMPLETE PDF PIPELINE"
#         )
#         print("=" * 70)

#         print()
#         print(
#             f"Input PDF: {pdf_path}"
#         )

#         # =====================================================
#         # RENDER
#         # =====================================================

#         pdf_id, rendered_pages = (
#             self.render_pdf(
#                 pdf_path
#             )
#         )

#         print()
#         print(
#             f"Total pages: "
#             f"{len(rendered_pages)}"
#         )

#         # =====================================================
#         # PROCESS EACH PAGE
#         # =====================================================

#         page_results = []

#         for page_number, page_path in enumerate(
#             rendered_pages,
#             start=1
#         ):

#             print()
#             print("=" * 70)
#             print(
#                 f"PROCESSING PDF PAGE {page_number}"
#             )
#             print("=" * 70)

#             # -------------------------------------------------
#             # PREPROCESS
#             # -------------------------------------------------

#             preprocessing_outputs = (
#                 self.preprocess_page(
#                     image_path=page_path,
#                     page_number=page_number,
#                     pdf_id=pdf_id,
#                 )
#             )

#             original_image = (
#                 preprocessing_outputs.get(
#                     "original"
#                 )
#             )

#             if not original_image:

#                 original_image = str(
#                     page_path
#                 )

#             # -------------------------------------------------
#             # COMPLETE OCR PIPELINE
#             # -------------------------------------------------

#             result = (
#                 self.pipeline.process_page(
#                     image_path=original_image,

#                     page_number=page_number,

#                     preprocessing_outputs=(
#                         preprocessing_outputs
#                     ),
#                 )
#             )

#             page_results.append(
#                 result
#             )

#             # -------------------------------------------------
#             # PAGE RESULT
#             # -------------------------------------------------

#             quality = (
#                 result.get(
#                     "final_quality",
#                     {}
#                 )
#                 or {}
#             )

#             print()
#             print(
#                 f"PAGE {page_number} COMPLETE"
#             )

#             print(
#                 f"Final level  : "
#                 f"{result.get('final_level')}"
#             )

#             print(
#                 f"Final source : "
#                 f"{result.get('final_source')}"
#             )

#             print(
#                 f"Quality      : "
#                 f"{quality.get('quality_score', 0)}"
#             )

#             print(
#                 f"Languages    : "
#                 f"{self.extract_languages(result)}"
#             )

#         # =====================================================
#         # JSON
#         # =====================================================

#         json_output = self.save_json(
#             pdf_path=pdf_path,
#             pdf_id=pdf_id,
#             page_results=page_results,
#         )

#         # =====================================================
#         # TXT
#         # =====================================================

#         txt_output = self.save_txt(
#             pdf_path=pdf_path,
#             page_results=page_results,
#         )

#         # =====================================================
#         # TWO PDFS
#         # =====================================================

#         pdf_outputs = self.create_pdfs(
#             pdf_path=pdf_path,
#             page_results=page_results,
#         )

#         # =====================================================
#         # FINAL
#         # =====================================================

#         print()
#         print("=" * 70)
#         print(
#             "             ASTRA-OCR COMPLETE"
#         )
#         print("=" * 70)

#         print()
#         print(
#             "FOUR OUTPUT FILES"
#         )

#         print()
#         print(
#             f"JSON:"
#         )

#         print(
#             json_output
#         )

#         print()
#         print(
#             f"TXT:"
#         )

#         print(
#             txt_output
#         )

#         print()
#         print(
#             f"STRUCTURED PDF:"
#         )

#         print(
#             pdf_outputs[
#                 "structured_pdf"
#             ]
#         )

#         print()
#         print(
#             f"LANGUAGE HIGHLIGHTED PDF:"
#         )

#         print(
#             pdf_outputs[
#                 "language_highlighted_pdf"
#             ]
#         )

#         print()
#         print("=" * 70)

#         return {
#             "success": True,

#             "input_pdf": str(
#                 pdf_path
#             ),

#             "pdf_id": pdf_id,

#             "total_pages": len(
#                 page_results
#             ),

#             "outputs": {
#                 "json": str(
#                     json_output
#                 ),

#                 "txt": str(
#                     txt_output
#                 ),

#                 "structured_pdf": (
#                     pdf_outputs[
#                         "structured_pdf"
#                     ]
#                 ),

#                 "language_highlighted_pdf": (
#                     pdf_outputs[
#                         "language_highlighted_pdf"
#                     ]
#                 ),
#             },

#             "pages": page_results,
#         }







from pathlib import Path
import json
import hashlib
import re
from datetime import datetime

import fitz

from services.ocr_pipeline_service import (
    OCRPipelineService
)

from services.preprocessing_service import (
    ImagePreprocessor
)

from services.structured_pdf_service import (
    StructuredPDFService
)

from services.language_highlighted_pdf_service import (
    LanguageHighlightedPDFService
)


class PDFOCRService:
    """
    Complete Astra-OCR PDF processing service.

    INPUT:
        PDF

    PIPELINE:
        PDF
        ↓
        Render
        ↓
        Preprocess
        ↓
        OCRPipelineService
        ↓
        Level 1
        ↓
        Level 2
        ↓
        Level 3 if required
        ↓
        Final OCR

    OUTPUT:
        JSON
        TXT
        Structured PDF
        Language Highlighted PDF
    """

    def __init__(
        self,
        output_dir="output",
        quality_threshold=50.0,
    ):

        self.output_dir = Path(
            output_dir
        )

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        self.quality_threshold = float(
            quality_threshold
        )

        # =====================================================
        # DIRECTORIES
        # =====================================================

        self.rendered_root = (
            self.output_dir
            / "rendered"
        )

        self.preprocessed_root = (
            self.output_dir
            / "preprocessed"
        )

        self.pipeline_root = (
            self.output_dir
            / "pipeline"
        )

        self.pdf_root = (
            self.output_dir
            / "pdf"
        )

        self.rendered_root.mkdir(
            parents=True,
            exist_ok=True
        )

        self.preprocessed_root.mkdir(
            parents=True,
            exist_ok=True
        )

        self.pipeline_root.mkdir(
            parents=True,
            exist_ok=True
        )

        self.pdf_root.mkdir(
            parents=True,
            exist_ok=True
        )

        # =====================================================
        # SERVICES
        # =====================================================

        self.pipeline = OCRPipelineService(
            output_dir=str(
                self.pipeline_root
            ),
            quality_threshold=(
                self.quality_threshold
            ),
        )

        self.preprocessor = ImagePreprocessor(
            output_dir=str(
                self.preprocessed_root
            )
        )

    # =========================================================
    # PDF ID
    # =========================================================

    @staticmethod
    def get_pdf_id(
        pdf_path
    ):

        pdf_path = Path(
            pdf_path
        )

        sha256 = hashlib.sha256()

        with open(
            pdf_path,
            "rb"
        ) as file:

            while True:

                chunk = file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                sha256.update(
                    chunk
                )

        short_hash = (
            sha256.hexdigest()[:8]
        )

        return (
            f"{pdf_path.stem}_"
            f"{short_hash}"
        )

    # =========================================================
    # RENDER PDF
    # =========================================================

    def render_pdf(
        self,
        pdf_path
    ):

        pdf_path = Path(
            pdf_path
        )

        pdf_id = self.get_pdf_id(
            pdf_path
        )

        rendered_dir = (
            self.rendered_root
            / pdf_id
        )

        rendered_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        print()
        print("=" * 70)
        print("RENDERING PDF")
        print("=" * 70)

        print(
            f"PDF       : {pdf_path}"
        )

        print(
            f"PDF ID    : {pdf_id}"
        )

        print(
            f"Pages dir : {rendered_dir}"
        )

        document = fitz.open(
            str(pdf_path)
        )

        rendered_pages = []

        try:

            for index, page in enumerate(
                document,
                start=1
            ):

                output_path = (
                    rendered_dir
                    / f"page_{index:03d}.png"
                )

                if output_path.exists():

                    print(
                        f"Using existing rendered "
                        f"page {index}"
                    )

                else:

                    print(
                        f"Rendering page {index}..."
                    )

                    pixmap = page.get_pixmap(
                        matrix=fitz.Matrix(
                            2.0,
                            2.0
                        ),
                        alpha=False
                    )

                    pixmap.save(
                        str(output_path)
                    )

                rendered_pages.append(
                    output_path
                )

        finally:

            document.close()

        return pdf_id, rendered_pages

    # =========================================================
    # PREPROCESS ONE PAGE
    # =========================================================

    def preprocess_page(
        self,
        image_path,
        page_number,
        pdf_id
    ):

        page_dir = (
            self.preprocessed_root
            / pdf_id
        )

        page_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        original_path = (
            page_dir
            / f"page_{page_number:03d}_original.png"
        )

        enhanced_path = (
            page_dir
            / f"page_{page_number:03d}_enhanced.png"
        )

        threshold_path = (
            page_dir
            / f"page_{page_number:03d}_threshold.png"
        )

        if (
            original_path.exists()
            and enhanced_path.exists()
            and threshold_path.exists()
        ):

            print(
                f"Using existing preprocessing "
                f"for page {page_number}"
            )

            return {
                "original": str(
                    original_path
                ),
                "enhanced": str(
                    enhanced_path
                ),
                "threshold": str(
                    threshold_path
                ),
            }

        print(
            f"Preprocessing page {page_number}..."
        )

        page_preprocessor = ImagePreprocessor(
            output_dir=str(
                page_dir
            )
        )

        outputs = (
            page_preprocessor.preprocess(
                str(image_path),
                page_number=page_number
            )
        )

        return outputs

    # =========================================================
    # CLEAN OCR TEXT
    # =========================================================

    @staticmethod
    def clean_ocr_text(
        text
    ):
        """
        Clean OCR text without destroying multilingual
        Unicode characters.

        Converts HTML line breaks into real newlines.
        Removes remaining HTML tags.
        Preserves Hindi, Gujarati, Bengali, Marathi,
        English and other Unicode scripts.
        """

        if text is None:
            return ""

        text = str(
            text
        )

        # -----------------------------------------------------
        # HTML line breaks
        # -----------------------------------------------------

        text = re.sub(
            r"<br\s*/?>",
            "\n",
            text,
            flags=re.IGNORECASE
        )

        # -----------------------------------------------------
        # Paragraph-like HTML
        # -----------------------------------------------------

        text = re.sub(
            r"</p\s*>",
            "\n",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            r"<p[^>]*>",
            "",
            text,
            flags=re.IGNORECASE
        )

        # -----------------------------------------------------
        # Remove remaining HTML tags
        # -----------------------------------------------------

        text = re.sub(
            r"<[^>]+>",
            "",
            text
        )

        # -----------------------------------------------------
        # HTML entities
        # -----------------------------------------------------

        replacements = {
            "&nbsp;": " ",
            "&amp;": "&",
            "&lt;": "<",
            "&gt;": ">",
            "&quot;": '"',
            "&#39;": "'",
        }

        for old, new in replacements.items():

            text = text.replace(
                old,
                new
            )

        # -----------------------------------------------------
        # Normalize line endings
        # -----------------------------------------------------

        text = text.replace(
            "\r\n",
            "\n"
        )

        text = text.replace(
            "\r",
            "\n"
        )

        # -----------------------------------------------------
        # Remove excessive blank lines
        # -----------------------------------------------------

        text = re.sub(
            r"\n[ \t]+\n",
            "\n\n",
            text
        )

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        return text.strip()

    # =========================================================
    # EXTRACT TEXT FROM ANY OCR OBJECT
    # =========================================================

    @classmethod
    def extract_text_recursive(
        cls,
        data
    ):
        """
        Recursively extract OCR text from different result
        structures.

        Supported examples:

            {
                "results": [
                    {"text": "..."}
                ]
            }

        or:

            {
                "results": [
                    {"html": "..."}
                ]
            }

        or nested Level 2 / Level 3 structures.

        This method is intentionally defensive so TXT output
        does not become blank when OCR text exists elsewhere
        in the result.
        """

        text_parts = []

        # =====================================================
        # STRING
        # =====================================================

        if isinstance(
            data,
            str
        ):

            cleaned = cls.clean_ocr_text(
                data
            )

            if cleaned:
                text_parts.append(
                    cleaned
                )

            return text_parts

        # =====================================================
        # LIST
        # =====================================================

        if isinstance(
            data,
            list
        ):

            for item in data:

                text_parts.extend(
                    cls.extract_text_recursive(
                        item
                    )
                )

            return text_parts

        # =====================================================
        # DICTIONARY
        # =====================================================

        if not isinstance(
            data,
            dict
        ):

            return text_parts

        # -----------------------------------------------------
        # IMPORTANT:
        #
        # If this object itself represents an OCR block,
        # prefer its text/html field.
        # -----------------------------------------------------

        block_text = data.get(
            "text"
        )

        if (
            block_text is not None
            and isinstance(
                block_text,
                (
                    str,
                    int,
                    float
                )
            )
        ):

            cleaned = cls.clean_ocr_text(
                block_text
            )

            if cleaned:

                text_parts.append(
                    cleaned
                )

            return text_parts

        # -----------------------------------------------------
        # Surya uses HTML for structured OCR blocks.
        # -----------------------------------------------------

        block_html = data.get(
            "html"
        )

        if (
            block_html is not None
            and isinstance(
                block_html,
                str
            )
        ):

            cleaned = cls.clean_ocr_text(
                block_html
            )

            if cleaned:

                text_parts.append(
                    cleaned
                )

            return text_parts

        # =====================================================
        # PRIORITIZED OCR CONTAINERS
        # =====================================================

        priority_keys = [
            "results",
            "blocks",
            "pages",
            "final_result",
            "corrected",
            "original",
            "selected_result",
            "ocr_result",
            "data",
        ]

        visited_keys = set()

        for key in priority_keys:

            if key not in data:
                continue

            visited_keys.add(
                key
            )

            value = data.get(
                key
            )

            extracted = (
                cls.extract_text_recursive(
                    value
                )
            )

            text_parts.extend(
                extracted
            )

        # =====================================================
        # FALLBACK:
        # SEARCH OTHER NESTED OBJECTS
        # =====================================================

        for key, value in data.items():

            if key in visited_keys:
                continue

            # -------------------------------------------------
            # Do not accidentally write metadata into TXT.
            # -------------------------------------------------

            if key in {
                "page_number",
                "quality_score",
                "confidence",
                "status",
                "language",
                "detected_languages",
                "bbox",
                "polygon",
                "reading_order",
                "label",
                "raw_label",
                "success",
                "error",
                "source",
                "selected",
                "final_level",
                "final_source",
            }:

                continue

            if isinstance(
                value,
                (
                    dict,
                    list
                )
            ):

                extracted = (
                    cls.extract_text_recursive(
                        value
                    )
                )

                text_parts.extend(
                    extracted
                )

        return text_parts

    # =========================================================
    # EXTRACT FINAL TEXT
    # =========================================================

    @classmethod
    def extract_final_text(
        cls,
        final_result
    ):
        """
        Extract final OCR text.

        Handles normal Level 1, Level 2 and Level 3
        normalized OCR structures.
        """

        if not final_result:

            return ""

        parts = cls.extract_text_recursive(
            final_result
        )

        # -----------------------------------------------------
        # Remove duplicate consecutive text.
        # -----------------------------------------------------

        cleaned_parts = []

        previous = None

        for part in parts:

            part = cls.clean_ocr_text(
                part
            )

            if not part:
                continue

            if part == previous:
                continue

            cleaned_parts.append(
                part
            )

            previous = part

        return "\n".join(
            cleaned_parts
        ).strip()

    # =========================================================
    # EXTRACT LANGUAGES
    # =========================================================

    @staticmethod
    def extract_languages(
        result
    ):

        if not isinstance(
            result,
            dict
        ):

            return []

        languages = []

        detected = result.get(
            "detected_languages",
            []
        )

        if isinstance(
            detected,
            list
        ):

            for language in detected:

                if (
                    language
                    and language not in languages
                ):

                    languages.append(
                        language
                    )

        if languages:
            return languages

        final_result = result.get(
            "final_result",
            {}
        )

        if not isinstance(
            final_result,
            dict
        ):

            return languages

        blocks = final_result.get(
            "results",
            []
        )

        if not isinstance(
            blocks,
            list
        ):

            return languages

        for block in blocks:

            if not isinstance(
                block,
                dict
            ):

                continue

            language = block.get(
                "language"
            )

            if (
                language
                and language not in languages
            ):

                languages.append(
                    language
                )

        return languages

    # =========================================================
    # SAVE JSON
    # =========================================================

    def save_json(
        self,
        pdf_path,
        pdf_id,
        page_results
    ):

        pdf_path = Path(
            pdf_path
        )

        quality_scores = []

        language_set = set()

        level_counts = {
            "1": 0,
            "2": 0,
            "3": 0,
            "error": 0,
        }

        pages = []

        for result in page_results:

            final_quality = (
                result.get(
                    "final_quality",
                    {}
                )
                or {}
            )

            try:

                quality_score = float(
                    final_quality.get(
                        "quality_score",
                        0
                    )
                )

            except (
                TypeError,
                ValueError
            ):

                quality_score = 0.0

            if quality_score > 0:

                quality_scores.append(
                    quality_score
                )

            level = result.get(
                "final_level"
            )

            if level in (
                1,
                2,
                3
            ):

                level_counts[
                    str(level)
                ] += 1

            else:

                level_counts[
                    "error"
                ] += 1

            languages = (
                self.extract_languages(
                    result
                )
            )

            for language in languages:

                language_set.add(
                    language
                )

            text = (
                self.extract_final_text(
                    result.get(
                        "final_result"
                    )
                )
            )

            pages.append({
                "page_number": result.get(
                    "page_number"
                ),

                "final_level": level,

                "final_source": result.get(
                    "final_source"
                ),

                "detected_languages": (
                    languages
                ),

                "quality": final_quality,

                "text": text,

                "ocr_result": result.get(
                    "final_result"
                ),

                "level1": result.get(
                    "level1"
                ),

                "level2": result.get(
                    "level2"
                ),

                "level3": result.get(
                    "level3"
                ),

                "level3_attempted": result.get(
                    "level3_attempted",
                    False
                ),

                "preprocessing_outputs": (
                    result.get(
                        "preprocessing_outputs"
                    )
                ),
            })

        if quality_scores:

            average_quality = round(
                sum(
                    quality_scores
                )
                / len(
                    quality_scores
                ),
                2
            )

        else:

            average_quality = 0.0

        document_json = {
            "success": True,

            "document": {
                "filename": pdf_path.name,
                "file_type": "application/pdf",
                "pdf_id": pdf_id,
            },

            "processing": {
                "processed_at": (
                    datetime.now().isoformat()
                ),

                "quality_threshold": (
                    self.quality_threshold
                ),

                "total_pages": len(
                    page_results
                ),

                "cache_directories": {
                    "rendered": str(
                        self.rendered_root
                        / pdf_id
                    ),

                    "preprocessed": str(
                        self.preprocessed_root
                        / pdf_id
                    ),

                    "pipeline": str(
                        self.pipeline_root
                    ),
                },
            },

            "summary": {
                "average_quality": (
                    average_quality
                ),

                "languages": sorted(
                    language_set
                ),

                "final_level_counts": (
                    level_counts
                ),
            },

            "pages": pages,
        }

        output_path = (
            self.output_dir
            / f"{pdf_path.stem}.json"
        )

        with open(
            output_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                document_json,
                file,
                ensure_ascii=False,
                indent=2,
            )

        print()
        print(
            "JSON saved to:"
        )

        print(
            output_path
        )

        return output_path

    # =========================================================
    # SAVE TXT
    # =========================================================

    def save_txt(
        self,
        pdf_path,
        page_results
    ):

        pdf_path = Path(
            pdf_path
        )

        output_path = (
            self.output_dir
            / f"{pdf_path.stem}.txt"
        )

        print()
        print("=" * 70)
        print("CREATING TXT OUTPUT")
        print("=" * 70)

        with open(
            output_path,
            "w",
            encoding="utf-8",
            newline="\n"
        ) as file:

            for index, result in enumerate(
                page_results,
                start=1
            ):

                page_number = result.get(
                    "page_number",
                    index
                )

                # -------------------------------------------------
                # IMPORTANT:
                #
                # Extract from FINAL RESULT exactly as JSON does.
                # -------------------------------------------------

                final_result = result.get(
                    "final_result"
                )

                text = (
                    self.extract_final_text(
                        final_result
                    )
                )

                # -------------------------------------------------
                # Fallback:
                #
                # If final_result somehow has no text, inspect
                # the complete page result.
                # -------------------------------------------------

                if not text:

                    text = (
                        self.extract_final_text(
                            result
                        )
                    )

                file.write(
                    f"--- PAGE {page_number} ---\n\n"
                )

                if text:

                    file.write(
                        text
                    )

                    print(
                        f"Page {page_number}: "
                        f"{len(text)} characters"
                    )

                else:

                    file.write(
                        "[No OCR text found]\n"
                    )

                    print(
                        f"Page {page_number}: "
                        f"WARNING - no OCR text found"
                    )

                file.write(
                    "\n\n"
                )

        print()
        print(
            "TXT saved to:"
        )

        print(
            output_path
        )

        return output_path

    # =========================================================
    # FIND RAW SURYA JSON
    # =========================================================

    def find_surya_json_files(
        self,
        page_results
    ):

        json_files = []

        for result in page_results:

            page_number = result.get(
                "page_number"
            )

            page_dir = (
                self.pipeline_root
                / f"page_{page_number:03d}"
                / "level1"
            )

            candidates = list(
                page_dir.rglob(
                    "results.json"
                )
            )

            if not candidates:

                raise FileNotFoundError(
                    "Could not find raw Surya "
                    f"results.json for page "
                    f"{page_number}.\n"
                    f"Search directory: "
                    f"{page_dir}"
                )

            candidates.sort(
                key=lambda path: path.stat().st_mtime,
                reverse=True
            )

            json_files.append(
                candidates[0]
            )

        return json_files

    # =========================================================
    # CREATE TWO PDFS
    # =========================================================

    def create_pdfs(
        self,
        pdf_path,
        page_results
    ):

        pdf_path = Path(
            pdf_path
        )

        print()
        print("=" * 70)
        print(
            "CREATING STRUCTURED PDF OUTPUTS"
        )
        print("=" * 70)

        json_files = (
            self.find_surya_json_files(
                page_results
            )
        )

        # -----------------------------------------------------
        # NORMAL STRUCTURED PDF
        # -----------------------------------------------------

        normal_output = (
            self.output_dir
            / f"{pdf_path.stem}_structured.pdf"
        )

        print()
        print(
            "Building normal structured PDF..."
        )

        normal_service = (
            StructuredPDFService()
        )

        normal_service.create_from_surya_json(
            json_paths=json_files,
            output_path=normal_output
        )

        # -----------------------------------------------------
        # LANGUAGE HIGHLIGHTED PDF
        # -----------------------------------------------------

        highlighted_output = (
            self.output_dir
            / f"{pdf_path.stem}_language_highlighted.pdf"
        )

        print()
        print(
            "Building language highlighted PDF..."
        )

        highlighted_service = (
            LanguageHighlightedPDFService(
                output_dir=str(
                    self.pdf_root
                ),
                fonts_dir="fonts",
            )
        )

        highlighted_service.create_from_surya_json(
            json_paths=json_files,
            output_path=highlighted_output
        )

        return {
            "structured_pdf": str(
                normal_output
            ),

            "language_highlighted_pdf": str(
                highlighted_output
            ),
        }

    # =========================================================
    # COMPLETE PDF PIPELINE
    # =========================================================

    def process_pdf(
        self,
        pdf_path
    ):

        pdf_path = Path(
            pdf_path
        )

        if not pdf_path.exists():

            raise FileNotFoundError(
                f"PDF not found: {pdf_path}"
            )

        if pdf_path.suffix.lower() != ".pdf":

            raise ValueError(
                "Input must be a PDF file."
            )

        print()
        print("=" * 70)
        print(
            "        ASTRA-OCR COMPLETE PDF PIPELINE"
        )
        print("=" * 70)

        print()
        print(
            f"Input PDF: {pdf_path}"
        )

        # =====================================================
        # RENDER
        # =====================================================

        pdf_id, rendered_pages = (
            self.render_pdf(
                pdf_path
            )
        )

        print()
        print(
            f"Total pages: "
            f"{len(rendered_pages)}"
        )

        # =====================================================
        # PROCESS EACH PAGE
        # =====================================================

        page_results = []

        for page_number, page_path in enumerate(
            rendered_pages,
            start=1
        ):

            print()
            print("=" * 70)
            print(
                f"PROCESSING PDF PAGE {page_number}"
            )
            print("=" * 70)

            # -------------------------------------------------
            # PREPROCESS
            # -------------------------------------------------

            preprocessing_outputs = (
                self.preprocess_page(
                    image_path=page_path,
                    page_number=page_number,
                    pdf_id=pdf_id,
                )
            )

            original_image = (
                preprocessing_outputs.get(
                    "original"
                )
            )

            if not original_image:

                original_image = str(
                    page_path
                )

            # -------------------------------------------------
            # COMPLETE OCR PIPELINE
            # -------------------------------------------------

            result = (
                self.pipeline.process_page(
                    image_path=original_image,

                    page_number=page_number,

                    preprocessing_outputs=(
                        preprocessing_outputs
                    ),
                )
            )

            page_results.append(
                result
            )

            # -------------------------------------------------
            # PAGE RESULT
            # -------------------------------------------------

            quality = (
                result.get(
                    "final_quality",
                    {}
                )
                or {}
            )

            page_text = (
                self.extract_final_text(
                    result.get(
                        "final_result"
                    )
                )
            )

            print()
            print(
                f"PAGE {page_number} COMPLETE"
            )

            print(
                f"Final level  : "
                f"{result.get('final_level')}"
            )

            print(
                f"Final source : "
                f"{result.get('final_source')}"
            )

            print(
                f"Quality      : "
                f"{quality.get('quality_score', 0)}"
            )

            print(
                f"Languages    : "
                f"{self.extract_languages(result)}"
            )

            print(
                f"Text chars   : "
                f"{len(page_text)}"
            )

        # =====================================================
        # JSON
        # =====================================================

        json_output = self.save_json(
            pdf_path=pdf_path,
            pdf_id=pdf_id,
            page_results=page_results,
        )

        # =====================================================
        # TXT
        # =====================================================

        txt_output = self.save_txt(
            pdf_path=pdf_path,
            page_results=page_results,
        )

        # =====================================================
        # TWO PDFS
        # =====================================================

        pdf_outputs = self.create_pdfs(
            pdf_path=pdf_path,
            page_results=page_results,
        )

        # =====================================================
        # FINAL
        # =====================================================

        print()
        print("=" * 70)
        print(
            "             ASTRA-OCR COMPLETE"
        )
        print("=" * 70)

        print()
        print(
            "FOUR OUTPUT FILES"
        )

        print()
        print(
            "JSON:"
        )

        print(
            json_output
        )

        print()
        print(
            "TXT:"
        )

        print(
            txt_output
        )

        print()
        print(
            "STRUCTURED PDF:"
        )

        print(
            pdf_outputs[
                "structured_pdf"
            ]
        )

        print()
        print(
            "LANGUAGE HIGHLIGHTED PDF:"
        )

        print(
            pdf_outputs[
                "language_highlighted_pdf"
            ]
        )

        print()
        print("=" * 70)

        return {
            "success": True,

            "input_pdf": str(
                pdf_path
            ),

            "pdf_id": pdf_id,

            "total_pages": len(
                page_results
            ),

            "outputs": {
                "json": str(
                    json_output
                ),

                "txt": str(
                    txt_output
                ),

                "structured_pdf": (
                    pdf_outputs[
                        "structured_pdf"
                    ]
                ),

                "language_highlighted_pdf": (
                    pdf_outputs[
                        "language_highlighted_pdf"
                    ]
                ),
            },

            "pages": page_results,
        }