import re


class LanguageService:

    def detect_script(self, text):

        if not text or not text.strip():
            return {
                "language": "unknown",
                "script": "unknown",
                "confidence": 0.0
            }

        gujarati_count = len(
            re.findall(r"[\u0A80-\u0AFF]", text)
        )

        hindi_count = len(
            re.findall(r"[\u0900-\u097F]", text)
        )

        english_count = len(
            re.findall(r"[A-Za-z]", text)
        )

        total_script_chars = (
            gujarati_count
            + hindi_count
            + english_count
        )

        if total_script_chars == 0:
            return {
                "language": "unknown",
                "script": "unknown",
                "confidence": 0.0
            }

        scores = {
            "guj": gujarati_count,
            "hin": hindi_count,
            "en": english_count
        }

        detected_language = max(
            scores,
            key=scores.get
        )

        highest_count = scores[detected_language]

        confidence = (
            highest_count /
            total_script_chars
        ) * 100

        if detected_language == "guj":
            script = "Gujarati"

        elif detected_language == "hin":
            script = "Devanagari"

        elif detected_language == "en":
            script = "Latin"

        else:
            script = "Unknown"

        return {
            "language": detected_language,
            "script": script,
            "confidence": round(confidence, 2)
        }

    def detect_mixed_languages(self, text):

        if not text or not text.strip():
            return []

        gujarati_count = len(
            re.findall(r"[\u0A80-\u0AFF]", text)
        )

        hindi_count = len(
            re.findall(r"[\u0900-\u097F]", text)
        )

        english_count = len(
            re.findall(r"[A-Za-z]", text)
        )

        counts = {
            "guj": gujarati_count,
            "hin": hindi_count,
            "en": english_count
        }

        total = sum(counts.values())

        if total == 0:
            return []

        detected = []

        for language, count in counts.items():

            if count == 0:
                continue

            percentage = (
                count / total
            ) * 100

            detected.append({
                "language": language,
                "percentage": round(
                    percentage,
                    2
                )
            })

        detected.sort(
            key=lambda x: x["percentage"],
            reverse=True
        )

        return detected