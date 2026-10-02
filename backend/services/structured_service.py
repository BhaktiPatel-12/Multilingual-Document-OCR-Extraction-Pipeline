import json
import re
from pathlib import Path
from difflib import SequenceMatcher


class AstraStructuredService:
    """
    ASTRA STRUCTURED OUTPUT ENGINE

    Consumes normalized Surya/Astra OCR JSON.

    Main responsibilities:
        1. Extract known fields
        2. Extract conservative generic key:value pairs
        3. Preserve tables
        4. Preserve unstructured text
        5. Support multilingual documents
        6. Handle OCR label variations
        7. Avoid extracting labels from normal paragraphs
    """

    # ============================================================
    # FIELD DEFINITIONS
    # ============================================================

    FIELD_DEFINITIONS = {
        "name": {
            "labels": [
                "name of candidate",
                "name of conditate",
                "candidate name",
                "name",
                "नाम",
            ],
            "type": "text",
        },

        "roll_number": {
            "labels": [
                "roll number",
                "roll no",
                "roll no.",
                "roll",
                "अनुक्रमांक",
            ],
            "type": "identifier",
        },

        "registration_number": {
            "labels": [
                "registration number",
                "registration no",
                "registration no.",
                "regn number",
                "regn no",
                "regn no.",
                "regn.no",
                "regn.no.",
                "रजि. नं.\nRegn.No.",
                "रजि नं",
            ],
            "type": "identifier",
        },

        "mother_name": {
            "labels": [
                "mother's name",
                "mother name",
                "mother",
                "माता का नाम",
            ],
            "type": "text",
        },

        "father_guardian_name": {
            "labels": [
                "father's / guardian's name",
                "father's/guardian's name",
                "father / guardian's name",
                "father/guardian's name",
                "father / guardian name",
                "father/guardian name",
                "father's name",
                "father name",
                "guardian's name",
                "guardian name",
                "father",
                "पिता/परिवार का नाम",
            ],
            "type": "text",
        },

        "school": {
            "labels": [
                "school name",
                "school",],
            "type": "text",
        },

        "date_of_birth": {
            "labels": [
                "date of birth",
                "date-of-birth",
                "dob",
                "d.o.b",
                "birth date",
                "जन्म तिथि",
                "जन्म दिनांक",
            ],
            "type": "date",
        },

        "date": {
            "labels": [
                "dated",
                "date",
                "दिनांक",
            ],
            "type": "date",
        },

        "result": {
            "labels": [
                "result",
                "परिणाम",
            ],
            "type": "text",
        },

        "address": {
            "labels": [
                "residential address",
                "permanent address",
                "address",
                "पता",
            ],
            "type": "text",
        },

        "phone": {
            "labels": [
                "phone number",
                "phone",
                "mobile number",
                "mobile",
                "contact number",
                "telephone",
            ],
            "type": "identifier",
        },

        "email": {
            "labels": [
                "email address",
                "email",
                "e-mail address",
                "e-mail",
            ],
            "type": "text",
        },

        "invoice_number": {
            "labels": [
                "invoice number",
                "invoice no",
                "invoice no.",
                "invoice id",
            ],
            "type": "identifier",
        },

        "total": {
            "labels": [
                "grand total",
                "amount total",
                "total amount",
                "total",
                "कुल",
            ],
            "type": "number",
        },

        "amount": {
            "labels": [
                "amount payable",
                "payable amount",
                "amount",
                "कुल राशि",
                "राशि",
            ],
            "type": "number",
        },
    }

    # ============================================================
    # CONSTRUCTOR
    # ============================================================

    def __init__(self):
        self.label_lookup = {}

        for field_name, definition in self.FIELD_DEFINITIONS.items():
            for label in definition["labels"]:
                normalized = self.normalize_label(label)

                if normalized:
                    self.label_lookup[normalized] = field_name

        self.sorted_labels = sorted(
            self.label_lookup.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        )

    # ============================================================
    # TEXT NORMALIZATION
    # ============================================================

    def normalize_text(self, text):
        if text is None:
            return ""

        text = str(text)

        text = text.replace("\r", " ")
        text = text.replace("\n", " ")

        text = text.replace("：", ":")
        text = text.replace("–", "-")
        text = text.replace("—", "-")

        text = re.sub(r"\s+", " ", text)

        return text.strip()

    # ============================================================
    # LABEL NORMALIZATION
    # ============================================================

    def normalize_label(self, text):
        if not text:
            return ""

        text = self.normalize_text(text).lower()

        text = text.replace("’", "'")

        text = re.sub(
            r"[.:;,/\\]+",
            " ",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    # ============================================================
    # LOAD JSON
    # ============================================================

    def load_json(self, input_path):
        input_path = Path(input_path)

        if not input_path.exists():
            raise FileNotFoundError(
                f"Input JSON not found: {input_path}"
            )

        with open(
            input_path,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError(
                "Input JSON must contain an object."
            )

        if "results" not in data:
            raise ValueError(
                "Input JSON does not contain 'results'."
            )

        return data

    # ============================================================
    # SPLIT LINES
    # ============================================================

    def split_lines(self, text):
        if not text:
            return []

        return [
            line.strip()
            for line in str(text).splitlines()
            if line.strip()
        ]

    # ============================================================
    # CLEAN VALUE
    # ============================================================

    def clean_value(self, value):
        if value is None:
            return None

        value = str(value)
        value = value.replace("\r", " ")
        value = value.replace("\n", " ")

    # Collapse whitespace
        value = re.sub(r"\s+", " ", value)
        value = value.strip()

    # Remove separators ONLY from the beginning.
    # Do NOT remove "/" inside identifiers such as A/12110.
        value = re.sub(r"^[\s:;,\-.*]+", "", value)

        return value.strip()

    # ============================================================
    # NORMALIZE OCR APOSTROPHE
    # ============================================================

    def normalize_apostrophes(self, text):
        if not text:
            return ""

        return (
            str(text)
            .replace("’", "'")
            .replace("`", "'")
        )

    # ============================================================
    # LABEL PREFIX MATCH
    # ============================================================

    def match_label_at_start(self, text):
        """
        IMPORTANT:

        Only match a known field label when it is actually
        at the beginning of the OCR block.

        This prevents:

            Scholastic Achievements ...

        from being interpreted as:

            school
        """

        if not text:
            return None

        original = self.normalize_text(text)
        normalized_original = self.normalize_label(original)

        if not normalized_original:
            return None

        for known_label, field_name in self.sorted_labels:

            # ----------------------------------------------------
            # Direct normalized prefix match
            # ----------------------------------------------------

            if normalized_original == known_label:
                return {
                    "field": field_name,
                    "label": known_label,
                    "original_label": original,
                    "remaining": "",
                    "match_type": "exact",
                }

            if normalized_original.startswith(
                known_label + " "
            ):
                remainder = normalized_original[
                    len(known_label):
                ]

                remainder = self.clean_value(
                    remainder
                )

                return {
                    "field": field_name,
                    "label": known_label,
                    "original_label": original[
                        :len(known_label)
                    ].strip(),
                    "remaining": remainder,
                    "match_type": "known_prefix",
                }

            # ----------------------------------------------------
            # Apostrophe/slash tolerant matching
            # ----------------------------------------------------

            original_compact = re.sub(
                r"[^a-z0-9\u0900-\u097f]+",
                "",
                normalized_original,
            )

            known_compact = re.sub(
                r"[^a-z0-9\u0900-\u097f]+",
                "",
                known_label,
            )

            if (
                original_compact.startswith(
                    known_compact
                )
                and len(original_compact) > len(
                    known_compact
                )
            ):
                # Do not blindly calculate character position
                # against the original text because punctuation
                # and spaces may differ.

                remaining = self.remove_label_from_start(
                    original,
                    known_label,
                )

                return {
                    "field": field_name,
                    "label": known_label,
                    "original_label": known_label,
                    "remaining": remaining,
                    "match_type": "normalized_prefix",
                }

        return None

    # ============================================================
    # REMOVE LABEL FROM START
    # ============================================================

    def remove_label_from_start(
        self,
        text,
        known_label,
    ):
        """
        Removes a known label from the beginning while
        tolerating OCR punctuation differences.
        """

        if not text:
            return ""

        text = self.normalize_text(text)

        label_words = re.findall(
            r"[\w\u0900-\u097F]+",
            known_label.lower(),
            flags=re.UNICODE,
        )

        if not label_words:
            return text

        pattern_parts = []

        for word in label_words:
            pattern_parts.append(
                re.escape(word)
            )

        pattern = r"^\s*"

        pattern += r"[\s./,:;'\-]*".join(
            pattern_parts
        )

        pattern += r"[\s./,:;'\-]*"

        match = re.match(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return self.clean_value(
                text[match.end():]
            )

        return text

    # ============================================================
    # FUZZY LABEL MATCH
    # ============================================================

    def fuzzy_label_match(self, text):
        """
        Conservative fuzzy matching.

        IMPORTANT:
        Fuzzy matching is NOT allowed against arbitrary
        paragraph text.

        It is only used when the complete block itself
        looks like a label.
        """

        if not text:
            return None

        normalized = self.normalize_label(text)

        if not normalized:
            return None

        # Too much text = almost certainly not a label.
        if len(normalized.split()) > 6:
            return None

        if len(normalized) > 60:
            return None

        best = None
        best_score = 0.0

        for known_label, field_name in self.sorted_labels:

            score = SequenceMatcher(
                None,
                normalized,
                known_label,
            ).ratio()

            if score > best_score:
                best_score = score
                best = (
                    known_label,
                    field_name,
                )

        if best and best_score >= 0.90:
            return {
                "field": best[1],
                "label": best[0],
                "score": round(
                    best_score,
                    4,
                ),
            }

        return None

    # ============================================================
    # DETECT LABEL
    # ============================================================

    def detect_label(self, text):
        """
        Detect known fields safely.

        Priority:

            1. Exact prefix
            2. OCR punctuation tolerant prefix
            3. Conservative fuzzy matching
        """

        if not text:
            return None

        original_text = self.normalize_text(text)

        if not original_text:
            return None

        # --------------------------------------------------------
        # Never attempt field extraction from tables.
        # --------------------------------------------------------

        # --------------------------------------------------------
        # FIRST: strict prefix matching
        # --------------------------------------------------------

        result = self.match_label_at_start(
            original_text
        )

        if result:
            return result

        # --------------------------------------------------------
        # SECOND: line-by-line prefix matching
        # --------------------------------------------------------

        for line in self.split_lines(
            original_text
        ):
            result = self.match_label_at_start(
                line
            )

            if result:
                return result

        # --------------------------------------------------------
        # THIRD: fuzzy matching ONLY if the whole block
        # itself looks like a label.
        # --------------------------------------------------------

        fuzzy = self.fuzzy_label_match(
            original_text
        )

        if fuzzy:
            return {
                "field": fuzzy["field"],
                "label": fuzzy["label"],
                "original_label": original_text,
                "remaining": "",
                "match_type": "fuzzy_label_only",
            }

        return None

    # ============================================================
    # EXTRACT INLINE VALUE
    # ============================================================

    def extract_inline_value(
        self,
        text,
        label_info,
    ):
        if not label_info:
            return None

        remaining = label_info.get(
            "remaining",
            "",
        )

        if not remaining:
            return None

        remaining = self.clean_value(
            remaining
        )

        # --------------------------------------------------------
        # Remove duplicate label text
        # --------------------------------------------------------

        matched_label = label_info.get(
            "label",
            "",
        )

        if matched_label:
            remaining = self.remove_label_from_start(
                remaining,
                matched_label,
            )

        return self.clean_value(
            remaining
        )

    # ============================================================
    # VALIDATE VALUE
    # ============================================================

    def is_valid_field_value(
        self,
        field_name,
        value,
    ):
        if not value:
            return False

        value = self.clean_value(
            value
        )

        if not value:
            return False

        if field_name == "registration_number":
            value = re.sub(
            r"(?<=\w)\s*/\s*(?=\w)",
            "/",
            value,
            )

        normalized = self.normalize_label(
            value
        )

        # --------------------------------------------------------
        # Never use table/header text as a value.
        # --------------------------------------------------------

        table_words = {
            "total",
            "total in words",
            "marks obtained",
            "subject",
            "code",
            "theory",
            "pr",
            "ia",
        }

        if normalized in table_words:
            return False

        # --------------------------------------------------------
        # Field-specific validation
        # --------------------------------------------------------

        if field_name == "roll_number":
            return bool(
                re.search(
                    r"\d",
                    value,
                )
            )

        if field_name == "registration_number":
            return bool(
                re.search(
                    r"\d",
                    value,
                )
            )

        if field_name == "phone":
            digits = re.sub(
                r"\D",
                "",
                value,
            )

            return 7 <= len(digits) <= 15

        if field_name == "email":
            return bool(
                re.search(
                    r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
                    value,
                )
            )

        if field_name == "date_of_birth":
            return bool(
                re.search(
                    r"\b\d{1,4}[/-]\d{1,2}[/-]\d{1,4}\b",
                    value,
                )
            )

        if field_name == "date":
            return bool(
                re.search(
                    r"\b\d{1,4}[/-]\d{1,2}[/-]\d{1,4}\b",
                    value,
                )
            )

        if field_name in {
            "total",
            "amount",
        }:
            return bool(
                re.search(
                    r"\d",
                    value,
                )
            )

        return True

    # ============================================================
    # EXTRACT DATE
    # ============================================================

    def extract_date_value(self, value):
        if not value:
            return None

        match = re.search(
            r"\b\d{1,4}[/-]\d{1,2}[/-]\d{1,4}\b",
            value,
        )

        if match:
            return match.group(0)

        return None

    # ============================================================
    # CLEAN SPECIAL FIELD VALUES
    # ============================================================

    def clean_field_value(
        self,
        field_name,
        value,
    ):
        value = self.clean_value(
            value
        )

        if not value:
            return None

        # --------------------------------------------------------
        # DATE OF BIRTH
        #
        # Input:
        # 12/06/2006 12TH JUNE TWO THOUSAND SIX
        #
        # Output:
        # 12/06/2006
        # --------------------------------------------------------

        if field_name == "date_of_birth":
            date_value = self.extract_date_value(
                value
            )

            if date_value:
                return date_value

        # --------------------------------------------------------
        # DATE
        # --------------------------------------------------------

        if field_name == "date":
            date_value = self.extract_date_value(
                value
            )

            if date_value:
                return date_value

        # --------------------------------------------------------
        # ROLL NUMBER
        #
        # Input:
        # No. 11120899
        #
        # Output:
        # 11120899
        # --------------------------------------------------------

        if field_name == "roll_number":
            value = re.sub(
                r"^(?:no\.?|number)\s*[:.-]?\s*",
                "",
                value,
                flags=re.IGNORECASE,
            )

            value = self.clean_value(
                value
            )

        # --------------------------------------------------------
        # FATHER/GUARDIAN OCR CLEANUP
        #
        # Handles:
        #
        # Father's / Guardian's Name GAUTAMKUMAR PATEL
        #
        # and OCR variants.
        # --------------------------------------------------------

        if field_name == "father_guardian_name":

            value = re.sub(
                r"^(?:father'?s?\s*/?\s*guardian'?s?\s*name)\s*",
                "",
                value,
                flags=re.IGNORECASE,
            )

            value = re.sub(
                r"^(?:father'?s?\s*/?\s*guardian'?s?)\s*",
                "",
                value,
                flags=re.IGNORECASE,
            )

            value = self.clean_value(
                value
            )

        # --------------------------------------------------------
        # SCHOOL
        # --------------------------------------------------------

        if field_name == "school":

            value = re.sub(
                r"^school\s*",
                "",
                value,
                flags=re.IGNORECASE,
            )

            value = self.clean_value(
                value
            )

        return value

    # ============================================================
    # FIND NEARBY VALUE
    # ============================================================

    def find_nearby_value(
        self,
        blocks,
        current_index,
        label_bbox,
    ):
        """
        Geometry-based fallback.

        This is deliberately conservative.

        We ONLY accept a nearby block if:
            - same page
            - block is immediately below label
            - small vertical distance
            - reasonable horizontal alignment
            - block is not another label
            - block is not a paragraph
        """

        if not label_bbox:
            return None

        if len(label_bbox) < 4:
            return None

        try:
            lx1, ly1, lx2, ly2 = label_bbox[:4]
        except (
            TypeError,
            ValueError,
        ):
            return None

        current_block = blocks[
            current_index
        ]

        current_page = current_block.get(
            "page",
            current_block.get(
                "page_number"
            ),
        )

        label_width = max(
            1,
            lx2 - lx1,
        )

        candidates = []

        for index, block in enumerate(
            blocks
        ):
            if index == current_index:
                continue

            if not isinstance(
                block,
                dict,
            ):
                continue

            block_text = self.clean_value(
                block.get(
                    "text",
                    "",
                )
            )

            if not block_text:
                continue

            # ----------------------------------------------------
            # Never use tables as values.
            # ----------------------------------------------------

            label = str(
                block.get(
                    "label",
                    "",
                )
            ).lower()

            raw_label = str(
                block.get(
                    "raw_label",
                    "",
                )
            ).lower()

            if (
                label == "table"
                or raw_label == "table"
            ):
                continue

            # ----------------------------------------------------
            # Never use a block containing a known label.
            # ----------------------------------------------------

            if self.match_label_at_start(
                block_text
            ):
                continue

            bbox = block.get(
                "bbox",
                [],
            )

            if not bbox or len(bbox) < 4:
                continue

            try:
                x1, y1, x2, y2 = bbox[:4]
            except (
                TypeError,
                ValueError,
            ):
                continue

            block_page = block.get(
                "page",
                block.get(
                    "page_number"
                ),
            )

            if block_page != current_page:
                continue

            vertical_gap = y1 - ly2

            horizontal_overlap = (
                min(lx2, x2)
                - max(lx1, x1)
            )

            horizontal_distance = min(
                abs(x1 - lx2),
                abs(lx1 - x2),
            )

            # ----------------------------------------------------
            # Only close blocks.
            # ----------------------------------------------------

            if not (
                0 <= vertical_gap <= 55
            ):
                continue

            if not (
                horizontal_overlap >= 0
                or horizontal_distance <= label_width
            ):
                continue

            # ----------------------------------------------------
            # Reject long paragraph-like blocks.
            # ----------------------------------------------------

            if len(block_text.split()) > 12:
                continue

            score = 0.0

            score += max(
                0,
                55 - vertical_gap,
            )

            if horizontal_overlap >= 0:
                score += 40

            reading_order = block.get(
                "reading_order"
            )

            current_order = current_block.get(
                "reading_order"
            )

            if (
                reading_order is not None
                and current_order is not None
            ):
                try:
                    order_gap = (
                        int(reading_order)
                        - int(current_order)
                    )

                    if 0 < order_gap <= 2:
                        score += 30

                    elif order_gap > 2:
                        score -= 20

                except (
                    TypeError,
                    ValueError,
                ):
                    pass

            candidates.append(
                (
                    -score,
                    vertical_gap,
                    index,
                    block,
                )
            )

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: (
                item[0],
                item[1],
            )
        )

        return candidates[0][3]

    # ============================================================
    # FIELD CONFIDENCE
    # ============================================================

    def calculate_field_confidence(
        self,
        label_block,
        value_block=None,
    ):
        try:
            label_confidence = float(
                label_block.get(
                    "confidence",
                    0.0,
                )
                or 0.0
            )
        except (
            TypeError,
            ValueError,
        ):
            label_confidence = 0.0

        if value_block:
            try:
                value_confidence = float(
                    value_block.get(
                        "confidence",
                        0.0,
                    )
                    or 0.0
                )
            except (
                TypeError,
                ValueError,
            ):
                value_confidence = 0.0

            return round(
                (
                    label_confidence
                    + value_confidence
                )
                / 2,
                4,
            )

        return round(
            label_confidence,
            4,
        )

    # ============================================================
    # CREATE FIELD
    # ============================================================

    def create_field(
        self,
        field_name,
        label,
        value,
        label_block,
        value_block=None,
    ):
        source_block = (
            value_block
            if value_block
            else label_block
        )

        return {
            "label": label,
            "value": value,
            "confidence": self.calculate_field_confidence(
                label_block,
                value_block,
            ),
            "source": {
                "page": source_block.get(
                    "page",
                    source_block.get(
                        "page_number"
                    ),
                ),
                "bbox": source_block.get(
                    "bbox",
                    [],
                ),
                "reading_order": source_block.get(
                    "reading_order"
                ),
            },
        }

    # ============================================================
    # DOCUMENT TYPE
    # ============================================================

    def detect_document_type(
        self,
        blocks,
    ):
        text = " ".join(
            str(
                block.get(
                    "text",
                    "",
                )
            )
            for block in blocks
            if isinstance(
                block,
                dict,
            )
        ).lower()

        if (
            "marks statement" in text
            or "central board of secondary education"
            in text
            or "अंक विवरणिका" in text
        ):
            return "marks_statement"

        if "invoice" in text:
            return "invoice"

        if (
            "certificate" in text
            or "प्रमाण पत्र" in text
        ):
            return "certificate"

        if (
            "admission" in text
            or "application form" in text
        ):
            return "application_form"

        if (
            "resume" in text
            or "curriculum vitae" in text
        ):
            return "resume"

        return "unknown"

    # ============================================================
    # TABLE EXTRACTION
    # ============================================================

    def extract_tables(
        self,
        blocks,
    ):
        tables = []

        for block in blocks:

            if not isinstance(
                block,
                dict,
            ):
                continue

            label = str(
                block.get(
                    "label",
                    "",
                )
            ).lower()

            raw_label = str(
                block.get(
                    "raw_label",
                    "",
                )
            ).lower()

            if (
                label == "table"
                or raw_label == "table"
            ):
                tables.append(
                    {
                        "type": "detected_table",
                        "page": block.get(
                            "page",
                            block.get(
                                "page_number"
                            ),
                        ),
                        "bbox": block.get(
                            "bbox",
                            [],
                        ),
                        "raw_text": block.get(
                            "text",
                            "",
                        ),
                        "confidence": block.get(
                            "confidence",
                            0.0,
                        ),
                    }
                )

        return tables

    # ============================================================
    # GENERIC KEY VALUE
    # ============================================================

    def make_key(self, text):
        if not text:
            return ""

        text = self.normalize_text(
            text
        )

        text = re.sub(
            r"[^\w\s]",
            " ",
            text,
            flags=re.UNICODE,
        )

        words = text.split()

        if not words:
            return ""

        return "_".join(words)[:100]

    def detect_generic_pair(
        self,
        text,
    ):
        if not text:
            return None

        for line in self.split_lines(text):

            if ":" not in line:
                continue

            left, right = line.split(
                ":",
                1,
            )

            left = left.strip()
            right = self.clean_value(
                right
            )

            if not left or not right:
                continue

            if "://" in line:
                continue

            if re.fullmatch(
                r"\d{1,2}:\d{2}(:\d{2})?",
                line.strip(),
            ):
                continue

            words = left.split()

            if len(words) > 8:
                continue

            if len(left) > 80:
                continue

            # ----------------------------------------------------
            # Don't turn normal sentences into fields.
            # ----------------------------------------------------

            if not re.match(
                r"^[A-Za-z\u0900-\u097F0-9][A-Za-z\u0900-\u097F0-9 _./()'\-]*$",
                left,
            ):
                continue

            key = self.make_key(
                left
            )

            if not key:
                continue

            return {
                "key": key,
                "label": left,
                "value": right,
            }

        return None

    def extract_generic_pairs(
        self,
        blocks,
        already_used_indexes,
    ):
        pairs = []

        for index, block in enumerate(
            blocks
        ):
            if index in already_used_indexes:
                continue

            if not isinstance(
                block,
                dict,
            ):
                continue

            text = block.get(
                "text",
                "",
            )

            if not text:
                continue

            pair = self.detect_generic_pair(
                text
            )

            if not pair:
                continue

            try:
                confidence = float(
                    block.get(
                        "confidence",
                        0.0,
                    )
                    or 0.0
                )
            except (
                TypeError,
                ValueError,
            ):
                confidence = 0.0

            pairs.append(
                {
                    "key": pair["key"],
                    "label": pair["label"],
                    "value": pair["value"],
                    "confidence": round(
                        confidence,
                        4,
                    ),
                    "source": {
                        "page": block.get(
                            "page",
                            block.get(
                                "page_number"
                            ),
                        ),
                        "bbox": block.get(
                            "bbox",
                            [],
                        ),
                        "reading_order": block.get(
                            "reading_order"
                        ),
                    },
                }
            )

        return pairs

    # ============================================================
    # UNSTRUCTURED TEXT
    # ============================================================

    def extract_unstructured_text(
        self,
        blocks,
        used_indexes,
    ):
        paragraphs = []

        for index, block in enumerate(
            blocks
        ):
            if index in used_indexes:
                continue

            if not isinstance(
                block,
                dict,
            ):
                continue

            text = self.clean_value(
                block.get(
                    "text",
                    "",
                )
            )

            if not text:
                continue

            label = str(
                block.get(
                    "label",
                    "",
                )
            ).lower()

            raw_label = str(
                block.get(
                    "raw_label",
                    "",
                )
            ).lower()

            if (
                label == "table"
                or raw_label == "table"
            ):
                continue

            try:
                confidence = float(
                    block.get(
                        "confidence",
                        0.0,
                    )
                    or 0.0
                )
            except (
                TypeError,
                ValueError,
            ):
                confidence = 0.0

            paragraphs.append(
                {
                    "text": text,
                    "page": block.get(
                        "page",
                        block.get(
                            "page_number"
                        ),
                    ),
                    "bbox": block.get(
                        "bbox",
                        [],
                    ),
                    "reading_order": block.get(
                        "reading_order"
                    ),
                    "confidence": round(
                        confidence,
                        4,
                    ),
                }
            )

        return paragraphs

    # ============================================================
    # MAIN STRUCTURE
    # ============================================================

    def structure(
        self,
        data,
    ):
        blocks = data.get(
            "results",
            [],
        )

        if not isinstance(
            blocks,
            list,
        ):
            raise ValueError(
                "'results' must be a list."
            )

        fields = {}
        used_indexes = set()

        # ========================================================
        # STEP 1 — KNOWN FIELDS
        # ========================================================

        for index, block in enumerate(
            blocks
        ):
            if not isinstance(
                block,
                dict,
            ):
                continue

            # ----------------------------------------------------
            # NEVER extract fields from tables.
            # ----------------------------------------------------

            block_label = str(
                block.get(
                    "label",
                    "",
                )
            ).lower()

            block_raw_label = str(
                block.get(
                    "raw_label",
                    "",
                )
            ).lower()

            if (
                block_label == "table"
                or block_raw_label == "table"
            ):
                continue

            text = block.get(
                "text",
                "",
            )

            if not text:
                continue

            label_info = self.detect_label(
                text
            )

            if not label_info:
                continue

            field_name = label_info[
                "field"
            ]

            # ----------------------------------------------------
            # Same-block value
            # ----------------------------------------------------

            value = self.extract_inline_value(
                text,
                label_info,
            )

            value_block = None

            # ----------------------------------------------------
            # Special case:
            #
            # Label only block.
            #
            # Example:
            #
            # Mother's Name
            #
            # PINALBEN PATEL
            # ----------------------------------------------------

            if not value:

                value_block = self.find_nearby_value(
                    blocks,
                    index,
                    block.get(
                        "bbox",
                        [],
                    ),
                )

                if value_block:

                    value = self.clean_value(
                        value_block.get(
                            "text",
                            "",
                        )
                    )

            # ----------------------------------------------------
            # Clean field value
            # ----------------------------------------------------

            if value:
                value = self.clean_field_value(
                    field_name,
                    value,
                )

            # ----------------------------------------------------
            # Validate value
            # ----------------------------------------------------

            if not self.is_valid_field_value(
                field_name,
                value,
            ):
                continue

            # ----------------------------------------------------
            # Create field
            # ----------------------------------------------------

            new_field = self.create_field(
                field_name,
                label_info.get(
                    "original_label",
                    label_info.get(
                        "label"
                    ),
                ),
                value,
                block,
                value_block,
            )

            # ----------------------------------------------------
            # If duplicate field:
            #
            # Prefer:
            #   1. valid value
            #   2. longer value
            #   3. higher confidence
            # ----------------------------------------------------

            if field_name not in fields:

                fields[field_name] = new_field

            else:

                existing = fields[
                    field_name
                ]

                existing_value = str(
                    existing.get(
                        "value",
                        "",
                    )
                )

                existing_confidence = float(
                    existing.get(
                        "confidence",
                        0.0,
                    )
                    or 0.0
                )

                new_confidence = float(
                    new_field.get(
                        "confidence",
                        0.0,
                    )
                    or 0.0
                )

                if (
                    new_confidence > existing_confidence
                    or (
                        new_confidence
                        == existing_confidence
                        and len(value)
                        > len(existing_value)
                    )
                ):
                    fields[field_name] = new_field

            # ----------------------------------------------------
            # Mark label block used.
            # ----------------------------------------------------

            used_indexes.add(
                index
            )

            # ----------------------------------------------------
            # Mark nearby value block used.
            # ----------------------------------------------------

            if value_block:

                try:
                    value_index = blocks.index(
                        value_block
                    )

                    used_indexes.add(
                        value_index
                    )

                except ValueError:
                    pass

        # ========================================================
        # STEP 2 — GENERIC KEY/VALUE
        # ========================================================

        generic_pairs = (
            self.extract_generic_pairs(
                blocks,
                used_indexes,
            )
        )

        # ========================================================
        # STEP 3 — TABLES
        # ========================================================

        tables = self.extract_tables(
            blocks
        )

        for index, block in enumerate(
            blocks
        ):
            if not isinstance(
                block,
                dict,
            ):
                continue

            label = str(
                block.get(
                    "label",
                    "",
                )
            ).lower()

            raw_label = str(
                block.get(
                    "raw_label",
                    "",
                )
            ).lower()

            if (
                label == "table"
                or raw_label == "table"
            ):
                used_indexes.add(
                    index
                )

        # ========================================================
        # STEP 4 — PARAGRAPHS
        # ========================================================

        paragraphs = (
            self.extract_unstructured_text(
                blocks,
                used_indexes,
            )
        )

        # ========================================================
        # DOCUMENT TYPE
        # ========================================================

        document_type = (
            self.detect_document_type(
                blocks
            )
        )

        # ========================================================
        # PAGES
        # ========================================================

        page_values = []

        for block in blocks:

            if not isinstance(
                block,
                dict,
            ):
                continue

            page = block.get(
                "page",
                block.get(
                    "page_number"
                ),
            )

            if page is not None:
                page_values.append(
                    page
                )

        pages = sorted(
            set(page_values)
        )

        # ========================================================
        # LANGUAGES
        # ========================================================

        languages = data.get(
            "detected_languages",
            [],
        )

        if not languages:

            languages = sorted(
                {
                    str(
                        block.get(
                            "language"
                        )
                    )
                    for block in blocks
                    if isinstance(
                        block,
                        dict,
                    )
                    and block.get(
                        "language"
                    )
                    and block.get(
                        "language"
                    )
                    != "unknown"
                }
            )

        # ========================================================
        # RESULT
        # ========================================================

        structured = {
            "document": {
                "type": document_type,
                "pages": len(pages),
                "languages": languages,
                "multilingual": data.get(
                    "multilingual",
                    len(languages) > 1,
                ),
            },

            "fields": fields,

            "key_value_pairs": generic_pairs,

            "tables": tables,

            "paragraphs": paragraphs,

            "metadata": {
                "total_ocr_blocks": data.get(
                    "total_blocks",
                    len(blocks),
                ),
                "structured_fields": len(
                    fields
                ),
                "generic_key_value_pairs": len(
                    generic_pairs
                ),
                "structured_tables": len(
                    tables
                ),
                "paragraph_blocks": len(
                    paragraphs
                ),
                "source_json": data.get(
                    "source_json"
                ),
            },
        }

        return structured

    # ============================================================
    # PROCESS FILE
    # ============================================================

    def process_file(
        self,
        input_path,
        output_path=None,
    ):
        input_path = Path(
            input_path
        )

        data = self.load_json(
            input_path
        )

        structured = self.structure(
            data
        )

        if output_path is None:
            output_path = (
                input_path.parent
                / "structured.json"
            )

        output_path = Path(
            output_path
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(
            output_path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                structured,
                file,
                ensure_ascii=False,
                indent=2,
            )

        return structured, output_path


# ================================================================
# COMMAND LINE
# ================================================================

if __name__ == "__main__":

    import sys

    print()
    print("=" * 70)
    print("       ASTRA STRUCTURED OUTPUT ENGINE")
    print("=" * 70)
    print()

    # ------------------------------------------------------------
    # Allow:
    #
    # python structured_runner.py "path\file.json"
    #
    # ------------------------------------------------------------

    if len(sys.argv) > 1:

        input_path = Path(
            sys.argv[1]
        )

    else:

        current_dir = Path(
            __file__
        ).resolve().parent

        input_path = (
            current_dir
            / "results.json"
        )

    output_path = (
        input_path.parent
        / "structured.json"
    )

    print(
        f"Input JSON:\n{input_path}"
    )

    print()
    print("-" * 60)

    if not input_path.exists():

        print()
        print(
            "ERROR: Input JSON was not found."
        )
        print()
        print(
            input_path
        )
        print()

        raise SystemExit(
            1
        )

    service = AstraStructuredService()

    structured, output_path = (
        service.process_file(
            input_path,
            output_path,
        )
    )

    print(
        "DOCUMENT TYPE:"
    )

    print(
        structured[
            "document"
        ][
            "type"
        ]
    )

    print()
    print(
        "STRUCTURED FIELDS:"
    )

    if structured[
        "fields"
    ]:

        for key, field in structured[
            "fields"
        ].items():

            print(
                f"  {key}: "
                f"{field.get('value')}"
            )

    else:

        print(
            "  No structured fields detected."
        )

    print()

    print(
        f"Tables detected: "
        f"{len(structured['tables'])}"
    )

    print()

    print(
        "Output:"
    )

    print(
        output_path
    )

    print()
    print("=" * 70)
    print(
        "       STRUCTURING COMPLETE"
    )
    print("=" * 70)