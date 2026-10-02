"""
ASTRA INTELLIGENCE SERVICE V2.1
================================

Independent intelligence layer for Astra OCR.

IMPORTANT:
-----------
This file does NOT modify Surya OCR.

Architecture:

    Surya OCR
         |
         v
    Normalized OCR blocks
         |
         v
    Astra Intelligence V2.1
         |
         +---- Field classification
         |
         +---- Field-specific validation
         |
         +---- OCR ambiguity detection
         |
         +---- Lexical anomaly detection
         |
         +---- Evidence combination
         |
         v
    NORMAL / SUSPICIOUS

The OCR text itself is NEVER automatically changed.
Astra only produces evidence and possible alternatives.
"""


import re
from difflib import SequenceMatcher


class AstraIntelligenceService:

    # ============================================================
    # INITIALIZATION
    # ============================================================

    def __init__(
        self,
        confidence_threshold=0.75,
        uncertainty_threshold=0.45,
    ):

        self.confidence_threshold = (
            confidence_threshold
        )

        self.uncertainty_threshold = (
            uncertainty_threshold
        )

        # --------------------------------------------------------
        # Document vocabulary.
        #
        # This is intentionally generic rather than a hard-coded
        # correction dictionary.
        # --------------------------------------------------------

        self.common_words = {

            "name",
            "candidate",
            "father",
            "mother",
            "date",
            "birth",
            "dateofbirth",

            "roll",
            "number",
            "rollnumber",

            "registration",
            "regn",

            "subject",
            "code",
            "marks",
            "total",
            "grade",

            "result",
            "percentage",

            "certificate",
            "signature",

            "address",
            "application",
            "student",

            "school",
            "college",
            "university",

            "government",
            "department",

            "invoice",
            "amount",
            "customer",

            "phone",
            "mobile",
            "email",
        }

        # --------------------------------------------------------
        # OCR character confusions.
        #
        # Used as evidence only.
        # --------------------------------------------------------

        self.confusion_pairs = {

            ("0", "O"),
            ("O", "0"),

            ("1", "I"),
            ("I", "1"),

            ("1", "l"),
            ("l", "1"),

            ("5", "S"),
            ("S", "5"),

            ("8", "B"),
            ("B", "8"),

            ("6", "G"),
            ("G", "6"),
        }

    # ============================================================
    # PUBLIC API
    # ============================================================

    def analyze(
        self,
        ocr_result,
    ):

        if not isinstance(
            ocr_result,
            dict,
        ):

            raise TypeError(
                "ocr_result must be a dictionary."
            )

        blocks = ocr_result.get(
            "results",
            [],
        )

        if not isinstance(
            blocks,
            list,
        ):

            blocks = []

        analyzed_blocks = []

        suspicious_regions = []

        # ========================================================
        # ANALYZE EACH BLOCK
        # ========================================================

        for index, block in enumerate(
            blocks
        ):

            if not isinstance(
                block,
                dict,
            ):

                continue

            analysis = (
                self._analyze_block(
                    block,
                    index,
                )
            )

            analyzed_blocks.append(
                analysis
            )

            if (
                analysis["status"]
                == "suspicious"
            ):

                suspicious_regions.append(
                    analysis
                )

        # ========================================================
        # DOCUMENT LEVEL
        # ========================================================

        document_signals = (
            self._document_level_analysis(
                analyzed_blocks
            )
        )

        return {

            "success": True,

            "version": "2.1",

            "total_blocks": len(
                analyzed_blocks
            ),

            "suspicious_blocks": len(
                suspicious_regions
            ),

            "blocks": analyzed_blocks,

            "suspicious_regions": (
                suspicious_regions
            ),

            "document_signals": (
                document_signals
            ),

            "summary": {

                "safe": (
                    len(analyzed_blocks)
                    - len(suspicious_regions)
                ),

                "suspicious": len(
                    suspicious_regions
                ),
            },
        }

    # ============================================================
    # BLOCK ANALYSIS
    # ============================================================

    def _analyze_block(
        self,
        block,
        index,
    ):

        text = str(
            block.get(
                "text",
                "",
            )
        ).strip()

        confidence = (
            self._safe_float(
                block.get(
                    "confidence",
                    0.0,
                )
            )
        )

        label = str(
            block.get(
                "label",
                "",
            )
        )

        signals = []

        evidence_scores = []

        # ========================================================
        # FIELD TYPE
        # ========================================================

        field_type = (
            self._detect_field_type(
                text
            )
        )

        # ========================================================
        # CONFIDENCE
        # ========================================================

        if (
            confidence
            < self.confidence_threshold
        ):

            signals.append(
                "low_ocr_confidence"
            )

            evidence_scores.append(
                min(
                    0.60,
                    1.0 - confidence,
                )
            )

        # ========================================================
        # FIELD-SPECIFIC ANALYSIS
        # ========================================================

        lexical_result = {
            "suspicious": False,
            "score": 0.0,
            "words": [],
            "possible_candidates": [],
        }

        structure_result = {
            "suspicious": False,
            "score": 0.0,
            "reason": "",
        }

        # --------------------------------------------------------
        # NAME / GENERAL TEXT
        # --------------------------------------------------------

        if field_type in {
            "name",
            "general_text",
        }:

            lexical_result = (
                self._detect_lexical_anomaly(
                    text
                )
            )

            if lexical_result[
                "suspicious"
            ]:

                signals.append(
                    "possible_lexical_anomaly"
                )

                evidence_scores.append(
                    lexical_result[
                        "score"
                    ]
                )

        # --------------------------------------------------------
        # STRUCTURED FIELDS
        # --------------------------------------------------------

        structure_result = (
            self._validate_field_structure(
                text,
                field_type,
            )
        )

        if structure_result[
            "suspicious"
        ]:

            signals.append(
                "field_structure_anomaly"
            )

            evidence_scores.append(
                structure_result[
                    "score"
                ]
            )

        # ========================================================
        # AMBIGUOUS CHARACTERS
        #
        # IMPORTANT:
        # Do NOT blindly apply this to every field.
        #
        # A normal name containing "B" or "I" is not suspicious.
        #
        # This detector is strongest for identifiers.
        # ========================================================

        ambiguous_count = 0

        if field_type in {
            "roll_number",
            "registration_number",
            "identifier",
        }:

            ambiguous_count = (
                self._count_ambiguous_sequences(
                    text
                )
            )

            if ambiguous_count > 0:

                signals.append(
                    "ambiguous_character_sequence"
                )

                evidence_scores.append(
                    min(
                        0.50,
                        ambiguous_count
                        * 0.20,
                    )
                )

        # ========================================================
        # GENERIC ALPHANUMERIC CHECK
        #
        # ONLY run on identifier-like fields.
        #
        # This fixes the false positive we saw earlier:
        #
        # Roll No. 17610283
        #
        # ========================================================

        if field_type in {
            "registration_number",
            "identifier",
        }:

            if (
                self._has_suspicious_alphanumeric_pattern(
                    text
                )
            ):

                signals.append(
                    "suspicious_alphanumeric_pattern"
                )

                evidence_scores.append(
                    0.45
                )

        # ========================================================
        # TABLE
        # ========================================================

        if label.lower() == "table":

            signals.append(
                "table_region"
            )

        # ========================================================
        # SYMBOL MIXING
        # ========================================================

        if (
            field_type
            in {
                "general_text",
                "name",
            }
        ):

            if self._has_unusual_symbol_mixing(
                text
            ):

                signals.append(
                    "unusual_symbol_mixing"
                )

                evidence_scores.append(
                    0.35
                )

        # ========================================================
        # UNCERTAINTY
        # ========================================================

        uncertainty = (
            self._calculate_uncertainty(
                confidence,
                evidence_scores,
            )
        )

        # ========================================================
        # STATUS
        # ========================================================

        if (
            uncertainty
            >= self.uncertainty_threshold
        ):

            status = "suspicious"

        else:

            status = "normal"

        # ========================================================
        # RESULT
        # ========================================================

        return {

            "index": index,

            "text": text,

            "page": block.get(
                "page",
                block.get(
                    "page_number",
                    1,
                ),
            ),

            "bbox": block.get(
                "bbox",
                [],
            ),

            "language": block.get(
                "language",
                "unknown",
            ),

            "label": label,

            "surya_confidence": confidence,

            "field_type": field_type,

            "uncertainty_score": round(
                uncertainty,
                4,
            ),

            "status": status,

            "signals": signals,

            "ambiguous_character_count": (
                ambiguous_count
            ),

            "lexical_analysis": (
                lexical_result
            ),

            "structure_analysis": (
                structure_result
            ),
        }

    # ============================================================
    # FIELD TYPE DETECTION
    # ============================================================

    def _detect_field_type(
        self,
        text,
    ):

        normalized = (
            text.lower()
            .strip()
        )

        compact = re.sub(
            r"\s+",
            "",
            normalized,
        )

        # --------------------------------------------------------
        # ROLL NUMBER
        # --------------------------------------------------------

        if (
            "roll no" in normalized
            or "rollno" in compact
            or "roll number" in normalized
        ):

            return "roll_number"

        # --------------------------------------------------------
        # REGISTRATION
        # --------------------------------------------------------

        if (
            "registration" in normalized
            or "regn.no" in normalized
            or "regnno" in compact
        ):

            return "registration_number"

        # --------------------------------------------------------
        # DATE
        # --------------------------------------------------------

        if re.search(
            r"\bdate\b",
            normalized,
        ):

            return "date"

        # --------------------------------------------------------
        # EMAIL
        # --------------------------------------------------------

        if "@" in text:

            return "email"

        # --------------------------------------------------------
        # PHONE
        # --------------------------------------------------------

        digits = re.sub(
            r"\D",
            "",
            text,
        )

        if len(digits) >= 10:

            return "phone"

        # --------------------------------------------------------
        # NAME
        # --------------------------------------------------------

        if re.search(
            r"\bname\b",
            normalized,
        ):

            return "name"

        # --------------------------------------------------------
        # MARKS
        # --------------------------------------------------------

        if re.search(
            r"\bmarks?\b",
            normalized,
        ):

            return "marks"

        # --------------------------------------------------------
        # GENERIC IDENTIFIER
        # --------------------------------------------------------

        if self._looks_like_identifier(
            text
        ):

            return "identifier"

        return "general_text"

    # ============================================================
    # LEXICAL ANALYSIS
    # ============================================================

    def _detect_lexical_anomaly(
        self,
        text,
    ):

        words = re.findall(
            r"[A-Za-z]+",
            text,
        )

        suspicious_words = []

        candidates = []

        for word in words:

            normalized = (
                word.lower()
            )

            if len(normalized) < 4:
                continue

            if (
                normalized
                in self.common_words
            ):
                continue

            candidate = (
                self._find_near_word(
                    normalized
                )
            )

            if candidate is None:
                continue

            # ----------------------------------------------------
            # Important:
            #
            # A word should only be considered suspicious when
            # the similarity is strong AND there is a plausible
            # OCR character-level relationship.
            # ----------------------------------------------------

            similarity = (
                SequenceMatcher(
                    None,
                    normalized,
                    candidate,
                ).ratio()
            )

            confusion_distance = (
                self._ocr_confusion_distance(
                    normalized,
                    candidate,
                )
            )

            if (
                similarity >= 0.78
                and confusion_distance
                is not None
            ):

                suspicious_words.append(
                    word
                )

                candidates.append(
                    {
                        "observed": word,

                        "possible": candidate,

                        "similarity": round(
                            similarity,
                            4,
                        ),

                        "confusion_distance": (
                            confusion_distance
                        ),
                    }
                )

        if suspicious_words:

            return {

                "suspicious": True,

                "score": 0.60,

                "words": suspicious_words,

                "possible_candidates": candidates,
            }

        return {

            "suspicious": False,

            "score": 0.0,

            "words": [],

            "possible_candidates": [],
        }

    # ============================================================
    # FIND NEAR WORD
    # ============================================================

    def _find_near_word(
        self,
        word,
    ):

        best_word = None

        best_ratio = 0.0

        for known in self.common_words:

            if abs(
                len(word)
                - len(known)
            ) > 2:

                continue

            ratio = (
                SequenceMatcher(
                    None,
                    word,
                    known,
                ).ratio()
            )

            if ratio > best_ratio:

                best_ratio = ratio

                best_word = known

        if (
            best_word is not None
            and best_word != word
            and best_ratio >= 0.78
        ):

            return best_word

        return None

    # ============================================================
    # OCR CONFUSION DISTANCE
    # ============================================================

    def _ocr_confusion_distance(
        self,
        observed,
        candidate,
    ):
        """
        Determine whether the difference between two words
        could plausibly be caused by an OCR character confusion.

        Returns:
            integer distance
            None if the difference is not explainable
            by our OCR confusion model.
        """

        if len(observed) != len(candidate):

            return None

        differences = 0

        for a, b in zip(
            observed,
            candidate,
        ):

            if a == b:

                continue

            if (
                a.upper(),
                b.upper(),
            ) in {
                ("O", "0"),
                ("0", "O"),
                ("I", "1"),
                ("1", "I"),
                ("I", "L"),
                ("L", "I"),
                ("S", "5"),
                ("5", "S"),
                ("B", "8"),
                ("8", "B"),
                ("G", "6"),
                ("6", "G"),
            }:

                differences += 1

            else:

                # A normal alphabetic substitution can still
                # occur in OCR, but don't allow too many.
                differences += 1

        if differences <= 2:

            return differences

        return None

    # ============================================================
    # FIELD STRUCTURE VALIDATION
    # ============================================================

    def _validate_field_structure(
        self,
        text,
        field_type,
    ):

        # ========================================================
        # ROLL NUMBER
        # ========================================================

        if field_type == "roll_number":

            value = (
                self._extract_value_after_label(
                    text,
                    [
                        "roll no",
                        "rollno",
                        "roll number",
                    ],
                )
            )

            if value:

                # Remove punctuation surrounding value.
                value = re.sub(
                    r"[^A-Za-z0-9]",
                    "",
                    value,
                )

                # ------------------------------------------------
                # Roll number should be numeric.
                # ------------------------------------------------

                if not re.fullmatch(
                    r"[0-9]{4,15}",
                    value,
                ):

                    return {

                        "suspicious": True,

                        "score": 0.70,

                        "reason": (
                            "Roll number contains "
                            "unexpected characters."
                        ),
                    }

            return self._normal_structure_result()

        # ========================================================
        # REGISTRATION NUMBER
        # ========================================================

        if field_type == "registration_number":

            compact = re.sub(
                r"\s+",
                "",
                text,
            )

            has_letters = bool(
                re.search(
                    r"[A-Za-z]",
                    compact,
                )
            )

            has_digits = bool(
                re.search(
                    r"\d",
                    compact,
                )
            )

            if not (
                has_letters
                and has_digits
            ):

                return {

                    "suspicious": True,

                    "score": 0.55,

                    "reason": (
                        "Registration identifier "
                        "does not contain the expected "
                        "mixed structure."
                    ),
                }

            return self._normal_structure_result()

        # ========================================================
        # DATE
        # ========================================================

        if field_type == "date":

            if re.search(
                r"\d{1,4}[-/]\d{1,2}[-/]\d{1,4}",
                text,
            ):

                return self._normal_structure_result()

            # Label-only blocks aren't necessarily errors.

            if re.search(
                r"\d",
                text,
            ):

                return {

                    "suspicious": True,

                    "score": 0.45,

                    "reason": (
                        "Possible malformed date."
                    ),
                }

            return self._normal_structure_result()

        # ========================================================
        # EMAIL
        # ========================================================

        if field_type == "email":

            if not re.search(
                r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
                text.strip(),
            ):

                return {

                    "suspicious": True,

                    "score": 0.60,

                    "reason": (
                        "Email-like content has "
                        "an unusual structure."
                    ),
                }

            return self._normal_structure_result()

        return self._normal_structure_result()

    # ============================================================
    # EXTRACT VALUE
    # ============================================================

    def _extract_value_after_label(
        self,
        text,
        labels,
    ):

        lowered = text.lower()

        for label in labels:

            position = lowered.find(
                label
            )

            if position == -1:

                continue

            value = text[
                position
                + len(label):
            ]

            value = re.sub(
                r"^[\s:.\-]+",
                "",
                value,
            )

            return value.strip()

        return ""

    # ============================================================
    # IDENTIFIER
    # ============================================================

    def _looks_like_identifier(
        self,
        text,
    ):

        compact = re.sub(
            r"\s+",
            "",
            text,
        )

        if len(compact) < 5:

            return False

        has_letters = bool(
            re.search(
                r"[A-Za-z]",
                compact,
            )
        )

        has_numbers = bool(
            re.search(
                r"\d",
                compact,
            )
        )

        return (
            has_letters
            and has_numbers
        )

    # ============================================================
    # AMBIGUOUS CHARACTER SEQUENCES
    # ============================================================

    def _count_ambiguous_sequences(
        self,
        text,
    ):

        compact = re.sub(
            r"\s+",
            "",
            text,
        )

        count = 0

        for i in range(
            len(compact) - 1
        ):

            pair = (
                compact[i],
                compact[i + 1],
            )

            if pair in self.confusion_pairs:

                count += 1

        return count

    # ============================================================
    # ALPHANUMERIC PATTERN
    # ============================================================

    def _has_suspicious_alphanumeric_pattern(
        self,
        text,
    ):

        compact = re.sub(
            r"\s+",
            "",
            text,
        )

        compact = re.sub(
            r"[^A-Za-z0-9]",
            "",
            compact,
        )

        if len(compact) < 4:

            return False

        has_letters = bool(
            re.search(
                r"[A-Za-z]",
                compact,
            )
        )

        has_numbers = bool(
            re.search(
                r"\d",
                compact,
            )
        )

        if not (
            has_letters
            and has_numbers
        ):

            return False

        ambiguous = sum(
            1
            for char in compact
            if char in {
                "O",
                "0",
                "I",
                "1",
                "l",
                "S",
                "5",
                "B",
                "8",
                "G",
                "6",
            }
        )

        return ambiguous >= 2

    # ============================================================
    # SYMBOL MIXING
    # ============================================================

    def _has_unusual_symbol_mixing(
        self,
        text,
    ):

        if len(text) < 6:

            return False

        symbols = sum(
            1
            for char in text
            if not (
                char.isalnum()
                or char.isspace()
            )
        )

        ratio = (
            symbols
            / len(text)
        )

        return ratio > 0.45

    # ============================================================
    # DOCUMENT LEVEL
    # ============================================================

    def _document_level_analysis(
        self,
        blocks,
    ):

        signals = []

        # --------------------------------------------------------
        # TABLES
        # --------------------------------------------------------

        tables = [

            block

            for block in blocks

            if str(
                block.get(
                    "label",
                    "",
                )
            ).lower()
            == "table"
        ]

        if tables:

            signals.append(
                {
                    "type": "table_detected",

                    "count": len(
                        tables
                    ),
                }
            )

        # --------------------------------------------------------
        # FIELD DISTRIBUTION
        # --------------------------------------------------------

        field_types = {}

        for block in blocks:

            field_type = block.get(
                "field_type",
                "general_text",
            )

            field_types[field_type] = (
                field_types.get(
                    field_type,
                    0,
                )
                + 1
            )

        signals.append(
            {
                "type": "field_distribution",

                "fields": field_types,
            }
        )

        # --------------------------------------------------------
        # HIGH CONFIDENCE SUSPICION
        # --------------------------------------------------------

        high_confidence_suspicious = [

            block

            for block in blocks

            if (
                block.get(
                    "surya_confidence",
                    0.0,
                )
                >= 0.85
                and block.get(
                    "status",
                    "normal",
                )
                == "suspicious"
            )
        ]

        if high_confidence_suspicious:

            signals.append(
                {
                    "type": (
                        "high_confidence_suspicion"
                    ),

                    "count": len(
                        high_confidence_suspicious
                    ),

                    "message": (
                        "Some OCR blocks were "
                        "flagged despite high "
                        "Surya confidence."
                    ),
                }
            )

        return signals

    # ============================================================
    # UNCERTAINTY
    # ============================================================

    def _calculate_uncertainty(
        self,
        confidence,
        evidence_scores,
    ):

        base_uncertainty = (
            1.0
            - confidence
        )

        if not evidence_scores:

            return base_uncertainty

        evidence = min(
            sum(
                evidence_scores
            ),
            1.0,
        )

        # --------------------------------------------------------
        # OCR confidence is one signal.
        # Astra evidence is another.
        #
        # This prevents high Surya confidence from completely
        # overriding structural anomalies.
        # --------------------------------------------------------

        uncertainty = (
            0.35
            * base_uncertainty
            +
            0.65
            * evidence
        )

        return max(
            0.0,
            min(
                1.0,
                uncertainty,
            ),
        )

    # ============================================================
    # NORMAL STRUCTURE
    # ============================================================

    def _normal_structure_result(
        self,
    ):

        return {

            "suspicious": False,

            "score": 0.0,

            "reason": "",
        }

    # ============================================================
    # SAFE FLOAT
    # ============================================================

    def _safe_float(
        self,
        value,
    ):

        try:

            return max(
                0.0,
                min(
                    1.0,
                    float(value),
                ),
            )

        except (
            TypeError,
            ValueError,
        ):

            return 0.0


# =================================================================
# DIRECT TEST
# =================================================================

if __name__ == "__main__":

    service = (
        AstraIntelligenceService()
    )

    test_result = {

        "results": [

            # ----------------------------------------------------
            # TEST 1
            # High confidence lexical anomaly
            # ----------------------------------------------------

            {
                "text":
                    "Name of Conditate SATYAM JHA",

                "confidence":
                    0.938,

                "bbox": [],

                "page":
                    1,

                "language":
                    "eng",

                "label":
                    "Text",
            },

            # ----------------------------------------------------
            # TEST 2
            # Normal name
            # ----------------------------------------------------

            {
                "text":
                    "Name of Candidate",

                "confidence":
                    0.95,

                "bbox": [],

                "page":
                    1,

                "language":
                    "eng",

                "label":
                    "Text",
            },

            # ----------------------------------------------------
            # TEST 3
            # Correct roll number
            # ----------------------------------------------------

            {
                "text":
                    "Roll No. 17610283",

                "confidence":
                    0.94,

                "bbox": [],

                "page":
                    1,

                "language":
                    "eng",

                "label":
                    "Text",
            },

            # ----------------------------------------------------
            # TEST 4
            # OCR confusion inside roll number
            # ----------------------------------------------------

            {
                "text":
                    "Roll No. 1761O283",

                "confidence":
                    0.94,

                "bbox": [],

                "page":
                    1,

                "language":
                    "eng",

                "label":
                    "Text",
            },

            # ----------------------------------------------------
            # TEST 5
            # Normal registration number
            # ----------------------------------------------------

            {
                "text":
                    "Regn.No. C220242/250046",

                "confidence":
                    0.94,

                "bbox": [],

                "page":
                    1,

                "language":
                    "eng",

                "label":
                    "Text",
            },

            # ----------------------------------------------------
            # TEST 6
            # Table
            # ----------------------------------------------------

            {
                "text":
                    "Subject Code Marks Total Grade",

                "confidence":
                    0.94,

                "bbox": [],

                "page":
                    1,

                "language":
                    "eng",

                "label":
                    "Table",
            },
        ]
    }

    result = service.analyze(
        test_result
    )

    print()
    print("=" * 65)
    print(
        "          ASTRA INTELLIGENCE V2.1 TEST"
    )
    print("=" * 65)

    print()

    print(
        f"Total blocks: "
        f"{result['total_blocks']}"
    )

    print(
        f"Suspicious blocks: "
        f"{result['suspicious_blocks']}"
    )

    print()

    for block in result["blocks"]:

        print("-" * 65)

        print(
            f"Block: "
            f"{block['index']}"
        )

        print(
            f"Text: "
            f"{block['text']}"
        )

        print(
            f"Field type: "
            f"{block['field_type']}"
        )

        print(
            f"Confidence: "
            f"{block['surya_confidence']}"
        )

        print(
            f"Uncertainty: "
            f"{block['uncertainty_score']}"
        )

        print(
            f"Status: "
            f"{block['status']}"
        )

        print(
            f"Signals: "
            f"{block['signals']}"
        )

        print(
            "Lexical analysis: "
            f"{block['lexical_analysis']}"
        )

        print(
            "Structure analysis: "
            f"{block['structure_analysis']}"
        )

    print()

    print(
        "Document signals:"
    )

    for signal in result[
        "document_signals"
    ]:

        print(
            signal
        )

    print()
    print("=" * 65)
    print(
        "                 TEST COMPLETE"
    )
    print("=" * 65)