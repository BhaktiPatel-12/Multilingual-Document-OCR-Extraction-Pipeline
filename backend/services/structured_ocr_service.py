"""
Astra Structured OCR Service (generalized)
==========================================

Converts the JSON produced by the Astra / Surya OCR pipeline into a clean
structured.json with fields, tables, key/value pairs and paragraphs,
separated per DOCUMENT (a PDF may contain several documents) and per PAGE.

Accepted input shapes
---------------------
1. Pipeline output   : {"pages": [{"page_number": 1, "ocr_result": {"results": [...]}}, ...]}
                       (falls back to level2.final_result / level1.result / page["text"])
2. Flat Surya output : {"results": [ {text, bbox, label, page, ...}, ... ]}
3. A bare list of blocks.

Usage
-----
    python astra_structured_ocr.py input.json [output.json] [--split auto|page|single] [--detailed]

    --split auto   (default) detect document boundaries between pages
    --split page   every page is its own document
    --split single the whole file is one document
    --detailed     keep bbox / confidence / raw values (verbose layout)

Default output layout
---------------------
    {"source": {...},
     "documents": [ {"document": 1, "type", "title", "issuer", "pages", "languages",
                     "confidence", "fields": {key: value}, "tables": [...], "text": [...]},
                    {"document": 2, ...} ],
     "metadata": {...}}
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
LATIN_RE = re.compile(r"[A-Za-z]")
NOT_WORD_END = r"(?![A-Za-z0-9\u0900-\u097F])"
SEP_CHARS = r"[\s./,:;'’\-_|*]*"

LANG_MAP = {"eng": "en", "en": "en", "hin": "hi", "hi": "hi", "guj": "gu", "gu": "gu",
            "mar": "mr", "mr": "mr", "ben": "bn", "bn": "bn", "tam": "ta", "ta": "ta",
            "tel": "te", "te": "te"}

NUMBER_WORDS = {
    "ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN",
    "ELEVEN", "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN", "SEVENTEEN",
    "EIGHTEEN", "NINETEEN", "TWENTY", "THIRTY", "FORTY", "FIFTY", "SIXTY", "SEVENTY",
    "EIGHTY", "NINETY", "HUNDRED", "THOUSAND", "LAKH", "CRORE", "AND", "ONLY", "RUPEES",
}

MONTHS = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
DATE_PATTERNS = [
    r"\b\d{1,4}[/\-.]\d{1,2}[/\-.]\d{1,4}\b",
    r"\b\d{1,2}(?:st|nd|rd|th)?[\s\-]+" + MONTHS + r"[\s,\-]+\d{2,4}\b",
    r"\b" + MONTHS + r"\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{2,4}\b",
]
DATE_RE = re.compile("|".join(DATE_PATTERNS), re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
URL_RE = re.compile(r"\b(?:https?://|www\.)[^\s]+", re.I)
GSTIN_RE = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b")
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
IFSC_RE = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")
PHONE_RE = re.compile(r"(?<![\d\w])\+?\d[\d\s\-()]{5,17}\d(?![\d\w])")
AMOUNT_RE = re.compile(
    r"(?:₹|rs\.?|inr|usd|\$|€|£)?\s*\d[\d,]*(?:\.\d+)?", re.I)
TIME_TAIL_RE = re.compile(r"[,\s]*\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp]\.?[Mm]\.?)?")
DEVANAGARI_RUN_RE = re.compile(r"[\u0900-\u097F]+(?:\s+[\u0900-\u097F]+)*")
# keys that may carry the page / image number of an OCR block
PAGE_KEYS = ("page_number", "page", "page_index", "page_no", "image_index", "image_id")


def has_devanagari(text):
    return bool(DEVANAGARI_RE.search(text or ""))


def latin_part(text):
    """Strip Devanagari characters (used to get the English part of a bilingual label)."""
    text = DEVANAGARI_RE.sub(" ", text or "")
    text = re.sub(r"\(\s*\)", " ", text)
    return re.sub(r"\s+", " ", text).strip(" :-,;").lstrip("./")


def slugify(text, max_len=60):
    text = (text or "").lower().replace("'", "").replace("’", "")
    text = re.sub(r"[^\w\u0900-\u097F]+", "_", text, flags=re.UNICODE).strip("_")
    return text[:max_len]


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ----------------------------------------------------------------------------
# Field definitions (extend freely - this is the only place you need to edit
# to teach the service new labels).
#   type: text | name | identifier | date | number | phone | email | any
# ----------------------------------------------------------------------------

FIELD_DEFINITIONS = {
    # ---- person / identity ------------------------------------------------
    "name": {"type": "name", "labels": [
        "name of candidate", "name of conditate", "candidate name", "name of student",
        "student name", "this is to certify that", "name", "full name", "नाम", "नाम"]},
    "mother_name": {"type": "name", "labels": ["mother's name", "mother name", "माता का नाम"]},
    "father_guardian_name": {"type": "name", "labels": [
        "father's / guardian's name", "father/guardian's name", "father / guardian name",
        "father's name", "father name", "guardian's name", "guardian name",
        "पिता/संरक्षक का नाम", "पिता/परिवार का नाम", "पिता का नाम"]},
    "spouse_name": {"type": "name", "labels": ["husband's name", "spouse name", "wife's name"]},
    "date_of_birth": {"type": "date", "labels": [
        "date of birth", "date-of-birth", "d.o.b", "dob", "birth date", "जन्म तिथि", "जन्म दिनांक"]},
    "gender": {"type": "text", "labels": ["gender", "sex", "लिंग"]},
    "nationality": {"type": "text", "labels": ["nationality"]},
    "blood_group": {"type": "text", "labels": ["blood group"]},
    "aadhaar_number": {"type": "identifier", "labels": ["aadhaar number", "aadhaar no", "aadhar no", "uid"]},
    "pan_number": {"type": "identifier", "labels": ["pan number", "pan no", "permanent account number", "pan"]},
    "passport_number": {"type": "identifier", "labels": ["passport number", "passport no"]},

    # ---- education / certificates -----------------------------------------
    "roll_number": {"type": "identifier", "labels": ["roll number", "roll no", "roll", "अनुक्रमांक"]},
    "registration_number": {"type": "identifier", "labels": [
        "registration number", "registration no", "regn number", "regn no", "regn.no",
        "रजि. नं. regn.no", "रजि. नं.", "रजि नं", "reg no"]},
    "enrollment_number": {"type": "identifier", "labels": [
        "enrollment no", "enrollment number", "enrolment no", "enrolment number"]},
    "seat_number": {"type": "identifier", "labels": ["seat no", "seat number"]},
    "serial_number": {"type": "identifier", "labels": ["sr no", "sr. no", "serial no", "serial number", "sl no"]},
    "school": {"type": "text", "labels": ["school name", "school", "विद्यालय"]},
    "college": {"type": "text", "labels": ["college name", "college", "institute", "institution"]},
    "programme": {"type": "text", "labels": ["programme", "program", "degree"]},
    "faculty": {"type": "text", "labels": ["faculty", "department", "branch"]},
    "semester": {"type": "text", "labels": ["semester", "sem"]},
    "examination": {"type": "text", "labels": ["examination", "exam"]},
    "result": {"type": "text", "labels": ["result", "परिणाम"]},
    "grade_obtained": {"type": "text", "labels": ["grade obtained", "overall grade"]},
    "class_obtained": {"type": "text", "labels": ["class obtained", "division"]},
    "percentage": {"type": "number", "labels": ["percentage", "percent"]},
    "cgpa": {"type": "number", "labels": ["cgpa"]},
    "sgpa": {"type": "number", "labels": ["sgpa"]},

    # ---- invoice / billing ---------------------------------------------------
    "invoice_number": {"type": "identifier", "labels": [
        "invoice number", "invoice no", "invoice id", "invoice #", "bill no", "bill number", "receipt no"]},
    "invoice_date": {"type": "date", "labels": ["invoice date", "bill date", "date of issue", "receipt date"]},
    "due_date": {"type": "date", "labels": ["due date", "payment due", "pay by"]},
    "po_number": {"type": "identifier", "labels": ["po number", "po no", "purchase order no", "purchase order number"]},
    "gstin": {"type": "identifier", "labels": ["gstin", "gst no", "gst number", "gst in", "gst"]},
    "vendor": {"type": "text", "labels": ["sold by", "seller", "vendor", "supplier", "from"]},
    "customer": {"type": "text", "labels": ["billed to", "bill to", "customer name", "customer", "buyer", "sold to", "client"]},
    "ship_to": {"type": "text", "labels": ["ship to", "shipped to", "delivery address", "shipping address"]},
    "subtotal": {"type": "number", "labels": ["sub total", "subtotal", "taxable value", "taxable amount"]},
    "discount": {"type": "number", "labels": ["discount"]},
    "cgst": {"type": "number", "labels": ["cgst"]},
    "sgst": {"type": "number", "labels": ["sgst"]},
    "igst": {"type": "number", "labels": ["igst"]},
    "tax": {"type": "number", "labels": ["total tax", "tax amount", "tax", "vat"]},
    "amount_in_words": {"type": "text", "labels": ["amount in words", "total in words", "rupees in words"]},
    "amount_due": {"type": "number", "labels": [
        "amount due", "amount payable", "payable amount", "net payable", "total due"]},
    "balance_due": {"type": "number", "labels": [
        "balance due", "balance amount", "balance payable", "outstanding amount", "outstanding",
        "pending amount", "balance"]},
    "amount_paid": {"type": "number", "labels": [
        "amount paid", "paid amount", "total paid", "amount received", "received amount", "paid"]},
    "advance_paid": {"type": "number", "labels": ["advance paid", "advance amount", "advance"]},
    "round_off": {"type": "number", "labels": ["round off", "rounding off", "rounding", "roundoff"]},
    "shipping_charges": {"type": "number", "labels": [
        "shipping charges", "shipping charge", "delivery charges", "shipping", "freight"]},
    "total": {"type": "number", "labels": [
        "grand total", "total amount", "amount total", "net total", "invoice total", "total value",
        "total payable", "total", "TOTAL", "कुल"]},
    "amount": {"type": "number", "labels": ["amount", "कुल राशि", "राशि"]},
    "transaction_id": {"type": "identifier", "labels": [
        "transaction id", "transaction no", "transaction number", "txn id", "txn no",
        "utr no", "utr number", "payment id", "reference no", "reference number", "ref no"]},
    "payment_status": {"type": "text", "labels": ["payment status", "transaction status", "status of payment"]},
    "payment_date": {"type": "date", "labels": ["payment date", "date of payment", "transaction date", "paid on"]},
    "application_number": {"type": "identifier", "labels": [
        "application number", "application no", "application id", "applicant id"]},
    "application_date": {"type": "date", "labels": ["application date", "date of application"]},
    "application_type": {"type": "text", "labels": ["application type", "type of application"]},
    "class": {"type": "text", "labels": ["class"]},
    "payment_method": {"type": "text", "labels": ["payment method", "payment mode", "mode of payment"]},
    "payment_terms": {"type": "text", "labels": ["payment terms", "terms"]},
    "bank_name": {"type": "text", "labels": ["bank name", "bank"]},
    "account_number": {"type": "identifier", "labels": ["account number", "account no", "a/c no", "acc no"]},
    "ifsc": {"type": "identifier", "labels": ["ifsc code", "ifsc"]},

    # ---- contact / generic ----------------------------------------------------
    "address": {"type": "text", "labels": ["residential address", "permanent address", "address", "पता"]},
    "phone": {"type": "phone", "labels": [
        "phone number", "phone no", "phone", "mobile number", "mobile no", "mobile", "contact number", "telephone", "tel"]},
    "email": {"type": "email", "labels": ["email address", "e-mail address", "email id", "email", "e-mail"]},
    "website": {"type": "any", "labels": ["website", "web"]},
    "date": {"type": "date", "labels": ["dated", "date", "दिनांक"]},
    "place": {"type": "text", "labels": ["place"]},
    "designation": {"type": "text", "labels": ["designation", "job title", "position"]},
    "company": {"type": "text", "labels": ["company name", "company", "organisation", "organization"]},
}

# Fields where, if repeated across pages of one document, the LAST value wins.
LAST_PAGE_WINS = {"total", "amount_due", "balance_due", "amount_paid", "amount_in_words", "subtotal",
                  "tax", "cgst", "sgst", "igst", "discount", "result", "grade_obtained", "class_obtained"}

# Fields scanned for inside tables (summary rows such as Total / Paid / Balance Due)
SUMMARY_FIELDS = {"total", "subtotal", "discount", "cgst", "sgst", "igst", "tax", "amount_due",
                  "balance_due", "amount_paid", "advance_paid", "round_off", "shipping_charges"}
AMOUNT_ONLY_RE = re.compile(r"^(?:₹|rs\.?|inr|usd|\$|€|£)?\s*\(?-?\d[\d,]*(?:\.\d+)?\)?\s*(?:/-)?$", re.I)
SUMMARY_TOKEN_OK_RE = re.compile(r"^(?:₹|rs\.?|inr|usd|\$|€|£|/-|only|-|@?\(?\d[\d,.]*%?\)?)$", re.I)

# Fields that identify a document - used to detect a new document in the next page.
IDENTITY_FIELDS = ["invoice_number", "enrollment_number", "roll_number", "registration_number",
                   "account_number", "serial_number", "seat_number", "po_number"]

# ----------------------------------------------------------------------------
# Document-type scoring
# ----------------------------------------------------------------------------

DOC_TYPES = {
    "marks_statement": ["marks statement", "statement of marks", "marksheet", "mark sheet",
                        "grade card", "scholastic", "obtained marks", "marks obtained",
                        "अंक विवरणिका", "sgpa", "cgpa", "examination"],
    "certificate": ["certificate", "प्रमाण पत्र", "this is to certify", "certify that"],
    "invoice": ["invoice", "tax invoice", "bill to", "billed to", "gstin", "subtotal", "sub total",
                "amount due", "balance due", "invoice no", "hsn"],
    "receipt": ["receipt", "payment received", "received with thanks"],
    "purchase_order": ["purchase order", "po number"],
    "resume": ["resume", "curriculum vitae", "work experience", "skills", "objective"],
    "id_card": ["identity card", "aadhaar", "driving licence", "driving license", "election commission",
                "income tax department", "passport"],
    "bank_statement": ["bank statement", "account statement", "opening balance", "closing balance", "ifsc"],
    "application_form": ["application form", "admission", "applicant", "revaluation", "re-evaluation",
                         "application type", "application date"],
    "report": ["report", "summary", "analysis"],
}
TITLE_KEYWORDS = ["statement of marks", "marks statement", "marksheet", "certificate", "invoice",
                  "receipt", "resume", "curriculum vitae", "purchase order", "bank statement",
                  "application form", "report card", "grade card", "transcript", "admit card",
                  "quotation", "agreement", "letter", "application", "revaluation"]
ORG_KEYWORDS = ["university", "board", "bank", "ltd", "pvt", "limited", "school", "college",
                "institute", "hospital", "corporation", "council", "department", "ministry",
                "enterprises", "industries", "company", "trust", "academy", "services", "solutions"]

HEADER_WORDS = {"description", "item", "items", "amount", "qty", "quantity", "price", "rate", "total",
                "particulars", "details", "value", "unit", "hsn", "sr", "no", "sl", "tax", "discount",
                "subject", "credit", "grade", "marks", "date", "balance", "debit"}


# ----------------------------------------------------------------------------
# Label matcher
# ----------------------------------------------------------------------------

def _word_pattern(word):
    """Regex for one label word, tolerant to optional apostrophes and OCR tail duplication
    (e.g. 'Nameme' for 'Name')."""
    if DEVANAGARI_RE.search(word):
        return re.escape(word)
    chars = "".join(re.escape(c) + r"['’]?" for c in word)
    tail = ""
    if len(word) >= 3:
        tail = r"(?:" + re.escape(word[-2:]) + "|" + re.escape(word[-1]) + r")?"
    return chars + tail


def _label_regex(label):
    label = label.lower().replace("’", "'")
    label = re.sub(r"[.:;,/*\\()\-]+", " ", label).replace("'", "")
    words = [w for w in label.split() if w]
    return SEP_CHARS.join(_word_pattern(w) for w in words), len(words)


class LabelMatcher:
    def __init__(self, definitions):
        self.entries = []
        for field, spec in definitions.items():
            for label in spec["labels"]:
                body, n_words = _label_regex(label)
                if not body:
                    continue
                self.entries.append({
                    "field": field,
                    "label": label,
                    "words": n_words,
                    "len": len(label),
                    "regex": re.compile(
                        r"^\s*(?P<label>" + body + r")" + NOT_WORD_END +
                        r"(?P<sep>\.?\s*[:：]\s*|\.?\s*[-–]\s+|\.?\s+|\.?$)(?P<rest>.*)$",
                        re.I | re.S),
                })
        self.entries.sort(key=lambda e: (-e["len"], -e["words"]))
        self.colon_regex = re.compile(
            r"(?:(?<=\s)|^)(?:" + "|".join(
                _label_regex(e["label"])[0] for e in self.entries if e["words"] >= 1
            ) + r")\s*[:：]", re.I)

    def match(self, text):
        """Return dict(field,label,rest,has_colon,words) or None for a text starting with a known label."""
        if not text:
            return None
        text = text.strip()
        for e in self.entries:
            m = e["regex"].match(text)
            if m:
                return {
                    "field": e["field"],
                    "label_text": m.group("label").strip(),
                    "canonical_label": e["label"],
                    "rest": m.group("rest").strip(),
                    "has_colon": ":" in m.group("sep") or "：" in m.group("sep"),
                    "words": e["words"],
                }
        return None


# ----------------------------------------------------------------------------
# Main service
# ----------------------------------------------------------------------------

class AstraStructuredOCRService:

    def __init__(self, split_mode="auto", detailed=False):
        self.matcher = LabelMatcher(FIELD_DEFINITIONS)
        self.split_mode = split_mode
        self.detailed = detailed  # True -> keep bbox / confidence / raw data (old verbose layout)

    # ------------------------------------------------------------------
    # INPUT ADAPTER
    # ------------------------------------------------------------------

    def load_pages(self, data):
        """Return (source_info, pages) where pages = [{'page_number','blocks','languages','quality'}]."""
        source = {}
        pages = []

        if isinstance(data, list):
            pages = self._group_flat_blocks(data)
            return source, pages

        if not isinstance(data, dict):
            raise ValueError("Input JSON must be an object or a list of blocks.")

        doc = data.get("document") or {}
        if isinstance(doc, dict):
            source = {k: doc.get(k) for k in ("filename", "file_type", "pdf_id") if doc.get(k)}
        if "processing" in data and isinstance(data["processing"], dict):
            source["total_pages"] = data["processing"].get("total_pages")
        if data.get("source_json"):
            source["source_json"] = data["source_json"]

        if isinstance(data.get("pages"), list):
            for idx, page in enumerate(data["pages"], start=1):
                pages.extend(self._load_page_entry(page, idx))
            if any(p.get("split") for p in pages):
                self._renumber(pages)
            return source, pages

        if isinstance(data.get("results"), list):
            return source, self._group_flat_blocks(data["results"], data)

        raise ValueError("Could not find 'pages' or 'results' in the input JSON.")

    def _load_page_entry(self, page, fallback_number):
        """Return a LIST of pages: normally one, several when images were merged into one page."""
        number = page.get("page_number") or page.get("page") or fallback_number
        raw_blocks = self._dig(page, [
            ("ocr_result", "results"), ("results",), ("blocks",),
            ("level2", "final_result", "results"), ("level1", "result", "results"),
        ])
        langs = page.get("detected_languages") or (page.get("ocr_result") or {}).get("detected_languages") or []
        quality = (page.get("quality") or {}).get("quality_score")

        segments = self._split_by_restart(raw_blocks) if raw_blocks else [None]
        out = []
        for seg in segments:
            if raw_blocks:
                blocks = self._normalise_blocks(seg, number)
            elif page.get("text"):
                blocks = self._blocks_from_plain_text(page["text"], number)
            else:
                blocks = []
            out.append({"page_number": number, "blocks": blocks, "languages": self._norm_langs(langs),
                        "quality": quality, "split": len(segments) > 1})
        return out

    @staticmethod
    def _renumber(pages):
        for n, p in enumerate(pages, start=1):
            p["page_number"] = n
            for b in p["blocks"]:
                b["page"] = n

    @staticmethod
    def _explicit_page(b):
        for key in PAGE_KEYS:
            v = b.get(key)
            if v is not None and v != "":
                return v
        return None

    @staticmethod
    def _page_sort_key(k):
        return (isinstance(k, str), k if isinstance(k, (int, float)) else 0, str(k))

    @staticmethod
    def _split_by_restart(raw):
        """Several pages/images merged into ONE list: the reading order restarts (0,1,2,..,0,1,2,..).
        Returns a list of block-lists (one per page); [raw] when nothing needs splitting."""
        items = [b for b in raw if isinstance(b, dict)]
        orders = [b.get("reading_order") for b in items]
        if len(items) < 6 or any(isinstance(o, bool) or not isinstance(o, (int, float)) for o in orders):
            return [raw]
        lo = min(orders)
        cuts = [i for i in range(1, len(items)) if orders[i] == lo and orders[i - 1] > lo]
        if not cuts:
            return [raw]
        segments, start = [], 0
        for c in cuts + [len(items)]:
            segments.append(items[start:c])
            start = c
        for seg in segments:
            seg_orders = [b["reading_order"] for b in seg]
            if len(seg) < 3 or len(set(seg_orders)) != len(seg_orders):
                return [raw]
        return segments

    @staticmethod
    def _dig(obj, paths):
        for path in paths:
            cur = obj
            for key in path:
                cur = cur.get(key) if isinstance(cur, dict) else None
                if cur is None:
                    break
            if isinstance(cur, list) and cur:
                return cur
        return None

    def _group_flat_blocks(self, results, container=None):
        results = [b for b in results if isinstance(b, dict)]
        found = []
        for b in results:
            p = self._explicit_page(b)
            if p is not None and p not in found:
                found.append(p)
        if len(found) >= 2:                      # blocks carry real page numbers
            grouped = {}
            for b in results:
                p = self._explicit_page(b)
                grouped.setdefault(found[0] if p is None else p, []).append(b)
            groups = [(k, grouped[k]) for k in sorted(grouped, key=self._page_sort_key)]
        else:                                    # no page info: detect restarts of the reading order
            segments = self._split_by_restart(results)
            if len(segments) > 1:
                groups = [(i, seg) for i, seg in enumerate(segments, start=1)]
            else:
                groups = [(found[0] if found else 1, results)]
        pages = []
        for number, raw in groups:
            blocks = self._normalise_blocks(raw, number)
            langs = []
            if container and len(groups) == 1:
                langs = container.get("detected_languages") or []
            pages.append({"page_number": number, "blocks": blocks,
                          "languages": self._norm_langs(langs) or self._langs_from_blocks(blocks),
                          "quality": None})
        return pages

    def _normalise_blocks(self, raw_blocks, page_number):
        blocks = []
        for i, b in enumerate(raw_blocks):
            if not isinstance(b, dict):
                continue
            text = b.get("text")
            if text is None or not str(text).strip():
                continue
            label = str(b.get("label") or b.get("raw_label") or "Text")
            blocks.append({
                "id": len(blocks),
                "text": str(text).replace("\r", ""),
                "label": label,
                "is_table": label.lower() == "table" or str(b.get("raw_label", "")).lower() == "table",
                "bbox": [to_float(v) for v in (b.get("bbox") or [])[:4]],
                "confidence": round(to_float(b.get("confidence")), 4),
                "language": b.get("language"),
                "reading_order": b.get("reading_order", i),
                "page": page_number,  # authoritative page number (outer one)
            })
        blocks.sort(key=lambda x: (x["reading_order"] if x["reading_order"] is not None else 0, x["id"]))
        for i, b in enumerate(blocks):
            b["id"] = i
        return blocks

    def _blocks_from_plain_text(self, text, page_number):
        paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
        return [{"id": i, "text": p, "label": "Text", "is_table": False, "bbox": [],
                 "confidence": 0.0, "language": None, "reading_order": i, "page": page_number}
                for i, p in enumerate(paras)]

    @staticmethod
    def _norm_langs(langs):
        out = []
        for l in langs or []:
            code = LANG_MAP.get(str(l).lower())
            if code and code not in out:
                out.append(code)
        return out

    def _langs_from_blocks(self, blocks):
        return self._norm_langs(sorted({b["language"] for b in blocks if b.get("language")}))

    # ------------------------------------------------------------------
    # VALUE VALIDATION / CLEANING
    # ------------------------------------------------------------------

    @staticmethod
    def clean_value(value):
        if value is None:
            return ""
        value = re.sub(r"\s+", " ", str(value).replace("\n", " ")).strip()
        return re.sub(r"^[\s:;,.\-–—*|]+", "", value).strip()

    def refine_value(self, ftype, raw):
        """Return (value, ok)."""
        raw = self.clean_value(raw)
        if not raw:
            return None, False
        if ftype == "date":
            m = DATE_RE.search(raw)
            if not m:
                return None, False
            tail = TIME_TAIL_RE.match(raw[m.end():])
            return (m.group(0) + tail.group(0) if tail else m.group(0)), True
        if ftype == "email":
            m = EMAIL_RE.search(raw)
            return (m.group(0), True) if m else (None, False)
        if ftype == "phone":
            m = PHONE_RE.search(raw)
            if m and 7 <= len(re.sub(r"\D", "", m.group(0))) <= 15:
                return m.group(0).strip(), True
            return None, False
        if ftype == "number":
            m = AMOUNT_RE.search(raw)
            return (m.group(0).strip(), True) if m else (None, False)
        if ftype == "identifier":
            if not re.search(r"\d", raw):
                return None, False
            tokens = raw.split()
            return (raw if len(tokens) <= 2 else tokens[0]), True
        if ftype == "name":
            if re.search(r"\d", raw) or len(raw) < 2:
                return None, False
            return raw, True
        return raw, True

    # ------------------------------------------------------------------
    # LINE STREAM (non-table blocks flattened to lines, in reading order)
    # ------------------------------------------------------------------

    def _line_stream(self, blocks):
        stream = []
        for b in blocks:
            if b["is_table"]:
                continue
            lines = [l.strip() for l in b["text"].split("\n") if l.strip()]
            for li, line in enumerate(lines):
                stream.append({"text": line, "block": b, "line_idx": li, "n_lines": len(lines)})
        return stream

    def _split_multi_pairs(self, line):
        """'Invoice No: 12  Date: 01/02/2024' -> ['Invoice No: 12', 'Date: 01/02/2024']"""
        starts = [m.start() for m in self.matcher.colon_regex.finditer(line)]
        if len(starts) < 2:
            return [line]
        if starts[0] != 0 and line[:starts[0]].strip():
            starts = [0] + starts
        starts.append(len(line))
        return [line[starts[i]:starts[i + 1]].strip() for i in range(len(starts) - 1)
                if line[starts[i]:starts[i + 1]].strip()]

    def _match_line(self, line):
        """Known-label match at the start of a line with repeated bilingual labels stripped."""
        info = self.matcher.match(line)
        if not info:
            return None
        # strip repeated labels of the same field: "परिणाम Result PASS" -> "PASS"
        for _ in range(3):
            again = self.matcher.match(info["rest"]) if info["rest"] else None
            if again and again["field"] == info["field"]:
                info["rest"] = again["rest"]
                info["has_colon"] = info["has_colon"] or again["has_colon"]
                info["words"] = max(info["words"], again["words"])
            else:
                break
        info["rest"] = self.clean_value(info["rest"])
        return info

    def _accept_inline(self, info, line):
        """Guard against single-word labels firing inside ordinary sentences."""
        rest = info["rest"]
        if not rest:
            return True
        n_words = len(line.split())
        if info["has_colon"] or info["words"] >= 2 or has_devanagari(info["label_text"]):
            return n_words <= 40
        if n_words > 9:
            return False
        if rest[:1].islower():
            return False
        return True

    # ------------------------------------------------------------------
    # SPATIAL VALUE LOOKUP
    # ------------------------------------------------------------------

    def _spatial_value(self, blocks, label_block):
        lb = label_block["bbox"]
        if len(lb) < 4:
            return None
        lx1, ly1, lx2, ly2 = lb
        height = max(ly2 - ly1, 1)
        best, best_score = None, 0
        for b in blocks:
            if b is label_block or b["is_table"] or len(b["bbox"]) < 4:
                continue
            text = self.clean_value(b["text"])
            if not text or len(text.split()) > 12 or self.matcher.match(text):
                continue
            x1, y1, x2, y2 = b["bbox"]
            y_overlap = min(ly2, y2) - max(ly1, y1)
            score = 0
            if y_overlap > 0.5 * height and x1 >= lx2 - 5:            # to the right, same row
                score = 100 - min(x1 - lx2, 99)
            elif 0 <= y1 - ly2 <= 1.5 * height and min(lx2, x2) - max(lx1, x1) > 0:  # right below
                score = 60 - min(y1 - ly2, 59)
            if score > best_score:
                best, best_score = b, score
        return best

    # ------------------------------------------------------------------
    # FIELD EXTRACTION FROM TEXT LINES
    # ------------------------------------------------------------------

    def _make_field(self, label, value, raw_value, conf, block, method, known, alt_labels=None):
        f = {
            "label": label,
            "value": value,
            "confidence": round(conf, 4),
            "page": block["page"],
            "bbox": block["bbox"],
            "method": method,
            "known_label": known,
        }
        if raw_value and raw_value != value:
            f["raw_value"] = raw_value
        if alt_labels:
            f["alt_labels"] = alt_labels
        return f

    def _store(self, fields, key, new):
        old = fields.get(key)
        if old is None:
            fields[key] = new
            return
        if new["confidence"] > old["confidence"] or (
                new["confidence"] == old["confidence"] and len(str(new["value"])) > len(str(old["value"]))):
            new.setdefault("alt_labels", [])
            fields[key] = new

    def extract_from_lines(self, blocks, stream, used, fields, pairs):
        i = 0
        pending_alt = {}
        while i < len(stream):
            entry = stream[i]
            line = entry["text"]
            block = entry["block"]

            for seg in self._split_multi_pairs(line):
                info = self._match_line(seg)
                if info and self._accept_inline(info, seg):
                    self._handle_known(blocks, stream, i, entry, seg, info, used, fields, pairs, pending_alt)
                else:
                    self._handle_generic(entry, seg, used, fields, pairs)
            i += 1

    def _handle_known(self, blocks, stream, i, entry, seg, info, used, fields, pairs, pending_alt):
        block = entry["block"]
        field = info["field"]
        ftype = FIELD_DEFINITIONS[field]["type"]
        rest = info["rest"]
        value_block = None
        value_conf = block["confidence"]
        method = "inline"

        # --- label only: value comes from next line / spatial neighbour --------
        if not rest:
            nxt = stream[i + 1] if i + 1 < len(stream) else None
            if nxt is not None:
                nxt_info = self._match_line(nxt["text"])
                if nxt_info and nxt_info["field"] == field:
                    # Bilingual label (e.g. Hindi label above English "Roll No. 123"): the next line carries it.
                    pending_alt.setdefault(i + 1, []).append(seg)
                    used.add((block["id"], entry["line_idx"]))
                    return
                if nxt_info is None and self._adjacent(entry, nxt):
                    rest = self.clean_value(nxt["text"])
                    value_block, value_conf, method = nxt["block"], nxt["block"]["confidence"], "next_line"
                    used.add((nxt["block"]["id"], nxt["line_idx"]))
            if not rest:
                vb = self._spatial_value(blocks, block)
                if vb:
                    rest = self.clean_value(vb["text"])
                    value_block, value_conf, method = vb, vb["confidence"], "spatial"
                    for li in range(len(vb["text"].split("\n"))):
                        used.add((vb["id"], li))

        value, ok = self.refine_value(ftype, rest)
        if not ok:
            return
        used.add((block["id"], entry["line_idx"]))
        label = info["label_text"]
        conf = (block["confidence"] + value_conf) / 2 if value_block else block["confidence"]
        alt = pending_alt.pop(i, None)
        new = self._make_field(label, value, rest, conf, value_block or block, method, True, alt)
        self._store(fields, field, new)
        pairs.append({"key": field, "label": label, "value": value, "confidence": round(conf, 4),
                      "page": block["page"], "known_label": True})

    @staticmethod
    def _adjacent(a, b):
        """True when line b is the visual continuation of line a (same block or close below)."""
        if a["block"]["id"] == b["block"]["id"]:
            return True
        ab, bb = a["block"]["bbox"], b["block"]["bbox"]
        if len(ab) < 4 or len(bb) < 4:
            return True
        height = max(ab[3] - ab[1], 1)
        return -height <= bb[1] - ab[3] <= 2.5 * height

    def _handle_generic(self, entry, seg, used, fields, pairs):
        """Generic 'Label : value' detection for labels unknown to the dictionary."""
        if ":" not in seg or "://" in seg:
            return
        left, right = seg.split(":", 1)
        left, right = left.strip(), self.clean_value(right)
        if not left or not right or len(right) > 120:
            return
        if re.fullmatch(r"\d{1,2}", left) and re.fullmatch(r"\d{2}(:\d{2})?", right):
            return  # time
        if len(left.split()) > 6 or len(left) > 50 or not LATIN_RE.search(left):
            return
        if len(right.split()) > 14:
            return  # long sentences are notes/paragraphs, not fields
        if left.replace(".", "").replace("/", "").isupper() and len(left) <= 8 and has_devanagari(right):
            return  # abbreviation legend such as "IA : आंतरिक मूल्यांकन Internal Assessment"
        if not re.match(r"^[A-Za-z\u0900-\u097F0-9 _./()'’\-&#]+$", left):
            return
        english = latin_part(left) or left
        key = slugify(english)
        if not key:
            return
        block = entry["block"]
        used.add((block["id"], entry["line_idx"]))
        pairs.append({"key": key, "label": left, "value": right, "confidence": block["confidence"],
                      "page": block["page"], "known_label": False})
        if key not in fields:
            fields[key] = self._make_field(left, right, None, block["confidence"], block, "colon", False)

    # ------------------------------------------------------------------
    # TABLES
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_table_text(text):
        """Accept HTML / markdown / tab separated table text as well: one cell per line, one row per group."""
        if re.search(r"</?(?:t[dhr]|table)\b", text, re.I):
            text = re.sub(r"</tr\s*>", "\n\n", text, flags=re.I)
            text = re.sub(r"</t[dh]\s*>", "\n", text, flags=re.I)
            text = re.sub(r"<[^>]+>", "", text)
        out = []
        for line in text.split("\n"):
            s = line.strip()
            if s and "-" in s and re.fullmatch(r"\|?[\s:\-|]+\|?", s):
                continue  # markdown separator row
            if "\t" in s or "|" in s:
                cells = [c.strip() for c in re.split(r"\t+|\s*\|\s*", s.strip("| \t")) if c.strip()]
                if len(cells) >= 2:
                    out.extend(cells)
                    out.append("")
                    continue
            out.append(line)
        return "\n".join(out)

    @staticmethod
    def _groups(text):
        text = AstraStructuredOCRService._normalise_table_text(text)
        groups, cur = [], []
        for line in text.split("\n"):
            line = line.strip()
            if line:
                cur.append(line)
            elif cur:
                groups.append(cur)
                cur = []
        if cur:
            groups.append(cur)
        return groups

    @staticmethod
    def _has_digit(group):
        return any(re.search(r"\d", l) for l in group)

    @staticmethod
    def _cell_kind(values):
        """Classify a column from its cell values."""
        vals = [v for v in values if v]
        if not vals:
            return "other"
        if all(re.fullmatch(r"[\d.,]+", v) for v in vals):
            return "num"
        if all(re.fullmatch(r"\d+\s*/\s*\d+", v) for v in vals):
            return "fraction"
        if all(DATE_RE.fullmatch(v) for v in vals):
            return "date"
        if all(re.fullmatch(r"[A-Za-z ]+", v) and all(w in NUMBER_WORDS for w in v.upper().split()) for v in vals):
            return "words"
        if all(re.fullmatch(r"[A-Z][0-9+\-]?\+?", v) and len(v) <= 3 for v in vals):
            return "grade"
        return "text"

    @staticmethod
    def _header_kind(h):
        l = h.lower().strip()
        if l.endswith("/"):
            return None
        if "word" in l:
            return "words"
        if "min" in l and "max" in l:
            return "fraction"
        if "grade" in l:
            return "grade"
        if "code" in l or "hsn" in l:
            return "num"
        if re.search(r"subject|name|description|item|particular|product|detail|title|semester", l):
            return "text"
        if "date" in l:
            return "date"
        if re.search(r"marks|theory|total|credit|qty|quantity|price|rate|amount|tax|gst|score|\bia\b|pt\.?|pr\.?|practical|internal|gpe|gpa", l):
            return "num"
        return None

    def _fit_headers(self, header_lines, columns):
        """Choose column names from a messy multi-line header, using data-column types."""
        n = len(columns)
        cleaned = []
        for l in header_lines:
            c = re.sub(r"\bI\s*A\s*/\s*", "IA/", latin_part(l))
            if c and re.search(r"[A-Za-z]", c):
                cleaned.append(c)
        # attach kind-less fragments ("SUB.", "POSITIONAL", "IA/") to the following header
        merged, carry = [], ""
        for c in cleaned:
            if self._header_kind(c) is None:
                carry = (carry + " " + c).strip()
                continue
            merged.append((carry + " " + c).strip())
            carry = ""
        if carry and merged:
            merged[-1] += " " + carry
        merged = [re.sub(r"^I\s*A\s*/\s*PT", "IA/PT", h) for h in merged]
        if len(merged) == n:
            return merged
        if len(merged) < n:
            return None
        kinds = [self._cell_kind(col) for col in columns]
        # surplus headers: drop generic group headers first
        while len(merged) > n:
            drop = next((h for h in merged if re.fullmatch(r"(?i)marks( obtained)?|obtained marks", h)), None)
            if drop is None:
                break
            merged.remove(drop)
        if len(merged) != n:
            # assign by kind
            pool = list(merged)
            result = []
            for k in kinds:
                pick = next((h for h in pool if (self._header_kind(h) == k or
                                                  (k in ("num", "fraction") and self._header_kind(h) == "num"))), None)
                if pick is None and pool:
                    pick = pool[0]
                if pick is None:
                    return None
                pool.remove(pick)
                result.append(pick)
            return result
        # same count after dropping: align by kind (header text order is not reliable in OCR output)
        pool, result = list(merged), []
        for k in kinds:
            pick = next((h for h in pool if self._header_kind(h) == k or
                         (k in ("num", "fraction") and self._header_kind(h) == "num")), None)
            if pick is None:
                pick = pool[0]
            pool.remove(pick)
            result.append(pick)
        return result

    def _make_unique(self, names):
        seen, out = Counter(), []
        for n in names:
            seen[n] += 1
            out.append(n if seen[n] == 1 else f"{n}_{seen[n]}")
        return out

    # ---- NEW: summary rows inside tables (Total / Paid / Balance Due ...) -----

    def parse_table(self, block, fields, pairs, used_unused=None, scan_summary=True):
        tables = self._parse_table_core(block, fields, pairs)
        if scan_summary:
            self._extract_table_summary(block, fields, pairs)
        return tables

    def _row_summary(self, cells):
        """Row like ['Total', '1,180.00'] or ['Total 1,180.00'] or ['CGST', '9%', '90.00'] -> (info, value)."""
        for idx, cell in enumerate(cells[:2]):
            info = self._match_line(cell)
            if not info or info["field"] not in SUMMARY_FIELDS:
                continue
            rest_tokens = info["rest"].split()
            if not all(SUMMARY_TOKEN_OK_RE.match(t) for t in rest_tokens):
                continue  # e.g. "Total Quantity 5", "Balance b/f"
            amounts = [t for t in rest_tokens if AMOUNT_ONLY_RE.match(t)]
            amounts += [self.clean_value(c) for c in cells[idx + 1:]
                        if AMOUNT_ONLY_RE.match(self.clean_value(c))]
            if amounts:
                return info, amounts[-1]
        return None

    def _extract_table_summary(self, block, fields, pairs):
        groups = self._groups(block["text"])
        found, i = [], 0
        while i < len(groups):
            g = groups[i]
            hit = self._row_summary(g)
            if hit:
                found.append(hit)
                i += 1
                continue
            # labels in one group, values in the next:  [Sub Total, Tax, Total] / [1000, 180, 1180]
            infos = [self._match_line(c) for c in g]
            if i + 1 < len(groups) and all(
                    inf and inf["field"] in SUMMARY_FIELDS and not inf["rest"] for inf in infos):
                vals = [self.clean_value(v) for v in groups[i + 1]]
                if len(vals) == len(g) and all(AMOUNT_ONLY_RE.match(v) for v in vals):
                    found.extend(zip(infos, vals))
                    i += 2
                    continue
            i += 1

        for info, value in found:
            field = info["field"]
            old = fields.get(field)
            if old and str(old["value"]) == value:
                continue
            new = self._make_field(info["label_text"], value, None, block["confidence"],
                                   block, "table_summary", True)
            if old and old.get("method") == "table_summary":
                fields[field] = new          # later summary row in tables wins
            else:
                self._store(fields, field, new)
            if not any(p["key"] == field and p["value"] == value and p["page"] == block["page"] for p in pairs):
                pairs.append({"key": field, "label": info["label_text"], "value": value,
                              "confidence": block["confidence"], "page": block["page"], "known_label": True})

    def _is_heading(self, text):
        t = latin_part(text) or text
        if re.search(r"\d", t) or len(t.split()) > 6 or len(t) > 60 or not LATIN_RE.search(t):
            return False
        return not self.matcher.match(text)

    def _split_sections(self, groups):
        """One table block that really holds several small tables, each introduced by a one-line heading
        ('Candidate Details', 'Transaction Details', ...). Returns (sections, heading_count, first_heading_index)."""
        sections = [{"title": None, "groups": []}]
        run, n_head, first_idx = None, 0, None
        for gi, g in enumerate(groups):
            if len(g) == 1 and gi + 1 < len(groups) and len(groups[gi + 1]) >= 2 and self._is_heading(g[0]):
                nxt = len(groups[gi + 1])
                if run is None or run == 2 or (run >= 3 and nxt != run):
                    n_head += 1
                    first_idx = gi if first_idx is None else first_idx
                    sections.append({"title": g[0], "groups": []})
                    run = None
                    continue
            sections[-1]["groups"].append(g)
            if len(g) >= 2:
                run = len(g)
        return [s for s in sections if s["groups"]], n_head, first_idx

    def _parse_table_core(self, block, fields, pairs):
        """Return list of table dicts; key/value tables also feed fields."""
        groups = self._groups(block["text"])
        base = {"page": block["page"], "bbox": block["bbox"], "confidence": block["confidence"],
                "raw_text": block["text"]}
        if not groups:
            return []

        # a one-line heading on top of the block ("Question Details") is the title of what follows
        lead = None
        if len(groups) > 1 and len(groups[0]) == 1 and len(groups[1]) >= 2 and self._is_heading(groups[0][0]):
            lead, groups = groups[0][0], groups[1:]

        sizes = Counter(len(g) for g in groups)
        mode_size, mode_count = sizes.most_common(1)[0]
        dominant_grid = mode_size >= 3 and mode_count >= 0.5 * len(groups)
        tables = None
        if not dominant_grid:
            sections, n_head, first_idx = self._split_sections(groups)
            if n_head >= 2:
                tables = []
                for s in sections:
                    for t in self._parse_groups(s["groups"], block, base, fields, pairs):
                        if s["title"]:
                            t["section"] = s["title"]
                        tables.append(t)
        if tables is None:
            tables = self._parse_groups(groups, block, base, fields, pairs)
        if lead:
            for t in tables:
                t.setdefault("section", lead)
        return tables

    def _parse_groups(self, groups, block, base, fields, pairs):
        if not groups:
            return []
        sizes = Counter(len(g) for g in groups)
        mode_size, mode_count = sizes.most_common(1)[0]

        # ---- 1. key / value table ---------------------------------------------
        all_pairs = all(len(g) >= 2 for g in groups) and max(len(g) for g in groups) <= 4 and mode_size == 2 \
            and sizes[2] == len(groups)
        if all_pairs and len(groups) >= 1:
            first_norm = [re.sub(r"[^a-z ]", "", l.lower()).split() for l in groups[0]]
            if all(any(w in HEADER_WORDS for w in ws) for ws in first_norm):
                all_pairs = False  # a two-column grid with a header row

        # ---- 2. grid with a dominant row size ---------------------------------
        grid_rows, header_lines, sections = None, [], {}
        n = None
        if not all_pairs and mode_count >= 2 and mode_size >= 3:
            n = mode_size
            first = next(i for i, g in enumerate(groups) if len(g) == n)
            header_groups = groups[:first]
            body = groups[first:]
            if not header_groups and not self._has_digit(body[0]) and len(body) > 1 and self._has_digit(body[1]):
                header_groups, body = [body[0]], body[1:]
            section = None
            rows = []
            for g in body:
                if len(g) == n:
                    rows.append((section, g))
                elif len(g) == 1:
                    section = g[0]
            grid_rows = rows
            header_lines = [l for g in header_groups for l in g]

            columns = list(zip(*[r for _, r in rows])) if rows else []
            names = None
            if header_groups and len(header_lines) == n:
                names = [latin_part(h) or h for h in header_lines]
            elif header_lines and columns:
                names = self._fit_headers(header_lines, columns)
            if not names:
                names = [f"column_{i + 1}" for i in range(n)]
            names = self._make_unique(names)
            out_rows = []
            for section, cells in rows:
                row = dict(zip(names, cells))
                if section:
                    row = {"section": section, **row}
                out_rows.append(row)
            return [dict(base, type="grid", columns=names, rows=out_rows, row_count=len(out_rows))]

        # ---- 3. header + rows of varying size (merged sub-tables) --------------
        if not all_pairs and len(groups) >= 2 and not self._has_digit(groups[0]) \
                and any(self._has_digit(g) for g in groups[1:]):
            header, rows = groups[0], groups[1:]
            segments, cur = [], []
            for l in header:
                if cur and l.lower() == header[0].lower():
                    segments.append(cur)
                    cur = []
                cur.append(l)
            segments.append(cur)
            segments = [[latin_part(h) or h for h in s] for s in segments]
            buckets = {i: [] for i in range(len(segments))}
            for r in rows:
                idx = min(range(len(segments)), key=lambda k: (abs(len(segments[k]) - len(r)),
                                                               len(r) > len(segments[k])))
                buckets[idx].append(r)
            tables = []
            for idx, seg in enumerate(segments):
                if not buckets[idx]:
                    continue
                cols = self._make_unique(seg)
                out_rows = [dict(zip(cols, r)) for r in buckets[idx]]
                tables.append(dict(base, type="grid", columns=cols, rows=out_rows, row_count=len(out_rows)))
            if tables:
                return tables

        # ---- key / value (default for label/value groups) ----------------------
        kv_items = []
        extras = []
        for g in groups:
            if len(g) >= 2 and not re.fullmatch(r"[\d.,/\s]+", g[0]):
                kv_items.append((g[0], g[1]))
                extras.extend(g[2:])
            else:
                extras.extend(g)
        if kv_items:
            for label, value in kv_items:
                self._add_table_pair(block, label, value, fields, pairs)
            return [dict(base, type="key_value", row_count=len(kv_items),
                         items=[{"label": l, "value": v} for l, v in kv_items],
                         extra_lines=extras)]
        return [dict(base, type="unparsed", row_count=0)]

    def _add_table_pair(self, block, label, value, fields, pairs):
        value = self.clean_value(value)
        info = self._match_line(label)
        if info and not info["rest"]:
            field = info["field"]
            v, ok = self.refine_value(FIELD_DEFINITIONS[field]["type"], value)
            if not ok:
                v = value
            key, known = field, True
        else:
            key, known, v = slugify(latin_part(label) or label), False, value
        if not key or not v:
            return
        new = self._make_field(label, v, value, block["confidence"], block, "table", known)
        self._store(fields, key, new) if known else fields.setdefault(key, new)
        pairs.append({"key": key, "label": label, "value": v, "confidence": block["confidence"],
                      "page": block["page"], "known_label": known})

    def _fallback_known_pairs(self, blocks, fields, pairs):
        """Safety net used only when (almost) nothing was found: read every table cell in order and pair
        each known label with the cell that follows it, whatever the table layout was."""
        for b in blocks:
            if not b["is_table"]:
                continue
            cells = [c for g in self._groups(b["text"]) for c in g]
            for j, cell in enumerate(cells):
                info = self._match_line(cell)
                if not info or info["field"] in fields:
                    continue
                raw = info["rest"]
                if not raw and j + 1 < len(cells):
                    if self._match_line(cells[j + 1]):
                        continue
                    raw = cells[j + 1]
                words = re.sub(r"[^a-z ]", "", (raw or "").lower()).split()
                if not raw or (words and all(w in HEADER_WORDS for w in words)):
                    continue
                ftype = FIELD_DEFINITIONS[info["field"]]["type"]
                value, ok = self.refine_value(ftype, raw)
                if not ok:
                    continue
                fields[info["field"]] = self._make_field(info["label_text"], value, raw, b["confidence"],
                                                        b, "table_scan", True)
                pairs.append({"key": info["field"], "label": info["label_text"], "value": value,
                              "confidence": b["confidence"], "page": b["page"], "known_label": True})

    # ------------------------------------------------------------------
    # PER-PAGE PROCESSING
    # ------------------------------------------------------------------

    def process_page(self, page):
        blocks = page["blocks"]
        fields, pairs, used = {}, [], set()

        stream = self._line_stream(blocks)
        self.extract_from_lines(blocks, stream, used, fields, pairs)

        # type is detected first: marksheet "Total" rows must not be read as invoice totals
        doc_type = self._detect_type(blocks)
        tables = []
        for b in blocks:
            if b["is_table"]:
                tables.extend(self.parse_table(b, fields, pairs,
                                               scan_summary=(doc_type != "marks_statement")))

        if len(fields) < 3:
            self._fallback_known_pairs(blocks, fields, pairs)

        entities = self._entities(blocks)
        self._fill_from_entities(fields, entities, blocks)

        paragraphs = []
        for b in blocks:
            if b["is_table"]:
                continue
            lines = [l.strip() for l in b["text"].split("\n") if l.strip()]
            left = [l for li, l in enumerate(lines) if (b["id"], li) not in used]
            if left:
                paragraphs.append({"text": " ".join(left), "role": b["label"], "page": b["page"],
                                   "bbox": b["bbox"], "reading_order": b["reading_order"],
                                   "confidence": b["confidence"]})

        text_blocks = [b for b in blocks if not b["is_table"]]
        title = self._detect_title(text_blocks)
        issuer = self._detect_issuer(text_blocks)

        return {
            "page_number": page["page_number"],
            "languages": page["languages"] or self._langs_from_blocks(blocks),
            "quality": page.get("quality"),
            "type": doc_type,
            "title": title,
            "issuer": issuer,
            "fields": fields,
            "key_value_pairs": pairs,
            "tables": tables,
            "paragraphs": paragraphs,
            "entities": entities,
        }

    # ------------------------------------------------------------------
    # ENTITIES (pattern based, label independent)
    # ------------------------------------------------------------------

    def _entities(self, blocks):
        text = "\n".join(b["text"] for b in blocks)
        ents = {
            "emails": EMAIL_RE.findall(text),
            "urls": [u for u in URL_RE.findall(text) if "@" not in u],
            "gstin": GSTIN_RE.findall(text),
            "pan": PAN_RE.findall(text),
            "ifsc": IFSC_RE.findall(text),
            "dates": [m.group(0) for m in DATE_RE.finditer(text)],
        }
        return {k: list(dict.fromkeys(v)) for k, v in ents.items() if v}

    def _fill_from_entities(self, fields, entities, blocks):
        conf = round(sum(b["confidence"] for b in blocks) / len(blocks), 4) if blocks else 0.0
        page = blocks[0]["page"] if blocks else None
        mapping = {"emails": "email", "gstin": "gstin", "pan": "pan_number", "ifsc": "ifsc", "urls": "website"}
        for ent, field in mapping.items():
            if ent in entities and field not in fields:
                fields[field] = {"label": None, "value": entities[ent][0], "confidence": conf, "page": page,
                                 "bbox": [], "method": "pattern", "known_label": False}

    # ------------------------------------------------------------------
    # TYPE / TITLE / ISSUER DETECTION
    # ------------------------------------------------------------------

    def _detect_type(self, blocks):
        text = " ".join(b["text"] for b in blocks).lower()
        scores = {}
        for dtype, kws in DOC_TYPES.items():
            scores[dtype] = sum(text.count(k) for k in kws)
        # a title keyword counts extra
        for kw, dtype in (("marks statement", "marks_statement"), ("statement of marks", "marks_statement"),
                          ("marksheet", "marks_statement"), ("invoice", "invoice"), ("receipt", "receipt"),
                          ("resume", "resume"), ("curriculum vitae", "resume")):
            if kw in text[:600]:
                scores[dtype] += 5
        best = max(scores, key=scores.get)
        return best if scores[best] >= 2 else "unknown"

    def _top_lines(self, text_blocks, limit_blocks=10):
        lines = []
        for b in text_blocks[:limit_blocks]:
            for l in b["text"].split("\n"):
                l = l.strip()
                if l:
                    lines.append((l, b))
        return lines

    @staticmethod
    def _english_parts(line):
        """A pure English line -> [line]. A mixed Hindi/English line -> its English runs."""
        if not has_devanagari(line):
            return [line]
        parts = [re.sub(r"\s+", " ", p).strip(" :-,;|") for p in DEVANAGARI_RUN_RE.split(line)]
        return [p for p in parts if len(p) >= 3 and LATIN_RE.search(p)]

    def _detect_title(self, text_blocks):
        lines = self._top_lines(text_blocks, 12)
        for l, b in lines:
            for c in self._english_parts(l):
                if any(k in c.lower() for k in TITLE_KEYWORDS) and len(c) < 80:
                    return c
        for l, b in lines:
            if b["label"].lower().startswith("sectionheader"):
                for c in self._english_parts(l):
                    if len(c) < 80:
                        return c
        return None

    def _detect_issuer(self, text_blocks):
        for l, b in self._top_lines(text_blocks, 12):
            for c in self._english_parts(l):
                if len(c) > 80 or len(c.split()) > 8:
                    continue
                if any(re.search(r"\b" + k + r"\b", c.lower()) for k in ORG_KEYWORDS):
                    return c.strip()
        return None

    # ------------------------------------------------------------------
    # DOCUMENT SEGMENTATION
    # ------------------------------------------------------------------

    @staticmethod
    def _norm(s):
        return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

    def _group_state(self, group):
        """Accumulated identity of the pages collected so far in the current document."""
        types = [p["type"] for p in group if p["type"] != "unknown"]
        ids = {}
        for p in group:
            for key in IDENTITY_FIELDS:
                if key in p["fields"] and key not in ids:
                    ids[key] = p["fields"][key]["value"]
        return {
            "issuer": next((p["issuer"] for p in group if p["issuer"]), None),
            "title": next((p["title"] for p in group if p["title"]), None),
            "type": Counter(types).most_common(1)[0][0] if types else "unknown",
            "ids": ids,
        }

    def _is_new_document(self, group, cur):
        """Decide whether page `cur` starts a new document, compared with the pages collected so far."""
        state = self._group_state(group)
        # explicit page numbering restart ("Page 1 of 3")
        for p in cur["paragraphs"][:3]:
            if re.search(r"\bpage\s*1\s*(?:of|/)\s*\d+", p["text"], re.I):
                return True
        for key, old in state["ids"].items():
            new = cur["fields"].get(key)
            if new and self._norm(str(new["value"])) != self._norm(str(old)):
                return True
        pi, ci = self._norm(state["issuer"]), self._norm(cur["issuer"])
        if pi and ci and pi != ci:
            return True
        if state["type"] != "unknown" and cur["type"] != "unknown" and state["type"] != cur["type"]:
            return True
        pt, ct = self._norm(state["title"]), self._norm(cur["title"])
        if pt and ct and pt != ct and any(k in ct for k in TITLE_KEYWORDS):
            return True
        # two pages that both carry many fields but almost none in common are different documents
        ours = {k for p in group for k in p["fields"]}
        theirs = set(cur["fields"])
        if len(ours) >= 5 and len(theirs) >= 5 and len(ours & theirs) / len(ours | theirs) < 0.12:
            return True
        return False

    def segment(self, page_results):
        if not page_results:
            return []
        if self.split_mode == "single":
            return [page_results]
        if self.split_mode == "page":
            return [[p] for p in page_results]
        docs, current = [], [page_results[0]]
        for cur in page_results[1:]:
            if self._is_new_document(current, cur):
                docs.append(current)
                current = [cur]
            else:
                current.append(cur)
        docs.append(current)
        return docs

    # ------------------------------------------------------------------
    # DOCUMENT ASSEMBLY
    # ------------------------------------------------------------------

    def build_document(self, index, pages):
        fields = {}
        for p in pages:
            for key, f in p["fields"].items():
                if key not in fields:
                    fields[key] = dict(f)
                    continue
                existing = fields[key]
                if str(existing["value"]) == str(f["value"]):
                    continue
                others = existing.setdefault("other_values", [])
                if key in LAST_PAGE_WINS:
                    others.append({"page": existing["page"], "value": existing["value"]})
                    carried = others
                    fields[key] = dict(f)
                    fields[key]["other_values"] = carried
                else:
                    others.append({"page": f["page"], "value": f["value"]})

        types = [p["type"] for p in pages if p["type"] != "unknown"]
        doc_type = Counter(types).most_common(1)[0][0] if types else "unknown"
        langs = []
        for p in pages:
            for l in p["languages"]:
                if l not in langs:
                    langs.append(l)

        entities = {}
        for p in pages:
            for k, v in p["entities"].items():
                entities.setdefault(k, [])
                entities[k].extend(x for x in v if x not in entities[k])

        return {
            "document_index": index,
            "type": doc_type,
            "title": next((p["title"] for p in pages if p["title"]), None),
            "issuer": next((p["issuer"] for p in pages if p["issuer"]), None),
            "pages": [p["page_number"] for p in pages],
            "languages": langs,
            "multilingual": len(langs) > 1,
            "fields": fields,
            "key_value_pairs": [kv for p in pages for kv in p["key_value_pairs"]],
            "tables": [t for p in pages for t in p["tables"]],
            "paragraphs": [x for p in pages for x in p["paragraphs"]],
            "entities": entities,
            "page_results": [
                {"page_number": p["page_number"], "quality": p["quality"], "fields": p["fields"],
                 "table_count": len(p["tables"]), "paragraph_count": len(p["paragraphs"])}
                for p in pages
            ],
        }

    # ------------------------------------------------------------------
    # COMPACT OUTPUT  (document -> fields / tables / text, nothing repeated)
    # ------------------------------------------------------------------

    def compact_document(self, doc, number):
        fields = {k: f["value"] for k, f in doc["fields"].items()}

        tables, text = [], []
        for t in doc["tables"]:
            if t["type"] == "grid":
                entry = {"page": t["page"], "columns": t["columns"], "rows": t["rows"]}
                if t.get("section"):
                    entry = {"section": t["section"], **entry}
                tables.append(entry)
            elif t["type"] == "unparsed":
                tables.append({"page": t["page"], "raw_text": t["raw_text"]})
            else:  # key/value tables are already in `fields`; keep only leftovers (signatures, notes)
                if t.get("section"):
                    text.append(t["section"])
                text.extend(t.get("extra_lines", []))

        text = [p["text"] for p in doc["paragraphs"]] + text

        confs = [f["confidence"] for f in doc["fields"].values() if f.get("confidence")]
        out = {
            "document": number,
            "type": doc["type"],
            "title": doc["title"],
            "issuer": doc["issuer"],
            "pages": doc["pages"],
            "languages": doc["languages"],
            "confidence": round(sum(confs) / len(confs), 4) if confs else None,
            "fields": fields,
            "tables": tables,
            "text": text,
        }
        return out

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def structure(self, data):
        source, pages = self.load_pages(data)
        page_results = [self.process_page(p) for p in pages]
        grouped = self.segment(page_results)
        full_docs = [self.build_document(i, g) for i, g in enumerate(grouped, start=1)]
        documents = full_docs if self.detailed else [
            self.compact_document(d, i) for i, d in enumerate(full_docs, start=1)]
        return {
            "source": source,
            "documents": documents,
            "metadata": {
                "total_pages": len(pages),
                "total_documents": len(documents),
                "split_mode": self.split_mode,
                "layout": "detailed" if self.detailed else "compact",
            },
        }

    def process_file(self, input_path, output_path=None):
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input JSON not found: {input_path}")
        with input_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        structured = self.structure(data)
        output_path = Path(output_path) if output_path else input_path.parent / "structured.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as fh:
            json.dump(structured, fh, ensure_ascii=False, indent=2)
        return structured, output_path


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    split = "auto"
    detailed = "--detailed" in argv
    argv = [a for a in argv if a != "--detailed"]
    if "--split" in argv:
        i = argv.index("--split")
        split = argv[i + 1]
        del argv[i:i + 2]
    if not argv:
        print("Usage: python astra_structured_ocr.py input.json [output.json] [--split auto|page|single] [--detailed]")
        return 1
    try:
        service = AstraStructuredOCRService(split_mode=split, detailed=detailed)
        structured, out = service.process_file(argv[0], argv[1] if len(argv) > 1 else None)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}")
        return 1

    print("=" * 70)
    for doc in structured["documents"]:
        idx = doc.get("document") or doc.get("document_index")
        print(f"Document {idx}: {doc['type']}  pages={doc['pages']}  issuer={doc['issuer']}")
        for key, f in doc["fields"].items():
            print(f"   {key}: {f['value'] if isinstance(f, dict) else f}")
        print(f"   tables: {len(doc['tables'])}")
    print(f"\nOutput: {out}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())