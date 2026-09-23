"""
Post-OCR correction for CBSE marks-statement documents.

Two independent, deterministic correction strategies -- no LLM calls,
so there's zero risk of hallucinating a name, roll number, or mark
that isn't actually on the page:

1. Lexicon-based fuzzy correction for FIXED TEMPLATE TEXT (field
   labels, footer boilerplate). These strings are identical on every
   copy of this form, so a close-enough OCR match can be safely
   snapped to the known-correct version. Anything too far off to be
   confident about is flagged "needs_review" instead of guessed.

2. Marks-table parsing + arithmetic / word-vs-digit cross-validation.
   Every subject row carries three independent signals that must
   agree: Theory + IA/PR = Total, and Total (digits) must equal
   Total (in words). Any mismatch is a near-certain OCR digit error,
   and in most cases the correct value is uniquely recoverable.

Use apply_corrections(final_result) as the single entry point -- it
runs both strategies over a Surya OCR result dict and returns a new
result dict plus a report of everything that was changed or flagged.
"""

import re
from collections import Counter

from rapidfuzz import fuzz


# ============================================================
# 1. LEXICON-BASED LABEL CORRECTION
# ============================================================

# Fixed template strings that appear on this document type. Extend
# this list as you process more pages/forms -- anything that's
# identical across every copy of the certificate belongs here.
KNOWN_LABELS = [
    "क्रम संख्या/",
    "रजि. नं.",
    "केन्द्रीय माध्यमिक शिक्षा बोर्ड",
    "CENTRAL BOARD OF SECONDARY EDUCATION",
    "अंक विवरणिका",
    "MARKS STATEMENT",
    "सीनियर स्कूल सर्टिफिकेट परीक्षा, 2020",
    "SENIOR SCHOOL CERTIFICATE EXAMINATION, 2020",
    "परीक्षार्थी का नाम",
    "Name of Candidate",
    "अनुक्रमांक",
    "Roll No.",
    "माता का नाम",
    "Mother's Name",
    "पिता/संरक्षक का नाम",
    "Father's/Guardian's Name",
    "विद्यालय",
    "School",
    "संक्षिप्तियों का अर्थ : Abbreviations",
    "AB : अनुपस्थित Absent",
    "परिणाम Result",
    "RP : प्रयोगात्मक में पुनरावृत्ति Repeat in Practical",
    "RT : लिखित में पुनरावृत्ति Repeat in Theory",
    "ER : अनिवार्य पुनरावृत्ति सभी विषयों में",
    "Essential Repeat in all subjects",
    "दिल्ली Delhi",
    "दिनांक Dated :",
    "परीक्षा नियंत्रक",
    "Controller of Examinations",
]

FUZZY_THRESHOLD = 82       # 0-100. Confident enough to auto-correct.
SUGGESTION_THRESHOLD = 40  # Below auto-correct but still worth a
                           # human glance -- e.g. heavily-garbled
                           # Devanagari conjuncts (द्य, क्ष, etc.) can
                           # legitimately have high edit-distance from
                           # the correct word even when a human would
                           # instantly recognize the intended label.
                           # No threshold can safely auto-fix those
                           # without risking false corrections on real
                           # data elsewhere -- so we surface them
                           # instead of guessing.


def correct_known_labels(text, known_labels=KNOWN_LABELS, threshold=FUZZY_THRESHOLD,
                          suggestion_threshold=SUGGESTION_THRESHOLD):
    """
    Correct fixed template text (labels/boilerplate) against a list of
    known-correct strings.

    Handles two shapes seen in Surya's output:
      - Standalone label blocks, e.g. "परीक्षाणी का नाम"
      - Label + variable value in one block, e.g.
        "Name of Cendidate SATYAM JHA" -- only the label PREFIX is
        corrected; the variable data (the actual name) is left
        untouched.

    Returns a dict:
      text            -- possibly-corrected text
      status          -- "corrected" | "needs_review" | "unchanged"
      matched_label   -- the known label it was compared against, if any
      score           -- best similarity score found (0-100)
    """
    if not text or not text.strip():
        return {"text": text, "status": "unchanged", "matched_label": None, "score": 0}

    best_label = None
    best_score = 0

    for label in known_labels:
        whole_score = fuzz.ratio(text, label)
        prefix = text[: len(label)]
        prefix_score = fuzz.ratio(prefix, label)
        score = max(whole_score, prefix_score)

        if score > best_score:
            best_score = score
            best_label = label

    if best_label is None or best_score < suggestion_threshold:
        return {"text": text, "status": "unchanged", "matched_label": None, "score": best_score}

    if best_score < threshold:
        return {
            "text": text,
            "status": "needs_review",
            "matched_label": best_label,
            "score": best_score,
        }

    if fuzz.ratio(text, best_label) >= fuzz.ratio(text[: len(best_label)], best_label):
        corrected = best_label
    else:
        remainder = text[len(best_label):]
        corrected = (best_label + remainder).rstrip()

    return {"text": corrected, "status": "corrected", "matched_label": best_label, "score": best_score}


# ============================================================
# 2. MARKS-TABLE PARSING
# ============================================================
#
# Surya's clean_html() flattens each table cell with " | " (from
# </td>/</th>) and preserves internal <br> line-wraps as "\n" WITHIN
# a cell. Blank cells (e.g. the Work Experience row, which has no
# Theory/IA/Total/Words marks) still produce an empty-but-present
# token -- critically, we must NOT drop those empty tokens, or every
# row after a blank-cell row would shift out of alignment.
#
# Body rows are a fixed width of 7 cells:
#   [subject_code, subject_name, theory, ia_pr, total, total_words, grade]
#
# We locate where the header ends and body rows begin by finding the
# first token that looks like a 3-digit subject code, rather than
# hardcoding a header cell count -- this is more robust to header
# wording/structure varying slightly between documents.
# ============================================================

ROW_WIDTH = 7
SUBJECT_CODE_RE = re.compile(r"^\d{3}$")


def parse_marks_table_block(block_text, row_width=ROW_WIDTH):
    """
    Parse a flattened Surya table block into a list of row dicts.
    Returns [] if this doesn't look like a marks table at all.
    """
    if not block_text or "|" not in block_text:
        return []

    raw_tokens = [t.strip() for t in block_text.split("|")]
    if raw_tokens and raw_tokens[-1] == "":
        raw_tokens = raw_tokens[:-1]

    start_index = None
    for i, token in enumerate(raw_tokens):
        if SUBJECT_CODE_RE.fullmatch(token):
            start_index = i
            break

    if start_index is None:
        return []

    body_tokens = raw_tokens[start_index:]

    rows = []
    for i in range(0, len(body_tokens), row_width):
        chunk = body_tokens[i:i + row_width]
        if len(chunk) < row_width:
            break  # incomplete trailing chunk (e.g. stray tokens after the table) -- ignore

        code, subject, theory, ia_pr, total, words, grade = chunk

        if not SUBJECT_CODE_RE.fullmatch(code):
            break  # alignment drifted -- stop rather than emit garbage rows

        rows.append({
            "subject_code": code,
            "subject_name": subject,
            "theory": theory,
            "ia_pr": ia_pr,
            "total": total,
            "total_words": words,
            "grade": grade,
        })

    return rows


def looks_like_marks_table(block_text):
    """Cheap pre-check before bothering to parse a block."""
    if not block_text:
        return False
    return bool(re.search(r"\b\d{3}\b\s*\|", block_text))


def rebuild_marks_table_text(rows):
    """
    Rebuild a clean, human-readable representation of the table body
    after correction -- one row per line, pipe-separated, in the same
    column order Surya used. This replaces the block's raw HTML-
    flattened text with something unambiguous and directly usable.
    """
    lines = []
    for row in rows:
        lines.append(
            " | ".join([
                row["subject_code"],
                row["subject_name"],
                row["theory"],
                row["ia_pr"],
                row["total"],
                row["total_words"],
                row["grade"],
            ])
        )
    return "\n".join(lines)


# ============================================================
# 3. NUMERIC CROSS-VALIDATION
# ============================================================

_ONES = {
    "ZERO": 0, "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5,
    "SIX": 6, "SEVEN": 7, "EIGHT": 8, "NINE": 9, "TEN": 10,
    "ELEVEN": 11, "TWELVE": 12, "THIRTEEN": 13, "FOURTEEN": 14,
    "FIFTEEN": 15, "SIXTEEN": 16, "SEVENTEEN": 17, "EIGHTEEN": 18,
    "NINETEEN": 19,
}

_TENS = {
    "TWENTY": 20, "THIRTY": 30, "FORTY": 40, "FIFTY": 50,
    "SIXTY": 60, "SEVENTY": 70, "EIGHTY": 80, "NINETY": 90,
}


def words_to_number(phrase):
    """
    Parse a spelled-out number like "NINETY ONE" or "SIXTY FOUR" or
    "HUNDRED" into an int. Returns None if it doesn't parse cleanly
    (safer to skip a row than to silently misinterpret it).
    """
    if not phrase:
        return None

    words = re.findall(r"[A-Za-z]+", phrase.upper())
    if not words:
        return None

    total = 0
    for word in words:
        if word == "HUNDRED":
            total = (total or 1) * 100
        elif word in _TENS:
            total += _TENS[word]
        elif word in _ONES:
            total += _ONES[word]
        else:
            return None  # unrecognized token -- don't guess

    return total


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def validate_and_correct_marks_row(row):
    """
    Cross-check one marks-table row dict (as produced by
    parse_marks_table_block). Returns a NEW row dict with corrected
    values applied where confidently determinable, plus an "issue"
    field describing what (if anything) was found.
    """
    result = dict(row)
    result["issue"] = None

    theory_n = _to_int(row["theory"])
    ia_n = _to_int(row["ia_pr"])
    total_n = _to_int(row["total"])
    words_n = words_to_number(row["total_words"])

    computed_n = None
    if theory_n is not None and ia_n is not None:
        computed_n = theory_n + ia_n

    signals = [v for v in (total_n, words_n, computed_n) if v is not None]

    if not signals:
        return result  # nothing numeric on this row (e.g. Work Experience) -- nothing to check

    if len(set(signals)) == 1:
        return result  # everything agrees -- no issue

    counts = Counter(signals)
    most_common_value, most_common_count = counts.most_common(1)[0]

    if most_common_count >= 2:
        result["issue"] = (
            f"total={total_n}, words={words_n}, theory+IA={computed_n} disagreed; "
            f"corrected to agreed value {most_common_value}"
        )
        if total_n != most_common_value:
            # Preserve the original digit width (e.g. "068" -> "058", not "58")
            width = len(row["total"]) if row["total"] else len(str(most_common_value))
            result["total"] = str(most_common_value).zfill(width)
    else:
        result["issue"] = (
            f"all three signals disagree (total={total_n}, words={words_n}, "
            f"theory+IA={computed_n}) -- needs manual review"
        )

    return result


def correct_marks_table_block(block_text):
    """
    Full pipeline for one table block: parse -> validate/correct each
    row -> rebuild text. Returns (corrected_text, rows_with_issues).
    If the block doesn't parse as a table, returns (original_text, []).
    """
    rows = parse_marks_table_block(block_text)
    if not rows:
        return block_text, []

    corrected_rows = [validate_and_correct_marks_row(r) for r in rows]
    rows_with_issues = [r for r in corrected_rows if r["issue"]]

    corrected_text = rebuild_marks_table_text(corrected_rows)
    return corrected_text, rows_with_issues


# ============================================================
# 4. SINGLE ENTRY POINT
# ============================================================

def apply_corrections(final_result):
    """
    Run both correction strategies over a Surya OCR result dict (the
    same shape SuryaOCRService.run_ocr() returns: {"results": [...],
    ...}). Returns a NEW result dict (input is not mutated) plus a
    report describing every change and every item flagged for review.

    Usage:
        corrected_result, report = apply_corrections(final_result)
    """
    report = {
        "labels_corrected": [],
        "labels_needing_review": [],
        "marks_table_issues": [],
    }

    new_results = []

    for item in final_result.get("results", []):
        new_item = dict(item)
        text = new_item.get("text", "")

        if looks_like_marks_table(text):
            corrected_text, rows_with_issues = correct_marks_table_block(text)
            if rows_with_issues:
                new_item["text"] = corrected_text
                for row in rows_with_issues:
                    report["marks_table_issues"].append({
                        "subject_code": row["subject_code"],
                        "subject_name": row["subject_name"],
                        "issue": row["issue"],
                    })
            new_results.append(new_item)
            continue

        label_result = correct_known_labels(text)

        if label_result["status"] == "corrected" and label_result["text"] != text:
            new_item["text"] = label_result["text"]
            report["labels_corrected"].append({
                "original": text,
                "corrected": label_result["text"],
                "score": label_result["score"],
            })
        elif label_result["status"] == "needs_review":
            report["labels_needing_review"].append({
                "text": text,
                "suggested_label": label_result["matched_label"],
                "score": label_result["score"],
            })

        new_results.append(new_item)

    new_final_result = dict(final_result)
    new_final_result["results"] = new_results

    return new_final_result, report