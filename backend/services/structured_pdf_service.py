# from pathlib import Path
# import html
# import re

# from reportlab.lib import colors
# from reportlab.lib.enums import TA_CENTER, TA_LEFT
# from reportlab.lib.pagesizes import A4
# from reportlab.lib.styles import ParagraphStyle
# from reportlab.lib.units import mm
# from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont
# from reportlab.platypus import (
#     SimpleDocTemplate,
#     Paragraph,
#     Spacer,
#     Table,
#     TableStyle,
#     PageBreak
# )

# from services.surya_layout_service import SuryaLayoutService


# class StructuredPDFService:

#     def __init__(self, output_dir="output/pdf"):

#         self.output_dir = Path(output_dir)

#         self.output_dir.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         self.fonts = {}

#         self._register_fonts()

#     # =========================================================
#     # FIND FONT
#     # =========================================================

#     def _find_font(self, filenames):

#         search_dirs = [
#             Path("fonts"),
#             Path("backend/fonts"),
#             Path(r"C:\Windows\Fonts"),
#         ]

#         for directory in search_dirs:

#             if not directory.exists():
#                 continue

#             for filename in filenames:

#                 path = directory / filename

#                 if path.exists():
#                     return path

#         return None

#     # =========================================================
#     # REGISTER FONTS
#     # =========================================================

#     def _register_fonts(self):

#         print("\nSearching for Unicode fonts...")

#         # -----------------------------------------------------
#         # LATIN
#         # -----------------------------------------------------

#         latin_regular = self._find_font([
#             "NotoSans-Regular.ttf",
#             "NotoSans-Regular.otf",
#             "DejaVuSans.ttf",
#         ])

#         latin_bold = self._find_font([
#             "NotoSans-Bold.ttf",
#             "NotoSans-Bold.otf",
#             "DejaVuSans-Bold.ttf",
#         ])

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
#             "NirmalaB.ttf",
#             "NirmalaUI-Bold.ttf",
#         ])

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
#             "NirmalaB.ttf",
#             "NirmalaUI-Bold.ttf",
#         ])

#         # -----------------------------------------------------
#         # REGISTER LATIN
#         # -----------------------------------------------------

#         if latin_regular:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraLatin",
#                     str(latin_regular)
#                 )
#             )

#             self.fonts["latin"] = "AstraLatin"

#             print(
#                 f"Latin font: {latin_regular}"
#             )

#         if latin_bold:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraLatinBold",
#                     str(latin_bold)
#                 )
#             )

#             self.fonts["latin_bold"] = "AstraLatinBold"

#         # -----------------------------------------------------
#         # REGISTER DEVANAGARI
#         # -----------------------------------------------------

#         if devanagari_regular:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraDevanagari",
#                     str(devanagari_regular)
#                 )
#             )

#             self.fonts["devanagari"] = "AstraDevanagari"

#             print(
#                 f"Devanagari font: {devanagari_regular}"
#             )

#         if devanagari_bold:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraDevanagariBold",
#                     str(devanagari_bold)
#                 )
#             )

#             self.fonts["devanagari_bold"] = (
#                 "AstraDevanagariBold"
#             )

#         # -----------------------------------------------------
#         # REGISTER GUJARATI
#         # -----------------------------------------------------

#         if gujarati_regular:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraGujarati",
#                     str(gujarati_regular)
#                 )
#             )

#             self.fonts["gujarati"] = "AstraGujarati"

#             print(
#                 f"Gujarati font: {gujarati_regular}"
#             )

#         if gujarati_bold:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraGujaratiBold",
#                     str(gujarati_bold)
#                 )
#             )

#             self.fonts["gujarati_bold"] = (
#                 "AstraGujaratiBold"
#             )

#         # -----------------------------------------------------
#         # FALLBACK
#         # -----------------------------------------------------

#         if "latin" not in self.fonts:

#             self.fonts["latin"] = "Helvetica"

#         if "latin_bold" not in self.fonts:

#             self.fonts["latin_bold"] = "Helvetica-Bold"

#         print(
#             "\nRegistered fonts:"
#         )

#         print(
#             self.fonts
#         )

#         # -----------------------------------------------------
#         # IMPORTANT WARNING
#         # -----------------------------------------------------

#         if "devanagari" not in self.fonts:

#             print(
#                 "\nWARNING: Devanagari font not found."
#             )

#         if "gujarati" not in self.fonts:

#             print(
#                 "\nWARNING: Gujarati font not found."
#             )

#     # =========================================================
#     # DETECT CHARACTER SCRIPT
#     # =========================================================

#     def character_script(self, character):

#         if re.match(
#             r"[\u0900-\u097F]",
#             character
#         ):
#             return "devanagari"

#         if re.match(
#             r"[\u0A80-\u0AFF]",
#             character
#         ):
#             return "gujarati"

#         return "latin"

#     # =========================================================
#     # GET FONT FOR SCRIPT
#     # =========================================================

#     def get_font_for_script(
#         self,
#         script,
#         bold=False
#     ):

#         if script == "devanagari":

#             if bold:
#                 return self.fonts.get(
#                     "devanagari_bold",
#                     self.fonts.get(
#                         "devanagari",
#                         self.fonts["latin_bold"]
#                     )
#                 )

#             return self.fonts.get(
#                 "devanagari",
#                 self.fonts["latin"]
#             )

#         if script == "gujarati":

#             if bold:
#                 return self.fonts.get(
#                     "gujarati_bold",
#                     self.fonts.get(
#                         "gujarati",
#                         self.fonts["latin_bold"]
#                     )
#                 )

#             return self.fonts.get(
#                 "gujarati",
#                 self.fonts["latin"]
#             )

#         if bold:

#             return self.fonts[
#                 "latin_bold"
#             ]

#         return self.fonts[
#             "latin"
#         ]

#     # =========================================================
#     # FORMAT MIXED UNICODE TEXT
#     # =========================================================

#     def format_unicode_text(
#         self,
#         text,
#         bold=False
#     ):

#         if text is None:
#             return ""

#         text = str(text)

#         if not text:
#             return ""

#         output = []

#         current_script = None
#         current_text = []

#         def flush():

#             nonlocal current_script
#             nonlocal current_text

#             if not current_text:
#                 return

#             chunk = "".join(
#                 current_text
#             )

#             font_name = self.get_font_for_script(
#                 current_script,
#                 bold=bold
#             )

#             chunk = html.escape(
#                 chunk
#             )

#             chunk = chunk.replace(
#                 "\n",
#                 "<br/>"
#             )

#             output.append(
#                 f'<font name="{font_name}">'
#                 f'{chunk}'
#                 f'</font>'
#             )

#             current_text = []

#         for character in text:

#             # Preserve newline
#             if character == "\n":

#                 current_text.append(
#                     character
#                 )

#                 continue

#             script = self.character_script(
#                 character
#             )

#             # Keep whitespace with current run
#             if character.isspace():

#                 current_text.append(
#                     character
#                 )

#                 continue

#             if current_script is None:

#                 current_script = script

#             elif script != current_script:

#                 flush()

#                 current_script = script

#             current_text.append(
#                 character
#             )

#         flush()

#         return "".join(
#             output
#         )

#     # =========================================================
#     # CREATE STYLE
#     # =========================================================

#     def make_style(
#         self,
#         font_size=10,
#         leading=14,
#         alignment=TA_LEFT,
#         space_before=2,
#         space_after=5
#     ):

#         # Base font doesn't matter much because individual
#         # script runs receive their own font.
#         return ParagraphStyle(
#             name="AstraUnicodeStyle",
#             fontName=self.fonts["latin"],
#             fontSize=font_size,
#             leading=leading,
#             alignment=alignment,
#             spaceBefore=space_before,
#             spaceAfter=space_after,
#             allowWidows=0,
#             allowOrphans=0,
#         )

#     # =========================================================
#     # HTML TABLE → DATA
#     # =========================================================

#     def html_table_to_data(
#         self,
#         raw_html
#     ):

#         if not raw_html:
#             return None

#         rows = re.findall(
#             r"<tr[^>]*>(.*?)</tr>",
#             raw_html,
#             flags=re.IGNORECASE | re.DOTALL
#         )

#         if not rows:
#             return None

#         table_data = []

#         for row in rows:

#             cells = re.findall(
#                 r"<(?:td|th)[^>]*>"
#                 r"(.*?)"
#                 r"</(?:td|th)>",
#                 row,
#                 flags=re.IGNORECASE | re.DOTALL
#             )

#             if not cells:
#                 continue

#             clean_cells = []

#             for cell in cells:

#                 text = re.sub(
#                     r"<br\s*/?>",
#                     "\n",
#                     cell,
#                     flags=re.IGNORECASE
#                 )

#                 text = re.sub(
#                     r"<[^>]+>",
#                     "",
#                     text
#                 )

#                 text = html.unescape(
#                     text
#                 )

#                 text = re.sub(
#                     r"[ \t]+",
#                     " ",
#                     text
#                 )

#                 clean_cells.append(
#                     text.strip()
#                 )

#             table_data.append(
#                 clean_cells
#             )

#         return table_data or None

#     # =========================================================
#     # BUILD TABLE
#     # =========================================================

#     def build_table(
#         self,
#         table_data
#     ):

#         if not table_data:
#             return None

#         max_columns = max(
#             len(row)
#             for row in table_data
#         )

#         normalized = []

#         for row in table_data:

#             row = list(row)

#             while len(row) < max_columns:

#                 row.append("")

#             normalized.append(
#                 row
#             )

#         formatted = []

#         for row in normalized:

#             formatted_row = []

#             for cell in row:

#                 cell_markup = self.format_unicode_text(
#                     cell,
#                     bold=False
#                 )

#                 style = self.make_style(
#                     font_size=7.5,
#                     leading=9,
#                     space_before=0,
#                     space_after=0
#                 )

#                 formatted_row.append(
#                     Paragraph(
#                         cell_markup,
#                         style
#                     )
#                 )

#             formatted.append(
#                 formatted_row
#             )

#         table = Table(
#             formatted,
#             repeatRows=1
#         )

#         table.setStyle(
#             TableStyle([
#                 (
#                     "GRID",
#                     (0, 0),
#                     (-1, -1),
#                     0.5,
#                     colors.black
#                 ),
#                 (
#                     "VALIGN",
#                     (0, 0),
#                     (-1, -1),
#                     "TOP"
#                 ),
#                 (
#                     "LEFTPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     4
#                 ),
#                 (
#                     "RIGHTPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     4
#                 ),
#                 (
#                     "TOPPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     3
#                 ),
#                 (
#                     "BOTTOMPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     3
#                 ),
#             ])
#         )

#         return table

#     # =========================================================
#     # ADD BLOCK
#     # =========================================================

#     def add_block(
#         self,
#         story,
#         block
#     ):

#         block_type = block.get(
#             "type",
#             "text"
#         )

#         text = block.get(
#             "text",
#             ""
#         )

#         if not text:
#             return

#         # -----------------------------------------------------
#         # TITLE
#         # -----------------------------------------------------

#         if block_type == "title":

#             style = self.make_style(
#                 font_size=16,
#                 leading=20,
#                 alignment=TA_CENTER,
#                 space_before=8,
#                 space_after=10
#             )

#             markup = self.format_unicode_text(
#                 text,
#                 bold=True
#             )

#         # -----------------------------------------------------
#         # SECTION HEADER
#         # -----------------------------------------------------

#         elif block_type == "section_header":

#             style = self.make_style(
#                 font_size=13,
#                 leading=17,
#                 alignment=TA_CENTER,
#                 space_before=8,
#                 space_after=8
#             )

#             markup = self.format_unicode_text(
#                 text,
#                 bold=True
#             )

#         # -----------------------------------------------------
#         # PAGE HEADER
#         # -----------------------------------------------------

#         elif block_type == "page_header":

#             style = self.make_style(
#                 font_size=8,
#                 leading=10,
#                 alignment=TA_LEFT,
#                 space_before=2,
#                 space_after=4
#             )

#             markup = self.format_unicode_text(
#                 text
#             )

#         # -----------------------------------------------------
#         # HEADER / FOOTER
#         # -----------------------------------------------------

#         elif block_type in (
#             "header",
#             "footer",
#             "page_footer"
#         ):

#             style = self.make_style(
#                 font_size=8,
#                 leading=10,
#                 alignment=TA_LEFT,
#                 space_before=2,
#                 space_after=4
#             )

#             markup = self.format_unicode_text(
#                 text
#             )

#         # -----------------------------------------------------
#         # LIST
#         # -----------------------------------------------------

#         elif block_type == "list":

#             style = self.make_style(
#                 font_size=10,
#                 leading=14,
#                 space_before=2,
#                 space_after=4
#             )

#             markup = self.format_unicode_text(
#                 "• " + text
#             )

#         # -----------------------------------------------------
#         # NORMAL TEXT
#         # -----------------------------------------------------

#         else:

#             style = self.make_style(
#                 font_size=10,
#                 leading=14,
#                 space_before=2,
#                 space_after=5
#             )

#             markup = self.format_unicode_text(
#                 text
#             )

#         story.append(
#             Paragraph(
#                 markup,
#                 style
#             )
#         )

#         story.append(
#             Spacer(
#                 1,
#                 2
#             )
#         )

#     # =========================================================
#     # CREATE PDF
#     # =========================================================

#     def create_pdf(
#         self,
#         layout_result,
#         output_path
#     ):

#         output_path = Path(
#             output_path
#         )

#         output_path.parent.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         doc = SimpleDocTemplate(
#             str(output_path),
#             pagesize=A4,
#             rightMargin=15 * mm,
#             leftMargin=15 * mm,
#             topMargin=15 * mm,
#             bottomMargin=15 * mm,
#             title="Astra OCR Structured PDF",
#             author="Astra OCR"
#         )

#         story = []

#         pages = layout_result.get(
#             "pages",
#             []
#         )

#         for page_index, page in enumerate(
#             pages
#         ):

#             print(
#                 f"Building PDF page "
#                 f"{page.get('page')}: "
#                 f"{page.get('total_blocks', 0)} blocks"
#             )

#             blocks = page.get(
#                 "blocks",
#                 []
#             )

#             for block in blocks:

#                 block_type = block.get(
#                     "type",
#                     "text"
#                 )

#                 # -------------------------------------------------
#                 # TABLE
#                 # -------------------------------------------------

#                 if block_type == "table":

#                     table_data = self.html_table_to_data(
#                         block.get(
#                             "html",
#                             ""
#                         )
#                     )

#                     if table_data:

#                         table = self.build_table(
#                             table_data
#                         )

#                         if table:

#                             story.append(
#                                 Spacer(
#                                     1,
#                                     4
#                                 )
#                             )

#                             story.append(
#                                 table
#                             )

#                             story.append(
#                                 Spacer(
#                                     1,
#                                     8
#                                 )
#                             )

#                             continue

#                 # -------------------------------------------------
#                 # IGNORE IMAGE
#                 # -------------------------------------------------

#                 if block_type == "image":
#                     continue

#                 # -------------------------------------------------
#                 # ADD NORMAL BLOCK
#                 # -------------------------------------------------

#                 self.add_block(
#                     story,
#                     block
#                 )

#             # -----------------------------------------------------
#             # PAGE BREAK
#             # -----------------------------------------------------

#             if page_index < len(pages) - 1:

#                 story.append(
#                     PageBreak()
#                 )

#         # ---------------------------------------------------------
#         # BUILD
#         # ---------------------------------------------------------

#         doc.build(
#             story
#         )

#         print(
#             "\nStructured PDF saved to:"
#         )

#         print(
#             output_path
#         )

#         return str(
#             output_path
#         )

#     # =========================================================
#     # CREATE FROM SURYA JSON
#     # =========================================================

#     def create_from_surya_json(
#         self,
#         json_paths,
#         output_path
#     ):

#         if isinstance(
#             json_paths,
#             (str, Path)
#         ):

#             json_paths = [
#                 json_paths
#             ]

#         layout_service = SuryaLayoutService()

#         all_pages = []

#         for json_path in json_paths:

#             result = layout_service.process(
#                 json_path
#             )

#             all_pages.extend(
#                 result.get(
#                     "pages",
#                     []
#                 )
#             )

#         all_pages.sort(
#             key=lambda page: page["page"]
#         )

#         combined_result = {
#             "total_pages": len(
#                 all_pages
#             ),
#             "pages": all_pages
#         }

#         return self.create_pdf(
#             combined_result,
#             output_path
#         )











# from pathlib import Path

# import html
# import re

# from reportlab.lib import colors
# from reportlab.lib.enums import TA_CENTER, TA_LEFT
# from reportlab.lib.pagesizes import A4
# from reportlab.lib.styles import ParagraphStyle
# from reportlab.lib.units import mm
# from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont
# from reportlab.platypus import (
#     SimpleDocTemplate,
#     Paragraph,
#     Spacer,
#     Table,
#     TableStyle,
#     PageBreak,
#     Image,
# )
# from services.surya_layout_service import SuryaLayoutService
# from services.math_renderer import MathRenderer


# class StructuredPDFService:

#     def __init__(self, output_dir="output/pdf"):

#         self.output_dir = Path(output_dir)

#         self.output_dir.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         self.fonts = {}

#         self._register_fonts()

#         # =====================================================
#         # MATH RENDERER
#         # =====================================================
#         # Used only for rendering mathematical OCR output
#         # inside the generated PDF.
#         #
#         # OCR itself is NOT changed.
#         # JSON/TXT output is NOT changed.
#         # =====================================================

#         self.math_renderer = MathRenderer(
#             output_dir="output/math"
#         )

#     # =========================================================
#     # FIND FONT
#     # =========================================================

#     def _find_font(self, filenames):

#         search_dirs = [
#             Path("fonts"),
#             Path("backend/fonts"),
#             Path(
#                 r"C:\Users\dalwa\desktop\astra-ocr\backend\fonts"
#             ),
#             Path(r"C:\Windows\Fonts"),
#         ]

#         for directory in search_dirs:

#             if not directory.exists():
#                 continue

#             for filename in filenames:

#                 path = directory / filename

#                 if path.exists():
#                     return path

#         return None

#     # =========================================================
#     # REGISTER FONTS
#     # =========================================================

#     def _register_fonts(self):

#         print("\nSearching for Unicode fonts...")

#         # -----------------------------------------------------
#         # LATIN
#         # -----------------------------------------------------

#         latin_regular = self._find_font([
#             "NotoSans-Regular.ttf",
#             "NotoSans-Regular.otf",
#             "DejaVuSans.ttf",
#         ])

#         latin_bold = self._find_font([
#             "NotoSans-Bold.ttf",
#             "NotoSans-Bold.otf",
#             "DejaVuSans-Bold.ttf",
#         ])

#         # -----------------------------------------------------
#         # DEVANAGARI - HINDI
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
#             "NirmalaB.ttf",
#             "NirmalaUI-Bold.ttf",
#         ])

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
#             "NirmalaB.ttf",
#             "NirmalaUI-Bold.ttf",
#         ])

#         # -----------------------------------------------------
#         # BENGALI
#         # -----------------------------------------------------

#         bengali_regular = self._find_font([
#             "NotoSansBengali-Regular.ttf",
#             "NotoSansBengali-Regular.otf",
#         ])

#         bengali_bold = self._find_font([
#             "NotoSansBengali-Bold.ttf",
#             "NotoSansBengali-Bold.otf",
#         ])

#         # =====================================================
#         # REGISTER LATIN
#         # =====================================================

#         if latin_regular:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraLatin",
#                     str(latin_regular)
#                 )
#             )

#             self.fonts["latin"] = "AstraLatin"

#             print(
#                 f"Latin font: {latin_regular}"
#             )

#         if latin_bold:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraLatinBold",
#                     str(latin_bold)
#                 )
#             )

#             self.fonts["latin_bold"] = (
#                 "AstraLatinBold"
#             )

#         # =====================================================
#         # REGISTER DEVANAGARI
#         # =====================================================

#         if devanagari_regular:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraDevanagari",
#                     str(devanagari_regular)
#                 )
#             )

#             self.fonts["devanagari"] = (
#                 "AstraDevanagari"
#             )

#             print(
#                 f"Devanagari font: "
#                 f"{devanagari_regular}"
#             )

#         if devanagari_bold:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraDevanagariBold",
#                     str(devanagari_bold)
#                 )
#             )

#             self.fonts["devanagari_bold"] = (
#                 "AstraDevanagariBold"
#             )

#         # =====================================================
#         # REGISTER GUJARATI
#         # =====================================================

#         if gujarati_regular:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraGujarati",
#                     str(gujarati_regular)
#                 )
#             )

#             self.fonts["gujarati"] = (
#                 "AstraGujarati"
#             )

#             print(
#                 f"Gujarati font: "
#                 f"{gujarati_regular}"
#             )

#         if gujarati_bold:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraGujaratiBold",
#                     str(gujarati_bold)
#                 )
#             )

#             self.fonts["gujarati_bold"] = (
#                 "AstraGujaratiBold"
#             )

#         # =====================================================
#         # REGISTER BENGALI
#         # =====================================================

#         if bengali_regular:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraBengali",
#                     str(bengali_regular)
#                 )
#             )

#             self.fonts["bengali"] = (
#                 "AstraBengali"
#             )

#             print(
#                 f"Bengali font: "
#                 f"{bengali_regular}"
#             )

#         else:

#             print(
#                 "\nWARNING: Bengali font not found."
#             )

#         if bengali_bold:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraBengaliBold",
#                     str(bengali_bold)
#                 )
#             )

#             self.fonts["bengali_bold"] = (
#                 "AstraBengaliBold"
#             )

#         # =====================================================
#         # FALLBACKS
#         # =====================================================

#         if "latin" not in self.fonts:

#             self.fonts["latin"] = "Helvetica"

#         if "latin_bold" not in self.fonts:

#             self.fonts["latin_bold"] = (
#                 "Helvetica-Bold"
#             )

#         if "devanagari" not in self.fonts:

#             self.fonts["devanagari"] = (
#                 self.fonts["latin"]
#             )

#         if "devanagari_bold" not in self.fonts:

#             self.fonts["devanagari_bold"] = (
#                 self.fonts["devanagari"]
#             )

#         if "gujarati" not in self.fonts:

#             self.fonts["gujarati"] = (
#                 self.fonts["latin"]
#             )

#         if "gujarati_bold" not in self.fonts:

#             self.fonts["gujarati_bold"] = (
#                 self.fonts["gujarati"]
#             )

#         if "bengali" not in self.fonts:

#             self.fonts["bengali"] = (
#                 self.fonts["latin"]
#             )

#         if "bengali_bold" not in self.fonts:

#             self.fonts["bengali_bold"] = (
#                 self.fonts["bengali"]
#             )

#         # =====================================================
#         # PRINT REGISTERED FONTS
#         # =====================================================

#         print(
#             "\nRegistered fonts:"
#         )

#         print(
#             self.fonts
#         )

#         if (
#             self.fonts["devanagari"]
#             == self.fonts["latin"]
#         ):

#             print(
#                 "WARNING: Devanagari font not found."
#             )

#         if (
#             self.fonts["gujarati"]
#             == self.fonts["latin"]
#         ):

#             print(
#                 "WARNING: Gujarati font not found."
#             )

#         if (
#             self.fonts["bengali"]
#             == self.fonts["latin"]
#         ):

#             print(
#                 "WARNING: Bengali font not found."
#             )

#     # =========================================================
#     # DETECT CHARACTER SCRIPT
#     # =========================================================

#     def character_script(self, character):

#         code = ord(character)

#         # -----------------------------------------------------
#         # Devanagari
#         # -----------------------------------------------------

#         if (
#             0x0900
#             <= code
#             <= 0x097F
#         ):

#             return "devanagari"

#         # -----------------------------------------------------
#         # Gujarati
#         # -----------------------------------------------------

#         if (
#             0x0A80
#             <= code
#             <= 0x0AFF
#         ):

#             return "gujarati"

#         # -----------------------------------------------------
#         # Bengali
#         # -----------------------------------------------------

#         if (
#             0x0980
#             <= code
#             <= 0x09FF
#         ):

#             return "bengali"

#         # -----------------------------------------------------
#         # Latin
#         # -----------------------------------------------------

#         return "latin"

#     # =========================================================
#     # GET FONT FOR SCRIPT
#     # =========================================================

#     def get_font_for_script(
#         self,
#         script,
#         bold=False
#     ):

#         if script == "devanagari":

#             if bold:

#                 return self.fonts.get(
#                     "devanagari_bold",
#                     self.fonts["latin_bold"]
#                 )

#             return self.fonts.get(
#                 "devanagari",
#                 self.fonts["latin"]
#             )

#         if script == "gujarati":

#             if bold:

#                 return self.fonts.get(
#                     "gujarati_bold",
#                     self.fonts["latin_bold"]
#                 )

#             return self.fonts.get(
#                 "gujarati",
#                 self.fonts["latin"]
#             )

#         if script == "bengali":

#             if bold:

#                 return self.fonts.get(
#                     "bengali_bold",
#                     self.fonts["latin_bold"]
#                 )

#             return self.fonts.get(
#                 "bengali",
#                 self.fonts["latin"]
#             )

#         if bold:

#             return self.fonts[
#                 "latin_bold"
#             ]

#         return self.fonts[
#             "latin"
#         ]

#     # =========================================================
#     # FORMAT MIXED UNICODE TEXT
#     # =========================================================

#     def format_unicode_text(
#         self,
#         text,
#         bold=False
#     ):

#         if text is None:
#             return ""

#         text = str(text)

#         if not text:
#             return ""

#         output = []

#         current_script = None

#         current_text = []

#         def flush():

#             nonlocal current_script
#             nonlocal current_text

#             if not current_text:
#                 return

#             chunk = "".join(
#                 current_text
#             )

#             script = (
#                 current_script
#                 if current_script
#                 else "latin"
#             )

#             font_name = (
#                 self.get_font_for_script(
#                     script,
#                     bold=bold
#                 )
#             )

#             chunk = html.escape(
#                 chunk
#             )

#             chunk = chunk.replace(
#                 "\n",
#                 "<br/>"
#             )

#             output.append(
#                 f'<font name="{font_name}">'
#                 f'{chunk}'
#                 f'</font>'
#             )

#             current_text = []

#         for character in text:

#             # -------------------------------------------------
#             # Preserve newline
#             # -------------------------------------------------

#             if character == "\n":

#                 current_text.append(
#                     character
#                 )

#                 continue

#             script = self.character_script(
#                 character
#             )

#             # -------------------------------------------------
#             # Keep whitespace with current script
#             # -------------------------------------------------

#             if character.isspace():

#                 current_text.append(
#                     character
#                 )

#                 continue

#             # -------------------------------------------------
#             # Start first script
#             # -------------------------------------------------

#             if current_script is None:

#                 current_script = script

#             # -------------------------------------------------
#             # Script changed
#             # -------------------------------------------------

#             elif script != current_script:

#                 flush()

#                 current_script = script

#             current_text.append(
#                 character
#             )

#         flush()

#         return "".join(
#             output
#         )

#     # =========================================================
#     # CREATE STYLE
#     # =========================================================

#     def make_style(
#         self,
#         font_size=10,
#         leading=14,
#         alignment=TA_LEFT,
#         space_before=2,
#         space_after=5
#     ):

#         return ParagraphStyle(
#             name="AstraUnicodeStyle",
#             fontName=self.fonts["latin"],
#             fontSize=font_size,
#             leading=leading,
#             alignment=alignment,
#             spaceBefore=space_before,
#             spaceAfter=space_after,
#             allowWidows=0,
#             allowOrphans=0,
#         )

#     # =========================================================
#     # HTML TABLE → DATA
#     # =========================================================

#     def html_table_to_data(
#         self,
#         raw_html
#     ):

#         if not raw_html:
#             return None

#         rows = re.findall(
#             r"<tr[^>]*>(.*?)</tr>",
#             raw_html,
#             flags=re.IGNORECASE | re.DOTALL
#         )

#         if not rows:
#             return None

#         table_data = []

#         for row in rows:

#             cells = re.findall(
#                 r"<(?:td|th)[^>]*>"
#                 r"(.*?)"
#                 r"</(?:td|th)>",
#                 row,
#                 flags=re.IGNORECASE | re.DOTALL
#             )

#             if not cells:
#                 continue

#             clean_cells = []

#             for cell in cells:

#                 text = re.sub(
#                     r"<br\s*/?>",
#                     "\n",
#                     cell,
#                     flags=re.IGNORECASE
#                 )

#                 text = re.sub(
#                     r"<[^>]+>",
#                     "",
#                     text
#                 )

#                 text = html.unescape(
#                     text
#                 )

#                 text = re.sub(
#                     r"[ \t]+",
#                     " ",
#                     text
#                 )

#                 clean_cells.append(
#                     text.strip()
#                 )

#             table_data.append(
#                 clean_cells
#             )

#         return table_data or None

#     # =========================================================
#     # BUILD TABLE
#     # =========================================================

#     def build_table(
#         self,
#         table_data
#     ):

#         if not table_data:
#             return None

#         max_columns = max(
#             len(row)
#             for row in table_data
#         )

#         normalized = []

#         for row in table_data:

#             row = list(row)

#             while len(row) < max_columns:

#                 row.append("")

#             normalized.append(
#                 row
#             )

#         formatted = []

#         for row in normalized:

#             formatted_row = []

#             for cell in row:

#                 cell_markup = (
#                     self.format_unicode_text(
#                         cell,
#                         bold=False
#                     )
#                 )

#                 style = self.make_style(
#                     font_size=7.5,
#                     leading=9,
#                     space_before=0,
#                     space_after=0
#                 )

#                 formatted_row.append(
#                     Paragraph(
#                         cell_markup,
#                         style
#                     )
#                 )

#             formatted.append(
#                 formatted_row
#             )

#         table = Table(
#             formatted,
#             repeatRows=1
#         )

#         table.setStyle(
#             TableStyle([
#                 (
#                     "GRID",
#                     (0, 0),
#                     (-1, -1),
#                     0.5,
#                     colors.black
#                 ),
#                 (
#                     "VALIGN",
#                     (0, 0),
#                     (-1, -1),
#                     "TOP"
#                 ),
#                 (
#                     "LEFTPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     4
#                 ),
#                 (
#                     "RIGHTPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     4
#                 ),
#                 (
#                     "TOPPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     3
#                 ),
#                 (
#                     "BOTTOMPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     3
#                 ),
#             ])
#         )

#         return table

#     # =========================================================
#     # ADD MATH BLOCK
#     # =========================================================

#     def add_math_block(
#         self,
#         story,
#         text
#     ):
#         """
#         Render a mathematical OCR block as actual
#         mathematical notation in the PDF.

#         The original OCR text remains unchanged in
#         JSON/TXT. This method only affects PDF display.
#         """

#         try:

#             math_paths = (
#                 self.math_renderer.render_block(
#                     text
#                 )
#             )

#         except Exception as exc:

#             print(
#                 "[StructuredPDF] Math rendering failed:"
#             )

#             print(exc)

#             return False

#         if not math_paths:
#             return False

#         for math_path in math_paths:

#             try:

#                 # -------------------------------------------------
#                 # Read image dimensions.
#                 # -------------------------------------------------

#                 from PIL import Image as PILImage

#                 with PILImage.open(
#                     math_path
#                 ) as pil_image:

#                     pixel_width, pixel_height = (
#                         pil_image.size
#                     )

#                 if pixel_width <= 0:
#                     pixel_width = 1

#                 if pixel_height <= 0:
#                     pixel_height = 1

#                 # -------------------------------------------------
#                 # Maximum width available on A4.
#                 # -------------------------------------------------

#                 max_width = 170 * mm

#                 # -------------------------------------------------
#                 # Keep original aspect ratio.
#                 # -------------------------------------------------

#                 aspect_ratio = (
#                     pixel_height
#                     / pixel_width
#                 )

#                 display_width = min(
#                     max_width,
#                     max(40 * mm, pixel_width * 0.264583)
#                 )

#                 display_height = (
#                     display_width
#                     * aspect_ratio
#                 )

#                 # Prevent extremely large equations.
#                 if display_height > 80 * mm:

#                     display_height = 80 * mm

#                     display_width = (
#                         display_height
#                         / aspect_ratio
#                     )

#                 image = Image(
#                     math_path,
#                     width=display_width,
#                     height=display_height
#                 )

#                 image.hAlign = "CENTER"

#                 story.append(
#                     Spacer(
#                         1,
#                         4
#                     )
#                 )

#                 story.append(
#                     image
#                 )

#                 story.append(
#                     Spacer(
#                         1,
#                         6
#                     )
#                 )

#             except Exception as exc:

#                 print(
#                     "[StructuredPDF] "
#                     f"Could not insert rendered "
#                     f"math: {exc}"
#                 )

#                 return False

#         return True

#     # =========================================================
#     # ADD BLOCK
#     # =========================================================

#     def add_block(
#         self,
#         story,
#         block
#     ):

#         block_type = block.get(
#             "type",
#             "text"
#         )

#         text = block.get(
#             "text",
#             ""
#         )

#         if not text:
#             return

#         # =====================================================
#         # MATHEMATICS
#         # =====================================================
#         #
#         # Only mathematical-looking blocks are sent to the
#         # math renderer.
#         #
#         # Everything else follows the existing pipeline.
#         # =====================================================

#         if self.math_renderer.looks_like_math(
#             text
#         ):

#             rendered = self.add_math_block(
#                 story,
#                 text
#             )

#             if rendered:

#                 return

#             # If math rendering fails, fall back to the
#             # original text renderer instead of losing OCR.
#             print(
#                 "[StructuredPDF] "
#                 "Falling back to normal text "
#                 "for mathematical block."
#             )

#         # =====================================================
#         # EXISTING TEXT HANDLING
#         # =====================================================

#         if block_type == "title":

#             style = self.make_style(
#                 font_size=16,
#                 leading=20,
#                 alignment=TA_CENTER,
#                 space_before=8,
#                 space_after=10
#             )

#             markup = self.format_unicode_text(
#                 text,
#                 bold=True
#             )

#         elif block_type == "section_header":

#             style = self.make_style(
#                 font_size=13,
#                 leading=17,
#                 alignment=TA_CENTER,
#                 space_before=8,
#                 space_after=8
#             )

#             markup = self.format_unicode_text(
#                 text,
#                 bold=True
#             )

#         elif block_type == "page_header":

#             style = self.make_style(
#                 font_size=8,
#                 leading=10,
#                 alignment=TA_LEFT,
#                 space_before=2,
#                 space_after=4
#             )

#             markup = self.format_unicode_text(
#                 text
#             )

#         elif block_type in (
#             "header",
#             "footer",
#             "page_footer"
#         ):

#             style = self.make_style(
#                 font_size=8,
#                 leading=10,
#                 alignment=TA_LEFT,
#                 space_before=2,
#                 space_after=4
#             )

#             markup = self.format_unicode_text(
#                 text
#             )

#         elif block_type == "list":

#             style = self.make_style(
#                 font_size=10,
#                 leading=14,
#                 space_before=2,
#                 space_after=4
#             )

#             markup = self.format_unicode_text(
#                 "• " + text
#             )

#         else:

#             style = self.make_style(
#                 font_size=10,
#                 leading=14,
#                 space_before=2,
#                 space_after=5
#             )

#             markup = self.format_unicode_text(
#                 text
#             )

#         story.append(
#             Paragraph(
#                 markup,
#                 style
#             )
#         )

#         story.append(
#             Spacer(
#                 1,
#                 2
#             )
#         )

#     # =========================================================
#     # CREATE PDF
#     # =========================================================

#     def create_pdf(
#         self,
#         layout_result,
#         output_path
#     ):

#         output_path = Path(
#             output_path
#         )

#         output_path.parent.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         doc = SimpleDocTemplate(
#             str(output_path),
#             pagesize=A4,
#             rightMargin=15 * mm,
#             leftMargin=15 * mm,
#             topMargin=15 * mm,
#             bottomMargin=15 * mm,
#             title="Astra OCR Structured PDF",
#             author="Astra OCR"
#         )

#         story = []

#         pages = layout_result.get(
#             "pages",
#             []
#         )

#         for page_index, page in enumerate(
#             pages
#         ):

#             print(
#                 f"Building PDF page "
#                 f"{page.get('page')}: "
#                 f"{page.get('total_blocks', 0)} blocks"
#             )

#             blocks = page.get(
#                 "blocks",
#                 []
#             )

#             for block in blocks:

#                 block_type = block.get(
#                     "type",
#                     "text"
#                 )

#                 # -------------------------------------------------
#                 # TABLE
#                 # -------------------------------------------------

#                 if block_type == "table":

#                     table_data = (
#                         self.html_table_to_data(
#                             block.get(
#                                 "html",
#                                 ""
#                             )
#                         )
#                     )

#                     if table_data:

#                         table = self.build_table(
#                             table_data
#                         )

#                         if table:

#                             story.append(
#                                 Spacer(
#                                     1,
#                                     4
#                                 )
#                             )

#                             story.append(
#                                 table
#                             )

#                             story.append(
#                                 Spacer(
#                                     1,
#                                     8
#                                 )
#                             )

#                             continue

#                 # -------------------------------------------------
#                 # IMAGE
#                 # -------------------------------------------------

#                 if block_type == "image":

#                     continue

#                 # -------------------------------------------------
#                 # NORMAL / MATH BLOCK
#                 # -------------------------------------------------

#                 self.add_block(
#                     story,
#                     block
#                 )

#             if page_index < len(pages) - 1:

#                 story.append(
#                     PageBreak()
#                 )

#         doc.build(
#             story
#         )

#         print(
#             "\nStructured PDF saved to:"
#         )

#         print(
#             output_path
#         )

#         return str(
#             output_path
#         )

#     # =========================================================
#     # CREATE FROM SURYA JSON
#     # =========================================================

#     def create_from_surya_json(
#         self,
#         json_paths,
#         output_path
#     ):

#         if isinstance(
#             json_paths,
#             (str, Path)
#         ):

#             json_paths = [
#                 json_paths
#             ]

#         layout_service = (
#             SuryaLayoutService()
#         )

#         all_pages = []

#         for json_path in json_paths:

#             result = (
#                 layout_service.process(
#                     json_path
#                 )
#             )

#             all_pages.extend(
#                 result.get(
#                     "pages",
#                     []
#                 )
#             )

#         all_pages.sort(
#             key=lambda page: page["page"]
#         )

#         combined_result = {
#             "total_pages": len(
#                 all_pages
#             ),
#             "pages": all_pages
#         }

#         return self.create_pdf(
#             combined_result,
#             output_path
#         )















































# from pathlib import Path
# import html
# import re

# from reportlab.lib import colors
# from reportlab.lib.enums import TA_CENTER, TA_LEFT
# from reportlab.lib.pagesizes import A4
# from reportlab.lib.styles import ParagraphStyle
# from reportlab.lib.units import mm
# from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont
# from reportlab.platypus import (
#     SimpleDocTemplate,
#     Paragraph,
#     Spacer,
#     Table,
#     TableStyle,
#     PageBreak
# )

# from services.surya_layout_service import SuryaLayoutService


# class StructuredPDFService:

#     def __init__(self, output_dir="output/pdf"):

#         self.output_dir = Path(output_dir)

#         self.output_dir.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         self.fonts = {}

#         self._register_fonts()

#     # =========================================================
#     # FIND FONT
#     # =========================================================

#     def _find_font(self, filenames):

#         search_dirs = [
#             Path("fonts"),
#             Path("backend/fonts"),
#             Path(r"C:\Windows\Fonts"),
#         ]

#         for directory in search_dirs:

#             if not directory.exists():
#                 continue

#             for filename in filenames:

#                 path = directory / filename

#                 if path.exists():
#                     return path

#         return None

#     # =========================================================
#     # REGISTER FONTS
#     # =========================================================

#     def _register_fonts(self):

#         print("\nSearching for Unicode fonts...")

#         # -----------------------------------------------------
#         # LATIN
#         # -----------------------------------------------------

#         latin_regular = self._find_font([
#             "NotoSans-Regular.ttf",
#             "NotoSans-Regular.otf",
#             "DejaVuSans.ttf",
#         ])

#         latin_bold = self._find_font([
#             "NotoSans-Bold.ttf",
#             "NotoSans-Bold.otf",
#             "DejaVuSans-Bold.ttf",
#         ])

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
#             "NirmalaB.ttf",
#             "NirmalaUI-Bold.ttf",
#         ])

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
#             "NirmalaB.ttf",
#             "NirmalaUI-Bold.ttf",
#         ])

#         # -----------------------------------------------------
#         # REGISTER LATIN
#         # -----------------------------------------------------

#         if latin_regular:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraLatin",
#                     str(latin_regular)
#                 )
#             )

#             self.fonts["latin"] = "AstraLatin"

#             print(
#                 f"Latin font: {latin_regular}"
#             )

#         if latin_bold:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraLatinBold",
#                     str(latin_bold)
#                 )
#             )

#             self.fonts["latin_bold"] = "AstraLatinBold"

#         # -----------------------------------------------------
#         # REGISTER DEVANAGARI
#         # -----------------------------------------------------

#         if devanagari_regular:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraDevanagari",
#                     str(devanagari_regular)
#                 )
#             )

#             self.fonts["devanagari"] = "AstraDevanagari"

#             print(
#                 f"Devanagari font: {devanagari_regular}"
#             )

#         if devanagari_bold:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraDevanagariBold",
#                     str(devanagari_bold)
#                 )
#             )

#             self.fonts["devanagari_bold"] = (
#                 "AstraDevanagariBold"
#             )

#         # -----------------------------------------------------
#         # REGISTER GUJARATI
#         # -----------------------------------------------------

#         if gujarati_regular:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraGujarati",
#                     str(gujarati_regular)
#                 )
#             )

#             self.fonts["gujarati"] = "AstraGujarati"

#             print(
#                 f"Gujarati font: {gujarati_regular}"
#             )

#         if gujarati_bold:

#             pdfmetrics.registerFont(
#                 TTFont(
#                     "AstraGujaratiBold",
#                     str(gujarati_bold)
#                 )
#             )

#             self.fonts["gujarati_bold"] = (
#                 "AstraGujaratiBold"
#             )

#         # -----------------------------------------------------
#         # FALLBACK
#         # -----------------------------------------------------

#         if "latin" not in self.fonts:

#             self.fonts["latin"] = "Helvetica"

#         if "latin_bold" not in self.fonts:

#             self.fonts["latin_bold"] = "Helvetica-Bold"

#         print(
#             "\nRegistered fonts:"
#         )

#         print(
#             self.fonts
#         )

#         # -----------------------------------------------------
#         # IMPORTANT WARNING
#         # -----------------------------------------------------

#         if "devanagari" not in self.fonts:

#             print(
#                 "\nWARNING: Devanagari font not found."
#             )

#         if "gujarati" not in self.fonts:

#             print(
#                 "\nWARNING: Gujarati font not found."
#             )

#     # =========================================================
#     # DETECT CHARACTER SCRIPT
#     # =========================================================

#     def character_script(self, character):

#         if re.match(
#             r"[\u0900-\u097F]",
#             character
#         ):
#             return "devanagari"

#         if re.match(
#             r"[\u0A80-\u0AFF]",
#             character
#         ):
#             return "gujarati"

#         return "latin"

#     # =========================================================
#     # GET FONT FOR SCRIPT
#     # =========================================================

#     def get_font_for_script(
#         self,
#         script,
#         bold=False
#     ):

#         if script == "devanagari":

#             if bold:
#                 return self.fonts.get(
#                     "devanagari_bold",
#                     self.fonts.get(
#                         "devanagari",
#                         self.fonts["latin_bold"]
#                     )
#                 )

#             return self.fonts.get(
#                 "devanagari",
#                 self.fonts["latin"]
#             )

#         if script == "gujarati":

#             if bold:
#                 return self.fonts.get(
#                     "gujarati_bold",
#                     self.fonts.get(
#                         "gujarati",
#                         self.fonts["latin_bold"]
#                     )
#                 )

#             return self.fonts.get(
#                 "gujarati",
#                 self.fonts["latin"]
#             )

#         if bold:

#             return self.fonts[
#                 "latin_bold"
#             ]

#         return self.fonts[
#             "latin"
#         ]

#     # =========================================================
#     # FORMAT MIXED UNICODE TEXT
#     # =========================================================

#     def format_unicode_text(
#         self,
#         text,
#         bold=False
#     ):

#         if text is None:
#             return ""

#         text = str(text)

#         if not text:
#             return ""

#         output = []

#         current_script = None
#         current_text = []

#         def flush():

#             nonlocal current_script
#             nonlocal current_text

#             if not current_text:
#                 return

#             chunk = "".join(
#                 current_text
#             )

#             font_name = self.get_font_for_script(
#                 current_script,
#                 bold=bold
#             )

#             chunk = html.escape(
#                 chunk
#             )

#             chunk = chunk.replace(
#                 "\n",
#                 "<br/>"
#             )

#             output.append(
#                 f'<font name="{font_name}">'
#                 f'{chunk}'
#                 f'</font>'
#             )

#             current_text = []

#         for character in text:

#             # Preserve newline
#             if character == "\n":

#                 current_text.append(
#                     character
#                 )

#                 continue

#             script = self.character_script(
#                 character
#             )

#             # Keep whitespace with current run
#             if character.isspace():

#                 current_text.append(
#                     character
#                 )

#                 continue

#             if current_script is None:

#                 current_script = script

#             elif script != current_script:

#                 flush()

#                 current_script = script

#             current_text.append(
#                 character
#             )

#         flush()

#         return "".join(
#             output
#         )

#     # =========================================================
#     # CREATE STYLE
#     # =========================================================

#     def make_style(
#         self,
#         font_size=10,
#         leading=14,
#         alignment=TA_LEFT,
#         space_before=2,
#         space_after=5
#     ):

#         # Base font doesn't matter much because individual
#         # script runs receive their own font.
#         return ParagraphStyle(
#             name="AstraUnicodeStyle",
#             fontName=self.fonts["latin"],
#             fontSize=font_size,
#             leading=leading,
#             alignment=alignment,
#             spaceBefore=space_before,
#             spaceAfter=space_after,
#             allowWidows=0,
#             allowOrphans=0,
#         )

#     # =========================================================
#     # HTML TABLE → DATA
#     # =========================================================

#     def html_table_to_data(
#         self,
#         raw_html
#     ):

#         if not raw_html:
#             return None

#         rows = re.findall(
#             r"<tr[^>]*>(.*?)</tr>",
#             raw_html,
#             flags=re.IGNORECASE | re.DOTALL
#         )

#         if not rows:
#             return None

#         table_data = []

#         for row in rows:

#             cells = re.findall(
#                 r"<(?:td|th)[^>]*>"
#                 r"(.*?)"
#                 r"</(?:td|th)>",
#                 row,
#                 flags=re.IGNORECASE | re.DOTALL
#             )

#             if not cells:
#                 continue

#             clean_cells = []

#             for cell in cells:

#                 text = re.sub(
#                     r"<br\s*/?>",
#                     "\n",
#                     cell,
#                     flags=re.IGNORECASE
#                 )

#                 text = re.sub(
#                     r"<[^>]+>",
#                     "",
#                     text
#                 )

#                 text = html.unescape(
#                     text
#                 )

#                 text = re.sub(
#                     r"[ \t]+",
#                     " ",
#                     text
#                 )

#                 clean_cells.append(
#                     text.strip()
#                 )

#             table_data.append(
#                 clean_cells
#             )

#         return table_data or None

#     # =========================================================
#     # BUILD TABLE
#     # =========================================================

#     def build_table(
#         self,
#         table_data
#     ):

#         if not table_data:
#             return None

#         max_columns = max(
#             len(row)
#             for row in table_data
#         )

#         normalized = []

#         for row in table_data:

#             row = list(row)

#             while len(row) < max_columns:

#                 row.append("")

#             normalized.append(
#                 row
#             )

#         formatted = []

#         for row in normalized:

#             formatted_row = []

#             for cell in row:

#                 cell_markup = self.format_unicode_text(
#                     cell,
#                     bold=False
#                 )

#                 style = self.make_style(
#                     font_size=7.5,
#                     leading=9,
#                     space_before=0,
#                     space_after=0
#                 )

#                 formatted_row.append(
#                     Paragraph(
#                         cell_markup,
#                         style
#                     )
#                 )

#             formatted.append(
#                 formatted_row
#             )

#         table = Table(
#             formatted,
#             repeatRows=1
#         )

#         table.setStyle(
#             TableStyle([
#                 (
#                     "GRID",
#                     (0, 0),
#                     (-1, -1),
#                     0.5,
#                     colors.black
#                 ),
#                 (
#                     "VALIGN",
#                     (0, 0),
#                     (-1, -1),
#                     "TOP"
#                 ),
#                 (
#                     "LEFTPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     4
#                 ),
#                 (
#                     "RIGHTPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     4
#                 ),
#                 (
#                     "TOPPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     3
#                 ),
#                 (
#                     "BOTTOMPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     3
#                 ),
#             ])
#         )

#         return table

#     # =========================================================
#     # ADD BLOCK
#     # =========================================================

#     def add_block(
#         self,
#         story,
#         block
#     ):

#         block_type = block.get(
#             "type",
#             "text"
#         )

#         text = block.get(
#             "text",
#             ""
#         )

#         if not text:
#             return

#         # -----------------------------------------------------
#         # TITLE
#         # -----------------------------------------------------

#         if block_type == "title":

#             style = self.make_style(
#                 font_size=16,
#                 leading=20,
#                 alignment=TA_CENTER,
#                 space_before=8,
#                 space_after=10
#             )

#             markup = self.format_unicode_text(
#                 text,
#                 bold=True
#             )

#         # -----------------------------------------------------
#         # SECTION HEADER
#         # -----------------------------------------------------

#         elif block_type == "section_header":

#             style = self.make_style(
#                 font_size=13,
#                 leading=17,
#                 alignment=TA_CENTER,
#                 space_before=8,
#                 space_after=8
#             )

#             markup = self.format_unicode_text(
#                 text,
#                 bold=True
#             )

#         # -----------------------------------------------------
#         # PAGE HEADER
#         # -----------------------------------------------------

#         elif block_type == "page_header":

#             style = self.make_style(
#                 font_size=8,
#                 leading=10,
#                 alignment=TA_LEFT,
#                 space_before=2,
#                 space_after=4
#             )

#             markup = self.format_unicode_text(
#                 text
#             )

#         # -----------------------------------------------------
#         # HEADER / FOOTER
#         # -----------------------------------------------------

#         elif block_type in (
#             "header",
#             "footer",
#             "page_footer"
#         ):

#             style = self.make_style(
#                 font_size=8,
#                 leading=10,
#                 alignment=TA_LEFT,
#                 space_before=2,
#                 space_after=4
#             )

#             markup = self.format_unicode_text(
#                 text
#             )

#         # -----------------------------------------------------
#         # LIST
#         # -----------------------------------------------------

#         elif block_type == "list":

#             style = self.make_style(
#                 font_size=10,
#                 leading=14,
#                 space_before=2,
#                 space_after=4
#             )

#             markup = self.format_unicode_text(
#                 "• " + text
#             )

#         # -----------------------------------------------------
#         # NORMAL TEXT
#         # -----------------------------------------------------

#         else:

#             style = self.make_style(
#                 font_size=10,
#                 leading=14,
#                 space_before=2,
#                 space_after=5
#             )

#             markup = self.format_unicode_text(
#                 text
#             )

#         story.append(
#             Paragraph(
#                 markup,
#                 style
#             )
#         )

#         story.append(
#             Spacer(
#                 1,
#                 2
#             )
#         )

#     # =========================================================
#     # CREATE PDF
#     # =========================================================

#     def create_pdf(
#         self,
#         layout_result,
#         output_path
#     ):

#         output_path = Path(
#             output_path
#         )

#         output_path.parent.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         doc = SimpleDocTemplate(
#             str(output_path),
#             pagesize=A4,
#             rightMargin=15 * mm,
#             leftMargin=15 * mm,
#             topMargin=15 * mm,
#             bottomMargin=15 * mm,
#             title="Astra OCR Structured PDF",
#             author="Astra OCR"
#         )

#         story = []

#         pages = layout_result.get(
#             "pages",
#             []
#         )

#         for page_index, page in enumerate(
#             pages
#         ):

#             print(
#                 f"Building PDF page "
#                 f"{page.get('page')}: "
#                 f"{page.get('total_blocks', 0)} blocks"
#             )

#             blocks = page.get(
#                 "blocks",
#                 []
#             )

#             for block in blocks:

#                 block_type = block.get(
#                     "type",
#                     "text"
#                 )

#                 # -------------------------------------------------
#                 # TABLE
#                 # -------------------------------------------------

#                 if block_type == "table":

#                     table_data = self.html_table_to_data(
#                         block.get(
#                             "html",
#                             ""
#                         )
#                     )

#                     if table_data:

#                         table = self.build_table(
#                             table_data
#                         )

#                         if table:

#                             story.append(
#                                 Spacer(
#                                     1,
#                                     4
#                                 )
#                             )

#                             story.append(
#                                 table
#                             )

#                             story.append(
#                                 Spacer(
#                                     1,
#                                     8
#                                 )
#                             )

#                             continue

#                 # -------------------------------------------------
#                 # IGNORE IMAGE
#                 # -------------------------------------------------

#                 if block_type == "image":
#                     continue

#                 # -------------------------------------------------
#                 # ADD NORMAL BLOCK
#                 # -------------------------------------------------

#                 self.add_block(
#                     story,
#                     block
#                 )

#             # -----------------------------------------------------
#             # PAGE BREAK
#             # -----------------------------------------------------

#             if page_index < len(pages) - 1:

#                 story.append(
#                     PageBreak()
#                 )

#         # ---------------------------------------------------------
#         # BUILD
#         # ---------------------------------------------------------

#         doc.build(
#             story
#         )

#         print(
#             "\nStructured PDF saved to:"
#         )

#         print(
#             output_path
#         )

#         return str(
#             output_path
#         )

#     # =========================================================
#     # CREATE FROM SURYA JSON
#     # =========================================================

#     def create_from_surya_json(
#         self,
#         json_paths,
#         output_path
#     ):

#         if isinstance(
#             json_paths,
#             (str, Path)
#         ):

#             json_paths = [
#                 json_paths
#             ]

#         layout_service = SuryaLayoutService()

#         all_pages = []

#         for json_path in json_paths:

#             result = layout_service.process(
#                 json_path
#             )

#             all_pages.extend(
#                 result.get(
#                     "pages",
#                     []
#                 )
#             )

#         all_pages.sort(
#             key=lambda page: page["page"]
#         )

#         combined_result = {
#             "total_pages": len(
#                 all_pages
#             ),
#             "pages": all_pages
#         }

#         return self.create_pdf(
#             combined_result,
#             output_path
#         )







from pathlib import Path

import html
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
)

from services.surya_layout_service import SuryaLayoutService
from services.math_renderer import MathRenderer


class StructuredPDFService:

    def __init__(self, output_dir="output/pdf"):
        self.output_dir = Path(output_dir)

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        self.fonts = {}

        self._register_fonts()

        # =====================================================
        # MATH RENDERER
        # =====================================================
        # Used only for rendering mathematical OCR output
        # inside the generated PDF.
        #
        # OCR itself is NOT changed.
        # JSON/TXT output is NOT changed.
        # =====================================================

        self.math_renderer = MathRenderer(
            output_dir="output/math"
        )

    # =========================================================
    # FIND FONT
    # =========================================================

    def _find_font(self, filenames):

        search_dirs = [
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

            # Search recursively so fonts can be organized in
            # script-specific subfolders.
            for filename in filenames:

                direct = directory / filename

                if direct.exists():
                    return direct

                try:
                    matches = list(
                        directory.rglob(filename)
                    )
                except Exception:
                    matches = []

                if matches:
                    return matches[0]

        return None

    # =========================================================
    # REGISTER CID FONTS
    # =========================================================
    #
    # NotoSansCJKsc-Regular.otf,
    # NotoSansCJKjp-Regular.otf,
    # NotoSansCJKkr-Regular.otf
    #
    # are CFF/OpenType fonts and should not be passed through
    # ReportLab TTFont().
    #
    # ReportLab provides Unicode CID fonts specifically for
    # CJK PDF generation.
    #
    # Chinese:
    #   STSong-Light
    #
    # Japanese:
    #   HeiseiMin-W3
    #
    # Korean:
    #   HYSMyeongJo-Medium
    #
    # These are embedded/referenced through PDF CID mechanisms
    # and allow Unicode CJK text to survive PDF generation.
    # =========================================================

    def _register_cjk_fonts(self):

        print("\nRegistering CJK Unicode fonts...")

        # -----------------------------------------------------
        # Simplified Chinese
        # -----------------------------------------------------

        try:

            pdfmetrics.registerFont(
                UnicodeCIDFont("STSong-Light")
            )

            self.fonts["chinese"] = "STSong-Light"

            # The generic CJK script is routed to Chinese by
            # default because the Astra use case primarily
            # requires Simplified Chinese.

            self.fonts["cjk"] = "STSong-Light"

            print(
                "Chinese font: STSong-Light"
            )

        except Exception as exc:

            print(
                "WARNING: Could not register Chinese CID font:"
            )

            print(exc)

        # -----------------------------------------------------
        # Japanese
        # -----------------------------------------------------

        try:

            pdfmetrics.registerFont(
                UnicodeCIDFont("HeiseiMin-W3")
            )

            self.fonts["japanese"] = "HeiseiMin-W3"

            print(
                "Japanese font: HeiseiMin-W3"
            )

        except Exception as exc:

            print(
                "WARNING: Could not register Japanese CID font:"
            )

            print(exc)

        # -----------------------------------------------------
        # Korean
        # -----------------------------------------------------

        try:

            pdfmetrics.registerFont(
                UnicodeCIDFont(
                    "HYSMyeongJo-Medium"
                )
            )

            self.fonts["korean"] = (
                "HYSMyeongJo-Medium"
            )

            print(
                "Korean font: HYSMyeongJo-Medium"
            )

        except Exception as exc:

            print(
                "WARNING: Could not register Korean CID font:"
            )

            print(exc)

        # -----------------------------------------------------
        # Bold fallback for CJK.
        #
        # CID fonts do not have the same bold registration
        # mechanism as TTF fonts. We therefore use the regular
        # CJK CID font for bold CJK text.
        # -----------------------------------------------------

        if "chinese" in self.fonts:
            self.fonts["chinese_bold"] = (
                self.fonts["chinese"]
            )

        if "cjk" in self.fonts:
            self.fonts["cjk_bold"] = (
                self.fonts["cjk"]
            )

        if "japanese" in self.fonts:
            self.fonts["japanese_bold"] = (
                self.fonts["japanese"]
            )

        if "korean" in self.fonts:
            self.fonts["korean_bold"] = (
                self.fonts["korean"]
            )

    # =========================================================
    # REGISTER TTF FONTS
    # =========================================================

    def _register_fonts(self):

        print("\nSearching for Unicode fonts...")

        # =====================================================
        # CJK CID FONTS FIRST
        # =====================================================

        self._register_cjk_fonts()

        # =====================================================
        # TTF FONT SPECIFICATIONS
        # =====================================================

        font_specs = {

            "latin": (
                [
                    "NotoSans-Regular.ttf",
                    "NotoSans-Regular.otf",
                    "DejaVuSans.ttf",
                ],
                [
                    "NotoSans-Bold.ttf",
                    "NotoSans-Bold.otf",
                    "DejaVuSans-Bold.ttf",
                ],
            ),

            "cyrillic": (
                [
                    "NotoSans-Regular.ttf",
                    "DejaVuSans.ttf",
                ],
                [
                    "NotoSans-Bold.ttf",
                    "DejaVuSans-Bold.ttf",
                ],
            ),

            "greek": (
                [
                    "NotoSansGreek-Regular.ttf",
                    "NotoSans-Regular.ttf",
                    "DejaVuSans.ttf",
                ],
                [
                    "NotoSansGreek-Bold.ttf",
                    "NotoSans-Bold.ttf",
                    "DejaVuSans-Bold.ttf",
                ],
            ),

            "arabic": (
                [
                    "NotoSansArabic-Regular.ttf",
                ],
                [
                    "NotoSansArabic-Bold.ttf",
                ],
            ),

            "hebrew": (
                [
                    "NotoSansHebrew-Regular.ttf",
                ],
                [
                    "NotoSansHebrew-Bold.ttf",
                ],
            ),

            "armenian": (
                [
                    "NotoSansArmenian-Regular.ttf",
                ],
                [
                    "NotoSansArmenian-Bold.ttf",
                ],
            ),

            "georgian": (
                [
                    "NotoSansGeorgian-Regular.ttf",
                ],
                [
                    "NotoSansGeorgian-Bold.ttf",
                ],
            ),

            "devanagari": (
                [
                    "NotoSansDevanagari-Regular.ttf",
                    "Nirmala.ttf",
                    "NirmalaUI.ttf",
                ],
                [
                    "NotoSansDevanagari-Bold.ttf",
                    "NirmalaB.ttf",
                    "NirmalaUI-Bold.ttf",
                ],
            ),

            "bengali": (
                [
                    "NotoSansBengali-Regular.ttf",
                ],
                [
                    "NotoSansBengali-Bold.ttf",
                ],
            ),

            "gurmukhi": (
                [
                    "NotoSansGurmukhi-Regular.ttf",
                ],
                [
                    "NotoSansGurmukhi-Bold.ttf",
                ],
            ),

            "gujarati": (
                [
                    "NotoSansGujarati-Regular.ttf",
                    "Nirmala.ttf",
                    "NirmalaUI.ttf",
                ],
                [
                    "NotoSansGujarati-Bold.ttf",
                    "NirmalaB.ttf",
                    "NirmalaUI-Bold.ttf",
                ],
            ),

            "oriya": (
                [
                    "NotoSansOriya-Regular.ttf",
                    "NotoSansOdia-Regular.ttf",
                ],
                [
                    "NotoSansOriya-Bold.ttf",
                    "NotoSansOdia-Bold.ttf",
                ],
            ),

            "tamil": (
                [
                    "NotoSansTamil-Regular.ttf",
                ],
                [
                    "NotoSansTamil-Bold.ttf",
                ],
            ),

            "telugu": (
                [
                    "NotoSansTelugu-Regular.ttf",
                ],
                [
                    "NotoSansTelugu-Bold.ttf",
                ],
            ),

            "kannada": (
                [
                    "NotoSansKannada-Regular.ttf",
                ],
                [
                    "NotoSansKannada-Bold.ttf",
                ],
            ),

            "malayalam": (
                [
                    "NotoSansMalayalam-Regular.ttf",
                ],
                [
                    "NotoSansMalayalam-Bold.ttf",
                ],
            ),

            "sinhala": (
                [
                    "NotoSansSinhala-Regular.ttf",
                ],
                [
                    "NotoSansSinhala-Bold.ttf",
                ],
            ),

            "thai": (
                [
                    "NotoSansThai-Regular.ttf",
                ],
                [
                    "NotoSansThai-Bold.ttf",
                ],
            ),

            "lao": (
                [
                    "NotoSansLao-Regular.ttf",
                ],
                [
                    "NotoSansLao-Bold.ttf",
                ],
            ),

            "khmer": (
                [
                    "NotoSansKhmer-Regular.ttf",
                ],
                [
                    "NotoSansKhmer-Bold.ttf",
                ],
            ),

            "myanmar": (
                [
                    "NotoSansMyanmar-Regular.ttf",
                ],
                [
                    "NotoSansMyanmar-Bold.ttf",
                ],
            ),

            "ethiopic": (
                [
                    "NotoSansEthiopic-Regular.ttf",
                ],
                [
                    "NotoSansEthiopic-Bold.ttf",
                ],
            ),

            "mongolian": (
                [
                    "NotoSansMongolian-Regular.ttf",
                ],
                [
                    "NotoSansMongolian-Bold.ttf",
                ],
            ),

            "javanese": (
                [
                    "NotoSansJavanese-Regular.ttf",
                ],
                [
                    "NotoSansJavanese-Bold.ttf",
                ],
            ),

            "sundanese": (
                [
                    "NotoSansSundanese-Regular.ttf",
                ],
                [
                    "NotoSansSundanese-Bold.ttf",
                ],
            ),
        }

        # =====================================================
        # REGISTER TTF FONTS
        # =====================================================

        for script, (
            regular_names,
            bold_names
        ) in font_specs.items():

            regular_path = self._find_font(
                regular_names
            )

            bold_path = self._find_font(
                bold_names
            )

            # -------------------------------------------------
            # REGULAR
            # -------------------------------------------------

            if regular_path:

                try:

                    font_name = (
                        "Astra"
                        + script.title().replace(
                            "_",
                            ""
                        )
                    )

                    pdfmetrics.registerFont(
                        TTFont(
                            font_name,
                            str(regular_path)
                        )
                    )

                    self.fonts[script] = (
                        font_name
                    )

                    print(
                        f"{script} font: "
                        f"{regular_path}"
                    )

                except Exception as exc:

                    print(
                        "WARNING: Could not register "
                        f"{script} font "
                        f"{regular_path}: {exc}"
                    )

            # -------------------------------------------------
            # BOLD
            # -------------------------------------------------

            if bold_path:

                try:

                    font_name = (
                        "Astra"
                        + script.title().replace(
                            "_",
                            ""
                        )
                        + "Bold"
                    )

                    pdfmetrics.registerFont(
                        TTFont(
                            font_name,
                            str(bold_path)
                        )
                    )

                    self.fonts[
                        script + "_bold"
                    ] = font_name

                except Exception as exc:

                    print(
                        "WARNING: Could not register "
                        f"{script} bold font "
                        f"{bold_path}: {exc}"
                    )

        # =====================================================
        # LATIN FALLBACK
        # =====================================================

        if "latin" not in self.fonts:

            self.fonts["latin"] = "Helvetica"

        if "latin_bold" not in self.fonts:

            self.fonts[
                "latin_bold"
            ] = "Helvetica-Bold"

        # =====================================================
        # SCRIPT FALLBACKS
        # =====================================================

        for script in font_specs:

            if script == "latin":
                continue

            self.fonts.setdefault(
                script,
                self.fonts["latin"]
            )

            self.fonts.setdefault(
                script + "_bold",
                self.fonts.get(
                    script,
                    self.fonts["latin_bold"]
                )
            )

        # =====================================================
        # CJK FALLBACKS
        # =====================================================

        if "cjk" not in self.fonts:

            self.fonts["cjk"] = (
                self.fonts["latin"]
            )

            self.fonts["cjk_bold"] = (
                self.fonts["latin_bold"]
            )

        if "chinese" not in self.fonts:

            self.fonts["chinese"] = (
                self.fonts["cjk"]
            )

            self.fonts["chinese_bold"] = (
                self.fonts["cjk_bold"]
            )

        if "japanese" not in self.fonts:

            self.fonts["japanese"] = (
                self.fonts["cjk"]
            )

            self.fonts["japanese_bold"] = (
                self.fonts["cjk_bold"]
            )

        if "korean" not in self.fonts:

            self.fonts["korean"] = (
                self.fonts["cjk"]
            )

            self.fonts["korean_bold"] = (
                self.fonts["cjk_bold"]
            )

        print("\nRegistered fonts:")

        print(self.fonts)

    # =========================================================
    # CHARACTER → SCRIPT
    # =========================================================

    def character_script(self, character):

        code = ord(character)

        # =====================================================
        # UNICODE SCRIPT RANGES
        # =====================================================

        ranges = [

            # -------------------------------------------------
            # INDIAN
            # -------------------------------------------------

            (0x0900, 0x097F, "devanagari"),

            (0x0980, 0x09FF, "bengali"),

            (0x0A00, 0x0A7F, "gurmukhi"),

            (0x0A80, 0x0AFF, "gujarati"),

            (0x0B00, 0x0B7F, "oriya"),

            (0x0B80, 0x0BFF, "tamil"),

            (0x0C00, 0x0C7F, "telugu"),

            (0x0C80, 0x0CFF, "kannada"),

            (0x0D00, 0x0D7F, "malayalam"),

            (0x0D80, 0x0DFF, "sinhala"),

            # -------------------------------------------------
            # SOUTH EAST ASIAN
            # -------------------------------------------------

            (0x0E00, 0x0E7F, "thai"),

            (0x0E80, 0x0EFF, "lao"),

            (0x1000, 0x109F, "myanmar"),

            (0x1780, 0x17FF, "khmer"),

            # -------------------------------------------------
            # GEORGIAN
            # -------------------------------------------------

            (0x10A0, 0x10FF, "georgian"),

            # -------------------------------------------------
            # ETHIOPIC
            # -------------------------------------------------

            (0x1200, 0x137F, "ethiopic"),

            # -------------------------------------------------
            # ARMENIAN
            # -------------------------------------------------

            (0x0530, 0x058F, "armenian"),

            # -------------------------------------------------
            # HEBREW
            # -------------------------------------------------

            (0x0590, 0x05FF, "hebrew"),

            # -------------------------------------------------
            # ARABIC
            # -------------------------------------------------

            (0x0600, 0x06FF, "arabic"),

            (0x0700, 0x074F, "arabic"),

            (0x0750, 0x077F, "arabic"),

            (0x0780, 0x07BF, "arabic"),

            (0x07C0, 0x07FF, "arabic"),

            # -------------------------------------------------
            # GREEK
            # -------------------------------------------------

            (0x0370, 0x03FF, "greek"),

            # -------------------------------------------------
            # CYRILLIC
            # -------------------------------------------------

            (0x0400, 0x04FF, "cyrillic"),

            (0x0500, 0x052F, "cyrillic"),

            # -------------------------------------------------
            # MONGOLIAN
            # -------------------------------------------------

            (0x1800, 0x18AF, "mongolian"),

            # -------------------------------------------------
            # SUNDANESE
            # -------------------------------------------------

            (0x1B00, 0x1B7F, "sundanese"),

            # -------------------------------------------------
            # JAVANESE
            # -------------------------------------------------

            (0xA980, 0xA9DF, "javanese"),

            # =================================================
            # CJK / CHINESE / JAPANESE
            # =================================================

            # CJK Radicals
            (0x2E80, 0x2EFF, "cjk"),

            # Ideographic Description
            (0x2FF0, 0x2FFF, "cjk"),

            # CJK Symbols / Punctuation
            (0x3000, 0x303F, "cjk"),

            # Hiragana
            (0x3040, 0x309F, "japanese"),

            # Katakana
            (0x30A0, 0x30FF, "japanese"),

            # Bopomofo
            (0x3100, 0x312F, "chinese"),

            # CJK Compatibility
            (0x3130, 0x318F, "cjk"),

            # Katakana Phonetic Extensions
            (0x31A0, 0x31BF, "japanese"),

            # CJK Strokes
            (0x31C0, 0x31EF, "cjk"),

            # Katakana extensions
            (0x31F0, 0x31FF, "japanese"),

            # CJK Unified Ideographs Extension A
            (0x3400, 0x4DBF, "chinese"),

            # CJK Unified Ideographs
            (0x4E00, 0x9FFF, "chinese"),

            # Yi
            (0xA000, 0xA4CF, "cjk"),

            # Hangul
            (0xAC00, 0xD7AF, "korean"),

            # CJK Compatibility Ideographs
            (0xF900, 0xFAFF, "chinese"),

            # CJK Compatibility Forms
            (0xFE30, 0xFE4F, "cjk"),

            # Full-width / Half-width
            (0xFF00, 0xFFEF, "cjk"),

            # CJK Extension B+
            (0x20000, 0x2FA1F, "chinese"),
        ]

        for start, end, script in ranges:

            if start <= code <= end:

                return script

        return "latin"

    # =========================================================
    # GET FONT FOR SCRIPT
    # =========================================================

    def get_font_for_script(
        self,
        script,
        bold=False
    ):

        script = script or "latin"

        key = (
            script
            + ("_bold" if bold else "")
        )

        return self.fonts.get(

            key,

            self.fonts.get(

                script,

                self.fonts[
                    "latin_bold"
                    if bold
                    else "latin"
                ]

            )

        )

    # =========================================================
    # FORMAT UNICODE TEXT
    # =========================================================

    def format_unicode_text(
        self,
        text,
        bold=False
    ):

        if text is None:
            return ""

        text = str(text)

        if not text:
            return ""

        output = []

        current_script = None

        current_text = []

        def flush():

            nonlocal current_script
            nonlocal current_text

            if not current_text:
                return

            chunk = "".join(
                current_text
            )

            script = (
                current_script
                if current_script
                else "latin"
            )

            font_name = (
                self.get_font_for_script(
                    script,
                    bold=bold
                )
            )

            chunk = html.escape(
                chunk
            )

            chunk = chunk.replace(
                "\n",
                "<br/>"
            )

            output.append(
                f'<font name="{font_name}">'
                f'{chunk}'
                f'</font>'
            )

            current_text = []

        for character in text:

            # -------------------------------------------------
            # Preserve newline
            # -------------------------------------------------

            if character == "\n":

                current_text.append(
                    character
                )

                continue

            script = self.character_script(
                character
            )

            # -------------------------------------------------
            # Keep whitespace with current script
            # -------------------------------------------------

            if character.isspace():

                current_text.append(
                    character
                )

                continue

            # -------------------------------------------------
            # Start first script
            # -------------------------------------------------

            if current_script is None:

                current_script = script

            # -------------------------------------------------
            # Script changed
            # -------------------------------------------------

            elif script != current_script:

                flush()

                current_script = script

            current_text.append(
                character
            )

        flush()

        return "".join(
            output
        )

    # =========================================================
    # CREATE STYLE
    # =========================================================

    def make_style(
        self,
        font_size=10,
        leading=14,
        alignment=TA_LEFT,
        space_before=2,
        space_after=5
    ):

        return ParagraphStyle(

            name="AstraUnicodeStyle",

            fontName=self.fonts[
                "latin"
            ],

            fontSize=font_size,

            leading=leading,

            alignment=alignment,

            spaceBefore=space_before,

            spaceAfter=space_after,

            allowWidows=0,

            allowOrphans=0,

        )

    # =========================================================
    # HTML TABLE → DATA
    # =========================================================

    def html_table_to_data(
        self,
        raw_html
    ):

        if not raw_html:
            return None

        rows = re.findall(

            r"<tr[^>]*>(.*?)</tr>",

            raw_html,

            flags=(
                re.IGNORECASE
                | re.DOTALL
            )

        )

        if not rows:
            return None

        table_data = []

        for row in rows:

            cells = re.findall(

                r"<(?:td|th)[^>]*>"
                r"(.*?)"
                r"</(?:td|th)>",

                row,

                flags=(
                    re.IGNORECASE
                    | re.DOTALL
                )

            )

            if not cells:
                continue

            clean_cells = []

            for cell in cells:

                text = re.sub(

                    r"<br\s*/?>",

                    "\n",

                    cell,

                    flags=re.IGNORECASE

                )

                text = re.sub(

                    r"<[^>]+>",

                    "",

                    text

                )

                text = html.unescape(
                    text
                )

                text = re.sub(
                    r"[\t ]+",
                    " ",
                    text
                )

                clean_cells.append(
                    text.strip()
                )

            table_data.append(
                clean_cells
            )

        return (
            table_data
            or None
        )

    # =========================================================
    # BUILD TABLE
    # =========================================================

    def build_table(
        self,
        table_data
    ):

        if not table_data:
            return None

        max_columns = max(
            len(row)
            for row in table_data
        )

        normalized = []

        for row in table_data:

            row = list(row)

            while len(row) < max_columns:

                row.append("")

            normalized.append(
                row
            )

        formatted = []

        for row in normalized:

            formatted_row = []

            for cell in row:

                cell_markup = (
                    self.format_unicode_text(
                        cell,
                        bold=False
                    )
                )

                style = self.make_style(

                    font_size=7.5,

                    leading=9,

                    space_before=0,

                    space_after=0

                )

                formatted_row.append(

                    Paragraph(
                        cell_markup,
                        style
                    )

                )

            formatted.append(
                formatted_row
            )

        table = Table(
            formatted,
            repeatRows=1
        )

        table.setStyle(

            TableStyle([

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.black
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
                    3
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3
                ),

            ])

        )

        return table

    # =========================================================
    # ADD MATH BLOCK
    # =========================================================

    def add_math_block(
        self,
        story,
        text
    ):

        """
        Render a mathematical OCR block as actual
        mathematical notation in the PDF.

        The original OCR text remains unchanged in
        JSON/TXT. This method only affects PDF display.
        """

        try:

            math_paths = (
                self.math_renderer.render_block(
                    text
                )
            )

        except Exception as exc:

            print(
                "[StructuredPDF] Math rendering failed:"
            )

            print(exc)

            return False

        if not math_paths:
            return False

        for math_path in math_paths:

            try:

                # -------------------------------------------------
                # Read image dimensions.
                # -------------------------------------------------

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

                # -------------------------------------------------
                # Maximum width available on A4.
                # -------------------------------------------------

                max_width = 170 * mm

                # -------------------------------------------------
                # Keep original aspect ratio.
                # -------------------------------------------------

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

                # -------------------------------------------------
                # Prevent extremely large equations.
                # -------------------------------------------------

                if display_height > 80 * mm:

                    display_height = 80 * mm

                    display_width = (
                        display_height
                        / aspect_ratio
                    )

                image = Image(

                    math_path,

                    width=display_width,

                    height=display_height

                )

                image.hAlign = "CENTER"

                story.append(
                    Spacer(
                        1,
                        4
                    )
                )

                story.append(
                    image
                )

                story.append(
                    Spacer(
                        1,
                        6
                    )
                )

            except Exception as exc:

                print(
                    "[StructuredPDF] "
                    f"Could not insert rendered "
                    f"math: {exc}"
                )

                return False

        return True

    # =========================================================
    # ADD BLOCK
    # =========================================================

    def add_block(
        self,
        story,
        block
    ):

        block_type = block.get(
            "type",
            "text"
        )

        text = block.get(
            "text",
            ""
        )

        if not text:
            return

        # =====================================================
        # MATHEMATICS
        # =====================================================

        if self.math_renderer.looks_like_math(
            text
        ):

            rendered = self.add_math_block(
                story,
                text
            )

            if rendered:
                return

            print(
                "[StructuredPDF] "
                "Falling back to normal text "
                "for mathematical block."
            )

        # =====================================================
        # EXISTING TEXT HANDLING
        # =====================================================

        if block_type == "title":

            style = self.make_style(

                font_size=16,

                leading=20,

                alignment=TA_CENTER,

                space_before=8,

                space_after=10

            )

            markup = (
                self.format_unicode_text(
                    text,
                    bold=True
                )
            )

        elif block_type == "section_header":

            style = self.make_style(

                font_size=13,

                leading=17,

                alignment=TA_CENTER,

                space_before=8,

                space_after=8

            )

            markup = (
                self.format_unicode_text(
                    text,
                    bold=True
                )
            )

        elif block_type == "page_header":

            style = self.make_style(

                font_size=8,

                leading=10,

                alignment=TA_LEFT,

                space_before=2,

                space_after=4

            )

            markup = (
                self.format_unicode_text(
                    text
                )
            )

        elif block_type in (
            "header",
            "footer",
            "page_footer"
        ):

            style = self.make_style(

                font_size=8,

                leading=10,

                alignment=TA_LEFT,

                space_before=2,

                space_after=4

            )

            markup = (
                self.format_unicode_text(
                    text
                )
            )

        elif block_type == "list":

            style = self.make_style(

                font_size=10,

                leading=14,

                space_before=2,

                space_after=4

            )

            markup = (
                self.format_unicode_text(
                    "• " + text
                )
            )

        else:

            style = self.make_style(

                font_size=10,

                leading=14,

                space_before=2,

                space_after=5

            )

            markup = (
                self.format_unicode_text(
                    text
                )
            )

        story.append(

            Paragraph(
                markup,
                style
            )

        )

        story.append(

            Spacer(
                1,
                2
            )

        )

    # =========================================================
    # CREATE PDF
    # =========================================================

    def create_pdf(
        self,
        layout_result,
        output_path
    ):

        output_path = Path(
            output_path
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        doc = SimpleDocTemplate(

            str(output_path),

            pagesize=A4,

            rightMargin=15 * mm,

            leftMargin=15 * mm,

            topMargin=15 * mm,

            bottomMargin=15 * mm,

            title="Astra OCR Structured PDF",

            author="Astra OCR"

        )

        story = []

        pages = layout_result.get(
            "pages",
            []
        )

        for page_index, page in enumerate(
            pages
        ):

            print(

                f"Building PDF page "
                f"{page.get('page')}: "
                f"{page.get('total_blocks', 0)} blocks"

            )

            blocks = page.get(
                "blocks",
                []
            )

            for block in blocks:

                block_type = block.get(
                    "type",
                    "text"
                )

                # -------------------------------------------------
                # TABLE
                # -------------------------------------------------

                if block_type == "table":

                    table_data = (
                        self.html_table_to_data(
                            block.get(
                                "html",
                                ""
                            )
                        )
                    )

                    if table_data:

                        table = self.build_table(
                            table_data
                        )

                        if table:

                            story.append(
                                Spacer(
                                    1,
                                    4
                                )
                            )

                            story.append(
                                table
                            )

                            story.append(
                                Spacer(
                                    1,
                                    8
                                )
                            )

                            continue

                # -------------------------------------------------
                # IMAGE
                # -------------------------------------------------

                if block_type == "image":
                    continue

                # -------------------------------------------------
                # NORMAL / MATH BLOCK
                # -------------------------------------------------

                self.add_block(
                    story,
                    block
                )

            if page_index < len(pages) - 1:

                story.append(
                    PageBreak()
                )

        doc.build(
            story
        )

        print(
            "\nStructured PDF saved to:"
        )

        print(
            output_path
        )

        return str(
            output_path
        )

    # =========================================================
    # CREATE FROM SURYA JSON
    # =========================================================

    def create_from_surya_json(
        self,
        json_paths,
        output_path
    ):

        if isinstance(
            json_paths,
            (str, Path)
        ):

            json_paths = [
                json_paths
            ]

        layout_service = (
            SuryaLayoutService()
        )

        all_pages = []

        for json_path in json_paths:

            result = (
                layout_service.process(
                    json_path
                )
            )

            all_pages.extend(
                result.get(
                    "pages",
                    []
                )
            )

        all_pages.sort(
            key=lambda page: page["page"]
        )

        combined_result = {

            "total_pages": len(
                all_pages
            ),

            "pages": all_pages

        }

        return self.create_pdf(

            combined_result,

            output_path

        )