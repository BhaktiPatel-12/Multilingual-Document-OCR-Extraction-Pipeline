"""
Astra-OCR
Gemini OCR Service

Level 3 OCR engine.

Responsibilities:
- OCR using Gemini.
- Preserve multilingual text.
- Preserve document structure.
- Retry failed requests.
- Use fallback Gemini model.
- Perform OCR adjudication when OCR.space and Gemini
  substantially disagree.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from google import genai


load_dotenv()

logger = logging.getLogger(__name__)


class GeminiOCRError(Exception):
    """Controlled Gemini OCR error."""


class GeminiOCRService:

    DEFAULT_MODEL = "gemini-3.8-flash"
    FALLBACK_MODEL = "gemini-3.7-flash"

    MAX_RETRIES = 4

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        max_retries: int = MAX_RETRIES,
    ):

        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
        )

        self.model = (
            model
            or os.getenv(
                "GEMINI_MODEL",
                self.DEFAULT_MODEL,
            )
        )

        self.fallback_model = (
            fallback_model
            or os.getenv(
                "GEMINI_FALLBACK_MODEL",
                self.FALLBACK_MODEL,
            )
        )

        self.max_retries = int(
            max_retries
        )

        if not self.api_key:
            raise GeminiOCRError(
                "GEMINI_API_KEY is not configured. "
                "Add GEMINI_API_KEY=your_api_key "
                "to backend/.env"
            )

        self.client = genai.Client(
            api_key=self.api_key
        )

    # ================================================================
    # PUBLIC OCR
    # ================================================================

    def run_ocr(
        self,
        image_path: Optional[str] = None,
        pdf_path: Optional[str] = None,
        page_number: Optional[int] = None,
    ) -> Dict[str, Any]:

        source_path = self._select_source(
            image_path=image_path,
            pdf_path=pdf_path,
        )

        logger.info(
            "Gemini OCR input: %s",
            source_path,
        )

        try:

            uploaded_file = (
                self.client.files.upload(
                    file=str(source_path)
                )
            )

            prompt = self._build_ocr_prompt(
                page_number=page_number
            )

            response, used_model = (
                self._generate_with_retry(
                    uploaded_file=uploaded_file,
                    prompt=prompt,
                )
            )

            text = self._extract_text(
                response
            )

            if not text:
                raise GeminiOCRError(
                    "Gemini returned empty OCR text."
                )

            return {
                "text": text,
                "model": used_model,
                "source": "gemini",
                "input_path": str(source_path),
                "page_number": page_number,
            }

        except GeminiOCRError:
            raise

        except Exception as exc:

            raise GeminiOCRError(
                f"Gemini OCR failed: {exc}"
            ) from exc

    # ================================================================
    # ADJUDICATION
    # ================================================================

    def adjudicate(
        self,
        ocrspace_text: str,
        gemini_text: str,
        page_number: Optional[int] = None,
    ) -> Dict[str, Any]:

        if not ocrspace_text and not gemini_text:
            raise GeminiOCRError(
                "Cannot adjudicate empty OCR results."
            )

        if not ocrspace_text:
            return {
                "text": gemini_text,
                "model": self.model,
                "source": "gemini_adjudication",
                "page_number": page_number,
            }

        if not gemini_text:
            return {
                "text": ocrspace_text,
                "model": self.model,
                "source": "gemini_adjudication",
                "page_number": page_number,
            }

        prompt = (
            self._build_adjudication_prompt(
                ocrspace_text=ocrspace_text,
                gemini_text=gemini_text,
                page_number=page_number,
            )
        )

        response, used_model = (
            self._generate_text_with_retry(
                prompt=prompt
            )
        )

        text = self._extract_text(
            response
        )

        if not text:
            raise GeminiOCRError(
                "Gemini adjudication returned empty text."
            )

        return {
            "text": text,
            "model": used_model,
            "source": "gemini_adjudication",
            "page_number": page_number,
        }

    # ================================================================
    # OCR PROMPT
    # ================================================================

    @staticmethod
    def _build_ocr_prompt(
        page_number: Optional[int] = None,
    ) -> str:

        page_instruction = ""

        if page_number is not None:
            page_instruction = (
                f"This is page {page_number}. "
                "Return OCR for this page only.\n"
            )

        return f"""
You are the OCR engine for Astra-OCR.

{page_instruction}

Extract all visible text from the document exactly as written.

CRITICAL RULES:

1. Perform OCR only.
2. Do not summarize.
3. Do not explain.
4. Do not translate.
5. Preserve the original language.
6. The document may contain English, Hindi, Gujarati,
   or a mixture of these languages.
7. Preserve English as English.
8. Preserve Hindi as Hindi.
9. Preserve Gujarati as Gujarati.
10. Preserve reading order.
11. Preserve headings.
12. Preserve paragraphs.
13. Preserve numbered lists.
14. Preserve bullet lists.
15. Preserve tables.
16. Preserve form structures.
17. Preserve labels and values.
18. Preserve names exactly.
19. Preserve dates exactly.
20. Preserve numbers exactly.
21. Preserve currency values exactly.
22. Preserve IDs, codes, roll numbers and registration numbers.
23. Preserve punctuation whenever visible.
24. Do not invent missing information.
25. Do not guess an unreadable word.
26. If genuinely unreadable, write [UNREADABLE].
27. Represent tables using Markdown table syntax
    when the table structure is clear.
28. Represent forms as:
    Label: Value
29. Do not fabricate confidence values.
30. Return only OCR text.

For multilingual documents, never translate one language
into another.

Return only the final OCR text.
""".strip()

    # ================================================================
    # ADJUDICATION PROMPT
    # ================================================================

    @staticmethod
    def _build_adjudication_prompt(
        ocrspace_text: str,
        gemini_text: str,
        page_number: Optional[int] = None,
    ) -> str:

        page_instruction = ""

        if page_number is not None:
            page_instruction = (
                f"The disputed OCR belongs to page "
                f"{page_number}.\n"
            )

        return f"""
You are the final OCR adjudicator for Astra-OCR.

Two independent OCR engines processed the same document.

OCR.space result:
----------------
{ocrspace_text}
----------------

Gemini OCR result:
----------------
{gemini_text}
----------------

{page_instruction}

Produce one final, accurate OCR result.

RULES:

1. Do not summarize.
2. Do not explain.
3. Do not translate.
4. Preserve original languages.
5. English remains English.
6. Hindi remains Hindi.
7. Gujarati remains Gujarati.
8. Preserve reading order.
9. Preserve headings.
10. Preserve paragraphs.
11. Preserve lists.
12. Preserve tables.
13. Preserve form structures.
14. Preserve names.
15. Preserve dates.
16. Preserve numbers.
17. Preserve IDs and codes.
18. Preserve punctuation where visible.
19. Prefer text supported by the OCR results.
20. If one result clearly contains an OCR error,
    use the supported/correct version.
21. Do not invent information.
22. If a word cannot reasonably be determined,
    use [UNREADABLE].
23. Do not add explanations.
24. Return only the final OCR text.

Return one clean final OCR result.
""".strip()

    # ================================================================
    # GEMINI OCR RETRIES
    # ================================================================

    def _generate_with_retry(
        self,
        uploaded_file,
        prompt: str,
    ):

        last_error = None

        models = [
            self.model,
            self.fallback_model,
        ]

        for model_index, model in enumerate(
            models
        ):

            if not model:
                continue

            for attempt in range(
                1,
                self.max_retries + 1,
            ):

                logger.info(
                    "Gemini OCR attempt %d/%d using %s",
                    attempt,
                    self.max_retries,
                    model,
                )

                try:

                    response = (
                        self.client.models.generate_content(
                            model=model,
                            contents=[
                                uploaded_file,
                                prompt,
                            ],
                        )
                    )

                    return response, model

                except Exception as exc:

                    last_error = exc

                    logger.warning(
                        "Gemini model %s failed: %s",
                        model,
                        exc,
                    )

                    if attempt < self.max_retries:

                        time.sleep(
                            min(
                                2 ** attempt,
                                15,
                            )
                        )

            if (
                model_index == 0
                and self.fallback_model
            ):

                logger.warning(
                    "Primary Gemini model failed. "
                    "Trying fallback model: %s",
                    self.fallback_model,
                )

        raise GeminiOCRError(
            "Gemini OCR failed after retries: "
            f"{last_error}"
        )

    # ================================================================
    # GEMINI TEXT RETRIES
    # ================================================================

    def _generate_text_with_retry(
        self,
        prompt: str,
    ):

        last_error = None

        models = [
            self.model,
            self.fallback_model,
        ]

        for model in models:

            if not model:
                continue

            for attempt in range(
                1,
                self.max_retries + 1,
            ):

                logger.info(
                    "Gemini adjudication attempt "
                    "%d/%d using %s",
                    attempt,
                    self.max_retries,
                    model,
                )

                try:

                    response = (
                        self.client.models.generate_content(
                            model=model,
                            contents=prompt,
                        )
                    )

                    return response, model

                except Exception as exc:

                    last_error = exc

                    logger.warning(
                        "Gemini adjudication failed: %s",
                        exc,
                    )

                    if attempt < self.max_retries:

                        time.sleep(
                            min(
                                2 ** attempt,
                                15,
                            )
                        )

        raise GeminiOCRError(
            "Gemini adjudication failed: "
            f"{last_error}"
        )

    # ================================================================
    # SOURCE
    # ================================================================

    @staticmethod
    def _select_source(
        image_path: Optional[str],
        pdf_path: Optional[str],
    ) -> Path:

        if pdf_path:

            path = Path(pdf_path)

            if not path.exists():
                raise FileNotFoundError(
                    f"Gemini PDF not found: {path}"
                )

            return path

        if image_path:

            path = Path(image_path)

            if not path.exists():
                raise FileNotFoundError(
                    f"Gemini image not found: {path}"
                )

            return path

        raise GeminiOCRError(
            "No Gemini input supplied."
        )

    # ================================================================
    # RESPONSE TEXT
    # ================================================================

    @staticmethod
    def _extract_text(
        response,
    ) -> str:

        text = getattr(
            response,
            "text",
            None,
        )

        if text:
            return str(text).strip()

        candidates = getattr(
            response,
            "candidates",
            None,
        )

        if not candidates:
            return ""

        parts = []

        for candidate in candidates:

            content = getattr(
                candidate,
                "content",
                None,
            )

            if not content:
                continue

            response_parts = getattr(
                content,
                "parts",
                None,
            )

            if not response_parts:
                continue

            for part in response_parts:

                part_text = getattr(
                    part,
                    "text",
                    None,
                )

                if part_text:
                    parts.append(
                        str(part_text)
                    )

        return "\n".join(
            parts
        ).strip()