import re


class OCRQualityService:

    SUPPORTED_LANGUAGES = {
        "en",
        "hin",
        "guj"
    }

    # =========================================================
    # QUALITY WEIGHTS
    # =========================================================
    #
    # OCR quality should primarily measure the quality of the
    # extracted text, not how much physical area of the page
    # contains text.
    #
    # Coverage is therefore deliberately given a small weight.
    #
    WEIGHTS = {
        "text": 0.35,
        "language": 0.25,
        "character": 0.20,
        "coverage": 0.05,
        "confidence": 0.15,
    }

    # =========================================================
    # MAIN QUALITY CALCULATION
    # =========================================================

    def calculate_quality(
        self,
        text,
        blocks=None,
        page_width=None,
        page_height=None,
        expected_language=None,
        layout_confidence=None
    ):

        text_score = self._calculate_text_score(
            text
        )

        language_score = self._calculate_language_score(
            text,
            expected_language
        )

        character_score = self._calculate_character_score(
            text,
            expected_language
        )

        coverage_score, coverage_available = (
            self._calculate_coverage(
                blocks,
                page_width,
                page_height
            )
        )

        confidence_score, confidence_available = (
            self._calculate_confidence_score(
                blocks,
                layout_confidence
            )
        )

        # -----------------------------------------------------
        # AVAILABLE COMPONENTS
        # -----------------------------------------------------

        available_scores = {
            "text": text_score,
            "language": language_score,
            "character": character_score,
        }

        if coverage_available:
            available_scores["coverage"] = coverage_score

        if confidence_available:
            available_scores["confidence"] = confidence_score

        # -----------------------------------------------------
        # RENORMALIZE WEIGHTS
        # -----------------------------------------------------

        total_weight = sum(
            self.WEIGHTS[key]
            for key in available_scores
        )

        if total_weight <= 0:
            quality_score = 0.0

        else:
            weighted_score = sum(
                available_scores[key]
                * self.WEIGHTS[key]
                for key in available_scores
            )

            quality_score = (
                weighted_score
                / total_weight
            )

        quality_score = round(
            quality_score,
            2
        )

        status = self._get_status(
            quality_score
        )

        # -----------------------------------------------------
        # RESULT
        # -----------------------------------------------------

        return {
            "quality_score": quality_score,

            "status": status,

            "text_score": round(
                text_score,
                2
            ),

            "language_score": round(
                language_score,
                2
            ),

            "character_score": round(
                character_score,
                2
            ),

            "coverage_score": (
                round(
                    coverage_score,
                    2
                )
                if coverage_available
                else None
            ),

            "confidence_score": (
                round(
                    confidence_score,
                    2
                )
                if confidence_available
                else None
            ),

            "components_used": sorted(
                available_scores.keys()
            )
        }

    # =========================================================
    # STATUS
    # =========================================================

    def _get_status(self, score):

        if score >= 80:
            return "good"

        elif score >= 60:
            return "review"

        return "retry"

    # =========================================================
    # TEXT QUALITY
    # =========================================================

    def _calculate_text_score(self, text):

        if not text or not text.strip():
            return 0

        text = text.strip()

        if len(text) <= 2:
            return 50

        meaningful_chars = len(
            re.findall(
                r"[A-Za-z"
                r"\u0900-\u097F"
                r"\u0A80-\u0AFF"
                r"0-9]",
                text
            )
        )

        total_chars = len(
            text.replace(
                " ",
                ""
            )
        )

        if total_chars == 0:
            return 0

        score = (
            meaningful_chars
            / total_chars
        ) * 100

        return min(
            score,
            100
        )

    # =========================================================
    # LANGUAGE QUALITY
    # =========================================================

    def _calculate_language_score(
        self,
        text,
        expected_language
    ):

        if not text or not text.strip():
            return 0

        # -----------------------------------------------------
        # NO EXPECTED LANGUAGE
        # -----------------------------------------------------

        if not expected_language:

            return self._multilingual_language_score(
                text
            )

        counts = self._get_language_counts(
            text
        )

        active_languages = [
            language
            for language, count
            in counts.items()
            if count > 0
        ]

        # -----------------------------------------------------
        # MULTILINGUAL DOCUMENT
        # -----------------------------------------------------

        if len(active_languages) >= 2:

            return self._multilingual_language_score(
                text
            )

        relevant_chars = sum(
            counts.values()
        )

        if relevant_chars == 0:
            return 0

        detected_count = counts.get(
            expected_language,
            0
        )

        return min(
            (
                detected_count
                / relevant_chars
            ) * 100,
            100
        )

    # =========================================================
    # MULTILINGUAL SCORE
    # =========================================================

    def _multilingual_language_score(
        self,
        text
    ):

        counts = self._get_language_counts(
            text
        )

        total = sum(
            counts.values()
        )

        if total == 0:
            return 0

        # Hindi + English, Gujarati + English,
        # Hindi + Gujarati, etc. are valid.
        #
        # Mixed language is not itself an OCR error.

        return 100

    # =========================================================
    # LANGUAGE COUNTS
    # =========================================================

    def _get_language_counts(
        self,
        text
    ):

        return {

            "guj": len(
                re.findall(
                    r"[\u0A80-\u0AFF]",
                    text
                )
            ),

            "hin": len(
                re.findall(
                    r"[\u0900-\u097F]",
                    text
                )
            ),

            "en": len(
                re.findall(
                    r"[A-Za-z]",
                    text
                )
            )
        }

    # =========================================================
    # CHARACTER VALIDITY
    # =========================================================

    def _calculate_character_score(
        self,
        text,
        expected_language=None
    ):

        if not text:
            return 0

        pattern = (
            r"[A-Za-z0-9"
            r"\u0900-\u097F"
            r"\u0A80-\u0AFF"
            r"\s"
            r"।"
            r","
            r"."
            r"!"
            r"?"
            r";"
            r":"
            r"'"
            r'"'
            r"("
            r")"
            r"/"
            r"-"
            r"₹"
            r"%]"
        )

        valid = len(
            re.findall(
                pattern,
                text
            )
        )

        total = len(
            text
        )

        if total == 0:
            return 0

        return min(
            (
                valid
                / total
            ) * 100,
            100
        )

    # =========================================================
    # COVERAGE
    # =========================================================

    def _calculate_coverage(
        self,
        blocks,
        page_width,
        page_height
    ):

        if not page_width or not page_height:
            return 0, False

        if not blocks:
            return 0, True

        page_area = (
            page_width
            * page_height
        )

        if page_area <= 0:
            return 0, False

        text_area = 0

        for block in blocks:

            bbox = block.get(
                "bbox"
            )

            if not bbox:
                continue

            if (
                isinstance(
                    bbox,
                    list
                )
                and len(bbox) >= 4
            ):

                try:

                    x1 = float(
                        bbox[0]
                    )

                    y1 = float(
                        bbox[1]
                    )

                    x2 = float(
                        bbox[2]
                    )

                    y2 = float(
                        bbox[3]
                    )

                except (
                    TypeError,
                    ValueError
                ):
                    continue

                width = max(
                    0,
                    x2 - x1
                )

                height = max(
                    0,
                    y2 - y1
                )

                text_area += (
                    width
                    * height
                )

        coverage = (
            text_area
            / page_area
        ) * 100

        return min(
            coverage,
            100
        ), True

    # =========================================================
    # CONFIDENCE
    # =========================================================

    def _calculate_confidence_score(
        self,
        blocks,
        layout_confidence=None
    ):

        # -----------------------------------------------------
        # EXPLICIT PAGE CONFIDENCE
        # -----------------------------------------------------

        if layout_confidence is not None:

            try:

                confidence = float(
                    layout_confidence
                )

            except (
                TypeError,
                ValueError
            ):

                confidence = None

            if confidence is not None:

                if confidence <= 1:
                    confidence *= 100

                return (
                    min(
                        max(
                            confidence,
                            0
                        ),
                        100
                    ),
                    True
                )

        # -----------------------------------------------------
        # BLOCK CONFIDENCE
        # -----------------------------------------------------

        if not blocks:
            return 0, False

        confidences = []

        for block in blocks:

            confidence = block.get(
                "confidence"
            )

            if confidence is None:

                confidence = block.get(
                    "layout_confidence"
                )

            if confidence is None:
                continue

            try:

                confidence = float(
                    confidence
                )

            except (
                TypeError,
                ValueError
            ):
                continue

            if confidence <= 1:
                confidence *= 100

            confidence = min(
                max(
                    confidence,
                    0
                ),
                100
            )

            confidences.append(
                confidence
            )

        if not confidences:
            return 0, False

        return (
            sum(confidences)
            / len(confidences),
            True
        )

    # =========================================================
    # DOCUMENT QUALITY
    # =========================================================

    def calculate_document_quality(
        self,
        structured_document
    ):

        pages = structured_document.get(
            "pages",
            []
        )

        if not pages:

            return {
                "document_quality_score": 0,

                "status": "retry",

                "multilingual": False,

                "detected_languages": [],

                "pages": []
            }

        page_results = []

        document_language_counts = {
            "en": 0,
            "hin": 0,
            "guj": 0
        }

        for page in pages:

            blocks = page.get(
                "blocks",
                []
            )

            # -------------------------------------------------
            # PAGE DIMENSIONS
            # -------------------------------------------------

            image_bbox = page.get(
                "image_bbox"
            )

            page_width = None
            page_height = None

            if (
                isinstance(
                    image_bbox,
                    list
                )
                and len(image_bbox) >= 4
            ):

                page_width = (
                    image_bbox[2]
                    - image_bbox[0]
                )

                page_height = (
                    image_bbox[3]
                    - image_bbox[1]
                )

            # -------------------------------------------------
            # PAGE TEXT
            # -------------------------------------------------

            page_text = "\n".join(
                block.get(
                    "text",
                    ""
                )
                for block in blocks
                if block.get(
                    "text",
                    ""
                ).strip()
            )

            # -------------------------------------------------
            # DETECT LANGUAGES
            # -------------------------------------------------

            page_languages = set()

            for block in blocks:

                language = block.get(
                    "language"
                )

                if language in self.SUPPORTED_LANGUAGES:

                    page_languages.add(
                        language
                    )

                    document_language_counts[
                        language
                    ] += 1

            # -------------------------------------------------
            # EXPECTED LANGUAGE
            # -------------------------------------------------

            expected_language = None

            if page_languages:

                page_language_counts = {}

                for block in blocks:

                    language = block.get(
                        "language"
                    )

                    if (
                        language
                        in self.SUPPORTED_LANGUAGES
                    ):

                        page_language_counts[
                            language
                        ] = (
                            page_language_counts.get(
                                language,
                                0
                            )
                            + 1
                        )

                if page_language_counts:

                    expected_language = max(
                        page_language_counts,
                        key=page_language_counts.get
                    )

            multilingual = (
                len(page_languages)
                >= 2
            )

            # -------------------------------------------------
            # PAGE QUALITY
            # -------------------------------------------------

            quality = self.calculate_quality(
                text=page_text,

                blocks=blocks,

                page_width=page_width,

                page_height=page_height,

                expected_language=expected_language
            )

            quality["page"] = page.get(
                "page"
            )

            quality[
                "detected_language"
            ] = expected_language

            quality[
                "detected_languages"
            ] = sorted(
                page_languages
            )

            quality[
                "multilingual"
            ] = multilingual

            page_results.append(
                quality
            )

        # -----------------------------------------------------
        # DOCUMENT LANGUAGES
        # -----------------------------------------------------

        detected_languages = [
            language

            for language, count
            in document_language_counts.items()

            if count > 0
        ]

        document_multilingual = (
            len(
                detected_languages
            ) >= 2
        )

        # -----------------------------------------------------
        # DOCUMENT SCORE
        # -----------------------------------------------------

        scores = [
            page["quality_score"]
            for page in page_results
        ]

        document_score = round(
            sum(scores)
            / len(scores),
            2
        )

        status = self._get_status(
            document_score
        )

        return {
            "document_quality_score":
                document_score,

            "status":
                status,

            "multilingual":
                document_multilingual,

            "detected_languages":
                detected_languages,

            "pages":
                page_results
        }