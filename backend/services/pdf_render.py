import fitz
from pathlib import Path


class PDFRenderer:

    def __init__(self, pdf_path, output_dir="output/rendered"):
        self.pdf_path = Path(pdf_path)
        self.output_dir = Path(output_dir)

        if not self.pdf_path.exists():
            raise FileNotFoundError(
                f"PDF not found: {self.pdf_path}"
            )

        if self.pdf_path.suffix.lower() != ".pdf":
            raise ValueError("Input file must be a PDF.")

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    def render(self, dpi=300):

        document = fitz.open(self.pdf_path)

        # Convert DPI to zoom factor.
        zoom = dpi / 72

        matrix = fitz.Matrix(zoom, zoom)

        rendered_pages = []

        for page_number, page in enumerate(
            document,
            start=1
        ):

            pixmap = page.get_pixmap(
                matrix=matrix,
                alpha=False
            )

            output_path = (
                self.output_dir /
                f"page_{page_number:03d}.png"
            )

            pixmap.save(str(output_path))

            rendered_pages.append(
                str(output_path)
            )

            print(
                f"Rendered page {page_number}: "
                f"{output_path}"
            )

        document.close()

        return rendered_pages