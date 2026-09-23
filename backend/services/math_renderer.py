from pathlib import Path
import re
import hashlib
import matplotlib

# Use matplotlib's internal math renderer.
# We do NOT require a LaTeX installation.
matplotlib.use("Agg")

import matplotlib.pyplot as plt


class MathRenderer:
    """
    Converts LaTeX-like OCR output into rendered mathematical images.

    This is a presentation-layer component.
    It does NOT participate in OCR recognition.
    """

    def __init__(self, output_dir="output/math"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # DETECTION
    # ---------------------------------------------------------

    @staticmethod
    def looks_like_math(text):
        """
        Determine whether a text block is probably mathematical.
        """

        if not isinstance(text, str):
            return False

        text = text.strip()

        if not text:
            return False

        math_patterns = [
            r"\\frac\s*\{",
            r"\\sqrt",
            r"\\pm",
            r"\\begin\s*\{",
            r"\\end\s*\{",
            r"\\left",
            r"\\right",
            r"\\log",
            r"\\sum",
            r"\\prod",
            r"\\int",
            r"\\leq",
            r"\\geq",
            r"\\neq",
            r"\\infty",
            r"\\alpha",
            r"\\beta",
            r"\\gamma",
            r"\\theta",
            r"\\pi",
            r"\^",
            r"_",
        ]

        matches = sum(
            1 for pattern in math_patterns
            if re.search(pattern, text)
        )

        # Strong mathematical markup
        if matches >= 1:
            return True

        # Equation-like text
        if (
            "=" in text
            and any(ch in text for ch in "+-*/^")
        ):
            return True

        return False

    # ---------------------------------------------------------
    # CLEAN OCR LATEX
    # ---------------------------------------------------------

    @staticmethod
    def clean_latex(text):
        """
        Clean common OCR-produced LaTeX wrappers.
        """

        if not text:
            return ""

        text = str(text)

        # HTML line breaks from Surya
        text = text.replace("<br/>", "\n")
        text = text.replace("<br>", "\n")
        text = text.replace("<br />", "\n")

        # Remove aligned environment wrappers.
        text = re.sub(
            r"\\begin\s*\{aligned\}",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\\end\s*\{aligned\}",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # Remove equation wrappers.
        text = re.sub(
            r"\\begin\s*\{equation\*?\}",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\\end\s*\{equation\*?\}",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # Remove display math delimiters
        text = text.replace("\\[", "")
        text = text.replace("\\]", "")
        text = text.replace("$$", "")

        # Convert LaTeX line endings
        text = text.replace(r"\\", "\n")

        # Clean alignment markers
        text = text.replace("&=", "=")
        text = text.replace("&", "")

        # Common LaTeX spacing commands
        text = re.sub(r"\\[,;:!]", " ", text)

        # \text{...} -> ...
        text = re.sub(
            r"\\text\s*\{([^{}]*)\}",
            r"\1",
            text,
        )

        # \mathrm{...} -> ...
        text = re.sub(
            r"\\mathrm\s*\{([^{}]*)\}",
            r"\1",
            text,
        )

        # \mathbf{...} -> ...
        text = re.sub(
            r"\\mathbf\s*\{([^{}]*)\}",
            r"\1",
            text,
        )

        # Remove excessive whitespace
        text = "\n".join(
            line.strip()
            for line in text.splitlines()
            if line.strip()
        )

        return text.strip()

    # ---------------------------------------------------------
    # SPLIT MULTI-LINE EQUATIONS
    # ---------------------------------------------------------

    @staticmethod
    def split_equations(text):
        """
        Split aligned mathematical expressions into individual
        equations.
        """

        text = MathRenderer.clean_latex(text)

        if not text:
            return []

        lines = []

        for line in text.splitlines():
            line = line.strip()

            if not line:
                continue

            lines.append(line)

        return lines

    # ---------------------------------------------------------
    # HASH
    # ---------------------------------------------------------

    @staticmethod
    def _hash(text):
        return hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()[:16]

    # ---------------------------------------------------------
    # RENDER ONE EQUATION
    # ---------------------------------------------------------

    def render_equation(
        self,
        latex,
        filename=None,
        dpi=200,
    ):
        """
        Render one mathematical expression to PNG.

        Returns:
            Path to generated PNG.
        """

        latex = self.clean_latex(latex)

        if not latex:
            return None

        if filename is None:
            filename = f"math_{self._hash(latex)}.png"

        output_path = self.output_dir / filename

        if output_path.exists():
            return str(output_path)

        # matplotlib mathtext expects $...$
        expression = f"${latex}$"

        try:
            fig = plt.figure(
                figsize=(10, 1.2),
                dpi=dpi,
            )

            fig.patch.set_alpha(0)

            fig.text(
                0.02,
                0.5,
                expression,
                fontsize=18,
                verticalalignment="center",
            )

            plt.axis("off")

            fig.savefig(
                output_path,
                dpi=dpi,
                transparent=True,
                bbox_inches="tight",
                pad_inches=0.08,
            )

            plt.close(fig)

            return str(output_path)

        except Exception as exc:
            plt.close("all")

            print(
                f"[MathRenderer] Could not render equation: "
                f"{latex}"
            )
            print(
                f"[MathRenderer] Reason: {exc}"
            )

            return None

    # ---------------------------------------------------------
    # RENDER MULTI-LINE EQUATION
    # ---------------------------------------------------------

    def render_block(
        self,
        text,
        filename_prefix=None,
        dpi=200,
    ):
        """
        Render a potentially multi-line mathematical block.

        Returns a list of PNG paths.
        """

        if not self.looks_like_math(text):
            return []

        lines = self.split_equations(text)

        if not lines:
            return []

        if filename_prefix is None:
            filename_prefix = f"math_{self._hash(text)}"

        output_paths = []

        for index, line in enumerate(lines):

            filename = (
                f"{filename_prefix}_{index:03d}.png"
            )

            path = self.render_equation(
                line,
                filename=filename,
                dpi=dpi,
            )

            if path:
                output_paths.append(path)

        return output_paths