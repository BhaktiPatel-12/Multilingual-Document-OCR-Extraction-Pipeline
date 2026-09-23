# from pathlib import Path
# import json
# import re
# from html import unescape

# from reportlab.lib import colors
# from reportlab.lib.enums import TA_LEFT, TA_CENTER
# from reportlab.lib.pagesizes import A4
# from reportlab.lib.styles import ParagraphStyle
# from reportlab.lib.units import mm
# from reportlab.platypus import (
#     SimpleDocTemplate,
#     Paragraph,
#     Spacer,
#     Table,
#     TableStyle,
#     PageBreak,
#     KeepTogether,
#     Flowable,
# )
# from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont


# class LanguageHighlightBox(Flowable):

#     def __init__(
#         self,
#         paragraph,
#         language,
#         background_color,
#         border_color,
#         label_color,
#         max_width=170 * mm,
#     ):
#         super().__init__()

#         self.paragraph = paragraph
#         self.language = language
#         self.background_color = background_color
#         self.border_color = border_color
#         self.label_color = label_color
#         self.max_width = max_width

#         self.padding = 6
#         self.label_height = 17

#         self.width = max_width
#         self.height = 0

#     def wrap(self, availWidth, availHeight):

#         self.width = min(
#             self.max_width,
#             availWidth
#         )

#         paragraph_width = (
#             self.width - self.padding * 2
#         )

#         _, paragraph_height = self.paragraph.wrap(
#             paragraph_width,
#             availHeight
#         )

#         self.height = (
#             paragraph_height
#             + self.padding * 2
#             + self.label_height
#         )

#         return self.width, self.height

#     def draw(self):

#         canvas = self.canv

#         canvas.setFillColor(
#             self.background_color
#         )

#         canvas.setStrokeColor(
#             self.border_color
#         )

#         canvas.setLineWidth(0.8)

#         canvas.roundRect(
#             0,
#             0,
#             self.width,
#             self.height,
#             5,
#             fill=1,
#             stroke=1,
#         )

#         label_width = 78

#         canvas.setFillColor(
#             self.label_color
#         )

#         canvas.roundRect(
#             self.width - label_width - 5,
#             self.height - self.label_height - 2,
#             label_width,
#             self.label_height,
#             3,
#             fill=1,
#             stroke=0,
#         )

#         canvas.setFillColor(
#             colors.white
#         )

#         canvas.setFont(
#             "Helvetica-Bold",
#             7,
#         )

#         canvas.drawCentredString(
#             self.width - (label_width / 2) - 5,
#             self.height - 13,
#             self.language.upper(),
#         )

#         self.paragraph.drawOn(
#             canvas,
#             self.padding,
#             self.padding,
#         )


# class LanguageHighlightedPDFService:

#     def __init__(
#         self,
#         output_dir="output/pdf",
#         fonts_dir="fonts",
#     ):

#         self.output_dir = Path(output_dir)

#         self.output_dir.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         self.fonts_dir = Path(fonts_dir)

#         if not self.fonts_dir.exists():
#             self.fonts_dir = Path("backend/fonts")

#         self.fonts = {
#             "latin": "Helvetica",
#             "latin_bold": "Helvetica-Bold",
#             "devanagari": "Helvetica",
#             "devanagari_bold": "Helvetica-Bold",
#             "gujarati": "Helvetica",
#             "gujarati_bold": "Helvetica-Bold",
#         }

#         self.register_fonts()

#     # =========================================================
#     # FONT SEARCH
#     # =========================================================

#     def _find_font(self, filenames):

#         search_dirs = [
#             self.fonts_dir,
#             Path("fonts"),
#             Path("backend/fonts"),
#             Path("C:/Windows/Fonts"),
#         ]

#         for directory in search_dirs:

#             for filename in filenames:

#                 path = directory / filename

#                 if path.exists():
#                     return path

#         return None

#     # =========================================================
#     # FONT REGISTRATION
#     # =========================================================

#     def register_fonts(self):

#         print("Searching for Unicode fonts...")

#         # -----------------------------------------------------
#         # DEVANAGARI
#         # -----------------------------------------------------

#         devanagari_regular = self._find_font([
#             "NotoSansDevanagari-Regular.ttf",
#             "NotoSansDevanagari-Regular.otf",
#             "Nirmala.ttf",
#             "NirmalaUI.ttf",
#         ])

#         devanagari_bold = self._find_font([
#             "NotoSansDevanagari-Bold.ttf",
#             "NotoSansDevanagari-Bold.otf",
#         ])

#         if devanagari_regular:

#             try:

#                 pdfmetrics.registerFont(
#                     TTFont(
#                         "HighlightDevanagari",
#                         str(devanagari_regular)
#                     )
#                 )

#                 self.fonts["devanagari"] = (
#                     "HighlightDevanagari"
#                 )

#                 print(
#                     f"Hindi font: {devanagari_regular}"
#                 )

#             except Exception as e:

#                 print(
#                     f"WARNING: Hindi font registration failed: {e}"
#                 )

#         else:

#             print(
#                 "WARNING: Hindi font not found."
#             )

#         if devanagari_bold:

#             try:

#                 pdfmetrics.registerFont(
#                     TTFont(
#                         "HighlightDevanagariBold",
#                         str(devanagari_bold)
#                     )
#                 )

#                 self.fonts["devanagari_bold"] = (
#                     "HighlightDevanagariBold"
#                 )

#             except Exception as e:

#                 print(
#                     f"WARNING: Hindi bold font failed: {e}"
#                 )

#         else:

#             self.fonts["devanagari_bold"] = (
#                 self.fonts["devanagari"]
#             )

#         # -----------------------------------------------------
#         # GUJARATI
#         # -----------------------------------------------------

#         gujarati_regular = self._find_font([
#             "NotoSansGujarati-Regular.ttf",
#             "NotoSansGujarati-Regular.otf",
#             "Nirmala.ttf",
#             "NirmalaUI.ttf",
#         ])

#         gujarati_bold = self._find_font([
#             "NotoSansGujarati-Bold.ttf",
#             "NotoSansGujarati-Bold.otf",
#         ])

#         if gujarati_regular:

#             try:

#                 pdfmetrics.registerFont(
#                     TTFont(
#                         "HighlightGujarati",
#                         str(gujarati_regular)
#                     )
#                 )

#                 self.fonts["gujarati"] = (
#                     "HighlightGujarati"
#                 )

#                 print(
#                     f"Gujarati font: {gujarati_regular}"
#                 )

#             except Exception as e:

#                 print(
#                     f"WARNING: Gujarati font registration failed: {e}"
#                 )

#         else:

#             print(
#                 "WARNING: Gujarati font not found."
#             )

#         if gujarati_bold:

#             try:

#                 pdfmetrics.registerFont(
#                     TTFont(
#                         "HighlightGujaratiBold",
#                         str(gujarati_bold)
#                     )
#                 )

#                 self.fonts["gujarati_bold"] = (
#                     "HighlightGujaratiBold"
#                 )

#             except Exception as e:

#                 print(
#                     f"WARNING: Gujarati bold font failed: {e}"
#                 )

#         else:

#             self.fonts["gujarati_bold"] = (
#                 self.fonts["gujarati"]
#             )

#         print()
#         print("Registered highlighted PDF fonts:")
#         print(self.fonts)

#     # =========================================================
#     # SCRIPT DETECTION
#     # =========================================================

#     def character_script(self, char):

#         code = ord(char)

#         if 0x0900 <= code <= 0x097F:
#             return "devanagari"

#         if 0x0A80 <= code <= 0x0AFF:
#             return "gujarati"

#         return "latin"

#     # =========================================================
#     # LANGUAGE DETECTION
#     # =========================================================

#     def detect_language(self, text):

#         if not text:
#             return "unknown"

#         devanagari_count = 0
#         gujarati_count = 0
#         latin_count = 0

#         for char in text:

#             code = ord(char)

#             if 0x0900 <= code <= 0x097F:

#                 devanagari_count += 1

#             elif 0x0A80 <= code <= 0x0AFF:

#                 gujarati_count += 1

#             elif char.isalpha():

#                 latin_count += 1

#         scripts = []

#         if devanagari_count > 0:
#             scripts.append("hindi")

#         if gujarati_count > 0:
#             scripts.append("gujarati")

#         if latin_count > 0:
#             scripts.append("english")

#         if not scripts:
#             return "unknown"

#         if len(scripts) == 1:
#             return scripts[0]

#         if set(scripts) == {
#             "hindi",
#             "english",
#         }:
#             return "hindi + english"

#         if set(scripts) == {
#             "gujarati",
#             "english",
#         }:
#             return "gujarati + english"

#         return "mixed"

#     # =========================================================
#     # COLORS
#     # =========================================================

#     def get_language_colors(self, language):

#         language = language.lower()

#         # ENGLISH - Yellow
#         if language == "english":

#             return (
#                 colors.HexColor("#FFF4B8"),
#                 colors.HexColor("#E6C200"),
#                 colors.HexColor("#B79500"),
#             )

#         # HINDI - Blue
#         if language == "hindi":

#             return (
#                 colors.HexColor("#CFE8FF"),
#                 colors.HexColor("#4A90E2"),
#                 colors.HexColor("#2171B5"),
#             )

#         # GUJARATI - Green
#         if language == "gujarati":

#             return (
#                 colors.HexColor("#D5F5D5"),
#                 colors.HexColor("#4CAF50"),
#                 colors.HexColor("#2E7D32"),
#             )

#         # HINDI + ENGLISH
#         if language == "hindi + english":

#             return (
#                 colors.HexColor("#E3E8FF"),
#                 colors.HexColor("#6879D0"),
#                 colors.HexColor("#4654A5"),
#             )

#         # GUJARATI + ENGLISH
#         if language == "gujarati + english":

#             return (
#                 colors.HexColor("#DDF2D7"),
#                 colors.HexColor("#66A856"),
#                 colors.HexColor("#3F7135"),
#             )

#         # MIXED
#         return (
#             colors.HexColor("#EBDFFF"),
#             colors.HexColor("#8E63CE"),
#             colors.HexColor("#6840A5"),
#         )

#     # =========================================================
#     # HTML CLEANING
#     # =========================================================

#     def clean_html(self, html):

#         if html is None:
#             return ""

#         text = str(html)

#         text = re.sub(
#             r"<br\s*/?>",
#             "\n",
#             text,
#             flags=re.IGNORECASE,
#         )

#         text = re.sub(
#             r"</p>",
#             "\n",
#             text,
#             flags=re.IGNORECASE,
#         )

#         text = re.sub(
#             r"<[^>]+>",
#             "",
#             text,
#         )

#         text = unescape(text)

#         return text.strip()

#     # =========================================================
#     # REPORTLAB ESCAPING
#     # =========================================================

#     def escape_text(self, text):

#         return (
#             text
#             .replace("&", "&amp;")
#             .replace("<", "&lt;")
#             .replace(">", "&gt;")
#         )

#     # =========================================================
#     # UNICODE FORMATTING
#     # =========================================================

#     def format_unicode_text(
#         self,
#         text,
#         bold=False,
#     ):

#         if not text:
#             return ""

#         output = []

#         current_script = None
#         current_text = ""

#         def flush():

#             nonlocal current_script
#             nonlocal current_text

#             if not current_text:
#                 return

#             if current_script == "devanagari":

#                 font = (
#                     self.fonts["devanagari_bold"]
#                     if bold
#                     else self.fonts["devanagari"]
#                 )

#             elif current_script == "gujarati":

#                 font = (
#                     self.fonts["gujarati_bold"]
#                     if bold
#                     else self.fonts["gujarati"]
#                 )

#             else:

#                 font = (
#                     self.fonts["latin_bold"]
#                     if bold
#                     else self.fonts["latin"]
#                 )

#             escaped = self.escape_text(
#                 current_text
#             )

#             escaped = escaped.replace(
#                 "\n",
#                 "<br/>"
#             )

#             output.append(
#                 f'<font name="{font}">'
#                 f'{escaped}'
#                 f'</font>'
#             )

#             current_text = ""
#             current_script = None

#         for char in text:

#             if char == "\n":

#                 current_text += char
#                 continue

#             script = self.character_script(
#                 char
#             )

#             # Keep spaces with current text
#             if char.isspace():

#                 current_text += char
#                 continue

#             if current_script is None:

#                 current_script = script
#                 current_text = char

#             elif script == current_script:

#                 current_text += char

#             else:

#                 flush()

#                 current_script = script
#                 current_text = char

#         flush()

#         return "".join(output)

#     # =========================================================
#     # PARAGRAPH
#     # =========================================================

#     def make_paragraph(
#         self,
#         text,
#         bold=False,
#         font_size=9,
#         alignment=TA_LEFT,
#     ):

#         formatted = self.format_unicode_text(
#             text,
#             bold=bold,
#         )

#         style = ParagraphStyle(
#             name="HighlightedOCRText",
#             fontName=self.fonts["latin"],
#             fontSize=font_size,
#             leading=font_size * 1.4,
#             alignment=alignment,
#             spaceBefore=0,
#             spaceAfter=0,
#         )

#         return Paragraph(
#             formatted,
#             style,
#         )

#     # =========================================================
#     # TABLE HTML
#     # =========================================================

#     def parse_table_html(self, html):

#         if not html:
#             return None

#         rows = re.findall(
#             r"<tr[^>]*>(.*?)</tr>",
#             html,
#             flags=re.IGNORECASE | re.DOTALL,
#         )

#         if not rows:
#             return None

#         table_data = []

#         for row in rows:

#             cells = re.findall(
#                 r"<(?:td|th)[^>]*>(.*?)"
#                 r"</(?:td|th)>",
#                 row,
#                 flags=re.IGNORECASE | re.DOTALL,
#             )

#             parsed_row = []

#             for cell in cells:

#                 text = self.clean_html(
#                     cell
#                 )

#                 if not text:
#                     text = " "

#                 paragraph = self.make_paragraph(
#                     text,
#                     font_size=8,
#                 )

#                 parsed_row.append(
#                     paragraph
#                 )

#             if parsed_row:

#                 table_data.append(
#                     parsed_row
#                 )

#         if not table_data:
#             return None

#         return table_data

#     # =========================================================
#     # TABLE
#     # =========================================================

#     def make_table(self, html):

#         table_data = self.parse_table_html(
#             html
#         )

#         if not table_data:
#             return None

#         # Find maximum number of columns
#         max_columns = max(
#             len(row)
#             for row in table_data
#         )

#         normalized_rows = []

#         for row in table_data:

#             while len(row) < max_columns:

#                 row.append(
#                     Paragraph(
#                         " ",
#                         ParagraphStyle(
#                             "EmptyCell",
#                             fontSize=8,
#                         )
#                     )
#                 )

#             normalized_rows.append(
#                 row
#             )

#         available_width = 170 * mm

#         column_width = (
#             available_width / max_columns
#         )

#         table = Table(
#             normalized_rows,
#             colWidths=[
#                 column_width
#             ] * max_columns,
#             repeatRows=1,
#             hAlign="LEFT",
#         )

#         table.setStyle(
#             TableStyle([
#                 (
#                     "GRID",
#                     (0, 0),
#                     (-1, -1),
#                     0.6,
#                     colors.grey,
#                 ),
#                 (
#                     "VALIGN",
#                     (0, 0),
#                     (-1, -1),
#                     "MIDDLE",
#                 ),
#                 (
#                     "LEFTPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     5,
#                 ),
#                 (
#                     "RIGHTPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     5,
#                 ),
#                 (
#                     "TOPPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     5,
#                 ),
#                 (
#                     "BOTTOMPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     5,
#                 ),
#             ])
#         )

#         return table

#     # =========================================================
#     # DIRECT SURYA JSON READER
#     # =========================================================

#     def read_surya_json(self, json_file):

#         json_file = Path(
#             json_file
#         )

#         with open(
#             json_file,
#             "r",
#             encoding="utf-8",
#         ) as file:

#             raw_data = json.load(file)

#         pages = []

#         # -----------------------------------------------------
#         # YOUR ACTUAL SURYA FORMAT
#         #
#         # {
#         #   "page_001_original": [
#         #       {
#         #           "blocks": [...]
#         #       }
#         #   ]
#         # }
#         # -----------------------------------------------------

#         if isinstance(
#             raw_data,
#             dict
#         ):

#             for page_name, page_results in raw_data.items():

#                 match = re.search(
#                     r"page[_-]?(\d+)",
#                     str(page_name),
#                     flags=re.IGNORECASE,
#                 )

#                 if match:

#                     page_number = int(
#                         match.group(1)
#                     )

#                 else:

#                     page_number = (
#                         len(pages) + 1
#                     )

#                 if not isinstance(
#                     page_results,
#                     list
#                 ):
#                     continue

#                 for page_result in page_results:

#                     if not isinstance(
#                         page_result,
#                         dict
#                     ):
#                         continue

#                     blocks = page_result.get(
#                         "blocks",
#                         []
#                     )

#                     normalized_blocks = []

#                     for block in blocks:

#                         if not isinstance(
#                             block,
#                             dict
#                         ):
#                             continue

#                         if block.get(
#                             "skipped",
#                             False
#                         ):
#                             continue

#                         html = block.get(
#                             "html",
#                             ""
#                         )

#                         if not html:
#                             continue

#                         normalized_blocks.append({
#                             "label": block.get(
#                                 "label",
#                                 "Text"
#                             ),
#                             "raw_label": block.get(
#                                 "raw_label",
#                                 block.get(
#                                     "label",
#                                     "Text"
#                                 )
#                             ),
#                             "reading_order": block.get(
#                                 "reading_order",
#                                 0
#                             ),
#                             "html": html,
#                             "bbox": block.get(
#                                 "bbox"
#                             ),
#                             "polygon": block.get(
#                                 "polygon"
#                             ),
#                         })

#                     normalized_blocks.sort(
#                         key=lambda block: block.get(
#                             "reading_order",
#                             0
#                         )
#                     )

#                     pages.append({
#                         "page": page_number,
#                         "source": page_name,
#                         "blocks": normalized_blocks,
#                     })

#         # -----------------------------------------------------
#         # ALTERNATIVE LIST FORMAT
#         # -----------------------------------------------------

#         elif isinstance(
#             raw_data,
#             list
#         ):

#             for index, page_result in enumerate(
#                 raw_data,
#                 start=1
#             ):

#                 if not isinstance(
#                     page_result,
#                     dict
#                 ):
#                     continue

#                 blocks = page_result.get(
#                     "blocks",
#                     []
#                 )

#                 normalized_blocks = []

#                 for block in blocks:

#                     if not isinstance(
#                         block,
#                         dict
#                     ):
#                         continue

#                     if block.get(
#                         "skipped",
#                         False
#                     ):
#                         continue

#                     if not block.get(
#                         "html",
#                         ""
#                     ):
#                         continue

#                     normalized_blocks.append({
#                         "label": block.get(
#                             "label",
#                             "Text"
#                         ),
#                         "reading_order": block.get(
#                             "reading_order",
#                             0
#                         ),
#                         "html": block.get(
#                             "html",
#                             ""
#                         ),
#                         "bbox": block.get(
#                             "bbox"
#                         ),
#                     })

#                 normalized_blocks.sort(
#                     key=lambda block: block.get(
#                         "reading_order",
#                         0
#                     )
#                 )

#                 pages.append({
#                     "page": index,
#                     "source": str(
#                         json_file
#                     ),
#                     "blocks": normalized_blocks,
#                 })

#         return pages

#     # =========================================================
#     # CREATE HIGHLIGHTED PDF
#     # =========================================================

#     def create_from_surya_json(
#         self,
#         json_files,
#         output_filename="input_language_highlighted.pdf",
#     ):

#         print()
#         print("=" * 70)
#         print("ASTRA OCR - LANGUAGE HIGHLIGHTED PDF")
#         print("=" * 70)

#         all_pages = []

#         # -----------------------------------------------------
#         # READ EVERY SURYA JSON FILE
#         # -----------------------------------------------------

#         for json_file in json_files:

#             print(
#                 f"Reading: {json_file}"
#             )

#             pages = self.read_surya_json(
#                 json_file
#             )

#             all_pages.extend(
#                 pages
#             )

#         # Sort pages
#         all_pages.sort(
#             key=lambda page: page.get(
#                 "page",
#                 0
#             )
#         )

#         if not all_pages:

#             raise ValueError(
#                 "No pages could be extracted "
#                 "from the Surya JSON files."
#             )

#         output_path = (
#             self.output_dir
#             / output_filename
#         )

#         # -----------------------------------------------------
#         # REPORTLAB DOCUMENT
#         # -----------------------------------------------------

#         doc = SimpleDocTemplate(
#             str(output_path),
#             pagesize=A4,
#             rightMargin=20 * mm,
#             leftMargin=20 * mm,
#             topMargin=18 * mm,
#             bottomMargin=18 * mm,
#         )

#         story = []

#         # =====================================================
#         # TITLE
#         # =====================================================

#         title_style = ParagraphStyle(
#             name="HighlightTitle",
#             fontName="Helvetica-Bold",
#             fontSize=15,
#             leading=19,
#             alignment=TA_CENTER,
#             spaceAfter=8,
#         )

#         story.append(
#             Paragraph(
#                 "ASTRA OCR - Language Highlighted Document",
#                 title_style,
#             )
#         )

#         subtitle_style = ParagraphStyle(
#             name="HighlightSubtitle",
#             fontName="Helvetica",
#             fontSize=8,
#             leading=10,
#             alignment=TA_CENTER,
#             textColor=colors.grey,
#             spaceAfter=8,
#         )

#         story.append(
#             Paragraph(
#                 "English • Hindi • Gujarati",
#                 subtitle_style,
#             )
#         )

#         # =====================================================
#         # LEGEND
#         # =====================================================

#         legend_style = ParagraphStyle(
#             name="Legend",
#             fontName="Helvetica-Bold",
#             fontSize=8,
#             alignment=TA_CENTER,
#         )

#         legend = Table(
#             [[
#                 Paragraph(
#                     "ENGLISH",
#                     legend_style
#                 ),
#                 Paragraph(
#                     "HINDI",
#                     legend_style
#                 ),
#                 Paragraph(
#                     "GUJARATI",
#                     legend_style
#                 ),
#                 Paragraph(
#                     "MIXED",
#                     legend_style
#                 ),
#             ]],
#             colWidths=[
#                 38 * mm,
#                 38 * mm,
#                 38 * mm,
#                 38 * mm,
#             ],
#         )

#         legend.setStyle(
#             TableStyle([
#                 (
#                     "BACKGROUND",
#                     (0, 0),
#                     (0, 0),
#                     colors.HexColor("#FFF4B8"),
#                 ),
#                 (
#                     "BACKGROUND",
#                     (1, 0),
#                     (1, 0),
#                     colors.HexColor("#CFE8FF"),
#                 ),
#                 (
#                     "BACKGROUND",
#                     (2, 0),
#                     (2, 0),
#                     colors.HexColor("#D5F5D5"),
#                 ),
#                 (
#                     "BACKGROUND",
#                     (3, 0),
#                     (3, 0),
#                     colors.HexColor("#EBDFFF"),
#                 ),
#                 (
#                     "GRID",
#                     (0, 0),
#                     (-1, -1),
#                     0.5,
#                     colors.grey,
#                 ),
#                 (
#                     "ALIGN",
#                     (0, 0),
#                     (-1, -1),
#                     "CENTER",
#                 ),
#                 (
#                     "VALIGN",
#                     (0, 0),
#                     (-1, -1),
#                     "MIDDLE",
#                 ),
#                 (
#                     "TOPPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     5,
#                 ),
#                 (
#                     "BOTTOMPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     5,
#                 ),
#             ])
#         )

#         story.append(
#             legend
#         )

#         story.append(
#             Spacer(1, 10)
#         )

#         # =====================================================
#         # PAGES
#         # =====================================================

#         for page_index, page in enumerate(
#             all_pages
#         ):

#             page_number = page.get(
#                 "page",
#                 page_index + 1
#             )

#             blocks = page.get(
#                 "blocks",
#                 []
#             )

#             print(
#                 f"Building highlighted PDF "
#                 f"page {page_number}: "
#                 f"{len(blocks)} blocks"
#             )

#             # -------------------------------------------------
#             # PAGE HEADER
#             # -------------------------------------------------

#             page_title_style = ParagraphStyle(
#                 name="PageTitle",
#                 fontName="Helvetica-Bold",
#                 fontSize=10,
#                 leading=13,
#                 alignment=TA_LEFT,
#                 spaceAfter=7,
#             )

#             story.append(
#                 Paragraph(
#                     f"Page {page_number}",
#                     page_title_style,
#                 )
#             )

#             # -------------------------------------------------
#             # SORT BY READING ORDER
#             # -------------------------------------------------

#             blocks = sorted(
#                 blocks,
#                 key=lambda block: block.get(
#                     "reading_order",
#                     0
#                 )
#             )

#             # -------------------------------------------------
#             # BLOCKS
#             # -------------------------------------------------

#             for block in blocks:

#                 label = str(
#                     block.get(
#                         "label",
#                         "Text"
#                     )
#                 )

#                 html = block.get(
#                     "html",
#                     ""
#                 )

#                 if not html:
#                     continue

#                 # -------------------------------------------------
#                 # TABLE
#                 # -------------------------------------------------

#                 if label.lower() == "table":

#                     table = self.make_table(
#                         html
#                     )

#                     if table:

#                         story.append(
#                             table
#                         )

#                         story.append(
#                             Spacer(1, 8)
#                         )

#                     continue

#                 # -------------------------------------------------
#                 # NORMAL TEXT
#                 # -------------------------------------------------

#                 text = self.clean_html(
#                     html
#                 )

#                 if not text:
#                     continue

#                 language = self.detect_language(
#                     text
#                 )

#                 (
#                     background_color,
#                     border_color,
#                     label_color,
#                 ) = self.get_language_colors(
#                     language
#                 )

#                 # -------------------------------------------------
#                 # HEADER FORMATTING
#                 # -------------------------------------------------

#                 is_header = label.lower() in [
#                     "pageheader",
#                     "page_header",
#                     "sectionheader",
#                     "section_header",
#                     "title",
#                 ]

#                 if is_header:

#                     font_size = 11
#                     bold = True

#                 else:

#                     font_size = 9
#                     bold = False

#                 paragraph = self.make_paragraph(
#                     text,
#                     bold=bold,
#                     font_size=font_size,
#                 )

#                 highlight_box = LanguageHighlightBox(
#                     paragraph=paragraph,
#                     language=language,
#                     background_color=background_color,
#                     border_color=border_color,
#                     label_color=label_color,
#                     max_width=170 * mm,
#                 )

#                 story.append(
#                     KeepTogether([
#                         highlight_box,
#                         Spacer(1, 6),
#                     ])
#                 )

#             # -------------------------------------------------
#             # PAGE BREAK
#             # -------------------------------------------------

#             if page_index < len(all_pages) - 1:

#                 story.append(
#                     PageBreak()
#                 )

#         # =====================================================
#         # BUILD PDF
#         # =====================================================

#         doc.build(
#             story
#         )

#         print()
#         print(
#             "Language highlighted PDF saved to:"
#         )

#         print(
#             output_path
#         )

#         print(
#             "=" * 70
#         )

#         return str(
#             output_path
#         )





# from pathlib import Path
# import json
# import re
# import html

# from reportlab.lib import colors
# from reportlab.lib.pagesizes import A4
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# from reportlab.lib.enums import TA_LEFT, TA_CENTER
# from reportlab.lib.units import mm
# from reportlab.platypus import (
#     SimpleDocTemplate,
#     Paragraph,
#     Spacer,
#     Table,
#     TableStyle,
#     PageBreak,
#     KeepTogether,
# )
# from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont


# class LanguageHighlightedPDFService:
#     """
#     Creates a text-only PDF from raw Surya OCR JSON.

#     Features:
#         - English highlighting
#         - Hindi highlighting
#         - Gujarati highlighting
#         - Mixed-language highlighting
#         - Language labels
#         - Structured tables
#         - Reading order
#         - Unicode fonts
#         - No original PDF images
#     """

#     # ============================================================
#     # COLORS
#     # ============================================================

#     ENGLISH_BG = colors.HexColor("#DCEEFF")
#     HINDI_BG = colors.HexColor("#DFF5E1")
#     GUJARATI_BG = colors.HexColor("#FFF1CC")
#     MIXED_BG = colors.HexColor("#EDEDED")
#     UNKNOWN_BG = colors.HexColor("#F2F2F2")

#     ENGLISH_LABEL = colors.HexColor("#1769AA")
#     HINDI_LABEL = colors.HexColor("#218838")
#     GUJARATI_LABEL = colors.HexColor("#B77900")
#     MIXED_LABEL = colors.HexColor("#666666")

#     BORDER = colors.HexColor("#B8B8B8")

#     # ============================================================
#     # INITIALIZATION
#     # ============================================================

#     def __init__(
#         self,
#         output_dir="output/pdf",
#         fonts_dir="fonts",
#     ):
#         self.output_dir = Path(output_dir)
#         self.output_dir.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         self.fonts_dir = Path(fonts_dir)

#         self.fonts = {}

#         self._register_fonts()

#         self.styles = getSampleStyleSheet()

#         self.body_style = ParagraphStyle(
#             "AstraHighlightBody",
#             parent=self.styles["BodyText"],
#             fontName=self.fonts["latin"],
#             fontSize=9.5,
#             leading=13,
#             alignment=TA_LEFT,
#             spaceAfter=2,
#         )

#         self.header_style = ParagraphStyle(
#             "AstraHighlightHeader",
#             parent=self.styles["Heading2"],
#             fontName=self.fonts["latin_bold"],
#             fontSize=12,
#             leading=15,
#             alignment=TA_CENTER,
#             spaceBefore=4,
#             spaceAfter=8,
#         )

#         self.label_style = ParagraphStyle(
#             "AstraLanguageLabel",
#             parent=self.styles["BodyText"],
#             fontName=self.fonts["latin_bold"],
#             fontSize=6.5,
#             leading=8,
#             alignment=TA_LEFT,
#         )

#     # ============================================================
#     # FONT DISCOVERY
#     # ============================================================

#     def _find_font(self, names):
#         search_dirs = [
#             self.fonts_dir,
#             Path("backend/fonts"),
#             Path("C:/Windows/Fonts"),
#         ]

#         for directory in search_dirs:

#             if not directory.exists():
#                 continue

#             for name in names:

#                 candidate = directory / name

#                 if candidate.exists():
#                     return candidate

#         return None

#     # ============================================================
#     # REGISTER FONTS
#     # ============================================================

#     def _register_fonts(self):

#         print("Searching for Unicode fonts...")

#         latin_regular = self._find_font([
#             "NotoSans-Regular.ttf",
#             "DejaVuSans.ttf",
#         ])

#         latin_bold = self._find_font([
#             "NotoSans-Bold.ttf",
#             "DejaVuSans-Bold.ttf",
#         ])

#         devanagari_regular = self._find_font([
#             "NotoSansDevanagari-Regular.ttf",
#         ])

#         devanagari_bold = self._find_font([
#             "NotoSansDevanagari-Bold.ttf",
#         ])

#         gujarati_regular = self._find_font([
#             "NotoSansGujarati-Regular.ttf",
#         ])

#         gujarati_bold = self._find_font([
#             "NotoSansGujarati-Bold.ttf",
#         ])

#         # --------------------------------------------------------
#         # LATIN
#         # --------------------------------------------------------

#         if latin_regular:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraHighlightLatin",
#                     str(latin_regular)
#                 )
#             )

#             self.fonts["latin"] = (
#                 "AstraHighlightLatin"
#             )

#         else:

#             self.fonts["latin"] = "Helvetica"

#         if latin_bold:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraHighlightLatinBold",
#                     str(latin_bold)
#                 )
#             )

#             self.fonts["latin_bold"] = (
#                 "AstraHighlightLatinBold"
#             )

#         else:

#             self.fonts["latin_bold"] = (
#                 "Helvetica-Bold"
#             )

#         # --------------------------------------------------------
#         # DEVANAGARI
#         # --------------------------------------------------------

#         if devanagari_regular:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraHighlightDevanagari",
#                     str(devanagari_regular)
#                 )
#             )

#             self.fonts["devanagari"] = (
#                 "AstraHighlightDevanagari"
#             )

#             print(
#                 f"Devanagari font: "
#                 f"{devanagari_regular}"
#             )

#         else:

#             self.fonts["devanagari"] = (
#                 self.fonts["latin"]
#             )

#             print(
#                 "WARNING: Devanagari font not found."
#             )

#         if devanagari_bold:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraHighlightDevanagariBold",
#                     str(devanagari_bold)
#                 )
#             )

#             self.fonts["devanagari_bold"] = (
#                 "AstraHighlightDevanagariBold"
#             )

#         else:

#             self.fonts["devanagari_bold"] = (
#                 self.fonts["devanagari"]
#             )

#         # --------------------------------------------------------
#         # GUJARATI
#         # --------------------------------------------------------

#         if gujarati_regular:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraHighlightGujarati",
#                     str(gujarati_regular)
#                 )
#             )

#             self.fonts["gujarati"] = (
#                 "AstraHighlightGujarati"
#             )

#             print(
#                 f"Gujarati font: "
#                 f"{gujarati_regular}"
#             )

#         else:

#             self.fonts["gujarati"] = (
#                 self.fonts["latin"]
#             )

#             print(
#                 "WARNING: Gujarati font not found."
#             )

#         if gujarati_bold:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraHighlightGujaratiBold",
#                     str(gujarati_bold)
#                 )
#             )

#             self.fonts["gujarati_bold"] = (
#                 "AstraHighlightGujaratiBold"
#             )

#         else:

#             self.fonts["gujarati_bold"] = (
#                 self.fonts["gujarati"]
#             )

#         print()
#         print(
#             "Registered highlighted PDF fonts:"
#         )

#         print(self.fonts)

#     # ============================================================
#     # LANGUAGE DETECTION
#     # ============================================================

#     @staticmethod
#     def detect_language(text):

#         if not text:
#             return "unknown"

#         devanagari = 0
#         gujarati = 0
#         latin = 0

#         for char in text:

#             code = ord(char)

#             if (
#                 0x0900
#                 <= code
#                 <= 0x097F
#             ):
#                 devanagari += 1

#             elif (
#                 0x0A80
#                 <= code
#                 <= 0x0AFF
#             ):
#                 gujarati += 1

#             elif (
#                 ("A" <= char <= "Z")
#                 or ("a" <= char <= "z")
#             ):
#                 latin += 1

#         total = (
#             devanagari
#             + gujarati
#             + latin
#         )

#         if total == 0:
#             return "unknown"

#         active = 0

#         if devanagari:
#             active += 1

#         if gujarati:
#             active += 1

#         if latin:
#             active += 1

#         if active > 1:
#             return "mixed"

#         if devanagari:
#             return "hindi"

#         if gujarati:
#             return "gujarati"

#         if latin:
#             return "english"

#         return "unknown"

#     # ============================================================
#     # LANGUAGE NAME
#     # ============================================================

#     @staticmethod
#     def language_name(language):

#         mapping = {
#             "en": "English",
#             "eng": "English",
#             "english": "English",

#             "hin": "Hindi",
#             "hindi": "Hindi",

#             "guj": "Gujarati",
#             "gujarati": "Gujarati",

#             "mixed": "Mixed",

#             "unknown": "Unknown",
#         }

#         return mapping.get(
#             str(language).lower(),
#             str(language)
#         )

#     # ============================================================
#     # CLEAN HTML
#     # ============================================================

#     @staticmethod
#     def clean_html(value):

#         if value is None:
#             return ""

#         value = str(value)

#         value = value.replace(
#             "<br/>",
#             "\n"
#         )

#         value = value.replace(
#             "<br />",
#             "\n"
#         )

#         value = value.replace(
#             "<br>",
#             "\n"
#         )

#         value = re.sub(
#             r"<[^>]+>",
#             "",
#             value
#         )

#         return html.unescape(
#             value
#         ).strip()

#     # ============================================================
#     # FORMAT TEXT WITH CORRECT FONT
#     # ============================================================

#     def format_text(self, text):

#         if not text:
#             return ""

#         text = self.clean_html(
#             text
#         )

#         output = []

#         current_script = None
#         current_text = []

#         def flush():

#             nonlocal current_text
#             nonlocal current_script

#             if not current_text:
#                 return

#             value = "".join(
#                 current_text
#             )

#             escaped = html.escape(
#                 value
#             )

#             if current_script == "devanagari":

#                 font = self.fonts[
#                     "devanagari"
#                 ]

#             elif current_script == "gujarati":

#                 font = self.fonts[
#                     "gujarati"
#                 ]

#             else:

#                 font = self.fonts[
#                     "latin"
#                 ]

#             output.append(
#                 f'<font name="{font}">'
#                 f'{escaped}'
#                 f'</font>'
#             )

#             current_text = []

#         for char in text:

#             code = ord(char)

#             if (
#                 0x0900
#                 <= code
#                 <= 0x097F
#             ):

#                 script = "devanagari"

#             elif (
#                 0x0A80
#                 <= code
#                 <= 0x0AFF
#             ):

#                 script = "gujarati"

#             else:

#                 script = "latin"

#             if (
#                 current_script is not None
#                 and script != current_script
#             ):

#                 flush()

#             current_script = script

#             current_text.append(
#                 char
#             )

#         flush()

#         return "".join(
#             output
#         )

#     # ============================================================
#     # LANGUAGE COLORS
#     # ============================================================

#     def get_background(self, language):

#         language = str(
#             language
#         ).lower()

#         if language in (
#             "en",
#             "eng",
#             "english",
#         ):

#             return self.ENGLISH_BG

#         if language in (
#             "hin",
#             "hindi",
#         ):

#             return self.HINDI_BG

#         if language in (
#             "guj",
#             "gujarati",
#         ):

#             return self.GUJARATI_BG

#         if language == "mixed":

#             return self.MIXED_BG

#         return self.UNKNOWN_BG

#     def get_label_color(self, language):

#         language = str(
#             language
#         ).lower()

#         if language in (
#             "en",
#             "eng",
#             "english",
#         ):

#             return self.ENGLISH_LABEL

#         if language in (
#             "hin",
#             "hindi",
#         ):

#             return self.HINDI_LABEL

#         if language in (
#             "guj",
#             "gujarati",
#         ):

#             return self.GUJARATI_LABEL

#         return self.MIXED_LABEL

#     # ============================================================
#     # LOAD RAW SURYA JSON
#     # ============================================================

#     def load_surya_json(self, json_path):

#         json_path = Path(
#             json_path
#         )

#         with open(
#             json_path,
#             "r",
#             encoding="utf-8"
#         ) as file:

#             data = json.load(
#                 file
#             )

#         return data

#     # ============================================================
#     # EXTRACT BLOCKS
#     # ============================================================

#     def extract_blocks(self, data):

#         blocks = []

#         if not isinstance(
#             data,
#             dict
#         ):

#             return blocks

#         for page_name, page_data in data.items():

#             if not isinstance(
#                 page_data,
#                 list
#             ):

#                 continue

#             for page_item in page_data:

#                 if not isinstance(
#                     page_item,
#                     dict
#                 ):

#                     continue

#                 page_blocks = page_item.get(
#                     "blocks",
#                     []
#                 )

#                 if not isinstance(
#                     page_blocks,
#                     list
#                 ):

#                     continue

#                 for block in page_blocks:

#                     if not isinstance(
#                         block,
#                         dict
#                     ):

#                         continue

#                     if block.get(
#                         "skipped",
#                         False
#                     ):

#                         continue

#                     text = self.clean_html(
#                         block.get(
#                             "html",
#                             block.get(
#                                 "text",
#                                 ""
#                             )
#                         )
#                     )

#                     if not text:
#                         continue

#                     new_block = dict(
#                         block
#                     )

#                     new_block[
#                         "_page_name"
#                     ] = page_name

#                     new_block[
#                         "_text"
#                     ] = text

#                     blocks.append(
#                         new_block
#                     )

#         blocks.sort(
#             key=lambda block: (
#                 block.get(
#                     "_page_name",
#                     ""
#                 ),
#                 block.get(
#                     "reading_order",
#                     999999
#                 )
#             )
#         )

#         return blocks

#     # ============================================================
#     # EXTRACT TABLE ROWS
#     # ============================================================

#     def parse_table_html(self, text):

#         rows = re.findall(
#             r"<tr[^>]*>(.*?)</tr>",
#             text,
#             flags=re.IGNORECASE | re.DOTALL
#         )

#         if not rows:
#             return None

#         table_data = []

#         for row in rows:

#             cells = re.findall(
#                 r"<t[dh][^>]*>(.*?)</t[dh]>",
#                 row,
#                 flags=re.IGNORECASE | re.DOTALL
#             )

#             if not cells:
#                 continue

#             cleaned = []

#             for cell in cells:

#                 cell_text = self.clean_html(
#                     cell
#                 )

#                 cleaned.append(
#                     cell_text
#                 )

#             table_data.append(
#                 cleaned
#             )

#         if not table_data:
#             return None

#         max_columns = max(
#             len(row)
#             for row in table_data
#         )

#         for row in table_data:

#             while len(row) < max_columns:

#                 row.append("")

#         return table_data

#     # ============================================================
#     # CREATE TABLE
#     # ============================================================

#     def create_highlighted_table(
#         self,
#         table_data
#     ):

#         formatted_rows = []

#         for row in table_data:

#             formatted_row = []

#             for cell in row:

#                 language = self.detect_language(
#                     cell
#                 )

#                 label = self.language_name(
#                     language
#                 )

#                 background = self.get_background(
#                     language
#                 )

#                 content = self.format_text(
#                     cell
#                 )

#                 cell_style = ParagraphStyle(
#                     "HighlightedTableCell",
#                     parent=self.body_style,
#                     fontSize=7.5,
#                     leading=10,
#                 )

#                 paragraph = Paragraph(
#                     content or " ",
#                     cell_style
#                 )

#                 formatted_row.append(
#                     paragraph
#                 )

#             formatted_rows.append(
#                 formatted_row
#             )

#         column_count = max(
#             len(row)
#             for row in formatted_rows
#         )

#         available_width = (
#             A4[0]
#             - 30 * mm
#         )

#         column_width = (
#             available_width
#             / column_count
#         )

#         table = Table(
#             formatted_rows,
#             colWidths=[
#                 column_width
#             ] * column_count,
#             repeatRows=1,
#         )

#         commands = [
#             (
#                 "GRID",
#                 (0, 0),
#                 (-1, -1),
#                 0.5,
#                 self.BORDER
#             ),
#             (
#                 "VALIGN",
#                 (0, 0),
#                 (-1, -1),
#                 "TOP"
#             ),
#             (
#                 "LEFTPADDING",
#                 (0, 0),
#                 (-1, -1),
#                 4
#             ),
#             (
#                 "RIGHTPADDING",
#                 (0, 0),
#                 (-1, -1),
#                 4
#             ),
#             (
#                 "TOPPADDING",
#                 (0, 0),
#                 (-1, -1),
#                 4
#             ),
#             (
#                 "BOTTOMPADDING",
#                 (0, 0),
#                 (-1, -1),
#                 4
#             ),
#         ]

#         for row_index, row in enumerate(
#             table_data
#         ):

#             for column_index, cell in enumerate(
#                 row
#             ):

#                 language = self.detect_language(
#                     cell
#                 )

#                 background = self.get_background(
#                     language
#                 )

#                 commands.append(
#                     (
#                         "BACKGROUND",
#                         (
#                             column_index,
#                             row_index
#                         ),
#                         (
#                             column_index,
#                             row_index
#                         ),
#                         background
#                     )
#                 )

#         table.setStyle(
#             TableStyle(commands)
#         )

#         return table

#     # ============================================================
#     # LANGUAGE LEGEND
#     # ============================================================

#     def create_legend(self):

#         title = Paragraph(
#             "<b>Language Highlight Legend</b>",
#             self.header_style
#         )

#         legend_data = [
#             [
#                 Paragraph(
#                     '<b><font color="#1769AA">'
#                     'ENGLISH'
#                     '</font></b>',
#                     self.label_style
#                 ),
#                 Paragraph(
#                     '<b><font color="#218838">'
#                     'HINDI'
#                     '</font></b>',
#                     self.label_style
#                 ),
#                 Paragraph(
#                     '<b><font color="#B77900">'
#                     'GUJARATI'
#                     '</font></b>',
#                     self.label_style
#                 ),
#                 Paragraph(
#                     '<b><font color="#666666">'
#                     'MIXED'
#                     '</font></b>',
#                     self.label_style
#                 ),
#             ]
#         ]

#         legend = Table(
#             legend_data,
#             colWidths=[
#                 40 * mm,
#                 40 * mm,
#                 40 * mm,
#                 40 * mm,
#             ],
#         )

#         legend.setStyle(
#             TableStyle([
#                 (
#                     "BACKGROUND",
#                     (0, 0),
#                     (0, 0),
#                     self.ENGLISH_BG
#                 ),
#                 (
#                     "BACKGROUND",
#                     (1, 0),
#                     (1, 0),
#                     self.HINDI_BG
#                 ),
#                 (
#                     "BACKGROUND",
#                     (2, 0),
#                     (2, 0),
#                     self.GUJARATI_BG
#                 ),
#                 (
#                     "BACKGROUND",
#                     (3, 0),
#                     (3, 0),
#                     self.MIXED_BG
#                 ),
#                 (
#                     "BOX",
#                     (0, 0),
#                     (-1, -1),
#                     0.5,
#                     self.BORDER
#                 ),
#                 (
#                     "INNERGRID",
#                     (0, 0),
#                     (-1, -1),
#                     0.5,
#                     self.BORDER
#                 ),
#                 (
#                     "ALIGN",
#                     (0, 0),
#                     (-1, -1),
#                     "CENTER"
#                 ),
#                 (
#                     "VALIGN",
#                     (0, 0),
#                     (-1, -1),
#                     "MIDDLE"
#                 ),
#                 (
#                     "TOPPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     6
#                 ),
#                 (
#                     "BOTTOMPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     6
#                 ),
#             ])
#         )

#         return [
#             title,
#             legend,
#             Spacer(1, 8),
#         ]

#     # ============================================================
#     # BUILD ONE BLOCK
#     # ============================================================

#     def build_block(self, block):

#         text = block.get(
#             "_text",
#             ""
#         )

#         if not text:
#             return []

#         label = block.get(
#             "language"
#         )

#         if not label:
#             label = self.detect_language(
#                 text
#             )

#         language = self.language_name(
#             label
#         )

#         background = self.get_background(
#             label
#         )

#         label_color = self.get_label_color(
#             label
#         )

#         block_label = (
#             f'<b><font color="{label_color.hexval()}">'
#             f'{html.escape(language)}'
#             f'</font></b>'
#         )

#         label_paragraph = Paragraph(
#             block_label,
#             self.label_style
#         )

#         content = self.format_text(
#             text
#         )

#         paragraph_style = ParagraphStyle(
#             "HighlightedBlock",
#             parent=self.body_style,
#             fontSize=9.5,
#             leading=13,
#         )

#         content_paragraph = Paragraph(
#             content,
#             paragraph_style
#         )

#         block_table = Table(
#             [
#                 [
#                     label_paragraph
#                 ],
#                 [
#                     content_paragraph
#                 ],
#             ],
#             colWidths=[
#                 170 * mm
#             ],
#         )

#         block_table.setStyle(
#             TableStyle([
#                 (
#                     "BACKGROUND",
#                     (0, 0),
#                     (-1, -1),
#                     background
#                 ),
#                 (
#                     "BOX",
#                     (0, 0),
#                     (-1, -1),
#                     0.5,
#                     self.BORDER
#                 ),
#                 (
#                     "LEFTPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     6
#                 ),
#                 (
#                     "RIGHTPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     6
#                 ),
#                 (
#                     "TOPPADDING",
#                     (0, 0),
#                     (-1, 0),
#                     3
#                 ),
#                 (
#                     "BOTTOMPADDING",
#                     (0, 0),
#                     (-1, 0),
#                     1
#                 ),
#                 (
#                     "TOPPADDING",
#                     (0, 1),
#                     (-1, 1),
#                     3
#                 ),
#                 (
#                     "BOTTOMPADDING",
#                     (0, 1),
#                     (-1, 1),
#                     5
#                 ),
#             ])
#         )

#         return [
#             KeepTogether(
#                 [
#                     block_table,
#                     Spacer(
#                         1,
#                         4
#                     ),
#                 ]
#             )
#         ]

#     # ============================================================
#     # CREATE PDF
#     # ============================================================

#     def create_from_surya_json(
#         self,
#         json_paths,
#         output_path
#     ):

#         output_path = Path(
#             output_path
#         )

#         output_path.parent.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         print()
#         print("=" * 70)
#         print(
#             "ASTRA OCR - LANGUAGE HIGHLIGHTED PDF"
#         )
#         print("=" * 70)

#         document = SimpleDocTemplate(
#             str(output_path),
#             pagesize=A4,
#             rightMargin=15 * mm,
#             leftMargin=15 * mm,
#             topMargin=15 * mm,
#             bottomMargin=15 * mm,
#             title="Astra-OCR Language Highlighted PDF",
#         )

#         story = []

#         # --------------------------------------------------------
#         # LEGEND
#         # --------------------------------------------------------

#         story.extend(
#             self.create_legend()
#         )

#         # --------------------------------------------------------
#         # EACH PAGE
#         # --------------------------------------------------------

#         for page_index, json_path in enumerate(
#             json_paths,
#             start=1
#         ):

#             print(
#                 f"Reading: {json_path}"
#             )

#             data = self.load_surya_json(
#                 json_path
#             )

#             blocks = self.extract_blocks(
#                 data
#             )

#             print(
#                 f"Page {page_index}: "
#                 f"{len(blocks)} blocks"
#             )

#             page_name = ""

#             if blocks:

#                 page_name = blocks[0].get(
#                     "_page_name",
#                     ""
#                 )

#             page_match = re.search(
#                 r"page[_-]?(\d+)",
#                 str(page_name),
#                 flags=re.IGNORECASE
#             )

#             if page_match:

#                 page_number = int(
#                     page_match.group(1)
#                 )

#             else:

#                 page_number = page_index

#             # ----------------------------------------------------
#             # PAGE HEADER
#             # ----------------------------------------------------

#             story.append(
#                 Paragraph(
#                     f"Page {page_number}",
#                     self.header_style
#                 )
#             )

#             # ----------------------------------------------------
#             # BLOCKS
#             # ----------------------------------------------------

#             for block in blocks:

#                 label = str(
#                     block.get(
#                         "label",
#                         ""
#                     )
#                 ).lower()

#                 raw_html = str(
#                     block.get(
#                         "html",
#                         ""
#                     )
#                 )

#                 # ------------------------------------------------
#                 # TABLE
#                 # ------------------------------------------------

#                 if (
#                     "table"
#                     in label
#                     or "<table"
#                     in raw_html.lower()
#                 ):

#                     table_data = (
#                         self.parse_table_html(
#                             raw_html
#                         )
#                     )

#                     if table_data:

#                         story.append(
#                             self.create_highlighted_table(
#                                 table_data
#                             )
#                         )

#                         story.append(
#                             Spacer(
#                                 1,
#                                 7
#                             )
#                         )

#                         continue

#                 # ------------------------------------------------
#                 # NORMAL TEXT
#                 # ------------------------------------------------

#                 story.extend(
#                     self.build_block(
#                         block
#                     )
#                 )

#             if page_index < len(
#                 json_paths
#             ):

#                 story.append(
#                     PageBreak()
#                 )

#         # --------------------------------------------------------
#         # BUILD
#         # --------------------------------------------------------

#         document.build(
#             story
#         )

#         print()
#         print(
#             "Language highlighted PDF saved to:"
#         )

#         print(
#             output_path
#         )

#         return str(
#             output_path
#         )











from pathlib import Path

import json
import re
import html

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    Image,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from services.math_renderer import MathRenderer


class LanguageHighlightedPDFService:
    """
    Creates a text-only PDF from raw Surya OCR JSON.

    Supported languages:
        - English
        - Hindi
        - Gujarati
        - Bengali
        - Mixed

    Features:
        - Language highlighting
        - Language labels
        - Unicode fonts
        - Mixed-script support
        - Structured tables
        - Reading order
        - No original PDF images
        - Mathematical equation rendering
    """

    # ============================================================
    # COLORS
    # ============================================================

    ENGLISH_BG = colors.HexColor("#DCEEFF")
    HINDI_BG = colors.HexColor("#DFF5E1")
    GUJARATI_BG = colors.HexColor("#FFF1CC")
    BENGALI_BG = colors.HexColor("#F3D9FF")
    MIXED_BG = colors.HexColor("#EDEDED")
    UNKNOWN_BG = colors.HexColor("#F2F2F2")

    ENGLISH_LABEL = colors.HexColor("#1769AA")
    HINDI_LABEL = colors.HexColor("#218838")
    GUJARATI_LABEL = colors.HexColor("#B77900")
    BENGALI_LABEL = colors.HexColor("#8E44AD")
    MIXED_LABEL = colors.HexColor("#666666")

    BORDER = colors.HexColor("#B8B8B8")

    # ============================================================
    # INITIALIZATION
    # ============================================================

    def __init__(
        self,
        output_dir="output/pdf",
        fonts_dir="fonts",
    ):

        self.output_dir = Path(
            output_dir
        )

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        self.fonts_dir = Path(
            fonts_dir
        )

        self.fonts = {}

        self._register_fonts()

        self.styles = (
            getSampleStyleSheet()
        )

        self.body_style = ParagraphStyle(
            "AstraHighlightBody",
            parent=self.styles["BodyText"],
            fontName=self.fonts["latin"],
            fontSize=9.5,
            leading=13,
            alignment=TA_LEFT,
            spaceAfter=2,
        )

        self.header_style = ParagraphStyle(
            "AstraHighlightHeader",
            parent=self.styles["Heading2"],
            fontName=self.fonts["latin_bold"],
            fontSize=12,
            leading=15,
            alignment=TA_CENTER,
            spaceBefore=4,
            spaceAfter=8,
        )

        self.label_style = ParagraphStyle(
            "AstraLanguageLabel",
            parent=self.styles["BodyText"],
            fontName=self.fonts["latin_bold"],
            fontSize=6.5,
            leading=8,
            alignment=TA_LEFT,
        )

        # ========================================================
        # MATH RENDERER
        # ========================================================

        self.math_renderer = MathRenderer(
            output_dir="output/math"
        )

    # ============================================================
    # FONT DISCOVERY
    # ============================================================

    def _find_font(self, names):

        search_dirs = [
            self.fonts_dir,
            Path("fonts"),
            Path("backend/fonts"),
            Path(
                r"C:\Users\dalwa\desktop\astra-ocr\backend\fonts"
            ),
            Path(r"C:\Windows\Fonts"),
        ]

        for directory in search_dirs:

            if not directory.exists():
                continue

            for name in names:

                candidate = (
                    directory / name
                )

                if candidate.exists():
                    return candidate

        return None

    # ============================================================
    # REGISTER FONTS
    # ============================================================

    def _register_fonts(self):

        print(
            "Searching for Unicode fonts..."
        )

        # ========================================================
        # LATIN
        # ========================================================

        latin_regular = self._find_font([
            "NotoSans-Regular.ttf",
            "DejaVuSans.ttf",
        ])

        latin_bold = self._find_font([
            "NotoSans-Bold.ttf",
            "DejaVuSans-Bold.ttf",
        ])

        # ========================================================
        # DEVANAGARI
        # ========================================================

        devanagari_regular = self._find_font([
            "NotoSansDevanagari-Regular.ttf",
        ])

        devanagari_bold = self._find_font([
            "NotoSansDevanagari-Bold.ttf",
        ])

        # ========================================================
        # GUJARATI
        # ========================================================

        gujarati_regular = self._find_font([
            "NotoSansGujarati-Regular.ttf",
        ])

        gujarati_bold = self._find_font([
            "NotoSansGujarati-Bold.ttf",
        ])

        # ========================================================
        # BENGALI
        # ========================================================

        bengali_regular = self._find_font([
            "NotoSansBengali-Regular.ttf",
        ])

        bengali_bold = self._find_font([
            "NotoSansBengali-Bold.ttf",
        ])

        # ========================================================
        # LATIN
        # ========================================================

        if latin_regular:

            pdfmetrics.registerFont(
                TTFont(
                    "AstraHighlightLatin",
                    str(latin_regular)
                )
            )

            self.fonts["latin"] = (
                "AstraHighlightLatin"
            )

            print(
                f"Latin font: {latin_regular}"
            )

        else:

            self.fonts["latin"] = (
                "Helvetica"
            )

        if latin_bold:

            pdfmetrics.registerFont(
                TTFont(
                    "AstraHighlightLatinBold",
                    str(latin_bold)
                )
            )

            self.fonts["latin_bold"] = (
                "AstraHighlightLatinBold"
            )

        else:

            self.fonts["latin_bold"] = (
                "Helvetica-Bold"
            )

        # ========================================================
        # DEVANAGARI
        # ========================================================

        if devanagari_regular:

            pdfmetrics.registerFont(
                TTFont(
                    "AstraHighlightDevanagari",
                    str(devanagari_regular)
                )
            )

            self.fonts["devanagari"] = (
                "AstraHighlightDevanagari"
            )

            print(
                f"Devanagari font: "
                f"{devanagari_regular}"
            )

        else:

            self.fonts["devanagari"] = (
                self.fonts["latin"]
            )

            print(
                "WARNING: Devanagari font not found."
            )

        if devanagari_bold:

            pdfmetrics.registerFont(
                TTFont(
                    "AstraHighlightDevanagariBold",
                    str(devanagari_bold)
                )
            )

            self.fonts["devanagari_bold"] = (
                "AstraHighlightDevanagariBold"
            )

        else:

            self.fonts["devanagari_bold"] = (
                self.fonts["devanagari"]
            )

        # ========================================================
        # GUJARATI
        # ========================================================

        if gujarati_regular:

            pdfmetrics.registerFont(
                TTFont(
                    "AstraHighlightGujarati",
                    str(gujarati_regular)
                )
            )

            self.fonts["gujarati"] = (
                "AstraHighlightGujarati"
            )

            print(
                f"Gujarati font: "
                f"{gujarati_regular}"
            )

        else:

            self.fonts["gujarati"] = (
                self.fonts["latin"]
            )

            print(
                "WARNING: Gujarati font not found."
            )

        if gujarati_bold:

            pdfmetrics.registerFont(
                TTFont(
                    "AstraHighlightGujaratiBold",
                    str(gujarati_bold)
                )
            )

            self.fonts["gujarati_bold"] = (
                "AstraHighlightGujaratiBold"
            )

        else:

            self.fonts["gujarati_bold"] = (
                self.fonts["gujarati"]
            )

        # ========================================================
        # BENGALI
        # ========================================================

        if bengali_regular:

            pdfmetrics.registerFont(
                TTFont(
                    "AstraHighlightBengali",
                    str(bengali_regular)
                )
            )

            self.fonts["bengali"] = (
                "AstraHighlightBengali"
            )

            print(
                f"Bengali font: "
                f"{bengali_regular}"
            )

        else:

            self.fonts["bengali"] = (
                self.fonts["latin"]
            )

            print(
                "WARNING: Bengali font not found."
            )

        if bengali_bold:

            pdfmetrics.registerFont(
                TTFont(
                    "AstraHighlightBengaliBold",
                    str(bengali_bold)
                )
            )

            self.fonts["bengali_bold"] = (
                "AstraHighlightBengaliBold"
            )

        else:

            self.fonts["bengali_bold"] = (
                self.fonts["bengali"]
            )

        # ========================================================
        # PRINT
        # ========================================================

        print()

        print(
            "Registered highlighted PDF fonts:"
        )

        print(
            self.fonts
        )

    # ============================================================
    # LANGUAGE DETECTION
    # ============================================================

    @staticmethod
    def detect_language(text):

        if not text:
            return "unknown"

        devanagari = 0
        gujarati = 0
        bengali = 0
        latin = 0

        for char in text:

            code = ord(char)

            # ----------------------------------------------------
            # Devanagari
            # ----------------------------------------------------

            if (
                0x0900
                <= code
                <= 0x097F
            ):

                devanagari += 1

            # ----------------------------------------------------
            # Bengali
            # ----------------------------------------------------

            elif (
                0x0980
                <= code
                <= 0x09FF
            ):

                bengali += 1

            # ----------------------------------------------------
            # Gujarati
            # ----------------------------------------------------

            elif (
                0x0A80
                <= code
                <= 0x0AFF
            ):

                gujarati += 1

            # ----------------------------------------------------
            # Latin
            # ----------------------------------------------------

            elif (
                ("A" <= char <= "Z")
                or ("a" <= char <= "z")
            ):

                latin += 1

        total = (
            devanagari
            + gujarati
            + bengali
            + latin
        )

        if total == 0:
            return "unknown"

        active = 0

        if devanagari:
            active += 1

        if gujarati:
            active += 1

        if bengali:
            active += 1

        if latin:
            active += 1

        if active > 1:
            return "mixed"

        if devanagari:
            return "hindi"

        if bengali:
            return "bengali"

        if gujarati:
            return "gujarati"

        if latin:
            return "english"

        return "unknown"

    # ============================================================
    # LANGUAGE NAME
    # ============================================================

    @staticmethod
    def language_name(language):

        mapping = {
            "en": "English",
            "eng": "English",
            "english": "English",

            "hin": "Hindi",
            "hindi": "Hindi",

            "guj": "Gujarati",
            "gujarati": "Gujarati",

            "bn": "Bengali",
            "ben": "Bengali",
            "bengali": "Bengali",

            "mixed": "Mixed",
            "unknown": "Unknown",
        }

        return mapping.get(
            str(language).lower(),
            str(language)
        )

    # ============================================================
    # CLEAN HTML
    # ============================================================

    @staticmethod
    def clean_html(value):

        if value is None:
            return ""

        value = str(value)

        value = re.sub(
            r"<br\s*/?>",
            "\n",
            value,
            flags=re.IGNORECASE
        )

        value = re.sub(
            r"</p\s*>",
            "\n",
            value,
            flags=re.IGNORECASE
        )

        value = re.sub(
            r"<p[^>]*>",
            "",
            value,
            flags=re.IGNORECASE
        )

        value = re.sub(
            r"<[^>]+>",
            "",
            value
        )

        return html.unescape(
            value
        ).strip()

    # ============================================================
    # FORMAT TEXT WITH CORRECT FONT
    # ============================================================

    def format_text(
        self,
        text
    ):

        if not text:
            return ""

        text = self.clean_html(
            text
        )

        output = []

        current_script = None
        current_text = []

        def flush():

            nonlocal current_text
            nonlocal current_script

            if not current_text:
                return

            value = "".join(
                current_text
            )

            if current_script == "devanagari":

                font = self.fonts[
                    "devanagari"
                ]

            elif current_script == "gujarati":

                font = self.fonts[
                    "gujarati"
                ]

            elif current_script == "bengali":

                font = self.fonts[
                    "bengali"
                ]

            else:

                font = self.fonts[
                    "latin"
                ]

            escaped = html.escape(
                value
            )

            escaped = escaped.replace(
                "\n",
                "<br/>"
            )

            output.append(
                f'<font name="{font}">'
                f'{escaped}'
                f'</font>'
            )

            current_text = []

        for char in text:

            code = ord(char)

            # ----------------------------------------------------
            # Devanagari
            # ----------------------------------------------------

            if (
                0x0900
                <= code
                <= 0x097F
            ):

                script = "devanagari"

            # ----------------------------------------------------
            # Bengali
            # ----------------------------------------------------

            elif (
                0x0980
                <= code
                <= 0x09FF
            ):

                script = "bengali"

            # ----------------------------------------------------
            # Gujarati
            # ----------------------------------------------------

            elif (
                0x0A80
                <= code
                <= 0x0AFF
            ):

                script = "gujarati"

            # ----------------------------------------------------
            # Everything else
            # ----------------------------------------------------

            else:

                script = "latin"

            # ----------------------------------------------------
            # Preserve whitespace
            # ----------------------------------------------------

            if char.isspace():

                current_text.append(
                    char
                )

                continue

            # ----------------------------------------------------
            # Script changed
            # ----------------------------------------------------

            if (
                current_script is not None
                and script != current_script
            ):

                flush()

            current_script = script

            current_text.append(
                char
            )

        flush()

        return "".join(
            output
        )

    # ============================================================
    # LANGUAGE COLORS
    # ============================================================

    def get_background(
        self,
        language
    ):

        language = str(
            language
        ).lower()

        if language in (
            "en",
            "eng",
            "english",
        ):

            return self.ENGLISH_BG

        if language in (
            "hin",
            "hindi",
        ):

            return self.HINDI_BG

        if language in (
            "guj",
            "gujarati",
        ):

            return self.GUJARATI_BG

        if language in (
            "bn",
            "ben",
            "bengali",
        ):

            return self.BENGALI_BG

        if language == "mixed":

            return self.MIXED_BG

        return self.UNKNOWN_BG

    # ============================================================
    # LABEL COLORS
    # ============================================================

    def get_label_color(
        self,
        language
    ):

        language = str(
            language
        ).lower()

        if language in (
            "en",
            "eng",
            "english",
        ):

            return self.ENGLISH_LABEL

        if language in (
            "hin",
            "hindi",
        ):

            return self.HINDI_LABEL

        if language in (
            "guj",
            "gujarati",
        ):

            return self.GUJARATI_LABEL

        if language in (
            "bn",
            "ben",
            "bengali",
        ):

            return self.BENGALI_LABEL

        return self.MIXED_LABEL

    # ============================================================
    # LOAD RAW SURYA JSON
    # ============================================================

    def load_surya_json(
        self,
        json_path
    ):

        json_path = Path(
            json_path
        )

        with open(
            json_path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        return data

    # ============================================================
    # EXTRACT BLOCKS
    # ============================================================

    def extract_blocks(
        self,
        data
    ):

        blocks = []

        if not isinstance(
            data,
            dict
        ):

            return blocks

        for page_name, page_data in data.items():

            if not isinstance(
                page_data,
                list
            ):

                continue

            for page_item in page_data:

                if not isinstance(
                    page_item,
                    dict
                ):

                    continue

                page_blocks = page_item.get(
                    "blocks",
                    []
                )

                if not isinstance(
                    page_blocks,
                    list
                ):

                    continue

                for block in page_blocks:

                    if not isinstance(
                        block,
                        dict
                    ):

                        continue

                    if block.get(
                        "skipped",
                        False
                    ):

                        continue

                    text = self.clean_html(
                        block.get(
                            "html",
                            block.get(
                                "text",
                                ""
                            )
                        )
                    )

                    if not text:
                        continue

                    new_block = dict(
                        block
                    )

                    new_block[
                        "_page_name"
                    ] = page_name

                    new_block[
                        "_text"
                    ] = text

                    blocks.append(
                        new_block
                    )

        blocks.sort(
            key=lambda block: (
                block.get(
                    "_page_name",
                    ""
                ),
                block.get(
                    "reading_order",
                    999999
                )
            )
        )

        return blocks

    # ============================================================
    # EXTRACT TABLE ROWS
    # ============================================================

    def parse_table_html(
        self,
        text
    ):

        rows = re.findall(
            r"<tr[^>]*>(.*?)</tr>",
            text,
            flags=re.IGNORECASE | re.DOTALL
        )

        if not rows:
            return None

        table_data = []

        for row in rows:

            cells = re.findall(
                r"<t[dh][^>]*>"
                r"(.*?)"
                r"</t[dh]>",
                row,
                flags=re.IGNORECASE | re.DOTALL
            )

            if not cells:
                continue

            cleaned = []

            for cell in cells:

                cell_text = self.clean_html(
                    cell
                )

                cleaned.append(
                    cell_text
                )

            table_data.append(
                cleaned
            )

        if not table_data:
            return None

        max_columns = max(
            len(row)
            for row in table_data
        )

        for row in table_data:

            while len(row) < max_columns:

                row.append("")

        return table_data

    # ============================================================
    # CREATE TABLE
    # ============================================================

    def create_highlighted_table(
        self,
        table_data
    ):

        formatted_rows = []

        for row in table_data:

            formatted_row = []

            for cell in row:

                content = self.format_text(
                    cell
                )

                cell_style = ParagraphStyle(
                    "HighlightedTableCell",
                    parent=self.body_style,
                    fontSize=7.5,
                    leading=10,
                )

                paragraph = Paragraph(
                    content or " ",
                    cell_style
                )

                formatted_row.append(
                    paragraph
                )

            formatted_rows.append(
                formatted_row
            )

        column_count = max(
            len(row)
            for row in formatted_rows
        )

        available_width = (
            A4[0]
            - 30 * mm
        )

        column_width = (
            available_width
            / column_count
        )

        table = Table(
            formatted_rows,
            colWidths=[
                column_width
            ] * column_count,
            repeatRows=1,
        )

        commands = [

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                self.BORDER
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                4
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                4
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                4
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                4
            ),

        ]

        for row_index, row in enumerate(
            table_data
        ):

            for column_index, cell in enumerate(
                row
            ):

                language = (
                    self.detect_language(
                        cell
                    )
                )

                background = (
                    self.get_background(
                        language
                    )
                )

                commands.append(
                    (
                        "BACKGROUND",
                        (
                            column_index,
                            row_index
                        ),
                        (
                            column_index,
                            row_index
                        ),
                        background
                    )
                )

        table.setStyle(
            TableStyle(
                commands
            )
        )

        return table

    # ============================================================
    # LANGUAGE LEGEND
    # ============================================================

    def create_legend(self):

        title = Paragraph(
            "<b>Language Highlight Legend</b>",
            self.header_style
        )

        legend_data = [

            [

                Paragraph(
                    '<b><font color="#1769AA">'
                    'ENGLISH'
                    '</font></b>',
                    self.label_style
                ),

                Paragraph(
                    '<b><font color="#218838">'
                    'HINDI'
                    '</font></b>',
                    self.label_style
                ),

                Paragraph(
                    '<b><font color="#B77900">'
                    'GUJARATI'
                    '</font></b>',
                    self.label_style
                ),

                Paragraph(
                    '<b><font color="#8E44AD">'
                    'BENGALI'
                    '</font></b>',
                    self.label_style
                ),

                Paragraph(
                    '<b><font color="#666666">'
                    'MIXED'
                    '</font></b>',
                    self.label_style
                ),

            ]

        ]

        legend = Table(
            legend_data,
            colWidths=[
                34 * mm,
                34 * mm,
                38 * mm,
                34 * mm,
                30 * mm,
            ],
        )

        legend.setStyle(
            TableStyle([

                (
                    "BACKGROUND",
                    (0, 0),
                    (0, 0),
                    self.ENGLISH_BG
                ),

                (
                    "BACKGROUND",
                    (1, 0),
                    (1, 0),
                    self.HINDI_BG
                ),

                (
                    "BACKGROUND",
                    (2, 0),
                    (2, 0),
                    self.GUJARATI_BG
                ),

                (
                    "BACKGROUND",
                    (3, 0),
                    (3, 0),
                    self.BENGALI_BG
                ),

                (
                    "BACKGROUND",
                    (4, 0),
                    (4, 0),
                    self.MIXED_BG
                ),

                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    self.BORDER
                ),

                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    self.BORDER
                ),

                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER"
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),

            ])
        )

        return [
            title,
            legend,
            Spacer(
                1,
                8
            ),
        ]

    # ============================================================
    # ADD MATH BLOCK
    # ============================================================

    def add_math_block(
        self,
        text,
        background,
        label,
        label_color
    ):
        """
        Render mathematical OCR as an image while preserving
        the language-highlighted visual appearance.

        The OCR text itself is NOT changed.

        Returns:
            Table containing the language label and rendered
            mathematical equation, or None if rendering fails.
        """

        try:

            math_paths = (
                self.math_renderer.render_block(
                    text
                )
            )

        except Exception as exc:

            print(
                "[LanguageHighlightedPDF] "
                "Math rendering failed:"
            )

            print(exc)

            return None

        if not math_paths:

            return None

        # --------------------------------------------------------
        # LANGUAGE LABEL
        # --------------------------------------------------------

        block_label = (
            f'<b><font color="'
            f'{label_color.hexval()}">'
            f'{html.escape(label)}'
            f'</font></b>'
        )

        label_paragraph = Paragraph(
            block_label,
            self.label_style
        )

        # --------------------------------------------------------
        # MATH IMAGES
        # --------------------------------------------------------

        math_flowables = []

        for math_path in math_paths:

            try:

                from PIL import Image as PILImage

                with PILImage.open(
                    math_path
                ) as pil_image:

                    pixel_width, pixel_height = (
                        pil_image.size
                    )

                if pixel_width <= 0:
                    pixel_width = 1

                if pixel_height <= 0:
                    pixel_height = 1

                # ------------------------------------------------
                # Available PDF width
                # ------------------------------------------------

                max_width = 158 * mm

                # ------------------------------------------------
                # Preserve aspect ratio
                # ------------------------------------------------

                aspect_ratio = (
                    pixel_height
                    / pixel_width
                )

                display_width = min(
                    max_width,
                    max(
                        40 * mm,
                        pixel_width * 0.264583
                    )
                )

                display_height = (
                    display_width
                    * aspect_ratio
                )

                # ------------------------------------------------
                # Prevent extremely tall equations
                # ------------------------------------------------

                if display_height > 80 * mm:

                    display_height = 80 * mm

                    display_width = (
                        display_height
                        / aspect_ratio
                    )

                equation_image = Image(
                    math_path,
                    width=display_width,
                    height=display_height
                )

                equation_image.hAlign = "CENTER"

                math_flowables.append(
                    Spacer(
                        1,
                        3
                    )
                )

                math_flowables.append(
                    equation_image
                )

                math_flowables.append(
                    Spacer(
                        1,
                        3
                    )
                )

            except Exception as exc:

                print(
                    "[LanguageHighlightedPDF] "
                    f"Could not insert math image: "
                    f"{exc}"
                )

                return None

        # --------------------------------------------------------
        # Put all rendered equations in one table cell
        # --------------------------------------------------------

        equation_table = Table(
            [
                [
                    flowable
                ]
                for flowable in math_flowables
            ],
            colWidths=[
                158 * mm
            ]
        )

        equation_table.setStyle(
            TableStyle([

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    background
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    0
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    0
                ),

            ])
        )

        block_table = Table(
            [
                [
                    label_paragraph
                ],

                [
                    equation_table
                ],
            ],
            colWidths=[
                170 * mm
            ]
        )

        block_table.setStyle(
            TableStyle([

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    background
                ),

                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    self.BORDER
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, 0),
                    3
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, 0),
                    1
                ),

                (
                    "TOPPADDING",
                    (0, 1),
                    (-1, 1),
                    3
                ),

                (
                    "BOTTOMPADDING",
                    (0, 1),
                    (-1, 1),
                    5
                ),

            ])
        )

        return block_table

    # ============================================================
    # BUILD ONE BLOCK
    # ============================================================

    def build_block(
        self,
        block
    ):

        text = block.get(
            "_text",
            ""
        )

        if not text:
            return []

        label = block.get(
            "language"
        )

        if not label:

            label = self.detect_language(
                text
            )

        language = self.language_name(
            label
        )

        background = self.get_background(
            label
        )

        label_color = self.get_label_color(
            label
        )

        # ========================================================
        # MATH
        # ========================================================

        if self.math_renderer.looks_like_math(
            text
        ):

            math_block = self.add_math_block(
                text=text,
                background=background,
                label=language,
                label_color=label_color
            )

            if math_block is not None:

                return [
                    KeepTogether(
                        [
                            math_block,
                            Spacer(
                                1,
                                4
                            ),
                        ]
                    )
                ]

            # If math rendering fails, continue to the
            # original highlighted text implementation.

        # ========================================================
        # LANGUAGE LABEL
        # ========================================================

        block_label = (
            f'<b><font color="'
            f'{label_color.hexval()}">'
            f'{html.escape(language)}'
            f'</font></b>'
        )

        label_paragraph = Paragraph(
            block_label,
            self.label_style
        )

        # ========================================================
        # NORMAL TEXT
        # ========================================================

        content = self.format_text(
            text
        )

        paragraph_style = ParagraphStyle(
            "HighlightedBlock",
            parent=self.body_style,
            fontSize=9.5,
            leading=13,
        )

        content_paragraph = Paragraph(
            content,
            paragraph_style
        )

        block_table = Table(
            [
                [
                    label_paragraph
                ],

                [
                    content_paragraph
                ],
            ],
            colWidths=[
                170 * mm
            ],
        )

        block_table.setStyle(
            TableStyle([

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    background
                ),

                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    self.BORDER
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, 0),
                    3
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, 0),
                    1
                ),

                (
                    "TOPPADDING",
                    (0, 1),
                    (-1, 1),
                    3
                ),

                (
                    "BOTTOMPADDING",
                    (0, 1),
                    (-1, 1),
                    5
                ),

            ])
        )

        return [
            KeepTogether(
                [
                    block_table,
                    Spacer(
                        1,
                        4
                    ),
                ]
            )
        ]

    # ============================================================
    # CREATE PDF
    # ============================================================

    def create_from_surya_json(
        self,
        json_paths,
        output_path
    ):

        output_path = Path(
            output_path
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        print()

        print(
            "=" * 70
        )

        print(
            "ASTRA OCR - LANGUAGE HIGHLIGHTED PDF"
        )

        print(
            "=" * 70
        )

        document = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
            title=(
                "Astra-OCR Language "
                "Highlighted PDF"
            ),
        )

        story = []

        # --------------------------------------------------------
        # LEGEND
        # --------------------------------------------------------

        story.extend(
            self.create_legend()
        )

        # --------------------------------------------------------
        # EACH PAGE
        # --------------------------------------------------------

        for page_index, json_path in enumerate(
            json_paths,
            start=1
        ):

            print(
                f"Reading: {json_path}"
            )

            data = self.load_surya_json(
                json_path
            )

            blocks = self.extract_blocks(
                data
            )

            print(
                f"Page {page_index}: "
                f"{len(blocks)} blocks"
            )

            page_name = ""

            if blocks:

                page_name = blocks[0].get(
                    "_page_name",
                    ""
                )

            page_match = re.search(
                r"page[_-]?(\d+)",
                str(page_name),
                flags=re.IGNORECASE
            )

            if page_match:

                page_number = int(
                    page_match.group(1)
                )

            else:

                page_number = page_index

            # ----------------------------------------------------
            # PAGE HEADER
            # ----------------------------------------------------

            story.append(
                Paragraph(
                    f"Page {page_number}",
                    self.header_style
                )
            )

            # ----------------------------------------------------
            # BLOCKS
            # ----------------------------------------------------

            for block in blocks:

                label = str(
                    block.get(
                        "label",
                        ""
                    )
                ).lower()

                raw_html = str(
                    block.get(
                        "html",
                        ""
                    )
                )

                # ------------------------------------------------
                # TABLE
                # ------------------------------------------------

                if (
                    "table" in label
                    or "<table"
                    in raw_html.lower()
                ):

                    table_data = (
                        self.parse_table_html(
                            raw_html
                        )
                    )

                    if table_data:

                        story.append(
                            self.create_highlighted_table(
                                table_data
                            )
                        )

                        story.append(
                            Spacer(
                                1,
                                7
                            )
                        )

                        continue

                # ------------------------------------------------
                # IMAGE
                # ------------------------------------------------

                if (
                    label == "image"
                    or label == "picture"
                ):

                    continue

                # ------------------------------------------------
                # NORMAL / MATH TEXT
                # ------------------------------------------------

                story.extend(
                    self.build_block(
                        block
                    )
                )

            if page_index < len(
                json_paths
            ):

                story.append(
                    PageBreak()
                )

        # --------------------------------------------------------
        # BUILD
        # --------------------------------------------------------

        document.build(
            story
        )

        print()

        print(
            "Language highlighted PDF saved to:"
        )

        print(
            output_path
        )

        return str(
            output_path
        )