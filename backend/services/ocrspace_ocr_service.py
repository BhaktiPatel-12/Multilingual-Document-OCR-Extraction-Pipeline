# """
# Astra-OCR
# OCR.space OCR Service

# Level 3 OCR engine.

# Responsibilities:
# - Send PDF/image to OCR.space.
# - Use OCR.space Engine 3.
# - Automatic language detection.
# - Table detection.
# - Orientation detection.
# - Scaling.
# - Overlay extraction.
# - Retry transient API failures.
# - Return normalized OCR result.
# - Never fabricate confidence values.
# """

# from __future__ import annotations

# import logging
# import os
# import time
# from pathlib import Path
# from typing import Any, Dict, Optional

# import requests
# from dotenv import load_dotenv
# from PIL import Image


# load_dotenv()

# logger = logging.getLogger(__name__)


# class OCRSpaceError(Exception):
#     """Controlled OCR.space error."""


# class OCRSpaceOCRService:

#     OCR_URL = "https://api.ocr.space/parse/image"

#     DEFAULT_ENGINE = "3"
#     DEFAULT_TIMEOUT = 300
#     DEFAULT_MAX_RETRIES = 3

#     # OCR.space free API practical image-size limit.
#     MAX_IMAGE_BYTES = 950_000

#     def __init__(
#         self,
#         api_key: Optional[str] = None,
#         engine: str = DEFAULT_ENGINE,
#         timeout: int = DEFAULT_TIMEOUT,
#         max_retries: int = DEFAULT_MAX_RETRIES,
#     ):
#         self.api_key = (
#             api_key
#             or os.getenv("OCR_SPACE_API_KEY")
#         )

#         self.engine = str(engine)
#         self.timeout = int(timeout)
#         self.max_retries = int(max_retries)

#     # ================================================================
#     # PUBLIC API
#     # ================================================================

#     def run_ocr(
#         self,
#         image_path: Optional[str] = None,
#         pdf_path: Optional[str] = None,
#         page_number: Optional[int] = None,
#     ) -> Dict[str, Any]:
#         """
#         Run OCR.space.

#         If pdf_path is supplied, the PDF is used.

#         Otherwise image_path is used.
#         """

#         if not self.api_key:
#             raise OCRSpaceError(
#                 "OCRSPACE_API_KEY is not configured. "
#                 "Add OCRSPACE_API_KEY=your_api_key "
#                 "to backend/.env"
#             )

#         source_path = self._select_source(
#             image_path=image_path,
#             pdf_path=pdf_path,
#         )

#         logger.info(
#             "OCR.space input: %s",
#             source_path,
#         )

#         if source_path.suffix.lower() == ".pdf":
#             return self._run_pdf(
#                 source_path=source_path,
#                 page_number=page_number,
#             )

#         return self._run_image(
#             source_path=source_path,
#             page_number=page_number,
#         )

#     # ================================================================
#     # SOURCE
#     # ================================================================

#     @staticmethod
#     def _select_source(
#         image_path: Optional[str],
#         pdf_path: Optional[str],
#     ) -> Path:

#         if pdf_path:
#             path = Path(pdf_path)

#             if not path.exists():
#                 raise FileNotFoundError(
#                     f"OCR.space PDF not found: {path}"
#                 )

#             return path

#         if image_path:
#             path = Path(image_path)

#             if not path.exists():
#                 raise FileNotFoundError(
#                     f"OCR.space image not found: {path}"
#                 )

#             return path

#         raise OCRSpaceError(
#             "No OCR.space input supplied. "
#             "Provide image_path or pdf_path."
#         )

#     # ================================================================
#     # PDF
#     # ================================================================

#     def _run_pdf(
#         self,
#         source_path: Path,
#         page_number: Optional[int],
#     ) -> Dict[str, Any]:

#         logger.info(
#             "OCR.space processing PDF directly."
#         )

#         return self._send_file(
#             source_path=source_path,
#             page_number=page_number,
#             is_pdf=True,
#         )

#     # ================================================================
#     # IMAGE
#     # ================================================================

#     def _run_image(
#         self,
#         source_path: Path,
#         page_number: Optional[int],
#     ) -> Dict[str, Any]:

#         prepared_path = source_path

#         temporary_path = None

#         try:

#             file_size = source_path.stat().st_size

#             logger.info(
#                 "OCR.space input size : %.2f MB",
#                 file_size / (1024 * 1024),
#             )

#             if file_size > self.MAX_IMAGE_BYTES:

#                 logger.info(
#                     "Image exceeds OCR.space free API limit."
#                 )

#                 prepared_path = self._compress_image(
#                     source_path
#                 )

#                 temporary_path = prepared_path

#                 logger.info(
#                     "Compressed size      : %.1f KB",
#                     prepared_path.stat().st_size / 1024,
#                 )

#             return self._send_file(
#                 source_path=prepared_path,
#                 page_number=page_number,
#                 is_pdf=False,
#             )

#         finally:

#             if temporary_path:
#                 try:
#                     temporary_path.unlink(
#                         missing_ok=True
#                     )
#                 except Exception as exc:
#                     logger.warning(
#                         "Could not delete temporary "
#                         "OCR.space image: %s",
#                         exc,
#                     )

#     # ================================================================
#     # IMAGE COMPRESSION
#     # ================================================================

#     def _compress_image(
#         self,
#         image_path: Path,
#     ) -> Path:

#         image = Image.open(
#             image_path
#         )

#         if image.mode != "RGB":
#             image = image.convert("RGB")

#         temporary_path = image_path.with_name(
#             image_path.stem
#             + "_ocrspace_temp.jpg"
#         )

#         # First try quality reduction.
#         for quality in (
#             85,
#             75,
#             65,
#             55,
#             45,
#             35,
#         ):

#             image.save(
#                 temporary_path,
#                 format="JPEG",
#                 quality=quality,
#                 optimize=True,
#             )

#             if (
#                 temporary_path.stat().st_size
#                 <= self.MAX_IMAGE_BYTES
#             ):
#                 return temporary_path

#         # If still too large, resize.
#         current = image

#         for _ in range(6):

#             width, height = current.size

#             width = int(width * 0.85)
#             height = int(height * 0.85)

#             if width < 500 or height < 500:
#                 break

#             current = current.resize(
#                 (width, height),
#                 Image.Resampling.LANCZOS,
#             )

#             current.save(
#                 temporary_path,
#                 format="JPEG",
#                 quality=65,
#                 optimize=True,
#             )

#             if (
#                 temporary_path.stat().st_size
#                 <= self.MAX_IMAGE_BYTES
#             ):
#                 return temporary_path

#         raise OCRSpaceError(
#             "Could not compress image below "
#             "OCR.space free API limit."
#         )

#     # ================================================================
#     # HTTP
#     # ================================================================

#     def _send_file(
#         self,
#         source_path: Path,
#         page_number: Optional[int],
#         is_pdf: bool,
#     ) -> Dict[str, Any]:

#         last_error = None

#         for attempt in range(
#             1,
#             self.max_retries + 1,
#         ):

#             logger.info(
#                 "OCR.space attempt %d/%d",
#                 attempt,
#                 self.max_retries,
#             )

#             try:

#                 with open(
#                     source_path,
#                     "rb",
#                 ) as file_handle:

#                     mime_type = (
#                         "application/pdf"
#                         if is_pdf
#                         else self._image_mime_type(
#                             source_path
#                         )
#                     )

#                     files = {
#                         "file": (
#                             source_path.name,
#                             file_handle,
#                             mime_type,
#                         )
#                     }

#                     data = {
#                         # Important:
#                         # automatic language detection.
#                         "language": "auto",

#                         # Preserve OCR layout information.
#                         "isOverlayRequired": "true",

#                         # Orientation detection.
#                         "detectOrientation": "true",

#                         # Scaling.
#                         "scale": "true",

#                         # Table mode.
#                         "isTable": "true",

#                         # OCR.space engine 3.
#                         "OCREngine": self.engine,
#                     }

#                     if is_pdf:
#                         data["filetype"] = "PDF"

#                     headers = {
#                         "apikey": self.api_key,
#                     }

#                     response = requests.post(
#                         self.OCR_URL,
#                         files=files,
#                         data=data,
#                         headers=headers,
#                         timeout=self.timeout,
#                     )

#                 logger.info(
#                     "OCR.space HTTP status: %s",
#                     response.status_code,
#                 )

#                 # ----------------------------------------------------
#                 # SUCCESS
#                 # ----------------------------------------------------

#                 if response.status_code == 200:

#                     try:
#                         response_data = response.json()
#                     except ValueError as exc:
#                         raise OCRSpaceError(
#                             "OCR.space returned invalid JSON."
#                         ) from exc

#                     return self._parse_response(
#                         response_data=response_data,
#                         source_path=source_path,
#                         page_number=page_number,
#                     )

#                 # ----------------------------------------------------
#                 # TRANSIENT ERRORS
#                 # ----------------------------------------------------

#                 if response.status_code in {
#                     408,
#                     429,
#                     500,
#                     502,
#                     503,
#                     504,
#                     522,
#                     524,
#                 }:

#                     last_error = OCRSpaceError(
#                         "OCR.space HTTP "
#                         f"{response.status_code}"
#                     )

#                     logger.warning(
#                         "%s",
#                         last_error,
#                     )

#                     if attempt < self.max_retries:

#                         delay = min(
#                             2 ** attempt,
#                             15,
#                         )

#                         logger.info(
#                             "Retrying OCR.space in %d seconds...",
#                             delay,
#                         )

#                         time.sleep(delay)

#                         continue

#                     break

#                 # ----------------------------------------------------
#                 # PERMANENT ERROR
#                 # ----------------------------------------------------

#                 error_text = (
#                     response.text[:1000]
#                     if response.text
#                     else "No response body."
#                 )

#                 raise OCRSpaceError(
#                     "OCR.space HTTP "
#                     f"{response.status_code}: "
#                     f"{error_text}"
#                 )

#             except requests.Timeout as exc:

#                 last_error = exc

#                 logger.warning(
#                     "OCR.space timeout: %s",
#                     exc,
#                 )

#                 if attempt < self.max_retries:

#                     delay = min(
#                         2 ** attempt,
#                         15,
#                     )

#                     time.sleep(delay)

#                     continue

#             except requests.RequestException as exc:

#                 last_error = exc

#                 logger.warning(
#                     "OCR.space request error: %s",
#                     exc,
#                 )

#                 if attempt < self.max_retries:

#                     delay = min(
#                         2 ** attempt,
#                         15,
#                     )

#                     time.sleep(delay)

#                     continue

#             except OCRSpaceError:
#                 raise

#             except Exception as exc:

#                 last_error = exc

#                 logger.warning(
#                     "Unexpected OCR.space error: %s",
#                     exc,
#                 )

#                 break

#         raise OCRSpaceError(
#             "OCR.space failed after "
#             f"{self.max_retries} attempts: "
#             f"{last_error}"
#         )

#     # ================================================================
#     # RESPONSE PARSING
#     # ================================================================

#     def _parse_response(
#         self,
#         response_data: Dict[str, Any],
#         source_path: Path,
#         page_number: Optional[int],
#     ) -> Dict[str, Any]:

#         if not isinstance(
#             response_data,
#             dict,
#         ):
#             raise OCRSpaceError(
#                 "Invalid OCR.space response."
#             )

#         if response_data.get(
#             "IsErroredOnProcessing"
#         ):

#             error_message = response_data.get(
#                 "ErrorMessage",
#                 "Unknown OCR.space processing error.",
#             )

#             if isinstance(
#                 error_message,
#                 list,
#             ):
#                 error_message = " ".join(
#                     str(item)
#                     for item in error_message
#                 )

#             raise OCRSpaceError(
#                 f"OCR.space processing error: "
#                 f"{error_message}"
#             )

#         parsed_results = response_data.get(
#             "ParsedResults",
#             [],
#         )

#         if not parsed_results:
#             raise OCRSpaceError(
#                 "OCR.space returned no ParsedResults."
#             )

#         text_parts = []
#         overlays = []

#         for parsed_result in parsed_results:

#             if not isinstance(
#                 parsed_result,
#                 dict,
#             ):
#                 continue

#             parsed_text = parsed_result.get(
#                 "ParsedText",
#                 "",
#             )

#             if parsed_text:
#                 text_parts.append(
#                     str(parsed_text).strip()
#                 )

#             overlay = parsed_result.get(
#                 "TextOverlay"
#             )

#             if overlay:
#                 overlays.append(
#                     overlay
#                 )

#         text = "\n\n".join(
#             part
#             for part in text_parts
#             if part
#         ).strip()

#         if not text:
#             raise OCRSpaceError(
#                 "OCR.space returned empty OCR text."
#             )

#         return {
#             "text": text,
#             "source": "ocrspace",
#             "engine": self.engine,
#             "input_path": str(source_path),
#             "page_number": page_number,
#             "parsed_results": parsed_results,
#             "overlays": overlays,
#             "raw_response": response_data,
#         }

#     # ================================================================
#     # HELPERS
#     # ================================================================

#     @staticmethod
#     def _image_mime_type(
#         path: Path,
#     ) -> str:

#         suffix = path.suffix.lower()

#         if suffix in {
#             ".jpg",
#             ".jpeg",
#         }:
#             return "image/jpeg"

#         if suffix == ".png":
#             return "image/png"

#         if suffix == ".webp":
#             return "image/webp"

#         if suffix == ".bmp":
#             return "image/bmp"

#         if suffix == ".tiff":
#             return "image/tiff"

#         return "application/octet-stream"






























"""
Astra-OCR
OCR.space OCR Service

Level 3 OCR engine.

Responsibilities:
- Send PDF/image to OCR.space.
- Use OCR.space Engine 3.
- Automatic language detection.
- Table detection.
- Orientation detection.
- Scaling.
- Overlay extraction when useful.
- Progressive retry for transient API failures.
- Return normalized OCR result.
- Never fabricate confidence values.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv
from PIL import Image


load_dotenv()

logger = logging.getLogger(__name__)


class OCRSpaceError(Exception):
    """Controlled OCR.space error."""


class OCRSpaceOCRService:

    OCR_URL = "https://api.ocr.space/parse/image"

    DEFAULT_ENGINE = "3"
    DEFAULT_TIMEOUT = 120
    DEFAULT_MAX_RETRIES = 3

    # OCR.space free API practical image-size limit.
    MAX_IMAGE_BYTES = 950_000

    def __init__(
        self,
        api_key: Optional[str] = None,
        engine: str = DEFAULT_ENGINE,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        self.api_key = (
            api_key
            or os.getenv("OCR_SPACE_API_KEY")
        )

        self.engine = str(engine)
        self.timeout = int(timeout)
        self.max_retries = int(max_retries)

    # ================================================================
    # PUBLIC API
    # ================================================================

    def run_ocr(
        self,
        image_path: Optional[str] = None,
        pdf_path: Optional[str] = None,
        page_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run OCR.space.

        If pdf_path is supplied, the PDF is used.

        Otherwise image_path is used.
        """

        if not self.api_key:
            raise OCRSpaceError(
                "OCRSPACE_API_KEY is not configured. "
                "Add OCRSPACE_API_KEY=your_api_key "
                "to backend/.env"
            )

        source_path = self._select_source(
            image_path=image_path,
            pdf_path=pdf_path,
        )

        logger.info(
            "OCR.space input: %s",
            source_path,
        )

        if source_path.suffix.lower() == ".pdf":
            return self._run_pdf(
                source_path=source_path,
                page_number=page_number,
            )

        return self._run_image(
            source_path=source_path,
            page_number=page_number,
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
                    f"OCR.space PDF not found: {path}"
                )

            return path

        if image_path:
            path = Path(image_path)

            if not path.exists():
                raise FileNotFoundError(
                    f"OCR.space image not found: {path}"
                )

            return path

        raise OCRSpaceError(
            "No OCR.space input supplied. "
            "Provide image_path or pdf_path."
        )

    # ================================================================
    # PDF
    # ================================================================

    def _run_pdf(
        self,
        source_path: Path,
        page_number: Optional[int],
    ) -> Dict[str, Any]:

        logger.info(
            "OCR.space processing PDF directly."
        )

        return self._send_file(
            source_path=source_path,
            page_number=page_number,
            is_pdf=True,
        )

    # ================================================================
    # IMAGE
    # ================================================================

    def _run_image(
        self,
        source_path: Path,
        page_number: Optional[int],
    ) -> Dict[str, Any]:

        prepared_path = source_path
        temporary_path = None

        try:

            file_size = source_path.stat().st_size

            logger.info(
                "OCR.space input size : %.2f MB",
                file_size / (1024 * 1024),
            )

            if file_size > self.MAX_IMAGE_BYTES:

                logger.info(
                    "Image exceeds OCR.space practical size limit."
                )

                prepared_path = self._compress_image(
                    source_path
                )

                temporary_path = prepared_path

                logger.info(
                    "Compressed size      : %.1f KB",
                    prepared_path.stat().st_size / 1024,
                )

            return self._send_file(
                source_path=prepared_path,
                page_number=page_number,
                is_pdf=False,
            )

        finally:

            if temporary_path:
                try:
                    temporary_path.unlink(
                        missing_ok=True
                    )
                except Exception as exc:
                    logger.warning(
                        "Could not delete temporary "
                        "OCR.space image: %s",
                        exc,
                    )

    # ================================================================
    # IMAGE COMPRESSION
    # ================================================================

    def _compress_image(
        self,
        image_path: Path,
    ) -> Path:

        image = Image.open(image_path)

        if image.mode != "RGB":
            image = image.convert("RGB")

        temporary_path = image_path.with_name(
            image_path.stem
            + "_ocrspace_temp.jpg"
        )

        # First try quality reduction.
        for quality in (
            85,
            75,
            65,
            55,
            45,
            35,
        ):

            image.save(
                temporary_path,
                format="JPEG",
                quality=quality,
                optimize=True,
            )

            if (
                temporary_path.stat().st_size
                <= self.MAX_IMAGE_BYTES
            ):
                return temporary_path

        # If still too large, resize.
        current = image

        for _ in range(6):

            width, height = current.size

            width = int(width * 0.85)
            height = int(height * 0.85)

            if width < 500 or height < 500:
                break

            current = current.resize(
                (width, height),
                Image.Resampling.LANCZOS,
            )

            current.save(
                temporary_path,
                format="JPEG",
                quality=65,
                optimize=True,
            )

            if (
                temporary_path.stat().st_size
                <= self.MAX_IMAGE_BYTES
            ):
                return temporary_path

        raise OCRSpaceError(
            "Could not compress image below "
            "OCR.space free API limit."
        )

    # ================================================================
    # REQUEST PROFILES
    # ================================================================

    def _get_request_profile(
        self,
        attempt: int,
    ) -> Dict[str, str]:
        """
        Return progressively lighter OCR.space request profiles.

        Attempt 1:
            Maximum quality/features.

        Attempt 2:
            Remove expensive overlay/scaling.

        Attempt 3:
            Minimal Engine 3 request for recovery.
        """

        # ------------------------------------------------------------
        # ATTEMPT 1
        # ------------------------------------------------------------

        if attempt == 1:
            return {
                "language": "auto",
                "isOverlayRequired": "true",
                "detectOrientation": "true",
                "scale": "true",
                "isTable": "true",
            }

        # ------------------------------------------------------------
        # ATTEMPT 2
        # ------------------------------------------------------------

        if attempt == 2:
            logger.warning(
                "OCR.space retry profile 2: "
                "disabling overlay and scaling."
            )

            return {
                "language": "auto",
                "isOverlayRequired": "false",
                "detectOrientation": "true",
                "scale": "false",
                "isTable": "true",
            }

        # ------------------------------------------------------------
        # ATTEMPT 3
        # ------------------------------------------------------------

        logger.warning(
            "OCR.space retry profile 3: "
            "using minimal Engine 3 request."
        )

        return {
            "language": "auto",
            "isOverlayRequired": "false",
            "detectOrientation": "false",
            "scale": "false",
            "isTable": "false",
        }

    # ================================================================
    # HTTP
    # ================================================================

    def _send_file(
        self,
        source_path: Path,
        page_number: Optional[int],
        is_pdf: bool,
    ) -> Dict[str, Any]:

        last_error = None

        for attempt in range(
            1,
            self.max_retries + 1,
        ):

            logger.info(
                "OCR.space attempt %d/%d",
                attempt,
                self.max_retries,
            )

            profile = self._get_request_profile(
                attempt
            )

            logger.info(
                "OCR.space profile: "
                "overlay=%s, orientation=%s, "
                "scale=%s, table=%s",
                profile["isOverlayRequired"],
                profile["detectOrientation"],
                profile["scale"],
                profile["isTable"],
            )

            try:

                with open(
                    source_path,
                    "rb",
                ) as file_handle:

                    mime_type = (
                        "application/pdf"
                        if is_pdf
                        else self._image_mime_type(
                            source_path
                        )
                    )

                    files = {
                        "file": (
                            source_path.name,
                            file_handle,
                            mime_type,
                        )
                    }

                    data = {
                        "language": profile["language"],
                        "isOverlayRequired": profile[
                            "isOverlayRequired"
                        ],
                        "detectOrientation": profile[
                            "detectOrientation"
                        ],
                        "scale": profile["scale"],
                        "isTable": profile["isTable"],
                        "OCREngine": self.engine,
                    }

                    if is_pdf:
                        data["filetype"] = "PDF"

                    headers = {
                        "apikey": self.api_key,
                    }

                    response = requests.post(
                        self.OCR_URL,
                        files=files,
                        data=data,
                        headers=headers,
                        timeout=(
                            20,
                            self.timeout,
                        ),
                    )

                logger.info(
                    "OCR.space HTTP status: %s",
                    response.status_code,
                )

                # ----------------------------------------------------
                # SUCCESS
                # ----------------------------------------------------

                if response.status_code == 200:

                    try:
                        response_data = response.json()
                    except ValueError as exc:
                        raise OCRSpaceError(
                            "OCR.space returned invalid JSON."
                        ) from exc

                    try:
                        return self._parse_response(
                            response_data=response_data,
                            source_path=source_path,
                            page_number=page_number,
                        )

                    except OCRSpaceError as exc:

                        # OCR.space sometimes returns HTTP 200
                        # but reports an internal processing timeout.
                        last_error = exc

                        logger.warning(
                            "OCR.space processing failed: %s",
                            exc,
                        )

                        if attempt < self.max_retries:

                            delay = min(
                                2 ** attempt,
                                8,
                            )

                            logger.info(
                                "Retrying with a lighter "
                                "OCR.space profile in %d seconds...",
                                delay,
                            )

                            time.sleep(delay)

                            continue

                        break

                # ----------------------------------------------------
                # TRANSIENT HTTP ERRORS
                # ----------------------------------------------------

                if response.status_code in {
                    408,
                    429,
                    500,
                    502,
                    503,
                    504,
                    522,
                    524,
                }:

                    response_preview = (
                        response.text[:500]
                        if response.text
                        else ""
                    )

                    last_error = OCRSpaceError(
                        "OCR.space HTTP "
                        f"{response.status_code}"
                        + (
                            f": {response_preview}"
                            if response_preview
                            else ""
                        )
                    )

                    logger.warning(
                        "%s",
                        last_error,
                    )

                    if attempt < self.max_retries:

                        delay = min(
                            2 ** attempt,
                            8,
                        )

                        logger.info(
                            "Retrying with a lighter "
                            "OCR.space profile in %d seconds...",
                            delay,
                        )

                        time.sleep(delay)

                        continue

                    break

                # ----------------------------------------------------
                # PERMANENT ERROR
                # ----------------------------------------------------

                error_text = (
                    response.text[:1000]
                    if response.text
                    else "No response body."
                )

                raise OCRSpaceError(
                    "OCR.space HTTP "
                    f"{response.status_code}: "
                    f"{error_text}"
                )

            except requests.Timeout as exc:

                last_error = exc

                logger.warning(
                    "OCR.space request timeout: %s",
                    exc,
                )

                if attempt < self.max_retries:

                    delay = min(
                        2 ** attempt,
                        8,
                    )

                    logger.info(
                        "Retrying with a lighter "
                        "OCR.space profile in %d seconds...",
                        delay,
                    )

                    time.sleep(delay)

                    continue

            except requests.RequestException as exc:

                last_error = exc

                logger.warning(
                    "OCR.space request error: %s",
                    exc,
                )

                if attempt < self.max_retries:

                    delay = min(
                        2 ** attempt,
                        8,
                    )

                    time.sleep(delay)

                    continue

            except OCRSpaceError:
                raise

            except Exception as exc:

                last_error = exc

                logger.warning(
                    "Unexpected OCR.space error: %s",
                    exc,
                )

                break

        raise OCRSpaceError(
            "OCR.space failed after "
            f"{self.max_retries} attempts: "
            f"{last_error}"
        )

    # ================================================================
    # RESPONSE PARSING
    # ================================================================

    def _parse_response(
        self,
        response_data: Dict[str, Any],
        source_path: Path,
        page_number: Optional[int],
    ) -> Dict[str, Any]:

        if not isinstance(
            response_data,
            dict,
        ):
            raise OCRSpaceError(
                "Invalid OCR.space response."
            )

        # ------------------------------------------------------------
        # OCR.SPACE PROCESSING ERROR
        # ------------------------------------------------------------

        if response_data.get(
            "IsErroredOnProcessing"
        ):

            error_message = response_data.get(
                "ErrorMessage",
                "Unknown OCR.space processing error.",
            )

            if isinstance(
                error_message,
                list,
            ):
                error_message = " ".join(
                    str(item)
                    for item in error_message
                )

            error_details = response_data.get(
                "ErrorDetails"
            )

            if error_details:
                error_message = (
                    f"{error_message} | "
                    f"{error_details}"
                )

            raise OCRSpaceError(
                "OCR.space processing error: "
                f"{error_message}"
            )

        # ------------------------------------------------------------
        # PARSED RESULTS
        # ------------------------------------------------------------

        parsed_results = response_data.get(
            "ParsedResults",
            [],
        )

        if not parsed_results:
            raise OCRSpaceError(
                "OCR.space returned no ParsedResults."
            )

        text_parts = []
        overlays = []

        for parsed_result in parsed_results:

            if not isinstance(
                parsed_result,
                dict,
            ):
                continue

            # --------------------------------------------------------
            # Detect per-page OCR engine failures.
            # --------------------------------------------------------

            exit_code = parsed_result.get(
                "FileParseExitCode"
            )

            if str(exit_code) in {
                "-10",
                "-20",
                "-30",
                "-99",
            }:

                error_message = parsed_result.get(
                    "ErrorDetails"
                    or "ErrorMessage"
                )

                if not error_message:
                    error_message = (
                        f"OCR.space parser "
                        f"exit code {exit_code}"
                    )

                raise OCRSpaceError(
                    f"OCR.space parsing error: "
                    f"{error_message}"
                )

            parsed_text = parsed_result.get(
                "ParsedText",
                "",
            )

            if parsed_text:
                text_parts.append(
                    str(parsed_text).strip()
                )

            overlay = parsed_result.get(
                "TextOverlay"
            )

            if overlay:
                overlays.append(
                    overlay
                )

        text = "\n\n".join(
            part
            for part in text_parts
            if part
        ).strip()

        if not text:
            raise OCRSpaceError(
                "OCR.space returned empty OCR text."
            )

        return {
            "text": text,
            "source": "ocrspace",
            "engine": self.engine,
            "input_path": str(source_path),
            "page_number": page_number,
            "parsed_results": parsed_results,
            "overlays": overlays,
            "raw_response": response_data,
        }

    # ================================================================
    # HELPERS
    # ================================================================

    @staticmethod
    def _image_mime_type(
        path: Path,
    ) -> str:

        suffix = path.suffix.lower()

        if suffix in {
            ".jpg",
            ".jpeg",
        }:
            return "image/jpeg"

        if suffix == ".png":
            return "image/png"

        if suffix == ".webp":
            return "image/webp"

        if suffix == ".bmp":
            return "image/bmp"

        if suffix == ".tiff":
            return "image/tiff"

        return "application/octet-stream"