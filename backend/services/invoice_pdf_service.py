import html
import json
import os
import re

import requests

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, Spacer, Table, TableStyle


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b"

PAGE_WIDTH_PT = (210 - 30) * mm  # A4 minus 15 mm margins each side

CURRENCY = r"(?:[$₹€£¥]|Rs\.?|INR|USD|EUR|GBP)"


# ---------------------------------------------------------------------
# Invoice detection keywords (multilingual, lower-case)
# ---------------------------------------------------------------------

STRONG_KEYWORDS = [
    "invoice", "tax invoice", "bill to", "bill of supply", "cash memo",
    "gstin", "gst registration", "hsn", "billing address", "sold by",
    # Hindi
    "चालान", "बीजक", "इनवॉइस", "इन्वॉइस", "जीएसटी", "क्रेता", "विक्रेता",
    # Gujarati
    "ઇન્વોઇસ", "ઇન્વૉઇસ", "ચલણ", "જીએસટી", "ખરીદનાર", "વેચનાર",
    # Other common languages
    "فاتورة", "发票", "發票", "factura", "facture", "rechnung", "fattura",
    "請求書", "청구서", "счет", "счёт", "fatura", "চালান", "ইনভয়েস",
    "விலைப்பட்டியல்", "ใบแจ้งหนี้",
]

WEAK_KEYWORDS = [
    "subtotal", "sub total", "grand total", "balance due", "amount due",
    "qty", "quantity", "unit price", "rate", "amount", "due date",
    "invoice no", "invoice number", "invoice date", "order number",
    "authorized signatory", "authorised signatory", "payment instructions",
    "vat", "discount", "total",
    # Hindi
    "कुल", "राशि", "मात्रा", "दर", "भुगतान", "हस्ताक्षर", "बिल",
    # Gujarati
    "કુલ", "રકમ", "જથ્થો", "દર", "ચુકવણી", "સહી", "બિલ",
    # Others
    "الإجمالي", "总计", "合計", "total a pagar", "montant", "gesamt",
]


# ---------------------------------------------------------------------
# LLM prompt
# ---------------------------------------------------------------------

SYSTEM_PROMPT = """You convert OCR text of a possibly non-English document into clean, structured English JSON.

First decide whether the document is an invoice / bill / cash memo / tax invoice / receipt-style bill with line items. If it is NOT, return {"is_invoice": false} and nothing else.

If it IS an invoice, return {"invoices": [ ... ]} where every separate invoice found in the text is ONE item. If the text contains two or more different invoices (different invoice numbers / sellers / buyers), return each as its own item and NEVER merge them. Each item has exactly this shape:

{
  "is_invoice": true,
  "source_language": "name of the original language",
  "title": "e.g. Tax Invoice / Invoice / Bill of Supply / Cash Memo",
  "subtitle": "e.g. (Original for Recipient) or empty string",
  "seller": {
    "label": "Sold By",
    "name": "",
    "lines": ["address / phone / email lines"],
    "ids": [["PAN No", "..."], ["GST Registration No", "..."]]
  },
  "parties": [
    {"label": "Bill To", "name": "", "lines": ["..."]},
    {"label": "Shipping Address", "name": "", "lines": ["..."]}
  ],
  "meta": [["Invoice Number", "..."], ["Invoice Date", "..."], ["Order Number", "..."]],
  "table": {
    "headers": ["Sl. No", "Description", "Qty", "Rate", "Amount"],
    "rows": [["1", "...", "1", "$ 10.00", "$ 10.00"]]
  },
  "totals": [["Subtotal", "$ 10.00"], ["Total", "$ 10.00"]],
  "amount_in_words": "",
  "payment_info": {"label": "Payment Instructions", "lines": []},
  "signatory": {"for": "", "label": "Authorized Signatory"},
  "notes": ["any remaining footer / terms lines"]
}

Rules:
- Translate EVERY word into English (labels, descriptions, addresses, notes, amount in words).
- Person, company and street names: transliterate to English letters, do not translate their meaning.
- NEVER change, round, recompute or invent numbers: amounts, quantities, dates, invoice / order / GST / PAN / phone numbers and codes are copied exactly as in the source (only convert non-Latin digits to 0-9).
- Keep currency symbols exactly as in the source.
- Keep the table's real columns. Every row must have exactly as many cells as "headers".
- OCR tables come in different shapes: pipe-separated rows, glued cells (e.g. "1Desktop furniture1$ 232.00$ 232.00"), or ONE CELL PER LINE with blank lines between (blank lines can mean an empty cell, e.g. a missing Discount). Rebuild proper rows using the headers.
- Lines such as "Subtotal / $25.99", "Tax Rate / 6.00%", "Sales Tax / $1.56", "TOTAL / $25.99" that follow the item rows are NOT item rows: put them in "totals".
- The text marked [TABLE] ... [/TABLE] is the table block.
- Put each total-like line (Subtotal, Tax, Discount, Total, Paid, Balance Due ...) into "totals" in the source order.
- Only fill fields that exist in the source. Use "" or [] when absent. Do not invent anything.
- Output JSON only, no commentary."""


# =====================================================================
# Formatter
# =====================================================================

class InvoiceFormatter:

    def __init__(self, pdf_service):
        self.svc = pdf_service

    # -----------------------------------------------------------------
    # PUBLIC
    # -----------------------------------------------------------------

    def build_story(self, layout_result):
        """Return a ReportLab story for invoices, otherwise None.

        One JSON can hold several invoices (one per page, or several on
        one page). Pages are grouped per invoice and each invoice gets
        its own page(s) in the PDF.
        """

        try:
            pages = [p for p in self._pages(layout_result)
                     if p["text"].strip()]

            if not pages:
                return None

            # A page that looks like an invoice starts a new invoice; a
            # page that does not is a continuation of the previous one.
            # If the first page is not an invoice -> normal PDF.
            groups = []
            for pg in pages:
                if self._looks_like_invoice(pg["text"]):
                    groups.append([pg])
                elif groups:
                    groups[-1].append(pg)
                else:
                    return None

            print(f"\n[InvoiceFormatter] Invoice document detected "
                  f"({len(groups)} invoice group(s)).")

            invoices = []
            for n, group in enumerate(groups, 1):
                found = self._extract(group)
                if not found:
                    print(f"[InvoiceFormatter] Group {n} could not be "
                          f"read as an invoice - using normal PDF.")
                    return None
                invoices.extend(found)

            story = []
            for i, data in enumerate(invoices):
                part = self._render(data)
                if not part:
                    return None
                if i > 0:
                    story.append(PageBreak())
                story += part

            print(f"[InvoiceFormatter] Rendered {len(invoices)} invoice(s).")
            return story or None

        except Exception as exc:  # never break the normal pipeline
            print(f"[InvoiceFormatter] Failed, using normal PDF: {exc}")
            return None

    # -----------------------------------------------------------------
    # 1. COLLECT PAGES / BLOCKS
    # -----------------------------------------------------------------

    def _html_table_to_lines(self, raw_html):
        lines = []
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", raw_html or "",
                              flags=re.I | re.S):
            cells = re.findall(r"<(?:td|th)[^>]*>(.*?)</(?:td|th)>", row,
                               flags=re.I | re.S)
            clean = []
            for cell in cells:
                cell = re.sub(r"<br\s*/?>", " ", cell, flags=re.I)
                cell = re.sub(r"<[^>]+>", "", cell)
                cell = re.sub(r"\s+", " ", html.unescape(cell)).strip()
                clean.append(cell)
            if clean:
                lines.append(" | ".join(clean))
        return lines

    def _pages(self, layout_result):
        """
        Per page: plain text, LLM text and the list of (type, text) blocks.
        Works with the SuryaLayoutService output
        ({"pages":[{"blocks":[{"type","text","html"}]}]}) and with the raw
        OCR JSON ({"pages":[{"text":..., "ocr_result":{"results":[...]}}]}).
        """

        out = []

        for page in (layout_result or {}).get("pages", []):

            blocks = page.get("blocks")
            if blocks is None:
                blocks = (page.get("ocr_result") or {}).get("results") or []

            items = []
            for block in blocks:
                btype = re.sub(r"[_\-\s]", "", str(
                    block.get("type") or block.get("label") or "text"
                ).lower())

                if btype in ("image", "picture", "figure"):
                    continue

                text = ""
                if btype == "table" and block.get("html"):
                    text = "\n".join(self._html_table_to_lines(block["html"]))
                if not text:
                    text = str(block.get("text") or "")

                if text.strip():
                    items.append((btype, text))

            if not items and page.get("text"):
                items.append(("text", str(page["text"])))

            plain = "\n".join(t for _, t in items)
            llm = "\n\n".join(
                f"[TABLE]\n{t}\n[/TABLE]" if b == "table" else t
                for b, t in items)

            out.append({"text": plain, "llm_text": llm, "blocks": items})

        return out

    # -----------------------------------------------------------------
    # 2. DETECTION
    # -----------------------------------------------------------------

    def _looks_like_invoice(self, text):

        low = text.lower()

        strong = {k for k in STRONG_KEYWORDS if k in low}
        weak = {k for k in WEAK_KEYWORDS if k in low}

        score = len(strong) * 2 + len(weak)

        return bool(strong) and score >= 3

    # -----------------------------------------------------------------
    # 3. EXTRACTION  (Groq LLM -> block-aware offline parser)
    # -----------------------------------------------------------------

    @staticmethod
    def _non_latin_ratio(text):
        letters = [c for c in text if c.isalpha()]
        if not letters:
            return 0.0
        non_latin = [c for c in letters if ord(c) > 0x024F]
        return len(non_latin) / len(letters)

    def _extract(self, group):
        """Return a list of cleaned invoice dicts (or None)."""

        llm_text = "\n\n".join(p["llm_text"] for p in group)
        plain = "\n".join(p["text"] for p in group)
        blocks = [b for p in group for b in p["blocks"]]

        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        raw = None

        if api_key:
            raw = self._extract_with_llm(llm_text, api_key)
        else:
            print("[InvoiceFormatter] GROQ_API_KEY not set - "
                  "cannot translate, using offline parser.")

        if raw is not None:
            if isinstance(raw.get("invoices"), list):
                items = raw["invoices"]
            elif raw.get("is_invoice", False) is False:
                print("[InvoiceFormatter] LLM says: not an invoice.")
                return None
            else:
                items = [raw]

            cleaned = [self._clean(i) for i in items
                       if isinstance(i, dict) and i.get("is_invoice", True)]
            cleaned = [c for c in cleaned
                       if c["table"]["rows"] or c["totals"]]
            if cleaned:
                return cleaned
            print("[InvoiceFormatter] LLM result had no items/totals - "
                  "trying offline parser.")

        # Offline parser cannot translate -> Latin-script text only.
        if self._non_latin_ratio(plain) > 0.10:
            print("[InvoiceFormatter] Non-English invoice but translation "
                  "unavailable - falling back to normal PDF.")
            return None

        data = self._parse_blocks(blocks)
        data = self._clean(data) if data else None

        if not data or not (data["table"]["rows"] or data["totals"]):
            print("[InvoiceFormatter] Offline parser found no items - "
                  "falling back to normal PDF.")
            return None

        return [data]

    def _extract_with_llm(self, text, api_key):

        model = os.environ.get("GROQ_MODEL", DEFAULT_MODEL)

        payload = {
            "model": model,
            "temperature": 0,
            "max_tokens": 6000,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",
                 "content": "OCR TEXT (blocks separated by blank lines):\n\n"
                            + text[:24000]},
            ],
        }

        if "gpt-oss" in model:
            payload["reasoning_effort"] = "low"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        for attempt in (1, 2):
            try:
                resp = requests.post(GROQ_URL, headers=headers,
                                     json=payload, timeout=90)
                if resp.status_code != 200:
                    print(f"[InvoiceFormatter] Groq HTTP {resp.status_code}"
                          f" (attempt {attempt}): {resp.text[:200]}")
                    continue

                content = resp.json()["choices"][0]["message"]["content"]
                content = re.sub(r"^```(?:json)?|```$", "",
                                 content.strip(), flags=re.M).strip()
                return json.loads(content)

            except Exception as exc:
                print(f"[InvoiceFormatter] LLM error (attempt {attempt}): "
                      f"{exc}")

        return None

    # =================================================================
    # OFFLINE, BLOCK-AWARE PARSER (English / Latin text only)
    # =================================================================

    _AMOUNT = re.compile(
        rf"^\(?-?\s*(?:{CURRENCY})?\s*-?\d[\d,]*(?:\.\d+)?\s*"
        rf"(?:{CURRENCY})?\)?\s*%?$", re.I)

    _TOTAL_INLINE = re.compile(
        rf"^(.*?[A-Za-z].*?)\s*[:\-]?\s*"
        rf"({CURRENCY}\s*-?[\d,]+(?:\.\d+)?|-?\d[\d,]*\.\d+\s*%?|"
        rf"\d+(?:\.\d+)?\s*%)\s*$", re.I)

    _TOTAL_KEYS = re.compile(
        r"sub\s*total|total|tax|vat|gst|igst|cgst|sgst|discount|deposit|"
        r"paid|balance|due|shipping|freight|round|advance|amount|adjust|"
        r"charges?|fee", re.I)

    _KV = re.compile(r"^([A-Za-z][^:]{0,34}?)\s*:\s*(.*)$")

    _META_KEYS = re.compile(
        r"invoice|\binv\b|date|due|job|order|\bpo\b|p\.o\.|\bref|terms|"
        r"number|\bno\b|#|period|project|account|place of|supply|delivery|"
        r"reverse charge|currency|salesperson|shipped|dated", re.I)

    _ID_KEYS = re.compile(
        r"\b(pan|gstin|gst|vat|tin|cin|ein|abn|tax\s*id|registration|"
        r"reg\.?\s*no)\b", re.I)

    _PARTY = re.compile(
        r"^(bill(?:ed)?\s*to|ship(?:ped)?\s*to|sold\s*to|deliver(?:ed)?\s*to|"
        r"invoice\s*to|issued\s*to|buyer|consignee|payable\s*to|remit\s*to|"
        r"(?:billing|shipping|delivery|customer)\s*address)\b\s*[:.\-]?\s*(.*)$",
        re.I)

    _SELLER = re.compile(
        r"^(sold\s*by|seller|vendor|supplier|issued\s*by|from)\b\s*[:\-]?\s*"
        r"(.*)$", re.I)

    _HEADER_VOCAB = re.compile(
        r"item|desc|qty|quantity|unit|price|rate|amount|total|discount|tax|"
        r"hsn|\bsl\b|sl\.|\bno\b|#|particular|\bsr\b|s\.no|code|net|gst|"
        r"igst|cgst|sgst|uom|name|sku|service|product|hours|ref", re.I)

    _SIG = re.compile(r"authori[sz]ed\s+signator|signature|signatory", re.I)
    _WORDS = re.compile(r"^amount\s+in\s+words\s*:?\s*(.*)$", re.I)
    _PAYLABEL = re.compile(
        r"^(payment|bank)\s*(instructions?|details?|info(?:rmation)?|terms|"
        r"method)?\s*:?$", re.I)

    # ---- small helpers ------------------------------------------------

    def _is_amount(self, token):
        t = (token or "").strip()
        if not t or not self._AMOUNT.match(t):
            return False
        return bool(re.search(CURRENCY, t, re.I) or "." in t or "%" in t)

    @staticmethod
    def _merge_lines(text):
        """Non-empty lines; a line ending with ',' continues on the next."""
        out = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if out and out[-1].endswith(","):
                out[-1] += " " + line
            else:
                out.append(line)
        return out

    def _is_title(self, lines):
        first = lines[0]
        return bool(
            re.search(r"invoice|bill of supply|cash memo|credit note|"
                      r"debit note|receipt|tax bill|proforma|quotation",
                      first, re.I)
            and len(first) <= 60
            and not re.search(r"[:#\d]", first)
            and not self._PARTY.match(first))

    def _pair_totals(self, lines):
        """Split lines into [label, value] total pairs and leftovers."""
        pairs, rest, i = [], [], 0
        while i < len(lines):
            line = lines[i]
            m = self._TOTAL_INLINE.match(line)
            if m and self._TOTAL_KEYS.search(m.group(1)):
                pairs.append([m.group(1).strip(" :-"), m.group(2).strip()])
                i += 1
                continue
            if (re.search(r"[A-Za-z]", line) and not self._is_amount(line)
                    and self._TOTAL_KEYS.search(line)
                    and i + 1 < len(lines)
                    and self._is_amount(lines[i + 1])):
                pairs.append([line.strip(" :-"), lines[i + 1].strip()])
                i += 2
                continue
            rest.append(line)
            i += 1
        return pairs, rest

    def _fit_row(self, cells, headers):
        """Make a row exactly len(headers) cells wide."""
        n = len(headers)
        cells = list(cells)

        desc = next((i for i, h in enumerate(headers)
                     if re.search(r"desc|item name|particular|product|"
                                  r"service", h, re.I)), 1 if n > 1 else 0)

        if len(cells) > n:  # extra cells belong to the description
            extra = len(cells) - n
            cells[desc:desc + extra + 1] = [" ".join(cells[desc:desc + extra + 1])]

        if len(cells) < n:
            missing = n - len(cells)
            optional = [i for i, h in enumerate(headers)
                        if re.search(r"disc|tax|hsn|remark|note|vat|gst", h,
                                     re.I)]
            blanks = optional[:missing]
            if len(blanks) < missing:
                for i in range(n - 2, 0, -1):
                    if i not in blanks and i != desc:
                        blanks.append(i)
                    if len(blanks) == missing:
                        break
            it = iter(cells)
            cells = ["" if c in blanks else next(it, "") for c in range(n)]

        return cells

    # ---- table block --------------------------------------------------

    def _parse_table(self, text):
        """Return (headers, rows, totals) for pipe / glued / vertical."""

        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if not lines:
            return [], [], []

        # --- pipe separated (from html tables) -----------------------
        if sum(1 for l in lines if "|" in l) >= max(1, len(lines) // 2):
            headers = [c.strip() for c in lines[0].split("|")]
            n = len(headers)
            rows, totals = [], []
            for l in lines[1:]:
                cells = [c.strip() for c in l.split("|")]
                filled = [c for c in cells if c]
                if (len(filled) == 2 and self._TOTAL_KEYS.search(filled[0])
                        and self._is_amount(filled[1])):
                    totals.append([filled[0], filled[1]])
                elif filled:
                    rows.append((cells + [""] * n)[:n])
            return headers, rows, totals

        # --- glued: header cells on one line -------------------------
        tokens = ["Sl. No", "Sl.No", "Sl No", "S.No", "Sr No", "Sl.",
                  "Description", "Item", "HSN", "Unit Price", "Qty",
                  "Quantity", "Rate", "Price", "Net Amount", "Tax Rate",
                  "Tax Type", "Tax Amount", "Total Amount", "Amount",
                  "Total", "Discount"]
        pattern = "|".join(re.escape(t) for t in
                           sorted(tokens, key=len, reverse=True))
        glued = re.findall(pattern, lines[0], flags=re.I)

        if len(glued) >= 3 and len(lines[0]) < 120:
            headers = [h.strip() for h in glued]
            n = len(headers)
            rows, totals = [], []
            for l in lines[1:]:
                pairs, _ = self._pair_totals([l])
                row = self._parse_row(l, n)
                if row:
                    rows.append(row)
                elif pairs:
                    totals += pairs
                elif rows:
                    di = next((k for k, h in enumerate(headers)
                               if re.search(r"desc|item", h, re.I)), 1)
                    rows[-1][di] += " " + l
            return headers, rows, totals

        # --- vertical: one cell per line -----------------------------
        i = 0
        while (i < len(lines) and len(lines[i]) <= 26
               and self._HEADER_VOCAB.search(lines[i])
               and not self._is_amount(lines[i])):
            i += 1

        headers = lines[:i]
        if len(headers) < 2:
            pairs, _ = self._pair_totals(lines)
            return [], [], pairs

        n = len(headers)
        data = lines[i:]
        rows, cur, k = [], [], 0

        def starts_totals(pos):
            return (pos + 1 < len(data)
                    and self._TOTAL_KEYS.search(data[pos])
                    and not self._is_amount(data[pos])
                    and self._is_amount(data[pos + 1]))

        while k < len(data):
            if not cur and starts_totals(k):
                break
            tok = data[k]
            cur.append(tok)
            nxt = data[k + 1] if k + 1 < len(data) else None
            done = (self._is_amount(tok) and len(cur) >= max(2, n - 2)
                    and (nxt is None or (re.search(r"[A-Za-z]", nxt)
                                         and not self._is_amount(nxt))))
            k += 1
            if done or len(cur) > 3 * n:
                rows.append(self._fit_row(cur, headers))
                cur = []

        if cur:
            rows.append(self._fit_row(cur, headers))

        totals, _ = self._pair_totals(data[k:])
        return headers, rows, totals

    @staticmethod
    def _parse_row(line, n_cols):
        """'1Desktop furniture1$ 232.00$ 232.00' (glued) or 'a | b | c'."""

        if "|" in line:
            cells = [c.strip() for c in line.split("|")]
            return cells if len(cells) == n_cols else None

        m = re.match(
            rf"^(\d{{1,3}})\s*(.+?)\s*(\d+(?:\.\d+)?)\s*"
            rf"({CURRENCY}\s*[\d,]+(?:\.\d+)?)\s*"
            rf"({CURRENCY}\s*[\d,]+(?:\.\d+)?)$", line, re.I)

        if m and n_cols == 5:
            return [m.group(1), m.group(2).strip(), m.group(3),
                    m.group(4).strip(), m.group(5).strip()]
        return None

    # ---- whole document -----------------------------------------------

    def _parse_blocks(self, blocks):

        d = {
            "is_invoice": True, "title": "", "subtitle": "",
            "seller": {"label": "Sold By", "name": "", "lines": [],
                       "ids": []},
            "parties": [], "meta": [],
            "table": {"headers": [], "rows": []},
            "totals": [], "amount_in_words": "",
            "payment_info": {"label": "", "lines": []},
            "signatory": {"for": "", "label": ""},
            "notes": [],
        }

        seen_table = False
        pending_party = None
        pending_meta = None
        pay_mode = False
        KV = self._KV

        def party_from(label, rest, lines):
            if rest:
                return {"label": label, "name": rest, "lines": lines[1:]}
            if len(lines) > 1:
                return {"label": label, "name": lines[1],
                        "lines": lines[2:]}
            return None

        for btype, text in blocks:

            # ---------------- table ----------------
            if btype == "table":
                headers, rows, totals = self._parse_table(text)
                if (headers or rows) and not d["table"]["rows"]:
                    d["table"] = {"headers": headers, "rows": rows}
                d["totals"] += totals
                seen_table = True
                pending_party = pending_meta = None
                continue

            lines = self._merge_lines(text)
            if not lines:
                continue
            first = lines[0]

            # value for a label that stood alone ("Invoice No :")
            if pending_meta and len(lines) == 1 and not KV.match(first):
                d["meta"].append([pending_meta, first])
                pending_meta = None
                continue
            pending_meta = None

            # ---------------- after the table ----------------
            if seen_table:
                pairs, rest = self._pair_totals(lines)
                if pairs:
                    d["totals"] += pairs
                    pay_mode = False
                for line in rest:
                    w = self._WORDS.match(line)
                    if w:
                        d["amount_in_words"] = w.group(1).strip()
                        pay_mode = False
                    elif (not d["amount_in_words"] and d["notes"]
                          and re.match(r"^amount in words", d["notes"][-1],
                                       re.I)):
                        d["amount_in_words"] = line
                    elif self._SIG.search(line):
                        d["signatory"]["label"] = line
                        pay_mode = False
                    elif self._PAYLABEL.match(line):
                        d["payment_info"]["label"] = line.rstrip(": ")
                        pay_mode = True
                    elif pay_mode:
                        d["payment_info"]["lines"].append(line)
                    elif re.match(r"^for\s+\S", line, re.I) and \
                            not d["signatory"]["for"] and len(line) < 80:
                        d["signatory"]["for"] = re.sub(
                            r"^for\s+|[:\s]+$", "", line, flags=re.I)
                    else:
                        d["notes"].append(line)
                continue

            # ---------------- before the table ----------------
            p = self._PARTY.match(first)
            if p:
                party = party_from(re.sub(r"[:\s]+$", "", first[:p.start(2)]
                                          if p.group(2) else first),
                                   p.group(2).strip(), lines)
                label = (first[:p.start(2)] if p.group(2) else first)
                label = re.sub(r"[:.\-\s]+$", "", label)
                if party:
                    party["label"] = label
                    d["parties"].append(party)
                else:
                    pending_party = {"label": label, "name": "",
                                     "lines": []}
                continue

            s = self._SELLER.match(first)
            if s:
                label = re.sub(r"[:.\-\s]+$", "",
                               first[:s.start(2)] if s.group(2) else first)
                d["seller"]["label"] = label or "Sold By"
                rest = s.group(2).strip()
                body = ([rest] + lines[1:]) if rest else lines[1:]
                if body:
                    d["seller"]["name"] = body[0]
                    d["seller"]["lines"] += body[1:]
                continue

            if not d["title"] and self._is_title(lines):
                d["title"] = first
                if len(lines) > 1 and lines[1].startswith("("):
                    d["subtitle"] = lines[1]
                continue

            w = self._WORDS.match(first)
            if w:
                d["amount_in_words"] = w.group(1).strip() or \
                    (lines[1] if len(lines) > 1 else "")
                continue

            if self._SIG.search(first):
                d["signatory"]["label"] = first
                continue

            # meta: "Invoice Date : ..." style blocks
            kvs = [KV.match(l) for l in lines]
            real = [m for m in kvs if m]
            is_meta = bool(real) and len(real) >= len(lines) / 2 and any(
                self._META_KEYS.search(m.group(1))
                and not self._ID_KEYS.search(m.group(1)) for m in real)
            if is_meta:
                if len(lines) == 1 and not real[0].group(2).strip():
                    pending_meta = real[0].group(1).strip()
                    continue
                for m in real:
                    d["meta"].append([m.group(1).strip(),
                                      m.group(2).strip()])
                continue

            # content for a party label that stood alone ("Bill To")
            if pending_party is not None:
                pending_party["name"] = lines[0]
                pending_party["lines"] = lines[1:]
                d["parties"].append(pending_party)
                pending_party = None
                continue

            # otherwise: seller details (name / address / ids)
            body = []
            for line in lines:
                m = KV.match(line)
                if m and self._ID_KEYS.search(m.group(1)):
                    d["seller"]["ids"].append([m.group(1).strip(),
                                               m.group(2).strip()])
                else:
                    body.append(line)

            if body and not d["seller"]["name"]:
                short = (len(body) <= 2 and all(
                    len(b) <= 30 and not re.search(r"\d", b) for b in body))
                if short:
                    d["seller"]["name"] = " ".join(body)
                    body = []
                else:
                    d["seller"]["name"] = body[0]
                    body = body[1:]
            d["seller"]["lines"] += body

        if d["signatory"]["label"] and not d["signatory"]["for"]:
            d["signatory"]["for"] = d["seller"]["name"]

        if not d["title"]:
            d["title"] = "Invoice"

        return d

    # ---- normalise whatever came back ---------------------------------

    @staticmethod
    def _s(v):
        return "" if v is None else str(v).strip()

    def _clean(self, data):

        s = self._s

        def pairs(seq):
            out = []
            for item in seq or []:
                if isinstance(item, dict):
                    item = [item.get("label", ""), item.get("value", "")]
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    out.append([s(item[0]), s(item[1])])
            return out

        def lines(seq):
            if isinstance(seq, str):
                seq = seq.splitlines()
            return [s(x) for x in (seq or []) if s(x)]

        seller = data.get("seller") or {}
        table = data.get("table") or {}
        headers = [s(h) for h in table.get("headers") or []]
        rows = []
        for r in table.get("rows") or []:
            r = [s(c) for c in (r if isinstance(r, (list, tuple)) else [r])]
            if headers:
                r = (r + [""] * len(headers))[:len(headers)]
            rows.append(r)

        parties = []
        for p in data.get("parties") or []:
            parties.append({
                "label": s(p.get("label")),
                "name": s(p.get("name")),
                "lines": lines(p.get("lines")),
            })

        pay = data.get("payment_info") or {}
        sig = data.get("signatory") or {}

        return {
            "is_invoice": data.get("is_invoice", True),
            "title": s(data.get("title")) or "Invoice",
            "subtitle": s(data.get("subtitle")),
            "seller": {
                "label": s(seller.get("label")) or "Sold By",
                "name": s(seller.get("name")),
                "lines": lines(seller.get("lines")),
                "ids": pairs(seller.get("ids")),
            },
            "parties": parties,
            "meta": pairs(data.get("meta")),
            "table": {"headers": headers, "rows": rows},
            "totals": pairs(data.get("totals")),
            "amount_in_words": s(data.get("amount_in_words")),
            "payment_info": {"label": s(pay.get("label")),
                             "lines": lines(pay.get("lines"))},
            "signatory": {"for": s(sig.get("for")),
                          "label": s(sig.get("label"))},
            "notes": lines(data.get("notes")),
        }

    # -----------------------------------------------------------------
    # 4. RENDER  (Amazon-style invoice)
    # -----------------------------------------------------------------

    def _p(self, text, size=9.5, leading=12.5, align=TA_LEFT, bold=False,
           before=0, after=0):
        style = self.svc.make_style(
            font_size=size, leading=leading, alignment=align,
            space_before=before, space_after=after)
        return Paragraph(self.svc.format_unicode_text(text, bold=bold), style)

    def _label_value(self, label, value, align=TA_LEFT, size=9.5):
        """'<b>Label:</b> value' on one line, mixed fonts handled."""
        lab = self.svc.format_unicode_text(label.rstrip() + " ", bold=True)
        val = self.svc.format_unicode_text(value)
        style = self.svc.make_style(
            font_size=size, leading=size + 3, alignment=align,
            space_before=0, space_after=0)
        return Paragraph(lab + val, style)

    def _block(self, label, name, lines, align):
        items = []
        if label:
            items.append(self._p(label.rstrip(" :") + " :", bold=True,
                                 size=10.5, leading=14, align=align))
        if name:
            items.append(self._p(name, align=align))
        for line in lines:
            items.append(self._p(line, align=align))
        return items

    def _two_col(self, left, right, space_after=8):
        t = Table([[left or "", right or ""]],
                  colWidths=[PAGE_WIDTH_PT * 0.5, PAGE_WIDTH_PT * 0.5])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return [t, Spacer(1, space_after)]

    def _box(self, flowables, align="LEFT"):
        t = Table([[flowables]], colWidths=[PAGE_WIDTH_PT])
        t.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    # ---- items table --------------------------------------------------

    @staticmethod
    def _is_numeric(cell):
        c = cell.strip()
        return bool(c) and bool(re.search(r"\d", c)) and \
            bool(re.fullmatch(r"[\s\d.,%:/\-+()$₹€£¥A-Za-z]{0,14}", c)) and \
            len(re.findall(r"[A-Za-z]", c)) <= 4

    def _items_table(self, table, totals):

        headers = table["headers"]
        rows = table["rows"]

        if not headers and rows:
            headers = [""] * len(rows[0])

        n = len(headers)
        if n == 0:
            return None

        # ---- column widths (content driven) -----------------------
        weights = []
        for c in range(n):
            lens = [len(headers[c])] + [len(r[c]) for r in rows if c < len(r)]
            longest = max(lens) if lens else 6
            avg = sum(lens) / len(lens)
            w = max(6, min(46, 0.6 * longest + 0.4 * avg))
            if re.search(r"desc|item|particular", headers[c], re.I):
                w = max(w, 28)
            if re.search(r"^(sl|s\.?\s*no|sr|#)", headers[c].strip(), re.I):
                w = min(w, 7)
            # never let a header word break across lines
            longest_word = max((len(x) for x in headers[c].split()),
                               default=0)
            w = max(w, longest_word * 1.25 + 3)
            weights.append(w)
        total_w = sum(weights)
        col_w = [PAGE_WIDTH_PT * w / total_w for w in weights]

        # ---- alignment per column ---------------------------------
        numeric_cols = []
        for c in range(n):
            vals = [r[c] for r in rows if c < len(r) and r[c].strip()]
            numeric_cols.append(c > 0 and bool(vals) and
                                sum(self._is_numeric(v) for v in vals)
                                >= 0.8 * len(vals))

        def cell(text, c, bold=False, header=False):
            align = TA_LEFT
            if numeric_cols[c] and not header:
                align = TA_RIGHT
            if header and numeric_cols[c]:
                align = TA_RIGHT
            return self._p(text, size=8.5, leading=10.5, align=align,
                           bold=bold or header)

        data = [[cell(h, c, header=True) for c, h in enumerate(headers)]]
        for r in rows:
            data.append([cell(r[c] if c < len(r) else "", c)
                         for c in range(n)])

        style = [
            ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9D9D9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]

        # ---- totals rows inside the same grid ---------------------
        if totals and n >= 2:
            for k, (label, value) in enumerate(totals):
                r_i = len(data)
                label_txt = label.upper() + ":" if k == 0 and \
                    re.fullmatch(r"(?i)\s*(grand\s+)?total\s*", label) \
                    else label
                row = [self._p(label_txt, size=9, leading=11, bold=True)]
                row += [""] * (n - 2)
                row += [self._p(value, size=9, leading=11, bold=True,
                                align=TA_RIGHT)]
                data.append(row)
                style += [
                    ("SPAN", (0, r_i), (n - 2, r_i)),
                    ("BACKGROUND", (n - 1, r_i), (n - 1, r_i),
                     colors.HexColor("#D9D9D9")),
                ]

        t = Table(data, colWidths=col_w, repeatRows=1)
        t.setStyle(TableStyle(style))
        return t

    # ---- whole page ---------------------------------------------------

    def _render(self, d):

        story = []
        seller = d["seller"]
        parties = d["parties"]

        # ---- header: title on the right (like the sample image) ---
        title_cells = [self._p(d["title"], size=14, leading=18, bold=True,
                               align=TA_RIGHT)]
        if d["subtitle"]:
            title_cells.append(self._p(d["subtitle"], size=11, leading=14,
                                       align=TA_RIGHT))
        story += self._two_col([], title_cells, space_after=18)

        # ---- row 1: Sold By | first party -------------------------
        left = self._block(seller["label"], seller["name"], seller["lines"],
                           TA_LEFT)

        right = []
        if parties:
            p = parties[0]
            right = self._block(p["label"], p["name"], p["lines"], TA_RIGHT)
        story += self._two_col(left, right, space_after=10)

        # ---- row 2: seller ids | remaining parties ----------------
        ids = [self._label_value(k.rstrip(" :") + ":", v)
               for k, v in seller["ids"]]
        rest = []
        for p in parties[1:]:
            rest += self._block(p["label"], p["name"], p["lines"], TA_RIGHT)
            rest.append(Spacer(1, 4))
        if ids or rest:
            story += self._two_col(ids, rest, space_after=10)

        # ---- row 3: order-ish meta left | invoice meta right ------
        left_meta, right_meta = [], []
        for k, v in d["meta"]:
            target = left_meta if re.search(r"order", k, re.I) \
                else right_meta
            align = TA_LEFT if target is left_meta else TA_RIGHT
            target.append(self._label_value(k.rstrip(" :") + ":", v,
                                            align=align))
        if left_meta or right_meta:
            story += self._two_col(left_meta, right_meta, space_after=8)

        # ---- items table with totals ------------------------------
        table = self._items_table(d["table"], d["totals"])
        if table is not None:
            story.append(table)
        elif d["totals"]:
            for k, v in d["totals"]:
                story.append(self._label_value(k + ":", v))

        # ---- amount in words box ----------------------------------
        if d["amount_in_words"]:
            story.append(self._box([
                self._p("Amount in Words:", size=10, leading=13, bold=True),
                self._p(d["amount_in_words"], size=10, leading=13),
            ]))

        # ---- payment info box -------------------------------------
        pay = d["payment_info"]
        if pay["label"] or pay["lines"]:
            items = []
            if pay["label"]:
                items.append(self._p(pay["label"], size=10, leading=13,
                                     bold=True))
            items += [self._p(l, size=9.5, leading=12) for l in pay["lines"]]
            story.append(self._box(items))

        # ---- signature box ----------------------------------------
        sig = d["signatory"]
        if sig["label"] or sig["for"]:
            items = []
            company = sig["for"] or seller["name"]
            if company:
                items.append(self._p(f"For {company}:", size=10.5,
                                     leading=14, bold=True, align=TA_RIGHT))
            items.append(Spacer(1, 34))
            if sig["label"]:
                items.append(self._p(sig["label"], size=10.5, leading=14,
                                     bold=True, align=TA_RIGHT))
            story.append(self._box(items))

        # ---- footer notes -----------------------------------------
        if d["notes"]:
            story.append(Spacer(1, 4))
            for line in d["notes"]:
                story.append(self._p(line, size=9, leading=11.5))

        return story