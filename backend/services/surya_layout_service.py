import json
import re
from pathlib import Path

from services.language_service import LanguageService


class SuryaLayoutService:

    def __init__(self):
        self.language_service = LanguageService()

    # ---------------------------------------------------------
    # LOAD JSON
    # ---------------------------------------------------------
    def load_json(self, json_path):
        json_path = Path(json_path)

        if not json_path.exists():
            raise FileNotFoundError(
                f"Surya JSON not found: {json_path}"
            )

        with open(
            json_path,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    # ---------------------------------------------------------
    # NORMALIZE BLOCK LABEL
    # ---------------------------------------------------------
    def normalize_label(self, label):

        if not label:
            return "unknown"

        label = str(label).lower().strip()

        mapping = {
            "text": "text",

            "sectionheader": "section_header",
            "section-header": "section_header",
            "section_header": "section_header",

            "title": "title",

            "caption": "caption",

            "list": "list",

            "table": "table",

            "picture": "image",
            "image": "image",

            "formula": "formula",

            "header": "header",
            "footer": "footer",

            "pageheader": "page_header",
            "page-header": "page_header",
            "page_header": "page_header",

            "pagefooter": "page_footer",
            "page-footer": "page_footer",
            "page_footer": "page_footer",
        }

        return mapping.get(
            label,
            label
        )

    # ---------------------------------------------------------
    # CLEAN HTML → TEXT
    # ---------------------------------------------------------
    def clean_html(self, html):

        if not html:
            return ""

        text = str(html)

        # <br> → newline
        text = re.sub(
            r"<br\s*/?>",
            "\n",
            text,
            flags=re.IGNORECASE
        )

        # paragraph endings
        text = re.sub(
            r"</p\s*>",
            "\n",
            text,
            flags=re.IGNORECASE
        )

        # Remove remaining HTML tags
        text = re.sub(
            r"<[^>]+>",
            "",
            text
        )

        # HTML entities
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&nbsp;", " ")

        # Normalize spaces
        text = re.sub(
            r"[ \t]+",
            " ",
            text
        )

        # Normalize excessive blank lines
        text = re.sub(
            r"\n\s*\n+",
            "\n",
            text
        )

        return text.strip()

    # ---------------------------------------------------------
    # DETECT LANGUAGE
    # ---------------------------------------------------------
    def detect_block_language(self, text):

        if not text:
            return {
                "language": "unknown",
                "script": "unknown",
                "language_confidence": 0.0,
                "languages": []
            }

        primary = self.language_service.detect_script(
            text
        )

        mixed = self.language_service.detect_mixed_languages(
            text
        )

        return {
            "language": primary.get(
                "language",
                "unknown"
            ),
            "script": primary.get(
                "script",
                "unknown"
            ),
            "language_confidence": primary.get(
                "confidence",
                0.0
            ),
            "languages": mixed
        }

    # ---------------------------------------------------------
    # EXTRACT BLOCKS FROM ONE RAW SURYA PAGE
    # ---------------------------------------------------------
    def extract_blocks(self, page_data):

        blocks = page_data.get(
            "blocks",
            []
        )

        normalized_blocks = []

        for index, block in enumerate(
            blocks,
            start=1
        ):

            if not isinstance(
                block,
                dict
            ):
                continue

            # Skip images / explicitly skipped blocks
            if block.get(
                "skipped",
                False
            ):
                continue

            raw_html = block.get(
                "html",
                ""
            )

            label = self.normalize_label(
                block.get("label")
            )

            text = self.clean_html(
                raw_html
            )

            # Don't create empty text blocks
            if not text and label != "table":
                continue

            language_info = self.detect_block_language(
                text
            )

            normalized_block = {
                "id": index,

                "type": label,

                "raw_label": block.get(
                    "raw_label"
                ),

                "text": text,

                "reading_order": block.get(
                    "reading_order"
                ),

                "bbox": block.get(
                    "bbox"
                ),

                "polygon": block.get(
                    "polygon"
                ),

                # This is Surya layout confidence,
                # NOT OCR recognition confidence.
                "layout_confidence": block.get(
                    "confidence"
                ),

                "language": language_info[
                    "language"
                ],

                "script": language_info[
                    "script"
                ],

                "language_confidence": language_info[
                    "language_confidence"
                ],

                "languages": language_info[
                    "languages"
                ]
            }

            # Preserve original HTML.
            # This is especially important for tables.
            if raw_html:
                normalized_block["html"] = raw_html

            normalized_blocks.append(
                normalized_block
            )

        # -----------------------------------------------------
        # READING ORDER
        # -----------------------------------------------------
        normalized_blocks.sort(
            key=lambda block: (
                block["reading_order"]
                if block["reading_order"] is not None
                else 999999
            )
        )

        return normalized_blocks

    # ---------------------------------------------------------
    # EXTRACT PAGES FROM RAW SURYA JSON
    # ---------------------------------------------------------
    def process(self, json_path):

        data = self.load_json(
            json_path
        )

        pages = []

        # -----------------------------------------------------
        # RAW SURYA FORMAT
        #
        # {
        #   "page_005_original": [
        #       {
        #           "blocks": [...],
        #           ...
        #       }
        #   ]
        # }
        # -----------------------------------------------------
        if isinstance(data, dict):

            for page_name, page_items in data.items():

                if not isinstance(
                    page_items,
                    list
                ):
                    continue

                for page_index, page_data in enumerate(
                    page_items,
                    start=1
                ):

                    if not isinstance(
                        page_data,
                        dict
                    ):
                        continue

                    # Try to get page number from:
                    # 1. explicit page field
                    # 2. filename/key
                    # 3. fallback
                    page_number = page_data.get(
                        "page"
                    )

                    if page_number is None:

                        match = re.search(
                            r"page[_-]?(\d+)",
                            str(page_name),
                            flags=re.IGNORECASE
                        )

                        if match:
                            page_number = int(
                                match.group(1)
                            )

                    if page_number is None:
                        page_number = page_index

                    blocks = self.extract_blocks(
                        page_data
                    )

                    pages.append({
                        "page": page_number,

                        "source": page_name,

                        "image_bbox": page_data.get(
                            "image_bbox"
                        ),

                        "total_blocks": len(
                            blocks
                        ),

                        "blocks": blocks
                    })

        # -----------------------------------------------------
        # LIST FORMAT
        # -----------------------------------------------------
        elif isinstance(data, list):

            for page_index, page_data in enumerate(
                data,
                start=1
            ):

                if not isinstance(
                    page_data,
                    dict
                ):
                    continue

                page_number = page_data.get(
                    "page",
                    page_index
                )

                blocks = self.extract_blocks(
                    page_data
                )

                pages.append({
                    "page": page_number,

                    "source": None,

                    "image_bbox": page_data.get(
                        "image_bbox"
                    ),

                    "total_blocks": len(
                        blocks
                    ),

                    "blocks": blocks
                })

        else:

            raise ValueError(
                "Unsupported Surya JSON format."
            )

        # -----------------------------------------------------
        # SORT PAGES
        # -----------------------------------------------------
        pages.sort(
            key=lambda page: page["page"]
        )

        return {
            "total_pages": len(
                pages
            ),
            "pages": pages
        }

    # ---------------------------------------------------------
    # SAVE RESULT
    # ---------------------------------------------------------
    def save_result(
        self,
        result,
        output_path="output/structured/surya_layout.json"
    ):

        output_path = Path(
            output_path
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            output_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                result,
                file,
                ensure_ascii=False,
                indent=2
            )

        print(
            f"Structured output saved to: "
            f"{output_path}"
        )

        return str(
            output_path
        )