import fitz
from pathlib import Path


class PDFAnalyzer:

    def __init__(self, pdf_path):
        self.pdf_path = Path(pdf_path)

        if not self.pdf_path.exists():
            raise FileNotFoundError(
                f"PDF not found: {self.pdf_path}"
            )

        if self.pdf_path.suffix.lower() != ".pdf":
            raise ValueError("Input file must be a PDF.")

    def analyze(self):

        document = fitz.open(self.pdf_path)

        result = {
            "filename": self.pdf_path.name,
            "total_pages": len(document),
            "pages": []
        }

        for page_number, page in enumerate(document, start=1):

            text = page.get_text("text").strip()

            images = page.get_images(full=True)

            page_width = page.rect.width
            page_height = page.rect.height

            has_text = len(text) > 0
            has_images = len(images) > 0

            # Basic page classification
            if has_text:
                page_type = "digital"
            else:
                page_type = "scanned"

            page_info = {
                "page_number": page_number,
                "type": page_type,
                "has_text": has_text,
                "has_images": has_images,
                "width": round(page_width, 2),
                "height": round(page_height, 2),
                "text_length": len(text),
                "image_count": len(images)
            }

            result["pages"].append(page_info)

        document.close()

        return result