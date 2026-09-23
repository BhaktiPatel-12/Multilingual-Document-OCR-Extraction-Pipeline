# import os
# import sys
# import json
# import signal
# import subprocess
# import time
# import uuid
# import re
# from pathlib import Path
# import threading

# class SuryaOCRService:
#     """
#     Astra-OCR Surya OCR Service

#     Pipeline:
#         Image
#           ↓
#         Surya OCR
#           ↓
#         results.json
#           ↓
#         Read JSON immediately
#           ↓
#         Return OCR result

#     IMPORTANT:
#     Once a valid results.json is detected, this service
#     immediately reads and returns the OCR result.

#     It intentionally does NOT:
#         - wait for Surya to finish
#         - terminate Surya
#         - kill Surya
#         - call _stop_process()
#         - perform cleanup

#     WINDOWS NOTE:
#     Surya stops its internal llama-server child using a
#     CTRL_C_EVENT broadcast. On Windows that broadcast can hit
#     THIS process too (even in a separate process group), which
#     raises a spurious KeyboardInterrupt in our own code. To
#     avoid that, SIGINT is temporarily ignored while we wait
#     for and read results.json, then restored afterward.
#     """

#     # ============================================================
#     # INITIALIZATION
#     # ============================================================

#     def __init__(
#         self,
#         output_dir="surya_output",
#         llama_cpp_binary=None,
#     ):
#         # --------------------------------------------------------
#         # Force llama.cpp backend
#         # --------------------------------------------------------

#         os.environ["SURYA_INFERENCE_BACKEND"] = "llamacpp"

#         # --------------------------------------------------------
#         # llama-server location
#         # --------------------------------------------------------

#         if llama_cpp_binary is None:
#             llama_cpp_binary = (
#                 r"C:\Users\dalwa\AppData\Local\Microsoft\WinGet\Packages"
#                 r"\ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe"
#                 r"\llama-server.exe"
#             )

#         self.llama_binary = Path(
#             llama_cpp_binary
#         )

#         # --------------------------------------------------------
#         # Set environment variable for Surya
#         # --------------------------------------------------------

#         if self.llama_binary.exists():
#             os.environ["LLAMA_CPP_BINARY"] = str(
#                 self.llama_binary
#             )

#         # --------------------------------------------------------
#         # Base output directory
#         # --------------------------------------------------------

#         self.output_dir = Path(
#             output_dir
#         )

#         self.output_dir.mkdir(
#             parents=True,
#             exist_ok=True,
#         )

#         # --------------------------------------------------------
#         # Startup information
#         # --------------------------------------------------------

#         print()
#         print("=" * 40)
#         print("        SURYA OCR SERVICE")
#         print("=" * 40)

#         print(
#             "llama-server binary:"
#         )

#         print(
#             self.llama_binary
#         )

#     # ============================================================
#     # LANGUAGE CLASSIFICATION
#     # ============================================================

#     def classify_language(self, text):
#         """
#         Detect language/script from OCR text.

#         Supported:
#             eng = English
#             hin = Hindi
#             guj = Gujarati
#             mixed = Multiple scripts
#             unknown = No supported script detected
#         """

#         if not text:
#             return "unknown"

#         text = str(text)

#         english_count = 0
#         hindi_count = 0
#         gujarati_count = 0

#         for char in text:

#             code = ord(char)

#             # ----------------------------------------------------
#             # Latin / English
#             # ----------------------------------------------------

#             if (
#                 "A" <= char <= "Z"
#                 or "a" <= char <= "z"
#             ):
#                 english_count += 1

#             # ----------------------------------------------------
#             # Devanagari / Hindi
#             # ----------------------------------------------------

#             elif 0x0900 <= code <= 0x097F:
#                 hindi_count += 1

#             # ----------------------------------------------------
#             # Gujarati
#             # ----------------------------------------------------

#             elif 0x0A80 <= code <= 0x0AFF:
#                 gujarati_count += 1

#         detected = []

#         if english_count > 0:
#             detected.append("eng")

#         if hindi_count > 0:
#             detected.append("hin")

#         if gujarati_count > 0:
#             detected.append("guj")

#         if not detected:
#             return "unknown"

#         if len(detected) > 1:
#             return "mixed"

#         return detected[0]

#     # ============================================================
#     # DETECT ALL LANGUAGES IN TEXT
#     # ============================================================

#     def detect_languages_from_text(self, text):
#         """
#         Return all supported scripts found in text.
#         """

#         detected = set()

#         if not text:
#             return detected

#         for char in str(text):

#             code = ord(char)

#             # English
#             if (
#                 "A" <= char <= "Z"
#                 or "a" <= char <= "z"
#             ):
#                 detected.add("eng")

#             # Hindi
#             elif 0x0900 <= code <= 0x097F:
#                 detected.add("hin")

#             # Gujarati
#             elif 0x0A80 <= code <= 0x0AFF:
#                 detected.add("guj")

#         return detected

#     # ============================================================
#     # HTML CLEANING
#     # ============================================================

#     def clean_html(self, html):
#         """
#         Convert Surya HTML output into plain readable text.
#         """

#         if html is None:
#             return ""

#         text = str(html)

#         # --------------------------------------------------------
#         # Remove image tags
#         # --------------------------------------------------------

#         text = re.sub(
#             r"<img[^>]*>",
#             "",
#             text,
#             flags=re.IGNORECASE,
#         )

#         # --------------------------------------------------------
#         # Convert structural tags into line breaks
#         # --------------------------------------------------------

#         text = re.sub(
#             r"</?(?:p|div|h[1-6]|li|tr|br|section|article)[^>]*>",
#             "\n",
#             text,
#             flags=re.IGNORECASE,
#         )

#         # --------------------------------------------------------
#         # Remove remaining HTML
#         # --------------------------------------------------------

#         text = re.sub(
#             r"<[^>]+>",
#             "",
#             text,
#         )

#         # --------------------------------------------------------
#         # Decode common HTML entities
#         # --------------------------------------------------------

#         replacements = {
#             "&nbsp;": " ",
#             "&amp;": "&",
#             "&lt;": "<",
#             "&gt;": ">",
#             "&quot;": '"',
#             "&#39;": "'",
#         }

#         for old, new in replacements.items():
#             text = text.replace(
#                 old,
#                 new,
#             )

#         # --------------------------------------------------------
#         # Normalize spaces
#         # --------------------------------------------------------

#         text = re.sub(
#             r"[ \t]+",
#             " ",
#             text,
#         )

#         # --------------------------------------------------------
#         # Normalize excessive newlines
#         # --------------------------------------------------------

#         text = re.sub(
#             r"\n\s*\n\s*\n+",
#             "\n\n",
#             text,
#         )

#         return text.strip()

#     # ============================================================
#     # FIND JSON FILE
#     # ============================================================

#     def find_json_file(self, output_dir):
#         """
#         Search recursively for results.json.

#         Because every OCR run uses a unique directory,
#         this cannot accidentally pick an old run's JSON.
#         """

#         output_dir = Path(
#             output_dir
#         )

#         if not output_dir.exists():
#             return None

#         json_files = list(
#             output_dir.rglob(
#                 "results.json"
#             )
#         )

#         if not json_files:
#             return None

#         # Newest first
#         json_files.sort(
#             key=lambda path: path.stat().st_mtime,
#             reverse=True,
#         )

#         return json_files[0]

#     # ============================================================
#     # VALIDATE JSON
#     # ============================================================

#     def is_valid_json(self, json_file):
#         """
#         Check whether results.json exists,
#         is non-empty, and contains valid JSON.
#         """

#         if json_file is None:
#             return False

#         json_file = Path(
#             json_file
#         )

#         if not json_file.exists():
#             return False

#         try:

#             if json_file.stat().st_size == 0:
#                 return False

#         except OSError:
#             return False

#         try:

#             with open(
#                 json_file,
#                 "r",
#                 encoding="utf-8",
#             ) as file:

#                 data = json.load(file)

#             return isinstance(
#                 data,
#                 dict,
#             )

#         except (
#             json.JSONDecodeError,
#             UnicodeDecodeError,
#             OSError,
#         ):
#             return False

#     # ============================================================
#     # PAGE SORTING
#     # ============================================================

#     def page_sort_key(self, item):
#         """
#         Natural page sorting.
#         """

#         try:

#             return int(
#                 item.get(
#                     "page",
#                     item.get(
#                         "page_number",
#                         0,
#                     ),
#                 )
#             )

#         except (
#             TypeError,
#             ValueError,
#         ):

#             return 0

#     # ============================================================
#     # EXTRACT OCR RESULT
#     # ============================================================

#     def extract_text_from_json(self, json_file):
#         """
#         Read Surya results.json and convert it into
#         Astra-OCR normalized format.
#         """

#         json_file = Path(
#             json_file
#         )

#         print()
#         print(
#             "Reading OCR JSON:"
#         )
#         print(
#             json_file
#         )

#         # --------------------------------------------------------
#         # IMPORTANT:
#         # Explicit UTF-8 reading.
#         # --------------------------------------------------------

#         with open(
#             json_file,
#             "r",
#             encoding="utf-8",
#         ) as file:

#             data = json.load(file)

#         results = []

#         # ========================================================
#         # Expected Surya structure:
#         #
#         # {
#         #     "page_002": [
#         #         {
#         #             "blocks": [...]
#         #         }
#         #     ]
#         # }
#         # ========================================================

#         for source_name, pages in data.items():

#             if not isinstance(
#                 pages,
#                 list,
#             ):
#                 continue

#             for page_data in pages:

#                 if not isinstance(
#                     page_data,
#                     dict,
#                 ):
#                     continue

#                 # ------------------------------------------------
#                 # Page number
#                 # ------------------------------------------------

#                 page_number = page_data.get(
#                     "page",
#                     page_data.get(
#                         "page_number",
#                         1,
#                     ),
#                 )

#                 # ------------------------------------------------
#                 # Image dimensions
#                 # ------------------------------------------------

#                 image_bbox = page_data.get(
#                     "image_bbox",
#                     [],
#                 )

#                 # ------------------------------------------------
#                 # Blocks
#                 # ------------------------------------------------

#                 blocks = page_data.get(
#                     "blocks",
#                     [],
#                 )

#                 if not isinstance(
#                     blocks,
#                     list,
#                 ):
#                     continue

#                 # =================================================
#                 # Process each block
#                 # =================================================

#                 for block in blocks:

#                     if not isinstance(
#                         block,
#                         dict,
#                     ):
#                         continue

#                     # ------------------------------------------------
#                     # Get HTML
#                     # ------------------------------------------------

#                     html = block.get(
#                         "html",
#                         "",
#                     )

#                     # ------------------------------------------------
#                     # Convert HTML → text
#                     # ------------------------------------------------

#                     text = self.clean_html(
#                         html
#                     )

#                     # ------------------------------------------------
#                     # Ignore empty blocks
#                     # ------------------------------------------------

#                     if not text:
#                         continue

#                     # ------------------------------------------------
#                     # Confidence
#                     # ------------------------------------------------

#                     confidence = block.get(
#                         "confidence",
#                         0.0,
#                     )

#                     try:

#                         confidence = float(
#                             confidence
#                         )

#                     except (
#                         TypeError,
#                         ValueError,
#                     ):

#                         confidence = 0.0

#                     # ------------------------------------------------
#                     # Bounding box
#                     # ------------------------------------------------

#                     bbox = block.get(
#                         "bbox",
#                         block.get(
#                             "polygon",
#                             [],
#                         ),
#                     )

#                     # ------------------------------------------------
#                     # Layout label
#                     # ------------------------------------------------

#                     label = block.get(
#                         "label",
#                         "",
#                     )

#                     raw_label = block.get(
#                         "raw_label",
#                         label,
#                     )

#                     # ------------------------------------------------
#                     # Reading order
#                     # ------------------------------------------------

#                     reading_order = block.get(
#                         "reading_order",
#                         0,
#                     )

#                     # ------------------------------------------------
#                     # Language
#                     # ------------------------------------------------

#                     language = self.classify_language(
#                         text
#                     )

#                     # ------------------------------------------------
#                     # Save normalized block
#                     # ------------------------------------------------

#                     results.append(
#                         {
#                             "text": text,
#                             "language": language,
#                             "confidence": confidence,
#                             "bbox": bbox,
#                             "label": label,
#                             "raw_label": raw_label,
#                             "reading_order": reading_order,
#                             "page": page_number,
#                             "page_number": page_number,
#                             "image_bbox": image_bbox,
#                             "source": source_name,
#                         }
#                     )

#         # ========================================================
#         # Sort OCR blocks
#         # ========================================================

#         results.sort(
#             key=lambda item: (
#                 item.get(
#                     "page",
#                     0,
#                 ),
#                 item.get(
#                     "reading_order",
#                     0,
#                 ),
#             )
#         )

#         # ========================================================
#         # Detect all languages
#         # ========================================================

#         detected_languages = set()

#         for item in results:

#             language = item.get(
#                 "language",
#                 "unknown",
#             )

#             if language == "eng":

#                 detected_languages.add(
#                     "eng"
#                 )

#             elif language == "hin":

#                 detected_languages.add(
#                     "hin"
#                 )

#             elif language == "guj":

#                 detected_languages.add(
#                     "guj"
#                 )

#             elif language == "mixed":

#                 text = item.get(
#                     "text",
#                     "",
#                 )

#                 detected_languages.update(
#                     self.detect_languages_from_text(
#                         text
#                     )
#                 )

#         # ========================================================
#         # Final normalized OCR result
#         # ========================================================

#         result = {
#             "results": results,
#             "total_blocks": len(results),
#             "detected_languages": sorted(
#                 detected_languages
#             ),
#             "multilingual": (
#                 len(detected_languages) > 1
#             ),
#             "source_json": str(
#                 json_file
#             ),
#         }

#         print()
#         print(
#             f"OCR blocks extracted: "
#             f"{len(results)}"
#         )

#         if detected_languages:

#             print(
#                 "Detected languages: "
#                 + ", ".join(
#                     sorted(
#                         detected_languages
#                     )
#                 )
#             )

#         else:

#             print(
#                 "Detected languages: None"
#             )

#         return result

#     # ============================================================
#     # SAVE NORMALIZED RESULT TO DISK
#     # ============================================================

#     def save_result_json(self, result, run_dir, image_path):
#         """
#         Write the normalized OCR result (the dict returned by
#         extract_text_from_json) to a clean, stable JSON file
#         of our own, separate from Surya's internal results.json.
#         """

#         out_path = (
#             Path(run_dir)
#             / f"{Path(image_path).stem}_ocr.json"
#         )

#         with open(
#             out_path,
#             "w",
#             encoding="utf-8",
#         ) as file:

#             json.dump(
#                 result,
#                 file,
#                 ensure_ascii=False,
#                 indent=2,
#             )

#         print()
#         print(
#             f"Saved normalized OCR JSON: {out_path}"
#         )

#         return out_path

#     # ============================================================
#     # CREATE UNIQUE RUN DIRECTORY
#     # ============================================================

#     def create_run_directory(
#         self,
#         base_output_dir,
#     ):
#         """
#         Create a completely unique directory for each OCR run.
#         """

#         timestamp = time.strftime(
#             "%Y%m%d_%H%M%S"
#         )

#         unique_id = uuid.uuid4().hex[:8]

#         run_dir = (
#             Path(base_output_dir)
#             / f"run_{timestamp}_{unique_id}"
#         )

#         run_dir.mkdir(
#             parents=True,
#             exist_ok=True,
#         )

#         return run_dir

#     # ============================================================
#     # MAIN OCR FUNCTION
#     # ============================================================

#     def run_ocr(
#         self,
#         image_path,
#         output_dir=None,
#         timeout=300,
#         save_json=True,
#     ):
#         """
#         Run Surya OCR.

#         CRITICAL DESIGN:

#             Start Surya
#                 ↓
#             Wait for results.json
#                 ↓
#             Validate JSON
#                 ↓
#             Read JSON
#                 ↓
#             RETURN

#         There is intentionally NO cleanup after this point.

#         WINDOWS SIGNAL GUARD:

#         From the moment the surya_ocr process is started until
#         we've finished reading/returning the result, SIGINT is
#         ignored. This is because Surya stops its internal
#         llama-server via a CTRL_C_EVENT broadcast, which on
#         Windows can reach THIS process too and abort us before
#         we ever get to read results.json. We don't need to be
#         interruptible during this short window anyway, since we
#         never touch the child process ourselves.
#         """

#         # ========================================================
#         # Validate image
#         # ========================================================

#         image_path = Path(
#             image_path
#         ).resolve()

#         if not image_path.exists():

#             raise FileNotFoundError(
#                 f"Image not found: "
#                 f"{image_path}"
#             )

#         # ========================================================
#         # Base output directory
#         # ========================================================

#         if output_dir is not None:

#             base_output_dir = Path(
#                 output_dir
#             ).resolve()

#         else:

#             base_output_dir = (
#                 self.output_dir.resolve()
#             )

#         base_output_dir.mkdir(
#             parents=True,
#             exist_ok=True,
#         )

#         # ========================================================
#         # Unique run directory
#         # ========================================================

#         run_dir = self.create_run_directory(
#             base_output_dir
#         )

#         # ========================================================
#         # Expected JSON location
#         #
#         # Surya creates:
#         #
#         # run_xxxxx/
#         #     page_002/
#         #         results.json
#         # ========================================================

#         expected_json = (
#             run_dir
#             / image_path.stem
#             / "results.json"
#         )

#         # ========================================================
#         # Display
#         # ========================================================

#         print()
#         print("=" * 40)
#         print("             SURYA OCR")
#         print("=" * 40)

#         print(
#             f"Image : {image_path}"
#         )

#         print(
#             f"Output: {run_dir}"
#         )

#         # ========================================================
#         # Command
#         # ========================================================

#         command = [
#             "surya_ocr",
#             str(image_path),
#             "--images",
#             "--output_dir",
#             str(run_dir),
#         ]

#         print()
#         print(
#             "Running Surya..."
#         )

#         print(
#             " ".join(command)
#         )

#         # ========================================================
#         # Environment
#         # ========================================================

#         process_env = os.environ.copy()

#         # Force llama.cpp
#         process_env[
#             "SURYA_INFERENCE_BACKEND"
#         ] = "llamacpp"

#         # llama-server
#         if self.llama_binary.exists():

#             process_env[
#                 "LLAMA_CPP_BINARY"
#             ] = str(
#                 self.llama_binary
#             )

#         # ========================================================
#         # START SURYA
#         #
#         # Keep it in its own process group too (harmless, and
#         # helps on some setups) - but the real fix is the SIGINT
#         # guard below, since group id 0 broadcasts ignore group
#         # boundaries on Windows.
#         # ========================================================

#         popen_kwargs = {}

#         if sys.platform == "win32":

#             popen_kwargs["creationflags"] = (
#                 subprocess.CREATE_NEW_PROCESS_GROUP
#             )

#         try:

#             process = subprocess.Popen(
#                 command,
#                 stdout=None,
#                 stderr=None,
#                 env=process_env,
#                 **popen_kwargs,
#             )

#         except FileNotFoundError as exc:

#             raise RuntimeError(
#                 "Could not start 'surya_ocr'. "
#                 "Make sure Surya is installed "
#                 "inside the active virtual environment."
#             ) from exc

#         start_time = time.time()

#         print()
#         print(
#             "Waiting for results.json..."
#         )

#         # ========================================================
#         # SIGINT GUARD
#         #
#         # From here until we return, ignore Ctrl+C style signals
#         # so Surya's own (occasionally flaky) shutdown of
#         # llama-server can never abort OUR process mid-read.
#         # ========================================================

#         old_sigint_handler = signal.getsignal(
#             signal.SIGINT
#         )

#         if threading.current_thread() is threading.main_thread():
#             signal.signal(
#             signal.SIGINT,
#             signal.SIG_IGN,
#             )

#         try:

#             # ====================================================
#             # WAIT FOR JSON ONLY
#             # ====================================================

#             while True:

#                 # ------------------------------------------------
#                 # 1. Check exact expected JSON
#                 # ------------------------------------------------

#                 if (
#                     expected_json.exists()
#                     and self.is_valid_json(
#                         expected_json
#                     )
#                 ):

#                     print()
#                     print(
#                         "JSON output detected:"
#                     )

#                     print(
#                         expected_json
#                     )

#                     print()
#                     print(
#                         "Valid results.json found."
#                     )

#                     print(
#                         "Reading OCR result..."
#                     )

#                     # =============================================
#                     # VERY IMPORTANT
#                     #
#                     # DO NOT TOUCH `process` HERE.
#                     #
#                     # No:
#                     #     process.wait()
#                     #     process.terminate()
#                     #     process.kill()
#                     #     _stop_process()
#                     #     cleanup
#                     #
#                     # Just read JSON and return.
#                     # =============================================

#                     result = (
#                         self.extract_text_from_json(
#                             expected_json
#                         )
#                     )

#                     if save_json:

#                         self.save_result_json(
#                             result,
#                             run_dir,
#                             image_path,
#                         )

#                     print()
#                     print(
#                         "OCR JSON successfully processed."
#                     )

#                     return result

#                 # ------------------------------------------------
#                 # 2. Fallback recursive search
#                 # ------------------------------------------------

#                 candidate = self.find_json_file(
#                     run_dir
#                 )

#                 if (
#                     candidate is not None
#                     and self.is_valid_json(
#                         candidate
#                     )
#                 ):

#                     print()
#                     print(
#                         "JSON output detected:"
#                     )

#                     print(
#                         candidate
#                     )

#                     print()
#                     print(
#                         "Valid results.json found."
#                     )

#                     print(
#                         "Reading OCR result..."
#                     )

#                     result = (
#                         self.extract_text_from_json(
#                             candidate
#                         )
#                     )

#                     if save_json:

#                         self.save_result_json(
#                             result,
#                             run_dir,
#                             image_path,
#                         )

#                     print()
#                     print(
#                         "OCR JSON successfully processed."
#                     )

#                     return result

#                 # ------------------------------------------------
#                 # 3. Timeout
#                 # ------------------------------------------------

#                 elapsed = (
#                     time.time()
#                     - start_time
#                 )

#                 if elapsed > timeout:

#                     raise TimeoutError(
#                         "Surya OCR did not produce "
#                         "a valid results.json within "
#                         f"{timeout} seconds.\n"
#                         f"Output directory: {run_dir}"
#                     )

#                 # ------------------------------------------------
#                 # 4. Check if process exited before JSON
#                 # ------------------------------------------------

#                 return_code = process.poll()

#                 if return_code is not None:

#                     # --------------------------------------------
#                     # One final search.
#                     # --------------------------------------------

#                     candidate = self.find_json_file(
#                         run_dir
#                     )

#                     if (
#                         candidate is not None
#                         and self.is_valid_json(
#                             candidate
#                         )
#                     ):

#                         print()
#                         print(
#                             "JSON output detected after "
#                             "process exit:"
#                         )

#                         print(
#                             candidate
#                         )

#                         result = (
#                             self.extract_text_from_json(
#                                 candidate
#                             )
#                         )

#                         if save_json:

#                             self.save_result_json(
#                                 result,
#                                 run_dir,
#                                 image_path,
#                             )

#                         return result

#                     raise RuntimeError(
#                         "Surya OCR process exited "
#                         f"with code {return_code} "
#                         "without producing a valid "
#                         "results.json."
#                     )

#                 # ------------------------------------------------
#                 # Poll again
#                 # ------------------------------------------------

#                 time.sleep(0.25)

#         finally:
#              if threading.current_thread() is threading.main_thread():
#                  signal.signal(
#                  signal.SIGINT,
#                  signal.SIG_IGN,
#                 )


# # ================================================================
# # DIRECT TEST
# # ================================================================

# if __name__ == "__main__":

#     service = SuryaOCRService()

#     result = service.run_ocr(
#         r"output/rendered/page_002.png"
#     )

#     print()
#     print("=" * 40)
#     print("             FINAL RESULT")
#     print("=" * 40)

#     print()
#     print(
#         f"Total text blocks: "
#         f"{result['total_blocks']}"
#     )

#     print(
#         f"Detected languages: "
#         f"{result['detected_languages']}"
#     )

#     print(
#         f"Multilingual: "
#         f"{result['multilingual']}"
#     )

#     for i, item in enumerate(
#         result["results"],
#         start=1,
#     ):

#         print()
#         print(
#             "-" * 40
#         )

#         print(
#             f"Block {i}"
#         )

#         print(
#             f"Text      : "
#             f"{item['text']}"
#         )

#         print(
#             f"Language  : "
#             f"{item['language']}"
#         )

#         print(
#             f"Confidence: "
#             f"{item['confidence']}"
#         )

#         print(
#             f"BBox      : "
#             f"{item['bbox']}"
#         )

#     print()
#     print("=" * 40)
#     print("          SURYA TEST COMPLETE")
#     print("=" * 40)















































# import os
# import sys
# import json
# import signal
# import subprocess
# import time
# import uuid
# import re
# from pathlib import Path
# import threading


# class SuryaOCRService:
#     """
#     Astra-OCR Surya OCR Service

#     Pipeline:
#         Image
#           ↓
#         Surya OCR
#           ↓
#         results.json
#           ↓
#         Read JSON immediately
#           ↓
#         Return OCR result

#     IMPORTANT:
#     Surya is run with --keep_server so that the internal
#     llama-server stays alive between OCR calls.

#     This allows:

#         Level 1
#            ↓
#         same llama-server
#            ↓
#         Level 2 Enhanced
#            ↓
#         same llama-server
#            ↓
#         Level 2 Threshold
#            ↓
#         same llama-server
#            ↓
#         next page
#            ↓
#         same llama-server

#     This avoids repeatedly loading the Surya model.

#     WINDOWS NOTE:
#     Surya can use CTRL_C_EVENT while managing its internal
#     llama-server. SIGINT is temporarily ignored while we
#     wait for and read results.json.
#     """

#     # ============================================================
#     # INITIALIZATION
#     # ============================================================

#     def __init__(
#         self,
#         output_dir="surya_output",
#         llama_cpp_binary=None,
#     ):
#         # --------------------------------------------------------
#         # Force llama.cpp backend
#         # --------------------------------------------------------

#         os.environ["SURYA_INFERENCE_BACKEND"] = "llamacpp"

#         # --------------------------------------------------------
#         # IMPORTANT:
#         #
#         # Keep the inference server alive between Surya calls.
#         #
#         # This is the environment equivalent of --keep_server.
#         # --------------------------------------------------------

#         os.environ["SURYA_INFERENCE_KEEP_ALIVE"] = "1"

#         # --------------------------------------------------------
#         # llama-server location
#         # --------------------------------------------------------

#         if llama_cpp_binary is None:
#             llama_cpp_binary = (
#                 r"C:\Users\dalwa\AppData\Local\Microsoft\WinGet\Packages"
#                 r"\ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe"
#                 r"\llama-server.exe"
#             )

#         self.llama_binary = Path(
#             llama_cpp_binary
#         )

#         # --------------------------------------------------------
#         # Set environment variable for Surya
#         # --------------------------------------------------------

#         if self.llama_binary.exists():
#             os.environ["LLAMA_CPP_BINARY"] = str(
#                 self.llama_binary
#             )

#         # --------------------------------------------------------
#         # Base output directory
#         # --------------------------------------------------------

#         self.output_dir = Path(
#             output_dir
#         )

#         self.output_dir.mkdir(
#             parents=True,
#             exist_ok=True,
#         )

#         # --------------------------------------------------------
#         # Startup information
#         # --------------------------------------------------------

#         print()
#         print("=" * 40)
#         print("        SURYA OCR SERVICE")
#         print("=" * 40)

#         print(
#             "llama-server binary:"
#         )

#         print(
#             self.llama_binary
#         )

#         print(
#             "Inference backend: llamacpp"
#         )

#         print(
#             "Persistent server: ENABLED"
#         )

#     # ============================================================
#     # LANGUAGE CLASSIFICATION
#     # ============================================================

#     def classify_language(self, text):
#         """
#         Detect language/script from OCR text.

#         Supported:
#             eng = English
#             hin = Hindi
#             guj = Gujarati
#             mixed = Multiple scripts
#             unknown = No supported script detected
#         """

#         if not text:
#             return "unknown"

#         text = str(text)

#         english_count = 0
#         hindi_count = 0
#         gujarati_count = 0

#         for char in text:

#             code = ord(char)

#             # ----------------------------------------------------
#             # Latin / English
#             # ----------------------------------------------------

#             if (
#                 "A" <= char <= "Z"
#                 or "a" <= char <= "z"
#             ):
#                 english_count += 1

#             # ----------------------------------------------------
#             # Devanagari / Hindi
#             # ----------------------------------------------------

#             elif 0x0900 <= code <= 0x097F:
#                 hindi_count += 1

#             # ----------------------------------------------------
#             # Gujarati
#             # ----------------------------------------------------

#             elif 0x0A80 <= code <= 0x0AFF:
#                 gujarati_count += 1

#         detected = []

#         if english_count > 0:
#             detected.append("eng")

#         if hindi_count > 0:
#             detected.append("hin")

#         if gujarati_count > 0:
#             detected.append("guj")

#         if not detected:
#             return "unknown"

#         if len(detected) > 1:
#             return "mixed"

#         return detected[0]

#     # ============================================================
#     # DETECT ALL LANGUAGES IN TEXT
#     # ============================================================

#     def detect_languages_from_text(self, text):
#         """
#         Return all supported scripts found in text.
#         """

#         detected = set()

#         if not text:
#             return detected

#         for char in str(text):

#             code = ord(char)

#             # English
#             if (
#                 "A" <= char <= "Z"
#                 or "a" <= char <= "z"
#             ):
#                 detected.add("eng")

#             # Hindi
#             elif 0x0900 <= code <= 0x097F:
#                 detected.add("hin")

#             # Gujarati
#             elif 0x0A80 <= code <= 0x0AFF:
#                 detected.add("guj")

#         return detected

#     # ============================================================
#     # HTML CLEANING
#     # ============================================================

#     def clean_html(self, html):
#         """
#         Convert Surya HTML output into plain readable text.
#         """

#         if html is None:
#             return ""

#         text = str(html)

#         # --------------------------------------------------------
#         # Remove image tags
#         # --------------------------------------------------------

#         text = re.sub(
#             r"<img[^>]*>",
#             "",
#             text,
#             flags=re.IGNORECASE,
#         )

#         # --------------------------------------------------------
#         # Convert structural tags into line breaks
#         # --------------------------------------------------------

#         text = re.sub(
#             r"</?(?:p|div|h[1-6]|li|tr|br|section|article)[^>]*>",
#             "\n",
#             text,
#             flags=re.IGNORECASE,
#         )

#         # --------------------------------------------------------
#         # Remove remaining HTML
#         # --------------------------------------------------------

#         text = re.sub(
#             r"<[^>]+>",
#             "",
#             text,
#         )

#         # --------------------------------------------------------
#         # Decode common HTML entities
#         # --------------------------------------------------------

#         replacements = {
#             "&nbsp;": " ",
#             "&amp;": "&",
#             "&lt;": "<",
#             "&gt;": ">",
#             "&quot;": '"',
#             "&#39;": "'",
#         }

#         for old, new in replacements.items():
#             text = text.replace(
#                 old,
#                 new,
#             )

#         # --------------------------------------------------------
#         # Normalize spaces
#         # --------------------------------------------------------

#         text = re.sub(
#             r"[ \t]+",
#             " ",
#             text,
#         )

#         # --------------------------------------------------------
#         # Normalize excessive newlines
#         # --------------------------------------------------------

#         text = re.sub(
#             r"\n\s*\n\s*\n+",
#             "\n\n",
#             text,
#         )

#         return text.strip()

#     # ============================================================
#     # FIND JSON FILE
#     # ============================================================

#     def find_json_file(self, output_dir):
#         """
#         Search recursively for results.json.

#         Because every OCR run uses a unique directory,
#         this cannot accidentally pick an old run's JSON.
#         """

#         output_dir = Path(
#             output_dir
#         )

#         if not output_dir.exists():
#             return None

#         json_files = list(
#             output_dir.rglob(
#                 "results.json"
#             )
#         )

#         if not json_files:
#             return None

#         # Newest first
#         json_files.sort(
#             key=lambda path: path.stat().st_mtime,
#             reverse=True,
#         )

#         return json_files[0]

#     # ============================================================
#     # VALIDATE JSON
#     # ============================================================

#     def is_valid_json(self, json_file):
#         """
#         Check whether results.json exists,
#         is non-empty, and contains valid JSON.
#         """

#         if json_file is None:
#             return False

#         json_file = Path(
#             json_file
#         )

#         if not json_file.exists():
#             return False

#         try:

#             if json_file.stat().st_size == 0:
#                 return False

#         except OSError:
#             return False

#         try:

#             with open(
#                 json_file,
#                 "r",
#                 encoding="utf-8",
#             ) as file:

#                 data = json.load(file)

#             return isinstance(
#                 data,
#                 dict,
#             )

#         except (
#             json.JSONDecodeError,
#             UnicodeDecodeError,
#             OSError,
#         ):
#             return False

#     # ============================================================
#     # PAGE SORTING
#     # ============================================================

#     def page_sort_key(self, item):
#         """
#         Natural page sorting.
#         """

#         try:

#             return int(
#                 item.get(
#                     "page",
#                     item.get(
#                         "page_number",
#                         0,
#                     ),
#                 )
#             )

#         except (
#             TypeError,
#             ValueError,
#         ):

#             return 0

#     # ============================================================
#     # EXTRACT OCR RESULT
#     # ============================================================

#     def extract_text_from_json(self, json_file):
#         """
#         Read Surya results.json and convert it into
#         Astra-OCR normalized format.
#         """

#         json_file = Path(
#             json_file
#         )

#         print()
#         print(
#             "Reading OCR JSON:"
#         )
#         print(
#             json_file
#         )

#         # --------------------------------------------------------
#         # IMPORTANT:
#         # Explicit UTF-8 reading.
#         # --------------------------------------------------------

#         with open(
#             json_file,
#             "r",
#             encoding="utf-8",
#         ) as file:

#             data = json.load(file)

#         results = []

#         # ========================================================
#         # Expected Surya structure:
#         #
#         # {
#         #     "page_002": [
#         #         {
#         #             "blocks": [...]
#         #         }
#         #     ]
#         # }
#         # ========================================================

#         for source_name, pages in data.items():

#             if not isinstance(
#                 pages,
#                 list,
#             ):
#                 continue

#             for page_data in pages:

#                 if not isinstance(
#                     page_data,
#                     dict,
#                 ):
#                     continue

#                 # ------------------------------------------------
#                 # Page number
#                 # ------------------------------------------------

#                 page_number = page_data.get(
#                     "page",
#                     page_data.get(
#                         "page_number",
#                         1,
#                     ),
#                 )

#                 # ------------------------------------------------
#                 # Image dimensions
#                 # ------------------------------------------------

#                 image_bbox = page_data.get(
#                     "image_bbox",
#                     [],
#                 )

#                 # ------------------------------------------------
#                 # Blocks
#                 # ------------------------------------------------

#                 blocks = page_data.get(
#                     "blocks",
#                     [],
#                 )

#                 if not isinstance(
#                     blocks,
#                     list,
#                 ):
#                     continue

#                 # =================================================
#                 # Process each block
#                 # =================================================

#                 for block in blocks:

#                     if not isinstance(
#                         block,
#                         dict,
#                     ):
#                         continue

#                     # ------------------------------------------------
#                     # Get HTML
#                     # ------------------------------------------------

#                     html = block.get(
#                         "html",
#                         "",
#                     )

#                     # ------------------------------------------------
#                     # Convert HTML → text
#                     # ------------------------------------------------

#                     text = self.clean_html(
#                         html
#                     )

#                     # ------------------------------------------------
#                     # Ignore empty blocks
#                     # ------------------------------------------------

#                     if not text:
#                         continue

#                     # ------------------------------------------------
#                     # Confidence
#                     # ------------------------------------------------

#                     confidence = block.get(
#                         "confidence",
#                         0.0,
#                     )

#                     try:

#                         confidence = float(
#                             confidence
#                         )

#                     except (
#                         TypeError,
#                         ValueError,
#                     ):

#                         confidence = 0.0

#                     # ------------------------------------------------
#                     # Bounding box
#                     # ------------------------------------------------

#                     bbox = block.get(
#                         "bbox",
#                         block.get(
#                             "polygon",
#                             [],
#                         ),
#                     )

#                     # ------------------------------------------------
#                     # Layout label
#                     # ------------------------------------------------

#                     label = block.get(
#                         "label",
#                         "",
#                     )

#                     raw_label = block.get(
#                         "raw_label",
#                         label,
#                     )

#                     # ------------------------------------------------
#                     # Reading order
#                     # ------------------------------------------------

#                     reading_order = block.get(
#                         "reading_order",
#                         0,
#                     )

#                     # ------------------------------------------------
#                     # Language
#                     # ------------------------------------------------

#                     language = self.classify_language(
#                         text
#                     )

#                     # ------------------------------------------------
#                     # Save normalized block
#                     # ------------------------------------------------

#                     results.append(
#                         {
#                             "text": text,
#                             "language": language,
#                             "confidence": confidence,
#                             "bbox": bbox,
#                             "label": label,
#                             "raw_label": raw_label,
#                             "reading_order": reading_order,
#                             "page": page_number,
#                             "page_number": page_number,
#                             "image_bbox": image_bbox,
#                             "source": source_name,
#                         }
#                     )

#         # ========================================================
#         # Sort OCR blocks
#         # ========================================================

#         results.sort(
#             key=lambda item: (
#                 item.get(
#                     "page",
#                     0,
#                 ),
#                 item.get(
#                     "reading_order",
#                     0,
#                 ),
#             )
#         )

#         # ========================================================
#         # Detect all languages
#         # ========================================================

#         detected_languages = set()

#         for item in results:

#             language = item.get(
#                 "language",
#                 "unknown",
#             )

#             if language == "eng":

#                 detected_languages.add(
#                     "eng"
#                 )

#             elif language == "hin":

#                 detected_languages.add(
#                     "hin"
#                 )

#             elif language == "guj":

#                 detected_languages.add(
#                     "guj"
#                 )

#             elif language == "mixed":

#                 text = item.get(
#                     "text",
#                     "",
#                 )

#                 detected_languages.update(
#                     self.detect_languages_from_text(
#                         text
#                     )
#                 )

#         # ========================================================
#         # Final normalized OCR result
#         # ========================================================

#         result = {
#             "results": results,
#             "total_blocks": len(results),
#             "detected_languages": sorted(
#                 detected_languages
#             ),
#             "multilingual": (
#                 len(detected_languages) > 1
#             ),
#             "source_json": str(
#                 json_file
#             ),
#         }

#         print()
#         print(
#             f"OCR blocks extracted: "
#             f"{len(results)}"
#         )

#         if detected_languages:

#             print(
#                 "Detected languages: "
#                 + ", ".join(
#                     sorted(
#                         detected_languages
#                     )
#                 )
#             )

#         else:

#             print(
#                 "Detected languages: None"
#             )

#         return result

#     # ============================================================
#     # SAVE NORMALIZED RESULT TO DISK
#     # ============================================================

#     def save_result_json(self, result, run_dir, image_path):
#         """
#         Write the normalized OCR result to a clean,
#         stable JSON file of our own.
#         """

#         out_path = (
#             Path(run_dir)
#             / f"{Path(image_path).stem}_ocr.json"
#         )

#         with open(
#             out_path,
#             "w",
#             encoding="utf-8",
#         ) as file:

#             json.dump(
#                 result,
#                 file,
#                 ensure_ascii=False,
#                 indent=2,
#             )

#         print()
#         print(
#             f"Saved normalized OCR JSON: {out_path}"
#         )

#         return out_path

#     # ============================================================
#     # CREATE UNIQUE RUN DIRECTORY
#     # ============================================================

#     def create_run_directory(
#         self,
#         base_output_dir,
#     ):
#         """
#         Create a completely unique directory for each OCR run.
#         """

#         timestamp = time.strftime(
#             "%Y%m%d_%H%M%S"
#         )

#         unique_id = uuid.uuid4().hex[:8]

#         run_dir = (
#             Path(base_output_dir)
#             / f"run_{timestamp}_{unique_id}"
#         )

#         run_dir.mkdir(
#             parents=True,
#             exist_ok=True,
#         )

#         return run_dir

#     # ============================================================
#     # MAIN OCR FUNCTION
#     # ============================================================

#     def run_ocr(
#         self,
#         image_path,
#         output_dir=None,
#         timeout=300,
#         save_json=True,
#     ):
#         """
#         Run Surya OCR using the persistent llama-server.

#         IMPORTANT:

#         The --keep_server flag means Surya keeps its
#         llama-server alive after this OCR call.

#         Therefore subsequent calls from:

#             Level 1
#             Level 2 Enhanced
#             Level 2 Threshold

#         can reuse the same model/server.

#         There is intentionally NO cleanup here.

#         The server lifecycle is handled by Surya's
#         --keep_server mechanism.
#         """

#         # ========================================================
#         # Validate image
#         # ========================================================

#         image_path = Path(
#             image_path
#         ).resolve()

#         if not image_path.exists():

#             raise FileNotFoundError(
#                 f"Image not found: "
#                 f"{image_path}"
#             )

#         # ========================================================
#         # Base output directory
#         # ========================================================

#         if output_dir is not None:

#             base_output_dir = Path(
#                 output_dir
#             ).resolve()

#         else:

#             base_output_dir = (
#                 self.output_dir.resolve()
#             )

#         base_output_dir.mkdir(
#             parents=True,
#             exist_ok=True,
#         )

#         # ========================================================
#         # Unique run directory
#         # ========================================================

#         run_dir = self.create_run_directory(
#             base_output_dir
#         )

#         # ========================================================
#         # Expected JSON location
#         #
#         # Surya creates:
#         #
#         # run_xxxxx/
#         #     page_002/
#         #         results.json
#         # ========================================================

#         expected_json = (
#             run_dir
#             / image_path.stem
#             / "results.json"
#         )

#         # ========================================================
#         # Display
#         # ========================================================

#         print()
#         print("=" * 40)
#         print("             SURYA OCR")
#         print("=" * 40)

#         print(
#             f"Image : {image_path}"
#         )

#         print(
#             f"Output: {run_dir}"
#         )

#         # ========================================================
#         # Command
#         # ========================================================

#         command = [
#             "surya_ocr",
#             str(image_path),
#             "--images",
#             "--output_dir",
#             str(run_dir),

#             # ----------------------------------------------------
#             # CRITICAL PERFORMANCE OPTION
#             #
#             # Keep llama-server alive after OCR.
#             # ----------------------------------------------------

#             "--keep_server",
#         ]

#         print()
#         print(
#             "Running Surya..."
#         )

#         print(
#             " ".join(command)
#         )

#         print()
#         print(
#             "Persistent Surya server: ENABLED"
#         )

#         print(
#             "The existing llama-server will be reused "
#             "by subsequent OCR calls."
#         )

#         # ========================================================
#         # Environment
#         # ========================================================

#         process_env = os.environ.copy()

#         # --------------------------------------------------------
#         # Force llama.cpp
#         # --------------------------------------------------------

#         process_env[
#             "SURYA_INFERENCE_BACKEND"
#         ] = "llamacpp"

#         # --------------------------------------------------------
#         # Keep server alive
#         # --------------------------------------------------------

#         process_env[
#             "SURYA_INFERENCE_KEEP_ALIVE"
#         ] = "1"

#         # --------------------------------------------------------
#         # llama-server
#         # --------------------------------------------------------

#         if self.llama_binary.exists():

#             process_env[
#                 "LLAMA_CPP_BINARY"
#             ] = str(
#                 self.llama_binary
#             )

#         # ========================================================
#         # START SURYA
#         # ========================================================

#         popen_kwargs = {}

#         if sys.platform == "win32":

#             popen_kwargs["creationflags"] = (
#                 subprocess.CREATE_NEW_PROCESS_GROUP
#             )

#         try:

#             process = subprocess.Popen(
#                 command,
#                 stdout=None,
#                 stderr=None,
#                 env=process_env,
#                 **popen_kwargs,
#             )

#         except FileNotFoundError as exc:

#             raise RuntimeError(
#                 "Could not start 'surya_ocr'. "
#                 "Make sure Surya is installed "
#                 "inside the active virtual environment."
#             ) from exc

#         start_time = time.time()

#         print()
#         print(
#             "Waiting for results.json..."
#         )

#         # ========================================================
#         # SIGINT GUARD
#         # ========================================================

#         old_sigint_handler = signal.getsignal(
#             signal.SIGINT
#         )

#         if (
#             sys.platform == "win32"
#             and threading.current_thread()
#             is threading.main_thread()
#         ):
#             signal.signal(
#                 signal.SIGINT,
#                 signal.SIG_IGN,
#             )

#         try:

#             # ====================================================
#             # WAIT FOR JSON ONLY
#             # ====================================================

#             while True:

#                 # ------------------------------------------------
#                 # 1. Check exact expected JSON
#                 # ------------------------------------------------

#                 if (
#                     expected_json.exists()
#                     and self.is_valid_json(
#                         expected_json
#                     )
#                 ):

#                     print()
#                     print(
#                         "JSON output detected:"
#                     )

#                     print(
#                         expected_json
#                     )

#                     print()
#                     print(
#                         "Valid results.json found."
#                     )

#                     print(
#                         "Reading OCR result..."
#                     )

#                     # --------------------------------------------
#                     # IMPORTANT
#                     #
#                     # Do NOT terminate Surya.
#                     #
#                     # --keep_server keeps llama-server alive.
#                     # --------------------------------------------

#                     result = (
#                         self.extract_text_from_json(
#                             expected_json
#                         )
#                     )

#                     if save_json:

#                         self.save_result_json(
#                             result,
#                             run_dir,
#                             image_path,
#                         )

#                     print()
#                     print(
#                         "OCR JSON successfully processed."
#                     )

#                     print(
#                         "Surya llama-server remains alive "
#                         "for the next OCR call."
#                     )

#                     return result

#                 # ------------------------------------------------
#                 # 2. Fallback recursive search
#                 # ------------------------------------------------

#                 candidate = self.find_json_file(
#                     run_dir
#                 )

#                 if (
#                     candidate is not None
#                     and self.is_valid_json(
#                         candidate
#                     )
#                 ):

#                     print()
#                     print(
#                         "JSON output detected:"
#                     )

#                     print(
#                         candidate
#                     )

#                     print()
#                     print(
#                         "Valid results.json found."
#                     )

#                     print(
#                         "Reading OCR result..."
#                     )

#                     result = (
#                         self.extract_text_from_json(
#                             candidate
#                         )
#                     )

#                     if save_json:

#                         self.save_result_json(
#                             result,
#                             run_dir,
#                             image_path,
#                         )

#                     print()
#                     print(
#                         "OCR JSON successfully processed."
#                     )

#                     print(
#                         "Surya llama-server remains alive "
#                         "for the next OCR call."
#                     )

#                     return result

#                 # ------------------------------------------------
#                 # 3. Timeout
#                 # ------------------------------------------------

#                 elapsed = (
#                     time.time()
#                     - start_time
#                 )

#                 if elapsed > timeout:

#                     raise TimeoutError(
#                         "Surya OCR did not produce "
#                         "a valid results.json within "
#                         f"{timeout} seconds.\n"
#                         f"Output directory: {run_dir}"
#                     )

#                 # ------------------------------------------------
#                 # 4. Check if process exited before JSON
#                 # ------------------------------------------------

#                 return_code = process.poll()

#                 if return_code is not None:

#                     # --------------------------------------------
#                     # One final search.
#                     # --------------------------------------------

#                     candidate = self.find_json_file(
#                         run_dir
#                     )

#                     if (
#                         candidate is not None
#                         and self.is_valid_json(
#                             candidate
#                         )
#                     ):

#                         print()
#                         print(
#                             "JSON output detected after "
#                             "process exit:"
#                         )

#                         print(
#                             candidate
#                         )

#                         result = (
#                             self.extract_text_from_json(
#                                 candidate
#                             )
#                         )

#                         if save_json:

#                             self.save_result_json(
#                                 result,
#                                 run_dir,
#                                 image_path,
#                             )

#                         print()
#                         print(
#                             "Surya llama-server remains alive "
#                             "for the next OCR call."
#                         )

#                         return result

#                     raise RuntimeError(
#                         "Surya OCR process exited "
#                         f"with code {return_code} "
#                         "without producing a valid "
#                         "results.json."
#                     )

#                 # ------------------------------------------------
#                 # Poll again
#                 # ------------------------------------------------

#                 time.sleep(0.25)

#         finally:

#             # ====================================================
#             # IMPORTANT:
#             #
#             # Restore the ORIGINAL SIGINT handler.
#             #
#             # Your previous version restored SIG_IGN here,
#             # which meant Ctrl+C could remain disabled after
#             # Surya returned.
#             # ====================================================

#             if (
#                 sys.platform == "win32"
#                 and threading.current_thread()
#                 is threading.main_thread()
#             ):
#                 signal.signal(
#                     signal.SIGINT,
#                     old_sigint_handler,
#                 )


# # ================================================================
# # DIRECT TEST
# # ================================================================

# if __name__ == "__main__":

#     service = SuryaOCRService()

#     result = service.run_ocr(
#         r"output/rendered/page_002.png"
#     )

#     print()
#     print("=" * 40)
#     print("             FINAL RESULT")
#     print("=" * 40)

#     print()

#     print(
#         f"Total text blocks: "
#         f"{result['total_blocks']}"
#     )

#     print(
#         f"Detected languages: "
#         f"{result['detected_languages']}"
#     )

#     print(
#         f"Multilingual: "
#         f"{result['multilingual']}"
#     )

#     for i, item in enumerate(
#         result["results"],
#         start=1,
#     ):

#         print()
#         print(
#             "-" * 40
#         )

#         print(
#             f"Block {i}"
#         )

#         print(
#             f"Text      : "
#             f"{item['text']}"
#         )

#         print(
#             f"Language  : "
#             f"{item['language']}"
#         )

#         print(
#             f"Confidence: "
#             f"{item['confidence']}"
#         )

#         print(
#             f"BBox      : "
#             f"{item['bbox']}"
#         )

#     print()
#     print("=" * 40)
#     print("          SURYA TEST COMPLETE")
#     print("=" * 40)


























































####final changend


import os
import sys
import json
import signal
import subprocess
import time
import uuid
import re
from pathlib import Path
import threading


class SuryaOCRService:
    """
    Astra-OCR Surya OCR Service

    Pipeline:
        Image
          ↓
        Surya OCR
          ↓
        results.json
          ↓
        Read JSON immediately
          ↓
        Return OCR result

    IMPORTANT:
    Surya is run with --keep_server so that the internal
    llama-server stays alive between OCR calls.

    This allows:

        Level 1
           ↓
        same llama-server
           ↓
        Level 2 Enhanced
           ↓
        same llama-server
           ↓
        Level 2 Threshold
           ↓
        same llama-server
           ↓
        next page
           ↓
        same llama-server

    This avoids repeatedly loading the Surya model.

    WINDOWS NOTE:
    Surya can use CTRL_C_EVENT while managing its internal
    llama-server. SIGINT is temporarily ignored while we
    wait for and read results.json.
    """

    # ============================================================
    # INITIALIZATION
    # ============================================================

    def __init__(
        self,
        output_dir="surya_output",
        llama_cpp_binary=None,
    ):
        # --------------------------------------------------------
        # Force llama.cpp backend
        # --------------------------------------------------------

        os.environ["SURYA_INFERENCE_BACKEND"] = "llamacpp"

        # --------------------------------------------------------
        # IMPORTANT:
        #
        # Keep the inference server alive between Surya calls.
        #
        # This is the environment equivalent of --keep_server.
        # --------------------------------------------------------

        os.environ["SURYA_INFERENCE_KEEP_ALIVE"] = "1"

        # --------------------------------------------------------
        # llama-server location
        # --------------------------------------------------------

        if llama_cpp_binary is None:
            llama_cpp_binary = (
                r"C:\Users\dalwa\AppData\Local\Microsoft\WinGet\Packages"
                r"\ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe"
                r"\llama-server.exe"
            )

        self.llama_binary = Path(
            llama_cpp_binary
        )

        # --------------------------------------------------------
        # Set environment variable for Surya
        # --------------------------------------------------------

        if self.llama_binary.exists():
            os.environ["LLAMA_CPP_BINARY"] = str(
                self.llama_binary
            )

        # --------------------------------------------------------
        # Base output directory
        # --------------------------------------------------------

        self.output_dir = Path(
            output_dir
        )

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # --------------------------------------------------------
        # Startup information
        # --------------------------------------------------------

        print()
        print("=" * 40)
        print("        SURYA OCR SERVICE")
        print("=" * 40)

        print(
            "llama-server binary:"
        )

        print(
            self.llama_binary
        )

        print(
            "Inference backend: llamacpp"
        )

        print(
            "Persistent server: ENABLED"
        )

    # ============================================================
    # LANGUAGE CLASSIFICATION
    # ============================================================

    def classify_language(self, text):
        """
        Detect language/script from OCR text.

        Supported:
            eng = English
            hin = Hindi
            guj = Gujarati
            mixed = Multiple scripts
            unknown = No supported script detected
        """

        if not text:
            return "unknown"

        text = str(text)

        english_count = 0
        hindi_count = 0
        gujarati_count = 0

        for char in text:

            code = ord(char)

            # ----------------------------------------------------
            # Latin / English
            # ----------------------------------------------------

            if (
                "A" <= char <= "Z"
                or "a" <= char <= "z"
            ):
                english_count += 1

            # ----------------------------------------------------
            # Devanagari / Hindi
            # ----------------------------------------------------

            elif 0x0900 <= code <= 0x097F:
                hindi_count += 1

            # ----------------------------------------------------
            # Gujarati
            # ----------------------------------------------------

            elif 0x0A80 <= code <= 0x0AFF:
                gujarati_count += 1

        detected = []

        if english_count > 0:
            detected.append("eng")

        if hindi_count > 0:
            detected.append("hin")

        if gujarati_count > 0:
            detected.append("guj")

        if not detected:
            return "unknown"

        if len(detected) > 1:
            return "mixed"

        return detected[0]

    # ============================================================
    # DETECT ALL LANGUAGES IN TEXT
    # ============================================================

    def detect_languages_from_text(self, text):
        """
        Return all supported scripts found in text.
        """

        detected = set()

        if not text:
            return detected

        for char in str(text):

            code = ord(char)

            # English
            if (
                "A" <= char <= "Z"
                or "a" <= char <= "z"
            ):
                detected.add("eng")

            # Hindi
            elif 0x0900 <= code <= 0x097F:
                detected.add("hin")

            # Gujarati
            elif 0x0A80 <= code <= 0x0AFF:
                detected.add("guj")

        return detected

    # ============================================================
    # HTML CLEANING
    # ============================================================

    def clean_html(self, html):
        """
        Convert Surya HTML output into plain readable text.
        """

        if html is None:
            return ""

        text = str(html)

        # --------------------------------------------------------
        # Remove image tags
        # --------------------------------------------------------

        text = re.sub(
            r"<img[^>]*>",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # --------------------------------------------------------
        # Convert structural tags into line breaks
        # --------------------------------------------------------

        text = re.sub(
            r"</?(?:p|div|h[1-6]|li|tr|br|section|article)[^>]*>",
            "\n",
            text,
            flags=re.IGNORECASE,
        )

        # --------------------------------------------------------
        # Remove remaining HTML
        # --------------------------------------------------------

        text = re.sub(
            r"<[^>]+>",
            "",
            text,
        )

        # --------------------------------------------------------
        # Decode common HTML entities
        # --------------------------------------------------------

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
                new,
            )

        # --------------------------------------------------------
        # Normalize spaces
        # --------------------------------------------------------

        text = re.sub(
            r"[ \t]+",
            " ",
            text,
        )

        # --------------------------------------------------------
        # Normalize excessive newlines
        # --------------------------------------------------------

        text = re.sub(
            r"\n\s*\n\s*\n+",
            "\n\n",
            text,
        )

        return text.strip()

    # ============================================================
    # FIND JSON FILE
    # ============================================================

    def find_json_file(self, output_dir):
        """
        Search recursively for results.json.

        Because every OCR run uses a unique directory,
        this cannot accidentally pick an old run's JSON.
        """

        output_dir = Path(
            output_dir
        )

        if not output_dir.exists():
            return None

        json_files = list(
            output_dir.rglob(
                "results.json"
            )
        )

        if not json_files:
            return None

        # Newest first
        json_files.sort(
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

        return json_files[0]

    # ============================================================
    # VALIDATE JSON
    # ============================================================

    def is_valid_json(self, json_file):
        """
        Check whether results.json exists,
        is non-empty, and contains valid JSON.
        """

        if json_file is None:
            return False

        json_file = Path(
            json_file
        )

        if not json_file.exists():
            return False

        try:

            if json_file.stat().st_size == 0:
                return False

        except OSError:
            return False

        try:

            with open(
                json_file,
                "r",
                encoding="utf-8",
            ) as file:

                data = json.load(file)

            return isinstance(
                data,
                dict,
            )

        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
            OSError,
        ):
            return False

    # ============================================================
    # PAGE SORTING
    # ============================================================

    def page_sort_key(self, item):
        """
        Natural page sorting.
        """

        try:

            return int(
                item.get(
                    "page",
                    item.get(
                        "page_number",
                        0,
                    ),
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            return 0

    # ============================================================
    # EXTRACT OCR RESULT
    # ============================================================

    def extract_text_from_json(self, json_file):
        """
        Read Surya results.json and convert it into
        Astra-OCR normalized format.
        """

        json_file = Path(
            json_file
        )

        print()
        print(
            "Reading OCR JSON:"
        )
        print(
            json_file
        )

        # --------------------------------------------------------
        # IMPORTANT:
        # Explicit UTF-8 reading.
        # --------------------------------------------------------

        with open(
            json_file,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        results = []

        # ========================================================
        # Expected Surya structure:
        #
        # {
        #     "page_002": [
        #         {
        #             "blocks": [...]
        #         }
        #     ]
        # }
        # ========================================================

        for source_name, pages in data.items():

            if not isinstance(
                pages,
                list,
            ):
                continue

            for page_data in pages:

                if not isinstance(
                    page_data,
                    dict,
                ):
                    continue

                # ------------------------------------------------
                # Page number
                # ------------------------------------------------

                page_number = page_data.get(
                    "page",
                    page_data.get(
                        "page_number",
                        1,
                    ),
                )

                # ------------------------------------------------
                # Image dimensions
                # ------------------------------------------------

                image_bbox = page_data.get(
                    "image_bbox",
                    [],
                )

                # ------------------------------------------------
                # Blocks
                # ------------------------------------------------

                blocks = page_data.get(
                    "blocks",
                    [],
                )

                if not isinstance(
                    blocks,
                    list,
                ):
                    continue

                # =================================================
                # Process each block
                # =================================================

                for block in blocks:

                    if not isinstance(
                        block,
                        dict,
                    ):
                        continue

                    # ------------------------------------------------
                    # Get HTML
                    # ------------------------------------------------

                    html = block.get(
                        "html",
                        "",
                    )

                    # ------------------------------------------------
                    # Convert HTML → text
                    # ------------------------------------------------

                    text = self.clean_html(
                        html
                    )

                    # ------------------------------------------------
                    # Ignore empty blocks
                    # ------------------------------------------------

                    if not text:
                        continue

                    # ------------------------------------------------
                    # Confidence
                    # ------------------------------------------------

                    confidence = block.get(
                        "confidence",
                        0.0,
                    )

                    try:

                        confidence = float(
                            confidence
                        )

                    except (
                        TypeError,
                        ValueError,
                    ):

                        confidence = 0.0

                    # ------------------------------------------------
                    # Bounding box
                    # ------------------------------------------------

                    bbox = block.get(
                        "bbox",
                        block.get(
                            "polygon",
                            [],
                        ),
                    )

                    # ------------------------------------------------
                    # Layout label
                    # ------------------------------------------------

                    label = block.get(
                        "label",
                        "",
                    )

                    raw_label = block.get(
                        "raw_label",
                        label,
                    )

                    # ------------------------------------------------
                    # Reading order
                    # ------------------------------------------------

                    reading_order = block.get(
                        "reading_order",
                        0,
                    )

                    # ------------------------------------------------
                    # Language
                    # ------------------------------------------------

                    language = self.classify_language(
                        text
                    )

                    # ------------------------------------------------
                    # Save normalized block
                    # ------------------------------------------------

                    results.append(
                        {
                            "text": text,
                            "language": language,
                            "confidence": confidence,
                            "bbox": bbox,
                            "label": label,
                            "raw_label": raw_label,
                            "reading_order": reading_order,
                            "page": page_number,
                            "page_number": page_number,
                            "image_bbox": image_bbox,
                            "source": source_name,
                        }
                    )

        # ========================================================
        # Sort OCR blocks
        # ========================================================

        results.sort(
            key=lambda item: (
                item.get(
                    "page",
                    0,
                ),
                item.get(
                    "reading_order",
                    0,
                ),
            )
        )

        # ========================================================
        # Detect all languages
        # ========================================================

        detected_languages = set()

        for item in results:

            language = item.get(
                "language",
                "unknown",
            )

            if language == "eng":

                detected_languages.add(
                    "eng"
                )

            elif language == "hin":

                detected_languages.add(
                    "hin"
                )

            elif language == "guj":

                detected_languages.add(
                    "guj"
                )

            elif language == "mixed":

                text = item.get(
                    "text",
                    "",
                )

                detected_languages.update(
                    self.detect_languages_from_text(
                        text
                    )
                )

        # ========================================================
        # Final normalized OCR result
        # ========================================================

        result = {
            "results": results,
            "total_blocks": len(results),
            "detected_languages": sorted(
                detected_languages
            ),
            "multilingual": (
                len(detected_languages) > 1
            ),
            "source_json": str(
                json_file
            ),
        }

        print()
        print(
            f"OCR blocks extracted: "
            f"{len(results)}"
        )

        if detected_languages:

            print(
                "Detected languages: "
                + ", ".join(
                    sorted(
                        detected_languages
                    )
                )
            )

        else:

            print(
                "Detected languages: None"
            )

        return result

    # ============================================================
    # SAVE NORMALIZED RESULT TO DISK
    # ============================================================

    def save_result_json(self, result, run_dir, image_path):
        """
        Write the normalized OCR result to a clean,
        stable JSON file of our own.
        """

        out_path = (
            Path(run_dir)
            / f"{Path(image_path).stem}_ocr.json"
        )

        with open(
            out_path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                result,
                file,
                ensure_ascii=False,
                indent=2,
            )

        print()
        print(
            f"Saved normalized OCR JSON: {out_path}"
        )

        return out_path

    # ============================================================
    # CREATE UNIQUE RUN DIRECTORY
    # ============================================================

    def create_run_directory(
        self,
        base_output_dir,
    ):
        """
        Create a completely unique directory for each OCR run.
        """

        timestamp = time.strftime(
            "%Y%m%d_%H%M%S"
        )

        unique_id = uuid.uuid4().hex[:8]

        run_dir = (
            Path(base_output_dir)
            / f"run_{timestamp}_{unique_id}"
        )

        run_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        return run_dir

    # ============================================================
    # MAIN OCR FUNCTION
    # ============================================================

    def run_ocr(
        self,
        image_path,
        output_dir=None,
        timeout=300,
        save_json=True,
    ):
        """
        Run Surya OCR using the persistent llama-server.

        IMPORTANT:

        The --keep_server flag means Surya keeps its
        llama-server alive after this OCR call.

        Therefore subsequent calls from:

            Level 1
            Level 2 Enhanced
            Level 2 Threshold

        can reuse the same model/server.

        There is intentionally NO cleanup here.

        The server lifecycle is handled by Surya's
        --keep_server mechanism.
        """

        # ========================================================
        # Validate image
        # ========================================================

        image_path = Path(
            image_path
        ).resolve()

        if not image_path.exists():

            raise FileNotFoundError(
                f"Image not found: "
                f"{image_path}"
            )

        # ========================================================
        # Base output directory
        # ========================================================

        if output_dir is not None:

            base_output_dir = Path(
                output_dir
            ).resolve()

        else:

            base_output_dir = (
                self.output_dir.resolve()
            )

        base_output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ========================================================
        # Unique run directory
        # ========================================================

        run_dir = self.create_run_directory(
            base_output_dir
        )

        # ========================================================
        # Expected JSON location
        #
        # Surya creates:
        #
        # run_xxxxx/
        #     page_002/
        #         results.json
        # ========================================================

        expected_json = (
            run_dir
            / image_path.stem
            / "results.json"
        )

        # ========================================================
        # Display
        # ========================================================

        print()
        print("=" * 40)
        print("             SURYA OCR")
        print("=" * 40)

        print(
            f"Image : {image_path}"
        )

        print(
            f"Output: {run_dir}"
        )

        # ========================================================
        # Command
        # ========================================================

        command = [
            "surya_ocr",
            str(image_path),
            "--images",
            "--output_dir",
            str(run_dir),

            # ----------------------------------------------------
            # CRITICAL PERFORMANCE OPTION
            #
            # Keep llama-server alive after OCR.
            # ----------------------------------------------------

            "--keep_server",
        ]

        print()
        print(
            "Running Surya..."
        )

        print(
            " ".join(command)
        )

        print()
        print(
            "Persistent Surya server: ENABLED"
        )

        print(
            "The existing llama-server will be reused "
            "by subsequent OCR calls."
        )

        # ========================================================
        # Environment
        # ========================================================

        process_env = os.environ.copy()

        # --------------------------------------------------------
        # Force llama.cpp
        # --------------------------------------------------------

        process_env[
            "SURYA_INFERENCE_BACKEND"
        ] = "llamacpp"

        # --------------------------------------------------------
        # Keep server alive
        # --------------------------------------------------------

        process_env[
            "SURYA_INFERENCE_KEEP_ALIVE"
        ] = "1"

        # --------------------------------------------------------
        # llama-server
        # --------------------------------------------------------

        if self.llama_binary.exists():

            process_env[
                "LLAMA_CPP_BINARY"
            ] = str(
                self.llama_binary
            )

        # ========================================================
        # START SURYA
        # ========================================================

        popen_kwargs = {}

        if sys.platform == "win32":

            popen_kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP
            )

        try:

            process = subprocess.Popen(
                command,
                stdout=None,
                stderr=None,
                env=process_env,
                **popen_kwargs,
            )

        except FileNotFoundError as exc:

            raise RuntimeError(
                "Could not start 'surya_ocr'. "
                "Make sure Surya is installed "
                "inside the active virtual environment."
            ) from exc

        start_time = time.time()

        print()
        print(
            "Waiting for results.json..."
        )

        # ========================================================
        # SIGINT GUARD
        # ========================================================

        old_sigint_handler = signal.getsignal(
            signal.SIGINT
        )

        if (
            sys.platform == "win32"
            and threading.current_thread()
            is threading.main_thread()
        ):
            signal.signal(
                signal.SIGINT,
                signal.SIG_IGN,
            )

        try:

            # ====================================================
            # WAIT FOR JSON ONLY
            # ====================================================

            while True:

                # ------------------------------------------------
                # 1. Check exact expected JSON
                # ------------------------------------------------

                if (
                    expected_json.exists()
                    and self.is_valid_json(
                        expected_json
                    )
                ):

                    print()
                    print(
                        "JSON output detected:"
                    )

                    print(
                        expected_json
                    )

                    print()
                    print(
                        "Valid results.json found."
                    )

                    print(
                        "Reading OCR result..."
                    )

                    # --------------------------------------------
                    # IMPORTANT
                    #
                    # Do NOT terminate Surya.
                    #
                    # --keep_server keeps llama-server alive.
                    # --------------------------------------------

                    result = (
                        self.extract_text_from_json(
                            expected_json
                        )
                    )

                    if save_json:

                        self.save_result_json(
                            result,
                            run_dir,
                            image_path,
                        )

                    print()
                    print(
                        "OCR JSON successfully processed."
                    )

                    print(
                        "Surya llama-server remains alive "
                        "for the next OCR call."
                    )

                    return result

                # ------------------------------------------------
                # 2. Fallback recursive search
                # ------------------------------------------------

                candidate = self.find_json_file(
                    run_dir
                )

                if (
                    candidate is not None
                    and self.is_valid_json(
                        candidate
                    )
                ):

                    print()
                    print(
                        "JSON output detected:"
                    )

                    print(
                        candidate
                    )

                    print()
                    print(
                        "Valid results.json found."
                    )

                    print(
                        "Reading OCR result..."
                    )

                    result = (
                        self.extract_text_from_json(
                            candidate
                        )
                    )

                    if save_json:

                        self.save_result_json(
                            result,
                            run_dir,
                            image_path,
                        )

                    print()
                    print(
                        "OCR JSON successfully processed."
                    )

                    print(
                        "Surya llama-server remains alive "
                        "for the next OCR call."
                    )

                    return result

                # ------------------------------------------------
                # 3. Timeout
                # ------------------------------------------------

                elapsed = (
                    time.time()
                    - start_time
                )

                if elapsed > timeout:

                    raise TimeoutError(
                        "Surya OCR did not produce "
                        "a valid results.json within "
                        f"{timeout} seconds.\n"
                        f"Output directory: {run_dir}"
                    )

                # ------------------------------------------------
                # 4. Check if process exited before JSON
                # ------------------------------------------------

                return_code = process.poll()

                if return_code is not None:

                    # --------------------------------------------
                    # One final search.
                    # --------------------------------------------

                    candidate = self.find_json_file(
                        run_dir
                    )

                    if (
                        candidate is not None
                        and self.is_valid_json(
                            candidate
                        )
                    ):

                        print()
                        print(
                            "JSON output detected after "
                            "process exit:"
                        )

                        print(
                            candidate
                        )

                        result = (
                            self.extract_text_from_json(
                                candidate
                            )
                        )

                        if save_json:

                            self.save_result_json(
                                result,
                                run_dir,
                                image_path,
                            )

                        print()
                        print(
                            "Surya llama-server remains alive "
                            "for the next OCR call."
                        )

                        return result

                    raise RuntimeError(
                        "Surya OCR process exited "
                        f"with code {return_code} "
                        "without producing a valid "
                        "results.json."
                    )

                # ------------------------------------------------
                # Poll again
                # ------------------------------------------------

                time.sleep(0.25)

        finally:

            # ====================================================
            # IMPORTANT:
            #
            # Restore the ORIGINAL SIGINT handler.
            #
            # Your previous version restored SIG_IGN here,
            # which meant Ctrl+C could remain disabled after
            # Surya returned.
            # ====================================================

            if (
                sys.platform == "win32"
                and threading.current_thread()
                is threading.main_thread()
            ):
                signal.signal(
                    signal.SIGINT,
                    old_sigint_handler,
                )


# ================================================================
# DIRECT TEST
# ================================================================

if __name__ == "__main__":

    service = SuryaOCRService()

    result = service.run_ocr(
        r"output/rendered/page_002.png"
    )

    print()
    print("=" * 40)
    print("             FINAL RESULT")
    print("=" * 40)

    print()

    print(
        f"Total text blocks: "
        f"{result['total_blocks']}"
    )

    print(
        f"Detected languages: "
        f"{result['detected_languages']}"
    )

    print(
        f"Multilingual: "
        f"{result['multilingual']}"
    )

    for i, item in enumerate(
        result["results"],
        start=1,
    ):

        print()
        print(
            "-" * 40
        )

        print(
            f"Block {i}"
        )

        print(
            f"Text      : "
            f"{item['text']}"
        )

        print(
            f"Language  : "
            f"{item['language']}"
        )

        print(
            f"Confidence: "
            f"{item['confidence']}"
        )

        print(
            f"BBox      : "
            f"{item['bbox']}"
        )

    print()
    print("=" * 40)
    print("          SURYA TEST COMPLETE")
    print("=" * 40)